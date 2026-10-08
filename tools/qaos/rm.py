"""需求模型（RM）的不可變修訂版、檢視與綁定（需求 A 第 5 章 §3～§5；附錄 A 5-1、5-8、5-11）。

- 每次持久化需求都寫入不可變的 `artifacts/requirements/<spec>/v<ver>/revisions/R<NNN>.yaml`，更新 `revisions/index.yaml` 與檢視 `requirements.yaml`。
  今後只能透過 `save_requirements` 寫需求。新分析從 R001 起編號；R000 保留給移轉時 legacy `requirements.yaml` 的逐位元複本。
- RMPin = {spec_id, spec_version, revision, sha256}（sha256 是 revision 檔的 sha256）。
- R000 的 `target_decl_rev`、`reference_pins` 存在只建立一次的 `R000.meta.yaml`；R001 之後讀 revision 檔本身的欄位。所有讀取點都經由 `revision_meta`。
- run 的依據：run.yaml 的 `requirement_model_revision`（spec-change-impact 另有 `from_requirement_model_revision`）→ run sidecar → 錯誤。
  TC 的依據：TC 版本檔的 `requirement_model_revision` → TC sidecar → 錯誤。任何地方都不退回讀可變的檢視。"""
import re
from . import store, schema, operation

class RMError(ValueError):
    pass

REV_RE = re.compile(r"R[0-9]{3,}")

def base(sid, ver) -> str: return f"artifacts/requirements/{sid}/v{ver}"
def rev_dir(sid, ver) -> str: return f"{base(sid, ver)}/revisions"
def rev_path(sid, ver, rev) -> str: return f"{rev_dir(sid, ver)}/{rev}.yaml"
def meta_path(sid, ver) -> str: return f"{rev_dir(sid, ver)}/R000.meta.yaml"
def index_path(sid, ver) -> str: return f"{rev_dir(sid, ver)}/index.yaml"
def run_sidecar_path(run_id) -> str: return f"artifacts/requirements/_bindings/{run_id}.yaml"
def tc_sidecar_path(tc_id, version) -> str: return f"testcases/_bindings/{tc_id}-v{version}.yaml"

# ---------------------------------------------------------------- 讀取
def index(sid, ver) -> list[dict]:
    p = index_path(sid, ver)
    return store.load(p).get("revisions", []) if store.exists(p) else []

def pin_of(sid, ver, rev) -> dict:
    """RMPin；revision 必須存在，sha256 取自實際檔案並和索引相符。"""
    if not REV_RE.fullmatch(str(rev)): raise RMError(f"revision 格式應為 R<NNN>：{rev!r}")
    entry = next((e for e in index(sid, ver) if e["revision"] == rev), None)
    if entry is None: raise RMError(f"{sid}@{ver} 沒有 revision {rev}")
    p = rev_path(sid, ver, rev)
    if not store.exists(p): raise RMError(f"{sid}@{ver} 的 revision 檔 {rev} 不存在")
    sha = store.sha256_file(p)
    if sha != entry["sha256"]: raise RMError(f"{sid}@{ver} {rev} 的 sha256 和索引不符")
    return {"spec_id": sid, "spec_version": str(ver), "revision": rev, "sha256": sha}

def latest_pin(sid, ver) -> dict | None:
    idx = index(sid, ver)
    return pin_of(sid, ver, idx[-1]["revision"]) if idx else None

def verify_pin(pin: dict) -> dict:
    """RMPin 能解析到實際存在、hash 相符的 revision（G8 也用這個）。"""
    actual = pin_of(pin["spec_id"], pin["spec_version"], pin["revision"])
    if actual["sha256"] != pin["sha256"]: raise RMError(f"{pin['spec_id']}@{pin['spec_version']} {pin['revision']} 的 sha256 和釘選值不符")
    return actual

def load_revision(pin: dict) -> dict:
    verify_pin(pin)
    return store.load(rev_path(pin["spec_id"], pin["spec_version"], pin["revision"]))

