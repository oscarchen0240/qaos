import { useEffect, useState } from "react";
import { PageHeader, EmptyState } from "@/components/PageHeader";
import { api } from "@/lib/api";

interface Contract { status: string; tables: string[]; result_values: string[]; run_status: string[]; endpoints: { method: string; path: string; state: string; desc: string }[]; next: string }

/** M4 stub：頁面可開、顯示預留的資料表與 API 契約；不接任何 runner。 */
export function AutomationPage() {
  const [c, setC] = useState<Contract | null>(null);
  const [runs, setRuns] = useState<unknown[]>([]);
  useEffect(() => {
    api.get<Contract>("/api/automation/contract").then(setC).catch(() => {});
    api.get<unknown[]>("/api/automation/runs").then(setRuns).catch(() => {});
  }, []);
  return (
    <>
      <PageHeader eyebrow="Future" title="自動化測試" description="規劃中（M4 預留）。未來在此挑 TC 建一次執行、逐條記 OK / NG、NG 產 bug 草稿到「單據 › Bug」，完成後自動產一份報告。" />
      <div className="page-body stack" style={{ gap: 16 }}>
        <EmptyState title={runs.length === 0 ? "還沒有任何執行" : `${runs.length} 次執行`}>
          資料表 {c?.tables.join(" / ") ?? "test_runs / test_results"} 已建；尚未接任何 runner，寫入類 API 回 501。
        </EmptyState>
        {c && (
          <div className="panel">
            <div className="section-title">預留的 API 契約</div>
            <table className="table">
              <thead><tr><th>方法</th><th>路徑</th><th>狀態</th><th>用途</th></tr></thead>
              <tbody>
                {c.endpoints.map((e) => (
                  <tr key={e.method + e.path}>
                    <td className="mono">{e.method}</td>
                    <td className="mono">{e.path}</td>
                    <td><span className={`tag ${e.state === "ok" ? "ok" : ""}`}>{e.state === "ok" ? "可用" : "501 未實作"}</span></td>
                    <td>{e.desc}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="card-tags" style={{ marginTop: 12 }}>
              <span className="faint" style={{ fontSize: 12 }}>結果值</span>
              {c.result_values.map((v) => <span key={v} className={`tag ${v === "pass" ? "ok" : v === "fail" ? "danger" : v === "blocked" ? "warn" : ""}`}>{v}</span>)}
              <span className="faint" style={{ fontSize: 12, marginLeft: 8 }}>執行狀態</span>
              {c.run_status.map((v) => <span key={v} className="tag">{v}</span>)}
            </div>
            <div className="muted" style={{ fontSize: 12, marginTop: 10 }}>{c.next}</div>
          </div>
        )}
      </div>
    </>
  );
}
