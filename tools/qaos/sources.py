"""有型別來源（SourceRef）：quote 正規化、引用閉包與 basis、三型 SourceRef 驗證、covers、X16、effective_basis
（需求 A 第 3 章 §6～§10、第 1 章名詞表；附錄 A 1-1、1-8、1-15、3-5、3-17、3-20、3-22）。

讀取用的函式（不寫檔）。CLR 與核准單預設從 store 讀取；呼叫端可傳入 loader（有 clarification(id)、approval(id) 兩個方法）。"""
import json, re, hashlib
from . import store, spec_ops

MAX_CLOSURE = 50
ANSWERED_STATES = ("ANSWERED", "INCORPORATED", "APPLIED")

class SourceError(ValueError):
    pass

def canonical(obj) -> bytes:
    """canonical JSON：鍵依字典序、不含空白、UTF-8、不做 Unicode 正規化（第 1 章 §1.1）。"""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

def chash(obj) -> str:
    return hashlib.sha256(canonical(obj)).hexdigest()

class StoreLoader:
    def clarification(self, clr_id):
        p = store.find_clarification(clr_id)
        return store.load(p) if p else None
    def approval(self, apr_id):
        p = f"approvals/{apr_id}.yaml"
        return store.load(p) if store.exists(p) else None

# ---------------------------------------------------------------- quote（§6.2）
def normalize_quote(text: str) -> str:
    """只處理三件事：移除行首的 markdown 引用符號、移除 **、連續空白合併。"""
    lines = [re.sub(r"^[ \t]*(?:>[ \t]?)+", "", ln) for ln in (text or "").split("\n")]
    return re.sub(r"\s+", " ", "\n".join(lines).replace("**", "")).strip()

def quote_in(quote: str, text: str) -> bool:
    q = normalize_quote(quote)
    return bool(q) and q in normalize_quote(text)

# ---------------------------------------------------------------- 閉包與 basis（第 1 章名詞表；附錄 A 1-1）
def _vkey(v: str):
    return tuple(int(x) for x in str(v).split("."))

def _node(sid, ver, content_hash):
    """閉包節點：核對 SpecPin（登記值與實體檔），帶該節點自己目前的 decl_rev。"""
    pin = spec_ops.verify_pin(sid, ver, content_hash)
    _, _, e = spec_ops.find_entry(sid, ver)
    return {**pin, "decl_rev": spec_ops.decl_rev(e)}

def _refs(sid, ver):
    _, _, e = spec_ops.find_entry(sid, ver)
    return e.get("references") or []

def reading_closure(sid: str, ver: str) -> list[dict]:
    """閱讀閉包（派發包、reference_pins、spec 型 SourceRef 的範圍）：normative 遞移引用＋直接層 informative；
    循環以已訪集合終止；超過 50 個節點拒絕。回傳 RefNode 清單（不含目標本身）。"""
    target = (sid, str(ver)); seen = {target}; nodes = []; frontier = [(target, 0)]
    while frontier:
        (s, v), depth = frontier.pop(0)
        for r in _refs(s, v):
            key = (r["spec_id"], r["spec_version"])
            if r["role"] != "normative" or key in seen: continue
            seen.add(key); nodes.append({**_node(*key, r["content_hash"]), "role": "normative", "depth": depth + 1}); frontier.append((key, depth + 1))
            if len(nodes) > MAX_CLOSURE: raise SourceError(f"{sid}@{ver} 的引用閉包超過 {MAX_CLOSURE} 個節點")
    for r in _refs(*target):
        key = (r["spec_id"], r["spec_version"])
        if r["role"] == "informative" and key not in seen:
            seen.add(key); nodes.append({**_node(*key, r["content_hash"]), "role": "informative", "depth": 1})
            if len(nodes) > MAX_CLOSURE: raise SourceError(f"{sid}@{ver} 的引用閉包超過 {MAX_CLOSURE} 個節點")
    return nodes

def basis(sid: str, ver: str) -> dict:
    """{target: SpecPin, target_decl_rev, closure}；closure 只取 normative 遞移閉包，依 (spec_id, spec_version) 排序。"""
    pin = spec_ops.verify_pin(sid, ver)
    _, _, e = spec_ops.find_entry(sid, ver)
    closure = [{k: n[k] for k in ("spec_id", "spec_version", "content_hash", "decl_rev")} for n in reading_closure(sid, ver) if n["role"] == "normative"]
    closure.sort(key=lambda n: (n["spec_id"], _vkey(n["spec_version"])))
    return {"target": pin, "target_decl_rev": spec_ops.decl_rev(e), "closure": closure}

