# 需求 A 正式部署操作手冊（W1～M5）

- 用途：需求 A（移轉與操作執行器）正式部署的逐步操作手冊。以後重新部署，或做同類的資料移轉時，可以照這份手冊操作。
- 來源：2026-10-08 部署使用的手冊。部署後依實際結果更正，並把該次的實際數字改寫成範例。
- **範例與實際紀錄**：
  - 文中標示「例：」或寫在「範例」欄的 SHA、檔數、計數、op_id、路徑，都是 2026-10-08 部署的實際值，只作為參考。
  - 再次執行時，要以當次的 M1 預演報告與現況為準，重新取得預期值。
  - 該次部署每一步的實際輸出、判斷與更正，記錄在 deploy log：主資料夾 `review-handoff/clr-spec-investigation/requirement-a-deploy-log.md`（未進版控）。
- 依據：
  - 最終規格 `docs/requirements/requirement-a-final.md` §11～§15（§15.1、§15.2）、附錄 A 5-16
  - 驗收紀錄 `docs/requirements/requirement-a-acceptance-record.md`
  - 當次的 M1 預演報告（規格 §15.1 M1）
- 原則：
  - 每一段做完就寫進 deploy log 並停下來，等 Oscar 說「開始下一段」。
  - 任何一步的結果與預期不符，立刻停下來回報，不自行修正，也不自行回復。
  - 回復（R0～R6）一律由 Oscar 決定，預設向前修正。
- 全程禁止：
  - 對主資料夾執行 `migrate rollback` 或任何回復操作
  - 修改程式、`admin-ui/`、`CLAUDE.md`
  - force push
  - `git add -A`、`git add .`

---

## 0. 變數與部署前要確認的事項

```sh
MAIN=<主資料夾>                     # 例：/Users/oscar/Desktop/qa-agent-os（main）
WT=<需求 A worktree>                # 例：/Users/oscar/Desktop/qa-agent-os-requirement-a（qaos/requirement-a）
DEP=<部署證據目錄>                  # 例：/Users/oscar/Desktop/qaos-deploy-requirement-a（主資料夾以外的固定路徑）
BY=<actor>                          # maintenance／migrate 的 --by；用既有核准紀錄中 Oscar 使用的 actor
H=<MR 的 HEAD 完整 SHA>             # 例：3b2b726…（MR !8）
OLD=<舊程式 SHA>                    # 部署前的 main = origin/main = github/main；例：f5188b0…
export PYTHONDONTWRITEBYTECODE=1
```

| # | 事項 | 建議（括號內為 2026-10-08 的決定） |
|---|---|---|
| **C1** | 部署證據放在哪裡 | 放在主資料夾以外、不在任何 git repo 內的固定路徑。理由如下：<br>• 快照工具禁止把結果寫在資料 root 內，所以不能放 `review-handoff/`。<br>• scratchpad 會隨 session 消失。<br>• worktree 會在 merge 後收掉。<br>• R5（如果發生）需要同一份 W1 對照和同一個工具檔。<br>（採用 `/Users/oscar/Desktop/qaos-deploy-requirement-a/`） |
| **C2** | `maintenance`、`migrate` 的 `--by` | 用既有核准紀錄中 Oscar 使用的 actor |
| **C3** | M2：本機 main 與 origin/main 分岔時怎麼處理 | 見 M2-4，建議方案 A（採用 A） |
| **C4** | M4：在主資料夾跑 pytest 與 CLAUDE.md 規則的關係 | CLAUDE.md 規定「跑完整測試時用 `git archive HEAD` 匯出乾淨目錄，或確認工作區乾淨後再跑」。M4 時工作區有未 commit 的移轉結果。<br>建議在主資料夾跑，前後各做一次逐檔 hash，確認測試沒有寫入業務資料；另外再用 `git archive` 匯出目錄跑一次作為對照。<br>（兩種都跑） |
| **C5** | M5：`locks/` 與 `operations/` 是否進資料 commit | `operations/` 要 commit；`locks/` 不要 commit。`locks/` 現已列入 `.gitignore` |

---

## 1. 前置條件

