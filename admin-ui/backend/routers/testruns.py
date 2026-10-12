"""M7 測試執行 API。/api/testruns"""
from typing import Literal

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from ..services import qaos_bug
from ..services import testruns as svc
from ..services import tickets as ticket_svc

router = APIRouter(prefix="/api/testruns", tags=["testruns"])


class ItemIn(BaseModel):
    group_key: str
    testcase_id: str


class RunIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    environment: str = ""
    build: str = ""
    notes: str = ""
    import_all: bool = False
    items: list[ItemIn]


class RunPatch(BaseModel):
    name: str | None = None
    environment: str | None = None
    build: str | None = None
    notes: str | None = None
    status: str | None = None          # 不接受：回合狀態只能經由記結果（planned→running）與 finish 改變；保留欄位是為了回 400 而不是默默忽略
    import_all: bool | None = None


class ResultPatch(BaseModel):
    result: str | None = None
    actual_result: str | None = None
    notes: str | None = None
    duration_ms: int | None = None


class FinishIn(BaseModel):
    status: str = "done"


def _err(e: svc.TestRunError):
    raise HTTPException(e.status, str(e))


@router.get("")
def list_runs():
    return svc.list_runs()


@router.post("", status_code=201)
def create_run(body: RunIn):
    try:
        return svc.create_run(body.name, body.environment, body.build, body.notes, [i.model_dump() for i in body.items], ticket_svc.operator(), body.import_all)
    except svc.TestRunError as e:
        _err(e)


@router.get("/meta")
def meta():
    return {"results": list(svc.RESULTS), "evidence_types": list(svc.EVIDENCE_TYPES), "run_status": list(svc.RUN_STATUS), "max_evidence_bytes": svc.MAX_EVIDENCE_BYTES}


@router.get("/{run_id}")
def get_run(run_id: int):
    r = svc.get_run(run_id)
    if not r:
        raise HTTPException(404, "回合不存在")
    return r


@router.patch("/{run_id}")
def patch_run(run_id: int, body: RunPatch):
    try:
        r = svc.patch_run(run_id, body.model_dump())
    except svc.TestRunError as e:
        _err(e)
    if not r:
        raise HTTPException(404, "回合不存在")
    return r


@router.delete("/{run_id}", status_code=204)
def delete_run(run_id: int):
    try:
        svc.delete_run(run_id)
    except svc.TestRunError as e:
        _err(e)


@router.patch("/{run_id}/results/{result_id}")
def set_result(run_id: int, result_id: int, body: ResultPatch):
    try:
        return svc.set_result(run_id, result_id, body.model_dump(), ticket_svc.operator())
    except svc.TestRunError as e:
        _err(e)


@router.post("/{run_id}/results/{result_id}/evidence", status_code=201)
async def add_evidence(run_id: int, result_id: int, file: UploadFile = File(...), type: str = Form("screenshot"), description: str = Form("")):
    # 分塊讀，超過上限就停：整份 await file.read() 會先把任意大小的上傳讀進記憶體，之後才檢查 25MB
    chunks, size = [], 0
    while chunk := await file.read(1024 * 1024):
        size += len(chunk)
        if size > svc.MAX_EVIDENCE_BYTES:
            await file.close()
            raise HTTPException(413, "檔案超過 25MB")
        chunks.append(chunk)
    data = b"".join(chunks)
    try:
        return svc.add_evidence(run_id, result_id, file.filename or "file", data, type, description, ticket_svc.operator())
    except svc.TestRunError as e:
        _err(e)


@router.delete("/{run_id}/results/{result_id}/evidence/{eid}", status_code=204)
def remove_evidence(run_id: int, result_id: int, eid: str):
    try:
        svc.remove_evidence(run_id, result_id, eid)
    except svc.TestRunError as e:
        _err(e)


@router.get("/{run_id}/evidence/{eid}")
def get_evidence(run_id: int, eid: str):
    p = svc.evidence_path(run_id, eid)
    if not p:
        raise HTTPException(404, "證據不存在")
    return FileResponse(p, filename=p.name.split("_", 1)[-1])


@router.post("/{run_id}/finish")
def finish(run_id: int, body: FinishIn):
    try:
        r = svc.finish(run_id, body.status)
    except svc.TestRunError as e:
        _err(e)
    # import_all：Pass／Blocked／Skipped 也匯進 QAOS executions（不開 bug）
    r["import_result"] = qaos_bug.import_passes(run_id) if r.get("import_all") else None
    return r


# ---- M7b：NG 送 QAOS 開 bug ----
@router.get("/{run_id}/results/{result_id}/bug-plan")
def bug_plan(run_id: int, result_id: int, mode: Literal["bug", "execution"] = "bug"):
    """預覽會跑的 bin/qaos 指令、預檢警告與寫入路徑；不執行。"""
    try:
        return qaos_bug.plan(run_id, result_id, mode)
    except qaos_bug.BugFileError as e:
        raise HTTPException(e.status, str(e))


@router.post("/{run_id}/results/{result_id}/file-bug")
def file_bug(run_id: int, result_id: int, mode: Literal["bug", "execution"] = "bug"):
    """執行：evidence add → execution import → run new spec-to-bug；成功後寫 handoff 交給 QA session。"""
    try:
        return qaos_bug.execute(run_id, result_id, mode)
    except qaos_bug.BugFileError as e:
        raise HTTPException(e.status, str(e))
