# 07 — Skill vs Agent 決策 & 既有 Skill 評估

## 1. Skill vs Agent 原則（Review 後）

**Skill = 可重用能力 / 方法論，沒有決策權、沒有狀態、不寫正式資料。**
**Agent = 角色 + 責任 + 決策邊界 + Allowed Actions，透過 Contract 被 Runtime 約束。**

判斷準則：一個東西若需要 `allowed_actions` 才能存在，它是 Agent；若可以被兩個以上 Agent 呼叫且行為不變，它是 Skill。

### 最終 Skill 清單（相對 Brief §30 的調整）

| Skill | 使用者 Agent | 狀態 | 調整說明 |
|---|---|---|---|
| `spec-analysis` | Spec Analyst | Rewrite | 需輸出 RequirementModel schema，無現成 skill |
| `test-case-design` | Test Designer | **Fork + Adapt `ll0v0ll/test-case-designer`**（見 §2.1 候選 T） | 方法論、分層、RTM、風險密度直接沿用；輸出層改為 QAOS `TestCaseDraft` + `TestDesignReport` schema，Human review gate 改由 Test Validator 承接 |
| `test-validation` | Test Validator | Rewrite | 市面上無「驗證 TC 是否符合 SPEC」的 skill |
| `bug-analysis` | Bug Analyst | Rewrite | 從本機 `bug-report` skill 吸收欄位 |
| `bug-report` | Bug Analyst（渲染） | **Wrap**（本機既有） | 保留其 Title/Detail 格式作為 Bug 的 **human-facing render**，不是 schema |
| `bug-validation` | Bug Validator | Rewrite | **新增**：Brief 未列，但 Bug Validator 需要獨立方法論（evidence 檢核、duplicate 檢索） |
| `change-impact-analysis` | Change Impact Analyst | Rewrite | |
| `regression-management` | Regression Curator | Rewrite（參考 qa-skills `test-suite-curation`） | |
| `traceability` | 全部 | Rewrite（工具型：`qaos trace`） | 實作為 CLI 而非 prompt |
| `schema-tools` | Runtime | **新增** | JSON Schema 驗證、ID 配發、state transition；純程式 |

**Brief §30 列的 `bug-report` 與 `bug-analysis` 保留分開**：前者是輸出格式（render），後者是分析方法論。

## 2. 既有 Skill 評估

### 評估方法
搜尋範圍：GitHub、skills.sh、qaskills.sh、claudemarketplaces.com、SkillsMP、本機 `~/.claude/skills` 與已安裝 plugins。評估日期：2026-09-13。

> ⚠️ **[NEEDS_DECISION-09]** `test-case-designer` 已由你指定為 https://github.com/ll0v0ll/test-case-designer（候選 T，已評估）。`spec-dd`、`spec-verify` 在公開來源仍 **找不到同名 Skill**；以下用最接近的候選評估，若有確切來源請提供。

### 2.1 候選總表

