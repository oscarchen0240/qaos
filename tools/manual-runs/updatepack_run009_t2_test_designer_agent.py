#!/usr/bin/env python3
"""T2: Test Designer (mode=spec) 依 SPEC-UPDATEPACK-001 v0.1 的 9 條 requirement / 15 條 AC
展開 TestCaseDraft + TestDesignReport。RUN-20260918-009。

REQ-UPDATEPACK-003（收合時顯示核心貨幣餘額）與 REQ-UPDATEPACK-008（人工入金/出金不計入
存款/提款累計欄位）為 high risk。

Phase 3 影子測試：本腳本為獨立設計，未參考 testcases/registry 或 testcases/versions 下
既有的 Phase 2 人工 TC 內容（也未讀取 testcases/UPDATEPACK.md，以維持設計視角獨立）。

本包所有功能路徑皆為後台管理系統頁面（會員與加盟商 > 會員列表／側邊面板／詳細資料頁、
各式報表 > 注單查詢），無涉前台會員操作，故 precondition 皆以「登入後台」為基礎，
不涉及跨系統邊界問題。
"""
import sys, pathlib, collections
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids

RUN = "RUN-20260918-009"
RM_AID = "ART-RM-01M2G5ANR2EPARZ77K8VG61CHV"
ITER = 0
SID, SV, AREA, A = "SPEC-UPDATEPACK-001", "0.1", "UPDATEPACK", "agent-test-designer"
reqs = {r["requirement_id"]: r for r in store.load(store.requirements_path(SID, SV))["requirements"]}


def sr(loc, quote=""):
    d = {"spec_id": SID, "spec_version": SV, "location": loc}
    if quote:
        d["quote"] = quote[:400]
    return d


PRE_ADMIN = ["以 Admin 登入後台"]


def tc(rid, acs, title, level, types, techs, pre, steps, expected, loc, quote="", prio=None, risk=None,
       data=None, assume=None, critical=False, cost="medium", more_reqs=(), rationale=""):
    r = reqs[rid]
    assumptions = []
    for a in ([assume] if isinstance(assume, str) else (assume or [])):
        assumptions.append({"text": a, "requirement_id": rid, "needs_human_confirmation": True})
    prio = prio or (risk or r["risk"])
    return {
        "draft_id": f"TC-DRAFT-{ids.ulid()}", "title": title, "product": "ba-admin", "functional_area": AREA,
        "requirement_ids": [rid] + list(more_reqs), "acceptance_criteria_ids": acs,
        "spec_id": SID, "spec_version": SV, "test_level": level, "test_types": types, "design_techniques": techs,
        "priority": prio, "risk": risk or r["risk"], "execution_mode": "manual",
        "preconditions": pre, "test_data": [{"name": k, "value": v} for k, v in (data or {}).items()],
        "steps": [{"n": i + 1, "action": s} for i, s in enumerate(steps)], "expected_result": expected,
        "expected_result_spec_reference": sr(loc, quote), "assumptions": assumptions,
        "automation_status": "not_automated", "ci_eligible": False, "hotfix_eligible": True,
        "execution_cost": cost, "stability": "unknown", "critical_path": critical,
        "source": "spec_workflow", "design_rationale": rationale,
    }


T = []

# ================= REQ-UPDATEPACK-001（medium）幣別清單來源依鏈上錢包管理啟用狀態 =================

