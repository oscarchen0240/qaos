import { useCallback, useEffect, useRef, useState } from "react";
import { PageHeader, Tabs, EmptyState } from "@/components/PageHeader";
import { Drawer } from "@/components/Drawer";
import { useToast } from "@/components/Toast";
import { refreshNav } from "@/lib/nav";
import { clickable } from "@/lib/a11y";
import { api, type BugDetail, type BugLite, type CommandOut, type TicketDraft } from "@/lib/api";
import { fmtDate } from "@/lib/format";
import { CommandBox } from "./CommandBox";

const SEV_CLASS: Record<string, string> = { critical: "danger", blocker: "danger", major: "warn", minor: "", trivial: "" };
const ST_CLASS: Record<string, string> = { OPEN: "danger", IN_PROGRESS: "accent", RESOLVED: "warn", VERIFYING: "warn", CLOSED: "ok", REJECTED: "" };
const ACTIONS: { key: string; label: string; hint: string }[] = [
  { key: "transition", label: "改狀態", hint: "依狀態機允許的目標" },
  { key: "resolve", label: "RD 已修復", hint: "登記外部參照（ticket / PR）" },
  { key: "verify", label: "複測通過", hint: "附 Execution（含 Evidence）" },
  { key: "close", label: "結案", hint: "" },
];

