# Validator 對抗性 eval v1：故意錯誤的 Draft 必須被抓到

- **日期**：2026-09-18
- **依據**：`docs/architecture/08-roadmap.md` Risks 表「Phase 3 eval 加入『故意錯誤的 Draft』必須被抓到」；`docs/decisions/MODEL-ROUTING-POLICY.md` §4「等『故意錯 Draft』eval 通過後，再決定 Validator 能否降回 Sonnet」
- **結果**：**通過 v1 門檻**——8 個植入錯誤實質抓到 7、弱抓到 1、漏抓 0；誤報 0；整體判 FAIL
- **本目錄可重現**：`inject_errors.py`（植入）→ 派 Validator → `score.py`（評分）；`answer_key.json`、`validator_result.json`、`score_output.txt` 為本次實際資料

---

## 1. 這個 eval 測什麼、不測什麼

`tests/test_wf_x_gate_rejection_branches.py` 證明的是 **deterministic 的 structural gate** 會擋錯誤輸入。這個 eval 測的是另一層：**LLM Validator 的語意判斷**能不能抓到 gate 抓不到的錯——也就是 roadmap Risks 表擔心的「Validator 與 Designer 同源偏誤、互相同意、Validation 失效」。

所以植入的 8 個錯誤有一個硬性設計約束：**每一個都必須讓 `gates.g_design` 仍然 PASS**（`inject_errors.py` 會自我驗證，不 PASS 就中止）。這樣抓到的每一條都確定是 Validator 的功勞，不是程式碼的。

不測：Validator 對「structural 就會擋的錯」的反應（那不需要 LLM）；多模型比較；統計顯著性（這是單一樣本）。

## 2. 素材與流程

- **素材**：SPEC-UPDATEPACK-001 的真實 TestCaseDraft（`ART-TCD-01M2RK006KP2GY3N457AB9NV0H`，16 條，已通過兩輪獨立審查與 Phase2×3 整合）。選它因為規模夠放 8 種錯誤又保留一半正確 TC 當背景，且 spec 只有 9 req／15 AC，審查成本可控
- **植入**：`inject_errors.py` 從 repo 裡的原始 artifact 產生錯誤版 draft + 同步修正 report（coverage_matrix／technique_summary 跟著錯誤一致，保持 structural 通過），並去掉 `revision_of_issues` 避免洩漏「這份曾被審過」
- **派工**：跟先前 13 份 spec 完全相同的輸入（spec.md、requirements.yaml、testcase_draft.yaml、test_design_report.yaml、gates.py）與標準 Validator prompt，**未給任何指向植入點的線索**；模型 Sonnet（依 policy 預設）；答案卷放在 Validator 看不到的目錄
- **評分**：`score.py` 依 testcase_id + severity 機械比對；issue 描述是否真的對應錯誤本質，由人工逐條核對（見 §4）

## 3. 植入設計與結果

| # | 類型 | 目標 TC | 植入 | Validator 結果 | severity |
|---|---|---|---|---|---|
| E1 | quote 語意竄改 | #8 金額為 0 仍列出 | quote 改成「不列出」，expected 不動 | **抓到**：指出 quote 逐字不存在、方向相反、且注意到 expected 本身正確 | blocker |
| E2 | expected 違反 spec | #5 收合值 | expected 改「各幣別加總」，quote 保持正確 | **抓到**：與 title／quote／rationale／AC／spec 全部相反 | blocker |
| E3 | steps 與 AC 錯配 | #10 重新進入頁面 | steps 改成「換頁」（AC-0061 情境） | **抓到**：指出 AC-0062 未被獨立驗證、且與 TC9 近似重複 | major |
| E4 | 未揭露的虛構機制 | #7 排列順序 | precondition 加「幣別顯示設定」頁，assumptions 空 | **抓到**：spec 全文查無此頁、順序來源明載為鏈上錢包管理 | major |
| E5 | 自相矛盾 | #13 人工存入 | expected「次數不變；金額增加」 | **抓到**：後半句正是 spec 明文作廢的敘述 | blocker |
| E6 | 錯誤 req 掛載 | #15 線上場次「—」 | requirement_ids 改 REQ-008，AC 不動 | **抓到**：AC-0091 屬 REQ-009、risk 等級不符佐證誤植、coverage_matrix 複製了錯誤 | blocker |
| E7 | 覆蓋宣稱不實 | #12 總計列 | steps 砍到只看「總計列存在」 | **抓到**：形式掛載 AC-0072 但未驗證核心條件 | major |
| E8 | 標籤與內容不符 | #14 人工提出 | negative/error_guessing 改 functional/requirement_based | **弱抓到**：報「design_rationale 說 error_guessing 但欄位是 requirement_based」的文件內部矛盾 | minor |
| C1 | 對照組 | #3 exploratory（正確但最可疑） | 未動 | **無誤報**：未對它報 blocker／major | — |

