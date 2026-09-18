"""唯讀讀取 runs/<RUN>/run.yaml（Runtime 的事實來源）。"""
import pathlib
from datetime import datetime, timezone

import yaml

from ..config import PROJECT_ROOT, RUNS_DIR

_cache: dict[str, tuple[float, dict]] = {}
_wf_cache: dict[str, tuple[float, int]] = {}


def max_iterations(workflow_id: str | None) -> int:
    """workflows/<id>.yaml 的 max_validation_iterations；讀不到就當 3。"""
    if not workflow_id:
        return 3
    p = PROJECT_ROOT / "workflows" / f"{workflow_id}.yaml"
    try:
        st = p.stat()
    except OSError:
        return 3
    c = _wf_cache.get(str(p))
    if c and c[0] == st.st_mtime:
        return c[1]
    try:
        n = int((yaml.safe_load(p.read_text(encoding="utf-8")) or {}).get("max_validation_iterations") or 3)
    except Exception:  # noqa: BLE001
        n = 3
    _wf_cache[str(p)] = (st.st_mtime, n)
    return n


def _ts(s: str | None) -> float:
    if not s:
        return 0.0
    try:
        return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()
    except Exception:  # noqa: BLE001
        return 0.0


def _load(p: pathlib.Path) -> dict | None:
    st = p.stat()
    c = _cache.get(str(p))
    if c and c[0] == st.st_mtime:
        return c[1]
    try:
        d = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001
        return None
    tasks = []
    for t in d.get("tasks", []):
        tasks.append({
            "task_id": t.get("task_id"), "type": t.get("type"), "agent_id": t.get("agent_id"), "status": t.get("status"),
            "iteration": t.get("iteration", 0), "gate": t.get("gate"), "mode": t.get("mode"),
            "started_at": t.get("started_at"), "ended_at": t.get("ended_at"), "approval_id": t.get("approval_id"),
            "outputs": len(t.get("output_artifact_ids") or []), "entities": len(t.get("input_entity_refs") or []),
            "history": [{"at": h.get("at"), "from": h.get("from_status"), "to": h.get("to_status"), "trigger": h.get("trigger")} for h in t.get("history") or []],
            "gate_results": [{"at": g.get("at"), "layer": g.get("layer"), "result": g.get("result"), "details": g.get("details") or []} for g in t.get("gate_results") or []],
        })
    inp = d.get("input") or {}
    run = {
        "run_id": d.get("run_id") or p.parent.name, "workflow_id": d.get("workflow_id"), "status": d.get("status"),
        "spec_id": inp.get("spec_id"), "spec_version": inp.get("spec_version"), "testcase_id": inp.get("testcase_id"),
        "initiated_by": d.get("initiated_by"), "created_at": d.get("created_at"), "updated_at": d.get("updated_at"),
        "_created": _ts(d.get("created_at")), "_updated": _ts(d.get("updated_at")),
        "current_task_id": d.get("current_task_id"), "waiting_on_approval_id": d.get("waiting_on_approval_id"),
        "max_iterations": max_iterations(d.get("workflow_id")),
        "tasks": tasks,
        "history": [{"at": h.get("at"), "from": h.get("from_status"), "to": h.get("to_status"), "trigger": h.get("trigger")} for h in d.get("history") or []],
        "file_mtime": st.st_mtime,
    }
    _cache[str(p)] = (st.st_mtime, run)
    return run


def signature() -> tuple:
    if not RUNS_DIR.exists():
        return ()
    return tuple((p.name, (p / "run.yaml").stat().st_mtime) for p in sorted(RUNS_DIR.glob("RUN-*")) if (p / "run.yaml").exists())


def all_runs() -> list[dict]:
    if not RUNS_DIR.exists():
        return []
    out = []
    for p in sorted(RUNS_DIR.glob("RUN-*")):
        f = p / "run.yaml"
        if f.exists():
            r = _load(f)
            if r:
                out.append(r)
    out.sort(key=lambda r: -(r["_updated"] or r["file_mtime"]))
    return out


def get(run_id: str) -> dict | None:
    f = RUNS_DIR / run_id / "run.yaml"
    return _load(f) if f.exists() else None


def audit_tail(run_id: str, n: int = 40) -> list[dict]:
    f = RUNS_DIR / run_id / "audit.log"
    if not f.exists():
        return []
    lines = f.read_text(encoding="utf-8", errors="replace").splitlines()[-n:]
    out = []
    for ln in lines:
        parts = ln.split("\t", 3)
        if len(parts) >= 3:
            out.append({"at": parts[0], "actor": parts[1], "action": parts[2], "detail": parts[3] if len(parts) > 3 else ""})
    return out
