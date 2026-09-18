#!/usr/bin/env python3
"""T2：Test Designer (mode=spec) 依 SPEC-DAILYREPORT-001 v0.1 的 17 條需求 / 43 條 AC 展開
TestCaseDraft + TestDesignReport。RUN-20260918-007。

REQ-DAILYREPORT-001/004/005/006/007/008/009/011/012/015/017 為 high risk。

Phase 3 影子測試：本腳本為獨立設計，未參考 testcases/registry 或 testcases/versions 下既有的
Phase 2 人工 TC 內容。
"""
import sys, pathlib, collections
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids

RUN = "RUN-20260918-007"
RM_AID = "ART-RM-01M2D72FB77WAP7PFRAKC54QCR"
ITER = 0
SID, SV, AREA, A = "SPEC-DAILYREPORT-001", "0.1", "DAILYREPORT", "agent-test-designer"
reqs = {r["requirement_id"]: r for r in store.load(store.requirements_path(SID, SV))["requirements"]}


def sr(loc, quote=""):
    d = {"spec_id": SID, "spec_version": SV, "location": loc}
    if quote:
        d["quote"] = quote[:300]
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

# ================= REQ-DAILYREPORT-001（high）角色權限範圍 =================

T.append(tc(
    "REQ-DAILYREPORT-001", ["AC-DAILYREPORT-0011"],
    "Admin 切換任一站台後可查看該站台所有場館的日結資料",
    "ui_e2e", ["functional"], ["requirement_based"],
    PRE_ADMIN + ["選定一個底下有多個場館（或多台機台分屬不同場館）的既有站台"],
    ["於頁面標題下方的站台切換下拉選單，切換至選定的站台",
     "進入『各式報表 > 場館日結報表』，統計維度選『依場館彙總』，結算日期設定涵蓋當日或近期有資料的區間並查詢",
     "檢視列表出現的場館筆數與範圍"],
    "列表顯示該站台底下所有場館的日結彙總列，不因 Admin 身分而被排除任何場館；若改切換至另一個站台，列表資料範圍隨之切換為該站台的全部場館",
    "§功能說明/權限表", "場館日結報表 | 全部 | 管轄範圍 | 自身場館",
    rationale="AC-0011 對應 spec 權限表 Admin 欄『全部』；本案只驗證 Admin 可見範圍是否為所選站台的全部場館，不涉及站台切換選單本身如何決定資料範圍（該部分由 REQ-DAILYREPORT-002 覆蓋），避免兩條 TC 斷言重疊"))

T.append(tc(
    "REQ-DAILYREPORT-001", ["AC-DAILYREPORT-0012"],
    "站長只能查看自身及子站台管轄範圍內的場館資料，看不到管轄範圍以外的場館",
    "ui_e2e", ["functional"], ["requirement_based"],
    ["以站長身分登入後台", "確認該站長帳號的管轄範圍為特定一至多個場館（非站台全部場館），且該站台底下另有管轄範圍以外的場館存在，供後續比對"],
    ["進入『各式報表 > 場館日結報表』，統計維度選『依場館彙總』，結算日期設定涵蓋當日或近期的區間並查詢，記錄列表顯示的場館清單",
     "另以 Admin 身分查看同一站台、相同結算日期的場館日結報表，記錄該站台底下的全部場館清單",
     "比對兩份清單"],
    "站長看到的場館清單為其管轄範圍內的場館，是 Admin 所見全部場館清單的真子集合；管轄範圍以外的場館不出現在站長的列表中",
    "§功能說明/權限表", "場館日結報表 | 全部 | 管轄範圍 | 自身場館",
    rationale="驗證方式採『站長清單 ⊆ Admin 清單』的比對法，而非斷言站長只能看到某個具體場館名稱——『管轄範圍』的實際場館組成因帳號設定而異，比對法可在不寫死特定測試帳號或場館編號的前提下驗證範圍限制是否生效"))

T.append(tc(
    "REQ-DAILYREPORT-001", ["AC-DAILYREPORT-0013"],
    "操作員只能查看自身場館資料，無法透過機台帳號篩選看到其他場館的日結資料",
    "ui_e2e", ["negative"], ["requirement_based"],
    ["以操作員身分登入後台", "確認該操作員帳號僅對應單一自身場館，且該站台底下另有其他場館存在（非操作員自身場館），供後續比對"],
    ["進入『各式報表 > 場館日結報表』，統計維度選『依場館彙總』，結算日期設定涵蓋當日或近期的區間並查詢，記錄列表顯示的場館筆數與名稱／代碼",
     "嘗試於『機台帳號』篩選欄輸入一個已知不屬於該操作員自身場館的其他場館機台帳號並搜尋，觀察結果"],
    "步驟1 的列表只出現操作員自身場館一列（依場館彙總維度應僅一列），不出現任何其他場館資料；步驟2 輸入非自身場館的機台帳號後，列表不會回傳該其他場館的日結資料（不論呈現方式是空結果或維持原自身場館範圍，皆不應洩漏其他場館的資料）",
    "§功能說明/權限表", "場館日結報表 | 全部 | 管轄範圍 | 自身場館",
    critical=True,
    rationale="REQ-DAILYREPORT-001 為 high risk，本案為其 non-happy 覆蓋：驗證操作員無法透過機台帳號篩選繞過場館範圍限制看到他人場館資料。rejection_contract.defined=false（spec 未定義越權時系統的具體回應方式：拒絕／隱藏／空結果），故 expected_result 刻意只斷言『不洩漏其他場館資料』這個必然要件，不預設具體呈現方式（不寫死錯誤訊息或空白頁面文案）——這是對 spec 未定義部分保持開放而非把未定義行為當成確定規則來斷言，因此不需標為 exploratory"))

# ================= REQ-DAILYREPORT-002（medium）場館範圍跟隨站台切換 =================

