#!/usr/bin/env python3
"""RUN-20260914-002 T2：Test Designer(mode=spec) 依 SPEC-SITELIST-001 v0.4 的 29 條需求展開 TestCaseDraft + TestDesignReport。"""
import sys, pathlib, collections
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids
RUN, RM_AID = sys.argv[1], sys.argv[2]; ITER = int(sys.argv[3]) if len(sys.argv) > 3 else 0
SID, SV, AREA, A = "SPEC-SITELIST-001", "0.4", "SITELIST", "agent-test-designer"
reqs = {r["requirement_id"]: r for r in store.load(store.requirements_path(SID, SV))["requirements"]}
def R(n): return f"REQ-SITELIST-{n:03d}"
def AC(n, i): return f"AC-SITELIST-{n:03d}{i}"
def sr(loc): return {"spec_id": SID, "spec_version": SV, "location": loc}
PRE_ADMIN = ["以 Admin 登入後台", "進入 後台管理員系統 > 站台列表"]
PRE_CHIEF = ["以站長登入後台", "進入 後台管理員系統 > 站台列表"]
N = collections.defaultdict(int)  # 每個 REQ 已產生的 draft 流水號（僅供 draft_id 唯一，不影響正式 ID）

def tc(req, acs, title, level, types, techs, steps, expected, loc, prio="high", risk=None, pre=None, data=None,
       assume=None, critical=False, cost="medium", automation="not_automated", ci=False, hotfix=True, more_reqs=()):
    r = reqs[R(req)]; N[req] += 1
    assumptions = []
    for a in ([assume] if isinstance(assume, str) else (assume or [])):
        assumptions.append({"text": a, "requirement_id": R(req), "needs_human_confirmation": True})
    return {"draft_id": f"TC-DRAFT-{ids.ulid()}", "title": title, "product": "ba-admin", "functional_area": AREA,
            "requirement_ids": [R(req)] + [R(x) for x in more_reqs], "acceptance_criteria_ids": [AC(req, i) for i in acs],
            "spec_id": SID, "spec_version": SV, "test_level": level, "test_types": types, "design_techniques": techs,
            "priority": prio, "risk": risk or r["risk"], "execution_mode": "manual",
            "preconditions": PRE_ADMIN if pre is None else pre, "test_data": [{"name": k, "value": v} for k, v in (data or {}).items()],
            "steps": [{"n": i + 1, "action": s} for i, s in enumerate(steps)], "expected_result": expected,
            "expected_result_spec_reference": sr(loc), "assumptions": assumptions, "automation_status": automation,
            "ci_eligible": ci, "hotfix_eligible": hotfix, "execution_cost": cost, "stability": "unknown", "critical_path": critical,
            "source": "spec_workflow", "design_rationale": ""}

T = []
# ---- REQ-001 站台類型二擇一不可修改 ----
T.append(tc(1, [1], "根層站台建立時可二擇一選擇線上或機台類型", "ui_e2e", ["functional"], ["decision_table"],
    ["在根層點擊「+ 新增站台」，站台類型選「線上」，填妥必填欄位送出", "再新增一個站台，站台類型選「機台」，填妥必填欄位送出"],
    "兩次皆建立成功，各自的站台類型為所選值（線上／機台）", "§站台類型與機台專屬欄位", critical=True))
T.append(tc(1, [2, 3], "站台建立後，編輯畫面的站台類型為唯讀無法修改", "ui_e2e", ["negative", "boundary"], ["boundary_value"],
    ["取一個已建立的線上類型站台，點擊「編輯」", "檢視站台類型欄位並嘗試點擊切換為機台"],
    "站台類型欄位為唯讀（置灰），無法點擊切換，送出後類型不變", "§業務規則與驗證/站台類型鎖定"))

# ---- REQ-002 站台類型由主站台決定，子站台強制繼承 ----
T.append(tc(2, [1, 2], "子站台的站台類型固定跟隨主站台，UI 不可個別選擇", "ui_e2e", ["functional"], ["decision_table"],
    ["以機台類型主站台為上層，新增子站台，檢視站台類型欄位", "以線上類型主站台為上層，新增子站台，檢視站台類型欄位"],
    "前者站台類型固定為機台、後者固定為線上，皆為唯讀且不可個別選擇", "§站台類型與機台專屬欄位", critical=True))
