"""關卡完整性（docs/phase3-shadow-test/2026-10-08-redpacket-shadow-test.md 待辦 #1、#5、#8、#9、#16）：
- #1  G-SPEC：REQ ID 必須由計數器配發（不得自行編號、不得用同 area 其他 spec 的 ID）。
- #9  G-SPEC 自動開 CLR 後，同一個操作重建 clarifications/index.md。
- #16 submit：envelope created_at 不能是未來時間，也不能早於本輪派發（agent 自填的時間）。
- #5  派給 Validator 的派發包附剝除 design_rationale 的 Draft 副本；G-TVAL 核對報告審的是那一份、副本未被改動。
- #8  G-TVAL 的派發包範圍檢查納入 expected_result_spec_reference。"""
import copy
from tools.qaos import store, engine, gates, dispatch, clarification as clr
from tools.qaos.cli import main as cli
from tests import helpers as H

AREA, SPEC, OTHER = "GATEINT", "SPEC-GATEINT-001", "SPEC-GATEINT-002"
S = {}

def _swap(obj):
    """helpers 的 AUTH 範本換成本檔的 area／spec（REQ／AC ID、spec_id、functional_area）。"""
    if isinstance(obj, dict): return {k: _swap(v) for k, v in obj.items()}
    if isinstance(obj, list): return [_swap(v) for v in obj]
    if isinstance(obj, str): return obj.replace("SPEC-AUTH-001", SPEC).replace("AUTH", AREA)
    return obj

def _rm():
    rm = _swap(copy.deepcopy(H.requirement_model()))
    rm["requirements"][3]["rejection_contract"] = {"defined": False, "description": "Spec 未寫登入失敗時的回應"}   # 舊格式需求 → G-SPEC 自動開 CLR
    return rm

def _tcs(prefix):
    tcs, ids_ = H.draft_set(prefix=prefix); tcs = _swap(tcs)
    for t in tcs: t["design_rationale"] = f"{t['draft_id']} 的設計推理（Validator 不得看到）"
    return tcs, ids_

def _counter():
    from tools.qaos import ids
    return ids._load()["counters"].get(f"REQ-{AREA}", 0)

def test_01_setup(fixtures):
    for sid in (SPEC, OTHER):
        cli(["spec", "import", str(fixtures / "SPEC-AUTH-001-v1.0.md"), "--spec-id", sid, "--version", "1.0", "--product", "demo", "--area", AREA, "--by", "oscar@example.com"])
    run = engine.new_run("spec-to-testcase", {"spec_id": SPEC, "spec_version": "1.0"}, "oscar@example.com", new_request=True); S["run"] = run["run_id"]
    assert _counter() == 0

def test_02_g_spec_rejects_req_ids_not_from_counter_then_passes_and_rebuilds_clr_index():
    rid = S["run"]; rm = _rm(); refs_ = [{"entity_type": "SpecVersion", "id": SPEC, "version": "1.0"}]
    h = store.load(store.spec_dir(SPEC) / "spec.yaml")["versions"][0]["content_hash"]
    sa = {"spec_id": SPEC, "spec_version": "1.0", "content_hash": h, "summary": "x", "scope": {"in_scope": [], "out_of_scope": []},
          "requirement_ids": [r["requirement_id"] for r in rm["requirements"]], "ambiguities": [], "constraints": [], "edge_case_candidates": [], "open_questions": []}
    _, p1 = H.write_artifact(rid, "T1", "agent-spec-analyst", "SpecAnalysis", sa, refs_, {"type": "SpecVersion", "ids": []}, "spec-analysis")
    _, p2 = H.write_artifact(rid, "T1", "agent-spec-analyst", "RequirementModel", rm, refs_, {"type": "SpecVersion", "ids": []}, "requirements", alloc_req=False)
    assert engine.submit(rid, "T1", str(p1))[0] and engine.submit(rid, "T1", str(p2))[0]
    r = engine.evaluate_gate(rid, "T1")
    assert r["result"] == "FAIL" and sum("未經計數器配發" in i for i in r["issues"]) == 4, r["issues"]   # Spec Analyst 自行編號（計數器仍為 0）
    assert not [c for c in clr.list_(open_only=False) if c["spec_id"] == SPEC]                             # FAIL 不開單
    # 以計數器配發後重送 → PASS；自動開的 CLR 同時出現在 clarifications/index.md
    S["rm"], p3 = H.write_artifact(rid, "T1", "agent-spec-analyst", "RequirementModel", _rm(), refs_, {"type": "SpecVersion", "ids": []}, "requirements")
    assert _counter() == 4 and engine.submit(rid, "T1", str(p3))[0]
    r = engine.evaluate_gate(rid, "T1"); assert r["result"] == "PASS", r["issues"]
    made = [c for c in clr.list_(open_only=False) if c["spec_id"] == SPEC]
    assert [c["requirement_id"] for c in made] == [f"REQ-{AREA}-004"]
    assert f"[{made[0]['clarification_id']}]" in store.read_text("clarifications/index.md")

