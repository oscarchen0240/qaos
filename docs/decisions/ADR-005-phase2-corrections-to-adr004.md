# ADR-005 · Phase 2 實測後修正 ADR-004 第 9、13 項

- **Status**: Accepted（2026-09-15，Oscar 口頭核准：「Yes，先開 ADR-005 補第9條，第13條照實際模式定調」）
- **Context**: ADR-004（2026-09-13）一次性核准 `NEEDS_DECISION.md` 全部 13 條 Recommended Option，屬於「AI 提出建議、Human 整批核准」，未逐項深入討論。Phase 2 實際跑完 10 份 spec、上百次 gate 迭代後，第 9、13 項的紙上決定被實測結果推翻或修正，依 ADR-004 Consequences「Phase 2 起若要推翻任一項，需新開 ADR」的規定，本檔記錄修正。

---

## 修正 1（原 ADR-004 #9）：`test-case-designer` 不 Fork + Adapt，改為方法論參考

- **原決定**：`ll0v0ll/test-case-designer` = Fork + Adapt。
- **實測發現（2026-09-15）**：重新評估該 repo 後發現：(1) 完全沒有 LICENSE 檔案，法律風險未解除；(2) 規模極小（1 star、2 commits、無實際使用驗證紀錄）；(3) 它強調的「7 層測試設計技巧」（場景/等價分割+邊界值/決策表/pairwise/狀態轉移/錯誤猜測）已全數對應到 QAOS 自己的 `schemas/common/defs.schema.json` 的 `DesignTechnique` enum（含 `pairwise`）；(4) 它的「分析文件先審後生成」門檻，實務上比不過 QAOS 已經在跑的 G-SPEC→人審→G-DESIGN→獨立 Validator（G-TVAL）四層流程。
- **新決定**：**不 clone、不 fork**。`spec-analysis`、`test-validation` 維持自寫（與 ADR-004 #9 後半段一致，不變）。該 repo 僅作方法論比對用途，不作為程式碼依賴。若未來真的需要 pairwise 組合演算法（例如某個需求的維度爆炸到手動枚舉不可行），應自行重寫等價的小腳本——pairwise/正交陣列演算法是公開的電腦科學技巧，非其專利，不涉及授權問題。
- **生效位置**：無程式碼變更（Phase 2 從未實際 clone 過該 repo，`docs/architecture/07-skill-evaluation.md` 若有引用 ADR-004 #9 的舊結論，Phase 3 啟動時一併更新）。

---

## 修正 2（原 ADR-004 #13）：Human Review Gate 改為「Requirement 層級」，取代原「TestDesignReport.analysis 層級」設計

- **原決定**：`test-case-designer` 的「分析文件先審後生成」精神，映射成 workflow input `analysis_review: required|skip`（預設 skip），開啟時在 **T2 之後**插入 `REVIEW_TEST_ANALYSIS` approval（審核 TestDesignReport 裡的分析內容，審完才正式生成/採用 TestCaseDraft）。
- **實測發現**：Phase 2 這 10 份 spec，**每一次**都不是照這個機制走，而是自然演化出另一種模式：**T1（Spec Analyst）完成、G-SPEC structural PASS 之後**，立刻用 `bin/qaos req-export` 把 RequirementModel 匯出成 `requirements/<spec_id>-v<version>.md`，交給 Human 審閱「需求切法是否合理」（尤其是範圍縮減/排除既有已測內容的判斷），**確認合理才進 T2 Test Design**。這個 checkpoint 卡在**「需求怎麼拆」這個更上游的節點**，而不是「測試案例的分析文件寫得好不好」這個下游節點——原因是：需求拆得不合理（範圍抓錯、漏掉排除既有覆蓋、AC 切太細或太粗）是更早、更根本、修正成本更低的錯誤，等到 TestDesignReport 階段才發現，回頭要改的東西更多。這個模式 100% 被使用（10 份 spec 沒有一次跳過），且確實攔下過需要調整的情況（例如 PLATFORMRULE 的範圍切法討論）。而原本設計的 `REVIEW_TEST_ANALYSIS`（T2 之後的分析審核）在 Phase 2 從未被觸發過一次——`analysis_review` 這個 input 從頭到尾都是預設值 `skip`，沒人手動開啟過。
- **新決定**：Phase 3 的 `workflows/spec-to-testcase.yaml` 應：
  1. 移除 `analysis_review: required|skip` 這個 input 與 `REVIEW_TEST_ANALYSIS` approval type 的原始設計（未被驗證有價值）。
  2. 在 **T1 的 `post_pass`**（G-SPEC PASS 之後、T2 開始之前）新增一個**必經**（非可開關）的 Human checkpoint，新的 approval type 暫名 `REVIEW_REQUIREMENTS`：Runtime 自動執行 `req-export` 產出 `requirements/<spec_id>-v<version>.md`，暫停於 `WAITING_HUMAN`，待 Human 核准（或要求 Spec Analyst 修訂範圍/切法）後才進入 T2。
  3. 因為 T1 本身已有 `skip_if: "RequirementModel exists AND status=ACTIVE"`，這個新 checkpoint 只會在**全新** spec/version 首次通過 G-SPEC 時觸發一次，重跑既有已核准 spec 不會重複卡關，不需要額外的開關來避免擾民。
- **生效位置**：`workflows/spec-to-testcase.yaml`（新增 T1 `post_pass` 的 approval 節點）、`schemas/common/defs.schema.json` 的 `ApprovalType` enum（新增 `REVIEW_REQUIREMENTS`，移除或保留 `REVIEW_TEST_ANALYSIS` 供未來備用）——**Phase 3 啟動時落地，Phase 2 不需要現在就改**，因為 Phase 2 是我人工在跑，這個 checkpoint 本來就是用對話形式自然發生。

---

- **Consequences**：ADR-004 表格第 9、13 列視為已被本檔取代；`NEEDS_DECISION.md` 對應兩條會加註指向本檔。之後若又有其他 Phase 1 決定被 Phase 2/3 實測推翻，比照本檔模式另開新 ADR，不直接改 ADR-004 原文（保留歷史決策的可追溯性）。