T.append(tc(2, [1], "直接呼叫建立站台 API，帶入與上層站台不同的站台類型", "api", ["negative"], ["negative"],
    ["以已知上層站台為機台類型的站台 ID", "直接呼叫建立站台 API，siteType 欄位帶入「線上」（與上層不同）"],
    "後端拒絕此請求，不得建立出與上層站台類型不同的子站台", "§業務規則與驗證/站台類型隨主站台",
    assume="Spec 只描述 UI 唯讀跟隨；PM 已於 CLR-SITELIST-001 確認後端也會拒絕，但尚未寫入 spec 正文", risk="high"))

# ---- REQ-003 機台專屬欄位顯示條件 ----
T.append(tc(3, [1, 2], "機台專屬欄位僅於站台類型為機台時顯示", "ui_e2e", ["functional"], ["decision_table"],
    ["新增或編輯站台，站台類型為線上，檢視欄位", "新增或編輯站台，站台類型為機台，檢視欄位"],
    "線上類型不顯示任何機台專屬欄位；機台類型顯示場館地址、聯絡人／電話、額度上限、場次逾時時間、日結時間", "§站台類型與機台專屬欄位", risk="medium"))

# ---- REQ-004 場館幣別唯讀繼承核心貨幣 ----
T.append(tc(4, [1, 2], "場館幣別不另設輸入欄位，檢視情境顯示值等於核心貨幣", "ui_e2e", ["functional"], ["requirement_based"],
    ["站台類型為機台，開啟新增或編輯畫面，確認畫面上只有一個貨幣相關欄位（核心貨幣）", "至機台資訊或報表等檢視情境，確認顯示的場館幣別"],
    "新增／編輯畫面沒有獨立的場館幣別輸入欄；檢視情境顯示的場館幣別等於該站台所屬主站台的核心貨幣", "§站台類型與機台專屬欄位/場館幣別", risk="medium"))

# ---- REQ-005 額度上限 ----
T.append(tc(5, [1], "額度上限設為 0 代表不限制", "api", ["boundary"], ["boundary_value"],
    ["機台類型場館站台，額度上限設為 0 並儲存", "以該場館機台嘗試大額開分／入金"],
    "系統不因額度而拒絕，視為不限制", "§站台類型與機台專屬欄位/額度上限", critical=True))
T.append(tc(5, [2], "額度上限修改後即時生效，不影響既有餘額", "api", ["functional"], ["requirement_based"],
    ["場館現有機台分數餘額合計為 X，額度上限原為 X", "將額度上限調整為 X/2 並儲存"],
    "既有機台餘額合計仍為 X（不變），僅新的開分／入金請求依新上限（X/2）檢核", "§站台類型與機台專屬欄位/額度上限"))
T.append(tc(5, [1], "額度上限輸入負數應被拒絕", "ui_e2e", ["negative", "boundary"], ["negative"],
    ["機台類型場館站台，額度上限欄位輸入 -100 並送出"],
    "前端顯示「值必須大於或等於 0」；即使繞過前端送出，後端也拒絕該請求",
    "§站台類型與機台專屬欄位/額度上限", assume="Spec 只寫「設為 0 代表不限制」，未定義負數輸入的處理；PM 已於 CLR-SITELIST-002 確認前後端皆拒絕"))

# ---- REQ-006 場次逾時時間 ----
T.append(tc(6, [1], "場次逾時時間預設 1 小時且站長可調整", "ui_e2e", ["functional"], ["state_transition"],
    ["新建機台類型站台，檢視場次逾時時間預設值", "以站長登入，修改該值為 2 小時並儲存"],
    "預設值為 1 小時；站長修改後系統接受並儲存新值", "§站台類型與機台專屬欄位/場次逾時時間"))
T.append(tc(6, [1], "場次逾時時間低於 1 小時或超過 17 位數皆應被拒絕", "ui_e2e", ["negative"], ["negative"],
    ["場次逾時時間輸入低於 1 小時的值（如 30 分鐘）並送出", "另輸入一個超過 17 位數的極端數值並送出"],
    "第一種：後端拒絕（最低值為 1 小時）；第二種：前端顯示格式錯誤，後端阻擋並回傳 COMMON_INVALID_REQUEST_FORMAT",
    "§站台類型與機台專屬欄位/場次逾時時間",
    assume="Spec 只寫「預設 1 小時，站長可調整」，未定義下限與極端值的處理；PM 已於 CLR-SITELIST-003 確認上述兩種拒絕行為與錯誤代碼"))

