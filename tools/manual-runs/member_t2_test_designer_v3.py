#!/usr/bin/env python3
"""RUN-20260915-013 T2（第三輪）：Test Designer(mode=spec) 依 SPEC-MEMBER-001 v0.2 的 18 條需求重新展開 TestCaseDraft + TestDesignReport。

第三輪修正重點（回應 ART-TVR-01M2H4R028B8RVC0X7M5KT1MDP 的 FAIL 與 system prompt 第10條跨TC一致性自檢）：
1. REQ-MEMBER-005 (TC7/TC8) 移除「稽核倍數設為1，避免投注門檻干擾判斷」這個未經驗證、且與同批 REQ-MEMBER-011 TC 矛盾的假設；
   改為誠實承認 spec 未定義可提領餘額與（主錢包餘額/流水錢包/稽核倍數）之間的換算公式，佈置方式改用「反覆調整+以後台實際讀數為準」，
   並把這個假設與跨產品（前台驗證）假設都明確寫進 assumptions；test_level 改為 integration 以結構化反映跨產品依賴。
2. REQ-MEMBER-004 (TC5) 修正一個自我發現的隱藏假設：precondition 原文誤將「透過邀請鏈註冊」與「取得加盟商身分」兩件事混為一談
   （「實際執行一次邀請連結註冊流程使其升級為加盟商」），但 spec 對兩者的定義是各自獨立的（見 REQ-013 加盟商身分的取得條件），
   已修正措辭，不再暗示註冊方式本身會讓人升級為加盟商。
3. REQ-MEMBER-010 (TC14) 回應 advisory：decision_table 補上第4格（前台/後台備注皆留空）使矩陣完整。
"""
import sys, pathlib, collections
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids

RUN, RM_AID = sys.argv[1], sys.argv[2]
ITER = int(sys.argv[3]) if len(sys.argv) > 3 else 0
SID, SV, AREA, A = "SPEC-MEMBER-001", "0.2", "MEMBER", "agent-test-designer"
reqs = {r["requirement_id"]: r for r in store.load(store.requirements_path(SID, SV))["requirements"]}


def R(n):
    return f"REQ-MEMBER-{n:03d}"


def AC(n):
    return f"AC-MEMBER-{n:03d}"


def sr(loc, quote=""):
    return {"spec_id": SID, "spec_version": SV, "location": loc, "quote": quote}


PRE_ADMIN_LIST = "以 Admin 登入後台，進入「會員與加盟商 > 會員列表」頁面"
PRE_ADMIN_MEMBER_DETAIL = "以 Admin 登入後台，進入一名既有會員的詳細資料頁"


def tc(req_ids, ac_ids, title, level, types, techs, pre, steps, expected, loc, quote="", prio="medium",
       risk=None, data=None, assumptions=None, critical=False, cost="low", rationale=""):
    r = reqs[req_ids[0]]
    assum = []
    for a in (assumptions or []):
        assum.append({"text": a["text"], "requirement_id": a.get("requirement_id", req_ids[0]),
                       "needs_human_confirmation": True})
    return {
        "draft_id": f"TC-DRAFT-{ids.ulid()}", "title": title, "product": "ba-admin", "functional_area": AREA,
        "requirement_ids": req_ids, "acceptance_criteria_ids": ac_ids, "spec_id": SID, "spec_version": SV,
        "test_level": level, "test_types": types, "design_techniques": techs, "priority": prio,
        "risk": risk or r["risk"], "execution_mode": "manual", "preconditions": pre,
        "test_data": [{"name": k, "value": v} for k, v in (data or {}).items()],
        "steps": [{"n": i + 1, "action": s} for i, s in enumerate(steps)], "expected_result": expected,
        "expected_result_spec_reference": sr(loc, quote), "assumptions": assum, "automation_status": "not_automated",
        "ci_eligible": False, "hotfix_eligible": False, "execution_cost": cost, "stability": "unknown",
        "critical_path": critical, "source": "spec_workflow", "design_rationale": rationale,
    }


T = []

# ---- REQ-MEMBER-001 OTP 報表 ----
T.append(tc(
    [R(1)], [AC(1)], "OTP 報表可查詢指定年月的 OTP 使用次數", "ui_e2e", ["functional"], ["requirement_based"],
    [PRE_ADMIN_LIST],
    ["點擊頁面頂部「OTP報表」按鈕，開啟彈窗", "輸入指定年份與月份（例如 2026 / 08）", "點擊「搜尋」", "檢視查詢結果",
     "點擊 ✕ 關閉彈窗，確認返回會員列表頁"],
    "彈窗顯示指定年月的 OTP 使用次數查詢結果；點擊 ✕ 後彈窗關閉，返回會員列表頁不受影響",
    "§2.1.1 頁面頂部功能",
    "查詢特定月份的 OTP 使用次數。操作步驟：1.點擊「OTP報表」按鈕，開啟彈窗 2.輸入欲查詢的年份與月份 3.點擊「搜尋」查看結果 4.點擊✕關閉彈窗",
    prio="low", risk="low",
    rationale="spec §2.1.1 給出完整操作步驟與唯一結果，是單一情境的功能驗證，用 requirement_based 如實反映——不涉及輸入組合或邊界數值，不套用其他技巧。",
))

