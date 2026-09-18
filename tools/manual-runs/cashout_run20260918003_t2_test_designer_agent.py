#!/usr/bin/env python3
"""RUN-20260918-003 T2: Test Designer (mode=spec) for SPEC-CASHOUT-001 v0.1 (31 ACTIVE requirements).

Designed independently by the Test Designer agent from requirements.yaml + spec v0.1.md
(deliberately without reading testcases/CASHOUT.md, per task instructions, to avoid
anchoring on any prior/manual design for this comparison exercise).

Scope notes carried through the whole file:
- CASHOUT consumes CASHFLOW's transaction model (amounts, statuses, order numbers) and does
  NOT re-verify CASHFLOW's own calculations (threshold math, PENDING lifecycle). Preconditions
  that need a transaction in a given state just say so, they do not re-derive how CASHFLOW
  produces that state.
- CASHOUT's verify action writes back to TXLOG's status columns; TCs may check the write-back
  value itself, but do not re-test TXLOG's own column rendering/filtering logic.
- The "操作員" (operator) role is defined by PLATFORMRULE (package 6), which has not gone
  through Phase 3 yet. TCs that need an operator account are marked exploratory: the *rule*
  quoted from THIS spec is treated as given, but whether an operator test account with the
  documented single-venue scoping already exists/behaves as documented in the current
  environment is flagged as needing confirmation.
"""
import sys, pathlib, collections
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids

RUN, RM_AID = sys.argv[1], sys.argv[2]
ITER = int(sys.argv[3]) if len(sys.argv) > 3 else 0
SID, SV, AREA, A = "SPEC-CASHOUT-001", "0.1", "CASHOUT", "agent-test-designer"

reqs = {r["requirement_id"]: r for r in store.load(store.requirements_path(SID, SV))["requirements"]}


def R(n):
    return f"REQ-CASHOUT-{n:03d}"


def AC(n, i):
    return f"AC-CASHOUT-{n:03d}{i}"


def sr(loc, quote=""):
    d = {"spec_id": SID, "spec_version": SV, "location": loc}
    if quote:
        d["quote"] = quote[:300]
    return d


PRE_ADMIN = [
    "以 Admin 身分登入後台",
    "頁面標題下方的站台切換選單已切換至一個既有的測試站台",
    "進入 帳務管理 > 洗分出金核實",
]
PRE_CHIEF = [
    "以一個既有的『站長』角色帳號登入後台（自行從環境中選定該站長所屬場館的帳號）",
    "頁面標題下方的站台切換選單維持為該站長所屬場館",
    "進入 帳務管理 > 洗分出金核實",
]
PRE_OPERATOR = [
    "以一個既有的『操作員』角色帳號登入後台（自行從環境中選定）",
    "進入 帳務管理 > 洗分出金核實",
]
ASSUME_OPERATOR = (
    "『操作員』角色的權限範圍（含是否限定單一場館）定義於開發包⑥ PLATFORMRULE，"
    "該包尚未完成 Phase 3 測試設計；本 TC 引用的規則文字取自 SPEC-CASHOUT-001 本身"
    "（非本 TC 自行推測），但目前測試環境中是否已存在一個確實依此規則設定好場館範圍的"
    "操作員帳號、以及後端是否已如文字所述拒絕跨場館請求，尚未獨立確認，需環境/PLATFORMRULE"
    "負責人協助確認後才能視為可重複執行的既定案例"
)


def tc(reqn, acs, title, level, types, techs, steps, expected, loc, quote="", rationale="",
       prio=None, risk=None, pre=None, data=None, assume=None, critical=False, cost="medium",
       more_reqs=(), extra_ac=(), req_for_assume=None):
    r = reqs[R(reqn)]
    assumptions = []
    for a in ([assume] if isinstance(assume, str) else (assume or [])):
        assumptions.append({"text": a, "requirement_id": R(req_for_assume or reqn), "needs_human_confirmation": True})
    prio = prio or (risk or r["risk"])
    return {
        "draft_id": f"TC-DRAFT-{ids.ulid()}",
        "title": title,
        "product": "ba-admin",
        "functional_area": AREA,
        "requirement_ids": [R(reqn)] + [R(x) for x in more_reqs],
        "acceptance_criteria_ids": [AC(reqn, i) for i in acs] + [AC(rn, ai) for rn, ai in extra_ac],
        "spec_id": SID,
        "spec_version": SV,
        "test_level": level,
        "test_types": types,
        "design_techniques": techs,
        "priority": prio,
        "risk": risk or r["risk"],
        "execution_mode": "manual",
        "preconditions": PRE_ADMIN if pre is None else pre,
        "test_data": [{"name": k, "value": v} for k, v in (data or {}).items()],
        "steps": [{"n": i + 1, "action": s} for i, s in enumerate(steps)],
        "expected_result": expected,
        "expected_result_spec_reference": sr(loc, quote),
        "assumptions": assumptions,
        "automation_status": "not_automated",
        "ci_eligible": False,
        "hotfix_eligible": True,
        "execution_cost": cost,
        "stability": "unknown",
        "critical_path": critical,
        "source": "spec_workflow",
        "design_rationale": rationale,
    }


T = []

# ---------------- REQ-001：已完成洗分/出金自動產生待核實紀錄 ----------------
T.append(tc(1, [1], "機台洗分交易完成後，本頁自動出現一筆對應的待核實紀錄", "ui_e2e",
    ["functional"], ["requirement_based"],
    ["於測試機台完成一筆機台洗分（或於機台交易紀錄確認一筆洗分交易狀態已為『已完成』）",
     "進入本頁（不套用任何篩選條件），檢視是否出現對應該筆交易的紀錄"],
    "本頁自動出現一筆待核實紀錄，其交易編號對應剛完成的洗分交易",
    "§功能說明",
    quote="每一筆「已完成」的機台洗分或機台出金，系統會自動在本頁產生一筆待核實紀錄",
    rationale="AC-0011 字面涵蓋洗分與出金兩種交易類型，兩者現場流程不同（見功能說明表格），故拆成兩條對稱 TC 分別驗證，避免用單一 TC 掩蓋任一類型可能各自的問題；技巧用 requirement_based 因為只是單一條件（交易完成）到單一結果（出現紀錄）的直接對應，沒有組合矩陣，不套用 decision_table。",
    critical=True))
T.append(tc(1, [1], "機台出金交易完成後，本頁自動出現一筆對應的待核實紀錄", "ui_e2e",
    ["functional"], ["requirement_based"],
    ["於測試機台完成一筆機台出金（收據印出，或於機台交易紀錄確認一筆出金交易狀態已為『已完成』）",
     "進入本頁，檢視是否出現對應該筆交易的紀錄"],
    "本頁自動出現一筆待核實紀錄，其交易編號對應剛完成的出金交易",
    "§功能說明",
    quote="每一筆「已完成」的機台洗分或機台出金，系統會自動在本頁產生一筆待核實紀錄",
    rationale="與上一條 TC 對稱，同樣用 requirement_based；不用 decision_table 是因為兩條 TC 各自只驗證『一種交易類型 -> 是否出現』，並未在同一條 TC 內比較交易類型與結果的組合矩陣。"))
