"""qaos CLI。用法：python3 -m tools.qaos <command> ...  （或 bin/qaos）"""
import argparse, json, sys, pathlib, shutil
from . import store, schema, ids, engine, trace, clarification as clr, bugindex, approval_render, tc_export, bug_lifecycle, req_export, tc_ops
from .engine import EngineError
from .state import TransitionError

def _print(obj):
    if isinstance(obj, (dict, list)): print(json.dumps(obj, ensure_ascii=False, indent=2, default=str))
    else: print(obj)

def cmd_validate(a):
    rel = a.schema or schema.infer(a.file)
    if not rel: sys.exit(f"無法推斷 schema，請用 --schema：{a.file}")
    obj = store.load(pathlib.Path(a.file).resolve())
    errs = schema.errors(obj, rel)
    if errs: print(f"INVALID ({rel})"); [print(" -", e) for e in errs]; sys.exit(1)
    print(f"VALID ({rel})")

def cmd_id(a): print(ids.alloc(a.kind, a.area))

def cmd_run_new(a):
    inputs = {}
    for kv in a.input or []:
        k, v = kv.split("=", 1)
        inputs[k] = json.loads(v) if v[:1] in "[{" else v
    run = engine.new_run(a.workflow, inputs, a.by)
    print(f"{run['run_id']} {run['status']} current_task={run.get('current_task_id')}")

def cmd_run_show(a): [print(l) for l in trace.trace(a.run_id)]
def cmd_run_cancel(a): engine.cancel(a.run_id, a.by); print("CANCELLED")

def cmd_submit(a):
    ok, problems = engine.submit(a.run_id, a.task_id, a.artifact)
    if ok: print("VALID"); return
    print("INVALID"); [print(" -", p) for p in problems]; sys.exit(1)

def cmd_gate(a):
    r = engine.evaluate_gate(a.run_id, a.task_id)
    print(f"{r['gate']} {r['layer']} {r['result']}")
    for i in r["issues"]: print(" -", i)
    run = engine.load_run(a.run_id); print(f"run={run['status']} current_task={run.get('current_task_id')} waiting={run.get('waiting_on_approval_id')}")
    if r["result"] != "PASS": sys.exit(1)

def cmd_approve(a):
    per = [{"id": x.split(":")[0], "decision": x.split(":")[1]} for x in (a.per_item or [])] or None
    adj = json.loads(a.adjustments) if a.adjustments else None
    apr = engine.approve(a.approval_id, a.decision, a.by, a.rationale or "", a.option, adj, per)
    run = engine.load_run(apr["run_id"]); print(f"{apr['approval_id']} {apr['type']} → {a.decision}; run={run['status']} current_task={run.get('current_task_id')}")

def cmd_approval_show(a): approval_render.render(a.approval_id); approval_render.render_html(a.approval_id); print(f"approvals/{a.approval_id}.md + .html")

def cmd_req_export(a): print(req_export.export(a.spec_id, a.spec_version))

def cmd_tc_retire(a): apr, suites = tc_ops.retire(a.tc_id, a.by, a.rationale); print(f"{a.tc_id} → RETIRED via {apr}" + (f"；仍在 suite {[s['suite_id'] for s in suites]}，請另跑 regression-generation 移除" if suites else ""))
def cmd_tc_revise(a): run = tc_ops.revise(a.tc_id, a.reason, a.by); print(f"{run['run_id']} testcase-revision 已建立，current_task={run.get('current_task_id')}（Test Designer 產新版本 Draft → Validator → 你核准）")
def cmd_manual_new(a):
    rid = tc_ops.manual_new(a.title, a.product, a.area, a.step, a.observed, a.outcome, a.by, a.spec_id, a.spec_version, a.requirement_id, a.environment or "", a.precondition, a.evidence, a.notes or "")
    print(f"{rid} → testcases/manual/{rid}.yaml；下一步：bin/qaos run new manual-test-to-regression --input manual_record_id={rid}" + (f" --input spec_id={a.spec_id} --input spec_version={a.spec_version}" if a.spec_id else "") + f" --by {a.by}")

def cmd_tc_export(a): print(tc_export.export(a.area))

