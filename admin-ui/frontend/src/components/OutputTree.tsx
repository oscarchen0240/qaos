import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams, useLocation } from "react-router-dom";
import { api, type Folder, type OutputGroup } from "@/lib/api";
import { NAV_REFRESH_EVENT } from "@/lib/nav";
import { clickable } from "@/lib/a11y";
import { CaretRight, FolderSimple, FolderOpen, FileText, FileCode, Tray } from "@phosphor-icons/react";

type NodeProps = { k: string; depth: number; label: string; icon: JSX.Element; count?: number; active?: boolean; onClick?: () => void; children?: JSX.Element | null; open: Set<string>; toggle: (k: string) => void };
/** 樹節點：定義在元件外，避免每次 render 重新掛載子樹 */
function Node({ k, depth, label, icon, count, active, onClick, children, open, toggle }: NodeProps) {
  const has = !!children;
  const isOpen = open.has(k);
  return (
    <div className="tree-node">
      <div className={`tree-row ${active ? "active" : ""}`} style={{ paddingLeft: 10 + depth * 14 }} {...clickable(() => { if (has) toggle(k); onClick?.(); }, label)} aria-expanded={has ? isOpen : undefined}>
        <span className={`tree-caret ${has ? "" : "none"} ${isOpen ? "open" : ""}`} onClick={(e) => { if (has) { e.stopPropagation(); toggle(k); } }} aria-hidden="true"><CaretRight /></span>
        <span className="tree-icon">{icon}</span>
        <span className="tree-label" title={label}>{label}</span>
        {count !== undefined && <span className="tree-count">{count}</span>}
      </div>
      {has && isOpen && children}
    </div>
  );
}

const LS_KEY = "qaos.tree.open";
function loadOpen(): Set<string> { try { return new Set(JSON.parse(localStorage.getItem(LS_KEY) ?? "[]")); } catch { return new Set(); } }

/**
 * 側邊欄「產出」底下的 worktree 式樹：
 *   final/                （testcases/final 的模組 → json/html 檔）
 *   資料夾名/              （歸檔資料夾 → 模組 → TC）
 * 點模組開預覽、點 TC 開預覽並捲到該條、點資料夾切到資料夾分頁。
 */
export function OutputTree() {
  const [groups, setGroups] = useState<OutputGroup[]>([]);
  const [folders, setFolders] = useState<Folder[]>([]);
  const [open, setOpen] = useState<Set<string>>(loadOpen);
  const nav = useNavigate();
  const loc = useLocation();
  const [params] = useSearchParams();
  const onOutputs = loc.pathname === "/outputs";
  const curFolder = onOutputs ? params.get("folder") : null;
  const curGroup = onOutputs ? params.get("group") : null;
  const curTc = onOutputs ? params.get("tc") : null;

  useEffect(() => {
    let alive = true;
    const load = () => {
      api.get<OutputGroup[]>("/api/outputs").then((x) => alive && setGroups((o) => JSON.stringify(o) === JSON.stringify(x) ? o : x)).catch(() => {});
      api.get<Folder[]>("/api/folders").then((x) => alive && setFolders((o) => JSON.stringify(o) === JSON.stringify(x) ? o : x)).catch(() => {});
    };
    load();
    const id = setInterval(load, 15000);
    window.addEventListener(NAV_REFRESH_EVENT, load);
    return () => { alive = false; clearInterval(id); window.removeEventListener(NAV_REFRESH_EVENT, load); };
  }, []);

  const toggle = useCallback((k: string) => setOpen((s) => { const n = new Set(s); n.has(k) ? n.delete(k) : n.add(k); try { localStorage.setItem(LS_KEY, JSON.stringify([...n])); } catch { /* ignore */ } return n; }), []);
  const byKey = useMemo(() => new Map(groups.map((g) => [g.key, g])), [groups]);
  const go = (q: Record<string, string | null>) => {
    const n = new URLSearchParams();
    Object.entries(q).forEach(([k, v]) => { if (v) n.set(k, v); });
    nav(`/outputs${n.toString() ? `?${n}` : ""}`);
  };

  if (groups.length === 0 && folders.length === 0) return null;

  return (
    <div className="tree" role="tree" aria-label="產出樹">
      <Node open={open} toggle={toggle} k="final" depth={0} label="final/" icon={<Tray />} count={groups.length}>
        <>
          {groups.map((g) => (
            <Node open={open} toggle={toggle} key={g.key} k={`g:${g.key}`} depth={1} label={g.label} icon={open.has(`g:${g.key}`) ? <FolderOpen /> : <FolderSimple />} count={g.meta.case_count ?? undefined} active={curGroup === g.key && !curTc && !curFolder}
              onClick={() => go({ group: g.key })}>
              <>
                {g.files.map((f) => (
                  <div key={f.path} className="tree-row leaf" style={{ paddingLeft: 10 + 2 * 14 }} {...clickable(() => go({ group: g.key }), f.name)} title={f.path}>
                    <span className="tree-caret none" aria-hidden="true" />
                    <span className="tree-icon">{f.kind === "json" ? <FileCode /> : <FileText />}</span>
                    <span className="tree-label mono">{f.name}</span>
                    {f.unread && <span className="tree-dot" title="未讀" />}
                  </div>
                ))}
              </>
            </Node>
          ))}
        </>
      </Node>
      {folders.map((f) => {
        const mods = new Map<string, string[]>();
        f.items.forEach((it) => { const a = mods.get(it.group_key) ?? []; a.push(it.testcase_id); mods.set(it.group_key, a); });
        const fk = `f:${f.id}`;
        return (
          <Node open={open} toggle={toggle} key={f.id} k={fk} depth={0} label={f.name} icon={open.has(fk) ? <FolderOpen /> : <FolderSimple />} count={f.count} active={curFolder === String(f.id) && !curGroup}
            onClick={() => go({ tab: "folders", folder: String(f.id) })}>
            <>
              {f.items.length === 0 && <div className="tree-row leaf faint" style={{ paddingLeft: 10 + 14 }}><span className="tree-caret none" /><span className="tree-label">（空）</span></div>}
              {[...mods.entries()].map(([gk, ids]) => (
                <Node open={open} toggle={toggle} key={gk} k={`${fk}/${gk}`} depth={1} label={byKey.get(gk)?.label ?? gk} icon={<FolderSimple />} count={ids.length}>
                  <>
                    {ids.sort().map((id) => (
                      <div key={id} className={`tree-row leaf ${curGroup === gk && curTc === id ? "active" : ""}`} style={{ paddingLeft: 10 + 2 * 14 }} {...clickable(() => go({ group: gk, tc: id, tab: "folders", folder: String(f.id) }), id)}>
                        <span className="tree-caret none" aria-hidden="true" />
                        <span className="tree-icon"><FileText /></span>
                        <span className="tree-label mono">{id}</span>
                      </div>
                    ))}
                  </>
                </Node>
              ))}
            </>
          </Node>
        );
      })}
    </div>
  );
}