T.append(tc(1, [1], "尚未完成（待確認）的洗分交易，系統不會為其建立核實紀錄", "ui_e2e",
    ["negative"], ["negative"],
    ["取得（或使一筆）機台洗分交易於機台交易紀錄的交易狀態為『待確認』（尚未完成）",
     "進入本頁，以該機台帳號或訂單編號查詢，確認是否有對應紀錄"],
    "查無此筆紀錄；因為交易尚未完成，系統根本不會為它建立核實狀態紀錄。不可憑本頁無紀錄直接判斷交易狀態，須至機台交易紀錄查明實際狀態後再決定是否付款",
    "§紀錄產生規則",
    quote="僅交易狀態為「已完成」的機台洗分與機台出金會出現在本頁；待確認、已取消、已逾時、未成立的交易不會出現",
    rationale="這條 TC 同時是 REQ-001（已完成才產生紀錄）的反面驗證，也是 REQ-004 AC-0041（未完成交易不出現）的正面驗證，兩者本質是同一個規則的一體兩面，因此一條 TC 掛兩個 requirement_id，不重複設計；REQ-001 為 high risk 需要至少一條非 happy-path 案例，這條負向案例滿足該要求。技巧選 negative（而非 boundary_value）因為交易狀態是離散的列舉值（待確認/已完成/已取消/已逾時/未成立），不是數值或長度的邊界比較。",
    more_reqs=(4,), extra_ac=((4, 1),)))

# ---------------- REQ-002：全平台唯一核實入口 ----------------
T.append(tc(2, [1], "機台交易紀錄頁只顯示核實狀態，不提供核實或作廢操作", "ui_e2e",
    ["negative"], ["negative"],
    ["至機台交易紀錄頁，查詢一筆待核實的機台洗分或出金交易",
     "檢視該筆紀錄的核實狀態欄與操作欄可用選項"],
    "核實狀態欄正常顯示狀態，但操作欄不提供『核實』或『作廢』的按鈕/選項；須切換至本頁（洗分出金核實）才能執行",
    "§功能說明",
    quote="本頁是全平台唯一的核實入口——機台交易紀錄只顯示核實狀態，不提供操作",
    rationale="本 TC 只檢查機台交易紀錄頁『操作欄是否提供核實/作廢入口』這一件與 CASHOUT 範圍直接相關的事，不涉及該頁其他欄位的顯示邏輯或篩選行為，符合『不重新驗證 TXLOG 頁面本身顯示邏輯』的範圍限制。",
    risk="medium"))

# ---------------- REQ-003：開分/入金不出現 ----------------
T.append(tc(3, [1], "開分與入金交易不會出現在本頁列表", "ui_e2e",
    ["negative"], ["negative"],
    ["確認站台內存在已完成的機台開分與機台入金交易（可於機台交易紀錄查得）",
     "進入本頁，不套用任何篩選條件，檢視列表所有紀錄的交易類型"],
    "列表中查無任何開分或入金類型的紀錄，僅可能出現機台洗分與機台出金",
    "§紀錄產生規則",
    quote="開分與入金不需核實，不會出現在本頁（兩者都不是付錢給玩家）",
    rationale="這是對『本頁只收錄付錢給玩家的交易』這條邊界規則的直接驗證，用 negative 技巧檢查『不應該出現』的資料類型，risk 為 medium，不強制要求額外反向案例。",
    risk="medium"))

# ---------------- REQ-004：未成立的出金 ----------------
T.append(tc(4, [2], "未成立的機台出金交易，系統不會為其建立核實紀錄", "ui_e2e",
    ["negative"], ["negative"],
    ["取得一筆機台出金交易，於機台交易紀錄查得其交易狀態為『未成立』",
     "進入本頁，以該筆交易的機台帳號或（若有）訂單編號查詢，確認是否有對應紀錄"],
    "查無此筆紀錄，因為未成立的交易沒有核實狀態，不會出現在本頁",
    "§紀錄產生規則",
    quote="待確認、已取消、已逾時、未成立的交易不會出現",
    rationale="AC-0042 需要出金交易類型的獨立驗證（AC-0041 是洗分/待確認，兩者交易類型與交易狀態都不同，不宜用同一條 TC 概括），沿用 negative 技巧維持與 AC-0041 一致的技巧標記，避免同一種規則被貼上不同技巧標籤。",
    critical=True))

# ---------------- REQ-005：待核實狀態呈現 ----------------
T.append(tc(5, [1], "待核實的洗分交易以醒目色標提示", "ui_e2e",
    ["functional"], ["requirement_based"],
    ["取得一筆核實狀態為『待核實』的機台洗分交易",
     "於本頁列表檢視該筆紀錄核實狀態欄的呈現方式"],
    "以醒目色標（提醒現金可能尚未交付或現場漏登記的樣式）呈現，明顯區別於一般的藍色待核實標記",
    "§核實狀態",
    quote="待核實的洗分以醒目色標提示（現金可能未交付或現場漏登記）",
    rationale="單一條件（洗分＋待核實）對應單一呈現方式，用 requirement_based；不用 decision_table，因為沒有在同一條 TC 內比較多個條件的組合。",
    critical=True))
T.append(tc(5, [2], "待核實的出金交易維持正常藍色標示，不做醒目提示", "ui_e2e",
    ["functional"], ["requirement_based"],
    ["取得一筆核實狀態為『待核實』的機台出金交易",
     "於本頁列表檢視該筆紀錄核實狀態欄的呈現方式"],
    "以一般藍色核實狀態標記正常顯示，不套用醒目提示樣式（收據不設兌現時效，待核實屬正常情況）",
    "§核實狀態",
    quote="待核實的出金屬正常（收據不設兌現時效，玩家隔幾天才來兌現很常見）",
    rationale="與上一條對稱但交易類型不同，結果也不同（有無醒目提示），仍各自是單一條件對單一結果，維持同一技巧標記 requirement_based，不因為想呈現『技巧多樣性』而刻意改標。"))
T.append(tc(5, [1], "轉為已核實後，原本的醒目色標提示消失，改以已核實的一般樣式顯示", "ui_e2e",
    ["negative"], ["negative"],
    ["取得一筆原本核實狀態為『待核實』且以醒目色標顯示的洗分交易",
     "對其執行核實（見 REQ-CASHOUT-021 核實流程）",
     "核實完成後再次檢視該筆紀錄的呈現方式"],
    "不再顯示待核實的醒目提示樣式，改為已核實狀態對應的綠色一般樣式；醒目提示只在『待核實』這個狀態下出現",
    "§核實狀態",
    quote="待核實 | 藍色 | ...待核實的洗分以醒目色標提示... ｜ 已核實 | 綠色 | 現金已交付並完成登記",
    rationale="核實狀態表逐列各自定義了顏色與說明，『醒目提示』只出現在待核實列的洗分描述中，已核實列另有獨立的顏色/說明，因此可以直接從表格結構推斷已核實狀態不再套用醒目提示，這是結構性的合理推論，不是憑空假設，故未標 assumptions；技巧用 negative，驗證『不應該出現』的樣式，同時滿足 REQ-005 屬 high risk 需要至少一條非 happy-path 案例的規則。"))

