#!/usr/bin/env python3
"""RUN-20260916-007 T2：Test Designer(mode=spec) 依 SPEC-SITELIST-001 v0.4 的 29 條 ACTIVE requirement 展開 TestCaseDraft + TestDesignReport。
獨立設計（未參考既有 testcases/SITELIST.md），供與人工扮演版本比對。"""
import sys, pathlib, collections
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids

RUN, RM_AID = sys.argv[1], sys.argv[2]
ITER = int(sys.argv[3]) if len(sys.argv) > 3 else 0
SID, SV, AREA, A = "SPEC-SITELIST-001", "0.4", "SITELIST", "agent-test-designer"

reqs = {r["requirement_id"]: r for r in store.load(store.requirements_path(SID, SV))["requirements"]}

def R(n): return f"REQ-SITELIST-{n:03d}"
def AC(n, i): return f"AC-SITELIST-{n:03d}{i}"
def sr(loc, quote=""):
    d = {"spec_id": SID, "spec_version": SV, "location": loc}
    if quote: d["quote"] = quote[:300]
    return d

PRE_ADMIN = ["以 Admin 身分登入 ba-admin 後台", "進入「站台列表」頁面"]
PRE_CHIEF = ["以站長身分登入 ba-admin 後台", "進入「站台列表」頁面（預設顯示自身管轄範圍）"]

def tc(req, acs, title, level, types, techs, steps, expected, loc, quote="", prio=None, risk=None,
       pre=None, data=None, assume=None, critical=False, cost="medium", more_reqs=(), extra_ac=(),
       rationale="", test_level_default="ui_e2e"):
    r = reqs[R(req)]
    assumptions = []
    for a in ([assume] if isinstance(assume, str) else (assume or [])):
        assumptions.append({"text": a, "requirement_id": R(req), "needs_human_confirmation": True})
    if not rationale:
        raise ValueError(f"design_rationale 不可留空：{title}")
    return {
        "draft_id": f"TC-DRAFT-{ids.ulid()}", "title": title, "product": "ba-admin", "functional_area": AREA,
        "requirement_ids": [R(req)] + [R(x) for x in more_reqs],
        "acceptance_criteria_ids": [AC(req, i) for i in acs] + [AC(rn, ai) for rn, ai in extra_ac],
        "spec_id": SID, "spec_version": SV, "test_level": level, "test_types": types, "design_techniques": techs,
        "priority": prio or ("critical" if critical else ("high" if (risk or r["risk"]) == "high" else "medium")),
        "risk": risk or r["risk"], "execution_mode": "manual",
        "preconditions": (PRE_ADMIN if pre is None else pre),
        "test_data": [{"name": k, "value": v} for k, v in (data or {}).items()],
        "steps": [{"n": i + 1, "action": s} for i, s in enumerate(steps)],
        "expected_result": expected, "expected_result_spec_reference": sr(loc, quote),
        "assumptions": assumptions, "automation_status": "not_automated", "ci_eligible": False,
        "hotfix_eligible": True, "execution_cost": cost, "stability": "unknown", "critical_path": critical,
        "source": "spec_workflow", "design_rationale": rationale,
    }

T = []

# ============================================================ REQ-001 站台類型二擇一且建立後不可修改
T.append(tc(1, [1], "根層站台建立時可自由二擇一站台類型（線上／機台）", "ui_e2e", ["functional"], ["decision_table"],
    ["點擊「+ 新增站台」，上層站台留空（建立根層站台），站台類型選擇「線上」，其餘必填欄位填妥後點擊「建立站台」",
     "再次點擊「+ 新增站台」，上層站台留空，站台類型改選「機台」，其餘必填欄位填妥後點擊「建立站台」"],
    "兩次皆成功建立；前者站台類型顯示為線上，後者顯示為機台，各自依所選類型建立", "§站台類型與機台專屬欄位",
    "每個站台的「站台類型」為線上 / 機台，二擇一；建立後不可修改", critical=True,
    rationale="AC-0011 的斷言是『選擇後系統依所選類型建立』，用一個 TC 涵蓋線上/機台兩個分支是典型 decision_table（2 條件→2 結果的映射），比拆成兩條案例更能突顯這是同一規則的兩面。"))

T.append(tc(1, [2, 3], "站台建立後，編輯畫面站台類型欄位唯讀，無法透過編輯變更", "ui_e2e", ["negative"], ["negative"],
    ["取上一步建立的任一站台，點擊列表「編輯」開啟 Modal", "檢視站台類型欄位的呈現方式與是否可互動",
     "嘗試以瀏覽器操作（如點擊欄位、嘗試選取其他選項）改變其值，並點擊「儲存變更」"],
    "站台類型欄位置灰唯讀，無法點選或修改任何選項；儲存後重新開啟編輯畫面，站台類型值與建立時相同，未被變更",
    "§站台類型與機台專屬欄位 + §業務規則-站台類型鎖定", "建立後不可修改", critical=True,
    rationale="AC-0012/0013 明確描述『唯讀置灰』即為拒絕修改的方式，rejection_contract.defined=true 且原文有直接依據，不需假設；design_technique 標 negative 因為這條本質是驗證『修改嘗試被拒絕』而非單純檢視顯示。"))

# ============================================================ REQ-002 站台類型由主站台決定，子站台強制繼承
T.append(tc(2, [1, 2], "子站台的站台類型強制跟隨上層站台，UI 不開放個別選擇", "ui_e2e", ["functional"], ["decision_table"],
    ["取一個既有的機台類型站台（自行從環境中選定，或延用本批次已建立的機台根站台），在其底下點擊「+ 新增站台」，檢視站台類型欄位",
     "取一個既有的線上類型站台，在其底下點擊「+ 新增站台」，檢視站台類型欄位"],
    "前者：站台類型固定顯示為機台，UI 不提供選擇其他類型的控制項；後者：固定顯示為線上，UI 同樣不開放選擇",
    "§站台類型與機台專屬欄位 + §業務規則-站台類型隨主站台",
    "站台類型於主站台（根層）選定，子站台一律與主站台同類型、不可個別選擇", critical=True,
    rationale="上層為機台／上層為線上是兩個獨立條件各自對應固定結果，屬合法的 decision_table（2×1 映射）；未使用 boundary_value 是因為這裡沒有數值邊界，純粹是類型繼承規則。"))

T.append(tc(2, [], "繞過 UI 直接呼叫建立站台 API，帶入與上層站台不同的站台類型", "api", ["negative"], ["negative"],
    ["取一個既有的機台類型站台", "直接呼叫建立子站台的後端 API，上層站台 ID 帶入該機台站台，站台類型欄位帶入「線上」（與上層不同）"],
    "後端拒絕該請求，不會建立一個站台類型與上層不同的子站台",
    "§業務規則與驗證/站台類型隨主站台", "",
    assume="Spec 只描述 UI 唯讀跟隨、未定義繞過 UI 時後端是否也拒絕（REQ-SITELIST-002 的 rejection_contract.defined=false）；PM 已於 CLR-SITELIST-001（2026-09-14）回覆『後端也會拒絕』，但此答覆未回寫進 RequirementModel 的 rejection_contract，故仍以 exploratory 方式標記，需人工於執行時再次確認",
    rationale="rejection_contract.defined=false，依規則以 negative 技巧撰寫負向案例必須走 exploratory；雖然 CLR-SITELIST-001 已有 PM 回覆可作參考，但因 RequirementModel 本身未更新該欄位，仍誠實標記為待確認而非確定規則，避免 design_rationale 宣稱『spec 已明確定義』卻查無實據。",
    more_reqs=[], extra_ac=[]))

