"""Workflow 引擎：Run 建立、Artifact 提交（Permission Guard + Structural Gate）、Gate 評估與效果、Approval、Commit。
Agent 永遠不呼叫這裡的 commit；只有 approve() 在 Human 決定後觸發。"""
import pathlib
from . import store, schema, ids, state, refs, gates, clarification as clr
from .state import TransitionError

SYSTEM = "system"

class EngineError(Exception): pass

# ---------- 載入設定 ----------
_agents = None
def agents():
    global _agents
    if _agents is None:
        _agents = {}
        for p in (store.ROOT / "agents").glob("*.yaml"):
            a = store.load(p); _agents[a["id"]] = a
    return _agents

def workflow(workflow_id: str) -> dict:
    return store.load(f"workflows/{workflow_id}.yaml")

# ---------- Run ----------
def _expand_tasks(wf: dict, inputs: dict) -> list[dict]:
    tasks = []
    for t in wf["tasks"]:
        task = {"task_id": t["id"], "type": t.get("type", "agent"), "status": "PENDING", "iteration": 0,
                "input_artifact_ids": [], "input_entity_refs": [], "output_artifact_ids": []}
        if task["type"] == "agent": task["agent_id"] = t["agent"]
        if t.get("mode"): task["mode"] = t["mode"]
        if t.get("phase"): task["mode"] = t["phase"]
        if t.get("gate"): task["gate"] = t["gate"].split(".")[0]
        tasks.append(task)
        if wf["workflow_id"] == "spec-to-testcase" and t["id"] == "T2" and inputs.get("analysis_review") == "required":
            tasks.append({"task_id": "T2R", "type": "approval", "status": "PENDING", "iteration": 0,
                          "input_artifact_ids": [], "input_entity_refs": [], "output_artifact_ids": []})
    return tasks

def _wf_task(wf: dict, task_id: str) -> dict:
    if task_id == "T2R": return {"id": "T2R", "type": "approval", "approval_type": "REVIEW_TEST_ANALYSIS"}
    return next(t for t in wf["tasks"] if t["id"] == task_id)

def _skip(wf: dict, wt: dict, inputs: dict) -> bool:
    """run_if / skip_if 的機械判斷（Phase 2 只支援 RequirementModel 存在性）。"""
    cond = wt.get("skip_if") or (f"NOT({wt['run_if']})" if wt.get("run_if") else None)
    if not cond: return False
    ver = inputs.get("spec_version") or inputs.get("to_version")
    exists = store.exists(store.requirements_path(inputs["spec_id"], ver)) if inputs.get("spec_id") and ver else False
    if wt.get("skip_if"): return exists
    return exists  # run_if "NOT exists" → skip when exists

def new_run(workflow_id: str, inputs: dict, by: str) -> dict:
    wf = workflow(workflow_id)
    missing = [k for k, v in wf["input"]["fields"].items() if v.get("required") and k not in inputs and k != "initiated_by"]
    if missing: raise EngineError(f"缺少必要 input：{missing}")
    if workflow_id == "spec-to-bug" and not inputs.get("evidence_ids"):
        raise EngineError("No Evidence, No Formal Bug：spec-to-bug 需要 evidence_ids")
    for eid in inputs.get("evidence_ids", []):
        err = refs.resolve({"entity_type": "Evidence", "id": eid})
        if err: raise EngineError(err)
    if inputs.get("spec_id"):
        for k in ("spec_version", "from_version", "to_version"):
            if inputs.get(k):
                err = refs.resolve({"entity_type": "SpecVersion", "id": inputs["spec_id"], "version": inputs[k]})
                if err: raise EngineError(err)
    run_id = ids.alloc("RUN")
    run = {"run_id": run_id, "workflow_id": workflow_id, "workflow_version": wf["version"], "status": None,
           "input": {**inputs, "initiated_by": by}, "initiated_by": by, "created_at": store.now(), "updated_at": store.now(),
           "tasks": _expand_tasks(wf, inputs), "history": []}
    state.apply("workflow_run", run, "CREATED", SYSTEM, f"new_run by {by}", run_id)
    state.apply("workflow_run", run, "RUNNING", SYSTEM, "task graph expanded", run_id)
    _save_run(run)
    store.audit(run_id, by, "CREATE_WORKFLOW_RUN", workflow_id)
    _advance(run)
    return run

def load_run(run_id: str) -> dict:
    return store.load(f"runs/{run_id}/run.yaml")

def _save_run(run: dict):
    run["updated_at"] = store.now()
    errs = schema.errors(run, "workflow/workflow-run.schema.json")
    if errs: raise EngineError("run.yaml 不符 schema：" + "; ".join(errs[:3]))
    store.save(f"runs/{run['run_id']}/run.yaml", run)

def _task(run: dict, task_id: str) -> dict:
    return next(t for t in run["tasks"] if t["task_id"] == task_id)

def _next_task(run: dict, after: str | None) -> dict | None:
    ids_ = [t["task_id"] for t in run["tasks"]]
    i = ids_.index(after) + 1 if after else 0
    return run["tasks"][i] if i < len(run["tasks"]) else None

def _advance(run: dict, after: str | None = None):
    """把下一個 PENDING task 變 READY；approval task 自動建立 ApprovalRequest；summary task 自動完成；到底則 COMPLETED。"""
    wf = workflow(run["workflow_id"])
    t = _next_task(run, after)
    while t is not None:
        wt = _wf_task(wf, t["task_id"])
        if t["type"] == "agent" and _skip(wf, wt, run["input"]):
            t["status"] = "DONE"; store.audit(run["run_id"], SYSTEM, "SKIP_TASK", t["task_id"]); t = _next_task(run, t["task_id"]); continue
        if t["type"] == "approval":
            state.apply("task", t, "READY", SYSTEM, "advance"); state.apply("task", t, "RUNNING", SYSTEM, "advance")
            _create_approval_for_task(run, t, wt["approval_type"]); _save_run(run); return
        if t["type"] == "agent" and t["agent_id"] == "agent-supervisor" and "WorkflowSummary" in (wt.get("outputs") or []):
            state.apply("task", t, "READY", SYSTEM, "advance"); state.apply("task", t, "RUNNING", SYSTEM, "advance")
            _summarize(run, t); return
        state.apply("task", t, "READY", SYSTEM, "advance"); run["current_task_id"] = t["task_id"]; _save_run(run); return
    if run["status"] == "RUNNING":
        state.apply("workflow_run", run, "COMPLETED", SYSTEM, "all tasks done", run["run_id"]); _save_run(run)

