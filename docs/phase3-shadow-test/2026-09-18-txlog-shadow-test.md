# Phase 3 影子測試紀錄：qaos-test-designer × SPEC-TXLOG-001

- **日期**：2026-09-18
- **Run**：RUN-20260918-001（spec-to-testcase，spec_id=SPEC-TXLOG-001, spec_version=0.1）—— COMPLETED
- **目的**：波次1（TXLOG＋BONUSCCY-001同步派工）之一。TXLOG是開發包④（機台交易紀錄），相依開發包③（CASHFLOW，已完成）的交易資料模型。Phase 2 已有 41 條 ACTIVE TestCase，Test Designer 獨立設計出 45 條 TestCaseDraft。
- **結果**：G-DESIGN 首輪即 PASS，G-TVAL 兩輪後 PASS。

---

## 設計與驗證階段

45 條 TC，覆蓋 29/30 requirement、49/51 AC。唯一未覆蓋的 REQ-TXLOG-029（AC-0291/0292）由 CLR-TXLOG-001 確認為 moot（手動取消操作本身不存在於本頁），risk=medium 非high，依結構化規則不強制要求 NO_REJECTION_CONTRACT: 前綴，用自由文字記載理由合規。

**第一輪 Validator FAIL**：1個major——TC-DRAFT-...ZMM6（REQ-TXLOG-017）的quote拿掉了同批其他TC已有的「原文已確認為錯誤敘述」揭露註記，比照REQ-TXLOG-017自己requirements.yaml的spec_reference.quote直接修正（精確小修正，未重新派工Test Designer，我直接編輯後驗證）。

**第二輪 PASS**，僅3個minor advisory（邊界值inclusive/exclusive未結構化揭露、門檻恰等於請求金額的方向性推論、Operator Reset造成永久卡單且無手動取消可用的RequirementModel覆蓋缺口，建議另開Clarification）。

## Phase 2 × Phase 3 交叉比對

51 條 AC 中：
- **49 條**：兩邊都覆蓋，其中 46 條 1:1 對應
- **只有 Phase2 / Phase3 覆蓋**：0（無單邊缺口）
- **兩邊都沒覆蓋**：2（AC-0291/0292，moot）
- **3 組 Phase3 比 Phase2 多 TC**，逐條讀完斷言後：
  - AC-TXLOG-0201（洗分門檻邊界）：1條是真正的邊界值新測項（門檻恰等於請求金額時不調小），另1條是Phase2既有案例的換句話說——只採用前者
  - AC-TXLOG-0071（訂單編號篩選）：Phase3拆分後的負向案例測了開分/洗分/入金三種非出金類型都顯示橫線，比Phase2單一例子更完整——採用
  - AC-TXLOG-0011（查詢範圍擴充）：Phase3第二條只是把第一條已涵蓋的「待確認」情況換個角度重講，無新斷言——判定純重複，不採用

**最終處置**：依ADR-007走輕量方式（無規則爭議、已在PASS輪次驗證過），用`bin/qaos approve APR-0114 --decision reject --per-item TC-TXLOG-176:approve --per-item TC-TXLOG-199:approve`核准這2條新增TC加入Registry，其餘43條Phase3草稿不採用。核准後獨立查驗Registry狀態（確認恰好2條變ACTIVE、43條維持非ACTIVE）。

**結果**：Phase2既有41條ACTIVE TC + 新增2條（TC-TXLOG-176、TC-TXLOG-199）= 43條ACTIVE。
