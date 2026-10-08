"""P6：CLR 生命週期與第一批整體 AC 的收尾（需求 A 第 6 章 §5、§11、§12.3、§12.4；第 1 章 §5 核准決議表；附錄 A 6-21）。

補驗 P5 驗收紀錄標「部分」「待 P6」的項目（AC-10A-14、47、15、28、39），以及 AC-A-B1 逐條核對時發現沒有專門測試的部分
（AC-A-B1-1 的逐停點斷言、AC-A-B1-6、AC-A-B1-9 的正式流程、AC-A-B1-10 的 AC-07-44、AC-A-B1-12 的 RA-P7 背景候選、AC-A-B1-13）。

所有狀態以測試 root 的正式流程建立：spec import、spec reference add、run new、dispatch、submit、gate、approve、
clarification new／ask／answer／applicability add／impact／apply、testcase-revision（TC 修訂）、spec-change-impact。
agent 的產出由 tests/helpers.write_artifact 寫入（外部寫入）。AC-A-B1-6、AC-07-44 的 legacy 資料由需求 A 之前的程式
（tests/p3_legacy.py）或 P1 的 legacy fixture（tests/test_p1_audit.legacy_root）產生，屬 legacy fixture。
拒絕案例依第 6 章 §12.1：先斷言拒絕、CLR 檔 hash 不變，最後才執行成功例。"""
import json, os, pathlib, re, subprocess, sys
import pytest
from tests import p1_util as U
from tests.test_p4_dispatch import mkroot, py

HDR = "from tests import p5_flow as P\nfrom tools.qaos import clr_lifecycle as L, tc_ops\n"

# testcase-revision：以正式流程修訂一張 ACTIVE TC（新版本 Draft → G-DESIGN → Validator → ACTIVATE_TESTCASE → 新版 ACTIVE、舊版 SUPERSEDED）
REV = """
def last_rm():
    arts = sorted((store.load(p_) for p_ in store.glob("artifacts/*/*/*.yaml")), key=lambda a: a["artifact_id"])
    return [a["artifact_id"] for a in arts if a.get("artifact_type") == "RequirementModel" and a.get("status") == "VALID"][-1]
def revise_tc(tc, title, drop_refs=False):
    ptr = store.load(store.tc_pointer_path(tc)); ver = ptr["active_version"]
    v = store.load(store.tc_version_path(tc, ver))
    rid = tc_ops.revise(tc, "PM 改口徑", F.BY)["run_id"]
    keep = ["title", "product", "functional_area", "requirement_ids", "acceptance_criteria_ids", "spec_id", "spec_version", "test_level", "test_types", "design_techniques",
            "priority", "risk", "execution_mode", "preconditions", "test_data", "steps", "expected_result", "expected_result_spec_reference", "assumptions",
            "automation_status", "ci_eligible", "hotfix_eligible", "execution_cost", "stability", "critical_path", "decision_refs", "source_refs"]
    d = {k: v[k] for k in keep if k in v}
    d.update(title=title, draft_id="TC-DRAFT-01ARZ3NDEKTSV4RRFFQ69GR" + tc[-3:], source="change_workflow", supersedes_testcase={"testcase_id": tc, "version": ver})
    if drop_refs: d.pop("decision_refs", None); d.pop("source_refs", None)
    did, pd = H.write_artifact(rid, "T1", "agent-test-designer", "TestCaseDraft", {"mode": "change", "spec_id": d["spec_id"], "spec_version": d["spec_version"], "testcases": [d]},
                               [{"entity_type": "TestCase", "id": tc}], {"type": "TestCaseVersion", "ids": [tc]}, "test-design")
    rep = H.design_report(did, [d]); rep["mode"] = "change"
    _, pr = H.write_artifact(rid, "T1", "agent-test-designer", "TestDesignReport", rep, [{"entity_type": "Artifact", "id": did}], {"type": "TestCaseDraft", "ids": [did]}, "test-design")
    for p_ in (pd, pr):
        ok_, pr_ = engine.submit(rid, "T1", str(p_)); assert ok_, pr_
    g_ = engine.evaluate_gate(rid, "T1"); assert g_["result"] == "PASS", g_
    _, pv = H.write_artifact(rid, "T2", "agent-test-validator", "TestValidationReport", H.validation_report(did, last_rm(), "PASS"),
                             [{"entity_type": "Artifact", "id": did}], {"type": "TestCaseDraft", "ids": [did]}, "validation")
    ok_, pr_ = engine.submit(rid, "T2", str(pv)); assert ok_, pr_
    g_ = engine.evaluate_gate(rid, "T2"); assert g_["result"] == "PASS", g_
    F.approve(F.waiting(rid)); assert engine.load_run(rid)["status"] == "COMPLETED"
    return rid
"""

T1 = "SPEC-DEMO-001@1.0:REQ-DEMO-001#Q01"
T2 = "SPEC-DEMO-001@1.0:REQ-DEMO-002#Q01"


def clr_file(root, cid):
    return pathlib.Path(root) / "clarifications/demo/DEMO" / f"{cid}.yaml"


# ================================================================ AC-10A-28：scan 之後候選 TC 被修訂
def test_ac_10a_28_candidate_revised_after_scan(tmp_path):
    """AC-10A-28（R1004-P2）：impact 產生 S1 → 候選 TC 以 testcase-revision 修訂（active_version 1 → 2）→ apply --scan S1：
    鎖內重新掃描、顯示差異、以新版本為準要求結論；landing 保存最新版本與 sha256。"""
    root = mkroot(tmp_path)
    out = py(root, HDR + REV + """
ra = P.full_ra(); cid = ra["cid"]; tc = ra["tcs"][0]
s1 = L.impact(cid, ["刪除"], [], "oscar", new_request=True); v1sha = store.sha256_file(store.tc_version_path(tc, 1))
rv = revise_tc(tc, "刪除子站台被拒（依 PM 回答，修訂版）")
ptr = store.load(store.tc_pointer_path(tc))
print(json.dumps({"cid": cid, "rid": ra["rid"], "tc": tc, "s1": s1, "ptr": ptr, "v1": v1sha,
                  "v2": store.sha256_file(store.tc_version_path(tc, 2))}, default=str))""")
    cid, tc = out["cid"], out["tc"]
    assert [(x["tc_id"], x["active_version"], x["tc_version_sha256"]) for x in out["s1"]["candidates"]] == [(tc, 1, out["v1"])]   # S1 保存的是 v1
    assert out["ptr"]["active_version"] == 2 and out["v1"] != out["v2"]
    base = ["clarification", "apply", cid, "--path", "a6", "--landed-in", out["rid"], "--target", T1, "--scan", out["s1"]["scan_id"],
            "--impact-reviewed", "逐張確認", "--by", "oscar", "--new-request"]
    h0 = U.sha(clr_file(root, cid))
    r = U.q(root, *base)                                                                          # 沒有結論 → 拒絕，列出 TC（以重新掃描的候選為準）
    assert r.returncode != 0 and "缺少 --tc-conclusion" in r.stderr and tc in r.stderr and U.sha(clr_file(root, cid)) == h0
    r = U.q(root, *base, "--tc-conclusion", f"{tc}=updated")
    assert r.returncode == 0, r.stderr
    assert "重新掃描的候選和 scan 不同" in r.stdout and f"('{tc}', 1)" in r.stdout and f"('{tc}', 2)" in r.stdout   # 顯示差異
    c = U.load(root, f"clarifications/demo/DEMO/{cid}.yaml"); l = c["landings"][-1]
    assert c["status"] == "APPLIED" and l["scan_reused"] == "full" and l["scan_id"] == out["s1"]["scan_id"]
    assert [(x["tc_id"], x["active_version"], x["tc_version_sha256"]) for x in l["candidates"]] == [(tc, 2, out["v2"])]   # landing 保存最新版本


