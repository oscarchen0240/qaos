# Workflows

| ID | 檔案 | 觸發 | 主要 Agents | 終態產物 |
|---|---|---|---|---|
| WF-A `spec-to-testcase` | `workflows/spec-to-testcase.yaml` | Human：「用 SPEC-X vN 產生 Test Case」 | Spec Analyst → Test Designer ⇄ Test Validator | Registry ACTIVE TC（經 Approval） |
| WF-B `spec-to-bug` | `workflows/spec-to-bug.yaml` | Human：提供 actual behavior + evidence | (Spec Analyst) → Bug Analyst ⇄ Bug Validator | Bug OPEN（經 Approval） |
| WF-C `spec-change-impact` | `workflows/spec-change-impact.yaml` | Human：匯入 SPEC-X vN+1 | Change Impact Analyst → Test Designer(change) ⇄ Test Validator → CIA(compare) | 新版 TC ACTIVE、舊版 SUPERSEDED（經 Approval） |
| WF-D `manual-test-to-regression` | `workflows/manual-test-to-regression.yaml` | Human：提交人工測試紀錄 | Test Designer(manual) ⇄ Test Validator → Regression Curator | TC ACTIVE + Suite membership（經 Approval） |
| WF-E `regression-generation` | `workflows/regression-generation.yaml` | Human：「重建 Full/CI/Hotfix suite」或 WF-C 完成後 | Regression Curator | Suite 新版本 ACTIVE（經 Approval） |

每個 Workflow YAML 都定義：`input`、`initial_state`、`agents`、`artifacts`、`gates`、`transitions`、`failure_handling`、`human_approval`、`output`、`final_state`（Brief §19）。

| （WF-B 之後）`bug-lifecycle` | `docs/workflows/bug-lifecycle.md` | RD 於共用表單回覆修復 | Human（QA）：resolve → verify（Execution+Evidence）→ close | Bug CLOSED（= done） |
| WF-R `testcase-revision` | `workflows/testcase-revision.yaml` | Human：`qaos tc revise TC-x --reason`（退回重審 / 修訂正式 TC） | Test Designer(change) ⇄ Validator | 新版 ACTIVE、舊版 SUPERSEDED（經 Approval） |
| — 退役 | `qaos tc retire TC-x --rationale` | Human | — | RETIRED（自動留 RETIRE_TESTCASE approval） |
| — 手動新增 | `qaos manual new …` → WF-D | Human 寫紀錄 | Test Designer(manual) ⇄ Validator → Curator | TC ACTIVE + Suite |
