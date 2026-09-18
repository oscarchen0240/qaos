# Phase 3 影子測試紀錄：qaos-test-designer × SPEC-CASHOUT-001

- **日期**：2026-09-18
- **Run**：RUN-20260918-003（spec-to-testcase，spec_id=SPEC-CASHOUT-001, spec_version=1.0）—— COMPLETED
- **目的**：波次2（CASHOUT＋BONUSCCY-002＋BONUSCCY-003同步派工）之一。CASHOUT是「洗分出金核實」頁面的完整功能規格，Phase 2 已有 42 條 ACTIVE TestCase，Test Designer 獨立設計出 45 條 TestCaseDraft，31/31 requirement、44/44 AC 首輪即全覆蓋（本專案目前唯一一次第一輪就滿覆蓋的案例）。
- **結果**：G-DESIGN 首輪即 PASS，G-TVAL 首輪即 PASS（內部engine gate與獨立Validator雙重確認）。Phase2×3交叉比對後新增6條TC。

---

## 設計與驗證階段

45 條 TC，31/31 requirement、44/44 AC 全部覆蓋，第一輪即 PASS，無需任何修正輪次。

**內部engine T3 gate（G-TVAL）**：semantic PASS。
**獨立Validator審查**（額外派工，比照本專案「結構性技術主張需獨立查證」的鐵則，交叉核對 gates.py）：同樣 PASS，僅 2 個 minor issue（一條TC的expected_result有未明講的結構推斷、一條TC的boundary_value標籤與實際驗證性質稍有落差）+ 4 個 minor advisory（quote跨表格列拼接、跨頁執行依賴、邊界測資精度假設等），無 blocker/major。

3 條 exploratory TC（AC-CASHOUT-0251/0252/0291，操作員角色跨場館權限）的assumption原引用「定義於開發包⑥ PLATFORMRULE、尚未完成Phase 3」，經Oscar 2026-09-18於CLR-CASHOUT-001確認此為過去已規劃定案的既有權限設計（場館切換設定在後台管理員系統，僅站長/admin有此權限），已收斂assumption揭露範圍，只保留「測試環境是否已備妥符合限制的操作員帳號」這個單純環境事實（詳見CLR-CASHOUT-001）。

## Phase 2 × Phase 3 交叉比對

44 條 AC 全部兩邊都覆蓋，其中 39 條 1:1 對應。**5 組 Phase3 比 Phase2 多 TC**，逐條讀完斷言後：

- **AC-CASHOUT-0011**（洗分/出金完成後自動產生待核實紀錄）：Phase2 TC-041 只測了洗分情境；Phase3多測了「出金」這個不同交易類型（spec明確定義兩種交易皆適用）——採用；另一條「尚未完成（待確認）的交易不會建立核實紀錄」是負向邊界案例，驗證『已完成』狀態才是建立紀錄的前提，spec依據明確——採用
- **AC-CASHOUT-0051**（待核實洗分醒目色標提示）：Phase3多測了「核實後醒目提示消失、改一般樣式」這個相反方向的狀態轉換，驗證醒目提示是狀態限定而非永久——採用，但此斷言是從核實狀態表的表格結構推斷而非逐字條文，交叉比對階段已補上assumption揭露此推斷性質，避免被誤當成有明確條文依據的規則
- **AC-CASHOUT-0061**（核實當下累計提款次數/金額）：Phase3多測了「待核實與已作廢的紀錄不計入」，驗證只有『已核實』狀態才會被計入，spec原文明確支持此排除規則——採用
- **AC-CASHOUT-0111**（訂單編號篩選查得待核銷紀錄）：Phase3多測了「查無資料的負向案例」，驗證不會誤配到其他紀錄——採用
- **AC-CASHOUT-0181**（洗分門檻計算實際金額顯示）：Phase3多測了「實際金額趨近於0的邊界顯示穩健性」，屬於防禦性顯示測試而非spec定義的數值邊界，交叉比對階段已將design_techniques由boundary_value改標為error_guessing以更準確反映驗證性質——採用

**最終處置**：依ADR-007走輕量方式，用`bin/qaos approve APR-0118 --decision reject --per-item TC-CASHOUT-084:approve --per-item TC-CASHOUT-085:approve --per-item TC-CASHOUT-091:approve --per-item TC-CASHOUT-093:approve --per-item TC-CASHOUT-100:approve --per-item TC-CASHOUT-110:approve`核准這6條新增TC，其餘39條Phase3草稿（多為與Phase2重疊的重複案例）不採用。核准後獨立查驗Registry狀態，確認恰好6條變ACTIVE。

**結果**：Phase2既有42條ACTIVE TC + 新增6條（TC-CASHOUT-084、085、091、093、100、110）= 48條ACTIVE。

## 關鍵教訓

CASHOUT是本專案目前規模最大（45條）且唯一第一輪設計即全覆蓋、零修正輪次通過的案例，顯示當RequirementModel品質夠高、spec本身結構清楚時，Phase 3 agent可以一次到位。交叉比對階段仍抓到2條需要收斂assumption/技巧標籤才能採用的TC（AC-0051的醒目提示消失推斷、AC-0181的邊界值標籤），驗證了「即使Validator已判PASS，正式納入Registry前仍需針對minor issue逐條收斂」這個標準流程的必要性，不因為輪次順利就跳過這道把關。另外，CLR-CASHOUT-001確認的操作員權限規則，也提醒了「Test Designer對『規則定義於尚未完成的其他開發包』這類assumption要謹慎，若RequirementModel本身已有明確且經確認的規則文字，不應該讓assumption的措辭反而製造出規則本身不確定的錯誤印象」。