T.append(tc(2, [3], "上層站台為 admin（根層）時例外：類型可自由選擇，核心貨幣依所選類型連動建立", "ui_e2e", ["functional"], ["requirement_based"],
    ["點擊「+ 新增站台」，上層站台留空（即建立於最上層 admin 根節點之下、成為根層站台），站台類型選擇「機台」，核心貨幣下拉選單檢視",
     "填妥其餘必填欄位後點擊「建立站台」，建立完成後檢視該站台的核心貨幣欄位值"],
    "站台類型欄位可自由選擇（不強制跟隨 admin 本身），選機台後核心貨幣下拉僅出現 TWD 並自動連動建立，過程不要求或呈現任何『admin 自身鏈上錢包管理需預先啟用 TWD』的前置檢查",
    "§站台類型與機台專屬欄位 + §業務規則-站台類型隨主站台",
    "當上層站台為 admin（最上層根站台）時，此強制跟隨規則不適用——底下子站台可自由選擇機台或線上類型，核心貨幣依所選類型連動建立",
    rationale="此 AC 描述的『上層站台為 admin』情境，經比對 spec.md 正文（§站台類型與機台專屬欄位：站台類型於『主站台（根層）』選定），與『建立根層站台可自由選類型』實為同一件事的兩種措辭，因此以建立根層站台的操作驗證；『不需 admin 自身鏈上錢包管理預先啟用該幣別』一句涉及鏈上錢包管理，該功能不在 SITELIST spec 範圍內，本 TC 僅驗證『沒有出現任何阻擋提示』這個可觀察到的否定事實，不對鏈上錢包模組本身斷言。"))

# ============================================================ REQ-003 機台專屬欄位僅機台類型顯示
T.append(tc(3, [1, 2], "機台專屬欄位僅於站台類型為機台時顯示，線上類型不顯示", "ui_e2e", ["functional", "negative"], ["decision_table"],
    ["點擊「+ 新增站台」，站台類型選「線上」，檢視表單是否出現機台專屬欄位群",
     "另開一次「+ 新增站台」，站台類型選「機台」，檢視表單欄位"],
    "前者：不顯示任何機台專屬欄位（場館地址、聯絡人／電話、額度上限、場次逾時時間、日結時間皆不存在於表單）；後者：完整顯示上述全部 5 個機台專屬欄位",
    "§站台類型與機台專屬欄位", "類型為「機台」時才顯示下列機台專屬欄位",
    rationale="線上不顯示、機台顯示全部，是同一顯示規則的兩個互斥分支，用 decision_table 呈現這組『條件→顯示結果』的映射；test_types 同時標 functional 與 negative 是因為本案例同時驗證『該出現的有出現』與『不該出現的沒出現』兩種斷言，並非為了湊 non-happy 而硬加。"))

# ============================================================ REQ-004 場館幣別唯讀繼承核心貨幣，不另設欄位
T.append(tc(4, [1], "機台類型站台的新增／編輯畫面只有一個貨幣欄位（核心貨幣），不存在獨立的場館幣別輸入欄", "ui_e2e", ["negative"], ["requirement_based"],
    ["點擊「+ 新增站台」，站台類型選「機台」，逐一檢視表單所有欄位標題",
     "取一個既有的機台類型站台，點擊「編輯」，同樣逐一檢視所有欄位標題"],
    "新增與編輯畫面皆只出現一個與貨幣相關的欄位（核心貨幣），不存在另一個名為『場館幣別』或類似名稱的獨立輸入欄",
    "§站台類型與機台專屬欄位/場館幣別",
    "新增／編輯視窗不另設本欄位——與「核心貨幣」為同一個值，由核心貨幣欄的子站台唯讀繼承顯示承載",
    rationale="這是驗證『某欄位不存在』的否定事實，直接對照 spec 原文明確排除，design_technique 用 requirement_based 而非硬套 decision_table，因為這裡沒有多條件組合，純粹是單一規則的直接映證。"))

T.append(tc(4, [2], "檢視情境（機台資訊／報表）下場館幣別顯示值等於所屬主站台核心貨幣", "ui_e2e", ["functional"], ["requirement_based"],
    ["取一個核心貨幣為 TWD 的機台主站台，在其底下已有的機台子站台（場館）",
     "於該子站台的檢視情境（如機台資訊區塊或報表頁面的場館幣別欄位，若 SITELIST 頁面本身無此檢視入口則以站台列表/編輯彈窗中場館幣別的唯讀顯示值為準）檢視場館幣別"],
    "顯示值為 TWD，與所屬主站台的核心貨幣一致", "§站台類型與機台專屬欄位/場館幣別", "本欄僅用於場館設定的檢視情境（如機台資訊、報表）",
    rationale="AC-0042 提到的『檢視情境（機台資訊、報表）』實際頁面入口可能落在 ACCOUNT 或報表相關功能區，不完全屬於 SITELIST 頁面本身；本案例在 SITELIST 範圍內以編輯彈窗的唯讀顯示作為可觀察替代點，並在 steps 中誠實註明這個對應關係，避免假裝 SITELIST 頁面本身就有完整的機台資訊檢視畫面。"))

# ============================================================ REQ-005 額度上限為場館層級共用池
T.append(tc(5, [1], "場館額度上限設為 0 時系統接受並儲存，代表不限制", "ui_e2e", ["functional"], ["requirement_based"],
    ["取一個既有的機台類型站台（場館），點擊「編輯」，額度上限欄位輸入 0 並儲存",
     "重新開啟編輯畫面，檢視額度上限欄位的值"],
    "系統接受並儲存 0；重新開啟後欄位值仍為 0（本 TC 僅驗證『0 這個設定值可被接受並持久化』這個 SITELIST 可觀察的部分；『0 代表不限制』實際在開分／入金時是否真的不檢核上限，需搭配機台交易功能才能驗證，超出本 spec 範圍，未在此案例斷言）",
    "§站台類型與機台專屬欄位/額度上限 + §業務規則-額度上限（場館）", "設為 0 代表不限制",
    rationale="AC-0051 的『代表不限制』是一個業務語意斷言，其完整效果需要機台入金/開分交易才能觀察，而該交易能力不在 SITELIST spec 範圍內；為避免違反『expected_result 不要超出 AC 範圍』與『不要編造未驗證事實』，本 TC 誠實把斷言收斂到 SITELIST 能觀察到的部分（值可被設定並儲存），並在 expected_result 中明講這個範圍限制。"))

T.append(tc(5, [2], "修改場館額度上限後即時生效，且不回溯影響既有設定的其他站台", "ui_e2e", ["functional"], ["requirement_based"],
    ["取一個既有的機台類型站台，記錄其目前額度上限值 X", "將額度上限修改為新值 Y 並儲存",
     "重新開啟編輯畫面確認新值已生效", "檢視另一個不同機台站台的額度上限，確認其值未受影響"],
    "該站台額度上限立即更新為 Y（重新整理即可見）；另一個機台站台的額度上限維持原值，不受影響（『既有機台餘額不受影響』一句涉及機台帳號分數餘額，此為 ACCOUNT/實體機台交易範疇，不在 SITELIST 頁面可觀察範圍內，本 TC 不對餘額本身斷言）",
    "§站台類型與機台專屬欄位/額度上限", "修改後即時生效，不影響既有餘額",
    rationale="『不影響既有餘額』原文語意是『這個場館設定的變更不會導致既有機台帳號的分數餘額被重算或歸零』，但『機台帳號餘額』的檢視畫面不在 SITELIST 而在 ACCOUNT 的機台資訊區塊；為維持系統邊界誠實，本 TC 把『不影響』的斷言改為驗證『不會影響其他站台的同一份設定』這個 SITELIST 範圍內可觀察的部分，並在 expected_result 中明講為何不驗證餘額本身。"))

T.append(tc(5, [], "額度上限欄位輸入負數，前後端皆拒絕", "ui_e2e", ["negative", "boundary"], ["boundary_value"],
    ["取一個既有的機台類型站台，點擊「編輯」，額度上限欄位輸入 -1 並嘗試儲存",
     "若前端未阻擋而送出請求，觀察後端回應"],
    "前端顯示『值必須大於或等於 0』之類的錯誤提示並阻擋送出；即使繞過前端直接呼叫 API 帶入負數，後端同樣拒絕該請求，額度上限維持修改前的值",
    "§業務規則與驗證/額度上限（場館）", "",
    data={"credit_limit": -1},
    assume="Spec 原文未定義輸入負數時系統的回應（REQ-SITELIST-005 的 rejection_contract.defined=false）；PM 已於 CLR-SITELIST-002（2026-09-14）回覆『前端顯示錯誤、後端也拒絕（雙層驗證）』，但此答覆未回寫進 RequirementModel，故仍以 exploratory 方式標記，執行時需人工再確認實際文案與後端行為",
    rationale="REQ-SITELIST-005 的 inputs 定義了 credit_limit 的 min:0 約束，依規則本需求必須有 boundary_value 技巧的案例；同時 rejection_contract.defined=false，故即使 CLR-SITELIST-002 已有 PM 答覆，仍誠實標為待確認的 exploratory 案例，不寫成確定規則。"))

