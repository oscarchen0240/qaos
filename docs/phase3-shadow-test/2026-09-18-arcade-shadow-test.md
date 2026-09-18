# Phase 3 影子測試紀錄：qaos-test-designer × SPEC-ARCADE-001

- **日期**：2026-09-18
- **Run**：RUN-20260918-011（spec-to-testcase，spec_id=SPEC-ARCADE-001, spec_version=0.7）—— COMPLETED
- **目的**：波次6（ARCADE獨立派工，本次系列最後一波）。ARCADE是整份「實體機台」正本規格（975行），但RequirementModel只從中抽取了6條跨開發包整合一致性檢查點（其餘內容已分別在CASHFLOW/TXLOG/SITELIST/ACCOUNT/CASHOUT/DAILYREPORT/BONUSCCY/UPDATEPACK/PLATFORMRULE等spec個別處理過）；其中REQ-ARCADE-005已於更早的波次（2026-09-14）因與REQ-PLATFORMRULE-014重複而RETIRED。Phase 2 已有 7 條 ACTIVE TestCase，Test Designer（`qaos-test-designer` subagent，未讀Phase2既有TC）獨立設計出 7 條 TestCaseDraft。
- **結果**：G-DESIGN首輪即PASS，觸發本專案首次遇到的exploratory比例NEEDS_DECISION circuit breaker，人工審閱後continue，G-TVAL首輪PASS。

---

## 設計與驗證階段

**Test Designer首次提交即G-DESIGN PASS**：7條TC，5/5 ACTIVE requirement覆蓋（REQ-ARCADE-005因已RETIRED正確排除，記在uncovered_with_reason屬記錄性質）、6/6 AC全覆蓋。

**觸發NEEDS_DECISION（APR-0156）**：7條TC中有5條（71%）是exploratory，超過本專案gates.py的50%閾值，觸發circuit breaker要求人工決定continue/retry/cancel。逐條核對5條assumption內容後，確認全部屬於「機台端硬體現場流程無法由後台UI直接觸發」「測試環境是否已具備特定站台掛載/待核實資料」這類環境依賴性質，非spec業務規則模糊，是ARCADE這個領域（機台實體硬體交易）的天然特性，非Test Designer設計缺陷。本次依使用者要求的核准流程分級，先將分析寫成建議文件（`.warroom/recommendations/APR-0156.md`，建議continue）交由使用者於QAOS指揮台決定，使用者確認continue後run推進到T3。

**獨立Validator審查PASS**：僅1個minor（TC1的quote markdown粗體符號位置誤植，內容語意完全正確、非跨列拼接問題，已直接修正）+ 5項advisory（design_techniques標籤一致性、REQ-ARCADE-002覆蓋深度、assumption中的spec ID推測待追溯查證等，皆不影響PASS）。獨立確認5條exploratory assumption誠實、精確、必要，REQ-ARCADE-002的加盟商站台樹掛載機制推測、REQ-ARCADE-004的稽核公式歸屬推測皆有spec原文佐證方向，判斷合理。

## Phase 2 × Phase 3 交叉比對

6條AC全部兩邊都覆蓋，其中5條AC兩邊數量相同（1:1或2:2）。逐條讀完斷言後：

- **AC-ARCADE-002**（機台流水不計入加盟傭金/代理返傭，high risk）：Phase2/Phase3核心斷言相同，但Phase3多驗證了「該筆機台流水本身在交易紀錄查詢/注單查詢中確實可查得」這個排除偽陰性的機制（證明流水真實發生過，而非「沒增加只是因為根本沒發生」）——**採用**
- **AC-ARCADE-004**（稽核倍數設定與套用效果）：Phase2的TC-004用「稽核明細顯示計算結果反映新倍數」驗證套用效果；Phase3新增一條聚焦「洗分/出金核可金額因未完成稽核而被扣減」的驗證，這是與「稽核明細記錄」相互獨立、可能各自出錯的環節（系統可能正確記錄了倍數卻沒有真的套用進核可金額計算，反之亦然），提供了額外驗證角度——**採用**
- **AC-ARCADE-001、003、006、007**：Phase3版本多為執行細節的補充說明（例如「常見位置逐一檢視」「時間誤差範圍」「確認查詢功能本身未壞」），與Phase2既有斷言深度相當、無淨新增覆蓋角度——不採用

**最終處置**：依ADR-007走輕量方式，用`bin/qaos approve APR-0157 --decision reject --per-item TC-ARCADE-010:approve --per-item TC-ARCADE-013:approve`核准這2條新增TC，其餘5條Phase3草稿不採用。核准後獨立查驗Registry狀態，確認恰好2條變ACTIVE。

**結果**：Phase2既有7條ACTIVE TC + 新增2條（TC-ARCADE-010、013）= 9條ACTIVE。

## 關鍵教訓

1. **本專案首次遇到exploratory比例NEEDS_DECISION circuit breaker**：7條TC中5條exploratory（71%）觸發了gates.py的50%閾值警示。事後分析確認這是分母小（僅7條TC）造成的統計假象，而非設計品質問題——5條assumption的性質高度一致（機台端硬體現場流程依賴），這是ARCADE這個特定領域（機台實體硬體交易）無法避免的天然特性。
2. **核准流程分級的首次實踐**：這是使用者明確要求「run流程層級的決策型單子（NEEDS_DECISION等）不可自主執行，須寫建議文件交由使用者於指揮台決定」這條新規則後的第一次實際應用（APR-0156）。分析建議寫入`.warroom/recommendations/APR-0156.md`，等使用者決定後才接續執行，與Phase2×3交叉比對後的TC採用決策（APR-0157，可自主執行）形成明確對比。
3. Phase 1-6全系列波次至此全部完成，是本次「CASHFLOW → SITELIST → ACCOUNT → TXLOG/BONUSCCY-001 → CASHOUT/BONUSCCY-002/BONUSCCY-003 → DAILYREPORT → UPDATEPACK → PLATFORMRULE → ARCADE」Phase 3影子測試系列的最後一個spec。
