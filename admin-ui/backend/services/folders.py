"""資料夾：把 TC（跨模組）歸檔到自訂名稱的資料夾。純管理系統資料，不動 testcases/。"""
from fastapi import HTTPException

from .. import db


def _folder(con, fid: int) -> dict:
    f = db.one(con.execute("SELECT * FROM folders WHERE id=?", (fid,)))
    if not f:
        raise HTTPException(404, "資料夾不存在")
    return f


def list_all() -> list[dict]:
    with db.connect() as con:
        fs = db.rows(con.execute("SELECT * FROM folders ORDER BY name"))
        for f in fs:
            f["items"] = db.rows(con.execute("SELECT group_key, testcase_id, added_at FROM folder_items WHERE folder_id=? ORDER BY group_key, testcase_id", (f["id"],)))
            f["count"] = len(f["items"])
        return fs


def create(name: str, description: str = "") -> dict:
    name = name.strip()
    if not name:
        raise HTTPException(400, "資料夾名稱必填")
    now = db.now()
    with db.connect() as con:
        if db.one(con.execute("SELECT id FROM folders WHERE name=?", (name,))):
            raise HTTPException(409, "已有同名資料夾")
        c = con.execute("INSERT INTO folders (name, description, created_at, updated_at) VALUES (?,?,?,?)", (name, description, now, now))
        fid = c.lastrowid
    return next(f for f in list_all() if f["id"] == fid)


def rename(fid: int, name: str | None, description: str | None) -> dict:
    with db.connect() as con:
        _folder(con, fid)
        if name is not None:
            con.execute("UPDATE folders SET name=?, updated_at=? WHERE id=?", (name.strip(), db.now(), fid))
        if description is not None:
            con.execute("UPDATE folders SET description=?, updated_at=? WHERE id=?", (description, db.now(), fid))
    return next(f for f in list_all() if f["id"] == fid)


def delete(fid: int):
    with db.connect() as con:
        _folder(con, fid)
        con.execute("DELETE FROM folders WHERE id=?", (fid,))


def add_items(fid: int, items: list[dict]) -> dict:
    now = db.now()
    with db.connect() as con:
        _folder(con, fid)
        for it in items:
            con.execute("INSERT OR IGNORE INTO folder_items (folder_id, group_key, testcase_id, added_at) VALUES (?,?,?,?)",
                        (fid, it["group_key"], it["testcase_id"], now))
        con.execute("UPDATE folders SET updated_at=? WHERE id=?", (now, fid))
    return next(f for f in list_all() if f["id"] == fid)


def remove_items(fid: int, items: list[dict]) -> dict:
    with db.connect() as con:
        _folder(con, fid)
        for it in items:
            con.execute("DELETE FROM folder_items WHERE folder_id=? AND group_key=? AND testcase_id=?", (fid, it["group_key"], it["testcase_id"]))
        con.execute("UPDATE folders SET updated_at=? WHERE id=?", (db.now(), fid))
    return next(f for f in list_all() if f["id"] == fid)


def membership(group_key: str) -> dict[str, list[dict]]:
    """{testcase_id: [{id, name}]} 這個模組的 TC 各自在哪些資料夾。"""
    with db.connect() as con:
        rows = db.rows(con.execute("SELECT fi.testcase_id, f.id, f.name FROM folder_items fi JOIN folders f ON f.id=fi.folder_id WHERE fi.group_key=?", (group_key,)))
    out: dict[str, list[dict]] = {}
    for r in rows:
        out.setdefault(r["testcase_id"], []).append({"id": r["id"], "name": r["name"]})
    return out
