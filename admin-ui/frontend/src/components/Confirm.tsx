import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";

interface Options { title: string; message?: ReactNode; confirmText?: string; danger?: boolean }
type Ask = (opts: Options) => Promise<boolean>;

const Ctx = createContext<Ask>(async () => false);
export const useConfirm = () => useContext(Ctx);

export function ConfirmProvider({ children }: { children: ReactNode }) {
  const [opts, setOpts] = useState<Options | null>(null);
  const resolver = useRef<((v: boolean) => void) | null>(null);

  const ask = useCallback<Ask>((o) => new Promise((resolve) => { resolver.current = resolve; setOpts(o); }), []);
  const finish = (v: boolean) => { resolver.current?.(v); resolver.current = null; setOpts(null); };

  useEffect(() => {
    if (!opts) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") finish(false); if (e.key === "Enter") finish(true); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }); // eslint-disable-line react-hooks/exhaustive-deps

  const value = useMemo(() => ask, [ask]);
  return (
    <Ctx.Provider value={value}>
      {children}
      {opts && (
        <div className="modal-backdrop" onClick={() => finish(false)}>
          <div className="modal" role="dialog" aria-modal="true" onClick={(e) => e.stopPropagation()}>
            <div className="modal-title">{opts.title}</div>
            {opts.message && <div className="modal-body">{opts.message}</div>}
            <div className="modal-foot">
              <span className="faint" style={{ fontSize: 12 }}><span className="kbd">Esc</span> 取消 · <span className="kbd">Enter</span> 確定</span>
              <div className="row">
                <button className="btn ghost" onClick={() => finish(false)}>取消</button>
                <button className={`btn ${opts.danger ? "danger" : "primary"}`} autoFocus onClick={() => finish(true)}>{opts.confirmText ?? "確定"}</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </Ctx.Provider>
  );
}
