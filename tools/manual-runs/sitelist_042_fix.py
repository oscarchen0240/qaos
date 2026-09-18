#!/usr/bin/env python3
"""RUN-20260914-003 T1 iteration=1：依 Validator 的具體建議修正 TC-SITELIST-042 的修訂草稿。
改引用 REQ-SITELIST-022（而非已作廢的 REQ-023），移除過時 assumption，
expected_result 補上 CLR-SITELIST-009 的樹狀結構原因，spec_reference 標註矛盾註記，
並新增第二條 TC 涵蓋後端 API 拒絕（AC-SITELIST-0222，先前遺漏）。"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids
RUN = "RUN-20260914-003"; ITER = 3
SID, SV, AREA, A = "SPEC-SITELIST-001", "0.4", "SITELIST", "agent-test-designer"
RM_AID = "ART-RM-01M2E2SWZ3GR030YTSZS54E1NE"
OLD_TC = "TC-SITELIST-042"

def sr(loc, q=""): return {"spec_id": SID, "spec_version": SV, "location": loc, "quote": q[:300]}

PRE_ADMIN = ["以 Admin 登入後台", "進入 站台列表"]
EXPECTED = ("兩種類型（線上／機台）皆不提供刪除操作／按鈕（列表與編輯畫面皆找不到任何刪除入口）。"
            "（原因：刪除站台會影響站台樹狀結構——子站台歸屬與上下層關係——故 PM／後端定案不提供刪除功能，見 CLR-SITELIST-009；"
            "可用的狀態切換選項依角色而定，非本案例斷言範圍，見 REQ-SITELIST-016）")
LOC = "§操作/刪除站台（此節內容已由 CLR-SITELIST-009 確認為錯誤敘述，非現行產品行為）"
QUOTE = "點擊列表「刪除」後顯示確認彈窗，列出站台名稱與代碼，二次確認後執行（＊此流程不存在於現行產品，見 CLR-SITELIST-009 PM 回覆）"

tc1 = {
    "draft_id": f"TC-DRAFT-{ids.ulid()}", "title": "任何站台類型皆不提供刪除操作（前端與編輯畫面皆無入口）",
    "product": "ba-admin", "functional_area": AREA,
    "requirement_ids": ["REQ-SITELIST-022"], "acceptance_criteria_ids": ["AC-SITELIST-0221"],
    "spec_id": SID, "spec_version": SV, "test_level": "ui_e2e", "test_types": ["negative"], "design_techniques": ["negative"],
    "priority": "high", "risk": "high", "execution_mode": "manual",
    "preconditions": PRE_ADMIN, "test_data": [],
    "steps": [{"n": 1, "action": "取一個線上類型站台，檢視其列表與編輯畫面的可用操作"},
              {"n": 2, "action": "取一個機台類型站台，檢視其列表與編輯畫面的可用操作"}],
    "expected_result": EXPECTED, "expected_result_spec_reference": sr(LOC, QUOTE),
    "assumptions": [], "automation_status": "not_automated", "ci_eligible": False, "hotfix_eligible": True,
    "execution_cost": "medium", "stability": "unknown", "critical_path": True, "source": "change_workflow",
    "supersedes_testcase": {"testcase_id": OLD_TC, "version": 1},
    "source_ref": "CLR-SITELIST-009",
    "design_rationale": "自 TC-SITELIST-042 v1 修訂：範圍由「機台類型」擴大為「任何類型」，並經 CLR-SITELIST-009 由 PM／後端共同確認前後端皆不可刪除，原因為影響站台樹狀結構",
}
tc2 = {
    "draft_id": f"TC-DRAFT-{ids.ulid()}", "title": "略過前端直接呼叫刪除站台 API，後端同樣拒絕",
    "product": "ba-admin", "functional_area": AREA,
    "requirement_ids": ["REQ-SITELIST-022"], "acceptance_criteria_ids": ["AC-SITELIST-0222"],
    "spec_id": SID, "spec_version": SV, "test_level": "api", "test_types": ["negative"], "design_techniques": ["negative"],
    "priority": "high", "risk": "high", "execution_mode": "manual",
    "preconditions": ["以 Admin 身分取得有效憑證（略過前端 UI 限制）"], "test_data": [],
    "steps": [{"n": 1, "action": "取一個線上類型站台，直接呼叫刪除站台的後端 API，帶入該站台 ID"},
              {"n": 2, "action": "取一個機台類型站台，直接呼叫刪除站台的後端 API，帶入該站台 ID"}],
    "expected_result": "兩種類型皆被後端拒絕該請求，站台資料不受影響（原因：刪除站台會影響站台樹狀結構，故 PM／後端定案不提供刪除功能，見 CLR-SITELIST-009）",
    "expected_result_spec_reference": sr(LOC, QUOTE),
    "assumptions": [], "automation_status": "not_automated", "ci_eligible": False, "hotfix_eligible": True,
    "execution_cost": "low", "stability": "unknown", "critical_path": False, "source": "change_workflow",
    "source_ref": "new_required:CLR-SITELIST-009",
    "design_rationale": "先前 Validator 指出 AC-SITELIST-0222（後端拒絕）未被覆蓋，新增本案例補齊。source_ref 需保留 new_required 前綴（G-DESIGN 規則：mode=change 下無 supersedes_testcase 的新案例必須以此標示），僅將 Validator 建議的自由文字後綴 _backend_coverage 換成單純的 CLR 編號",
}
T = [tc1, tc2]

rep = {"mode": "change", "testcase_draft_artifact_id": None,
       "coverage_matrix": [{"requirement_id": "REQ-SITELIST-022", "draft_ids": [t["draft_id"] for t in T],
                             "acceptance_criteria": [{"ac_id": "AC-SITELIST-0221", "draft_ids": [tc1["draft_id"]]},
                                                      {"ac_id": "AC-SITELIST-0222", "draft_ids": [tc2["draft_id"]]}]}],
       "uncovered_with_reason": [],
       "technique_summary": [{"technique": "negative", "count": 2}],
       "self_check": {k: True for k in ["requirements_covered", "acceptance_criteria_covered", "negative_considered", "boundary_considered", "expected_results_traceable", "no_unsupported_assumptions", "duplicate_detection_completed"]},
       "assumptions": [], "duplicate_check": {"against_registry": True, "findings": []}}

def envelope(t, payload, sub, refs, task="T1"):
    aid = ids.artifact_id(t); art = {"artifact_id": aid, "artifact_type": t, "schema_version": "1.0", "version": 1, "run_id": RUN, "task_id": task, "iteration": ITER,
           "created_by": A, "created_at": store.now(), "status": "DRAFT", "source": {"type": "TestCaseVersion", "ids": [OLD_TC]},
           "references": refs, "requires_approval": None, "payload": payload}
    p = store.ROOT / "artifacts" / "test-design" / RUN / f"{aid}.yaml"; store.save(p, art); return aid, p

refs = [{"entity_type": "Requirement", "id": "REQ-SITELIST-022"}, {"entity_type": "TestCase", "id": OLD_TC}, {"entity_type": "Artifact", "id": RM_AID}]
did, p1 = envelope("TestCaseDraft", {"mode": "change", "spec_id": SID, "spec_version": SV, "testcases": T}, "test-design", refs)
rep["testcase_draft_artifact_id"] = did
_, p2 = envelope("TestDesignReport", rep, "test-design", [{"entity_type": "Artifact", "id": did}])
print(p1.relative_to(store.ROOT)); print(p2.relative_to(store.ROOT))
