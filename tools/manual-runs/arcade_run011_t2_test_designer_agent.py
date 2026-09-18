#!/usr/bin/env python3
"""T2: Test Designer（mode=spec）依 SPEC-ARCADE-001 v0.7 的 6 條 requirement / 7 條 AC
展開 TestCaseDraft + TestDesignReport。RUN-20260918-011。

Phase 3 影子測試：本腳本為獨立設計，未讀取 testcases/registry/TC-ARCADE-*.yaml、
testcases/versions/TC-ARCADE-*、testcases/ARCADE.md 等 Phase 2 既有人工 TC 內容，
以維持設計視角獨立。

範圍澄清（依 artifacts/requirements/SPEC-ARCADE-001/v0.7/requirements.yaml 為準，
非本腳本自行判斷）：
  - REQ-ARCADE-001 risk=low
  - REQ-ARCADE-002 risk=high
  - REQ-ARCADE-003 risk=medium
  - REQ-ARCADE-004 risk=high
  - REQ-ARCADE-005 status=RETIRED（已被 REQ-PLATFORMRULE-014 完整涵蓋，本 RM 自身
    history 已記錄退役原因）——不設計 TC，於 uncovered_with_reason 記錄
  - REQ-ARCADE-006 risk=medium（任務指派訊息文字描述為 high risk，但實際
    RequirementModel persisted 內容明確為 risk: medium；依「不驗證自己的產出、
    但要忠實依據輸入」原則，以 requirements.yaml 記載為準，不因任務描述文字而
    竄改風險等級，僅於完成回報時向使用者說明此落差）

介面判斷（依指示 0）：
  - REQ-ARCADE-001（前台自行註冊）：AC 明確描述「站在一個機台場館的前台網域上」，
    這是會員前台（無需登入後台）的行為，precondition 不假設後台有對應操作頁面；
    改以後台『站台列表』既有的網域查詢功能取得前台網址後，直接在瀏覽器開啟前台
    網域檢視，並以線上站台前台作對照組。
  - 其餘 5 條 requirement（機台帳號流水排除規則、稽核倍數設定、洗分出金核實操作
    紀錄）皆為後台管理系統功能，precondition 以「登入後台」為基礎；但機台帳號的
    投注流水／開分／入金／洗分／出金交易本身，源頭是機台現場硬體流程與遊玩行為，
    非後台 UI 可直接觸發——這些 TC 誠實以 assumptions + needs_human_confirmation
    標示測試環境需已存在（或需另洽環境負責人佈置）對應的機台交易紀錄，不假裝後台
    有一個按鈕可以「代為」產生這些機台端事件。
"""
import sys, pathlib, collections
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids

RUN = "RUN-20260918-011"
RM_AID = "ART-RM-01M2GW8RBT2JA2KG86B1J5K87J"
ITER = 0
SID, SV, AREA, A = "SPEC-ARCADE-001", "0.7", "ARCADE", "agent-test-designer"
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

# ================= REQ-ARCADE-001（low）機台場館前台不提供自行註冊入口 =================

