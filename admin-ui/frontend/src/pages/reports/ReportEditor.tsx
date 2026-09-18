import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { PageHeader } from "@/components/PageHeader";
import { Drawer } from "@/components/Drawer";
import { useToast } from "@/components/Toast";
import { refreshNav } from "@/lib/nav";
import { api, type OutputGroup, type Report } from "@/lib/api";
import { fmtDate } from "@/lib/format";
import { ArrowLeft } from "@phosphor-icons/react";

export function ReportEditor() {
  const { id } = useParams();
  const [sp] = useSearchParams();
  const nav = useNavigate();
  const { toast } = useToast();
  const isNew = !id;

  const [title, setTitle] = useState("");
  const [summary, setSummary] = useState("");
  const [body, setBody] = useState("");
  const [paths, setPaths] = useState<string[]>([]);
  const [saved, setSaved] = useState<Report | null>(null);
  const [outputs, setOutputs] = useState<OutputGroup[]>([]);
  const [pickOpen, setPickOpen] = useState(false);
  const [mode, setMode] = useState<"edit" | "preview">("edit");
  const [previewHtml, setPreviewHtml] = useState("");
  const [autoHtml, setAutoHtml] = useState("");
  const [autoOpen, setAutoOpen] = useState(true);
  const [busy, setBusy] = useState(false);
  const loadedFor = useRef<string | null>(null);

  useEffect(() => { api.get<OutputGroup[]>("/api/outputs").then(setOutputs).catch(() => setOutputs([])); }, []);

  useEffect(() => {
    const key = id ?? `new:${sp.get("outputs") ?? ""}`;
    if (loadedFor.current === key) return;
    loadedFor.current = key;
    if (id) {
      api.get<Report>(`/api/reports/${id}`).then((r) => {
        setSaved(r); setTitle(r.title); setSummary(r.summary); setBody(r.body_md); setPaths(r.output_paths);
        if (r.auto_md) api.post<{ html: string }>("/api/reports/preview", { body_md: r.auto_md }).then((x) => setAutoHtml(x.html)).catch(() => {});
      }).catch((e) => { toast(`載入失敗：${e.message}`, "danger"); nav("/reports"); });
    } else {
      const initial = (sp.get("outputs") ?? "").split(",").filter(Boolean);
      setPaths(initial);
      if (initial.length) {
        api.post<{ body_md: string }>("/api/reports/template", { output_paths: initial }).then((r) => setBody(r.body_md)).catch(() => {});
        setTitle(`${initial.join(" / ")} 測試案例審閱報告`);
      }
    }
  }, [id, sp, nav, toast]);

  const dirty = !saved || saved.title !== title || saved.summary !== summary || saved.body_md !== body || saved.output_paths.join() !== paths.join();

  const save = async () => {
    if (!title.trim()) { toast("標題必填", "danger"); return; }
    setBusy(true);
    try {
      const payload = { title: title.trim(), summary, body_md: body, output_paths: paths };
      if (isNew && !saved) {
        const r = await api.post<Report>("/api/reports", payload);
        setSaved(r); refreshNav(); toast("報告已建立", "ok");
        nav(`/reports/${r.id}`, { replace: true });
      } else {
        const r = await api.patch<Report>(`/api/reports/${saved!.id}`, payload);
        setSaved(r); toast("已儲存", "ok");
      }
    } catch (e) { toast(`儲存失敗：${(e as Error).message}`, "danger"); }
    finally { setBusy(false); }
  };

  const showPreview = async () => {
    setMode("preview");
    try { const r = await api.post<{ html: string }>("/api/reports/preview", { body_md: body }); setPreviewHtml(r.html); }
    catch { setPreviewHtml("<p>預覽失敗</p>"); }
  };

  const regenerate = async () => {
    if (!saved) return;
    try {
      const r = await api.post<Report>(`/api/reports/${saved.id}/regenerate`);
      setSaved(r);
      if (r.auto_md) { const x = await api.post<{ html: string }>("/api/reports/preview", { body_md: r.auto_md }); setAutoHtml(x.html); }
      toast("自動段落已重新產生", "ok");
    } catch (e) { toast(`重新產生失敗：${(e as Error).message}`, "danger"); }
  };

  const insertTemplate = async () => {
    if (!paths.length) { toast("先選擇引用的產出", "danger"); return; }
    const r = await api.post<{ body_md: string }>("/api/reports/template", { output_paths: paths });
    setBody((b) => (b.trim() ? b + "\n\n" + r.body_md : r.body_md));
    setMode("edit");
  };

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if ((e.metaKey || e.ctrlKey) && e.key === "s") { e.preventDefault(); if (dirty && !busy) save(); } };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  const byKey = new Map(outputs.map((o) => [o.key, o]));

  return (
    <>
      <PageHeader
        eyebrow="Work · Report"
        title={saved ? `#${saved.id} ${saved.title}` : "新報告"}
        description={saved ? `建立 ${fmtDate(saved.created_at)} · 更新 ${fmtDate(saved.updated_at)}` : "填寫標題、摘要與內文（Markdown），並勾選引用的產出。"}
        actions={
          <>
            <button className="btn ghost" onClick={() => nav("/reports")}><ArrowLeft className="ic" aria-hidden="true" />列表</button>
            {saved && <a className="btn" href={`/api/reports/${saved.id}/export?format=md`}>匯出 MD</a>}
            {saved && <a className="btn" href={`/api/reports/${saved.id}/export?format=html`}>匯出 HTML</a>}
            <button className="btn primary" disabled={!dirty || busy} onClick={save}>儲存 <span className="kbd">⌘S</span></button>
          </>
        }
      />
      <div className="page-body">
        <div className="report-grid">
          <div className="stack" style={{ gap: 14 }}>
            <div className="field">
              <label>標題<span className="req">*</span></label>
              <input className="input" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="例如：MEMBER 測試案例審閱報告" />
            </div>
            <div className="field">
              <label>摘要</label>
              <textarea className="textarea" style={{ minHeight: 70 }} value={summary} onChange={(e) => setSummary(e.target.value)} placeholder="一兩句話的結論" />
            </div>
            {saved && saved.kind !== "manual" && (
              <div className="panel auto-section">
                <div className="row" style={{ justifyContent: "space-between" }}>
                  <div className="row">
                    <span className={`tag ${saved.kind === "output" ? "cyan" : "violet"}`}>{saved.kind === "output" ? "產出" : "自動化測試"}</span>
                    <span className="section-title" style={{ margin: 0 }}>系統自動段落 · {fmtDate(saved.auto_generated_at)}</span>
                  </div>
                  <div className="row">
                    <button className="btn ghost sm" onClick={regenerate}>重新產生</button>
                    <button className="btn ghost sm" onClick={() => setAutoOpen(!autoOpen)}>{autoOpen ? "收合" : "展開"}</button>
                  </div>
                </div>
                {autoOpen && <div className="md-preview" style={{ marginTop: 10, minHeight: 0 }} dangerouslySetInnerHTML={{ __html: autoHtml || "<p class='faint'>載入中…</p>" }} />}
                <div className="faint" style={{ fontSize: 12, marginTop: 6 }}>此段由產出檔、run.yaml、approvals 與 hook 事件自動產生；來源更新時會自動重生，不會覆蓋你在下方寫的結論。</div>
              </div>
            )}
            <div className="field">
              <div className="row" style={{ justifyContent: "space-between" }}>
                <label>{saved && saved.kind !== "manual" ? "結論與備註（Markdown，你寫的部分）" : "內文（Markdown）"}</label>
                <div className="row">
                  <button className={`btn sm ${mode === "edit" ? "" : "ghost"}`} onClick={() => setMode("edit")}>編輯</button>
                  <button className={`btn sm ${mode === "preview" ? "" : "ghost"}`} onClick={showPreview}>預覽</button>
                  <button className="btn ghost sm" onClick={insertTemplate}>插入產出摘要</button>
                </div>
              </div>
              {mode === "edit" ? (
                <textarea className="textarea mono" style={{ minHeight: 420, fontSize: 12.5 }} value={body} onChange={(e) => setBody(e.target.value)} placeholder="## 摘要&#10;&#10;…" />
              ) : (
                <div className="md-preview" dangerouslySetInnerHTML={{ __html: previewHtml }} />
              )}
            </div>
          </div>
          <aside className="stack" style={{ gap: 12 }}>
            <div className="panel">
              <div className="row" style={{ justifyContent: "space-between", marginBottom: 8 }}>
                <div className="section-title" style={{ margin: 0 }}>引用產出 · {paths.length}</div>
                <button className="btn sm" onClick={() => setPickOpen(true)}>選擇</button>
              </div>
              {paths.length === 0 ? <div className="faint" style={{ fontSize: 12 }}>尚未引用任何產出</div> : (
                <div className="stack" style={{ gap: 6 }}>
                  {paths.map((p) => {
                    const o = byKey.get(p);
                    return (
                      <div key={p} className="ref-row">
                        <div>
                          <div style={{ fontWeight: 600 }}>{p}</div>
                          <div className="faint" style={{ fontSize: 12 }}>{o ? `${o.kinds.map((k) => k.toUpperCase()).join("+")} · ${o.meta.case_count ?? "—"} cases · ${fmtDate(o.modified_at)}` : "（產出目前不存在）"}</div>
                        </div>
                        <button className="btn ghost sm" onClick={() => setPaths(paths.filter((x) => x !== p))}>移除</button>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
            <div className="panel faint" style={{ fontSize: 12 }}>
              匯出的 Markdown / HTML 會自動附上引用產出的表格（模組、檔案、案例數、產生時間、審閱狀態）。
            </div>
          </aside>
        </div>
      </div>
      <Drawer open={pickOpen} onClose={() => setPickOpen(false)} title="選擇引用產出" subtitle="testcases/final/" footer={<><span className="faint">{paths.length} 已選</span><button className="btn primary" onClick={() => setPickOpen(false)}>完成</button></>}>
        {outputs.map((o) => (
          <label key={o.key} className="pick-row">
            <input type="checkbox" checked={paths.includes(o.key)} onChange={(e) => setPaths(e.target.checked ? [...paths, o.key] : paths.filter((x) => x !== o.key))} />
            <div>
              <div style={{ fontWeight: 600 }}>{o.label}</div>
              <div className="faint" style={{ fontSize: 12 }}>{o.kinds.map((k) => k.toUpperCase()).join("+")} · {o.meta.case_count ?? "—"} cases · {fmtDate(o.modified_at)}</div>
            </div>
          </label>
        ))}
      </Drawer>
    </>
  );
}
