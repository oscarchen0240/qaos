#!/usr/bin/env python3
"""RUN-20260916-004 T1：Test Designer(mode=change) 修訂 TC-CASHFLOW-008（REQ-CASHFLOW-007/AC-CASHFLOW-0071,0072）。
Phase2×3交叉比對整合發現：原版只測「未超過上限」與「將超過上限」兩個籠統情況，沒測「恰等於上限」這個精確邊界；
Phase3影子測試(RUN-20260916-002, TC-DRAFT-01M2MBHFR66GECM0VGRNFRGH61)用真正的邊界值手法測了兩側
（恰等於上限→成立並預留、多1單位→拒絕不預留）。併入Phase3這個精確邊界測法。"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids
SID, SV, AREA, A = "SPEC-CASHFLOW-001", "0.1", "CASHFLOW", "agent-test-designer"
RUN = "RUN-20260916-004"
RM_AID = store.load(store.requirements_path(SID, SV))["source_artifact_id"]
OLD = "TC-CASHFLOW-008"

def sr(loc, q=""): return {"spec_id": SID, "spec_version": SV, "location": loc, "quote": q[:300]}
def envelope(t, payload, refs, task="T1"):
    aid = ids.artifact_id(t); art = {"artifact_id": aid, "artifact_type": t, "schema_version": "1.0", "version": 1, "run_id": RUN, "task_id": task, "iteration": 0,
           "created_by": A, "created_at": store.now(), "status": "DRAFT", "source": {"type": "TestCaseVersion", "ids": []},
           "references": refs, "requires_approval": None, "payload": payload}
    p = store.ROOT / "artifacts" / "test-design" / RUN / f"{aid}.yaml"; store.save(p, art); return aid, p

tc = {
    "draft_id": f"TC-DRAFT-{ids.ulid()}",
    "title": "入金加計後恰等於額度上限可成立並預留，超過 1 單位則 1-OVER LIMIT 且不建立 PENDING、不預留",
    "product": "ba-admin", "functional_area": AREA,
    "requirement_ids": ["REQ-CASHFLOW-007"], "acceptance_criteria_ids": ["AC-CASHFLOW-0071", "AC-CASHFLOW-0072"],
    "spec_id": SID, "spec_version": SV, "test_level": "api", "test_types": ["boundary", "negative"], "design_techniques": ["boundary_value"],
    "priority": "high", "risk": "high", "execution_mode": "manual",
    "preconditions": ["機台已透過憑證通過認證", "機台所屬場館為開通狀態，機台為啟用狀態",
                       "設定該場館額度上限為 A，並確認目前「全場館機台分數餘額合計＋已預留未入帳入金金額」恰為 A-100"],
    "test_data": [{"name": "第一筆入金金額", "value": "100（使加計後恰等於上限 A）"}, {"name": "第二筆入金金額", "value": "1（使加計後超過上限 A）"}],
    "steps": [
        {"n": 1, "action": "送出 req-cashin，金額 100，使「全場館餘額合計＋已預留未入帳金額＋本筆金額」恰等於額度上限 A"},
        {"n": 2, "action": "確認回覆建立 PENDING 並將 100 計入預留（此時全場館「餘額合計＋預留」恰為 A）"},
        {"n": 3, "action": "再送出 req-cashin，金額 1，使加計後超過額度上限 A"},
        {"n": 4, "action": "確認此筆的回覆，並確認機台未收到分數變化、無新 PENDING 產生，機台直接退鈔；查詢交易紀錄"},
    ],
    "expected_result": "第一筆恰等於上限：成立，建立 PENDING 並將本筆金額計入預留；第二筆超過上限：回 1-OVER LIMIT，不建立 PENDING、不預留，機台直接退鈔，但交易紀錄留有「未成立」紀錄可查得拒絕原因（超過額度上限不屬於餘額不足的不寫入交易紀錄例外）",
    "expected_result_spec_reference": sr("§附錄-入金 + §四種金流/交易不成立的原因", "req-cashin 於場館鎖內以「全場館餘額＋已預留＋本筆金額」判定額度，未超限才建立 PENDING 並預留；餘額不足不寫入交易紀錄，其餘原因才會留下「未成立」紀錄"),
    "assumptions": [], "automation_status": "not_automated", "ci_eligible": False, "hotfix_eligible": False,
    "execution_cost": "medium", "stability": "unknown", "critical_path": True, "source": "change_workflow",
    "supersedes_testcase": {"testcase_id": OLD, "version": 1},
    "design_rationale": "Phase2×3交叉比對整合：原版(v1)只用「未超過上限」與「將超過上限」兩個籠統值測試，未精確驗證「恰等於上限」這個邊界點是否真的成立。Phase3影子測試(RUN-20260916-002)對同一組AC採用真正的邊界值兩側測法，先驗證恰等於上限時成立並正確預留，再測多1單位驗證拒絕且不預留。本版採用Phase3的精確邊界測法取代原版籠統值；並比照同批TC-CASHFLOW-005的整合結果補上「超過上限的拒絕仍留有交易紀錄」斷言，保持整合深度一致。",
}
rep = {"mode": "change", "testcase_draft_artifact_id": None,
       "coverage_matrix": [{"requirement_id": "REQ-CASHFLOW-007", "draft_ids": [tc["draft_id"]],
                             "acceptance_criteria": [{"ac_id": "AC-CASHFLOW-0071", "draft_ids": [tc["draft_id"]]}, {"ac_id": "AC-CASHFLOW-0072", "draft_ids": [tc["draft_id"]]}]}],
       "uncovered_with_reason": [], "technique_summary": [{"technique": "boundary_value", "count": 1}],
       "self_check": {k: True for k in ["requirements_covered", "acceptance_criteria_covered", "negative_considered", "boundary_considered", "expected_results_traceable", "no_unsupported_assumptions", "duplicate_detection_completed"]},
       "assumptions": [], "duplicate_check": {"against_registry": True, "findings": []}}
refs = [{"entity_type": "Requirement", "id": "REQ-CASHFLOW-007"}, {"entity_type": "TestCase", "id": OLD}, {"entity_type": "Artifact", "id": RM_AID}]
did, p1 = envelope("TestCaseDraft", {"mode": "change", "spec_id": SID, "spec_version": SV, "testcases": [tc]}, refs)
rep["testcase_draft_artifact_id"] = did
_, p2 = envelope("TestDesignReport", rep, [{"entity_type": "Artifact", "id": did}])
print(p1.relative_to(store.ROOT)); print(p2.relative_to(store.ROOT))