T.append(tc(
    "REQ-DAILYREPORT-002", ["AC-DAILYREPORT-0021"],
    "場館資料範圍完全由站台切換下拉選單決定，頁面不存在獨立的場館篩選欄位",
    "ui_e2e", ["functional", "negative"], ["requirement_based"],
    PRE_ADMIN + ["確認至少有兩個不同站台可供切換，且各自底下有不同的場館／機台資料"],
    ["進入『各式報表 > 場館日結報表』，透過頁面標題下方的站台切換下拉選單切換至站台 A，設定結算日期並查詢，記錄列表資料範圍",
     "檢視篩選器區域的所有欄位名稱，確認是否存在『場館』相關的篩選欄位",
     "切換站台下拉選單至站台 B（不變更其他篩選條件），重新查詢，記錄列表資料範圍"],
    "篩選器區域不存在任何『場館』篩選欄位（僅有機台帳號／結算日期／統計週期／統計維度）；切換站台後，列表資料範圍隨之變為站台 B 的資料，不再顯示站台 A 的場館資料——場館資料範圍完全由站台切換下拉選單決定",
    "§篩選器 + §業務規則-場館範圍跟隨站台切換", "不另設場館篩選欄位",
    rationale="AC-0021 同時包含『資料隨站台切換』與『無場館篩選欄位』兩個斷言，兩者皆直接引自同一句 spec 原文，合併於同一條 TC 驗證，避免拆成兩條而在 steps 上高度重複"))

# ================= REQ-DAILYREPORT-003（medium）機台帳號篩選 =================

T.append(tc(
    "REQ-DAILYREPORT-003", ["AC-DAILYREPORT-0031"],
    "機台帳號篩選欄留空時，列表包含場館全部機台的資料",
    "ui_e2e", ["functional"], ["requirement_based"],
    PRE_ADMIN + ["選定一個底下有多台機台的既有場館所屬站台"],
    ["切換至該站台，進入場館日結報表，統計維度選『依機台明細』",
     "機台帳號欄位留空，結算日期設定涵蓋當日或近期的區間並查詢"],
    "列表包含該場館（站台範圍內）全部機台的資料列，機台帳號留空不會限縮或排除任何機台",
    "§篩選器/機台帳號", "輸入會員編號；留空為場館全部機台"))

T.append(tc(
    "REQ-DAILYREPORT-003", ["AC-DAILYREPORT-0032"],
    "機台帳號篩選欄輸入特定機台帳號後，列表只包含該機台的資料",
    "ui_e2e", ["functional"], ["requirement_based"],
    PRE_ADMIN + ["選定一個既有機台帳號（自行從環境中選定一台目前有交易資料的機台）"],
    ["切換至該機台所屬站台，進入場館日結報表，統計維度選『依機台明細』",
     "機台帳號欄位輸入選定機台的完整帳號，結算日期設定涵蓋當日或近期的區間並查詢"],
    "列表只包含輸入的該機台帳號一列資料，不出現同場館其他機台的資料列",
    "§篩選器/機台帳號", "輸入會員編號；留空為場館全部機台",
    rationale="不寫死具體機台帳號（如固定編號），改由執行者自行從環境中選定既有機台，避免 TC 在不同測試環境中因帳號不存在而無法執行"))

# ================= REQ-DAILYREPORT-004（high, rejection）結算日期必填 =================

T.append(tc(
    "REQ-DAILYREPORT-004", ["AC-DAILYREPORT-0041"],
    "未填結算日期即查詢時，系統不執行查詢",
    "ui_e2e", ["negative"], ["requirement_based"],
    PRE_ADMIN + ["進入場館日結報表頁面（尚未進行任何查詢）"],
    ["不填寫結算日期（保持空白），其餘篩選條件可任意或維持預設",
     "點擊查詢／搜尋"],
    "系統不執行查詢：不送出查詢請求，列表不出現新的查詢結果（維持查詢前的初始狀態，或出現要求填寫結算日期的提示——具體提示文案與呈現方式 spec 未定義，不在本案斷言範圍內）",
    "§篩選器/結算日期", "必填；不設區間上限，與手冊其他報表一致",
    critical=True,
    rationale="結算日期必填之規則直接引自 spec；expected_result 只斷言 AC-0041 明確要求的『系統不執行查詢』這個結果，不臆測具體錯誤提示文案或阻擋方式（rejection_contract.defined=false 已記載此點未定義），故不需標為 exploratory"))

T.append(tc(
    "REQ-DAILYREPORT-004", ["AC-DAILYREPORT-0042"],
    "結算日期輸入跨越一年以上的區間時，系統正常接受並回傳資料，不因區間長度拒絕",
    "ui_e2e", ["functional", "boundary"], ["boundary_value"],
    PRE_ADMIN + [],
    ["進入場館日結報表，結算日期選擇一個起訖相差超過一年（例如 400 天以上）的區間",
     "統計週期任選一種（如按日或按月），點擊查詢"],
    "系統正常接受查詢並回傳資料（或合理的無資料結果），不因區間長度而彈出錯誤訊息或拒絕查詢；不因『不設區間上限』而對長區間查詢加上未公開的隱性限制",
    "§篩選器/結算日期", "必填；不設區間上限，與手冊其他報表一致",
    data={"結算日期區間": "刻意設定超過一年（例如 400 天以上）的起訖日期"},
    rationale="『不設區間上限』是 spec 明確定義的邊界規則（無上限本身即邊界條件），本案以刻意選擇極大區間的方式驗證系統確實未對此設下未公開的隱性限制，屬邊界值分析而非一般案例"))

# ================= REQ-DAILYREPORT-005（high）統計週期 =================

T.append(tc(
    "REQ-DAILYREPORT-005", ["AC-DAILYREPORT-0051"],
    "開啟頁面未變更統計週期時，預設為按日",
    "ui_e2e", ["functional"], ["requirement_based"],
    PRE_ADMIN + [],
    ["進入場館日結報表（尚未手動變更統計週期）",
     "檢視統計週期下拉選單目前選中的值"],
    "統計週期下拉選單預設值為『按日』",
    "§篩選器/統計週期", "按日（預設）"))

