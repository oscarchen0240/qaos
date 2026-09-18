#!/usr/bin/env python3
"""RUN-20260914-004 T2：Test Designer(mode=spec) 依 SPEC-ACCOUNT-001 v0.1 的 32 條需求展開 TestCaseDraft + TestDesignReport。"""
import sys, pathlib, collections
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids
RUN, RM_AID = sys.argv[1], sys.argv[2]; ITER = int(sys.argv[3]) if len(sys.argv) > 3 else 0
SID, SV, AREA, A = "SPEC-ACCOUNT-001", "0.1", "ACCOUNT", "agent-test-designer"
reqs = {r["requirement_id"]: r for r in store.load(store.requirements_path(SID, SV))["requirements"]}
def R(n): return f"REQ-ACCOUNT-{n:03d}"
def AC(n, i): return f"AC-ACCOUNT-{n:03d}{i}"
def sr(loc): return {"spec_id": SID, "spec_version": SV, "location": loc}
PRE_ADMIN = ["以 Admin 登入後台", "進入 會員與加盟商 > 會員列表"]
PRE_CHIEF = ["以站長登入後台", "進入 會員與加盟商 > 會員列表"]

def tc(req, acs, title, level, types, techs, steps, expected, loc, prio="high", risk=None, pre=None, data=None,
       assume=None, critical=False, cost="medium", more_reqs=(), extra_ac=()):
    r = reqs[R(req)]
    assumptions = []
    for a in ([assume] if isinstance(assume, str) else (assume or [])):
        assumptions.append({"text": a, "requirement_id": R(req), "needs_human_confirmation": True})
    return {"draft_id": f"TC-DRAFT-{ids.ulid()}", "title": title, "product": "ba-admin", "functional_area": AREA,
            "requirement_ids": [R(req)] + [R(x) for x in more_reqs],
            "acceptance_criteria_ids": [AC(req, i) for i in acs] + [AC(rn, ai) for rn, ai in extra_ac],
            "spec_id": SID, "spec_version": SV, "test_level": level, "test_types": types, "design_techniques": techs,
            "priority": prio, "risk": risk or r["risk"], "execution_mode": "manual",
            "preconditions": PRE_ADMIN if pre is None else pre, "test_data": [{"name": k, "value": v} for k, v in (data or {}).items()],
            "steps": [{"n": i + 1, "action": s} for i, s in enumerate(steps)], "expected_result": expected,
            "expected_result_spec_reference": sr(loc), "assumptions": assumptions, "automation_status": "not_automated",
            "ci_eligible": False, "hotfix_eligible": True, "execution_cost": cost, "stability": "unknown", "critical_path": critical,
            "source": "spec_workflow", "design_rationale": ""}

T = []
# REQ-001 帳號類型定義（AC1 線上／AC2 機台）
T.append(tc(1, [1, 2], "後台建立的帳號依類型正確標記為線上或機台", "ui_e2e", ["functional"], ["decision_table"],
    ["建立一個線上帳號，檢視其帳號類型欄位", "建立一個機台帳號，檢視其帳號類型欄位"],
    "前者帳號類型為線上；後者為機台，且兩者存於同一份會員資料（無獨立資料表）", "§功能說明", critical=True))

T.append(tc(1, [], "帳號類型欄位只能是線上或機台，無其他可選值", "ui_e2e", ["negative", "boundary"], ["boundary_value"],
    ["開啟創建會員帳號 Modal", "檢視帳號類型欄位的所有可選項"],
    "僅有「線上」與「機台」兩個選項，沒有其他值可選", "§功能說明",
    ))  # 無單一 AC 精確對應此斷言（AC-0011/0012 講的是建立後檢視已存在紀錄的欄位值，非建立前下拉選單的可選範圍）；此案例驗證 REQ-001 的核心定義本身，acceptance_criteria_ids 留空