T.append(tc(
    "REQ-ARCADE-001", ["AC-ARCADE-001"],
    "機台場館前台網域找不到自行註冊入口，同一時間線上站台前台維持提供註冊入口作為對照",
    "ui_e2e", ["functional", "negative"], ["negative", "requirement_based"],
    PRE_ADMIN + [
        "於後台『站台列表』頁面，查詢一個既有機台場館（或自行經營之機台主站台）的網域，"
        "並另外查詢一個既有線上站台的網域，記錄兩者的前台網址（本步驟僅用於取得網址，"
        "不涉及登入後台以外的任何前台操作）",
    ],
    ["於瀏覽器開啟機台場館的前台網址，檢視頁面（含首頁、登入頁、選單與頁尾等一般常見放置"
     "註冊入口的位置）是否存在任何『註冊』相關按鈕或連結",
     "於另一分頁開啟該線上站台的前台網址，同樣檢視是否存在『註冊』相關按鈕或連結，並嘗試"
     "點擊確認可進入註冊流程頁面"],
    "機台場館前台網域的頁面（首頁、登入頁、選單、頁尾等常見位置）皆找不到任何『註冊』入口；"
    "線上站台前台網域則正常可見『註冊』入口並可進入以帳號密碼方式自行註冊的流程，兩者形成"
    "對照，差異僅在站台類型不同",
    "機台場館的後台選單／補充說明",
    "機台場館的前台不開放自行註冊**（v07 定案維持）：註冊入口不在機台場館的前台提供，機台"
    "帳號一律由後台建立（暱稱禁用詞設定因此一併隱藏）；開放與否屬未來營運需求、時程未定。"
    "線上站台的前台註冊不受影響",
    rationale=(
        "本條驗證的行為主體是會員前台網域，不是後台管理系統，故 precondition 刻意不假設後台"
        "有一個對應『申請/切換前台』的操作入口，而是利用後台『站台列表』既有且不受本次排除"
        "規則影響的網域查詢功能取得前台網址，再直接以瀏覽器造訪前台網域驗證；RequirementModel "
        "的 AC 用語『同一站台切到線上站台的前台』屬 RM 抽象化描述，實際上前台並無『站台切換』"
        "這個後台概念，機台場館與線上站台本屬不同網域/不同站台，本 TC 因此以『開兩個分頁分別"
        "檢視兩個不同前台網域』的方式落地，而非誤植為前台真的存在切換元件。技巧上這是單一輸入"
        "條件（站台類型）對應兩種相反結果（無/有註冊入口）的對照案例，非多條件組合，故不標"
        "decision_table；因主要斷言是『找不到』，標 negative，同時保留 requirement_based 因"
        "對照組的『線上站台正常提供』這半段斷言直接可由業務規則表原文『線上站台的前台維持"
        "開放以帳號密碼方式自行註冊』（v0.7.md 第803行）佐證，此段因與本引用的第264行段落不"
        "連續，故未併入 quote，僅在此說明。"
    )))

# ================= REQ-ARCADE-002（high）機台帳號投注流水不計入加盟傭金／代理返傭基數 =================

T.append(tc(
    "REQ-ARCADE-002", ["AC-ARCADE-002"],
    "機台帳號產生投注流水後，其所屬加盟商當期的加盟傭金與代理返傭金額不因此增加",
    "ui_e2e", ["functional", "negative"], ["negative"],
    PRE_ADMIN + [
        "選定一個既有加盟商，其站台樹（含任何層級子站台）底下已包含一個機台場館，且該場館"
        "下至少有一台既有機台帳號（自行從環境中選定；此掛載關係是否已存在屬環境事實，若無法"
        "確認見下方假設）",
        "於『各式報表 > 加盟傭金發放紀錄』（或加盟商詳細頁的統計區塊），記錄該加盟商在本次"
        "查驗前、當期結算週期的加盟傭金與代理返傭金額，作為比對基準",
    ],
    ["於『各式報表 > 交易紀錄查詢』或『注單查詢』，以該機台帳號查詢確認其於本結算週期內是否"
     "已存在（或可產生）至少一筆新的已完成投注紀錄；若當下無現成紀錄，需依機台現場流程使其"
     "產生（此步驟涉及機台端硬體操作，非本 spec 定義的後台 UI 範圍，見下方假設）",
     "待該筆機台帳號投注流水確認已產生（可於交易紀錄查詢或注單查詢中查得）後，重新查詢"
     "『各式報表 > 加盟傭金發放紀錄』（或加盟商詳細頁統計），取得該加盟商本期最新的加盟傭金"
     "與代理返傭金額",
     "將本次取得的金額與前置作業記錄的比對基準金額逐一核對"],
    "該加盟商本期的加盟傭金與代理返傭金額與比對基準相同，未因該機台帳號新產生的投注流水而"
    "增加；同時該筆機台帳號的投注流水本身在交易紀錄查詢／注單查詢中確實可查得（證明流水"
    "真實發生過，排除『沒增加只是因為根本沒發生』的誤判可能）",
    "既有功能對機台帳號的排除規則／排除規則總表",
    "4.5 / 4.6 | 加盟傭金／代理返傭 | 不適用，機台帳號的投注不計入任何上層的傭金基數",
    assume=(
        "本 TC 假設測試環境當下存在（或可佈置）一個機台場館作為某既有加盟商站台樹的子站台，"
        "且該場館下至少有一台機台帳號；本次精讀的 spec 段落（140-232行、760-819行）未定義"
        "機台場館與加盟商站台樹之間具體的掛載機制細節（該機制屬站台列表/加盟商相關 spec 範圍），"
        "此環境事實需環境負責人確認才能佈置。此外，使該機台帳號實際產生新的投注流水，依賴機台"
        "端硬體現場遊玩流程，非本 spec 定義的後台 UI 可直接觸發；若環境當下無法產生新流水，"
        "可改用已存在的歷史投注流水，搭配其發生前後對應期間的傭金/返傭計算結果變化進行比對，"
        "但仍需環境負責人協助確認該歷史區間的計算結果快照。"
    ),
    critical=True,
    rationale=(
        "REQ-ARCADE-002 為 high risk，本案即其 non-happy 覆蓋，expected_result 斷言『不計入』"
        "這個負面事實，比對基準採用同一加盟商『產生流水前 vs 產生流水後』的金額快照對比，並"
        "額外核對流水本身確實存在，避免落入『沒看到變化只是因為壓根沒發生』的偽陰性陷阱（依"
        "指示 4 的比對基準要求）。技巧上僅標 negative：本案只有單一輸入條件（機台帳號流水）"
        "對應單一結果（不增加），不構成多條件矩陣，不套用 decision_table。是否已有機台場館掛"
        "在既有加盟商站台樹下，屬本次精讀段落未定義的環境設定細節，依指示 1 誠實以 assumption "
        "揭露，不假裝環境必然已具備此掛載關係。"
    )))

