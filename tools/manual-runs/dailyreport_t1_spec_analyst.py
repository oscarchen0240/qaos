#!/usr/bin/env python3
"""RUN-20260913-001 T1：以 Spec Analyst 角色產出 SpecAnalysis + RequirementModel（人工驅動，Phase 3 前）。"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids
RUN = sys.argv[1]; SID, SV = "SPEC-DAILYREPORT-001", "0.1"; A = "agent-spec-analyst"
spec = store.load(store.spec_dir(SID) / "spec.yaml"); H = spec["versions"][0]["content_hash"]
def sr(loc, q=""): return {"spec_id": SID, "spec_version": SV, "location": loc, "quote": q[:300]}
def req(n, title, stmt, typ, kind, loc, quote, acs, risk, rc, inputs=None, states=None, amb=None, constraints=None):
    r = {"requirement_id": f"REQ-DAILYREPORT-{n:03d}", "version": 1, "spec_id": SID, "spec_version": SV, "type": typ, "title": title, "statement": stmt,
         "acceptance_criteria": [{"ac_id": f"AC-DAILYREPORT-{n:03d}{i}", "given": g, "when": w, "then": t} for i, (g, w, t) in enumerate(acs, 1)],
         "spec_reference": sr(loc, quote), "ambiguity": amb, "risk": risk, "status": "DRAFT", "history": [], "behavior_kind": kind, "rejection_contract": rc}
    if inputs: r["inputs"] = inputs
    if states: r["states"] = states
    if constraints: r["constraints"] = constraints
    return r
RC_DEF = lambda d, loc: {"defined": True, "description": d, "spec_reference": sr(loc)}
RC_UNDEF = lambda d: {"defined": False, "description": d}
reqs = [
 req(1, "角色權限範圍", "場館日結報表依角色限制可見範圍：Admin 全部；站長 管轄範圍；操作員 自身場館。", "security", "constraint", "§功能說明/權限表",
     "場館日結報表 | 全部 | 管轄範圍 | 自身場館",
     [("以 Admin 登入", "開啟場館日結報表並切換任一站台", "可查看該站台所有場館資料"),
      ("以站長登入", "開啟場館日結報表", "只能查看自身及子站台管轄範圍內的場館資料"),
      ("以操作員登入", "開啟場館日結報表", "只能查看自身場館資料")],
     "high", RC_UNDEF("Spec 未定義越權（例如操作員切換至非自身場館）時系統的回應：拒絕、隱藏選項或回空資料")),
 req(2, "場館範圍跟隨站台切換", "頁面資料範圍由頁面標題下方的站台切換下拉選單決定，一次僅顯示所選站台，不另設場館篩選欄位。", "functional", "constraint", "§篩選器 / §業務規則-場館範圍跟隨站台切換",
     "不另設場館篩選欄位",
     [("使用者在場館日結報表", "切換站台下拉選單", "列表只顯示所選站台的場館資料，且頁面上不存在場館篩選欄位")],
     "medium", RC_DEF("不存在場館篩選欄位即為規則本身", "§篩選器")),
 req(3, "機台帳號篩選", "篩選欄「機台帳號」為文字輸入，輸入會員編號；留空表示場館全部機台。", "functional", "success", "§篩選器/機台帳號",
     "輸入會員編號；留空為場館全部機台",
     [("場館下有多台機台", "機台帳號留空並搜尋", "列表包含場館全部機台的資料"),
      ("場館下有機台帳號 ACAA00250", "輸入 ACAA00250 並搜尋", "列表只包含該機台的資料")],
     "medium", RC_UNDEF("Spec 未定義輸入不存在或非本場館的機台帳號時的回應（空列表？錯誤提示？）"),
     inputs=[{"name": "machine_account", "type": "string", "required": False, "constraints": {"note": "會員編號格式未在本包定義"}}]),
 req(4, "結算日期必填", "結算日期為日期範圍、必填；不設區間上限。", "constraint", "rejection", "§篩選器/結算日期",
     "必填；不設區間上限，與手冊其他報表一致",
     [("使用者在場館日結報表", "未填結算日期即搜尋", "系統不執行查詢（必填）"),
      ("使用者在場館日結報表", "輸入跨越一年以上的日期區間並搜尋", "系統接受並回傳資料，不因區間長度拒絕")],
     "high", RC_UNDEF("Spec 只寫「必填」，未定義未填時的提示文案或阻擋方式；亦未定義起日晚於迄日時的行為"),
     inputs=[{"name": "settle_date_from", "type": "date", "required": True}, {"name": "settle_date_to", "type": "date", "required": True, "constraints": {"note": "不設區間上限"}}]),
 req(5, "統計週期", "統計週期為下拉選單：按日（預設）／按週／按月／區間合計。按週以週一為週起；非按日時每列為該週期內各營業日的彙總。", "functional", "success", "§篩選器/統計週期",
     "按週以週一為週起；非按日時，每列為該週期內各營業日的彙總",
     [("使用者開啟頁面", "未變更統計週期", "預設為「按日」"),
      ("結算日期涵蓋 2026-09-02(三)～2026-09-10(四)", "統計週期選「按週」並搜尋", "列出兩列：週起為 2026-08-31(一) 與 2026-09-07(一) 的兩週，金額為各週內營業日合計"),
      ("結算日期涵蓋多個營業日", "統計週期選「區間合計」", "只有一列，各欄為區間內所有營業日合計")],
     "high", RC_DEF("下拉選單只能選四種之一，無非法值", "§篩選器/統計週期"),
     inputs=[{"name": "period", "type": "enum", "required": True, "constraints": {"enum": ["按日", "按週", "按月", "區間合計"]}}]),
 req(6, "統計維度", "統計維度為下拉選單：依場館彙總／依機台明細／依場次明細。「依場次明細」時統計週期僅決定查詢範圍，列表逐場次列出、不彙總。", "functional", "success", "§篩選器/統計維度",
     "「依場次明細」時統計週期僅決定查詢範圍，列表仍逐場次列出、不彙總",
     [("場館內有 3 台機台、共 10 個已結束場次", "維度選「依場館彙總」", "一列場館彙總"),
      ("同上", "維度選「依機台明細」", "3 列，每台機台一列"),
      ("同上，統計週期選「區間合計」", "維度選「依場次明細」", "10 列逐場次列出，不因週期而彙總")],
     "high", RC_DEF("下拉選單三選一", "§篩選器/統計維度"),
     inputs=[{"name": "dimension", "type": "enum", "required": True, "constraints": {"enum": ["依場館彙總", "依機台明細", "依場次明細"]}}]),
 req(7, "結算期間欄位與營業日切分", "「結算期間」欄按日顯示營業日（依場館設定的日結時間切分，UTC+0）；按週／按月／區間合計顯示該週期起訖日期。", "functional", "success", "§列表欄位/結算期間 + §業務規則/日結時間",
     "按日顯示營業日（依場館日結時間切分）",
     [("場館日結時間設為 06:00 UTC+0", "一筆交易發生在 2026-09-05 05:59 UTC+0", "計入營業日 2026-09-04"),
      ("場館日結時間設為 06:00 UTC+0", "一筆交易發生在 2026-09-05 06:00 UTC+0", "計入營業日 2026-09-05"),
      ("統計週期為按月", "查看結算期間欄", "顯示該月起訖日期")],
     "high", RC_UNDEF("Spec 未定義場館未設定日結時間時的預設值"),
     inputs=[{"name": "settle_time", "type": "datetime", "required": True, "constraints": {"format": "HH:mm UTC+0", "note": "場館設定欄位，切分營業日的邊界"}}]),
 req(8, "場次編號欄（依場次明細）", "「場次編號」欄僅在「依場次明細」維度顯示，並附開始／結束時間與場次時長；進行中場次結束時間顯示「—」、時長為累計至查詢當下。", "functional", "success", "§列表欄位/場次編號 + §背景:場次資訊",
     "僅「依場次明細」維度顯示；另附開始／結束時間與場次時長",
     [("維度為依場次明細", "查看列表", "每列有場次編號、開始時間、結束時間（UTC+0）、場次時長"),
      ("維度為依場館彙總或依機台明細", "查看列表", "不顯示場次編號欄"),
      ("有一場次仍進行中", "查看該列", "結束時間顯示「—」，場次時長為開始至查詢當下的累計")],
     "high", RC_DEF("非場次明細維度不顯示該欄", "§列表欄位/場次編號")),
 req(9, "場次數", "「場次數」於「依場館彙總」與「依機台明細」維度顯示，為當日結束的場次筆數：依機台明細＝該機台帳號當日場次數；依場館彙總＝該場館底下所有機台帳號當日場次數的加總。", "functional", "success", "§列表欄位/場次數（2026-09-03 定案）",
     "依場館彙總＝該場館底下所有機台帳號當日場次數的加總",
     [("機台 A 當日結束 3 場、機台 B 當日結束 2 場", "維度依機台明細", "A 列場次數 3、B 列場次數 2"),
      ("同上", "維度依場館彙總", "場次數 5"),
      ("機台 A 有 1 場進行中", "維度依機台明細", "進行中場次不計入場次數")],
     "high", RC_DEF("進行中場次不計（『當日結束的場次筆數』）", "§列表欄位/場次數"),
     amb={"level": "major", "description": "「當日結束的場次」是否包含狀態為「逾時結束」與「日結結算」的場次，Spec 未明示", "options": ["包含所有非進行中狀態（已結束、逾時結束、日結結算）", "僅包含「已結束」"]}),
 req(10, "現金收支金額欄定義", "開分金額＝當日開分總額；洗分金額＝當日洗分總額；進鈔金額＝當日入金總額；收據金額＝當日出金總額（收據面額合計；過渡期機台無印表機時為結算結果畫面顯示的出金金額合計）。", "functional", "success", "§列表欄位/開分~收據金額",
     "收據金額 | 當日出金總額（印出的收據面額合計；過渡期機台暫無印表機時，為結算結果畫面顯示的出金金額合計）",
     [("當日機台 A 開分 1000、洗分 300、入金 500、出金 200", "查看依機台明細", "開分 1000、洗分 300、進鈔 500、收據 200"),
      ("過渡期機台無印表機、當日出金 200", "查看收據金額", "顯示 200（取結算結果畫面出金金額）")],
     "medium", RC_DEF("純統計，無拒絕行為", "§列表欄位")),
 req(11, "核實狀態連動欄位", "已核實洗分＝當日洗分中已於「洗分出金核實」頁核實的金額合計；待核實洗分＝仍待核實的合計，不為 0 時標示提醒；已兌現＝已核實的收據金額合計；未兌現＝截至查詢當下仍待核實的收據金額合計。", "functional", "success", "§列表欄位/已核實洗分~未兌現金額",
     "待核實洗分 | ...不為 0 時標示提醒",
     [("當日洗分 300，其中 200 已核實", "查看列表", "已核實洗分 200、待核實洗分 100 且該格有提醒標示"),
      ("當日洗分全部已核實", "查看列表", "待核實洗分 0，無提醒標示"),
      ("當日收據 200，其中 150 已核銷", "查看列表", "已兌現 150、未兌現 50"),
      ("在洗分出金核實頁將一筆待核實洗分核實後", "重新搜尋報表", "已核實／待核實數字對應變動")],
     "high", RC_UNDEF("「標示提醒」的呈現方式（顏色／圖示／文字）未定義"),
     amb={"level": "minor", "description": "「標示提醒」的具體呈現方式未定義", "options": ["紅字", "圖示", "文字標籤"]}),
 req(12, "現金淨收計算", "現金淨收＝開分＋進鈔－已核實洗分－已兌現；不扣待核實洗分。", "functional", "constraint", "§列表欄位/現金淨收 + §業務規則/現金淨收計算",
     "開分 ＋ 進鈔 － 已核實洗分 － 已兌現（不扣待核實洗分）",
     [("開分 1000、進鈔 500、已核實洗分 200、待核實洗分 100、已兌現 150", "查看現金淨收", "1150（=1000+500-200-150，不扣 100）"),
      ("開分 0、進鈔 0、已核實洗分 300、已兌現 0", "查看現金淨收", "-300（允許負值）")],
     "high", RC_DEF("純計算", "§業務規則/現金淨收計算")),
 req(13, "有效投注額與損益以核心貨幣計算", "有效投注額與損益以主站台核心貨幣計算（機台場館為 TWD）；損益正值綠色、負值紅色。", "functional", "success", "§列表欄位/有效投注額、損益（2026-09-03 定案）",
     "以主站台核心貨幣計算（機台場館為 TWD）；正值綠色、負值紅色",
     [("機台場館（核心貨幣 TWD）當日投注", "查看有效投注額與損益", "數值以 TWD 表示"),
      ("當日損益為正", "查看損益欄", "綠色"), ("當日損益為負", "查看損益欄", "紅色")],
     "medium", RC_DEF("純顯示", "§列表欄位")),
 req(14, "期末餘額", "期末餘額為該日結算時點各機台分數合計；統計週期非按日時取該週期最後一個營業日結算時點的值。", "functional", "success", "§列表欄位/期末餘額 + 欄位說明附註",
     "「期末餘額」取該週期最後一個營業日結算時點的值",
     [("按日、場館有 A(期末 50)、B(期末 30)", "依場館彙總", "期末餘額 80"),
      ("按週，週內最後營業日期末合計 80、前一日 120", "依場館彙總", "期末餘額 80（非 200）")],
     "medium", RC_DEF("純統計", "§列表欄位")),
 req(15, "非按日週期的彙總規則", "統計週期非按日時：各金額與筆數欄為該週期內各營業日的合計；期末餘額取最後營業日；未兌現金額不受週期影響，一律為截至查詢當下的累計。", "functional", "constraint", "§列表欄位附註",
     "「未兌現金額」不受週期影響、一律為截至查詢當下的累計",
     [("按週，週內三個營業日開分各 100", "查看開分金額", "300"),
      ("按週，查詢當下未兌現累計 500（含週外）", "查看未兌現金額", "500，不受週期限制")],
     "high", RC_DEF("純統計", "§列表欄位附註"),
     amb={"level": "major", "description": "「未兌現金額不受週期影響」與「結算日期」篩選的關係未明：是否也不受結算日期範圍限制？", "options": ["不受結算日期限制（全期累計）", "受結算日期限制、只不受統計週期切分影響"]}),
 req(16, "列表總計與匯出 CSV", "列表底部顯示當前篩選結果的各欄總計；頁面右上角「匯出 CSV」匯出當前篩選結果。本頁為統計檢視，不提供新增／編輯／刪除／審核。", "functional", "success", "§列表欄位末段 + §操作",
     "列表底部顯示當前篩選結果的各欄總計。頁面右上角提供「匯出 CSV」",
     [("列表有多列", "查看底部", "各欄總計等於各列合計"),
      ("已搜尋出結果", "點匯出 CSV", "下載內容與當前篩選結果一致"),
      ("任何角色", "檢視頁面", "無新增／編輯／刪除／審核按鈕")],
     "medium", RC_UNDEF("Spec 未定義無資料時匯出 CSV 的行為（空檔？停用按鈕？）")),
 req(17, "場次日結強制結束", "日結時間到達時強制結束所有進行中的場次（狀態為日結結算），餘額轉為隔日新場次的期初餘額。", "functional", "state_change", "§業務規則/場次日結 + §場次資訊/場次狀態、期初餘額",
     "日結時間到達時強制結束所有進行中的場次，餘額轉為隔日新場次的期初餘額",
     [("機台 A 有進行中場次、餘額 80", "日結時間到達", "該場次狀態變為「日結結算」、結束時間＝日結時間，隔日新場次期初餘額 80"),
      ("機台 A 無進行中場次", "日結時間到達", "不產生新場次")],
     "high", RC_DEF("狀態轉換規則明確", "§業務規則/場次日結"),
     states=[{"from": "進行中", "to": "日結結算", "trigger": "日結時間到達"}, {"from": "進行中", "to": "已結束", "trigger": "洗分／出金／分數歸 0"}, {"from": "進行中", "to": "逾時結束", "trigger": "逾時（定義於開發包③）"}, {"from": "已結束", "to": "進行中", "trigger": "不可逆", "allowed": False}]),
]
for r in reqs:
    if r["rejection_contract"].get("spec_reference") is None and r["rejection_contract"]["defined"]: r["rejection_contract"]["spec_reference"] = r["spec_reference"]
rm = {"spec_id": SID, "spec_version": SV, "requirements": reqs, "traceability": [{"requirement_id": r["requirement_id"], "spec_reference": r["spec_reference"]} for r in reqs]}
sa = {"spec_id": SID, "spec_version": SV, "content_hash": H,
      "summary": "場館日結報表：依場館／機台／場次三種維度、四種統計週期，統計開分／洗分／入金／出金與核實狀態連動金額、現金淨收、投注與損益、期末餘額；權限三層；唯讀＋匯出 CSV。相依開發包③場次引擎與開發包⑤之一洗分出金核實。",
      "scope": {"in_scope": ["篩選器", "列表欄位與計算規則", "權限", "匯出 CSV", "場次日結（影響本報表分日）"], "out_of_scope": ["核實操作本身（洗分出金核實）", "場次引擎細節（開發包③）", "客戶版手冊"]},
      "requirement_ids": [r["requirement_id"] for r in reqs],
      "ambiguities": [{"requirement_id": r["requirement_id"], "ambiguity": r["ambiguity"]} for r in reqs if r["ambiguity"]],
      "constraints": [{"text": "所有時間以 UTC+0", "spec_reference": sr("§場次資訊/開始時間")}, {"text": "本包與正本 v07 重疊處以正本為準", "spec_reference": sr("拆包說明")}, {"text": "本功能未對客戶開放（INTERNAL）", "spec_reference": sr("首行標記")}],
      "edge_case_candidates": [
        {"text": "結算日期起日 = 迄日（單日）", "requirement_id": "REQ-DAILYREPORT-004", "spec_reference": sr("§篩選器/結算日期")},
        {"text": "交易剛好落在日結時間邊界（同秒）", "requirement_id": "REQ-DAILYREPORT-007", "spec_reference": sr("§業務規則/日結時間")},
        {"text": "按週且結算日期起日非週一", "requirement_id": "REQ-DAILYREPORT-005", "spec_reference": sr("§篩選器/統計週期")},
        {"text": "場館當日無任何交易（各欄為 0 或不列出？）", "requirement_id": "REQ-DAILYREPORT-016", "spec_reference": sr("§列表欄位")},
        {"text": "查詢區間內核實狀態變動（同一筆先待核實後已核實）", "requirement_id": "REQ-DAILYREPORT-011", "spec_reference": sr("§列表欄位/已核實洗分")},
        {"text": "現金淨收為負值的顯示", "requirement_id": "REQ-DAILYREPORT-012", "spec_reference": sr("§列表欄位/現金淨收")}],
      "open_questions": ["場館當日無交易時是否列出一列全 0？", "「依場次明細」是否也顯示底部總計？", "匯出 CSV 欄位順序與時區標示？"]}
def envelope(t, payload, sub, refs):
    aid = ids.artifact_id(t)
    art = {"artifact_id": aid, "artifact_type": t, "schema_version": "1.0", "version": 1, "run_id": RUN, "task_id": "T1", "iteration": 0, "created_by": A, "created_at": store.now(), "status": "DRAFT",
           "source": {"type": "SpecVersion", "ids": [f"{SID}@{SV}"]}, "references": refs, "requires_approval": None, "payload": payload}
    p = store.ROOT / "artifacts" / sub / RUN / f"{aid}.yaml"; store.save(p, art); print(p.relative_to(store.ROOT)); return p
refs = [{"entity_type": "SpecVersion", "id": SID, "version": SV}]
envelope("SpecAnalysis", sa, "spec-analysis", refs); envelope("RequirementModel", rm, "requirements", refs)