| 項目 | 預期 | 範例（2026-10-08 D0 實際） |
|---|---|---|
| 需求 A 分支 HEAD | 等於 `$H`；worktree 乾淨 | `qaos/requirement-a` @ `3b2b726` |
| GitLab MR | 指向 `$H`，未 merge，mergeable、無衝突 | MR !8：`opened`、base `f5188b0` |
| GitHub PR | 指向 `$H`，未 merge | PR #1：`OPEN`、`MERGEABLE` |
| GitHub CI | 通過 | runtime-pytest 653 passed、1 skipped；admin-ui-pytest 83 passed |
| 主資料夾 | main，與 origin/main、github/main 一致 | HEAD `f5188b0` |
| 主資料夾未追蹤檔 | 只有已知的檔案；未追蹤的業務檔在 W1-3 納入資料 commit | `review-handoff/`，以及 9/18 留下的 10 個業務檔（見 W1-3 範例） |
| 被忽略的檔案 | — | `.warroom/{events.jsonl,handoff.jsonl,recommendations/}`、`admin-ui/data/`、`locks/` |
| GitLab 專案設定 | — | `merge_method: merge`（會產生 merge commit）、squash 預設關閉 |
| MR 差異範圍 | 只有程式與定義層，**沒有任何業務資料檔** | 127 檔：tools、tests、schemas、docs、agents、workflows、`.claude`、`.github` |

---

## W1 進入維護窗口（Oscar 宣告開始）

### W1-1 確認沒有其他寫入者

```sh
pgrep -fl 'uvicorn|vite'                                   # 預期：沒有輸出
pgrep -fl 'tools\.qaos|bin/qaos'                           # 預期：沒有輸出
pgrep -fl 'claude|codex' | grep -v "$$"                    # 列出其他 Claude／Codex 程序，交 Oscar 確認都沒有在跑 bin/qaos
git -C $MAIN rev-parse HEAD origin/main                    # 預期：兩者都是 $OLD
git -C $MAIN status --porcelain                            # 預期：與第 1 節的未追蹤清單完全相同，沒有 M／D
```

**停止條件**：
- uvicorn／vite 或 `bin/qaos` 程序還在；
- 或主資料夾有未預期的變更；
- 或 admin-ui（Session B）還沒回覆「已停止」。

**注意**：程式無法判斷其他 Claude／Codex session 有沒有在跑 `bin/qaos`，最後要以 Oscar 的確認為準。

### W1-2 建立證據目錄、保存工具與腳本、取得寫入前的 hash

```sh
mkdir -p $DEP/{w1,m2,m3,m4,w2,m5,hash,scripts,tool}
cp $WT/tools/legacy_validate_snapshot.py $DEP/tool/        # R5 必須使用同一個工具檔（compare 會核對 tool_sha256）
shasum -a 256 $DEP/tool/legacy_validate_snapshot.py
git -C $WT show $H:tools/legacy_validate_snapshot.py | shasum -a 256   # 預期：與上一行相同
# M1 預演用過的唯讀腳本：hashtree.py（逐檔 sha256）、inventory.py（業務現況），從 M1 的工作目錄複製到 $DEP/scripts/
cp <M1 工作目錄>/scripts/{hashtree.py,inventory.py} $DEP/scripts/
python3 $DEP/scripts/hashtree.py $MAIN $DEP/hash/W1a.json
```

**檢查**：
- 工具的 sha256 一致；
- `tool_version` 是 2（`grep '^TOOL_VERSION' $DEP/tool/legacy_validate_snapshot.py`）。

### W1-3 資料 commit（回復點；不 push）

逐檔列出要納入的未追蹤業務檔，記錄大小與 sha256，核對後再 commit。

**範例**（2026-10-08 共 10 檔，都是 9/18 留下的）：

