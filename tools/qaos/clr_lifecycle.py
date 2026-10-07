"""CLR 生命週期（需求 A 第 6 章 FIX-10，人工確認結案）：A4 納入、採用目標解析、候選掃描、impact、apply（a6／a6b／a7）、
文件索取單的 fulfill／waive-item 與最後判定（A8、A9）、唯讀查詢 show／stale-tcs。

- 寫入指令都以操作計畫執行（取全域鎖）；唯讀查詢不取鎖、不寫檔，也不保證跨檔一致的快照。
- 系統不驗證 --tc-conclusion 是否屬實，也不自動追蹤延後事項（第 6 章 §13）。"""
import re, pathlib
from . import store, state, operation, sources, spec_ops, rm, schema, clarification as clr

RULE_VERSION = "2"   # 2：(d) 關鍵字也比對 steps[].expected（附錄 A 6-16）；1 的 scan 只沿用關鍵字
APPLIED_RESOLUTIONS = ("requirement_clarified", "spec_updated")
QUIET_RESOLUTIONS = ("no_change", "out_of_scope")
CONCLUSIONS = ("updated", "not_affected", "retire_planned")
READONLY_NOTE = "（唯讀查詢：不取鎖，不保證跨檔一致的快照）"

class LifecycleError(ValueError):
    pass

def _human(by: str):
    if by == "system" or by.startswith("agent-"): raise LifecycleError(f"只能由人執行（--by {by}）")

def latest(c: dict) -> dict:
    revs = c.get("answer_revisions") or []
    if not revs: raise LifecycleError(f"{c['clarification_id']} 沒有答案修訂")
    return revs[-1]

def target_id(t: dict) -> str:
    return f"{t['spec_id']}@{t['spec_version']}:{t['requirement_id']}#{t['question_id']}"

def _spec_meta(sid: str) -> tuple[str, str]:
    s = store.load(store.spec_dir(sid) / "spec.yaml")
    return s["product"], s["functional_area"]

# ---------------------------------------------------------------- 採用位置與 effective_basis
def adoption_refs(req: dict, dp: dict) -> list:
    """決策點上「採用」CLR 答案的明確 SourceRef：resolution.source；basis 為 defined_by_decision 時的 known_rules（附錄 A 6-22）。"""
    out = []
    if (dp.get("resolution") or {}).get("source"): out.append(dp["resolution"]["source"])
    if dp.get("basis") == "defined_by_decision": out += [r for r in dp.get("known_rules") or [] if r.get("type") in ("clarification", "approval")]
    return out

def _eb(ref, at):
    try: return sources.effective_basis(ref, at=at)
    except sources.SourceError: return None

def _via(c: dict, rev: dict, scope: dict, dp_bh: str) -> str | None:
    """適用依據：自身範圍（basis 相同且涵蓋）或 applicability（回傳該筆 sha256）；都不成立 → None。"""
    own = sources.self_scope(c)
    if rev["basis_hash"] == dp_bh and own is not None and sources.covers(own, scope): return "own_scope"
    for ap in c.get("applicability") or []:
        if ap["answer_rev"] == rev["rev"] and ap["basis_hash"] == dp_bh and sources.covers(ap["scope"], scope): return f"applicability({ap['sha256']})"
    return None

def _dp_scope(req, dp):
    return {"spec_id": req["spec_id"], "requirement_id": req["requirement_id"], "subject": dp["subject"], "role_scope": dp["role_scope"], "params": dp["params"]}

def _adopting_points(c: dict) -> list:
    """stale-tcs 用：各 spec 版本最新 revision 中，採用本 CLR **任一** answer_rev 的決策點（不限最新 rev、不做 X16；唯讀查詢的目標）。"""
    out = []
    for idx in store.glob("artifacts/requirements/*/*/revisions/index.yaml"):
        d = store.load(idx)
        if not d.get("revisions"): continue
        pin = rm.pin_of(d["spec_id"], d["spec_version"], d["revisions"][-1]["revision"]); product, area = _spec_meta(pin["spec_id"])
        for req in rm.requirements_of(pin).values():
            for dp in req.get("decision_points") or []:
                at = (req["requirement_id"], dp["question_id"])
                if any((eb := _eb(r, at)) and eb[0] == "clarification" and eb[1] == c["clarification_id"] for r in adoption_refs(req, dp)):
                    out.append({"product": product, "area": area, "spec_id": pin["spec_id"], "spec_version": pin["spec_version"],
                                "requirement_id": req["requirement_id"], "question_id": dp["question_id"]})
    return out

def _targets_in_revision(c: dict, pin: dict) -> list:
    rev = latest(c); want = ("clarification", c["clarification_id"], rev["rev"], rev["sha256"]); out = []
    product, area = _spec_meta(pin["spec_id"])
    for req in rm.requirements_of(pin).values():
        for dp in req.get("decision_points") or []:
            at = (req["requirement_id"], dp["question_id"])
            if not any(_eb(r, at) == want for r in adoption_refs(req, dp)): continue
            scope = _dp_scope(req, dp); via = _via(c, rev, scope, dp.get("basis_hash"))
            if via is None: continue                                            # 沒有通過 X16：不是採用目標
            out.append({"product": product, "area": area, "spec_id": pin["spec_id"], "spec_version": pin["spec_version"], "source": {"revision": pin},
                        "requirement_id": req["requirement_id"], "question_id": dp["question_id"], "scope": scope, "via": via})
    return out

_FINAL = {"BugDraft": ("agent-bug-analyst", "agent-bug-validator", "BugValidationReport", "bug_draft_artifact_id"),
          "TestCaseDraft": ("agent-test-designer", "agent-test-validator", "TestValidationReport", "testcase_draft_artifact_id")}

def _last_output(run: dict, agent: str, art_type: str) -> dict | None:
    t = next((x for x in run["tasks"] if x.get("agent_id") == agent), None)
    for aid in reversed((t or {}).get("output_artifact_ids") or []):
        p = store.find_artifact(aid); a = store.load(p) if p else None
        if a and a["artifact_type"] == art_type and a["status"] == "VALID": return a
    return None

