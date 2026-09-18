# Phase 3 影子測試紀錄：qaos-test-designer × SPEC-BONUSCCY-003

- **日期**：2026-09-18
- **Run**：RUN-20260918-005（spec-to-testcase，spec_id=SPEC-BONUSCCY-003, spec_version=1.0）—— CANCELLED（交叉比對後決定不採用任何Phase3草稿，正式關閉run）
- **目的**：波次2（CASHOUT＋BONUSCCY-002＋BONUSCCY-003同步派工）之一。BONUSCCY-003是簽到活動「有效會員」判定改讀正確資料表（deposit_log_v2）的小型修正包。Phase 2 已有 6 條 ACTIVE TestCase，Test Designer 獨立設計出 6 條 TestCaseDraft。
- **結果**：G-DESIGN 首輪即 PASS，G-TVAL 第一輪即 PASS（僅上游RequirementModel繼承的quote格式minor問題）。Phase2×3交叉比對後：6組TC逐條對應，內容深度與斷言重疊度高，Phase3未提供任何淨新增覆蓋，全數不採用。

---

## 設計與驗證階段

6 條 TC，4/4 requirement、5/5 AC 全部覆蓋。

**第一輪 PASS**：僅少量minor advisory（quote格式繼承自RequirementModel源頭的既有慣例），無blocker/major，未觸發任何修正輪次。

## Phase 2 × Phase 3 交叉比對

5 條 AC 全部兩邊都覆蓋，且全部 1:1 對應（AC-BONUSCCY-017 兩邊各 2 條，其餘四條 AC 各 1 條）。逐條讀完斷言後：

- **AC-BONUSCCY-017**（存款金額精確入帳）：Phase2 TC-023/024（基本金額、小數精度）與 Phase3 兩條斷言幾乎完全相同，同一驗證深度——不採用
- **AC-BONUSCCY-018**（流水門檻/手續費以原始金額為基數）：Phase2 TC-025 與 Phase3 斷言相同；Phase3多揭露了「目前存款幣別必然等於記帳幣別，本測試無法真正區辨兩種基數差異，僅為回歸驗證」這個誠實的測試侷限說明，屬於文件說明品質的差異，不構成新增的驗證廣度或深度——不採用（Phase2既有TC已足夠）
- **AC-BONUSCCY-019**（前台進度條與後台判定一致）：Phase2 TC-026 與 Phase3 斷言相同，Phase3多寫了資料來源細節（deposit_log_v2），不構成新斷言——不採用
- **AC-BONUSCCY-020**（開一次前台頁即直接寫入有效會員）：Phase2 TC-027 的 design_rationale 已明確點名「精確驗證spec的『前台每次開頁重算並直接寫入、後台被動同步』這個不對稱機制，不是只驗兩邊最終一致的較弱陳述」，驗證深度不輸甚至優於 Phase3 對應TC——不採用
- **AC-BONUSCCY-021**（跨月歸零重算）：Phase2 TC-028 與 Phase3 斷言相同——不採用

**最終處置**：6 條 Phase3 草稿逐條核對後，全數與 Phase2 既有 TC 重疊、無淨新增覆蓋，依ADR-007走輕量方式，用`bin/qaos approve APR-0117 --decision reject`（不含任何--per-item approve）全數退回，確認 TC-BONUSCCY-046~051 皆為 NO_ACTIVE_VERSION。run 以`bin/qaos run cancel`正式關閉。

**結果**：Phase2既有6條ACTIVE TC維持不變，無新增TC。

## 關鍵教訓

這是本專案目前為止唯一一次交叉比對後「全數不採用」的案例——與其他spec（多半有1~4條淨新增）不同，BONUSCCY-003本身是規模小、規則單純的修正包（4 requirement、5 AC），Phase2既有測試設計已經精準覆蓋每一顆AC的核心斷言，Phase3獨立設計雖然合格（G-DESIGN/G-TVAL皆一輪即過），但未能提供額外的驗證角度。這驗證了「深度底線＞廣度覆蓋＞深度精進」原則中最後一項的實務意義：當Phase2已經做到位時，堆疊風格相近的Phase3案例不會增加真正的測試廣度，誠實判定不採用比為了「用到Phase3產出」而勉強塞入重複案例更符合TC準則。
