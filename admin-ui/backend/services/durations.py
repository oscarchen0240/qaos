"""Pipeline 各節點耗時：由 run.yaml 的 task history 推算（run.yaml 為事實來源，hook 事件不參與）。

QAOS 的時間語意（見 runs/*/run.yaml）：
  PENDING → READY   ：可以開始（advance）
  READY   → RUNNING ：agent 提交產物（first submit）——所以 READY 期間就是 agent 在工作
  RUNNING → DONE / GATE_FAILED ：gate 評估
  GATE_FAILED → READY：退回重做（下一輪迭代）
  approval task：RUNNING → DONE 這段是「等人決定」
每個 stage：elapsed = 第一次 READY → 最後一次 DONE（未完成則到最後一筆紀錄）；
           work = 各輪 READY→RUNNING 之和；gate = RUNNING→DONE/GATE_FAILED 之和；human = approval 的 RUNNING→DONE。
"""
from __future__ import annotations

import datetime as dt
import statistics

from . import runs as run_svc
from . import stages as st_svc

TERMINAL = ("COMPLETED", "CANCELLED", "FAILED")


def _ts(s: str | None) -> float | None:
    if not s:
        return None
    try:
        return dt.datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _task_durations(t: dict, now: float, run_terminal: bool) -> dict:
    hist = [(h.get("to"), _ts(h.get("at"))) for h in t.get("history") or []]
    hist = [(s, at) for s, at in hist if at is not None]
    first_ready = next((at for s, at in hist if s == "READY"), None)
    last = hist[-1] if hist else None
    done_at = next((at for s, at in reversed(hist) if s == "DONE"), None)
    work = gate = human = 0.0
    submits = 0
    prev_state, prev_at = None, None
    for s, at in hist:
        if prev_state == "READY" and s == "RUNNING":
            work += at - prev_at; submits += 1
        elif prev_state == "RUNNING" and s in ("DONE", "GATE_FAILED"):
            if t.get("type") == "approval":
                human += at - prev_at
            else:
                gate += at - prev_at
        prev_state, prev_at = s, at
    # 進行中的 task：把「到現在」算進去
    open_seconds = 0.0
    if not run_terminal and last and last[0] in ("READY", "RUNNING") and t.get("status") in ("READY", "RUNNING"):
        open_seconds = max(0.0, now - last[1])
        if last[0] == "READY":
            work += open_seconds
        elif t.get("type") == "approval":
            human += open_seconds
        else:
            gate += open_seconds
    end = done_at if done_at is not None else (now if open_seconds else (last[1] if last else None))
    elapsed = (end - first_ready) if (first_ready is not None and end is not None) else None
    return {"task_id": t["task_id"], "status": t["status"], "iterations": max(submits, t.get("iteration") or 0),
            "elapsed": elapsed, "work": work, "gate": gate, "human": human, "running": open_seconds > 0,
            "started_at": first_ready, "ended_at": done_at, "no_history": not hist}


def run_durations(run: dict, now: float | None = None) -> dict:
    now = now or dt.datetime.now(dt.timezone.utc).timestamp()
    cfg = st_svc.load()
    pipeline = st_svc.pipeline_for_workflow(cfg, run.get("workflow_id"))
    terminal = run["status"] in TERMINAL
    created = _ts(run.get("created_at"))
    updated = _ts(run.get("updated_at"))
    total = ((updated if terminal else now) - created) if created else None
    stages: dict[str, dict] = {}
    for t in run["tasks"]:
        st = st_svc.stage_for_task(pipeline, t["task_id"])
        if not st:
            continue
        d = _task_durations(t, now, terminal)
        stages[st["id"]] = {**d, "title": st["title"]}
    # 整合／匯出（不是 task）：specflow 證據，只有 Phase 3 run 有
    if run.get("workflow_id") == "spec-to-testcase":
        from . import specflow as sf_svc
        for sid, ev in sf_svc.stage_evidence(run).items():
            if ev.get("status") in ("done", "active") and ev.get("elapsed_seconds") is not None:
                stages[sid] = {"task_id": None, "status": ev["status"].upper(), "iterations": ev.get("revisions", 0), "elapsed": ev["elapsed_seconds"], "work": ev["elapsed_seconds"], "gate": 0, "human": 0,
                               "running": bool(ev.get("elapsed_running")), "title": {"integration": "交叉整合", "final-export": "匯出 final"}[sid], "no_history": False}
    # intake：建立 → 第一個 task READY；summary：最後一個 DONE → run 結束
    firsts = [s["started_at"] for s in stages.values() if s.get("started_at")]
    if created and firsts:
        stages["intake"] = {"task_id": None, "status": "DONE", "iterations": 0, "elapsed": max(0.0, min(firsts) - created), "work": 0, "gate": 0, "human": 0, "running": False, "title": "建立 Run", "no_history": False}
    # 人工等待也可從 run 層 history 的 WAITING_HUMAN 區間算（與 approval task 應一致，取較大者）
    rh = [(h.get("to"), _ts(h.get("at"))) for h in run.get("history") or []]
    wait = 0.0; wstart = None
    for s, at in rh:
        if at is None: continue
        if s == "WAITING_HUMAN": wstart = at
        elif wstart is not None: wait += at - wstart; wstart = None
    if wstart is not None and not terminal: wait += now - wstart
    human_total = max(wait, sum(s["human"] for s in stages.values()))
    from . import specflow as sf_svc
    return {"run_id": run["run_id"], "status": run["status"], "workflow_id": run.get("workflow_id"), "phase": sf_svc.run_phase(run["run_id"]), "spec": f"{run.get('spec_id') or ''}@{run.get('spec_version') or ''}".strip("@"),
            "created_at": run.get("created_at"), "updated_at": run.get("updated_at"), "total": total, "human_total": human_total,
            "agent_total": sum(s["work"] + s["gate"] for s in stages.values()), "stages": stages}