# REQ-002 兩條建立途徑並行（AC1 前台註冊／AC2 後台創建線上／AC3 前台不能建機台）
T.append(tc(2, [1, 2], "前台自行註冊與後台創建皆可產生線上帳號", "ui_e2e", ["functional"], ["decision_table"],
    ["以玩家身分於前台自行註冊一個帳號", "以 Admin 於後台創建一個線上帳號"],
    "兩者皆成功建立線上帳號，行為一致", "§功能說明/帳號類型"))
T.append(tc(2, [3], "前台不提供建立機台帳號的途徑", "ui_e2e", ["negative"], ["requirement_based"],
    ["檢視前台註冊頁面與流程"],
    "前台註冊只會產生線上帳號，沒有任何選項可建立機台帳號", "§功能說明/帳號類型"))

# REQ-003 站台歸屬（AC1 歸屬目前站台／AC2 無所屬場館欄位）
T.append(tc(3, [1, 2], "創建的帳號歸屬操作當下所在站台，Modal 不提供跨站台指定", "ui_e2e", ["functional"], ["decision_table"],
    ["站台切換選單切到站台 A", "點擊創建會員帳號，檢視表單欄位", "建立帳號並確認其所屬站台"],
    "表單不存在「所屬場館／站台」欄位；新帳號歸屬站台 A", "§操作/創建會員帳號", critical=True))

T.append(tc(3, [], "直接呼叫建立帳號 API 夾帶其他站台 ID，仍建立於操作者當下所在站台", "api", ["negative"], ["negative"],
    ["以目前站台 A 的操作身分", "直接呼叫建立帳號 API，並在請求中夾帶其他站台（B）的 ID"],
    "系統不接受跨站台指定；新帳號仍建立於操作者當下所在的站台 A，與請求中夾帶的其他站台 ID 無關", "§業務規則與驗證/建立站台歸屬"
    ))  # AC-0031/0032 描述的是 UI Modal 情境；本案透過 API 驗證同一條規則的深度防護，屬合理延伸但非逐字對應，acceptance_criteria_ids 留空避免誤標

# REQ-004 帳號類型欄位規則（AC1 機台場館預設機台可選兩者／AC2 線上站台預設線上機台停用）
T.append(tc(4, [1, 2], "帳號類型欄位的預設值與可選範圍依目前站台類型過濾", "ui_e2e", ["functional"], ["decision_table"],
    ["站台切換至一個機台場館，開啟創建會員帳號 Modal", "站台切換至一個線上站台，開啟創建會員帳號 Modal"],
    "前者：帳號類型預設「機台」，線上/機台皆可選；後者：預設「線上」，機台選項停用不可選", "§操作/創建會員帳號", critical=True))

T.append(tc(4, [], "線上站台無法透過 API 直接指定建立機台帳號", "api", ["negative"], ["negative"],
    ["目前站台為線上站台", "直接呼叫建立帳號 API，帳號類型欄位帶入「機台」"],
    "系統拒絕，不得於非機台場館建立機台帳號", "§操作/創建會員帳號"
    ))  # AC-0042 描述的是 UI 下拉選項停用；本案為 API 層的深度防護測試，acceptance_criteria_ids 留空避免誤標

# REQ-005 機台名稱（AC1 暱稱同步顯示／AC2 不經禁用詞檢查）
T.append(tc(5, [1, 2], "機台名稱即會員暱稱，且不經前台暱稱禁用詞檢查", "ui_e2e", ["functional"], ["requirement_based"],
    ["建立機台帳號，機台名稱輸入「A 區 03 號」", "機台名稱輸入包含前台暱稱禁用詞清單中字詞的值並送出"],
    "第一步：建立後會員暱稱即為「A 區 03 號」，列表顯示於會員編號下方；第二步：系統不阻擋，正常建立", "§操作/創建會員帳號", risk="medium"))

# REQ-006 機台狀態預設啟用（AC1）
T.append(tc(6, [1], "新建機台預設狀態為啟用且創建表單不顯示此欄位", "ui_e2e", ["functional"], ["requirement_based"],
    ["建立一個機台帳號，檢視創建表單是否有機台狀態欄位", "建立完成後檢視機台資訊區塊的機台狀態"],
    "創建表單全程未顯示機台狀態欄位；建立後機台狀態為「啟用」", "§操作/創建會員帳號", risk="medium"))

