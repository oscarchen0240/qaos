# Phase 3 影子測試紀錄：SPEC-REDPACKET-001 重跑（驗證 MR !15 agent 指示與契約）

- **日期**：2026-10-09
- **目的**：驗證 MR !15（`a22f837`）修正的 agent 指示與契約在實際流程中是否生效：
  - agent 不自行 submit／gate，寫入由主 session 經 `bin/qaos` 執行（待辦 #2、#6）。
  - Validator 的 assumption 規則對齊需求 A 第 1 章 §3.6（#4）。
  - REDPACKET 納入 TC Risk Reviewer（#10）。
- **執行位置**：隔離副本（main `a22f837` 以 `git archive` 匯出到暫存目錄），主資料夾不留資料。
  - 副本中移除 REDPACKET 既有的 93 條 TC（registry、versions、`testcases/REDPACKET.md`），讓 Designer 從 R002 全新設計，以便和真實結果比對。
  - 其餘資料（R002、CLR、宣告、閉包 spec）與 main 相同。
  - 副本內的 TC 編號（TC-REDPACKET-094～180）、APR-0196、RUN-20261009-001 都只存在於副本，**不是正式資料**。
- **範圍**：T1（Spec Analyst）依 skip_if 跳過（R002 全部 ACTIVE、宣告未變），從 T2 開始。Spec Analyst 的新指示（REQ 由主 session 配發、AC 照推導）未在本次驗證。
- **結果**：RUN-20261009-001 COMPLETED。
  - G-DESIGN 兩輪皆 PASS。
  - G-TVAL 第 1 輪 FAIL（9 major），第 2 輪 PASS（0 major）。
  - T3RR（G-RISK）PASS。
  - APR-0196 核准 81 條，逐項退回 6 條含未確認 assumption 的 TC。

---

## 流程

| 步驟 | 結果 | 說明 |
|---|---|---|
| T2 iter0 | G-DESIGN PASS | 86 條 TC，需求 33/33，AC 122/123（缺 AC-0286），exploratory 3 條 |
| T3 iter0 | G-TVAL FAIL | 0 blocker、9 major、4 minor、14 advisory |
| T2 iter1 | G-DESIGN PASS | 87 條（新增 1 條 exploratory），exploratory 6 條，AC-0286 登記於 uncovered_with_reason |
| T3 iter1 | G-TVAL **PASS** | 0 major、5 minor、2 advisory；13 個 iter0 問題全部解決，未衍生新 major |
| T3RR | G-RISK PASS | 五個面向皆 gaps_found，27 項（high 10），13 項需澄清 |
| T4 | APR-0196 | 核准 81 條；退回 TC-108、109、120、123、148、160 |

## !15 驗證結果

1. **寫入分工（#2、#6）：生效。**
   - Designer、Validator、Risk Reviewer 三個 agent 都只把 artifact 寫進 `write_paths`、回報路徑。
   - submit、gate、dispatch 全部由主 session 執行，沒有 agent 呼叫 `store.save` 或丟 `NoExecutorContext`。
   - 兩個 agent 曾用唯讀方式在記憶體中呼叫 `gates.g_design`／`gates.g_risk` 自查，沒有寫入，不違規。
2. **Validator assumption 規則（#4）：生效。**
   - 依賴 E4 決策點、標 `needs_human_confirmation: true` 的 exploratory 被判合法，沒有再因「未被 RESOLVE_AMBIGUITY 覆蓋」判 blocker。
   - 隱含依賴 E3／E4 卻寫成確定斷言的 8 處，被判 major。
3. **REDPACKET 風險抽查（#10）：生效。** `run new` 即插入 T3RR，實際執行並通過 G-RISK。

## 和上一次影子測試（RUN-20261008-001）比較

| | 2026-10-08（舊指示） | 本次（!15 後） |
|---|---|---|
| G-TVAL 輪數 | 3 輪才 PASS | **2 輪** PASS |
| 修正衍生新 major | 有（iter1 為修 minor 加確定斷言，製造新 major） | **無**（Validator 逐行比對確認沒有新增確定斷言） |
| 第一輪 major 性質 | 隱含依賴未定事項寫成確定斷言 | 同一類（8/9） |

