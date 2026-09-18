"""產出完成 → 自動建立「產出報告」並記錄工作流程（run.yaml / approvals / hook）。

自動化測試（M4）完成後也用同一機制：kind='automation'、source_key=test_runs.id，呼叫 upsert_auto()。
"""
import hashlib
import re
from datetime import datetime, timezone

import yaml

from .. import db
from ..config import PROJECT_ROOT
from . import outputs as out_svc
from . import runs as run_svc
from . import specflow as sf_svc
from . import events as ev_svc

TASK_LABEL = {"T1": "Spec 分析", "T2": "測試設計", "T3": "獨立驗證", "T4": "人工核准", "T5": "結案"}
RUN_LABEL = {"RUNNING": "執行中", "WAITING_HUMAN": "等待核准", "COMPLETED": "已完成", "FAILED": "失敗", "CANCELLED": "已取消", "CREATED": "已建立"}
_apr_cache: dict[str, tuple[float, dict]] = {}


PHASE_LABEL = {"phase2": "**Phase 2** · ", "phase3": "**Phase 3** · ", "revision": "**修訂** · "}


def _area(key: str) -> str:
    m = re.match(r"([A-Z0-9_]+)", key)
    return m.group(1) if m else key


def _approval(apr_id: str) -> dict | None:
    p = PROJECT_ROOT / "approvals" / f"{apr_id}.yaml"
    if not p.exists():
        return None
    st = p.stat()
    c = _apr_cache.get(apr_id)
    if c and c[0] == st.st_mtime:
        return c[1]
    try:
        d = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001
        return None
    _apr_cache[apr_id] = (st.st_mtime, d)
    return d


def _dur(a: str | None, b: str | None) -> str:
    ta, tb = run_svc._ts(a), run_svc._ts(b)
    if not ta or not tb:
        return "—"
    s = int(tb - ta)
    h, m = s // 3600, (s % 3600) // 60
    return f"{h}h {m:02d}m" if h else f"{m}m {s % 60:02d}s"


def runs_for_area(area: str) -> list[dict]:
    """同功能區的 run，新→舊（舊版：只看功能區前綴，BONUSCCY-001/002/003 會混在一起）。"""
    out = [r for r in run_svc.all_runs() if _area((r.get("spec_id") or "").replace("SPEC-", "")) == area or _area((r.get("testcase_id") or "").replace("TC-", "")) == area]
    return out


def runs_for_group(group_key: str) -> list[dict]:
    """產出群組對應的 run：spec-to-testcase 依 spec 編號精確對應（BONUSCCY-002 只認 SPEC-BONUSCCY-002；CASHFLOW 認 SPEC-CASHFLOW-001），
    其他 workflow（修訂、bug、regression）只有功能區可對，依前綴納入。新→舊。"""
    area = _area(group_key)
    out = []
    for r in run_svc.all_runs():
        sid = (r.get("spec_id") or "").replace("SPEC-", "")
        if r.get("workflow_id") == "spec-to-testcase":
            if sf_svc._matches_key(group_key, sid) if sid else False:
                out.append(r)
        elif _area(sid) == area or _area((r.get("testcase_id") or "").replace("TC-", "")) == area:
            out.append(r)
    return out


def main_run(runs: list[dict]) -> dict | None:
    """主 run：這份 spec 的 Phase 3 spec-to-testcase run（整合線的起點）；沒有就取最新完成的 spec-to-testcase，再沒有就最新的 run。"""
    s2t = [r for r in runs if r.get("workflow_id") == "spec-to-testcase"]
    p3 = next((r for r in s2t if sf_svc.run_phase(r["run_id"]) == "phase3"), None)
    if p3:
        return p3
    return next((r for r in s2t if r["status"] == "COMPLETED"), s2t[0] if s2t else (runs[0] if runs else None))


