"""admin-ui 後端 code review（review-handoff/admin-ui-backend-review）第 1 批的回歸測試。

每項（R02、R05、R06、R09、R11～R17，以及第 1 輪複審的 F1-01～F1-03）至少有一條測試在舊程式上會失敗；
標「控制案例」的是確認修正沒有誤擋正常情況，舊程式本來就會通過。全部在假根，bin/qaos 換成假的。
"""
import asyncio
import io
import json
import os
import pathlib
import shlex
import subprocess
import sys
import typing

import pytest
import yaml


@pytest.fixture
def bug_sandbox(full_sandbox, monkeypatch):
    from backend.services import qaos_bug, testruns
    root = full_sandbox.root
    monkeypatch.setattr(qaos_bug, "PROJECT_ROOT", root)
    monkeypatch.setattr(qaos_bug, "VER_DIR", root / "testcases" / "versions")
    monkeypatch.setattr(qaos_bug, "DATA_DIR", root / "admin-ui" / "data")
    monkeypatch.setattr(testruns, "EVIDENCE_DIR", root / "admin-ui" / "data" / "evidence")
    monkeypatch.setattr(testruns, "DATA_DIR", root / "admin-ui" / "data")
    monkeypatch.setattr(qaos_bug, "_target_session", lambda: "sess-A")
    full_sandbox.qaos_bug = qaos_bug
    full_sandbox.testruns = testruns
    return full_sandbox


def _make_result(sb, write_registry_tc, result="fail", actual="畫面卡住", notes="", executed_at="2026-10-08T00:00:00Z", with_evidence=True, run_status="running"):
    write_registry_tc("TC-AREA-042", 1, "SPEC-AREA-001", spec_version="0.3")
    now = sb.db.now()
    with sb.db.connect() as con:
        rid = con.execute("INSERT INTO test_runs (name, trigger, status, environment, build, created_by, import_all, created_at, updated_at) VALUES ('r','manual',?,'stage','b1','me',0,?,?)",
                          (run_status, now, now)).lastrowid
        res_id = con.execute("INSERT INTO test_results (run_id, position, testcase_id, testcase_version, group_key, title, result, actual_result, notes, executed_at, created_at, updated_at) "
                             "VALUES (?,0,'TC-AREA-042',1,'AREA','t',?,?,?,?,?,?)", (rid, result, actual, notes, executed_at, now, now)).lastrowid
    if with_evidence:
        sb.testruns.add_evidence(rid, res_id, "shot.png", b"\x89PNG fake", "screenshot", "卡住畫面", "me")
    return rid, res_id


def _fake_cli(sb, calls, outputs, write_run=None):
    def fake(cmd):
        calls.append(cmd)
        if " evidence add " in cmd: out = outputs.get("evidence", "EVD-0101")
        elif " execution import " in cmd: out = outputs["execution"]
        else:
            out = outputs["run"]
            if write_run:
                write_run(out.split()[0], "RUNNING", "T1", [("T0", "DONE", None), ("T1", "READY", "agent-bug-analyst")], workflow_id="spec-to-bug")
        return {"command": cmd, "exit_code": 0, "stdout": out, "stderr": ""}
    sb.qaos_exec._run = fake


def _result_row(sb, rid, res_id):
    return next(x for x in sb.testruns.get_run(rid)["results"] if x["id"] == res_id)


# ---------------------------------------------------------------- R05：四位流水號
def test_r05_four_digit_exe_and_run_ids_are_kept_whole(bug_sandbox, write_registry_tc, fake_qaos, write_run):
    rid, res_id = _make_result(bug_sandbox, write_registry_tc)
    _fake_cli(bug_sandbox, fake_qaos["calls"], {"execution": "EXE-20261008-1000", "run": "RUN-20261008-1000 RUNNING current_task=T1"}, write_run)
    res = bug_sandbox.qaos_bug.execute(rid, res_id)
    assert res["execution_id"] == "EXE-20261008-1000" and res["bug_run_id"] == "RUN-20261008-1000"
    assert "execution_id=EXE-20261008-1000" in fake_qaos["calls"][-1]
    r = _result_row(bug_sandbox, rid, res_id)
    assert r["qaos_execution_id"] == "EXE-20261008-1000" and r["bug_run_id"] == "RUN-20261008-1000"


