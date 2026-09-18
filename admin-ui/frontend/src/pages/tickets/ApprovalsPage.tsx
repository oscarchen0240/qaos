import { useCallback, useEffect, useRef, useState } from "react";
import { PageHeader, Tabs, EmptyState } from "@/components/PageHeader";
import { Drawer } from "@/components/Drawer";
import { useConfirm } from "@/components/Confirm";
import { useToast } from "@/components/Toast";
import { refreshNav } from "@/lib/nav";
import { clickable } from "@/lib/a11y";
import { api, type ApprovalDetail, type ApprovalItem, type ApprovalLite, type CommandOut, type Memo, type TicketDraft } from "@/lib/api";
import { fmtDate } from "@/lib/format";
import { CommandBox } from "./CommandBox";
import { CaretDown, CaretRight, Warning, CheckCircle, XCircle } from "@phosphor-icons/react";

const TYPE_LABEL: Record<string, string> = { ACTIVATE_TESTCASE: "啟用 TC", HUMAN_OVERRIDE: "人工裁決", NEEDS_DECISION: "需要決定", RETIRE_TESTCASE: "退役 TC", OPEN_BUG: "開 Bug", CLOSE_BUG: "關 Bug", APPLY_CHANGE: "套用變更", RESOLVE_AMBIGUITY: "釐清歧義" };
const DEC_LABEL: Record<string, string> = { approve: "核准", reject: "退回", override: "強制通過" };
const DEFAULT_REJECT = "未採用：Phase 2 既有 TC 已覆蓋（交叉比對後不採用）";
const REC_REJECT = "交叉比對不採用（依 shadow-test 文件）";

/** 列表用的一句話摘要：ACTIVATE_TESTCASE 只講數量，完整句子放 title */
function shortSummary(a: ApprovalLite): string {
  if (a.type === "ACTIVATE_TESTCASE") {
    const m = a.summary.match(/含\s*(\d+)\s*條 exploratory/);
    return `${a.item_count} 條 TC 待啟用${m ? ` · ${m[1]} 條 exploratory` : ""}`;
  }
  return a.summary.length > 90 ? a.summary.slice(0, 90) + "…" : a.summary;
}

