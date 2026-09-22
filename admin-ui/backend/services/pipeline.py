"""把 hook 事件 + run.yaml 依 stages.yaml 合成「階段狀態」；session 追蹤選擇存 SQLite。"""
import json
import pathlib
import re
import time

from .. import db
from . import events as ev_svc
from . import runs as run_svc
from . import stages as st_svc
from . import durations as dur_svc
from . import specflow as sf_svc

ACTIVE_RUN_STATUSES = ("RUNNING", "WAITING_HUMAN", "CREATED")
_meta_cache: dict[str, dict | None] = {}


# ---------- subagent meta.json（專案外唯讀，用來把 general-purpose 辨識成 Validator） ----------
def _subagent_meta(transcript_path: str, session_id: str, agent_id: str) -> dict | None:
    if not transcript_path or not agent_id:
        return None
    key = f"{session_id}:{agent_id}"
    if key in _meta_cache:
        return _meta_cache[key]
    base = pathlib.Path(transcript_path).parent / session_id / "subagents"
    meta = None
    try:
        cands = [base / f"agent-{agent_id}.meta.json"] + sorted(base.glob(f"agent-{agent_id[:8]}*.meta.json")) if base.exists() else []
        for c in cands:
            if c.exists():
                meta = json.loads(c.read_text(encoding="utf-8"))
                break
    except Exception:  # noqa: BLE001
        meta = None
    _meta_cache[key] = meta
    return meta


def _classify_agent(pipeline: dict, a: dict, s: dict) -> dict:
    """回傳 {stage_id, stage_title, signal, description, role}。pipeline 是這個 agent 所屬 run 的階段大綱
    （由呼叫端依 active_run.workflow_id 解出），不是全域設定——不同 workflow 的 stage id／agent 不共用。"""
    st, sig = st_svc.stage_for_agent_type(pipeline, a["agent_type"])
    meta = _subagent_meta(s.get("transcript_path", ""), s["session_id"], a["agent_id"])
    desc = (meta or {}).get("description") or ""
    role = a["subagent_name"] or a["agent_type"]
    if a["agent_type"] == "general-purpose":
        if desc and any(k in desc for k in ("獨立審查", "審查", "驗證", "Validator", "validator", "review")):
            iv = st_svc.independent_review_stage(pipeline)
            if iv:
                st = iv; sig = "strong"; role = f"{iv['title']}（獨立審查）"
        elif desc:
            role = f"general-purpose：{desc}"
    return {"stage_id": st["id"] if st else None, "stage_title": st["title"] if st else None, "signal": sig, "description": desc, "role": role}


# ---------- session 追蹤設定 ----------
def _session_rows() -> dict[str, dict]:
    with db.connect() as con:
        return {r["session_id"]: r for r in db.rows(con.execute("SELECT * FROM sessions"))}


def _sync_session_rows(sessions: dict[str, dict]):
    now = db.now()
    with db.connect() as con:
        known = {r["session_id"] for r in db.rows(con.execute("SELECT session_id FROM sessions"))}
        for sid, s in sessions.items():
            if sid in known:
                con.execute("UPDATE sessions SET last_seen_at=? WHERE session_id=?", (s["last_seen"], sid))
            else:
                con.execute("INSERT INTO sessions (session_id, first_seen_at, last_seen_at) VALUES (?,?,?)", (sid, s["first_seen"], s["last_seen"]))
        _ = now


