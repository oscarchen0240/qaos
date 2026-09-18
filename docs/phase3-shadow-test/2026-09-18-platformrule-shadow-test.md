# Phase 3 影子測試紀錄：qaos-test-designer × SPEC-PLATFORMRULE-001

- **日期**：2026-09-18
- **Run**：RUN-20260918-010（spec-to-testcase，spec_id=SPEC-PLATFORMRULE-001, spec_version=0.1）—— COMPLETED
- **目的**：波次5（PLATFORMRULE獨立派工）。機台場館平台規則（開發包⑥）涵蓋既有功能排除規則、機台場館後台選單顯示規則、操作員角色與權限、機台場館遊戲更新規則四大面向，23條requirement、31條AC，是CASHOUT那次CLR-CASHOUT-001（操作員無場館切換權限）確認規則的正式來源spec。Phase 2 已有 32 條 ACTIVE TestCase，Test Designer（`qaos-test-designer` subagent，未讀Phase2既有TC）獨立設計出 32 條 TestCaseDraft。
- **結果**：G-DESIGN首輪即PASS，G-TVAL兩輪PASS。核准過程一度出現本專案首次的「整批approve」情形（見下方說明），事後已修正回歸交叉比對分析建議的範圍。

---

## 設計與驗證階段

**Test Designer首次提交即G-DESIGN PASS**：32條TC，22/23 requirement覆蓋（REQ-PLATFORMRULE-011留有uncovered_with_reason）、31/31 AC全覆蓋（其中REQ-011的AC-0111因該REQ本身無法設計黑箱TC而未覆蓋，故AC覆蓋實際30/31）。7條exploratory TC，分散於REQ-001/002/013/015/021×2/023，均未超過MAX_EXPLORATORY_PER_REQ=3。這次特別要求Test Designer吸取上一波次（UPDATEPACK）的教訓，主動檢查環境依賴假設是否誠實揭露，結果在REQ-013/015（測試環境需要至少兩個既有機台場館）確實做到位。

**第一輪獨立Validator FAIL**（1個major）：TC-DRAFT-...ZT6FKHGJWTR0YS6N（REQ-PLATFORMRULE-013）的quote把spec.md中相隔11列的『可見場館範圍』與『場館日結報表』兩個表格列拼接成看似連續的原文，是本輪Test Designer自行新造（非繼承自RequirementModel）的quote真實性問題。另有1個minor：TC對前一條TC的執行順序有隱性依賴。

**修正**：quote改回單一列（與REQ-013本身spec_reference一致），另一列的引用移到design_rationale說明；TC補上獨立可執行的因應說明。

**第二輪獨立Validator PASS**：確認兩項修正皆正確、無regression。另有3個advisory維持不強制修正：REQ-010、REQ-018的quote拼接問題繼承自RequirementModel既有內容（非本輪新造）、design_techniques裡的「scenario」標籤合法性存疑（gates.py無白名單機制，不構成結構性違規）。

## Phase 2 × Phase 3 交叉比對

30條AC（扣除REQ-011未覆蓋的1條）全部兩邊都覆蓋，其中28條Phase2/Phase3內容相當。依本專案一貫的「深度底線＞廣度覆蓋＞深度精進」交叉比對分析，僅2組Phase3有明確新增價值：

- **AC-PLATFORMRULE-0131**（操作員可見場館範圍，跨頁通用規則）：Phase2的TC-016選「機台交易紀錄查詢頁」作為具體驗證頁面；Phase3新增一條專門驗證「場館日結報表」頁面（AC-0131字面點名的頁面），用不同頁面驗證同一條跨頁通則，提高「這確實是跨頁通用、不是某一頁碰巧對」的信心——**採用**
- **AC-PLATFORMRULE-0151**（機台交易紀錄查詢頁角色範圍：Admin全部/站長管轄範圍/操作員自身場館）：Phase2的TC-019只測了操作員一個角色，完全沒有測到Admin/站長；Phase3新增一條專門驗證Admin查全部、站長查管轄範圍——**採用**
- 其餘30組Phase3 TC與Phase2既有內容重疊度高，**不採用**

**核准過程的插曲**：APR-0125一度於外部「QAOS指揮台」介面被使用者整批approve（32條Phase3草稿全數變ACTIVE，非per-item篩選），事後使用者發現TC數量從32條暴增為64條而追問，確認是誤以為指揮台上的操作等同於「看過交叉比對建議後核准」，實際上並未看到本session的分析內容。確認後已用`bin/qaos tc retire`將不建議採用的30條正式退役（APR-0126~0155），回歸分析建議的範圍。

**最終處置**：依ADR-007走輕量方式，僅保留TC-PLATFORMRULE-048、051這2條新增TC，其餘30條Phase3草稿退役。核准後獨立查驗Registry狀態，確認恰好34條ACTIVE。

**結果**：Phase2既有32條ACTIVE TC + 新增2條（TC-PLATFORMRULE-048、051）= 34條ACTIVE。

## 關鍵教訓

1. **核准動作可能發生在本session之外、且執行者不一定清楚該次操作的實際範圍**：本專案的approve指令可透過QAOS指揮台等外部介面直接執行。這次的整批approve並非使用者看過per-item分析後的刻意選擇，而是介面操作與本session的分析結果脫節所致——「已核准」不等於「已依分析建議核准」，發現數量異常時應主動查證，而非假設一切如常。
2. `bin/qaos tc retire`提供了ACTIVE→RETIRED的正式修正路徑（走state-machine定義的ApprovalDecision(RETIRE_TESTCASE)），可在核准範圍需要事後修正時使用，不需要繞過正式流程直接改檔案。
