"""補 Runtime「拒絕分支」的測試（對應 TEST-AUTOMATION-COVERAGE-AUDIT §1 Runtime 的 high 缺口）。

既有 tests/ 主要證明「正確輸入會過」；本檔專門證明「這幾種錯誤輸入會被擋」：
  A. gates.py 9 條從未被觸發的攔截規則（g_design / g_tval / g_compare）
  B. engine.submit 的 Permission Guard：引用其他 run 的 artifact、TestCaseDraft source 與 mode 不一致
  C. engine.evaluate_gate：task 為 READY 且仍留有 VALID artifact 時，會拿舊 artifact 重新評估並推進
     （BONUSCCY-002 實際踩過：新 submit 因引用狀態失敗，接著 gate 卻用舊 artifact PASS。本測試把這個行為固定成明確契約）
  D. refs.resolve 的 Evidence 完整性偵測：「檔案不存在」與「sha256 欄位被替換」（「檔案內容被改」已由 test_10 覆蓋）

隔離原則：需要特殊 RequirementModel 狀態的案例（A 組）用獨立的 SPEC-GATE-001 直接持久化，且 g_design 不用 run/task 參數，可直接呼叫；
需要 engine 流程的案例（B、C 組）用既有已 ACTIVE 的 SPEC-AUTH-001@1.0 開新 run，只新增 run／artifact，不改共用 requirements。
"""
import pytest
from tests.helpers import raw_save
from tools.qaos import store, engine, gates, refs
from tests import helpers as H

GATE_SPEC, GATE_VER = "SPEC-GATE-001", "1.0"


# ---------- A 組共用：獨立的 RequirementModel ----------

def _req(rid, ac_id, status="ACTIVE", risk="medium", **extra):
    r = {"requirement_id": rid, "version": 1, "spec_id": GATE_SPEC, "spec_version": GATE_VER, "type": "functional",
         "title": rid, "statement": f"{rid} 的規則", "status": status, "risk": risk, "history": [],
         "acceptance_criteria": [{"ac_id": ac_id, "given": "g", "when": "w", "then": "t"}],
         "spec_reference": {"spec_id": GATE_SPEC, "spec_version": GATE_VER, "location": "§1"},
         "ambiguity": None, "rejection_contract": {"defined": True, "description": "已定義"}}
    r.update(extra); return r


RUN = {}   # g_design 讀 run 綁定的 revision（需求 A 第 5 章 §4.1）：以記憶體中的 run 帶入 RMPin

def _persist_gate_model(reqs, tmp):
    """以正式流程匯入 SPEC-GATE-001，再經 save_requirements 產生 revision（不再直接寫 requirements.yaml）。"""
    from tools.qaos import operation, rm, spec_ops
    f = tmp / "gate.md"; f.write_text("# GATE\n\n測試用規格。\n", encoding="utf-8")
    if not store.spec_dir(GATE_SPEC): spec_ops.spec_import(str(f), GATE_SPEC, GATE_VER, "demo", "GATE", by="oscar@example.com", new_request=True)
    pin = operation.run_operation("test_internal", lambda: rm.save_requirements(GATE_SPEC, GATE_VER, reqs, reason="test fixture", by="system", source_artifact_id="ART-RM-01M5GATETEST00000000000000"), new_request=True)
    RUN.clear(); RUN.update({"run_id": "RUN-20260101-999", "requirement_model_revision": pin})


def _gtc(draft_id, req, ac, types, techs, **kw):
    """SPEC-GATE-001 專用的 TC；預設 happy path（functional / requirement_based）。"""
    return H.tc(draft_id, f"{draft_id} 的案例", req, ac, "api", types, techs, ["步驟一"], "預期結果", "§1", risk="medium", prio="medium", spec_id=GATE_SPEC, **kw)


