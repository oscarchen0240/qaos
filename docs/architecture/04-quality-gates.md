# 04 — Quality Gates

> 每個 Gate = **Structural checks（Runtime、deterministic）** + **Semantic checks（Validator Agent / Human）**。Structural 全部通過才進入 Semantic。任何一項 FAIL → Gate FAIL，並產生對應 Report。

## Gate Matrix

| Gate ID | 位置 | Structural（Runtime） | Semantic（執行者） | FAIL 時產物 | FAIL 路由 |
|---|---|---|---|---|---|
| **G-SPEC** Spec Analysis Gate | Spec Analyst 之後 | SpecAnalysis + RequirementModel 通過 schema；每個 REQ 有 ≥1 AC；`spec_id@spec_version` 存在且 `content_hash` 相符；每個 REQ 有 `spec_reference`（章節/行） | Supervisor checklist（非 LLM 判斷，僅結構 checklist）：Requirements identified、AC identified、Ambiguities identified（可為空但欄位必存在）、Constraints identified | `GateFailure` 附缺項 | 回 Spec Analyst，max 2 次後 Human |
| **G-DESIGN** Test Design Gate（self-check） | Test Designer 之後、Validator 之前 | TestCaseDraft + TestDesignReport schema；每個 TC 有 ≥1 `requirement_ids` 且 ID 存在於 RequirementModel；`expected_result` 非空；`steps` ≥1；`design_technique[]` 非空；Report 的 coverage matrix 覆蓋所有 ACTIVE Requirement（未覆蓋者需列於 `uncovered_with_reason`）；Draft 內無同 `title+steps` hash 重複 | Test Designer 自檢 checklist（記錄在 TestDesignReport.self_check）：negative 考慮、boundary 考慮、無 unsupported assumption 宣告 | `GateFailure` | 回 Test Designer（不計入 Validation 迭代） |
| **G-TVAL** Test Validation Gate | Test Validator 之後 | TestValidationReport schema；`result ∈ {PASS, FAIL}`；FAIL 時 `issues[]` ≥1 且每個 issue 含 8 個必填欄位（Brief §7.4）；每個 issue 的 `testcase_id` 存在於被驗證的 Draft | Test Validator：No SPEC mismatch、No requirement mismatch、Expected Result 有 spec 依據、Steps 可執行、Traceability 完整、無 critical ambiguity、無重複、Negative/Boundary 合理 | TestValidationReport(FAIL) | 回 Test Designer；iteration > max → Human Override |
| **G-BVAL** Bug Validation Gate | Bug Validator 之後 | BugDraft schema；`spec_id@spec_version`、`requirement_id` 存在；`evidence_ids` ≥1 且每筆 Evidence 檔案存在、sha256 相符；`reproduction_steps` ≥1；`severity`、`priority` 在 enum 內 | Bug Validator：真的違反 SPEC、expected 有 SPEC 依據、actual 被 Evidence 支撐、步驟足以重現、severity/priority 合理、無 duplicate（查 `bugs/`）、非單純 ambiguity | BugValidationReport(FAIL / AMBIGUITY / DUPLICATE) | 回 Bug Analyst / 升級 Human |
| **G-IMPACT** Change Impact Gate | Change Impact Analyst 之後 | ChangeImpactReport schema；from/to SpecVersion 皆存在；每個 ACTIVE Requirement 都出現在 `requirement_diff`；每個引用該 spec 的 ACTIVE TC 都出現在 `testcase_impact`（完整性檢查由 Runtime 用 trace 反查） | Supervisor checklist：每個 `affected` 有 reason 與 affected_requirement_ids | GateFailure | 回 Change Impact Analyst |
| **G-COMPARE** Version Comparison Gate | 新版 TC 通過 G-TVAL 之後 | VersionComparisonReport schema；每個 impacted TC 都有 `unchanged/changed/added/removed` 判定 | — | GateFailure | 回 Change Impact Analyst |
| **G-REG** Regression Gate | Regression Curator 之後 | RegressionProposal schema；每個 membership 的 TC `status = ACTIVE`（VALIDATED + APPROVED）；version 存在；`justification` 非空；`risk_tag` 非空；Suite 內無重複 `testcase_id`；CI suite 的 TC 必須 `ci_eligible=true` 且 `execution_mode≠manual` | Human（Approval 時審視 justification） | GateFailure | 回 Regression Curator |
| **G-APPROVAL** Human Approval Gate | 任何 production change 之前 | ApprovalRequest schema；`decision` 存在且 `decided_by` 非 agent；`override` 必附 `rationale` | Human | — | reject → 回前一 generator |

## G-DESIGN 的行為契約檢查（2026-09-13 新增，依 `RECOMMENDATIONS-negative-exploratory.md`）