def legacy_basis(sid: str, ver: str) -> dict:
    """legacy 答案（rev 0）的 basis：只有目標、target_decl_rev 0、閉包空（第 3 章 §7.3）。"""
    _, _, e = spec_ops.find_entry(sid, ver)
    return {"target": {"spec_id": sid, "spec_version": str(ver), "content_hash": e["content_hash"]}, "target_decl_rev": 0, "closure": []}

def basis_hash(b: dict) -> str:
    return chash(b)

# ---------------------------------------------------------------- SourceRef 驗證（§6.1）
def _validate_spec(ref, target, errors, warnings):
    sid, ver = ref["spec_id"], ref["spec_version"]
    try: spec_ops.verify_pin(sid, ver, ref.get("content_hash"))
    except spec_ops.SpecError as e: errors.append(f"spec 型來源：{e}"); return
    p, _, e = spec_ops.find_entry(sid, ver); text = store.read_text(p.parent / e["file"])
    if not quote_in(ref.get("quote"), text): errors.append(f"spec 型來源：quote 不在 {sid}@{ver} 的實體檔中")
    if target is not None and (sid, str(ver)) != (target[0], str(target[1])):
        in_closure = {(n["spec_id"], n["spec_version"]) for n in reading_closure(*target)}
        if (sid, str(ver)) not in in_closure: errors.append(f"spec 型來源：{sid}@{ver} 不是目標 {target[0]}@{target[1]}，也不在它的引用閉包內")
    loc = ref.get("location") or ""
    m = re.match(r"§\s*([^\s/（(，,]+)", loc)
    if m and not any(m.group(1) in ln for ln in text.split("\n") if ln.lstrip().startswith("#")):
        warnings.append(f"spec 型來源：location {loc!r} 的標題在 {sid}@{ver} 中找不到（只警告）")

def _validate_clarification(ref, loader, errors):
    c = loader.clarification(ref["clarification_id"])
    if c is None: errors.append(f"clarification 型來源：{ref['clarification_id']} 不存在"); return
    if c["status"] == "WITHDRAWN": errors.append(f"clarification 型來源：{ref['clarification_id']} 已撤回（WITHDRAWN）"); return
    revs = c.get("answer_revisions") or []
    if not revs: errors.append(f"clarification 型來源：{ref['clarification_id']} 沒有答案修訂（{c['status']}），不能被引用"); return
    if ref["answer_rev"] >= len(revs): errors.append(f"clarification 型來源：{ref['clarification_id']} 沒有 answer_rev {ref['answer_rev']}"); return
    rev = revs[ref["answer_rev"]]
    if rev["sha256"] != ref["answer_sha256"] or store.sha256_text(rev["answer"]) != rev["sha256"]:
        errors.append(f"clarification 型來源：{ref['clarification_id']} rev {ref['answer_rev']} 的 answer_sha256 不符")
    if not quote_in(ref.get("quote"), rev["answer"]): errors.append(f"clarification 型來源：quote 不在 {ref['clarification_id']} rev {ref['answer_rev']} 的答案中")
    if rev["resolution"] not in ("requirement_clarified", "spec_updated"):
        errors.append(f"clarification 型來源：rev {ref['answer_rev']} 的 resolution 是 {rev['resolution']}，不能作為依據（附錄 A 1-15）")

