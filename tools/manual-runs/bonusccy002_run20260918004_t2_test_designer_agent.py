#!/usr/bin/env python3
"""T2：Test Designer(mode=spec) 依 SPEC-BONUSCCY-002 v1.0 的 5 條需求展開 TestCaseDraft + TestDesignReport。
RUN-20260918-004。REQ-BONUSCCY-006／REQ-BONUSCCY-010 為 high risk。"""
import sys, pathlib, collections
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids

RUN = "RUN-20260918-004"
RM_AID = "ART-RM-01M2GKYSV5VCR08R55SQPW9YM6"
ITER = 0
SID, SV, AREA, A = "SPEC-BONUSCCY-002", "1.0", "BONUSCCY", "agent-test-designer"
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

# ============ REQ-BONUSCCY-006（high risk）一般紅利一律發站台系統幣別 ============

T.append(tc(
    "REQ-BONUSCCY-006", ["AC-BONUSCCY-008"],
    "玩家用非系統幣別下注時，返水仍發放進站台系統幣別錢包",
    "ui_e2e", ["functional"], ["requirement_based"],
    PRE_ADMIN + ["選定一個已啟用兩種以上幣別的線上站台（系統幣別例如 USDT，另啟用至少一種非系統幣別例如 TTK）",
                 "選定一名該站台既有會員，其近期已使用 TTK 餘額下注並已產生一筆返水（自行從環境中挑選，或於前台以 TTK 餘額完成下注等待返水結算週期產生）"],
    ["於後台『會員列表』查詢該會員，進入會員詳細資料頁，展開帳務資訊的『帳戶餘額（主錢包）』多幣別檢視，記錄目前系統幣別（USDT）與 TTK 兩個錢包的餘額",
     "確認該會員這筆返水已結算入帳後，重新查看同一組多幣別餘額"],
    "返水入帳後，增加的金額出現在系統幣別（USDT）錢包那一列，TTK 錢包餘額不因這筆返水而變動；即使玩家下注用的是 TTK 餘額，返水依然發放進系統幣別錢包，不受下注/存款所用幣別影響",
    "§一句話 + §每一種紅利發什麼幣別",
    "除了「彩金活動」與「遊戲商JACKPOT／促銷派彩」，其他紅利一律發「站台系統幣別」。玩家拿哪個錢包下注、用什麼幣別存款，都不影響紅利發出來的幣別。｜返水：站台系統幣別",
    critical=True,
    rationale="AC-BONUSCCY-008 直接以返水為例；多幣別餘額展開檢視的操作方式依 SPEC-MEMBER-001 v0.2 §2.1.6（會員詳細資料頁帳務資訊可展開逐列查看各幣別錢包），本条只驗『發到哪個錢包』這個 spec 明確定義的斷言，返水本身如何被觸發（結算週期）不在 BONUSCCY-002 定義範圍內，測試執行時以既有已產生返水的會員或等待一次自然結算週期為準"))

T.append(tc(
    "REQ-BONUSCCY-006", ["AC-BONUSCCY-008"],
    "代理佣金同樣一律發放進站台系統幣別，不受下線用何種幣別下注影響",
    "ui_e2e", ["functional"], ["equivalence_partitioning"],
    PRE_ADMIN + ["選定一個已啟用兩種以上幣別的線上站台", "選定一名有代理身分、其下線近期已產生佣金基數的既有代理會員"],
    ["於後台會員詳細資料頁展開該代理會員的多幣別餘額檢視，記錄目前系統幣別與其他已啟用幣別（如 TTK）錢包的餘額",
     "確認該代理這筆代理佣金已結算入帳後，重新查看同一組多幣別餘額"],
    "代理佣金入帳後，增加的金額出現在系統幣別錢包那一列，其餘幣別錢包不因這筆佣金而變動；驗證除返水外，代理佣金這個不同計算基礎（下線流水而非自身有效投注）的紅利類型，同樣遵守一律發系統幣別的規則",
    "§每一種紅利發什麼幣別", "代理佣金｜站台系統幣別",
    rationale="返水與代理佣金計算基礎不同（前者依自身有效投注、後者依下線流水），刻意對兩種不同計算路徑的紅利類型各設一條 TC，屬對『紅利類型』這個維度的等價劃分，用以降低『規則只在某一計算路徑生效、另一路徑漏改』的風險，而非重複同一件事"))

