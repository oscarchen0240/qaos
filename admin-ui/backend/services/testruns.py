"""M7 測試執行（TestRail 式）：回合 → 逐條 OK/NG → 證據 → 結束產測試報告。

本檔只動 admin-ui 自己的資料（SQLite、data/evidence/）。送 QAOS 開 bug 的部分在 qaos_bug.py（M7b）。
TC 在建立回合時做快照（版本、標題、步驟、預期），之後 final 重新匯出不會改到這輪的內容。
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import uuid

from .. import db
from ..config import DATA_DIR
from . import outputs as out_svc

EVIDENCE_DIR = DATA_DIR / "evidence"
RESULTS = ("untested", "pass", "fail", "blocked", "skipped")
RUN_STATUS = ("planned", "running", "done", "aborted")
EVIDENCE_TYPES = ("screenshot", "recording", "api_request", "api_response", "log", "console", "db_observation", "execution_result", "other")  # = QAOS schemas/execution/evidence.schema.json 的 type enum
MAX_EVIDENCE_BYTES = 25 * 1024 * 1024


class TestRunError(Exception):
    def __init__(self, status: int, msg: str):
        super().__init__(msg)
        self.status = status


# ---------- 讀 ----------
def _row_run(r: dict) -> dict:
    r["import_all"] = bool(r.get("import_all"))
    return r


def _row_result(r: dict) -> dict:
    for k in ("requirement_ids", "preconditions", "steps", "evidence", "qaos_evidence_ids"):
        try:
            r[k] = json.loads(r.get(k) or "[]")
        except ValueError:
            r[k] = []
    return r


def counts_for(con, run_id: int) -> dict:
    rows = con.execute("SELECT result, COUNT(*) n FROM test_results WHERE run_id=? GROUP BY result", (run_id,)).fetchall()
    c = {k: 0 for k in RESULTS}
    for r in rows:
        c[r["result"]] = r["n"]
    c["total"] = sum(c[k] for k in RESULTS)
    done = c["total"] - c["untested"]
    c["done"] = done
    c["pass_rate"] = round(c["pass"] / c["total"] * 100, 1) if c["total"] else 0.0
    c["progress"] = round(done / c["total"] * 100, 1) if c["total"] else 0.0
    return c


def list_runs() -> list[dict]:
    with db.connect() as con:
        runs = [_row_run(r) for r in db.rows(con.execute("SELECT * FROM test_runs ORDER BY id DESC"))]
        for r in runs:
            r["counts"] = counts_for(con, r["id"])
    return runs


def get_run(run_id: int) -> dict | None:
    with db.connect() as con:
        r = db.one(con.execute("SELECT * FROM test_runs WHERE id=?", (run_id,)))
        if not r:
            return None
        r = _row_run(r)
        r["counts"] = counts_for(con, run_id)
        r["results"] = [_row_result(x) for x in db.rows(con.execute("SELECT * FROM test_results WHERE run_id=? ORDER BY position, id", (run_id,)))]
    return r


# ---------- 建立回合 ----------
def _cases_by_group() -> dict[str, tuple[dict, list[dict]]]:
    """group_key → (group, cases)。只讀 final JSON。"""
    out = {}
    for g in out_svc.scan():
        f = next((x for x in g["files"] if x["kind"] == "json"), None)
        if not f:
            continue
        try:
            c = out_svc.content(f["path"])
        except Exception:  # noqa: BLE001
            continue
        if c.get("kind") == "json":
            out[g["key"]] = (g, c["cases"])
    return out


def create_run(name: str, environment: str, build: str, notes: str, items: list[dict], created_by: str, import_all: bool = False, trigger: str = "manual") -> dict:
    """items: [{group_key, testcase_id}]；從 final JSON 快照 TC 內容。"""
    if not name.strip():
        raise TestRunError(400, "回合名稱必填")
    if not items:
        raise TestRunError(400, "至少要挑一條 TC")
    groups = _cases_by_group()
    snap = []
    missing = []
    seen = set()
    for it in items:
        key = (it.get("group_key"), it.get("testcase_id"))
        if key in seen:
            continue
        seen.add(key)
        g_c = groups.get(it.get("group_key"))
        case = next((c for c in (g_c[1] if g_c else []) if c.get("testcase_id") == it.get("testcase_id")), None)
        if not case:
            missing.append(it.get("testcase_id")); continue
        g = g_c[0]
        specs = (g.get("meta") or {}).get("specs") or []
        snap.append({
            "testcase_id": case["testcase_id"], "testcase_version": case.get("version"), "group_key": g["key"],
            "spec_id": specs[0] if specs else None, "spec_version": None,
            "title": case.get("title") or "", "priority": case.get("priority"), "risk": case.get("risk"),
            "requirement_ids": case.get("requirement_ids") or [], "preconditions": case.get("preconditions") or [],
            "steps": case.get("steps") or [], "expected_result": case.get("expected_result") or "",
        })
    if not snap:
        raise TestRunError(400, f"挑的 TC 在 final JSON 裡找不到：{', '.join(missing[:5])}")
    now = db.now()
    with db.connect() as con:
        cur = con.execute("INSERT INTO test_runs (name, trigger, status, environment, build, notes, created_by, import_all, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                          (name.strip(), trigger, "planned", environment.strip(), build.strip(), notes, created_by, 1 if import_all else 0, now, now))
        rid = cur.lastrowid
        for i, s in enumerate(snap):
            con.execute("""INSERT INTO test_results (run_id, position, testcase_id, testcase_version, group_key, spec_id, spec_version, title, priority, risk, requirement_ids, preconditions, steps, expected_result, result, created_at, updated_at)
                           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,'untested',?,?)""",
                        (rid, i, s["testcase_id"], s["testcase_version"], s["group_key"], s["spec_id"], s["spec_version"], s["title"], s["priority"], s["risk"],
                         json.dumps(s["requirement_ids"], ensure_ascii=False), json.dumps(s["preconditions"], ensure_ascii=False), json.dumps(s["steps"], ensure_ascii=False), s["expected_result"], now, now))
    run = get_run(rid)
    run["missing"] = missing
    return run


def patch_run(run_id: int, fields: dict) -> dict:
    if fields.get("status") is not None:
        # 回合狀態只能經由記結果（planned→running）與 finish（→ done／aborted，同時寫結束時間、產報告、import_all 匯入）改變；
        # 通用 PATCH 改狀態會把已結束的回合重開、留下過期的結束時間與報告，或略過 finish 的流程
        raise TestRunError(400, "回合狀態不能用 PATCH 修改；結束或中止請用 POST /api/testruns/{id}/finish")
    allowed = {"name", "environment", "build", "notes", "import_all"}
    sets = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not sets:
        return get_run(run_id)
    sets["updated_at"] = db.now()
    if "import_all" in sets:
        sets["import_all"] = 1 if sets["import_all"] else 0
    with db.connect() as con:
        con.execute(f"UPDATE test_runs SET {', '.join(f'{k}=?' for k in sets)} WHERE id=?", (*sets.values(), run_id))
    return get_run(run_id)


def delete_run(run_id: int):
    """刪回合連同它的測試報告與證據檔（報告的 source_key 就是 run id，留著會變孤兒）。"""
    with db.connect() as con:
        con.execute("DELETE FROM reports WHERE kind='automation' AND source_key=?", (str(run_id),))
        con.execute("DELETE FROM test_runs WHERE id=?", (run_id,))
    d = EVIDENCE_DIR / str(run_id)
    if d.exists():
        for p in d.iterdir():
            p.unlink(missing_ok=True)
        d.rmdir()


# ---------- 記結果 ----------
def set_result(run_id: int, result_id: int, fields: dict, by: str) -> dict:
    allowed = {"result", "actual_result", "notes", "duration_ms"}
    sets = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if "result" in sets and sets["result"] not in RESULTS:
        raise TestRunError(400, f"result 必須是 {', '.join(RESULTS)}")
    now = db.now()
    with db.connect() as con:
        run = db.one(con.execute("SELECT status FROM test_runs WHERE id=?", (run_id,)))
        if not run:
            raise TestRunError(404, "回合不存在")
        if run["status"] in ("done", "aborted"):
            raise TestRunError(409, "回合已結束，不能再改結果")
        if "result" in sets:
            sets["executed_at"] = now if sets["result"] != "untested" else None
            sets["executed_by"] = by if sets["result"] != "untested" else None
        sets["updated_at"] = now
        con.execute(f"UPDATE test_results SET {', '.join(f'{k}=?' for k in sets)} WHERE id=? AND run_id=?", (*sets.values(), result_id, run_id))
        if run["status"] == "planned":
            con.execute("UPDATE test_runs SET status='running', started_at=COALESCE(started_at, ?), updated_at=? WHERE id=?", (now, now, run_id))
        r = db.one(con.execute("SELECT * FROM test_results WHERE id=? AND run_id=?", (result_id, run_id)))
        if not r:
            raise TestRunError(404, "結果不存在")
        return {"result": _row_result(r), "counts": counts_for(con, run_id)}


# ---------- 證據 ----------
def add_evidence(run_id: int, result_id: int, filename: str, data: bytes, ev_type: str, description: str, by: str) -> dict:
    if ev_type not in EVIDENCE_TYPES:
        raise TestRunError(400, f"type 必須是 {', '.join(EVIDENCE_TYPES)}")
    if len(data) > MAX_EVIDENCE_BYTES:
        raise TestRunError(413, "檔案超過 25MB")
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", filename)[:80] or "file"
    eid = uuid.uuid4().hex[:12]
    d = EVIDENCE_DIR / str(run_id)
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{eid}_{safe}"
    path.write_bytes(data)
    rec = {"id": eid, "filename": filename, "stored": str(path.relative_to(DATA_DIR)), "type": ev_type, "description": description,
           "size": len(data), "sha256": hashlib.sha256(data).hexdigest(), "added_at": db.now(), "added_by": by}
    with db.connect() as con:
        r = db.one(con.execute("SELECT evidence FROM test_results WHERE id=? AND run_id=?", (result_id, run_id)))
        if not r:
            path.unlink(missing_ok=True); raise TestRunError(404, "結果不存在")
        ev = json.loads(r["evidence"] or "[]"); ev.append(rec)
        con.execute("UPDATE test_results SET evidence=?, updated_at=? WHERE id=?", (json.dumps(ev, ensure_ascii=False), db.now(), result_id))
    return rec


def remove_evidence(run_id: int, result_id: int, eid: str):
    with db.connect() as con:
        r = db.one(con.execute("SELECT evidence FROM test_results WHERE id=? AND run_id=?", (result_id, run_id)))
        if not r:
            raise TestRunError(404, "結果不存在")
        ev = json.loads(r["evidence"] or "[]")
        keep = [e for e in ev if e["id"] != eid]
        gone = [e for e in ev if e["id"] == eid]
        con.execute("UPDATE test_results SET evidence=?, updated_at=? WHERE id=?", (json.dumps(keep, ensure_ascii=False), db.now(), result_id))
    for e in gone:
        (DATA_DIR / e["stored"]).unlink(missing_ok=True)


def evidence_path(run_id: int, eid: str) -> pathlib.Path | None:
    d = EVIDENCE_DIR / str(run_id)
    if not d.exists():
        return None
    return next((p for p in d.iterdir() if p.name.startswith(f"{eid}_")), None)


# ---------- 結束回合 → 測試報告 ----------
def finish(run_id: int, status: str = "done") -> dict:
    if status not in ("done", "aborted"):
        raise TestRunError(400, "status 只能是 done 或 aborted")
    now = db.now()
    with db.connect() as con:
        run = db.one(con.execute("SELECT * FROM test_runs WHERE id=?", (run_id,)))
        if not run:
            raise TestRunError(404, "回合不存在")
        con.execute("UPDATE test_runs SET status=?, ended_at=?, started_at=COALESCE(started_at, ?), updated_at=? WHERE id=?", (status, now, now, now, run_id))
    rid = sync_report(run_id)
    with db.connect() as con:
        con.execute("UPDATE test_runs SET report_id=? WHERE id=?", (rid, run_id))
    return get_run(run_id)


def report_md(run: dict) -> str:
    c = run["counts"]
    lines = [f"## 測試回合 #{run['id']} · {run['name']}", "",
             f"- 環境 **{run['environment'] or '—'}** · build **{run['build'] or '—'}** · 執行者 {run['created_by'] or '—'}",
             f"- 開始 {run.get('started_at') or '—'} · 結束 {run.get('ended_at') or '—'} · 狀態 **{run['status']}**",
             "", "| 結果 | 數量 | 比例 |", "|---|---|---|"]
    for k, label in (("pass", "Pass"), ("fail", "Fail"), ("blocked", "Blocked"), ("skipped", "Skipped"), ("untested", "Untested")):
        pct = round(c[k] / c["total"] * 100, 1) if c["total"] else 0
        lines.append(f"| {label} | {c[k]} | {pct}% |")
    lines += [f"| **合計** | **{c['total']}** | 通過率 **{c['pass_rate']}%** |", ""]
    fails = [r for r in run["results"] if r["result"] == "fail"]
    blocked = [r for r in run["results"] if r["result"] == "blocked"]
    if fails:
        lines += ["### NG（Fail）", ""]
        for r in fails:
            lines += [f"- **{r['testcase_id']}** {r['title']}", f"  - 實際結果：{r['actual_result'] or '（未填）'}"]
            if r["notes"]: lines.append(f"  - 備註：{r['notes']}")
            if r["evidence"]: lines.append("  - 證據：" + "、".join(f"{e['filename']}（{e['type']}）" for e in r["evidence"]))
            if r.get("bug_run_id"): lines.append(f"  - 已送 QAOS 開 bug：{r['bug_run_id']}")
        lines.append("")
    if blocked:
        lines += ["### Blocked", ""] + [f"- **{r['testcase_id']}** {r['title']}：{r['actual_result'] or r['notes'] or '—'}" for r in blocked] + [""]
    lines += ["### 逐條結果", "", "| # | TC | 標題 | 優先 | 結果 | 實際結果 |", "|---|---|---|---|---|---|"]
    for i, r in enumerate(run["results"], 1):
        lines.append(f"| {i} | `{r['testcase_id']}` | {r['title']} | {r['priority'] or ''} | {r['result']} | {(r['actual_result'] or '').replace(chr(10), ' ')[:120]} |")
    if run["notes"]:
        lines += ["", "### 回合備註", "", run["notes"]]
    return "\n".join(lines) + "\n"


def sync_report(run_id: int) -> int | None:
    """結束的回合對應一份 kind=automation（介面上叫「測試執行」）的報告；逐條結果變了會重生。"""
    from . import autoreports
    run = get_run(run_id)
    if not run:
        return None
    sig = hashlib.sha1(json.dumps([run["status"], run["ended_at"], [(r["testcase_id"], r["result"], r["actual_result"], len(r["evidence"]), r.get("bug_run_id")) for r in run["results"]]], ensure_ascii=False).encode()).hexdigest()
    c = run["counts"]
    summary = f"{run['name']} · {c['total']} 條 · Pass {c['pass']} / Fail {c['fail']} / Blocked {c['blocked']} · 通過率 {c['pass_rate']}%"
    keys = sorted({r["group_key"] for r in run["results"] if r["group_key"]})
    autoreports.upsert_auto("automation", str(run_id), f"測試回合 #{run_id} {run['name']}", summary, report_md(run), sig, keys)
    with db.connect() as con:
        r = db.one(con.execute("SELECT id FROM reports WHERE kind='automation' AND source_key=?", (str(run_id),)))
    return r["id"] if r else None


def open_count() -> int:
    with db.connect() as con:
        return con.execute("SELECT COUNT(*) FROM test_runs WHERE status IN ('planned','running')").fetchone()[0]
