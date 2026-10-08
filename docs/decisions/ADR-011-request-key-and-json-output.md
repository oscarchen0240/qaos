# ADR-011 · 寫入指令的穩定請求身分（`--request-key`）與機器可讀輸出（`--json`）

- **Status**: Proposed——Oscar 2026-10-08 核准「第 3 批：CLI 加 `--request-key`、`--json`，補 ADR」；2026-10-09 定案順序「第 1 批 merge → B1（本 ADR）與 B2 並行 → C（admin-ui 改用新 CLI）」。本 ADR 隨 B1 的 MR 合併後生效，Accepted 日期由 Oscar 於合併時確認。
- **延伸**：需求 A 最終規格第 4 章 §3（CanonicalRequest 與 op_id）。不取代任何既有契約：不帶新參數時行為完全不變，`request_schema` 不升版。

## Context

admin-ui 後端以子程序呼叫 `bin/qaos` 寫入 QAOS。後端審查（review-01）指出三個根源相同的問題：

- **R01**：人工決定（CLR ask／answer／withdraw、Bug 決定）每次都帶 `--new-request`。第一次在登錄計畫後中止，重送時產生新的 token、算出另一個 op，被第 3b 步「存在未完成的計畫」擋下，原計畫沒有機會續做。
- **R02**：兩筆不同 admin 測試結果的 `execution import` 參數完全相同時，CLI 依規格把第二次視為同一請求的重送，回傳第一筆的 EXE；平台卻把它當成新匯入。呼叫端沒有辦法表達「這是另一件事」又「同一件事重試時不要重做」。
- **R07**：平台從人看的 stdout 用正則擷取 ID，分不出「新建立」「已完成的回放」「續做」，把回放的舊 run 當成新開的工作。

`--new-request` 只能表達「刻意再做一次」，而且 token 只在第一次產生，之後必須改用 `operation resume <op_id>`；呼叫端若沒保存 op_id，重試就無法回到原計畫。

## Decision

### 1. `--request-key <key>`

- 加在所有寫入指令共用的參數群組，和 `--new-request` **互斥**（同時帶 → argparse 錯誤；API 層 `run_operation` 也拒絕）。
- 格式：`[A-Za-z0-9:._/-]{1,128}`，不符 → 拒絕（`validation`），不寫任何東西。
- 有 key 時 CanonicalRequest 加上 `request_key`，**不加** `new_request_token`：
  - 同 key、同內容 → 同一 op → 第 2 步：已完成就回報 `completed`、不寫入；未完成就續做（`resumed`）。第 2 步在第 3b 步之前，所以**中斷後用同一 key 重試會續做自己的計畫，不會被「存在未完成的計畫」擋下**（R01）。
  - 不同 key、同內容 → 不同 op（R02：每筆 admin 測試結果用自己的 key）。
  - 同 key、不同內容 → **拒絕**（`key_conflict`），不寫任何東西。呼叫端改了草稿內容就必須換新 key；否則會靜默變成另一個 op。
- **key 索引**：`operations/_global/request_keys.d/<sha256(key)>.yaml`，內容 `{request_key, op_id}`。
  - 只在持有全域操作鎖時讀寫；以 link 一次建立（已存在且內容相同 → 不動；內容不同 → 證據衝突），不會半寫。
  - 建立時點：計畫**登錄之後、執行第一步之前**。登錄後、建立索引前中止的計畫，在下次同 key 重送（第 2 步）、`operation resume` 或回報已完成時補齊。
  - 衝突判斷在第 2 步之前：key 已綁定的 op 和這次算出的 op 不同 → `key_conflict`。
  - 已知窗口：計畫登錄後、索引建立前中止，又在續做之前以同 key 送出**不同內容**——此時索引還沒有這個 key，請求會被第 3b 步以 `incomplete_plan` 擋下（附上未完成的 op），而不是 `key_conflict`。續做該 op 後索引即補齊。
  - 驗證失敗的請求（診斷輸出、沒有計畫）不綁定 key：同 key 可以修正內容後重送。
  - rollback 不清除索引：被回復（`rolled_back`、`aborted_for_rollback`）的 op 以同 key 重送會被拒絕（終態），要重做請換新 key。
- **audit**：有 key 的請求在計畫中追加一筆全域事件 `REQUEST_KEY`（detail `<key> → <action>`），進入 `runs/_audit.d` 與 render 後的 audit.log。`migrate rollback`（不經擷取的計畫）只把 key 記在計畫的 `canonical_request`。
- 不帶 `--request-key` 時行為與之前完全相同。

### 2. `--json`

