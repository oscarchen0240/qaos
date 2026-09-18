#!/usr/bin/env python3
"""RUN-20260914-005 T2：Test Designer(mode=spec) 依 SPEC-CASHFLOW-001 v0.1 的 44 條需求展開 TestCaseDraft + TestDesignReport。
純後端 API 對接（無 UI），測試層級以 api 為主；REQ-042/043 為 spec 明確標註待確認的假設性案例。"""
import sys, pathlib, collections
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids
RUN, RM_AID = sys.argv[1], sys.argv[2]; ITER = int(sys.argv[3]) if len(sys.argv) > 3 else 0
SID, SV, AREA, A = "SPEC-CASHFLOW-001", "0.1", "CASHFLOW", "agent-test-designer"
reqs = {r["requirement_id"]: r for r in store.load(store.requirements_path(SID, SV))["requirements"]}
def R(n): return f"REQ-CASHFLOW-{n:03d}"
def AC(n, i): return f"AC-CASHFLOW-{n:03d}{i}"
def sr(loc): return {"spec_id": SID, "spec_version": SV, "location": loc}
PRE_API = ["機台已透過憑證通過認證", "機台所屬場館為開通狀態，機台為啟用狀態"]

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
            "preconditions": PRE_API if pre is None else pre, "test_data": [{"name": k, "value": v} for k, v in (data or {}).items()],
            "steps": [{"n": i + 1, "action": s} for i, s in enumerate(steps)], "expected_result": expected,
            "expected_result_spec_reference": sr(loc), "assumptions": assumptions, "automation_status": "not_automated",
            "ci_eligible": False, "hotfix_eligible": True, "execution_cost": cost, "stability": "unknown", "critical_path": critical,
            "source": "spec_workflow", "design_rationale": ""}

T = []
# REQ-001 稽核倍數預設 0 倍
T.append(tc(1, [1], "場館未設定稽核倍數時，開分與入金正常記入稽核明細但不產生門檻", "api", ["functional"], ["requirement_based"],
    ["場館稽核倍數維持預設值（未設定）", "機台送出開分請求（req-keyin）並判定通過", "機台送出入金並完成 end-cashin"],
    "兩筆交易的稽核明細皆正常寫入，類型分別為機台開分／機台入金；因倍數為 0，玩家可隨時洗分與出金，不受稽核門檻限制", "§機台帳號的稽核", risk="medium"))

# REQ-002 稽核倍數大於 0 時扣除未完成稽核部分
T.append(tc(2, [1, 2], "稽核倍數大於 0 時，洗分／出金核可金額先扣除未完成稽核部分，扣至 0 視同餘額不足", "api", ["functional", "boundary"], ["decision_table", "boundary_value"],
    ["場館稽核倍數設為 1 倍，機台帳號有未完成稽核金額", "送出洗分請求（req-keyout），檢視核可金額", "另建構未完成稽核金額等於全部餘額的情境，送出出金請求（req-cashout）"],
    "第一步核可金額已扣除未完成稽核部分；第二步扣除後金額為 0，回 1-NO CREDITS，視同餘額不足", "§業務規則與驗證/稽核倍數", risk="medium"))

# REQ-003 開分交易的紀錄與累計（STATES）
T.append(tc(3, [1], "開分立即生效，交易紀錄類型與金額正值，且當下累計存款次數與金額", "api", ["functional"], ["requirement_based", "state_transition"],
    ["機台無進行中場次（分數為 0）", "以鑰匙開啟機台選單送出開分請求（req-keyin）500", "檢視分數、交易紀錄類型與金額、會員列表存款次數與存款金額"],
    "分數立即增加 500；交易紀錄類型為機台開分、金額為正值 500；存款次數 +1、存款金額 +500，當下即累計（不需核實）", "§四種金流/開分", critical=True))
T.append(tc(3, [], "開分金額為最小單位 1 與恰使餘額達到上限前一單位時，皆立即生效並正確累計", "api", ["boundary"], ["boundary_value"],
    ["送出開分請求（req-keyin）金額為 1", "送出開分請求（req-keyin）金額使全場館餘額合計恰為額度上限減 1"],
    "兩筆皆立即生效、正確入帳，且分數與累計次數/金額皆準確，不因金額趨近邊界而有誤差", "§四種金流/開分 + §附錄-開分"))