# ---------- Submit（Permission Guard + Structural Gate 第一層） ----------
def submit(run_id: str, task_id: str, artifact_path: str) -> tuple[bool, list[str]]:
    run = load_run(run_id); task = _task(run, task_id); problems = []
    if run["status"] != "RUNNING": raise EngineError(f"Run 狀態 {run['status']}，不接受提交")
    if task["type"] != "agent": raise EngineError(f"{task_id} 不是 agent task")
    if task["status"] == "READY": state.apply("task", task, "RUNNING", SYSTEM, "first submit"); task["started_at"] = store.now()
    if task["status"] != "RUNNING": raise EngineError(f"{task_id} 狀態 {task['status']}，不接受提交")
    p = pathlib.Path(artifact_path).resolve()
    rel = p.relative_to(store.ROOT).as_posix()
    art = store.load(p)
    problems += schema.errors(art, "artifact/envelope.schema.json")
    if problems:
        _mark_invalid(run, task, art, p, problems); return False, problems
    agent = agents()[task["agent_id"]]
    # Permission Guard
    if art["created_by"] != task["agent_id"]: problems.append(f"created_by {art['created_by']} ≠ task agent {task['agent_id']}（越權）")
    if art["artifact_type"] not in agent["produces"]: problems.append(f"{task['agent_id']} 無權產出 {art['artifact_type']}（produces={agent['produces']}）")
    if not any(rel.startswith(w.replace("<run_id>", run_id).replace("/**", "/")) for w in agent["write_paths"]):
        problems.append(f"寫入路徑 {rel} 不在 {task['agent_id']} 的 write_paths")
    if art["run_id"] != run_id or art["task_id"] != task_id: problems.append("artifact 的 run_id/task_id 與提交目標不符")
    if p.stem != art["artifact_id"]: problems.append(f"檔名 {p.name} 必須等於 artifact_id")
    if art["status"] not in ("DRAFT", "SUBMITTED"): problems.append(f"artifact 狀態 {art['status']} 不可提交")
    # 引用逐一存在
    for r in art["references"]:
        err = refs.resolve(r)
        if err: problems.append(f"reference: {err}")
    # 輸入 artifact 必須是 dispatch 指定的（Phase 2：必須屬於本 run 且 VALID）
    for r in art["references"]:
        if r["entity_type"] == "Artifact":
            a = store.load(store.find_artifact(r["id"]))
            if a["run_id"] != run_id and a["artifact_type"] != "RequirementModel" and art["artifact_type"] not in ("ChangeImpactReport", "TestCaseDraft", "BugDraft"):   # RequirementModel 為跨 run 持久參考
                problems.append(f"引用了其他 run 的 artifact {r['id']}")
    # payload 語意前置
    if art["artifact_type"] == "TestCaseDraft":
        for tc in art["payload"]["testcases"]:
            if tc["source"] != {"spec": "spec_workflow", "change": "change_workflow", "manual": "manual_integration"}[art["payload"]["mode"]]:
                problems.append(f"{tc['draft_id']} source 與 mode 不一致")
    if problems:
        _mark_invalid(run, task, art, p, problems); return False, problems
    # VALID
    art["status"] = "SUBMITTED"; state.apply("artifact", art, "VALID", SYSTEM, "structural gate", run_id)
    store.save(p, art)
    for old in task["output_artifact_ids"]:
        op = store.find_artifact(old)
        if op is None: continue   # artifact 檔案已不存在（例如人工清理過），沒有東西可標 SUPERSEDED，略過而非崩潰
        o = store.load(op)
        if o["artifact_type"] == art["artifact_type"] and o["status"] == "VALID":
            state.apply("artifact", o, "SUPERSEDED", SYSTEM, f"replaced by {art['artifact_id']}", run_id); store.save(op, o)
    task["output_artifact_ids"].append(art["artifact_id"])
    task.setdefault("gate_results", []).append({"at": store.now(), "layer": "structural", "result": "PASS", "details": [f"{art['artifact_type']} {art['artifact_id']} VALID"]})
    _save_run(run); store.audit(run_id, task["agent_id"], "SUBMIT_ARTIFACT", f"{art['artifact_type']} {art['artifact_id']} VALID")
    return True, []

def _mark_invalid(run, task, art, p, problems):
    if isinstance(art, dict) and art.get("artifact_id") and art.get("status") in ("DRAFT", "SUBMITTED"):
        # 只有本次真正被評估中的 artifact（DRAFT/SUBMITTED）才標 INVALID；
        # 若問題是「artifact 狀態 X 不可提交」這種 client 端誤用已存在的 VALID/SUPERSEDED artifact，不得覆寫其狀態。
        art["status"] = "INVALID"; art.setdefault("history", None)
        art.pop("history", None); store.save(p, art)
    task.setdefault("gate_results", []).append({"at": store.now(), "layer": "structural", "result": "FAIL", "details": problems[:20]})
    if any("越權" in x or "無權" in x or "write_paths" in x for x in problems):
        task.setdefault("permission_violations", []).append({"at": store.now(), "action": "CREATE_ARTIFACT", "detail": "; ".join(problems)[:500]})
        state.apply("task", task, "FAILED", SYSTEM, "permission violation")
        state.apply("workflow_run", run, "FAILED", SYSTEM, f"{task['task_id']} permission violation", run["run_id"])
        store.audit(run["run_id"], task.get("agent_id", "?"), "PERMISSION_VIOLATION", "; ".join(problems)[:300])
    else:
        state.apply("task", task, "ARTIFACT_INVALID", SYSTEM, "structural fail")
        n = sum(1 for g in task["gate_results"] if g["layer"] == "structural" and g["result"] == "FAIL")
        if n >= 3:
            _create_approval(run, task, "NEEDS_DECISION", f"{task['task_id']} 連續 {n} 次 Structural FAIL", [], [], options=[{"key": "retry", "label": "重新 dispatch"}, {"key": "cancel", "label": "取消 run"}])
        else:
            state.apply("task", task, "READY", SYSTEM, "retry allowed")
        store.audit(run["run_id"], task.get("agent_id", "?"), "ARTIFACT_INVALID", "; ".join(problems)[:300])
    _save_run(run)

# ---------- Gate 評估與效果 ----------
def _valid_outputs(task) -> dict:
    out = {}
    for aid in task["output_artifact_ids"]:
        p = store.find_artifact(aid)
        if p is None: continue   # artifact 檔案已不存在，略過而非崩潰
        a = store.load(p)
        if a["status"] == "VALID": out[a["artifact_type"]] = a
    return out

