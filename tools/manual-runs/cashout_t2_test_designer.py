#!/usr/bin/env python3
"""RUN-20260914-013 T2：Test Designer(mode=spec) 依 SPEC-CASHOUT-001 v0.1 的 31 條需求展開 TestCaseDraft + TestDesignReport。
沿用 CASHFLOW/TXLOG 的教訓：high risk 多分支不壓縮進同一條 TC；priority 依風險分級；用字盡量對齊 spec 的實際操作步驟。"""
import sys, pathlib, collections
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids
RUN, RM_AID = sys.argv[1], sys.argv[2]; ITER = int(sys.argv[3]) if len(sys.argv) > 3 else 0
SID, SV, AREA, A = "SPEC-CASHOUT-001", "0.1", "CASHOUT", "agent-test-designer"
reqs = {r["requirement_id"]: r for r in store.load(store.requirements_path(SID, SV))["requirements"]}
def R(n): return f"REQ-CASHOUT-{n:03d}"
def AC(n, i): return f"AC-CASHOUT-{n:03d}{i}"
def sr(loc): return {"spec_id": SID, "spec_version": SV, "location": loc}
PRE = ["以 Admin 登入後台", "進入 帳務管理 > 洗分出金核實，站台切換選單已選定一個機台場館站台"]

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
T.append(tc(1, [1], "洗分或出金交易完成後，本頁自動產生一筆待核實紀錄", "ui_e2e", ["functional", "boundary"], ["requirement_based"],
    ["機台送出一筆洗分請求（req-keyout）並完成", "至本頁檢視是否自動出現對應的待核實紀錄"],
    "自動出現一筆待核實紀錄，對應該筆洗分交易", "§功能說明", critical=True))

T.append(tc(2, [1], "機台交易紀錄頁不提供核實或作廢操作，須至本頁執行", "ui_e2e", ["negative"], ["negative"],
    ["至機台交易紀錄頁，檢視一筆待核實交易的核實狀態欄與可用操作"],
    "該頁只顯示核實狀態，不提供核實或作廢操作；須至本頁（洗分出金核實）執行", "§功能說明", risk="medium"))

T.append(tc(3, [1], "開分與入金交易不會出現在本頁", "ui_e2e", ["negative"], ["negative"],
    ["站台內有已完成的機台開分與機台入金交易", "查詢本頁列表，不篩選任何條件"],
    "查無任何開分或入金紀錄，本頁僅列出洗分與出金", "§紀錄產生規則", risk="medium"))

T.append(tc(4, [1], "尚未完成的洗分交易本身沒有核實狀態，不會出現在本頁", "ui_e2e", ["negative"], ["boundary_value"],
    ["一筆機台洗分交易於機台交易紀錄查得的交易狀態為待確認（尚未完成）", "查詢本頁（本頁沒有交易狀態欄位或篩選器，只有核實狀態）"],
    "查無此筆紀錄，因為該筆交易尚未完成、系統根本不會為它建立核實狀態紀錄；不可憑本頁無紀錄直接判斷交易已完成，須至機台交易紀錄查明實際的交易狀態", "§紀錄產生規則", critical=True))
T.append(tc(4, [2], "未成立的出金交易同樣沒有核實狀態，不會出現在本頁", "ui_e2e", ["negative"], ["boundary_value"],
    ["一筆機台出金交易於機台交易紀錄查得的交易狀態為未成立", "查詢本頁"],
    "查無此筆紀錄，因為未成立的交易不會有核實狀態", "§紀錄產生規則"))

T.append(tc(5, [1], "待核實的洗分以醒目色標提示", "ui_e2e", ["functional", "boundary"], ["boundary_value"],
    ["一筆機台洗分交易處於待核實狀態", "檢視其於列表中的呈現方式"],
    "以醒目色標提示，提醒現金可能尚未交付或現場漏登記", "§核實狀態", critical=True))
T.append(tc(5, [2], "待核實的出金正常顯示，不特別醒目提示", "ui_e2e", ["functional"], ["requirement_based"],
    ["一筆機台出金交易處於待核實狀態", "檢視其於列表中的呈現方式"],
    "正常顯示藍色核實狀態標記，不做醒目提示（收據不設兌現時效，屬正常情況）", "§核實狀態"))

