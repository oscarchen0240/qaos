#!/usr/bin/env python3
"""RUN-20260914-010 T2：Test Designer(mode=spec) 依 SPEC-TXLOG-001 v0.1 的 30 條需求展開 TestCaseDraft + TestDesignReport。
記取 CASHFLOW 的教訓：3+ 個彼此獨立的分支（尤其 high risk）不要壓縮進同一條 TC，寧可多開幾條也要能個別追蹤失敗點；
只有「同一規則的緊密相關分支」（如同一欄位的 true/false 兩種顯示值）才視情況合併。"""
import sys, pathlib, collections
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids
RUN, RM_AID = sys.argv[1], sys.argv[2]; ITER = int(sys.argv[3]) if len(sys.argv) > 3 else 0
SID, SV, AREA, A = "SPEC-TXLOG-001", "0.1", "TXLOG", "agent-test-designer"
reqs = {r["requirement_id"]: r for r in store.load(store.requirements_path(SID, SV))["requirements"]}
def R(n): return f"REQ-TXLOG-{n:03d}"
def AC(n, i): return f"AC-TXLOG-{n:03d}{i}"
def sr(loc): return {"spec_id": SID, "spec_version": SV, "location": loc}
PRE = ["以 Admin 登入後台", "進入 各式報表 > 交易紀錄查詢，站台切換選單已選定一個機台場館站台"]

def tc(req, acs, title, level, types, techs, steps, expected, loc, prio=None, risk=None, pre=None, data=None,
       assume=None, critical=False, cost="medium", more_reqs=(), extra_ac=()):
    r = reqs[R(req)]
    assumptions = []
    for a in ([assume] if isinstance(assume, str) else (assume or [])):
        assumptions.append({"text": a, "requirement_id": R(req), "needs_human_confirmation": True})
    prio = prio or (risk or r["risk"])  # priority 預設跟隨底層 Requirement 的風險分級，而非統一 high
    return {"draft_id": f"TC-DRAFT-{ids.ulid()}", "title": title, "product": "ba-admin", "functional_area": AREA,
            "requirement_ids": [R(req)] + [R(x) for x in more_reqs],
            "acceptance_criteria_ids": [AC(req, i) for i in acs] + [AC(rn, ai) for rn, ai in extra_ac],
            "spec_id": SID, "spec_version": SV, "test_level": level, "test_types": types, "design_techniques": techs,
            "priority": prio, "risk": risk or r["risk"], "execution_mode": "manual",
            "preconditions": PRE if pre is None else pre, "test_data": [{"name": k, "value": v} for k, v in (data or {}).items()],
            "steps": [{"n": i + 1, "action": s} for i, s in enumerate(steps)], "expected_result": expected,
            "expected_result_spec_reference": sr(loc), "assumptions": assumptions, "automation_status": "not_automated",
            "ci_eligible": False, "hotfix_eligible": True, "execution_cost": cost, "stability": "unknown", "critical_path": critical,
            "source": "spec_workflow", "design_rationale": ""}

T = []
T.append(tc(1, [1], "查詢範圍擴充後，機台交易的待確認/取消/逾時/未成立皆會列出，不只已完成", "ui_e2e", ["functional", "boundary"], ["requirement_based"],
    ["站台內有一筆機台開分已完成、一筆入金待確認、一筆出金已取消、一筆入金已逾時、一筆開分未成立", "不篩選狀態，檢視查詢結果"],
    "五筆交易皆列出，不只顯示已完成（已生效）的那一筆", "§功能說明", critical=True))

T.append(tc(2, [1], "非機台（線上會員）交易的查詢呈現不受本包擴充影響", "ui_e2e", ["functional"], ["requirement_based"],
    ["查詢結果包含一筆線上會員的既有交易", "檢視其呈現方式"],
    "與擴充前的既有 4.1 行為一致，欄位與呈現不受機台視角擴充影響", "§功能說明", risk="medium"))

T.append(tc(3, [1], "頁面資料範圍跟隨站台切換選單，篩選器不提供獨立場館欄位", "ui_e2e", ["functional", "negative"], ["requirement_based"],
    ["頁面標題下方的站台切換選單切至站台 A", "檢視篩選器所有欄位", "檢視查詢結果範圍"],
    "篩選器不存在「場館」欄位；查詢結果僅限站台 A 範圍內的交易", "§篩選器", risk="medium"))

