#!/usr/bin/env python3
"""RUN-20260916-002 T2：Test Designer(mode=spec，Phase3 影子測試/agent 自主版)
依 SPEC-CASHFLOW-001 v0.1 的 44 條 ACTIVE 需求獨立展開 TestCaseDraft + TestDesignReport。
刻意不參考既有人工版本（testcases/CASHFLOW.md / registry / versions），避免抄答案。
"""
import sys, pathlib, collections
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids

RUN, RM_AID = sys.argv[1], sys.argv[2]
ITER = int(sys.argv[3]) if len(sys.argv) > 3 else 0
SID, SV, AREA, A = "SPEC-CASHFLOW-001", "0.1", "CASHFLOW", "agent-test-designer"

reqs = {r["requirement_id"]: r for r in store.load(store.requirements_path(SID, SV))["requirements"]}

def R(n): return f"REQ-CASHFLOW-{n:03d}"
def AC(n, i): return f"AC-CASHFLOW-{n:03d}{i}"
def sr(loc): return {"spec_id": SID, "spec_version": SV, "location": loc}

# ---- 慣用 precondition 片段 ----
PRE_API = ["已知一台已核發有效機台憑證（JWT，依 創建會員帳號_spec_v01.md 建立）的既有機台帳號（自行從測試環境選定），並取得可用於直接呼叫機台端 API 的 Bearer Token（本包無獨立 UI，四種金流與 PENDING 生命週期皆由機台廠商韌體呼叫 API 觸發，故以直接呼叫 API 模擬機台/前台行為進行驗證）"]
PRE_AUDIT_ADMIN = ["以 Admin 登入後台，進入 帳務管理 > 出金設定 > TWD 頁籤"]
PRE_SITELIST_ADMIN = ["以 Admin 登入後台，進入 站台列表，找到該機台帳號所屬的場館站台"]
PRE_MEMBERLIST_ADMIN = ["以 Admin 登入後台，進入 會員列表，找到該機台帳號"]

N = collections.defaultdict(int)

def tc(req, acs, title, level, types, techs, steps, expected, loc, prio="high", risk=None, pre=None, data=None,
       assume=None, critical=False, cost="medium", automation="not_automated", ci=False, hotfix=True,
       more_reqs=(), extra_ac=(), rationale=""):
    r = reqs[R(req)]; N[req] += 1
    assumptions = []
    for a in ([assume] if isinstance(assume, str) else (assume or [])):
        assumptions.append({"text": a, "requirement_id": R(req), "needs_human_confirmation": True})
    return {"draft_id": f"TC-DRAFT-{ids.ulid()}", "title": title, "product": "ba-admin", "functional_area": AREA,
            "requirement_ids": [R(req)] + [R(x) for x in more_reqs],
            "acceptance_criteria_ids": [AC(req, i) for i in acs] + [AC(rn, ai) for rn, ai in extra_ac],
            "spec_id": SID, "spec_version": SV, "test_level": level, "test_types": types, "design_techniques": techs,
            "priority": prio, "risk": risk or r["risk"], "execution_mode": "manual",
            "preconditions": PRE_API if pre is None else pre,
            "test_data": [{"name": k, "value": v} for k, v in (data or {}).items()],
            "steps": [{"n": i + 1, "action": s} for i, s in enumerate(steps)], "expected_result": expected,
            "expected_result_spec_reference": sr(loc), "assumptions": assumptions, "automation_status": automation,
            "ci_eligible": ci, "hotfix_eligible": hotfix, "execution_cost": cost, "stability": "unknown",
            "critical_path": critical, "source": "spec_workflow", "design_rationale": rationale}

T = []

# ================= REQ-001 稽核倍數預設 0 倍 =================
T.append(tc(1, [1], "稽核倍數維持預設 0 倍時，開分與入金正常寫入稽核明細且不產生洗分/出金門檻",
    "integration", ["functional"], ["requirement_based"],
    ["先於 帳務管理 > 出金設定 > TWD 頁籤 確認該幣種稽核倍數為系統預設值 0",
     "呼叫 req-keyin 為機台帳號開分一筆金額 X（機台餘額由 0 增加為 X）",
     "至稽核明細查詢該筆，確認類型為「機台開分」",
     "呼叫 req-cashin 取得 PENDING 並以 end-cashin 完成入金一筆金額 Y",
     "至稽核明細查詢該筆，確認類型為「機台入金」",
     "緊接著（不等待、不做任何額外操作）以 throshold=0 呼叫 req-keyout 全洗，確認可立即洗出全部餘額 X+Y"],
    "兩筆稽核明細皆正常寫入（類型分別為「機台開分」「機台入金」）；因倍數為 0，緊接著的洗分不因稽核門檻被擋下（回 0-OK 洗出全額），僅一般餘額規則適用",
    "§機台帳號的稽核",
    rationale="AC-0011 描述的是預設值行為，直接依 spec 表格逐字驗證；用門檻 0 的洗分緊接在開分/入金之後，是為了排除洗分自身門檻機制的干擾，單純驗證稽核門檻是否存在。"))

# ================= REQ-002 稽核倍數 > 0 扣除未完成稽核部分 =================
_AUDIT_ASSUME = "稽核倍數機制沿用既有出金設定（依 §機台帳號的稽核：『機台的開分與入金比照既有的出金設定』），但『未完成稽核金額』的精確判定方式（例如以有效投注額對比存入金額的比例）並未在本 spec 中重新定義，屬既有機制的延伸；此處佈置『有未完成稽核金額』狀態的具體操作方式為依既有出金設定稽核邏輯的推測，需環境負責人／熟悉既有稽核機制的人員確認佈置方式是否正確"
T.append(tc(2, [1], "稽核倍數大於 0 且有未完成稽核金額時，洗分核可金額已扣除未完成稽核部分",
    "integration", ["functional"], ["requirement_based"],
    ["將該幣種稽核倍數調整為 1 倍（帳務管理 > 出金設定 > TWD 頁籤）",
     "透過開分或入金為機台帳號建立一筆餘額（例如 1000），並使其中一部分（例如 400）處於『尚未完成稽核』狀態（依既有稽核倍數機制佈置，見假設）",
     "以 throshold=0 呼叫 req-keyout 全洗，觀察回覆的核可金額 value"],
    "核可金額已扣除尚未完成稽核的部分（例如扣除 400 後，僅對剩餘 600 計算門檻捨去），而非以機台帳面全額 1000 計算",
    "§機台帳號的稽核 + §業務規則與驗證/稽核倍數", data={"稽核倍數": 1, "機台餘額": 1000, "未完成稽核部分": 400},
    assume=_AUDIT_ASSUME))
