"""Clarification（問 PM 的單子）：建立、送出、回答、落地，以及給 PM 看的 Markdown 渲染。

需求 A（第 3 章 FIX-06、FIX-08）：決策點欄位、不可變答案修訂（answer_revisions）與 basis、人工適用紀錄（applicability）、
補充佐證（evidence_addenda）、舊 CLR 的 metadata 升級。開單關卡與去重、生命週期（INCORPORATED、apply 的落地檢查）在 P5。"""
import json
from . import store, ids, schema, state, operation, sources, spec_ops

class ClarificationError(ValueError):
    pass

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

{_render_decision_sections(c)}## PM 回覆
{c.get('answer', '（待回覆）')}
{('— ' + c['answered_by'] + '，' + c['answered_at'][:10] + '，落地方式：' + c['resolution']) if c.get('answer') else ''}
"""

def _ref_text(r: dict) -> str:
    if r.get("type") == "spec": return f"{r['spec_id']} v{r['spec_version']} {r['location']}：「{r['quote']}」"
    if r.get("type") == "clarification": return f"{r['clarification_id']} 答案 rev {r['answer_rev']}：「{r['quote']}」"
    if r.get("type") == "approval": return f"{r['approval_id']} 決議 #{r['resolution_index']}：「{r['quote']}」"
    return f"{r.get('file_name', '')} {r.get('location', '')}"

def _render_decision_sections(c: dict) -> str:
    """決策點欄位的段落（第 3 章 §3.8）；舊 CLR 沒有這些欄位時不顯示。"""
    out = []
    cov = c.get("coverage") or {}
    if cov.get("consulted") or cov.get("missing_sources"):
        out += ["## 已查文件", *[f"- {p['spec_id']} v{p['spec_version']}（{p['content_hash'][:12]}…）" for p in cov.get("consulted", [])]]
        out += [f"- 缺：{m['name']}（{m['cited_at']['spec_id']} v{m['cited_at']['spec_version']} 第 {m['cited_at']['line']} 行提到）" for m in cov.get("missing_sources", [])]
        out.append("")
    if c.get("known_rules"): out += ["## 已確定的部分", *[f"- {_ref_text(r)}" for r in c["known_rules"]], ""]
    if c.get("decision_needed"): out += ["## 還需決定的事", c["decision_needed"], *[f"- 細節：{g}" for g in c.get("detail_gaps", [])], ""]
    if c.get("conflict_sides"): out += ["## 衝突兩邊", *[f"- {_ref_text(r)}" for r in c["conflict_sides"]], *([c["conflict_note"]] if c.get("conflict_note") else []), ""]
    return "\n".join(out) + ("\n" if out else "")

def save(c: dict):
    errs = schema.errors(c, "spec/clarification.schema.json")
    if errs: raise ValueError("Clarification 不符 schema：" + "; ".join(errs[:3]))
    path = store.clarification_path(c["product"], c["functional_area"], c["clarification_id"])
    store.save(path, c); store.write_derived(path[:-len(".yaml")] + ".md", _render(c))
    return path

DECISION_FIELDS = ("kind", "question_id", "topic", "subject", "params", "role_scope", "level", "known_rules", "conflict_sides", "conflict_note",
                   "coverage", "possible_source_missing", "decision_needed", "detail_gaps")

def _check_decision_fields(c: dict):
    """決策點欄位的驗證（第 3 章 §3.3、§3.4）：known_rules／conflict_sides 的 SourceRef、查閱的 SpecPin、文件索取單的引用處。"""
    target, at = (c["spec_id"], c["spec_version"]), (c.get("requirement_id"), c.get("question_id"))
    for field in ("known_rules", "conflict_sides"):
        for i, r in enumerate(c.get(field) or []):
            errs, _ = sources.validate(r, target=target, at=at)
            if errs: raise ClarificationError(f"{field}[{i}] 驗證失敗：{'; '.join(errs)}")
    cov = c.get("coverage") or {}
    for p in cov.get("consulted", []) + cov.get("unconsulted_normative", []):
        spec_ops.verify_pin(p["spec_id"], p["spec_version"], p["content_hash"])
    if c.get("kind") == "document_request":
        ms = cov.get("missing_sources") or []
        if not ms: raise ClarificationError("document_request 的 coverage.missing_sources 至少要有一項（每項只需要引用處）")
        for m in ms:
            if not m.get("cited_at"): raise ClarificationError(f"缺檔 {m.get('name')!r} 沒有引用處 cited_at")
            spec_ops.verify_pin(m["cited_at"]["spec_id"], m["cited_at"]["spec_version"], m["cited_at"]["content_hash"])
        c["document_items"] = [{"item_id": f"D{i + 1:02d}", "cited_at": m["cited_at"], "name": m["name"], "status": "open"} for i, m in enumerate(ms)]

@operation.operation("clarification_new")
def new(product, area, spec_id, spec_version, question, by, context="", options=None, requirement_id=None, spec_reference=None, run_id=None, approval_id=None, impact=None,
        **decision) -> dict:
    """建立 CLR。decision 為決策點欄位（DECISION_FIELDS，入口 A、B、D 提供）；給了就驗證，舊呼叫端不受影響。"""
    unknown = set(decision) - set(DECISION_FIELDS)
    if unknown: raise ClarificationError(f"不認得的欄位：{sorted(unknown)}")
    c = {"clarification_id": ids.alloc("CLR", area), "product": product, "functional_area": area, "spec_id": spec_id, "spec_version": spec_version,
         "question": question, "context": context, "options": options or [], "raised_by": by, "raised_at": store.now(), "status": None, "history": []}
    for k, v in {"requirement_id": requirement_id, "spec_reference": spec_reference, "run_id": run_id, "approval_id": approval_id, "impact_if_unanswered": impact}.items():
        if v: c[k] = v
    c.update({k: v for k, v in decision.items() if v is not None})
    if any(k in c for k in DECISION_FIELDS): _check_decision_fields(c)
    state.apply("clarification", c, "OPEN", "system" if by == "system" or by.startswith("agent-") else by, "new", run_id)
    save(c); store.audit(run_id, by, "NEW_CLARIFICATION", f"{c['clarification_id']}: {question}")
    return c

def load(clr_id: str) -> dict:
    p = store.find_clarification(clr_id)
    if not p: raise FileNotFoundError(f"Clarification {clr_id} 不存在")
    return store.load(p)

@operation.operation("clarification_ask")
def ask(clr_id, asked_to, by):
    c = load(clr_id); c["asked_to"] = asked_to; c["asked_at"] = store.now()
    state.apply("clarification", c, "ASKED", by, f"asked {asked_to}"); save(c); return c

def _legacy_rev0(c: dict) -> dict:
    """舊 CLR 的既有答案存成 rev 0：hash 等於原答案文字的 sha256；basis 只有目標、target_decl_rev 0、閉包空（第 3 章 §7）。"""
    b = sources.legacy_basis(c["spec_id"], c["spec_version"])
    return {"rev": 0, "answer": c["answer"], "answered_by": c.get("answered_by", ""), "answered_at": c["answered_at"], "resolution": c["resolution"],
            "answer_sources": [], "basis": b, "basis_hash": sources.basis_hash(b), "sha256": store.sha256_text(c["answer"])}

def revisions(c: dict) -> list[dict]:
    """答案修訂的檢視：有 answer_revisions 就用它；舊 CLR 有答案但還沒有修訂 → 以 rev 0 表示（尚未寫入，移轉或下一次 answer 時寫入）。"""
    if c.get("answer_revisions"): return c["answer_revisions"]
    return [_legacy_rev0(c)] if c.get("answer") else []

@operation.operation("clarification_answer")
def answer(clr_id, answer_text, answered_by, resolution, by, resulting_spec_version=None):
    """追加一筆不可變的答案修訂（A2、A3），記錄回答當時的 basis（附錄 A 3-6）；APPLIED 之後不追加。"""
    c = load(clr_id)
    if c["status"] == "APPLIED": raise ClarificationError(f"{clr_id} 已 APPLIED，不追加答案修訂；要改變決議請另開 CLR（relation prior_version）")
    try: revs = list(revisions(c)); b = sources.basis(c["spec_id"], c["spec_version"])
    except (spec_ops.SpecError, sources.SourceError) as e:
        raise ClarificationError(f"{clr_id} 的 spec 版本無法建立 basis（{e}）；答案修訂必須記錄回答當時的依據，請先匯入或修正該 spec 版本")
    revs.append({"rev": len(revs), "answer": answer_text, "answered_by": answered_by, "answered_at": store.now(), "resolution": resolution, "answer_sources": [],
                 "basis": b, "basis_hash": sources.basis_hash(b), "sha256": store.sha256_text(answer_text), "op_id": store.capturing().op_id})
    c["answer_revisions"] = revs
    c.update({"answer": answer_text, "answered_by": answered_by, "answered_at": store.now(), "resolution": resolution})
    if resulting_spec_version: c["resulting_spec_version"] = resulting_spec_version
    state.apply("clarification", c, "ANSWERED", by, f"answered by {answered_by}"); save(c)
    store.audit(c.get("run_id"), by, "ANSWER_CLARIFICATION", f"{clr_id} resolution={resolution}")
    _resync_human_docs(c); return c

def _resync_human_docs(c):
    """PM 回答後同步 Human 看的文件：需求清單、PENDING 審批摘要（feedback 2026-09-14）。"""
    try:
        from . import req_export, approval_render
        if store.exists(store.requirements_path(c["spec_id"], c["spec_version"])): req_export.export(c["spec_id"], c["spec_version"])
        for p in store.glob("approvals/APR-*.yaml"):
            a = store.load(p)
            if a["status"] == "PENDING" and a["type"] in ("ACTIVATE_TESTCASE", "APPLY_CHANGE"): approval_render.render(a["approval_id"]); approval_render.render_html(a["approval_id"])
    except Exception as e:
        store.audit(c.get("run_id"), "system", "RESYNC_DOCS_FAILED", str(e)[:200])

def impact(clr_id, keywords=None) -> list[dict]:
    """ADR-008：apply 前必掃——列出同 product/area 的 ACTIVE TC 中，掛同一 requirement 或步驟／expected 文字命中關鍵詞的候選。
    回傳 [{testcase_id, version, title, reasons:[...]}]；reasons 為 'requirement' 或 'keyword:<詞>'。"""
    c = load(clr_id); req = c.get("requirement_id"); kws = [k for k in (keywords or []) if k]
    out = []
    for ptr_p in store.glob("testcases/registry/TC-*.yaml"):
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

@operation.operation("clarification_apply")
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

@operation.operation("clarification_withdraw")
def withdraw(clr_id, by, note=""):
    c = load(clr_id); state.apply("clarification", c, "WITHDRAWN", by, "withdrawn", note=note); save(c); return c

def _require_human(by: str):
    if not by or not by.strip() or by == "system" or by.startswith("agent-"):
        raise ClarificationError(f"這個指令只能由人執行（--by {by!r} 不接受 system 或 agent-*）")

def scope_of(spec_id, requirement_id, subject, role_scope, params) -> dict:
    """QuestionScope；每個維度都必須明示（["*"]、{} 也要明寫）。"""
    sc = {"spec_id": spec_id, "requirement_id": requirement_id, "subject": subject, "role_scope": role_scope, "params": params}
    missing = [k for k, v in sc.items() if v is None]
    if missing: raise ClarificationError(f"適用範圍缺少 {', '.join(missing)}（[\"*\"]、{{}} 也必須明示）")
    errs = _scope_errors(sc)
    if errs: raise ClarificationError("適用範圍不合法：" + "; ".join(errs))
    return sc

def _scope_errors(sc) -> list[str]:
    from jsonschema import Draft202012Validator
    v = Draft202012Validator({"$ref": "https://qaos.local/schemas/common/defs.schema.json#/$defs/QuestionScope"}, registry=schema.registry())
    return [f"{e.json_path}: {e.message}" for e in v.iter_errors(sc)]

@operation.operation("applicability_add")
def applicability_add(clr_id, answer_rev, requirement_id, subject, role_scope, params, target, rationale, by, confirm_basis=None):
    """人工適用紀錄（第 3 章 §11；附錄 A 3-12）：CLI 依 --target 計算並顯示本次 basis_hash，人以 --confirm-basis 帶入相同值才寫入。"""
    _require_human(by)
    if not (rationale or "").strip(): raise ClarificationError("--rationale 必填")
    c = load(clr_id)
    if c["status"] == "WITHDRAWN": raise ClarificationError(f"{clr_id} 已撤回，不能追加適用紀錄")
    revs = c.get("answer_revisions") or []
    if not (0 <= int(answer_rev) < len(revs)):
        raise ClarificationError(f"{clr_id} 沒有 answer_rev {answer_rev}（目前有 {len(revs)} 筆答案修訂；舊 CLR 的 rev 0 由移轉或下一次 answer 寫入）")
    sid, ver = spec_ops.parse_pin(target)
    sc = scope_of(sid, requirement_id, subject, role_scope, params)
    bh = sources.basis_hash(sources.basis(sid, ver))
    if confirm_basis != bh:
        raise ClarificationError(f"本次 {sid}@{ver} 的 basis_hash = {bh}；確認後以 --confirm-basis {bh} 重新執行（未寫入）")
    rec = {"answer_rev": int(answer_rev), "scope": sc, "basis_hash": bh, "rationale": rationale.strip(), "by": by, "at": store.now(), "op_id": store.capturing().op_id}
    rec["sha256"] = sources.chash(rec)
    c.setdefault("applicability", []).append(rec); save(c)
    store.audit(c.get("run_id"), by, "ADD_APPLICABILITY", f"{clr_id} rev {answer_rev} → {sid}@{ver} {requirement_id} {subject}")
    return rec

@operation.operation("clarification_addenda_add")
def addenda_add(clr_id, source, note, by):
    """補充佐證（第 3 章 §3.6；附錄 A 3-11）：只能追加；不改變答案、answer_revisions、狀態。"""
    if not (note or "").strip(): raise ClarificationError("--note 必填")
    if not (by or "").strip(): raise ClarificationError("--by 必填")
    c = load(clr_id)
    if (source or {}).get("type") == "document":
        missing = [k for k in ("file_name", "sha256", "location") if not source.get(k)]
        if missing: raise ClarificationError(f"document 型佐證缺少 {', '.join(missing)}")
    else:
        errs, _ = sources.validate(source, target=(c["spec_id"], c["spec_version"]), at=(c.get("requirement_id"), c.get("question_id")))
        if errs: raise ClarificationError("佐證來源驗證失敗：" + "; ".join(errs))
    c.setdefault("evidence_addenda", []).append({"source": source, "note": note.strip(), "by": by, "at": store.now(), "op_id": store.capturing().op_id}); save(c)
    store.audit(c.get("run_id"), by, "ADD_EVIDENCE_ADDENDUM", clr_id)
    return c

UPGRADE_FIELDS = ("kind", "question_id", "subject", "role_scope", "params")

@operation.operation("clarification_metadata_upgrade")
def metadata_upgrade(clr_id, by, reason, **fields):
    """舊 CLR 只補缺的欄位（第 3 章 §3.9）：kind、question_id、subject、role_scope、params；不能改寫既有欄位；答案、修訂、狀態不變。"""
    _require_human(by)
    if not (reason or "").strip(): raise ClarificationError("--reason 必填")
    given = {k: v for k, v in fields.items() if v is not None}
    unknown = set(given) - set(UPGRADE_FIELDS)
    if unknown: raise ClarificationError(f"metadata upgrade 只能補 {', '.join(UPGRADE_FIELDS)}：{sorted(unknown)}")
    if not given: raise ClarificationError("沒有要補的欄位")
    c = load(clr_id)
    present = [k for k in given if k in c]
    if present: raise ClarificationError(f"{clr_id} 已有 {', '.join(present)}，不能經 metadata upgrade 改寫")
    keep = {k: c.get(k) for k in ("answer", "answer_revisions", "status", "resolution")}
    c.update(given)
    c["history"].append({"at": store.now(), "from_status": c["status"], "to_status": c["status"], "by": by, "trigger": "metadata_upgrade",
                         "note": f"{reason.strip()}；補 {', '.join(sorted(given))}"})
    assert {k: c.get(k) for k in keep} == keep
    save(c); store.audit(c.get("run_id"), by, "UPGRADE_CLARIFICATION_METADATA", f"{clr_id} {', '.join(sorted(given))}")
    return c

def list_(open_only=True):
    out = []
    for p in store.glob("clarifications/*/*/CLR-*.yaml"):
        c = store.load(p)
        if not open_only or c["status"] in ("OPEN", "ASKED", "ANSWERED"): out.append(c)
    return out

@operation.operation("clarification_index")
def build_index():
    """clarifications/index.md：依 product/area 分組的總表。"""
    rows = list_(open_only=False); lines = ["# Clarifications（待 PM 釐清的需求）", "", f"- 更新：{store.now()[:10]}", ""]
    groups = {}
    for c in rows: groups.setdefault((c["product"], c["functional_area"]), []).append(c)
    for (prod, area), cs in sorted(groups.items()):
        lines += [f"## {prod} / {area}", "", "| ID | 狀態 | 規格 | 問題 | PM 回覆 |", "|---|---|---|---|---|"]
        for c in cs: lines.append(f"| [{c['clarification_id']}]({prod}/{area}/{c['clarification_id']}.md) | {c['status']} | {c['spec_id']} v{c['spec_version']} | {c['question']} | {(c.get('answer') or '')[:60]} |")
        lines.append("")
    store.write_derived("clarifications/index.md", "\n".join(lines))
    return len(rows)
