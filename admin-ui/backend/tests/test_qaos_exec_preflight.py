"""A6 #1–#3：qaos_exec 預檢與 handoff 寫入。"""
import pytest


def _draft(sandbox, apr_id: str, decision: str = "approve"):
    return sandbox.tickets.save_draft(apr_id, "approval", decision, None, "", None, None)


def test_non_pending_approval_is_409_and_writes_nothing(sandbox, fake_qaos, write_run, write_approval, read_handoff):
    """#1 APR 非 PENDING → 409、不寫 handoff、不改 run。"""
    write_run("RUN-T-001", "COMPLETED", None, [("T4", "DONE", None)])
    p = write_approval("APR-0001", "RUN-T-001", status="DECIDED", decision={"decision": "approve", "decided_by": "x", "decided_at": "2026-09-18T00:06:00Z"})
    before = p.read_text(encoding="utf-8")
    _draft(sandbox, "APR-0001")
    with pytest.raises(sandbox.qaos_exec.ExecError) as ei:
        sandbox.qaos_exec.execute("APR-0001")
    assert ei.value.status == 409
    assert fake_qaos["calls"] == []
    assert read_handoff() == []
    assert p.read_text(encoding="utf-8") == before


def test_run_not_waiting_human_is_409(sandbox, fake_qaos, write_run, write_approval, read_handoff):
    """#1 延伸：APR PENDING 但 run 不在 WAITING_HUMAN → 409（避免與 QA session 同時寫 run.yaml）。"""
    write_run("RUN-T-002", "RUNNING", "T3", [("T3", "READY", "agent-test-validator")])
    write_approval("APR-0002", "RUN-T-002", status="PENDING")
    _draft(sandbox, "APR-0002")
    with pytest.raises(sandbox.qaos_exec.ExecError) as ei:
        sandbox.qaos_exec.execute("APR-0002")
    assert ei.value.status == 409
    assert fake_qaos["calls"] == []
    assert read_handoff() == []


def test_failed_execution_does_not_append_handoff(sandbox, fake_qaos, write_run, write_approval, read_handoff):
    """#2 執行失敗（exit != 0）→ 不 append handoff、不 mark_sent。"""
    write_run("RUN-T-003", "WAITING_HUMAN", "T4", [("T4", "RUNNING", None)], waiting_on_approval_id="APR-0003")
    write_approval("APR-0003", "RUN-T-003")
    _draft(sandbox, "APR-0003")
    fake_qaos["exit_code"] = 1
    res = sandbox.qaos_exec.execute("APR-0003")
    assert res["ok"] is False and res["exit_code"] == 1
    assert read_handoff() == []
    assert sandbox.tickets.get_draft("APR-0003")["sent_at"] is None
    assert len(fake_qaos["calls"]) == 1 and fake_qaos["calls"][0].startswith("bin/qaos approve APR-0003")


def test_successful_execution_appends_handoff_with_required_fields(sandbox, fake_qaos, write_run, write_approval, read_handoff):
    """#3 執行成功 → append kind=handoff，欄位含 session_id / run_id / action；run 推進到 READY task 時 handoff_kind=resume_agent。"""
    write_run("RUN-T-004", "WAITING_HUMAN", "T4", [("T4", "RUNNING", None)], waiting_on_approval_id="APR-0004")
    write_approval("APR-0004", "RUN-T-004")
    _draft(sandbox, "APR-0004")

    def advance(cmd):  # 假 bin/qaos 的副作用：核准後 run 推進到 T5 READY
        write_run("RUN-T-004", "RUNNING", "T5", [("T4", "DONE", None), ("T5", "READY", "agent-supervisor")])
    fake_qaos["side_effect"] = advance
    res = sandbox.qaos_exec.execute("APR-0004")
    assert res["ok"] is True
    recs = read_handoff()
    assert len(recs) == 1
    h = recs[0]
    assert h["kind"] == "handoff"
    assert h["session_id"] == "sess-A"
    assert h["run_id"] == "RUN-T-004"
    assert h["action"] == "approve"
    assert h["next_task"] == "T5"
    assert h["handoff_kind"] == "resume_agent"
    assert sandbox.tickets.get_draft("APR-0004")["sent_at"] is not None


def test_completed_run_handoff_is_notify_only(sandbox, fake_qaos, write_run, write_approval, read_handoff):
    """#3 延伸：核准後 run 直接 COMPLETED → handoff_kind=notify_only（沒有 agent task 要接）。"""
    write_run("RUN-T-005", "WAITING_HUMAN", "T4", [("T4", "RUNNING", None)], waiting_on_approval_id="APR-0005")
    write_approval("APR-0005", "RUN-T-005")
    _draft(sandbox, "APR-0005")
    fake_qaos["side_effect"] = lambda cmd: write_run("RUN-T-005", "COMPLETED", "T5", [("T4", "DONE", None), ("T5", "DONE", "agent-supervisor")])
    res = sandbox.qaos_exec.execute("APR-0005")
    assert res["ok"] is True
    assert read_handoff()[0]["handoff_kind"] == "notify_only"


def test_missing_draft_is_409(sandbox, fake_qaos, write_run, write_approval):
    write_run("RUN-T-006", "WAITING_HUMAN", "T4", [("T4", "RUNNING", None)])
    write_approval("APR-0006", "RUN-T-006")
    with pytest.raises(sandbox.qaos_exec.ExecError) as ei:
        sandbox.qaos_exec.execute("APR-0006")
    assert ei.value.status == 409
    assert fake_qaos["calls"] == []
