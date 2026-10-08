import { useCallback, useEffect, useRef, useState } from "react";
import { PageHeader, Tabs, EmptyState } from "@/components/PageHeader";
import { Drawer } from "@/components/Drawer";
import { useToast } from "@/components/Toast";
import { refreshNav } from "@/lib/nav";
import { clickable } from "@/lib/a11y";
import { api, type ClarificationDetail, type ClarificationLite, type CommandOut, type TicketDraft } from "@/lib/api";
import { fmtDate } from "@/lib/format";
import { CommandBox } from "./CommandBox";

const ST_LABEL: Record<string, string> = { OPEN: "待處理", ASKED: "已問 PM", ANSWERED: "已回答", INCORPORATED: "已納入（待套用）", APPLIED: "已套用", WITHDRAWN: "已撤回" };
const ST_CLASS: Record<string, string> = { OPEN: "warn", ASKED: "accent", ANSWERED: "ok", INCORPORATED: "ok", APPLIED: "", WITHDRAWN: "" };
// 還需要人處理的狀態；終止狀態只有 APPLIED、WITHDRAWN。INCORPORATED 是答案已被提交的 revision／BugDraft 引用，仍待人工套用或撤回。
const ACTIVE = ["OPEN", "ASKED", "ANSWERED", "INCORPORATED"];
const PENDING_APPLY = ["ANSWERED", "INCORPORATED"];
const RES_LABEL: Record<string, string> = { spec_updated: "Spec 已更新", requirement_clarified: "需求已釐清", no_change: "不需更動", out_of_scope: "超出範圍" };
const ACTION_LABEL: Record<string, string> = { ask: "送問 PM", answer: "登記回答", apply: "套用", withdraw: "撤回" };
const ACTION_FOR: Record<string, string> = { ASKED: "ask", ANSWERED: "answer", APPLIED: "apply", WITHDRAWN: "withdraw" };