def set_session(session_id: str, tracked: bool | None, ignored: bool | None, label: str | None) -> dict:
    with db.connect() as con:
        cur = db.one(con.execute("SELECT * FROM sessions WHERE session_id=?", (session_id,)))
        if not cur:
            ts = db.now()
            con.execute("INSERT INTO sessions (session_id, first_seen_at, last_seen_at) VALUES (?,?,?)", (session_id, ts, ts))
        if tracked is not None:
            if tracked:
                con.execute("UPDATE sessions SET tracked=0")  # 同時只追蹤一個
            con.execute("UPDATE sessions SET tracked=?, ignored=CASE WHEN ? THEN 0 ELSE ignored END WHERE session_id=?", (int(tracked), int(tracked), session_id))
        if ignored is not None:
            con.execute("UPDATE sessions SET ignored=?, tracked=CASE WHEN ? THEN 0 ELSE tracked END WHERE session_id=?", (int(ignored), int(ignored), session_id))
        if label is not None:
            con.execute("UPDATE sessions SET label=? WHERE session_id=?", (label, session_id))
        return db.one(con.execute("SELECT * FROM sessions WHERE session_id=?", (session_id,)))


# ---------- 狀態合成 ----------
def _health(cfg: dict, s: dict, now: float) -> dict:
    stall = cfg["stall"]
    idle = now - s["_last"]
    if s["ended_at"]:
        return {"state": "ended", "idle_seconds": int(idle)}
    if idle > stall.get("dead_after_seconds", 1800):
        return {"state": "dead", "idle_seconds": int(idle)}
    if idle > stall.get("warn_after_seconds", 600):
        return {"state": "stalled", "idle_seconds": int(idle)}
    return {"state": "live", "idle_seconds": int(idle)}


TERMINAL = ("CANCELLED", "FAILED", "COMPLETED")
TASK_LABEL = {"T1": "Spec 分析", "T2": "測試設計", "T3": "獨立驗證", "T4": "人工核准", "T5": "結案"}


def _run_stage_status(cfg: dict, run: dict, pipeline: dict | None = None) -> dict[str, dict]:
    """由 run.yaml 的 task 狀態推每個 stage 的 runtime 狀態，依 run 的 workflow_id 選對應的 pipeline 大綱
    （不再有「所有 workflow 共用 spec-to-testcase 的 T1..T5 大綱」這件事——task id 相同不代表語意相同）。

    run 已終止（CANCELLED/FAILED）時：實際開始過的階段標 cancelled/failed，從未開始的標 skipped。
    """
    out: dict[str, dict] = {}
    if not run:
        return out
    pipeline = pipeline or st_svc.pipeline_for_workflow(cfg, run.get("workflow_id"))
    out["intake"] = {"status": "done", "at": run.get("created_at")}
    max_iter = run.get("max_iterations") or 3
    for t in run["tasks"]:
        st = st_svc.stage_for_task(pipeline, t["task_id"])
        if not st:
            continue
        status = t["status"]
        mapped = {"DONE": "done", "RUNNING": "active", "READY": "active", "GATE_FAILED": "failed", "PENDING": "pending"}.get(status, "pending")
        if t["type"] == "approval" and status in ("RUNNING", "READY"):
            mapped = "waiting_human"
        started = bool(t["started_at"] or status in ("DONE", "RUNNING", "GATE_FAILED") or any(h.get("to") == "RUNNING" for h in t["history"]))
        dd = dur_svc._task_durations(t, time.time(), run["status"] in ("COMPLETED", "CANCELLED", "FAILED"))
        out[st["id"]] = {"status": mapped, "task_status": status, "iteration": t["iteration"], "max_iterations": max_iter,
                         "started_at": t["started_at"], "ended_at": t["ended_at"], "gate": t["gate"], "approval_id": t.get("approval_id"),
                         "task_id": t["task_id"], "started": started, "awaiting": mapped == "waiting_human",
                         "elapsed_seconds": dd["elapsed"], "work_seconds": dd["work"], "human_seconds": dd["human"], "elapsed_running": dd["running"]}
    if run.get("workflow_id") == "spec-to-testcase":
        # 整合／匯出不是 run 的 task，只有 spec-to-testcase 有這兩個合成階段：
        # 用 shadow-test 文件、修訂 run、final 檔當證據（specflow）
        for sid, ev in sf_svc.stage_evidence(run).items():
            out[sid] = ev
    if run["status"] == "COMPLETED":
        out["summary"] = {"status": "done", "at": run.get("updated_at"), "started": True}
    elif run["status"] in ("FAILED", "CANCELLED"):
        terminal = "cancelled" if run["status"] == "CANCELLED" else "failed"
        for v in out.values():
            if v.get("status") in ("active", "waiting_human", "pending"):
                v["status"] = terminal if v.get("started") else "skipped"
            v["awaiting"] = False
        out["summary"] = {"status": "skipped", "run_status": run["status"], "started": False}
    return out


