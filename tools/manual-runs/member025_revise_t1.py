#!/usr/bin/env python3
"""RUN-20260915-024 T1：Test Designer(mode=change) 修訂 TC-MEMBER-025（REQ-MEMBER-017，刪除推薦註冊金設定）。
Phase 3 影子測試產出的同意圖TC-MEMBER-049（已退役）多了「重新整理列表確認已移除」與「確認畫面上無任何
復原操作入口」的驗證步驟，Phase 2版本只斷言結果、缺乏實際驗證動作。"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids
SID, SV, AREA, A = "SPEC-MEMBER-001", "0.2", "MEMBER", "agent-test-designer"
RUN = "RUN-20260915-024"
RM_AID = store.load(store.requirements_path(SID, SV))["source_artifact_id"]

def sr(loc, q=""): return {"spec_id": SID, "spec_version": SV, "location": loc, "quote": q[:300]}
def envelope(t, payload, refs, task="T1"):
    aid = ids.artifact_id(t); art = {"artifact_id": aid, "artifact_type": t, "schema_version": "1.0", "version": 1, "run_id": RUN, "task_id": task, "iteration": 0,
           "created_by": A, "created_at": store.now(), "status": "DRAFT", "source": {"type": "TestCaseVersion", "ids": []},
           "references": refs, "requires_approval": None, "payload": payload}
    p = store.ROOT / "artifacts" / "test-design" / RUN / f"{aid}.yaml"; store.save(p, art); return aid, p

tc = {
    "draft_id": f"TC-DRAFT-{ids.ulid()}",
    "title": "刪除推薦註冊金設定須二次確認，確認後永久刪除、清單中不再出現、且無任何復原入口",
    "product": "ba-admin", "functional_area": AREA,
    "requirement_ids": ["REQ-MEMBER-017"], "acceptance_criteria_ids": ["AC-MEMBER-024"],
    "spec_id": SID, "spec_version": SV, "test_level": "ui_e2e", "test_types": ["negative"], "design_techniques": ["requirement_based"],
    "priority": "medium", "risk": "medium", "execution_mode": "manual",
    "preconditions": ["推薦註冊金設定列表存在至少一筆既有設定"],
    "test_data": [],
    "steps": [
        {"n": 1, "action": "點擊該筆設定旁的刪除圖示，確認彈出確認視窗"},
        {"n": 2, "action": "於確認視窗點擊確認"},
        {"n": 3, "action": "重新整理列表，確認該筆設定已從清單移除"},
        {"n": 4, "action": "於推薦註冊金設定列表頁確認該列（含整頁）無任何「復原」/「還原」/「取消刪除」按鈕、連結或選單項；依spec.md全文（無任何回收桶/垃圾桶頁面或操作歷程復原功能的定義），本頁面之檢查已涵蓋spec所定義的驗證範圍——若日後系統新增回收桶或操作紀錄等功能，需回頭補測本案例"},
    ],
    "expected_result": "彈出確認視窗；確認後該筆設定被永久刪除，重新整理後清單中不再出現該筆記錄；推薦註冊金設定列表頁不存在任何復原此操作的按鈕或入口（spec全文未定義回收桶或操作歷程復原功能，本案例之驗證範圍以此頁面為準）",
    "expected_result_spec_reference": sr("§2.4.3 列表欄位", "點擊旁側刪除圖示後，彈出確認視窗，確認後刪除該筆設定，操作不可復原"),
    "assumptions": [],
    "automation_status": "not_automated", "ci_eligible": False, "hotfix_eligible": False,
    "execution_cost": "low", "stability": "unknown", "critical_path": False, "source": "change_workflow",
    "supersedes_testcase": {"testcase_id": "TC-MEMBER-025", "version": 1},
    "design_rationale": "已比對Phase 3影子測試(qaos-test-designer agent)產出的TC-MEMBER-049（已退役），其多了「重新整理列表確認已移除」與「確認畫面上無任何復原操作入口」兩個實際驗證動作，Phase 2原版只在expected_result斷言「被永久刪除」「不提供復原功能」，卻沒有對應的steps去實際驗證這兩件事（若只是前端樂觀移除、後端未真的刪除，或者復原入口藏在其他頁面，原TC測不出來）。依整合原則(深度優先)補上這兩個驗證步驟，讓斷言真正可被驗證。v2依獨立Validator FAIL判定修正：v1步驟4「確認畫面上不存在任何可復原的操作入口」範圍界定不清（AC/expected_result講的是系統層級的『不提供復原功能』，但步驟只講『畫面上』，未定義具體檢查範圍），不同執行者可能有不同判定標準。已將步驟4具體化為：僅檢查推薦註冊金設定列表頁本身，並明確寫出範圍依據（spec全文未定義任何回收桶/操作歷程復原功能，故此頁面檢查已涵蓋spec定義的驗證範圍；若日後新增此類功能需回頭補測），同時補上expected_result_spec_reference的實際spec引用文字",
}

rep = {"mode": "change", "testcase_draft_artifact_id": None,
       "coverage_matrix": [{"requirement_id": "REQ-MEMBER-017", "draft_ids": [tc["draft_id"]],
                             "acceptance_criteria": [{"ac_id": "AC-MEMBER-024", "draft_ids": [tc["draft_id"]]}]}],
       "uncovered_with_reason": [], "technique_summary": [{"technique": "requirement_based", "count": 1}],
       "self_check": {k: True for k in ["requirements_covered", "acceptance_criteria_covered", "negative_considered", "boundary_considered", "expected_results_traceable", "no_unsupported_assumptions", "duplicate_detection_completed"]},
       "assumptions": [], "duplicate_check": {"against_registry": True, "findings": [{"draft_id": tc["draft_id"], "similar_to": "TC-MEMBER-049", "resolution": "TC-MEMBER-049(RETIRED)的驗證步驟已整合進本次修訂，不重複進Registry"}]}}
refs = [{"entity_type": "Requirement", "id": "REQ-MEMBER-017"}, {"entity_type": "TestCase", "id": "TC-MEMBER-025"}, {"entity_type": "Artifact", "id": RM_AID}]
did, p1 = envelope("TestCaseDraft", {"mode": "change", "spec_id": SID, "spec_version": SV, "testcases": [tc]}, refs)
rep["testcase_draft_artifact_id"] = did
_, p2 = envelope("TestDesignReport", rep, [{"entity_type": "Artifact", "id": did}])
print(p1.relative_to(store.ROOT)); print(p2.relative_to(store.ROOT))