def _stat(vals: list[float], how: str) -> float | None:
    if not vals: return None
    return {"avg": statistics.fmean, "median": statistics.median, "max": max, "min": min, "sum": sum}[how](vals)


def analysis(scope: str = "completed", workflow: str | None = "spec-to-testcase", limit: int = 100) -> dict:
    now = dt.datetime.now(dt.timezone.utc).timestamp()
    runs = run_svc.all_runs()
    if workflow: runs = [r for r in runs if r.get("workflow_id") == workflow]
    if scope == "completed": runs = [r for r in runs if r["status"] == "COMPLETED"]
    elif scope == "terminal": runs = [r for r in runs if r["status"] in TERMINAL]
    runs = sorted(runs, key=lambda r: -(r.get("_created") or 0))[:limit]
    per_run = [run_durations(r, now) for r in runs]
    if workflow:
        cfg = st_svc.load()
        order = [{"id": s["id"], "title": s["title"], "agent": s.get("agent")} for s in st_svc.pipeline_for_workflow(cfg, workflow)["stages"]]
    else:
        # 沒指定單一 workflow（跨 workflow 混算）：大綱用實際出現過的階段，依第一次出現的順序去重
        seen: dict[str, dict] = {}
        for pr in per_run:
            for sid, sd in pr["stages"].items():
                seen.setdefault(sid, {"id": sid, "title": sd["title"], "agent": None})
        order = list(seen.values())
    agg = []
    for s in order:
        rows = [pr["stages"].get(s["id"]) for pr in per_run]
        rows = [x for x in rows if x and x.get("elapsed") is not None and not x.get("no_history")]
        el = [x["elapsed"] for x in rows]
        if not el:
            agg.append({**s, "n": 0}); continue
        worst = max(rows, key=lambda x: x["elapsed"])
        worst_run = next(pr["run_id"] for pr in per_run if pr["stages"].get(s["id"]) is worst)
        agg.append({**s, "n": len(el), "avg": _stat(el, "avg"), "median": _stat(el, "median"), "max": _stat(el, "max"), "min": _stat(el, "min"), "sum": _stat(el, "sum"),
                    "work_avg": _stat([x["work"] for x in rows], "avg"), "gate_avg": _stat([x["gate"] for x in rows], "avg"), "human_avg": _stat([x["human"] for x in rows], "avg"),
                    "iter_avg": _stat([float(x["iterations"]) for x in rows], "avg"), "iter_max": max(x["iterations"] for x in rows), "worst_run": worst_run})
    tot = [pr["total"] for pr in per_run if pr["total"] is not None]
    return {"scope": scope, "workflow": workflow, "runs": per_run, "stages": agg,
            "summary": {"n": len(per_run), "total_avg": _stat(tot, "avg"), "total_median": _stat(tot, "median"), "total_max": _stat(tot, "max"),
                        "human_avg": _stat([pr["human_total"] for pr in per_run], "avg"), "agent_avg": _stat([pr["agent_total"] for pr in per_run], "avg")}}
