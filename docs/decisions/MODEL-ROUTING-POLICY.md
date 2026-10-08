# Model Routing Policy — 預設 Sonnet，升級是例外

> **狀態：部分取代（2026-10-01）**——各 agent 的模型分配改依 [ADR-009](ADR-009-agent-model-assignment.md)（判斷用 Opus、產出用 Sonnet，新增 tc-risk-reviewer）；本檔 §0 第 1～2 點、§1 對照表中的模型結論、§5 預設模型表**不再適用**。§2.4（不得用升模型補 spec 缺口、假設不得默默變成 expected）與 §3 Phase 5「Opus 不進 CI 熱路徑」**仍有效**。原文保留供追溯。  
> 原狀態：現行政策（2026-09-14）。給 Claude Code / 實作者直接遵守。  
> **不是**新模組、不是 Phase 2/3 開發項目、不改 Master Architecture 的五層。  
> 來源：GPT 的 QAOS 模型路由建議 × 依本專案現況收斂後的採用版。

---

## 0. Claude Code 先讀這段

你接下來實作 QAOS（Phase 3 Agent、skill、workflow、修 Runtime）時：

1. **預設用 Sonnet。** 不要因為「這是複雜 Agent System」就全程 Opus。
2. **只有下面 §2 的三種狀況才切 Opus。** 除此之外不升。
3. **現在不要實作 Model Router / complexity check / Agent 自動申請 Opus。**
4. **現在不要做「Designer 與 Validator 不同模型」的工程。** 時機見 §4。
5. **Spec 模糊不准用升模型來補完。** 一律 `[NEEDS_DECISION]` / Clarification，問 Human。
6. **假設不得默默變成 expected。** 未被 `RESOLVE_AMBIGUITY` 覆蓋的 assumption，必須 `needs_human_confirmation: true`，不得進 ACTIVE。實例：`TC-DAILYREPORT-046`。

可靠性靠既有 invariant，不靠模型比較聰明：

- No Artifact, No Transition
- Structural Gate / State / Permission / ID / Commit = `tools/qaos`（非 LLM）
- Semantic Gate = 獨立 Validator artifact
- Human owns business decisions

---

## 1. 兩份建議的對照（採用哪一邊）

| 主題 | GPT 建議 | 本專案採用 |
|---|---|---|
| Sonnet 能不能做 QAOS 大量工作 | 能，而且應該 80% Sonnet + 20% Opus | **採用方向**：預設 Sonnet，Opus 是例外 |
| 可靠性從哪來 | Schema + Rule + Gate + Traceability + Human，不要只靠 LLM Judge LLM | **採用**。這已是 ADR-001 / ADR-002 |
| Supervisor | 用 Sonnet；不要做成「超聰明 Opus 大腦」 | **採用**。Supervisor 只做分類、routing 建議、Summary |
| Agent 自己決定升 Opus | 禁止；由 Supervisor / Router 控制 | **採用禁止**。但 **現在沒有 Router**，升級由 Human 切模型 |
| 每個 Agent 綁死一個 model | `.claude/agents/*.md` 寫 `model: sonnet` / `opus` | **延後**到 Phase 3 生成 agent md 時再加一行。現在不為此改架構 |
| 建 Model Routing Layer（Allowed Models、Cost Policy、Fallback…） | 現在就寫進 Master Architecture | **不採用（現在）**。先一頁政策。等 run log 證明規則後再收進架構 |
| complexity check → 自動升 Opus | Task 分流 Normal/Critical | **不採用（現在）**。沒有可執行的複雜度檢測，會變成 prompt 願望 |
| Designer / Validator 都 Sonnet | 兩者都固定 Sonnet | **現在不拆、也不規定兩者都必須 Sonnet。** Phase 3 兩邊都變 LLM 時再拆，見 §4 |
| Architecture Review 固定 Opus | 常駐 Opus Reviewer | **部分採用**：只有「改架構 / 跨檔案 architecture audit」才用 Opus，不當常駐服務 |
| 模糊 Requirement | 必須停，問人 | **採用，且優先於升模型** |

GPT 講的是「成熟多 Agent 系統的理想路由」。本專案 Phase 1 已核准、Phase 2 Runtime 已能跑真實 Spec。下一步是 **照 contract 實作**，不是再開一層作業系統。

---

## 2. 現行規則（現在立刻生效）

### 2.1 預設

| 工作 | 模型 |
|---|---|
| 寫 / 改 schema、CLI、hook、workflow yaml、docs、測試 | Sonnet |
| Spec Analyst、Test Designer、Bug Analyst、Regression Curator、Change Impact（日常） | Sonnet |
| Supervisor 分類 task、寫 WorkflowSummary | Sonnet |
| 一般 coding / refactor | Sonnet |
| 一般 debug（單一 artifact / 單一 gate 失敗） | Sonnet |

