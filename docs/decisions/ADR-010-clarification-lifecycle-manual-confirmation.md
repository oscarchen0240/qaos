# ADR-010 · CLR 生命週期改為人工確認結案（取代 ADR-008 的部分契約）

- **Status**: Proposed——依需求 A 最終規格第 6 章（FIX-10）實作。Oscar 於 2026-10-06 授權依需求 A 實作（`review-handoff/clr-spec-investigation/requirement-a-decisions.md`）；本 ADR 隨需求 A 的 MR 合併後生效，Accepted 日期由 Oscar 於合併時確認。
- **取代範圍**：ADR-008 的 Decision 1～4 與 Consequences 依下表逐項保留、修改、取消或放寬；ADR-008 原文保留為歷史。
- **取捨**：CLR 結案先維持**人工確認**（需求 B 的機械追蹤延後）。這**不等於**原本的 DoD 完全維持：APPLIED 只代表人工結論已落地，不保證所有受影響 TC 都已完成處理。

## Context

ADR-008 讓 `clarification apply` 必須附 `--impact-reviewed`，並讓 RESOLVE_AMBIGUITY 核准時自動 apply。實務上：

- 一段 `--impact-reviewed` 文字無法表示「每張候選都已逐張判定」，也無法重現當時掃到哪些 TC、哪個版本。
- 核准即 apply 會讓 CLR 在答案還沒被任何分析採用前就結案。
- 「四項缺一不可、同一次工作處理完」在跨 area、跨 product、要分批修訂時無法硬性保證。

需求 A 把「核准」「答案被分析納入（INCORPORATED）」「人工確認結案（APPLIED）」分成三個事件。

## Decision

### 與 ADR-008 的逐點對照

| ADR-008 | 處理 | 現行契約（以本 ADR 為準） |
|---|---|---|
| Decision 1（`impact` 掃描範圍與關鍵字） | **修改** | `clarification impact` 保存掃描紀錄（`clarifications/<product>/<area>/scans/<CLR>-<scan_id>.yaml`），是寫入指令。掃描以 `(product, area)` 為單位分開：CLR 自身的單位，加上採用目標（確認與延後的）所在的單位；不同 product、相同 area 名稱不合併。候選規則：(a) 目標需求、(b) 依賴舊答案的 `decision_refs`、(c) CLR 原題需求（只在 CLR 自身單位）、(d) 關鍵字（所有單位）。關鍵字＝`--keyword` ∪ scan 的關鍵字；空集合時必須提供 `--no-keyword-reason`。目標解析與 apply 的重新掃描都在全域操作鎖內進行，舊 scan 不能取代當前狀態（scan 屬於舊答案修訂或規則版本不同時只沿用關鍵字）。 |
| Decision 2（`apply` 沒有 `--impact-reviewed` 就拒絕；候選與結論寫入 history note） | **修改** | `--impact-reviewed` 仍必填，但只是整體說明。`apply --path a6\|a6b\|a7` 要求：每張重新掃描的候選都有 `--tc-conclusion`（updated／not_affected／retire_planned／deferred:理由）；最新答案綁定；a6 的每個採用目標都被 `--target` 確認或 `--defer-target` 延後；`--landed-in` run 已 COMPLETED 且含已確認的目標。landing 保存候選（ID、版本、sha256）、結論、關鍵字、掃描單位與規則版本；history 只是摘要，不是唯一證據。 |
| Decision 3（RESOLVE_AMBIGUITY 核准即 apply） | **取消** | approve 和 override 都不再 apply 任何 CLR（新舊資料皆同）。答案被 revision 或 BugDraft 以明確 SourceRef 採用（最新 answer_rev、通過 X16）時，CLR 轉 INCORPORATED（A4）。結案路徑：A6（`--path a6`，INCORPORATED）；A6b（`--path a6b`，bug reject 路徑：reject 決議條目的**內部** clarification source 是落地證據，reject 核准單本身不是有效的裁決包裝）；A7（`--path a7`，答案 no_change／out_of_scope 而且全部歷史都沒有引用）。文件索取單依逐項 fulfill／waive-item（或核准的 waive_missing）結案（A8），核准的 waive_missing 涵蓋全部項目而且沒有有效 fulfillment 時撤回（A9）。 |
| Decision 4（需修訂／retire 的 TC 必須在同一次工作中處理完；「四項缺一不可」） | **放寬** | 不再作為 APPLIED 的硬保證。允許 `retire_planned`、`deferred:<理由>`，但必須逐張記錄在 landing，可用 `clarification show` 查詢。三件事分開：CLR 人工結案（APPLIED）、TC 尚待處理（結論與延後清單）、final 輸出更新（另依 DoD 執行）。 |
| Consequences | **修改** | CLI：`clarification impact [--keyword] [--target]`、`apply --path … --landed-in --target --defer-target --keyword --scan --no-keyword-reason --tc-conclusion --impact-reviewed --by`、`fulfill`、`waive-item`、`withdraw --reason`、`show`、`stale-tcs`。狀態機：A1～A10（`workflows/state-machines.yaml`）。證據位置：CLR 的 `landings[]`、`document_items[].fulfillments[]`、掃描紀錄。ADR-008 原有的 `test_20`／`test_20b` 已改寫為本 ADR 的契約；原測試只作為歷史驗證。保留限制：關鍵字掃描是文字比對，會漏掉換了說法的依賴。 |

## 已知限制與風險（需求 A 第 6 章 §13）

1. 系統**不驗證** `--tc-conclusion` 是否屬實（例如標 updated 的 TC 是否真的已更新並核准），由人負責。
2. `deferred`、`retire_planned` 的 TC 和 `--defer-target` 的目標**不會被自動追蹤**；只記錄在 landing，可用 `clarification show` 查詢。`retire_planned` 不代表已退休。
3. 關鍵字由人選擇；換了說法、同義改寫、沒有追溯欄位的間接依賴，可能被漏掃。
4. 一次 apply 確認的 landed-in run，不證明所有 spec 版本、所有 area 的相關 TC 都已完成（a6 的所有採用目標都必須被明示確認或延後）。APPLIED 不代表全部 TC、版本、area 都已完成。
5. 每個 landed-in run 至少含一個已確認的目標，但**不保證每個已確認的目標都各有自己的已完成 run**；人可以確認一個沒有對應 run 的目標，這是人工確認的一部分。
6. APPLIED 之後，新出現的依賴 TC 或新的採用**不會**自動重新開單或提醒；`stale-tcs` 只是唯讀查詢（依 `decision_refs`、`requirement_ids` 與最近一次的關鍵字），不保證完整。
7. 文件的人工對應（`human_mapping`）正確性由人負責；系統不理解文件內容。
8. 第一批中，沒有提供 SourceRef 的 BugDraft 不會觸發 A4。
9. fork 的鎖隔離只涵蓋經由 Python 的 fork；C 擴充模組直接 fork 不在保證範圍內。
10. 以上限制屬於需求 B（如果重啟）的範圍；在需求 B 完成之前，CLR 結案由人逐張確認，這是 Oscar 決定的取捨。

## 範圍外

- Oscar 本機 DoD memory 的修改另依 Oscar 授權；本 ADR 不代為修改，也不構成修改授權。
