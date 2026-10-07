"""Workflow 引擎：Run 建立、Artifact 提交（Permission Guard + Structural Gate）、Gate 評估與效果、Approval、Commit。
Agent 永遠不呼叫這裡的 commit；只有 approve() 在 Human 決定後觸發。"""
import pathlib
from . import store, schema, ids, state, refs, gates, operation, rm, clarification as clr
from .state import TransitionError

SYSTEM = "system"

class EngineError(Exception): pass

# ---------- 載入設定 ----------
_agents = None
def agents():
    global _agents
    if _agents is None:
        _agents = {}
        for p in store.glob("agents/*.yaml"):
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
        rr = _risk_review_task_id(wf, inputs)
        if rr and t["id"] == wf["risk_review"]["after"]:
            tasks.append({"task_id": rr, "type": "agent", "agent_id": wf["risk_review"]["agent"], "gate": "G-RISK", "status": "PENDING", "iteration": 0,
                          "input_artifact_ids": [], "input_entity_refs": [], "output_artifact_ids": []})
    return tasks

def _risk_review_task_id(wf: dict, inputs: dict) -> str | None:
    """ADR-009：run 的 functional area（store.run_area）在風險抽查 agent 的 applies_to_areas 內 → 插入 <after>RR。
    area 判定不了時由 new_run 事先拒絕，這裡不會把「未知」當成「不需抽查」。"""
    cfg = wf.get("risk_review")
    if not cfg: return None
    if store.run_area(inputs) not in (agents()[cfg["agent"]].get("applies_to_areas") or []): return None
    return cfg["after"] + "RR"

def _wf_task(wf: dict, task_id: str) -> dict:
    if task_id == "T2R": return {"id": "T2R", "type": "approval", "approval_type": "REVIEW_TEST_ANALYSIS"}
    if wf.get("risk_review") and task_id == wf["risk_review"]["after"] + "RR":
        return {"id": task_id, "agent": wf["risk_review"]["agent"], "outputs": ["TCRiskReview"], "gate": "G-RISK"}
    return next(t for t in wf["tasks"] if t["id"] == task_id)

def _skip_decision(wf: dict, wt: dict, inputs: dict) -> tuple[bool, str | None]:
    """分析 task（有 run_if／skip_if 的 T0、T1）是否跳過，依第 5 章 §7 的優先序；回傳 (是否跳過, 要記入 audit 的警告)。"""
    if not (wt.get("skip_if") or wt.get("run_if")): return False, None
    sid, ver = inputs.get("spec_id"), inputs.get("spec_version") or inputs.get("to_version")
    if not (sid and ver): return False, None
    if wf["workflow_id"] == "spec-change-impact" and str(inputs.get("from_version")) == str(inputs.get("to_version")): return False, None   # 同版本 CIA：T0 一定執行（§8）
    pin = rm.latest_pin(sid, ver)
    if pin is None: return False, None                                       # 1. 沒有 RM
    if rm.has_non_active(pin): return False, None                            # 2. 最新 revision 有非 ACTIVE 的需求（優先於 legacy 例外）
    o = rm.outdated(pin)
    if o["declaration_changed"] or o["decision_revised"]: return False, None # 3.
    from . import spec_ops
    _, _, e = spec_ops.find_entry(sid, ver)
    if pin["revision"] == "R000" and spec_ops.references_status(e) == "undeclared":   # 4. 只有 legacy R000、未宣告引用、全部 ACTIVE
        return True, f"沿用 legacy {sid}@{ver} R000（引用未宣告）跳過分析"
    return True, None                                                         # 5.

def _skip(wf: dict, wt: dict, inputs: dict) -> bool:
    return _skip_decision(wf, wt, inputs)[0]

def _require_fresh(pin: dict, label: str):
    """沒有 T0 的流程（testcase-revision、manual）在 run new 時凍結 revision：過時或有非 ACTIVE 需求 → 拒絕，提示先重新分析（§4.3）。"""
    o = rm.outdated(pin); why = [k for k in ("declaration_changed", "decision_revised") if o[k]]
    if rm.has_non_active(pin): why.append("最新 revision 有非 ACTIVE 的需求")
    if why: raise EngineError(f"{label} 的 {pin['spec_id']}@{pin['spec_version']} {pin['revision']} 不能直接沿用（{', '.join(why)}）；請先重新分析。" + ("；".join(o["details"]) and f" 細節：{'；'.join(o['details'])}"))

