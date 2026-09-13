# 05 — Permission / Allowed Action Matrix

> 機器可讀版本：`permissions/action-registry.yaml` 與 `agents/*.yaml`。Runtime 在 dispatch 前以此檢查；越權呼叫一律拒絕並寫入 audit log（不 silently ignore）。

## 1. Action Registry（擴充後）

| Action | 類別 | Phase | 說明 / 相對 Brief 的變更 |
|---|---|---|---|
| READ_SPEC | read | 1 | |
| READ_SPEC_VERSION | read | 1 | |
| READ_REQUIREMENT | read | 1 | |
| READ_TESTCASE | read | 1 | 含 registry 與 versions |
| READ_TEST_SUITE | read | 1 | |
| READ_EXECUTION | read | 1 | |
| READ_EVIDENCE | read | 1 | |
| READ_BUG | read | 1 | **新增**：Bug Validator 做 duplicate 檢查必需 |
| READ_ARTIFACT | read | 1 | **新增**：讀取上游 VALID artifact（僅限被 dispatch 指定者）；RequirementModel 為跨 run 的持久參考，任何 run 皆可引用 |
| READ_APPROVAL | read | 1 | **新增**：讀取 Human 已決定的 ambiguity / override |
| CREATE_ARTIFACT | write-artifact | 1 | 只能寫入 `artifacts/<own-type>/<run_id>/` |
| UPDATE_DRAFT | write-artifact | 1 | 只能更新自己建立、狀態為 DRAFT/INVALID 的 artifact |
| CREATE_TESTCASE_DRAFT | write-artifact | 1 | |
| CREATE_BUG_DRAFT | write-artifact | 1 | |
| CREATE_SUITE_DRAFT | write-artifact | 1 | |
| VALIDATE_TESTCASE | validate | 1 | 產出 TestValidationReport |
| VALIDATE_BUG | validate | 1 | 產出 BugValidationReport |
| CALCULATE_CHANGE_IMPACT | analyze | 1 | |
| COMPARE_VERSIONS | analyze | 1 | |
| PROPOSE_REGRESSION_UPDATE | propose | 1 | 產出 RegressionProposal |
| REQUEST_HUMAN_APPROVAL | propose | 1 | 產出 ApprovalRequest（只有 Supervisor 與 Runtime 可建立；其他 Agent 透過 artifact 的 `requires_approval` 欄位請求） |
| EXECUTE_TEST | execute | **5 (reserved)** | Phase 1–4 不授權任何 Agent |
| CREATE_WORKFLOW_RUN | orchestrate | 1 | **新增**，Supervisor only |
| DISPATCH_AGENT | orchestrate | 1 | **新增**，Supervisor only |
| EVALUATE_GATE | orchestrate | 1 | **新增**，Runtime（Supervisor 觸發） |
| TRANSITION_STATE | orchestrate | 1 | **新增**，Runtime only |
| CREATE_WORKFLOW_SUMMARY | orchestrate | 1 | **新增**，Supervisor only |
| COMMIT_TO_REGISTRY | system | 1 | **新增**，system-only，需 ApprovalDecision |
| UPDATE_SUITE_MEMBERSHIP | system | 1 | **新增**，system-only，需 ApprovalDecision |
| COMMIT_BUG | system | 1 | **新增**，system-only，需 ApprovalDecision |
| SUPERSEDE_TESTCASE | system | 1 | **新增**，system-only，隨 COMMIT_TO_REGISTRY |
| RECORD_APPROVAL | system | 1 | **新增**，僅 Human 透過 CLI |
| MODIFY_SPEC | forbidden | — | **明列為全域禁止**，Spec 只能由 Human 匯入新版本 |

## 2. Agent × Action 矩陣

`✓` 允許 · `—` 不允許 · `S` system-only（無 Agent 可用） · `H` Human only

