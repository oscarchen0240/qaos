"""Traceability：由任一 ID 向上下游展開；suites-of 反查。"""
from . import store, refs

def suites_of(tc_id: str) -> list[dict]:
    out = []
    for p in (store.ROOT / "testsuites").rglob("SUITE-*.yaml"):
        if ".v" in p.name: continue
        s = store.load(p)
        for m in s["memberships"]:
            if m["testcase_id"] == tc_id: out.append({"suite_id": s["suite_id"], "suite_type": s["suite_type"], "version": s["version"], "status": s["status"], "pinned_version": m["pinned_version"]})
    return out

def _tc_versions(tc_id):
    ptr = store.load(store.tc_pointer_path(tc_id))
    return ptr, [store.load(store.tc_version_path(tc_id, v["version"])) for v in ptr["versions"]]

def _executions_of(tc_id):
    return [store.load(p) for p in (store.ROOT / "executions").rglob("EXE-*.yaml") if store.load(p).get("testcase_id") == tc_id]

def _bugs_where(pred):
    return [store.load(p) for p in (store.ROOT / "bugs").rglob("BUG-*.yaml") if pred(store.load(p))]

def trace(entity_id: str) -> list[str]:
    lines = []
    if entity_id.startswith("TC-"):
        ptr, vers = _tc_versions(entity_id)
        lines.append(f"TestCase {entity_id}  active_version={ptr['active_version']}  status={ptr['status']}")
        for v in vers:
            lines.append(f"  v{v['version']} [{v['status']}]  {v['title']}")
            lines.append(f"    ↑ SpecVersion {v['spec_id']}@{v['spec_version']}")
            for rid in v["requirement_ids"]:
                r, _ = refs.find_requirement(rid, v["spec_id"], v["spec_version"])
                lines.append(f"    ↑ Requirement {rid} [{r['status'] if r else '?'}]  {(r or {}).get('statement', '')[:60]}")
            for aid in v.get("acceptance_criteria_ids", []): lines.append(f"      ↑ AC {aid}")
            if v.get("approval_id"): lines.append(f"    ✓ approved_by {v['approved_by']} via {v['approval_id']}")
        for s in suites_of(entity_id): lines.append(f"  → Suite {s['suite_id']} v{s['version']} [{s['status']}] pinned={s['pinned_version']}")
        for e in _executions_of(entity_id): lines.append(f"  → Execution {e['execution_id']} v{e['testcase_version']} {e['result']} @{e['executed_at']}")
        for b in _bugs_where(lambda b: b.get("testcase_id") == entity_id): lines.append(f"  → Bug {b['bug_id']} [{b['status']}] {b['title']}")
    elif entity_id.startswith("BUG-"):
        b = store.load(store.find_bug(entity_id))
        lines.append(f"Bug {entity_id} [{b['status']}] {b['severity']}/{b['priority']}  {b['title']}")
        lines.append(f"  ↑ Requirement {b['requirement_id']}")
        lines.append(f"  ↑ SpecVersion {b['spec_id']}@{b['spec_version']}  ({b['expected_result_spec_reference']['location']})")
        if b.get("testcase_id"): lines.append(f"  ↑ TestCase {b['testcase_id']} v{b.get('testcase_version')}")
        if b.get("execution_id"): lines.append(f"  ↑ Execution {b['execution_id']}")
        for eid in b["evidence_ids"]:
            e = store.load(store.find_evidence(eid)); lines.append(f"  ↑ Evidence {eid} [{e['type']}] sha256={e['sha256'][:12]}…")
        lines.append(f"  ✓ validated_by {b.get('validated_by')} ({b.get('validation_report_id')}); approved_by {b.get('approved_by')} via {b.get('approval_id')}")
    elif entity_id.startswith("REQ-"):
        r, p = refs.find_requirement(entity_id)
        lines.append(f"Requirement {entity_id} [{r['status']}] {r['statement'][:80]}")
        lines.append(f"  ↑ SpecVersion {r['spec_id']}@{r['spec_version']}  ({r['spec_reference']['location']})")
        for ptr in (store.ROOT / "testcases" / "registry").glob("TC-*.yaml"):
            d = store.load(ptr)
            for v in d["versions"]:
                tc = store.load(store.tc_version_path(d["testcase_id"], v["version"]))
                if entity_id in tc["requirement_ids"]: lines.append(f"  → TestCase {d['testcase_id']} v{v['version']} [{tc['status']}] {tc['title']}")
        for b in _bugs_where(lambda b: b["requirement_id"] == entity_id): lines.append(f"  → Bug {b['bug_id']} [{b['status']}]")
    elif entity_id.startswith("SPEC-"):
        d = store.spec_dir(entity_id); spec = store.load(d / "spec.yaml")
        lines.append(f"Spec {entity_id}  {spec['title']}")
        for v in spec["versions"]:
            lines.append(f"  v{v['spec_version']} [{v['status']}] {v['file']} hash={v['content_hash'][:12]}…")
            path = store.requirements_path(entity_id, v["spec_version"])
            if store.exists(path):
                for r in store.load(path)["requirements"]: lines.append(f"    → Requirement {r['requirement_id']} [{r['status']}] {r['statement'][:60]}")
    elif entity_id.startswith("RUN-"):
        run = store.load(f"runs/{entity_id}/run.yaml")
        lines.append(f"Run {entity_id} {run['workflow_id']} [{run['status']}] by {run['initiated_by']}")
        for t in run["tasks"]:
            lines.append(f"  {t['task_id']} {t['type']} {t.get('agent_id', t.get('approval_id', ''))} [{t['status']}] iter={t['iteration']} out={t['output_artifact_ids']}")
    else:
        lines.append(f"不支援的 ID 前綴：{entity_id}")
    return lines