def evaluate_gate(run_id: str, task_id: str) -> dict:
    run = load_run(run_id); task = _task(run, task_id); wf = workflow(run["workflow_id"]); wt = _wf_task(wf, task_id)
    if run["status"] != "RUNNING": raise EngineError(f"Run 狀態 {run['status']}")
    if task["status"] == "READY" and _valid_outputs(task):
        state.apply("task", task, "RUNNING", SYSTEM, "gate re-evaluation on existing VALID artifacts")   # Gate 規則修正後可直接重評
    if task["status"] != "RUNNING": raise EngineError(f"{task_id} 狀態 {task['status']}，需先 submit artifact")
    arts = _valid_outputs(task)
    expected = wt.get("outputs") or []
    missing = [o for o in expected if o not in arts]
    if missing: raise EngineError(f"尚缺 VALID artifact：{missing}")
    gate = task.get("gate")
    issues = gates.GATES[gate](run, task, arts) if gate else []
    task.setdefault("gate_results", []).append({"at": store.now(), "layer": "structural", "result": "FAIL" if issues else "PASS", "details": issues[:20] or [f"{gate} structural PASS"]})
    if issues:
        state.apply("task", task, "GATE_FAILED", SYSTEM, f"{gate} structural"); state.apply("task", task, "READY", SYSTEM, "revise")
        _save_run(run); store.audit(run_id, SYSTEM, "GATE_FAIL", f"{gate} structural: " + "; ".join(issues)[:300])
        return {"gate": gate, "layer": "structural", "result": "FAIL", "issues": issues}
    sem = gates.semantic_result(gate, arts)
    if sem is not None:
        task["gate_results"].append({"at": store.now(), "layer": "semantic", "result": "PASS" if sem == "PASS" else "FAIL", "details": [f"validator result = {sem}"]})
    result = {"gate": gate, "layer": "semantic" if sem else "structural", "result": sem or "PASS", "issues": []}
    _apply_effects(run, task, wf, wt, arts, sem)
    return result

def _apply_effects(run, task, wf, wt, arts, sem):
    run_id = run["run_id"]; gate = task.get("gate")
    if gate == "G-SPEC":
        _persist_requirements(run, task, arts["RequirementModel"])
        _open_rejection_clarifications(run, arts["RequirementModel"])
        if _has_unresolved_critical(arts["RequirementModel"]):
            state.apply("task", task, "DONE", SYSTEM, "G-SPEC PASS (critical ambiguity)")
            apr = _create_approval(run, task, "RESOLVE_AMBIGUITY", "Spec 有 critical ambiguity，需 Human 決定解讀", [], [arts["RequirementModel"]["artifact_id"]],
                             options=[{"key": "resolved", "label": "已選定解讀（於 requirements.yaml 填 resolved_by_approval）"}, {"key": "return_to_author", "label": "退回 Spec 作者"}], reopen_task=task["task_id"])
            _open_clarifications(run, apr, arts["RequirementModel"]); _save_run(run); return
    elif gate == "G-DESIGN":
        tcs = arts["TestCaseDraft"]["payload"]["testcases"]; n_exp = sum(1 for tc in tcs if gates.is_exploratory(tc))
        if arts["TestCaseDraft"]["payload"]["mode"] == "spec" and len(tcs) >= 5 and n_exp / len(tcs) > 0.5:   # 佔比規則只對整包 spec 設計有意義
            state.apply("task", task, "DONE", SYSTEM, "G-DESIGN PASS (exploratory > 50%)")
            _create_approval(run, task, "NEEDS_DECISION", f"Draft 中 {n_exp}/{len(tcs)} 條為 exploratory（Spec 缺錯誤契約）。先補 Spec 還是繼續驗證？", [], [arts["TestCaseDraft"]["artifact_id"], arts["TestDesignReport"]["artifact_id"]],
                             options=[{"key": "continue", "label": "繼續進 Validator（假設將在 ACTIVATE 逐項確認）"}, {"key": "retry", "label": "退回 Designer（等 Spec 補完錯誤契約）"}, {"key": "cancel", "label": "取消 run"}])
            apr = store.load(f"approvals/{run['waiting_on_approval_id']}.yaml"); apr["diff_summary"] = f"continue_after={task['task_id']}"; store.save(f"approvals/{apr['approval_id']}.yaml", apr)
            _save_run(run); return
    elif gate == "G-TVAL":
        ci_path = f"runs/{run_id}/entities/change-impact.yaml"; ci = store.load(ci_path) if store.exists(ci_path) else None
        if ci and ci["status"] == "TEST_UPDATE_REQUIRED": state.apply("change_impact", ci, "VALIDATING", SYSTEM, "validator dispatched", run_id)
        if sem == "FAIL":
            if ci: state.apply("change_impact", ci, "TEST_UPDATE_REQUIRED", SYSTEM, "validation FAIL", run_id); store.save(ci_path, ci)
            _route_back(run, task, wf, arts["TestValidationReport"]); return
        if ci: state.apply("change_impact", ci, "COMPARING", SYSTEM, "validation PASS", run_id); store.save(ci_path, ci)
        _materialize_testcases(run, task, arts["TestValidationReport"])
    elif gate == "G-BVAL" and "BugValidationReport" in arts:
        if sem == "FAIL": _route_back(run, task, wf, arts["BugValidationReport"]); return
        if sem == "DUPLICATE":
            state.apply("task", task, "DONE", SYSTEM, "validator DUPLICATE")
            _bug_entity_transition(run, "VALIDATION_FAILED", "validator DUPLICATE")
            _create_approval(run, task, "CONFIRM_DUPLICATE", f"Bug Validator 判定重複於 {arts['BugValidationReport']['payload']['duplicate_check']['duplicate_of']}", [], [arts["BugValidationReport"]["artifact_id"]],
                             options=[{"key": "approve", "label": "確認重複 → REJECTED"}, {"key": "reject", "label": "非重複 → 退回 Bug Analyst"}]); _save_run(run); return
        if sem == "AMBIGUITY":
            state.apply("task", task, "DONE", SYSTEM, "validator AMBIGUITY")
            _bug_entity_transition(run, "AMBIGUITY_ESCALATED", "validator AMBIGUITY")
            _create_approval(run, task, "RESOLVE_AMBIGUITY", "Bug Validator 判定為需求 ambiguity", [], [arts["BugValidationReport"]["artifact_id"]],
                             options=[{"key": "approve", "label": "澄清後退回 Bug Analyst 重分析"}, {"key": "reject", "label": "非 Bug → REJECTED"}]); _save_run(run); return
        _bug_entity_transition(run, "VALIDATED", arts["BugValidationReport"]["artifact_id"], validator=task["agent_id"], report_id=arts["BugValidationReport"]["artifact_id"])
    elif gate == "G-BVAL" and "BugDraft" in arts:
        _bug_entity_init(run, task, arts["BugDraft"])
    elif gate == "G-IMPACT":
        p = arts["ChangeImpactReport"]["payload"]
        ci = _ci_entity(run, p)
        impacted = any(t["impact"] != "unaffected" for t in p["testcase_impact"]) or bool(p.get("new_required"))
        state.apply("change_impact", ci, "IMPACTED" if impacted else "NO_IMPACT", SYSTEM, arts["ChangeImpactReport"]["artifact_id"], run["run_id"])
        if impacted: state.apply("change_impact", ci, "TEST_UPDATE_REQUIRED", SYSTEM, "dispatch designer", run["run_id"])
        store.save(f"runs/{run['run_id']}/entities/change-impact.yaml", ci)
        if not impacted:
            state.apply("task", task, "DONE", SYSTEM, "NO_IMPACT")
            for t in run["tasks"]:
                if t["status"] == "PENDING" and not (t["type"] == "agent" and t.get("agent_id") == "agent-supervisor"): t["status"] = "DONE"
            _advance(run, task["task_id"]); return
    state.apply("task", task, "DONE", SYSTEM, f"{gate or 'no-gate'} PASS"); task["ended_at"] = store.now()
    store.audit(run_id, SYSTEM, "GATE_PASS", f"{task['task_id']} {gate}")
    _advance(run, task["task_id"])

