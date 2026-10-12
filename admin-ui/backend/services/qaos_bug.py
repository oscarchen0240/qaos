"""M7b：測試執行的 NG → 送 QAOS 開 bug；Pass（可選）→ 匯進 QAOS executions。

寫 QAOS 的動作全部透過 QAOS 自己的 CLI（不改 QAOS 程式），路徑清單（2026-09-18 Oscar 確認）：
  1) bin/qaos evidence add   → evidence/testrun-<回合>/EVD-*.{ext,yaml}、testcases/registry/_counters.yaml、runs/_audit.log
  2) bin/qaos execution import → executions/YYYY-MM/EXE-*.yaml、_counters.yaml、runs/_audit.log
  3) bin/qaos run new spec-to-bug → runs/RUN-*/run.yaml + audit.log、_counters.yaml、runs/_audit.log
之後寫 .warroom/handoff.jsonl（resume_agent），relay 讓 QA session 接手 Bug Analyst／Validator；OPEN_BUG 核准單再回單據頁。
平台自己只寫 admin-ui/data/admin.db（把 EVD／EXE／RUN 編號記回該筆結果）。
"""
from __future__ import annotations

import json
import re
import sqlite3

import yaml

from .. import db
from ..config import DATA_DIR, PROJECT_ROOT
from . import qaos_exec, testruns
from . import tickets as tk

VER_DIR = PROJECT_ROOT / "testcases" / "versions"
MODES = ("bug", "execution")
# QAOS 的流水號是 :03d（最小寬度），單日第 1000 筆起是四位數；尾端要有界線，不能截成前三位
EVD_RE = re.compile(r"\bEVD-\d+\b")
EXE_RE = re.compile(r"\bEXE-\d{8}-\d{3,}\b")
RUN_RE = re.compile(r"\bRUN-\d{8}-\d{3,}\b")
LOG_FIELD_MAX = 2000


class BugFileError(Exception):
    def __init__(self, status: int, msg: str):
        super().__init__(msg)
        self.status = status


def _tc_meta(tc_id: str, version: int | None) -> dict:
    """從 testcases/versions 讀 spec_id / spec_version（唯讀）。沒有版本號就取 registry 目前 active 版。"""
    if not version:
        from . import registry
        ptr = registry.active_index(tc_id.split("-")[1] if tc_id.count("-") >= 2 else None).get(tc_id)
        version = int(ptr["active_version"]) if ptr else None
    if not version:
        return {}
    p = VER_DIR / tc_id / f"v{version}.yaml"
    if not p.exists():
        return {}
    try:
        d = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001
        return {}
    return {"spec_id": d.get("spec_id"), "spec_version": str(d.get("spec_version")) if d.get("spec_version") is not None else None, "version": version}


def _result(run_id: int, result_id: int) -> tuple[dict, dict]:
    run = testruns.get_run(run_id)
    if not run:
        raise BugFileError(404, "回合不存在")
    r = next((x for x in run["results"] if x["id"] == result_id), None)
    if not r:
        raise BugFileError(404, "結果不存在")
    return run, r


_cmd = tk.cmdline
_opt = tk.opt


def _execution_argv(run: dict, r: dict, meta: dict, who: str) -> list[str]:
    """execution import 的 argv（不含 --evidence）。預覽與實際執行共用；證據編號由呼叫端以 argv 元素追加，
    不對含使用者文字的整條指令做字串替換。"""
    parts = ["bin/qaos", "execution", "import", *_opt("--testcase-id", r["testcase_id"]), *_opt("--result", r["result"]), "--executor-type", "human",
             *_opt("--environment", run.get("environment") or ""), *_opt("--by", who)]
    if meta.get("version"): parts += _opt("--testcase-version", meta["version"])
    if run.get("build"): parts += _opt("--build", run["build"])
    if r.get("executed_at"): parts += _opt("--executed-at", r["executed_at"])
    if (r.get("actual_result") or "").strip(): parts += _opt("--actual-result", r["actual_result"].strip())
    if (r.get("notes") or "").strip(): parts += _opt("--notes", r["notes"].strip())
    return parts


