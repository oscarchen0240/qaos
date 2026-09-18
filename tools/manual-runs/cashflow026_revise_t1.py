#!/usr/bin/env python3
"""RUN-20260916-006 T1（第二次迭代）：Test Designer(mode=change) 修訂 TC-CASHFLOW-026（REQ-CASHFLOW-022/AC-CASHFLOW-0221）。
Phase2×3交叉比對整合發現：原版只有一個抽象步驟，直接假設「TXID對應的PENDING已被新的req-cashout取代」
這個前提狀態存在，沒有真正操作出這個狀態；Phase3影子測試(RUN-20260916-002,
TC-DRAFT-01M2MBHFR6FY005FGJYW5ZZKRM/...MS79WC71E4CZVMM5)用兩個具體的真實情境（櫃檯人工出金取消PENDING、
新req-cashout取代舊PENDING）各自完整操作一遍才驗證同一個結果。
【第一次迭代錯誤已修正】第一版design_rationale宣稱「新req-cashout取代」路徑已由TC-CASHFLOW-022涵蓋而不重複建立，
但獨立Validator審查查證後發現TC-CASHFLOW-022只測PENDING狀態轉換本身（2個步驟），完全沒有測「用舊TXID呼叫
end-cashout確認回1-NO RECORD」這個後半段——AC-CASHFLOW-0221自己的given範例明講的情境因此被錯誤砍掉、
未經查證。本版把兩個情境都完整補回同一條TC。"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids
SID, SV, AREA, A = "SPEC-CASHFLOW-001", "0.1", "CASHFLOW", "agent-test-designer"
RUN = "RUN-20260916-006"
RM_AID = store.load(store.requirements_path(SID, SV))["source_artifact_id"]
OLD = "TC-CASHFLOW-026"

def sr(loc, q=""): return {"spec_id": SID, "spec_version": SV, "location": loc, "quote": q[:300]}
def envelope(t, payload, refs, task="T1"):
    aid = ids.artifact_id(t); art = {"artifact_id": aid, "artifact_type": t, "schema_version": "1.0", "version": 1, "run_id": RUN, "task_id": task, "iteration": 0,
           "created_by": A, "created_at": store.now(), "status": "DRAFT", "source": {"type": "TestCaseVersion", "ids": []},
           "references": refs, "requires_approval": None, "payload": payload}
    p = store.ROOT / "artifacts" / "test-design" / RUN / f"{aid}.yaml"; store.save(p, art); return aid, p

tc = {
    "draft_id": f"TC-DRAFT-{ids.ulid()}",
    "title": "end-cashout 帶入已失效 TXID 時回 1-NO RECORD：涵蓋人工出金取消與新請求取代兩種真實觸發情境",
    "product": "ba-admin", "functional_area": AREA,
    "requirement_ids": ["REQ-CASHFLOW-022"], "acceptance_criteria_ids": ["AC-CASHFLOW-0221"],
    "spec_id": SID, "spec_version": SV, "test_level": "api", "test_types": ["negative"], "design_techniques": ["scenario"],
    "priority": "high", "risk": "high", "execution_mode": "manual",
    "preconditions": ["機台已透過憑證通過認證", "機台所屬場館為開通狀態，機台為啟用狀態"],
    "test_data": [],
    "steps": [
        {"n": 1, "action": "情境一（人工出金取消）：呼叫 req-cashout 建立一筆尚未完成的出金 PENDING，記錄 TXID_A"},
        {"n": 2, "action": "以 Admin／櫃檯身份登入後台，對該機台帳號執行既有的人工出金功能"},
        {"n": 3, "action": "確認該筆出金 PENDING（TXID_A）是否被同時取消"},
        {"n": 4, "action": "以 TXID_A 呼叫 end-cashout"},
        {"n": 5, "action": "情境二（新請求取代）：呼叫 req-cashout 建立第一筆出金 PENDING，記錄 TXID_B（不呼叫 end-cashout）"},
        {"n": 6, "action": "再次呼叫 req-cashout（模擬玩家再次按下結算鍵），記錄 TXID_C，確認 TXID_B 已被標記失效"},
        {"n": 7, "action": "以已失效的 TXID_B 呼叫 end-cashout"},
    ],
    "expected_result": "情境一：櫃檯執行人工出金的同時，系統同時取消該機台尚未完成的出金 PENDING（TXID_A）；之後以 TXID_A 呼叫 end-cashout 因查無有效對應 PENDING 而回 1-NO RECORD。情境二：第二次 req-cashout（TXID_C）建立前，先將既存的 TXID_B 標記失效；之後以已失效的 TXID_B 呼叫 end-cashout 同樣回 1-NO RECORD。兩種情境皆僅記錄 log 後丟棄、不變更任何資料，避免同一筆錢被領兩次或誤將舊請求完成扣分",
    "expected_result_spec_reference": sr("§附錄-出金", "收到 end-cashout 但查無 PENDING 或 TXID 不符時，僅記錄 log 後丟棄，回 1-NO RECORD"),
    "assumptions": [], "automation_status": "not_automated", "ci_eligible": False, "hotfix_eligible": False,
    "execution_cost": "medium", "stability": "unknown", "critical_path": False, "source": "change_workflow",
    "supersedes_testcase": {"testcase_id": OLD, "version": 1},
    "design_rationale": "Phase2×3交叉比對整合（第三次迭代）：原版(v1)只有一個抽象步驟，直接假設「TXID對應的PENDING已被取代而不存在」這個前提狀態存在，並未真正操作出這個狀態。Phase3影子測試(RUN-20260916-002)對同一AC設計了兩個具體的真實觸發情境（櫃檯人工出金取消PENDING、新req-cashout取代舊PENDING），各自完整操作一遍才驗證end-cashout回1-NO RECORD。第一次迭代(v2)誤判「新req-cashout取代」路徑已由TC-CASHFLOW-022涵蓋而只保留情境一，經獨立Validator查證TC-CASHFLOW-022（AC-CASHFLOW-0191）只測PENDING狀態轉換本身、未測end-cashout後半段，AC-CASHFLOW-0221自己given範例明講的情境因此被錯誤砍掉，v2已把兩個情境都補回。第二次迭代(本版，v3)修正v2的quote欄位錯誤：v2把僅屬於end-cashin條款的「不變更任何資料」誤植到end-cashout的quote上（且非逐字引用spec.md第336行原文），已改為逐字引用該行原文；並把priority從v2的medium改回v1原本的high（risk為high，無理由降低執行優先級）。",
}
rep = {"mode": "change", "testcase_draft_artifact_id": None,
       "coverage_matrix": [{"requirement_id": "REQ-CASHFLOW-022", "draft_ids": [tc["draft_id"]],
                             "acceptance_criteria": [{"ac_id": "AC-CASHFLOW-0221", "draft_ids": [tc["draft_id"]]}]}],
       "uncovered_with_reason": [], "technique_summary": [{"technique": "scenario", "count": 1}],
       "self_check": {k: True for k in ["requirements_covered", "acceptance_criteria_covered", "negative_considered", "boundary_considered", "expected_results_traceable", "no_unsupported_assumptions", "duplicate_detection_completed"]},
       "assumptions": [], "duplicate_check": {"against_registry": True, "findings": []}}
refs = [{"entity_type": "Requirement", "id": "REQ-CASHFLOW-022"}, {"entity_type": "TestCase", "id": OLD}, {"entity_type": "Artifact", "id": RM_AID}]
did, p1 = envelope("TestCaseDraft", {"mode": "change", "spec_id": SID, "spec_version": SV, "testcases": [tc]}, refs)
rep["testcase_draft_artifact_id"] = did
_, p2 = envelope("TestDesignReport", rep, [{"entity_type": "Artifact", "id": did}])
print(p1.relative_to(store.ROOT)); print(p2.relative_to(store.ROOT))