| 路徑 | 大小 | sha256 前 12 碼 | 說明 |
|---|---|---|---|
| `evidence/testrun-6/EVD-0060.jpg` | 7991 | `238c70a110e9` | 證據 |
| `evidence/testrun-6/EVD-0060.yaml` | 275 | `3de35101ed18` | 證據 metadata |
| `evidence/testrun-6/EVD-0061.jpg` | 7991 | `238c70a110e9` | 證據（與 0060 同一張圖） |
| `evidence/testrun-6/EVD-0061.yaml` | 275 | `ebf808f392c9` | 證據 metadata |
| `executions/2026-09/EXE-20260918-001.yaml` | 289 | `b35adb339dba` | 執行紀錄 |
| `executions/2026-09/EXE-20260918-002.yaml` | 289 | `00516dc5dd1f` | 執行紀錄 |
| `runs/RUN-20260918-012/run.yaml` | 1878 | `acb1a1dc2497` | CANCELLED 的 spec-to-bug |
| `runs/RUN-20260918-012/audit.log` | 121 | `e80127a3b393` | 同上 |
| `runs/RUN-20260918-013/run.yaml` | 1878 | `e5d9ebc6a13a` | CANCELLED 的 spec-to-bug |
| `runs/RUN-20260918-013/audit.log` | 121 | `ec8496cf5f95` | 同上 |

**排除**（不進資料 commit）：

| 路徑 | 理由 |
|---|---|
| `review-handoff/` | Claude／Codex 交接區（CLAUDE.md 例外區），不進版控 |
| `.warroom/`、`admin-ui/data/`、`locks/` | 已被 gitignore；不是 QAOS 業務資料。`.warroom/events.jsonl` 由 hooks 持續追加，不納入 hash 比對 |
| 其他非業務檔（例如 Codex Desktop 匯入產生的 `.codex/hooks.json`、未追蹤的 `AGENTS.md`） | 不是業務資料；出現時先回報來源 |

先核對 sha256，再 commit：

```sh
cd $MAIN
shasum -a 256 <逐檔路徑>                                   # 預期：與清單相同
git add -- <逐檔路徑>                                      # 逐檔列出，不使用 -A 或 .
git diff --cached --name-status                            # 預期：剛好是清單的檔案，都是 A，沒有其他檔案
git commit -m "data: 需求 A 部署 W1 回復點（納入未追蹤業務檔）" -m "..." -m "Co-Authored-By: ..."
git rev-parse HEAD                                         # 記為 D1（例：7bd2a63）
git status --porcelain                                     # 預期：未追蹤的業務檔是 0
git diff --stat $OLD HEAD -- tools bin schemas workflows agents permissions   # 預期：沒有輸出（程式仍是舊的）
```

**停止條件**：
- sha256 不符；
- staged 的檔案和清單不同；
- commit 後還有其他未追蹤的業務檔。

### W1-4 W1 對照（舊程式、工具版本 2）

```sh
cd $WT
python3 tools/legacy_validate_snapshot.py snapshot --root $MAIN --out $DEP/w1/legacy-validate-w1.json
which python3; python3 --version                           # 記錄（R5 必須用同一個 python3）
```

說明：
- `--program` 不指定時等於 `--root`，也就是主資料夾的舊程式。
- 工具用 `PYTHONDONTWRITEBYTECODE=1` 執行子程序，只讀資料 root。

**預期**：
- 結束碼 0。
- 計數與 M1 的對照組相同。例：「3681 檔：VALID 3658、INVALID 23」。
- 結果檔的 `tool_version` 是 `"2"`。
- `root` 和 `program` 都是 `$MAIN`。
- `root_git_head` 和 `program_git_head` 都是 D1。
  - 舊程式的內容等於 `$OLD`，由 W1-3 的 diff 為空證明。
  - 舊程式 SHA 記為 `$OLD`。
- `registered_ops` 是空的（舊程式沒有 `operations/`）。

**檢查**：

```sh
python3 - "$DEP/w1/legacy-validate-w1.json" <<'EOF'
import json, sys; d = json.load(open(sys.argv[1]))
print({k: d[k] for k in ("tool_version","tool_sha256","root","root_git_head","program_git_head","program_sha256","root_schemas_sha256","env_versions","registered_ops","summary","no_schema")})
print(sorted(r for r, v in d["files"].items() if v["rc"] != 0))
EOF
shasum -a 256 $DEP/w1/legacy-validate-w1.json
```