def _same_import_elsewhere(r: dict, request: str) -> dict | None:
    """暫時擋法（R02，第 3 批 --request-key 上線後移除）：execution import 的請求內容沒有 admin 結果的身分，
    兩筆結果送出完全相同的 argv 時，CLI 會把第二次當成同一請求的重送、回傳第一筆的 EXE。

    比對的是「當時實際送出的指令」（匯入成功時存進 qaos_import_request）與這次要送的指令，兩邊都用同一個 argv builder 組出
    （有效 TC 版本、操作者等都已解析），不從可修改的回合／結果欄位回推過去的請求。
    限制：只比對平台自己匯入過、且有存請求的結果；QA session 在終端機匯入的同參數紀錄擋不到。"""
    if r.get("evidence"):
        return None                      # 有證據時 --evidence 帶的是新登記的 EVD，請求內容必然不同
    with db.connect() as con:
        return db.one(con.execute("SELECT id, run_id, qaos_execution_id FROM test_results WHERE qaos_import_request=? AND id<>? AND qaos_execution_id IS NOT NULL",
                                  (request, r["id"])))


def _evidence_mismatch(r: dict) -> str | None:
    """R03：EXE 還沒成功、但 EVD 已經登記過（例如 execution import 失敗後重試）時，目前的證據清單必須和當初登記的一致；
    登記過的證據無法從 QAOS 撤回，清單變了卻沿用舊的 EVD，送出去的 execution／bug 會對不上平台上看到的證據。"""
    ids = r.get("qaos_evidence_ids") or []
    if not ids or r.get("qaos_execution_id"):
        return None
    cur = testruns.evidence_signature(r.get("evidence") or [])
    snap = r.get("qaos_evidence_snapshot") or []
    same = (snap == cur) if snap else len(cur) == len(ids)       # 舊資料沒有快照，只能比數量
    if same:
        return None
    return (f"證據已登記到 QAOS（{'、'.join(ids)}），但目前的證據清單和當初登記時不一致；已登記的證據無法撤回，沿用會讓 QAOS 與平台對不上。"
            "請把清單還原成當初登記的內容，或在回合裡重開一筆")


def _has_filing_record(run_id: int, result_id: int) -> bool:
    with db.connect() as con:
        return con.execute("SELECT 1 FROM ticket_executions WHERE ticket_id=? AND kind IN ('execution_import','bug_filing')", (f"TESTRUN-{run_id}/{result_id}",)).fetchone() is not None