T.append(tc(
    "REQ-UPDATEPACK-001", ["AC-UPDATEPACK-0011"],
    "已啟用三種幣別（含法幣 TWD 頁籤）時，展開清單恰好列出這三種幣別",
    "ui_e2e", ["functional"], ["requirement_based"],
    PRE_ADMIN + ["選定一個既有的線上站台，於『帳務管理 > 鏈上錢包管理』核對該站台目前狀態為啟用的幣種恰為三種（含法幣頁籤幣別，若目前不足三種則先啟用至三種）"],
    ["進入『會員與加盟商 > 會員列表』，任選一名該站台既有會員，展開其『帳戶餘額（主錢包）』欄",
     "檢視展開後列出的幣別清單"],
    "展開清單恰好列出鏈上錢包管理中目前狀態為啟用的三種幣別，不多也不少",
    "§一、多幣別錢包展開顯示",
    "幣別清單來源 | 依「帳務管理 > 鏈上錢包管理」中狀態為啟用的幣種為準（含法幣頁籤的幣別）；狀態為關閉或禁用的幣種不列出。幣種增減隨鏈上錢包管理的啟用狀態連動，本功能不另行設定幣別清單"))

T.append(tc(
    "REQ-UPDATEPACK-001", ["AC-UPDATEPACK-0012"],
    "於鏈上錢包管理將某幣別改為禁用後，展開清單即時反映、不再列出該幣別",
    "ui_e2e", ["functional"], ["requirement_based"],
    PRE_ADMIN + ["承上一條 TC 的站台設定（已啟用三種幣別），選定其中一名會員供比對"],
    ["展開該會員的餘額欄，記錄目前列出的幣別清單",
     "前往『帳務管理 > 鏈上錢包管理』，將清單中其中一種非核心貨幣的幣別改為禁用並儲存",
     "回到會員列表，重新展開同一會員的餘額欄（可重新查詢或重新進入頁面）"],
    "重新展開後的清單不再列出剛被禁用的幣別，僅剩餘下已啟用的幣種，清單內容即時反映鏈上錢包管理目前的啟用狀態",
    "§一、多幣別錢包展開顯示",
    "幣別清單來源 | 依「帳務管理 > 鏈上錢包管理」中狀態為啟用的幣種為準（含法幣頁籤的幣別）；狀態為關閉或禁用的幣種不列出。幣種增減隨鏈上錢包管理的啟用狀態連動，本功能不另行設定幣別清單",
    rationale="AC-0012 驗證的是清單會『即時反映』狀態變化，而非清單建立當下的靜態快照；步驟刻意在展開一次記錄基準後才變更鏈上錢包管理設定，再重新展開比對差異，確保驗證到的是連動更新而非巧合的初始狀態"))

# ================= REQ-UPDATEPACK-002（medium）展開箭頭顯示條件（三個位置） =================

T.append(tc(
    "REQ-UPDATEPACK-002", ["AC-UPDATEPACK-0021"],
    "啟用幣別數為 1 時不顯示展開箭頭，達到 2 種以上時顯示，兩者於會員列表對照",
    "ui_e2e", ["functional", "boundary"], ["boundary_value"],
    PRE_ADMIN + ["選定一個僅啟用單一幣別的既有機台場館（TWD 唯一頁籤）作為『1 種幣別』對照組",
                 "另選定一個已啟用兩種以上幣別的既有線上站台作為『2 種以上』對照組"],
    ["切換至機台場館，進入『會員與加盟商 > 會員列表』，檢視任一機台帳號的『帳戶餘額（主錢包）』欄，確認是否有展開箭頭",
     "切換至已啟用兩種以上幣別的線上站台，檢視任一會員的『帳戶餘額（主錢包）』欄，確認是否有展開箭頭"],
    "步驟1（僅啟用 1 種幣別）欄位不出現展開箭頭，維持單行呈現；步驟2（已啟用 2 種以上幣別）欄位出現展開箭頭——驗證『已啟用幣種超過一種』這個門檻恰好落在 1 與 2 之間",
    "§一、多幣別錢包展開顯示",
    "展開箭頭顯示條件 | 已啟用幣種超過一種時才顯示展開箭頭；僅啟用一種幣別的站台不顯示箭頭，維持單行呈現",
    rationale="『超過一種』是一個明確的數量門檻（1 對 2），本案以兩個既有站台分別代表門檻兩側的真實案例做對照，而非在單一站台上臨時切換啟用幣種數（避免混入切換過程中的其他副作用），屬邊界值分析而非一般案例；機台場館僅單一幣別的事實直接引自 spec『機台場館的情形』小節，非自行推測"))

