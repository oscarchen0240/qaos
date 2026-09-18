# QAOS 管理介面（admin-ui）

本機運行的指揮台：監看 TC 產生 pipeline、管理 `testcases/final/` 產出、撰寫報告、待辦看板。

- 只讀取專案其他目錄（`testcases/`、`runs/`、`.warroom/`），**不會寫入**。
- 自己的資料只放在 `admin-ui/data/`（SQLite：`admin.db`）。

## 啟動（一個指令）

```bash
admin-ui/dev.sh
```

第一次會自動建立 `admin-ui/.venv` 並 `npm install`。之後：

- 前端 http://127.0.0.1:5180
- 後端 http://127.0.0.1:8780（API 文件 `/api/docs`）

需求：Python 3.11+、Node 18+。

## 目錄

```
admin-ui/
├─ dev.sh              一鍵啟動
├─ backend/            FastAPI（routers/ 路由、services/ 讀檔邏輯（tickets.py 讀單據＋組 bin/qaos 指令）、db.py SQLite schema）
├─ frontend/           React + Vite + TypeScript
├─ config/stages.yaml  pipeline 階段大綱：events / run.yaml / final 檔如何對應到階段、stall 門檻
├─ design-system/      ui-ux-pro-max 產生的設計系統（MASTER.md 下半「採用版」為準：slate 基底、藍色互動色、語意色只給狀態、JetBrains Mono、最小 12px、Phosphor 圖示）
├─ hooks/              Claude Code hook 腳本：log_event（記錄事件）、handoff_relay（交接回 QA session）、guard_qaos（守門）、PROPOSED-settings.local.json（待確認的設定）
├─ scripts/            write_ci_status.py（工程 CI 結果 → data/ci-status.json）
├─ backend/tests/      工程測試（qaos_exec 預檢、handoff_relay、guard_qaos、Pipeline 主狀態）
├─ fixtures/           假事件產生器（make_demo_events.py）
├─ data/               SQLite 與快取（git 忽略）
└─ PLAN.md             第 0 步規劃
```

## 驗證

- 待辦：新增／拖曳／勾選／刪除後重新整理頁面，資料仍在（存在 `data/admin.db`）。
- 產出：同模組的 JSON / HTML 合為一列；點開預覽可逐條把 TC 標 待審／已審／退回（退回可填理由，理由進報告），模組狀態由 TC 彙總；摘要的 high/medium/exploratory/revised 標籤可點擊直接篩選。每 10 秒自動掃描，出現新檔或既有檔被重新產生時會跳提示並標 NEW。
  - **final 已過期**：比對 `testcases/registry/` 的 ACTIVE 版本與 final JSON；registry 有新版／新 TC／退役 TC 但尚未重新匯出時，列表與預覽會標「final 已過期」並列出數量——這是「spec 更新或臨時加測項後，要請 QAOS 重新匯出」的訊號。
  - **資料夾**：勾選模組（整批）或在預覽裡勾選個別 TC → 「加入資料夾」→ 選既有或建新資料夾；「資料夾」分頁可更名、刪除、移出；TC 列顯示所屬資料夾。純管理系統資料。
- 報告：三種來源同一張表（`reports.kind`）——
  - **產出（自動）**：`testcases/final/` 每個模組一出現就自動建一份「產出報告」，系統段落含產出摘要與**工作流程紀錄**（run 狀態、各階段時間／迭代、核准單與決定理由、Gate FAIL、hook 派工）；產出檔、審閱狀態或 run 更新時自動重生，你寫的「結論與備註」不會被蓋掉。
  - **自動化測試（預留）**：M4 的 runner 完成後呼叫 `autoreports.upsert_auto(kind="automation", …)` 就會出現在同一頁。
  - 列表可搜尋（標題／摘要／模組／run）、每頁 20 筆分頁、欄位排序。側欄徽章：報告總數；有尚未寫結論的自動報告時徽章變亮。匯出 MD / HTML 會包含系統段落＋你的結論。
