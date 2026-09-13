"""Bug OPEN 之後：resolve（外部修復登記）→ verify（複測需 Evidence）→ close；複測 fail → reopen。沿用 test_13 建立的 BUG-AUTH-001（已 IN_PROGRESS）。"""
import pytest
from tools.qaos import store, bug_lifecycle as bl
from tools.qaos.cli import main as cli
from tools.qaos.engine import EngineError

def _bug(): return store.load(store.find_bug("BUG-AUTH-001"))

def test_16_resolve_from_in_progress_records_external_ref():
    b = bl.resolve("BUG-AUTH-001", "oscar@example.com", "共用表單 #42", note="後端補長度檢查", fixed_by="RD-Kyle")
    assert b["status"] == "RESOLVED" and b["external_ref"] == "共用表單 #42" and b["resolved_at"]

def test_17_verify_requires_evidence_and_matching_tc(capsys):
    b = _bug(); tc = b["testcase_id"]
    cli(["execution", "import", "--testcase-id", tc, "--testcase-version", "1", "--result", "pass", "--environment", "stage", "--by", "oscar@example.com"]); exe_no_ev = capsys.readouterr().out.strip()
    with pytest.raises(EngineError): bl.verify("BUG-AUTH-001", exe_no_ev, "oscar@example.com")            # 無 Evidence
    cli(["evidence", "add", "--type", "screenshot", "--inline", "retest-fail", "--owner", "retest", "--by", "oscar@example.com"]); ev = capsys.readouterr().out.strip()
    cli(["execution", "import", "--testcase-id", "TC-AUTH-999", "--testcase-version", "1", "--result", "pass", "--environment", "stage", "--evidence", ev, "--by", "oscar@example.com"]); exe_wrong_tc = capsys.readouterr().out.strip()
    with pytest.raises(EngineError): bl.verify("BUG-AUTH-001", exe_wrong_tc, "oscar@example.com")         # TC 不符
    cli(["execution", "import", "--testcase-id", tc, "--testcase-version", "1", "--result", "fail", "--environment", "stage", "--evidence", ev, "--by", "oscar@example.com"]); exe_fail = capsys.readouterr().out.strip()
    b = bl.verify("BUG-AUTH-001", exe_fail, "oscar@example.com"); assert b["status"] == "OPEN" and b["reopen_count"] == 1   # 複測 fail → reopen
    with pytest.raises(EngineError): bl.close("BUG-AUTH-001", "oscar@example.com")                         # OPEN 不能 close

def test_18_resolve_again_verify_pass_and_close():
    bl.resolve("BUG-AUTH-001", "oscar@example.com", "共用表單 #42 (第二次)")
    b = _bug(); tc = b["testcase_id"]
    from tools.qaos.cli import main as cli; import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf): cli(["evidence", "add", "--type", "screenshot", "--inline", "retest-pass", "--owner", "retest", "--by", "oscar@example.com"])
    ev = buf.getvalue().strip(); buf = io.StringIO()
    with contextlib.redirect_stdout(buf): cli(["execution", "import", "--testcase-id", tc, "--testcase-version", "1", "--result", "pass", "--environment", "stage", "--evidence", ev, "--by", "oscar@example.com"])
    exe = buf.getvalue().strip()
    assert bl.verify("BUG-AUTH-001", exe, "oscar@example.com")["status"] == "VERIFIED"
    b = bl.close("BUG-AUTH-001", "oscar@example.com"); assert b["status"] == "CLOSED" and len(b["retest_execution_ids"]) == 2
    assert [h["to_status"] for h in b["history"]][-6:] == ["RESOLVED", "OPEN", "IN_PROGRESS", "RESOLVED", "VERIFIED", "CLOSED"]
    apr = store.load(f"approvals/{b['history'][-1]['trigger']}.yaml"); assert apr["type"] == "CLOSE_BUG" and apr["decision"]["decided_by"] == "oscar@example.com"