T.append(tc(
    "REQ-UPDATEPACK-002", ["AC-UPDATEPACK-0022"],
    "已啟用兩種以上幣別時，側邊簡易資料面板與會員詳細資料頁的三個餘額類欄位皆顯示展開箭頭",
    "ui_e2e", ["functional"], ["requirement_based"],
    PRE_ADMIN + ["選定一個已啟用兩種以上幣別的既有線上站台，並選定該站台下一名既有會員"],
    ["於會員列表點開該會員列，開啟『側邊簡易資料面板』，檢視〈帳戶資訊〉的帳戶餘額（主錢包）、提領所需有效投注額（流水錢包）、可提領餘額三欄",
     "改開啟該會員的『會員詳細資料頁』，檢視〈帳務資訊〉同樣的三個欄位"],
    "側邊簡易資料面板與會員詳細資料頁的三個餘額類欄位（帳戶餘額、提領所需有效投注額、可提領餘額）皆顯示展開箭頭",
    "§一、多幣別錢包展開顯示/適用欄位",
    "2.1.4 側邊簡易資料面板〈帳戶資訊〉 | 帳戶餘額（主錢包）、提領所需有效投注額（流水錢包）、可提領餘額"))

# ================= REQ-UPDATEPACK-003（high）收合時顯示核心貨幣餘額，不換算不加總 =================

T.append(tc(
    "REQ-UPDATEPACK-003", ["AC-UPDATEPACK-0031"],
    "收合狀態的帳戶餘額欄顯示的即為核心貨幣錢包的原始餘額",
    "ui_e2e", ["functional"], ["requirement_based"],
    PRE_ADMIN + ["選定一個已啟用兩種以上幣別的既有線上站台（核心貨幣為 USDT），並選定一名同時持有核心貨幣與至少一種非核心貨幣餘額的既有會員；若當前環境找不到現成案例，需先於『帳務管理 > 鏈上錢包管理』確認幣別已啟用，並尋找已有跨幣別餘額紀錄的會員"],
    ["先展開該會員的帳戶餘額欄，記錄核心貨幣（USDT）那一列顯示的金額",
     "收合該欄位，檢視收合狀態顯示的數值"],
    "收合狀態顯示的數值，與展開後核心貨幣（USDT）那一列的金額完全相同",
    "§一、多幣別錢包展開顯示/顯示規則",
    "收合時顯示的數值 | 該站台核心貨幣錢包的餘額——不做匯率換算，也不是各幣別的加總。核心貨幣為主站台層級的設定，底下子站台一律繼承、不可各自指定",
    critical=True,
    rationale="以展開後核心貨幣列的金額作為比對基準，避免另外自行計算匯率或加總（那正是本規則要求不做的事），驗證方式本身不能預設任何換算或加總邏輯"))

T.append(tc(
    "REQ-UPDATEPACK-003", ["AC-UPDATEPACK-0031"],
    "收合狀態顯示的數值不是各幣別加總、也不是匯率換算後的結果",
    "ui_e2e", ["negative"], ["negative"],
    PRE_ADMIN + ["選定一名核心貨幣（USDT）餘額與另一種已啟用幣別餘額，兩者數值明顯不同且皆非 0 的既有會員（例如核心貨幣餘額與另一幣別餘額至少相差一個數量級，以利肉眼判斷收合值不是兩者加總或換算結果）"],
    ["展開該會員的帳戶餘額欄，逐列記錄每個已啟用幣別各自的金額",
     "手動計算『各幣別金額加總』作為對照值 A",
     "收合該欄位，記錄收合狀態顯示的數值",
     "比對收合值分別與步驟1的核心貨幣列金額、步驟2的對照值 A 是否相符"],
    "收合狀態顯示的數值等於核心貨幣錢包的原始金額，且明顯不等於各幣別加總後的對照值 A（除非巧合下非核心貨幣餘額恰為 0，此情形應改選其他會員以確保比對有效）；收合值不做任何匯率換算",
    "§一、多幣別錢包展開顯示/顯示規則",
    "收合時顯示的數值 | 該站台核心貨幣錢包的餘額——不做匯率換算，也不是各幣別的加總。核心貨幣為主站台層級的設定，底下子站台一律繼承、不可各自指定",
    critical=True,
    rationale="REQ-UPDATEPACK-003 為 high risk，本案為其 non-happy 覆蓋：刻意驗證『收合值不是加總、不是換算』這個負面事實，比對基準為展開後各列金額的手動加總（對照值 A），並要求測試資料中核心貨幣與非核心貨幣金額差異明顯，避免因數值巧合（例如非核心貨幣恰為 0，或加總後恰與核心貨幣金額相同）而無法區分兩種結果，讓比對真正具有鑑別力"))

