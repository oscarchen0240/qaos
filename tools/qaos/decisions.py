"""決策點的推導與檢查（需求 A 第 1 章 FIX-05 §3）：不合法組合 X1～X18、推導旗標、有效狀態 E1～E6、有效等級、路由 R0～R9。

- 讀取用（不寫檔）。G-SPEC 以 check() 擋下矛盾資料；持久化時以 stamp() 寫入 runtime 推導的欄位（basis_hash、derived、
  ambiguity.level／raised_level、rejection_contract.defined）。
- 有 decision_points 的需求是新資料；沒有的是 E6，維持現行行為（R0）。"""
from . import store, sources, spec_ops

LEVELS = ("none", "minor", "major", "critical")
DEFINED = ("defined_in_target", "defined_in_reference", "defined_by_decision")
DRAFT_ROUTES = ("R3", "R5", "R7", "R9")
KIND = {"E2": "conflict_resolution", "E3": "document_request", "E4": "spec_question", "E5": "spec_question"}
ANSWERED = ("ANSWERED", "INCORPORATED", "APPLIED")
OUTCOMES_FOR = {"E2": ("select_interpretation",), "E3": ("select_interpretation", "waive_missing"), "E4": ("select_interpretation",), "E5": ("select_interpretation",)}

def lmax(levels) -> str:
    return max(levels, key=LEVELS.index, default="none")

def is_new(req: dict) -> bool:
    return bool(req.get("decision_points"))

class Ctx:
    """推導所需的分析脈絡：目標 SpecPin、basis_hash、目標的 references_status、閱讀閉包（派發包提供）。"""
    def __init__(self, target_pin: dict, basis_hash: str, references_status: str, closure: list, loader=None):
        self.target_pin, self.basis_hash, self.references_status, self.closure = target_pin, basis_hash, references_status, closure
        self.target = (target_pin["spec_id"], str(target_pin["spec_version"]))
        self.loader = loader or sources.StoreLoader()
        self.depth1_normative = {_pk(n) for n in closure if n["role"] == "normative" and n["depth"] == 1}
        self.closure_pins = {_pk(n) for n in closure}

    @classmethod
    def from_packet(cls, packet: dict, loader=None) -> "Ctx":
        return cls(packet["target"], packet["basis_hash"], packet.get("references_status") or "undeclared", packet["closure"], loader)

    @classmethod
    def from_spec(cls, sid: str, ver: str, loader=None) -> "Ctx":
        _, _, e = spec_ops.find_entry(sid, ver)
        return cls(spec_ops.verify_pin(sid, ver), sources.basis_hash(sources.basis(sid, ver)), spec_ops.references_status(e), sources.reading_closure(sid, ver), loader)

def _pk(p: dict) -> tuple:
    return (p["spec_id"], str(p["spec_version"]), p["content_hash"])

def scope_of(req: dict, dp: dict) -> dict:
    return {"spec_id": req["spec_id"], "requirement_id": req["requirement_id"], "subject": dp["subject"], "role_scope": dp["role_scope"], "params": dp["params"]}

# ---------------------------------------------------------------- 豁免（§3.2 waiver_valid）
def _wid(item: dict) -> tuple:
    if "pin" in item: return ("pin",) + _pk(item["pin"])
    c = item["cited_at"]
    return ("missing", c["spec_id"], str(c["spec_version"]), c["content_hash"], c["line"], item["name"])

def dp_items(dp: dict) -> set:
    """決策點可被豁免的項目身分：缺檔（cited_at 的 SpecPin＋line＋name）與未查參考（pin）。"""
    cov = dp["coverage"]
    return {_wid(m) for m in cov.get("missing_sources") or []} | {_wid(u) for u in cov.get("unconsulted_normative") or []}

def is_index(v) -> bool:
    """索引與行號只接受整數表示且不小於 0（附錄 A 3-24、1-37）：bool、0.0 這類浮點寫法都是形狀錯誤（不轉換、不截斷）。"""
    return type(v) is int and v >= 0