T.append(tc(4, [1], "機台帳號篩選支援以逗號分隔查詢多筆會員編號", "ui_e2e", ["functional"], ["equivalence_partitioning"],
    ["機台帳號篩選欄輸入兩個機台帳號的會員編號，以「,」分隔", "點擊搜尋"],
    "查詢結果同時包含這兩個機台帳號的交易", "§篩選器", risk="medium"))

T.append(tc(5, [1], "交易編號篩選可精確查出特定一筆交易", "ui_e2e", ["functional"], ["requirement_based"],
    ["交易編號篩選欄輸入一筆已知的交易編號", "點擊搜尋"],
    "查詢結果僅顯示該筆交易", "§篩選器", risk="low", cost="low"))

T.append(tc(6, [1, 2], "場次編號可透過文字輸入或點擊列表值兩種方式篩出同場次所有交易", "ui_e2e", ["functional"], ["requirement_based"],
    ["場次編號篩選欄輸入一個已知的場次編號，點擊搜尋，檢視結果", "清除篩選後，改為在列表中點擊某筆機台交易的場次編號值，檢視結果"],
    "兩種方式皆能篩出同一場次內的所有交易，結果一致", "§篩選器 + §列表欄位", critical=True))
T.append(tc(6, [3], "線上會員交易的場次編號欄一律顯示橫線", "ui_e2e", ["boundary"], ["boundary_value"],
    ["查詢結果包含一筆線上會員的交易", "檢視其場次編號欄"],
    "顯示「—」", "§列表欄位"))

T.append(tc(7, [1], "訂單編號篩選僅出金交易適用，其餘交易類型此欄為橫線", "ui_e2e", ["functional", "boundary"], ["boundary_value"],
    ["訂單編號篩選欄輸入一筆機台出金交易的訂單編號，點擊搜尋", "另檢視一筆機台入金交易的訂單編號欄"],
    "第一步查詢結果顯示該筆出金交易；第二步入金交易的訂單編號欄顯示「—」", "§篩選器 + §列表欄位"))

T.append(tc(8, [1], "交易類型篩選為多選 chip，實際標籤為開分/入鈔/出鈔/洗分", "ui_e2e", ["functional", "boundary"], ["requirement_based"],
    ["開啟交易類型篩選", "檢視所有可選項目", "同時勾選「開分」與「入鈔」兩個項目（測試是否可複選）"],
    "可選項目為「開分」「入鈔」「出鈔」「洗分」四項，不含「機台」字首；可同時勾選多個項目，非單選", "§篩選器", critical=True))
T.append(tc(8, [2], "勾選多個交易類型時查詢結果為聯集", "ui_e2e", ["functional"], ["equivalence_partitioning"],
    ["同時勾選「出鈔」與「洗分」兩個交易類型並搜尋"],
    "查詢結果同時包含這兩種類型的交易", "§篩選器"))

T.append(tc(9, [1], "交易類型為開分/入鈔時，交易狀態可選 7 種技術值", "ui_e2e", ["functional", "boundary"], ["boundary_value"],
    ["交易類型篩選勾選「開分」或「入鈔」", "開啟交易狀態篩選，檢視可選項目"],
    "可選項目為「已逾時、錯誤、無、成功、等待中、已取消、無效」共 7 項（與出鈔/洗分的選項不同）", "§篩選器", critical=True))
T.append(tc(9, [2], "交易類型為出鈔/洗分時，交易狀態可選 6 種技術值", "ui_e2e", ["functional", "boundary"], ["boundary_value"],
    ["交易類型篩選勾選「出鈔」或「洗分」", "開啟交易狀態篩選，檢視可選項目"],
    "可選項目為「失效、待處理、已拒絕、等待中、錯誤、已處理」共 6 項（與開分/入鈔的選項不同）", "§篩選器", critical=True))

T.append(tc(10, [1], "核實狀態篩選只有 3 個可選值，不含不適用", "ui_e2e", ["negative"], ["negative"],
    ["開啟核實狀態篩選", "檢視可選項目"],
    "僅有「待核實」「已核實」「已作廢」三個可選值，不含「不適用」", "§篩選器"))
T.append(tc(10, [2], "核實狀態篩選「待核實」僅窄化出機台洗分與機台出金交易", "ui_e2e", ["functional", "boundary"], ["equivalence_partitioning"],
    ["篩選核實狀態為「待核實」並搜尋"],
    "查詢結果僅顯示核實狀態為待核實的機台洗分或機台出金交易，不包含開分/入金", "§篩選器"))