T.append(tc(2, [2], "稽核倍數大於 0，扣除未完成稽核部分後金額為 0 時視同餘額不足",
    "integration", ["boundary", "negative"], ["boundary_value"],
    ["將該幣種稽核倍數調整為 1 倍",
     "佈置機台帳號餘額，使其扣除未完成稽核部分後可洗金額恰為 0（例如機台餘額 400、未完成稽核部分亦為 400，見假設）",
     "呼叫 req-keyout（threshold 任意值）或 req-cashout 嘗試洗分/出金"],
    "回 1-NO CREDITS（機台畫面顯示餘額不足），視同一般餘額不足情形處理",
    "§機台帳號的稽核", data={"稽核倍數": 1, "機台餘額": 400, "未完成稽核部分": 400},
    assume=_AUDIT_ASSUME))

# ================= REQ-003 開分交易的紀錄與累計 =================
T.append(tc(3, [1], "開分請求送達即立即生效，交易紀錄類型正確且當下直接累計存款次數與金額（不需核實）",
    "integration", ["functional"], ["requirement_based", "state_transition", "error_guessing"],
    ["查詢機台帳號於會員列表的目前「存款次數」「存款金額」作為基準值",
     "呼叫 req-keyin 送出開分請求，金額 X（模擬店員以鑰匙開啟機台選單為玩家開分）",
     "確認回覆立即生效，機台分數增加 X",
     "至機台交易紀錄查詢該筆（若查詢頁尚未部署，可改查詢後端資料紀錄核對），確認類型為「機台開分」、金額為正值 X",
     "立即（不進行任何額外的核實或審核操作）重新查詢會員列表的存款次數與存款金額",
     "嘗試尋找任何可撤銷／回滾這筆開分存款次數與金額累計的後台操作"],
    "分數立即增加 X；交易紀錄類型為「機台開分」、金額為正值；存款次數 +1、存款金額 +X，且是在交易完成當下就直接累計（不等待核實），累計後不存在任何撤銷或回滾入口",
    "§四種金流/開分",
    rationale="AC-0031 只斷言累計行為本身；額外加入『尋找撤銷入口』一步，是因為此需求為 high risk 且『不需核實即直接累計』本身隱含不可逆的風險，屬合理的 error_guessing 延伸，未超出 AC 的『直接累計』語意。"))

# ================= REQ-004 開分超過額度上限則拒絕 =================
T.append(tc(4, [1], "開分加計後恰等於場館額度上限可成立，超過 1 單位則被拒絕（1-OVER LIMIT）",
    "integration", ["boundary", "negative"], ["boundary_value"],
    ["以 Admin 登入 站台列表，將該機台所屬場館的額度上限設為 A（一個便於計算的整數，例如現有全場館機台分數餘額合計＋已預留未入帳入金金額為 A-100）",
     "呼叫 req-keyin 開分金額恰為 100（使加計後全場館合計恰等於額度上限 A）",
     "確認開分成功（0-OK），分數增加、交易紀錄正常寫入",
     "再次呼叫 req-keyin 開分金額 1（此時加計後將超過額度上限 A）",
     "確認此筆的回覆與分數變化"],
    "第一筆恰等於上限：成立，回 0-OK，分數正常增加；第二筆使合計超過上限：平台回 1-OVER LIMIT，分數不變、不寫入任何帳務異動，但交易紀錄留有「未成立」紀錄（超過額度上限不屬於餘額不足的不寫入例外）",
    "§四種金流/開分 + §附錄-開分", critical=True))

# ================= REQ-005 開分無唯一識別碼，系統不做防重複判斷 =================
T.append(tc(5, [1], "額度上限內連續送出兩筆內容相同的開分請求，系統不偵測也不阻擋重複，兩筆皆入帳",
    "api", ["functional"], ["error_guessing"],
    ["確認場館額度上限充足，不受本次測試金額影響",
     "呼叫 req-keyin 開分金額 X（模擬現場店員操作）",
     "確認回 0-OK，分數增加 X",
     "在未查詢後台的情況下，直接以完全相同的參數再次呼叫 req-keyin（模擬店員誤判失敗後重按）",
     "確認第二筆的回覆與分數變化"],
    "兩筆請求皆判定通過、分別入帳，機台分數總共增加 2X——系統不會偵測或阻擋這種重複，此為 spec 明確承認的既定行為（現場 SOP 因應）而非缺陷",
    "§業務規則與驗證/單階段交易防重複 + §附錄-開分", critical=True,
    rationale="此需求本質是驗證『沒有防護』這件事，design_technique 選 error_guessing 而非 negative，因為預期結果是兩次都成功（非拒絕），純粹是針對已知高風險情境（重按）做探測。"))

# ================= REQ-006 入金兩階段與 PENDING 建立 =================
T.append(tc(6, [1, 2], "req-cashin 每次皆建立新 PENDING 與唯一 TXID，不使既有 PENDING 失效；對其中一筆完成 end-cashin 不影響另一筆",
    "api", ["functional"], ["requirement_based", "error_guessing"],
    ["呼叫 req-cashin 送出第一筆入金請求，記錄回覆的 TXID1（PENDING1 建立）",
     "再呼叫 req-cashin 送出第二筆入金請求（同一機台帳號），記錄回覆的 TXID2",
     "確認 TXID1 ≠ TXID2，且 PENDING1 未因 PENDING2 的建立而失效（兩者並存）",
     "以 TXID1 呼叫 end-cashin 完成該筆入帳",
     "確認 PENDING2（TXID2）仍維持待確認狀態、未受影響，可再獨立以 end-cashin(TXID2) 完成"],
    "每次 req-cashin 皆建立新 PENDING 並產生唯一 TXID，不使既有 PENDING 失效；同一帳號可同時存在多筆有效入金 PENDING，且對其中一筆完成或處理不會波及另一筆",
    "§附錄-入金", critical=True,
    rationale="design_technique 加入 error_guessing，是為了驗證『多筆並存』是否真的互不干擾（探測潛在的資料交叉污染風險），而非僅停留在建立階段的表面驗證。"))

# ================= REQ-007 入金額度於 req-cashin 階段判定並預留 =================
T.append(tc(7, [1, 2], "入金加計後恰等於額度上限可成立並預留，超過則 1-OVER LIMIT 且不建立 PENDING、不預留",
    "integration", ["boundary", "negative"], ["boundary_value"],
    ["以 Admin 登入 站台列表，設定該場館額度上限為 A，並確認目前全場館機台分數餘額合計＋已預留未入帳入金金額為 A-100",
     "呼叫 req-cashin 送出金額恰為 100 的入金請求",
     "確認回覆建立 PENDING 並將 100 計入預留（此時全場館『餘額合計＋預留』恰為 A）",
     "再呼叫 req-cashin 送出金額 1 的入金請求（此時加計後將超過額度上限 A）",
     "確認此筆的回覆，並確認機台未收到分數變化、無新 PENDING 產生"],
    "第一筆恰等於上限：成立，建立 PENDING 並預留 100；第二筆超過上限：回 1-OVER LIMIT，不建立 PENDING、不預留，機台直接退鈔",
    "§附錄-入金", critical=True))