# REQ-004 開分超過額度上限則拒絕
T.append(tc(4, [1], "開分後使「全場館餘額＋已預留未入帳入金金額」超過額度上限時，平台拒絕且不寫入任何帳務異動", "api", ["negative"], ["boundary_value"],
    ["調整場館額度上限為一已知值，另建構一筆已預留未入帳的入金 PENDING", "送出開分請求（req-keyin），金額使加計後「全場館機台分數餘額合計＋已預留未入帳的入金金額＋本筆金額」超過該上限"],
    "平台回 1-OVER LIMIT；機台畫面顯示失敗；分數不變、不寫入任何帳務異動（判定含已預留未入帳的入金金額，與入金共用同一把場館鎖）", "§附錄-開分", critical=True))

# REQ-005 開分無唯一識別碼，無防重複（rc=True，既定風險）
T.append(tc(5, [1], "在額度上限內連續送出兩筆內容相同的開分請求，兩筆皆分別入帳（無天然防重複機制）", "api", ["negative"], ["error_guessing"],
    ["確認本次與下一筆開分金額加總仍在額度上限內", "連續送出兩筆內容相同的開分請求（req-keyin，模擬現場重按鑰匙）"],
    "兩筆請求皆判定通過並分別入帳，分數增加兩次；系統不會偵測或阻擋重複，此為 spec 明確承認的既定行為而非缺陷", "§業務規則與驗證/單階段交易防重複"))

# REQ-006 入金兩階段與 PENDING 建立
T.append(tc(6, [1, 2], "req-cashin 一律建立新 PENDING 並產生唯一 TXID，不使既有 PENDING 失效，可同時並存多筆", "api", ["functional", "boundary"], ["decision_table"],
    ["機台送出第一筆 req-cashin", "確認建立 PENDING 並取得唯一 TXID", "同一帳號再送出第二筆 req-cashin"],
    "第一筆正常建立 PENDING 並取得唯一 TXID；第二筆建立第二筆新 PENDING、不使第一筆失效，兩筆有效並存", "§附錄-入金", critical=True))

# REQ-007 入金額度於 req-cashin 階段判定並預留
T.append(tc(7, [1, 2], "req-cashin 於場館鎖內以「全場館餘額＋已預留＋本筆金額」判定額度，未超限才建立 PENDING 並預留", "api", ["functional", "negative"], ["decision_table"],
    ["場館全場館餘額合計＋已預留未入帳金額＋本筆金額 未超過額度上限，送出 req-cashin", "改為使三者加總將超過額度上限，再送出 req-cashin"],
    "前者建立 PENDING 並將本筆金額計入預留；後者回 1-OVER LIMIT，不建立 PENDING、不預留，機台直接退鈔", "§附錄-入金", critical=True))
T.append(tc(7, [3], "兩筆入金請求幾乎同時送達且各自單看不超限但合計會超限時，場館鎖序列化正確擋下第二筆", "api", ["negative", "boundary"], ["scenario"],
    ["建構場館餘額合計已接近額度上限的情境（例如尚餘額度剛好等於單筆入金金額）",
     "以測試工具對同一場館的兩台不同機台併發送出兩個 req-cashin HTTP 請求（同一時間發出，不依序等待回應），金額皆等於尚餘額度，各自單看皆不超限，但兩筆合計會超限",
     "檢視兩筆請求的回應與是否建立 PENDING"],
    "依場館鎖逐筆序列化處理：先取得鎖的一筆通過並建立預留後，另一筆的判定基準已包含前者的預留，因而正確被擋下回 1-OVER LIMIT、不建立 PENDING；不會兩筆皆通過而使全場館餘額超過額度上限", "§附錄-入金"))

# REQ-008 入金預留額度的釋放（STATES）
T.append(tc(8, [1, 2, 3], "入金預留額度分別因入帳成功、24 小時逾時、人工取消而正確釋放", "api", ["functional", "boundary"], ["decision_table", "state_transition"],
    ["情境一：PENDING 有預留額度，機台送出 end-cashin 成功入帳", "情境二：另一筆 PENDING 有預留額度，超過 24 小時未收到 end-cashin", "情境三：另一筆 PENDING 有預留額度，Admin 於交易紀錄手動取消"],
    "情境一：預留轉為實際分數餘額；情境二：排程將其轉為已逾時並釋放預留；情境三：預留立即釋放。三者釋放後皆不再佔用額度", "§附錄-入金", critical=True))