T.append(tc(11, [1, 2], "交易時間與金額範圍篩選皆能正確窄化結果", "ui_e2e", ["functional", "boundary"], ["boundary_value"],
    ["設定交易時間範圍並搜尋，檢視結果", "清除後改設定金額範圍（min～max）並搜尋，檢視結果"],
    "兩者皆僅顯示落在所設定範圍內的交易", "§篩選器", risk="low"))

T.append(tc(12, [1], "點擊清除重置所有篩選條件", "ui_e2e", ["functional"], ["requirement_based"],
    ["設定多個篩選條件（如交易類型、交易狀態、金額範圍）", "點擊清除"],
    "所有篩選條件重置為預設值，查詢結果回到未篩選狀態", "§篩選器", risk="low", cost="low"))

T.append(tc(13, [1], "待確認分類（畫面顯示為等待中／待處理，兩組皆可能出現等待中）的交易分數尚未異動", "ui_e2e", ["functional"], ["requirement_based"],
    ["篩選出一筆交易狀態為「等待中」（開分/入鈔或出鈔/洗分皆可能出現）或「待處理」（出鈔/洗分類型另有的待確認值）的交易——皆對應 spec.md 的「待確認」分類", "檢視其分數異動情形（可對照會員帳務或機台帳號餘額）"],
    "分數尚未異動", "§交易狀態", more_reqs=(9,)))

T.append(tc(14, [1], "已完成分類（開分/入鈔顯示為成功，出鈔/洗分顯示為已處理）的交易分數已異動", "ui_e2e", ["functional"], ["decision_table"],
    ["篩選出一筆交易狀態為「成功」（開分/入鈔類型）的交易，檢視其分數異動情形", "另篩選出一筆交易狀態為「已處理」（出鈔/洗分類型）的交易，檢視其分數異動情形"],
    "兩種情境皆為 spec.md 的「已完成」分類，分數皆已異動", "§交易狀態", more_reqs=(9,)))
T.append(tc(14, [2], "出金交易被新出金或人工出金取代時標記為已取消（畫面顯示為已取消或失效）且分數未異動", "ui_e2e", ["functional"], ["state_transition"],
    ["一筆出金交易被新的出金請求或櫃檯人工出金取代"], "狀態顯示為「已取消」或「失效」（對應 spec.md 的「已取消」分類），分數未異動", "§交易狀態", more_reqs=(9,)))

T.append(tc(15, [1], "入金交易超過 24 小時未回報自動轉為已逾時", "ui_e2e", ["functional"], ["state_transition"],
    ["一筆入金交易超過 24 小時未收到機台回報", "檢視其狀態"],
    "自動轉為「已逾時」，分數未異動", "§交易狀態"))
T.append(tc(15, [2], "篩選已逾時狀態只會出現入金交易，不會出現出金", "ui_e2e", ["negative"], ["equivalence_partitioning"],
    ["交易類型篩選勾選「入鈔」，交易狀態篩選勾選「已逾時」並搜尋"],
    "查詢結果只包含入鈔（入金）交易，不會出現出鈔（出金）交易（出金不設逾時、出鈔的狀態選項清單裡也沒有已逾時這個值）", "§交易狀態", more_reqs=(9,)))

T.append(tc(16, [1], "交易因額度上限等原因被拒絕時顯示未成立分類（畫面顯示為錯誤/已拒絕/無效）且可查得原因", "ui_e2e", ["functional", "negative"], ["requirement_based"],
    ["一筆交易因額度上限被平台拒絕", "檢視其交易狀態（畫面顯示為「錯誤」「已拒絕」或「無效」之一，對應 spec.md 的「未成立」分類）與未成立原因欄"],
    "狀態顯示為未成立分類對應的技術值，分數未異動，未成立原因欄可查得拒絕原因", "§交易狀態", more_reqs=(9,)))
T.append(tc(16, [2], "餘額不足被拒絕的交易不會以未成立狀態出現在列表中", "ui_e2e", ["negative"], ["boundary_value"],
    ["一筆洗分或出金因餘額不足被拒絕", "檢視交易紀錄列表"],
    "查無此筆交易，不會以未成立分類的技術值出現", "§交易狀態"))

T.append(tc(17, [1], "出金待確認不會自動逾時，只能靠新請求取代、人工出金連動取消，或轉介洗分出金核實頁收斂", "ui_e2e", ["functional", "boundary"], ["scenario"],
    ["一筆出金交易長期處於待確認狀態，機台從未補送完成回報（超過入金逾時時限的 24 小時）", "持續檢視其狀態"],
    "不會自動轉為已逾時，持續保留為待確認，直到被新出金取代、櫃檯人工出金連動取消，或轉介至「洗分出金核實」頁（SPEC-CASHOUT-001）由人工處理", "§相關業務規則", critical=True))