def test_03_req_id_rules_reuse_owner_and_format():
    ok = gates.requirement_id_issues(SPEC, AREA, [f"REQ-{AREA}-001"])                 # 同 spec 已持久化 → 可沿用
    other = gates.requirement_id_issues(OTHER, AREA, [f"REQ-{AREA}-001"])             # 同 area 其他 spec 的需求 → 不能用
    fmt = gates.requirement_id_issues(OTHER, AREA, ["REQ-AUTH-001", f"REQ-{AREA}-ABC"])
    beyond = gates.requirement_id_issues(OTHER, AREA, [f"REQ-{AREA}-{_counter() + 1:03d}"])
    assert ok == [] and len(other) == 1 and f"已是 {SPEC} 的需求" in other[0]
    assert len(fmt) == 2 and all("格式" in m for m in fmt) and len(beyond) == 1 and "未經計數器配發" in beyond[0]

def _draft(rid, tcs, iteration=0, created_at=None):
    refs_ = [{"entity_type": "Requirement", "id": r} for r in sorted({r for t in tcs for r in t["requirement_ids"]})]
    return H.write_artifact(rid, "T2", "agent-test-designer", "TestCaseDraft", {"mode": "spec", "spec_id": SPEC, "spec_version": "1.0", "testcases": tcs},
                            refs_, {"type": "RequirementModel", "ids": [S["rm"]]}, "test-design", iteration=iteration, created_at=created_at)

def test_04_submit_rejects_future_and_backdated_created_at():
    rid = S["run"]; tcs, _ = _tcs("01GZZZZZZZZZZZZZZZZZZZZZZ")
    _, pf = _draft(rid, tcs, created_at="2099-01-01T00:00:00Z")
    ok, problems = engine.submit(rid, "T2", str(pf)); assert not ok and any("不能是未來時間" in x for x in problems), problems
    _, pb = _draft(rid, tcs, created_at="2000-01-01T00:00:00Z")
    ok, problems = engine.submit(rid, "T2", str(pb)); assert not ok and any("早於T2 iteration 0 的派發時間" in x for x in problems), problems
    t2 = engine.load_run(rid)["tasks"][1]; assert t2["status"] == "READY" and not t2["output_artifact_ids"]

def _design(rid, tcs, iteration=0):
    did, pd = _draft(rid, tcs, iteration)
    assert engine.submit(rid, "T2", str(pd))[0]
    _, pr = H.write_artifact(rid, "T2", "agent-test-designer", "TestDesignReport", H.design_report(did, tcs), [{"entity_type": "Artifact", "id": did}],
                             {"type": "TestCaseDraft", "ids": [did]}, "test-design", iteration=iteration)
    assert engine.submit(rid, "T2", str(pr))[0]
    r = engine.evaluate_gate(rid, "T2"); assert r["result"] == "PASS", r["issues"]
    return did