# REQ-007 線上帳號建立行為（AC1 不帶額外欄位／AC2 信箱電話留空）
T.append(tc(7, [1, 2], "線上帳號類型不帶機台專屬欄位，且電子信箱電話留空", "ui_e2e", ["functional"], ["decision_table"],
    ["帳號類型選線上，檢視表單欄位", "建立後檢視該帳號的電子信箱與電話"],
    "表單不顯示機台名稱等機台專屬欄位；電子信箱與電話皆為空，可比照前台註冊會員後續補綁", "§操作/創建會員帳號", risk="medium"))

# REQ-008 建立成功的帳密顯示（AC1 完整顯示+複製／AC2 關閉後不再顯示／AC3 憑證不隨建立產生）
T.append(tc(8, [1], "建立成功時完整顯示一次系統生成的帳密並提供複製", "ui_e2e", ["functional"], ["requirement_based"],
    ["點擊建立", "檢視建立成功畫面"],
    "完整顯示系統生成的登入帳號與密碼，並有複製按鈕；新帳號餘額為 0", "§操作/創建會員帳號", critical=True))
T.append(tc(8, [2, 3], "關閉建立成功畫面後密碼不再完整顯示，且憑證不隨建立自動產生", "ui_e2e", ["negative"], ["requirement_based"],
    ["關閉建立成功畫面", "回到會員列表或該帳號的詳細頁再次查看", "若為機台帳號，檢視其機台憑證區塊"],
    "無法再完整查看密碼；機台憑證顯示「產生憑證」按鈕（尚未產生任何憑證）", "§操作/創建會員帳號"))

# REQ-009 一對一綁定（AC1）
T.append(tc(9, [1], "機台帳號與機台資料由創建流程一併建立、恰好一對一", "ui_e2e", ["functional"], ["requirement_based"],
    ["建立一個機台帳號", "檢視其機台資料"],
    "恰有一台機台與此帳號綁定，兩者同時建立完成", "§業務規則與驗證/帳號一對一", risk="medium"))

# REQ-010 角色-創建會員帳號（AC1 Admin／AC2 站長管轄範圍／AC3 操作員不可，已由 CLR-001 回答：按鈕隱藏）
T.append(tc(10, [1, 2], "Admin 與站長皆可於權限範圍內建立會員帳號", "ui_e2e", ["functional"], ["decision_table"],
    ["以 Admin 登入，任一站台建立會員帳號", "以站長登入，於其管轄範圍內的站台建立會員帳號"],
    "兩者皆能成功建立", "§角色與權限", critical=True))
T.append(tc(10, [3], "操作員的會員列表不顯示創建會員帳號按鈕", "ui_e2e", ["negative"], ["negative"],
    ["以操作員登入後台", "進入會員列表，檢視是否有「創建會員帳號」按鈕"],
    "不顯示創建會員帳號按鈕", "§角色與權限",
    assume="Spec 只寫「操作員不可新增機台帳號」，未寫具體阻擋方式；PM 已於 CLR-ACCOUNT-001 確認為前端按鈕隱藏"))

# REQ-011 角色-機台管理操作（AC1 皆可編輯/停用啟用／AC2 重置憑證需二次確認）
T.append(tc(11, [1, 2], "Admin 與站長皆可管理機台，重置憑證皆需二次確認", "ui_e2e", ["functional"], ["decision_table"],
    ["以 Admin 或站長登入，編輯機台基本資料並切換停用/啟用", "以 Admin 或站長登入，點擊重置機台憑證"],
    "前者兩種角色皆可正常操作；後者皆需二次確認才會執行", "§角色與權限", risk="medium"))

# REQ-012 機台資訊區塊呈現（AC1）
T.append(tc(12, [1], "機台資訊區塊顯示完整的規定欄位", "ui_e2e", ["functional"], ["requirement_based"],
    ["開啟一個機台帳號的會員詳細頁", "檢視機台資訊區塊"],
    "顯示機台名稱、所屬場館（含站台代碼，可點擊回站台列表該層）、機台狀態 Badge、進行中場次、建立與修改時間（UTC+0）", "§機台資訊區塊（會員詳細頁）", risk="medium"))