def cmd_approvals(a):
    for p in sorted((store.ROOT / "approvals").glob("APR-*.yaml")):
        d = store.load(p)
        if a.all or d["status"] == "PENDING":
            print(f"{d['approval_id']} [{d['status']}] {d['type']} run={d['run_id']} — {d['summary']}")
            for it in d.get("batch_items", []): print(f"    · {it['entity_type']} {it['id']} v{it.get('version', '')}")

def cmd_trace(a): [print(l) for l in trace.trace(a.id)]
def cmd_suites_of(a): _print(trace.suites_of(a.tc_id))

def cmd_spec_import(a):
    """Human 匯入 Spec 版本：複製 markdown 到 specs/<product>/<area>/<spec_id>/v<ver>.md，登記 hash。"""
    src = pathlib.Path(a.file).resolve(); text = src.read_text(encoding="utf-8")
    d = store.ROOT / "specs" / a.product / a.area / a.spec_id; d.mkdir(parents=True, exist_ok=True)
    areas = store.load(f"specs/{a.product}/areas.yaml") if store.exists(f"specs/{a.product}/areas.yaml") else {"product": a.product, "areas": {}}
    if a.area not in areas["areas"]: areas["areas"][a.area] = {"title": a.area_title or a.area}; store.save(f"specs/{a.product}/areas.yaml", areas)
    spec = store.load(d / "spec.yaml") if (d / "spec.yaml").exists() else {"spec_id": a.spec_id, "product": a.product, "functional_area": a.area, "title": a.title or a.spec_id, "versions": []}
    if any(v["spec_version"] == a.version for v in spec["versions"]): sys.exit(f"{a.spec_id} v{a.version} 已存在（Spec 版本不可覆蓋，請用新版本號）")
    fname = f"v{a.version}.md"; (d / fname).write_text(text, encoding="utf-8")
    for v in spec["versions"]:
        if v["status"] != "SUPERSEDED": v["status"] = "SUPERSEDED" if a.supersede else v["status"]
    spec["versions"].append({k: v for k, v in {"spec_version": a.version, "file": fname, "content_hash": store.sha256_text(text), "source_uri": a.source or str(src),
                            "imported_by": a.by, "imported_at": store.now(), "status": "IMPORTED", "change_summary": a.change_summary}.items() if v is not None})
    errs = schema.errors(spec, "spec/spec.schema.json")
    if errs: sys.exit("spec.yaml 不符 schema：" + "; ".join(errs))
    store.save(d / "spec.yaml", spec); store.audit(None, a.by, "IMPORT_SPEC", f"{a.spec_id}@{a.version}")
    print(f"{a.spec_id}@{a.version} imported → {d.relative_to(store.ROOT)}/{fname}")

def cmd_evidence_add(a):
    """Human / CI 加入 Evidence：複製檔案（或 inline 文字）到 evidence/<owner>/，自動算 sha256。"""
    eid = ids.alloc("EVD"); owner = a.owner or "unassigned"
    ev = {"evidence_id": eid, "type": a.type, "captured_at": a.captured_at or store.now(), "captured_by": a.by, "description": a.description or ""}
    if a.inline is not None:
        ev["uri"] = f"evidence/{owner}/{eid}.txt"; ev["inline_content"] = a.inline; ev["sha256"] = store.sha256_text(a.inline)
        (store.ROOT / "evidence" / owner).mkdir(parents=True, exist_ok=True); (store.ROOT / ev["uri"]).write_text(a.inline, encoding="utf-8")
    else:
        src = pathlib.Path(a.file).resolve(); dst_rel = f"evidence/{owner}/{eid}{src.suffix}"
        (store.ROOT / "evidence" / owner).mkdir(parents=True, exist_ok=True); shutil.copyfile(src, store.ROOT / dst_rel)
        ev["uri"] = dst_rel; ev["sha256"] = store.sha256_file(dst_rel); ev["size_bytes"] = src.stat().st_size
    if a.execution_id: ev["execution_id"] = a.execution_id
    errs = schema.errors(ev, "execution/evidence.schema.json")
    if errs: sys.exit("Evidence 不符 schema：" + "; ".join(errs))
    store.save(f"evidence/{owner}/{eid}.yaml", ev); store.audit(None, a.by, "ADD_EVIDENCE", f"{eid} {a.type}"); print(eid)

