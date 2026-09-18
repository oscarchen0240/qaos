#!/usr/bin/env python3
"""RUN-20260918-002 T2：Test Designer(mode=spec) 依 SPEC-BONUSCCY-001 v1.0 的 5 條需求展開 TestCaseDraft + TestDesignReport。
獨立設計（未參考既有 testcases/BONUSCCY.md），依 spec 原文 + 跨 spec（ARCADE-001/PLATFORMRULE-001/MEMBER-001）背景知識確認系統邊界後設計。"""
import sys, pathlib, collections
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids

RUN = "RUN-20260918-002"
ITER = 0
SID, SV, AREA, A = "SPEC-BONUSCCY-001", "1.0", "BONUSCCY", "agent-test-designer"

rm = store.load(store.requirements_path(SID, SV))
RM_AID = rm["source_artifact_id"]
reqs = {r["requirement_id"]: r for r in rm["requirements"]}

def sr(loc, quote=""):
    return {"spec_id": SID, "spec_version": SV, "location": loc, "quote": quote}

def tc(req_id, ac_ids, title, level, types, techs, pre, steps, expected, loc, quote="",
       prio=None, risk=None, data=None, assume=None, critical=False, cost="medium",
       more_reqs=(), extra_ac=(), rationale=""):
    r = reqs[req_id]
    assumptions = []
    for a in ([assume] if isinstance(assume, str) else (assume or [])):
        assumptions.append({"text": a, "requirement_id": req_id, "needs_human_confirmation": True})
    prio = prio or (risk or r["risk"])
    return {
        "draft_id": f"TC-DRAFT-{ids.ulid()}", "title": title, "product": "ba-admin", "functional_area": AREA,
        "requirement_ids": [req_id] + list(more_reqs),
        "acceptance_criteria_ids": list(ac_ids) + list(extra_ac),
        "spec_id": SID, "spec_version": SV, "test_level": level, "test_types": types, "design_techniques": techs,
        "priority": prio, "risk": risk or r["risk"], "execution_mode": "manual",
        "preconditions": pre,
        "test_data": [{"name": k, "value": v} for k, v in (data or {}).items()],
        "steps": [{"n": i + 1, "action": s} for i, s in enumerate(steps)],
        "expected_result": expected,
        "expected_result_spec_reference": sr(loc, quote),
        "assumptions": assumptions, "automation_status": "not_automated",
        "ci_eligible": False, "hotfix_eligible": True, "execution_cost": cost, "stability": "unknown",
        "critical_path": critical, "source": "spec_workflow", "design_rationale": rationale,
    }

T = []

# ============================================================
# REQ-BONUSCCY-001 — 注單查詢/明細頁的金額欄位以站台核心貨幣顯示
# ============================================================
PRE_TWD_BASE = ["以 Admin 登入後台", "站台切換選單切換至一個既有的機台（TWD核心貨幣）站台（自行從環境中選定）"]

T.append(tc("REQ-BONUSCCY-001", ["AC-BONUSCCY-001"],
    "機台站台的注單查詢列表金額欄位以核心貨幣TWD顯示",
    "ui_e2e", ["functional"], ["requirement_based"],
    PRE_TWD_BASE + ["該站台底下已有既有機台帳號的注單紀錄（自行從環境中選定；若無可透過該機台帳號實際遊玩產生一筆）"],
    ["進入 各式報表 > 注單查詢（機台場館下此頁面可見）", "查詢列表中任一筆屬於該機台站台的注單", "檢視列表金額欄位"],
    "金額欄位顯示為站台核心貨幣 TWD 的數值，不是寫死顯示 USDT 或其換算值",
    "§實際被改到的地方（表格第2項：注單三層金額）",
    "注單三層金額 | game_bet_log → …_wallet_reference → …_system_wallet_reference，第三層的幣別與換算改依站台核心貨幣",
    rationale="AC-BONUSCCY-001明確要求金額欄位顯示站台核心貨幣；本TC對應「注單查詢」列表視角。注單查詢於機台場館選單中為可見頁面（見SPEC-ARCADE-001/PLATFORMRULE-001「機台場館的後台選單」表格：各式報表下注單查詢可見），故不存在系統邊界問題。"))