def _final_draft(run: dict, art_type: str) -> dict | None:
    """run 的最終 Draft（第 6 章 §5.6、附錄 A 6-31）：產生者 task 本輪 output_artifact_ids 中的 VALID Draft，而且必須是本 run 最後一份 VALID
    驗證報告審查的那份。退回重做會清空 output_artifact_ids 但不把舊稿改成 SUPERSEDED，所以不能以檔名或 artifact ID 排序推定；兩者對不上視為沒有最終稿。"""
    gen, val, rep_type, key = _FINAL[art_type]
    draft, rep = _last_output(run, gen, art_type), _last_output(run, val, rep_type)
    if draft is None or rep is None or rep["payload"].get(key) != draft["artifact_id"]: return None
    return draft

def bug_rejected(run_id: str) -> bool:
    """spec-to-bug run 的 Bug 已 REJECTED（CONFIRM_DUPLICATE 確認重複、RESOLVE_AMBIGUITY reject）。"""
    p = f"runs/{run_id}/entities/bug.yaml"
    return store.exists(p) and store.load(p)["status"] == "REJECTED"

def _final_bugdraft(run_id: str) -> dict | None:
    """最終 BugDraft；Bug 已 REJECTED 的 run 沒有可作為落地證據的最終稿（附錄 A 6-37：改走 a6b 或其他 run）。"""
    if bug_rejected(run_id): return None
    return _final_draft(store.load(f"runs/{run_id}/run.yaml"), "BugDraft")

def _targets_in_bugdraft(c: dict, run: dict, art: dict) -> list:
    """BugDraft 的明確 SourceRef（必須對應 decision_refs 的決策點）中，effective_basis 為最新 answer_rev、通過 X16 者。"""
    rev = latest(c); want = ("clarification", c["clarification_id"], rev["rev"], rev["sha256"]); out = []
    p = art["payload"]
    try: pin = rm.run_pin(run)
    except rm.RMError: return []
    reqs = rm.requirements_of(pin); product, area = _spec_meta(p["spec_id"])
    for d in p.get("decision_refs") or []:
        req = reqs.get(d["requirement_id"]); dp = next((x for x in (req or {}).get("decision_points") or [] if x["question_id"] == d["question_id"]), None)
        if dp is None: continue
        at = (d["requirement_id"], d["question_id"])
        refs_ = [r for r in p.get("source_refs") or [] if r.get("type") in ("clarification", "approval") and _ident(r) == d.get("basis_ref")]
        if not any(_eb(r, at) == want for r in refs_): continue
        scope = _dp_scope(req, dp); via = _via(c, rev, scope, dp.get("basis_hash"))
        if via is None: continue
        out.append({"product": product, "area": area, "spec_id": p["spec_id"], "spec_version": str(p["spec_version"]), "source": {"bug_draft": art["artifact_id"]},
                    "requirement_id": d["requirement_id"], "question_id": d["question_id"], "scope": scope, "via": via})
    return out

def _ident(r):
    from .dispatch import basis_ref
    try: return basis_ref(r)
    except (KeyError, TypeError): return None

def resolve_targets(c: dict, landed_in=()) -> list:
    """採用目標（第 6 章 §5.4）：每個 spec 版本的最新 revision，加上 landed-in run 綁定的 revision 與最終 BugDraft。依 target_id 去重。"""
    found = {}
    for idx in store.glob("artifacts/requirements/*/*/revisions/index.yaml"):
        d = store.load(idx)
        if not d.get("revisions"): continue
        for t in _targets_in_revision(c, rm.pin_of(d["spec_id"], d["spec_version"], d["revisions"][-1]["revision"])): found.setdefault(target_id(t), t)
    for rid in landed_in:
        run = store.load(f"runs/{rid}/run.yaml")
        try: pin = rm.run_pin(run)
        except rm.RMError: pin = None
        if pin:
            for t in _targets_in_revision(c, pin): found.setdefault(target_id(t), t)
        bd = _final_bugdraft(rid)
        if bd:
            for t in _targets_in_bugdraft(c, run, bd): found.setdefault(target_id(t), t)
    return [found[k] for k in sorted(found)]

def _run_scope(run: dict) -> set | None:
    """run 的範圍（第 6 章 §5.6 第 3 點；附錄 A 6-31）：manual-test-to-regression 是本 run 最終 TestCaseDraft 各 TC 的 requirement_ids；
    其他（spec-to-testcase、spec-change-impact）是綁定 revision 的全部需求（None）。spec-to-bug 只看最終 BugDraft，不經過這裡。"""
    if run.get("workflow_id") != "manual-test-to-regression": return None
    draft = _final_draft(run, "TestCaseDraft")
    return {r for t in ((draft or {}).get("payload") or {}).get("testcases") or [] for r in t.get("requirement_ids") or []}

def run_targets(c: dict, run_id: str) -> list:
    """landed-in run 自己的產出中、在 run 範圍內解析出的目標：spec-to-bug 只看最終 BugDraft（綁定的 revision 是分析依據，不是這個 run 的產出）；
    其他 workflow 看綁定的目標 revision，manual 另外限於本 run TC 的需求。"""
    run = store.load(f"runs/{run_id}/run.yaml")
    if run.get("workflow_id") == "spec-to-bug":
        bd = _final_bugdraft(run_id)
        return _targets_in_bugdraft(c, run, bd) if bd else []
    try: out = _targets_in_revision(c, rm.run_pin(run))
    except rm.RMError: return []
    scope = _run_scope(run)
    return out if scope is None else [t for t in out if t["requirement_id"] in scope]

# ---------------------------------------------------------------- A4、A4'（第 6 章 §3.2；附錄 A 6-4）
def _incorporate(cid: str, landing: dict, by="system"):
    c = clr.load(cid)
    if c["status"] == "ANSWERED": state.apply("clarification", c, "INCORPORATED", by, "A4", landing.get("run_id"))
    elif c["status"] not in ("INCORPORATED", "APPLIED"): return
    c.setdefault("landings", []).append({"type": "incorporated", **landing, "op_id": store.capturing().op_id, "at": store.now()})
    clr.save(c); store.audit(landing.get("run_id"), by, "INCORPORATE_CLARIFICATION", f"{cid} ← {landing.get('rm_pin', {}).get('revision') or landing.get('bug_draft')}")