def _route_back(run, task, wf, report):
    """Validator FAIL → 前一個 agent task 重新 READY（iteration+1），報告成為其 input；超限 → HUMAN_OVERRIDE。"""
    state.apply("task", task, "DONE", SYSTEM, f"validator FAIL ({report['artifact_id']})")
    ids_ = [t["task_id"] for t in run["tasks"]]; i = ids_.index(task["task_id"])
    gen = next(t for t in reversed(run["tasks"][:i]) if t["type"] == "agent" and t["status"] == "DONE" and t.get("agent_id") != "agent-supervisor")
    gen["iteration"] += 1; gen["input_artifact_ids"].append(report["artifact_id"])
    if run["workflow_id"] in ("spec-to-bug",): _bug_entity_transition(run, "VALIDATION_FAILED", report["artifact_id"]); _bug_entity_transition(run, "DRAFT", "revise")
    maxit = wf.get("max_validation_iterations", 3)
    if gen["iteration"] >= maxit:
        _create_approval(run, task, "HUMAN_OVERRIDE", f"{gen['task_id']} 已迭代 {gen['iteration']} 次仍 FAIL", [], [report["artifact_id"]],
                         options=[{"key": "override", "label": "強制通過（需 rationale）"}, {"key": "reject", "label": "再給一次迭代"}, {"key": "cancel", "label": "取消 run"}], reopen_task=gen["task_id"])
        _save_run(run); return
    gen["status"] = "READY"; task["status"] = "PENDING"; task["output_artifact_ids"] = []
    gen.setdefault("history", None); gen.pop("history", None)
    run["current_task_id"] = gen["task_id"]; _save_run(run)
    store.audit(run["run_id"], SYSTEM, "ROUTE_BACK", f"{task['task_id']} → {gen['task_id']} iteration {gen['iteration']}")

def _open_rejection_clarifications(run, rm):
    """rejection_contract.defined == false 的 REQ：開一張不阻塞的 Clarification 問 PM「不符合時系統該怎麼做」。"""
    p = rm["payload"]; d = store.spec_dir(p["spec_id"]); spec = store.load(d / "spec.yaml")
    existing = {c.get("requirement_id") for c in clr.list_(open_only=True)}
    for r in p["requirements"]:
        rc = r.get("rejection_contract")
        if rc and rc.get("defined") is False and r["requirement_id"] not in existing:
            clr.new(spec["product"], spec["functional_area"], p["spec_id"], p["spec_version"],
                    f"{r['requirement_id']} 不符合時系統應如何反應？（Spec 未定義拒絕行為）", rm["created_by"],
                    context=f"{r['statement']}\n{rc.get('description', '')}", requirement_id=r["requirement_id"], spec_reference=r.get("spec_reference"),
                    run_id=run["run_id"], impact="Test Designer 只能以 exploratory（假設）方式撰寫此需求的負向案例，expected 需 Human 確認")

def _open_clarifications(run, apr, rm):
    """每個未解的 critical ambiguity 開一張問 PM 的單，掛在 approval 上。"""
    p = rm["payload"]; d = store.spec_dir(p["spec_id"]); spec = store.load(d / "spec.yaml"); made = []
    for r in p["requirements"]:
        amb = r.get("ambiguity") or {}
        if amb.get("level") == "critical" and not amb.get("resolved_by_approval"):
            c = clr.new(spec["product"], spec["functional_area"], p["spec_id"], p["spec_version"], amb["description"], rm["created_by"],
                        context=f"{r['requirement_id']}：{r['statement']}", options=amb.get("options"), requirement_id=r["requirement_id"],
                        spec_reference=r.get("spec_reference"), run_id=run["run_id"], approval_id=apr["approval_id"],
                        impact="此 Requirement 停留 DRAFT，Test Designer 不得為其設計 Test Case")
            made.append({"entity_type": "Clarification", "id": c["clarification_id"]})
    if made:
        apr["impact"] = apr.get("impact", []) + made; store.save(f"approvals/{apr['approval_id']}.yaml", apr)

def _has_unresolved_critical(rm) -> bool:
    return any((r.get("ambiguity") or {}).get("level") == "critical" and not (r.get("ambiguity") or {}).get("resolved_by_approval") for r in rm["payload"]["requirements"])

def _persist_requirements(run, task, rm):
    p = rm["payload"]; path = store.requirements_path(p["spec_id"], p["spec_version"])
    reqs = []
    for r in p["requirements"]:
        r = dict(r); r["status"] = None; r.pop("history", None); r["history"] = []
        crit = (r.get("ambiguity") or {}).get("level") == "critical" and not (r.get("ambiguity") or {}).get("resolved_by_approval")
        state.apply("requirement", r, "DRAFT", SYSTEM, rm["artifact_id"], run["run_id"])
        if not crit: state.apply("requirement", r, "ACTIVE", SYSTEM, "G-SPEC PASS", run["run_id"])
        reqs.append(r)
    doc = {"spec_id": p["spec_id"], "spec_version": p["spec_version"], "source_artifact_id": rm["artifact_id"], "persisted_at": store.now(), "requirements": reqs}
    errs = schema.errors(doc, "spec/requirements-file.schema.json")
    if errs: raise EngineError("requirements.yaml 不符 schema：" + "; ".join(errs[:3]))
    store.save(path, doc)
    d = store.spec_dir(p["spec_id"]); spec = store.load(d / "spec.yaml")
    for v in spec["versions"]:
        if v["spec_version"] == p["spec_version"] and v["status"] == "IMPORTED": v["status"] = "ANALYZED"
    store.save(d / "spec.yaml", spec)
    store.audit(run["run_id"], SYSTEM, "PERSIST_REQUIREMENTS", f"{path} ({len(reqs)} reqs)")