def _related_runs(s: dict, runs: list[dict]) -> list[dict]:
    """和 session 活動區間（前後各留 10 分鐘）重疊的 run，依「區間內的活動筆數」排序。"""
    lo, hi = s["_first"] - 600, s["_last"] + 600
    scored = []
    for r in runs:
        score = 0
        if lo <= r["_created"] <= hi:
            score += 2
        for t in r["tasks"]:
            for h in t["history"]:
                if lo <= run_svc._ts(h.get("at")) <= hi:
                    score += 1
            for g in t["gate_results"]:
                if lo <= run_svc._ts(g.get("at")) <= hi:
                    score += 1
        for h in r["history"]:
            if lo <= run_svc._ts(h.get("at")) <= hi:
                score += 1
        if score:
            scored.append((score, r["_updated"], r))
    # 活著的 run 永遠排最前面：剛建立、還沒累積活動的 run 分數低，但它正是車道要顯示的對象（視圖只回前 8 筆）
    scored.sort(key=lambda x: (x[2]["status"] not in ACTIVE_RUN_STATUSES, -x[0], -x[1]))
    return [r for _, _, r in scored]


def _spec_short(run: dict | None) -> str | None:
    """SPEC-SITELIST-001 @ 0.4 → 'SITELIST v0.4'"""
    if not run:
        return None
    sid = run.get("spec_id") or ""
    m = re.match(r"SPEC-([A-Z0-9_]+)-\d+", sid)
    area = m.group(1) if m else (sid or run.get("testcase_id") or run["run_id"])
    ver = run.get("spec_version")
    return f"{area} v{ver}" if ver else area


def _area_of(run: dict | None) -> str | None:
    if not run:
        return None
    m = re.match(r"(?:SPEC|TC)-([A-Z0-9_]+)-", run.get("spec_id") or run.get("testcase_id") or "")
    return m.group(1) if m else None


def _timeline(run: dict | None, agents: list[dict]) -> list[dict]:
    """Agent 活動：run.yaml 的 task history / gate 為主，hook 的 SubagentStart/Stop 疊上去。"""
    items: list[dict] = []
    if run:
        items.append({"ts": run["created_at"], "kind": "run", "label": f"建立 run · {run['workflow_id']}", "status": "info"})
        for t in run["tasks"]:
            name = TASK_LABEL.get(t["task_id"], t["task_id"])
            role = "人工核准" if t["type"] == "approval" else (t["agent_id"] or "").replace("agent-", "")
            for h in t["history"]:
                to = h.get("to")
                if to == "RUNNING":
                    items.append({"ts": h["at"], "kind": "task", "label": f"{t['task_id']} {name} · {role} 開始" + (f"（第 {t['iteration'] + 1} 輪）" if t["task_id"] == "T2" and t["iteration"] else ""), "status": "active"})
                elif to == "DONE":
                    items.append({"ts": h["at"], "kind": "task", "label": f"{t['task_id']} {name} 完成" + (f" · {h.get('trigger')}" if h.get("trigger") and "PASS" in str(h.get("trigger")) else ""), "status": "done"})
                elif to == "GATE_FAILED":
                    items.append({"ts": h["at"], "kind": "task", "label": f"{t['task_id']} {name} · {t['gate'] or 'gate'} FAIL", "status": "failed"})
                elif to == "READY" and h.get("trigger") in ("revise", "route back"):
                    items.append({"ts": h["at"], "kind": "task", "label": f"{t['task_id']} 退回 {role} 修訂", "status": "warn"})
            for g in t["gate_results"]:
                if g.get("layer") == "semantic":
                    items.append({"ts": g["at"], "kind": "gate", "label": f"{t['task_id']} {t['gate']} {g['layer']} {g['result']}", "status": "done" if g["result"] == "PASS" else "failed"})
        for h in run["history"]:
            to = h.get("to")
            if to == "WAITING_HUMAN":
                items.append({"ts": h["at"], "kind": "run", "label": f"等待核准 {h.get('trigger')}", "status": "warn"})
            elif to in ("COMPLETED", "CANCELLED", "FAILED"):
                items.append({"ts": h["at"], "kind": "run", "label": {"COMPLETED": "run 完成", "CANCELLED": "run 取消", "FAILED": "run 失敗"}[to], "status": "done" if to == "COMPLETED" else "failed"})
    for a in agents:
        items.append({"ts": a["started_at"], "kind": "agent", "label": f"{a['role']} 開始" + (f" · {a['description']}" if a["description"] and a["description"] not in a["role"] else ""), "status": "active" if a["running"] else "info", "running": a["running"]})
        if a["ended_at"]:
            items.append({"ts": a["ended_at"], "kind": "agent", "label": f"{a['role']} 結束", "status": "info"})
    items = [i for i in items if i.get("ts")]
    items.sort(key=lambda i: i["ts"])
    return items


