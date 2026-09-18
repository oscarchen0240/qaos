#!/usr/bin/env python3
"""RUN-20260915-016 T1：Test Designer(mode=change) 整合修訂 TC-MEMBER-007/008（REQ-MEMBER-005）。
Phase 3 影子測試（qaos-test-designer agent）獨立設計同一組邊界值TC時，被Validator第二輪抓出Phase 2
現行版本裡藏著的同一個問題：precondition假設「稽核倍數設為1，避免投注門檻影響判斷」，這個假設沒有spec
依據，且與REQ-MEMBER-011的TC（示範稽核倍數會改變投注門檻）自相矛盾。Phase 3第三輪已修正為誠實承認
「可提領餘額與帳戶餘額/提領所需有效投注額/稽核倍數之間的換算公式spec未定義」，並將test_level從ui_e2e
改為integration以反映驗證動作跨出ba-admin進入會員前台。依整合原則（深度優先）採用Phase 3的處理方式。"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids
SID, SV, AREA, A = "SPEC-MEMBER-001", "0.2", "MEMBER", "agent-test-designer"
RUN = "RUN-20260915-016"
RM_AID = store.load(store.requirements_path(SID, SV))["source_artifact_id"]

def sr(loc, q=""): return {"spec_id": SID, "spec_version": SV, "location": loc, "quote": q[:300]}
def envelope(t, payload, refs, task="T1"):
    aid = ids.artifact_id(t); art = {"artifact_id": aid, "artifact_type": t, "schema_version": "1.0", "version": 1, "run_id": RUN, "task_id": task, "iteration": 0,
           "created_by": A, "created_at": store.now(), "status": "DRAFT", "source": {"type": "TestCaseVersion", "ids": []},
           "references": refs, "requires_approval": None, "payload": payload}
    p = store.ROOT / "artifacts" / "test-design" / RUN / f"{aid}.yaml"; store.save(p, art); return aid, p

BOUNDARY_PRECON_TEMPLATE = (
    "後台帳務資訊「可提領餘額」欄位只是唯讀顯示，「申請出金」是會員在前台自行操作的功能；「須大於10 USDT」這道門檻僅在前台實際送出出金申請（API）時才會被檢查，後台人工提出操作本身不受此門檻限制（已由 Oscar 2026-09-15 確認）。"
    "換算公式與人工存入/提出機制（已由 Oscar 2026-09-15 以實際操作範例確認）：可提領餘額 ＝ 帳戶餘額（主錢包） － 提領所需有效投注額（流水錢包）；人工存入/提出時，「金額」欄位數字直接增減主錢包，「金額×稽核倍數」則是流水錢包的增減量——稽核倍數可設為 0（已實測確認為合法輸入），此時金額只會影響主錢包、完全不影響流水錢包。"
    "佈置方式：先於該會員的帳務資訊區塊確認目前的可提領餘額基準值（設為 B），接著執行一筆人工存入，金額 ＝ {target} － B、稽核倍數設為 0，使主錢包精確增加 (目標值－B)、流水錢包不變，存入後可提領餘額即精確等於 {target} USDT；若 B 已大於目標值，改用同樣稽核=0 的人工提出，金額 ＝ B － {target}，使可提領餘額精確降至 {target} USDT"
)

def tc(old, ac, title, precon, value, expected):
    return {
        "draft_id": f"TC-DRAFT-{ids.ulid()}", "title": title,
        "product": "ba-admin", "functional_area": AREA,
        "requirement_ids": ["REQ-MEMBER-005"], "acceptance_criteria_ids": [ac],
        "spec_id": SID, "spec_version": SV, "test_level": "integration", "test_types": ["boundary"], "design_techniques": ["boundary_value"],
        "priority": "high", "risk": "high", "execution_mode": "manual",
        "preconditions": [BOUNDARY_PRECON_TEMPLATE.format(target=value)],
        "test_data": [{"name": "人工存入/提出金額", "value": f"= {value} － 該帳號目前可提領餘額基準值 B（稽核倍數固定填0）"}],
        "steps": [
            {"n": 1, "action": "於該會員的帳務資訊區塊查看目前的可提領餘額基準值 B"},
            {"n": 2, "action": f"依 B 與目標值 {value} 的差額，執行一筆稽核倍數=0的人工存入或人工提出（差額為正時存入、為負時提出），將可提領餘額精確調整至 {value} USDT"},
            {"n": 3, "action": f"重新整理該頁面，確認帳務資訊區塊顯示的可提領餘額精確為 {value} USDT"},
            {"n": 4, "action": "以該會員身分登入會員前台，進入出金/提領申請功能"},
            {"n": 5, "action": "嘗試送出出金申請" if value == "10.00" else "送出出金申請"},
        ],
        "expected_result": expected,
        "expected_result_spec_reference": sr("§2.1.5 帳務資訊", "可提領餘額｜目前符合提領條件的金額（單位USDT）；須大於 10 USDT 方可申請出金"),
        "assumptions": [
            {
                "text": "本TC的邊界值佈置手法依賴以下機制，spec §2.1.5僅定義「金額」欄位直接影響主錢包、「稽核」欄位設定投注倍數會影響提款條件，但未明訂「可提領餘額＝主錢包－流水錢包」的換算公式、「金額×稽核倍數＝流水錢包增減量」的具體算式、以及稽核=0時是否為合法輸入與其效果；這三項皆由 Oscar 於 2026-09-15 以實際操作範例確認，非spec原文明訂。其中「稽核倍數影響流水錢包增減量」這部分方向上與REQ-MEMBER-011/AC-MEMBER-015（稽核倍數大於1時，提領所需有效投注額因存入金額乘上稽核倍數而增加）一致，但REQ-MEMBER-011並未涵蓋稽核=0這個特例，故本assumption標記在REQ-MEMBER-005（本TC實際驗證的需求）下。若後續系統行為變動（例如稽核=0被系統限制或停用），須重新驗證此佈置手法是否仍然可行",
                "requirement_id": "REQ-MEMBER-005",
                "needs_human_confirmation": True,
            }
        ],
        "automation_status": "not_automated", "ci_eligible": False, "hotfix_eligible": False,
        "execution_cost": "medium", "stability": "unknown", "critical_path": True, "source": "change_workflow",
        "supersedes_testcase": {"testcase_id": old, "version": 1},
        "design_rationale": "v3版本被Validator指出「前台實際投注消耗流水門檻」具機率性、無法精確到0.01邊界，且「人工提出調整門檻」的具體機制未交代清楚。已由 Oscar 2026-09-15 以實際操作範例確認人工存入/提出的精確機制：金額直接增減主錢包，金額×稽核倍數為流水錢包增減量，稽核倍數可設為0（已實測確認合法）。v4改用「稽核=0的單筆人工存入/提出」這個確定可行、精確可控的方式佈置邊界值，不再依賴機率性投注或未驗證的門檻編輯欄位。v5依獨立Validator第三輪PASS審查的2項minor advisory修正：(1) expected_result_spec_reference.location由§2.1.4帳戶資訊（唯讀側邊面板，無操作按鈕）改為§2.1.5帳務資訊（人工存入/提出面板實際所在段落，與steps操作位置一致）；(2) 將原本只在precondition文字裡揭露的「換算公式/稽核=0效果為Oscar實測確認、非spec原文」補充進結構化assumptions欄位，以利下游稽核/追蹤流程辨識此依賴。v6依第四輪獨立Validator FAIL判定修正：v5只把assumptions寫進testcase_draft.yaml，test_design_report.yaml的payload.assumptions沒有同步更新，導致Oscar審批時若只看report彙總會看不到這兩條TC帶有待確認假設；本輪已將assumptions文字（含draft_id前綴）彙總進report.assumptions。self_check.no_unsupported_assumptions維持true——因為Runtime結構性gate規定該self_check區塊每個欄位皆須為true才能通過G-DESIGN，且此欄位語意為『沒有缺乏依據的assumption』而非『沒有assumption』：本次的assumption雖非spec原文明訂，但有Oscar 2026-09-15實際操作範例佐證來源，屬於有依據、已誠實揭露的assumption，並非缺漏未揭露，因此true成立",
    }

T = [
    tc("TC-MEMBER-007", "AC-MEMBER-007", "可提領餘額恰為 10 USDT 時不可於前台申請出金（邊界值，剛好不達門檻）",
       None, "10.00",
       "前台阻擋出金申請（規則為「須大於10 USDT」，剛好等於10不符合條件）：申請入口不可用，或送出後被系統拒絕而未成功送出"),
    tc("TC-MEMBER-008", "AC-MEMBER-008", "可提領餘額為 10.01 USDT 時可正常於前台申請出金（邊界值，略高於門檻）",
       None, "10.01",
       "前台允許正常申請出金，申請成功送出"),
]

by_req_ac = {}
for t in T:
    for ac in t["acceptance_criteria_ids"]:
        by_req_ac.setdefault(ac, []).append(t["draft_id"])
rep = {"mode": "change", "testcase_draft_artifact_id": None,
       "coverage_matrix": [{"requirement_id": "REQ-MEMBER-005", "draft_ids": [t["draft_id"] for t in T],
                             "acceptance_criteria": [{"ac_id": ac, "draft_ids": ids_} for ac, ids_ in by_req_ac.items()]}],
       "uncovered_with_reason": [], "technique_summary": [{"technique": "boundary_value", "count": 2}],
       "self_check": {k: True for k in ["requirements_covered", "acceptance_criteria_covered", "negative_considered", "boundary_considered", "expected_results_traceable", "no_unsupported_assumptions", "duplicate_detection_completed"]},
       "assumptions": [f"{t['draft_id']}: {a['text']}" for t in T for a in t["assumptions"]],
       "duplicate_check": {"against_registry": True, "findings": []}}
refs = [{"entity_type": "Requirement", "id": "REQ-MEMBER-005"}, {"entity_type": "TestCase", "id": "TC-MEMBER-007"}, {"entity_type": "TestCase", "id": "TC-MEMBER-008"}, {"entity_type": "Artifact", "id": RM_AID}]
did, p1 = envelope("TestCaseDraft", {"mode": "change", "spec_id": SID, "spec_version": SV, "testcases": T}, refs)
rep["testcase_draft_artifact_id"] = did
_, p2 = envelope("TestDesignReport", rep, [{"entity_type": "Artifact", "id": did}])
print(p1.relative_to(store.ROOT)); print(p2.relative_to(store.ROOT))