def _require_analyzable(workflow_id: str, inputs: dict):
    """reference_only 的 spec 版本不能當任何 run 的分析目標（需求 A 第 2 章 §3.4 的 7 個入口）。"""
    from . import spec_ops
    checks = []
    if inputs.get("spec_id"):
        for k, label in (("spec_version", f"{workflow_id} 的 inputs.spec_id"), ("from_version", "spec-change-impact 的 from 端"), ("to_version", "spec-change-impact 的 to 端")):
            if inputs.get(k): checks.append((inputs["spec_id"], inputs[k], label))
    if workflow_id == "testcase-revision" and inputs.get("testcase_id") and store.exists(store.tc_pointer_path(inputs["testcase_id"])):
        ptr = store.load(store.tc_pointer_path(inputs["testcase_id"]))
        ver = ptr.get("active_version")
        if ver and store.exists(store.tc_version_path(inputs["testcase_id"], ver)):
            tv = store.load(store.tc_version_path(inputs["testcase_id"], ver))
            if tv.get("spec_id") and tv.get("spec_version"): checks.append((tv["spec_id"], tv["spec_version"], "被修訂 TC 版本的 spec"))
    if workflow_id == "manual-test-to-regression" and inputs.get("manual_record_id") and store.exists(f"testcases/manual/{inputs['manual_record_id']}.yaml"):
        h = store.load(f"testcases/manual/{inputs['manual_record_id']}.yaml").get("spec_hint") or {}
        if h.get("spec_id") and h.get("spec_version"): checks.append((h["spec_id"], h["spec_version"], "manual record 的 spec_hint"))
    for sid, ver, label in checks:
        try: spec_ops.require_analyzable(sid, str(ver), label)
        except spec_ops.SpecError as e: raise EngineError(str(e))

def _target_of(workflow_id: str, inputs: dict) -> tuple[str, str] | None:
    """manual-test-to-regression 的目標 spec：inputs 優先，其次 manual record 的 spec_hint（第 5 章 §4.2）。"""
    if inputs.get("spec_id") and inputs.get("spec_version"): return inputs["spec_id"], str(inputs["spec_version"])
    if workflow_id == "manual-test-to-regression" and inputs.get("manual_record_id") and store.exists(f"testcases/manual/{inputs['manual_record_id']}.yaml"):
        h = store.load(f"testcases/manual/{inputs['manual_record_id']}.yaml").get("spec_hint") or {}
        if h.get("spec_id") and h.get("spec_version"): return h["spec_id"], str(h["spec_version"])
    return None

def _tc_target(inputs: dict) -> tuple[str, str]:
    """testcase-revision 的目標由被修訂 TC 的 ACTIVE 版本推得（第 5 章 §4.2、§4.3）；inputs 的 spec 和它不符 → 拒絕（跨版本改動走 CIA）。"""
    tc = inputs.get("testcase_id")
    if not tc or not store.exists(store.tc_pointer_path(tc)): raise EngineError(f"testcase-revision 找不到被修訂的 TC：{tc!r}")
    ptr = store.load(store.tc_pointer_path(tc))
    if not ptr.get("active_version"): raise EngineError(f"{tc} 沒有 ACTIVE 版本，不能 testcase-revision")
    v = store.load(store.tc_version_path(tc, ptr["active_version"]))
    tgt = (v["spec_id"], str(v["spec_version"]))
    given = (inputs.get("spec_id"), str(inputs.get("spec_version")) if inputs.get("spec_version") is not None else None)
    if given != tgt: raise EngineError(f"testcase-revision 的 spec 必須是 {tc} v{ptr['active_version']} 自己的 {tgt[0]}@{tgt[1]}（inputs 是 {given[0]}@{given[1]}）；跨版本改動請走 spec-change-impact")
    return tgt