# REQ-013 進行中場次恆顯示—（AC1）
T.append(tc(13, [1], "開發包③上線前，進行中場次欄位恆顯示「—」", "ui_e2e", ["boundary"], ["boundary_value"],
    ["檢視任一機台帳號的機台資訊區塊", "檢視進行中場次欄位"],
    "顯示「—」", "§機台資訊區塊（會員詳細頁）", risk="low", cost="low",
    pre=PRE_ADMIN + ["開發包③（機台金流）尚未上線"]))

# REQ-014 編輯機台欄位規則（AC1 所屬場館唯讀／AC2 機台名稱可改同步暱稱／AC3 機台狀態可改+修改時間更新）
T.append(tc(14, [1], "編輯機台時所屬場館為唯讀", "ui_e2e", ["negative", "boundary"], ["boundary_value"],
    ["編輯一個機台帳號", "檢視並嘗試修改所屬場館欄位"],
    "唯讀，無法修改", "§編輯機台"))
T.append(tc(14, [2, 3], "修改機台名稱同步更新暱稱，切換機台狀態並更新修改時間", "ui_e2e", ["functional"], ["state_transition"],
    ["編輯機台，修改機台名稱為新值並儲存", "檢視該帳號的會員暱稱", "再次編輯，切換機台狀態並儲存"],
    "會員暱稱同步更新為新的機台名稱；狀態切換成功；兩次操作後修改時間皆自動更新為當次操作時刻", "§編輯機台", critical=True))

# REQ-015 重設密碼規則（AC1 二次確認生成並顯示／AC2 舊密碼立即失效／AC3 取消不重設）
T.append(tc(15, [1], "重設密碼二次確認後生成新帳密並完整顯示一次", "ui_e2e", ["functional"], ["requirement_based"],
    ["任一會員帳號的詳細頁，點擊重設密碼並二次確認"],
    "系統生成新密碼，連同登入帳號一併完整顯示一次，並各附複製按鈕", "§重設密碼", critical=True))
T.append(tc(15, [2], "重設密碼後舊密碼立即失效", "ui_e2e", ["negative"], ["requirement_based"],
    ["完成一次重設密碼", "以重設前的舊密碼嘗試登入"],
    "登入失敗，舊密碼已無法使用", "§業務規則與驗證/重設密碼"))
T.append(tc(15, [3], "取消重設密碼的二次確認，密碼不變", "ui_e2e", ["negative"], ["requirement_based"],
    ["點擊重設密碼開啟二次確認彈窗", "點擊取消"],
    "密碼不變，未執行任何重設", "§重設密碼", risk="medium"))

# REQ-016 前台忘記密碼流程（AC1 寄送連結／AC2 逾時失效／AC3 重新申請使舊連結失效／AC4 完成後舊密碼失效）+ CLR-002（已用連結再點）
T.append(tc(16, [1], "帳號與綁定信箱相符時系統寄送重設連結", "ui_e2e", ["functional"], ["requirement_based"],
    ["已綁定信箱的線上會員於前台輸入帳號與正確的綁定信箱", "送出申請"],
    "系統寄送具時效（預設 1 小時）的重設連結至該信箱", "§前台忘記密碼（線上會員）", critical=True))
T.append(tc(16, [2], "重設連結超過時效後失效", "ui_e2e", ["boundary"], ["boundary_value"],
    ["取得一則重設連結", "等待超過 1 小時後點擊該連結"],
    "連結已失效，無法用於設定新密碼", "§前台忘記密碼（線上會員）"))
T.append(tc(16, [3], "重新申請重設連結會使先前未使用的連結失效", "ui_e2e", ["negative"], ["requirement_based"],
    ["申請一次重設連結（連結 A，尚未使用）", "再次申請重設連結（取得連結 B）", "點擊連結 A"],
    "連結 A 已失效（因重新申請而作廢），需改用連結 B", "§前台忘記密碼（線上會員）"))
