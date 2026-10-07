# qa-agent-os 協作規則

## Worktree 隔離規則
- 一個 session 一個 worktree。開工前先確認 `pwd` 與 `git branch --show-current`；若在 main 的主目錄（`~/Desktop/qa-agent-os`），先 `git worktree add ../qa-agent-os-<任務名> -b <分支>` 再開工
- 只在自己的 worktree 路徑下讀寫檔案，一律使用該 worktree 的絕對路徑；不得寫入主目錄或其他 worktree
- 交辦給其他 session 的 prompt 必須寫明對方的 worktree 絕對路徑與分支
- commit 前跑 `git status`，只 `git add` 本 session 改過的檔案，禁止 `git add -A`／`git add .`
- 發現不是自己改的未 commit 變更：停下來回報，不修改、不 commit、不 stash
- 跑完整測試時用 `git archive HEAD` 匯出乾淨目錄，或確認工作區乾淨後再跑
- Codex 複審只針對已 commit 的 SHA，不審工作區
- 任務完成並 merge 回 main 後，用 `git worktree remove` 收掉該 worktree