def resolution_entry(ref, loader, at=None) -> tuple[dict | None, list[str]]:
    """approval 型：核對核准單與條目，回傳 (條目, errors)。at = (requirement_id, question_id)。"""
    shape = _shape_errors(ref)
    if shape: return None, shape
    a = loader.approval(ref["approval_id"]); errs = []
    if a is None: return None, [f"approval 型來源：{ref['approval_id']} 不存在"]
    if a["type"] != "RESOLVE_AMBIGUITY": return None, [f"approval 型來源：{ref['approval_id']} 是 {a['type']}，只接受 RESOLVE_AMBIGUITY"]
    d = a.get("decision")
    if not d: return None, [f"approval 型來源：{ref['approval_id']} 還沒有決議"]
    if d["decision"] not in ("approve", "override"): return None, [f"approval 型來源：{ref['approval_id']} 的決議是 {d['decision']}，只接受 approve 或 override（X15）"]
    if chash(d) != ref["decision_sha256"]: errs.append(f"approval 型來源：{ref['approval_id']} 的 decision_sha256 不符")
    res = d.get("resolutions") or []
    if ref["resolution_index"] >= len(res): return None, errs + [f"approval 型來源：{ref['approval_id']} 沒有 resolutions[{ref['resolution_index']}]"]
    entry = res[ref["resolution_index"]]
    if at is not None and (entry["requirement_id"], entry["question_id"]) != tuple(at):
        errs.append(f"approval 型來源：條目是 {entry['requirement_id']}/{entry['question_id']}，和引用處 {at[0]}/{at[1]} 不符")
    if (entry.get("source") or {}).get("type") == "approval": errs.append("approval 型來源：條目的 source 又是 approval 型（巢狀，X15）")
    return entry, errs

def _validate_approval(ref, loader, target, at, errors, warnings):
    entry, errs = resolution_entry(ref, loader, at); errors += errs
    if entry is None: return
    if not quote_in(ref.get("quote"), entry.get("rationale", "")):
        errors.append(f"approval 型來源：quote 不在 {ref['approval_id']} resolutions[{ref['resolution_index']}] 的 rationale 中")
    src = entry.get("source")
    if src is not None and src.get("type") != "approval":            # 巢狀 approval 已由 resolution_entry 拒絕（X15）
        inner_errs, inner_warns = validate(src, target=target, at=at, loader=loader)   # 包裝不解除內部來源的基本驗證（hash、quote、resolution、WITHDRAWN）
        where = f"（{ref['approval_id']} resolutions[{ref['resolution_index']}] 的 source）"
        errors += [e + where for e in inner_errs]; warnings += [w + where for w in inner_warns]

def validate(ref: dict, *, target=None, at=None, loader=None) -> tuple[list[str], list[str]]:
    """SourceRef 本身的驗證（不含 X16）。target = (spec_id, spec_version)：spec 型必須是目標或在閉包內；at = (requirement_id, question_id)。
    回傳 (errors, warnings)。"""
    loader = loader or StoreLoader(); errors, warnings = [], []
    errs = _shape_errors(ref)
    if errs: return errs, warnings
    {"spec": lambda: _validate_spec(ref, target, errors, warnings), "clarification": lambda: _validate_clarification(ref, loader, errors),
     "approval": lambda: _validate_approval(ref, loader, target, at, errors, warnings)}[ref["type"]]()
    return errors, warnings

REQUIRED = {"spec": ("spec_id", "spec_version", "content_hash", "location", "quote"), "clarification": ("clarification_id", "answer_rev", "answer_sha256", "quote"),
            "approval": ("approval_id", "decision_sha256", "resolution_index", "quote")}

INDEX_FIELDS = {"clarification": ("answer_rev",), "approval": ("resolution_index",)}

def _shape_errors(ref) -> list[str]:
    """先檢查 type 與必要欄位（訊息指出缺哪個），再以 defs 的 SourceRef 該型分支驗證形狀（型別、hash 格式、索引非負）。"""
    if not isinstance(ref, dict) or ref.get("type") not in REQUIRED: return [f"SourceRef 的 type 必須是 spec、clarification 或 approval：{ref!r}"[:200]]
    missing = [k for k in REQUIRED[ref["type"]] if ref.get(k) in (None, "")]
    if missing: return [f"{ref['type']} 型來源缺少 {', '.join(missing)}（新產出的 quote、location 不能是空字串）"]
    from jsonschema import Draft202012Validator
    from . import schema
    bad_idx = [k for k in INDEX_FIELDS.get(ref["type"], ()) if type(ref[k]) is not int]
    if bad_idx: return [f"{ref['type']} 型來源的形狀不合法：{', '.join(bad_idx)} 必須是整數表示（不接受 boolean、字串或 0.0 這類浮點寫法；附錄 A 3-24）"]
    branch = list(REQUIRED).index(ref["type"])
    v = Draft202012Validator({"$ref": f"https://qaos.local/schemas/common/defs.schema.json#/$defs/SourceRef/oneOf/{branch}"}, registry=schema.registry())
    return [f"{ref['type']} 型來源的形狀不合法：{e.json_path}: {e.message}" for e in v.iter_errors(ref)]