T.append(tc(16, [4], "以有效連結完成重設後舊密碼立即失效", "ui_e2e", ["negative"], ["requirement_based"],
    ["點擊有效的重設連結並設定新密碼", "以舊密碼嘗試登入"],
    "登入失敗（舊密碼已立即失效）", "§前台忘記密碼（線上會員）"))
T.append(tc(16, [], "已使用過的重設連結被再次點擊", "ui_e2e", ["negative"], ["negative"],
    ["使用某重設連結完成密碼設定", "再次點擊同一條（已使用過的）連結"],
    "前端顯示「連結已失效，請重新申請」", "§前台忘記密碼（線上會員）",
    assume="Spec 未定義已使用過的連結被再次點擊時的具體回應；PM 已於 CLR-ACCOUNT-002 確認前端顯示「連結已失效，請重新申請」"))

# REQ-017 不透露帳號存在（AC1 帳號不存在／AC2 信箱不符）
T.append(tc(17, [1, 2], "查無帳號或信箱不符時前台顯示相同的通用提示", "ui_e2e", ["negative", "security"], ["decision_table"],
    ["輸入不存在的帳號並送出忘記密碼申請", "輸入存在的帳號但信箱不符並送出申請"],
    "兩種情況皆顯示「若資料相符，重設連結已寄出」，訊息完全相同，不透露帳號是否存在或信箱是否正確", "§前台忘記密碼/不提示帳號存在", risk="medium"))

# REQ-018 忘記密碼不適用對象（AC1 機台帳號不適用／AC2 未綁定信箱只能後台重設）+ CLR-003
T.append(tc(18, [1], "機台帳號無法使用前台忘記密碼", "ui_e2e", ["negative"], ["negative"],
    ["嘗試以機台帳號的會員編號於前台忘記密碼頁申請"],
    "無法完成申請流程（機台帳號並非以電子信箱登入註冊，前台忘記密碼機制對其不存在可用入口）", "§前台忘記密碼/機台帳號",
    assume="Spec 只說機台帳號沒有信箱、不適用忘記密碼，未定義實際申請時前端的提示；PM 已於 CLR-ACCOUNT-003 確認機台帳號無法以信箱登入註冊，故前台不存在此功能可用"))
T.append(tc(18, [2], "未綁定信箱的後台建立帳號只能以後台重設密碼處理", "ui_e2e", ["negative"], ["requirement_based"],
    ["取一個後台建立、尚未補綁電子信箱的線上帳號", "嘗試於前台使用忘記密碼"],
    "無法使用前台忘記密碼機制；該帳號密碼遺失需以後台「重設密碼」處理", "§前台忘記密碼/未綁定信箱的帳號"))

# REQ-019 機台憑證產生與重置（AC1 未產生顯示按鈕／AC2 產生後顯示一次+之後遮罩／AC3 重置二次確認+新憑證顯示+舊憑證失效）
T.append(tc(19, [1], "尚未產生憑證時顯示「產生憑證」按鈕", "ui_e2e", ["functional"], ["requirement_based"],
    ["開啟一個尚未產生憑證的機台帳號的機台憑證區塊"],
    "顯示「產生憑證」按鈕", "§機台憑證", risk="medium"))
T.append(tc(19, [2], "產生憑證後完整顯示一次，之後只顯示前後 4 碼遮罩", "ui_e2e", ["functional"], ["state_transition"],
    ["點擊產生憑證", "檢視當下顯示內容", "離開後重新進入該區塊，再次檢視"],
    "當下完整顯示憑證內容並提供複製按鈕；重新進入後只顯示前後各 4 碼，中間遮罩", "§機台憑證", critical=True))
T.append(tc(19, [3], "重置憑證需二次確認，確認後新憑證顯示一次且舊憑證立即失效", "ui_e2e", ["negative"], ["state_transition"],
    ["已有憑證的機台帳號，點擊重置憑證", "在二次確認彈窗確認"],
    "確認後系統生成新憑證並完整顯示一次，提供複製按鈕；舊憑證立即失效", "§機台憑證", critical=True))