由 Runtime 依 Requirement 的 `behavior_kind` / `inputs` / `states` / `rejection_contract` 機械檢查（`tools/qaos/gates.py::g_design`）：

| 規則 | 觸發 | 結果 |
|---|---|---|
| high-risk 覆蓋 | ACTIVE ∧ `risk=high` 的 REQ 沒有任何 negative / boundary / error_guessing 案例 | FAIL，除非 `uncovered_with_reason` 以 `NO_REJECTION_CONTRACT:` 開頭 |
| rejection 類 | `behavior_kind=rejection` 的 REQ 沒有 `test_types` 含 negative 的案例 | FAIL |
| 邊界 | `inputs[].constraints` 有 min/max/min_length/max_length 但無 `boundary_value` 案例 | FAIL |
| 狀態 | `states[]` 非空但無 `state_transition` 案例 | FAIL |
| 臆測偵測 | （舊格式需求，沒有 `decision_points`）`rejection_contract.defined=false` 的 REQ，以 `negative` / `error_guessing` **技術**寫的案例沒有 `assumptions`（寫成了確定規則）。boundary / requirement_based 案例不受此限（其 expected 來自成功路徑條文）。新格式需求改依需求 A 第 1 章 §3.6 逐決策點檢查（negative 技術的 TC 沒有 `decision_refs` → FAIL；依賴 E3～E5 的斷言必須 exploratory） | FAIL |
| 假設外顯 | `assumptions[]` 每筆必須 `needs_human_confirmation: true`（已由核准解決、填 `resolved_by_approval` 的歷史假設除外；其有效性由 Validator 核對）且指向本 TC 的 REQ | FAIL |
| 上限 | 單一 REQ 的 exploratory > 3 | FAIL |
| 統計一致 | `technique_summary` 與 Draft 實際計數不符 | FAIL |
| 整份 | 沒有任何非 happy-path 案例 | FAIL |
| 佔比 | `mode=spec` 且 ≥ 5 條時 exploratory > 50% | 不 FAIL；PASS 後建立 `NEEDS_DECISION`（先補 Spec 還是繼續）。manual / change 模式不套用 |

補充：`mode=manual` / `change` 的覆蓋範圍只看本 Draft 涉及的 REQ（不要求覆蓋整份 RequirementModel）；manual 模式下 Validator 另要求「Designer 不得補充人工紀錄中不存在的行為」，這一項只能由 Semantic 層判斷。

配套：G-SPEC PASS 時，`rejection_contract.defined=false` 的 REQ 自動開一張不阻塞的 Clarification 問 PM；ACTIVATE approve 時 Runtime 把該 TC 的 `assumptions[].resolved_by_approval` 填上。

## Gate 與 Principle 對應

| Principle | 由哪個 Gate 保證 |
|---|---|
| No Artifact, No Transition | 所有 Gate 的 Structural 層 |
| No Validation, No Registry | G-TVAL（TC）、G-BVAL（Bug） |
| No Approval, No Production Change | G-APPROVAL |
| No Evidence, No Formal Bug | G-BVAL Structural（evidence_ids ≥1 + hash） |
| No Traceability, No Accepted Test Case | G-DESIGN + G-TVAL |
| Suite references, never copies | G-REG（schema 不允許 steps 欄位出現在 membership） |
| Version everything | Structural 層一律要求 `version` 欄位 |
| Explicit permissions | Permission Guard（不是 Gate，是 dispatch 前檢查） |

## Severity 分級（Validation Report 共用）

| severity | 意義 | 對 Gate 的影響 |
|---|---|---|
| `blocker` | 與 SPEC 直接矛盾、Evidence 缺失、Traceability 斷裂 | 單一即 FAIL |
| `major` | 覆蓋缺口、步驟不可執行、明顯重複 | 單一即 FAIL |
| `minor` | 措辭、可讀性、優先級建議 | 不影響 PASS，記錄為 `advisories[]` |

## Ambiguity 分級

| level | 定義 | 處理 |
|---|---|---|
| `critical` | 無法決定 expected result | Requirement 停留 DRAFT；Test Designer 不得為其設計 TC；產生 `ApprovalRequest(RESOLVE_AMBIGUITY)` |
| `major` | 可設計 TC 但 expected result 有 ≥2 合理解讀 | 舊格式需求：TC 標記 `assumptions[]`（`needs_human_confirmation: true`），以 exploratory 呈現；Validator 不因未裁決而 FAIL，寫成確定斷言才 FAIL。新格式需求依決策點有效狀態判斷（需求 A 第 1 章 §3.6：依賴 E3～E5 的斷言必須 exploratory） |
| `minor` | 不影響 expected result | 記錄即可 |
