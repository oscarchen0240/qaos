#!/usr/bin/env python3
"""RUN-20260923-008(CASHFLOW-005)/009(CASHFLOW-035)/010(TXLOG-125)/011(TXLOG-146)/012(TXLOG-158) T1：
Test Designer(mode=change) 依 CLR-CASHFLOW-006 回覆 B（所有未成立原因一律不寫入交易紀錄）重寫五條 TC。
用法：clr006_revise_t1.py <RUN> [iter]"""
import sys, pathlib, collections
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids
RUN = sys.argv[1]; ITER = int(sys.argv[2]) if len(sys.argv) > 2 else 0
CFG = {
 "RUN-20260924-001": ("SPEC-CASHFLOW-001", "0.1", "TC-CASHFLOW-005"),
 "RUN-20260923-009": ("SPEC-CASHFLOW-001", "0.1", "TC-CASHFLOW-035"),
 "RUN-20260923-010": ("SPEC-TXLOG-001", "0.1", "TC-TXLOG-125"),
 "RUN-20260923-011": ("SPEC-TXLOG-001", "0.1", "TC-TXLOG-146"),
 "RUN-20260923-012": ("SPEC-TXLOG-001", "0.1", "TC-TXLOG-158"),
}
SID, SV, OLD = CFG[RUN]
A = "agent-test-designer"
RM_AID = store.load(store.requirements_path(SID, SV))["source_artifact_id"]
old = store.load(store.tc_version_path(OLD, store.load(store.tc_pointer_path(OLD))["active_version"]))
def sr(loc, q=""): return {"spec_id": SID, "spec_version": SV, "location": loc, **({"quote": q[:300]} if q else {})}
RATIONALE = ("CLR-CASHFLOW-006 回覆 B（2026-09-23）：所有未成立原因（額度上限、資料格式錯誤、機台停用/場館未開通、憑證失效、餘額不足）"
             "一律不寫入交易紀錄，理由與 CLR-CASHFLOW-005 一致——避免客戶端可輕易觸發的拒絕情境把資料庫灌爆。RM 已回寫，本 TC 依新規則修訂。ADR-008 影響掃描判定。")
COMMON_PRE_CF = ["機台已透過憑證通過認證", "機台所屬場館為開通狀態，機台為啟用狀態"]

if OLD == "TC-CASHFLOW-005":
    T = dict(title="開分加計後恰等於場館額度上限可成立；超過 1 單位則被拒絕，不寫入帳務異動、也不寫入交易紀錄",
      pre=COMMON_PRE_CF + ["調整場館額度上限為一已知值 A，另建構一筆已預留未入帳的入金 PENDING，使目前「全場館機台分數餘額合計＋已預留未入帳入金金額」恰為 A-100"],
      steps=["送出開分請求（req-keyin），金額 100，使「全場館機台分數餘額合計＋已預留未入帳入金金額＋本筆金額」恰等於額度上限 A", "確認回覆為 0-OK，分數正常增加，交易紀錄正常寫入",
             "再送出開分請求（req-keyin），金額 1，使加計後超過額度上限 A", "確認此筆的回覆、分數變化，並查詢交易紀錄（不篩選狀態）確認查無此筆"],
      expected="第一筆恰等於上限：成立，回 0-OK，分數正常增加，交易紀錄正常寫入；第二筆使合計超過上限：平台回 1-OVER LIMIT，機台畫面顯示失敗，分數不變、不寫入任何帳務異動，且查無此次拒絕的交易紀錄（CLR-CASHFLOW-006：額度上限不再屬於「其他未成立原因會留紀錄」，與餘額不足同一待遇）",
      acs=["AC-CASHFLOW-0041", "AC-CASHFLOW-0301", "AC-CASHFLOW-0302"], reqs=["REQ-CASHFLOW-004", "REQ-CASHFLOW-030"], level="api", types=["functional", "negative"], techs=["decision_table"])
elif OLD == "TC-CASHFLOW-035":
    T = dict(title="所有未成立原因（餘額不足、額度上限、資料格式錯誤、機台停用/場館未開通、憑證失效）一律不寫入交易紀錄",
      pre=COMMON_PRE_CF,
      steps=["洗分或出金因餘額不足被拒絕，查詢機台交易紀錄", "開分或入金因額度上限被拒絕，查詢機台交易紀錄",
             "交易請求 currency 與主站台核心貨幣不符（資料格式錯誤），查詢機台交易紀錄",
             "機台停用中送出任一交易請求，查詢機台交易紀錄", "機台憑證已失效送出任一交易請求，查詢機台交易紀錄"],
      expected="五種未成立原因，查詢機台交易紀錄皆查無此次拒絕的紀錄，僅收到對應狀態碼（依序 1-NO CREDITS／1-OVER LIMIT／6-BAD DATA/FORMAT／7-OUT OF SERVICE／9-OTHER ERROR）；分數皆未異動；「未成立」狀態不會出現在交易紀錄查詢中，五種原因待遇一致（CLR-CASHFLOW-006）",
      acs=["AC-CASHFLOW-0301", "AC-CASHFLOW-0302"], reqs=["REQ-CASHFLOW-030"], level="api", types=["negative"], techs=["decision_table"])
