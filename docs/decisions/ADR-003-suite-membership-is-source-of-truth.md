# ADR-003 · Suite Membership 是唯一事實來源，TC 上不存 regression / ci 狀態

- **Status**: Accepted（2026-09-13，APPROVE ARCHITECTURE）
- **Context**: Brief §11 TC 欄位有 `regression_status`、`ci_status`；§15 又說 Suite 只 reference TC。雙寫必然不一致。
- **Decision**: TC 只存 eligibility（`ci_eligible`、`hotfix_eligible`、`critical_path`、`execution_cost`、`stability`）；「在哪些 suite」由 `qaos suites-of <tc_id>` 反查 `testsuites/`。`test_types` 移除 `regression/smoke/hotfix`。
- **Consequences**: (+) 單一事實來源；(−) 查 TC 狀態需反查（Runtime 可快取）。