def _arts(tcs, mode="spec", report_override=None):
    tcd = {"artifact_id": "ART-TCD-GATE", "payload": {"mode": mode, "spec_id": GATE_SPEC, "spec_version": GATE_VER, "testcases": tcs}}
    rep = H.design_report("ART-TCD-GATE", tcs); rep["mode"] = mode
    if report_override: rep.update(report_override)
    return {"TestCaseDraft": tcd, "TestDesignReport": {"artifact_id": "ART-TDR-GATE", "payload": rep}}


@pytest.fixture(scope="module")
def gate_model(tmp_path_factory):
    """一份含各種特殊狀態 requirement 的 RequirementModel，只讀不改。"""
    _persist_gate_model(tmp=tmp_path_factory.mktemp("gate"), reqs=[
        _req("REQ-GATE-001", "AC-GATE-001"),
        _req("REQ-GATE-002", "AC-GATE-002", status="RETIRED"),
        _req("REQ-GATE-003", "AC-GATE-003", ambiguity={"level": "critical", "description": "未決"}),
        _req("REQ-GATE-004", "AC-GATE-004", behavior_kind="rejection"),
        _req("REQ-GATE-005", "AC-GATE-005", rejection_contract={"defined": False, "description": "spec 未定義拒絕行為"}),
    ])
    yield
    import shutil; shutil.rmtree(store.ROOT / f"artifacts/requirements/{GATE_SPEC}", ignore_errors=True)   # 只清本測試建立的需求模型


# ---------- A. gates.py 拒絕分支 ----------

def test_50_g_design_rejects_tc_referencing_non_active_requirement(gate_model):
    """L62：TC 引用 RETIRED 的 requirement → 擋。"""
    tcs = [_gtc("TC-DRAFT-01GATE0000000000000000000A", "REQ-GATE-002", "AC-GATE-002", ["negative"], ["negative"])]
    issues = gates.g_design(RUN, None, _arts(tcs))
    assert any("非 ACTIVE" in i and "REQ-GATE-002" in i and "RETIRED" in i for i in issues)


def test_51_g_design_rejects_tc_for_critical_ambiguity_requirement(gate_model):
    """L64：requirement 有 critical ambiguity 且未被 approval 解決 → 不得為它設計 TC。"""
    tcs = [_gtc("TC-DRAFT-01GATE0000000000000000000B", "REQ-GATE-003", "AC-GATE-003", ["negative"], ["negative"])]
    issues = gates.g_design(RUN, None, _arts(tcs))
    assert any("critical ambiguity" in i and "REQ-GATE-003" in i for i in issues)


def test_52_g_design_rejects_change_mode_tc_without_supersedes(gate_model):
    """L73：mode=change 的 TC 既無 supersedes_testcase、source_ref 也不以 new_required 開頭 → 擋。"""
    tcs = [_gtc("TC-DRAFT-01GATE0000000000000000000C", "REQ-GATE-001", "AC-GATE-001", ["negative"], ["negative"], mode="change")]
    issues = gates.g_design(RUN, None, _arts(tcs, mode="change"))
    assert any("mode=change 但無 supersedes_testcase" in i for i in issues)
    # 對照：帶 source_ref=new_required:* 的新 TC 可以不 supersede
    ok = [_gtc("TC-DRAFT-01GATE0000000000000000000D", "REQ-GATE-001", "AC-GATE-001", ["negative"], ["negative"], mode="change", source_ref="new_required:CLR-X")]
    assert not any("supersedes_testcase" in i for i in gates.g_design(RUN, None, _arts(ok, mode="change")))


def test_53_g_design_rejects_rejection_kind_requirement_without_negative_case(gate_model):
    """L103：behavior_kind=rejection 的 requirement 有 TC，但沒有一條 test_types 含 negative → 擋。"""
    tcs = [_gtc("TC-DRAFT-01GATE0000000000000000000E", "REQ-GATE-004", "AC-GATE-004", ["functional"], ["error_guessing"])]
    issues = gates.g_design(RUN, None, _arts(tcs))
    assert any("rejection 類需求" in i and "REQ-GATE-004" in i for i in issues)