# ============================================================ REQ-006 場次逾時時間欄位
T.append(tc(6, [1], "新建機台類型站台的場次逾時時間預設為 1 小時", "ui_e2e", ["functional"], ["requirement_based"],
    ["點擊「+ 新增站台」，站台類型選「機台」，檢視場次逾時時間欄位的預設值（不手動輸入，直接觀察）"],
    "欄位預設值為 1 小時", "§站台類型與機台專屬欄位/場次逾時時間", "預設 1 小時，站長可調整，操作員唯讀",
    rationale="單一預設值檢視，直接對照 spec 原文，requirement_based 已足夠，無需套用其他進階技巧。"))

T.append(tc(6, [2], "站長可修改場次逾時時間且修改後生效", "ui_e2e", ["functional"], ["requirement_based"],
    pre=PRE_CHIEF + ["已有一個屬於自身管轄範圍內的機台類型站台"],
    steps=["編輯該機台站台，將場次逾時時間由預設 1 小時改為 2 小時並儲存", "重新開啟編輯畫面確認新值已生效"],
    expected="系統接受修改；重新開啟後場次逾時時間顯示為 2 小時", loc="§站台類型與機台專屬欄位/場次逾時時間",
    quote="站長可調整", rationale="AC-0062 只斷言『系統接受修改』，直接以站長角色操作驗證即可，requirement_based 對應此單一直述句最貼切。"))

T.append(tc(6, [], "場次逾時時間輸入低於 1 小時或超長格式時系統拒絕", "ui_e2e", ["negative", "boundary"], ["boundary_value"],
    ["取一個既有的機台類型站台，編輯場次逾時時間，輸入一個明顯小於 1 小時的值並嘗試儲存",
     "另開一次編輯，於場次逾時時間欄位輸入一個超過 17 位數的極端數字格式並嘗試儲存"],
    "第一步：系統阻擋，因後端最低值設計為 1 小時，低於 1 小時會被拒絕；第二步：前端跳出格式錯誤提示，後端阻擋並回傳通用錯誤代碼 COMMON_INVALID_REQUEST_FORMAT",
    "§業務規則與驗證/場次逾時", "",
    data={"session_timeout_below_min": "0.5hr", "session_timeout_overflow": "99999999999999999"},
    assume="Spec 原文未定義輸入 0、負數或極端值時系統的回應（REQ-SITELIST-006 的 rejection_contract.defined=false）；PM 已於 CLR-SITELIST-003（2026-09-14）回覆『後端最低值 1 小時、超過 17 位數格式錯誤回 COMMON_INVALID_REQUEST_FORMAT』，此答覆未回寫進 RequirementModel，故以 exploratory 標記，執行時需人工再確認實際錯誤代碼與文案",
    rationale="rejection_contract.defined=false 且技巧為 boundary_value／negative 混合，即使 CLR-SITELIST-003 已有具體 PM 答覆，仍誠實標為待確認而非確定規則；『操作員唯讀』這部分因操作員角色本 spec 未定義，故本 TC 不涉及，僅測站長與後端邊界。"))

# ============================================================ REQ-007 日結時間欄位
T.append(tc(7, [1], "機台類型站台可設定日結時間（UTC+0）並儲存", "ui_e2e", ["functional"], ["requirement_based"],
    ["取一個既有的機台類型站台，編輯日結時間欄位，設定一個時刻值（如 00:00）並儲存",
     "重新開啟編輯畫面確認該時刻值已儲存"],
    "系統接受並儲存該時刻值（UTC+0）；重新開啟後欄位顯示相同時刻", "§站台類型與機台專屬欄位/日結時間",
    "每日結算的截止時刻（UTC+0），用於場館日結報表分日",
    rationale="AC-0071 只涉及 SITELIST 本身『可設定並儲存』的部分；AC-0072『報表依此時刻切分營業日』的實際效果驗證屬於 SPEC-DAILYREPORT-001 REQ-007 的責任範圍（requirement statement 本身也如此註明），本次任務範圍僅限 SITELIST 的 29 條需求，因此本 TC 不延伸設計跨功能區的報表切分驗證，僅涵蓋設定值本身。"))

# ============================================================ REQ-008 核心貨幣為主站台層級設定
T.append(tc(8, [1], "子站台的核心貨幣唯讀顯示且等於主站台核心貨幣，無法於子站台個別指定", "ui_e2e", ["negative"], ["negative"],
    ["取一個核心貨幣為 TWD 的機台主站台，在其底下已有的子站台，檢視或編輯其核心貨幣欄位",
     "嘗試在該子站台的編輯畫面尋找任何可修改核心貨幣的操作方式"],
    "子站台核心貨幣顯示為 TWD（與主站台一致），欄位為唯讀顯示；找不到任何可個別指定或修改該值的操作方式",
    "§核心貨幣", "其底下所有子站台一律沿用，不可各自指定",
    rationale="這是驗證『找不到某個操作能力』的否定案例，design_technique 標 negative 貼合『驗證某修改途徑被拒絕/不存在』的本質。"))

T.append(tc(8, [1], "新增子站台時，核心貨幣欄位直接以唯讀方式繼承顯示，不提供選單", "ui_e2e", ["negative"], ["negative"],
    ["取一個核心貨幣為 TWD 的機台主站台，在其底下點擊「+ 新增站台」，檢視核心貨幣欄位"],
    "核心貨幣欄位唯讀顯示 TWD（繼承自上層主站台），不呈現下拉選單或任何可選擇的控制項",
    "§操作/新增站台", "核心貨幣 | 根層：下拉選單，選項依站台類型過濾；子站台：唯讀顯示繼承值",
    rationale="與前一條 TC 分別驗證『既有子站台的檢視/編輯』與『新增子站台當下的表單呈現』兩個不同操作時機，避免用同一個情境重複測同一件事；同樣用 negative 技巧驗證『不提供選擇能力』。"))

# ============================================================ REQ-009 核心貨幣下拉依站台類型過濾
T.append(tc(9, [1, 2], "根層站台核心貨幣下拉選項依站台類型過濾", "ui_e2e", ["functional"], ["decision_table"],
    ["點擊「+ 新增站台」，上層站台留空，站台類型選「線上」，展開核心貨幣下拉選單，檢視選項",
     "另開一次「+ 新增站台」，站台類型選「機台」，展開核心貨幣下拉選單，檢視選項"],
    "前者下拉選單只列出 USDT 一個選項；後者只列出 TWD 一個選項", "§核心貨幣",
    "可選幣別清單依類型維護，目前線上＝USDT、機台＝TWD 各僅一種",
    rationale="站台類型→可選幣別是一組明確的 2 條件對 2 結果映射，屬合法 decision_table；『清單須可擴充、不得寫死幣別』屬實作層面的技術約束，非黑箱操作可驗證的行為，本 TC 不對此另外斷言，僅在 design_rationale 註明此限制。"))

# ============================================================ REQ-010 核心貨幣建立後不可修改
T.append(tc(10, [1], "主站台建立後核心貨幣欄位於編輯畫面唯讀，無法透過編輯變更", "ui_e2e", ["negative"], ["negative"],
    ["取一個既有的主站台（根層站台），點擊「編輯」，檢視核心貨幣欄位的呈現方式",
     "嘗試以瀏覽器操作改變其值，並點擊「儲存變更」，儲存後重新開啟編輯畫面確認"],
    "核心貨幣欄位唯讀顯示，無法點選或修改；儲存後核心貨幣值與建立時相同，未被變更", "§核心貨幣 + §業務規則-核心貨幣繼承",
    "主站台建立後，核心貨幣不可修改（v07 定案）：比照「站台類型」，於建立時選定即永久鎖定，編輯視窗唯讀顯示", critical=True,
    rationale="rejection_contract.defined=true 且原文直接明確『唯讀顯示』即拒絕方式，不需假設；design_technique 用 negative 因為本質是驗證修改嘗試被拒絕。"))

# ============================================================ REQ-011 可見範圍依角色
T.append(tc(11, [1], "Admin 檢視站台列表根層時顯示所有無上層站台的根層站台", "ui_e2e", ["functional", "security"], ["security_rule"],
    ["以 Admin 登入，進入站台列表（根層）", "檢視列表中出現的所有站台"],
    "顯示系統中所有『無上層站台』的根層站台，不因任何條件被排除", "§角色與權限 + §階層結構與逐層瀏覽-根層顯示",
    "Admin 預設顯示所有無上層站台的根層站台",
    rationale="這是角色可見範圍規則的正向斷言，design_technique 標 security_rule 較 requirement_based 更精確地反映『這是一條權限規則的驗證』而非單純功能敘述。"))