- Pipeline：`run.yaml` 為事實來源、hook 事件補即時 agent 活動；SSE 推送（連不上退回 5 秒輪詢）。
  - **主狀態**（車道標題）由後端合成：`run.status` 優先（已取消／失敗／已完成／等你決定／執行中），其次目前階段，session 健康度只當淡色副標（例如「session 仍連線」）。run 終止後「已執行」時鐘凍結，改顯示「跑了多久後結束」。
  - **下一步**一行：請核准 APR / 請回 CLR / 可能卡住 / Validator FAIL 第 n/max 輪 / Run 已停可忽略 / 產出已可審 / 進行中：階段；一次只顯示第一個命中的。
  - 階段條：gate 完整顯示；run 取消／失敗時，實際開始過的階段標「已取消／失敗」，從未開始的標「未執行」；Designer⇄Validator 迭代顯示「第 n / 3 輪」，達上限用警告色；已決定的核准單淡色「曾開單」。
  - Agent 活動：以 `run.yaml` 的 task history／gate 結果為主，hook 的 SubagentStart/Stop 疊加。
  - final 產出：掃描 `testcases/final/` 對應功能區的檔案（Bash cp 也抓得到），hook Write/Edit 只是輔助。
  - 「即時」一個活著的 run（RUNNING / WAITING_HUMAN）一條車道——同 session 並行的 run 各自一條；手選／追蹤中的 session 額外保留一條。不畫空車道；已取消／完成的請看「歷史 Session」。
  - **Spec 進度**分頁（`GET /api/pipeline/specs`，`backend/services/specflow.py`）：QAOS 的 workflow 只有 T1–T5，交叉整合與匯出 final 不是 run 的 task，而是 QA session 在 run 之後做的。每份 spec 一列匯流圖：Phase 2 run（人扮 agent 腳本）與 Phase 3 run（qaos-test-designer）匯入「交叉整合」再到「匯出 final」。整合與匯出的證據（皆唯讀）：`docs/phase3-shadow-test/<date>-<slug>-shadow-test.md`（內文 **Run** 指出 Phase 3 run；Phase 3 run 在整合後被 `run cancel` 也算完成）、同功能區在 Phase 3 之後的 `testcase-revision` run、`testcases/final/` 檔案時間與 registry 落差。每列標 DoD 三項：整合完成／shadow-test 記錄／final 已產出，缺項用警告色，可只看未完成。Phase 判定也用在即時車道、Runs 清單的「Phase 2 / Phase 3 / 修訂」標籤；階段條的整合、匯出兩節點對 Phase 3 run 用同一份證據，對 Phase 2 run 標未執行。
  - 分頁順序：即時 / Spec 進度 / Runs（紀錄，每個 run.yaml 一列）/ Session（Claude Code session 的生命週期與子 agent，用來分辨兩個 session 各做了什麼）/ 耗時分析。
  - **耗時分析**分頁（`GET /api/pipeline/durations?scope=completed|terminal|all`，`backend/services/durations.py`）：由 run.yaml 的 task history 推算每個節點「可開始→完成」的時間（交叉整合、匯出 final 兩節點取自 Spec 進度的證據，只有 Phase 3 run 計入），給出平均／中位數／最大、最花時間的節點與對應 run，長條分成 agent 工作（READY→RUNNING）、gate（RUNNING→DONE）、等人（核准單開出→決定）；下方是每個 run × 每個節點的分解表（熱度＝佔該 run 的比例，點列開 run 細節）。範圍與統計值選擇存瀏覽器。標題列的「節點耗時」開關會在階段條每個節點下方顯示該節點耗時（設定存瀏覽器）。
  - 用假事件驗證：
  ```bash
  python3 admin-ui/fixtures/make_demo_events.py .warroom
  ```
  會產生 3 個 demo session（進行中／已結束／開發用），面板應顯示 demo-live 為追蹤對象、qaos-test-designer 執行中、階段 5「人工核准」等你決定。清掉：`rm .warroom/events.jsonl`。
