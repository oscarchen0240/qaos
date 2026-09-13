# WF-C — SPEC Change Impact（Mermaid #5）

```mermaid
flowchart TD
    IN([Input: spec_id, from_version, to_version]) --> T0{RequirementModel<br/>for to_version 存在?}
    T0 -->|否| SA[Task 0 · Spec Analyst on to_version] --> T0
    T0 -->|是| T1
    subgraph T1["Task 1 · Change Impact Analyst (phase: impact)"]
        CIA[輸入: 兩版 SpecVersion + 兩版 RequirementModel + 引用 from_version 的 ACTIVE TC<br/>產 ChangeImpactReport: requirement_diff + testcase_impact]
    end
    T1 --> G1{G-IMPACT<br/>完整性: 所有 REQ / TC 皆有判定}
    G1 -->|FAIL| T1
    G1 -->|PASS| NI{有 affected /<br/>obsolete / new_required?}
    NI -->|否| S0[WorkflowSummary NO_IMPACT] --> END0([COMPLETED])
    NI -->|是| T2
    subgraph T2["Task 2 · Test Designer (mode=change)"]
        TD[輸入: ChangeImpactReport + 舊版 TC + 新 RequirementModel<br/>產 TestCaseDraft（新版本 supersedes 舊版）+ TestDesignReport]
    end
    T2 --> G2{G-DESIGN} -->|FAIL| T2
    G2 -->|PASS| T3
    subgraph T3["Task 3 · Test Validator"]
        TV[驗證新版 Draft 對 to_version]
    end
    T3 --> G3{G-TVAL}
    G3 -->|FAIL ≤3| T2
    G3 -->|FAIL >3| HO[[HUMAN_OVERRIDE]]
    G3 -->|PASS| T4
    subgraph T4["Task 4 · Change Impact Analyst (phase: compare)"]
        CMP[輸入: 舊 ACTIVE 版本 + 新 VALIDATED 版本<br/>產 VersionComparisonReport: unchanged/changed/added/removed + impacted requirement]
    end
    T4 --> G4{G-COMPARE} -->|FAIL| T4
    G4 -->|PASS| AR[ApprovalRequest APPLY_CHANGE<br/>「是否將此新版 Test Case 更新為正式 Registry 版本？」]
    AR --> H[[Human]]
    H -->|approve| C[Runtime: 新版 ACTIVE、舊版 SUPERSEDED、obsolete → RETIRED<br/>ChangeImpact APPLIED]
    H -->|reject| T2
    C --> RG{受影響 TC 在<br/>任何 Suite 中?}
    RG -->|是| WFE[觸發 WF-E regression-generation<br/>scope = impacted]
    RG -->|否| S[WorkflowSummary]
    WFE --> S --> END([COMPLETED])
```

| 項目 | 定義 |
|---|---|
| Input | `spec_id`, `from_version`, `to_version`（to_version 已由 Human 匯入 `specs/`） |
| Initial State | ChangeImpact DETECTED |
| Agents | Change Impact Analyst（兩階段）、Test Designer、Test Validator、(Spec Analyst) |
| Artifacts | ChangeImpactReport、TestCaseDraft、TestDesignReport、TestValidationReport、VersionComparisonReport、ApprovalRequest、WorkflowSummary |
| Gates | G-IMPACT → G-DESIGN → G-TVAL → G-COMPARE → G-APPROVAL |
| Transitions | ChangeImpact：DETECTED → ANALYZING → IMPACTED → TEST_UPDATE_REQUIRED → VALIDATING → COMPARING → PENDING_APPROVAL → APPLIED |
| Failure Handling | 同 WF-A；「不能直接覆蓋既有正式 TC」由 Runtime 保證（Agent 無 COMMIT 權限） |
| Human Approval | APPLY_CHANGE（必要，Brief §10 原句）、RETIRE_TESTCASE（obsolete 時併入同一 request） |
| Output | 新 TC 版本 ACTIVE、舊版 SUPERSEDED、VersionComparisonReport |
| Final State | APPLIED / NO_IMPACT |
