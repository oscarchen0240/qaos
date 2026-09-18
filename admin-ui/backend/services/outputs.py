"""唯讀掃描 testcases/final/。絕不寫入該目錄；審閱狀態存在 admin-ui 自己的 SQLite。

同一模組（檔名 <AREA>-final*.{json,html}）的檔案視為一個「群組」，共用審閱狀態與備註。
"""
import datetime
import json
import pathlib
import re
from collections import Counter

from fastapi import HTTPException

from .. import db
from ..config import FINAL_DIR, PROJECT_ROOT

NAME_RE = re.compile(r"^(?P<area>[A-Z0-9_]+(?:-\d+)?)-final(?P<suffix>-active)?\.(?P<ext>html|json)$")  # AREA 或 AREA-001
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S | re.I)
TC_ID_RE = re.compile(r"\bTC-[A-Z0-9_]+-\d+\b")
REVIEW_STATUSES = ("pending", "reviewed", "returned")

_meta_cache: dict[str, tuple[float, int, dict]] = {}


def _base_dir() -> pathlib.Path:
    """API 路徑的基底：正常是專案根目錄（→ testcases/final/x.json）；FINAL_DIR 被環境變數指到外面時用其上一層。"""
    try:
        FINAL_DIR.resolve().relative_to(PROJECT_ROOT.resolve())
        return PROJECT_ROOT
    except ValueError:
        return FINAL_DIR.resolve().parent


def rel_of(p: pathlib.Path) -> str:
    return str(p.resolve().relative_to(_base_dir().resolve()))


def _iso(ts: float) -> str:
    return datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def resolve(rel_path: str) -> pathlib.Path:
    """把 API 傳入的相對路徑限制在 testcases/final/ 之內。"""
    p = (_base_dir() / rel_path).resolve()
    try:
        p.relative_to(FINAL_DIR.resolve())
    except ValueError:
        raise HTTPException(400, "path 必須在 testcases/final/ 之內")
    if not p.is_file():
        raise HTTPException(404, "檔案不存在")
    return p


def group_key_of(name: str, rel: str) -> tuple[str, str | None]:
    m = NAME_RE.match(name)
    return (m.group("area"), m.group("area")) if m else (rel, None)


# ---- 中繼資料解析 ----
def _parse_json(p: pathlib.Path) -> dict:
    from . import registry
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        return {"parse_error": str(e)[:200]}
    cases = data if isinstance(data, list) else data.get("testcases") if isinstance(data, dict) else None
    if not isinstance(cases, list):
        return {"parse_error": "不是 TestCase 陣列"}
    cases = [c for c in cases if isinstance(c, dict)]
    specs = sorted({f"{c.get('spec_id')}@{c.get('spec_version')}" for c in cases if c.get("spec_id")})
    updated = [c.get("updated_at") for c in cases if c.get("updated_at")]
    versions = Counter(int(c.get("version", 1)) for c in cases)
    m = NAME_RE.match(p.name)
    return {
        "case_count": len(cases),
        "case_ids": [c.get("testcase_id") for c in cases if c.get("testcase_id")],
        "drift": registry.drift_for_final(cases, m.group("area") if m else None),
        "specs": specs,
        "priority": dict(Counter(c.get("priority") for c in cases)),
        "risk": dict(Counter(c.get("risk") for c in cases)),
        "exploratory": sum(1 for c in cases if c.get("assumptions")),
        "revised": sum(n for v, n in versions.items() if v > 1),
        "latest_case_update": max(updated) if updated else None,
    }


def _parse_html(p: pathlib.Path) -> dict:
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except Exception as e:  # noqa: BLE001
        return {"parse_error": str(e)[:200]}
    m = TITLE_RE.search(text)
    return {"title": m.group(1).strip() if m else None, "case_count": len(set(TC_ID_RE.findall(text))) or None}


def _meta(p: pathlib.Path, st) -> dict:
    from . import registry
    key = str(p)
    cached = _meta_cache.get(key)
    sig = (st.st_mtime, st.st_size, registry.signature())
    if cached and cached[0] == sig:
        return cached[2]
    meta = _parse_json(p) if p.suffix == ".json" else _parse_html(p) if p.suffix == ".html" else {}
    _meta_cache[key] = (sig, None, meta)
    return meta