def test_54_g_design_rejects_negative_case_written_as_certain_when_rejection_contract_undefined(gate_model):
    """L113：rejection_contract.defined=False 的 requirement，用 negative/error_guessing 寫成確定規則（無 assumptions）→ 擋；
    加上 assumptions（exploratory）後該條不再出現。這條規則正是本專案多次踩過的 exploratory 誤判來源。"""
    certain = [_gtc("TC-DRAFT-01GATE0000000000000000000F", "REQ-GATE-005", "AC-GATE-005", ["negative"], ["negative"])]
    issues = gates.g_design(RUN, None, _arts(certain))
    assert any("rejection_contract 未定義" in i and "必須是 exploratory" in i for i in issues)
    exploratory = [_gtc("TC-DRAFT-01GATE0000000000000000000G", "REQ-GATE-005", "AC-GATE-005", ["negative"], ["negative"],
                        assumptions=[{"text": "拒絕行為待確認", "requirement_id": "REQ-GATE-005", "needs_human_confirmation": True}])]
    assert not any("rejection_contract 未定義" in i for i in gates.g_design(RUN, None, _arts(exploratory)))


def test_55_g_design_rejects_draft_with_no_non_happy_case_at_all(gate_model):
    """L117：整份 Draft 全是 happy path（無 negative/boundary/error_guessing）→ 擋。"""
    tcs = [_gtc("TC-DRAFT-01GATE0000000000000000000H", "REQ-GATE-001", "AC-GATE-001", ["functional"], ["requirement_based"])]
    issues = gates.g_design(RUN, None, _arts(tcs))
    assert any("整份 Draft 沒有任何 negative / boundary / error_guessing 案例" in i for i in issues)


def test_58_g_design_rejects_ac_not_owned_by_tc_requirements(gate_model):
    """AC 歸屬：TC 引用的 AC 必須屬於其 requirement_ids 之一。
    Validator 對抗性 eval v1 的 E6 揭示：舊規則只驗 AC 存在於全域集合，掛錯 requirement 仍 structural PASS，
    只能靠 LLM Validator 兜底——這是能寫成 deterministic 規則的事。"""
    # 掛 REQ-GATE-001 卻引用屬於 REQ-GATE-004 的 AC → 擋，訊息帶實際 owner
    wrong = [_gtc("TC-DRAFT-01GATE0000000000000000000I", "REQ-GATE-001", "AC-GATE-004", ["negative"], ["negative"])]
    issues = gates.g_design(RUN, None, _arts(wrong))
    assert any("AC-GATE-004" in i and "屬於 REQ-GATE-004" in i and "不在本 TC 的 requirement_ids 內" in i for i in issues)
    # 對照 1：正確配對 → 不擋
    ok = [_gtc("TC-DRAFT-01GATE0000000000000000000J", "REQ-GATE-001", "AC-GATE-001", ["negative"], ["negative"])]
    assert not any("不在本 TC 的 requirement_ids 內" in i for i in gates.g_design(RUN, None, _arts(ok)))
    # 對照 2：合法的跨 requirement TC（掛兩個 req、引用各自的 AC）→ 不擋
    multi = [_gtc("TC-DRAFT-01GATE0000000000000000000K", "REQ-GATE-001", "AC-GATE-001", ["negative"], ["negative"],
                  requirement_ids=["REQ-GATE-001", "REQ-GATE-004"], acceptance_criteria_ids=["AC-GATE-001", "AC-GATE-004"])]
    assert not any("不在本 TC 的 requirement_ids 內" in i for i in gates.g_design(RUN, None, _arts(multi)))
    # 對照 3：AC 根本不存在 → 走原本的「不存在」訊息，不誤報歸屬、不 KeyError
    missing = [_gtc("TC-DRAFT-01GATE0000000000000000000L", "REQ-GATE-001", "AC-GATE-009", ["negative"], ["negative"])]
    issues = gates.g_design(RUN, None, _arts(missing))
    assert any("引用不存在的 AC AC-GATE-009" in i for i in issues) and not any("不在本 TC 的 requirement_ids 內" in i for i in issues)


