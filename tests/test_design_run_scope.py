"""ADR-013：spec-to-testcase 的 input.scope 寫成需求清單時，G-DESIGN 只要求 scope 內需求的覆蓋與規則；派發包帶出解析後的 scope。"""
import copy, pytest
from tools.qaos import store, engine, dispatch, gates, run_scope
from tools.qaos.cli import main as cli
from tests import helpers as H

SPEC, AREA = "SPEC-DSC-001", "DSC"
BY = "oscar@example.com"
S = {}

def _rm():
    rm = copy.deepcopy(H.requirement_model()); rm["spec_id"] = SPEC
    for r in rm["requirements"]:
        r["spec_id"] = SPEC; r["requirement_id"] = r["requirement_id"].replace("AUTH", AREA); r["spec_reference"]["spec_id"] = SPEC
        for ac in r["acceptance_criteria"]: ac["ac_id"] = ac["ac_id"].replace("AUTH", AREA)
    for t in rm["traceability"]: t["requirement_id"] = t["requirement_id"].replace("AUTH", AREA); t["spec_reference"]["spec_id"] = SPEC
    return rm

def _tcs(prefix):
    tcs, ids_ = H.draft_set(prefix=prefix)
    for t in tcs:
        t["spec_id"] = SPEC; t["functional_area"] = AREA; t["expected_result_spec_reference"]["spec_id"] = SPEC
        t["requirement_ids"] = [r.replace("AUTH", AREA) for r in t["requirement_ids"]]; t["acceptance_criteria_ids"] = [a.replace("AUTH", AREA) for a in t["acceptance_criteria_ids"]]
    return tcs, ids_

def _submit_design(rid, tcs, uncovered=None):
    it = engine._task(engine.load_run(rid), "T2")["iteration"]
    refs_ = [{"entity_type": "Requirement", "id": r} for r in sorted({r for t in tcs for r in t["requirement_ids"]})]
    did, pd = H.write_artifact(rid, "T2", "agent-test-designer", "TestCaseDraft", {"mode": "spec", "spec_id": SPEC, "spec_version": "1.0", "testcases": tcs},
                               refs_, {"type": "RequirementModel", "ids": []}, "test-design", iteration=it)
    assert engine.submit(rid, "T2", str(pd))[0], "draft submit"
    rep = H.design_report(did, tcs, uncovered=uncovered)
    _, pr = H.write_artifact(rid, "T2", "agent-test-designer", "TestDesignReport", rep, [{"entity_type": "Artifact", "id": did}], {"type": "TestCaseDraft", "ids": [did]}, "test-design", iteration=it)
    assert engine.submit(rid, "T2", str(pr))[0], "report submit"
    return engine.evaluate_gate(rid, "T2")

def _packet(rid, task_id):
    return dispatch.load_packet(dispatch.current_entry(engine._task(engine.load_run(rid), task_id)))

# ---------------------------------------------------------------- 解析
@pytest.mark.parametrize("text, want", [
    ("REQ-ARCADE-004", ["REQ-ARCADE-004"]),
    ("REQ-DAILYREPORT-008,REQ-DAILYREPORT-014（CLR-DAILYREPORT-013 新增 AC-0083、AC-0143 的 TC）", ["REQ-DAILYREPORT-008", "REQ-DAILYREPORT-014"]),
    ("REQ-DAILYREPORT-001,005,007,010（T3RR 風險抽查補強：RUN-20261012-007 RF-02/03）", ["REQ-DAILYREPORT-001", "REQ-DAILYREPORT-005", "REQ-DAILYREPORT-007", "REQ-DAILYREPORT-010"]),
    ("  REQ-A-001， 002、REQ-B-010, 011 (note, with comma)", ["REQ-A-001", "REQ-A-002", "REQ-B-010", "REQ-B-011"]),
    ("REQ-A-001,001,REQ-A-001", ["REQ-A-001"]),
    ("REQ-A-001,002（說明（含括號）與 REQ-A-009 的關係）", ["REQ-A-001", "REQ-A-002"]),
    # 主目錄既有 run 的實際寫法
    ("REQ-REDPACKET-008,010,011,013,014,015,016,017,023,024,025,031,032,036,039（T3RR 風險抽查補強：RUN-20261012-002 RF-01/02/03/05/07/08/09/11/12/15/16）",
     [f"REQ-REDPACKET-{n}" for n in "008 010 011 013 014 015 016 017 023 024 025 031 032 036 039".split()]),
    ("REQ-CASHOUT-001,006,018,022,024,028,029,031,032（T3RR 風險抽查補強：RUN-20261012-006 RF-03/04/05/12/14/15/17/18）",
     [f"REQ-CASHOUT-{n}" for n in "001 006 018 022 024 028 029 031 032".split()]),
    ("DAILYREPORT", None), ("日結報表全部需求", None), ("", None), (None, None),
])
def test_parse_formats(text, want):
    assert run_scope.parse(text) == want

