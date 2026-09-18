#!/usr/bin/env python3
"""RUN-20260915-012 T2：Test Designer(mode=change)，重新設計 REQ-ARCADE-004 的負向 TC，取代先前被
per-item reject 的 TC-ARCADE-005（exploratory 假設「稽核倍數應阻擋負數」，該版從未 ACTIVE 過）。
已由 Oscar 2026-09-15 實測確認：前端顯示「失敗，不可小於0」，後端回傳 400 COMMON_NON_NEGATIVE。
改為 grounded TC。用 mode=change 是因為本次 run 範圍只針對這一條補件，不重新分析整份 spec 的其他
4 條已核准 Requirement（REQ-ARCADE-001/002/003/006 已於 RUN-20260915-010／APR-0051 核准）。"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids
SID, SV, AREA, A = "SPEC-ARCADE-001", "0.7", "ARCADE", "agent-test-designer"
RUN = "RUN-20260915-012"; ITER = 1
RM_AID = store.load(store.requirements_path(SID, SV))["source_artifact_id"]

def sr(loc, q=""): return {"spec_id": SID, "spec_version": SV, "location": loc, "quote": q[:300]}

tc = {
    "draft_id": f"TC-DRAFT-{ids.ulid()}", "title": "鏈上錢包管理TWD頁籤稽核倍數輸入負數時，前端阻擋且後端回傳400 COMMON_NON_NEGATIVE",
    "product": "ba-admin", "functional_area": AREA,
    "requirement_ids": ["REQ-ARCADE-004"], "acceptance_criteria_ids": ["AC-ARCADE-004"],
    "spec_id": SID, "spec_version": SV, "test_level": "ui_e2e", "test_types": ["negative"], "design_techniques": ["boundary_value"],
    "priority": "high", "risk": "high", "execution_mode": "manual",
    "preconditions": ["以 Admin 登入後台，站台切換至一個機台場館", "至鏈上錢包管理 > TWD 頁籤"],
    "test_data": [{"name": "稽核倍數", "value": "-1"}],
    "steps": [
        {"n": 1, "action": "將稽核倍數欄位輸入 -1"},
        {"n": 2, "action": "點擊儲存，觀察前端畫面反應"},
    ],
    "expected_result": "前端阻擋此輸入並顯示錯誤訊息「不可小於0」，稽核倍數不會被儲存為負數（已由 Oscar 2026-09-15 實測確認）。備註（可選，需開發者工具能力方可驗證）：後端 API 回傳 400 狀態碼，錯誤代碼 COMMON_NON_NEGATIVE，非正式驗證步驟的必要條件",
    "expected_result_spec_reference": sr("機台帳號的稽核／設定位置", "設定位置｜鏈上錢包管理，於 TWD 頁籤設定稽核倍數（負數輸入驗證行為由 Oscar 2026-09-15 實測確認，spec.md 原文未明訂此輸入驗證規則）"),
    "assumptions": [], "automation_status": "not_automated", "ci_eligible": False, "hotfix_eligible": False,
    "execution_cost": "medium", "stability": "unknown", "critical_path": True, "source": "change_workflow",
    "design_rationale": "原版（TC-ARCADE-005 v1）為 exploratory 假設，已由 Oscar 2026-09-15 實機測試證實：前端顯示「失敗，不可小於0」，後端回傳 400 COMMON_NON_NEGATIVE，改為 grounded TC，不再需要 needs_human_confirmation",
    "source_ref": "new_required:oscar_confirmed_negative_input_validation_2026-09-15",
}
rep = {"mode": "change", "testcase_draft_artifact_id": None,
       "coverage_matrix": [{"requirement_id": "REQ-ARCADE-004", "draft_ids": [tc["draft_id"]],
                             "acceptance_criteria": [{"ac_id": "AC-ARCADE-004", "draft_ids": [tc["draft_id"]]}]}],
       "uncovered_with_reason": [],
       "technique_summary": [{"technique": "boundary_value", "count": 1}],
       "self_check": {k: True for k in ["requirements_covered", "acceptance_criteria_covered", "negative_considered", "boundary_considered", "expected_results_traceable", "no_unsupported_assumptions", "duplicate_detection_completed"]},
       "assumptions": [], "duplicate_check": {"against_registry": True, "findings": [{"draft_id": tc["draft_id"], "similar_to": "TC-ARCADE-005 v1 (rejected exploratory draft, never ACTIVE)", "resolution": "取代前版被拒絕的exploratory草稿，非重複"}]}}
def envelope(t, payload, refs, task="T2"):
    aid = ids.artifact_id(t); art = {"artifact_id": aid, "artifact_type": t, "schema_version": "1.0", "version": 1, "run_id": RUN, "task_id": task, "iteration": ITER,
           "created_by": A, "created_at": store.now(), "status": "DRAFT", "source": {"type": "TestCaseVersion", "ids": []},
           "references": refs, "requires_approval": None, "payload": payload}
    p = store.ROOT / "artifacts" / "test-design" / RUN / f"{aid}.yaml"; store.save(p, art); return aid, p
refs = [{"entity_type": "Requirement", "id": "REQ-ARCADE-004"}, {"entity_type": "Artifact", "id": RM_AID}]
did, p1 = envelope("TestCaseDraft", {"mode": "change", "spec_id": SID, "spec_version": SV, "testcases": [tc]}, refs)
rep["testcase_draft_artifact_id"] = did
_, p2 = envelope("TestDesignReport", rep, [{"entity_type": "Artifact", "id": did}])
print(p1.relative_to(store.ROOT)); print(p2.relative_to(store.ROOT))
