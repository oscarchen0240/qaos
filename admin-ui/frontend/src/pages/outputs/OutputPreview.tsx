import { useEffect, useMemo, useState } from "react";
import { Drawer } from "@/components/Drawer";
import { useToast } from "@/components/Toast";
import { useConfirm } from "@/components/Confirm";
import { api, type CaseFilter, type Folder, type OutputContent, type OutputFile, type OutputGroup, type ReviewStatus, type TcCase } from "@/lib/api";
import { FolderPicker } from "./FolderPicker";
import { fmtBytes, fmtDate } from "@/lib/format";
import { clickable } from "@/lib/a11y";
import { CaretDown, CaretRight } from "@phosphor-icons/react";
import { REVIEW_CLASS, REVIEW_LABEL, REVIEW_STATUSES as STATUSES } from "@/lib/review";

interface Props {
  group: OutputGroup | null;
  initialFilter?: CaseFilter | null;
  onClose: () => void;
  onSaved: (g: OutputGroup) => void;
  folders?: Folder[];
  onFoldersChanged?: () => void;
  /** 從側邊欄樹點進來時，展開並捲到這條 TC */
  focusTc?: string | null;
}

export function OutputPreview({ group, initialFilter, onClose, onSaved, folders = [], onFoldersChanged, focusTc = null }: Props) {
  const [picked, setPicked] = useState<Set<string>>(new Set());
  const [pickFor, setPickFor] = useState<{ group_key: string; testcase_id: string }[] | null>(null);
  const [filePath, setFilePath] = useState<string | null>(null);
  const [content, setContent] = useState<OutputContent | null>(null);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [q, setQ] = useState("");
  const { toast } = useToast();
  const confirm = useConfirm();

  // 開啟群組時：預設顯示 JSON（有逐條檢視），否則第一個檔
  useEffect(() => {
    if (!group) { setFilePath(null); setContent(null); return; }
    setNote(group.note); setQ(""); setPicked(new Set());
    const first = group.files.find((f) => f.kind === "json") ?? group.files[0];
    setFilePath(first?.path ?? null);
  }, [group?.key]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!filePath) { setContent(null); return; }
    setContent(null);
    api.get<OutputContent>(`/api/outputs/content?path=${encodeURIComponent(filePath)}`).then(setContent)
      .catch((e) => toast(`讀取失敗：${e.message}`, "danger"));
  }, [filePath, toast]);

  const saveNote = async () => {
    if (!group) return;
    setBusy(true);
    try {
      const g = await api.patch<OutputGroup>("/api/outputs/review", { key: group.key, note });
      onSaved(g); toast("備註已儲存", "ok");
    } catch (e) { toast(`儲存失敗：${(e as Error).message}`, "danger"); }
    finally { setBusy(false); }
  };

  const setAll = async (status: ReviewStatus) => {
    if (!group) return;
    const ok = await confirm({
      title: `全部設為「${REVIEW_LABEL[status]}」？`,
      message: `${group.label} 共 ${group.tc_summary.total} 條 TC 都會改成「${REVIEW_LABEL[status]}」，會覆蓋目前逐條標記。`,
      confirmText: `全部設為 ${REVIEW_LABEL[status]}`,
      danger: status === "returned",
    });
    if (!ok) return;
    try {
      const g = await api.patch<OutputGroup>("/api/outputs/review", { key: group.key, review_status: status });
      onSaved(g);
      setContent((c) => c && c.kind === "json" ? { ...c, cases: c.cases.map((x) => ({ ...x, review_status: status })) } : c);
      toast(`已全部設為 ${REVIEW_LABEL[status]}`, "ok");
    } catch (e) { toast(`更新失敗：${(e as Error).message}`, "danger"); }
  };

  const setTc = async (ids: string[], status: ReviewStatus, reason?: string) => {
    if (!group) return;
    setContent((c) => c && c.kind === "json" ? { ...c, cases: c.cases.map((x) => ids.includes(x.testcase_id) ? { ...x, review_status: status, ...(reason !== undefined ? { review_reason: reason } : {}) } : x) } : c);
    try {
      const g = await api.patch<OutputGroup>("/api/outputs/tc-review", { key: group.key, testcase_ids: ids, review_status: status, ...(reason !== undefined ? { reason } : {}) });
      onSaved(g);
    } catch (e) { toast(`更新失敗：${(e as Error).message}`, "danger"); }
  };

  const copy = async (label: string, ids: string[]) => {
    try { await navigator.clipboard.writeText(ids.join(", ")); toast(`已複製 ${label} ${ids.length} 條 TC ID`, "ok"); }
    catch { toast("複製失敗（瀏覽器不允許剪貼簿）", "danger"); }
  };

  const noteDirty = group && note !== group.note;
  const file: OutputFile | undefined = group?.files.find((f) => f.path === filePath);
  const s = group?.tc_summary;

  return (
    <Drawer
      open={!!group}
      onClose={onClose}
      wide
      title={group?.label ?? ""}
      subtitle={group ? `${group.files.length} 個檔案 · 最後產生 ${fmtDate(group.modified_at)} · 唯讀` : ""}
      footer={
        <>
          <div className="row" style={{ gap: 8 }}>
            {group && s && s.total > 0 && (
              <>
                <span className="faint" style={{ fontSize: 12 }}>模組狀態</span>
                <div className="seg lg" title="目前狀態由各 TC 彙總；點其他選項會把全部 TC 一次設為該狀態">
                  {STATUSES.map((k) => (
                    <button key={k} className={`seg-btn ${group.review_status === k ? `on ${REVIEW_CLASS[k]}` : ""}`} onClick={() => { if (k !== group.review_status) setAll(k); }}>
                      {REVIEW_LABEL[k]}
                    </button>
                  ))}
                </div>
              </>
            )}
            {file && <a className="btn ghost sm" href={`/api/outputs/raw?path=${encodeURIComponent(file.path)}`} target="_blank" rel="noreferrer">開新視窗</a>}
          </div>
          <div className="row">
            <button className="btn ghost" onClick={onClose}>關閉</button>
            <button className="btn primary" disabled={!noteDirty || busy} onClick={saveNote}>儲存備註</button>
          </div>
        </>
      }
    >
      {group && s && (
        <div className="review-summary">
          <div className="row" style={{ gap: 10, flexWrap: "wrap" }}>
            <span className={`tag ${REVIEW_CLASS[group.review_status]}`} style={{ fontSize: 12 }}>模組狀態 · {REVIEW_LABEL[group.review_status]}</span>
            <span className="faint mono" style={{ fontSize: 12 }}>
              {s.total > 0 ? `已審 ${s.reviewed} · 待審 ${s.pending.length} · 退回 ${s.returned.length} / 共 ${s.total}` : "此產出沒有可逐條審閱的 TC（無 JSON）"}
            </span>
          </div>
          {s.pending.length > 0 && (
            <IdList label="待審" cls="warn" ids={s.pending} onCopy={() => copy("待審", s.pending)} />
          )}
          {s.returned.length > 0 && (
            <>
              <IdList label="退回" cls="danger" ids={s.returned} onCopy={() => copy("退回", s.returned)} />
              <div className="stack" style={{ gap: 2, fontSize: 12 }}>
                {s.returned.map((t) => <div key={t}><span className="mono">{t}</span>：{s.reasons?.[t] ? <span className="muted">{s.reasons[t]}</span> : <span className="tag warn">未填理由</span>}</div>)}
              </div>
            </>
          )}
        </div>
      )}
      {group?.meta.drift?.stale && (
        <div className="next-action" data-kind="clarify" role="status" style={{ marginBottom: 0 }}>
          <span className="na-label">過期</span>
          <span className="na-text">final 檔已過期</span>
          <span className="faint" style={{ fontSize: 12, fontWeight: 400 }}>
            registry 有變動但尚未重新匯出：新增 {group.meta.drift.added.length}、新版 {group.meta.drift.newer.length}、退役 {group.meta.drift.retired.length}。請讓 QAOS 重新匯出 {group.label}。
          </span>
        </div>
      )}
      <div className="field">
        <label>審閱備註（整個模組共用）</label>
        <textarea className="textarea" style={{ minHeight: 64 }} value={note} onChange={(e) => setNote(e.target.value)} placeholder="給這份產出的備註（存在管理系統，不改原檔）" />
      </div>
      {group && (
        <div className="file-tabs">
          {group.files.map((f) => (
            <button key={f.path} className={`file-tab ${f.path === filePath ? "active" : ""}`} onClick={() => setFilePath(f.path)}>
              <span className={`tag ${f.kind === "json" ? "cyan" : "violet"}`}>{f.kind.toUpperCase()}</span>
              <span className="mono">{f.name}</span>
              <span className="faint mono">{fmtBytes(f.size)}</span>
              {f.unread && <span className="tag accent">NEW</span>}
            </button>
          ))}
        </div>
      )}
      {!content ? <div className="faint">載入中…</div>
        : content.kind === "html" ? (
          <iframe title="preview" src={content.raw_url} className="preview-frame" />
        ) : content.kind === "json" ? (
          <>
            {picked.size > 0 && (
              <div className="row" style={{ justifyContent: "space-between", padding: "6px 10px", background: "var(--accent-soft)", borderRadius: 5 }}>
                <span>已勾選 {picked.size} 條 TC</span>
                <div className="row">
                  <button className="btn ghost sm" onClick={() => setPicked(new Set())}>清除</button>
                  <button className="btn sm primary" onClick={() => setPickFor(Array.from(picked).map((t) => ({ group_key: group!.key, testcase_id: t })))}>加入資料夾</button>
                </div>
              </div>
            )}
            <CaseList cases={content.cases} q={q} setQ={setQ} onSet={setTc} initialFilter={initialFilter ?? null} focusTc={focusTc} picked={picked} onPick={(id, on) => setPicked((s) => { const n = new Set(s); on ? n.add(id) : n.delete(id); return n; })} onPickAll={(ids) => setPicked(new Set(ids))} />
          </>
        ) : (
          <pre className="mono" style={{ whiteSpace: "pre-wrap" }}>{content.text}</pre>
        )}
      <FolderPicker folders={folders} items={pickFor} onClose={() => setPickFor(null)} onDone={() => { setPickFor(null); setPicked(new Set()); onFoldersChanged?.(); if (filePath) { const fp = filePath; setFilePath(null); setTimeout(() => setFilePath(fp), 0); } }} />
    </Drawer>
  );
}