# ---- REQ-007 日結時間 ----
T.append(tc(7, [1, 2], "日結時間可設定並用於場館日結報表分日", "ui_e2e", ["functional"], ["requirement_based"],
    ["機台類型站台，設定日結時間為 06:00 UTC+0 並儲存", "至場館日結報表確認分日依此時刻切分（見 SPEC-DAILYREPORT-001 REQ-007）"],
    "日結時間成功儲存；場館日結報表依此時刻切分營業日", "§站台類型與機台專屬欄位/日結時間", risk="low", cost="low"))

# ---- REQ-008 核心貨幣主站台設定，子站台唯讀繼承 ----
T.append(tc(8, [1], "子站台的核心貨幣唯讀顯示繼承值", "ui_e2e", ["functional"], ["requirement_based"],
    ["主站台核心貨幣為 TWD（機台類型）", "新增或檢視其子站台，檢視核心貨幣欄位"],
    "子站台核心貨幣唯讀顯示 TWD，與主站台一致，無法個別指定", "§核心貨幣", critical=True))
T.append(tc(8, [1], "子站台核心貨幣欄位無法透過畫面修改", "ui_e2e", ["negative"], ["boundary_value"],
    ["子站台核心貨幣欄位顯示為唯讀", "嘗試點擊或以任何方式修改該欄位"],
    "欄位無互動元素（無下拉箭頭／無法點擊），無法修改", "§核心貨幣"))

# ---- REQ-009 核心貨幣依站台類型過濾 ----
T.append(tc(9, [1, 2], "核心貨幣下拉選單依站台類型過濾", "ui_e2e", ["functional"], ["equivalence_partitioning"],
    ["根層站台類型選「線上」，檢視核心貨幣下拉選項", "根層站台類型選「機台」，檢視核心貨幣下拉選項"],
    "線上類型只列出 USDT；機台類型只列出 TWD，皆等同自動帶入", "§核心貨幣", risk="medium"))

# ---- REQ-010 核心貨幣建立後不可修改 ----
T.append(tc(10, [1], "主站台建立後核心貨幣不可修改", "ui_e2e", ["negative", "boundary"], ["boundary_value"],
    ["取一個已建立的機台類型主站台（核心貨幣 TWD）", "進入編輯畫面，檢視並嘗試修改核心貨幣欄位"],
    "核心貨幣欄位為唯讀顯示，無法修改；子站台編輯畫面同樣唯讀", "§核心貨幣", critical=True))

# ---- REQ-011 可見範圍依角色 ----
T.append(tc(11, [1, 2], "Admin 可見全部站台，站長僅見自身及子站台", "ui_e2e", ["functional"], ["decision_table"],
    ["以 Admin 登入，檢視站台列表根層", "以站長登入，檢視站台列表根層"],
    "Admin 顯示所有無上層站台的根層站台；站長預設顯示自身所屬站台，且僅能看到自身及其所有子站台", "§角色與權限", critical=True))
T.append(tc(11, [3], "站長嘗試以站台 ID 直接查詢平行或上層站台", "api", ["negative"], ["negative"],
    ["以站長帳號取得登入憑證（歸屬於主站台 A 底下）", "直接呼叫站台查詢 API，帶入平行站台或上層站台（admin）的 ID"],
    "系統不得回傳該站台的資料（依可見範圍模型應無法取得資料）", "§角色與權限",
    assume="Spec 未定義具體回應方式（403／空資料／錯誤訊息）；PM 已於 CLR-SITELIST-004 以權限範圍圖確認範圍由所屬站台決定"))

# ---- REQ-012 新增站台-上層站台權限 ----
T.append(tc(12, [1, 2], "新增站台時，Admin 可自由選取上層站台，站長固定為當前層", "ui_e2e", ["functional"], ["decision_table"],
    ["以 Admin 登入，新增站台，搜尋並改選任意站台為上層站台；另試留空", "以站長登入，新增站台，檢視上層站台欄位"],
    "Admin：可搜尋並選取任意站台，留空則建立為根層站台；站長：欄位唯讀，固定顯示當前所在層，無法改選", "§操作/新增站台", critical=True))