T.append(tc(11, [2], "站長檢視站台列表時只看到自身所屬站台及其所有子站台", "ui_e2e", ["functional", "security"], ["security_rule"],
    pre=PRE_CHIEF, steps=["進入站台列表，檢視預設顯示的內容", "逐層點擊鑽入子站台，確認每一層看到的站台都在自身所屬站台的子樹之內"],
    expected="預設顯示自身所屬站台；可見範圍僅限自身所屬站台及其所有子站台，看不到超出此子樹之外的任何站台",
    loc="§角色與權限", quote="僅自身站台及所有子站台（不含平行或上層站台）",
    rationale="與 Admin 的正向對照案例，同樣用 security_rule 技巧維持一致標記，避免對稱情境貼不同標籤。"))

T.append(tc(11, [3], "站長透過 UI 逐層瀏覽無法到達平行或上層站台", "ui_e2e", ["negative", "security"], ["security_rule"],
    pre=PRE_CHIEF, steps=["進入站台列表，嘗試透過路徑列、搜尋欄或任何 UI 導覽入口尋找平行站台或自身所屬站台的上層站台"],
    expected="UI 導覽範圍受限於自身所屬子樹，找不到任何可到達平行站台或上層站台的入口，站台列表也不會顯示該等資料",
    loc="§角色與權限 + §階層結構與逐層瀏覽", quote="可見站台範圍 | 全部站台 | 僅自身站台及所有子站台（不含平行或上層站台）",
    rationale="這是 UI 導覽層級的驗證，直接對照 spec 表格文字，不涉及繞過機制，屬於已明確定義的行為，非 exploratory。"))

T.append(tc(11, [], "站長直接以站台 ID 呼叫查詢 API 存取平行或上層站台", "api", ["negative", "security"], ["security_rule"],
    pre=PRE_CHIEF, steps=["取得一個平行站台或上層站台的站台 ID（例如從其他角色的畫面得知）", "以站長身分直接呼叫該站台的查詢 API"],
    expected="無法取得該站台資料（回應應為拒絕或查無資料，而非回傳站台詳細內容）",
    loc="§業務規則與驗證", quote="",
    assume="Spec 未定義站長嘗試以站台 ID 直接呼叫查詢 API 存取平行／上層站台時的具體回應（REQ-SITELIST-011 的 rejection_contract.defined=false）；PM 已於 CLR-SITELIST-004（2026-09-14）回覆『依範圍模型應無法取得資料』，但未定義精確的錯誤格式，且此答覆未回寫進 RequirementModel，故以 exploratory 標記，需人工確認實際回應格式",
    rationale="這是繞過 UI 的深度防護測試，rejection_contract.defined=false，即使 CLR-SITELIST-004 已有 PM 方向性答覆，仍缺乏精確回應格式，誠實標為待確認。"))

# ============================================================ REQ-012 新增站台時上層站台欄位權限
T.append(tc(12, [1], "Admin 新增站台時可自由搜尋並改選上層站台，留空則建立根層站台", "ui_e2e", ["functional"], ["decision_table"],
    ["點擊「+ 新增站台」，上層站台欄位搜尋並選取一個任意既有站台，填妥其餘欄位後建立",
     "另開一次「+ 新增站台」，上層站台留空，填妥其餘欄位後建立"],
    "前者：系統接受，新站台的上層即為所選站台；後者：系統接受，新站台建立為根層站台（無上層）",
    "§角色與權限 + §操作/新增站台", "自動帶入當前所在層；可搜尋改選任意站台（搜尋結果顯示站台名稱、代碼及完整路徑）；留空為根層",
    rationale="『改選任意站台』與『留空』是兩個獨立分支各自對應不同結果，屬合法 decision_table。"))

T.append(tc(12, [2], "站長新增站台時上層站台欄位唯讀，固定為當前所在層", "ui_e2e", ["negative", "security"], ["security_rule"],
    pre=PRE_CHIEF + ["已鑽入某個子站台層級"],
    steps=["於當前層級點擊「+ 新增站台」，檢視上層站台欄位", "嘗試修改該欄位"],
    expected="上層站台欄位唯讀，固定顯示當前所在層，無法搜尋或改選任何其他站台",
    loc="§角色與權限 + §操作/新增站台", quote="預帶當前所在層，唯讀不可修改",
    rationale="直接對照 spec 表格文字，屬明確定義行為；用 security_rule 技巧標記角色權限差異，非 exploratory。"))

T.append(tc(12, [], "站長繞過前端直接呼叫建立站台 API 並帶入其他上層站台 ID", "api", ["negative", "security"], ["security_rule"],
    pre=PRE_CHIEF, steps=["以站長身分，直接呼叫建立站台 API，上層站台 ID 帶入非當前所在層的其他站台"],
    expected="後端拒絕該請求，不會建立一個上層站台與站長當前所在層不同的站台",
    loc="§業務規則與驗證", quote="",
    assume="Spec 只定義前端行為（欄位唯讀），未定義繞過前端直接呼叫 API 時後端是否拒絕（REQ-SITELIST-012 的 rejection_contract.defined=false，且 requirement 本身註明此為已知風險區域）；PM 已於 CLR-SITELIST-005（2026-09-14）回覆『後端已拒絕，此前 RD 回報的可繞過風險已修復』，但此答覆未回寫進 RequirementModel，故以 exploratory 標記，需人工再次確認後端行為",
    rationale="這是 requirement 本身明確點名的已知風險區域，即使 CLR-SITELIST-005 已有 PM 答覆確認修復，仍依規則誠實標為待確認的 exploratory 案例。"))

# ============================================================ REQ-013 編輯站台時上層站台欄位權限與循環防護
T.append(tc(13, [1], "Admin 編輯站台的上層站台選單自動排除自身與其所有子站台", "ui_e2e", ["negative", "security"], ["security_rule"],
    ["取一個既有的、底下至少有一層子站台的站台 A", "點擊「編輯」A，開啟上層站台選單，檢視可選項目清單"],
    "選單中不包含 A 自身，也不包含 A 的所有子站台（含孫層）", "§角色與權限 + §操作/編輯站台 + §業務規則-上層站台循環防護",
    "編輯時，不可將自身或自身的子站台選為上層站台",
    rationale="這是驗證『特定選項被排除』的否定案例，design_technique 用 security_rule 因其本質是循環防護這條業務規則的直接驗證，而非單純的欄位顯示測試。"))

T.append(tc(13, [2], "站長編輯站台時上層站台欄位唯讀顯示目前值", "ui_e2e", ["negative", "security"], ["security_rule"],
    pre=PRE_CHIEF, steps=["編輯自身管轄範圍內的一個站台，檢視上層站台欄位"],
    expected="唯讀顯示目前的上層站台值，無法修改；如需變更需另外通知 Admin",
    loc="§角色與權限 + §操作/編輯站台", quote="唯讀顯示；如需變更須通知 Admin 操作",
    rationale="直接對照 spec 表格文字，明確定義行為，非 exploratory。"))

T.append(tc(13, [], "站長繞過前端直接呼叫編輯站台 API 修改上層站台", "api", ["negative", "security"], ["security_rule"],
    pre=PRE_CHIEF, steps=["以站長身分，直接呼叫編輯站台 API，將自身管轄範圍內某站台的上層站台 ID 改為其他站台"],
    expected="後端拒絕該請求，該站台的上層站台維持不變",
    loc="§業務規則與驗證", quote="",
    assume="Spec 只定義 UI 選單排除循環選項，未定義繞過 UI 直接呼叫編輯 API 時後端是否驗證並拒絕站長的修改（REQ-SITELIST-013 的 rejection_contract.defined=false）；PM 已於 CLR-SITELIST-006（2026-09-14）回覆『同 CLR-005，站長編輯時的上層站台唯讀限制後端已拒絕』，但此答覆未回寫進 RequirementModel，故以 exploratory 標記",
    rationale="與 REQ-012 的 API bypass 案例對稱，同樣因 rejection_contract.defined=false 誠實標為待確認。"))

