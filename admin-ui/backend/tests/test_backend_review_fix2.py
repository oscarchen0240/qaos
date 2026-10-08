"""admin-ui 後端 code review（review-handoff/admin-ui-backend-review）第 2 批（B2）的回歸測試：R03、R04、R08、R10（後端部分）。

每項至少有一條測試在舊程式上會失敗；標「控制案例」的是確認修正沒有誤擋正常情況。全部在假根，bin/qaos 換成假的。
R01、R07 依 evaluation-02 刻意不做暫時擋法；R10 刻意不改 HTTP 狀態碼（失敗仍是 200＋ok=False，bug 流程仍是 BugFileError.status）。
"""
import contextlib
import json
import sqlite3
import subprocess
import threading

import pytest

from backend import db as db_mod
from .test_requirement_a_compat import _answer_draft, _answer_effect, _clr, real_sm  # noqa: F401


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


def _make_result(sb, write_registry_tc, result="fail", actual="畫面卡住", with_evidence=True, run_status="running"):
    write_registry_tc("TC-AREA-042", 1, "SPEC-AREA-001", spec_version="0.3")
    now = sb.db.now()
    with sb.db.connect() as con:
        rid = con.execute("INSERT INTO test_runs (name, trigger, status, environment, build, created_by, import_all, created_at, updated_at) VALUES ('r','manual',?,'stage','b1','me',0,?,?)",
                          (run_status, now, now)).lastrowid
        res_id = con.execute("INSERT INTO test_results (run_id, position, testcase_id, testcase_version, group_key, title, result, actual_result, executed_at, created_at, updated_at) "
                             "VALUES (?,0,'TC-AREA-042',1,'AREA','t',?,?,'2026-10-08T00:00:00Z',?,?)", (rid, result, actual, now, now)).lastrowid
    if with_evidence:
        sb.testruns.add_evidence(rid, res_id, "shot.png", b"\x89PNG fake", "screenshot", "卡住畫面", "me")
    return rid, res_id


def _fake_cli(sb, calls, write_run, exe="EXE-20261009-001", run="RUN-20261009-001", fail_on=None):
    """fail_on: 'execution' 讓 execution import 失敗（exit 1）。"""
    def fake(cmd):
        calls.append(cmd)
        if " evidence add " in cmd:
            out = f"EVD-{100 + len(calls)}"
        elif " execution import " in cmd:
            if fail_on == "execution":
                return {"command": cmd, "exit_code": 1, "stdout": "", "stderr": "boom"}
            out = exe
        else:
            out = f"{run} RUNNING current_task=T1"
            write_run(run, "RUNNING", "T1", [("T0", "DONE", None), ("T1", "READY", "agent-bug-analyst")], workflow_id="spec-to-bug")
        return {"command": cmd, "exit_code": 0, "stdout": out, "stderr": ""}
    sb.qaos_exec._run = fake


def _row(sb, rid, res_id):
    return next(x for x in sb.testruns.get_run(rid)["results"] if x["id"] == res_id)


def _evidence_files(sb, rid):
    d = sb.testruns.EVIDENCE_DIR / str(rid)
    return sorted(p.name for p in d.iterdir()) if d.exists() else []


# ================================================================ R03：匯入後不可再改
def test_r03_imported_result_cannot_be_edited_or_have_evidence_changed(bug_sandbox, write_registry_tc, fake_qaos, write_run):
    sb = bug_sandbox
    rid, res_id = _make_result(sb, write_registry_tc)
    _fake_cli(sb, fake_qaos["calls"], write_run)
    sb.qaos_bug.execute(rid, res_id)
    before = _row(sb, rid, res_id)
    files_before = _evidence_files(sb, rid)
    tr = sb.testruns
    with pytest.raises(tr.TestRunError) as ei:
        tr.set_result(rid, res_id, {"actual_result": "改過了"}, "me")
    assert ei.value.status == 409 and "已匯入 QAOS" in str(ei.value) and "重開" in str(ei.value)
    with pytest.raises(tr.TestRunError) as ei:
        tr.add_evidence(rid, res_id, "late.png", b"x", "screenshot", "", "me")
    assert ei.value.status == 409
    with pytest.raises(tr.TestRunError) as ei:
        tr.remove_evidence(rid, res_id, before["evidence"][0]["id"])
    assert ei.value.status == 409
    after = _row(sb, rid, res_id)
    assert after["actual_result"] == "畫面卡住" and after["evidence"] == before["evidence"]
    assert _evidence_files(sb, rid) == files_before            # 被拒的上傳不留孤兒檔，被拒的刪除不動檔案


def test_r03_execution_only_import_also_locks_the_result(bug_sandbox, write_registry_tc, fake_qaos, write_run):
    sb = bug_sandbox
    rid, res_id = _make_result(sb, write_registry_tc, result="pass", actual="")
    _fake_cli(sb, fake_qaos["calls"], write_run)
    sb.qaos_bug.execute(rid, res_id, "execution")
    with pytest.raises(sb.testruns.TestRunError) as ei:
        sb.testruns.set_result(rid, res_id, {"result": "fail"}, "me")
    assert ei.value.status == 409


