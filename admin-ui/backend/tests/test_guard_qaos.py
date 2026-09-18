"""A6 #7：guard_qaos（PreToolUse Bash）。人工決定類 bin/qaos 指令 → permissionDecision=ask；其他不輸出。"""
import json
import pytest


@pytest.mark.parametrize("cmd", [
    "bin/qaos approve APR-0001 --decision approve --by me",
    "cd /x && bin/qaos approve APR-0001 --decision reject --by me 2>&1",
    "bin/qaos clarification answer CLR-X --answer 'y' --by me",
    "bin/qaos clarification ask CLR-X --to pm --by me",
    "bin/qaos bug close BUG-X --by me",
    "bin/qaos bug resolve BUG-X --external-ref J-1 --by me",
    "bin/qaos bug transition BUG-X --to IN_PROGRESS --by me",
])
def test_human_decision_commands_ask(run_hook, cmd):
    rc, out, _ = run_hook("guard_qaos.py", {"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": cmd}})
    assert rc == 0
    payload = json.loads(out.strip())
    hso = payload["hookSpecificOutput"]
    assert hso["hookEventName"] == "PreToolUse"
    assert hso["permissionDecision"] == "ask"
    assert "指揮台" in hso["permissionDecisionReason"]


@pytest.mark.parametrize("cmd", [
    "bin/qaos tc-export CASHOUT",
    "bin/qaos run show RUN-20260918-011",
    "bin/qaos approvals --all",
    "bin/qaos clarification list",
    "pytest tests/ -q",
])
def test_other_commands_pass_through(run_hook, cmd):
    rc, out, _ = run_hook("guard_qaos.py", {"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": cmd}})
    assert rc == 0 and out.strip() == ""


def test_non_bash_tool_and_garbage_pass_through(run_hook):
    rc, out, _ = run_hook("guard_qaos.py", {"hook_event_name": "PreToolUse", "tool_name": "Write", "tool_input": {"file_path": "x"}})
    assert rc == 0 and out.strip() == ""
    rc, out, _ = run_hook("guard_qaos.py", "{{{")
    assert rc == 0 and out.strip() == ""