function ReasonEditor({ value, onSave }: { value: string; onSave: (r: string) => void }) {
  const [v, setV] = useState(value);
  useEffect(() => setV(value), [value]);
  return (
    <div className="reason-box">
      <label className="faint" style={{ fontSize: 12 }}>退回理由（會寫進報告；未來送回 QAOS 重做時作為 rationale）</label>
      <div className="row" style={{ alignItems: "flex-start" }}>
        <textarea className="textarea" style={{ minHeight: 56, flex: 1 }} value={v} onChange={(e) => setV(e.target.value)} placeholder="例如：步驟 3 的預期結果與 spec §4.2 不符，應為…" />
        <button className="btn sm" disabled={v === value} onClick={() => onSave(v.trim())}>儲存理由</button>
      </div>
    </div>
  );
}

function IdList({ label, cls, ids, onCopy }: { label: string; cls: string; ids: string[]; onCopy: () => void }) {
  const [expanded, setExpanded] = useState(false);
  const shown = expanded ? ids : ids.slice(0, 12);
  return (
    <div className="id-list">
      <span className={`tag ${cls}`}>{label} {ids.length}</span>
      <span className="mono" style={{ fontSize: 12, color: "var(--text-muted)" }}>
        {shown.join("、")}{!expanded && ids.length > shown.length ? ` … 另 ${ids.length - shown.length} 條` : ""}
      </span>
      {ids.length > 12 && <button className="btn ghost sm" onClick={() => setExpanded(!expanded)}>{expanded ? "收合" : "全部"}</button>}
      <button className="btn ghost sm" onClick={onCopy}>複製 ID</button>
    </div>
  );
}