### 2.2 只有這三種切 Opus

1. **改架構決策**：architecture、state machine、permission、agent 邊界、workflow 依賴衝突。
2. **Validator 語義失敗達到上限仍修不好**：`max_validation_iterations`（預設 3，NEEDS_DECISION-06）。升 **這一次修訂**，不是把整個 Agent 改籍。
3. **跨多檔 / 跨 workflow 的 architecture audit**：例如「整個系統有沒有 inconsistency / deadlock / traceability 斷裂」。

三種以外（含「這題好像很難」「Spec 寫不清楚」）**不准升 Opus**。

### 2.3 升級權

- **現在：Human 切模型。** Agent / Supervisor 不得自行申請 Opus。
- 升級必須能事後解釋是 §2.2 的哪一條。
- 建議（有做再做，不阻擋開發）：在該次 `runs/<run_id>/audit.log` 留一筆 `model_escalation`：觸發條件、升完是否比較好（PASS / 少假設 / 少被 Human 改）。沒有這份 log，以後不得自動升級。

### 2.4 永遠不准用升模型解決的事

- Spec 缺口、欄位語意不明、acceptance 未定義
- 「看起來合理」的業務假設（例：未兌現金額是否受結算日期限制）
- Designer 與 Validator 互相同意但缺少 spec 依據

對應既有規則：`agents/test-validator.yaml` 要求——assumption 未標 `needs_human_confirmation: true`、也沒有經核對有效的 `resolved_by_approval` → **blocker**；依賴未定事項卻寫成確定斷言 → **major**。依賴未定決策點（E3～E5）而以 exploratory 呈現的斷言是合法的，不因未被 `ApprovalDecision(RESOLVE_AMBIGUITY)` 覆蓋而判 blocker（需求 A 第 1 章 §3.6；2026-10-08 起）。

實例（必須當成反面教材，不要重演）：

- `TC-DAILYREPORT-014`：不完整週的期間顯示、範圍外同週營業日是否計入——Spec 未定義，只准驗無歧義的那一列，或開 Clarification。
- `TC-DAILYREPORT-046`：Spec 只說未兌現「不受週期影響、累計至查詢當下」，**沒說不受結算日期限制**。模型假設「含 200」。Human 已裁定：**結算日期仍是篩選條件，只算範圍內** → expected 應為不含該 200。此類假設不得 `needs_human_confirmation: false` 就進 ACTIVE。

---

## 3. 未來怎麼長（同一原則，升級權慢慢交給 Runtime）

原則不變：**預設 Sonnet，Opus 永遠是例外。**  
變的是誰按升級鈕、按什麼數字按。新規則只能來自 run log，不能來自「覺得應該自動」。

| 階段 | 預設 | 誰決定升級 | 比現在多什麼 | 不要做什麼 |
|---|---|---|---|---|
| **現在〜Phase 3 剛通** | Sonnet | Human | 只有 §2.2 三條；能記 escalation log 更好 | 不建 Router；不拆 Designer/Validator 模型 |
| **Phase 3 穩定**（同一類真實 Spec 跑過 2～3 份） | Sonnet | Runtime + Human | 「三次 FAIL」可由 Runtime 升**一次**；agent md 可寫 default model | 不按 complexity 自動升 |
| **Phase 4**（Change Impact / Regression） | Sonnet | Runtime | 僅當 VersionComparison / 影響面與 Registry 對不上，升**那一次 compare** | 不把 CIA 整顆改成 Opus |
| **Phase 5**（CI、量大） | 規則優先，其次 Sonnet | 幾乎不升 | 高風險 TC 抽樣複核（`risk: high` / 有 assumption / 有 NEEDS_DECISION） | Opus 不准進 CI 熱路徑 |
| **Phase 6**（真的自治） | Sonnet 工人 + 限額 Opus | 只認 log 裡的條件 | 可有 `max_opus_escalations`（建議每 run 1–2）；override 率門檻沿用 roadmap（建議 < 10%） | Agent 自己申請 Opus；為省錢拿掉 Human Approval |

Phase 6 的 Model Router 只有在前面數字穩了才值得做。現在寫進 Master Architecture 會變成空政策。

---

## 4. Designer 與 Validator 要不要不同模型

### 現在：不做

現況仍是人在 loop 裡（上一輪真實跑法：人扮 Designer、獨立 subagent 扮 Validator）。同源偏誤的前提是 **兩邊都是同一顆模型在寫、在審**。還沒發生，不為此做工程。

