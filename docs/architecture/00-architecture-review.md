# 00 — Architecture Review（Phase 1 總覽）

> **狀態：已核准（2026-09-13，APPROVE ARCHITECTURE，全部採用建議選項 → ADR-004）。Phase 2 進行中。** 本文件是 Phase 1 的入口，整理 Brief 的矛盾、缺失決策、18 項 Deliverables 的位置，以及 Definition of Done 核對。
> 只有在你明確回覆 **`APPROVE ARCHITECTURE`**（並回答 `docs/decisions/NEEDS_DECISION.md`）之後，才進入 Phase 2。

## 1. Brief 分析：需求矛盾與不一致

| # | Brief 位置 | 矛盾 / 不一致 | Review 處置 |
|---|---|---|---|
| C1 | §20 Workflow A / §35 MVP-1 vs §27 TC State Machine | Workflow 是 `Validator PASS → Registry`，State Machine 卻有 `PENDING_APPROVAL → APPROVED`；§26 只說「加入 Full Regression」需批准，沒說「進 Registry」 | 拆成兩層：VALIDATED 版本寫入 `versions/`，ACTIVE 需 `ACTIVATE_TESTCASE`（可批次）。→ NEEDS_DECISION-02 |
| C2 | §11 TC 欄位 `regression_status` / `ci_status` vs §15 / Principle 6 | TC 上存 suite 狀態 = 與 Suite Membership 雙寫 | TC 只存 eligibility，membership 唯一事實來源。→ ADR-003、NEEDS_DECISION-05 |
| C3 | §8 Test Type 含 Regression / Smoke / Hotfix，同時 §8 Test Suite 也是這三種 | 同一概念出現在兩個維度 | 從 test_type 移除。→ NEEDS_DECISION-05 |
| C4 | §8 Test Level 含 Manual | Manual 是執行方式，不是層級；與 UI/E2E 不互斥 | 改 `execution_mode`。→ NEEDS_DECISION-04 |
| C5 | §6 Action Registry 有 `EXECUTE_TEST` vs §36 Phase 5 才做 automated execution；§7 無任何 Agent 被授權執行 | Action 存在但無人可用 | 標記 `reserved`，Phase 1–4 不授權 |
| C6 | §6 Action Registry vs §7.6 / §25 Bug Validation Gate 要求 duplicate 檢查 | 無 `READ_BUG` action，Bug Validator 無法查 duplicate；同理缺 `READ_ARTIFACT`、`READ_APPROVAL` | 新增 3 個 read action |
| C7 | §6 vs §26 | 「誰把 approved TC 寫進 Registry / Suite」沒有 action；若給 Agent 就違反 §26 | 新增 system-only actions（COMMIT_TO_REGISTRY、UPDATE_SUITE_MEMBERSHIP、COMMIT_BUG…），無 Agent 可用，只由 ApprovalDecision 觸發 |
| C8 | §7.7 Change Impact Analyst 流程含「Generate New / Updated TC + Compare」 vs §22 Workflow C 由 Test Designer 產生新 TC | 誰產生、誰比較不明 | CIA 兩階段（impact / compare），TC 產生一律 Test Designer；新增 `VersionComparisonReport` artifact（§28 漏列） |
| C9 | §7.1 Supervisor「檢查 Quality Gate」 vs §4「Agent 做錯事卻沒人知道」 | Gate 若由 LLM 判斷，Gate 本身不可信 | Structural Gate 由 deterministic Runtime；Semantic Gate 由獨立 Validator artifact。→ ADR-002 |
| C10 | §25 Test Design Gate vs Test Validation Gate | 6 項檢查重疊，且未說 Test Design Gate 由誰執行 | Design Gate = Runtime structural + Designer self-check；正式判定在 Validation Gate |
| C11 | §7.4「直到 PASS 或 Human Override」 | 無迭代上限 | `max_validation_iterations` 預設 3。→ NEEDS_DECISION-06 |
| C12 | §13 `bugs/<functional-area>/` vs §29 `specs/<product>/<area>/` | bug 路徑少 product 層 | 統一 `bugs/<product>/<area>/` |
| C13 | §28 有 SpecAnalysis 與 RequirementModel 兩個 artifact vs §7.2 只說「Spec Analysis Artifact」 | 一個還是兩個 | 兩個：RequirementModel 是被 TC 長期引用的持久 entity；SpecAnalysis 是一次性分析 |
| C14 | §7.9 Manual → Regression 直接進 Full Regression vs §11 Registry 是所有 TC 的來源 | 人工 TC 進 Registry 與進 Suite 是兩件事 | WF-D 兩段 approval：ACTIVATE_TESTCASE 再 UPDATE_SUITE_MEMBERSHIP |
| C15 | §3 九個 Agent vs §4「不追求 Agent 數量」 | Manual Test Integrator 沒有獨立決策邊界 | 併入 Test Designer mode=manual。→ NEEDS_DECISION-03 |
| C16 | §7.3 指名 `test-case-designer` skill 的 Phase 2.5 Human Review Gate vs §7.4 Generator→Validator 迴圈 | 兩種審核機制並存 | Validator 為必經；Human analysis review 為可開關 checkpoint。→ NEEDS_DECISION-13 |