export function ClarificationsPage() {
  const [list, setList] = useState<ClarificationLite[]>([]);
  const [tab, setTab] = useState<"open" | "answered" | "done">("open");
  const [open, setOpen] = useState<string | null>(null);
  const { toast } = useToast();
  const load = useCallback(() => api.get<ClarificationLite[]>("/api/tickets/clarifications").then(setList).catch((e) => toast(`載入失敗：${e.message}`, "danger")), [toast]);
  useEffect(() => { load(); const id = setInterval(load, 10000); return () => clearInterval(id); }, [load]);
  const opens = list.filter((c) => ["OPEN", "ASKED"].includes(c.status));
  const answered = list.filter((c) => PENDING_APPLY.includes(c.status));
  const done = list.filter((c) => !ACTIVE.includes(c.status));
  const shown = tab === "open" ? opens : tab === "answered" ? answered : done;
  return (
    <>
      <PageHeader eyebrow="Tickets" title="釐清" description="Spec Analyst 找到的需求歧義（clarifications/）。在這裡送問 PM、登記回答，平台組好 bin/qaos clarification 指令。" />
      <Tabs tabs={[{ key: "open", label: "待處理", count: opens.length }, { key: "answered", label: "已回答・待套用", count: answered.length }, { key: "done", label: "已結案", count: done.length }]} active={tab} onChange={(k) => setTab(k as typeof tab)} />
      <div className="page-body">
        {shown.length === 0 ? <EmptyState title={tab === "open" ? "沒有待處理的釐清單" : tab === "answered" ? "沒有已回答待套用的釐清單" : "沒有已結案的釐清單"} /> : (
          <table className="table">
            <thead><tr><th>單號</th><th>狀態</th><th>Spec</th><th>需求</th><th>問題</th><th>提出</th></tr></thead>
            <tbody>
              {shown.map((c) => (
                <tr key={c.clarification_id} className="clickable" {...clickable(() => setOpen(c.clarification_id), `開啟 ${c.clarification_id}`)}>
                  <td className="mono">{c.clarification_id}</td>
                  <td><span className={`tag ${ST_CLASS[c.status] ?? ""}`}>{ST_LABEL[c.status] ?? c.status}</span></td>
                  <td className="mono faint">{c.spec_id}@{c.spec_version}</td>
                  <td className="mono">{c.requirement_id ?? "—"}</td>
                  <td style={{ maxWidth: 460 }}><div className="clamp2" title={c.question}>{c.question}</div></td>
                  <td className="mono">{fmtDate(c.raised_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      <ClrDrawer id={open} onClose={() => setOpen(null)} onChanged={() => { load(); refreshNav(); }} />
    </>
  );
}

function ClrDrawer({ id, onClose, onChanged }: { id: string | null; onClose: () => void; onChanged: () => void }) {
  const [d, setD] = useState<ClarificationDetail | null>(null);
  const [draft, setDraft] = useState<TicketDraft | null>(null);
  const [cmd, setCmd] = useState<CommandOut | null>(null);
  // 最新草稿（同步更新），避免連續 onBlur 時用到過期的 extra 互相覆蓋
  const latest = useRef<TicketDraft | null>(null);
  const { toast } = useToast();
  useEffect(() => {
    if (!id) { setD(null); setDraft(null); setCmd(null); latest.current = null; return; }
    api.get<ClarificationDetail>(`/api/tickets/clarifications/${id}`).then((x) => { setD(x); setDraft(x.draft); latest.current = x.draft; if (ACTIVE.includes(x.status)) put({}, x); })
      .catch((e) => toast(`載入失敗：${e.message}`, "danger"));
  }, [id]); // eslint-disable-line react-hooks/exhaustive-deps
  const put = async (patch: Partial<Pick<TicketDraft, "decision" | "rationale" | "extra">>, base?: ClarificationDetail) => {
    const tid = (base ?? d)?.clarification_id ?? id; if (!tid) return;
    try {
      const r = await api.put<{ draft: TicketDraft } & CommandOut>(`/api/tickets/clarifications/${tid}/draft`, patch);
      latest.current = { ...r.draft, extra: { ...(latest.current?.extra ?? {}), ...r.draft.extra } };
      setDraft(latest.current); setCmd({ command: r.command, warnings: r.warnings });
    } catch (e) { toast(`儲存失敗：${(e as Error).message}`, "danger"); }
  };
  const setExtra = (k: string, v: string) => {
    const extra = { ...(latest.current?.extra ?? {}), [k]: v };
    latest.current = { ...(latest.current ?? ({} as TicketDraft)), extra };
    put({ extra });
  };
  const active = !!d && ACTIVE.includes(d.status);
  const actions = (d?.allowed ?? []).map((to) => ACTION_FOR[to]).filter(Boolean);
  const action = draft?.decision ?? actions[0] ?? null;
  return (
    <Drawer open={!!id} onClose={onClose} wide title={d ? d.clarification_id : "釐清單"} subtitle={d ? `${d.spec_id}@${d.spec_version} · ${d.requirement_id ?? ""} · ${ST_LABEL[d.status] ?? d.status}` : ""}>
      {!d ? <div className="faint">載入中…</div> : (
        <>
          <div className="clr-hero">
            <div className="clr-q">{d.question}</div>
            <dl className="kv">
              <dt>需求</dt><dd><span className="tag accent">{d.requirement_id ?? "—"}</span> <span className="mono faint">{d.spec_id}@{d.spec_version}</span></dd>
              <dt>提出</dt><dd>{d.raised_by} · {fmtDate(d.raised_at)}{d.run_id ? <span className="mono faint"> · {d.run_id}</span> : null}</dd>
              {d.asked_to && <><dt>已問</dt><dd>{d.asked_to} · {fmtDate(d.asked_at)}</dd></>}
              {d.answered_by && <><dt>回答</dt><dd>{d.answered_by} · {fmtDate(d.answered_at)} · <span className="tag ok">{RES_LABEL[d.resolution ?? ""] ?? d.resolution}</span></dd></>}
            </dl>
            {d.spec_reference?.quote && (
              <div className="spec-quote block">
                <div className="tc2-sec-t">Spec 原文{d.spec_reference.location ? ` · ${d.spec_reference.location}` : ""}</div>
                <q>{d.spec_reference.quote}</q>
              </div>
            )}
            {d.context && (
              <div className="tc2-sec"><div className="tc2-sec-t">為什麼要問</div>{d.context.split(/\n+/).filter(Boolean).map((para, i) => <p key={i} className="para">{para}</p>)}</div>
            )}
            {d.impact && <div className="tc2-sec"><div className="tc2-sec-t">不回答的影響</div><p className="para" style={{ color: "var(--warn)" }}>{d.impact}</p></div>}
            {d.options?.length > 0 && <div className="tc2-sec"><div className="tc2-sec-t">Spec Analyst 提供的選項</div><ol className="tc-steps">{(d.options as unknown[]).map((o, i) => <li key={i}>{typeof o === "string" ? o : JSON.stringify(o)}</li>)}</ol></div>}
            {d.answer && <div className="tc2-sec answer"><div className="tc2-sec-t">PM 的回答</div><p className="para">{d.answer}</p></div>}
          </div>

          {active && actions.length > 0 && (
            <div className="panel stack" style={{ gap: 10 }}>
              <div className="step-title">下一步動作</div>
              <div className="row">{actions.map((a) => <button key={a} className={`btn sm ${action === a ? "primary" : "ghost"}`} onClick={() => put({ decision: a })}>{ACTION_LABEL[a]}</button>)}</div>
              {action === "ask" && <div className="field"><label>問誰（PM 名字或信箱）</label><input className="input" defaultValue={draft?.extra?.asked_to ?? ""} onBlur={(e) => setExtra("asked_to", e.target.value.trim())} /></div>}
              {action === "answer" && (
                <>
                  <div className="form-grid">
                    <div className="field"><label>回答者</label><input className="input" defaultValue={draft?.extra?.answered_by ?? d.asked_to ?? ""} onBlur={(e) => setExtra("answered_by", e.target.value.trim())} placeholder="PM 名字" /></div>
                    <div className="field"><label>落地方式</label>
                      <select className="select" value={draft?.extra?.resolution ?? "requirement_clarified"} onChange={(e) => setExtra("resolution", e.target.value)}>
                        {Object.entries(RES_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                      </select>
                    </div>
                    {(draft?.extra?.resolution ?? "") === "spec_updated" && <div className="field"><label>新的 spec 版本</label><input className="input" defaultValue={draft?.extra?.spec_version ?? ""} onBlur={(e) => setExtra("spec_version", e.target.value.trim())} placeholder="例如 0.5" /></div>}
                  </div>
                  <div className="field"><label>PM 的回答（逐字，會進 --answer）</label><textarea className="textarea" defaultValue={draft?.rationale ?? ""} onBlur={(e) => { if (e.target.value !== (draft?.rationale ?? "")) put({ rationale: e.target.value }); }} /></div>
                </>
              )}
              {action === "withdraw" && <div className="field"><label>撤回原因（必填，會進 --reason）</label><input className="input" defaultValue={draft?.rationale ?? ""} onBlur={(e) => put({ rationale: e.target.value })} /></div>}
              {action === "apply" && <div className="faint" style={{ fontSize: 12.5 }}>套用要選落地路徑（a6／a6b／a7），並對重新掃描出的每張候選 TC 下結論，由 QA session 逐條判定，指揮台不執行；下方只提供指令骨架。</div>}
            </div>
          )}

          {active && <CommandBox kind="clarification" ticketId={d.clarification_id} cmd={cmd} draft={draft} onSent={onChanged} />}

          <div>
            <div className="section-title">歷程</div>
            <div className="stack" style={{ gap: 3 }}>
              {d.history.map((h, i) => <div key={i} className="hist-row"><span className="mono faint">{fmtDate(h.at)}</span><span className={`tag ${ST_CLASS[h.to_status] ?? ""}`}>{ST_LABEL[h.to_status] ?? h.to_status}</span><span className="faint">{h.by}{h.trigger ? ` · ${h.trigger}` : ""}</span></div>)}
            </div>
          </div>
        </>
      )}
    </Drawer>
  );
}
