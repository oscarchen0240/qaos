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

def impact(clr_id, keywords=None) -> list[dict]:
    """ADR-008：apply 前必掃——列出同 product/area 的 ACTIVE TC 中，掛同一 requirement 或步驟／expected 文字命中關鍵詞的候選。
    回傳 [{testcase_id, version, title, reasons:[...]}]；reasons 為 'requirement' 或 'keyword:<詞>'。"""
    c = load(clr_id); req = c.get("requirement_id"); kws = [k for k in (keywords or []) if k]
    out = []
    for ptr_p in sorted((store.ROOT / "testcases" / "registry").glob("TC-*.yaml")):
        ptr = store.load(ptr_p)
        if ptr.get("status") != "ACTIVE": continue
        tc = store.load(store.tc_version_path(ptr_p.stem, ptr["active_version"]))
        if tc.get("product") != c["product"] or tc.get("functional_area") != c["functional_area"]: continue
        reasons = []
        if req and req in tc.get("requirement_ids", []): reasons.append("requirement")
        blob = " ".join([tc.get("title", ""), *tc.get("preconditions", []), *(s.get("action", "") for s in tc.get("steps", [])), tc.get("expected_result", "")])
        reasons += [f"keyword:{k}" for k in kws if k in blob]
        if reasons: out.append({"testcase_id": ptr_p.stem, "version": ptr["active_version"], "title": tc.get("title", ""), "reasons": reasons})
    return out

def apply_(clr_id, by, note="", impact_reviewed=None, keywords=None):
    """落地 Clarification。ADR-008：必須先做影響掃描並逐條判定——impact_reviewed 為人／agent 對候選 TC 的結論（不受影響／需修訂／需 retire），
    未提供即拒絕；掃描候選清單與結論一併寫入 history note，供日後追溯。"""
    c = load(clr_id)
    if c["status"] != "ANSWERED": state.apply("clarification", c, "APPLIED", by, "applied", c.get("run_id"))   # 非法轉換先於 ADR-008 檢查報錯
    if not impact_reviewed:
        raise ValueError(f"{clr_id} apply 需 --impact-reviewed：先跑 `qaos clarification impact {clr_id} [--keyword ...]` 掃同 area ACTIVE TC，逐條判定後把結論寫進 --impact-reviewed（ADR-008）")
    cands = impact(clr_id, keywords)
    scan = "；".join(f"{x['testcase_id']}({','.join(x['reasons'])})" for x in cands) or "無候選"
    full = f"{note + '；' if note else ''}impact-scan[{len(cands)}]: {scan}；reviewed: {impact_reviewed}"
    state.apply("clarification", c, "APPLIED", by, "applied", c.get("run_id"), note=full); save(c)
    store.audit(c.get("run_id"), by, "APPLY_CLARIFICATION", f"{clr_id} impact-scan {len(cands)} candidates")
    return c

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