def incorporate_revision(run: dict, pin: dict):
    """G-SPEC 提交：revision 中以明確 SourceRef 採用某 CLR 最新 answer_rev、且通過 X16 的決策點 → A4／A4'（每張 CLR 每份 revision 一筆 landing）。"""
    seen = set()
    for req in rm.requirements_of(pin).values():
        for dp in req.get("decision_points") or []:
            at = (req["requirement_id"], dp["question_id"])
            for ref in adoption_refs(req, dp):
                eb = _eb(ref, at)
                if not eb or eb[0] != "clarification" or eb[1] in seen: continue
                c = clr.load(eb[1]); revs = c.get("answer_revisions") or []
                if not revs or eb[2] != len(revs) - 1: continue
                if _via(c, revs[-1], _dp_scope(req, dp), dp.get("basis_hash")) is None: continue
                seen.add(eb[1]); _incorporate(eb[1], {"rm_pin": pin, "run_id": run["run_id"]})

def incorporate_bugdraft(run: dict, art: dict):
    """G-BVAL 提交的 BugDraft：明確 SourceRef（對應 decision_refs）引用最新 answer_rev 且通過 X16 → A4／A4'。沒有 SourceRef 的 BugDraft 不觸發（第一批，§3.3 第 3 點）。"""
    p = art["payload"]; cids = set()
    for r in p.get("source_refs") or []:
        if r.get("type") == "clarification": cids.add(r["clarification_id"])
        if r.get("type") == "approval":
            for d in p.get("decision_refs") or []:
                eb = _eb(r, (d["requirement_id"], d["question_id"]))
                if eb and eb[0] == "clarification": cids.add(eb[1])
    for cid in sorted(cids):
        c = clr.load(cid)
        if c.get("answer_revisions") and _targets_in_bugdraft(c, run, art): _incorporate(cid, {"bug_draft": art["artifact_id"], "run_id": run["run_id"]})

# ---------------------------------------------------------------- 候選掃描（第 6 章 §5.10）
def _active_tcs():
    for ptr_p in store.glob("testcases/registry/TC-*.yaml"):
        ptr = store.load(ptr_p)
        if ptr.get("status") != "ACTIVE" or not ptr.get("active_version"): continue
        vp = store.tc_version_path(ptr_p.stem, ptr["active_version"])
        yield ptr_p.stem, ptr["active_version"], store.load(vp), store.sha256_file(vp)

def scan_units(c: dict, targets: list, path: str) -> list:
    units = {(c["product"], c["functional_area"])}
    if path != "a7": units |= {(t["product"], t["area"]) for t in targets}
    return [{"product": p, "area": a} for p, a in sorted(units)]

def scan_candidates(c: dict, targets: list, keywords: list, units: list, path: str) -> list:
    rev = latest(c); latest_eb = ("clarification", c["clarification_id"], rev["rev"], rev["sha256"])
    own = (c["product"], c["functional_area"]); unit_set = {(u["product"], u["area"]) for u in units}; out = []
    for tc_id, ver, tc, sha in _active_tcs():
        unit = (tc.get("product"), tc.get("functional_area"))
        if unit not in unit_set: continue
        reasons = []
        tgt = [t for t in targets if (t["product"], t["area"]) == unit] if path != "a7" else []
        if any(t["requirement_id"] in tc.get("requirement_ids", []) for t in tgt): reasons.append("target_requirement")       # (a)
        for d in tc.get("decision_refs") or []:                                                                                  # (b)
            if any((t["requirement_id"], t["question_id"]) == (d["requirement_id"], d["question_id"]) for t in tgt):
                br = d.get("basis_ref"); eb = _eb({**br, "quote": "x"}, (d["requirement_id"], d["question_id"])) if br else None
                if eb != latest_eb: reasons.append(f"stale_decision_ref:{d['requirement_id']}#{d['question_id']}")
        if unit == own and c.get("requirement_id") and c["requirement_id"] in tc.get("requirement_ids", []): reasons.append("clr_requirement")   # (c)
        blob = " ".join([tc.get("title", ""), *tc.get("preconditions", []), *(s.get(k) or "" for s in tc.get("steps", []) for k in ("action", "expected")), tc.get("expected_result", "")])
        reasons += [f"keyword:{k}" for k in keywords if k in blob]                                                              # (d)
        if reasons: out.append({"tc_id": tc_id, "active_version": ver, "tc_version_sha256": sha, "reasons": sorted(set(reasons))})
    return sorted(out, key=lambda x: x["tc_id"])

def parse_target(text: str) -> tuple:
    m = re.fullmatch(r"(SPEC-[A-Z0-9]+-[0-9]{3,})@([0-9]+\.[0-9]+):(REQ-[A-Z0-9]+-[0-9]{3,})#(Q[0-9]{2,})", text or "")
    if not m: raise LifecycleError(f"目標格式是 <spec_id>@<ver>:<REQ>#<Q>：{text!r}")
    return m.groups()

# ---------------------------------------------------------------- impact（第 6 章 §4）
def _scan_dir(c): return f"clarifications/{c['product']}/{c['functional_area']}/scans"

def load_scan(c: dict, scan_id: str) -> dict:
    hit = store.glob(f"clarifications/*/*/scans/*-{scan_id}.yaml")
    if not hit: raise LifecycleError(f"沒有掃描紀錄 {scan_id}")
    s = store.load(hit[0])
    if s["clr_id"] != c["clarification_id"]: raise LifecycleError(f"scan {scan_id} 屬於 {s['clr_id']}，不是 {c['clarification_id']}（第 6 章 §5.9）")
    if s["scan_id"] != scan_id or store.rel(hit[0]) != f"{_scan_dir(c)}/{c['clarification_id']}-{scan_id}.yaml": raise LifecycleError(f"掃描紀錄 {scan_id} 的位置或內容不一致")
    return s

def _given_targets(c: dict, texts) -> list:
    out = []
    for t in texts or []:
        sid, ver, rid, qid = parse_target(t); product, area = _spec_meta(sid)
        out.append({"product": product, "area": area, "spec_id": sid, "spec_version": ver, "requirement_id": rid, "question_id": qid, "given": True})
    return out