| # | 候選 | 來源 | 對應 Brief 名稱 | Architecture Fit | Quality | Maintainability | Overlap | Customization 難度 | Reusability | Claude Code 相容 | **結論** |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **T** | **`ll0v0ll/test-case-designer`** | github.com/ll0v0ll/test-case-designer（你指定的來源） | **= `test-case-designer`** | **高**：「分析先於生成」+ 強制 Review Gate（Phase 2.5）+ RTM + 風險驅動密度 + 6 層技術（Scenario / EP+BVA / Decision Table / AllPairs / State / Error Guessing）+ 明文「Do not assume undefined requirements」，與 Brief §12、§25 幾乎一一對應 | 高（流程嚴謹、有 sample、有 technique-reference.md、allpairs.py 可執行） | 中（1★、單人維護；**README 未標 License**，fork 前須確認） | 與 A 重疊（A 的 per-feature 累積 index 概念可補 T 沒有的「累積」面向）；與 C/D 的技術內容重疊但 T 已整合 | **中**：需改 4 處 — (1) 輸出 Markdown 10 欄表 → QAOS schema；(2) 自編 `TC-001` → `TC-DRAFT-<ulid>`；(3) Phase 2.5 的互動式 Human 審核 → subagent 環境下改為「autonomous mode」，把疑問寫入 `open_questions` / `assumptions`，審核由 Test Validator 承接（或保留為可選 Human checkpoint，見 NEEDS_DECISION-13）；(4) 欄位對映 | 高 | ✓ 原生 `.claude/skills` 格式，autonomous / interactive 雙模式 | **Fork + Adapt → 成為 `test-case-design` skill 的核心**。A 提供累積 index 概念，C 的 `test-oracle-writer`、`negative-test-designer` 作為 references 補充 |
| A | `test-case-gen`（本機） | `~/.claude/skills/test-case-gen` | — | 中：有 YAML index + report 概念、per-feature 累積、`source_ref` 溯源 | 中高（明確 workflow、防重複、假設外顯） | 高（單檔、自有） | 高（與 Test Designer 直接重疊） | 低 | 中 | ✓ 原生 | **部分吸收**：per-feature 累積、`source_ref`、「不為數量湊案例」規則併入 `test-case-design`；骨架改用 T |
| B | `bug-report`（本機） | anthropic-skills plugin | — | 低（純格式模板，無 schema、無 evidence 要求） | 低 | 高 | 中 | 低 | 低 | ✓ | **Wrap**：作為 Bug human-facing render 模板（Title / Detail / API / Request / Response），schema 由 QAOS 定義 |
| C | `45ck/verification-test-design-skills`（16 個 skills） | github.com/45ck/verification-test-design-skills | 最接近 `test-case-designer` 的「方法論 pack」 | 高：BVA / EP / Decision Table / State Transition / Negative / Pairwise / Test Oracle 各自獨立 | 中（4 stars、6 commits，成熟度低，但結構清楚） | 中（外部、更新不確定） | 與 A 互補（A 是 workflow，C 是技術） | 中（command-driven，需改為被 Agent 內部呼叫） | 高（每個技術獨立） | ✓ `.claude/skills` 格式 | **降為補充參考**：T 已涵蓋 EP/BVA/DT/State；只取 `negative-test-designer`、`test-oracle-writer` 兩個放入 `references/`（T 缺 negative 專章與 oracle 撰寫指引） |
| D | `qaskills istqb-test-design-techniques` | qaskills.sh（PramodDutta/qaskills, MIT） | 同上候選 | 中高：ISTQB 技術對齊 Brief §12 | 中高（quality score 82） | 中（CLI 安裝、npm 生態） | 與 C 高度重疊 | 中 | 中 | ✓（CLI 安裝到 `.claude/skills`） | **參考不安裝**：作為 `test-case-design` 方法論 checklist 的對照，避免兩套相似技術 skill |
| E | `petrkindlmann/qa-skills`（50 skills, MIT, 121★） | github | 可能對應「QA Engineering / Systems QA」 | 部分：`test-case-management`（traceability）、`test-suite-curation`（regression pruning）、`ai-bug-triage`、`bug-reproduction`、`risk-based-testing` | 高（有 evals/、skills_index.json） | 高 | 中 | 中 | 高 | ✓ | **選擇性參考**：`test-suite-curation` → `regression-management` 的 CI eligibility 演算法參考；`risk-based-testing` → risk 分級定義；`bug-reproduction` → Bug Analyst 的 minimal repro 步驟。**不整體安裝**（50 個 skill 會污染 skill 觸發） |
| F | `omkamal/pypict-claude-skill` | github | — | 低中：Pairwise 組合，適用參數多的功能 | 中 | 中（依賴 pypict Python） | 低 | 中 | 中 | ✓ plugin | **Phase 3 再評估**：作為 `test-case-design` 的 optional technique |
| G | Spec-Driven Development 類（SpillwaveSolutions/sdd-skill、genkovich/sdd、FredAntB/Spec-Driven-Development、revagomes/spec-skill） | github | 可能對應 `spec-dd` | **低**：這些是「用 spec 驅動寫程式」的開發流程 skill（requirements.md → design.md → tasks.md → code），不是「從 SPEC 導出 QA Requirement Model」 | 中高 | 中 | 低 | 高（目的不同） | 低 | ✓ | **不採用**。QAOS 的 Spec Analyst 需要的是 requirement extraction + ambiguity detection + traceability，與 SDD 的 code-generation 導向不同。可借用其「requirements.md 結構化格式」做 RequirementModel 的人可讀 render |
| H | `spec-verify` 類（Claude Academy verification skills、mcpmarket verify skill、connect_kit spec-verification） | 多來源 | 可能對應 `spec-verify` | 低中：驗證「程式碼是否符合 spec」，QAOS 需要驗證「Test Case 是否符合 spec」 | 中 | 低（多為文章/範例，非可安裝 skill） | 低 | 高 | 低 | 部分 | **不採用**；`test-validation` 自行重寫，但借用其「逐條對照 spec → 產出 violation list」的報告結構 |
| I | Casely | casely.digital | — | 中：atomic markdown cases、TestRail/Xray 匯出 | 中 | 低（商業、非開源） | 中 | 高 | 低 | ? | **不採用**；Phase 5 若需匯出 TestRail 再看 |

### 2.2 決策摘要

