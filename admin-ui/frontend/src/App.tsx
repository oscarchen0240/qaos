import { useEffect, useState } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Sidebar } from "@/components/Sidebar";
import { ToastProvider } from "@/components/Toast";
import { ConfirmProvider } from "@/components/Confirm";
import { api, type NavCounts } from "@/lib/api";
import { NAV_REFRESH_EVENT } from "@/lib/nav";
import { TodosPage } from "@/pages/TodosPage";
import { PipelinePage } from "@/pages/PipelinePage";
import { OutputsPage } from "@/pages/OutputsPage";
import { ReportsPage } from "@/pages/ReportsPage";
import { TestRunsPage } from "@/pages/TestRunsPage";
import { TestRunPage } from "@/pages/testruns/TestRunPage";
import { ApprovalsPage } from "@/pages/tickets/ApprovalsPage";
import { ClarificationsPage } from "@/pages/tickets/ClarificationsPage";
import { BugsPage } from "@/pages/tickets/BugsPage";

export function App() {
  const [counts, setCounts] = useState<NavCounts | null>(null);
  const [backendOk, setBackendOk] = useState(true);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let alive = true;
    const load = () =>
      api.get<NavCounts>("/api/nav").then((c) => { if (alive) { setCounts(c); setBackendOk(true); } })
        .catch(() => { if (alive) setBackendOk(false); });
    load();
    const id = setInterval(load, 15000);
    const onRefresh = () => load();
    window.addEventListener(NAV_REFRESH_EVENT, onRefresh);
    return () => { alive = false; clearInterval(id); window.removeEventListener(NAV_REFRESH_EVENT, onRefresh); };
  }, [tick]);

  return (
    <ToastProvider>
      <ConfirmProvider>
      <BrowserRouter>
        <div className="shell">
          <Sidebar counts={counts} backendOk={backendOk} />
          <main className="main">
            <Routes>
              <Route path="/" element={<Navigate to="/pipeline" replace />} />
              <Route path="/pipeline" element={<PipelinePage />} />
              <Route path="/outputs" element={<OutputsPage />} />
              <Route path="/reports/*" element={<ReportsPage />} />
              <Route path="/todos" element={<TodosPage onChanged={() => setTick((t) => t + 1)} />} />
              <Route path="/tickets/approvals" element={<ApprovalsPage />} />
              <Route path="/tickets/clarifications" element={<ClarificationsPage />} />
              <Route path="/tickets/bugs" element={<BugsPage />} />
              <Route path="/testruns" element={<TestRunsPage />} />
              <Route path="/testruns/:id" element={<TestRunPage />} />
              <Route path="/automation" element={<Navigate to="/testruns" replace />} />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
      </ConfirmProvider>
    </ToastProvider>
  );
}
