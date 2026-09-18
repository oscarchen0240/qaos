# QAOS 管理介面 — 第 0 步規劃（待確認）

## 1. 現有 TC 產生系統的理解

### 1.1 實際結構（與任務描述的差異）
- 最終產出目錄是 **`testcases/final/`**（不是 `testcase/final/`）。
- 專案語言 **100% Python 3.11**（`tools/qaos/` Runtime CLI + `bin/qaos`），無 Node 專案；但機器上有 Node 24 / npm 11。
- 「多 agent 協作」目前的真實形態：
  | 角色（agents/*.yaml） | 實際執行者 | 可觀測方式 |
  |---|---|---|
  | Supervisor | 主 Claude Code session（名稱「QA Agent Operating System Architecture」，session_id `17db7604…`） | `bin/qaos run new/submit/gate/approve` → `runs/<RUN>/run.yaml` |
  | Spec Analyst (T1) | 主 session 手寫腳本 `tools/manual-runs/*_t1_spec_analyst.py` | run.yaml T1；hook 看不到「agent」 |
  | Test Designer (T2) | **`.claude/agents/qaos-test-designer.md` 子 agent**（Phase 3 起，透過 Agent 工具派工，已 13 次） | hook `SubagentStart/Stop` 的 `agent_type=qaos-test-designer` |
  | Test Validator (T3) | 每輪全新的 `general-purpose` 子 agent（description 含「獨立審查」，已 53 次） | hook `agent_type=general-purpose`（弱訊號） |
  | Human Approval (T4) | 你 | run.yaml `WAITING_HUMAN` + `approvals/APR-xxxx.yaml` |
  | 交叉整合 | 主 session 逐條 `bin/qaos tc revise` | 一連串 `testcase-revision` run |
  | 匯出 final | 主 session 用 **Bash `cp /tmp/... testcases/final/`** | 只有檔案系統看得到（PostToolUse Write/Edit 抓不到） |

### 1.2 Workflow（`workflows/spec-to-testcase.yaml`）
`T1 spec-analyst (G-SPEC)` → `T2 test-designer (G-DESIGN)` ⇄ `T3 test-validator (G-TVAL)`（最多 3 輪，超限 HUMAN_OVERRIDE）→ `T4 approval ACTIVATE_TESTCASE` → `T5 supervisor summary`。
`runs/<RUN>/run.yaml` 對每個 task 都有 `status / iteration / started_at / ended_at / history[] / gate_results[]`，**這就是現成的階段層級狀態**，不需要靠 hook 才能知道 pipeline 走到哪。

### 1.3 `testcases/final/` 格式與命名
- `<AREA>-final-active.json`：JSON **陣列**，每個元素是一條 ACTIVE `TestCaseVersion`（欄位：`testcase_id, title, functional_area, spec_id, spec_version, requirement_ids[], priority, risk, steps[], expected_result, assumptions[], status, version, created_at, updated_at, approval_id …`）。**案例數 = 陣列長度**；模組 = `functional_area`；產生時間 = 檔案 mtime（JSON 本身沒有匯出時間戳，可另取 `max(updated_at)`）。
- `<AREA>-final.html`：單頁人可讀報表，`<title><AREA> 測試案例集</title>`，自含 CSS，可直接 iframe 預覽。
- 目前有 MEMBER（26 條）、CASHFLOW（60 條）兩組；同一 AREA 重新匯出會**覆寫同名檔**（版本靠 mtime / JSON 內 `version` 欄位辨識）。

## 2. Hook payload 查證結果（Claude Code 2.1.66 官方文件）
| 事件 | 主要欄位 |
|---|---|
| SessionStart | `session_id, transcript_path, cwd, hook_event_name, reason(startup/resume/clear/compact/fork), model` |
| SessionEnd | `session_id, transcript_path, cwd, hook_event_name, reason` |
| Stop | `session_id, prompt_id, transcript_path, cwd, hook_event_name, last_assistant_message` |
| SubagentStart | `session_id, prompt_id, cwd, hook_event_name, agent_id, agent_type, subagent_name` |
| SubagentStop | 同上 + `last_assistant_message` |
| PostToolUse | `session_id, hook_event_name, tool_name, tool_use_id, tool_input{file_path,…}, tool_response`；子 agent 內的 Write 也會觸發並帶 `agent_id` |

- **agent 名稱拿得到**（`agent_type` / `subagent_name`），不需替代方案。可選的加值：讀 `~/.claude/projects/<proj>/<session>/subagents/agent-<id>.meta.json`（唯讀，含 `description` 例如「CASHFLOW T2修訂輪(iteration 1)」）把 general-purpose 區分成 Validator。
- hook 子程序**繼承啟動時的環境變數**（除 OTEL_*），所以 `QAOS_TRACK=1 claude` 的標籤法可行；但沒有官方 session 標籤機制。
- hook 可放在 `.claude/settings.local.json`；`timeout` 單位為秒。
- 注意：hook 設定是在 session 啟動時載入，**正在跑的那個 session 可能要重啟／resume 才會開始送事件**——所以 pipeline 面板不能只靠 hook，要以 run.yaml 為主、hook 為即時補充。
- 實測探針已備好（`scratchpad/hooktest/`），但 `claude -p` 不能在 Claude Code 內巢狀啟動（會影響正在跑的 session），我沒有繞過；你可在一般終端機執行一次確認真實 payload（見 §8）。

## 3. Session 過濾方案（請選）
| 方案 | 做法 | 優點 | 缺點 |
|---|---|---|---|
| **A. UI 手選 + 自動建議（推薦）** | hook 記錄所有 session；後端把「曾出現 `agent_type=qaos-test-designer`」的 session 標為建議追蹤；UI 可切換／忽略；選擇存在 SQLite；開發本介面的 session 預設加入忽略清單 | 對 Desktop App 啟動的 session 也有效（無法設環境變數）；不會漏 | 第一次要手動點一下 |
| B. 環境變數標籤 | `QAOS_TRACK=1 claude` 啟動；hook 把 `tag` 寫進事件；後端只算有 tag 的 | 零誤判 | 目前那個 session 是 Desktop App 開的，設不了環境變數；忘記帶就整段沒紀錄 |
| C. 全自動 | 只用建議規則，不給手選 | 零操作 | 誤判無法修正 |

實作上 A 會同時支援 B（hook 腳本一律記 `tag` 欄位，有就用）。

## 4. 技術選型
- **後端：Python 3.11 + FastAPI + uvicorn**（沿用專案語言；venv 在 `admin-ui/.venv`，依賴：fastapi、uvicorn、pyyaml、markdown）。資料用 **SQLite**（stdlib `sqlite3`，無 ORM）存 `admin-ui/data/admin.db`。SSE 推事件（`text/event-stream`，無額外依賴）。
- **前端：React 18 + Vite + TypeScript**，自寫 CSS（深色、指揮中心風格，不用 UI kit），`react-router`、`@dnd-kit`（看板拖曳）。開發時 Vite proxy `/api` 到後端；build 後由 FastAPI 直接 serve `dist/`。
- **一鍵啟動**：`admin-ui/dev.sh`（第一次自動建 venv + npm install，之後直接起前後端）。
- 替代方案（若你不想裝任何套件）：後端改用 stdlib `http.server`，功能相同、程式碼較醜；請告訴我要不要。

## 5. 資料模型（SQLite，`admin-ui/data/admin.db`）
```
todos            id, title, status(todo|doing|done), scheduled_date, due_date, estimate_min,
                 details, linked_output_path, linked_report_id, position, created_at, updated_at, completed_at
output_reviews   output_path PK, review_status(pending|reviewed|returned), note,
                 first_seen_at, last_seen_mtime, last_seen_size, acknowledged_at
reports          id, title, summary, body_md, created_at, updated_at
report_outputs   report_id, output_path, PK(report_id, output_path)
sessions         session_id PK, label, tracked(bool), ignored(bool), first_seen_at, last_seen_at
settings         key PK, value
-- M4 stub（只建表、不實作）
test_runs        id, name, trigger, started_at, ended_at, status
test_results     id, run_id, testcase_id, result, duration_ms, log_path
```
hook 事件**不進 SQLite**：後端啟動時讀 `.warroom/events.jsonl`（含輪替檔 `events.1.jsonl`…），之後 tail 增量解析成記憶體內的 session/stage 狀態，並定期輪詢 `runs/*/run.yaml` mtime 與 `testcases/final/`。

## 6. 頁面清單（左側導覽 3 組）
```
監控   ├ Pipeline（Agent 執行狀態）  tabs：即時 / 歷史 Session / Runs         徽章：進行中 session 數
       └ 產出                         tabs：全部 / 待審 / 已審 / 退回；右側預覽面板   徽章：未讀新產出數
