# ADR-013 · spec-to-testcase 的 run scope 可機器解析，G-DESIGN 依 scope 判定覆蓋範圍

- **Status**: Proposed——merge 後生效，Accepted 日期由 Oscar 於合併時確認。
- **範圍**：`workflows/spec-to-testcase.yaml` 的 `input.scope`；程式：`tools/qaos/run_scope.py`（解析）、`engine.new_run`（語法檢查；已綁定 revision 時核對需求）、`dispatch.build`（派發包 `run_scope`）、`gates.g_design`（`design_scope`、`run_scope_issues`）；`schemas/workflow/dispatch-packet.schema.json` 新增選填欄位 `run_scope`。

## Context

`spec-to-testcase` 的 `input.scope` 定義為「functional area 或 requirement_ids 子集」，但只是自由文字，程式沒有讀。`gates.g_design()` 在 `mode=spec` 下一律把綁定 revision 的**全部**需求當成覆蓋範圍。

只補幾條需求的 run（T3RR 風險抽查補強、CLR 新增 AC 的補 TC）因此要把範圍外的需求全部列進 TestDesignReport 的 `uncovered_with_reason`；其中 high risk 的還得加 `NO_REJECTION_CONTRACT:` 前綴才不被擋——語意錯誤：不是缺拒絕契約，而是不在本 run 範圍。

實例（2026-10-13）：RUN-20261013-004（SPEC-DAILYREPORT-001 0.3，scope 10 條需求）的報告列了 19 條範圍外需求，其中 11 條掛 `NO_REJECTION_CONTRACT:`；RUN-20261013-001～003 相同。

## Decision

### 1. scope 的語法

`<REQ 清單>[（說明）]`：

- REQ 清單以 `,`／`，`／`、` 分隔；每一項是完整 ID（`REQ-<AREA>-<序號>`，序號至少三位，與 RequirementId schema 一致），或只寫序號（至少三位，沿用前一個完整 ID 的 `REQ-<AREA>-` 前綴）。例：`REQ-DAILYREPORT-001,005,007` ＝ 001、005、007。
- 說明只能是結尾的一段括號：從第一個 `（`／`(` 開始，到 scope 最後一個字元才閉合（說明內可有成對括號），不參與解析。括號中途閉合又接著文字（例如 `REQ-X-001（補 AC）、REQ-X-002（補 AC）`）→ 不合語法；否則後面的需求會被靜默丟掉。
- 不以 `REQ-` 開頭的 scope（functional area 或其他自由文字）**不是需求範圍**：沿用原本的行為（全部需求）。
- 以 `REQ-`（不分大小寫）開頭卻不符語法 → `run new` 拒絕，錯誤訊息附正確寫法（例如 `REQ-X-001 補強` 要寫成 `REQ-X-001（補強）`；JSON 陣列 `--input 'scope=["REQ-X-001"]'` 也拒絕，改寫成逗號分隔）。

既有 run 的三種寫法都相容：`REQ-ARCADE-004`、`REQ-DAILYREPORT-008,REQ-DAILYREPORT-014（…）`、`REQ-DAILYREPORT-001,005,…（…）`。本變更之前建立、以 `REQ-` 開頭卻不合語法的 run（目前沒有）沿用原本的行為。

沒有另開結構化欄位：既有 run 已經以這個慣例填寫，CLI 也只有 `--input scope=…`；同一個資訊兩個欄位會分歧。

### 2. G-DESIGN（`mode=spec`，scope 是需求清單時）

| 項目 | 範圍 |
|---|---|
| 必須覆蓋或列 `uncovered_with_reason` | 只有 scope 內的需求 |
| 行為契約規則（high-risk 負向、rejection、邊界、狀態、exploratory 上限、整份沒有負向案例） | scope 內的需求，加上 TC 實際涉及的需求（`requirement_ids` 或 coverage_matrix 有 draft 的） |
| scope 外、沒有 TC 涉及的需求 | 不檢查；列在 `uncovered_with_reason` 也不檢查（相容舊報告） |
| 新增 FAIL | scope 列的需求不在綁定的 revision，或 scope 內沒有任何可設計的需求（非 ACTIVE 或未解決的 critical ambiguity）；某條 TC 的 `requirement_ids` 全部在 scope 外 |

scope 不是需求清單、或沒有 scope：行為不變（全部需求）。`mode=change`／`manual` 不受影響。

### 3. 派發包與提早檢查

Test Designer、Test Validator 的派發包新增 `run_scope: {raw, requirement_ids}`（run 有 `scope` 才寫入；`requirement_ids: null` 代表不是需求清單）。Spec Analyst 仍分析整份 spec，不帶 scope；TC Risk Reviewer 抽查的是 Draft 本身，不帶 scope。ADR-013 之前產生的派發包沒有這個欄位，gate 一律以 run 的 `input.scope` 判定，agent 指示也要求此時讀 run 的 `input.scope`。

scope 對不上綁定的 revision（列了 revision 沒有的需求，或沒有任何可設計的需求——G-DESIGN 不可能 PASS）時盡早拒絕，不讓 Designer 白做：
- `run new` 建立時已綁定 revision（T1 跳過）→ 拒絕建立 run（整個操作不寫入）；
- T1 要重新分析的 run，revision 在 T1 之後才有 → Designer／Validator 的 `dispatch` 拒絕，須取消 run 以正確的 scope 重開；
- G-DESIGN 另有同一條防線（`run_scope.pin_issues` 共用）。

## Consequences

- 範圍外需求不再需要 `NO_REJECTION_CONTRACT:`；這個前綴回到原本的意義（spec 沒有定義拒絕契約）。
- Designer 若在 scope 外設計 TC（TC 只涉及 scope 外需求）會被 G-DESIGN 擋下；要擴大範圍須重開 run。
- 用真實資料比對（主目錄 main `3d2e5332` 唯讀匯出）：既有 spec-to-testcase run 的最後一份設計產出在新舊規則下 G-DESIGN 的 issue 集合相同；RUN-20261013-002（T2 iter0，`ART-TDR-01M4RGYHPHE8C2C8A574VPPFYF`）、003（iter1，`ART-TDR-01M4RH8ER0MAQ56PHGRVV4R4EJ`）、004（iter1，`ART-TDR-01M4RHBRR3255BS51Y5GSNC4CY`）的報告拿掉範圍外的 uncovered 條目後，新規則 0 issue（舊規則分別 30／59／28 條「未被覆蓋」）。
  之後的資料版本中，TC 若順帶涉及範圍外的 high-risk 需求，該需求的 uncovered 豁免仍須保留（例如 main `d9f9e754` 的 RUN-20261013-004 T2 iter4，兩條 TC 涉及 REQ-DAILYREPORT-012）；拿掉的應是「範圍外且沒有 TC 涉及」的條目。這是本 ADR 規則的預期結果（Codex 審查 01 輪 m01）。
- 不在本 ADR 範圍：CLR 落地的「run 範圍」（`clr_lifecycle._run_scope`，需求 A 第 6 章 §5.6；附錄 A 6-31）對 spec-to-testcase 仍是整份 revision，沒有跟著 scope 收斂。Oscar 於 2026-10-13 決定先不改，另案處理。
- 測試：`tests/test_design_run_scope.py`。