def _materialize_testcases(run, task, report):
    """G-TVAL PASS：Draft → 正式 ID → versions/ (VALIDATED) → pointer；回傳 EntityRefs 供 approval。"""
    draft = store.load(store.find_artifact(report["payload"]["testcase_draft_artifact_id"]))
    created = []
    for tc in draft["payload"]["testcases"]:
        sup = tc.get("supersedes_testcase")
        if sup:
            tc_id = sup["testcase_id"]; ptr = store.load(store.tc_pointer_path(tc_id)); version = max(v["version"] for v in ptr["versions"]) + 1
        else:
            tc_id = ids.alloc("TC", tc["functional_area"]); version = 1; ptr = {"testcase_id": tc_id, "active_version": None, "status": "NO_ACTIVE_VERSION", "versions": []}
        v = {k: tc[k] for k in tc if k not in ("draft_id", "supersedes_testcase", "design_rationale")}
        v.update({"testcase_id": tc_id, "version": version, "supersedes": sup["version"] if sup else None, "status": None,
                  "created_by": draft["created_by"], "validated_by": report["created_by"], "validation_report_id": report["artifact_id"],
                  "created_at": store.now(), "updated_at": store.now(), "history": []})
        v["assumptions"] = [dict(a) for a in tc.get("assumptions", [])]   # 保留 needs_human_confirmation，ACTIVATE 時由 Human 逐項確認
        state.apply("testcase", v, "DRAFT", SYSTEM, draft["artifact_id"], run["run_id"])
        state.apply("testcase", v, "VALIDATING", SYSTEM, "dispatch validator", run["run_id"])
        state.apply("testcase", v, "VALIDATED", SYSTEM, report["artifact_id"], run["run_id"])
        errs = schema.errors(v, "testcase/testcase-version.schema.json")
        if errs: raise EngineError(f"{tc_id} v{version} 不符 schema：" + "; ".join(errs[:3]))
        store.save(store.tc_version_path(tc_id, version), v)
        ptr["versions"].append({"version": version, "status": "VALIDATED", "superseded_by": None})
        store.save(store.tc_pointer_path(tc_id), ptr)
        created.append({"entity_type": "TestCaseVersion", "id": tc_id, "version": version, "_draft_id": tc["draft_id"]})
    run.setdefault("input", {}); task["input_entity_refs"] = [{k: c[k] for k in c if not k.startswith("_")} for c in created]
    store.audit(run["run_id"], SYSTEM, "MATERIALIZE_TESTCASES", ", ".join(f"{c['id']} v{c['version']}" for c in created))

# ---------- Bug / ChangeImpact run 期 entity ----------
def _bug_path(run): return f"runs/{run['run_id']}/entities/bug.yaml"
def _bug_entity_init(run, task, bd):
    b = {"draft_id": bd["payload"]["draft_id"], "draft_artifact_id": bd["artifact_id"], "status": None, "history": []}
    state.apply("bug", b, "DRAFT", SYSTEM, bd["artifact_id"], run["run_id"]); state.apply("bug", b, "VALIDATING", SYSTEM, "dispatch validator", run["run_id"])
    store.save(_bug_path(run), b)
def _bug_entity_transition(run, to, trigger, by=SYSTEM, **extra):
    b = store.load(_bug_path(run)); b.update(extra)
    if b["status"] == "DRAFT" and to == "VALIDATION_FAILED": state.apply("bug", b, "VALIDATING", SYSTEM, "re-validate", run["run_id"])
    if b["status"] == "DRAFT" and to == "VALIDATED": state.apply("bug", b, "VALIDATING", SYSTEM, "re-validate", run["run_id"])
    state.apply("bug", b, to, by, trigger, run["run_id"]); store.save(_bug_path(run), b); return b
def _ci_entity(run, p):
    path = f"runs/{run['run_id']}/entities/change-impact.yaml"
    if store.exists(path): return store.load(path)
    ci = {"change_impact_id": p["change_impact_id"], "spec_id": p["spec_id"], "from_version": p["from_version"], "to_version": p["to_version"], "status": None, "history": []}
    state.apply("change_impact", ci, "DETECTED", SYSTEM, "spec imported", run["run_id"]); state.apply("change_impact", ci, "ANALYZING", SYSTEM, "dispatch CIA", run["run_id"])
    return ci

# ---------- Approval ----------
def _create_approval_for_task(run, task, approval_type):
    prev = next(t for t in reversed(run["tasks"][:[t["task_id"] for t in run["tasks"]].index(task["task_id"])]) if t["type"] == "agent")
    arts = _valid_outputs(prev); art_ids = [a["artifact_id"] for a in arts.values()]
    items, impact, summary, options = [], [], "", [{"key": "approve", "label": "核准"}, {"key": "reject", "label": "退回"}, {"key": "override", "label": "強制通過（需 rationale）"}]
    if approval_type in ("ACTIVATE_TESTCASE", "APPLY_CHANGE"):
        src = next(t for t in reversed(run["tasks"]) if t.get("input_entity_refs"))
        items = list(src["input_entity_refs"]); impact = items
        for it in items:
            v = store.load(store.tc_version_path(it["id"], it["version"])); state.apply("testcase", v, "PENDING_APPROVAL", SYSTEM, "approval requested", run["run_id"]); store.save(store.tc_version_path(it["id"], it["version"]), v)
            ptr = store.load(store.tc_pointer_path(it["id"]))
            for pv in ptr["versions"]:
                if pv["version"] == it["version"]: pv["status"] = "PENDING_APPROVAL"
            store.save(store.tc_pointer_path(it["id"]), ptr)
        summary = (f"{len(items)} 個 Test Case 版本已 VALIDATED，是否成為 Registry ACTIVE 版本？" if approval_type == "ACTIVATE_TESTCASE"
                   else "是否將此新版 Test Case 更新為正式 Registry 版本？")
        exp_lines = []
        for it in items:
            v = store.load(store.tc_version_path(it["id"], it["version"]))
            if v.get("assumptions"): exp_lines.append(f"[exploratory] {it['id']} v{it['version']} {v['title']}：" + "；".join(a["text"] for a in v["assumptions"]))
        if exp_lines: summary += f"（含 {len(exp_lines)} 條 exploratory，approve 即確認其假設）"
        if approval_type == "APPLY_CHANGE":
            ci = store.load(f"runs/{run['run_id']}/entities/change-impact.yaml"); state.apply("change_impact", ci, "PENDING_APPROVAL", SYSTEM, "compare done", run["run_id"]); store.save(f"runs/{run['run_id']}/entities/change-impact.yaml", ci)
    elif approval_type == "OPEN_BUG":
        b = _bug_entity_transition(run, "PENDING_APPROVAL", "approval requested")
        bd = store.load(store.find_artifact(b["draft_artifact_id"]))["payload"]
        summary = f"[{bd['severity_proposed']}/{bd['priority_proposed']}] {bd['title']} — 是否成為正式 Bug（OPEN）？"
        impact = [{"entity_type": "Requirement", "id": bd["requirement_id"]}]
    elif approval_type == "UPDATE_SUITE_MEMBERSHIP":
        rp = arts["RegressionProposal"]["payload"]
        summary = f"{rp['suite_id']}：+{len(rp['diff']['add'])} / −{len(rp['diff']['remove'])} / repin {len(rp['diff']['repin'])}，共 {len(rp['proposed_memberships'])} 筆"
        impact = [{"entity_type": "TestSuite", "id": rp["suite_id"]}] + [{"entity_type": "TestCase", "id": m["testcase_id"]} for m in rp["proposed_memberships"]]
    elif approval_type == "REVIEW_TEST_ANALYSIS":
        summary = "請審核 Test Analysis（TestDesignReport），核准後才進入 Validation"
    if items: task["input_entity_refs"] = [{k: v for k, v in i.items() if not k.startswith("_")} for i in items]
    apr = _create_approval(run, task, approval_type, summary, impact, art_ids, options=options, batch_items=items)
    if approval_type in ("ACTIVATE_TESTCASE", "APPLY_CHANGE") and exp_lines:
        apr["diff_summary"] = "\n".join(exp_lines); store.save(f"approvals/{apr['approval_id']}.yaml", apr)

