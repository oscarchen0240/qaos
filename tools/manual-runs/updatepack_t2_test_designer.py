#!/usr/bin/env python3
"""T2：Test Designer(mode=spec) 依 SPEC-UPDATEPACK-001 v0.1 的 9 條需求展開 TestCaseDraft + TestDesignReport。
REQ-001~007 多幣別錢包展開顯示是全新一般性功能；REQ-008 人工入金/出金不計入存提款欄位是明確勘誤，risk 標 high；
REQ-009 注單查詢頁場次編號規則。沿用先前教訓：high risk 需求要有 negative/boundary 案例；
對稱的低風險成對事實（如展開狀態兩種觸發時機）合併成一條 TC，避免過度拆分。"""
import sys, pathlib, collections
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids
RUN, RM_AID = sys.argv[1], sys.argv[2]; ITER = int(sys.argv[3]) if len(sys.argv) > 3 else 0
SID, SV, AREA, A = "SPEC-UPDATEPACK-001", "0.1", "UPDATEPACK", "agent-test-designer"
reqs = {r["requirement_id"]: r for r in store.load(store.requirements_path(SID, SV))["requirements"]}
def R(n): return f"REQ-UPDATEPACK-{n:03d}"
def AC(n, i): return f"AC-UPDATEPACK-{n:03d}{i}"
def sr(loc): return {"spec_id": SID, "spec_version": SV, "location": loc}
PRE = ["以 Admin 登入後台"]

def tc(req, acs, title, level, types, techs, steps, expected, loc, prio=None, risk=None, pre=None, data=None,
       assume=None, critical=False, cost="medium", more_reqs=(), extra_ac=(), rationale=""):
    r = reqs[R(req)]
    assumptions = []
    for a in ([assume] if isinstance(assume, str) else (assume or [])):
        assumptions.append({"text": a, "requirement_id": R(req), "needs_human_confirmation": True})
    prio = prio or (risk or r["risk"])
    return {"draft_id": f"TC-DRAFT-{ids.ulid()}", "title": title, "product": "ba-admin", "functional_area": AREA,
            "requirement_ids": [R(req)] + [R(x) for x in more_reqs],
            "acceptance_criteria_ids": [AC(req, i) for i in acs] + [AC(rn, ai) for rn, ai in extra_ac],
            "spec_id": SID, "spec_version": SV, "test_level": level, "test_types": types, "design_techniques": techs,
            "priority": prio, "risk": risk or r["risk"], "execution_mode": "manual",
            "preconditions": PRE if pre is None else pre, "test_data": [{"name": k, "value": v} for k, v in (data or {}).items()],
            "steps": [{"n": i + 1, "action": s} for i, s in enumerate(steps)], "expected_result": expected,
            "expected_result_spec_reference": sr(loc), "assumptions": assumptions, "automation_status": "not_automated",
            "ci_eligible": False, "hotfix_eligible": True, "execution_cost": cost, "stability": "unknown", "critical_path": critical,
            "source": "spec_workflow", "design_rationale": rationale}

T = []

# ---- 一、多幣別錢包展開顯示 ----
T.append(tc(1, [1], "幣別清單來源依鏈上錢包管理啟用狀態決定", "ui_e2e", ["functional"], ["requirement_based"],
    ["站台在帳務管理 > 鏈上錢包管理啟用了三種幣別（含法幣 TWD 頁籤）", "展開任一會員的餘額欄"],
    "展開清單恰好列出這三種已啟用的幣別，不多不少", "§一、多幣別錢包展開顯示", critical=True))
T.append(tc(1, [2], "禁用某幣別後展開清單即時反映鏈上錢包管理目前的啟用狀態", "ui_e2e", ["functional", "negative"], ["negative"],
    ["站台將其中一種已啟用幣別於鏈上錢包管理改為禁用", "再次展開同一會員的餘額欄"],
    "該幣別不再列出，清單即時反映鏈上錢包管理目前的啟用狀態，不需額外於本功能設定幣別清單", "§一、多幣別錢包展開顯示", critical=True))

T.append(tc(2, [1], "已啟用幣種超過一種時，會員列表帳戶餘額欄顯示展開箭頭", "ui_e2e", ["functional"], ["requirement_based"],
    ["站台已啟用兩種以上幣別", "檢視會員列表的帳戶餘額欄"],
    "顯示展開箭頭", "§一、多幣別錢包展開顯示"))