## 2. Brief 缺少的架構決策（已補）

| 缺項 | 補在哪 |
|---|---|
| TestExecution / Evidence 的 schema 與不可變性（Bug 追溯鏈需要） | `02-data-model.md` §3.5、`schemas/execution/` |
| ApprovalRequest / ApprovalDecision 的結構、override 語意 | `09-human-approval-flow.md`、`schemas/approval/` |
| WorkflowRun / Task 的狀態機與 audit log | `03-state-machines.md` §4、`schemas/workflow/` |
| Artifact 的狀態機（VALID 才可被下游消費） | `03-state-machines.md` §5 |
| Requirement 的狀態機與 ambiguity 分級處理 | `03-state-machines.md` §7、`04-quality-gates.md` |
| ID 配發權責（Agent 不得自編） | `02-data-model.md` §5 |
| Agent 寫入路徑邊界（Claude Code hook 可執行） | `05-permission-matrix.md` §4 |
| 同源偏誤（Validator 與 Generator 同模型）緩解 | `08-roadmap.md` Risks、Validator contract forbidden |
| Bug 進入 OPEN 之後由誰驅動 | NEEDS_DECISION-11 |
| 執行環境（Claude Code native vs SDK） | NEEDS_DECISION-01 |
| Spec 匯入格式 | NEEDS_DECISION-08 |
| 既有資料遷移 | NEEDS_DECISION-10 |

## 3. Deliverables 索引（Brief §34 十八項）

| # | Deliverable | 位置 |
|---|---|---|
| 1 | System Architecture | `01-system-architecture.md` |
| 2 | Agent Responsibility Matrix | `../agent-contracts/README.md` §1 |
| 3 | Agent Contract Matrix | `../agent-contracts/README.md` §2 + `agents/*.yaml` |
| 4 | Data Model | `02-data-model.md` + `schemas/` (35 schemas) |
| 5 | Entity Relationship Diagram | `02-data-model.md` §2 |
| 6 | Workflow Diagrams | `../workflows/*.md` (5) |
| 7 | State Machines | `03-state-machines.md` (TC / Bug / ChangeImpact / Run / Artifact / Suite / Requirement / Approval) |
| 8 | Quality Gate Matrix | `04-quality-gates.md` |
| 9 | Permission / Allowed Action Matrix | `05-permission-matrix.md` + `permissions/action-registry.yaml` |
| 10 | Repository Structure | `06-repository-structure.md` |
| 11 | Skill vs Agent Decision | `07-skill-evaluation.md` §1 |
| 12 | Existing Skill Evaluation | `07-skill-evaluation.md` §2 |
| 13 | MVP Scope | `08-roadmap.md` |
| 14 | Phase 2 Roadmap | `08-roadmap.md` |
| 15 | Phase 3 Roadmap | `08-roadmap.md` |
| 16 | Risks | `08-roadmap.md` |
| 17 | Architectural Trade-offs | `08-roadmap.md` |
| 18 | Open Decisions | `../decisions/NEEDS_DECISION.md` (13 項) |

## 4. Mermaid 索引（Brief §33 十二張）

