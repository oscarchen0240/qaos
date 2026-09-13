# 建議草案：負向 / 反邏輯測試案例如何產生

> 狀態：**已採納並執行 §10「立刻」欄（2026-09-13）**：Requirement 加 `behavior_kind / inputs / states / rejection_contract`、G-DESIGN 九條機械檢查、rejection 未定義 → 自動開 Clarification、exploratory > 50% → NEEDS_DECISION、ACTIVATE 逐項確認假設、`docs/templates/spec-template.md`。測試：`tests/test_wf_y_negative_coverage.py`。Phase 3 skill 層待做。  
> 目的：回答「Agent 寫 TC 時除了 Spec 還會不會發想？反邏輯操作寫不出來怎麼辦？」  
> 相關：`agents/test-designer.yaml`、`agents/test-validator.yaml`、`07-skill-evaluation.md`、`04-quality-gates.md`、`RECOMMENDATIONS-skill-and-top3.md`

---

## 1. 問題陳述

實務上 Agent 產出的測試案例常出現：

- 幾乎只有**正向 / 順向**（happy path）
- 使用者**違反流程、亂操作、跳步驟、重複提交**這類案例很少或沒有
- 即使有負向步驟，**expected result** 也容易變成 Agent 自己編的產品規則

核心張力：

| 需求 | 約束 |
|---|---|
| 希望有反邏輯、探索性案例 | QAOS / skill 禁止臆測未定義需求（Do not assume undefined requirements） |
| 希望 expected 可信 | Validator 要求 expected 有 Spec / Requirement 依據 |
| 希望覆蓋真實使用者行為 | Spec 往往只寫成功路徑，沒寫錯誤契約 |

---

## 2. 建議原則（一句話）

**可以發想「怎麼測亂操作」；不可以發想「沒寫過的產品規則」。**

- **行為發想（允許）**：重複提交、跳過步驟、空值、超長、無權限仍點擊、並發連點…
- **規則發想（禁止或僅能標假設）**：Spec 沒寫重複提交時的提示文案 / HTTP code，卻寫成確定的 expected

---

## 3. 建議的案例分層

### 3.1 `grounded`（有 Spec 依據）— 正式路徑主力

- Spec / Requirement / AC **有寫**錯誤、拒絕、邊界行為
- `expected_result` 必須引用具體條文（`expected_result_spec_reference`）
- `test_types` 可標 `negative` / `boundary` 等
- 可走完整 Validator →（人審後）進 Registry

### 3.2 `exploratory`（探索 / 假設）— 補反邏輯，但不假裝已定論

- Spec **沒明寫**系統應如何反應，但從領域常識看「不該成功」
- **可以寫操作步驟**（亂操作怎麼做）
- expected 只能二選一：
  - 寫成 `assumptions[]` + `needs_human_confirmation: true`
  - 或 expected 表述為「系統不得完成原本的成功結果」（若連這點 Spec 都沒暗示，則降為 open question，不進正式 Draft）
- **預設不直接 ACTIVE**；需 Human 確認假設，或先回 Spec Analyst 補錯誤契約後再改寫成 `grounded`

### 3.3 不可寫成正式 TC

- Spec 完全沒定義、也看不出任何約束
- Agent 不應硬編 expected
- 應列入 `TestDesignReport.open_questions` / `uncovered_with_reason`，或升級 Spec ambiguity

---

## 4. 建議的強制覆蓋規則（避免只產出正向）

若採納，建議寫進 `test-case-design` skill 與 G-DESIGN self-check：

1. **每個 `risk=high` 的 ACTIVE Requirement**  
   至少 1 條 `design_technique` 含 `negative` **或** `error_guessing` 的 Draft；  
   若無法產出 → 必須在 `uncovered_with_reason` 寫明原因（例如「Spec 無錯誤行為定義」）。

2. **每個 ACTIVE Requirement 的技術組合**（建議下限，可調）  
   - 至少 1 條 functional / scenario（正向）  
   - 至少嘗試 1 條 boundary **或** negative（高風險強制；中低風險可列 uncovered）