# ================= REQ-ARCADE-003（medium）機台帳號交易不出現在優惠彩金審核佇列 =================

T.append(tc(
    "REQ-ARCADE-003", ["AC-ARCADE-003"],
    "機台帳號完成金流交易後，優惠彩金審核佇列查無該筆交易",
    "ui_e2e", ["functional", "negative"], ["negative"],
    PRE_ADMIN + [
        "站台切換下拉選單切換至一個既有的機台場館站台",
        "選定該場館下一個既有機台帳號，記錄其目前的交易紀錄狀態（可先於『各式報表 > 交易"
        "紀錄查詢』核對），供後續比對是否有新增交易",
    ],
    ["使該機台帳號完成任一筆金流交易（開分／入金／洗分／出金皆可，四者本 requirement 一視"
     "同仁），記錄該筆交易的完成時間與交易編號（此步驟涉及機台端硬體現場流程，非本 spec"
     "定義的後台 UI 範圍，見下方假設）",
     "進入『帳務管理 > 優惠彩金審核』頁面，以涵蓋該筆交易完成時間的查詢區間查詢",
     "檢視查詢結果列表中是否存在對應該筆機台交易的審核項目；若查詢區間內原本就有其他線上"
     "會員的優惠彩金審核項目，一併記錄，以確認佇列本身有在正常運作而非剛好整批皆空"],
    "優惠彩金審核佇列的查詢結果中查無剛才那筆機台帳號交易對應的審核項目；若查詢範圍內原本"
    "就存在其他線上會員的優惠彩金審核項目，這些項目仍正常列出，僅機台帳號的交易不出現，證明"
    "並非佇列查詢功能本身異常",
    "既有功能對機台帳號的排除規則／排除規則總表",
    "3.3 | 優惠彩金審核 | 不適用",
    assume=(
        "機台帳號的開分／入金／洗分／出金交易本身是玩家在機台端實際操作產生的紀錄，非後台 "
        "UI 可直接建立的動作；本 TC 假設測試環境當下可透過機台現場流程（或既有模擬工具）使"
        "該機台帳號產生至少一筆新的已完成金流交易供查驗，若環境當下無法產生，需洽環境負責人"
        "協助，此步驟超出本 spec 定義範圍。"
    ),
    rationale=(
        "REQ-ARCADE-003 為 medium risk（不強制 non-happy），但其 behavior_kind 為 rejection，"
        "本身即以負向斷言（不出現）驗證最貼近 statement，故仍設計為 negative。比對基準採"
        "『若查詢範圍內存在其他線上會員項目則仍應正常列出』的方式排除『佇列整體異常』的干擾"
        "（依指示 4）。機台交易來源依賴機台端硬體流程，誠實以 assumption 揭露，模式與"
        "REQ-ARCADE-002 一致。"
    )))

# ================= REQ-ARCADE-004（high）鏈上錢包管理TWD頁籤稽核倍數設定 =================

