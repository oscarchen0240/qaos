import { useEffect, useState } from "react";
import { Drawer } from "@/components/Drawer";
import { useConfirm } from "@/components/Confirm";
import { api, type Todo, type TodoStatus } from "@/lib/api";

interface OutputLite { key: string; label: string }
interface ReportLite { id: number; title: string }

export interface TodoDraft {
  title: string;
  status: TodoStatus;
  scheduled_date: string | null;
  due_date: string | null;
  estimate_min: number | null;
  details: string;
  linked_output_path: string | null;
  linked_report_id: number | null;
  auto_complete: boolean;
}

const empty: TodoDraft = {
  title: "", status: "todo", scheduled_date: null, due_date: null, estimate_min: null,
  details: "", linked_output_path: null, linked_report_id: null, auto_complete: true,
};

interface Props {
  open: boolean;
  initial: Todo | null;
  onClose: () => void;
  onSubmit: (draft: TodoDraft, id: number | null) => Promise<void>;
  onDelete?: (id: number) => Promise<void>;
}

export function TodoForm({ open, initial, onClose, onSubmit, onDelete }: Props) {
  const [d, setD] = useState<TodoDraft>(empty);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [outputs, setOutputs] = useState<OutputLite[]>([]);
  const [reports, setReports] = useState<ReportLite[]>([]);
  const confirm = useConfirm();

  useEffect(() => {
    if (!open) return;
    setErr("");
    setD(initial ? {
      title: initial.title, status: initial.status, scheduled_date: initial.scheduled_date, due_date: initial.due_date,
      estimate_min: initial.estimate_min, details: initial.details,
      linked_output_path: initial.linked_output_path, linked_report_id: initial.linked_report_id,
      auto_complete: initial.auto_complete,
    } : empty);
    api.get<OutputLite[]>("/api/outputs").then(setOutputs).catch(() => setOutputs([]));
    api.get<ReportLite[]>("/api/reports").then(setReports).catch(() => setReports([]));
  }, [open, initial]);

  const set = <K extends keyof TodoDraft>(k: K, v: TodoDraft[K]) => setD((x) => ({ ...x, [k]: v }));

  const submit = async () => {
    if (!d.title.trim()) { setErr("主旨必填"); return; }
    setBusy(true); setErr("");
    try { await onSubmit({ ...d, title: d.title.trim() }, initial?.id ?? null); onClose(); }
    catch (e) { setErr((e as Error).message); }
    finally { setBusy(false); }
  };

  return (
    <Drawer
      open={open}
      onClose={onClose}
      title={initial ? "編輯待辦" : "新增待辦"}
      subtitle={initial ? `#${initial.id} · 建立於 ${initial.created_at}` : "Enter 送出 · Esc 關閉"}
      footer={
        <>
          <div>
            {initial && onDelete && (
              <button className="btn danger sm" disabled={busy} onClick={async () => { if (await confirm({ title: "刪除這筆待辦？", message: initial.title, confirmText: "刪除", danger: true })) { await onDelete(initial.id); onClose(); } }}>刪除</button>
            )}
          </div>
          <div className="row">
            <button className="btn ghost" onClick={onClose} disabled={busy}>取消</button>
            <button className="btn primary" onClick={submit} disabled={busy}>{initial ? "儲存" : "建立"}</button>
          </div>
        </>
      }
    >
      <div className="field">
        <label>主旨<span className="req">*</span></label>
        <input className="input" autoFocus value={d.title} onChange={(e) => set("title", e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && !e.nativeEvent.isComposing) submit(); }} placeholder="要做什麼？" />
      </div>
      <div className="form-grid">
        <div className="field">
          <label>狀態</label>
          <select className="select" value={d.status} onChange={(e) => set("status", e.target.value as TodoStatus)}>
            <option value="todo">待處理</option>
            <option value="doing">進行中</option>
            <option value="done">已完成</option>
          </select>
        </div>
        <div className="field">
          <label>預估（分鐘）</label>
          <input className="input" type="number" min={0} value={d.estimate_min ?? ""} onChange={(e) => set("estimate_min", e.target.value === "" ? null : Number(e.target.value))} />
        </div>
        <div className="field">
          <label>排定日期</label>
          <input className="input" type="date" value={d.scheduled_date ?? ""} onChange={(e) => set("scheduled_date", e.target.value || null)} />
        </div>
        <div className="field">
          <label>截止日</label>
          <input className="input" type="date" value={d.due_date ?? ""} onChange={(e) => set("due_date", e.target.value || null)} />
        </div>
        <div className="field span2">
          <label>細節</label>
          <textarea className="textarea" value={d.details} onChange={(e) => set("details", e.target.value)} placeholder="補充說明、連結、驗收條件…" />
        </div>
        <div className="field">
          <label>關聯產出</label>
          <select className="select" value={d.linked_output_path ?? ""} onChange={(e) => set("linked_output_path", e.target.value || null)}>
            <option value="">（無）</option>
            {outputs.map((o) => <option key={o.key} value={o.key}>{o.label}</option>)}
          </select>
        </div>
        {d.linked_output_path && (
          <label className="field span2 check-row">
            <input type="checkbox" checked={d.auto_complete} onChange={(e) => set("auto_complete", e.target.checked)} />
            <span>產出「{d.linked_output_path}」審閱完成（已審）時自動完成此待辦；若之後被退回則自動回到進行中</span>
          </label>
        )}
        <div className="field">
          <label>關聯報告</label>
          <select className="select" value={d.linked_report_id ?? ""} onChange={(e) => set("linked_report_id", e.target.value ? Number(e.target.value) : null)}>
            <option value="">（無）</option>
            {reports.map((r) => <option key={r.id} value={r.id}>{r.title}</option>)}
          </select>
        </div>
      </div>
      {err && <div className="form-error">{err}</div>}
    </Drawer>
  );
}