def test_r03_unimported_result_is_still_editable(bug_sandbox, write_registry_tc):  # 控制案例
    sb = bug_sandbox
    rid, res_id = _make_result(sb, write_registry_tc)
    sb.testruns.set_result(rid, res_id, {"actual_result": "新的描述"}, "me")
    rec = sb.testruns.add_evidence(rid, res_id, "more.png", b"y", "screenshot", "", "me")
    sb.testruns.remove_evidence(rid, res_id, rec["id"])
    r = _row(sb, rid, res_id)
    assert r["actual_result"] == "新的描述" and len(r["evidence"]) == 1


def test_r03_result_being_sent_cannot_be_edited(bug_sandbox, write_registry_tc):
    sb = bug_sandbox
    rid, res_id = _make_result(sb, write_registry_tc)
    with sb.testruns.sending(res_id):
        with pytest.raises(sb.testruns.TestRunError) as ei:
            sb.testruns.add_evidence(rid, res_id, "x.png", b"x", "screenshot", "", "me")
        assert ei.value.status == 409
        with pytest.raises(sb.testruns.TestRunError):
            sb.testruns.set_result(rid, res_id, {"notes": "n"}, "me")
    sb.testruns.set_result(rid, res_id, {"notes": "n"}, "me")  # 送完之後恢復可改


def test_r03_changed_evidence_after_partial_registration_is_not_silently_reused(bug_sandbox, write_registry_tc, fake_qaos, write_run):
    """原報告情境 2：EVD 已登記、execution import 失敗；之後換了證據再重送，舊程式會沿用舊 EVD 送出。"""
    sb = bug_sandbox
    rid, res_id = _make_result(sb, write_registry_tc)
    _fake_cli(sb, fake_qaos["calls"], write_run, fail_on="execution")
    with pytest.raises(sb.qaos_bug.BugFileError):
        sb.qaos_bug.execute(rid, res_id)
    r = _row(sb, rid, res_id)
    assert r["qaos_evidence_ids"] and r["qaos_execution_id"] is None
    # 換證據：刪掉原本的、上傳不同內容（數量不變，只比數量會漏）
    sb.testruns.remove_evidence(rid, res_id, r["evidence"][0]["id"])
    sb.testruns.add_evidence(rid, res_id, "other.png", b"different", "screenshot", "", "me")
    p = sb.qaos_bug.plan(rid, res_id)
    assert any("不一致" in w for w in p["warnings"])
    fake_qaos["calls"].clear()
    _fake_cli(sb, fake_qaos["calls"], write_run)
    with pytest.raises(sb.qaos_bug.BugFileError) as ei:
        sb.qaos_bug.execute(rid, res_id)
    assert ei.value.status == 409 and "不一致" in str(ei.value)
    assert fake_qaos["calls"] == []


def test_r03_added_evidence_after_partial_registration_is_flagged(bug_sandbox, write_registry_tc, fake_qaos, write_run):
    sb = bug_sandbox
    rid, res_id = _make_result(sb, write_registry_tc)
    _fake_cli(sb, fake_qaos["calls"], write_run, fail_on="execution")
    with pytest.raises(sb.qaos_bug.BugFileError):
        sb.qaos_bug.execute(rid, res_id)
    sb.testruns.add_evidence(rid, res_id, "extra.png", b"extra", "screenshot", "", "me")
    assert any("不一致" in w for w in sb.qaos_bug.plan(rid, res_id)["warnings"])


def test_r03_unchanged_evidence_retry_reuses_registration(bug_sandbox, write_registry_tc, fake_qaos, write_run):  # 控制案例
    sb = bug_sandbox
    rid, res_id = _make_result(sb, write_registry_tc)
    _fake_cli(sb, fake_qaos["calls"], write_run, fail_on="execution")
    with pytest.raises(sb.qaos_bug.BugFileError):
        sb.qaos_bug.execute(rid, res_id)
    assert not sb.qaos_bug.plan(rid, res_id)["warnings"]
    fake_qaos["calls"].clear()
    _fake_cli(sb, fake_qaos["calls"], write_run)
    res = sb.qaos_bug.execute(rid, res_id)
    assert res["ok"] and all(" evidence add " not in c for c in fake_qaos["calls"])