# ================================================================ AC-10A-39：SUPERSEDED 版本的 decision_refs 也算全部歷史
def test_ac_10a_39_superseded_version_counts_as_history(tmp_path):
    """AC-10A-39（R1101-N2）：TC v1 的 decision_refs 引用 CLR rev 0；TC 經 testcase-revision 修訂 → v1 成為 SUPERSEDED；
    答案改為 no_change 後 a7 → 拒絕，引用位置逐版列出，含 SUPERSEDED 的 v1（全部歷史）；CLR 不變。
    限制：正式流程中 SUPERSEDED 版本無法成為唯一的引用處（G-DESIGN 要求有決策點的 TC 帶 decision_refs，revision 與核准單也引用同一張 CLR），
    所以本案例以「拒絕訊息逐一列出 SUPERSEDED 版本」作為專門斷言；只掃 ACTIVE 版本的實作會漏列 v1。"""
    root = mkroot(tmp_path)
    out = py(root, HDR + REV + """
ra = P.full_ra(); cid = ra["cid"]; tc = ra["tcs"][0]
revise_tc(tc, "刪除子站台被拒（修訂版）")
v1, v2 = store.load(store.tc_version_path(tc, 1)), store.load(store.tc_version_path(tc, 2))
clr.answer(cid, "維持原規則，不需要改。", "pm", "no_change", "oscar", new_request=True)
cands = [x["tc_id"] for x in L.scan_candidates(clr.load(cid), [], [], [{"product": "demo", "area": "DEMO"}], "a7")]
h0 = P.clr_sha(cid); ref = P.apply_(cid, path="a7", no_keyword_reason="x", tc_conclusions=[f"{t}=not_affected" for t in cands]); h1 = P.clr_sha(cid)
print(json.dumps({"tc": tc, "v1": [v1["status"], v1.get("decision_refs")], "v2": [v2["status"], v2.get("decision_refs")], "ref": ref, "h": [h0, h1]}, default=str))""")
    tc = out["tc"]
    assert out["v1"][0] == "SUPERSEDED" and out["v1"][1] and out["v2"][0] == "ACTIVE"
    err = out["ref"]["error"]
    assert "全部歷史都沒有引用" in err and f"TC {tc} v1（SUPERSEDED）" in err and f"TC {tc} v2（ACTIVE）" in err
    assert out["h"][0] == out["h"][1]


# ================================================================ AC-10A-14、47：同 product、跨 area
OA_FLOW = """
from tests import helpers as H
from tools.qaos import spec_ops
OA, VER = "SPEC-OA-001", "1.0"
def oa_pin(): return spec_ops.verify_pin(OA, VER)
def oa_run(cid, k):
    '''對 SPEC-OA-001（product demo、area OTH）做 spec-to-testcase：REQ-OTH-001/Q01 以 CLR 最新 rev 為依據（defined_by_decision，經 applicability 通過 X16）→ 設計 → 驗證 → ACTIVATE。'''
    src = F.cref(cid, "任何站台都不能刪除")
    dp = F.dp("Q01", "defined_by_decision", "none", subject="site.child.delete", role=["admin"], known=[src],
              coverage={"references_status": "undeclared", "consulted": [oa_pin()], "unconsulted_normative": [], "missing_sources": [], "waivers": []})
    req = {"requirement_id": "REQ-OTH-001", "version": 1, "spec_id": OA, "spec_version": VER, "type": "functional", "title": "營運區站台刪除", "statement": "營運區站台刪除規則",
           "acceptance_criteria": [{"ac_id": "AC-OTH-0011", "given": "已登入", "when": "刪除子站台", "then": "依規則"}],
           "spec_reference": {"spec_id": OA, "spec_version": VER, "location": "§刪除", "quote": "營運區的站台刪除規則依總規格辦理。"}, "ambiguity": None, "risk": "medium",
           "status": "DRAFT", "history": [], "decision_points": [dp]}
    rid = engine.new_run("spec-to-testcase", {"spec_id": OA, "spec_version": VER}, F.BY, new_request=True)["run_id"]
    refs_ = [{"entity_type": "SpecVersion", "id": OA, "version": VER}]; s_ = {"type": "SpecVersion", "ids": [f"{OA}@{VER}"]}
    sa = {"spec_id": OA, "spec_version": VER, "content_hash": oa_pin()["content_hash"], "summary": "s", "scope": {"in_scope": ["x"], "out_of_scope": []},
          "requirement_ids": ["REQ-OTH-001"], "ambiguities": [], "constraints": [], "edge_case_candidates": [], "open_questions": []}
    _, p1 = H.write_artifact(rid, "T1", "agent-spec-analyst", "SpecAnalysis", sa, refs_, s_, "spec-analysis")
    rmid, p2 = H.write_artifact(rid, "T1", "agent-spec-analyst", "RequirementModel", {"spec_id": OA, "spec_version": VER, "requirements": [req],
                                "traceability": [{"requirement_id": "REQ-OTH-001", "spec_reference": req["spec_reference"]}]}, refs_, s_, "requirements")
    assert engine.submit(rid, "T1", str(p1))[0] and engine.submit(rid, "T1", str(p2))[0]
    g = engine.evaluate_gate(rid, "T1"); assert g["result"] == "PASS", g
    tc = F.tc(1, "REQ-OTH-001", f"營運區刪除子站台被拒（第 {k} 輪）", techs=["negative"], types=["negative"],
              drefs=[{"requirement_id": "REQ-OTH-001", "question_id": "Q01", "basis_ref": F.ident(src)}], srcs=[src])
    tc.update({"functional_area": "OTH", "spec_id": OA, "acceptance_criteria_ids": ["AC-OTH-0011"], "expected_result_spec_reference": {"spec_id": OA, "spec_version": VER, "location": "§刪除"},
               "draft_id": f"TC-DRAFT-01ARZ3NDEKTSV4RRFFQ69GOA0{k}"})
    did, pd = H.write_artifact(rid, "T2", "agent-test-designer", "TestCaseDraft", {"mode": "spec", "spec_id": OA, "spec_version": VER, "testcases": [tc]},
                               [{"entity_type": "Requirement", "id": "REQ-OTH-001"}], {"type": "RequirementModel", "ids": []}, "test-design")
    _, pr = H.write_artifact(rid, "T2", "agent-test-designer", "TestDesignReport", H.design_report(did, [tc]), [{"entity_type": "Artifact", "id": did}], {"type": "TestCaseDraft", "ids": [did]}, "test-design")
    assert engine.submit(rid, "T2", str(pd))[0] and engine.submit(rid, "T2", str(pr))[0]
    g2 = engine.evaluate_gate(rid, "T2"); assert g2["result"] == "PASS", g2
    _, pv = H.write_artifact(rid, "T3", "agent-test-validator", "TestValidationReport", H.validation_report(did, rmid, "PASS"), [{"entity_type": "Artifact", "id": did}], {"type": "TestCaseDraft", "ids": [did]}, "validation")
    assert engine.submit(rid, "T3", str(pv))[0] and engine.evaluate_gate(rid, "T3")["result"] == "PASS"
    F.approve(F.waiting(rid)); assert engine.load_run(rid)["status"] == "COMPLETED"
    return rid
def oa_tcs():
    return sorted(p.stem for p in store.glob("testcases/registry/TC-*.yaml") if store.load(store.tc_version_path(p.stem, 1))["functional_area"] == "OTH")
"""

