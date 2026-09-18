import { useCallback, useEffect, useState } from "react";
import { PageHeader, Tabs, EmptyState } from "@/components/PageHeader";
import { useToast } from "@/components/Toast";
import { useConfirm } from "@/components/Confirm";
import { api, type Todo, type TodoStatus } from "@/lib/api";
import { fmtDate, fmtMinutes } from "@/lib/format";
import { clickable } from "@/lib/a11y";
import { Plus } from "@phosphor-icons/react";
import { REVIEW_LABEL } from "@/lib/review";
import { Kanban } from "./todos/Kanban";
import { TodoForm, type TodoDraft } from "./todos/TodoForm";

export function TodosPage({ onChanged }: { onChanged: () => void }) {
  const [todos, setTodos] = useState<Todo[]>([]);
  const [tab, setTab] = useState<"board" | "history">("board");
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<Todo | null>(null);
  const { toast } = useToast();
  const confirm = useConfirm();

  const load = useCallback(() => api.get<Todo[]>("/api/todos").then(setTodos).catch((e) => toast(`載入失敗：${e.message}`, "danger")), [toast]);
  useEffect(() => {
    load();
    const id = setInterval(load, 10000);
    return () => clearInterval(id);
  }, [load]);

  const changed = () => { load(); onChanged(); };

  const submit = async (d: TodoDraft, id: number | null) => {
    if (id == null) { await api.post("/api/todos", d); toast("已建立待辦", "ok"); }
    else { await api.patch(`/api/todos/${id}`, d); toast("已儲存", "ok"); }
    changed();
  };

  const remove = async (id: number) => {
    await api.del(`/api/todos/${id}`);
    toast("已刪除");
    changed();
  };

  const move = async (id: number, status: TodoStatus, beforeId: number | null) => {
    // 樂觀更新：先在本地重排，再送後端
    setTodos((xs) => {
      const cur = xs.find((t) => t.id === id);
      if (!cur) return xs;
      const rest = xs.filter((t) => t.id !== id);
      const moved = { ...cur, status };
      if (beforeId == null) return [...rest, moved];
      const idx = rest.findIndex((t) => t.id === beforeId);
      return [...rest.slice(0, idx), moved, ...rest.slice(idx)];
    });
    try { await api.post(`/api/todos/${id}/move`, { status, before_id: beforeId }); changed(); }
    catch (e) { toast(`移動失敗：${(e as Error).message}`, "danger"); load(); }
  };

  const toggleDone = async (t: Todo) => {
    const status: TodoStatus = t.status === "done" ? "todo" : "done";
    try { await api.patch(`/api/todos/${t.id}`, { status }); changed(); }
    catch (e) { toast(`更新失敗：${(e as Error).message}`, "danger"); }
  };

  const open = todos.filter((t) => t.status !== "done");
  const done = todos.filter((t) => t.status === "done").sort((a, b) => (b.completed_at ?? "").localeCompare(a.completed_at ?? ""));

  return (
    <>
      <PageHeader
        eyebrow="Work"
        title="待辦"
        description="看板管理待處理／進行中／已完成；拖曳改狀態、勾選完成、可關聯到產出或報告。"
        actions={<button className="btn primary" onClick={() => { setEditing(null); setFormOpen(true); }}><Plus className="ic" aria-hidden="true" />新增待辦</button>}
      />
      <Tabs
        tabs={[{ key: "board", label: "看板", count: open.length }, { key: "history", label: "已完成歷史", count: done.length }]}
        active={tab}
        onChange={(k) => setTab(k as typeof tab)}
      />
      <div className="page-body">
        {tab === "board" ? (
          <Kanban
            todos={todos}
            onMove={move}
            onToggleDone={toggleDone}
            onEdit={(t) => { setEditing(t); setFormOpen(true); }}
            onDelete={async (t) => { if (await confirm({ title: "刪除待辦？", message: t.title, confirmText: "刪除", danger: true })) remove(t.id); }}
          />
        ) : done.length === 0 ? (
          <EmptyState title="還沒有完成的待辦">完成的項目會依完成時間列在這裡。</EmptyState>
        ) : (
          <table className="table">
            <thead>
              <tr><th>#</th><th>主旨</th><th>完成時間</th><th>排定</th><th>截止</th><th>預估</th><th>關聯</th><th></th></tr>
            </thead>
            <tbody>
              {done.map((t) => (
                <tr key={t.id} className="clickable" {...clickable(() => { setEditing(t); setFormOpen(true); }, `編輯 ${t.title}`)}>
                  <td className="mono faint">{t.id}</td>
                  <td>{t.title}</td>
                  <td className="mono">{fmtDate(t.completed_at)}</td>
                  <td className="mono">{t.scheduled_date ?? "—"}</td>
                  <td className="mono">{t.due_date ?? "—"}</td>
                  <td className="mono">{fmtMinutes(t.estimate_min)}</td>
                  <td>
                    {t.linked_output && <span className="tag cyan">{t.linked_output.label}{t.linked_output.review_status ? ` · ${REVIEW_LABEL[t.linked_output.review_status]}` : ""}</span>}{" "}
                    {t.linked_report_id && <span className="tag violet">報告 #{t.linked_report_id}</span>}
                  </td>
                  <td><button className="btn ghost sm" onClick={(e) => { e.stopPropagation(); toggleDone(t); }}>復原</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      <TodoForm open={formOpen} initial={editing} onClose={() => setFormOpen(false)} onSubmit={submit} onDelete={remove} />
    </>
  );
}