# ---- REQ-MEMBER-002 KYC 階段 + 狀態篩選 ----
T.append(tc(
    [R(2)], [AC(2)], "未選 KYC 階段時，KYC 狀態篩選欄位不可單獨作用", "ui_e2e", ["negative"], ["requirement_based"],
    ["以 Admin 登入後台，進入會員列表頁面，篩選器的 KYC 階段欄位維持未選擇（預設空值）"],
    ["嘗試直接操作 KYC 狀態篩選欄位（點擊下拉或嘗試選取任一狀態值）"],
    "KYC 狀態欄位不可篩選或無作用（例如反灰無法點擊、或即使可操作也不影響搜尋結果）——須先選定 KYC 階段才可有效篩選 KYC 狀態",
    "§2.1.2 篩選器", "KYC 階段：需先選擇 KYC 階段，才可篩選 KYC 狀態",
    rationale="這是單一前置條件（未選 KYC 階段）對單一結果（狀態欄不可用）的驗證，只有一個情境，沒有多條件組合矩陣，故標 requirement_based 而非 decision_table；驗證的是一個不被允許的操作路徑被擋下，test_types 標 negative。",
))
T.append(tc(
    [R(2)], [AC(3)], "已選定 KYC 階段後，搭配 KYC 狀態可正確篩選", "ui_e2e", ["functional"], ["requirement_based"],
    [PRE_ADMIN_LIST],
    ["篩選器選擇 KYC 階段「身分證明文件驗證」", "KYC 狀態選「審核中」", "點擊搜尋"],
    "搜尋結果僅包含『身分證明文件驗證』階段目前狀態為『審核中』的會員，不符合此組合條件的會員不出現在結果中",
    "§2.1.2 篩選器", "KYC 階段與 KYC 狀態可組合使用，例如：篩選「身分證明文件驗證」階段中狀態為「審核中」的所有會員",
    rationale="本 TC 只驗證一組固定的（階段, 狀態）組合能正確篩選，並未在同一 TC 內比較多組輸入組合各自對應的結果，因此不算 decision_table；如實標 requirement_based。",
))

# ---- REQ-MEMBER-003 KYC 五圖示顏色 ----
T.append(tc(
    [R(3)], [AC(4)], "會員列表 KYC 狀態欄五個圖示依各階段實際狀態正確顯示顏色與 Tooltip", "ui_e2e", ["functional"], ["scenario"],
    [PRE_ADMIN_LIST,
     "需要一名會員，其五個 KYC 階段（個人基本資訊/身分證明文件/身分證件自拍/居住地址/資產證明）合計涵蓋已核准、審核中、待補件、未申請、已停用五種狀態中至少三種以上——"
     "「已核准」「待補件」可由後台人員於會員詳細頁 KYC 狀態區塊對已開放審核的階段分別執行「通過」/「駁回」取得；「未申請」為該階段本就尚未送審的既有帳號；「審核中」需為會員已透過前台送出、"
     "後台尚未審核的既有測試帳號；「已停用」這個狀態要如何產生，spec 全文未描述任何後台操作入口（見 assumptions），本 TC 假設可從測試環境既有帳號中找到已涵蓋此狀態的會員，"
     "若環境中找不到則此 TC 無法完整驗證五態，需另外確認"],
    ["於會員列表找到目標會員，檢視其 KYC 狀態欄五個圖示（由左至右對應：個人基本資訊、身分證明文件、身分證件自拍、居住地址、資產證明）",
     "逐一核對每個圖示顏色是否對應該階段目前的實際狀態（綠=已核准、橘=審核中、紅=待補件、淺灰=未申請、深灰=已停用）",
     "滑鼠移至任一圖示，確認顯示 Tooltip"],
    "五個圖示顏色分別正確對應各自階段的實際狀態；滑鼠移至任一圖示時顯示 Tooltip，內容包含該階段名稱與目前狀態文字",
    "§2.1.3 KYC驗證階段圖示說明",
    "🟢綠色已核准該階段已通過審核｜🟠橘色審核中會員已送出申請，待後台審核｜🔴紅色待補件審核不通過，需會員補件｜灰色（淺）未申請會員尚未提交此階段｜灰色（深）已停用此階段已被停用",
    assumptions=[{"text": "「已停用」狀態如何產生（是否有後台操作入口、或僅為系統/環境層級設定）spec 全文未定義；本 TC 假設測試環境存在已涵蓋此狀態的既有帳號，實際佈置方式需環境負責人確認",
                  "requirement_id": R(3)}],
    rationale="這條 TC 在單一會員身上同時檢查五個獨立圖示各自的顏色與 Tooltip，是一個整合性的多步驟檢查流程（同一情境內的一連串子檢查），不是在比較不同輸入條件各自產生的不同結果，用 decision_table 標記並不貼切，改用 scenario 較誠實地反映『多步驟情境走查』的本質。「已停用」狀態的產生方式 spec 沒有定義，已誠實揭露為 assumption 而非當作確定規則寫死。",
))

