"""行為契約驅動的負向覆蓋：G-DESIGN 機械檢查、rejection_contract → Clarification、exploratory 佔比、ACTIVATE 確認假設。"""
import copy, pytest
from tools.qaos import store, engine, clarification as clr
from tools.qaos.cli import main as cli
from tests import helpers as H

S = {}
def _rm(area="NEG", spec_id="SPEC-NEG-001"):
    rm = copy.deepcopy(H.requirement_model()); rm["spec_id"] = spec_id
    for r in rm["requirements"]:
        r["spec_id"] = spec_id; r["requirement_id"] = r["requirement_id"].replace("AUTH", area); r["spec_reference"]["spec_id"] = spec_id
        for ac in r["acceptance_criteria"]: ac["ac_id"] = ac["ac_id"].replace("AUTH", area)
    for t in rm["traceability"]: t["requirement_id"] = t["requirement_id"].replace("AUTH", area); t["spec_reference"]["spec_id"] = spec_id
    R = {r["requirement_id"]: r for r in rm["requirements"]}
    R[f"REQ-{area}-001"].update(behavior_kind="boundary", inputs=[{"name": "password", "type": "string", "required": True, "constraints": {"min_length": 8}}], rejection_contract={"defined": True, "description": "拒絕並提示長度不足"})
    R[f"REQ-{area}-002"].update(behavior_kind="rejection", rejection_contract={"defined": True})
    R[f"REQ-{area}-003"].update(behavior_kind="state_change", states=[{"from": "active", "to": "locked", "trigger": "5 次錯誤"}], rejection_contract={"defined": False, "description": "Spec 未寫鎖定期間登入的回應內容"})
    R[f"REQ-{area}-004"].update(behavior_kind="success", rejection_contract={"defined": False})
    return rm

def _tcs(area="NEG", spec_id="SPEC-NEG-001", prefix="01CZZZZZZZZZZZZZZZZZZZZZZ"):
    tcs, ids_ = H.draft_set(prefix=prefix)
    for t in tcs:
        t["spec_id"] = spec_id; t["functional_area"] = area; t["expected_result_spec_reference"]["spec_id"] = spec_id
        t["requirement_ids"] = [r.replace("AUTH", area) for r in t["requirement_ids"]]; t["acceptance_criteria_ids"] = [a.replace("AUTH", area) for a in t["acceptance_criteria_ids"]]
    return tcs, ids_

def _submit_design(rid, tcs, iteration=0, report_fix=None):
    refs_ = [{"entity_type": "Requirement", "id": r} for r in sorted({r for t in tcs for r in t["requirement_ids"]})]
    did, pd = H.write_artifact(rid, "T2", "agent-test-designer", "TestCaseDraft", {"mode": "spec", "spec_id": "SPEC-NEG-001", "spec_version": "1.0", "testcases": tcs}, refs_, {"type": "RequirementModel", "ids": []}, "test-design", iteration=iteration)
    assert engine.submit(rid, "T2", str(pd))[0], "draft submit"
    rep = H.design_report(did, tcs); rep["mode"] = "spec"
    if report_fix: report_fix(rep)
    _, pr = H.write_artifact(rid, "T2", "agent-test-designer", "TestDesignReport", rep, [{"entity_type": "Artifact", "id": did}], {"type": "TestCaseDraft", "ids": [did]}, "test-design", iteration=iteration)
    assert engine.submit(rid, "T2", str(pr))[0], "report submit"
    return did, engine.evaluate_gate(rid, "T2")

def test_30_rejection_contract_undefined_opens_clarification(fixtures):
    cli(["spec", "import", str(fixtures / "SPEC-AUTH-001-v1.0.md"), "--spec-id", "SPEC-NEG-001", "--version", "1.0", "--product", "demo", "--area", "NEG", "--by", "oscar@example.com"])
    run = engine.new_run("spec-to-testcase", {"spec_id": "SPEC-NEG-001", "spec_version": "1.0"}, "oscar@example.com", new_request=True); S["run"] = run["run_id"]; rid = run["run_id"]
    rm = _rm(); h = store.load(store.spec_dir("SPEC-NEG-001") / "spec.yaml")["versions"][0]["content_hash"]
    sa = {"spec_id": "SPEC-NEG-001", "spec_version": "1.0", "content_hash": h, "summary": "x", "scope": {"in_scope": [], "out_of_scope": []}, "requirement_ids": list(r["requirement_id"] for r in rm["requirements"]), "ambiguities": [], "constraints": [], "edge_case_candidates": [], "open_questions": []}
    refs_ = [{"entity_type": "SpecVersion", "id": "SPEC-NEG-001", "version": "1.0"}]
    _, p1 = H.write_artifact(rid, "T1", "agent-spec-analyst", "SpecAnalysis", sa, refs_, {"type": "SpecVersion", "ids": []}, "spec-analysis")
    S["rm"], p2 = H.write_artifact(rid, "T1", "agent-spec-analyst", "RequirementModel", rm, refs_, {"type": "SpecVersion", "ids": []}, "requirements")
    assert engine.submit(rid, "T1", str(p1))[0] and engine.submit(rid, "T1", str(p2))[0] and engine.evaluate_gate(rid, "T1")["result"] == "PASS"
    open_clrs = [c for c in clr.list_() if c["spec_id"] == "SPEC-NEG-001"]
    assert {c["requirement_id"] for c in open_clrs} == {"REQ-NEG-003", "REQ-NEG-004"} and all(c["status"] == "OPEN" for c in open_clrs)
    assert engine.load_run(rid)["status"] == "RUNNING" and engine.load_run(rid)["current_task_id"] == "T2"   # 不阻塞
    persisted = store.load(store.requirements_path("SPEC-NEG-001", "1.0"))["requirements"][0]
    assert persisted["behavior_kind"] == "boundary" and persisted["inputs"][0]["constraints"]["min_length"] == 8