export function BugsPage() {
  const [list, setList] = useState<BugLite[]>([]);
  const [tab, setTab] = useState<"open" | "closed">("open");
  const [open, setOpen] = useState<string | null>(null);
  const { toast } = useToast();
  const load = useCallback(() => api.get<BugLite[]>("/api/tickets/bugs").then(setList).catch((e) => toast(`載入失敗：${e.message}`, "danger")), [toast]);
  useEffect(() => { load(); const id = setInterval(load, 10000); return () => clearInterval(id); }, [load]);
  const opens = list.filter((b) => !["CLOSED", "REJECTED"].includes(b.status));
  const closed = list.filter((b) => ["CLOSED", "REJECTED"].includes(b.status));
  const shown = tab === "open" ? opens : closed;
  return (
    <>
      <PageHeader eyebrow="Tickets" title="Bug" description="QAOS 開出並經你核准的正式 Bug（bugs/）。在這裡看內容、登記 RD 修復與複測，平台組好 bin/qaos bug 指令。" />
      <Tabs tabs={[{ key: "open", label: "未結案", count: opens.length }, { key: "closed", label: "已結案", count: closed.length }]} active={tab} onChange={(k) => setTab(k as typeof tab)} />
      <div className="page-body">
        {shown.length === 0 ? <EmptyState title="沒有 Bug" /> : (
          <table className="table">
            <thead><tr><th>單號</th><th>狀態</th><th>嚴重度</th><th>標題</th><th>Spec / 需求</th><th>證據</th><th>更新</th></tr></thead>
            <tbody>
              {shown.map((b) => (
                <tr key={b.bug_id} className="clickable" {...clickable(() => setOpen(b.bug_id), `開啟 ${b.bug_id}`)}>
                  <td className="mono">{b.bug_id}</td>
                  <td><span className={`tag ${ST_CLASS[b.status] ?? ""}`}>{b.status}</span></td>
                  <td><span className={`tag ${SEV_CLASS[b.severity] ?? ""}`}>{b.severity}</span></td>
                  <td style={{ maxWidth: 460 }}>{b.title}</td>
                  <td className="mono faint">{b.spec_id}@{b.spec_version}<br />{b.requirement_id}</td>
                  <td className="mono">{b.evidence_count}</td>
                  <td className="mono">{fmtDate(b.updated_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      <BugDrawer id={open} onClose={() => setOpen(null)} onChanged={() => { load(); refreshNav(); }} />
    </>
  );
}

function BugDrawer({ id, onClose, onChanged }: { id: string | null; onClose: () => void; onChanged: () => void }) {
  const [d, setD] = useState<BugDetail | null>(null);
  const [draft, setDraft] = useState<TicketDraft | null>(null);
  const [cmd, setCmd] = useState<CommandOut | null>(null);
  // 最新草稿（同步更新），避免連續 onBlur 時用到過期的 extra 互相覆蓋
  const latest = useRef<TicketDraft | null>(null);
  const { toast } = useToast();
  useEffect(() => {
    if (!id) { setD(null); setDraft(null); setCmd(null); latest.current = null; return; }
    api.get<BugDetail>(`/api/tickets/bugs/${id}`).then((x) => { setD(x); setDraft(x.draft); latest.current = x.draft; if (!["CLOSED", "REJECTED"].includes(x.status)) put({}, x); }).catch((e) => toast(`載入失敗：${e.message}`, "danger"));
  }, [id]); // eslint-disable-line react-hooks/exhaustive-deps
  const put = async (patch: Partial<Pick<TicketDraft, "decision" | "rationale" | "extra">>, base?: BugDetail) => {
    const tid = (base ?? d)?.bug_id ?? id; if (!tid) return;
    try {
      const r = await api.put<{ draft: TicketDraft } & CommandOut>(`/api/tickets/bugs/${tid}/draft`, patch);
      latest.current = { ...r.draft, extra: { ...(latest.current?.extra ?? {}), ...r.draft.extra } };
      setDraft(latest.current); setCmd({ command: r.command, warnings: r.warnings });
    } catch (e) { toast(`儲存失敗：${(e as Error).message}`, "danger"); }
  };
  const setExtra = (k: string, v: string) => {
    const extra = { ...(latest.current?.extra ?? {}), [k]: v };
    latest.current = { ...(latest.current ?? ({} as TicketDraft)), extra };
    put({ extra });
  };
  const active = !!d && !["CLOSED", "REJECTED"].includes(d.status);
  const action = draft?.decision ?? "transition";
  const steps = (d?.reproduction_steps ?? []).map((s) => typeof s === "string" ? s : s.action);
  return (
    <Drawer open={!!id} onClose={onClose} wide title={d ? d.bug_id : "Bug"} subtitle={d ? `${d.title}` : ""}>
      {!d ? <div className="faint">載入中…</div> : (
        <>
          <div className="card-tags">
            <span className={`tag ${ST_CLASS[d.status] ?? ""} big`}>{d.status}</span>
            <span className={`tag ${SEV_CLASS[d.severity] ?? ""}`}>severity {d.severity}</span>
            <span className="tag">priority {d.priority}</span>
            <span className="tag accent">{d.requirement_id}</span>
            <span className="tag">{d.spec_id}@{d.spec_version}</span>
            {d.approval_id && <span className="tag">核准 {d.approval_id}</span>}
            {d.external_ref && <span className="tag ok">外部 {d.external_ref}</span>}
          </div>
          <div className="panel stack" style={{ gap: 10 }}>
            <div><div className="section-title">期望</div><div>{d.expected_result}</div>{d.expected_result_spec_reference?.location && <div className="faint" style={{ fontSize: 12 }}>{d.expected_result_spec_reference.location}{d.expected_result_spec_reference.quote ? ` — 「${d.expected_result_spec_reference.quote}」` : ""}</div>}</div>
            <div><div className="section-title">實際</div><div>{d.actual_result}</div></div>
            {steps.length > 0 && <div><div className="section-title">重現步驟</div><ol className="tc-list">{steps.map((s, i) => <li key={i}>{s}</li>)}</ol></div>}
            {d.preconditions?.length > 0 && <div><div className="section-title">前置條件</div><ul className="tc-list">{d.preconditions.map((p, i) => <li key={i}>{p}</li>)}</ul></div>}
            {d.environment && <div><div className="section-title">環境</div><div className="mono faint" style={{ fontSize: 12 }}>{Object.entries(d.environment).map(([k, v]) => `${k}=${v}`).join(" · ")}</div></div>}
            <div><div className="section-title">影響</div><div className="muted">{d.impact}</div></div>
            <div><div className="section-title">疑似範圍</div><div className="muted">{d.suspected_area}</div></div>
            <div><div className="section-title">嚴重度理由</div><div className="muted" style={{ fontSize: 12 }}>{d.severity_rationale}</div></div>
            <div><div className="section-title">證據 · {d.evidence_ids?.length ?? 0}</div><div className="card-tags">{(d.evidence_ids ?? []).map((e) => <span key={e} className="tag mono">{e}</span>)}</div></div>
          </div>

          {active && (
            <div className="panel stack" style={{ gap: 10 }}>
              <div className="step-title">下一步動作</div>
              <div className="row" style={{ flexWrap: "wrap" }}>{ACTIONS.map((a) => <button key={a.key} className={`btn sm ${action === a.key ? "primary" : "ghost"}`} title={a.hint} onClick={() => put({ decision: a.key })}>{a.label}</button>)}</div>
              {action === "transition" && (
                <div className="form-grid">
                  <div className="field"><label>目標狀態（狀態機允許）</label>
                    <select className="select" value={draft?.extra?.to ?? ""} onChange={(e) => setExtra("to", e.target.value)}>
                      <option value="">— 選擇 —</option>
                      {d.allowed.map((a) => <option key={a.to} value={a.to}>{a.to}{a.requires ? `（需 ${a.requires}）` : ""}</option>)}
                    </select>
                  </div>
                  <div className="field"><label>觸發說明</label><input className="input" defaultValue={draft?.extra?.trigger ?? ""} onBlur={(e) => setExtra("trigger", e.target.value.trim())} /></div>
                </div>
              )}
              {action === "resolve" && (
                <div className="form-grid">
                  <div className="field"><label>外部參照（RD ticket / PR）<span className="req">*</span></label><input className="input" defaultValue={draft?.extra?.external_ref ?? ""} onBlur={(e) => setExtra("external_ref", e.target.value.trim())} /></div>
                  <div className="field"><label>修復者</label><input className="input" defaultValue={draft?.extra?.fixed_by ?? ""} onBlur={(e) => setExtra("fixed_by", e.target.value.trim())} /></div>
                </div>
              )}
              {action === "verify" && <div className="field"><label>複測 Execution ID<span className="req">*</span></label><input className="input" defaultValue={draft?.extra?.execution_id ?? ""} onBlur={(e) => setExtra("execution_id", e.target.value.trim())} placeholder="EXE-…（由 bin/qaos execution import 取得）" /></div>}
              <div className="field"><label>備註／理由</label><textarea className="textarea" style={{ minHeight: 56 }} defaultValue={draft?.rationale ?? ""} onBlur={(e) => { if (e.target.value !== (draft?.rationale ?? "")) put({ rationale: e.target.value }); }} /></div>
            </div>
          )}
          {active && <CommandBox kind="bug" ticketId={d.bug_id} cmd={cmd} draft={draft} onSent={onChanged} />}

          <div>
            <div className="section-title">歷程</div>
            <div className="stack" style={{ gap: 3 }}>
              {(d.history ?? []).map((h, i) => <div key={i} className="hist-row"><span className="mono faint">{fmtDate(h.at)}</span><span className={`tag ${ST_CLASS[h.to_status] ?? ""}`}>{h.to_status}</span><span className="faint">{h.by}{h.trigger ? ` · ${h.trigger}` : ""}</span></div>)}
            </div>
          </div>
        </>
      )}
    </Drawer>
  );
}
