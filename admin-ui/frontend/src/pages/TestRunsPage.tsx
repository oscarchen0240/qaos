import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { PageHeader, Tabs, EmptyState } from "@/components/PageHeader";
import { Drawer } from "@/components/Drawer";
import { useToast } from "@/components/Toast";
import { useConfirm } from "@/components/Confirm";
import { refreshNav } from "@/lib/nav";
import { clickable } from "@/lib/a11y";
import { api, type Folder, type OutputContent, type OutputGroup, type TestRun } from "@/lib/api";
import { fmtDate } from "@/lib/format";
import { Donut, ProgressBar } from "./testruns/Donut";
import { Plus, Trash } from "@phosphor-icons/react";

const ST_LABEL: Record<string, string> = { planned: "未開始", running: "進行中", done: "已完成", aborted: "已中止" };
const ST_CLASS: Record<string, string> = { planned: "", running: "accent", done: "ok", aborted: "danger" };

export function TestRunsPage() {
  const [runs, setRuns] = useState<TestRun[]>([]);
  const [tab, setTab] = useState<"open" | "done">("open");
  const [creating, setCreating] = useState(false);
  const { toast } = useToast();
  const confirm = useConfirm();
  const nav = useNavigate();
  const load = useCallback(() => api.get<TestRun[]>("/api/testruns").then(setRuns).catch((e) => toast(`載入失敗：${e.message}`, "danger")), [toast]);
  useEffect(() => { load(); const id = setInterval(load, 15000); return () => clearInterval(id); }, [load]);
  const open = runs.filter((r) => r.status === "planned" || r.status === "running");
  const done = runs.filter((r) => r.status === "done" || r.status === "aborted");
  const shown = tab === "open" ? open : done;
  const remove = async (r: TestRun) => {
    if (!(await confirm({ title: `刪除回合 #${r.id}？`, message: `「${r.name}」的 ${r.counts.total} 條結果、證據檔與測試報告會一起刪除。`, confirmText: "刪除", danger: true }))) return;
    await api.del(`/api/testruns/${r.id}`); toast("已刪除"); load(); refreshNav();
  };
  return (
    <>
      <PageHeader eyebrow="Work" title="測試執行" description="用產出的 TC 開一輪測試，逐條記 Pass / Fail / Blocked，附證據；結束後自動產一份測試報告。NG 可送 QAOS 開 bug。"
        actions={<button className="btn primary" onClick={() => setCreating(true)}><Plus className="ic sm" aria-hidden="true" />新回合</button>} />
      <Tabs tabs={[{ key: "open", label: "進行中", count: open.length }, { key: "done", label: "已結束", count: done.length }]} active={tab} onChange={(k) => setTab(k as typeof tab)} />
      <div className="page-body">
        {shown.length === 0 ? (
          <EmptyState title={tab === "open" ? "沒有進行中的回合" : "還沒有結束的回合"} action={tab === "open" ? <button className="btn primary" onClick={() => setCreating(true)}>建立第一輪</button> : undefined}>
            {tab === "open" ? "從產出或資料夾挑 TC，建立一輪測試。" : ""}
          </EmptyState>
        ) : (
          <div className="run-grid">
            {shown.map((r) => (
              <div key={r.id} className="run-card" {...clickable(() => nav(`/testruns/${r.id}`), `開啟回合 ${r.name}`)}>
                <Donut counts={r.counts} size={88} stroke={10} />
                <div className="run-card-body">
                  <div className="row" style={{ gap: 8 }}>
                    <span className="mono faint">#{r.id}</span>
                    <span style={{ fontWeight: 600, fontSize: 14 }}>{r.name}</span>
                    <span className={`tag ${ST_CLASS[r.status]}`}>{ST_LABEL[r.status]}</span>
                  </div>
                  <div className="faint" style={{ fontSize: 12 }}>{r.environment || "—"} · {r.build || "—"} · {r.counts.total} 條 · 建立 {fmtDate(r.created_at)}{r.ended_at ? ` · 結束 ${fmtDate(r.ended_at)}` : ""}</div>
                  <ProgressBar counts={r.counts} />
                  <div className="row" style={{ gap: 10, fontSize: 12 }}>
                    <span style={{ color: "var(--ok)" }}>Pass {r.counts.pass}</span><span style={{ color: "var(--danger)" }}>Fail {r.counts.fail}</span><span style={{ color: "var(--warn)" }}>Blocked {r.counts.blocked}</span><span className="faint">Untested {r.counts.untested}</span>
                    <span className="faint mono" style={{ marginLeft: "auto" }}>{r.counts.done} / {r.counts.total}</span>
                  </div>
                </div>
                <button className="btn ghost sm" style={{ color: "var(--danger)" }} onClick={(e) => { e.stopPropagation(); remove(r); }} aria-label="刪除回合"><Trash className="ic sm" aria-hidden="true" /></button>
              </div>
            ))}
          </div>
        )}
      </div>
      <CreateRunDrawer open={creating} onClose={() => setCreating(false)} onCreated={(r) => { setCreating(false); load(); refreshNav(); nav(`/testruns/${r.id}`); }} />
    </>
  );
}