def plan(run_id: int, result_id: int, mode: str = "bug") -> dict:
    """組出要跑的指令與預檢警告，不執行。mode=bug（Fail → 開 bug）或 execution（只匯 execution，給 Pass 用）。"""
    if mode not in MODES:
        raise BugFileError(400, f"mode 必須是 {'／'.join(MODES)}")
    run, r = _result(run_id, result_id)
    who = tk.operator()
    summary = {k: r.get(k) for k in ("id", "testcase_id", "testcase_version", "result", "actual_result", "bug_run_id", "qaos_execution_id")}
    if mode == "bug" and r.get("bug_run_id") and not r.get("bug_handoff_id"):
        # R04：run 已經開了、交接或執行紀錄沒補齊：重試只補這兩樣，不重跑任何 CLI
        return {"mode": mode, "steps": [{"kind": "handoff", "label": f"補做交接與執行紀錄（{r['bug_run_id']} 已開，不會重開）", "command": r.get("bug_run_command") or ""}],
                "warnings": [], "writes": [".warroom/handoff.jsonl（平台）"], "meta": {}, "operator": who, "pending_handoff": True, "pending_record": False, "result": summary}
    if mode == "execution" and r.get("qaos_execution_id") and not _has_filing_record(run_id, result_id):
        # 已匯入 QAOS、但平台的執行紀錄沒寫成（例如 DB 暫時鎖住）：重試只補紀錄，不重跑 CLI
        return {"mode": mode, "steps": [{"kind": "record", "label": f"補做執行紀錄（{r['qaos_execution_id']} 已匯入，不會重匯）", "command": r.get("qaos_import_request") or ""}],
                "warnings": [], "writes": [], "meta": {}, "operator": who, "pending_handoff": False, "pending_record": True, "result": summary}
    warnings: list[str] = []
    if mode == "bug":
        if r["result"] != "fail":
            warnings.append("只有 Fail 的結果可以送 QAOS 開 bug")
        if r.get("bug_run_id"):
            warnings.append(f"這條已經送過：{r['bug_run_id']}")
        if not (r.get("actual_result") or "").strip():
            warnings.append("請先填「實際結果」（QAOS 的 Bug Analyst 需要它）")
        if not r.get("evidence"):
            warnings.append("至少要附一份證據（QAOS：No Evidence, No Formal Bug）")
    else:
        if r["result"] == "untested":
            warnings.append("未測的結果不匯入")
        if r.get("qaos_execution_id"):
            warnings.append(f"這條已經匯過：{r['qaos_execution_id']}")
    mismatch = _evidence_mismatch(r)
    if mismatch:
        warnings.append(mismatch)
    meta = _tc_meta(r["testcase_id"], r.get("testcase_version"))
    if not meta.get("spec_id") or not meta.get("spec_version"):
        warnings.append(f"找不到 {r['testcase_id']} 的 spec 版本（testcases/versions/{r['testcase_id']}/v{r.get('testcase_version') or '?'}.yaml）")
    env = run.get("environment") or ""
    if not env:
        warnings.append("回合沒有填「環境」（execution import 的 --environment 必填）")
    owner = f"testrun-{run_id}"
    steps: list[dict] = []
    for e in r.get("evidence") or []:
        path = DATA_DIR / e["stored"]
        if not path.exists():
            warnings.append(f"證據檔不存在：{e['filename']}")
        steps.append({"kind": "evidence", "label": f"登記證據 {e['filename']}", "command": _cmd(["bin/qaos", "evidence", "add", *_opt("--type", e["type"]), *_opt("--file", str(path)), *_opt("--owner", owner),
                                                                                              *_opt("--description", e.get("description") or e["filename"]), *_opt("--captured-at", e["added_at"]), *_opt("--by", who)])})
    if not r.get("qaos_execution_id"):
        dup = _same_import_elsewhere(r, _cmd(_execution_argv(run, r, meta, who)))
        if dup:
            warnings.append(f"另一筆結果（回合 #{dup['run_id']}）已用完全相同的內容匯入為 {dup['qaos_execution_id']}；QAOS 會把這次當成同一筆重送、不會新增 execution。"
                            "請補一段備註或實際結果，讓兩筆內容不同後再送")
    steps.append({"kind": "execution", "label": "匯入執行紀錄（--evidence 會在證據登記後帶入）", "command": _cmd(_execution_argv(run, r, meta, who)) + (" --evidence <EVD…>" if r.get("evidence") else "")})
    if mode == "bug":
        bug_parts = ["bin/qaos", "run", "new", "spec-to-bug", *_opt("--input", f"spec_id={meta.get('spec_id')}"), *_opt("--input", f"spec_version={meta.get('spec_version')}"),
                     *_opt("--input", f"testcase_id={r['testcase_id']}"), *_opt("--input", f"testcase_version={meta.get('version')}"), *_opt("--by", who)]
        steps.append({"kind": "run", "label": "開 spec-to-bug run（execution_id／evidence_ids 由前兩步帶入）", "command": _cmd(bug_parts) + " --input execution_id=<EXE> --input 'evidence_ids=[…]'"})
    writes = ["evidence/testrun-%d/EVD-*.{ext,yaml}" % run_id, "executions/YYYY-MM/EXE-*.yaml", "testcases/registry/_counters.yaml", "runs/_audit.log"]
    if mode == "bug":
        writes += ["runs/RUN-*/run.yaml（新 spec-to-bug run）", ".warroom/handoff.jsonl（平台）"]
    return {"mode": mode, "steps": steps, "warnings": warnings, "writes": writes, "meta": meta, "operator": who, "pending_handoff": False, "pending_record": False, "result": summary}