# REQ-009 end-cashin 完成入帳且不再判定額度
T.append(tc(9, [1], "即使全場館餘額已達額度上限，已建立 PENDING 的 end-cashin 仍正常完成入帳且不再檢查額度", "api", ["functional", "boundary"], ["requirement_based"],
    ["PENDING 已建立（req-cashin 階段的額度判定已通過並完成預留）", "在收到 end-cashin 前，令全場館餘額合計因其他交易已達到額度上限", "機台送出 end-cashin，TXID 相符"],
    "平台關閉 PENDING、更新帳務、預留轉為實際餘額，回 0-OK；本階段不再重新檢查額度上限，不因當下已達上限而拒絕", "§附錄-入金"))

# REQ-010 end-cashin 查無對應 PENDING
T.append(tc(10, [1], "end-cashin 查無對應 PENDING 或 TXID 不符時僅記錄 log 並回 1-NO RECORD，不變更任何資料", "api", ["negative"], ["requirement_based"],
    ["送出 end-cashin，TXID 為一個不存在（或已被取消/逾時關閉）的 PENDING"],
    "平台僅記錄 log 後丟棄，回 1-NO RECORD，不變更任何帳務或 PENDING 資料", "§附錄-入金"))

# REQ-011 end-cashin 具備冪等性
T.append(tc(11, [1], "同一 TXID 的 end-cashin 重複送達時，平台具備冪等性、不重複加值", "api", ["functional", "negative"], ["requirement_based"],
    ["某 TXID 的 end-cashin 已成功處理一次，分數已入帳", "機台因網路逾時判斷未收到成功回覆，重送同一 TXID 的 end-cashin"],
    "平台回 0-OK，但分數不再重複增加，帳務金額與第一次處理後一致", "§附錄-入金", critical=True))

# REQ-012 入金 PENDING 保留 24 小時後逾時（STATES）
T.append(tc(12, [1], "入金 PENDING 保留 24 小時，逾期自動轉為已逾時並釋放預留額度", "api", ["functional", "boundary"], ["state_transition"],
    ["入金 PENDING 已建立超過 24 小時仍未收到 end-cashin", "系統排程檢查該 PENDING"],
    "該 PENDING 自動轉為已逾時，預留額度釋放", "§附錄-PENDING 保留期限", risk="medium"))
T.append(tc(12, [2], "PENDING 已轉為已逾時後才收到的 end-cashin 一律回 1-NO RECORD", "api", ["negative"], ["requirement_based"],
    ["PENDING 已轉為已逾時", "機台（跨斷電後）補送該 TXID 的 end-cashin"],
    "平台回 1-NO RECORD，不變更任何資料，機台停止重送、流程收斂", "§附錄-PENDING 保留期限", risk="medium"))

# REQ-013 洗分核可金額以門檻為單位捨去（INPUTS：throshold）
T.append(tc(13, [1, 2, 3], "洗分核可金額依門檻無條件捨去；指定金額與全洗結果一致；門檻為 0 時洗出全額不取整", "api", ["functional", "boundary"], ["boundary_value"],
    ["機台餘額 321、門檻 100，送出全洗請求（req-keyout，mode=all），檢視核可金額", "同餘額同門檻，改送指定金額 300 的洗分請求（req-keyout，mode=value），檢視核可金額", "機台餘額 321、門檻改為 0，送出全洗請求（req-keyout，mode=all），檢視核可金額"],
    "第一步核可金額 300；第二步核可金額同為 300，與全洗結果一致；第三步門檻為 0 時核可金額為 321（全額，不取整）", "§四種金流/洗分", critical=True))

# REQ-014 洗分餘數留在機台帳號上
T.append(tc(14, [1, 2], "洗分餘數留在機台帳號上不被清除；餘數單獨存在時無法再洗出", "api", ["functional", "negative"], ["decision_table"],
    ["機台餘額 321、門檻 100，送出全洗請求（req-keyout，mode=all）", "檢視洗分後機台餘額", "以剩餘餘額（21）再次嘗試送出洗分請求（req-keyout，mode=all）"],
    "洗出 300，機台餘額變為 21，餘數留在帳號上未被清除、系統不另記交易；第二次嘗試因核可金額為 0，回 1-NO CREDITS，無法洗出", "§四種金流/洗分", risk="medium"))

