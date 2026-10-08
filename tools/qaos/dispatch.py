"""派發包（需求 A 第 1 章 §2.2、§2.3；附錄 A 1-6）：runtime 為某個 run 的某個 task 的某次 iteration 產生不可變的輸入包。

- 必須有派發包的 task：Spec Analyst、Test Designer、Test Validator、TC Risk Reviewer、Change Impact Analyst（第一批）。
- 同一 iteration 只能派發一次；要改輸入就必須進入新的 iteration。
- 額外來源只能在產生派發包時登記，每筆附理由與 hash。
- 派發包保存所用決議的快照，舊 run 恢復時自給自足，不依賴 CLR 的目前內容。"""
import re
from . import store, schema, operation, rm, sources, spec_ops

DISPATCH_AGENTS = ("agent-spec-analyst", "agent-test-designer", "agent-test-validator", "agent-tc-risk-reviewer", "agent-change-impact-analyst")
RESOLVED_STATES = ("ANSWERED", "INCORPORATED", "APPLIED")
OPEN_STATES = ("OPEN", "ASKED")

class DispatchError(ValueError):
    pass

def needs_packet(task: dict) -> bool:
    return task.get("type") == "agent" and task.get("agent_id") in DISPATCH_AGENTS

def packet_path(run_id: str, task_id: str, iteration: int) -> str:
    return f"runs/{run_id}/dispatch/{task_id}-iter{iteration}.yaml"

def target_of(run: dict) -> tuple[str, str] | None:
    """run 的目標 spec 版本：spec-change-impact 取 to 端；其餘取 inputs 的 spec（manual 另看 spec_hint）。"""
    inp = run["input"]
    if run["workflow_id"] == "spec-change-impact": return inp["spec_id"], str(inp["to_version"])
    if inp.get("spec_id") and inp.get("spec_version"): return inp["spec_id"], str(inp["spec_version"])
    if run["workflow_id"] == "manual-test-to-regression" and inp.get("manual_record_id") and store.exists(f"testcases/manual/{inp['manual_record_id']}.yaml"):
        h = store.load(f"testcases/manual/{inp['manual_record_id']}.yaml").get("spec_hint") or {}
        if h.get("spec_id") and h.get("spec_version"): return h["spec_id"], str(h["spec_version"])
    return None

def current_entry(task: dict) -> dict | None:
    """task 本次 iteration 的派發包紀錄（task.dispatch_packets[]）。"""
    return next((e for e in task.get("dispatch_packets") or [] if e["iteration"] == task["iteration"]), None)

def load_packet(entry: dict) -> dict:
    """依 task 上的紀錄讀派發包，位元組 sha256 必須相符（派發包不可變）。"""
    if not store.exists(entry["path"]): raise DispatchError(f"派發包 {entry['path']} 不存在")
    if store.sha256_file(entry["path"]) != entry["sha256"]: raise DispatchError(f"派發包 {entry['path']} 的 sha256 和 task 的紀錄不符（派發包不可變）")
    return store.load(entry["path"])

def current_packet(run: dict, task: dict) -> dict | None:
    e = current_entry(task)
    return load_packet(e) if e else None

# ---------------------------------------------------------------- 內容
def _areas(target) -> set[str]:
    """同 area 以及直接參考（depth=1）所屬 area。"""
    out = set()
    for sid in [target[0]] + [n["spec_id"] for n in sources.reading_closure(*target) if n["depth"] == 1]:
        d = store.spec_dir(sid)
        if d: out.add((d.parent.parent.name, d.parent.name))
    return out

def _clr_snapshot(c: dict) -> dict | None:
    revs = c.get("answer_revisions") or []
    if not revs: return None
    r = revs[-1]
    return {"clarification_id": c["clarification_id"], "status": c["status"], "kind": c.get("kind", "spec_question"),
            "spec_id": c["spec_id"], "spec_version": str(c["spec_version"]), "requirement_id": c.get("requirement_id"), "question_id": c.get("question_id"),
            "answer_rev": r["rev"], "answer_sha256": r["sha256"], "answer": r["answer"], "resolution": r["resolution"], "basis_hash": r["basis_hash"],
            "scope": sources.self_scope(c), "applicability": list(c.get("applicability") or [])}

def _clarifications(areas) -> tuple[list, list]:
    resolved, pending = [], []
    for prod, area in sorted(areas):
        for p in store.glob(f"clarifications/{prod}/{area}/CLR-*.yaml"):
            c = store.load(p)
            if c["status"] in RESOLVED_STATES:
                s = _clr_snapshot(c)
                if s: resolved.append(s)
            elif c["status"] in OPEN_STATES:
                pending.append({"clarification_id": c["clarification_id"], "status": c["status"], "kind": c.get("kind", "spec_question"),
                                "spec_id": c["spec_id"], "spec_version": str(c["spec_version"]), "requirement_id": c.get("requirement_id"),
                                "question_id": c.get("question_id"), "question": c["question"]})
    key = lambda x: x["clarification_id"]
    return sorted(resolved, key=key), sorted(pending, key=key)

