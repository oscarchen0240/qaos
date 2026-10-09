# qa-agent-os 協作規則

## Worktree 隔離規則
- 一個 session 一個 worktree。開工前先確認 `pwd` 與 `git branch --show-current`；若在 main 的主目錄（`~/Desktop/qa-agent-os`），先 `git worktree add ../qa-agent-os-<任務名> -b <分支>` 再開工
- 只在自己的 worktree 路徑下讀寫檔案，一律使用該 worktree 的絕對路徑；不得寫入主目錄或其他 worktree
- 交辦給其他 session 的 prompt 必須寫明對方的 worktree 絕對路徑與分支
- commit 前跑 `git status`，只 `git add` 本 session 改過的檔案，禁止 `git add -A`／`git add .`
- 發現不是自己改的未 commit 變更：停下來回報，不修改、不 commit、不 stash
- 跑完整測試時用 `git archive HEAD` 匯出乾淨目錄，或確認工作區乾淨後再跑
- Codex 複審只針對已 commit 的 SHA，不審工作區
- 例外：主目錄的 `review-handoff/`（未進版控）是 Claude／Codex 交接區，可讀寫，但每個任務只寫自己的子目錄
- 任務完成並 merge 回 main 後，用 `git worktree remove` 收掉該 worktree

## Merge 前必經 Codex code review
- 程式變更 merge 回 main 前，必須以 `codex exec` 送 Codex code review，審查對象為已 commit 的 SHA，結果寫入 `review-handoff/<任務子目錄>/`
- Codex 提出的問題須全部修正並再送複審，直到問題清零才可 merge；Oscar 明確決定延後的項目需記錄在交接區，不算未清零
- 未經 Oscar 確認，不得自行 merge 回 main

## GitLab／GitHub 雙邊同步
- GitLab（remote `origin`，公司）與 GitHub（remote `github`，個人）必須保持同一版：功能分支兩邊都 push，GitLab 開 MR（`glab`）的同時也在 GitHub 開 PR（`gh pr create -R oscarchen0240/qaos`），兩邊用同一份說明
- 必須在 merge 之前開 PR；GitLab 先 merge 後，GitHub 就無法再開 PR，紀錄會缺漏
- CI 只在 GitHub Actions 執行（GitLab CI/CD 未開放）；merge 前確認 GitHub PR 的 CI 綠燈
- merge 前先 `git fetch origin`，確認 `origin/main` 是分支的祖先；main 已前進時，先 rebase 或合併最新 main、重跑測試，再請 Oscar 確認，fetch 與 merge 不可寫在同一個指令裡
- 在 GitLab merge MR 後，立即 `git push github origin/main:refs/heads/main` 同步 GitHub main（PR 會自動變成 MERGED），並確認 main 的 CI 結果
- 避開 21:00～21:30（每晚資料 push 排程）；QAOS 資料 commit 直接在本機 main，由排程同時推兩邊，不開 MR／PR
- 交辦給其他 session 的 prompt 必須寫明「GitLab MR 與 GitHub PR 都要開」

## 注意事項
- 本專案避免用 Codex Desktop 匯入 Claude 對話；若有匯入，事後檢查 `git status` 與 `.codex/`、`AGENTS.md` 是否被重新產生或覆寫