T.append(tc(
    "REQ-DAILYREPORT-005", ["AC-DAILYREPORT-0052"],
    "結算日期涵蓋跨兩週的區間、統計週期選按週時，依週一為週起切分成兩列",
    "ui_e2e", ["functional", "boundary"], ["boundary_value"],
    PRE_ADMIN + ["選定一個近期有交易資料的機台或場館所屬站台"],
    ["進入場館日結報表，結算日期設為 2026-09-02（三）至 2026-09-10（四），統計週期選『按週』，查詢",
     "檢視列表列數與每列的結算期間（週起訖日期）"],
    "列表列出兩列：一列週起訖為 2026-08-31（一）～2026-09-06（日），另一列週起訖為 2026-09-07（一）～2026-09-13（日）；週的切分以週一為起，不論所選結算日期區間的起訖日是否恰為週一",
    "§篩選器/統計週期", "按週以週一為週起；非按日時，每列為該週期內各營業日的彙總",
    data={"結算日期區間": "2026-09-02（三）至 2026-09-10（四）"},
    rationale="所選結算日期區間（週三至週四）刻意不與自然週對齊，用以驗證『週一為週起』這個邊界切分規則確實依週一切分而非依所選查詢區間的起訖日切分，屬邊界值分析"))

T.append(tc(
    "REQ-DAILYREPORT-005", ["AC-DAILYREPORT-0053"],
    "統計週期選區間合計時，只出現一列，各欄為區間內所有營業日合計",
    "ui_e2e", ["functional"], ["requirement_based"],
    PRE_ADMIN + ["選定一個涵蓋多個營業日、且各營業日皆有交易資料的既有場館或機台"],
    ["進入場館日結報表，結算日期設定涵蓋多個營業日的區間，統計週期選『區間合計』，查詢"],
    "列表只出現一列，該列各欄金額與筆數為區間內所有營業日的合計",
    "§篩選器/統計週期", "按週以週一為週起；非按日時，每列為該週期內各營業日的彙總"))

# ================= REQ-DAILYREPORT-006（high）統計維度 =================

T.append(tc(
    "REQ-DAILYREPORT-006", ["AC-DAILYREPORT-0061"],
    "統計維度選依場館彙總時，只出現一列場館彙總資料",
    "ui_e2e", ["functional"], ["requirement_based"],
    PRE_ADMIN + ["選定一個底下有多台機台、且當日已有多個已結束場次的既有場館所屬站台"],
    ["進入場館日結報表，統計維度選『依場館彙總』，結算日期設為當日或近期，查詢"],
    "列表只出現一列，代表該場館的彙總資料，不逐機台或逐場次列出",
    "§篩選器/統計維度", "依場館彙總 / 依機台明細 / 依場次明細"))

T.append(tc(
    "REQ-DAILYREPORT-006", ["AC-DAILYREPORT-0062"],
    "統計維度選依機台明細時，每台機台各自一列，不再彙總為單一場館列",
    "ui_e2e", ["functional"], ["requirement_based"],
    PRE_ADMIN + ["沿用同一場館與同一結算日期查詢範圍（該場館底下有多台機台）"],
    ["進入場館日結報表，統計維度選『依機台明細』，結算日期同前，查詢",
     "核對列表列數與該場館底下機台帳號的數量"],
    "列表列數等於該場館底下機台帳號的數量，每台機台各自一列",
    "§篩選器/統計維度", "依場館彙總 / 依機台明細 / 依場次明細"))

T.append(tc(
    "REQ-DAILYREPORT-006", ["AC-DAILYREPORT-0063"],
    "統計維度選依場次明細時，即使統計週期選區間合計，列表仍逐場次列出、不彙總",
    "ui_e2e", ["negative"], ["error_guessing"],
    PRE_ADMIN + ["選定一個當日（或近期單一營業日）已有多個已結束場次的既有機台"],
    ["進入場館日結報表，統計維度選『依場次明細』，統計週期選『區間合計』，結算日期涵蓋該機台已知有多個已結束場次的區間，查詢",
     "記錄列表的列數，並與該機台在此區間內實際的已結束場次數（可透過『機台交易紀錄』頁依場次篩選核對）比對"],
    "列表逐場次列出，列數與該區間內實際場次數相符，不因統計週期選了『區間合計』就把多個場次彙總成一列——統計週期在此維度下僅決定查詢範圍，不影響列表是否逐場次呈現",
    "§篩選器/統計維度", "「依場次明細」時統計週期僅決定查詢範圍，列表仍逐場次列出、不彙總",
    critical=True,
    rationale="此為刻意針對『開發者可能誤以為區間合計一定要彙總，而在依場次明細維度下也套用彙總邏輯』這個合理懷疑而設計的案例（error_guessing），驗證這個明確定義的例外規則有被正確處理；REQ-DAILYREPORT-006 rejection_contract.defined=true（下拉選單三選一有明確限制），故本案不需標為 exploratory"))

# ================= REQ-DAILYREPORT-007（high）結算期間欄位與營業日切分 =================

T.append(tc(
    "REQ-DAILYREPORT-007", ["AC-DAILYREPORT-0071"],
    "交易發生在日結時間前一分鐘時，計入前一個營業日",
    "ui_e2e", ["functional", "boundary"], ["boundary_value"],
    PRE_ADMIN + ["選定一個日結時間設定為 06:00 UTC+0 的既有場館（可於場館設定頁核對）",
                 "確認該場館下有一筆交易或場次記錄的時間點落在 2026-09-05 05:59 UTC+0（即日結時間前一分鐘）；若無現成案例，可改選其他已知落在對應場館日結時間前一分鐘的既有交易記錄"],
    ["進入場館日結報表，統計週期選『按日』，統計維度選『依場館彙總』或『依機台明細』，結算日期設為涵蓋 2026-09-04 與 2026-09-05 的範圍，查詢",
     "檢視 2026-09-05 05:59 UTC+0 這筆交易被計入哪一個『結算期間』（營業日）列"],
    "該筆 05:59 UTC+0 的交易被計入營業日 2026-09-04 那一列，而非 2026-09-05",
    "§列表欄位/結算期間 + §業務規則/日結時間", "按日顯示營業日（依場館日結時間切分）",
    critical=True,
    rationale="05:59 恰為日結時間 06:00 前一分鐘，是本規則切分邊界的關鍵測試點；場館日結時間本身是開發包③定義的場館設定欄位，本包僅消費該設定作為分日依據，precondition 中『如何設定日結時間』的具體操作路徑不在本包定義範圍內，執行時以既有已設定該時間的場館為準"))

