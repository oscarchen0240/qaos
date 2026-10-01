"""ADR-009：模型分配與高風險 TC 抽查（tc-risk-reviewer）。
- 每個 agent 契約都有 model，且派發用的 .claude/agents/qaos-<name>.md 與之一致
- 高風險 area 的 run 在 Validator 之後插入 <after>RR（G-RISK），非高風險 area 不插
- G-RISK 只擋結構：審錯 draft、五面向不齊、無 spec 依據卻未標需澄清
- 抽查結果附在 ACTIVATE 核准單；整批 reject 後抽查 task 重設、退回的是 Designer 而非 Reviewer"""
import pathlib, yaml, pytest
from tools.qaos import store, engine
from tests import helpers as H
from tests.test_wf_y_negative_coverage import _tcs, _submit_design

REPO = pathlib.Path(__file__).resolve().parents[1]
DIMS = ["boundary", "exception_flow", "concurrency", "duplicate_submission", "permission"]

def test_70_agent_models_match_dispatch_wrappers():
    for c in sorted((REPO / "agents").glob("*.yaml")):
        a = yaml.safe_load(open(c, encoding="utf-8")); short = a["id"].removeprefix("agent-")
        assert a.get("model") in ("opus", "sonnet"), f"{c.name} 缺 model"
        if short == "supervisor": continue   # 主 session 擔任，無 sub agent 定義檔
        md = REPO / ".claude" / "agents" / f"qaos-{short}.md"
        assert md.exists(), f"缺 {md.name}"
        fm = yaml.safe_load(md.read_text(encoding="utf-8").split("---")[1])
        assert fm["model"] == a["model"], f"{md.name} model={fm['model']} ≠ {c.name} model={a['model']}"
    rr = yaml.safe_load(open(REPO / "agents" / "tc-risk-reviewer.yaml", encoding="utf-8"))
    assert rr["model"] == "opus" and set(rr["applies_to_areas"]) >= {"CASHFLOW", "CASHOUT", "TXLOG", "DAILYREPORT"}

def test_71_non_high_risk_area_has_no_risk_task():
    run = engine.new_run("spec-to-testcase", {"spec_id": "SPEC-NEG-001", "spec_version": "1.0"}, "oscar@example.com")
    assert [t["task_id"] for t in run["tasks"]] == ["T1", "T2", "T3", "T4", "T5"]
    engine.cancel(run["run_id"], "oscar@example.com")

def test_72_analysis_review_task_id_passes_schema():
    """T2R 過去不符 TaskId ^T[0-9]+$，analysis_review=required 的 run 根本存不進 run.yaml（回歸）。"""
    run = engine.new_run("spec-to-testcase", {"spec_id": "SPEC-NEG-001", "spec_version": "1.0", "analysis_review": "required"}, "oscar@example.com")
    assert "T2R" in [t["task_id"] for t in run["tasks"]]
    engine.cancel(run["run_id"], "oscar@example.com")

def _review(rid, did, tvr, draft_ids, dims=None, findings=None, task_id="T3RR", agent="agent-tc-risk-reviewer"):
    payload = {"reviewed": {"testcase_draft_artifact_id": did, "validation_report_artifact_id": tvr, "functional_area": "NEG",
                            "spec_id": "SPEC-NEG-001", "spec_version": "1.0", "testcase_draft_ids": draft_ids},
               "dimension_results": [{"dimension": d, "status": "gaps_found" if any(f["dimension"] == d for f in (findings or [])) else "covered",
                                      "rationale": f"{d} 已逐條檢視本次 draft"} for d in (dims or DIMS)],
               "findings": findings or [], "summary": "抽查完成，列出補充建議"}
    _, p = H.write_artifact(rid, task_id, agent, "TCRiskReview", payload, [{"entity_type": "Artifact", "id": did}, {"entity_type": "Artifact", "id": tvr}],
                            {"type": "TestCaseDraft", "ids": [did]}, "risk-review")
    return p

def _finding(**kw):
    f = {"finding_id": "RF-01", "dimension": "concurrency", "severity": "high", "related_testcase_ids": [], "related_requirement_ids": ["REQ-NEG-003"],
         "gap": "同帳號兩個裝置同時輸入錯誤密碼時，失敗次數是否會漏算", "suggested_scenario": "兩個 session 同時送出第 5 次錯誤密碼，確認只觸發一次鎖定且計數正確",
         "spec_basis": None, "needs_clarification": True}
    f.update(kw); return f