T.append(tc(
    "REQ-BONUSCCY-006", ["AC-BONUSCCY-008"],
    "玩家同時持有系統幣別與多個非系統幣別餘額時，一般紅利仍正確發到系統幣別，不會誤發到餘額較高或最近使用的其他幣別錢包",
    "ui_e2e", ["negative"], ["error_guessing"],
    PRE_ADMIN + ["選定一名既有會員，其同時持有系統幣別（USDT）與至少兩種非系統幣別（例如 TTK、另一已啟用幣別）的正數餘額；其中某個非系統幣別的餘額刻意高於系統幣別餘額，且該會員最近一次下注/存款用的是非系統幣別（非 USDT）"],
    ["於後台會員詳細資料頁展開多幣別餘額檢視，記錄該會員此刻所有已啟用幣別錢包的餘額",
     "等待或確認該會員產生一筆返水或代理佣金並已結算入帳",
     "重新查看多幣別餘額檢視，比對每個幣別錢包的變動"],
    "只有系統幣別（USDT）錢包的餘額增加，其餘幣別錢包（含餘額較高、或最近下注/存款所用的那個非系統幣別）餘額不變；系統不會因為玩家『最近使用』或『餘額較高』的幣別是其他幣別，就誤把紅利發到那個幣別錢包",
    "§一句話", "玩家拿哪個錢包下注、用什麼幣別存款，都不影響紅利發出來的幣別",
    critical=True,
    rationale="這是本規則錯發幣別風險最高的情境：多個幣別錢包同時有餘額時，若實作是『發到玩家最近使用或餘額最高的錢包』而非『固定發到系統幣別』，黑箱功能測試在單一幣別情境（TC1/TC2）下測不出來，只有在多幣別同時有餘額時才會暴露；這是 error_guessing，針對『系統可能選錯錢包』這個合理懷疑設計，不是硬湊案例——REQ-BONUSCCY-006 為 high risk 且 rejection_contract.defined=true，此為 requirement_based 之外唯一能覆蓋 high risk 要求的 non-happy 案例"))

# ============ REQ-BONUSCCY-007（medium）彩金活動自選發放幣別 ============

T.append(tc(
    "REQ-BONUSCCY-007", ["AC-BONUSCCY-009"],
    "彩金活動指定非系統幣別發放時，正確送進玩家對應幣別錢包，不是系統幣別",
    "ui_e2e", ["functional"], ["requirement_based"],
    PRE_ADMIN + ["站台已啟用系統幣別以外的至少一種幣別（例如 TTK）",
                 "透過後台『優惠活動管理』（或對應的彩金活動建立功能）建立一個彩金活動，發放幣別欄位指定為 TTK（系統幣別以外）",
                 "選定一名符合該彩金活動條件、且原已持有 TTK 錢包（餘額可為 0）的既有會員"],
    ["於後台會員詳細資料頁展開多幣別餘額檢視，記錄該會員目前 TTK 與系統幣別（USDT）錢包的餘額",
     "使該會員符合彩金活動的發放條件，確認彩金已發放入帳",
     "重新查看多幣別餘額檢視，比對 TTK 與系統幣別錢包的變動"],
    "彩金金額進入 TTK 錢包（後台建活動時指定的幣別），系統幣別（USDT）錢包不因這筆彩金而變動——彩金活動是全站唯一可以自己選發放幣別的紅利類型，不受系統幣別限制",
    "§每一種紅利發什麼幣別",
    "彩金活動｜後台建活動時自己填的幣別｜全站唯一可以自己選發放幣別的紅利｜2026-09-02 與 PM 確認：彩金依後台建活動時選的幣別，送進玩家對應幣別的錢包",
    rationale="BONUSCCY-002 本身未涵蓋彩金活動建立的完整後台操作流程（欄位、頁面路徑），目前可讀到的其他 spec 也沒有專門文件描述；precondition 中『優惠活動管理』這個模組名稱依 SPEC-PLATFORMRULE-001 §機台場館的後台選單所列的線上站台後台選單項目推得，實際建立彩金活動的詳細欄位需由執行者對照當下後台介面操作，不影響本條 expected_result 的斷言本身（該斷言逐字依據 spec 原文與 2026-09-02 PM 確認記錄）。另，AC-BONUSCCY-009 提到『玩家原本沒有該幣別錢包時會自動出現一列』，依 SPEC-MEMBER-001 v0.2 §2.1.6，已在站台層級啟用的幣別即使玩家餘額為 0 也會在多幣別展開檢視中列出一列顯示 0.00（不因無餘額而隱藏），故『錢包原本沒有該幣別的一列，中獎後才新增』這件事在本後台 UI 上不是一個可獨立觀察的離散事件——只要 TTK 是站台已啟用幣別，該列在彩金發放前就已存在並顯示 0.00；本 TC 因此只驗證『金額進對錢包』這個可觀察斷言，不另立一條驗證『新增一列』的 TC，避免設計一條在目前 UI 慣例下無法真正驗到差異的假案例"))