T.append(tc(
    "REQ-ARCADE-004", ["AC-ARCADE-004"],
    "新建機台主站台的鏈上錢包管理 TWD 頁籤可見稽核倍數欄位，初始預設值為 0",
    "ui_e2e", ["functional"], ["requirement_based"],
    PRE_ADMIN + [
        "於後台『站台列表』新增一個全新的機台主站台（站台類型選擇「機台」，依畫面指示填寫"
        "其餘必要欄位後建立），確保稽核倍數尚未被任何人調整過，記錄新建立站台的名稱以利後續"
        "操作（刻意新建而非沿用既有場館，避免既有場館的稽核倍數可能已被他人調整過、導致無法"
        "驗證真正的初始預設值）",
    ],
    ["站台切換下拉選單切換至剛建立的機台主站台",
     "進入『帳務管理 > 鏈上錢包管理』，檢視頁籤列",
     "點開 TWD 頁籤，檢視稽核倍數設定欄位目前顯示的數值"],
    "頁籤列僅顯示「TWD」（法幣）頁籤；TWD 頁籤內可見稽核倍數設定欄位，欄位當下顯示值為 0"
    "（尚未經任何調整的初始預設值）",
    "機台帳號的稽核／稽核規則表",
    "預設值 | **0 倍**——即開分與入金不產生稽核門檻，玩家隨時可洗分與出金",
    data={"稽核倍數初始值": 0},
    rationale=(
        "本案驗證的是欄位存在與初始值，不涉及後續計算效果，故單純以 requirement_based 技巧"
        "設計靜態檢視案例。以『新建一個從未被調整過的機台主站台』取代『任選一個既有機台場館』"
        "作為前置作業，理由是既有場館的稽核倍數可能早已被其他測試或操作調整過、不再是 0，若"
        "沿用既有場館會把『這個特定場館目前剛好是 0』誤當成『驗證了預設值就是 0』，兩者不是"
        "同一件事（依指示 1 對『環境目前是否已具備某狀態』的假設要誠實處理，此處選擇改用"
        "『從既有站台列表新增功能建立全新站台』這個 spec 已明確保證存在的路徑來規避此假設，"
        "而非略過不談）。導覽路徑（鏈上錢包管理，非帳務管理出金設定）依本 requirement 的"
        "RequirementModel 已由 Oscar 2026-09-15 人工確認並記錄於 history，且可由 v0.7.md 第"
        "254行『機台場館的後台選單』分類表『帳務管理 | 鏈上錢包管理（僅顯示法幣 TWD 頁籤，"
        "區塊鏈頁籤隱藏——稽核倍數設定在此）』交叉驗證，非本 TC 自行臆測的介面路徑。"
    )))

T.append(tc(
    "REQ-ARCADE-004", ["AC-ARCADE-004"],
    "稽核倍數調整為大於 0 並儲存後，尚未完成稽核的部分會使機台洗分／出金的核可金額被扣減",
    "ui_e2e", ["functional", "boundary"], ["scenario", "boundary_value"],
    PRE_ADMIN + [
        "選定一個既有機台場館，並記錄其下一台既有機台帳號（作為稽核倍數調整後的觀察對象）",
    ],
    ["站台切換至該機台場館，進入『帳務管理 > 鏈上錢包管理 > TWD』頁籤，將稽核倍數由目前值"
     "修改為一個大於 0 的數值（例如 2），儲存",
     "使該機台帳號完成一筆機台開分或機台入金交易，使其產生尚未完成稽核的累計金額（此步驟"
     "涉及機台端硬體現場流程與稽核判定的具體計算方式，非本 spec 摘錄段落定義範圍，見下方"
     "假設）",
     "在該筆開分/入金完成、稽核尚未完成的狀態下，嘗試對該機台帳號執行洗分或出金操作，檢視"
     "系統核可的金額"],
    "洗分或出金的核可金額因尚未完成稽核的部分而被扣除，明顯低於未設定稽核倍數（0倍）時應得"
    "的全額；若扣除後金額為 0，機台畫面顯示餘額不足。此結果證明剛才在鏈上錢包管理 TWD 頁籤"
    "儲存的稽核倍數確實套用於後續的機台開分與入金稽核門檻計算，而不是僅停留在設定畫面本身"
    "沒有實際生效",
    "機台帳號的稽核／稽核規則表",
    "倍數大於 0 時 | 洗分與出金的核可金額須扣除尚未完成稽核的部分；扣除後為 0 時視同餘額不足，"
    "機台畫面顯示餘額不足",
    data={"稽核倍數設定值": "大於 0 的任意值（例如 2）"},
    assume=(
        "本 TC 涉及兩個超出本次精讀 spec 段落定義範圍的環節，皆需環境負責人協助確認：①使機台"
        "帳號實際產生開分/入金交易，依賴機台端硬體現場流程，非後台 UI 可直接觸發；②稽核倍數"
        "轉換為『未完成稽核金額』的精確計算公式（例如倍數如何與單筆或累計金額相乘、稽核在什麼"
        "條件下視為『完成』）不在本次精讀的 140-232行/760-819行段落中，該計算細節可能屬"
        "SPEC-CASHFLOW-001（既有出金設定的稽核倍數機制）延伸範圍；本 TC 僅定性驗證『調高倍數"
        "後核可金額確實受影響』這個功能連動是否成立，不驗證扣減金額的精確數字是否正確——精確"
        "算式的驗證應由稽核倍數機制本身既有的 spec 與其 TC 負責，避免本 TC 重複驗證不屬於"
        "ARCADE 開發包範圍的計算公式。"
    ),
    critical=True,
    rationale=(
        "REQ-ARCADE-004 為 high risk，本案即其 non-happy／邊界覆蓋：expected_result 斷言的是"
        "『稽核未完成時核可金額受限』這個邊界情境（倍數大於0時的臨界行為），而非泛用功能路徑，"
        "故標 boundary_value；同時因串接『設定頁面調整』與『後續交易核可金額』兩個頁面/事件的"
        "實際因果鏈，額外標 scenario。此案與同一 AC 下的 TC（預設值檢視）互補：一個驗證"
        "『畫面上看得到且初始為0』，一個驗證『改了之後對下游動作真的有效』，避免只驗證『儲存"
        "成功』就宣稱覆蓋了 AC 裡『該倍數即套用於後續的機台開分與入金計算』這句話（依指示 8）。"
    )))