elif OLD == "TC-TXLOG-125":
    T = dict(title="查詢範圍擴充後，機台交易的待確認/取消/逾時皆會列出；未成立不會列出",
      pre=["站台內有一筆機台開分已完成、一筆入金待確認、一筆出金已取消、一筆入金已逾時、一筆開分因額度上限被拒絕（未成立）"],
      steps=["不篩選狀態，檢視查詢結果的總筆數與各筆狀態"],
      expected="僅列出四筆：已完成、待確認、已取消、已逾時；因額度上限被拒絕的那筆（未成立）不會出現在結果中（CLR-CASHFLOW-006：所有未成立原因皆不寫入交易紀錄）",
      acs=["AC-TXLOG-0011"], reqs=["REQ-TXLOG-001"], level="api", types=["functional", "boundary"], techs=["requirement_based"])
elif OLD == "TC-TXLOG-146":
    T = dict(title="交易因額度上限被拒絕時，不會出現在交易紀錄查詢中（與餘額不足待遇一致）",
      pre=[],
      steps=["一筆交易因額度上限被平台拒絕（req-cashin 建立 PENDING 後 end-cashin 依實際清點金額判定超限）", "查詢交易紀錄（不篩選狀態），檢視是否有對應紀錄"],
      expected="查無此筆交易，不會以「未成立」狀態或任何其他狀態出現在列表中；分數未異動（CLR-CASHFLOW-006：額度上限與餘額不足待遇一致，皆不寫入紀錄，比照 TC-TXLOG-147）",
      acs=["AC-TXLOG-0161"], reqs=["REQ-TXLOG-016"], level="api", types=["negative"], techs=["scenario"])
else:  # TXLOG-158
    T = dict(title="未成立原因欄僅未成立狀態顯示內容（AC-0231 正向分支因未成立不再出現而無法驗證，本次僅驗負向分支）",
      pre=[],
      steps=["檢視一筆狀態為已完成的交易，檢視其「未成立原因」欄"],
      expected="未成立原因欄不顯示內容（顯示「—」）——因所有未成立原因皆不寫入交易紀錄（CLR-CASHFLOW-006），「未成立」狀態實務上不會出現，AC-TXLOG-0231（未成立狀態顯示拒絕原因文字）的正向情境無法以黑箱測試建立前置條件，本 TC 僅覆蓋 AC-TXLOG-0232",
      acs=["AC-TXLOG-0232"], reqs=["REQ-TXLOG-023"], level="api", types=["negative"], techs=["scenario"])

tc = {k: old[k] for k in ("product", "functional_area", "spec_id", "spec_version", "execution_mode", "test_data", "automation_status",
                          "ci_eligible", "hotfix_eligible", "execution_cost", "stability", "critical_path", "priority", "risk")}
tc.update({"draft_id": f"TC-DRAFT-{ids.ulid()}", "title": T["title"], "requirement_ids": T["reqs"], "acceptance_criteria_ids": T["acs"],
           "test_level": T.get("level", old["test_level"]), "test_types": T.get("types", old["test_types"]), "design_techniques": T.get("techs", old["design_techniques"]),
           "preconditions": T["pre"], "steps": [{"n": i + 1, "action": s} for i, s in enumerate(T["steps"])], "expected_result": T["expected"],
           "expected_result_spec_reference": sr(f"{SID} v{SV}（依 RM 回寫，2026-09-23 依 CLR-CASHFLOW-006；spec.md 正本待更新）"),
           "assumptions": old.get("assumptions", []), "source": "change_workflow",
           "supersedes_testcase": {"testcase_id": OLD, "version": old["version"]}, "design_rationale": RATIONALE})
cnt = collections.Counter(tc["design_techniques"])
rm = store.load(store.requirements_path(SID, SV)); owner = {a["ac_id"]: r["requirement_id"] for r in rm["requirements"] for a in r["acceptance_criteria"]}
cov = {}
for rid in tc["requirement_ids"]: cov[rid] = {"requirement_id": rid, "draft_ids": [tc["draft_id"]], "acceptance_criteria": []}
for aid in tc["acceptance_criteria_ids"]: cov.setdefault(owner[aid], {"requirement_id": owner[aid], "draft_ids": [tc["draft_id"]], "acceptance_criteria": []})["acceptance_criteria"].append({"ac_id": aid, "draft_ids": [tc["draft_id"]]})
unc = []
if OLD == "TC-TXLOG-158":
    unc = [{"requirement_id": "REQ-TXLOG-023", "reason": "AC-TXLOG-0231（未成立狀態顯示拒絕原因文字）無法建立前置條件：所有未成立原因皆不寫入交易紀錄（CLR-CASHFLOW-006），該狀態實務上不會出現。零覆蓋，規則本身仍有效"}]
rep = {"mode": "change", "testcase_draft_artifact_id": None, "coverage_matrix": list(cov.values()), "uncovered_with_reason": unc,
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