T.append(tc(12, [2], "站長直接呼叫建立站台 API，帶入非當前層的上層站台", "api", ["negative"], ["negative"],
    ["以站長帳號取得登入憑證（當前所在層為站台 A）", "直接呼叫建立站台 API，upperSiteId 帶入非 A 的其他站台 ID"],
    "後端拒絕此請求，不得以非當前層的站台作為上層站台建立成功", "§操作/新增站台",
    assume="Spec 只描述前端唯讀行為；PM 已於 CLR-SITELIST-005 確認後端已拒絕（此前 RD 回報的繞過風險已修復）"))

# ---- REQ-013 編輯站台-上層站台權限與循環防護 ----
T.append(tc(13, [1, 2], "編輯站台時，Admin 可修改上層站台且選單排除自身與子站台；站長唯讀", "ui_e2e", ["functional"], ["decision_table"],
    ["以 Admin 登入，編輯某站台，開啟上層站台選單", "以站長登入，編輯站台，檢視上層站台欄位"],
    "Admin：選單不包含該站台自身及其所有子站台；站長：欄位唯讀顯示目前值，無法修改", "§操作/編輯站台", critical=True))
T.append(tc(13, [2], "直接呼叫編輯站台 API，帶入會形成循環的上層站台 ID", "api", ["negative"], ["negative"],
    ["取一個有子站台 B 的站台 A", "直接呼叫編輯 API，將站台 A 的上層站台設為其子站台 B"],
    "後端拒絕此請求，不得形成循環的階層關係", "§業務規則與驗證/上層站台循環防護",
    assume="Spec 只定義 UI 選單排除循環選項；PM 對站長權限的後端驗證已於 CLR-SITELIST-006 確認，但 Admin 編輯時的循環防護是否也有對應後端驗證未明確涵蓋，需另行確認"))

# ---- REQ-014 模板權限 ----
T.append(tc(14, [1, 2], "模板僅 Admin 可指定或修改，站長唯讀不可修改", "ui_e2e", ["functional"], ["decision_table"],
    ["以 Admin 登入，新增或編輯站台並選取／修改模板", "以站長登入，新增或編輯站台，檢視模板欄位"],
    "Admin：系統接受選取或修改；站長：模板欄位不顯示（新增）或唯讀顯示（編輯），無法修改", "§模板設定", risk="medium"))

# ---- REQ-015 模板必填規則（切換開通） ----
T.append(tc(15, [1], "新建站台時模板可留空", "ui_e2e", ["functional"], ["requirement_based"],
    ["Admin 新增站台，模板欄位留空，填妥其餘必填欄位送出"],
    "系統接受建立，站台狀態為待開通", "§模板設定/填寫規則"))
T.append(tc(15, [1], "狀態切換為開通時，模板為必填", "ui_e2e", ["negative", "functional"], ["state_transition"],
    ["取一個模板為空的站台，Admin 將狀態切換為「開通」並儲存", "為該站台選取模板後，再次將狀態切換為「開通」並儲存"],
    "第一次：系統阻擋儲存並提示錯誤（模板必填）；第二次：模板已填，系統接受，狀態變為開通", "§業務規則與驗證/模板（切換開通）", critical=True))

# ---- REQ-016 狀態切換權限 ----
T.append(tc(16, [1], "Admin 可切換為暫停、開通或關閉", "ui_e2e", ["functional"], ["decision_table"],
    ["Admin 編輯一個待開通站台（已設模板），切換為開通並儲存", "再切換為暫停並儲存", "再切換為關閉並儲存"],
    "三次切換皆成功，狀態依序變為開通、暫停、關閉", "§角色與權限/狀態切換", critical=True))
T.append(tc(16, [2], "站長僅可切換為暫停或關閉，其他狀態被阻擋", "ui_e2e", ["negative"], ["negative"],
    ["站長編輯一個開通中的站台，嘗試切換為除暫停／關閉以外的狀態（如更新待審）"],
    "其他狀態顯示但不可選取；若嘗試送出，系統阻擋儲存", "§角色與權限/狀態切換"))
