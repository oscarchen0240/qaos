import { useState } from "react";
import {
  DndContext, DragOverlay, PointerSensor, KeyboardSensor, closestCorners, useSensor, useSensors,
  useDroppable, type DragEndEvent, type DragStartEvent,
} from "@dnd-kit/core";
import { SortableContext, useSortable, verticalListSortingStrategy, sortableKeyboardCoordinates } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import type { Todo, TodoStatus } from "@/lib/api";
import { dueClass, fmtMinutes } from "@/lib/format";
import { REVIEW_CLASS, REVIEW_LABEL } from "@/lib/review";

export const COLUMNS: { key: TodoStatus; title: string; color: string }[] = [
  { key: "todo", title: "待處理", color: "var(--text-muted)" },
  { key: "doing", title: "進行中", color: "var(--accent)" },
  { key: "done", title: "已完成", color: "var(--ok)" },
];

interface Props {
  todos: Todo[];
  onMove: (id: number, status: TodoStatus, beforeId: number | null) => void;
  onToggleDone: (t: Todo) => void;
  onEdit: (t: Todo) => void;
  onDelete: (t: Todo) => void;
}

export function Kanban({ todos, onMove, onToggleDone, onEdit, onDelete }: Props) {
  const [activeId, setActiveId] = useState<number | null>(null);
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );
  const byStatus = (s: TodoStatus) => todos.filter((t) => t.status === s);
  const active = activeId != null ? todos.find((t) => t.id === activeId) ?? null : null;

  const onDragStart = (e: DragStartEvent) => setActiveId(Number(e.active.id));
  const onDragEnd = (e: DragEndEvent) => {
    setActiveId(null);
    const { active: a, over } = e;
    if (!over) return;
    const id = Number(a.id);
    const overId = String(over.id);
    if (overId.startsWith("col:")) {
      const status = overId.slice(4) as TodoStatus;
      const cur = todos.find((t) => t.id === id);
      if (cur && cur.status === status && byStatus(status).at(-1)?.id === id) return;
      onMove(id, status, null);
      return;
    }
    const overTodo = todos.find((t) => t.id === Number(overId));
    if (!overTodo || overTodo.id === id) return;
    const col = byStatus(overTodo.status);
    const fromIdx = col.findIndex((t) => t.id === id);
    const toIdx = col.findIndex((t) => t.id === overTodo.id);
    // 同欄往下拖時，放到目標之後；否則放到目標之前
    if (fromIdx !== -1 && fromIdx < toIdx) {
      const next = col[toIdx + 1];
      onMove(id, overTodo.status, next ? next.id : null);
    } else {
      onMove(id, overTodo.status, overTodo.id);
    }
  };

  return (
    <DndContext sensors={sensors} collisionDetection={closestCorners} onDragStart={onDragStart} onDragEnd={onDragEnd} onDragCancel={() => setActiveId(null)}>
      <div className="kanban">
        {COLUMNS.map((c) => (
          <Column key={c.key} col={c} items={byStatus(c.key)} onToggleDone={onToggleDone} onEdit={onEdit} onDelete={onDelete} />
        ))}
      </div>
      <DragOverlay>{active ? <CardView t={active} overlay /> : null}</DragOverlay>
    </DndContext>
  );
}

function Column({ col, items, onToggleDone, onEdit, onDelete }: { col: (typeof COLUMNS)[number]; items: Todo[] } & Pick<Props, "onToggleDone" | "onEdit" | "onDelete">) {
  const { setNodeRef, isOver } = useDroppable({ id: `col:${col.key}` });
  return (
    <section className={`kcol ${isOver ? "over" : ""}`} ref={setNodeRef}>
      <header className="kcol-head">
        <span className="kdot" style={{ background: col.color, boxShadow: `0 0 8px ${col.color}` }} />
        <span className="ktitle">{col.title}</span>
        <span className="kcount">{items.length}</span>
      </header>
      <SortableContext items={items.map((t) => t.id)} strategy={verticalListSortingStrategy}>
        <div className="kcol-body">
          {items.length === 0 && <div className="kcol-empty">拖曳卡片到這裡</div>}
          {items.map((t) => <SortableCard key={t.id} t={t} onToggleDone={onToggleDone} onEdit={onEdit} onDelete={onDelete} />)}
        </div>
      </SortableContext>
    </section>
  );
}

function SortableCard({ t, ...rest }: { t: Todo } & Pick<Props, "onToggleDone" | "onEdit" | "onDelete">) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: t.id });
  const style = { transform: CSS.Translate.toString(transform), transition };
  return (
    <div ref={setNodeRef} style={style} {...attributes} {...listeners}>
      <CardView t={t} dragging={isDragging} {...rest} />
    </div>
  );
}

export function CardView({ t, dragging, overlay, onToggleDone, onEdit, onDelete }: { t: Todo; dragging?: boolean; overlay?: boolean } & Partial<Pick<Props, "onToggleDone" | "onEdit" | "onDelete">>) {
  const due = dueClass(t.due_date, t.status);
  const done = t.status === "done";
  return (
    <article className={`card ${dragging ? "dragging" : ""} ${overlay ? "overlay" : ""}`} onDoubleClick={() => onEdit?.(t)}>
      <div className="card-top">
        <button className={`check ${done ? "on" : ""}`} aria-label="完成" onPointerDown={(e) => e.stopPropagation()} onClick={(e) => { e.stopPropagation(); onToggleDone?.(t); }}>
          {done && <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3.5"><path d="m5 13 4 4L19 7" /></svg>}
        </button>
        <div className={`card-title ${done ? "done" : ""}`}>{t.title}</div>
      </div>
      {(t.linked_output_path || t.linked_report_id || t.estimate_min != null) && (
        <div className="card-tags">
          {t.linked_output && (
            <span className={`tag ${t.linked_output.exists ? "cyan" : ""}`} title={t.linked_output.exists ? `產出 ${t.linked_output.label}` : "產出目前不存在"}>
              產出 · {t.linked_output.label}
              {t.linked_output.review_status && <span className={`dot ${REVIEW_CLASS[t.linked_output.review_status]}`}>{REVIEW_LABEL[t.linked_output.review_status]}</span>}
              {!t.linked_output.exists && " · 已不存在"}
            </span>
          )}
          {t.linked_report_id && <span className="tag violet">報告 #{t.linked_report_id}</span>}
          {t.auto_completed_at && <span className="tag ok" title={`依產出審閱狀態自動完成於 ${t.auto_completed_at}`}>自動完成</span>}
          {t.estimate_min != null && <span className="tag">est {fmtMinutes(t.estimate_min)}</span>}
        </div>
      )}
      <div className="card-meta">
        <span className="mono">#{t.id}</span>
        {t.scheduled_date && <span>排定 {t.scheduled_date}</span>}
        {t.due_date && <span className={due}>截止 {t.due_date}{due === "overdue" ? " · 逾期" : ""}</span>}
      </div>
      {!overlay && (
        <div className="card-actions">
          <button className="btn ghost sm" onPointerDown={(e) => e.stopPropagation()} onClick={(e) => { e.stopPropagation(); onEdit?.(t); }}>編輯</button>
          <button className="btn ghost sm" style={{ color: "var(--danger)" }} onPointerDown={(e) => e.stopPropagation()} onClick={(e) => { e.stopPropagation(); onDelete?.(t); }}>刪除</button>
        </div>
      )}
    </article>
  );
}