def test_73_high_risk_area_inserts_risk_task_and_attaches_to_approval(monkeypatch):
    rr = engine.agents()["agent-tc-risk-reviewer"]
    monkeypatch.setitem(rr, "applies_to_areas", rr["applies_to_areas"] + ["NEG"])   # 測試用：把 NEG 當高風險 area
    run = engine.new_run("spec-to-testcase", {"spec_id": "SPEC-NEG-001", "spec_version": "1.0"}, "oscar@example.com"); rid = run["run_id"]
    assert [t["task_id"] for t in run["tasks"]] == ["T1", "T2", "T3", "T3RR", "T4", "T5"]
    rm_aid = store.load(store.requirements_path("SPEC-NEG-001", "1.0"))["source_artifact_id"]
    tcs, draft_ids = _tcs(prefix="01R0ZZZZZZZZZZZZZZZZZZZZZ")
    did, r = _submit_design(rid, tcs); assert r["result"] == "PASS"
    _, p = H.write_artifact(rid, "T3", "agent-test-validator", "TestValidationReport", H.validation_report(did, rm_aid, "PASS"), [{"entity_type": "Artifact", "id": did}], {"type": "TestCaseDraft", "ids": [did]}, "validation")
    assert engine.submit(rid, "T3", str(p))[0] and engine.evaluate_gate(rid, "T3")["result"] == "PASS"
    run = engine.load_run(rid); tvr = p.stem
    assert run["status"] == "RUNNING" and run["current_task_id"] == "T3RR"   # 抽查完成前不會建 ACTIVATE 核准單

    # G-RISK 結構檢查：面向不齊／無 spec 依據未標需澄清／漏審 draft
    bad = _review(rid, did, tvr, draft_ids[:-1], dims=DIMS[:4] + ["boundary"], findings=[_finding(needs_clarification=False)])
    assert engine.submit(rid, "T3RR", str(bad))[0]
    g = engine.evaluate_gate(rid, "T3RR"); msgs = " ".join(g["issues"])
    assert g["result"] == "FAIL" and "五個面向各一" in msgs and "未標 needs_clarification" in msgs and "testcase_draft_ids 必須恰為" in msgs
    # 正確的抽查 → PASS → ACTIVATE 核准單帶上抽查結果
    good = _review(rid, did, tvr, draft_ids, findings=[_finding(related_testcase_ids=[draft_ids[3]])])
    assert engine.submit(rid, "T3RR", str(good))[0] and engine.evaluate_gate(rid, "T3RR")["result"] == "PASS"
    run = engine.load_run(rid); assert run["status"] == "WAITING_HUMAN"
    apr = store.load(f"approvals/{run['waiting_on_approval_id']}.yaml")
    assert apr["type"] == "ACTIVATE_TESTCASE" and tvr in apr["artifact_ids"] and good.stem in apr["artifact_ids"]
    assert "高風險抽查" in apr["summary"] and "需澄清 1" in apr["summary"] and "[RF-01/high/concurrency/需澄清]" in apr["diff_summary"]

    # 整批 reject → 回到 Designer（不是 Reviewer），T3／T3RR 重設待重跑
    engine.approve(apr["approval_id"], "reject", "oscar@example.com", rationale="依抽查建議補情境")
    run = engine.load_run(rid); st = {t["task_id"]: t["status"] for t in run["tasks"]}
    assert run["current_task_id"] == "T2" and st["T2"] == "READY" and st["T3"] == "PENDING" and st["T3RR"] == "PENDING"
    engine.cancel(rid, "oscar@example.com")

def test_74_only_risk_reviewer_may_produce_risk_review(monkeypatch):
    rr = engine.agents()["agent-tc-risk-reviewer"]
    monkeypatch.setitem(rr, "applies_to_areas", rr["applies_to_areas"] + ["NEG"])
    run = engine.new_run("spec-to-testcase", {"spec_id": "SPEC-NEG-001", "spec_version": "1.0"}, "oscar@example.com"); rid = run["run_id"]
    rm_aid = store.load(store.requirements_path("SPEC-NEG-001", "1.0"))["source_artifact_id"]
    tcs, draft_ids = _tcs(prefix="01R1ZZZZZZZZZZZZZZZZZZZZZ")
    did, _ = _submit_design(rid, tcs)
    _, p = H.write_artifact(rid, "T3", "agent-test-validator", "TestValidationReport", H.validation_report(did, rm_aid, "PASS"), [{"entity_type": "Artifact", "id": did}], {"type": "TestCaseDraft", "ids": [did]}, "validation")
    assert engine.submit(rid, "T3", str(p))[0] and engine.evaluate_gate(rid, "T3")["result"] == "PASS"
    # Validator 冒充 Reviewer 提交 → 越權 → run FAILED
    forged = _review(rid, did, p.stem, draft_ids, agent="agent-test-validator")
    ok, problems = engine.submit(rid, "T3RR", str(forged))
    assert not ok and any("越權" in x for x in problems) and engine.load_run(rid)["status"] == "FAILED"

