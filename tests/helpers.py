"""測試用：模擬各 Agent 產出 artifact（Phase 3 前由測試手寫）。"""
import pathlib, yaml
from tools.qaos import store, ids

def raw_save(path, obj):
    """測試專用：模擬 QAOS 以外的寫入（agent 產出 artifact、或標明的竄改反例），直接寫檔、不經 executor。
    QAOS 自己的寫入一律經過 executor；這個函式只能用在「外部寫入」的情境。"""
    p = store.ROOT / store.rel(path); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump(obj, allow_unicode=True, sort_keys=False, width=120), encoding="utf-8"); return p

def packet_sha(run_id, task_id, auto=True):
    """task 本次 iteration 的派發包 sha256。auto=True 且還沒派發時，以正式指令 dispatch 產生（模擬 orchestrator 在派工前執行 qaos dispatch）；
    task 不存在、不需要派發包或狀態不允許時回傳 None（讓刻意送錯的反例照原本的方式失敗）。"""
    from tools.qaos import engine, dispatch
    try: run = engine.load_run(run_id); task = engine._task(run, task_id)
    except (FileNotFoundError, StopIteration): return None
    if not dispatch.needs_packet(task): return None
    e = dispatch.current_entry(task)
    if e is None and auto and task["status"] in ("READY", "RUNNING") and run["status"] == "RUNNING":
        try: e = dispatch.dispatch(run_id, task_id)
        except dispatch.DispatchError: return None
    return e["sha256"] if e else None

def consulted_all(run_id, task_id, sha):
    """模擬 Spec Analyst 讀完目標與派發包（sha 指定的那一份）中的全部必讀參考（read_scope: full）。"""
    from tools.qaos import engine, dispatch
    e = next((x for x in engine._task(engine.load_run(run_id), task_id).get("dispatch_packets") or [] if x["sha256"] == sha), None)
    if e is None: return []
    pk = dispatch.load_packet(e)
    pins = [pk["target"]] + [n for n in pk["closure"] if n["required"]]
    return [{"spec_id": p["spec_id"], "spec_version": p["spec_version"], "content_hash": p["content_hash"], "read_scope": "full"} for p in pins]

def write_artifact(run_id, task_id, agent, artifact_type, payload, references, source, subdir, iteration=0, requires_approval=None, packet="auto", alloc_req=True, created_at=None):
    """packet：'auto' 自動派發並填入本次 iteration 的派發包 sha；None 不填；字串則直接填入（反例用）。
    alloc_req=False：不替 RequirementModel 配發 REQ ID（模擬 agent 自行編號的反例）；created_at：指定 envelope 時間（反例用）。"""
    aid = ids.artifact_id(artifact_type)
    sha = packet_sha(run_id, task_id) if packet == "auto" else packet       # 先派發再產出：created_at 不得早於派發包
    if artifact_type == "RequirementModel" and alloc_req: alloc_req_ids(payload)
    art = {"artifact_id": aid, "artifact_type": artifact_type, "schema_version": "1.0", "version": 1, "run_id": run_id, "task_id": task_id,
           "iteration": iteration, "created_by": agent, "created_at": created_at or store.now(), "status": "DRAFT",
           "source": source, "references": references, "requires_approval": requires_approval, "payload": payload}
    if sha: art["dispatch_packet_sha256"] = sha
    if artifact_type == "SpecAnalysis" and "consulted_sources" not in payload and sha:
        payload["consulted_sources"] = consulted_all(run_id, task_id, sha)
    p = store.ROOT / "artifacts" / subdir / run_id / f"{aid}.yaml"
    raw_save(p, art); return aid, p

def alloc_req_ids(payload):
    """模擬主 session 以 bin/qaos id REQ --area <AREA> 配發、再交給 Spec Analyst 的 REQ ID（agent 不自行配號）：
    經正式 executor 把計數器推進到測試 payload 用到的最大序號（G-SPEC 會核對）。這是測試 fixture，不是 agent 行為或派發訊息交付的端到端測試。"""
    import re
    want = {}
    for r in payload.get("requirements") or []:
        m = re.fullmatch(r"REQ-([A-Z0-9]+)-(\d+)", str(r.get("requirement_id")))
        if m: want[m.group(1)] = max(want.get(m.group(1), 0), int(m.group(2)))
    for area, n in want.items():
        while ids._load()["counters"].get(f"REQ-{area}", 0) < n: ids.alloc_cmd("REQ", area, new_request=True)

