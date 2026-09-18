# 測試自動化覆蓋稽核（Runtime + admin-ui）

> 依 [PROMPT-test-automation-coverage-audit.md](PROMPT-test-automation-coverage-audit.md) Phase 0／Phase 5 產出。平台 session 撰寫，範圍：平台與交握；Runtime 只盤點、不改。
> 狀態：`covered`＝有自動化測試在 CI 必跑；`partial`＝部分路徑；`manual_only`＝只有人工／腳本驗過（`tools/manual-runs/`、`admin-ui/fixtures/` 不算 covered）；`none`＝沒有。
> 日期：2026-09-18。git：9e11f98 起。

## 1. 矩陣

### 1a. Runtime（`tools/qaos`，測試在 `tests/`，30 條，CI job `runtime-pytest`）

| 區域 | 狀態 | 風險 | 測試 |
|---|---|---|---|
| spec import／run new／permission guard | covered | high | test_00–02 |
| T1 G-SPEC structural、T2 G-DESIGN traceability | covered | high | test_03、04、31 |
| T3 Validator FAIL 路由回 T2 → PASS materialize | covered | high | test_05 |
| 無核准不改 production、批次核准含 per-item reject | covered | high | test_06、07、41 |
| trace／validate CLI | covered | low | test_08 |
| Evidence／Execution import、無證據不開 bug | covered | high | test_10、11 |
| Bug Analyst → Validator → OPEN_BUG（含人工調整）→ resolve／verify／close | covered | high | test_12、13、16、17、18 |
| Regression gate、change-impact supersede | covered | medium | test_14、15 |
| exploratory 比例 → NEEDS_DECISION → continue、assumption 確認 | covered | high | test_30、32、33、34 |
| structural retry 不吃 semantic 迭代、iteration 上限 | covered | high | test_40 |
| Clarification 生命週期、critical ambiguity 擋 approve、bug index、tc retire／revise、重送不毀損 | covered | medium | test_20–24 |
| `tc-export`（final html/json 產生） | manual_only | medium | 只在 QA session 手動跑 |
| 夾具：session scope 共用一份 tmp root（`tests/conftest.py`） | partial | medium | 測試間共用 Registry／counters，順序相依風險；Runtime session 之後可評估改 function scope，本稽核不動 |

### 1b. admin-ui 後端（`admin-ui/backend`，測試在 `admin-ui/backend/tests/`，31 條，CI job `admin-ui-pytest`）

| 區域 | 狀態 | 風險 | 測試 |
|---|---|---|---|
| `qaos_exec` 預檢：APR 非 PENDING／run 非 WAITING_HUMAN／無草稿 → 409，不寫 handoff、不改 run | covered | high | test_qaos_exec_preflight（3） |
| `qaos_exec` 執行失敗不 append handoff、不 mark_sent | covered | high | test_failed_execution_does_not_append_handoff |
| `qaos_exec` 成功 append handoff：session_id／run_id／action／handoff_kind（resume_agent／notify_only） | covered | high | test_successful_execution…、test_completed_run_handoff_is_notify_only |
| `pipeline._primary` 主狀態（CANCELLED＋live 不是執行中、COMPLETED 凍結時鐘、WAITING_HUMAN 帶 APR） | covered | high | test_pipeline_primary_status（5） |
| `tickets` 指令組裝（approve per-item／rationale、clarification、bug）與 warnings | manual_only | high | 之前只用 smoke script 驗；**下一批要補** |
| `tickets._activation_context` 交叉比對守門（Phase 2 ACTIVE 計數、shadow 文件解析採用清單） | manual_only | high | 用 4 份既有文件人工驗過；**下一批要補**（純函式，易測） |
| `specflow` Phase 判定、DoD 三項、整合／匯出證據 | manual_only | medium | 真實 runs 驗過 |
| `durations` 各節點耗時（READY→RUNNING＝agent 工作） | none | medium | 純函式 `_task_durations`，易測 |
| `pipeline` 車道／related_runs（活著的 run 優先） | manual_only | medium | 曾出過「新 run 被前 8 筆截掉」bug |
| `outputs` 掃描／群組／TC 審閱、`registry.drift_for_final` | manual_only | medium | |
| `autoreports` 產出報告對應 run（依 spec 編號）、簽章重生 | manual_only | medium | 曾出過 BONUSCCY-001/002/003 混在一起 |
| `testruns` 建立快照／記結果／證據／結束產報告／結束後鎖定 | manual_only | medium | 用 API 走過一輪 |
| `reports`／`todos`／`folders` CRUD | manual_only | low | |
| 路由層（FastAPI）HTTP 契約 | none | low | 可用 TestClient 補 smoke |

### 1c. hooks／交握（`admin-ui/hooks`，用 subprocess 跑真實腳本）