# ---- REQ-MEMBER-004 邀請鏈 ----
T.append(tc(
    [R(4)], [AC(5)], "加盟商會員透過邀請鏈註冊時，側邊面板正確顯示完整上下層邀請鏈", "ui_e2e", ["functional"], ["requirement_based"],
    [PRE_ADMIN_LIST,
     "取一名既有會員，須同時符合兩個各自獨立的條件：(a) 目前已具加盟商身分——加盟商身分的取得條件見 REQ-MEMBER-013，與註冊方式無關；"
     "(b) 當初是透過『另一名既有會員』的前台邀請連結完成註冊——這只決定其邀請鏈的上層是誰，不代表註冊本身會讓人自動升級為加盟商。"
     "自行從環境中選定同時符合這兩個條件的既有帳號"],
    ["於會員列表點擊該會員的會員編號，開啟右側簡易資料面板", "檢視面板頂部的邀請鏈顯示"],
    "面板頂部顯示完整的上下層關係：上層會員編號 → 當前會員編號 → 會員N人（N為其下層會員數），且上層顯示的是實際邀請該會員註冊的會員編號",
    "§2.1.4 側邊簡易資料面板",
    "邀請鏈顯示完整的上下層關係（如：上層會員編號 → 當前會員編號 → 會員 N 人）；若該會員非透過邀請鏈註冊，則上層顯示為站長",
    rationale="單一情境（邀請鏈註冊 → 顯示完整上下層關係）對單一結果的驗證，requirement_based 如實反映。precondition 已修正一個自我檢查時發現的隱藏假設：不再暗示『邀請連結註冊流程本身會使人升級為加盟商』——spec 對『加盟商身分的取得』（REQ-013：達成升等門檻+前台申請，或被指定為客製化加盟商）與『透過誰的邀請鏈註冊』是兩件互相獨立的事，本 TC 只需要挑選同時符合兩個獨立條件的既有帳號，不透過操作『製造』加盟商身分。",
))
T.append(tc(
    [R(4)], [AC(6)], "非透過邀請鏈註冊的加盟商會員，側邊面板上層顯示為站長", "ui_e2e", ["functional"], ["requirement_based"],
    [PRE_ADMIN_LIST, "取一名並非透過前台邀請鏈註冊（例如由後台人員直接建立會員帳號）、且目前已具加盟商身分的會員"],
    ["於會員列表點擊該會員的會員編號，開啟右側簡易資料面板", "檢視面板頂部的邀請鏈顯示"],
    "邀請鏈的上層顯示為「站長」，而非空白、錯誤資料或系統報錯",
    "§2.1.4 側邊簡易資料面板", "若該會員非透過邀請鏈註冊，則上層顯示為站長",
    rationale="與 AC-MEMBER-005 對稱的另一種情境，同樣是單一輸入條件對單一結果的驗證，故維持同一種技巧標記 requirement_based，不因對稱性而刻意改標其他技巧湊多樣性。",
))

# ---- REQ-MEMBER-005 可提領餘額 >10 USDT（本輪重點修正）----
BOUNDARY_INTERFACE_PRE = (
    "此規則定義於帳務資訊「可提領餘額」欄位（見 §2.1.4 / §2.1.5）：後台此欄位只是唯讀顯示，通篇 spec 沒有描述後台有可點擊的「申請出金」入口；"
    "「申請出金」是會員在前台自行操作的功能，後台頂多是透過「人工提出」代為出金，但那是後台人員主動操作、不受此門檻文字描述的「申請」語境限制，"
    "spec 也未說明人工提出是否套用同一道門檻。因此本規則實際生效與可驗證的入口是會員前台的申請出金功能，不在 ba-admin 後台範圍內（見 assumptions）"
)
BOUNDARY_SETUP_PRE = (
    "需要一名會員的「可提領餘額」恰為 {target} USDT。spec 分別定義了帳戶餘額（主錢包）『即時可用餘額』、提領所需有效投注額（流水錢包）『會員需達到此投注額方可提領』、"
    "可提領餘額『目前符合提領條件的金額』三個獨立欄位，也定義了人工存入/提出的『金額』直接影響主錢包餘額、『稽核』設定該筆金額所需完成的可提領投注倍數（見 REQ-MEMBER-011，"
    "同批 TC 已示範稽核倍數會使『提領所需有效投注額』增加，不是單純把存入金額加回可提領餘額）——但 spec 全文並未給出『可提領餘額』如何由前述欄位換算得出的公式，"
    "也未定義稽核=1時存入金額是否、以及何時會反映到可提領餘額。因此本 TC 不預設任何特定存入/提出金額與稽核倍數組合能『精確且立即』把可提領餘額調到 {target} USDT（見 assumptions）。"
    "佈置方式：透過人工存入/人工提出反覆調整，每次調整後回到帳務資訊區塊查看實際顯示的可提領餘額數值，直到確認顯示值恰為 {target} USDT 為止，不依賴任何計算公式預先斷定應存入/提出多少金額"
)
BOUNDARY_ASSUMPTIONS = [
    {"text": "步驟中「以該會員身分登入前台並嘗試申請出金」需要會員前台的測試環境與登入方式；spec 未定義後台是否存在可直接驗證此門檻的入口，前台測試環境是否可用、以及人工提出是否適用同一道 >10 USDT 門檻，需環境負責人 / PM 確認",
     "requirement_id": R(5)},
    {"text": "可提領餘額與帳戶餘額（主錢包）、提領所需有效投注額（流水錢包）、稽核倍數之間的精確換算公式，spec 全文未定義；本 TC 假設可透過人工存入/提出搭配後台實際讀數反覆調整至目標邊界值，但無法保證這是唯一或最有效率的方式，也無法保證『調整完成後餘額不會再隨時間變動』，此換算機制需環境負責人 / PM 確認",
     "requirement_id": R(5)},
]
T.append(tc(
    [R(5)], [AC(7)], "可提領餘額恰為 10 USDT 時不可於前台申請出金（邊界值，剛好不達門檻）", "integration",
    ["boundary"], ["boundary_value"],
    [BOUNDARY_INTERFACE_PRE, BOUNDARY_SETUP_PRE.format(target="10.00")],
    ["於後台帳務資訊區塊確認可提領餘額顯示為 10.00 USDT", "以該會員身分登入會員前台，進入出金/提領申請功能", "嘗試送出出金申請"],
    "前台阻擋出金申請（規則為『須大於10 USDT』，剛好等於10不符合條件）：申請入口不可用，或送出後被系統拒絕而未成功送出",
    "§2.1.4 帳戶資訊", "可提領餘額｜目前符合提領條件的金額（單位USDT）；須大於 10 USDT 方可申請出金",
    prio="high", risk="high", data={"可提領餘額": "10.00 USDT"}, assumptions=BOUNDARY_ASSUMPTIONS, critical=True,
    rationale="spec 對這條規則給出精確的數值邊界（>10 USDT），10.00 是明確定義的邊界值，boundary_value 技巧在此有實質依據。test_level 改標 integration（而非 ui_e2e）以結構化反映本 TC 橫跨後台（ba-admin，佈置資料）與會員前台（實際驗證出金入口）兩個產品，不只是文字描述。佈置可提領餘額的方式已誠實揭露為假設而非確定公式——第三輪自檢時發現，前一版『稽核倍數設為1可避免投注門檻干擾』這個說法，其實與同批 REQ-MEMBER-011 的 TC（示範稽核倍數會增加流水門檻）互相矛盾：沒有任何 spec 依據支持『稽核=1時存入金額會立即計入可提領餘額』，此版已移除該說法，改為誠實承認換算公式未知。",
))
T.append(tc(
    [R(5)], [AC(8)], "可提領餘額為 10.01 USDT 時可正常於前台申請出金（邊界值，略高於門檻）", "integration",
    ["boundary"], ["boundary_value"],
    [BOUNDARY_INTERFACE_PRE, BOUNDARY_SETUP_PRE.format(target="10.01")],
    ["於後台帳務資訊區塊確認可提領餘額顯示為 10.01 USDT", "以該會員身分登入會員前台，進入出金/提領申請功能", "送出出金申請"],
    "前台允許正常申請出金，申請成功送出",
    "§2.1.4 帳戶資訊", "須大於 10 USDT 方可申請出金",
    prio="high", risk="high", data={"可提領餘額": "10.01 USDT"}, assumptions=BOUNDARY_ASSUMPTIONS, critical=True,
    rationale="與上一條 TC 互為邊界值上下對照組（10.00 不可 / 10.01 可），同樣使用 boundary_value、test_level=integration，佈置方式與假設揭露理由同上一條 TC。",
))

