"""迭代規則：structural retry 不計入 semantic 迭代；HUMAN_OVERRIDE reject 後 Validator task 可再跑。"""
import pytest
from tools.qaos import store, engine
from tests import helpers as H
from tests.test_wf_y_negative_coverage import _tcs, _submit_design

def _validator_fail(rid, did, rm_aid, it):
    issue = {"testcase_id": "*", "issue_type": "other", "severity": "major", "violated_requirement": None, "spec_reference": None, "evidence": "x", "explanation": "x", "recommended_change": "x"}
    _, p = H.write_artifact(rid, "T3", "agent-test-validator", "TestValidationReport", H.validation_report(did, rm_aid, "FAIL", [issue]), [{"entity_type": "Artifact", "id": did}], {"type": "TestCaseDraft", "ids": [did]}, "validation", iteration=it)
    assert engine.submit(rid, "T3", str(p))[0]; return engine.evaluate_gate(rid, "T3")

def test_40_structural_retry_does_not_consume_semantic_iterations():
    run = engine.new_run("spec-to-testcase", {"spec_id": "SPEC-NEG-001", "spec_version": "1.0"}, "oscar@example.com"); rid = run["run_id"]
    rm_aid = store.load(store.requirements_path("SPEC-NEG-001", "1.0"))["source_artifact_id"]
    # 3 次 structural INVALID（引用不存在的 REQ）→ NEEDS_DECISION
    for i in range(3):
        tcs, _ = _tcs(prefix=f"01F{i}ZZZZZZZZZZZZZZZZZZZZZ"[:25])
        tcs[0]["requirement_ids"] = ["REQ-NEG-999"]
        _, p = H.write_artifact(rid, "T2", "agent-test-designer", "TestCaseDraft", {"mode": "spec", "spec_id": "SPEC-NEG-001", "spec_version": "1.0", "testcases": tcs}, [{"entity_type": "Requirement", "id": "REQ-NEG-999"}], {"type": "x", "ids": []}, "test-design")
        assert not engine.submit(rid, "T2", str(p))[0]
    run = engine.load_run(rid); assert run["status"] == "WAITING_HUMAN"
    apr = store.load(f"approvals/{run['waiting_on_approval_id']}.yaml"); assert apr["type"] == "NEEDS_DECISION"
    engine.approve(apr["approval_id"], "approve", "oscar@example.com", selected_option="retry")
    assert engine.load_run(rid)["tasks"][1]["iteration"] == 0   # structural retry 不計入
    # 正常 Draft → Validator FAIL ×3 → HUMAN_OVERRIDE
    for it in range(3):
        tcs, _ = _tcs(prefix=f"01G{it}ZZZZZZZZZZZZZZZZZZZZZ"[:25]); lock = tcs[3]
        lock["assumptions"] = [{"text": "假設", "requirement_id": "REQ-NEG-003", "needs_human_confirmation": True}]
        did, r = _submit_design(rid, tcs, iteration=it); assert r["result"] == "PASS"
        r = _validator_fail(rid, did, rm_aid, it); assert r["result"] == "FAIL"
    run = engine.load_run(rid); apr = store.load(f"approvals/{run['waiting_on_approval_id']}.yaml")
    assert apr["type"] == "HUMAN_OVERRIDE" and run["tasks"][1]["iteration"] == 3
    # Human：再給一次 → T2 READY、T3 PENDING，且 T3 可再提交
    engine.approve(apr["approval_id"], "reject", "oscar@example.com", rationale="再給一次")
    run = engine.load_run(rid); assert run["tasks"][1]["status"] == "READY" and run["tasks"][2]["status"] == "PENDING"
    tcs, _ = _tcs(prefix="01H0ZZZZZZZZZZZZZZZZZZZZZ"); tcs[3]["assumptions"] = [{"text": "假設", "requirement_id": "REQ-NEG-003", "needs_human_confirmation": True}]
    did, r = _submit_design(rid, tcs, iteration=3); assert r["result"] == "PASS" and engine.load_run(rid)["current_task_id"] == "T3"
    _, p = H.write_artifact(rid, "T3", "agent-test-validator", "TestValidationReport", H.validation_report(did, rm_aid, "PASS"), [{"entity_type": "Artifact", "id": did}], {"type": "TestCaseDraft", "ids": [did]}, "validation", iteration=3)
    assert engine.submit(rid, "T3", str(p))[0] and engine.evaluate_gate(rid, "T3")["result"] == "PASS"
    assert engine.load_run(rid)["status"] == "WAITING_HUMAN"   # ACTIVATE_TESTCASE
    engine.cancel(rid, "oscar@example.com")