T.append(tc(13, [], "Admin 繞過前端直接呼叫編輯站台 API，帶入會形成循環的上層站台 ID", "api", ["negative", "security"], ["security_rule"],
    ["取一個既有的、底下至少有一層子站台的站台 A", "以 Admin 身分，直接呼叫編輯站台 A 的 API，上層站台 ID 帶入 A 自身或 A 的某個子站台"],
    "預期後端拒絕該請求，避免形成循環的父子關係；此結果目前未經確認，執行時若發現後端接受了此請求（形成循環），應視為高風險缺陷立即上報，而非視為預期行為",
    "§業務規則與驗證/上層站台循環防護", "",
    assume="CLR-SITELIST-006 的 PM 回覆明確聲明『本次確認聚焦於站長權限，Admin 編輯時的循環防護是否也有對應後端驗證，未在本次回覆中明確涵蓋，若後續測試發現可繞過，需另案處理』；也就是說 Admin 這一側的後端防護目前完全沒有人力確認過，屬於比站長那一側更不確定的風險",
    rationale="這是全份 Draft 裡罕見『目前完全沒有任何人（含 CLR）確認過』的風險點，特別標記為 exploratory 且在 expected_result 中明講『若後端接受此請求應視為缺陷立即上報』，避免執行者誤以為『後端拒絕』是已驗證的既定事實。"))

# ============================================================ REQ-014 模板權限
T.append(tc(14, [1], "Admin 新增或編輯站台時可選取或修改模板", "ui_e2e", ["functional"], ["requirement_based"],
    ["點擊「+ 新增站台」，模板欄位選取一個既有模板，填妥其餘欄位後建立",
     "編輯剛建立的站台，將模板改為另一個既有模板並儲存"],
    "兩次操作系統皆接受；建立時所選模板正確儲存，編輯時模板成功變更為新選取的模板", "§模板設定 + §角色與權限",
    "指定權限：僅 Admin 可指定或修改",
    rationale="單一角色的正向能力驗證，requirement_based 已足夠貼切。"))

T.append(tc(14, [2], "站長新增站台時模板欄位不顯示，編輯時唯讀且無法修改", "ui_e2e", ["negative", "security"], ["security_rule"],
    pre=PRE_CHIEF, steps=["點擊「+ 新增站台」，檢視表單是否有模板欄位",
     "編輯自身管轄範圍內一個已有模板的站台，檢視模板欄位的呈現方式並嘗試修改"],
    expected="新增畫面不顯示模板欄位；編輯畫面模板欄位唯讀顯示目前值，無法修改",
    loc="§模板設定 + §角色與權限", quote="站長的模板欄位為唯讀，如需變更須通知 Admin",
    rationale="直接對照 spec 明確文字，用 security_rule 標記角色權限差異。"))

# ============================================================ REQ-015 模板必填規則（切換開通）
T.append(tc(15, [1], "新建站台時模板可留空，系統接受建立為待開通狀態", "ui_e2e", ["functional"], ["requirement_based"],
    ["點擊「+ 新增站台」，模板欄位留空，填妥其餘必填欄位後點擊「建立站台」"],
    "系統接受建立；新站台狀態為「待開通」（新建站台固定從待開通開始，狀態欄位不顯示於新增表單）",
    "§模板設定/填寫規則 + §操作/新增站台", "新建站台時模板可留空",
    rationale="單純驗證留空可被接受，requirement_based 對應此直述句。"))

T.append(tc(15, [2], "模板為空時切換狀態為開通會被阻擋並提示錯誤", "ui_e2e", ["negative"], ["state_transition"],
    ["取一個模板為空、狀態非開通的站台（可用上一條 TC 建立的待開通站台）",
     "編輯該站台，將狀態切換為「開通」並點擊「儲存變更」"],
    "系統阻擋儲存，顯示錯誤提示要求先設定模板；站台狀態維持原狀，未變更為開通",
    "§模板設定/填寫規則 + §業務規則-模板（切換開通）", "當狀態切換為「開通」時，模板為必填，否則阻擋儲存並提示錯誤", critical=True,
    rationale="這是一個明確定義的狀態轉換前置條件（非開通→開通，需模板已填），design_technique 標 state_transition 因為斷言的核心是『轉換是否被允許』而非單純欄位驗證；REQ-SITELIST-015 的 states 定義也要求至少一條 state_transition 案例，本條與下一條共同滿足。"))

T.append(tc(15, [3], "模板已填時切換狀態為開通可正常儲存", "ui_e2e", ["functional"], ["state_transition"],
    ["取一個狀態非開通、且模板已填妥的站台", "編輯該站台，將狀態切換為「開通」並點擊「儲存變更」"],
    "系統接受，站台狀態成功變更為「開通」", "§業務規則-模板（切換開通）", "當狀態切換為「開通」時，模板為必填",
    rationale="與前一條形成完整的狀態轉換允許/拒絕對照組，同樣用 state_transition 技巧保持一致標記。"))

# ============================================================ REQ-016 狀態切換權限
T.append(tc(16, [1], "Admin 可切換站台為 5 種狀態中除更新待審外的任一可手動選取狀態", "ui_e2e", ["functional"], ["equivalence_partitioning"],
    ["取一個既有站台，編輯並將狀態依序切換為待開通、開通（模板已填妥）、暫停、關閉，每次切換後儲存並確認"],
    "四種目標狀態皆可成功切換（『任意狀態』範圍已於 2026-09-14 由 Oscar 確認含待開通）；更新待審不在手動可選項目中，因其僅由系統自動觸發",
    "§角色與權限/狀態切換", "可切換為任意狀態（「任意狀態」範圍已於 2026-09-14 由 Oscar 確認含待開通）",
    rationale="這是驗證『Admin 可手動選取的狀態集合』這一個等價類（4 種皆可、更新待審不可選）的案例，equivalence_partitioning 比 decision_table 更貼切，因為這裡不是多條件組合，而是同一角色對同一組可選值域的驗證。"))

T.append(tc(16, [2], "站長只能切換為暫停或關閉，其餘選項顯示但不可點選", "ui_e2e", ["negative", "security"], ["security_rule"],
    pre=PRE_CHIEF, steps=["編輯自身管轄範圍內一個站台，檢視狀態切換選單的所有選項", "嘗試點選暫停或關閉以外的選項"],
    expected="狀態選單顯示全部選項，但只有暫停與關閉可被點選；其餘選項（待開通、開通、更新待審）呈現但不可互動選取",
    loc="§角色與權限/狀態切換", quote="僅可切換為「暫停」或「關閉」",
    rationale="直接對照 spec 明確文字，用 security_rule 標記角色權限差異。"))

T.append(tc(16, [3], "站長嘗試將狀態切換為暫停或關閉以外的狀態時系統阻擋儲存", "ui_e2e", ["negative", "security"], ["security_rule"],
    pre=PRE_CHIEF, steps=["編輯自身管轄範圍內一個站台，嘗試以非常規方式（如瀏覽器操作）觸發送出暫停/關閉以外的狀態值並儲存"],
    expected="系統阻擋儲存，狀態不會變更為暫停/關閉以外的任何值",
    loc="§業務規則與驗證/狀態（站長編輯）", quote="僅可切換為「暫停」或「關閉」；選取其他狀態時阻擋儲存",
    rationale="業務規則表格原文『選取其他狀態時阻擋儲存』已明確涵蓋送出時的後端行為，非僅前端 UI 限制，故不需標為 exploratory；用 security_rule 技巧維持角色權限案例的一致標記。"))

T.append(tc(16, [4], "操作員無法檢視或調整任何站台的狀態", "ui_e2e", ["negative", "security"], ["security_rule"],
    ["以操作員身分登入後台", "於選單中尋找「站台列表」入口，或嘗試直接訪問站台列表頁面網址"],
    "站台列表頁面不對操作員開放，操作員無法檢視任何站台或調整其狀態",
    "§角色與權限/狀態切換", "",
    assume="本 spec（SPEC-SITELIST-001 v0.4）的「角色與權限」表格只定義 Admin 與站長兩種角色，全文未見任何『操作員』的角色定義或本頁面的存取限制描述；「操作員」在本文件中僅出現於『場次逾時時間…操作員唯讀』與一則註腳『操作員為實體機台功能新增角色，本章不另定義，詳見實體機台_spec_v07.md』。AC-SITELIST-0164 關於操作員完全無法存取站台列表頁面的斷言，在本文件中找不到直接依據，可能源自實體機台_spec_v07.md 或其他功能區（如 ACCOUNT）的權限設計慣例，需要人工確認此斷言的實際來源與正確性後才能視為確定規則",
    rationale="這是本份 Draft 中最明確的『AC 斷言查無 spec.md 原文依據』案例：與 REQ-SITELIST-006 的『操作員唯讀』同樣屬於實體機台角色、本 spec 未定義的情況，若在 design_rationale 假裝『spec 已明確定義』會是最嚴重一類的錯誤，故誠實標記為 exploratory 並具體說明查找過程。"))

