# Phase 3 影子測試紀錄：qaos-test-designer × SPEC-CASHFLOW-001

- **日期**：2026-09-16
- **Run**：RUN-20260916-002（spec-to-testcase，spec_id=SPEC-CASHFLOW-001, spec_version=0.1）—— 已於整合完成後 `run cancel`
- **目的**：第二次讓 `.claude/agents/qaos-test-designer.md` 獨立扮演 Test Designer，這次是真正透過 `Agent` 工具背景派工執行（MEMBER 那次多數是人工手寫腳本模擬）。同一份 RequirementModel（44條 ACTIVE Requirement），Phase 2 已由人工核准 61 條 ACTIVE TestCase。Agent 獨立設計出 47 條 TestCaseDraft，送獨立 Validator（每輪皆為全新、無共享 context 的 subagent）審查。
- **結果**：G-DESIGN 三輪迭代後 PASS（過程中因累計 3 次 Structural FAIL 觸發 supervisor 熔斷，經人工 retry 解除）；G-TVAL 三輪 PASS；隨後進行 Phase 2×3 交叉比對整合。

---

## Test Designer 產出階段（T1→T2, G-DESIGN）

47 條 TC，覆蓋 42/44 requirement、66/69 AC，一次性由 Agent 完成（未如 MEMBER 那樣刻意排除既有 TC 參考，因 T1 spec-analyst 階段判定 RequirementModel 已存在而自動跳過，直接進入 T2 設計）。

過程中累計 3 次 Structural FAIL（`state_change` 不在 test_types 枚舉 / `revision_of_issues[0].draft_id` 型別錯誤 / quote 欄位超過 300 字上限），觸發 supervisor 熔斷開出 **APR-0099**（NEEDS_DECISION，3次累計非連續），人工核准 retry 後解除，G-DESIGN 最終 PASS。

## 獨立驗證階段（T3, G-TVAL）三輪演進

| 輪次 | 判定 | 主要發現 |
|---|---|---|
| 1 | FAIL | major：REQ-CASHFLOW-008/AC-CASHFLOW-0083 未被 coverage_matrix 或 uncovered_with_reason 記載（RequirementModel 本身 statement 已於前一日修正但 AC/states 未同步），且轉述給 Validator 的任務描述與實際檔案內容不符（design_rationale 實際是空字串）—— Validator 正確地沒有採信轉述，改依實際檔案判斷；minor：4條 decision_table 中3條誤標 |
| 2 | FAIL | blocker：72%（34/47）TC 的 design_rationale 為空字串（第一輪只挑出2條，第二輪換一個全新獨立審查者才發現這是系統性問題，非個案）；major：47/47 TC 的 expected_result_spec_reference 皆缺少 quote 欄位 |
| 3 | PASS | 僅2個minor（步驟指示不夠明確、revision_of_issues記錄不完整） + 4個advisory（多為報告可讀性/效率建議） |

**關鍵觀察**：第二輪抓到的「72% design_rationale 空白」是第一輪完全沒發現的系統性問題——證明每輪換一個全新、無共享 context 的獨立審查者，比重複使用同一個審查脈絡更能避免「審查盲點固化」。

---

## Phase 2 × Phase 3 交叉比對整合

沿用 MEMBER 確立的原則：**深度底線（不能誤判）> 廣度覆蓋（不能留白）> 深度精進（可以慢慢做）**，逐條交叉比對兩邊的實際斷言內容，而非依文字相似度等機械代理指標篩選（原因：文字相似度可能讓語意上有實質差異、但用字高度重疊的配對被誤判為「等價」而漏審——MEMBER 那次的提領門檻定義爭議就是這種典型案例）。

### 涵蓋圖（69條AC）

