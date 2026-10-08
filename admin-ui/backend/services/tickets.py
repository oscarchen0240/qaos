"""單據（唯讀）：approvals/APR-*、clarifications/**/CLR-*、bugs/**/BUG-*。

決定草稿存在管理系統 DB（ticket_drafts），並組成 bin/qaos 指令供人複製到 QA session 執行。
M5b 才會在平台直接執行；本檔不寫入 QAOS 任何檔案。
"""
import json
import re
import shlex

import yaml

from .. import db
from ..config import PROJECT_ROOT
from . import runs as run_svc

_cache: dict[str, tuple[float, dict]] = {}
APR_DIR = PROJECT_ROOT / "approvals"
CLR_DIR = PROJECT_ROOT / "clarifications"
BUG_DIR = PROJECT_ROOT / "bugs"
VER_DIR = PROJECT_ROOT / "testcases" / "versions"
SM_PATH = PROJECT_ROOT / "workflows" / "state-machines.yaml"


def _load(path) -> dict | None:
    try:
        st = path.stat()
    except OSError:
        return None
    c = _cache.get(str(path))
    if c and c[0] == st.st_mtime:
        return c[1]
    try:
        d = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001
        return None
    _cache[str(path)] = (st.st_mtime, d)
    return d


def signature() -> tuple:
    def sig(d, pat):
        if not d.exists():
            return ()
        fs = list(d.glob(pat))
        return (len(fs), max((f.stat().st_mtime for f in fs), default=0))
    return (sig(APR_DIR, "APR-*.yaml"), sig(CLR_DIR, "*/*/CLR-*.yaml"), sig(BUG_DIR, "*/*/BUG-*.yaml"))


def operator() -> str:
    with db.connect() as con:
        r = db.one(con.execute("SELECT value FROM settings WHERE key='operator_email'"))
    if r:
        return r["value"]
    # 沒設定就用最近一個 run 的 initiated_by
    runs = run_svc.all_runs()
    return (runs[0].get("initiated_by") if runs else None) or "you@example.com"


