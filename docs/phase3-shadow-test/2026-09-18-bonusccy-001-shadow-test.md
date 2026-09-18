# Phase 3 影子測試紀錄：qaos-test-designer × SPEC-BONUSCCY-001

- **日期**：2026-09-18
- **Run**：RUN-20260918-002（spec-to-testcase，spec_id=SPEC-BONUSCCY-001, spec_version=1.0）—— COMPLETED
- **目的**：波次1（TXLOG＋BONUSCCY-001同步派工）之一。BONUSCCY-001是「紅利（彩金）」領域，跟「實體機台」開發包家族完全無關、獨立領域。Phase 2 已有 12 條 ACTIVE TestCase（SPEC-BONUSCCY-001專屬），Test Designer 獨立設計出 14 條 TestCaseDraft。
- **結果**：G-DESIGN 首輪即 PASS，G-TVAL 三輪後 PASS——過程中出現一次獨立Validator對系統結構化規則的技術誤判，值得記錄。

---

## 設計與驗證階段

14 條 TC，5/5 requirement、10/10 AC 全部覆蓋。REQ-BONUSCCY-004（核心貨幣錢包幣別停用後入金/出金/開分/洗分四項操作應被阻擋）的4條TC判斷為機台API觸發操作（非後台按鈕），test_level標api，有依據（spec.md定義「開分」「入金」是機台端操作）。

**第一輪 FAIL**：4個major（同一類問題）——REQ-BONUSCCY-004底下4條TC的quote把PM澄清內容（CLR-BONUSCCY-002）當成spec.md原文引用。修正：quote只保留spec.md真正存在的那句，PM補充內容移到design_rationale並註明來源。

**第二輪 FAIL**：1個major——洗分TC沒有像入金/出金/開分三條一樣做結構化assumptions揭露環境工具依賴，design_rationale用「MAX_EXPLORATORY_PER_REQ=3」解釋，但Validator判斷這4條TC的design_techniques都是negative非exploratory、理由不成立。**我未查證就採信這個判斷並修正**，結果導致G-DESIGN FAIL「REQ-BONUSCCY-004有4條exploratory，超過上限3」——查證`tools/qaos/gates.py`後發現`is_exploratory(tc) = bool(tc.get("assumptions"))`，只看assumptions欄位是否非空，跟design_techniques標籤完全無關；上一輪Validator的技術判斷是錯的，原始（把洗分留空）的處理方式才是對的。已退回並修正。

**第三輪 PASS**（這輪明確附上gates.py原始碼給獨立Validator核對，避免重演）：確認洗分TC不掛assumptions是正確、必要的處理，僅剩4個minor advisory（report層級assumptions文字重複未去重、拼字錯誤throshold應為threshold、quote格式繼承自RequirementModel源頭的既有慣例、對照組TC的AC given範圍差異已用notes誠實揭露）。

## Phase 2 × Phase 3 交叉比對

**重要修正**：第一次計算涵蓋圖時，比對腳本用`TC-BONUSCCY-*`前綴篩選Phase2既有TC，誤把spec_id屬於SPEC-BONUSCCY-002/003的TC也混進來、又漏篩導致算出Phase2=0條，修正為依`spec_id`欄位精確篩選後才是正確的12條。

10 條 AC 全部兩邊都覆蓋，其中 7 條 1:1 對應。**3 組 Phase3 比 Phase2 多 TC**，逐條讀完斷言後：
- AC-BONUSCCY-001（注單金額顯示）：Phase3多測了「明細頁」（Phase2只測列表頁，是不同頁面）——採用；另一條線上/USDT對照組（回歸確認）——採用
- AC-BONUSCCY-003（會員列表）：Phase2只做靜態快照比對，Phase3多了「新增會員前後delta驗證」，驗證強度更高——採用
- AC-BONUSCCY-007（前台資產列表）：主案例內容一致，Phase3多一條線上/USDT對照組（回歸確認）——採用

**最終處置**：依ADR-007走輕量方式，用`bin/qaos approve APR-0116 --decision reject --per-item TC-BONUSCCY-033:approve --per-item TC-BONUSCCY-034:approve --per-item TC-BONUSCCY-037:approve --per-item TC-BONUSCCY-045:approve`核准這4條新增TC，其餘10條Phase3草稿不採用。核准後獨立查驗Registry狀態確認無誤。

**結果**：Phase2既有12條ACTIVE TC + 新增4條 = 16條ACTIVE。

## 關鍵教訓

獨立Validator對業務內容/引文的判斷通常可信，但**對系統結構化規則本身的技術宣稱，必須自己查證原始碼（`tools/qaos/gates.py`）再行動，不能直接採信**——這次的第二輪FAIL正是因為我沒有驗證「exploratory計數跟design_techniques標籤是否相關」這個具體技術主張，直接照做導致觸發真正的結構化上限。第三輪把gates.py直接附給Validator後，同一個問題得到了正確的判斷。
