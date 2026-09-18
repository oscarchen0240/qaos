import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { EmptyState } from "@/components/PageHeader";
import { api, type RunRef, type SpecFlowData, type SpecFlow } from "@/lib/api";
import { fmtDate, fmtElapsed } from "@/lib/format";
import { clickable } from "@/lib/a11y";
import { CheckCircle, Circle, Warning, ArrowRight } from "@phosphor-icons/react";

const DOD_LABEL: Record<string, string> = { integrated: "整合完成", shadow_doc: "shadow-test 記錄", final: "final 已產出" };
const RUN_CLASS: Record<string, string> = { COMPLETED: "ok", CANCELLED: "", FAILED: "danger", RUNNING: "accent", WAITING_HUMAN: "warn", CREATED: "" };
const sec = (s: number | null | undefined) => s == null ? "—" : fmtElapsed(s * 1000);

/**
 * Spec 進度：每份 spec 一列匯流圖。
 *   Phase 2 run ─┐
 *   Phase 3 run ─┴→ 交叉整合 → 匯出 final    ＋ DoD 三項
 */
export function SpecFlowView({ onOpenRun }: { onOpenRun: (id: string) => void }) {
  const [data, setData] = useState<SpecFlowData | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [onlyMissing, setOnlyMissing] = useState(false);
  const nav = useNavigate();
  useEffect(() => {
    let alive = true;
    const load = () => api.get<SpecFlowData>("/api/pipeline/specs").then((d) => { if (alive) { setData(d); setErr(null); } }).catch((e) => alive && setErr(e.message));
    load(); const id = setInterval(load, 15000);
    return () => { alive = false; clearInterval(id); };
  }, []);
  const specs = useMemo(() => (data?.specs ?? []).filter((s) => !onlyMissing || !s.complete), [data, onlyMissing]);
  const missingCount = (data?.specs ?? []).filter((s) => !s.complete).length;
  if (err) return <div className="form-error">{err}</div>;
  if (!data) return <div className="faint">載入中…</div>;
  if (data.specs.length === 0) return <EmptyState title="還沒有 spec-to-testcase 的 run" />;
  return (
    <div className="stack" style={{ gap: 12 }}>
      <div className="toolbar">
        <label className="check-row" style={{ flexDirection: "row" }}><input type="checkbox" checked={onlyMissing} onChange={(e) => setOnlyMissing(e.target.checked)} />只看未完成（{missingCount}）</label>
        <div className="grow" />
        <span className="faint" style={{ fontSize: 12 }}>Phase 2＝人扮 agent 腳本的 run；Phase 3＝qaos-test-designer 的 run；整合與匯出以 shadow-test 文件、修訂 run、final 檔為證據</span>
      </div>
      <div className="stack" style={{ gap: 8 }}>
        {specs.map((s) => <SpecRow key={s.key} s={s} onOpenRun={onOpenRun} onOutputs={(k) => nav(`/outputs?group=${encodeURIComponent(k)}`)} />)}
      </div>
    </div>
  );
}

function RunPill({ r, label, onOpenRun }: { r: RunRef | null; label: string; onOpenRun: (id: string) => void }) {
  if (!r) return <div className="flow-node empty"><div className="flow-label">{label}</div><div className="faint" style={{ fontSize: 12 }}>尚未執行</div></div>;
  return (
    <div className={`flow-node ${RUN_CLASS[r.status] ?? ""}`} {...clickable(() => onOpenRun(r.run_id), `開啟 ${r.run_id}`)}>
      <div className="flow-label">{label}{r.spec_version ? <span className="faint"> v{r.spec_version}</span> : null}</div>
      <div className="mono" style={{ fontSize: 12 }}>{r.run_id}</div>
      <div className="row" style={{ gap: 4 }}><span className={`tag ${RUN_CLASS[r.status] ?? ""}`}>{r.status}</span>{r.iterations > 1 && <span className="tag">{r.iterations} 輪</span>}</div>
    </div>
  );
}