def waived_shape_errors(items) -> list[str]:
    """豁免項目的形狀（附錄 A 1-37）：每項是物件，二選一——{cited_at: {spec_id, spec_version, content_hash, line（正整數）, text?}, name}
    或 {pin: SpecPin}。形狀錯誤回報為結構錯誤，不拋例外。"""
    if not isinstance(items, list): return ["waived 必須是清單"]
    errs = []
    for k, it in enumerate(items):
        if not isinstance(it, dict): errs.append(f"waived[{k}] 必須是物件"); continue
        if "cited_at" in it:
            c = it["cited_at"]
            if not isinstance(c, dict) or not all(isinstance(c.get(x), str) for x in ("spec_id", "spec_version", "content_hash")):
                errs.append(f"waived[{k}] 的 cited_at 必須是含 spec_id、spec_version、content_hash、line 的物件"); continue
            if not (is_index(c.get("line")) and c["line"] >= 1):
                errs.append(f"waived[{k}]（{it.get('name')!r}）的 cited_at.line 必須是正整數表示（實際 {c.get('line')!r}）")
            if not isinstance(it.get("name"), str) or not it["name"].strip(): errs.append(f"waived[{k}] 的 cited_at 項目必須有 name")
        elif "pin" in it:
            pn = it["pin"]
            if not isinstance(pn, dict) or not all(isinstance(pn.get(x), str) for x in ("spec_id", "spec_version", "content_hash")):
                errs.append(f"waived[{k}] 的 pin 必須是 SpecPin 物件")
        else: errs.append(f"waived[{k}] 必須有 cited_at＋name 或 pin")
    return errs

def waiver_errors(w: dict, req: dict, dp: dict, loader) -> list[str]:
    if not is_index(w.get("resolution_index")): return [f"resolution_index 必須是整數表示（實際 {w.get('resolution_index')!r}）"]
    shape = waived_shape_errors(w.get("waived"))
    if shape: return shape
    a = loader.approval(w["approval_id"])
    if a is None: return [f"{w['approval_id']} 不存在"]
    d = a.get("decision") or {}
    if a["type"] != "RESOLVE_AMBIGUITY" or d.get("decision") not in ("approve", "override"):
        return [f"{w['approval_id']} 不是決議為 approve 或 override 的 RESOLVE_AMBIGUITY"]
    errs = []
    if sources.chash(d) != w["decision_sha256"]: errs.append(f"{w['approval_id']} 的 decision_sha256 不符")
    res = d.get("resolutions") or []
    if w["resolution_index"] >= len(res): return errs + [f"{w['approval_id']} 沒有 resolutions[{w['resolution_index']}]"]
    entry = res[w["resolution_index"]]
    if (entry["requirement_id"], entry["question_id"]) != (req["requirement_id"], dp["question_id"]):
        errs.append(f"條目是 {entry['requirement_id']}/{entry['question_id']}，不是本決策點")
    if entry["outcome"] != "waive_missing": errs.append(f"條目的 outcome 是 {entry['outcome']}，不是 waive_missing")
    mine, approved = dp_items(dp), set()
    for it in entry.get("waived") or []:
        try: approved.add(_wid(it))
        except (KeyError, TypeError): pass
    for it in w["waived"]:
        k = _wid(it)
        if k not in mine: errs.append(f"豁免項目 {it.get('name') or it.get('pin')} 不完全等於本決策點的任何缺檔或未查參考（只有名稱相同不算）")
        elif k not in approved: errs.append(f"豁免項目 {it.get('name') or it.get('pin')} 不在核准條目的 waived 中")
    return errs

# ---------------------------------------------------------------- 決策點檢查（§3.4）與推導（§3.2、§3.3）
def _route(state: str, eff: str) -> str:
    if state == "E1": return "R1"
    hi = eff == "critical"
    return {"E2": ("R2", "R3"), "E3": ("R4", "R5"), "E4": ("R6", "R7"), "E5": ("R8", "R9")}[state][hi]

def _ref_errs(ref, ctx, at) -> list[str]:
    errs, _ = sources.validate(ref, target=ctx.target, at=at, loader=ctx.loader)
    return errs

def _x15(src: dict, at, loader) -> list[str]:
    """resolution.source 的 X15（類型、決議、條目、outcome、rationale、巢狀；clarification 型要已回答）。"""
    if src.get("type") == "spec": return ["resolution.source 只能是 clarification 或 approval 型"]
    if src.get("type") == "clarification":
        c = loader.clarification(src.get("clarification_id"))
        if c is not None and c["status"] not in ANSWERED: return [f"{src['clarification_id']} 是 {c['status']}，不是 ANSWERED、INCORPORATED 或 APPLIED"]
        return []
    entry, errs = sources.resolution_entry(src, loader, at)
    if errs: return errs
    out = []
    if entry["outcome"] != "select_interpretation": out.append(f"{src['approval_id']} resolutions[{src['resolution_index']}] 的 outcome 是 {entry['outcome']}，不是 select_interpretation")
    if not (entry.get("rationale") or "").strip(): out.append(f"{src['approval_id']} resolutions[{src['resolution_index']}] 缺 rationale")
    return out

