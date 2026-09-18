import { useEffect, useState } from "react";
import { PageHeader, EmptyState } from "@/components/PageHeader";
import { api, type CiStatusResp } from "@/lib/api";
import { fmtDate } from "@/lib/format";
import { ArrowSquareOut, CheckCircle, XCircle, CircleNotch, MinusCircle } from "@phosphor-icons/react";

const ST: Record<string, { label: string; cls: string; icon: JSX.Element }> = {
  pass: { label: "通過", cls: "ok", icon: <CheckCircle className="ic" aria-hidden="true" /> },
  fail: { label: "失敗", cls: "danger", icon: <XCircle className="ic" aria-hidden="true" /> },
  running: { label: "執行中", cls: "accent", icon: <CircleNotch className="ic" aria-hidden="true" /> },
  skipped: { label: "略過", cls: "", icon: <MinusCircle className="ic" aria-hidden="true" /> },
};

/** 工程 CI：tools/qaos 與 admin-ui 的程式有沒有壞（pytest）。不是產品 TC 的執行結果，那在「測試執行」。 */
export function CiPage() {
  const [d, setD] = useState<CiStatusResp | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    let alive = true;
    const load = () => api.get<CiStatusResp>("/api/ci/status").then((x) => { if (alive) { setD(x); setErr(null); } }).catch((e) => alive && setErr(e.message));
    load(); const id = setInterval(load, 30000);
    return () => { alive = false; clearInterval(id); };
  }, []);
  const s = d?.status ?? null;
  return (
    <>
      <PageHeader eyebrow="Monitor" title="工程 CI" description="這頁看的是程式有沒有壞：tools/qaos 的 Runtime pytest 與 admin-ui 後端／交握的 pytest。產品測試案例的執行結果不在這裡，請看「測試執行」。"
        actions={s?.web_url || d?.web_url ? <a className="btn" href={s?.web_url || d?.web_url} target="_blank" rel="noreferrer"><ArrowSquareOut className="ic sm" aria-hidden="true" />GitLab Pipeline</a> : undefined} />
      <div className="page-body">
        {err && <div className="form-error">{err}</div>}
        {!d ? <div className="faint">載入中…</div> : !d.available || !s ? (
          <EmptyState title="還沒有工程 CI 的狀態檔">
            <div className="stack" style={{ gap: 8, textAlign: "left" }}>
              <div>控制台讀 <span className="mono">{d.file}</span>，目前不存在{d.error ? `（${d.error}）` : ""}。三種接法：</div>
              <ol className="tc-steps">
                <li>本機跑一次並寫檔：<code className="mono">python3 admin-ui/scripts/write_ci_status.py --run</code></li>
                <li>GitLab CI（<span className="mono">.gitlab-ci.yml</span> 的 admin-ui-pytest job）會產 <span className="mono">reports/ci-status.json</span> artifact，下載後放到上面的路徑。</li>
                <li>設環境變數 <span className="mono">GITLAB_PIPELINE_URL</span> 讓右上角出現 GitLab 連結。</li>
              </ol>
              <div className="faint">範例格式：<span className="mono">{d.example}</span>{d.remote ? `；目前 git remote：${d.remote}` : "；尚未接遠端 CI"}</div>
            </div>
          </EmptyState>
        ) : (
          <div className="stack" style={{ gap: 14 }}>
            <div className={`ci-hero ${s.status}`}>
              <div className="ci-hero-icon">{ST[s.status]?.icon}</div>
              <div className="stack" style={{ gap: 4 }}>
                <div style={{ fontSize: 18, fontWeight: 600 }}>最近一次工程 CI：{ST[s.status]?.label ?? s.status}</div>
                <div className="faint" style={{ fontSize: 12.5 }}>
                  <span className="mono">{s.sha}</span>{s.branch ? ` · ${s.branch}` : ""} · {fmtDate(s.updated_at)} · 來源 {s.source === "gitlab" ? "GitLab CI" : "本機 pytest"} · 讀自 <span className="mono">{d.file}</span>
                </div>
              </div>
              <div className="grow" />
              <div className="row" style={{ gap: 16 }}>
                <Stat label="測試數" v={s.jobs.reduce((a, j) => a + j.tests, 0)} />
                <Stat label="失敗" v={s.jobs.reduce((a, j) => a + j.failures + j.errors, 0)} danger />
                <Stat label="秒" v={Math.round(s.jobs.reduce((a, j) => a + (j.duration_s || 0), 0))} />
              </div>
            </div>
            <table className="table">
              <thead><tr><th>Job</th><th>狀態</th><th>測試</th><th>失敗</th><th>錯誤</th><th>耗時</th><th>說明</th></tr></thead>
              <tbody>
                {s.jobs.map((j) => (
                  <tr key={j.name}>
                    <td className="mono">{j.name}</td>
                    <td><span className={`tag ${ST[j.status]?.cls ?? ""}`}>{ST[j.status]?.label ?? j.status}</span></td>
                    <td className="mono">{j.tests}</td>
                    <td className="mono" style={j.failures ? { color: "var(--danger)" } : undefined}>{j.failures}</td>
                    <td className="mono" style={j.errors ? { color: "var(--danger)" } : undefined}>{j.errors}</td>
                    <td className="mono">{j.duration_s}s</td>
                    <td className="faint">{j.name === "runtime-pytest" ? "tools/qaos Runtime：tests/（iteration 上限、clarification、bug 狀態機…）" : j.name === "admin-ui-pytest" ? "admin-ui 後端與交握：qaos_exec 預檢、handoff_relay、guard_qaos、Pipeline 主狀態" : ""}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {s.jobs.some((j) => j.log) && (
              <details className="details"><summary>pytest 輸出尾段</summary>
                {s.jobs.filter((j) => j.log).map((j) => <pre key={j.name} className="cmd-pre" style={{ marginTop: 8 }}>{`[${j.name}]\n${j.log}`}</pre>)}
              </details>
            )}
            <div className="faint" style={{ fontSize: 12 }}>觸發規則：GitLab merge request 與 push 到 main（.gitlab-ci.yml）。本機更新這頁：<span className="mono">python3 admin-ui/scripts/write_ci_status.py --run</span>。</div>
          </div>
        )}
      </div>
    </>
  );
}

function Stat({ label, v, danger }: { label: string; v: number; danger?: boolean }) {
  return <div className="apr-stat"><div className={`apr-stat-v ${danger && v > 0 ? "danger" : ""}`}>{v}</div><div className="apr-stat-k">{label}</div></div>;
}