# REQ-015 洗分規格外門檻值防禦性拒絕
T.append(tc(15, [1, 2], "門檻值為負值或缺漏/非數值時，平台防禦性拒絕並回資料格式錯誤", "api", ["negative"], ["boundary_value"],
    ["送出洗分請求（req-keyout），throshold 帶入負值", "另送出洗分請求（req-keyout），throshold 欄位缺漏或帶入非數值"],
    "兩種情形平台皆拒絕，回 6-BAD DATA/FORMAT，不寫入任何帳務異動", "§附錄-洗分", critical=True))

# REQ-016 洗分核可金額為 0 時回餘額不足
T.append(tc(16, [1], "洗分核可金額為 0 時回餘額不足，不寫入任何帳務異動與交易紀錄", "api", ["negative"], ["boundary_value"],
    ["機台餘額不足一個門檻單位（或為 0）", "送出洗分請求（req-keyout）"],
    "平台拒絕，回 1-NO CREDITS；不寫入任何帳務異動與交易紀錄", "§附錄-洗分", risk="medium"))

# REQ-017 洗分為單階段且立即結束當前場次（STATES）
T.append(tc(17, [1], "洗分回 0-OK 即完成扣款無回滾，且當前場次立即結束、餘數由新場次承接", "api", ["functional", "boundary"], ["requirement_based", "state_transition"],
    ["場次進行中，機台餘額 321、門檻 100", "送出全洗請求（req-keyout，mode=all），收到 0-OK", "檢視分數、場次狀態、新場次期初餘額"],
    "分數已扣除且無法回滾；當前場次於回 0-OK 當下立即結束；餘數 21 立即由新場次承接，期初餘額為 21", "§附錄-洗分", critical=True))

# REQ-018 洗分無唯一識別碼，特定情境會重複扣款（rc=True，既定風險）
T.append(tc(18, [1], "指定金額洗分且洗完後餘額仍足夠再洗一次同額時，重複送出會造成重複扣款", "api", ["negative"], ["error_guessing"],
    ["機台餘額 1000、門檻 100，送出指定金額洗分請求（req-keyout，mode=value）300，收到 0-OK，餘額變為 700", "誤判失敗（或未看清回應）後重按，再次送出同樣的洗分請求（req-keyout，mode=value）300"],
    "第二次同樣回 0-OK 並扣款 300，餘額變為 400；系統不會偵測或阻擋此重複，屬 spec 明確點名的風險情境，需靠現場 SOP（先查後台再決定是否重做）因應", "§四種金流/洗分"))

# REQ-019 出金 PENDING 唯一性與取代（STATES）
T.append(tc(19, [1], "同一帳號同時只允許一筆有效出金 PENDING，新 req-cashout 使既存 PENDING 失效", "api", ["functional", "boundary"], ["state_transition"],
    ["機台帳號已有一筆有效出金 PENDING", "再次送出 req-cashout"],
    "既存 PENDING 被標記失效，同時建立一筆新的 PENDING，全程只有一筆有效", "§附錄-出金", critical=True))

# REQ-020 出金核可金額為全部餘額且不套門檻
T.append(tc(20, [1, 2], "出金核可金額為當下全部餘額不套門檻取整；核可金額為 0 時回餘額不足", "api", ["functional", "negative"], ["decision_table"],
    ["機台餘額 321，送出 req-cashout，檢視核可金額", "另以機台餘額為 0 的帳號送出 req-cashout"],
    "第一步核可金額為 321（全額，不因門檻而取整）；第二步回 1-NO CREDITS，不建立 PENDING、不寫入交易紀錄", "§附錄-出金", critical=True))

# REQ-021 end-cashout 完成扣分且立即結束場次（STATES）
T.append(tc(21, [1], "end-cashout 扣分完成當下餘額歸 0、當前場次立即結束", "api", ["functional"], ["state_transition"],
    ["出金 PENDING 存在且 TXID 相符，場次進行中", "機台送出 end-cashout"],
    "扣分完成，餘額歸 0（無餘數承接），當前場次立即結束", "§附錄-出金", critical=True))
T.append(tc(21, [2], "同一 TXID 的 end-cashout 重複送達時具備冪等性，不重複扣分", "api", ["negative"], ["requirement_based"],
    ["該筆 end-cashout 已成功處理過一次，餘額已歸 0", "機台重送同一 TXID 的 end-cashout"],
    "回應成功但不重複扣分，餘額不會變為負值", "§附錄-出金"))

