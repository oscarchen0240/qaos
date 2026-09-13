# SPEC-ADMQUERY-001 mcp-admin 查詢工具篩選規則 v1.0

> **⏸ HOLD（2026-09-13）：Human 指示 mcp-admin 這批暫不開單、不設計 TC、不匯入本 SPEC。保留供日後啟用。**
>
> 草稿狀態：由 Claude 依 `mcp-admin-query-tools-audit-2026-08-06.md` 與 8 份 bug report 反推的「隱含規格」。標 **[待確認]** 的條文是目前系統未定義的行為，需 Human 決定是否成為正式需求；確認後以 `bin/qaos spec import` 匯入。

## 1. 範圍
適用於 mcp-admin 所有 `*_query-*` 唯讀工具的 `query`、`sorter`、`pagination` 參數處理行為。不涵蓋寫入類工具。

## 2. 名詞
- **baseline**：不帶任何 `query` 條件時該工具回傳的 `pagination.total` 與列表。
- **已列出欄位**：工具 input schema 的 `query` 物件中正式宣告的屬性。
- **未列出欄位**：`query` 中出現、但 schema 未宣告的屬性。

## 3. 功能需求

### 3.1 已列出欄位的篩選必須生效
- **R1** 帶入任一已列出欄位的合法值後，回傳的 `pagination.total` 與列表必須只包含符合條件的記錄；若條件確實排除了部分記錄，結果不得等於 baseline 全量。
- **R2** 陣列型欄位（如 `userNo`、`transactionType`、`status`）：回傳每一筆記錄的該欄位值必須屬於帶入的陣列。
- **R3** 數值範圍欄位 `{min, max}`：回傳每一筆記錄的該欄位值必須落在 `[min, max]`（含端點）；`min == max` 時只回傳恰好等於該值的記錄。
- **R4** 日期範圍欄位：回傳每一筆記錄的時間必須落在 `[startDate, endDate]`（含端點），比較以 UTC、秒級精度；一個剛好框住單筆記錄時間戳的窄窗口必須命中該筆。
- **R5** 篩選欄位的語意必須與 schema description 一致（例如 `status` 的 `0:停用 1:啟用`）；不得出現「查啟用回 0 筆、查停用回啟用帳號」的反向結果。

### 3.2 未列出或不存在的欄位
- **R6 [待確認]** `query` 中出現未列出欄位時，工具必須回傳 400 並指出該欄位名稱；不得靜默忽略後回傳 baseline 全量。
- **R7** schema 中列出的每一個 `query` 欄位，都必須對應該工具回傳資料中實際存在、且可篩選的欄位；不得列出資料中不存在的欄位（例如 rebate-log 的 `transactionNo`）。

### 3.3 日期參數形狀
- **R8 [待確認]** 同一 API 家族內，日期範圍參數的形狀必須一致（巢狀 `{startDate, endDate}`）。若個別工具採扁平 `timeStart` / `timeEnd`，其 schema description 必須明示，且帶入巢狀形狀時應回 400 而非靜默忽略。

### 3.4 與後台 UI 的對應
- **R9** 後台 UI 畫面提供的每一個篩選功能（例如 Bet Record 的 Bet Status），對應的 MCP 查詢工具必須提供可實際生效的 `query` 欄位，且以真實資料欄位名（如 `betStatus`）帶入時不得回 400。

### 3.5 排序
- **R10** `sorter.order` 只接受 `asc` / `desc`；帶入其他值（如 `descend`）應回 400，不得靜默改為 `asc`。
