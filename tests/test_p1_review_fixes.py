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

DIAG_CASES = ["legit", "other_file", "run_field", "two_tasks", "rewrite_gate_results", "two_events",
              "status_done", "status_failed", "status_forced", "updated_at", "gate_pass", "gate_two", "started_at", "history_rewrite"]

@pytest.mark.parametrize("bad", DIAG_CASES)
def test_p1_05_diagnostic_beyond_boundary_is_refused(bad):
    """診斷擷取超出附錄 A 4-16 的邊界 → 拒絕、完整快照不變（以測試專用的內部呼叫造出越界寫入）。
    legit 是對照組：照 engine 的正式轉換（RUNNING → ARTIFACT_INVALID → READY）只寫允許的診斷，必須被接受。"""
    root = U.mkroot(); rid = _reg_run(root)
    assert U.q(root, "submit", rid, "T1", _bad_artifact(root, rid)).returncode != 0          # 先有一筆合法診斷（gate_results、history、started_at 非空）
    code = f"""
from tools.qaos import operation as op, store, state, engine
S = engine.SYSTEM; bad = "{bad}"
def body():
    store.mark_diagnostic()
    run = store.load("runs/{rid}/run.yaml"); t = run["tasks"]
    state.apply("task", t[0], "RUNNING", S, "x")
    if bad == "status_done": state.apply("task", t[0], "DONE", S, "x")
    elif bad == "status_failed": state.apply("task", t[0], "FAILED", S, "x")
    else: state.apply("task", t[0], "ARTIFACT_INVALID", S, "x"); state.apply("task", t[0], "READY", S, "x")
    if bad == "status_forced": t[0]["status"] = "DONE"
    t[0]["gate_results"].append({{"at": store.now(), "layer": "structural", "result": "PASS" if bad == "gate_pass" else "FAIL", "details": []}})
    if bad == "gate_two": t[0]["gate_results"].append({{"at": store.now(), "layer": "structural", "result": "FAIL", "details": []}})
    if bad == "rewrite_gate_results": t[0]["gate_results"][0] = {{**t[0]["gate_results"][0], "result": "PASS"}}
    if bad == "history_rewrite": t[0]["history"][0]["by"] = "someone"
    if bad == "started_at": t[0]["started_at"] = "2000-01-01T00:00:00Z"
    if bad == "run_field": run["status"] = "FAILED"
    if bad == "two_tasks": t[1]["status"] = "READY"
    engine._save_run(run)
    if bad == "updated_at": run["updated_at"] = "2000-01-01T00:00:00Z"; store.save("runs/{rid}/run.yaml", run)
    if bad == "other_file": store.save("artifacts/x.yaml", {{"a": 1}})
    store.audit("{rid}", "t", "ARTIFACT_INVALID")
    if bad == "two_events": store.audit("{rid}", "t", "ARTIFACT_INVALID")
try: op.run_operation("test_internal", body, new_request=True); print("accepted")
except op.OperationError as e: print("refused", e)
"""
    before = U.snapshot(root); n = len(U.op_list(root))
    out = U.py(root, code).stdout.strip().splitlines()[-1]
    d = U.diff(before, U.snapshot(root))
    if bad == "legit":
        assert out == "accepted" and d["changed"] == [f"runs/{rid}/run.yaml"] and len(d["added"]) == 1 and "/adhoc-" in d["added"][0], (out, d)
        assert U.load(root, f"runs/{rid}/run.yaml")["tasks"][0]["status"] == "READY"
    else:
        assert out.startswith("refused"), out
        assert d == {"added": [], "removed": [], "changed": []}, d
    assert len(U.op_list(root)) == n

# ---------------------------------------------------------------- P1-06／P1R2-01／P1R3-01、02：只清寫入清單列出的殘留
def _plant_foreign(root):
    """模擬其他程式放在 operations/ 下的內容（不是 executor 寫的）；回傳路徑 → 內容。另建一個空的 hex 目錄。"""
    import hashlib
    r = pathlib.Path(root); blob = b"external CAS contents"; sha = hashlib.sha256(blob).hexdigest()
    files = {"operations/_global/other-tool/important.txt": b"keep",
             f"operations/_global/{'a' * 64}/external.txt": b"keep",                              # 64 hex 目錄，但內容不是 blobs
             f"operations/_global/{'b' * 64}/blobs/{'c' * 64}": blob,                           # 名稱和內容 hash 不符
             f"operations/_global/{'d' * 64}/blobs/{sha}": blob,                                # 形狀完全符合（只有合法內容檔），但沒有寫入清單
             f"operations/misc/{'e' * 64}/blobs/{sha}": blob,                                   # 不合法的 scope
             f"operations/_global/.qaos-tmp-{'f' * 16}-{'0' * 64}.yaml-01234567": b"keep",      # tag 和 op 不符
             f"operations/_global/staging.d/{'9' * 64}.yaml": b"kind: other\n",                # 不是 executor 的清單格式
             f"operations/_global/staging.d/notes.txt": b"keep"}
    for k, v in files.items():
        (r / k).parent.mkdir(parents=True, exist_ok=True); (r / k).write_bytes(v)
    (r / f"operations/_global/{'8' * 64}").mkdir(parents=True)                                     # 空的 hex 目錄
    return files