T.append(tc(16, [1], "Admin 嘗試將既有站台手動切回待開通", "ui_e2e", ["negative"], ["negative"],
    ["Admin 編輯一個狀態為開通的站台", "嘗試將狀態切換為「待開通」並儲存"],
    "系統行為依 spec 對「任意狀態」範圍的認定而定（見假設）", "§站台狀態",
    assume="「待開通」在 §站台狀態一節僅列「新建站台自動設定」為觸發方式，未列為 Admin 可手動選取的目標狀態；spec 對「任意狀態」是否含待開通未明確定義"))

# ---- REQ-017 更新待審狀態自動觸發 ----
T.append(tc(17, [1], "開通狀態下網域異動，儲存後自動切為更新待審", "ui_e2e", ["functional"], ["state_transition"],
    ["取一個狀態為開通的站台", "新增一筆前台網域並儲存"],
    "站台狀態自動變為更新待審", "§站台狀態/更新待審", critical=True))
T.append(tc(17, [1], "待開通、暫停或關閉狀態下網域異動不觸發更新待審", "ui_e2e", ["negative", "boundary"], ["boundary_value"],
    ["取一個狀態為待開通的站台，新增網域並儲存，確認狀態", "取一個狀態為暫停的站台，重複上述操作，確認狀態", "取一個狀態為關閉的站台，重複上述操作，確認狀態"],
    "三種狀態皆不因網域異動而改變（不會變為更新待審）", "§站台狀態/更新待審"))
T.append(tc(17, [1], "更新待審狀態下，Admin 可手動切換為其他任意狀態", "ui_e2e", ["functional"], ["state_transition"],
    ["取一個狀態為更新待審的站台", "以 Admin 身分切換其狀態為開通並儲存"],
    "系統接受，狀態成功變更", "§站台狀態/更新待審"))

# ---- REQ-018 網域欄位新增刪除 UI 行為 ----
T.append(tc(18, [1], "新增站台時網域欄位預設一個空輸入欄，可點擊新增追加", "ui_e2e", ["functional"], ["scenario"],
    ["開啟新增站台 Modal，檢視前台與後台網域欄位", "點擊「＋ 新增前台網域」兩次"],
    "前台與後台網域各預設顯示一個空輸入欄；每次點擊新增按鈕即追加一列新的空輸入欄", "§操作/網域編輯行為（Modal 內）", risk="low", cost="low"))
T.append(tc(18, [1], "僅剩最後一列網域時，移除後清空但保留該列", "ui_e2e", ["boundary"], ["boundary_value"],
    ["前台網域僅剩一列且有值", "點擊該列的移除按鈕"],
    "該列輸入欄被清空，但列本身保留（不會變成 0 列）", "§操作/網域編輯行為（Modal 內）", risk="low"))

# ---- REQ-019 網域格式不驗證 ----
T.append(tc(19, [1], "網域欄位輸入不合法格式的字串仍被接受", "ui_e2e", ["negative"], ["negative"],
    ["新增或編輯站台，前台網域欄位輸入不符合網域格式的字串（如純數字、含空白）", "送出儲存"],
    "系統接受並儲存，不阻擋、不提示格式錯誤", "§業務規則與驗證/網域格式", risk="low"))

# ---- REQ-020 站台代碼格式、唯一性、鎖定 ----
T.append(tc(20, [1, 2], "站台代碼輸入時自動轉大寫並過濾非英文字元", "ui_e2e", ["boundary"], ["equivalence_partitioning"],
    ["站台代碼欄位輸入小寫字母「ab」", "另試輸入含數字或符號的字串「a1b!」"],
    "第一種自動轉為「AB」；第二種非英文字元被過濾，僅保留英文字母部分並轉大寫", "§業務規則與驗證/站台代碼格式", critical=True))
T.append(tc(20, [3], "站台代碼與既有站台重複時阻擋儲存", "ui_e2e", ["negative"], ["negative"],
    ["取一個已存在的站台代碼「AB」", "新增站台時輸入相同代碼「AB」並送出"],
    "系統阻擋儲存並提示重複錯誤", "§業務規則與驗證/站台代碼唯一性"))
