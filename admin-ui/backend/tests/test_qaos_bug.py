"""M7b：qaos_bug.plan / execute（NG 送 QAOS 開 bug）。全部在假根，bin/qaos 換成假的。"""
import json

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


def _make_run_with_fail(sb, write_registry_tc, with_evidence=True, actual="畫面卡住"):
    """直接寫 test_runs / test_results（略過 final JSON 快照流程），一條 fail。"""
    write_registry_tc("TC-AREA-042", 1, "SPEC-AREA-001", spec_version="0.3")
    with sb.db.connect() as con:
        cur = con.execute("INSERT INTO test_runs (name, trigger, status, environment, build, created_by, import_all, created_at, updated_at) VALUES ('r','manual','running','stage','b1','me',0,?,?)", (sb.db.now(), sb.db.now()))
        rid = cur.lastrowid
        cur = con.execute("INSERT INTO test_results (run_id, position, testcase_id, testcase_version, group_key, title, result, actual_result, executed_at, created_at, updated_at) VALUES (?,0,'TC-AREA-042',1,'AREA','t','fail',?,?,?,?)", (rid, actual, sb.db.now(), sb.db.now(), sb.db.now()))
        res_id = cur.lastrowid
    if with_evidence:
        sb.testruns.add_evidence(rid, res_id, "shot.png", b"\x89PNG fake", "screenshot", "卡住畫面", "me")
    return rid, res_id


def test_plan_lists_three_steps_and_writes(bug_sandbox, write_registry_tc):
    rid, res_id = _make_run_with_fail(bug_sandbox, write_registry_tc)
    p = bug_sandbox.qaos_bug.plan(rid, res_id)
    assert p["warnings"] == []
    assert [s["kind"] for s in p["steps"]] == ["evidence", "execution", "run"]
    assert p["meta"] == {"spec_id": "SPEC-AREA-001", "spec_version": "0.3", "version": 1}
    assert "--input spec_id=SPEC-AREA-001" in p["steps"][2]["command"]
    assert "--environment stage" in p["steps"][1]["command"]
    assert any("evidence/testrun-" in w for w in p["writes"])


def test_plan_warns_without_evidence_or_actual(bug_sandbox, write_registry_tc):
    rid, res_id = _make_run_with_fail(bug_sandbox, write_registry_tc, with_evidence=False, actual="")
    p = bug_sandbox.qaos_bug.plan(rid, res_id)
    assert any("實際結果" in w for w in p["warnings"])
    assert any("證據" in w for w in p["warnings"])
    with pytest.raises(bug_sandbox.qaos_bug.BugFileError) as ei:
        bug_sandbox.qaos_bug.execute(rid, res_id)
    assert ei.value.status == 409


def test_execute_runs_three_commands_and_records_ids(bug_sandbox, write_registry_tc, fake_qaos, read_handoff, write_run):
    rid, res_id = _make_run_with_fail(bug_sandbox, write_registry_tc)
    outputs = {"evidence": "EVD-0101", "execution": "EXE-20260918-007", "run": "RUN-20260918-030 RUNNING current_task=T1"}

    def fake(cmd):
        fake_qaos["calls"].append(cmd)
        if " evidence add " in cmd: out = outputs["evidence"]
        elif " execution import " in cmd: out = outputs["execution"]
        else:
            write_run("RUN-20260918-030", "RUNNING", "T1", [("T0", "DONE", None), ("T1", "READY", "agent-bug-analyst")], workflow_id="spec-to-bug")
            out = outputs["run"]
        return {"command": cmd, "exit_code": 0, "stdout": out, "stderr": ""}
    bug_sandbox.qaos_exec._run = fake  # fake_qaos 已 monkeypatch 過 _run，這裡覆蓋成有輸出的版本
    res = bug_sandbox.qaos_bug.execute(rid, res_id)
    assert res["ok"] and res["evidence_ids"] == ["EVD-0101"] and res["execution_id"] == "EXE-20260918-007" and res["bug_run_id"] == "RUN-20260918-030"
    calls = fake_qaos["calls"]
    assert calls[0].startswith("bin/qaos evidence add --type screenshot --file")
    assert calls[1].startswith("bin/qaos execution import --testcase-id TC-AREA-042 --result fail") and "--evidence EVD-0101" in calls[1]
    assert calls[2].startswith("bin/qaos run new spec-to-bug") and "execution_id=EXE-20260918-007" in calls[2] and '"EVD-0101"' in calls[2]
    # 結果列記下三個編號
    r = next(x for x in bug_sandbox.testruns.get_run(rid)["results"] if x["id"] == res_id)
    assert r["bug_run_id"] == "RUN-20260918-030" and r["qaos_execution_id"] == "EXE-20260918-007" and r["qaos_evidence_ids"] == ["EVD-0101"]
    # 交接：resume_agent、指定 session、run 推進到 T1
    h = [x for x in read_handoff() if x.get("kind") == "handoff"]
    assert len(h) == 1 and h[0]["handoff_kind"] == "resume_agent" and h[0]["session_id"] == "sess-A" and h[0]["run_id"] == "RUN-20260918-030" and h[0]["next_task"] == "T1"


def test_execute_stops_at_first_failure_and_keeps_partial_ids(bug_sandbox, write_registry_tc, fake_qaos, read_handoff):
    """證據登記成功、execution import 失敗 → 502、不寫 handoff、EVD 編號保留（重送不重複登記證據）。"""
    rid, res_id = _make_run_with_fail(bug_sandbox, write_registry_tc)

    def fake(cmd):
        fake_qaos["calls"].append(cmd)
        if " evidence add " in cmd: return {"command": cmd, "exit_code": 0, "stdout": "EVD-0102", "stderr": ""}
        return {"command": cmd, "exit_code": 1, "stdout": "", "stderr": "Execution 不符 schema"}
    bug_sandbox.qaos_exec._run = fake
    with pytest.raises(bug_sandbox.qaos_bug.BugFileError) as ei:
        bug_sandbox.qaos_bug.execute(rid, res_id)
    assert ei.value.status == 502
    assert read_handoff() == []
    r = next(x for x in bug_sandbox.testruns.get_run(rid)["results"] if x["id"] == res_id)
    assert r["qaos_evidence_ids"] == ["EVD-0102"] and r["qaos_execution_id"] is None and r["bug_run_id"] is None
    # 重送：不再跑 evidence add
    fake_qaos["calls"].clear()
    with pytest.raises(bug_sandbox.qaos_bug.BugFileError):
        bug_sandbox.qaos_bug.execute(rid, res_id)
    assert all(" evidence add " not in c for c in fake_qaos["calls"])


def test_already_filed_is_rejected(bug_sandbox, write_registry_tc):
    rid, res_id = _make_run_with_fail(bug_sandbox, write_registry_tc)
    bug_sandbox.qaos_bug._save(res_id, bug_run_id="RUN-20260918-031", bug_handoff_id="h1")   # 交接完成才算「已送過」（B2 R04）
    p = bug_sandbox.qaos_bug.plan(rid, res_id)
    assert any("已經送過" in w for w in p["warnings"])