INVALID 清單應該等於 M1 報告列出的清單。例：23 檔，包括：
- 6-38 baseline 中的 11 檔；
- 10 個 `runs/*/entities/bug.yaml`；
- 2 個 `entities/change-impact.yaml`。

**停止條件**：
- 結束碼不是 0（2 表示舊程式環境或範圍異常）；
- 計數或 INVALID 清單與 M1 不同；
- 中繼資料缺項；
- HEAD 不是 D1。

### W1-5 寫入後的 hash

```sh
python3 $DEP/scripts/hashtree.py $MAIN $DEP/hash/W1b.json
# 比對 W1a 與 W1b，排除 review-handoff/ 與 .warroom/events.jsonl：預期沒有任何新增、移除或內容差異
```

**停止條件**：除了排除項目以外有任何差異。

W1 → **停下來回報**。回報內容：D1 SHA、舊程式 SHA、工具 sha256、W1 對照的路徑與 sha256、計數。

---

## M2 merge 與部署（Oscar 說 merge）

### M2-1 merge 前核對

```sh
git -C $MAIN fetch origin && git -C $MAIN fetch github
git -C $MAIN rev-parse origin/main github/main             # 預期：兩者都是 $OLD
glab mr view <MR> -F json | python3 -c 'import json,sys;d=json.load(sys.stdin);print(d["state"],d["sha"],d["detailed_merge_status"],d["has_conflicts"])'
# 預期：opened <$H> mergeable False
```

**停止條件**：origin/main 已經前進、MR 的 sha 改變，或狀態不是 mergeable。

### M2-2 GitLab merge

```sh
cd $MAIN && glab mr merge <MR> --sha $H --auto-merge=false --yes
```

- 不加 `--squash`、`--rebase`、`--remove-source-branch`。
- 保留來源分支：worktree 收掉時再一起處理。

**預期**：
- MR 變成 `merged`；
- origin/main 是新的 merge commit M，parents 是 `$OLD` 和 `$H`。

### M2-3 核對 M

```sh
git -C $MAIN fetch origin
M=$(git -C $MAIN rev-parse origin/main); git -C $MAIN log -1 --format='%H %P %s' $M
git -C $MAIN rev-parse "$M^{tree}" "$H^{tree}"             # 預期：相同（$OLD 是 $H 的祖先時）
```

**停止條件**：parents 不對，或 tree 和 `$H` 不同。

### M2-4 更新本機 main【C3】

D1 還沒 push，所以這時本機 main = `$OLD` + D1，origin/main = `$OLD` + M，兩邊各領先一個 commit。可以選的做法：

| 方案 | 做法 | 結果 |
|---|---|---|
| **A（建議）** | `git -C $MAIN merge --no-ff --no-edit origin/main`（也就是 `git pull --no-rebase origin main`）<br>GitHub 只推 GitLab 的 main：`git -C $MAIN push github origin/main:main` | • D1 的 SHA 不變，和 W1 對照記錄的資料 commit 一致。<br>• 產生本機 merge commit L。<br>• GitHub main = GitLab main = M（從 `$OLD` fast-forward），GitHub PR 變成已合併。<br>• D1、L 留在本機，到 M5 再一般 push |
| B | `git pull --rebase` | D1 會被改寫成新的 SHA，和 W1 對照的紀錄不一致。**不建議** |
| C | 先把 D1 push 到 GitLab，再 merge | 違反「W1 先不要 push」。不採用 |
| A' | 同 A，但 GitHub 推本機 main（`git push github main`） | • GitHub main = L（含 D1）、GitLab main = M，兩個 remote 暫時不同步，到 M5 再同步。<br>• GitHub 會先拿到 D1 資料 |

方案 A 的指令與預期：

```sh
cd $MAIN
git merge --no-ff --no-edit origin/main                    # 預期：沒有衝突（D1 只新增業務檔，M 只動程式與定義層）
git log -1 --format='%H %P'                                # L：parents = D1、M
git diff --stat $H HEAD -- tools bin schemas workflows agents permissions tests docs .claude .github   # 預期：沒有輸出
git push github origin/main:main                           # 一般 push，必須是 fast-forward
gh pr view <PR> -R oscarchen0240/qaos --json state,mergedAt,mergeCommit    # 預期：MERGED
```