@pytest.mark.parametrize("text", ["REQ-A-001 補強", "REQ-A-001,abc", "REQ-A-001,", "req-a-001", "REQ-A-001,,002", "REQ-（說明）", 5, ["REQ-A-001"],
    "REQ-A-001（補 AC-0011）、REQ-A-002（補 AC-0021）", "REQ-A-001 (x) REQ-A-002", "REQ-A-001（說明", "REQ-A-001）", "REQ-A-001（a（b）",
    "REQ-A-001,5", "REQ-A-1", "REQ-A-01,002"])
def test_parse_rejects_malformed_req_list(text):
    with pytest.raises(run_scope.ScopeError):
        run_scope.parse(text)

def test_parse_error_message_shows_correct_form():
    with pytest.raises(run_scope.ScopeError, match="REQ-DAILYREPORT-001,005（T3RR 補強）"):
        run_scope.parse("REQ-A-001（x）、REQ-A-002")

def test_pin_issues_unknown_and_not_designable():
    act = {"status": "ACTIVE", "ambiguity": None}
    crit = {"status": "ACTIVE", "ambiguity": {"level": "critical"}}
    resolved = {"status": "ACTIVE", "ambiguity": {"level": "critical", "resolved_by_approval": "APR-0001"}}
    dep = {"status": "DEPRECATED"}
    assert run_scope.pin_issues(["REQ-A-001", "REQ-A-009"], {"REQ-A-001": act}, "R") == ["run 的 scope 列出的 REQ-A-009 不在綁定的 R"]
    assert "沒有任何可設計的需求" in run_scope.pin_issues(["REQ-A-001", "REQ-A-002"], {"REQ-A-001": crit, "REQ-A-002": dep}, "R")[0]
    assert run_scope.pin_issues(["REQ-A-001", "REQ-A-002"], {"REQ-A-001": crit, "REQ-A-002": resolved}, "R") == []

def test_requirement_ids_only_for_spec_to_testcase_and_tolerates_legacy():
    assert run_scope.requirement_ids({"workflow_id": "spec-to-testcase", "input": {"scope": "REQ-A-001,002"}}) == ["REQ-A-001", "REQ-A-002"]
    assert run_scope.requirement_ids({"workflow_id": "regression-generation", "input": {"scope": "REQ-A-001"}}) is None
    assert run_scope.requirement_ids({"workflow_id": "spec-to-testcase", "input": {"scope": "REQ-A-001 補強"}}) is None   # 變更前建立的不合語法 run：原本的行為
    assert run_scope.packet_field({"workflow_id": "spec-to-testcase", "input": {}}) is None
    assert run_scope.packet_field({"workflow_id": "spec-to-testcase", "input": {"scope": "DSC"}}) == {"raw": "DSC", "requirement_ids": None}

