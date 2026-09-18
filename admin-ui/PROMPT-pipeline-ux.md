# Prompt：優化 QAOS Pipeline 指揮台（給 Claude Code）

請在 `~/Desktop/qa-agent-os/admin-ui` 實作下列 Pipeline 監看 UX 優化。只改管理介面（frontend / backend / 必要時 `config/stages.yaml`），**不要改 QAOS Runtime 狀態機、workflow yaml、agent contract**。

讀完再動手：

- `admin-ui/PLAN.md`（尤其 §1.2、hook 與 run.yaml 的關係）
- `admin-ui/config/stages.yaml`
- `admin-ui/frontend/src/pages/PipelinePage.tsx`
- `admin-ui/frontend/src/pages/pipeline/parts.tsx`
- `admin-ui/backend/services/pipeline.py`
- `admin-ui/README.md` 裡 Pipeline 行為說明

原則：**`runs/<RUN>/run.yaml` 是事實來源；Claude Code hook 只補即時 agent 活動。** 畫面必須讓人 3 秒內知道：這條算不算活的、卡在哪、要不要人出手。

---

## 問題（目前畫面已出現）

實例：`SPEC-SITELIST-001@0.4` / `RUN-20260916-007` / session `17db7604`

- Session `HealthTag` 顯示「進行中」，`RunStatusTag` 顯示「已取消」，階段 3–8 全是「已取消」，「目前 agent」為空，副標卻寫「目前階段：結案」。三種來源互相矛盾。
- Run 已取消，大時鐘還在累加（例如 29m）。
- 未真正執行的後段階段也被標成「已取消」，與「做到一半取消」無法區分。
- Gate 名稱被截成 `G-SP…`、`G-D…`。
- `iter 10` 沒有對照架構上限（Designer⇄Validator 預設最多 3 輪）。
- 已取消階段上的 `APR-0112` / `APR-0113` 仍用 warn 色，看起來像還在等核准。
- 「Agent 活動」在 hook 沒事件時顯示「尚無子 agent 事件」，但其實 `run.yaml` 的 task history 有資料。
- 「final 寫入」只認 Write/Edit hook；實際匯出常用 Bash `cp`，應以 `testcases/final/` 檔案掃描為主（見 `stages.yaml` notes）。
- 同 session 的 `RUN-20260916-008 已完成` 埋在右下。
- `lanes: 3` 在只有 1 條活 session 時仍顯示兩個「預留 pipeline 車道」，浪費空間。
- 已取消／已結束的 session 仍佔「即時」第一欄。

---

## 目標行為

### 1. 單一主狀態（最優先）

合成一個給人看的 **primary status**，優先序：

1. `run.yaml` 的 `status`（CANCELLED / FAILED / WAITING_HUMAN / RUNNING / COMPLETED / CREATED）
2. 目前階段（測試設計／人工核准…）
3. Session health（live / stalled / dead / ended）只當次要標籤

頂列標題區應類似：

- `SITELIST v0.4 · 已取消`（session 仍連線）
- 或 `SITELIST v0.4 · 等你決定 APR-xxxx`
- 或 `SITELIST v0.4 · 執行中 · 測試設計`

規則：

- Run 已 `CANCELLED` / `FAILED` / `COMPLETED` → **停止累計「已執行」時鐘**，改顯示「跑了多久後結束／取消」。
- Session 仍 live 但 run 已結束 → 主狀態跟 run，health 用較淡的「session 仍連線」。
- 不要同時用綠色「進行中」+「已取消」。

請在 backend 組好欄位（例如 `primary_status`、`primary_label`、`clock_frozen`），前端不要自己猜。

### 2. Next action 一行（固定、最醒目）

每條 lane 頂部（階段大綱上方）加一條 **現在要你做什麼**，只顯示一句 + 可點連結：

| 條件（由上而下第一個命中） | 文案方向 |
|---|---|
| `WAITING_HUMAN` 或階段 `waiting_human` | **請核准 {APR-id}**（點開 RunDrawer 或 approval） |
| 有未回答 Clarification（若 snapshot 已能拿到） | **請回 {CLR-id}** |
| health = stalled 且 run 仍 RUNNING | **可能卡住，已安靜 N 分鐘** |
| 目前 task `GATE_FAILED` | **Validator FAIL，回 Designer 修 · 第 n / max 輪** |
| run CANCELLED/FAILED 且 session 仍 live | **Run 已停，可忽略此 session**（帶「忽略」按鈕，沿用現有 `patchSession ignored`） |
| COMPLETED 且該 spec 在 `testcases/final/` 有檔 | **產出已可審**（連到產出頁） |
| 其餘 RUNNING | **進行中：{目前階段}** |
| 無 run、僅 hook | 維持「無關聯 run（僅事件）」 |

