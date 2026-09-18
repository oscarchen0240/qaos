#!/usr/bin/env python3
"""RUN-20260916-003 T1：Test Designer(mode=change) 修訂 TC-CASHFLOW-005（REQ-CASHFLOW-004/AC-CASHFLOW-0041）。
Phase2×3交叉比對整合發現：原版只測「加計後超過額度上限→拒絕」單邊，沒測「恰等於上限」這一側；
Phase3影子測試(RUN-20260916-002, TC-DRAFT-01M2MBHFR6XP0FQFE63NXFH2BG)用真正的邊界值手法測了兩側
（恰等於上限→成立、多1單位→拒絕），還多驗證了「超過上限的拒絕仍要留交易紀錄」（不屬於餘額不足的不寫入例外）。
併入Phase3這兩點加值，Phase2原版的「與入金共用同一把場館鎖」細節保留。"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids
SID, SV, AREA, A = "SPEC-CASHFLOW-001", "0.1", "CASHFLOW", "agent-test-designer"
RUN = "RUN-20260916-003"
RM_AID = store.load(store.requirements_path(SID, SV))["source_artifact_id"]
OLD = "TC-CASHFLOW-005"

def sr(loc, q=""): return {"spec_id": SID, "spec_version": SV, "location": loc, "quote": q[:300]}
def envelope(t, payload, refs, task="T1"):
    aid = ids.artifact_id(t); art = {"artifact_id": aid, "artifact_type": t, "schema_version": "1.0", "version": 1, "run_id": RUN, "task_id": task, "iteration": 0,
           "created_by": A, "created_at": store.now(), "status": "DRAFT", "source": {"type": "TestCaseVersion", "ids": []},
           "references": refs, "requires_approval": None, "payload": payload}
    p = store.ROOT / "artifacts" / "test-design" / RUN / f"{aid}.yaml"; store.save(p, art); return aid, p

tc = {
    "draft_id": f"TC-DRAFT-{ids.ulid()}",
    "title": "開分加計後恰等於場館額度上限可成立，超過 1 單位則被拒絕且不寫入帳務異動但留交易紀錄",
    "product": "ba-admin", "functional_area": AREA,
    "requirement_ids": ["REQ-CASHFLOW-004"], "acceptance_criteria_ids": ["AC-CASHFLOW-0041"],
    "spec_id": SID, "spec_version": SV, "test_level": "api", "test_types": ["boundary", "negative"], "design_techniques": ["boundary_value"],
    "priority": "high", "risk": "high", "execution_mode": "manual",
    "preconditions": ["機台已透過憑證通過認證", "機台所屬場館為開通狀態，機台為啟用狀態",
                       "調整場館額度上限為一已知值 A，另建構一筆已預留未入帳的入金 PENDING，使目前「全場館機台分數餘額合計＋已預留未入帳入金金額」恰為 A-100"],
    "test_data": [{"name": "第一筆開分金額", "value": "100（使加計後恰等於上限 A）"}, {"name": "第二筆開分金額", "value": "1（使加計後超過上限 A）"}],
    "steps": [
        {"n": 1, "action": "送出開分請求（req-keyin），金額 100，使「全場館機台分數餘額合計＋已預留未入帳入金金額＋本筆金額」恰等於額度上限 A"},
        {"n": 2, "action": "確認回覆為 0-OK，分數正常增加，交易紀錄正常寫入"},
        {"n": 3, "action": "再送出開分請求（req-keyin），金額 1，使加計後超過額度上限 A"},
        {"n": 4, "action": "確認此筆的回覆、分數變化，並查詢交易紀錄"},
    ],
    "expected_result": "第一筆恰等於上限：成立，回 0-OK，分數正常增加；第二筆使合計超過上限：平台回 1-OVER LIMIT，機台畫面顯示失敗，分數不變、不寫入任何帳務異動（判定含已預留未入帳的入金金額，與入金共用同一把場館鎖），但交易紀錄留有「未成立」紀錄可查得拒絕原因（超過額度上限不屬於餘額不足的不寫入交易紀錄例外）",
    "expected_result_spec_reference": sr("§附錄-開分 + §四種金流/交易不成立的原因", "全場館機台分數餘額合計＋已預留未入帳的入金金額，加計本筆金額後不可超過場館額度上限，超過則回 1-OVER LIMIT；餘額不足不寫入交易紀錄，其餘原因才會留下「未成立」紀錄"),
    "assumptions": [], "automation_status": "not_automated", "ci_eligible": False, "hotfix_eligible": False,
    "execution_cost": "medium", "stability": "unknown", "critical_path": True, "source": "change_workflow",
    "supersedes_testcase": {"testcase_id": OLD, "version": 1},
    "design_rationale": "Phase2×3交叉比對整合：原版(v1)只測「加計後超過上限→拒絕」單邊，未驗證「恰等於上限」這一側是否真的成立，也沒驗證超過上限的拒絕是否留交易紀錄。Phase3影子測試(RUN-20260916-002)的獨立設計對同一AC採用真正的邊界值兩側測法（恰等於上限先驗證成立，再測多1單位驗證拒絕），並額外驗證了「超過額度上限不屬於餘額不足的不寫入交易紀錄例外」這個P2原版沒提到的細節。本版整合兩者：保留原版「與入金共用同一把場館鎖」的判定範圍說明，併入Phase3的兩側邊界測法與交易紀錄斷言。",
}
rep = {"mode": "change", "testcase_draft_artifact_id": None,
       "coverage_matrix": [{"requirement_id": "REQ-CASHFLOW-004", "draft_ids": [tc["draft_id"]],
                             "acceptance_criteria": [{"ac_id": "AC-CASHFLOW-0041", "draft_ids": [tc["draft_id"]]}]}],
       "uncovered_with_reason": [], "technique_summary": [{"technique": "boundary_value", "count": 1}],
       "self_check": {k: True for k in ["requirements_covered", "acceptance_criteria_covered", "negative_considered", "boundary_considered", "expected_results_traceable", "no_unsupported_assumptions", "duplicate_detection_completed"]},
       "assumptions": [], "duplicate_check": {"against_registry": True, "findings": []}}
refs = [{"entity_type": "Requirement", "id": "REQ-CASHFLOW-004"}, {"entity_type": "TestCase", "id": OLD}, {"entity_type": "Artifact", "id": RM_AID}]
did, p1 = envelope("TestCaseDraft", {"mode": "change", "spec_id": SID, "spec_version": SV, "testcases": [tc]}, refs)
rep["testcase_draft_artifact_id"] = did
_, p2 = envelope("TestDesignReport", rep, [{"entity_type": "Artifact", "id": did}])
print(p1.relative_to(store.ROOT)); print(p2.relative_to(store.ROOT))