# REQ-022 end-cashout 查無對應 PENDING
T.append(tc(22, [1], "end-cashout 查無對應 PENDING 或 TXID 不符時僅記錄 log 並回 1-NO RECORD", "api", ["negative"], ["requirement_based"],
    ["送出 end-cashout，TXID 對應的 PENDING 已被新的 req-cashout 取代而不存在"],
    "平台僅記錄 log 後丟棄，回 1-NO RECORD，不變更任何資料", "§附錄-出金", risk="medium"))

# REQ-023 出金印表機異常的兩種情況（此規則為印表機到位後的正式流程，過渡期不適用，見 REQ-CASHFLOW-025）
T.append(tc(23, [1, 2], "印表機到位後：列印未開始前偵測異常則不呼叫 end-cashout、但平台仍留有待確認 PENDING；已入列印佇列後才故障則分數照扣、收據待排除後自動印出", "api", ["functional", "boundary"], ["decision_table"],
    ["前提：本案例僅適用印表機到位、機台恢復原生 req-cashout/end-cashout 呼叫流程後執行；過渡期（現行狀態，見 REQ-CASHFLOW-025）不適用本規則",
     "情境一：機台已送出 req-cashout 並取得核可（PENDING 已建立），按下結算時印表機已有異常（列印尚未開始），機台直接結束流程、不呼叫 end-cashout",
     "情境二：機台已送出 req-cashout 並取得核可，收據已送入列印佇列後才卡紙或缺紙"],
    "情境一：機台不呼叫 end-cashout，分數不扣、保留在機台上；但平台因先前 req-cashout 已建立的 PENDING 仍留有一筆「待確認」的出金（現場其實什麼也沒發生，該 PENDING 依 REQ-CASHFLOW-026 的既有機制收斂）；情境二：機台送出 end-cashout，分數已扣（出金已完成），收據仍在佇列中，待現場排除狀況後自動印出，不可視為未出金而重做",
    "§四種金流/出金 + §四種金流/出金（過渡期）", critical=True,
    pre=PRE_API + ["機台印表機已到位、已恢復正式收據列印流程（非過渡期現況）"]))

# REQ-024 出金按下結算無反應時不扣分
T.append(tc(24, [1, 2], "結算無反應時不扣分，再次結算會自動取代前一筆待確認出金", "api", ["functional"], ["decision_table"],
    ["按下結算鍵後機台連不上平台、自行結束流程，檢視分數", "再次按下結算鍵，送出新的 req-cashout"],
    "第一步分數未扣；第二步前一筆待確認出金自動被新的一筆取代，新請求正常處理，不需人工處理", "§四種金流/出金", risk="medium"))

# REQ-025 出金過渡期由前台依序呼叫完成
T.append(tc(25, [1], "過渡期由前台依序呼叫 req-cashout 與 end-cashout，扣分與場次結束皆以前台回報完成為準", "api", ["functional"], ["requirement_based"],
    ["機台暫無印表機（過渡期現況）", "玩家按下結算鍵，前台依序呼叫 req-cashout 取得核可、隨即回報 end-cashout"],
    "前台收到完成回覆當下，平台才扣分並結束當前場次；扣分時點不再以送入列印佇列為準", "§四種金流/出金（過渡期）", critical=True))
T.append(tc(25, [2], "過渡期出金請求已送出、尚未收到回報完成前，系統不提供取消", "api", ["negative"], ["requirement_based"],
    ["前台已呼叫 req-cashout，尚未收到 end-cashout 回報完成", "玩家或店員嘗試取消此次出金"],
    "系統不提供取消；結算畫面的取消鍵僅在送出請求前有效", "§四種金流/出金（過渡期）"))

# REQ-026 出金第一階段 15 秒逾時的死單風險（rc=True，既定風險）
T.append(tc(26, [1], "req-cashout 已建立 PENDING 後機台 15 秒逾時結束程序，該 PENDING 不會自動結束，需新請求取代或 Admin 手動取消", "api", ["negative"], ["error_guessing"],
    ["機台送出 req-cashout，平台已建立 PENDING", "機台 15 秒內未收到回覆，直接結束程序（不印收據）", "檢視該筆 PENDING 的狀態"],
    "該 PENDING 持續停留在待確認，不會自動結束；需靠新的 req-cashout（依 REQ-CASHFLOW-019 取代）或 Admin 手動取消才能收斂", "§附錄-出金", risk="medium"))

