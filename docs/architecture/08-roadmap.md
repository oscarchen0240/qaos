# 08 — MVP Scope & Roadmap

## MVP 範圍（對應 Brief §35）

| MVP | 流程 | Workflow | Agents | 必要 Gate | Human Approval | Phase 1 產出狀態 |
|---|---|---|---|---|---|---|
| MVP-1 | SPEC → Spec Analyst → Test Designer → Test Validator → Registry | `spec-to-testcase` | Supervisor, Spec Analyst, Test Designer, Test Validator | G-SPEC, G-DESIGN, G-TVAL, G-APPROVAL | ACTIVATE_TESTCASE（批次） | 已定義 |
| MVP-2 | SPEC + Execution + Evidence → Bug Analyst → Bug Validator → Human → Bug Repo | `spec-to-bug` | + Bug Analyst, Bug Validator | G-BVAL, G-APPROVAL | OPEN_BUG | 已定義 |
| MVP-3 | SPEC vN → vN+1 → Change Impact → TC versioning → Human | `spec-change-impact` | + Change Impact Analyst | G-IMPACT, G-TVAL, G-COMPARE, G-APPROVAL | APPLY_CHANGE | 已定義 |
| MVP-4 | Registry → Full / Hotfix / CI suites | `regression-generation` | + Regression Curator | G-REG, G-APPROVAL | UPDATE_SUITE_MEMBERSHIP | 已定義 |
| MVP-5 | Manual record → TC Draft → Validator → Candidate → Human → Suite | `manual-test-to-regression` | Test Designer(mode=manual) | G-DESIGN, G-TVAL, G-REG, G-APPROVAL | ACTIVATE_TESTCASE + UPDATE_SUITE_MEMBERSHIP | 已定義 |

MVP 排除：自動執行測試、外部工單系統同步、Agent 並行、autonomous planning、TestRail/Xray 匯出。

## Phase 2 — Foundation（Roadmap）

> 狀態（2026-09-13）：1–5 已完成（`bin/qaos`、`workflows/state-machines.yaml`、`tests/` 15 passed）；6（既有資料 fixture）：8 份 bug report 已轉為 `testcases/manual/MAN-20260913-001~008.yaml` + `evidence/bug-reports/EVD-0001~0008`（`tools/import_bug_reports.py ~/Desktop/mcp/bug-reports`，可重跑；專案已移至 `~/Desktop/qa-agent-os`）；對應 SPEC 草稿 `specs/_drafts/SPEC-ADMQUERY-001-v1.0.md`。**⏸ 2026-09-13 Human 指示：mcp-admin 這批暫停（不匯入 SPEC、不開 Clarification、不走 WF-D）；records 保留為日後 fixture。**`bug-kyc-*` 未納入（格式不同且結論為非 admin-srv 問題）。

目標：**沒有任何 LLM 也能跑的骨架**。

1. `schemas/` 完成 + `tools/qaos validate <file>`（jsonschema）
2. `tools/qaos` CLI：`new-run`、`transition`、`gate`、`approve`、`commit`、`trace`、`suites-of`、`id-alloc`
3. `testcases/registry/_counters.yaml` 與 ID 配發
4. 以手寫 fixture（一份 SPEC-AUTH v1.0、3 個 REQ、5 個 TC）走完 `spec-to-testcase` 的所有狀態轉換 **不用 agent**
5. git hooks / Claude Code hooks：PostToolUse 自動 validate artifact；PreToolUse 守衛寫入路徑
6. 既有資料遷移評估：`../test-cases/claim-bonus-event-reward/index.yaml`（16+ 案例）與 `../bug-reports/`（9 個 bug）作為 import fixture（[NEEDS_DECISION-10]）

DoD：`qaos` 能拒絕所有「違反 state machine / 缺 approval / 越權寫入」的操作，且有測試證明。

## Phase 2 後記：第一次用真實 Spec 跑（2026-09-13）

`SPEC-DAILYREPORT-001 v0.1`（場館日結報表）以「人扮 Spec Analyst / Test Designer、獨立 subagent 扮 Validator、Runtime 全程把關」跑完 WF-A，再把對應 bug 單拆成兩個 WF-B：