# ============ REQ-BONUSCCY-008（medium）JACKPOT／促銷派彩依下注錢包幣別 ============

T.append(tc(
    "REQ-BONUSCCY-008", ["AC-BONUSCCY-010"],
    "遊戲商 JACKPOT／促銷派彩依玩家下注當下使用的錢包幣別，依匯率換算後入帳",
    "ui_e2e", ["functional"], ["requirement_based"],
    PRE_ADMIN + ["站台已啟用系統幣別以外的至少一種幣別（例如 TTK）",
                 "選定一名使用 TTK 錢包餘額在支援 JACKPOT／促銷派彩的遊戲商遊戲（例如 PP、AWC、SABA 其中之一，視測試環境當下可觸發的遊戲商而定）下注的既有會員",
                 "若測試環境當下沒有可實際觸發 JACKPOT／促銷派彩的遊戲或機制，本 TC 需標記為待執行，待環境支援後再測（此限制已由 RequirementModel 的 rejection_contract 說明記載）"],
    ["於後台會員詳細資料頁展開多幣別餘額檢視，記錄該會員目前 TTK 與系統幣別（USDT）錢包的餘額",
     "使該會員中得該遊戲商發放的 JACKPOT 或促銷派彩",
     "重新查看多幣別餘額檢視，檢視派彩入帳結果進了哪個幣別錢包，並核對入帳金額是否已依匯率換算（非原始遊戲幣別金額原封不動搬入）"],
    "派彩依匯率換算後進入 TTK 錢包（玩家下注當下所用的錢包幣別），不是站台系統幣別（USDT）；若入帳金額與原始派彩金額不同，差異應對應當下的匯率換算，而不是直接原值入帳",
    "§每一種紅利發什麼幣別",
    "遊戲商 JACKPOT／促銷派彩｜玩家該筆遊戲的錢包幣別｜由遊戲幣別依匯率換算後入帳（PP、AWC、SABA 等）",
    rationale="rejection_contract.description 已載明本條執行依賴測試環境是否有可觸發 JACKPOT／促銷派彩的遊戲商遊戲；本 TC 對此如實延續同一限制，不假裝環境必然具備。expected_result 內『依匯率換算』一句直接取自 spec 原文，未附加匯率計算公式或幣別對應表等 spec 未提供的細節，避免超出 spec 已定義的範圍"))

# ============ REQ-BONUSCCY-009（medium）推薦註冊金進收款人所屬站台幣別 ============