def _create_approval(run, task, approval_type, summary, impact, art_ids, options, batch_items=None, reopen_task=None):
    apr_id = ids.alloc("APR")
    apr = {"approval_id": apr_id, "type": approval_type, "run_id": run["run_id"], "task_id": task["task_id"], "status": "PENDING",
           "summary": summary, "impact": [{k: v for k, v in i.items() if not k.startswith("_")} for i in impact], "artifact_ids": art_ids,
           "trace": [], "options": options, "batch_items": [{k: v for k, v in i.items() if not k.startswith("_")} for i in (batch_items or [])],
           "requested_by": "agent-supervisor", "requested_at": store.now()}
    if reopen_task: apr["diff_summary"] = f"reopen_task={reopen_task}"
    errs = schema.errors(apr, "approval/approval-request.schema.json")
    if errs: raise EngineError("ApprovalRequest 不符 schema：" + "; ".join(errs[:3]))
    store.save(f"approvals/{apr_id}.yaml", apr)
    task["approval_id"] = apr_id; run["waiting_on_approval_id"] = apr_id
    state.apply("workflow_run", run, "WAITING_HUMAN", SYSTEM, apr_id, run["run_id"]); _save_run(run)
    store.audit(run["run_id"], "agent-supervisor", "REQUEST_HUMAN_APPROVAL", f"{apr_id} {approval_type}: {summary}")
    return apr

def approve(apr_id: str, decision: str, by: str, rationale: str = "", selected_option: str | None = None, adjustments: dict | None = None, per_item: list | None = None) -> dict:
    if by.startswith("agent-") or by == SYSTEM: raise EngineError("RECORD_APPROVAL 只能由 Human 執行")
    if decision == "override" and not rationale.strip(): raise EngineError("override 必須提供 rationale")
    apr = store.load(f"approvals/{apr_id}.yaml")
    if apr["status"] != "PENDING": raise EngineError(f"{apr_id} 狀態 {apr['status']}")
    _preflight_approval(apr, decision)
    apr["decision"] = {k: v for k, v in {"decision": decision, "selected_option": selected_option, "decided_by": by, "decided_at": store.now(),
                       "rationale": rationale or None, "per_item": per_item, "adjustments": adjustments}.items() if v is not None}
    apr["status"] = "DECIDED"
    errs = schema.errors(apr, "approval/approval-request.schema.json")
    if errs: raise EngineError("ApprovalDecision 不符 schema：" + "; ".join(errs[:3]))
    store.save(f"approvals/{apr_id}.yaml", apr)
    store.audit(apr["run_id"], by, "RECORD_APPROVAL", f"{apr_id} {apr['type']} → {decision}" + (" [OVERRIDE]" if decision == "override" else ""))
    run = load_run(apr["run_id"]); task = _task(run, apr["task_id"])
    run.pop("waiting_on_approval_id", None)
    state.apply("workflow_run", run, "RUNNING", by, apr_id, run["run_id"])
    handler = {"ACTIVATE_TESTCASE": _commit_testcases, "APPLY_CHANGE": _commit_testcases, "OPEN_BUG": _commit_bug,
               "UPDATE_SUITE_MEMBERSHIP": _commit_suite, "RESOLVE_AMBIGUITY": _after_ambiguity, "HUMAN_OVERRIDE": _after_override,
               "CONFIRM_DUPLICATE": _after_duplicate, "REVIEW_TEST_ANALYSIS": _after_review, "NEEDS_DECISION": _after_needs_decision}[apr["type"]]
    handler(run, task, apr, decision, by)
    return apr

def _preflight_approval(apr, decision):
    """寫入 decision 之前的檢查：失敗時 approval 維持 PENDING、run 維持 WAITING_HUMAN。"""
    if apr["type"] == "RESOLVE_AMBIGUITY" and decision in ("approve", "override"):
        for ref in apr.get("impact", []):
            if ref["entity_type"] == "Clarification":
                c = clr.load(ref["id"])
                if c["status"] in ("OPEN", "ASKED"):
                    raise EngineError(f"{ref['id']} 尚未有 PM 回答（狀態 {c['status']}）；請先 qaos clarification answer，再 approve")

def _finish_approval_task(run, task, ok: bool, back_to_generator: bool = False):
    if task["type"] == "approval":
        state.apply("task", task, "DONE", SYSTEM, "decided")
    if ok:
        _advance(run, task["task_id"]); return
    if back_to_generator:
        ids_ = [t["task_id"] for t in run["tasks"]]; i = ids_.index(task["task_id"])
        gen = next(t for t in reversed(run["tasks"][:i]) if t["type"] == "agent" and t.get("agent_id") not in ("agent-supervisor", "agent-test-validator", "agent-bug-validator"))
        gen["iteration"] += 1; gen["status"] = "READY"; gen["output_artifact_ids"] = []
        for t in run["tasks"][ids_.index(gen["task_id"]) + 1:]:
            if t["task_id"] != task["task_id"] and t["status"] in ("DONE",) and not (t["type"] == "agent" and t.get("agent_id") == "agent-supervisor"):
                t["status"] = "PENDING"; t["output_artifact_ids"] = []
            if t["type"] == "approval": t["input_entity_refs"] = []   # 清掉舊的 entity refs，避免下次 _create_approval_for_task 誤撿到本輪 reject 前的殘留資料
        task["status"] = "PENDING"; task["input_entity_refs"] = []
        run["current_task_id"] = gen["task_id"]
    _save_run(run)