def _final_files(run: dict | None, s: dict) -> dict:
    """final 產出：以 testcases/final/ 檔案掃描為主（Bash cp 也抓得到），hook Write/Edit 為輔。"""
    from . import outputs as out_svc
    area = _area_of(run)
    files = []
    try:
        for f in out_svc.scan_files():
            fa = f.get("area") or ""
            if area is None or fa == area or fa.startswith(area + "-"):  # BONUSCCY 也對得上 BONUSCCY-001
                files.append({"name": f["name"], "path": f["path"], "group_key": f["group_key"], "kind": f["kind"], "modified_at": f["modified_at"], "mtime": f["mtime"]})
    except Exception:  # noqa: BLE001
        files = []
    files.sort(key=lambda f: -f["mtime"])
    return {"area": area, "files": files[:6], "hook_writes": s["final_writes"][-6:], "source": "hook" if s["final_writes"] else "scan"}


def _primary(run: dict | None, current_stage_title: str | None, health: dict, s: dict, now: float, spec_short: str | None) -> dict:
    """單一主狀態：run.status 優先，其次目前階段，session health 只當次要標籤。"""
    if not run:
        return {"primary_status": "no_run", "primary_label": "無關聯 run（僅事件）", "clock_frozen": bool(s["ended_at"]),
                "run_elapsed_seconds": None, "secondary": None}
    st = run["status"]
    started, updated = run["_created"], run["_updated"] or run["file_mtime"]
    frozen = st in TERMINAL
    elapsed = int(max(0, (updated if frozen else now) - started)) if started else None
    base = spec_short or run["run_id"]
    if st == "CANCELLED":
        label = f"{base} · 已取消"
    elif st == "FAILED":
        label = f"{base} · 失敗"
    elif st == "COMPLETED":
        label = f"{base} · 已完成"
    elif st == "WAITING_HUMAN":
        label = f"{base} · 等你決定" + (f" {run['waiting_on_approval_id']}" if run.get("waiting_on_approval_id") else "")
    elif st == "RUNNING":
        label = f"{base} · 執行中" + (f" · {current_stage_title}" if current_stage_title else "")
    else:
        label = f"{base} · {st or '未知'}"
    secondary = None
    if frozen and health["state"] in ("live", "stalled"):
        secondary = "session 仍連線"
    elif health["state"] == "stalled":
        secondary = "可能卡住"
    elif health["state"] == "dead":
        secondary = "session 已停止"
    elif health["state"] == "ended":
        secondary = "session 已結束"
    return {"primary_status": st.lower(), "primary_label": label, "clock_frozen": frozen, "run_elapsed_seconds": elapsed, "secondary": secondary}


