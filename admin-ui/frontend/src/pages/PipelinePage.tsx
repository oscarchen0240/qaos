import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { PageHeader, Tabs, EmptyState } from "@/components/PageHeader";
import { useToast } from "@/components/Toast";
import { refreshNav } from "@/lib/nav";
import { api, type RunLite, type SessionView } from "@/lib/api";
import { usePipeline } from "@/lib/usePipeline";
import { fmtDate, fmtElapsed } from "@/lib/format";
import { clickable } from "@/lib/a11y";
import { ArrowRight } from "@phosphor-icons/react";
import { StageRail, HealthTag, SessionDrawer, RunDrawer, TaskChips, RunStatusTag, Timeline, PhaseTag } from "./pipeline/parts";
import { DurationsView } from "./pipeline/DurationsView";
import { SpecFlowView } from "./pipeline/SpecFlowView";

export function PipelinePage() {
  const [session, setSession] = useState<string | null>(null);
  const { snap, mode, error, reconnect } = usePipeline(session);
  const [tab, setTab] = useState<"live" | "specs" | "sessions" | "runs" | "durations">("live");
  const [showDur, setShowDur] = useState<boolean>(() => { try { return localStorage.getItem("qaos.rail.showDur") === "1"; } catch { return false; } });
  const toggleDur = () => setShowDur((v) => { try { localStorage.setItem("qaos.rail.showDur", v ? "0" : "1"); } catch { /* ignore */ } return !v; });
  const [runs, setRuns] = useState<RunLite[]>([]);
  const [openSession, setOpenSession] = useState<string | null>(null);
  const [openRun, setOpenRun] = useState<string | null>(null);
  const [showIgnored, setShowIgnored] = useState(false);
  const [now, setNow] = useState(Date.now());
  const { toast } = useToast();
  const nav = useNavigate();

  useEffect(() => { const id = setInterval(() => setNow(Date.now()), 1000); return () => clearInterval(id); }, []);
  useEffect(() => { if (tab === "runs") api.get<RunLite[]>("/api/pipeline/runs").then(setRuns).catch(() => {}); }, [tab, snap?.generated_at]);

  const focus = snap?.focus ?? null;
  const sessions = useMemo(() => (snap?.sessions ?? []).filter((s) => showIgnored || !s.ignored), [snap, showIgnored]);
  const genAt = snap ? new Date(snap.generated_at).getTime() : now;
  const drift = Math.max(0, now - genAt); // 快照產生後又過了多久，用來讓計時器走動

  const patchSession = async (id: string, body: { tracked?: boolean; ignored?: boolean; label?: string }, msg: string) => {
    try { await api.patch(`/api/pipeline/sessions/${id}`, body); toast(msg, "ok"); reconnect(); refreshNav(); }
    catch (e) { toast(`更新失敗：${(e as Error).message}`, "danger"); }
  };

  return (
    <>
      <PageHeader
        eyebrow="Monitor"
        title="Pipeline"
        description="以階段大綱呈現 TC 產生流程：run.yaml 為事實來源，Claude Code hook 事件補上即時的 agent 活動。"
        actions={
          <>
            <span className={`tag ${mode === "sse" ? "ok" : mode === "poll" ? "warn" : ""}`} title="資料連線方式">{mode === "sse" ? "SSE 即時" : mode === "poll" ? "輪詢 5s" : "連線中"}</span>
            <select className="select" style={{ width: 260 }} value={session ?? ""} onChange={(e) => setSession(e.target.value || null)} title="要追蹤哪個 session">
              <option value="">自動（追蹤中／建議的 session）</option>
              {(snap?.sessions ?? []).filter((s) => showIgnored || !s.ignored || s.session_id === session).map((s) => (
                <option key={s.session_id} value={s.session_id}>
                  {s.short_id} · {s.label || s.primary_label}{s.tracked ? " · 追蹤中" : s.suggested ? " · 建議" : ""}{s.ignored ? " · 已忽略" : ""}
                </option>
              ))}
            </select>
            <label className="row" style={{ gap: 6, fontSize: 12, color: "var(--text-muted)", cursor: "pointer" }} title="在階段條的每個節點下方顯示該節點耗時"><input type="checkbox" checked={showDur} onChange={toggleDur} />節點耗時</label>
            {focus && !focus.tracked && <button className="btn" onClick={() => patchSession(focus.session_id, { tracked: true }, "已設為追蹤")}>設為追蹤</button>}
            {focus && <button className="btn ghost" onClick={() => patchSession(focus.session_id, { ignored: !focus.ignored }, focus.ignored ? "已取消忽略" : "已忽略此 session")}>{focus.ignored ? "取消忽略" : "忽略此 session"}</button>}
          </>
        }
      />
      <Tabs
        tabs={[{ key: "live", label: "即時" }, { key: "specs", label: "Spec 進度" }, { key: "runs", label: "Runs（紀錄）", count: runs.length || undefined }, { key: "sessions", label: "Session", count: sessions.length }, { key: "durations", label: "耗時分析" }]}
        active={tab}
        onChange={(k) => setTab(k as typeof tab)}
      />
      <div className="page-body">
        {error && <div className="form-error" style={{ marginBottom: 10 }}>{error}</div>}
        {!snap ? <div className="faint">載入中…</div>
          : tab === "durations" ? <DurationsView onOpenRun={setOpenRun} />
          : tab === "specs" ? <SpecFlowView onOpenRun={setOpenRun} />
          : tab === "live" ? (
            snap.lanes.length === 0 ? (
              <EmptyState title="目前沒有進行中的 pipeline">
                {snap.events_files.length === 0
                  ? "尚未收到任何 hook 事件。裝好 hook 並啟動／resume 一個 Claude Code session 後，這裡會自動出現。"
                  : "沒有 run 仍在執行或等待核准的 session；已取消／已完成的 run 請看「歷史 Session」，或用右上角下拉手動選一個、或「設為追蹤」。"}
              </EmptyState>
            ) : (
              <div className="lanes">
                {snap.lanes.map((ln, i) => (
                  <LiveView key={ln.lane_key} showDur={showDur} s={ln} index={i} total={snap.lanes.length} drift={drift} onOpenRun={setOpenRun} onOpenSession={setOpenSession}
                    onIgnore={(id) => patchSession(id, { ignored: true }, "已忽略此 session")} onOutputs={() => nav("/outputs")} />
                ))}
              </div>
            )
          ) : tab === "sessions" ? (
            <>
              <div className="toolbar">
                <label className="check-row" style={{ flexDirection: "row" }}><input type="checkbox" checked={showIgnored} onChange={(e) => setShowIgnored(e.target.checked)} />顯示已忽略</label>
                <div className="grow" />
                <span className="faint mono">{snap.events_files.join(", ") || "無事件檔"}</span>
              </div>
              {sessions.length === 0 ? <EmptyState title="沒有 session" /> : (
                <table className="table">
                  <thead><tr><th>Session</th><th>Spec</th><th>狀態</th><th>開始</th><th>最後事件</th><th>時長</th><th>Agents</th><th>final 寫入</th><th>Run</th><th></th></tr></thead>
                  <tbody>
                    {sessions.map((s) => (
                      <tr key={s.session_id} className="clickable" {...clickable(() => setOpenSession(s.session_id), `開啟 session ${s.short_id}`)}>
                        <td>
                          <div className="row"><span className="mono">{s.short_id}</span>{s.tracked && <span className="tag accent">追蹤中</span>}{s.suggested && !s.tracked && <span className="tag cyan">建議</span>}{s.tag && <span className="tag violet">tag {s.tag}</span>}{s.ignored && <span className="tag">已忽略</span>}</div>
                          {s.label && <div className="faint" style={{ fontSize: 12 }}>{s.label}</div>}
                        </td>
                        <td><div>{s.spec_short ?? "—"}</div>{s.run_status && <RunStatusTag status={s.run_status} />}</td>
                        <td><HealthTag h={s.health} muted={s.clock_frozen} label={s.clock_frozen ? (s.secondary ?? undefined) : undefined} /></td>
                        <td className="mono">{fmtDate(s.started_at)}</td>
                        <td className="mono">{fmtDate(s.last_seen)}</td>
                        <td className="mono">{fmtElapsed(s.duration_seconds * 1000)}</td>
                        <td><div className="card-tags">{s.agent_types.map((t) => <span key={t} className={`tag ${t === "qaos-test-designer" ? "cyan" : ""}`}>{t}</span>)}<span className="faint mono">×{s.agent_count}</span></div></td>
                        <td className="mono">{s.final_writes.length || "—"}</td>
                        <td className="mono">{s.active_run_id ?? "—"}</td>
                        <td onClick={(e) => e.stopPropagation()}>
                          <div className="row">
                            {!s.tracked && <button className="btn ghost sm" onClick={() => patchSession(s.session_id, { tracked: true }, "已設為追蹤")}>追蹤</button>}
                            <button className="btn ghost sm" onClick={() => patchSession(s.session_id, { ignored: !s.ignored }, s.ignored ? "已取消忽略" : "已忽略")}>{s.ignored ? "取消忽略" : "忽略"}</button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </>
          ) : (
            runs.length === 0 ? <EmptyState title="runs/ 沒有 run.yaml" /> : (
              <table className="table">
                <thead><tr><th>Run</th><th>Phase</th><th>Workflow</th><th>Spec</th><th>狀態</th><th>Tasks</th><th>等待</th><th>更新</th></tr></thead>
                <tbody>
                  {runs.map((r) => (
                    <tr key={r.run_id} className="clickable" {...clickable(() => setOpenRun(r.run_id), `開啟 ${r.run_id}`)}>
                      <td className="mono">{r.run_id}</td>
                      <td><PhaseTag phase={r.phase} /></td>
                      <td className="mono faint">{r.workflow_id}</td>
                      <td className="mono">{r.spec_id}{r.spec_version ? `@${r.spec_version}` : ""}</td>
                      <td><RunStatusTag status={r.status} /></td>
                      <td><TaskChips tasks={r.tasks} current={r.current_task_id} /></td>
                      <td className="mono">{r.waiting_on_approval_id ?? "—"}</td>
                      <td className="mono">{fmtDate(r.updated_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )
          )}
      </div>
      <SessionDrawer sessionId={openSession} onClose={() => setOpenSession(null)} onOpenRun={setOpenRun} />
      <RunDrawer runId={openRun} onClose={() => setOpenRun(null)} />
    </>
  );
}

function LiveView({ s, index, total, drift, onOpenRun, onOpenSession, onIgnore, onOutputs, showDur }: {
  s: SessionView; index: number; total: number; drift: number; showDur?: boolean;
  onOpenRun: (id: string) => void; onOpenSession: (id: string) => void; onIgnore: (id: string) => void; onOutputs: () => void;
}) {
  const ended = !!s.ended_at;
  const frozen = s.clock_frozen;
  const idle = s.health.idle_seconds * 1000 + (ended ? 0 : drift);
  const runElapsed = s.run_elapsed_seconds != null ? s.run_elapsed_seconds * 1000 + (frozen ? 0 : drift) : null;
  const cur = s.current_agent;
  const activeRun = s.related_runs.find((r) => r.run_id === s.active_run_id) ?? null;
  const compact = total > 1;
  const terminal = ["cancelled", "failed", "completed"].includes(s.primary_status);
  const na = s.next_action;
  const onNext = () => {
    if (!na.link) return;
    if (na.link.type === "run") onOpenRun(na.link.id);
    else if (na.link.type === "session") onOpenSession(na.link.id);
    else if (na.link.type === "ignore") onIgnore(na.link.id);
    else if (na.link.type === "outputs") onOutputs();
  };
  const stallState = !terminal && s.health.state === "stalled";
  return (
    <div className={`lane ${compact ? "compact" : ""} ${terminal ? "terminal" : s.health.state}`}>
      <div className="lane-head">
        <span className="lane-idx">{index + 1}</span>
        <span className="lane-primary">{s.primary_label}</span>
        {s.secondary && <HealthTag h={s.health} muted label={s.secondary} />}
        {!s.secondary && !terminal && s.health.state !== "live" && <HealthTag h={s.health} />}
        <PhaseTag phase={s.phase} />
        {s.tracked && <span className="tag accent">追蹤中</span>}
        {s.tag && <span className="tag violet">tag {s.tag}</span>}
        <div className="grow" />
        {s.workflow_id && <span className="mono faint" title={s.workflow_id}>{s.pipeline_title || s.workflow_id}</span>}
        {activeRun && <button className="btn ghost sm mono" onClick={() => onOpenRun(activeRun.run_id)}>{activeRun.run_id}</button>}
        <span className="mono faint" title={s.session_id}>session {s.short_id}</span>
        <button className="btn ghost sm" onClick={() => onOpenSession(s.session_id)}>詳細</button>
      </div>

      <div className={`next-action ${na.link ? "clickable" : ""}`} data-kind={na.kind} title={na.detail ?? undefined}
        role="status" aria-atomic="true" aria-label={`${s.primary_label}。下一步：${na.text}`}
        {...(na.link ? { tabIndex: 0, onClick: onNext, onKeyDown: (e: React.KeyboardEvent) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onNext(); } } } : {})}>
        <span className="na-label">下一步</span>
        <span className="na-text">{na.text}</span>
        {na.detail && <span className="faint" style={{ fontSize: 12 }}>· {na.detail}</span>}
        {na.link?.type === "ignore" && <button className="btn sm" onClick={(e) => { e.stopPropagation(); onIgnore(na.link!.id); }}>忽略</button>}
        {na.link?.type === "outputs" && <button className="btn sm" onClick={(e) => { e.stopPropagation(); onOutputs(); }}>去產出頁</button>}
        {na.link?.type === "run" && <span className="faint row" style={{ fontSize: 12 }}>點開 run <ArrowRight className="ic sm" aria-hidden="true" /></span>}
      </div>

      {s.sibling_runs.map((sb) => (
        <div key={sb.run_id} className={`sibling-banner clickable ${sb.status === "COMPLETED" ? "" : "active"}`} {...clickable(() => onOpenRun(sb.run_id), `開啟 ${sb.run_id}`)}>
          同 session 另有 <span className="mono">{sb.run_id}</span> {sb.spec} <RunStatusTag status={sb.status} /> <span className="faint row" style={{ display: "inline-flex" }}>點開 <ArrowRight className="ic sm" aria-hidden="true" /></span>
        </div>
      ))}

      <div className="stack" style={{ gap: 12 }}>
      <div className="live-strip">
        <Stat label="Run" value={activeRun ? <span className="row"><RunStatusTag status={activeRun.status} big /></span> : <span className="faint">無關聯 run</span>}
          sub={activeRun ? `${activeRun.run_id} · 建立 ${fmtDate(s.run_created_at)}` : "僅 hook 事件"} onClick={activeRun ? () => onOpenRun(activeRun.run_id) : undefined} />
        <Stat label={frozen ? "跑了多久後結束" : "已執行"} value={<span className={`mono big ${frozen ? "muted" : ""}`}>{runElapsed != null ? fmtElapsed(runElapsed) : "—"}</span>}
          sub={frozen ? `${s.run_status === "CANCELLED" ? "取消" : s.run_status === "FAILED" ? "失敗" : "完成"}於 ${fmtDate(s.run_updated_at)}` : `${s.current_stage_title ?? "—"}`} />
        <Stat label="目前階段" value={<span>{s.current_stage_title ?? "—"}</span>}
          sub={cur ? `${cur.role}${cur.description && !cur.role.includes(cur.description) ? ` · ${cur.description}` : ""} · 已跑 ${fmtElapsed(cur.elapsed_seconds * 1000 + drift)}` : (terminal ? "run 已結束" : s.agent_note ?? "無子 agent 執行中（依 run.yaml）")} />
        <Stat label="最後事件" value={<span className="mono big" style={{ color: stallState ? "var(--warn)" : undefined }}>{fmtElapsed(idle)} 前</span>} sub={`${fmtDate(s.last_seen)} · ${s.event_count} 事件`} />
        <Stat label="Session" value={<span className="row"><span className="mono">{s.short_id}</span><HealthTag h={{ ...s.health, idle_seconds: Math.floor(idle / 1000) }} muted={terminal} label={terminal ? (s.secondary ?? undefined) : undefined} /></span>}
          sub={s.label || (ended ? `結束 ${fmtDate(s.ended_at)}` : `開始 ${fmtDate(s.started_at)}`)} onClick={() => onOpenSession(s.session_id)} />
      </div>

      <section className="panel">
        <div className="row" style={{ justifyContent: "space-between", marginBottom: 12 }}>
          <div className="section-title" style={{ margin: 0 }}>階段大綱{activeRun ? <> · <button className="link-btn mono" onClick={() => onOpenRun(activeRun.run_id)}>{activeRun.run_id}</button></> : " · 無關聯 run（僅事件）"}</div>
          {activeRun && <div className="row"><span className="faint mono">{activeRun.spec_id}@{activeRun.spec_version}</span>{activeRun.waiting_on_approval_id && <span className="tag warn">等待 {activeRun.waiting_on_approval_id}</span>}</div>}
        </div>
        <StageRail showDur={showDur} stages={s.stages} currentId={s.current_stage} drift={drift} runTerminal={terminal} />
      </section>

      {!compact && <div className="two-col">
        <section className="panel">
          <div className="section-title">Agent 活動（runtime 為主、hook 為輔 · 最近 12 筆）</div>
          {activeRun || (s.timeline ?? []).length > 0 ? <Timeline items={s.timeline ?? []} /> : <div className="faint">無關聯 run，也尚無子 agent 事件</div>}
        </section>
        <section className="panel">
          <div className="section-title">final 產出{s.final.area ? ` · ${s.final.area}` : ""}（檔案掃描）</div>
          {s.final.files.length === 0 ? (
            <div className="faint">testcases/final/ 尚無{s.final.area ? ` ${s.final.area} 的` : ""}檔案；匯出後由產出頁檔案掃描偵測（Bash cp 也抓得到）。</div>
          ) : (
            <div className="stack" style={{ gap: 6 }}>
              {s.final.files.map((f) => (
                <div key={f.path} className="agent-row clickable" {...clickable(onOutputs, `到產出頁檢視 ${f.name}`)}>
                  <span className={`tag ${f.kind === "json" ? "cyan" : "violet"}`}>{f.kind.toUpperCase()}</span>
                  <span className="mono">{f.name}</span>
                  <div className="grow" />
                  <span className="mono faint">{fmtDate(f.modified_at)}</span>
                </div>
              ))}
              {s.final.hook_writes.length > 0 && <div className="faint" style={{ fontSize: 12 }}>hook 也偵測到 {s.final.hook_writes.length} 次 Write/Edit</div>}
            </div>
          )}
          {s.related_runs.filter((r) => r.run_id !== s.active_run_id && !s.sibling_runs.some((x) => x.run_id === r.run_id)).length > 0 && (
            <>
              <div className="section-title" style={{ marginTop: 16 }}>其他相關 run</div>
              <div className="stack" style={{ gap: 6 }}>
                {s.related_runs.filter((r) => r.run_id !== s.active_run_id && !s.sibling_runs.some((x) => x.run_id === r.run_id)).map((r) => (
                  <div key={r.run_id} className="agent-row clickable" {...clickable(() => onOpenRun(r.run_id), `開啟 ${r.run_id}`)}><span className="mono">{r.run_id}</span><RunStatusTag status={r.status} /><span className="faint mono">{r.spec_id}</span></div>
                ))}
              </div>
            </>
          )}
        </section>
      </div>}
      </div>
    </div>
  );
}

function Stat({ label, value, sub, onClick }: { label: string; value: React.ReactNode; sub?: string; onClick?: () => void }) {
  return (
    <div className={`stat ${onClick ? "clickable" : ""}`} {...(onClick ? clickable(onClick, label) : {})}>
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
      {sub && <div className="stat-sub" title={sub}>{sub}</div>}
    </div>
  );
}
