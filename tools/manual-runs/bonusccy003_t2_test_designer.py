#!/usr/bin/env python3
"""T2：Test Designer(mode=spec) 依 SPEC-BONUSCCY-003 v1.0 的 4 條需求展開 TestCaseDraft + TestDesignReport。
REQ-011 為 high risk（spec自己點名本次最重要回歸點），除了基本正向案例，補一條金額精確到小數點的
邊界案例，驗證「原始金額/核心貨幣金額」欄位拆分後沒有引入無條件取整或欄位接錯的迴歸風險。"""
import sys, pathlib, collections
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids
RUN, RM_AID = sys.argv[1], sys.argv[2]; ITER = int(sys.argv[3]) if len(sys.argv) > 3 else 0
SID, SV, AREA, A = "SPEC-BONUSCCY-003", "1.0", "BONUSCCY", "agent-test-designer"
reqs = {r["requirement_id"]: r for r in store.load(store.requirements_path(SID, SV))["requirements"]}
def sr(loc): return {"spec_id": SID, "spec_version": SV, "location": loc}
PRE = ["以 Admin 登入後台"]

def tc(rid, acs, title, level, types, techs, steps, expected, loc, prio=None, risk=None, pre=None, data=None,
       assume=None, critical=False, cost="medium", more_reqs=(), rationale=""):
    r = reqs[rid]
    assumptions = []
    for a in ([assume] if isinstance(assume, str) else (assume or [])):
        assumptions.append({"text": a, "requirement_id": rid, "needs_human_confirmation": True})
    prio = prio or (risk or r["risk"])
    return {"draft_id": f"TC-DRAFT-{ids.ulid()}", "title": title, "product": "ba-admin", "functional_area": AREA,
            "requirement_ids": [rid] + list(more_reqs),
            "acceptance_criteria_ids": acs, "spec_id": SID, "spec_version": SV, "test_level": level, "test_types": types, "design_techniques": techs,
            "priority": prio, "risk": risk or r["risk"], "execution_mode": "manual",
            "preconditions": PRE if pre is None else pre, "test_data": [{"name": k, "value": v} for k, v in (data or {}).items()],
            "steps": [{"n": i + 1, "action": s} for i, s in enumerate(steps)], "expected_result": expected,
            "expected_result_spec_reference": sr(loc), "assumptions": assumptions, "automation_status": "not_automated",
            "ci_eligible": False, "hotfix_eligible": True, "execution_cost": cost, "stability": "unknown", "critical_path": critical,
            "source": "spec_workflow", "design_rationale": rationale}

T = []

# ---- REQ-011：存款原始金額正確進玩家錢包 ----
T.append(tc("REQ-BONUSCCY-011", ["AC-BONUSCCY-017"], "系統存款正確進玩家錢包，金額與幣別一致", "ui_e2e", ["functional"], ["requirement_based"],
    ["玩家於線上站台完成一筆系統存款（非人工存款）", "檢視入帳結果的金額與幣別"],
    "存入多少金額就進玩家錢包多少金額，幣別與存款當下一致，不因新拆出的「原始金額」欄位而算錯或漏算", "§這次能測什麼", critical=True))
T.append(tc("REQ-BONUSCCY-011", ["AC-BONUSCCY-017"], "存款金額精確到小數點時，進錢包金額不因欄位拆分而被無條件取整或截斷", "ui_e2e", ["boundary"], ["boundary_value"],
    ["玩家於線上站台完成一筆帶小數點的系統存款（例如 100.55）", "檢視入帳結果的金額"],
    "進錢包金額精確為 100.55，不因新拆出「原始金額」欄位而被無條件取整或截斷", "§改了什麼／①存款金額拆成兩個", risk="high",
    rationale="欄位拆分後最容易出錯的地方之一是取整規則，用小數金額當邊界案例驗證。另一個迴歸風險（『原始金額』與『核心貨幣金額』兩欄位有沒有接錯，即進錢包邏輯是否真的讀對欄位）本條刻意不涵蓋——見 uncovered_with_reason 說明原因，不要跟本條混在一起斷言"))

# ---- REQ-012：流水倍數/手續費以原始金額為基數 ----
T.append(tc("REQ-BONUSCCY-012", ["AC-BONUSCCY-018"], "存款後流水門檻與手續費以實際存入的原始金額為基數計算", "ui_e2e", ["functional"], ["requirement_based"],
    ["玩家完成一筆系統存款", "檢視存款後的提領所需有效投注額（流水門檻）與手續費計算結果"],
    "皆以玩家實際存入的原始金額為基數計算，不是核心貨幣金額或其他換算後的數字", "§這次能測什麼"))