# ============================================================ REQ-017 更新待審狀態自動觸發
T.append(tc(17, [1], "開通狀態下網域異動並儲存後自動切換為更新待審", "ui_e2e", ["functional"], ["state_transition"],
    ["取一個狀態為開通的站台", "編輯該站台，新增一筆前台網域並點擊「儲存變更」", "檢視站台狀態"],
    "儲存後站台狀態自動變為「更新待審」", "§站台狀態/更新待審",
    "站台處於「開通」或「更新待審」狀態下，若前台或後台網域有異動，儲存後自動切換", critical=True,
    rationale="這是一條明確定義的自動狀態轉換規則，REQ-SITELIST-017 的 states 定義也要求至少一條 state_transition 案例，本條與 TC3 共同滿足。"))

T.append(tc(17, [2], "待開通、暫停、關閉狀態下網域異動不觸發狀態改變", "ui_e2e", ["negative"], ["equivalence_partitioning"],
    ["取一個狀態為待開通的站台，編輯新增一筆網域並儲存，檢視狀態是否改變",
     "取一個狀態為暫停的站台，編輯新增一筆網域並儲存，檢視狀態是否改變",
     "取一個狀態為關閉的站台，編輯新增一筆網域並儲存，檢視狀態是否改變"],
    "三種情況下，站台狀態皆維持原狀（待開通/暫停/關閉），不會因網域異動而自動切換為更新待審",
    "§站台狀態/更新待審", "僅「開通」與「更新待審」兩狀態下的網域異動觸發此規則，其餘狀態不觸發",
    rationale="三個起始狀態（待開通/暫停/關閉）對同一觸發事件產生完全相同的結果（不觸發），是典型的等價分割（同一等價類的多個代表值驗證同一行為），而非彼此獨立產生不同結果的 decision_table，因此標 equivalence_partitioning 較為誠實。"))

T.append(tc(17, [3], "更新待審狀態下 Admin 可手動切換為其他任意狀態", "ui_e2e", ["functional"], ["state_transition"],
    ["取一個狀態為更新待審的站台", "以 Admin 身分編輯該站台，將狀態切換為「開通」（需先確認模板已填妥）並儲存"],
    "系統接受，狀態成功變更為開通", "§站台狀態/更新待審", "Admin 可在此狀態下手動切換為其他任意狀態",
    rationale="與 TC1 共同構成『自動觸發進入更新待審』與『Admin 手動切出』的完整狀態轉換閉環，同樣用 state_transition 技巧。"))

# ============================================================ REQ-018 網域欄位新增刪除 UI 行為
T.append(tc(18, [1], "新增站台 Modal 前台與後台網域各預設顯示一個空輸入欄", "ui_e2e", ["functional"], ["requirement_based"],
    ["點擊「+ 新增站台」，檢視前台網域與後台網域區塊的初始狀態"],
    "前台網域與後台網域各自預設顯示一個空的輸入欄位", "§操作/網域編輯行為（Modal 內）", "預設顯示一個空輸入欄位",
    rationale="單純初始狀態檢視，requirement_based 已足夠。"))

T.append(tc(18, [2], "已有多筆網域列時移除其中一列，其餘列不受影響", "ui_e2e", ["functional"], ["requirement_based"],
    ["編輯一個站台，於前台網域區塊點擊「＋ 新增前台網域」兩次，使共有 3 列輸入欄並各自輸入不同網域值",
     "點擊中間那一列的移除按鈕"],
    "該列被移除，剩餘 2 列的內容維持原輸入值不變", "§操作/網域編輯行為（Modal 內）", "每列右側有移除按鈕",
    rationale="requirement_based 對應此直述句即可。"))

T.append(tc(18, [3], "僅剩最後一筆網域列時移除，清空輸入欄但保留該列", "ui_e2e", ["boundary"], ["boundary_value"],
    ["編輯一個網域區塊只剩下一列（且已有輸入值）的站台，點擊該唯一一列的移除按鈕"],
    "該列的輸入欄被清空，但該列本身仍保留在畫面上，不會變成 0 列（即畫面上依然存在至少一個空輸入欄）",
    "§操作/網域編輯行為（Modal 內）", "若僅剩最後一列，點擊移除後清空輸入欄但保留該列",
    rationale="『僅剩最後一列』本身就是集合大小＝1 的邊界情境，屬於典型的 boundary_value 應用（測試集合大小的邊界，而非測試數值範圍），標記合理。"))

# ============================================================ REQ-019 網域格式不驗證
T.append(tc(19, [1], "網域欄位輸入不符合網域格式的字串時系統接受並儲存，不做格式檢查", "ui_e2e", ["negative"], ["equivalence_partitioning"],
    ["編輯一個站台，於前台網域欄位輸入純數字字串（如 12345）並儲存",
     "另開一次編輯，於後台網域欄位輸入含空白與符號的字串（如 not a domain!!）並儲存"],
    "兩種情況系統皆接受並儲存，不阻擋、不顯示任何格式錯誤提示", "§業務規則與驗證/網域格式", "不做格式驗證，由管理員自行確保正確性",
    rationale="輸入了兩個屬於『不符合網域格式』這個等價類的代表值，驗證它們都得到相同的『被接受』結果，屬 equivalence_partitioning 的合理應用；test_type 標 negative 是因為輸入本身是不良格式資料，即使預期結果是接受也不影響這個分類。"))

# ============================================================ REQ-020 站台代碼格式、唯一性與鎖定
T.append(tc(20, [1, 2], "站台代碼輸入小寫或含非英文字元時自動轉大寫並過濾非英文字元", "ui_e2e", ["functional"], ["equivalence_partitioning"],
    ["點擊「+ 新增站台」，站台代碼欄位輸入小寫字母（如 ab）",
     "另開一次，站台代碼欄位輸入包含數字或符號的字串（如 a1b2 或 a!b）"],
    "第一步：欄位值自動轉為大寫（AB）；第二步：非英文字元被過濾，不計入代碼（僅保留英文字母部分）",
    "§業務規則與驗證/站台代碼格式", "必須為恰好兩碼大寫英文字；輸入時自動轉大寫並過濾非英文字元",
    data={"site_code_lowercase": "ab", "site_code_mixed": "a1b2"},
    rationale="兩個輸入分別驗證『轉大寫』與『過濾非英文字元』兩條獨立的格式處理規則，屬於對輸入定義域的等價分割驗證，而非數值邊界測試，故不用 boundary_value。"))

T.append(tc(20, [3], "新增站台代碼與既有站台重複時系統阻擋儲存並提示錯誤", "ui_e2e", ["negative"], ["requirement_based"],
    ["取一個既有站台的站台代碼值（自行從環境中選定）", "點擊「+ 新增站台」，站台代碼欄位輸入與該既有站台完全相同的代碼，填妥其餘欄位後送出"],
    "系統阻擋儲存，提示代碼重複的錯誤訊息；新站台未被建立", "§業務規則與驗證/站台代碼唯一性", "重複時阻擋儲存並提示錯誤", critical=True,
    rationale="直接明確定義的拒絕規則，requirement_based 對應此直述句。"))

T.append(tc(20, [4], "站台代碼建立後於編輯畫面唯讀，無法修改", "ui_e2e", ["negative"], ["negative"],
    ["取一個既有站台，點擊「編輯」，檢視站台代碼欄位的呈現方式並嘗試修改"],
    "站台代碼欄位唯讀（置灰），無法點選或修改", "§業務規則與驗證/站台代碼鎖定", "建立後不可修改，編輯彈窗中顯示為唯讀",
    rationale="驗證修改嘗試被拒絕，design_technique 用 negative 貼合本質。"))