@operation.operation("clarification_impact")
def impact(clr_id: str, keywords=(), targets=(), by: str = "system") -> dict:
    """保存掃描紀錄：不帶 --target 時自動解析採用目標（附錄 A 6-8）；帶 --target 時以它們作為掃描輸入。"""
    c = clr.load(clr_id)
    if c["status"] == "WITHDRAWN": raise LifecycleError(f"{clr_id} 已撤回")
    rev = latest(c); kws = sorted({k for k in keywords if k})
    tg = _given_targets(c, targets) if targets else resolve_targets(c)
    units = scan_units(c, tg, "a6"); cands = scan_candidates(c, tg, kws, units, "a6")
    from . import ids
    sid = f"SCAN-{ids.ulid()}"                                                             # 全域唯一：--scan 指到別張 CLR 的紀錄時能明確拒絕（AC-10A-63）
    rec = {"scan_id": sid, "clr_id": clr_id, "answer_rev": rev["rev"], "keywords": kws, "targets": [_tgt_view(t) for t in tg], "scan_units": units,
           "rule_version": RULE_VERSION, "candidates": cands, "scanned_at": store.now(), "op_id": store.capturing().op_id}
    rec["sha256"] = sources.chash(rec)
    errs = schema.errors(rec, "spec/clarification-scan.schema.json")
    if errs: raise LifecycleError("掃描紀錄不符 schema：" + "; ".join(errs[:3]))
    store.save(f"{_scan_dir(c)}/{clr_id}-{sid}.yaml", rec)
    c.setdefault("scan_ids", []).append(sid); clr.save(c)
    store.audit(c.get("run_id"), by, "CLARIFICATION_IMPACT", f"{clr_id} {sid}：{len(cands)} 張候選、{len(units)} 個掃描單位")
    return rec

def _tgt_view(t):
    return {k: t[k] for k in ("product", "area", "spec_id", "spec_version", "requirement_id", "question_id") if k in t} | ({"via": t["via"]} if "via" in t else {})

# ---------------------------------------------------------------- apply（第 6 章 §5）
def _parse_conclusions(items) -> dict:
    out = {}
    for x in items or []:
        if "=" not in x: raise LifecycleError(f"--tc-conclusion 格式是 <TC-ID>=<結論>：{x!r}")
        tc, v = x.split("=", 1)
        if not (v in CONCLUSIONS or (v.startswith("deferred:") and v[len("deferred:"):].strip())):
            raise LifecycleError(f"{tc} 的結論只能是 updated、not_affected、retire_planned 或 deferred:<理由>（實際 {v!r}）")
        if tc in out: raise LifecycleError(f"{tc} 重複給了 --tc-conclusion（{out[tc]!r}、{v!r}）；每張 TC 只能有一個結論")
        out[tc] = v
    return out

def _parse_defer(items) -> dict:
    out = {}
    for x in items or []:
        if "=" not in x or not x.split("=", 1)[1].strip(): raise LifecycleError(f"--defer-target 格式是 <spec_id>@<ver>:<REQ>#<Q>=<理由>：{x!r}")
        t, reason = x.split("=", 1); parse_target(t)
        if t in out: raise LifecycleError(f"{t} 重複給了 --defer-target")
        out[t] = reason.strip()
    return out

def _keywords(c, keywords, scan_id, no_keyword_reason) -> tuple[list, dict]:
    kws = {k for k in keywords or [] if k}; meta = {"scan_reused": "none"}
    if scan_id:
        s = load_scan(c, scan_id); kws |= set(s["keywords"])
        meta = {"scan_id": scan_id, "scan_answer_rev": s["answer_rev"],
                "scan_reused": "full" if (s["answer_rev"] == latest(c)["rev"] and s["rule_version"] == RULE_VERSION) else "keywords_only", "_scan": s}
    reason = (no_keyword_reason or "").strip()
    if kws and reason: raise LifecycleError("最終關鍵字非空，又提供了 --no-keyword-reason：兩者互相矛盾（第 6 章 §5.9）")
    if not kws and not reason: raise LifecycleError("沒有最終關鍵字：請給 --keyword、--scan，或 --no-keyword-reason <理由>（第 6 章 §5.9）")
    if reason: meta["no_keyword_reason"] = reason
    return sorted(kws), meta

def _ra_reject_entry(run_id: str, target: str, c: dict) -> tuple[dict, str]:
    """a6b 的 --target：<APR>#<index>（附錄 A 6-5）。回傳 (目標, 錯誤)。"""
    m = re.fullmatch(r"(APR-[0-9]{4,})#([0-9]+)", target or "")
    if not m: return None, f"a6b 的 --target 格式是 <APR>#<resolutions 索引>：{target!r}"
    apr_id, idx = m.group(1), int(m.group(2))
    if not store.exists(f"approvals/{apr_id}.yaml"): return None, f"{apr_id} 不存在"
    a = store.load(f"approvals/{apr_id}.yaml"); d = a.get("decision") or {}
    if a.get("run_id") != run_id: return None, f"{apr_id} 不屬於落地 run {run_id}"
    if a["type"] != "RESOLVE_AMBIGUITY" or d.get("decision") != "reject": return None, f"{apr_id} 不是決議為 reject 的 RESOLVE_AMBIGUITY"
    res = d.get("resolutions") or []
    if idx >= len(res): return None, f"{apr_id} 沒有 resolutions[{idx}]"
    e = res[idx]; src = e.get("source")
    if not src or src.get("type") != "clarification" or src.get("clarification_id") != c["clarification_id"]:
        return None, f"{apr_id} resolutions[{idx}] 的 source 不是本 CLR（普通的 reject 不能作為 A6b 證據）"
    rev = latest(c)
    if (src["answer_rev"], src["answer_sha256"]) != (rev["rev"], rev["sha256"]): return None, f"{apr_id} resolutions[{idx}] 指向 rev {src['answer_rev']}，不是最新的 rev {rev['rev']}"
    errs, _ = sources.validate(src, at=(e["requirement_id"], e["question_id"]))
    if errs: return None, f"{apr_id} resolutions[{idx}] 的 source：{'; '.join(errs)}"
    run = store.load(f"runs/{run_id}/run.yaml")
    try: reqs = rm.requirements_of(rm.run_pin(run))
    except rm.RMError as ex: return None, str(ex)
    req = reqs.get(e["requirement_id"]); dp = next((x for x in (req or {}).get("decision_points") or [] if x["question_id"] == e["question_id"]), None)
    if dp is None: return None, f"{e['requirement_id']}/{e['question_id']} 不是落地 run 綁定 revision 中的決策點"
    scope = _dp_scope(req, dp); via = _via(c, rev, scope, dp.get("basis_hash"))
    if via is None: return None, f"{apr_id} resolutions[{idx}] 的 source 沒有通過 X16（scope 或 basis 不符）"
    product, area = _spec_meta(req["spec_id"])
    return {"product": product, "area": area, "spec_id": req["spec_id"], "spec_version": str(req["spec_version"]), "source": {"approval": apr_id, "resolution_index": idx},
            "requirement_id": e["requirement_id"], "question_id": e["question_id"], "scope": scope, "via": via, "entry": target}, None