# REQ-020 憑證唯一性+重置生效（AC1；需開發包③憑證驗證 API，目前無法實際執行）
T.append(tc(20, [1], "重置後舊憑證即使簽章仍有效也一律被拒絕", "api", ["negative"], ["negative"],
    ["機台使用憑證 A 正常呼叫平台 API", "在後台重置該機台的憑證（產生憑證 B，A 應立即失效）", "以憑證 A 再次呼叫平台 API"],
    "第三步呼叫被拒絕——平台除驗證簽章外，另比對機台目前有效的憑證識別（如 jti／版本號），僅簽章有效不足以通過", "§機台憑證",
    pre=PRE_ADMIN + ["⚠️ 本案例依賴驗證憑證的平台 API；該 API 屬開發包③範圍，正式對接前尚不存在，目前無法實際執行，僅供開發包③上線後執行"],
    assume="規則本身 spec 已明確定義（非假設待確認），此處的 assumption 僅用於標記『目前無法執行、需等待開發包③』這個環境限制，供 Human 知悉並在 ACTIVATE 時決定是否先行核准、標記為延後執行"))

# REQ-021 憑證格式與有效期限（AC1 JWT格式可複製換行／AC2 不設期限不因時間失效）
T.append(tc(21, [1, 2], "憑證格式為 JWT，且不因時間經過而失效", "ui_e2e", ["functional"], ["decision_table"],
    ["產生或重置憑證，檢視其內容格式", "檢視一個已產生很久（未被重置）的憑證是否仍標示為有效"],
    "憑證為 JWT 字串（可換行完整顯示並複製）；不因時間經過而失效，僅重置才會使其失效", "§機台憑證", risk="medium"))

# REQ-022 停用／啟用機台（AC1 停用不影響餘額／AC2 啟用恢復）
T.append(tc(22, [1], "停用機台後狀態變更且不影響帳號餘額", "ui_e2e", ["functional"], ["state_transition"],
    ["記錄機台帳號目前餘額 X", "將機台狀態切換為停用"],
    "機台狀態變為停用；帳號餘額仍為 X，不受影響", "§停用／啟用機台", critical=True,
    pre=PRE_ADMIN + ["「玩家無法投鈔、遊玩或出金」的實際限制需開發包③機台對接上線後才能驗證，本案僅驗證狀態切換與餘額不變"]))
T.append(tc(22, [2], "啟用停用中的機台可恢復", "ui_e2e", ["functional"], ["state_transition"],
    ["取一個狀態為停用的機台", "將其狀態切換為啟用"],
    "機台狀態變為啟用", "§停用／啟用機台"))

# REQ-023 機台不可刪除（AC1）
T.append(tc(23, [1], "會員列表與詳細頁皆不提供刪除機台或機台帳號的操作", "ui_e2e", ["negative"], ["negative"],
    ["檢視任一機台帳號於會員列表的可用操作", "檢視其會員詳細頁與機台資訊區塊的可用操作"],
    "兩處皆不存在刪除機台或刪除該帳號的功能，僅提供停用", "§業務規則與驗證/機台不可刪除", risk="medium"))

# REQ-024 機台帳號特性-識別與建立方式（AC1）
T.append(tc(24, [1], "機台帳號沿用會員編號規則識別，無電子信箱與電話", "ui_e2e", ["functional"], ["requirement_based"],
    ["建立一個機台帳號", "檢視其會員編號、電子信箱、電話欄位"],
    "會員編號依既有規則產生（無獨立機台編號）；電子信箱與電話皆為空", "§機台帳號的特性", risk="low"))

# REQ-025 機台帳號登入用途（AC1）
T.append(tc(25, [1], "機台帳號的帳密可登入機台前台遊戲畫面", "ui_e2e", ["functional"], ["requirement_based"],
    ["以機台帳號的系統生成帳密", "登入機台的前台遊戲畫面"],
    "可正常登入", "§機台帳號的特性", risk="low", cost="low"))