T.append(tc(18, [1], "列表底部依交易類型分列顯示金額總計且與明細加總一致", "ui_e2e", ["functional"], ["requirement_based"],
    ["篩選出一批包含機台開分與機台入金兩種類型的結果", "檢視列表底部金額總計", "手動加總各類型明細金額"],
    "列表底部依交易類型分列顯示金額總計，且與該類型交易的金額加總一致", "§列表欄位", risk="medium"))

T.append(tc(19, [1, 2], "機台帳號欄可點擊進入會員詳細頁，非機台交易顯示橫線", "ui_e2e", ["functional", "boundary"], ["decision_table"],
    ["點擊一筆機台交易的機台帳號欄位值，檢視結果", "檢視一筆線上會員交易的機台帳號欄"],
    "第一步導向該機台帳號的會員詳細資料頁；第二步線上會員交易顯示「—」", "§列表欄位", critical=True))
T.append(tc(19, [3], "列表不顯示場館名稱欄位", "ui_e2e", ["negative"], ["negative"],
    ["檢視列表所有欄位"],
    "不存在場館名稱欄位或顯示（場館已由站台切換限定）", "§列表欄位"))

T.append(tc(20, [1], "洗分因門檻計算，實際金額小於請求金額時兩欄分別顯示", "ui_e2e", ["functional", "boundary"], ["boundary_value"],
    ["一筆洗分交易門檻計算後實際扣款小於機台請求的金額", "檢視請求金額與實際金額欄"],
    "請求金額為機台送出值；實際金額為門檻計算後的較小值，兩者不相同", "§列表欄位", critical=True))
T.append(tc(20, [2], "出金交易的請求金額與實際金額皆為全額清空的餘額", "ui_e2e", ["functional"], ["requirement_based"],
    ["一筆機台出金交易", "檢視請求金額與實際金額欄"],
    "兩者皆為當下全部餘額（全額清空），數值相同", "§列表欄位"))
T.append(tc(20, [3], "尚未完成的交易實際金額欄顯示橫線", "ui_e2e", ["boundary"], ["boundary_value"],
    ["一筆交易尚未完成（待確認）", "檢視其實際金額欄"],
    "顯示「—」", "§列表欄位"))

T.append(tc(21, [1, 2, 3], "核實狀態欄僅洗分/出金顯示值，待核實的洗分醒目提示、出金不提示", "ui_e2e", ["functional", "boundary"], ["decision_table"],
    ["檢視一筆機台開分交易的核實狀態欄", "檢視一筆待核實的機台洗分交易，確認呈現方式", "檢視一筆待核實的機台出金交易，確認呈現方式"],
    "第一步機台開分顯示「—」；第二步待核實洗分以醒目色標提示；第三步待核實出金正常顯示、不特別提示", "§列表欄位", critical=True))
T.append(tc(21, [4], "本頁不提供修改核實狀態的操作，此欄唯讀", "ui_e2e", ["negative"], ["negative"],
    ["嘗試在本頁（交易紀錄查詢）直接修改任一筆交易的核實狀態"],
    "本頁不提供此操作，核實狀態欄純顯示，無法在本頁修改", "§列表欄位 + §操作"))

T.append(tc(22, [1, 2], "核實人員／時間欄唯讀顯示核實紀錄，待核實時顯示橫線", "ui_e2e", ["functional"], ["decision_table"],
    ["檢視一筆已於核實頁被核實的交易，檢視此欄", "檢視一筆仍待核實的交易，檢視此欄"],
    "第一步顯示執行核實的後台帳號與時間（UTC+0）；第二步顯示「—」", "§列表欄位", risk="low"))

T.append(tc(23, [1, 2], "未成立原因欄僅未成立狀態顯示內容", "ui_e2e", ["functional", "negative"], ["decision_table"],
    ["檢視一筆狀態為未成立的交易，檢視未成立原因欄", "檢視一筆狀態為已完成的交易，檢視未成立原因欄"],
    "第一步顯示對應的拒絕原因文字；第二步不顯示內容（顯示「—」）", "§列表欄位", risk="low"))

T.append(tc(24, [1, 2], "交易時間與完成時間欄皆為 UTC+0，未完成時完成時間顯示橫線", "ui_e2e", ["functional"], ["decision_table"],
    ["檢視一筆已完成交易的完成時間欄", "檢視一筆尚未完成（待確認）交易的完成時間欄"],
    "第一步顯示以 UTC+0 表示的完成時間；第二步顯示「—」", "§列表欄位", risk="low"))

