#!/usr/bin/env python3
"""RUN-20260915-011 T1（第二輪修訂，iteration 1）：Test Designer(mode=change) 修訂 TC-PLATFORMRULE-018（REQ-PLATFORMRULE-014）。
原版斷言「操作員可進入場館設定頁面，額度上限欄位唯讀」——已由 Oscar 2026-09-15 確認為錯誤假設。

第一輪修訂（已 FAIL）：把規則過度外推成「操作員對整個場館相關功能都無存取權限」，與 spec 權限表裡操作員對
機台管理/人工入出金/洗分出金核實/機台交易紀錄查詢/場館日結報表皆為可操作/可查看的事實矛盾；且「場次逾時
時間」這個欄位在 SPEC-PLATFORMRULE-001 原文中查無依據（只出現在 ARCADE 正本）。

本輪修正依據：Oscar 2026-09-15 提供操作員實際登入後台的選單截圖，確認選單中完全沒有「站台列表」這個項目，
但「會員與加盟商>會員列表」「帳務管理>洗分出金核實」「各式報表>交易紀錄查詢/場館日結報表」都正常存在。
比對正本說法「機台不設獨立管理頁——機台帳號照常列於會員列表...單一機台的管理位於該機台帳號會員詳細頁的
『機台資訊』區塊」，確認「編輯機台基本資料」「機台停用/啟用」「人工入出金」是透過會員列表進入的獨立功能，
跟「額度上限」「場次逾時時間」所在的「站台列表/場館設定」是完全不同的頁面——規則精確範圍是「操作員選單
沒有站台列表項目，因此該頁面內所有欄位（含額度上限、場次逾時時間）皆整頁無法進入」，不影響其他頁面。
這也解決了 ARCADE 正本比對報告裡 REQ-ARCADE-005（場次逾時時間操作員唯讀）的疑慮，不需要為它另開一條
Requirement，已被本條修正後的規則完整涵蓋。

第二輪修訂（本檔案）：獨立 Validator 於第二輪 T2 審查判定 FAIL，抓出 2 個問題：
  1. (blocker) 「場次逾時時間」仍缺來源依據——額度上限有雙來源（spec原文+Oscar確認），場次逾時時間卻用
     同等確定語氣寫，卻完全沒標明它其實只出處於 SPEC-ARCADE-001 正本、不在本 spec 原文
  2. (major) 「機台管理/人工入出金透過會員列表進入」這條路徑推論，被寫成確定事實，但 Oscar 只確認了選單
     項目存在，沒有逐項確認這些功能實際的頁面路徑，屬於未經驗證的推測當成既定事實
本輪修正：requirement.yaml 的 statement/spec_reference 已明確拆解每個論斷各自的出處（額度上限=本spec原文+
Oscar確認；場次逾時時間=SPEC-ARCADE-001正本，本spec原文未提及），並把機台管理走會員列表這條路徑推論明確
標註為「尚未經 Oscar 逐項確認、非已確認事實」，不再用確定語氣寫。"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids
SID, SV, AREA, A = "SPEC-PLATFORMRULE-001", "0.1", "PLATFORMRULE", "agent-test-designer"
RUN = "RUN-20260915-011"; ITER = 2
RM_AID = store.load(store.requirements_path(SID, SV))["source_artifact_id"]
OLD = "TC-PLATFORMRULE-018"

def sr(loc, q=""): return {"spec_id": SID, "spec_version": SV, "location": loc, "quote": q[:300]}
def envelope(t, payload, refs, task="T1"):
    aid = ids.artifact_id(t); art = {"artifact_id": aid, "artifact_type": t, "schema_version": "1.0", "version": 1, "run_id": RUN, "task_id": task, "iteration": ITER,
           "created_by": A, "created_at": store.now(), "status": "DRAFT", "source": {"type": "TestCaseVersion", "ids": []},
           "references": refs, "requires_approval": None, "payload": payload}
    p = store.ROOT / "artifacts" / "test-design" / RUN / f"{aid}.yaml"; store.save(p, art); return aid, p

tc = {
    "draft_id": f"TC-DRAFT-{ids.ulid()}", "title": "操作員後台選單無「站台列表」項目，無法進入場館設定頁面，額度上限等欄位無從檢視或修改",
    "product": "ba-admin", "functional_area": AREA,
    "requirement_ids": ["REQ-PLATFORMRULE-014"], "acceptance_criteria_ids": ["AC-PLATFORMRULE-0141"],
    "spec_id": SID, "spec_version": SV, "test_level": "ui_e2e", "test_types": ["negative"], "design_techniques": ["negative"],
    "priority": "high", "risk": "high", "execution_mode": "manual",
    "preconditions": ["以操作員身分登入後台", "站台切換選單已選定自身所屬的機台場館"],
    "test_data": [],
    "steps": [
        {"n": 1, "action": "檢視後台左側選單，確認「站台列表」是否存在於選單中"},
        {"n": 2, "action": "確認「會員與加盟商>會員列表」「帳務管理>洗分出金核實」「各式報表>交易紀錄查詢/場館日結報表」是否正常存在於選單中"},
        {"n": 3, "action": "若嘗試直接以網址存取站台列表頁面，觀察系統反應"},
    ],
    "expected_result": "選單中沒有「站台列表」這個項目，因此無法進入場館設定頁面，該頁面內的額度上限（本 spec 原文欄位）與場次逾時時間（SPEC-ARCADE-001 正本定義的欄位，本 spec 原文未提及）皆無從檢視，更無法修改；會員列表、洗分出金核實、交易紀錄查詢、場館日結報表等其他操作員可操作項目正常存在於選單中，不受影響（若直接以網址嘗試存取站台列表頁面，若實際錯誤訊息/阻擋方式與選單消失不同，不視為違反本條，僅測是否被阻擋）",
    "expected_result_spec_reference": sr("§角色與權限", "額度上限（場館層級） | 可設定 | 可設定 | 唯讀（本spec原文欄位，經 Oscar 2026-09-15 選單截圖確認整頁無法進入，非可檢視唯讀）。場次逾時時間欄位本身不在本 spec 原文中，出處見 SPEC-ARCADE-001 §場館設定"),
    "assumptions": [], "automation_status": "not_automated", "ci_eligible": False, "hotfix_eligible": True,
    "execution_cost": "medium", "stability": "unknown", "critical_path": True, "source": "change_workflow",
    "supersedes_testcase": {"testcase_id": OLD, "version": 1},
    "design_rationale": "第二輪 Validator 指出兩點：①場次逾時時間仍缺明確出處標註，本輪已拆解清楚——額度上限是本spec原文欄位+Oscar確認，場次逾時時間出處為SPEC-ARCADE-001正本、本spec原文未提及此欄位名稱；②「機台管理/人工入出金透過會員列表進入」這條路徑推論不寫進本TC的expected_result/steps可測試斷言中（僅作為排除說明留在REQ層級的statement），避免把未經Oscar逐項確認的頁面路徑當成本TC的判定依據；本TC的判定範圍精確限定在「站台列表選單項目是否存在」與「額度上限/場次逾時時間是否可存取」，不涉及機台管理的實際路徑",
}
rep = {"mode": "change", "testcase_draft_artifact_id": None,
       "coverage_matrix": [{"requirement_id": "REQ-PLATFORMRULE-014", "draft_ids": [tc["draft_id"]],
                             "acceptance_criteria": [{"ac_id": "AC-PLATFORMRULE-0141", "draft_ids": [tc["draft_id"]]}]}],
       "uncovered_with_reason": [], "technique_summary": [{"technique": "negative", "count": 1}],
       "self_check": {k: True for k in ["requirements_covered", "acceptance_criteria_covered", "negative_considered", "boundary_considered", "expected_results_traceable", "no_unsupported_assumptions", "duplicate_detection_completed"]},
       "assumptions": [], "duplicate_check": {"against_registry": True, "findings": []}}
refs = [{"entity_type": "Requirement", "id": "REQ-PLATFORMRULE-014"}, {"entity_type": "TestCase", "id": OLD}, {"entity_type": "Artifact", "id": RM_AID}]
did, p1 = envelope("TestCaseDraft", {"mode": "change", "spec_id": SID, "spec_version": SV, "testcases": [tc]}, refs)
rep["testcase_draft_artifact_id"] = did
_, p2 = envelope("TestDesignReport", rep, [{"entity_type": "Artifact", "id": did}])
print(p1.relative_to(store.ROOT)); print(p2.relative_to(store.ROOT))