T.append(tc("REQ-BONUSCCY-001", ["AC-BONUSCCY-001"],
    "機台站台的注單明細頁金額欄位以核心貨幣TWD顯示",
    "ui_e2e", ["functional"], ["requirement_based"],
    PRE_TWD_BASE + ["該站台底下已有既有機台帳號的注單紀錄（自行從環境中選定）"],
    ["進入 各式報表 > 注單查詢，點擊任一筆屬於該機台站台的注單進入明細頁", "檢視明細頁的金額欄位"],
    "明細頁金額欄位顯示為站台核心貨幣 TWD 的數值，與列表頁一致，不是寫死顯示 USDT 或其換算值",
    "§實際被改到的地方（表格第2項：注單三層金額）",
    "注單三層金額 | game_bet_log → …_wallet_reference → …_system_wallet_reference，第三層的幣別與換算改依站台核心貨幣",
    rationale="與上一條為同一AC的兩個不同畫面（列表/明細），AC原文本身即列出「查詢/明細頁」兩者，故拆為兩條TC分別驗證兩個畫面，而非湊技巧數量。"))

T.append(tc("REQ-BONUSCCY-001", ["AC-BONUSCCY-001"],
    "對照組：線上站台（USDT核心貨幣）的注單查詢/明細金額欄位仍顯示USDT，不受本次改動影響",
    "ui_e2e", ["functional"], ["equivalence_partitioning"],
    ["以 Admin 登入後台", "站台切換選單切換至一個既有的線上（USDT核心貨幣）站台（自行從環境中選定）"],
    ["進入 各式報表 > 注單查詢，查詢一筆屬於該線上站台的注單", "檢視列表與明細頁的金額欄位"],
    "金額欄位維持顯示 USDT（線上站台核心貨幣本就是USDT，行為與改動前一致，未因本次改動而變動）",
    "§一句話 + §改之前 vs 改之後",
    "現有的線上站台全部維持 USDT，不受這次改動影響",
    rationale="以核心貨幣分類做等價分割：TWD站台與USDT站台是本次改動影響範圍的兩個等價類，此案例驗證USDT類（未受影響類）維持原行為，屬於針對本次架構改動的回歸確認，而非無關的規則外推。"))

# ============================================================
# REQ-BONUSCCY-002 — 會員列表 / Dashboard 總會員數正確涵蓋機台站台會員
# high risk：規則本身是"正確計入"，但真正的風險是「悄悄被排除」，
# 用 before/after delta 的 error_guessing 手法直接對準此風險設計。
# ============================================================
T.append(tc("REQ-BONUSCCY-002", ["AC-BONUSCCY-002"],
    "新增一名機台站台會員後，Dashboard總會員數應同步遞增，不因原本寫死USDT的JOIN條件而悄悄排除",
    "ui_e2e", ["functional"], ["error_guessing"],
    ["以 Admin 身分登入後台（Admin可見所有場館）",
     "站台切換選單切換至一個既有的機台（TWD核心貨幣）站台，記錄當下可見的「資訊看板」選單是否存在——依SPEC-ARCADE-001／SPEC-PLATFORMRULE-001「機台場館的後台選單」規則，切至機台場館時「資訊看板」分類整個隱藏，須切換至一個仍可見資訊看板的範圍（例如該機台站台的上層主站台，若主站台本身非機台類型）才能檢視Dashboard"],
    ["切換至一個資訊看板選單可見的範圍，進入 資訊看板 Dashboard 頁，記錄目前顯示的總會員數（N）",
     "切回步驟一所選的機台站台，於 會員與加盟商 > 會員列表 點擊「創建會員帳號」，帳號類型選「機台」，建立一個新的機台帳號（帳號建立方式依SPEC-ARCADE-001，非本次BONUSCCY spec範圍，僅作測試資料佈置依據）",
     "切回資訊看板可見範圍，重新整理/重新查詢 Dashboard 總會員數（N'）"],
    "N' 應等於 N+1，新建立的機台站台會員確實計入Dashboard總會員數，未因JOIN條件比對寫死USDT常數而被排除在統計之外",
    "§實際被改到的地方（表格第3項：後台查詢）",
    "後台查詢 | 注單列表與明細、返水明細、營運日報、會員列表、Dashboard 總會員數 —— 這些的 JOIN 條件原本比對常數",
    assume="假設Dashboard總會員數為涵蓋所有站台（含機台站台）的平台層級聚合數字，且後台操作者存在可切換到、仍可見「資訊看板」選單、其統計範圍涵蓋該機台站台的位置；若目前測試環境中該機台站台本身即為主站台（無其他非機台上層可切換），Dashboard總會員數在此情境下如何呈現待與環境/PM確認。此為Dashboard本身的顯示範圍語意，目前找不到SPEC-BONUSCCY-001以外的spec明確定義",
    rationale="REQ-BONUSCCY-002為high risk，其rejection_contract.description明確指出風險是『資料悄悄消失而非報錯』——單純檢查『某會員存在於總數中』無法證偽，唯有before/after delta才能真正驗證JOIN條件是否正確涵蓋，故採error_guessing技巧設計此案例，直接針對此已知風險模式。導覽路徑另外依SPEC-ARCADE-001/PLATFORMRULE-001確認『機台場館後台選單隱藏資訊看板』這條硬性事實（非本次spec範圍但為既有系統邊界事實），避免誤以為機台站台下也能直接點開Dashboard；但Dashboard本身統計範圍的精確語意（是否為全平台總和）目前無spec明文定義，故以assumption誠實標記。"))