def _run_to_risk_task(prefix):
    run = engine.new_run("spec-to-testcase", {"spec_id": "SPEC-NEG-001", "spec_version": "1.0"}, "oscar@example.com"); rid = run["run_id"]
    rm_aid = store.load(store.requirements_path("SPEC-NEG-001", "1.0"))["source_artifact_id"]
    tcs, draft_ids = _tcs(prefix=prefix)
    did, _ = _submit_design(rid, tcs)
    _, p = H.write_artifact(rid, "T3", "agent-test-validator", "TestValidationReport", H.validation_report(did, rm_aid, "PASS"), [{"entity_type": "Artifact", "id": did}], {"type": "TestCaseDraft", "ids": [did]}, "validation")
    assert engine.submit(rid, "T3", str(p))[0] and engine.evaluate_gate(rid, "T3")["result"] == "PASS"
    return rid, did, p.stem, draft_ids

def test_75_risk_gate_binds_version_rejects_blank_basis_and_checks_active_area(monkeypatch):
    """MR !1 review：版本須與 draft／run 一致；空白 spec_basis 不算依據；引用 ACTIVE TC 要看 ACTIVE 版本本身的 area。"""
    rr = engine.agents()["agent-tc-risk-reviewer"]
    monkeypatch.setitem(rr, "applies_to_areas", rr["applies_to_areas"] + ["NEG"])
    rid, did, tvr, draft_ids = _run_to_risk_task("01R2ZZZZZZZZZZZZZZZZZZZZZ")
    # 空白 spec_basis → schema INVALID（不進 gate）
    blank = _review(rid, did, tvr, draft_ids, findings=[_finding(spec_basis={"location": " ", "quote": " "}, needs_clarification=False)])
    ok, problems = engine.submit(rid, "T3RR", str(blank)); assert not ok
    # 版本與 draft／run 不符
    p = _review(rid, did, tvr, draft_ids); d = store.load(p); d["payload"]["reviewed"]["spec_version"] = "9.9"; store.save(p, d)
    assert engine.submit(rid, "T3RR", str(p))[0]
    msgs = " ".join(engine.evaluate_gate(rid, "T3RR")["issues"])
    assert "Validator 審過的 draft SPEC-NEG-001@1.0" in msgs and "目標版本 1.0" in msgs
    # ID 前綴是 TC-NEG-，但 ACTIVE 版本實際是 AUTH 的 TC → 不算同 area
    src = next(q for q in sorted((store.ROOT / "testcases" / "registry").glob("TC-AUTH-*.yaml")) if store.load(q)["status"] == "ACTIVE")
    ptr = store.load(src); ver = ptr["active_version"]; v = store.load(store.tc_version_path(src.stem, ver))
    store.save(store.tc_version_path("TC-NEG-900", ver), dict(v, testcase_id="TC-NEG-900")); store.save(store.tc_pointer_path("TC-NEG-900"), dict(ptr, testcase_id="TC-NEG-900"))
    try:
        p = _review(rid, did, tvr, draft_ids, findings=[_finding(related_testcase_ids=["TC-NEG-900"])])
        assert engine.submit(rid, "T3RR", str(p))[0]
        g = engine.evaluate_gate(rid, "T3RR")
        assert g["result"] == "FAIL" and any("TC-NEG-900 既不是本次 draft，也不是同 area 的 ACTIVE TC" in x for x in g["issues"])
    finally:
        (store.ROOT / store.tc_pointer_path("TC-NEG-900")).unlink(); (store.ROOT / store.tc_version_path("TC-NEG-900", ver)).unlink()
    engine.cancel(rid, "oscar@example.com")