def _bind_at_new_run(workflow_id: str, inputs: dict) -> dict:
    """new_run 時就要綁定的 revision（第 5 章 §4.2）：spec-change-impact 的 from 端；沒有 T0 的 testcase-revision、manual 綁目標版本的最新 revision。"""
    out = {}
    if workflow_id == "spec-change-impact":
        if str(inputs["from_version"]) == str(inputs["to_version"]):         # 同版本 CIA（§8）
            if not inputs.get("from_revision") or not inputs.get("reason"):
                raise EngineError("同版本的 spec-change-impact 必須帶 --input from_revision=R<NNN> 與 --input reason=declaration_changed|decision_revised|decision_applied")
            try: pin = rm.pin_of(inputs["spec_id"], str(inputs["from_version"]), inputs["from_revision"])
            except rm.RMError as e: raise EngineError(str(e))
            reason = inputs["reason"]
            if reason not in ("declaration_changed", "decision_revised", "decision_applied"): raise EngineError(f"reason 只能是 declaration_changed、decision_revised 或 decision_applied：{reason!r}")
            actual = rm.decision_applied(pin) if reason == "decision_applied" else rm.outdated(pin)[reason]
            if not actual: raise EngineError(f"{inputs['from_revision']} 的判定結果不是 {reason}；不能以這個理由做同版本 CIA")
            out["from_requirement_model_revision"] = pin
        else:
            pin = rm.latest_pin(inputs["spec_id"], inputs["from_version"])
            if pin: out["from_requirement_model_revision"] = pin
    elif workflow_id in ("testcase-revision", "manual-test-to-regression"):
        tgt = _tc_target(inputs) if workflow_id == "testcase-revision" else _target_of(workflow_id, inputs)
        if tgt is None: raise EngineError("沒有可分析的 spec：先在 manual record 補 spec_hint（spec_id、spec_version），或以 inputs 指定 spec")
        pin = rm.latest_pin(*tgt)
        if pin is None: raise EngineError(f"{tgt[0]}@{tgt[1]} 還沒有需求模型 revision；先以 spec-to-testcase 分析")
        _require_fresh(pin, workflow_id)
        out["requirement_model_revision"] = pin
        if workflow_id == "testcase-revision" and inputs.get("testcase_id") and store.exists(store.tc_pointer_path(inputs["testcase_id"])):
            ptr = store.load(store.tc_pointer_path(inputs["testcase_id"]))
            if ptr.get("active_version"): out["testcase_pin"] = rm.tc_pin(inputs["testcase_id"], ptr["active_version"])   # 被修訂 TC 自己的舊 pin，供 diff
    return out

@operation.operation("run_new")
def new_run(workflow_id: str, inputs: dict, by: str) -> dict:
    wf = workflow(workflow_id)
    missing = [k for k, v in wf["input"]["fields"].items() if v.get("required") and k not in inputs and k != "initiated_by"]
    if missing: raise EngineError(f"缺少必要 input：{missing}")
    if wf.get("risk_review") and store.run_area(inputs) is None:
        raise EngineError("無法判定本 run 的 functional area（需 spec_id，或 functional_area 有值的 manual_record_id），無法決定是否需要高風險抽查（ADR-009）")
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
    _require_analyzable(workflow_id, inputs)
    pins = _bind_at_new_run(workflow_id, inputs)
    run_id = ids.alloc("RUN")
    run = {"run_id": run_id, "workflow_id": workflow_id, "workflow_version": wf["version"], "status": None,
           "input": {**inputs, "initiated_by": by}, "initiated_by": by, "created_at": store.now(), "updated_at": store.now(),
           "tasks": _expand_tasks(wf, inputs), "history": [], **pins}
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
        skip, warn = _skip_decision(wf, wt, run["input"]) if t["type"] == "agent" else (False, None)
        if skip:
            inp = run["input"]
            if warn: store.audit(run["run_id"], SYSTEM, "WARN_LEGACY_SKIP", warn)
            if not run.get("requirement_model_revision"):                    # 跳過分析時，run 綁定最新 revision（第 5 章 §4.2、§7）
                rm.bind_run(run, rm.latest_pin(inp["spec_id"], inp.get("spec_version") or inp.get("to_version")))
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
def _submit_request(run_id, task_id, artifact_path):
    # 只用路徑與 artifact_id：提交本身會改寫 artifact 的狀態，內容 hash 不能進 op_id（否則中止後重送會變成另一個 op）
    r = store.rel(artifact_path)
    aid = store.load(r).get("artifact_id") if store.exists(r) else None
    return {"targets": {"run_id": run_id, "task_id": task_id}, "inputs": {"artifact": r, "artifact_id": aid}}

def _run_pins(run) -> list[dict]:
    """run 綁定的 RMPin（目標／to 端在前，spec-change-impact 另有 from 端），依 run 欄位 → run sidecar 解析（第 5 章 §4.1）。"""
    out = []
    for end in ("target", "from"):
        try: out.append(rm.run_pin(run, end))
        except rm.RMError: pass
    return out

def _resolve_in_run(ref, run) -> str | None:
    """artifact 引用的 Requirement／AC 只在 run 綁定的 revision 中找（不讀可變的檢視、不改查最新）。
    run 沒有任何綁定 → 錯誤；只有本來就不綁 spec 的 regression-generation 例外（第 5 章 §4.2）。"""
    if ref["entity_type"] not in ("Requirement", "AcceptanceCriterion"): return refs.resolve(ref)
    pins = _run_pins(run)
    if not pins:
        if run["workflow_id"] == "regression-generation": return refs.resolve(ref)
        return f"{ref['entity_type']} {ref['id']}：run {run['run_id']} 還沒有綁定需求模型 revision，不能解析需求引用"
    errs = [refs.resolve(ref, pin=p) for p in pins]
    return None if any(e is None for e in errs) else errs[0]

