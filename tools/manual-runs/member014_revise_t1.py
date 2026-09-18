#!/usr/bin/env python3
"""RUN-20260915-019 T1：Test Designer(mode=change) 修訂 TC-MEMBER-014（REQ-MEMBER-010，前台/後台備注必填）。
Phase 3 影子測試產出的同意圖TC-MEMBER-040（已退役）用decision_table技術涵蓋完整4種組合(前台留空/後台留空/
兩者皆留空/兩者皆填寫)，Phase 2現行版本只測1種組合(前台留空)。依整合原則(廣度覆蓋不能留白)採用Phase 3
的決策表設計。"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids
SID, SV, AREA, A = "SPEC-MEMBER-001", "0.2", "MEMBER", "agent-test-designer"
RUN = "RUN-20260915-019"
RM_AID = store.load(store.requirements_path(SID, SV))["source_artifact_id"]

def sr(loc, q=""): return {"spec_id": SID, "spec_version": SV, "location": loc, "quote": q[:300]}
def envelope(t, payload, refs, task="T1"):
    aid = ids.artifact_id(t); art = {"artifact_id": aid, "artifact_type": t, "schema_version": "1.0", "version": 1, "run_id": RUN, "task_id": task, "iteration": 0,
           "created_by": A, "created_at": store.now(), "status": "DRAFT", "source": {"type": "TestCaseVersion", "ids": []},
           "references": refs, "requires_approval": None, "payload": payload}
    p = store.ROOT / "artifacts" / "test-design" / RUN / f"{aid}.yaml"; store.save(p, art); return aid, p

tc = {
    "draft_id": f"TC-DRAFT-{ids.ulid()}",
    "title": "人工存入前台備注與後台備注兩個必填欄位的組合驗證：任一或兩者留空即阻擋，皆填寫才允許送出",
    "product": "ba-admin", "functional_area": AREA,
    "requirement_ids": ["REQ-MEMBER-010"], "acceptance_criteria_ids": ["AC-MEMBER-014"],
    "spec_id": SID, "spec_version": SV, "test_level": "ui_e2e", "test_types": ["negative"], "design_techniques": ["decision_table"],
    "priority": "medium", "risk": "medium", "execution_mode": "manual",
    "preconditions": ["以 Admin 登入後台，進入一名既有會員的詳細資料頁，開啟人工存入面板"],
    "test_data": [],
    "steps": [
        {"n": 1, "action": "情境一：金額等其他欄位填妥，前台備注留空、後台備注填寫，點擊儲存，觀察結果"},
        {"n": 2, "action": "情境二：金額等其他欄位填妥，前台備注填寫、後台備注留空，點擊儲存，觀察結果"},
        {"n": 3, "action": "情境三：金額等其他欄位填妥，前台備注與後台備注皆留空，點擊儲存，觀察結果"},
        {"n": 4, "action": "情境四：前台備注與後台備注皆填寫，點擊儲存，觀察結果"},
    ],
    "expected_result": "情境一、二、三皆被系統阻擋，不允許在缺少任一（或兩個）必填備注的情況下送出；情境四（兩者皆填寫）成功送出",
    "expected_result_spec_reference": sr("§2.1.5 帳務資訊", "前台備注｜必填；填寫後顯示於會員端，作為該筆金額異動的說明 ｜ 後台備注｜必填；僅後台人員可見，作為該筆操作紀錄的內部說明"),
    "assumptions": [],
    "automation_status": "not_automated", "ci_eligible": False, "hotfix_eligible": False,
    "execution_cost": "low", "stability": "unknown", "critical_path": False, "source": "change_workflow",
    "supersedes_testcase": {"testcase_id": "TC-MEMBER-014", "version": 1},
    "design_rationale": "已比對Phase 3影子測試(qaos-test-designer agent)產出的TC-MEMBER-040（已退役），Phase 2原版只測「前台備注留空、後台備注填寫」這1種組合，AC-MEMBER-014本身雖只明確定義「其中一項留空→阻擋」，但完整的2x2決策表(4種組合)能同時驗證「兩者皆留空」與「兩者皆填寫」這兩個AC未明確提及、但屬於同一條規則自然延伸的組合，避免只測1/4組合就宣稱規則成立。依整合原則(廣度覆蓋不能留白)採用Phase 3的決策表設計技術，design_techniques由requirement_based改為decision_table",
}

rep = {"mode": "change", "testcase_draft_artifact_id": None,
       "coverage_matrix": [{"requirement_id": "REQ-MEMBER-010", "draft_ids": [tc["draft_id"]],
                             "acceptance_criteria": [{"ac_id": "AC-MEMBER-014", "draft_ids": [tc["draft_id"]]}]}],
       "uncovered_with_reason": [], "technique_summary": [{"technique": "decision_table", "count": 1}],
       "self_check": {k: True for k in ["requirements_covered", "acceptance_criteria_covered", "negative_considered", "boundary_considered", "expected_results_traceable", "no_unsupported_assumptions", "duplicate_detection_completed"]},
       "assumptions": [], "duplicate_check": {"against_registry": True, "findings": []}}
refs = [{"entity_type": "Requirement", "id": "REQ-MEMBER-010"}, {"entity_type": "TestCase", "id": "TC-MEMBER-014"}, {"entity_type": "Artifact", "id": RM_AID}]
did, p1 = envelope("TestCaseDraft", {"mode": "change", "spec_id": SID, "spec_version": SV, "testcases": [tc]}, refs)
rep["testcase_draft_artifact_id"] = did
_, p2 = envelope("TestDesignReport", rep, [{"entity_type": "Artifact", "id": did}])
print(p1.relative_to(store.ROOT)); print(p2.relative_to(store.ROOT))