def _run_decisions(run_id: str) -> list[dict]:
    out = []
    for p in store.glob("approvals/APR-*.yaml"):
        a = store.load(p)
        if a.get("run_id") != run_id or a["type"] != "RESOLVE_AMBIGUITY" or a["status"] != "DECIDED": continue
        d = a["decision"]
        out.append({"approval_id": a["approval_id"], "decision": d["decision"], "decision_sha256": sources.chash(d), "resolutions": list(d.get("resolutions") or [])})
    return sorted(out, key=lambda x: x["approval_id"])

def _pin_groups(spec_id: str) -> list[dict]:
    """spec-change-impact：from 端候選 TC（同 spec_id 的 ACTIVE TC）各自 pin 的去重清單（第 5 章 §9）。"""
    from . import gates
    cand, errs = gates._cia_candidates(spec_id)
    if errs: raise DispatchError("; ".join(errs))
    seen = {}
    for p in cand.values(): seen[sources.chash(p)] = p
    return [seen[k] for k in sorted(seen, key=lambda k: (seen[k]["spec_version"], seen[k]["revision"]))]

def _decision_sources(pins: list[dict]) -> list[dict]:
    """綁定的 revision 中決策點用到的 SourceRef（known_rules、conflict_sides、resolution.source），供下游判斷派發包範圍。"""
    out = {}
    for pin in pins:
        for r in rm.requirements_of(pin).values():
            for dp in r.get("decision_points") or []:
                refs_ = list(dp.get("known_rules") or []) + list(dp.get("conflict_sides") or []) + ([dp["resolution"]["source"]] if (dp.get("resolution") or {}).get("source") else [])
                for ref in refs_: out[sources.chash(basis_ref(ref))] = basis_ref(ref)
    return [out[k] for k in sorted(out)]

def basis_ref(ref: dict) -> dict:
    """SourceRef 的身分（不含 quote；第 1 章名詞表 basis_ref）。"""
    keys = {"spec": ("spec_id", "spec_version", "content_hash", "location"), "clarification": ("clarification_id", "answer_rev", "answer_sha256"),
            "approval": ("approval_id", "resolution_index", "decision_sha256")}[ref["type"]]
    return {"type": ref["type"], **{k: ref[k] for k in keys}}

def _extra(item: dict) -> dict:
    ref, reason = item["ref"], (item.get("reason") or "").strip()
    if not reason: raise DispatchError(f"額外來源 {ref!r} 沒有附理由（--reason）")
    if re.fullmatch(r"SPEC-[A-Z0-9-]+@[0-9.]+", ref):
        sid, ver = spec_ops.parse_pin(ref)
        try: pin = spec_ops.verify_pin(sid, ver)
        except spec_ops.SpecError as e: raise DispatchError(f"額外來源 {ref}：{e}")
        return {"kind": "spec_pin", "ref": ref, "pin": pin, "sha256": pin["content_hash"], "reason": reason}
    rel = store.rel(ref)
    if not store.exists(rel) or store.abspath(rel).is_dir(): raise DispatchError(f"額外來源 {ref} 不存在或不是檔案")
    return {"kind": "path", "ref": rel, "sha256": store.sha256_file(rel), "reason": reason}

def build(run: dict, task: dict, extras: list[dict]) -> dict:
    tgt = target_of(run)
    pins = {}
    for end in ("target", "from"):
        try: pins[end] = rm.run_pin(run, end)
        except rm.RMError: pins[end] = None
    doc = {"packet_version": 1, "run_id": run["run_id"], "task_id": task["task_id"], "iteration": task["iteration"], "agent_id": task["agent_id"],
           "workflow_id": run["workflow_id"], "created_at": store.now(),
           "target": None, "target_decl_rev": None, "closure": [], "basis_hash": None,
           "rm_pins": {"target": pins["target"], "from": pins["from"], "pin_groups": []},
           "resolutions": [], "run_decisions": _run_decisions(run["run_id"]), "open_questions": [], "decision_sources": [], "extra_inputs": [_extra(x) for x in extras]}
    if tgt:
        try:
            pin = spec_ops.verify_pin(*tgt); _, _, entry = spec_ops.find_entry(*tgt)
            closure = sources.reading_closure(*tgt); b = sources.basis(*tgt)
        except (spec_ops.SpecError, sources.SourceError) as e: raise DispatchError(f"目標 {tgt[0]}@{tgt[1]}：{e}")
        doc.update({"target": pin, "target_decl_rev": spec_ops.decl_rev(entry), "references_status": spec_ops.references_status(entry),
                    "closure": [{**n, "required": n["role"] == "normative" and n["depth"] == 1} for n in closure], "basis_hash": sources.basis_hash(b)})
        doc["resolutions"], doc["open_questions"] = _clarifications(_areas(tgt))
    if run["workflow_id"] == "spec-change-impact": doc["rm_pins"]["pin_groups"] = _pin_groups(run["input"]["spec_id"])
    bound = [p for p in (pins["target"], pins["from"]) if p] + doc["rm_pins"]["pin_groups"]
    doc["decision_sources"] = _decision_sources(bound)
    return doc