def spec_ref(loc, quote=""): return {"spec_id": "SPEC-AUTH-001", "spec_version": "1.0", "location": loc, "quote": quote}

def requirement_model(spec_version="1.0", min_len="8"):
    sr = lambda loc, q="": {"spec_id": "SPEC-AUTH-001", "spec_version": spec_version, "location": loc, "quote": q}
    reqs = [
        {"requirement_id": "REQ-AUTH-001", "version": 1, "spec_id": "SPEC-AUTH-001", "spec_version": spec_version, "type": "functional", "title": "密碼最小長度",
         "statement": f"密碼長度必須大於或等於 {min_len} 個字元", "acceptance_criteria": [
             {"ac_id": "AC-AUTH-001", "given": "使用者在設定密碼", "when": f"輸入長度為 {min_len} 的密碼", "then": "系統接受"},
             {"ac_id": "AC-AUTH-002", "given": "使用者在設定密碼", "when": f"輸入長度為 {int(min_len)-1} 的密碼", "then": "系統拒絕並提示長度不足"}],
         "spec_reference": sr("§3.1 R1", f"密碼長度必須大於或等於 {min_len} 個字元"), "ambiguity": None, "risk": "high", "status": "DRAFT", "history": []},
        {"requirement_id": "REQ-AUTH-002", "version": 1, "spec_id": "SPEC-AUTH-001", "spec_version": spec_version, "type": "functional", "title": "密碼需含數字",
         "statement": "密碼必須包含至少一個數字", "acceptance_criteria": [
             {"ac_id": "AC-AUTH-003", "given": "使用者在設定密碼", "when": "輸入不含數字的密碼", "then": "系統拒絕並提示需含數字"}],
         "spec_reference": sr("§3.1 R2"), "ambiguity": None, "risk": "medium", "status": "DRAFT", "history": []},
        {"requirement_id": "REQ-AUTH-003", "version": 1, "spec_id": "SPEC-AUTH-001", "spec_version": spec_version, "type": "functional", "title": "連續失敗鎖定",
         "statement": "同一帳號連續 5 次密碼錯誤後鎖定 15 分鐘", "acceptance_criteria": [
             {"ac_id": "AC-AUTH-004", "given": "帳號已連續錯 4 次", "when": "第 5 次輸入錯誤密碼", "then": "帳號鎖定 15 分鐘，後續登入回「帳號已鎖定」"}],
         "spec_reference": sr("§3.2 R3"), "ambiguity": None, "risk": "high", "status": "DRAFT", "history": []},
        {"requirement_id": "REQ-AUTH-004", "version": 1, "spec_id": "SPEC-AUTH-001", "spec_version": spec_version, "type": "functional", "title": "登入成功",
         "statement": "帳號密碼正確時導向首頁並顯示使用者名稱", "acceptance_criteria": [
             {"ac_id": "AC-AUTH-005", "given": "帳號存在且啟用", "when": "輸入正確帳密", "then": "導向首頁並顯示使用者名稱"}],
         "spec_reference": sr("§3.3 R4"), "ambiguity": None, "risk": "medium", "status": "DRAFT", "history": []},
    ]
    return {"spec_id": "SPEC-AUTH-001", "spec_version": spec_version, "requirements": reqs,
            "traceability": [{"requirement_id": r["requirement_id"], "spec_reference": r["spec_reference"]} for r in reqs]}

def tc(draft_id, title, req, ac, level, types, techs, steps, expected, loc, prio="high", risk="high", mode="spec", **kw):
    d = {"draft_id": draft_id, "title": title, "product": "demo", "functional_area": "AUTH", "requirement_ids": [req], "acceptance_criteria_ids": [ac],
         "spec_id": "SPEC-AUTH-001", "spec_version": kw.pop("spec_version", "1.0"), "test_level": level, "test_types": types, "design_techniques": techs,
         "priority": prio, "risk": risk, "execution_mode": kw.pop("execution_mode", "automated"), "preconditions": kw.pop("preconditions", ["使用者在密碼設定頁"]),
         "test_data": kw.pop("test_data", []), "steps": [{"n": i + 1, "action": s} for i, s in enumerate(steps)], "expected_result": expected,
         "expected_result_spec_reference": {"spec_id": "SPEC-AUTH-001", "spec_version": d_sv if (d_sv := kw.pop("ref_version", None)) else "1.0", "location": loc},
         "assumptions": [], "automation_status": "not_automated", "ci_eligible": kw.pop("ci_eligible", True), "hotfix_eligible": True, "execution_cost": "low",
         "stability": "unknown", "critical_path": kw.pop("critical_path", False),
         "source": {"spec": "spec_workflow", "change": "change_workflow", "manual": "manual_integration"}[mode]}
    d.update(kw); return d

