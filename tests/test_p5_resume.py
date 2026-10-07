"""P5：CLR 生命週期相關操作的中止加續做（需求 A 第 6 章 §8 第 2、3 點）：submit_gate（含 A4）、approve（含 A9）、impact、
apply（a6、a7）、fulfill、waive-item；每種都以兩種入口（同請求重送、operation resume）續做，斷言業務物件沒有重複
（landing 只有一筆、掃描紀錄只有一份、文件索取單只 WITHDRAWN 一次、fulfillment 只有一筆）。故障以 QAOS_FAULT 注入（明確標示）。"""
import json, pathlib
import pytest
from tests import p1_util as U
from tests.test_p4_dispatch import mkroot, py
from tests.test_p5_documents import TWO_MISSING, import_doc, doc_clr

HDR = "from tests import p5_flow as P\nfrom tools.qaos import clr_lifecycle as L\n"

def abort_then_continue(root, args, entry, fault="after_output:1"):
    r = U.q(root, *args, fault=fault); assert r.returncode == 86, (r.stdout, r.stderr)
    inc = U.incomplete(root); assert len(inc) == 1, inc
    r = U.q(root, *args) if entry == "resend" else U.q(root, "operation", "resume", inc[0]["op_id"])
    assert r.returncode in (0, 1) and "Traceback" not in r.stderr, r.stderr
    assert U.incomplete(root) == []
    return r

def clr_doc(root, cid):
    return U.load(root, f"clarifications/demo/DEMO/{cid}.yaml")

@pytest.mark.parametrize("entry", ["resend", "resume"])
def test_gate_with_a4_and_apply_a6(entry, tmp_path):
    root = mkroot(tmp_path)
    rid, cid = py(root, HDR + """
rid, cid, apr = P.ra_p1()
res = {"source": F.cref(cid, "任何站台都不能刪除"), "decided_at": "2026-10-07", "adopted_side_index": 1}
r = P.conflict_req(1, res)
rm_ = {"spec_id": F.SPEC, "spec_version": F.VER, "requirements": [r], "traceability": [{"requirement_id": r["requirement_id"], "spec_reference": r["spec_reference"]}]}
sa = {"spec_id": F.SPEC, "spec_version": F.VER, "content_hash": F.pin()["content_hash"], "summary": "s", "scope": {"in_scope": ["x"], "out_of_scope": []},
      "requirement_ids": [r["requirement_id"]], "ambiguities": [], "constraints": [], "edge_case_candidates": [], "open_questions": []}
from tests import helpers as H
refs_ = [{"entity_type": "SpecVersion", "id": F.SPEC, "version": F.VER}]; src = {"type": "SpecVersion", "ids": [f"{F.SPEC}@{F.VER}"]}
for t, pl, sub in (("SpecAnalysis", sa, "spec-analysis"), ("RequirementModel", rm_, "requirements")):
    _, p = H.write_artifact(rid, "T1", "agent-spec-analyst", t, pl, refs_, src, sub); assert engine.submit(rid, "T1", str(p))[0]
print(json.dumps([rid, cid]))""")
    abort_then_continue(root, ["gate", rid, "T1"], entry, fault="after_output:2")                     # submit_gate（含 A4）
    c = clr_doc(root, cid)
    assert c["status"] == "INCORPORATED" and [l["type"] for l in c["landings"]] == ["incorporated"]
    tcs = py(root, HDR + f"""
g = {{"rmid": [a for a in engine._task(engine.load_run("{rid}"), "T1")["output_artifact_ids"] if a.startswith("ART-RM")][-1]}}
print(json.dumps(P.ra_p3_design("{rid}", "{cid}", g)))""")
    args = ["clarification", "apply", cid, "--path", "a6", "--landed-in", rid, "--target", "SPEC-DEMO-001@1.0:REQ-DEMO-001#Q01", "--keyword", "刪除",
            *sum((["--tc-conclusion", f"{t}=updated"] for t in tcs), []), "--impact-reviewed", "逐張確認", "--by", "oscar"]
    abort_then_continue(root, args, entry, fault="after_output:1")                                    # apply：CLR 狀態寫入之後、landing 之前（同一檔）中止
    c = clr_doc(root, cid)
    assert c["status"] == "APPLIED" and [l["type"] for l in c["landings"]] == ["incorporated", "applied"]

