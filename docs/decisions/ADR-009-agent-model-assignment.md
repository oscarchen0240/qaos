# ADR-009 · Agent 模型分配：判斷用 Opus、產出用 Sonnet；高風險 TC 加一道 Opus 抽查

- **Status**: Accepted — 2026-10-01，Oscar 決定。取代 `MODEL-ROUTING-POLICY.md`（2026-09-14）中「預設 Sonnet、Opus 只限三種例外」與 §5 各 agent 預設模型表；該文件 §2.4（不得用升模型補 spec 缺口）仍有效。
- **Context**:
  - 盤點時沒有任何地方寫死模型：`agents/*.yaml` 無 model 欄位、`.claude/agents/` 只有一份 `qaos-test-designer.md` 也沒寫；`engine.py` 不呼叫模型。實際派發 130 次未帶 `model`，跟著主 session 的模型跑（主 session 過去大多是 Sonnet，所以看起來「全部 Sonnet」；主 session 一切到 Opus，所有 sub agent 就跟著變 Opus）。
  - Supervisor、Spec Analyst、Bug Analyst、Change Impact Analyst 一直由主 session 擔任，不是 sub agent。
  - 「找漏掉的情境」需要判斷力；TC 產出量大但範圍明確。
- **Decision**:
  1. **分配原則**：審視 spec、找缺漏矛盾、分析影響範圍、規劃測試策略、審查 TC、orchestrator → `opus`；依確認觀點展開 TC、格式轉換、撰寫 bug 單 → `sonnet`。同時負責分析與產出的 agent 先不改，標 `model_note`。
  2. **最終分配**（`agents/*.yaml` 的 `model` 欄位為唯一來源）：

     | agent | model | 備註 |
     |---|---|---|
     | supervisor | opus | 主 session 擔任；以 `/model` 決定，檔案無法強制 |
     | spec-analyst | opus | |
     | test-designer | sonnet | 混合職責，先不拆（理由見下） |
     | test-validator | opus | 同時達成 MODEL-ROUTING-POLICY §4「Validator 與 Designer 不同模型」 |
     | bug-analyst | sonnet | |
     | bug-validator | opus | |
     | change-impact-analyst | sonnet | 混合職責（impact＋compare），先不拆、維持現行值 |
     | regression-curator | sonnet | 入選條件已是明確規則 |
     | **tc-risk-reviewer（新增）** | opus | 見 3 |
  3. **高風險 TC 抽查**：新增 `agent-tc-risk-reviewer`。`applies_to_areas`（目前 CASHFLOW／CASHOUT／TXLOG／DAILYREPORT）內的 run，Runtime 在 Validator task 後插入 `<after>RR`（gate `G-RISK`），四個會產出 TC 的 workflow 都宣告 `risk_review`。
     - 五個面向（邊界值／異常流程／併發／重複提交／權限）逐一給結論；沒有 spec 依據的建議必須 `needs_clarification: true`，不得寫出預期結果。
     - **只提建議**：不改 TC、不判 PASS/FAIL；`G-RISK` 只檢查結構（審的是 Validator PASS 的那份 draft、五面向齊全、引用可追溯）。結果附在 ACTIVATE／APPLY_CHANGE 核准單的 summary 與 diff_summary，由 Human 決定要不要另起 run 或開 CLR。
     - **為什麼不併進 Test Validator**：Validator 只能對照 spec 判斷，契約要求 Negative／Edge「不過度」；Validator 的 issue 會擋關；Validator 只看當次 draft。三者都和「只提建議、可涵蓋 spec 沒寫的情境」衝突。
  4. **派發一致性**：每個非 Supervisor agent 都有 `.claude/agents/qaos-<name>.md`，frontmatter `model` 必須等於 yaml 的 `model`（`tests/test_wf_y_zzz_risk_review.py::test_70` 檢查）。wrapper 只指向 yaml 契約，不另寫角色 prompt。派發時用對應的 `subagent_type`，不再用 general-purpose 加契約全文。
- **為什麼 Test Designer 先不拆成 strategist＋designer**：拆分要新增 artifact、gate 與 workflow 節點，交接時 Sonnet 容易自行補細節（TC-DAILYREPORT-046 型風險）。先讓兩道 Opus 審查（Validator＋Risk Reviewer）跑 2～3 個 area，若漏掉的多半是「整類情境沒想到」再拆；若多半是展開時寫錯，拆分沒有幫助。
- **Consequences**:
  - schema：`TaskId` 放寬為 `^T[0-9]+[A-Z]{0,2}$`（順帶修好 `analysis_review=required` 時 `T2R` 存不進 run.yaml 的既有問題）；`GateId` 加 `G-RISK`；envelope 加 `TCRiskReview`（`ART-TRR`）；agent 契約加 `model`／`model_note`／`applies_to_areas`；workflow 定義加 `risk_review`；action registry 加 `REVIEW_TESTCASE_RISK`。
  - engine：`_expand_tasks` 依 spec 所在 area 決定是否插入；核准單附抽查結果；整批 reject 退回 Designer（排除 Reviewer），抽查 task 重設待重跑。
  - 既有、進行中的 run 不受影響（是否插入在 run 建立時決定）。
  - MR !1 code review（Codex 第一輪）修正：①ACTIVATE_TESTCASE／APPLY_CHANGE 整批 reject 一律退回 Test Designer（`to_agent`）——spec-change-impact 原本會誤退回 T4 CIA compare（MR 前就存在），Designer／Validator／RR 都不重跑；其他核准（suite 成員、bug）維持退回最近的產出者；②area 改由 `store.run_area` 判定，依序看 run 的 spec_id、manual record 的 spec_hint（皆取 spec 所在目錄）、manual record 的 functional_area（須為有效 area 代碼，空白不算），判定不了就拒絕建 run，不把「未知」當成「不需抽查」；③G-RISK 綁定 spec 版本（須與 Validator 審過的 draft 及 run 目標版本一致）；④空白 spec_basis 不算依據；⑤引用 ACTIVE TC 要看 ACTIVE 版本本身的狀態與 area，不只看 ID 前綴。
  - 成本：每個高風險 run 多一次 Opus 呼叫；Validator 由 Sonnet 改 Opus。Designer（輸出量最大）維持 Sonnet。
  - Opus 不進 CI 熱路徑（沿用 MODEL-ROUTING-POLICY §3 Phase 5）。