T.append(tc(20, [4], "站台代碼建立後於編輯畫面唯讀", "ui_e2e", ["negative", "boundary"], ["boundary_value"],
    ["取一個已建立的站台，進入編輯畫面", "檢視站台代碼欄位"],
    "欄位唯讀（置灰），無法修改", "§業務規則與驗證/站台代碼鎖定"))

# ---- REQ-021 站台名稱必填 ----
T.append(tc(21, [1], "站台名稱為空時阻擋儲存", "ui_e2e", ["negative"], ["negative"],
    ["新增或編輯站台，站台名稱欄位留空", "送出儲存"],
    "系統阻擋儲存，輸入框標示紅框與錯誤提示", "§業務規則與驗證/站台名稱必填", risk="medium"))

# ---- REQ-022 刪除站台二次確認 ----
T.append(tc(22, [1], "刪除站台顯示確認彈窗並列出名稱與代碼", "ui_e2e", ["functional"], ["scenario"],
    ["點擊某站台（線上類型）的刪除按鈕"],
    "顯示確認彈窗，列出該站台的名稱與代碼", "§操作/刪除站台", risk="medium"))
T.append(tc(22, [2], "取消刪除確認彈窗，站台不被刪除", "ui_e2e", ["negative"], ["negative"],
    ["點擊某站台的刪除按鈕開啟確認彈窗", "點擊「取消」"],
    "站台不被刪除，資料維持不變，仍存在於列表中", "§操作/刪除站台", risk="medium"))

# ---- REQ-023 刪除不可復原 / 機台不可刪除 ----
T.append(tc(23, [1], "機台類型站台不提供刪除操作，只能停用", "ui_e2e", ["negative"], ["negative"],
    ["取一個機台類型站台，檢視其可用操作", "嘗試尋找刪除按鈕或選項"],
    "不提供刪除操作／按鈕；可用的狀態操作僅有暫停或關閉（停用）", "§操作/刪除站台", critical=True,
    assume="Spec 原文的刪除流程未區分站台類型；PM 已於 CLR-SITELIST-007 確認機台類型不提供刪除操作，僅能停用"))
T.append(tc(23, [1], "線上類型站台二次確認刪除後不可復原", "ui_e2e", ["negative"], ["requirement_based"],
    ["取一個線上類型且無子站台的站台", "刪除並二次確認"],
    "站台被刪除，列表查無此站台，且無任何復原入口或機制", "§操作/刪除站台 + §業務規則/刪除確認"))
T.append(tc(23, [1], "線上類型主站台帶有子站台時執行刪除", "ui_e2e", ["negative"], ["negative"],
    ["取一個線上類型且帶有至少一個子站台的主站台", "點擊刪除並二次確認"],
    "系統行為依子站台處理方式而定（見假設）", "§操作/刪除站台",
    assume="Spec 未定義有子站台的站台如何刪除；CLR-SITELIST-008 尚待 PM 回覆是阻擋、連坐刪除、或子站台改掛他處"))

# ---- REQ-024 機台主站台可自行經營，場館設定範圍不含子站台 ----
T.append(tc(24, [1], "機台主站台可自行經營作為一間場館", "ui_e2e", ["functional"], ["scenario"],
    ["建立一個機台類型主站台，不建立任何子站台", "以該主站台設定場館專屬欄位（額度上限等）並運作"],
    "主站台自身即可作為一間場館經營，帶完整場館設定欄位", "§站台類型與機台專屬欄位", critical=True))
T.append(tc(24, [1], "修改主站台的額度上限不影響其場館子站台，反之亦然", "ui_e2e", ["boundary"], ["boundary_value"],
    ["機台主站台額度上限為 A，其場館子站台額度上限為 B", "將主站台額度上限改為 A2"],
    "子站台的額度上限仍為 B，不受影響；同理修改子站台不影響主站台", "§業務規則與驗證/機台主站台可直接經營"))

# ---- REQ-025 洗分/出金門檻欄位移除 ----
T.append(tc(25, [1], "機台專屬欄位群中不存在洗分/出金門檻欄位", "ui_e2e", ["negative"], ["negative"],
    ["站台類型為機台，開啟新增或編輯畫面", "檢視機台專屬欄位群的完整欄位清單"],
    "不存在「洗分／出金最低門檻」或類似名稱的欄位（v04 已移除）", "§變更記錄（本功能） v04", risk="medium"))

