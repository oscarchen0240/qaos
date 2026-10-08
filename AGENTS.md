# Codex 在 qa-agent-os 的規則

開工前先讀 `CLAUDE.md`；其中的 worktree 隔離、commit 與 merge 規則對 Codex 同樣適用。

- 角色：主要負責 code review。只審已 commit 的 SHA，不審工作區；結果寫入主目錄 `review-handoff/<任務子目錄>/`（Claude／Codex 交接區，未進版控）。
- 需要執行 QAOS 流程時，用 `admin-ui/hooks/codex/qaos-codex` 啟動，才會載入 QAOS hooks；一般 Codex／審查 session 直接用 `codex`。
- 不要建立或 commit 專案層 `.codex/hooks.json`。
- `.codex/agents/*.toml` 由 `admin-ui/hooks/codex/sync-agents` 從 `.claude/agents` 產生，不要手動修改。
