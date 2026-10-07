"""Clarification（問 PM 的單）：手動生命週期、與 RESOLVE_AMBIGUITY 的自動接線；bug index。"""
import pytest
from tests.helpers import raw_save
from tools.qaos import store, engine, clarification as clr, clr_lifecycle, bugindex
from tools.qaos.cli import main as cli
from tools.qaos.engine import EngineError
from tools.qaos.state import TransitionError
from tests import helpers as H

def test_20_manual_clarification_lifecycle(capsys):
    cli(["clarification", "new", "--product", "demo", "--area", "AUTH", "--spec-id", "SPEC-AUTH-001", "--spec-version", "1.1",
         "--question", "密碼長度 12 是否含全形字元？", "--context", "R1 未定義字元計數方式", "--option", "以 Unicode code point 計", "--option", "以 byte 計", "--no-source-check", "--reason", "手動補問，未附查閱證據", "--by", "oscar@example.com"])
    cid = capsys.readouterr().out.split()[0]; assert cid.startswith("CLR-AUTH-")
    c = clr.load(cid); assert c["status"] == "OPEN" and (store.ROOT / "clarifications/demo/AUTH" / f"{cid}.md").exists()
    with pytest.raises(ValueError, match="需要 CLR 狀態"):                                      # ADR-010：OPEN 不能 apply（三條路徑都不接受 OPEN）
        clr_lifecycle.apply(cid, "a7", "oscar@example.com", no_keyword_reason="x", impact_reviewed="x")
    with pytest.raises(TransitionError): clr.ask(cid, "pm@example.com", "agent-spec-analyst")  # Agent 不能送單
    clr.ask(cid, "pm@example.com", "oscar@example.com"); assert clr.load(cid)["status"] == "ASKED"
    clr.answer(cid, "以 Unicode code point 計；規格本身不需修改", "pm@example.com", "no_change", "oscar@example.com")
    c = clr.load(cid); assert c["status"] == "ANSWERED" and "PM 回覆" in (store.ROOT / "clarifications/demo/AUTH" / f"{cid}.md").read_text()
    with pytest.raises(ValueError, match="INCORPORATED"): clr_lifecycle.apply(cid, "a6", "oscar@example.com", landed_in=["RUN-X"], no_keyword_reason="x", impact_reviewed="x")   # 路徑和狀態不符
    with pytest.raises(ValueError, match="--impact-reviewed"): clr_lifecycle.apply(cid, "a7", "oscar@example.com", no_keyword_reason="x", impact_reviewed=" ")
    cands = clr_lifecycle.impact(cid, [], [], "oscar@example.com")["candidates"]                 # 背景候選（原題需求）與關鍵字候選
    clr_lifecycle.apply(cid, "a7", "oscar@example.com", no_keyword_reason="答案不改變規格，原題沒有掛需求", tc_conclusions=[f"{x['tc_id']}=not_affected" for x in cands],
                        impact_reviewed="無 ACTIVE TC 受影響")
    c = clr.load(cid); assert c["status"] == "APPLIED" and c["landings"][-1]["path"] == "a7" and c["landings"][-1]["no_keyword_reason"].startswith("答案不改變")
    cli(["clarification", "list", "--all"]); assert cid in capsys.readouterr().out   # list 是唯讀指令，不寫檔
    cli(["clarification", "index"]); assert (store.ROOT / "clarifications/index.md").exists()

def _fake_active_tc(tc_id, area, req, title, steps, expected, product="demo"):
    """直接寫 registry pointer + version（impact 掃描只讀這兩個檔）。"""
    raw_save(store.tc_pointer_path(tc_id), {"testcase_id": tc_id, "active_version": 1, "status": "ACTIVE", "versions": [{"version": 1, "status": "ACTIVE"}]})
    raw_save(store.tc_version_path(tc_id, 1), {"testcase_id": tc_id, "version": 1, "status": "ACTIVE", "product": product, "functional_area": area, "title": title,
                                                  "requirement_ids": [req], "preconditions": [], "steps": [{"n": i + 1, "action": a} for i, a in enumerate(steps)], "expected_result": expected})