/** 建立回合：名稱／環境／build，從產出模組或資料夾挑 TC */
function CreateRunDrawer({ open, onClose, onCreated }: { open: boolean; onClose: () => void; onCreated: (r: TestRun) => void }) {
  const [name, setName] = useState("");
  const [env, setEnv] = useState("");
  const [build, setBuild] = useState("");
  const [notes, setNotes] = useState("");
  const [groups, setGroups] = useState<OutputGroup[]>([]);
  const [folders, setFolders] = useState<Folder[]>([]);
  const [source, setSource] = useState<"group" | "folder">("group");
  const [gkey, setGkey] = useState("");
  const [cases, setCases] = useState<{ testcase_id: string; title: string; priority: string }[]>([]);
  const [q, setQ] = useState("");
  const [picked, setPicked] = useState<Map<string, { group_key: string; testcase_id: string; title: string }>>(new Map());
  const [busy, setBusy] = useState(false);
  const { toast } = useToast();
  useEffect(() => {
    if (!open) return;
    api.get<OutputGroup[]>("/api/outputs").then((xs) => { setGroups(xs); if (!gkey && xs[0]) setGkey(xs[0].key); }).catch(() => {});
    api.get<Folder[]>("/api/folders").then(setFolders).catch(() => {});
  }, [open]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    const g = groups.find((x) => x.key === gkey); const f = g?.files.find((x) => x.kind === "json");
    if (!f) { setCases([]); return; }
    api.get<OutputContent>(`/api/outputs/content?path=${encodeURIComponent(f.path)}`).then((c) => setCases(c.kind === "json" ? c.cases.map((x) => ({ testcase_id: x.testcase_id, title: x.title, priority: x.priority })) : [])).catch(() => setCases([]));
  }, [gkey, groups]);
  const ql = q.trim().toLowerCase();
  const shownCases = useMemo(() => cases.filter((c) => !ql || `${c.testcase_id} ${c.title}`.toLowerCase().includes(ql)), [cases, ql]);
  const keyOf = (g: string, t: string) => `${g}:${t}`;
  const togglePick = (g: string, t: string, title: string) => setPicked((m) => { const n = new Map(m); const k = keyOf(g, t); n.has(k) ? n.delete(k) : n.set(k, { group_key: g, testcase_id: t, title }); return n; });
  const pickAll = (on: boolean) => setPicked((m) => { const n = new Map(m); for (const c of shownCases) { const k = keyOf(gkey, c.testcase_id); on ? n.set(k, { group_key: gkey, testcase_id: c.testcase_id, title: c.title }) : n.delete(k); } return n; });
  const pickFolder = (f: Folder) => setPicked((m) => { const n = new Map(m); for (const it of f.items) n.set(keyOf(it.group_key, it.testcase_id), { group_key: it.group_key, testcase_id: it.testcase_id, title: "" }); return n; });
  const create = async () => {
    setBusy(true);
    try {
      const r = await api.post<TestRun>("/api/testruns", { name, environment: env, build, notes, items: Array.from(picked.values()).map(({ group_key, testcase_id }) => ({ group_key, testcase_id })) });
      toast(`已建立回合 #${r.id}，${r.counts.total} 條 TC${r.missing?.length ? `（${r.missing.length} 條找不到已略過）` : ""}`, "ok");
      setName(""); setEnv(""); setBuild(""); setNotes(""); setPicked(new Map());
      onCreated(r);
    } catch (e) { toast(`建立失敗：${(e as Error).message}`, "danger"); }
    finally { setBusy(false); }
  };
  const byGroup = useMemo(() => { const m = new Map<string, number>(); for (const v of picked.values()) m.set(v.group_key, (m.get(v.group_key) ?? 0) + 1); return m; }, [picked]);
  return (
    <Drawer open={open} onClose={onClose} wide title="新測試回合" subtitle="挑 TC 時會把目前 final 的版本快照進回合"
      footer={<><span className="faint" style={{ fontSize: 12 }}>已挑 {picked.size} 條{byGroup.size ? `（${Array.from(byGroup.entries()).map(([g, n]) => `${g} ${n}`).join("、")}）` : ""}</span><div className="row"><button className="btn ghost" onClick={onClose}>取消</button><button className="btn primary" disabled={busy || !name.trim() || picked.size === 0} onClick={create}>建立回合</button></div></>}>
      <div className="form-grid">
        <div className="field span2"><label>回合名稱<span className="req">*</span></label><input className="input" value={name} onChange={(e) => setName(e.target.value)} placeholder="例如：CASHOUT 出金 回歸 第 1 輪" autoFocus /></div>
        <div className="field"><label>環境</label><input className="input" value={env} onChange={(e) => setEnv(e.target.value)} placeholder="stage / uat / prod" /></div>
        <div className="field"><label>Build</label><input className="input" value={build} onChange={(e) => setBuild(e.target.value)} placeholder="版本或 commit" /></div>
        <div className="field span2"><label>備註</label><textarea className="textarea" style={{ minHeight: 56 }} value={notes} onChange={(e) => setNotes(e.target.value)} /></div>
      </div>
      <div className="section-title" style={{ marginTop: 16 }}>挑 TC</div>
      <div className="row" style={{ gap: 4, marginBottom: 8 }}>
        <div className="seg"><button className={`seg-btn ${source === "group" ? "on" : ""}`} onClick={() => setSource("group")}>從產出模組</button><button className={`seg-btn ${source === "folder" ? "on" : ""}`} onClick={() => setSource("folder")}>從資料夾</button></div>
      </div>
      {source === "group" ? (
        <div className="stack">
          <div className="row">
            <select className="select" value={gkey} onChange={(e) => setGkey(e.target.value)} style={{ maxWidth: 260 }}>{groups.map((g) => <option key={g.key} value={g.key}>{g.label}（{g.meta.case_count ?? "?"}）</option>)}</select>
            <input className="input" placeholder="搜尋 ID / 標題" value={q} onChange={(e) => setQ(e.target.value)} />
            <button className="btn ghost sm" onClick={() => pickAll(true)}>全選</button><button className="btn ghost sm" onClick={() => pickAll(false)}>清除</button>
          </div>
          <div className="pick-list">
            {shownCases.map((c) => { const on = picked.has(keyOf(gkey, c.testcase_id)); return (
              <label key={c.testcase_id} className={`pick-row ${on ? "on" : ""}`}><input type="checkbox" checked={on} onChange={() => togglePick(gkey, c.testcase_id, c.title)} /><span className="mono accent-text">{c.testcase_id}</span><span className="pick-title">{c.title}</span><span className={`tag ${c.priority === "high" ? "danger" : c.priority === "medium" ? "warn" : ""}`}>{c.priority}</span></label>
            ); })}
            {shownCases.length === 0 && <div className="faint" style={{ padding: 12 }}>這個模組沒有可挑的 TC</div>}
          </div>
        </div>
      ) : (
        <div className="stack">
          {folders.length === 0 && <div className="faint">還沒有資料夾</div>}
          {folders.map((f) => <div key={f.id} className="row" style={{ justifyContent: "space-between" }}><span>{f.name} <span className="faint">· {f.count} 條</span></span><button className="btn sm" onClick={() => pickFolder(f)}>全部加入</button></div>)}
        </div>
      )}
    </Drawer>
  );
}