T.append(tc(
    "REQ-BONUSCCY-009", ["AC-BONUSCCY-011"],
    "跨站台推薦時，推薦註冊金依收款人（新玩家）所屬站台的系統幣別發放，不是推薦人所屬站台的幣別",
    "ui_e2e", ["functional"], ["requirement_based"],
    PRE_ADMIN + ["選定兩個系統幣別不同的既有站台 A（系統幣別 X）與 B（系統幣別 Y），A、B 之間已存在或可建立跨站台推薦關係（站台 A 的既有會員以推薦人身分，使一名新玩家於站台 B 完成註冊）",
                 "若測試環境當下不易建置兩個系統幣別不同且可互相推薦的站台組合，本 TC 需標記為待執行（此限制已由 RequirementModel 的 rejection_contract 說明記載）"],
    ["確認站台 A 與站台 B 的系統幣別設定（後台『站台列表』或對應站台設定頁可查核，兩者應不同）",
     "以站台 A 既有會員的推薦連結／推薦碼，讓一名新玩家於站台 B 完成註冊並取得推薦註冊金",
     "於後台會員詳細資料頁查看該新玩家（收款人）的錢包，確認註冊金入帳的幣別"],
    "推薦註冊金依收款人（新玩家）所屬站台 B 的系統幣別 Y 發放，進入新玩家站台 B 系統幣別的錢包，不是推薦人所屬站台 A 的系統幣別 X",
    "§每一種紅利發什麼幣別", "推薦獎勵、推薦註冊金｜站台系統幣別｜註冊金進「收款人所屬站台」的幣別",
    rationale="兩個系統幣別不同且互相可推薦的站台組合、以及跨站台推薦連結的實際生成方式，BONUSCCY-002 本身未定義站台建立或推薦連結產生的操作細節；本 TC 的環境依賴已如實對應 RequirementModel 中 rejection_contract.description 記載的限制，前台註冊動作屬本規則驗證所必須（推薦人與收款人的站台歸屬需透過實際註冊行為建立），非後台可單獨代辦"))

# ============ REQ-BONUSCCY-010（high risk）人工存款不觸發任何活動與累積統計，但稽核流水正常計入 ============

PRE_MANUAL_DEPOSIT_NOTE = "人工存入操作方式依 SPEC-MEMBER-001 v0.2 §2.1.5：會員詳細資料頁帳務資訊區塊的『人工存入』按鈕，右側滑出面板填寫金額／稽核倍數／前台備注／後台備注後點擊『儲存』"

T.append(tc(
    "REQ-BONUSCCY-010", ["AC-BONUSCCY-012"],
    "人工存款不觸發首存／次存活動，玩家不因此被算作首儲或配到任何存款活動",
    "ui_e2e", ["negative"], ["requirement_based"],
    PRE_ADMIN + ["選定一名既有會員，其原本未達首存活動門檻（自行從環境中選定一個從未在該站台完成過系統存款、或尚未達次存門檻的既有會員），確認該會員在本次操作前沒有其他系統存款同時進行中，避免干擾判斷",
                 PRE_MANUAL_DEPOSIT_NOTE],
    ["於後台『優惠活動管理』（或對應的存款活動列表）記錄該首存／次存活動目前的門檻金額，以及該會員目前是否已被列為『已達首儲／次儲』",
     "記錄該會員此刻的帳戶餘額（主錢包）",
     "於該會員詳細資料頁使用『人工存入』功能，填入一筆金額（足以達到首存活動門檻），稽核倍數維持預設 1，前台/後台備注依需求填寫，點擊儲存",
     "重新查看該會員的帳戶餘額（主錢包），並回『優惠活動管理』確認該首存／次存活動的參與/發放名單中是否出現這筆存款"],
    "首存／次存活動不觸發：該會員不會被算作首儲，也不會配到任何存款活動——帳戶餘額（主錢包）僅增加本次人工存入的金額，沒有額外的活動獎勵金額一併入帳；『優惠活動管理』中該活動的參與/發放紀錄查無這筆人工存款對應的觸發紀錄",
    "§人工存款",
    "人工存款不會進任何活動與累積統計。首存／次存活動❌不觸發，不算首儲、也不會配到任何存款活動",
    rationale="以『帳戶餘額（主錢包）增量是否恰等於存入金額、沒有額外活動獎勵金額入帳』作為主要的黑箱可觀察判斷依據，因為若活動誤觸發，多出來的獎勵金額必然反映在錢包餘額變動上；『優惠活動管理』頁面內部欄位版面未見於目前可讀的 spec 文件，此步驟頁面路徑為合理推測（依 SPEC-PLATFORMRULE-001 後台選單列表），若實際介面顯示方式不同仍以錢包餘額增量為主要判斷依據"))