| 指標 | 結果 |
|---|---|
| Requirement | 17 條（2 條 major ambiguity；6 條 rejection 未定義 → 自動開 Clarification） |
| Test Case | 53 條（24 條非 happy-path、9 條 exploratory） |
| Validator 迭代 | FAIL(15 issues) → FAIL(4) → PASS(0)；第一輪抓到 7 個 blocker 全部成立（歧義案例未標假設、借用 AC、步驟不可獨立執行） |
| Bug | 2 張 PASS（related 非 duplicate），severity major/high |
| 停在 | APR-0003 ACTIVATE_TESTCASE、APR-0004/0005 OPEN_BUG — Human 決定 |
| Runtime 修正 | 臆測偵測對 boundary 誤判；structural retry 誤計 semantic 迭代；override-reject 未重設下游 task；Gate 可對既有 VALID artifact 重評 |

觀察：(1) Validator 獨立於 Designer 是有效的——它抓到的問題全是 Designer 自己看不到的盲點；(2) 「rejection_contract 未定義 → 自動開單問 PM」讓 6 個 Spec 缺口在設計階段就浮現；(3) 每包 spec 人工扮演成本約 2 小時，Phase 3 的 Agent 化值得做。

## Phase 3 — Agent Layer

1. 由 `agents/*.yaml` 生成 `.claude/agents/*.md`（tools allowlist 對映 allowed_actions）
2. Skills：`spec-analysis`、`test-case-design`（fork A + C）、`test-validation`、`bug-analysis`、`bug-validation`
3. 每個 Agent 各一組 eval：給定 input artifact → 輸出必須通過 Structural Gate
4. Supervisor skill（`/qaos <task>`）：task_type 分類 + 依 workflow yaml 逐 task dispatch

DoD：MVP-1 與 MVP-2 端到端可用真實 SPEC 跑通，每一步有 artifact 與 audit log。

## Phase 4 — Workflow Layer

1. `spec-change-impact`、`regression-generation`、`manual-test-to-regression` 三個 workflow 接上 Change Impact Analyst / Regression Curator
2. VersionComparisonReport 的 diff 渲染
3. ApprovalRequest 的人可讀呈現（CLI + Markdown；可選 Artifact 頁面）

DoD：MVP-3 / 4 / 5 跑通；`qaos trace` 可從任一 Bug 回溯到 SpecVersion。

## Phase 5 — Automation
CI 結果 ingestion（executions/ 自動寫入）、`EXECUTE_TEST` 解鎖給新 Agent（Test Executor）、automation eligibility 自動評估、stability 由執行歷史計算、TestRail/Xray/Jira 匯出。

## Phase 6 — Advanced Collaboration
Agent 並行（Test Designer 依 functional area 分片）、Supervisor 自主 re-planning、Agent Teams。前提：Phase 2–5 的 audit log 顯示 override 率 < 某門檻（建議 10%）。

## Risks

| 風險 | 影響 | 緩解 |
|---|---|---|
| LLM Validator 與 Generator 同源偏誤（同一模型互相「同意」） | Validation 失效 | Validator prompt 只給 SPEC + Draft，不給 Designer 的推理；Phase 3 eval 加入「故意錯誤的 Draft」必須被抓到 |
| Spec 品質差（ambiguity 多） | Requirement 停留 DRAFT，流程卡住 | RESOLVE_AMBIGUITY 批次呈現；Spec Analyst 提供 options |
| 檔案型 storage 在多 run 併發時衝突 | 資料損毀 | Phase 1–4 單 run 序列執行；Runtime 用 lock file |
| Human Approval 疲勞 | 全部 approve 不看 | 批次 approval + diff 摘要 + 只在 production change 才要求 |
| 外部 skill 更新破壞輸出格式 | Gate 大量 FAIL | Fork 而非直接依賴；schema 是唯一契約 |
| ID / version 由 Agent 亂編 | 追溯斷裂 | Runtime 配發，Agent 只能用 DRAFT 暫時 ID |
| Evidence 可被事後替換 | Bug 可信度 | sha256 + 不可變目錄 |

## Architectural Trade-offs

| 取捨 | 選擇 | 代價 |
|---|---|---|
| 檔案 + git vs 資料庫 | 檔案 + git | 查詢慢、無交易；換得可審、可 diff、Claude Code 原生 |
| Supervisor 全 LLM vs 拆 Runtime | 拆 Runtime | 多一個 CLI 要維護；換得 Gate / State / Permission deterministic |
| 每個 TC 逐案 Approval vs 批次 | 批次（可逐案） | 批次可能漏看；用 diff 摘要緩解 |
| 9 Agent vs 8 Agent | 8 | Manual Integrator 失去獨立 prompt 空間；換得少一份 Contract |
| YAML vs JSON | YAML source, JSON schema | YAML 解析歧異（Norway problem）；schema 驗證 + 字串加引號規則緩解 |
| Regression/Smoke/Hotfix 當 test_type vs 當 suite | 當 suite | 匯入既有資料需轉換 |