def _next_action(run: dict | None, stages: list[dict], health: dict, s: dict, clrs: list[dict], final: dict, current_stage_title: str | None) -> dict:
    """現在要你做什麼——只回第一個命中的一句。"""
    if not run:
        return {"kind": "none", "text": "無關聯 run（僅事件）", "link": None}
    st = run["status"]
    waiting = next((x for x in stages if x["status"] == "waiting_human"), None)
    if st == "WAITING_HUMAN" or waiting:
        apr = run.get("waiting_on_approval_id") or (waiting or {}).get("runtime", {}).get("approval_id")
        return {"kind": "approve", "text": f"請核准 {apr or '（見 run）'}", "link": {"type": "run", "id": run["run_id"]}}
    if clrs:
        c = clrs[0]
        return {"kind": "clarify", "text": f"請回 {c['clarification_id']}" + (f"（另 {len(clrs) - 1} 張）" if len(clrs) > 1 else ""), "link": {"type": "run", "id": run["run_id"]}, "detail": c["question"]}
    if health["state"] == "stalled" and st == "RUNNING":
        return {"kind": "stalled", "text": f"可能卡住，已安靜 {health['idle_seconds'] // 60} 分鐘", "link": {"type": "session", "id": s["session_id"]}}
    cur = next((t for t in run["tasks"] if t["task_id"] == run.get("current_task_id")), None)
    if cur and cur["status"] == "GATE_FAILED":
        n, mx = cur["iteration"], run.get("max_iterations") or 3
        return {"kind": "gate_failed", "text": f"Validator FAIL，回 Designer 修 · 第 {n} / {mx} 輪", "link": {"type": "run", "id": run["run_id"]}}
    if st in ("CANCELLED", "FAILED") and health["state"] in ("live", "stalled", "dead"):
        return {"kind": "ignore", "text": "Run 已停，可忽略此 session", "link": {"type": "ignore", "id": s["session_id"]}}
    if st == "COMPLETED" and final["files"]:
        return {"kind": "review", "text": "產出已可審", "link": {"type": "outputs", "id": final["files"][0]["group_key"]}}
    if st in ("RUNNING", "CREATED"):
        return {"kind": "running", "text": f"進行中：{current_stage_title or '—'}", "link": {"type": "run", "id": run["run_id"]}}
    return {"kind": "done", "text": {"COMPLETED": "已完成", "CANCELLED": "已取消", "FAILED": "已失敗"}.get(st, st), "link": {"type": "run", "id": run["run_id"]}}