def _write_v11(root):
    before = U.snapshot(root); r = U.q(root, *spec_args("1.1"))
    return U.diff(before, U.snapshot(root)), r

@pytest.mark.parametrize("how", ["fault", "kill_after_staging", "kill_after_first_blob", "kill_blob_tmp_written"])
def test_p1_06_residue_before_plan_save_is_cleaned(how, tmp_path):
    import signal, collections, re as _re
    ref = U.mkroot(); _plant_foreign(ref); ref_d, _ = _write_v11(ref)                            # 對照：沒有中止時 v1.1 匯入的差異
    root = U.mkroot(); foreign = _plant_foreign(root); base = U.snapshot(root)
    if how == "fault":
        assert U.q(root, *spec_args(), fault="before_plan_save").returncode == FAULT_EXIT
    else:
        from tests.test_p1_lock_fork import popen_q, wait_file
        d = tmp_path / "p"; p = popen_q(root, spec_args(), pause=(how[len("kill_"):], d))
        wait_file(d / "paused"); p.send_signal(signal.SIGKILL); p.wait(timeout=30)
    left = U.diff(base, U.snapshot(root))
    assert left["removed"] == [] and left["changed"] == [] and left["added"], left
    assert any(x.startswith("operations/_global/staging.d/") for x in left["added"]), left             # 清單先於任何內容檔
    assert all(x.startswith("operations/_global/staging.d/") or "/blobs/" in x for x in left["added"]), left
    if how == "kill_blob_tmp_written": assert any("/blobs/.qaos-tmp-" in x for x in left["added"]), left
    d, r = _write_v11(root); assert r.returncode == 0, r.stderr                                    # 下一個寫入請求持鎖清除
    assert sorted(d["removed"]) == sorted(left["added"]), d                                        # 只刪本次殘留（含清單）
    norm = lambda xs: collections.Counter(_re.sub(r"/blobs/[0-9a-f]{64}$", "/blobs/<sha>", x) for x in xs)   # 內容檔名是含時間的 hash
    assert d["changed"] == ref_d["changed"] and norm(d["added"]) == norm(ref_d["added"]), (d, ref_d)
    for k, v in foreign.items(): assert (pathlib.Path(root) / k).read_bytes() == v                 # 外部內容原樣保留
    assert (pathlib.Path(root) / f"operations/_global/{'8' * 64}").is_dir()
    assert "保留無法辨識的內容" in r.stderr, r.stderr

def test_p1_06_abort_after_plan_save_keeps_blobs_and_drops_manifest():
    """計畫已保存、清單尚未刪除時中止 → 內容檔屬於計畫；同請求重送續做完成，清單被刪、內容檔保留。"""
    root = U.mkroot()
    assert U.q(root, *spec_args(), fault="after_plan_save").returncode == FAULT_EXIT
    op = U.unregistered_plans(root)[0]
    assert (pathlib.Path(root) / f"operations/_global/staging.d/{op}.yaml").exists()
    U.q(root, *spec_args(), check=True)
    assert not (pathlib.Path(root) / f"operations/_global/staging.d/{op}.yaml").exists()
    assert U.incomplete(root) == [] and list((pathlib.Path(root) / f"operations/_global/{op}/blobs").iterdir())