def test_ac_10a_14_47_same_product_cross_area(tmp_path):
    """AC-10A-14（R1002-P3）、AC-10A-47（R1102-P1）：答案經 applicability 用到同 product（demo）、另一個 area（OTH）的 spec。
    A5 之後兩邊都重新納入最新 rev：impact 的掃描單位含 (demo, OTH)，OTH 中依賴舊答案的 TC 以 (b) 列出；
    缺它的結論 → 拒絕、CLR 不變；全部有結論 → APPLIED，landing 的掃描單位為兩個 area、候選含兩個 area 的 TC。"""
    root = mkroot(tmp_path)
    f = tmp_path / "oa.md"; f.write_text("# 營運區站台規格\n\n## 刪除\n\n營運區的站台刪除規則依總規格辦理。\n", encoding="utf-8")
    U.q(root, "spec", "import", f, "--spec-id", "SPEC-OA-001", "--version", "1.0", "--product", "demo", "--area", "OTH", "--by", "oscar", check=True)
    out = py(root, HDR + OA_FLOW + """
ra = P.full_ra(); cid = ra["cid"]                                                         # SA（demo/DEMO）以 rev 0 落地
bh = sources.basis_hash(sources.basis(OA, VER))
clr.applicability_add(cid, 0, "REQ-OTH-001", "site.child.delete", ["admin"], {}, f"{OA}@{VER}", "同一條刪除規則也適用營運區", "oscar", confirm_basis=bh, new_request=True)
rb = oa_run(cid, 1); old_oa = oa_tcs()                                                     # OTH 的 TC 依 rev 0
clr.answer(cid, "任何站台都不能刪除；表格已更正。", "pm", "requirement_clarified", "oscar", new_request=True)      # A5 → rev 1
clr.applicability_add(cid, 1, "REQ-OTH-001", "site.child.delete", ["admin"], {}, f"{OA}@{VER}", "rev 1 同樣適用營運區", "oscar", confirm_basis=bh, new_request=True)
rid2 = F.new_run(); g = F.analyze(rid2, [P.conflict_req(1, {"source": F.cref(cid, "任何站台都不能刪除"), "decided_at": "2026-10-07", "adopted_side_index": 1})])
assert g["result"] == "PASS", g
P.ra_p3_design(rid2, cid, g)
rb2 = oa_run(cid, 2); new_oa = [t for t in oa_tcs() if t not in old_oa]
targets = sorted(L.target_id(t) for t in L.resolve_targets(clr.load(cid)))
scan = L.impact(cid, ["刪除"], [], "oscar", new_request=True)
cands = [x["tc_id"] for x in scan["candidates"]]
T_OA = "SPEC-OA-001@1.0:REQ-OTH-001#Q01"; base = dict(landed_in=[rid2, rb2], targets=["SPEC-DEMO-001@1.0:REQ-DEMO-001#Q01", T_OA], keywords=["刪除"])
h0 = P.clr_sha(cid)
miss = P.apply_(cid, **base, tc_conclusions=[f"{t}=updated" for t in cands if t not in old_oa])
h1 = P.clr_sha(cid)
ok = P.apply_(cid, **base, tc_conclusions=[f"{t}=updated" for t in cands])
print(json.dumps({"old_oa": old_oa, "new_oa": new_oa, "targets": targets, "scan": scan, "miss": miss, "h": [h0, h1], "ok": ok, "c": clr.load(cid)}, default=str))""")
    assert out["targets"] == ["SPEC-DEMO-001@1.0:REQ-DEMO-001#Q01", "SPEC-OA-001@1.0:REQ-OTH-001#Q01"]
    s = out["scan"]; units = [{"product": "demo", "area": "DEMO"}, {"product": "demo", "area": "OTH"}]
    assert s["scan_units"] == units                                                               # AC-10A-14：掃描範圍包含同 product 的另一個 area
    reasons = {x["tc_id"]: x["reasons"] for x in s["candidates"]}
    assert out["old_oa"] and all("stale_decision_ref:REQ-OTH-001#Q01" in reasons[t] for t in out["old_oa"])   # 那裡依賴舊答案的 TC 被列出
    assert out["new_oa"] and all("stale_decision_ref:REQ-OTH-001#Q01" not in reasons[t] for t in out["new_oa"])
    assert "缺少 --tc-conclusion" in out["miss"]["error"] and out["old_oa"][0] in out["miss"]["error"] and out["h"][0] == out["h"][1]
    c = out["c"]; l = c["landings"][-1]                                                           # AC-10A-47：apply 正例，兩個 area 都掃描
    assert c["status"] == "APPLIED" and l["scan_units"] == units
    assert {t["area"] for t in l["targets_confirmed"]} == {"DEMO", "OTH"}
    assert set(out["old_oa"] + out["new_oa"]) <= {x["tc_id"] for x in l["candidates"]}


# ================================================================ AC-10A-15：已確認的第二個目標中，依賴舊答案的 TC 缺結論
def test_ac_10a_15_confirmed_second_target_stale_tc(tmp_path):
    """AC-10A-15（R1002-N1）：答案經 applicability 用到 REQ-DEMO-002；A5 之後重新分析，落地 run 含原題 REQ-DEMO-001，兩個目標都以 --target 確認；
    REQ-DEMO-002 中一張依賴舊答案（rev 0）的 TC 沒有結論 → 拒絕並列出該 TC，CLR 不變；補上結論 → APPLIED。"""
    root = mkroot(tmp_path)
    out = py(root, HDR + """
rid, cid, apr = P.ra_p1()
bh = sources.basis_hash(sources.basis(F.SPEC, F.VER))
clr.applicability_add(cid, 0, "REQ-DEMO-002", "site.child.delete", ["admin"], {}, "SPEC-DEMO-001@1.0", "答案同樣適用 REQ-DEMO-002", "oscar", confirm_basis=bh, new_request=True)
res = lambda: {"source": F.cref(cid, "任何站台都不能刪除"), "decided_at": "2026-10-07", "adopted_side_index": 1}
g = F.analyze(rid, [P.conflict_req(1, res()), P.conflict_req(2, res())]); assert g["result"] == "PASS", g
src0 = F.cref(cid, "任何站台都不能刪除")
P.ra_p3_design(rid, cid, g, extra_tcs=[F.tc(2, "REQ-DEMO-002", "REQ-002 刪除子站台被拒（依 rev 0）", techs=["negative"], types=["negative"],
                                            drefs=[{"requirement_id": "REQ-DEMO-002", "question_id": "Q01", "basis_ref": F.ident(src0)}], srcs=[src0])])
stale = [t for t in sorted(p.stem for p in store.glob("testcases/registry/TC-DEMO-*.yaml")) if "REQ-DEMO-002" in store.load(store.tc_version_path(t, 1))["requirement_ids"]]
clr.answer(cid, "任何站台都不能刪除；表格已更正。", "pm", "requirement_clarified", "oscar", new_request=True)          # A5 → rev 1
clr.applicability_add(cid, 1, "REQ-DEMO-002", "site.child.delete", ["admin"], {}, "SPEC-DEMO-001@1.0", "rev 1 同樣適用 REQ-DEMO-002", "oscar", confirm_basis=bh, new_request=True)
rid2 = F.new_run(); g2 = F.analyze(rid2, [P.conflict_req(1, res()), P.conflict_req(2, res())]); assert g2["result"] == "PASS", g2
src1 = F.cref(cid, "任何站台都不能刪除")                                                   # 落地 run：只為原題 REQ-DEMO-001 設計新 TC（REQ-DEMO-002 以理由不涵蓋）
d2 = F.design(rid2, [F.tc(1, "REQ-DEMO-001", "刪除子站台被拒（依 rev 1）", techs=["negative"], types=["negative"], srcs=[src1],
                          drefs=[{"requirement_id": "REQ-DEMO-001", "question_id": "Q01", "basis_ref": F.ident(src1)}])], uncovered=["REQ-DEMO-002"]); assert d2["result"] == "PASS", d2
v2 = F.validate(rid2, d2["did"], g2["rmid"]); assert v2["result"] == "PASS", v2
F.approve(F.waiting(rid2)); assert engine.load_run(rid2)["status"] == "COMPLETED"
scan = L.impact(cid, ["刪除"], [], "oscar", new_request=True)
cands = [x["tc_id"] for x in scan["candidates"]]
T1, T2 = "SPEC-DEMO-001@1.0:REQ-DEMO-001#Q01", "SPEC-DEMO-001@1.0:REQ-DEMO-002#Q01"
targets = sorted(L.target_id(t) for t in L.resolve_targets(clr.load(cid)))
h0 = P.clr_sha(cid)
miss = P.apply_(cid, landed_in=[rid2], targets=[T1, T2], keywords=["刪除"], tc_conclusions=[f"{t}=updated" for t in cands if t not in stale])
h1 = P.clr_sha(cid)
ok = P.apply_(cid, landed_in=[rid2], targets=[T1, T2], keywords=["刪除"], tc_conclusions=[f"{t}=updated" for t in cands])
print(json.dumps({"stale": stale, "scan": scan, "targets": targets, "miss": miss, "h": [h0, h1], "ok": ok, "c": clr.load(cid)}, default=str))""")
    assert out["targets"] == [T1, T2] and len(out["stale"]) == 1
    st = out["stale"][0]; reasons = {x["tc_id"]: x["reasons"] for x in out["scan"]["candidates"]}
    assert "stale_decision_ref:REQ-DEMO-002#Q01" in reasons[st]                                    # 先以掃描紀錄斷言該 TC 在候選中（§12.1 第 3 點）
    err = out["miss"]["error"]
    assert "缺少 --tc-conclusion" in err and f"['{st}']" in err.split("（重新掃描的候選")[0] and st in err.split("（重新掃描的候選")[1]
    assert out["h"][0] == out["h"][1]
    c = out["c"]; l = c["landings"][-1]
    assert c["status"] == "APPLIED" and sorted(L_["requirement_id"] for L_ in l["targets_confirmed"]) == ["REQ-DEMO-001", "REQ-DEMO-002"]
    assert {"tc_id": st, "conclusion": "updated"} in l["conclusions"]