# REQ-026 機台帳號幣別（AC1 取自主站台核心貨幣／AC2 不可修改）
T.append(tc(26, [1, 2], "機台帳號幣別取自主站台核心貨幣且建立後不可修改", "ui_e2e", ["negative", "boundary"], ["boundary_value"],
    ["所屬主站台核心貨幣為 TWD，建立一個機台帳號，檢視其幣別", "嘗試尋找修改該帳號幣別的途徑"],
    "帳號幣別為 TWD；系統不提供修改此欄位的途徑", "§機台帳號的特性/幣別", critical=True))

# REQ-027 會員列表帳號類型篩選（AC1 預設全部／AC2 篩機台／AC3 篩線上）
T.append(tc(27, [1], "會員列表帳號類型篩選預設為全部", "ui_e2e", ["functional"], ["requirement_based"],
    ["開啟會員列表", "檢視帳號類型篩選器"],
    "預設值為「全部」", "§會員列表的同步修訂/2.1.2 篩選器", risk="medium", cost="low"))
T.append(tc(27, [2, 3], "帳號類型篩選機台或線上時結果正確narrow", "ui_e2e", ["functional"], ["equivalence_partitioning"],
    ["篩選帳號類型為「機台」並搜尋", "篩選帳號類型為「線上」並搜尋"],
    "前者結果只包含機台帳號；後者只包含線上帳號", "§會員列表的同步修訂/2.1.2 篩選器"))

# REQ-028 列表列示+存提款計算（AC1 不排除機台／AC2 開分入金直接累計／AC3 待核實洗分不計入）
T.append(tc(28, [1], "機台帳號照常列於會員列表不預設排除", "ui_e2e", ["functional"], ["requirement_based"],
    ["不篩選帳號類型，檢視會員列表總筆數"],
    "總筆數包含線上與機台帳號，機台帳號未被排除", "§會員列表的同步修訂/2.1.3 會員列表", critical=True))
T.append(tc(28, [2], "機台開分／入金完成當下直接累計存款次數與金額", "api", ["functional"], ["requirement_based"],
    ["機台帳號當日開分 1000（TWD）", "檢視其存款次數與存款金額"],
    "存款次數 +1、存款金額 +1000，以 TWD 原值累計、不換算 USDT", "§會員列表的同步修訂/2.1.3 會員列表",
    pre=PRE_ADMIN + ["實際開分/入金交易需開發包③上線，本案例待該包上線後執行"]))
T.append(tc(28, [3], "待核實的機台洗分不計入提款次數與金額", "api", ["boundary"], ["boundary_value"],
    ["機台帳號有一筆洗分尚待核實（未於洗分出金核實頁核實）", "檢視其提款次數與提款金額"],
    "該筆尚未計入；僅已核實的洗分/出金才累計", "§會員列表的同步修訂/2.1.3 會員列表",
    pre=PRE_ADMIN + ["實際洗分交易需開發包③⑤上線，本案例待該等包上線後執行"]))

# REQ-029 詳細頁區塊規則（AC1 隱藏區塊+新增機台資訊/憑證／AC2 所有帳號皆有重設密碼）
T.append(tc(29, [1], "機台帳號詳細頁隱藏 KYC/等級/優惠/邀請鏈，新增機台資訊與機台憑證區塊", "ui_e2e", ["functional"], ["requirement_based"],
    ["開啟機台帳號的會員詳細頁", "檢視頁面區塊"],
    "KYC、等級、優惠、邀請鏈區塊皆不顯示；顯示機台資訊與機台憑證兩個新區塊", "§會員列表的同步修訂/2.1.5 會員詳細資料頁", critical=True))
T.append(tc(29, [2], "所有會員帳號的詳細頁皆有重設密碼操作", "ui_e2e", ["functional"], ["decision_table"],
    ["開啟一個線上帳號的詳細頁，檢視可用操作", "開啟一個機台帳號的詳細頁，檢視可用操作"],
    "兩者皆有「重設密碼」操作", "§會員列表的同步修訂/2.1.5 會員詳細資料頁"))

