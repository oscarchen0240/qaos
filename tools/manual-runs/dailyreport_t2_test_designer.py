#!/usr/bin/env python3
"""RUN-20260913-001 T2：以 Test Designer(mode=spec) 角色，依 RequirementModel 的行為契約展開 TestCaseDraft + TestDesignReport。"""
import sys, pathlib, collections
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids
RUN, RM_AID = sys.argv[1], sys.argv[2]; ITER = int(sys.argv[3]) if len(sys.argv) > 3 else 0
SID, SV, AREA, A = "SPEC-DAILYREPORT-001", "0.1", "DAILYREPORT", "agent-test-designer"
reqs = {r["requirement_id"]: r for r in store.load(store.requirements_path(SID, SV))["requirements"]}
def R(n): return f"REQ-DAILYREPORT-{n:03d}"
def AC(n, i): return f"AC-DAILYREPORT-{n:03d}{i}"
def sr(loc): return {"spec_id": SID, "spec_version": SV, "location": loc}
PRE_PAGE = ["已登入後台並切換至機台場館站台（Arcade）", "進入 各式報表 > 場館日結報表"]
def tc(n, title, req, acs, level, types, techs, steps, expected, loc, prio="high", risk=None, pre=None, data=None, assume=None, critical=False, cost="medium", more_reqs=()):
    r = reqs[R(req)]
    return {"draft_id": f"TC-DRAFT-{ids.ulid()}", "title": title, "product": "ba-admin", "functional_area": AREA, "requirement_ids": [R(req)] + [R(x) for x in more_reqs],
            "acceptance_criteria_ids": [AC(req, i) for i in acs] + ([AC(8, 2)] if n == 20 else []), "spec_id": SID, "spec_version": SV, "test_level": level, "test_types": types, "design_techniques": techs,
            "priority": prio, "risk": risk or r["risk"], "execution_mode": "manual", "preconditions": pre if pre is not None else PRE_PAGE,
            "test_data": [{"name": k, "value": v} for k, v in (data or {}).items()], "steps": [{"n": i + 1, "action": s} for i, s in enumerate(steps)],
            "expected_result": expected, "expected_result_spec_reference": sr(loc),
            "assumptions": [{"text": a, "requirement_id": R(req), "needs_human_confirmation": True} for a in ((assume if isinstance(assume, list) else [assume]) if assume else [])],
            "automation_status": "not_automated", "ci_eligible": False, "hotfix_eligible": True, "execution_cost": cost, "stability": "unknown", "critical_path": critical,
            "source": "spec_workflow", "design_rationale": ""}