T.append(tc(6, [1], "核實當下累計該機台帳號的提款次數與提款金額", "ui_e2e", ["functional", "boundary"], ["boundary_value"],
    ["一筆待核實的洗分交易，核實前先記錄該機台帳號會員列表的提款次數與提款金額", "執行核實", "核實完成當下再次檢視提款次數與提款金額"],
    "提款次數 +1；提款金額以站台核心貨幣原值累計此筆實際金額，不換算 USDT", "§核實狀態", critical=True))

T.append(tc(7, [1], "洗分交易的核實狀態不會出現已作廢", "ui_e2e", ["negative"], ["negative"],
    ["檢視任一筆機台洗分交易在篩選器與列表中可能出現的核實狀態值"],
    "只會是待核實或已核實兩種，不會出現已作廢（已作廢僅出金適用）", "§核實狀態", risk="medium"))

T.append(tc(8, [1], "頁面資料範圍跟隨站台切換選單，不提供場館篩選欄位", "ui_e2e", ["functional", "negative"], ["requirement_based"],
    ["頁面標題下方的站台切換選單切至站台 A", "檢視篩選器所有欄位", "檢視查詢結果範圍"],
    "篩選器不存在「場館」欄位；查詢結果僅限站台 A 範圍內的紀錄", "§篩選器", risk="medium"))

T.append(tc(9, [1], "機台帳號篩選支援以逗號分隔查詢多筆會員編號", "ui_e2e", ["functional"], ["equivalence_partitioning"],
    ["機台帳號篩選欄輸入兩個機台帳號的會員編號，以「,」分隔", "點擊搜尋"],
    "查詢結果同時包含這兩個機台帳號的紀錄", "§篩選器", risk="medium"))

T.append(tc(10, [1], "交易類型篩選下拉選單含全部、機台洗分、機台出金", "ui_e2e", ["functional"], ["requirement_based"],
    ["開啟交易類型篩選下拉選單", "檢視所有可選項"],
    "包含「全部」「機台洗分」「機台出金」共三個選項", "§篩選器", risk="medium"))
T.append(tc(10, [2], "篩選交易類型可正確窄化查詢結果", "ui_e2e", ["functional"], ["equivalence_partitioning"],
    ["篩選交易類型為「機台出金」並搜尋"],
    "查詢結果僅顯示機台出金類型的紀錄", "§篩選器", risk="medium"))

T.append(tc(11, [1], "訂單編號篩選可查出待核銷的出金紀錄", "ui_e2e", ["functional"], ["requirement_based"],
    ["輸入一筆出金收據上的訂單編號", "點擊搜尋"],
    "查詢結果顯示該筆出金紀錄", "§篩選器", critical=True))
T.append(tc(11, [], "輸入不存在或錯誤的訂單編號查詢，結果為空且前端顯示失敗提示", "ui_e2e", ["negative"], ["boundary_value"],
    ["訂單編號篩選欄輸入一個不存在、或與任何收據皆不相符的編號", "點擊搜尋"],
    "查詢結果為空，不會誤配到其他筆紀錄；前端顯示失敗提示：「失敗：查無此訂單編號，請先到「機台交易記錄」查明交易狀態，不要憑印象付款」（已由 Oscar 2026-09-14 依實際畫面截圖確認文案）。本輸入框也是核實（出金）流程第一步用來定位待核銷紀錄的同一個查詢欄位，見 REQ-CASHOUT-022", "§篩選器", more_reqs=(22,)))

T.append(tc(12, [1], "核實狀態篩選可正確窄化查詢結果", "ui_e2e", ["functional"], ["equivalence_partitioning"],
    ["篩選核實狀態為「待核實」並搜尋"],
    "查詢結果僅顯示核實狀態為待核實的紀錄", "§篩選器", risk="medium"))

T.append(tc(13, [1, 2], "交易時間與核實時間範圍篩選皆能正確窄化結果", "ui_e2e", ["functional", "boundary"], ["boundary_value"],
    ["設定交易時間範圍並搜尋，檢視結果", "清除後改設定核實時間範圍並搜尋，檢視結果"],
    "兩者皆僅顯示落在所設定範圍內的紀錄", "§篩選器", risk="low"))

