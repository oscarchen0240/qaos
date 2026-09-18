import { NavLink } from "react-router-dom";
import type { NavCounts } from "@/lib/api";
import { OutputTree } from "./OutputTree";

const Icon = {
  pipeline: <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><circle cx="5" cy="12" r="2" /><circle cx="12" cy="12" r="2" /><circle cx="19" cy="12" r="2" /><path d="M7 12h3M14 12h3" /></svg>,
  outputs: <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M4 4h10l6 6v10H4z" /><path d="M14 4v6h6" /></svg>,
  reports: <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M5 3h14v18H5z" /><path d="M9 8h6M9 12h6M9 16h4" /></svg>,
  todos: <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M4 6h4v4H4zM4 14h4v4H4zM11 8h9M11 16h9" /></svg>,
  approvals: <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M5 12l4 4L19 6" /></svg>,
  clr: <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><circle cx="12" cy="12" r="9" /><path d="M9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.7.3-1 .9-1 1.7M12 17h.01" /></svg>,
  bug: <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M9 8V6a3 3 0 0 1 6 0v2" /><rect x="7" y="8" width="10" height="12" rx="5" /><path d="M3 13h4M17 13h4M4 19l3-2M20 19l-3-2M4 8l3 2M20 8l-3 2" /></svg>,
  ci: <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M4 7h16M4 12h16M4 17h10" /><circle cx="18" cy="17" r="2" /></svg>,
  automation: <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M12 3v3M12 18v3M3 12h3M18 12h3" /><circle cx="12" cy="12" r="4" /></svg>,
};

interface Props { counts: NavCounts | null; backendOk: boolean }

export function Sidebar({ counts, backendOk }: Props) {
  const item = (to: string, label: string, icon: JSX.Element, badge?: number, hot?: boolean, hotTitle?: string) => (
    <NavLink to={to} className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}>
      {icon}
      <span className="nav-label">{label}</span>
      {badge !== undefined && <span className={`nav-badge ${hot ? "hot" : ""}`} title={hot ? hotTitle : undefined} aria-label={`${label} ${badge}${hot && hotTitle ? `，${hotTitle}` : ""}`}>{badge}</span>}
    </NavLink>
  );
  return (
    <nav className="sidebar">
      <div className="brand">
        <div className="brand-mark">Q</div>
        <div>
          <div className="brand-title">QAOS 指揮台</div>
          <div className="brand-sub">admin · local</div>
        </div>
      </div>
      <div className="nav-group">
        <div className="nav-group-title">監控</div>
        {item("/pipeline", "Pipeline", Icon.pipeline, counts?.pipeline.active_sessions, (counts?.pipeline.active_sessions ?? 0) > 0, "有 session 進行中")}
        {item("/outputs", "產出", Icon.outputs, counts?.outputs.total, (counts?.outputs.unread ?? 0) > 0, `${counts?.outputs.unread} 個未讀`)}
        <OutputTree />
        {item("/ci", "工程 CI", Icon.ci)}
      </div>
      <div className="nav-group">
        <div className="nav-group-title">單據</div>
        {item("/tickets/approvals", "核准 APR", Icon.approvals, counts?.tickets?.approvals_pending, (counts?.tickets?.approvals_pending ?? 0) > 0, "等你決定")}
        {item("/tickets/clarifications", "釐清 CLR", Icon.clr, counts?.tickets?.clarifications_open, (counts?.tickets?.clarifications_open ?? 0) > 0, "尚未結案")}
        {item("/tickets/bugs", "Bug", Icon.bug, counts?.tickets?.bugs_open, (counts?.tickets?.bugs_open ?? 0) > 0, "尚未結案")}
      </div>
      <div className="nav-group">
        <div className="nav-group-title">工作</div>
        {item("/reports", "報告", Icon.reports, counts?.reports.total, (counts?.reports.unreviewed ?? 0) > 0, `${counts?.reports.unreviewed} 份自動報告尚未寫結論`)}
        {item("/todos", "待辦", Icon.todos, counts?.todos.open)}
        {item("/testruns", "測試執行", Icon.automation, counts?.automation.runs, (counts?.automation.open ?? 0) > 0, `${counts?.automation.open} 輪進行中`)}
      </div>
      <div className="sidebar-foot">
        <div><span className={`status-dot ${backendOk ? "on" : "off"}`} />backend {backendOk ? "online" : "offline"}</div>
        <div className="faint">testcases/final · read-only</div>
      </div>
    </nav>
  );
}