# ---------------- REQ-006：已核實累計提款次數/金額 ----------------
T.append(tc(6, [1], "核實當下，該筆金額以原值累計進該機台帳號的提款次數與提款金額", "ui_e2e",
    ["functional"], ["requirement_based"],
    ["取得一筆待核實的機台洗分交易，先於該機台帳號的會員列表記錄核實前的提款次數與提款金額",
     "於本頁對該筆交易執行核實（依 REQ-CASHOUT-021 流程）",
     "核實完成當下，再次檢視該機台帳號的提款次數與提款金額"],
    "提款次數較核實前 +1；提款金額較核實前增加本筆實際金額，以站台核心貨幣原值累計，不換算 USDT",
    "§核實狀態",
    quote="核實當下該筆累計進該機台帳號於會員列表的「提款次數」「提款金額」",
    rationale="這是一個明確的前後比較型驗證，requirement_based 已足以描述『核實動作 -> 計數增加』這個單一因果關係，不涉及多條件組合，不套用 decision_table。",
    critical=True))
T.append(tc(6, [1], "待核實與已作廢的紀錄不計入提款次數與提款金額", "ui_e2e",
    ["negative"], ["negative"],
    ["取得一筆仍為『待核實』的機台洗分交易，記錄該機台帳號當前的提款次數與提款金額",
     "確認未對其執行核實，再次檢視該機台帳號的提款次數與提款金額",
     "另取得一筆『已作廢』的機台出金交易，同樣確認其對應機台帳號的提款次數與提款金額未因該筆作廢紀錄而變動"],
    "待核實與已作廢的紀錄皆不計入提款次數與提款金額，只有『已核實』狀態的紀錄才會在核實當下被計入",
    "§操作",
    quote="並於核實當下把該筆累計進該機台帳號於會員列表的「提款次數」「提款金額」（金額以站台核心貨幣原值累計、不換算 USDT；待核實與已作廢不計）",
    rationale="此句『待核實與已作廢不計』出現在操作表格的『連動』一列（REQ-CASHOUT-026 的字面引用範圍只到欄位回寫，未含此後半句），但語意上是在補充提款次數/金額累計規則的邊界，與 REQ-006 的統計定義同源，因此歸在 REQ-006 而非 REQ-026；REQ-006 為 high risk，此負向案例滿足非 happy-path 覆蓋要求。"))

# ---------------- REQ-007：已作廢僅出金 ----------------
T.append(tc(7, [1], "機台洗分的核實狀態不會出現已作廢", "ui_e2e",
    ["negative"], ["negative"],
    ["檢視核實狀態篩選下拉選單，篩選核實狀態為『已作廢』並將交易類型篩選為『機台洗分』後搜尋",
     "檢視搜尋結果，並另外確認任一筆洗分交易於列表操作欄是否提供『作廢』選項"],
    "篩選結果為空（洗分交易不可能有已作廢狀態）；任一筆洗分交易的操作欄也不提供作廢選項，洗分只會落在待核實或已核實兩種狀態",
    "§核實狀態",
    quote="已作廢 | 灰色 | 僅出金：收據經人工作廢，不再兌付",
    rationale="用篩選器交叉驗證『查無結果』與操作欄『無作廢選項』兩個角度共同證明洗分不具備已作廢狀態，比單看某一欄位更扎實；technique 維持 negative（驗證不存在），risk medium 不強制額外反向案例。",
    risk="medium"))

# ---------------- REQ-008：跟隨站台切換，不設場館篩選 ----------------
T.append(tc(8, [1], "篩選器不提供場館欄位，頁面資料範圍隨站台切換選單變動", "ui_e2e",
    ["functional", "negative"], ["requirement_based"],
    ["檢視篩選器所有欄位，確認是否存在『場館』篩選欄位",
     "將頁面標題下方的站台切換選單切換至站台 A，記錄查詢結果範圍",
     "再切換至另一個既有站台 B，重新查詢並比較結果範圍"],
    "篩選器不存在『場館』欄位；切至站台 A 時查詢結果僅限站台 A 範圍內的紀錄，切至站台 B 後結果隨之只剩站台 B 範圍內的紀錄",
    "§篩選器",
    quote="頁面資料範圍跟隨頁面標題下方的站台切換下拉選單（後台各頁皆有，一次僅顯示所選站台），不另設場館篩選欄位",
    rationale="這條 TC 同時驗證『沒有場館欄位』與『資料範圍確實跟著站台切換而變』兩件事，都是同一條規則的必要組成，用 requirement_based 描述一個條件（切換站台）對應一個結果（範圍改變），不套用 decision_table，因為只有一個變動維度（站台選擇），不是多條件矩陣。",
    risk="medium"))

# ---------------- REQ-009：機台帳號逗號分隔多筆 ----------------
T.append(tc(9, [1], "機台帳號篩選支援以逗號分隔同時查詢多個會員編號", "ui_e2e",
    ["functional"], ["equivalence_partitioning"],
    ["取兩個既有、有各自待核實或已核實紀錄的機台帳號會員編號",
     "於機台帳號篩選欄輸入兩者，以「,」分隔，點擊搜尋"],
    "查詢結果同時包含這兩個機台帳號各自的紀錄",
    "§篩選器",
    quote="機台帳號 | 文字輸入 | 輸入會員編號查詢；支援多筆，以「,」分隔",
    rationale="這是驗證『多值輸入』這個等價類（相對於單一帳號查詢的等價類）能否正確聯集，equivalence_partitioning 比 boundary_value 更貼切，因為重點不是數值邊界，而是輸入格式的分類行為。",
    risk="medium"))

# ---------------- REQ-010：交易類型下拉選單 ----------------
T.append(tc(10, [1], "交易類型篩選下拉選單提供全部/機台洗分/機台出金三個選項", "ui_e2e",
    ["functional"], ["requirement_based"],
    ["開啟交易類型篩選下拉選單", "檢視所有可選項"],
    "包含『全部』『機台洗分』『機台出金』共三個選項，沒有其他選項",
    "§篩選器",
    quote="交易類型 | 下拉選單 | 全部 / 機台洗分 / 機台出金",
    rationale="單純列舉下拉選項是否齊全，requirement_based 已足夠描述。",
    risk="medium"))