# ---------------------------------------------------------------- 流程
def test_10_setup_and_new_run_rejects_malformed_scope(fixtures):
    cli(["spec", "import", str(fixtures / "SPEC-AUTH-001-v1.0.md"), "--spec-id", SPEC, "--version", "1.0", "--product", "demo", "--area", AREA, "--by", BY])
    with pytest.raises(engine.EngineError, match="不是需求 ID"):
        engine.new_run("spec-to-testcase", {"spec_id": SPEC, "spec_version": "1.0", "scope": "REQ-DSC-002 補強"}, BY, new_request=True)
    run = engine.new_run("spec-to-testcase", {"spec_id": SPEC, "spec_version": "1.0", "scope": "REQ-DSC-002,004（T3RR 補強）"}, BY, new_request=True)
    rid = S["run"] = run["run_id"]
    rm = _rm(); h = store.load(store.spec_dir(SPEC) / "spec.yaml")["versions"][0]["content_hash"]
    sa = {"spec_id": SPEC, "spec_version": "1.0", "content_hash": h, "summary": "x", "scope": {"in_scope": [], "out_of_scope": []},
          "requirement_ids": [r["requirement_id"] for r in rm["requirements"]], "ambiguities": [], "constraints": [], "edge_case_candidates": [], "open_questions": []}
    refs_ = [{"entity_type": "SpecVersion", "id": SPEC, "version": "1.0"}]
    _, p1 = H.write_artifact(rid, "T1", "agent-spec-analyst", "SpecAnalysis", sa, refs_, {"type": "SpecVersion", "ids": []}, "spec-analysis")
    _, p2 = H.write_artifact(rid, "T1", "agent-spec-analyst", "RequirementModel", rm, refs_, {"type": "SpecVersion", "ids": []}, "requirements")
    assert engine.submit(rid, "T1", str(p1))[0] and engine.submit(rid, "T1", str(p2))[0]
    assert engine.evaluate_gate(rid, "T1")["result"] == "PASS"
    assert "run_scope" not in _packet(rid, "T1")                                  # Spec Analyst 分析整份 spec，派發包不帶 scope

def test_11_scope_limits_coverage_and_rules():
    rid = S["run"]; tcs, ids_ = _tcs("01EZZZZZZZZZZZZZZZZZZZZZZ")
    # (a) 只交 scope 內的 REQ-002；REQ-004（scope 內）沒覆蓋也沒理由；另一條 TC 只涉及 scope 外的 REQ-003
    r = _submit_design(rid, [tcs[2], tcs[3]])
    assert _packet(rid, "T2")["run_scope"] == {"raw": "REQ-DSC-002,004（T3RR 補強）", "requirement_ids": ["REQ-DSC-002", "REQ-DSC-004"]}
    msgs = "\n".join(r["issues"])
    assert r["result"] == "FAIL"
    assert "requirement REQ-DSC-004 未被覆蓋且無 uncovered_with_reason" in msgs
    assert f"{ids_[3]} 的 requirement_ids（REQ-DSC-003）都不在本 run 的 scope 內" in msgs
    assert "REQ-DSC-001" not in msgs                                              # scope 外、沒有 TC 涉及的 high-risk 需求不檢查

def test_12_out_of_scope_requirement_touched_by_tc_still_gets_rules():
    rid = S["run"]; tcs, ids_ = _tcs("01FZZZZZZZZZZZZZZZZZZZZZZ")
    # REQ-002 的 TC 同時涉及 scope 外的 high-risk REQ-001，但只有 happy path → REQ-001 仍要符合 high-risk 規則
    extra = tcs[0]; extra["requirement_ids"] = ["REQ-DSC-002", "REQ-DSC-001"]; extra["test_types"] = ["functional"]; extra["design_techniques"] = ["requirement_based"]
    r = _submit_design(rid, [tcs[2], tcs[4], extra])
    assert r["result"] == "FAIL" and any("REQ-DSC-001 為 high risk" in i for i in r["issues"]), r["issues"]
    assert not any("REQ-DSC-003" in i for i in r["issues"])

