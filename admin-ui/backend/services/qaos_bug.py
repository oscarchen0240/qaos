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
import shlex

import yaml

from .. import db
from ..config import DATA_DIR, PROJECT_ROOT
from . import qaos_exec, testruns
from . import tickets as tk

VER_DIR = PROJECT_ROOT / "testcases" / "versions"


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


def _cmd(parts: list[str]) -> str:
    return " ".join(shlex.quote(x) for x in parts)


def plan(run_id: int, result_id: int, mode: str = "bug") -> dict:
    """組出要跑的指令與預檢警告，不執行。mode=bug（Fail → 開 bug）或 execution（只匯 execution，給 Pass 用）。"""
    run, r = _result(run_id, result_id)
    who = tk.operator()
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
        steps.append({"kind": "evidence", "label": f"登記證據 {e['filename']}", "command": _cmd(["bin/qaos", "evidence", "add", "--type", e["type"], "--file", str(path), "--owner", owner, "--description", e.get("description") or e["filename"], "--captured-at", e["added_at"], "--by", who])})
    ex_parts = ["bin/qaos", "execution", "import", "--testcase-id", r["testcase_id"], "--result", r["result"], "--executor-type", "human", "--environment", env, "--by", who]
    if meta.get("version"): ex_parts += ["--testcase-version", str(meta["version"])]
    if run.get("build"): ex_parts += ["--build", run["build"]]
    if r.get("executed_at"): ex_parts += ["--executed-at", r["executed_at"]]
    if (r.get("actual_result") or "").strip(): ex_parts += ["--actual-result", r["actual_result"].strip()]
    if (r.get("notes") or "").strip(): ex_parts += ["--notes", r["notes"].strip()]
    steps.append({"kind": "execution", "label": "匯入執行紀錄（--evidence 會在證據登記後帶入）", "command": _cmd(ex_parts) + (" --evidence <EVD…>" if r.get("evidence") else "")})
    if mode == "bug":
        bug_parts = ["bin/qaos", "run", "new", "spec-to-bug", "--input", f"spec_id={meta.get('spec_id')}", "--input", f"spec_version={meta.get('spec_version')}",
                     "--input", f"testcase_id={r['testcase_id']}", "--input", f"testcase_version={meta.get('version')}", "--by", who]
        steps.append({"kind": "run", "label": "開 spec-to-bug run（execution_id／evidence_ids 由前兩步帶入）", "command": _cmd(bug_parts) + " --input execution_id=<EXE> --input 'evidence_ids=[…]'"})
    writes = ["evidence/testrun-%d/EVD-*.{ext,yaml}" % run_id, "executions/YYYY-MM/EXE-*.yaml", "testcases/registry/_counters.yaml", "runs/_audit.log"]
    if mode == "bug":
        writes += ["runs/RUN-*/run.yaml（新 spec-to-bug run）", ".warroom/handoff.jsonl（平台）"]
    return {"mode": mode, "steps": steps, "warnings": warnings, "writes": writes, "meta": meta, "operator": who, "result": {k: r.get(k) for k in ("id", "testcase_id", "testcase_version", "result", "actual_result", "bug_run_id", "qaos_execution_id")}}


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
    res = qaos_exec._run(cmd)
    log.append({"what": what, **res})
    if res["exit_code"] != 0:
        raise BugFileError(502, f"{what} 失敗（exit {res['exit_code']}）：{(res['stderr'] or res['stdout'])[-300:]}")
    return res["stdout"].strip()