def session_view(cfg: dict, s: dict, rows: dict[str, dict], runs: list[dict], now: float, with_timeline: bool = False, run: dict | None = None) -> dict:
    """一個 session（可指定要看的 run）的完整視圖。run=None 時自動挑活著的／最相關的 run。"""
    row = rows.get(s["session_id"], {})
    related = _related_runs(s, runs)
    active_run = run or next((r for r in related if r["status"] in ACTIVE_RUN_STATUSES), None) or (related[0] if related else None)
    # 這個 session／run 的階段大綱：每個 workflow_id 各自一套（不是全域共用 spec-to-testcase 的大綱）
    pipeline = st_svc.pipeline_for_workflow(cfg, active_run["workflow_id"] if active_run else None)
    agents = []
    for a in s["agents"]:
        c = _classify_agent(pipeline, a, s)
        end = a["_end"] if a["_end"] else (now if not s["ended_at"] else s["_last"])
        agents.append({**{k: v for k, v in a.items() if not k.startswith("_")}, **c,
                       "elapsed_seconds": int(max(0, end - a["_start"])), "running": a["ended_at"] is None and not s["ended_at"]})
    current = next((a for a in reversed(agents) if a["running"]), None)
    health = _health(cfg, s, now)
    suggested = any(t in (cfg["session_filter"].get("suggest_when_agent_type") or []) for t in s["agent_types"])
    run_terminal = bool(active_run and active_run["status"] in TERMINAL)
    final = _final_files(active_run, s)
    # hook 事件沒有 run id：同 session 同時有 >1 個活 run 時，子 agent 無法歸屬到特定 run，不可用來覆蓋階段狀態
    concurrent = [r for r in related if r["status"] in ACTIVE_RUN_STATUSES]
    ambiguous = bool(active_run) and len(concurrent) > 1
    running_agents = [a for a in agents if a["running"]]

    # 階段合成：runtime 為主、events 補充。用「這個 run 的 workflow」對應的 pipeline 大綱，不是全域固定的清單。
    rt = _run_stage_status(cfg, active_run, pipeline) if active_run else {}
    stages = []
    for st in pipeline["stages"]:
        r = rt.get(st["id"], {})
        ev_hits = [a for a in agents if a["stage_id"] == st["id"]] if not ambiguous else []
        live = any(a["running"] for a in ev_hits)
        status = r.get("status", "pending")
        if active_run and active_run["status"] in ("CANCELLED", "FAILED") and status == "pending":
            status = "skipped"  # 只有取消／失敗才算「未執行」；COMPLETED 之後的整合、匯出是另外的流程，維持待進行
        if live and not run_terminal:
            status = "active"  # 事件比 run.yaml 即時：子 agent 還在跑就是進行中（可能是下一輪迭代）
        if st["id"] == "final-export" and not r and (final["files"] or s["final_writes"]) and not run_terminal:
            status = "done"
        elif st["id"] == "final-export" and not r and final["files"] and active_run and active_run["status"] == "COMPLETED":
            status = "done"
        last = max([a["ended_at"] or a["started_at"] for a in ev_hits] + [r.get("ended_at") or r.get("started_at") or ""], default="") or None
        stages.append({
            "id": st["id"], "title": st["title"], "agent": st.get("agent"), "gate": st.get("gate"), "order": st.get("order", 0),
            "status": status, "runtime": r or None, "event_agents": len(ev_hits), "live": live, "last_at": last,
            "notes": st.get("notes"), "loop_partner": bool(st.get("loop_partner")), "independent_review": bool(st.get("independent_review")),
        })
    if run_terminal:
        started_ids = [x["id"] for x in stages if x["status"] in ("cancelled", "failed")]
        current_stage = started_ids[-1] if started_ids else next((x["id"] for x in reversed(stages) if x["status"] == "done"), None)
    else:
        active_ids = [x["id"] for x in stages if x["status"] in ("active", "waiting_human", "failed")]
        current_stage = active_ids[-1] if active_ids else next((x["id"] for x in reversed(stages) if x["status"] == "done"), None)
    current_title = next((x["title"] for x in stages if x["id"] == current_stage), None)

    spec = f"{active_run['spec_id']}@{active_run['spec_version']}" if active_run and active_run.get("spec_id") else (active_run["testcase_id"] if active_run and active_run.get("testcase_id") else None)
    spec_short = _spec_short(active_run)
    from . import clarifications as clr_svc
    clrs = clr_svc.open_for_spec(active_run["spec_id"]) if active_run and active_run.get("spec_id") else []
    primary = _primary(active_run, current_title, health, s, now, spec_short)
    next_action = _next_action(active_run, stages, health, s, clrs, final, current_title)
    # 同 session 其他值得抬到頂的 run：目前 run 已終止時的 COMPLETED；以及同時在跑的其他 active run
    sibling = None
    siblings = []
    for r in related:
        if not active_run or r["run_id"] == active_run["run_id"]:
            continue
        keep = (run_terminal and r["status"] == "COMPLETED") or r["status"] in ACTIVE_RUN_STATUSES
        if keep:
            siblings.append({"run_id": r["run_id"], "spec": f"{r['spec_id']}@{r['spec_version']}" if r.get("spec_id") else r["run_id"], "status": r["status"]})
    if run_terminal:
        sibling = next((x for x in siblings if x["status"] == "COMPLETED"), None)

    view = {
        "lane_key": f"{s['session_id']}:{active_run['run_id'] if active_run else '-'}",
        "session_id": s["session_id"], "short_id": s["session_id"][:8], "label": row.get("label") or "",
        "spec": spec, "spec_short": spec_short, "workflow_id": active_run["workflow_id"] if active_run else None, "run_status": active_run["status"] if active_run else None,
        "pipeline_id": pipeline["id"], "pipeline_title": pipeline["title"],
        **primary, "next_action": next_action, "sibling_completed": sibling, "sibling_runs": siblings[:3], "open_clarifications": clrs,
        "tracked": bool(row.get("tracked")), "ignored": bool(row.get("ignored")), "suggested": suggested, "tag": s["tag"],
        "cwd": s["cwd"], "started_at": s["started_at"] or s["first_seen"], "ended_at": s["ended_at"], "end_reason": s["end_reason"],
        "first_seen": s["first_seen"], "last_seen": s["last_seen"], "event_count": s["event_count"], "stops": s["stops"],
        "duration_seconds": int(((s["_last"] if s["ended_at"] else now) - s["_first"])),
        "health": health, "agent_types": s["agent_types"], "agent_count": len(agents),
        "current_agent": current if not (run_terminal or ambiguous) else None, "current_stage": current_stage, "current_stage_title": current_title,
        "agent_note": (f"session 有 {len(running_agents)} 個子 agent 執行中（{len(concurrent)} 個 run 並行，hook 無法分辨屬於哪個 run）" if ambiguous and running_agents
                       else f"{len(concurrent)} 個 run 並行" if ambiguous else None),
        "final_writes": s["final_writes"], "final": final, "stages": stages,
        "related_runs": [{"run_id": r["run_id"], "workflow_id": r["workflow_id"], "status": r["status"], "spec_id": r["spec_id"], "spec_version": r["spec_version"],
                          "current_task_id": r["current_task_id"], "waiting_on_approval_id": r["waiting_on_approval_id"], "updated_at": r["updated_at"],
                          "tasks": [{"task_id": t["task_id"], "status": t["status"], "iteration": t["iteration"], "agent_id": t["agent_id"], "type": t["type"]} for t in r["tasks"]]}
                         for r in related[:8]],
        "active_run_id": active_run["run_id"] if active_run else None, "phase": sf_svc.run_phase(active_run["run_id"]) if active_run else None,
        "run_created_at": active_run["created_at"] if active_run else None,
        "run_updated_at": active_run["updated_at"] if active_run else None,
    }
    if with_timeline:
        view["agents"] = agents
        view["timeline"] = _timeline(active_run, agents)
    return view