`TC-DAILYREPORT-046` 漏過的主因是 **Spec 缺口被寫成確定 expected**，不是同模型互拍。換 Validator 用 Opus 也可能接受同一套推論。先修「假設必須擋下來問人」。

同源偏誤的既有緩解（已在架構裡，繼續遵守即可）：

- Validator **只讀** SPEC + Draft（+ Report 的 coverage matrix），不讀 Designer 推理過程（見 `agents/test-validator.yaml` `forbidden_actions`）
- Phase 3 eval 必須包含：**故意錯誤的 Draft 一定被抓到**（`docs/architecture/08-roadmap.md` Risks）

### Phase 3 兩邊都改由 LLM 產出時：做，而且只要一行

時機：`Sonnet Designer → Sonnet Validator → Gate` 即將發生。

做法（到時才做）：

- `agents/test-designer.yaml` / 生成的 `.claude/agents/test-designer.md` → `model: sonnet`
- `agents/test-validator.yaml` / `.claude/agents/test-validator.md` → **先用不同模型**（Opus，或至少不要與 Designer 同一顆）
- 等「故意錯 Draft」eval 通過後，再決定 Validator 能否降回 Sonnet

不要為此先做 routing 層、不要現在改五層架構。

---

## 5. Agent 預設模型（Phase 3 生成 `.claude/agents/*.md` 時才寫）

現在 `agents/*.yaml` **不必**為了本政策大改。到 Phase 3 從 yaml 生成 md 時加上：

| Agent | 預設模型 | 備註 |
|---|---|---|
| QA Supervisor | sonnet | 控制流程，不解決業務內容 |
| Spec Analyst | sonnet | 歧義 → Clarification，不猜 |
| Test Designer | sonnet | — |
| Test Validator | 與 Designer **錯開**（見 §4） | 不是永遠 Opus |
| Bug Analyst | sonnet | — |
| Bug Validator | 與 Bug Analyst **錯開**（同一時間點） | — |
| Change Impact Analyst | sonnet | 僅 §3 Phase 4 那一次 compare 可升 |
| Regression Curator | sonnet | — |
| Architecture review（臨時任務，非常駐 Agent） | opus | 對應 §2.2 第 1、3 種 |

禁止：

- Agent prompt 寫「若你覺得困難就改用 Opus」
- Supervisor 把「看起來複雜」當成升 Opus 條件

---

## 6. 與現有架構的關係（不要重做）

本政策 **依附** 既有設計，不取代：

| 已有 | 本政策只補充 |
|---|---|
| ADR-002：Supervisor = LLM 分類 + Runtime 執行 Gate/State/Permission | Runtime 也不負責「覺得該用哪個模型」（現在） |
| 8 Agent Role + Deterministic Runtime | 不新增 Architecture Reviewer 常駐 Agent |
| `max_validation_iterations = 3` | 這是 Opus 例外 #2 的唯一計數器 |
| Quality Gate + Human Approval | 升模型不能繞過 Approval |
| Phase 3 DoD：真實 SPEC 跑通、每步有 artifact / audit | 模型選擇不得變成 Phase 3 範圍膨脹 |
| Phase 6 前提：override 率夠低才准更自治 | 自動 Model Router 同門檻 |

GPT 建議新增的「Model Routing & Escalation Policy」模組（Allowed Models、Cost Policy、Fallback…）**列為未來候選**，不是現在 deliverable。本檔就是目前的政策原文。

---

## 7. Claude Code 檢查清單

實作或開新對話時核對：

- [ ] 這次任務是不是 §2.2 三種之一？不是 → 用 Sonnet，不要提議切 Opus
- [ ] 有沒有在建 Model Router / complexity 分流 / 常駐 Opus Reviewer？有 → 停，不在範圍
- [ ] 有沒有為「Designer ≠ Validator 模型」開獨立工作？Phase 3 雙 LLM 之前 → 停
- [ ] Spec / AC / 欄位語意不明？→ Clarification / `[NEEDS_DECISION]`，禁止寫死 expected
- [ ] 新的 assumption 是否 `needs_human_confirmation: true`，且未核准前不能 ACTIVE？
- [ ] Validator 是否仍被禁止讀 Designer 推理？
- [ ] 有切 Opus 的話，是否能指出 §2.2 哪一條？

---

## 8. 一句話

> **Opus = 架構 / 三次仍修不好 / 跨系統審查。**  
> **Sonnet = 工人。**  
> **規則 + Gate + 問人 = 正確性。**  
> **現在不做路由 OS；未來每一條自動升級都必須先被 run log 證明過。**