3. **Design Report 必須統計**  
   - `technique_summary`：scenario / negative / boundary / error_guessing 各幾條  
   - 若 negative + error_guessing = 0 → self-check **不得**宣告通過（除非全部 uncovered 且理由成立）

4. **Validator 規則差異**  
   - `grounded`：expected 無 Spec 依據 → **blocker FAIL**  
   - `exploratory`：缺 `assumptions` / 未標 `needs_human_confirmation` → **blocker FAIL**；有標則可 PASS structural，但下游 ACTIVATE 仍需人審假設

---

## 5. 對 Spec 與流程的建議配套

光改 Designer prompt 不夠，建議同步：

| 配套 | 說明 |
|---|---|
| Spec 補「不該發生什麼」 | 比再堆正向步驟更有用。例：不可重複提交、未登入不可結帳、金額不可為負 |
| Spec Analyst 抽錯誤契約 | Requirement 可標 `behavior_kind: success \| rejection \| boundary`（若採納需改 schema，請 Claude 評估工作量） |
| exploratory → 回補 Spec | Human 確認後的假設，優先變成 Spec 修訂，再把 TC 升級為 grounded |
| 補充 skill reference | 依既有評估：納入 `negative-test-designer`、`test-oracle-writer` 作 references（不安裝整包） |

---

## 6. 與現有架構的對齊（不衝突處）

現有設計**已允許**負向技術，並非禁止：

- Test Designer responsibilities 已列 Negative / Boundary / Error Guessing
- `test_types` enum 含 `negative`
- G-DESIGN self-check 已提到 negative / boundary 考慮
- skill 評估已承認核心 skill 對 negative 專章偏弱，建議補 reference

本草案要補的是：**強制覆蓋 + 分層（grounded / exploratory）+ Validator 差異化**，避免「理論上能寫、實務上全寫正向」。

---

## 7. 風險與代價（請 Claude 一併評估）

| 風險 | 說明 | 可能緩解 |
|---|---|---|
| exploratory 氾濫 | 人審負擔上升 | 僅 high risk 強制；exploratory 批次呈現 assumptions |
| Agent 把臆測標成 grounded | 污染 Registry | Validator 嚴格查 spec reference；ACTIVATE 批次可逐項 reject |
| Spec 仍只寫成功路徑 | uncovered 變多、負向仍少 | Spec 模板加「錯誤 / 拒絕行為」章節 |
| schema / workflow 變更 | 若加 `case_class` 或 `behavior_kind` 有 Phase 2 成本 | 可先只用 `assumptions[]` + `test_types` 表達，不加新欄位做 MVP |

---

## 8. 請 Claude 回答的問題

請針對本草案評估並回覆：

1. **是否採納** grounded / exploratory 分層？若採納，欄位要用新 enum（如 `case_class`）還是沿用 `assumptions[]` + `needs_human_confirmation` 即可？
2. **覆蓋硬指標**（§4）是否過嚴或過鬆？請給可執行的數字建議。
3. **G-DESIGN / G-TVAL** 要改哪些檢查條目？
4. **WF-A** 是否需要多一個節點處理 exploratory 的人審，還是併入既有 `ACTIVATE_TESTCASE` / `RESOLVE_AMBIGUITY`？
5. 與 `NEEDS_DECISION-13`（分析審核 gate）是否衝突或可合併？
6. Phase 2 / 3 最小實作路徑：哪些立刻做、哪些可延後？

---

## 9. 人工確認前的預設立場（可改）

作者目前傾向：

- **採納**行為發想 + 禁止規則臆測
- **採納** grounded / exploratory 分層（MVP 先用 assumptions，不加新欄位也可）
- **採納**高風險 REQ 強制至少 1 條 negative / error_guessing
- **暫不**在未確認前改 schema / workflow；等 Claude 評估後再決定

確認用語（之後若要執行可回）：