- 第一輪的主要問題仍是「斷言隱含依賴未定事項、未宣告 decision_refs」（待辦 #3）。G-DESIGN 機械檢查依然抓不到，靠 Validator 語意審查。
- Designer 在修正輪一次套用「依賴未定事項就 exploratory、刪除或改條件式，不新增確定斷言」，因此一輪收斂。

## 和真實 Registry（main，89 條 ACTIVE）比對

| | 真實 | 影子 |
|---|---|---|
| ACTIVE TC | 89 | 81 |
| AC 覆蓋 | 123/123 | 120/123 |
| non-happy TC（含 negative 或 boundary） | 56 | 56 |
| 多需求 TC | 17 | 15 |
| technique 前三 | requirement_based 39、boundary_value 16、negative 12 | requirement_based 31、boundary_value 20、state_transition 10 |

- **影子缺的 3 個 AC**：
  - AC-0081、AC-0091：唯一覆蓋它們的 TC-120、123 為混合型。主體是確定斷言，精確換算部分依賴 008Q02（E4）而帶 assumption。核准會讓 Runtime 把 assumption 標成已核准確認，因此比照 APR-0194 退回。
  - AC-0286：依賴 028Q04（E2）與 028Q02（E4），Designer 刻意不寫並登記理由。
- **每條需求 TC 數差距 ≥ 2**：
  - REQ-003：真實 8／影子 11。
  - REQ-013：真實 2／影子 4。
  - REQ-016：真實 9／影子 4。
  - REQ-027：真實 6／影子 4。
  - REQ-028：真實 7／影子 5。
- 影子只覆蓋到真實 Registry 已覆蓋的 AC，沒有多出真實沒有的 AC。

## 本次觀察到的問題

1. **混合型 exploratory 讓 AC 失去覆蓋**：一條 TC 同時有確定斷言和依賴未定事項的斷言時，核准者只能整條退回或整條確認。建議 Designer 把依賴未定事項的部分拆成獨立的 exploratory TC，讓確定部分可以單獨核准。本次是 TC-120、123。
2. **待辦 #5 的手動處理**：本次基準 `a22f837` 尚未含 #5 的修正，給 Validator 的 Draft 由主 session 手動剝除 `design_rationale`（另附 coverage matrix 摘錄）。#5 已在 `qaos/gate-integrity`（main `61cf145`）以 `review_drafts` 修正，下次 run 會由派發包提供。
3. **Risk Reviewer 偏離指示兩處**：
   - 必讀閉包 spec 只完整讀了目標 spec 與 SPEC-CASHFLOW-001，其餘以關鍵字搜尋讀相關段落。
   - 產生報告的腳本寫在 ROOT 之外的暫存目錄。
   - 不影響結果正確性，但「`required: true` 必讀」沒有機械檢查。
4. **Validator iter1 留下 5 個 minor**：CSV 案例依賴紅包編號欄（輕度依賴 022Q03）、取價失敗與多幣種案例的判定方法、共用前置條件的清空範圍、日結切分前提無從確認。不擋流程。真實資料若要沿用影子的寫法，需一併處理。

## 風險抽查（T3RR）重點

REDPACKET 首次風險抽查。真實 Registry 的 89 條 TC 未經抽查，以下缺口多數同樣適用於真實資料。

- **併發**：所有案例都是循序操作。最高風險為多帳號同時搶最後一份預算（可能超發）、同帳號多筆注單同時結算。
- **重複提交**：同一紅包重複開啟（連點、多分頁、重放請求）。
- **異常流程**：
  - 平台已扣分但機台顯示失敗。
  - 第一階段 15 秒逾時讓紅包持續鎖定。
  - 開啟紅包中途失敗時，錢包、交易紀錄、稽核明細與紅包狀態是否全有或全無。
- **權限**：改紅包編號開啟他人紅包；以網址、API、CSV 越權存取。
- **需澄清 13 項**：RF-03、05、07、12、13、17、19、20、22、23、24、25、26。其中 RF-25～27 與 CLR-REDPACKET-039、040、042 部分重疊。

## 建議後續

1. 對真實 Registry 的 REDPACKET 89 條 TC 補做一次 T3RR 風險抽查，或以本次 27 項 finding 為底，開 CLR 或補案例。
2. Designer 指示補一條：依賴未定事項的部分拆成獨立 exploratory TC，不與確定斷言混在同一條（觀察 1）。
3. Spec Analyst 的新指示（REQ 配發、AC 推導）待 B+ 完成後，以一次實際會跑 T1 的 run 驗證。