def set_operator(email: str):
    with db.connect() as con:
        con.execute("INSERT INTO settings (key, value) VALUES ('operator_email', ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (email.strip(),))


# ---------- drafts ----------
def get_draft(ticket_id: str) -> dict | None:
    with db.connect() as con:
        r = db.one(con.execute("SELECT * FROM ticket_drafts WHERE ticket_id=?", (ticket_id,)))
    if r:
        r["per_item"] = json.loads(r["per_item"] or "{}")
        r["extra"] = json.loads(r["extra"] or "{}")
    return r


def save_draft(ticket_id: str, kind: str, decision: str | None, option: str | None, rationale: str | None,
               per_item: dict | None, extra: dict | None) -> dict:
    cur = get_draft(ticket_id) or {}
    now = db.now()
    merged = {
        "decision": decision if decision is not None else cur.get("decision"),
        "option": option if option is not None else cur.get("option"),
        "rationale": rationale if rationale is not None else (cur.get("rationale") or ""),
        "per_item": per_item if per_item is not None else (cur.get("per_item") or {}),
        # extra 採 patch 合併：前端每次只送變動的 key 也不會蓋掉其他欄位
        "extra": {**(cur.get("extra") or {}), **extra} if extra is not None else (cur.get("extra") or {}),
    }
    with db.connect() as con:
        con.execute("""INSERT INTO ticket_drafts (ticket_id, kind, decision, option, rationale, per_item, extra, updated_at)
                       VALUES (?,?,?,?,?,?,?,?)
                       ON CONFLICT(ticket_id) DO UPDATE SET decision=excluded.decision, option=excluded.option, rationale=excluded.rationale,
                       per_item=excluded.per_item, extra=excluded.extra, updated_at=excluded.updated_at""",
                    (ticket_id, kind, merged["decision"], merged["option"], merged["rationale"], json.dumps(merged["per_item"], ensure_ascii=False),
                     json.dumps(merged["extra"], ensure_ascii=False), now))
    return get_draft(ticket_id)


def mark_sent(ticket_id: str, command: str):
    with db.connect() as con:
        con.execute("UPDATE ticket_drafts SET sent_at=?, sent_command=? WHERE ticket_id=?", (db.now(), command, ticket_id))


# ---------- approvals ----------
def _tc_version(tc_id: str, version: int) -> dict | None:
    return _load(VER_DIR / tc_id / f"v{version}.yaml")


def approvals(status: str | None = None) -> list[dict]:
    out = []
    if not APR_DIR.exists():
        return out
    for p in sorted(APR_DIR.glob("APR-*.yaml")):
        d = _load(p)
        if not d or (status and d.get("status") != status):
            continue
        dec = d.get("decision") or {}
        out.append({
            "approval_id": d.get("approval_id") or p.stem, "type": d.get("type"), "status": d.get("status"), "run_id": d.get("run_id"),
            "task_id": d.get("task_id"), "summary": d.get("summary") or "", "requested_at": d.get("requested_at"), "requested_by": d.get("requested_by"),
            "options": d.get("options") or [], "item_count": len(d.get("batch_items") or []),
            "decision": dec.get("decision"), "decided_by": dec.get("decided_by"), "decided_at": dec.get("decided_at"),
            "selected_option": dec.get("selected_option"), "rationale": dec.get("rationale"),
        })
    out.sort(key=lambda a: (a["status"] != "PENDING", -(int(a["approval_id"].split("-")[1]) if a["approval_id"].split("-")[1].isdigit() else 0)))
    return out


def approval_detail(apr_id: str) -> dict | None:
    d = _load(APR_DIR / f"{apr_id}.yaml")
    if not d:
        return None
    items = []
    per = (d.get("decision") or {}).get("per_item") or []
    per_map = {x.get("id"): x.get("decision") for x in per if isinstance(x, dict)}
    for it in d.get("batch_items") or []:
        tc = _tc_version(it.get("id"), int(it.get("version") or 1)) or {}
        items.append({
            "testcase_id": it.get("id"), "version": it.get("version"), "title": tc.get("title"), "priority": tc.get("priority"), "risk": tc.get("risk"),
            "test_level": tc.get("test_level"), "requirement_ids": tc.get("requirement_ids") or [], "preconditions": tc.get("preconditions") or [],
            "steps": tc.get("steps") or [], "expected_result": tc.get("expected_result"), "assumptions": tc.get("assumptions") or [],
            "spec_reference": tc.get("expected_result_spec_reference"), "exploratory": bool(tc.get("assumptions")),
            "decided": per_map.get(it.get("id")),
        })
    run = run_svc.get(d.get("run_id")) if d.get("run_id") else None
    return {
        **{k: d.get(k) for k in ("approval_id", "type", "status", "run_id", "task_id", "summary", "impact", "artifact_ids", "trace", "options", "requested_by", "requested_at", "diff_summary", "decision")},
        "items": items,
        "context": _activation_context(d, items, run),
        "artifacts": _artifact_context(d),
        "memo": _memo(apr_id, d.get("options") or []),
        "run": {"status": run["status"], "spec_id": run["spec_id"], "spec_version": run["spec_version"], "workflow_id": run["workflow_id"], "current_task_id": run["current_task_id"]} if run else None,
        "draft": get_draft(apr_id),
        "md_path": f"approvals/{apr_id}.md" if (APR_DIR / f"{apr_id}.md").exists() else None,
    }


def _find_artifact(aid: str):
    hits = list((PROJECT_ROOT / "artifacts").glob(f"**/{aid}.yaml"))
    return hits[0] if hits else None


def _artifact_context(apr: dict) -> list[dict]:
    """核准單引用的產物，抽成人看得懂的摘要（唯讀）。NEEDS_DECISION / HUMAN_OVERRIDE 沒有 batch_items，只能靠這個看內容。"""
    out = []
    for aid in apr.get("artifact_ids") or []:
        p = _find_artifact(aid)
        d = _load(p) if p else None
        if not d:
            out.append({"id": aid, "type": None, "missing": True}); continue
        t = d.get("artifact_type"); pl = d.get("payload") or {}
        rec = {"id": aid, "type": t, "created_by": d.get("created_by"), "created_at": d.get("created_at"), "iteration": d.get("iteration"), "path": str(p.relative_to(PROJECT_ROOT))}
        if t == "TestCaseDraft":
            tcs = pl.get("testcases") or []
            rec["cases"] = [{"draft_id": c.get("draft_id"), "title": c.get("title"), "priority": c.get("priority"), "risk": c.get("risk"), "test_level": c.get("test_level"),
                             "requirement_ids": c.get("requirement_ids") or [], "assumptions": [a.get("text") if isinstance(a, dict) else str(a) for a in (c.get("assumptions") or [])],
                             "exploratory": bool(c.get("assumptions")), "expected_result": c.get("expected_result"), "steps": c.get("steps") or []} for c in tcs]
            rec["count"] = len(tcs); rec["exploratory"] = sum(1 for c in rec["cases"] if c["exploratory"])
        elif t == "TestDesignReport":
            rec["assumptions"] = pl.get("assumptions") or []
            rec["uncovered"] = pl.get("uncovered_with_reason") or []
            rec["techniques"] = pl.get("technique_summary") or []
            rec["self_check"] = pl.get("self_check") or {}
            rec["coverage_count"] = len(pl.get("coverage_matrix") or [])
        elif t in ("TestValidationReport", "BugValidationReport"):
            rec["result"] = pl.get("result") or pl.get("overall_result")
            rec["issues"] = [{"severity": i.get("severity"), "draft_id": i.get("draft_id") or i.get("target"), "message": i.get("message") or i.get("description") or str(i)} for i in (pl.get("issues") or pl.get("findings") or [])][:30]
            rec["summary"] = pl.get("summary")
        else:
            rec["keys"] = list(pl.keys())[:12]
        out.append(rec)
    return out


MEMO_DIR = PROJECT_ROOT / ".warroom" / "recommendations"


def _memo(apr_id: str, options: list[dict]) -> dict | None:
    """QA session 的分析建議：`.warroom/recommendations/<APR>.md`。第一行可寫 `suggest: <option key>`；沒寫就從內文找選項 key 或標籤。"""
    p = MEMO_DIR / f"{apr_id}.md"
    if not p.exists():
        return None
    try:
        text = p.read_text(encoding="utf-8")
    except OSError:
        return None
    suggested = None
    m = re.search(r"^\s*suggest(?:ed|ion)?\s*[:：]\s*([A-Za-z_]+)\s*$", text, re.M | re.I)
    keys = {o.get("key") for o in options}
    if m and m.group(1) in keys:
        suggested = m.group(1)
    if not suggested:
        for o in options:
            if re.search(rf"建議[^\n]{{0,12}}({re.escape(o.get('key') or '')}|{re.escape((o.get('label') or '')[:8])})", text):
                suggested = o.get("key"); break
    return {"path": str(p.relative_to(PROJECT_ROOT)), "text": text, "mtime": _iso_mtime(p), "suggested": suggested}


def _iso_mtime(p) -> str:
    import datetime as _dt
    return _dt.datetime.fromtimestamp(p.stat().st_mtime, _dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _activation_context(apr: dict, items: list[dict], run: dict | None) -> dict | None:
    """啟用類核准單的脈絡：同 spec 已有多少 Phase 2 ACTIVE TC（不在這批裡的）、這批有沒有做過交叉比對（shadow-test 文件是否點名這個 run）。
    目的：避免在平台整批核准時繞過 QA session 的 Phase 2×3 交叉比對（2026-09-18 APR-0125 事故）。"""
    if apr.get("type") not in ("ACTIVATE_TESTCASE", "APPLY_CHANGE") or not run:
        return None
    from . import registry, specflow
    key = specflow.spec_key(run.get("spec_id"))
    if not key:
        return None
    area = key.rsplit("-", 1)[0]
    batch = {it["testcase_id"] for it in items}
    active = registry.active_index(area)
    existing = {tc: v for tc, v in active.items() if tc not in batch and specflow._matches_key(key, (v.get("spec_id") or "").replace("SPEC-", ""))}
    # 需求重疊：這批每條 TC 的 requirement_ids 與既有 ACTIVE 的重疊（粗略提示，不是語意比對）
    req_of_existing: dict[str, list[str]] = {}
    for tc in existing:
        v = _tc_version(tc, int(active[tc]["active_version"])) or {}
        for r in v.get("requirement_ids") or []:
            req_of_existing.setdefault(r, []).append(tc)
    overlap = {}
    for it in items:
        hits = sorted({tc for r in it.get("requirement_ids") or [] for tc in req_of_existing.get(r, [])})
        if hits:
            overlap[it["testcase_id"]] = hits[:6]
    docs = [dd for dd in specflow._shadow_docs() if specflow._matches_key(dd["slug"], key)]
    doc = next((dd for dd in docs if run["run_id"] in dd["run_ids"]), None)
    rec = _recommendation(doc, area, batch) if doc else None
    return {
        "spec_key": key, "phase2_active": len(existing), "phase2_ids": sorted(existing)[:200],
        "cross_compared": bool(doc), "shadow_doc": doc["path"] if doc else None,
        "overlap": overlap, "overlap_count": len(overlap),
        "needs_review": len(existing) > 0 and not doc,
        "recommendation": rec,
    }


_REC_PATTERNS = [
    # 1) 文件裡直接寫的指令：--per-item TC-X:approve / :reject
    ("per_item", re.compile(r"--per-item\s+(TC-[A-Z0-9_]+-\d+):(approve|reject)")),
    # 2) 「新增 N 條（TC-AREA-048、051、TC-AREA-093）」「保留TC-AREA-048、051」「採用 TC-AREA-084、085」
    ("listed", re.compile(r"(?:新增|保留|採用|核准)\s*(?:這\s*)?(?:\d+\s*條)?\s*(?:新增\s*TC)?[（(]?\s*((?:TC-[A-Z0-9_]+-\d+|\d{2,3})(?:\s*[、,，]\s*(?:TC-[A-Z0-9_]+-\d+|\d{2,3}))*)")),
]


def _recommendation(doc: dict, area: str, batch: set[str]) -> dict:
    """從 shadow-test 文件抓「採用哪幾條」。只認得三種寫法（見 _REC_PATTERNS）；抓不到就回 found=False，讓人自己看文件。"""
    try:
        text = (PROJECT_ROOT / doc["path"]).read_text(encoding="utf-8")
    except OSError:
        return {"found": False, "adopt": [], "reject": [], "evidence": [], "note": "讀不到文件"}
    adopt: set[str] = set(); reject: set[str] = set(); evidence: list[str] = []
    for kind, pat in _REC_PATTERNS:
        for m in pat.finditer(text):
            line = text[text.rfind("\n", 0, m.start()) + 1: text.find("\n", m.end()) if text.find("\n", m.end()) != -1 else len(text)].strip()
            if kind == "per_item":
                (adopt if m.group(2) == "approve" else reject).add(m.group(1)); evidence.append(line[:160])
            else:
                ids = [x.strip() for x in re.split(r"[、,，]", m.group(1))]
                full = [x if x.startswith("TC-") else f"TC-{area}-{int(x):03d}" for x in ids if x]
                hits = [x for x in full if x in batch]
                if hits:
                    adopt.update(hits); evidence.append(line[:160])
    # 若文件是「--decision reject --per-item X:approve」寫法，其餘就是不採用；若是 approve + per-item reject，其餘就是採用
    mode = None
    if re.search(r"--decision\s+reject", text) and adopt: mode = "adopt_listed"
    elif re.search(r"--decision\s+approve", text) and reject: mode = "reject_listed"
    elif adopt: mode = "adopt_listed"
    adopt_l = sorted(adopt & batch) if mode == "adopt_listed" else sorted(batch - reject) if mode == "reject_listed" else []
    reject_l = sorted(batch - set(adopt_l)) if mode else []
    seen = set(); ev = [e for e in evidence if not (e in seen or seen.add(e))]
    return {"found": bool(mode), "mode": mode, "adopt": adopt_l, "reject": reject_l, "evidence": ev[:6],
            "note": None if mode else "文件裡沒有可辨識的採用清單（認得：--per-item 指令、『新增 N 條（TC-…）』、『保留／採用 TC-…』）"}


def approval_command(apr_id: str, draft: dict) -> dict:
    """組 bin/qaos approve 指令。decision=approve/reject/override；option=NEEDS_DECISION 等的 selected_option；per_item 退回。"""
    who = operator()
    decision = draft.get("decision") or "approve"
    parts = ["bin/qaos", "approve", apr_id, "--decision", decision, "--by", who]
    if draft.get("option"):
        parts += ["--option", draft["option"]]
    per = draft.get("per_item") or {}
    rejected = [(t, v) for t, v in per.items() if isinstance(v, dict) and v.get("decision") == "reject"]
    for t, _ in rejected:
        parts += ["--per-item", f"{t}:reject"]
    reasons = [f"{t}：{v.get('reason')}" for t, v in rejected if v.get("reason")]
    rationale = (draft.get("rationale") or "").strip()
    if reasons:
        rationale = (rationale + "；" if rationale else "") + "退回：" + "；".join(reasons)
    if rationale:
        parts += ["--rationale", rationale]
    warnings = []
    if decision == "override" and not rationale:
        warnings.append("override 需要 --rationale")
    if rejected and decision != "approve":
        warnings.append("--per-item 只在 --decision approve 時有意義（整批決定＋例外）；目前 decision 不是 approve")
    missing = [t for t, v in rejected if not v.get("reason")]
    if missing:
        warnings.append(f"退回的 TC 未填理由：{', '.join(missing[:5])}{'…' if len(missing) > 5 else ''}（共 {len(missing)} 條）")
    d = _load(APR_DIR / f"{apr_id}.yaml") or {}
    n_items = len(d.get("batch_items") or [])
    if decision == "approve" and n_items and len(rejected) >= n_items:
        warnings.append("這批全部標退回：整批退回請把整體決定改成「退回」，QAOS 才會把 Designer task 重開")
    return {"command": " ".join(shlex.quote(x) for x in parts), "warnings": warnings, "rejected": [t for t, _ in rejected]}


# ---------- clarifications ----------
CLR_ACTIVE = ("OPEN", "ASKED", "ANSWERED", "INCORPORATED")      # 還需要人處理的狀態（終止狀態只有 APPLIED、WITHDRAWN）


def clarifications(open_only: bool = False) -> list[dict]:
    out = []
    if not CLR_DIR.exists():
        return out
    for p in sorted(CLR_DIR.glob("*/*/CLR-*.yaml")):
        d = _load(p)
        if not d:
            continue
        if open_only and d.get("status") not in CLR_ACTIVE:
            continue
        out.append({**{k: d.get(k) for k in ("clarification_id", "product", "functional_area", "spec_id", "spec_version", "status", "question", "requirement_id",
                                              "raised_by", "raised_at", "asked_to", "asked_at", "answered_by", "answered_at", "resolution", "run_id", "approval_id", "impact")},
                    "kind": d.get("kind") or "spec_question",
                    "answer": d.get("answer"), "options": d.get("options") or [], "context": d.get("context") or "",
                    "impact": d.get("impact") or d.get("impact_if_unanswered"),
                    "path": str(p.relative_to(PROJECT_ROOT))})
    order = {"OPEN": 0, "ASKED": 1, "ANSWERED": 2, "INCORPORATED": 3, "APPLIED": 4, "WITHDRAWN": 5}
    out.sort(key=lambda c: (order.get(c["status"], 9), c.get("raised_at") or ""), reverse=False)
    return out


def clarification_detail(clr_id: str) -> dict | None:
    for c in clarifications():
        if c["clarification_id"] == clr_id:
            d = _load(PROJECT_ROOT / c["path"]) or {}
            return {**c, "history": d.get("history") or [], "spec_reference": d.get("spec_reference"), "draft": get_draft(clr_id),
                    "allowed": _clr_allowed(c["status"], c["kind"])}
    return None


def _clr_allowed(status: str, kind: str = "spec_question") -> list[str]:
    """人可以做的轉換目標。轉換帶 kinds 時只適用於那幾種單（例如文件索取單的 OPEN→APPLIED 是逐項 fulfill／waive-item，
    不是 apply；spec_question 的 ANSWERED 等轉換不適用文件索取單）。"""
    sm = _load(SM_PATH) or {}
    m = (sm.get("machines") or {}).get("clarification") or {}
    return sorted({t["to"] for t in m.get("transitions") or []
                   if t.get("from") == status and "human" in (t.get("by") or []) and (not t.get("kinds") or kind in t["kinds"])})


def clarification_command(clr_id: str, draft: dict) -> dict:
    """action=ask|answer|apply|withdraw"""
    who = operator()
    ex = draft.get("extra") or {}
    action = draft.get("decision") or "answer"
    warnings = []
    if action == "ask":
        to = ex.get("asked_to") or ""
        if not to:
            warnings.append("需要填「問誰」（--to）")
        parts = ["bin/qaos", "clarification", "ask", clr_id, "--to", to, "--by", who, "--new-request"]
    elif action == "answer":
        ans = (draft.get("rationale") or "").strip()
        res = ex.get("resolution") or "requirement_clarified"
        by2 = ex.get("answered_by") or ex.get("asked_to") or "PM"
        if not ans:
            warnings.append("需要填回答內容（--answer）")
        parts = ["bin/qaos", "clarification", "answer", clr_id, "--answer", ans, "--answered-by", by2, "--resolution", res]
        if ex.get("spec_version"):
            parts += ["--spec-version", str(ex["spec_version"])]
        parts += ["--by", who, "--new-request"]
    elif action == "withdraw":
        reason = (draft.get("rationale") or "").strip()
        if not reason:
            warnings.append("需要填撤回原因（--reason）")
        parts = ["bin/qaos", "clarification", "withdraw", clr_id, "--reason", reason, "--by", who, "--new-request"]
    elif action == "apply":
        # 需求 A 後 apply 要選落地路徑（--path a6|a6b|a7），並對重新掃描出的每一張候選 TC 下結論（--tc-conclusion），
        # 是 ADR-008 規定由 QA session 逐條判定的動作，不適合做成指揮台表單；這裡只給指令骨架，不讓平台執行。
        kind = next((c["kind"] for c in clarifications() if c["clarification_id"] == clr_id), "spec_question")
        if kind == "document_request":
            warnings.append("文件索取單不是用 apply 結案，而是逐項 fulfill／waive-item；指揮台不支援，請在 QA session／終端機依 clarification --help 執行")
        else:
            warnings.append("套用（apply）需要 --path {a6,a6b,a7}、--impact-reviewed，以及對每張候選 TC 的 --tc-conclusion；指揮台不支援，"
                            "請框選下方指令骨架，到 QA session／終端機依 clarification apply --help 補齊後執行")
        parts = ["bin/qaos", "clarification", "apply", clr_id, "--path", "<a6|a6b|a7>", "--impact-reviewed", "<整體說明>", "--by", who, "--new-request"]
    else:
        return {"command": "", "warnings": [f"未知動作 {action}"]}
    return {"command": " ".join(shlex.quote(x) for x in parts), "warnings": warnings}


# ---------- bugs ----------
def bugs() -> list[dict]:
    out = []
    if not BUG_DIR.exists():
        return out
    for p in sorted(BUG_DIR.glob("*/*/BUG-*.yaml")):
        d = _load(p)
        if not d:
            continue
        out.append({**{k: d.get(k) for k in ("bug_id", "title", "product", "functional_area", "spec_id", "spec_version", "requirement_id", "severity", "priority",
                                              "status", "created_at", "updated_at", "approval_id", "external_ref", "duplicate_of")},
                    "evidence_count": len(d.get("evidence_ids") or []), "path": str(p.relative_to(PROJECT_ROOT))})
    order = {"OPEN": 0, "IN_PROGRESS": 1, "RESOLVED": 2, "VERIFYING": 3, "CLOSED": 8, "REJECTED": 9}
    out.sort(key=lambda b: (order.get(b["status"], 5), b.get("updated_at") or ""), reverse=False)
    return out


def bug_detail(bug_id: str) -> dict | None:
    for b in bugs():
        if b["bug_id"] == bug_id:
            d = _load(PROJECT_ROOT / b["path"]) or {}
            keys = ("severity_rationale", "environment", "acceptance_criteria_ids", "preconditions", "reproduction_steps", "expected_result", "expected_result_spec_reference",
                    "actual_result", "actual_result_evidence_map", "evidence_ids", "api", "impact", "suspected_area", "ambiguity_suspected", "history", "resolution", "verification")
            return {**b, **{k: d.get(k) for k in keys}, "draft": get_draft(bug_id), "allowed": _bug_allowed(b["status"])}
    return None


def _bug_allowed(status: str) -> list[dict]:
    sm = _load(SM_PATH) or {}
    m = (sm.get("machines") or {}).get("bug") or {}
    return [{"to": t["to"], "requires": t.get("requires")} for t in m.get("transitions") or [] if t.get("from") == status and "human" in (t.get("by") or [])]


def bug_command(bug_id: str, draft: dict) -> dict:
    """action=resolve|verify|close|transition"""
    who = operator()
    ex = draft.get("extra") or {}
    action = draft.get("decision") or "transition"
    warnings = []
    note = (draft.get("rationale") or "").strip()
    if action == "resolve":
        ref = ex.get("external_ref") or ""
        if not ref:
            warnings.append("需要 RD 修復的外部參照（--external-ref，例如 ticket 或 PR）")
        parts = ["bin/qaos", "bug", "resolve", bug_id, "--external-ref", ref, "--by", who]
        if note: parts += ["--note", note]
        if ex.get("fixed_by"): parts += ["--fixed-by", ex["fixed_by"]]
    elif action == "verify":
        exe = ex.get("execution_id") or ""
        if not exe:
            warnings.append("需要複測的 Execution ID（--execution，含 Evidence）")
        parts = ["bin/qaos", "bug", "verify", bug_id, "--execution", exe, "--by", who]
    elif action == "close":
        parts = ["bin/qaos", "bug", "close", bug_id, "--by", who]
        if note: parts += ["--rationale", note]
    else:
        to = ex.get("to") or ""
        if not to:
            warnings.append("需要目標狀態（--to）")
        parts = ["bin/qaos", "bug", "transition", bug_id, "--to", to, "--by", who]
        if ex.get("trigger"): parts += ["--trigger", ex["trigger"]]
        if note: parts += ["--note", note]
    # Bug 有重開迴圈（RESOLVED→OPEN→IN_PROGRESS…），同一個 bug 會合法地再次出現內容完全相同的請求；
    # 需求 A 後 CLI 會把它當成先前已完成而「印成功訊息卻不寫入」，所以人工決定的指令一律帶 --new-request
    # （狀態預檢與單飛鎖由 qaos_exec 負責，狀態機本身仍會拒絕不合法的轉換）。
    parts.append("--new-request")
    return {"command": " ".join(shlex.quote(x) for x in parts), "warnings": warnings}


def counts() -> dict:
    return {
        "approvals_pending": sum(1 for a in approvals() if a["status"] == "PENDING"),
        "clarifications_open": sum(1 for c in clarifications() if c["status"] in ("OPEN", "ASKED")),
        "bugs_open": sum(1 for b in bugs() if b["status"] not in ("CLOSED", "REJECTED")),
    }