def requirements_of(pin: dict) -> dict:
    """{requirement_id: requirement}：依 RMPin 讀，不讀檢視。"""
    return {r["requirement_id"]: r for r in load_revision(pin).get("requirements", [])}

def revision_meta(pin: dict) -> dict:
    """統一的讀取函式：{target_decl_rev, reference_pins}。R000 讀 R000.meta.yaml；R001 之後讀 revision 檔。缺少 → 拒絕，不以目前狀態補值。"""
    if pin["revision"] == "R000":
        p = meta_path(pin["spec_id"], pin["spec_version"])
        if not store.exists(p): raise RMError(f"{pin['spec_id']}@{pin['spec_version']} 缺少 R000.meta.yaml")
        m = store.load(p)
        if m.get("revision_sha256") != verify_pin(pin)["sha256"]: raise RMError(f"{pin['spec_id']}@{pin['spec_version']} 的 R000.meta.yaml 和 R000 不符")
        return {"target_decl_rev": m["target_decl_rev"], "reference_pins": m["reference_pins"]}
    d = load_revision(pin)
    if "target_decl_rev" not in d or "reference_pins" not in d: raise RMError(f"{pin['spec_id']}@{pin['spec_version']} {pin['revision']} 缺少 target_decl_rev 或 reference_pins")
    return {"target_decl_rev": d["target_decl_rev"], "reference_pins": d["reference_pins"]}

def requirement_owners(area) -> dict:
    """同 area 各 spec 已持久化（任一版本、任一 revision）的 requirement_id → spec_id 集合。"""
    out = {}
    for sp in store.glob(f"specs/*/{area}/*/spec.yaml"):
        sid = sp.parent.name
        for ip in store.glob(f"artifacts/requirements/{sid}/v*/revisions/index.yaml"):
            for e in store.load(ip).get("revisions") or []:
                if not store.exists(e["path"]): continue
                for r in store.load(e["path"]).get("requirements") or []: out.setdefault(r["requirement_id"], set()).add(sid)
    return out

def derived_ac_seq(ac_id: str, requirement_id: str) -> int | None:
    """AC 是否為所屬 REQ 的推導格式 AC-<AREA>-<REQ 序號><AC 序號>（docs/architecture/02-data-model.md §5）：是 → AC 序號；否則 None。
    AC 序號從 1 起、不補 0；REQ 序號照抄所屬 REQ（REQ 不是 REQ-<AREA>-<數字> 格式時無從推導）。"""
    m = re.fullmatch(r"REQ-([A-Z0-9]+)-([0-9]{3,})", requirement_id)
    if not m: return None
    a = re.fullmatch(rf"AC-{m.group(1)}-{m.group(2)}([1-9][0-9]*)", ac_id)
    return int(a.group(1)) if a else None

def ac_history(spec_id) -> dict:
    """同一 spec 已持久化（任一版本、任一 revision）的 AC：
    owners＝ac_id → 所屬 requirement_id 集合；high_water＝requirement_id → 用過的最大推導格式 AC 序號（舊 3 位數 AC 不計入）；
    live＝各 spec_version 最新 revision 中的 ac_id（只出現在較舊 revision 的 AC 視為已刪除）。"""
    owners, high, live = {}, {}, set()
    for ip in store.glob(f"artifacts/requirements/{spec_id}/v*/revisions/index.yaml"):
        entries = [e for e in store.load(ip).get("revisions") or [] if store.exists(e["path"])]
        for i, e in enumerate(entries):
            for r in store.load(e["path"]).get("requirements") or []:
                rid = r["requirement_id"]
                for a in r.get("acceptance_criteria") or []:
                    owners.setdefault(a["ac_id"], set()).add(rid)
                    if i == len(entries) - 1: live.add(a["ac_id"])
                    n = derived_ac_seq(a["ac_id"], rid)
                    if n is not None: high[rid] = max(high.get(rid, 0), n)
    return {"owners": owners, "high_water": high, "live": live}