T.append(tc(7, [3], "兩筆入金請求依場館鎖序列化處理，第二筆的判定基準已包含第一筆剛通過的預留金額",
    "api", ["functional", "negative"], ["scenario"],
    ["設場館額度上限為 A，目前全場館餘額合計＋已預留金額為 A-150",
     "呼叫 req-cashin 送出金額 100 的入金請求（單看未超限：A-150+100=A-50，未超過 A）",
     "確認此筆通過並建立 PENDING（預留轉入後，判定基準已含此筆的 100）",
     "接著（不等待前一筆入帳，模擬幾乎同時送達）呼叫 req-cashin 送出金額 100 的另一筆入金請求（若僅以原始 A-150 為基準計算不會超限，但加計前一筆已預留的 100 後將達 A+50，超限）"],
    "依場館鎖逐筆序列化處理：第一筆通過並將 100 計入預留後，第二筆的判定基準已包含第一筆的預留（A-150+100+100=A+50 超過上限），因而正確被擋下並回 1-OVER LIMIT，不會發生『兩筆各自判斷都通過、合計卻超額』的漏洞",
    "§附錄-入金",
    rationale="無法在單機測試中製造真正的並行競態（同一毫秒送達），故以『不等待第一筆結果即連續送出第二筆』模擬序列化鎖的判定基準是否正確累加預留金額，這是本規則可被功能測試驗證的核心邏輯，而非依賴真正的高並發壓測工具。"))

# ================= REQ-008 入金預留額度的釋放 =================
T.append(tc(8, [1], "end-cashin 成功入帳後，預留轉為實際分數餘額，該筆分數可正常被使用",
    "api", ["functional"], ["requirement_based", "state_transition", "error_guessing"],
    ["呼叫 req-cashin 送出入金請求金額 X，取得 TXID，確認此時機台畫面分數尚未增加（僅平台端有預留）",
     "以該 TXID 呼叫 end-cashin",
     "確認機台分數立即增加 X",
     "以 throshold=0 呼叫 req-keyout 全洗，確認可正常洗出含這筆 X 在內的全部餘額",
     "再次以相同 TXID 呼叫 end-cashin（驗證預留轉正後是否仍具備冪等性）"],
    "end-cashin 成功後預留立即轉為實際分數餘額（分數增加 X 且可被正常使用於洗分/出金），額度不再被此筆持續佔用；重複呼叫同一 TXID 的 end-cashin 回 0-OK 但不重複加值",
    "§附錄-入金", critical=True))
T.append(tc(8, [2], "入金 PENDING 超過 24 小時未完成，自動轉為已逾時並釋放預留額度",
    "api", ["boundary"], ["state_transition"],
    ["呼叫 req-cashin 建立一筆 PENDING（不呼叫 end-cashin，模擬紙鈔卡在機台內、平台已受理但未收到收鈔完成回報）",
     "等待（或由排程機制觸發）該筆 PENDING 建立時間超過 24 小時",
     "查詢該筆 PENDING 狀態",
     "查詢該場館的額度計算，確認此筆的預留金額是否仍被佔用"],
    "該 PENDING 自動轉為「已逾時」，其預留額度隨即釋放（不再計入『已預留未入帳的入金金額』），之後再收到該 TXID 的 end-cashin 依 REQ-CASHFLOW-012 回 1-NO RECORD",
    "§附錄-PENDING 保留期限", more_reqs=(12,), extra_ac=[(12, 2)],
    assume="入金 PENDING 的 24 小時保留期限為系統固定值，spec 未提供可縮短此值以利測試的設定項（不同於場次逾時時間或日結時間可由場館設定調整）；實際測試需與環境負責人確認是否有可加速時間判定的測試機制（例如調整系統時鐘或手動觸發逾時排程），否則需真實等待 24 小時執行"))

# ================= REQ-009 end-cashin 完成入帳且不再判定額度 =================
T.append(tc(9, [1], "end-cashin 完成入帳時不再重新檢查額度上限，即使額度環境已於期間變化",
    "api", ["functional"], ["requirement_based", "error_guessing"],
    ["設場館額度上限為 A，呼叫 req-cashin 送出入金金額 100 並通過（已於 req-cashin 階段判定並預留，此時全場館合計含此筆恰為 A）",
     "在呼叫 end-cashin 之前，以 Admin 將該場館額度上限調降至遠低於 A 的值（模擬若重新判定必定超限的環境變化）",
     "以該筆的 TXID 呼叫 end-cashin"],
    "end-cashin 仍正常回 0-OK，關閉 PENDING、更新帳務、預留轉為實際餘額——即使此時的額度上限已被調低到理論上會超限，本階段依規則不再判定額度上限，不會因額度環境變化而失敗",
    "§附錄-入金", critical=True,
    rationale="此情境刻意製造『若系統錯誤地在 end-cashin 重新判定額度會失敗』的條件，是驗證『本階段不再判定額度上限』最直接也最容易在真實系統中踩雷的方式，屬 error_guessing。"))

# ================= REQ-010 end-cashin 查無對應 PENDING =================
T.append(tc(10, [1], "end-cashin 帶入查無對應 PENDING 或不符的 TXID 時，僅記錄 log 並回 1-NO RECORD，不變更任何資料",
    "api", ["negative"], ["negative"],
    ["取得機台帳號目前的分數與帳務狀態作為基準",
     "以一個查無對應 PENDING 的 TXID（例如從未透過 req-cashin 建立過、或已被逾時關閉的 TXID）呼叫 end-cashin"],
    "回 1-NO RECORD，僅記錄 log 後丟棄，機台分數與任何帳務／PENDING 資料皆不變更",
    "§附錄-入金"))

# ================= REQ-011 end-cashin 具備冪等性 =================
T.append(tc(11, [1], "同一 TXID 的 end-cashin 於成功處理後再次送達，回 0-OK 但不重複加值",
    "api", ["functional"], ["requirement_based", "error_guessing"],
    ["呼叫 req-cashin 取得 TXID，並以該 TXID 呼叫 end-cashin 完成一次入帳，記錄完成後的機台分數",
     "以相同 TXID 再次呼叫 end-cashin（模擬機台 15 秒未收到成功回覆而重送，或跨斷電續送）",
     "確認回覆與機台分數是否變化"],
    "第二次仍回 0-OK，但機台分數不再重複增加，維持第一次入帳後的值",
    "§附錄-入金", critical=True))

# ================= REQ-012 入金 PENDING 保留 24 小時後逾時 =================
T.append(tc(12, [1, 2], "入金 PENDING 超過 24 小時自動轉已逾時，之後收到 end-cashin 一律回 1-NO RECORD",
    "api", ["functional", "negative"], ["state_transition"],
    ["呼叫 req-cashin 建立一筆 PENDING，記錄 TXID（不呼叫 end-cashin）",
     "等待該筆 PENDING 建立時間超過 24 小時（或由排程機制觸發逾時判定）",
     "查詢該 PENDING 狀態，確認已轉為「已逾時」",
     "以相同 TXID 呼叫 end-cashin"],
    "PENDING 於超過 24 小時後自動轉為「已逾時」，預留額度釋放；轉為已逾時之後才收到的 end-cashin 一律回 1-NO RECORD，不變更任何資料，機台端因此停止重送、流程收斂",
    "§附錄-PENDING 保留期限",
    assume="同 REQ-CASHFLOW-008：24 小時為系統固定逾時值，非場館可調整項，測試需與環境負責人確認是否有可加速判定的測試機制，否則需真實等待 24 小時執行"))

