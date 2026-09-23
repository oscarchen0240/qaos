#!/usr/bin/env python3
"""RUN-20260923-002（TC-CASHOUT-044）／003（TC-CASHOUT-085）T1：Test Designer(mode=change)
依 CLR-CASHOUT-002 回覆 A（洗分單階段、無待確認路徑）把 given 自洗分改為出金（兩階段）。
用法：cashout_clr002_revise_t1.py <RUN> [iter]"""
import sys, pathlib, collections
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids
RUN = sys.argv[1]; ITER = int(sys.argv[2]) if len(sys.argv) > 2 else 0
OLD = {"RUN-20260923-002": "TC-CASHOUT-044", "RUN-20260923-003": "TC-CASHOUT-085"}[RUN]
SID, SV, A = "SPEC-CASHOUT-001", "0.1", "agent-test-designer"
RM_AID = store.load(store.requirements_path(SID, SV))["source_artifact_id"]
old = store.load(store.tc_version_path(OLD, store.load(store.tc_pointer_path(OLD))["active_version"]))
RATIONALE = ("CLR-CASHOUT-002 回覆 A（2026-09-23）：機台洗分為單階段交易（req-keyout，帳務立即生效），不會停在「待處理／等待中」（＝待確認）；"
             "畫面篩選器上那兩個技術值係與「出鈔」共用同一組的結果，對洗分不適用。原版 given「洗分交易狀態為待確認」的情境不存在、前置條件無法建立。"
             "改用出金（兩階段：req-cashout 已核可但 end-cashout 完成回報未送達時會停在待確認，見 SPEC-CASHFLOW-001 出金段），"
             "RM 的 AC-CASHOUT-0041 given 已同步自洗分改為出金。ADR-008 影響掃描判定需修訂。")
COMMON_PRE = ["以 Admin 登入後台", "進入 帳務管理 > 洗分出金核實，站台切換選單已選定一個機台場館站台",
              "已取得一筆機台出金交易，其於機台交易紀錄的交易狀態為「待確認」（技術值待處理／等待中；即 req-cashout 已核可、end-cashout 完成回報未送達，分數尚未扣除）"]
REV = {
 "TC-CASHOUT-044": dict(
    title="尚未完成的出金交易本身沒有核實狀態，不會出現在本頁",
    steps=["於機台交易紀錄確認該筆出金的交易狀態為待確認（尚未完成），記下其機台帳號與交易時間",
           "回到本頁，以該機台帳號查詢（本頁沒有交易狀態欄位或篩選器，只有核實狀態）"],
    expected=("查無此筆紀錄，因為該筆交易尚未完成、系統根本不會為它建立核實狀態紀錄；不可憑本頁無紀錄直接判斷交易已完成，"
              "須至機台交易紀錄查明實際的交易狀態。（機台洗分不適用本案：洗分為單階段交易，不會停在待確認，其未完成路徑僅有未成立，見 CLR-CASHOUT-002）")),
 "TC-CASHOUT-085": dict(
    title="尚未完成（待確認）的出金交易，系統不會為其建立核實紀錄",
    steps=["取得（或使一筆）機台出金交易於機台交易紀錄的交易狀態為『待確認』（尚未完成）",
           "進入本頁，以該機台帳號或訂單編號查詢，確認是否有對應紀錄"],
    expected=("查無此筆紀錄；因為交易尚未完成，系統根本不會為它建立核實狀態紀錄。不可憑本頁無紀錄直接判斷交易狀態，"
              "須至機台交易紀錄查明實際狀態後再決定是否付款。（洗分為單階段交易、不會停在待確認，故本規則的待確認情境一律以出金驗證，見 CLR-CASHOUT-002）")),
}[OLD]
tc = {k: old[k] for k in ("product", "functional_area", "requirement_ids", "acceptance_criteria_ids", "spec_id", "spec_version", "test_level",
                          "test_types", "design_techniques", "priority", "risk", "execution_mode", "test_data", "automation_status",
                          "ci_eligible", "hotfix_eligible", "execution_cost", "stability", "critical_path")}
tc.update({"draft_id": f"TC-DRAFT-{ids.ulid()}", "title": REV["title"], "preconditions": COMMON_PRE,
           "steps": [{"n": i + 1, "action": s} for i, s in enumerate(REV["steps"])], "expected_result": REV["expected"],
           "expected_result_spec_reference": {"spec_id": SID, "spec_version": SV,
               "location": "§紀錄產生規則（「僅交易狀態為「已完成」的機台洗分與機台出金會出現在本頁；待確認、已取消、已逾時、未成立的交易不會出現」）；待確認情境改以出金驗證之依據為 CLR-CASHOUT-002 回覆 A 與 SPEC-CASHFLOW-001 §出金（「請求成功但完成回報未送達時，交易停在「待確認」」）"},
           "assumptions": old.get("assumptions", []), "source": "change_workflow",
           "supersedes_testcase": {"testcase_id": OLD, "version": old["version"]}, "design_rationale": RATIONALE})
cnt = collections.Counter(tc["design_techniques"])
cov = {}
for rid in tc["requirement_ids"]: cov[rid] = {"requirement_id": rid, "draft_ids": [tc["draft_id"]], "acceptance_criteria": []}
rm = store.load(store.requirements_path(SID, SV))
owner = {a["ac_id"]: r["requirement_id"] for r in rm["requirements"] for a in r["acceptance_criteria"]}
for aid in tc["acceptance_criteria_ids"]: cov[owner[aid]]["acceptance_criteria"].append({"ac_id": aid, "draft_ids": [tc["draft_id"]]})
rep = {"mode": "change", "testcase_draft_artifact_id": None, "coverage_matrix": list(cov.values()), "uncovered_with_reason": [],
       "technique_summary": [{"technique": k, "count": v} for k, v in cnt.items()],
       "self_check": {k: True for k in ["requirements_covered", "acceptance_criteria_covered", "negative_considered", "boundary_considered",
                                        "expected_results_traceable", "no_unsupported_assumptions", "duplicate_detection_completed"]},
       "assumptions": [], "duplicate_check": {"against_registry": True, "findings": []}}
def envelope(t, payload, refs):
    aid = ids.artifact_id(t); art = {"artifact_id": aid, "artifact_type": t, "schema_version": "1.0", "version": 1, "run_id": RUN, "task_id": "T1",
        "iteration": ITER, "created_by": A, "created_at": store.now(), "status": "DRAFT",
        "source": {"type": "TestCaseVersion", "ids": [f"{OLD}@v{old['version']}"]}, "references": refs, "requires_approval": None, "payload": payload}
    p = store.ROOT / "artifacts" / "test-design" / RUN / f"{aid}.yaml"; store.save(p, art); return aid, p
refs = [{"entity_type": "Requirement", "id": r} for r in tc["requirement_ids"]] + [{"entity_type": "TestCase", "id": OLD}, {"entity_type": "Artifact", "id": RM_AID}]
did, p1 = envelope("TestCaseDraft", {"mode": "change", "spec_id": SID, "spec_version": SV, "testcases": [tc]}, refs)
rep["testcase_draft_artifact_id"] = did
_, p2 = envelope("TestDesignReport", rep, [{"entity_type": "Artifact", "id": did}])
print(p1.relative_to(store.ROOT)); print(p2.relative_to(store.ROOT))