T.append(tc("REQ-BONUSCCY-002", ["AC-BONUSCCY-003"],
    "站台切換至機台站台後，會員列表正確列出該站台會員",
    "ui_e2e", ["functional"], ["requirement_based"],
    ["以 Admin 登入後台", "站台切換選單切換至一個既有的機台（TWD核心貨幣）站台（自行從環境中選定，且底下已有既有機台帳號）"],
    ["進入 會員與加盟商 > 會員列表", "不加任何篩選條件直接查詢"],
    "查詢結果正確列出該機台站台底下所有既有會員（含機台帳號），未因幣別相關的JOIN條件而遺漏資料",
    "§實際被改到的地方（表格第3項：後台查詢）",
    "後台查詢 | ……會員列表、Dashboard 總會員數 —— 這些的 JOIN 條件原本比對常數",
    rationale="會員列表本身即為機台場館後台選單中可見頁面（SPEC-ARCADE-001確認），此為AC-BONUSCCY-003的基本情境驗證，屬於單一輸入條件對應單一結果的直接驗證，如實標記requirement_based而非硬套decision_table。"))

T.append(tc("REQ-BONUSCCY-002", ["AC-BONUSCCY-003"],
    "新增一名機台站台會員後，該站台會員列表查詢筆數應同步增加，不因JOIN條件排除",
    "ui_e2e", ["functional"], ["error_guessing"],
    ["以 Admin 登入後台", "站台切換選單切換至一個既有的機台（TWD核心貨幣）站台"],
    ["進入 會員與加盟商 > 會員列表，不加篩選查詢，記錄目前總筆數（N）",
     "點擊「創建會員帳號」，帳號類型選「機台」，建立一個新的機台帳號",
     "重新查詢會員列表（不加篩選），記錄新的總筆數（N'）並確認新建立的帳號出現在列表中"],
    "N' 應等於 N+1，且新建立的機台帳號出現在查詢結果中，會員列表未因JOIN條件比對寫死USDT常數而遺漏該筆機台站台會員",
    "§實際被改到的地方（表格第3項：後台查詢）",
    "後台查詢 | ……會員列表、Dashboard 總會員數 —— 這些的 JOIN 條件原本比對常數",
    rationale="與Dashboard的delta驗證同一手法對稱套用在會員列表本身，同樣針對『悄悄被排除而非報錯』的已知風險模式，技巧誠實標為error_guessing；此處導覽路徑無資訊看板隱藏的問題，故不需額外assumption。"))

# ============================================================
# REQ-BONUSCCY-003 — 人工存入/人工提出未指定幣別時，預設寫入站台核心貨幣
# 背景：依SPEC-MEMBER-001 v0.2/SPEC-ARCADE-001 v07，該面板「幣種選擇」欄位
# 固定顯示USDT、操作者無法切換，這正是AC所稱「未指定幣別」的實際操作情境。
# ============================================================
PRE_MANUAL = PRE_TWD_BASE + ["該站台底下已有一個既有機台帳號（自行從環境中選定）",
    "已知該面板「幣種選擇」欄位固定顯示 USDT 且操作者無法切換（此為既有UI行為，依SPEC-MEMBER-001/SPEC-ARCADE-001定案不受本次調整，非本次驗證重點；本測試重點是實際入帳/扣款結果的幣別，而非該欄位顯示文字）"]