def _latest_rev_errs(ref, at, loader) -> list[str]:
    """附錄 A 3-18：新的 revision 不得以舊的 answer_rev 為 effective_basis。"""
    try: eb = sources.effective_basis(ref, at=at, loader=loader)
    except sources.SourceError: return []                                  # 無法解析的來源已由 X10／X12／X15 回報
    if eb[0] != "clarification": return []
    c = loader.clarification(eb[1]); revs = (c or {}).get("answer_revisions") or []
    if revs and eb[2] != len(revs) - 1: return [f"{eb[1]} 的最新答案是 rev {len(revs) - 1}，不能再以 rev {eb[2]} 為依據（改引用最新 rev，或標為未解決）"]
    return []

def check_dp(req: dict, dp: dict, ctx: Ctx) -> list[str]:
    rid, qid = req["requirement_id"], dp["question_id"]; at = (rid, qid); tag = f"{rid}/{qid}"
    out = []
    def x(n, msg): out.append(f"X{n}：{tag} {msg}")
    b, lvl, res, cov = dp["basis"], dp["level"], dp.get("resolution"), dp["coverage"]
    defined = b in DEFINED; sides = dp.get("conflict_sides") or []; kr = dp.get("known_rules") or []
    if dp["role_scope"] == []: x(18, "role_scope 是空陣列（與角色無關請寫 [\"*\"]）")
    if "*" in dp["role_scope"] and dp["role_scope"] != ["*"]: x(18, "role_scope 的 * 不得和具名角色混用")
    if defined and lvl in ("major", "critical"): x(1, f"basis {b} 的 level 不能是 {lvl}（真有疑慮應為 conflict）")
    if b == "conflict" and lvl in ("none", "minor"): x(2, f"conflict 的 level 至少是 major（實際 {lvl}）")
    if b == "conflict" and (len(sides) < 2 or not (dp.get("conflict_note") or "").strip()): x(3, "conflict 必須有至少兩筆 conflict_sides 和 conflict_note")
    if b == "undefined" and lvl == "none": x(4, "undefined 的 level 至少是 minor")
    if b == "undefined" and any(u["reason"] == "out_of_scope" for u in cov["unconsulted_normative"]): x(5, "undefined 但有 out_of_scope 的未查參考（改用 unavailable 或去查）")
    if defined and not kr: x(6, f"basis {b} 但 known_rules 是空的")
    if defined and res is not None: x(7, f"basis {b} 不需要 resolution")
    if res is not None and "source" not in res: x(13, "resolution 沒有 source" + ("，卻帶有其他子欄位" if res else ""))
    if res is not None and not defined:
        idx = res.get("adopted_side_index")
        if idx is not None and not is_index(idx): x(11, f"adopted_side_index 必須是 null 或整數表示（實際 {idx!r}）"); idx = None
        if b == "undefined" and idx is not None: x(11, "basis 為 undefined 時 adopted_side_index 必須是 null")
        if b == "conflict" and idx is not None and not (0 <= idx < len(sides)): x(11, f"adopted_side_index {idx} 超出 conflict_sides 範圍（{len(sides)} 筆）")
    for u in cov["unconsulted_normative"]:
        if _pk(u["pin"]) not in ctx.depth1_normative: x(17, f"unconsulted_normative 的 {u['pin']['spec_id']}@{u['pin']['spec_version']} 不是派發包中 depth=1 的 normative 參考")
    # coverage 本身（抄自目標、查閱的 pin、缺檔的引用處）
    if cov["references_status"] != ctx.references_status: out.append(f"G-SPEC：{tag} coverage.references_status 是 {cov['references_status']}，但目標版本是 {ctx.references_status}（必須抄自目標版本）")
    for p in cov["consulted"]:
        if _pk(p) != _pk(ctx.target_pin) and _pk(p) not in ctx.closure_pins: out.append(f"G-SPEC：{tag} coverage.consulted 的 {p['spec_id']}@{p['spec_version']} 不是目標，也不在派發包的閉包內")
    for m in cov["missing_sources"]:
        c = m["cited_at"]
        if not (is_index(c["line"]) and c["line"] >= 1):
            out.append(f"G-SPEC：{tag} 缺檔 {m['name']!r} 的 cited_at.line 必須是正整數表示（實際 {c['line']!r}）"); continue
        try:
            spec_ops.verify_pin(c["spec_id"], c["spec_version"], c["content_hash"])
            p_, _, e = spec_ops.find_entry(c["spec_id"], c["spec_version"]); lines = store.read_text(p_.parent / e["file"]).split("\n")
            if not (1 <= c["line"] <= len(lines)) or not sources.quote_in(c["text"], lines[c["line"] - 1]):
                out.append(f"G-SPEC：{tag} 缺檔 {m['name']!r} 的引用處：第 {c['line']} 行沒有「{c['text']}」")
        except spec_ops.SpecError as ex: out.append(f"G-SPEC：{tag} 缺檔 {m['name']!r} 的引用處：{ex}")
    # SourceRef 本身（X10）、resolution 來源（X15）、basis 對應（X12）、適用性（X16）、最新答案（3-18）
    src = (res or {}).get("source")
    x15 = _x15(src, at, ctx.loader) if src is not None else []
    for m in x15: x(15, m)
    for field, refs_ in (("known_rules", kr), ("conflict_sides", sides), ("resolution.source", [src] if src is not None and not x15 else [])):
        for i, r in enumerate(refs_):
            for m in _ref_errs(r, ctx, at): x(10, f"{field}[{i}]：{m}")
    if b == "defined_in_target" and not any(r.get("type") == "spec" and _pk(r) == _pk(ctx.target_pin) for r in kr):
        x(12, "defined_in_target 的 known_rules 至少要有一筆目標 spec 的 spec 型來源")
    if b == "defined_in_reference" and not any(r.get("type") == "spec" and _pk(r) != _pk(ctx.target_pin) and _pk(r) in ctx.closure_pins for r in kr):
        x(12, "defined_in_reference 的 known_rules 至少要有一筆閉包內、不是目標的 spec 型來源")
    if b == "defined_by_decision" and not any(r.get("type") in ("clarification", "approval") for r in kr):
        x(12, "defined_by_decision 的 known_rules 至少要有一筆 clarification 或 approval 型來源")
    if b == "defined_by_decision":                                         # approval 型依據只能是 select_interpretation 條目（名詞表 effective_basis）
        for i, r in enumerate(kr):
            if r.get("type") != "approval": continue
            entry, errs = sources.resolution_entry(r, ctx.loader, at)
            if entry is not None and entry["outcome"] != "select_interpretation":
                x(12, f"known_rules[{i}] 指向的 {r['approval_id']} resolutions[{r['resolution_index']}] 是 {entry['outcome']}，不是 select_interpretation，不能作為依據")
    decisive = [r for r in kr if r.get("type") in ("clarification", "approval")] if b == "defined_by_decision" else []
    if src is not None and not x15 and b in ("conflict", "undefined"): decisive.append(src)
    for r in decisive:
        for m in sources.x16(r, scope_of(req, dp), ctx.basis_hash, loader=ctx.loader, at=at): x(16, m)
        out.extend(f"附錄 A 3-18：{tag} {m}" for m in _latest_rev_errs(r, at, ctx.loader))
    for i, w in enumerate(cov["waivers"]):
        for m in waiver_errors(w, req, dp, ctx.loader): x(14, f"waivers[{i}]：{m}")
    return out

