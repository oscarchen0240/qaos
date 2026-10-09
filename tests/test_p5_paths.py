"""P5：apply 的 a7、a6b 路徑與 bug 流程的 A4（需求 A 第 6 章 §5.2、§5.7、§5.8；AC-10A-9、11、31、32、36～41、43～46）。
所有狀態以正式流程建立：spec-to-testcase／spec-to-bug run、evidence add、submit、gate、approve、clarification ask／answer。"""
import json
from tests import p1_util as U
from tests.test_p4_dispatch import mkroot, py

HDR = "from tests import p5_flow as P\nfrom tools.qaos import clr_lifecycle as L\n"
BUG = HDR + """
from tests import helpers as H
from tools.qaos.cli import evidence_add
def e4_clr():
    '''REQ-DEMO-001/Q01 為 E4 minor（需求 ACTIVE）→ 入口 A 開 spec_question；回答 requirement_clarified。'''
    rid = F.new_run(); g = F.analyze(rid, [F.req(1, [F.dp("Q01", "undefined", "minor", decision_needed="站長能否刪除自己站的子站台")], ambiguity=F.amb("minor", "minor"))])
    cid = F.clrs(requirement_id="REQ-DEMO-001")[0]["clarification_id"]
    clr.answer(cid, "任何站台都不能刪除。", "pm", "requirement_clarified", "oscar", new_request=True)
    return rid, cid
def bug_run():
    evd = evidence_add("api_response", "oscar", inline='{"deleted": true}', owner="demo", description="子站台被刪除", new_request=True)
    run = engine.new_run("spec-to-bug", {"spec_id": F.SPEC, "spec_version": F.VER, "evidence_ids": [evd]}, F.BY, new_request=True)
    return run["run_id"], evd
def bug_draft(rid, evd, srcs=None, drefs=None):
    d = {"draft_id": "BUG-DRAFT-01ARZ3NDEKTSV4RRFFQ69G5FAV", "title": "站長可以刪除自己站台的子站台", "product": "demo", "functional_area": "DEMO",
         "severity_proposed": "major", "priority_proposed": "high", "severity_rationale": "違反刪除規則", "environment": {"name": "stage"},
         "spec_id": F.SPEC, "spec_version": F.VER, "requirement_id": "REQ-DEMO-001", "acceptance_criteria_ids": ["AC-DEMO-0011"], "preconditions": ["以站長登入"],
         "reproduction_steps": ["進入站台列表", "刪除子站台"], "expected_result": "系統拒絕刪除", "expected_result_spec_reference": {"spec_id": F.SPEC, "spec_version": F.VER, "location": "§刪除規則"},
         "actual_result": "子站台被刪除", "actual_result_evidence_map": [{"claim": "回 deleted=true", "evidence_id": evd}], "evidence_ids": [evd], "impact": "資料遺失",
         "suspected_area": "site api", "ambiguity_suspected": False, "duplicate_candidates": []}
    if srcs is not None: d["source_refs"] = srcs
    if drefs is not None: d["decision_refs"] = drefs
    bd, p = H.write_artifact(rid, "T1", "agent-bug-analyst", "BugDraft", d, [{"entity_type": "Requirement", "id": "REQ-DEMO-001"}, {"entity_type": "Evidence", "id": evd}],
                             {"type": "Evidence", "ids": [evd]}, "bug-analysis")
    assert engine.submit(rid, "T1", str(p))[0]; g = engine.evaluate_gate(rid, "T1"); assert g["result"] == "PASS", g
    return bd
def bug_validate(rid, bd, evd, result):
    rep = {"result": result, "bug_draft_artifact_id": bd,
           "checks": {k: result == "PASS" for k in ["violates_spec", "expected_has_spec_basis", "actual_supported_by_evidence", "reproduction_sufficient", "severity_reasonable", "priority_reasonable", "not_duplicate", "not_mere_ambiguity"]},
           "issues": [] if result == "PASS" else [{"testcase_id": "*", "issue_type": "critical_ambiguity", "severity": "major", "violated_requirement": "REQ-DEMO-001", "spec_reference": None,
                                                   "evidence": "e", "explanation": "規則有歧義", "recommended_change": "問 PM"}],
           "evidence_verification": [{"evidence_id": evd, "hash_verified": True, "supports_claim": True}],
           "severity_assessment": {"severity_recommended": "major", "priority_recommended": "high", "agrees_with_analyst": True, "rationale": "同意"},
           "duplicate_check": {"searched": True, "duplicate_of": None}}
    if result == "AMBIGUITY": rep["ambiguity"] = {"level": "critical", "description": "站長能否刪除子站台未定義"}
    _, p = H.write_artifact(rid, "T2", "agent-bug-validator", "BugValidationReport", rep, [{"entity_type": "Artifact", "id": bd}, {"entity_type": "Evidence", "id": evd}], {"type": "BugDraft", "ids": [bd]}, "validation")
    ok, pr = engine.submit(rid, "T2", str(p)); assert ok, pr
    return engine.evaluate_gate(rid, "T2")
def reject_with(rid, entries):
    apr = F.waiting(rid); F.approve(apr, decision="reject", resolutions=entries, rationale="不是 bug，是需求歧義")
    return apr
"""

