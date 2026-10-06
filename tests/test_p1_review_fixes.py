"""P1 程式碼審查 P1-01～P1-06 的反例驗收（每個案例獨立暫存 root、子程序執行）。"""
import os, json, pathlib, textwrap, yaml, pytest
from tests import p1_util as U

FAULT_EXIT = 86

def spec_args(v="1.0"):
    return ["spec", "import", U.FIXTURES / f"SPEC-AUTH-001-v{v}.md", "--spec-id", "SPEC-AUTH-001", "--version", v, "--product", "demo", "--area", "AUTH", "--by", "t"]

# ---------------------------------------------------------------- P1-01：Validator FAIL 的 gate 中止後同請求續做
TO_T3 = textwrap.dedent("""
    from tools.qaos import engine, store
    from tests import helpers as H
    rid = engine.new_run("spec-to-testcase", {"spec_id": "SPEC-AUTH-001", "spec_version": "1.0"}, "t")["run_id"]
    rm = H.requirement_model(); refs_ = [{"entity_type": "SpecVersion", "id": "SPEC-AUTH-001", "version": "1.0"}]
    ch = store.load(store.spec_dir("SPEC-AUTH-001") / "spec.yaml")["versions"][0]["content_hash"]
    sa = {"spec_id": "SPEC-AUTH-001", "spec_version": "1.0", "content_hash": ch, "summary": "s", "scope": {"in_scope": ["x"], "out_of_scope": []},
          "requirement_ids": [r["requirement_id"] for r in rm["requirements"]], "ambiguities": [], "constraints": [], "edge_case_candidates": [], "open_questions": []}
    _, p1 = H.write_artifact(rid, "T1", "agent-spec-analyst", "SpecAnalysis", sa, refs_, {"type": "SpecVersion", "ids": ["SPEC-AUTH-001@1.0"]}, "spec-analysis")
    rmid, p2 = H.write_artifact(rid, "T1", "agent-spec-analyst", "RequirementModel", rm, refs_, {"type": "SpecVersion", "ids": ["SPEC-AUTH-001@1.0"]}, "requirements")
    assert engine.submit(rid, "T1", str(p1))[0] and engine.submit(rid, "T1", str(p2))[0] and engine.evaluate_gate(rid, "T1")["result"] == "PASS"
    tcs, ids_ = H.draft_set()
    refs2 = [{"entity_type": "Requirement", "id": r} for r in ["REQ-AUTH-001", "REQ-AUTH-002", "REQ-AUTH-003", "REQ-AUTH-004"]] + [{"entity_type": "Artifact", "id": rmid}]
    did, pd = H.write_artifact(rid, "T2", "agent-test-designer", "TestCaseDraft", {"mode": "spec", "spec_id": "SPEC-AUTH-001", "spec_version": "1.0", "testcases": tcs}, refs2, {"type": "RequirementModel", "ids": [rmid]}, "test-design")
    _, pr = H.write_artifact(rid, "T2", "agent-test-designer", "TestDesignReport", H.design_report(did, tcs), [{"entity_type": "Artifact", "id": did}], {"type": "TestCaseDraft", "ids": [did]}, "test-design")
    assert engine.submit(rid, "T2", str(pd))[0] and engine.submit(rid, "T2", str(pr))[0] and engine.evaluate_gate(rid, "T2")["result"] == "PASS"
    issue = {"testcase_id": ids_[2], "issue_type": "spec_mismatch", "severity": "major", "violated_requirement": "REQ-AUTH-002", "spec_reference": None,
             "evidence": "x", "explanation": "x", "recommended_change": "x"}
    _, pv = H.write_artifact(rid, "T3", "agent-test-validator", "TestValidationReport", H.validation_report(did, rmid, "FAIL", [issue]),
                             [{"entity_type": "Artifact", "id": did}, {"entity_type": "Artifact", "id": rmid}], {"type": "TestCaseDraft", "ids": [did]}, "validation")
    assert engine.submit(rid, "T3", str(pv))[0]
    print(rid)
""")

def _to_t3(root):
    U.import_auth_spec(root)
    return U.py(root, TO_T3).stdout.strip().splitlines()[-1]

