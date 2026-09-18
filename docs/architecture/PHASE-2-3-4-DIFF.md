# Phase 2 / 3 / 4 差異與工作目的

> 來源：`docs/architecture/08-roadmap.md`  
> 產出日期：2026-09-14  
> 用途：快速對照各 Phase 在做什麼、差在哪、驗收是什麼

---

## 一句對照

| | Phase 2 Foundation | Phase 3 Agent Layer | Phase 4 Workflow Layer |
|---|---|---|---|
| **目的** | 先有不會被 LLM 搞壞的骨架 | 讓 LLM Agent 真的能跑前兩條主流程 | 補齊其餘三條業務流程 + 人看得懂的呈現 |
| **主角** | `tools/qaos`（程式） | Spec / Test / Bug 相關 Agent + Skills | Change Impact、Regression、Manual→Suite |
| **LLM？** | **刻意不要靠 LLM** | **開始靠 LLM 產內容** | LLM + 更完整的 workflow 串接 |
| **對應 MVP** | 骨架可支撐全部 | **MVP-1、MVP-2** | **MVP-3、4、5** |
| **DoD** | 違規操作會被擋，有測試證明 | 真實 SPEC 端到端跑通，每步有 artifact／audit | 三條新 workflow 跑通；Bug 可 trace 回 Spec |

---

## Phase 2 — Foundation

**目標：** 沒有任何 LLM 也能跑的骨架。

**工作內容：**

1. `schemas/` 完成 + `tools/qaos validate <file>`（jsonschema）
2. `tools/qaos` CLI：`new-run`、`transition`、`gate`、`approve`、`commit`、`trace`、`suites-of`、`id-alloc`
3. `testcases/registry/_counters.yaml` 與 ID 配發
4. 以手寫 fixture 走完 `spec-to-testcase` 的所有狀態轉換（**不用 agent**）
5. git hooks / Claude Code hooks：自動 validate、守衛寫入路徑
6. 既有資料遷移評估（import fixture）

**DoD：** `qaos` 能拒絕所有「違反 state machine / 缺 approval / 越權寫入」的操作，且有測試證明。

**一句話：** Phase 2 保證「錯的進不去」。

---

## Phase 3 — Agent Layer

**目標：** 把人扮演的角色換成 Agent，但仍走 Phase 2 的 Gate／Approval。

**工作內容：**

1. 由 `agents/*.yaml` 生成 `.claude/agents/*.md`（tools allowlist 對映 allowed_actions）
2. Skills：`spec-analysis`、`test-case-design`、`test-validation`、`bug-analysis`、`bug-validation`
3. 每個 Agent 各一組 eval：給定 input artifact → 輸出必須通過 Structural Gate
4. Supervisor skill（`/qaos <task>`）：task_type 分類 + 依 workflow yaml 逐 task dispatch

**DoD：** MVP-1 與 MVP-2 端到端可用真實 SPEC 跑通，每一步有 artifact 與 audit log。

| MVP | 流程 |
|---|---|
| MVP-1 | SPEC → Spec Analyst → Test Designer → Test Validator → Registry |
| MVP-2 | SPEC + Execution + Evidence → Bug Analyst → Bug Validator → Human → Bug Repo |

**一句話：** Phase 3 保證「對的內容可以由 Agent 產出」。

> Phase 2 後記觀察：人扮一包 Spec 約 2 小時，所以 Phase 3 的 Agent 化值得做。

---

## Phase 4 — Workflow Layer

**目標：** 不只「新增 TC／開 Bug」，還能處理改版影響、回歸套件、人工案例入庫。

**工作內容：**

1. `spec-change-impact`、`regression-generation`、`manual-test-to-regression` 三個 workflow 接上 Change Impact Analyst / Regression Curator
2. VersionComparisonReport 的 diff 渲染
3. ApprovalRequest 的人可讀呈現（CLI + Markdown；可選 Artifact 頁面）

**DoD：** MVP-3 / 4 / 5 跑通；`qaos trace` 可從任一 Bug 回溯到 SpecVersion。

| MVP | 流程 |
|---|---|
| MVP-3 | SPEC vN → vN+1 → Change Impact → TC versioning → Human |
| MVP-4 | Registry → Full / Hotfix / CI suites |
| MVP-5 | Manual record → TC Draft → Validator → Candidate → Human → Suite |

**一句話：** Phase 4 把「變更、回歸、人工匯入」這類長期營運流程接起來。

---

## 串起來怎麼看

```text
Phase 2  Runtime／規則／擋錯
    ↓
Phase 3  Agent 自動跑「Spec→TC」「Spec→Bug」
    ↓
Phase 4  再跑「Spec 變更影響」「組回歸套件」「人工測進入 Suite」
```

| Phase | 角色比喻 |
|---|---|
| 2 | 地基（沒有工人也能擋錯） |
| 3 | 工人上場跑兩條主流程 |
| 4 | 把整廠其餘產線接起來 |

---

## 與後續 Phase（參考）

| Phase | 重點 |
|---|---|
| Phase 5 Automation | CI ingestion、自動執行測試、eligibility／stability、外部系統匯出 |
| Phase 6 Advanced Collaboration | Agent 並行、Supervisor 自主 re-planning；前提 override 率夠低（建議 < 10%） |

MVP 排除（整個 roadmap 皆然）：自動執行測試、外部工單同步、Agent 並行、autonomous planning、TestRail/Xray 匯出——這些屬 Phase 5／6，不是 2–4 的範圍。
