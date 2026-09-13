# ADR-001 · 以 Artifact 為中心的狀態機，而非以對話為中心的 Agent 鏈

- **Status**: Accepted（2026-09-13，APPROVE ARCHITECTURE）
- **Context**: Brief §2 要求 No Artifact, No Transition；LLM Agent 之間若靠對話記憶傳遞，無法審計也無法重放。
- **Decision**: 每個 Agent 的唯一輸出是通過 Schema 的 Artifact 檔案；每個狀態轉換必須引用觸發它的 artifact_id 或 approval_id；Supervisor 不傳遞自然語言，只傳 artifact id。
- **Consequences**: (+) 可重放、可 diff、可離線驗證；(−) 每個 Agent 多一層序列化成本；Schema 演進需版本化（envelope.schema_version）。