def cmd_execution_import(a):
    exe_id = ids.alloc("EXE")
    ex = {k: v for k, v in {"execution_id": exe_id, "testcase_id": a.testcase_id, "testcase_version": a.testcase_version, "result": a.result,
          "executor": a.by, "executor_type": a.executor_type, "environment": a.environment, "build": a.build, "executed_at": a.executed_at or store.now(),
          "actual_result": a.actual_result, "evidence_ids": a.evidence or [], "recorded_by": a.by, "notes": a.notes}.items() if v is not None}
    errs = schema.errors(ex, "execution/test-execution.schema.json")
    if errs: sys.exit("Execution 不符 schema：" + "; ".join(errs))
    store.save(f"executions/{ex['executed_at'][:7]}/{exe_id}.yaml", ex); store.audit(None, a.by, "IMPORT_EXECUTION", f"{exe_id} {a.testcase_id} {a.result}"); print(exe_id)

def cmd_bug_transition(a):
    """Bug OPEN 之後由 Human 推進（ADR-004 #11）。"""
    from . import state
    p = store.find_bug(a.bug_id); b = store.load(p)
    state.apply("bug", b, a.to, a.by, a.trigger or "manual", note=a.note or "")
    store.save(p, b); store.audit(None, a.by, "BUG_TRANSITION", f"{a.bug_id} → {a.to}"); print(f"{a.bug_id} → {a.to}")

def cmd_clr_new(a):
    c = clr.new(a.product, a.area, a.spec_id, a.spec_version, a.question, a.by, context=a.context or "", options=a.option or [], requirement_id=a.requirement_id, impact=a.impact)
    print(f"{c['clarification_id']} → clarifications/{a.product}/{a.area}/{c['clarification_id']}.md")
def cmd_clr_ask(a): c = clr.ask(a.id, a.to, a.by); print(f"{c['clarification_id']} ASKED → {a.to}")
def cmd_clr_answer(a): c = clr.answer(a.id, a.answer, a.answered_by, a.resolution, a.by, a.spec_version); print(f"{c['clarification_id']} ANSWERED ({a.resolution})")
def cmd_clr_impact(a):
    cands = clr.impact(a.id, a.keyword or [])
    for x in cands: print(f"{x['testcase_id']} v{x['version']} [{', '.join(x['reasons'])}] {x['title']}")
    print(f"({len(cands)} 條候選；逐條判定後以 --impact-reviewed 寫入 apply)")
def cmd_clr_apply(a): clr.apply_(a.id, a.by, a.note or "", impact_reviewed=a.impact_reviewed, keywords=a.keyword or []); print(f"{a.id} APPLIED")
def cmd_clr_withdraw(a): clr.withdraw(a.id, a.by, a.note or ""); print(f"{a.id} WITHDRAWN")
def cmd_clr_list(a):
    for c in clr.list_(open_only=not a.all): print(f"{c['clarification_id']} [{c['status']}] {c['product']}/{c['functional_area']} {c['spec_id']}@{c['spec_version']} — {c['question']}")
    n = clr.build_index(); print(f"(index: clarifications/index.md, {n} total)")
def cmd_bug_resolve(a): b = bug_lifecycle.resolve(a.bug_id, a.by, a.external_ref, a.note or "", a.fixed_by or ""); print(f"{a.bug_id} → {b['status']}")
def cmd_bug_verify(a): b = bug_lifecycle.verify(a.bug_id, a.execution, a.by); print(f"{a.bug_id} → {b['status']}")
def cmd_bug_close(a): b = bug_lifecycle.close(a.bug_id, a.by, a.rationale or ""); print(f"{a.bug_id} → {b['status']} (done)")
def cmd_bug_index(a): print(f"{bugindex.build()} bugs indexed → bugs/index.md + bugs/<product>/<area>/index.md")

