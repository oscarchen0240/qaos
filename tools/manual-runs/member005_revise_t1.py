#!/usr/bin/env python3
"""RUN-20260915-015 T1：Test Designer(mode=change) 修訂 TC-MEMBER-005（REQ-MEMBER-004）。
原版 precondition「使用既有加盟商帳號的邀請連結，實際完成一筆新會員註冊並使其升級為加盟商」有歧義，
已由 Oscar 2026-09-15 澄清：「完成註冊」這個動作只會讓新用戶成為邀請人的下線會員，不會讓新用戶自己
也變成加盟商——這是兩件獨立的事，加盟商身分的取得見 REQ-MEMBER-013（達成升等門檻+前台申請，或被
指定為客製化加盟商），跟透過誰的邀請鏈註冊完全無關。"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids
SID, SV, AREA, A = "SPEC-MEMBER-001", "0.2", "MEMBER", "agent-test-designer"
RUN = "RUN-20260915-015"
RM_AID = store.load(store.requirements_path(SID, SV))["source_artifact_id"]
OLD = "TC-MEMBER-005"

def sr(loc, q=""): return {"spec_id": SID, "spec_version": SV, "location": loc, "quote": q[:300]}
def envelope(t, payload, refs, task="T1"):
    aid = ids.artifact_id(t); art = {"artifact_id": aid, "artifact_type": t, "schema_version": "1.0", "version": 1, "run_id": RUN, "task_id": task, "iteration": 0,
           "created_by": A, "created_at": store.now(), "status": "DRAFT", "source": {"type": "TestCaseVersion", "ids": []},
           "references": refs, "requires_approval": None, "payload": payload}
    p = store.ROOT / "artifacts" / "test-design" / RUN / f"{aid}.yaml"; store.save(p, art); return aid, p

tc = {
    "draft_id": f"TC-DRAFT-{ids.ulid()}", "title": "加盟商會員透過邀請鏈註冊時，側邊面板正確顯示完整上下層邀請鏈",
    "product": "ba-admin", "functional_area": AREA,
    "requirement_ids": ["REQ-MEMBER-004"], "acceptance_criteria_ids": ["AC-MEMBER-005"],
    "spec_id": SID, "spec_version": SV, "test_level": "ui_e2e", "test_types": ["functional"], "design_techniques": ["requirement_based"],
    "priority": "medium", "risk": "medium", "execution_mode": "manual",
    "preconditions": [
        "以 Admin 登入後台，進入「會員與加盟商 > 會員列表」頁面",
        "取一名既有會員 X，須同時符合兩個各自獨立的條件：(a) X 目前已具加盟商身分——加盟商身分的取得見 REQ-MEMBER-013（達成升等門檻並透過前台申請，或被指定為客製化加盟商），與註冊方式無關；(b) X 當初是透過『另一名既有會員』的前台邀請連結完成註冊，成為該會員的下線——「完成註冊」這個動作本身只會建立 X 與邀請人之間的上下層關係，不會讓 X 自動取得加盟商身分；自行從環境中選定同時符合這兩個獨立條件的既有帳號，或分兩步驟分別達成：先讓 X 透過邀請連結註冊成為下線，再另外讓 X 依 REQ-MEMBER-013 的途徑取得加盟商身分",
    ],
    "test_data": [],
    "steps": [
        {"n": 1, "action": "於會員列表點擊該會員 X 的會員編號，開啟右側簡易資料面板"},
        {"n": 2, "action": "檢視面板頂部的邀請鏈顯示區塊"},
    ],
    "expected_result": "面板頂部顯示完整的上下層關係：上層會員編號 → 當前會員編號 → 會員N人（N為其下層會員數），且上層顯示的是實際邀請該會員 X 註冊的會員編號",
    "expected_result_spec_reference": sr("§2.1.4 側邊簡易資料面板", "若該會員為加盟商，則顯示其成為加盟商的時間與邀請鏈。邀請鏈顯示完整的上下層關係（如：上層會員編號 → 當前會員編號 → 會員 N 人）"),
    "assumptions": [], "automation_status": "not_automated", "ci_eligible": False, "hotfix_eligible": False,
    "execution_cost": "medium", "stability": "unknown", "critical_path": False, "source": "change_workflow",
    "supersedes_testcase": {"testcase_id": OLD, "version": 1},
    "design_rationale": "原版precondition「完成註冊並使其升級為加盟商」把『透過邀請鏈註冊』與『取得加盟商身分』混為一談，已由Oscar 2026-09-15澄清：完成註冊這個動作只會讓新用戶成為邀請人的下線會員，不會自動讓新用戶自己也變成加盟商，這是兩件獨立的事。已修正precondition，明確區分「成為下線」與「取得加盟商身分」是兩個各自獨立、需分別滿足的條件",
}
rep = {"mode": "change", "testcase_draft_artifact_id": None,
       "coverage_matrix": [{"requirement_id": "REQ-MEMBER-004", "draft_ids": [tc["draft_id"]],
                             "acceptance_criteria": [{"ac_id": "AC-MEMBER-005", "draft_ids": [tc["draft_id"]]}]}],
       "uncovered_with_reason": [
           {"requirement_id": "REQ-MEMBER-004", "reason": "本次修訂僅針對TC-MEMBER-005一條既有TC的precondition措辭精確化（澄清「完成註冊」與「取得加盟商身分」是獨立兩件事），不涉及新增測試設計；此REQ另一條AC-006（非透過邀請鏈註冊時上層顯示為站長，rejection_contract.defined=true，spec §2.1.4已明確定義）已有既存的TC-MEMBER-006覆蓋，本次change範圍不含它、未變動"}
       ],
       "technique_summary": [{"technique": "requirement_based", "count": 1}],
       "self_check": {k: True for k in ["requirements_covered", "acceptance_criteria_covered", "negative_considered", "boundary_considered", "expected_results_traceable", "no_unsupported_assumptions", "duplicate_detection_completed"]},
       "assumptions": [], "duplicate_check": {"against_registry": True, "findings": []}}
refs = [{"entity_type": "Requirement", "id": "REQ-MEMBER-004"}, {"entity_type": "TestCase", "id": OLD}, {"entity_type": "Artifact", "id": RM_AID}]
did, p1 = envelope("TestCaseDraft", {"mode": "change", "spec_id": SID, "spec_version": SV, "testcases": [tc]}, refs)
rep["testcase_draft_artifact_id"] = did
_, p2 = envelope("TestDesignReport", rep, [{"entity_type": "Artifact", "id": did}])
print(p1.relative_to(store.ROOT)); print(p2.relative_to(store.ROOT))