@operation.operation("submit", request=_submit_request, scope=lambda run_id, *a, **k: run_id)
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
        err = _resolve_in_run(r, run)
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
    # 驗證失敗不改 artifact 檔（最終規格第 4 章 §13）：INVALID 只記在 task 的 gate_results（含 artifact_id）。
    aid = art.get("artifact_id") if isinstance(art, dict) else None
    task.setdefault("gate_results", []).append({"at": store.now(), "layer": "structural", "result": "FAIL", "details": problems[:20], **({"artifact_id": aid} if aid else {})})
    if any("越權" in x or "無權" in x or "write_paths" in x for x in problems):
        task.setdefault("permission_violations", []).append({"at": store.now(), "action": "CREATE_ARTIFACT", "detail": "; ".join(problems)[:500]})
        state.apply("task", task, "FAILED", SYSTEM, "permission violation")
        state.apply("workflow_run", run, "FAILED", SYSTEM, f"{task['task_id']} permission violation", run["run_id"])
        store.audit(run["run_id"], task.get("agent_id", "?"), "PERMISSION_VIOLATION", "; ".join(problems)[:300])
    else:
        # 驗證失敗：只寫允許的診斷（task 欄位與一個事件），不建立計畫、不開核准單；task 維持可重試，要放棄由人 run cancel
        store.mark_diagnostic()
        state.apply("task", task, "ARTIFACT_INVALID", SYSTEM, "structural fail")
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

def _gate_request(run_id, task_id):
    """gate 請求的身分：這個 task 目前所有 VALID 的 artifact（gate 不改寫 artifact 檔）。
    不用 task.output_artifact_ids：Validator FAIL 的退回會在同一個操作中清空它，中止後重送就會變成另一個 op。"""
    task = _task(load_run(run_id), task_id)
    valid = []
    for p in store.glob(f"artifacts/*/{run_id}/*.yaml"):
        a = store.load(p)
        if a.get("task_id") == task_id and a.get("status") == "VALID": valid.append(a["artifact_id"])
    return {"targets": {"run_id": run_id, "task_id": task_id, "iteration": task.get("iteration")}, "inputs": {"valid_artifacts": sorted(valid)}}

@operation.operation("evaluate_gate", request=_gate_request, scope=lambda run_id, *a, **k: run_id)
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
        store.mark_diagnostic()   # 驗證失敗：只寫允許的診斷，不建立計畫
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

def _persist_requirements(run, task, rm_art):
    p = rm_art["payload"]; path = store.requirements_path(p["spec_id"], p["spec_version"])
    reqs = []
    for r in p["requirements"]:
        r = dict(r); r["status"] = None; r.pop("history", None); r["history"] = []
        crit = (r.get("ambiguity") or {}).get("level") == "critical" and not (r.get("ambiguity") or {}).get("resolved_by_approval")
        state.apply("requirement", r, "DRAFT", SYSTEM, rm_art["artifact_id"], run["run_id"])
        if not crit: state.apply("requirement", r, "ACTIVE", SYSTEM, "G-SPEC PASS", run["run_id"])
        reqs.append(r)
    pin = rm.save_requirements(p["spec_id"], p["spec_version"], reqs, reason="analysis", by=SYSTEM, run_id=run["run_id"], source_artifact_id=rm_art["artifact_id"])
    run["requirement_model_revision"] = pin                                  # 本 run 自己的分析：綁定（重新分析時改綁本 run 新產生的 revision）
    d = store.spec_dir(p["spec_id"]); spec = store.load(d / "spec.yaml")
    for v in spec["versions"]:
        if v["spec_version"] == p["spec_version"] and v["status"] == "IMPORTED": v["status"] = "ANALYZED"
    store.save(d / "spec.yaml", spec)
    store.audit(run["run_id"], SYSTEM, "PERSIST_REQUIREMENTS", f"{path} {pin['revision']} ({len(reqs)} reqs)")

