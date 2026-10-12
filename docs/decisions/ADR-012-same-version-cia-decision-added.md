# ADR-012 · 同版本 CIA 新增 reason `decision_added`（同版本新回答的 CLR 落地）

- **Status**: Proposed——merge 後生效，Accepted 日期由 Oscar 於合併時確認。
- **範圍**：需求 A 第 5 章 §6、§8；附錄 A 5-19～5-21。程式：`tools/qaos/rm.py` 的 `decision_added`、`engine.py` 的同版本 CIA 檢查與 `WARN_DECISION_ADDED` 提示。

## Context

同版本 CIA（`run new spec-change-impact`，`from_version == to_version`）原本只接受三種 reason：

| reason | 判定 |
|---|---|
| `declaration_changed` | 目標或閉包的宣告改變 |
| `decision_revised` | revision **引用的** CLR 有更新的答案，或已撤回 |
| `decision_applied` | revision **引用的** CLR 在 revision 之後新增了 applied landing |

三者都以「revision 已引用的 CLR」為前提。同一版本**新開並回答**、但目前 revision 從未引用的 CLR，三種判定都不成立，`run new` 拒絕，新答案無法落地到同版本的 RM，也就進不了 TC 影響分析。

實例（2026-10-12）：CLR-TXLOG-002（SPEC-TXLOG-001@0.1，REQ-TXLOG-028）已 ANSWERED（requirement_clarified），推翻 2026-09-14 依 CLR-TXLOG-001 改寫的「本頁不提供手動取消」。TXLOG 只有 legacy R000，`rm.outdated()` 三旗標皆 false，`decision_applied()` 也是 false。AC-09-15 的測試（PLATFORMRULE 形狀）當時也只能借用 `declaration_changed`。

## Decision

### 1. 新增 reason `decision_added`

`rm.decision_added(pin)` 回傳成立的 CLR ID 清單（空＝不成立）。CLR 必須同時符合：

1. 位於 T0 決議快照的範圍（目標 spec 的 area 與直接參考的 area，與 `dispatch._areas` 相同），而且最新答案**落在 from_revision 的版本**（落地途徑，對應 X16 的兩種適用依據）：
   - 自身版本：CLR 的 `spec_id@spec_version` 就是這個版本；但 `spec_updated` 且 `resulting_spec_version` 指向其他版本時不算——答案落在那個版本的 spec 原文；
   - 適用紀錄：最新 answer_rev 有指向這個 spec、`basis_hash` 等於這個版本目前 basis_hash 的 applicability（同 spec 跨版本、跨 spec 的落地都走這條）；
2. 狀態是 ANSWERED 或 INCORPORATED；
3. 最新 answer_rev 的 resolution 是 `requirement_clarified` 或 `spec_updated`；
4. from_revision 沒有引用這張 CLR 的任何 answer_rev，同版本的其他 revision 也沒有引用最新 answer_rev；
5. 至少一個落地途徑不在 from_revision 的分析範圍內（見 2）。

不納入的情形與理由：

- **APPLIED**：已經人工確認落地（apply 的 impact 掃描）。CLR-TXLOG-001 就是 APPLIED，TXLOG R000 只會判出 CLR-TXLOG-002。
- **no_change、out_of_scope**：不改需求，結案走 a7。
- **from_revision 引用舊 answer_rev**：屬 `decision_revised`，兩種判定互斥。
- **同版本較新的 revision 已引用最新答案**：答案已落到這個版本的 RM；再從舊 revision 做同版本 CIA 沒有意義（TC 依各自的 pin 分組，不依 from_revision）。
- **spec_updated 指向新版本**：例如 CLR-REDPACKET-026～050（resulting 0.2）不會讓 REDPACKET 0.1 成立。

### 2. 「分析範圍」：以決議快照為準，時間只作退回

