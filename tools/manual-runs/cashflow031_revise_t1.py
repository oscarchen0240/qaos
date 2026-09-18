#!/usr/bin/env python3
"""RUN-20260915-014 T1：Test Designer(mode=change) 修訂 TC-CASHFLOW-031（REQ-CASHFLOW-026）。
已由 Oscar 2026-09-15 確認（CLR-CASHFLOW-004）：交易紀錄查詢頁不存在「手動取消」功能，洗分出金核實頁的
「作廢」也只適用於已完成的出金交易、範圍對不上待確認狀態的 PENDING。原 title/expected_result 提到的
「Admin手動取消」收斂路徑需移除，改為實際存在的兩條路徑：新的 req-cashout 取代（REQ-CASHFLOW-019）、
人工出金連動取消（REQ-CASHFLOW-027）。"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids
SID, SV, AREA, A = "SPEC-CASHFLOW-001", "0.1", "CASHFLOW", "agent-test-designer"
RUN = "RUN-20260915-014"
RM_AID = store.load(store.requirements_path(SID, SV))["source_artifact_id"]
OLD = "TC-CASHFLOW-031"

def sr(loc, q=""): return {"spec_id": SID, "spec_version": SV, "location": loc, "quote": q[:300]}
def envelope(t, payload, refs, task="T1"):
    aid = ids.artifact_id(t); art = {"artifact_id": aid, "artifact_type": t, "schema_version": "1.0", "version": 1, "run_id": RUN, "task_id": task, "iteration": 0,
           "created_by": A, "created_at": store.now(), "status": "DRAFT", "source": {"type": "TestCaseVersion", "ids": []},
           "references": refs, "requires_approval": None, "payload": payload}
    p = store.ROOT / "artifacts" / "test-design" / RUN / f"{aid}.yaml"; store.save(p, art); return aid, p

tc = {
    "draft_id": f"TC-DRAFT-{ids.ulid()}", "title": "req-cashout 已建立 PENDING 後機台 15 秒逾時結束程序，該 PENDING 不會自動結束，需新請求取代或人工出金連動取消",
    "product": "ba-admin", "functional_area": AREA,
    "requirement_ids": ["REQ-CASHFLOW-026"], "acceptance_criteria_ids": ["AC-CASHFLOW-0261"],
    "spec_id": SID, "spec_version": SV, "test_level": "api", "test_types": ["negative"], "design_techniques": ["error_guessing"],
    "priority": "high", "risk": "medium", "execution_mode": "manual",
    "preconditions": ["機台已透過憑證通過認證", "機台所屬場館為開通狀態，機台為啟用狀態"],
    "test_data": [],
    "steps": [
        {"n": 1, "action": "機台送出 req-cashout，平台已建立 PENDING"},
        {"n": 2, "action": "機台 15 秒內未收到回覆，直接結束程序（不印收據）"},
        {"n": 3, "action": "檢視該筆 PENDING 的狀態"},
    ],
    "expected_result": "該 PENDING 持續停留在待確認，不會自動結束；需靠新的 req-cashout（依 REQ-CASHFLOW-019 取代）或櫃檯對該機台帳號執行人工出金（依 REQ-CASHFLOW-027 連動取消既有 PENDING）才能收斂——交易紀錄查詢頁不存在手動取消操作，已由 Oscar 2026-09-15 確認（CLR-CASHFLOW-004）",
    "expected_result_spec_reference": sr("§附錄-出金", "須由新的 req-cashout 取代或 Admin 手動取消收斂（spec.md原文，2026-09-15已由Oscar確認「Admin手動取消」此路徑不存在於現行產品，見REQ-CASHFLOW-026 statement/CLR-CASHFLOW-004）"),
    "assumptions": [], "automation_status": "not_automated", "ci_eligible": False, "hotfix_eligible": True,
    "execution_cost": "medium", "stability": "unknown", "critical_path": False, "source": "change_workflow",
    "supersedes_testcase": {"testcase_id": OLD, "version": 1},
    "design_rationale": "原版斷言「Admin手動取消」是收斂路徑之一，已由 Oscar 2026-09-15 確認此操作不存在於交易紀錄查詢頁，改為實際存在的兩條路徑：新請求取代、人工出金連動取消",
}
rep = {"mode": "change", "testcase_draft_artifact_id": None,
       "coverage_matrix": [{"requirement_id": "REQ-CASHFLOW-026", "draft_ids": [tc["draft_id"]],
                             "acceptance_criteria": [{"ac_id": "AC-CASHFLOW-0261", "draft_ids": [tc["draft_id"]]}]}],
       "uncovered_with_reason": [], "technique_summary": [{"technique": "error_guessing", "count": 1}],
       "self_check": {k: True for k in ["requirements_covered", "acceptance_criteria_covered", "negative_considered", "boundary_considered", "expected_results_traceable", "no_unsupported_assumptions", "duplicate_detection_completed"]},
       "assumptions": [], "duplicate_check": {"against_registry": True, "findings": []}}
refs = [{"entity_type": "Requirement", "id": "REQ-CASHFLOW-026"}, {"entity_type": "TestCase", "id": OLD}, {"entity_type": "Artifact", "id": RM_AID}]
did, p1 = envelope("TestCaseDraft", {"mode": "change", "spec_id": SID, "spec_version": SV, "testcases": [tc]}, refs)
rep["testcase_draft_artifact_id"] = did
_, p2 = envelope("TestDesignReport", rep, [{"entity_type": "Artifact", "id": did}])
print(p1.relative_to(store.ROOT)); print(p2.relative_to(store.ROOT))