@pytest.mark.parametrize("state", ["completed", "in_progress"])
@pytest.mark.parametrize("variant", ["plan_removed", "plan_and_dir_removed", "plan_to_tmp"])
def test_p1_06_registered_without_plan_is_refused(variant, state):
    """有登錄紀錄卻沒有計畫（竄改反例）→ 拒絕寫入；拒絕前不清理任何東西（另有一份可清的殘留也保留）。"""
    import shutil
    root = U.mkroot()
    if state == "completed": U.q(root, *spec_args(), check=True)
    else: assert U.q(root, *spec_args(), fault="after_register").returncode == FAULT_EXIT
    op = next(o["op_id"] for o in U.op_list(root) if o["action"] == "spec_import")
    plan = pathlib.Path(root) / f"operations/_global/{op}.yaml"
    if variant == "plan_to_tmp": plan.rename(plan.with_name(f".qaos-tmp-{op[:16]}-{op}.yaml-01234567"))
    else:
        plan.rename(pathlib.Path(root) / "moved-plan.yaml")
        if variant == "plan_and_dir_removed": shutil.move(str(pathlib.Path(root) / f"operations/_global/{op}"), str(pathlib.Path(root) / "moved-op-dir"))
    # 另一份真正可清的殘留：以另一個 root 正式中止產生，複製過來（模擬同一 root 先前的中止）
    other = U.mkroot(); assert U.q(other, "tc-export", "AUTH", fault="before_plan_save").returncode == FAULT_EXIT
    for x in (pathlib.Path(other) / "operations/_global").rglob("*"):
        if x.is_file() and ("staging.d" in x.parts or "blobs" in x.parts):
            t = pathlib.Path(root) / x.relative_to(other); t.parent.mkdir(parents=True, exist_ok=True); t.write_bytes(x.read_bytes())
    before = U.snapshot(root)
    for cmd in (spec_args("1.1"), ["tc-export", "AUTH"]):
        r = U.q(root, *cmd); assert r.returncode != 0 and "有登錄紀錄卻沒有計畫" in r.stderr, r.stderr
    assert U.diff(before, U.snapshot(root)) == {"added": [], "removed": [], "changed": []}

# ---------------------------------------------------------------- P1R4-01：目標既存時不取得擁有權
def _staged(root):
    """root 中唯一一份寫入清單 → (op_id, manifest)。"""
    m = next(pathlib.Path(root).glob("operations/_global/staging.d/*.yaml"))
    return m.stem, yaml.safe_load(m.read_text())

def _tree_hash(d):
    import hashlib
    d = pathlib.Path(d)
    return {x.relative_to(d).as_posix(): hashlib.sha256(x.read_bytes()).hexdigest() for x in d.rglob("*") if x.is_file() and not x.is_symlink()}

@pytest.mark.parametrize("content", ["different", "same"])
def test_p1r4_01_preexisting_target_is_not_claimed(content):
    ref = U.mkroot(); assert U.q(ref, "tc-export", "AUTH", fault="before_plan_save").returncode == FAULT_EXIT
    op, man = _staged(ref); sha = man["blobs"][0]
    data = (pathlib.Path(ref) / f"operations/_global/{op}/blobs/{sha}").read_bytes() if content == "same" else b"pre-existing foreign file"
    root = U.mkroot(); victim = pathlib.Path(root) / f"operations/_global/{op}/blobs/{sha}"
    victim.parent.mkdir(parents=True); victim.write_bytes(data)                                     # 模擬其他程式先放好的檔案
    before = U.snapshot(root)
    r = U.q(root, "tc-export", "AUTH"); assert r.returncode != 0 and "不是本次建立的" in r.stderr, r.stderr
    assert U.diff(before, U.snapshot(root)) == {"added": [], "removed": [], "changed": []}            # 沒有建立認領、清單或任何檔案
    r = U.q(root, *spec_args()); assert r.returncode == 0, r.stderr                                 # 其他操作照常；既存檔案不被清
    assert victim.read_bytes() == data and "保留無法辨識的內容" in r.stderr
    assert U.q(root, "tc-export", "AUTH").returncode != 0 and victim.read_bytes() == data           # 衝突不會被自動處理成成功