# ================================================================ R08：證據讀改寫不遺失
class _PausingJson:
    """把 testruns 裡的 json.loads 換成：名為 'A' 的執行緒第一次呼叫（＝讀完證據清單、準備寫回前）停下來，等 `release` 才繼續。
    release 由 B 的行為觸發，不是固定時間：
      - 舊程式（沒有交易保護）：B 完成整個新增／刪除後才 release → A 拿著舊清單寫回，遺失才會重現；
      - 新程式：B 一執行 BEGIN IMMEDIATE（要取得寫鎖，會卡在 A 的交易外面）就 release → A 先提交，B 隨後讀到新清單。
    wait 的逾時（10 秒）只是失敗保護，會被 assert 抓到。"""

    def __init__(self, a_has_read, release):
        self.a_has_read, self.release, self.timed_out, self._fired = a_has_read, release, False, False
        self.dumps = json.dumps

    def loads(self, s, *a, **k):
        if threading.current_thread().name == "A" and not self._fired:
            self._fired = True
            self.a_has_read.set()
            if not self.release.wait(10):
                self.timed_out = True
        return json.loads(s, *a, **k)


class _ConnProxy:
    def __init__(self, con, release):
        self._con, self._release = con, release

    def execute(self, sql, *a, **k):
        if threading.current_thread().name == "B" and "BEGIN IMMEDIATE" in sql:
            self._release.set()                  # B 已要求寫鎖；接下來它會在 sqlite 裡等 A 提交
        return self._con.execute(sql, *a, **k)

    def __getattr__(self, name):
        return getattr(self._con, name)


class _DbProxy:
    def __init__(self, release):
        self._release = release

    @contextlib.contextmanager
    def connect(self):
        with db_mod.connect() as con:
            yield _ConnProxy(con, self._release)

    def __getattr__(self, name):
        return getattr(db_mod, name)


def _interleave(sb, monkeypatch, a_fn, b_fn):
    a_has_read, release = threading.Event(), threading.Event()
    pj = _PausingJson(a_has_read, release)
    monkeypatch.setattr(sb.testruns, "json", pj)
    monkeypatch.setattr(sb.testruns, "db", _DbProxy(release))
    errs = []

    def run(fn, done=None):
        try:
            fn()
        except BaseException as e:  # noqa: BLE001
            errs.append(e)
        finally:
            if done:
                done.set()
    ta = threading.Thread(target=run, args=(a_fn,), name="A")
    ta.start()
    assert a_has_read.wait(10), "A 沒有走到讀取點"
    tb = threading.Thread(target=run, args=(b_fn, release), name="B")     # B 結束時也 release（舊程式路徑）
    tb.start()
    ta.join(20); tb.join(20)
    assert not ta.is_alive() and not tb.is_alive(), "執行緒沒有結束"
    assert not pj.timed_out, "A 等到逾時才被放行：交錯不是由 B 的行為觸發"
    assert not errs, errs


def test_r08_concurrent_add_add_keeps_both_records(bug_sandbox, write_registry_tc, monkeypatch):
    sb = bug_sandbox
    rid, res_id = _make_result(sb, write_registry_tc, with_evidence=False)
    tr = sb.testruns
    _interleave(sb, monkeypatch,
                lambda: tr.add_evidence(rid, res_id, "a.png", b"aaa", "screenshot", "", "me"),
                lambda: tr.add_evidence(rid, res_id, "b.png", b"bbb", "screenshot", "", "me"))
    monkeypatch.setattr(sb.testruns, "json", json); monkeypatch.setattr(sb.testruns, "db", db_mod)
    ev = _row(sb, rid, res_id)["evidence"]
    assert sorted(e["filename"] for e in ev) == ["a.png", "b.png"]
    assert len(_evidence_files(sb, rid)) == 2          # 每筆紀錄都有對應檔，沒有孤兒檔


def test_r08_concurrent_add_and_remove_neither_loses_the_new_record_nor_resurrects_the_removed(bug_sandbox, write_registry_tc, monkeypatch):
    sb = bug_sandbox
    rid, res_id = _make_result(sb, write_registry_tc)             # 先有一筆 E0
    tr = sb.testruns
    e0 = _row(sb, rid, res_id)["evidence"][0]
    _interleave(sb, monkeypatch,
                lambda: tr.add_evidence(rid, res_id, "new.png", b"new", "screenshot", "", "me"),
                lambda: tr.remove_evidence(rid, res_id, e0["id"]))
    monkeypatch.setattr(sb.testruns, "json", json); monkeypatch.setattr(sb.testruns, "db", db_mod)
    ev = _row(sb, rid, res_id)["evidence"]
    assert [e["filename"] for e in ev] == ["new.png"]
    assert len(_evidence_files(sb, rid)) == 1 and _evidence_files(sb, rid)[0].endswith("new.png")


# ================================================================ R04：交接補做
def _handoffs(read_handoff):
    return [h for h in read_handoff() if h.get("kind") == "handoff"]


def _filing_rows(sb, rid, res_id):
    with sb.db.connect() as con:
        return sb.db.rows(con.execute("SELECT * FROM ticket_executions WHERE ticket_id=? AND kind='bug_filing'", (f"TESTRUN-{rid}/{res_id}",)))


