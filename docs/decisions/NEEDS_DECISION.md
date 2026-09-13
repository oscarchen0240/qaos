# [NEEDS_DECISION] 清單

> **已核准（2026-09-13）：全部採用 Recommended Option，見 [ADR-004](ADR-004-phase1-decisions-approved.md)。** 本檔保留原始選項供追溯。

---

### NEEDS_DECISION-01 · 執行環境
- **問題**：Runtime（Supervisor 的 deterministic 部分、Gate、State Machine、Permission Guard）用什麼實作？
- **Option A**：Claude Code Native — `.claude/agents/` subagents + `.claude/skills/` + `tools/qaos` Python CLI + hooks。狀態全在檔案。
- **Option B**：Claude Agent SDK 程式（Python/TS），自寫 orchestrator 呼叫 Claude API，自管 state。
- **Recommended**：**A**。Phase 2–4 不需要並行與長駐服務；A 的 audit trail 就是 git；B 留到 Phase 5/6。
- **Risk if undecided**：schemas 與 contracts 可共用，但 `write_paths`、hook 設計、Supervisor 的形態會分岔。

### NEEDS_DECISION-02 · 新 Test Case 進 Registry 是否需逐案 Human Approval
- **問題**：Brief §27 state machine 有 `PENDING_APPROVAL → APPROVED`，但 §20 Workflow A 與 §35 MVP-1 是 `Validator PASS → Registry`，沒有 Human。
- **Option A**：VALIDATED 即 ACTIVE（Validator PASS = 進 Registry），Human 只審 Suite membership。
- **Option B**：VALIDATED 寫入 `versions/`，ACTIVE 需 `ACTIVATE_TESTCASE` approval，**支援批次核准**（一個 request 多個 TC，可逐項 reject）。
- **Recommended**：**B**。符合 Principle 3 與 §27；批次核准避免審批疲勞。
- **Risk if undecided**：State machine 與 Workflow A 的 T4 節點是否存在。

### NEEDS_DECISION-03 · Manual Test Integrator 是否獨立 Agent
- **問題**：其職責（正規化人工紀錄 → Draft + 對映 requirement）沒有獨立決策邊界。
- **Option A**：保留獨立 Agent（9 個）。
- **Option B**：併入 Test Designer `mode=manual`（8 個），Contract 中以 mode 規則限制「不得補充紀錄中不存在的行為」。
- **Recommended**：**B**。少一份 Contract 與 prompt 維護；若日後 manual 來源複雜（多格式匯入）再拆。
- **Risk if undecided**：`agents/` 檔案數與 WF-D 的 T1 定義。

### NEEDS_DECISION-04 · Test Level 是否包含 `manual`
- **問題**：Brief §8 把 Manual 當 Level，但 Manual 是執行方式；一個手動 UI 測試會同時是 `ui_e2e` 與 `manual`。
- **Option A**：照 Brief，`test_level` 含 `manual`。
- **Option B**：移除，改 `execution_mode: manual | automated | hybrid`（與 `automation_status` 區分：mode 是設計意圖，status 是現況）。
- **Recommended**：**B**。
- **Risk if undecided**：CI eligibility 規則（G-REG 的「CI suite 不得含 manual」）無法用 level 表達。

### NEEDS_DECISION-05 · `regression / smoke / hotfix` 是否為 Test Type
- **問題**：Brief §8 同時把它們列為 Test Type 與 Test Suite；一個 TC 的 `test_type=regression` 與「在 Full Regression suite 中」語意重複且可能不一致。
- **Option A**：照 Brief 保留在 `test_types`。
- **Option B**：從 `test_types` 移除，只由 Suite Membership 表達（TC 只留 `ci_eligible`、`hotfix_eligible`、`critical_path` 等 eligibility 屬性；`regression_status`/`ci_status` 改為 derived）。
- **Recommended**：**B**（Principle 6 的直接推論）。
- **Risk if undecided**：`testcase-version.schema.json` 的 enum；既有 `test-cases/*/index.yaml` 匯入時的欄位對映。

### NEEDS_DECISION-06 · Generator → Validator 最大迭代次數
- **問題**：Brief 說「直到 PASS 或 Human Override」，未給上限。
- **Option A**：3 次（預設）。
- **Option B**：5 次。
- **Recommended**：**A**；超過 3 次通常代表 Spec ambiguity 或 Designer 系統性誤解，該由 Human 介入。
- **Risk if undecided**：workflow yaml 的 `max_validation_iterations`；成本上限。