def _materialize_testcases(run, task, report):
    """G-TVAL PASS：Draft → 正式 ID → versions/ (VALIDATED) → pointer；回傳 EntityRefs 供 approval。"""
    draft = store.load(store.find_artifact(report["payload"]["testcase_draft_artifact_id"]))
    pin = rm.run_pin(run)                                                    # TC 版本綁定 run 的依據（第 5 章 §4.1）
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
                  "created_at": store.now(), "updated_at": store.now(), "history": [], "requirement_model_revision": pin})
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
    before = run["tasks"][:[t["task_id"] for t in run["tasks"]].index(task["task_id"])]
    prev = next(t for t in reversed(before) if t["type"] == "agent" and t.get("agent_id") != "agent-tc-risk-reviewer")
    arts = _valid_outputs(prev); art_ids = [a["artifact_id"] for a in arts.values()]
    risk = next((_valid_outputs(t).get("TCRiskReview") for t in reversed(before) if t.get("agent_id") == "agent-tc-risk-reviewer" and t["status"] == "DONE"), None)
    if risk: art_ids.append(risk["artifact_id"])
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
        if risk:
            rp = risk["payload"]; fs = rp["findings"]
            summary += (f"（高風險抽查 {risk['artifact_id']}：{len(fs)} 條補充建議，high {sum(f['severity'] == 'high' for f in fs)}、需澄清 {sum(f['needs_clarification'] for f in fs)}；建議不影響本次核准，要採納請另起 run／開 CLR）"
                        if fs else f"（高風險抽查 {risk['artifact_id']}：五面向皆無補充建議）")
            exp_lines += [f"[risk-review] {rp['summary']}"] + [
                f"[{f['finding_id']}/{f['severity']}/{f['dimension']}{'/需澄清' if f['needs_clarification'] else ''}] {f['gap']} → 建議：{f['suggested_scenario']}"
                + (f"（相關 {', '.join(f['related_testcase_ids'])}）" if f["related_testcase_ids"] else "") for f in fs]
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

@operation.operation("approve")
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

def _finish_approval_task(run, task, ok: bool, back_to_generator: bool = False, to_agent: str | None = None):
    if task["type"] == "approval":
        state.apply("task", task, "DONE", SYSTEM, "decided")
    if ok:
        _advance(run, task["task_id"]); return
    if back_to_generator:
        ids_ = [t["task_id"] for t in run["tasks"]]; i = ids_.index(task["task_id"])
        before = run["tasks"][:i]
        # to_agent：呼叫端明確指定退回對象。ACTIVATE_TESTCASE／APPLY_CHANGE 一律退回 Test Designer——spec-change-impact
        # 的 T4 CIA compare 排在核准前，只找「最近一個非 validator agent」會誤退回 compare（ADR-009 review 修正）。
        # 其餘核准（suite 成員、bug 等）維持「最近一個產出者」，例如 UPDATE_SUITE_MEMBERSHIP 退回 regression curator。
        gen = (next((t for t in reversed(before) if t.get("agent_id") == to_agent), None) if to_agent else None) or \
              next(t for t in reversed(before) if t["type"] == "agent" and t.get("agent_id") not in ("agent-supervisor", "agent-test-validator", "agent-bug-validator", "agent-tc-risk-reviewer"))
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
    _finish_approval_task(run, task, ok=decision in ("approve", "override") or bool(activated), back_to_generator=decision == "reject", to_agent="agent-test-designer")

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
            if decision in ("approve", "override") and c["status"] == "ANSWERED": clr.apply_(ref["id"], by, note=apr["approval_id"], impact_reviewed=f"由 {apr['approval_id']}（RESOLVE_AMBIGUITY）核准者於 run 內判定；候選清單見本 note，run 外 TC 若受影響需另行修訂")
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

def cancel_body(run_id: str, by: str, reason: str = "cancel") -> list[str]:
    """run 轉 CANCELLED，並把該 run **所有** PENDING 的核准單轉 CANCELLED（不只 waiting_on_approval_id）；每張的 ID 與理由寫進 run 的 audit 事件。
    已綁定的 revision 與 sidecar 保留（第 5 章 §10）。`migrate --cancel-run` 在同一個移轉操作中呼叫這裡。回傳被取消的核准單。"""
    from . import approval_render
    run = load_run(run_id); state.apply("workflow_run", run, "CANCELLED", by, reason, run_id); _save_run(run)
    store.audit(run_id, by, "CANCEL_RUN", reason)
    cancelled = []
    for p in store.glob("approvals/APR-*.yaml"):
        a = store.load(p)
        if a.get("run_id") != run_id or a.get("status") != "PENDING": continue
        a["status"] = "CANCELLED"; store.save(p, a); cancelled.append(a["approval_id"])
        store.audit(run_id, by, "CANCEL_APPROVAL", f"{a['approval_id']}：run {run_id} 取消（{reason}）")
        approval_render.render(a["approval_id"]); approval_render.render_html(a["approval_id"])
    return cancelled

@operation.operation("run_cancel", scope=lambda run_id, *a, **k: run_id)
def cancel(run_id: str, by: str):
    return cancel_body(run_id, by)

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