def _target_session() -> str | None:
    """交接給哪個 QA session：pipeline 目前的 focus（追蹤中／建議的、未忽略、活著）。新 run 沒有活動，無法用 related_runs 歸屬。"""
    try:
        from . import pipeline
        snap = pipeline.snapshot()
        f = snap.get("focus")
        if f and not f.get("ignored") and f["health"]["state"] in ("live", "stalled"):
            return f["session_id"]
        for v in snap.get("sessions", []):
            if not v.get("ignored") and v["health"]["state"] in ("live", "stalled"):
                return v["session_id"]
    except Exception:  # noqa: BLE001
        return None
    return None


def _run_or_raise(cmd: str, what: str, log: list[dict]) -> str:
    try:
        res = qaos_exec._run(cmd)
    except qaos_exec.ExecError as e:      # 例如 PROJECT_ROOT 是 git worktree → 拒絕執行
        raise BugFileError(e.status, str(e)) from e
    log.append({"what": what, **res})
    if res.get("timed_out"):
        raise BugFileError(502, f"{what} 逾時，結果不確定（QAOS 可能已完成部分或全部動作）。請先對帳（{qaos_exec.RECONCILE}）再決定是否重試；"
                                f"已取得的輸出：{((res['stderr'] or '') + (res['stdout'] or ''))[-300:]}")
    if res["exit_code"] != 0:
        raise BugFileError(502, f"{what} 失敗（exit {res['exit_code']}）：{(res['stderr'] or res['stdout'])[-300:]}")
    return res["stdout"].strip()