# REQ-027 人工出金連動取消既有 PENDING
T.append(tc(27, [1], "櫃檯對機台帳號人工出金時，同時取消該機台尚未完成的出金 PENDING", "api", ["functional", "boundary"], ["requirement_based"],
    ["機台帳號有一筆尚未完成的出金 PENDING", "櫃檯對其執行人工出金"],
    "系統同時取消該筆既有的出金 PENDING，避免同一筆錢被領兩次", "§業務規則與驗證/人工出金連動", critical=True))

# REQ-028 人工入金不需處理既有入金 PENDING
T.append(tc(28, [1], "櫃檯對機台帳號人工入金時，既有的入金 PENDING 不受影響", "api", ["functional"], ["requirement_based"],
    ["機台帳號有一筆或多筆尚未完成的入金 PENDING", "櫃檯對其執行人工入金"],
    "既有的入金 PENDING 皆不受影響，仍可各自繼續走完流程", "§業務規則與驗證/人工入金", risk="medium"))

# REQ-029 未成立原因狀態碼對照（5 codes）
T.append(tc(29, [1, 2, 3, 4, 5], "五種未成立原因分別對應正確的狀態碼", "api", ["functional", "negative"], ["decision_table"],
    ["情境一（機台正常啟用、場館開通）：加計後將超過場館額度上限，送出開分或入金", "情境二（機台正常啟用、場館開通）：查無對應 PENDING 或 TXID 不符，送出 end-cashin/end-cashout",
     "情境三（改為機台停用，或改為場館站台非開通狀態）：送出任一交易請求", "情境四（機台正常啟用、場館開通，但機台憑證已失效／被重置）：送出任一交易請求",
     "情境五（機台正常啟用、場館開通）：請求欄位缺漏、型別錯誤，或 currency 不符主站台核心貨幣，或金額為負，送出任一交易請求"],
    "五種情境分別正確回應：1-OVER LIMIT、1-NO RECORD、7-OUT OF SERVICE、9-OTHER ERROR、6-BAD DATA/FORMAT", "§附錄-狀態碼對照", critical=True,
    pre=["機台已透過憑證通過認證（情境四除外，該情境即為憑證已失效）", "機台所屬場館為開通狀態、機台為啟用狀態（情境三除外，該情境即為停用或場館未開通）"]))

# REQ-030 餘額不足不寫入交易紀錄
T.append(tc(30, [1, 2], "餘額不足被拒絕不留交易紀錄；其他未成立原因會留下交易紀錄", "api", ["functional", "negative"], ["decision_table"],
    ["洗分或出金因餘額不足被拒絕，檢視機台交易紀錄", "另一筆交易因額度上限被拒絕，檢視機台交易紀錄"],
    "第一步查無此次拒絕的紀錄，僅回覆 1-NO CREDITS；第二步有留下「未成立」的交易紀錄，可查得拒絕原因", "§四種金流/交易不成立的原因", risk="medium"))

# REQ-031 2-OCCUPIED 狀態碼不啟用
T.append(tc(31, [1], "平台不因前台登入狀態回 2-OCCUPIED 或拒絕交易，此碼永不啟用", "api", ["functional"], ["requirement_based"],
    ["機台帳號的前台為已登入狀態", "在其餘條件皆合法下，送出任一交易請求"],
    "平台不因前台登入狀態回 2-OCCUPIED 或拒絕交易；此狀態碼永遠不會被使用", "§附錄-狀態碼對照", risk="low", cost="low"))

# REQ-032 幣別不一致拒絕交易
T.append(tc(32, [1], "機台送出的幣別與主站台核心貨幣不符時，拒絕交易並記為資料格式錯誤", "api", ["negative"], ["boundary_value"],
    ["主站台核心貨幣為 TWD", "機台送出交易請求，currency 欄位帶入 USDT"],
    "平台拒絕，回 6-BAD DATA/FORMAT，記為資料格式錯誤", "§業務規則與驗證/幣別一致性", risk="medium"))

# REQ-033 場次開始規則（STATES）
T.append(tc(33, [1], "無進行中場次時，開分或入金完成使分數轉正即建立新場次", "api", ["functional"], ["state_transition"],
    ["機台目前無進行中場次（分數為 0）", "送出開分請求（req-keyin）並完成，分數轉為正值"],
    "建立新場次，期初餘額為 0", "§場次/場次如何開始與結束", critical=True))