**停止條件**：
- merge 衝突；
- push 被拒絕（non-fast-forward），**絕不 force**；
- GitHub PR 沒有變成 MERGED。

### M2-5 確認 working tree 是新程式，立刻 maintenance start

```sh
cd $MAIN
git status --porcelain                                     # 預期：只剩 review-handoff/ 等已知的非業務檔
test -f tools/qaos/migrate.py && test -f tools/qaos/operation.py && echo new-code
bin/qaos operation list                                    # 唯讀；預期：沒有任何計畫
bin/qaos maintenance start --by $BY                        # 預期：rc=0
```

**檢查**：

```sh
cat locks/maintenance.yaml                                 # 存在，內容的 op_id 等於本次 maintenance start
bin/qaos operation list                                    # 一筆 maintenance_start，completed
ls runs/_audit.d/                                          # 一個 <op>-1.yaml 事件檔
git diff --quiet -- runs/ && echo audit-unchanged          # 標記寫入前不 render：沒有任何既有 audit.log 被改
```

**停止條件**：
- `operation list` 有計畫；
- `maintenance start` 的 rc 不是 0；
- 既有的 `audit.log` 被改動。

M2 → **停下來回報**：MR、PR 的狀態、M、L、maintenance start 的 op_id。

---

## M3 移轉（Oscar 授權）

### M3-1 唯讀重新讀取業務現況

```sh
python3 $DEP/scripts/inventory.py $MAIN > $DEP/m3/inventory.json   # 直接讀 YAML，不呼叫 bin/qaos
```

**預期**：與 M1 預演時的業務現況相同，或差異都能逐項說明。

| 項目 | 範例（2026-10-08） |
|---|---|
| run 總數 | 93：COMPLETED 82、CANCELLED 9、RUNNING 1、WAITING_HUMAN 1 |
| RUNNING | 只有 `RUN-20260914-001`：manual-test-to-regression，T1～T3 DONE、T4 READY，沒有 `waiting_on_approval_id` |
| WAITING_HUMAN | 只有 `RUN-20261002-001`（APR-0192） |
| PENDING 核准單 | 只有 APR-0192 |
| 最新 run／APR | RUN-20261002-002／APR-0193 |

**停止條件**：任何一項和 M1 不同，而且無法說明。

### M3-2 把 RUNNING 的 run 列給 Oscar，確認是 idle

- 對每個 RUNNING 的 run，列出 `run.yaml` 的 status、tasks、`updated_at`、inputs。
- 確認沒有任何 agent 正在執行這些 run。
- **等 Oscar 確認每個 run 的處理方式**（`--acknowledge-idle` 或 `--cancel-run`）之後，才進行下一步。

### M3-3 移轉

```sh
cd $MAIN
bin/qaos migrate --by $BY --acknowledge-idle <RUN>         # 或 --cancel-run <RUN>；記錄 X（op_id）
```

**預期**：rc=0。清單分類應與 M1 預演時相同。

| 類別 | 範例（2026-10-08，與 M1 w1-ack 相同） |
|---|---|
| restore | 43 |
| remove | 735 |
| retain_audit | 45 |
| planned_audit | 825 |
| shared_control | 5 |
| untouched | 2800 |

計畫的步數與 no_change 數，從 `operations/_global/<X>/manifest.yaml` 與計畫檔統計。例：共 824 步，no_change 135。

**停止條件**：
- rc 不是 0；
- 或分類數量與 M1 不同。不同時先回報，不判斷對錯；
- 中途中止時，不自行續做、不 rollback，直接回報。續做或回復都由 Oscar 決定。

### M3-4 移轉驗證

```sh
bin/qaos migrate verify                                    # 預期：rc=0，通過
bin/qaos operation list                                    # 預期：X completed；沒有 in_progress
```

M3 → **停下來回報**：X、清單數量、verify 結果。

---

## M4 驗證（回報）