def reference_history(c: dict) -> tuple[list, str]:
    """A7：全部歷史中引用本 CLR 任何 answer_rev 的位置（approval 包裝展開）；回傳 (位置, reference_scan_sha256)。"""
    cid = c["clarification_id"]; locs = []; scanned = []
    def hit(obj): return any(r.get("clarification_id") == cid for r in rm._clarification_refs(obj))
    for p in sorted(store.glob("artifacts/requirements/*/*/revisions/R*.yaml")):
        if p.name.endswith(".meta.yaml"): continue
        scanned.append([store.rel(p), store.sha256_file(p)])
        if hit(store.load(p)): locs.append(f"revision {store.rel(p)}")
    for p in sorted(store.glob("artifacts/*/*/*.yaml")):
        a = store.load(p)
        if a.get("artifact_type") != "BugDraft": continue
        scanned.append([store.rel(p), store.sha256_file(p)])
        if hit(a.get("payload")): locs.append(f"BugDraft {a['artifact_id']}")
    for p in sorted(store.glob("testcases/versions/*/v*.yaml")):
        scanned.append([store.rel(p), store.sha256_file(p)])
        v = store.load(p)
        if hit({"decision_refs": v.get("decision_refs"), "source_refs": v.get("source_refs")}): locs.append(f"TC {v['testcase_id']} v{v['version']}（{v['status']}）")
    for p in sorted(store.glob("approvals/APR-*.yaml")):
        a = store.load(p); scanned.append([store.rel(p), store.sha256_file(p)])
        for i, e in enumerate((a.get("decision") or {}).get("resolutions") or []):
            if hit({"source": e.get("source")}): locs.append(f"{a['approval_id']} resolutions[{i}]（{a['decision']['decision']}）")
    return locs, sources.chash(scanned)

def _apply_request(clr_id, path, by, **kw):
    return {"targets": {"clarification_ids": [clr_id]}, "params": operation.normalize({"path": path, "by": by, **kw})}

