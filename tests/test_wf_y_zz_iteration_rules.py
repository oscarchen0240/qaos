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

def test_41_reject_full_activate_batch_then_resubmit_gives_fresh_approval_refs():
    """T3（approval）整批 reject 後，approval task 自己的 input_entity_refs 必須被清掉；否則下一輪
    Designer→Validator 重新 PASS、materialize 出全新版本時，_create_approval_for_task 會誤撿到
    上一輪已被打回 DRAFT 的舊 refs，對其 state.apply(...→PENDING_APPROVAL) 直接崩潰（回歸測試）。"""
    run = engine.new_run("spec-to-testcase", {"spec_id": "SPEC-NEG-001", "spec_version": "1.0"}, "oscar@example.com"); rid = run["run_id"]
    rm_aid = store.load(store.requirements_path("SPEC-NEG-001", "1.0"))["source_artifact_id"]
    tcs, _ = _tcs(prefix="01J0ZZZZZZZZZZZZZZZZZZZZZ")
    did1, r = _submit_design(rid, tcs, iteration=0); assert r["result"] == "PASS"
    _, p = H.write_artifact(rid, "T3", "agent-test-validator", "TestValidationReport", H.validation_report(did1, rm_aid, "PASS"), [{"entity_type": "Artifact", "id": did1}], {"type": "TestCaseDraft", "ids": [did1]}, "validation", iteration=0)
    assert engine.submit(rid, "T3", str(p))[0] and engine.evaluate_gate(rid, "T3")["result"] == "PASS"
    run = engine.load_run(rid); assert run["status"] == "WAITING_HUMAN"
    apr1 = store.load(f"approvals/{run['waiting_on_approval_id']}.yaml")
    first_ids = {it["id"] for it in apr1["batch_items"]}; assert len(first_ids) == 5
    # 整批 reject（非 per-item）→ 回到 T2，第一輪版本打回 DRAFT
    engine.approve(apr1["approval_id"], "reject", "oscar@example.com", rationale="重新設計")
    run = engine.load_run(rid); assert run["tasks"][1]["status"] == "READY" and run["tasks"][1]["iteration"] == 1
    for tc_id in first_ids:
        assert store.load(store.tc_pointer_path(tc_id))["versions"][0]["status"] == "DRAFT"
    # 第二輪：重新設計 → Validator PASS → 應產生全新 ApprovalRequest，不崩潰、且與第一輪的 TC id 不重疊
    tcs2, _ = _tcs(prefix="01J1ZZZZZZZZZZZZZZZZZZZZZ")
    did2, r = _submit_design(rid, tcs2, iteration=1); assert r["result"] == "PASS"
    _, p2 = H.write_artifact(rid, "T3", "agent-test-validator", "TestValidationReport", H.validation_report(did2, rm_aid, "PASS"), [{"entity_type": "Artifact", "id": did2}], {"type": "TestCaseDraft", "ids": [did2]}, "validation", iteration=1)
    assert engine.submit(rid, "T3", str(p2))[0]
    r2 = engine.evaluate_gate(rid, "T3")   # 修正前：TransitionError（testcase: 沒有 DRAFT → PENDING_APPROVAL 這條轉換）
    assert r2["result"] == "PASS"
    run = engine.load_run(rid); assert run["status"] == "WAITING_HUMAN"
    apr2 = store.load(f"approvals/{run['waiting_on_approval_id']}.yaml")
    second_ids = {it["id"] for it in apr2["batch_items"]}
    assert len(second_ids) == 5 and second_ids.isdisjoint(first_ids)
    for it in apr2["batch_items"]:
        assert store.load(store.tc_version_path(it["id"], it["version"]))["status"] == "PENDING_APPROVAL"
    engine.cancel(rid, "oscar@example.com")