def workflow_md(runs: list[dict]) -> str:
    """把 run.yaml 整理成工作流程紀錄（Markdown）。"""
    if not runs:
        return "_找不到對應的 run（runs/ 內沒有同功能區的 run.yaml）。_\n"
    main = main_run(runs) or runs[0]
    lines = ["## 工作流程紀錄", "",
             f"- **Run**：`{main['run_id']}` · {PHASE_LABEL.get(sf_svc.run_phase(main['run_id']) or '', '')}{main['workflow_id']} · {main.get('spec_id')}@{main.get('spec_version')} · **{RUN_LABEL.get(main['status'], main['status'])}**",
             f"- 建立 {main['created_at']} · 最後更新 {main['updated_at']} · 歷時 {_dur(main['created_at'], main['updated_at'])} · 發起 {main.get('initiated_by') or '—'}",
             "", "| 階段 | 執行者 | 狀態 | 迭代 | 開始 | 結束 | Gate | 最後 gate 結果 |", "|---|---|---|---|---|---|---|---|"]
    for t in main["tasks"]:
        who = "human" if t["type"] == "approval" else (t["agent_id"] or "").replace("agent-", "")
        last_gate = t["gate_results"][-1] if t["gate_results"] else None
        gr = f"{last_gate['layer']} {last_gate['result']}" if last_gate else "—"
        lines.append(f"| {t['task_id']} {TASK_LABEL.get(t['task_id'], '')} | {who} | {t['status']} | {t['iteration'] or 0} | {(t['started_at'] or '—')[5:16]} | {(t['ended_at'] or '—')[5:16]} | {t['gate'] or '—'} | {gr} |")
    # 核准
    aprs = [t.get("approval_id") for t in main["tasks"] if t.get("approval_id")]
    # 也把 audit 裡出現的 APR 抓進來（NEEDS_DECISION / HUMAN_OVERRIDE 不一定掛在 task 上）
    for a in run_svc.audit_tail(main["run_id"], 200):
        for m in re.findall(r"\bAPR-\d{4}\b", a.get("detail", "")):
            if m not in aprs:
                aprs.append(m)
    if aprs:
        lines += ["", "### 核准紀錄", ""]
        for aid in aprs:
            d = _approval(aid)
            if not d:
                lines.append(f"- {aid}"); continue
            dec = d.get("decision") or {}
            lines.append(f"- **{aid}** {d.get('type')} · {d.get('status')}" + (f" → **{dec.get('decision')}**" + (f"（{dec.get('selected_option')}）" if dec.get("selected_option") else "") + f" by {dec.get('decided_by')} at {dec.get('decided_at')}" if dec else "")
                         + (f"\n    - {str(d.get('summary'))[:200]}" if d.get("summary") else "")
                         + (f"\n    - 理由：{str(dec.get('rationale'))[:300]}" if dec and dec.get("rationale") else ""))
    # gate 失敗紀錄
    fails = [(t["task_id"], g) for t in main["tasks"] for g in t["gate_results"] if g["result"] == "FAIL"]
    if fails:
        lines += ["", f"### Gate FAIL（{len(fails)} 次）", ""]
        for tid, g in fails[-8:]:
            lines.append(f"- {g['at'][5:16]} {tid} {g['layer']}：" + "；".join(g["details"][:2])[:220])
    # hook agent 活動
    agents = []
    for s in ev_svc.sessions().values():
        lo, hi = run_svc._ts(main["created_at"]) - 300, (run_svc._ts(main["updated_at"]) or 0) + 300
        for a in s["agents"]:
            if lo <= a["_start"] <= hi:
                agents.append(a)
    if agents:
        lines += ["", f"### Agent 活動（Claude Code hook，{len(agents)} 次派工）", ""]
        for a in sorted(agents, key=lambda a: a["_start"])[:20]:
            lines.append(f"- {a['started_at'][5:16]} → {(a['ended_at'] or '…')[5:16]} · {a['agent_type']}")
    others = [r for r in runs if r["run_id"] != main["run_id"]]
    if others:
        lines += ["", "### 同功能區其他 run", ""] + [f"- `{r['run_id']}` {PHASE_LABEL.get(sf_svc.run_phase(r['run_id']) or '', '')}{r['workflow_id']} · {RUN_LABEL.get(r['status'], r['status'])} · {r['updated_at']}" for r in others[:8]]
    return "\n".join(lines) + "\n"