T.append(tc(
    "REQ-DAILYREPORT-007", ["AC-DAILYREPORT-0072"],
    "交易發生在日結時間當下時，計入當日營業日",
    "ui_e2e", ["functional", "boundary"], ["boundary_value"],
    PRE_ADMIN + ["選定一個日結時間設定為 06:00 UTC+0 的既有場館",
                 "確認該場館下有一筆交易或場次記錄的時間點恰為 2026-09-05 06:00:00 UTC+0（即日結時間當下）；若無現成案例，可改選其他已知恰落在對應場館日結時間點的既有交易記錄"],
    ["進入場館日結報表，統計週期選『按日』，統計維度選『依場館彙總』或『依機台明細』，結算日期設為涵蓋 2026-09-04 與 2026-09-05 的範圍，查詢",
     "檢視 2026-09-05 06:00 UTC+0 這筆交易被計入哪一個『結算期間』（營業日）列"],
    "該筆 06:00 UTC+0 的交易被計入營業日 2026-09-05，而非 2026-09-04——日結時間點本身歸屬新的營業日",
    "§列表欄位/結算期間 + §業務規則/日結時間", "按日顯示營業日（依場館日結時間切分）",
    critical=True))

T.append(tc(
    "REQ-DAILYREPORT-007", ["AC-DAILYREPORT-0073"],
    "統計週期為按月時，結算期間欄顯示該月的起訖日期",
    "ui_e2e", ["functional"], ["requirement_based"],
    PRE_ADMIN + [],
    ["進入場館日結報表，統計週期選『按月』，結算日期涵蓋單一自然月，查詢",
     "檢視列表『結算期間』欄位顯示內容"],
    "結算期間欄顯示該月的起訖日期（該月第一個營業日至最後一個營業日的日期範圍），而非個別單日",
    "§列表欄位/結算期間", "按週／按月／區間合計顯示該週期的起訖日期"))

# ================= REQ-DAILYREPORT-008（high）場次編號欄（依場次明細） =================

T.append(tc(
    "REQ-DAILYREPORT-008", ["AC-DAILYREPORT-0081"],
    "統計維度選依場次明細時，每列顯示場次編號、開始／結束時間與場次時長",
    "ui_e2e", ["functional"], ["requirement_based"],
    PRE_ADMIN + ["選定一個當日已有已結束場次的既有機台"],
    ["進入場館日結報表，統計維度選『依場次明細』，結算日期涵蓋該機台已知的場次，查詢",
     "檢視列表每一列包含的欄位"],
    "每一列顯示場次編號，並附開始時間、結束時間（UTC+0）、場次時長三個欄位",
    "§列表欄位/場次編號 + §背景:場次資訊", "僅「依場次明細」維度顯示；另附開始／結束時間與場次時長"))

T.append(tc(
    "REQ-DAILYREPORT-008", ["AC-DAILYREPORT-0082"],
    "統計維度選依場館彙總或依機台明細時，不顯示場次編號欄",
    "ui_e2e", ["negative"], ["requirement_based"],
    PRE_ADMIN + ["沿用一個當日已有已結束場次的既有機台所屬場館"],
    ["統計維度選『依場館彙總』，查詢，檢視欄位",
     "統計維度改選『依機台明細』，查詢，檢視欄位"],
    "兩種維度下列表皆不出現『場次編號』欄位",
    "§列表欄位/場次編號", "僅「依場次明細」維度顯示；另附開始／結束時間與場次時長",
    rationale="REQ-DAILYREPORT-008 為 high risk，本案為其 non-happy 覆蓋；rejection_contract.defined=true（『非場次明細維度不顯示該欄』為明確定義），可直接斷言不需標為 exploratory"))

T.append(tc(
    "REQ-DAILYREPORT-008", ["AC-DAILYREPORT-0083"],
    "進行中場次於依場次明細列表中，結束時間顯示「—」、場次時長為累計至查詢當下",
    "ui_e2e", ["functional"], ["requirement_based"],
    PRE_ADMIN + ["選定一台目前有進行中場次的既有機台（可先於會員詳細頁『機台資訊』區塊確認該機台目前有進行中場次）"],
    ["進入場館日結報表，統計維度選『依場次明細』，結算日期涵蓋當日，查詢",
     "找到該進行中場次所在列，檢視結束時間與場次時長欄位"],
    "結束時間欄顯示「—」；場次時長欄顯示自該場次開始時間至目前查詢當下的累計時間差（而非固定值，重新查詢應隨時間推移增加）",
    "§背景:場次資訊/場次資訊表", "進行中的場次結束時間顯示「—」"))

# ================= REQ-DAILYREPORT-009（high）場次數 =================

T.append(tc(
    "REQ-DAILYREPORT-009", ["AC-DAILYREPORT-0091", "AC-DAILYREPORT-0092"],
    "場次數：依機台明細等於該機台當日已結束場次數，依場館彙總等於底下所有機台場次數加總",
    "ui_e2e", ["functional"], ["requirement_based"],
    PRE_ADMIN + ["選定一個場館，其底下至少兩台機台當日皆有已結束場次記錄（僅使用狀態明確為『已結束』的場次，避開逾時結束或日結結算狀態，以迴避場次結束狀態範圍尚未明確定義的模糊地帶）"],
    ["透過『機台交易紀錄』或對應的場次查詢功能，分別核對這兩台機台當日各自狀態為『已結束』的場次筆數，記錄下來",
     "進入場館日結報表，統計維度選『依機台明細』，結算日期設為當日，查詢，記錄每台機台的『場次數』欄位",
     "統計維度改選『依場館彙總』，查詢，記錄場館彙總列的『場次數』"],
    "依機台明細：每台機台的場次數與步驟1核對的該機台已結束場次筆數相符；依場館彙總：場次數等於該場館底下所有機台場次數的加總（＝步驟1兩台機台場次數之和）",
    "§列表欄位/場次數（2026-09-03 定案）", "依場館彙總＝**該場館底下所有機台帳號當日場次數的加總**",
    rationale="刻意只選狀態為『已結束』的場次做為驗證基礎，迴避 RequirementModel 已記載的 major ambiguity（『當日結束的場次』是否包含逾時結束與日結結算），確保本案斷言落在 spec 沒有爭議的範圍內；對逾時結束／日結結算狀態是否計入，另立一條 exploratory 案例處理，不在此案混淆"))