- 兩邊都覆蓋：66（其中64條為1:1對應）
- 兩邊都沒覆蓋：1（AC-CASHFLOW-0083，RequirementModel本身的AC/statement資料落差，兩邊獨立判斷皆為不適用，殊途同歸）
- 只有Phase2覆蓋：2（AC-CASHFLOW-0421/0431，spec明確標「待確認」，Phase2用exploratory TC暫依假設提供臨時覆蓋，CLR-CASHFLOW-001/002仍OPEN未回覆，Phase3判斷「不確定就不測」而未涵蓋）
- 只有Phase3覆蓋：0

### 逐條讀完66組assertion後的判讀

59組確認語意等價（差異僅為TC拆分方式或措辭詳略），維持Phase2原版不動。7組（對應5個AC群組）標記需要深入比對，逐一讀完steps/preconditions後：

| TC | AC | Phase3的加值是否成立 | 處置 |
|---|---|---|---|
| TC-CASHFLOW-005 | 0041 | 成立：Phase2只測單邊，Phase3測邊界兩側+交易紀錄斷言 | 整合，v2 |
| TC-CASHFLOW-008 | 0071/0072 | 成立：同上模式 | 整合，v2 |
| TC-CASHFLOW-018 | 0151/0152 | 成立：Phase2的"缺漏或非數值"合併成一步可能漏測 | 整合，v2 |
| TC-CASHFLOW-026 | 0221 | 成立：Phase2只有抽象斷言，Phase3具體操作出情境 | 整合，v2→v3（見下方事故） |
| TC-CASHFLOW-027/061 | 0231/0232 | **不成立，Phase3反而漏測**：Phase3合併兩情境時，把"收據送入列印佇列後才卡紙缺紙→收據待現場排除後自動印出"簡化成"視角等同印表機正常完成"，遺漏了Phase2原本測到的收據佇列/自動補印行為 | **不採用Phase3合併版，維持Phase2原版TC-027/061不動** |

### 中途事故：Claude自己的未查證斷言，被獨立Validator抓到兩次

處理TC-CASHFLOW-026整合時，第一版design_rationale宣稱「新req-cashout取代」這個觸發路徑已由TC-CASHFLOW-022涵蓋、不重複建立，因而把AC-CASHFLOW-0221自己given範例明講的情境砍掉——**這個宣稱沒有實際查證TC-CASHFLOW-022的完整內容就寫下**（TC-022只有2個步驟，只測PENDING狀態轉換本身，完全沒測後半段end-cashout回1-NO RECORD）。獨立Validator查證後判FAIL，v2把兩個情境補回。

修正v2時，又把僅屬於end-cashin條款的「不變更任何資料」誤植到end-cashout的quote欄位上（且改寫非逐字引用），違反本專案quote欄位一貫要求的逐字忠實慣例，被第二輪獨立Validator再次抓到，v3修正為逐字引用。

**教訓**：獨立驗證機制存在的價值，不只是抓agent的錯，也包括抓orchestrating session（也就是Claude自己）在轉述、判斷「是否已被涵蓋」時的未查證斷言——這次連續兩輪都被抓到，而不是自己主動發現。之後每次寫「已由XX涵蓋、不重複」這類排除理由之前，應先實際讀取被引用TC的完整內容，而非依標題/AC關聯推測。

### 最終處置

- TC-CASHFLOW-005/008/018/026 四條：核准為 v2（026經三輪迭代），APR-0101~0104
- APR-0100（原「47條Phase3草稿整批變ACTIVE」）：**reject**——有價值的內容已個別併入Phase2既有TC，不整批啟用避免佔用Registry新編號、重複既有覆蓋
- RUN-20260916-002：整合完成後 `run cancel`

### 與MEMBER整合的差異

MEMBER當時Phase2×3的AC層級落差較大、需要處理一次誤核准事故；CASHFLOW這次AC層級高度收斂（64/66為1:1對應），真正需要深入比對的只有7組，但過程中發現Phase3合併多情境TC時有真實的覆蓋率倒退案例（027/061），且Claude自己在判斷「是否已被涵蓋」時犯了兩次未查證錯誤——顯示交叉比對整合本身也需要跟Test Designer產出同等嚴格的獨立審查，不能因為是「orchestrating session做的修訂」就降低審查標準。