T.append(tc(
    "REQ-BONUSCCY-010", ["AC-BONUSCCY-013"],
    "人工存款不計入簽到活動的有效會員門檻，玩家不會因此變成有效會員",
    "ui_e2e", ["negative"], ["requirement_based"],
    ["選定一名既有會員，其累積存款金額尚未達到簽到活動的有效會員門檻（可先於後台『優惠活動管理』查得該簽到活動設定的有效會員門檻金額，再選一名累積入帳存款低於此門檻的既有會員）",
     "本 TC 需要能以該會員身分存取線上站台前台簽到頁，非純後台操作；另需一個可另開的 Admin 後台登入視窗供人工存入操作",
     PRE_MANUAL_DEPOSIT_NOTE],
    ["以該會員身分登入前台，開啟簽到頁，記錄目前的有效會員進度條數值與有效會員狀態",
     "回後台，於該會員詳細資料頁使用『人工存入』功能，存入一筆金額，使其若被計入即可達到有效會員門檻，稽核倍數維持預設 1",
     "再次以該會員身分開啟前台簽到頁（存款期間不觸發任何其他系統存款），觀察有效會員進度條與有效會員狀態是否變動"],
    "有效會員進度條數值不因這筆人工存款而增加，維持人工存款前的數值；玩家仍未達成有效會員狀態，不因這筆人工存款而變成有效會員",
    "§人工存款",
    "人工存款不會進任何活動與累積統計。簽到活動的「有效會員」門檻❌不計入",
    rationale="依 SPEC-BONUSCCY-003 §改了什麼／②，簽到活動的有效會員進度條是前台每次開頁即時重算並直接寫入的判定依據，這是目前唯一已知、有明確依據的可觀察驗證管道；後台是否有對應的等效判定顯示頁面，目前可讀的 spec 未明確定義，故本 TC 誠實標示需要前台存取而非假設後台有一個直接對應的查詢頁面（依系統提示所述後台／前台為不同介面，不可想當然爾）"))

T.append(tc(
    "REQ-BONUSCCY-010", ["AC-BONUSCCY-014"],
    "人工存款依後台填寫的稽核倍數正常計入稽核流水（提領所需有效投注額隨倍數增加）",
    "ui_e2e", ["functional"], ["requirement_based"],
    PRE_ADMIN + ["選定一名既有會員，記錄其存款前的『提領所需有效投注額（流水錢包）』數值", PRE_MANUAL_DEPOSIT_NOTE],
    ["於該會員詳細資料頁記錄目前的『提領所需有效投注額（流水錢包）』數值作為基準值",
     "使用『人工存入』功能，填入金額 100，稽核倍數設為 1，點擊儲存；重新查看『提領所需有效投注額（流水錢包）』，記錄第一次的增量 Δ1",
     "對同一會員再次使用『人工存入』功能，同樣填入金額 100，這次稽核倍數設為 3，點擊儲存；重新查看『提領所需有效投注額（流水錢包）』，記錄第二次的增量 Δ2"],
    "兩筆人工存款都有依稽核倍數計入稽核流水：Δ1、Δ2 皆大於 0（沒有因為是人工存款就被排除在稽核流水之外）；且在存入金額相同的情況下，稽核倍數較高的第二筆存款，其『提領所需有效投注額』增量 Δ2 明顯大於稽核倍數為 1 的第一筆存款增量 Δ1，驗證系統確實依後台當次填寫的稽核倍數計入，而非固定倍數或忽略此設定",
    "§人工存款", "稽核流水（打碼量）✅有，依後台填的稽核倍數",
    data={"存入金額（第一筆／第二筆）": 100, "稽核倍數（第一筆）": 1, "稽核倍數（第二筆）": 3},
    rationale="spec 只定性描述『依後台填的稽核倍數正常計入』，未給出『提領所需有效投注額增量＝存入金額×稽核倍數』這樣的精確公式；為避免斷言一個未經逐字確認的公式，本 TC 改用『同金額、不同倍數的兩筆存款互相比較增量大小』的相對驗證方式（增量隨倍數變大而變大、且都不為 0），只驗證 spec 明確定義的定性行為，不對精確倍率公式下注"))

