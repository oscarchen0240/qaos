# ADR-002 · Supervisor 拆為 LLM Agent + Deterministic Runtime

- **Status**: Accepted（2026-09-13，APPROVE ARCHITECTURE）
- **Context**: Brief §7.1 要 Supervisor「檢查 Quality Gate」；若 Gate 由 LLM 判斷，Gate 本身就不可信。
- **Decision**: Structural Gate、State Transition、Permission Guard、ID 配發、Commit 全部由 `tools/qaos`（非 LLM）執行；Supervisor Agent 只做 task 分類、routing 建議、Summary 撰寫。Semantic Gate 由獨立 Validator Agent 產出 artifact，再由 Runtime 讀取其 `result` 欄位。
- **Consequences**: (+) 「Agent 做錯事卻沒人知道」的風險被 Runtime 攔截；(−) 多維護一個 CLI；Supervisor 的自主性受限（符合 Brief §4）。