| from_revision | 規則 |
|---|---|
| R000 | 沒有分析紀錄 → 任何符合其餘條件的 CLR 都算。比照附錄 A 5-14 對 `decision_applied` 的處理。legacy 檢視的 `persisted_at` 是寫檔時間，不反映之後的人工改寫（例如 TXLOG 2026-09-14 依 CLR-TXLOG-001 改寫），不作為分析時間 |
| 有 `dispatch_packet_sha256` | 依 revision 的 `run_id` 在 run 的派發紀錄找到該派發包（sha256 相符）。答案不在 `resolutions` 中，或適用紀錄是快照之後才補的，才算。找不到 → 拒絕（「無法判定」），不改用時間推定 |
| 沒有派發包（P4 之前的分析） | 回答（適用紀錄）時間不早於 revision 的 `created_at` 才算。時間精度到秒，同一秒無法分先後，視為沒看過（寧可放行 CIA，不漏掉答案） |
| `accepted_without_analysis`（accept-declaration） | 沒有經過分析 → 沿用 parent 的判定 |

原本建議的「答案建立在 from_revision 之後」只看時間，有兩個漏洞：

- T0 派發之後、G-SPEC 持久化之前回答的 CLR，回答時間早於 revision 建立時間，卻沒有被分析看過；
- accept-declaration 產生的 revision 建立得比答案晚，但需求內容是從 parent 複製的，同樣沒有看過。

以決議快照判定可以直接回答「這次分析有沒有看過這個答案」。

### 3. 不擋 `_skip`，也不擋無 T0 流程的 `run new`；只記 audit 警告

比照 `decision_applied`，`decision_added` 只是同版本 CIA 的 reason。跳過 T0、或 testcase-revision／manual 凍結 revision 時，若判定成立，run 的 audit 記一筆 `WARN_DECISION_ADDED`（列出 CLR 與建議的 reason），不改變放行結果；判定本身失敗時也只記警告。理由：

1. `decision_revised` 證明 revision 的依據已經失效；`decision_added` 只表示「可能需要重新分析」，答案也可能早已人工反映在 legacy 需求中。
2. 2026-10-12 的現況有 5 個 spec 版本成立（CASHFLOW 0.1、DAILYREPORT 0.2、REDPACKET 0.2、SITELIST 0.7、TXLOG 0.1）。如果擋下，這些版本的 testcase-revision、manual 會全部停擺，spec-to-testcase 一律重跑 T0，影響 TC 更新排程。
3. CLR 本身已有未落地的訊號（ANSWERED／INCORPORATED、未 APPLIED），結案必須經 apply 的 impact 掃描。

已知風險：在 CLR 落地之前做 testcase-revision（例如 TXLOG 0.1），TC 會綁仍寫著舊結論的 revision；audit 警告會提示，但不阻擋。日後若要改為擋下，另以 ADR 決定。

### 4. 錯誤訊息

reason 不符時，錯誤訊息附上該 reason 的判定條件。派發包找不到、資料欄位缺漏等問題，以「無法判定」拒絕，不建立 run。

## Consequences

- `run new spec-change-impact … --input reason=decision_added` 可以把同版本新回答的 CLR 帶進 T0。T0 的決議快照本來就收錄同 area 已回答的 CLR；新 revision 以 clarification 型 SourceRef 採用最新 answer_rev、通過 X16 時，CLR 依 A4 轉 INCORPORATED。run COMPLETED 後以 `clarification apply --path a6 --landed-in <run>` 結案。
- X16 照舊：CLR 自身的範圍只涵蓋它自己的 `requirement_id` 與 `subject`。同一張 CLR 要作為其他需求決策點的依據（例如 CLR-TXLOG-002 之於 REQ-TXLOG-017、029），需先以 `clarification applicability add` 補人工適用紀錄；否則這些需求只能以 spec 原文為依據改寫。
- 測試：`tests/test_same_version_decision_added.py`（端到端 T0→A4→G-IMPACT→apply a6；R000；no_change／out_of_scope；撤回；同 area 其他 spec；已被引用；同版本其他 revision 已引用；引用舊 rev 與 `decision_revised` 互斥；派發後才回答、快照內未採用、派發包遺失；accept-declaration 沿用 parent；沒有派發包時以時間判定；spec_updated 指向其他版本；applicability 途徑；不擋 `_skip` 與 testcase-revision 但記 audit 警告；reason 不符時拒絕且不建立 run）。
