from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..services import tickets as svc
from ..services import qaos_exec

router = APIRouter(prefix="/api/tickets", tags=["tickets"])


class PerItemIn(BaseModel):
    decision: str | None = None
    reason: str | None = None


class DraftIn(BaseModel):
    """extra／per_item 的值會被組進 bin/qaos 的 argv：寫入 DB 前先限定型別（非字串回 422），
    不讓壞草稿先存進去、組指令時才 500。"""
    decision: str | None = None
    option: str | None = None
    rationale: str | None = None
    per_item: dict[str, PerItemIn] | None = None
    extra: dict[str, str] | None = None

    def save(self, ticket_id: str, kind: str) -> dict:
        per = {k: v.model_dump(exclude_none=True) for k, v in self.per_item.items()} if self.per_item is not None else None
        return svc.save_draft(ticket_id, kind, self.decision, self.option, self.rationale, per, self.extra)


class SentIn(BaseModel):
    command: str


class OperatorIn(BaseModel):
    email: str


@router.get("/counts")
def counts():
    return svc.counts()


@router.get("/operator")
def get_operator():
    return {"email": svc.operator()}


@router.put("/operator")
def put_operator(body: OperatorIn):
    svc.set_operator(body.email)
    return {"email": svc.operator()}


# ---- approvals ----
@router.get("/approvals")
def list_approvals(status: str | None = None):
    return svc.approvals(status)


@router.get("/approvals/{apr_id}")
def get_approval(apr_id: str):
    d = svc.approval_detail(apr_id)
    if not d:
        raise HTTPException(404, "approval 不存在")
    return d


@router.put("/approvals/{apr_id}/draft")
def put_approval_draft(apr_id: str, body: DraftIn):
    if not svc.approval_detail(apr_id):
        raise HTTPException(404, "approval 不存在")
    draft = body.save(apr_id, "approval")
    return {"draft": draft, **svc.approval_command(apr_id, draft)}


@router.get("/approvals/{apr_id}/command")
def approval_command(apr_id: str):
    return svc.approval_command(apr_id, svc.get_draft(apr_id) or {})


# ---- clarifications ----
@router.get("/clarifications")
def list_clarifications(open_only: bool = False):
    return svc.clarifications(open_only)


@router.get("/clarifications/{clr_id}")
def get_clarification(clr_id: str):
    d = svc.clarification_detail(clr_id)
    if not d:
        raise HTTPException(404, "clarification 不存在")
    return d


@router.put("/clarifications/{clr_id}/draft")
def put_clr_draft(clr_id: str, body: DraftIn):
    if not svc.clarification_detail(clr_id):
        raise HTTPException(404, "clarification 不存在")
    draft = body.save(clr_id, "clarification")
    return {"draft": draft, **svc.clarification_command(clr_id, draft)}


# ---- bugs ----
@router.get("/bugs")
def list_bugs():
    return svc.bugs()


@router.get("/bugs/{bug_id}")
def get_bug(bug_id: str):
    d = svc.bug_detail(bug_id)
    if not d:
        raise HTTPException(404, "bug 不存在")
    return d


@router.put("/bugs/{bug_id}/draft")
def put_bug_draft(bug_id: str, body: DraftIn):
    if not svc.bug_detail(bug_id):
        raise HTTPException(404, "bug 不存在")
    draft = body.save(bug_id, "bug")
    return {"draft": draft, **svc.bug_command(bug_id, draft)}


@router.post("/{ticket_id}/sent")
def mark_sent(ticket_id: str, body: SentIn):
    """使用者已把指令貼到 QA session 執行：記錄時間與指令（M5b 會改成平台直接執行）。"""
    svc.mark_sent(ticket_id, body.command)
    return {"ok": True}


# ---- M5b：平台直接執行 ----
@router.post("/{ticket_id}/execute")
def execute(ticket_id: str):
    """用草稿組出的 bin/qaos 指令，由平台在專案根目錄執行（單飛、60s 逾時、執行前預檢）。"""
    try:
        return qaos_exec.execute(ticket_id)
    except qaos_exec.ExecError as e:
        raise HTTPException(e.status, str(e))


@router.get("/{ticket_id}/executions")
def executions(ticket_id: str):
    return qaos_exec.executions(ticket_id)


@router.get("/handoff/recent")
def handoff_recent(n: int = 30):
    """`.warroom/handoff.jsonl` 最近的交接紀錄（含是否已被 QA session 的 relay hook 消費）。"""
    return qaos_exec.handoff_tail(n)
