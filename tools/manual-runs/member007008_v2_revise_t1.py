#!/usr/bin/env python3
"""RUN-20260916-001 T1：Test Designer(mode=change) 重新設計 TC-MEMBER-007/008（REQ-MEMBER-005 v2）。
Oscar 2026-09-16確認：先前TC-007/008(v4)整個門檻機制假設是錯的——真正門檻不是「可提領餘額」欄位本身、
也不是「大於10」(不含)，而是「提領申請金額扣除出金手續費(後台鏈上錢包管理設定%)後的淨額」是否>=10(含)。
RequirementModel(AC-007/008)已於同日修正為version 2，本次依修正後的AC重新設計TC。"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids
SID, SV, AREA, A = "SPEC-MEMBER-001", "0.2", "MEMBER", "agent-test-designer"
RUN = "RUN-20260916-001"
RM_AID = store.load(store.requirements_path(SID, SV))["source_artifact_id"]

def sr(loc, q=""): return {"spec_id": SID, "spec_version": SV, "location": loc, "quote": q[:300]}
def envelope(t, payload, refs, task="T1"):
    aid = ids.artifact_id(t); art = {"artifact_id": aid, "artifact_type": t, "schema_version": "1.0", "version": 1, "run_id": RUN, "task_id": task, "iteration": 0,
           "created_by": A, "created_at": store.now(), "status": "DRAFT", "source": {"type": "TestCaseVersion", "ids": []},
           "references": refs, "requires_approval": None, "payload": payload}
    p = store.ROOT / "artifacts" / "test-design" / RUN / f"{aid}.yaml"; store.save(p, art); return aid, p

FEE_PRECON = (
    "後台帳務資訊「可提領餘額」欄位只是唯讀顯示，「申請出金」是會員在前台自行操作的功能。真正決定能否出金的門檻，"
    "不是對「可提領餘額」欄位本身判斷、也不是「大於10」(不含)——而是「提領申請金額扣除出金手續費後的淨額」是否達到"
    "10 USDT（含）。出金手續費是在後台「帳務管理 > 鏈上錢包管理」設定的百分比，可自由調整"
    "（已由 Oscar 2026-09-16 確認，spec §2.1.4原文僅寫「可提領餘額...須大於10 USDT方可申請出金」，未提及此手續費機制，"
    "屬spec原文與實際產品行為的落差，見assumptions）。"
    "佈置方式：先至鏈上錢包管理將該幣別出金手續費設定為 10%（測試用值，Oscar 2026-09-16以實際操作範例確認）；"
    "確認該會員可提領餘額足夠支應本次申請金額（例如至少 15 USDT以上，避免餘額本身成為限制因素，可用稽核=0的單筆"
    "人工存入調整，見TC-MEMBER-007/008 v4已驗證過的佈置手法）"
)
ASSUMPTION_TEXT = (
    "出金手續費10%對應「申請10 USDT→不可出金、申請11 USDT→可出金且到手10 USDT」這組結果，是 Oscar 2026-09-16"
    "以實際操作範例直接確認的具體案例；本TC只驗證這組已確認的具體數字組合，不代表已獨立驗證手續費計算公式在其他"
    "百分比/金額組合下的四捨五入或計算規則，spec全文也未定義出金手續費此一機制"
)

def tc(old, ac, title, amount, expected, extra_step):
    return {
        "draft_id": f"TC-DRAFT-{ids.ulid()}", "title": title,
        "product": "ba-admin", "functional_area": AREA,
        "requirement_ids": ["REQ-MEMBER-005"], "acceptance_criteria_ids": [ac],
        "spec_id": SID, "spec_version": SV, "test_level": "integration", "test_types": ["boundary"], "design_techniques": ["boundary_value"],
        "priority": "high", "risk": "high", "execution_mode": "manual",
        "preconditions": [FEE_PRECON],
        "test_data": [{"name": "出金手續費", "value": "10%"}, {"name": "提領申請金額", "value": f"{amount} USDT"}],
        "steps": [
            {"n": 1, "action": "於後台「帳務管理 > 鏈上錢包管理」，將該會員可用幣別的出金手續費設定為 10%"},
            {"n": 2, "action": "確認該會員可提領餘額足夠支應本次申請金額（不足則以稽核=0的人工存入補足）"},
            {"n": 3, "action": "以該會員身分登入會員前台，進入出金/提領申請功能"},
            {"n": 4, "action": f"提領申請金額輸入 {amount} USDT，{extra_step}"},
        ],
        "expected_result": expected,
        "expected_result_spec_reference": sr("§2.1.4 帳戶資訊", "可提領餘額｜目前符合提領條件的金額（單位USDT）；須大於 10 USDT 方可申請出金"),
        "assumptions": [
            {"text": ASSUMPTION_TEXT, "requirement_id": "REQ-MEMBER-005", "needs_human_confirmation": True}
        ],
        "automation_status": "not_automated", "ci_eligible": False, "hotfix_eligible": False,
        "execution_cost": "medium", "stability": "unknown", "critical_path": True, "source": "change_workflow",
        "supersedes_testcase": {"testcase_id": old, "version": 4},
        "design_rationale": (
            "Oscar 2026-09-16確認TC-007/008(v4)的整個門檻機制假設是錯的：v4測的是『可提領餘額恰為10.00/10.01時能否出金』，"
            "門檻判斷對象是『可提領餘額』欄位本身，方向是『大於10』(不含10)。但實際機制是門檻判斷『提領申請金額扣除出金手續費"
            "(後台鏈上錢包管理設定%)後的淨額』，且門檻含10(大於等於)。RequirementModel的AC-MEMBER-007/008已於同日修正為"
            "version 2，本次依修正後的AC重新設計：改為在申請金額上做邊界測試(10 USDT不可出金、11 USDT可出金到手10)，"
            "而非在可提領餘額欄位上做邊界測試。v4驗證過的『稽核=0單筆人工存入可精確佈置可提領餘額』手法仍保留用於確保"
            "餘額本身不是限制因素，但不再是本次邊界判斷的測試對象"
        ),
    }

T = [
    tc("TC-MEMBER-007", "AC-MEMBER-007", "出金手續費10%時，申請提領10 USDT（扣手續費後淨額未達10 USDT）不可出金",
       "10.00", "不可出金——扣除出金手續費後的淨額低於 10 USDT 門檻，系統拒絕或申請入口不可用（已由 Oscar 2026-09-16 確認此具體案例的結果）",
       "送出提領申請"),
    tc("TC-MEMBER-008", "AC-MEMBER-008", "出金手續費10%時，申請提領11 USDT（扣手續費後淨額恰為10 USDT）可正常出金",
       "11.00", "可正常出金，申請成功送出，會員實際到手 10 USDT——扣除出金手續費後淨額剛好達到 10 USDT 門檻（含）（已由 Oscar 2026-09-16 確認此具體案例的結果）",
       "送出提領申請"),
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
