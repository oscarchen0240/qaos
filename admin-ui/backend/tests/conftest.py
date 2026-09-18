"""admin-ui 工程測試夾具（PROMPT-test-automation-coverage-audit A2）。

原則：
- 全部 function scope：每個測試一個獨立的假專案根（tmp_path），teardown 由 pytest 回收，不留 .warroom 殘渣。
- 夾具裡不放 assert。
- 透過 monkeypatch 把服務模組讀寫的目錄指到假根（approvals/、runs/、.warroom/、admin.db），不碰真專案。
- hook 測試用 subprocess 跑 `admin-ui/hooks/*.py`，stdin 餵 JSON，CLAUDE_PROJECT_DIR 指向假根（跟 Claude Code 實際呼叫方式一致）。
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest
import yaml

ADMIN_DIR = pathlib.Path(__file__).resolve().parents[2]
HOOKS_DIR = ADMIN_DIR / "hooks"
if str(ADMIN_DIR) not in sys.path:
    sys.path.insert(0, str(ADMIN_DIR))


# ---------- 假專案根 ----------
@pytest.fixture
def qaos_root(tmp_path: pathlib.Path) -> pathlib.Path:
    """最小 QAOS 專案骨架：runs/ approvals/ .warroom/ workflows/state-machines.yaml。"""
    for d in ("runs", "approvals", "clarifications", "bugs", ".warroom", "workflows", "testcases/registry", "testcases/versions", "admin-ui/data"):
        (tmp_path / d).mkdir(parents=True, exist_ok=True)
    (tmp_path / "workflows" / "state-machines.yaml").write_text("machines: {}\n", encoding="utf-8")
    return tmp_path


@pytest.fixture
def write_run(qaos_root: pathlib.Path):
    """寫一個最小 run.yaml。tasks: [(task_id, status, agent_id)]。"""
    def _write(run_id: str, status: str, current: str | None, tasks: list[tuple[str, str, str | None]], **extra) -> pathlib.Path:
        d = qaos_root / "runs" / run_id
        d.mkdir(parents=True, exist_ok=True)
        doc = {
            "run_id": run_id, "workflow_id": extra.get("workflow_id", "spec-to-testcase"), "status": status,
            "input": {"spec_id": extra.get("spec_id", "SPEC-TEST-001"), "spec_version": "0.1", "initiated_by": "tester@example.com"},
            "initiated_by": "tester@example.com", "created_at": "2026-09-18T00:00:00Z", "updated_at": "2026-09-18T00:10:00Z",
            "current_task_id": current, "tasks": [{"task_id": t, "type": "agent", "agent_id": a, "status": s, "iteration": 0, "history": []} for t, s, a in tasks],
            "history": [],
        }
        if extra.get("waiting_on_approval_id"):
            doc["waiting_on_approval_id"] = extra["waiting_on_approval_id"]
        (d / "run.yaml").write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), encoding="utf-8")
        return d / "run.yaml"
    return _write


@pytest.fixture
def write_approval(qaos_root: pathlib.Path):
    def _write(apr_id: str, run_id: str, status: str = "PENDING", apr_type: str = "ACTIVATE_TESTCASE", batch_items: list[dict] | None = None, decision: dict | None = None) -> pathlib.Path:
        doc = {"approval_id": apr_id, "type": apr_type, "run_id": run_id, "task_id": "T4", "status": status,
               "summary": f"{apr_id} test", "impact": [], "artifact_ids": [], "trace": [],
               "options": [{"key": "approve", "label": "核准"}, {"key": "reject", "label": "退回"}],
               "batch_items": batch_items or [], "requested_by": "agent-supervisor", "requested_at": "2026-09-18T00:05:00Z"}
        if decision:
            doc["decision"] = decision
        p = qaos_root / "approvals" / f"{apr_id}.yaml"
        p.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), encoding="utf-8")
        return p
    return _write


@pytest.fixture
def handoff_file(qaos_root: pathlib.Path) -> pathlib.Path:
    return qaos_root / ".warroom" / "handoff.jsonl"


@pytest.fixture
def write_handoff(handoff_file: pathlib.Path):
    """append 一筆 handoff（kind=handoff）；回傳 id。"""
    def _write(hid: str, session_id: str, run_id: str, **extra) -> str:
        rec = {"kind": "handoff", "id": hid, "ts": "2026-09-18T00:20:00Z", "ticket_id": extra.get("ticket_id", "APR-0001"), "ticket_kind": "approval",
               "action": extra.get("action", "approve"), "command": "bin/qaos approve ...", "exit_code": 0, "run_id": run_id,
               "run_status_after": extra.get("run_status_after", "RUNNING"), "next_task": extra.get("next_task", "T3"), "next_agent": extra.get("next_agent", "agent-test-validator"),
               "session_id": session_id, "hint": "", "by": "tester@example.com"}
        rec.update({k: v for k, v in extra.items() if k not in rec})
        with open(handoff_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return hid
    return _write


@pytest.fixture
def read_handoff(handoff_file: pathlib.Path):
    def _read() -> list[dict]:
        if not handoff_file.exists():
            return []
        return [json.loads(l) for l in handoff_file.read_text(encoding="utf-8").splitlines() if l.strip()]
    return _read


# ---------- hook 執行 ----------
@pytest.fixture
def run_hook(qaos_root: pathlib.Path):
    """跑 hooks/<name>.py，stdin 餵 payload，回 (returncode, stdout, stderr)。"""
    def _run(name: str, payload: dict | str) -> tuple[int, str, str]:
        raw = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)
        env = {**os.environ, "CLAUDE_PROJECT_DIR": str(qaos_root)}
        r = subprocess.run([sys.executable, str(HOOKS_DIR / name)], input=raw, capture_output=True, text=True, env=env, timeout=20)
        return r.returncode, r.stdout, r.stderr
    return _run


# ---------- 服務沙盒：把 backend 各模組的目錄指到假根 ----------
@pytest.fixture
def sandbox(qaos_root: pathlib.Path, monkeypatch: pytest.MonkeyPatch):
    """回傳已重新指向假根的模組集合。DB 用假根下的 admin-ui/data/admin.db。"""
    from backend import db
    from backend.services import qaos_exec, runs, tickets

    data_dir = qaos_root / "admin-ui" / "data"
    monkeypatch.setattr(db, "DATA_DIR", data_dir)
    monkeypatch.setattr(db, "DB_PATH", data_dir / "admin.db")
    monkeypatch.setattr(runs, "RUNS_DIR", qaos_root / "runs")
    monkeypatch.setattr(runs, "_cache", {})
    monkeypatch.setattr(tickets, "APR_DIR", qaos_root / "approvals")
    monkeypatch.setattr(tickets, "CLR_DIR", qaos_root / "clarifications")
    monkeypatch.setattr(tickets, "BUG_DIR", qaos_root / "bugs")
    monkeypatch.setattr(tickets, "SM_PATH", qaos_root / "workflows" / "state-machines.yaml")
    monkeypatch.setattr(tickets, "MEMO_DIR", qaos_root / ".warroom" / "recommendations")
    monkeypatch.setattr(tickets, "PROJECT_ROOT", qaos_root)
    monkeypatch.setattr(tickets, "_cache", {})
    monkeypatch.setattr(qaos_exec, "PROJECT_ROOT", qaos_root)
    monkeypatch.setattr(qaos_exec, "WARROOM_DIR", qaos_root / ".warroom")
    monkeypatch.setattr(qaos_exec, "HANDOFF_FILE", qaos_root / ".warroom" / "handoff.jsonl")
    monkeypatch.setattr(qaos_exec, "_owner_session", lambda run_id: "sess-A" if run_id else None)
    db.init_db()

    class Box:
        pass
    box = Box()
    box.db, box.runs, box.tickets, box.qaos_exec, box.root = db, runs, tickets, qaos_exec, qaos_root
    return box


@pytest.fixture
def fake_qaos(sandbox, monkeypatch: pytest.MonkeyPatch):
    """把 qaos_exec._run 換成假的 bin/qaos：記錄被呼叫的指令，可設定 exit code 與副作用。"""
    calls: list[str] = []
    state = {"exit_code": 0, "side_effect": None}

    def _fake(cmd: str) -> dict:
        calls.append(cmd)
        if state["side_effect"]:
            state["side_effect"](cmd)
        return {"command": cmd, "exit_code": state["exit_code"], "stdout": "ok" if state["exit_code"] == 0 else "", "stderr": "" if state["exit_code"] == 0 else "boom"}

    monkeypatch.setattr(sandbox.qaos_exec, "_run", _fake)
    state["calls"] = calls
    return state
