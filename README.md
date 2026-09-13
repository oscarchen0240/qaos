# QA Agent Operating System (QAOS)

> 位置：`~/Desktop/qa-agent-os`（獨立專案，不屬於任何產品 repo；`product` 欄位區分 demo / mcp-admin / …）

**Agent + Artifact + Schema + Workflow + State + Quality Gate + Human Approval + Traceability** 的 QA 作業系統。

> 目前狀態：**Phase 1 已核准（ADR-004），Phase 2 — Foundation 進行中。**
> 入口文件：[`docs/architecture/00-architecture-review.md`](docs/architecture/00-architecture-review.md)
> 待決事項：[`docs/decisions/NEEDS_DECISION.md`](docs/decisions/NEEDS_DECISION.md)

## 十大原則
1. No Artifact, No Transition · 2. No Validation, No Registry · 3. No Approval, No Production Change · 4. No Evidence, No Formal Bug · 5. No Traceability, No Accepted Test Case · 6. Suite references, never copies · 7. Version everything · 8. Explicit permissions · 9. Human owns business decisions · 10. Correctness & auditability before autonomy

## Phase 1 產出
| 目錄 | 內容 |
|---|---|
| `docs/architecture/` | 00 Review、01 系統架構、02 資料模型+ERD、03 狀態機、04 Quality Gates、05 權限矩陣、06 目錄結構、07 Skill 評估、08 Roadmap/Risk、09 Human Approval |
| `docs/workflows/` | 5 個 Workflow 說明 + Mermaid |
| `docs/agent-contracts/` | Responsibility Matrix、Contract Matrix |
| `docs/decisions/` | 13 項 `[NEEDS_DECISION]`、ADR-001~003 |
| `agents/` | 8 個 Agent Contract（YAML，通過 schema） |
| `workflows/` | 5 個 Workflow Definition（YAML，通過 schema） |
| `permissions/` | Action Registry |
| `schemas/` | 35 個 JSON Schema（Draft 2020-12） |
| `tools/validate_phase1.py` | Phase 1 自洽性驗證 |

其餘目錄（`specs/ testcases/ testsuites/ bugs/ artifacts/ executions/ evidence/ approvals/ runs/ skills/ .claude/`）為 Phase 2 起使用的骨架，目前為空。

## Phase 2 產出（Runtime）
| 位置 | 內容 |
|---|---|
| `bin/qaos` / `tools/qaos/` | Deterministic Runtime CLI：`validate`、`id`、`run new/show/cancel`、`submit`、`gate`、`approve`、`approvals`、`trace`、`suites-of`、`spec import`、`evidence add`、`execution import`、`bug transition`、`bug index`、`clarification new/ask/answer/apply/withdraw/list`、`approval <id>`（渲染審批摘要到 approvals/<id>.md） |
| `workflows/state-machines.yaml` | 機器可讀狀態機（9 個 entity），Runtime 只允許此處列出的轉換 |
| `clarifications/` | 問 PM 的需求釐清單（依 product/area 分資料夾），`RESOLVE_AMBIGUITY` 時自動開單 |
| `testcases/manual/` + `evidence/bug-reports/` | 8 份既有 bug report 轉成的人工測試紀錄（MVP-5 輸入）；`tools/import_bug_reports.py <bug-reports 目錄>` |
| `specs/_drafts/` | 待 Human 確認後匯入的 SPEC 草稿 |
| `intake/` | 收件匣：原始文件分類與去向（`intake/README.md`） |
| `tools/manual-runs/` | Phase 3 前「人扮 Agent」產 artifact 的腳本（Spec Analyst / Test Designer / Bug Analyst）；Validator 由獨立 subagent 擔任 |
| `docs/templates/spec-template.md` | 給 Spec 作者的模板（§4「不該發生什麼」是重點） |
| `tests/` | 24 個端到端測試：WF-A / B / C / E 不用 Agent 走完全部狀態；證明 Runtime 拒絕越權、缺 approval、非法轉換、證據竄改、斷裂 traceability |
| `testcases/registry/_counters.yaml` | ID 配發（Runtime 專用） |

```bash
python3 -m pytest tests -q          # Phase 2 DoD
python3 tools/validate_phase1.py    # Phase 1 定義層自洽
bin/qaos --help
```

### 一次 run 的最小流程（Phase 3 前由人代替 Agent 提交 artifact）
```bash
bin/qaos spec import spec.md --spec-id SPEC-AUTH-001 --version 1.0 --product demo --area AUTH --by you@x
bin/qaos run new spec-to-testcase --input spec_id=SPEC-AUTH-001 --input spec_version=1.0 --by you@x
bin/qaos submit RUN-… T1 artifacts/requirements/RUN-…/ART-RM-….yaml   # Permission Guard + Structural
bin/qaos gate RUN-… T1                                                 # G-SPEC → requirements 持久化
…
bin/qaos approvals                                                      # 待你決定的事
bin/qaos approve APR-0001 --decision approve --by you@x [--per-item TC-AUTH-005:reject]
bin/qaos trace TC-AUTH-001
```
