"""WF-B spec-to-bug 與 WF-E regression-generation 的引擎路徑（沿用 WF-A 建好的 Registry）。"""
import pytest
from tools.qaos import store, engine, state, refs, trace
from tools.qaos.cli import main as cli
from tools.qaos.engine import EngineError
from tools.qaos.state import TransitionError
from tests import helpers as H

S = {}

def _active_tcs():
    out = []
    for p in sorted((store.ROOT / "testcases" / "registry").glob("TC-*.yaml")):
        d = store.load(p)
        if d["status"] == "ACTIVE": out.append((d["testcase_id"], d["active_version"], store.load(store.tc_version_path(d["testcase_id"], d["active_version"]))))
    return out

def test_10_evidence_and_execution_import(capsys):
    cli(["evidence", "add", "--type", "api_response", "--inline", '{"status":200,"accepted":true,"password_len":7}', "--owner", "manual", "--description", "長度 7 密碼被接受", "--by", "oscar@example.com"])
    S["evd"] = capsys.readouterr().out.strip(); assert S["evd"].startswith("EVD-")
    tc_id, ver, _ = _active_tcs()[1]  # 長度 7 拒絕 的 TC
    cli(["execution", "import", "--testcase-id", tc_id, "--testcase-version", str(ver), "--result", "fail", "--environment", "stage", "--evidence", S["evd"],
         "--actual-result", "長度 7 的密碼被接受", "--by", "oscar@example.com"])
    S["exe"] = capsys.readouterr().out.strip(); assert S["exe"].startswith("EXE-"); S["tc"] = (tc_id, ver)
    assert refs.resolve({"entity_type": "Evidence", "id": S["evd"]}) is None
    # 竄改 Evidence 檔案 → hash 不符 → 不可引用
    ev = store.load(store.find_evidence(S["evd"])); p = store.ROOT / ev["uri"]; orig = p.read_text(); p.write_text(orig + " ")
    msg = refs.resolve({"entity_type": "Evidence", "id": S["evd"]}); p.write_text(orig)
    assert msg and "竄改" in msg and refs.resolve({"entity_type": "Evidence", "id": S["evd"]}) is None

def test_11_no_evidence_no_formal_bug():
    with pytest.raises(EngineError): engine.new_run("spec-to-bug", {"spec_id": "SPEC-AUTH-001", "spec_version": "1.0", "evidence_ids": []}, "oscar@example.com", new_request=True)
    run = engine.new_run("spec-to-bug", {"spec_id": "SPEC-AUTH-001", "spec_version": "1.0", "execution_id": S["exe"], "evidence_ids": [S["evd"]]}, "oscar@example.com", new_request=True)
    S["run"] = run["run_id"]
    assert run["tasks"][0]["status"] == "DONE" and run["current_task_id"] == "T1"  # T0 因 RequirementModel 已存在而 skip

def _bug_draft(evd, tc):
    return {"draft_id": "BUG-DRAFT-01ARZ3NDEKTSV4RRFFQ69G5FAV", "title": "長度 7 的密碼被接受，違反最小長度 8", "product": "demo", "functional_area": "AUTH",
            "severity_proposed": "major", "priority_proposed": "high", "severity_rationale": "核心驗證規則失效", "environment": {"name": "stage"},
            "spec_id": "SPEC-AUTH-001", "spec_version": "1.0", "requirement_id": "REQ-AUTH-001", "acceptance_criteria_ids": ["AC-AUTH-002"],
            "testcase_id": tc[0], "testcase_version": tc[1], "execution_id": S["exe"], "preconditions": ["使用者在密碼設定頁"],
            "reproduction_steps": ["輸入長度 7 且含數字的密碼", "送出"], "expected_result": "系統拒絕，提示長度不足",
            "expected_result_spec_reference": {"spec_id": "SPEC-AUTH-001", "spec_version": "1.0", "location": "§3.1 R1"},
            "actual_result": "系統回 200 並接受密碼", "actual_result_evidence_map": [{"claim": "回 200 且 accepted=true", "evidence_id": evd}],
            "evidence_ids": [evd], "impact": "弱密碼可被建立", "suspected_area": "password validator", "ambiguity_suspected": False, "duplicate_candidates": []}