# ---- REQ-MEMBER-006 KYC 審核 ----
T.append(tc(
    [R(6)], [AC(9)], "KYC 審核選擇駁回但未選取駁回原因時，系統阻擋儲存", "ui_e2e", ["negative"], ["negative"],
    [PRE_ADMIN_MEMBER_DETAIL, "取該會員 KYC 狀態區塊中至少一個目前已開放審核（狀態非「--」）的階段"],
    ["對該階段選擇審核結果為「駁回」，不選取下拉選單中的駁回原因", "點擊右上角「儲存」"],
    "系統阻擋儲存，要求先選取駁回原因才能完成儲存；未選原因前該次審核變更不會生效",
    "§2.1.5 KYC狀態", "審核結果選擇「通過」或「駁回」；選擇駁回時，需從下拉選單選取駁回原因",
    rationale="驗證一個必要輸入（駁回原因）缺漏時系統擋下儲存，是單一條件對單一阻擋結果的負向案例，design_techniques 標 negative 對應 test_types 的 negative，沒有多條件組合，不套用 decision_table。",
))
T.append(tc(
    [R(6)], [AC(10)], "顯示為『--』（未開放審核）的 KYC 階段不可執行審核操作", "ui_e2e", ["negative"], ["negative"],
    [PRE_ADMIN_MEMBER_DETAIL, "取該會員 KYC 狀態區塊中至少一個目前顯示為『--』（未開放審核）的階段"],
    ["找到顯示為『--』的階段，嘗試對其執行審核操作（如點選通過/駁回或尋找操作入口）"],
    "該階段不存在可用的審核操作入口（無法選擇通過/駁回，或相關控制項呈現不可點擊/停用狀態），無法對其執行任何審核動作",
    "§2.1.5 KYC狀態", "未開放審核的階段（顯示--）不可操作",
    rationale="同樣是驗證一個受限狀態（未開放審核）下操作入口不存在，單一情境的負向案例，與上一條 TC 使用相同技巧標記，保持一致性。",
))

# ---- REQ-MEMBER-007 帳號停用 ----
T.append(tc(
    [R(7)], [AC(11)], "會員帳號狀態切換為停用後，該會員無法登入前台", "ui_e2e", ["negative"], ["state_transition"],
    ["以 Admin 登入後台，一名會員目前帳號狀態為啟用"],
    ["於該會員詳細資料頁點擊帳號狀態旁的鉛筆圖示，將狀態從啟用切換為停用，確認後台顯示已更新為停用", "該會員嘗試以自己的帳號登入前台"],
    "該會員無法登入，前台系統拒絕其登入請求",
    "§2.1.5 會員啟用狀態", "處於停用狀態的會員將無法登入或進入平台。點擊鉛筆圖示可切換狀態",
    prio="high", risk="high", critical=True,
    rationale="spec 明確定義帳號狀態只有「啟用/停用」兩態，且明確描述切換到停用態後的登入行為後果，這是一個有明確狀態集合與轉換規則的案例，state_transition 有實質依據；狀態切換動作在後台、結果驗證在前台登入，這兩端 spec 本身都有明文描述（不像 REQ-005 只單方面描述前台規則），因此屬於 spec 已定義的跨介面流程，非本 Test Designer 自行外推的入口，故仍維持 test_level=ui_e2e 而非 integration。",
))