def test_59_resolved_assumption_need_not_flag_human_confirmation(gate_model):
    """L75：assumption 未標 needs_human_confirmation: true 會擋；但已由核准解決（resolved_by_approval）者豁免——
    change 模式沿用現行 ACTIVE 版的已核准假設時，不該被迫翻成「需人工確認」造成與 resolved_by_approval 自相矛盾（CLR-012 修訂 TC-054 踩到）。"""
    def mk(did, assumptions): return _gtc(did, "REQ-GATE-001", "AC-GATE-001", ["negative"], ["negative"], assumptions=assumptions)
    flagged = mk("TC-DRAFT-01GATE59AAAAAAAAAAAAAAAAAA", [{"text": "a", "requirement_id": "REQ-GATE-001", "needs_human_confirmation": False}])
    resolved = mk("TC-DRAFT-01GATE59BBBBBBBBBBBBBBBBBB", [{"text": "a", "requirement_id": "REQ-GATE-001", "needs_human_confirmation": False, "resolved_by_approval": "APR-0007"}])
    explicit = mk("TC-DRAFT-01GATE59CCCCCCCCCCCCCCCCCC", [{"text": "a", "requirement_id": "REQ-GATE-001", "needs_human_confirmation": True}])
    issues = gates.g_design(RUN, None, _arts([flagged, resolved, explicit]))
    hits = [i for i in issues if "needs_human_confirmation" in i]
    assert len(hits) == 1 and "01GATE59AAAA" in hits[0], issues


def test_56_g_tval_rejects_pass_report_that_still_contains_blocker_or_major():
    """L134：Validator 宣稱 PASS，issues 卻含 blocker/major → 自相矛盾，擋。"""
    tcs, ids_ = H.draft_set(prefix="01GATETVAL000000000000000")
    did, _ = H.write_artifact("RUN-GATE-TVAL", "T2", "agent-test-designer", "TestCaseDraft",
                              {"mode": "spec", "spec_id": "SPEC-AUTH-001", "spec_version": "1.0", "testcases": tcs}, [], {"type": "x", "ids": []}, "test-design")
    blocker = {"testcase_id": ids_[0], "issue_type": "spec_mismatch", "severity": "blocker", "violated_requirement": "REQ-AUTH-001",
               "spec_reference": {"spec_id": "SPEC-AUTH-001", "spec_version": "1.0", "location": "§3.1"}, "evidence": "e", "explanation": "x", "recommended_change": "r"}
    rep = H.validation_report(did, "ART-RM-TESTONLY", "PASS", [blocker])
    issues = gates.g_tval(None, None, {"TestValidationReport": {"artifact_id": "ART-TVR-GATE", "payload": rep}})
    assert any("PASS 但含 blocker/major issue" in i for i in issues)
    # 對照：同樣是 PASS 但只有 minor → 不擋
    minor = dict(blocker, severity="minor")
    assert not gates.g_tval(None, None, {"TestValidationReport": {"artifact_id": "ART-TVR-GATE", "payload": H.validation_report(did, "ART-RM-TESTONLY", "PASS", [minor])}})


def test_57_g_compare_rejects_verdicts_missing_required_ids():
    """L190／L192：VersionComparisonReport 的 verdict 與必填 id 不一致 → 擋。"""
    def vcr(comparisons): return {"VersionComparisonReport": {"artifact_id": "ART-VCR-GATE", "payload": {"comparisons": comparisons}}}
    base = {"field_diffs": [{"field": "title", "old": "a", "new": "b"}]}
    # changed 缺 testcase_id / old_version
    issues = gates.g_compare(None, None, vcr([dict(base, verdict="changed", testcase_id=None, old_version=None, new_draft_id="TC-DRAFT-01GATECMPX0000000000000000")]))
    assert any("需要 testcase_id + old_version" in i for i in issues)
    # added 缺 new_draft_id
    issues = gates.g_compare(None, None, vcr([dict(base, verdict="added", testcase_id=None, old_version=None, new_draft_id=None)]))
    assert any("需要 new_draft_id" in i for i in issues)
    # 對照：欄位齊全的 changed → 不擋
    assert not gates.g_compare(None, None, vcr([dict(base, verdict="changed", testcase_id="TC-AUTH-001", old_version=1, new_draft_id="TC-DRAFT-01GATECMPX0000000000000000")]))