def test_12_bug_analyst_then_validator_pass():
    rid = S["run"]
    refs_ = [{"entity_type": "Requirement", "id": "REQ-AUTH-001"}, {"entity_type": "Evidence", "id": S["evd"]}, {"entity_type": "TestExecution", "id": S["exe"]},
             {"entity_type": "TestCaseVersion", "id": S["tc"][0], "version": S["tc"][1]}]
    bd, p = H.write_artifact(rid, "T1", "agent-bug-analyst", "BugDraft", _bug_draft(S["evd"], S["tc"]), refs_, {"type": "TestExecution", "ids": [S["exe"]]}, "bug-analysis")
    assert engine.submit(rid, "T1", str(p))[0] and engine.evaluate_gate(rid, "T1")["result"] == "PASS"
    b = store.load(f"runs/{rid}/entities/bug.yaml"); assert [h["to_status"] for h in b["history"]] == ["DRAFT", "VALIDATING"]
    rep = {"result": "PASS", "bug_draft_artifact_id": bd,
           "checks": {k: True for k in ["violates_spec", "expected_has_spec_basis", "actual_supported_by_evidence", "reproduction_sufficient", "severity_reasonable", "priority_reasonable", "not_duplicate", "not_mere_ambiguity"]},
           "issues": [], "evidence_verification": [{"evidence_id": S["evd"], "hash_verified": True, "supports_claim": True}],
           "severity_assessment": {"severity_recommended": "critical", "priority_recommended": "high", "agrees_with_analyst": False, "rationale": "安全相關，建議 critical"},
           "duplicate_check": {"searched": True, "duplicate_of": None}}
    vr, p = H.write_artifact(rid, "T2", "agent-bug-validator", "BugValidationReport", rep, [{"entity_type": "Artifact", "id": bd}, {"entity_type": "Evidence", "id": S["evd"]}], {"type": "BugDraft", "ids": [bd]}, "validation")
    assert engine.submit(rid, "T2", str(p))[0] and engine.evaluate_gate(rid, "T2")["result"] == "PASS"
    run = engine.load_run(rid); assert run["status"] == "WAITING_HUMAN"; S["apr"] = run["waiting_on_approval_id"]
    assert store.load(f"runs/{rid}/entities/bug.yaml")["status"] == "PENDING_APPROVAL"
    assert not list((store.ROOT / "bugs").rglob("BUG-*.yaml"))  # 未核准前 bugs/ 不得有正式檔

def test_13_open_bug_with_human_adjustment_and_manual_lifecycle(capsys):
    engine.approve(S["apr"], "approve", "oscar@example.com", adjustments={"severity": "critical"})
    bugs = list((store.ROOT / "bugs").rglob("BUG-*.yaml")); assert len(bugs) == 1
    b = store.load(bugs[0]); S["bug"] = b["bug_id"]
    assert b["status"] == "OPEN" and b["severity"] == "critical" and b["approved_by"] == "oscar@example.com" and b["validation_report_id"].startswith("ART-BVR")
    assert [h["to_status"] for h in b["history"]] == ["DRAFT", "VALIDATING", "VALIDATED", "PENDING_APPROVAL", "OPEN"]
    assert engine.load_run(S["run"])["status"] == "COMPLETED"
    cli(["trace", S["bug"]]); out = capsys.readouterr().out
    assert "Requirement REQ-AUTH-001" in out and f"Evidence {S['evd']}" in out and f"TestCase {S['tc'][0]}" in out
    cli(["bug", "transition", S["bug"], "--to", "IN_PROGRESS", "--by", "dev@example.com"]); capsys.readouterr()
    with pytest.raises(SystemExit): cli(["bug", "transition", S["bug"], "--to", "CLOSED", "--by", "dev@example.com"])       # IN_PROGRESS → CLOSED 不存在
    with pytest.raises(SystemExit): cli(["bug", "transition", S["bug"], "--to", "RESOLVED", "--by", "agent-bug-analyst"])  # Agent 不能推進

