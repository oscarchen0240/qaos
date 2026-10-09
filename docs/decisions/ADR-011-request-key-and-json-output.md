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
  - 只在持有全域操作鎖時讀寫；新建以 link 一次建立，不會半寫。
  - 建立時點：產生計畫之後、**保存計畫之前**（擷取型計畫與 migrate rollback 的 planner 計畫都一樣）。所以只要計畫存在，key 一定已綁定它；之後任何時點中止、被 rollback 接管或終結，key 都不會變成未綁定。
  - 綁定的判斷（第 2 步之前，`_bound_op`）：
    - 索引指向的 op 有計畫檔，而且計畫的 `canonical_request.request_key` 就是這個 key → 已綁定；和這次算出的 op 不同 → `key_conflict`，不寫任何東西。
    - 索引指向的 op **沒有計畫檔路徑**（綁定之後、計畫保存之前中止，該 op 從未建立；殘留清理與登錄補齊之後，計畫檔存在 ⇔ 已登錄）→ 視為未綁定，本次請求改綁到自己的 op（原子取代）。「從未建立」只看路徑是否存在，不看解析結果。
    - 索引形狀不符；計畫檔路徑存在但和登錄紀錄不符（例如被外部改成空檔、YAML null 或清單，以 `verify_registration` 核對雜湊）；或計畫沒有帶同一個 key → 證據衝突（`internal`），需人工處理，不改綁、不寫入。
    - 同 key 同內容重送（回報已完成或續做）時會再核對一次綁定：索引指向從未建立的 op → 改回本 op；指向另一份計畫 → 證據衝突。
    - 限制：索引被竄改成指向不存在的 op、又在同內容重送修復之前以同 key 送出不同內容，會被當成未綁定（系統不另外掃描所有計畫找同 key）。正常流程不會產生這種狀態。
  - 綁定途中中止留下的暫存檔，在同一 op 下次綁定時清除（只清本 op、本 key 的暫存檔）。
  - 驗證失敗的請求（診斷輸出、沒有計畫）不綁定 key：同 key 可以修正內容後重送。
  - rollback 不清除索引：被回復（`rolled_back`、`aborted_for_rollback`）或被接管的 op 仍保有它的 key；同 key 同內容重送會被拒絕（終態），同 key 不同內容（包括以同一 key 發出的 rollback）→ `key_conflict`。要重做請換新 key。
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
  - `ids`：本 op 計畫記錄的 `allocated_ids` 依前綴命名（EVD → `evidence_id`、EXE → `execution_id`、RUN → `run_id`、APR → `approval_id`、BUG → `bug_id`、CLR → `clarification_id`、TC → `testcase_id`、REQ → `requirement_id`、AC → `acceptance_criteria_id`、MAN → `manual_record_id`）。同一種類配發多個時不放進 `ids`，只列在 `allocated_ids`。沒有配發計數器 ID 的指令（例如狀態轉換）`ids` 為 `{}`。
  - `allocated_ids` 只含**計數器 ID**（上列十種，`tools/qaos/ids.py`）。ULID 型的 `ART-…`（artifact、`qaos id ART-<TYPE>`）不寫計數器，不會出現在 `allocated_ids`／`ids`，只在 `result` 中。
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
  | `maintenance` | 維護中，一般寫入的准入拒絕 | 維護結束後再試 |
  | `locked` | 全域操作鎖由其他 executor 持有 | 稍後重試 |
  | `refused` | 業務規則或狀態機拒絕、op 已終結或被接管、已配發的 ID 不能重用、控制指令（maintenance、migrate、rollback）的狀態前置條件不符（例如已移轉後再 migrate） | 不要原樣重試 |
  | `internal` | 證據衝突、executor context 失效、未預期的例外 | 結果不明，需人工確認（`operation list`） |

- **argparse 層級的錯誤**（未知參數、缺必填參數、`--request-key` 與 `--new-request` 同時使用）維持原生行為：結束碼 2、usage 印在 stderr、stdout 沒有 JSON。
- `--json` 只用於寫入：和 `--stdout`（唯讀 export）、`migrate verify` 一起使用 → `validation`。
- `operation resume` 不在共用參數群組內，沒有 `--json`；呼叫端以同 key 重送即可續做。

### 3. `completed` 回放的是當時的結果

`outcome: completed` 時，JSON 的 `result` 與 `ids` 取自計畫當時存下的內容，**不是實體目前的狀態**（例如 run 之後被取消，回放的 `result.status` 仍是建立當時的狀態）。JSON 欄位不另外反映目前狀態；需要目前狀態的呼叫端自行讀取（admin-ui 讀 `run.yaml` 對帳，R07 的做法）。

`--json` 執行的是和不帶 `--json` 時相同的指令流程，只是把給人看的輸出改到 stderr，所以**部分指令在回放時仍會讀取目前狀態來產生人看的輸出**（例如 `run new` 回放顯示 run 目前的狀態、`clarification ask|answer|…`、`bug resolve|verify|close|transition` 顯示單據目前的狀態）。這個讀取失敗（例如實體檔已不存在）時，指令和不帶 `--json` 時一樣以錯誤結束，JSON 為對應的 `error_kind`（檔案不存在 → `validation`），不回傳計畫存下的結果；op 本身仍是 completed，可用 `operation list` 依 op_id 確認。結束碼一致性優先於「回放一定成功」。

### 4. `--new-request` 保留給「刻意重做」

`--new-request` 的語意不變：產生新 token、新 op，之後續做要用 `operation resume <op_id>`。有穩定身分的呼叫端（admin-ui）改用 `--request-key`；需要「每次都重做」的維護動作（例如重建 index）仍用 `--new-request`。

## Consequences

- **對 agent 沒有影響**：`agents/`、`.claude/agents/` 沒有使用 `--new-request`（repo 沒有 `skills/` 目錄），也不需要 `--request-key`；agent 合約不變。
- admin-ui（C 階段）所有寫入改帶 `--json --request-key`，解析 JSON 取 ID，移除 EVD／EXE／RUN 的正則與 R02 的暫擋比對；key 規劃見 `review-handoff/admin-ui-backend-review/evaluation-02.md` §3.3。
- 新增的持久資料只有 key 索引檔；既有計畫、登錄、狀態紀錄的格式不變。
- 測試：`tests/test_request_key.py`。