# ---------------------------------------------------------------- R16：預覽占位符不能動到使用者文字
def test_r16_actual_result_containing_the_placeholder_is_sent_verbatim(bug_sandbox, write_registry_tc, fake_qaos, write_run):
    actual = "actual --evidence <EVD…> end"
    rid, res_id = _make_result(bug_sandbox, write_registry_tc, actual=actual)
    _fake_cli(bug_sandbox, fake_qaos["calls"], {"execution": "EXE-20261008-001", "run": "RUN-20261008-001 RUNNING current_task=T1"}, write_run)
    bug_sandbox.qaos_bug.execute(rid, res_id)
    argv = shlex.split(next(c for c in fake_qaos["calls"] if " execution import " in c))
    assert argv[argv.index("--actual-result") + 1] == actual
    assert argv[argv.index("--evidence") + 1] == "EVD-0101"


# ---------------------------------------------------------------- R17：未知 mode 不寫 QAOS
def test_r17_unknown_mode_is_rejected_before_any_write(bug_sandbox, write_registry_tc, fake_qaos):
    rid, res_id = _make_result(bug_sandbox, write_registry_tc, result="blocked", with_evidence=False)
    for fn in (bug_sandbox.qaos_bug.plan, bug_sandbox.qaos_bug.execute):
        with pytest.raises(bug_sandbox.qaos_bug.BugFileError) as ei:
            fn(rid, res_id, "BUG")
        assert ei.value.status == 400
    assert fake_qaos["calls"] == []
    assert _result_row(bug_sandbox, rid, res_id)["qaos_execution_id"] is None


def test_r17_router_declares_mode_as_literal():
    from backend.routers import testruns as rt
    for fn in (rt.bug_plan, rt.file_bug):
        assert typing.get_args(typing.get_type_hints(fn)["mode"]) == ("bug", "execution")


# ---------------------------------------------------------------- R13：執行歷史 JSON 不可被切壞
def test_r13_long_output_keeps_history_parseable(bug_sandbox, write_registry_tc, fake_qaos):
    rid, res_id = _make_result(bug_sandbox, write_registry_tc, result="pass", actual="X" * 9000, with_evidence=False)
    _fake_cli(bug_sandbox, fake_qaos["calls"], {"execution": "EXE-20261008-002"})
    bug_sandbox.qaos_bug.execute(rid, res_id, "execution")
    hist = bug_sandbox.qaos_exec.executions(f"TESTRUN-{rid}/{res_id}")
    assert len(hist) == 1 and hist[0]["post"] and hist[0]["post"][0]["what"] == "匯入執行紀錄"
    assert "post_error" not in hist[0]
    cmd = hist[0]["post"][0]["command"]
    assert len(cmd) <= bug_sandbox.qaos_bug.LOG_FIELD_MAX + 20 and "已截斷" in cmd


def test_r13_previously_corrupted_history_is_reported_not_raised(sandbox):
    with sandbox.db.connect() as con:
        con.execute("INSERT INTO ticket_executions (ticket_id, kind, action, command, exit_code, post_json, started_at, ended_at) VALUES ('TESTRUN-1/1','execution_import','execution','x',0,?,'t','t')",
                    ('ommand": "bin/qaos execution import …"}]',))
    hist = sandbox.qaos_exec.executions("TESTRUN-1/1")
    assert hist[0]["post"] == [] and "損毀" in hist[0]["post_error"]