# ================================================================ AC-A-B1-1：每個停點的 CLR 狀態
def test_ac_a_b1_1_every_stop_asserts_clr_state(tmp_path):
    """AC-A-B1-1（RA-P1 → P2 → P3）：逐停點斷言 CLR 狀態——開單 OPEN → answer ANSWERED → RESOLVE_AMBIGUITY 核准仍 ANSWERED（T1 重開）
    → G-SPEC（A4）INCORPORATED → G-DESIGN、G-TVAL、ACTIVATE 核准、run COMPLETED、impact 都仍 INCORPORATED → apply a6 APPLIED；history 中 APPLIED 只出現一次、在最後。"""
    root = mkroot(tmp_path)
    out = py(root, HDR + """
st = {}
rid = F.new_run(); g = F.analyze(rid, [P.conflict_req(1)]); assert g["result"] == "PASS", g
apr = F.waiting(rid); cid = F.clrs(requirement_id="REQ-DEMO-001")[0]["clarification_id"]
S = lambda k: st.__setitem__(k, clr.load(cid)["status"])
S("open")
clr.answer(cid, "任何站台都不能刪除，表格的「可操作」是舊文案。", "pm", "requirement_clarified", "oscar", new_request=True); S("answered")
F.approve(apr, resolutions=[{"requirement_id": "REQ-DEMO-001", "question_id": "Q01", "outcome": "select_interpretation", "source": F.cref(cid, "任何站台都不能刪除"),
                             "rationale": "依 PM 回答：任何站台都不能刪除"}]); S("approved")
run = engine.load_run(rid); st["reopen"] = [run["current_task_id"], run["tasks"][0]["iteration"]]
g = P.ra_p2(rid, cid); assert g["result"] == "PASS", g; S("gspec")
src = F.cref(cid, "任何站台都不能刪除")
d = F.design(rid, [F.tc(1, "REQ-DEMO-001", "刪除子站台被拒（依 PM 回答）", techs=["negative"], types=["negative"], srcs=[src],
                        drefs=[{"requirement_id": "REQ-DEMO-001", "question_id": "Q01", "basis_ref": F.ident(src)}])]); assert d["result"] == "PASS", d; S("gdesign")
v = F.validate(rid, d["did"], g["rmid"]); assert v["result"] == "PASS", v; S("gtval")
F.approve(F.waiting(rid)); st["run"] = engine.load_run(rid)["status"]; S("completed")
tcs = sorted(p.stem for p in store.glob("testcases/registry/TC-DEMO-*.yaml"))
L.impact(cid, ["刪除"], [], "oscar", new_request=True); S("impact")
P.apply_(cid, landed_in=[rid], targets=["SPEC-DEMO-001@1.0:REQ-DEMO-001#Q01"], keywords=["刪除"], tc_conclusions=[f"{t}=updated" for t in tcs]); S("applied")
print(json.dumps({"st": st, "hist": [h["to_status"] for h in clr.load(cid)["history"]]}, default=str))""")
    st = out["st"]
    assert (st["open"], st["answered"], st["approved"]) == ("OPEN", "ANSWERED", "ANSWERED") and st["reopen"] == ["T1", 1]
    assert [st[k] for k in ("gspec", "gdesign", "gtval", "completed", "impact")] == ["INCORPORATED"] * 5 and st["run"] == "COMPLETED"
    assert st["applied"] == "APPLIED"
    h = [x for x in out["hist"] if x in ("ANSWERED", "INCORPORATED", "APPLIED")]
    assert h.count("APPLIED") == 1 and h[-1] == "APPLIED" and h.index("ANSWERED") < h.index("INCORPORATED") < h.index("APPLIED")


# ================================================================ AC-A-B1-12（RA-P7）：a7 的背景候選要逐張給結論
def test_ac_10a_36_ra_p7_background_candidates(tmp_path):
    """AC-10A-36（RA-P7 = R1101-P1）：開 CLR（原題 REQ-DEMO-001）→ ask → answer no_change，沒有任何引用 → impact --keyword → apply a7 --scan；
    背景候選 (c) 與關鍵字候選 (d) 確實存在：缺結論 → 拒絕、CLR 不變；逐張給結論 → APPLIED，landing 的 path 為 a7、保存候選與結論。"""
    root = mkroot(tmp_path)
    out = py(root, HDR + """
ra = P.full_ra()
q = clr.new("demo", "DEMO", F.SPEC, F.VER, "刪除被拒時的提示文字要不要改？", "oscar", consulted=["SPEC-DEMO-001@1.0"], requirement_id="REQ-DEMO-001", new_request=True)
qid = q["clarification_id"]
clr.ask(qid, "pm", "oscar", sent_at="2026-10-01T09:00:00Z", channel="slack", new_request=True)
clr.answer(qid, "維持現狀，不需要改。", "pm", "no_change", "oscar", new_request=True)
s = L.impact(qid, ["刪除"], [], "oscar", new_request=True)
h0 = P.clr_sha(qid); miss = P.apply_(qid, path="a7", scan_id=s["scan_id"], tc_conclusions=[]); h1 = P.clr_sha(qid)
ok = P.apply_(qid, path="a7", scan_id=s["scan_id"], tc_conclusions=[f"{x['tc_id']}=not_affected" for x in s["candidates"]])
print(json.dumps({"tcs": ra["tcs"], "s": s, "miss": miss, "h": [h0, h1], "c": clr.load(qid)}, default=str))""")
    cands = {x["tc_id"]: x["reasons"] for x in out["s"]["candidates"]}
    assert set(out["tcs"]) <= set(cands) and all({"clr_requirement", "keyword:刪除"} <= set(cands[t]) for t in out["tcs"])
    assert "缺少 --tc-conclusion" in out["miss"]["error"] and out["tcs"][0] in out["miss"]["error"] and out["h"][0] == out["h"][1]
    c = out["c"]; l = c["landings"][-1]
    assert c["status"] == "APPLIED" and l["path"] == "a7" and l["scan_id"] == out["s"]["scan_id"] and l["reference_scan_sha256"]
    assert {x["tc_id"] for x in l["candidates"]} == set(cands) and all(x["conclusion"] == "not_affected" for x in l["conclusions"])


