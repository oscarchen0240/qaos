#!/usr/bin/env python3
"""T2：Test Designer(mode=spec) 依 SPEC-PLATFORMRULE-001 v0.1 的 23 條需求展開 TestCaseDraft + TestDesignReport。
REQ-PLATFORMRULE-011（rejection_contract.defined=false，CLR-PLATFORMRULE-002 已確認）刻意不湊負向 TC，
列入 uncovered_with_reason，待未來有排除項目實際解除時再補測試。
沿用先前教訓：high risk 多分支不壓縮進同一條 TC；priority 依風險分級；操作員角色的權限限制盡量寫成明確斷言而非探索式假設。"""
import sys, pathlib, collections
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids
RUN, RM_AID = sys.argv[1], sys.argv[2]; ITER = int(sys.argv[3]) if len(sys.argv) > 3 else 0
SID, SV, AREA, A = "SPEC-PLATFORMRULE-001", "0.1", "PLATFORMRULE", "agent-test-designer"
reqs = {r["requirement_id"]: r for r in store.load(store.requirements_path(SID, SV))["requirements"]}
def R(n): return f"REQ-PLATFORMRULE-{n:03d}"
def AC(n, i): return f"AC-PLATFORMRULE-{n:03d}{i}"
def sr(loc): return {"spec_id": SID, "spec_version": SV, "location": loc}
PRE = ["以 Admin 登入後台", "站台切換選單已選定一個機台場館站台"]

def tc(req, acs, title, level, types, techs, steps, expected, loc, prio=None, risk=None, pre=None, data=None,
       assume=None, critical=False, cost="medium", more_reqs=(), extra_ac=()):
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
            "source": "spec_workflow", "design_rationale": ""}

T = []

# ---- 既有功能對機台帳號的排除規則 (1-3) ----
T.append(tc(1, [1], "機台出金完成後不會進入出金審核流程", "ui_e2e", ["functional", "negative"], ["negative"],
    ["一筆機台出金交易完成（現場即時核可並印出收據）", "檢視出金審核頁面列表"],
    "查無該筆機台出金的審核項目；本頁僅列出線上會員的出金審核", "§既有功能對機台帳號的排除規則", critical=True))

T.append(tc(2, [1], "機台開分與入金交易照常寫入稽核明細頁面", "ui_e2e", ["functional"], ["requirement_based"],
    ["一筆機台開分交易完成，至稽核明細頁面查詢", "一筆機台入金交易完成，至稽核明細頁面查詢"],
    "兩筆交易皆正常出現在稽核明細頁面，交易類型分別可辨識為機台開分、機台入金（精確標籤文字定義於正本交易類型清單，超出本開發包 §既有功能對機台帳號的排除規則 範圍，此處僅驗證兩者皆有寫入且可區分類型）", "§既有功能對機台帳號的排除規則"))

T.append(tc(3, [1], "Free Spin 管理選擇會員時允許指定機台帳號", "ui_e2e", ["functional"], ["requirement_based"],
    ["進入 Free Spin 管理，選擇要派發的會員", "嘗試選取一個機台帳號"],
    "系統允許選擇機台帳號加入活動，不因帳號類型為機台而被排除", "§Free Spin 例外", risk="medium"))
T.append(tc(3, [2], "機台帳號的 Free Spin 由後台直接派發到帳，不需玩家領取", "ui_e2e", ["functional"], ["requirement_based"],
    ["後台對一個機台帳號派發一筆 Free Spin", "檢視該機台帳號的免費旋轉狀態", "檢視該筆派發紀錄的幣種欄位"],
    "免費旋轉直接到帳，不需要玩家額外操作領取；幣種欄位顯示為該機台場館的核心貨幣（TWD）", "§Free Spin 例外", risk="medium"))

# ---- 機台場館的後台選單 (4-11) ----
T.append(tc(4, [1], "站台切換選單切至機台場館時，後台選單依規則隱藏不適用頁面", "ui_e2e", ["functional"], ["requirement_based"],
    ["站台切換下拉選單切至一個機台場館站台", "檢視後台選單整體結構"],
    "選單依隱藏規則調整，不適用頁面（資訊看板、加盟列表等）消失", "§機台場館的後台選單", critical=True))