# ---------------------------------------------------------------- R12：以連字號開頭的文字
REPO = pathlib.Path(__file__).resolve().parents[3]
_PARSE = """
import json, sys
from tools.qaos import cli
got = []
for name in dir(cli):
    if name.startswith("cmd_"):
        setattr(cli, name, lambda a: got.append({k: v for k, v in vars(a).items() if k != "f"}))
cli._notice = lambda: None
for argv in json.loads(sys.stdin.read()):
    cli.main(argv)
print(json.dumps(got, ensure_ascii=False))
"""


def _parse_with_real_cli(commands: list[str]) -> list[dict]:
    """用正式 bin/qaos 的 argparse 解析（所有 cmd_* 換成只記錄參數，不執行、不寫入）；在子行程裡跑，不污染本行程的模組狀態。"""
    argvs = [shlex.split(c)[1:] for c in commands]
    r = subprocess.run([sys.executable, "-c", _PARSE], input=json.dumps(argvs), capture_output=True, text=True, cwd=REPO,
                       env={**os.environ, "QAOS_ROOT": str(REPO), "PYTHONPATH": str(REPO)}, timeout=60)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_r12_dash_leading_text_is_parsed_by_the_real_cli(sandbox, write_run, write_approval):
    ans = sandbox.tickets.clarification_command("CLR-T-9", {"decision": "answer", "rationale": "--verbose", "extra": {"answered_by": "-PM"}})["command"]
    assert "--answer=--verbose" in shlex.split(ans) and "--answered-by=-PM" in shlex.split(ans)
    write_run("RUN-P", "WAITING_HUMAN", "T4", [("T4", "RUNNING", None)])
    write_approval("APR-P", "RUN-P", batch_items=[{"id": "TC-X-001", "version": 1}, {"id": "TC-X-002", "version": 1}])
    apr = sandbox.tickets.approval_command("APR-P", {"decision": "approve", "rationale": "-整批核准",
                                                    "per_item": {"TC-X-001": {"decision": "reject", "reason": "-缺前置"}}})["command"]
    a, b = _parse_with_real_cli([ans, apr])
    assert a["answer"] == "--verbose" and a["answered_by"] == "-PM" and a["new_request"] is True
    assert b["per_item"] == ["TC-X-001:reject"] and b["rationale"].startswith("-整批核准")


def test_r12_append_options_mix_both_forms_in_the_real_cli(bug_sandbox, write_registry_tc):
    rid, res_id = _make_result(bug_sandbox, write_registry_tc, actual="-1 卡住", notes="--literal")
    run = bug_sandbox.testruns.get_run(rid); r = _result_row(bug_sandbox, rid, res_id)
    meta = bug_sandbox.qaos_bug._tc_meta(r["testcase_id"], r["testcase_version"])
    argv = bug_sandbox.qaos_bug._execution_argv(run, r, meta, "me") + ["--evidence", "EVD-0001", "--evidence=-weird"]
    (ex,) = _parse_with_real_cli([bug_sandbox.qaos_bug._cmd(argv)])
    assert ex["actual_result"] == "-1 卡住" and ex["notes"] == "--literal" and ex["evidence"] == ["EVD-0001", "-weird"] and ex["testcase_version"] == 1


def test_r12_plain_values_keep_the_readable_form(sandbox):
    out = sandbox.tickets.bug_command("BUG-T-9", {"decision": "transition", "rationale": "-1 這版沒修", "extra": {"to": "OPEN"}})
    assert "--to OPEN" in out["command"] and "'--note=-1 這版沒修'" in out["command"]


# ---------------------------------------------------------------- R14：草稿型別
def test_r14_non_string_extra_is_rejected_by_the_draft_model():
    from pydantic import ValidationError
    from backend.routers.tickets import DraftIn
    with pytest.raises(ValidationError):
        DraftIn(decision="ask", extra={"asked_to": 123})
    with pytest.raises(ValidationError):
        DraftIn(per_item={"TC-X-001": {"decision": "reject", "reason": ["x"]}})
    assert DraftIn(extra={"asked_to": "PM"}).extra == {"asked_to": "PM"}