const PRIO_ORDER = ["critical", "high", "medium", "low"];
const RISK_ORDER = ["high", "medium", "low"];

function CaseList({ cases, q, setQ, onSet, initialFilter, focusTc, picked, onPick, onPickAll }: { cases: TcCase[]; q: string; setQ: (s: string) => void; onSet: (ids: string[], s: ReviewStatus, reason?: string) => void; initialFilter: CaseFilter | null; focusTc: string | null; picked: Set<string>; onPick: (id: string, on: boolean) => void; onPickAll: (ids: string[]) => void }) {
  const [open, setOpen] = useState<Set<string>>(new Set());
  useEffect(() => {
    if (!focusTc || !cases.some((c) => c.testcase_id === focusTc)) return;
    setFilter("all"); setPrio(""); setRisk(""); setKind(""); setQ("");
    setOpen((s) => new Set(s).add(focusTc));
    const t = setTimeout(() => document.getElementById(`tc-${focusTc}`)?.scrollIntoView({ block: "center" }), 60);
    return () => clearTimeout(t);
  }, [focusTc, cases]); // eslint-disable-line react-hooks/exhaustive-deps
  const [filter, setFilter] = useState<"all" | ReviewStatus>(initialFilter?.review ?? "all");
  const [prio, setPrio] = useState<string>(initialFilter?.priority ?? "");
  const [risk, setRisk] = useState<string>(initialFilter?.risk ?? "");
  const [kind, setKind] = useState<"" | "exploratory" | "revised">(initialFilter?.kind ?? "");
  useEffect(() => { setFilter(initialFilter?.review ?? "all"); setPrio(initialFilter?.priority ?? ""); setRisk(initialFilter?.risk ?? ""); setKind(initialFilter?.kind ?? ""); }, [initialFilter]);
  const ql = q.trim().toLowerCase();
  const prios = useMemo(() => PRIO_ORDER.filter((p) => cases.some((c) => c.priority === p)), [cases]);
  const risks = useMemo(() => RISK_ORDER.filter((r) => cases.some((c) => c.risk === r)), [cases]);
  const shown = useMemo(() => cases.filter((c) => (filter === "all" || c.review_status === filter)
    && (!prio || c.priority === prio) && (!risk || c.risk === risk)
    && (!kind || (kind === "exploratory" ? c.assumptions?.length > 0 : c.version > 1))
    && (!ql || [c.testcase_id, c.title, c.expected_result, ...c.requirement_ids].join(" ").toLowerCase().includes(ql))), [cases, filter, prio, risk, kind, ql]);
  const anyFacet = !!(prio || risk || kind);
  const counts = useMemo(() => ({
    all: cases.length,
    pending: cases.filter((c) => c.review_status === "pending").length,
    reviewed: cases.filter((c) => c.review_status === "reviewed").length,
    returned: cases.filter((c) => c.review_status === "returned").length,
  }), [cases]);
  const toggle = (id: string) => setOpen((s) => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n; });
  return (
    <div className="stack">
      <div className="row">
        <input type="checkbox" title="全選目前篩選結果" checked={shown.length > 0 && shown.every((c) => picked.has(c.testcase_id))} onChange={(e) => onPickAll(e.target.checked ? shown.map((c) => c.testcase_id) : [])} />
        <input className="input" placeholder="搜尋案例 ID / 標題 / 需求…" value={q} onChange={(e) => setQ(e.target.value)} />
        <span className="faint mono" style={{ whiteSpace: "nowrap" }}>{shown.length}/{cases.length}</span>
      </div>
      <div className="facets">
        <span className="faint" style={{ fontSize: 12 }}>優先</span>
        {prios.map((p) => <button key={p} className={`tag chip ${prio === p ? "on" : ""} ${p === "critical" || p === "high" ? "danger" : p === "medium" ? "warn" : ""}`} onClick={() => setPrio(prio === p ? "" : p)}>{p} {cases.filter((c) => c.priority === p).length}</button>)}
        <span className="faint" style={{ fontSize: 12, marginLeft: 8 }}>風險</span>
        {risks.map((r) => <button key={r} className={`tag chip ${risk === r ? "on" : ""}`} onClick={() => setRisk(risk === r ? "" : r)}>{r} {cases.filter((c) => c.risk === r).length}</button>)}
        <span className="faint" style={{ fontSize: 12, marginLeft: 8 }}>類型</span>
        <button className={`tag chip warn ${kind === "exploratory" ? "on" : ""}`} onClick={() => setKind(kind === "exploratory" ? "" : "exploratory")}>exploratory {cases.filter((c) => c.assumptions?.length > 0).length}</button>
        <button className={`tag chip ${kind === "revised" ? "on" : ""}`} onClick={() => setKind(kind === "revised" ? "" : "revised")}>revised {cases.filter((c) => c.version > 1).length}</button>
        {anyFacet && <button className="btn ghost sm" onClick={() => { setPrio(""); setRisk(""); setKind(""); }}>清除</button>}
      </div>
      <div className="row" style={{ gap: 4 }}>
        {(["all", ...STATUSES] as const).map((k) => (
          <button key={k} className={`btn sm ${filter === k ? "" : "ghost"}`} onClick={() => setFilter(k)}>
            {k === "all" ? "全部" : REVIEW_LABEL[k]} <span className="tab-count">{counts[k]}</span>
          </button>
        ))}
        {filter !== "all" && shown.length > 0 && (
          <>
            <div className="grow" />
            <span className="faint" style={{ fontSize: 12 }}>篩選結果設為</span>
            {STATUSES.filter((k) => k !== filter).map((k) => (
              <button key={k} className="btn ghost sm" onClick={() => onSet(shown.map((c) => c.testcase_id), k)}>{REVIEW_LABEL[k]}</button>
            ))}
          </>
        )}
      </div>
      {shown.length === 0 && <div className="faint" style={{ padding: 20, textAlign: "center" }}>沒有符合的案例</div>}
      {shown.map((c) => {
        const isOpen = open.has(c.testcase_id);
        const exploratory = c.assumptions?.length > 0;
        return (
          <div key={c.testcase_id} id={`tc-${c.testcase_id}`} className={`tc rs-${c.review_status} ${focusTc === c.testcase_id ? "focus" : ""}`}>
            <div className="tc-head" {...clickable(() => toggle(c.testcase_id), `${isOpen ? "收合" : "展開"} ${c.testcase_id}`)} aria-expanded={isOpen}>
              <input type="checkbox" checked={picked.has(c.testcase_id)} onClick={(e) => e.stopPropagation()} onChange={(e) => onPick(c.testcase_id, e.target.checked)} aria-label={`勾選 ${c.testcase_id}`} />
              <span className="mono accent-text">{c.testcase_id}</span>
              {c.folders?.map((f) => <span key={f.id} className="tag violet" title="所在資料夾">{f.name}</span>)}
              <span className="tag">v{c.version}</span>
              <span className="tc-title">{c.title}</span>
              <span className={`tag ${c.priority === "high" ? "danger" : c.priority === "medium" ? "warn" : ""}`}>{c.priority}</span>
              <span className={`tag ${exploratory ? "warn" : "ok"}`}>{exploratory ? "exploratory" : "grounded"}</span>
              <div className="seg" onClick={(e) => e.stopPropagation()}>
                {STATUSES.map((k) => (
                  <button key={k} className={`seg-btn ${c.review_status === k ? `on ${REVIEW_CLASS[k]}` : ""}`} title={REVIEW_LABEL[k]} onClick={() => { onSet([c.testcase_id], k); if (k === "returned") setOpen((s) => new Set(s).add(c.testcase_id)); }}>
                    {REVIEW_LABEL[k].slice(0, 1)}
                  </button>
                ))}
              </div>
              <span className="faint">{isOpen ? <CaretDown className="ic sm" aria-hidden="true" /> : <CaretRight className="ic sm" aria-hidden="true" />}</span>
            </div>
            {isOpen && (
              <div className="tc-body">
                {c.review_status === "returned" && <ReasonEditor value={c.review_reason} onSave={(r) => onSet([c.testcase_id], "returned", r)} />}
                <div className="card-tags">
                  {c.requirement_ids.map((r) => <span key={r} className="tag accent">{r}</span>)}
                  <span className="tag">{c.test_level}</span>
                  {c.test_types.map((t) => <span key={t} className="tag cyan">{t}</span>)}
                  {c.design_techniques.map((t) => <span key={t} className="tag violet">{t}</span>)}
                  <span className="tag">risk {c.risk}</span>
                </div>
                {c.preconditions.length > 0 && <div><div className="section-title">前置條件</div><ul className="tc-list">{c.preconditions.map((p, i) => <li key={i}>{p}</li>)}</ul></div>}
                <div><div className="section-title">步驟</div><ol className="tc-list">{c.steps.map((s) => <li key={s.n}>{s.action}</li>)}</ol></div>
                <div><div className="section-title">預期結果</div><div>{c.expected_result}</div>
                  {c.spec_reference?.location && <div className="faint" style={{ fontSize: 12, marginTop: 4 }}>{c.spec_reference.location}{c.spec_reference.quote ? ` — 「${c.spec_reference.quote}」` : ""}</div>}
                </div>
                {exploratory && <div><div className="section-title">假設（需人工確認）</div><ul className="tc-list">{c.assumptions.map((a, i) => <li key={i} style={{ color: "var(--warn)" }}>{a.text}</li>)}</ul></div>}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