def execute(run_id: int, result_id: int, mode: str = "bug") -> dict:
    p = plan(run_id, result_id, mode)
    if p["warnings"]:
        raise BugFileError(409, "；".join(p["warnings"]))
    run, r = _result(run_id, result_id)
    who = p["operator"]; meta = p["meta"]
    if not qaos_exec._lock.acquire(blocking=False):
        raise BugFileError(409, "另一條 bin/qaos 正在執行，稍後再試")
    log: list[dict] = []
    started = db.now()
    try:
        evd_ids: list[str] = list(r.get("qaos_evidence_ids") or [])
        if not evd_ids:
            for st in [s for s in p["steps"] if s["kind"] == "evidence"]:
                out = _run_or_raise(st["command"], st["label"], log)
                m = re.search(r"EVD-\d+", out)
                if not m:
                    raise BugFileError(502, f"證據登記沒有回傳 EVD 編號：{out[-200:]}")
                evd_ids.append(m.group(0))
            _save(result_id, qaos_evidence_ids=evd_ids)
        exe_id = r.get("qaos_execution_id")
        if not exe_id:
            ex_cmd = next(s for s in p["steps"] if s["kind"] == "execution")["command"].replace(" --evidence <EVD…>", "")
            for e in evd_ids:
                ex_cmd += " --evidence " + shlex.quote(e)
            out = _run_or_raise(ex_cmd, "匯入執行紀錄", log)
            m = re.search(r"EXE-\d{8}-\d{3}", out)
            if not m:
                raise BugFileError(502, f"execution import 沒有回傳 EXE 編號：{out[-200:]}")
            exe_id = m.group(0)
            _save(result_id, qaos_execution_id=exe_id)
        bug_run = None; hint = f"已匯入 QAOS：{exe_id}"
        if mode == "bug":
            bug_cmd = _cmd(["bin/qaos", "run", "new", "spec-to-bug", "--input", f"spec_id={meta['spec_id']}", "--input", f"spec_version={meta['spec_version']}",
                            "--input", f"testcase_id={r['testcase_id']}", "--input", f"testcase_version={meta['version']}",
                            "--input", f"execution_id={exe_id}", "--input", "evidence_ids=" + json.dumps(evd_ids), "--by", who])
            out = _run_or_raise(bug_cmd, "開 spec-to-bug run", log)
            m = re.search(r"RUN-\d{8}-\d{3}", out)
            if not m:
                raise BugFileError(502, f"run new 沒有回傳 RUN 編號：{out[-200:]}")
            bug_run = m.group(0)
            _save(result_id, bug_run_id=bug_run)
            hint = f"已開 {bug_run}（spec-to-bug）。Bug Analyst 的 T1 已 READY，QA session 會由 relay 接續；走到 OPEN_BUG 核准單時會出現在「單據 › 核准」。"
    finally:
        qaos_exec._lock.release()
    ended = db.now()
    handoff_id = None
    if bug_run:
        from . import runs as run_svc
        run_svc._cache.pop(str(run_svc.RUNS_DIR / bug_run / "run.yaml"), None)
        after = run_svc.get(bug_run)
        cur = next((t for t in (after or {}).get("tasks", []) if t["task_id"] == (after or {}).get("current_task_id")), None)
        sid = _target_session()
        import uuid
        handoff_id = uuid.uuid4().hex[:12]
        qaos_exec._append_handoff({
            "kind": "handoff", "id": handoff_id, "ts": ended, "ticket_id": f"TESTRUN-{run_id}/{result_id}", "ticket_kind": "bug_filing", "action": "spec-to-bug",
            "handoff_kind": "resume_agent" if (after and after["status"] == "RUNNING" and cur and cur.get("status") == "READY") else "notify_only",
            "command": bug_cmd, "exit_code": 0, "run_id": bug_run, "run_status_after": after["status"] if after else None,
            "next_task": (after or {}).get("current_task_id"), "next_agent": cur.get("agent_id") if cur else None,
            "session_id": sid, "hint": hint, "by": who,
        })
        if not sid:
            hint += " 找不到活著的 QA session 可交接，請到 QA session 說「繼續 " + bug_run + "」。"
    with db.connect() as con:
        con.execute("""INSERT INTO ticket_executions (ticket_id, kind, action, command, exit_code, stdout, stderr, post_json, run_id, run_status_after, next_task, session_id, handoff_id, hint, started_at, ended_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (f"TESTRUN-{run_id}/{result_id}", "bug_filing" if mode == "bug" else "execution_import", mode, "\n".join(x["command"] for x in log), 0,
                     "\n".join(x["stdout"] for x in log)[-4000:], "", json.dumps(log, ensure_ascii=False)[-8000:], bug_run, None, None, None, handoff_id, hint, started, ended))
    if run.get("status") in ("done", "aborted"):
        testruns.sync_report(run_id)
    return {"ok": True, "evidence_ids": evd_ids, "execution_id": exe_id, "bug_run_id": bug_run, "hint": hint, "log": log}


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


def _save(result_id: int, **fields):
    sets = {k: (json.dumps(v, ensure_ascii=False) if isinstance(v, list) else v) for k, v in fields.items()}
    sets["updated_at"] = db.now()
    with db.connect() as con:
        con.execute(f"UPDATE test_results SET {', '.join(f'{k}=?' for k in sets)} WHERE id=?", (*sets.values(), result_id))
