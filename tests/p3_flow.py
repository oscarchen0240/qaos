"""P3 測試用的正式流程（在子程序中、QAOS_ROOT 指向暫存 root 時呼叫）：spec-to-testcase 的 T1 分析、T2／T3、T4 核准。
每一步都經過正式 API（new_run、submit、evaluate_gate、approve），不手造業務狀態。"""
from tools.qaos import engine, store
from tests import helpers as H

BY = "oscar@example.com"
SPEC, VER = "SPEC-AUTH-001", "1.0"

def new_run(**extra) -> str:
    return engine.new_run("spec-to-testcase", {"spec_id": SPEC, "spec_version": VER, **extra}, BY, new_request=True)["run_id"]

def analyze(rid: str, crit: bool = False) -> str:
    """T1：提交 SpecAnalysis＋RequirementModel 並跑 gate。crit=True 時 REQ-AUTH-002 帶未解決的 critical ambiguity（會持久化為 DRAFT）。回傳 RM artifact_id。"""
    rm = H.requirement_model()
    if crit: rm["requirements"][1]["ambiguity"] = {"level": "critical", "description": "數字要不要含全形？", "options": ["含", "不含"]}
    refs_ = [{"entity_type": "SpecVersion", "id": SPEC, "version": VER}]
    ch = store.load(store.spec_dir(SPEC) / "spec.yaml")["versions"][0]["content_hash"]
    sa = {"spec_id": SPEC, "spec_version": VER, "content_hash": ch, "summary": "s", "scope": {"in_scope": ["x"], "out_of_scope": []},
          "requirement_ids": [r["requirement_id"] for r in rm["requirements"]], "ambiguities": [], "constraints": [], "edge_case_candidates": [], "open_questions": []}
    _, p1 = H.write_artifact(rid, "T1", "agent-spec-analyst", "SpecAnalysis", sa, refs_, {"type": "SpecVersion", "ids": [f"{SPEC}@{VER}"]}, "spec-analysis")
    rmid, p2 = H.write_artifact(rid, "T1", "agent-spec-analyst", "RequirementModel", rm, refs_, {"type": "SpecVersion", "ids": [f"{SPEC}@{VER}"]}, "requirements")
    assert engine.submit(rid, "T1", str(p1))[0] and engine.submit(rid, "T1", str(p2))[0]
    engine.evaluate_gate(rid, "T1")
    return rmid

def design_and_validate(rid: str, rmid: str, prefix="01ARZ3NDEKTSV4RRFFQ69G5FA") -> str:
    """T2 提交 Draft＋Report 並過 gate；T3 Validator PASS → TC 實體化。回傳 draft artifact_id。"""
    tcs, _ = H.draft_set(prefix=prefix)
    refs_ = [{"entity_type": "Requirement", "id": r} for r in ["REQ-AUTH-001", "REQ-AUTH-002", "REQ-AUTH-003", "REQ-AUTH-004"]]
    did, pd = H.write_artifact(rid, "T2", "agent-test-designer", "TestCaseDraft", {"mode": "spec", "spec_id": SPEC, "spec_version": VER, "testcases": tcs}, refs_,
                               {"type": "RequirementModel", "ids": [rmid]}, "test-design")
    _, pr = H.write_artifact(rid, "T2", "agent-test-designer", "TestDesignReport", H.design_report(did, tcs), [{"entity_type": "Artifact", "id": did}], {"type": "TestCaseDraft", "ids": [did]}, "test-design")
    assert engine.submit(rid, "T2", str(pd))[0] and engine.submit(rid, "T2", str(pr))[0]
    assert engine.evaluate_gate(rid, "T2")["result"] == "PASS"
    _, pv = H.write_artifact(rid, "T3", "agent-test-validator", "TestValidationReport", H.validation_report(did, rmid, "PASS"),
                             [{"entity_type": "Artifact", "id": did}, {"entity_type": "Artifact", "id": rmid}], {"type": "TestCaseDraft", "ids": [did]}, "validation")
    assert engine.submit(rid, "T3", str(pv))[0] and engine.evaluate_gate(rid, "T3")["result"] == "PASS"
    return did

def approve_pending(rid: str, decision: str = "approve") -> str:
    run = engine.load_run(rid); apr = run["waiting_on_approval_id"]
    engine.approve(apr, decision, BY, rationale="test")
    return apr

def full(prefix="01ARZ3NDEKTSV4RRFFQ69G5FA") -> str:
    """一個完整的 spec-to-testcase run：分析 → 設計 → 驗證 → ACTIVATE 核准。回傳 run_id。"""
    rid = new_run(); rmid = analyze(rid); design_and_validate(rid, rmid, prefix); approve_pending(rid)
    return rid
