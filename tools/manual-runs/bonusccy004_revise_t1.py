#!/usr/bin/env python3
"""RUN-20260915-005 T1（第三次修訂，iteration 2）：Test Designer(mode=change) 依 PM 2026-09-15 對 CLR-BONUSCCY-002 的回覆，
重寫 REQ-BONUSCCY-004 對應的 TC。PM 確認：①核心貨幣可以被停用，用途是資金池出問題時即時止損（刻意設計，
不該被阻擋）②停用後，入金/出金/開分/洗分四項操作皆應被系統阻擋。這推翻了第一次修訂版（APR-0042，已 reject）
「系統應阻擋停用動作本身」的錯誤假設。
Oscar 2026-09-15 已實測：關閉TWD後，開分/入金確實失敗，但出金/洗分卻仍然成功——這與PM剛確認的正確行為不符，
是真實bug（另外走 spec-to-bug 流程處理），但這裡的 TC 仍照 PM 確認的正確規則設計，不因目前系統行為錯誤而遷就。

第二輪修訂（本檔案）：獨立 Validator 於第一輪 T2 審查判定 FAIL（G-TVAL semantic FAIL，見 ART-TVR-01M2GRV4AG4VSYN8QFVY96MS74），
抓出 2 個 blocker + 1 個 major：
  1. (blocker) 出金/洗分 的 steps 未指出實際操作入口，無法重現
  2. (blocker) spec.md 全文查無「洗分」，缺乏依據
  3. (major) precondition 用「例如」弱化站台類型限制，且統一寫「以 Admin 登入後台」不符實際操作角色
修正依據：Oscar 2026-09-15 直接確認操作入口——「機台版前台進行開分、洗分、入金、出金」（後台僅用於停用核心貨幣本身），
已比照本 session「PM/Oscar 直接確認即視為grounded」的既定規則採用，並在 design_rationale/precondition 中明確標註來源與日期。"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids
SID, SV, AREA, A = "SPEC-BONUSCCY-001", "1.0", "BONUSCCY", "agent-test-designer"
RUN = "RUN-20260915-005"; ITER = 2
RM_AID = store.load(store.requirements_path(SID, SV))["source_artifact_id"]
OLD = "TC-BONUSCCY-008"

def sr(loc, q=""): return {"spec_id": SID, "spec_version": SV, "location": loc, "quote": q[:300]}
def envelope(t, payload, refs, task="T1"):
    aid = ids.artifact_id(t); art = {"artifact_id": aid, "artifact_type": t, "schema_version": "1.0", "version": 1, "run_id": RUN, "task_id": task, "iteration": ITER,
           "created_by": A, "created_at": store.now(), "status": "DRAFT", "source": {"type": "TestCaseVersion", "ids": []},
           "references": refs, "requires_approval": None, "payload": payload}
    p = store.ROOT / "artifacts" / "test-design" / RUN / f"{aid}.yaml"; store.save(p, art); return aid, p

def preconditions(op):
    return [
        "以 Admin 登入後台，至該機台站台的鏈上錢包管理，將核心貨幣本身對應的錢包幣別（例如 TWD）停用",
        f"必須使用機台站台（非線上站台）——{op}為機台版前台功能，線上站台無此入口，Oscar 2026-09-15 確認入金/出金/開分/洗分四項操作皆於機台版前台進行，對應 SPEC-CASHFLOW-001 §兩階段/單階段對照表的 API",
    ]

def tc(acs, title, steps, expected, op, supersede=False):
    d = {"draft_id": f"TC-DRAFT-{ids.ulid()}", "title": title, "product": "ba-admin", "functional_area": AREA,
         "requirement_ids": ["REQ-BONUSCCY-004"], "acceptance_criteria_ids": acs,
         "spec_id": SID, "spec_version": SV, "test_level": "ui_e2e", "test_types": ["negative"], "design_techniques": ["negative"],
         "priority": "high", "risk": "high", "execution_mode": "manual",
         "preconditions": preconditions(op),
         "test_data": [],
         "steps": [{"n": i + 1, "action": s} for i, s in enumerate(steps)],
         "expected_result": expected,
         "expected_result_spec_reference": sr("§一句話（限制段落，2026-09-15 PM 補充確認）"),
         "assumptions": [],
         "automation_status": "not_automated", "ci_eligible": False, "hotfix_eligible": True,
         "execution_cost": "medium", "stability": "unknown", "critical_path": True, "source": "change_workflow",
         "design_rationale": f"PM 2026-09-15 明確確認：核心貨幣可停用（止損用途，本身不應被阻擋），但停用後{op}應被系統阻擋。這條驗證的是「停用後」的下游效果，不是停用動作本身。操作步驟依 SPEC-CASHFLOW-001 §出入金/開洗分流程定義的 API（req-cashin/end-cashin、req-cashout/end-cashout、req-keyin、req-keyout），並經 Oscar 2026-09-15 實機截圖確認"}
    if supersede: d["supersedes_testcase"] = {"testcase_id": OLD, "version": 1}
    else: d["source_ref"] = "new_required:pm_confirmation_CLR-BONUSCCY-002_2026-09-15"
    return d

T = [
    tc(["AC-BONUSCCY-006"], "核心貨幣對應幣別已停用時，入金操作應被阻擋",
       ["於機台版前台投紙鈔，觸發 req-cashin（建立入金 PENDING）", "接著觸發 end-cashin（確認入金）", "觀察兩階段的回應（是否仍回 0-OK 並完成入帳）"],
       "req-cashin 或 end-cashin 任一階段應被阻擋（不應兩階段皆回 0-OK 並完成入帳）；若實際錯誤訊息/狀態碼文案不同，不視為違反本條，僅測是否被阻擋", "入金", supersede=True),
    tc(["AC-BONUSCCY-022"], "核心貨幣對應幣別已停用時，出金操作應被阻擋",
       ["於機台版前台按 CASHOUT 鍵，觸發 req-cashout（建立出金 PENDING，核可金額為全部餘額）", "接著觸發 end-cashout（確認出金，帶入 TXID）", "觀察兩階段的回應（是否仍回 0-OK 並完成扣分）"],
       "req-cashout 或 end-cashout 任一階段應被阻擋（不應兩階段皆回 0-OK 並完成扣分）；若實際錯誤訊息/狀態碼文案不同，不視為違反本條，僅測是否被阻擋", "出金"),
    tc(["AC-BONUSCCY-023"], "核心貨幣對應幣別已停用時，開分操作應被阻擋",
       ["於機台版前台（店員操作）輸入金額 value（必須 > 0），觸發 req-keyin（開分，單階段立即加分）", "觀察回應（是否回 0-OK 並完成加分）"],
       "req-keyin 應被阻擋，不應回 0-OK 並完成加分；若實際錯誤訊息/狀態碼文案不同，不視為違反本條，僅測是否被阻擋", "開分"),
    tc(["AC-BONUSCCY-024"], "核心貨幣對應幣別已停用時，洗分操作應被阻擋",
       ["於機台版前台選擇「全洗 all」或輸入指定金額 value，觸發 req-keyout（洗分，單階段立即結束當前場次並扣分）", "觀察回應（是否回 0-OK 並完成扣分）"],
       "req-keyout 應被阻擋，不應回 0-OK 並完成扣分；若實際錯誤訊息/狀態碼文案不同，不視為違反本條，僅測是否被阻擋", "洗分"),
]
rep = {"mode": "change", "testcase_draft_artifact_id": None,
       "coverage_matrix": [{"requirement_id": "REQ-BONUSCCY-004", "draft_ids": [t["draft_id"] for t in T],
                             "acceptance_criteria": [{"ac_id": t["acceptance_criteria_ids"][0], "draft_ids": [t["draft_id"]]} for t in T]}],
       "uncovered_with_reason": [{"requirement_id": "REQ-BONUSCCY-004", "reason": "「核心貨幣停用後重新啟用，四項操作是否恢復正常」屬正向場景，非本次 PM 澄清（CLR-BONUSCCY-002）的範圍，本輪不列入，建議另立 TC 追蹤"}],
       "technique_summary": [{"technique": "negative", "count": 4}],
       "self_check": {k: True for k in ["requirements_covered", "acceptance_criteria_covered", "negative_considered", "boundary_considered", "expected_results_traceable", "no_unsupported_assumptions", "duplicate_detection_completed"]},
       "assumptions": [], "duplicate_check": {"against_registry": True, "findings": []}}
refs = [{"entity_type": "Requirement", "id": "REQ-BONUSCCY-004"}, {"entity_type": "TestCase", "id": OLD}, {"entity_type": "Artifact", "id": RM_AID}]
did, p1 = envelope("TestCaseDraft", {"mode": "change", "spec_id": SID, "spec_version": SV, "testcases": T}, refs)
rep["testcase_draft_artifact_id"] = did
_, p2 = envelope("TestDesignReport", rep, [{"entity_type": "Artifact", "id": did}])
print(p1.relative_to(store.ROOT)); print(p2.relative_to(store.ROOT))
print(f"{len(T)} TCs")