@pytest.mark.parametrize("entry", ["resend", "resume"])
def test_p1_01_validator_fail_gate_abort_then_resume(entry):
    root = U.mkroot(); rid = _to_t3(root)
    args = ["gate", rid, "T3"]
    r = U.q(root, *args, fault="after_progress:1"); assert r.returncode == FAULT_EXIT
    op = U.incomplete(root)[0]["op_id"]
    assert U.load(root, f"runs/{rid}/run.yaml")["tasks"][2]["output_artifact_ids"] == []      # 退回已清空 outputs（中止點在 run.yaml 之後）
    r = U.q(root, *args) if entry == "resend" else U.q(root, "operation", "resume", op)
    assert r.returncode in (0, 1) and "拒絕" not in r.stderr, r.stderr                          # gate FAIL 的 CLI 回傳 1
    assert U.incomplete(root) == []
    run = U.load(root, f"runs/{rid}/run.yaml"); assert run["current_task_id"] == "T2" and run["tasks"][1]["iteration"] == 1
    again = U.q(root, *args); assert "先前已完成的同一請求" in again.stderr                        # 完成後重送：同一 op，回報已完成
    assert len([o for o in U.op_list(root) if o["action"] == "evaluate_gate"]) == 3

# ---------------------------------------------------------------- P1-02：fork 子程序繼承的擷取失效
def test_p1_02_fork_inside_active_capture_cannot_write():
    root = U.mkroot(); d = pathlib.Path(root) / "_sync"; d.mkdir()
    code = textwrap.dedent(f"""
        import os, json, time
        from tools.qaos import operation as op, store, tc_export
        def body():
            pid = os.fork()
            if pid == 0:
                res = {{"capturing": store.capturing() is not None, "in_operation": op.in_operation()}}
                try: store.save("child.yaml", {{}}); res["save"] = "written"
                except store.NoExecutorContext: res["save"] = "refused"
                try: tc_export.export("AUTH"); res["api"] = "accepted"
                except op.LockHeld: res["api"] = "lock_held"
                open("{d}/child1.json", "w").write(json.dumps(res))
                while not os.path.exists("{d}/parent_done"): time.sleep(0.02)
                try: tc_export.export("AUTH", new_request=True); res2 = "ok"       # 父程序結束後：新的 executor 正式取鎖
                except Exception as e: res2 = repr(e)
                open("{d}/child2.json", "w").write(json.dumps(res2)); os._exit(0)
            while not os.path.exists("{d}/child1.json"): time.sleep(0.02)
            store.save("parent.yaml", {{"ok": 1}}); return pid
        pid = op.run_operation("test_internal", body, new_request=True)
        open("{d}/parent_done", "w").write("1"); os.waitpid(pid, 0)
        res = {{}}
        try: store.begin_capture("t", "t", "x" * 64); res["forge"] = "accepted"
        except store.NoExecutorContext: res["forge"] = "refused"
        print(json.dumps(res))
    """)
    out = json.loads(U.py(root, code).stdout.strip().splitlines()[-1])
    c1 = json.loads((d / "child1.json").read_text()); c2 = json.loads((d / "child2.json").read_text())
    assert c1 == {"capturing": False, "in_operation": False, "save": "refused", "api": "lock_held"}, c1
    assert c2 == "ok" and out == {"forge": "refused"}
    assert not (pathlib.Path(root) / "child.yaml").exists() and (pathlib.Path(root) / "parent.yaml").exists()

# ---------------------------------------------------------------- P1-03：登錄紀錄各欄位的竄改
def _tamper_reg(root, op, field):
    reg = next(pathlib.Path(root).glob(f"operations/_global/index.d/*-{op}.yaml")); d = yaml.safe_load(reg.read_text())
    if field == "plan_seq":
        d["plan_seq"] += 100; reg.rename(reg.with_name(f"{d['plan_seq']:08d}-{op}.yaml")); reg = reg.with_name(f"{d['plan_seq']:08d}-{op}.yaml")
    elif field == "filename": reg.rename(reg.with_name(f"{d['plan_seq'] + 1:08d}-{op}.yaml")); return
    else: d[field] = {"action": "migrate_rollback", "registered_at": "2000-01-01T00:00:00Z", "plan_sha256": "0" * 64}[field]
    reg.write_text(yaml.safe_dump(d))