- 產出樹（側欄）：「產出」底下是 worktree 式樹——`final/` 列出各模組與其 json/html 檔；每個歸檔資料夾展開是「模組 → TC」。點模組開預覽、點 TC 開預覽並捲到該條（網址帶 `?group=&tc=`，可直接分享／重整不掉）。展開狀態存瀏覽器 localStorage。
- 單據（M5a，**平台不寫 QAOS**）：側欄「單據」三頁讀 `approvals/`、`clarifications/`、`bugs/`（唯讀），徽章＝等你決定的 APR／未結案 CLR（OPEN/ASKED）／未結案 Bug。
  - **核准 APR**：等你決定／已決定；抽屜列出批次 TC 全文，逐條「通過／退回＋理由」，整體 核准／退回／強制通過，NEEDS_DECISION 選項；平台組出 `bin/qaos approve … --per-item TC:reject --rationale "…；退回：TC：理由"`。
  - **釐清 CLR**：待處理／已回答・待套用／已結案；動作依 `workflows/state-machines.yaml` 的 human 轉移：送問 PM／登記回答（回答者、落地方式、spec 版本、逐字回答）／套用／撤回 → `bin/qaos clarification <action> …`。
  - **Bug**：未結案／已結案；改狀態（狀態機允許的目標）／RD 已修復（外部參照）／複測通過（Execution ID）／結案 → `bin/qaos bug <action> …`。
  - 草稿存 `data/admin.db`（`ticket_drafts`），重整不掉；必填缺漏時指令框顯示警告並停用「複製」。流程：填好 → **複製指令** → 貼到 QA session 執行 → 按「已送出」記錄（只記錄，不執行）。QAOS 更新檔案後單據狀態自動反映。M5b（平台直接執行 `bin/qaos`）需先放寬邊界 1。
  - 執行者（`--by`）預設取最近 run 的 `initiated_by`，可用 `PUT /api/tickets/operator` 改。
  - **啟用類核准單的交叉比對守門**（2026-09-18 APR-0125 事故後加）：同 spec 已有 Phase 2 ACTIVE TC 時，抽屜頂端顯示「已有 N 條 Phase 2 ACTIVE，這批有／沒有交叉比對紀錄」（紀錄＝shadow-test 文件點名此 run）；每條 TC 標「同需求 N 條既有」提示（只比需求編號，非語意比對）。第一次打開時**預設全部退回**（理由預填「未採用：Phase 2 既有 TC 已覆蓋」），要採用的再逐條標通過，工具列有「全部通過／全部退回」。沒有比對紀錄卻 0 條退回時，送出前會再跳一次確認；全部退回但整體決定是核准時指令框會警告。清單頁會提示最近 24 小時 QAOS 自動決定的審計單（退役／結案）數量，這類單子不需處理。
    - **需要決定類（NEEDS_DECISION / HUMAN_OVERRIDE 等沒有 batch_items 的單）**：抽屜以「選項」當決定（key 是 approve/reject/override 的直接當整體決定，其他如 continue/retry/cancel 走 `--option`，整體決定固定 approve）；數字卡改讀引用的產物（草稿 TC 數、exploratory 數、未覆蓋需求、第幾輪）；「這張單引用的產物」區塊列出 TestCaseDraft 的每條草稿與假設、TestDesignReport 的假設／未覆蓋需求／技巧統計、驗證報告的問題清單（皆唯讀 `artifacts/`）。
    - **QA session 的分析建議**：讀 `.warroom/recommendations/<APR>.md`（第一行 `suggest: <option key>`，其餘 markdown），抽屜顯示內容、標出建議的選項並提供「採用建議」。沒有檔案時顯示要對 QA session 講的那句話。這是 QA session 把「只有結果沒有分析」補起來的通道，跟 handoff 一樣走 `.warroom/`。
    - **依建議套用**：有 shadow-test 文件時，平台從文件抓「採用哪幾條」（`tickets._recommendation`，只認三種寫法：`--per-item TC-X:approve|reject` 指令、「新增 N 條（TC-…、nnn）」、「保留／採用 TC-…」），橫幅列出建議採用的 TC、引用文件原句，按「依建議套用」＝整體核准＋其餘逐條退回（理由「交叉比對不採用（依 shadow-test 文件）」）；每條 TC 標「建議採用／建議不採用」。抓不到清單時橫幅說明原因，請自己看文件。**前提是 QA session 在核准前就先做交叉比對並寫好文件**（含「最終處置」那行指令）；文件在核准後才寫的話，平台只會看到「沒有比對紀錄」的警告。
  - **M5b 送出到 QAOS**（2026-09-18 Oscar 放寬邊界 1 後啟用）：指令框的「送出到 QAOS」由平台在專案根目錄執行 `bin/qaos …`（`backend/services/qaos_exec.py`）。規則：只接受 tickets.py 組出、以 `bin/qaos` 開頭的指令；同時只跑一條、60 秒逾時；執行前預檢（APR 必須 PENDING 且 run 為 WAITING_HUMAN；CLR／Bug 動作必須是狀態機允許的轉移；必填齊全），不符回 409、不重試。成功後 append 一筆到 `.warroom/handoff.jsonl`，並把結果存 `ticket_executions`；釐清／Bug 動作後順帶跑 `bin/qaos clarification list` / `bin/qaos bug index` 重建 index.md。確認框會列出這次 QAOS 會寫到的路徑。「複製」與「已手動執行」保留為備援。
    - QAOS 會寫的路徑：核准 → `approvals/<APR>.yaml`、`runs/<RUN>/run.yaml`＋`audit.log`、`runs/_audit.log`；啟用 TC 另寫 `testcases/versions/<TC>/v<N>.yaml`、`testcases/registry/<TC>.yaml`；APPLY_CHANGE 寫 `runs/<RUN>/entities/change-impact.yaml`；OPEN_BUG 新建 `bugs/<p>/<a>/BUG-*.yaml`＋`_counters.yaml`；推進後可能新建 `approvals/APR-*.yaml` 或 `artifacts/summaries/`。**不寫 `testcases/final/`**。釐清 → `clarifications/<p>/<a>/<CLR>.yaml`＋`.md`；answer 另更新需求文件與 PENDING 核准單的 `.md/.html`。Bug → `bugs/<p>/<a>/<BUG>.yaml`、`runs/_audit.log`；close 新建一張 `approvals/APR-*.yaml`。
    - 交接給 QA session：`hooks/handoff_relay.sh`（Stop：run 仍 RUNNING 且 current task READY 時回 `decision: block` 讓 QA session 接續，只 append 這一筆 `consumed(resumed)`，其餘 pending 不動（run 已結案的 notify_only 不會被吞）；UserPromptSubmit：把待接續的交接印成上下文，notify_only 顯示過即標 `consumed(notified)`）與 `hooks/guard_qaos.sh`（PreToolUse Bash：agent 要跑 approve / clarification ask|answer|apply|withdraw / bug resolve|verify|close|transition 時回 `permissionDecision: ask`，跳權限確認讓 Oscar 按允許；口頭交辦與平台送出兩個入口都保留，但 agent 不能無人看管地自行核准）。只認 `session_id` 相符的交接，開發 session 不受影響。建議的設定在 `hooks/PROPOSED-settings.local.json`，**經 Oscar 確認後才寫進 `.claude/settings.local.json`**。
    - 已知限制：QA session 已停下等你時，平台核准後不會立刻被喚醒；要等它下一回合結束（Stop）或你在 QA session 送出任何訊息（UserPromptSubmit）。`GET /api/tickets/handoff/recent` 可看交接是否已被消費。