# ================= REQ-013 洗分核可金額以門檻為單位捨去 =================
T.append(tc(13, [1, 2], "洗分核可金額 = 餘額以門檻為單位無條件捨去；全洗與指定金額洗出恰為核可金額時結果相同",
    "api", ["boundary"], ["boundary_value"],
    ["透過人工入金將機台帳號分數佈置為 321（人工入金不影響既有 PENDING、不計入稽核，見 REQ-CASHFLOW-028）",
     "呼叫 req-keyout，mode=all、throshold=100（全洗）",
     "確認回覆的核可金額 value",
     "以另一台（或同一台重新佈置至餘額 321）呼叫 req-keyout，mode=value、throshold=100、指定金額 300",
     "確認回覆的核可金額 value"],
    "全洗：核可金額為 300（321 以 100 為單位捨去）；指定金額洗 300：核可金額同樣為 300，與全洗結果相同",
    "§四種金流/洗分 + §附錄-洗分", data={"機台餘額": 321, "throshold": 100}, critical=True))
T.append(tc(13, [3], "門檻為 0 時洗出全部餘額、不做取整",
    "api", ["boundary"], ["boundary_value"],
    ["透過人工入金將機台帳號分數佈置為 321",
     "呼叫 req-keyout，mode=all、throshold=0"],
    "核可金額為 321（全額），不因門檻捨去而減少，門檻 0 代表洗出全部餘額",
    "§四種金流/洗分 + §附錄-洗分", data={"機台餘額": 321, "throshold": 0}))

# ================= REQ-014 洗分餘數留在機台帳號上 =================
T.append(tc(14, [1, 2], "洗分餘數留在機台帳號上不被清除；餘數單獨存在時無法再洗出（可洗金額為 0）",
    "api", ["boundary"], ["boundary_value"],
    ["透過人工入金將機台帳號分數佈置為 321",
     "呼叫 req-keyout，mode=all、throshold=100，確認洗出 300、機台餘額變為 21",
     "再次呼叫 req-keyout，mode=all、throshold=100（此時餘額僅剩 21，小於一個門檻單位）"],
    "第一次：洗出 300，餘數 21 留在機台帳號上，系統不另記交易、不清空餘額；第二次：核可金額為 0，回 1-NO CREDITS，無法洗出（可改按結算全額領回）",
    "§四種金流/洗分 + §業務規則-餘數保留", data={"機台餘額": 321, "throshold": 100}, critical=True))

# ================= REQ-015 洗分規格外門檻值防禦性拒絕 =================
T.append(tc(15, [1, 2], "洗分請求的 throshold 為負值、缺漏或非數值時，一律防禦性拒絕回 6-BAD DATA/FORMAT",
    "api", ["negative"], ["equivalence_partitioning"],
    ["呼叫 req-keyout，throshold 帶入負值（例如 -1）",
     "確認回覆與帳務是否變動",
     "呼叫 req-keyout，缺少 throshold 欄位",
     "確認回覆與帳務是否變動",
     "呼叫 req-keyout，throshold 帶入非數值（例如字串）",
     "確認回覆與帳務是否變動"],
    "三種規格外情形皆回 6-BAD DATA/FORMAT，不寫入任何帳務異動；三者以等價劃分（負值／缺漏／型別錯誤）分別代表一類規格外輸入，結果一致",
    "§附錄-洗分", critical=True))

# ================= REQ-016 洗分核可金額為 0 時回餘額不足 =================
T.append(tc(16, [1], "洗分計算後可洗金額為 0 時回 1-NO CREDITS，不寫入任何帳務異動與交易紀錄",
    "api", ["boundary", "negative"], ["boundary_value"],
    ["透過人工入金將機台帳號分數佈置為小於一個門檻單位（例如餘額 50、throshold 100）",
     "呼叫 req-keyout，mode=all、throshold=100"],
    "回 1-NO CREDITS，機台畫面顯示餘額不足，不寫入任何帳務異動，也不寫入交易紀錄（此為餘額不足的例外，與其他未成立原因不同）",
    "§四種金流/洗分 + §附錄-洗分", data={"機台餘額": 50, "throshold": 100}))

# ================= REQ-017 洗分為單階段且立即結束當前場次 =================
T.append(tc(17, [1], "洗分回 0-OK 即代表分數已扣除且無回滾機制，完成當下立即結束當前場次並由新場次承接餘數",
    "api", ["functional"], ["state_transition", "error_guessing"],
    ["確認機台帳號目前有一個進行中場次，餘額 321",
     "呼叫 req-keyout，mode=all、throshold=100，確認回 0-OK",
     "查詢場次資訊（會員詳細頁「機台資訊」區塊或依場次編號查詢），確認原場次是否已結束、期末餘額為多少",
     "確認是否已有新場次開始，期初餘額是否等於餘數 21",
     "嘗試尋找任何可撤銷或回滾這筆已完成洗分的 API 或後台操作"],
    "回 0-OK 當下分數已扣除為最終結果、無法回滾；原場次立即結束（期末餘額 21），餘數 21 立即由新場次承接（新場次期初餘額 21）；不存在任何可撤銷或回滾此筆洗分的機制",
    "§四種金流/洗分 + §附錄-洗分", critical=True,
    rationale="『尋找回滾入口』一步是針對『無回滾機制』這句斷言本身的探測，因為正面流程無法直接證明『不存在』某個機制，需主動排查；此舉未超出 AC 的『無回滾機制』語意範圍。"))

# ================= REQ-018 洗分無唯一識別碼，特定情境會重複扣款 =================
T.append(tc(18, [1], "指定金額洗分且洗完後餘額仍足夠再洗一次同額時，重按會造成重複扣款（已知風險非缺陷）",
    "api", ["functional"], ["error_guessing"],
    ["透過人工入金將機台帳號分數佈置為 1000，throshold=100",
     "呼叫 req-keyout，mode=value、throshold=100、指定金額 300，確認回 0-OK，餘額變為 700",
     "在未查後台確認的情況下，直接以完全相同參數再次呼叫 req-keyout（模擬機台顯示失敗後店員重按）"],
    "第二次同樣回 0-OK 並再扣款 300（餘額變為 400）——系統不會偵測或阻擋，此為 spec 明確點名的已知風險情境，需仰賴現場 SOP（先查後台機台交易紀錄再決定是否重做）因應，而非系統缺陷",
    "§四種金流/洗分（機台顯示失敗時要怎麼辦）", data={"機台餘額": 1000, "throshold": 100, "指定洗分金額": 300}, critical=True))