def test_r04_handoff_failure_then_retry_only_completes_handoff(bug_sandbox, write_registry_tc, fake_qaos, write_run, read_handoff, monkeypatch):
    sb = bug_sandbox
    rid, res_id = _make_result(sb, write_registry_tc)
    _fake_cli(sb, fake_qaos["calls"], write_run)
    real_append = sb.qaos_exec._append_handoff

    def boom(rec):
        raise OSError("disk full")
    monkeypatch.setattr(sb.qaos_exec, "_append_handoff", boom)
    with pytest.raises(sb.qaos_bug.BugFileError) as ei:
        sb.qaos_bug.execute(rid, res_id)
    assert "交接" in str(ei.value) and "RUN-20261009-001" in str(ei.value)
    r = _row(sb, rid, res_id)
    assert r["bug_run_id"] == "RUN-20261009-001" and not r["bug_handoff_id"]
    assert _handoffs(read_handoff) == [] and _filing_rows(sb, rid, res_id) == []
    # plan 不再說「這條已經送過」，改為待補交接
    p = sb.qaos_bug.plan(rid, res_id)
    assert p["warnings"] == [] and p["pending_handoff"] is True

    monkeypatch.setattr(sb.qaos_exec, "_append_handoff", real_append)
    calls_before = len(fake_qaos["calls"])
    res = sb.qaos_bug.execute(rid, res_id)
    assert res["ok"] and res["bug_run_id"] == "RUN-20261009-001"
    assert len(fake_qaos["calls"]) == calls_before                 # 沒有重跑任何 CLI
    hs = _handoffs(read_handoff)
    assert len(hs) == 1 and hs[0]["run_id"] == "RUN-20261009-001" and hs[0]["id"] == sb.qaos_exec.stable_handoff_id("bug_filing", "RUN-20261009-001")
    rows = _filing_rows(sb, rid, res_id)
    assert len(rows) == 1 and rows[0]["handoff_id"] == hs[0]["id"] and rows[0]["run_id"] == "RUN-20261009-001"
    assert _row(sb, rid, res_id)["bug_handoff_id"] == hs[0]["id"]
    # 補齊之後才是「已經送過」
    with pytest.raises(sb.qaos_bug.BugFileError) as ei:
        sb.qaos_bug.execute(rid, res_id)
    assert ei.value.status == 409 and "已經送過" in str(ei.value)
    assert len(_handoffs(read_handoff)) == 1


def test_r04_failure_after_handoff_written_does_not_duplicate_handoff(bug_sandbox, write_registry_tc, fake_qaos, write_run, read_handoff, monkeypatch):
    """交接已寫進檔案、但最後記錄完成的那一步失敗：重試不能再寫第二筆（穩定 ID＋寫入前檢查）。"""
    sb = bug_sandbox
    rid, res_id = _make_result(sb, write_registry_tc)
    _fake_cli(sb, fake_qaos["calls"], write_run)
    orig_save = sb.qaos_bug._save

    def flaky_save(result_id, **fields):
        if "bug_handoff_id" in fields:
            raise sqlite3.OperationalError("database is locked")
        return orig_save(result_id, **fields)
    monkeypatch.setattr(sb.qaos_bug, "_save", flaky_save)
    with pytest.raises(sb.qaos_bug.BugFileError):
        sb.qaos_bug.execute(rid, res_id)
    assert len(_handoffs(read_handoff)) == 1 and len(_filing_rows(sb, rid, res_id)) == 1
    monkeypatch.setattr(sb.qaos_bug, "_save", orig_save)
    sb.qaos_bug.execute(rid, res_id)
    assert len(_handoffs(read_handoff)) == 1 and len(_filing_rows(sb, rid, res_id)) == 1
    assert _row(sb, rid, res_id)["bug_handoff_id"]


def test_r04_normal_flow_records_stable_handoff_id(bug_sandbox, write_registry_tc, fake_qaos, write_run, read_handoff):  # 控制案例
    sb = bug_sandbox
    rid, res_id = _make_result(sb, write_registry_tc)
    _fake_cli(sb, fake_qaos["calls"], write_run)
    res = sb.qaos_bug.execute(rid, res_id)
    hid = sb.qaos_exec.stable_handoff_id("bug_filing", "RUN-20261009-001")
    assert res["handoff_id"] == hid and _row(sb, rid, res_id)["bug_handoff_id"] == hid
    assert [h["id"] for h in _handoffs(read_handoff)] == [hid]


