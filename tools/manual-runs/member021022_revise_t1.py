#!/usr/bin/env python3
"""RUN-20260915-023 T1：Test Designer(mode=change) 修訂 TC-MEMBER-021/022（REQ-MEMBER-014，客製化加盟商Inline編輯）。
Phase 3 影子測試產出的同意圖TC-MEMBER-045/046（已退役）多了「重新整理列表，確認該列數值」的持久性驗證，
Phase 2版本只驗證UI即時狀態、未驗證是否真的存入/未存入後端。"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids
SID, SV, AREA, A = "SPEC-MEMBER-001", "0.2", "MEMBER", "agent-test-designer"
RUN = "RUN-20260915-023"
RM_AID = store.load(store.requirements_path(SID, SV))["source_artifact_id"]

def sr(loc, q=""): return {"spec_id": SID, "spec_version": SV, "location": loc, "quote": q[:300]}
def envelope(t, payload, refs, task="T1"):
    aid = ids.artifact_id(t); art = {"artifact_id": aid, "artifact_type": t, "schema_version": "1.0", "version": 1, "run_id": RUN, "task_id": task, "iteration": 0,
           "created_by": A, "created_at": store.now(), "status": "DRAFT", "source": {"type": "TestCaseVersion", "ids": []},
           "references": refs, "requires_approval": None, "payload": payload}
    p = store.ROOT / "artifacts" / "test-design" / RUN / f"{aid}.yaml"; store.save(p, art); return aid, p

FIELDS = "佣金比例%、優惠%、返水%、推薦返傭%、行政費、稽核"

tc_confirm = {
    "draft_id": f"TC-DRAFT-{ids.ulid()}",
    "title": "客製化加盟商 Inline 編輯修改欄位數值後點擊確認，成功儲存且重新整理後仍維持新值",
    "product": "ba-admin", "functional_area": AREA,
    "requirement_ids": ["REQ-MEMBER-014"], "acceptance_criteria_ids": ["AC-MEMBER-020"],
    "spec_id": SID, "spec_version": SV, "test_level": "ui_e2e", "test_types": ["functional"], "design_techniques": ["requirement_based"],
    "priority": "medium", "risk": "medium", "execution_mode": "manual",
    "preconditions": ["以 Admin 登入後台，進入加盟列表，取一名已設定客製化加盟商（S Partner）身分的會員"],
    "test_data": [],
    "steps": [
        {"n": 1, "action": f"點擊「超級加盟商」按鈕，確認該列的{FIELDS}欄位進入 Inline 編輯模式"},
        {"n": 2, "action": "修改佣金比例%與行政費為新數值"},
        {"n": 3, "action": "點擊列尾 ✓ 確認"},
        {"n": 4, "action": "重新整理列表，檢視該列數值"},
    ],
    "expected_result": "數值成功更新並儲存為修改後的新值；重新整理列表後該列仍顯示新值（確認資料已持久化存入後端，非僅前端暫存狀態）",
    "expected_result_spec_reference": sr("§2.2.3 客製化加盟商設定", "點擊列尾的 ✓ 確認儲存；或點擊 ✕ 取消並還原原始值"),
    "assumptions": [],
    "automation_status": "not_automated", "ci_eligible": False, "hotfix_eligible": False,
    "execution_cost": "low", "stability": "unknown", "critical_path": False, "source": "change_workflow",
    "supersedes_testcase": {"testcase_id": "TC-MEMBER-021", "version": 1},
    "design_rationale": "已比對Phase 3影子測試(qaos-test-designer agent)產出的TC-MEMBER-045（已退役），其多了「重新整理列表，檢視該列數值」的持久性驗證步驟，Phase 2原版只驗證點擊確認後畫面上顯示更新，未驗證重新整理後是否仍維持（若只是前端樂觀更新、實際未寫入後端，原TC測不出這個缺陷）。依整合原則(深度優先)補上持久性驗證，同時明確列出Inline編輯涉及的6個欄位名稱。v2依獨立Validator FAIL判定修正：v1把第6個欄位誤寫為「稽核倍數」，但spec §2.2.2/§2.2.3實際定義的名稱是「稽核」，「稽核倍數」是§2.4.3推薦註冊金設定的另一個欄位，已修正為「稽核」；並補上expected_result_spec_reference的實際spec引文。TC1只取樣修改2個欄位（佣金比例%、行政費）而非全部6個，是因為6個欄位共用同一套Inline編輯/儲存邏輯，抽樣驗證即可代表整體儲存機制，重點是驗證『儲存後持久化』這個行為本身，非窮舉每個欄位",
}

tc_cancel = {
    "draft_id": f"TC-DRAFT-{ids.ulid()}",
    "title": "客製化加盟商 Inline 編輯修改數值後點擊取消，還原為原始值且不儲存",
    "product": "ba-admin", "functional_area": AREA,
    "requirement_ids": ["REQ-MEMBER-014"], "acceptance_criteria_ids": ["AC-MEMBER-021"],
    "spec_id": SID, "spec_version": SV, "test_level": "ui_e2e", "test_types": ["negative"], "design_techniques": ["requirement_based"],
    "priority": "medium", "risk": "medium", "execution_mode": "manual",
    "preconditions": ["以 Admin 登入後台，進入加盟列表，取一名已設定客製化加盟商（S Partner）身分的會員"],
    "test_data": [],
    "steps": [
        {"n": 1, "action": f"記錄該列目前的{FIELDS}原始數值"},
        {"n": 2, "action": "點擊「超級加盟商」按鈕進入 Inline 編輯模式，將上述欄位修改為與原始值不同的新數值"},
        {"n": 3, "action": "點擊列尾 ✕ 取消"},
        {"n": 4, "action": "檢視該列數值；重新整理列表，再次檢視該列數值"},
    ],
    "expected_result": "點擊取消後立即還原為修改前的原始值，先前輸入的變更未被儲存；重新整理列表後仍維持原始值（畫面顯示狀態與後端實際儲存狀態一致，取消操作未造成資料被覆寫）",
    "expected_result_spec_reference": sr("§2.2.3 客製化加盟商設定", "點擊列尾的 ✓ 確認儲存；或點擊 ✕ 取消並還原原始值"),
    "assumptions": [],
    "automation_status": "not_automated", "ci_eligible": False, "hotfix_eligible": False,
    "execution_cost": "low", "stability": "unknown", "critical_path": False, "source": "change_workflow",
    "supersedes_testcase": {"testcase_id": "TC-MEMBER-022", "version": 1},
    "design_rationale": "已比對Phase 3影子測試(qaos-test-designer agent)產出的TC-MEMBER-046（已退役），同TC-MEMBER-021/045的問題：Phase 2原版只驗證點擊取消後畫面即時還原，未驗證重新整理後是否仍為原始值（若取消動作其實已呼叫API寫入、只是前端顯示還原，原TC測不出這個缺陷）。依整合原則(深度優先)補上重新整理後的二次驗證，同時明確列出涉及的6個欄位名稱。v2依獨立Validator FAIL判定修正：v1把第6個欄位誤寫為「稽核倍數」，實際spec定義名稱是「稽核」，已修正；expected_result原本聲稱『確認取消動作未在後端留下任何殘留變更』略有過度宣稱（手動UI測試只能觀察最終呈現值，無法嚴格證明後端完全未被呼叫），已改為較保守的『畫面顯示狀態與後端實際儲存狀態一致』措辭；並補上expected_result_spec_reference的實際spec引文",
}

T = [tc_confirm, tc_cancel]
by_req_ac = {}
for t in T:
    for ac in t["acceptance_criteria_ids"]:
        by_req_ac.setdefault(ac, []).append(t["draft_id"])
rep = {"mode": "change", "testcase_draft_artifact_id": None,
       "coverage_matrix": [{"requirement_id": "REQ-MEMBER-014", "draft_ids": [t["draft_id"] for t in T],
                             "acceptance_criteria": [{"ac_id": ac, "draft_ids": ids_} for ac, ids_ in by_req_ac.items()]}],
       "uncovered_with_reason": [], "technique_summary": [{"technique": "requirement_based", "count": 2}],
       "self_check": {k: True for k in ["requirements_covered", "acceptance_criteria_covered", "negative_considered", "boundary_considered", "expected_results_traceable", "no_unsupported_assumptions", "duplicate_detection_completed"]},
       "assumptions": [], "duplicate_check": {"against_registry": True, "findings": [
           {"draft_id": tc_confirm["draft_id"], "similar_to": "TC-MEMBER-045", "resolution": "TC-MEMBER-045(RETIRED)的持久性驗證已整合進本次修訂，不重複進Registry"},
           {"draft_id": tc_cancel["draft_id"], "similar_to": "TC-MEMBER-046", "resolution": "TC-MEMBER-046(RETIRED)的持久性驗證已整合進本次修訂，不重複進Registry"},
       ]}}
refs = [{"entity_type": "Requirement", "id": "REQ-MEMBER-014"}, {"entity_type": "TestCase", "id": "TC-MEMBER-021"}, {"entity_type": "TestCase", "id": "TC-MEMBER-022"}, {"entity_type": "Artifact", "id": RM_AID}]
did, p1 = envelope("TestCaseDraft", {"mode": "change", "spec_id": SID, "spec_version": SV, "testcases": T}, refs)
rep["testcase_draft_artifact_id"] = did
_, p2 = envelope("TestDesignReport", rep, [{"entity_type": "Artifact", "id": did}])
print(p1.relative_to(store.ROOT)); print(p2.relative_to(store.ROOT))
