"""P6：P5 自審 F1、F5（附錄 A 6-36、6-37）。狀態都以正式流程建立；標明「函式層」的子例直接呼叫內部函式。"""
import json
from tests.test_p4_dispatch import mkroot, py
from tests.test_p5_review_r2_fixes import REDO

OKQ = 'F.req(1, [F.dp("Q01", "defined_in_target", "none", known=[F.sref("任何站台都不能刪除。")])])'
DREF = '[{"requirement_id": "REQ-DEMO-001", "question_id": "Q01", "basis_ref": F.ident(F.sref("任何站台都不能刪除。"))}]'

def test_f1_tval_report_must_review_this_round_draft(tmp_path):
    """F1／6-36（G-TVAL）：Validator FAIL 退回 → Designer 重做第二稿 → 兩邊本輪都有產出，但報告的 payload 審的是第一稿（已 SUPERSEDED，檔案仍在；
    references 指第二稿，所以 submit 的引用檢查擋不到）→ Structural FAIL，不 materialize、只寫診斷；報告改審第二稿 → PASS，正式 TC 由第二稿產生。"""
    root = mkroot(tmp_path)
    out = py(root, f"""
rid = F.new_run(); g = F.analyze(rid, [{OKQ}])
d1 = F.design(rid, [F.tc(1, "REQ-DEMO-001", "刪除子站台被拒（第一稿）", techs=["negative"], types=["negative"], drefs={DREF})])
issue = {{"testcase_id": "*", "issue_type": "missing_coverage", "severity": "major", "violated_requirement": "REQ-DEMO-001", "spec_reference": None,
          "evidence": "e", "explanation": "缺少列表頁的檢查", "recommended_change": "補一條"}}
f1 = F.validate(rid, d1["did"], g["rmid"], "FAIL", [issue])
d2 = F.design(rid, [F.tc(1, "REQ-DEMO-001", "刪除子站台被拒（第二稿）", techs=["negative"], types=["negative"], drefs={DREF}),
                    F.tc(2, "REQ-DEMO-001", "列表頁沒有刪除按鈕", drefs={DREF})])
before = sorted(store.glob("testcases/registry/TC-*.yaml"))
_, pv = H.write_artifact(rid, "T3", "agent-test-validator", "TestValidationReport", H.validation_report(d1["did"], g["rmid"], "PASS"),   # references 指第二稿、payload 審第一稿
                         [{{"entity_type": "Artifact", "id": d2["did"]}}, {{"entity_type": "Artifact", "id": g["rmid"]}}], {{"type": "TestCaseDraft", "ids": [d2["did"]]}}, "validation")
sub = engine.submit(rid, "T3", str(pv)); stale = engine.evaluate_gate(rid, "T3")
run = engine.load_run(rid); t3 = engine._task(run, "T3")
mid = sorted(store.glob("testcases/registry/TC-*.yaml"))
ok = F.validate(rid, d2["did"], g["rmid"], "PASS")
after = sorted(store.glob("testcases/registry/TC-*.yaml"))
titles = sorted(store.load(store.tc_version_path(store.load(p)["testcase_id"], 1))["title"] for p in after if p not in before)
print(json.dumps({{"f1": f1["result"], "d1_status": store.load(store.find_artifact(d1["did"]))["status"], "t2_out": engine._task(run, "T2")["output_artifact_ids"], "d2": d2["did"],
                  "sub": sub[0], "stale": stale, "t3": [t3["status"], t3["gate_results"][-1]], "mid": mid == before, "ok": ok["result"], "titles": titles}}, default=str))""")
    assert out["f1"] == "FAIL" and out["d1_status"] == "SUPERSEDED" and out["d2"] in out["t2_out"] and len(out["t2_out"]) == 4   # 退回不清空清單：兩稿與各自的 Report
    s = out["stale"]
    assert out["sub"] is True and s["result"] == "FAIL" and any("SUPERSEDED，不是本輪有效的 Draft" in i for i in s["issues"]), s
    assert out["t3"][0] == "READY" and out["mid"]                                              # 診斷：task 回 READY，沒有 materialize
    assert out["ok"] == "PASS" and out["titles"] == ["列表頁沒有刪除按鈕", "刪除子站台被拒（第二稿）"]