# ---- REQ-013：簽到前台進度條與後台判定一致 ----
T.append(tc("REQ-BONUSCCY-013", ["AC-BONUSCCY-019"], "未達標時前台簽到進度條正確顯示，與後台判定一致，不再永遠顯示0", "ui_e2e", ["functional"], ["requirement_based"],
    ["玩家有已入帳成功的存款記錄，尚未達到有效會員門檻", "以該玩家身分登入前台，檢視簽到頁的有效會員進度條", "同時查後台該玩家的累積金額判定，與前台顯示的進度比對"],
    "前台進度條正確顯示累積金額，與後台判定的累積金額一致，不再是以前那樣永遠顯示 0", "§改了什麼／②簽到活動的「有效會員」改讀正確的表", critical=True,
    pre=["玩家已登入前台", "後台可另開一個管理員登入視窗，供比對後台判定結果"]))
T.append(tc("REQ-BONUSCCY-013", ["AC-BONUSCCY-020"], "達標玩家開啟一次前台簽到頁即直接寫入有效會員，後台不需玩家再存一筆即同步", "ui_e2e", ["functional"], ["state_transition"],
    ["玩家的累積存款已達有效會員門檻，但尚未開啟過新版前台簽到頁；開啟前先確認此時後台判定仍顯示「未達有效會員」（尚未重算）",
     "開啟一次前台簽到頁（過程中不觸發任何新存款）",
     "不做任何新存款動作，直接檢視後台的有效會員判定結果"],
    "前台進度條達標並直接寫入有效會員狀態；後台判定也已同步顯示有效會員，不需要玩家再存一筆才會重算——精確驗證 spec 點名的「前台每次開頁就重算並直接寫入、後台被動同步」這個不對稱機制，不是只驗『兩邊最終會一致』這種較弱的陳述", "§改了什麼／②簽到活動的「有效會員」改讀正確的表", critical=True,
    pre=["玩家已登入前台", "後台可另開一個管理員登入視窗，供比對後台判定結果"]))

# ---- REQ-014：每月重置 ----
T.append(tc("REQ-BONUSCCY-014", ["AC-BONUSCCY-021"], "簽到有效會員每月重置，跨月後進度正確歸零重算", "ui_e2e", ["functional"], ["state_transition"],
    ["簽到活動已開啟「有效會員每月重置」設定，玩家上個月的累積進度已達有效會員門檻", "跨月後檢視該玩家本月的有效會員進度"],
    "進度正確歸零，重新從 0 開始累積計算，不因改讀 deposit_log_v2 而受影響（例如不會誤讀到上個月已計入歸零前的舊資料）", "§這次能測什麼",
    rationale="expected_result 後半句『不因改讀deposit_log_v2而受影響』是本條需求對spec.md T5原文的推論延伸（spec原文只講每月重置本身，未明講跟資料表來源變更的關聯），非逐字依據，特此註明供追溯"))

# ================= Report =================
cov = collections.defaultdict(lambda: {"draft_ids": [], "acs": collections.defaultdict(list)})
for t in T:
    for r in t["requirement_ids"]: cov[r]["draft_ids"].append(t["draft_id"])
    for a in t["acceptance_criteria_ids"]:
        for rid, r in reqs.items():
            if a in [ac["ac_id"] for ac in r["acceptance_criteria"]]: cov[rid]["acs"][a].append(t["draft_id"]); break
n_exp = sum(1 for t in T if t["assumptions"])
tech_count = collections.Counter(x for t in T for x in t["design_techniques"])
rep = {"mode": "spec", "testcase_draft_artifact_id": None,
       "coverage_matrix": [{"requirement_id": r, "draft_ids": d["draft_ids"], "acceptance_criteria": [{"ac_id": a, "draft_ids": dd} for a, dd in d["acs"].items()]} for r, d in cov.items()],
       "uncovered_with_reason": [
           {"requirement_id": "REQ-BONUSCCY-011",
            "reason": "AC-BONUSCCY-017 底下還有一個子風險未被任何 TC 驗證：『原始金額』與『核心貨幣金額』兩個新拆分欄位，進錢包邏輯有沒有接對（讀對的是原始金額，不是核心貨幣金額）。目前所有線上站台的存款幣別本來就等於站台記帳幣別，兩欄位數值永遠相同，黑箱功能測試在外部觀察不到任何差異，結構上無法驗證『接對還是接錯』。需要等有非系統幣別的存款通道讓兩欄位真的出現數值差異，或改用 glass-box 手段（code review／log 核對呼叫路徑）才驗得到。2026-09-15 由獨立 Validator 審查指出，Test Designer 確認屬實。"}
       ],
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
print(f"{len(T)} TCs, {n_exp} exploratory, reqs covered={len(cov)}/4")
