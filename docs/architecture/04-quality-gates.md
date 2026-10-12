# 04 — Quality Gates

> 每個 Gate = **Structural checks（Runtime、deterministic）** + **Semantic checks（Validator Agent / Human）**。Structural 全部通過才進入 Semantic。任何一項 FAIL → Gate FAIL，並產生對應 Report。

## Gate Matrix

| Gate ID | 位置 | Structural（Runtime） | Semantic（執行者） | FAIL 時產物 | FAIL 路由 |
|---|---|---|---|---|---|
| **G-SPEC** Spec Analysis Gate | Spec Analyst 之後 | SpecAnalysis + RequirementModel 通過 schema；每個 REQ 有 ≥1 AC；`spec_id@spec_version` 存在且 `content_hash` 相符；每個 REQ 有 `spec_reference`（章節/行）；REQ ID：同 spec 已持久化的可沿用，新 ID 須為 `REQ-<AREA>-<序號>`、不超過計數器、不屬於同 area 其他 spec（`requirement_id_issues`）；AC ID 依所屬 REQ 推導（見 `02-data-model.md` §5；`ac_id_issues`），一條 REQ 有 10 個以上 AC 只記 advisory 不擋 | Supervisor checklist（非 LLM 判斷，僅結構 checklist）：Requirements identified、AC identified、Ambiguities identified（可為空但欄位必存在）、Constraints identified | `GateFailure` 附缺項 | 回 Spec Analyst，max 2 次後 Human |
| **G-DESIGN** Test Design Gate（self-check） | Test Designer 之後、Validator 之前 | TestCaseDraft + TestDesignReport schema；change 模式且 run 有 CIR：`supersedes_testcase` 只能取代 CIR 判定 affected 的 TC（見下方「change 模式的取代範圍」）；每個 TC 有 ≥1 `requirement_ids` 且 ID 存在於 RequirementModel；`expected_result` 非空；`steps` ≥1；`design_technique[]` 非空；Report 的 coverage matrix 覆蓋所有 ACTIVE Requirement（未覆蓋者需列於 `uncovered_with_reason`）；Draft 內無同 `title+steps` hash 重複 | Test Designer 自檢 checklist（記錄在 TestDesignReport.self_check）：negative 考慮、boundary 考慮、無 unsupported assumption 宣告 | `GateFailure` | 回 Test Designer（不計入 Validation 迭代） |
| **G-TVAL** Test Validation Gate | Test Validator 之後 | TestValidationReport schema；`result ∈ {PASS, FAIL}`；FAIL 時 `issues[]` ≥1 且每個 issue 含 8 個必填欄位（Brief §7.4）；每個 issue 的 `testcase_id` 存在於被驗證的 Draft | Test Validator：No SPEC mismatch、No requirement mismatch、Expected Result 有 spec 依據、Steps 可執行、Traceability 完整、無 critical ambiguity、無重複、Negative/Boundary 合理 | TestValidationReport(FAIL) | 回 Test Designer；iteration > max → Human Override |
| **G-BVAL** Bug Validation Gate | Bug Validator 之後 | BugDraft schema；`spec_id@spec_version`、`requirement_id` 存在；`evidence_ids` ≥1 且每筆 Evidence 檔案存在、sha256 相符；`reproduction_steps` ≥1；`severity`、`priority` 在 enum 內 | Bug Validator：真的違反 SPEC、expected 有 SPEC 依據、actual 被 Evidence 支撐、步驟足以重現、severity/priority 合理、無 duplicate（查 `bugs/`）、非單純 ambiguity | BugValidationReport(FAIL / AMBIGUITY / DUPLICATE) | 回 Bug Analyst / 升級 Human |
| **G-IMPACT** Change Impact Gate | Change Impact Analyst 之後 | ChangeImpactReport schema；from/to SpecVersion 皆存在；每個 ACTIVE Requirement 都出現在 `requirement_diff`；每個引用該 spec 的 ACTIVE TC 都出現在 `testcase_impact`（完整性檢查由 Runtime 用 trace 反查） | Supervisor checklist：每個 `affected` 有 reason 與 affected_requirement_ids | GateFailure | 回 Change Impact Analyst |
| **G-COMPARE** Version Comparison Gate | 新版 TC 通過 G-TVAL 之後 | VersionComparisonReport schema；每個 impacted TC 都有 `unchanged/changed/added/removed` 判定；比較範圍與 Draft 身分（`_compare_coverage_issues`）；Draft 的取代範圍（與 G-DESIGN 共用） | — | GateFailure | 報告問題 → 回 Change Impact Analyst；只剩 Draft 超出 CIR 範圍 → `HUMAN_OVERRIDE`（見下方「G-COMPARE 失敗的出路」） |
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

## change 模式的取代範圍（2026-10-12 新增，RUN-20261012-001 事故）

`workflows/spec-change-impact.yaml` T2 的 constraint（unaffected 不得重產、obsolete 只列入 retire 建議）原本沒有機械檢查：Designer 修訂了 CIR 判定 unaffected 的 TC-REDPACKET-018、035，G-DESIGN 與 G-TVAL 都放行，到 T4 G-COMPARE 才 structural FAIL，而 T4 沒有路徑退回 T2，只能取消 run 重開（RUN-20261012-002）。

