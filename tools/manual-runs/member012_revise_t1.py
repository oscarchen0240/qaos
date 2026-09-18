#!/usr/bin/env python3
"""RUN-20260915-021 T1：Test Designer(mode=change) 修訂 TC-MEMBER-012（REQ-MEMBER-008，會員等級編輯）。
Phase 3 影子測試產出的同意圖TC-MEMBER-038（已退役）多了「後台備注欄位選填，可留空」這個步驟；
spec §2.1.5明訂編輯面板有「後台備注（選填）」欄位，Phase 2現行版本完全沒提到，屬廣度缺口。"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids
SID, SV, AREA, A = "SPEC-MEMBER-001", "0.2", "MEMBER", "agent-test-designer"
RUN = "RUN-20260915-021"
RM_AID = store.load(store.requirements_path(SID, SV))["source_artifact_id"]

def sr(loc, q=""): return {"spec_id": SID, "spec_version": SV, "location": loc, "quote": q[:300]}
def envelope(t, payload, refs, task="T1"):
    aid = ids.artifact_id(t); art = {"artifact_id": aid, "artifact_type": t, "schema_version": "1.0", "version": 1, "run_id": RUN, "task_id": task, "iteration": 0,
           "created_by": A, "created_at": store.now(), "status": "DRAFT", "source": {"type": "TestCaseVersion", "ids": []},
           "references": refs, "requires_approval": None, "payload": payload}
    p = store.ROOT / "artifacts" / "test-design" / RUN / f"{aid}.yaml"; store.save(p, art); return aid, p

tc = {
    "draft_id": f"TC-DRAFT-{ids.ulid()}",
    "title": "會員等級可由後台人員編輯，後台備注選填、操作人員自動帶入當前登入帳號",
    "product": "ba-admin", "functional_area": AREA,
    "requirement_ids": ["REQ-MEMBER-008"], "acceptance_criteria_ids": ["AC-MEMBER-012"],
    "spec_id": SID, "spec_version": SV, "test_level": "ui_e2e", "test_types": ["functional"], "design_techniques": ["requirement_based"],
    "priority": "medium", "risk": "medium", "execution_mode": "manual",
    "preconditions": ["以 Admin 登入後台，進入一名會員的詳細資料頁"],
    "test_data": [],
    "steps": [
        {"n": 1, "action": "點擊會員等級旁的「編輯」按鈕，確認右側滑出「會員等級編輯」面板"},
        {"n": 2, "action": "面板中選擇一個與目前不同的新會員等級"},
        {"n": 3, "action": "後台備注欄位（選填）留空，不填寫"},
        {"n": 4, "action": "點擊儲存"},
    ],
    "expected_result": "會員等級成功更新為新選擇的等級；後台備注為選填欄位，留空不影響儲存成功；操作人員欄位自動帶入當前登入帳號，不需手動填寫",
    "expected_result_spec_reference": sr("§2.1.5 等級資訊", "會員等級｜可透過「編輯」按鈕手動調整；點擊後右側滑出「會員等級編輯」面板，填寫以下欄位後點擊「儲存」：會員編號（唯讀）、會員等級（下拉選單）、後台備注（選填）、操作人員（自動帶入當前登入帳號，唯讀）"),
    "assumptions": [],
    "automation_status": "not_automated", "ci_eligible": False, "hotfix_eligible": False,
    "execution_cost": "low", "stability": "unknown", "critical_path": False, "source": "change_workflow",
    "supersedes_testcase": {"testcase_id": "TC-MEMBER-012", "version": 1},
    "design_rationale": "已比對Phase 3影子測試(qaos-test-designer agent)產出的TC-MEMBER-038（已退役），其步驟多了「後台備注欄位選填，可留空」；核對spec §2.1.5發現編輯面板確實定義了「後台備注（選填）」欄位，Phase 2原版precondition/steps/expected_result完全沒提到這個欄位存在，屬廣度缺口（若後台備注其實有隱藏的驗證規則，原TC完全測不到）。本輪已在steps中加入該欄位（驗證選填、留空可儲存），expected_result同步補充說明",
}

rep = {"mode": "change", "testcase_draft_artifact_id": None,
       "coverage_matrix": [{"requirement_id": "REQ-MEMBER-008", "draft_ids": [tc["draft_id"]],
                             "acceptance_criteria": [{"ac_id": "AC-MEMBER-012", "draft_ids": [tc["draft_id"]]}]}],
       "uncovered_with_reason": [
           {"requirement_id": "REQ-MEMBER-008", "reason": "本次修訂僅針對TC-MEMBER-012既有1條TC補充後台備注欄位的揭露，不涉及新增測試設計；REQ-MEMBER-008本身無其他negative/boundary案例，屬既有現況，不在本次修訂範圍內"}
       ], "technique_summary": [{"technique": "requirement_based", "count": 1}],
       "self_check": {k: True for k in ["requirements_covered", "acceptance_criteria_covered", "negative_considered", "boundary_considered", "expected_results_traceable", "no_unsupported_assumptions", "duplicate_detection_completed"]},
       "assumptions": [], "duplicate_check": {"against_registry": True, "findings": [{"draft_id": tc["draft_id"], "similar_to": "TC-MEMBER-038", "resolution": "TC-MEMBER-038(RETIRED)的後台備注揭露已整合進本次修訂，不重複進Registry"}]}}
refs = [{"entity_type": "Requirement", "id": "REQ-MEMBER-008"}, {"entity_type": "TestCase", "id": "TC-MEMBER-012"}, {"entity_type": "Artifact", "id": RM_AID}]
did, p1 = envelope("TestCaseDraft", {"mode": "change", "spec_id": SID, "spec_version": SV, "testcases": [tc]}, refs)
rep["testcase_draft_artifact_id"] = did
_, p2 = envelope("TestDesignReport", rep, [{"entity_type": "Artifact", "id": did}])
print(p1.relative_to(store.ROOT)); print(p2.relative_to(store.ROOT))
