import { useEffect, useRef, useState } from "react";
import { Drawer } from "@/components/Drawer";
import { api, type HealthState, type RunDetail, type SessionView, type StageView, type TimelineItem } from "@/lib/api";
import { fmtDate, fmtElapsed } from "@/lib/format";
import { clickable } from "@/lib/a11y";
import { ArrowsClockwise, HandPalm } from "@phosphor-icons/react";

const RUN_LABEL: Record<string, string> = { RUNNING: "執行中", WAITING_HUMAN: "等你決定", COMPLETED: "已完成", FAILED: "失敗", CANCELLED: "已取消", CREATED: "已建立" };
const RUN_CLASS: Record<string, string> = { RUNNING: "accent", WAITING_HUMAN: "warn", COMPLETED: "ok", FAILED: "danger", CANCELLED: "" };

export function PhaseTag({ phase }: { phase?: string | null }) {
  if (!phase) return null;
  const m: Record<string, [string, string, string]> = { phase2: ["Phase 2", "", "人扮 agent 腳本跑的 spec-to-testcase"], phase3: ["Phase 3", "cyan", "qaos-test-designer 跑的 spec-to-testcase"], revision: ["修訂", "violet", "testcase-revision：交叉整合時修訂 Phase 2 既有 TC"] };
  const [label, cls, title] = m[phase] ?? [phase, "", ""];
  return <span className={`tag ${cls}`} title={title}>{label}</span>;
}

export function RunStatusTag({ status, big }: { status: string | null; big?: boolean }) {
  return <span className={`tag ${status ? RUN_CLASS[status] ?? "" : ""} ${big ? "big" : ""}`} title={status ?? ""}>{status ? (RUN_LABEL[status] ?? status) : "—"}</span>;
}

const HEALTH_LABEL: Record<HealthState, string> = { live: "進行中", stalled: "可能卡住", dead: "已停止", ended: "已結束" };
const HEALTH_CLASS: Record<HealthState, string> = { live: "ok", stalled: "warn", dead: "danger", ended: "" };

/** session 連線健康度；當 run 已終止時用淡色「session 仍連線」，不和主狀態搶視覺 */
export function HealthTag({ h, muted, label }: { h: { state: HealthState; idle_seconds: number }; muted?: boolean; label?: string | null }) {
  const cls = muted ? "" : HEALTH_CLASS[h.state];
  return <span className={`tag ${cls}`} style={muted ? { opacity: 0.7 } : undefined} title={`最後事件 ${fmtElapsed(h.idle_seconds * 1000)} 前`}>{label ?? HEALTH_LABEL[h.state]}</span>;
}

const STAGE_LABEL: Record<string, string> = { pending: "待進行", active: "進行中", done: "完成", failed: "失敗", waiting_human: "等你決定", cancelled: "已取消", skipped: "未執行" };
const STAGE_TAG: Record<string, string> = { done: "ok", active: "accent", failed: "danger", waiting_human: "warn", cancelled: "", skipped: "", pending: "" };

