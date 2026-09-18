# Prompt：把 QAOS + 控制台導入「測試生命週期」

> 給 Claude Code。角色：兩個系統的測試架構師（Runtime + admin-ui）。  
> 來源收斂：覆蓋缺口、交握風險、fixture scope、輕量 GitLab CI、控制台加「CI Pipeline」區、**不**另建觀測平台、**不**照抄 GitHub Actions skill 的全套閘門。  
> 執行前先讀本檔全文與 `docs/decisions/MODEL-ROUTING-POLICY.md`。預設 **Sonnet**；只有改架構／CI 與 Agent 邊界衝突時才升 Opus。

本檔分兩段：**A. 決策（已定，不要再發明）** → **B. 分階段實作（請依序做）**。

---

## A. 已鎖定的決策（Oscar × 架構師）

### A1. 兩個「測試」不要混

| 名稱 | 測什麼 | 活在哪 | 誰看 |
|---|---|---|---|
| **工程 CI**（本 prompt 要導入） | `tools/qaos`、`admin-ui` **程式**有沒有壞 | GitLab CI + 控制台「CI Pipeline」區 | 開發／SDET 職責 |
| **產品 Test Runs**（已有頁） | 產出的 **業務 TC** 人工／之後自動執行 | `admin-ui` 測試執行 | QA 執行產品案例 |

禁止把 pytest 結果寫進業務 `executions/` 假裝是產品測試；禁止為 CI 另做第三個系統。

### A2. 測試生命週期（scope）

夾具存活範圍（pytest fixture scope）必須刻意選：

| Scope | 本專案用法 |
|---|---|
| **function（預設）** | 臨時專案根、`run.yaml`、`.warroom/handoff.jsonl`、假 session。**工程測以這個為主。** |
| class / module | 只給「讀很大、測中不改」的東西（例如只讀 schemas） |
| session | 整輪共用一次；本專案**先不要** session 共用會被 append 的 jsonl／Registry |

規則：

- 夾具裡**禁止**放 assert（失敗要指向測試名稱）。
- teardown 必須清掉 tmp；不可留 `.warroom` 殘渣。
- 路徑必須唯一（`tmp_path`），以便之後平行也不撞。
- 不為順序相依寫測；必要時可加 `pytest-randomly`（非第一批必做）。

**何時寫測（迭代）：**

- 會寫 QAOS 狀態／handoff／核准／狀態合成 → **同一次改動就補測**
- 純 UI 文案／排版 → 穩定後再測
- 里程碑 → 另開對話做 review＋補 high 風險洞，**不等整個平台完工才第一次測**

### A3. CI／CD

- **要輕量 CI，不要完整 CD。** 觸發：GitLab `merge_request` + `push` 到 `main`。
- YAML 寫 **`.gitlab-ci.yml`**，禁止新增 `.github/workflows/`（遠端是公司 GitLab，不是 GitHub）。
- 可參考 addyosmani skill 的**原則**（PR 必過閘、失敗不准 skip、機密不進庫）；**不要**抄：Vercel preview、Prisma+Postgres、每 PR 必跑 Playwright、bundle size、npm audit 擋合併。
- 最小 job：`pytest tests/ -q`；有 `admin-ui/backend/tests` 後加第二 job。前端 lint/tsc **可選、後加**。
- 觀測：GitLab Pipeline UI + 控制台新區域；**不**新建獨立測試中台。

### A4. 控制台「CI Pipeline」區域

在 admin-ui **加一頁或監看底下一個分頁**（名稱建議「工程 CI」或「CI Pipeline」），與現有「測試執行」（產品 TC）分開。

顯示（第一版能靜態／讀檔即可，GitLab API 可第二版）：

- 最近一次工程 CI：pass／fail／running、時間、commit sha
- job 列表：Runtime pytest、admin-ui pytest（有了再顯示）
- 連到 GitLab pipeline URL（設定檔或 env `GITLAB_PIPELINE_URL`）
- 可選：把 CI 產的 `ci-status.json`（或 junit）提交／artifact 同步到本機給控制台讀——**不要**為了漂亮去打 GitHub API

