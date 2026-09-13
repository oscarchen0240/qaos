# WF-E — Regression Generation（Mermaid #7）

```mermaid
flowchart TD
    IN(["Input: target suites[], scope: all / area / impacted tc_ids, trigger: manual / post-change / hotfix"]) --> T1
    subgraph T1["Task 1 · Regression Curator"]
        direction TB
        R1[讀 Registry ACTIVE TC + metadata<br/>risk, priority, ci_eligible, execution_cost, stability, execution_mode]
        R2[讀既有 Suite 版本 + ChangeImpactReport（若 trigger=post-change/hotfix）]
        R3[Full Regression: 依 functional area × risk × critical path 選入]
        R4[Hotfix Suite: affected area + changed requirement + impacted TC + high-risk regression + critical deps]
        R5["CI Regression: automated ∧ stable ∧ ci_eligible ∧ cost ≤ medium ∧ (high value ∨ high risk)"]
        R6[Smoke: critical path ∧ cost=low]
        R1 --> R3 & R4 & R5 & R6
        R2 --> R4
        R3 & R4 & R5 & R6 --> P[RegressionProposal<br/>每筆 membership 附 justification + risk_tag<br/>與現行 Suite 的 diff: add / remove / repin]
    end
    T1 --> G1{G-REG<br/>TC ACTIVE? version 存在? 無重複?<br/>CI suite 無 manual?}
    G1 -->|FAIL| T1
    G1 -->|PASS| AR[ApprovalRequest UPDATE_SUITE_MEMBERSHIP<br/>（每個 suite 一個 request）]
    AR --> H[[Human]]
    H -->|approve| C[Runtime UPDATE_SUITE_MEMBERSHIP<br/>Suite version+1 → ACTIVE，舊版保留]
    H -->|reject| T1
    C --> S[WorkflowSummary] --> END([COMPLETED])
```

| 項目 | 定義 |
|---|---|
| Input | `target_suites[]`（full_regression / ci_regression / hotfix / smoke / feature）、`scope`、`trigger`、hotfix 時附 `change_impact_id` |
| Initial State | Registry 有 ACTIVE TC |
| Agents | Regression Curator |
| Artifacts | RegressionProposal、ApprovalRequest、WorkflowSummary |
| Gates | G-REG → G-APPROVAL |
| Failure Handling | 任一 membership 引用非 ACTIVE TC → Structural FAIL |
| Human Approval | UPDATE_SUITE_MEMBERSHIP（**加入與移出都要**，Brief §26） |
| Output | Suite 新版本；`suites-of` 反查即為 TC 的 derived regression/ci status |
| Final State | COMPLETED |