# ---------- B、C 組共用：在 SPEC-AUTH-001@1.0 上開新 run ----------

@pytest.fixture(scope="module")
def auth_ready(fixtures):
    """讓本檔可以單獨跑：若 SPEC-AUTH-001@1.0 尚未由 test_spec_to_testcase 準備好，就自己補齊最小前置
    （spec import + 一份 VALID 的 RequirementModel artifact + 持久化 ACTIVE requirements）。整套一起跑時已就緒，直接略過。"""
    from tools.qaos.cli import main as cli
    if store.spec_dir("SPEC-AUTH-001") is None:
        cli(["spec", "import", str(fixtures / "SPEC-AUTH-001-v1.0.md"), "--spec-id", "SPEC-AUTH-001", "--version", "1.0",
             "--product", "demo", "--area", "AUTH", "--by", "bootstrap"])
    if not store.exists(store.requirements_path("SPEC-AUTH-001", "1.0")):
        rm = H.requirement_model()
        for r in rm["requirements"]: r["status"] = "ACTIVE"
        rmid, p = H.write_artifact("RUN-GATE-BOOT", "T1", "agent-spec-analyst", "RequirementModel", rm,
                                   [{"entity_type": "SpecVersion", "id": "SPEC-AUTH-001", "version": "1.0"}], {"type": "SpecVersion", "ids": ["SPEC-AUTH-001@1.0"]}, "requirements")
        raw_save(p, dict(store.load(p), status="VALID"))
        raw_save(store.requirements_path("SPEC-AUTH-001", "1.0"),
                   {"spec_id": "SPEC-AUTH-001", "spec_version": "1.0", "source_artifact_id": rmid, "persisted_at": store.now(), "requirements": rm["requirements"]})


def _auth_rm_id():
    return store.load(store.requirements_path("SPEC-AUTH-001", "1.0"))["source_artifact_id"]


def _new_run_at_t2():
    """T1 因 RequirementModel 已存在而 skip，run 直接停在 T2 READY。"""
    run = engine.new_run("spec-to-testcase", {"spec_id": "SPEC-AUTH-001", "spec_version": "1.0"}, "oscar@example.com", new_request=True)
    assert run["current_task_id"] == "T2"
    return run["run_id"]


def _submit_draft(rid, prefix, **draft_kw):
    tcs, ids_ = H.draft_set(prefix=prefix)
    refs_ = [{"entity_type": "Requirement", "id": r} for r in ["REQ-AUTH-001", "REQ-AUTH-002", "REQ-AUTH-003", "REQ-AUTH-004"]] + [{"entity_type": "Artifact", "id": _auth_rm_id()}]
    payload = {"mode": "spec", "spec_id": "SPEC-AUTH-001", "spec_version": "1.0", "testcases": tcs}; payload.update(draft_kw)
    did, p = H.write_artifact(rid, "T2", "agent-test-designer", "TestCaseDraft", payload, refs_, {"type": "RequirementModel", "ids": [_auth_rm_id()]}, "test-design")
    return did, p, tcs, ids_


def _submit_report(rid, did, tcs, extra_refs=()):
    rep = H.design_report(did, tcs)
    refs_ = [{"entity_type": "Artifact", "id": did}] + list(extra_refs)
    trid, p = H.write_artifact(rid, "T2", "agent-test-designer", "TestDesignReport", rep, refs_, {"type": "TestCaseDraft", "ids": [did]}, "test-design")
    return trid, p


# ---------- B. Permission Guard ----------

