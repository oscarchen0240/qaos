from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .. import db
from ..services import outputs as out_svc

router = APIRouter(prefix="/api/todos", tags=["todos"])

STATUSES = ("todo", "doing", "done")


class TodoIn(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    status: str = "todo"
    scheduled_date: str | None = None
    due_date: str | None = None
    estimate_min: int | None = Field(default=None, ge=0, le=100000)
    details: str = ""
    linked_output_path: str | None = None
    linked_report_id: int | None = None
    auto_complete: bool = True


class TodoPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    status: str | None = None
    scheduled_date: str | None = None
    due_date: str | None = None
    estimate_min: int | None = Field(default=None, ge=0, le=100000)
    details: str | None = None
    linked_output_path: str | None = None
    linked_report_id: int | None = None
    auto_complete: bool | None = None


class MoveIn(BaseModel):
    status: str
    before_id: int | None = None  # 放到這張卡之前；None = 該欄最後


def _check_status(s: str):
    if s not in STATUSES:
        raise HTTPException(400, f"status 必須是 {STATUSES}")


def _norm_output(v: str | None) -> str | None:
    """linked_output_path 存的是產出群組 key；M1 初版存檔案路徑，讀取時轉成群組。"""
    if v and "/" in v:
        v, _ = out_svc.group_key_of(v.rsplit("/", 1)[-1], v)
    return v


def _enrich(ts: list[dict]) -> list[dict]:
    """附上關聯產出的即時狀態（模組、審閱狀態），讓卡片能跟著產出更新。"""
    keys = {_norm_output(t["linked_output_path"]) for t in ts if t["linked_output_path"]}
    groups = {g["key"]: g for g in out_svc.scan()} if keys else {}
    for t in ts:
        k = _norm_output(t["linked_output_path"])
        t["linked_output_path"] = k
        t["auto_complete"] = bool(t.get("auto_complete", 1))
        g = groups.get(k) if k else None
        t["linked_output"] = ({"key": k, "label": g["label"], "review_status": g["review_status"], "exists": True} if g
                              else {"key": k, "label": k, "review_status": None, "exists": False} if k else None)
    return ts


def sync_auto_complete(con) -> int:
    """關聯產出「已審」→ 自動完成；曾被自動完成的待辦，若產出又變「退回」→ 退回進行中。回傳異動筆數。"""
    ts = _enrich(db.rows(con.execute("SELECT * FROM todos WHERE linked_output_path IS NOT NULL AND auto_complete=1")))
    now = db.now()
    n = 0
    for t in ts:
        lo = t["linked_output"]
        if not lo or not lo["exists"]:
            continue
        if lo["review_status"] == "reviewed" and t["status"] != "done":
            con.execute("UPDATE todos SET status='done', position=?, completed_at=?, auto_completed_at=?, updated_at=? WHERE id=?",
                        (_next_position(con, "done"), now, now, now, t["id"]))
            n += 1
        elif lo["review_status"] == "returned" and t["status"] == "done" and t.get("auto_completed_at"):
            con.execute("UPDATE todos SET status='doing', position=?, completed_at=NULL, auto_completed_at=NULL, updated_at=? WHERE id=?",
                        (_next_position(con, "doing"), now, t["id"]))
            n += 1
    return n


def _get(con, todo_id: int) -> dict:
    t = db.one(con.execute("SELECT * FROM todos WHERE id=?", (todo_id,)))
    if not t:
        raise HTTPException(404, "todo 不存在")
    return _enrich([t])[0]


def _next_position(con, status: str) -> float:
    r = con.execute("SELECT COALESCE(MAX(position),0)+1 AS p FROM todos WHERE status=?", (status,)).fetchone()
    return float(r["p"])


@router.get("")
def list_todos(status: str | None = None):
    with db.connect() as con:
        sync_auto_complete(con)
        if status:
            _check_status(status)
            cur = con.execute("SELECT * FROM todos WHERE status=? ORDER BY position, id", (status,))
        else:
            cur = con.execute("SELECT * FROM todos ORDER BY status, position, id")
        return _enrich(db.rows(cur))


@router.post("", status_code=201)
def create_todo(body: TodoIn):
    _check_status(body.status)
    ts = db.now()
    with db.connect() as con:
        pos = _next_position(con, body.status)
        cur = con.execute(
            """INSERT INTO todos (title,status,scheduled_date,due_date,estimate_min,details,
               linked_output_path,linked_report_id,auto_complete,position,created_at,updated_at,completed_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (body.title, body.status, body.scheduled_date, body.due_date, body.estimate_min, body.details,
             _norm_output(body.linked_output_path), body.linked_report_id, int(body.auto_complete), pos, ts, ts, ts if body.status == "done" else None),
        )
        sync_auto_complete(con)
        return _get(con, cur.lastrowid)


@router.patch("/{todo_id}")
def patch_todo(todo_id: int, body: TodoPatch):
    data = body.model_dump(exclude_unset=True)
    if "linked_output_path" in data:
        data["linked_output_path"] = _norm_output(data["linked_output_path"])
    if "auto_complete" in data and data["auto_complete"] is not None:
        data["auto_complete"] = int(data["auto_complete"])
    with db.connect() as con:
        cur = _get(con, todo_id)
        if "status" in data and data["status"] is not None:
            _check_status(data["status"])
            if data["status"] != cur["status"]:
                data["position"] = _next_position(con, data["status"])
                data["completed_at"] = db.now() if data["status"] == "done" else None
                data["auto_completed_at"] = None  # 手動改狀態就不再視為自動完成
        if not data:
            return cur
        data["updated_at"] = db.now()
        sets = ", ".join(f"{k}=?" for k in data)
        con.execute(f"UPDATE todos SET {sets} WHERE id=?", (*data.values(), todo_id))
        sync_auto_complete(con)
        return _get(con, todo_id)


@router.post("/{todo_id}/move")
def move_todo(todo_id: int, body: MoveIn):
    _check_status(body.status)
    with db.connect() as con:
        cur = _get(con, todo_id)
        siblings = db.rows(con.execute(
            "SELECT id, position FROM todos WHERE status=? AND id<>? ORDER BY position, id", (body.status, todo_id)))
        if body.before_id is None:
            pos = (siblings[-1]["position"] + 1) if siblings else 1.0
        else:
            idx = next((i for i, s in enumerate(siblings) if s["id"] == body.before_id), None)
            if idx is None:
                raise HTTPException(400, "before_id 不在目標欄位")
            after = siblings[idx]["position"]
            before = siblings[idx - 1]["position"] if idx > 0 else after - 1
            pos = (before + after) / 2
        completed_at = cur["completed_at"]
        if body.status != cur["status"]:
            completed_at = db.now() if body.status == "done" else None
        con.execute("UPDATE todos SET status=?, position=?, completed_at=?, auto_completed_at=NULL, updated_at=? WHERE id=?",
                    (body.status, pos, completed_at, db.now(), todo_id))
        return _get(con, todo_id)


@router.delete("/{todo_id}", status_code=204)
def delete_todo(todo_id: int):
    with db.connect() as con:
        _get(con, todo_id)
        con.execute("DELETE FROM todos WHERE id=?", (todo_id,))
