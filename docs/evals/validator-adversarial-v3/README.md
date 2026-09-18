# Validator 對抗性 eval v3：契約 1.1.0 的性質判斷檢查能否補回 E8

- **日期**：2026-09-19
- **依據**：v2 結論——剝除 `design_rationale` 後 E8（標籤與內容不符）由弱抓到轉漏抓；v2 §4 建議「在檢查清單加一條性質判斷」。`agents/test-validator.yaml` 已於 1.1.0 加入該條（commit a2aa82c）；v3 驗證它有沒有用
- **結果**：**部分補回，不穩定**——同一份剝除 rationale 的錯誤 draft、同一段 prompt 跑兩次：run 1 漏、run 2 弱抓到（minor）。E1～E7 兩次皆實質抓到、誤報 0、皆 FAIL
- **本目錄可重現**：素材 = v2-B（v1.1 `inject_errors.py` 產出後 `strip_rationale.py`）；prompt = v2 逐字，僅第 7 項換成 1.1.0 契約原文；評分用 v1 `score.py`；`result_run{1,2}.json`、`score_run{1,2}.txt` 為本次實際資料

---

## 1. 設計：單一變因

與 v2-B 相比只改一處——審查項目第 7 項：

| | v2-B | v3 |
|---|---|---|
| 第 7 項 | 「design_techniques／test_types 標籤：標籤是否與案例的實際性質相符。」 | 「test_types／design_techniques 與案例實際性質相符（性質判斷，只看 Draft 內容不看 Designer 說明）：expected_result 斷言『不變動／不顯示／不存在／不提供／被拒絕』等反向結果者應含 negative；驗證邊界值者應含 boundary；標籤與性質不符→advisory（minor），若導致 high-risk requirement 失去實質 non-happy 覆蓋→major。」 |
| 其餘 7 項、素材、模型（Sonnet）、派工方式 | 同 | 同 |

也就是說 v2-B 本來就有「標籤是否相符」這句，v3 加的是**判準**（什麼算反向）與**分級規則**。

## 2. 結果

| # | 類型 | TC | v2-B（無判準） | v3 run 1 | v3 run 2 |
|---|---|---|---|---|---|
| E1 | quote 語意竄改 | SR5Y6J | blocker | blocker | blocker |
| E2 | expected 違反 spec | 1HJXYJ | blocker | blocker | blocker |
| E3 | steps 與 AC 錯配 | CN7R3V | major | major | major |
| E4 | 未揭露的虛構機制 | YKAH1N | major | major | major |
| E5 | 自相矛盾 | T55KVR | blocker | blocker | blocker |
| E6 | AC given 偷換 | 6WNBVZ | blocker | blocker | blocker |
| E7 | 覆蓋宣稱不實 | SHW7C4 | major | major | major |
| E8 | 標籤與內容不符 | 692S4G | **漏** | **漏** | **minor** |
| C1 | 對照組 | SV1JAD | 無誤報 | 無誤報 | 無誤報 |

三次（含 v2-B）E1～E7 的 severity 完全相同、落在同一組 TC；誤報皆 0。

## 3. 人工核對

### 3.1 run 2 的 E8 是真的性質判斷

advisory 原文：「AC-0082 斷言『兩者皆不變動』，屬反向／不變動結果，但本 TC test_types 僅為 [functional]，design_techniques 僅 [requirement_based]，未標 negative」——證據是 AC then 與 expected 的內容，檔案裡已經沒有 rationale 可比對。severity 推理也照新規則：「不影響 REQ-008 的 gates.py non-happy 覆蓋（同 AC 組 TC13 已標 negative），故列為 minor 而非 major」。這正是 1.1.0 契約想要的判斷方式，跟 v1／v2-A 靠「rationale 說 A、欄位說 B」的文件比對是不同機制。

### 3.2 run 1 為什麼漏：判準有生效，但沒打在目標上

run 1 並非忽略第 7 項——它在兩處套用了：

- **S839EP**（背景 TC，正確）：報「expected 屬反向斷言，test_types 已含 negative，但 design_techniques 僅 requirement_based」——判準對，只是這條本來就標對了，落在 minor 也合理
- **SHW7C4**（E7）：報「標 negative 但內容無任何反向斷言」——這是 E7 掏空 steps 後的真實副作用，判得對，run 2 也報了同一點

但對 692S4G，run 1 在 E5 的說明裡引用它兩次當「姊妹案例正確」（斷言方向正確），卻沒回頭看它的標籤。可能的解釋：Validator 在逐條掃時把它歸為「E5 的對照」而不是獨立審查對象。這是 LLM 注意力分配的問題，不是判準寫錯。

### 3.3 E1～E7 穩定

三次結果 severity 逐條相同，issue 描述機制一致（E6 三次都看出「從姊妹 TC 複製忘改」；E7 兩次都同時報覆蓋空洞與標籤不符）。1.1.0 新增的檢查項沒有擠掉其他項目的召回，也沒有帶來新誤報。

## 4. 結論

1. **判準有效，但 Sonnet 單次執行不穩定**：加了具體判準後 E8 從 0/1 變 1/2；run 1 證明模型有讀懂並套用判準（打在 S839EP／SHW7C4），只是對目標 TC 漏掃。
2. **契約 1.1.0 保留**：它讓「性質判斷」變成可執行的檢查，且沒有副作用。剝除 rationale 的生產派工可以照契約做。
3. **這類 minor 級錯誤的殘餘漏抓率可接受**：E8 是分類標籤錯，不影響 TC 能否正確驗收；high-risk 的 non-happy 覆蓋另有 gate 兜底（v2 §4 已論述）。不值得為它把 Validator 升 Opus 或加第二輪審查。
4. **若要再往上推**：不是繼續改 prompt 文字，而是把「反向斷言關鍵詞 → 應含 negative」的部分做成 deterministic 的 advisory（gates.py 或 lint 層，只提示不擋）——這樣 100% 穩定、零 token，Validator 只需處理關鍵詞抓不到的語意情況。是否做，留給人決定。

## 5. 限制

| 限制 | 說明 |
|---|---|
| n=2 | 1/2 只能說「有時抓到」；要估穩定率至少 5～10 次，成本約 125k token／次 |
| 同一份 draft、同一個 E8 樣本 | 「不變動」是判準裡明列的關鍵詞，屬最容易的情況；「被拒絕」「不顯示」等變體未測 |
| 只測 Sonnet | 未測 Opus 是否穩定抓到 |
| 判準關鍵詞列舉式 | 反向斷言的表達方式無窮（「維持原值」「與基準相同」），列舉必有遺漏；run 2 抓到的是 AC then 裡的「不變動」，不是 expected 裡的「完全相同」 |