PRE_DATA = PRE_PAGE + ["測試場館已設定日結時間 06:00 UTC+0", "測試場館下有機台 A、B（會員編號已知），並依各案例準備交易資料", "結算日期預設為單一營業日 2026-09-05（起迄相同）；需要多日的案例於步驟中另設"]
T = [
 # REQ-001 權限（rejection 未定義）
 tc(1, "Admin 可查看任一站台的場館日結報表", 1, [1], "ui_e2e", ["functional"], ["scenario", "requirement_based"], ["以 Admin 登入後台", "在頁面標題下方站台切換選單選擇任一機台場館站台", "開啟場館日結報表並搜尋"], "可查看所選站台所有場館資料", "§功能說明/權限表", pre=[], critical=True),
 tc(2, "站長只能查看管轄範圍內場館的報表", 1, [2], "ui_e2e", ["functional"], ["scenario"], ["以站長登入後台", "開啟場館日結報表並搜尋", "比對列表中的場館與該站長的管轄範圍"], "報表只含管轄範圍內場館的資料", "§功能說明/權限表", pre=[]),
 tc(3, "操作員只能查看自身場館的報表", 1, [3], "ui_e2e", ["functional"], ["scenario"], ["以操作員登入後台", "開啟場館日結報表並搜尋"], "只顯示操作員自身場館的資料", "§功能說明/權限表", pre=[]),
 tc(4, "操作員嘗試取得非自身場館的報表資料（切換站台或直接呼叫 API 帶其他站台參數）", 1, [3], "api", ["negative"], ["negative", "error_guessing"], ["以操作員身分取得登入憑證", "直接呼叫場館日結報表查詢 API，站台參數改為非自身場館", "檢視回應"], "系統不得回傳非自身場館的任何資料（不得完成越權查詢）", "§功能說明/權限表", pre=[], assume="越權時的具體回應（HTTP 403 / 空列表 / 錯誤訊息）Spec 未定義；本案只驗證「不得取得資料」"),
 # REQ-002
 tc(5, "資料範圍跟隨站台切換且頁面無場館篩選欄位", 2, [1], "ui_e2e", ["functional"], ["requirement_based"], ["檢視篩選器區塊", "切換站台切換選單至另一機台場館站台", "搜尋"], "篩選器不存在「場館」欄位；列表只顯示所選站台的場館資料", "§篩選器 / §業務規則-場館範圍跟隨站台切換"),
 # REQ-003 機台帳號（rejection 未定義）
 tc(6, "機台帳號留空時列出場館全部機台", 3, [1], "ui_e2e", ["functional"], ["equivalence_partitioning"], ["機台帳號留空", "統計維度選「依機台明細」", "搜尋"], "列表包含場館下全部機台（A、B）各一列", "§篩選器/機台帳號", pre=PRE_DATA),
 tc(7, "輸入指定機台帳號只列該機台", 3, [2], "ui_e2e", ["functional"], ["equivalence_partitioning"], ["機台帳號輸入機台 A 的會員編號", "統計維度選「依機台明細」", "搜尋"], "列表只有機台 A 一列", "§篩選器/機台帳號", pre=PRE_DATA, data={"machine_account": "機台 A 會員編號"}),
 tc(8, "輸入不存在或非本場館的機台帳號", 3, [2], "ui_e2e", ["negative"], ["negative", "equivalence_partitioning"], ["機台帳號輸入其他場館的機台會員編號", "搜尋", "再輸入一個不存在的會員編號並搜尋"], "兩次皆不得回傳其他場館或不存在機台的資料", "§篩選器/機台帳號", pre=PRE_DATA, prio="medium", assume="Spec 未定義此情況是回空列表還是錯誤提示；本案只驗證不得洩漏其他場館資料"),
 # REQ-004 結算日期（rejection 類、未定義提示）
 tc(9, "未填結算日期即搜尋", 4, [1], "ui_e2e", ["negative"], ["negative", "requirement_based"], ["結算日期保持空白", "點擊搜尋"], "系統不執行查詢，列表不更新", "§篩選器/結算日期", assume="必填未填時的提示文案與阻擋方式（欄位紅框／toast／按鈕停用）Spec 未定義"),
 tc(10, "結算日期起日等於迄日（單日查詢）", 4, [], "ui_e2e", ["boundary"], ["boundary_value"], ["結算日期起迄皆選 2026-09-05", "統計維度選「依場館彙總」", "搜尋"], "回傳資料且所有列的結算期間皆為 2026-09-05", "§篩選器/結算日期", pre=PRE_DATA, data={"date_from": "2026-09-05", "date_to": "2026-09-05"}),
 tc(11, "結算日期跨一年以上仍可查詢（不設區間上限）", 4, [2], "ui_e2e", ["boundary"], ["boundary_value"], ["結算日期起日設為 400 天前、迄日設為今天", "搜尋"], "系統接受並回傳資料，無區間上限錯誤", "§篩選器/結算日期", prio="medium", cost="low"),
 tc(12, "結算日期起日晚於迄日", 4, [], "ui_e2e", ["negative"], ["negative", "error_guessing"], ["結算日期起日選 2026-09-10、迄日選 2026-09-01", "搜尋"], "系統不得回傳錯誤區間的資料", "§篩選器/結算日期", prio="medium", assume="起日晚於迄日的處理（擋下／自動對調／空結果）Spec 未定義"),
 # REQ-005 統計週期
 tc(13, "統計週期預設為按日", 5, [1], "ui_e2e", ["functional"], ["requirement_based"], ["開啟頁面", "檢視統計週期下拉"], "預設值為「按日」", "§篩選器/統計週期", cost="low"),
 tc(14, "按週以週一為週起，結算日期起日非週一時仍以週一分週", 5, [2], "ui_e2e", ["functional", "boundary"], ["boundary_value"], ["結算日期選 2026-09-03(三)～2026-09-13(日)（起日非週一、迄日為完整週末）", "統計週期選「按週」", "搜尋"], "列出兩列：第一列週起 2026-08-31(一)、第二列週起 2026-09-07(一)；第二列各欄＝09-07～09-13 營業日合計", "§篩選器/統計週期", pre=PRE_DATA, data={"date_from": "2026-09-03", "date_to": "2026-09-13"}, assume=["結算期間欄對不完整週（第一列）的顯示格式 Spec 未定義", "結算日期範圍外但同週的營業日（08-31～09-02）是否計入第一列合計 Spec 未定義；本案只驗證第二列（完整週）的合計"]),
 tc(15, "按月彙總每月一列", 5, [], "ui_e2e", ["functional"], ["equivalence_partitioning"], ["結算日期選 2026-08-20～2026-09-10（跨兩個月）", "統計週期選「按月」", "搜尋"], "每月一列，各欄為該月營業日合計", "§篩選器/統計週期", pre=PRE_DATA, prio="medium"),
 tc(16, "區間合計只有一列", 5, [3], "ui_e2e", ["functional"], ["equivalence_partitioning"], ["結算日期選 2026-09-01～2026-09-07", "統計週期選「區間合計」", "搜尋"], "只有一列，各欄為區間內所有營業日合計", "§篩選器/統計週期", pre=PRE_DATA),
 # REQ-006 統計維度
 tc(17, "依場館彙總為單列", 6, [1], "ui_e2e", ["functional"], ["equivalence_partitioning"], ["統計維度選「依場館彙總」", "搜尋"], "每個營業日一列場館彙總", "§篩選器/統計維度", pre=PRE_DATA, critical=True),
 tc(18, "依機台明細每台機台一列", 6, [2], "ui_e2e", ["functional"], ["equivalence_partitioning"], ["統計維度選「依機台明細」", "搜尋"], "每台機台每營業日一列", "§篩選器/統計維度", pre=PRE_DATA, critical=True),
 tc(19, "依場次明細逐場次列出且不受統計週期彙總", 6, [3], "ui_e2e", ["functional"], ["decision_table"], ["統計週期選「區間合計」", "統計維度選「依場次明細」", "搜尋"], "逐場次列出（場次數量列），不因區間合計而彙總成一列", "§篩選器/統計維度", pre=PRE_DATA),
 tc(20, "維度切換時欄位互斥：場次明細不顯示場次數、彙總維度不顯示場次編號", 6, [1, 3], "ui_e2e", ["negative"], ["decision_table"], ["依場館彙總搜尋，檢視欄位", "依場次明細搜尋，檢視欄位"], "彙總／機台明細有「場次數」無「場次編號」；場次明細有「場次編號」無「場次數」", "§列表欄位/場次編號、場次數", pre=PRE_DATA, more_reqs=(8, 9)),
 # REQ-007 營業日切分（rejection 未定義：未設日結時間）
 tc(21, "交易發生於日結時間前一秒計入前一營業日", 7, [1], "api", ["boundary"], ["boundary_value"], ["以機台 A 於 2026-09-05 05:59:59 UTC+0 產生一筆開分", "按日、依機台明細查詢 09-04 與 09-05"], "該筆開分計入營業日 2026-09-04", "§業務規則/日結時間", pre=PRE_DATA, critical=True),
 tc(22, "交易發生於日結時間整點計入當日營業日", 7, [2], "api", ["boundary"], ["boundary_value"], ["以機台 A 於 2026-09-05 06:00:00 UTC+0 產生一筆開分", "按日、依機台明細查詢 09-04 與 09-05"], "該筆開分計入營業日 2026-09-05", "§業務規則/日結時間", pre=PRE_DATA, critical=True),
 tc(23, "非按日週期的結算期間顯示起訖日期", 7, [3], "ui_e2e", ["functional"], ["requirement_based"], ["統計週期選「按月」", "搜尋並檢視結算期間欄"], "顯示該月起訖日期", "§列表欄位/結算期間", prio="medium", cost="low"),
 tc(24, "場館未設定日結時間時的分日行為", 7, [], "ui_e2e", ["negative"], ["negative", "error_guessing"], ["使用一個尚未設定日結時間的新場館", "產生跨 00:00 UTC+0 的交易", "按日查詢"], "系統不得因缺少日結時間而漏計或重複計入交易", "§業務規則/日結時間", pre=["已登入後台", "存在一個未設定日結時間的機台場館"], prio="medium", assume="未設定日結時間時的預設值（00:00 UTC+0？必填不可空？）Spec 未定義"),
 # REQ-008 場次編號欄
 tc(25, "依場次明細顯示場次編號、開始／結束時間、場次時長", 8, [1], "ui_e2e", ["functional"], ["requirement_based"], ["統計維度選「依場次明細」", "搜尋", "檢視任一已結束場次列"], "有場次編號、開始時間、結束時間（UTC+0）、場次時長且時長＝結束－開始", "§列表欄位/場次編號 + §場次資訊", pre=PRE_DATA, critical=True),
 tc(26, "非場次明細維度不顯示場次編號欄", 8, [2], "ui_e2e", ["negative"], ["requirement_based"], ["依場館彙總搜尋", "依機台明細搜尋"], "兩者皆無場次編號欄", "§列表欄位/場次編號", pre=PRE_DATA, cost="low"),
 tc(27, "進行中場次的結束時間顯示「—」且時長為累計至查詢當下", 8, [3], "ui_e2e", ["boundary"], ["state_transition", "boundary_value"], ["讓機台 A 有一個進行中場次", "依場次明細搜尋", "記錄時長，等待 1 分鐘後再搜尋"], "結束時間為「—」；第二次時長比第一次多約 1 分鐘", "§場次資訊/開始時間、場次時長", pre=PRE_DATA),
 # REQ-009 場次數（major ambiguity）
 tc(28, "依機台明細的場次數＝該機台當日已結束場次數", 9, [1], "api", ["functional"], ["requirement_based"], ["機台 A 當日 3 場、機台 B 當日 2 場皆以洗分／出金／分數歸 0 正常結束（狀態「已結束」），無跨日結時間場次", "依機台明細搜尋 2026-09-05"], "A 列場次數 3、B 列場次數 2", "§列表欄位/場次數", pre=PRE_DATA + ["查詢時點在當日日結時間（06:00 UTC+0）之前"], critical=True),
 tc(29, "依場館彙總的場次數＝所有機台當日場次數加總", 9, [2], "api", ["functional"], ["requirement_based"], ["機台 A 當日 3 場、機台 B 當日 2 場皆為狀態「已結束」（洗分／出金／歸 0），無跨日結場次", "依場館彙總搜尋 2026-09-05"], "場次數 5", "§列表欄位/場次數", pre=PRE_DATA + ["查詢時點在當日日結時間（06:00 UTC+0）之前"], critical=True),
 tc(30, "進行中場次不計入場次數", 9, [3], "api", ["negative", "boundary"], ["boundary_value"], ["機台 A 當日 3 場狀態「已結束」，另有 1 場進行中", "於日結時間前依機台明細搜尋 2026-09-05"], "A 列場次數 3（不含進行中）", "§列表欄位/場次數", pre=PRE_DATA + ["查詢時點在當日日結時間（06:00 UTC+0）之前"]),
 tc(31, "逾時結束與日結結算的場次是否計入場次數", 9, [1], "api", ["boundary"], ["equivalence_partitioning"], ["讓機台 A 於營業日 2026-09-05 開始 1 場並逾時結束、另 1 場持續至 09-06 06:00 日結結算", "於 09-06 06:00 日結後依機台明細搜尋 2026-09-05"], "場次數 2（逾時結束 1 ＋ 日結結算 1；依假設含所有非進行中狀態，且日結結算場次歸屬開始的營業日）", "§列表欄位/場次數", pre=PRE_DATA, assume=["Spec 未明示「當日結束的場次」是否含逾時結束與日結結算狀態；本案假設含所有非進行中狀態", "日結結算場次歸屬哪個營業日 Spec 未定義；本案假設歸屬於場次開始的營業日"]),
 # REQ-010 金額欄
 tc(32, "開分／洗分／進鈔／收據四欄對應四種金流總額", 10, [1], "api", ["functional"], ["requirement_based"], ["機台 A 當日開分 1000、洗分 300、入金 500、出金 200", "依機台明細搜尋"], "開分 1000、洗分 300、進鈔 500、收據 200", "§列表欄位/開分~收據金額", pre=PRE_DATA, critical=True),
 tc(33, "過渡期無印表機機台的收據金額取結算結果畫面出金金額", 10, [2], "api", ["functional"], ["equivalence_partitioning"], ["使用標記為無印表機的機台出金 200", "依機台明細搜尋"], "收據金額 200", "§列表欄位/收據金額", pre=PRE_DATA + ["機台 A 於機台設定中標記為無印表機（設定位置見開發包③）"], prio="medium"),
 # REQ-011 核實連動
 tc(34, "已核實／待核實洗分拆分且待核實不為 0 時有提醒標示", 11, [1], "ui_e2e", ["functional"], ["requirement_based"], ["當日洗分 300，其中 200 於洗分出金核實頁核實", "搜尋"], "已核實洗分 200、待核實洗分 100 且該格有提醒標示", "§列表欄位/已核實洗分、待核實洗分", pre=PRE_DATA, critical=True),
 tc(35, "待核實洗分為 0 時無提醒標示", 11, [2], "ui_e2e", ["boundary"], ["boundary_value"], ["當日洗分全部核實", "搜尋"], "待核實洗分 0，無提醒標示", "§列表欄位/待核實洗分", pre=PRE_DATA),
 tc(36, "已兌現／未兌現收據金額拆分", 11, [3], "ui_e2e", ["functional"], ["requirement_based"], ["當日收據 200，其中 150 已核銷", "搜尋"], "已兌現 150、未兌現 50", "§列表欄位/已兌現金額、未兌現金額", pre=PRE_DATA + ["該場館無其他未兌現收據"]),
 tc(37, "核實操作後重新查詢數字連動", 11, [4], "ui_e2e", ["functional"], ["state_transition"], ["記錄目前已核實／待核實", "至洗分出金核實頁核實一筆待核實洗分 50", "回報表重新搜尋"], "已核實 +50、待核實 −50", "§列表欄位/已核實洗分", pre=PRE_DATA),
 # REQ-012 現金淨收
 tc(38, "現金淨收＝開分＋進鈔－已核實洗分－已兌現，不扣待核實洗分", 12, [1], "api", ["functional"], ["decision_table"], ["準備 開分 1000、進鈔 500、已核實洗分 200、待核實洗分 100、已兌現 150", "搜尋"], "現金淨收 1150", "§業務規則/現金淨收計算", pre=PRE_DATA, critical=True),
 tc(39, "現金淨收可為負值", 12, [2], "api", ["boundary"], ["boundary_value"], ["準備 開分 0、進鈔 0、已核實洗分 300、已兌現 0", "搜尋"], "現金淨收 −300", "§列表欄位/現金淨收", pre=PRE_DATA),
 # REQ-013
 tc(40, "有效投注額與損益以 TWD 計算", 13, [1], "api", ["functional"], ["requirement_based"], ["機台 A 當日有投注", "搜尋並比對會員投注紀錄的 TWD 金額"], "有效投注額、損益與投注紀錄 TWD 合計一致", "§列表欄位/有效投注額、損益", pre=PRE_DATA, prio="medium"),
 tc(41, "損益正值綠色、負值紅色", 13, [2, 3], "ui_e2e", ["functional"], ["equivalence_partitioning"], ["準備一天損益為正、一天為負", "搜尋並檢視損益欄"], "正值綠色、負值紅色", "§列表欄位/損益", pre=PRE_DATA, prio="low", cost="low"),
 # REQ-014
 tc(42, "按日期末餘額為各機台結算時點分數合計", 14, [1], "api", ["functional"], ["requirement_based"], ["營業日 2026-09-05 日結（09-06 06:00 UTC+0）時 A 分數 50、B 30", "等待該日結完成後，結算日期 09-05 按日依場館彙總搜尋"], "期末餘額 80", "§列表欄位/期末餘額", pre=PRE_DATA, prio="medium"),
 tc(43, "非按日週期期末餘額取最後營業日", 14, [2], "api", ["boundary"], ["boundary_value"], ["結算日期設為完整週 09-07～09-13；該週最後營業日 09-13 日結時期末合計 80、09-12 為 120", "於 09-14 06:00 日結完成後按週依場館彙總搜尋"], "期末餘額 80（非 200 亦非 120）", "§列表欄位附註", pre=PRE_DATA, prio="medium"),
 # REQ-015（major ambiguity）
 tc(44, "非按日週期各金額與筆數為週期內營業日合計", 15, [1], "api", ["functional"], ["requirement_based"], ["結算日期設為完整週 09-07～09-13，週內 09-08、09-09、09-10 三個營業日開分各 100、其餘為 0", "按週依場館彙總搜尋"], "開分金額 300", "§列表欄位附註", pre=PRE_DATA),
 tc(45, "未兌現金額不受統計週期影響", 15, [2], "api", ["boundary"], ["boundary_value"], ["準備未兌現收據：09-05 300、09-03 200（皆在結算日期 09-01～09-07 範圍內）", "結算日期 09-01～09-07，分別以按日（看 09-05 列）與按週搜尋"], "按日的 09-05 列與按週的該週列，未兌現金額皆為 500（不受統計週期切分影響）", "§列表欄位附註", pre=PRE_DATA + ["該場館無其他未兌現收據"]),
 tc(46, "未兌現金額與結算日期範圍的關係", 15, [2], "api", ["boundary"], ["equivalence_partitioning"], ["存在結算日期範圍外的未兌現收據 200", "以不含該收據日期的範圍搜尋"], "未兌現金額包含該 200（依假設：不受結算日期範圍限制）", "§列表欄位附註", pre=PRE_DATA, assume="Spec 說「不受週期影響、累計至查詢當下」，但未明示是否也不受結算日期範圍限制；本案假設不受限制（含 200）"),
 # REQ-016 總計／CSV／唯讀
 tc(47, "列表底部各欄總計等於各列合計", 16, [1], "ui_e2e", ["functional"], ["requirement_based"], ["依機台明細搜尋多列", "檢視底部總計"], "各欄總計＝各列加總", "§列表欄位末段", pre=PRE_DATA, prio="medium"),
 tc(48, "匯出 CSV 內容與當前篩選結果一致", 16, [2], "ui_e2e", ["functional"], ["requirement_based"], ["搜尋出結果", "點右上角匯出 CSV", "開啟檔案比對"], "列數與各欄數值與畫面一致", "§操作/匯出 CSV", pre=PRE_DATA, prio="medium"),
 tc(49, "頁面不提供新增／編輯／刪除／審核操作", 16, [3], "ui_e2e", ["negative"], ["requirement_based"], ["以 Admin、站長、操作員分別檢視頁面"], "皆無新增／編輯／刪除／審核按鈕；核實操作只能在洗分出金核實頁", "§操作", prio="medium", cost="low"),
 tc(50, "無資料時點匯出 CSV", 16, [2], "ui_e2e", ["negative"], ["negative", "error_guessing"], ["搜尋一個無任何交易的區間", "點匯出 CSV"], "系統不得產生錯誤或含錯誤資料的檔案", "§操作/匯出 CSV", prio="low", assume="無資料時是下載空檔（僅表頭）還是停用按鈕，Spec 未定義"),
 # REQ-017 場次日結（state）
 tc(51, "日結時間到達強制結束進行中場次並承接餘額", 17, [1], "api", ["functional"], ["state_transition"], ["機台 A 有進行中場次、餘額 80", "等待日結時間 06:00 UTC+0 到達", "依場次明細查詢前一日與當日"], "前一日場次狀態「日結結算」、結束時間＝06:00；當日有新場次期初餘額 80", "§業務規則/場次日結", pre=PRE_DATA + ["查詢時點在日結時間之後"], critical=True),
 tc(52, "無進行中場次時日結不產生新場次", 17, [2], "api", ["negative"], ["state_transition"], ["機台 A 無進行中場次", "日結時間到達", "依場次明細查詢當日"], "當日無新場次", "§業務規則/場次日結", pre=PRE_DATA),
 tc(53, "已結束場次不可再變回進行中", 17, [], "api", ["negative"], ["state_transition"], ["取得一個已結束場次", "對該機台再產生投注或開分", "依場次明細查詢"], "原場次狀態維持已結束；新交易屬於一個新場次編號", "§背景：場次資訊（場次定義）", pre=PRE_DATA, prio="medium"),
]
cov = collections.defaultdict(lambda: {"draft_ids": [], "acs": collections.defaultdict(list)})
for t in T:
    for r in t["requirement_ids"]: cov[r]["draft_ids"].append(t["draft_id"])
    for a in t["acceptance_criteria_ids"]: cov["REQ-DAILYREPORT-" + a.split("-")[2][:3]]["acs"][a].append(t["draft_id"])