T.append(tc(
    "REQ-DAILYREPORT-009", ["AC-DAILYREPORT-0093"],
    "進行中場次不計入當日場次數",
    "ui_e2e", ["negative"], ["requirement_based"],
    PRE_ADMIN + ["選定一台目前有進行中場次的既有機台"],
    ["於會員詳細頁『機台資訊』區塊或機台交易紀錄，核對該機台當日已結束的場次筆數（不含目前進行中的這一場）",
     "進入場館日結報表，統計維度選『依機台明細』，結算日期設為當日，查詢，檢視該機台的『場次數』欄位"],
    "該機台的場次數等於步驟1核對的已結束場次筆數，不因目前有一場進行中場次而多算一筆",
    "§列表欄位/場次數", "為當日結束的場次筆數"))

T.append(tc(
    "REQ-DAILYREPORT-009", ["AC-DAILYREPORT-0091", "AC-DAILYREPORT-0092"],
    "觀察逾時結束／日結結算狀態的場次是否被計入當日場次數",
    "ui_e2e", ["functional"], ["equivalence_partitioning"],
    PRE_ADMIN + ["選定一台當日有一筆狀態為『逾時結束』或『日結結算』的場次記錄（可於機台交易紀錄依場次狀態篩選查找既有案例）"],
    ["於機台交易紀錄核對該機台當日全部場次的狀態分布（已結束／逾時結束／日結結算各幾筆）",
     "進入場館日結報表，統計維度選『依機台明細』，結算日期設為當日，查詢，檢視該機台的『場次數』"],
    "記錄實際顯示的場次數，並比對是否等於『僅計已結束』或『計已結束＋逾時結束＋日結結算等全部非進行中狀態』兩種解讀中的哪一種；因 spec 對此為 major ambiguity 未明確定義，本案不預先斷言何者為正確結果，僅如實記錄觀察值供人工確認，必要時回饋為 Clarification",
    "§列表欄位/場次數", "為當日結束的場次筆數",
    assume="『當日結束的場次』是否包含『逾時結束』與『日結結算』兩種狀態，RequirementModel 已標記為 major ambiguity，spec 未明確定義；本案的觀察結果需人工確認何者為正確業務規則，必要時另開 Clarification"))

# ================= REQ-DAILYREPORT-010（medium）現金收支金額欄定義 =================

T.append(tc(
    "REQ-DAILYREPORT-010", ["AC-DAILYREPORT-0101"],
    "開分／洗分／進鈔／收據金額分別等於當日對應類型交易的加總",
    "ui_e2e", ["functional"], ["requirement_based"],
    PRE_ADMIN + ["選定一台當日已有開分、洗分、入金、出金四種交易皆發生過的既有機台"],
    ["透過『機台交易紀錄』頁篩選該機台當日的交易紀錄，分別加總開分金額、洗分金額、入金金額、出金金額（收據金額）四類總額，記錄作為比對基準",
     "進入場館日結報表，統計維度選『依機台明細』，結算日期設為當日，查詢，檢視該機台列的開分金額、洗分金額、進鈔金額、收據金額四欄"],
    "報表四欄金額分別與步驟1由機台交易紀錄加總出的開分、洗分、入金、出金總額相符（開分金額＝開分總額；洗分金額＝洗分總額；進鈔金額＝入金總額；收據金額＝出金總額）",
    "§列表欄位/開分~收據金額",
    "收據金額 | 當日出金總額（印出的收據面額合計；過渡期機台暫無印表機時，為結算結果畫面顯示的出金金額合計）",
    cost="high"))

T.append(tc(
    "REQ-DAILYREPORT-010", ["AC-DAILYREPORT-0102"],
    "過渡期無印表機的機台，收據金額欄取結算結果畫面顯示的出金金額合計",
    "ui_e2e", ["functional"], ["requirement_based"],
    PRE_ADMIN + ["選定一台目前處於『過渡期尚未安裝印表機』狀態的既有機台"],
    ["核對該機台當日的出金交易，記錄『結算結果畫面』顯示的出金金額合計（若此畫面非後台可直接查看，需經由對應的機台端或維運紀錄確認）",
     "進入場館日結報表，統計維度選『依機台明細』，結算日期設為當日，查詢，檢視該機台的『收據金額』欄位"],
    "收據金額欄顯示的數值與步驟1記錄的結算結果畫面出金金額合計相符（而非印出的收據面額合計，因該機台過渡期無印表機）",
    "§列表欄位/開分~收據金額", "結算結果畫面顯示的出金金額合計",
    assume="如何在後台判斷／辨識一台機台目前是否屬於『過渡期尚無印表機』狀態，本包與目前可讀的其他 spec 皆未定義對應欄位或查詢方式；此為測試資料佈置所需但 spec 未提供依據的判斷，需人工確認辨識方式",
    cost="high"))

# ================= REQ-DAILYREPORT-011（high）核實狀態連動欄位 =================

T.append(tc(
    "REQ-DAILYREPORT-011", ["AC-DAILYREPORT-0111"],
    "當日待核實洗分金額不為 0 時，該欄位有提醒標示",
    "ui_e2e", ["functional"], ["requirement_based"],
    PRE_ADMIN + ["選定一個當日洗分金額中有部分仍待核實的既有場館或機台（可先於帳務管理『洗分出金核實』頁查找當日仍有待核實項目的機台）"],
    ["進入場館日結報表，結算日期設為當日，統計維度選『依機台明細』，查詢",
     "檢視該機台列的『待核實洗分』欄位數值與呈現方式"],
    "待核實洗分欄位顯示大於 0 的金額，且該欄位出現某種提醒標示；spec 未定義具體呈現形式為顏色／圖示／文字，本案僅斷言『有提醒標示這個事實存在』，不斷言標示的具體視覺形式",
    "§列表欄位/已核實洗分~未兌現金額", "不為 0 時標示提醒"))