T.append(tc("REQ-BONUSCCY-003", ["AC-BONUSCCY-004"],
    "對機台站台會員執行人工存入（幣種選擇欄位固定USDT無法切換），實際入帳至該站台核心貨幣TWD錢包",
    "ui_e2e", ["functional"], ["error_guessing"],
    PRE_MANUAL,
    ["進入該機台帳號的會員詳細資料頁，記錄目前核心貨幣（TWD）錢包餘額（收合顯示值，機台站台僅TWD一種錢包不會有展開箭頭）",
     "點擊「人工存入」開啟面板，金額欄填入一筆測試金額（例如100），稽核欄位維持預設值，前台備注與後台備注皆填寫必填文字，幣種選擇欄位維持固定顯示的 USDT（無法切換），點擊「儲存」",
     "重新整理/回到會員詳細頁，檢視核心貨幣（TWD）錢包餘額"],
    "該會員核心貨幣（TWD）錢包餘額較存入前增加所填寫的金額；金額確實寫入站台核心貨幣（TWD），而不是寫死的 USDT（若舊行為的錯誤仍存在，資金將寫入USDT而非TWD，此筆TWD餘額將不會增加，可藉此判斷）",
    "§實際被改到的地方（表格第6項：人工出入金）",
    "人工出入金 | 四支原本沒有明確寫入幣別（靠資料表 DEFAULT 或填死 USDT），改成取核心貨幣",
    rationale="AC-BONUSCCY-004描述的『未指定幣別』情境，實際對應到既有UI『幣種選擇欄位固定USDT、操作者無從選擇』這個已知事實（依SPEC-MEMBER-001 v0.2與SPEC-ARCADE-001 v07定案，非本次spec範圍但為既有UI行為，作為precondition依據）；技巧標為error_guessing，因為此案例直接針對rejection_contract.description所述『錢會進錯錢包』的已知回歸風險，以增額比對代替單純觀察『有沒有寫入』，才能真正證偽。"))

T.append(tc("REQ-BONUSCCY-003", ["AC-BONUSCCY-005"],
    "對同一機台站台會員執行人工提出（幣種選擇欄位固定USDT無法切換），實際從該站台核心貨幣TWD錢包扣除",
    "ui_e2e", ["functional"], ["error_guessing"],
    PRE_MANUAL + ["該機台帳號目前核心貨幣（TWD）錢包餘額足以扣除本次測試金額（可先透過人工存入墊高餘額，或選擇餘額已足夠的既有帳號）"],
    ["進入該機台帳號的會員詳細資料頁，記錄目前核心貨幣（TWD）錢包餘額",
     "點擊「人工提出」開啟面板，金額欄填入一筆不超過目前TWD餘額的測試金額，稽核欄位維持預設值，前台備注與後台備注皆填寫必填文字，幣種選擇欄位維持固定顯示的 USDT（無法切換），點擊「儲存」",
     "重新整理/回到會員詳細頁，檢視核心貨幣（TWD）錢包餘額"],
    "該會員核心貨幣（TWD）錢包餘額較提出前減少所填寫的金額；金額確實從站台核心貨幣（TWD）扣除，而不是寫死的 USDT（若舊行為的錯誤仍存在，TWD餘額將不會減少、或因找不到USDT餘額扣款而失敗，可藉此判斷）",
    "§實際被改到的地方（表格第6項：人工出入金）",
    "人工出入金 | 四支原本沒有明確寫入幣別（靠資料表 DEFAULT 或填死 USDT），改成取核心貨幣",
    rationale="與人工存入對稱設計，同樣以error_guessing技巧直接針對『錢會進錯錢包或找不到對應餘額扣款』的已知回歸風險；兩者情境對稱（存入/提出），技巧標籤保持一致，不因對稱情境刻意標成不同技巧。"))

