"""A6 #4–#6：handoff_relay（Stop / UserPromptSubmit）。用 subprocess 跑真實腳本。"""
import json


def _consumed(recs):
    return [r for r in recs if r.get("kind") == "consumed"]


def test_stop_blocks_when_run_running_and_task_ready_and_consumes_only_that_one(run_hook, write_run, write_handoff, read_handoff):
    """#4 RUNNING + current task READY → stdout decision=block；只 consume 這一筆。"""
    write_run("RUN-A", "RUNNING", "T3", [("T2", "DONE", "agent-test-designer"), ("T3", "READY", "agent-test-validator")])
    write_run("RUN-B", "COMPLETED", "T5", [("T5", "DONE", "agent-supervisor")])
    write_handoff("h-resume", "sess-A", "RUN-A")
    write_handoff("h-notify", "sess-A", "RUN-B", run_status_after="COMPLETED", handoff_kind="notify_only")
    rc, out, _ = run_hook("handoff_relay.py", {"hook_event_name": "Stop", "session_id": "sess-A"})
    assert rc == 0
    payload = json.loads(out.strip())
    assert payload["decision"] == "block"
    assert "RUN-A" in payload["reason"] and "T3" in payload["reason"]
    consumed = _consumed(read_handoff())
    assert [c["handoff_id"] for c in consumed] == ["h-resume"]
    assert consumed[0]["note"] == "resumed"


def test_stop_does_not_swallow_pending_when_run_completed(run_hook, write_run, write_handoff, read_handoff):
    """#5 run COMPLETED / notify_only → 不輸出 block，也禁止 consumed/no-op 吃掉 pending。"""
    write_run("RUN-B", "COMPLETED", "T5", [("T5", "DONE", "agent-supervisor")])
    write_handoff("h-notify", "sess-A", "RUN-B", run_status_after="COMPLETED", handoff_kind="notify_only")
    rc, out, _ = run_hook("handoff_relay.py", {"hook_event_name": "Stop", "session_id": "sess-A"})
    assert rc == 0
    assert out.strip() == ""
    assert _consumed(read_handoff()) == []


def test_user_prompt_submit_shows_pending_and_marks_notified(run_hook, write_run, write_handoff, read_handoff):
    """notify_only 由 UserPromptSubmit 顯示後才算送達（consumed note=notified）；resume_agent 的不在這裡 consume。"""
    write_run("RUN-A", "RUNNING", "T3", [("T3", "READY", "agent-test-validator")])
    write_run("RUN-B", "COMPLETED", "T5", [("T5", "DONE", "agent-supervisor")])
    write_handoff("h-resume", "sess-A", "RUN-A")
    write_handoff("h-notify", "sess-A", "RUN-B", run_status_after="COMPLETED", handoff_kind="notify_only")
    rc, out, _ = run_hook("handoff_relay.py", {"hook_event_name": "UserPromptSubmit", "session_id": "sess-A"})
    assert rc == 0
    assert "QAOS 指揮台交接" in out and "RUN-A" in out and "RUN-B" in out
    consumed = _consumed(read_handoff())
    assert [(c["handoff_id"], c["note"]) for c in consumed] == [("h-notify", "notified")]


def test_stop_hook_active_never_blocks(run_hook, write_run, write_handoff, read_handoff):
    """#6 stop_hook_active=true → 不 block、不 consume（防迴圈）。"""
    write_run("RUN-A", "RUNNING", "T3", [("T3", "READY", "agent-test-validator")])
    write_handoff("h-resume", "sess-A", "RUN-A")
    rc, out, _ = run_hook("handoff_relay.py", {"hook_event_name": "Stop", "session_id": "sess-A", "stop_hook_active": True})
    assert rc == 0
    assert out.strip() == ""
    assert _consumed(read_handoff()) == []


def test_other_session_is_ignored(run_hook, write_run, write_handoff, read_handoff):
    write_run("RUN-A", "RUNNING", "T3", [("T3", "READY", "agent-test-validator")])
    write_handoff("h-resume", "sess-A", "RUN-A")
    rc, out, _ = run_hook("handoff_relay.py", {"hook_event_name": "Stop", "session_id": "sess-B"})
    assert rc == 0 and out.strip() == ""
    assert _consumed(read_handoff()) == []


def test_garbage_stdin_exits_zero(run_hook):
    rc, out, _ = run_hook("handoff_relay.py", "not json {")
    assert rc == 0 and out.strip() == ""
