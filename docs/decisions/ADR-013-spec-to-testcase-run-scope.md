# ADR-013 · spec-to-testcase 的 run scope 可機器解析，G-DESIGN 依 scope 判定覆蓋範圍

- **Status**: Proposed——merge 後生效，Accepted 日期由 Oscar 於合併時確認。
- **範圍**：`workflows/spec-to-testcase.yaml` 的 `input.scope`；程式：`tools/qaos/run_scope.py`（解析）、`engine.new_run`（語法檢查）、`dispatch.build`（派發包 `run_scope`）、`gates.g_design`（`design_scope`、`run_scope_issues`）；`schemas/workflow/dispatch-packet.schema.json` 新增選填欄位 `run_scope`。

## Context

`spec-to-testcase` 的 `input.scope` 定義為「functional area 或 requirement_ids 子集」，但只是自由文字，程式沒有讀。`gates.g_design()` 在 `mode=spec` 下一律把綁定 revision 的**全部**需求當成覆蓋範圍。

只補幾條需求的 run（T3RR 風險抽查補強、CLR 新增 AC 的補 TC）因此要把範圍外的需求全部列進 TestDesignReport 的 `uncovered_with_reason`；其中 high risk 的還得加 `NO_REJECTION_CONTRACT:` 前綴才不被擋——語意錯誤：不是缺拒絕契約，而是不在本 run 範圍。

實例（2026-10-13）：RUN-20261013-004（SPEC-DAILYREPORT-001 0.3，scope 10 條需求）的報告列了 19 條範圍外需求，其中 11 條掛 `NO_REJECTION_CONTRACT:`；RUN-20261013-001～003 相同。

## Decision

### 1. scope 的語法

`<REQ 清單>[（說明）]`：

- REQ 清單以 `,`／`，`／`、` 分隔；每一項是完整 ID（`REQ-<AREA>-<序號>`），或只寫序號（沿用前一個完整 ID 的 `REQ-<AREA>-` 前綴）。例：`REQ-DAILYREPORT-001,005,007` ＝ 001、005、007。
- 說明放在第一個 `（` 或 `(` 之後，不參與解析。
- 不以 `REQ-` 開頭的 scope（functional area 或其他自由文字）**不是需求範圍**：沿用原本的行為（全部需求）。
- 以 `REQ-`（不分大小寫）開頭卻不符語法 → `run new` 拒絕（例如 `REQ-X-001 補強` 要寫成 `REQ-X-001（補強）`）。

既有 run 的三種寫法都相容：`REQ-ARCADE-004`、`REQ-DAILYREPORT-008,REQ-DAILYREPORT-014（…）`、`REQ-DAILYREPORT-001,005,…（…）`。本變更之前建立、以 `REQ-` 開頭卻不合語法的 run（目前沒有）沿用原本的行為。

沒有另開結構化欄位：既有 run 已經以這個慣例填寫，CLI 也只有 `--input scope=…`；同一個資訊兩個欄位會分歧。

### 2. G-DESIGN（`mode=spec`，scope 是需求清單時）

| 項目 | 範圍 |
|---|---|
| 必須覆蓋或列 `uncovered_with_reason` | 只有 scope 內的需求 |
| 行為契約規則（high-risk 負向、rejection、邊界、狀態、exploratory 上限、整份沒有負向案例） | scope 內的需求，加上 TC 實際涉及的需求（`requirement_ids` 或 coverage_matrix 有 draft 的） |
| scope 外、沒有 TC 涉及的需求 | 不檢查；列在 `uncovered_with_reason` 也不檢查（相容舊報告） |
| 新增 FAIL | scope 列的需求不在綁定的 revision；某條 TC 的 `requirement_ids` 全部在 scope 外 |

scope 不是需求清單、或沒有 scope：行為不變（全部需求）。`mode=change`／`manual` 不受影響。

### 3. 派發包

Test Designer、Test Validator、TC Risk Reviewer 的派發包新增 `run_scope: {raw, requirement_ids}`（run 有 `scope` 才寫入；`requirement_ids: null` 代表不是需求清單）。Spec Analyst 仍分析整份 spec，不帶 scope。

run 已綁定 revision 時，scope 列的需求不在該 revision → `dispatch` 拒絕（打錯 ID 或 spec 不符，不讓 Designer 白做），須取消 run 以正確的 scope 重開。T1 尚未產生 revision 時不檢查；T1 之後的派發才檢查，G-DESIGN 另有同一條防線。

## Consequences

- 範圍外需求不再需要 `NO_REJECTION_CONTRACT:`；這個前綴回到原本的意義（spec 沒有定義拒絕契約）。
- Designer 若在 scope 外設計 TC（TC 只涉及 scope 外需求）會被 G-DESIGN 擋下；要擴大範圍須重開 run。
- 用真實資料比對：既有 spec-to-testcase run 的最後一份設計產出在新舊規則下 G-DESIGN 結果相同；RUN-20261013-002～004 的報告拿掉範圍外的 uncovered 條目後，新規則 PASS（舊規則各報 28～59 條「未被覆蓋」）。
- 測試：`tests/test_design_run_scope.py`。