# ================================================================ AC-A-B1-9：effective_basis 的三種解析（正式流程）
def test_ac_a_b1_9_effective_basis_in_formal_flow(tmp_path):
    """AC-A-B1-9（附錄 A 6-21：R603-P1、N4、N5）以正式流程驗證：同一張 RESOLVE_AMBIGUITY 核准的兩個條目——
    條目 0 的 source 是 CLR rev 0、條目 1 的 source 為 null。重新分析時：
    (N5) REQ-DEMO-002 引用條目 0（requirement 不同）→ G-SPEC X15 FAIL、沒有 A4；
    (P1) REQ-DEMO-001 以 approval 包裝（條目 0）為 resolution → effective_basis 解析成 CLR rev 0 → A4 INCORPORATED；
    (N4) REQ-DEMO-002 以條目 1 為 resolution → effective_basis 是核准本身，不是任何 CLR（另一張 CLR 仍 ANSWERED）。"""
    root = mkroot(tmp_path)
    out = py(root, HDR + """
rid = F.new_run(); g = F.analyze(rid, [P.conflict_req(1), P.conflict_req(2, subject="site.child.rename")]); assert g["result"] == "PASS", g
apr = F.waiting(rid)
c1 = F.clrs(requirement_id="REQ-DEMO-001")[0]["clarification_id"]; c2 = F.clrs(requirement_id="REQ-DEMO-002")[0]["clarification_id"]
clr.answer(c1, "任何站台都不能刪除，表格的「可操作」是舊文案。", "pm", "requirement_clarified", "oscar", new_request=True)
clr.answer(c2, "交由核准者裁決。", "pm", "requirement_clarified", "oscar", new_request=True)
F.approve(apr, resolutions=[
    {"requirement_id": "REQ-DEMO-001", "question_id": "Q01", "outcome": "select_interpretation", "source": F.cref(c1, "任何站台都不能刪除"), "rationale": "依 PM 回答：任何站台都不能刪除"},
    {"requirement_id": "REQ-DEMO-002", "question_id": "Q01", "outcome": "select_interpretation", "source": None, "rationale": "核准者裁決：以刪除規則為準"}])
wrap0 = lambda: {"source": F.aref(apr, 0, "依 PM 回答"), "decided_at": "2026-10-07", "adopted_side_index": 1}
wrap1 = {"source": F.aref(apr, 1, "核准者裁決"), "decided_at": "2026-10-07", "adopted_side_index": 1}
bad = F.analyze(rid, [P.conflict_req(1, wrap0()), P.conflict_req(2, wrap0(), subject="site.child.rename")])
s_bad = [clr.load(c1)["status"], clr.load(c2)["status"]]
good = F.analyze(rid, [P.conflict_req(1, wrap0()), P.conflict_req(2, wrap1, subject="site.child.rename")])
rev = rm.requirements_of(F.current_rev())
eb = {r: list(sources.effective_basis(rev[r]["decision_points"][0]["resolution"]["source"], at=(r, "Q01"))) for r in ("REQ-DEMO-001", "REQ-DEMO-002")}
c1_ = clr.load(c1)
print(json.dumps({"bad": [bad["result"], bad.get("issues")], "s_bad": s_bad, "good": good["result"], "eb": eb, "c1": [c1_["status"], c1_["landings"]],
                  "c2": clr.load(c2)["status"], "apr": apr, "c1id": c1, "r0sha": c1_["answer_revisions"][0]["sha256"]}, default=str))""")
    assert out["bad"][0] == "FAIL" and any(i.startswith("X15：REQ-DEMO-002/Q01") and "不符" in i for i in out["bad"][1]), out["bad"]   # N5
    assert out["s_bad"] == ["ANSWERED", "ANSWERED"]                                              # FAIL 沒有持久化 revision、沒有 A4
    assert out["good"] == "PASS"
    assert out["eb"]["REQ-DEMO-001"] == ["clarification", out["c1id"], 0, out["r0sha"]]           # P1：approval 包裝解析成條目內的 CLR rev
    assert out["c1"][0] == "INCORPORATED" and out["c1"][1][-1]["type"] == "incorporated"         # 包裝展開後觸發 A4（附錄 A 6-22）
    assert out["eb"]["REQ-DEMO-002"][:3] == ["approval", out["apr"], 1]                           # N4：source 為 null → 核准本身
    assert out["c2"] == "ANSWERED"


# ================================================================ AC-A-B1-13：核准決議表 4 列（ACTIVATE_TESTCASE）
ROW_FLOW = """
def to_activate():
    '''RA-P1、P2 之後設計兩張 TC（都在 REQ-DEMO-001、依 CLR 最新 rev）→ Validator PASS → 等 ACTIVATE_TESTCASE。'''
    rid, cid, apr = P.ra_p1(); g = P.ra_p2(rid, cid); assert g["result"] == "PASS", g
    src = F.cref(cid, "任何站台都不能刪除"); dref = [{"requirement_id": "REQ-DEMO-001", "question_id": "Q01", "basis_ref": F.ident(src)}]
    d = F.design(rid, [F.tc(1, "REQ-DEMO-001", "刪除子站台被拒", techs=["negative"], types=["negative"], drefs=dref, srcs=[src]),
                       F.tc(2, "REQ-DEMO-001", "刪除總站台被拒", techs=["negative"], types=["negative"], drefs=dref, srcs=[src])]); assert d["result"] == "PASS", d
    v = F.validate(rid, d["did"], g["rmid"]); assert v["result"] == "PASS", v
    a = F.waiting(rid); items = [i["id"] for i in store.load(f"approvals/{a}.yaml")["batch_items"]]
    return rid, cid, a, items
def status_of(tcs):
    return {t: [store.load(store.tc_pointer_path(t))["status"], store.load(store.tc_version_path(t, 1))["status"]] for t in tcs}
"""

ROWS = {
    "1": ('"approve"', "None"),
    "2": ('"approve"', '[{"id": items[1], "decision": "reject", "rationale": "與另一張重複"}]'),
    "3": ('"reject"', '[{"id": items[0], "decision": "approve", "rationale": "只採用這一張"}]'),
    "4a": ('"reject"', "None"),
    "4b": ('"reject"', '[{"id": i, "decision": "reject", "rationale": "全部重做"} for i in items]'),
}

