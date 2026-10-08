"""P5：跨 product 的採用目標（需求 A 第 6 章 §5.4、§5.10；R1102：AC-10A-47～51、64～66；AC-A-B1-17）。
以正式流程建立第二個 product 的 spec（product other、area 名稱同樣是 DEMO，同時涵蓋「不同 product、相同 area 名稱不合併」AC-10A-51），
CLR 經人建立的 applicability 被 SB 的分析採用。執行順序依規格：P2 → P3a → N2 → N1 → N3 → P5，每個反例之後斷言 CLR 檔 hash 不變。"""
import json
from tests import p1_util as U
from tests.test_p4_dispatch import mkroot, py

SB_TEXT = "# 另一產品的站台規格\n\n## 刪除\n\n站台刪除規則依總規格辦理。\n"
SB_FLOW = """
from tests import p5_flow as P
from tests import helpers as H
from tools.qaos import clr_lifecycle as L, spec_ops
SB, VER = "SPEC-SB-001", "1.0"
def sb_pin(): return spec_ops.verify_pin(SB, VER)
def sb_run(cid):
    '''RB：對 SB 做 spec-to-testcase，REQ-DEMO-020/Q01 以 CLR-1 rev 0 為依據（defined_by_decision，經 applicability 通過 X16）→ 設計 → 驗證 → ACTIVATE。'''
    src = F.cref(cid, "任何站台都不能刪除")
    dp = F.dp("Q01", "defined_by_decision", "none", subject="site.child.delete", role=["admin"], known=[src],
              coverage={"references_status": "undeclared", "consulted": [sb_pin()], "unconsulted_normative": [], "missing_sources": [], "waivers": []})
    req = {"requirement_id": "REQ-DEMO-020", "version": 1, "spec_id": SB, "spec_version": VER, "type": "functional", "title": "另一產品的站台刪除", "statement": "另一產品的站台刪除規則",
           "acceptance_criteria": [{"ac_id": "AC-SB-001", "given": "已登入", "when": "刪除子站台", "then": "依規則"}],
           "spec_reference": {"spec_id": SB, "spec_version": VER, "location": "§刪除", "quote": "站台刪除規則依總規格辦理。"}, "ambiguity": None, "risk": "medium", "status": "DRAFT", "history": [],
           "decision_points": [dp]}
    rid = engine.new_run("spec-to-testcase", {"spec_id": SB, "spec_version": VER}, F.BY, new_request=True)["run_id"]
    refs_ = [{"entity_type": "SpecVersion", "id": SB, "version": VER}]; s_ = {"type": "SpecVersion", "ids": [f"{SB}@{VER}"]}
    sa = {"spec_id": SB, "spec_version": VER, "content_hash": sb_pin()["content_hash"], "summary": "s", "scope": {"in_scope": ["x"], "out_of_scope": []},
          "requirement_ids": ["REQ-DEMO-020"], "ambiguities": [], "constraints": [], "edge_case_candidates": [], "open_questions": []}
    _, p1 = H.write_artifact(rid, "T1", "agent-spec-analyst", "SpecAnalysis", sa, refs_, s_, "spec-analysis")
    rmid, p2 = H.write_artifact(rid, "T1", "agent-spec-analyst", "RequirementModel", {"spec_id": SB, "spec_version": VER, "requirements": [req],
                                "traceability": [{"requirement_id": "REQ-DEMO-020", "spec_reference": req["spec_reference"]}]}, refs_, s_, "requirements")
    assert engine.submit(rid, "T1", str(p1))[0] and engine.submit(rid, "T1", str(p2))[0]
    g = engine.evaluate_gate(rid, "T1"); assert g["result"] == "PASS", g
    tc = F.tc(1, "REQ-DEMO-020", "另一產品刪除子站台被拒", techs=["negative"], types=["negative"], drefs=[{"requirement_id": "REQ-DEMO-020", "question_id": "Q01", "basis_ref": F.ident(src)}], srcs=[src])
    tc.update({"product": "other", "spec_id": SB, "acceptance_criteria_ids": ["AC-SB-001"], "expected_result_spec_reference": {"spec_id": SB, "spec_version": VER, "location": "§刪除"},
               "draft_id": "TC-DRAFT-01ARZ3NDEKTSV4RRFFQ69GSB01"})
    did, pd = H.write_artifact(rid, "T2", "agent-test-designer", "TestCaseDraft", {"mode": "spec", "spec_id": SB, "spec_version": VER, "testcases": [tc]},
                               [{"entity_type": "Requirement", "id": "REQ-DEMO-020"}], {"type": "RequirementModel", "ids": []}, "test-design")
    _, pr = H.write_artifact(rid, "T2", "agent-test-designer", "TestDesignReport", H.design_report(did, [tc]), [{"entity_type": "Artifact", "id": did}], {"type": "TestCaseDraft", "ids": [did]}, "test-design")
    assert engine.submit(rid, "T2", str(pd))[0] and engine.submit(rid, "T2", str(pr))[0]
    g2 = engine.evaluate_gate(rid, "T2"); assert g2["result"] == "PASS", g2
    _, pv = H.write_artifact(rid, "T3", "agent-test-validator", "TestValidationReport", H.validation_report(did, rmid, "PASS"), [{"entity_type": "Artifact", "id": did}], {"type": "TestCaseDraft", "ids": [did]}, "validation")
    assert engine.submit(rid, "T3", str(pv))[0] and engine.evaluate_gate(rid, "T3")["result"] == "PASS"
    F.approve(F.waiting(rid)); assert engine.load_run(rid)["status"] == "COMPLETED"
    return rid
"""