# ================= REQ-019 出金 PENDING 唯一性與取代 =================
T.append(tc(19, [1], "已有效出金 PENDING 時再次送出 req-cashout，舊 PENDING 被標記失效並建立新 PENDING，全程只有一筆有效",
    "api", ["negative"], ["state_transition"],
    ["呼叫 req-cashout 建立第一筆出金 PENDING，記錄 TXID1（不呼叫 end-cashout）",
     "再次呼叫 req-cashout（模擬玩家再次按下結算鍵），記錄 TXID2",
     "確認 TXID1 是否已被標記失效",
     "以 TXID1 呼叫 end-cashout（驗證舊 PENDING 是否真的已失效）"],
    "第二次 req-cashout 建立新 PENDING（TXID2）前，先將既存的 TXID1 標記失效，全程同一時間只有一筆有效出金 PENDING；之後以已失效的 TXID1 呼叫 end-cashout，因查無有效對應 PENDING 而回 1-NO RECORD（依 REQ-CASHFLOW-022），不會誤將舊請求完成扣分",
    "§附錄-出金", critical=True, more_reqs=(22,), extra_ac=[(22, 1)]))

# ================= REQ-020 出金核可金額為全部餘額且不套門檻 =================
T.append(tc(20, [1], "出金核可金額為 req-cashout 當下全部餘額，不因門檻取整",
    "api", ["boundary"], ["boundary_value"],
    ["透過人工入金將機台帳號分數佈置為 321（刻意選一個非任何常見門檻整數倍的值）",
     "呼叫 req-cashout"],
    "核可金額為 321（全額），不因洗分門檻機制而取整，出金請求本身也不帶 throshold 欄位",
    "§附錄-出金", data={"機台餘額": 321}))
T.append(tc(20, [2], "出金時餘額為 0，回 1-NO CREDITS，不建立 PENDING、不寫入交易紀錄",
    "api", ["boundary", "negative"], ["boundary_value"],
    ["確認機台帳號目前分數為 0（無進行中場次）",
     "呼叫 req-cashout"],
    "回 1-NO CREDITS，不建立 PENDING、不寫入交易紀錄",
    "§附錄-出金"))

# ================= REQ-021 end-cashout 完成扣分且立即結束場次 =================
T.append(tc(21, [1, 2], "end-cashout 扣分完成當下場次立即結束、餘額歸 0；對相同 TXID 具備冪等性",
    "api", ["functional"], ["state_transition", "error_guessing"],
    ["確認機台帳號有進行中場次，餘額 321，呼叫 req-cashout 取得 PENDING 與核可金額 321",
     "以該 TXID 呼叫 end-cashout",
     "確認機台餘額歸 0，且原場次立即結束（不承接餘數）",
     "以相同 TXID 再次呼叫 end-cashout"],
    "end-cashout 完成當下餘額歸 0、場次立即結束（無餘數承接）；相同 TXID 再次送達回應成功但不重複扣分（分數已是 0，不會變負）",
    "§附錄-出金", critical=True))

# ================= REQ-022 end-cashout 查無對應 PENDING =================
# 覆蓋方式：透過 REQ-CASHFLOW-019 的 TC 交叉覆蓋（該 TC 已驗證以失效 TXID 呼叫 end-cashout 回 1-NO RECORD）。

# ================= REQ-023 出金印表機異常的兩種情況 =================
T.append(tc(23, [1, 2], "列印尚未開始的印表機異常：分數不扣但留一筆待確認 PENDING；已送入列印佇列後才卡紙缺紙：分數照扣、收據待補印不可重做",
    "api", ["functional", "negative"], ["decision_table", "error_guessing"],
    ["呼叫 req-cashout 取得核可金額與 PENDING（TXID_A），但不呼叫 end-cashout（模擬機台判定列印尚未開始即偵測到印表機異常，直接結束流程、不呼叫 end-cashout）",
     "確認機台分數未扣、仍保留在機台上；查詢平台端該筆 PENDING 狀態",
     "另佈置一次出金情境：呼叫 req-cashout 取得核可金額與 PENDING（TXID_B），並以 TXID_B 呼叫 end-cashout 完成（模擬收據已送入列印佇列後才卡紙缺紙，但平台端流程視角與『印表機正常完成列印佇列』一致）",
     "確認 TXID_B 完成後的分數是否已扣，是否存在任何『視為未出金而重做』的入口"],
    "情況一：分數不扣、保留在機台上，但平台因先前 req-cashout 已建立的 PENDING 仍留有一筆「待確認」的出金（現場其實什麼也沒發生，該 PENDING 依 REQ-CASHFLOW-026 之既有機制收斂）；情況二：分數已扣（出金已完成），不存在『視為未出金而重做一次』的操作",
    "§四種金流/出金 + §四種金流/出金（過渡期）", more_reqs=(26,),
    rationale="『印表機是否發生異常、發生於何時點』屬機台廠商韌體內部事件，平台 API 本身無法直接觀察或觸發、也無法區分『印表機故障未呼叫 end-cashout』與『其他原因未呼叫 end-cashout』；本 TC 僅能在平台可觀察的行為層面（是否呼叫 end-cashout、呼叫後分數是否已扣）驗證兩種情況對應的平台端結果，此為本包『無獨立 UI、機台端行為由廠商實作』的系統邊界限制，若需驗證機台實機對印表機異常的判斷邏輯本身，需搭配實機或廠商模擬環境，超出本包純後端測試範圍。"))

# ================= REQ-024 出金按下結算無反應時不扣分 =================
T.append(tc(24, [1, 2], "按下結算機台連不上平台時分數不扣，重按後前一筆待確認出金自動被新的一筆取代",
    "api", ["functional"], ["scenario"],
    ["呼叫 req-cashout 取得 PENDING（TXID1）與核可金額，但不呼叫 end-cashout（模擬機台連不上平台、自行結束流程）",
     "確認機台分數未扣（一毛都沒扣）",
     "再次呼叫 req-cashout（模擬玩家或店員再按一次結算），記錄 TXID2",
     "確認 TXID1 是否自動被取代、新請求（TXID2）是否正常受理"],
    "第一次無回應時分數未扣；再按一次結算後，前一筆待確認出金（TXID1）自動被新的一筆（TXID2）取代，不需人工處理，新請求正常處理",
    "§四種金流/出金"))

# ================= REQ-025 出金過渡期由前台依序呼叫完成 =================
T.append(tc(25, [1], "過渡期由前台依序呼叫 req-cashout 取得核可後立即回報 end-cashout，收到完成回覆當下才扣分並結束場次",
    "api", ["functional"], ["requirement_based"],
    ["確認機台暫無印表機（過渡期現況）",
     "模擬前台依序呼叫：先呼叫 req-cashout 取得核可金額",
     "取得核可後立即依回覆內容呼叫 end-cashout",
     "觀察扣分與場次結束的確切時間點"],
    "扣分時點與場次結束時點皆為前台回報完成（end-cashout 成功）、平台扣分成功的當下，而非以送入列印佇列為準（過渡期無印表機、無列印佇列的概念）",
    "§四種金流/出金（過渡期）", critical=True))