@pytest.mark.parametrize("row", list(ROWS))
def test_ac_a_b1_13_approval_table_activate(row, tmp_path):
    """AC-A-B1-13（第 1 章 §5 核准決議表，ACTIVATE_TESTCASE）：
    第 1 列 approve → 全部啟用、run COMPLETED；第 2 列 approve＋部分 reject → 被 reject 的回 DRAFT、其餘啟用、COMPLETED；
    第 3 列 reject＋至少一項 approve → 那些項目啟用、推進（不回 Designer）、COMPLETED；第 4 列 reject 沒有 per_item（4a）或 per_item 全部 reject（4b）
    → 沒有啟用、退回 Test Designer（iteration 加 1）、run 不會 COMPLETED。需求 A 的後續：核准與 run 完成都不改變 CLR 狀態（hash 不變）；
    第 1～3 列的 run 可作為 --landed-in（apply 成功），第 4 列不能（拒絕、CLR 不變）。"""
    dec, per = ROWS[row]
    root = mkroot(tmp_path)
    out = py(root, HDR + ROW_FLOW + f"""
rid, cid, a, items = to_activate()
h0 = P.clr_sha(cid); s0 = clr.load(cid)["status"]
engine.approve(a, {dec}, F.BY, rationale="決議表第 {row} 列", per_item={per}, new_request=True)
h1 = P.clr_sha(cid); run = engine.load_run(rid); t2 = next(t for t in run["tasks"] if t["task_id"] == "T2")
res = {{"items": items, "tc": status_of(items), "run": run["status"], "cur": run.get("current_task_id"), "t2": [t2["status"], t2["iteration"]], "s0": s0, "h": [h0, h1]}}
active = [t for t in items if res["tc"][t][0] == "ACTIVE"]
cands = [x["tc_id"] for x in L.scan_candidates(clr.load(cid), [], ["刪除"], [{{"product": "demo", "area": "DEMO"}}], "a6")]
res["apply"] = P.apply_(cid, landed_in=[rid], targets=["SPEC-DEMO-001@1.0:REQ-DEMO-001#Q01"], keywords=["刪除"], tc_conclusions=[f"{{t}}=updated" for t in active])
res["h2"] = P.clr_sha(cid); res["s2"] = clr.load(cid)["status"]
print(json.dumps(res, default=str))""")
    i0, i1 = out["items"]; tc = out["tc"]
    assert out["s0"] == "INCORPORATED" and out["h"][0] == out["h"][1]                              # 核准（與 run 完成）不改變 CLR
    expect = {"1": (["ACTIVE", "ACTIVE"], "COMPLETED"), "2": (["ACTIVE", "DRAFT"], "COMPLETED"), "3": (["ACTIVE", "DRAFT"], "COMPLETED"),
              "4a": (["DRAFT", "DRAFT"], "RUNNING"), "4b": (["DRAFT", "DRAFT"], "RUNNING")}[row]
    assert [tc[i0][1], tc[i1][1]] == expect[0] and out["run"] == expect[1], out
    if row in ("1", "2", "3"):
        assert out["t2"] == ["DONE", 0]                                                          # 推進，不回 Designer（第 3 列：ok = bool(activated)）
        assert out["s2"] == "APPLIED", out["apply"]                                              # COMPLETED 的 run 可作為 landed-in
    else:
        assert out["cur"] == "T2" and out["t2"] == ["READY", 1]                                   # 退回 Test Designer，iteration 加 1
        assert "不是 COMPLETED" in out["apply"]["error"] and out["h2"] == out["h"][0] and out["s2"] == "INCORPORATED"


# ================================================================ AC-A-B1-13：第 3 列以 APPLY_CHANGE 再測一次
CHANGE_FLOW = r"""
import json as _json
from tests import helpers as H
from tools.qaos import rm
from tools.qaos.cli import main as cli
BY = "oscar@example.com"; SPEC = "SPEC-AUTH-001"
def tcs_active():
    out = []
    for p in sorted(store.glob("testcases/registry/TC-*.yaml")):
        d = store.load(p)
        if d["status"] == "ACTIVE": out.append((d["testcase_id"], d["active_version"], store.load(store.tc_version_path(d["testcase_id"], d["active_version"]))))
    return out
def analyze(rid, task, ver, rm_):
    refs_ = [{"entity_type": "SpecVersion", "id": SPEC, "version": ver}]
    e = next(x for x in store.load(store.spec_dir(SPEC) / "spec.yaml")["versions"] if str(x["spec_version"]) == ver)
    sa = {"spec_id": SPEC, "spec_version": ver, "content_hash": e["content_hash"], "summary": "s", "scope": {"in_scope": ["x"], "out_of_scope": []},
          "requirement_ids": [r["requirement_id"] for r in rm_["requirements"]], "ambiguities": [], "constraints": [], "edge_case_candidates": [], "open_questions": []}
    _, p1 = H.write_artifact(rid, task, "agent-spec-analyst", "SpecAnalysis", sa, refs_, {"type": "SpecVersion", "ids": [f"{SPEC}@{ver}"]}, "spec-analysis")
    rmid, p2 = H.write_artifact(rid, task, "agent-spec-analyst", "RequirementModel", rm_, refs_, {"type": "SpecVersion", "ids": [f"{SPEC}@{ver}"]}, "requirements")
    assert engine.submit(rid, task, str(p1))[0] and engine.submit(rid, task, str(p2))[0]
    g = engine.evaluate_gate(rid, task); assert g["result"] == "PASS", g
    return rmid
# v1.0：spec-to-testcase 建立 5 張 ACTIVE TC
cli(["spec", "import", "tests/fixtures/SPEC-AUTH-001-v1.0.md", "--spec-id", SPEC, "--version", "1.0", "--product", "demo", "--area", "AUTH", "--by", BY])
rid1 = engine.new_run("spec-to-testcase", {"spec_id": SPEC, "spec_version": "1.0"}, BY, new_request=True)["run_id"]
rmid1 = analyze(rid1, "T1", "1.0", H.requirement_model())
tcs, _ = H.draft_set(); refs2 = [{"entity_type": "Requirement", "id": r} for r in ["REQ-AUTH-001", "REQ-AUTH-002", "REQ-AUTH-003", "REQ-AUTH-004"]]
did, pd = H.write_artifact(rid1, "T2", "agent-test-designer", "TestCaseDraft", {"mode": "spec", "spec_id": SPEC, "spec_version": "1.0", "testcases": tcs}, refs2, {"type": "RequirementModel", "ids": [rmid1]}, "test-design")
_, pr = H.write_artifact(rid1, "T2", "agent-test-designer", "TestDesignReport", H.design_report(did, tcs), [{"entity_type": "Artifact", "id": did}], {"type": "TestCaseDraft", "ids": [did]}, "test-design")
assert engine.submit(rid1, "T2", str(pd))[0] and engine.submit(rid1, "T2", str(pr))[0] and engine.evaluate_gate(rid1, "T2")["result"] == "PASS"
_, pv = H.write_artifact(rid1, "T3", "agent-test-validator", "TestValidationReport", H.validation_report(did, rmid1, "PASS"), [{"entity_type": "Artifact", "id": did}, {"entity_type": "Artifact", "id": rmid1}], {"type": "TestCaseDraft", "ids": [did]}, "validation")
assert engine.submit(rid1, "T3", str(pv))[0] and engine.evaluate_gate(rid1, "T3")["result"] == "PASS"
engine.approve(engine.load_run(rid1)["waiting_on_approval_id"], "approve", BY, new_request=True); assert engine.load_run(rid1)["status"] == "COMPLETED"
# v1.1：spec-change-impact（REQ-AUTH-001 changed，兩張 TC affected）
cli(["spec", "import", "tests/fixtures/SPEC-AUTH-001-v1.1.md", "--spec-id", SPEC, "--version", "1.1", "--product", "demo", "--area", "AUTH", "--change-summary", "密碼最小長度 8 → 12", "--by", BY])
rid = engine.new_run("spec-change-impact", {"spec_id": SPEC, "from_version": "1.0", "to_version": "1.1"}, BY, new_request=True)["run_id"]
rmid = analyze(rid, "T0", "1.1", H.requirement_model("1.1", "12"))
active = tcs_active(); affected = [t for t in active if "REQ-AUTH-001" in t[2]["requirement_ids"]]; unaffected = [t for t in active if t not in affected]
cir = {"change_impact_id": "CI-SPEC-AUTH-001-1.0-1.1", "spec_id": SPEC, "from_version": "1.0", "to_version": "1.1",
       "requirement_diff": [{"requirement_id": "REQ-AUTH-001", "change": "changed", "detail": "8 → 12"}] + [{"requirement_id": r, "change": "unchanged"} for r in ["REQ-AUTH-002", "REQ-AUTH-003", "REQ-AUTH-004"]],
       "testcase_impact": [{"testcase_id": t[0], "active_version": t[1], "impact": "affected" if t in affected else "unaffected", "reason": "邊界值變更" if t in affected else "-",
                            "affected_requirement_ids": ["REQ-AUTH-001"] if t in affected else []} for t in active],
       "summary": {"requirements_changed": 1, "requirements_added": 0, "requirements_removed": 0, "testcases_affected": len(affected), "testcases_obsolete": 0, "testcases_unaffected": len(unaffected)},
       "completeness": {"all_active_requirements_judged": True, "all_referencing_testcases_judged": True}}
r = engine.load_run(rid); groups = {}
for t in active: groups.setdefault(_json.dumps(rm.tc_pin(t[0], t[1]), sort_keys=True), []).append(t[0])
pin_groups = [{"from_pin": _json.loads(k), "testcase_ids": v, "requirement_diff": cir["requirement_diff"]} for k, v in groups.items()]
gidx = {t: k for k, g in enumerate(pin_groups) for t in g["testcase_ids"]}
cir.update(from_rm_revision=r["from_requirement_model_revision"], to_rm_revision=r["requirement_model_revision"], pin_groups=pin_groups)
for ti in cir["testcase_impact"]: ti["pin_group_index"] = gidx[ti["testcase_id"]]
refs_ = [{"entity_type": "SpecVersion", "id": SPEC, "version": "1.1"}]
cid, p = H.write_artifact(rid, "T1", "agent-change-impact-analyst", "ChangeImpactReport", cir, refs_ + [{"entity_type": "TestCaseVersion", "id": t[0], "version": t[1]} for t in active], {"type": "SpecVersion", "ids": []}, "change-impact")
assert engine.submit(rid, "T1", str(p))[0] and engine.evaluate_gate(rid, "T1")["result"] == "PASS"
tcs2, _ = H.draft_set(12, prefix="01BX5ZZKBKACTAV9WEVGEMMVR"); new = []
for t, d in zip(affected, tcs2[:2]):
    d = dict(d, spec_version="1.1", source="change_workflow", supersedes_testcase={"testcase_id": t[0], "version": t[1]}); d["expected_result_spec_reference"]["spec_version"] = "1.1"; new.append(d)
refs3 = [{"entity_type": "Requirement", "id": "REQ-AUTH-001"}, {"entity_type": "Artifact", "id": cid}]
did, pd = H.write_artifact(rid, "T2", "agent-test-designer", "TestCaseDraft", {"mode": "change", "spec_id": SPEC, "spec_version": "1.1", "change_impact_id": cir["change_impact_id"], "testcases": new}, refs3, {"type": "ChangeImpactReport", "ids": [cid]}, "test-design")
rep = H.design_report(did, new); rep["mode"] = "change"
_, pr = H.write_artifact(rid, "T2", "agent-test-designer", "TestDesignReport", rep, [{"entity_type": "Artifact", "id": did}], {"type": "TestCaseDraft", "ids": [did]}, "test-design")
assert engine.submit(rid, "T2", str(pd))[0] and engine.submit(rid, "T2", str(pr))[0] and engine.evaluate_gate(rid, "T2")["result"] == "PASS"
_, p = H.write_artifact(rid, "T3", "agent-test-validator", "TestValidationReport", H.validation_report(did, rmid, "PASS", spec_version="1.1"), [{"entity_type": "Artifact", "id": did}], {"type": "TestCaseDraft", "ids": [did]}, "validation")
assert engine.submit(rid, "T3", str(p))[0] and engine.evaluate_gate(rid, "T3")["result"] == "PASS"
vcr = {"change_impact_id": cir["change_impact_id"], "comparisons": [{"testcase_id": t[0], "old_version": 1, "new_draft_id": d["draft_id"], "verdict": "changed",
       "field_diffs": [{"field": "steps[0]", "old": "8", "new": "12"}], "impacted_requirement_ids": ["REQ-AUTH-001"]} for t, d in zip(affected, new)],
       "retire_recommendations": [{"testcase_id": unaffected[0][0], "reason": "與另一張重複"}], "summary": {"unchanged": 0, "changed": 2, "added": 0, "removed": 0}}
_, p = H.write_artifact(rid, "T4", "agent-change-impact-analyst", "VersionComparisonReport", vcr, [{"entity_type": "Artifact", "id": cid}], {"type": "x", "ids": []}, "change-impact")
assert engine.submit(rid, "T4", str(p))[0]; g4 = engine.evaluate_gate(rid, "T4"); assert g4["result"] == "PASS", g4
apr = store.load(f"approvals/{engine.load_run(rid)['waiting_on_approval_id']}.yaml"); assert apr["type"] == "APPLY_CHANGE"
"""

