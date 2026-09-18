#!/usr/bin/env python3
"""Validator 對抗性 eval v1：對一份已通過審查的真實 TestCaseDraft 故意植入 8 種語意錯誤。

設計約束：每個錯誤都必須讓 structural gate（gates.g_design）仍然 PASS，只有語意層面錯——
這樣才是在測 LLM Validator 的判斷，而不是在測 deterministic 程式碼。

用法：
    python3 inject_errors.py <out_dir>
產出：
    <out_dir>/testcase_draft.yaml      植入錯誤後的 Draft（artifact envelope 格式，與派工 Validator 時給的一致）
    <out_dir>/test_design_report.yaml  同步修正 coverage_matrix / technique_summary 的 Report（保持 structural 一致）
    <out_dir>/answer_key.json          答案卷：每個植入點的位置、類型、Validator 應偵測到什麼
執行後會用 gates.g_design 自我驗證 structural 仍 PASS；不 PASS 即中止（代表植入設計錯誤）。
"""
import copy, json, pathlib, sys, collections
ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from tools.qaos import store, gates

SRC_TCD = "artifacts/test-design/RUN-20260918-009/ART-TCD-01M2RK006KP2GY3N457AB9NV0H.yaml"
SRC_TDR = "artifacts/test-design/RUN-20260918-009/ART-TDR-01M2RK006ZH5J28T4D5DJCKZV8.yaml"

out = pathlib.Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
tcd = copy.deepcopy(store.load(SRC_TCD)); tdr = copy.deepcopy(store.load(SRC_TDR))
tcs = {t["draft_id"][-6:]: t for t in tcd["payload"]["testcases"]}
key = {}

def mark(tag, suffix, etype, detail, expect):
    key[tag] = {"draft_id": tcs[suffix]["draft_id"], "suffix": suffix, "type": etype, "injected": detail, "expected_detection": expect}

# E1 quote 語意竄改（#8 金額為 0 仍列出）
t = tcs["SR5Y6J"]
t["expected_result_spec_reference"]["quote"] = "金額為 0 的幣別 | 不列出，僅顯示有餘額的幣別，避免清單冗長"
mark("E1", "SR5Y6J", "quote_semantic_tamper",
     "quote 改成與 spec 相反的句子（spec 原文是『仍列出並顯示 0.00，不因無餘額而隱藏』），expected_result 保持正確",
     "quote 不存在於 spec.md 原文；且 quote 與 expected_result 互相矛盾")

# E2 expected_result 違反 spec（#5 收合值＝核心貨幣原始餘額）
t = tcs["1HJXYJ"]
t["expected_result"] = "收合狀態顯示的數值，等於展開後各已啟用幣別金額的加總（含核心貨幣與非核心貨幣）"
mark("E2", "1HJXYJ", "expected_contradicts_spec",
     "expected 改成『各幣別加總』，quote 仍是正確原文『不做匯率換算，也不是各幣別的加總』",
     "expected_result 直接違反自己引用的 quote／spec 規則")

# E3 steps 與 AC 錯配（#10 AC-0062 離開頁面重新進入 → 改成測換頁）
t = tcs["CN7R3V"]
t["steps"] = [{"n": 1, "action": "於會員列表展開任一會員的餘額欄"},
              {"n": 2, "action": "點擊分頁控制項切換到下一頁，再切回原頁"},
              {"n": 3, "action": "檢視該會員的餘額欄是否仍為展開狀態"}]
mark("E3", "CN7R3V", "steps_ac_mismatch",
     "AC-0062 是『離開頁面後重新進入』，steps 改成『換頁再切回』（那是 AC-0061 的情境，且已由另一條 TC 覆蓋）",
     "steps 驗證的情境與所掛 AC-0062 不符；AC-0062『重新進入頁面』實質未被覆蓋；與 AC-0061 的 TC 重複")

# E4 未揭露的虛構機制依賴（#7 排列順序）
t = tcs["YKAH1N"]
t["preconditions"].append("已於後台『系統管理 > 幣別顯示設定』頁將幣種顯示順序手動調整為 TTK → USDT → BTC 並儲存")
mark("E4", "YKAH1N", "undisclosed_fabricated_mechanism",
     "precondition 加入不存在的『幣別顯示設定』頁（spec 明說順序依鏈上錢包管理、本功能不另行設定幣別清單），assumptions 保持空",
     "precondition 依賴 spec 未定義／明確排除的機制，卻未以 assumptions 揭露；且與 spec『核心貨幣固定第一列』規則衝突")

# E5 自相矛盾（#13 人工存入不計入存款次數／金額）
t = tcs["T55KVR"]
t["expected_result"] = "該會員的存款次數維持不變；存款金額則增加本次人工存入的金額"
mark("E5", "T55KVR", "self_contradiction",
     "expected 前半句『次數不變』正確，後半句『金額增加』違反 spec『人工入金一律不計入』，兩句互相矛盾",
     "expected_result 內部自相矛盾；後半句違反 spec")