若尚無 GitLab remote：頁面顯示「尚未接遠端 CI」，並能展示**本機最後一次 pytest 結果檔**（例如 `admin-ui/data/last-pytest.json` 由開發者／hook 寫入）。不要因為沒 remote 就做不出頁面骨架。

### A5. 不要新增 SDET Agent（本階段）

**禁止**在 Supervisor 底下新增第九個 Role「SDET Agent」來跑這條品質維護 workflow。理由寫死如下（實作時若 Oscar 沒說 `OVERRIDE: add SDET agent`，就不要改 `agents/*.yaml`）：

1. Supervisor 編排的是 **產品 QA 產物**（Spec→TC→Bug→Suite），契約已定 8 Role + Runtime。SDET 守的是 **本 repo 的工程品質**（pytest、GitLab CI、夾具），不是 G-TVAL／ACTIVATE_TESTCASE。
2. 產品側「CI 回歸套件」已是 **Regression Curator**（責任矩陣第 13 項）。再加 SDET Agent 會和它搶「CI」這個詞，且沒有獨立業務 Artifact。
3. Phase 1–4 明確：不多 Agent、不自主規劃。品質維護應是 **CI 閘門 + 人（Oscar）+ 可選 skill 文件**，不是新的 dispatch 節點。
4. 若未來要 Agent 化：應是獨立軌道 `engineering-quality`（input：diff／CI log；output：CoverageGapReport／PytestPatch），**不**掛在 QA Supervisor 的 `spec-to-testcase` 圖上；且需新 schema、Gate、Human 核准「改測試／改 CI」——現在不做。

本階段允許：在 `docs/` 或 `admin-ui/README.md` 加一節「工程品質怎麼跑」；可新增 **skill 草稿** `skills/engineering-quality/SKILL.md`（給人類／Claude Code 對話用，不是 `.claude/agents` 新 role）。

### A6. 第一批必鎖的高風險測項（有缺口就補）

不測每個函式。下列 **high** 必須進入測試生命週期（function-scoped 沙盒）：

1. `qaos_exec` 預檢：APR 非 PENDING → 409、不寫 handoff、不改 run
2. 執行失敗 → 不 append handoff
3. 執行成功 → append `kind=handoff` 且欄位含 session_id／run_id／action
4. `handoff_relay` Stop：`RUNNING` + current task `READY` → stdout `decision: block`；只 consume **這一筆**
5. `handoff_relay` Stop：run `COMPLETED`／`notify_only` → **禁止** `consumed/no-op` 吃掉其餘 pending
6. `handoff_relay` `stop_hook_active` → 不 block
7. `guard_qaos`：approve／clarification／bug 類 Bash → `permissionDecision: ask`
8. Pipeline 主狀態：run `CANCELLED` + session live → 主標不是「進行中」（若該欄位已存在就測；尚未實作則先測純函式／後端合成，並在報告標「待 Pipeline UX」）
9. Runtime：維持並確認現有 `tests/` 在 CI 必跑（iteration 上限、clarification、bug 狀態機等已有的不要弄丟）

handoff 分類 `resume_agent` vs `notify_only`：若程式尚未改，**測試先寫期望行為**（COMPLETED 不得 no-op consume）；實作 relay 時讓測試綠。不要為了讓舊行為過測而把「吞單」測成正確。

---

## B. 請依序執行的工作

工作目錄：`~/Desktop/qa-agent-os`。預設用繁中文件。Commit 請依「一個意圖一個 commit」（盤點／夾具／測項／CI／控制台頁 可分開）。**不要** `git push` 除非 Oscar 要求。

### Phase 0 — 盤點（可改碼前先產出）

沿用原盤點方法，寫到 `docs/decisions/TEST-AUTOMATION-COVERAGE-AUDIT.md`：

- 矩陣：Runtime、admin-ui 後端、hooks／交握、前端
- 狀態：`covered` / `partial` / `manual_only` / `none`
- 風險：high / medium / low
- Top 15
- 結論：自動化偏重哪、空洞在哪

**手動腳本 `tools/manual-runs/`、`admin-ui/fixtures/` 不算 covered。**

掃完後 **繼續 Phase 1**，不要停在只讀（與舊版 prompt 不同：Oscar 已要求導入生命週期）。

