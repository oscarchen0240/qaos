"""Bug OPEN 之後的生命週期（RD 不進系統；QA 登記，每步有紀錄與證據）。"""
from . import store, state, schema, ids, refs
from .engine import EngineError

def _load(bug_id):
    p = store.find_bug(bug_id)
    if not p: raise EngineError(f"Bug {bug_id} 不存在（尚未 OPEN？）")
    return store.load(p), p

def _save(b, p):
    b["updated_at"] = store.now(); errs = schema.errors(b, "bug/bug.schema.json")
    if errs: raise EngineError("Bug 不符 schema：" + "; ".join(errs[:3]))
    store.save(p, b)

def resolve(bug_id, by, external_ref, note="", fixed_by=""):
    """QA 依共用表單登記 RD 已修復：OPEN → IN_PROGRESS → RESOLVED。"""
    b, p = _load(bug_id)
    if b["status"] == "OPEN": state.apply("bug", b, "IN_PROGRESS", by, external_ref, note="RD 修復中（依共用表單）")
    state.apply("bug", b, "RESOLVED", by, external_ref, note=(f"{fixed_by}：" if fixed_by else "") + (note or "RD 回報已修復，待 QA 複測"))
    b["external_ref"] = external_ref; b["resolution_note"] = note; b["resolved_at"] = store.now(); _save(b, p)
    store.audit(None, by, "BUG_RESOLVE", f"{bug_id} external_ref={external_ref}"); return b

def verify(bug_id, execution_id, by):
    """QA 複測：Execution 必須有 Evidence 且對應同一 TC；pass → VERIFIED，fail → OPEN（reopen）。"""
    b, p = _load(bug_id)
    if b["status"] != "RESOLVED": raise EngineError(f"{bug_id} 狀態 {b['status']}，只有 RESOLVED 可複測")
    ep = store.find_execution(execution_id)
    if not ep: raise EngineError(f"Execution {execution_id} 不存在")
    e = store.load(ep)
    if not e.get("evidence_ids"): raise EngineError("No Evidence, No Verification：複測 Execution 必須附 Evidence")
    for eid in e["evidence_ids"]:
        err = refs.resolve({"entity_type": "Evidence", "id": eid})
        if err: raise EngineError(err)
    if b.get("testcase_id") and e.get("testcase_id") and e["testcase_id"] != b["testcase_id"]:
        raise EngineError(f"複測 Execution 的 TC {e['testcase_id']} ≠ Bug 的 TC {b['testcase_id']}")
    b.setdefault("retest_execution_ids", []).append(execution_id)
    if e["result"] == "pass":
        state.apply("bug", b, "VERIFIED", by, execution_id, note="複測通過")
    else:
        state.apply("bug", b, "OPEN", by, execution_id, note=f"複測 {e['result']}，reopen"); b["reopen_count"] = b.get("reopen_count", 0) + 1
    _save(b, p); store.audit(None, by, "BUG_VERIFY", f"{bug_id} {execution_id} {e['result']} → {b['status']}"); return b

def close(bug_id, by, rationale=""):
    """結案（= 共用表單的 done）。Human 動作即為 CLOSE_BUG approval，但仍留一張 ApprovalRequest 供審計。"""
    b, p = _load(bug_id)
    if b["status"] != "VERIFIED": raise EngineError(f"{bug_id} 狀態 {b['status']}，只有 VERIFIED 可結案")
    apr_id = ids.alloc("APR")
    apr = {"approval_id": apr_id, "type": "CLOSE_BUG", "run_id": (b["history"][0].get("run_id") if b["history"] else None) or "RUN-00000000-000", "status": "DECIDED",
           "summary": f"結案 {bug_id}：{b['title']}", "impact": [{"entity_type": "Bug", "id": bug_id}], "artifact_ids": [], "trace": [],
           "options": [{"key": "approve", "label": "結案"}], "requested_by": "system", "requested_at": store.now(),
           "decision": {"decision": "approve", "decided_by": by, "decided_at": store.now(), "rationale": rationale or "複測通過，結案"}}
    errs = schema.errors(apr, "approval/approval-request.schema.json")
    if errs: raise EngineError("ApprovalRequest 不符 schema：" + "; ".join(errs[:3]))
    store.save(f"approvals/{apr_id}.yaml", apr)
    state.apply("bug", b, "CLOSED", by, apr_id, note="done"); _save(b, p)
    store.audit(None, by, "BUG_CLOSE", f"{bug_id} via {apr_id}"); return b