規則只看 CIR 與 Draft，由 `tools/qaos/gates.py::supersede_scope_issues` 判定，**G-DESIGN 與 G-COMPARE 共用同一個函式**（不會分歧）：

| 規則 | FAIL 條件 |
|---|---|
| 只能取代 affected | `supersedes_testcase` 指向的 TC 不在本 run CIR 的 `testcase_impact`，或 CIR 判定為 `unaffected`／`obsolete`（obsolete 只能在 VersionComparisonReport 列 retire 建議） |
| 版本相符 | `supersedes_testcase.version` ≠ CIR 的 `active_version` |
| 一張 TC 一筆新稿 | 同一張 TC 被兩筆以上 Draft 取代 |

- **G-DESIGN**：run 在設計 task 之前有本輪有效的 ChangeImpactReport 時套用，不看 Draft 自填的 `mode`（testcase-revision 沒有 CIR，不套用；spec-change-impact 找不到 CIR 直接 FAIL）。另外 Draft 的 `mode` 必須等於設計 task 的 mode（workflow 定義），不能以 `mode=spec` 繞過 change 模式的檢查。FAIL → 設計 task READY，Designer 修正，不計入 Validation 迭代。
- **G-COMPARE**：同一套規則仍保留（防線：修正前已通過 G-DESIGN、正在途中的 run）。

### G-COMPARE 失敗的出路

G-COMPARE 的問題分兩類（`gates.compare_issue_split`）：

1. **比較報告本身的問題**（漏列、對錯取代關係、`old_version` 不符、`new_draft_id` 不屬於本輪 Draft、新 TC 不是 `added`、`retire_recommendations` 不是 CIR obsolete 或是本輪 Draft 取代的 TC……）：Change Impact Analyst 重交報告即可修正 → 維持現行行為，只寫診斷、T4 READY。
2. **Draft 超出 CIR 範圍**（上表三條）：不論報告怎麼寫都會存在，READY 重試只會卡死。被超出範圍取代的 TC，報告仍必須照 Draft 寫——比較列恰好是取代它的各筆 Draft、對到 `supersedes_testcase` 的 TC 與版本；只豁免「`old_version` 等於 CIR 的 `active_version`」（版本不符時兩者互相矛盾）。報告本身沒有其他問題、只剩這一類時，`engine._escalate_compare` 記錄 structural FAIL、T4 停在 `GATE_FAILED`，並建立 `HUMAN_OVERRIDE`（`reopen_task=T2`），選項比照 Validator 迭代超限（`engine._route_back`）：

| 選項 | 決定 | Runtime 動作 |
|---|---|---|
| `override` | `--decision override`（必填 rationale） | 視為 G-COMPARE 通過：T4 DONE，推進到 T5 APPLY_CHANGE（由 Human 在核准單上看到全部取代）；WorkflowSummary 的 `overrides` 記錄此單 |
| `reject` | `--decision reject` | 退回 T2 再給一次迭代：本輪 G-TVAL 登記的 VALIDATED 版本 → DRAFT（比照 APPLY_CHANGE reject）、ChangeImpact `COMPARING → TEST_UPDATE_REQUIRED`、T2 iteration+1 READY、T3（含 T3RR）／T4 重設為 PENDING，之後以新的派發包重做 |
| `cancel` | `--decision approve --option cancel`（與 Validator 超限的 HUMAN_OVERRIDE 相同） | run CANCELLED |

兩類同時存在時先以診斷 FAIL 回報全部問題（報告問題修好後才升級），避免 override 帶著有問題的比較報告進 APPLY_CHANGE。

HUMAN_OVERRIDE 的 decision 與 option 必須一致（`engine._preflight_approval`，所有 HUMAN_OVERRIDE 皆適用）：`approve` 只代表取消，必須帶 `--option cancel`；`override`／`reject` 若帶 option 必須同名。原本 `approve` 不論 option 都會取消 run，CLI 容易誤觸。

修正前在 Validator 迭代超限選 override 的在途 run，ChangeImpact 可能停在 `TEST_UPDATE_REQUIRED`：G-COMPARE 升級後選 reject 不再轉換（已是該狀態），選 override 先補走 `VALIDATING → COMPARING` 再建 APPLY_CHANGE。

為何不另開新的核准類型：`HUMAN_OVERRIDE` 本來就涵蓋「Gate FAIL 但 Human 認為可接受」（`09-human-approval-flow.md`），`_after_override` 的 reopen／override／cancel 處理與 admin-ui 的選項呈現都可沿用；G-COMPARE 專屬的差異（不 materialize、撤回已登記版本、ChangeImpact 回退）以核准單所屬 task 的 gate 判斷。狀態機為此新增兩條 Human 轉換：TestCase `VALIDATED → DRAFT`、ChangeImpact `COMPARING → TEST_UPDATE_REQUIRED`（`03-state-machines.md`）。

同時修正：spec-change-impact 的 Validator 迭代超限選 `override` 時，ChangeImpact 原本停在 `TEST_UPDATE_REQUIRED`，T4 PASS 後建立 APPLY_CHANGE 會因 `TEST_UPDATE_REQUIRED → PENDING_APPROVAL` 不合法而失敗；現在 override 時比照 G-TVAL PASS 轉入 `COMPARING`。

測試：`tests/test_cia_supersede_scope.py`、`tests/test_p6_c01_fixes.py`。

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