@operation.operation("clarification_apply", request=_apply_request)
def apply(clr_id: str, path: str, by: str, landed_in=(), targets=(), defer_targets=(), keywords=(), scan_id=None, no_keyword_reason=None,
          tc_conclusions=(), impact_reviewed=None) -> dict:
    """人工確認結案（第 6 章 §5）。任一檢查不成立就拒絕，CLR 不變。"""
    _human(by)
    c = clr.load(clr_id)
    if path not in ("a6", "a6b", "a7"): raise LifecycleError(f"--path 只能是 a6、a6b 或 a7：{path!r}")
    if c.get("kind") == "document_request": raise LifecycleError(f"{clr_id} 是文件索取單，依逐項 fulfill／waive-item 結案（第 6 章 §6）")
    if not (impact_reviewed or "").strip(): raise LifecycleError("--impact-reviewed 必填")
    landed_in = list(landed_in or []); targets = list(targets or []); defer = _parse_defer(defer_targets)
    # 2. 路徑和狀態、resolution、輸入一致（§5.2）
    need = {"a6": ("INCORPORATED",), "a6b": ("ANSWERED", "INCORPORATED"), "a7": ("ANSWERED",)}[path]
    if c["status"] not in need: raise LifecycleError(f"--path {path} 需要 CLR 狀態為 {'／'.join(need)}（實際 {c['status']}）")
    rev = latest(c)
    want_res = QUIET_RESOLUTIONS if path == "a7" else APPLIED_RESOLUTIONS
    if rev["resolution"] not in want_res: raise LifecycleError(f"--path {path} 需要最新答案的 resolution 為 {'／'.join(want_res)}（實際 {rev['resolution']}）")
    if path == "a7" and (landed_in or targets or defer): raise LifecycleError("--path a7 不接受 --landed-in、--target、--defer-target")
    if path == "a6b" and defer: raise LifecycleError("--path a6b 不接受 --defer-target")
    if path == "a6" and not landed_in: raise LifecycleError("--path a6 至少要一個 --landed-in")
    if path == "a6b" and (len(landed_in) != 1 or len(targets) != 1): raise LifecycleError("--path a6b 需要恰好一個 --landed-in 與一個 --target（<APR>#<索引>）")
    confirmed, deferred, ref_sha = [], [], None
    # 3. a6、a6b：目標解析、確認／延後、landed-in 檢查
    if path in ("a6", "a6b"):
        for rid in landed_in:
            if not store.exists(f"runs/{rid}/run.yaml"): raise LifecycleError(f"--landed-in {rid} 不存在")
            st = store.load(f"runs/{rid}/run.yaml")["status"]
            if st != "COMPLETED": raise LifecycleError(f"--landed-in {rid} 的狀態是 {st}，不是 COMPLETED")
            if path == "a6" and bug_rejected(rid): raise LifecycleError(f"--landed-in {rid} 的 Bug 已 REJECTED，不能作為 a6 的落地證據；答案只經 bug reject 路徑落地時改用 --path a6b，否則以其他 run 落地（附錄 A 6-37）")
    if path == "a6":
        resolved = {target_id(t): t for t in resolve_targets(c, landed_in)}
        unknown = [t for t in list(targets) + list(defer) if t not in resolved]
        if unknown: raise LifecycleError(f"指定的目標不在解析結果中：{unknown}（解析結果：{sorted(resolved) or '無'}）")
        missing = [t for t in resolved if t not in targets and t not in defer]
        if missing: raise LifecycleError(f"採用目標沒有被 --target 確認或 --defer-target 延後：{missing}")
        both = [t for t in targets if t in defer]
        if both: raise LifecycleError(f"目標不能同時確認又延後：{both}")
        confirmed = [resolved[t] for t in targets]; deferred = [{"target": t, "reason": r} for t, r in defer.items()]
        conf_ids = set(targets)
        for rid in landed_in:
            mine = {target_id(t) for t in run_targets(c, rid)} & conf_ids
            if not mine: raise LifecycleError(f"--landed-in {rid} 的產出不含任何被 --target 確認的目標（只含延後目標、目標不在 run 的範圍內，或引用的不是最新 answer_rev；第 6 章 §5.6）")
        tg_all = confirmed + [resolved[t] for t in defer]
    elif path == "a6b":
        run = store.load(f"runs/{landed_in[0]}/run.yaml")
        if run["workflow_id"] != "spec-to-bug": raise LifecycleError(f"--path a6b 的落地 run 必須是 spec-to-bug（實際 {run['workflow_id']}）")
        if resolve_targets(c): raise LifecycleError(f"{clr_id} 另有 revision 上的採用目標，請改用 --path a6（a6b 只用於答案僅經 bug reject 路徑落地；附錄 A 6-6）")
        t, err = _ra_reject_entry(landed_in[0], targets[0], c)
        if err: raise LifecycleError(err)
        confirmed = [t]; tg_all = [t]
    else:
        locs, ref_sha = reference_history(c)
        if locs: raise LifecycleError(f"--path a7 需要全部歷史都沒有引用 {clr_id}：{locs}")
        tg_all = []
    # 5. 最終關鍵字與 scan
    kws, kmeta = _keywords(c, keywords, scan_id, no_keyword_reason)
    # 6. 鎖內重新掃描；每張候選都要有結論
    units = scan_units(c, tg_all, path); cands = scan_candidates(c, tg_all, kws, units, path)
    concl = _parse_conclusions(tc_conclusions); cand_ids = {x["tc_id"] for x in cands}
    stray = sorted(set(concl) - cand_ids)
    if stray: raise LifecycleError(f"這些 TC 不在重新掃描的候選中，不能下結論（附錄 A 6-17）：{stray}；候選：{sorted(cand_ids) or '無'}")
    lack = sorted(cand_ids - set(concl))
    if lack: raise LifecycleError(f"這些候選 TC 缺少 --tc-conclusion：{lack}（重新掃描的候選：{sorted(cand_ids)}）")
    scan_diff = None
    if kmeta.get("_scan") and kmeta["scan_reused"] == "full":
        old = {(x["tc_id"], x["active_version"]) for x in kmeta["_scan"]["candidates"]}; now = {(x["tc_id"], x["active_version"]) for x in cands}
        if old != now: scan_diff = {"only_in_scan": sorted(old - now), "only_now": sorted(now - old)}
    # 7. 寫入：狀態 → landing → history（摘要）
    scan_sha = sources.chash({"units": units, "keywords": kws, "candidates": cands})
    landing = {"type": "applied", "path": path, "answer_rev": rev["rev"],
               **({"landed_in": landed_in} if path != "a7" else {}),
               "targets_confirmed": [_tgt_view(t) | ({"entry": t["entry"]} if "entry" in t else {}) for t in confirmed],
               **({"targets_deferred": deferred} if path == "a6" else {}),
               "scan_units": units, **({"final_keywords": kws} if kws else {"no_keyword_reason": kmeta["no_keyword_reason"]}),
               **{k: v for k, v in kmeta.items() if k in ("scan_id", "scan_answer_rev")}, "scan_reused": kmeta["scan_reused"],
               "rule_version": RULE_VERSION, "candidates": cands, "conclusions": [{"tc_id": t, "conclusion": concl[t]} for t in sorted(concl)],
               "scan_sha256": scan_sha, **({"reference_scan_sha256": ref_sha} if ref_sha else {}),
               "impact_reviewed": impact_reviewed.strip(), "op_id": store.capturing().op_id, "at": store.now(), "by": by}
    state.apply("clarification", c, "APPLIED", by, f"apply --path {path}", c.get("run_id"),
                note=f"{len(cands)} 張候選；確認 {len(confirmed)}、延後 {len(deferred)} 個目標；{impact_reviewed.strip()}")
    c.setdefault("landings", []).append(landing)
    clr.save(c); store.audit(c.get("run_id"), by, "APPLY_CLARIFICATION", f"{clr_id} --path {path}：{len(cands)} 張候選")
    return {"clarification_id": clr_id, "path": path, "candidates": cands, "scan_diff": scan_diff, "scan_reused": kmeta["scan_reused"]}

# ---------------------------------------------------------------- 文件索取單（第 6 章 §6）
def _strip_name(fn: str) -> str:
    stem = pathlib.Path(fn).stem if fn else ""
    return re.sub(r"_v(\d+|NN)$", "", stem, flags=re.I)

def _match(doc_entry: dict, item: dict) -> str | None:
    """名稱比對（§6.3）：有效名稱（n1 外部檔名去副檔名與版本、n2 title；正規化後非空）以子字串出現在 item.name 或 cited_at.text 中。"""
    names = []
    fn = ((doc_entry.get("source") or {}).get("external_filename")) or ""
    n1 = spec_ops.normalize_title(_strip_name(fn)); n2 = spec_ops.normalize_title(doc_entry.get("title") or "")
    names = [n for n in (n1, n2) if n]
    hay = [spec_ops.normalize_title(item.get("name") or ""), spec_ops.normalize_title((item.get("cited_at") or {}).get("text") or "")]
    hay = [h for h in hay if h]
    for n in names:
        if any(n in h for h in hay): return n
    return None

def _doc_entry(sid, ver):
    p, spec, e = spec_ops.find_entry(sid, ver)
    return {**e, "title": e.get("title") or spec.get("title")}

