import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { PageHeader } from "@/components/PageHeader";
import { useToast } from "@/components/Toast";
import { useConfirm } from "@/components/Confirm";
import { refreshNav } from "@/lib/nav";
import { clickable } from "@/lib/a11y";
import { api, type Evidence, type RunCounts, type TestResult, type TestResultKind, type TestRun, type TestRunMeta } from "@/lib/api";
import { fmtBytes, fmtDate } from "@/lib/format";
import { Donut, Legend, ProgressBar, RESULT_COLOR, RESULT_LABEL } from "./Donut";
import { ArrowLeft, ArrowRight, Paperclip, Trash, FlagCheckered, FileText } from "@phosphor-icons/react";

const ST_LABEL: Record<string, string> = { planned: "未開始", running: "進行中", done: "已完成", aborted: "已中止" };
const RESULT_KEYS: TestResultKind[] = ["pass", "fail", "blocked", "skipped", "untested"];
const HOTKEY: Record<string, TestResultKind> = { p: "pass", f: "fail", b: "blocked", s: "skipped", u: "untested" };

export function TestRunPage() {
  const { id } = useParams();
  const runId = Number(id);
  const [run, setRun] = useState<TestRun | null>(null);
  const [meta, setMeta] = useState<TestRunMeta | null>(null);
  const [cur, setCur] = useState<number | null>(null);
  const [filter, setFilter] = useState<"all" | TestResultKind>("all");
  const [q, setQ] = useState("");
  const { toast } = useToast();
  const confirm = useConfirm();
  const nav = useNavigate();

  const load = useCallback(() => api.get<TestRun>(`/api/testruns/${runId}`).then((r) => { setRun(r); setCur((c) => c ?? r.results?.find((x) => x.result === "untested")?.id ?? r.results?.[0]?.id ?? null); }).catch((e) => toast(`載入失敗：${e.message}`, "danger")), [runId, toast]);
  useEffect(() => { load(); api.get<TestRunMeta>("/api/testruns/meta").then(setMeta).catch(() => {}); }, [load]);

  const results = run?.results ?? [];
  const ql = q.trim().toLowerCase();
  const shown = useMemo(() => results.filter((r) => (filter === "all" || r.result === filter) && (!ql || `${r.testcase_id} ${r.title}`.toLowerCase().includes(ql))), [results, filter, ql]);
  const current = results.find((r) => r.id === cur) ?? null;
  const locked = run?.status === "done" || run?.status === "aborted";

  const applyPatch = (res: TestResult, counts: RunCounts) => setRun((r) => r && ({ ...r, status: r.status === "planned" ? "running" : r.status, counts, results: (r.results ?? []).map((x) => x.id === res.id ? res : x) }));
  const setResult = async (rid: number, fields: Partial<Pick<TestResult, "result" | "actual_result" | "notes" | "duration_ms">>) => {
    try { const x = await api.patch<{ result: TestResult; counts: RunCounts }>(`/api/testruns/${runId}/results/${rid}`, fields); applyPatch(x.result, x.counts); refreshNav(); return true; }
    catch (e) { toast(`儲存失敗：${(e as Error).message}`, "danger"); return false; }
  };
  const goNext = () => { const i = shown.findIndex((r) => r.id === cur); const nx = shown.slice(i + 1).find((r) => r.result === "untested") ?? shown[i + 1]; if (nx) setCur(nx.id); };
  const mark = async (k: TestResultKind) => { if (!current || locked) return; if (await setResult(current.id, { result: k }) && k !== "untested" && k !== "fail") goNext(); };

  // 快捷鍵：P/F/B/S/U 標結果，J/K 上下，焦點在輸入框時不觸發
  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement; if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.tagName === "SELECT" || t.isContentEditable)) return;
      const k = e.key.toLowerCase();
      if (HOTKEY[k]) { e.preventDefault(); mark(HOTKEY[k]); }
      else if (k === "j" || k === "k") { e.preventDefault(); const i = shown.findIndex((r) => r.id === cur); const nx = shown[i + (k === "j" ? 1 : -1)]; if (nx) setCur(nx.id); }
    };
    window.addEventListener("keydown", h); return () => window.removeEventListener("keydown", h);
  }, [shown, cur, current, locked]); // eslint-disable-line react-hooks/exhaustive-deps

  const finish = async (status: "done" | "aborted") => {
    if (!run) return;
    const c = run.counts;
    const ok = await confirm({ title: status === "done" ? "結束這一輪？" : "中止這一輪？", message: `${c.done} / ${c.total} 已執行${c.untested ? `，還有 ${c.untested} 條未測` : ""}。結束後結果鎖定，並自動產一份測試報告。`, confirmText: status === "done" ? "結束並產報告" : "中止", danger: status === "aborted" });
    if (!ok) return;
    try { const r = await api.post<TestRun>(`/api/testruns/${runId}/finish`, { status }); setRun(r); refreshNav(); toast(`回合已${status === "done" ? "結束" : "中止"}，報告 #${r.report_id} 已產生`, "ok"); }
    catch (e) { toast(`失敗：${(e as Error).message}`, "danger"); }
  };

  if (!run) return <div className="page-body faint">載入中…</div>;
  return (
    <>
      <PageHeader eyebrow={`Test Run #${run.id}`} title={run.name} description={`${run.environment || "—"} · build ${run.build || "—"} · ${ST_LABEL[run.status]} · 建立 ${fmtDate(run.created_at)}${run.ended_at ? ` · 結束 ${fmtDate(run.ended_at)}` : ""}`}
        actions={<>
          <button className="btn ghost" onClick={() => nav("/testruns")}><ArrowLeft className="ic sm" aria-hidden="true" />回合列表</button>
          {run.report_id && <button className="btn" onClick={() => nav(`/reports/${run.report_id}`)}><FileText className="ic sm" aria-hidden="true" />測試報告</button>}
          {!locked && <button className="btn ghost" onClick={() => finish("aborted")}>中止</button>}
          {!locked && <button className="btn primary" onClick={() => finish("done")}><FlagCheckered className="ic sm" aria-hidden="true" />結束回合</button>}
        </>} />
      <div className="page-body">
        <div className="run-summary">
          <Donut counts={run.counts} size={132} stroke={16} />
          <Legend counts={run.counts} />
          <div className="run-summary-right">
            <div className="stack" style={{ gap: 6 }}>
              <div className="row" style={{ justifyContent: "space-between" }}><span className="faint" style={{ fontSize: 12 }}>進度</span><span className="mono">{run.counts.done} / {run.counts.total}（{run.counts.progress}%）</span></div>
              <ProgressBar counts={run.counts} />
              <div className="faint" style={{ fontSize: 12 }}>快捷鍵：P Pass · F Fail · B Blocked · S Skipped · U 未測 · J / K 上下一條</div>
              {locked && <div className="tag ok" style={{ alignSelf: "flex-start" }}>結果已鎖定</div>}
            </div>
          </div>
        </div>

        <div className="run-layout">
          <aside className="run-list">
            <div className="facets" style={{ marginBottom: 6 }}>
              {(["all", ...RESULT_KEYS] as const).map((k) => <button key={k} className={`tag chip ${filter === k ? "on" : ""}`} style={k !== "all" ? { borderColor: RESULT_COLOR[k] } : undefined} onClick={() => setFilter(k)}>{k === "all" ? "全部" : RESULT_LABEL[k]} {k === "all" ? run.counts.total : run.counts[k]}</button>)}
            </div>
            <input className="input" placeholder="搜尋 ID / 標題" value={q} onChange={(e) => setQ(e.target.value)} style={{ marginBottom: 6 }} />
            <div className="run-rows">
              {shown.map((r, i) => (
                <div key={r.id} className={`run-row ${r.id === cur ? "current" : ""}`} {...clickable(() => setCur(r.id), `${r.testcase_id} ${r.title}`)}>
                  <span className="run-row-dot" style={{ background: RESULT_COLOR[r.result] }} title={RESULT_LABEL[r.result]} />
                  <span className="mono faint" style={{ fontSize: 11, minWidth: 22 }}>{i + 1}</span>
                  <div className="run-row-main"><div className="mono accent-text" style={{ fontSize: 12 }}>{r.testcase_id}</div><div className="run-row-title">{r.title}</div></div>
                  {r.evidence.length > 0 && <Paperclip className="ic sm faint" aria-label={`${r.evidence.length} 份證據`} />}
                  {r.bug_run_id && <span className="tag danger" title={r.bug_run_id}>bug</span>}
                </div>
              ))}
              {shown.length === 0 && <div className="faint" style={{ padding: 12 }}>沒有符合的 TC</div>}
            </div>
          </aside>
          <section className="run-detail">
            {!current ? <div className="faint">左邊選一條 TC</div> : (
              <ResultPanel key={current.id} r={current} locked={locked} meta={meta} runId={runId} onMark={mark} onSave={(f) => setResult(current.id, f)} onNext={goNext} onEvidenceChanged={load} />
            )}
          </section>
        </div>
      </div>
    </>
  );
}

