import { useCallback, useEffect, useState } from "react";
import { Route, Routes, useNavigate } from "react-router-dom";
import { PageHeader, EmptyState, Tabs } from "@/components/PageHeader";
import { useToast } from "@/components/Toast";
import { useConfirm } from "@/components/Confirm";
import { refreshNav } from "@/lib/nav";
import { api, type ReportKind, type ReportLite, type ReportPage } from "@/lib/api";
import { fmtDate } from "@/lib/format";
import { clickable } from "@/lib/a11y";
import { ReportEditor } from "./reports/ReportEditor";

export function ReportsPage() {
  return (
    <Routes>
      <Route index element={<ReportList />} />
      <Route path=":id" element={<ReportEditor />} />
    </Routes>
  );
}

const KIND_LABEL: Record<ReportKind, string> = { output: "產出", automation: "測試執行", manual: "手動" };
const KIND_CLASS: Record<ReportKind, string> = { output: "cyan", automation: "violet", manual: "" };

const PAGE_SIZE = 20;

function ReportList() {
  const [data, setData] = useState<ReportPage | null>(null);
  const [tab, setTab] = useState<"all" | ReportKind>("all");
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const [sort, setSort] = useState<"updated_at" | "id" | "title" | "kind">("updated_at");
  const [desc, setDesc] = useState(true);
  const setSort2 = (k: typeof sort) => { if (sort === k) setDesc(!desc); else { setSort(k); setDesc(k === "updated_at" || k === "id"); } setPage(1); };
  const th = (k: typeof sort, label: string) => (
    <th onClick={() => setSort2(k)} style={{ cursor: "pointer", userSelect: "none" }} aria-sort={sort === k ? (desc ? "descending" : "ascending") : "none"} title="點擊排序">{label}{sort === k ? (desc ? " ↓" : " ↑") : ""}</th>
  );
  const nav = useNavigate();
  const { toast } = useToast();
  const confirm = useConfirm();

  const load = useCallback(() => {
    const qs = new URLSearchParams({ q, kind: tab === "all" ? "" : tab, page: String(page), page_size: String(PAGE_SIZE), sort, desc: String(desc) });
    return api.get<ReportPage>(`/api/reports?${qs}`).then(setData).catch((e) => toast(`載入失敗：${e.message}`, "danger"));
  }, [q, tab, page, sort, desc, toast]);
  useEffect(() => { const t = setTimeout(load, q ? 250 : 0); return () => clearTimeout(t); }, [load, q]);
  const reports: ReportLite[] = data?.items ?? [];
  const total = data?.total ?? 0;
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const remove = async (r: ReportLite) => {
    if (!(await confirm({ title: "刪除報告？", message: r.title, confirmText: "刪除", danger: true }))) return;
    await api.del(`/api/reports/${r.id}`);
    toast("已刪除"); load(); refreshNav();
  };

  return (
    <>
      <PageHeader
        eyebrow="Work"
        title="報告"
        description="產出完成時自動建立報告並記錄工作流程（run、階段、核准、gate）；測試執行結束後的測試報告也會送進這裡。你只需要補結論。"
      />
      <Tabs
        tabs={[{ key: "all", label: "全部", count: data?.counts.all }, { key: "output", label: "產出", count: data?.counts.output }, { key: "automation", label: "測試執行", count: data?.counts.automation }]}
        active={tab}
        onChange={(k) => { setTab(k as typeof tab); setPage(1); }}
      />
      <div className="page-body">
        <div className="toolbar">
          <input className="input" style={{ maxWidth: 360 }} placeholder="搜尋標題、摘要、模組、run…" value={q} onChange={(e) => { setQ(e.target.value); setPage(1); }} />
          <div className="grow" />
          <span className="faint mono">{total} 份 · 第 {page} / {pages} 頁</span>
          <button className="btn ghost sm" disabled={page <= 1} onClick={() => setPage(page - 1)}>上一頁</button>
          <button className="btn ghost sm" disabled={page >= pages} onClick={() => setPage(page + 1)}>下一頁</button>
        </div>
        {!data ? <div className="faint">載入中…</div> : reports.length === 0 ? (
          <EmptyState title={q ? "沒有符合的報告" : "還沒有報告"}>
            {q ? "換個關鍵字試試。" : "當 testcases/final/ 出現新產出、或測試回合結束時，報告會自動建立在這裡。"}
          </EmptyState>
        ) : (
          <table className="table">
            <thead><tr>{th("id", "#")}{th("kind", "類型")}{th("title", "標題")}<th>摘要</th><th>引用產出</th>{th("updated_at", "更新")}<th></th></tr></thead>
            <tbody>
              {reports.map((r) => (
                <tr key={r.id} className="clickable" {...clickable(() => nav(`/reports/${r.id}`), `開啟報告 ${r.title}`)}>
                  <td className="mono faint">{r.id}</td>
                  <td><span className={`tag ${KIND_CLASS[r.kind]}`}>{KIND_LABEL[r.kind]}</span></td>
                  <td style={{ fontWeight: 500 }}>{r.title}{r.kind !== "manual" && <div className="faint" style={{ fontSize: 12, fontWeight: 400 }}>自動產生 {fmtDate(r.auto_generated_at)}</div>}</td>
                  <td className="muted" style={{ maxWidth: 320 }}>{r.summary}</td>
                  <td><div className="card-tags">{r.output_paths.map((p) => <span key={p} className="tag cyan">{p}</span>)}</div></td>
                  <td className="mono">{fmtDate(r.updated_at)}</td>
                  <td onClick={(e) => e.stopPropagation()}>
                    <div className="row">
                      <a className="btn ghost sm" href={`/api/reports/${r.id}/export?format=md`}>MD</a>
                      <a className="btn ghost sm" href={`/api/reports/${r.id}/export?format=html`}>HTML</a>
                      <button className="btn ghost sm" style={{ color: "var(--danger)" }} onClick={() => remove(r)}>刪除</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}