def test_a7_paths(tmp_path):
    """a7：沒有任何引用 → APPLIED（AC-10A-36、37）；有引用（核准決議包裝、revision、TC）→ 拒絕並列出位置（AC-10A-9、38、39）；a7 帶 --landed-in → 拒絕（AC-10A-40）。"""
    root = mkroot(tmp_path)
    out = py(root, HDR + """
q = clr.new("demo", "DEMO", F.SPEC, F.VER, "子站台的排序要不要可設定？", "oscar", consulted=["SPEC-DEMO-001@1.0"], requirement_id="REQ-DEMO-009", new_request=True)
clr.ask(q["clarification_id"], "pm", "oscar", sent_at="2026-10-01T09:00:00Z", channel="slack", new_request=True)
clr.answer(q["clarification_id"], "維持現狀，不需要。", "pm", "no_change", "oscar", new_request=True)
s = L.impact(q["clarification_id"], ["排序"], [], "oscar", new_request=True)
land_in = P.apply_(q["clarification_id"], path="a7", landed_in=["RUN-X"], scan_id=s["scan_id"])
land_tg = P.apply_(q["clarification_id"], path="a7", targets=["SPEC-DEMO-001@1.0:REQ-DEMO-009#Q01"], scan_id=s["scan_id"])
land_df = P.apply_(q["clarification_id"], path="a7", defer_targets=["SPEC-DEMO-001@1.0:REQ-DEMO-009#Q01=下週"], scan_id=s["scan_id"])
ok36 = P.apply_(q["clarification_id"], path="a7", scan_id=s["scan_id"], tc_conclusions=[f"{x['tc_id']}=not_affected" for x in s["candidates"]])
q2 = clr.new("demo", "DEMO", F.SPEC, F.VER, "子站台名稱要不要支援表情符號？", "oscar", consulted=["SPEC-DEMO-001@1.0"], new_request=True)
clr.answer(q2["clarification_id"], "超出本次範圍。", "pm", "out_of_scope", "oscar", new_request=True)
ok37 = P.apply_(q2["clarification_id"], path="a7", no_keyword_reason="沒有掛需求，也沒有可用的關鍵字", tc_conclusions=[])
ra = P.full_ra(); cid = ra["cid"]                                                       # rev 0 被 approval 包裝、revision、TC 引用
clr.answer(cid, "維持原規則，不需要改。", "pm", "no_change", "oscar", new_request=True)    # A5 → ANSWERED，最新 resolution no_change
h0 = P.clr_sha(cid); ref = P.apply_(cid, path="a7", no_keyword_reason="x", tc_conclusions=[f"{t}=not_affected" for t in ra["tcs"]]); h1 = P.clr_sha(cid)
print(json.dumps({"land_in": land_in, "land_tg": land_tg, "land_df": land_df, "ok36": clr.load(q["clarification_id"]), "ok37": clr.load(q2["clarification_id"]), "ref": ref, "h": [h0, h1], "apr": ra["apr"], "q": q}, default=str))""")
    for k in ("land_in", "land_tg", "land_df"): assert "--path a7 不接受" in out[k]["error"], k            # AC-A-B1-16：a7 的不接受輸入
    c36 = out["ok36"]; l = c36["landings"][-1]
    assert c36["status"] == "APPLIED" and l["path"] == "a7" and l["reference_scan_sha256"] and l["final_keywords"] == ["排序"] and l["scan_id"].startswith("SCAN-")
    assert c36["sent_at"] == "2026-10-01T09:00:00Z" and c36["asked_at"] and c36["channel"] == "slack"         # A1：兩個時間都保留
    assert out["ok37"]["status"] == "APPLIED" and out["ok37"]["landings"][-1]["no_keyword_reason"]
    err = out["ref"]["error"]
    assert "全部歷史都沒有引用" in err and f"{out['apr']} resolutions[0]（approve）" in err and "revision " in err and "TC TC-DEMO-001 v1" in err
    assert out["h"][0] == out["h"][1]