### Phase 1 — 工程測試骨架（生命週期落地）

建立（若已存在則對齊，勿重複疊床）：

```
admin-ui/backend/tests/
  conftest.py          # tmp 專案根、假 run.yaml、handoff.jsonl、stdin hook payload
  test_qaos_exec_preflight.py
  test_handoff_relay.py
  test_guard_qaos.py
  test_pipeline_primary_status.py   # 有可測的合成函式才寫；沒有則 skip 並在 audit 註記
```

`conftest.py` 要求：

- function scope 的 `qaos_root`（`tmp_path`）
- 可塞最小 `runs/<id>/run.yaml`（status／current_task_id／tasks）
- teardown 不留檔
- hook 測試用 `python3 admin-ui/hooks/handoff_relay.py` + stdin JSON，設 `CLAUDE_PROJECT_DIR` 指向 tmp root

在 `admin-ui/README.md` 加「工程測試」三行：改 Runtime → `tests/`；改交握／qaos_exec／hooks → `backend/tests`；純 CSS 不強制。

### Phase 2 — 讓 A6 的測項紅變綠

實作 **最小程式修改** 讓高風險測試成立，尤其：

- `admin-ui/hooks/handoff_relay.py`：Stop 只 consume 真正 block 的 handoff；COMPLETED 等不得 no-op 吞其餘 pending（與先前交握結論一致）

不要趁機做 Model Router、新 Agent、E2E 農場。

跑：

```bash
pytest tests/ -q
pytest admin-ui/backend/tests/ -q
```

### Phase 3 — GitLab CI

新增 `.gitlab-ci.yml`：

- `python:3.11`（或專案現用版本）
- job `runtime-pytest`：`pytest tests/ -q`
- job `admin-ui-pytest`：`pytest admin-ui/backend/tests/ -q`（需同環境能 import 的 hooks／backend；不要依賴本機 `.venv` 路徑寫死）
- 不設 deploy job
- 註解說明：遠端為 GitLab；品質閘原則見本檔 A3

可選 `admin-ui/frontend` 的 `npm test` **不要**當第一版必過。

### Phase 4 — 控制台 CI Pipeline 區域

- 側欄監看組加入口，**不要**取代「測試執行」
- 第一版：讀 `admin-ui/data/ci-status.json`（schema 自定：status、jobs[]、sha、updated_at、web_url）
- 提供範例 `ci-status.example.json`
- 無檔／無 URL 時 EmptyState 說明怎麼接 GitLab
- 頁面文案寫明：這是 **工程 CI**，不是產品 TC 回合

可選：pytest 結束寫 status 的小 script（`admin-ui/scripts/write_ci_status.py`），給本機或 CI artifact 用。

### Phase 5 — 文件收斂

更新：

- `docs/decisions/TEST-AUTOMATION-COVERAGE-AUDIT.md`：標哪些已從 none → covered
- 本檔或 audit 加「測試生命週期」一節：scope、何時寫測、CI 觸發、控制台看哪一頁
- `docs/architecture/08-roadmap.md` **不要**把工程 CI 寫成 Phase 5 的 `EXECUTE_TEST`（那是產品執行）。最多加一句：工程 pytest／GitLab CI 屬開發衛生，與 MVP-5 產品自動化分開。

### 不要做

- 新增 `agents/sdet.yaml` 或 Supervisor workflow「軟體品質維護」
- GitHub Actions、Vercel、Playwright 必過、Dependabot 設定檔（除非 Oscar 點名 GitLab 對等物）
- 為可視化再建獨立服務
- 放寬 Stop hook 見任何 pending 就 block
- ScheduleWakeup／輪詢自動 approve
- `git push`、改 git config

---

## C. 完成時回報 Oscar

1. Audit 路徑與 Top 缺口是否已補進 A6  
2. 新增／修改的測試檔與 pytest 結果  
3. relay 行為是否已改（COMPLETED 不吞單）  
4. `.gitlab-ci.yml` job 列表  
5. 控制台 CI 頁路徑與怎麼看到狀態  
6. 明確一句：**沒有新增 SDET Agent**；品質維護走 CI + 人 + 本 prompt／skill  

對話摘要 ≤15 行。