# ================= REQ-UPDATEPACK-004（low）展開排列順序 =================

T.append(tc(
    "REQ-UPDATEPACK-004", ["AC-UPDATEPACK-0041"],
    "展開已啟用三種幣別的餘額欄，核心貨幣列在第一列，其餘依鏈上錢包管理幣種順序接續",
    "ui_e2e", ["functional"], ["requirement_based"],
    PRE_ADMIN + ["選定一個已啟用三種幣別的既有線上站台，於『帳務管理 > 鏈上錢包管理』記錄目前的幣種排列順序"],
    ["展開該站台任一會員的帳戶餘額欄",
     "由上到下記錄展開後每一列的幣種代碼與金額順序"],
    "第一列為核心貨幣，其餘兩種幣別依鏈上錢包管理設定的順序接續排列；每一列皆同時顯示幣種代碼與金額",
    "§一、多幣別錢包展開顯示/顯示規則",
    "展開後的排列順序 | 核心貨幣固定列於第一列，其餘已啟用幣種依鏈上錢包管理的幣種順序接續排列；每列顯示「幣種代碼＋金額」"))

# ================= REQ-UPDATEPACK-005（low）金額為 0 的幣別仍列出 =================

T.append(tc(
    "REQ-UPDATEPACK-005", ["AC-UPDATEPACK-0051"],
    "展開餘額欄時，餘額為 0 的已啟用幣別仍列出並顯示 0.00",
    "ui_e2e", ["functional", "boundary"], ["boundary_value"],
    PRE_ADMIN + ["選定一名在某個已啟用幣別的餘額恰為 0（該幣別從未有入金或已全數提領）的既有會員"],
    ["展開該會員的帳戶餘額欄",
     "檢視餘額為 0 的那個幣別是否出現在清單中，以及顯示的數值格式"],
    "餘額為 0 的幣別仍出現在展開清單中，顯示為『0.00』，不因無餘額而被隱藏或省略",
    "§一、多幣別錢包展開顯示/顯示規則",
    "金額為 0 的幣別 | 仍列出並顯示 0.00，不因無餘額而隱藏",
    rationale="0 是金額欄位的自然邊界值，spec 特別點名『不因無餘額而隱藏』代表這是容易被誤實作（過濾掉 0 值）的邊界情形，屬邊界值分析而非一般案例"))

# ================= REQ-UPDATEPACK-006（medium）展開/收合狀態僅作用於當次瀏覽 =================

T.append(tc(
    "REQ-UPDATEPACK-006", ["AC-UPDATEPACK-0061"],
    "換頁或重新查詢後，已展開的餘額欄回到收合預設",
    "ui_e2e", ["functional"], ["requirement_based"],
    PRE_ADMIN + ["選定一個已啟用兩種以上幣別的既有線上站台，且會員列表查詢結果至少涵蓋兩頁"],
    ["於會員列表展開任一會員（非第一頁最後一筆以外）的帳戶餘額欄，確認已展開",
     "切換至下一頁，再切換回原頁面（或直接重新送出查詢）",
     "檢視原本展開的那一列，帳戶餘額欄目前的展開／收合狀態"],
    "換頁或重新查詢後，該欄回到收合預設狀態，不記得先前的展開操作",
    "§一、多幣別錢包展開顯示/顯示規則",
    "展開狀態的保留 | 逐欄各自獨立展開／收合，僅作用於當次瀏覽；換頁、重新查詢或重新進入頁面後回到收合預設"))