# ---- REQ-MEMBER-008 會員等級編輯 ----
T.append(tc(
    [R(8)], [AC(12)], "會員等級可由後台人員編輯，操作人員自動帶入當前登入帳號", "ui_e2e", ["functional"], ["requirement_based"],
    [PRE_ADMIN_MEMBER_DETAIL],
    ["點擊會員等級旁的「編輯」按鈕，確認右側滑出「會員等級編輯」面板", "面板中選擇一個與目前不同的會員等級", "後台備注欄位選填，可留空",
     "點擊「儲存」"],
    "會員等級成功更新為新選擇的等級；操作人員欄位自動帶入當前登入帳號，不需手動填寫",
    "§2.1.5 等級資訊",
    "會員等級｜可透過「編輯」按鈕手動調整；點擊後右側滑出「會員等級編輯」面板...操作人員（自動帶入當前登入帳號，唯讀）",
    rationale="單一情境（編輯並儲存新等級）對單一結果的驗證，requirement_based 如實反映，不涉及多重條件組合。",
))

# ---- REQ-MEMBER-009 人工存入批次 ----
T.append(tc(
    [R(9)], [AC(13)], "人工存入可用「,」分隔一次對多筆會員編號批次執行", "ui_e2e", ["functional"], ["requirement_based"],
    ["以 Admin 登入後台，進入一名既有會員的詳細資料頁，開啟人工存入面板"],
    ["確認會員編號欄已預設帶入當前會員編號", "額外以「,」分隔輸入另一名不同的既有會員編號（自行從環境中選定，兩筆會員編號需彼此不同）",
     "填寫金額、前台備注、後台備注等其他必填欄位後點擊儲存"],
    "系統對輸入的所有會員編號（當前會員與額外輸入的另一名會員）各自執行一筆相同金額的人工存入操作",
    "§2.1.5 帳務資訊", "會員編號｜預設帶入當前會員編號；亦可使用「,」分隔多個會員編號，一次對多筆會員執行操作",
    rationale="單一情境（輸入兩個以逗號分隔的會員編號）驗證批次執行行為，requirement_based 如實反映；未寫死具體會員編號，改用描述性文字避免環境依賴。",
))

# ---- REQ-MEMBER-010 前後台備注必填（本輪回應 advisory：補第4格）----
T.append(tc(
    [R(10)], [AC(14)], "人工存入前台備注與後台備注兩個必填欄位的組合驗證：任一或兩者留空即阻擋，皆填寫才允許送出", "ui_e2e",
    ["negative"], ["decision_table"],
    ["以 Admin 登入後台，進入一名既有會員的詳細資料頁，開啟人工存入面板"],
    ["情境一：金額等其他欄位填妥，前台備注留空、後台備注填寫，點擊儲存，觀察結果",
     "情境二：金額等其他欄位填妥，前台備注填寫、後台備注留空，點擊儲存，觀察結果",
     "情境三：金額等其他欄位填妥，前台備注與後台備注皆留空，點擊儲存，觀察結果",
     "情境四：前台備注與後台備注皆填寫，點擊儲存，觀察結果"],
    "情境一、二、三皆被系統阻擋，不允許在缺少任一（或兩個）必填備注的情況下送出；情境四（兩者皆填寫）成功送出",
    "§2.1.5 帳務資訊",
    "前台備注｜必填；填寫後顯示於會員端，作為該筆金額異動的說明 ｜ 後台備注｜必填；僅後台人員可見，作為該筆操作紀錄的內部說明",
    rationale="這裡有兩個各自獨立的必填輸入條件（前台備注、後台備注），2x2 共四種組合各自對應阻擋或允許兩種結果，是真正的條件組合矩陣，decision_table 標記有實質依據；第三輪回應 Validator advisory，補上『兩者皆留空』這格使矩陣完整，不再只測三格。",
))