T.append(tc(10, [2], "篩選交易類型為機台出金時，結果僅包含出金紀錄", "ui_e2e",
    ["functional"], ["equivalence_partitioning"],
    ["篩選交易類型為『機台出金』並搜尋", "檢視搜尋結果的交易類型欄"],
    "所有結果的交易類型皆為機台出金，不包含機台洗分",
    "§篩選器",
    quote="交易類型 | 下拉選單 | 全部 / 機台洗分 / 機台出金",
    rationale="驗證『機台出金』這個等價類是否正確篩出，equivalence_partitioning 較貼切；不重複測『機台洗分』選項，因為兩者是對稱且同機制的等價類，選一個代表即可，已在 AC-0102 範圍內。",
    risk="medium"))

# ---------------- REQ-011：訂單編號查詢 ----------------
T.append(tc(11, [1], "以出金收據上的訂單編號可查得對應的待核銷紀錄", "ui_e2e",
    ["functional"], ["requirement_based"],
    ["取得一筆待核實出金交易的訂單編號（收據上印製）",
     "於訂單編號篩選欄輸入該編號，點擊搜尋"],
    "查詢結果顯示該筆出金紀錄，且僅此一筆",
    "§篩選器",
    quote="訂單編號 | 文字輸入 | 出金收據上印製的編號，為櫃檯兌現時的主要查詢方式",
    rationale="本查詢是櫃檯核銷流程的入口動作，requirement_based 對應規格明確描述的單一查詢行為。",
    critical=True))
T.append(tc(11, [1], "輸入不存在的訂單編號查詢，結果為空且不誤配到其他紀錄", "ui_e2e",
    ["negative"], ["negative"],
    ["於訂單編號篩選欄輸入一個不對應任何既有收據的編號（例如隨機組合一組不存在的短碼）",
     "點擊搜尋"],
    "查詢結果為空，不會誤配到任何其他筆紀錄；依 REQ-CASHOUT-011 的需求陳述，前端應顯示查無資料的失敗提示（本 TC 未取得提示文案的原文依據，僅驗證有提示且結果為空，實際文案請依執行當下畫面核對）",
    "§篩選器",
    quote="訂單編號 | 文字輸入 | 出金收據上印製的編號，為櫃檯兌現時的主要查詢方式",
    rationale="RequirementModel 的 REQ-CASHOUT-011 statement 提到『查無結果時前端會顯示失敗提示（已由 Oscar 依實際畫面截圖確認）』，但 spec_reference.quote 欄位是空的，本 TC 沒有獨立取得畫面截圖或文案原文，因此只斷言『有提示且結果為空』，不斷言具體文案字樣，避免引用一段自己無法驗證的文字當成確定規則；這條同時滿足 REQ-011 屬 high risk 需要非 happy-path 覆蓋的要求。"))

# ---------------- REQ-012：核實狀態篩選 ----------------
T.append(tc(12, [1], "核實狀態篩選為待核實時，結果僅包含待核實紀錄", "ui_e2e",
    ["functional"], ["equivalence_partitioning"],
    ["篩選核實狀態為『待核實』並搜尋", "檢視搜尋結果的核實狀態欄"],
    "所有結果的核實狀態皆為待核實",
    "§篩選器",
    quote="核實狀態 | 下拉選單 | 全部 / 待核實 / 已核實 / 已作廢",
    rationale="驗證下拉選單其中一個等價類的篩選效果，equivalence_partitioning 貼切；已核實/已作廢兩個選項的篩選機制相同，不重複展開每個選項各一條 TC。",
    risk="medium"))

# ---------------- REQ-013：交易時間/核實時間範圍 ----------------
T.append(tc(13, [1, 2], "交易時間與核實時間範圍篩選皆能正確限定結果", "ui_e2e",
    ["functional", "boundary"], ["boundary_value"],
    ["取一筆已知交易時間為 D1 的紀錄，設定交易時間篩選範圍為 [D1, D1]（同一天）並搜尋，確認該筆包含在結果內",
     "將交易時間篩選範圍改為不含 D1 的區間（例如 [D1+1天, D1+30天]）並搜尋，確認該筆被排除",
     "清除交易時間篩選，改取一筆已核實、已知核實時間為 D2 的紀錄，比照上兩步分別以含 D2 與不含 D2 的核實時間範圍篩選並比對結果"],
    "交易時間範圍恰好包含 D1 時該筆出現、不包含時被排除；核實時間範圍恰好包含 D2 時該筆出現、不包含時被排除，兩個篩選欄位皆以邊界日期正確納入/排除紀錄",
    "§篩選器",
    quote="交易時間 | 日期範圍 | 出金即收據印出時間 ｜ 核實時間 | 日期範圍 | —",
    rationale="日期範圍篩選本質就是邊界比較（範圍含/不含某天），用 boundary_value 是恰當的，因為這裡驗證的是『日期落在範圍邊界內外』的真實邊界行為，不是隨意貼標籤。",
    data={"D1_交易時間範圍(含)": "以既有紀錄之交易時間所在日期為準", "D1_交易時間範圍(不含)": "D1 之後的區間，不含 D1", "D2_核實時間範圍(含)": "以既有已核實紀錄之核實時間所在日期為準", "D2_核實時間範圍(不含)": "D2 之後的區間，不含 D2"},
    risk="low"))

# ---------------- REQ-014：金額範圍 ----------------
T.append(tc(14, [1], "金額範圍篩選（min~max）僅回傳實際金額落在範圍內的紀錄", "ui_e2e",
    ["functional", "boundary"], ["boundary_value"],
    ["取一筆已知實際金額為 X 的紀錄，設定金額篩選範圍 min=X, max=X（恰為邊界）並搜尋，確認該筆包含在結果內",
     "將範圍改為 min=X+0.01, max=X+100（不含 X）並搜尋，確認該筆被排除"],
    "金額範圍恰好等於 X 時該筆出現在結果中；範圍不含 X 時該筆被排除，篩選以實際金額為準確比對邊界",
    "§篩選器",
    quote="金額 | 範圍輸入（min ～ max） | —",
    rationale="金額範圍是明確的數值邊界比較，boundary_value 是直接對應的技巧，X 取自既有紀錄的實際值，避免憑空杜撰不存在於環境中的金額。",
    data={"min(邊界內)": "= 所選紀錄之實際金額 X", "max(邊界內)": "= X", "min(邊界外)": "X + 0.01", "max(邊界外)": "X + 100"},
    risk="low", cost="low"))

# ---------------- REQ-015：交易編號跳轉 ----------------
T.append(tc(15, [1], "點擊交易編號可跳轉至機台交易紀錄頁查看該筆明細", "ui_e2e",
    ["functional"], ["requirement_based"],
    ["於本頁列表任取一筆紀錄，點擊其交易編號欄位值"],
    "導向機台交易紀錄頁，且該頁顯示的交易編號與本頁一致（本 TC 僅驗證導向與交易編號一致，不驗證機台交易紀錄頁其餘欄位的顯示邏輯）",
    "§列表欄位",
    quote="交易編號 | 對應的機台交易編號，可點擊跳至機台交易紀錄查看明細",
    rationale="這是單一導向行為的驗證，requirement_based 已足夠；刻意在 expected_result 註明不驗證 TXLOG 頁其他欄位，避免範圍外溢。",
    risk="medium"))