def test_a6b_bug_reject_path(tmp_path):
    """a6b：reject 決議條目的內部 source 指向 CLR 最新 rev → APPLIED（AC-10A-31、43）；指向舊 rev、普通 reject、條目不是 reject 決議 → 拒絕（AC-10A-44、45）；
    G-SPEC 以 reject 核准單作為 approval 型 SourceRef → X15（AC-10A-46）。"""
    root = mkroot(tmp_path)
    out = py(root, BUG + """
rid0, cid = e4_clr()
src0 = F.cref(cid, "任何站台都不能刪除")
entry = lambda src: [{"requirement_id": "REQ-DEMO-001", "question_id": "Q01", "outcome": "select_interpretation", "source": src, "rationale": "依 PM 回答，這不是 bug"}]
b1, evd = bug_run(); bd = bug_draft(b1, evd); assert bug_validate(b1, bd, evd, "AMBIGUITY")["result"] == "AMBIGUITY"; apr1 = reject_with(b1, entry(src0))
b3, evd3 = bug_run(); bd3 = bug_draft(b3, evd3); bug_validate(b3, bd3, evd3, "AMBIGUITY"); apr3 = reject_with(b3, [])                       # 普通 reject（沒有條目）
clr.answer(cid, "任何站台都不能刪除（補充：含總站台）。", "pm", "requirement_clarified", "oscar", new_request=True)                        # 最新 rev 變成 1
h0 = P.clr_sha(cid); r = {}
r["old_rev"] = P.apply_(cid, path="a6b", landed_in=[b1], targets=[f"{apr1}#0"], keywords=["刪除"])
r["plain"] = P.apply_(cid, path="a6b", landed_in=[b3], targets=[f"{apr3}#0"], keywords=["刪除"])
r["not_bug_run"] = P.apply_(cid, path="a6b", landed_in=[rid0], targets=[f"{apr1}#0"], keywords=["刪除"])
r["defer"] = P.apply_(cid, path="a6b", landed_in=[b1], targets=[f"{apr1}#0"], defer_targets=["SPEC-DEMO-001@1.0:REQ-DEMO-001#Q01=下週"], keywords=["刪除"])
h1 = P.clr_sha(cid)
b2, evd2 = bug_run(); bd2 = bug_draft(b2, evd2); bug_validate(b2, bd2, evd2, "AMBIGUITY"); apr2 = reject_with(b2, entry(F.cref(cid, "任何站台都不能刪除")))
st = engine.load_run(b2)["status"]
ok = P.apply_(cid, path="a6b", landed_in=[b2], targets=[f"{apr2}#0"], keywords=["刪除"])
print(json.dumps({"r": r, "h": [h0, h1], "st": st, "ok": ok, "c": clr.load(cid), "apr1": apr1, "apr2": apr2}, default=str))""")
    r = out["r"]
    assert "不是最新的 rev 1" in r["old_rev"]["error"]                                             # AC-10A-44
    assert "沒有 resolutions[0]" in r["plain"]["error"]                                           # AC-10A-45
    assert "--path a6b 不接受 --defer-target" in r["defer"]["error"]                                # AC-A-B1-16：a6b 的不接受輸入
    assert "不是 COMPLETED" in r["not_bug_run"]["error"]                                            # 落地 run 必須 COMPLETED（非 bug run 另由 workflow 檢查擋下）
    assert out["h"][0] == out["h"][1] and out["st"] == "COMPLETED"
    c = out["c"]; l = c["landings"][-1]
    assert c["status"] == "APPLIED" and l["path"] == "a6b" and l["targets_confirmed"][0]["entry"] == f"{out['apr2']}#0"   # AC-10A-31、43