def test_r04_migration_marks_previously_completed_filings_as_done(sandbox):
    """升級時：此前開過 bug 且已有執行紀錄的結果，bug_handoff_id 回填成當時的 handoff_id；沒有紀錄的維持待補。"""
    db = sandbox.db
    now = db.now()
    with db.connect() as con:
        rid = con.execute("INSERT INTO test_runs (name, trigger, status, created_at, updated_at) VALUES ('r','manual','running',?,?)", (now, now)).lastrowid
        done = con.execute("INSERT INTO test_results (run_id, testcase_id, result, bug_run_id, created_at, updated_at) VALUES (?, 'TC-A-001','fail','RUN-1',?,?)", (rid, now, now)).lastrowid
        lost = con.execute("INSERT INTO test_results (run_id, testcase_id, result, bug_run_id, created_at, updated_at) VALUES (?, 'TC-A-002','fail','RUN-2',?,?)", (rid, now, now)).lastrowid
        con.execute("INSERT INTO ticket_executions (ticket_id, kind, action, command, exit_code, handoff_id, started_at, ended_at) VALUES (?, 'bug_filing','bug','x',0,'old-h',?,?)",
                    (f"TESTRUN-{rid}/{done}", now, now))
        try:
            con.execute("ALTER TABLE test_results DROP COLUMN bug_handoff_id")
        except sqlite3.OperationalError:
            pytest.skip("這個 SQLite 不支援 DROP COLUMN")
    db.init_db()
    with db.connect() as con:
        got = {r["id"]: r["bug_handoff_id"] for r in db.rows(con.execute("SELECT id, bug_handoff_id FROM test_results"))}
    assert got[done] == "old-h" and got[lost] is None


# ---- 單據 execute（qaos_exec）
def _approval_ready(sandbox, write_run, write_approval, apr="APR-0100", run="RUN-T-100"):
    write_run(run, "WAITING_HUMAN", "T4", [("T4", "RUNNING", None)], waiting_on_approval_id=apr)
    write_approval(apr, run)
    sandbox.tickets.save_draft(apr, "approval", "approve", None, "", None, None)

    def advance(cmd):
        write_run(run, "RUNNING", "T5", [("T4", "DONE", None), ("T5", "READY", "agent-supervisor")])
    return advance


def test_r04_ticket_execute_handoff_failure_then_retry_completes_without_rerunning(sandbox, fake_qaos, write_run, write_approval, read_handoff, monkeypatch):
    advance = _approval_ready(sandbox, write_run, write_approval)
    fake_qaos["side_effect"] = advance
    qe = sandbox.qaos_exec
    real_append = qe._append_handoff
    monkeypatch.setattr(qe, "_append_handoff", lambda rec: (_ for _ in ()).throw(OSError("disk full")))
    with pytest.raises(qe.ExecError) as ei:
        qe.execute("APR-0100")
    assert "已成功執行" in str(ei.value) and "不會重跑" in str(ei.value)
    assert len(fake_qaos["calls"]) == 1 and _handoffs(read_handoff) == []
    assert sandbox.tickets.get_draft("APR-0100")["sent_at"] is None
    rows = qe.executions("APR-0100")
    assert len(rows) == 1 and rows[0]["pending_completion"] is True

    monkeypatch.setattr(qe, "_append_handoff", real_append)
    res = qe.execute("APR-0100")                       # 不經預檢、不重跑指令
    assert res["ok"] and res["completed_pending"] is True and len(fake_qaos["calls"]) == 1
    hs = _handoffs(read_handoff)
    assert len(hs) == 1 and hs[0]["id"] == res["handoff_id"] and hs[0]["handoff_kind"] == "resume_agent" and hs[0]["next_task"] == "T5"
    assert sandbox.tickets.get_draft("APR-0100")["sent_at"] is not None
    rows = qe.executions("APR-0100")
    assert len(rows) == 1 and rows[0]["pending_completion"] is False and rows[0]["handoff_id"] == hs[0]["id"] and "T5" in rows[0]["hint"]


def test_r04_ticket_execute_mark_sent_failure_does_not_duplicate_handoff(sandbox, fake_qaos, write_run, write_approval, read_handoff, monkeypatch):
    fake_qaos["side_effect"] = _approval_ready(sandbox, write_run, write_approval)
    qe = sandbox.qaos_exec
    real = qe.tk.mark_sent
    monkeypatch.setattr(qe.tk, "mark_sent", lambda *a: (_ for _ in ()).throw(sqlite3.OperationalError("database is locked")))
    with pytest.raises(qe.ExecError):
        qe.execute("APR-0100")
    assert len(_handoffs(read_handoff)) == 1
    monkeypatch.setattr(qe.tk, "mark_sent", real)
    qe.execute("APR-0100")
    assert len(_handoffs(read_handoff)) == 1 and len(fake_qaos["calls"]) == 1
    assert sandbox.tickets.get_draft("APR-0100")["sent_at"] is not None


def test_r04_successful_ticket_execute_leaves_no_pending_row(sandbox, fake_qaos, write_run, write_approval, read_handoff):  # 控制案例
    fake_qaos["side_effect"] = _approval_ready(sandbox, write_run, write_approval)
    res = sandbox.qaos_exec.execute("APR-0100")
    assert res["ok"] and res["completed_pending"] is False
    rows = sandbox.qaos_exec.executions("APR-0100")
    assert len(rows) == 1 and rows[0]["pending_completion"] is False and rows[0]["handoff_id"] == res["handoff_id"]


