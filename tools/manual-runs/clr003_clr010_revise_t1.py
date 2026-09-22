#!/usr/bin/env python3
"""RUN-20260922-007（TC-PLATFORMRULE-018 修訂 + REQ-024 兩條新 TC，依 CLR-PLATFORMRULE-003）
   RUN-20260922-008（TC-DAILYREPORT-036 修訂 + AC-0115 一條新 TC，依 CLR-DAILYREPORT-010）
Test Designer(mode=change)。新 TC 以 source_ref new_required:<CLR> 標示（先例 bonusccy004_revise_t1.py）。
用法：clr003_clr010_revise_t1.py <RUN> [iter]"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids
RUN = sys.argv[1]; ITER = int(sys.argv[2]) if len(sys.argv) > 2 else 0
A = "agent-test-designer"
CFG = {
 "RUN-20260922-007": dict(SID="SPEC-PLATFORMRULE-001", SV="0.1", AREA="PLATFORMRULE", OLD="TC-PLATFORMRULE-018", CLR="CLR-PLATFORMRULE-003"),
 "RUN-20260922-008": dict(SID="SPEC-DAILYREPORT-001", SV="0.1", AREA="DAILYREPORT", OLD="TC-DAILYREPORT-036", CLR="CLR-DAILYREPORT-010"),
}[RUN]
SID, SV, AREA, OLD, CLR = CFG["SID"], CFG["SV"], CFG["AREA"], CFG["OLD"], CFG["CLR"]
RM_AID = store.load(store.requirements_path(SID, SV))["source_artifact_id"]
old = store.load(store.tc_version_path(OLD, store.load(store.tc_pointer_path(OLD))["active_version"]))
def sr(loc, q=""): return {"spec_id": SID, "spec_version": SV, "location": loc, **({"quote": q[:300]} if q else {})}
BASE = {k: old[k] for k in ("product", "functional_area", "spec_id", "spec_version", "execution_mode", "automation_status", "ci_eligible", "hotfix_eligible", "execution_cost", "stability")}
def mk(title, reqs, acs, level, types, techs, pre, steps, expected, ref, prio="high", risk="high", critical=True, supersede=False, rationale="", test_data=None):
    d = dict(BASE, draft_id=f"TC-DRAFT-{ids.ulid()}", title=title, requirement_ids=reqs, acceptance_criteria_ids=acs, test_level=level, test_types=types, design_techniques=techs,
             priority=prio, risk=risk, preconditions=pre, test_data=test_data or [], steps=[{"n": i + 1, "action": s} for i, s in enumerate(steps)], expected_result=expected,
             expected_result_spec_reference=ref, assumptions=[], critical_path=critical, source="change_workflow", design_rationale=rationale)
    if supersede: d["supersedes_testcase"] = {"testcase_id": OLD, "version": old["version"]}
    else: d["source_ref"] = f"new_required:{CLR}_2026-09-22"
    return d

if RUN == "RUN-20260922-007":
    R = "CLR-PLATFORMRULE-003 PM 回覆（2026-09-22）：新需求，操作員可進入注單查詢與稽核明細；RM 已新增 REQ-PLATFORMRULE-024（AC-0241 可進入、AC-0242 限自身場館）。"
    T = [
      mk("操作員後台選單無「站台列表」項目，無法進入場館設定頁面，額度上限等欄位無從檢視或修改", ["REQ-PLATFORMRULE-014"], ["AC-PLATFORMRULE-0141"], "ui_e2e", ["negative"], ["negative"],
         ["以操作員身分登入後台", "站台切換選單已選定自身所屬的機台場館"],
         ["檢視後台左側選單，確認「站台列表」是否存在於選單中",
          "確認「會員與加盟商>會員列表」「帳務管理>洗分出金核實」「各式報表>交易紀錄查詢/注單查詢/稽核明細/場館日結報表」是否正常存在於選單中",
          "若嘗試直接以網址存取站台列表頁面，觀察系統反應"],
         "選單中沒有「站台列表」這個項目，因此無法進入場館設定頁面，該頁面內的額度上限（本 spec 原文欄位）與場次逾時時間（SPEC-ARCADE-001 正本定義的欄位，本 spec 原文未提及）皆無從檢視，更無法修改；會員列表、洗分出金核實、交易紀錄查詢、注單查詢、稽核明細、場館日結報表等操作員可操作項目正常存在於選單中，不受影響（若直接以網址嘗試存取站台列表頁面，若實際錯誤訊息/阻擋方式與選單消失不同，不視為違反本條，僅測是否被阻擋）",
         old["expected_result_spec_reference"], supersede=True,
         rationale=R + " 本條僅在步驟 2／expected 的操作員可用頁面列舉補入注單查詢與稽核明細（依 REQ-024），其餘與 v2 相同。"),
      mk("操作員後台選單含注單查詢與稽核明細，可進入並查詢", ["REQ-PLATFORMRULE-024"], ["AC-PLATFORMRULE-0241"], "ui_e2e", ["functional"], ["requirement_based"],
         ["以操作員身分登入後台", "站台切換選單已選定自身所屬的機台場館", "該場館已有至少一筆注單與一筆機台開分／入金交易（供稽核明細顯示）"],
         ["展開左側選單「各式報表」分類", "點擊「注單查詢」，以涵蓋既有注單的日期範圍查詢", "點擊「稽核明細」，以涵蓋既有交易的日期範圍查詢"],
         "各式報表分類含「注單查詢」與「稽核明細」兩項；兩頁皆可進入，查詢回傳自身場館的資料（注單查詢至少含該筆注單；稽核明細至少含該筆機台開分／入金）",
         sr("§角色與權限（權限表未列此兩頁；依 CLR-PLATFORMRULE-003 PM 回覆 2026-09-22 新增，見 RM REQ-PLATFORMRULE-024）"),
         rationale=R + " 正向：頁面存在且可查。spec 權限表尚未補列，依據為 CLR 定案（已落入 RM）。"),
      mk("操作員於注單查詢與稽核明細僅能查得自身所屬場館的資料", ["REQ-PLATFORMRULE-024", "REQ-PLATFORMRULE-013"], ["AC-PLATFORMRULE-0242", "AC-PLATFORMRULE-0131"], "ui_e2e", ["negative"], ["negative"],
         ["以操作員身分登入後台，其所屬場館為 A", "另一機台場館 B 有已知的注單與機台交易（會員編號已知）"],
         ["於注單查詢以場館 B 的會員編號查詢；若頁面提供站台／場館切換入口則嘗試切至 B", "於稽核明細以涵蓋場館 B 交易的日期範圍查詢；同上嘗試切換", "檢視兩頁查詢結果"],
         "兩頁皆查無場館 B 的資料，僅能查得場館 A 範圍內的注單與稽核明細；若切換入口存在且可選 B，選擇後應查無資料或被系統阻擋（Spec 只定義資料層可見範圍，切換入口是否隱藏屬實作細節）",
         sr("§角色與權限", "可見場館範圍 | 全部場館 | 自身站台及所有子站台下的場館 | 僅自身所屬場館"),
         rationale=R + " 反向：資料範圍依 REQ-013 通用規則限自身場館，比照 TC-PLATFORMRULE-016／019 對交易紀錄查詢的寫法。"),
    ]
    cov = [{"requirement_id": "REQ-PLATFORMRULE-014", "draft_ids": [T[0]["draft_id"]], "acceptance_criteria": [{"ac_id": "AC-PLATFORMRULE-0141", "draft_ids": [T[0]["draft_id"]]}]},
           {"requirement_id": "REQ-PLATFORMRULE-024", "draft_ids": [T[1]["draft_id"], T[2]["draft_id"]], "acceptance_criteria": [{"ac_id": "AC-PLATFORMRULE-0241", "draft_ids": [T[1]["draft_id"]]}, {"ac_id": "AC-PLATFORMRULE-0242", "draft_ids": [T[2]["draft_id"]]}]},
           {"requirement_id": "REQ-PLATFORMRULE-013", "draft_ids": [T[2]["draft_id"]], "acceptance_criteria": [{"ac_id": "AC-PLATFORMRULE-0131", "draft_ids": [T[2]["draft_id"]]}]}]
    unc = []
else:
    R = "CLR-DAILYREPORT-010 PM 定案 A（2026-09-22）：已兌現以收據日歸屬；RM REQ-011 已補 statement 並新增 AC-0115。"
    T = [
      mk("已兌現／未兌現收據金額拆分（皆以收據日歸屬）", ["REQ-DAILYREPORT-011"], ["AC-DAILYREPORT-0113"], "ui_e2e", ["functional"], ["requirement_based"],
         old["preconditions"],
         ["當日出金收據合計 200（可為多張），其中 150 於當日或之後任一日在洗分出金核實頁核銷", "以結算日期＝該日搜尋"],
         "該日列：已兌現 150、未兌現 50（歸屬依收據日，不受核銷是哪一天影響）",
         sr("§列表欄位/已兌現金額、未兌現金額（歸屬基準依 CLR-DAILYREPORT-010 A，見 RM REQ-011）"), critical=False, supersede=True,
         rationale=R + " 本條僅把核銷時點寫明（當日或之後皆可），expected 不變。"),
      mk("跨日兌現的收據歸屬收據日，不歸兌現日", ["REQ-DAILYREPORT-011"], ["AC-DAILYREPORT-0115"], "ui_e2e", ["functional"], ["boundary_value"],
         [p for p in old["preconditions"] if "結算日期預設" not in p and "無其他未兌現" not in p] + ["場館於 9/10 與 9/12 皆無其他出金收據"],
         ["9/10 機台 A 出金，印出收據 1000（當日不核銷）", "9/12 於洗分出金核實頁將該收據核銷（付現）", "以結算日期 9/10～9/12 按日搜尋"],
         "9/10 列：收據 1000、已兌現 1000、未兌現 0；9/12 列：收據 0、已兌現 0、未兌現 0（已兌現歸收據日 9/10，不出現在兌現日 9/12）",
         sr("§列表欄位/已兌現金額（CLR-DAILYREPORT-010 A：已兌現＝當日出金的收據中已核實者，不論付現日；RM AC-0115）"), critical=False,
         rationale=R + " 邊界：收據日與兌現日不同時的歸屬，是 A／B 兩種讀法的唯一分歧點。"),
    ]
    cov = [{"requirement_id": "REQ-DAILYREPORT-011", "draft_ids": [t["draft_id"] for t in T], "acceptance_criteria": [{"ac_id": "AC-DAILYREPORT-0113", "draft_ids": [T[0]["draft_id"]]}, {"ac_id": "AC-DAILYREPORT-0115", "draft_ids": [T[1]["draft_id"]]}]}]
    unc = []
import collections
cnt = collections.Counter(x for t in T for x in t["design_techniques"])
rep = {"mode": "change", "testcase_draft_artifact_id": None, "coverage_matrix": cov, "uncovered_with_reason": unc,
       "technique_summary": [{"technique": k, "count": v} for k, v in cnt.items()],
       "self_check": {k: True for k in ["requirements_covered", "acceptance_criteria_covered", "negative_considered", "boundary_considered", "expected_results_traceable", "no_unsupported_assumptions", "duplicate_detection_completed"]},
       "assumptions": [], "duplicate_check": {"against_registry": True, "findings": []}}
def envelope(t, payload, refs):
    aid = ids.artifact_id(t); art = {"artifact_id": aid, "artifact_type": t, "schema_version": "1.0", "version": 1, "run_id": RUN, "task_id": "T1", "iteration": ITER,
           "created_by": A, "created_at": store.now(), "status": "DRAFT", "source": {"type": "TestCaseVersion", "ids": [f"{OLD}@v{old['version']}"]}, "references": refs, "requires_approval": None, "payload": payload}
    p = store.ROOT / "artifacts" / "test-design" / RUN / f"{aid}.yaml"; store.save(p, art); return aid, p
refs = [{"entity_type": "Requirement", "id": r["requirement_id"]} for r in cov] + [{"entity_type": "TestCase", "id": OLD}, {"entity_type": "Artifact", "id": RM_AID}]
did, p1 = envelope("TestCaseDraft", {"mode": "change", "spec_id": SID, "spec_version": SV, "testcases": T}, refs)
rep["testcase_draft_artifact_id"] = did
_, p2 = envelope("TestDesignReport", rep, [{"entity_type": "Artifact", "id": did}])
print(p1.relative_to(store.ROOT)); print(p2.relative_to(store.ROOT))