def max_requirement_seq(area) -> int:
    """同 area 已持久化的 REQ-<AREA>-<序號> 的最大序號（沒有 → 0）。"""
    pat = re.compile(rf"REQ-{re.escape(area)}-([0-9]+)")
    return max((int(m.group(1)) for rid in requirement_owners(area) if (m := pat.fullmatch(rid))), default=0)

# ---------------------------------------------------------------- 寫入（唯一的需求寫入點）
def save_requirements(sid, ver, requirements: list, *, reason: str, by: str, run_id=None, source_artifact_id=None, extra: dict | None = None) -> dict:
    """產生新的不可變 revision、更新索引與檢視；回傳新 revision 的 RMPin。"""
    from . import sources, spec_ops
    view = store.requirements_path(sid, ver); idx = index(sid, ver)
    if not idx and store.exists(view):
        raise RMError(f"{sid}@{ver} 有未移轉的 legacy requirements.yaml（沒有 revision 索引）；請先完成移轉")
    n = max((int(e["revision"][1:]) for e in idx), default=0) + 1
    rev = f"R{n:03d}"; parent = idx[-1]["revision"] if idx else None
    _, _, entry = spec_ops.find_entry(sid, ver)
    doc = {"spec_id": sid, "spec_version": str(ver), "revision": rev, "parent": parent, "reason": reason, "run_id": run_id, "source_artifact_id": source_artifact_id,
           "created_at": store.now(), "created_by": by, "op_id": store.capturing().op_id,
           "target_decl_rev": spec_ops.decl_rev(entry), "reference_pins": sources.reading_closure(sid, ver), **(extra or {}), "requirements": requirements}
    doc = {k: v for k, v in doc.items() if v is not None or k == "parent"}
    errs = schema.errors(doc, "spec/requirements-revision.schema.json")
    if errs: raise RMError(f"{sid}@{ver} {rev} 不符 schema：" + "; ".join(errs[:3]))
    data = store.dump(doc)
    store.write_bytes(rev_path(sid, ver, rev), data)
    store.save(index_path(sid, ver), {"spec_id": sid, "spec_version": str(ver), "revisions": idx + [
        {"revision": rev, "path": rev_path(sid, ver, rev), "sha256": store.sha256_bytes(data), "created_at": doc["created_at"], "op_id": doc["op_id"], "reason": reason}]})
    view_doc = {"spec_id": sid, "spec_version": str(ver), "source_artifact_id": source_artifact_id, "persisted_at": doc["created_at"], "revision": rev, "requirements": requirements}
    errs = schema.errors({k: v for k, v in view_doc.items() if v is not None}, "spec/requirements-file.schema.json")
    if errs: raise RMError("requirements.yaml 不符 schema：" + "; ".join(errs[:3]))
    store.save(view, {k: v for k, v in view_doc.items() if v is not None})
    return {"spec_id": sid, "spec_version": str(ver), "revision": rev, "sha256": store.sha256_bytes(data)}

# ---------------------------------------------------------------- 綁定與解析（§4.1）
RUN_FIELDS = {"target": "requirement_model_revision", "from": "from_requirement_model_revision"}

def run_pin(run: dict, end: str = "target") -> dict:
    field = RUN_FIELDS[end]
    if run.get(field): return run[field]
    sc = run_sidecar_path(run["run_id"])
    if store.exists(sc):
        s = store.load(sc)
        if s.get(field): return s[field]
        if s.get("binding") == "none": raise RMError(f"{run['run_id']} 移轉時沒有 spec（binding: none），需要需求模型的步驟不能執行")
    raise RMError(f"{run['run_id']} 沒有綁定需求模型 revision（{field}），不讀可變的檢視")

def bind_run(run: dict, pin: dict, end: str = "target"):
    """新 run 的綁定：寫入 run.yaml（呼叫端負責保存 run）。已綁定就不改。"""
    field = RUN_FIELDS[end]
    if run.get(field) and run[field] != pin: raise RMError(f"{run['run_id']} 已綁定 {run[field]['revision']}，不能改綁 {pin['revision']}")
    run[field] = pin