def draft_set(min_len=8, prefix="01ARZ3NDEKTSV4RRFFQ69G5FA"):
    ids_ = [f"TC-DRAFT-{prefix}{c}" for c in "ABCDE"]
    return [
        tc(ids_[0], f"密碼長度恰為 {min_len} 時接受", "REQ-AUTH-001", "AC-AUTH-001", "api", ["functional", "boundary"], ["boundary_value"],
           [f"輸入長度 {min_len} 且含數字的密碼", "送出"], "系統接受密碼", "§3.1 R1", critical_path=True),
        tc(ids_[1], f"密碼長度為 {min_len-1} 時拒絕", "REQ-AUTH-001", "AC-AUTH-002", "api", ["negative", "boundary"], ["boundary_value", "negative"],
           [f"輸入長度 {min_len-1} 且含數字的密碼", "送出"], "系統拒絕，提示長度不足", "§3.1 R1"),
        tc(ids_[2], "密碼不含數字時拒絕", "REQ-AUTH-002", "AC-AUTH-003", "api", ["negative"], ["equivalence_partitioning", "negative"],
           ["輸入長度 12 但不含數字的密碼", "送出"], "系統拒絕，提示需含數字", "§3.1 R2", prio="medium", risk="medium"),
        tc(ids_[3], "連續 5 次錯誤後鎖定 15 分鐘", "REQ-AUTH-003", "AC-AUTH-004", "ui_e2e", ["functional", "negative"], ["state_transition"],
           ["以錯誤密碼登入 4 次", "第 5 次以錯誤密碼登入", "立即以正確密碼登入"], "第 5 次後顯示帳號已鎖定；正確密碼亦被拒絕", "§3.2 R3",
           preconditions=["帳號存在且未鎖定"], execution_mode="manual", ci_eligible=False),
        tc(ids_[4], "正確帳密登入成功", "REQ-AUTH-004", "AC-AUTH-005", "ui_e2e", ["functional"], ["scenario"],
           ["輸入正確帳密", "點擊登入"], "導向首頁並顯示使用者名稱", "§3.3 R4", prio="medium", risk="medium", preconditions=["帳號存在且啟用"], critical_path=True),
    ], ids_

def design_report(draft_aid, tcs, uncovered=None):
    cov = {}
    for t in tcs:
        for r in t["requirement_ids"]: cov.setdefault(r, []).append(t["draft_id"])
    return {"mode": "spec", "testcase_draft_artifact_id": draft_aid,
            "coverage_matrix": [{"requirement_id": r, "draft_ids": d} for r, d in cov.items()],
            "uncovered_with_reason": uncovered or [],
            "technique_summary": [{"technique": k, "count": v} for k, v in __import__("collections").Counter(t2 for t in tcs for t2 in t["design_techniques"]).items()],
            "self_check": {"requirements_covered": True, "acceptance_criteria_covered": True, "negative_considered": True, "boundary_considered": True,
                           "expected_results_traceable": True, "no_unsupported_assumptions": True, "duplicate_detection_completed": True},
            "assumptions": [], "duplicate_check": {"against_registry": True, "findings": []}}

def validation_report(draft_aid, rm_aid, result, issues=None, spec_version="1.0"):
    return {"result": result, "testcase_draft_artifact_id": draft_aid,
            "validated_against": {"spec_id": "SPEC-AUTH-001", "spec_version": spec_version, "requirement_model_artifact_id": rm_aid},
            "issues": issues or [], "advisories": [],
            "coverage_summary": {"requirements_total": 4, "requirements_covered": 4, "ac_total": 5, "ac_covered": 5},
            "checks": {k: result == "PASS" or k != "no_spec_mismatch" for k in ["no_spec_mismatch", "no_requirement_mismatch", "expected_result_valid", "steps_executable", "traceability_complete", "no_critical_ambiguity", "no_duplicates", "edge_cases_reasonable"]}}
