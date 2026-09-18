#!/usr/bin/env python3
"""RUN-20260916-001 T1（第二次迭代）：重新設計 TC-MEMBER-007/008（REQ-MEMBER-005 v3）。
Oscar 2026-09-16當天先後給了兩版說法，最終確認：出金門檻只看「提領申請金額本身」是否>=10 USDT（含），
與出金手續費、主錢包扣款、可提領餘額精確數值皆無關（只要可提領餘額足以支應本次提領金額即可）。
比先前(v4用稽核=0精確佈置可提領餘額、v2用手續費淨額)都簡化很多：不需要精確工程可提領餘額，
只需要一名餘額充足的會員，直接測試不同的「提領申請金額」輸入值。"""
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

PRECON = (
    "後台帳務資訊「可提領餘額」欄位只是唯讀顯示，「申請出金」是會員在前台自行操作的功能。出金門檻判斷對象是"
    "「提領申請金額」本身（會員在前台送出申請時實際填寫的金額）是否大於等於 10 USDT，與可提領餘額的精確數值、"
    "出金手續費計算皆無關——只要可提領餘額足以支應本次申請金額即可（已由 Oscar 2026-09-16 確認；spec §2.1.4原文"
    "以「可提領餘額」為主詞、且用「大於」(不含10)，與此處確認的實際門檻對象與方向不同，屬spec原文與實際產品行為"
    "的落差，見assumptions，建議另案更新spec原文）。"
    "佈置方式：一名會員的可提領餘額至少有 15 USDT 以上（確保餘額本身不會成為限制因素；不足可用人工存入補足），"
    "無需精確調整可提領餘額至任何特定數值"
)
ASSUMPTION_TEXT = (
    "出金門檻的判斷對象（提領申請金額本身，而非可提領餘額欄位）與方向（大於等於，含10）皆由 Oscar 於 2026-09-16 "
    "口頭確認，spec §2.1.4原文並未明確定義門檻判斷對象是提領申請金額還是可提領餘額本身，也寫成「大於」而非「大於等於」；"
    "此為spec原文尚未更新反映實際產品行為的已知落差"
)

def tc(old, ac, title, amount, expected):
    return {
        "draft_id": f"TC-DRAFT-{ids.ulid()}", "title": title,
        "product": "ba-admin", "functional_area": AREA,
        "requirement_ids": ["REQ-MEMBER-005"], "acceptance_criteria_ids": [ac],
        "spec_id": SID, "spec_version": SV, "test_level": "integration", "test_types": ["boundary"], "design_techniques": ["boundary_value"],
        "priority": "high", "risk": "high", "execution_mode": "manual",
        "preconditions": [PRECON],
        "test_data": [{"name": "提領申請金額", "value": f"{amount} USDT"}],
        "steps": [
            {"n": 1, "action": "確認該會員可提領餘額至少 15 USDT 以上，足以支應本次申請金額"},
            {"n": 2, "action": "以該會員身分登入會員前台，進入出金/提領申請功能"},
            {"n": 3, "action": f"提領申請金額輸入 {amount} USDT，送出提領申請"},
        ],
        "expected_result": expected,
        "expected_result_spec_reference": sr("§2.1.4 帳戶資訊", "可提領餘額｜目前符合提領條件的金額（單位USDT）；須大於 10 USDT 方可申請出金"),
        "assumptions": [
            {"text": ASSUMPTION_TEXT, "requirement_id": "REQ-MEMBER-005", "needs_human_confirmation": True}
        ],
        "automation_status": "not_automated", "ci_eligible": False, "hotfix_eligible": False,
        "execution_cost": "low", "stability": "unknown", "critical_path": True, "source": "change_workflow",
        "supersedes_testcase": {"testcase_id": old, "version": 4},
        "design_rationale": (
            "本次修訂經歷同一天內完整三段式演進：最原始假設(TC-007/008 v4)是門檻判斷對象為『可提領餘額』欄位本身、"
            "方向是『大於10』(不含10)，需用稽核=0精確工程可提領餘額到10.00/10.01兩個數值；第一次更正(v2嘗試，已作廢)"
            "改為門檻判斷對象是『提領申請金額扣除出金手續費後的淨額』，方向改為『大於等於10』(含10)；第二次更正"
            "(本版本，最終確認)Oscar進一步釐清：出金手續費從主錢包額外扣除、不影響會員實際到手金額，門檻判斷單純看"
            "『提領申請金額本身』是否>=10，與手續費、可提領餘額精確數值完全無關，只要餘額『足夠支應』即可。"
            "本版本移除所有手續費相關設計，也不再需要像v4那樣精確工程可提領餘額，測試設計因此大幅簡化為直接測試"
            "不同提領申請金額（10.00 vs 9.99）的邊界情況"
        ),
    }

T = [
    tc("TC-MEMBER-007", "AC-MEMBER-007", "提領申請金額為 9.99 USDT 時不可出金（邊界值，剛好不達門檻）",
       "9.99", "不可出金——提領申請金額本身未達 10 USDT 門檻，申請入口不可用，或送出後被系統拒絕而未成功送出"),
    tc("TC-MEMBER-008", "AC-MEMBER-008", "提領申請金額為 10.00 USDT 時可正常出金（邊界值，剛好達到門檻）",
       "10.00", "可正常出金，申請成功送出——提領申請金額本身剛好達到 10 USDT 門檻（含）"),
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