# ================================================================ R10：逾時保留輸出、不宣稱沒改狀態
def test_r10_timeout_keeps_partial_output(sandbox, monkeypatch):
    qe = sandbox.qaos_exec
    monkeypatch.setattr(qe, "_write_guard", lambda: None)

    def timeout(args, **kw):
        raise subprocess.TimeoutExpired(args, 60, output=b"partial stdout \xe4\xb8\xad", stderr=b"partial stderr")      # POSIX 上是 bytes
    monkeypatch.setattr(qe.subprocess, "run", timeout)
    res = qe._run("bin/qaos approve APR-1")
    assert res["exit_code"] == -1 and res["timed_out"] is True
    assert "partial stdout 中" in res["stdout"]
    assert "partial stderr" in res["stderr"] and "逾時" in res["stderr"]


def test_r10_timeout_with_no_output_still_reports(sandbox, monkeypatch):  # 控制案例（output 為 None）
    qe = sandbox.qaos_exec
    monkeypatch.setattr(qe, "_write_guard", lambda: None)
    monkeypatch.setattr(qe.subprocess, "run", lambda args, **kw: (_ for _ in ()).throw(subprocess.TimeoutExpired(args, 60)))
    res = qe._run("bin/qaos approve APR-1")
    assert res["stdout"] == "" and "逾時" in res["stderr"]


def test_r10_ticket_timeout_hint_asks_for_reconciliation_and_status_is_unchanged(sandbox, fake_qaos, write_run, write_approval, read_handoff):
    _approval_ready(sandbox, write_run, write_approval)
    sandbox.qaos_exec._run = lambda cmd: {"command": cmd, "exit_code": -1, "stdout": "half", "stderr": "逾時 60s", "timed_out": True}
    res = sandbox.qaos_exec.execute("APR-0100")                # 沒有丟例外＝HTTP 仍是 200（前端依 ok 判斷）
    assert res["ok"] is False and res["stdout"] == "half"
    assert "結果不確定" in res["hint"] and "bin/qaos operation list --incomplete" in res["hint"]
    assert "沒有改任何狀態" not in res["hint"]
    assert read_handoff() == []


def test_r10_ordinary_failure_hint_no_longer_claims_nothing_changed(sandbox, fake_qaos, write_run, write_approval):
    _approval_ready(sandbox, write_run, write_approval)
    fake_qaos["exit_code"] = 1
    res = sandbox.qaos_exec.execute("APR-0100")
    assert res["ok"] is False and res["exit_code"] == 1
    assert "沒有改任何狀態" not in res["hint"] and "operation list --incomplete" in res["hint"] and "stderr" in res["hint"]
    assert sandbox.qaos_exec.executions("APR-0100")[0]["hint"] == res["hint"]


def test_r10_bug_flow_timeout_is_reported_as_uncertain_with_output(bug_sandbox, write_registry_tc, fake_qaos):
    sb = bug_sandbox
    rid, res_id = _make_result(sb, write_registry_tc)

    def fake(cmd):
        if " evidence add " in cmd:
            return {"command": cmd, "exit_code": 0, "stdout": "EVD-0201", "stderr": ""}
        return {"command": cmd, "exit_code": -1, "stdout": "importing…", "stderr": "逾時 60s", "timed_out": True}
    sb.qaos_exec._run = fake
    with pytest.raises(sb.qaos_bug.BugFileError) as ei:
        sb.qaos_bug.execute(rid, res_id)
    assert ei.value.status == 502                              # 狀態碼不變
    assert "結果不確定" in str(ei.value) and "operation list --incomplete" in str(ei.value) and "importing" in str(ei.value)


# ================================================================ 第 01 輪複審（B2-01～B2-04）
def test_b2_01_delete_run_is_refused_while_a_result_is_being_sent(bug_sandbox, write_registry_tc, fake_qaos, write_run):
    sb = bug_sandbox
    rid, res_id = _make_result(sb, write_registry_tc)
    seen = {}
    _fake_cli(sb, fake_qaos["calls"], write_run)
    inner = sb.qaos_exec._run

    def run_and_try_delete(cmd):
        if " evidence add " in cmd:                          # 送出途中（證據剛登記）有人刪回合
            try:
                sb.testruns.delete_run(rid)
                seen["deleted"] = True
            except sb.testruns.TestRunError as e:
                seen["status"] = e.status
        return inner(cmd)
    sb.qaos_exec._run = run_and_try_delete
    res = sb.qaos_bug.execute(rid, res_id)
    assert seen == {"status": 409}                           # 刪除被擋
    assert res["ok"] and _row(sb, rid, res_id)["bug_run_id"] == "RUN-20261009-001"    # 追蹤資料還在


def test_b2_01_delete_run_with_imported_results_is_refused_and_keeps_evidence(bug_sandbox, write_registry_tc, fake_qaos, write_run):
    sb = bug_sandbox
    rid, res_id = _make_result(sb, write_registry_tc)
    _fake_cli(sb, fake_qaos["calls"], write_run)
    sb.qaos_bug.execute(rid, res_id)
    files = _evidence_files(sb, rid)
    with pytest.raises(sb.testruns.TestRunError) as ei:
        sb.testruns.delete_run(rid)
    assert ei.value.status == 409 and "已匯入 QAOS" in str(ei.value)
    assert sb.testruns.get_run(rid) is not None and _evidence_files(sb, rid) == files