# ---------------------------------------------------------------- 寫入指令
def _request(run_id, task_id, extras=(), by="system"):
    from .engine import load_run, _task
    task = _task(load_run(run_id), task_id)
    return {"targets": {"run_id": run_id, "task_id": task_id, "iteration": task["iteration"]},
            "params": {"extras": [{"ref": x["ref"], "reason_sha256": store.sha256_text(x.get("reason") or "")} for x in extras]}}

@operation.operation("dispatch", request=_request, scope=lambda run_id, *a, **k: run_id)
def dispatch(run_id: str, task_id: str, extras=(), by: str = "system") -> dict:
    """產生 runs/<run>/dispatch/<task>-iter<N>.yaml，並把路徑與 sha256 記在 task.dispatch_packets[]。"""
    from .engine import load_run, _task, _save_run
    run = load_run(run_id)
    try: task = _task(run, task_id)
    except StopIteration: raise DispatchError(f"{run_id} 沒有 task {task_id}")
    if run["status"] not in ("RUNNING",): raise DispatchError(f"run 狀態 {run['status']}，不能派發")
    if not needs_packet(task): raise DispatchError(f"{task_id}（{task.get('agent_id') or task['type']}）不需要派發包（附錄 A 1-6）")
    if task["status"] not in ("READY", "RUNNING"): raise DispatchError(f"{task_id} 狀態 {task['status']}，不能派發")
    if current_entry(task) or store.exists(packet_path(run_id, task_id, task["iteration"])):
        raise DispatchError(f"{task_id} iteration {task['iteration']} 已經派發過；同一 iteration 只能派發一次，要改輸入必須進入新的 iteration")
    doc = build(run, task, list(extras))
    errs = schema.errors(doc, "workflow/dispatch-packet.schema.json")
    if errs: raise DispatchError("派發包不符 schema：" + "; ".join(errs[:3]))
    data = store.dump(doc); path = packet_path(run_id, task_id, task["iteration"])
    store.write_bytes(path, data)
    entry = {"iteration": task["iteration"], "path": path, "sha256": store.sha256_bytes(data), "at": doc["created_at"]}
    task.setdefault("dispatch_packets", []).append(entry)
    _save_run(run)
    store.audit(run_id, by, "DISPATCH", f"{task_id} iteration {task['iteration']} → {path}" + (f"（額外來源 {len(doc['extra_inputs'])} 筆）" if doc["extra_inputs"] else ""))
    return entry

# ---------------------------------------------------------------- 範圍檢查（第 1 章 §2.6）
def in_scope(packet: dict, ref: dict) -> bool:
    """SourceRef 是否在派發包範圍內：spec 型為目標、閉包或額外 spec；clarification 型為決議快照中的同一 answer_rev；
    approval 型為本 run 已決的裁決；或是綁定 revision 決策點已使用的來源。"""
    try: ident = basis_ref(ref)
    except (KeyError, TypeError): return False
    if ident in packet.get("decision_sources") or []: return True
    t = ref["type"]
    if t == "spec":
        pin = (ref["spec_id"], str(ref["spec_version"]), ref["content_hash"])
        pins = [packet["target"]] if packet.get("target") else []
        pins += packet.get("closure") or []
        pins += [x["pin"] for x in packet.get("extra_inputs") or [] if x["kind"] == "spec_pin"]
        return any((p["spec_id"], str(p["spec_version"]), p["content_hash"]) == pin for p in pins)
    if t == "clarification":
        return any((s["clarification_id"], s["answer_rev"], s["answer_sha256"]) == (ref["clarification_id"], ref["answer_rev"], ref["answer_sha256"]) for s in packet.get("resolutions") or [])
    return any((d["approval_id"], d["decision_sha256"]) == (ref["approval_id"], ref["decision_sha256"]) for d in packet.get("run_decisions") or [])