def test_60_submit_rejects_artifact_referencing_another_runs_artifact(auth_ready):
    """engine.submit L144：TestDesignReport 引用了「另一個 run」的 VALID TestCaseDraft → 越 run 引用，擋。
    （被引用者必須先是 VALID，否則會在更前面的 refs.resolve 就被擋、走不到這條規則）"""
    rid_a = _new_run_at_t2()
    did_a, p_a, tcs_a, _ = _submit_draft(rid_a, "01GATEPGA0000000000000000")
    assert engine.submit(rid_a, "T2", str(p_a))[0] and store.load(p_a)["status"] == "VALID"
    rid_b = _new_run_at_t2()
    did_b, p_b, tcs_b, _ = _submit_draft(rid_b, "01GATEPGB0000000000000000")
    assert engine.submit(rid_b, "T2", str(p_b))[0]
    # run B 的 report 偷引用 run A 的 draft
    _, p_rep = _submit_report(rid_b, did_b, tcs_b, extra_refs=[{"entity_type": "Artifact", "id": did_a}])
    ok, problems = engine.submit(rid_b, "T2", str(p_rep))
    assert not ok and any("其他 run 的 artifact" in x and did_a in x for x in problems)
    assert store.load(p_rep)["status"] == "DRAFT"   # 驗證失敗不改 artifact 檔；INVALID 記在 gate_results
    t2 = next(t for t in engine.load_run(rid_b)["tasks"] if t["task_id"] == "T2"); assert t2["gate_results"][-1]["result"] == "FAIL"


def test_61_submit_rejects_testcase_draft_whose_source_mismatches_mode(auth_ready):
    """engine.submit L149：Draft 宣告 mode=spec，但某條 TC 的 source 是 change_workflow → 不一致，擋。"""
    rid = _new_run_at_t2()
    did, p, tcs, ids_ = _submit_draft(rid, "01GATEPGC0000000000000000")
    tcs[1]["source"] = "change_workflow"
    raw_save(p, dict(store.load(p), payload=dict(store.load(p)["payload"], testcases=tcs)))
    ok, problems = engine.submit(rid, "T2", str(p))
    assert not ok and any("source 與 mode 不一致" in x and ids_[1] in x for x in problems)


# ---------- C. READY + 既有 VALID artifact 重新 gate ----------

def test_62_gate_on_ready_task_reuses_existing_valid_artifacts_and_advances(auth_ready):
    """engine.evaluate_gate L202：T3 FAIL 把 T2 route back 成 READY，但 T2 的 output_artifact_ids 仍留著舊的 VALID artifact；
    此時「不重新 submit、直接 gate T2」會拿舊 artifact 重新評估並推進到 T3。
    這正是 BONUSCCY-002 踩過的坑（新 submit 失敗卻以為修正已生效）。本測試把它固定成契約，並斷言推進用的確實是舊 artifact。"""
    rid = _new_run_at_t2()
    did, p, tcs, ids_ = _submit_draft(rid, "01GATERDY0000000000000000")
    assert engine.submit(rid, "T2", str(p))[0]
    trid, p_rep = _submit_report(rid, did, tcs)
    assert engine.submit(rid, "T2", str(p_rep))[0]
    assert engine.evaluate_gate(rid, "T2")["result"] == "PASS" and engine.load_run(rid)["current_task_id"] == "T3"
    # T3 FAIL → route back
    issue = {"testcase_id": ids_[2], "issue_type": "spec_mismatch", "severity": "major", "violated_requirement": "REQ-AUTH-002",
             "spec_reference": {"spec_id": "SPEC-AUTH-001", "spec_version": "1.0", "location": "§3.1 R2"}, "evidence": "e", "explanation": "x", "recommended_change": "r"}
    vr, pv = H.write_artifact(rid, "T3", "agent-test-validator", "TestValidationReport", H.validation_report(did, _auth_rm_id(), "FAIL", [issue]),
                              [{"entity_type": "Artifact", "id": did}, {"entity_type": "Artifact", "id": _auth_rm_id()}], {"type": "TestCaseDraft", "ids": [did]}, "validation")
    assert engine.submit(rid, "T3", str(pv))[0] and engine.evaluate_gate(rid, "T3")["result"] == "FAIL"
    run = engine.load_run(rid); t2 = run["tasks"][1]
    assert run["current_task_id"] == "T2" and t2["status"] == "READY" and t2["iteration"] == 1
    assert set(t2["output_artifact_ids"]) >= {did, trid}  # route back 沒有清掉舊 artifact
    # 不重新 submit，直接 gate → 用舊 artifact 重評並推進
    r = engine.evaluate_gate(rid, "T2")
    assert r["result"] == "PASS"
    run = engine.load_run(rid); t2 = run["tasks"][1]
    assert t2["status"] == "DONE" and run["current_task_id"] == "T3"
    assert set(t2["output_artifact_ids"]) >= {did, trid} and store.load(store.find_artifact(did))["status"] == "VALID"


