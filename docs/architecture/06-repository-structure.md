# 06 — Repository Structure

> 對 Brief §29 的重新評估。原則：**Source of truth 只有一份、每個目錄只有一個寫入者角色、正式資料與 run 期資料分離。**

```
qa-agent-os/
├── .claude/
│   ├── agents/                 # Claude Code subagent 定義（Phase 3 產生，內容由 agents/*.yaml 生成）
│   ├── skills/                 # 專案層 skills（Phase 2–3）
│   └── settings.json           # hooks：PostToolUse → qaos validate；PreToolUse → 寫入路徑守衛
│
├── agents/                     # ★ Agent Contract（機器可讀 YAML，單一事實來源）
│   ├── supervisor.yaml
│   ├── spec-analyst.yaml … regression-curator.yaml
│
├── permissions/
│   └── action-registry.yaml    # ★ Action Registry
│
├── schemas/                    # ★ JSON Schema 2020-12
│   ├── common/                 # $defs：ids、enums、envelope、history
│   ├── agent/                  # agent-contract
│   ├── artifact/               # envelope + 12 payload schemas
│   ├── spec/                   # spec, spec-version, requirement
│   ├── testcase/               # testcase-version, registry-pointer, test-suite
│   ├── bug/                    # bug
│   ├── execution/              # test-execution, evidence
│   ├── approval/               # approval-request (+decision)
│   └── workflow/               # workflow-definition, workflow-run, task
│
├── workflows/                  # ★ 5 個 Workflow Definition（YAML，符合 schemas/workflow/workflow-definition）
│
├── specs/                      # Human 寫入。specs/<product>/areas.yaml 登記 <AREA> code
│   └── <product>/<area>/<spec_id>/
│       ├── spec.yaml           # 身份 + versions[] 索引
│       └── v1.0.md, v1.1.md    # 不可變快照
│
├── testcases/
│   ├── registry/               # Runtime 寫入。<tc_id>.yaml = pointer（active_version, status, versions[]）；_counters.yaml
│   ├── versions/<tc_id>/v<n>.yaml   # Runtime 寫入（VALIDATED 以上才存在）
│   └── manual/                 # Human 寫入：人工測試原始紀錄（Test Designer mode=manual 的輸入）
│
├── testsuites/<type>/<suite_id>.yaml    # Runtime 寫入（Approval 後）；type = full-regression|ci-regression|hotfix|smoke|feature
│
├── bugs/<product>/<area>/<bug_id>.yaml  # Runtime 寫入（Approval 後）；OPEN 之後的狀態由 Human 更新；`qaos bug index` 產生各層 index.md
│
├── clarifications/<product>/<area>/<clr_id>.yaml + .md   # 問 PM 的單：Runtime（RESOLVE_AMBIGUITY）或 Human 建立；PM 回答由 Human 填入；index.md 總表
│
├── executions/<yyyy-mm>/<exe_id>.yaml   # Human / CI 匯入
├── evidence/<exe_id|bug_id>/<evd_id>.yaml + 檔案   # Human / CI 匯入
│
├── artifacts/                  # Agent 寫入（各自目錄）；run 期產物，永不刪除
│   ├── spec-analysis/<run_id>/
│   ├── requirements/<run_id>/       # RequirementModel；G-SPEC PASS 後由 Runtime 複製一份到 artifacts/requirements/<spec_id>/v<ver>/ 作為持久 Requirement
│   ├── test-design/<run_id>/
│   ├── validation/<run_id>/
│   ├── bug-analysis/<run_id>/
│   ├── change-impact/<run_id>/
│   ├── regression/<run_id>/
│   └── summaries/<run_id>/
│
├── approvals/<apr_id>.yaml     # Supervisor 建立 request；Human 寫入 decision
├── runs/<run_id>/              # Supervisor/Runtime：run.yaml、tasks/*.yaml、audit.log
│
├── skills/                     # 自寫 / fork 的 skill 原始碼（symlink 或複製到 .claude/skills）
├── tools/                      # Phase 2：qaos CLI（validate / transition / gate / commit / approve / trace）
└── docs/
    ├── architecture/           # 本套文件
    ├── workflows/              # 每個 workflow 的說明 + Mermaid
    ├── agent-contracts/        # 每個 agent 的人可讀 contract
    └── decisions/              # ADR + NEEDS_DECISION 清單
```

## 相對 Brief §29 的變更

| 變更 | 理由 |
|---|---|
| 新增 `permissions/`、`evidence/`、`runs/`、`tools/`、`schemas/common|execution|approval` | Brief 有 Action Registry、Evidence、Workflow Run 概念但無落點 |
| `bugs/<product>/<area>/` 加 product 層 | 與 `specs/<product>/<area>/` 一致 |
| `artifacts/requirements/` 兼作持久 Requirement 存放（`<spec_id>/v<ver>/`） | Requirement 是被 TC 引用的長期 entity，不應只是 run 期 artifact |
| `testcases/registry/` 只存 pointer | 避免 registry 與 versions 雙寫 |
| `agents/*.yaml` 為 source of truth，`.claude/agents/*.md` 為生成物 | Contract 必須可被 Runtime 驗證，Markdown frontmatter 不夠 |
| `.claude/skills/` 與 `skills/` 分離 | `skills/` 存 fork/rewrite 的原始碼與測試；`.claude/skills/` 只放安裝後的版本 |