def test_b2_01_delete_run_without_imports_still_works(bug_sandbox, write_registry_tc):  # 控制案例
    sb = bug_sandbox
    rid, _ = _make_result(sb, write_registry_tc)
    sb.testruns.delete_run(rid)
    assert sb.testruns.get_run(rid) is None and _evidence_files(sb, rid) == []


def test_b2_01_router_maps_delete_refusal_to_409(bug_sandbox, write_registry_tc, fake_qaos, write_run):
    from fastapi import HTTPException
    from backend.routers import testruns as router
    sb = bug_sandbox
    rid, res_id = _make_result(sb, write_registry_tc)
    _fake_cli(sb, fake_qaos["calls"], write_run)
    sb.qaos_bug.execute(rid, res_id)
    with pytest.raises(HTTPException) as ei:
        router.delete_run(rid)
    assert ei.value.status_code == 409


def test_b2_01_result_vanishing_mid_send_is_not_reported_as_saved(bug_sandbox, write_registry_tc, fake_qaos, write_run):
    """_save 的 UPDATE 影響 0 列不能當成功（直接刪列模擬別條路徑造成的消失）。"""
    sb = bug_sandbox
    rid, res_id = _make_result(sb, write_registry_tc)
    _fake_cli(sb, fake_qaos["calls"], write_run)
    inner = sb.qaos_exec._run

    def vanish(cmd):
        out = inner(cmd)
        if " execution import " in cmd:
            with sb.db.connect() as con:
                con.execute("DELETE FROM test_results WHERE id=?", (res_id,))
        return out
    sb.qaos_exec._run = vanish
    with pytest.raises(sb.qaos_bug.BugFileError) as ei:
        sb.qaos_bug.execute(rid, res_id)
    assert ei.value.status == 409 and "不存在" in str(ei.value) and "對帳" in str(ei.value)


def test_b2_02_failing_to_record_the_successful_result_is_recoverable(sandbox, fake_qaos, write_run, write_approval, read_handoff, monkeypatch):
    """CLI 已成功、把成功結果寫進 ticket_executions 失敗：同一個 process 重試補寫、完成交接，不重跑、不走回預檢（預檢此時必然 409）。"""
    fake_qaos["side_effect"] = _approval_ready(sandbox, write_run, write_approval)
    qe = sandbox.qaos_exec
    real = qe._record_outcome
    state = {"fail": True}

    def flaky(row_id, res, post, ended, completion, hint="", handoff_id=None):
        if completion == "pending" and state["fail"]:
            raise sqlite3.OperationalError("disk full")
        return real(row_id, res, post, ended, completion, hint, handoff_id)
    monkeypatch.setattr(qe, "_record_outcome", flaky)
    with pytest.raises(qe.ExecError) as ei:
        qe.execute("APR-0100")
    assert ei.value.status == 500 and "已成功執行" in str(ei.value)
    assert len(fake_qaos["calls"]) == 1 and _handoffs(read_handoff) == []
    state["fail"] = False
    res = qe.execute("APR-0100")
    assert res["ok"] and res["completed_pending"] is True and len(fake_qaos["calls"]) == 1
    assert len(_handoffs(read_handoff)) == 1 and sandbox.tickets.get_draft("APR-0100")["sent_at"] is not None
    rows = qe.executions("APR-0100")
    assert len(rows) == 1 and rows[0]["ok"] is True and rows[0]["pending_completion"] is False


def test_b2_02_attempt_is_recorded_before_the_cli_runs(sandbox, fake_qaos, write_run, write_approval):
    fake_qaos["side_effect"] = _approval_ready(sandbox, write_run, write_approval)
    seen = {}
    inner = fake_qaos["side_effect"]

    def peek(cmd):
        seen["rows"] = sandbox.qaos_exec.executions("APR-0100")
        inner(cmd)
    fake_qaos["side_effect"] = peek
    sandbox.qaos_exec.execute("APR-0100")
    assert len(seen["rows"]) == 1 and seen["rows"][0]["completion"] == "started"


def test_b2_02_stale_started_attempt_is_marked_uncertain_and_does_not_block(sandbox, fake_qaos, write_run, write_approval):
    """process 在 CLI 前後中斷留下 started：標成不確定（要對帳），不卡死這張單；之後照一般預檢走。"""
    fake_qaos["side_effect"] = _approval_ready(sandbox, write_run, write_approval)
    qe = sandbox.qaos_exec
    old = qe._start_execution("APR-0100", "approval", "approve", "bin/qaos approve APR-0100", "RUN-T-100", sandbox.db.now())
    res = qe.execute("APR-0100")
    assert res["ok"]
    rows = {r["id"]: r for r in qe.executions("APR-0100")}
    assert rows[old]["completion"] == "abandoned" and "對帳" in rows[old]["hint"] and rows[old]["ok"] is False
    assert len(rows) == 2