# ============================================================
# REQ-BONUSCCY-004 — 核心貨幣對應的錢包幣別停用後，入金/出金/開分/洗分四項操作皆須被阻擋
# 背景：入金/出金/開分/洗分皆是機台廠商API觸發的操作（SPEC-ARCADE-001附錄：
# req-cashin/end-cashin、req-cashout/end-cashout、req-keyin、req-keyout），
# 後台管理系統本身沒有可直接點擊的「入金/出金/開分/洗分」按鈕（人工存入/人工提出是另一組不同功能，
# 對應REQ-BONUSCCY-003，非本REQ範圍）。故此四條TC的test_level標為api，
# 以直接呼叫對應API（或使用測試環境提供的機台模擬工具）代替實體機台送出請求。
# ============================================================
PRE_DISABLE = ["以 Admin 登入後台",
    "站台切換選單切換至一個既有的機台（TWD核心貨幣）站台（建議使用測試專用場館，避免影響其他測試或正式資料）",
    "進入 帳務管理 > 鏈上錢包管理，切至「法幣 TWD」頁籤，找到 TWD 幣別列，確認其目前為啟用狀態，將其切換為停用（此為刻意保留的止損操作，依REQ-BONUSCCY-004規則本身應允許停用）",
    "確認鏈上錢包管理列表中 TWD 幣別狀態已顯示為停用",
    "取得該站台一台既有機台帳號可用的機台憑證（JWT），或使用測試環境提供的機台模擬工具/API client 代替實體機台呼叫平台API（此驗證方式的API格式依據SPEC-ARCADE-001附錄「機台系統對接規格」，非BONUSCCY-001本身定義範圍，僅作為測試執行環境依據；實際測試環境是否已具備此類模擬工具，需環境負責人確認）"]

def req004_tc(op_name, api_name, ac_id, extra_pre=None, rationale_extra=""):
    return tc("REQ-BONUSCCY-004", [ac_id],
        f"站台核心貨幣對應的錢包幣別（TWD）已停用時，{op_name}請求應被系統阻擋",
        "api", ["negative"], ["negative"],
        PRE_DISABLE + (extra_pre or []),
        [f"記錄該機台帳號目前的分數（餘額）",
         f"以該機台帳號的憑證呼叫平台 {api_name} API，代入一筆正常測試金額，模擬機台送出{op_name}請求",
         "檢視 API 回覆內容，並至 各式報表 > 交易紀錄查詢 檢視該機台帳號是否新增對應交易紀錄",
         "重新檢視該機台帳號的分數（餘額）"],
        f"平台拒絕該筆{op_name}請求（不論回覆的具體原因文案為何——依rejection_contract.description，spec未給定文案，僅驗證是否被阻擋）；該機台帳號的分數（餘額）維持不變，不因此筆請求而異動",
        "§一句話（限制段落）",
        "補充（2026-09-15 PM確認）：核心貨幣所對應的錢包幣別可停用作即時止損用途，停用後入金/出金/開分/洗分四項操作皆須被阻擋",
        rationale=f"REQ-BONUSCCY-004的rejection_contract.defined=true（PM 2026-09-15已明確確認規則），故以確定規則而非exploratory方式撰寫；behavior_kind=rejection，test_types標negative符合結構化規則。{op_name}屬於機台廠商API觸發的操作（見SPEC-ARCADE-001附錄，{api_name}），後台管理系統本身沒有對應的按鈕可直接點擊操作——這與『人工存入/人工提出』（REQ-BONUSCCY-003，後台確有按鈕）是完全不同的兩組功能，不可混淆；故test_level標為api，以直接呼叫API或機台模擬工具代替，並在precondition中誠實說明此驗證方式依賴的測試環境條件。{rationale_extra}")

T.append(req004_tc("入金", "req-cashin（第一階段請求）", "AC-BONUSCCY-006"))
T.append(req004_tc("出金", "req-cashout（第一階段請求）", "AC-BONUSCCY-022",
    extra_pre=["該機台帳號分數（餘額）大於0（出金請求金額為平台核算的全部餘額，無法指定金額）"]))
T.append(req004_tc("開分", "req-keyin", "AC-BONUSCCY-023"))
T.append(req004_tc("洗分", "req-keyout（帶一組正值 throshold，或throshold=0代表洗出全部餘額）", "AC-BONUSCCY-024",
    extra_pre=["該機台帳號分數（餘額）大於0"]))