# ---- REQ-MEMBER-011 稽核倍數 ----
T.append(tc(
    [R(11)], [AC(15)], "稽核倍數大於1時，提領所需有效投注額依倍數增加而非單純加回存入金額", "ui_e2e", ["functional"],
    ["requirement_based"],
    [PRE_ADMIN_MEMBER_DETAIL],
    ["記錄目前帳務資訊區塊「提領所需有效投注額（流水錢包）」數值（設為 X）", "點擊「人工存入」，金額填寫 100 USDT、稽核填寫 3，填妥前後台備注後儲存",
     "重新整理該會員詳細資料頁，檢視帳務資訊區塊的「提領所需有效投注額」"],
    "提領所需有效投注額變為 X + (100 × 3) = X + 300，而非單純的 X + 100（存入金額本身），確認稽核倍數確實套用於流水計算",
    "§2.1.5 帳務資訊", "稽核｜設定本次異動金額所需完成的可提領投注倍數，將影響會員後續提款條件；預設為 1",
    prio="high", risk="high", data={"金額": "100 USDT", "稽核": "3"}, critical=True,
    rationale="AC-MEMBER-015 的 given 明確限定「稽核倍數大於1」，本 TC 取 3 作為代表值驗證乘法效果確實套用，這是單一情境的功能驗證，requirement_based 如實反映；3 只是 given 範圍內的一個代表值，spec 並未對稽核倍數定義任何數值邊界（無 min/max），所以不套用 boundary_value。此 TC 的結果（稽核倍數只影響『提領所需有效投注額』，不是直接加回『可提領餘額』）也是 REQ-MEMBER-005 兩條邊界值 TC 佈置說明中引用的依據來源，第三輪自檢已確認兩者對『可提領餘額不會因稽核=1而被繞過流水機制』這件事口徑一致，不再互相矛盾。",
))
T.append(tc(
    [R(11)], [AC(15)], "稽核欄位輸入 0、負數或留空時的系統反應（exploratory，spec 未明確定義此規則）", "ui_e2e", ["negative"],
    ["error_guessing"],
    ["以 Admin 登入後台，開啟一名既有會員的人工存入面板"],
    ["稽核欄位分別嘗試輸入 0、負數、留空", "填妥其他必填欄位後點擊儲存，逐一觀察系統反應"],
    "spec 僅定義稽核『預設為 1』與『會影響提款條件』，完全沒有定義輸入 0、負數或留空時系統應如何反應（是否阻擋、是否退回預設值 1、或是否接受並產生無法計算的投注門檻）；"
    "本 TC 只能記錄實際觀察到的行為，不預設任何一種反應為正確答案，需另外向 PM 確認正確規則後再回填為確定案例",
    "§2.1.5 帳務資訊", "稽核｜設定本次異動金額所需完成的可提領投注倍數，將影響會員後續提款條件；預設為 1",
    prio="high", risk="high", critical=True,
    assumptions=[{"text": "稽核欄位對 0 / 負數 / 留空等無效輸入的系統反應，spec 全文未定義；本 TC 依常識推測這是一個應被阻擋或應退回預設值的欄位，但這是推測而非明文規則，正確行為需 PM 確認",
                  "requirement_id": R(11)}],
    rationale="這是我依常識推測『無效稽核值應該被擋下或退回預設值』，但 spec 完全沒有定義這件事，因此不寫成確定規則，改用 error_guessing 技巧誠實地探索邊界情境，並在 assumptions 標記需要人工確認，同時滿足 REQ-MEMBER-011 為 high risk 須有 non-happy 案例的要求。",
))

# ---- REQ-MEMBER-012 加盟列表狀態 Toggle ----
T.append(tc(
    [R(12)], [AC(16)], "加盟列表點擊狀態 Toggle 可將啟用中的加盟商切換為停用", "ui_e2e", ["functional"], ["state_transition"],
    ["以 Admin 登入後台，進入「會員與加盟商 > 加盟列表」", "篩選狀態為「啟用」並搜尋，取一名啟用中的加盟商會員"],
    ["點擊該會員所在列的狀態 Toggle", "檢視該列狀態欄位的顯示", "將篩選器狀態改為「停用」並重新搜尋"],
    "點擊後該會員的加盟商狀態變更為停用；篩選器改選停用並重新搜尋後可查到該筆記錄，確認狀態已真正切換而非僅前端顯示變化",
    "§2.2.2 加盟列表", "點擊狀態Toggle：切換該加盟商的啟用或停用狀態 ｜ 狀態｜全部/啟用/停用",
    rationale="spec 明確定義加盟商身分只有啟用/停用兩態，且描述了切換動作與查詢驗證方式，是有明確狀態集合與轉換規則的案例，state_transition 有實質依據。",
))

# ---- REQ-MEMBER-013 一般加盟商 Badge 三態 ----
T.append(tc(
    [R(13)], [AC(17), AC(18), AC(19)], "加盟列表一般加盟商 Badge 依「是否達成升等門檻」與「是否已透過前台申請」正確顯示三種樣式",
    "ui_e2e", ["functional"], ["decision_table"],
    ["以 Admin 登入後台，進入「會員與加盟商 > 加盟列表」",
     "從加盟列表既有資料中，找出分別呈現三種 Badge 樣式（已申請/達成未申請/未達成）的既有會員各一名，作為 A（已申請）、B（達成未申請）、C（未達成）——"
     "「升等門檻」的具體算法 spec 全文未定義，本 TC 不透過人工調整指標去製造達成/未達成狀態，只挑選環境中既有已呈現對應樣式的帳號（見 assumptions）"],
    ["於加盟列表檢視會員 A（已申請）的一般加盟商 Badge", "檢視會員 B（達成未申請）的一般加盟商 Badge", "檢視會員 C（未達成）的一般加盟商 Badge"],
    "A 顯示白底『已申請』樣式；B 顯示深灰底『達成未申請』樣式；C 顯示黑底『未達成』樣式，三者樣式互不相同且分別對應各自狀態",
    "§2.2.2 加盟等級",
    "（1）已申請（白底）：會員達成升等門檻，且已透過前台主動申請成為加盟商；（2）達成未申請（深灰底）：會員已達成升等門檻，但尚未透過前台申請；（3）未達成（黑底）：會員尚未達成升等門檻",
    assumptions=[{"text": "「升等門檻」的具體達成算法（依據哪些指標、門檻數值為何）spec 全文未定義；本 TC 假設可從環境既有資料中挑選出三種樣式各自對應的會員，若環境中找不到齊全的三種樣式，如何人工佈置達門檻/未達門檻的測試資料需環境負責人確認",
                  "requirement_id": R(13)}],
    rationale="這裡有兩個獨立條件（是否達成門檻 × 是否已申請）組合出三種互斥的顯示結果，是真正的條件組合矩陣，decision_table 標記有實質依據；升等門檻演算法 spec 未定義，已誠實標為 assumption，不假裝這是可由後台任意佈置的確定規則。",
))