def _commit_testcases(run, task, apr, decision, by):
    per = {i["id"]: i["decision"] for i in (apr["decision"].get("per_item") or [])}
    activated = []
    for it in apr["batch_items"]:
        d = per.get(it["id"], decision)
        path = store.tc_version_path(it["id"], it["version"]); v = store.load(path); ptr = store.load(store.tc_pointer_path(it["id"]))
        if d in ("approve", "override"):
            state.apply("testcase", v, "APPROVED", by, apr["approval_id"], run["run_id"], note="override" if d == "override" else "")
            v["approved_by"] = by; v["approval_id"] = apr["approval_id"]
            for a in v.get("assumptions", []):
                if a.get("needs_human_confirmation"): a["needs_human_confirmation"] = False; a["resolved_by_approval"] = apr["approval_id"]
            state.apply("testcase", v, "ACTIVE", SYSTEM, "COMMIT_TO_REGISTRY", run["run_id"])
            old = ptr["active_version"]
            if old is not None and old != it["version"]:
                op = store.tc_version_path(it["id"], old); o = store.load(op)
                state.apply("testcase", o, "SUPERSEDED", SYSTEM, f"v{it['version']} ACTIVE", run["run_id"]); store.save(op, o)
                for pv in ptr["versions"]:
                    if pv["version"] == old: pv["status"] = "SUPERSEDED"; pv["superseded_by"] = it["version"]
            ptr["active_version"] = it["version"]; ptr["status"] = "ACTIVE"
            for pv in ptr["versions"]:
                if pv["version"] == it["version"]: pv["status"] = "ACTIVE"; pv["activated_by_approval"] = apr["approval_id"]
            activated.append(f"{it['id']} v{it['version']}")
        else:
            state.apply("testcase", v, "DRAFT", by, apr["approval_id"], run["run_id"], note="rejected")
            for pv in ptr["versions"]:
                if pv["version"] == it["version"]: pv["status"] = "DRAFT"
        store.save(path, v); store.save(store.tc_pointer_path(it["id"]), ptr)
    if apr["type"] == "APPLY_CHANGE":
        ci_path = f"runs/{run['run_id']}/entities/change-impact.yaml"; ci = store.load(ci_path)
        if decision in ("approve", "override"):
            state.apply("change_impact", ci, "APPLIED", by, apr["approval_id"], run["run_id"])
            vcr = next((store.load(store.find_artifact(a)) for a in apr["artifact_ids"] if store.load(store.find_artifact(a))["artifact_type"] == "VersionComparisonReport"), None)
            for r in (vcr["payload"]["retire_recommendations"] if vcr else []):
                ptr = store.load(store.tc_pointer_path(r["testcase_id"]))
                if ptr["active_version"] is not None:
                    vp = store.tc_version_path(r["testcase_id"], ptr["active_version"]); v = store.load(vp)
                    state.apply("testcase", v, "RETIRED", by, apr["approval_id"], run["run_id"], note=r["reason"]); store.save(vp, v)
                    for pv in ptr["versions"]:
                        if pv["version"] == ptr["active_version"]: pv["status"] = "RETIRED"
                    ptr["status"] = "RETIRED"; ptr["active_version"] = None; store.save(store.tc_pointer_path(r["testcase_id"]), ptr)
        else:
            state.apply("change_impact", ci, "TEST_UPDATE_REQUIRED", by, apr["approval_id"], run["run_id"])
        store.save(ci_path, ci)
    store.audit(run["run_id"], SYSTEM, "COMMIT_TO_REGISTRY", ", ".join(activated) or "(none)")
    _finish_approval_task(run, task, ok=decision in ("approve", "override") or bool(activated), back_to_generator=decision == "reject")

def _commit_bug(run, task, apr, decision, by):
    b = store.load(_bug_path(run))
    if decision == "reject":
        state.apply("bug", b, "DRAFT", by, apr["approval_id"], run["run_id"], note="rejected"); store.save(_bug_path(run), b)
        _finish_approval_task(run, task, ok=False, back_to_generator=True); return
    bd = store.load(store.find_artifact(b["draft_artifact_id"]))["payload"]; rep = store.load(store.find_artifact(b["validator_report"])) if b.get("validator_report") else None
    adj = apr["decision"].get("adjustments") or {}
    bug_id = ids.alloc("BUG", bd["functional_area"])
    bug = {k: bd[k] for k in bd if k not in ("draft_id", "severity_proposed", "priority_proposed", "duplicate_candidates", "ambiguity_note")}
    bug.update({"bug_id": bug_id, "version": 1, "severity": adj.get("severity", bd["severity_proposed"]), "priority": adj.get("priority", bd["priority_proposed"]),
                "duplicate_of": None, "status": None, "created_by": store.load(store.find_artifact(b["draft_artifact_id"]))["created_by"],
                "validated_by": b.get("validator"), "validation_report_id": b.get("report_id"), "approved_by": by, "approval_id": apr["approval_id"],
                "created_at": store.now(), "updated_at": store.now(), "history": list(b["history"])})
    bug["status"] = b["status"]
    state.apply("bug", bug, "OPEN", by, apr["approval_id"], run["run_id"], note="override" if decision == "override" else "")
    errs = schema.errors(bug, "bug/bug.schema.json")
    if errs: raise EngineError(f"Bug 不符 schema：" + "; ".join(errs[:3]))
    path = store.bug_path(bd["product"], bd["functional_area"], bug_id); store.save(path, bug)
    b["bug_id"] = bug_id; b["status"] = "OPEN"; store.save(_bug_path(run), b)
    task["input_entity_refs"] = [{"entity_type": "Bug", "id": bug_id}]
    store.audit(run["run_id"], SYSTEM, "COMMIT_BUG", f"{bug_id} → {path}")
    _finish_approval_task(run, task, ok=True)

def _commit_suite(run, task, apr, decision, by):
    if decision == "reject": _finish_approval_task(run, task, ok=False, back_to_generator=True); return
    rp = next(store.load(store.find_artifact(a)) for a in apr["artifact_ids"] if store.load(store.find_artifact(a))["artifact_type"] == "RegressionProposal")["payload"]
    path = store.suite_path(rp["suite_type"], rp["suite_id"])
    cur = store.load(path) if store.exists(path) else None
    suite = {"suite_id": rp["suite_id"], "suite_type": rp["suite_type"], "version": (cur["version"] + 1) if cur else 1,
             "title": (cur or {}).get("title", rp["suite_id"]), "status": None,
             "memberships": [{**m, "added_by_approval": apr["approval_id"]} for m in rp["proposed_memberships"]],
             "approved_by": by, "approval_id": apr["approval_id"], "created_at": store.now(), "history": []}
    if rp.get("change_impact_id"): suite["change_impact_id"] = rp["change_impact_id"]
    state.apply("test_suite", suite, "DRAFT", SYSTEM, rp["suite_id"], run["run_id"]); state.apply("test_suite", suite, "PENDING_APPROVAL", SYSTEM, apr["approval_id"], run["run_id"])
    state.apply("test_suite", suite, "ACTIVE", by, apr["approval_id"], run["run_id"])
    errs = schema.errors(suite, "testcase/test-suite.schema.json")
    if errs: raise EngineError("TestSuite 不符 schema：" + "; ".join(errs[:3]))
    if cur: store.save(path.replace(".yaml", f".v{cur['version']}.yaml"), cur)   # 舊版本保留
    store.save(path, suite)
    task["input_entity_refs"] = [{"entity_type": "TestSuite", "id": rp["suite_id"], "version": suite["version"]}]
    store.audit(run["run_id"], SYSTEM, "UPDATE_SUITE_MEMBERSHIP", f"{rp['suite_id']} v{suite['version']} ({len(suite['memberships'])} memberships)")
    _finish_approval_task(run, task, ok=True)