def test_a6b_reject_approval_is_not_a_wrapper_in_gspec(tmp_path):
    """AC-10A-46：G-SPEC 以 reject 的核准單作為 approval 型 SourceRef → X15。（先改宣告，讓新 run 一定重新分析。）"""
    root = mkroot(tmp_path)
    apr = py(root, BUG + """
rid0, cid = e4_clr()
b1, evd = bug_run(); bd = bug_draft(b1, evd); bug_validate(b1, bd, evd, "AMBIGUITY")
apr = reject_with(b1, [{"requirement_id": "REQ-DEMO-001", "question_id": "Q01", "outcome": "select_interpretation", "source": F.cref(cid, "任何站台都不能刪除"), "rationale": "依 PM 回答，這不是 bug"}])
print(json.dumps(apr))""")
    U.q(root, "spec", "reference", "add", "SPEC-DEMO-001@1.0", "--ref", "SPEC-REFB-001@1.0", "--role", "informative", "--by", "oscar", check=True)
    out = py(root, BUG + f"""
rid2 = F.new_run(); cur = engine.load_run(rid2)["current_task_id"]
g = F.analyze(rid2, [F.req(1, [F.dp("Q01", "undefined", "minor", resolution={{"source": F.aref("{apr}", 0, "依 PM 回答"), "decided_at": "2026-10-07", "adopted_side_index": None}})], ambiguity=F.amb("none", "minor"))])
print(json.dumps([cur, g["result"], g.get("issues")]))""")
    assert out[0] == "T1" and out[1] == "FAIL" and any(i.startswith("X15：") and "reject" in i for i in out[2]), out

def test_bug_flow_a4_and_a6(tmp_path):
    """BugDraft 以明確 SourceRef（對應 decision_refs）引用 CLR 最新 rev → A4（AC-10A-11）；沒有 SourceRef 的 BugDraft 不觸發 A4（AC-10A-32）；
    bug run COMPLETED 後以 a6 結案，目標來自最終 BugDraft。"""
    root = mkroot(tmp_path)
    out = py(root, BUG + """
rid0, cid = e4_clr()
b0, evd0 = bug_run(); bug_draft(b0, evd0); s_plain = clr.load(cid)["status"]; engine.cancel(b0, F.BY, new_request=True)
src = F.cref(cid, "任何站台都不能刪除")
b1, evd = bug_run(); bd = bug_draft(b1, evd, srcs=[src], drefs=[{"requirement_id": "REQ-DEMO-001", "question_id": "Q01", "basis_ref": F.ident(src)}])
s_a4 = clr.load(cid); assert bug_validate(b1, bd, evd, "PASS")["result"] == "PASS"
F.approve(F.waiting(b1)); st = engine.load_run(b1)["status"]
T = "SPEC-DEMO-001@1.0:REQ-DEMO-001#Q01"
cands = L.impact(cid, ["刪除"], [], "oscar", new_request=True)["candidates"]
ok = P.apply_(cid, landed_in=[b1], targets=[T], keywords=["刪除"], tc_conclusions=[f"{x['tc_id']}=not_affected" for x in cands])
print(json.dumps({"s_plain": s_plain, "s_a4": s_a4["status"], "land": s_a4["landings"][-1], "st": st, "ok": ok, "c": clr.load(cid)}, default=str))""")
    assert out["s_plain"] == "ANSWERED"                                                            # AC-10A-32
    assert out["s_a4"] == "INCORPORATED" and out["land"]["type"] == "incorporated" and out["land"]["bug_draft"].startswith("ART-")   # AC-10A-11
    assert out["st"] == "COMPLETED", out
    c = out["c"]; assert c["status"] == "APPLIED", out["ok"]
    assert c["landings"][-1]["targets_confirmed"][0]["requirement_id"] == "REQ-DEMO-001"
