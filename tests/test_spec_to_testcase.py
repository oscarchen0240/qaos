"""Phase 2 DoD：不用任何 Agent，用手寫 artifact 走完 spec-to-testcase 的所有狀態轉換；
並證明 Runtime 拒絕：越權、缺 approval、非法轉換、斷裂的 traceability。"""
import pytest
from tools.qaos import store, engine, state, refs
from tools.qaos.cli import main as cli
from tools.qaos.engine import EngineError
from tools.qaos.state import TransitionError
from tests import helpers as H

RUN = {}

def test_00_spec_import(fixtures):
    cli(["spec", "import", str(fixtures / "SPEC-AUTH-001-v1.0.md"), "--spec-id", "SPEC-AUTH-001", "--version", "1.0",
         "--product", "demo", "--area", "AUTH", "--title", "帳號登入規格", "--by", "oscar@example.com"])
    spec = store.load(store.spec_dir("SPEC-AUTH-001") / "spec.yaml")
    assert spec["versions"][0]["status"] == "IMPORTED" and len(spec["versions"][0]["content_hash"]) == 64
    with pytest.raises(SystemExit):  # 同版本不可覆蓋
        cli(["spec", "import", str(fixtures / "SPEC-AUTH-001-v1.0.md"), "--spec-id", "SPEC-AUTH-001", "--version", "1.0", "--product", "demo", "--area", "AUTH", "--by", "x"])

def test_01_new_run_requires_valid_spec_version():
    with pytest.raises(EngineError): engine.new_run("spec-to-testcase", {"spec_id": "SPEC-AUTH-001", "spec_version": "9.9"}, "oscar@example.com")
    run = engine.new_run("spec-to-testcase", {"spec_id": "SPEC-AUTH-001", "spec_version": "1.0"}, "oscar@example.com")
    RUN["id"] = run["run_id"]
    assert run["status"] == "RUNNING" and run["current_task_id"] == "T1"
    assert [t["status"] for t in run["tasks"]] == ["READY", "PENDING", "PENDING", "PENDING", "PENDING"]

def test_02_permission_guard_rejects_wrong_agent_and_type():
    rid = RUN["id"]
    # Test Designer 冒充在 T1 提交（created_by 不符）→ permission violation → run FAILED
    bad = engine.new_run("spec-to-testcase", {"spec_id": "SPEC-AUTH-001", "spec_version": "1.0"}, "oscar@example.com")
    aid, p = H.write_artifact(bad["run_id"], "T1", "agent-test-designer", "RequirementModel", H.requirement_model(),
                              [{"entity_type": "SpecVersion", "id": "SPEC-AUTH-001", "version": "1.0"}], {"type": "SpecVersion", "ids": ["SPEC-AUTH-001@1.0"]}, "spec-analysis")
    ok, problems = engine.submit(bad["run_id"], "T1", str(p))
    assert not ok and any("越權" in x for x in problems)
    b = engine.load_run(bad["run_id"]); assert b["status"] == "FAILED" and b["tasks"][0]["permission_violations"]
    # Spec Analyst 產出自己無權產出的 TestCaseDraft → 無權產出
    bad3 = engine.new_run("spec-to-testcase", {"spec_id": "SPEC-AUTH-001", "spec_version": "1.0"}, "oscar@example.com")
    tcs, _ = H.draft_set()
    aid, p = H.write_artifact(bad3["run_id"], "T1", "agent-spec-analyst", "TestCaseDraft", {"mode": "spec", "spec_id": "SPEC-AUTH-001", "spec_version": "1.0", "testcases": tcs},
                              [], {"type": "x", "ids": []}, "spec-analysis")
    ok, problems = engine.submit(bad3["run_id"], "T1", str(p))
    assert not ok and any("無權產出" in x for x in problems) and engine.load_run(bad3["run_id"])["status"] == "FAILED"
    # 寫錯目錄（Spec Analyst 寫到 test-design/）→ violation
    bad2 = engine.new_run("spec-to-testcase", {"spec_id": "SPEC-AUTH-001", "spec_version": "1.0"}, "oscar@example.com")
    aid, p = H.write_artifact(bad2["run_id"], "T1", "agent-spec-analyst", "RequirementModel", H.requirement_model(),
                              [{"entity_type": "SpecVersion", "id": "SPEC-AUTH-001", "version": "1.0"}], {"type": "SpecVersion", "ids": []}, "test-design")
    ok, problems = engine.submit(bad2["run_id"], "T1", str(p))
    assert not ok and any("write_paths" in x for x in problems)