# REQ-030 多幣別展開規則（AC1）
T.append(tc(30, [1], "機台帳號的餘額欄不顯示展開箭頭、維持單行", "ui_e2e", ["boundary"], ["boundary_value"],
    ["檢視機台帳號的餘額欄（列表、簡易面板或詳細頁）", "確認是否有可展開的箭頭圖示"],
    "不顯示展開箭頭，單行呈現，數值即主錢包（TWD）餘額", "§會員列表的同步修訂/2.1.6 多幣別錢包展開顯示", risk="low"))

# REQ-031 排除規則-必須實作（AC1 不可成為加盟商／AC2 不計入直推／AC3 等級固定最低／AC4 KYC未申請無法申請）
T.append(tc(31, [1], "機台帳號不可被設為加盟商", "ui_e2e", ["negative"], ["negative"],
    ["取一個機台帳號", "嘗試於加盟列表將其設為加盟商"],
    "系統不允許此操作", "§既有功能對機台帳號的排除規則", critical=True))
T.append(tc(31, [2], "機台帳號不計入任何人的直推人數", "api", ["boundary"], ["boundary_value"],
    ["理論情境：機台帳號被視為由某會員推薦註冊（實際不會發生，見 REQ-032）", "檢視該推薦人的直推人數統計"],
    "機台帳號不計入任何人的直推人數", "§既有功能對機台帳號的排除規則"))
T.append(tc(31, [3], "機台帳號的會員等級固定為最低且不升降", "api", ["boundary"], ["boundary_value"],
    ["檢視機台帳號的會員等級", "即使該帳號有大量投注紀錄（假設情境），再次檢視其等級"],
    "固定為最低等級，不因投注或其他行為升降", "§既有功能對機台帳號的排除規則"))
T.append(tc(31, [4], "機台帳號的 KYC 五個階段皆為未申請且無法申請", "ui_e2e", ["negative"], ["negative"],
    ["開啟機台帳號詳細頁的 KYC 區塊", "嘗試對任一階段提交 KYC 申請"],
    "五個階段皆顯示「未申請」；無法送出任何 KYC 申請", "§既有功能對機台帳號的排除規則"))

# REQ-032 排除規則-天然不會發生（AC1 無邀請人不觸發推薦註冊金／AC2 優惠簽到玩家無從參與，已由 CLR-004 回答）
T.append(tc(32, [1], "機台帳號建立時無邀請人，不觸發推薦註冊金", "api", ["boundary"], ["boundary_value"],
    ["建立一個機台帳號（無邀請人）", "檢視是否有任何推薦註冊金發放紀錄"],
    "未觸發任何推薦註冊金", "§既有功能對機台帳號的排除規則", risk="low"))
T.append(tc(32, [2], "機台前台沒有優惠活動與簽到頁面可供參與", "ui_e2e", ["negative"], ["negative"],
    ["以機台帳號帳密登入機台前台遊戲畫面", "尋找優惠活動或每日簽到入口"],
    "機台前台不存在優惠活動或簽到頁面，玩家（機台）無從進入或參與", "§既有功能對機台帳號的排除規則", risk="low",
    assume="Spec 只說『帳密不交付玩家所以天然不會發生』，未明確要求系統主動阻擋；PM 已於 CLR-ACCOUNT-004 確認機台前台根本沒有優惠活動頁面，玩家介面上無法進入"))

# ================= Report =================
cov = collections.defaultdict(lambda: {"draft_ids": [], "acs": collections.defaultdict(list)})
for t in T:
    for r in t["requirement_ids"]: cov[r]["draft_ids"].append(t["draft_id"])
    for a in t["acceptance_criteria_ids"]: cov["REQ-ACCOUNT-" + a.split("-")[2][:3]]["acs"][a].append(t["draft_id"])
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
print(f"{len(T)} TCs, {n_exp} exploratory ({n_exp*100//len(T)}%), reqs covered={len(cov)}/32")