### NEEDS_DECISION-07 · ID 是否含 Product 前綴
- **問題**：Brief 範例 `TC-AUTH-001` 只有 functional area；但 §13 bug 依 Product / Functional Area 分類，`specs/<product>/` 也有 product 層。多 product 時 `AUTH` 會撞名。
- **Option A**：`TC-<AREA>-<seq>`，`<AREA>` 在全域 `areas.yaml` 唯一（跨 product 不得重名，例如 `OWAUTH`、`ADMAUTH`）。
- **Option B**：`TC-<PRODUCT>-<AREA>-<seq>`。
- **Recommended**：**A**（ID 短、符合 Brief 範例；靠 areas.yaml 唯一性保證），除非你確定有 ≥2 個 product 共用相同 area 名稱。
- **Risk if undecided**：`schemas/common/defs.schema.json` 的所有 ID pattern。

### NEEDS_DECISION-08 · Spec 來源與匯入格式
- **問題**：Spec 從哪來（Confluence / Jira / Google Doc / Markdown）？誰負責匯入？
- **Option A**：Human 手動放 Markdown 到 `specs/`，Runtime 計算 hash。
- **Option B**：Phase 5 加 importer（Confluence API → Markdown）。
- **Recommended**：**A** for Phase 2–4，B 排入 Phase 5。
- **Risk if undecided**：`spec.schema.json` 的 `source_uri` 語意；MVP-1 無法開始。

### NEEDS_DECISION-09 · Brief 指名的外部 Skills 來源
- **問題**：`test-case-designer` 已確認為 `ll0v0ll/test-case-designer`（已評估，結論 Fork + Adapt）。`spec-dd`、`spec-verify` 仍找不到同名 Skill。
- **Option A**：你提供 `spec-dd` / `spec-verify` 的確切 URL，我補做評估。
- **Option B**：接受目前結論：`spec-analysis`、`test-validation` 自寫；SDD 類與 code-verify 類不採用。
- **Recommended**：**B**，除非你有特定來源。
- **Risk if undecided**：Phase 3 skill 工作量估計。
- **附帶**：`ll0v0ll/test-case-designer` README 未標 License；fork 前需向作者確認或改為「重寫但註明方法論出處」。

### NEEDS_DECISION-10 · 既有資料是否遷移
- **問題**：`../test-cases/claim-bonus-event-reward/`（test-case-gen 產出）與 `../bug-reports/`（9 個 mcp-admin bug）是否匯入 QAOS。
- **Option A**：Phase 2 作為 import fixture 匯入（`source=import`，需要先建對應 SPEC 與 Requirement，否則違反 Principle 5）。
- **Option B**：不匯入，QAOS 從新 SPEC 開始。
- **Recommended**：**A 但只匯入 1 個 feature 作為 Phase 2 fixture**（驗證 import 路徑），其餘等 Phase 4。
- **Risk if undecided**：Phase 2 fixture 來源。

### NEEDS_DECISION-11 · Bug 進 OPEN 後是否同步外部工單系統
- **問題**：`OPEN → IN_PROGRESS → RESOLVED` 由誰驅動？
- **Option A**：Phase 2–4 全由 Human 用 `qaos bug transition` 手動更新。
- **Option B**：Phase 5 與 Jira 雙向同步（`external_ref`）。
- **Recommended**：A now，B later。
- **Risk if undecided**：Bug state machine 後半段的 trigger 定義。

### NEEDS_DECISION-12 · Artifact / Report 語言
- **問題**：欄位 key 是英文（schema），內容用什麼語言？
- **Option A**：內容繁體中文（與既有 test-cases / bug-reports 一致），key 英文。
- **Option B**：全英文。
- **Recommended**：**A**。
- **Risk if undecided**：Skill prompt 的語言指示；Validator 對照 Spec 原文語言。

### NEEDS_DECISION-13 · `test-case-designer` 的 Phase 2.5 Human Review Gate 如何映射
- **問題**：原 skill 強制「Test Analysis Document 先經使用者審核批准，才生成案例」。QAOS 的 subagent 無法互動，且 QAOS 已有獨立 Test Validator。
- **Option A**：**Validator 承接**：Designer 一次產出 TestDesignReport（=分析文件）+ TestCaseDraft；G-DESIGN structural 檢查後直接交 Test Validator；Human 只在 ACTIVATE_TESTCASE 時看到分析摘要。
- **Option B**：**保留 Human checkpoint**：WF-A 拆成 T2a（Designer 只產 TestDesignReport.analysis）→ ApprovalRequest(`REVIEW_TEST_ANALYSIS`) → T2b（產 TestCaseDraft）。多一個 approval type 與 workflow node。
- **Option C**：B 但 checkpoint 可由 workflow input 的 `analysis_review: required|skip` 開關（預設 skip，高風險 spec 時開）。
- **Recommended**：**C**。保留原 skill 「分析先於生成」的價值，但不讓每次都卡 Human；Validator 仍是必經的機械防線。
- **Risk if undecided**：WF-A 的 task 數、`ApprovalType` enum 是否要加 `REVIEW_TEST_ANALYSIS`、Designer contract 是否拆兩階段。
