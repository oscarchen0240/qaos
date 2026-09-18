import { useEffect, useState } from "react";
import { EmptyState } from "@/components/PageHeader";
import { useToast } from "@/components/Toast";
import { useConfirm } from "@/components/Confirm";
import { api, type Folder, type OutputGroup } from "@/lib/api";
import { clickable } from "@/lib/a11y";
import { fmtDate } from "@/lib/format";
import { FolderSimple, Trash, PencilSimple } from "@phosphor-icons/react";

export function FoldersView({ folders, groups, onChanged, onOpenGroup, initialFolder = null }: { folders: Folder[]; groups: OutputGroup[]; onChanged: () => void; onOpenGroup: (key: string) => void; initialFolder?: number | null }) {
  const [open, setOpen] = useState<number | null>(initialFolder ?? folders[0]?.id ?? null);
  useEffect(() => { if (initialFolder != null) setOpen(initialFolder); }, [initialFolder]);
  const [editing, setEditing] = useState<number | null>(null);
  const [name, setName] = useState("");
  const { toast } = useToast();
  const confirm = useConfirm();
  const cur = folders.find((f) => f.id === open) ?? null;
  const byKey = new Map(groups.map((g) => [g.key, g]));

  const remove = async (f: Folder) => {
    if (!(await confirm({ title: "刪除資料夾？", message: `「${f.name}」內的 ${f.count} 條歸檔會一起移除（TC 本身不受影響）`, confirmText: "刪除", danger: true }))) return;
    await api.del(`/api/folders/${f.id}`); toast("已刪除"); onChanged(); if (open === f.id) setOpen(null);
  };
  const rename = async (f: Folder) => {
    if (!name.trim()) return;
    await api.patch(`/api/folders/${f.id}`, { name: name.trim() }); setEditing(null); toast("已更名", "ok"); onChanged();
  };
  const removeItem = async (f: Folder, it: { group_key: string; testcase_id: string }) => {
    await fetch(`/api/folders/${f.id}/items`, { method: "DELETE", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ items: [it] }) });
    onChanged();
  };

  if (folders.length === 0) return <EmptyState title="還沒有資料夾">在「全部」分頁勾選模組、或在預覽面板勾選 TC，按「加入資料夾」即可建立。</EmptyState>;

  return (
    <div className="folders-grid">
      <aside className="stack" style={{ gap: 4 }}>
        {folders.map((f) => (
          <div key={f.id} className={`folder-row ${open === f.id ? "active" : ""}`} {...clickable(() => setOpen(f.id), `開啟資料夾 ${f.name}`)}>
            <FolderSimple className="ic" aria-hidden="true" />
            {editing === f.id ? (
              <input className="input" style={{ padding: "2px 6px" }} autoFocus value={name} onChange={(e) => setName(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") rename(f); if (e.key === "Escape") setEditing(null); }} onClick={(e) => e.stopPropagation()} />
            ) : <span style={{ flex: 1 }}>{f.name}</span>}
            <span className="tag">{f.count}</span>
          </div>
        ))}
      </aside>
      <section className="panel" style={{ minWidth: 0 }}>
        {!cur ? <div className="faint">選一個資料夾</div> : (
          <>
            <div className="row" style={{ justifyContent: "space-between", marginBottom: 10 }}>
              <div>
                <div style={{ fontWeight: 600, fontSize: 16 }}>{cur.name}</div>
                <div className="faint" style={{ fontSize: 12 }}>{cur.description || "—"} · 建立 {fmtDate(cur.created_at)} · {cur.count} 條 TC</div>
              </div>
              <div className="row">
                <button className="btn ghost sm" onClick={() => { setEditing(cur.id); setName(cur.name); }}><PencilSimple className="ic sm" aria-hidden="true" />更名</button>
                <button className="btn ghost sm" style={{ color: "var(--danger)" }} onClick={() => remove(cur)}><Trash className="ic sm" aria-hidden="true" />刪除</button>
              </div>
            </div>
            {cur.items.length === 0 ? <div className="faint">空的</div> : (
              <table className="table">
                <thead><tr><th>模組</th><th>TC</th><th>加入時間</th><th></th></tr></thead>
                <tbody>
                  {cur.items.map((it) => (
                    <tr key={`${it.group_key}:${it.testcase_id}`}>
                      <td><button className="link-btn" onClick={() => onOpenGroup(it.group_key)}>{byKey.get(it.group_key)?.label ?? it.group_key}</button></td>
                      <td className="mono">{it.testcase_id}</td>
                      <td className="mono faint">{fmtDate(it.added_at)}</td>
                      <td><button className="btn ghost sm" onClick={() => removeItem(cur, it)}>移出</button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </>
        )}
      </section>
    </div>
  );
}