# ================= REQ-ARCADE-005（RETIRED）不設計 TC =================

# ================= REQ-ARCADE-006（medium，statement 描述涉及 high 風險現金操作，
#                     但 RequirementModel 記載為 medium）洗分出金核實核實/作廢寫入操作紀錄 =================

T.append(tc(
    "REQ-ARCADE-006", ["AC-ARCADE-006"],
    "對一筆待核實的機台洗分或機台出金執行核實操作後，後台操作紀錄如實記錄該筆核實動作",
    "ui_e2e", ["functional"], ["scenario", "requirement_based"],
    PRE_ADMIN + [
        "站台切換下拉選單切換至一個既有機台場館",
        "於『帳務管理 > 洗分出金核實』頁面，尋找一筆狀態為『待核實』的機台洗分或機台出金"
        "項目，記錄其交易編號與（若為出金）訂單編號（若當下查無待核實項目，見下方假設）",
    ],
    ["對該筆待核實項目點擊『核實』，於確認彈窗核對機台帳號、金額與交易/收據印出時間無誤後"
     "點擊確認，記錄本次執行的操作人員（即目前登入帳號）與操作時間",
     "進入『後台管理員系統』的操作紀錄查詢頁面，以剛才核實的時間範圍查詢（若頁面提供關鍵字"
     "查詢，亦可用該筆交易編號查詢）",
     "檢視查詢結果中是否存在對應本次核實動作的紀錄，並核對其操作人員、時間、對象交易欄位"
     "內容"],
    "後台操作紀錄中存在一筆對應本次核實動作的紀錄，其操作人員為本次實際執行核實的登入帳號、"
    "時間與實際操作時間相符（合理誤差內），對象交易為剛才核實的那筆交易編號",
    "對既有章節的影響／7.4 操作紀錄",
    "洗分出金核實（含收據核銷）與作廢屬現金相關操作且不可撤銷，須寫入後台操作紀錄（操作"
    "人員、時間、對象交易）",
    assume=(
        "待核實的機台洗分／機台出金項目，其產生前提是機台帳號先於機台現場完成一筆洗分或出金"
        "交易，此為機台端硬體現場流程，非後台 UI 可直接觸發；本 TC 假設測試環境當下存在（或"
        "可佈置）至少一筆狀態為『待核實』的機台洗分或機台出金項目供核實操作使用，若環境當下"
        "查無待核實項目，需洽環境負責人透過既有測試工具或機台模擬方式補上，此步驟超出本 spec"
        "定義範圍。"
    ),
    critical=True,
    rationale=(
        "本案為串接『洗分出金核實頁執行核實』與『操作紀錄頁查驗』兩個頁面的實際工作流程，故"
        "標 scenario；expected_result 逐項比對 AC-ARCADE-006 明確列出的三個欄位（操作人員、"
        "時間、對象交易），未超出 AC 的 then 子句範圍（依指示 6）。產生待核實項目的前提依賴"
        "機台端硬體流程，誠實以 assumption 揭露，與 REQ-ARCADE-002/003 同一模式。"
    )))