def execute(run_id: int, result_id: int, mode: str = "bug") -> dict:
    if mode not in MODES:
        raise BugFileError(400, f"mode 必須是 {'／'.join(MODES)}")
    if not qaos_exec._lock.acquire(blocking=False):
        raise BugFileError(409, "另一條 bin/qaos 正在執行，稍後再試")
    log: list[dict] = []
    started = db.now()
    try:
        # sending：送出期間這筆結果不能被改（證據、結果），標記後的屏障保證接下來讀到的是定案內容（R03）
        with testruns.sending(result_id):
            # 預檢與讀結果都在鎖內（同 qaos_exec.execute）：鎖外讀到的舊快照會讓後到的請求看不到前一個請求剛存的編號，重複交接
            p = plan(run_id, result_id, mode)
            if p["warnings"]:
                raise BugFileError(409, "；".join(p["warnings"]))
            run, r = _result(run_id, result_id)
            who = p["operator"]; meta = p["meta"]
            bug_run = None; bug_cmd = ""
            if p["pending_record"]:
                # 只補執行紀錄：沒有這次的 CLI 紀錄，留下當初匯入的請求與 EXE 編號
                evd_ids = list(r.get("qaos_evidence_ids") or []); exe_id = r["qaos_execution_id"]
                log.append({"what": "匯入執行紀錄（補做紀錄）", "command": r.get("qaos_import_request") or "", "exit_code": 0, "stdout": exe_id, "stderr": ""})
                hint = f"已匯入 QAOS：{exe_id}，這次補做執行紀錄。"
            elif p["pending_handoff"]:
                # R04：run 已開、交接未補齊。只補後段，不重跑任何 CLI
                evd_ids = list(r.get("qaos_evidence_ids") or []); exe_id = r.get("qaos_execution_id")
                bug_run = r["bug_run_id"]; bug_cmd = r.get("bug_run_command") or ""
                hint = f"已開 {bug_run}（spec-to-bug），這次補做交接與執行紀錄。"
            else:
                evd_ids = list(r.get("qaos_evidence_ids") or [])
                if not evd_ids:
                    for st in [s for s in p["steps"] if s["kind"] == "evidence"]:
                        out = _run_or_raise(st["command"], st["label"], log)
                        m = EVD_RE.search(out)
                        if not m:
                            raise BugFileError(502, f"證據登記沒有回傳 EVD 編號：{out[-200:]}")
                        evd_ids.append(m.group(0))
                    _save(result_id, qaos_evidence_ids=evd_ids, qaos_evidence_snapshot=testruns.evidence_signature(r.get("evidence") or []))
                exe_id = r.get("qaos_execution_id")
                if not exe_id:
                    ex_parts = _execution_argv(run, r, meta, who)
                    for e in evd_ids:
                        ex_parts += _opt("--evidence", e)
                    ex_cmd = _cmd(ex_parts)
                    out = _run_or_raise(ex_cmd, "匯入執行紀錄", log)
                    m = EXE_RE.search(out)
                    if not m:
                        raise BugFileError(502, f"execution import 沒有回傳 EXE 編號：{out[-200:]}")
                    exe_id = m.group(0)
                    _save(result_id, qaos_execution_id=exe_id, qaos_import_request=ex_cmd)
                hint = f"已匯入 QAOS：{exe_id}"
                if mode == "bug":
                    bug_cmd = _cmd(["bin/qaos", "run", "new", "spec-to-bug", *_opt("--input", f"spec_id={meta['spec_id']}"), *_opt("--input", f"spec_version={meta['spec_version']}"),
                                    *_opt("--input", f"testcase_id={r['testcase_id']}"), *_opt("--input", f"testcase_version={meta['version']}"),
                                    *_opt("--input", f"execution_id={exe_id}"), *_opt("--input", "evidence_ids=" + json.dumps(evd_ids)), *_opt("--by", who)])
                    out = _run_or_raise(bug_cmd, "開 spec-to-bug run", log)
                    m = RUN_RE.search(out)
                    if not m:
                        raise BugFileError(502, f"run new 沒有回傳 RUN 編號：{out[-200:]}")
                    bug_run = m.group(0)
                    _save(result_id, bug_run_id=bug_run, bug_run_command=bug_cmd)
                    hint = f"已開 {bug_run}（spec-to-bug）。Bug Analyst 的 T1 已 READY，QA session 會由 relay 接續；走到 OPEN_BUG 核准單時會出現在「單據 › 核准」。"
            ended = db.now()
            handoff_id = None
            try:
                if bug_run:
                    handoff_id, hint = _complete_bug_handoff(run_id, result_id, bug_run, bug_cmd, who, hint, started, ended, log)
                else:
                    with db.connect() as con:
                        _insert_filing_row(con, run_id, result_id, mode, log, None, None, hint, started, ended)
            except (OSError, sqlite3.Error) as e:
                raise BugFileError(500, f"QAOS 端已完成（{bug_run or exe_id}），但{'交接或' if bug_run else ''}執行紀錄寫入失敗：{e}。"
                                        "再按一次「送 QAOS」只會補做" + ("交接與紀錄，不會重跑 CLI、不會重開 run。" if bug_run else "執行紀錄，不會重匯。")) from e
    finally:
        qaos_exec._lock.release()
    if run.get("status") in ("done", "aborted"):
        testruns.sync_report(run_id)
    return {"ok": True, "evidence_ids": evd_ids, "execution_id": exe_id, "bug_run_id": bug_run, "handoff_id": handoff_id, "hint": hint, "log": log}