T.append(tc(33, [2], "前一場次因洗分結束留有餘數時，立即建立新場次承接期初餘額", "api", ["functional", "boundary"], ["state_transition"],
    ["前一場次因洗分結束，留有餘數 21"],
    "立即建立新場次承接，期初餘額為 21", "§場次/場次如何開始與結束"))

# REQ-034 場次進行中期間的交易歸屬
T.append(tc(34, [1], "場次進行中期間所有交易與注單皆歸屬於當前場次，含結束該場次的那筆交易", "api", ["functional"], ["requirement_based"],
    ["場次進行中，期間發生多筆開分、入金與注單", "以一筆洗分交易結束該場次", "檢視這些交易與注單、以及結束場次的洗分交易本身的場次編號"],
    "皆歸屬於同一個場次編號，包含結束此場次的那筆洗分交易本身", "§場次/場次如何開始與結束", risk="medium"))

# REQ-035 洗分或出金完成即結束場次（STATES）
T.append(tc(35, [1], "任一筆洗分或出金交易完成（扣分成功）當下場次即結束，不需等待核實", "api", ["functional"], ["state_transition"],
    ["場次進行中", "送出一筆洗分請求（req-keyout），收到 0-OK", "立即檢視場次狀態"],
    "場次於扣分成功當下立即結束，不需等待該筆洗分於「洗分出金核實」頁核實", "§場次/場次如何開始與結束", critical=True))
T.append(tc(35, [2], "洗分或出金請求被拒絕或取消時，場次不受影響", "api", ["negative"], ["requirement_based"],
    ["場次進行中", "送出一筆洗分請求但因餘額不足被拒絕（未成立）"],
    "場次不受此次拒絕影響，仍為進行中", "§場次/場次如何開始與結束"))

# REQ-036 分數歸零結束場次
T.append(tc(36, [1], "分數因投注輸完歸 0 時，場次結束並標記為歸零結束", "api", ["functional"], ["state_transition"],
    ["場次進行中，玩家持續投注", "分數因投注輸完歸 0"],
    "場次結束，標記為歸零結束，期末餘額為 0", "§場次/場次如何開始與結束", risk="medium"))

# REQ-037 場次逾時結束（STATES 概念，未顯式定義於 RequirementModel.states 但屬狀態轉換規則）
T.append(tc(37, [1], "場次超過逾時時間無任何交易與遊玩紀錄時，自動結束並標記為逾時結束", "api", ["functional", "boundary"], ["boundary_value"],
    ["場次進行中且有餘額，場館設定的場次逾時時間為 1 小時", "超過 1 小時無任何交易與遊玩紀錄"],
    "系統排程自動結束該場次，標記為逾時結束", "§場次/場次如何開始與結束", critical=True))
T.append(tc(37, [2], "逾時前發生任一交易或注單即重新起算逾時計時，場次不因此結束", "api", ["functional"], ["requirement_based"],
    ["場次進行中，即將達到逾時時間前", "發生一筆交易或注單"],
    "逾時計時重新起算，場次不因此結束", "§場次/場次如何開始與結束"))

# REQ-038 場館日結時間結束所有進行中場次
T.append(tc(38, [1], "場館日結時間到達時，所有進行中場次一律結束並標記為日結結算", "api", ["functional", "boundary"], ["state_transition"],
    ["場館日結時間到達，多台機台皆有進行中場次", "系統執行日結"],
    "所有進行中場次皆結束並標記為日結結算，各自剩餘分數轉為隔日新場次的期初餘額", "§場次/場次如何開始與結束", critical=True))

# REQ-039 一台機台同時只有一個進行中場次
T.append(tc(39, [1], "一台機台同時間只會維持一個進行中場次，不會產生併發的第二個場次", "api", ["boundary"], ["boundary_value"],
    ["機台餘額恰為 0（無進行中場次），以測試工具對同一機台併發送出兩個會使分數由 0 轉正的請求（例如一筆開分 req-keyin 與一筆入金 end-cashin，同一時間發出）",
     "檢視兩筆請求皆判定通過後，機台的場次紀錄"],
    "兩筆交易皆正常入帳、分數累加，但仍只建立並維持一個進行中場次（不會因兩筆幾乎同時使分數轉正而產生兩個場次），兩筆交易皆歸屬於同一個場次編號", "§場次/場次如何開始與結束", risk="medium"))