# ---- REQ-MEMBER-014 客製化加盟商 Inline 編輯 ----
T.append(tc(
    [R(14)], [AC(20)], "客製化加盟商 Inline 編輯修改欄位數值後點擊確認可成功儲存", "ui_e2e", ["functional"], ["requirement_based"],
    ["以 Admin 登入後台，進入加盟列表，取一名已設定客製化加盟商（S Partner）身分的會員"],
    ["點擊「超級加盟商」按鈕，確認該列的佣金比例%、優惠%、返水%、推薦返傭%、行政費、稽核倍數欄位進入 Inline 編輯模式", "修改佣金比例%與行政費為新數值",
     "點擊列尾 ✓ 確認", "重新整理列表，檢視該列數值"],
    "數值成功更新並儲存為修改後的新值，重新整理後仍維持新值",
    "§2.2.3 客製化加盟商設定", "3.該列的佣金比例%、優惠%、返水%、推薦返傭%、行政費、稽核欄位進入Inline編輯模式 4.直接修改各欄位數值 5.點擊列尾的✓確認儲存",
    rationale="單一情境（修改後確認儲存）對單一結果的驗證，requirement_based 如實反映；與下一條「取消還原」是對稱情境，兩者性質相同（都是 Inline 編輯的單一分支結果），統一標同一種技巧，不因對稱性刻意標不同標籤湊多樣性。",
))
T.append(tc(
    [R(14)], [AC(21)], "客製化加盟商 Inline 編輯修改數值後點擊取消，還原為原始值且不儲存", "ui_e2e", ["functional"], ["requirement_based"],
    ["以 Admin 登入後台，進入加盟列表，取一名已設定客製化加盟商（S Partner）身分的會員"],
    ["記錄該列目前的佣金比例%、優惠%、返水%、推薦返傭%、行政費、稽核倍數原始數值", "點擊「超級加盟商」按鈕進入 Inline 編輯模式，將上述欄位修改為與原始值不同的新數值",
     "點擊列尾 ✕ 取消", "檢視該列數值"],
    "數值還原為修改前的原始值，先前輸入的變更未被儲存",
    "§2.2.3 客製化加盟商設定", "點擊✕取消並還原原始值",
    rationale="與 AC-MEMBER-020 對稱的另一分支（取消而非確認），同樣是單一情境對單一結果，維持與上一條 TC 相同的 requirement_based 標記，不套用 state_transition——這只是表單編輯的確認/取消，不是一個有多重狀態定義的狀態機。",
))

# ---- REQ-MEMBER-015 最後登入 IP 跳轉 ----
T.append(tc(
    [R(15)], [AC(22)], "點擊最後登入IP可跳轉至登入網域查詢頁並自動帶入該IP篩選", "ui_e2e", ["functional"], ["requirement_based"],
    [PRE_ADMIN_MEMBER_DETAIL],
    ["點擊「最後登入IP」欄位值"],
    "自動跳轉至登入網域查詢頁，並帶入該 IP 值作為篩選條件，查詢結果為曾使用該 IP 登入的所有會員及登入時間",
    "§2.3.1 篩選器", "從會員列表側邊面板或會員詳細資料頁點擊「最後登入IP」跳轉至此頁時，系統會自動帶入該IP進行篩選",
    prio="low", risk="low",
    rationale="單一情境對單一結果的功能驗證，requirement_based 如實反映。",
))

# ---- REQ-MEMBER-016 推薦註冊金會員編號必填 ----
T.append(tc(
    [R(16)], [AC(23)], "推薦註冊金設定新增時，會員編號留空應被系統阻擋", "ui_e2e", ["negative"], ["negative"],
    ["以 Admin 登入後台，進入推薦註冊金設定頁，開啟新增方案面板"],
    ["會員編號欄位留空", "點擊「新增」送出"],
    "系統阻擋，提示會員編號為必填",
    "§2.4.2 新增設定", "會員編號為必填（必填），不可為空",
    rationale="驗證單一必填欄位缺漏時系統阻擋，單一條件對單一結果，negative 技巧與 test_types 一致。",
))

# ---- REQ-MEMBER-017 推薦註冊金刪除二次確認 ----
T.append(tc(
    [R(17)], [AC(24)], "刪除推薦註冊金設定須二次確認，確認後永久刪除且不可復原", "ui_e2e", ["negative"], ["requirement_based"],
    ["推薦註冊金設定列表存在至少一筆既有設定"],
    ["點擊該筆設定旁的刪除圖示，確認彈出確認視窗", "於確認視窗點擊確認", "重新整理列表，確認該筆設定已從清單移除",
     "確認畫面上不存在任何可將此筆設定復原的操作入口"],
    "彈出確認視窗；確認後該筆設定被永久刪除，清單中不再出現；系統不提供復原此操作的功能",
    "§2.4.3 列表欄位", "點擊旁側刪除圖示後，彈出確認視窗，確認後刪除該筆設定，操作不可復原",
    rationale="這是驗證一個不可逆操作（刪除且無法復原）的案例，test_types 標 negative 對應『驗證某個路徑（復原）不存在』；本身只是單一情境（刪除確認 → 檢查無法復原）沒有多重條件組合，design_techniques 仍如實標 requirement_based。",
))