def test_r1102_cross_product(tmp_path):
    root = mkroot(tmp_path)
    f = tmp_path / "sb.md"; f.write_text(SB_TEXT, encoding="utf-8")
    U.q(root, "spec", "import", f, "--spec-id", "SPEC-SB-001", "--version", "1.0", "--product", "other", "--area", "DEMO", "--by", "oscar", check=True)
    out = py(root, SB_FLOW + """
ra = P.full_ra(); cid = ra["cid"]                                                        # 前置 1～3：product A 的落地 RA
bh = sources.basis_hash(sources.basis(SB, VER))
clr.applicability_add(cid, 0, "REQ-DEMO-020", "site.child.delete", ["admin"], {}, f"{SB}@{VER}", "同一條刪除規則也適用另一產品", "oscar", confirm_basis=bh, new_request=True)   # 前置 4
rb = sb_run(cid)
landings = [l["type"] for l in clr.load(cid)["landings"]]
SA_T, SB_T = "SPEC-DEMO-001@1.0:REQ-DEMO-001#Q01", "SPEC-SB-001@1.0:REQ-DEMO-020#Q01"
targets = [(t["product"], L.target_id(t)) for t in L.resolve_targets(clr.load(cid))]                       # P2（AC-10A-48）
scan = L.impact(cid, ["刪除"], [SB_T], "oscar", new_request=True)                                          # P3a（AC-10A-50、51）
sb_tc = [x["tc_id"] for x in scan["candidates"] if x["tc_id"].startswith("TC-DEMO-") and store.load(store.tc_version_path(x["tc_id"], 1))["product"] == "other"]
all_c = [x["tc_id"] for x in L.impact(cid, ["刪除"], [], "oscar", new_request=True)["candidates"]]
h = [P.clr_sha(cid)]; r = {}
r["n2"] = P.apply_(cid, landed_in=[rb], defer_targets=[SB_T + "=另一產品下週處理"], keywords=["刪除"], tc_conclusions=[f"{t}=updated" for t in all_c]); h.append(P.clr_sha(cid))   # 64
r["n1"] = P.apply_(cid, landed_in=[rb], targets=[SA_T], defer_targets=[SB_T + "=另一產品下週處理"], keywords=["刪除"], tc_conclusions=[f"{t}=updated" for t in all_c]); h.append(P.clr_sha(cid))   # 49
r["n3"] = P.apply_(cid, landed_in=[ra["rid"]], targets=[SA_T], defer_targets=[SB_T + "=另一產品下週處理"], keywords=["刪除"],
                   tc_conclusions=[f"{t}=updated" for t in all_c if t not in sb_tc]); h.append(P.clr_sha(cid))   # 66
ok = P.apply_(cid, landed_in=[ra["rid"]], targets=[SA_T], defer_targets=[SB_T + "=另一產品下週處理"], keywords=["刪除"],
              tc_conclusions=[f"{t}=updated" if t not in sb_tc else f"{t}=deferred:另一產品下週處理" for t in all_c])   # 65
print(json.dumps({"landings": landings, "targets": targets, "scan": scan, "sb_tc": sb_tc, "r": r, "h": h, "ok": ok, "c": clr.load(cid)}, default=str))""")
    assert out["landings"] == ["incorporated", "incorporated"]                                          # A4 後再被 SB 引用：A4' 只追加 landing
    assert out["targets"] == [["demo", "SPEC-DEMO-001@1.0:REQ-DEMO-001#Q01"], ["other", "SPEC-SB-001@1.0:REQ-DEMO-020#Q01"]]   # AC-10A-48
    s = out["scan"]
    assert s["scan_units"] == [{"product": "demo", "area": "DEMO"}, {"product": "other", "area": "DEMO"}]   # AC-10A-50、51：同 area 名稱、不同 product 分開
    assert out["sb_tc"] and set(out["sb_tc"]) <= {x["tc_id"] for x in s["candidates"]}
    r = out["r"]
    assert "沒有被 --target 確認或 --defer-target 延後" in r["n2"]["error"] or "不含任何被 --target 確認的目標" in r["n2"]["error"]   # AC-10A-64
    assert "不含任何被 --target 確認的目標" in r["n1"]["error"]                                                                     # AC-10A-49
    assert "缺少 --tc-conclusion" in r["n3"]["error"] and out["sb_tc"][0] in r["n3"]["error"]                                       # AC-10A-66
    assert len(set(out["h"])) == 1
    c = out["c"]; l = c["landings"][-1]                                                                  # AC-10A-65
    assert c["status"] == "APPLIED" and l["path"] == "a6"
    assert l["scan_units"] == [{"product": "demo", "area": "DEMO"}, {"product": "other", "area": "DEMO"}]
    assert l["targets_deferred"] == [{"target": "SPEC-SB-001@1.0:REQ-DEMO-020#Q01", "reason": "另一產品下週處理"}]
    assert {x["tc_id"] for x in l["candidates"]} >= set(out["sb_tc"])