# ---- 掃描 ----
def scan_files() -> list[dict]:
    """每個檔案一筆，並同步 output_files 追蹤表。"""
    if not FINAL_DIR.exists():
        return []
    files = [(p, p.stat()) for p in sorted(FINAL_DIR.iterdir()) if p.is_file() and not p.name.startswith(".")]
    now = db.now()
    items = []
    with db.connect() as con:
        tracked = {r["output_path"]: r for r in db.rows(con.execute("SELECT * FROM output_files"))}
        for p, st in files:
            rel = rel_of(p)
            gkey, area = group_key_of(p.name, rel)
            t = tracked.get(rel)
            changed = False
            if t is None:
                con.execute("INSERT INTO output_files (output_path, group_key, first_seen_at, last_seen_mtime, last_seen_size, updated_at) VALUES (?,?,?,?,?,?)",
                            (rel, gkey, now, st.st_mtime, st.st_size, now))
                t = {"first_seen_at": now, "acknowledged_at": None}
                changed = True
            elif st.st_mtime > t["last_seen_mtime"] + 1e-6 or st.st_size != t["last_seen_size"]:
                # 檔案被重新產生：視為新版本，重設「已讀」
                con.execute("UPDATE output_files SET last_seen_mtime=?, last_seen_size=?, acknowledged_at=NULL, updated_at=? WHERE output_path=?",
                            (st.st_mtime, st.st_size, now, rel))
                t = {**t, "acknowledged_at": None}
                changed = True
            items.append({
                "path": rel, "name": p.name, "group_key": gkey, "area": area,
                "kind": "json" if p.suffix == ".json" else "html" if p.suffix == ".html" else "other",
                "size": st.st_size, "mtime": st.st_mtime, "modified_at": _iso(st.st_mtime),
                "meta": _meta(p, st),
                "first_seen_at": t["first_seen_at"], "acknowledged_at": t["acknowledged_at"],
                "unread": t["acknowledged_at"] is None, "changed_now": changed,
            })
    return items


def scan() -> list[dict]:
    """群組視圖：同模組的檔案合為一筆，帶共用的審閱狀態。"""
    files = scan_files()
    with db.connect() as con:
        reviews = {r["group_key"]: r for r in db.rows(con.execute("SELECT * FROM output_reviews"))}
        tc_rows = db.rows(con.execute("SELECT group_key, testcase_id, review_status, reason FROM tc_reviews"))
    tc_by_group: dict[str, dict[str, str]] = {}
    reasons: dict[str, dict[str, str]] = {}
    for r in tc_rows:
        tc_by_group.setdefault(r["group_key"], {})[r["testcase_id"]] = r["review_status"]
        if r.get("reason"):
            reasons.setdefault(r["group_key"], {})[r["testcase_id"]] = r["reason"]
    groups: dict[str, dict] = {}
    for f in files:
        g = groups.setdefault(f["group_key"], {"key": f["group_key"], "area": f["area"], "files": []})
        g["files"].append(f)
    out = []
    for g in groups.values():
        fs = g["files"]
        js = next((f for f in fs if f["kind"] == "json" and not f["meta"].get("parse_error")), None)
        html = next((f for f in fs if f["kind"] == "html"), None)
        meta = dict(js["meta"]) if js else {}
        if html and html["meta"].get("title"):
            meta["title"] = html["meta"]["title"]
        if "case_count" not in meta and html:
            meta["case_count"] = html["meta"].get("case_count")
        rv = reviews.get(g["key"]) or {"review_status": "pending", "note": "", "updated_at": None}
        tc_summary = summarize_tcs(meta.get("case_ids") or [], tc_by_group.get(g["key"], {}))
        tc_summary["reasons"] = {t: reasons.get(g["key"], {}).get(t, "") for t in tc_summary["returned"]}
        # 有 TC 清單時模組狀態由 TC 彙總；沒有（純 HTML 或解析失敗）才用模組層手動狀態
        status = tc_summary["derived_status"] if meta.get("case_ids") else rv["review_status"]
        newest = max(fs, key=lambda f: f["mtime"])
        out.append({
            "key": g["key"], "area": g["area"],
            "label": g["area"] or fs[0]["name"],
            "files": fs,
            "kinds": sorted({f["kind"] for f in fs}),
            "size": sum(f["size"] for f in fs),
            "mtime": newest["mtime"], "modified_at": newest["modified_at"],
            "meta": meta,
            "review_status": status, "note": rv["note"], "review_updated_at": rv["updated_at"],
            "tc_summary": tc_summary,
            "unread": any(f["unread"] for f in fs),
            "changed_now": any(f["changed_now"] for f in fs),
        })
    out.sort(key=lambda g: -g["mtime"])
    return out


def summarize_tcs(case_ids: list[str], marks: dict[str, str]) -> dict:
    pending = [i for i in case_ids if marks.get(i, "pending") == "pending"]
    reviewed = [i for i in case_ids if marks.get(i) == "reviewed"]
    returned = [i for i in case_ids if marks.get(i) == "returned"]
    derived = "returned" if returned else ("reviewed" if case_ids and not pending else "pending")
    return {"total": len(case_ids), "pending": pending, "reviewed": len(reviewed), "returned": returned, "derived_status": derived}


def _group(key: str) -> dict:
    g = next((g for g in scan() if g["key"] == key), None)
    if not g:
        raise HTTPException(404, "找不到此產出群組")
    return g