# ---------------------------------------------------------------- P1R5-01：同 op 既存的 staging 入口不能被新認領檔追溯取得
@pytest.mark.parametrize("variant", ["manifest_other_format", "manifest_parseable", "manifest_symlink", "staging_tmp", "scope_plan_tmp"])
def test_p1r5_01_preexisting_staging_entry_is_not_claimed(variant, tmp_path):
    ref = U.mkroot(); assert U.q(ref, "tc-export", "AUTH", fault="before_plan_save").returncode == FAULT_EXIT
    op, _ = _staged(ref); ref_manifest = (pathlib.Path(ref) / f"operations/_global/staging.d/{op}.yaml").read_bytes()
    root = U.mkroot(); r_ = pathlib.Path(root); st = r_ / "operations/_global/staging.d"; st.mkdir(parents=True, exist_ok=True)
    path = {"manifest_other_format": st / f"{op}.yaml", "manifest_parseable": st / f"{op}.yaml", "manifest_symlink": st / f"{op}.yaml",
            "staging_tmp": st / f".qaos-tmp-{op[:16]}-{op}.yaml-01234567", "scope_plan_tmp": r_ / f"operations/_global/.qaos-tmp-{op[:16]}-{op}.yaml-01234567"}[variant]
    if variant == "manifest_symlink": (tmp_path / "victim").write_bytes(b"outside"); path.symlink_to(tmp_path / "victim")
    else: path.write_bytes({"manifest_other_format": b"kind: other\n", "manifest_parseable": ref_manifest}.get(variant, b"foreign temp keep"))   # 模擬請求前就存在的外部檔案
    data = path.read_bytes()
    before = U.snapshot(root)
    for fault in (None, "after_claim"):                                                             # 帶 after_claim 也在認領之前就被拒（不是 86）
        r = U.q(root, "tc-export", "AUTH", fault=fault); assert r.returncode == 1 and "不是本次建立的" in r.stderr, (fault, r.returncode, r.stderr)
        assert U.diff(before, U.snapshot(root)) == {"added": [], "removed": [], "changed": []}
        assert not (st / f"{op}.claim").exists()
    r = U.q(root, *spec_args()); assert r.returncode == 0, r.stderr                                 # 其他操作照常
    assert path.read_bytes() == data and (variant != "manifest_symlink" or path.is_symlink())       # 既存檔案保留
    r = U.q(root, *spec_args("1.1")); assert r.returncode == 0 and path.read_bytes() == data         # 再一個寫入請求的清理也不碰它
    assert U.q(root, "tc-export", "AUTH").returncode == 1 and not (st / f"{op}.claim").exists()    # 衝突不會被自動處理成成功

# ---------------------------------------------------------------- P1R4-02：路徑任何一層是 symlink → 拒絕，不刪任何東西
@pytest.mark.parametrize("level", ["scope", "op", "blobs", "staging", "file"])
def test_p1r4_02_symlink_anywhere_on_path_is_refused(level, tmp_path):
    import shutil
    root = U.mkroot(); assert U.q(root, *spec_args(), fault="before_plan_save").returncode == FAULT_EXIT
    op, man = _staged(root); r_ = pathlib.Path(root); outside = tmp_path / "foreign-store"; outside.mkdir()
    target = {"scope": r_ / "operations/_global", "op": r_ / f"operations/_global/{op}", "blobs": r_ / f"operations/_global/{op}/blobs",
              "staging": r_ / "operations/_global/staging.d"}.get(level)
    if level == "file":                                                                             # 清單列出的內容檔換成指向外部檔案的 symlink
        f = r_ / f"operations/_global/{op}/blobs/{man['blobs'][0]}"; (outside / "victim").write_bytes(f.read_bytes()); f.unlink(); f.symlink_to(outside / "victim")
    else:                                                                                           # 把該層目錄搬到 root 之外，原位置改為 symlink
        shutil.move(str(target), str(outside / "moved")); target.symlink_to(outside / "moved", target_is_directory=True)
    before_root, before_out = U.snapshot(root), _tree_hash(outside)
    r = U.q(root, "tc-export", "AUTH"); assert r.returncode != 0 and ("symlink" in r.stderr or "不是一般檔案" in r.stderr), r.stderr
    assert U.diff(before_root, U.snapshot(root)) == {"added": [], "removed": [], "changed": []}
    assert _tree_hash(outside) == before_out                                                        # 外部檔案一個都沒少

# ---------------------------------------------------------------- P1R4-03：建立證據途中中止、清理途中中止
@pytest.mark.parametrize("point", ["after_claim", "short:staging_manifest", "empty:staging_manifest"])
def test_p1r4_03_abort_while_creating_evidence_is_cleaned(point):
    root = U.mkroot(); base = U.snapshot(root)
    assert U.q(root, *spec_args(), fault=point).returncode == FAULT_EXIT
    left = U.diff(base, U.snapshot(root))["added"]
    assert left and all(x.startswith("operations/_global/staging.d/") for x in left), left          # 只有認領檔（與半寫的清單暫存）
    assert any(x.endswith(".claim") for x in left) and (point == "after_claim" or any("/.qaos-tmp-" in x for x in left)), left
    d, r = _write_v11(root); assert r.returncode == 0, r.stderr
    assert sorted(d["removed"]) == sorted(left), d
    assert not list((pathlib.Path(root) / "operations/_global/staging.d").iterdir())

