# WF-B — SPEC → Bug（Mermaid #4）

```mermaid
flowchart TD
    IN([Input: spec_id@version, execution_id 或 actual_behavior + evidence_ids, testcase_id?]) --> CHK{RequirementModel<br/>for spec_version 存在?}
    CHK -->|否| T0[Task 0 · Spec Analyst<br/>同 WF-A Task 1] --> CHK
    CHK -->|是| T1
    subgraph T1["Task 1 · Bug Analyst"]
        BA["輸入: RequirementModel + Execution + Evidence + (TC version)<br/>推導 Expected Behavior ← Requirement/AC<br/>比對 Actual<br/>產 BugDraft（含 severity/priority 建議, suspected_area）"]
    end
    T1 --> G1{G-BVAL structural<br/>evidence ≥1 + hash 相符?}
    G1 -->|FAIL| T1
    G1 -->|PASS| T2
    subgraph T2["Task 2 · Bug Validator"]
        BV[輸入: SpecVersion + RequirementModel + BugDraft + Evidence + bugs/ 索引<br/>產 BugValidationReport]
    end
    T2 --> R{result}
    R -->|FAIL, iter ≤ 3| T1
    R -->|FAIL, iter > 3| HO[[Human: HUMAN_OVERRIDE]]
    R -->|DUPLICATE| HD[[Human 確認 duplicate_of]] --> REJ([Bug REJECTED])
    R -->|AMBIGUITY| HA[[Human: RESOLVE_AMBIGUITY]] --> T1
    R -->|PASS| V[Bug → VALIDATED]
    HO -->|override| V
    V --> AR[ApprovalRequest OPEN_BUG<br/>含最終 severity/priority]
    AR --> H[[Human]]
    H -->|approve| C[Runtime COMMIT_BUG → bugs/product/area/<br/>Bug OPEN；render bug-report 格式]
    H -->|reject| T1
    C --> S[WorkflowSummary] --> END([COMPLETED])
```

| 項目 | 定義 |
|---|---|
| Input | `spec_id@spec_version`；`execution_id`（或 `actual_behavior` 文字 + `evidence_ids[]`）；可選 `testcase_id@version` |
| Initial State | Evidence 已由 Human/CI 存入 `evidence/`（帶 sha256） |
| Agents | (Spec Analyst 若無 RequirementModel)、Bug Analyst、Bug Validator |
| Artifacts | BugDraft、BugValidationReport、ApprovalRequest、WorkflowSummary |
| Gates | G-BVAL、G-APPROVAL |
| Failure Handling | 無 Evidence → Structural FAIL，Run 不得繼續（No Evidence, No Formal Bug）；DUPLICATE / AMBIGUITY 是 Validator 的特殊 FAIL 子型 |
| Human Approval | OPEN_BUG（必要）、確認 duplicate、RESOLVE_AMBIGUITY、HUMAN_OVERRIDE |
| Output | `bugs/<product>/<area>/<bug_id>.yaml`（OPEN）+ human-facing render（md/html） |
| Final State | COMPLETED / REJECTED / FAILED |