def tc_pin(tc_id: str, version: int) -> dict:
    v = store.load(store.tc_version_path(tc_id, version))
    if v.get("requirement_model_revision"): return v["requirement_model_revision"]
    sc = tc_sidecar_path(tc_id, version)
    if store.exists(sc): return store.load(sc)["requirement_model_revision"]
    raise RMError(f"{tc_id} v{version} 沒有綁定需求模型 revision（版本檔沒有、也沒有 sidecar）")

def _premigration() -> bool:
    return not store.exists(operation.MARKER_PATH)

def run_pin_for_display(run: dict) -> dict | None:
    """顯示用（核准單渲染等）：移轉前的 legacy run 沒有 pin 時回傳 None；移轉後缺 pin 一律錯誤，不以「顯示用」換依據。"""
    try: return run_pin(run)
    except RMError:
        if _premigration(): return None
        raise

def tc_pin_for_display(tc_id: str, version: int) -> dict | None:
    try: return tc_pin(tc_id, version)
    except RMError:
        if _premigration(): return None
        raise

def find_requirement_latest(req_id: str):
    """run 外的查詢（trace、匯出標題等）：依各版本的最新 revision 找需求；回傳 (requirement, RMPin)。"""
    for p in store.glob("artifacts/requirements/*/*/revisions/index.yaml"):
        idx = store.load(p)
        if not idx.get("revisions"): continue
        pin = pin_of(idx["spec_id"], idx["spec_version"], idx["revisions"][-1]["revision"])
        r = requirements_of(pin).get(req_id)
        if r: return r, pin
    return None, None

# ---------------------------------------------------------------- 過時判定（§6；衍生查詢，不寫入）
def _clarification_refs(obj):
    """revision 內容中所有 clarification 型 SourceRef（決策點的依據、resolution 等）；approval 型包裝展開為條目內部的 clarification 來源。"""
    if isinstance(obj, dict):
        if obj.get("type") == "clarification" and "clarification_id" in obj and "answer_rev" in obj: yield obj
        if obj.get("type") == "approval" and "approval_id" in obj and type(obj.get("resolution_index")) is int:
            p = f"approvals/{obj['approval_id']}.yaml"
            res = ((store.load(p).get("decision") or {}).get("resolutions") or []) if store.exists(p) else []
            if obj["resolution_index"] < len(res): yield from _clarification_refs(res[obj["resolution_index"]].get("source"))
        for v in obj.values(): yield from _clarification_refs(v)
    elif isinstance(obj, list):
        for v in obj: yield from _clarification_refs(v)

def _vkey(v):
    return tuple(int(x) for x in str(v).split("."))

def outdated(pin: dict) -> dict:
    """{newer_available, declaration_changed, decision_revised, details[]}（第 5 章 §6）。"""
    from . import sources, spec_ops
    meta = revision_meta(pin); details = []
    _, _, entry = spec_ops.find_entry(pin["spec_id"], pin["spec_version"])
    decl = spec_ops.decl_rev(entry) != meta["target_decl_rev"]
    if decl: details.append(f"目標 {pin['spec_id']}@{pin['spec_version']} 的 decl_rev {meta['target_decl_rev']} → {spec_ops.decl_rev(entry)}")
    recorded = {(n["spec_id"], n["spec_version"]): n for n in meta["reference_pins"]}
    current = {(n["spec_id"], n["spec_version"]): n for n in sources.reading_closure(pin["spec_id"], pin["spec_version"])}
    if set(recorded) != set(current) or any(recorded[k]["role"] != current[k]["role"] for k in recorded if k in current):
        decl = True; details.append(f"閉包組成改變：新增 {sorted(set(current) - set(recorded))}，移除 {sorted(set(recorded) - set(current))}")
    for k in set(recorded) & set(current):
        if recorded[k]["decl_rev"] != current[k]["decl_rev"]:
            decl = True; details.append(f"閉包節點 {k[0]}@{k[1]} 的 decl_rev {recorded[k]['decl_rev']} → {current[k]['decl_rev']}")
    newer = False
    for (sid, ver) in recorded:
        p = spec_ops.spec_path(sid)
        if p and any(_vkey(v["spec_version"]) > _vkey(ver) for v in store.load(p)["versions"]):
            newer = True; details.append(f"{sid} 有比 {ver} 更新的匯入版本")
    revised = False
    for ref in _clarification_refs(load_revision(pin)):
        c = store.find_clarification(ref["clarification_id"])
        doc = store.load(c) if c else {}
        revs = doc.get("answer_revisions") or []
        if doc.get("status") == "WITHDRAWN":                                                  # A10：撤回的 CLR → 引用它的 revision 為 decision_revised（附錄 A 6-3）
            revised = True; details.append(f"{ref['clarification_id']} 已撤回（WITHDRAWN）"); continue
        if revs and ref["answer_rev"] != len(revs) - 1:
            revised = True; details.append(f"{ref['clarification_id']} 的最新答案是 rev {len(revs) - 1}，revision 引用 rev {ref['answer_rev']}")
    return {"newer_available": newer, "declaration_changed": decl, "decision_revised": revised, "details": details}