def _insert_filing_row(con, run_id: int, result_id: int, mode: str, log: list[dict], bug_run: str | None, handoff_id: str | None, hint: str, started: str, ended: str):
    con.execute("""INSERT INTO ticket_executions (ticket_id, kind, action, command, exit_code, stdout, stderr, post_json, run_id, run_status_after, next_task, session_id, handoff_id, hint, started_at, ended_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (f"TESTRUN-{run_id}/{result_id}", "bug_filing" if mode == "bug" else "execution_import", mode, "\n".join(x["command"] for x in log), 0,
                 "\n".join(x["stdout"] for x in log)[-4000:], "", json.dumps(_compact_log(log), ensure_ascii=False), bug_run, None, None, None, handoff_id, hint, started, ended))


def _complete_bug_handoff(run_id: int, result_id: int, bug_run: str, bug_cmd: str, who: str, hint: str, started: str, ended: str, log: list[dict]) -> tuple[str, str]:
    """開 bug 之後的後段，每一步都冪等，失敗後重試只會補沒做完的：
    1) 交接寫進 handoff.jsonl（ID 由 bug run 衍生；已經在檔案裡就不再寫）
    2) 執行紀錄（同一個 handoff_id 已有就不再插）
    3) 最後才在結果上記 bug_handoff_id＝交接完成（plan 看這個欄位決定是「已送過」還是「待補交接」）。"""
    from . import runs as run_svc
    run_svc._cache.pop(str(run_svc.RUNS_DIR / bug_run / "run.yaml"), None)
    after = run_svc.get(bug_run)
    cur = next((t for t in (after or {}).get("tasks", []) if t["task_id"] == (after or {}).get("current_task_id")), None)
    sid = _target_session()
    handoff_id = qaos_exec.stable_handoff_id("bug_filing", bug_run)
    qaos_exec.append_handoff_once({
        "kind": "handoff", "id": handoff_id, "ts": ended, "ticket_id": f"TESTRUN-{run_id}/{result_id}", "ticket_kind": "bug_filing", "action": "spec-to-bug",
        "handoff_kind": "resume_agent" if (after and after["status"] == "RUNNING" and cur and cur.get("status") == "READY") else "notify_only",
        "command": bug_cmd, "exit_code": 0, "run_id": bug_run, "run_status_after": after["status"] if after else None,
        "next_task": (after or {}).get("current_task_id"), "next_agent": cur.get("agent_id") if cur else None,
        "session_id": sid, "hint": hint, "by": who,
    })
    if not sid:
        hint += " 找不到活著的 QA session 可交接，請到 QA session 說「繼續 " + bug_run + "」。"
    with db.connect() as con:
        if not con.execute("SELECT 1 FROM ticket_executions WHERE ticket_id=? AND handoff_id=?", (f"TESTRUN-{run_id}/{result_id}", handoff_id)).fetchone():
            if not log:        # 補做：沒有這次的 CLI 紀錄，執行紀錄裡至少留下當初開 run 的指令
                log = [{"what": "開 spec-to-bug run（補做交接）", "command": bug_cmd, "exit_code": 0, "stdout": bug_run, "stderr": ""}]
            _insert_filing_row(con, run_id, result_id, "bug", log, bug_run, handoff_id, hint, started, ended)
    _save(result_id, bug_handoff_id=handoff_id)
    return handoff_id, hint


def import_passes(run_id: int) -> dict:
    """回合 import_all 開著時，結束回合把 pass／blocked／skipped 也匯進 QAOS executions（不開 bug）。"""
    run = testruns.get_run(run_id)
    if not run or not run.get("import_all"):
        return {"imported": 0, "skipped": 0}
    n = 0; skipped = 0; errors = []
    for r in run["results"]:
        if r["result"] in ("untested", "fail") or r.get("qaos_execution_id"):
            skipped += 1; continue
        try:
            execute(run_id, r["id"], mode="execution"); n += 1
        except BugFileError as e:
            errors.append(f"{r['testcase_id']}: {e}")
    return {"imported": n, "skipped": skipped, "errors": errors}


def _compact_log(log: list[dict]) -> list[dict]:
    """先截各欄位再序列化：對序列化後的 JSON 字串切片會切出無法解析的 post_json，執行歷史就讀不出來。"""
    def cut(v):
        return v if not isinstance(v, str) or len(v) <= LOG_FIELD_MAX else v[:LOG_FIELD_MAX // 2] + "\n…（已截斷）…\n" + v[-LOG_FIELD_MAX // 2:]
    return [{k: cut(v) for k, v in x.items()} for x in log]


def _save(result_id: int, **fields):
    sets = {k: (json.dumps(v, ensure_ascii=False) if isinstance(v, list) else v) for k, v in fields.items()}
    sets["updated_at"] = db.now()
    with db.connect() as con:
        cur = con.execute(f"UPDATE test_results SET {', '.join(f'{k}=?' for k in sets)} WHERE id=?", (*sets.values(), result_id))
        if cur.rowcount == 0:
            # 結果在送出途中消失（例如回合被刪）：不能當成儲存成功，否則 QAOS 已執行的步驟會變成沒有任何平台紀錄
            raise BugFileError(409, f"結果 #{result_id} 已不存在（回合可能在送出途中被刪除）；QAOS 端已執行的步驟請用 bin/qaos operation list --incomplete 與 evidence／execution 清單對帳")
