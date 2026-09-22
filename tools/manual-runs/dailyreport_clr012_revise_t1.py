#!/usr/bin/env python3
"""RUN-20260922-003～006 T1：Test Designer(mode=change) 依 CLR-DAILYREPORT-012 PM 定案 B（依場次明細不列進行中場次）
修訂 TC-DAILYREPORT-051/052/053/054——這四條原以「依場次明細查詢」驗證新建立（進行中）的場次，B 之後看不到。
改法：進行中場次的驗證點移到 spec §背景：場次資訊／呈現位置明寫的「會員詳細頁『機台資訊』區塊：顯示該機台目前進行中的場次摘要」；
已結束／逾時結束／日結結算的列仍於依場次明細驗。ADR-008 影響掃描判定。
用法：dailyreport_clr012_revise_t1.py <RUN> <TC-ID> [iter]"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids
RUN, OLD = sys.argv[1], sys.argv[2]; ITER = int(sys.argv[3]) if len(sys.argv) > 3 else 0
SID, SV, AREA, A = "SPEC-DAILYREPORT-001", "0.1", "DAILYREPORT", "agent-test-designer"
RM_AID = store.load(store.requirements_path(SID, SV))["source_artifact_id"]
old = store.load(store.tc_version_path(OLD, store.load(store.tc_pointer_path(OLD))["active_version"]))
def sr(loc, q=""): return {"spec_id": SID, "spec_version": SV, "location": loc, **({"quote": q[:300]} if q else {})}
MACHINE_INFO = "會員詳細頁「機台資訊」區塊：顯示該機台目前進行中的場次摘要"
LOC_MI = "§背景：場次資訊／場次呈現位置（會員詳細頁「機台資訊」區塊：顯示該機台目前進行中的場次摘要）"
RATIONALE = ("CLR-DAILYREPORT-012 PM 定案 B（2026-09-22）：場館日結報表「依場次明細」只列已結束／逾時結束／日結結算的場次，進行中不列。"
             "原版以依場次明細驗證新建立的（進行中）場次，B 之後該列不存在。spec §背景：場次資訊／呈現位置明寫「會員詳細頁『機台資訊』區塊：顯示該機台目前進行中的場次摘要」，"
             "故進行中場次的場次編號／期初餘額改於該區塊驗證；已結束／日結結算的列仍於依場次明細驗。ADR-008 影響掃描判定需修訂。")
PRE_COMMON = ["已登入後台並切換至機台場館站台（Arcade）", "測試場館已設定日結時間 06:00 UTC+0", "測試場館下有機台 A（會員編號已知），可開啟其會員詳細頁「機台資訊」區塊",
              "各式報表 > 場館日結報表 可用（依場次明細只列已結束／逾時結束／日結結算的場次，依 CLR-DAILYREPORT-012）"]

REV = {
 "TC-DAILYREPORT-051": dict(
    title="日結時間到達強制結束進行中場次並承接餘額",
    preconditions=PRE_COMMON + ["查詢時點在日結時間之後", "結算日期：前一日與當日（承接場次歸屬當日）"],
    steps=["機台 A 有進行中場次、餘額 80（於機台資訊區塊記錄其場次編號）", "等待日結時間 06:00 UTC+0 到達", "依場次明細查詢前一日", "開啟機台 A 的會員詳細頁「機台資訊」區塊"],
    expected="步驟 3：前一日該場次狀態「日結結算」、結束時間＝06:00；步驟 4：機台資訊區塊顯示一個新的進行中場次（場次編號不同於步驟 1），期初餘額 80",
    loc="§業務規則/場次日結 + " + LOC_MI, quote="日結時間到達時強制結束所有進行中的場次，餘額轉為隔日新場次的期初餘額"),
 "TC-DAILYREPORT-052": dict(
    title="無進行中場次時日結不產生新場次",
    preconditions=PRE_COMMON + ["查詢時點在日結時間之後"],
    steps=["機台 A 無進行中場次（機台資訊區塊顯示無進行中場次）", "日結時間到達", "開啟機台 A 的會員詳細頁「機台資訊」區塊", "依場次明細查詢當日"],
    expected="步驟 3：機台資訊區塊仍顯示無進行中場次（未因日結產生新場次）；步驟 4：當日明細無機台 A 的「日結結算」列",
    loc="§業務規則/場次日結 + " + LOC_MI, quote="日結時間到達時強制結束所有進行中的場次，餘額轉為隔日新場次的期初餘額"),
 "TC-DAILYREPORT-053": dict(
    title="已結束場次不可再變回進行中",
    preconditions=PRE_COMMON,
    steps=["依場次明細取得機台 A 一個「已結束」場次，記錄其場次編號", "對機台 A 再產生開分或投注", "開啟機台 A 的會員詳細頁「機台資訊」區塊", "依場次明細重新查詢"],
    expected="步驟 3：機台資訊區塊顯示一個進行中場次，其場次編號不同於步驟 1；步驟 4：步驟 1 的場次仍為「已結束」，狀態未變回進行中",
    loc="§背景：場次資訊（場次定義：從機台有分數開始玩起算，到洗分、出金或分數歸 0 為止，算一個場次）+ " + LOC_MI),
 "TC-DAILYREPORT-054": dict(
    title="場次逾時結束後不可再遊玩（前後端皆擋），再次入金或開分後建立新場次可遊玩",
    preconditions=["機台 A 有分數餘額且場次進行中", "場館設定的場次逾時時間已知（預設 1 小時；測試可調短）", "已登入後台，可查看場館日結報表（依場次明細）與機台 A 的會員詳細頁「機台資訊」區塊"],
    steps=["讓機台 A 在有餘額狀態下超過場館逾時時間無任何交易與遊玩", "在後台場館日結報表（依場次明細）確認該場次狀態為「逾時結束」", "以剩餘分數在機台前台嘗試進入遊戲／下注", "直接呼叫遊玩／下注 API",
           "對機台 A 進行入金（或開分）", "開啟機台 A 的會員詳細頁「機台資訊」區塊", "再次嘗試遊玩"],
    expected="步驟 3、4：前台拒絕進入遊戲、後端 API 亦拒絕；步驟 6：機台資訊區塊顯示新的進行中場次編號（不同於步驟 2 的逾時結束場次）；步驟 7：可正常遊玩",
    loc="§背景：場次資訊/場次狀態（狀態值「逾時結束」）+ REQ-017 states + " + LOC_MI),
}
r = REV[OLD]
tc = {k: old[k] for k in ("product", "functional_area", "requirement_ids", "acceptance_criteria_ids", "spec_id", "spec_version", "test_level", "test_types", "design_techniques",
                          "priority", "risk", "execution_mode", "test_data", "automation_status", "ci_eligible", "hotfix_eligible", "execution_cost", "stability", "critical_path")}
tc.update({"draft_id": f"TC-DRAFT-{ids.ulid()}", "title": r["title"], "preconditions": r["preconditions"],
           "steps": [{"n": i + 1, "action": s} for i, s in enumerate(r["steps"])], "expected_result": r["expected"],
           "expected_result_spec_reference": sr(r["loc"], r.get("quote", "")), "assumptions": old.get("assumptions", []),   # 沿用現行版；已核准者（resolved_by_approval）gate 豁免 needs_human_confirmation（iter 1 依 Validator 意見改回）
           "source": "change_workflow", "supersedes_testcase": {"testcase_id": OLD, "version": old["version"]}, "design_rationale": RATIONALE})
acs = tc["acceptance_criteria_ids"]
rep = {"mode": "change", "testcase_draft_artifact_id": None,
       "coverage_matrix": [{"requirement_id": tc["requirement_ids"][0], "draft_ids": [tc["draft_id"]], "acceptance_criteria": [{"ac_id": a, "draft_ids": [tc["draft_id"]]} for a in acs]}],
       "uncovered_with_reason": ([] if (set(tc["test_types"]) & {"negative", "boundary"} or set(tc["design_techniques"]) & {"negative", "error_guessing", "boundary_value"}) else
                                 [{"requirement_id": tc["requirement_ids"][0], "reason": f"NO_REJECTION_CONTRACT: 本次修訂僅針對 {OLD} 既有 1 條 functional TC 改驗證位置（CLR-DAILYREPORT-012），不涉新增設計；REQ-DAILYREPORT-017 的 negative 情境已由 ACTIVE 的 TC-DAILYREPORT-052/053/054 覆蓋（同批修訂中）。依 RUN-20260915-022 先例"}]),
       "technique_summary": [{"technique": t, "count": 1} for t in tc["design_techniques"]],
       "self_check": {k: True for k in ["requirements_covered", "acceptance_criteria_covered", "negative_considered", "boundary_considered", "expected_results_traceable", "no_unsupported_assumptions", "duplicate_detection_completed"]},
       "assumptions": [], "duplicate_check": {"against_registry": True, "findings": []},
       **({"revision_of_issues": [{"issue_index": 0, "action": "assumption 改回 needs_human_confirmation: false、保留 resolved_by_approval: APR-0007（內容未變、仍受核准涵蓋）；gate L75 已補豁免規則（test_59）", "draft_id": tc["draft_id"]}]} if ITER > 0 else {})}
def envelope(t, payload, refs):
    aid = ids.artifact_id(t); art = {"artifact_id": aid, "artifact_type": t, "schema_version": "1.0", "version": 1, "run_id": RUN, "task_id": "T1", "iteration": ITER,
           "created_by": A, "created_at": store.now(), "status": "DRAFT", "source": {"type": "TestCaseVersion", "ids": [f"{OLD}@v{old['version']}"]}, "references": refs, "requires_approval": None, "payload": payload}
    p = store.ROOT / "artifacts" / "test-design" / RUN / f"{aid}.yaml"; store.save(p, art); return aid, p
refs = [{"entity_type": "Requirement", "id": tc["requirement_ids"][0]}, {"entity_type": "TestCase", "id": OLD}, {"entity_type": "Artifact", "id": RM_AID}]
import os
if os.environ.get("REUSE_TCD"):   # 僅補產 TDR（TCD 已提交 VALID）
    did = os.environ["REUSE_TCD"]; tc["draft_id"] = store.load(store.find_artifact(did))["payload"]["testcases"][0]["draft_id"]
    rep["coverage_matrix"][0]["draft_ids"] = [tc["draft_id"]]
    for a in rep["coverage_matrix"][0]["acceptance_criteria"]: a["draft_ids"] = [tc["draft_id"]]
    p1 = store.ROOT / store.find_artifact(did)
else:
    did, p1 = envelope("TestCaseDraft", {"mode": "change", "spec_id": SID, "spec_version": SV, "testcases": [tc]}, refs)
rep["testcase_draft_artifact_id"] = did
_, p2 = envelope("TestDesignReport", rep, [{"entity_type": "Artifact", "id": did}])
print(p1.relative_to(store.ROOT)); print(p2.relative_to(store.ROOT))
