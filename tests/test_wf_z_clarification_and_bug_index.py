"""Clarification（問 PM 的單）：手動生命週期、與 RESOLVE_AMBIGUITY 的自動接線；bug index。"""
import pytest
from tools.qaos import store, engine, clarification as clr, bugindex
from tools.qaos.cli import main as cli
from tools.qaos.engine import EngineError
from tools.qaos.state import TransitionError
from tests import helpers as H

def test_20_manual_clarification_lifecycle(capsys):
    cli(["clarification", "new", "--product", "demo", "--area", "AUTH", "--spec-id", "SPEC-AUTH-001", "--spec-version", "1.1",
         "--question", "密碼長度 12 是否含全形字元？", "--context", "R1 未定義字元計數方式", "--option", "以 Unicode code point 計", "--option", "以 byte 計", "--by", "oscar@example.com"])
    cid = capsys.readouterr().out.split()[0]; assert cid.startswith("CLR-AUTH-")
    c = clr.load(cid); assert c["status"] == "OPEN" and (store.ROOT / "clarifications/demo/AUTH" / f"{cid}.md").exists()
    with pytest.raises(TransitionError): clr.apply_(cid, "oscar@example.com")            # OPEN → APPLIED 不存在
    with pytest.raises(TransitionError): clr.ask(cid, "pm@example.com", "agent-spec-analyst")  # Agent 不能送單
    clr.ask(cid, "pm@example.com", "oscar@example.com"); assert clr.load(cid)["status"] == "ASKED"
    clr.answer(cid, "以 Unicode code point 計", "pm@example.com", "requirement_clarified", "oscar@example.com")
    c = clr.load(cid); assert c["status"] == "ANSWERED" and "PM 回覆" in (store.ROOT / "clarifications/demo/AUTH" / f"{cid}.md").read_text()
    clr.apply_(cid, "oscar@example.com"); assert clr.load(cid)["status"] == "APPLIED"
    cli(["clarification", "list", "--all"]); assert cid in capsys.readouterr().out and (store.ROOT / "clarifications/index.md").exists()

def test_21_critical_ambiguity_opens_clarification_and_blocks_approve(fixtures):
    cli(["spec", "import", str(fixtures / "SPEC-AUTH-001-v1.0.md"), "--spec-id", "SPEC-PAY-001", "--version", "1.0", "--product", "demo", "--area", "PAY", "--by", "oscar@example.com"])
    run = engine.new_run("spec-to-testcase", {"spec_id": "SPEC-PAY-001", "spec_version": "1.0"}, "oscar@example.com"); rid = run["run_id"]
    rm = H.requirement_model(); 
    for r in rm["requirements"]:
        r["spec_id"] = "SPEC-PAY-001"; r["requirement_id"] = r["requirement_id"].replace("AUTH", "PAY"); r["spec_reference"]["spec_id"] = "SPEC-PAY-001"
        for ac in r["acceptance_criteria"]: ac["ac_id"] = ac["ac_id"].replace("AUTH", "PAY")
    for t in rm["traceability"]: t["requirement_id"] = t["requirement_id"].replace("AUTH", "PAY"); t["spec_reference"]["spec_id"] = "SPEC-PAY-001"
    rm["spec_id"] = "SPEC-PAY-001"
    rm["requirements"][0]["ambiguity"] = {"level": "critical", "description": "「8 個字元」是否含全形？", "options": ["code point", "byte"]}
    h = store.load(store.spec_dir("SPEC-PAY-001") / "spec.yaml")["versions"][0]["content_hash"]
    sa = {"spec_id": "SPEC-PAY-001", "spec_version": "1.0", "content_hash": h, "summary": "x", "scope": {"in_scope": [], "out_of_scope": []},
          "requirement_ids": [r["requirement_id"] for r in rm["requirements"]], "ambiguities": [{"requirement_id": "REQ-PAY-001", "ambiguity": rm["requirements"][0]["ambiguity"]}],
          "constraints": [], "edge_case_candidates": [], "open_questions": []}
    refs_ = [{"entity_type": "SpecVersion", "id": "SPEC-PAY-001", "version": "1.0"}]
    _, p1 = H.write_artifact(rid, "T1", "agent-spec-analyst", "SpecAnalysis", sa, refs_, {"type": "SpecVersion", "ids": []}, "spec-analysis")
    _, p2 = H.write_artifact(rid, "T1", "agent-spec-analyst", "RequirementModel", rm, refs_, {"type": "SpecVersion", "ids": []}, "requirements")
    assert engine.submit(rid, "T1", str(p1))[0] and engine.submit(rid, "T1", str(p2))[0] and engine.evaluate_gate(rid, "T1")["result"] == "PASS"
    run = engine.load_run(rid); apr = store.load(f"approvals/{run['waiting_on_approval_id']}.yaml")
    assert run["status"] == "WAITING_HUMAN" and apr["type"] == "RESOLVE_AMBIGUITY"
    clrs = [i["id"] for i in apr["impact"] if i["entity_type"] == "Clarification"]; assert len(clrs) == 1
    c = clr.load(clrs[0]); assert c["requirement_id"] == "REQ-PAY-001" and c["approval_id"] == apr["approval_id"] and c["options"] == ["code point", "byte"]
    reqs = store.load(store.requirements_path("SPEC-PAY-001", "1.0"))["requirements"]
    assert reqs[0]["status"] == "DRAFT" and all(r["status"] == "ACTIVE" for r in reqs[1:])   # critical 的停在 DRAFT，其他 ACTIVE
    with pytest.raises(EngineError): engine.approve(apr["approval_id"], "approve", "oscar@example.com", selected_option="resolved")  # PM 未回答不得 approve
    assert store.load(f"approvals/{apr['approval_id']}.yaml")["status"] == "PENDING"
    clr.answer(clrs[0], "以 code point 計", "pm@example.com", "requirement_clarified", "oscar@example.com")
    engine.approve(apr["approval_id"], "approve", "oscar@example.com", selected_option="resolved")
    assert clr.load(clrs[0])["status"] == "APPLIED"
    run = engine.load_run(rid); assert run["status"] == "RUNNING" and run["current_task_id"] == "T1" and run["tasks"][0]["iteration"] == 1  # T1 重開讓 Spec Analyst 帶答案重產