| # | 圖 | 位置 |
|---|---|---|
| 1 | System Architecture | `01-system-architecture.md` §2 |
| 2 | Agent Dependency Graph | `01-system-architecture.md` §4 |
| 3 | SPEC → Test Case | `../workflows/spec-to-testcase.md` |
| 4 | SPEC → Bug | `../workflows/spec-to-bug.md` |
| 5 | SPEC Change Impact | `../workflows/spec-change-impact.md` |
| 6 | Manual Test → Regression | `../workflows/manual-test-to-regression.md` |
| 7 | Regression Generation | `../workflows/regression-generation.md` |
| 8 | Entity Relationship Diagram | `02-data-model.md` §2 |
| 9 | Test Case State Machine | `03-state-machines.md` §1 |
| 10 | Bug State Machine | `03-state-machines.md` §2 |
| 11 | Supervisor Task Graph | `01-system-architecture.md` §5 |
| 12 | Human Approval Flow | `09-human-approval-flow.md` |
| + | Change Impact / Workflow Run 狀態機 | `03-state-machines.md` §3–4 |

## 5. Definition of Done 核對（Brief §39）

| 條件 | 狀態 | 證明 |
|---|---|---|
| 所有 Agent 都有 Input Schema | ✓ | `schemas/artifact/*-input.schema.json` ×7 + `schemas/workflow/supervisor-input.schema.json` |
| 所有 Agent 都有 Output Schema | ✓ | 12 個 artifact payload schema，`envelope.schema.json` 以 `artifact_type` 分派 |
| 所有 Agent 都有 Allowed Actions | ✓ | `agents/*.yaml`；`tools/validate_phase1.py` 驗證 ⊆ registry、不含 system-only |
| 所有 Agent 都有 Dependencies | ✓ | `agents/*.yaml` `dependencies.{skills,agents,runtime}` |
| 所有 Agent 都有 Quality Gate | ✓ | `agents/*.yaml` `quality_gate` ↔ `04-quality-gates.md` |
| 所有 Workflow 都有 Input / Agent / Artifact / Gate / Transition / Human Approval / Output | ✓ | `workflows/*.yaml` 通過 `workflow-definition.schema.json`（10 個必填段落） |
| 所有核心 Entity 都有 Schema / Version / Lifecycle / Relationships | ✓ | `schemas/` 每個 entity 有 `version` + `status` + `history[]`；ERD 定義關聯；`03-state-machines.md` 定義生命週期 |
| 需求不明確處未自行猜測 | ✓ | 13 項 `[NEEDS_DECISION]`，每項含 Option A/B、Recommended、Risk |
| 沒有開始 Coding 系統 | ✓ | 唯一程式碼是 `tools/validate_phase1.py`（僅驗證 Phase 1 產物自洽，不是系統） |

自我驗證指令：
```bash
python3 tools/validate_phase1.py
```

## 6. 需要你決定的事（摘要）

完整內容在 `docs/decisions/NEEDS_DECISION.md`。若全部採用 Recommended，回覆：

> APPROVE ARCHITECTURE（採用全部建議選項）

或逐項回覆，例如 `02:A, 07:B, 其餘採建議`。

| # | 主題 | 建議 |
|---|---|---|
| 01 | 執行環境 | Claude Code native + `tools/qaos` CLI |
| 02 | 新 TC 進 Registry 要不要 Human Approval | 要，批次核准 |
| 03 | Manual Test Integrator 獨立與否 | 併入 Test Designer mode=manual |
| 04 | Test Level 含 manual？ | 否，改 execution_mode |
| 05 | regression/smoke/hotfix 當 test_type？ | 否，只在 Suite |
| 06 | 最大驗證迭代 | 3 |
| 07 | ID 含 product？ | 否，靠 areas.yaml 唯一 |
| 08 | Spec 來源 | 手動放 Markdown |
| 09 | `spec-dd` / `spec-verify` 來源 | 找不到，自寫 |
| 10 | 既有資料遷移 | 只匯 1 個 feature 當 fixture |
| 11 | Bug OPEN 後驅動 | Human 手動，Phase 5 再同步 Jira |
| 12 | 內容語言 | 繁體中文，key 英文 |
| 13 | test-case-designer 的分析審核 gate | 可開關 checkpoint，預設交 Validator |

## 7. Phase 2 進入條件
1. 收到 `APPROVE ARCHITECTURE`
2. NEEDS_DECISION 全部有答案（ADR 化）
3. `ll0v0ll/test-case-designer` License 確認