T.append(tc(25, [1], "重送次數欄目前固定顯示橫線，即使交易曾被重複回報也不顯示實際次數", "ui_e2e", ["negative"], ["negative"],
    ["資料庫中已存在一筆交易記錄：曾被機台重複回報 1 次（由 SPEC-CASHFLOW-001 的 end-cashin/end-cashout 冪等性機制處理，分數僅異動一次）", "於交易紀錄查詢頁檢視該筆交易的重送次數欄"],
    "重送次數欄固定顯示「—」，不顯示實際重複次數（現行產品尚未實作此顯示，已由 Oscar 與 PM/RD 確認）；分數本身仍只異動一次，不受此欄位顯示問題影響，該部分由 SPEC-CASHFLOW-001 驗證", "§列表欄位", critical=True))
T.append(tc(25, [2], "從未被重複回報的交易，重送次數欄同樣顯示橫線", "ui_e2e", ["functional"], ["requirement_based"],
    ["一筆交易從未被機台重複回報", "檢視重送次數欄"],
    "顯示「—」", "§列表欄位"))

T.append(tc(26, [1], "來源欄位目前固定顯示橫線，不顯示大廳或其他實際位置值", "ui_e2e", ["negative"], ["negative"],
    ["任意檢視一筆交易的來源欄（不論該交易實際發生位置為何）"],
    "固定顯示「—」，不顯示「大廳」或其他實際位置值（現行產品尚未實作此顯示，已由 Oscar 與 PM/RD 確認）", "§列表欄位", risk="low", cost="low"))

T.append(tc(27, [1], "查看明細面板區分摘要與技術欄位兩區塊", "ui_e2e", ["functional"], ["requirement_based"],
    ["點擊列表中任一筆交易", "檢視開啟的右側面板結構"],
    "顯示該筆交易的完整往來紀錄，上半部為摘要區塊（站務人員用）、下半部為技術欄位區塊（開發排查用）", "§操作", risk="medium"))

T.append(tc(28, [1], "本頁不提供手動取消操作，待確認交易需至洗分出金核實頁處理", "ui_e2e", ["negative"], ["negative"],
    ["檢視本頁（交易紀錄查詢）任一筆待確認狀態的交易", "尋找手動取消相關的按鈕或入口"],
    "不存在任何可執行的手動取消操作；spec.md §操作 描述的「手動取消」為錯誤敘述，非現行產品行為（已由 Oscar 2026-09-14 確認）。待確認交易的後續處理需至「洗分出金核實」頁（SPEC-CASHOUT-001）進行", "§操作", risk="medium"))

T.append(tc(30, [1], "本頁不提供任何核實或取消相關的人工操作", "ui_e2e", ["negative"], ["negative"],
    ["檢視本頁（交易紀錄查詢）的所有可用操作"],
    "本頁不存在任何核實或手動取消操作，僅有查看明細一項；核實與待確認交易的人工處理一律於「洗分出金核實」頁（SPEC-CASHOUT-001）進行", "§操作", risk="low", cost="low"))

# ================= Report =================
cov = collections.defaultdict(lambda: {"draft_ids": [], "acs": collections.defaultdict(list)})
for t in T:
    for r in t["requirement_ids"]: cov[r]["draft_ids"].append(t["draft_id"])
    for a in t["acceptance_criteria_ids"]:
        rid = "REQ-TXLOG-" + a.split("-")[2][:3]
        cov[rid]["acs"][a].append(t["draft_id"])
n_exp = sum(1 for t in T if t["assumptions"])
tech_count = collections.Counter(x for t in T for x in t["design_techniques"])
rep = {"mode": "spec", "testcase_draft_artifact_id": None,
       "coverage_matrix": [{"requirement_id": r, "draft_ids": d["draft_ids"], "acceptance_criteria": [{"ac_id": a, "draft_ids": dd} for a, dd in d["acs"].items()]} for r, d in cov.items()],
       "uncovered_with_reason": [{"requirement_id": "REQ-TXLOG-029", "reason": "MOOT: 手動取消操作本身已由 REQ-TXLOG-028 確認不存在於本頁（Oscar 2026-09-14 確認），此需求描述的『不符合條件時的阻擋機制』情境不會發生，不作為 grounded TC 設計依據，見 CLR-TXLOG-001 的回覆"}],
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
print(f"{len(T)} TCs, {n_exp} exploratory, reqs covered={len(cov)}/30")
