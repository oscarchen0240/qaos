#!/usr/bin/env python3
"""RUN-20260915-022 T1：Test Designer(mode=change) 修訂 TC-MEMBER-015（REQ-MEMBER-011，稽核倍數>1）。
Phase 3 影子測試產出的同意圖TC-MEMBER-041（已退役）用具體數值(存入100 USDT、稽核3倍、預期X+300)
取代Phase 2抽象描述(僅說會增加)，可執行性與可驗證性更高。"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids
SID, SV, AREA, A = "SPEC-MEMBER-001", "0.2", "MEMBER", "agent-test-designer"
RUN = "RUN-20260915-022"
RM_AID = store.load(store.requirements_path(SID, SV))["source_artifact_id"]

def sr(loc, q=""): return {"spec_id": SID, "spec_version": SV, "location": loc, "quote": q[:300]}
def envelope(t, payload, refs, task="T1"):
    aid = ids.artifact_id(t); art = {"artifact_id": aid, "artifact_type": t, "schema_version": "1.0", "version": 1, "run_id": RUN, "task_id": task, "iteration": 0,
           "created_by": A, "created_at": store.now(), "status": "DRAFT", "source": {"type": "TestCaseVersion", "ids": []},
           "references": refs, "requires_approval": None, "payload": payload}
    p = store.ROOT / "artifacts" / "test-design" / RUN / f"{aid}.yaml"; store.save(p, art); return aid, p

tc = {
    "draft_id": f"TC-DRAFT-{ids.ulid()}",
    "title": "稽核倍數大於1時，提領所需有效投注額依倍數增加而非單純加回存入金額（具體數值驗證）",
    "product": "ba-admin", "functional_area": AREA,
    "requirement_ids": ["REQ-MEMBER-011"], "acceptance_criteria_ids": ["AC-MEMBER-015"],
    "spec_id": SID, "spec_version": SV, "test_level": "ui_e2e", "test_types": ["functional"], "design_techniques": ["requirement_based"],
    "priority": "high", "risk": "high", "execution_mode": "manual",
    "preconditions": ["以 Admin 登入後台，進入一名既有會員的詳細資料頁"],
    "test_data": [{"name": "人工存入金額", "value": "100 USDT"}, {"name": "稽核倍數", "value": "3"}],
    "steps": [
        {"n": 1, "action": "記錄目前帳務資訊區塊「提領所需有效投注額（流水錢包）」數值（設為 X）"},
        {"n": 2, "action": "點擊「人工存入」，金額填寫 100 USDT、稽核填寫 3，填妥前後台備注後儲存"},
        {"n": 3, "action": "重新整理該會員詳細資料頁，檢視帳務資訊區塊的「提領所需有效投注額」"},
    ],
    "expected_result": "提領所需有效投注額變為 X + (100 × 3) = X + 300，而非單純的 X + 100（存入金額本身），確認稽核倍數確實套用於流水計算",
    "expected_result_spec_reference": sr("§2.1.5 帳務資訊", "稽核｜設定本次異動金額所需完成的可提領投注倍數，將影響會員後續提款條件；預設為 1"),
    "assumptions": [],
    "automation_status": "not_automated", "ci_eligible": False, "hotfix_eligible": False,
    "execution_cost": "low", "stability": "unknown", "critical_path": True, "source": "change_workflow",
    "supersedes_testcase": {"testcase_id": "TC-MEMBER-015", "version": 1},
    "design_rationale": "已比對Phase 3影子測試(qaos-test-designer agent)產出的TC-MEMBER-041（已退役），該版本用具體數值(存入100 USDT、稽核3倍、預期X+300)取代Phase 2原版「執行人工存入，稽核倍數設為3」「因存入金額乘上稽核倍數而增加」這種抽象描述。抽象描述不利於執行者判定「增加多少才算通過」，具體數值使測試結果可被精確驗證、不留模糊空間。依整合原則(深度優先)採用Phase 3的具體數值版本，同時補上重新整理頁面的驗證步驟以確認資料已持久化",
}

rep = {"mode": "change", "testcase_draft_artifact_id": None,
       "coverage_matrix": [{"requirement_id": "REQ-MEMBER-011", "draft_ids": [tc["draft_id"]],
                             "acceptance_criteria": [{"ac_id": "AC-MEMBER-015", "draft_ids": [tc["draft_id"]]}]}],
       "uncovered_with_reason": [
           {"requirement_id": "REQ-MEMBER-011", "reason": "NO_REJECTION_CONTRACT: 本次修訂僅針對TC-MEMBER-015既有1條TC補充具體測試數值，不涉及新增測試設計；REQ-MEMBER-011的negative/boundary情境已由TC-MEMBER-016（ACTIVE）覆蓋（稽核0/負數/留空），本次change範圍不含它、未變動"}
       ], "technique_summary": [{"technique": "requirement_based", "count": 1}],
       "self_check": {k: True for k in ["requirements_covered", "acceptance_criteria_covered", "negative_considered", "boundary_considered", "expected_results_traceable", "no_unsupported_assumptions", "duplicate_detection_completed"]},
       "assumptions": [], "duplicate_check": {"against_registry": True, "findings": [{"draft_id": tc["draft_id"], "similar_to": "TC-MEMBER-041", "resolution": "TC-MEMBER-041(RETIRED)的具體數值設計已整合進本次修訂，不重複進Registry"}]}}
refs = [{"entity_type": "Requirement", "id": "REQ-MEMBER-011"}, {"entity_type": "TestCase", "id": "TC-MEMBER-015"}, {"entity_type": "Artifact", "id": RM_AID}]
did, p1 = envelope("TestCaseDraft", {"mode": "change", "spec_id": SID, "spec_version": SV, "testcases": [tc]}, refs)
rep["testcase_draft_artifact_id"] = did
_, p2 = envelope("TestDesignReport", rep, [{"entity_type": "Artifact", "id": did}])
print(p1.relative_to(store.ROOT)); print(p2.relative_to(store.ROOT))
