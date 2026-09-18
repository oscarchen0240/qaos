#!/usr/bin/env python3
"""RUN-20260915-004 T1：Test Designer(mode=change) 依 Oscar 2026-09-15 確認新增 TC，覆蓋 REQ-SITELIST-002
新補的 AC-SITELIST-0023（上層站台為 admin 時，子站台類型不強制跟隨）。"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids
SID, SV, AREA, A = "SPEC-SITELIST-001", "0.4", "SITELIST", "agent-test-designer"
RUN = "RUN-20260915-004"
RM_AID = "ART-RM-01M2E2SWZ3GR030YTSZS54E1NE"
ANCHOR_TC = "TC-SITELIST-003"

def sr(loc, q=""): return {"spec_id": SID, "spec_version": SV, "location": loc, "quote": q[:300]}
def envelope(t, payload, refs, task="T1"):
    aid = ids.artifact_id(t); art = {"artifact_id": aid, "artifact_type": t, "schema_version": "1.0", "version": 1, "run_id": RUN, "task_id": task, "iteration": 0,
           "created_by": A, "created_at": store.now(), "status": "DRAFT", "source": {"type": "TestCaseVersion", "ids": []},
           "references": refs, "requires_approval": None, "payload": payload}
    p = store.ROOT / "artifacts" / "test-design" / RUN / f"{aid}.yaml"; store.save(p, art); return aid, p

tc = {
    "draft_id": f"TC-DRAFT-{ids.ulid()}", "title": "上層站台為 admin 時，子站台類型不強制跟隨，可自由選擇機台或線上",
    "product": "ba-admin", "functional_area": AREA,
    "requirement_ids": ["REQ-SITELIST-002"], "acceptance_criteria_ids": ["AC-SITELIST-0023"],
    "spec_id": SID, "spec_version": SV, "test_level": "ui_e2e", "test_types": ["functional"], "design_techniques": ["requirement_based"],
    "priority": "high", "risk": "high", "execution_mode": "manual",
    "preconditions": ["以 Admin 登入後台", "admin 為既有的最上層根站台（線上類型；測試環境中此站台目前命名為 admin，如環境有變動請以平台最上層根站台為準）"], "test_data": [],
    "steps": [
        {"n": 1, "action": "至後台管理員系統 > 站台列表，新增子站台，上層站台選擇 admin，站台類型選擇「機台」並儲存"},
        {"n": 2, "action": "檢視這個新建立的機台子站台，確認核心貨幣欄位與其自身的鏈上錢包管理"},
        {"n": 3, "action": "再新增另一個子站台，上層站台同樣選擇 admin，這次站台類型選擇「線上」並儲存"},
        {"n": 4, "action": "檢視這個新建立的線上子站台，確認核心貨幣欄位與其自身的鏈上錢包管理"},
    ],
    "expected_result": "兩次新增站台類型欄位皆可自由選擇，不因上層站台 admin 本身是線上類型而被強制鎖定為線上、UI 也未唯讀跟隨；機台類型的子站台建立後核心貨幣顯示 TWD，且該子站台自己的鏈上錢包管理裡 TWD 已連動為啟用狀態；線上類型的子站台建立後核心貨幣顯示 USDT，且該子站台自己的鏈上錢包管理裡 USDT 同樣已連動為啟用狀態——兩種類型皆不需要 admin 自身的鏈上錢包管理預先啟用對應幣別",
    "expected_result_spec_reference": sr("REQ-SITELIST-002 / AC-SITELIST-0023（RequirementModel，非 spec.md 原文——spec.md 全文未記載 admin 特例，此為 Oscar 2026-09-15 口頭確認並寫入 RequirementModel 的行為）"),
    "assumptions": [], "automation_status": "not_automated", "ci_eligible": False, "hotfix_eligible": True,
    "execution_cost": "medium", "stability": "unknown", "critical_path": True, "source": "change_workflow",
    "source_ref": "new_required:oscar_2026-09-15_confirmation",
    "design_rationale": "REQ-SITELIST-002 新增 AC-SITELIST-0023，涵蓋先前完全沒有 TC 測過的 admin 特例路徑；一般主站台（非 admin）底下子站台強制跟隨類型的既有規則由 TC-SITELIST-003/004 覆蓋，維持不變、不受本條影響",
}
tc2 = {
    "draft_id": f"TC-DRAFT-{ids.ulid()}", "title": "admin 底下自由選型建立的子站台，建立後站台類型同樣不可修改", "product": "ba-admin", "functional_area": AREA,
    "requirement_ids": ["REQ-SITELIST-002", "REQ-SITELIST-001"], "acceptance_criteria_ids": ["AC-SITELIST-0023", "AC-SITELIST-0012"],
    "spec_id": SID, "spec_version": SV, "test_level": "ui_e2e", "test_types": ["boundary"], "design_techniques": ["boundary_value"],
    "priority": "high", "risk": "high", "execution_mode": "manual",
    "preconditions": ["以 Admin 登入後台", "admin 底下已有一個依特例自由選型建立的機台類型子站台"], "test_data": [],
    "steps": [{"n": 1, "action": "編輯這個機台類型子站台，檢視站台類型欄位"}],
    "expected_result": "站台類型欄位唯讀、不可修改——這條驗證的其實是既有的 REQ-SITELIST-001／AC-SITELIST-0012（站台類型二擇一、建立後不可修改），本條案例是確認 admin 特例只解除「建立當下強制跟隨上層」這件事（REQ-SITELIST-002／AC-SITELIST-0023 的範圍），不影響「建立後類型鎖定」這條不同需求下的通用規則",
    "expected_result_spec_reference": sr("§站台類型與機台專屬欄位", "每個站台的「站台類型」為線上 / 機台，二擇一；建立後不可修改"),
    "assumptions": [], "automation_status": "not_automated", "ci_eligible": False, "hotfix_eligible": True,
    "execution_cost": "low", "stability": "unknown", "critical_path": False, "source": "change_workflow",
    "source_ref": "new_required:oscar_2026-09-15_confirmation",
    "design_rationale": "admin 特例（REQ-SITELIST-002/AC-0023）只解除子站台建立當下的類型選擇限制，不代表放寬 REQ-SITELIST-001/AC-0012「建立後不可修改」的規則；補一條跨需求的邊界案例避免修復/實作時誤把兩條規則混為一談。本案例主要驗證對象是 AC-SITELIST-0012，掛在 REQ-SITELIST-002 底下是次要關聯（用 admin 特例建立的站台作為測試素材），故 requirement_ids/acceptance_criteria_ids 同時列出兩者",
}
rep = {"mode": "change", "testcase_draft_artifact_id": None,
       "coverage_matrix": [{"requirement_id": "REQ-SITELIST-002", "draft_ids": [tc["draft_id"], tc2["draft_id"]],
                             "acceptance_criteria": [{"ac_id": "AC-SITELIST-0023", "draft_ids": [tc["draft_id"]]}]},
                            {"requirement_id": "REQ-SITELIST-001", "draft_ids": [tc2["draft_id"]],
                             "acceptance_criteria": [{"ac_id": "AC-SITELIST-0012", "draft_ids": [tc2["draft_id"]]}]}],
       "uncovered_with_reason": [], "technique_summary": [{"technique": "requirement_based", "count": 1}, {"technique": "boundary_value", "count": 1}],
       "self_check": {k: True for k in ["requirements_covered", "acceptance_criteria_covered", "negative_considered", "boundary_considered", "expected_results_traceable", "no_unsupported_assumptions", "duplicate_detection_completed"]},
       "assumptions": [], "duplicate_check": {"against_registry": True, "findings": []}}
refs = [{"entity_type": "Requirement", "id": "REQ-SITELIST-002"}, {"entity_type": "TestCase", "id": ANCHOR_TC}, {"entity_type": "Artifact", "id": RM_AID}]
did, p1 = envelope("TestCaseDraft", {"mode": "change", "spec_id": SID, "spec_version": SV, "testcases": [tc, tc2]}, refs)
rep["testcase_draft_artifact_id"] = did
_, p2 = envelope("TestDesignReport", rep, [{"entity_type": "Artifact", "id": did}])
print(p1.relative_to(store.ROOT)); print(p2.relative_to(store.ROOT))
