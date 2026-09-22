"""讀 admin-ui/config/stages.yaml（mtime 快取）。

2026-09-22 起支援多 workflow：cfg["pipelines"] 是一個列表，每個 pipeline 有自己的 workflow_ids
與 stages 大綱，忠實對應 workflows/<id>.yaml 的真實 task 圖（不同 workflow 的 task_id 即使都叫
"T1"，語意也不同，不能共用同一套大綱）。呼叫端一律先用 pipeline_for_workflow() 拿到正確的
pipeline，再對它的 stages 做比對。
"""
import yaml

from ..config import STAGES_YAML

_cache: tuple[float, dict] | None = None

_FALLBACK_PIPELINE = {
    "id": "unknown", "workflow_ids": [], "title": "未知流程", "description": "沒有對應的階段大綱定義，只顯示建立與結束。",
    "stages": [
        {"id": "intake", "order": 0, "title": "建立 Run", "agent": "agent-supervisor", "signals": [{"source": "runtime", "match": {"run_created": True}, "signal": "strong"}]},
        {"id": "summary", "order": 1, "title": "結案", "agent": "agent-supervisor", "signals": []},
    ],
}


def load() -> dict:
    global _cache
    mtime = STAGES_YAML.stat().st_mtime
    if _cache and _cache[0] == mtime:
        return _cache[1]
    cfg = yaml.safe_load(STAGES_YAML.read_text(encoding="utf-8")) or {}
    cfg.setdefault("pipelines", [])
    cfg.setdefault("stall", {"warn_after_seconds": 600, "dead_after_seconds": 1800})
    cfg.setdefault("session_filter", {})
    cfg.setdefault("lanes", 3)
    by_workflow: dict[str, dict] = {}
    by_id: dict[str, dict] = {}
    for p in cfg["pipelines"]:
        p.setdefault("stages", [])
        p["stages"].sort(key=lambda s: s.get("order", 0))
        by_id[p["id"]] = p
        for wf in p.get("workflow_ids") or []:
            by_workflow[wf] = p
    cfg["_pipeline_by_workflow"] = by_workflow
    cfg["_pipeline_by_id"] = by_id
    _cache = (mtime, cfg)
    return cfg


def pipeline_for_workflow(cfg: dict, workflow_id: str | None) -> dict:
    """對應 workflow_id 的 pipeline 大綱；沒定義過的 workflow（不該發生，但防呆）回一個最小的 fallback。"""
    return cfg["_pipeline_by_workflow"].get(workflow_id or "", _FALLBACK_PIPELINE)


def pipeline_by_id(cfg: dict, pipeline_id: str) -> dict | None:
    return cfg["_pipeline_by_id"].get(pipeline_id)


def all_pipelines(cfg: dict) -> list[dict]:
    return cfg["pipelines"]


def stage_for_agent_type(pipeline: dict, agent_type: str) -> tuple[dict | None, str]:
    """回傳 (stage, signal_strength)；找不到回 (None, '')。"""
    for st in pipeline["stages"]:
        for sig in st.get("signals", []):
            if sig.get("source") == "events":
                m = sig.get("match", {})
                if m.get("hook") == "SubagentStart" and m.get("agent_type") == agent_type:
                    return st, sig.get("signal", "weak")
    return None, ""


def stage_for_task(pipeline: dict, task_id: str) -> dict | None:
    for st in pipeline["stages"]:
        for sig in st.get("signals", []):
            if sig.get("source") == "runtime" and sig.get("match", {}).get("task") == task_id:
                return st
    return None


def stage_by_id(pipeline: dict, stage_id: str) -> dict | None:
    return next((s for s in pipeline["stages"] if s["id"] == stage_id), None)


def independent_review_stage(pipeline: dict) -> dict | None:
    """這個 pipeline 裡「獨立驗證」性質的 stage（取代舊版寫死的 stage id "validation"）。"""
    return next((s for s in pipeline["stages"] if s.get("independent_review")), None)