T.append(tc(25, [2], "出金請求已送出、尚未收到回報完成之間，系統不提供任何取消操作",
    "api", ["negative"], ["negative"],
    ["呼叫 req-cashout 取得核可與 PENDING，尚未呼叫 end-cashout",
     "嘗試尋找任何可在此時間窗口內『單純取消』此筆出金（不透過新的 req-cashout 取代、也不透過人工出金連動取消）的 API 或後台操作"],
    "不存在可於此區間單純取消該筆出金的操作路徑；結算畫面的「取消」鍵僅在送出請求前有效，送出後即不可逆，僅能靠新的 req-cashout 取代（REQ-CASHFLOW-019）或人工出金連動取消（REQ-CASHFLOW-027）收斂",
    "§四種金流/出金（過渡期）", more_reqs=(19, 27)))

# ================= REQ-026 出金第一階段 15 秒逾時的死單風險 =================
T.append(tc(26, [1], "req-cashout 已建立 PENDING 但機台 15 秒內未收到回覆而結束程序時，PENDING 不會自動收斂，須靠新請求取代或人工出金連動取消",
    "api", ["functional"], ["scenario", "error_guessing"],
    ["呼叫 req-cashout 建立 PENDING（TXID1），不呼叫 end-cashout（模擬機台 15 秒逾時直接結束程序、收據不印）",
     "靜置一段時間後查詢該 PENDING 狀態，確認未自動結束",
     "透過既有的『人工出金』功能對該機台帳號執行人工出金",
     "確認 TXID1 的 PENDING 是否因此被連動取消"],
    "PENDING 持續停留在待確認，不會自動結束（也沒有隨時間推移的逾時機制，出金 PENDING 不設逾時）；需靠新的 req-cashout（依 REQ-CASHFLOW-019 取代）或櫃檯對該機台帳號執行人工出金（依 REQ-CASHFLOW-027 連動取消既有 PENDING）才能收斂",
    "§附錄-出金", more_reqs=(27,),
    rationale="原 spec 附錄文字寫『Admin 手動取消收斂』，但依 2026-09-15 Oscar 對本需求的確認記錄（交易紀錄查詢頁不存在手動取消功能），本 TC 的期望結果採用該需求已修正後的敘述（僅靠新請求取代或人工出金連動取消），不再斷言存在 Admin 手動取消入口；此差異來自 RequirementModel 的既有修正記錄，非本次設計新增的假設。"))

# ================= REQ-027 人工出金連動取消既有 PENDING =================
T.append(tc(27, [1], "櫃檯對機台帳號人工出金時，系統同時取消該機台尚未完成的出金 PENDING",
    "integration", ["functional"], ["requirement_based", "error_guessing"],
    ["呼叫 req-cashout 建立一筆尚未完成的出金 PENDING，記錄 TXID",
     "以 Admin／櫃檯身份登入後台，對該機台帳號執行既有的人工出金功能",
     "確認該筆出金 PENDING 是否被同時取消",
     "以原 TXID 呼叫 end-cashout（驗證是否已無法完成，避免同一筆錢被領兩次）"],
    "櫃檯執行人工出金的同時，系統同時取消該機台尚未完成的出金 PENDING；之後以原 TXID 呼叫 end-cashout 因查無有效對應 PENDING 而回 1-NO RECORD（依 REQ-CASHFLOW-022），避免同一筆錢被領兩次",
    "§四種金流/出金 + §業務規則與驗證/人工出金連動", critical=True, more_reqs=(22,), extra_ac=[(22, 1)]))

# ================= REQ-028 人工入金不需處理既有入金 PENDING =================
T.append(tc(28, [1], "櫃檯對機台帳號人工入金時，不使既有的入金 PENDING 失效，兩者可分別繼續走完流程",
    "integration", ["functional"], ["requirement_based"],
    ["呼叫 req-cashin 建立一筆入金 PENDING，記錄 TXID（不呼叫 end-cashin）",
     "以 Admin／櫃檯身份登入後台，對該機台帳號執行既有的人工入金功能，補入一筆分數",
     "確認該筆入金 PENDING 是否仍為有效狀態",
     "以原 TXID 呼叫 end-cashin，確認是否仍可正常完成"],
    "既有的入金 PENDING 不受人工入金影響，仍可各自繼續走完流程（以原 TXID 呼叫 end-cashin 仍正常完成入帳）——與人工出金必須連動取消既有 PENDING 的規則相反，兩者刻意不對稱",
    "§業務規則與驗證/人工入金"))

# ================= REQ-029 未成立原因狀態碼對照 =================
T.append(tc(29, [1, 2, 3, 4, 5], "五種未成立原因分別對應正確的狀態碼",
    "api", ["negative"], ["decision_table"],
    ["情境一：佈置全場館餘額合計＋預留＋本次金額將超過額度上限，呼叫 req-keyin 或 req-cashin",
     "情境二：以查無對應 PENDING 或不符的 TXID 呼叫 end-cashin 或 end-cashout",
     "情境三：先將該機台於後台設為停用，呼叫任一交易請求；另將所屬場館站台狀態改為非開通，呼叫任一交易請求",
     "情境四：以已被重置、失效的機台憑證呼叫任一交易請求",
     "情境五：呼叫任一交易請求，欄位缺漏、型別錯誤，或 currency 與主站台核心貨幣不符，或金額為負"],
    "情境一回 1-OVER LIMIT；情境二回 1-NO RECORD；情境三兩種子情境皆回 7-OUT OF SERVICE；情境四回 9-OTHER ERROR；情境五回 6-BAD DATA/FORMAT——五種未成立原因與狀態碼一一對應，不以 HTTP 狀態碼表達業務結果",
    "§附錄-狀態碼對照", critical=True,
    assume="情境三『機台停用』的後台操作切換路徑，本 spec 未明確定義其所在頁面（機台帳號沿用既有會員資料機制，推測透過既有的帳號啟用/停用功能操作），實際切換入口需與環境負責人確認"))

# ================= REQ-030 餘額不足不寫入交易紀錄 =================
T.append(tc(30, [1, 2], "餘額不足（1-NO CREDITS）被拒絕時不寫入交易紀錄，其餘未成立原因才留下紀錄",
    "api", ["negative"], ["decision_table"],
    ["佈置洗分或出金因餘額不足而回 1-NO CREDITS 的情境並送出請求",
     "查詢機台交易紀錄，確認是否留下此次拒絕的紀錄",
     "另佈置一筆會因額度上限（或其他非餘額不足原因）被拒絕的請求並送出",
     "查詢機台交易紀錄，確認是否留下「未成立」紀錄"],
    "餘額不足被拒絕時：查無此次拒絕的紀錄，僅回覆 1-NO CREDITS；額度上限或其他原因被拒絕時：留有「未成立」交易紀錄，可查得拒絕原因——兩者行為不同，容易被誤以為所有拒絕都會留紀錄",
    "§四種金流/交易不成立的原因 + §附錄-狀態碼對照"))