| Brief 指名 | 決策 |
|---|---|
| `test-case-designer` | = `ll0v0ll/test-case-designer`。**Fork + Adapt 為 `test-case-design` skill 核心**；補 A 的累積概念與 C 的兩個 references；輸出層改 QAOS schema。License 待確認。 |
| `spec-dd` | 找不到同名；SDD 類 skill 目的不符，**不採用**。 |
| `spec-verify` | 找不到同名；驗證程式碼非驗證 TC，**不採用**，`test-validation` 自寫。 |
| QA Engineering / Systems QA | 以 `petrkindlmann/qa-skills` 為代表，**選擇性參考三個 skill 的內容，不安裝**。 |


### 2.2a `ll0v0ll/test-case-designer` → QAOS 欄位對映

| test-case-designer | QAOS `TestCaseDraft` / `TestDesignReport` | 備註 |
|---|---|---|
| `ID` TC-001（自編、全域連號） | `draft_id: TC-DRAFT-<ulid>`；正式 ID 由 Runtime 配發 | Principle 8 / ID 規則 |
| `Technique` Scenario / Equivalence / Boundary / Decision Table / Orthogonal / Workflow / Error Guessing | `design_techniques[]`: scenario / equivalence_partitioning / boundary_value / decision_table / pairwise / state_transition / error_guessing | enum 已涵蓋 |
| `Test Level` UI / API / DB / Logic（可多個） | `test_level`（單一）：UI→`ui_e2e`、API→`api`、DB→`integration`、Logic→`unit` 或 `component`；多個時取最外層並在 `description` 註記 | Brief §8 一個 TC 一個 level |
| `Test Scenario` | `title` | |
| `Preconditions` | `preconditions[]` | |
| `Steps` 內嵌編號 | `steps[]: {n, action}` | |
| `Expected Result` | `expected_result` + **必須補** `expected_result_spec_reference` | T 沒有 spec reference，這是 QAOS 新增的硬性要求 |
| `Priority` P1/P2/P3 | `priority`: P1→`high`（critical 由 risk=high ∧ P1 判定）、P2→`medium`、P3→`low` | |
| `Smoke ✓` | `critical_path: true`（TC 屬性），**不是** suite membership | ADR-003；Smoke suite 由 Regression Curator 依 critical_path 提案 |
| `Requirement Ref` REQ-001（來源無 ID 時自動產生） | `requirement_ids[]` **必須指向 RequirementModel 中既有的 REQ**；不得自動產生 | Principle 5；REQ 只能由 Spec Analyst 建立 |
| Test Analysis Document（Module Overview / Scope / Risk / Coverage Targets / per-layer analysis / Error Guessing / RTM） | `TestDesignReport.payload`：`coverage_matrix`（=RTM）、`technique_summary`、`self_check`、`assumptions`、`uncovered_with_reason`；per-layer 分析表放入 `design_rationale` 或 report 附錄欄位（Phase 3 schema 可擴充 `analysis_sections[]`） | |
| Risk 🔴🟡🟢 + P1/P2/P3 密度規則 | Requirement.risk（由 Spec Analyst 給）→ Designer 依同一密度規則 | 規則沿用：高風險 ≥3 P1 ≥2 P2 |
| Phase 2.5 Review Gate（Human 互動審核） | 見 NEEDS_DECISION-13 | |
| `allpairs.py` | 保留於 `skills/test-case-design/scripts/`，Designer subagent 可執行（需 `allpairspy`） | Phase 3 決定是否納入 Runtime 依賴 |

### 2.3 安裝策略（Brief §32）
- Phase 1：**不安裝任何外部 skill**。
- Phase 2：建立 `skills/` 目錄；**先向 ll0v0ll 確認 License**，再以 git subtree fork `test-case-designer` 進 `skills/vendor/`；C 的兩個 skill 同法；A 本機複製。
- Phase 3：完成 `test-case-design` 等自寫 skill，才安裝到 `.claude/skills/`。
- 任何 skill 進入 `.claude/skills/` 前必須通過：(1) 輸出符合 QAOS schema (2) 不直接寫正式目錄 (3) 有至少一個 eval case。

### 來源
- https://github.com/ll0v0ll/test-case-designer （你指定的 `test-case-designer`）
- https://github.com/45ck/verification-test-design-skills
- https://qaskills.sh/skills/thetestingacademy/istqb-test-design-techniques
- https://github.com/PramodDutta/qaskills
- https://github.com/petrkindlmann/qa-skills
- https://github.com/omkamal/pypict-claude-skill
- https://github.com/SpillwaveSolutions/sdd-skill 、https://github.com/genkovich/sdd 、https://github.com/FredAntB/Spec-Driven-Development 、https://github.com/revagomes/spec-skill
- https://claudemarketplaces.com/skills/category/testing