# ---------------------------------------------------------------- covers（第 1 章名詞表；附錄 A 1-8）
def covers(a: dict, d: dict) -> bool:
    """答案範圍 A 是否涵蓋決策點範圍 D（A 必須和 D 一樣寬或更寬）。"""
    if (a["spec_id"], a["requirement_id"], a["subject"]) != (d["spec_id"], d["requirement_id"], d["subject"]): return False
    ar, dr = a["role_scope"], d["role_scope"]
    if ar != ["*"]:
        if dr == ["*"] or not set(dr) <= set(ar): return False
    for k, av in a["params"].items():
        if k not in d["params"]: return False
        dv = d["params"][k]
        if isinstance(av, list) or isinstance(dv, list):
            if not set(dv if isinstance(dv, list) else [dv]) <= set(av if isinstance(av, list) else [av]): return False
        elif av != dv: return False
    return True

def self_scope(c: dict) -> dict | None:
    """CLR 自身的答案範圍；舊 CLR（沒有 subject 等欄位）沒有答案範圍。"""
    if not all(k in c for k in ("requirement_id", "subject", "role_scope", "params")): return None
    return {"spec_id": c["spec_id"], "requirement_id": c["requirement_id"], "subject": c["subject"], "role_scope": c["role_scope"], "params": c["params"]}

# ---------------------------------------------------------------- X16（§9.3）
def x16(ref: dict, scope: dict, dp_basis_hash: str, *, loader=None, at=None) -> list[str]:
    """clarification 型來源作為依據或 resolution 時，(a) 答案自身 basis_hash 相等且自身範圍涵蓋，或 (b) 有相符的人工 applicability。
    approval 型遞迴檢查條目內部的 clarification source；spec 型不適用。"""
    loader = loader or StoreLoader()
    shape = _shape_errors(ref)
    if shape: return shape
    if ref["type"] == "spec": return []
    if ref["type"] == "approval":
        entry, errs = resolution_entry(ref, loader, at)
        if errs or entry is None: return errs
        src = entry.get("source")
        if src is None: return []                                         # 核准者自行裁決：不是任何 CLR
        return [f"X16（經 {ref['approval_id']} resolutions[{ref['resolution_index']}]）：{e}" for e in x16(src, scope, dp_basis_hash, loader=loader, at=at)]
    c = loader.clarification(ref["clarification_id"])
    revs = (c or {}).get("answer_revisions") or []
    if c is None or ref["answer_rev"] >= len(revs): return [f"X16：{ref['clarification_id']} rev {ref['answer_rev']} 不存在"]
    rev = revs[ref["answer_rev"]]; own = self_scope(c)
    if rev["basis_hash"] == dp_basis_hash and own is not None and covers(own, scope): return []
    if any(ap["answer_rev"] == ref["answer_rev"] and ap["basis_hash"] == dp_basis_hash and covers(ap["scope"], scope) for ap in c.get("applicability") or []): return []
    why = "basis_hash 不同" if rev["basis_hash"] != dp_basis_hash else ("CLR 沒有自身的答案範圍" if own is None else "CLR 自身的範圍不涵蓋決策點")
    return [f"X16：{ref['clarification_id']} rev {ref['answer_rev']} 不能用在這個決策點（{why}，也沒有相符的 applicability）"]

# ---------------------------------------------------------------- effective_basis（§10）
def effective_basis(ref: dict, *, at=None, loader=None) -> tuple:
    loader = loader or StoreLoader()
    shape = _shape_errors(ref)
    if shape: raise SourceError("; ".join(shape))
    if ref["type"] == "clarification": return ("clarification", ref["clarification_id"], ref["answer_rev"], ref["answer_sha256"])
    if ref["type"] == "spec": return ("spec", ref["spec_id"], ref["spec_version"], ref["content_hash"], ref["location"])
    entry, errs = resolution_entry(ref, loader, at)
    if errs or entry is None: raise SourceError("; ".join(errs) or "無法解析 approval 型來源")
    if entry["outcome"] != "select_interpretation": raise SourceError(f"{ref['approval_id']} resolutions[{ref['resolution_index']}] 的 outcome 不是 select_interpretation")
    src = entry.get("source")
    if src is None: return ("approval", ref["approval_id"], ref["resolution_index"], ref["decision_sha256"])
    return effective_basis(src, at=at, loader=loader)