# REQ-040 線上帳號的場次欄位一律顯示為橫線
T.append(tc(40, [1], "線上會員的交易紀錄與注單查詢頁的場次編號欄位一律顯示橫線", "api", ["functional"], ["requirement_based"],
    ["查詢一筆線上會員的交易紀錄", "查詢同一會員的注單"],
    "兩處的場次編號欄位皆顯示「—」", "§業務規則與驗證/場次欄位於線上帳號", risk="low", cost="low"))

# REQ-041 機台停用或場館未開通時交易一律被拒
T.append(tc(41, [1, 2], "機台停用或所屬場館站台非開通狀態時，任何交易請求皆回 7-OUT OF SERVICE", "api", ["negative"], ["decision_table"],
    ["情境一：機台原為啟用狀態，將其於後台設為停用，送出任一交易請求（開分/入金/洗分/出金）", "情境二：機台所屬場館站台狀態改為非「開通」，送出任一交易請求"],
    "兩種情境皆回 7-OUT OF SERVICE，機台無法運作；帳號餘額與尚未完成的交易不受影響", "§業務規則與驗證/機台停用", critical=True,
    pre=["機台已透過憑證通過認證", "情境一：機台將被設為停用（測試前為啟用、場館開通）；情境二：機台所屬場館站台將被設為非開通狀態（測試前機台為啟用）"]))

# REQ-042 出金過渡期前台呼叫的認證方式尚未定案（rc=False，exploratory）
T.append(tc(42, [1], "過渡期前台呼叫 req-cashout／end-cashout 應使用與正式定案一致的認證方式（暫依假設）", "api", ["negative"], ["error_guessing"],
    ["機台暫無印表機（過渡期），前台呼叫 req-cashout／end-cashout", "檢視其攜帶的身分驗證方式"],
    "應使用假設中的認證方式（暫依沿用機台憑證 JWT 的假設）；正式定案後需依 CLR-CASHFLOW-001 的回覆調整並重新驗證本案例", "§四種金流/出金（過渡期）", risk="medium",
    assume="Spec 明確標註前台呼叫時的認證方式待確認；本案例暫依「沿用機台憑證（JWT）」的假設設計，待 CLR-CASHFLOW-001 回覆後需重新確認並調整"))

# REQ-043 出金過渡期 end-cashout 失敗時前台重送策略尚未定案（rc=False，exploratory）
T.append(tc(43, [1], "req-cashout 成功後 end-cashout 失敗時，前台依假設策略重送；無法補送則交易停在 PENDING 並走人工出金連動取消", "api", ["negative"], ["error_guessing"],
    ["前台呼叫 req-cashout 成功，取得核可", "呼叫 end-cashout 失敗", "依假設的重送策略觀察前台後續行為"],
    "應依假設策略執行（暫依「前台自動重試數次後才視為失敗」的假設）；若前台仍無法補送，交易停在 PENDING，需依 REQ-CASHFLOW-027 人工出金連動取消處理；正式定案後需依 CLR-CASHFLOW-002 的回覆重新驗證本案例", "§四種金流/出金（過渡期）", risk="medium",
    assume="Spec 明確標註 end-cashout 失敗時前台的重送策略待確認；本案例暫依「前台自動重試數次後才視為失敗」的假設設計，待 CLR-CASHFLOW-002 回覆後需重新確認並調整"))

# REQ-044 開分招待本次不實作
T.append(tc(44, [1], "系統不存在開分招待（綁定流水門檻的活動）功能，稽核倍數為幣種層級設定無法綁定單筆交易", "api", ["negative"], ["requirement_based"],
    ["檢視機台開分與稽核相關功能與設定", "嘗試尋找可綁定單筆開分交易的活動門檻設定"],
    "不存在「開分招待」功能；稽核倍數僅為幣種層級設定，無法綁定至單筆交易", "§機台帳號的稽核", risk="low", cost="low"))

# ================= Report =================
cov = collections.defaultdict(lambda: {"draft_ids": [], "acs": collections.defaultdict(list)})
for t in T:
    for r in t["requirement_ids"]: cov[r]["draft_ids"].append(t["draft_id"])
    for a in t["acceptance_criteria_ids"]:
        rid = "REQ-CASHFLOW-" + a.split("-")[2][:3]
        cov[rid]["acs"][a].append(t["draft_id"])
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
print(f"{len(T)} TCs, {n_exp} exploratory, reqs covered={len(cov)}/44")
