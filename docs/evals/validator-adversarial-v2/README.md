# Validator 對抗性 eval v2：剝除 `design_rationale` 的對照組

- **日期**：2026-09-19
- **依據**：v1 README §5／§8——v1 揭露 E8 是靠 `design_rationale` 抓到的，而 `agents/test-validator.yaml` 的 `forbidden_actions` 明定 Validator 不得讀 Designer 的推理過程；v2 就是把這條契約真的執行一次，看召回會不會掉
- **結果**：**契約可以照做**——剝除 rationale 後 E1～E7 全部維持實質抓到（7/8 → 7/8）、誤報 0 → 0、整體 FAIL → FAIL；唯一差異是 **E8 從弱抓到（minor）變漏抓**，與 v1 的預測一致
- **本目錄可重現**：v1 的 `inject_errors.py`（v1.1 版）產出 A → 複製一份跑 `strip_rationale.py` 得 B → 兩個 Validator 平行審 → `compare.py`；`answer_key.json`、`result_A_with_rationale.json`、`result_B_without_rationale.json`、`compare_output.txt` 為本次實際資料

---

## 1. 設計：單一變因

| | A（含 rationale） | B（剝除） |
|---|---|---|
| Draft | v1.1 `inject_errors.py` 產出（8 植入 + 1 對照，structural PASS） | 同一份，只 pop 每條 TC 的 `design_rationale`（16 條全部移除） |
| Report | 同一份 | 同一份（coverage_matrix／technique_summary／self_check 是結構化資料不是推理，保持不動） |
| 輸入 | spec.md、requirements.yaml、draft、report、gates.py | 同 |
| Prompt | 標準 Validator prompt，無任何指向植入點的線索 | 逐字相同 |
| 模型 | Sonnet | Sonnet |
| 派工 | 平行、互不可見、答案卷放在兩者都看不到的目錄 | 同 |

已程式驗證：A 剝除 rationale 後與 B 逐 byte 相等，除了這個欄位沒有其他差異。

## 2. 結果

`compare_output.txt`：

| # | 類型 | TC | A（含） | B（剝除） | 差異 |
|---|---|---|---|---|---|
| E1 | quote 語意竄改 | SR5Y6J | blocker | blocker | |
| E2 | expected 違反 spec | 1HJXYJ | blocker | blocker | |
| E3 | steps 與 AC 錯配 | CN7R3V | major | major | |
| E4 | 未揭露的虛構機制 | YKAH1N | major | major | |
| E5 | 自相矛盾 | T55KVR | blocker | blocker | |
| E6 | **AC given 條件偷換（v1.1 新類型）** | 6WNBVZ | blocker | blocker | |
| E7 | 覆蓋宣稱不實 | SHW7C4 | major | major | |
| E8 | 標籤與內容不符 | 692S4G | minor | **漏** | ↓ |
| C1 | 對照組 | SV1JAD | 無誤報 | 無誤報 | |

實質抓到 A 7/8、B 7/8；誤報 A 0、B 0；整體皆 FAIL。severity 分佈（4 blocker + 3 major）在兩組**落在完全相同的 7 條 TC 上**。

## 3. 人工核對

### 3.1 E1～E7：剝除 rationale 沒有降低描述品質

兩組對每一條的描述都精確對應錯誤本質，且 B 沒有因為少了 rationale 而變籠統——反而多了幾處 A 沒寫的旁證：

- **E2**：B 注意到「同 AC 另一條 TC 給出互斥結論」（同 AC-0031 的兩條 TC 一條說原始餘額、一條說加總）
- **E4**：B 指出 precondition 第 2 項（依鏈上錢包管理順序）與植入的第 3 項（手動調整順序）互相衝突
- **E5**：兩組都用「對稱的提款版 692S4G 寫法正確」反證這是獨立缺陷；B 額外強調 REQ-008 是 critical_path

這與 v1 §5 的推論一致：E1～E7 都是 draft 欄位 vs spec／AC 的比對，本來就不需要 rationale。

### 3.2 E6 新類型首次結果：兩組都 blocker