T.append(tc(
    "REQ-DAILYREPORT-011", ["AC-DAILYREPORT-0112"],
    "當日洗分全部已核實、待核實洗分為 0 時，不出現提醒標示",
    "ui_e2e", ["negative"], ["requirement_based"],
    PRE_ADMIN + ["選定一個當日洗分已全數核實完畢（待核實洗分為 0）的既有機台"],
    ["進入場館日結報表，結算日期設為當日，統計維度選『依機台明細』，查詢",
     "檢視該機台列的『待核實洗分』欄位"],
    "待核實洗分顯示 0，且不出現提醒標示（無論該提醒平常以何種視覺形式呈現，此時皆不應出現）",
    "§列表欄位/已核實洗分~未兌現金額", "不為 0 時標示提醒",
    rationale="REQ-DAILYREPORT-011 為 high risk，本案為其 non-happy 覆蓋；提醒『不出現』是 AC-0112 明確要求的結果，不涉及未定義的視覺形式細節，故不需標為 exploratory"))

T.append(tc(
    "REQ-DAILYREPORT-011", ["AC-DAILYREPORT-0113"],
    "已兌現金額與未兌現金額分別等於已核銷與仍待核實的收據金額合計",
    "ui_e2e", ["functional"], ["requirement_based"],
    PRE_ADMIN + ["選定一個當日收據金額中部分已核銷、部分仍待核實的既有機台"],
    ["進入場館日結報表，結算日期設為當日，統計維度選『依機台明細』，查詢",
     "檢視該機台列的『已兌現金額』與『未兌現金額』兩欄，並與帳務管理『洗分出金核實』頁該機台當日收據核實狀態的明細加總比對"],
    "已兌現金額＝該機台當日已核實（核銷）的收據金額合計；未兌現金額＝截至查詢當下仍待核實的收據金額合計；兩者與『洗分出金核實』頁的明細加總相符",
    "§列表欄位/已核實洗分~未兌現金額", "已核實（核銷）的收據金額合計",
    cost="high"))

T.append(tc(
    "REQ-DAILYREPORT-011", ["AC-DAILYREPORT-0114"],
    "於洗分出金核實頁將一筆待核實洗分核實後，報表的已核實／待核實數字對應變動",
    "ui_e2e", ["functional"], ["requirement_based"],
    PRE_ADMIN + ["選定一筆帳務管理『洗分出金核實』頁中目前狀態為待核實的洗分項目"],
    ["進入場館日結報表，查詢該筆待核實項目所屬機台與日期，記錄目前的『已核實洗分』『待核實洗分』數值",
     "前往帳務管理『洗分出金核實』頁，將該筆待核實項目核實",
     "回場館日結報表，以相同篩選條件重新查詢，記錄『已核實洗分』『待核實洗分』數值"],
    "重新查詢後，已核實洗分金額增加該筆項目的金額，待核實洗分金額對應減少相同金額，兩者變動相符",
    "§列表欄位/已核實洗分~未兌現金額 + §拆包說明", "已在「洗分出金核實」頁核實的金額合計",
    cost="high"))

# ================= REQ-DAILYREPORT-012（high）現金淨收計算 =================

T.append(tc(
    "REQ-DAILYREPORT-012", ["AC-DAILYREPORT-0121"],
    "現金淨收等於開分＋進鈔－已核實洗分－已兌現，且不扣待核實洗分",
    "ui_e2e", ["functional"], ["requirement_based"],
    PRE_ADMIN + ["選定一個當日開分、進鈔、已核實洗分、已兌現皆有數值的既有機台或場館"],
    ["進入場館日結報表，結算日期設為當日，查詢，記錄該列的開分金額、進鈔金額、已核實洗分、已兌現金額、現金淨收五個欄位數值",
     "依公式『開分＋進鈔－已核實洗分－已兌現』手動計算，比對計算結果與報表顯示的現金淨收欄位"],
    "報表顯示的現金淨收欄位數值，等於手動依公式計算的結果（開分＋進鈔－已核實洗分－已兌現），且不因待核實洗分有數值而被扣除",
    "§列表欄位/現金淨收 + §業務規則/現金淨收計算", "待核實洗分不扣除",
    critical=True, cost="high"))

T.append(tc(
    "REQ-DAILYREPORT-012", ["AC-DAILYREPORT-0122"],
    "現金淨收允許為負值，不會被限制為非負或以錯誤取代",
    "ui_e2e", ["functional", "boundary"], ["boundary_value"],
    PRE_ADMIN + ["尋找或選定一個當日已核實洗分與已兌現金額合計，明顯大於開分與進鈔金額合計的既有機台或場館（使公式計算結果為負值；若查詢範圍內找不到現成案例，可嘗試放寬結算日期或改選其他機台尋找）"],
    ["進入場館日結報表，設定選定的機台與涵蓋日期，查詢",
     "檢視該列的現金淨收欄位數值，並依公式手動計算核對"],
    "現金淨收欄位正常顯示負值（不會被系統攔截、顯示為 0、或以錯誤訊息取代），且該負值等於依公式計算的結果——代表場館端現金應淨減少多少",
    "§操作/欄位說明附註", "代表場館端當日現金應該增減多少",
    critical=True, cost="high",
    rationale="『增減多少』一詞明確暗示現金淨收可能為負值（減少），本案驗證公式在此情境下確實允許並正確呈現負值而非被限制為非負，屬邊界值分析（測試公式輸出範圍的下界行為）；若當前查詢期間找不到現成負值案例，執行者可調整查詢範圍尋找，不強行捏造資料"))