def test_f1_bval_report_must_review_this_round_draft(tmp_path):
    """F1／6-36（G-BVAL）：第一稿 PASS → 人 reject OPEN_BUG → 第二稿；報告指向第一稿（仍 VALID）→ Structural FAIL，Bug 狀態不轉換；
    改指第二稿 → PASS → OPEN_BUG 核准 → 正式 Bug 的 draft 與落地判定的最終稿都是第二稿。"""
    root = mkroot(tmp_path)
    out = py(root, REDO + """
rid0, cid = e4_clr()                                                                     # 建立 RM（spec-to-bug 的 T0 才能略過）
b, evd = bug_run()
bd1 = bug_draft(b, evd); assert bug_validate(b, bd1, evd, "PASS")["result"] == "PASS"
F.approve(F.waiting(b), decision="reject", rationale="重寫")
bd2 = bug_draft(b, evd)
st0 = store.load(engine._bug_path(engine.load_run(b)))["status"]
stale = bug_validate(b, bd1, evd, "PASS")
run = engine.load_run(b); t2 = engine._task(run, "T2"); st1 = store.load(engine._bug_path(run))["status"]
ok = bug_validate(b, bd2, evd, "PASS"); F.approve(F.waiting(b))
run = engine.load_run(b); ent = store.load(engine._bug_path(run))
print(json.dumps({"stale": stale, "t2": t2["status"], "st": [st0, st1], "ok": ok["result"], "run": run["status"], "ent": [ent["status"], ent["draft_artifact_id"]],
                  "final": L._final_bugdraft(b)["artifact_id"], "bd": [bd1, bd2], "bd1": store.load(store.find_artifact(bd1))["status"]}))""")
    s = out["stale"]
    assert out["bd1"] == "VALID" and s["result"] == "FAIL" and any("不是 T1 本輪的產出" in i for i in s["issues"]), s
    assert out["t2"] == "READY" and out["st"] == ["VALIDATING", "VALIDATING"]                  # 只寫診斷，Bug 沒有轉成 VALIDATED
    assert out["ok"] == "PASS" and out["run"] == "COMPLETED"
    assert out["ent"] == ["OPEN", out["bd"][1]] and out["final"] == out["bd"][1]

def test_f1_function_level_wrong_type_and_no_producer(tmp_path):
    """函式層（6-36）：報告指向產生者本輪產出中的非 Draft artifact（TestDesignReport）→ 拒絕；run 沒有產生者 task → 拒絕；task 為 None → 不核對。"""
    root = mkroot(tmp_path)
    out = py(root, f"""
rid = F.new_run(); g = F.analyze(rid, [{OKQ}])
d1 = F.design(rid, [F.tc(1, "REQ-DEMO-001", "刪除子站台被拒", techs=["negative"], types=["negative"], drefs={DREF})])
run = engine.load_run(rid); t2 = engine._task(run, "T2"); t3 = engine._task(run, "T3")
rep_id = next(a for a in t2["output_artifact_ids"] if a != d1["did"])
wrong = gates.reviewed_draft_issues(run, t3, "TestCaseDraft", rep_id)
right = gates.reviewed_draft_issues(run, t3, "TestCaseDraft", d1["did"])
nobug = gates.reviewed_draft_issues(run, t3, "BugDraft", d1["did"])
fn = gates.reviewed_draft_issues(run, None, "TestCaseDraft", "ART-X")
print(json.dumps({{"wrong": wrong, "right": right, "nobug": nobug, "fn": fn}}))""")
    assert out["wrong"] and "不是 TestCaseDraft" in out["wrong"][0]
    assert out["right"] == [] and out["fn"] == []
    assert out["nobug"] and "沒有產生 BugDraft 的 task" in out["nobug"][0]

