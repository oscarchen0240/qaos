# ADR-008 · Clarification 落地前必須掃描同 area 全部 ACTIVE TC 的連帶影響

- **Status**: Accepted — 2026-09-22，Oscar 於 CLR-DAILYREPORT-012 落地後提出。**部分被 [ADR-010](ADR-010-clarification-lifecycle-manual-confirmation.md) 取代**：Decision 1、2 修改，Decision 3（核准即 apply）取消，Decision 4 放寬；現行契約以 ADR-010 為準，本文保留為歷史
- **Context**:
  `CLR-DAILYREPORT-012`（PM 定案 B：場館日結報表「依場次明細」不列進行中場次）落地時，只處理了直接掛 `AC-DAILYREPORT-0083` 的 `TC-DAILYREPORT-027`（retire）與 RM 回寫。事後掃描才發現另有三條 ACTIVE TC 的驗證步驟依賴同一個被推翻的假設：

  | TC | 依賴點 |
  |---|---|
  | TC-DAILYREPORT-051 | expected「依場次明細查詢當日有新場次期初餘額 80」——承接的新場次是進行中，B 之後明細看不到 |
  | TC-DAILYREPORT-053 | expected「新交易屬於一個新場次編號」——新場次是進行中 |
  | TC-DAILYREPORT-054 | 步驟 5「依場次明細可見新的場次編號」 |
  | TC-DAILYREPORT-052 | expected「當日無新場次」——B 之下變成空驗證，無鑑別力 |

  這四條都不掛 AC-0083，靠「掛哪個 AC」找不到；它們是靠步驟／expected 的**文字**依賴同一件事。`clarification apply` 過去只翻狀態，不看 TC，所以這種連帶影響完全靠人記得去掃——而這次沒記得。

  同類先例：`CLR-DAILYREPORT-009`（未兌現受結算日期限制）落地時修了 TC-046，但沒有紀錄是否掃過其他提到「未兌現」的 TC。

- **Decision**:
  1. **`bin/qaos clarification impact <CLR> [--keyword ...]`**：列出同 product/area 的 ACTIVE TC 中 (a) `requirement_ids` 含該 CLR 的 requirement、或 (b) title／preconditions／steps／expected_result 文字命中任一關鍵詞的候選。關鍵詞由落地者依 PM 回覆內容給（例如「進行中」「新場次」），是語意判斷的輸入，不是程式猜的。
  2. **`clarification apply` 沒有 `--impact-reviewed` 就拒絕**（`ValueError`）。`--impact-reviewed` 是落地者對每一條候選的結論：不受影響／需修訂（走 `testcase-revision`）／需 retire。掃描候選清單與結論一併寫入 CLR 的 `history[-1].note`（`impact-scan[N]: …；reviewed: …`），供日後追溯「當時掃到什麼、怎麼判的」。
  3. **Run 內自動落地路徑**（`engine._after_ambiguity`：RESOLVE_AMBIGUITY 核准即 apply）不擋，但同樣寫入掃描清單，並在 note 註明「run 外 TC 若受影響需另行修訂」——因為核准者在 run 內判定的是該 run 的 draft，run 外的 ACTIVE TC 仍要有人看。
  4. 判定為「需修訂／需 retire」的 TC，落地者必須在同一次工作中處理完（起 `testcase-revision` run 或 `tc retire`），不得只寫在 note 裡。這是 [[feedback_tc_integration_docs]] DoD 的延伸：CLR 落地 = 狀態翻轉 + RM 回寫 + 受影響 TC 處理 + final 重匯，四項缺一不可。

- **Consequences**:
  - `tools/qaos/clarification.py` 新增 `impact()`，`apply_()` 加 `impact_reviewed`／`keywords` 參數；`cli.py` 新增 `impact` 子指令與 `apply --impact-reviewed/--keyword`；`engine.py` 自動路徑帶入 reviewed 說明。測試 `tests/test_wf_z_clarification_and_bug_index.py::test_20`（拒絕分支）、`test_20b`（掃描規則：同 area／ACTIVE／requirement 或 keyword 命中；他 area、RETIRED、無命中不列）。
  - `CLR-DAILYREPORT-012` 補掃結果：10 條候選，020／025／026／030／031／077 不受影響；051／053／054 需修訂（新場次改到會員詳細頁「機台資訊」區塊驗）；052 需修訂（改到機台資訊區塊驗「無進行中場次」）。
  - 關鍵詞掃描是文字比對，會漏掉換了說法的依賴（「維持原值」vs「不變動」）。這是已知限制；`impact` 的定位是「至少不會漏掉字面命中的」，語意層仍靠落地者讀 PM 回覆後自己選詞。
  - 與 ADR-006 對稱：ADR-006 管「開 CLR 前要讀完整 spec」，本 ADR 管「CLR 落地後要掃完整 TC 集」。