function SpecRow({ s, onOpenRun, onOutputs }: { s: SpecFlow; onOpenRun: (id: string) => void; onOutputs: (k: string) => void }) {
  const i = s.integration; const f = s.final;
  const p2 = s.phase2[s.phase2.length - 1] ?? null;
  const p3 = s.phase3 ?? s.others.find((o) => o.phase === "phase3") ?? null;
  return (
    <div className={`flow-row ${s.complete ? "" : "incomplete"}`}>
      <div className="flow-head">
        <span style={{ fontWeight: 600 }}>{s.key}</span>
        <span className="mono faint" style={{ fontSize: 12 }}>{s.spec_id}</span>
        {s.approval_id && <span className="tag" title="Phase 3 的核准單">{s.approval_id}</span>}
        <div className="grow" />
        {(["integrated", "shadow_doc", "final"] as const).map((k) => (
          <span key={k} className={`tag ${s.dod[k] ? "ok" : "warn"}`} title={k === "shadow_doc" && i.doc ? i.doc : k === "final" && f.at ? `final ${fmtDate(f.at)}${f.stale ? "（已過期）" : ""}` : ""}>
            {s.dod[k] ? <CheckCircle className="ic sm" aria-hidden="true" /> : <Warning className="ic sm" aria-hidden="true" />}{DOD_LABEL[k]}
          </span>
        ))}
      </div>
      <div className="flow-line">
        <div className="flow-branches">
          <RunPill r={p2} label="Phase 2" onOpenRun={onOpenRun} />
          <RunPill r={p3} label="Phase 3" onOpenRun={onOpenRun} />
        </div>
        <div className="flow-merge" aria-hidden="true"><ArrowRight className="ic" /></div>
        <div className={`flow-node stage ${i.status}`}>
          <div className="flow-label">交叉整合</div>
          <div className="row" style={{ gap: 4, flexWrap: "wrap" }}>
            <span className={`tag ${i.status === "done" ? "ok" : i.status === "active" ? "accent" : ""}`}>{i.status === "done" ? "完成" : i.status === "active" ? "進行中" : "待進行"}</span>
            {i.elapsed != null && <span className="mono faint" style={{ fontSize: 12 }}>{sec(i.elapsed)}{i.status === "active" ? "…" : ""}</span>}
            {i.revisions.length > 0 && <span className="tag violet" title={i.revisions.map((r) => `${r.run_id} ${r.status}`).join("\n")}>修訂 {i.revisions.length}{i.revisions_open ? `（${i.revisions_open} 進行中）` : ""}</span>}
          </div>
          {i.doc ? <div className="faint mono" style={{ fontSize: 11 }} title={i.doc}>{i.doc.split("/").pop()}</div> : <div className="faint" style={{ fontSize: 11 }}>無 shadow-test 文件</div>}
        </div>
        <div className="flow-merge" aria-hidden="true"><ArrowRight className="ic" /></div>
        <div className={`flow-node stage ${f.status === "done" ? "done" : f.status === "stale" ? "stale" : "pending"}`} {...(f.group_key ? clickable(() => onOutputs(f.group_key!), `開啟產出 ${f.group_key}`) : {})}>
          <div className="flow-label">匯出 final</div>
          <div className="row" style={{ gap: 4, flexWrap: "wrap" }}>
            <span className={`tag ${f.status === "done" ? "ok" : f.status === "stale" ? "danger" : ""}`}>{f.status === "done" ? "完成" : f.status === "stale" ? "final 已過期" : "待進行"}</span>
            {f.elapsed != null && <span className="mono faint" style={{ fontSize: 12 }}>{sec(f.elapsed)}</span>}
            {f.case_count != null && <span className="tag">{f.case_count} 條</span>}
          </div>
          {f.at ? <div className="faint mono" style={{ fontSize: 11 }}>{fmtDate(f.at)}</div> : <div className="faint" style={{ fontSize: 11 }}><Circle className="ic sm" aria-hidden="true" /> testcases/final 無檔</div>}
        </div>
      </div>
      {s.others.length > 0 && <div className="faint" style={{ fontSize: 12, paddingLeft: 4 }}>其他嘗試：{s.others.map((o) => <button key={o.run_id} className="link-btn mono" style={{ marginRight: 8 }} onClick={() => onOpenRun(o.run_id)}>{o.run_id} {o.status}</button>)}</div>}
    </div>
  );
}
