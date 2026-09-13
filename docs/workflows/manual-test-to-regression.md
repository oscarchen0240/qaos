# WF-D — Manual Test → Regression（Mermaid #6）

```mermaid
flowchart TD
    IN(["Input: testcases/manual/<record>.yaml<br/>(步驟、觀察、環境、執行者、spec hint)"]) --> T1
    subgraph T1["Task 1 · Test Designer (mode=manual)"]
        TD[正規化為 TestCaseDraft<br/>對映 requirement_ids / AC<br/>補 preconditions / test_data / design_technique<br/>source = manual_integration<br/>產 TestDesignReport（含 mapping confidence）]
    end
    T1 --> G1{G-DESIGN<br/>requirement_ids ≥1?}
    G1 -->|無法對映| H1[[Human: 指定 requirement 或 觸發 WF-A 補 Spec Analysis]]
    H1 --> T1
    G1 -->|PASS| T2
    subgraph T2["Task 2 · Test Validator"]
        TV[驗證 + duplicate 檢查（對 Registry 既有 ACTIVE TC）]
    end
    T2 --> G2{G-TVAL}
    G2 -->|DUPLICATE| H2[[Human: 合併或放棄]]
    G2 -->|FAIL ≤3| T1
    G2 -->|PASS| V[TC VALIDATED] --> AR1[ApprovalRequest ACTIVATE_TESTCASE]
    AR1 --> H3[[Human]] -->|approve| ACT[TC ACTIVE]
    ACT --> T3
    subgraph T3["Task 3 · Regression Curator"]
        RC[評估 risk / value / stability / ci_eligible<br/>產 RegressionProposal: full_regression 必, ci_regression 建議]
    end
    T3 --> G3{G-REG} -->|FAIL| T3
    G3 -->|PASS| AR2[ApprovalRequest UPDATE_SUITE_MEMBERSHIP] --> H4[[Human]]
    H4 -->|approve| C[Runtime UPDATE_SUITE_MEMBERSHIP<br/>Suite 新版本 ACTIVE]
    H4 -->|reject| S
    C --> S[WorkflowSummary] --> END([COMPLETED])
```

| 項目 | 定義 |
|---|---|
| Input | `testcases/manual/<record_id>.yaml`（Human 寫入；schema：`manual-test-record`） |
| Initial State | 記錄存在；TC 不存在 |
| Agents | Test Designer(mode=manual)、Test Validator、Regression Curator |
| Artifacts | TestCaseDraft、TestDesignReport、TestValidationReport、RegressionProposal、ApprovalRequest ×2、WorkflowSummary |
| Gates | G-DESIGN → G-TVAL → G-APPROVAL → G-REG → G-APPROVAL |
| Failure Handling | 無法對映 requirement → 停止並詢問 Human（不得假設） |
| Human Approval | ACTIVATE_TESTCASE、UPDATE_SUITE_MEMBERSHIP（**兩段分開**：進 Registry ≠ 進 Regression） |
| Output | TC ACTIVE + Full Regression membership（+ CI 建議） |
| Final State | COMPLETED |