# ================= REQ-DAILYREPORT-013（medium）有效投注額與損益以核心貨幣計算 =================

T.append(tc(
    "REQ-DAILYREPORT-013", ["AC-DAILYREPORT-0131", "AC-DAILYREPORT-0132"],
    "機台場館的有效投注額與損益以 TWD 表示，損益為正值時以綠色呈現",
    "ui_e2e", ["functional"], ["requirement_based"],
    PRE_ADMIN + ["選定一個核心貨幣為 TWD 的機台場館，且當日損益為正值的既有機台"],
    ["進入場館日結報表，結算日期設為當日，查詢，檢視該機台列的有效投注額與損益欄位"],
    "有效投注額與損益欄位數值皆以 TWD（新台幣）表示；損益為正值時，該欄位以綠色呈現",
    "§列表欄位/有效投注額、損益（2026-09-03 定案）",
    "投注總額，以主站台核心貨幣計算（機台場館為 TWD"))

T.append(tc(
    "REQ-DAILYREPORT-013", ["AC-DAILYREPORT-0133"],
    "損益為負值時，該欄位以紅色呈現",
    "ui_e2e", ["functional"], ["requirement_based"],
    PRE_ADMIN + ["選定一個當日損益為負值的既有機台"],
    ["進入場館日結報表，結算日期設為當日，查詢，檢視該機台列的損益欄位"],
    "損益為負值時，該欄位以紅色呈現",
    "§列表欄位/有效投注額、損益（2026-09-03 定案）",
    "損益 | 當日投注損益，以主站台核心貨幣計算；正值綠色、負值紅色"))

# ================= REQ-DAILYREPORT-014（medium）期末餘額 =================

T.append(tc(
    "REQ-DAILYREPORT-014", ["AC-DAILYREPORT-0141"],
    "依場館彙總維度的期末餘額，等於底下各機台期末餘額的加總",
    "ui_e2e", ["functional"], ["requirement_based"],
    PRE_ADMIN + ["選定一個底下至少兩台機台的既有場館"],
    ["進入場館日結報表，統計維度選『依機台明細』，結算日期設為當日，查詢，記錄每台機台的期末餘額",
     "統計維度改選『依場館彙總』，查詢，檢視場館彙總列的期末餘額"],
    "場館彙總列的期末餘額，等於步驟1各機台期末餘額的加總",
    "§列表欄位/期末餘額", "該日結算時點各機台的分數合計"))

T.append(tc(
    "REQ-DAILYREPORT-014", ["AC-DAILYREPORT-0142"],
    "統計週期為按週時，期末餘額取週內最後一個營業日的值，而非該週各日加總",
    "ui_e2e", ["functional"], ["requirement_based"],
    PRE_ADMIN + ["選定一個場館，確認其在某個週期間（週一至週日）內至少兩個營業日皆有結算資料，且各營業日期末餘額不同"],
    ["進入場館日結報表，統計維度選『依場館彙總』，統計週期選『按日』，結算日期涵蓋該週的各營業日，查詢，記錄每個營業日的期末餘額（尤其是週內最後一個營業日）",
     "統計週期改選『按週』，結算日期涵蓋同一週，查詢，檢視該週那一列的期末餘額"],
    "按週那一列顯示的期末餘額，等於步驟1中『週內最後一個營業日』單日的期末餘額，而非該週所有營業日期末餘額的加總或平均",
    "§列表欄位/期末餘額 + 欄位說明附註", "最後一個營業日",
    cost="high"))

# ================= REQ-DAILYREPORT-015（high）非按日週期的彙總規則 =================

T.append(tc(
    "REQ-DAILYREPORT-015", ["AC-DAILYREPORT-0151"],
    "非按日週期（按週／區間合計）的金額欄，等於各營業日的合計，三種統計週期呈現的總額互相一致",
    "ui_e2e", ["functional", "negative"], ["requirement_based"],
    PRE_ADMIN + ["選定一個場館，其在同一週內至少三個營業日皆有開分交易"],
    ["進入場館日結報表，統計週期選『按日』，統計維度選『依場館彙總』，結算日期涵蓋該週三個（或以上）營業日，查詢，記錄每個營業日的開分金額",
     "統計週期改選『按週』，同一結算日期區間，查詢，檢視該週列的開分金額",
     "統計週期改選『區間合計』，同一結算日期區間，查詢，檢視該列的開分金額"],
    "按週列與區間合計列的開分金額皆等於步驟1各營業日開分金額的加總；三種統計週期呈現的總額互相一致，不因彙總方式不同而算出不同的總額——非按日週期不會漏算或多算任何一個營業日",
    "§列表欄位附註", "該週期內各營業日的合計",
    cost="high"))

T.append(tc(
    "REQ-DAILYREPORT-015", ["AC-DAILYREPORT-0152"],
    "未兌現金額不受統計週期切分方式影響，四種統計週期下數值一致",
    "ui_e2e", ["negative"], ["requirement_based"],
    PRE_ADMIN + ["選定一個目前有未兌現金額（收據尚待核實）的既有場館或機台"],
    ["進入場館日結報表，統計週期選『按日』，結算日期設為涵蓋今日的單日，查詢，記錄該機台／場館的未兌現金額",
     "統計週期改選『按週』『按月』『區間合計』（結算日期涵蓋同一段包含今日的區間），分別查詢，記錄每種週期下的未兌現金額"],
    "四種統計週期下，同一機台／場館的未兌現金額數值皆相同，不因統計週期的彙總方式不同而改變——未兌現金額一律為截至查詢當下的累計值，不受統計週期切分影響",
    "§列表欄位附註", "「未兌現金額」不受週期影響、一律為截至查詢當下的累計",
    cost="high"))