def _lane_worthy(v: dict) -> bool:
    """即時分頁預設只放：run 仍活著（RUNNING / WAITING_HUMAN / CREATED），或明確追蹤中。"""
    if v["tracked"]:
        return True
    if v["ignored"]:
        return False
    if v["run_status"] in ACTIVE_RUN_STATUSES:
        return v["health"]["state"] != "ended"
    return False


def snapshot(session_id: str | None = None) -> dict:
    cfg = st_svc.load()
    now = time.time()
    sessions = ev_svc.sessions()
    _sync_session_rows(sessions)
    rows = _session_rows()
    runs = run_svc.all_runs()
    views = [session_view(cfg, s, rows, runs, now) for s in sessions.values()]
    views.sort(key=lambda v: v["last_seen"], reverse=True)
    visible = [v for v in views if not v["ignored"]]

    chosen = next((v for v in views if v["session_id"] == session_id), None) if session_id else None
    if not chosen:
        chosen = next((v for v in visible if v["tracked"]), None)
    if not chosen:
        chosen = next((v for v in visible if _lane_worthy(v)), None) \
            or next((v for v in visible if v["suggested"] and v["health"]["state"] != "ended"), None) \
            or next((v for v in visible if v["suggested"]), None)
    focus = session_view(cfg, sessions[chosen["session_id"]], rows, runs, now, with_timeline=True) if chosen else None

    # 即時車道：一個「活著的 run」一條（同 session 並行的 run 各自一條）；手選／追蹤中的 session 額外保留一條
    max_lanes = int(cfg.get("lanes") or 3)
    by_sid = {v["session_id"]: v for v in views}

    def owner_session(run: dict) -> dict | None:
        """這個 run 屬於哪個 session：related_runs 含它、且未忽略的 session 中最近活動的那個。"""
        cands = [v for v in visible if any(r["run_id"] == run["run_id"] for r in v["related_runs"])]
        return cands[0] if cands else None

    lane_views: list[dict] = []
    seen_runs: set[str] = set()
    active_runs = sorted([r for r in runs if r["status"] in ACTIVE_RUN_STATUSES], key=lambda r: -(r["_updated"] or r["file_mtime"]))
    for r in active_runs:
        v = owner_session(r)
        if not v or v["health"]["state"] == "ended" and not v["tracked"]:
            continue
        lane_views.append(session_view(cfg, sessions[v["session_id"]], rows, runs, now, with_timeline=True, run=r))
        seen_runs.add(r["run_id"])
    # 手選 / 追蹤中的 session：若它的 run 沒在上面出現，補一條（run 可能已結束，主狀態會說清楚且時鐘凍結）
    extra = [chosen] if chosen and (session_id or chosen["tracked"]) else []
    extra += [v for v in visible if v["tracked"] and v is not chosen]
    for v in extra:
        if v["active_run_id"] not in seen_runs:
            lane_views.insert(0, session_view(cfg, sessions[v["session_id"]], rows, runs, now, with_timeline=True))
            seen_runs.add(v["active_run_id"])
    lanes = lane_views[:max_lanes]
    lane_run_ids = {v["active_run_id"] for v in lanes}
    for v in lanes:
        v["sibling_runs"] = [x for x in v["sibling_runs"] if x["run_id"] not in lane_run_ids]
    _ = by_sid

    return {
        "generated_at": db.now(),
        "stall": cfg["stall"],
        "max_lanes": max_lanes,
        "lanes": lanes,
        # 舊欄位：spec-to-testcase 的階段大綱（相容用；各 lane/session 自己的 stages 才是實際顯示的，見 session_view）
        "stages": [{"id": s["id"], "title": s["title"], "agent": s.get("agent"), "gate": s.get("gate"), "order": s.get("order", 0), "notes": s.get("notes")}
                   for s in st_svc.pipeline_for_workflow(cfg, "spec-to-testcase")["stages"]],
        "pipelines": [{"id": p["id"], "title": p["title"], "description": p.get("description"), "workflow_ids": p.get("workflow_ids") or []} for p in st_svc.all_pipelines(cfg)],
        "focus": focus,
        "sessions": views,
        "live_count": sum(1 for v in visible if v["health"]["state"] in ("live", "stalled") and v["run_status"] in ACTIVE_RUN_STATUSES),
        "events_files": [str(p.name) for p in ev_svc.files()],
    }


def signature() -> tuple:
    return (ev_svc.signature(), run_svc.signature())


def session_detail(session_id: str) -> dict | None:
    cfg = st_svc.load()
    sessions = ev_svc.sessions()
    s = sessions.get(session_id)
    if not s:
        return None
    rows = _session_rows()
    v = session_view(cfg, s, rows, run_svc.all_runs(), time.time(), with_timeline=True)
    v["events"] = [{k: e[k] for k in ("ts", "event", "agent_id", "agent_type", "subagent_name", "tool_name", "file_path", "reason") if k in e}
                   for e in ev_svc.all_events() if e["session_id"] == session_id and e["event"] != "Stop"][-200:]
    return v