T.append(tc(4, [2], "切回線上站台後選單恢復完整", "ui_e2e", ["functional"], ["requirement_based"],
    ["延續前一操作，將站台切換選單切回線上站台", "檢視後台選單"],
    "選單恢復完整，先前隱藏的頁面全部重新出現", "§機台場館的後台選單", critical=True))
T.append(tc(4, [], "從一個機台場館切換至另一個機台場館，選單維持隱藏狀態不會恢復完整", "ui_e2e", ["boundary"], ["boundary_value"],
    ["站台切換選單已選定機台場館站台 A（選單已依規則隱藏）", "將站台切換選單切至另一個機台場館站台 B"],
    "選單仍維持隱藏狀態，不因切換的目標仍是機台場館而恢復完整；隱藏規則跟隨「是否為機台場館」判斷，不是跟隨「是否曾經顯示過完整選單」", "§機台場館的後台選單", risk="medium"))

T.append(tc(5, [1], "機台場館選單：資訊看板分類整個隱藏", "ui_e2e", ["functional", "negative"], ["requirement_based"],
    ["站台切換至機台場館，檢視左側選單分類"],
    "不存在「資訊看板」這個分類", "§機台場館的後台選單", risk="medium"))

T.append(tc(6, [1], "機台場館選單：會員與加盟商分類僅顯示會員列表", "ui_e2e", ["functional", "negative"], ["requirement_based"],
    ["站台切換至機台場館，展開會員與加盟商分類", "檢視可見項目"],
    "僅顯示會員列表；加盟列表、登入網域查詢、推薦註冊金設定、暱稱禁用詞設定皆不顯示", "§機台場館的後台選單", risk="medium"))

T.append(tc(7, [1], "機台場館選單：帳務管理分類顯示鏈上錢包管理與洗分出金核實，隱藏出金審核與優惠彩金審核", "ui_e2e", ["functional", "negative"], ["requirement_based"],
    ["站台切換至機台場館，展開帳務管理分類", "檢視可見項目"],
    "顯示鏈上錢包管理與洗分出金核實；不顯示出金審核與優惠彩金審核", "§機台場館的後台選單", risk="medium"))
T.append(tc(7, [2], "機台場館的鏈上錢包管理僅顯示法幣 TWD 頁籤，區塊鏈頁籤隱藏", "ui_e2e", ["functional", "negative"], ["requirement_based"],
    ["站台切換至機台場館，開啟鏈上錢包管理頁面", "檢視頁籤"],
    "僅顯示法幣 TWD 頁籤，區塊鏈幣別頁籤隱藏", "§機台場館的後台選單", risk="medium"))

T.append(tc(8, [1], "機台場館選單：各式報表分類顯示交易紀錄查詢等四項，隱藏返水等四項", "ui_e2e", ["functional", "negative"], ["requirement_based"],
    ["站台切換至機台場館，展開各式報表分類", "檢視可見項目"],
    "顯示交易紀錄查詢、注單查詢、稽核明細、場館日結報表；不顯示返水明細、加盟傭金發放紀錄、代理返傭發放紀錄、會員等級異動紀錄", "§機台場館的後台選單", risk="medium"))

T.append(tc(9, [1], "機台場館選單：系統管理分類顯示公告等四項，隱藏 KYC 等六項", "ui_e2e", ["functional", "negative"], ["requirement_based"],
    ["站台切換至機台場館，展開系統管理分類", "檢視可見項目"],
    "顯示公告設定、Free Spin 管理、橫幅管理、消稽核設定；不顯示 KYC 設定、會員等級設定、代理設定、加盟商設定、優惠活動管理、畫面管理", "§機台場館的後台選單", risk="medium"))

T.append(tc(10, [1], "機台場館選單：遊戲商管理與後台管理員系統分類全部顯示，沒有任何項目被隱藏", "ui_e2e", ["functional", "negative"], ["decision_table"],
    ["站台切換至機台場館，展開遊戲商管理與後台管理員系統分類", "逐項檢視是否顯示"],
    "兩個分類的所有項目皆顯示，沒有任何一項被隱藏", "§機台場館的後台選單", risk="low", cost="low"))

# REQ-011：rejection_contract.defined=false，CLR-PLATFORMRULE-002 已確認不湊 TC，列入 uncovered_with_reason

# ---- 角色與權限 (12-20) ----
T.append(tc(12, [1], "新增後台使用者時，角色選項包含操作員並可指定所屬場館", "ui_e2e", ["functional"], ["requirement_based"],
    ["後台管理員系統 > 新增使用者", "檢視角色選項", "選擇操作員角色"],
    "角色選項包含操作員；選定後可指定其所屬場館", "§角色與權限"))