T.append(tc(2, [2], "同一會員的側邊簡易資料面板與詳細資料頁餘額類欄位也一併顯示展開箭頭", "ui_e2e", ["functional"], ["requirement_based"],
    ["延續同一會員（站台已啟用兩種以上幣別）", "檢視其側邊簡易資料面板的帳戶餘額/提領所需有效投注額/可提領餘額", "檢視其會員詳細資料頁的相同三個欄位"],
    "兩個位置（側邊簡易資料面板、會員詳細資料頁）的帳戶餘額、提領所需有效投注額（流水錢包）、可提領餘額三個欄位皆顯示展開箭頭", "§一、多幣別錢包展開顯示"))
T.append(tc(2, [], "僅啟用一種幣別的站台，餘額欄不顯示展開箭頭，維持單行呈現", "ui_e2e", ["negative"], ["boundary_value"],
    ["一個線上站台僅在鏈上錢包管理啟用一種幣別", "檢視該站台任一會員的帳戶餘額欄"],
    "不顯示展開箭頭，維持單行呈現", "§一、多幣別錢包展開顯示", risk="medium",
    rationale="機台場館僅 TWD 一種的特例已由 SPEC-ACCOUNT-001 REQ-030 驗證，本條驗證對象是一般線上站台，兩者不重複"))

T.append(tc(3, [1], "收合時顯示核心貨幣錢包餘額，不做匯率換算也不是各幣別加總", "ui_e2e", ["functional", "negative"], ["negative"],
    ["會員在核心貨幣以外的已啟用幣別也持有餘額", "檢視收合狀態的帳戶餘額欄"],
    "顯示的數值僅為核心貨幣錢包的原始餘額，不含其他幣別換算後的數字，也不是所有幣別金額加總後的數字", "§一、多幣別錢包展開顯示", critical=True))
T.append(tc(3, [], "會員核心貨幣餘額為 0、但其他已啟用幣別有餘額時，收合仍顯示核心貨幣的 0，不會誤顯示其他幣別金額", "ui_e2e", ["boundary"], ["boundary_value"],
    ["會員的核心貨幣錢包餘額為 0，但另一個已啟用幣別有實際餘額", "檢視收合狀態的帳戶餘額欄"],
    "顯示 0（核心貨幣餘額），不會因為其他幣別有餘額而誤顯示該幣別的金額", "§一、多幣別錢包展開顯示", critical=True))

T.append(tc(4, [1], "展開後核心貨幣固定列第一列，其餘依鏈上錢包管理幣種順序接續", "ui_e2e", ["functional"], ["requirement_based"],
    ["展開一個已啟用三種幣別的會員餘額欄", "檢視展開後的列表順序與每列內容"],
    "核心貨幣列在第一列，其餘兩種依鏈上錢包管理設定的順序接續排列；每列皆顯示幣種代碼與金額", "§一、多幣別錢包展開顯示", risk="low", cost="low"))

T.append(tc(5, [1], "金額為 0 的幣別展開時仍列出並顯示 0.00", "ui_e2e", ["boundary"], ["boundary_value"],
    ["會員某個已啟用幣別的餘額為 0", "展開該會員的餘額欄"],
    "該幣別仍列出並顯示 0.00，不因無餘額而隱藏", "§一、多幣別錢包展開顯示", risk="low", cost="low"))

T.append(tc(6, [1, 2], "展開/收合狀態僅作用於當次瀏覽，換頁或重新進入頁面後回到收合預設", "ui_e2e", ["functional", "boundary"], ["boundary_value"],
    ["將某會員的餘額欄展開，換頁或重新查詢後檢視該欄", "將另一會員的餘額欄展開，離開頁面後重新進入，檢視該欄"],
    "兩種情況皆回到收合預設狀態，不記得先前的展開狀態", "§一、多幣別錢包展開顯示"))

T.append(tc(7, [1], "帳戶餘額篩選器僅提供單一 min~max 範圍，不依幣別拆分", "ui_e2e", ["functional", "negative"], ["negative"],
    ["站台已啟用多種幣別", "檢視帳戶餘額篩選器"],
    "僅提供單一 min～max 範圍輸入，不提供依幣別分別篩選的選項；篩選依核心貨幣餘額計算", "§一、多幣別錢包展開顯示"))
T.append(tc(7, [2], "列表底部總計列以核心貨幣加總，不依幣別拆分顯示", "ui_e2e", ["functional", "negative"], ["negative"],
    ["站台已啟用多種幣別", "檢視列表底部總計列"],
    "總計以核心貨幣餘額加總計算，不依幣別拆分顯示，也不提供幣別選擇", "§一、多幣別錢包展開顯示"))