def test_03_T1_spec_analyst_structural_gate():
    rid = RUN["id"]; rm = H.requirement_model()
    refs_ = [{"entity_type": "SpecVersion", "id": "SPEC-AUTH-001", "version": "1.0"}]
    # 先提交一份缺 AC 的 RequirementModel → schema INVALID（requirement.acceptance_criteria minItems 1）
    broken = H.requirement_model(); broken["requirements"][0]["acceptance_criteria"] = []
    aid, p = H.write_artifact(rid, "T1", "agent-spec-analyst", "RequirementModel", broken, refs_, {"type": "SpecVersion", "ids": ["SPEC-AUTH-001@1.0"]}, "requirements")
    ok, problems = engine.submit(rid, "T1", str(p)); assert not ok and store.load(p)["status"] == "INVALID"
    assert engine.load_run(rid)["tasks"][0]["status"] == "READY"  # structural fail 不計迭代、可重試
    # 正確提交 SpecAnalysis + RequirementModel
    sa_payload = {"spec_id": "SPEC-AUTH-001", "spec_version": "1.0", "content_hash": store.load(store.spec_dir("SPEC-AUTH-001") / "spec.yaml")["versions"][0]["content_hash"],
                  "summary": "登入與密碼規則", "scope": {"in_scope": ["密碼規則", "登入失敗", "登入成功"], "out_of_scope": []},
                  "requirement_ids": [r["requirement_id"] for r in rm["requirements"]], "ambiguities": [], "constraints": [], "edge_case_candidates": [], "open_questions": []}
    sa, p1 = H.write_artifact(rid, "T1", "agent-spec-analyst", "SpecAnalysis", sa_payload, refs_, {"type": "SpecVersion", "ids": ["SPEC-AUTH-001@1.0"]}, "spec-analysis")
    rmid, p2 = H.write_artifact(rid, "T1", "agent-spec-analyst", "RequirementModel", rm, refs_, {"type": "SpecVersion", "ids": ["SPEC-AUTH-001@1.0"]}, "requirements")
    assert engine.submit(rid, "T1", str(p1))[0] and engine.submit(rid, "T1", str(p2))[0]
    RUN["rm"] = rmid
    # G-DESIGN 之前 Requirement 尚未持久化 → 此時 TestCaseDraft 若引用 REQ 會被 refs 拒絕
    assert refs.resolve({"entity_type": "Requirement", "id": "REQ-AUTH-001"}) is not None
    r = engine.evaluate_gate(rid, "T1"); assert r["result"] == "PASS"
    reqs = store.load(store.requirements_path("SPEC-AUTH-001", "1.0"))["requirements"]
    assert all(q["status"] == "ACTIVE" for q in reqs) and reqs[0]["history"][-1]["to_status"] == "ACTIVE"
    assert store.load(store.spec_dir("SPEC-AUTH-001") / "spec.yaml")["versions"][0]["status"] == "ANALYZED"
    assert engine.load_run(rid)["current_task_id"] == "T2"

def test_04_T2_designer_gate_rejects_broken_traceability():
    rid = RUN["id"]; tcs, ids_ = H.draft_set()
    # 引用不存在的 requirement → reference 解析失敗 → INVALID
    broken = [dict(t) for t in tcs]; broken[0] = dict(broken[0], requirement_ids=["REQ-AUTH-999"])
    refs_ = [{"entity_type": "Requirement", "id": "REQ-AUTH-999"}]
    aid, p = H.write_artifact(rid, "T2", "agent-test-designer", "TestCaseDraft", {"mode": "spec", "spec_id": "SPEC-AUTH-001", "spec_version": "1.0", "testcases": broken},
                              refs_, {"type": "RequirementModel", "ids": [RUN["rm"]]}, "test-design")
    ok, problems = engine.submit(rid, "T2", str(p)); assert not ok and any("REQ-AUTH-999" in x for x in problems)
    # 正確 Draft + Report，但 Report 漏掉 REQ-AUTH-004 的覆蓋 → G-DESIGN structural FAIL
    refs_ = [{"entity_type": "Requirement", "id": r} for r in ["REQ-AUTH-001", "REQ-AUTH-002", "REQ-AUTH-003", "REQ-AUTH-004"]] + [{"entity_type": "Artifact", "id": RUN["rm"]}]
    did, pd = H.write_artifact(rid, "T2", "agent-test-designer", "TestCaseDraft", {"mode": "spec", "spec_id": "SPEC-AUTH-001", "spec_version": "1.0", "testcases": tcs},
                               refs_, {"type": "RequirementModel", "ids": [RUN["rm"]]}, "test-design")
    assert engine.submit(rid, "T2", str(pd))[0]
    rep = H.design_report(did, tcs); rep["coverage_matrix"] = [c for c in rep["coverage_matrix"] if c["requirement_id"] != "REQ-AUTH-004"]
    trid, pr = H.write_artifact(rid, "T2", "agent-test-designer", "TestDesignReport", rep, [{"entity_type": "Artifact", "id": did}], {"type": "TestCaseDraft", "ids": [did]}, "test-design")
    assert engine.submit(rid, "T2", str(pr))[0]
    r = engine.evaluate_gate(rid, "T2"); assert r["result"] == "FAIL" and any("REQ-AUTH-004" in i for i in r["issues"])
    # 補齊 → PASS
    trid2, pr2 = H.write_artifact(rid, "T2", "agent-test-designer", "TestDesignReport", H.design_report(did, tcs), [{"entity_type": "Artifact", "id": did}], {"type": "TestCaseDraft", "ids": [did]}, "test-design")
    assert engine.submit(rid, "T2", str(pr2))[0]
    assert store.load(store.find_artifact(trid))["status"] == "SUPERSEDED"  # 同型 artifact 被新版取代
    assert engine.evaluate_gate(rid, "T2")["result"] == "PASS"
    RUN["draft"] = did; RUN["draft_ids"] = ids_
    assert engine.load_run(rid)["current_task_id"] == "T3"