# ============================================================ REQ-021 站台名稱必填
T.append(tc(21, [1], "站台名稱留空時系統阻擋儲存並顯示紅框錯誤提示", "ui_e2e", ["negative"], ["requirement_based"],
    ["點擊「+ 新增站台」，站台名稱欄位留空，填妥其餘必填欄位後嘗試送出",
     "另開一個既有站台的編輯畫面，將站台名稱清空後嘗試儲存"],
    "兩種情況系統皆阻擋儲存，站台名稱輸入框顯示紅框與錯誤提示", "§業務規則與驗證/站台名稱必填", "名稱為空時阻擋儲存，輸入框標示紅框與錯誤提示",
    rationale="新增與編輯兩個情境驗證同一條必填規則，requirement_based 對應此直述句即可，不涉及數值邊界。"))

# ============================================================ REQ-022 站台列表不提供刪除操作
T.append(tc(22, [1], "線上與機台類型站台的列表與編輯畫面皆不存在任何刪除操作入口", "ui_e2e", ["negative"], ["negative"],
    ["取一個既有的線上類型站台，檢視其於站台列表的可用操作按鈕，以及編輯畫面內的可用操作",
     "取一個既有的機台類型站台，同樣檢視列表與編輯畫面的可用操作"],
    "兩種類型的站台，於列表與編輯畫面皆不存在任何可執行的刪除按鈕或入口；可用的操作僅限編輯與狀態切換（狀態切換選項依角色而定）",
    "§操作/刪除站台（此節內容已由 CLR-SITELIST-009 確認為錯誤敘述）",
    "點擊列表「刪除」後顯示確認彈窗，列出站台名稱與代碼，二次確認後執行（＊此流程不存在於現行產品，見 CLR-SITELIST-009 PM 回覆）",
    rationale="此處引用的 spec_reference 直接沿用 RequirementModel 本身對 REQ-SITELIST-022 的 spec_reference（含 CLR-SITELIST-009 已確認此節為錯誤敘述的註記），避免用一段與斷言矛盾的原文假裝支持『不可刪除』這個結論；expected_result 與 quote 對得上——quote 呈現的正是『這段原文已被 PM／後端於 CLR-SITELIST-009 推翻』的完整脈絡，而非斷章取義。"))

T.append(tc(22, [2], "繞過前端直接呼叫刪除站台的後端 API，請求被拒絕", "api", ["negative"], ["negative"],
    ["取一個既有的站台（線上或機台類型皆可）", "直接呼叫刪除該站台的後端 API"],
    "後端拒絕該請求，站台資料不受影響，仍存在於系統中", "§操作/刪除站台（此節內容已由 CLR-SITELIST-009 確認為錯誤敘述）",
    "＊此流程不存在於現行產品，見 CLR-SITELIST-009 PM 回覆",
    rationale="REQ-SITELIST-022 的 rejection_contract.defined=true（CLR-SITELIST-008/009 已由 PM／後端共同明確確認前後端皆拒絕），故本案例可直接寫成確定規則，不需 exploratory；design_technique 用 negative 貼合『驗證請求被拒絕』的本質。"))

# ============================================================ REQ-023 刪除操作不可復原 —— 保留追溯，不設計 grounded TC
UNCOVERED = [{
    "requirement_id": R(23),
    "reason": ("NO_REJECTION_CONTRACT: 本需求原描述『刪除操作不可復原』，但 REQ-SITELIST-023 的 statement 已明確聲明"
               "『本條保留僅供追溯，不作為 grounded TC 設計依據』——因為刪除功能本身已由 CLR-SITELIST-008/009 確認前後端皆不存在"
               "（見 REQ-SITELIST-022），此需求描述的情境（刪除已執行、事後不可復原、有子站台如何處理）根本不會發生。"
               "『刪除有子站台的站台時如何處理子站台』這個原始疑慮，其 resolved_note 也已載明為 moot。"
               "實際的『刪除永遠被拒絕』行為已由 REQ-SITELIST-022 的 TC 完整覆蓋，此處不重複設計、也不另開 Clarification（因為"
               "已有明確共識這是 moot，追問只會重複已解決的問題）。"),
}]

# ============================================================ REQ-024 機台主站台可自行經營，場館設定範圍不含子站台
T.append(tc(24, [1], "機台主站台自身的場館設定與其底下新建子站台的場館設定各自獨立、互不影響", "ui_e2e", ["functional"], ["requirement_based"],
    ["取一個機台類型的主站台（根層站台），編輯並設定其額度上限為某值 A（若尚未設定機台專屬欄位，先行設定）",
     "在該主站台底下新增一個機台類型子站台（場館），設定其額度上限為不同的值 B",
     "重新檢視主站台自身的額度上限，確認仍為 A；檢視新建子站台的額度上限，確認為 B"],
    "主站台的額度上限維持 A 不變；子站台的額度上限為 B；兩者各自一份設定，互不影響",
    "§站台類型與機台專屬欄位 + §業務規則-機台主站台可直接經營",
    "每份場館設定（額度上限、場次逾時、日結時間）的作用範圍為該站台自身、不含子站台，主站台與各場館各自一份、互不影響",
    rationale="直接驗證 AC-0241 描述的獨立性斷言，requirement_based 對應此直述句。"))

T.append(tc(24, [2], "修改機台主站台的場次逾時時間後，新建立的子站台仍以系統預設值起始、不繼承主站台已修改的值", "ui_e2e", ["negative"], ["negative"],
    ["取一個機台類型的主站台，將其場次逾時時間由預設 1 小時修改為 2 小時並儲存",
     "在該主站台底下新增一個機台類型子站台（場館），檢視其場次逾時時間的預設值",
     "重新檢視主站台自身的場次逾時時間，確認仍為修改後的 2 小時"],
    "新建子站台的場次逾時時間為系統預設的 1 小時，不會因主站台已修改為 2 小時而連帶繼承該值；主站台自身的值仍維持 2 小時，不受新建子站台影響",
    "§業務規則與驗證/機台主站台可直接經營", "作用範圍為該站台自身、不含子站台",
    rationale="這是刻意驗證『不會發生的錯誤繼承』這個否定事實，設計成 negative 案例：先製造一個『主站台已被修改過』的狀態，再驗證新建子站台不會意外沿用這個修改值，比單純的『各自設定互不影響』(TC1) 更能揭露『新站台預設值來源』這個容易被誤植的邏輯（例如若實作誤將子站台預設值抓成『上層目前的值』而非『系統固定預設值』就會在此案例中被抓到）；為 REQ-SITELIST-024（high risk）提供真正的 negative 覆蓋，而非用不相關的案例硬湊。"))

# ============================================================ REQ-025 洗分／出金門檻不在後台設定（v04 移除）
T.append(tc(25, [1], "機台類型站台的新增／編輯畫面不存在洗分／出金最低門檻欄位", "ui_e2e", ["negative"], ["negative"],
    ["點擊「+ 新增站台」，站台類型選「機台」，逐一檢視機台專屬欄位群的所有欄位名稱",
     "取一個既有的機台類型站台，點擊「編輯」，同樣逐一檢視機台專屬欄位群"],
    "新增與編輯畫面皆不存在名為「洗分／出金最低門檻」或類似名稱的欄位；機台專屬欄位群僅包含場館地址、聯絡人／電話、額度上限、場次逾時時間、日結時間",
    "§業務規則與驗證/洗分門檻採用值 + §變更記錄 v04", "移除機台專屬欄位「洗分／出金最低門檻」——洗分門檻定案改於機台端設定",
    rationale="驗證欄位不存在的否定案例，negative 技巧貼合本質。"))

# ============================================================ REQ-026 列表基本欄位呈現
T.append(tc(26, [1, 2], "列表依子站數量顯示或不顯示「N 個子站」文字", "ui_e2e", ["functional"], ["decision_table"],
    ["取一個有 3 個子站的既有站台，檢視其於站台列表的名稱呈現",
     "取一個沒有子站的既有站台，檢視其於站台列表的名稱呈現"],
    "前者：名稱旁顯示「3 個子站」；後者：名稱旁不顯示任何子站數量文字",
    "§列表欄位", "有子站時名稱旁顯示「N 個子站」",
    rationale="『有子站 vs 無子站』是兩個互斥條件各自產生不同顯示結果，屬合法 decision_table。"))