def test_31_g_design_rejects_happy_only_and_mismatched_summary():
    rid = S["run"]; tcs, ids_ = _tcs()
    # (a) high-risk REQ-NEG-001 只留 happy path；(b) 移除 REQ-NEG-003 的 state_transition；(c) technique_summary 灌水
    happy = [t for t in tcs if t["draft_id"] != ids_[1]]
    for t in happy:
        if t["draft_id"] == ids_[0]: t["test_types"] = ["functional"]; t["design_techniques"] = ["requirement_based"]
        if t["draft_id"] == ids_[3]: t["design_techniques"] = ["scenario"]
    def fudge(rep): rep["technique_summary"].append({"technique": "negative", "count": 5})
    _, r = _submit_design(rid, happy, report_fix=fudge)
    assert r["result"] == "FAIL"
    msgs = "\n".join(r["issues"])
    assert "REQ-NEG-001 為 high risk 但沒有任何 negative" in msgs and "必須有 boundary_value 案例" in msgs
    assert "REQ-NEG-003 定義了狀態轉換" in msgs and "technique_summary.negative 宣告 5" in msgs
    assert engine.load_run(rid)["tasks"][1]["status"] == "READY"

def test_32_exploratory_needs_flag_and_over_half_triggers_decision():
    rid = S["run"]; tcs, ids_ = _tcs(prefix="01DZZZZZZZZZZZZZZZZZZZZZZ")
    # REQ-NEG-003 rejection 未定義 → 其非 happy-path 必須是 exploratory；先故意不標 needs_human_confirmation
    lock = next(t for t in tcs if t["draft_id"] == ids_[3]); lock["assumptions"] = [{"text": "鎖定期間回「帳號已鎖定」文案（Spec 未定義）", "requirement_id": "REQ-NEG-003"}]
    _, r = _submit_design(rid, tcs); assert r["result"] == "FAIL" and any("needs_human_confirmation" in i for i in r["issues"])
    # 標上後 PASS（1/5 exploratory）
    lock["assumptions"][0]["needs_human_confirmation"] = True
    did, r = _submit_design(rid, tcs); assert r["result"] == "PASS", r["issues"]; assert engine.load_run(rid)["current_task_id"] == "T3"
    S["draft"] = did; S["ids"] = ids_; S["tcs"] = tcs

def test_33_over_half_exploratory_routes_to_needs_decision_then_continue():
    """另開一個 run：4/5 exploratory → NEEDS_DECISION（不 FAIL）→ Human 選 continue → 進 T3。"""
    run = engine.new_run("spec-to-testcase", {"spec_id": "SPEC-NEG-001", "spec_version": "1.0"}, "oscar@example.com", new_request=True); rid = run["run_id"]
    assert run["tasks"][0]["status"] == "DONE" and run["current_task_id"] == "T2"   # RequirementModel 已存在 → T1 skip
    tcs, ids_ = _tcs(prefix="01EZZZZZZZZZZZZZZZZZZZZZZ")
    for t in tcs[:4]: t["assumptions"] = [{"text": "假設", "requirement_id": t["requirement_ids"][0], "needs_human_confirmation": True}]
    _, r = _submit_design(rid, tcs); assert r["result"] == "PASS", r["issues"]
    run = engine.load_run(rid); apr = store.load(f"approvals/{run['waiting_on_approval_id']}.yaml")
    assert run["status"] == "WAITING_HUMAN" and apr["type"] == "NEEDS_DECISION" and "4/5" in apr["summary"]
    engine.approve(apr["approval_id"], "approve", "oscar@example.com", selected_option="continue")
    run = engine.load_run(rid); assert run["status"] == "RUNNING" and run["current_task_id"] == "T3"
    engine.cancel(rid, "oscar@example.com")

def test_34_activate_confirms_assumptions():
    rid = S["run"]
    vr, p = H.write_artifact(rid, "T3", "agent-test-validator", "TestValidationReport", H.validation_report(S["draft"], S["rm"], "PASS"), [{"entity_type": "Artifact", "id": S["draft"]}], {"type": "TestCaseDraft", "ids": [S["draft"]]}, "validation")
    assert engine.submit(rid, "T3", str(p))[0] and engine.evaluate_gate(rid, "T3")["result"] == "PASS"
    run = engine.load_run(rid); apr = store.load(f"approvals/{run['waiting_on_approval_id']}.yaml")
    assert "含 1 條 exploratory" in apr["summary"] and "[exploratory]" in apr["diff_summary"]
    exp_item = next(i for i in apr["batch_items"] if store.load(store.tc_version_path(i["id"], i["version"])).get("assumptions"))
    v = store.load(store.tc_version_path(exp_item["id"], exp_item["version"])); assert v["assumptions"][0]["needs_human_confirmation"] is True
    engine.approve(apr["approval_id"], "approve", "oscar@example.com")
    v = store.load(store.tc_version_path(exp_item["id"], exp_item["version"]))
    assert v["status"] == "ACTIVE" and v["assumptions"][0]["needs_human_confirmation"] is False and v["assumptions"][0]["resolved_by_approval"] == apr["approval_id"]