def test_13_pass_without_listing_out_of_scope_and_legacy_uncovered_is_ignored():
    rid = S["run"]; tcs, _ = _tcs("01GZZZZZZZZZZZZZZZZZZZZZZ")
    # 舊寫法：把 scope 外的 high-risk 需求列進 uncovered 但沒有 NO_REJECTION_CONTRACT 前綴 → 不再檢查
    legacy = [{"requirement_id": "REQ-DSC-001", "reason": "不在本 run scope"}, {"requirement_id": "REQ-DSC-003", "reason": "不在本 run scope"}]
    r = _submit_design(rid, [tcs[2], tcs[4]], uncovered=legacy)
    assert r["result"] == "PASS", r["issues"]
    run = engine.load_run(rid); assert run["current_task_id"] == "T3"
    H.packet_sha(rid, "T3")                                                       # Validator 的派發包也帶 scope
    assert _packet(rid, "T3")["run_scope"]["requirement_ids"] == ["REQ-DSC-002", "REQ-DSC-004"]

def test_14_no_scope_or_free_text_keeps_full_coverage():
    for inputs in ({}, {"scope": "DSC 全面補強"}):
        run = engine.new_run("spec-to-testcase", {"spec_id": SPEC, "spec_version": "1.0", **inputs}, BY, new_request=True)
        rid = run["run_id"]; assert run["current_task_id"] == "T2"                # T1 跳過，綁定最新 revision
        tcs, _ = _tcs("01HZZZZZZZZZZZZZZZZZZZZZZ" if not inputs else "01JZZZZZZZZZZZZZZZZZZZZZZ")
        r = _submit_design(rid, [tcs[2], tcs[4]])
        assert r["result"] == "FAIL" and any("requirement REQ-DSC-001 未被覆蓋" in i for i in r["issues"]) and any("requirement REQ-DSC-003 未被覆蓋" in i for i in r["issues"])
        pk = _packet(rid, "T2")
        assert pk.get("run_scope") == ({"raw": "DSC 全面補強", "requirement_ids": None} if inputs else None)

def test_15_unknown_requirement_in_scope_rejected_at_new_run_when_bound():
    before = sorted(p.name for p in (store.ROOT / "runs").iterdir())
    with pytest.raises(engine.EngineError, match="REQ-DSC-099 不在綁定的 SPEC-DSC-001@1.0"):
        engine.new_run("spec-to-testcase", {"spec_id": SPEC, "spec_version": "1.0", "scope": "REQ-DSC-002,099"}, BY, new_request=True)
    assert sorted(p.name for p in (store.ROOT / "runs").iterdir()) == before          # 整個操作不寫入

def test_16_unknown_requirement_blocks_dispatch_for_run_created_before_check():
    """建立時還沒有 revision（或本變更前建立）的 run：派發 Designer 時才擋。以外部寫入模擬 scope 與 revision 對不上的既有 run。"""
    run = engine.new_run("spec-to-testcase", {"spec_id": SPEC, "spec_version": "1.0", "scope": "REQ-DSC-002"}, BY, new_request=True)
    data = engine.load_run(run["run_id"]); data["input"]["scope"] = "REQ-DSC-002,099"
    H.raw_save(f"runs/{run['run_id']}/run.yaml", data)
    with pytest.raises(dispatch.DispatchError, match="REQ-DSC-099 不在綁定的"):
        dispatch.dispatch(run["run_id"], "T2")
    assert not dispatch.current_entry(engine._task(engine.load_run(run["run_id"]), "T2"))
    # 防線：g_design 直接呼叫時同樣報出
    msgs = gates.run_scope_issues(["REQ-DSC-002", "REQ-DSC-099"], "REQ-DSC-002,099", {"testcases": []}, {"REQ-DSC-002": {"status": "ACTIVE"}})
    assert len(msgs) == 1 and "REQ-DSC-099 不在綁定的 revision" in msgs[0]

def test_17_risk_reviewer_packet_has_no_scope():
    assert "agent-tc-risk-reviewer" not in dispatch.SCOPE_AGENTS and "agent-test-designer" in dispatch.SCOPE_AGENTS