def _after_ambiguity(run, task, apr, decision, by):
    reopen = (apr.get("diff_summary") or "").replace("reopen_task=", "") or None
    for ref in apr.get("impact", []):
        if ref["entity_type"] == "Clarification":
            c = clr.load(ref["id"])
            if decision in ("approve", "override") and c["status"] == "ANSWERED": clr.apply_(ref["id"], by, note=apr["approval_id"])
    if run["workflow_id"] == "spec-to-bug":
        if decision == "reject":
            _bug_entity_transition(run, "REJECTED", apr["approval_id"], by=by)
            for t in run["tasks"]:
                if t["status"] == "PENDING": t["status"] = "DONE"
            state.apply("workflow_run", run, "COMPLETED", SYSTEM, "bug rejected", run["run_id"]); _save_run(run); return
        _bug_entity_transition(run, "DRAFT", apr["approval_id"], by=by)
        _finish_approval_task(run, task, ok=False, back_to_generator=True); return
    if reopen:
        t = _task(run, reopen); t["iteration"] += 1; t["status"] = "READY"; t["output_artifact_ids"] = []; run["current_task_id"] = reopen
        for later in run["tasks"][[x["task_id"] for x in run["tasks"]].index(reopen) + 1:]:
            if later["status"] == "DONE" and not (later["type"] == "agent" and later.get("agent_id") == "agent-supervisor"): later["status"] = "PENDING"
        _save_run(run)

def _after_override(run, task, apr, decision, by):
    reopen = (apr.get("diff_summary") or "").replace("reopen_task=", "") or None
    if decision == "override":
        # 視為 Validator PASS：以最後一份 validator 報告的 draft 進行 materialize / bug VALIDATED
        vt = _task(run, task["task_id"]); arts = _valid_outputs(vt)
        if "TestValidationReport" in arts:
            _materialize_testcases(run, vt, arts["TestValidationReport"])
        elif "BugValidationReport" in arts:
            _bug_entity_transition(run, "DRAFT", "override"); _bug_entity_transition(run, "VALIDATED", apr["approval_id"], by=SYSTEM)
        vt["status"] = "DONE"; _advance(run, vt["task_id"]); return
    if decision == "reject" and reopen:
        t = _task(run, reopen); t["status"] = "READY"; t["output_artifact_ids"] = []; run["current_task_id"] = reopen
        ids_ = [x["task_id"] for x in run["tasks"]]
        for later in run["tasks"][ids_.index(reopen) + 1:]:   # 下游已 DONE 的 task 重設，讓 Validator 可再跑
            if later["status"] == "DONE" and not (later["type"] == "agent" and later.get("agent_id") == "agent-supervisor"):
                later["status"] = "PENDING"; later["output_artifact_ids"] = []; later.pop("history", None)
            if later["type"] == "approval": later["input_entity_refs"] = []   # 清掉舊的 entity refs，避免下次 _create_approval_for_task 誤撿到殘留資料
        _save_run(run); return
    state.apply("workflow_run", run, "CANCELLED", by, apr["approval_id"], run["run_id"]); _save_run(run)

def _after_duplicate(run, task, apr, decision, by):
    if decision in ("approve", "override"):
        rep = store.load(store.find_artifact(apr["artifact_ids"][0]))["payload"]
        _bug_entity_transition(run, "REJECTED", apr["approval_id"], by=by, duplicate_of=rep["duplicate_check"]["duplicate_of"])
        for t in run["tasks"]:
            if t["status"] == "PENDING": t["status"] = "DONE"
        state.apply("workflow_run", run, "COMPLETED", SYSTEM, "duplicate confirmed", run["run_id"]); _save_run(run); return
    _bug_entity_transition(run, "DRAFT", apr["approval_id"], by=by)
    _finish_approval_task(run, task, ok=False, back_to_generator=True)

def _after_review(run, task, apr, decision, by):
    _finish_approval_task(run, task, ok=decision in ("approve", "override"), back_to_generator=decision == "reject")

def _after_needs_decision(run, task, apr, decision, by):
    opt = apr["decision"].get("selected_option")
    if opt == "cancel" or decision == "reject":
        state.apply("workflow_run", run, "CANCELLED", by, apr["approval_id"], run["run_id"]); _save_run(run); return
    cont = (apr.get("diff_summary") or "").replace("continue_after=", "") if (apr.get("diff_summary") or "").startswith("continue_after=") else None
    if cont and opt != "retry":
        _advance(run, cont); return
    t = _task(run, apr["task_id"]); t["status"] = "READY"; t["output_artifact_ids"] = []; _save_run(run)   # structural retry 不計入 semantic 迭代

def cancel(run_id: str, by: str):
    run = load_run(run_id); state.apply("workflow_run", run, "CANCELLED", by, "cancel", run_id); _save_run(run)

# ---------- Summary ----------
def _summarize(run, task):
    aid = ids.artifact_id("WorkflowSummary")
    outputs = [r for t in run["tasks"] for r in t.get("input_entity_refs", []) if t["type"] == "approval"]
    approvals = []
    for t in run["tasks"]:
        if t.get("approval_id"):
            a = store.load(f"approvals/{t['approval_id']}.yaml")
            approvals.append({"approval_id": a["approval_id"], "type": a["type"], "decision": (a.get("decision") or {}).get("decision"), "decided_by": (a.get("decision") or {}).get("decided_by", "")})
    payload = {"run_id": run["run_id"], "workflow_id": run["workflow_id"], "final_status": "COMPLETED", "started_at": run["created_at"], "ended_at": store.now(),
               "tasks": [{"task_id": t["task_id"], "agent_id": t.get("agent_id", "human"), "status": "DONE" if t["task_id"] == task["task_id"] else t["status"], "iterations": t["iteration"],
                          "gate": t.get("gate", ""), "gate_result": (t.get("gate_results") or [{}])[-1].get("result", "")} for t in run["tasks"]],
               "artifacts_produced": [{"entity_type": "Artifact", "id": a} for t in run["tasks"] for a in t["output_artifact_ids"]] + [{"entity_type": "Artifact", "id": aid}],
               "approvals": approvals, "outputs": outputs, "iterations": {t["task_id"]: t["iteration"] for t in run["tasks"]},
               "overrides": [a["approval_id"] for a in approvals if a["decision"] == "override"],
               "open_items": [], "narrative": "（Phase 2：由 Runtime 機械彙整；Phase 3 由 Supervisor 補敘述）"}
    art = {"artifact_id": aid, "artifact_type": "WorkflowSummary", "schema_version": "1.0", "version": 1, "run_id": run["run_id"], "task_id": task["task_id"],
           "created_by": "agent-supervisor", "created_at": store.now(), "status": "VALID", "source": {"type": "WorkflowRun", "ids": [run["run_id"]]},
           "references": [{"entity_type": "WorkflowRun", "id": run["run_id"]}], "payload": payload}
    errs = schema.errors(art, "artifact/envelope.schema.json")
    if errs: raise EngineError("WorkflowSummary 不符 schema：" + "; ".join(errs[:3]))
    store.save(f"artifacts/summaries/{run['run_id']}/{aid}.yaml", art)
    task["output_artifact_ids"].append(aid); state.apply("task", task, "DONE", SYSTEM, aid); run["summary_artifact_id"] = aid
    state.apply("workflow_run", run, "COMPLETED", SYSTEM, aid, run["run_id"]); _save_run(run)
    store.audit(run["run_id"], "agent-supervisor", "CREATE_WORKFLOW_SUMMARY", aid)