所有檢查都是唯讀。檢查腳本放在 `$DEP/scripts/m4_checks.py`，於 M4 時撰寫，只讀取不寫入；輸出寫到 `$DEP/m4/checks.json`。

| # | 檢查 | 方法 | 預期（範例數字為 2026-10-08） |
|---|---|---|---|
| 1 | 標記存在 | `artifacts/requirements/_migration.yaml` | `migrate_op_id` 等於 X；`mode_per_run` 與 M3-3 指定的一致；`manifest_sha256` 等於清單檔 |
| 2 | 第一次 render 成功 | 有 `operations/_global/status.d/<X>-completed.yaml`；計畫中 render 步驟都有完成紀錄 | 全部 render 步驟都是 done |
| 3 | `audit.log` 開頭逐位元等於原檔 | 對標記中每個 `frozen` 的 log（每個 run 一份，加上全域一份）：<br>• 原檔 = `git show D1:<path>`<br>• `audit.legacy.log` 的位元組等於原檔<br>• sha 等於標記中的 frozen 值<br>• 現在的 `audit.log` 以原檔位元組開頭 | 全部符合（例：94／94）；`absent` 0 份 |
| 4 | untouched 全部吻合 | 清單 `untouched[]` 每筆的目前 sha256 等於 `pre_sha256` | 全部吻合（例：2800／2800） |
| 5 | 抽查 sidecar | • RUNNING run 的 `_bindings` sidecar（例：`RUN-20260914-001` 綁 DAILYREPORT 0.1 R000、`legacy_binding: true`）<br>• R000 的位元組等於 `git show D1:` 對應的 `requirements.yaml`<br>• 任一 TC 的 sidecar<br>• 任一 CLR 的 `answer_revisions[0]`<br>• 總數（例：run sidecar 93、TC sidecar 499、CLR rev 0 42 張） | 全部符合 M1 |
| 6 | restore 與 remove | restore 的 backup sha 等於 `pre_sha256`；目前內容等於 `planned_post_sha256`。remove 類目前存在，sha 等於 `planned_post_sha256` | 全部符合 |
| 7 | pytest【C4】 | 在 `$MAIN` 執行 `python3 -m pytest tests/ -q`；前後各跑一次 `hashtree.py`，比對時排除 `__pycache__`、`.pytest_cache`、`review-handoff/`、`.warroom/events.jsonl`。完整測試約需 40 分鐘 | 全部通過，0 skip；前後 hash 沒有差異 |
| 8 | `validate_phase1` | `cd $MAIN && python3 tools/validate_phase1.py` | ALL CHECKS PASSED |
| 9 | 狀態 | `bin/qaos operation list`；`locks/maintenance.yaml` 存在 | 仍是 `S_maint`，沒有未完成計畫 |

**停止條件**：任何一項不符。pytest 失敗時，只保存輸出並回報，不修改程式。

M4 → **停下來回報**。

---

## W2 結束維護窗口（Oscar 宣告）

```sh
cd $MAIN
bin/qaos maintenance end --by $BY                          # 預期：rc=0
test ! -e locks/maintenance.yaml && echo S_post
bin/qaos operation list                                    # 預期：maintenance_end completed；沒有 in_progress
bin/qaos migrate verify                                    # 預期：rc=1，只報 runs/_audit.log 的 2 項（見下方說明）
```

**說明**（2026-10-08 依實際結果更正；原本預期「仍然通過」是錯的）：
- `maintenance end` 依規格 §11.7 會重建全域 `runs/_audit.log`，在末尾追加一行 `MAINTENANCE_END`。
- 規格 §12 的 `migrate verify` 要求 restore 類等於移轉當下的計畫值，所以這時一定會回報 `runs/_audit.log` 的 2 項：「計畫值不符」與「restore 不等於移轉後的值」。
- W2 改用下列方式驗證：`runs/_audit.log` 去掉最後一行 `MAINTENANCE_END` 之後，sha256 等於移轉計畫中 `runs/_audit.log` 步驟（render）的 expected_after。
- 除了這 2 項以外，verify 回報其他任何失敗都要停下來。

**停止條件**：`maintenance end` 的 rc 不是 0、維護檔仍然存在，或 verify 回報上述 2 項以外的失敗。