# ---------- D. Evidence 完整性偵測 ----------

def _write_evidence(eid, uri, sha256, inline=None):
    ev = {"evidence_id": eid, "type": "api_response", "captured_at": store.now(), "captured_by": "test", "description": "d", "uri": uri, "sha256": sha256}
    if inline is not None: ev["inline_content"] = inline
    raw_save(f"evidence/test/{eid}.yaml", ev)


def test_70_evidence_resolve_rejects_when_file_missing_and_no_inline():
    """refs.py L51-52：uri 指向不存在的檔案、又沒有 inline_content → 無法驗證，擋。"""
    _write_evidence("EVD-GATE-MISSING", "evidence/test/EVD-GATE-MISSING.txt", "0" * 64)
    msg = refs.resolve({"entity_type": "Evidence", "id": "EVD-GATE-MISSING"})
    assert msg and "不存在" in msg


def test_71_evidence_resolve_rejects_when_sha256_field_replaced():
    """refs.py L55 else 分支：檔案與 inline_content 一致（內容沒被動），但記錄上的 sha256 欄位被換掉 → 「可能被替換」，擋。
    （test_10 測的是「內容被改、inline 對不上」；這裡測的是 metadata 被動、內容沒動的相反情境）"""
    content = '{"status":200}'
    path = store.ROOT / "evidence" / "test" / "EVD-GATE-SWAP.txt"; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(content, encoding="utf-8")
    _write_evidence("EVD-GATE-SWAP", "evidence/test/EVD-GATE-SWAP.txt", "f" * 64, inline=content)
    msg = refs.resolve({"entity_type": "Evidence", "id": "EVD-GATE-SWAP"})
    assert msg and "sha256 不符" in msg and "替換" in msg
    # 對照：sha256 正確 → 可引用
    _write_evidence("EVD-GATE-SWAP", "evidence/test/EVD-GATE-SWAP.txt", store.sha256_text(content), inline=content)
    assert refs.resolve({"entity_type": "Evidence", "id": "EVD-GATE-SWAP"}) is None


def test_72_evidence_resolve_falls_back_to_inline_when_file_missing():
    """refs.py L49-50：實體檔遺失但記錄有 inline_content → 退而用 inline 的 sha256 比對；
    inline 與記錄的 sha256 一致 → 仍可引用；不一致 → 「可能被替換」。這是 Evidence 四種組合中最後一條。"""
    content = '{"status":500}'
    _write_evidence("EVD-GATE-INLINE", "evidence/test/EVD-GATE-INLINE-missing.txt", store.sha256_text(content), inline=content)
    assert refs.resolve({"entity_type": "Evidence", "id": "EVD-GATE-INLINE"}) is None
    _write_evidence("EVD-GATE-INLINE", "evidence/test/EVD-GATE-INLINE-missing.txt", "e" * 64, inline=content)
    msg = refs.resolve({"entity_type": "Evidence", "id": "EVD-GATE-INLINE"})
    assert msg and "sha256 不符" in msg
