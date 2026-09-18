export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(method: string, url: string, body?: unknown): Promise<T> {
  const res = await fetch(url, {
    method,
    headers: body !== undefined ? { "Content-Type": "application/json" } : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    let msg = res.statusText;
    try {
      const j = await res.json();
      msg = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail ?? j);
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, msg);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  get: <T>(url: string) => request<T>("GET", url),
  post: <T>(url: string, body?: unknown) => request<T>("POST", url, body),
  put: <T>(url: string, body?: unknown) => request<T>("PUT", url, body),
  patch: <T>(url: string, body?: unknown) => request<T>("PATCH", url, body),
  del: <T = void>(url: string) => request<T>("DELETE", url),
};

export type TodoStatus = "todo" | "doing" | "done";

export interface Todo {
  id: number;
  title: string;
  status: TodoStatus;
  scheduled_date: string | null;
  due_date: string | null;
  estimate_min: number | null;
  details: string;
  linked_output_path: string | null;
  linked_output: { key: string; label: string; review_status: ReviewStatus | null; exists: boolean } | null;
  linked_report_id: number | null;
  auto_complete: boolean;
  auto_completed_at: string | null;
  position: number;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

export type ReviewStatus = "pending" | "reviewed" | "returned";

export interface Drift { stale: boolean; newer: string[]; added: string[]; retired: string[]; registry_active?: number }
export interface Folder { id: number; name: string; description: string; created_at: string; updated_at: string; count: number; items: { group_key: string; testcase_id: string; added_at: string }[] }
export interface OutputMeta {
  case_count?: number | null;
  case_ids?: string[];
  drift?: Drift;
  areas?: string[];
  specs?: string[];
  priority?: Record<string, number>;
  risk?: Record<string, number>;
  exploratory?: number;
  revised?: number;
  latest_case_update?: string | null;
  title?: string | null;
  parse_error?: string;
}

export interface OutputFile {
  path: string;
  name: string;
  group_key: string;
  area: string | null;
  kind: "json" | "html" | "other";
  size: number;
  mtime: number;
  modified_at: string;
  meta: OutputMeta;
  first_seen_at: string;
  acknowledged_at: string | null;
  unread: boolean;
  changed_now: boolean;
}

/** 同模組的 json/html 合為一個群組，共用審閱狀態 */
export interface OutputGroup {
  key: string;
  area: string | null;
  label: string;
  files: OutputFile[];
  kinds: string[];
  size: number;
  mtime: number;
  modified_at: string;
  meta: OutputMeta;
  review_status: ReviewStatus;
  note: string;
  review_updated_at: string | null;
  tc_summary: { total: number; pending: string[]; reviewed: number; returned: string[]; derived_status: ReviewStatus; reasons: Record<string, string> };
  unread: boolean;
  changed_now: boolean;
}

export interface TcStep { n: number; action: string }
export interface TcCase {
  testcase_id: string; title: string; version: number; priority: string; risk: string; test_level: string;
  test_types: string[]; design_techniques: string[]; requirement_ids: string[]; preconditions: string[];
  steps: TcStep[]; expected_result: string; assumptions: { text: string; requirement_id?: string; needs_human_confirmation?: boolean }[];
  status: string; updated_at: string | null; spec_reference: { location?: string; quote?: string } | null;
  review_status: ReviewStatus;
  review_reason: string;
  folders: { id: number; name: string }[];
}
export interface CaseFilter { priority?: string; risk?: string; kind?: "exploratory" | "revised"; review?: ReviewStatus }
export type OutputContent = { kind: "json"; cases: TcCase[] } | { kind: "html"; raw_url: string } | { kind: "text"; text: string };

export type ReportKind = "manual" | "output" | "automation";
export interface Report {
  id: number;
  title: string;
  summary: string;
  body_md: string;
  kind: ReportKind;
  source_key: string | null;
  auto_md: string;
  auto_generated_at: string | null;
  created_at: string;
  updated_at: string;
  output_paths: string[];
}
export type ReportLite = Omit<Report, "body_md" | "auto_md">;
export interface ReportPage { items: ReportLite[]; total: number; page: number; page_size: number; counts: Record<string, number> }

// ---- pipeline ----
export type StageStatus = "pending" | "active" | "done" | "failed" | "waiting_human" | "cancelled" | "skipped";
export type HealthState = "live" | "stalled" | "dead" | "ended";

export interface StageDef { id: string; title: string; agent: string | null; gate: string | null; order: number; notes: string | null }

export interface StageView extends StageDef {
  status: StageStatus;
  runtime: { status: string; task_status?: string; iteration?: number; max_iterations?: number; started_at?: string | null; ended_at?: string | null; gate?: string | null; approval_id?: string | null; task_id?: string; run_status?: string; at?: string; started?: boolean; awaiting?: boolean; elapsed_seconds?: number | null; work_seconds?: number; human_seconds?: number; elapsed_running?: boolean } | null;
  event_agents: number;
  live: boolean;
  last_at: string | null;
}

export interface AgentSpan {
  agent_id: string; agent_type: string; subagent_name: string; started_at: string; ended_at: string | null;
  stage_id: string | null; stage_title: string | null; signal: string; description: string; role: string;
  elapsed_seconds: number; running: boolean;
}

export interface RunLite {
  phase?: "phase2" | "phase3" | "revision" | null;
  run_id: string; workflow_id: string | null; status: string | null; spec_id: string | null; spec_version: string | null;
  current_task_id: string | null; waiting_on_approval_id: string | null; updated_at: string | null;
  tasks: { task_id: string; status: string; iteration: number; agent_id: string | null; type: string | null }[];
}

export interface NextAction { kind: string; text: string; link: { type: "run" | "session" | "ignore" | "outputs"; id: string } | null; detail?: string }
export interface TimelineItem { ts: string; kind: "run" | "task" | "gate" | "agent"; label: string; status: "info" | "active" | "done" | "failed" | "warn"; running?: boolean }
export interface FinalInfo { area: string | null; files: { name: string; path: string; group_key: string; kind: string; modified_at: string; mtime: number }[]; hook_writes: { ts: string; path: string; tool: string }[]; source: "hook" | "scan" }

export interface SessionView {
  lane_key: string;
  session_id: string; short_id: string; label: string; spec: string | null; spec_short: string | null; workflow_id: string | null; run_status: string | null;
  primary_status: string; primary_label: string; clock_frozen: boolean; run_elapsed_seconds: number | null; secondary: string | null;
  next_action: NextAction; sibling_completed: { run_id: string; spec: string; status: string } | null; sibling_runs: { run_id: string; spec: string; status: string }[]; open_clarifications: { clarification_id: string; status: string; question: string }[];
  current_stage_title: string | null; agent_note: string | null; final: FinalInfo; run_created_at: string | null; run_updated_at: string | null; timeline?: TimelineItem[];
  tracked: boolean; ignored: boolean; suggested: boolean; tag: string;
  cwd: string; started_at: string; ended_at: string | null; end_reason: string | null; first_seen: string; last_seen: string;
  event_count: number; stops: number; duration_seconds: number;
  health: { state: HealthState; idle_seconds: number };
  agent_types: string[]; agent_count: number;
  current_agent: AgentSpan | null; current_stage: string | null;
  final_writes: { ts: string; path: string; tool: string; agent_id: string }[];
  stages: StageView[];
  related_runs: RunLite[];
  active_run_id: string | null;
  phase?: "phase2" | "phase3" | "revision" | null;
  agents?: AgentSpan[];
  events?: { ts: string; event: string; agent_id?: string; agent_type?: string; subagent_name?: string; tool_name?: string; file_path?: string; reason?: string }[];
}

export interface PipelineSnapshot {
  generated_at: string;
  stall: { warn_after_seconds: number; dead_after_seconds: number };
  stages: StageDef[];
  focus: SessionView | null;
  max_lanes: number;
  lanes: SessionView[];
  sessions: SessionView[];
  live_count: number;
  events_files: string[];
}

export interface RunDetail extends Omit<RunLite, "tasks"> {
  created_at: string | null; initiated_by: string | null; testcase_id: string | null;
  tasks: { task_id: string; type: string | null; agent_id: string | null; status: string; iteration: number; gate: string | null; mode: string | null;
    started_at: string | null; ended_at: string | null; approval_id: string | null; outputs: number; entities: number;
    history: { at: string; from: string | null; to: string; trigger: string }[];
    gate_results: { at: string; layer: string; result: string; details: string[] }[] }[];
  history: { at: string; from: string | null; to: string; trigger: string }[];
  audit: { at: string; actor: string; action: string; detail: string }[];
}

export interface NavCounts {
  pipeline: { active_sessions: number };
  outputs: { total: number; unread: number };
  reports: { total: number; unreviewed: number };
  todos: { open: number };
  tickets: { approvals_pending: number; clarifications_open: number; bugs_open: number };
  automation: { runs: number; open: number };
}

// ---- tickets ----
export interface TicketDraft { ticket_id: string; kind: string; decision: string | null; option: string | null; rationale: string; per_item: Record<string, { decision?: string; reason?: string }>; extra: Record<string, string>; sent_at: string | null; sent_command: string | null; updated_at: string }
export interface CommandOut { command: string; warnings: string[]; rejected?: string[] }
export interface ExecResult { ok: boolean; command: string; exit_code: number; stdout: string; stderr: string; post: { command: string; exit_code: number; stdout: string; stderr: string }[]; run_id: string | null; run_status_after: string | null; next_task: string | null; session_id: string | null; handoff_id: string | null; hint: string; started_at: string; ended_at: string }
export interface Execution extends ExecResult { id: number; ticket_id: string; kind: string; action: string }
export interface ApprovalLite { approval_id: string; type: string; status: string; run_id: string | null; task_id: string | null; summary: string; requested_at: string | null; requested_by: string | null; options: { key: string; label: string }[]; item_count: number; decision: string | null; decided_by: string | null; decided_at: string | null; selected_option: string | null; rationale: string | null }
export interface ApprovalItem { testcase_id: string; version: number; title: string | null; priority: string | null; risk: string | null; test_level: string | null; requirement_ids: string[]; preconditions: string[]; steps: { n: number; action: string }[]; expected_result: string | null; assumptions: { text: string }[]; spec_reference: { location?: string; quote?: string } | null; exploratory: boolean; decided: string | null }
export interface DraftCase { draft_id: string; title: string; priority: string | null; risk: string | null; test_level: string | null; requirement_ids: string[]; assumptions: string[]; exploratory: boolean; expected_result: string | null; steps: { n: number; action: string }[] }
export interface ArtifactCtx { id: string; type: string | null; missing?: boolean; created_by?: string; created_at?: string; iteration?: number; path?: string; cases?: DraftCase[]; count?: number; exploratory?: number; assumptions?: string[]; uncovered?: { requirement_id: string; reason: string }[]; techniques?: { technique: string; count: number }[]; self_check?: Record<string, boolean>; coverage_count?: number; result?: string; issues?: { severity: string; draft_id: string; message: string }[]; summary?: string; keys?: string[] }
export interface Memo { path: string; text: string; mtime: string; suggested: string | null }
export interface ApprovalDetail extends ApprovalLite { impact: unknown; artifact_ids: string[]; trace: unknown[]; diff_summary: string | null; items: ApprovalItem[]; context: ActivationContext | null; artifacts: ArtifactCtx[]; memo: Memo | null; run: { status: string; spec_id: string; spec_version: string; workflow_id: string; current_task_id: string | null } | null; draft: TicketDraft | null; md_path: string | null; decision: any }
export interface Recommendation { found: boolean; mode: string | null; adopt: string[]; reject: string[]; evidence: string[]; note: string | null }
export interface ActivationContext { spec_key: string; phase2_active: number; phase2_ids: string[]; cross_compared: boolean; shadow_doc: string | null; overlap: Record<string, string[]>; overlap_count: number; needs_review: boolean; recommendation: Recommendation | null }
export interface ClarificationLite { clarification_id: string; product: string; functional_area: string; spec_id: string; spec_version: string; status: string; question: string; requirement_id: string | null; raised_by: string; raised_at: string; asked_to: string | null; asked_at: string | null; answered_by: string | null; answered_at: string | null; resolution: string | null; run_id: string | null; approval_id: string | null; impact: string | null; answer: string | null; options: unknown[]; context: string; path: string }
export interface ClarificationDetail extends ClarificationLite { history: { at: string; from_status: string | null; to_status: string; by: string; trigger: string }[]; spec_reference: { spec_id?: string; spec_version?: string; location?: string; quote?: string } | null; draft: TicketDraft | null; allowed: string[] }
export interface BugLite { bug_id: string; title: string; product: string; functional_area: string; spec_id: string; spec_version: string; requirement_id: string | null; severity: string; priority: string; status: string; created_at: string; updated_at: string; approval_id: string | null; external_ref: string | null; duplicate_of: string | null; evidence_count: number; path: string }
export interface BugDetail extends BugLite { severity_rationale: string; environment: Record<string, string>; acceptance_criteria_ids: string[]; preconditions: string[]; reproduction_steps: (string | { n: number; action: string })[]; expected_result: string; expected_result_spec_reference: { location?: string; quote?: string } | null; actual_result: string; actual_result_evidence_map: unknown[]; evidence_ids: string[]; api: Record<string, unknown> | null; impact: string; suspected_area: string; ambiguity_suspected: boolean; history: { at: string; from_status: string | null; to_status: string; by: string; trigger: string }[]; resolution: unknown; verification: unknown; draft: TicketDraft | null; allowed: { to: string; requires: string | null }[] }

// ---- pipeline 耗時分析 ----
export interface StageDur { task_id: string | null; status: string; iterations: number; elapsed: number | null; work: number; gate: number; human: number; running: boolean; title: string; no_history: boolean }
export interface RunDur { run_id: string; status: string; phase?: string | null; workflow_id: string | null; spec: string; created_at: string | null; updated_at: string | null; total: number | null; human_total: number; agent_total: number; stages: Record<string, StageDur> }
export interface StageAgg { id: string; title: string; agent: string | null; n: number; avg?: number; median?: number; max?: number; min?: number; sum?: number; work_avg?: number; gate_avg?: number; human_avg?: number; iter_avg?: number; iter_max?: number; worst_run?: string }
export interface DurationAnalysis { scope: string; workflow: string | null; runs: RunDur[]; stages: StageAgg[]; summary: { n: number; total_avg: number | null; total_median: number | null; total_max: number | null; human_avg: number | null; agent_avg: number | null } }

// ---- spec 進度（匯流圖）----
export interface RunRef { run_id: string; status: string; created_at: string | null; updated_at: string | null; spec_version: string | null; iterations: number; phase?: string }
export interface SpecFlow {
  key: string; spec_id: string | null; area: string; phase2: RunRef[]; phase3: RunRef | null; others: RunRef[]; approval_id: string | null; phase3_end: string | null;
  integration: { status: "done" | "active" | "pending"; elapsed: number | null; doc: string | null; doc_at: string | null; revisions: RunRef[]; revisions_open: number; ended_at: string | null };
  final: { status: "done" | "stale" | "pending"; elapsed: number | null; group_key: string | null; at: string | null; stale: boolean; case_count: number | null };
  dod: { integrated: boolean; shadow_doc: boolean; final: boolean }; missing: string[]; complete: boolean;
}
export interface SpecFlowData { specs: SpecFlow[]; run_phase: Record<string, string>; generated_at: string }

// ---- 測試執行（M7）----
export type TestResultKind = "untested" | "pass" | "fail" | "blocked" | "skipped";
export interface RunCounts { untested: number; pass: number; fail: number; blocked: number; skipped: number; total: number; done: number; pass_rate: number; progress: number }
export interface Evidence { id: string; filename: string; stored: string; type: string; description: string; size: number; sha256: string; added_at: string; added_by: string }
export interface TestResult {
  id: number; run_id: number; position: number; testcase_id: string; testcase_version: number | null; group_key: string; spec_id: string | null; spec_version: string | null;
  title: string; priority: string | null; risk: string | null; requirement_ids: string[]; preconditions: string[]; steps: { n: number; action: string }[]; expected_result: string;
  result: TestResultKind; actual_result: string; notes: string; duration_ms: number | null; evidence: Evidence[]; executed_at: string | null; executed_by: string | null;
  qaos_execution_id: string | null; qaos_evidence_ids: string[]; bug_run_id: string | null; created_at: string; updated_at: string;
}
export interface TestRun {
  id: number; name: string; trigger: string; status: "planned" | "running" | "done" | "aborted"; environment: string; build: string; notes: string; created_by: string; import_all: boolean;
  report_id: number | null; started_at: string | null; ended_at: string | null; created_at: string; updated_at: string; counts: RunCounts; results?: TestResult[]; missing?: string[];
}
export interface TestRunMeta { results: TestResultKind[]; evidence_types: string[]; run_status: string[]; max_evidence_bytes: number }

// ---- 工程 CI（讀 admin-ui/data/ci-status.json）----
export interface CiJob { name: string; status: "pass" | "fail" | "running" | "skipped"; tests: number; failures: number; errors: number; duration_s: number; log: string }
export interface CiStatus { status: "pass" | "fail" | "running"; sha: string; branch: string; updated_at: string; web_url: string; source: "local" | "gitlab"; jobs: CiJob[] }
export interface CiStatusResp { available: boolean; file: string; example?: string; error?: string; web_url?: string; remote?: string; status: CiStatus | null }