def test_r14_draft_is_not_saved_when_validation_fails(sandbox):
    from pydantic import ValidationError
    from backend.routers.tickets import DraftIn
    with pytest.raises(ValidationError):
        DraftIn(decision="ask", extra={"asked_to": 123}).save("CLR-T-8", "clarification")
    assert sandbox.tickets.get_draft("CLR-T-8") is None
    d = DraftIn(decision="approve", per_item={"TC-X-001": {"decision": "reject", "reason": "缺前置"}}).save("APR-T-8", "approval")
    assert d["per_item"] == {"TC-X-001": {"decision": "reject", "reason": "缺前置"}}


def _asgi_put(app, path: str, payload: dict) -> int:
    """不經 httpx／TestClient，直接以 ASGI 呼叫 app，回 HTTP 狀態碼（CI 的 requirements 沒有 httpx）。"""
    raw = json.dumps(payload).encode()
    sent: list[dict] = []

    async def receive():
        return {"type": "http.request", "body": raw, "more_body": False}

    async def send(message):
        sent.append(message)
    scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": "PUT", "scheme": "http", "path": path, "raw_path": path.encode(),
             "query_string": b"", "root_path": "", "headers": [(b"content-type", b"application/json")], "server": ("test", 80), "client": ("test", 1)}
    asyncio.run(app(scope, receive, send))
    return next(m["status"] for m in sent if m["type"] == "http.response.start")


def test_r14_http_put_with_non_string_values_is_422_and_writes_nothing(sandbox, monkeypatch):
    from fastapi import FastAPI
    from backend.routers import tickets as rt
    app = FastAPI(); app.include_router(rt.router)

    def must_not_reach(*a, **k):
        raise AssertionError("驗證失敗的請求不該進到 endpoint／service")
    for name in ("approval_detail", "clarification_detail", "bug_detail"):
        monkeypatch.setattr(sandbox.tickets, name, must_not_reach)
    for kind, plural in (("approval", "approvals"), ("clarification", "clarifications"), ("bug", "bugs")):
        tid = f"T-{kind}"
        before = sandbox.tickets.save_draft(tid, kind, "ask", None, "原內容", None, {"asked_to": "PM"})
        for payload in ({"extra": {"asked_to": 123}}, {"per_item": {"TC-X-001": {"reason": ["x"]}}}):
            assert _asgi_put(app, f"/api/tickets/{plural}/{tid}/draft", payload) == 422
            assert sandbox.tickets.get_draft(tid) == before


def test_r14_legacy_non_string_extra_does_not_crash_command_assembly(sandbox):
    out = sandbox.tickets.clarification_command("CLR-T-7", {"decision": "ask", "extra": {"asked_to": 123}})
    assert "--to 123" in out["command"]


# ---------------------------------------------------------------- R15：上傳上限分塊檢查
class _CountingFile:
    """模擬 UploadFile：記錄最多讀了多少位元組。"""
    def __init__(self, size):
        self.buf = io.BytesIO(b"x" * size); self.read_total = 0; self.closed = False
        self.filename = "big.log"

    async def read(self, n=-1):
        b = self.buf.read(n); self.read_total += len(b); return b

    async def close(self):
        self.closed = True


def test_r15_oversized_upload_stops_reading_at_the_limit(bug_sandbox, write_registry_tc, monkeypatch):
    from fastapi import HTTPException
    from backend.routers import testruns as rt
    rid, res_id = _make_result(bug_sandbox, write_registry_tc, with_evidence=False)
    monkeypatch.setattr(bug_sandbox.testruns, "MAX_EVIDENCE_BYTES", 3 * 1024 * 1024)
    f = _CountingFile(10 * 1024 * 1024)
    with pytest.raises(HTTPException) as ei:
        asyncio.run(rt.add_evidence(rid, res_id, f, "log", ""))
    assert ei.value.status_code == 413
    assert f.read_total <= 4 * 1024 * 1024 and f.closed
    assert _result_row(bug_sandbox, rid, res_id)["evidence"] == []