def test_22_bug_index():
    n = bugindex.build(); assert n >= 1
    assert (store.ROOT / "bugs/index.md").exists() and (store.ROOT / "bugs/demo/AUTH/index.md").exists()
    assert "BUG-AUTH-001" in (store.ROOT / "bugs/demo/AUTH/index.md").read_text()

def test_23_tc_retire_and_revise_run():
    from tools.qaos import tc_ops, engine, store
    from tools.qaos.engine import EngineError
    active = sorted(p.stem for p in (store.ROOT / "testcases/registry").glob("TC-AUTH-*.yaml") if store.load(p)["status"] == "ACTIVE")
    tc = active[0]
    run = tc_ops.revise(tc, "PM 改口徑", "oscar@example.com")
    assert run["workflow_id"] == "testcase-revision" and run["current_task_id"] == "T1" and run["input"]["testcase_id"] == tc
    engine.cancel(run["run_id"], "oscar@example.com")
    apr, suites = tc_ops.retire(tc, "oscar@example.com", "重複案例")
    ptr = store.load(store.tc_pointer_path(tc)); assert ptr["status"] == "RETIRED" and ptr["active_version"] is None
    assert store.load(f"approvals/{apr}.yaml")["type"] == "RETIRE_TESTCASE"
    with pytest.raises(EngineError): tc_ops.retire(tc, "oscar@example.com", "again")
    with pytest.raises(EngineError): tc_ops.revise(tc, "x", "oscar@example.com")
    rid = tc_ops.manual_new("手動案例", "demo", "AUTH", ["步驟一", "步驟二"], "觀察結果", "pass", "oscar@example.com", "SPEC-AUTH-001", "1.1")
    assert store.exists(f"testcases/manual/{rid}.yaml")

def test_24_resubmit_already_valid_artifact_does_not_corrupt_it():
    """engine bug fix (2026-09-14)：重複提交一份已是 VALID 的 artifact，不得把它的狀態改成 INVALID。"""
    from tools.qaos import engine, store
    from tests import helpers as H
    run = engine.new_run("spec-to-testcase", {"spec_id": "SPEC-NEG-001", "spec_version": "1.0"}, "oscar@example.com"); rid = run["run_id"]
    tcs, _ = __import__("tests.test_wf_y_negative_coverage", fromlist=["_tcs"])._tcs(prefix="01JZZZZZZZZZZZZZZZZZZZZZZ")
    refs_ = [{"entity_type": "Requirement", "id": r} for r in sorted({r for t in tcs for r in t["requirement_ids"]})]
    did, p = H.write_artifact(rid, "T2", "agent-test-designer", "TestCaseDraft", {"mode": "spec", "spec_id": "SPEC-NEG-001", "spec_version": "1.0", "testcases": tcs}, refs_, {"type": "x", "ids": []}, "test-design")
    assert engine.submit(rid, "T2", str(p))[0]
    assert store.load(p)["status"] == "VALID"
    ok, problems = engine.submit(rid, "T2", str(p))   # 重複提交同一份已 VALID 的檔案
    assert not ok and any("不可提交" in x for x in problems)
    assert store.load(p)["status"] == "VALID"   # 狀態不得被覆寫成 INVALID
    engine.cancel(rid, "oscar@example.com")