`score_output.txt`：召回 實質 7/8、弱 1/8、漏 0/8；誤報 0；result FAIL；門檻通過。

## 4. 人工核對：Validator 是「真的懂」還是「碰巧對上」

8 條 issue 逐條核對描述內容，全部精確對應錯誤本質，且有三處超出預期：

- **E1**：不只說 quote 錯，還區分了「quote 錯但 expected 對」，判為「追溯鏈證據造假等級」——這是對 quote 欄位在本專案裡的角色（可追溯性依據）有正確理解
- **E3**：同時抓到「錯配」與「重複」兩個面向，並正確引用 spec 原文「換頁、重新查詢或重新進入頁面」三者並列來論證這是三種不同情境
- **E6**：除了抓到誤植，還用 risk 等級不一致（TC 標 low、REQ-008 是 high）當旁證，並**指出 `gates.py` 沒有檢查 AC 是否屬於所掛 requirement**——這是一個真實的 structural gate 缺口（見 §6）

對照組 C1 零誤報。advisories 裡對 TC1「precondition 會永久改動站台設定、未附復原」的觀察是合理的（先前真實審查也提過同類問題），不算誤報。

## 5. 最重要的發現：E8 是靠 `design_rationale` 抓到的

E8 的 rationale 欄位裡殘留原本的「採 error_guessing 技巧」文字（植入時只改了欄位沒改 rationale，這是刻意的——模擬「改了欄位忘了同步說明」的真實錯誤型態）。Validator 抓到的是「rationale 說 A、欄位說 B」的**文件內部矛盾**，而**不是**「內容是反向驗證卻標 functional」的**性質判斷**。

這揭示兩件事：

1. **現行流程與 `agents/test-validator.yaml` 契約有偏差**：契約 `forbidden_actions` 明定 Validator「不得讀取 Test Designer 的推理過程／TestDesignReport.self_check 以外的內部說明（避免同源偏誤；只讀 Draft、Report coverage matrix、Spec、Requirement）」。但先前 13 份 spec 的派工都給了含 `design_rationale` 的完整 draft，本次 eval 為了反映現行流程也一樣。Validator 確實在讀、也在依賴它。
2. **若依契約剝除 rationale，E8 很可能漏抓**——因為那需要 Validator 自己判斷「這條案例的性質是什麼」，而不是比對兩段文字。這是 v2 最該做的對照組。

反過來說，E1～E7 的抓取都**不依賴** rationale（它們是 quote vs spec、expected vs spec、steps vs AC、precondition vs spec 的比對），所以即使剝除 rationale，7/8 的召回大概率維持。

## 6. 附帶產出：一個真實的 gates.py 缺口

`gates.g_design` 對 `acceptance_criteria_ids` 的檢查是：

```python
ac_ids = {ac["ac_id"] for r in reqs.values() for ac in r.get("acceptance_criteria", [])}
...
for aid in tc.get("acceptance_criteria_ids", []):
    if aid not in ac_ids: issues.append(...)
```