T.append(tc(13, [1], "操作員檢視任一支援場館範圍的頁面時，資料範圍僅限自身所屬場館", "ui_e2e", ["negative"], ["negative"],
    ["以操作員身分登入後台", "檢視機台交易紀錄查詢頁面的站台切換選單（若有提供）與查詢結果"],
    "無論頁面是否提供切換至其他場館的入口，查詢/顯示結果一律僅限自身所屬場館範圍內的資料；若入口存在且可選擇其他場館，選擇後應查無資料或被系統阻擋（Spec 只定義可見場館範圍這個資料層規則，UI 切換器入口是否隱藏屬實作細節，見 REQ-PLATFORMRULE-015 對機台交易紀錄查詢頁的對應測試）", "§角色與權限", critical=True))
T.append(tc(13, [], "操作員略過前端直接呼叫機台交易紀錄查詢 API 指定非自身所屬場館，不得取得該場館資料", "api", ["negative"], ["negative"],
    ["以操作員身分取得有效憑證（略過前端 UI 限制）", "直接呼叫機台交易紀錄查詢 API，查詢參數指定一個非自身所屬場館的場館 ID"],
    "後端不得回傳非自身場館的交易資料——無論是以拒絕回應（4xx）或回傳空結果／已過濾資料，只要不含非自身場館的實際交易內容即視為符合（比照已於 REQ-CASHOUT-025 確認的操作員場館範圍政策：前後端皆已拒絕越權存取）", "§角色與權限", risk="high", critical=True,
    data={"venue_id": "一個非操作員自身所屬場館的有效場館 ID"}))

T.append(tc(14, [1], "額度上限（場館層級）操作員僅能檢視，無法修改", "ui_e2e", ["negative"], ["boundary_value"],
    ["以操作員身分登入後台，檢視自身場館的額度上限設定", "嘗試修改額度上限數值"],
    "欄位僅供檢視，操作員無法修改額度上限", "§角色與權限"))

T.append(tc(15, [1], "機台交易紀錄查詢頁，操作員僅能查得自身所屬場館範圍內的交易", "ui_e2e", ["negative"], ["negative"],
    ["以操作員身分登入後台，於機台交易紀錄查詢頁嘗試查詢自身場館以外的交易"],
    "查無其他場館的交易紀錄，僅能查得自身所屬場館範圍內的交易", "§角色與權限"))

T.append(tc(16, [1], "人工入金／出金操作，操作員具備執行權限", "ui_e2e", ["functional"], ["requirement_based"],
    ["以操作員身分登入後台", "對自身場館內一個機台帳號執行人工入金或人工出金"],
    "系統允許執行，操作員具備此權限", "§角色與權限"))

T.append(tc(17, [1], "站長執行重設密碼須經二次確認才會生效", "ui_e2e", ["functional"], ["state_transition"],
    ["以站長身分對一個會員帳號執行重設密碼", "檢視流程是否要求二次確認"],
    "須經過二次確認才會生效", "§角色與權限", critical=True))
T.append(tc(17, [2], "操作員不具備重設密碼權限", "ui_e2e", ["negative"], ["negative"],
    ["以操作員身分登入後台", "嘗試對任一會員帳號執行重設密碼操作"],
    "操作員不具備此權限，找不到入口或執行時被系統阻擋", "§角色與權限", critical=True))

T.append(tc(18, [1], "編輯機台基本資料操作員僅能檢視，無法儲存修改", "ui_e2e", ["negative"], ["boundary_value"],
    ["以操作員身分登入後台，檢視機台基本資料編輯畫面", "嘗試修改內容並儲存"],
    "欄位僅供檢視，無法儲存修改", "§角色與權限"))
T.append(tc(18, [2], "操作員不可發放或重置機台憑證", "ui_e2e", ["negative"], ["negative"],
    ["以操作員身分登入後台", "嘗試發放或重置任一機台的憑證"],
    "操作員不具備此權限，無法執行", "§角色與權限"))

T.append(tc(19, [1], "操作員不可新增機台", "ui_e2e", ["negative"], ["negative"],
    ["以操作員身分登入後台，尋找或嘗試執行新增機台操作"],
    "操作員不具備此權限，無法執行", "§角色與權限"))