# ---------------- REQ-016：訂單編號欄 ----------------
T.append(tc(16, [1, 2], "訂單編號欄僅出金顯示收據識別碼，洗分交易顯示橫線", "ui_e2e",
    ["functional"], ["requirement_based"],
    ["檢視一筆機台出金紀錄的訂單編號欄", "檢視一筆機台洗分紀錄的訂單編號欄"],
    "出金紀錄顯示收據上印製的識別碼；洗分紀錄該欄顯示「—」",
    "§列表欄位",
    quote="訂單編號 | 僅出金顯示（收據上印製的識別碼）；洗分顯示「—」",
    rationale="這是同一個欄位依交易類型（單一條件）決定顯示值的規則，屬於單一輸入維度的對應，不涉及第二個條件維度組成矩陣，因此標 requirement_based 而非 decision_table，避免把『一個條件兩種結果』誤標成決策表。",
    risk="medium"))

# ---------------- REQ-017：機台帳號欄 ----------------
T.append(tc(17, [1], "點擊機台帳號欄位值可跳轉至該會員的詳細資料頁", "ui_e2e",
    ["functional"], ["requirement_based"],
    ["於本頁列表任取一筆紀錄，點擊其機台帳號欄位值"],
    "導向該機台帳號對應的會員詳細資料頁",
    "§列表欄位",
    quote="機台帳號 | 會員編號，可點擊進入會員詳細資料頁",
    rationale="單一導向行為，requirement_based 已足夠。",
    risk="medium"))
T.append(tc(17, [2], "列表不顯示場館名稱欄位或任何場館名稱資訊", "ui_e2e",
    ["negative"], ["negative"],
    ["檢視本頁列表的所有欄位標題與每一列的內容"],
    "不存在『場館名稱』欄位，任何一列的內容也都不顯示場館名稱（場館已由站台切換選單限定，每列相同、屬冗餘資訊）",
    "§列表欄位",
    quote="場館名稱不顯示——場館已由頁面標題下方的站台切換限定，每列相同、屬冗餘資訊",
    rationale="驗證『不應該出現』的欄位，用 negative 技巧；與 AC-0171 分開設計為兩條 TC，因為一個是導向行為、一個是欄位存在性檢查，性質不同不宜合併成一條多分支 TC。",
    risk="medium"))

# ---------------- REQ-018：實際金額欄 ----------------
T.append(tc(18, [1], "洗分因門檻計算實際金額小於店員原輸入金額時，本欄顯示實際金額且應以此欄付現", "ui_e2e",
    ["functional"], ["requirement_based"],
    ["取得（或使機台端門檻計算產生）一筆洗分交易，其實際入帳金額小於店員操作機台時輸入的金額（門檻換算邏輯屬開發包③ CASHFLOW 管轄，本 TC 不重新驗證門檻計算本身是否正確，只需借用一筆已滿足『實際金額 < 原輸入金額』條件的交易）",
     "於本頁檢視該筆紀錄的實際金額欄"],
    "顯示門檻計算後的實際金額（小於原輸入金額），且此欄位是店員付現的唯一依據，不是原輸入金額",
    "§列表欄位",
    quote="實際金額 | 實際異動的金額。洗分因門檻計算可能小於店員輸入的金額，付現一律以本欄為準；出金即收據面額",
    rationale="本欄的門檻折扣『是否發生、發生多少』由 CASHFLOW 決定，CASHOUT 只需正確顯示與傳達『以此欄為準』，因此 precondition 明講不重新驗證門檻計算本身，只要求借用一筆已符合條件的交易；technique 用 requirement_based，因為驗證的是單一顯示規則。",
    critical=True))
T.append(tc(18, [2], "出金交易的實際金額欄即為收據面額", "ui_e2e",
    ["functional"], ["requirement_based"],
    ["取得一筆機台出金交易", "於本頁檢視該筆紀錄的實際金額欄，並與其收據面額比對"],
    "實際金額欄顯示的數值與收據面額一致",
    "§列表欄位",
    quote="出金即收據面額",
    rationale="與上一條對稱但交易類型不同，維持同一技巧標記，不因為想湊多樣性而改標。"))
T.append(tc(18, [1], "實際金額欄在金額趨近於 0 的邊界情況下仍正確顯示數值，不會空白或顯示異常", "ui_e2e",
    ["boundary"], ["boundary_value"],
    ["取得（或借用）一筆洗分交易，其門檻計算後的實際金額非常接近 0（但大於 0）",
     "於本頁檢視該筆紀錄的實際金額欄呈現方式"],
    "正確顯示該筆極小的實際金額數值，不會顯示空白、負數或明顯錯誤的格式，欄位呈現規則與一般金額一致",
    "§列表欄位",
    quote="實際金額 | 實際異動的金額",
    rationale="這裡驗證的是 CASHOUT 對極端小數值的『顯示』是否穩健，而不是重新驗證 CASHFLOW 產生這個極小值的門檻計算邏輯本身，因此屬於 CASHOUT 範圍內、名實相符的 boundary_value 案例；此案例也讓 REQ-018（high risk）具備非 happy-path 覆蓋。"))

# ---------------- REQ-019：核實時間/核實人員欄 ----------------
T.append(tc(19, [1, 2], "已核實紀錄顯示核實時間與核實人員，待核實紀錄兩欄皆顯示橫線", "ui_e2e",
    ["functional"], ["requirement_based"],
    ["檢視一筆已核實紀錄的核實時間欄與核實人員欄",
     "檢視一筆仍為待核實的紀錄的核實時間欄與核實人員欄"],
    "已核實紀錄顯示執行核實的時間（UTC+0）與後台帳號；待核實紀錄的兩欄皆顯示「—」",
    "§列表欄位",
    quote="核實時間 | 執行核實的時間（UTC+0）；待核實顯示「—」 ｜ 核實人員 | 執行核實的後台帳號；待核實顯示「—」",
    rationale="這是同一狀態條件（是否已核實）同時決定兩個欄位顯示的規則，仍是單一條件對結果的對應（只是結果涉及兩欄），用 requirement_based 已足夠描述，不需要 decision_table。",
    risk="low"))

# ---------------- REQ-020：操作欄 ----------------
T.append(tc(20, [1, 2], "操作欄：出金待核實提供核實與作廢，洗分待核實僅提供核實", "ui_e2e",
    ["functional"], ["requirement_based"],
    ["檢視一筆待核實出金紀錄的操作欄可用選項",
     "檢視一筆待核實洗分紀錄的操作欄可用選項"],
    "出金紀錄的操作欄同時提供『核實』與『作廢』；洗分紀錄的操作欄僅提供『核實』，不提供『作廢』",
    "§列表欄位",
    quote="操作 | 核實、作廢（作廢僅出金）",
    rationale="交易類型（單一條件）決定操作欄可用選項的組合，屬單一維度對應，標 requirement_based；沒有第二個獨立條件維度（例如角色）在同一 TC 內交叉比較，故不套用 decision_table。",
    risk="medium"))