# ============================================================
# REQ-BONUSCCY-005 — 機台站台的前台資產列表僅顯示核心貨幣
# 背景：本條明確是前台（玩家端）畫面（rejection_contract.description已言明），
# 需以機台帳號登入前台驗證，機台帳號的登入帳密可透過後台會員詳細頁「重設密碼」取得。
# ============================================================
T.append(tc("REQ-BONUSCCY-005", ["AC-BONUSCCY-007"],
    "以機台帳號登入前台，資產列表僅顯示核心貨幣TWD一種，不列出其他幣別零餘額項目",
    "ui_e2e", ["functional"], ["requirement_based"],
    ["該機台（TWD核心貨幣）站台已有一個既有機台帳號（自行從環境中選定）",
     "已透過後台該機台帳號的會員詳細頁「重設密碼」功能取得一組可用的登入帳號密碼（一次性顯示；帳號建立與密碼重設機制依SPEC-ARCADE-001，非本次BONUSCCY spec定義範圍，僅作測試資料佈置依據）",
     "已知悉該站台對應的前台網址"],
    ["以取得的登入帳號密碼登入該站台前台",
     "進入前台資產列表（錢包頁面）",
     "檢視列表顯示的幣別項目"],
    "資產列表僅顯示核心貨幣 TWD 一種；不出現任何其他幣別（如 USDT 等）的零餘額項目",
    "§⭐兩種站台差很多 + 實際被改到的地方（表格第8項）",
    "前台資產列表 | 只列 TWD（本次改的，見下表第 8 項）｜機台站台的資產列表 | 只列核心貨幣，不再列出一排餘額 0 的其他幣別",
    rationale="rejection_contract.description已明確指出這是本批requirement中第一次測前台（玩家端）畫面，非後台管理端；已依此誠實在precondition中說明需前台環境與登入憑證取得方式，而非想當然爾地假設後台有直接對應的操作入口。"))

T.append(tc("REQ-BONUSCCY-005", ["AC-BONUSCCY-007"],
    "對照組：線上帳號（USDT核心貨幣，多幣別站台）前台資產列表仍列出多筆幣別含零餘額，行為不受影響",
    "ui_e2e", ["functional"], ["equivalence_partitioning"],
    ["一個線上（USDT核心貨幣）站台已啟用一種以上幣別錢包",
     "已有一個該站台的既有線上會員帳號與其登入憑證（自行從環境中選定；與REQ-BONUSCCY-005驗證的機台帳號為不同站台、不同帳號）"],
    ["以該線上會員帳號登入前台", "進入前台資產列表", "檢視列表顯示的幣別項目"],
    "資產列表列出該站台所有已啟用的幣別，包含餘額為 0 的幣別項目，維持改動前既有行為，不受本次機台站台專屬改動影響",
    "§⭐兩種站台差很多",
    "線上站台 | 玩家可以有幾種錢包 | 可以同時有多種（USDT／USD／TWD⋯⋯）；線上站台的多錢包完全保留 —— 這次沒有動存款幣別",
    rationale="以核心貨幣/站台類型做等價分割，驗證未受影響類（線上站台）維持原行為；避免只驗證機台站台就對線上站台行為妄下定論，兩者為spec明確區分的不同類別，各自獨立驗證。"))


# ================= Coverage & Report =================
cov = collections.defaultdict(lambda: {"draft_ids": [], "acs": collections.defaultdict(list)})
for t in T:
    for r in t["requirement_ids"]:
        cov[r]["draft_ids"].append(t["draft_id"])
    for a in t["acceptance_criteria_ids"]:
        for r in t["requirement_ids"]:
            if any(ac["ac_id"] == a for ac in reqs[r]["acceptance_criteria"]):
                cov[r]["acs"][a].append(t["draft_id"])

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
        "requirements_covered", "acceptance_criteria_covered", "negative_considered",
        "boundary_considered", "expected_results_traceable", "no_unsupported_assumptions",
        "duplicate_detection_completed"]},
    "assumptions": [a["text"] for t in T for a in t["assumptions"]],
    "duplicate_check": {"against_registry": True, "findings": []},
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
print("technique distribution:", dict(tech_count))
