from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from ..services import reports as svc

router = APIRouter(prefix="/api/reports", tags=["reports"])


class ReportIn(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    summary: str = ""
    body_md: str = ""
    output_paths: list[str] = []


class ReportPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    summary: str | None = None
    body_md: str | None = None
    output_paths: list[str] | None = None


class TemplateIn(BaseModel):
    output_paths: list[str]


class PreviewIn(BaseModel):
    body_md: str


@router.get("")
def list_reports(q: str = "", kind: str = "", page: int = 1, page_size: int = 20, sort: str = "updated_at", desc: bool = True):
    rs = svc.list_all()
    ql = q.strip().lower()
    if kind:
        rs = [r for r in rs if r["kind"] == kind]
    if ql:
        rs = [r for r in rs if ql in f"{r['title']} {r['summary']} {r.get('source_key') or ''} {' '.join(r['output_paths'])}".lower()]
    key = sort if sort in ("updated_at", "created_at", "id", "title", "kind") else "updated_at"
    rs.sort(key=lambda r: (r.get(key) is None, r.get(key)), reverse=desc)
    total = len(rs)
    page = max(1, page); page_size = max(1, min(100, page_size))
    start = (page - 1) * page_size
    return {"items": rs[start:start + page_size], "total": total, "page": page, "page_size": page_size,
            "counts": {"all": len(svc.list_all()), **{k: sum(1 for r in svc.list_all() if r["kind"] == k) for k in ("output", "automation", "manual")}}}


@router.post("", status_code=201)
def create_report(body: ReportIn):
    return svc.create(body.title, body.summary, body.body_md, body.output_paths)


@router.post("/template")
def make_template(body: TemplateIn):
    return {"body_md": svc.template(body.output_paths)}


@router.post("/preview")
def preview(body: PreviewIn):
    return {"html": svc.render_html(body.body_md)}


@router.get("/{report_id}")
def get_report(report_id: int):
    return svc.get(report_id)


@router.patch("/{report_id}")
def patch_report(report_id: int, body: ReportPatch):
    return svc.update(report_id, body.model_dump(exclude_unset=True))


@router.delete("/{report_id}", status_code=204)
def delete_report(report_id: int):
    svc.delete(report_id)


@router.post("/{report_id}/regenerate")
def regenerate(report_id: int):
    return svc.regenerate(report_id)


@router.get("/{report_id}/export")
def export_report(report_id: int, format: str = "md"):
    if format == "md":
        name, text = svc.export_md(report_id)
        media = "text/markdown; charset=utf-8"
    elif format == "html":
        name, text = svc.export_html(report_id)
        media = "text/html; charset=utf-8"
    else:
        raise HTTPException(400, "format 必須是 md 或 html")
    return Response(text, media_type=media, headers={"Content-Disposition": f'attachment; filename="{name}"'})
