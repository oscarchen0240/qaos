from fastapi import APIRouter, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

from ..services import outputs as svc

router = APIRouter(prefix="/api/outputs", tags=["outputs"])


class ReviewIn(BaseModel):
    key: str
    review_status: str | None = None
    note: str | None = None


class TcReviewIn(BaseModel):
    key: str
    testcase_ids: list[str]
    review_status: str
    reason: str | None = None


class AckIn(BaseModel):
    keys: list[str] | None = None  # None = 全部標為已讀


@router.get("")
def list_groups():
    return svc.scan()


@router.get("/files")
def list_files():
    return svc.scan_files()


@router.get("/content")
def get_content(path: str = Query(...)):
    return svc.content(path)


@router.get("/raw")
def get_raw(path: str = Query(...)):
    p = svc.resolve(path)
    media = "text/html; charset=utf-8" if p.suffix == ".html" else "application/json" if p.suffix == ".json" else "text/plain; charset=utf-8"
    return FileResponse(p, media_type=media)


@router.patch("/review")
def patch_review(body: ReviewIn):
    return svc.set_review(body.key, body.review_status, body.note)


@router.patch("/tc-review")
def patch_tc_review(body: TcReviewIn):
    return svc.set_tc_review(body.key, body.testcase_ids, body.review_status, body.reason)


@router.post("/ack")
def ack(body: AckIn):
    return {"acknowledged": svc.acknowledge(body.keys)}