```text
採納「負向/反邏輯案例草案」RECOMMENDATIONS-negative-exploratory.md
請依你的評估調整後寫入架構（或列出你建議修改的段落）
```

或：

```text
暫不採納該草案，維持現況（僅靠 skill 技術清單，不加覆蓋硬指標）
```

---

## 10. Claude 評估（2026-09-13，僅評估、未執行）

**立場：採納，但不加新欄位；分層由 Runtime 派生；硬指標只綁 high-risk。**

| Q | 回答 |
|---|---|
| 1 分層 | 採納。**不加 `case_class` enum**。`grounded` ⇔ `assumptions == []`；`exploratory` ⇔ `assumptions` 非空且每筆 `needs_human_confirmation: true`。Runtime 派生顯示於 ApprovalRequest batch item。需修 `engine.py` materialize（目前丟掉 `needs_human_confirmation`），ACTIVATE approve 時填 `resolved_by_approval`。 |
| 2 硬指標 | (a) ACTIVE ∧ `risk=high` 的 REQ 至少 1 條非 happy-path（`test_types ∩ {negative, boundary}` 或 `design_techniques ∩ {negative, error_guessing, boundary_value}`），否則 `uncovered_with_reason` 且 reason 以 `NO_REJECTION_CONTRACT:` 開頭；(b) `risk=medium` 為 advisory；(c) 整份 negative+boundary+error_guessing = 0 → FAIL（除非全部 uncovered 且理由成立）；(d) exploratory 佔比 > 50% → `NEEDS_DECISION`（先補 Spec？）；(e) 每 REQ exploratory ≤ 3。**不用比例下限**（會湊數）。 |
| 3 Gate | G-DESIGN structural：上述規則 + assumptions 結構 + **`technique_summary` 與 Draft 實際統計一致**（現有漏洞）。G-TVAL semantic：grounded 無 spec 依據 → blocker；exploratory 缺 assumptions → blocker；exploratory 寫具體文案/狀態碼 → major；新增 issue_type `missing_negative_coverage`。Validator 對 exploratory 只問「Spec 有沒有寫」不問「合不合理」（同源偏誤）。 |
| 4 WF-A | **不加節點**。併入 `ACTIVATE_TESTCASE` 批次 per-item 確認；認為該進 Spec 者 reject 該 item 並開 `Clarification` 問 PM → Spec 新版 → WF-C。 |
| 5 vs -13 | 互補。`analysis_review=required` 時 Designer 分析階段輸出 `planned_exploratory[]`，生成前即可砍/補 Spec。Phase 3 prompt 層，不改 schema。 |
| 6 路徑 | **立刻（Phase 2）**：G-DESIGN 三條機械檢查、保留假設、ACTIVATE 填 resolved、batch item 附 assumptions、>50% → NEEDS_DECISION（~80 行 + 3 測試）。**Phase 3**：skill 規則、`planned_exploratory`、references；Requirement `behavior_kind` optional 欄位隨 spec-analysis skill 一起做。**現在可寫**：`docs/templates/spec-template.md` 加「錯誤 / 拒絕行為」章節。 |

建議修改草案：§3.2「系統不得完成原本的成功結果」升為 exploratory 的**預設** expected 寫法；§4 規則 3 改為 negative + **boundary** + error_guessing；§7 加「>50% 觸發 NEEDS_DECISION，把問題導回 Spec」。

## 附記（2026-09-14）：發現通用錯誤代碼 `COMMON_INVALID_REQUEST_FORMAT`

PM 回覆 CLR-SITELIST-003 時提到後端對格式錯誤的輸入回傳統一錯誤代碼 `COMMON_INVALID_REQUEST_FORMAT`。這暗示系統有一套**跨功能共用的錯誤代碼**，值得之後每個 Spec Analysis 主動詢問「這個欄位驗證失敗時的確切錯誤代碼／訊息」，而不是每次都當獨立未知數處理——可以在 `docs/templates/spec-template.md` 補一句提醒 Spec 作者列出共用錯誤代碼表。