def test_14_regression_gate_rejects_manual_in_ci_and_commits_full():
    active = _active_tcs(); assert len(active) == 4
    manual = next(t for t in active if t[2]["execution_mode"] == "manual")
    run = engine.new_run("regression-generation", {"target_suites": ["ci_regression"], "scope": "all", "trigger": "manual"}, "oscar@example.com", new_request=True)
    prop = {"suite_id": "SUITE-CI", "suite_type": "ci_regression", "base_suite_version": None, "trigger": "manual",
            "proposed_memberships": [{"testcase_id": t[0], "pinned_version": "active", "justification": "high risk", "risk_tag": "auth"} for t in active],
            "diff": {"add": [{"testcase_id": t[0], "reason": "new"} for t in active], "remove": [], "repin": []},
            "selection_criteria": "all active", "summary": {"total": 4, "added": 4, "removed": 0, "repinned": 0}}
    rp, p = H.write_artifact(run["run_id"], "T1", "agent-regression-curator", "RegressionProposal", prop, [{"entity_type": "TestCase", "id": t[0]} for t in active], {"type": "Registry", "ids": []}, "regression")
    assert engine.submit(run["run_id"], "T1", str(p))[0]
    r = engine.evaluate_gate(run["run_id"], "T1"); assert r["result"] == "FAIL" and any(manual[0] in i and "manual" in i for i in r["issues"])
    # Full regression：全部 4 個 → PASS → approval → commit
    run2 = engine.new_run("regression-generation", {"target_suites": ["full_regression"], "scope": "all", "trigger": "manual"}, "oscar@example.com", new_request=True)
    prop.update({"suite_id": "SUITE-FULL", "suite_type": "full_regression"})
    rp, p = H.write_artifact(run2["run_id"], "T1", "agent-regression-curator", "RegressionProposal", prop, [{"entity_type": "TestCase", "id": t[0]} for t in active], {"type": "Registry", "ids": []}, "regression")
    assert engine.submit(run2["run_id"], "T1", str(p))[0] and engine.evaluate_gate(run2["run_id"], "T1")["result"] == "PASS"
    apr = engine.load_run(run2["run_id"])["waiting_on_approval_id"]
    assert not store.exists("testsuites/full-regression/SUITE-FULL.yaml")
    engine.approve(apr, "approve", "oscar@example.com")
    suite = store.load("testsuites/full-regression/SUITE-FULL.yaml")
    assert suite["status"] == "ACTIVE" and suite["version"] == 1 and len(suite["memberships"]) == 4 and all(m["added_by_approval"] == apr for m in suite["memberships"])
    assert "steps" not in suite["memberships"][0]  # Suite 不複製 TC 內容
    assert trace.suites_of(active[0][0])[0]["suite_id"] == "SUITE-FULL"
    assert engine.load_run(run2["run_id"])["status"] == "COMPLETED"