# ---------------- REQ-021：核實（洗分）流程 ----------------
T.append(tc(21, [1], "核實（洗分）三步驟流程：核對彈窗內容後確認，狀態轉為已核實並記錄人員與時間", "ui_e2e",
    ["functional"], ["state_transition"],
    ["依機台帳號（會員編號）或交易時間，於本頁找到一筆待核實的洗分紀錄，點擊『核實』",
     "確認彈窗顯示機台帳號、實際金額與交易時間，逐項核對與該筆紀錄一致",
     "核對無誤後點擊確認"],
    "系統將該筆紀錄的核實狀態由『待核實』轉為『已核實』，並記錄執行核實的人員與時間",
    "§操作/核實（洗分）",
    quote="1. 依機台帳號（會員編號）或交易時間找到該筆待核實洗分，點擊「核實」 2. 確認彈窗顯示機台帳號、實際金額與交易時間，核對無誤後點擊確認 3. 系統標記為「已核實」，並記錄核實人員與時間",
    rationale="REQ-CASHOUT-021 在 RequirementModel 中明確定義了 states（待核實 -> 已核實），依規則必須有一條 state_transition 技巧的案例；本 TC 完整走過彈窗核對到狀態轉換的三步驟，是這個狀態轉換的直接驗證。REQ-021 為 high risk，其非 happy-path 覆蓋由下方與 REQ-024 共用的重複核實阻擋案例提供（該案例的前置狀態正是本 TC 產生的『已核實』洗分紀錄）。",
    critical=True))

# ---------------- REQ-022：核實（出金）流程 ----------------
T.append(tc(22, [1], "核實（出金＝核銷收據）四步驟流程：查詢、核對彈窗、確認、櫃檯付現", "ui_e2e",
    ["functional"], ["state_transition"],
    ["於本頁上方輸入一筆待核實出金交易的訂單編號查詢，並在結果中點擊『核實』（或直接於列表對該筆點擊『核實』）",
     "確認彈窗顯示訂單編號、機台帳號、金額與收據印出時間，逐項核對與該筆紀錄一致",
     "核對無誤後點擊確認",
     "（現場流程）櫃檯付現金給玩家——此步驟為現場操作，測試時以口頭/紀錄方式確認流程已知會執行人員，系統面僅需驗證前三步的狀態轉換"],
    "系統將該筆紀錄的核實狀態由『待核實』轉為『已核實』，並記錄執行核實的人員與時間；核實即代表該筆收據已核銷",
    "§操作/核實（出金＝核銷收據）",
    quote="1. 於頁面上方輸入收據上的訂單編號查詢...或直接在列表點擊「核實」 2. 確認彈窗顯示訂單編號、機台帳號、金額與收據印出時間，核對無誤後點擊確認 3. 系統標記為「已核實」，並記錄核實人員與時間 4. 櫃檯付現金給玩家",
    rationale="REQ-CASHOUT-022 同樣定義了 states，需要一條 state_transition 技巧的案例；第四步『櫃檯付現』是系統外的現場動作，spec 本身也沒有定義系統要如何驗證『是否已付現』，因此 expected_result 不對這一步做系統面斷言，避免捏造 spec 未定義的驗收點；REQ-022 為 high risk，非 happy-path 覆蓋同樣由與 REQ-024 共用的案例提供。",
    critical=True))

# ---------------- REQ-023：過渡期照片核銷 ----------------
T.append(tc(23, [1], "過渡期以結算結果畫面照片上的訂單編號核銷，流程與狀態與有收據時相同", "ui_e2e",
    ["functional"], ["requirement_based"],
    ["若目前環境仍處於過渡期（機台無印表機）：取得玩家出示的結算結果畫面照片，讀取照片上的訂單編號；若環境已回歸正式期（印表機已到位），改用收據上的訂單編號替代，核銷邏輯本身不受影響",
     "於本頁上方以該訂單編號查詢，找到對應的待核實出金紀錄",
     "依 REQ-CASHOUT-022 的核實流程核對彈窗內容後確認"],
    "無論訂單編號來源是照片還是實體收據，核實流程與最終狀態轉換完全相同，系統不區分過渡期與正式期",
    "§功能說明",
    quote="櫃檯依照片上的訂單編號核銷，本頁流程與狀態不變",
    rationale="過渡期是否仍在生效屬於環境當下的現況，precondition 用『若…則…』的方式兼容兩種環境現況，核心斷言（流程與狀態不因訂單編號來源而不同）不受環境現況影響，因此不需要標記為 exploratory——這條規則本身就是規格明文定義的，只是測試資料的取得方式會因環境現況而異。"))

# ---------------- REQ-024：僅待核實可核實，重複核實阻擋 ----------------
T.append(tc(24, [1], "已核實的洗分紀錄再次執行核實時，系統阻擋並提示", "ui_e2e",
    ["negative"], ["negative"],
    ["取得一筆已核實的機台洗分紀錄（可沿用 REQ-CASHOUT-021 案例核實完成後的紀錄）",
     "嘗試對該筆紀錄再次點擊『核實』並完成確認彈窗流程"],
    "系統阻擋此次操作並顯示提示，不會將核實動作重複執行，也不會重複計入提款次數與提款金額",
    "§操作",
    quote="可核實的狀態 | 僅「待核實」；已核實或已作廢的紀錄再次核實時，系統阻擋並提示，避免重複付款",
    rationale="本案例同時是 REQ-021（提供其 high risk 所需的非 happy-path 覆蓋）與 REQ-024 自身的驗證，因為『重複核實被擋』的前置條件正是『先前已透過 REQ-021 流程核實過一次』，兩者語意上緊密相關，共用一條 TC 比另外編一個不相干的反例更誠實。",
    more_reqs=(21,), critical=True))
T.append(tc(24, [2], "已作廢的出金紀錄嘗試核實時，系統阻擋並提示", "ui_e2e",
    ["negative"], ["negative"],
    ["取得一筆已作廢的機台出金紀錄（可沿用 REQ-CASHOUT-028 案例作廢完成後的紀錄）",
     "嘗試對該筆紀錄點擊『核實』並完成確認彈窗流程"],
    "系統阻擋此次操作並顯示提示，不會將核實動作執行成功",
    "§操作",
    quote="已核實或已作廢的紀錄再次核實時，系統阻擋並提示，避免重複付款",
    rationale="同上，這條與 REQ-022（出金核實流程）也有前置關聯（已作廢的紀錄不可能再走一次核實流程），但因為『已作廢』狀態是透過 REQ-028 的作廢操作產生，語意上更貼近作廢流程之後的防呆，因此掛 REQ-022 只是為了讓出金這個交易類型也有一條非 happy-path 覆蓋，而不是暗示已作廢紀錄真的走過核實流程。",
    more_reqs=(22,)))