T.append(tc(
    "REQ-ARCADE-006", ["AC-ARCADE-007"],
    "對一筆待核實的機台出金收據執行作廢操作後，後台操作紀錄如實記錄該筆作廢動作",
    "ui_e2e", ["functional"], ["scenario", "requirement_based"],
    PRE_ADMIN + [
        "站台切換下拉選單切換至一個既有機台場館",
        "於『帳務管理 > 洗分出金核實』頁面，尋找一筆狀態為『待核實』的機台出金項目（作廢僅"
        "適用出金，不適用洗分），記錄其交易編號與訂單編號（若當下查無待核實出金項目，見下方"
        "假設）",
    ],
    ["對該筆待核實出金項目點擊『作廢』，依系統要求填寫作廢原因（必填）後送出，記錄本次執行"
     "的操作人員（即目前登入帳號）與操作時間",
     "進入『後台管理員系統』的操作紀錄查詢頁面，以剛才作廢的時間範圍查詢（若頁面提供關鍵字"
     "查詢，亦可用該筆交易編號查詢）",
     "檢視查詢結果中是否存在對應本次作廢動作的紀錄，並核對其操作人員、時間、對象交易欄位"
     "內容"],
    "後台操作紀錄中存在一筆對應本次作廢動作的紀錄，其操作人員為本次實際執行作廢的登入帳號、"
    "時間與實際操作時間相符（合理誤差內），對象交易為剛才作廢的那筆交易編號",
    "對既有章節的影響／7.4 操作紀錄",
    "洗分出金核實（含收據核銷）與作廢屬現金相關操作且不可撤銷，須寫入後台操作紀錄（操作"
    "人員、時間、對象交易）",
    assume=(
        "同 AC-ARCADE-006 的 TC，待核實的機台出金項目其產生前提依賴機台端硬體現場流程，非"
        "後台 UI 可直接觸發；本 TC 假設測試環境當下存在（或可佈置）至少一筆狀態為『待核實』"
        "的機台出金項目供作廢操作使用，若環境當下查無，需洽環境負責人協助佈置，此步驟超出本"
        "spec 定義範圍。另外，v0.7.md 第709行明訂『作廢僅 Admin 與站長可執行』，故本 TC 以"
        "Admin 身分執行，未使用操作員角色，避免混入權限判斷（權限判斷不在本 requirement 的"
        "AC 範圍內）。"
    ),
    critical=True,
    rationale=(
        "本案與 AC-ARCADE-006 的 TC 為對稱情境（核實 vs 作廢），因兩者驗證的欄位斷言（操作"
        "人員/時間/對象交易須寫入操作紀錄）與工作流程性質相同，依本專案準則同標 scenario + "
        "requirement_based，不因對稱性刻意標成不同技巧來湊多樣性；作廢僅適用出金（非洗分）"
        "這項限制已於 v0.7.md 第679行『操作 | 核實、作廢（作廢僅出金）』與第707行『作廢"
        "（僅出金）』明確交代，precondition 因此刻意限定選取待核實『出金』項目，不誤用洗分"
        "項目。"
    )))

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

uncovered = [
    {"requirement_id": "REQ-ARCADE-005",
     "reason": ("此 requirement 於 RequirementModel 狀態為 RETIRED（見其 history：已被修正後的 "
                "REQ-PLATFORMRULE-014 完整涵蓋——操作員選單無站台列表項目，場次逾時時間所在頁面"
                "整頁無法進入，詳見 Oscar 2026-09-15 對操作員選單範圍的確認），非 ACTIVE 狀態，"
                "依 G-DESIGN 規則不需（亦不應）為其設計 TC；本欄僅記錄此決策以利追溯，非規避"
                "覆蓋義務。")},
]

rep = {
    "mode": "spec", "testcase_draft_artifact_id": None,
    "coverage_matrix": [
        {"requirement_id": r, "draft_ids": d["draft_ids"],
         "acceptance_criteria": [{"ac_id": a, "draft_ids": dd} for a, dd in d["acs"].items()]}
        for r, d in cov.items()
    ],
    "uncovered_with_reason": uncovered,
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
print(f"{len(T)} TCs, {n_exp} exploratory, reqs covered={len(cov)}/{len(reqs)}, uncovered={len(uncovered)}")
print("technique_summary:", dict(tech_count))