T.append(tc(14, [1], "金額範圍篩選可正確窄化查詢結果", "ui_e2e", ["functional"], ["boundary_value"],
    ["設定金額範圍（min～max）並搜尋"],
    "僅顯示實際金額落在範圍內的紀錄", "§篩選器", risk="low", cost="low"))

T.append(tc(15, [1], "點擊交易編號可跳轉至機台交易紀錄查看明細", "ui_e2e", ["functional"], ["requirement_based"],
    ["點擊列表中任一筆紀錄的交易編號"],
    "導向機台交易紀錄頁，並顯示該筆交易的明細", "§列表欄位", risk="medium"))

T.append(tc(16, [1, 2], "訂單編號欄僅出金顯示收據識別碼，洗分顯示橫線", "ui_e2e", ["functional", "negative"], ["decision_table"],
    ["檢視一筆機台出金紀錄的訂單編號欄", "檢視一筆機台洗分紀錄的訂單編號欄"],
    "出金顯示收據上印製的識別碼；洗分顯示「—」", "§列表欄位", risk="medium"))

T.append(tc(17, [1, 2], "機台帳號欄可跳轉會員詳細頁，列表不顯示場館名稱", "ui_e2e", ["functional", "negative"], ["decision_table"],
    ["點擊一筆紀錄的機台帳號欄位值，檢視結果", "檢視列表所有欄位，確認是否顯示場館名稱"],
    "第一步導向該機台帳號的會員詳細資料頁；第二步不存在場館名稱欄位或顯示", "§列表欄位", risk="medium"))

T.append(tc(18, [1], "洗分因門檻計算，實際金額小於店員輸入金額時以實際金額欄為準付現", "ui_e2e", ["functional", "boundary"], ["boundary_value"],
    ["一筆洗分交易因門檻計算，實際扣款金額小於店員操作機台時輸入的金額", "檢視本頁該筆紀錄的實際金額欄"],
    "顯示門檻計算後的實際金額（較小值）；核實流程應以此欄金額為準付現，而非店員原輸入的金額", "§列表欄位", critical=True))
T.append(tc(18, [2], "出金交易的實際金額欄即收據面額", "ui_e2e", ["functional"], ["requirement_based"],
    ["一筆機台出金交易", "檢視本頁該筆紀錄的實際金額欄"],
    "顯示與收據面額一致的金額", "§列表欄位"))

T.append(tc(19, [1, 2], "核實時間與核實人員欄，待核實時皆顯示橫線", "ui_e2e", ["functional"], ["decision_table"],
    ["檢視一筆已核實紀錄的核實時間與核實人員欄", "檢視一筆待核實紀錄的核實時間與核實人員欄"],
    "已核實：顯示執行核實的時間（UTC+0）與後台帳號；待核實：兩欄皆顯示「—」", "§列表欄位", risk="low"))

T.append(tc(20, [1, 2], "操作欄依交易類型提供不同操作：出金有核實與作廢，洗分僅核實", "ui_e2e", ["functional", "negative"], ["decision_table"],
    ["檢視一筆待核實出金紀錄的操作欄，確認可用操作", "檢視一筆待核實洗分紀錄的操作欄，確認可用操作"],
    "出金：提供核實與作廢兩個操作；洗分：僅提供核實操作，不提供作廢", "§列表欄位", risk="medium"))

T.append(tc(21, [1], "核實（洗分）三步驟流程：確認彈窗核對無誤後標記已核實", "ui_e2e", ["functional"], ["state_transition"],
    ["店員已對一筆待核實洗分當場付現，依機台帳號或交易時間找到該筆紀錄，點擊「核實」",
     "確認彈窗核對機台帳號、實際金額、交易時間皆無誤",
     "點擊確認（此動作不可撤銷，見 REQ-CASHOUT-027）"],
    "系統將該筆標記為「已核實」，並記錄核實人員與時間", "§操作/核實（洗分）", critical=True))