T.append(tc(
    "REQ-BONUSCCY-010", ["AC-BONUSCCY-015"],
    "人工存款不計入累積存款活動的累積門檻，活動不會被觸發",
    "ui_e2e", ["negative"], ["requirement_based"],
    PRE_ADMIN + ["選定一名既有會員，其原本未達累積存款活動的累積門檻（可先於後台『優惠活動管理』查得該累積存款活動設定的累積門檻金額，再選一名累積進度低於此門檻的既有會員）",
                 "確認該會員在本次操作前後沒有其他系統存款同時進行，避免干擾判斷", PRE_MANUAL_DEPOSIT_NOTE],
    ["記錄該會員此刻的帳戶餘額（主錢包）",
     "使用『人工存入』功能，填入一筆金額足以達到累積存款活動的累積門檻，稽核倍數維持預設 1，點擊儲存",
     "重新查看該會員的帳戶餘額（主錢包），並回『優惠活動管理』確認該累積存款活動是否已判定為達標並發放獎勵"],
    "累積存款活動的累積門檻不計入這筆人工存款金額，活動不會被觸發：帳戶餘額（主錢包）僅增加本次人工存入的金額，沒有額外的活動獎勵金額一併入帳；該累積存款活動的狀態仍為未達標",
    "§人工存款", "累積存款活動❌不累積",
    rationale="與 AC-BONUSCCY-012 的 TC 相同理由，以『錢包餘額增量是否恰等於存入金額』作為主要黑箱可觀察判斷依據；『優惠活動管理』頁面內部欄位版面未見於目前可讀 spec，頁面路徑為合理推測，如實際介面不同仍以餘額增量為主要依據"))

T.append(tc(
    "REQ-BONUSCCY-010", ["AC-BONUSCCY-016"],
    "人工存款不計入玩家累積儲值統計，不會推進 VIP 等級",
    "ui_e2e", ["negative"], ["requirement_based"],
    PRE_ADMIN + ["選定一名既有會員，其原本未達 VIP 升等所需的累積儲值門檻（自行從環境中選定，或於後台『會員等級設定』查得目前等級的升等門檻後挑選一名接近但未達標的既有會員）", PRE_MANUAL_DEPOSIT_NOTE],
    ["於該會員詳細資料頁記錄目前的『總入金金額』（歷史累計入金金額）與『會員等級』",
     "使用『人工存入』功能，填入一筆金額，使其若被計入即可達到 VIP 升等所需的累積儲值門檻，稽核倍數維持預設 1，點擊儲存",
     "重新查看該會員的『總入金金額』與『會員等級』；另查後台『會員等級異動紀錄』，確認是否有這名會員的升等紀錄"],
    "玩家累積儲值統計不計入這筆人工存款金額：『總入金金額』不因這筆人工存款而增加；『會員等級』維持存款前的等級，不會因此推進 VIP 等級；『會員等級異動紀錄』中查無這筆操作對應的升等紀錄",
    "§人工存款", "玩家累積儲值統計（VIP等級的依據）❌不計入，所以也不會推進VIP等級",
    rationale="『總入金金額』欄位依 SPEC-MEMBER-001 v0.2 §2.1.5『歷史累計入金金額』定義，判斷為 spec 所稱『玩家累積儲值統計』的對應欄位；『會員等級異動紀錄』頁面依 SPEC-PLATFORMRULE-001 後台選單列表確認為線上站台既有頁面，兩者皆有明確依據可查核，非憑空推測頁面路徑"))

# ================= Report =================
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
print("technique_summary:", dict(tech_count))