| Action | Supervisor | Spec Analyst | Test Designer | Test Validator | Bug Analyst | Bug Validator | Change Impact | Regression Curator |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| READ_SPEC | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| READ_SPEC_VERSION | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| READ_REQUIREMENT | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| READ_TESTCASE | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| READ_TEST_SUITE | ✓ | — | — | — | — | — | ✓ | ✓ |
| READ_EXECUTION | ✓ | — | ✓¹ | — | ✓ | ✓ | — | ✓ |
| READ_EVIDENCE | ✓ | — | — | — | ✓ | ✓ | — | — |
| READ_BUG | ✓ | — | — | — | ✓ | ✓ | ✓ | ✓ |
| READ_ARTIFACT | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| READ_APPROVAL | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| CREATE_ARTIFACT | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| UPDATE_DRAFT | — | ✓ | ✓ | — | ✓ | — | ✓ | ✓ |
| CREATE_TESTCASE_DRAFT | — | — | ✓ | — | — | — | — | — |
| CREATE_BUG_DRAFT | — | — | — | — | ✓ | — | — | — |
| CREATE_SUITE_DRAFT | — | — | — | — | — | — | — | ✓ |
| VALIDATE_TESTCASE | — | — | — | ✓ | — | — | — | — |
| VALIDATE_BUG | — | — | — | — | — | ✓ | — | — |
| CALCULATE_CHANGE_IMPACT | — | — | — | — | — | — | ✓ | — |
| COMPARE_VERSIONS | — | — | — | — | — | — | ✓ | ✓² |
| PROPOSE_REGRESSION_UPDATE | — | — | — | — | — | — | — | ✓ |
| REQUEST_HUMAN_APPROVAL | ✓ | — | — | — | — | — | — | — |
| EXECUTE_TEST | — | — | — | — | — | — | — | — |
| CREATE_WORKFLOW_RUN | ✓ | — | — | — | — | — | — | — |
| DISPATCH_AGENT | ✓ | — | — | — | — | — | — | — |
| EVALUATE_GATE | ✓³ | — | — | — | — | — | — | — |
| TRANSITION_STATE | S | — | — | — | — | — | — | — |
| CREATE_WORKFLOW_SUMMARY | ✓ | — | — | — | — | — | — | — |
| COMMIT_TO_REGISTRY | S | — | — | — | — | — | — | — |
| UPDATE_SUITE_MEMBERSHIP | S | — | — | — | — | — | — | — |
| COMMIT_BUG | S | — | — | — | — | — | — | — |
| SUPERSEDE_TESTCASE | S | — | — | — | — | — | — | — |
| RECORD_APPROVAL | H | — | — | — | — | — | — | — |
| MODIFY_SPEC | — | — | — | — | — | — | — | — |

¹ Test Designer `mode=manual` 讀取人工測試的 Execution 記錄。 ² Regression Curator 比較 Suite 版本差異。 ³ Supervisor 觸發，Runtime 執行。

## 3. Forbidden Actions（每個 Agent Contract 明列）

| Agent | 明列禁止 |
|---|---|
| 全部 | MODIFY_SPEC、寫入 `testcases/registry/`、`testsuites/`、`bugs/` 的正式檔、寫入他人的 artifact 目錄、自行配發正式 ID、讀取其他 Agent 的對話上下文 |
| Spec Analyst | 自動批准 Requirement、將 ambiguity 自行裁定為需求、建立 TestCase |
| Test Designer | 批准 TC、建立 Bug、修改 Full Regression、為 `critical` ambiguity 的 Requirement 設計 TC |
| Test Validator | 修改 TestCaseDraft（只能產 Report）、批准進 Registry |
| Bug Analyst | 判定最終 severity（只能 propose）、關閉 Bug、將推論當 Evidence |
| Bug Validator | 修改 BugDraft、開 Bug（只能 PASS/FAIL） |
| Change Impact Analyst | 覆蓋既有 TC、直接建立 TC Draft（必須經 Test Designer） |
| Regression Curator | 直接修改 Suite、複製 TC 內容進 Suite、將 `execution_mode=manual` 的 TC 放入 CI suite |
| Supervisor | 自行完成 QA 內容工作（設計 TC、寫 Bug）、跳過 Gate、代替 Human 決定 |

## 4. 檔案系統寫入邊界（Claude Code 實作時的 hook 規則）

| Agent | 可寫路徑 |
|---|---|
| Spec Analyst | `artifacts/spec-analysis/<run_id>/`、`artifacts/requirements/<run_id>/` |
| Test Designer | `artifacts/test-design/<run_id>/` |
| Test Validator | `artifacts/validation/<run_id>/` |
| Bug Analyst | `artifacts/bug-analysis/<run_id>/` |
| Bug Validator | `artifacts/validation/<run_id>/` |
| Change Impact Analyst | `artifacts/change-impact/<run_id>/` |
| Regression Curator | `artifacts/regression/<run_id>/` |
| Supervisor | `runs/<run_id>/`、`artifacts/summaries/<run_id>/`、`approvals/`（僅建立 request） |
| Runtime (system) | 全部 |
| Human | `specs/`、`approvals/`（decision）、`executions/`、`evidence/`、`testcases/manual/` |