v1.1 把 E6 換成更隱晦的「AC given 條件偷換」（requirement／AC 都掛對，只有 precondition／steps 的測試對象從機台帳號換成線上會員）。兩組都抓到 blocker，且都看穿了機制：

- A：「疑似從姊妹 TC（AC-0091）複製貼上後忘記把『線上會員（非機台帳號）』改成『機台帳號』」
- B：「照此執行只會驗到 AC-0091（線上顯示「—」），實質無法驗證 AC-0092」

這類錯誤是 structural gate 無法攔的（AC 歸屬規則補了也攔不到），且比 v1 舊 E6 更接近真實的複製貼上失誤，兩組都抓到是好消息。

### 3.3 E8：A 靠 rationale、B 完全沒提

- **A** 的 advisory 逐字引用 rationale：「design_rationale『…採 error_guessing 技巧』，但 test_types: [functional]、design_techniques: [requirement_based]」——issue_type 甚至直接叫 `label_inconsistent_with_rationale`。跟 v1 的抓法一模一樣：比對兩段文字，不是判斷案例性質。
- **B** 的 issues／advisories 裡**沒有任何一條指向 692S4G**。B 不是沒在看標籤——它有一條 `*` advisory 說 S839EP／SHW7C4「test_types 含 negative 但 design_techniques 只有 requirement_based」——但它看的是**標籤之間**的一致性，沒有做「這條 TC 的 expected 是『皆不變動』，性質是反向驗證，卻標 functional」這個**內容→性質**的判斷。

兩次含 rationale（v1、v2-A）都是 minor 靠 rationale，一次剝除（v2-B）漏抓，機制解釋清楚（A 的證據就是 rationale 本身），這不是 run-to-run 雜訊。

### 3.4 誤報

兩組對 C1 都未報 blocker／major。A 的另一條 advisory（EZBK 的 location 顆粒度）與 B 的兩條（Y1T8 precondition 承上一條 TC；高風險 req 的 non-happy 覆蓋本身就是 blocker 案例）都是合理觀察，不算誤報。

## 4. 結論與建議

**契約可以照做。** 生產派工把 `design_rationale` 從給 Validator 的 draft 剝除，代價只有「標籤與內容不符」這一類從弱抓到變漏抓，而這類錯誤：

1. 本來就只是 minor（v1、v2-A 都沒把它當 issue，只放 advisory）
2. 不影響 TC 能不能正確驗收 spec——它是分類標籤錯，不是內容錯
3. 對 high-risk requirement 已有 deterministic 兜底：`gates.g_design` 要求 high risk 必須有 non-happy 覆蓋，標籤錯到讓 high-risk 失去 non-happy 覆蓋時 gate 會擋

換來的是符合契約設計初衷（避免同源偏誤——Validator 不再能「看 Designer 怎麼說服自己」），且本次資料顯示 B 的描述不比 A 弱。

**若想把 E8 補回來**，方向不是還給 rationale，而是在 Validator 的檢查清單裡明確加一條「性質判斷」：`expected_result` 斷言「不變／不顯示／不存在／被拒絕」的 TC，`test_types` 應含 `negative`。這是 `agents/test-validator.yaml`／派工 prompt 層的改動，不必動程式；是否加、加在哪，留給人決定。

**是否剝除、何時剝除是流程決策**，本 eval 只提供證據；不在這裡改派工方式。

## 5. 限制

| 限制 | 說明 |
|---|---|
| 單次、單 spec、單模型 | 與 v1 相同；E8 的結論有機制解釋支撐，但仍是 n=1 的對照 |
| LLM 非確定性 | A/B 的細部措辭差異（例如 B 多的旁證）可能是雜訊，不能歸因於變因；只有 E8 的有／無是可歸因的 |
| 只剝了 `design_rationale` | Report 的 `self_check`（契約也提到「self_check 以外的內部說明」）本次未動，因為它是結構化布林值不是推理；若要完全依契約，可再做一組同時剝 self_check 的 C 組 |
| 未測 Opus | v1 §8 的「同一份錯誤 draft 跑 Sonnet 與 Opus 各一次」仍未做；本次兩組都是 Sonnet，結論只對 Sonnet Validator 成立 |