def derive_dp(req: dict, dp: dict, ctx: Ctx) -> dict:
    """在 check_dp 沒有錯誤的前提下推導（§3.2、§3.3、§3.5）。"""
    b, lvl, res, cov = dp["basis"], dp["level"], dp.get("resolution"), dp["coverage"]
    resolved = b in ("conflict", "undefined") and res is not None and "source" in res
    waived = set()
    for w in cov["waivers"]:
        if not waiver_errors(w, req, dp, ctx.loader): waived |= {_wid(it) for it in w["waived"]}
    gaps = [_wid(m) for m in cov["missing_sources"]] + [_wid(u) for u in cov["unconsulted_normative"] if u["reason"] == "unavailable"]
    gap_missing = any(g not in waived for g in gaps)
    gap_unverified = ctx.references_status == "undeclared"                  # 附錄 A 1-17：第一批沒有引用候選紀錄
    if b in DEFINED: state, eff = "E1", lvl
    elif resolved: state, eff = "E1", "none"
    elif b == "conflict": state, eff = "E2", lvl
    elif gap_missing: state, eff = "E3", lvl
    elif not gap_unverified: state, eff = "E4", lvl
    else: state, eff = "E5", lvl
    d = {"state": state, "effective_level": eff, "route": _route(state, eff), "resolved": resolved, "gap_missing": gap_missing, "gap_unverified": gap_unverified}
    if state == "E1" and b == "conflict": d["resolved_conflict"] = True
    return d