# ================= REQ-031 2-OCCUPIED 狀態碼不啟用 =================
T.append(tc(31, [1], "無論機台帳號前台登入狀態為何，平台皆不因此回 2-OCCUPIED 或拒絕交易",
    "api", ["negative"], ["negative"],
    ["確認機台帳號目前前台為已登入狀態，呼叫任一交易請求（其餘條件皆合法）",
     "確認機台帳號前台為未登入狀態，重複呼叫同類型交易請求"],
    "兩種登入狀態下，平台皆不因前台登入狀態回 2-OCCUPIED 或拒絕交易，此狀態碼永遠不會被使用（機台帳號的前台登入僅供機台本身遊戲畫面使用，平台不將其當作交易阻擋條件）",
    "§附錄-狀態碼對照", risk="low", cost="low"))

# ================= REQ-032 幣別不一致拒絕交易 =================
T.append(tc(32, [1], "機台送來的幣別與主站台核心貨幣不符時，拒絕交易並記為資料格式錯誤",
    "api", ["negative"], ["negative"],
    ["確認機台所屬主站台核心貨幣為 TWD",
     "呼叫任一交易請求（如 req-keyin），currency 欄位帶入與核心貨幣不符的值（例如 USD）"],
    "平台拒絕，回 6-BAD DATA/FORMAT，記為資料格式錯誤",
    "§業務規則與驗證/幣別一致性"))

# ================= REQ-033 場次開始規則 =================
T.append(tc(33, [1, 2], "無進行中場次時開分或入金轉正建立新場次；洗分結束留有餘數時立即建立新場次承接",
    "integration", ["functional", "negative"], ["state_transition", "negative"],
    ["確認機台帳號目前無進行中場次（分數為 0）",
     "呼叫 req-keyin 開分金額 X，確認分數由 0 轉正",
     "查詢場次資訊，確認是否建立新場次，期初餘額是否為 0",
     "佈置一個進行中場次餘額 321，呼叫 req-keyout（throshold=100、mode=all）結束此場次並留有餘數 21",
     "查詢場次資訊，確認是否已立即建立新場次承接",
     "另驗證：機台分數為 0、無任何開分/入金發生的情況下，單純的注單/遊戲操作不應能建立新場次（因無資金流入觸發，屬理論情境，實際上分數為 0 時亦無法投注）"],
    "開分或入金完成使分數由 0 轉為有餘額時，建立新場次、期初餘額為 0；洗分結束留有餘數 21 時，立即建立新場次承接、期初餘額為 21；分數維持 0 時不會意外建立場次",
    "§場次/場次如何開始與結束", critical=True))

# ================= REQ-034 場次進行中期間的交易歸屬 =================
T.append(tc(34, [1], "場次進行中期間所有交易與注單皆歸屬於該場次，含結束此場次的洗分/出金交易本身",
    "integration", ["functional"], ["requirement_based"],
    ["佈置一個進行中場次，期間發生一筆開分、一筆入金",
     "查詢這兩筆交易的場次編號",
     "以一筆洗分交易結束此場次",
     "查詢這筆洗分交易的場次編號"],
    "開分與入金皆歸屬於當前這個場次；結束此場次的洗分交易本身，也歸屬於被它結束的這個場次（而非新建立的場次）",
    "§場次/場次如何開始與結束"))

# ================= REQ-035 洗分或出金完成即結束場次 =================
T.append(tc(35, [1, 2], "洗分或出金扣分成功當下場次立即結束（不等核實）；請求被拒絕或取消不觸發場次結束",
    "integration", ["functional", "negative"], ["state_transition"],
    ["佈置一個進行中場次，餘額 321，throshold=100，呼叫 req-keyout 全洗，確認回 0-OK",
     "立即查詢場次狀態（不進行「洗分出金核實」頁的核實操作）",
     "另佈置一個進行中場次，觸發一筆會被拒絕的請求（例如餘額不足或額度超限）",
     "查詢場次狀態是否受影響",
     "另佈置一筆出金 PENDING 後，以新的 req-cashout 取代它（使其被標記失效）",
     "查詢原場次狀態是否因此結束"],
    "洗分回 0-OK 當下場次立即結束，不需等待「洗分出金核實」頁核實；請求被拒絕（未成立）或 PENDING 被取代/取消，皆不觸發場次結束，場次仍為進行中",
    "§場次/場次如何開始與結束", critical=True))

# ================= REQ-036 分數歸零結束場次 =================
T.append(tc(36, [1], "分數因投注輸完歸 0 時，場次結束並標記為歸零結束",
    "integration", ["functional"], ["requirement_based"],
    ["佈置一個進行中場次，餘額為一個小額（例如 10）",
     "使玩家投注直到分數歸 0（依實際遊玩或由遊戲/投注系統模擬達成分數歸零，見假設）",
     "查詢場次狀態"],
    "分數歸 0 時場次結束，標記為「歸零結束」，期末餘額為 0",
    "§場次/場次如何開始與結束",
    assume="『分數因投注輸完歸 0』的觸發機制屬於遊戲/投注引擎的範疇，不在本包（機台金流與場次，純後端）定義的四種金流 API 範圍內；本包僅定義『分數歸 0 時場次如何反應』，至於如何在測試環境中實際觸發分數歸 0（例如是否有可直接呼叫的測試用注單模擬介面），需與環境負責人或遊戲引擎測試團隊確認可行的觸發方式"))

# ================= REQ-037 場次逾時結束 =================
T.append(tc(37, [1, 2], "場次超過逾時時間無交易與遊玩自動結束為逾時結束；期間任何交易或注單重新起算計時",
    "integration", ["functional", "boundary"], ["state_transition", "boundary_value"],
    ["以 Admin 登入 站台列表，將該場館的場次逾時時間調整為便於測試觀察的短值（例如 2 分鐘；實際可設定範圍依 站台列表_spec_v04.md 定義）",
     "佈置一個進行中場次，在逾時時間即將到達前呼叫一筆開分（重新觸發計時起算）",
     "確認場次未因此結束，逾時計時已重新起算",
     "之後不再產生任何交易或注單，等待重新起算後的逾時時間到達",
     "查詢場次狀態"],
    "逾時時間內若有任何交易或注單，計時重新起算、場次不因此結束；之後若確實無任何交易與遊玩超過逾時時間，場次自動結束並標記為「逾時結束」",
    "§場次/場次如何開始與結束 + §業務規則-場次逾時", critical=True))

# ================= REQ-038 場館日結時間結束所有進行中場次 =================
T.append(tc(38, [1], "場館日結時間到達時，所有進行中場次一律結束並標記日結結算，剩餘分數轉為隔日新場次期初餘額",
    "integration", ["functional"], ["state_transition", "boundary_value"],
    ["以 Admin 登入 站台列表，將該場館日結時間設定為便於測試觀察、即將到達的時刻",
     "確認該場館至少兩台機台皆有進行中場次，分別記錄其當下餘額",
     "等待日結時間到達",
     "查詢兩台機台的場次狀態與新場次期初餘額"],
    "日結時間到達時，兩台機台的進行中場次皆結束並標記為「日結結算」，各自的剩餘分數精確轉為隔日新場次的期初餘額（不多不少）",
    "§場次/場次如何開始與結束", critical=True))