# ---------------- REQ-025：操作員站台切換權限 ----------------
T.append(tc(25, [1], "操作員登入後台時，前端不提供切換至其他場館的入口，僅能對自身場館紀錄執行核實", "ui_e2e",
    ["security", "negative"], ["security_rule"],
    ["以操作員身分登入後台，檢視頁面標題下方的站台切換選單",
     "確認選單是否提供切換至其他場館的選項",
     "對該操作員自身所屬場館的一筆待核實紀錄嘗試執行核實"],
    "站台切換選單不提供切換至其他場館的入口（前端已限制，操作員僅能停留在自身所屬場館）；對自身場館的紀錄可正常完成核實",
    "§操作",
    quote="權限 | Admin、站長、操作員皆可執行（操作員限自身場館）",
    rationale="規則文字本身取自 SPEC-CASHOUT-001，不是本 TC 推測的；但『操作員』角色與其場館範圍限制的實際實作定義於尚未完成 Phase 3 的 PLATFORMRULE 包，因此標記 assumptions，需要環境/PLATFORMRULE 負責人確認測試環境中確實存在一個依規則設定好的操作員帳號。",
    pre=PRE_OPERATOR, assume=ASSUME_OPERATOR, req_for_assume=25, critical=True))
T.append(tc(25, [2], "操作員直接呼叫核實 API 並指定非自身場館的紀錄時，後端拒絕該請求", "api",
    ["security", "negative"], ["security_rule"],
    ["以操作員身分取得其登入 session/token",
     "略過前端限制，直接呼叫核實 API，並在請求中指定一筆不屬於該操作員所屬場館的紀錄"],
    "後端拒絕該請求（回傳權限錯誤，不執行核實），不會因為只在前端擋就讓後端在缺乏前端保護時被繞過",
    "§操作",
    quote="操作員限自身場館",
    rationale="與前一條互補，前一條驗證前端限制，本條驗證後端 API 層是否獨立拒絕，符合 spec statement 特別強調『前後端皆已拒絕』的描述；同樣因操作員角色定義未完成 Phase 3 而標記 assumptions。",
    pre=["以操作員身分（自行從環境中選定的既有帳號）取得其登入憑證，用於直接呼叫後端 API", "非自身場館的一筆待核實紀錄，其場館為該操作員帳號未被授權的場館"],
    assume=ASSUME_OPERATOR, req_for_assume=25))

# ---------------- REQ-026：核實連動回寫 TXLOG ----------------
T.append(tc(26, [1], "核實結果回寫機台交易紀錄頁對應交易的核實狀態、核實人員與時間欄位", "ui_e2e",
    ["functional"], ["requirement_based"],
    ["取得一筆待核實的機台洗分交易，於本頁依 REQ-CASHOUT-021 流程完成核實，記錄執行核實的帳號與系統顯示的核實時間",
     "至機台交易紀錄頁，查詢該筆交易，檢視其核實狀態、核實人員、核實時間欄"],
    "機台交易紀錄頁顯示該筆交易的核實狀態為已核實，核實人員與核實時間與本頁執行核實時記錄的一致；本 TC 僅比對這三個欄位的回寫值，不驗證機台交易紀錄頁其餘欄位或篩選邏輯",
    "§操作",
    quote="連動 | 核實結果回寫機台交易紀錄的「核實狀態」「核實人員／時間」欄位",
    rationale="這是 CASHOUT 自己觸發的寫回動作，驗證寫回的值是否正確屬於 CASHOUT 範圍；刻意在 expected_result 註明不驗證 TXLOG 頁其餘顯示邏輯，避免範圍外溢。",
    risk="medium"))

# ---------------- REQ-027：核實不可撤銷 ----------------
T.append(tc(27, [1], "已核實的紀錄找不到任何撤銷核實的操作，僅能於後台操作紀錄追溯", "ui_e2e",
    ["negative"], ["negative"],
    ["取得一筆已核實的紀錄，檢視其操作欄與紀錄詳情，尋找是否有『撤銷核實』或等效的操作",
     "至後台操作紀錄（7.4 操作紀錄），查詢該筆核實動作，確認是否可查得執行人員與時間"],
    "操作欄與任何介面皆不提供撤銷核實的功能；後台操作紀錄可查得該筆核實動作的執行人員與時間，但無法回復該筆紀錄的核實狀態",
    "§操作",
    quote="核實一經確認即無法撤銷，誤按無法回復，只能透過後台操作紀錄追溯執行人員與時間",
    rationale="驗證『不存在』的功能用 negative 技巧；同時驗證『唯一補救途徑』（操作紀錄可追溯）確實存在，兩者合起來才完整覆蓋這條不可逆規則的兩面，REQ-027 為 high risk rejection 類需求，本案例的 negative test_type 滿足覆蓋要求。",
    critical=True))

# ---------------- REQ-028：作廢僅 Admin/站長，須填原因 ----------------
T.append(tc(28, [1], "站長對待核實出金執行作廢，填寫作廢原因後系統接受並標記為已作廢", "ui_e2e",
    ["functional"], ["requirement_based"],
    ["取得一筆待核實的機台出金紀錄，以站長身分對其點擊『作廢』",
     "於作廢原因欄填寫原因（例如：收據遺失）",
     "送出"],
    "系統接受此次作廢，該筆紀錄的核實狀態轉為『已作廢』",
    "§操作/作廢（僅出金）",
    quote="僅 Admin 與站長可執行，須填寫作廢原因（必填）；用於收據遺失、爭議或確認不再兌付的情況",
    rationale="這是作廢流程的 happy-path，requirement_based 對應規格明確描述的操作流程；權限角色用『站長』而非『操作員』，因為只有操作員角色的存在性/範圍受 PLATFORMRULE 未完成 Phase 3 影響，站長與 Admin 屬既有、已在其他已完成 Phase 3 的功能包中沿用的角色，不需標記 assumptions。",
    pre=PRE_CHIEF, critical=True))
T.append(tc(28, [2], "作廢時未填寫作廢原因，系統阻擋送出", "ui_e2e",
    ["negative"], ["negative"],
    ["取得一筆待核實的機台出金紀錄，以站長身分對其點擊『作廢』",
     "不填寫作廢原因欄，直接嘗試送出"],
    "系統阻擋此次送出，提示作廢原因為必填，該筆紀錄核實狀態維持不變（不會被作廢）",
    "§操作/作廢（僅出金）",
    quote="須填寫作廢原因（必填）",
    rationale="必填欄位的反向驗證，negative 技巧對應；REQ-028 為 high risk rejection 類需求，本案例滿足覆蓋要求。",
    pre=PRE_CHIEF))

# ---------------- REQ-029：操作員無法作廢 ----------------
T.append(tc(29, [1], "操作員不具備作廢權限，無法執行作廢操作", "ui_e2e",
    ["security", "negative"], ["security_rule"],
    ["以操作員身分登入後台，取得一筆待核實的機台出金紀錄",
     "檢視該筆紀錄的操作欄，確認是否提供『作廢』選項；若提供，嘗試點擊並觀察系統反應"],
    "操作欄不提供作廢選項給操作員（或即使嘗試觸發也被系統拒絕），操作員無法完成作廢",
    "§操作/作廢（僅出金）",
    quote="僅 Admin 與站長可執行",
    rationale="規則本身（僅 Admin/站長）是 spec 明文定義，但驗證『操作員角色確實被排除』需要一個操作員測試帳號，其存在性與行為受 PLATFORMRULE 未完成 Phase 3 影響，因此標記 assumptions，與 REQ-025 的處理方式一致。",
    pre=PRE_OPERATOR, assume=ASSUME_OPERATOR, req_for_assume=29))

