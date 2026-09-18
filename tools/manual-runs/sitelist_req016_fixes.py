#!/usr/bin/env python3
"""RUN-20260914-011（TC-SITELIST-028）與 RUN-20260914-012（TC-SITELIST-026）的 T1：
依 Oscar 2026-09-14 的直接確認修訂 REQ-SITELIST-016 相關 TC：
- TC-SITELIST-028：ambiguity 已解，雙情境探索式斷言改為單一定論
- TC-SITELIST-026：新增涵蓋 AC-SITELIST-0164（操作員無站台列表頁面存取權）的新案例"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids
SID, SV, AREA, A = "SPEC-SITELIST-001", "0.4", "SITELIST", "agent-test-designer"
RM_AID = "ART-RM-01M2E2SWZ3GR030YTSZS54E1NE"

def sr(loc, q=""): return {"spec_id": SID, "spec_version": SV, "location": loc, "quote": q[:300]}
def envelope(run, t, payload, refs, iteration=0, task="T1"):
    aid = ids.artifact_id(t); art = {"artifact_id": aid, "artifact_type": t, "schema_version": "1.0", "version": 1, "run_id": run, "task_id": task, "iteration": iteration,
           "created_by": A, "created_at": store.now(), "status": "DRAFT", "source": {"type": "TestCaseVersion", "ids": []},
           "references": refs, "requires_approval": None, "payload": payload}
    p = store.ROOT / "artifacts" / "test-design" / run / f"{aid}.yaml"; store.save(p, art); return aid, p

# ===== RUN-20260914-011: TC-SITELIST-028 =====
RUN1 = "RUN-20260914-011"; OLD1 = "TC-SITELIST-028"
tc28 = {
    "draft_id": f"TC-DRAFT-{ids.ulid()}", "title": "Admin 可將既有開通站台手動切回待開通",
    "product": "ba-admin", "functional_area": AREA,
    "requirement_ids": ["REQ-SITELIST-016"], "acceptance_criteria_ids": ["AC-SITELIST-0161"],
    "spec_id": SID, "spec_version": SV, "test_level": "ui_e2e", "test_types": ["functional", "boundary"], "design_techniques": ["requirement_based"],
    "priority": "high", "risk": "high", "execution_mode": "manual",
    "preconditions": ["以 Admin 登入後台", "進入 後台管理員系統 > 站台列表"], "test_data": [],
    "steps": [{"n": 1, "action": "Admin 編輯一個狀態為開通的站台（非例行操作，屬邊界情境：讓一個現正上線中的站台回到上線前狀態）"}, {"n": 2, "action": "將狀態切換為「待開通」並儲存"}],
    "expected_result": "系統接受切換，狀態變為待開通（Oscar 已於 2026-09-14 確認 Admin 的「任意狀態」含待開通，此為定論而非假設）",
    "expected_result_spec_reference": sr("§站台狀態 + §角色與權限/狀態切換（範圍已於 2026-09-14 由 Oscar 確認含待開通）"),
    "assumptions": [], "automation_status": "not_automated", "ci_eligible": False, "hotfix_eligible": True,
    "execution_cost": "medium", "stability": "unknown", "critical_path": False, "source": "change_workflow",
    "supersedes_testcase": {"testcase_id": OLD1, "version": 1}, "source_ref": "oscar_2026-09-14_confirmation",
    "design_rationale": "REQ-SITELIST-016 的 ambiguity 已由 Oscar 直接確認解決，原本雙情境探索式斷言（含 assumptions）改為單一定論的 grounded 案例",
}
rep1 = {"mode": "change", "testcase_draft_artifact_id": None,
        "coverage_matrix": [{"requirement_id": "REQ-SITELIST-016", "draft_ids": [tc28["draft_id"]],
                              "acceptance_criteria": [{"ac_id": "AC-SITELIST-0161", "draft_ids": [tc28["draft_id"]]}]}],
        "uncovered_with_reason": [], "technique_summary": [{"technique": "requirement_based", "count": 1}],
        "self_check": {k: True for k in ["requirements_covered", "acceptance_criteria_covered", "negative_considered", "boundary_considered", "expected_results_traceable", "no_unsupported_assumptions", "duplicate_detection_completed"]},
        "assumptions": [], "duplicate_check": {"against_registry": True, "findings": []}}
refs1 = [{"entity_type": "Requirement", "id": "REQ-SITELIST-016"}, {"entity_type": "TestCase", "id": OLD1}, {"entity_type": "Artifact", "id": RM_AID}]
did1, p1 = envelope(RUN1, "TestCaseDraft", {"mode": "change", "spec_id": SID, "spec_version": SV, "testcases": [tc28]}, refs1)
rep1["testcase_draft_artifact_id"] = did1
_, p1b = envelope(RUN1, "TestDesignReport", rep1, [{"entity_type": "Artifact", "id": did1}])
print(p1.relative_to(store.ROOT)); print(p1b.relative_to(store.ROOT))

# ===== RUN-20260914-012: TC-SITELIST-026 所屬需求新增 AC，本身內容不變，只新增一條案例覆蓋新 AC =====
RUN2 = "RUN-20260914-012"; OLD2 = "TC-SITELIST-026"
tc_operator = {
    "draft_id": f"TC-DRAFT-{ids.ulid()}", "title": "操作員後台看不到站台列表頁面，無法檢視或調整任何站台狀態",
    "product": "ba-admin", "functional_area": AREA,
    "requirement_ids": ["REQ-SITELIST-016"], "acceptance_criteria_ids": ["AC-SITELIST-0164"],
    "spec_id": SID, "spec_version": SV, "test_level": "ui_e2e", "test_types": ["negative"], "design_techniques": ["negative"],
    "priority": "high", "risk": "high", "execution_mode": "manual",
    "preconditions": ["以操作員身分登入後台"], "test_data": [],
    "steps": [{"n": 1, "action": "檢視後台選單，尋找站台列表相關入口"}, {"n": 2, "action": "嘗試直接訪問站台列表頁面路徑"}],
    "expected_result": "後台選單不顯示站台列表入口；直接訪問該頁面路徑也不被允許（無權限）。操作員因此無法檢視或調整任何站台的狀態",
    "expected_result_spec_reference": sr("§角色與權限/狀態切換（操作員範圍已於 2026-09-14 由 Oscar 補充確認）"),
    "assumptions": [], "automation_status": "not_automated", "ci_eligible": False, "hotfix_eligible": True,
    "execution_cost": "low", "stability": "unknown", "critical_path": True, "source": "change_workflow",
    "source_ref": "new_required:oscar_2026-09-14_confirmation",
    "design_rationale": "REQ-SITELIST-016 新增 AC-SITELIST-0164，spec.md v0.4 對操作員此節本不定義（引用實體機台_spec_v07.md），由 Oscar 直接補充確認",
}
T2 = [tc_operator]
rep2 = {"mode": "change", "testcase_draft_artifact_id": None,
        "coverage_matrix": [{"requirement_id": "REQ-SITELIST-016", "draft_ids": [t["draft_id"] for t in T2],
                              "acceptance_criteria": [{"ac_id": "AC-SITELIST-0164", "draft_ids": [tc_operator["draft_id"]]}]}],
        "uncovered_with_reason": [], "technique_summary": [{"technique": "negative", "count": 1}],
        "self_check": {k: True for k in ["requirements_covered", "acceptance_criteria_covered", "negative_considered", "boundary_considered", "expected_results_traceable", "no_unsupported_assumptions", "duplicate_detection_completed"]},
        "assumptions": [], "duplicate_check": {"against_registry": True, "findings": []}}
refs2 = [{"entity_type": "Requirement", "id": "REQ-SITELIST-016"}, {"entity_type": "TestCase", "id": OLD2}, {"entity_type": "Artifact", "id": RM_AID}]
did2, p2 = envelope(RUN2, "TestCaseDraft", {"mode": "change", "spec_id": SID, "spec_version": SV, "testcases": T2}, refs2)
rep2["testcase_draft_artifact_id"] = did2
_, p2b = envelope(RUN2, "TestDesignReport", rep2, [{"entity_type": "Artifact", "id": did2}])
print(p2.relative_to(store.ROOT)); print(p2b.relative_to(store.ROOT))