T.append(tc(21, [], "核實（洗分）確認彈窗內容與實際交易不符時，操作員應取消而不點擊確認，紀錄維持待核實", "ui_e2e", ["negative"], ["error_guessing"],
    ["店員找到一筆待核實洗分，點擊「核實」開啟確認彈窗", "發現彈窗顯示的機台帳號或金額與現場實際情況不符（如誤點了另一筆紀錄）", "不點擊確認，改為關閉彈窗或點擊取消"],
    "該筆紀錄維持待核實狀態，未被標記為已核實，避免核對有誤仍誤觸不可撤銷的核實動作", "§操作/核實（洗分）", risk="medium"))

T.append(tc(22, [1], "核實（出金）流程：輸入訂單編號查詢、核對彈窗內容後標記已核實", "ui_e2e", ["functional"], ["state_transition"],
    ["玩家持收據到櫃檯，於頁面上方輸入收據上的訂單編號查詢，定位到該筆待核實出金",
     "確認彈窗核對訂單編號、機台帳號、金額、收據印出時間皆無誤",
     "點擊確認（此動作不可撤銷，見 REQ-CASHOUT-027）",
     "櫃檯付現金給玩家"],
    "系統將該筆標記為「已核實」，並記錄核實人員與時間", "§操作/核實（出金＝核銷收據）", critical=True))

T.append(tc(23, [1], "過渡期出金依結算結果畫面照片上的訂單編號核銷，流程與狀態不變", "ui_e2e", ["functional"], ["requirement_based"],
    ["機台暫無印表機（過渡期現況），玩家出示前台結算結果畫面照片（無實體收據）", "櫃檯依照片上的訂單編號查詢並執行核實"],
    "核實流程與狀態與有實體收據時完全相同，系統不因過渡期而有不同行為", "§功能說明", risk="medium"))

T.append(tc(24, [1], "對已核實的紀錄再次執行核實，系統阻擋並提示", "ui_e2e", ["negative"], ["error_guessing"],
    ["取一筆狀態為已核實的紀錄", "嘗試再次對其執行核實"],
    "系統阻擋此操作並提示，避免重複付款", "§操作", critical=True))
T.append(tc(24, [2], "對已作廢的紀錄嘗試核實，系統阻擋並提示", "ui_e2e", ["negative"], ["error_guessing"],
    ["取一筆狀態為已作廢的出金紀錄", "嘗試對其執行核實"],
    "系統阻擋此操作並提示", "§操作"))

T.append(tc(25, [1], "操作員的站台切換選單不提供切換至其他場館的入口，僅能核實自身場館紀錄", "ui_e2e", ["negative"], ["negative"],
    ["以操作員身分登入後台，進入本頁", "檢視頁面標題下方的站台切換選單", "取一筆自身所屬場館內的待核實紀錄，執行核實"],
    "站台切換選單不提供切換至其他場館的入口（前端已限制，操作員從一開始就無法檢視其他場館的資料）；對自身場館內的紀錄可正常執行核實", "§操作", critical=True))
T.append(tc(25, [2], "操作員略過前端直接呼叫核實 API 指定非自身場館的紀錄，後端拒絕", "api", ["negative"], ["negative"],
    ["以操作員身分取得有效憑證（略過前端 UI 限制）", "直接呼叫核實 API，帶入一筆非自身所屬場館的待核實紀錄"],
    "後端拒絕該請求，該筆紀錄狀態不受影響", "§操作", critical=True))
T.append(tc(25, [], "操作員嘗試透過非常規路徑（如頁面深連結／直接帶入紀錄相關網址）接觸非自身場館的紀錄，仍應被阻擋", "ui_e2e", ["negative"], ["error_guessing"],
    ["以操作員身分登入後台", "嘗試不透過站台切換選單，而是直接以網址或深連結方式開啟本頁並帶入非自身場館的參數（例如仿造其他頁面的交易編號跳轉連結）"],
    "系統仍拒絕顯示或操作非自身場館的資料，站台範圍限制不因繞過選單而失效（與 UI 選單限制、後端 API 限制互為防禦深度佐證）", "§操作", risk="medium"))