def main(argv=None):
    ap = argparse.ArgumentParser(prog="qaos", description="QAOS Deterministic Runtime"); sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("validate"); p.add_argument("file"); p.add_argument("--schema"); p.set_defaults(f=cmd_validate)
    p = sp.add_parser("id"); p.add_argument("kind"); p.add_argument("--area"); p.set_defaults(f=cmd_id)
    r = sp.add_parser("run"); rs = r.add_subparsers(dest="sub", required=True)
    p = rs.add_parser("new"); p.add_argument("workflow"); p.add_argument("--input", action="append", metavar="key=value"); p.add_argument("--by", required=True); p.set_defaults(f=cmd_run_new)
    p = rs.add_parser("show"); p.add_argument("run_id"); p.set_defaults(f=cmd_run_show)
    p = rs.add_parser("cancel"); p.add_argument("run_id"); p.add_argument("--by", required=True); p.set_defaults(f=cmd_run_cancel)
    p = sp.add_parser("submit"); p.add_argument("run_id"); p.add_argument("task_id"); p.add_argument("artifact"); p.set_defaults(f=cmd_submit)
    p = sp.add_parser("gate"); p.add_argument("run_id"); p.add_argument("task_id"); p.set_defaults(f=cmd_gate)
    p = sp.add_parser("approve"); p.add_argument("approval_id"); p.add_argument("--decision", required=True, choices=["approve", "reject", "override"]); p.add_argument("--by", required=True)
    p.add_argument("--rationale"); p.add_argument("--option"); p.add_argument("--adjustments", help='JSON，如 {"severity":"critical"}'); p.add_argument("--per-item", action="append", metavar="ID:decision"); p.set_defaults(f=cmd_approve)
    p = sp.add_parser("approvals"); p.add_argument("--all", action="store_true"); p.set_defaults(f=cmd_approvals)
    p = sp.add_parser("approval"); p.add_argument("approval_id"); p.set_defaults(f=cmd_approval_show)
    p = sp.add_parser("tc-export"); p.add_argument("area"); p.set_defaults(f=cmd_tc_export)
    t = sp.add_parser("tc", help="正式 Test Case 的 Human 操作"); ts = t.add_subparsers(dest="sub", required=True)
    p = ts.add_parser("retire", help="退役一條 ACTIVE TC"); p.add_argument("tc_id"); p.add_argument("--rationale", required=True); p.add_argument("--by", required=True); p.set_defaults(f=cmd_tc_retire)
    p = ts.add_parser("revise", help="對 ACTIVE TC 發起修訂（產新版本，舊版保留）"); p.add_argument("tc_id"); p.add_argument("--reason", required=True); p.add_argument("--by", required=True); p.set_defaults(f=cmd_tc_revise)
    mn = sp.add_parser("manual", help="人工測試紀錄"); ms = mn.add_subparsers(dest="sub", required=True)
    p = ms.add_parser("new"); p.add_argument("--title", required=True); p.add_argument("--product", required=True); p.add_argument("--area", required=True); p.add_argument("--step", action="append", required=True, help="可重複，依序")
    p.add_argument("--observed", required=True); p.add_argument("--outcome", required=True, choices=["pass", "fail", "blocked"]); p.add_argument("--spec-id"); p.add_argument("--spec-version"); p.add_argument("--requirement-id", action="append")
    p.add_argument("--environment"); p.add_argument("--precondition", action="append"); p.add_argument("--evidence", action="append"); p.add_argument("--notes"); p.add_argument("--by", required=True); p.set_defaults(f=cmd_manual_new)
    p = sp.add_parser("req-export"); p.add_argument("spec_id"); p.add_argument("spec_version"); p.set_defaults(f=cmd_req_export)
    p = sp.add_parser("trace"); p.add_argument("id"); p.set_defaults(f=cmd_trace)
    p = sp.add_parser("suites-of"); p.add_argument("tc_id"); p.set_defaults(f=cmd_suites_of)
    s = sp.add_parser("spec"); ss = s.add_subparsers(dest="sub", required=True)
    p = ss.add_parser("import"); p.add_argument("file"); p.add_argument("--spec-id", required=True); p.add_argument("--version", required=True); p.add_argument("--product", required=True); p.add_argument("--area", required=True)
    p.add_argument("--title"); p.add_argument("--area-title"); p.add_argument("--source"); p.add_argument("--change-summary"); p.add_argument("--supersede", action="store_true"); p.add_argument("--by", required=True); p.set_defaults(f=cmd_spec_import)
    e = sp.add_parser("evidence"); es = e.add_subparsers(dest="sub", required=True)
    p = es.add_parser("add"); p.add_argument("--type", required=True); p.add_argument("--file"); p.add_argument("--inline"); p.add_argument("--owner", help="exe_id 或 bug 暫時歸屬目錄"); p.add_argument("--execution-id")
    p.add_argument("--description"); p.add_argument("--captured-at"); p.add_argument("--by", required=True); p.set_defaults(f=cmd_evidence_add)
    x = sp.add_parser("execution"); xs = x.add_subparsers(dest="sub", required=True)
    p = xs.add_parser("import"); p.add_argument("--testcase-id"); p.add_argument("--testcase-version", type=int); p.add_argument("--result", required=True, choices=["pass", "fail", "blocked", "skipped"])
    p.add_argument("--executor-type", default="human", choices=["human", "ci"]); p.add_argument("--environment", required=True); p.add_argument("--build"); p.add_argument("--executed-at"); p.add_argument("--actual-result")
    p.add_argument("--evidence", action="append"); p.add_argument("--notes"); p.add_argument("--by", required=True); p.set_defaults(f=cmd_execution_import)
    b = sp.add_parser("bug"); bs = b.add_subparsers(dest="sub", required=True)
    p = bs.add_parser("transition"); p.add_argument("bug_id"); p.add_argument("--to", required=True); p.add_argument("--by", required=True); p.add_argument("--trigger"); p.add_argument("--note"); p.set_defaults(f=cmd_bug_transition)
    p = bs.add_parser("index"); p.set_defaults(f=cmd_bug_index)
    p = bs.add_parser("resolve", help="QA 依共用表單登記 RD 已修復"); p.add_argument("bug_id"); p.add_argument("--external-ref", required=True); p.add_argument("--note"); p.add_argument("--fixed-by"); p.add_argument("--by", required=True); p.set_defaults(f=cmd_bug_resolve)
    p = bs.add_parser("verify", help="QA 複測：附 Execution（含 Evidence）"); p.add_argument("bug_id"); p.add_argument("--execution", required=True); p.add_argument("--by", required=True); p.set_defaults(f=cmd_bug_verify)
    p = bs.add_parser("close", help="結案（= done）"); p.add_argument("bug_id"); p.add_argument("--rationale"); p.add_argument("--by", required=True); p.set_defaults(f=cmd_bug_close)
    c = sp.add_parser("clarification", help="問 PM 的單子"); cs = c.add_subparsers(dest="sub", required=True)
    p = cs.add_parser("new"); p.add_argument("--product", required=True); p.add_argument("--area", required=True); p.add_argument("--spec-id", required=True); p.add_argument("--spec-version", required=True)
    p.add_argument("--question", required=True); p.add_argument("--context"); p.add_argument("--option", action="append"); p.add_argument("--requirement-id"); p.add_argument("--impact"); p.add_argument("--by", required=True); p.set_defaults(f=cmd_clr_new)
    p = cs.add_parser("ask"); p.add_argument("id"); p.add_argument("--to", required=True); p.add_argument("--by", required=True); p.set_defaults(f=cmd_clr_ask)
    p = cs.add_parser("answer"); p.add_argument("id"); p.add_argument("--answer", required=True); p.add_argument("--answered-by", required=True); p.add_argument("--resolution", required=True, choices=["spec_updated", "requirement_clarified", "no_change", "out_of_scope"]); p.add_argument("--spec-version"); p.add_argument("--by", required=True); p.set_defaults(f=cmd_clr_answer)
    p = cs.add_parser("impact", help="ADR-008：apply 前的影響掃描"); p.add_argument("id"); p.add_argument("--keyword", action="append"); p.set_defaults(f=cmd_clr_impact)
    p = cs.add_parser("apply"); p.add_argument("id"); p.add_argument("--by", required=True); p.add_argument("--note"); p.add_argument("--impact-reviewed", help="ADR-008：對 impact 候選 TC 的逐條結論（必填）"); p.add_argument("--keyword", action="append"); p.set_defaults(f=cmd_clr_apply)
    p = cs.add_parser("withdraw"); p.add_argument("id"); p.add_argument("--by", required=True); p.add_argument("--note"); p.set_defaults(f=cmd_clr_withdraw)
    p = cs.add_parser("list"); p.add_argument("--all", action="store_true"); p.set_defaults(f=cmd_clr_list)
    a = ap.parse_args(argv)
    try: a.f(a)
    except (EngineError, TransitionError, FileNotFoundError, ValueError) as e: sys.exit(f"qaos: {e}")

if __name__ == "__main__": main()