| 區域 | 狀態 | 風險 | 測試 |
|---|---|---|---|
| `handoff_relay` Stop：RUNNING＋READY → block，只 consume 這一筆 | covered | high | test_stop_blocks_when_run_running_and_task_ready_and_consumes_only_that_one |
| `handoff_relay` Stop：COMPLETED／notify_only 不 no-op 吞單 | covered | high | test_stop_does_not_swallow_pending_when_run_completed（**原本紅，Phase 2 改 relay 後綠**） |
| `handoff_relay` UserPromptSubmit：顯示 pending；notify_only 顯示後標 notified | covered | high | test_user_prompt_submit_shows_pending_and_marks_notified |
| `handoff_relay` stop_hook_active 不 block；他人 session 不理；壞輸入 exit 0 | covered | high | 3 條 |
| `guard_qaos` approve／clarification／bug 類 → permissionDecision=ask；其他放行 | covered | high | test_guard_qaos（7＋5＋2） |
| `log_event` 事件過濾（只記 final/ 的 Write/Edit）、輪替 | none | low | 純記錄，壞了只影響面板即時性 |

### 1d. 前端（`admin-ui/frontend`）

| 區域 | 狀態 | 風險 | 備註 |
|---|---|---|---|
| 型別檢查 `tsc --noEmit` | manual_only | low | 每次改動手動跑；CI 可選、後加 |
| 核准抽屜（預設全部退回、依建議套用、送出前守門） | manual_only | high | 瀏覽器手動驗；邏輯多在後端 `_activation_context`／`approval_command`，優先補後端測 |
| 測試執行（回合／快捷鍵／證據上傳） | manual_only | medium | |
| Pipeline／Spec 進度／耗時分析／報告／產出 | manual_only | low–medium | 純呈現 |

## 2. Top 15 缺口（依風險）

已補（本批）：1 qaos_exec 預檢 · 2 執行失敗不寫 handoff · 3 成功 handoff 欄位與分類 · 4 relay Stop 只 consume block 那筆 · 5 relay 不吞 COMPLETED · 6 stop_hook_active · 7 guard ask · 8 Pipeline 主狀態 · 9 Runtime tests 進 CI。

待補（下一批，都在後端純函式，function scope 即可）：
10. `tickets.approval_command`：per-item reject＋理由進 rationale、全部退回但 decision=approve 要警告、override 缺 rationale 警告。
11. `tickets._activation_context`／`_recommendation`：shadow 文件三種寫法解析、`needs_review` 判定、Phase 3 run 取消仍算整合完成。
12. `specflow.build`：Phase 2／3 判定、新 run 在跑時整合退回 pending、DoD 三項。
13. `durations._task_durations`：READY→RUNNING 算 agent 工作、approval RUNNING→DONE 算等人、多輪加總。
14. `autoreports.runs_for_group`／`main_run`：依 spec 編號精確對應（BONUSCCY-001/002/003 不混）、主 run 取 Phase 3。
15. `pipeline._related_runs`：活著的 run 永遠在前 8 筆內。

## 3. 結論

- 自動化偏重 **Runtime 業務規則**（Gate、狀態機、核准）與本批新增的 **交握三支**（qaos_exec、relay、guard）。這兩塊是「寫 QAOS 狀態」的高風險路徑，現在都在 CI 必跑。
- 空洞在 **平台的合成邏輯**（tickets 守門、specflow、durations、autoreports 對應）：全是純函式，曾各出過一次真實 bug，但目前只靠人工驗。下一批優先。
- 前端維持手動＋tsc；不做 E2E 農場。

## 4. 測試生命週期（怎麼跑、何時寫）

| 問題 | 答案 |
|---|---|
| 夾具 scope | 平台測試全部 **function**：`admin-ui/backend/tests/conftest.py` 用 `tmp_path` 建假專案根（runs／approvals／.warroom／admin.db），monkeypatch 各服務模組的目錄常數；teardown 由 pytest 回收，不留 `.warroom` 殘渣。Runtime 既有 `tests/conftest.py` 是 session scope，本稽核不動。 |
| hook 怎麼測 | subprocess 跑 `admin-ui/hooks/*.py`，stdin 餵 hook JSON，`CLAUDE_PROJECT_DIR` 指向假根，跟 Claude Code 實際呼叫方式一致。 |
| 何時寫測 | 會寫 QAOS 狀態／handoff／核准／狀態合成 → 同一次改動就補；純 UI 文案／排版 → 穩定後再測。 |
| CI 觸發 | GitLab merge request、push 到 main（`.gitlab-ci.yml`）：`runtime-pytest`、`admin-ui-pytest` 兩個 job，失敗不准 skip；不做 deploy。 |
| 本機怎麼跑 | `python3 -m pytest tests/ -q`；`admin-ui/.venv/bin/python -m pytest admin-ui/backend/tests -q`；一次跑完並更新控制台：`admin-ui/.venv/bin/python admin-ui/scripts/write_ci_status.py --run` |
| 控制台看哪一頁 | 側欄「監控 › 工程 CI」（`/ci`）讀 `admin-ui/data/ci-status.json`；有 `GITLAB_PIPELINE_URL` 就給 GitLab 連結。與「測試執行」（產品 TC）分開。 |
| SDET Agent | **沒有新增**。品質維護走 CI ＋ 人 ＋ 本文件（A5）。 |