def _rejected_bug_case(kind):
    """CLR E4 → 回答 → BugDraft 以明確 SourceRef 採用（A4 → INCORPORATED）→ Validator DUPLICATE（確認重複）或 AMBIGUITY（reject：非 Bug）→ Bug REJECTED、run COMPLETED。"""
    return REDO + f"""
rid0, cid = e4_clr()
b, evd = bug_run(); bd = bug_draft(b, evd, **adopt(cid))
inc = clr.load(cid)["status"]
rep = {{"result": "{kind}", "bug_draft_artifact_id": bd,
       "checks": {{k: False for k in ["violates_spec", "expected_has_spec_basis", "actual_supported_by_evidence", "reproduction_sufficient", "severity_reasonable", "priority_reasonable", "not_duplicate", "not_mere_ambiguity"]}},
       "issues": [], "evidence_verification": [{{"evidence_id": evd, "hash_verified": True, "supports_claim": True}}],
       "severity_assessment": {{"severity_recommended": "major", "priority_recommended": "high", "agrees_with_analyst": True, "rationale": "同意"}},
       "duplicate_check": {{"searched": True, "duplicate_of": "BUG-DEMO-0001" if "{kind}" == "DUPLICATE" else None}}}}
if "{kind}" == "AMBIGUITY": rep["ambiguity"] = {{"level": "critical", "description": "站長能否刪除子站台未定義"}}
_, p = H.write_artifact(b, "T2", "agent-bug-validator", "BugValidationReport", rep, [{{"entity_type": "Artifact", "id": bd}}, {{"entity_type": "Evidence", "id": evd}}], {{"type": "BugDraft", "ids": [bd]}}, "validation")
assert engine.submit(b, "T2", str(p))[0]; g2 = engine.evaluate_gate(b, "T2")
F.approve(F.waiting(b), decision="approve" if "{kind}" == "DUPLICATE" else "reject", rationale="確認重複" if "{kind}" == "DUPLICATE" else "不是 bug")
run = engine.load_run(b); ent = store.load(engine._bug_path(run))["status"]
cands = L.impact(cid, ["刪除"], [], "oscar", new_request=True)["candidates"]; concl = [f"{{x['tc_id']}}=not_affected" for x in cands]
h0 = P.clr_sha(cid)
bad = P.apply_(cid, landed_in=[b], targets=[T], keywords=["刪除"], tc_conclusions=concl)
h1 = P.clr_sha(cid)
rt = L.run_targets(clr.load(cid), b); fb = L._final_bugdraft(b)
"""

def test_f5_rejected_duplicate_bug_run_is_not_a6_landed_in(tmp_path):
    """F5／6-37：Bug 經 CONFIRM_DUPLICATE 確認重複 → REJECTED、run COMPLETED；最終 BugDraft 雖採用 CLR，該 run 不能作為 a6 的 landed-in（明確拒絕、CLR 不變），
    也不提供採用目標。對照：同一張 CLR 以 Bug 成立的 run 落地 → APPLIED。"""
    root = mkroot(tmp_path)
    out = py(root, _rejected_bug_case("DUPLICATE") + """
b2, evd2 = bug_run(); bd2 = bug_draft(b2, evd2, **adopt(cid)); assert bug_validate(b2, bd2, evd2, "PASS")["result"] == "PASS"; F.approve(F.waiting(b2))
ok = P.apply_(cid, landed_in=[b2], targets=[T], keywords=["刪除"], tc_conclusions=concl)
print(json.dumps({"inc": inc, "g2": g2["result"], "run": run["status"], "ent": ent, "bad": bad, "h": [h0, h1], "rt": rt, "fb": fb, "ok": ok, "s": clr.load(cid)["status"]}, default=str))""")
    assert out["inc"] == "INCORPORATED" and out["run"] == "COMPLETED" and out["ent"] == "REJECTED"
    assert "Bug 已 REJECTED" in out["bad"].get("error", "") and "確認重複於 BUG-DEMO-0001" in out["bad"]["error"] and "a6b" not in out["bad"]["error"], out["bad"]
    assert out["h"][0] == out["h"][1] and out["rt"] == [] and out["fb"] is None
    assert "error" not in out["ok"] and out["s"] == "APPLIED", out["ok"]

def test_f5_rejected_ambiguity_bug_run_is_not_a6_landed_in(tmp_path):
    """F5／6-37：Validator AMBIGUITY → RESOLVE_AMBIGUITY reject（非 Bug）→ REJECTED、run COMPLETED → a6 拒絕；CLR 維持 INCORPORATED。"""
    root = mkroot(tmp_path)
    out = py(root, _rejected_bug_case("AMBIGUITY") + """
print(json.dumps({"run": run["status"], "ent": ent, "bad": bad, "h": [h0, h1], "rt": rt, "fb": fb, "s": clr.load(cid)["status"]}, default=str))""")
    assert out["run"] == "COMPLETED" and out["ent"] == "REJECTED"
    assert "Bug 已 REJECTED" in out["bad"].get("error", "") and "--path a6b" in out["bad"]["error"], out["bad"]
    assert out["h"][0] == out["h"][1] and out["rt"] == [] and out["fb"] is None and out["s"] == "INCORPORATED"