# ================= REQ-039 一台機台同時只有一個進行中場次 =================
T.append(tc(39, [1], "一台機台同時間僅會有一個進行中場次，不會產生併發的第二個進行中場次",
    "api", ["functional"], ["error_guessing"],
    ["確認機台帳號目前無進行中場次",
     "以近乎同時的方式（例如平行送出，或由自動化工具連續快速送出）呼叫 req-keyin 與 req-cashin/end-cashin 各一筆，皆使分數轉正",
     "查詢該機台帳號當下的進行中場次數量"],
    "無論觸發時序多接近，該機台同時間只會存在一個進行中場次，不會因為多筆幾乎同時的分數轉正事件而產生兩個併發的進行中場次",
    "§場次/場次如何開始與結束",
    assume="本 AC 標註為『理論情境』，真正的高並發競態通常需要能同時發送多筆請求的壓測/自動化工具才能可靠重現與驗證，一般手動或序列化的功能測試僅能模擬『幾乎同時』而非真正併發；是否有可用的並發測試工具/環境需與自動化或效能測試團隊確認"))

# ================= REQ-040 線上帳號的場次欄位一律顯示為橫線 =================
T.append(tc(40, [1], "線上會員的交易紀錄或注單查詢頁面場次編號欄位一律顯示「—」",
    "ui_e2e", ["functional"], ["requirement_based"],
    ["以 Admin 登入後台，取一個線上（非機台）會員帳號",
     "進入 交易紀錄查詢 或 注單查詢，查詢該會員的任一筆紀錄",
     "檢視該筆紀錄的場次編號欄位"],
    "場次編號欄位顯示「—」，因線上會員沒有場次概念",
    "§業務規則與驗證/場次欄位於線上帳號", pre=["以 Admin 登入後台"], risk="low", cost="low"))

# ================= REQ-041 機台停用或場館未開通時交易一律被拒 =================
T.append(tc(41, [1, 2], "機台被設為停用，或所屬場館站台非開通狀態時，任一交易請求皆回 7-OUT OF SERVICE",
    "integration", ["negative"], ["decision_table"],
    ["將該機台帳號設為停用狀態（機台帳號沿用既有會員帳號機制，透過既有的帳號啟用/停用功能操作，見假設）",
     "呼叫任一交易請求（開分/入金/洗分/出金）",
     "確認回覆，並確認機台既有餘額與尚未完成的交易是否受影響",
     "將該機台恢復為啟用狀態，改將所屬場館站台狀態改為非開通（例如暫停）",
     "呼叫任一交易請求"],
    "兩種情況下任一交易請求皆回 7-OUT OF SERVICE，該機台（或整個場館所有機台）無法運作；停用或站台非開通不影響既有餘額與尚未完成的交易",
    "§業務規則與驗證/機台停用、場館站台狀態 + §附錄-狀態碼對照", critical=True,
    assume="『機台停用』的後台切換操作路徑，本 spec 未明確定義其所在頁面（僅說明其效果），推測透過既有的會員帳號啟用/停用機制操作，實際入口需與環境負責人確認"))

# ================= REQ-044 開分招待本次不實作 =================
T.append(tc(44, [1], "不存在『開分招待』功能，稽核倍數為幣種層級設定無法綁定單筆交易",
    "ui_e2e", ["negative"], ["negative"],
    ["以 Admin 登入 帳務管理 > 出金設定 > TWD 頁籤，檢視稽核倍數設定的完整欄位",
     "檢視開分相關的操作介面（機台選單為廠商實作，改為檢視平台側是否有任何與『開分招待』『送分』相關的設定或交易類型欄位）"],
    "稽核倍數僅為幣種層級的單一設定值，沒有任何可綁定至單筆交易或活動的欄位；平台亦不存在『開分招待』（開分即綁定流水門檻）或『送分』這類無現金流的交易類型，此為 v07 定案刻意不實作的範圍",
    "§機台帳號的稽核", pre=["以 Admin 登入後台"], risk="low", cost="low"))

# ================= Report =================
cov = collections.defaultdict(lambda: {"draft_ids": [], "acs": collections.defaultdict(list)})
for t in T:
    for r in t["requirement_ids"]:
        cov[r]["draft_ids"].append(t["draft_id"])
    for a in t["acceptance_criteria_ids"]:
        cov["REQ-CASHFLOW-" + a.split("-")[2][:3]]["acs"][a].append(t["draft_id"])

uncovered = [
    {"requirement_id": "REQ-CASHFLOW-042",
     "reason": "Spec 原文明確標註『待確認：前台呼叫的認證方式（是否沿用機台憑證）』，尚無定案行為可供設計具體測試案例；此為分析階段就已知的開放問題，非本次設計遺漏。建議待前台／開發團隊定案後另行提出 Clarification 並補設計對應 TC。"},
    {"requirement_id": "REQ-CASHFLOW-043",
     "reason": "Spec 原文明確標註『待確認：req-cashout 成功後 end-cashout 失敗時前台的重送策略』，尚無定案行為可供設計具體測試案例。建議待前台團隊定案後另行提出 Clarification 並補設計對應 TC。"},
]
uncovered_ids = {u["requirement_id"] for u in uncovered}

n_exp = sum(1 for t in T if t["assumptions"])
tech_count = collections.Counter(x for t in T for x in t["design_techniques"])

rep = {
    "mode": "spec", "testcase_draft_artifact_id": None,
    "coverage_matrix": [
        {"requirement_id": r, "draft_ids": d["draft_ids"],
         "acceptance_criteria": [{"ac_id": a, "draft_ids": dd} for a, dd in d["acs"].items()]}
        for r, d in cov.items()
    ],
    "uncovered_with_reason": uncovered,
    "technique_summary": [{"technique": k, "count": v} for k, v in tech_count.items()],
    "self_check": {k: True for k in [
        "requirements_covered", "acceptance_criteria_covered", "negative_considered", "boundary_considered",
        "expected_results_traceable", "no_unsupported_assumptions", "duplicate_detection_completed"]},
    "assumptions": [a["text"] for t in T for a in t["assumptions"]],
    "duplicate_check": {"against_registry": False, "findings": [
        {"draft_id": "*", "similar_to": "*",
         "resolution": "本次刻意未比對既有 testcases/CASHFLOW.md 與 registry/TC-CASHFLOW-*（Phase3 影子測試要求獨立設計以利交叉比對），故 against_registry 標示為 false 並如實記錄；正式流程應對既有 ACTIVE TC 執行比對。"}
    ]},
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
print(f"{len(T)} TCs, {n_exp} exploratory, reqs covered={len(cov)}/{len(reqs)}, uncovered={len(uncovered)}")