export function StageRail({ stages, currentId, drift, runTerminal, showDur }: { stages: StageView[]; currentId: string | null; drift: number; runTerminal?: boolean; showDur?: boolean }) {
  const ref = useRef<HTMLOListElement>(null);
  const [scrollable, setScrollable] = useState(false);
  useEffect(() => {
    const el = ref.current; if (!el) return;
    const check = () => setScrollable(el.scrollWidth > el.clientWidth + 2 && el.scrollLeft + el.clientWidth < el.scrollWidth - 2);
    check(); el.addEventListener("scroll", check); const ro = new ResizeObserver(check); ro.observe(el);
    return () => { el.removeEventListener("scroll", check); ro.disconnect(); };
  }, [stages.length]);
  return (
    <div className={`rail-wrap ${scrollable ? "scrollable" : ""}`}>
    <ol className="rail" ref={ref} aria-label="pipeline 階段">
      {stages.map((st, i) => {
        const isCur = st.id === currentId;
        const r = st.runtime;
        const started = r?.started_at ? new Date(r.started_at).getTime() : null;
        const ended = r?.ended_at ? new Date(r.ended_at).getTime() : null;
        const running = st.status === "active" && !ended && !runTerminal;
        const dur = started ? (ended ?? (running ? Date.now() : started)) - started : null;
        const iter = r?.iteration ?? 0;
        const maxIter = r?.max_iterations ?? 3;
        const overIter = iter >= maxIter;
        // 迭代迴圈（Designer ⇄ Validator）由後端依 pipeline 大綱標 loop_partner，不同 workflow 的迴圈節點名稱不同，不寫死 id
        const loopPartner = !!st.loop_partner;
        const isFirstLoopNode = loopPartner && !stages.slice(0, i).some((s) => s.loop_partner);
        return (
          <li key={st.id} className={`rail-item ${st.status} ${isCur ? "current" : ""}`}>
            <div className="rail-node">
              <span className="rail-idx">{i + 1}</span>
              {(st.live || (isCur && running)) && <span className="pulse" />}
              {isFirstLoopNode && <span className="rail-loop" title="Designer ⇄ Validator 迭代迴圈" aria-label="與獨立驗證形成迭代迴圈"><ArrowsClockwise className="ic sm" aria-hidden="true" /></span>}
            </div>
            <div className="rail-body">
              <div className="rail-title">{st.title}</div>
              <div className="rail-sub mono">{st.agent?.replace("agent-", "") ?? ""}</div>
              {st.gate && <div className="rail-gate mono">{st.gate}</div>}
              <div className="rail-status">
                <span className={`tag ${STAGE_TAG[st.status] ?? ""}`}>{STAGE_LABEL[st.status] ?? st.status}</span>
                {loopPartner && iter > 0 && (
                  <span className={`tag ${overIter ? "danger" : ""}`} title={`迭代第 ${iter} 輪（上限 ${maxIter}）`}>
                    第 {iter} / {maxIter} 輪{overIter ? " · 超限" : ""}
                  </span>
                )}
                {r?.approval_id && (r.awaiting
                  ? <span className="tag warn">{r.approval_id}</span>
                  : <span className="tag" style={{ opacity: 0.6 }} title="此核准單已決定或該 run 已結束">曾開單 {r.approval_id}</span>)}
              </div>
              {showDur && r?.elapsed_seconds != null && r.elapsed_seconds > 0 && (
                <div className="rail-dur mono" title={`agent 工作 ${fmtElapsed((r.work_seconds ?? 0) * 1000)} · 等人 ${fmtElapsed((r.human_seconds ?? 0) * 1000)}`}>
                  ⏱ {fmtElapsed(r.elapsed_seconds * 1000 + (r.elapsed_running && !runTerminal ? drift : 0))}{r.elapsed_running && !runTerminal ? "…" : ""}
                </div>
              )}
              {(dur != null || st.last_at) && !showDur && (
                <div className="rail-meta mono">
                  {dur != null && dur > 0 && <span>{fmtElapsed(dur + (running ? drift : 0))}</span>}
                  {st.last_at && <span title="最後活動">{fmtDate(st.last_at).slice(5)}</span>}
                </div>
              )}
            </div>
          </li>
        );
      })}
    </ol>
    </div>
  );
}

const TASK_CLASS: Record<string, string> = { DONE: "ok", RUNNING: "accent", READY: "accent", GATE_FAILED: "danger", PENDING: "" };

export function TaskChips({ tasks, current }: { tasks: { task_id: string; status: string; iteration: number; type: string | null }[]; current: string | null }) {
  return (
    <div className="card-tags">
      {tasks.map((t) => (
        <span key={t.task_id} className={`tag ${TASK_CLASS[t.status] ?? ""} ${t.task_id === current ? "cur" : ""}`} title={`${t.status}${t.iteration ? ` · iteration ${t.iteration}` : ""}`}>
          {t.task_id}{t.type === "approval" ? <HandPalm className="ic sm" aria-label="人工核准" /> : null}{t.iteration ? `·${t.iteration}` : ""}
        </span>
      ))}
    </div>
  );
}

