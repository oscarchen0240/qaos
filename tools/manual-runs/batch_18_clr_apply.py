#!/usr/bin/env python3
"""批次把18張已ANSWERED/APPLIED但答案尚未真正寫回RequirementModel的CLR，正式套用到
對應REQ的rejection_contract.description（部分需同時修正statement本身）。
涵蓋ACCOUNT 5張、DAILYREPORT 7張（001/002/003/004/005/006/008）、SITELIST 6張。
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store

def load(sid, sv):
    return store.load(store.requirements_path(sid, sv))

def get_req(d, rid):
    return next(r for r in d["requirements"] if r["requirement_id"] == rid)

def add_history(r, trigger):
    r.setdefault("history", []).append({
        "at": store.now(), "from_status": "ACTIVE", "to_status": "ACTIVE",
        "by": "oscarchen@blockaction.tech", "trigger": trigger,
    })

# ============ ACCOUNT ============
d = load("SPEC-ACCOUNT-001", "0.1")

r = get_req(d, "REQ-ACCOUNT-010")
r["rejection_contract"]["description"] = (
    "操作員權限在會員列表裡「創建會員帳號」按鈕隱藏（前端層級限制，非送出後才被API拒絕）。"
    "依CLR-ACCOUNT-001確認"
)
add_history(r, "clarification_applied_CLR-ACCOUNT-001")

r = get_req(d, "REQ-ACCOUNT-016")
r["rejection_contract"]["description"] = (
    "已使用過或已逾時的重設連結被再次點擊時，前端顯示「連結已失效，請重新申請」。依CLR-ACCOUNT-002確認"
)
add_history(r, "clarification_applied_CLR-ACCOUNT-002")

r = get_req(d, "REQ-ACCOUNT-018")
r["rejection_contract"]["description"] = (
    "機台帳號無法使用信箱登入註冊，所以前台不存在「忘記密碼」功能入口可用——並非送出申請後才被擋，"
    "而是該帳號本身無法透過此入口操作（因非以信箱註冊）。依CLR-ACCOUNT-003確認"
)
add_history(r, "clarification_applied_CLR-ACCOUNT-003")

r = get_req(d, "REQ-ACCOUNT-032")
r["rejection_contract"]["description"] = (
    "機台前台沒有優惠活動與簽到頁面，玩家（機台）介面上根本無法進入，因此無從參與，"
    "不需要後端額外阻擋邏輯。依CLR-ACCOUNT-004確認"
)
add_history(r, "clarification_applied_CLR-ACCOUNT-004")

r = get_req(d, "REQ-ACCOUNT-007")
r["statement"] = (
    "帳號類型選「線上」時不帶額外欄位，建立一名所屬目前站台的線上會員，電子信箱與電話留空。"
    "若所屬站台為機台場館：帳號類型雖為線上，但因所屬站台是機台場館，仍需套用該場館的部分設定"
    "（例如額度上限），具體要套用哪些場館設定與此類帳號的用途/設計目的，PM表示後續再另行設計"
    "（依CLR-ACCOUNT-005確認方向為此選項，非完全比照一般線上會員，也非禁止此組合）；"
    "其餘一般站台底下建立的線上會員，建立後行為與前台註冊會員完全相同"
)
r["rejection_contract"]["description"] = "不帶額外欄位即為規則；機台場館底下的例外規則見statement，依CLR-ACCOUNT-005"
add_history(r, "clarification_applied_CLR-ACCOUNT-005")

store.save(store.requirements_path("SPEC-ACCOUNT-001", "0.1"), d)
print("ACCOUNT: 5 requirements updated")

# ============ DAILYREPORT ============
d = load("SPEC-DAILYREPORT-001", "0.1")

r = get_req(d, "REQ-DAILYREPORT-001")
r["rejection_contract"]["description"] = (
    "越權時（操作員嘗試切換至非自身場館）：前端已擋（站台切換選單不提供其他場館選項）；"
    "後端也擋（直接呼叫API帶非自身場館參數會被拒絕）。依CLR-DAILYREPORT-001確認（含2026-09-14補充）"
)
add_history(r, "clarification_applied_CLR-DAILYREPORT-001")

r = get_req(d, "REQ-DAILYREPORT-003")
r["rejection_contract"]["description"] = (
    "輸入不存在或非本場館的機台帳號：找不到用戶即可，API回rows: []（空列表，不報錯）。"
    "依CLR-DAILYREPORT-002確認"
)
add_history(r, "clarification_applied_CLR-DAILYREPORT-002")

r = get_req(d, "REQ-DAILYREPORT-004")
r["rejection_contract"]["description"] = (
    "結算日期異常（起日晚於迄日等）：找不到資料即可，API回rows: []；未填結算日期時，前端popup"
    "警示「失敗：結算日期為必填」，不送出查詢。依CLR-DAILYREPORT-003確認（含2026-09-14補充）"
)
add_history(r, "clarification_applied_CLR-DAILYREPORT-003")

r = get_req(d, "REQ-DAILYREPORT-007")
r["rejection_contract"]["description"] = (
    "場館未設定日結時間時，以預設值00:00 UTC+0切分營業日（畫面截圖顯示該欄位預設值為上午12:00）。"
    "依CLR-DAILYREPORT-004確認"
)
add_history(r, "clarification_applied_CLR-DAILYREPORT-004")

r = get_req(d, "REQ-DAILYREPORT-011")
r["rejection_contract"]["description"] = (
    "「標示提醒」的呈現方式：待核實的機台洗分交易列表顯示黃色標籤「⚠ 現金未確認」，核實狀態欄為"
    "藍色「待核實」，已核實者為綠色「已核實」；報表的待核實洗分提醒沿用同款黃色警示標籤。"
    "依CLR-DAILYREPORT-005確認"
)
add_history(r, "clarification_applied_CLR-DAILYREPORT-005")

r = get_req(d, "REQ-DAILYREPORT-016")
r["rejection_contract"]["description"] = (
    "無資料時列表仍列出（日期正常顯示、各欄位顯示0）；匯出CSV無資料時的行為推定同列表（一列0）。"
    "依CLR-DAILYREPORT-006確認（PM提供的完整欄位清單含「注單數」，但spec.md v0.1列表欄位定義尚未"
    "列出此欄，屬文件缺口，已記錄於project memory待後續統一處理，不影響本條rejection_contract的"
    "有效性）"
)
add_history(r, "clarification_applied_CLR-DAILYREPORT-006")

r = get_req(d, "REQ-DAILYREPORT-005")
r["rejection_contract"]["description"] = (
    "不完整週：照結算日期範圍實際起迄顯示（不強制補滿整週），只要「完整」的週仍以週一為週起；"
    "範圍外的營業日不計入該列合計。依CLR-DAILYREPORT-008確認（含具體算例：結算日期09-03起、按週"
    "→列出「2026-09-07~2026-09-13」與「2026-09-03~2026-09-06」兩列，08-31~09-02不計入第一列合計）"
)
add_history(r, "clarification_applied_CLR-DAILYREPORT-008")

store.save(store.requirements_path("SPEC-DAILYREPORT-001", "0.1"), d)
print("DAILYREPORT: 7 requirements updated")

# ============ SITELIST ============
d = load("SPEC-SITELIST-001", "0.4")

r = get_req(d, "REQ-SITELIST-002")
r["rejection_contract"]["description"] = (
    "若繞過前端UI、直接呼叫建立站台API並帶入與上層站台不同的站台類型，後端同樣拒絕"
    "（不只是前端唯讀限制）。依CLR-SITELIST-001確認"
)
add_history(r, "clarification_applied_CLR-SITELIST-001")

r = get_req(d, "REQ-SITELIST-005")
r["rejection_contract"]["description"] = (
    "額度上限輸入負數：前端顯示「值必須大於或等於0」，後端也拒絕（雙層驗證）。依CLR-SITELIST-002確認"
)
add_history(r, "clarification_applied_CLR-SITELIST-002")

r = get_req(d, "REQ-SITELIST-006")
r["rejection_contract"]["description"] = (
    "場次逾時時間輸入0、負數或低於1小時：後端拒絕（最低值1小時）；輸入超過17位數等極端格式："
    "前端跳格式錯誤，後端阻擋並回傳通用錯誤代碼COMMON_INVALID_REQUEST_FORMAT。依CLR-SITELIST-003"
    "確認（原問題另提及「操作員唯讀」，因本spec未定義該角色，無法在本功能區驗證，不在此規則範圍內）"
)
add_history(r, "clarification_applied_CLR-SITELIST-003")

r = get_req(d, "REQ-SITELIST-011")
r["rejection_contract"]["description"] = (
    "站長嘗試存取平行或上層站台（含直接以站台ID呼叫查詢API）：依「三個角色的關係」權限範圍模型"
    "（範圍由所屬站台決定，不是角色本身；站長可見範圍＝自身所屬站台及其子樹），該站台不在其可見"
    "範圍內，應無法取得資料。依CLR-SITELIST-004確認"
)
add_history(r, "clarification_applied_CLR-SITELIST-004")

r = get_req(d, "REQ-SITELIST-012")
r["rejection_contract"]["description"] = (
    "站長若繞過前端直接呼叫建立站台API並帶入其他上層站台ID：後端已拒絕（不接受繞過前端指定其他"
    "上層站台），此前RD回報的「直接呼叫API仍會成功」風險已修復。依CLR-SITELIST-005確認"
)
add_history(r, "clarification_applied_CLR-SITELIST-005")

r = get_req(d, "REQ-SITELIST-013")
r["rejection_contract"]["description"] = (
    "站長若繞過前端直接呼叫編輯站台API並帶入會形成循環的上層站台ID：後端已拒絕（同CLR-SITELIST-005"
    "的修復範圍）。依CLR-SITELIST-006確認（Admin編輯時的循環防護是否也有對應後端驗證，本次回覆"
    "未涵蓋，若後續測試發現可繞過需另案處理）"
)
add_history(r, "clarification_applied_CLR-SITELIST-006")

store.save(store.requirements_path("SPEC-SITELIST-001", "0.4"), d)
print("SITELIST: 6 requirements updated")