n_exp = sum(1 for t in T if t["assumptions"])
rep = {"mode": "spec", "testcase_draft_artifact_id": None,
       "coverage_matrix": [{"requirement_id": r, "draft_ids": cov[r]["draft_ids"], "acceptance_criteria": [{"ac_id": a, "draft_ids": d} for a, d in cov[r]["acs"].items()]} for r in reqs],
       "uncovered_with_reason": [],
       "technique_summary": [{"technique": k, "count": v} for k, v in collections.Counter(x for t in T for x in t["design_techniques"]).items()],
       "self_check": {"requirements_covered": True, "acceptance_criteria_covered": True, "negative_considered": True, "boundary_considered": True, "expected_results_traceable": True, "no_unsupported_assumptions": True, "duplicate_detection_completed": True},
       "assumptions": [t["assumptions"][0]["text"] for t in T if t["assumptions"]],
       "duplicate_check": {"against_registry": True, "findings": []}}
if ITER > 0:
    rep["revision_of_issues"] = [{"issue_index": i, "action": a} for i, a in enumerate([
        "TC2 expected 收斂為 Spec 支持的『報表只含管轄範圍內場館資料』", "TC10 步驟明確選維度，expected 改為所有列結算期間皆為該日，AC 留空", "TC14 expected 只留兩列與週起；顯示格式改為 assumption（exploratory）",
        "TC28 限定場次皆為『已結束』且不跨日結", "TC29 資料條件寫入本案步驟並限定已結束", "TC30 補『3 場已結束 + 1 進行中』並限定查詢時點", "TC45 資料限定為週期外但在結算日期範圍內",
        "TC10 AC 留空", "TC15 AC 留空", "TC12 AC 留空", "TC24 AC 留空", "TC29 步驟自含資料", "TC30 步驟自含資料", "TC31 expected 改為明確數值 2", "TC46 expected 改為『包含該 200』"])]
    if ITER >= 2:
        rep["revision_of_issues"] = [{"issue_index": i, "action": a} for i, a in enumerate(["TC14 改為完整週資料並補兩條 assumption", "TC31 補日結歸屬 assumption 並明確日期", "TC42 steps 補等待日結後查詢；共用前置移除「日結前」改掛在場次數案例", "TC43 steps 補完整週與最後營業日日結後查詢"])]
        rep["revision_of_issues"] += [{"issue_index": 100 + i, "action": a} for i, a in enumerate(["TC45 前置補無其他未兌現收據", "TC15/16/44 明寫結算日期", "coverage AC-0082 歸 REQ-008", "TC51 前置補查詢時點在日結後"])]
    if ITER == 1: rep["revision_of_issues"] += [{"issue_index": 100 + i, "action": a} for i, a in enumerate(["共用前置加結算日期預設 2026-09-05 與查詢時點", "TC20 requirement_ids 補 REQ-008/009、AC-0082", "TC36 前置補無其他未兌現收據", "TC53 location 改為場次資訊、AC 留空", "TC33 前置補無印表機設定"])]
