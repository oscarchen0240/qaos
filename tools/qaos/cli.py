"""qaos CLI。用法：python3 -m tools.qaos <command> ...  （或 bin/qaos）

寫入指令一律經過 executor（tools/qaos/operation.py）：取得 flock、產生操作計畫、依序寫入；同一請求重送會續做或回報已完成，
要刻意再執行一次相同內容的請求請加 --new-request。唯讀指令（list、show、trace、approvals、--stdout 版 export、operation list）不取鎖，
也不保證跨檔一致的快照。"""
import argparse, json, sys, pathlib
from . import store, schema, ids, engine, trace, operation, spec_ops, clarification as clr, bugindex, approval_render, tc_export, bug_lifecycle, req_export, tc_ops, final_export, state
from .engine import EngineError
from .state import TransitionError

READONLY_NOTE = "（唯讀指令：不取鎖，不保證跨檔一致的快照）"

def _print(obj):
    if isinstance(obj, (dict, list)): print(json.dumps(obj, ensure_ascii=False, indent=2, default=str))
    else: print(obj)

def _nr(a) -> dict:
    return {"new_request": bool(getattr(a, "new_request", False))}

def _notice():
    o = operation.LAST_OUTCOME
    if o.get("kind") == "completed":
        print(f"（這是先前已完成的同一請求 op={o['op_id'][:12]}…，沒有再次寫入；要再執行一次請加 --new-request）", file=sys.stderr)
    elif o.get("kind") == "resumed":
        print(f"（已續做未完成的計畫 op={o['op_id'][:12]}…）", file=sys.stderr)

# ---------------------------------------------------------------- 寫入（executor）
def _evidence_request(type_, by, file=None, inline=None, **kw):
    inp = {"inline_sha256": store.sha256_text(inline)} if inline is not None else {"file_sha256": store.sha256_bytes(pathlib.Path(file).read_bytes())}
    return {"params": operation.normalize({"type": type_, "by": by, **kw}), "inputs": inp}

@operation.operation("evidence_add", request=_evidence_request)
def evidence_add(type_, by, file=None, inline=None, owner=None, execution_id=None, description=None, captured_at=None):
    """Human / CI 加入 Evidence：複製檔案（或 inline 文字）到 evidence/<owner>/，自動算 sha256。"""
    eid = ids.alloc("EVD"); owner = owner or "unassigned"
    ev = {"evidence_id": eid, "type": type_, "captured_at": captured_at or store.now(), "captured_by": by, "description": description or ""}
    if inline is not None:
        ev["uri"] = f"evidence/{owner}/{eid}.txt"; ev["inline_content"] = inline; ev["sha256"] = store.sha256_text(inline)
        store.write_text(ev["uri"], inline)
    else:
        src = pathlib.Path(file).resolve(); data = src.read_bytes(); dst_rel = f"evidence/{owner}/{eid}{src.suffix}"
        store.write_bytes(dst_rel, data); ev["uri"] = dst_rel; ev["sha256"] = store.sha256_bytes(data); ev["size_bytes"] = len(data)
    if execution_id: ev["execution_id"] = execution_id
    errs = schema.errors(ev, "execution/evidence.schema.json")
    if errs: raise ValueError("Evidence 不符 schema：" + "; ".join(errs))
    store.save(f"evidence/{owner}/{eid}.yaml", ev); store.audit(None, by, "ADD_EVIDENCE", f"{eid} {type_}"); return eid

@operation.operation("execution_import")
def execution_import(result, environment, by, testcase_id=None, testcase_version=None, executor_type="human", build=None, executed_at=None, actual_result=None, evidence=None, notes=None):
    exe_id = ids.alloc("EXE")
    ex = {k: v for k, v in {"execution_id": exe_id, "testcase_id": testcase_id, "testcase_version": testcase_version, "result": result,
          "executor": by, "executor_type": executor_type, "environment": environment, "build": build, "executed_at": executed_at or store.now(),
          "actual_result": actual_result, "evidence_ids": evidence or [], "recorded_by": by, "notes": notes}.items() if v is not None}
    errs = schema.errors(ex, "execution/test-execution.schema.json")
    if errs: raise ValueError("Execution 不符 schema：" + "; ".join(errs))
    store.save(f"executions/{ex['executed_at'][:7]}/{exe_id}.yaml", ex); store.audit(None, by, "IMPORT_EXECUTION", f"{exe_id} {testcase_id} {result}"); return exe_id