def fulfillment_status(item: dict) -> tuple[bool, str]:
    """最新一筆 fulfillment 的重新驗證（§6.6）。回傳 (有效, 原因)。"""
    fs = item.get("fulfillments") or []
    if not fs: return False, "沒有 fulfillment"
    f = fs[-1]; d, t = f["document_pin"], f["target_pin"]
    try: spec_ops.verify_pin(d["spec_id"], d["spec_version"], d["content_hash"])
    except spec_ops.SpecError as e: return False, f"文件版本失效：{e}"
    try: _, _, te = spec_ops.find_entry(t["spec_id"], t["spec_version"])
    except spec_ops.SpecError as e: return False, f"目標版本失效：{e}"
    refs_ = {(r["spec_id"], r["spec_version"], r["content_hash"]) for r in te.get("references") or []}
    if (d["spec_id"], d["spec_version"], d["content_hash"]) not in refs_: return False, f"{t['spec_id']}@{t['spec_version']} 目前的宣告（decl_rev {spec_ops.decl_rev(te)}）已不包含 {d['spec_id']}@{d['spec_version']}"
    m = f.get("match") or {}
    if m.get("method") not in ("name_match", "human_mapping") or (m["method"] == "human_mapping" and not (m.get("reason") or "").strip()): return False, "對應方式的紀錄不完整"
    return True, ""

def final_judgment(c: dict, by: str, note: str, approval_items=None):
    """§6.6、§6.7：A9 → WITHDRAWN；否則全部有效 fulfillment 或 waived → APPLIED（A8，追加 landing）；其他不轉換。
    approval_items：核准的 waive_missing 列出的項目；A9 只在**這張核准**涵蓋全部項目時成立（先前以 waive-item 豁免的項目不算）。"""
    items = c.get("document_items") or []
    if not items or c["status"] not in ("OPEN", "ASKED"): return
    valid = {it["item_id"]: fulfillment_status(it)[0] for it in items}
    if approval_items is not None and {it["item_id"] for it in items} <= set(approval_items) and not any(valid.values()):
        state.apply("clarification", c, "WITHDRAWN", "system", "A9 waive_missing", note=note); return
    if all(valid[it["item_id"]] or it["status"] == "waived" for it in items):
        state.apply("clarification", c, "APPLIED", by, "A8", c.get("run_id"), note=note)
        c.setdefault("landings", []).append({"type": "applied", "path": "a8", "items": [{"item_id": it["item_id"], "result": "fulfilled" if valid[it["item_id"]] else "waived"} for it in items],
                                             "op_id": store.capturing().op_id, "at": store.now(), "by": by})

def _doc_clr(clr_id):
    c = clr.load(clr_id)
    if c.get("kind") != "document_request": raise LifecycleError(f"{clr_id} 不是文件索取單")
    if c["status"] not in ("OPEN", "ASKED"): raise LifecycleError(f"{clr_id} 狀態 {c['status']}，不能再處理文件項目")
    return c

def _item(c, item_id):
    it = next((x for x in c.get("document_items") or [] if x["item_id"] == item_id), None)
    if it is None: raise LifecycleError(f"{c['clarification_id']} 沒有項目 {item_id}")
    return it

def _vkey(v): return tuple(int(x) for x in str(v).split("."))

@operation.operation("clarification_fulfill")
def fulfill(clr_id: str, item_id: str, document: str, by: str, mapping_reason: str | None = None) -> dict:
    """§6.2：document 已匯入、hash 相符；在 CLR 目標 spec（同 spec_id、版本 ≥ CLR 的版本）某版本目前的宣告中；名稱比對成立或附人工對應理由。"""
    _human(by)
    c = _doc_clr(clr_id); it = _item(c, item_id)
    sid, ver = spec_ops.parse_pin(document)
    try: dpin = spec_ops.verify_pin(sid, ver)
    except spec_ops.SpecError as e: raise LifecycleError(f"文件 {document}：{e}")
    target = None
    for v in sorted((x["spec_version"] for x in store.load(spec_ops.spec_path(c["spec_id"]))["versions"]), key=_vkey):
        if _vkey(v) < _vkey(c["spec_version"]): continue
        _, _, te = spec_ops.find_entry(c["spec_id"], v)
        if any((r["spec_id"], r["spec_version"], r["content_hash"]) == (dpin["spec_id"], dpin["spec_version"], dpin["content_hash"]) for r in te.get("references") or []):
            target = (spec_ops.verify_pin(c["spec_id"], v), spec_ops.decl_rev(te)); break
    if target is None: raise LifecycleError(f"{document} 沒有在 {c['spec_id']}（v{c['spec_version']} 以後）任何版本目前的宣告中被引用；請先 spec reference add")
    matched = _match(_doc_entry(sid, ver), it); reason = (mapping_reason or "").strip()
    if matched is None and not reason: raise LifecycleError(f"{document} 的名稱和項目 {item_id}（{it['name']}）比對不成立；請附 --mapping-reason 走人工對應（§6.3）")
    match = {"method": "name_match", "matched_text": matched, "by": by} if matched is not None and not reason else {"method": "human_mapping", "reason": reason, "by": by}
    rec = {"item_id": item_id, "document_pin": dpin, "target_pin": target[0], "target_decl_rev": target[1], "match": match, "op_id": store.capturing().op_id, "at": store.now()}
    rec["sha256"] = sources.chash(rec)
    it.setdefault("fulfillments", []).append(rec); it["status"] = "fulfilled"
    c["history"].append({"at": store.now(), "from_status": c["status"], "to_status": c["status"], "by": by, "trigger": f"fulfill {item_id}", "note": f"{document}（{match['method']}）"})
    final_judgment(c, by, f"fulfill {item_id}")
    clr.save(c); store.audit(c.get("run_id"), by, "FULFILL_DOCUMENT_ITEM", f"{clr_id} {item_id} ← {document} → {c['status']}")
    return c

