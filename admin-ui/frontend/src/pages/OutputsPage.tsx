import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { PageHeader, Tabs, EmptyState } from "@/components/PageHeader";
import { useToast } from "@/components/Toast";
import { refreshNav } from "@/lib/nav";
import { api, type CaseFilter, type Folder, type OutputGroup, type ReviewStatus } from "@/lib/api";
import { FoldersView } from "./outputs/FoldersView";
import { fmtBytes, fmtDate } from "@/lib/format";
import { clickable } from "@/lib/a11y";
import { REVIEW_CLASS, REVIEW_LABEL } from "@/lib/review";
import { OutputPreview } from "./outputs/OutputPreview";
import { FolderPicker } from "./outputs/FolderPicker";

type SortKey = "mtime" | "label" | "cases";
const PRIO_CLASS: Record<string, string> = { critical: "danger", high: "danger", medium: "warn", low: "" };

export function OutputsPage() {
  const [groups, setGroups] = useState<OutputGroup[]>([]);
  const [params, setParams] = useSearchParams();
  const tab = (params.get("tab") as "all" | ReviewStatus | "folders" | null) ?? "all";
  const setTab = (t: string) => setParams((p) => { const n = new URLSearchParams(p); if (t === "all") n.delete("tab"); else n.set("tab", t); n.delete("folder"); return n; }, { replace: true });
  const urlFolder = params.get("folder") ? Number(params.get("folder")) : null;
  const urlGroup = params.get("group");
  const urlTc = params.get("tc");
  const [q, setQ] = useState("");
  const [sort, setSort] = useState<SortKey>("mtime");
  const [desc, setDesc] = useState(true);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [previewKey, setPreviewKey] = useState<string | null>(null);
  const [previewFilter, setPreviewFilter] = useState<CaseFilter | null>(null);
  const known = useRef<Set<string> | null>(null);
  const [folders, setFolders] = useState<Folder[]>([]);
  const { toast } = useToast();

  const load = useCallback(async (silent = false) => {
    try {
      const xs = await api.get<OutputGroup[]>("/api/outputs");
      setGroups(xs);
      if (known.current) {
        const fresh = xs.filter((x) => !known.current!.has(x.key) || x.changed_now);
        if (fresh.length && !silent) toast(`偵測到新產出：${fresh.map((f) => f.label).join("、")}`, "ok");
      }
      known.current = new Set(xs.map((x) => x.key));
      api.get<Folder[]>("/api/folders").then(setFolders).catch(() => {});
      refreshNav();
    } catch (e) { toast(`掃描失敗：${(e as Error).message}`, "danger"); }
  }, [toast]);

  useEffect(() => {
    load(true);
    const id = setInterval(() => load(false), 10000);
    return () => clearInterval(id);
  }, [load]);

  const counts = useMemo(() => ({
    all: groups.length,
    pending: groups.filter((g) => g.review_status === "pending").length,
    reviewed: groups.filter((g) => g.review_status === "reviewed").length,
    returned: groups.filter((g) => g.review_status === "returned").length,
  }), [groups]);

  const shown = useMemo(() => {
    const ql = q.trim().toLowerCase();
    const hay = (g: OutputGroup) => [g.label, g.note, ...(g.meta.specs ?? []), ...g.files.map((f) => f.name)].join(" ").toLowerCase();
    let xs = groups.filter((g) => (tab === "all" || tab === "folders" || g.review_status === tab) && (!ql || hay(g).includes(ql)));
    const key = (g: OutputGroup) => sort === "mtime" ? g.mtime : sort === "label" ? g.label : (g.meta.case_count ?? -1);
    xs = [...xs].sort((a, b) => { const ka = key(a), kb = key(b); return (ka < kb ? -1 : ka > kb ? 1 : 0) * (desc ? -1 : 1); });
    return xs;
  }, [groups, tab, q, sort, desc]);

  const toggleSel = (k: string) => setSelected((s) => { const n = new Set(s); n.has(k) ? n.delete(k) : n.add(k); return n; });
  const allShownSelected = shown.length > 0 && shown.every((g) => selected.has(g.key));

  const openPreview = async (g: OutputGroup, filter: CaseFilter | null = null) => {
    setPreviewFilter(filter);
    setPreviewKey(g.key);
    if (g.unread) {
      await api.post("/api/outputs/ack", { keys: [g.key] }).catch(() => {});
      setGroups((xs) => xs.map((x) => x.key === g.key ? { ...x, unread: false, files: x.files.map((f) => ({ ...f, unread: false })) } : x));
      refreshNav();
    }
  };

  const ackAll = async () => { await api.post("/api/outputs/ack", {}); load(true); toast("已全部標為已讀"); };

  const setSort2 = (k: SortKey) => { if (sort === k) setDesc(!desc); else { setSort(k); setDesc(k !== "label"); } };
  const th = (k: SortKey, label: string) => (
    <th onClick={() => setSort2(k)} style={{ cursor: "pointer", userSelect: "none" }}>{label}{sort === k ? (desc ? " ↓" : " ↑") : ""}</th>
  );

  // 側邊欄樹深連結：?group=<key>&tc=<id> → 開預覽並捲到該 TC
  const openedFromUrl = useRef<string | null>(null);
  useEffect(() => {
    if (!urlGroup || groups.length === 0) return;
    const sig = `${urlGroup}|${urlTc ?? ""}`;
    if (openedFromUrl.current === sig) return;
    const g = groups.find((x) => x.key === urlGroup);
    if (!g) return;
    openedFromUrl.current = sig;
    openPreview(g);
  }, [urlGroup, urlTc, groups]); // eslint-disable-line react-hooks/exhaustive-deps
  const closePreview = () => {
    setPreviewKey(null); setPreviewFilter(null); openedFromUrl.current = null;
    if (urlGroup) setParams((p) => { const n = new URLSearchParams(p); n.delete("group"); n.delete("tc"); return n; }, { replace: true });
  };

  const preview = previewKey ? groups.find((g) => g.key === previewKey) ?? null : null;
  const [folderPickFor, setFolderPickFor] = useState<{ group_key: string; testcase_id: string }[] | null>(null);
  const reloadFolders = () => api.get<Folder[]>("/api/folders").then(setFolders).catch(() => {});

  return (
    <>
      <PageHeader
        eyebrow="Monitor"
        title="產出"
        description="testcases/final/ 的唯讀清單；同一模組的 JSON / HTML 視為一份產出，共用審閱狀態與備註（存在管理系統，不改原檔）。"
        actions={
          <>
            {groups.some((g) => g.unread) && <button className="btn" onClick={ackAll}>全部標為已讀</button>}
            <button className="btn" onClick={() => load(false)}>重新掃描</button>
            <button className="btn primary" disabled={selected.size === 0} title="把勾選模組的全部 TC 加進資料夾" onClick={() => setFolderPickFor(Array.from(selected).flatMap((k) => (groups.find((g) => g.key === k)?.meta.case_ids ?? []).map((t) => ({ group_key: k, testcase_id: t }))))}>
              加入資料夾{selected.size > 0 ? `（${selected.size} 模組）` : ""}
            </button>
          </>
        }
      />
      <Tabs
        tabs={[{ key: "all", label: "全部", count: counts.all }, { key: "pending", label: "待審", count: counts.pending }, { key: "reviewed", label: "已審", count: counts.reviewed }, { key: "returned", label: "退回", count: counts.returned }, { key: "folders", label: "資料夾", count: folders.length }]}
        active={tab}
        onChange={(k) => setTab(k as typeof tab)}
      />
      <div className="page-body">
        {tab === "folders" ? (
          <FoldersView folders={folders} groups={groups} onChanged={reloadFolders} initialFolder={urlFolder} onOpenGroup={(k) => { const g = groups.find((x) => x.key === k); if (g) openPreview(g); }} />
        ) : (<>
        <div className="toolbar">
          <input className="input" style={{ maxWidth: 320 }} placeholder="搜尋模組、檔名、spec、備註…" value={q} onChange={(e) => setQ(e.target.value)} />
          <div className="grow" />
          <span className="faint mono">{shown.length} / {groups.length}</span>
        </div>
        {groups.length === 0 ? (
          <EmptyState title="testcases/final/ 目前沒有檔案">當 pipeline 匯出 final 產出時會自動出現在這裡。</EmptyState>
        ) : shown.length === 0 ? (
          <EmptyState title="沒有符合條件的產出" />
        ) : (
          <table className="table outputs-table">
            <thead>
              <tr>
                <th style={{ width: 28 }}><input type="checkbox" checked={allShownSelected} onChange={() => setSelected(allShownSelected ? new Set() : new Set(shown.map((g) => g.key)))} /></th>
                {th("label", "模組")}
                <th style={{ width: 120 }}>檔案</th>
                {th("cases", "案例數")}
                <th style={{ minWidth: 300 }}>摘要（點標籤可篩選）</th>
                {th("mtime", "產生時間")}
                <th style={{ width: 150 }}>審閱</th>
                <th>備註</th>
              </tr>
            </thead>
            <tbody>
              {shown.map((g) => (
                <tr key={g.key} className="clickable" {...clickable(() => openPreview(g), `預覽 ${g.label}`)}>
                  <td onClick={(e) => e.stopPropagation()}><input type="checkbox" checked={selected.has(g.key)} onChange={() => toggleSel(g.key)} /></td>
                  <td className="col-module">
                    <div className="row" style={{ whiteSpace: "nowrap" }}>
                      {g.unread && <span className="tag accent">NEW</span>}
                      <span style={{ fontWeight: 600 }}>{g.label}</span>
                      {g.meta.drift?.stale && <span className="tag warn" title={`registry 已變動但 final 尚未重新匯出：新增 ${g.meta.drift.added.length}、新版 ${g.meta.drift.newer.length}、退役 ${g.meta.drift.retired.length}`}>final 已過期</span>}
                    </div>
                    {g.meta.specs && <div className="faint mono" style={{ fontSize: 12, whiteSpace: "nowrap" }}>{g.meta.specs.join(", ")}</div>}
                  </td>
                  <td>
                    <div className="row" style={{ gap: 4, whiteSpace: "nowrap" }}>
                      {g.files.map((f) => (
                        <span key={f.path} className={`tag ${f.kind === "json" ? "cyan" : "violet"} ${f.unread ? "has-dot" : ""}`} title={`${f.path} · ${fmtBytes(f.size)}${f.unread ? " · 未讀" : ""}`}>
                          {f.kind.toUpperCase()}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="mono">{g.meta.case_count ?? "—"}</td>
                  <td className="muted" style={{ fontSize: 12 }} onClick={(e) => e.stopPropagation()}>
                    {g.meta.parse_error ? <span className="tag danger">解析失敗</span> : (
                      <div className="card-tags">
                        {(["critical", "high", "medium", "low"] as const).filter((k) => g.meta.priority?.[k]).map((k) => (
                          <button key={k} className={`tag chip ${PRIO_CLASS[k]}`} title={`只看 priority=${k} 的 TC`} onClick={() => openPreview(g, { priority: k })}>{k} {g.meta.priority![k]}</button>
                        ))}
                        {g.meta.exploratory ? <button className="tag chip warn" title="只看有假設（exploratory）的 TC" onClick={() => openPreview(g, { kind: "exploratory" })}>exploratory {g.meta.exploratory}</button> : null}
                        {g.meta.revised ? <button className="tag chip" title="只看修訂過（v2 以上）的 TC" onClick={() => openPreview(g, { kind: "revised" })}>revised {g.meta.revised}</button> : null}
                      </div>
                    )}
                  </td>
                  <td className="mono">{fmtDate(g.modified_at)}</td>
                  <td>
                    <span className={`tag ${REVIEW_CLASS[g.review_status]}`}>{REVIEW_LABEL[g.review_status]}</span>
                    {g.tc_summary.total > 0 && (
                      <div className="faint mono" style={{ fontSize: 12, marginTop: 4, whiteSpace: "nowrap" }}>
                        待 {g.tc_summary.pending.length} · 審 {g.tc_summary.reviewed} · 退 {g.tc_summary.returned.length}
                      </div>
                    )}
                  </td>
                  <td className="muted" style={{ maxWidth: 220, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{g.note}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        </>)}
      </div>
      <FolderPicker folders={folders} items={folderPickFor} onClose={() => setFolderPickFor(null)} onDone={() => { setFolderPickFor(null); setSelected(new Set()); reloadFolders(); }} />
      <OutputPreview
        group={preview}
        initialFilter={previewFilter}
        onClose={closePreview}
        focusTc={previewKey && previewKey === urlGroup ? urlTc : null}
        onSaved={(g) => { setGroups((xs) => xs.map((x) => x.key === g.key ? { ...x, ...g, unread: x.unread, files: x.files } : x)); refreshNav(); }}
        folders={folders}
        onFoldersChanged={reloadFolders}
      />
    </>
  );
}