@operation.operation("bug_transition")
def bug_transition(bug_id, to, by, trigger=None, note=None):
    """Bug OPEN 之後由 Human 推進（ADR-004 #11）。"""
    p = store.find_bug(bug_id); b = store.load(p)
    state.apply("bug", b, to, by, trigger or "manual", note=note or "")
    store.save(p, b); store.audit(None, by, "BUG_TRANSITION", f"{bug_id} → {to}"); return f"{bug_id} → {to}"

# ---------------------------------------------------------------- 指令
def cmd_validate(a):
    rel = a.schema or schema.infer(a.file)
    if not rel: sys.exit(f"無法推斷 schema，請用 --schema：{a.file}")
    obj = store.load(pathlib.Path(a.file).resolve())
    errs = schema.errors(obj, rel)
    if errs: print(f"INVALID ({rel})"); [print(" -", e) for e in errs]; sys.exit(1)
    print(f"VALID ({rel})")

def cmd_id(a): print(ids.alloc_cmd(a.kind, a.area, **_nr(a)))

def cmd_run_new(a):
    inputs = {}
    for kv in a.input or []:
        k, v = kv.split("=", 1)
        inputs[k] = json.loads(v) if v[:1] in "[{" else v
    run = engine.new_run(a.workflow, inputs, a.by, **_nr(a))
    print(f"{run['run_id']} {run['status']} current_task={run.get('current_task_id')}")

def cmd_run_show(a): [print(l) for l in trace.trace(a.run_id)]
def cmd_run_cancel(a): engine.cancel(a.run_id, a.by, **_nr(a)); print("CANCELLED")

def cmd_submit(a):
    ok, problems = engine.submit(a.run_id, a.task_id, a.artifact, **_nr(a))
    if ok: print("VALID"); return
    print("INVALID"); [print(" -", p) for p in problems]; sys.exit(1)

def cmd_gate(a):
    r = engine.evaluate_gate(a.run_id, a.task_id, **_nr(a))
    print(f"{r['gate']} {r['layer']} {r['result']}")
    for i in r["issues"]: print(" -", i)
    run = engine.load_run(a.run_id); print(f"run={run['status']} current_task={run.get('current_task_id')} waiting={run.get('waiting_on_approval_id')}")
    if r["result"] != "PASS": sys.exit(1)

def cmd_approve(a):
    per = [{"id": x.split(":")[0], "decision": x.split(":")[1]} for x in (a.per_item or [])] or None
    adj = json.loads(a.adjustments) if a.adjustments else None
    apr = engine.approve(a.approval_id, a.decision, a.by, a.rationale or "", a.option, adj, per, **_nr(a))
    run = engine.load_run(apr["run_id"]); print(f"{apr['approval_id']} {apr['type']} → {a.decision}; run={run['status']} current_task={run.get('current_task_id')}")

def cmd_approval_show(a):
    @operation.operation("approval_show")
    def _both(apr_id): approval_render.render(apr_id); approval_render.render_html(apr_id)
    _both(a.approval_id, **_nr(a)); print(f"approvals/{a.approval_id}.md + .html")

def cmd_req_export(a):
    if a.stdout: print(READONLY_NOTE); print(req_export.build(a.spec_id, a.spec_version)); return
    print(req_export.export(a.spec_id, a.spec_version, **_nr(a)))

def cmd_tc_retire(a):
    apr, suites = tc_ops.retire(a.tc_id, a.by, a.rationale, **_nr(a))
    print(f"{a.tc_id} → RETIRED via {apr}" + (f"；仍在 suite {[s['suite_id'] for s in suites]}，請另跑 regression-generation 移除" if suites else ""))
