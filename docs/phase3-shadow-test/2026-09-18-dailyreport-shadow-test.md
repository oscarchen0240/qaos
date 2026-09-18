# Phase 3 影子測試紀錄：qaos-test-designer × SPEC-DAILYREPORT-001

- **日期**：2026-09-18
- **Run**：RUN-20260918-007（spec-to-testcase，spec_id=SPEC-DAILYREPORT-001, spec_version=0.1）—— COMPLETED
- **目的**：波次3（DAILYREPORT獨立派工）。場館日結報表是本專案目前規模最大的規格之一（17條requirement、43條AC），Phase 2 已有 54 條 ACTIVE TestCase，這次首度改用真正的 `qaos-test-designer` subagent（而非人扮agent腳本）獨立設計，且刻意不讓它讀取 Phase 2 既有 TC 以維持交叉比對的獨立性。
- **結果**：G-DESIGN 首輪即 PASS（43條TC，17/17 requirement、43/43 AC全覆蓋）。過程中發現一個影響交叉領域的系統性問題（見下），修正後 G-TVAL 兩輪PASS。

---

## 系統性問題：`clarification apply` 不會自動把答案寫回 RequirementModel

在正式派工Test Designer之前，我依使用者要求逐一驗證了26張此前ANSWERED但未APPLIED的CLR，確認內容已落地後批次補跑apply。但DAILYREPORT的Test Designer草稿產出後，其中3條exploratory TC有2條的「疑義」實際上已經被CLR-DAILYREPORT-007、CLR-DAILYREPORT-009正式回答過——只是`clarification apply`這個指令本身只會轉CLR自己的status，**不會**自動把答案內容寫回RequirementModel的statement/rejection_contract，導致只讀RequirementModel的Test Designer仍看到「未解的ambiguity」。

進一步排查全部25張已apply的CLR後發現：僅2張（CLR-SITELIST-007、CLR-TXLOG-001）因整個需求描述情境已變成moot而被正確改寫；其餘18張（ACCOUNT 5、DAILYREPORT 7、SITELIST 6）的`rejection_contract.description`都還停留在「Spec未定義拒絕行為」的模板文字。已依使用者指示，將這18張的答案內容正式套用進對應RequirementModel（詳見`tools/manual-runs/batch_18_clr_apply.py`），並修正DAILYREPORT自己的REQ-009、REQ-015 statement（詳見`tools/manual-runs/req_dailyreport009_clr007_apply.py`、`req_dailyreport015_clr009_apply.py`）。

同時，依CLR-DAILYREPORT-009修正了Phase 2既有的`TC-DAILYREPORT-046`（新版本v2，透過正式的`testcase-revision` workflow產生，RUN-20260918-006，APR-0122核准，v1 SUPERSEDED）——該TC原本的斷言方向（未兌現金額不受結算日期範圍限制）已被PM正式推翻。

## 設計與驗證階段

**Test Designer首次提交即G-DESIGN PASS**：43條TC，17/17 requirement、43/43 AC全覆蓋。3條exploratory TC（各自requirement下皆僅1條，遠低於MAX_EXPLORATORY_PER_REQ=3上限）：
- REQ-DAILYREPORT-009（場次數計算）、REQ-DAILYREPORT-015（未兌現金額範圍限制）：因RequirementModel未同步CLR答案而誤判為ambiguity，已修正為grounded案例（見上）
- REQ-DAILYREPORT-010（過渡期無印表機機台的辨識方式）：真正無依據的exploratory，保留

**第一輪獨立Validator FAIL**（1個major）：我修正REQ-009那條TC時，只在expected_result文末補了CLR-007引用句，卻沒把公式/precondition一併理順——expected_result寫『已結束+逾時結束+日結結算』三者相加，卻又在同段引用CLR-007『只會以已結束或日結結算收尾』的結論，自相矛盾；precondition要求尋找『當日逾時結束』樣本，但依CLR-007的推理這在當日範圍內結構上不應出現，等於要求執行者找一個理論上不存在的資料。

**修正**：聚焦驗證『已結束+日結結算』兩者相加＝場次數，移除逾時結束樣本要求，並與既有的「僅已結束」保守案例明確做分工區隔（一條驗證基本加總邏輯、一條專門驗證CLR-007新確認的關鍵規則「日結結算也要計入」）。

**第二輪獨立Validator PASS**：確認矛盾已解、precondition不再要求不可能的樣本、與既有TC無重複，僅剩1個文件殘留的minor advisory（另一條TC的design_rationale還留著過時措辭），已順手清理。

## Phase 2 × Phase 3 交叉比對

43條AC全部兩邊都覆蓋，其中42條Phase2/Phase3覆蓋量相當（Phase2本身就非常詳盡，54條TC對43條AC）。**僅1組Phase3比Phase2多TC**：

- **AC-DAILYREPORT-0092**（依場館彙總的場次數＝所有機台場次數加總）：Phase2的TC-029只測了純「已結束」狀態的具體數字案例（機台A 3場+機台B 2場=5場）；Phase3的其中一條與此重疊（不採用），但另一條專門驗證「日結結算狀態的場次同樣計入場次數彙總，不因是被強制結束而排除」——這正是本次CLR-DAILYREPORT-007新確認的關鍵規則點，Phase2完全沒有測試這個角度——**採用**

**最終處置**：依ADR-007走輕量方式，用`bin/qaos approve APR-0123 --decision reject --per-item TC-DAILYREPORT-077:approve`核准這1條新增TC，其餘42條Phase3草稿不採用。核准後獨立查驗Registry狀態，確認恰好1條變ACTIVE。

**結果**：Phase2既有54條ACTIVE TC + 新增1條（TC-DAILYREPORT-077）= 55條ACTIVE。

## 關鍵教訓

1. **`clarification apply` ≠ 答案真正落地**：這是本次最重要的系統性發現。CLR的狀態機制（OPEN→ANSWERED→APPLIED）只追蹤「這個問題本身的處理進度」，不會自動同步答案內容到RequirementModel——這個同步動作必須額外用manual-run腳本手動執行。往後每次apply一張CLR，都應該同時檢查對應REQ的statement/rejection_contract是否已經反映答案內容，而不能假設apply完成就代表資訊已經傳遞到位。
2. **即使已經修正RequirementModel，還是要盯緊Test Designer後續設計出的TC本身**：修正REQ-009的statement後，Test Designer當初設計的TC（在修正前產出）需要我手動同步調整，而我第一次調整時只改了expected_result的文字結尾、沒有把整條TC的precondition/公式一併理順，反而製造了新的自相矛盾——這正是本專案一貫強調的「不能倉促修補，要通盤檢視」的教訓再次應驗，而這次是連我自己的修正動作都需要被獨立Validator抓出問題，顯示這道獨立審查機制的必要性不僅適用於Test Designer agent，也適用於我自己的手動修正。
3. **本次首度使用真正的qaos-test-designer subagent**（而非人扮agent腳本），且刻意不讓它讀Phase2既有TC以維持獨立視角，結果證明可行：43條TC首輪即G-DESIGN PASS，交叉比對後也只有極少數重疊（僅1條AC有新增空間），顯示這個獨立設計視角本身的品質是可信賴的。