- **測試執行（M7，TestRail 式）**：側欄「工作 › 測試執行」，取代原本的自動化測試 stub（`/automation` 轉到 `/testruns`）。
  - **建立回合**：名稱／環境／build／備註，從產出模組（列出 final JSON 的 TC，可搜尋、全選）或資料夾挑 TC；建立時把 TC 的版本、標題、前置、步驟、預期**快照**進回合，之後 final 重新匯出不影響這輪。找不到的 TC 會略過並提示。
  - **執行畫面**：上方甜甜圈（純 SVG）＋圖例＋進度條；左邊 TC 清單可依結果篩選、搜尋；右邊結果面板：Pass / Fail / Blocked / Skipped / Untested、實際結果、備註、證據上傳（類型對齊 QAOS evidence schema：screenshot / video / log / network / db_query / api_response / other，單檔 25MB，存 `admin-ui/data/evidence/<run>/`）。快捷鍵 P / F / B / S / U 標結果，J / K 上下一條；Pass 後自動跳下一條未測，Fail 停在原地讓你填實際結果與證據。
  - **結束回合**：確認後鎖定結果，自動產一份報告（`reports.kind=automation`，介面標「測試執行」，`source_key=run id`）：結果表、通過率、NG 清單（實際結果、證據、bug run）、逐條結果表；你補結論。刪除回合會連報告與證據檔一起刪。
  - API：`/api/testruns`（list / create / get / patch / delete）、`/{id}/results/{rid}`（PATCH 結果）、`/{id}/results/{rid}/evidence`（POST multipart、DELETE）、`/{id}/evidence/{eid}`（下載）、`/{id}/finish`、`/meta`。資料表 `test_runs` / `test_results`（M4 stub 建的舊表由 `_migrate_testruns` 補欄位）。
  - **NG 送 QAOS 開 bug（M7b，待做）**：對 Fail 的 TC 依 spec-to-bug 必填（spec、TC、實際行為、至少一份證據、環境／build）依序執行 `bin/qaos evidence add` → `execution import --result fail` → `run new spec-to-bug`，之後 Bug Analyst／Validator 在 QA session 跑，OPEN_BUG 核准單出現在「單據 › 核准」。回合設定 `import_all` 預留「Pass 也匯進 QAOS executions」。