const TL_CLASS: Record<string, string> = { info: "", active: "accent", done: "ok", failed: "danger", warn: "warn" };
const TL_KIND: Record<string, string> = { run: "run", task: "task", gate: "gate", agent: "hook" };

/** Agent 活動：run.yaml 的 task history 為主，hook 事件疊加 */
export function Timeline({ items, limit = 12 }: { items: TimelineItem[]; limit?: number }) {
  const shown = [...items].reverse().slice(0, limit);
  if (shown.length === 0) return <div className="faint">此 run 尚無任何 task 歷程</div>;
  return (
    <div className="stack" style={{ gap: 5 }}>
      {shown.map((it, i) => (
        <div key={i} className={`agent-row tl-${it.status}`}>
          <span className={`dot ${it.running ? "on" : ""}`} />
          <span className="mono faint" style={{ width: 88 }}>{fmtDate(it.ts).slice(5)}</span>
          <span className={`tag ${TL_CLASS[it.status]}`} style={{ minWidth: 40, justifyContent: "center" }}>{TL_KIND[it.kind]}</span>
          <span style={{ flex: 1 }}>{it.label}</span>
        </div>
      ))}
    </div>
  );
}

export function SessionDrawer({ sessionId, onClose, onOpenRun }: { sessionId: string | null; onClose: () => void; onOpenRun: (id: string) => void }) {
  const [s, setS] = useState<SessionView | null>(null);
  useEffect(() => {
    if (!sessionId) { setS(null); return; }
    api.get<SessionView>(`/api/pipeline/sessions/${sessionId}`).then(setS).catch(() => setS(null));
  }, [sessionId]);
  const terminal = !!s && ["cancelled", "failed", "completed"].includes(s.primary_status);
  return (
    <Drawer open={!!sessionId} onClose={onClose} wide title={s ? s.primary_label : "Session"} subtitle={s ? `session ${s.session_id} · ${s.cwd}` : ""}>
      {!s ? <div className="faint">載入中…</div> : (
        <>
          <div className="card-tags">
            {s.run_status && <RunStatusTag status={s.run_status} big />}
            <HealthTag h={s.health} muted={terminal} label={terminal && s.secondary ? s.secondary : undefined} />
            <span className="tag">session 開始 {fmtDate(s.started_at)}</span>
            {s.ended_at && <span className="tag">結束 {fmtDate(s.ended_at)}</span>}
            {s.run_elapsed_seconds != null && <span className="tag">run {s.clock_frozen ? "共跑" : "已跑"} {fmtElapsed(s.run_elapsed_seconds * 1000)}</span>}
            {s.tag && <span className="tag violet">tag {s.tag}</span>}
            {s.suggested && <span className="tag cyan">建議追蹤</span>}
          </div>
          <div className="next-action" data-kind={s.next_action.kind} role="status" aria-atomic="true"><span className="na-label">下一步</span><span>{s.next_action.text}</span></div>
          <div>
            <div className="section-title">階段時間軸{s.active_run_id ? ` · ${s.active_run_id}` : ""}</div>
            <StageRail stages={s.stages} currentId={s.current_stage} drift={0} runTerminal={terminal} />
          </div>
          <div>
            <div className="section-title">活動（runtime 為主、hook 為輔）</div>
            <Timeline items={s.timeline ?? []} limit={40} />
          </div>
          {s.related_runs.length > 0 && (
            <div>
              <div className="section-title">相關 run</div>
              <div className="stack" style={{ gap: 6 }}>
                {s.related_runs.map((r) => (
                  <div key={r.run_id} className="agent-row clickable" {...clickable(() => onOpenRun(r.run_id), `開啟 ${r.run_id}`)}>
                    <span className="mono">{r.run_id}</span><RunStatusTag status={r.status} /><span className="faint mono">{r.spec_id}@{r.spec_version}</span>
                    <div className="grow" /><TaskChips tasks={r.tasks} current={r.current_task_id} />
                  </div>
                ))}
              </div>
            </div>
          )}
          <div>
            <div className="section-title">hook 事件（不含 Stop）</div>
            {(s.events ?? []).length === 0 ? <div className="faint">無</div> : (
              <div className="stack" style={{ gap: 3 }}>
                {(s.events ?? []).map((e, i) => (
                  <div key={i} className="agent-row" style={{ fontSize: 12 }}>
                    <span className="mono faint" style={{ width: 140 }}>{fmtDate(e.ts)}</span>
                    <span className="tag">{e.event}</span>
                    <span className="mono">{e.agent_type || e.tool_name || e.reason || ""}</span>
                    {e.file_path && <span className="mono faint">{e.file_path}</span>}
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </Drawer>
  );
}

export function RunDrawer({ runId, onClose }: { runId: string | null; onClose: () => void }) {
  const [r, setR] = useState<RunDetail | null>(null);
  useEffect(() => {
    if (!runId) { setR(null); return; }
    api.get<RunDetail>(`/api/pipeline/runs/${runId}`).then(setR).catch(() => setR(null));
  }, [runId]);
  return (
    <Drawer open={!!runId} onClose={onClose} wide title={runId ?? ""} subtitle={r ? `${r.workflow_id} · ${r.spec_id}@${r.spec_version} · by ${r.initiated_by}` : ""}>
      {!r ? <div className="faint">載入中…</div> : (
        <>
          <div className="card-tags">
            <RunStatusTag status={r.status} big />
            <span className="tag">建立 {fmtDate(r.created_at)}</span>
            <span className="tag">更新 {fmtDate(r.updated_at)}</span>
            {r.current_task_id && <span className="tag accent">目前 {r.current_task_id}</span>}
            {r.waiting_on_approval_id && <span className="tag warn">等待 {r.waiting_on_approval_id}</span>}
          </div>
          <div className="stack" style={{ gap: 8 }}>
            {r.tasks.map((t) => (
              <div key={t.task_id} className={`task-card ${t.task_id === r.current_task_id ? "current" : ""}`}>
                <div className="row" style={{ justifyContent: "space-between" }}>
                  <div className="row">
                    <span className="mono" style={{ fontWeight: 600 }}>{t.task_id}</span>
                    <span className={`tag ${TASK_CLASS[t.status] ?? ""}`}>{t.status}</span>
                    <span className="faint">{t.type === "approval" ? "人工核准" : (t.agent_id ?? "").replace("agent-", "")}{t.mode ? ` · ${t.mode}` : ""}{t.gate ? ` · ${t.gate}` : ""}</span>
                  </div>
                  <div className="row faint mono" style={{ fontSize: 12 }}>
                    {t.iteration ? <span>iter {t.iteration}</span> : null}
                    {t.started_at && <span>{fmtDate(t.started_at).slice(5)} → {t.ended_at ? fmtDate(t.ended_at).slice(11) : "…"}</span>}
                    {t.approval_id && <span className="tag warn">{t.approval_id}</span>}
                  </div>
                </div>
                {t.gate_results.length > 0 && (
                  <div className="stack" style={{ gap: 2, marginTop: 6 }}>
                    {t.gate_results.slice(-4).map((g, i) => (
                      <div key={i} className="faint" style={{ fontSize: 12 }}>
                        <span className={`tag ${g.result === "PASS" ? "ok" : "danger"}`}>{g.layer} {g.result}</span> <span className="mono">{fmtDate(g.at).slice(11)}</span> {g.details.slice(0, 2).join("；").slice(0, 160)}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
          <div>
            <div className="section-title">audit.log（最後 40 行）</div>
            <div className="stack" style={{ gap: 3 }}>
              {r.audit.map((a, i) => (
                <div key={i} className="agent-row" style={{ fontSize: 12 }}>
                  <span className="mono faint" style={{ width: 140 }}>{fmtDate(a.at)}</span>
                  <span className="tag">{a.action}</span>
                  <span className="faint mono">{a.actor.replace("agent-", "")}</span>
                  <span className="muted" style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{a.detail}</span>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </Drawer>
  );
}