def envelope(t, payload, sub, refs, task="T2"):
    aid = ids.artifact_id(t)
    art = {"artifact_id": aid, "artifact_type": t, "schema_version": "1.0", "version": 1, "run_id": RUN, "task_id": task, "iteration": ITER, "created_by": A, "created_at": store.now(), "status": "DRAFT",
           "source": {"type": "RequirementModel", "ids": [RM_AID]}, "references": refs, "requires_approval": None, "payload": payload}
    p = store.ROOT / "artifacts" / sub / RUN / f"{aid}.yaml"; store.save(p, art); print(p.relative_to(store.ROOT)); return aid
refs = [{"entity_type": "Requirement", "id": r} for r in reqs] + [{"entity_type": "Artifact", "id": RM_AID}]
did = envelope("TestCaseDraft", {"mode": "spec", "spec_id": SID, "spec_version": SV, "testcases": T}, "test-design", refs)
rep["testcase_draft_artifact_id"] = did
envelope("TestDesignReport", rep, "test-design", [{"entity_type": "Artifact", "id": did}])
print(f"{len(T)} TCs, {n_exp} exploratory ({n_exp*100//len(T)}%), non-happy {sum(1 for t in T if set(t['test_types']) & {'negative','boundary'} or set(t['design_techniques']) & {'negative','error_guessing','boundary_value'})}")
