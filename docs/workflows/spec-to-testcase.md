# WF-A — SPEC → Test Case（Mermaid #3）

```mermaid
flowchart TD
    IN([Input: spec_id@spec_version, scope?]) --> T1
    subgraph T1["Task 1 · Spec Analyst"]
        SA[讀 SpecVersion<br/>產 SpecAnalysis + RequirementModel]
    end
    T1 --> G1{G-SPEC}
    G1 -->|FAIL ≤2| T1
    G1 -->|FAIL >2| H1[[Human: NEEDS_DECISION]]
    G1 -->|PASS| AMB{有 critical<br/>ambiguity?}
    AMB -->|是| H2[[Human: RESOLVE_AMBIGUITY]] --> T1
    AMB -->|否| REQ[(Requirements ACTIVE<br/>artifacts/requirements/spec_id/vN)]
    REQ --> T2
    subgraph T2["Task 2 · Test Designer (mode=spec)"]
        TD[輸入: RequirementModel + 既有 ACTIVE TC 同 area<br/>產 TestDesignReport + TestCaseDraft]
    end
    T2 --> G2{G-DESIGN<br/>structural + self-check}
    G2 -->|FAIL| T2
    G2 -->|PASS| T3
    subgraph T3["Task 3 · Test Validator"]
        TV[輸入: SpecVersion + RequirementModel + TestCaseDraft<br/>產 TestValidationReport]
    end
    T3 --> G3{G-TVAL}
    G3 -->|FAIL, iter ≤ 3| T2
    G3 -->|FAIL, iter > 3| H3[[Human: HUMAN_OVERRIDE]]
    H3 -->|override| V
    H3 -->|reject| END2([Run FAILED])
    G3 -->|PASS| V[TC → VALIDATED<br/>寫入 testcases/versions/]
    V --> AR[ApprovalRequest<br/>ACTIVATE_TESTCASE（批次）]
    AR --> H4[[Human]]
    H4 -->|approve| C[Runtime COMMIT_TO_REGISTRY<br/>TC → ACTIVE]
    H4 -->|reject + rationale| T2
    C --> S[WorkflowSummary] --> END([Run COMPLETED])
```

| 項目 | 定義 |
|---|---|
| Input | `spec_id`, `spec_version`, 可選 `scope`（functional area / requirement 子集） |
| Initial State | WorkflowRun CREATED；TC 不存在 |
| Agents | Spec Analyst、Test Designer、Test Validator（Supervisor 編排） |
| Artifacts | SpecAnalysis、RequirementModel、TestDesignReport、TestCaseDraft、TestValidationReport、ApprovalRequest、WorkflowSummary |
| Gates | G-SPEC → G-DESIGN → G-TVAL → G-APPROVAL |
| Transitions | 見 Mermaid；TC：DRAFT → VALIDATING → VALIDATED → PENDING_APPROVAL → APPROVED → ACTIVE |
| Failure Handling | Structural FAIL 不計迭代；G-TVAL FAIL 最多 3 次後升級 Human Override |
| Human Approval | RESOLVE_AMBIGUITY（條件）、HUMAN_OVERRIDE（條件）、ACTIVATE_TESTCASE（必要） |
| Output | Registry ACTIVE TC 列表、WorkflowSummary |
| Final State | Run COMPLETED / FAILED / CANCELLED |