def test_b2_02_index_failure_after_success_keeps_the_result_and_retry_completes(real_sm, fake_qaos, monkeypatch, read_handoff):
    """clarification 的 index 重建在成功結果落地『之後』才跑：它拋例外不會丟掉已成功的結果。"""
    sb = real_sm
    _clr(sb.root, "CLR-B2-1", "OPEN")
    sb.tickets.save_draft("CLR-B2-1", "clarification", "ask", None, "", None, {"asked_to": "PM"})
    qe = sb.qaos_exec
    inner = qe._run
    state = {"boom": True}

    def run(cmd):
        if "clarification index" in cmd and state["boom"]:
            raise qe.ExecError(409, "index 逾時")
        return fake_cli(cmd)
    fake_cli = sb.qaos_exec._run          # fake_qaos 已換掉 _run
    monkeypatch.setattr(qe, "_run", run)
    with pytest.raises(qe.ExecError):
        qe.execute("CLR-B2-1")
    rows = qe.executions("CLR-B2-1")
    assert len(rows) == 1 and rows[0]["pending_completion"] is True and rows[0]["exit_code"] == 0
    state["boom"] = False
    res = qe.execute("CLR-B2-1")
    assert res["ok"] and res["completed_pending"] is True and "已重建" in res["hint"]
    assert sum(1 for c in fake_qaos["calls"] if " ask " in f" {c} ") == 1       # 指令本身只跑一次
    assert len(_handoffs(read_handoff)) == 1


def test_b2_03_execution_only_record_failure_is_completed_by_retry(bug_sandbox, write_registry_tc, fake_qaos, write_run, monkeypatch):
    sb = bug_sandbox
    rid, res_id = _make_result(sb, write_registry_tc, result="pass", actual="")
    _fake_cli(sb, fake_qaos["calls"], write_run)
    real = sb.qaos_bug._insert_filing_row
    monkeypatch.setattr(sb.qaos_bug, "_insert_filing_row", lambda *a, **k: (_ for _ in ()).throw(sqlite3.OperationalError("database is locked")))
    with pytest.raises(sb.qaos_bug.BugFileError) as ei:
        sb.qaos_bug.execute(rid, res_id, "execution")
    assert ei.value.status == 500 and "不會重匯" in str(ei.value)
    p = sb.qaos_bug.plan(rid, res_id, "execution")
    assert p["warnings"] == [] and p["pending_record"] is True
    monkeypatch.setattr(sb.qaos_bug, "_insert_filing_row", real)
    n = len(fake_qaos["calls"])
    res = sb.qaos_bug.execute(rid, res_id, "execution")
    assert res["ok"] and len(fake_qaos["calls"]) == n                       # 沒有重匯
    with sb.db.connect() as con:
        assert len(sb.db.rows(con.execute("SELECT * FROM ticket_executions WHERE kind='execution_import'"))) == 1
    with pytest.raises(sb.qaos_bug.BugFileError) as ei:                     # 補齊後才是「已經匯過」
        sb.qaos_bug.execute(rid, res_id, "execution")
    assert ei.value.status == 409 and "已經匯過" in str(ei.value)


def test_b2_03_normally_imported_result_is_not_offered_a_record_completion(bug_sandbox, write_registry_tc, fake_qaos, write_run):  # 控制案例
    sb = bug_sandbox
    rid, res_id = _make_result(sb, write_registry_tc, result="pass", actual="")
    _fake_cli(sb, fake_qaos["calls"], write_run)
    sb.qaos_bug.execute(rid, res_id, "execution")
    p = sb.qaos_bug.plan(rid, res_id, "execution")
    assert p["pending_record"] is False and any("已經匯過" in w for w in p["warnings"])


def test_b2_04_same_second_legitimate_repeat_gets_its_own_handoff(real_sm, fake_qaos, read_handoff, monkeypatch):
    """同一秒內 A、B、A 三次合法的回答：handoff ID 由各次嘗試的 row id 衍生，三次都有自己的交接（舊做法第 1、3 次同 ID，第 3 次被當成已交接而吞掉）。"""
    sb = real_sm
    p = _clr(sb.root, "CLR-B2-2", "OPEN")
    fake_qaos["side_effect"] = _answer_effect(sb, p)
    monkeypatch.setattr(sb.db, "now", lambda: "2026-10-09T10:00:00Z")
    for text in ("答案 A", "答案 B", "答案 A"):
        _answer_draft(sb, "CLR-B2-2", text)
        assert sb.qaos_exec.execute("CLR-B2-2")["ok"]
    ids = [h["id"] for h in _handoffs(read_handoff)]
    assert len(ids) == 3 and len(set(ids)) == 3
    assert sorted(r["handoff_id"] for r in sb.qaos_exec.executions("CLR-B2-2")) == sorted(ids)