def test_r15_upload_within_the_limit_is_stored(  # 控制案例
bug_sandbox, write_registry_tc):
    from backend.routers import testruns as rt
    rid, res_id = _make_result(bug_sandbox, write_registry_tc, with_evidence=False)
    rec = asyncio.run(rt.add_evidence(rid, res_id, _CountingFile(2 * 1024 * 1024 + 7), "log", ""))
    assert rec["size"] == 2 * 1024 * 1024 + 7


# ---------------------------------------------------------------- R09：預檢在鎖內
def test_r09_plan_and_snapshot_are_read_while_holding_the_lock(bug_sandbox, write_registry_tc, fake_qaos, write_run, monkeypatch):
    rid, res_id = _make_result(bug_sandbox, write_registry_tc)
    _fake_cli(bug_sandbox, fake_qaos["calls"], {"execution": "EXE-20261008-003", "run": "RUN-20261008-003 RUNNING current_task=T1"}, write_run)
    qb = bug_sandbox.qaos_bug
    seen = []
    orig_plan, orig_result = qb.plan, qb._result
    monkeypatch.setattr(qb, "plan", lambda *a, **k: (seen.append(("plan", qb.qaos_exec._lock.locked())), orig_plan(*a, **k))[1])
    monkeypatch.setattr(qb, "_result", lambda *a, **k: (seen.append(("_result", qb.qaos_exec._lock.locked())), orig_result(*a, **k))[1])
    qb.execute(rid, res_id)
    assert seen and all(locked for _, locked in seen), seen


def test_r09_second_request_after_first_completes_is_rejected_without_handoff(  # 控制案例（循序；鎖內時序由上一條驗證）
bug_sandbox, write_registry_tc, fake_qaos, write_run, read_handoff):
    rid, res_id = _make_result(bug_sandbox, write_registry_tc)
    _fake_cli(bug_sandbox, fake_qaos["calls"], {"execution": "EXE-20261008-004", "run": "RUN-20261008-004 RUNNING current_task=T1"}, write_run)
    bug_sandbox.qaos_bug.execute(rid, res_id)
    with pytest.raises(bug_sandbox.qaos_bug.BugFileError) as ei:
        bug_sandbox.qaos_bug.execute(rid, res_id)
    assert ei.value.status == 409 and "已經送過" in str(ei.value)
    assert len([h for h in read_handoff() if h.get("kind") == "handoff"]) == 1


# ---------------------------------------------------------------- R11：PATCH 不能改回合狀態
def test_r11_patch_cannot_change_run_status(bug_sandbox, write_registry_tc):
    tr = bug_sandbox.testruns
    rid, _ = _make_result(bug_sandbox, write_registry_tc, run_status="done", with_evidence=False)
    for st in ("running", "planned", "done", "aborted"):
        with pytest.raises(tr.TestRunError) as ei:
            tr.patch_run(rid, {"status": st})
        assert ei.value.status == 400
    assert tr.get_run(rid)["status"] == "done"
    assert tr.patch_run(rid, {"environment": "prod", "status": None})["environment"] == "prod"


# ---------------------------------------------------------------- R06：新格式 RESOLVE_AMBIGUITY
def _pinned_resolve_ambiguity(sandbox, write_run, write_approval, apr_id="APR-RA"):
    write_run("RUN-RA", "WAITING_HUMAN", "T4", [("T4", "RUNNING", None)], waiting_on_approval_id=apr_id)
    p = write_approval(apr_id, "RUN-RA", apr_type="RESOLVE_AMBIGUITY")
    d = yaml.safe_load(p.read_text(encoding="utf-8"))
    d["requirement_model_revision"] = {"spec_id": "SPEC-DEMO-001", "spec_version": "0.1", "revision": 2}
    p.write_text(yaml.safe_dump(d, allow_unicode=True), encoding="utf-8")