def cmd_tc_revise(a): run = tc_ops.revise(a.tc_id, a.reason, a.by, **_nr(a)); print(f"{run['run_id']} testcase-revision 已建立，current_task={run.get('current_task_id')}（Test Designer 產新版本 Draft → Validator → 你核准）")
def cmd_manual_new(a):
    rid = tc_ops.manual_new(a.title, a.product, a.area, a.step, a.observed, a.outcome, a.by, a.spec_id, a.spec_version, a.requirement_id, a.environment or "", a.precondition, a.evidence, a.notes or "", **_nr(a))
    print(f"{rid} → testcases/manual/{rid}.yaml；下一步：bin/qaos run new manual-test-to-regression --input manual_record_id={rid}" + (f" --input spec_id={a.spec_id} --input spec_version={a.spec_version}" if a.spec_id else "") + f" --by {a.by}")

def cmd_tc_export(a):
    if a.stdout: print(READONLY_NOTE); print(tc_export.build(a.area)); return
    print(tc_export.export(a.area, **_nr(a)))
def cmd_tc_final(a): n, g = final_export.export(a.area, **_nr(a)); print(f"testcases/final/{a.area}-final.html + -final-active.json（{n} 條 ACTIVE、{g} 項需求）")

def cmd_approvals(a):
    for p in store.glob("approvals/APR-*.yaml"):
        d = store.load(p)
        if a.all or d["status"] == "PENDING":
            print(f"{d['approval_id']} [{d['status']}] {d['type']} run={d['run_id']} — {d['summary']}")
            for it in d.get("batch_items", []): print(f"    · {it['entity_type']} {it['id']} v{it.get('version', '')}")

def cmd_trace(a): [print(l) for l in trace.trace(a.id)]
def cmd_suites_of(a): _print(trace.suites_of(a.tc_id))

def _src_kw(a) -> dict:
    return {"package": a.package, "package_file": a.package_file, "external_filename": a.external_filename, "external_version": a.external_version,
            "external_effective_date": a.external_effective_date, "external_commit": a.external_commit}

def cmd_spec_import(a):
    print(spec_ops.spec_import(a.file, a.spec_id, a.version, a.product, a.area, title=a.title, area_title=a.area_title, source=a.source,
                               change_summary=a.change_summary, supersede=a.supersede, by=a.by, analysis_policy_value=a.analysis_policy, **_src_kw(a), **_nr(a)))

def cmd_spec_ref_add(a): _print(spec_ops.reference_add(a.target, a.ref, a.role, a.by, scope=a.scope, **_nr(a)))
def cmd_spec_ref_remove(a): _print(spec_ops.reference_remove(a.target, a.ref, a.by, reason=a.reason, **_nr(a)))
def cmd_spec_ref_empty(a): _print(spec_ops.reference_declare_empty(a.target, a.reason, a.by, **_nr(a)))
def cmd_spec_meta_upgrade(a):
    _print(spec_ops.metadata_upgrade(a.target, a.by, a.reason, analysis_policy_value=a.analysis_policy, original_file=a.original_file, note=a.note, **_src_kw(a), **_nr(a)))

def cmd_evidence_add(a):
    if a.inline is None and not a.file: sys.exit("evidence add 需要 --file 或 --inline")
    print(evidence_add(a.type, a.by, file=a.file, inline=a.inline, owner=a.owner, execution_id=a.execution_id, description=a.description, captured_at=a.captured_at, **_nr(a)))

def cmd_execution_import(a):
    print(execution_import(a.result, a.environment, a.by, testcase_id=a.testcase_id, testcase_version=a.testcase_version, executor_type=a.executor_type,
                           build=a.build, executed_at=a.executed_at, actual_result=a.actual_result, evidence=a.evidence, notes=a.notes, **_nr(a)))

def cmd_bug_transition(a): print(bug_transition(a.bug_id, a.to, a.by, trigger=a.trigger, note=a.note, **_nr(a)))

def cmd_clr_new(a):
    c = clr.new(a.product, a.area, a.spec_id, a.spec_version, a.question, a.by, context=a.context or "", options=a.option or [], requirement_id=a.requirement_id, impact=a.impact, **_nr(a))
    print(f"{c['clarification_id']} → clarifications/{a.product}/{a.area}/{c['clarification_id']}.md")