- 自動化測試（M4 stub，API 契約仍在 `/api/automation/*`）：頁面可開，顯示預留的資料表（`test_runs` / `test_results`）與 API 契約；`GET /api/automation/runs` 回空清單，其餘寫入類端點回 501。契約與 M7 流程寫在 `backend/routers/automation.py` 開頭註解。
- API：`curl http://127.0.0.1:8780/api/health`；完整文件 http://127.0.0.1:8780/api/docs

## 工程測試（程式有沒有壞，不是產品 TC）

- 改 Runtime（`tools/qaos`）→ 測試在根目錄 `tests/`：`python3 -m pytest tests/ -q`。
- 改交握／`qaos_exec`／hooks／Pipeline 狀態合成 → 測試在 `admin-ui/backend/tests/`（function scope 假專案根，hook 用 subprocess 跑真腳本）：`admin-ui/.venv/bin/python -m pytest admin-ui/backend/tests -q`。同一次改動就補測。
- 純 CSS／文案不強制。CI：`.gitlab-ci.yml` 兩個 job（`runtime-pytest`、`admin-ui-pytest`），merge request 與 push main 觸發。控制台「監控 › 工程 CI」讀 `admin-ui/data/ci-status.json`（本機 `admin-ui/.venv/bin/python admin-ui/scripts/write_ci_status.py --run` 產生；範例 `admin-ui/config/ci-status.example.json`；環境變數 `GITLAB_PIPELINE_URL` 給連結）。盤點與缺口見 `docs/decisions/TEST-AUTOMATION-COVERAGE-AUDIT.md`。

## Claude Code hook（Agent 狀態來源）

- `.claude/settings.local.json` 掛 6 個事件（SessionStart / SessionEnd / Stop / SubagentStart / SubagentStop / PostToolUse(Write|Edit)）到 `admin-ui/hooks/log_event.sh`。
- 腳本只保留：時間、session_id、事件、agent_id / agent_type / subagent_name、tool_name、`testcases/final/` 內的 file_path、reason、cwd、transcript_path、`QAOS_TRACK` 環境變數；不打網路、永遠 exit 0、超過 5MB 輪替（保留 3 份）。
- 管理系統沒開時 hook 照樣只是 append 檔案，對 TC 產出零影響。
- Session 過濾：UI 手選＋自動建議（曾派工 `qaos-test-designer` 的 session 標為建議）；可把開發用 session 設為忽略。啟動時帶 `QAOS_TRACK=1 claude` 會在事件加上 tag。
- 注意：hook 設定在 session 啟動時載入，已在跑的 session 要重啟或 resume 才會開始送事件；在那之前面板仍能從 `runs/*/run.yaml` 顯示階段狀態。

## 測試用環境變數（不碰真實資料）

```bash
QAOS_ADMIN_FINAL_DIR=/path/to/fake/final QAOS_ADMIN_DATA_DIR=/tmp/qaos-admin-data \
  .venv/bin/python -m uvicorn backend.app:app --port 8781
```
另有 `QAOS_ADMIN_RUNS_DIR`、`QAOS_ADMIN_WARROOM_DIR`（M3 使用）。