@pytest.mark.parametrize("state", ["in_progress", "completed"])
@pytest.mark.parametrize("field", ["action", "registered_at", "plan_sha256", "plan_seq", "filename"])
def test_p1_03_registration_tamper_is_refused(state, field):
    root = U.mkroot(); args = spec_args()
    if state == "in_progress": assert U.q(root, *args, fault="after_register").returncode == FAULT_EXIT
    else: U.q(root, *args, check=True)
    op = next(o["op_id"] for o in U.op_list(root) if o["action"] == "spec_import")
    _tamper_reg(root, op, field)
    for cmd in ([*args], ["operation", "resume", op], ["operation", "list"]):
        r = U.q(root, *cmd); assert r.returncode != 0 and ("不符" in r.stderr or "衝突" in r.stderr), (cmd, r.stderr)

def test_p1_03_completed_status_tamper_is_refused():
    root = U.mkroot(); args = spec_args(); U.q(root, *args, check=True)
    op = next(o["op_id"] for o in U.op_list(root) if o["action"] == "spec_import")
    st = pathlib.Path(root) / f"operations/_global/status.d/{op}-completed.yaml"; st.write_text(st.read_text() + "x: 1\n")
    r = U.q(root, *args); assert r.returncode != 0 and "狀態紀錄" in r.stderr

# ---------------------------------------------------------------- P1-04：render 的 legacy 狀態 fail closed
def _legacy_migrated_root():
    from tests.test_p1_audit import legacy_root
    root, run_id, run_legacy, glob_legacy = legacy_root()
    U.q(root, "maintenance", "start", "--by", "m", check=True)
    U.q(root, "migrate", "--by", "m", "--acknowledge-idle", run_id, check=True)
    U.q(root, "maintenance", "end", "--by", "m", check=True)
    return root, run_id

@pytest.mark.parametrize("case", ["global_missing", "global_unknown", "old_run_missing"])
def test_p1_04_render_refuses_missing_or_unknown_legacy_state(case):
    root, run_id = _legacy_migrated_root()
    mkp = pathlib.Path(root) / "artifacts/requirements/_migration.yaml"; mk = yaml.safe_load(mkp.read_text())
    if case == "global_missing": del mk["logs"]["runs/_audit.log"]                 # 故障注入
    elif case == "global_unknown": mk["logs"]["runs/_audit.log"]["legacy"] = "weird"
    else: del mk["logs"][f"runs/{run_id}/audit.log"]
    mkp.write_text(yaml.safe_dump(mk, allow_unicode=True))
    target = ["audit", "render", run_id] if case == "old_run_missing" else ["audit", "render", "--global", "--new-request"]
    before = U.snapshot(root); n = len(U.op_list(root))
    r = U.q(root, *target); assert r.returncode != 0 and "legacy" in r.stderr, r.stderr
    assert U.diff(before, U.snapshot(root)) == {"added": [], "removed": [], "changed": []} and len(U.op_list(root)) == n

def test_p1_04_new_run_after_migration_still_renders():
    root, _ = _legacy_migrated_root()
    r = U.q(root, "run", "new", "regression-generation", "--input", 'target_suites=["full_regression"]', "--input", "scope=all", "--input", "trigger=manual", "--by", "t", check=True)
    rid = r.stdout.split()[0]
    assert "CREATE_WORKFLOW_RUN" in (pathlib.Path(root) / f"runs/{rid}/audit.log").read_text()

# ---------------------------------------------------------------- P1-05：驗證失敗只寫診斷（含第 3 次）；越權失敗是正常操作
def _reg_run(root):
    r = U.q(root, "run", "new", "regression-generation", "--input", 'target_suites=["full_regression"]', "--input", "scope=all", "--input", "trigger=manual", "--by", "t", check=True)
    return r.stdout.split()[0]