def output_md(g: dict) -> str:
    m = g["meta"]
    lines = ["## 產出摘要", "", f"- 模組：**{g['label']}** · Spec：{', '.join(m.get('specs') or []) or '—'}",
             "- 檔案：" + "、".join(f"`{f['path']}`（{f['modified_at']}）" for f in g["files"])]
    if m.get("case_count") is not None:
        lines.append(f"- 案例數：{m['case_count']}")
    if m.get("priority"):
        lines.append("- 優先級：" + "、".join(f"{k} {v}" for k, v in m["priority"].items()))
    if m.get("risk"):
        lines.append("- 風險：" + "、".join(f"{k} {v}" for k, v in m["risk"].items()))
    if m.get("exploratory") is not None:
        lines.append(f"- exploratory（含假設，需人工確認）：{m['exploratory']}")
    if m.get("revised"):
        lines.append(f"- 修訂過（v2 以上）：{m['revised']}")
    ts = g.get("tc_summary") or {}
    lines.append(f"- 審閱狀態：**{g['review_status']}**（已審 {ts.get('reviewed', 0)} · 待審 {len(ts.get('pending') or [])} · 退回 {len(ts.get('returned') or [])}）")
    if ts.get("returned"):
        rs = ts.get("reasons") or {}
        lines.append("- 退回：")
        for t in ts["returned"]:
            lines.append(f"    - {t}" + (f"：{rs[t]}" if rs.get(t) else "（未填理由）"))
    if g.get("note"):
        lines.append(f"- 備註：{g['note']}")
    return "\n".join(lines) + "\n"


def _signature(g: dict, runs: list[dict]) -> str:
    h = hashlib.sha1()
    h.update(b"template-v3|")  # 模板或 run 對應規則改了就 bump，讓既有報告重生
    ts = g.get("tc_summary") or {}
    h.update(f"{g['mtime']}|{g['review_status']}|{g.get('note','')}|{ts.get('reviewed')}|{len(ts.get('pending') or [])}|{sorted((ts.get('reasons') or {}).items())}|".encode())
    for r in runs[:3]:
        h.update(f"{r['run_id']}:{sf_svc.run_phase(r['run_id'])}:{r['status']}:{r['updated_at']}|".encode())
    return h.hexdigest()


def upsert_auto(kind: str, source_key: str, title: str, summary: str, auto_md: str, signature: str, output_keys: list[str]) -> bool:
    """建立或更新自動報告。回傳是否有變動。人寫的 body_md 不動。"""
    now = db.now()
    with db.connect() as con:
        cur = db.one(con.execute("SELECT * FROM reports WHERE kind=? AND source_key=?", (kind, source_key)))
        if cur and cur.get("auto_signature") == signature:
            return False
        if cur:
            con.execute("UPDATE reports SET summary=?, auto_md=?, auto_generated_at=?, auto_signature=?, updated_at=? WHERE id=?",
                        (summary, auto_md, now, signature, now, cur["id"]))
            rid = cur["id"]
        else:
            c = con.execute("INSERT INTO reports (title, summary, body_md, kind, source_key, auto_md, auto_generated_at, auto_signature, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                            (title, summary, "", kind, source_key, auto_md, now, signature, now, now))
            rid = c.lastrowid
        con.execute("DELETE FROM report_outputs WHERE report_id=?", (rid,))
        for k in dict.fromkeys(output_keys):
            con.execute("INSERT INTO report_outputs (report_id, output_path) VALUES (?,?)", (rid, k))
    return True


def sync_outputs() -> int:
    """每個產出群組對應一份 kind=output 的報告；產出檔／審閱／run 有變就重生自動段落。回傳異動數。"""
    n = 0
    for g in out_svc.scan():
        runs = runs_for_group(g["key"])
        sig = _signature(g, runs)
        main = main_run(runs)
        summary = f"{g['label']} · {g['meta'].get('case_count') or '?'} 條 TC · 審閱 {g['review_status']}" + (f" · {main['run_id']} {RUN_LABEL.get(main['status'], main['status'])}" if main else "")
        md = output_md(g) + "\n" + workflow_md(runs)
        if upsert_auto("output", g["key"], f"{g['label']} 產出報告", summary, md, sig, [g["key"]]):
            n += 1
    return n