def test_05_T3_validator_fail_routes_back_then_pass_materializes():
    rid = RUN["id"]
    issue = {"testcase_id": RUN["draft_ids"][2], "issue_type": "spec_mismatch", "severity": "major", "violated_requirement": "REQ-AUTH-002",
             "spec_reference": {"spec_id": "SPEC-AUTH-001", "spec_version": "1.0", "location": "§3.1 R2"}, "evidence": "步驟用長度 12 的密碼，與 v1.0 無關", "explanation": "測試資料不必要地耦合長度", "recommended_change": "改用長度 8"}
    vr, p = H.write_artifact(rid, "T3", "agent-test-validator", "TestValidationReport", H.validation_report(RUN["draft"], RUN["rm"], "FAIL", [issue]),
                             [{"entity_type": "Artifact", "id": RUN["draft"]}, {"entity_type": "Artifact", "id": RUN["rm"]}], {"type": "TestCaseDraft", "ids": [RUN["draft"]]}, "validation")
    assert engine.submit(rid, "T3", str(p))[0]
    r = engine.evaluate_gate(rid, "T3"); assert r["layer"] == "semantic" and r["result"] == "FAIL"
    run = engine.load_run(rid); t2 = run["tasks"][1]
    assert run["current_task_id"] == "T2" and t2["status"] == "READY" and t2["iteration"] == 1 and vr in t2["input_artifact_ids"]
    assert not list((store.ROOT / "testcases" / "versions").glob("*"))  # FAIL 時不得寫入 versions/
    # Designer 修訂（iteration 1）
    tcs, ids_ = H.draft_set(); tcs[2]["steps"][0]["action"] = "輸入長度 8 但不含數字的密碼"
    refs_ = [{"entity_type": "Requirement", "id": r} for r in ["REQ-AUTH-001", "REQ-AUTH-002", "REQ-AUTH-003", "REQ-AUTH-004"]]
    did, pd = H.write_artifact(rid, "T2", "agent-test-designer", "TestCaseDraft", {"mode": "spec", "spec_id": "SPEC-AUTH-001", "spec_version": "1.0", "testcases": tcs}, refs_, {"type": "RequirementModel", "ids": [RUN["rm"]]}, "test-design", iteration=1)
    assert engine.submit(rid, "T2", str(pd))[0]
    rep = H.design_report(did, tcs); rep["revision_of_issues"] = [{"issue_index": 0, "action": "改用長度 8", "draft_id": ids_[2]}]
    trid, pr = H.write_artifact(rid, "T2", "agent-test-designer", "TestDesignReport", rep, [{"entity_type": "Artifact", "id": did}], {"type": "TestCaseDraft", "ids": [did]}, "test-design", iteration=1)
    assert engine.submit(rid, "T2", str(pr))[0] and engine.evaluate_gate(rid, "T2")["result"] == "PASS"
    # Validator PASS → materialize → T4 approval → WAITING_HUMAN
    vr2, p = H.write_artifact(rid, "T3", "agent-test-validator", "TestValidationReport", H.validation_report(did, RUN["rm"], "PASS"),
                              [{"entity_type": "Artifact", "id": did}, {"entity_type": "Artifact", "id": RUN["rm"]}], {"type": "TestCaseDraft", "ids": [did]}, "validation")
    assert engine.submit(rid, "T3", str(p))[0]
    assert engine.evaluate_gate(rid, "T3")["result"] == "PASS"
    run = engine.load_run(rid)
    assert run["status"] == "WAITING_HUMAN" and run["waiting_on_approval_id"] is not None
    RUN["apr"] = run["waiting_on_approval_id"]
    vers = sorted((store.ROOT / "testcases" / "versions").glob("*/v1.yaml")); assert len(vers) == 5
    v = store.load(vers[0]); assert v["status"] == "PENDING_APPROVAL" and [h["to_status"] for h in v["history"]] == ["DRAFT", "VALIDATING", "VALIDATED", "PENDING_APPROVAL"]
    ptr = store.load(store.tc_pointer_path(v["testcase_id"])); assert ptr["active_version"] is None and ptr["status"] == "NO_ACTIVE_VERSION"
    RUN["tc_ids"] = [store.load(x)["testcase_id"] for x in vers]