def has_non_active(pin: dict) -> bool:
    return any(r.get("status") != "ACTIVE" for r in requirements_of(pin).values())

def decision_applied(pin: dict) -> bool:
    """reason=decision_applied 的判定（附錄 A 5-3）：revision 引用的 CLR 在 revision 建立之後新增了 applied landing。"""
    created = operation.parse_ts(load_revision(pin)["created_at"]) if pin["revision"] != "R000" else None
    for ref in _clarification_refs(load_revision(pin)):
        c = store.find_clarification(ref["clarification_id"])
        for ld in (store.load(c).get("landings") or []) if c else []:
            if ld.get("type") == "applied" and (created is None or operation.parse_ts(ld["at"]) > created): return True
    return False

# ---------------------------------------------------------------- req accept-declaration（§6）
def _accept_request(target, rev, reason, by):
    return {"targets": {"spec_pins": [target]}, "params": {"rev": rev, "reason_sha256": store.sha256_text(reason or ""), "by": by}}

@operation.operation("req_accept_declaration", request=_accept_request)
def accept_declaration(target: str, rev: str, reason: str, by: str) -> dict:
    """產生新 revision：需求內容和 rev 相同、pins 依目前宣告更新；記錄 accepted_diff 與 accepted_without_analysis: true（新 pins 的文件沒有經過分析）。"""
    from . import spec_ops
    spec_ops.require_human(by)
    if not (reason or "").strip(): raise RMError("--reason 必填")
    sid, ver = spec_ops.parse_pin(target)
    latest = latest_pin(sid, ver)
    if latest is None or latest["revision"] != rev: raise RMError(f"--rev 必須是 {sid}@{ver} 的最新 revision（目前 {latest and latest['revision']}）")
    o = outdated(latest)
    if not o["declaration_changed"]: raise RMError(f"{sid}@{ver} {rev} 沒有宣告變動，不需要 accept-declaration")
    if o["decision_revised"]: raise RMError(f"{sid}@{ver} {rev} 另有 decision_revised，不能只接受宣告；請重新分析")
    from . import sources
    old = {(n["spec_id"], n["spec_version"]): n for n in revision_meta(latest)["reference_pins"]}
    new = {(n["spec_id"], n["spec_version"]): n for n in sources.reading_closure(sid, ver)}
    diff = {"added": [f"{k[0]}@{k[1]}" for k in sorted(set(new) - set(old))], "removed": [f"{k[0]}@{k[1]}" for k in sorted(set(old) - set(new))],
            "changed": [f"{k[0]}@{k[1]} decl_rev {old[k]['decl_rev']}→{new[k]['decl_rev']}" for k in sorted(set(old) & set(new)) if old[k]["decl_rev"] != new[k]["decl_rev"]]}
    doc = load_revision(latest)
    return save_requirements(sid, ver, doc["requirements"], reason=f"accept_declaration: {reason.strip()}", by=by, source_artifact_id=doc.get("source_artifact_id"),
                             extra={"accepted_without_analysis": True, "accepted_diff": diff})