def check(req: dict, ctx: Ctx) -> tuple[list[str], dict | None]:
    """一條需求的 G-SPEC 檢查與推導。回傳 (錯誤, 推導)；舊資料（沒有 decision_points）回傳 ([], None)。"""
    if not is_new(req): return [], None
    dps = req["decision_points"]; rid = req["requirement_id"]; errs = []
    qids = [dp["question_id"] for dp in dps]
    errs += [f"G-SPEC：{rid} 的 question_id {q} 重複" for q in sorted({q for q in qids if qids.count(q) > 1})]
    for dp in dps: errs += check_dp(req, dp, ctx)
    if errs: return errs, None
    der = {dp["question_id"]: derive_dp(req, dp, ctx) for dp in dps}
    for dp in dps:
        if der[dp["question_id"]]["state"] == "E3" and not dp["coverage"]["missing_sources"]:
            errs.append(f"附錄 A 1-19：{rid}/{dp['question_id']} 推導為缺文件（E3），但沒有 missing_sources；文件索取單至少要有一個正文引用處。"
                        "未查參考標為 unavailable 時：目標正文有提到它，就把該行列入 missing_sources；正文沒有提到它，不得捏造引用處——"
                        "已宣告的參考一定已匯入，請停下由人處理（重新讀取後取消此 run 重新分析，或移除該引用宣告）")
    eff_max = lmax(d["effective_level"] for d in der.values()); raised = lmax(dp["level"] for dp in dps)
    rr = [dp for dp in dps if dp["topic"] == "rejection_response"]
    rej = all(der[dp["question_id"]]["state"] == "E1" for dp in rr) if rr else None
    rc = req.get("rejection_contract")
    if rej is None and rc is not None: errs.append(f"X8：{rid} 沒有 rejection_response 決策點，不產生 rejection_contract（附錄 A 1-2），但 agent 填了")
    elif rc is not None and "defined" in rc and rc["defined"] != rej: errs.append(f"X8：{rid} rejection_contract.defined 是 {rc['defined']}，推導值是 {rej}")
    amb = req.get("ambiguity") or {}
    given = (amb.get("level", "none"), amb.get("raised_level", "none"))
    if given != (eff_max, raised): errs.append(f"X9：{rid} ambiguity.level／raised_level 是 {given[0]}／{given[1]}，推導值是 {eff_max}／{raised}")
    status = "DRAFT" if any(d["route"] in DRAFT_ROUTES for d in der.values()) else "ACTIVE"
    return errs, {"dps": der, "level": eff_max, "raised_level": raised, "rejection_defined": rej, "status": status}

def stamp(req: dict, derived: dict | None, ctx: Ctx) -> dict:
    """持久化前寫入 runtime 推導的欄位（決策點 basis_hash、derived；需求的 ambiguity、rejection_contract）。"""
    r = dict(req)
    if derived is None: return r
    r["decision_points"] = [{**dp, "basis_hash": ctx.basis_hash, "derived": derived["dps"][dp["question_id"]]} for dp in req["decision_points"]]
    if derived["level"] == "none" and derived["raised_level"] == "none" and not req.get("ambiguity"): r["ambiguity"] = None
    else:
        amb = dict(req.get("ambiguity") or {"description": "決策點推導"})
        amb.update({"level": derived["level"], "raised_level": derived["raised_level"]}); amb.pop("resolved_by_approval", None)
        r["ambiguity"] = amb
    if derived["rejection_defined"] is None: r.pop("rejection_contract", None)
    else: r["rejection_contract"] = {**(req.get("rejection_contract") or {}), "defined": derived["rejection_defined"]}
    return r

def critical_points(requirements) -> list[tuple[dict, dict]]:
    """持久化後的 revision 中，有效等級為 critical 的決策點 (requirement, dp)。"""
    return [(r, dp) for r in requirements for dp in r.get("decision_points") or [] if (dp.get("derived") or {}).get("effective_level") == "critical"]