def test_15_change_impact_v1_1_supersedes_testcase(fixtures):
    """WF-C：v1.0 → v1.1（8 → 12），REQ-AUTH-001 changed，兩個 TC affected → 新版本 → APPLY_CHANGE → v2 ACTIVE、v1 SUPERSEDED。"""
    cli(["spec", "import", str(fixtures / "SPEC-AUTH-001-v1.1.md"), "--spec-id", "SPEC-AUTH-001", "--version", "1.1", "--product", "demo", "--area", "AUTH", "--change-summary", "密碼最小長度 8 → 12", "--by", "oscar@example.com"])
    run = engine.new_run("spec-change-impact", {"spec_id": "SPEC-AUTH-001", "from_version": "1.0", "to_version": "1.1"}, "oscar@example.com", new_request=True); rid = run["run_id"]
    assert run["current_task_id"] == "T0"  # to_version 尚無 RequirementModel
    rm = H.requirement_model("1.1", "12")
    sa = {"spec_id": "SPEC-AUTH-001", "spec_version": "1.1", "content_hash": store.load(store.spec_dir("SPEC-AUTH-001") / "spec.yaml")["versions"][1]["content_hash"], "summary": "v1.1", "scope": {"in_scope": [], "out_of_scope": []},
          "requirement_ids": [r["requirement_id"] for r in rm["requirements"]], "ambiguities": [], "constraints": [], "edge_case_candidates": [], "open_questions": []}
    refs_ = [{"entity_type": "SpecVersion", "id": "SPEC-AUTH-001", "version": "1.1"}]
    _, p1 = H.write_artifact(rid, "T0", "agent-spec-analyst", "SpecAnalysis", sa, refs_, {"type": "SpecVersion", "ids": []}, "spec-analysis")
    rmid, p2 = H.write_artifact(rid, "T0", "agent-spec-analyst", "RequirementModel", rm, refs_, {"type": "SpecVersion", "ids": []}, "requirements")
    assert engine.submit(rid, "T0", str(p1))[0] and engine.submit(rid, "T0", str(p2))[0] and engine.evaluate_gate(rid, "T0")["result"] == "PASS"
    active = _active_tcs(); affected = [t for t in active if "REQ-AUTH-001" in t[2]["requirement_ids"]]; assert len(affected) == 2
    cir = {"change_impact_id": "CI-SPEC-AUTH-001-1.0-1.1", "spec_id": "SPEC-AUTH-001", "from_version": "1.0", "to_version": "1.1",
           "requirement_diff": [{"requirement_id": "REQ-AUTH-001", "change": "changed", "detail": "8 → 12"}] + [{"requirement_id": r, "change": "unchanged"} for r in ["REQ-AUTH-002", "REQ-AUTH-003", "REQ-AUTH-004"]],
           "testcase_impact": [{"testcase_id": t[0], "active_version": t[1], "impact": "affected" if t in affected else "unaffected", "reason": "邊界值變更" if t in affected else "-", "affected_requirement_ids": ["REQ-AUTH-001"] if t in affected else []} for t in active],
           "summary": {"requirements_changed": 1, "requirements_added": 0, "requirements_removed": 0, "testcases_affected": 2, "testcases_obsolete": 0, "testcases_unaffected": 2},
           "completeness": {"all_active_requirements_judged": True, "all_referencing_testcases_judged": True}}
    # 漏判一個 TC → G-IMPACT FAIL
    bad = dict(cir, testcase_impact=cir["testcase_impact"][:-1], completeness={"all_active_requirements_judged": True, "all_referencing_testcases_judged": False})
    _, p = H.write_artifact(rid, "T1", "agent-change-impact-analyst", "ChangeImpactReport", bad, refs_, {"type": "SpecVersion", "ids": []}, "change-impact")
    assert engine.submit(rid, "T1", str(p))[0] and engine.evaluate_gate(rid, "T1")["result"] == "FAIL"
    cid, p = H.write_artifact(rid, "T1", "agent-change-impact-analyst", "ChangeImpactReport", cir, refs_ + [{"entity_type": "TestCaseVersion", "id": t[0], "version": t[1]} for t in active], {"type": "SpecVersion", "ids": []}, "change-impact")
    assert engine.submit(rid, "T1", str(p))[0] and engine.evaluate_gate(rid, "T1")["result"] == "PASS"
    assert store.load(f"runs/{rid}/entities/change-impact.yaml")["status"] == "TEST_UPDATE_REQUIRED"
    # Designer(change)：兩個新版本 supersedes v1
    tcs, ids_ = H.draft_set(12, prefix="01BX5ZZKBKACTAV9WEVGEMMVR")
    new = []
    for t, d in zip(affected, tcs[:2]):
        d = dict(d, spec_version="1.1", source="change_workflow", supersedes_testcase={"testcase_id": t[0], "version": t[1]}); d["expected_result_spec_reference"]["spec_version"] = "1.1"; new.append(d)
    refs2 = [{"entity_type": "Requirement", "id": "REQ-AUTH-001"}, {"entity_type": "Artifact", "id": cid}]
    did, pd = H.write_artifact(rid, "T2", "agent-test-designer", "TestCaseDraft", {"mode": "change", "spec_id": "SPEC-AUTH-001", "spec_version": "1.1", "change_impact_id": cir["change_impact_id"], "testcases": new}, refs2, {"type": "ChangeImpactReport", "ids": [cid]}, "test-design")
    assert engine.submit(rid, "T2", str(pd))[0]
    rep = H.design_report(did, new); rep["mode"] = "change"
    _, pr = H.write_artifact(rid, "T2", "agent-test-designer", "TestDesignReport", rep, [{"entity_type": "Artifact", "id": did}], {"type": "TestCaseDraft", "ids": [did]}, "test-design")
    assert engine.submit(rid, "T2", str(pr))[0] and engine.evaluate_gate(rid, "T2")["result"] == "PASS"
    vr, p = H.write_artifact(rid, "T3", "agent-test-validator", "TestValidationReport", H.validation_report(did, rmid, "PASS", spec_version="1.1"), [{"entity_type": "Artifact", "id": did}], {"type": "TestCaseDraft", "ids": [did]}, "validation")
    assert engine.submit(rid, "T3", str(p))[0] and engine.evaluate_gate(rid, "T3")["result"] == "PASS"
    for t in affected:
        assert store.load(store.tc_version_path(t[0], 2))["status"] == "VALIDATED" and store.load(store.tc_pointer_path(t[0]))["active_version"] == 1  # pointer 未動
    vcr = {"change_impact_id": cir["change_impact_id"], "comparisons": [{"testcase_id": t[0], "old_version": 1, "new_draft_id": d["draft_id"], "verdict": "changed",
           "field_diffs": [{"field": "steps[0]", "old": "8", "new": "12"}], "impacted_requirement_ids": ["REQ-AUTH-001"]} for t, d in zip(affected, new)],
           "retire_recommendations": [], "summary": {"unchanged": 0, "changed": 2, "added": 0, "removed": 0}}
    _, p = H.write_artifact(rid, "T4", "agent-change-impact-analyst", "VersionComparisonReport", vcr, [{"entity_type": "Artifact", "id": cid}], {"type": "x", "ids": []}, "change-impact")
    assert engine.submit(rid, "T4", str(p))[0] and engine.evaluate_gate(rid, "T4")["result"] == "PASS"
    run = engine.load_run(rid); apr = store.load(f"approvals/{run['waiting_on_approval_id']}.yaml")
    assert apr["type"] == "APPLY_CHANGE" and "是否將此新版 Test Case 更新為正式 Registry 版本" in apr["summary"]
    engine.approve(apr["approval_id"], "approve", "oscar@example.com")
    for t in affected:
        ptr = store.load(store.tc_pointer_path(t[0])); assert ptr["active_version"] == 2
        assert store.load(store.tc_version_path(t[0], 1))["status"] == "SUPERSEDED" and store.load(store.tc_version_path(t[0], 2))["status"] == "ACTIVE"
        assert store.load(store.tc_version_path(t[0], 2))["supersedes"] == 1
    assert store.load(f"runs/{rid}/entities/change-impact.yaml")["status"] == "APPLIED" and engine.load_run(rid)["status"] == "COMPLETED"
    # Suite pinned "active" 自動跟隨；v1 檔案仍在（歷史保留）
    assert trace.suites_of(affected[0][0])[0]["pinned_version"] == "active" and store.exists(store.tc_version_path(affected[0][0], 1))