@operation.operation("clarification_waive_item")
def waive_item(clr_id: str, item_id: str, reason: str, by: str) -> dict:
    _human(by)
    if not (reason or "").strip(): raise LifecycleError("--reason 必填")
    c = _doc_clr(clr_id); it = _item(c, item_id)
    it["status"] = "waived"; it.setdefault("waive_records", []).append({"by": by, "at": store.now(), "source": "waive-item", "reason": reason.strip()})
    c["history"].append({"at": store.now(), "from_status": c["status"], "to_status": c["status"], "by": by, "trigger": f"waive-item {item_id}", "note": reason.strip()})
    final_judgment(c, by, f"waive-item {item_id}")
    clr.save(c); store.audit(c.get("run_id"), by, "WAIVE_DOCUMENT_ITEM", f"{clr_id} {item_id} → {c['status']}")
    return c

def waive_items_by_approval(clr_id, item_ids, approval_id, by):
    """核准操作套用 waive_missing（由 approve 呼叫，已在操作中）：列出的項目標為 waived，再做最後判定（§6.6、§6.7）。"""
    c = clr.load(clr_id)
    if c["status"] not in ("OPEN", "ASKED"): return c
    for it in c.get("document_items") or []:
        if it["item_id"] in item_ids and it["status"] != "waived":
            it["status"] = "waived"; it.setdefault("waive_records", []).append({"by": by, "at": store.now(), "source": f"approval {approval_id}"})
    c["history"].append({"at": store.now(), "from_status": c["status"], "to_status": c["status"], "by": by, "trigger": f"waive_missing {approval_id}", "note": f"豁免項目 {sorted(item_ids)}"})
    final_judgment(c, by, f"{approval_id} 的 waive_missing", approval_items=list(item_ids))
    clr.save(c); store.audit(c.get("run_id"), by, "WAIVE_DOCUMENT_ITEMS", f"{clr_id} {sorted(item_ids)} by {approval_id} → {c['status']}")
    return c

# ---------------------------------------------------------------- 唯讀查詢（第 6 章 §7）
def show(clr_id: str) -> dict:
    c = clr.load(clr_id); out = {"note": READONLY_NOTE, "clarification_id": clr_id, "kind": c.get("kind", "spec_question"), "status": c["status"],
                                 "answer_revisions": [{k: r[k] for k in ("rev", "resolution", "answered_by", "answered_at", "sha256")} for r in c.get("answer_revisions") or []],
                                 "landings": [{k: v for k, v in l.items() if k not in ("candidates",)} for l in c.get("landings") or []]}
    follow = []
    for l in c.get("landings") or []:
        if l.get("type") != "applied": continue
        for x in l.get("conclusions") or []:
            if x["conclusion"] == "retire_planned" or x["conclusion"].startswith("deferred:"): follow.append({"tc_id": x["tc_id"], "conclusion": x["conclusion"]})
        for d in l.get("targets_deferred") or []: follow.append({"target": d["target"], "deferred_reason": d["reason"]})
    out["follow_ups"] = follow
    if c.get("document_items"):
        out["document_items"] = []
        for it in c["document_items"]:
            ok, why = fulfillment_status(it)
            out["document_items"].append({"item_id": it["item_id"], "name": it["name"], "status": it["status"],
                                          "fulfillment": "有效" if ok else (f"失效：{why}" if it.get("fulfillments") else "—")})
    return out

def stale_tcs(clr_id: str) -> dict:
    """依賴本 CLR、但尚未依最新答案處理的 TC（第 6 章 §7；不保證完整）。掃描規則同 (a)～(d)：目標＝各 spec 版本最新 revision 中採用本 CLR
    任一 answer_rev 的決策點（A5 之後 revision 還沒重新納入時仍能找到依賴舊答案的 TC），加上歷次 applied landing 確認與延後的目標；單位依 (product, area)；另外列出任何單位中 decision_refs 指向本 CLR 舊 rev 的 TC。
    關鍵字取最近一次 applied landing（無關鍵字結案時為空集合）；完全沒有 applied landing 時才取最近一次掃描紀錄（附錄 A 6-19）。"""
    c = clr.load(clr_id); rev = (c.get("answer_revisions") or [{}])[-1]; cid = clr_id
    applied = next((l for l in reversed(c.get("landings") or []) if l.get("type") == "applied"), None)
    kws = list(applied.get("final_keywords") or []) if applied else []      # 無關鍵字結案（no_keyword_reason）也以該 landing 為準，不退回舊掃描
    if applied is None and c.get("scan_ids"):
        try: kws = load_scan(c, c["scan_ids"][-1])["keywords"]
        except LifecycleError: kws = []
    targets = {target_id(t): t for t in _adopting_points(c)}
    for l in c.get("landings") or []:
        if l.get("type") != "applied": continue
        for t in l.get("targets_confirmed") or []:
            if "requirement_id" in t and "question_id" in t: targets.setdefault(target_id(t), t)
        for d in l.get("targets_deferred") or []:
            sid_ver, rq = d["target"].split(":", 1); sid, ver = sid_ver.split("@"); rid, qid = rq.split("#"); product, area = _spec_meta(sid)
            targets.setdefault(d["target"], {"product": product, "area": area, "spec_id": sid, "spec_version": ver, "requirement_id": rid, "question_id": qid})
    tg = list(targets.values()); units = scan_units(c, tg, "a6")
    found = {x["tc_id"]: x for x in (scan_candidates(c, tg, kws, units, "a6") if rev else [])}
    for tc_id, ver, tc, _ in _active_tcs():
        for d in tc.get("decision_refs") or []:
            br = d.get("basis_ref") or {}
            eb = _eb({**br, "quote": "x"}, (d["requirement_id"], d["question_id"])) if br else None
            if eb and eb[0] == "clarification" and eb[1] == cid and eb[2] != rev.get("rev"):
                x = found.setdefault(tc_id, {"tc_id": tc_id, "active_version": ver, "reasons": []})
                x["reasons"] = sorted(set(x["reasons"]) | {f"stale_decision_ref:{d['requirement_id']}#{d['question_id']}"})
    out = [{k: x[k] for k in ("tc_id", "active_version", "reasons")} for _, x in sorted(found.items())]
    return {"note": "不保證完整：只依 decision_refs、requirement_ids 與最近一次的關鍵字比對；" + READONLY_NOTE, "clarification_id": cid, "latest_rev": rev.get("rev"), "tcs": out}
