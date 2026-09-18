import { useEffect, useState } from "react";
import { useToast } from "@/components/Toast";
import { useConfirm } from "@/components/Confirm";
import { api, type CommandOut, type ExecResult, type Execution, type TicketDraft } from "@/lib/api";
import { fmtDate } from "@/lib/format";
import { Copy, CheckCircle, Warning, PaperPlaneRight, XCircle } from "@phosphor-icons/react";

const WRITES: Record<string, string[]> = {
  approval: ["approvals/<APR>.yaml", "runs/<RUN>/run.yaml、audit.log、runs/_audit.log", "啟用 TC：testcases/versions/<TC>/v<N>.yaml、testcases/registry/<TC>.yaml", "推進後可能新建 approvals/APR-*.yaml 或 artifacts/summaries/", "不會寫 testcases/final/（請 QA session 重新匯出）"],
  clarification: ["clarifications/<p>/<a>/<CLR>.yaml 與 .md", "answer：audit.log、requirements 文件、PENDING 核准單的 .md/.html", "clarifications/index.md（平台順帶重建）"],
  bug: ["bugs/<p>/<a>/<BUG>.yaml", "runs/_audit.log", "close：新建 approvals/APR-*.yaml", "bugs/index.md（平台順帶重建）"],
};

/** 產生的 bin/qaos 指令：M5b 由平台直接執行；保留複製指令當備援。 */
export function CommandBox({ ticketId, kind, cmd, draft, onSent, beforeSend }: { ticketId: string; kind: "approval" | "clarification" | "bug"; cmd: CommandOut | null; draft: TicketDraft | null; onSent: () => void; beforeSend?: () => Promise<boolean> }) {
  const { toast } = useToast();
  const confirm = useConfirm();
  const [busy, setBusy] = useState(false);
  const [last, setLast] = useState<ExecResult | Execution | null>(null);
  useEffect(() => {
    setLast(null);
    api.get<Execution[]>(`/api/tickets/${ticketId}/executions`).then((xs) => setLast(xs[0] ?? null)).catch(() => {});
  }, [ticketId]);
  if (!cmd) return null;
  const ready = !!cmd.command && cmd.warnings.length === 0;

  const copy = async () => {
    try { await navigator.clipboard.writeText(cmd.command); toast("指令已複製", "ok"); }
    catch { toast("複製失敗（瀏覽器不允許剪貼簿）", "danger"); }
  };
  const send = async () => {
    if (beforeSend && !(await beforeSend())) return;
    const ok = await confirm({
      title: "送出到 QAOS？",
      message: (
        <div className="stack" style={{ gap: 8 }}>
          <pre className="cmd-pre" style={{ margin: 0 }}>{cmd.command}</pre>
          <div className="faint" style={{ fontSize: 12 }}>平台會在專案根目錄執行這條指令，QAOS 會寫入：</div>
          <ul className="tc-list" style={{ fontSize: 12 }}>{(WRITES[kind] ?? []).map((w, i) => <li key={i}>{w}</li>)}</ul>
        </div>
      ),
      confirmText: "執行",
      danger: kind === "approval" && (draft?.decision === "reject" || draft?.decision === "override"),
    });
    if (!ok) return;
    setBusy(true);
    try {
      const r = await api.post<ExecResult>(`/api/tickets/${ticketId}/execute`);
      setLast(r);
      toast(r.ok ? "QAOS 已執行" : `執行失敗（exit ${r.exit_code}）`, r.ok ? "ok" : "danger");
      onSent();
    } catch (e) { toast(`無法執行：${(e as Error).message}`, "danger"); }
    finally { setBusy(false); }
  };
  const manual = async () => {
    try { await api.post(`/api/tickets/${ticketId}/sent`, { command: cmd.command }); toast("已記錄為手動執行", "ok"); onSent(); }
    catch (e) { toast(`記錄失敗：${(e as Error).message}`, "danger"); }
  };

  return (
    <div className="cmd-box">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <div className="section-title" style={{ margin: 0 }}>送回 QAOS 的指令</div>
        <div className="row">
          <button className="btn sm ghost" onClick={copy} disabled={!ready} title="備援：自己貼到 QA session 執行"><Copy className="ic sm" aria-hidden="true" />複製</button>
          <button className="btn sm ghost" onClick={manual} disabled={!ready} title="你已手動貼去執行，只記錄"><CheckCircle className="ic sm" aria-hidden="true" />已手動執行</button>
          <button className="btn sm primary" onClick={send} disabled={busy || !ready}><PaperPlaneRight className="ic sm" aria-hidden="true" />{busy ? "執行中…" : "送出到 QAOS"}</button>
        </div>
      </div>
      {cmd.warnings.length > 0 && (
        <div className="stack" style={{ gap: 2 }}>
          {cmd.warnings.map((w, i) => <div key={i} className="row" style={{ color: "var(--warn)", fontSize: 12 }}><Warning className="ic sm" aria-hidden="true" />{w}</div>)}
        </div>
      )}
      <pre className="cmd-pre">{cmd.command || "（尚未組出指令）"}</pre>
      {last && (
        <div className={`exec-result ${last.ok ? "ok" : "fail"}`}>
          <div className="row" style={{ gap: 6 }}>
            {last.ok ? <CheckCircle className="ic sm" aria-hidden="true" /> : <XCircle className="ic sm" aria-hidden="true" />}
            <span style={{ fontWeight: 600 }}>{last.ok ? "QAOS 已執行" : `執行失敗（exit ${last.exit_code}）`}</span>
            <span className="faint mono" style={{ fontSize: 12 }}>{fmtDate(last.ended_at)}</span>
            {last.run_status_after && <span className="tag">run {last.run_status_after}</span>}
            {last.next_task && <span className="tag accent">next {last.next_task}</span>}
            {last.session_id && <span className="tag" title="交接給這個 QA session">→ {last.session_id.slice(0, 8)}</span>}
          </div>
          {last.hint && <div style={{ fontSize: 12.5 }}>{last.hint}</div>}
          {last.stdout && <pre className="cmd-pre" style={{ fontSize: 11.5 }}>{last.stdout}</pre>}
          {last.stderr && <pre className="cmd-pre" style={{ fontSize: 11.5, color: "var(--danger)" }}>{last.stderr}</pre>}
          {last.command !== cmd.command && <div className="faint" style={{ fontSize: 12 }}>（上次執行的指令與目前草稿不同）</div>}
        </div>
      )}
      {!last && draft?.sent_at && <div className="faint" style={{ fontSize: 12 }}>手動執行記錄：{fmtDate(draft.sent_at)}</div>}
    </div>
  );
}