def test_ac_a_b1_13_row3_apply_change(tmp_path):
    """AC-A-B1-13 第 3 列（APPLY_CHANGE）：spec-change-impact 的 APPLY_CHANGE 整體 reject、per_item 只 approve 一張 →
    該張新版本啟用（舊版 SUPERSEDED）、另一張新版本回 DRAFT（舊版仍 ACTIVE）；ok = bool(activated) → 推進、run COMPLETED（不回 Designer）；
    change_impact 為 TEST_UPDATE_REQUIRED、不執行 retire 建議（已知不一致，本需求不修改）。"""
    root = U.mkroot()
    out = py(root, CHANGE_FLOW + """
a0, a1 = affected[0][0], affected[1][0]
engine.approve(apr["approval_id"], "reject", BY, rationale="只採用其中一張", per_item=[{"id": a0, "decision": "approve", "rationale": "這張改對了"}], new_request=True)
run = engine.load_run(rid); t2 = next(t for t in run["tasks"] if t["task_id"] == "T2")
st = lambda t: [store.load(store.tc_pointer_path(t))["active_version"], store.load(store.tc_version_path(t, 1))["status"], store.load(store.tc_version_path(t, 2))["status"]]
print(json.dumps({"a0": st(a0), "a1": st(a1), "run": run["status"], "t2": [t2["status"], t2["iteration"]], "ci": store.load(f"runs/{rid}/entities/change-impact.yaml")["status"],
                  "retire": store.load(store.tc_pointer_path(unaffected[0][0]))["status"]}, default=str))""")
    assert out["a0"] == [2, "SUPERSEDED", "ACTIVE"] and out["a1"] == [1, "ACTIVE", "DRAFT"]
    assert out["run"] == "COMPLETED" and out["t2"] == ["DONE", 0]
    assert out["ci"] == "TEST_UPDATE_REQUIRED" and out["retire"] == "ACTIVE"


# ================================================================ AC-A-B1-6：S1（Q）→ S3 全程只用第一批的指令
S1_DOCS = [("SPEC-S1A-001", "A"), ("SPEC-S1B-001", "B"), ("SPEC-S1C-001", "C"), ("SPEC-S1D-001", "D"), ("SPEC-S1E-001", "E"), ("SPEC-S1F-001", "F")]