export function ApprovalsPage() {
  const [list, setList] = useState<ApprovalLite[]>([]);
  const [tab, setTab] = useState<"pending" | "decided">("pending");
  const [open, setOpen] = useState<string | null>(null);
  const { toast } = useToast();
  const load = useCallback(() => api.get<ApprovalLite[]>("/api/tickets/approvals").then(setList).catch((e) => toast(`載入失敗：${e.message}`, "danger")), [toast]);
  useEffect(() => { load(); const id = setInterval(load, 10000); return () => clearInterval(id); }, [load]);
  const pending = list.filter((a) => a.status === "PENDING");
  const decided = list.filter((a) => a.status !== "PENDING");
  const shown = tab === "pending" ? pending : decided;
  const dayAgo = Date.now() - 86400_000;
  const autoRecent = decided.filter((a) => ["RETIRE_TESTCASE", "CLOSE_BUG"].includes(a.type) && a.decided_at && new Date(a.decided_at).getTime() > dayAgo);
  return (
    <>
      <PageHeader eyebrow="Tickets" title="核准" description="QAOS 開給你的核准單（approvals/）。在這裡逐條看、標決定與理由，平台幫你組好 bin/qaos approve 指令。" />
      <Tabs tabs={[{ key: "pending", label: "等你決定", count: pending.length }, { key: "decided", label: "已決定", count: decided.length }]} active={tab} onChange={(k) => setTab(k as typeof tab)} />
      <div className="page-body">
        {tab === "pending" && autoRecent.length > 0 && (
          <div className="notice" style={{ marginBottom: 10 }}>最近 24 小時 QAOS 自動決定了 {autoRecent.length} 張審計用核准單（{Array.from(new Set(autoRecent.map((a) => TYPE_LABEL[a.type] ?? a.type))).join("、")}），不需要你處理，在「已決定」分頁。</div>
        )}
        {shown.length === 0 ? <EmptyState title={tab === "pending" ? "沒有等待中的核准單" : "還沒有已決定的核准單"}>{tab === "pending" ? "QAOS 的 run 走到人工核准節點時，單子會出現在這裡。" : ""}</EmptyState> : (
          <table className="table">
            <thead><tr><th>單號</th><th>類型</th><th>Run</th><th>摘要</th><th>項目</th><th>開單</th>{tab === "decided" && <th>決定</th>}</tr></thead>
            <tbody>
              {shown.map((a) => (
                <tr key={a.approval_id} className="clickable" {...clickable(() => setOpen(a.approval_id), `開啟 ${a.approval_id}`)}>
                  <td className="mono">{a.approval_id}</td>
                  <td><span className={`tag ${a.type === "ACTIVATE_TESTCASE" ? "cyan" : a.type === "HUMAN_OVERRIDE" ? "danger" : "warn"}`}>{TYPE_LABEL[a.type] ?? a.type}</span></td>
                  <td className="mono faint">{a.run_id}</td>
                  <td style={{ maxWidth: 420 }} title={a.summary}>{shortSummary(a)}</td>
                  <td className="mono">{a.item_count || "—"}</td>
                  <td className="mono">{fmtDate(a.requested_at)}</td>
                  {tab === "decided" && <td><span className={`tag ${a.decision === "approve" ? "ok" : a.decision === "reject" ? "danger" : "warn"}`}>{DEC_LABEL[a.decision ?? ""] ?? a.decision}{a.selected_option ? ` · ${a.selected_option}` : ""}</span></td>}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      <ApprovalDrawer id={open} onClose={() => setOpen(null)} onChanged={() => { load(); refreshNav(); }} />
    </>
  );
}

function ApprovalDrawer({ id, onClose, onChanged }: { id: string | null; onClose: () => void; onChanged: () => void }) {
  const [d, setD] = useState<ApprovalDetail | null>(null);
  const [draft, setDraft] = useState<TicketDraft | null>(null);
  const [cmd, setCmd] = useState<CommandOut | null>(null);
  const [openTc, setOpenTc] = useState<Set<string>>(new Set());
  const [filter, setFilter] = useState<"all" | "exploratory" | "high" | "rejected">("all");
  const [q, setQ] = useState("");
  const [showAssump, setShowAssump] = useState(false);
  const latest = useRef<TicketDraft | null>(null);
  const { toast } = useToast();
  const confirm = useConfirm();

  useEffect(() => {
    if (!id) { setD(null); setDraft(null); setCmd(null); latest.current = null; return; }
    setFilter("all"); setQ(""); setOpenTc(new Set()); setShowAssump(false);
    api.get<ApprovalDetail>(`/api/tickets/approvals/${id}`).then(async (x) => {
      setD(x);
      // 安全預設：啟用類、同 spec 已有 Phase 2 ACTIVE、還沒有草稿 → 全部先標退回，要採用的再逐條標通過（避免整批放行繞過交叉比對）
      if (!x.draft && x.status === "PENDING" && x.context && x.context.phase2_active > 0 && x.items.length > 0) {
        const per: TicketDraft["per_item"] = {};
        for (const it of x.items) per[it.testcase_id] = { decision: "reject", reason: DEFAULT_REJECT };
        const r = await api.put<{ draft: TicketDraft } & CommandOut>(`/api/tickets/approvals/${id}/draft`, { decision: "approve", per_item: per });
        setDraft(r.draft); latest.current = r.draft; setCmd({ command: r.command, warnings: r.warnings, rejected: r.rejected });
        toast("此 spec 已有 Phase 2 ACTIVE TC：這批預設全部退回，請逐條把要採用的標通過", "info");
        return;
      }
      setDraft(x.draft); latest.current = x.draft;
      const c = await api.get<CommandOut>(`/api/tickets/approvals/${id}/command`); setCmd(c);
    }).catch((e) => toast(`載入失敗：${e.message}`, "danger"));
  }, [id, toast]);

  const setAll = (decision: "approve" | "reject") => {
    if (!d) return;
    const per: TicketDraft["per_item"] = {};
    if (decision === "reject") for (const it of d.items) per[it.testcase_id] = { decision: "reject", reason: latest.current?.per_item?.[it.testcase_id]?.reason || DEFAULT_REJECT };
    latest.current = { ...(latest.current ?? ({} as TicketDraft)), per_item: per };
    put({ per_item: per });
  };
  const applyRecommendation = () => {
    const rec = d?.context?.recommendation;
    if (!d || !rec?.found) return;
    const adopt = new Set(rec.adopt);
    const per: TicketDraft["per_item"] = {};
    for (const it of d.items) if (!adopt.has(it.testcase_id)) per[it.testcase_id] = { decision: "reject", reason: latest.current?.per_item?.[it.testcase_id]?.reason || REC_REJECT };
    latest.current = { ...(latest.current ?? ({} as TicketDraft)), per_item: per, decision: "approve" };
    put({ decision: "approve", per_item: per });
    toast(`已依建議：通過 ${adopt.size} 條、退回 ${d.items.length - adopt.size} 條`, "ok");
  };
  const beforeSend = async () => {
    if (!d?.context) return true;
    const rej = (cmd?.rejected ?? []).length;
    if (d.context.needs_review && rej === 0) {
      return confirm({ title: `整批啟用 ${d.items.length} 條？`, message: `這份 spec 已有 ${d.context.phase2_active} 條 Phase 2 ACTIVE TC，這批還沒有交叉比對紀錄（找不到 shadow-test 文件）。整批啟用會把重疊的 TC 也放進 Registry。`, confirmText: "我確定整批啟用", danger: true });
    }
    return true;
  };

  const put = async (patch: Partial<Pick<TicketDraft, "decision" | "option" | "rationale" | "per_item">>) => {
    if (!id) return;
    try {
      const r = await api.put<{ draft: TicketDraft } & CommandOut>(`/api/tickets/approvals/${id}/draft`, patch);
      latest.current = { ...r.draft, per_item: { ...(latest.current?.per_item ?? {}), ...r.draft.per_item } };
      setDraft(latest.current); setCmd({ command: r.command, warnings: r.warnings, rejected: r.rejected });
    } catch (e) { toast(`儲存失敗：${(e as Error).message}`, "danger"); }
  };
  const setItem = (tc: string, decision: "approve" | "reject", reason?: string) => {
    const per = { ...(latest.current?.per_item ?? {}) };
    per[tc] = { ...(per[tc] ?? {}), decision, ...(reason !== undefined ? { reason } : {}) };
    if (decision === "approve") delete per[tc];
    latest.current = { ...(latest.current ?? ({} as TicketDraft)), per_item: per };
    put({ per_item: per });
  };
  const pending = d?.status === "PENDING";
  const dec = draft?.decision ?? (d?.decision?.decision ?? null);
  const rejectedSet = new Set(cmd?.rejected ?? []);
  const toggle = (t: string) => setOpenTc((s) => { const n = new Set(s); n.has(t) ? n.delete(t) : n.add(t); return n; });
  const jumpTo = (t: string) => { setFilter("all"); setQ(""); setOpenTc((s) => new Set(s).add(t)); setTimeout(() => document.getElementById(`apr-tc-${t}`)?.scrollIntoView({ block: "center" }), 50); };

  const items = d?.items ?? [];
  const draftArt = d?.artifacts?.find((a) => a.type === "TestCaseDraft") ?? null;
  const reportArt = d?.artifacts?.find((a) => a.type === "TestDesignReport") ?? null;
  const valArt = d?.artifacts?.find((a) => a.type === "TestValidationReport" || a.type === "BugValidationReport") ?? null;
  // 選項 → 指令：key 是 approve/reject/override 就直接當整體決定；其他（continue/retry/cancel…）是 --option，整體決定固定 approve
  const pickOption = (key: string) => {
    if (["approve", "reject", "override"].includes(key)) put({ decision: key, option: null });
    else put({ decision: "approve", option: key });
  };
  const optionActive = (key: string) => ["approve", "reject", "override"].includes(key) ? (draft?.decision === key && !draft?.option) : draft?.option === key;
  const isRej = (it: ApprovalItem) => rejectedSet.has(it.testcase_id) || it.decided === "reject";
  const stats = {
    total: items.length,
    exploratory: items.filter((i) => i.exploratory).length,
    prio: ["critical", "high", "medium", "low"].map((p) => [p, items.filter((i) => i.priority === p).length] as const).filter(([, n]) => n > 0),
    rejected: items.filter(isRej).length,
  };
  const ql = q.trim().toLowerCase();
  const shown = items.filter((it) => (filter === "all" || (filter === "exploratory" && it.exploratory) || (filter === "high" && (it.priority === "high" || it.priority === "critical")) || (filter === "rejected" && isRej(it)))
    && (!ql || [it.testcase_id, it.title ?? "", it.expected_result ?? "", ...it.requirement_ids].join(" ").toLowerCase().includes(ql)));

  return (
    <Drawer open={!!id} onClose={onClose} wide title={d ? `${d.approval_id} · ${TYPE_LABEL[d.type] ?? d.type}` : "核准單"} subtitle={d ? `${d.run_id} · ${d.run?.spec_id ?? ""}@${d.run?.spec_version ?? ""}` : ""}>
      {!d ? <div className="faint">載入中…</div> : (
        <>
          {/* 1. 一眼看懂這張單在問什麼 */}
          <div className="apr-hero">
            <div className="apr-question">{d.type === "ACTIVATE_TESTCASE" ? `這 ${stats.total} 條 TC 要不要進 Registry 成為 ACTIVE？` : d.summary}</div>
            {items.length > 0 ? (
              <div className="apr-stats">
                <div className="apr-stat"><div className="apr-stat-v">{stats.total}</div><div className="apr-stat-k">TC 版本</div></div>
                <div className="apr-stat"><div className={`apr-stat-v ${stats.exploratory ? "warn" : ""}`}>{stats.exploratory}</div><div className="apr-stat-k">exploratory</div></div>
                {stats.prio.map(([p, n]) => <div key={p} className="apr-stat"><div className={`apr-stat-v ${p === "high" || p === "critical" ? "danger" : p === "medium" ? "warn" : ""}`}>{n}</div><div className="apr-stat-k">{p}</div></div>)}
                {pending && <div className="apr-stat"><div className={`apr-stat-v ${stats.rejected ? "danger" : "ok"}`}>{stats.rejected}</div><div className="apr-stat-k">你退回</div></div>}
              </div>
            ) : draftArt ? (
              <div className="apr-stats">
                <div className="apr-stat"><div className="apr-stat-v">{draftArt.count ?? 0}</div><div className="apr-stat-k">草稿 TC</div></div>
                <div className="apr-stat"><div className={`apr-stat-v ${draftArt.exploratory ? "warn" : ""}`}>{draftArt.exploratory ?? 0}</div><div className="apr-stat-k">exploratory</div></div>
                {reportArt?.uncovered?.length ? <div className="apr-stat"><div className="apr-stat-v warn">{reportArt.uncovered.length}</div><div className="apr-stat-k">未覆蓋需求</div></div> : null}
                {draftArt.iteration != null && <div className="apr-stat"><div className="apr-stat-v">{draftArt.iteration + 1}</div><div className="apr-stat-k">第幾輪</div></div>}
              </div>
            ) : null}
            <dl className="kv">
              <dt>開單</dt><dd>{fmtDate(d.requested_at)} · {d.requested_by}</dd>
              <dt>Run</dt><dd><span className="mono">{d.run_id}</span> {d.run && <span className={`tag ${d.run.status === "WAITING_HUMAN" ? "warn" : ""}`}>{d.run.status === "WAITING_HUMAN" ? "等你決定" : d.run.status}</span>}</dd>
              {!pending && d.decision && <><dt>決定</dt><dd><span className={`tag ${d.decision.decision === "approve" ? "ok" : "danger"}`}>{DEC_LABEL[d.decision.decision] ?? d.decision.decision}</span> {d.decision.decided_by} · {fmtDate(d.decision.decided_at)}{d.decision.rationale ? <div className="muted" style={{ marginTop: 4 }}>{d.decision.rationale}</div> : null}</dd></>}
            </dl>
            <MemoPanel memo={d.memo} options={d.options ?? []} pending={pending} onPick={pickOption} aprId={d.approval_id} />
            {(draftArt || reportArt || valArt) && (
              <details className="details" open={!items.length}>
                <summary>這張單引用的產物{draftArt ? ` · 草稿 ${draftArt.count} 條` : ""}{reportArt ? " · 設計報告" : ""}{valArt ? " · 驗證報告" : ""}</summary>
                <div className="stack" style={{ gap: 12, marginTop: 8 }}>
                  {valArt && (
                    <div className="tc2-sec"><div className="tc2-sec-t">驗證報告 · {valArt.result ?? ""}</div>
                      {valArt.summary && <p className="para">{valArt.summary}</p>}
                      {valArt.issues?.length ? <ul className="tc-list">{valArt.issues.map((i, k) => <li key={k}><span className={`tag ${/blocker|critical|major/.test(i.severity ?? "") ? "danger" : "warn"}`}>{i.severity}</span> <span className="mono faint">{i.draft_id}</span> {i.message}</li>)}</ul> : <div className="faint">沒有列出問題</div>}
                    </div>
                  )}
                  {reportArt && (
                    <>
                      {reportArt.assumptions?.length ? <div className="tc2-sec"><div className="tc2-sec-t">設計報告：假設（{reportArt.assumptions.length}）</div>{reportArt.assumptions.map((a, k) => <div key={k} className="assump-text">{a}</div>)}</div> : null}
                      {reportArt.uncovered?.length ? <div className="tc2-sec"><div className="tc2-sec-t">未覆蓋的需求</div><ul className="tc-list">{reportArt.uncovered.map((u, k) => <li key={k}><span className="tag accent">{u.requirement_id}</span> {u.reason}</li>)}</ul></div> : null}
                      {reportArt.techniques?.length ? <div className="card-tags">{reportArt.techniques.map((t) => <span key={t.technique} className="tag">{t.technique} {t.count}</span>)}</div> : null}
                    </>
                  )}
                  {draftArt?.cases?.length ? (
                    <div className="tc2-sec"><div className="tc2-sec-t">草稿 TC（{draftArt.count}，exploratory 標黃）</div>
                      <div className="stack" style={{ gap: 6 }}>
                        {draftArt.cases.map((c, k) => (
                          <div key={c.draft_id} className={`tc2 ${c.exploratory ? "" : ""}`} style={c.exploratory ? { borderColor: "rgba(255,176,32,0.45)" } : undefined}>
                            <div className="tc2-head" style={{ cursor: "default" }}>
                              <span className="tc2-idx mono">{k + 1}</span>
                              <div className="tc2-main">
                                <div className="tc2-title">{c.title}</div>
                                <div className="tc2-meta"><span className={`tag ${c.priority === "high" ? "danger" : c.priority === "medium" ? "warn" : ""}`}>{c.priority}</span>{c.exploratory && <span className="tag warn">exploratory</span>}{c.requirement_ids.slice(0, 3).map((r) => <span key={r} className="tag accent">{r}</span>)}</div>
                                {c.assumptions.map((a, i) => <div key={i} className="assump-text">{a}</div>)}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : null}
                </div>
              </details>
            )}
            {d.context && d.context.phase2_active > 0 && (
              <div className={`assump-box ${d.context.cross_compared ? "ok" : ""}`}>
                <div className="row" style={{ gap: 6, fontWeight: 600, fontSize: 13 }}>
                  {d.context.cross_compared ? <CheckCircle className="ic sm" aria-hidden="true" /> : <Warning className="ic sm" aria-hidden="true" />}
                  {d.context.spec_key} 已有 {d.context.phase2_active} 條 Phase 2 ACTIVE TC
                  {d.context.cross_compared ? "，這批已有交叉比對紀錄" : "，這批還沒有交叉比對紀錄"}
                </div>
                <div style={{ fontSize: 12.5, lineHeight: 1.6 }}>
                  {d.context.cross_compared
                    ? <>比對紀錄：<span className="mono">{d.context.shadow_doc?.split("/").pop()}</span>。</>
                    : <>QA session 通常會先做 Phase 2×3 交叉比對再決定。這批預設全部退回，只把有新增價值的標通過；或先到 QA session 說「先做 {d.context.spec_key} 的交叉比對」再回來。</>}
                  {d.context.overlap_count > 0 && <> 需求重疊提示：{d.context.overlap_count} 條與既有 TC 有相同需求編號（列在每條 TC 下，只是線索，不是語意比對）。</>}
                </div>
                {d.context.recommendation && (
                  d.context.recommendation.found ? (
                    <div className="rec-box">
                      <div className="row" style={{ gap: 8, flexWrap: "wrap" }}>
                        <span style={{ fontWeight: 600, fontSize: 13 }}>文件建議採用 {d.context.recommendation.adopt.length} 條，其餘 {d.context.recommendation.reject.length} 條不採用</span>
                        {pending && <button className="btn sm primary" onClick={applyRecommendation}>依建議套用</button>}
                        {pending && <button className="link-btn" style={{ fontSize: 12 }} onClick={() => { setFilter("all"); setQ(""); setOpenTc(new Set(d.context!.recommendation!.adopt)); setTimeout(() => document.getElementById(`apr-tc-${d.context!.recommendation!.adopt[0]}`)?.scrollIntoView({ block: "center" }), 50); }}>看建議採用的那幾條</button>}
                      </div>
                      <div className="card-tags">{d.context.recommendation.adopt.map((t) => <button key={t} className="tag ok chip" onClick={() => jumpTo(t)}>{t}</button>)}</div>
                      <div className="faint" style={{ fontSize: 11.5 }}>依據（文件原句）：{d.context.recommendation.evidence.map((e, i) => <div key={i} className="prewrap" style={{ margin: 0, fontSize: 11.5 }}>{e}</div>)}</div>
                    </div>
                  ) : <div className="faint" style={{ fontSize: 12 }}>{d.context.recommendation.note}</div>
                )}
              </div>
            )}
            {d.type === "ACTIVATE_TESTCASE" && stats.exploratory > 0 && (
              <div className="assump-box">
                <button className="link-btn row" style={{ gap: 6 }} onClick={() => setShowAssump(!showAssump)} aria-expanded={showAssump}>
                  {showAssump ? <CaretDown className="ic sm" aria-hidden="true" /> : <CaretRight className="ic sm" aria-hidden="true" />}
                  <Warning className="ic sm" aria-hidden="true" />核准即等於確認這 {stats.exploratory} 條 exploratory 的假設，先看一遍
                </button>
                {showAssump && (
                  <ol className="assump-list">
                    {items.filter((i) => i.exploratory).map((it) => (
                      <li key={it.testcase_id}>
                        <div className="row" style={{ gap: 6, flexWrap: "wrap" }}><button className="link-btn mono" onClick={() => jumpTo(it.testcase_id)}>{it.testcase_id}</button><span>{it.title}</span></div>
                        {it.assumptions.map((a, i) => <div key={i} className="assump-text">{a.text}</div>)}
                      </li>
                    ))}
                  </ol>
                )}
              </div>
            )}
            {d.type !== "ACTIVATE_TESTCASE" && d.diff_summary && <details className="details"><summary>詳細說明</summary><pre className="prewrap">{d.diff_summary}</pre></details>}
          </div>

          {/* 2. 決定 */}
          {pending && (
            <div className="panel stack" style={{ gap: 10 }}>
              <div className="step-title"><span className="step-n">1</span>整體決定</div>
              {d.type !== "ACTIVATE_TESTCASE" && (d.options?.length ?? 0) > 0 ? (
                <div className="option-list">
                  {d.options.map((o) => (
                    <button key={o.key} className={`option-btn ${optionActive(o.key) ? "on" : ""} ${o.key === "cancel" || o.key === "reject" ? "danger" : ""}`} onClick={() => pickOption(o.key)}>
                      <span className="option-key mono">{o.key}</span><span>{o.label}</span>
                      {d.memo?.suggested === o.key && <span className="tag ok" style={{ marginLeft: "auto" }}>QA session 建議</span>}
                    </button>
                  ))}
                </div>
              ) : (
              <div className="row" style={{ flexWrap: "wrap" }}>
                {(["approve", "reject", "override"] as const).map((k) => (
                  <button key={k} className={`btn ${dec === k ? (k === "reject" ? "danger" : "primary") : "ghost"}`} onClick={() => put({ decision: k })}>
                    {k === "approve" ? <CheckCircle className="ic sm" aria-hidden="true" /> : k === "reject" ? <XCircle className="ic sm" aria-hidden="true" /> : <Warning className="ic sm" aria-hidden="true" />}{DEC_LABEL[k]}
                  </button>
                ))}
              </div>
              )}
              <div className="faint" style={{ fontSize: 12 }}>
                {d.type === "ACTIVATE_TESTCASE" ? "選「核准」後可在下方逐條把不要的標退回；「退回」會整批退給 Designer 重做；「強制通過」需填理由。" : "選一個選項就是你的決定；QA session 有寫建議的話會標在選項上。"}
              </div>
              <div className="field">
                <label>整體理由{dec === "override" ? <span className="req">*</span> : null}<span className="faint">（逐條退回的理由會自動附在後面）</span></label>
                <textarea className="textarea" style={{ minHeight: 56 }} defaultValue={draft?.rationale ?? ""} onBlur={(e) => { if (e.target.value !== (draft?.rationale ?? "")) put({ rationale: e.target.value }); }} placeholder="例如：其餘與 Phase 2 既有 TC 語意等價，不重複啟用" />
              </div>
            </div>
          )}

          {/* 3. 逐條 */}
          {items.length > 0 && (
            <div className="stack" style={{ gap: 8 }}>
              <div className="step-title">{pending && <span className="step-n">2</span>}逐條檢視{pending ? "，決定每條要不要採用" : ""}<span className="faint" style={{ fontWeight: 400, marginLeft: 8 }}>{shown.length} / {items.length}</span>{pending && <span style={{ marginLeft: "auto", fontWeight: 500, fontSize: 12.5 }}><span style={{ color: "var(--ok)" }}>通過 {items.length - stats.rejected}</span> · <span style={{ color: "var(--danger)" }}>退回 {stats.rejected}</span></span>}</div>
              <div className="facets">
                {([["all", "全部", items.length], ["exploratory", "exploratory", stats.exploratory], ["high", "high", items.filter((i) => i.priority === "high" || i.priority === "critical").length], ["rejected", "已退回", stats.rejected]] as const).map(([k, label, n]) => (
                  <button key={k} className={`tag chip ${filter === k ? "on" : ""} ${k === "exploratory" ? "warn" : k === "high" || k === "rejected" ? "danger" : ""}`} onClick={() => setFilter(k)}>{label} {n}</button>
                ))}
                <input className="input" style={{ maxWidth: 240, marginLeft: 8, padding: "4px 8px" }} placeholder="搜尋 ID / 標題 / 需求" value={q} onChange={(e) => setQ(e.target.value)} />
                <div className="grow" />
                {pending && <><button className="btn ghost sm" onClick={() => setAll("approve")}>全部通過</button><button className="btn ghost sm" style={{ color: "var(--danger)" }} onClick={() => setAll("reject")}>全部退回</button></>}
                <button className="btn ghost sm" onClick={() => setOpenTc(new Set(shown.map((i) => i.testcase_id)))}>全部展開</button>
                <button className="btn ghost sm" onClick={() => setOpenTc(new Set())}>全部收合</button>
              </div>
              {shown.length === 0 && <div className="faint" style={{ padding: 16, textAlign: "center" }}>沒有符合的 TC</div>}
              {shown.map((it, idx) => {
                const isOpen = openTc.has(it.testcase_id);
                const rej = isRej(it);
                return (
                  <div key={it.testcase_id} id={`apr-tc-${it.testcase_id}`} className={`tc2 ${rej ? "rejected" : ""}`}>
                    <div className="tc2-head" {...clickable(() => toggle(it.testcase_id), `${isOpen ? "收合" : "展開"} ${it.testcase_id}`)} aria-expanded={isOpen}>
                      <span className="tc2-idx mono">{idx + 1}</span>
                      <div className="tc2-main">
                        <div className="tc2-title">{it.title}</div>
                        <div className="tc2-meta">
                          <span className="mono accent-text">{it.testcase_id}</span><span className="faint mono">v{it.version}</span>
                          <span className={`tag ${it.priority === "high" || it.priority === "critical" ? "danger" : it.priority === "medium" ? "warn" : ""}`}>{it.priority}</span>
                          {it.exploratory && <span className="tag warn">exploratory</span>}
                          {it.requirement_ids.slice(0, 3).map((r) => <span key={r} className="tag accent">{r}</span>)}{it.requirement_ids.length > 3 && <span className="faint">+{it.requirement_ids.length - 3}</span>}
                          {d.context?.recommendation?.found && (d.context.recommendation.adopt.includes(it.testcase_id) ? <span className="tag ok" title="shadow-test 文件建議採用">建議採用</span> : <span className="tag" style={{ opacity: 0.7 }} title="shadow-test 文件不採用">建議不採用</span>)}
                          {d.context?.overlap[it.testcase_id] && <span className="tag violet" title={`同需求的 Phase 2 既有 TC：${d.context.overlap[it.testcase_id].join(", ")}`}>同需求 {d.context.overlap[it.testcase_id].length} 條既有</span>}
                        </div>
                      </div>
                      {pending ? (
                        <div className="seg" onClick={(e) => e.stopPropagation()}>
                          <button className={`seg-btn ${!rej ? "on ok" : ""}`} onClick={() => setItem(it.testcase_id, "approve")}>通過</button>
                          <button className={`seg-btn ${rej ? "on danger" : ""}`} onClick={() => { setItem(it.testcase_id, "reject"); setOpenTc((s) => new Set(s).add(it.testcase_id)); }}>退回</button>
                        </div>
                      ) : it.decided && <span className={`tag ${it.decided === "reject" ? "danger" : "ok"}`}>{DEC_LABEL[it.decided] ?? it.decided}</span>}
                      <span className="faint">{isOpen ? <CaretDown className="ic sm" aria-hidden="true" /> : <CaretRight className="ic sm" aria-hidden="true" />}</span>
                    </div>
                    {isOpen && (
                      <div className="tc2-body">
                        {pending && rej && (
                          <div className="reason-box">
                            <label className="faint" style={{ fontSize: 12 }}>退回理由（會送回 QAOS 讓 Designer 重做）</label>
                            <textarea className="textarea" style={{ minHeight: 56 }} defaultValue={draft?.per_item?.[it.testcase_id]?.reason ?? ""} onBlur={(e) => setItem(it.testcase_id, "reject", e.target.value.trim())} placeholder="哪一步／哪個預期結果有問題、應該改成什麼" />
                          </div>
                        )}
                        {it.assumptions.length > 0 && (
                          <div className="assump-box inline">
                            <div className="row" style={{ gap: 6, color: "var(--warn)", fontWeight: 600, fontSize: 12.5 }}><Warning className="ic sm" aria-hidden="true" />這條建立在以下假設上，核准即確認</div>
                            {it.assumptions.map((a, i) => <div key={i} className="assump-text">{a.text}</div>)}
                          </div>
                        )}
                        <div className="tc2-grid">
                          <div className="tc2-sec"><div className="tc2-sec-t">前置條件</div>{it.preconditions.length ? <ul className="tc-list">{it.preconditions.map((p, i) => <li key={i}>{p}</li>)}</ul> : <div className="faint">無</div>}</div>
                          <div className="tc2-sec"><div className="tc2-sec-t">屬性</div><div className="card-tags"><span className="tag">{it.test_level}</span><span className="tag">risk {it.risk}</span>{it.requirement_ids.map((r) => <span key={r} className="tag accent">{r}</span>)}</div></div>
                        </div>
                        <div className="tc2-sec"><div className="tc2-sec-t">步驟</div><ol className="tc-steps">{it.steps.map((s) => <li key={s.n}>{s.action}</li>)}</ol></div>
                        <div className="tc2-sec expected"><div className="tc2-sec-t">預期結果</div><div>{it.expected_result}</div>{it.spec_reference?.location && <div className="spec-quote"><span className="faint">{it.spec_reference.location}</span>{it.spec_reference.quote ? <q>{it.spec_reference.quote}</q> : null}</div>}</div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {pending && (
            <div className="stack" style={{ gap: 8 }}>
              <div className="step-title"><span className="step-n">3</span>送出<span className="faint" style={{ fontWeight: 400, marginLeft: 8 }}>{draft?.option ? (d.options.find((o) => o.key === draft.option)?.label ?? draft.option) : dec ? `${DEC_LABEL[dec]}${stats.rejected ? `，退回 ${stats.rejected} 條` : ""}` : "尚未選整體決定"}</span></div>
              <CommandBox kind="approval" ticketId={d.approval_id} cmd={cmd} draft={draft} onSent={onChanged} beforeSend={beforeSend} />
            </div>
          )}
        </>
      )}
    </Drawer>
  );
}

/** QA session 的分析建議：讀 .warroom/recommendations/<APR>.md，markdown 由後端轉 HTML */
function MemoPanel({ memo, options, pending, onPick, aprId }: { memo: Memo | null; options: { key: string; label: string }[]; pending: boolean; onPick: (k: string) => void; aprId: string }) {
  const [html, setHtml] = useState<string>("");
  useEffect(() => {
    if (!memo) { setHtml(""); return; }
    api.post<{ html: string }>("/api/reports/preview", { body_md: memo.text }).then((x) => setHtml(x.html)).catch(() => setHtml(`<pre>${memo.text}</pre>`));
  }, [memo?.text]); // eslint-disable-line react-hooks/exhaustive-deps
  if (!memo) {
    return (
      <div className="memo-box empty">
        <div className="row" style={{ gap: 6, fontWeight: 600, fontSize: 13 }}>還沒有 QA session 的分析建議</div>
        <div className="faint" style={{ fontSize: 12, lineHeight: 1.6 }}>
          這類單子只有結果沒有分析。要讓 QA session 把它的判斷放進來，請對它說：「每張需要我決定的核准單，先把你的分析與建議寫到 <span className="mono">.warroom/recommendations/{aprId}.md</span>（第一行 <span className="mono">suggest: &lt;選項 key&gt;</span>），再停下來等我在指揮台決定。」寫好後這裡會自動顯示，建議的選項會標記出來。
        </div>
      </div>
    );
  }
  const sug = options.find((o) => o.key === memo.suggested);
  return (
    <div className="memo-box">
      <div className="row" style={{ gap: 8, flexWrap: "wrap" }}>
        <span style={{ fontWeight: 600, fontSize: 13 }}>QA session 的分析建議</span>
        <span className="faint mono" style={{ fontSize: 11.5 }}>{memo.path.split("/").pop()} · {fmtDate(memo.mtime)}</span>
        {sug && <span className="tag ok">建議：{sug.label}</span>}
        {sug && pending && <button className="btn sm primary" style={{ marginLeft: "auto" }} onClick={() => onPick(sug.key)}>採用建議</button>}
      </div>
      <div className="md-preview memo-md" dangerouslySetInnerHTML={{ __html: html || "<p class='faint'>載入中…</p>" }} />
    </div>
  );
}