def _check_status(s: str):
    if s not in REVIEW_STATUSES:
        raise HTTPException(400, f"review_status 必須是 {'/'.join(REVIEW_STATUSES)}")


def set_tc_review(key: str, testcase_ids: list[str], review_status: str, reason: str | None = None) -> dict:
    _check_status(review_status)
    g = _group(key)
    known = set(g["meta"].get("case_ids") or [])
    bad = [t for t in testcase_ids if t not in known]
    if bad:
        raise HTTPException(400, f"不在此產出內的 TC：{', '.join(bad[:5])}")
    now = db.now()
    with db.connect() as con:
        for t in testcase_ids:
            if reason is None:
                con.execute("INSERT INTO tc_reviews (group_key, testcase_id, review_status, updated_at) VALUES (?,?,?,?) "
                            "ON CONFLICT(group_key, testcase_id) DO UPDATE SET review_status=excluded.review_status, updated_at=excluded.updated_at",
                            (key, t, review_status, now))
            else:
                con.execute("INSERT INTO tc_reviews (group_key, testcase_id, review_status, reason, updated_at) VALUES (?,?,?,?,?) "
                            "ON CONFLICT(group_key, testcase_id) DO UPDATE SET review_status=excluded.review_status, reason=excluded.reason, updated_at=excluded.updated_at",
                            (key, t, review_status, reason, now))
    return _group(key)


def tc_marks(key: str) -> dict[str, dict]:
    with db.connect() as con:
        return {r["testcase_id"]: {"status": r["review_status"], "reason": r.get("reason") or ""} for r in db.rows(con.execute(
            "SELECT testcase_id, review_status, reason FROM tc_reviews WHERE group_key=?", (key,)))}


def set_review(key: str, review_status: str | None, note: str | None) -> dict:
    """模組層：note 直接存；review_status 若群組有 TC 清單則視為「全部設為」，否則存模組層狀態。"""
    g = _group(key)
    if review_status is not None:
        _check_status(review_status)
        if g["meta"].get("case_ids"):
            set_tc_review(key, g["meta"]["case_ids"], review_status)
    now = db.now()
    with db.connect() as con:
        cur = db.one(con.execute("SELECT * FROM output_reviews WHERE group_key=?", (key,)))
        status = review_status if review_status is not None else (cur["review_status"] if cur else "pending")
        text = note if note is not None else (cur["note"] if cur else "")
        con.execute("INSERT INTO output_reviews (group_key, review_status, note, updated_at) VALUES (?,?,?,?) "
                    "ON CONFLICT(group_key) DO UPDATE SET review_status=excluded.review_status, note=excluded.note, updated_at=excluded.updated_at",
                    (key, status, text, now))
    return _group(key)


def acknowledge(keys: list[str] | None) -> int:
    now = db.now()
    with db.connect() as con:
        if keys is None:
            return con.execute("UPDATE output_files SET acknowledged_at=? WHERE acknowledged_at IS NULL", (now,)).rowcount
        n = 0
        for k in keys:
            n += con.execute("UPDATE output_files SET acknowledged_at=? WHERE group_key=? AND acknowledged_at IS NULL", (now, k)).rowcount
        return n


def content(rel_path: str) -> dict:
    p = resolve(rel_path)
    if p.suffix == ".json":
        data = json.loads(p.read_text(encoding="utf-8"))
        cases = data if isinstance(data, list) else data.get("testcases", [])
        from . import folders as folder_svc
        gkey, _ = group_key_of(p.name, rel_path)
        marks = tc_marks(gkey)
        member = folder_svc.membership(gkey)
        slim = [{
            "folders": member.get(c.get("testcase_id"), []),
            "review_status": marks.get(c.get("testcase_id"), {}).get("status", "pending"),
            "review_reason": marks.get(c.get("testcase_id"), {}).get("reason", ""),
            "testcase_id": c.get("testcase_id"), "title": c.get("title"), "version": c.get("version"),
            "priority": c.get("priority"), "risk": c.get("risk"), "test_level": c.get("test_level"),
            "test_types": c.get("test_types", []), "design_techniques": c.get("design_techniques", []),
            "requirement_ids": c.get("requirement_ids", []), "preconditions": c.get("preconditions", []),
            "steps": c.get("steps", []), "expected_result": c.get("expected_result"),
            "assumptions": c.get("assumptions", []), "status": c.get("status"), "updated_at": c.get("updated_at"),
            "spec_reference": c.get("expected_result_spec_reference"),
        } for c in cases if isinstance(c, dict)]
        return {"kind": "json", "cases": slim}
    if p.suffix == ".html":
        return {"kind": "html", "raw_url": f"/api/outputs/raw?path={rel_path}"}
    return {"kind": "text", "text": p.read_text(encoding="utf-8", errors="replace")[:200_000]}


def counts() -> dict:
    groups = scan()
    return {"total": len(groups), "unread": sum(1 for g in groups if g["unread"])}