完成後寫一則通知 admin-ui（Session B）可以恢復的訊息，交給 Oscar 轉貼。內容包括：
- 新程式已經上線；
- 行為改變的項目；
- admin-ui 直接寫檔的處理方式。

W2 → **停下來**。

---

## M5 資料 commit（Oscar 授權）

### M5-1 列出移轉結果

```sh
cd $MAIN
git status --porcelain > $DEP/m5/status.txt
```

預期只有以下幾類變更：
- **修改**：
  - CLR 的 yaml，以及 render 有變的 `CLR-*.md`；
  - `audit.log`。
  - 這兩類都要與清單的 restore 一致。例：修改 43 檔，也就是 42 張 CLR 的 yaml 加上 `runs/_audit.log`。
- **新增**：
  - `artifacts/requirements/**/revisions/*`
  - `artifacts/requirements/_bindings/*`
  - `artifacts/requirements/_migration.yaml`
  - `testcases/_bindings/*`
  - `runs/**/audit.legacy.log`
  - `runs/_audit.d/*`
  - `operations/**`，其中包括移轉 X 的控制檔（規格 §11.3「移轉計畫、清單、backup 檔」，retain_audit，kind: control）：
    - `operations/_global/<X>.yaml`（計畫檔）
    - `operations/_global/<X>/manifest.yaml`（清單檔，1 個；它的 sha256 要等於移轉標記的 `manifest_sha256`）
    - `operations/_global/<X>/blobs/*`（計畫步驟引用的內容檔；例：824 個）
    - `operations/_global/<X>/backup/**`（restore 的備份；例：43 個）
    - `operations/_global/<X>/progress.d/*`
    - `operations/_global/index.d/<seq>-<X>.yaml`、`operations/_global/status.d/<X>-completed.yaml`
    - maintenance start／end 各自的計畫檔、`blobs/*`、`progress.d/*`、`index.d`、`status.d`
- 加上原本就有的非業務檔（例如 `review-handoff/`）。`locks/` 已列入 `.gitignore`，不會出現在 `git status`。

逐檔對照清單：
- 修改的檔案集合，必須等於 restore 中目前內容和 D1 不同的路徑。
- 新增的檔案集合，必須等於 remove、retain_audit、planned_audit 和控制類操作輸出的聯集，再加上 X 的清單檔與 `blobs/*`。清單檔本身與計畫的 blobs 不在清單的分類內，要另外對照：
  - `manifest.yaml` 1 個；
  - `blobs/*` 的數量與計畫步驟引用的 blob 一致。允許多出 1 個未被引用的孤兒 blob，內容是 `manifest_sha256: null` 的移轉標記草稿（程式既有行為）；其他未被引用的 blob 都算清單以外的變更。

範例（2026-10-08 實際對照，詳見 deploy log 的 M5-1）：

| 來源 | 數量 |
|---|---|
| remove | 735 |
| retain_audit | 44（另 1 項是清單預留的 `index.d/<plan_seq>-<X>.yaml`，實際路徑為 `index.d/00000002-<X>.yaml`） |
| planned_audit | 825 |
| maintenance start／end 的控制類輸出 | 19 |
| X 的 `index.d/00000002-<X>.yaml` | 1 |
| X 的 `manifest.yaml` | 1 |
| X 的 `blobs/*` | 824（823 個被計畫引用，加上 1 個孤兒） |

**停止條件**：出現清單以外的變更。

### M5-2 決定納入範圍【C5】

| 路徑 | 建議 | 理由 |
|---|---|---|
| 業務檔：CLR、audit、revisions、`_bindings`、`_migration.yaml`、`audit.legacy.log`、`audit.d` | 納入 | 移轉結果本身 |
| `operations/`（計畫、清單、blobs、backup、`index.d`、`status.d`、`progress.d`） | 納入 | 稽核證據與回復依據（`retain_audit`），規格要求保留 |
| `locks/`（`qaos-operation.lock`、`qaos-operation.owner`） | **不納入**（已 gitignore） | flock 控制面與診斷檔。`.owner` 每次操作都會變。鎖檔永不刪除 |
| `review-handoff/` 等非業務檔 | 不納入 | 同 W1 |