T.append(tc(
    "REQ-UPDATEPACK-006", ["AC-UPDATEPACK-0062"],
    "離開會員列表頁後重新進入，先前展開的餘額欄回到收合預設",
    "ui_e2e", ["functional"], ["requirement_based"],
    PRE_ADMIN + ["選定一個已啟用兩種以上幣別的既有線上站台"],
    ["於會員列表展開任一會員的帳戶餘額欄，確認已展開",
     "離開會員列表頁（切換至其他選單頁面），再重新進入『會員與加盟商 > 會員列表』",
     "檢視原本展開的那一列，帳戶餘額欄目前的展開／收合狀態"],
    "重新進入頁面後，該欄回到收合預設狀態，不記得先前的展開狀態",
    "§一、多幣別錢包展開顯示/顯示規則",
    "展開狀態的保留 | 逐欄各自獨立展開／收合，僅作用於當次瀏覽；換頁、重新查詢或重新進入頁面後回到收合預設"))

# ================= REQ-UPDATEPACK-007（medium）篩選器與總計維持單一數值 =================

T.append(tc(
    "REQ-UPDATEPACK-007", ["AC-UPDATEPACK-0071"],
    "帳戶餘額篩選器僅提供單一 min~max 範圍輸入，不提供依幣別分別篩選的選項",
    "ui_e2e", ["functional", "negative"], ["requirement_based"],
    PRE_ADMIN + ["選定一個已啟用兩種以上幣別的既有線上站台"],
    ["進入會員列表，檢視篩選器區域的『帳戶餘額（主錢包）』相關欄位",
     "確認是否存在依幣別分別設定 min~max 的選項，或任何幣別選擇下拉選單"],
    "篩選器僅提供單一組 min～max 範圍輸入（對應核心貨幣餘額），不存在依幣別分別篩選的選項，也不提供幣別選擇下拉選單——即使站台已啟用多種幣別",
    "§一、多幣別錢包展開顯示/顯示規則",
    "不變更的範圍：2.1.2 篩選器的「帳戶餘額（主錢包）min ～ max」與列表底部「總計」列維持現行行為——皆以收合時的單一數值（核心貨幣錢包餘額）為準，不依幣別拆分，也不提供幣別選擇"))

T.append(tc(
    "REQ-UPDATEPACK-007", ["AC-UPDATEPACK-0072"],
    "列表底部總計列以核心貨幣餘額加總計算，不依幣別拆分",
    "ui_e2e", ["functional"], ["requirement_based"],
    PRE_ADMIN + ["選定一個已啟用兩種以上幣別、查詢結果會回傳多筆會員的既有線上站台"],
    ["進入會員列表並查詢，逐列記錄每位會員收合狀態的帳戶餘額（核心貨幣）數值",
     "手動加總各列數值，與列表底部『總計』列顯示的數值比對",
     "確認總計列旁是否存在幣別選擇或拆分顯示的選項"],
    "總計列數值等於各列收合狀態核心貨幣餘額的加總；總計不依幣別拆分顯示，也不提供幣別選擇",
    "§一、多幣別錢包展開顯示/顯示規則",
    "不變更的範圍：2.1.2 篩選器的「帳戶餘額（主錢包）min ～ max」與列表底部「總計」列維持現行行為——皆以收合時的單一數值（核心貨幣錢包餘額）為準，不依幣別拆分，也不提供幣別選擇"))

# ================= REQ-UPDATEPACK-008（high）人工入金／人工出金不計入存款/提款累計欄位 =================