工作   ├ 報告                         列表 + 編輯頁（標題/摘要/內文 Markdown/引用產出）；匯出 MD/HTML   徽章：報告數
       └ 待辦                         tabs：看板(待處理/進行中/已完成) / 已完成歷史；右側滑出新增/編輯   徽章：未完成數
未來   └ 自動化測試                   「規劃中」空狀態 + 預留路由/型別/API stub
```
版面：深色主題、固定左欄導覽（分組標題＋徽章）、主區塊頂部標題＋說明＋右上主要按鈕、內容區 tabs（附數量）、右側滑出面板（新增/編輯/預覽共用）。

## 7. Hook 腳本與設定（M3 才寫入，先給你看方向）
- `admin-ui/hooks/log_event.sh`：`cat` stdin → 用 `python3 -c`（或純 `sed`）抽 `ts, session_id, hook_event_name, agent_id, agent_type, subagent_name, tool_name, file_path(只留 testcases/final/ 前綴), reason, tag=$QAOS_TRACK, cwd` → `>> .warroom/events.jsonl`；檔案 > 5 MB 時 `mv` 成 `events.1.jsonl`（保留 3 份）；全程 `2>/dev/null; exit 0`；不輸出任何 stdout。
- `.claude/settings.local.json` 預計內容（**寫入前會再給你確認**）：
```json
{
  "hooks": {
    "SessionStart":  [{"hooks":[{"type":"command","command":"\"$CLAUDE_PROJECT_DIR\"/admin-ui/hooks/log_event.sh","timeout":5}]}],
    "SessionEnd":    [{"hooks":[{"type":"command","command":"\"$CLAUDE_PROJECT_DIR\"/admin-ui/hooks/log_event.sh","timeout":5}]}],
    "Stop":          [{"hooks":[{"type":"command","command":"\"$CLAUDE_PROJECT_DIR\"/admin-ui/hooks/log_event.sh","timeout":5}]}],
    "SubagentStart": [{"hooks":[{"type":"command","command":"\"$CLAUDE_PROJECT_DIR\"/admin-ui/hooks/log_event.sh","timeout":5}]}],
    "SubagentStop":  [{"hooks":[{"type":"command","command":"\"$CLAUDE_PROJECT_DIR\"/admin-ui/hooks/log_event.sh","timeout":5}]}],
    "PostToolUse":   [{"matcher":"Write|Edit","hooks":[{"type":"command","command":"\"$CLAUDE_PROJECT_DIR\"/admin-ui/hooks/log_event.sh","timeout":5}]}]
  }
}
```
- `.warroom/` 與 `admin-ui/data/` 各放自己的 `.gitignore`（不改根目錄 `.gitignore`）。

## 8. 可選：你在一般終端機實測真實 payload
```bash
cd /private/tmp/claude-501/-Users-oscar-Desktop-qa-agent-os/e546a92d-a01b-4d2f-a27a-b8437fa25c68/scratchpad/hooktest && QAOS_TRACK=1 claude -p 'Step 1: use the Write tool to create hello.txt containing hi. Step 2: use the Agent tool with subagent_type "probe-writer", description "probe subagent", telling it to Write hello2.txt containing yo. Step 3: reply DONE.' --settings ./settings.json --agents "$(cat .claude-agents-probe.json)" --model haiku --permission-mode acceptEdits --allowedTools "Write,Read,Agent,Task" --max-turns 12 && python3 -c "import json;[print(json.loads(l)['_payload'].get('hook_event_name'), sorted(json.loads(l)['_payload'].keys())) for l in open('events.jsonl')]"
```
（只寫 scratchpad，不碰專案。）

## 9. 里程碑
| | 內容 | 驗證方式 |
|---|---|---|
| M1 | 骨架（FastAPI + Vite）、版面（導覽/主區/右側面板）、待辦完整功能（看板、拖曳、歷史、關聯） | `admin-ui/dev.sh` 起來；新增/拖曳/刪除待辦，重新整理仍在 |
| M2 | 產出管理（掃描、搜尋/篩選/排序、預覽、審閱狀態、備註、新產出提示）＋ 報告（建立/編輯/列表/匯出 MD、HTML） | 標記 MEMBER 為已審、加備註後重整仍在；`touch` 一個新 final 檔看到提示 |
| M3 | hook 腳本、事件解析、Pipeline 面板（階段大綱、即時 agent、elapsed、stall、歷史 session 時間軸、run.yaml 整合）、session 過濾；**hook 設定經你確認後寫入** | 用手工假造的 `.warroom/events.jsonl` 呈現正確階段；再以真實 session 驗證。**狀態：程式與假事件驗證完成（2026-09-17），待 hook 設定確認** |
| M4 | 自動化測試框架預留（路由、頁面空狀態、schema/API stub + 註解） | 頁面可開、API 回 501 |

## 9a. M3 實作備註
- 事件檔由 `admin-ui/hooks/log_event.sh` → `log_event.py` 寫入；後端 `services/events.py` 讀（含輪替檔）、`services/runs.py` 讀 run.yaml、`services/pipeline.py` 依 `config/stages.yaml` 合成。
- Validator 辨識：`general-purpose` 子 agent 讀 `~/.claude/projects/<proj>/<session>/subagents/agent-<id>.meta.json` 的 description 含「獨立審查／審查／驗證」→ 對應「獨立驗證」階段（strong）。
- 關聯 run：session 活動區間內 run 的 task history / gate_results / created 筆數計分，最高者為 active run。
- SSE：`/api/pipeline/stream` 每秒比對事件檔與 run.yaml 的 mtime，有變才推完整快照；app shutdown 旗標讓長連線在 uvicorn --reload 時自行結束。
- 已知限制：hook 在 session 啟動時載入，正在跑的 session 要 resume；final 檔用 Bash cp 產生時 hook 抓不到（由產出頁掃描補）。

## 10. 需要你決定的事
1. Session 過濾：A（推薦）/ B / C？
2. 後端 FastAPI（需 pip install 到 `admin-ui/.venv`）還是 stdlib 零依賴？
3. Pipeline 面板以 `run.yaml` 為主、hook 為即時補充（推薦）——可以嗎？
4. 要不要讀 `~/.claude/projects/.../subagents/*.meta.json` 來把 Validator 從 general-purpose 中辨識出來（唯讀、專案外）？
5. `stages.yaml` 草稿的階段切法（intake / spec-analysis / test-design / validation / approval / integration / final-export / summary）是否符合你的心智模型？
