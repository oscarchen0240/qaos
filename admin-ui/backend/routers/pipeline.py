import asyncio
import json

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..services import pipeline as svc
from ..services import durations as dur_svc
from ..services import specflow as sf_svc
from ..services import runs as run_svc

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])

# uvicorn --reload 關機時會等所有連線結束；SSE 長連線必須看到這個旗標自己收掉，否則重載卡死
SHUTTING_DOWN = {"flag": False}


class SessionPatch(BaseModel):
    tracked: bool | None = None
    ignored: bool | None = None
    label: str | None = None


@router.get("/state")
def state(session: str | None = Query(default=None)):
    return svc.snapshot(session)


@router.get("/sessions/{session_id}")
def session_detail(session_id: str):
    v = svc.session_detail(session_id)
    if not v:
        raise HTTPException(404, "session 不存在")
    return v


@router.patch("/sessions/{session_id}")
def patch_session(session_id: str, body: SessionPatch):
    return svc.set_session(session_id, body.tracked, body.ignored, body.label)


@router.get("/runs")
def list_runs():
    phases = sf_svc.build()["run_phase"]
    return [{"phase": phases.get(r["run_id"])} | {k: v for k, v in r.items() if k not in ("tasks", "history") or k == "tasks"} | {"tasks": [{"task_id": t["task_id"], "status": t["status"], "iteration": t["iteration"], "agent_id": t["agent_id"], "type": t["type"]} for t in r["tasks"]]}
            for r in run_svc.all_runs()]


@router.get("/runs/{run_id}")
def get_run(run_id: str):
    r = run_svc.get(run_id)
    if not r:
        raise HTTPException(404, "run 不存在")
    return {**r, "audit": run_svc.audit_tail(run_id)}


@router.get("/stream")
async def stream(session: str | None = Query(default=None)):
    """SSE：事件檔或 run.yaml 有變化就推一份完整快照；每 15 秒心跳。"""
    async def gen():
        last_sig = None
        last_beat = 0.0
        loop = asyncio.get_event_loop()
        born = loop.time()
        yield "retry: 1000\n\n"
        # 連線最多活 20 秒就主動收掉（瀏覽器 EventSource 會自動重連）：避免長連線卡住 uvicorn --reload
        while not SHUTTING_DOWN["flag"] and loop.time() - born < 20:
            sig = await loop.run_in_executor(None, svc.signature)
            now = loop.time()
            if sig != last_sig:
                snap = await loop.run_in_executor(None, svc.snapshot, session)
                yield f"event: state\ndata: {json.dumps(snap, ensure_ascii=False)}\n\n"
                last_sig = sig; last_beat = now
            elif now - last_beat > 8:
                yield "event: ping\ndata: {}\n\n"
                last_beat = now
            await asyncio.sleep(1)
    return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.get("/durations")
def durations(scope: str = Query(default="completed", pattern="^(completed|terminal|all)$"), workflow: str | None = Query(default="spec-to-testcase"), limit: int = Query(default=100, ge=1, le=500)):
    """各節點耗時分析：由 run.yaml task history 推算，每個 run 一列、每個 stage 平均／中位數／最大／最花時間的 run。"""
    return dur_svc.analysis(scope, workflow or None, limit)



@router.get("/specs")
def specs():
    """Spec 進度（匯流圖）：每份 spec 的 Phase 2 run、Phase 3 run、交叉整合證據、final 與 DoD 三項。"""
    return sf_svc.build()