def test_06_no_approval_no_production_change():
    apr = store.load(f"approvals/{RUN['apr']}.yaml")
    assert apr["type"] == "ACTIVATE_TESTCASE" and len(apr["batch_items"]) == 5
    with pytest.raises(EngineError): engine.approve(RUN["apr"], "approve", "agent-supervisor")           # Agent 不能批
    with pytest.raises(EngineError): engine.approve(RUN["apr"], "override", "oscar@example.com", "")     # override 必附 rationale
    with pytest.raises(EngineError): engine.submit(RUN["id"], "T2", "x")                                  # WAITING_HUMAN 不接受提交
    tc0 = RUN["tc_ids"][0]; v = store.load(store.tc_version_path(tc0, 1))
    with pytest.raises(TransitionError): state.apply("testcase", v, "ACTIVE", "system", "hack")          # PENDING_APPROVAL → ACTIVE 不存在
    with pytest.raises(TransitionError): state.apply("testcase", v, "APPROVED", "agent-test-validator", "hack")  # 只有 human 能 APPROVED

def test_07_batch_approve_with_one_reject_then_complete():
    rid = RUN["id"]; rejected = RUN["tc_ids"][4]
    apr = engine.approve(RUN["apr"], "approve", "oscar@example.com", per_item=[{"id": rejected, "decision": "reject", "rationale": "與既有 smoke 重複"}])
    for tc_id in RUN["tc_ids"][:4]:
        v = store.load(store.tc_version_path(tc_id, 1)); ptr = store.load(store.tc_pointer_path(tc_id))
        assert v["status"] == "ACTIVE" and v["approved_by"] == "oscar@example.com" and v["approval_id"] == RUN["apr"]
        assert ptr["active_version"] == 1 and ptr["status"] == "ACTIVE" and ptr["versions"][0]["activated_by_approval"] == RUN["apr"]
    assert store.load(store.tc_version_path(rejected, 1))["status"] == "DRAFT"
    run = engine.load_run(rid)
    assert run["status"] == "COMPLETED" and run["summary_artifact_id"]
    summ = store.load(store.find_artifact(run["summary_artifact_id"]))["payload"]
    assert summ["iterations"]["T2"] == 1 and len(summ["outputs"]) == 5 and summ["approvals"][0]["decision"] == "approve"
    audit = (store.ROOT / "runs" / rid / "audit.log").read_text()
    for token in ("CREATE_WORKFLOW_RUN", "ARTIFACT_INVALID", "GATE_FAIL", "ROUTE_BACK", "MATERIALIZE_TESTCASES", "REQUEST_HUMAN_APPROVAL", "RECORD_APPROVAL", "COMMIT_TO_REGISTRY", "CREATE_WORKFLOW_SUMMARY"):
        assert token in audit, token

def test_08_trace_and_validate_cli(capsys):
    tc0 = RUN["tc_ids"][0]
    cli(["trace", tc0]); out = capsys.readouterr().out
    assert "SpecVersion SPEC-AUTH-001@1.0" in out and "Requirement REQ-AUTH-001 [ACTIVE]" in out and "approved_by oscar@example.com" in out
    cli(["validate", str(store.ROOT / store.tc_version_path(tc0, 1))]); assert "VALID" in capsys.readouterr().out
    cli(["trace", "REQ-AUTH-001"]); assert f"TestCase {tc0} v1 [ACTIVE]" in capsys.readouterr().out
    assert cli(["suites-of", tc0]) is None
