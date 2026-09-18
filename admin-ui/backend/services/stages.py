"""讀 admin-ui/config/stages.yaml（mtime 快取）。"""
import yaml

from ..config import STAGES_YAML

_cache: tuple[float, dict] | None = None


def load() -> dict:
    global _cache
    mtime = STAGES_YAML.stat().st_mtime
    if _cache and _cache[0] == mtime:
        return _cache[1]
    cfg = yaml.safe_load(STAGES_YAML.read_text(encoding="utf-8")) or {}
    cfg.setdefault("stages", [])
    cfg.setdefault("stall", {"warn_after_seconds": 600, "dead_after_seconds": 1800})
    cfg.setdefault("session_filter", {})
    cfg.setdefault("lanes", 3)
    cfg["stages"].sort(key=lambda s: s.get("order", 0))
    _cache = (mtime, cfg)
    return cfg


def stage_for_agent_type(cfg: dict, agent_type: str) -> tuple[dict | None, str]:
    """回傳 (stage, signal_strength)；找不到回 (None, '')。"""
    for st in cfg["stages"]:
        for sig in st.get("signals", []):
            if sig.get("source") == "events":
                m = sig.get("match", {})
                if m.get("hook") == "SubagentStart" and m.get("agent_type") == agent_type:
                    return st, sig.get("signal", "weak")
    return None, ""


def stage_for_task(cfg: dict, task_id: str) -> dict | None:
    for st in cfg["stages"]:
        for sig in st.get("signals", []):
            if sig.get("source") == "runtime" and sig.get("match", {}).get("task") == task_id:
                return st
    return None


def stage_for_workflow(cfg: dict, workflow_id: str) -> dict | None:
    for st in cfg["stages"]:
        for sig in st.get("signals", []):
            if sig.get("source") == "runtime" and sig.get("match", {}).get("workflow_id") == workflow_id:
                return st
    return None


def stage_by_id(cfg: dict, stage_id: str) -> dict | None:
    return next((s for s in cfg["stages"] if s["id"] == stage_id), None)