# E6 AC 的 given 條件被偷換（#16 機台帳號注單顯示場次編號 → 測試對象偷換成線上會員）
# v1.1 變更：原 E6「錯誤 requirement 掛載」自 gates.g_design 補「AC 必須屬於所掛 requirement」規則後改由 structural 攔截，
#            不再是純語意錯誤，故替換為本類型。v1 的 answer_key.json / validator_result.json 反映的是舊 E6。
t = tcs["6WNBVZ"]
t["preconditions"] = ["以 Admin 登入後台",
                      "選定一名既有線上會員（非機台帳號），其至少有一筆注單記錄已知所屬的場次編號（可先於『各式報表 > 交易紀錄查詢』核對）"]
t["steps"] = [{"n": 1, "action": "進入『各式報表 > 注單查詢』，篩選出該線上會員的注單記錄，查詢"},
              {"n": 2, "action": "檢視該筆注單列的『場次編號』欄位，與前置作業核對的場次編號比對"}]
mark("E6", "6WNBVZ", "ac_given_condition_swapped",
     "AC-0092 的 given 是『機台帳號的注單』，precondition／steps 的測試對象偷換成『線上會員』；title 與 expected（顯示所屬場次編號）不動。"
     "requirement_ids／acceptance_criteria_ids 皆正確，structural 不擋",
     "測試對象與 AC given 不符；且依 spec 線上會員的場次編號欄應顯示「—」，expected 卻斷言顯示場次編號，與 AC-0091 矛盾")

# E7 覆蓋宣稱不實（#12 總計列以核心貨幣加總、不拆分）
t = tcs["SHW7C4"]
t["steps"] = [{"n": 1, "action": "進入會員列表並查詢"}, {"n": 2, "action": "確認列表底部有顯示『總計』列"}]
t["expected_result"] = "列表底部顯示總計列，總計列有數值"
mark("E7", "SHW7C4", "coverage_claim_not_substantiated",
     "steps／expected 砍到只驗證『總計列存在』，沒驗證『以核心貨幣加總』也沒驗證『不依幣別拆分』，report 仍宣稱覆蓋 AC-0072",
     "TC 內容未實質驗證 AC-0072 的核心條件；coverage_matrix 的覆蓋宣稱不實")

# E8 標籤與內容不符（#14 人工提出後提款不變 → negative 改成 functional）
t = tcs["692S4G"]
t["test_types"] = ["functional"]; t["design_techniques"] = ["requirement_based"]
mark("E8", "692S4G", "technique_label_mismatch",
     "內容是『執行人工提出後提款次數／金額皆不變』的反向驗證，標籤卻從 negative/error_guessing 改成 functional/requirement_based（REQ-008 仍有另一條 negative 撐 high-risk 規則，structural 不擋）",
     "test_types／design_techniques 與案例實際性質不符")

# 對照組 C1：#3 exploratory 那條刻意不動（先前第二輪已驗證正確），測誤報
key["C1"] = {"draft_id": tcs["SV1JAD"]["draft_id"], "suffix": "SV1JAD", "type": "control_correct_but_suspicious",
             "injected": "未植入任何錯誤。此條本身帶 assumptions、precondition 較長，是全份最『看起來可疑』的案例",
             "expected_detection": "Validator 不應對此條報出 blocker/major"}

# --- 同步 Report，保持 structural 一致（只留語意錯誤） ---
# v1.1：coverage_matrix 不再需要改動（舊 E6 的 requirement 改掛已移除）；只同步 technique_summary（E8 改了標籤）
rep = tdr["payload"]
cnt = collections.Counter(x for t in tcd["payload"]["testcases"] for x in t["design_techniques"])
rep["technique_summary"] = [{"technique": k, "count": v} for k, v in cnt.items()]
rep.pop("revision_of_issues", None)   # 去掉修訂歷程，避免洩漏「這份曾被審過」

# --- 自我驗證：structural 必須仍 PASS ---
issues = gates.g_design(None, None, {"TestCaseDraft": tcd, "TestDesignReport": tdr})
if issues:
    print("植入設計錯誤：structural gate 會擋，這些錯誤就不是純語意錯誤了：", file=sys.stderr)
    for i in issues: print("  -", i, file=sys.stderr)
    sys.exit(1)

store.save(out / "testcase_draft.yaml", tcd); store.save(out / "test_design_report.yaml", tdr)
(out / "answer_key.json").write_text(json.dumps(key, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"structural gate PASS（純語意錯誤）；已植入 {len([k for k in key if k.startswith('E')])} 個錯誤 + {len([k for k in key if k.startswith('C')])} 個對照 → {out}")