def test_76_change_impact_reject_returns_to_designer_and_resets_risk_task(monkeypatch):
    """MR !1 review：spec-change-impact 的核准前是 T4 CIA compare；整批 reject 必須退回 T2 Designer，T3／T3RR／T4 一起重設。"""
    rr = engine.agents()["agent-tc-risk-reviewer"]
    monkeypatch.setitem(rr, "applies_to_areas", rr["applies_to_areas"] + ["AUTH"])
    run = engine.new_run("spec-change-impact", {"spec_id": "SPEC-AUTH-001", "from_version": "1.0", "to_version": "1.1"}, "oscar@example.com"); rid = run["run_id"]
    assert [t["task_id"] for t in run["tasks"]] == ["T0", "T1", "T2", "T3", "T3RR", "T4", "T5", "T6"]
    for t in run["tasks"]:
        if t["task_id"] in ("T0", "T1", "T2", "T3", "T3RR", "T4"): t["status"] = "DONE"
    apr_task = next(t for t in run["tasks"] if t["task_id"] == "T5"); apr_task["status"] = "RUNNING"
    engine._finish_approval_task(run, apr_task, ok=False, back_to_generator=True)
    run = engine.load_run(rid); st = {t["task_id"]: t["status"] for t in run["tasks"]}
    assert run["current_task_id"] == "T2" and st["T2"] == "READY" and st["T1"] == "DONE"
    assert st["T3"] == st["T3RR"] == st["T4"] == st["T5"] == "PENDING"
    engine.cancel(rid, "oscar@example.com")

def test_77_manual_run_area_comes_from_record_and_unknown_area_is_rejected(monkeypatch):
    """MR !1 review：manual-test-to-regression 可不填 spec_id；area 改看 manual record，判定不了就拒絕建 run，不默默跳過抽查。"""
    from tools.qaos import tc_ops
    rr = engine.agents()["agent-tc-risk-reviewer"]
    monkeypatch.setitem(rr, "applies_to_areas", rr["applies_to_areas"] + ["NEG"])
    rec = tc_ops.manual_new("提款連點測試", "demo", "NEG", ["連點送出"], "產生兩筆", "fail", "oscar@example.com")
    run = engine.new_run("manual-test-to-regression", {"manual_record_id": rec}, "oscar@example.com")
    assert "T2RR" in [t["task_id"] for t in run["tasks"]]
    engine.cancel(run["run_id"], "oscar@example.com")
    with pytest.raises(engine.EngineError, match="無法判定本 run 的 functional area"):
        engine.new_run("manual-test-to-regression", {"manual_record_id": "MAN-19990101-001"}, "oscar@example.com")

def test_78_risk_reviewer_input_schema_binds_validation_report():
    """MR !1 review 第二輪：Reviewer 原本沿用 test-validator-input（additionalProperties false），傳不進必須綁定的 TVR ID。"""
    from tools.qaos import schema
    ok = {"run_id": "RUN-20261001-001", "task_id": "T3RR", "iteration": 0, "functional_area": "CASHOUT", "spec_id": "SPEC-CASHOUT-901", "spec_version": "1.0",
          "requirement_model_artifact_id": "ART-RM-01M3TWMMFJAVVA15XRQY8RK4X5", "testcase_draft_artifact_id": "ART-TCD-01M3TWRCPN91JEQ9C2MGK4AZB2",
          "validation_report_artifact_id": "ART-TVR-01M3TXFPR4DAFK585X0WD14DXE", "existing_active_testcase_ids": []}
    assert schema.errors(ok, "artifact/tc-risk-reviewer-input.schema.json") == []
    missing = {k: v for k, v in ok.items() if k != "validation_report_artifact_id"}
    assert any("validation_report_artifact_id" in e for e in schema.errors(missing, "artifact/tc-risk-reviewer-input.schema.json"))
    leaked = dict(ok, test_design_report_artifact_id="ART-TDR-01M3TWRCRS3B92JKQ4WR3JTWX2")   # 不給 Designer 的報告
    assert schema.errors(leaked, "artifact/tc-risk-reviewer-input.schema.json")
    # 每份 agent 契約指到的 input／output schema 檔都要存在
    for c in sorted((REPO / "agents").glob("*.yaml")):
        a = yaml.safe_load(open(c, encoding="utf-8"))
        for key in ("input_schema", "output_schema"):
            for s in ([a[key]] if isinstance(a[key], str) else a[key]):
                assert (REPO / s).exists(), f"{c.name} {key} 指向不存在的 {s}"