def cmd_clr_ask(a): c = clr.ask(a.id, a.to, a.by, **_nr(a)); print(f"{c['clarification_id']} ASKED → {a.to}")
def cmd_clr_answer(a): c = clr.answer(a.id, a.answer, a.answered_by, a.resolution, a.by, a.spec_version, **_nr(a)); print(f"{c['clarification_id']} ANSWERED ({a.resolution})")
def cmd_clr_impact(a):
    cands = clr.impact(a.id, a.keyword or [])
    for x in cands: print(f"{x['testcase_id']} v{x['version']} [{', '.join(x['reasons'])}] {x['title']}")
    print(f"({len(cands)} 條候選；逐條判定後以 --impact-reviewed 寫入 apply)")
def cmd_clr_apply(a): clr.apply_(a.id, a.by, a.note or "", impact_reviewed=a.impact_reviewed, keywords=a.keyword or [], **_nr(a)); print(f"{a.id} APPLIED")
def cmd_clr_withdraw(a): clr.withdraw(a.id, a.by, a.note or "", **_nr(a)); print(f"{a.id} WITHDRAWN")
def cmd_clr_list(a):
    for c in clr.list_(open_only=not a.all): print(f"{c['clarification_id']} [{c['status']}] {c['product']}/{c['functional_area']} {c['spec_id']}@{c['spec_version']} — {c['question']}")
def cmd_clr_index(a): n = clr.build_index(**_nr(a)); print(f"clarifications/index.md（{n} 張）")
def _json_arg(text, name):
    try: return json.loads(text)
    except json.JSONDecodeError as e: raise ValueError(f"{name} 必須是 JSON：{e}")
def _role_scope(values): return ["*"] if values == ["*"] else values
def cmd_clr_applicability_add(a):
    _print(clr.applicability_add(a.id, a.answer_rev, a.requirement, a.subject, _role_scope(a.role_scope), _json_arg(a.params, "--params"), a.target, a.rationale, a.by,
                                 confirm_basis=a.confirm_basis, **_nr(a)))
def cmd_clr_addenda_add(a): clr.addenda_add(a.id, _json_arg(a.source, "--source"), a.note, a.by, **_nr(a)); print(f"{a.id} evidence_addenda +1")
def cmd_clr_meta_upgrade(a):
    c = clr.metadata_upgrade(a.id, a.by, a.reason, kind=a.kind, question_id=a.question_id, subject=a.subject,
                             role_scope=_role_scope(a.role_scope) if a.role_scope else None, params=_json_arg(a.params, "--params") if a.params else None, **_nr(a))
    print(f"{a.id} metadata upgraded")
def cmd_bug_resolve(a): b = bug_lifecycle.resolve(a.bug_id, a.by, a.external_ref, a.note or "", a.fixed_by or "", **_nr(a)); print(f"{a.bug_id} → {b['status']}")
def cmd_bug_verify(a): b = bug_lifecycle.verify(a.bug_id, a.execution, a.by, **_nr(a)); print(f"{a.bug_id} → {b['status']}")
def cmd_bug_close(a): b = bug_lifecycle.close(a.bug_id, a.by, a.rationale or "", **_nr(a)); print(f"{a.bug_id} → {b['status']} (done)")
def cmd_bug_index(a): print(f"{bugindex.build(**_nr(a))} bugs indexed → bugs/index.md + bugs/<product>/<area>/index.md")

def cmd_op_list(a):
    print(READONLY_NOTE)
    for o in operation.list_operations(a.incomplete):
        print(f"{o['plan_seq'] if o['plan_seq'] is not None else '-':>5} {o['state']:<20} {str(o['action'] or '?'):<22} {o['op_id']}")
def cmd_op_resume(a): _print(operation.resume(a.op_id)); print(f"{a.op_id} 已完成")
def cmd_maint_start(a): _print(operation.maintenance_start(a.by, **_nr(a)))
def cmd_maint_end(a): _print(operation.maintenance_end(a.by, **_nr(a)))
def cmd_migrate(a): _print(operation.migrate(a.by, a.acknowledge_idle or [], **_nr(a)))
def cmd_audit_render(a):
    if a.target and a.global_: sys.exit("audit render：<run_id> 和 --global 只能擇一")
    _print(operation.audit_render(None if a.global_ else a.target, **_nr(a)))

