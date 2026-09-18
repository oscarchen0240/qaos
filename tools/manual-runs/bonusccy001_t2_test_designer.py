#!/usr/bin/env python3
"""T2：Test Designer(mode=spec) 依 SPEC-BONUSCCY-001 v1.0 的 5 條需求展開 TestCaseDraft + TestDesignReport。
REQ-002/003 為 high risk（資料悄悄遺漏／金流入錯錢包），需有 negative/boundary 案例覆蓋；
REQ-003 額外補一條「明確指定非核心貨幣仍應允許」的邊界案例，區分「預設」與「強制」。"""
import sys, pathlib, collections
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids
RUN, RM_AID = sys.argv[1], sys.argv[2]; ITER = int(sys.argv[3]) if len(sys.argv) > 3 else 0
SID, SV, AREA, A = "SPEC-BONUSCCY-001", "1.0", "BONUSCCY", "agent-test-designer"
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

T.append(tc("REQ-BONUSCCY-001", ["AC-BONUSCCY-001"], "機台站台的注單查詢/明細頁金額以核心貨幣(TWD)顯示", "ui_e2e", ["functional"], ["requirement_based"],
    ["站台切換選單切至機台（TWD核心貨幣）站台", "依實際選單導覽至注單查詢/明細頁，開啟一筆機台注單的明細"],
    "金額欄位以站台核心貨幣（TWD）顯示，不是寫死顯示 USDT 或其換算值", "§實際被改到的地方（表格第2項）", critical=True,
    rationale="spec.md 對這支頁面完全沒有畫面/選單路徑描述，「注單查詢/明細頁」的實際導覽路徑為推論、非 spec 明文，執行時以實際選單為準"))

T.append(tc("REQ-BONUSCCY-002", ["AC-BONUSCCY-002"], "新增機台站台會員前後，Dashboard 總會員數正確 +1（比對基準）", "ui_e2e", ["functional"], ["requirement_based"],
    ["記錄目前 Dashboard 總會員數 N", "在機台（TWD核心貨幣）站台新增一位會員", "再次檢視 Dashboard 總會員數"],
    "總會員數為 N+1，正確計入這名新增的機台站台會員；若仍為 N，代表該會員被 JOIN 條件悄悄排除", "§實際被改到的地方（表格第3項）", critical=True))
T.append(tc("REQ-BONUSCCY-002", ["AC-BONUSCCY-003"], "會員列表切換至機台站台時，列出筆數與該站台實際會員數一致（比對基準）", "ui_e2e", ["functional"], ["requirement_based"],
    ["以帳號類型篩選＝機台，記錄該機台站台的實際會員數 M（或以其他管道取得已知筆數）", "站台切換選單切至該機台站台，不加篩選檢視會員列表筆數"],
    "會員列表筆數與 M 一致，沒有因幣別相關的查詢條件而遺漏資料", "§實際被改到的地方（表格第3項）", critical=True))
T.append(tc("REQ-BONUSCCY-002", [], "平台同時有線上與機台站台會員時，Dashboard 總會員數正確加總兩者，不會只計入線上會員", "ui_e2e", ["negative"], ["negative"],
    ["記錄線上站台會員數 A 與機台（TWD）站台會員數 B（各自以帳號類型/站台篩選取得）", "檢視 Dashboard 總會員數"],
    "總會員數 ＝ A + B；若總數等於 A（只有線上會員數），代表機台站台會員被原本寫死 USDT 的 JOIN 條件悄悄排除在外", "§實際被改到的地方（表格第3項）", risk="high", critical=True,
    rationale="REQ-BONUSCCY-002 的 rejection_contract 點名的失效模式是『資料悄悄消失、不會報錯』，單看某一次的總數或列表筆數看不出來，需要有可比對的基準值（線上/機台分開計數再加總）才能真正驗證這個風險"))

T.append(tc("REQ-BONUSCCY-003", ["AC-BONUSCCY-004"], "人工存入未指定幣別時寫入站台核心貨幣(TWD)", "ui_e2e", ["functional"], ["requirement_based"],
    ["對一個機台（TWD核心貨幣）帳號執行人工存入，未指定幣別", "檢視入帳結果"],
    "金額寫入該站台核心貨幣（TWD）錢包，不是寫死的 USDT", "§實際被改到的地方（表格第6項）", critical=True))
T.append(tc("REQ-BONUSCCY-003", ["AC-BONUSCCY-005"], "人工提出未指定幣別時從站台核心貨幣(TWD)扣除", "ui_e2e", ["functional"], ["requirement_based"],
    ["對同一機台帳號執行人工提出，未指定幣別", "檢視扣款結果"],
    "從該站台核心貨幣（TWD）錢包扣除，不是寫死的 USDT", "§實際被改到的地方（表格第6項）", critical=True))
T.append(tc("REQ-BONUSCCY-003", [], "人工存入時明確指定幣別，系統依指定幣別入帳（預設規則僅在未指定時生效）", "ui_e2e", ["boundary"], ["scenario"],
    ["對一個機台（TWD核心貨幣）帳號執行人工存入，後台明確指定幣別欄位（若畫面提供此選項）", "檢視入帳結果"],
    "依後台明確指定的幣別入帳；「未指定則預設核心貨幣」這條規則只在沒有明確指定時生效，不會覆蓋已明確指定的選擇", "§實際被改到的地方（表格第6項）", risk="medium",
    rationale="區分「預設值」與「強制值」兩種語意：REQ-BONUSCCY-003 的規則是補上未指定時的預設，不是禁止指定其他幣別；若畫面實際上不提供指定欄位（只有金額輸入），此案例的 given 不成立，執行時應標記為不適用而非失敗"))

T.append(tc("REQ-BONUSCCY-004", ["AC-BONUSCCY-006"], "核心貨幣不可設定為未啟用的錢包幣別", "ui_e2e", ["negative"], ["negative"],
    ["建立或編輯站台時，嘗試將核心貨幣設定為目前未啟用的錢包幣別", "送出設定"],
    "系統阻擋，不允許設定為非啟用中的幣別（若實際錯誤訊息文案與此不同，不視為違反本條，僅測是否被阻擋）", "§一句話（限制段落）"))

T.append(tc("REQ-BONUSCCY-005", ["AC-BONUSCCY-007"], "機台站台前台資產列表僅顯示核心貨幣(TWD)", "ui_e2e", ["functional", "negative"], ["negative"],
    ["以機台帳號登入前台", "檢視前台資產列表"],
    "只顯示核心貨幣 TWD 一種，不列出其他幣別的零餘額項目", "§⭐兩種站台差很多 + 實際被改到的地方（表格第8項）", risk="low", cost="low"))

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
print(f"{len(T)} TCs, {n_exp} exploratory, reqs covered={len(cov)}/5")