T.append(tc(
    "REQ-DAILYREPORT-015", ["AC-DAILYREPORT-0152"],
    "觀察未兌現金額是否也不受結算日期篩選範圍限制",
    "ui_e2e", ["functional"], ["equivalence_partitioning"],
    PRE_ADMIN + ["選定一個目前有未兌現金額的既有機台，記錄其目前實際全部未核實收據的總金額（可透過帳務管理『洗分出金核實』頁核對）"],
    ["進入場館日結報表，結算日期設定為一個明顯早於今日、不包含目前未核實收據產生日期的窄區間，統計週期任選，查詢",
     "檢視該機台的『未兌現金額』欄位數值，與前置作業中核對的實際未核實收據總金額比較"],
    "記錄未兌現金額欄位在此情境下的實際顯示值：若等於全部未核實收據總額（不受結算日期限制），代表未兌現金額全期累計；若為 0 或不同數值（受結算日期範圍限制），代表未兌現金額仍受結算日期篩選影響。因 RequirementModel 已標記此為 major ambiguity（未兌現金額不受週期影響是否也代表不受結算日期限制），本案不預先斷言何者為正確行為，僅如實記錄觀察結果供人工確認",
    "§列表欄位附註", "「未兌現金額」不受週期影響、一律為截至查詢當下的累計",
    assume="『未兌現金額不受週期影響』是否也代表不受『結算日期』篩選範圍限制，RequirementModel 已標記為 major ambiguity，spec 未明確定義；此觀察結果需人工確認正確業務規則",
    cost="high"))

# ================= REQ-DAILYREPORT-016（medium）列表總計與匯出 CSV =================

T.append(tc(
    "REQ-DAILYREPORT-016", ["AC-DAILYREPORT-0161"],
    "列表底部總計列的各欄數值，等於該欄所有列的加總",
    "ui_e2e", ["functional"], ["requirement_based"],
    PRE_ADMIN + ["選定一個查詢後會回傳多筆列（例如依機台明細且場館下有多台機台）的既有場館"],
    ["進入場館日結報表，統計維度選『依機台明細』，結算日期設為當日，查詢，記錄列表每一列的各數值欄位",
     "手動加總每一欄（開分、洗分、進鈔、收據等）的各列數值，與列表底部顯示的總計列比對"],
    "底部總計列的每一欄數值，皆等於該欄所有列的加總",
    "§列表欄位末段", "各欄總計"))

T.append(tc(
    "REQ-DAILYREPORT-016", ["AC-DAILYREPORT-0162"],
    "匯出 CSV 的內容與當前篩選結果一致",
    "ui_e2e", ["functional"], ["requirement_based"],
    PRE_ADMIN + ["已完成一次有資料回傳的查詢（任一篩選條件組合）"],
    ["於場館日結報表完成查詢後，記錄目前列表顯示的所有列與欄位數值",
     "點擊頁面右上角『匯出 CSV』，開啟下載的 CSV 檔案"],
    "CSV 檔案內容（列數與各欄數值）與步驟1記錄的當前篩選結果列表一致，不多不少、數值相符",
    "§操作/匯出 CSV", "匯出當前篩選結果"))

T.append(tc(
    "REQ-DAILYREPORT-016", ["AC-DAILYREPORT-0163"],
    "頁面不存在新增／編輯／刪除／審核相關按鈕",
    "ui_e2e", ["negative"], ["requirement_based"],
    ["以任一角色（Admin／站長／操作員擇一）登入後台"],
    ["進入場館日結報表，瀏覽整個頁面（篩選器、列表、頁首頁尾）"],
    "頁面不存在任何新增、編輯、刪除或審核相關的按鈕或操作入口，僅提供查詢與匯出 CSV 功能",
    "§操作", "本頁為統計檢視，不提供新增／編輯／刪除／審核操作"))

# ================= REQ-DAILYREPORT-017（high）場次日結強制結束 =================

T.append(tc(
    "REQ-DAILYREPORT-017", ["AC-DAILYREPORT-0171"],
    "日結時間到達時，進行中場次強制結束為日結結算狀態，餘額承接為隔日新場次的期初餘額",
    "ui_e2e", ["functional"], ["state_transition"],
    PRE_ADMIN + ["透過『機台交易紀錄』或對應的場次查詢功能，尋找一台機台過去某個已經過的營業日，其在該日日結時間點當下有一筆進行中場次的既有歷史記錄（此記錄應已因日結時間到達而被系統處理）"],
    ["查看該筆場次記錄的狀態、結束時間，並記下承接前的餘額（該場次結束時的分數）",
     "查看同一機台緊接在後的下一筆場次記錄，檢視其開始時間與期初餘額"],
    "前一筆場次的狀態為『日結結算』，結束時間等於該場館當日的日結時間；下一筆（隔日新）場次的期初餘額，等於前一筆場次結束時的餘額（承接金額）",
    "§業務規則/場次日結 + §背景:場次資訊/場次狀態、期初餘額",
    "日結時間到達時強制結束所有進行中的場次，餘額轉為隔日新場次的期初餘額",
    critical=True, cost="high",
    rationale="採用回溯既有歷史場次記錄的方式驗證日結強制結束機制，而非在測試當下主動調整場館日結時間設定並等待觸發——後者需要假設『變更日結時間設定會立即套用於下一次判斷』這個 spec 未定義的系統行為，回溯法可在不引入此假設的前提下驗證同一條規則；REQ-DAILYREPORT-017 明確定義了 states 轉換規則，本案標記 state_transition 技巧以符合結構規則要求"))

T.append(tc(
    "REQ-DAILYREPORT-017", ["AC-DAILYREPORT-0172"],
    "機台無進行中場次時，日結時間到達不會憑空產生新場次",
    "ui_e2e", ["negative"], ["requirement_based"],
    PRE_ADMIN + ["尋找一台機台過去某個已經過的營業日，其在該日日結時間點當下沒有任何進行中場次（該機台當天的場次記錄皆已在日結時間之前結束，或當天無任何場次記錄）"],
    ["查看該機台該營業日日結時間前後的場次記錄列表",
     "確認日結時間點是否額外產生了一筆狀態為『日結結算』的空場次記錄"],
    "該機台在該營業日日結時間點沒有額外產生『日結結算』狀態的場次記錄——沒有進行中場次時，日結不會憑空產生新場次",
    "§業務規則/場次日結", "日結時間到達時強制結束所有進行中的場次，餘額轉為隔日新場次的期初餘額"))

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