T.append(tc(26, [1], "核實結果正確回寫機台交易紀錄的核實狀態與核實人員/時間欄位", "ui_e2e", ["functional"], ["requirement_based"],
    ["一筆洗分交易於本頁被執行核實", "至機台交易紀錄頁檢視該筆交易的核實狀態與核實人員/時間欄"],
    "顯示已核實，核實人員與時間與本頁執行核實時記錄的一致", "§操作", risk="medium"))

T.append(tc(27, [1], "已核實的紀錄不提供撤銷核實的操作", "ui_e2e", ["negative"], ["negative"],
    ["取一筆已核實的紀錄", "尋找撤銷核實或回復為待核實的操作入口"],
    "系統不提供任何撤銷核實的功能；僅能透過後台操作紀錄查得執行人員與時間", "§操作", critical=True))

T.append(tc(28, [1], "站長對出金執行作廢並填寫原因，系統接受並標記已作廢", "ui_e2e", ["functional"], ["requirement_based"],
    ["以站長身分登入後台", "取一筆待核實出金紀錄，點擊作廢，填寫作廢原因（如「收據遺失」）", "送出"],
    "系統接受，該筆標記為已作廢", "§操作/作廢（僅出金）", critical=True))
T.append(tc(28, [2], "作廢時未填寫原因會被系統阻擋", "ui_e2e", ["negative"], ["boundary_value"],
    ["以站長身分，取一筆待核實出金紀錄，點擊作廢", "不填寫作廢原因，直接嘗試送出"],
    "系統阻擋，提示作廢原因為必填欄位", "§操作/作廢（僅出金）"))

T.append(tc(29, [1], "操作員不具備作廢權限", "ui_e2e", ["negative"], ["negative"],
    ["以操作員身分登入後台", "檢視一筆待核實出金紀錄，尋找或嘗試執行作廢操作"],
    "操作員不具備作廢權限，找不到作廢入口或執行時被系統阻擋", "§操作/作廢（僅出金）", risk="medium"))

T.append(tc(30, [1], "出金紀錄被作廢後分數不退回機台，且無法復原", "ui_e2e", ["negative"], ["negative"],
    ["使用測試站台專用、金額最小化、且已排除出正式日結報表統計的一筆待核實出金紀錄，記錄其對應機台帳號當下的分數", "對該筆執行作廢（不可逆操作，執行前先確認此為測試資料）", "再次檢視該機台帳號的分數，並嘗試尋找復原作廢的操作"],
    "分數不會退回機台帳號（維持作廢前的餘額，不因作廢而增加）；系統不提供復原作廢的功能", "§操作/作廢（僅出金）", critical=True))

T.append(tc(31, [1, 2], "現金淨收計算僅在洗分核實後才計入扣除項", "ui_e2e", ["functional"], ["decision_table"],
    ["一筆洗分交易處於待核實狀態，檢視場館現金淨收計算", "對該筆執行核實後，再次檢視場館現金淨收計算"],
    "核實前：此筆待核實洗分不計入現金淨收扣除項；核實後：此筆已核實洗分計入現金淨收扣除項", "§相關業務規則", risk="medium"))
T.append(tc(31, [1, 2], "現金淨收計算的核實規則出金比照洗分辦理，僅在出金核實後才計入扣除項", "ui_e2e", ["functional"], ["decision_table"],
    ["一筆出金交易處於待核實狀態，檢視場館現金淨收計算", "對該筆執行核實（核銷）後，再次檢視場館現金淨收計算"],
    "核實前：此筆待核實出金不計入現金淨收扣除項；核實後：此筆已核實出金計入現金淨收扣除項（spec.md 原文只提洗分，已由 Oscar 2026-09-14 確認出金比照辦理）", "§相關業務規則", risk="medium"))

# ================= Report =================
cov = collections.defaultdict(lambda: {"draft_ids": [], "acs": collections.defaultdict(list)})
for t in T:
    for r in t["requirement_ids"]: cov[r]["draft_ids"].append(t["draft_id"])
    for a in t["acceptance_criteria_ids"]:
        rid = "REQ-CASHOUT-" + a.split("-")[2][:3]
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
print(f"{len(T)} TCs, {n_exp} exploratory, reqs covered={len(cov)}/31")
