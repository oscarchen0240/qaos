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
- **⚠️ 2026-09-15 更新**：Recommended（Fork + Adapt）已由 [ADR-005](ADR-005-phase2-corrections-to-adr004.md) 修正為「不 clone/fork，僅作方法論參考」，理由見該檔。

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
- **⚠️ 2026-09-15 更新**：Recommended（Option C，T2 之後的 `REVIEW_TEST_ANALYSIS`）已由 [ADR-005](ADR-005-phase2-corrections-to-adr004.md) 修正——Phase 2 實測 10 份 spec，這個機制從未被觸發過；實際自然演化出的 checkpoint 是「T1 完成、G-SPEC PASS 後，匯出 RequirementModel 給 Human 審閱，才進 T2」，卡在 Requirement 層級、且是必經（非可開關）。Phase 3 落地時改採此模式，新 approval type 為 `REVIEW_REQUIREMENTS`。

### NEEDS_DECISION-14 · `spec-to-bug` 需要「優化建議 / Enhancement」票種，不只是「Bug」
- **問題**：2026-09-15 實測發現：`bug-validation-report.schema.json` 的 `checks` 物件（含 `violates_spec`）在 `result=PASS` 時被 `gates.py` 強制要求全部為 `true`（見 `if not all(p["checks"].values())`）。但實務上會遇到「證據屬實、Validator 也同意內容正確，但這件事本身**不是**違反 spec 的 defect，只是可用性/UX 建議」的情況（案例：`SPEC-UPDATEPACK-001` 的錢包展開清單 bug 排查過程中，順帶發現 Arcade 站台 TWD 稽核設定有兩筆完全無法區分的紀錄——這是 UX 問題不是資料錯誤）。目前 Bug 實體的 schema（`requirement_id` 必填、`expected_result_spec_reference` 必填）與 gate 邏輯整個是繞著「違反 spec」這個前提設計，無法乾淨地讓這類票種走到 `OPEN` 狀態；當時的因應是讓 run 卡在 `RUNNING/T2`（`RUN-20260915-002`），最後由 Human 決定 `run cancel`，改用 RD 內容輸出到卻沒有列入 Bug repository。
- **Option A**：新增獨立的 `EnhancementDraft` artifact 類型與對應 `spec-to-enhancement` workflow（比照 `spec-to-bug` 但不要求 `violates_spec`，改用 `usability_rationale` 類欄位），Gate 只檢查證據與 severity 合理性，不檢查是否違反 spec。
- **Option B**：擴充既有 `BugValidationResult` enum 加入 `SUGGESTION`（或擴充 `checks` 讓 `violates_spec` 在特定 `result` 值下可以是 `false` 而不觸發 `PASS 但 checks 有 false` 的結構性錯誤），沿用同一套 BugDraft/Bug schema，只是狀態機多一條分支（例如 `VALIDATED_AS_SUGGESTION`），最終落地時標記 `bug.type: defect|enhancement`。
- **Option C**：不進 QAOS 追蹤，優化建議一律只走 RD 面文件（`bug-report` skill 產出的 HTML/MD + 可 publish 連結），不佔用 Bug repository，QAOS 完全不介入。2026-09-15 當下臨時採用的做法就是這個，但屬於權宜之計，未落地為架構決策。
- **Recommended**：**A**。Enhancement 與 Bug 的驗證重點本質不同（Bug 驗證「是否真的違反 spec」；Enhancement 驗證「觀察是否屬實、建議是否合理」），硬塞進同一個 schema 會持續製造 gate 摩擦；獨立 artifact 類型也讓兩者的 Approval 流程可以分開（Enhancement 或許不需要 `OPEN_BUG` 這麼重的 Human Approval）。
- **Risk if undecided**：每次遇到「屬實但非違規」的觀察，都要嘛被迫塞進 Bug（severity/violates_spec 造假）、要嘛卡在 run 裡等 Human 手動 cancel，兩者都不是乾淨的長期解法；Phase 3 若要讓 agent-bug-analyst 自主判斷 bug vs enhancement，現在的 schema 邊界必須先定案。