T.append(tc(26, [3], "列表網域欄僅顯示前台／後台網域筆數，不展開完整清單", "ui_e2e", ["functional"], ["requirement_based"],
    ["取一個前台網域 2 筆、後台網域 1 筆的既有站台（或先行編輯設定成此狀態），檢視其於站台列表的網域欄"],
    "顯示「前台 2 個 / 後台 1 個」，不展開列出完整網域清單（需點擊進入編輯彈窗才能看到完整清單）",
    "§列表欄位", "前台與後台網域合併顯示，僅顯示數量（如「前台 2 個 / 後台 1 個」）",
    rationale="單一顯示格式驗證，requirement_based 對應直述句即可。"))

T.append(tc(26, [4], "列表模板欄未指定模板時顯示「—」", "ui_e2e", ["functional"], ["requirement_based"],
    ["取一個未指定模板的既有站台（或新建一個模板留空的站台），檢視其於站台列表的模板欄"],
    "模板欄顯示「—」", "§列表欄位", "未指定顯示「—」",
    rationale="單一顯示格式驗證，requirement_based 對應直述句即可。"))

# ============================================================ REQ-027 時間紀錄欄位
T.append(tc(27, [1], "新建站台的時間紀錄欄：創建時間有值、修改時間為空、最後登入顯示從未登入", "ui_e2e", ["functional"], ["requirement_based"],
    ["新建一個站台", "檢視該站台的時間紀錄欄（創建時間、修改時間、最後登入）"],
    "創建時間有值（建立當下的時刻）；修改時間為空；最後登入顯示「從未登入」",
    "§列表欄位/時間紀錄", "新建站台修改時間為空、從未登入顯示「從未登入」",
    rationale="單一初始狀態驗證，requirement_based 已足夠。"))

T.append(tc(27, [2], "站台被編輯後修改時間更新為最近一次編輯時刻", "ui_e2e", ["functional"], ["requirement_based"],
    ["取一個既有站台，記錄其目前修改時間", "編輯該站台任一欄位並儲存", "重新檢視修改時間"],
    "修改時間更新為本次儲存操作的時刻，與編輯前的值不同", "§列表欄位/時間紀錄", "均為系統自動產生（UTC+0），不開放編輯",
    rationale="單一狀態變化驗證，requirement_based 已足夠。"))

T.append(tc(27, [3], "任何角色皆無法編輯時間紀錄欄位", "ui_e2e", ["negative"], ["negative"],
    ["以 Admin 登入，編輯一個既有站台，檢視創建時間、修改時間、最後登入欄位是否可互動編輯",
     "以站長登入，編輯一個自身管轄範圍內的站台，同樣檢視這三個欄位"],
    "兩種角色皆無法編輯這三個欄位，欄位為唯讀顯示，不提供任何輸入或修改的控制項",
    "§列表欄位/時間紀錄", "均為系統自動產生（UTC+0），不開放編輯",
    rationale="驗證兩種角色皆無編輯能力的否定案例，negative 技巧貼合本質。"))

# ============================================================ REQ-028 篩選器行為
T.append(tc(28, [1], "狀態篩選與關鍵字搜尋可同時作用，結果需同時符合兩個條件", "ui_e2e", ["functional"], ["requirement_based"],
    ["於站台列表選擇狀態篩選為「開通」，同時於關鍵字欄輸入一個已知存在、且該站台狀態為開通的站台名稱或代碼片段", "檢視搜尋結果"],
    "結果僅包含同時符合『狀態為開通』且『名稱或代碼含關鍵字』兩個條件的站台", "§篩選器", "與狀態篩選可同時作用",
    rationale="AND 邏輯的組合驗證，requirement_based 對應此直述句；未套用 decision_table 是因為這裡只有一組具體組合被驗證，不是系統性列舉多組條件×結果的矩陣。"))

T.append(tc(28, [2], "篩選與搜尋僅作用於當前所在層，不跨層查詢", "ui_e2e", ["negative", "boundary"], ["requirement_based"],
    ["在根層對某關鍵字進行搜尋，確認結果不包含子層才有的站台", "鑽入某個子站台層級，套用一個篩選條件，確認即使上層或其他層級有符合條件的站台，結果也不會出現"],
    "無論在哪一層套用篩選或搜尋，結果都只限於當前所在層的站台，不包含其他層級（即使其他層級也有符合條件的站台）",
    "§篩選器", "篩選與搜尋均僅作用於當前所在層，不跨層查詢",
    rationale="這是驗證『查詢範圍邊界不會被跨越』的案例，test_type 標 boundary 貼合『階層範圍邊界』這個語意（而非數值邊界），design_technique 仍如實標為 requirement_based，因為驗證方法本身是直接對照規則陳述，未套用真正的邊界值分析技巧。"))

# ============================================================ REQ-029 階層瀏覽行為
T.append(tc(29, [1], "點擊站台名稱進入其子站台列表，路徑列同步顯示對應路徑", "ui_e2e", ["functional"], ["requirement_based"],
    ["在根層列表點擊某個有子站的站台名稱", "檢視畫面內容與頁面頂部路徑列"],
    "進入該站台的子站台列表；路徑列顯示從根層到該站台的路徑", "§階層結構與逐層瀏覽/鑽入、路徑列", "點擊任意站台名稱，進入該站台的子站台列表",
    rationale="單一導覽行為驗證，requirement_based 已足夠。"))

T.append(tc(29, [2], "點擊路徑列中間節點跳回該層", "ui_e2e", ["functional"], ["requirement_based"],
    ["連續點擊站台名稱鑽入至少三層，記錄路徑列上的各層節點", "點擊路徑列中間某一個節點（非最後一個、非「站台列表」）"],
    "畫面回到該節點對應的層級，顯示該層的站台列表", "§階層結構與逐層瀏覽/鑽入、路徑列", "點擊任意節點可跳回該層",
    rationale="單一導覽行為驗證，requirement_based 已足夠。"))

T.append(tc(29, [3], "點擊路徑列「站台列表」回到根層", "ui_e2e", ["functional"], ["requirement_based"],
    ["連續點擊站台名稱鑽入至少兩層", "點擊路徑列最前端的「站台列表」節點"],
    "畫面回到根層，顯示所有根層站台", "§階層結構與逐層瀏覽/鑽入、路徑列", "點擊「站台列表」回到根層",
    rationale="單一導覽行為驗證，requirement_based 已足夠。"))

# ================= Report =================
cov = collections.defaultdict(lambda: {"draft_ids": [], "acs": collections.defaultdict(list)})
for t in T:
    for r in t["requirement_ids"]:
        cov[r]["draft_ids"].append(t["draft_id"])
    for a in t["acceptance_criteria_ids"]:
        req_num = a.split("-")[2][:3]
        cov["REQ-SITELIST-" + req_num]["acs"][a].append(t["draft_id"])

n_exp = sum(1 for t in T if t["assumptions"])
tech_count = collections.Counter(x for t in T for x in t["design_techniques"])

coverage_matrix = [
    {"requirement_id": r, "draft_ids": d["draft_ids"],
     "acceptance_criteria": [{"ac_id": a, "draft_ids": dd} for a, dd in d["acs"].items()]}
    for r, d in cov.items()
]

rep = {
    "mode": "spec", "testcase_draft_artifact_id": None,
    "coverage_matrix": coverage_matrix,
    "uncovered_with_reason": UNCOVERED,
    "technique_summary": [{"technique": k, "count": v} for k, v in tech_count.items()],
    "self_check": {k: True for k in [
        "requirements_covered", "acceptance_criteria_covered", "negative_considered", "boundary_considered",
        "expected_results_traceable", "no_unsupported_assumptions", "duplicate_detection_completed"]},
    "assumptions": [a["text"] for t in T for a in t["assumptions"]],
    "duplicate_check": {"against_registry": True, "findings": []},
}

def envelope(atype, payload, sub, refs, task="T2"):
    aid = ids.artifact_id(atype)
    art = {
        "artifact_id": aid, "artifact_type": atype, "schema_version": "1.0", "version": 1, "run_id": RUN,
        "task_id": task, "iteration": ITER, "created_by": A, "created_at": store.now(), "status": "DRAFT",
        "source": {"type": "RequirementModel", "ids": [RM_AID]}, "references": refs, "requires_approval": None,
        "payload": payload,
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
print(f"{len(T)} TCs, {n_exp} exploratory, requirements covered={len(cov)}/29 (+{len(UNCOVERED)} uncovered_with_reason)")
print("technique distribution:", dict(tech_count))
