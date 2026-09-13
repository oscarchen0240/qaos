# 建議結論：Skill 策略與三大矛盾處置

> 狀態：**已採納（2026-09-13）** — 全部內容與 [ADR-004](ADR-004-phase1-decisions-approved.md) 一致（#02、#05、#09、Brief 矛盾 C5）。ADR-004 為事實來源；本文保留為推理紀錄。Claude 的補充意見見文末 §5。  
> 來源：Phase 1 審查後的人工建議整理  
> 相關：`07-skill-evaluation.md`、`NEEDS_DECISION.md`（02 / 05）、`ADR-003`、Action Registry `EXECUTE_TEST`

---

## 1. `ll0v0ll/test-case-designer` 為何用 Fork + Adapt

該 skill 與 QAOS 需求高度重合：分析先於生成、Review Gate、RTM、風險密度、六層設計技術、不臆測未定義需求。方法論值得保留，不必從零重寫。

但它不能原樣進系統，至少要改四處：

1. 輸出從 Markdown 十欄表 → QAOS 的 `TestCaseDraft` / `TestDesignReport` schema
2. 自編 `TC-001` → 只能用 `TC-DRAFT-<ulid>`，正式 ID 由 Runtime 配發
3. 互動式 Human Review → subagent 環境改成 autonomous，疑問寫進 `open_questions` / `assumptions`
4. `Requirement Ref` 不得自動造 REQ；必須指向 Spec Analyst 已建的 Requirement

### 策略比較

| 做法 | 為何不選 / 為何選 |
|---|---|
| 直接依賴 upstream | upstream 一改，Gate 會大量 FAIL；且輸出契約是 Markdown，不是 schema |
| 完全重寫 | 浪費已對齊 Brief 的方法論與 `allpairs.py` 等可執行件 |
| **Fork + Adapt** | 方法論進 `skills/vendor/`，輸出層改成 QAOS 契約；上游更新不會直接撞壞系統 |

### 附帶條件

- README 未標 License，fork 前須向作者確認；確認不了則改為「重寫但註明方法論出處」。
- 本機 `test-case-gen` 的「按 feature 累積 index」概念併入，補原 skill 缺的累積面向。
- `45ck` 的 `negative-test-designer`、`test-oracle-writer` 可作 `references/` 補充，不安裝整包。

**結論：Fork + Adapt 為 `test-case-design` skill 核心。**

---

## 2. 三大矛盾的建議處置

### 2.1 新 TC 進 Registry 要不要人審（NEEDS_DECISION-02）

**建議：B — 要，且支援批次核准**

- Validator PASS → 只進 `versions/`（狀態 `VALIDATED`）
- 正式 `ACTIVE` / 進 Registry 指標 → 需要 `ACTIVATE_TESTCASE`
- 一個 ApprovalRequest 可批多個 TC，可逐項 reject

**理由：** Principle 3「No Approval, No Production Change」。Registry 已是生產事實；若選 A（Validator 過就進庫），等於把「能不能進庫」交給 LLM Validator，與「人擁有業務決策」衝突。批次核准是為了避免逐案審批疲勞。

---

### 2.2 `regression_status` 與 Suite Membership 雙寫（NEEDS_DECISION-05 / ADR-003）

**建議：B — 只認 Suite Membership**

- TC 上只留 eligibility：`ci_eligible`、`hotfix_eligible`、`critical_path` 等
- 「在不在 Full / Smoke / Hotfix」只看 Suite Membership
- 從 `test_types` 移除 `regression` / `smoke` / `hotfix`
- `regression_status` / `ci_status` 改為 derived（由 Runtime 反查）

**理由：** 同一事實寫兩處，遲早不一致（TC 標 regression、Suite 裡卻沒有）。查「這個 TC 在哪些 suite」用 `qaos suites-of <tc_id>` 即可。這是 Principle 6 的直接推論。

---

### 2.3 `EXECUTE_TEST` 無人可用（Brief 矛盾 C5）

**建議：保持 `reserved`，Phase 5 再解鎖**

- Phase 1–4：不授權任何 Agent
- Execution / Evidence 由人工或 CI 匯入
- Phase 5 再開 `Test Executor` Agent，並解鎖該 Action

**理由：** Brief 本身把自動執行排在 Phase 5。現在就授權，等於提前引入執行環境、穩定性、CI 耦合，會拖垮 MVP。Action 留在 registry 是為了 schema / 權限矩陣完整，不是現在就能用。

---

## 3. 一句話摘要

Skill 用 Fork 保方法論、Adapt 接契約；人審卡在進 Registry（可批次）；suite 狀態只認 Membership；執行能力先占位、後實作。

---

## 4. 建議回覆 Claude 的用語（可選）

若採納本文件全部建議，可回：

```text
APPROVE ARCHITECTURE（採用全部建議選項）
額外確認：
- Skill：ll0v0ll/test-case-designer = Fork + Adapt（License 確認後再 subtree）
- 02:B（進 Registry 需批次 Human Approval）
- 05:B（Suite Membership 唯一事實來源）
- EXECUTE_TEST：reserved 至 Phase 5
```

---

## 5. Claude 的補充意見（2026-09-13）

三項處置與 Skill 策略均同意，無分歧。以下是「說對了但還不夠」的補強：

1. **License fallback 要分開「方法論」與「表達」。** ISTQB 技術本身不受著作權保護；`SKILL.md` 文字與 `allpairs.py` 程式碼受保護。作者無回應時的 fallback 應為：以自己的文字重寫 SKILL.md、自寫 pairwise wrapper（底層 `allpairspy` 為 MIT），**不複製原文再加註**。
2. **批次核准的真正風險是「全選 approve」。** 配套：(a) `ApprovalRequest.batch_items` 可逐項決定（已實作）；(b) 每個 item 附 Validator `advisories` 與 `assumptions` 摘要，讓有疑慮的項目在清單中可辨識（Phase 4 呈現層）；(c) Phase 3 eval 追蹤 override / reject 率，作為 Phase 6 自主化的前提。
3. **derived status 目前是全目錄掃描。** `qaos suites-of` 反查 `testsuites/`；數百 TC 為毫秒級，Phase 5 資料量上來再建索引。
4. **`EXECUTE_TEST` reserved 的必然配套：Human / CI 匯入入口。** 沒有 Agent 執行測試，就必須有 `qaos execution import` 與 `qaos evidence add`（自動計算 sha256），否則 MVP-2 沒有輸入。Phase 2 CLI 補上。
5. 與本文相關但未提及的 ADR-004 #13：`test-case-designer` 的 Phase 2.5 Human review gate 改為可開關 checkpoint（`analysis_review: required|skip`），Validator 為必經。
