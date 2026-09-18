import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { PageHeader } from "@/components/PageHeader";
import { useToast } from "@/components/Toast";
import { useConfirm } from "@/components/Confirm";
import { refreshNav } from "@/lib/nav";
import { clickable } from "@/lib/a11y";
import { api, type BugFileResult, type BugPlan, type Evidence, type RunCounts, type TestResult, type TestResultKind, type TestRun, type TestRunMeta } from "@/lib/api";
import { fmtBytes, fmtDate } from "@/lib/format";
import { Donut, Legend, ProgressBar, RESULT_COLOR, RESULT_LABEL } from "./Donut";
import { ArrowLeft, ArrowRight, Paperclip, Trash, FlagCheckered, FileText, Bug, PaperPlaneRight } from "@phosphor-icons/react";

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
              {locked && <div className="tag ok" style={{ alignSelf: "flex-start" }} title="結束後結果不能改，但 Fail 仍可送 QAOS 開 bug">結果已鎖定</div>}
              <RunSettings run={run} onSaved={(r) => setRun((cur) => cur ? { ...cur, ...r, results: cur.results } : r)} />
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
              <ResultPanel key={current.id} r={current} locked={locked} meta={meta} runId={runId} envOk={!!(run.environment || "").trim()} onMark={mark} onSave={(f) => setResult(current.id, f)} onNext={goNext} onEvidenceChanged={load} />
            )}
          </section>
        </div>
      </div>
    </>
  );
}

function ResultPanel({ r, locked, meta, runId, envOk, onMark, onSave, onNext, onEvidenceChanged }: { r: TestResult; locked: boolean; meta: TestRunMeta | null; runId: number; envOk: boolean; onMark: (k: TestResultKind) => void; onSave: (f: Partial<Pick<TestResult, "actual_result" | "notes">>) => Promise<boolean>; onNext: () => void; onEvidenceChanged: () => void }) {
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

      {r.result === "fail" && <FileBugBox r={r} runId={runId} envOk={envOk} onChanged={onEvidenceChanged} />}
      {r.result !== "fail" && r.qaos_execution_id && <div className="notice">已匯入 QAOS executions：<span className="mono">{r.qaos_execution_id}</span></div>}

      <div className="row" style={{ justifyContent: "flex-end" }}>
        <button className="btn ghost" onClick={onNext}>下一條<ArrowRight className="ic sm" aria-hidden="true" /></button>
      </div>
    </div>
  );
}

