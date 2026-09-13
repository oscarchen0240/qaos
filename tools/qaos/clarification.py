"""Clarification（問 PM 的單子）：建立、送出、回答、落地，以及給 PM 看的 Markdown 渲染。"""
from . import store, ids, schema, state

def _render(c: dict) -> str:
    opts = "\n".join(f"- [ ] {o}" for o in c.get("options", [])) or "- （無預設選項，請自由回答）"
    return f"""# {c['clarification_id']}：{c['question']}

- 產品 / 功能：{c['product']} / {c['functional_area']}
- 規格：{c['spec_id']} v{c['spec_version']}{'  §' + c['spec_reference']['location'] if c.get('spec_reference') else ''}
- 相關需求：{c.get('requirement_id', '—')}
- 提出者：{c['raised_by']}（{c['raised_at'][:10]}）
- 狀態：{c['status']}

## 背景
{c.get('context', '')}

## 可能的解讀（請勾選或補充）
{opts}

## 若未回答的影響
{c.get('impact_if_unanswered', '相關 Test Case 無法設計 / 相關 Bug 無法判定是否違反規格')}

## PM 回覆
{c.get('answer', '（待回覆）')}
{('— ' + c['answered_by'] + '，' + c['answered_at'][:10] + '，落地方式：' + c['resolution']) if c.get('answer') else ''}
"""

def save(c: dict):
    errs = schema.errors(c, "spec/clarification.schema.json")
    if errs: raise ValueError("Clarification 不符 schema：" + "; ".join(errs[:3]))
    path = store.clarification_path(c["product"], c["functional_area"], c["clarification_id"])
    store.save(path, c); (store.ROOT / path).with_suffix(".md").write_text(_render(c), encoding="utf-8")
    return path

def new(product, area, spec_id, spec_version, question, by, context="", options=None, requirement_id=None, spec_reference=None, run_id=None, approval_id=None, impact=None) -> dict:
    c = {"clarification_id": ids.alloc("CLR", area), "product": product, "functional_area": area, "spec_id": spec_id, "spec_version": spec_version,
         "question": question, "context": context, "options": options or [], "raised_by": by, "raised_at": store.now(), "status": None, "history": []}
    for k, v in {"requirement_id": requirement_id, "spec_reference": spec_reference, "run_id": run_id, "approval_id": approval_id, "impact_if_unanswered": impact}.items():
        if v: c[k] = v
    state.apply("clarification", c, "OPEN", "system" if by == "system" or by.startswith("agent-") else by, "new", run_id)
    save(c); store.audit(run_id, by, "NEW_CLARIFICATION", f"{c['clarification_id']}: {question}")
    return c

def load(clr_id: str) -> dict:
    p = store.find_clarification(clr_id)
    if not p: raise FileNotFoundError(f"Clarification {clr_id} 不存在")
    return store.load(p)

def ask(clr_id, asked_to, by):
    c = load(clr_id); c["asked_to"] = asked_to; c["asked_at"] = store.now()
    state.apply("clarification", c, "ASKED", by, f"asked {asked_to}"); save(c); return c

def answer(clr_id, answer_text, answered_by, resolution, by, resulting_spec_version=None):
    c = load(clr_id); c.update({"answer": answer_text, "answered_by": answered_by, "answered_at": store.now(), "resolution": resolution})
    if resulting_spec_version: c["resulting_spec_version"] = resulting_spec_version
    state.apply("clarification", c, "ANSWERED", by, f"answered by {answered_by}"); save(c)
    store.audit(c.get("run_id"), by, "ANSWER_CLARIFICATION", f"{clr_id} resolution={resolution}")
    _resync_human_docs(c); return c

def _resync_human_docs(c):
    """PM 回答後同步 Human 看的文件：需求清單、PENDING 審批摘要（feedback 2026-09-14）。"""
    try:
        from . import req_export, approval_render
        if store.exists(store.requirements_path(c["spec_id"], c["spec_version"])): req_export.export(c["spec_id"], c["spec_version"])
        for p in (store.ROOT / "approvals").glob("APR-*.yaml"):
            a = store.load(p)
            if a["status"] == "PENDING" and a["type"] in ("ACTIVATE_TESTCASE", "APPLY_CHANGE"): approval_render.render(a["approval_id"]); approval_render.render_html(a["approval_id"])
    except Exception as e:
        store.audit(c.get("run_id"), "system", "RESYNC_DOCS_FAILED", str(e)[:200])

def apply_(clr_id, by, note=""):
    c = load(clr_id); state.apply("clarification", c, "APPLIED", by, "applied", c.get("run_id"), note=note); save(c); return c

def withdraw(clr_id, by, note=""):
    c = load(clr_id); state.apply("clarification", c, "WITHDRAWN", by, "withdrawn", note=note); save(c); return c

def list_(open_only=True):
    out = []
    for p in sorted((store.ROOT / "clarifications").glob("*/*/CLR-*.yaml")):
        c = store.load(p)
        if not open_only or c["status"] in ("OPEN", "ASKED", "ANSWERED"): out.append(c)
    return out

def build_index():
    """clarifications/index.md：依 product/area 分組的總表。"""
    rows = list_(open_only=False); lines = ["# Clarifications（待 PM 釐清的需求）", "", f"- 更新：{store.now()[:10]}", ""]
    groups = {}
    for c in rows: groups.setdefault((c["product"], c["functional_area"]), []).append(c)
    for (prod, area), cs in sorted(groups.items()):
        lines += [f"## {prod} / {area}", "", "| ID | 狀態 | 規格 | 問題 | PM 回覆 |", "|---|---|---|---|---|"]
        for c in cs: lines.append(f"| [{c['clarification_id']}]({prod}/{area}/{c['clarification_id']}.md) | {c['status']} | {c['spec_id']} v{c['spec_version']} | {c['question']} | {(c.get('answer') or '')[:60]} |")
        lines.append("")
    (store.ROOT / "clarifications" / "index.md").write_text("\n".join(lines), encoding="utf-8")
    return len(rows)
