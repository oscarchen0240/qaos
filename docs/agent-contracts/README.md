# Agent Contracts — Responsibility Matrix & Contract Matrix

> 機器可讀的完整 Contract 在 `agents/<slug>.yaml`（通過 `schemas/agent/agent-contract.schema.json`）。本文是人可讀的彙整。

## 1. Agent Responsibility Matrix

`R` = Responsible（產出者） · `V` = Validates · `C` = Consumes · `A` = Approves（僅 Human） · `O` = Orchestrates

| 工作項（Brief §1） | Supervisor | Spec Analyst | Test Designer | Test Validator | Bug Analyst | Bug Validator | Change Impact | Regression Curator | Human |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| 1 閱讀與分析 SPEC | O | R | C | C | C | C | C | | |
| 2 建立 Requirement / AC | O | R | C | C | C | C | C | | A (ambiguity) |
| 3 從 SPEC 產生 Test Case | O | | R | | | | | | |
| 4 驗證 Test Case 符合 SPEC | O | | C | R/V | | | | | A (override) |
| 5 依 SPEC + Evidence 找 Bug | O | | | | R | | | | |
| 6 結構化 Bug Report | O | | | | R | V | | | A (open) |
| 7 SPEC 變更 Change Impact | O | (C) | C | | | | R | C | |
| 8 建立新版 Test Case | O | | R (mode=change) | V | | | C | | |
| 9 比較新舊 Test Case | O | | | | | | R (compare) | | |
| 10 詢問是否更新正式 TC | O (request) | | | | | | | | A |
| 11 維護 Full Regression | O | | | | | | | R | A |
| 12 從 Full Regression 產生 Hotfix Suite | O | | | | | | C | R | A |
| 13 維護 CI/CD Regression | O | | | | | | | R | A |
| 14 人工測試納入 Regression | O | | R (mode=manual) | V | | | | R | A |
| 15 所有 TC 追溯到 SPEC | Runtime enforces | R | R | V | | | | V | |
| 16 所有 Bug 追溯到 SPEC/REQ/TC/EXE/EVD | Runtime enforces | | | | R | V | | | |

## 2. Agent Contract Matrix

| Agent | Input (schema) | Output (schema) | Allowed Actions（摘要） | Dependencies (skills) | Consumes | Produces | Gate | Failure Handling | Human Approval |
|---|---|---|---|---|---|---|---|---|---|
| **Supervisor** | `workflow/supervisor-input` | `artifact/workflow-summary` | READ_* 全部、CREATE_ARTIFACT、REQUEST_HUMAN_APPROVAL、CREATE_WORKFLOW_RUN、DISPATCH_AGENT、EVALUATE_GATE、CREATE_WORKFLOW_SUMMARY | runtime | HumanTask、所有 VALID artifact | WorkflowRun、Task、ApprovalRequest、WorkflowSummary | enforces all | unknown task → NEEDS_DECISION；iteration 超限 → HUMAN_OVERRIDE；越權 → run FAILED | NEEDS_DECISION、HUMAN_OVERRIDE |
| **Spec Analyst** | `artifact/spec-analyst-input` | `spec-analysis`、`requirement-model` | READ_SPEC、READ_SPEC_VERSION、READ_REQUIREMENT、READ_ARTIFACT、READ_APPROVAL、CREATE_ARTIFACT、UPDATE_DRAFT | spec-analysis、traceability | SpecVersion、prev RequirementModel、ambiguity decisions | SpecAnalysis、RequirementModel | G-SPEC | hash mismatch → stop；gate fail ≤2 | RESOLVE_AMBIGUITY（條件） |
| **Test Designer** | `artifact/test-designer-input` | `test-design-report`、`testcase-draft` | + READ_TESTCASE、READ_EXECUTION(manual)、CREATE_TESTCASE_DRAFT | test-case-design、traceability | RequirementModel / ChangeImpactReport / ManualTestRecord、FAIL report | TestDesignReport、TestCaseDraft | G-DESIGN → G-TVAL | 依 issues 修訂；cannot map → Human | —（下游 ACTIVATE_TESTCASE） |
| **Test Validator** | `artifact/test-validator-input` | `test-validation-report` | READ_SPEC/VERSION/REQ/TC/ARTIFACT/APPROVAL、CREATE_ARTIFACT、VALIDATE_TESTCASE | test-validation、traceability | SpecVersion、RequirementModel、TestCaseDraft、coverage matrix | TestValidationReport | G-TVAL | 無 spec → FAIL missing_reference | — |
| **Bug Analyst** | `artifact/bug-analyst-input` | `bug-draft` | READ_*（含 EXECUTION/EVIDENCE/BUG）、CREATE_ARTIFACT、UPDATE_DRAFT、CREATE_BUG_DRAFT | bug-analysis、bug-report(render)、traceability | RequirementModel、Execution、Evidence、TC version | BugDraft | G-BVAL(structural) | 無 evidence → stop | — |
| **Bug Validator** | `artifact/bug-validator-input` | `bug-validation-report` | READ_*（含 EVIDENCE/BUG）、CREATE_ARTIFACT、VALIDATE_BUG | bug-validation、traceability | SpecVersion、RequirementModel、BugDraft、Evidence、bugs/ | BugValidationReport | G-BVAL | hash mismatch → blocker；ambiguity → AMBIGUITY | — |
| **Change Impact Analyst** | `artifact/change-impact-input` | `change-impact-report`、`version-comparison-report` | READ_*（含 SUITE/BUG）、CREATE_ARTIFACT、UPDATE_DRAFT、CALCULATE_CHANGE_IMPACT、COMPARE_VERSIONS | change-impact-analysis、traceability | 2× SpecVersion、2× RequirementModel、ACTIVE TC | ChangeImpactReport、VersionComparisonReport | G-IMPACT、G-COMPARE | 不完整 → 補齊 | —（下游 APPLY_CHANGE） |
| **Regression Curator** | `artifact/regression-curator-input` | `regression-proposal` | READ_*（含 SUITE/EXECUTION/BUG）、CREATE_ARTIFACT、UPDATE_DRAFT、CREATE_SUITE_DRAFT、COMPARE_VERSIONS、PROPOSE_REGRESSION_UPDATE | regression-management、traceability | Registry ACTIVE + metadata、current suites、ChangeImpactReport | RegressionProposal | G-REG | 移除不合規 membership 重提 | —（下游 UPDATE_SUITE_MEMBERSHIP） |

## 3. 每個 Agent 的三個核心要素（Brief §5）

| Agent | Input Schema | Output Schema | Allowed Actions 數 |
|---|---|---|---|
| Supervisor | ✓ | ✓ | 16 |
| Spec Analyst | ✓ | ✓ ✓ | 7 |
| Test Designer | ✓ | ✓ ✓ | 10 |
| Test Validator | ✓ | ✓ | 8 |
| Bug Analyst | ✓ | ✓ | 12 |
| Bug Validator | ✓ | ✓ | 11 |
| Change Impact Analyst | ✓ | ✓ ✓ | 12 |
| Regression Curator | ✓ | ✓ | 13 |

驗證方式：`python3 tools/validate_phase1.py`（檢查 contract schema、allowed ⊆ registry、不含 system-only、forbidden ∩ allowed = ∅、引用的 schema 檔存在）。