一次只顯示一條。不要做成 checklist。

### 3. 階段條（StageRail）

- Gate **完整顯示**（`G-SPEC`、`G-DESIGN`、`G-TVAL`、`G-APPROVAL`），禁止 CSS 截斷到看不懂。
- 區分階段狀態：
  - `done` 完成
  - `active` / `live` 進行中
  - `waiting_human` 等你決定
  - `failed` 失敗
  - `cancelled` **實際開始後被取消**
  - `skipped` / `pending` **從未開始就被略過**（run 取消或失敗時，後面沒 started_at 的階段用這個，不要全打已取消）
- 目前階段節點加大／pulse 更明顯。
- `iteration`：若 ≥ `max_validation_iterations`（workflow 預設 3，可從 run/workflow 讀；讀不到就當 3）→ 警告色，標「超限」或「第 n / 3 輪」。
- `approval_id`：僅當該階段／run 仍在等核准時用 warn 醒目色；已取消／已完成則淡色「曾開單 {id}」。
- Designer ⇄ Validator 迴圈：在測試設計與獨立驗證之間標明 `⇄` 或副標 `第 n 輪`，避免被看成純線性。

### 4. Agent 活動：runtime 為主，hook 為輔

「Agent 活動（最近 12 筆）」在 hook `agents[]` 為空時，**必須**用 `run.yaml` 的 tasks / history / gate_results 產生時間軸，例如：

- T1 DONE → Spec 分析完成
- T2 RUNNING → Designer 執行中
- T3 GATE_FAILED → Validator FAIL
- T4 WAITING_HUMAN → 等待核准

有 SubagentStart/Stop 再疊在對應時間點。禁止再因沒有 hook 就顯示「尚無子 agent 事件」（除非連 run 都沒有）。

### 5. Final 寫入：掃檔案系統

不要只靠 PostToolUse Write/Edit。

- 依 `stages.yaml` 的 `outputs.glob` 掃描 `testcases/final/*-final*.{html,json}`。
- 能對上目前 spec / functional area 的，顯示檔名、mtime、可連到產出頁。
- 若只有 Bash cp、沒有 hook：文案改為「由產出頁檔案掃描偵測」，不要暗示「完全沒匯出」。

### 6. 相關 run 抬到頂

同 session `related_runs` 裡，若 **目前 active run 已取消／失敗** 且另有 `COMPLETED`，在 lane 頭或 Next action 旁顯示：

`同 session 另有 {RUN-id} {spec} 已完成`

可點開 RunDrawer。不要只埋在右下「其他相關 run」。

### 7. 即時分頁版面

- 只有 1 條 lane 時：**不要渲染空的預留車道**。
- `lanes.length >= 2` 才並排；空車道可完全不畫（`max_lanes` 留給後端選哪些 session，不必在 UI 佔位）。
- 「即時」預設只放：RUNNING、WAITING_HUMAN、stalled（run 仍活著）。
- `CANCELLED` / `COMPLETED` / `FAILED` 且非使用者明確「追蹤中」→ 不要佔即時第一欄，讓它們待在「歷史 Session」。
- 已追蹤（`tracked: true`）的結束 session 可留在即時，但主狀態必須清楚是已結束，且時鐘凍結。

### 8. 文案與標籤

- 保持繁中。
- `HealthTag` 與 `RunStatusTag` 不要搶同一個視覺權重；run 主狀態用較大標籤。
- 更新 `admin-ui/README.md` 一小段：說明主狀態規則、Next action、即時不分空車道、final 靠檔案掃描。

---

## 驗收（請自己在瀏覽器或至少用現有 snapshot 邏輯核對）

1. 用「run=CANCELLED + session=live」這種資料：主標是已取消，不是進行中；時鐘凍結；後段階段是略過不是全取消；Next action 建議忽略 session。
2. Gate 名稱完整可見。
3. iter ≥ 3 有警告樣式。
4. hook 無 agents 時，活動區仍有來自 run.yaml 的列。
5. `testcases/final/` 有對應檔時，final 區不是空的「尚無 Write/Edit」。
6. 僅 1 條即時 session 時沒有「預留 pipeline 車道」。
7. 不迴歸：SSE／輪詢、設為追蹤、忽略 session、RunDrawer／SessionDrawer 仍可用。

---

## 不要做

- 不要重寫整個 admin-ui。
- 不要把 Structural Gate 改成 LLM 判斷。
- 不要新增 Model Router。
- 不要為了 UI 改 `tools/qaos` 的 commit／approval 語意。
- 不要一次做桌面系統通知、產出頁大改、Runs 分頁大翻修（可列為後續，本次不做）。

做完請列出改了哪些檔、主狀態怎麼合成、以及如何用現有 SITELIST 取消 run 驗證。