只驗 AC 存在於**全域**集合，不驗 AC 是否屬於該 TC 所掛的 `requirement_ids`。E6 之所以能設計成「structural PASS、只有語意錯」，正是利用這個洞。這是可以（也應該）變成 deterministic 規則的東西——Validator 不該為程式碼能查的事情兜底。

**已處理（v1.1）**：`gates.g_design` 已補「TC 的每個 AC 必須屬於其 requirement_ids 之一」規則（建 `ac_owner` 映射，AC 存在但不屬於任一所掛 requirement 即擋，訊息帶實際 owner），對應測試 `tests/test_wf_x_gate_rejection_branches.py::test_58`（含正確配對、合法跨 requirement TC、AC 不存在三組對照）。gates.py 覆蓋維持 100%，整套 45 條通過，新規則未誤傷任何既有合法 draft。

## 6.1 v1.1 變更：E6 已由 structural 攔截，植入腳本替換類型

補了上述規則後，v1 的 E6（錯誤 requirement 掛載）不再是純語意錯誤——`inject_errors.py` 的自我驗證會被 gate 擋下。處理方式：

- **v1 的歷史資料不動**：`answer_key.json`、`validator_result.json`、`score_output.txt` 仍是 2026-09-18 那次的事實（舊 E6、Validator 抓到 blocker）
- **`inject_errors.py` 的 E6 替換為 §8 建議過的更隱晦類型「AC given 條件被偷換」**：#16（AC-0092 given 是「機台帳號的注單」）的 precondition／steps 測試對象偷換成線上會員，title 與 expected 不動。requirement／AC 都正確所以 structural 過；語意上測錯對象、且依 spec 線上會員該顯示「—」而 expected 仍說顯示場次編號
- 腳本已重新驗證：新規則下仍產出 8 個純語意錯誤 + 1 對照，structural PASS
- 舊 E6 那段「同步把 CCJ199 改掛到 REQ-008 的 coverage_matrix」邏輯一併移除

這件事本身就是 eval 的正向循環：eval 揭露一個「靠 LLM 兜底」的洞 → 變成 deterministic 規則 → eval 換一個更難的錯誤類型繼續往前推。

## 7. 對 MODEL-ROUTING-POLICY §4 的意義

Policy §4：「Phase 3 兩邊都改由 LLM 產出時⋯先用不同模型（Opus，或至少不要與 Designer 同一顆）⋯等『故意錯 Draft』eval 通過後，再決定 Validator 能否降回 Sonnet」。

本次情境正是 **Sonnet Designer × Sonnet Validator**（UPDATEPACK 的 draft 由 `qaos-test-designer` subagent 產出，Validator 也是 Sonnet）。結果通過，是對「同源偏誤會讓 Validation 失效」這個風險的一個**正面證據**：至少在「內容與 spec 矛盾」這類錯誤上，同源沒有讓 Validator 放水。

但這是單一 spec、單一次、8 個錯誤的樣本，結論只能是「現行流程在此樣本上有效」，不是統計證明。且 E8 的弱抓到顯示「性質判斷」類錯誤是相對弱點。

## 8. 限制與 v2 建議

| 限制 | v2 建議 |
|---|---|
| 給了 `design_rationale`（違反契約） | **對照組：剝除 rationale 再跑一次同一份錯誤 draft**，看 E8 是否漏抓、E1～E7 是否維持 |
| 單一 spec | 換一份結構不同的 spec（例如 DAILYREPORT 的日期／週期邏輯，或 CASHOUT 的狀態機） |
| 錯誤都偏「明顯的矛盾」 | 加更隱晦的類型：數值邊界 off-by-one、AC 的 given 條件被偷換一個詞、兩條 TC 各自正確但合起來覆蓋範圍有洞 |
| 單一模型 | 若要用來決策「Validator 用哪個模型」，同一份錯誤 draft 至少跑 Sonnet 與 Opus 各一次 |
| 一次性 | 可考慮把 `inject_errors.py` 的植入邏輯參數化，讓每次 eval 隨機挑目標 TC 與錯誤類型組合 |