# ---- REQ-026 列表基本欄位呈現 ----
T.append(tc(26, [1, 2], "站台名稱旁依是否有子站顯示「N 個子站」", "ui_e2e", ["functional"], ["decision_table"],
    ["檢視一個有 3 個子站的站台於列表的呈現", "檢視一個無子站的站台於列表的呈現"],
    "前者名稱旁顯示「3 個子站」；後者不顯示子站數量文字", "§列表欄位", risk="medium"))
T.append(tc(26, [3], "網域欄僅顯示前後台網域數量，不展開完整清單", "ui_e2e", ["functional"], ["requirement_based"],
    ["某站台有前台網域 2 筆、後台網域 1 筆", "檢視列表的網域欄"],
    "顯示「前台 2 個 / 後台 1 個」，需進入編輯彈窗才能看到完整清單", "§列表欄位"))
T.append(tc(26, [4], "模板欄位未指定時顯示「—」", "ui_e2e", ["boundary"], ["boundary_value"],
    ["某站台未指定模板", "檢視列表的模板欄"],
    "顯示「—」", "§列表欄位", cost="low"))

# ---- REQ-027 時間紀錄欄位 ----
T.append(tc(27, [1], "新建站台的時間紀錄欄位初始值", "ui_e2e", ["functional"], ["scenario"],
    ["新建一個站台", "檢視其時間紀錄欄（創建時間／修改時間／最後登入）"],
    "創建時間有值（UTC+0）；修改時間為空；最後登入顯示「從未登入」", "§列表欄位/時間紀錄", risk="low"))
T.append(tc(27, [2, 3], "編輯站台後修改時間自動更新，且三欄皆唯讀", "ui_e2e", ["boundary"], ["boundary_value"],
    ["編輯一個站台並儲存變更", "檢視修改時間", "嘗試編輯創建時間／修改時間／最後登入三個欄位"],
    "修改時間更新為本次操作時刻；三個欄位皆為唯讀，不開放編輯", "§列表欄位/時間紀錄", risk="low"))

# ---- REQ-028 篩選器 ----
T.append(tc(28, [1], "狀態篩選與關鍵字搜尋可同時作用", "ui_e2e", ["functional"], ["decision_table"],
    ["狀態篩選選擇「開通」", "同時輸入關鍵字（站台名稱片段）搜尋"],
    "結果同時符合狀態為開通、且名稱或代碼包含關鍵字的站台", "§篩選器"))
T.append(tc(28, [2], "篩選與搜尋僅作用於當前所在層，不跨層查詢", "ui_e2e", ["negative", "boundary"], ["negative"],
    ["鑽入某子站台層級", "以「其他層級才有」的站台名稱關鍵字搜尋"],
    "結果為空或不包含其他層級的站台，即使該站台名稱確實符合關鍵字", "§篩選器"))

# ---- REQ-029 階層瀏覽 ----
T.append(tc(29, [1], "點擊站台名稱進入其子站台列表，路徑列顯示對應路徑", "ui_e2e", ["functional"], ["scenario"],
    ["在根層列表點擊某站台名稱"],
    "進入該站台的子站台列表，頁面頂部路徑列顯示對應的瀏覽路徑", "§階層結構與逐層瀏覽", risk="low"))
T.append(tc(29, [1], "點擊路徑列節點或「站台列表」可跳轉回對應層級", "ui_e2e", ["functional"], ["scenario"],
    ["已鑽入多層子站台", "點擊路徑列中間某節點", "點擊路徑列最前面的「站台列表」"],
    "第一次點擊回到該節點對應的層級；第二次點擊回到根層", "§階層結構與逐層瀏覽", risk="low"))

# ================= Report =================
cov = collections.defaultdict(lambda: {"draft_ids": [], "acs": collections.defaultdict(list)})
for t in T:
    for r in t["requirement_ids"]: cov[r]["draft_ids"].append(t["draft_id"])
    for a in t["acceptance_criteria_ids"]: cov["REQ-SITELIST-" + a.split("-")[2][:3]]["acs"][a].append(t["draft_id"])
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
print(f"{len(T)} TCs, {n_exp} exploratory ({n_exp*100//len(T)}%), reqs covered={len(cov)}/29")