範例：2026-10-08 共納入 2492 檔，依目錄分為 artifacts 142、clarifications 42、operations 1711、runs 98、testcases 499。

### M5-3 commit 並 push

**放行清單（`ALLOW`）要依當次 M5-1 調整。** 下面的五個目錄是 2026-10-08 移轉的範圍。如果當次 M5-1 的修改或新增涉及其他業務目錄（例如 `approvals/`、`bugs/`、`evidence/`、`executions/`、`specs/`），要先更新 `ALLOW`，再執行下面的指令。

```sh
cd $MAIN
# 逐檔清單：修改的檔案 + 未追蹤檔（--others 會把未追蹤目錄展開成檔案），只放行 M5-1／M5-2 的業務目錄
#   artifacts/      revisions、_bindings、_migration.yaml
#   clarifications/ CLR 的 yaml 與 render 的 md
#   operations/     計畫、清單、blobs、backup、index.d、status.d、progress.d
#   runs/           audit.log、audit.legacy.log、_audit.d、audit.d
#   testcases/      _bindings
# core.quotePath=false：中文路徑不轉成八進位跳脫，pathspec 才對得上
ALLOW='^(artifacts|clarifications|operations|runs|testcases)/'
{ git -c core.quotePath=false diff --name-only; git -c core.quotePath=false ls-files --others --exclude-standard; } | sort -u > $DEP/m5/changed.txt
grep -E "$ALLOW" $DEP/m5/changed.txt > $DEP/m5/paths.txt
grep -vE "$ALLOW" $DEP/m5/changed.txt                      # 不納入的變更：預期只有 review-handoff/ 底下的路徑；出現其他任何路徑就停下來回報
git -c core.quotePath=false diff --name-only --diff-filter=D | grep -E "$ALLOW"   # 刪除檢查：預期沒有輸出（移轉不刪除業務檔）
git --literal-pathspecs add --pathspec-from-file=$DEP/m5/paths.txt   # 逐檔路徑清單，路徑不當成萬用字元；不使用 -A 或 .
git -c core.quotePath=false diff --cached --name-only | sort > $DEP/m5/staged.txt
diff $DEP/m5/paths.txt $DEP/m5/staged.txt                  # 預期：沒有差異
git diff --cached --stat | tail -1                          # 檔數必須與 M5-1 的預期相符
git commit -m "data: 需求 A 資料移轉（migrate <X 前 12 碼>，<RUN 的處理方式>）" -m "..." -m "Co-Authored-By: ..."
git log --oneline origin/main..main                        # 預期：D1、L、D2 三個 commit
git push origin main                                       # 一般 push（fast-forward：M → L → D2）
git push github main                                       # 一般 push（fast-forward：M → … → D2）
git rev-parse main origin/main github/main                 # 預期：三者相同
git status --porcelain                                     # 預期：只剩 review-handoff/
```

**停止條件**：
- 有清單以外的檔案被 staged；
- 業務目錄以外出現 `review-handoff/` 以外的任何路徑；
- 刪除檢查有輸出；
- push 被拒絕（non-fast-forward），**絕不 force**。

M5 → **回報**，並附上部署後待辦（寫在 deploy log）。

---

## 附：回復（只在 Oscar 決定時執行，本手冊不執行）

- R0～R6 依規格 §15.2。資料回復（R2、R3）一定要在程式 revert（R4）之前。
- R5 要用 `$DEP/tool/legacy_validate_snapshot.py`（與 W1 同一個檔），在同一個 canonical 路徑 `--root $MAIN` 取得回復後的結果：

  ```sh
  python3 $DEP/tool/legacy_validate_snapshot.py compare --w1 $DEP/w1/legacy-validate-w1.json --after <R5 結果> --root $MAIN --op <X> --report <報告>
  ```

- W1 時記錄的 `which python3` 與套件版本，在 R5 時必須相同。
- R6 刪除 `locks/maintenance.yaml` 是人工步驟，需要授權，並記錄在回復報告中。