- 加在同一個參數群組。開啟時 **stdout 只輸出一個 JSON 物件（一行）**；給人看的輸出與提示（含「先前已完成」的說明）一律改到 stderr。結束碼和不帶 `--json` 時相同。
- 成功：

  ```json
  {"ok": true, "outcome": "new|completed|resumed|diagnostic", "op_id": "<完整 op_id；diagnostic 為 null>", "action": "<action>",
   "request_key": "<key 或 null>", "ids": {"evidence_id": "...", "execution_id": "...", "run_id": "..."},
   "allocated_ids": ["..."], "result": <寫入函式的回傳值>, "exit_code": <只在非零時出現>}
  ```

  - `outcome` 取自 executor 的 `LAST_OUTCOME.kind`。
  - `ids`：本 op 計畫記錄的 `allocated_ids` 依前綴命名（EVD → `evidence_id`、EXE → `execution_id`、RUN → `run_id`、APR → `approval_id`、BUG → `bug_id`、CLR → `clarification_id`、TC → `testcase_id`、REQ → `requirement_id`、AC → `acceptance_criteria_id`）。同一種類配發多個時不放進 `ids`，只列在 `allocated_ids`。沒有配發計數器 ID 的指令（例如狀態轉換）`ids` 為 `{}`。
  - `result`：`new` 時是本次寫入函式的回傳值；`completed`、`resumed` 時是**計畫當時存下的結果**。
  - 寫入成功、但指令依既有語意以非零結束（例如 gate FAIL、submit INVALID）：`ok: true`，加上 `exit_code`，程序結束碼照舊。
- 失敗（程序結束碼非零）：

  ```json
  {"ok": false, "error_kind": "refused|incomplete_plan|maintenance|locked|validation|key_conflict|internal",
   "message": "...", "incomplete_ops": ["<op_id>", ...]}
  ```

  | error_kind | 來源 | 呼叫端的處理 |
  |---|---|---|
  | `validation` | 輸入不合法：參數格式、key 格式、指令層的輸入檢查、檔案不存在 | 修正輸入；沒有寫入 |
  | `key_conflict` | key 已用於不同內容 | 內容改變 → 換新 key |
  | `incomplete_plan` | 第 3b 步或續做 V3：有其他未完成的計畫；`incomplete_ops` 列出 op | 先續做（同 key 重送或 `operation resume`） |
  | `maintenance` | 維護中，准入拒絕 | 維護結束後再試 |
  | `locked` | 全域操作鎖由其他 executor 持有 | 稍後重試 |
  | `refused` | 業務規則或狀態機拒絕、op 已終結或被接管、已配發的 ID 不能重用 | 不要原樣重試 |
  | `internal` | 證據衝突、executor context 失效、未預期的例外 | 結果不明，需人工確認（`operation list`） |

- **argparse 層級的錯誤**（未知參數、缺必填參數、`--request-key` 與 `--new-request` 同時使用）維持原生行為：結束碼 2、usage 印在 stderr、stdout 沒有 JSON。
- `--json` 只用於寫入：和 `--stdout`（唯讀 export）、`migrate verify` 一起使用 → `validation`。
- `operation resume` 不在共用參數群組內，沒有 `--json`；呼叫端以同 key 重送即可續做。

### 3. `completed` 回放的是當時的結果

`outcome: completed` 時，`result` 與 `ids` 是計畫當時存下的內容，**不是實體目前的狀態**（例如 run 之後被取消，回放的 `result.status` 仍是建立當時的狀態）。CLI 不另外查目前狀態；需要目前狀態的呼叫端自行讀取（admin-ui 讀 `run.yaml` 對帳，R07 的做法）。人看的輸出（stderr）照舊顯示目前狀態。

### 4. `--new-request` 保留給「刻意重做」

`--new-request` 的語意不變：產生新 token、新 op，之後續做要用 `operation resume <op_id>`。有穩定身分的呼叫端（admin-ui）改用 `--request-key`；需要「每次都重做」的維護動作（例如重建 index）仍用 `--new-request`。

## Consequences

- **對 agent 沒有影響**：`agents/`、`.claude/agents/` 沒有使用 `--new-request`（repo 沒有 `skills/` 目錄），也不需要 `--request-key`；agent 合約不變。
- admin-ui（C 階段）所有寫入改帶 `--json --request-key`，解析 JSON 取 ID，移除 EVD／EXE／RUN 的正則與 R02 的暫擋比對；key 規劃見 `review-handoff/admin-ui-backend-review/evaluation-02.md` §3.3。
- 新增的持久資料只有 key 索引檔；既有計畫、登錄、狀態紀錄的格式不變。
- 測試：`tests/test_request_key.py`。