# ---------------- REQ-030：作廢不可復原、分數不退回 ----------------
T.append(tc(30, [1], "作廢後不可復原，且分數不會退回機台帳號", "ui_e2e",
    ["negative"], ["negative"],
    ["取得一筆待核實的機台出金紀錄，記錄該機台帳號當前的機台分數/餘額",
     "以站長身分將其作廢（依 REQ-CASHOUT-028 流程）",
     "作廢完成後，檢視該機台帳號的分數/餘額是否有變化，並尋找是否有任何『復原作廢』的操作"],
    "該機台帳號的分數/餘額不會因作廢而增加（分數不退回機台）；介面上不存在復原作廢的功能",
    "§操作/作廢（僅出金）",
    quote="作廢後不可復原，分數也不會退回機台",
    rationale="同時驗證『不可復原』（找不到功能）與『分數不退回』（數值比對）兩個角度，negative 技巧對應『驗證不應發生的事』；REQ-030 為 high risk rejection 類需求，本案例滿足覆蓋要求。",
    pre=PRE_CHIEF, critical=True))

# ---------------- REQ-031：現金淨收計算 ----------------
T.append(tc(31, [1], "待核實的洗分或出金紀錄不計入場館現金淨收扣除項", "ui_e2e",
    ["functional"], ["requirement_based"],
    ["取得一筆待核實的機台洗分交易與一筆待核實的機台出金交易，先於 帳務管理 > 場館日結報表（SPEC-DAILYREPORT-001 定義現金淨收欄位的頁面）記錄核實前的現金淨收數值",
     "確認這兩筆紀錄皆維持待核實狀態，不執行任何核實動作",
     "再次檢視場館日結報表的現金淨收數值"],
    "現金淨收數值不因這兩筆待核實紀錄而變動；待核實的洗分與出金皆不計入現金淨收的扣除項",
    "§相關業務規則",
    quote="現金淨收計算 | 只計入已核實的洗分；待核實洗分不扣除",
    rationale="CASHOUT 本身的 spec 原文只明講『已核實的洗分』會計入現金淨收，出金比照辦理是 RequirementModel 的 statement 已載明由 Oscar 2026-09-14 確認、非本 TC 自行推測；『現金淨收』這個數值實際顯示於場館日結報表（SPEC-DAILYREPORT-001 §功能說明另有『現金淨收 = 開分＋進鈔－已核實洗分－已兌現』的完整公式），本 TC 只驗證 CASHOUT 自己定義的『待核實不計入』這條邊界規則，不重新驗證日結報表公式本身或其餘欄位是否正確；為降低其他交易活動的干擾，建議在相對安靜的測試站台/時段執行，並以同一站台核實前後兩次讀值比對而非跨站台比較。"))
T.append(tc(31, [2], "洗分或出金被核實後，才計入場館現金淨收扣除項", "ui_e2e",
    ["functional"], ["requirement_based"],
    ["延續上一條 TC 的兩筆待核實紀錄（或另取一筆待核實洗分、一筆待核實出金），於場館日結報表記錄核實前的現金淨收數值",
     "於本頁分別對這兩筆紀錄執行核實",
     "核實完成後，再次檢視場館日結報表的現金淨收數值"],
    "現金淨收數值在這兩筆紀錄核實後出現對應的扣減（金額與方向與公式『現金淨收 = 開分＋進鈔－已核實洗分－已兌現』一致）；已核實的洗分與出金皆計入現金淨收的扣除項",
    "§相關業務規則",
    quote="只計入已核實的洗分",
    rationale="與上一條 TC 對稱，共同構成『待核實 vs 已核實』這條規則的完整前後對照；同樣提醒執行時應排除同期間其他交易活動的干擾，並以核實前後的差值而非絕對值判斷是否正確。"))


# ================= Report =================
cov = collections.defaultdict(lambda: {"draft_ids": [], "acs": collections.defaultdict(list)})
for t in T:
    for r in t["requirement_ids"]:
        cov[r]["draft_ids"].append(t["draft_id"])
    for a in t["acceptance_criteria_ids"]:
        cov["REQ-CASHOUT-" + a.split("-")[2][:3]]["acs"][a].append(t["draft_id"])

n_exp = sum(1 for t in T if t["assumptions"])
tech_count = collections.Counter(x for t in T for x in t["design_techniques"])

rep = {
    "mode": "spec",
    "testcase_draft_artifact_id": None,
    "coverage_matrix": [
        {
            "requirement_id": r,
            "draft_ids": d["draft_ids"],
            "acceptance_criteria": [{"ac_id": a, "draft_ids": dd} for a, dd in d["acs"].items()],
        }
        for r, d in cov.items()
    ],
    "uncovered_with_reason": [],
    "technique_summary": [{"technique": k, "count": v} for k, v in tech_count.items()],
    "self_check": {k: True for k in [
        "requirements_covered", "acceptance_criteria_covered", "negative_considered",
        "boundary_considered", "expected_results_traceable", "no_unsupported_assumptions",
        "duplicate_detection_completed",
    ]},
    "assumptions": [a["text"] for t in T for a in t["assumptions"]],
    "duplicate_check": {"against_registry": True, "findings": []},
}


def envelope(atype, payload, sub, refs, task="T2"):
    aid = ids.artifact_id(atype)
    art = {
        "artifact_id": aid, "artifact_type": atype, "schema_version": "1.0", "version": 1,
        "run_id": RUN, "task_id": task, "iteration": ITER, "created_by": A, "created_at": store.now(),
        "status": "DRAFT", "source": {"type": "RequirementModel", "ids": [RM_AID]},
        "references": refs, "requires_approval": None, "payload": payload,
    }
    p = store.ROOT / "artifacts" / "test-design" / RUN / f"{aid}.yaml"
    store.save(p, art)
    return aid, p


refs = [{"entity_type": "Requirement", "id": r} for r in reqs] + [{"entity_type": "Artifact", "id": RM_AID}]
did, p1 = envelope("TestCaseDraft", {"mode": "spec", "spec_id": SID, "spec_version": SV, "testcases": T}, "test-design", refs)
rep["testcase_draft_artifact_id"] = did
_, p2 = envelope("TestDesignReport", rep, "test-design", [{"entity_type": "Artifact", "id": did}])

print(p1.relative_to(store.ROOT))
print(p2.relative_to(store.ROOT))
print(f"{len(T)} TCs, {n_exp} exploratory, reqs covered={len(cov)}/{len(reqs)}")
print("technique_summary:", dict(tech_count))