/** Fail → 送 QAOS 開 bug：預覽三條 bin/qaos 指令與寫入路徑 → 確認 → 執行 → 顯示 EVD／EXE／RUN 編號與交接提示 */
function FileBugBox({ r, runId, envOk, onChanged }: { r: TestResult; runId: number; envOk: boolean; onChanged: () => void }) {
  const [plan, setPlan] = useState<BugPlan | null>(null);
  const [busy, setBusy] = useState(false);
  const [last, setLast] = useState<BugFileResult | null>(null);
  const { toast } = useToast();
  const confirm = useConfirm();
  const ready = !!(r.actual_result || "").trim() && r.evidence.length > 0 && !r.bug_run_id && !!envOk;
  useEffect(() => { setPlan(null); setLast(null); }, [r.id, r.actual_result, r.evidence.length, r.bug_run_id]);

  const send = async () => {
    setBusy(true);
    try {
      const p = await api.get<BugPlan>(`/api/testruns/${runId}/results/${r.id}/bug-plan`);
      setPlan(p);
      if (p.warnings.length) { toast(p.warnings[0], "danger"); return; }
      const ok = await confirm({
        title: `送 QAOS 開 bug：${r.testcase_id}`,
        message: (
          <div className="stack" style={{ gap: 8 }}>
            <div className="faint" style={{ fontSize: 12 }}>平台會依序執行 {p.steps.length} 條 QAOS 指令（執行者 {p.operator}）：</div>
            <ol className="tc-steps" style={{ fontSize: 12 }}>{p.steps.map((s, i) => <li key={i}><div>{s.label}</div><pre className="cmd-pre" style={{ margin: "4px 0 0", fontSize: 11 }}>{s.command}</pre></li>)}</ol>
            <div className="faint" style={{ fontSize: 12 }}>QAOS 會寫入：</div>
            <ul className="tc-list" style={{ fontSize: 12 }}>{p.writes.map((w, i) => <li key={i} className="mono">{w}</li>)}</ul>
            <div className="faint" style={{ fontSize: 12 }}>spec {p.meta.spec_id}@{p.meta.spec_version} · TC v{p.meta.version}。之後 Bug Analyst／Validator 由 QA session 跑，OPEN_BUG 核准單會出現在「單據 › 核准」。</div>
          </div>
        ),
        confirmText: "執行並開 bug",
        danger: true,
      });
      if (!ok) return;
      const res = await api.post<BugFileResult>(`/api/testruns/${runId}/results/${r.id}/file-bug`);
      setLast(res);
      toast(res.bug_run_id ? `已開 ${res.bug_run_id}` : "已送出", "ok");
      onChanged();
    } catch (e) { toast(`失敗：${(e as Error).message}`, "danger"); }
    finally { setBusy(false); }
  };

  if (r.bug_run_id) {
    return (
      <div className="notice" style={{ borderColor: "rgba(60,200,140,0.4)" }}>
        <div className="row" style={{ gap: 8, flexWrap: "wrap" }}>
          <Bug className="ic sm" aria-hidden="true" />
          <span>已送 QAOS 開 bug：<span className="mono">{r.bug_run_id}</span></span>
          {r.qaos_execution_id && <span className="faint mono" style={{ fontSize: 12 }}>{r.qaos_execution_id}</span>}
          {r.qaos_evidence_ids.length > 0 && <span className="faint mono" style={{ fontSize: 12 }}>{r.qaos_evidence_ids.join(" ")}</span>}
        </div>
        {last?.hint && <div style={{ fontSize: 12.5, marginTop: 6 }}>{last.hint}</div>}
      </div>
    );
  }
  return (
    <div className="cmd-box">
      <div className="row" style={{ justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
        <div>
          <div className="section-title" style={{ margin: 0 }}>送 QAOS 開 bug</div>
          <div className="faint" style={{ fontSize: 12 }}>{ready ? "會登記證據、匯入執行紀錄、開一條 spec-to-bug run；按下去會先給你看指令與寫入路徑。" : !envOk ? "回合還沒填「環境」：到上方「回合設定」補上（QAOS 的 execution import 必填）。" : "需要：實際結果已填、至少一份證據。"}</div>
        </div>
        <button className="btn primary" disabled={!ready || busy} onClick={send}><PaperPlaneRight className="ic sm" aria-hidden="true" />{busy ? "執行中…" : "送 QAOS 開 bug"}</button>
      </div>
      {plan && plan.warnings.length > 0 && <div className="stack" style={{ gap: 2 }}>{plan.warnings.map((w, i) => <div key={i} style={{ color: "var(--warn)", fontSize: 12 }}>{w}</div>)}</div>}
      {last && !last.ok && <pre className="cmd-pre" style={{ color: "var(--danger)" }}>{last.log.map((l) => `[${l.what}] exit ${l.exit_code}\n${l.stderr || l.stdout}`).join("\n")}</pre>}
    </div>
  );
}

/** 回合設定就地編輯：環境（送 QAOS 必填）、build、全部匯入開關。結束後也能改（只影響之後的匯入／開 bug）。 */
function RunSettings({ run, onSaved }: { run: TestRun; onSaved: (r: TestRun) => void }) {
  const [open, setOpen] = useState(!(run.environment || "").trim());
  const [env, setEnv] = useState(run.environment);
  const [build, setBuild] = useState(run.build);
  const [importAll, setImportAll] = useState(run.import_all);
  const [busy, setBusy] = useState(false);
  const { toast } = useToast();
  useEffect(() => { setEnv(run.environment); setBuild(run.build); setImportAll(run.import_all); }, [run.id, run.environment, run.build, run.import_all]);
  const dirty = env !== run.environment || build !== run.build || importAll !== run.import_all;
  const save = async () => {
    setBusy(true);
    try { const r = await api.patch<TestRun>(`/api/testruns/${run.id}`, { environment: env, build, import_all: importAll }); onSaved(r); toast("回合設定已儲存", "ok"); if ((r.environment || "").trim()) setOpen(false); }
    catch (e) { toast(`儲存失敗：${(e as Error).message}`, "danger"); }
    finally { setBusy(false); }
  };
  if (!open) {
    return (
      <div className="row" style={{ gap: 8, fontSize: 12 }}>
        <span className="faint">回合設定</span>
        <span className="mono">{run.environment || "—"}</span><span className="faint">·</span><span className="mono">{run.build || "—"}</span>
        {run.import_all && <span className="tag">Pass 也匯入 QAOS</span>}
        <button className="link-btn" style={{ fontSize: 12 }} onClick={() => setOpen(true)}>編輯</button>
      </div>
    );
  }
  return (
    <div className="run-settings">
      <div className="row" style={{ gap: 8, flexWrap: "wrap", alignItems: "flex-end" }}>
        <div className="field" style={{ minWidth: 180 }}><label>環境<span className="req">*</span><span className="faint">（送 QAOS 必填）</span></label><input className="input" value={env} onChange={(e) => setEnv(e.target.value)} placeholder="stage / uat / prod" autoFocus={!run.environment} /></div>
        <div className="field" style={{ minWidth: 160 }}><label>Build</label><input className="input" value={build} onChange={(e) => setBuild(e.target.value)} placeholder="版本或 commit" /></div>
        <label className="check-row" style={{ flexDirection: "row", paddingBottom: 8 }}><input type="checkbox" checked={importAll} onChange={(e) => setImportAll(e.target.checked)} />結束回合時 Pass／Blocked／Skipped 也匯進 QAOS executions</label>
        <div className="row" style={{ paddingBottom: 2 }}>
          <button className="btn sm ghost" onClick={() => { setOpen(false); setEnv(run.environment); setBuild(run.build); setImportAll(run.import_all); }}>取消</button>
          <button className="btn sm primary" disabled={busy || !dirty || !env.trim()} onClick={save}>儲存</button>
        </div>
      </div>
      {!env.trim() && <div style={{ color: "var(--warn)", fontSize: 12, marginTop: 4 }}>沒有環境就不能送 QAOS 開 bug（execution import 的 --environment 必填）。</div>}
    </div>
  );
}