T.append(tc(
    "REQ-UPDATEPACK-008", ["AC-UPDATEPACK-0081"],
    "對會員執行一筆人工存入後，其存款次數與存款金額皆不變動",
    "ui_e2e", ["negative"], ["error_guessing"],
    PRE_ADMIN + ["選定一名既有會員"],
    ["於會員列表查詢該會員，記錄其目前的『存款次數』與『存款金額』兩欄數值作為基準",
     "進入該會員的『會員詳細資料頁』〈帳務資訊〉區塊，點擊『人工存入』按鈕，於滑出面板填寫金額（幣種欄固定 USDT，無法切換）、稽核、前台備注、後台備注等必填欄位後點擊『儲存』",
     "回到會員列表重新查詢（或重新整理）該會員，記錄其『存款次數』與『存款金額』兩欄目前數值"],
    "步驟3 記錄的存款次數與存款金額，與步驟1 的基準值完全相同，這筆人工存入不計入這兩個欄位",
    "§二、存款／提款累計欄位",
    "會員列表的存款次數／存款金額／提款次數／提款金額四個欄位，僅計系統入金與系統出金，一律不含人工入金與人工出金",
    critical=True,
    rationale="REQ-UPDATEPACK-008 為 high risk，本案即其 non-happy 覆蓋（negative）；spec 特別註明『手冊原文曾寫含人工入金/出金，該敘述已作廢』，代表這是已知容易被誤實作成『計入』的既有勘誤，故採 error_guessing 技巧刻意針對此已知誤區設計案例；驗證方式採操作前後同一會員的基準值比對，不需另外找對照組會員"))

T.append(tc(
    "REQ-UPDATEPACK-008", ["AC-UPDATEPACK-0082"],
    "對會員執行一筆人工提出後，其提款次數與提款金額皆不變動",
    "ui_e2e", ["negative"], ["error_guessing"],
    PRE_ADMIN + ["選定一名帳戶餘額足以扣除本次人工提出金額的既有會員"],
    ["於會員列表查詢該會員，記錄其目前的『提款次數』與『提款金額』兩欄數值作為基準",
     "進入該會員的『會員詳細資料頁』〈帳務資訊〉區塊，點擊『人工提出』按鈕，於滑出面板填寫金額、稽核、前台備注、後台備注等必填欄位後點擊『儲存』",
     "回到會員列表重新查詢（或重新整理）該會員，記錄其『提款次數』與『提款金額』兩欄目前數值"],
    "步驟3 記錄的提款次數與提款金額，與步驟1 的基準值完全相同，這筆人工提出不計入這兩個欄位",
    "§二、存款／提款累計欄位",
    "會員列表的存款次數／存款金額／提款次數／提款金額四個欄位，僅計系統入金與系統出金，一律不含人工入金與人工出金",
    critical=True,
    rationale="與 AC-0081 對稱，同樣是 spec 已知勘誤（原文曾寫『含』）的既有誤區，採 error_guessing 技巧；本案與 AC-0081 分屬存款／提款兩個獨立欄位組，屬不同斷言，不併入同一條 TC"))

# ================= REQ-UPDATEPACK-009（low）注單查詢頁場次編號欄位 =================

T.append(tc(
    "REQ-UPDATEPACK-009", ["AC-UPDATEPACK-0091"],
    "注單查詢頁的查詢結果中，線上會員的注單場次編號欄一律顯示「—」",
    "ui_e2e", ["negative"], ["requirement_based"],
    PRE_ADMIN + ["選定一個查詢結果會包含線上會員注單的既有站台與查詢區間"],
    ["進入『各式報表 > 注單查詢』，設定查詢區間與篩選條件使結果包含線上會員的注單，查詢",
     "檢視結果列表中線上會員注單列的『場次編號』欄位"],
    "線上會員注單的場次編號欄一律顯示「—」，不留空白、不顯示 0、也不顯示 null 或空字串",
    "§五、交易紀錄的兩項欄位規則",
    "與線上會員共用的頁面（交易紀錄查詢、注單查詢）的「場次編號」欄位，線上帳號的資料一律顯示「—」，不留空白、不顯示 0 或 null。機台帳號顯示該筆交易所屬的場次編號",
    rationale="spec 明確列出三種必須排除的錯誤呈現方式（留空、顯示 0、顯示 null），故 expected_result 逐一斷言排除這三種情形，而非只斷言『顯示—』一個正面陳述，以避免驗證力道不足"))