def test_r06_pinned_resolve_ambiguity_approve_warns_and_is_not_executed(sandbox, write_run, write_approval, fake_qaos):
    _pinned_resolve_ambiguity(sandbox, write_run, write_approval)
    for decision in ("approve", "override"):
        out = sandbox.tickets.approval_command("APR-RA", {"decision": decision, "option": "resolved", "rationale": "選 A"})
        assert any("--resolution" in w for w in out["warnings"])
    sandbox.tickets.save_draft("APR-RA", "approval", "approve", "resolved", "選 A", None, None)
    with pytest.raises(sandbox.qaos_exec.ExecError) as ei:
        sandbox.qaos_exec.execute("APR-RA")
    assert ei.value.status == 409 and fake_qaos["calls"] == []


def test_r06_reject_and_legacy_resolve_ambiguity_are_unaffected(  # 控制案例
sandbox, write_run, write_approval):
    _pinned_resolve_ambiguity(sandbox, write_run, write_approval)
    assert sandbox.tickets.approval_command("APR-RA", {"decision": "reject", "rationale": "退回作者"})["warnings"] == []
    write_run("RUN-OLD", "WAITING_HUMAN", "T4", [("T4", "RUNNING", None)])
    write_approval("APR-OLD", "RUN-OLD", apr_type="RESOLVE_AMBIGUITY")
    assert sandbox.tickets.approval_command("APR-OLD", {"decision": "approve", "option": "resolved"})["warnings"] == []


# ---------------------------------------------------------------- R02：同內容匯入的暫時擋法
def _canonical_cli(sb, calls):
    """假 CLI 依請求內容配發 EXE：完全相同的 argv 回同一個 EXE（= CLI 對同一 CanonicalRequest 的重送），不同就配新號。"""
    seen: dict[str, str] = {}

    def fake(cmd):
        calls.append(cmd)
        if " evidence add " in cmd:
            out = f"EVD-{len(calls):04d}"
        else:
            out = seen.setdefault(cmd, f"EXE-20261008-{len(seen) + 1:03d}")
        return {"command": cmd, "exit_code": 0, "stdout": out, "stderr": ""}
    sb.qaos_exec._run = fake
    return seen


def _set_version(sb, res_id, version):
    with sb.db.connect() as con:
        con.execute("UPDATE test_results SET testcase_version=? WHERE id=?", (version, res_id))


PASS_OK = dict(result="pass", actual="ok", with_evidence=False)


def test_r02_identical_import_from_another_result_is_blocked(bug_sandbox, write_registry_tc, fake_qaos):
    rid1, res1 = _make_result(bug_sandbox, write_registry_tc, **PASS_OK)
    _canonical_cli(bug_sandbox, fake_qaos["calls"])
    bug_sandbox.qaos_bug.execute(rid1, res1, "execution")
    rid2, res2 = _make_result(bug_sandbox, write_registry_tc, **PASS_OK)
    p = bug_sandbox.qaos_bug.plan(rid2, res2, "execution")
    assert any("EXE-20261008-001" in w and f"#{rid1}" in w for w in p["warnings"])
    fake_qaos["calls"].clear()
    with pytest.raises(bug_sandbox.qaos_bug.BugFileError) as ei:
        bug_sandbox.qaos_bug.execute(rid2, res2, "execution")
    assert ei.value.status == 409 and fake_qaos["calls"] == []
    assert _result_row(bug_sandbox, rid2, res2)["qaos_execution_id"] is None


