# ADR-004 · Phase 1 待決事項核准紀錄

- **Status**: **Accepted** — 2026-09-13，Human 回覆「APPROVE ARCHITECTURE（採用全部建議選項）」
- **Context**: `NEEDS_DECISION.md` 13 項，全部採用 Recommended Option。以下為生效內容，後續 Phase 以此為準。

| # | 決定 | 生效位置 |
|---|---|---|
| 01 | 執行環境 = Claude Code Native：`.claude/agents/` subagents + `.claude/skills/` + `tools/qaos` Python CLI + hooks；狀態全在檔案，git 為 audit trail | `01-system-architecture.md` §6.4 |
| 02 | VALIDATED 版本寫入 `testcases/versions/`；ACTIVE 需 `ACTIVATE_TESTCASE` approval，支援批次核准 | TC state machine、WF-A T4 |
| 03 | Manual Test Integrator 併入 Test Designer `mode=manual`；共 8 個 Agent | `agents/test-designer.yaml` |
| 04 | `test_level` 不含 manual；新增 `execution_mode: manual\|automated\|hybrid` | `schemas/common/defs.schema.json` |
| 05 | `test_types` 移除 regression/smoke/hotfix；Suite Membership 為唯一事實來源；TC 只存 eligibility | ADR-003、`testcase-version.schema.json` |
| 06 | `max_validation_iterations = 3` | `workflows/*.yaml` |
| 07 | ID 格式 `TC-<AREA>-<seq>`，`<AREA>` 全域唯一（登記於 `specs/<product>/areas.yaml`） | `defs.schema.json` ID patterns |
| 08 | Spec 由 Human 手動放 Markdown 至 `specs/`，Runtime 計算 hash；Confluence importer 排 Phase 5 | `spec.schema.json` |
| 09 | ~~`test-case-designer` = `ll0v0ll/test-case-designer`，Fork + Adapt~~ **→ 已由 [ADR-005](ADR-005-phase2-corrections-to-adr004.md) 修正 2026-09-15：不 clone/fork，改為方法論參考**；`spec-dd` / `spec-verify` 不採用，`spec-analysis` / `test-validation` 自寫（不變） | `07-skill-evaluation.md` |
| 10 | 既有資料只匯入 1 個 feature（`claim-bonus-event-reward`）作為 Phase 2 fixture | Phase 2 工作項 |
| 11 | Bug OPEN 之後由 Human 以 `qaos bug transition` 手動推進；Jira 同步排 Phase 5 | Bug state machine |
| 12 | Artifact 內容繁體中文，欄位 key 英文 | Skill prompt 規範 |
| 13 | ~~`test-case-designer` 的 Phase 2.5 分析審核改為可開關 checkpoint（workflow input `analysis_review: required\|skip`，預設 skip）~~ **→ 已由 [ADR-005](ADR-005-phase2-corrections-to-adr004.md) 修正 2026-09-15：改為 Requirement 層級的必經 checkpoint（`REVIEW_REQUIREMENTS`，G-SPEC PASS 後、T2 前），非 TestDesignReport.analysis 層級**；Validator 為必經（不變） | WF-A 新增 `REVIEW_REQUIREMENTS` approval type（Phase 3 落地） |

- **Consequences**: Phase 1 文件中的 `[NEEDS_DECISION-xx]` 標記視為已解決；Phase 2 起若要推翻任一項，需新開 ADR。
- **待辦（非阻塞）**: `ll0v0ll/test-case-designer` License 仍未確認 — Phase 2 clone 到 `skills/vendor/` 僅供內部 adapt。作者無回應時的 fallback：以自己的文字重寫 SKILL.md、自寫 pairwise wrapper（`allpairspy` 為 MIT），不複製原文；方法論出處以引用方式註明。
- **相關**: `RECOMMENDATIONS-skill-and-top3.md`（人工建議整理，與本 ADR 一致，含 Claude 補充意見）。