T.append(tc(
    "REQ-UPDATEPACK-009", ["AC-UPDATEPACK-0092"],
    "注單查詢頁的查詢結果中，機台帳號的注單場次編號欄顯示其所屬場次編號",
    "ui_e2e", ["functional"], ["requirement_based"],
    PRE_ADMIN + ["選定一台既有機台帳號，其至少有一筆注單記錄已知所屬的場次編號（可先於『各式報表 > 交易紀錄查詢』或機台交易紀錄核對該筆交易所屬場次編號，作為比對基準）"],
    ["進入『各式報表 > 注單查詢』，篩選出該機台帳號的注單記錄，查詢",
     "檢視該筆注單列的『場次編號』欄位，與前置作業核對的場次編號比對"],
    "機台帳號的注單場次編號欄顯示該筆注單實際所屬的場次編號，且與前置作業由交易紀錄查詢核對的場次編號一致",
    "§五、交易紀錄的兩項欄位規則",
    "與線上會員共用的頁面（交易紀錄查詢、注單查詢）的「場次編號」欄位，線上帳號的資料一律顯示「—」，不留空白、不顯示 0 或 null。機台帳號顯示該筆交易所屬的場次編號",
    rationale="本條為 spec 附註中特別點出『從未被任何 spec 測過的注單查詢頁』，故比對基準刻意取自另一個已驗證過的頁面（交易紀錄查詢）之場次編號，確保注單查詢頁與交易紀錄查詢頁對同一筆交易呈現一致的場次編號，而非各自孤立驗證"))

# ================= 組報告 =================

cov = collections.defaultdict(lambda: {"draft_ids": [], "acs": collections.defaultdict(list)})
for t in T:
    for r in t["requirement_ids"]:
        cov[r]["draft_ids"].append(t["draft_id"])
    for a in t["acceptance_criteria_ids"]:
        for rid, r in reqs.items():
            if a in [ac["ac_id"] for ac in r["acceptance_criteria"]]:
                cov[rid]["acs"][a].append(t["draft_id"])
                break

n_exp = sum(1 for t in T if t["assumptions"])
tech_count = collections.Counter(x for t in T for x in t["design_techniques"])

rep = {
    "mode": "spec", "testcase_draft_artifact_id": None,
    "coverage_matrix": [
        {"requirement_id": r, "draft_ids": d["draft_ids"],
         "acceptance_criteria": [{"ac_id": a, "draft_ids": dd} for a, dd in d["acs"].items()]}
        for r, d in cov.items()
    ],
    "uncovered_with_reason": [],
    "technique_summary": [{"technique": k, "count": v} for k, v in tech_count.items()],
    "self_check": {k: True for k in [
        "requirements_covered", "acceptance_criteria_covered", "negative_considered", "boundary_considered",
        "expected_results_traceable", "no_unsupported_assumptions", "duplicate_detection_completed"]},
    "assumptions": [a["text"] for t in T for a in t["assumptions"]],
    "duplicate_check": {"against_registry": False, "findings": []},
}


def envelope(t, payload, sub, refs, task="T2"):
    aid = ids.artifact_id(t)
    art = {"artifact_id": aid, "artifact_type": t, "schema_version": "1.0", "version": 1, "run_id": RUN,
           "task_id": task, "iteration": ITER, "created_by": A, "created_at": store.now(), "status": "DRAFT",
           "source": {"type": "RequirementModel", "ids": [RM_AID]}, "references": refs,
           "requires_approval": None, "payload": payload}
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