def test_r02_uses_the_request_actually_sent_not_the_editable_run_settings(bug_sandbox, write_registry_tc, fake_qaos):
    """F1-01：匯入後改回合的 build，原內容（b1）的新結果仍要擋；改後的內容（b2）從沒匯入過，不能誤擋。"""
    rid1, res1 = _make_result(bug_sandbox, write_registry_tc, **PASS_OK)
    issued = _canonical_cli(bug_sandbox, fake_qaos["calls"])
    bug_sandbox.qaos_bug.execute(rid1, res1, "execution")
    bug_sandbox.testruns.patch_run(rid1, {"build": "b2"})
    rid2, res2 = _make_result(bug_sandbox, write_registry_tc, **PASS_OK)               # 與 A 當時送出的 b1 請求相同
    with pytest.raises(bug_sandbox.qaos_bug.BugFileError) as ei:
        bug_sandbox.qaos_bug.execute(rid2, res2, "execution")
    assert ei.value.status == 409
    rid3, res3 = _make_result(bug_sandbox, write_registry_tc, **PASS_OK)
    bug_sandbox.testruns.patch_run(rid3, {"build": "b2"})
    assert bug_sandbox.qaos_bug.plan(rid3, res3, "execution")["warnings"] == []
    res = bug_sandbox.qaos_bug.execute(rid3, res3, "execution")
    assert res["execution_id"] == "EXE-20261008-002" and len(issued) == 2


def test_r02_compares_the_effective_testcase_version(bug_sandbox, write_registry_tc, fake_qaos):
    """F1-02：DB 版本為 NULL 時 argv 用 registry active 版本；與明確寫 1 的請求相同就要擋。
    active 版本換成 2 之後，NULL 解析成 2，與當時送出的 v1 請求不同，不能誤擋。"""
    rid1, res1 = _make_result(bug_sandbox, write_registry_tc, **PASS_OK)
    _canonical_cli(bug_sandbox, fake_qaos["calls"])
    bug_sandbox.qaos_bug.execute(rid1, res1, "execution")
    rid2, res2 = _make_result(bug_sandbox, write_registry_tc, **PASS_OK)
    _set_version(bug_sandbox, res2, None)
    with pytest.raises(bug_sandbox.qaos_bug.BugFileError) as ei:
        bug_sandbox.qaos_bug.execute(rid2, res2, "execution")
    assert ei.value.status == 409 and not any(" execution import " in c for c in fake_qaos["calls"][1:])
    write_registry_tc("TC-AREA-042", 2, "SPEC-AREA-001", spec_version="0.4")
    assert bug_sandbox.qaos_bug.plan(rid2, res2, "execution")["warnings"] == []


def test_r02_different_content_or_evidence_is_not_blocked(bug_sandbox, write_registry_tc, fake_qaos):  # 控制案例
    rid1, res1 = _make_result(bug_sandbox, write_registry_tc, **PASS_OK)
    _canonical_cli(bug_sandbox, fake_qaos["calls"])
    bug_sandbox.qaos_bug.execute(rid1, res1, "execution")
    rid2, res2 = _make_result(bug_sandbox, write_registry_tc, result="pass", actual="ok", notes="第二次複測", with_evidence=False)
    assert bug_sandbox.qaos_bug.plan(rid2, res2, "execution")["warnings"] == []
    rid3, res3 = _make_result(bug_sandbox, write_registry_tc, result="pass", actual="ok", with_evidence=True)
    assert bug_sandbox.qaos_bug.plan(rid3, res3, "execution")["warnings"] == []
    # 自己已匯入：只提示「已經匯過」，不誤報成另一筆
    assert not any("另一筆結果" in w for w in bug_sandbox.qaos_bug.plan(rid1, res1, "execution")["warnings"])


# ---------------------------------------------------------------- F1-03：影子測試索引的 RUN 編號
def test_f1_03_shadow_doc_keeps_four_digit_run_ids(full_sandbox, write_shadow_doc):
    write_shadow_doc("AREA-001", ["RUN-20261008-1000"], "內文提到 RUN-20261008-0999X 不算")
    docs = full_sandbox.specflow._shadow_docs()
    assert docs[0]["run_ids"] == ["RUN-20261008-1000"]
