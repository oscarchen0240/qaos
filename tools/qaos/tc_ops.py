"""Human 對正式 Test Case 的操作：retire（退役）、revise（發起修訂 run）；以及手動新增人工測試紀錄。"""
from . import store, state, schema, ids, engine
from .engine import EngineError

def retire(tc_id, by, rationale):
    ptr = store.load(store.tc_pointer_path(tc_id))
    if ptr["status"] != "ACTIVE": raise EngineError(f"{tc_id} 狀態 {ptr['status']}，只有 ACTIVE 可退役")
    apr_id = ids.alloc("APR")
    apr = {"approval_id": apr_id, "type": "RETIRE_TESTCASE", "run_id": "RUN-00000000-000", "status": "DECIDED", "summary": f"退役 {tc_id}：{rationale}",
           "impact": [{"entity_type": "TestCase", "id": tc_id}], "artifact_ids": [], "trace": [], "options": [{"key": "approve", "label": "退役"}],
           "requested_by": "system", "requested_at": store.now(), "decision": {"decision": "approve", "decided_by": by, "decided_at": store.now(), "rationale": rationale}}
    assert not schema.errors(apr, "approval/approval-request.schema.json"); store.save(f"approvals/{apr_id}.yaml", apr)
    vp = store.tc_version_path(tc_id, ptr["active_version"]); v = store.load(vp)
    state.apply("testcase", v, "RETIRED", by, apr_id, note=rationale); store.save(vp, v)
    for pv in ptr["versions"]:
        if pv["version"] == ptr["active_version"]: pv["status"] = "RETIRED"
    ptr["status"] = "RETIRED"; ptr["active_version"] = None; store.save(store.tc_pointer_path(tc_id), ptr)
    # 從 ACTIVE suite 中移除的提醒（不自動改 suite：那要走 UPDATE_SUITE_MEMBERSHIP）
    from . import trace as _t; suites = _t.suites_of(tc_id)
    store.audit(None, by, "RETIRE_TESTCASE", f"{tc_id} via {apr_id}; in suites: {[s['suite_id'] for s in suites]}")
    return apr_id, suites

def revise(tc_id, reason, by):
    ptr = store.load(store.tc_pointer_path(tc_id))
    if ptr["status"] != "ACTIVE": raise EngineError(f"{tc_id} 狀態 {ptr['status']}，只有 ACTIVE 可修訂（草稿請直接在原 run 修）")
    v = store.load(store.tc_version_path(tc_id, ptr["active_version"]))
    return engine.new_run("testcase-revision", {"testcase_id": tc_id, "reason": reason, "spec_id": v["spec_id"], "spec_version": v["spec_version"]}, by)

def manual_new(title, product, area, steps, observed, outcome, by, spec_id=None, spec_version=None, requirement_ids=None, environment="", preconditions=None, evidence_ids=None, notes=""):
    rid = ids.alloc("MAN")
    rec = {"record_id": rid, "title": title, "tester": by, "tested_at": store.now(), "product": product, "functional_area": area, "environment": environment or "—",
           "preconditions": preconditions or [], "steps_performed": steps, "observed_result": observed, "outcome": outcome, "evidence_ids": evidence_ids or [], "notes": notes}
    if spec_id: rec["spec_hint"] = {k: v for k, v in {"spec_id": spec_id, "spec_version": spec_version, "requirement_ids": requirement_ids}.items() if v}
    errs = schema.errors(rec, "testcase/manual-test-record.schema.json")
    if errs: raise EngineError("ManualTestRecord 不符 schema：" + "; ".join(errs[:3]))
    store.save(f"testcases/manual/{rid}.yaml", rec); store.audit(None, by, "NEW_MANUAL_RECORD", f"{rid} {title}"); return rid