function ResultPanel({ r, locked, meta, runId, onMark, onSave, onNext, onEvidenceChanged }: { r: TestResult; locked: boolean; meta: TestRunMeta | null; runId: number; onMark: (k: TestResultKind) => void; onSave: (f: Partial<Pick<TestResult, "actual_result" | "notes">>) => Promise<boolean>; onNext: () => void; onEvidenceChanged: () => void }) {
  const [actual, setActual] = useState(r.actual_result);
  const [notes, setNotes] = useState(r.notes);
  const [evType, setEvType] = useState("screenshot");
  const [evDesc, setEvDesc] = useState("");
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const { toast } = useToast();
  const confirm = useConfirm();
  const dirty = actual !== r.actual_result || notes !== r.notes;
  const save = async () => { if (dirty) await onSave({ actual_result: actual, notes }); };

  const upload = async (files: FileList | null) => {
    if (!files || !files.length) return;
    setUploading(true);
    try {
      for (const f of Array.from(files)) {
        const fd = new FormData(); fd.append("file", f); fd.append("type", evType); fd.append("description", evDesc);
        const res = await fetch(`/api/testruns/${runId}/results/${r.id}/evidence`, { method: "POST", body: fd });
        if (!res.ok) { const j = await res.json().catch(() => ({})); throw new Error(j.detail || res.statusText); }
      }
      toast(`已加入 ${files.length} 份證據`, "ok"); setEvDesc(""); if (fileRef.current) fileRef.current.value = ""; onEvidenceChanged();
    } catch (e) { toast(`上傳失敗：${(e as Error).message}`, "danger"); }
    finally { setUploading(false); }
  };
  const removeEv = async (e: Evidence) => {
    if (!(await confirm({ title: "移除證據？", message: e.filename, confirmText: "移除", danger: true }))) return;
    await fetch(`/api/testruns/${runId}/results/${r.id}/evidence/${e.id}`, { method: "DELETE" }); onEvidenceChanged();
  };
  const needsFailInfo = r.result === "fail" && (!r.actual_result || r.evidence.length === 0);

  return (
    <div className="stack" style={{ gap: 14 }}>
      <div>
        <div className="row" style={{ gap: 8, flexWrap: "wrap" }}>
          <span className="mono accent-text" style={{ fontSize: 14 }}>{r.testcase_id}</span>
          {r.testcase_version && <span className="tag">v{r.testcase_version}</span>}
          <span className={`tag ${r.priority === "high" ? "danger" : r.priority === "medium" ? "warn" : ""}`}>{r.priority}</span>
          {r.requirement_ids.map((x) => <span key={x} className="tag accent">{x}</span>)}
          <span className="faint mono" style={{ marginLeft: "auto", fontSize: 12 }}>{r.group_key}</span>
        </div>
        <h2 style={{ fontSize: 17, margin: "8px 0 0", lineHeight: 1.4 }}>{r.title}</h2>
      </div>

      <div className="result-bar" role="group" aria-label="結果">
        {RESULT_KEYS.map((k) => (
          <button key={k} className={`result-btn ${r.result === k ? "on" : ""}`} style={{ ["--c" as string]: RESULT_COLOR[k] }} disabled={locked} onClick={() => onMark(k)} title={`快捷鍵 ${Object.entries(HOTKEY).find(([, v]) => v === k)?.[0].toUpperCase()}`}>{RESULT_LABEL[k]}</button>
        ))}
        {r.executed_at && <span className="faint" style={{ fontSize: 12, marginLeft: "auto" }}>{fmtDate(r.executed_at)} · {r.executed_by}</span>}
      </div>
      {needsFailInfo && !locked && <div className="notice" style={{ borderColor: "rgba(255,107,122,0.5)" }}>Fail 需要填「實際結果」並附至少一份證據，之後才能送 QAOS 開 bug。</div>}

      <div className="tc2-grid">
        <div className="tc2-sec"><div className="tc2-sec-t">前置條件</div>{r.preconditions.length ? <ul className="tc-list">{r.preconditions.map((p, i) => <li key={i}>{p}</li>)}</ul> : <div className="faint">無</div>}</div>
        <div className="tc2-sec expected"><div className="tc2-sec-t">預期結果</div><div>{r.expected_result}</div></div>
      </div>
      <div className="tc2-sec"><div className="tc2-sec-t">步驟</div><ol className="tc-steps">{r.steps.map((s) => <li key={s.n}>{s.action}</li>)}</ol></div>

      <div className="form-grid">
        <div className="field span2"><label>實際結果{r.result === "fail" ? <span className="req">*</span> : null}</label><textarea className="textarea" style={{ minHeight: 70 }} value={actual} onChange={(e) => setActual(e.target.value)} onBlur={save} disabled={locked} placeholder="看到什麼、跟預期差在哪" /></div>
        <div className="field span2"><label>備註</label><input className="input" value={notes} onChange={(e) => setNotes(e.target.value)} onBlur={save} disabled={locked} /></div>
      </div>

      <div className="tc2-sec">
        <div className="tc2-sec-t">證據 · {r.evidence.length}</div>
        {r.evidence.length > 0 && (
          <div className="stack" style={{ gap: 4 }}>
            {r.evidence.map((e) => (
              <div key={e.id} className="ev-row">
                <span className="tag">{e.type}</span>
                <a className="link-btn" href={`/api/testruns/${runId}/evidence/${e.id}`} target="_blank" rel="noreferrer">{e.filename}</a>
                <span className="faint" style={{ fontSize: 12 }}>{fmtBytes(e.size)}{e.description ? ` · ${e.description}` : ""}</span>
                {!locked && <button className="btn ghost sm" style={{ marginLeft: "auto", color: "var(--danger)" }} onClick={() => removeEv(e)} aria-label="移除證據"><Trash className="ic sm" aria-hidden="true" /></button>}
              </div>
            ))}
          </div>
        )}
        {!locked && (
          <div className="row" style={{ gap: 6, flexWrap: "wrap", marginTop: 6 }}>
            <select className="select" value={evType} onChange={(e) => setEvType(e.target.value)} style={{ width: 150 }}>{(meta?.evidence_types ?? ["screenshot"]).map((t) => <option key={t} value={t}>{t}</option>)}</select>
            <input className="input" style={{ maxWidth: 260 }} placeholder="說明（選填）" value={evDesc} onChange={(e) => setEvDesc(e.target.value)} />
            <input ref={fileRef} type="file" multiple onChange={(e) => upload(e.target.files)} disabled={uploading} />
          </div>
        )}
      </div>

      <div className="row" style={{ justifyContent: "flex-end" }}>
        <button className="btn ghost" onClick={onNext}>下一條<ArrowRight className="ic sm" aria-hidden="true" /></button>
      </div>
    </div>
  );
}