def test_p1r4_03_cleanup_interrupted_twice_then_completes():
    root = U.mkroot(); base = U.snapshot(root)
    assert U.q(root, *spec_args(), fault="before_plan_save").returncode == FAULT_EXIT
    left = U.diff(base, U.snapshot(root))["added"]; n_blobs = sum("/blobs/" in x for x in left); assert n_blobs >= 2
    for i in range(2):                                                                              # 清理刪掉一個檔案就中止，兩次
        assert U.q(root, *spec_args("1.1"), fault="cleanup_mid").returncode == FAULT_EXIT
        now = U.diff(base, U.snapshot(root))["added"]
        assert sum("/blobs/" in x for x in now) == n_blobs - (i + 1) and any(x.endswith(".claim") for x in now)   # 證據最後才刪
    d, r = _write_v11(root); assert r.returncode == 0, r.stderr
    assert not [x for x in U.snapshot(root) if x in left]                                            # 殘留全部清除
    assert not list((pathlib.Path(root) / "operations/_global/staging.d").iterdir())

# ---------------------------------------------------------------- P1R2-02：store 單獨載入時不能自建擷取
def test_p1r2_02_store_alone_fails_closed():
    root = U.mkroot()
    code = """
import sys, json
from tools.qaos import store
res = {"operation_loaded": "tools.qaos.operation" in sys.modules}
try: store.begin_capture("t", "t", "0" * 64); res["begin"] = "accepted"
except store.NoExecutorContext: res["begin"] = "refused"
store._CAP = store.Capture("t", "t", "0" * 64)
res["capturing"] = store.capturing() is not None
try: store.save("x.yaml", {"a": 1}); res["save"] = "accepted"
except store.NoExecutorContext: res["save"] = "refused"
from tools.qaos import operation
store._CAP = store.Capture("t", "t", "0" * 64, owner_token="forged")
try: store.save("y.yaml", {"a": 1}); res["after_import"] = "accepted"
except store.NoExecutorContext: res["after_import"] = "refused"
print(json.dumps(res))
"""
    out = json.loads(U.py(root, code).stdout.strip().splitlines()[-1])
    assert out == {"operation_loaded": False, "begin": "refused", "capturing": False, "save": "refused", "after_import": "refused"}, out
    assert not (pathlib.Path(root) / "x.yaml").exists() and not (pathlib.Path(root) / "y.yaml").exists()

# ---------------------------------------------------------------- P1R2-04：render 以解析後的時間判定移轉後的新 run
RENDER_CASES = [("2026-10-07T03:00:00+08:00", False), ("2026-10-07T01:00:00.001Z", True), ("2026-10-07T01:00:00Z", True),
                ("2026-10-07T09:00:00+08:00", True), ("2026-10-07T00:59:59.999Z", False), ("2026-10-07T02:00:00", False),
                ("garbage", False), (None, False)]

@pytest.mark.parametrize("source", ["overlay", "disk"])
def test_p1r2_04_render_compares_parsed_times(source):
    root = U.mkroot(); rid = "RUN-20261007-900"
    code = f"""
import json, yaml, pathlib
from tools.qaos import operation as op, store
mk = {{"migrated_at": "2026-10-07T01:00:00Z", "runs": [], "logs": {{"runs/_audit.log": {{"legacy": "absent"}}}}}}
cases = {RENDER_CASES!r} + [["2026-10-07T05:00:00Z", "in_runs"]]
out = []
for created, _ in cases:
    m = dict(mk, runs=["{rid}"]) if _ == "in_runs" else mk
    data = yaml.safe_dump({{"run_id": "{rid}", **({{"created_at": created}} if created is not None else {{}})}}).encode()
    if "{source}" == "disk":   # 模擬既有的 run.yaml（測試直接寫檔）；另含一個未加引號、YAML 解析成 datetime 的寫法
        p = store.ROOT / "runs/{rid}/run.yaml"; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(data); ov = None
    else: ov = {{"runs/{rid}/run.yaml": data}}
    try: op.render_log_bytes("runs/{rid}/audit.log", [], m, overlay=ov); out.append(True)
    except op.Refused: out.append(False)
if "{source}" == "disk":
    p = store.ROOT / "runs/{rid}/run.yaml"
    for raw in ("created_at: 2026-10-07T01:00:00.001Z", "created_at: 2026-10-07T00:59:59Z", "created_at: 2026-10-07 02:00:00"):
        p.write_text(f"run_id: {rid}\\n" + raw + "\\n")
        try: op.render_log_bytes("runs/{rid}/audit.log", [], mk); out.append(True)
        except op.Refused: out.append(False)
print(json.dumps(out))
"""
    out = json.loads(U.py(root, code).stdout.strip().splitlines()[-1])
    expect = [ok for _, ok in RENDER_CASES] + [False] + ([True, False, False] if source == "disk" else [])
    assert out == expect, out