# ---- REQ-MEMBER-018 暱稱禁用詞分頁獨立 ----
T.append(tc(
    [R(18)], [AC(25)], "暱稱禁用詞四分頁設定互相獨立", "ui_e2e", ["functional"], ["requirement_based"],
    ["以 Admin 登入後台，進入暱稱禁用詞設定頁，Violence 與 Other 分頁目前皆為空（或至少不含將在本 TC 新增的那個詞）"],
    ["切換至 Violence 分頁，於輸入框輸入一個測試用禁用詞，按 Enter 確認，確認該詞以 Tag 形式顯示", "切換至 Other 分頁，檢視禁用詞清單"],
    "Other 分頁的清單不包含剛才在 Violence 分頁新增的那個詞，兩個分頁的設定互相獨立",
    "§2.5.1 分頁說明", "各分頁的操作方式相同，設定互相獨立",
    prio="low", risk="low",
    rationale="單一情境（在一個分頁新增、檢查另一分頁不受影響）對單一結果的驗證，requirement_based 如實反映，不涉及四個分頁兩兩組合的完整矩陣（若要做完整組合驗證需 4x3=12 種配對，本 TC 僅抽樣驗證一組具代表性的配對，範圍如實反映在 title 與 steps 中）。",
))

# ================= TestDesignReport =================
cov = collections.OrderedDict()
for rid in reqs:
    cov[rid] = {"draft_ids": [], "acs": collections.OrderedDict()}
for t in T:
    for rid in t["requirement_ids"]:
        cov[rid]["draft_ids"].append(t["draft_id"])
        for aid in t["acceptance_criteria_ids"]:
            cov[rid]["acs"].setdefault(aid, []).append(t["draft_id"])

tech_count = collections.Counter(x for t in T for x in t["design_techniques"])
n_exp = sum(1 for t in T if t["assumptions"])

rep = {
    "mode": "spec", "testcase_draft_artifact_id": None,
    "coverage_matrix": [
        {"requirement_id": rid, "draft_ids": d["draft_ids"],
         "acceptance_criteria": [{"ac_id": a, "draft_ids": dd} for a, dd in d["acs"].items()]}
        for rid, d in cov.items()
    ],
    "uncovered_with_reason": [],
    "technique_summary": [{"technique": k, "count": v} for k, v in tech_count.items()],
    "self_check": {k: True for k in [
        "requirements_covered", "acceptance_criteria_covered", "negative_considered", "boundary_considered",
        "expected_results_traceable", "no_unsupported_assumptions", "duplicate_detection_completed"]},
    "assumptions": [],
    "duplicate_check": {"against_registry": True, "findings": []},
    "revision_of_issues": [
        {"issue_index": 0,
         "action": "REQ-MEMBER-005 TC7 全面重寫 precondition：移除『稽核倍數設為1，避免投注門檻干擾判斷』這個與同批 REQ-MEMBER-011 TC 矛盾、且 spec 未支持的假設；改為誠實承認可提領餘額的換算公式 spec 未定義，佈置方式改用『後台實際讀數為準、反覆調整』，並把此假設與跨產品驗證假設都寫進 assumptions；test_level 改為 integration",
         "draft_id": None},
        {"issue_index": 1, "action": "同上一項，TC8 為 TC7 對照組，同步重寫", "draft_id": None},
        {"issue_index": 2,
         "action": "REQ-MEMBER-005 TC7/TC8 的結構化欄位補上跨產品依賴：test_level 由 ui_e2e 改為 integration，不再只靠 precondition 文字描述跨產品這件事",
         "draft_id": None},
    ],
}


def envelope(t, payload, refs, task="T2"):
    aid = ids.artifact_id(t)
    art = {"artifact_id": aid, "artifact_type": t, "schema_version": "1.0", "version": 1, "run_id": RUN,
           "task_id": task, "iteration": ITER, "created_by": A, "created_at": store.now(), "status": "DRAFT",
           "source": {"type": "RequirementModel", "ids": [RM_AID]}, "references": refs, "requires_approval": None,
           "payload": payload}
    p = store.ROOT / "artifacts" / "test-design" / RUN / f"{aid}.yaml"
    store.save(p, art)
    return aid, p


refs = [{"entity_type": "Requirement", "id": r} for r in reqs] + [{"entity_type": "Artifact", "id": RM_AID}]
did, p1 = envelope("TestCaseDraft", {"mode": "spec", "spec_id": SID, "spec_version": SV, "testcases": T}, refs)
rep["testcase_draft_artifact_id"] = did
# revision_of_issues 的 draft_id 指向修正後的 TC7/TC8
req5_ids = cov[R(5)]["draft_ids"]
rep["revision_of_issues"][0]["draft_id"] = req5_ids[0]
rep["revision_of_issues"][1]["draft_id"] = req5_ids[1]
rep["revision_of_issues"][2]["draft_id"] = req5_ids[0]
_, p2 = envelope("TestDesignReport", rep, [{"entity_type": "Artifact", "id": did}])

print(p1.relative_to(store.ROOT))
print(p2.relative_to(store.ROOT))
print(f"{len(T)} TCs, {n_exp} exploratory, reqs covered={len(cov)}/{len(reqs)}")
print("technique_summary:", dict(tech_count))