def test_ac_a_b1_6_s1_q_to_s3_first_batch_commands_only(tmp_path):
    """AC-A-B1-6（第 6 章 §11 S1（Q）→ S2 → S3）：部署前以舊 importer（需求 A 之前的程式）匯入 7 份文件、留下 legacy CLR（已回答、未回答各一）；
    移轉後全程只用第一批的 CLI：S1 `spec metadata upgrade` 補來源 → S2 `spec reference add` → S3 `clarification ask`（補記 --sent-at --channel）、
    `answer --answer-source`、`clarification metadata upgrade`、`applicability add --confirm-basis`、`addenda add`。每一步成功，答案、狀態依規則保留。"""
    from tests import p3_legacy as LG
    root, info = LG.legacy_root()
    old = LG.old_checkout(); env = {**os.environ, "QAOS_ROOT": str(root), "PYTHONDONTWRITEBYTECODE": "1"}
    files = {"SPEC-AUTH-001": U.REPO / "tests/fixtures/SPEC-AUTH-001-v1.0.md"}
    for sid, x in S1_DOCS:                                                                        # S1（Q）前半：舊 importer（部署前）
        f = tmp_path / f"{sid}.md"; f.write_text(f"# 回覆包文件 {x}\n\n## 內容\n\n文件 {x} 的規則。\n", encoding="utf-8"); files[sid] = f
        r = subprocess.run([sys.executable, "-m", "tools.qaos", "spec", "import", str(f), "--spec-id", sid, "--version", "1.0", "--product", "demo", "--area", "AUTH", "--by", "oscar"],
                           cwd=old, env=env, capture_output=True, text=True, timeout=120)
        assert r.returncode == 0, r.stderr
    LG.migrate(root, "--acknowledge-idle", info["running"]); U.q(root, "maintenance", "end", "--by", "m", check=True)
    ok = lambda *a: U.q(root, *a, check=True)
    cid, cid2 = info["clr"], info["open_clr"]
    before = U.load(root, f"clarifications/demo/AUTH/{cid}.yaml")
    # S1（Q）後半：metadata upgrade 補 source（舊 importer 沒有 source）
    for sid, f in files.items():
        e0 = next(e for e in U.load(root, f"specs/demo/AUTH/{sid}/spec.yaml")["versions"] if str(e["spec_version"]) == "1.0")
        assert "source" not in e0
        ok("spec", "metadata", "upgrade", f"{sid}@1.0", "--original-file", f, "--external-filename", f.name, "--external-version", "v01", "--reason", "S1（Q）：補來源", "--by", "oscar")
        e1 = next(e for e in U.load(root, f"specs/demo/AUTH/{sid}/spec.yaml")["versions"] if str(e["spec_version"]) == "1.0")
        assert e1["source"]["external_filename"] == f.name and e1["content_hash"] == e0["content_hash"] and len(e1["metadata_history"]) == 1
    # S2：引用表
    ok("spec", "reference", "add", "SPEC-AUTH-001@1.0", "--ref", "SPEC-S1A-001@1.0", "--role", "normative", "--by", "oscar")
    ok("spec", "reference", "add", "SPEC-AUTH-001@1.0", "--ref", "SPEC-S1B-001@1.0", "--role", "informative", "--by", "oscar")
    # S3：已回答的 legacy CLR（移轉建立 rev 0）——metadata upgrade、applicability（確認 basis）、evidence_addenda
    ok("clarification", "metadata", "upgrade", cid, "--kind", "spec_question", "--question-id", "Q01", "--subject", "password.min_length", "--role-scope", "*", "--params", "{}",
       "--reason", "S3：補答案範圍", "--by", "oscar")
    ap = ["clarification", "applicability", "add", cid, "--answer-rev", "0", "--requirement", "REQ-AUTH-001", "--subject", "password.min_length", "--role-scope", "*",
          "--params", "{}", "--target", "SPEC-AUTH-001@1.0", "--rationale", "S3：人核對宣告後的 basis，答案仍適用", "--by", "oscar"]
    r = U.q(root, *ap); assert r.returncode != 0 and "未寫入" in r.stderr                          # CLI 先顯示本次 basis_hash
    bh = re.search(r"basis_hash = ([0-9a-f]{64})", r.stderr).group(1)
    ok(*ap, "--confirm-basis", bh)
    doc = {"type": "document", "file_name": "PM回覆_v01.pdf", "sha256": "b" * 64, "location": "第 1 段"}
    ok("clarification", "addenda", "add", cid, "--source", json.dumps(doc), "--note", "PM 重申同一決議", "--by", "oscar")
    # S3：未回答的 legacy CLR——ask 補記、answer（附 answer_source）、metadata upgrade
    ok("clarification", "ask", cid2, "--to", "pm", "--sent-at", "2026-09-20T10:00:00Z", "--channel", "slack", "--by", "oscar")
    msg = {"type": "message", "channel": "slack", "sent_by": "pm", "at": "2026-09-21T09:00:00Z"}
    ok("clarification", "answer", cid2, "--answer", "連續 5 次失敗鎖定 15 分鐘。", "--answered-by", "pm", "--resolution", "requirement_clarified", "--answer-source", json.dumps(msg), "--by", "oscar")
    ok("clarification", "metadata", "upgrade", cid2, "--kind", "spec_question", "--question-id", "Q01", "--subject", "login.lockout", "--role-scope", "*", "--params", "{}",
       "--reason", "S3：補答案範圍", "--by", "oscar")
    c = U.load(root, f"clarifications/demo/AUTH/{cid}.yaml"); c2 = U.load(root, f"clarifications/demo/AUTH/{cid2}.yaml")
    assert c["status"] == before["status"] == "ANSWERED" and c["answer_revisions"] == before["answer_revisions"]       # 答案與狀態不變
    assert (c["subject"], c["role_scope"], c["params"]) == ("password.min_length", ["*"], {})
    assert c["applicability"][0]["basis_hash"] == bh and c["evidence_addenda"][0]["source"] == doc
    assert c2["status"] == "ANSWERED" and c2["sent_at"] == "2026-09-20T10:00:00Z" and c2["channel"] == "slack" and c2["asked_at"]
    assert c2["answer_revisions"][0]["answer_sources"] == [msg] and c2["subject"] == "login.lockout"
    x16 = U.py(root, f"""
import json
from tools.qaos import sources, clarification as clr
r = clr.load("{cid}")["answer_revisions"][0]
ref = {{"type": "clarification", "clarification_id": "{cid}", "answer_rev": 0, "answer_sha256": r["sha256"], "quote": "8"}}
sc = {{"spec_id": "SPEC-AUTH-001", "requirement_id": "REQ-AUTH-001", "subject": "password.min_length", "role_scope": ["*"], "params": {{}}}}
print(json.dumps(sources.x16(ref, sc, sources.basis_hash(sources.basis("SPEC-AUTH-001", "1.0")))))""").stdout.strip().splitlines()[-1]
    assert json.loads(x16) == []                                                                   # S3 的結果：legacy 答案經人確認後可作為依據
    for p in (f"clarifications/demo/AUTH/{cid}.yaml", f"clarifications/demo/AUTH/{cid2}.yaml"):
        errs = U.py(root, f"import json\nfrom tools.qaos import schema, store\nprint(json.dumps(schema.errors(store.load('{p}'), 'spec/clarification.schema.json')))").stdout.strip()
        assert json.loads(errs) == [], (p, errs)


# ================================================================ AC-A-B1-10：AC-07-44（migrate --cancel-run 的 legacy 凍結與第一次 render）
def test_ac_07_44_cancel_run_in_migrate_freezes_legacy(tmp_path):
    """AC-07-44（AC-A-B1-10）：`migrate --cancel-run X` → 兩個 audit.legacy.log 都逐位元等於移轉前的 audit.log；
    第一次 render 的結果以 legacy 原位元組開頭，後面接 cancel 事件與移轉事件（同 AC-07-43）；移轉標記記錄 cancel_run 與 frozen。"""
    from tests.test_p1_audit import legacy_root
    root, run_id, run_legacy, glob_legacy = legacy_root()
    U.q(root, "maintenance", "start", "--by", "m", check=True)
    U.q(root, "migrate", "--by", "m", "--cancel-run", run_id, check=True)
    U.q(root, "maintenance", "end", "--by", "m", check=True)
    R = pathlib.Path(root)
    assert (R / f"runs/{run_id}/audit.legacy.log").read_bytes() == run_legacy and (R / "runs/_audit.legacy.log").read_bytes() == glob_legacy
    run_log = (R / f"runs/{run_id}/audit.log").read_bytes(); g = (R / "runs/_audit.log").read_bytes()
    assert run_log.startswith(run_legacy) and b"CANCEL_RUN" in run_log[len(run_legacy):]
    tail = g[len(glob_legacy):].decode()
    assert g.startswith(glob_legacy) and "CANCEL_RUN" in tail and "MIGRATE" in tail and tail.index("CANCEL_RUN") < tail.rindex("MIGRATE")
    assert U.load(root, f"runs/{run_id}/run.yaml")["status"] == "CANCELLED"
    mk = U.load(root, "artifacts/requirements/_migration.yaml")
    assert mk["mode_per_run"] == {run_id: "cancel_run"} and mk["logs"][f"runs/{run_id}/audit.log"]["legacy"] == "frozen"