def main(argv=None):
    ap = argparse.ArgumentParser(prog="qaos", description="QAOS Deterministic Runtime"); sp = ap.add_subparsers(dest="cmd", required=True)
    W = argparse.ArgumentParser(add_help=False); W.add_argument("--new-request", action="store_true", help="刻意再執行一次相同內容的請求（產生新的 op）")
    p = sp.add_parser("validate"); p.add_argument("file"); p.add_argument("--schema"); p.set_defaults(f=cmd_validate)
    p = sp.add_parser("id", parents=[W]); p.add_argument("kind"); p.add_argument("--area"); p.set_defaults(f=cmd_id)
    r = sp.add_parser("run"); rs = r.add_subparsers(dest="sub", required=True)
    p = rs.add_parser("new", parents=[W]); p.add_argument("workflow"); p.add_argument("--input", action="append", metavar="key=value"); p.add_argument("--by", required=True); p.set_defaults(f=cmd_run_new)
    p = rs.add_parser("show"); p.add_argument("run_id"); p.set_defaults(f=cmd_run_show)
    p = rs.add_parser("cancel", parents=[W]); p.add_argument("run_id"); p.add_argument("--by", required=True); p.set_defaults(f=cmd_run_cancel)
    p = sp.add_parser("submit", parents=[W]); p.add_argument("run_id"); p.add_argument("task_id"); p.add_argument("artifact"); p.set_defaults(f=cmd_submit)
    p = sp.add_parser("gate", parents=[W]); p.add_argument("run_id"); p.add_argument("task_id"); p.set_defaults(f=cmd_gate)
    p = sp.add_parser("approve", parents=[W]); p.add_argument("approval_id"); p.add_argument("--decision", required=True, choices=["approve", "reject", "override"]); p.add_argument("--by", required=True)
    p.add_argument("--rationale"); p.add_argument("--option"); p.add_argument("--adjustments", help='JSON，如 {"severity":"critical"}'); p.add_argument("--per-item", action="append", metavar="ID:decision"); p.set_defaults(f=cmd_approve)
    p = sp.add_parser("approvals"); p.add_argument("--all", action="store_true"); p.set_defaults(f=cmd_approvals)
    p = sp.add_parser("approval", parents=[W]); p.add_argument("approval_id"); p.set_defaults(f=cmd_approval_show)
    p = sp.add_parser("tc-export", parents=[W]); p.add_argument("area"); p.add_argument("--stdout", action="store_true", help="唯讀：輸出到 stdout，不寫檔、不取鎖"); p.set_defaults(f=cmd_tc_export)
    p = sp.add_parser("tc-final", parents=[W], help="重匯 testcases/final/<AREA>-final.html／json（DoD）"); p.add_argument("area"); p.set_defaults(f=cmd_tc_final)
    t = sp.add_parser("tc", help="正式 Test Case 的 Human 操作"); ts = t.add_subparsers(dest="sub", required=True)
    p = ts.add_parser("retire", parents=[W], help="退役一條 ACTIVE TC"); p.add_argument("tc_id"); p.add_argument("--rationale", required=True); p.add_argument("--by", required=True); p.set_defaults(f=cmd_tc_retire)
    p = ts.add_parser("revise", parents=[W], help="對 ACTIVE TC 發起修訂（產新版本，舊版保留）"); p.add_argument("tc_id"); p.add_argument("--reason", required=True); p.add_argument("--by", required=True); p.set_defaults(f=cmd_tc_revise)
    mn = sp.add_parser("manual", help="人工測試紀錄"); ms = mn.add_subparsers(dest="sub", required=True)
    p = ms.add_parser("new", parents=[W]); p.add_argument("--title", required=True); p.add_argument("--product", required=True); p.add_argument("--area", required=True); p.add_argument("--step", action="append", required=True, help="可重複，依序")
    p.add_argument("--observed", required=True); p.add_argument("--outcome", required=True, choices=["pass", "fail", "blocked"]); p.add_argument("--spec-id"); p.add_argument("--spec-version"); p.add_argument("--requirement-id", action="append")
    p.add_argument("--environment"); p.add_argument("--precondition", action="append"); p.add_argument("--evidence", action="append"); p.add_argument("--notes"); p.add_argument("--by", required=True); p.set_defaults(f=cmd_manual_new)
    p = sp.add_parser("req-export", parents=[W]); p.add_argument("spec_id"); p.add_argument("spec_version"); p.add_argument("--stdout", action="store_true", help="唯讀：輸出到 stdout，不寫檔、不取鎖"); p.set_defaults(f=cmd_req_export)
    p = sp.add_parser("trace"); p.add_argument("id"); p.set_defaults(f=cmd_trace)
    p = sp.add_parser("suites-of"); p.add_argument("tc_id"); p.set_defaults(f=cmd_suites_of)
    s = sp.add_parser("spec"); ss = s.add_subparsers(dest="sub", required=True)
    SRC = argparse.ArgumentParser(add_help=False)
    SRC.add_argument("--package", help="開發包名稱"); SRC.add_argument("--package-file", help="開發包 zip 或 manifest；計算 package_sha256")
    SRC.add_argument("--external-filename"); SRC.add_argument("--external-version", help="外部版本標示"); SRC.add_argument("--external-effective-date", help="外部文件宣告的生效日（只當參考）")
    SRC.add_argument("--external-commit", help="來源聲稱的 commit（記錄為 claimed: true）")
    p = ss.add_parser("import", parents=[W, SRC]); p.add_argument("file"); p.add_argument("--spec-id", required=True); p.add_argument("--version", required=True); p.add_argument("--product", required=True); p.add_argument("--area", required=True)
    p.add_argument("--title"); p.add_argument("--area-title"); p.add_argument("--source", help="來源 URI（舊欄位 source_uri）"); p.add_argument("--change-summary"); p.add_argument("--supersede", action="store_true"); p.add_argument("--by", required=True)
    p.add_argument("--analysis-policy", choices=["analyze", "reference_only"], help="reference_only：只當參考文件，不建需求模型、不能當 run 目標")
    p.set_defaults(f=cmd_spec_import)
    r = ss.add_parser("reference", help="引用宣告（只能由人執行）"); rs = r.add_subparsers(dest="sub2", required=True)
    p = rs.add_parser("add", parents=[W]); p.add_argument("target", metavar="SPEC_ID@VER"); p.add_argument("--ref", required=True, metavar="SPEC_ID@VER"); p.add_argument("--role", required=True, choices=["normative", "informative"])
    p.add_argument("--scope", help="章節或關鍵段落說明"); p.add_argument("--by", required=True); p.set_defaults(f=cmd_spec_ref_add)
    p = rs.add_parser("remove", parents=[W]); p.add_argument("target", metavar="SPEC_ID@VER"); p.add_argument("--ref", required=True, metavar="SPEC_ID@VER"); p.add_argument("--reason", help="移除最後一個引用時必填")
    p.add_argument("--by", required=True); p.set_defaults(f=cmd_spec_ref_remove)
    p = rs.add_parser("declare-empty", parents=[W]); p.add_argument("target", metavar="SPEC_ID@VER"); p.add_argument("--reason", required=True); p.add_argument("--by", required=True); p.set_defaults(f=cmd_spec_ref_empty)
    mt = ss.add_parser("metadata", help="metadata 升級（只補 legacy 條目缺少的欄位）"); mts = mt.add_subparsers(dest="sub2", required=True)
    p = mts.add_parser("upgrade", parents=[W, SRC]); p.add_argument("target", metavar="SPEC_ID@VER"); p.add_argument("--analysis-policy", choices=["analyze", "reference_only"])
    p.add_argument("--original-file", help="補 source 時必填：原檔，由指令重算 source_bytes_sha256"); p.add_argument("--note", help="原檔 hash 和 content_hash 不同時必填")
    p.add_argument("--reason", required=True); p.add_argument("--by", required=True); p.set_defaults(f=cmd_spec_meta_upgrade)
    e = sp.add_parser("evidence"); es = e.add_subparsers(dest="sub", required=True)
    p = es.add_parser("add", parents=[W]); p.add_argument("--type", required=True); p.add_argument("--file"); p.add_argument("--inline"); p.add_argument("--owner", help="exe_id 或 bug 暫時歸屬目錄"); p.add_argument("--execution-id")
    p.add_argument("--description"); p.add_argument("--captured-at"); p.add_argument("--by", required=True); p.set_defaults(f=cmd_evidence_add)
    x = sp.add_parser("execution"); xs = x.add_subparsers(dest="sub", required=True)
    p = xs.add_parser("import", parents=[W]); p.add_argument("--testcase-id"); p.add_argument("--testcase-version", type=int); p.add_argument("--result", required=True, choices=["pass", "fail", "blocked", "skipped"])
    p.add_argument("--executor-type", default="human", choices=["human", "ci"]); p.add_argument("--environment", required=True); p.add_argument("--build"); p.add_argument("--executed-at"); p.add_argument("--actual-result")
    p.add_argument("--evidence", action="append"); p.add_argument("--notes"); p.add_argument("--by", required=True); p.set_defaults(f=cmd_execution_import)
    b = sp.add_parser("bug"); bs = b.add_subparsers(dest="sub", required=True)
    p = bs.add_parser("transition", parents=[W]); p.add_argument("bug_id"); p.add_argument("--to", required=True); p.add_argument("--by", required=True); p.add_argument("--trigger"); p.add_argument("--note"); p.set_defaults(f=cmd_bug_transition)
    p = bs.add_parser("index", parents=[W]); p.set_defaults(f=cmd_bug_index)
    p = bs.add_parser("resolve", parents=[W], help="QA 依共用表單登記 RD 已修復"); p.add_argument("bug_id"); p.add_argument("--external-ref", required=True); p.add_argument("--note"); p.add_argument("--fixed-by"); p.add_argument("--by", required=True); p.set_defaults(f=cmd_bug_resolve)
    p = bs.add_parser("verify", parents=[W], help="QA 複測：附 Execution（含 Evidence）"); p.add_argument("bug_id"); p.add_argument("--execution", required=True); p.add_argument("--by", required=True); p.set_defaults(f=cmd_bug_verify)
    p = bs.add_parser("close", parents=[W], help="結案（= done）"); p.add_argument("bug_id"); p.add_argument("--rationale"); p.add_argument("--by", required=True); p.set_defaults(f=cmd_bug_close)
    c = sp.add_parser("clarification", help="問 PM 的單子"); cs = c.add_subparsers(dest="sub", required=True)
    p = cs.add_parser("new", parents=[W]); p.add_argument("--product", required=True); p.add_argument("--area", required=True); p.add_argument("--spec-id", required=True); p.add_argument("--spec-version", required=True)
    p.add_argument("--question", required=True); p.add_argument("--context"); p.add_argument("--option", action="append"); p.add_argument("--requirement-id"); p.add_argument("--impact"); p.add_argument("--by", required=True); p.set_defaults(f=cmd_clr_new)
    p = cs.add_parser("ask", parents=[W]); p.add_argument("id"); p.add_argument("--to", required=True); p.add_argument("--by", required=True); p.set_defaults(f=cmd_clr_ask)
    p = cs.add_parser("answer", parents=[W]); p.add_argument("id"); p.add_argument("--answer", required=True); p.add_argument("--answered-by", required=True); p.add_argument("--resolution", required=True, choices=["spec_updated", "requirement_clarified", "no_change", "out_of_scope"]); p.add_argument("--spec-version"); p.add_argument("--by", required=True); p.set_defaults(f=cmd_clr_answer)
    p = cs.add_parser("impact", help="ADR-008：apply 前的影響掃描"); p.add_argument("id"); p.add_argument("--keyword", action="append"); p.set_defaults(f=cmd_clr_impact)
    p = cs.add_parser("apply", parents=[W]); p.add_argument("id"); p.add_argument("--by", required=True); p.add_argument("--note"); p.add_argument("--impact-reviewed", help="ADR-008：對 impact 候選 TC 的逐條結論（必填）"); p.add_argument("--keyword", action="append"); p.set_defaults(f=cmd_clr_apply)
    p = cs.add_parser("withdraw", parents=[W]); p.add_argument("id"); p.add_argument("--by", required=True); p.add_argument("--note"); p.set_defaults(f=cmd_clr_withdraw)
    p = cs.add_parser("list", help="唯讀：列出 CLR"); p.add_argument("--all", action="store_true"); p.set_defaults(f=cmd_clr_list)
    p = cs.add_parser("index", parents=[W], help="寫檔：重建 clarifications/index.md"); p.set_defaults(f=cmd_clr_index)
    ap_ = cs.add_parser("applicability", help="人工適用紀錄（只能由人執行）"); aps = ap_.add_subparsers(dest="sub2", required=True)
    p = aps.add_parser("add", parents=[W]); p.add_argument("id"); p.add_argument("--answer-rev", type=int, required=True); p.add_argument("--requirement", required=True)
    p.add_argument("--subject", required=True); p.add_argument("--role-scope", action="append", required=True, help="可重複；與角色無關時只給一個 *")
    p.add_argument("--params", required=True, help='JSON 物件；沒有參數限制時明寫 {}'); p.add_argument("--target", required=True, metavar="SPEC_ID@VER", help="決定 scope 的 spec 與本次 basis")
    p.add_argument("--rationale", required=True); p.add_argument("--confirm-basis", help="CLI 顯示的本次 basis_hash；相同才寫入"); p.add_argument("--by", required=True)
    p.set_defaults(f=cmd_clr_applicability_add)
    ad = cs.add_parser("addenda", help="補充佐證（只能追加）"); ads = ad.add_subparsers(dest="sub2", required=True)
    p = ads.add_parser("add", parents=[W]); p.add_argument("id"); p.add_argument("--source", required=True, help="SourceRef 或 document 型來源（JSON）")
    p.add_argument("--note", required=True); p.add_argument("--by", required=True); p.set_defaults(f=cmd_clr_addenda_add)
    cm = cs.add_parser("metadata", help="舊 CLR 的 metadata 升級（只補缺的欄位）"); cms = cm.add_subparsers(dest="sub2", required=True)
    p = cms.add_parser("upgrade", parents=[W]); p.add_argument("id"); p.add_argument("--kind", choices=["spec_question", "conflict_resolution", "document_request"])
    p.add_argument("--question-id"); p.add_argument("--subject"); p.add_argument("--role-scope", action="append"); p.add_argument("--params", help="JSON 物件")
    p.add_argument("--reason", required=True); p.add_argument("--by", required=True); p.set_defaults(f=cmd_clr_meta_upgrade)
    o = sp.add_parser("operation", help="操作計畫：查詢與續做"); os_ = o.add_subparsers(dest="sub", required=True)
    p = os_.add_parser("list", help="唯讀：列出操作計畫與狀態"); p.add_argument("--incomplete", action="store_true"); p.set_defaults(f=cmd_op_list)
    p = os_.add_parser("resume", help="續做一份未完成的計畫"); p.add_argument("op_id"); p.set_defaults(f=cmd_op_resume)
    m = sp.add_parser("maintenance", help="維護模式"); mss = m.add_subparsers(dest="sub", required=True)
    p = mss.add_parser("start", parents=[W]); p.add_argument("--by", required=True); p.set_defaults(f=cmd_maint_start)
    p = mss.add_parser("end", parents=[W]); p.add_argument("--by", required=True); p.set_defaults(f=cmd_maint_end)
    p = sp.add_parser("migrate", parents=[W], help="移轉既有資料（維護中執行）"); p.add_argument("--by", required=True); p.add_argument("--acknowledge-idle", action="append", metavar="RUN_ID"); p.set_defaults(f=cmd_migrate)
    au = sp.add_parser("audit"); aus = au.add_subparsers(dest="sub", required=True)
    p = aus.add_parser("render", parents=[W], help="重建 audit.log（<run_id>；不給或 --global 為全域 runs/_audit.log）")
    p.add_argument("target", nargs="?", metavar="RUN_ID"); p.add_argument("--global", dest="global_", action="store_true"); p.set_defaults(f=cmd_audit_render)
    a = ap.parse_args(argv)
    try:
        try: a.f(a)
        except SystemExit: _notice(); raise     # gate FAIL 等以非零結束的指令，也要提示「先前已完成」
        _notice()
    except (EngineError, TransitionError, FileNotFoundError, ValueError, operation.OperationError, store.NoExecutorContext) as e:
        sys.exit(f"qaos: {e}")

if __name__ == "__main__": main()