def _bad_artifact(root, run_id, agent="agent-regression-curator", subdir="regression"):
    code = f"""
from tests import helpers as H
rp, p = H.write_artifact("{run_id}", "T1", "{agent}", "RegressionProposal", {{"suite_id": "X"}}, [], {{"type": "Registry", "ids": []}}, "{subdir}")
print(p)
"""
    return U.py(root, code).stdout.strip()

def test_p1_05_three_structural_failures_only_diagnostics():
    root = U.mkroot(); rid = _reg_run(root)
    for i in range(3):
        art = _bad_artifact(root, rid); a_sha = U.sha(art)
        before = U.snapshot(root); n = len(U.op_list(root))
        r = U.q(root, "submit", rid, "T1", art); assert r.returncode != 0 and "INVALID" in r.stdout
        d = U.diff(before, U.snapshot(root))
        assert len(U.op_list(root)) == n and U.unregistered_plans(root) == []                           # 沒有計畫、登錄
        assert d["changed"] == [f"runs/{rid}/run.yaml"] and d["removed"] == [], d                         # artifact 不改
        assert len(d["added"]) == 1 and "/audit.d/adhoc-" in d["added"][0], d
        assert U.sha(art) == a_sha
        assert not list(pathlib.Path(root).glob("approvals/APR-*.yaml"))                                  # 沒有核准單
    run = U.load(root, f"runs/{rid}/run.yaml")
    assert run["status"] == "RUNNING" and not run.get("waiting_on_approval_id") and run["tasks"][0]["status"] == "READY"

def test_p1_05_permission_violation_is_a_normal_operation():
    """越權（Test Designer 冒充 T1 提交 RequirementModel）→ 依 Oscar 決定視為正常操作：建立計畫、run FAILED。"""
    root = U.mkroot(); U.import_auth_spec(root)
    rid = U.q(root, "run", "new", "spec-to-testcase", "--input", "spec_id=SPEC-AUTH-001", "--input", "spec_version=1.0", "--by", "t", check=True).stdout.split()[0]
    art = U.py(root, f"""
from tests import helpers as H
_, p = H.write_artifact("{rid}", "T1", "agent-test-designer", "RequirementModel", H.requirement_model(),
    [{{"entity_type": "SpecVersion", "id": "SPEC-AUTH-001", "version": "1.0"}}], {{"type": "SpecVersion", "ids": ["SPEC-AUTH-001@1.0"]}}, "spec-analysis")
print(p)
""").stdout.strip()
    n = len(U.op_list(root))
    r = U.q(root, "submit", rid, "T1", art); assert r.returncode != 0 and "越權" in r.stdout, r.stdout
    assert len(U.op_list(root)) == n + 1 and U.op_list(root)[-1]["action"] == "submit" and U.incomplete(root) == []
    run = U.load(root, f"runs/{rid}/run.yaml"); assert run["status"] == "FAILED" and run["tasks"][0]["permission_violations"]

# ---------------------------------------------------------------- P1-06：計畫保存前中止的殘留
@pytest.mark.parametrize("how", ["fault", "kill"])
def test_p1_06_residue_before_plan_save_is_cleaned(how, tmp_path):
    import signal, subprocess, sys, time
    root = U.mkroot(); before = U.snapshot(root)
    if how == "fault":
        assert U.q(root, *spec_args(), fault="before_plan_save").returncode == FAULT_EXIT
    else:
        from tests.test_p1_lock_fork import popen_q, wait_file
        d = tmp_path / "p"; p = popen_q(root, spec_args(), pause=("after_lock", d))
        wait_file(d / "paused"); p.send_signal(signal.SIGKILL); p.wait(timeout=30)
    left = U.diff(before, U.snapshot(root))["added"]
    U.q(root, *spec_args("1.1"), check=True)                                                              # 下一個寫入請求持鎖清除
    new_ops = {o["op_id"] for o in U.op_list(root)} - {o["op_id"] for o in U.op_list(root)[:-1]}
    after = U.diff(before, U.snapshot(root))["added"]
    stray = [p for p in after if p.startswith("operations/") and not any(op in p for op in new_ops) and "/index.d/" not in p and "/status.d/" not in p]
    assert stray == [], (left, stray)
    assert not list(pathlib.Path(root).rglob(".qaos-tmp-*"))
