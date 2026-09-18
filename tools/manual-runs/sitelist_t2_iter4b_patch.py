#!/usr/bin/env python3
"""RUN-20260916-007 T2 iteration 4b：跨 TC 一致性自檢後的收斂。

自檢發現：iteration 4a 新增的 TC（AC-SITELIST-0023 核心貨幣連動）在 step 4 / expected_result
斷言了「核心貨幣欄位為唯讀」，但這是 AC-SITELIST-0101（REQ-SITELIST-010）的斷言、已由
TC-DRAFT-01M2NCSW5D3W9ZQDASZW5FV4BK 覆蓋，且超出 AC-SITELIST-0023 then 子句的範圍。
本次把 step 4 收斂為「只取顯示值 TWD 作為連動建立的證據」，不對唯讀性另作斷言。
其餘內容不動，以新 artifact_id 產出新版本（不刪除舊版）。
"""
import sys, pathlib, copy
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids

RUN, ITER, A = "RUN-20260916-007", 4, "agent-test-designer"
SID, SV = "SPEC-SITELIST-001", "0.4"
RM_AID = "ART-RM-01M2E2SWZ3GR030YTSZS54E1NE"
PREV_TCD = "ART-TCD-01M2QR8VA7WG0RQMTC2A5MKWBT"
PREV_TDR = "ART-TDR-01M2QR8VBDMER2PNBDBH38T71W"
TARGET = "TC-DRAFT-01M2QR8VA6H9TKKST1WYK73T74"
BASE = store.ROOT / "artifacts" / "test-design" / RUN

tcd = store.load(BASE / f"{PREV_TCD}.yaml")
tdr = store.load(BASE / f"{PREV_TDR}.yaml")
TCS = copy.deepcopy(tcd["payload"]["testcases"])
REP = copy.deepcopy(tdr["payload"])

tc = next(t for t in TCS if t["draft_id"] == TARGET)

s4 = next(s for s in tc["steps"] if s["n"] == 4)
s4["expected"] = ("核心貨幣顯示為 TWD。（編輯視窗中核心貨幣為唯讀，屬 AC-SITELIST-0101／REQ-SITELIST-010 的斷言，"
                  "已由 TC-DRAFT-01M2NCSW5D3W9ZQDASZW5FV4BK 覆蓋；本步驟只取其顯示值 TWD 作為「連動建立」的證據，不對唯讀性另作斷言）")

tc["expected_result"] = tc["expected_result"].replace(
    "step 4 顯示該站台核心貨幣為 TWD（唯讀）、",
    "step 4 在該站台的編輯視窗中核心貨幣顯示為 TWD（唯讀性不在本 TC 的斷言範圍內，見 AC-SITELIST-0101）、")
assert "唯讀性不在本 TC 的斷言範圍內" in tc["expected_result"]

tc["design_rationale"] = tc["design_rationale"].replace(
    "step 3/4 的「機台→TWD 連動帶入、建立後唯讀」有 spec.md §核心貨幣 明文（即 expected_result_spec_reference 的引文）；",
    "step 3/4 的「機台→TWD 連動帶入」有 spec.md §核心貨幣 明文（即 expected_result_spec_reference 的引文）；"
    "step 4 刻意只取核心貨幣的顯示值、不斷言其唯讀性——唯讀是 AC-SITELIST-0101 的斷言，"
    "已由 TC-DRAFT-01M2NCSW5D3W9ZQDASZW5FV4BK 覆蓋，在此重複斷言會超出 AC-SITELIST-0023 then 子句的範圍；")
assert "刻意只取核心貨幣的顯示值" in tc["design_rationale"]

REP["revision_of_issues"] = list(REP["revision_of_issues"]) + [{
    "issue_index": 0, "draft_id": TARGET,
    "action": "iteration 4b／submit 前的跨 TC 一致性自檢（非 Validator issue）："
              f"發現新增的 {TARGET} 在 step 4 與 expected_result 斷言了「核心貨幣欄位唯讀」，"
              "但唯讀是 AC-SITELIST-0101（REQ-SITELIST-010）的斷言、已由 TC-DRAFT-01M2NCSW5D3W9ZQDASZW5FV4BK 覆蓋，"
              "且超出 AC-SITELIST-0023 then 子句要求的範圍。已把 step 4 收斂為只取核心貨幣的顯示值 TWD 作為「連動建立」的證據，"
              "並在 step 4 的 expected 與 design_rationale 中標明唯讀性歸屬於哪一條 AC／哪一條 TC。"}]


def envelope(t, payload, refs, supersedes):
    aid = ids.artifact_id(t)
    art = {"artifact_id": aid, "artifact_type": t, "schema_version": "1.0", "version": 1, "run_id": RUN,
           "task_id": "T2", "iteration": ITER, "created_by": A, "created_at": store.now(), "status": "DRAFT",
           "source": {"type": "RequirementModel", "ids": [RM_AID]}, "references": refs,
           "requires_approval": None, "payload": payload, "supersedes_artifact_id": supersedes}
    p = BASE / f"{aid}.yaml"
    store.save(p, art)
    return aid, p


did, p1 = envelope("TestCaseDraft", {"mode": "spec", "spec_id": SID, "spec_version": SV, "testcases": TCS},
                   tcd["references"], PREV_TCD)
REP["testcase_draft_artifact_id"] = did
rid, p2 = envelope("TestDesignReport", REP, [{"entity_type": "Artifact", "id": did}], PREV_TDR)
print(p1); print(p2); print(did, rid)
