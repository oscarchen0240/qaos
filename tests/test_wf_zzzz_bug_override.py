"""spec-to-bug：Bug Validator FAIL ×3 → HUMAN_OVERRIDE，以 override 強制通過 → bug VALIDATED → OPEN_BUG 核准 → run COMPLETED。
回歸：_route_back 已把 bug 退回 DRAFT，_after_override 不可再做 DRAFT → DRAFT（TransitionError）；
override 也要帶上 validator／report，否則 OPEN_BUG 核准時 Bug 的 validated_by／validation_report_id 為 None、不符 schema。
放在最後執行：會多建立一張 AUTH Bug，避免影響前面依 BUG-AUTH-001／Bug 數量的情境測試。"""
from tools.qaos import store, engine
from tools.qaos.cli import main as cli
from tests import helpers as H
from tests.test_wf_b_bug_and_e_regression import _bug_draft

CHECKS = ["violates_spec", "expected_has_spec_basis", "actual_supported_by_evidence", "reproduction_sufficient", "severity_reasonable", "priority_reasonable", "not_duplicate", "not_mere_ambiguity"]

def _fail_report(bd, evd):
    return {"result": "FAIL", "bug_draft_artifact_id": bd, "checks": {k: False for k in CHECKS},
            "issues": [{"testcase_id": "*", "issue_type": "other", "severity": "major", "violated_requirement": "REQ-AUTH-001", "spec_reference": None,
                        "evidence": "e", "explanation": "重現步驟不足", "recommended_change": "補步驟"}],
            "evidence_verification": [{"evidence_id": evd, "hash_verified": True, "supports_claim": True}],
            "severity_assessment": {"severity_recommended": "major", "priority_recommended": "high", "agrees_with_analyst": True, "rationale": "同意"},
            "duplicate_check": {"searched": True, "duplicate_of": None}}

def test_90_bug_validator_fail_x3_then_override_opens_bug(capsys):
    cli(["evidence", "add", "--type", "api_response", "--inline", '{"accepted":true,"password_len":7}', "--owner", "manual", "--description", "長度 7 密碼被接受", "--by", "oscar@example.com"])
    evd = capsys.readouterr().out.strip()
    rid = engine.new_run("spec-to-bug", {"spec_id": "SPEC-AUTH-001", "spec_version": "1.0", "actual_behavior": "長度 7 的密碼被接受", "evidence_ids": [evd]}, "oscar@example.com")["run_id"]
    draft = {k: v for k, v in _bug_draft(evd, (None, None)).items() if k not in ("testcase_id", "testcase_version", "execution_id")}
    for it in range(3):
        bd, p = H.write_artifact(rid, "T1", "agent-bug-analyst", "BugDraft", draft, [{"entity_type": "Requirement", "id": "REQ-AUTH-001"}, {"entity_type": "Evidence", "id": evd}],
                                 {"type": "Evidence", "ids": [evd]}, "bug-analysis", iteration=it)
        assert engine.submit(rid, "T1", str(p))[0] and engine.evaluate_gate(rid, "T1")["result"] == "PASS"
        _, p = H.write_artifact(rid, "T2", "agent-bug-validator", "BugValidationReport", _fail_report(bd, evd), [{"entity_type": "Artifact", "id": bd}, {"entity_type": "Evidence", "id": evd}],
                                {"type": "BugDraft", "ids": [bd]}, "validation", iteration=it)
        assert engine.submit(rid, "T2", str(p))[0] and engine.evaluate_gate(rid, "T2")["result"] == "FAIL"
    run = engine.load_run(rid); apr = store.load(f"approvals/{run['waiting_on_approval_id']}.yaml")
    assert apr["type"] == "HUMAN_OVERRIDE" and store.load(engine._bug_path(run))["status"] == "DRAFT"
    engine.approve(apr["approval_id"], "override", "oscar@example.com", rationale="人工確認 bug 成立")
    run = engine.load_run(rid); assert run["status"] == "WAITING_HUMAN" and store.load(engine._bug_path(run))["status"] == "PENDING_APPROVAL"
    assert store.load(f"approvals/{run['waiting_on_approval_id']}.yaml")["type"] == "OPEN_BUG"
    engine.approve(run["waiting_on_approval_id"], "approve", "oscar@example.com")
    run = engine.load_run(rid); assert run["status"] == "COMPLETED"
    b = store.load(store.find_bug(store.load(engine._bug_path(run))["bug_id"]))
    rep = engine._valid_outputs(engine._task(run, "T2"))["BugValidationReport"]["artifact_id"]
    assert b["status"] == "OPEN" and b["validated_by"] == "agent-bug-validator" and b["validation_report_id"] == rep
    assert [h["to_status"] for h in b["history"]][-6:] == ["VALIDATION_FAILED", "DRAFT", "VALIDATING", "VALIDATED", "PENDING_APPROVAL", "OPEN"]   # 不得出現 DRAFT → DRAFT