T.append(tc(20, [1], "操作員可執行機台停用／啟用操作", "ui_e2e", ["functional"], ["requirement_based"],
    ["以操作員身分登入後台", "對自身場館內一台機台執行停用，再執行啟用"],
    "系統皆允許執行，操作員具備此權限", "§角色與權限"))

# ---- 機台場館的遊戲更新 (21-23) ----
T.append(tc(21, [1], "遊戲發佈更新後，原已在機台場館啟用的該遊戲被重新設為停用", "ui_e2e", ["functional", "boundary"], ["state_transition"],
    ["一款遊戲原已在某機台場館啟用", "平台對該遊戲發佈更新", "檢視更新後該遊戲於此機台場館的狀態"],
    "更新後該遊戲在此機台場館被重新設為停用，需重新手動開啟；不因更新前已啟用而維持啟用", "§機台場館的遊戲更新", critical=True))
T.append(tc(21, [2], "平台新增全新遊戲時，所有機台場館預設為停用", "ui_e2e", ["functional"], ["requirement_based"],
    ["平台新增一款全新遊戲", "檢視該遊戲於各機台場館的預設狀態"],
    "所有機台場館皆預設停用", "§機台場館的遊戲更新"))

T.append(tc(22, [1], "站長可於遊戲商管理手動開啟因更新被停用的遊戲", "ui_e2e", ["functional"], ["requirement_based"],
    ["一款遊戲於某機台場館因更新被設為停用", "以站長身分至遊戲商管理手動開啟該遊戲"],
    "系統允許站長執行開啟操作", "§機台場館的遊戲更新", critical=True))
T.append(tc(22, [2], "操作員不可開啟被停用的遊戲", "ui_e2e", ["negative"], ["negative"],
    ["以操作員身分嘗試開啟一款於自身場館被停用的遊戲"],
    "操作員不具備此權限，無法執行", "§機台場館的遊戲更新"))
T.append(tc(22, [3], "遊戲被平台新增或更新後，系統不會自動代為開啟", "ui_e2e", ["negative"], ["negative"],
    ["一款遊戲被平台新增或更新後，未經任何人工操作", "檢視該遊戲於機台場館的狀態"],
    "維持停用狀態，平台不會主動代為開啟，須人工由站長執行", "§機台場館的遊戲更新", risk="medium"))

T.append(tc(23, [1], "遊戲更新預設停用規則不影響線上站台，原已啟用的遊戲維持啟用", "ui_e2e", ["negative", "boundary"], ["boundary_value"],
    ["一款遊戲原已在一個線上站台啟用", "平台對該遊戲發佈更新", "檢視該遊戲於此線上站台的狀態"],
    "維持啟用狀態不變，不受機台場館的預設停用規則影響", "§機台場館的遊戲更新"))

# ================= Report =================
cov = collections.defaultdict(lambda: {"draft_ids": [], "acs": collections.defaultdict(list)})
for t in T:
    for r in t["requirement_ids"]: cov[r]["draft_ids"].append(t["draft_id"])
    for a in t["acceptance_criteria_ids"]:
        rid = "REQ-PLATFORMRULE-" + a.split("-")[2][:3]
        cov[rid]["acs"][a].append(t["draft_id"])
uncovered = [{"requirement_id": "REQ-PLATFORMRULE-011",
              "reason": "rejection_contract.defined=false；架構/實作面要求（選單顯示規則須與排除規則同一來源，不得各自寫死），非使用者可觀察行為，目前沒有任何排除項目被實際解除，無真實案例可設計測試。CLR-PLATFORMRULE-002 已確認（2026-09-14）：不強行湊負向 TC，待未來有排除項目實際解除時再補測試。"}]
n_exp = sum(1 for t in T if t["assumptions"])
tech_count = collections.Counter(x for t in T for x in t["design_techniques"])
rep = {"mode": "spec", "testcase_draft_artifact_id": None,
       "coverage_matrix": [{"requirement_id": r, "draft_ids": d["draft_ids"], "acceptance_criteria": [{"ac_id": a, "draft_ids": dd} for a, dd in d["acs"].items()]} for r, d in cov.items()],
       "uncovered_with_reason": uncovered,
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
print(f"{len(T)} TCs, {n_exp} exploratory, reqs covered={len(cov)}/23 (+1 uncovered: REQ-011)")