def test_20b_clarification_impact_scan_lists_requirement_and_keyword_hits(capsys, tmp_path):
    """ADR-008：impact 掃同 product/area 的 ACTIVE TC——掛同 requirement 者、步驟／expected 命中關鍵詞者；其他 area、非 ACTIVE、無命中者不列。"""
    f = tmp_path / "imp.md"; f.write_text("# IMP\n\n明細規格。\n", encoding="utf-8")       # 回答時要記錄 basis（需求 A 第 3 章 §7），CLR 的 spec 必須已匯入
    cli(["spec", "import", str(f), "--spec-id", "SPEC-IMP-001", "--version", "1.0", "--product", "demo", "--area", "IMP", "--by", "oscar@example.com"]); capsys.readouterr()
    _fake_active_tc("TC-IMP-001", "IMP", "REQ-IMP-001", "掛同一需求", ["做 A"], "看到 A")
    _fake_active_tc("TC-IMP-002", "IMP", "REQ-IMP-002", "步驟提到進行中", ["讓機台有進行中場次"], "看到列")
    _fake_active_tc("TC-IMP-003", "IMP", "REQ-IMP-002", "expected 提到新場次", ["做 B"], "系統建立新場次")
    _fake_active_tc("TC-IMP-004", "IMP", "REQ-IMP-002", "不相干", ["做 C"], "看到 C")
    _fake_active_tc("TC-IMP-005", "OTHER", "REQ-IMP-001", "別的 area 掛同需求", ["做 D"], "看到 D")
    ptr = store.load(store.tc_pointer_path("TC-IMP-004")); ptr["status"] = "RETIRED"; ptr["active_version"] = None; raw_save(store.tc_pointer_path("TC-IMP-004"), ptr)
    _fake_active_tc("TC-IMP-006", "IMP", "REQ-IMP-002", "已退役但提到進行中", ["進行中"], "x")
    ptr = store.load(store.tc_pointer_path("TC-IMP-006")); ptr["status"] = "RETIRED"; ptr["active_version"] = None; raw_save(store.tc_pointer_path("TC-IMP-006"), ptr)
    c = clr.new("demo", "IMP", "SPEC-IMP-001", "1.0", "明細是否列進行中？", "oscar@example.com", no_source_check_reason="測試 fixture（入口 D，未附查閱證據）", requirement_id="REQ-IMP-001")
    clr.ask(c["clarification_id"], "pm@example.com", "oscar@example.com"); clr.answer(c["clarification_id"], "不列", "pm@example.com", "out_of_scope", "oscar@example.com")
    scan = clr_lifecycle.impact(c["clarification_id"], ["進行中", "新場次"], [], "oscar@example.com")     # ADR-010：impact 保存掃描紀錄
    cands = {x["tc_id"]: x["reasons"] for x in scan["candidates"]}
    assert cands == {"TC-IMP-001": ["clr_requirement"], "TC-IMP-002": ["keyword:進行中"], "TC-IMP-003": ["keyword:新場次"]}
    assert scan["scan_units"] == [{"product": "demo", "area": "IMP"}] and (store.ROOT / f"clarifications/demo/IMP/scans/{c['clarification_id']}-{scan['scan_id']}.yaml").exists()
    cli(["clarification", "impact", c["clarification_id"], "--keyword", "進行中", "--by", "oscar@example.com"]); out = capsys.readouterr().out
    assert "TC-IMP-002" in out and "TC-IMP-001" in out and "TC-IMP-005" not in out and "TC-IMP-006" not in out
    with pytest.raises(ValueError, match="缺少 --tc-conclusion"):                                  # 每張候選都要有結論
        clr_lifecycle.apply(c["clarification_id"], "a7", "oscar@example.com", scan_id=scan["scan_id"], tc_conclusions=["TC-IMP-001=not_affected"], impact_reviewed="x")
    clr_lifecycle.apply(c["clarification_id"], "a7", "oscar@example.com", scan_id=scan["scan_id"],
                        tc_conclusions=["TC-IMP-001=not_affected", "TC-IMP-002=updated", "TC-IMP-003=deferred:等 PM 補充畫面"], impact_reviewed="001 不受影響；002 已修訂；003 延後")
    l = clr.load(c["clarification_id"])["landings"][-1]
    assert l["path"] == "a7" and l["final_keywords"] == ["新場次", "進行中"] and l["scan_id"] == scan["scan_id"] and l["scan_reused"] == "full"
    assert {x["tc_id"] for x in l["candidates"]} == {"TC-IMP-001", "TC-IMP-002", "TC-IMP-003"} and all(x["tc_version_sha256"] for x in l["candidates"])
    show = clr_lifecycle.show(c["clarification_id"])
    assert {"tc_id": "TC-IMP-003", "conclusion": "deferred:等 PM 補充畫面"} in show["follow_ups"]

def test_21_critical_ambiguity_opens_clarification_and_blocks_approve(fixtures):
    cli(["spec", "import", str(fixtures / "SPEC-AUTH-001-v1.0.md"), "--spec-id", "SPEC-PAY-001", "--version", "1.0", "--product", "demo", "--area", "PAY", "--by", "oscar@example.com"])
    run = engine.new_run("spec-to-testcase", {"spec_id": "SPEC-PAY-001", "spec_version": "1.0"}, "oscar@example.com", new_request=True); rid = run["run_id"]
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
    assert clr.load(clrs[0])["status"] == "ANSWERED"                                       # ADR-010：核准不再 apply CLR（由人以 apply 確認結案）
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
    run = engine.new_run("spec-to-testcase", {"spec_id": "SPEC-NEG-001", "spec_version": "1.0"}, "oscar@example.com", new_request=True); rid = run["run_id"]
    tcs, _ = __import__("tests.test_wf_y_negative_coverage", fromlist=["_tcs"])._tcs(prefix="01JZZZZZZZZZZZZZZZZZZZZZZ")
    refs_ = [{"entity_type": "Requirement", "id": r} for r in sorted({r for t in tcs for r in t["requirement_ids"]})]
    did, p = H.write_artifact(rid, "T2", "agent-test-designer", "TestCaseDraft", {"mode": "spec", "spec_id": "SPEC-NEG-001", "spec_version": "1.0", "testcases": tcs}, refs_, {"type": "x", "ids": []}, "test-design")
    assert engine.submit(rid, "T2", str(p))[0]
    assert store.load(p)["status"] == "VALID"
    ok, problems = engine.submit(rid, "T2", str(p))   # 同一請求重送：冪等，回報先前的結果，不再寫入
    assert ok and store.load(p)["status"] == "VALID"
    ok, problems = engine.submit(rid, "T2", str(p), new_request=True)   # 刻意再提交一次同一份已 VALID 的檔案
    assert not ok and any("不可提交" in x for x in problems)
    assert store.load(p)["status"] == "VALID"   # 狀態不得被覆寫成 INVALID
    engine.cancel(rid, "oscar@example.com")