def _report(rid, did, result, issues=None):
    rep = _swap(H.validation_report(did, S["rm"], result, issues))
    return H.write_artifact(rid, "T3", "agent-test-validator", "TestValidationReport", rep, [{"entity_type": "Artifact", "id": did}], {"type": "TestCaseDraft", "ids": [did]}, "validation")

def test_05_validator_packet_strips_rationale_and_g_tval_checks_expected_result_reference_scope():
    rid = S["run"]; tcs, ids_ = _tcs("01HZZZZZZZZZZZZZZZZZZZZZZ")
    tcs[4]["expected_result_spec_reference"]["spec_id"] = OTHER                       # 依據寫成派發包範圍外的 spec（沒有 hash，只有 spec_id＋version）
    did = _design(rid, tcs); S["bad_tc"] = ids_[4]; S["draft"] = did
    _, p = _report(rid, did, "PASS")
    t3 = engine._task(engine.load_run(rid), "T3"); pk = dispatch.current_packet(engine.load_run(rid), t3)
    assert [x["artifact_id"] for x in pk["review_drafts"]] == [did] and pk["review_drafts"][0]["stripped_fields"] == ["design_rationale"]
    copy_ = dispatch.load_review_draft(pk["review_drafts"][0])
    assert all("design_rationale" not in t for t in copy_["payload"]["testcases"])
    assert all(t["design_rationale"] for t in store.load(store.find_artifact(did))["payload"]["testcases"])   # 原稿保留，只有副本剝除
    assert [{k: v for k, v in t.items() if k != "design_rationale"} for t in store.load(store.find_artifact(did))["payload"]["testcases"]] == copy_["payload"]["testcases"]
    assert engine.submit(rid, "T3", str(p))[0]
    r = engine.evaluate_gate(rid, "T3")
    assert r["result"] == "FAIL" and any(ids_[4] in i and "expected_result_spec_reference" in i and "missing_reference" in i for i in r["issues"]), r["issues"]

def test_06_missing_reference_routes_back_then_tampered_copy_fails_and_intact_copy_passes():
    rid = S["run"]
    issue = {"testcase_id": S["bad_tc"], "issue_type": "missing_reference", "severity": "major", "violated_requirement": f"REQ-{AREA}-004",
             "spec_reference": {"spec_id": OTHER, "spec_version": "1.0", "location": "§3.3 R4"}, "evidence": "expected_result_spec_reference 指向派發包外的 spec",
             "explanation": "依據不在派發包範圍內", "recommended_change": f"改引用 {SPEC}"}
    _, p = _report(rid, S["draft"], "FAIL", [issue])
    assert engine.submit(rid, "T3", str(p))[0]
    r = engine.evaluate_gate(rid, "T3"); assert r["layer"] == "semantic" and r["result"] == "FAIL", r
    assert engine.load_run(rid)["current_task_id"] == "T2"
    tcs, _ = _tcs("01JZZZZZZZZZZZZZZZZZZZZZZ"); did = _design(rid, tcs, iteration=1)
    _, p = _report(rid, did, "PASS")
    t3 = engine._task(engine.load_run(rid), "T3"); entry = dispatch.current_packet(engine.load_run(rid), t3)["review_drafts"][0]
    assert entry["artifact_id"] == did and t3["iteration"] == 1
    original = store.read_bytes(entry["path"])
    leaked = store.load(entry["path"]); leaked["payload"]["testcases"][0]["design_rationale"] = "被塞回的推理說明"
    H.raw_save(entry["path"], leaked)                                                 # 竄改副本（外部寫入）
    assert engine.submit(rid, "T3", str(p))[0]
    r = engine.evaluate_gate(rid, "T3"); assert r["result"] == "FAIL" and any("審查用 Draft 副本" in i and "sha256" in i for i in r["issues"]), r["issues"]
    store.abspath(entry["path"]).write_bytes(original)                                # 還原後同一份報告 PASS
    r = engine.evaluate_gate(rid, "T3", new_request=True); assert r["result"] == "PASS", r["issues"]   # 同一組 artifact 重評：新請求
    assert engine.load_run(rid)["status"] == "WAITING_HUMAN"
