import { useEffect, useMemo, useState } from "react";
import { EmptyState } from "@/components/PageHeader";
import { api, type DurationAnalysis, type StageAgg } from "@/lib/api";
import { fmtElapsed } from "@/lib/format";
import { clickable } from "@/lib/a11y";

type Stat = "avg" | "median" | "max";
const STAT_LABEL: Record<Stat, string> = { avg: "平均", median: "中位數", max: "最大" };
const sec = (s: number | null | undefined) => s == null ? "—" : fmtElapsed(s * 1000);

/** 各節點耗時分析：哪個節點最花時間、agent 工作 vs 等人 vs gate 的比例、每個 run 的分解。 */
export function DurationsView({ onOpenRun }: { onOpenRun: (id: string) => void }) {
  const [scope, setScope] = useState<"completed" | "terminal" | "all">(() => (localStorage.getItem("qaos.dur.scope") as "completed" | "terminal" | "all") || "completed");
  const [stat, setStat] = useState<Stat>(() => (localStorage.getItem("qaos.dur.stat") as Stat) || "median");
  const [data, setData] = useState<DurationAnalysis | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => { try { localStorage.setItem("qaos.dur.scope", scope); localStorage.setItem("qaos.dur.stat", stat); } catch { /* ignore */ } }, [scope, stat]);
  useEffect(() => {
    let alive = true;
    const load = () => api.get<DurationAnalysis>(`/api/pipeline/durations?scope=${scope}`).then((d) => { if (alive) { setData(d); setErr(null); } }).catch((e) => alive && setErr(e.message));
    load(); const id = setInterval(load, 30000);
    return () => { alive = false; clearInterval(id); };
  }, [scope]);

  const stages = useMemo(() => (data?.stages ?? []).filter((s) => s.n > 0), [data]);
  const maxVal = useMemo(() => Math.max(1, ...stages.map((s) => (s[stat] ?? 0))), [stages, stat]);
  const top = useMemo(() => stages.length ? stages.reduce((a, b) => ((b[stat] ?? 0) > (a[stat] ?? 0) ? b : a)) : null, [stages, stat]);
  const cols = useMemo(() => (data?.stages ?? []).filter((s) => data?.runs.some((r) => r.stages[s.id] && !r.stages[s.id].no_history)), [data]);

  if (err) return <div className="form-error">{err}</div>;
  if (!data) return <div className="faint">載入中…</div>;

  return (
    <div className="stack" style={{ gap: 16 }}>
      <div className="toolbar" style={{ flexWrap: "wrap" }}>
        <span className="faint" style={{ fontSize: 12 }}>範圍</span>
        <div className="seg">
          {(["completed", "terminal", "all"] as const).map((k) => <button key={k} className={`seg-btn ${scope === k ? "on" : ""}`} onClick={() => setScope(k)}>{k === "completed" ? "只看已完成" : k === "terminal" ? "含取消／失敗" : "含進行中"}</button>)}
        </div>
        <span className="faint" style={{ fontSize: 12, marginLeft: 8 }}>統計值</span>
        <div className="seg">
          {(["median", "avg", "max"] as Stat[]).map((k) => <button key={k} className={`seg-btn ${stat === k ? "on" : ""}`} onClick={() => setStat(k)}>{STAT_LABEL[k]}</button>)}
        </div>
        <div className="grow" />
        <span className="faint mono" style={{ fontSize: 12 }}>{data.summary.n} 個 run · 整條 {STAT_LABEL[stat === "max" ? "max" : stat]} {sec(stat === "avg" ? data.summary.total_avg : stat === "max" ? data.summary.total_max : data.summary.total_median)} · 等人平均 {sec(data.summary.human_avg)} · agent 平均 {sec(data.summary.agent_avg)}</span>
      </div>

      {stages.length === 0 ? <EmptyState title="沒有可分析的 run">run.yaml 的 task history 沒有時間點，或範圍內沒有 run。</EmptyState> : (
        <>
          <div className="panel">
            <div className="section-title">各節點耗時（{STAT_LABEL[stat]}，從「可開始」到「完成」）</div>
            <div className="stack" style={{ gap: 6 }}>
              {stages.map((s) => <StageBar key={s.id} s={s} stat={stat} maxVal={maxVal} isTop={top?.id === s.id} onOpenRun={onOpenRun} />)}
            </div>
            <div className="faint" style={{ fontSize: 12, marginTop: 10 }}>
              時間語意：QAOS 在 agent 提交產物時才把 task 標 RUNNING，所以「agent 工作」＝READY→RUNNING，「gate」＝RUNNING→DONE，「等人」＝核准單開出到你決定。迭代多次的節點會把每輪加總。
            </div>
          </div>

          <div className="panel" style={{ overflowX: "auto" }}>
            <div className="section-title">每個 run 的分解（點 run 看細節）</div>
            <table className="table dur-table">
              <thead>
                <tr><th>Run</th><th>Spec</th><th>狀態</th><th>整條</th><th>等人</th>{cols.map((c) => <th key={c.id}>{c.title}</th>)}</tr>
              </thead>
              <tbody>
                {data.runs.map((r) => {
                  const rowMax = Math.max(1, ...cols.map((c) => r.stages[c.id]?.elapsed ?? 0));
                  return (
                    <tr key={r.run_id} className="clickable" {...clickable(() => onOpenRun(r.run_id), `開啟 ${r.run_id}`)}>
                      <td className="mono">{r.run_id}</td>
                      <td className="mono faint">{r.spec}</td>
                      <td><span className={`tag ${r.status === "COMPLETED" ? "ok" : r.status === "CANCELLED" || r.status === "FAILED" ? "danger" : "accent"}`}>{r.status}</span></td>
                      <td className="mono">{sec(r.total)}</td>
                      <td className="mono">{r.human_total > 0 ? sec(r.human_total) : "—"}</td>
                      {cols.map((c) => {
                        const d = r.stages[c.id];
                        if (!d || d.no_history || d.elapsed == null) return <td key={c.id} className="faint">—</td>;
                        const heat = Math.min(1, d.elapsed / rowMax);
                        return (
                          <td key={c.id} className="mono dur-cell" style={{ background: `rgba(110,168,255,${(0.06 + heat * 0.28).toFixed(2)})` }} title={`agent ${sec(d.work)} · gate ${sec(d.gate)} · 等人 ${sec(d.human)} · ${d.iterations} 輪`}>
                            {sec(d.elapsed)}{d.running ? "…" : ""}{d.iterations > 1 ? <span className="faint"> ×{d.iterations}</span> : null}
                          </td>
                        );
                      })}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}

function StageBar({ s, stat, maxVal, isTop, onOpenRun }: { s: StageAgg; stat: Stat; maxVal: number; isTop: boolean; onOpenRun: (id: string) => void }) {
  const v = s[stat] ?? 0;
  const pct = Math.max(2, (v / maxVal) * 100);
  const parts = [{ k: "work", v: s.work_avg ?? 0, cls: "work", label: "agent 工作" }, { k: "gate", v: s.gate_avg ?? 0, cls: "gate", label: "gate" }, { k: "human", v: s.human_avg ?? 0, cls: "human", label: "等人" }];
  const tot = parts.reduce((a, p) => a + p.v, 0) || 1;
  return (
    <div className={`dur-row ${isTop ? "top" : ""}`}>
      <div className="dur-label">
        <span>{s.title}</span>
        <span className="faint mono" style={{ fontSize: 11 }}>{s.agent?.replace("agent-", "") ?? ""} · n={s.n}{(s.iter_avg ?? 0) > 1 ? ` · 平均 ${s.iter_avg!.toFixed(1)} 輪` : ""}</span>
      </div>
      <div className="dur-bar-wrap" title={parts.map((p) => `${p.label} ${sec(p.v)}`).join(" · ")}>
        <div className="dur-bar" style={{ width: `${pct}%` }}>
          {parts.map((p) => <span key={p.k} className={`dur-seg ${p.cls}`} style={{ width: `${(p.v / tot) * 100}%` }} />)}
        </div>
      </div>
      <div className="dur-val mono">{sec(v)}</div>
      <div className="dur-extra faint mono">最大 {sec(s.max)}{s.worst_run && <button className="link-btn" style={{ marginLeft: 6 }} onClick={() => onOpenRun(s.worst_run!)}>{s.worst_run}</button>}</div>
      {isTop && <span className="tag warn">最花時間</span>}
    </div>
  );
}
