import { useEffect, useState } from "react";
import { Drawer } from "@/components/Drawer";
import { useToast } from "@/components/Toast";
import { api, type Folder } from "@/lib/api";

interface Item { group_key: string; testcase_id: string }

/** 把一批 TC 加進既有資料夾，或建新資料夾 */
export function FolderPicker({ folders, items, onClose, onDone }: { folders: Folder[]; items: Item[] | null; onClose: () => void; onDone: () => void }) {
  const [target, setTarget] = useState<number | "new">(folders[0]?.id ?? "new");
  const [name, setName] = useState("");
  const [desc, setDesc] = useState("");
  const [busy, setBusy] = useState(false);
  const { toast } = useToast();
  // 只在面板開啟（items 改變）時重設；folders 每次輪詢都是新陣列，不能當依賴
  useEffect(() => { if (items) { setTarget(folders[0]?.id ?? "new"); setName(""); setDesc(""); } }, [items]); // eslint-disable-line react-hooks/exhaustive-deps

  const submit = async () => {
    if (!items?.length) return;
    setBusy(true);
    try {
      let fid = target;
      if (fid === "new") {
        if (!name.trim()) { toast("資料夾名稱必填", "danger"); setBusy(false); return; }
        const f = await api.post<Folder>("/api/folders", { name: name.trim(), description: desc });
        fid = f.id;
      }
      const f = await api.post<Folder>(`/api/folders/${fid}/items`, { items });
      toast(`已加入「${f.name}」，共 ${f.count} 條`, "ok");
      onDone();
    } catch (e) { toast(`加入失敗：${(e as Error).message}`, "danger"); }
    finally { setBusy(false); }
  };

  const groupsCount = new Set((items ?? []).map((i) => i.group_key)).size;
  return (
    <Drawer open={!!items} onClose={onClose} title="加入資料夾" subtitle={items ? `${items.length} 條 TC · 來自 ${groupsCount} 個模組` : ""}
      footer={<><span className="faint" style={{ fontSize: 12 }}>資料夾只是管理系統的歸檔，不動 testcases/</span><div className="row"><button className="btn ghost" onClick={onClose}>取消</button><button className="btn primary" disabled={busy} onClick={submit}>加入</button></div></>}>
      <div className="field">
        <label>目標資料夾</label>
        <select className="select" value={String(target)} onChange={(e) => setTarget(e.target.value === "new" ? "new" : Number(e.target.value))}>
          {folders.map((f) => <option key={f.id} value={f.id}>{f.name}（{f.count}）</option>)}
          <option value="new">＋ 新資料夾…</option>
        </select>
      </div>
      {target === "new" && (
        <>
          <div className="field"><label>名稱<span className="req">*</span></label><input className="input" autoFocus value={name} onChange={(e) => setName(e.target.value)} placeholder="例如：第一輪上線驗證、支付相關回歸" /></div>
          <div className="field"><label>說明</label><input className="input" value={desc} onChange={(e) => setDesc(e.target.value)} placeholder="選填" /></div>
        </>
      )}
      <div className="stack" style={{ gap: 3, maxHeight: 260, overflow: "auto" }}>
        {(items ?? []).slice(0, 60).map((i) => <div key={`${i.group_key}:${i.testcase_id}`} className="mono faint" style={{ fontSize: 12 }}>{i.testcase_id}</div>)}
        {(items?.length ?? 0) > 60 && <div className="faint">… 另 {items!.length - 60} 條</div>}
      </div>
    </Drawer>
  );
}