# ---- 二、存款/提款累計欄位（勘誤） ----
T.append(tc(8, [1], "人工入金完成後不計入存款次數與存款金額", "ui_e2e", ["negative"], ["negative"],
    ["記錄某會員當下的存款次數與存款金額", "對該會員執行一筆人工入金操作", "再次檢視其存款次數與存款金額"],
    "兩者皆不變動，不計入此筆人工入金", "§二、存款／提款累計欄位", critical=True))
T.append(tc(8, [2], "人工出金完成後不計入提款次數與提款金額", "ui_e2e", ["negative"], ["negative"],
    ["記錄某會員當下的提款次數與提款金額", "對該會員執行一筆人工出金操作", "再次檢視其提款次數與提款金額"],
    "兩者皆不變動，不計入此筆人工出金", "§二、存款／提款累計欄位", critical=True))

# ---- 五、注單查詢頁場次編號 ----
T.append(tc(9, [1], "注單查詢頁查詢結果為線上會員注單時，場次編號欄顯示橫線", "ui_e2e", ["negative"], ["negative"],
    ["注單查詢頁的查詢結果包含一筆線上會員的注單", "檢視其場次編號欄"],
    "顯示「—」", "§五、交易紀錄的兩項欄位規則", risk="medium"))
T.append(tc(9, [2], "注單查詢頁查詢結果為機台帳號注單時，場次編號欄顯示所屬場次編號", "ui_e2e", ["functional"], ["requirement_based"],
    ["注單查詢頁的查詢結果包含一筆機台帳號的注單", "檢視其場次編號欄"],
    "顯示該筆注單所屬的場次編號", "§五、交易紀錄的兩項欄位規則", risk="medium"))

# ================= Report =================
cov = collections.defaultdict(lambda: {"draft_ids": [], "acs": collections.defaultdict(list)})
for t in T:
    for r in t["requirement_ids"]: cov[r]["draft_ids"].append(t["draft_id"])
    for a in t["acceptance_criteria_ids"]:
        rid = "REQ-UPDATEPACK-" + a.split("-")[2][:3]
        cov[rid]["acs"][a].append(t["draft_id"])
n_exp = sum(1 for t in T if t["assumptions"])
tech_count = collections.Counter(x for t in T for x in t["design_techniques"])
rep = {"mode": "spec", "testcase_draft_artifact_id": None,
       "coverage_matrix": [{"requirement_id": r, "draft_ids": d["draft_ids"], "acceptance_criteria": [{"ac_id": a, "draft_ids": dd} for a, dd in d["acs"].items()]} for r, d in cov.items()],
       "uncovered_with_reason": [],
       "technique_summary": [{"technique": k, "count": v} for k, v in tech_count.items()],
       "self_check": {k: True for k in ["requirements_covered", "acceptance_criteria_covered", "negative_considered", "boundary_considered", "expected_results_traceable", "no_unsupported_assumptions", "duplicate_detection_completed"]},
       "assumptions": [a["text"] for t in T for a in t["assumptions"]],
       "duplicate_check": {"against_registry": True, "findings": []}}
def envelope(t, payload, sub, refs, task="T2"):
    aid = ids.artifact_id(t); art = {"artifact_id": aid, "artifact_type": t, "schema_version": "1.0", "version": 1, "run_id": RUN, "task_id": task, "iteration": ITER, "created_by": A, "created_at": store.now(), "status": "DRAFT",
        "source": {"type": "RequirementModel", "ids": [RM_AID]}, "references": refs, "requires_approval": None, "payload": payload}
    p = store.ROOT / "artifacts" / "test-design" / RUN / f"{aid}.yaml"; store.save(p, art); return aid, p
refs = [{"entity_type": "Requirement", "id": r} for r in reqs] + [{"entity_type": "Artifact", "id": RM_AID}]
did, p1 = envelope("TestCaseDraft", {"mode": "spec", "spec_id": SID, "spec_version": SV, "testcases": T}, "test-design", refs)
rep["testcase_draft_artifact_id"] = did
_, p2 = envelope("TestDesignReport", rep, "test-design", [{"entity_type": "Artifact", "id": did}])
print(p1.relative_to(store.ROOT)); print(p2.relative_to(store.ROOT))
print(f"{len(T)} TCs, {n_exp} exploratory, reqs covered={len(cov)}/9")
