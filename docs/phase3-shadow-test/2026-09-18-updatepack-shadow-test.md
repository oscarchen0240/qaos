# Phase 3 影子測試紀錄：qaos-test-designer × SPEC-UPDATEPACK-001

- **日期**：2026-09-18
- **Run**：RUN-20260918-009（spec-to-testcase，spec_id=SPEC-UPDATEPACK-001, spec_version=0.1）—— COMPLETED
- **目的**：波次4（UPDATEPACK獨立派工）。機台更新包收錄六個開發包發出後才定案的規格，RequirementModel僅正式收錄其中「多幣別錢包展開顯示」「存款/提款累計欄位」「交易紀錄場次編號」相關的9條requirement（spec.md其餘章節——機台憑證JWT、洗分門檻、餘額不足不寫入交易紀錄、日結報表場次數、入金額度預留——依spec.md自身的「本包範圍」表格，正式歸屬在其他開發包的spec，不在本次範圍）。Phase 2 已有 16 條 ACTIVE TestCase，Test Designer（`qaos-test-designer` subagent，未讀Phase2既有TC）獨立設計出 16 條 TestCaseDraft。
- **結果**：G-DESIGN首輪即PASS，G-TVAL兩輪PASS。

---

## 設計與驗證階段

**Test Designer首次提交即G-DESIGN PASS**：16條TC，9/9 requirement、15/15 AC全覆蓋，0條exploratory（初版宣稱：所有requirement的rejection_contract.defined皆為true，未觸發exploratory強制路徑）。

**第一輪獨立Validator FAIL**（1個major+3個minor）：獨立審查被特別要求質疑「0條exploratory」這個宣稱是否站得住腳，結果確實抓到問題——TC-DRAFT-...JQVXNJ74BV2SV1JAD（REQ-UPDATEPACK-002，驗證1種vs2種以上幣別展開箭頭門檻）的precondition依賴「既有機台場館測試站台」這個環境事實（機台場館是本更新包才涉及的內部新場景），卻未像其他TC那樣附加應變條款或用assumptions標註。另外3個minor：TC2缺少幣別復原步驟（會污染同站台其他TC前提）、TC4的quote引用不夠精準（引了表格列名而非實際規則文字）、TC11/TC12對negative標籤的判斷不一致。

**修正**：TC3補上assumptions揭露環境fixture依賴（改為1條exploratory，遠低於MAX_EXPLORATORY_PER_REQ=3）；TC2補復原步驟；TC4改引更精準的spec段落；TC12補negative標籤與TC11一致。同時順手修正了requirements.yaml中REQ-UPDATEPACK-008的quote（原本帶有非逐字前綴「本功能說明：」，後續又發現拼接了spec.md兩段不連續文字，已用刪節號標示清楚）。

**第二輪獨立Validator PASS**：逐項核對5處修正皆正確、完整，未發現新問題，僅剩1個advisory（REQ-008 quote的刪節號標示，屬於已充分處理的殘留瑕疵）。

## Phase 2 × Phase 3 交叉比對

15條AC全部兩邊都覆蓋，其中14條Phase2/Phase3覆蓋量相當。**僅1組Phase3比Phase2多TC**：

- **AC-UPDATEPACK-0031**（收合時顯示核心貨幣餘額，不做匯率換算也不是加總，REQ-UPDATEPACK-003為high risk）：Phase2的TC-UPDATEPACK-006是一條籠統的單一TC，expected_result同時斷言「是核心貨幣原始餘額」與「不是加總/換算」兩件事，但steps只寫「檢視收合狀態的帳戶餘額欄」，沒有具體記錄任何比對數值，執行時容易流於主觀判斷、缺乏明確可重複驗證的依據。Phase3把這句話拆成兩條更嚴謹的TC：一條做正向對照（先展開記錄核心貨幣列金額，再收合比對是否相同）；另一條做排他驗證（手動計算各幣別加總值作為對照組，且刻意選用數值相差一個數量級的測試資料以確保比對有鑑別力，並考慮了「非核心貨幣餘額恰為0」導致比對失去鑑別力的edge case、提出改選其他會員的因應）——後者正是REQ-UPDATEPACK-003這個high risk requirement所需、但Phase2版本實質缺乏的排他/non-happy-path覆蓋——**兩條皆採用**

**最終處置**：依ADR-007走輕量方式，用`bin/qaos approve APR-0124 --decision reject --per-item TC-UPDATEPACK-021:approve --per-item TC-UPDATEPACK-022:approve`核准這2條新增TC，其餘14條Phase3草稿不採用。核准後獨立查驗Registry狀態，確認恰好2條變ACTIVE。

**結果**：Phase2既有16條ACTIVE TC + 新增2條（TC-UPDATEPACK-021、022）= 18條ACTIVE。

## 關鍵教訓

1. **「0條exploratory」的宣稱值得被主動質疑，不能只看gates.py的結構性通過就照單全收**：is_exploratory的判定只看assumptions欄位是否非空，一條TC即使實質上依賴一個未經確認的環境事實（測試環境是否有機台場館站台），只要Test Designer沒有主動把這個依賴寫進assumptions，gates.py就不會攔下來、也不會被算進exploratory計數。這次特別指示獨立Validator針對這個宣稱做重點質疑，才抓出了這個原本會被結構性檢查放行的缺口。
2. **一句話涵蓋兩個斷言的Phase2 TC，可能在Phase3拆解後才顯現原本的驗證強度不足**：TC-UPDATEPACK-006的expected_result文字本身沒有錯，但因為steps缺乏具體比對依據，正向確認與排他驗證兩個角度都沒有被扎實驗證到。這提醒了交叉比對不能只看「兩邊是否都有TC覆蓋同一個AC」，還要細看實際的steps是否提供了可重複執行、有鑑別力的驗證方法，即使Phase2的expected_result表面上看起來完整。