@pytest.mark.parametrize("entry", ["resend", "resume"])
def test_impact_and_apply_a7(entry, tmp_path):
    root = mkroot(tmp_path)
    cid = py(root, HDR + """
q = clr.new("demo", "DEMO", F.SPEC, F.VER, "子站台的排序要不要可設定？", "oscar", consulted=["SPEC-DEMO-001@1.0"], new_request=True)
clr.answer(q["clarification_id"], "維持現狀，不需要。", "pm", "no_change", "oscar", new_request=True)
print(json.dumps(q["clarification_id"]))""")
    abort_then_continue(root, ["clarification", "impact", cid, "--keyword", "排序", "--by", "oscar"], entry)
    c = clr_doc(root, cid); assert len(c["scan_ids"]) == 1
    assert len(list(pathlib.Path(root).glob(f"clarifications/demo/DEMO/scans/{cid}-*.yaml"))) == 1     # 掃描紀錄只有一份
    abort_then_continue(root, ["clarification", "apply", cid, "--path", "a7", "--scan", c["scan_ids"][0], "--impact-reviewed", "無影響", "--by", "oscar"], entry)
    c = clr_doc(root, cid); assert c["status"] == "APPLIED" and [l["path"] for l in c["landings"]] == ["a7"]

@pytest.mark.parametrize("entry", ["resend", "resume"])
def test_fulfill_waive_item_and_approve_a9(entry, tmp_path):
    root = mkroot(tmp_path)
    import_doc(root, tmp_path, "SPEC-ROLE-001", filename="後台角色與權限_spec_v02.md")
    _, cid, _ = doc_clr(root, level="critical")
    abort_then_continue(root, ["clarification", "fulfill", cid, "--item", "D02", "--document", "SPEC-ROLE-001@1.0", "--by", "oscar"], entry)
    c = clr_doc(root, cid); assert len(c["document_items"][1]["fulfillments"]) == 1
    abort_then_continue(root, ["clarification", "waive-item", cid, "--item", "D01", "--reason", "手冊不再提供", "--by", "oscar"], entry)
    c = clr_doc(root, cid)
    assert c["status"] == "APPLIED" and [l["path"] for l in c["landings"] if l["type"] == "applied"] == ["a8"] and len(c["document_items"][0]["waive_records"]) == 1
    # 核准決議寫入之後、A9 之前中止（恢復表第 5 列）
    rid, cid2, apr = py(root, HDR + f"""
rid = F.new_run(); g = F.analyze(rid, [{TWO_MISSING.format(LEVEL="critical").replace("F.req(1,", "F.req(2,")}]); assert g["result"] == "PASS", g
c = [x for x in F.clrs(requirement_id="REQ-DEMO-002") if x.get("kind") == "document_request"][-1]
print(json.dumps([rid, c["clarification_id"], F.waiting(rid)]))""")
    pin = U.load(root, "specs/demo/DEMO/SPEC-DEMO-001/spec.yaml")["versions"][0]["content_hash"]
    p = {"spec_id": "SPEC-DEMO-001", "spec_version": "1.0", "content_hash": pin}
    res = {"requirement_id": "REQ-DEMO-002", "question_id": "Q01", "outcome": "waive_missing", "rationale": "改向 PM 直接確認",
           "waived": [{"cited_at": {**p, "line": 13}, "name": "手冊 7.1.1 角色說明"}, {"cited_at": {**p, "line": 3}, "name": "後台角色與權限_spec_vNN.md"}]}
    abort_then_continue(root, ["approve", apr, "--decision", "approve", "--by", "oscar", "--resolution", json.dumps(res, ensure_ascii=False)], entry, fault="after_output:1")
    c = clr_doc(root, cid2)
    assert c["status"] == "WITHDRAWN" and [h["to_status"] for h in c["history"]].count("WITHDRAWN") == 1
