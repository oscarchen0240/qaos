"""P3：migrate、migrate verify、migrate rollback（需求 A 第 5 章 §10～§14；AC-09-4～6、13、26、42～46、55～63、65、70～91 中可在獨立 root 驗收的部分）。

legacy 資料由需求 A 之前的程式（base 2e01d4b）以它自己的正式流程產生（tests/p3_legacy.py）；之後全部以新程式的正式指令操作。
標明「竄改」或「故障注入」的子例，才在流程後故意修改檔案；「模擬經授權的人工修復」也另外標示。"""
import pathlib, shutil, tempfile, yaml, pytest
from tests import p1_util as U, p3_legacy as L

_TEMPLATE = {}

def legacy():
    """複製一份 legacy 範本 root（範本只產生一次）。回傳 (root, 摘要)。"""
    if not _TEMPLATE:
        root, info = L.legacy_root(); _TEMPLATE.update(root=root, info=info)
    dst = pathlib.Path(tempfile.mkdtemp(prefix="qaos-p3-")) / "root"
    shutil.copytree(_TEMPLATE["root"], dst)
    return dst, dict(_TEMPLATE["info"])

def x_of(root): return U.load(root, "artifacts/requirements/_migration.yaml")["migrate_op_id"]
def ok(r): assert r.returncode == 0, r.stdout + r.stderr; return r
def status_files(root, op): return sorted(p.name[len(op) + 1:-5] for p in (pathlib.Path(root) / "operations/_global/status.d").glob(f"{op}-*.yaml"))
def plans(root): return sorted(p.stem for p in pathlib.Path(root).glob("operations/*/*.yaml"))
NOTHING = {"added": [], "removed": [], "changed": []}

def migrated(cancel=False):
    root, info = legacy(); mode = "--cancel-run" if cancel else "--acknowledge-idle"
    L.migrate(root, mode, info["running"], check=True)
    return root, info

# ---------------------------------------------------------------- 准入與 RUNNING run 的處理方式
def test_ac_09_6_42_46_running_run_needs_a_mode():
    root, info = legacy(); ok(U.q(root, "maintenance", "start", "--by", "m"))
    before = U.snapshot(root); n = len(plans(root))
    for args, msg in (([], "逐一指定"), (["--acknowledge-idle", info["done"]], "不是 RUNNING"),
                      (["--acknowledge-idle", info["running"], "--cancel-run", info["running"]], "同時")):
        r = U.q(root, "migrate", "--by", "m", *args); assert r.returncode != 0 and msg in r.stderr, (args, r.stderr)
    assert U.diff(before, U.snapshot(root)) == NOTHING and len(plans(root)) == n          # 連計畫都不寫
    ok(U.q(root, "migrate", "--by", "m", "--acknowledge-idle", info["running"]))

def test_ac_09_65_rollback_requires_maintenance():
    root, info = migrated(); x = x_of(root); ok(U.q(root, "maintenance", "end", "--by", "m"))
    r = U.q(root, "migrate", "rollback", "--op", x, "--by", "m"); assert r.returncode != 0 and "維護" in r.stderr

def test_ac_09_91_declarations_before_migration_refuse():
    """防禦性（故障注入）：移轉前就有宣告，分 (a) references 非空、(b) 只有宣告歷史；兩例都拒絕、不寫任何檔案。"""
    for variant in ("references", "history"):
        root, info = legacy()
        p = pathlib.Path(root) / "specs/demo/AUTH/SPEC-AUTH-001/spec.yaml"; spec = yaml.safe_load(p.read_text())
        v = spec["versions"][0]
        if variant == "references": v["references"] = [{"spec_id": "SPEC-AUTH-001", "spec_version": "1.0", "content_hash": v["content_hash"], "role": "informative"}]
        else: v["reference_declarations"] = [{"decl_rev": 1, "action": "declare_empty", "references": [], "references_status": "declared_empty", "reason": "x", "by": "o", "at": "2026-09-01T00:00:00Z", "op_id": "0" * 64}]
        p.write_text(yaml.safe_dump(spec, allow_unicode=True, sort_keys=False))
        ok(U.q(root, "maintenance", "start", "--by", "m")); before = U.snapshot(root)
        r = U.q(root, "migrate", "--by", "m", "--acknowledge-idle", info["running"]); assert r.returncode != 0 and "引用宣告" in r.stderr
        assert U.diff(before, U.snapshot(root)) == NOTHING

# ---------------------------------------------------------------- 移轉的結果（AC-09-4、13、43、88；verify）
def test_migrate_acknowledge_idle_results():
    root, info = legacy(); r_ = pathlib.Path(root)
    view = r_ / "artifacts/requirements/SPEC-AUTH-001/v1.0/requirements.yaml"; view_bytes = view.read_bytes()
    runs_before = {p.parent.name: p.read_bytes() for p in r_.glob("runs/*/run.yaml")}
    tcs_before = {p: p.read_bytes() for p in r_.glob("testcases/versions/*/v*.yaml")}
    logs_before = {p: p.read_bytes() for p in r_.glob("runs/**/audit.log")}
    L.migrate(root, "--acknowledge-idle", info["running"], check=True)
    ok(U.q(root, "migrate", "verify"))
    rev = r_ / "artifacts/requirements/SPEC-AUTH-001/v1.0/revisions"
    assert (rev / "R000.yaml").read_bytes() == view_bytes and view.read_bytes() == view_bytes                     # AC-09-4、88
    meta = yaml.safe_load((rev / "R000.meta.yaml").read_text())
    assert meta == {"revision": "R000", "legacy": True, "revision_sha256": U.sha(rev / "R000.yaml"), "target_decl_rev": 0, "reference_pins": [], "created_by_op": x_of(root)}
    assert {p.parent.name: p.read_bytes() for p in r_.glob("runs/*/run.yaml")} == runs_before                     # acknowledge-idle：run.yaml 不變
    assert {p: p.read_bytes() for p in r_.glob("testcases/versions/*/v*.yaml")} == tcs_before
    for rid in (info["done"], info["running"]):
        sc = U.load(root, f"artifacts/requirements/_bindings/{rid}.yaml")
        assert sc["requirement_model_revision"]["revision"] == "R000" and sc["legacy_binding"] is False
    for tc in info["tcs"]:
        sc = U.load(root, f"testcases/_bindings/{tc}-v1.yaml")                                                   # AC-09-13
        assert sc["requirement_model_revision"]["revision"] == "R000" and sc["legacy_binding"] is True
    c = U.load(root, f"clarifications/demo/AUTH/{info['clr']}.yaml"); r0 = c["answer_revisions"][0]
    import hashlib
    assert r0["sha256"] == hashlib.sha256("密碼下限 8 碼。".encode()).hexdigest() and r0["rev"] == 0
    assert r0["basis_hash"] == U.py(root, f"from tools.qaos import sources\nprint(sources.chash({r0['basis']!r}))").stdout.strip()
    assert r0["basis"] == {"target": {"spec_id": "SPEC-AUTH-001", "spec_version": "1.0", "content_hash": U.load(root, "specs/demo/AUTH/SPEC-AUTH-001/spec.yaml")["versions"][0]["content_hash"]},
                           "target_decl_rev": 0, "closure": []}
    assert "answer_revisions" not in U.load(root, f"clarifications/demo/AUTH/{info['open_clr']}.yaml")
    for p, b in logs_before.items(): assert p.read_bytes().startswith(b) and (p.parent / "audit.legacy.log").read_bytes() == b   # 凍結＋第一次 render
    mk = U.load(root, "artifacts/requirements/_migration.yaml")
    assert mk["mode_per_run"] == {info["running"]: "acknowledge_idle"} and mk["manifest_sha256"] == U.sha(r_ / f"operations/_global/{x_of(root)}/manifest.yaml")

def test_ac_09_44_cancel_run_in_same_operation():
    root, info = migrated(cancel=True)
    run = U.load(root, f"runs/{info['running']}/run.yaml"); assert run["status"] == "CANCELLED"
    log = (pathlib.Path(root) / f"runs/{info['running']}/audit.log").read_text(); assert "CANCEL_RUN" in log and "migrate --cancel-run" in log
    assert U.load(root, f"artifacts/requirements/_bindings/{info['running']}.yaml")["requirement_model_revision"]["revision"] == "R000"
    ok(U.q(root, "migrate", "verify"))

def test_ac_09_88_legacy_r000_skip_rule_and_89_declaration():
    """移轉後：legacy R000、未宣告、全部 ACTIVE → _skip 跳過並記警告；宣告之後 → declaration_changed，不跳過。"""
    root, info = migrated(); ok(U.q(root, "maintenance", "end", "--by", "m"))
    rid = ok(U.q(root, "run", "new", "spec-to-testcase", "--input", "spec_id=SPEC-AUTH-001", "--input", "spec_version=1.0", "--by", "o")).stdout.split()[0]
    assert U.load(root, f"runs/{rid}/run.yaml")["requirement_model_revision"]["revision"] == "R000"
    assert "WARN_LEGACY_SKIP" in (pathlib.Path(root) / f"runs/{rid}/audit.log").read_text()
    ok(U.q(root, "spec", "reference", "declare-empty", "SPEC-AUTH-001@1.0", "--reason", "x", "--by", "o"))
    rid2 = ok(U.q(root, "run", "new", "spec-to-testcase", "--input", "spec_id=SPEC-AUTH-001", "--input", "spec_version=1.0", "--by", "o", "--new-request")).stdout.split()[0]
    assert U.load(root, f"runs/{rid2}/run.yaml")["current_task_id"] == "T1"
    assert (pathlib.Path(root) / "artifacts/requirements/SPEC-AUTH-001/v1.0/revisions/R000.meta.yaml").read_text().count("target_decl_rev: 0") == 1   # meta 不改寫

def test_old_running_run_resumes_on_its_sidecar_revision():
    """移轉前就在跑的 run（T2 READY）移轉後繼續：引用解析與 G-DESIGN 讀 sidecar 的 R000，不讀最新 revision；新 TC 版本綁 R000。
    P3 審查 P3-04：先以另一個新 run 重新分析產生內容不同的 R001（拿掉 REQ-AUTH-004），舊 run 仍要能引用 REQ-AUTH-004。"""
    root, info = migrated(); ok(U.q(root, "maintenance", "end", "--by", "m")); rid = info["running"]
    ok(U.q(root, "spec", "reference", "declare-empty", "SPEC-AUTH-001@1.0", "--reason", "x", "--by", "o"))
    U.py(root, "from tests import p3_flow as F\nr = F.new_run(); F.analyze(r, drop=('REQ-AUTH-004',))")
    r001 = U.load(root, "artifacts/requirements/SPEC-AUTH-001/v1.0/revisions/R001.yaml")
    assert "REQ-AUTH-004" not in {q["requirement_id"] for q in r001["requirements"]}                                  # 最新 revision 已沒有它
    code = f"""
import json
from tools.qaos import engine, store
from tests import helpers as H
tcs, _ = H.draft_set(prefix="01CX5ZZKBKACTAV9WEVGEMMVR")
rmid = store.load("artifacts/requirements/SPEC-AUTH-001/v1.0/requirements.yaml")["source_artifact_id"]
refs_ = [{{"entity_type": "Requirement", "id": r}} for r in ["REQ-AUTH-001", "REQ-AUTH-002", "REQ-AUTH-003", "REQ-AUTH-004"]]
did, pd = H.write_artifact("{rid}", "T2", "agent-test-designer", "TestCaseDraft", {{"mode": "spec", "spec_id": "SPEC-AUTH-001", "spec_version": "1.0", "testcases": tcs}}, refs_, {{"type": "RequirementModel", "ids": [rmid]}}, "test-design")
_, pr = H.write_artifact("{rid}", "T2", "agent-test-designer", "TestDesignReport", H.design_report(did, tcs), [{{"entity_type": "Artifact", "id": did}}], {{"type": "TestCaseDraft", "ids": [did]}}, "test-design")
assert engine.submit("{rid}", "T2", str(pd))[0] and engine.submit("{rid}", "T2", str(pr))[0]
g = engine.evaluate_gate("{rid}", "T2")
_, pv = H.write_artifact("{rid}", "T3", "agent-test-validator", "TestValidationReport", H.validation_report(did, rmid, "PASS"), [{{"entity_type": "Artifact", "id": did}}, {{"entity_type": "Artifact", "id": rmid}}], {{"type": "TestCaseDraft", "ids": [did]}}, "validation")
assert engine.submit("{rid}", "T3", str(pv))[0] and engine.evaluate_gate("{rid}", "T3")["result"] == "PASS"
print(json.dumps(g["result"]))"""
    assert U.py(root, code).stdout.strip().splitlines()[-1] == '"PASS"'
    newest = max(pathlib.Path(root).glob("testcases/versions/*/v1.yaml"), key=lambda p: p.parent.name)
    assert yaml.safe_load(newest.read_text())["requirement_model_revision"]["revision"] == "R000"

# ---------------------------------------------------------------- rollback：完整回復（AC-09-55、56、68）
@pytest.mark.parametrize("cancel", [False, True])
def test_ac_09_55_56_rollback_after_completed_migration(cancel):
    root, info = legacy(); before = U.snapshot(root)
    L.migrate(root, "--cancel-run" if cancel else "--acknowledge-idle", info["running"], check=True); x = x_of(root)
    r = ok(U.q(root, "migrate", "rollback", "--op", x, "--by", "m"))
    ok(U.q(root, "migrate", "verify", "--rolled-back"))
    d = U.diff(before, U.snapshot(root))
    assert d["changed"] == [] and d["removed"] == []                                                                  # restore 回到 pre、remove 不存在
    assert all(p.startswith(("operations/", "runs/_audit.d/", "runs/RUN-", "locks/")) for p in d["added"]), d["added"]
    assert not [p for p in d["added"] if p.startswith("runs/RUN-") and "/audit.d/" not in p]                         # run 內只留下事件（cancel 事件屬 retain_audit）
    assert status_files(root, x) == ["completed", "rolled_back"]
    assert U.load(root, f"runs/{info['running']}/run.yaml")["status"] == "RUNNING"
    ok(U.q(root, "maintenance", "end", "--by", "m"))                                                                   # 回到 S_pre
    assert not (pathlib.Path(root) / "artifacts/requirements/_migration.yaml").exists()

# ---------------------------------------------------------------- rollback：部分移轉（AC-09-57、71、72、75、78a）
@pytest.mark.parametrize("fault,label", [("after_register", "FP-M0"), ("after_progress:3", "FP-M1"), ("after_progress:6", "FP-M2"), ("after_output:6", "FP-W")])
def test_rollback_after_partial_migration(fault, label):
    root, info = legacy(); before = U.snapshot(root)
    r = L.migrate(root, "--acknowledge-idle", info["running"], check=False, fault=fault); assert r.returncode == 86, (label, r.stderr)
    x = U.incomplete(root)[0]["op_id"]
    ok(U.q(root, "migrate", "rollback", "--op", x, "--by", "m"))
    ok(U.q(root, "migrate", "verify", "--rolled-back"))
    d = U.diff(before, U.snapshot(root)); assert d["changed"] == [] and d["removed"] == [], (label, d)
    assert status_files(root, x) == ["aborted_for_rollback"]
    rplan = next(U.plan_of(root, o) for o in plans(root) if U.plan_of(root, o) and U.plan_of(root, o)["action"] == "migrate_rollback")
    xp = rplan["x_progress"]; assert xp["x_status_at_creation"] == "in_progress"
    if label == "FP-M0": assert all(s["status"] == "not_executed" for s in xp["steps"]) and [s["group"] for s in rplan["steps"]] == ["takeover", "takeover", "restore", "terminal"]
    if label == "FP-W": assert xp["tail_step"] == 6 and next(s for s in xp["steps"] if s["seq"] == 6)["proof"] == "content_tail"
    r = U.q(root, "migrate", "--by", "m", "--acknowledge-idle", info["running"]); assert r.returncode != 0 and "已終結" in r.stderr   # AC-09-57：同 op 重送 X 被拒
    r = U.q(root, "operation", "resume", x); assert r.returncode != 0

def test_ac_09_26_x_resumes_after_partial_migration():
    root, info = legacy()
    assert L.migrate(root, "--acknowledge-idle", info["running"], check=False, fault="after_progress:6").returncode == 86
    r = U.q(root, "run", "new", "regression-generation", "--input", 'target_suites=["full_regression"]', "--input", "scope=all", "--input", "trigger=manual", "--by", "o")
    assert r.returncode != 0                                                                                          # 標記寫入之前，業務寫入一直被拒絕
    ok(U.q(root, "migrate", "--by", "m", "--acknowledge-idle", info["running"]))                                      # 同請求重送續做
    ok(U.q(root, "migrate", "verify"))

# ---------------------------------------------------------------- T5、T7（AC-09-59、73、82）
def test_ac_09_59_82_t7_refuses_unrecoverable_path_until_repaired():
    root, info = migrated(); x = x_of(root)
    clr = pathlib.Path(root) / f"clarifications/demo/AUTH/{info['clr']}.yaml"; post = clr.read_bytes()
    clr.write_bytes(post + b"# tampered\n")                                                                         # 竄改：既不是 pre 也不是 post
    before = U.snapshot(root); n = len(plans(root))
    for _ in range(2):                                                                                                # 相同請求重送仍被拒（沒有計畫可續做）
        r = U.q(root, "migrate", "rollback", "--op", x, "--by", "m"); assert r.returncode != 0 and "T7" in r.stderr and info["clr"] in r.stderr
    assert U.diff(before, U.snapshot(root)) == NOTHING and len(plans(root)) == n and status_files(root, x) == ["completed"]
    clr.write_bytes(post)                                                                                             # 模擬經授權的人工修復：恢復成移轉後的內容
    ok(U.q(root, "migrate", "rollback", "--op", x, "--by", "m")); ok(U.q(root, "migrate", "verify", "--rolled-back"))

@pytest.mark.parametrize("what", ["untouched", "remove_path", "audit_log"])
def test_ac_09_82_t7_other_categories(what):
    """竄改：untouched 路徑、remove 路徑；audit.log 改成「不是依目前事件重新 render」的內容（附錄 A 5-13 只接受正常的 render）。"""
    root, info = migrated(); x = x_of(root)
    p = pathlib.Path(root) / {"untouched": "specs/demo/AUTH/SPEC-AUTH-001/spec.yaml", "remove_path": f"artifacts/requirements/_bindings/{info['done']}.yaml", "audit_log": "runs/_audit.log"}[what]
    p.write_bytes(p.read_bytes() + b"# tampered\n")
    r = U.q(root, "migrate", "rollback", "--op", x, "--by", "m"); assert r.returncode != 0 and "T7" in r.stderr and {"untouched": "untouched", "remove_path": "remove", "audit_log": "restore"}[what] in r.stderr
    assert status_files(root, x) == ["completed"] and (pathlib.Path(root) / "artifacts/requirements/_migration.yaml").exists()

def test_ac_09_73_t5_evidence_conflict():
    root, info = legacy()
    assert L.migrate(root, "--acknowledge-idle", info["running"], check=False, fault="after_progress:6").returncode == 86
    x = U.incomplete(root)[0]["op_id"]
    prog = sorted((pathlib.Path(root) / f"operations/_global/{x}/progress.d").glob("*.yaml"))[1]; prog.unlink()        # 竄改：刪掉尾端之前某一步的完成紀錄
    before = U.snapshot(root)
    r = U.q(root, "migrate", "rollback", "--op", x, "--by", "m"); assert r.returncode != 0 and "T5" in r.stderr
    assert U.diff(before, U.snapshot(root)) == NOTHING and status_files(root, x) == []

# ---------------------------------------------------------------- 後續操作（AC-09-60、61、70）
def _later_write(root, info, kind):
    ok(U.q(root, "maintenance", "end", "--by", "m"))
    if kind == "answer": ok(U.q(root, "clarification", "answer", info["clr"], "--answer", "改成 10 碼", "--answered-by", "pm", "--resolution", "requirement_clarified", "--by", "o"))
    else:
        f = pathlib.Path(root).parent / "z.md"; f.write_text("# Z\n", encoding="utf-8")
        ok(U.q(root, "spec", "import", f, "--spec-id", "SPEC-Z-001", "--version", "1.0", "--product", "demo", "--area", "ZONE", "--by", "o"))
    ok(U.q(root, "maintenance", "start", "--by", "m", "--new-request"))                                             # 第二次進入維護是新請求

def test_ac_09_60_61_later_ops():
    root, info = migrated(); x = x_of(root); _later_write(root, info, "answer")
    r = U.q(root, "migrate", "rollback", "--op", x, "--by", "m"); assert r.returncode != 0 and "T6" in r.stderr and "後續操作報告" in r.stderr and "clarification_answer" in r.stderr
    r = U.q(root, "migrate", "rollback", "--op", x, "--by", "m", "--allow-later-ops"); assert r.returncode != 0 and "T7" in r.stderr   # ①：改過清單內的 CLR
    assert status_files(root, x) == ["completed"]
    root, info = migrated(); x = x_of(root); _later_write(root, info, "spec")                                         # ②：只寫清單以外的路徑
    assert U.q(root, "migrate", "rollback", "--op", x, "--by", "m").returncode != 0
    ok(U.q(root, "migrate", "rollback", "--op", x, "--by", "m", "--allow-later-ops")); ok(U.q(root, "migrate", "verify", "--rolled-back"))
    assert (pathlib.Path(root) / "specs/demo/ZONE/SPEC-Z-001/spec.yaml").exists()                                     # 後續操作新增的檔案保留

# ---------------------------------------------------------------- R 的中止與續做（AC-09-58、79、81、84、85）
def _r_plan(root):
    return next(U.plan_of(root, o) for o in plans(root) if (U.plan_of(root, o) or {}).get("action") == "migrate_rollback")

POINTS = ["R_saved", "takeover_tail", "restore_mid", "check_a_passed", "marker_tail", "before_check_b", "rt1_tail"]

def _prog(root, plan, st):
    return (pathlib.Path(root) / f"operations/_global/{plan['op_id']}/progress.d/{st['seq']:04d}-{st['step_id']}.yaml").exists()

def _out_after(root, st):
    p = pathlib.Path(root) / st["path"]
    return (not p.exists()) if st["expected_after"] is None else (p.exists() and U.sha(p) == st["expected_after"])

@pytest.mark.parametrize("point", POINTS)
@pytest.mark.parametrize("entry", ["resend", "resume"])
def test_rollback_abort_points_then_resume(point, entry):
    """R 的各中止點（FP-R0～R5、FP-W）：依不可變的 R 計畫找出各群組的步驟，先斷言中止時各群組的實際狀態，再以兩種入口續做完成。"""
    root, info = migrated(); x = x_of(root); args = ["migrate", "rollback", "--op", x, "--by", "m"]
    assert U.q(root, *args, fault="after_register").returncode == 86                                                 # FP-R0：R 已建立，第一步還沒執行
    rp = _r_plan(root); rid = rp["op_id"]; G = {g: [st for st in rp["steps"] if st.get("group") == g] for g in ("takeover", "restore", "marker", "terminal")}
    rt1 = G["terminal"][0]; marker = G["marker"][0]; restore = G["restore"]
    assert rt1["step_id"] == "Rt1" and marker["path"].endswith("_migration.yaml") and len(restore) >= 3
    fault = {"R_saved": None, "takeover_tail": f"after_output:{G['takeover'][0]['seq']}", "restore_mid": f"after_progress:{restore[1]['seq']}",
             "check_a_passed": "after_check_a", "marker_tail": f"after_output:{marker['seq']}", "before_check_b": "before_check_b", "rt1_tail": f"after_output:{rt1['seq']}"}[point]
    if fault: assert U.q(root, "operation", "resume", rid, fault=fault).returncode == 86
    done = lambda st: _out_after(root, st) and _prog(root, rp, st)
    if point == "R_saved": assert not any(_out_after(root, st) for st in G["takeover"]) and (pathlib.Path(root) / marker["path"]).exists()
    if point == "takeover_tail": assert _out_after(root, G["takeover"][0]) and not _prog(root, rp, G["takeover"][0])
    if point == "restore_mid": assert done(restore[0]) and done(restore[1]) and not _out_after(root, restore[2])
    if point in ("check_a_passed", "marker_tail", "before_check_b", "rt1_tail"): assert all(done(st) for st in G["takeover"] + restore)
    if point == "check_a_passed": assert (pathlib.Path(root) / marker["path"]).exists() and not _prog(root, rp, marker)
    if point == "marker_tail": assert not (pathlib.Path(root) / marker["path"]).exists() and not _prog(root, rp, marker)
    if point in ("before_check_b", "rt1_tail"): assert done(marker)
    if point == "rt1_tail": assert _out_after(root, rt1) and not _prog(root, rp, rt1)
    if point != "rt1_tail": assert not (pathlib.Path(root) / rt1["path"]).exists()
    assert not (pathlib.Path(root) / G["terminal"][-1]["path"]).exists()                                             # Rt2 都還沒寫
    assert U.q(root, "maintenance", "end", "--by", "m").returncode != 0                                               # R 未完成：維護窗口持續
    assert U.q(root, "operation", "resume", x).returncode != 0                                                        # X 已被 R 接管
    ok(U.q(root, *args) if entry == "resend" else U.q(root, "operation", "resume", rid))
    ok(U.q(root, "migrate", "verify", "--rolled-back"))
    assert status_files(root, x) == ["completed", "rolled_back"] and status_files(root, rid) == ["completed"]

# ---------------------------------------------------------------- P3 審查 P3-01～03：X 的證據
def test_p3_01_completed_x_missing_last_progress_is_refused():
    for variant in ("last_progress", "completed_status"):
        root, info = migrated(); x = x_of(root); xp = U.plan_of(root, x)
        if variant == "last_progress":                                                                               # 竄改：只刪 X 最後一個非最終步驟的完成紀錄
            last = xp["steps"][-2]; (pathlib.Path(root) / f"operations/_global/{x}/progress.d/{last['seq']:04d}-{last['step_id']}.yaml").unlink()
        else:
            f = pathlib.Path(root) / f"operations/_global/status.d/{x}-completed.yaml"; f.write_text(f.read_text() + "x: 1\n")
        before = U.snapshot(root); n = len(plans(root))
        r = U.q(root, "migrate", "rollback", "--op", x, "--by", "m")
        assert r.returncode != 0 and ("T5" if variant == "last_progress" else "completed 狀態紀錄內容不符") in r.stderr, (variant, r.stderr)   # completed 紀錄竄改在 T2 的登錄核對就被拒
        assert U.diff(before, U.snapshot(root)) == NOTHING and len(plans(root)) == n

@pytest.mark.parametrize("entry", ["resend", "resume"])
def test_p3_02_frozen_x_progress_deleted_stops_checks(entry):
    root, info = migrated(); x = x_of(root); args = ["migrate", "rollback", "--op", x, "--by", "m"]
    assert U.q(root, *args, fault="after_register").returncode == 86
    rid = _r_plan(root)["op_id"]; xp = U.plan_of(root, x)
    (pathlib.Path(root) / f"operations/_global/{x}/progress.d/0001-{xp['steps'][0]['step_id']}.yaml").unlink()          # 竄改：刪掉 R 已凍結為 proof=progress 的 X 完成紀錄
    r = U.q(root, *args) if entry == "resend" else U.q(root, "operation", "resume", rid)
    assert r.returncode != 0 and "檢查 A" in r.stderr and "完成紀錄" in r.stderr, r.stderr
    assert status_files(root, rid) == [] and status_files(root, x) == ["completed"] and (pathlib.Path(root) / "artifacts/requirements/_migration.yaml").exists()

def test_p3_03_verify_detects_missing_or_tampered_evidence():
    root, info = migrated(); x = x_of(root); xp = U.plan_of(root, x)
    f = pathlib.Path(root) / f"operations/_global/{x}/progress.d/0001-{xp['steps'][0]['step_id']}.yaml"; data = f.read_bytes(); f.unlink()   # 竄改
    r = U.q(root, "migrate", "verify"); assert r.returncode != 0 and "0001-manifest" in r.stdout, r.stdout
    f.write_bytes(data); ok(U.q(root, "migrate", "verify"))
    ok(U.q(root, "migrate", "rollback", "--op", x, "--by", "m")); rp = _r_plan(root)
    ev = next(st for st in rp["steps"] if st["kind"] == "event"); p = pathlib.Path(root) / ev["path"]; p.write_bytes(p.read_bytes() + b"# tampered\n")
    r = U.q(root, "migrate", "verify", "--rolled-back"); assert r.returncode != 0 and ev["path"] in r.stdout, r.stdout
    p.write_bytes(p.read_bytes()[:-len(b"# tampered\n")]); ok(U.q(root, "migrate", "verify", "--rolled-back"))
    xprog = pathlib.Path(root) / f"operations/_global/{x}/progress.d/0001-{xp['steps'][0]['step_id']}.yaml"; xprog.unlink()
    r = U.q(root, "migrate", "verify", "--rolled-back"); assert r.returncode != 0 and "0001-manifest" in r.stdout

def test_check_a_and_b_stop_on_external_change_then_repair():
    """FP-R4：③ 檢查 A 前改動 untouched 路徑 → 檢查 A 停止、標記保留；④ 標記刪除後改動 → 檢查 B 停止、沒有終態紀錄；恢復記錄值後續做完成。"""
    for fault, where in (("before_check_a", "檢查 A"), ("before_check_b", "檢查 B")):
        root, info = migrated(); x = x_of(root); args = ["migrate", "rollback", "--op", x, "--by", "m"]
        assert U.q(root, *args, fault=fault).returncode == 86
        rid = _r_plan(root)["op_id"]
        p = pathlib.Path(root) / "specs/demo/AUTH/SPEC-AUTH-001/spec.yaml"; orig = p.read_bytes(); p.write_bytes(orig + b"# external\n")   # 外部改動
        for cmd in (args, ["operation", "resume", rid]):
            r = U.q(root, *cmd); assert r.returncode != 0 and where in r.stderr, (where, r.stderr)
        assert status_files(root, rid) == [] and status_files(root, x) == ["completed"]
        assert (pathlib.Path(root) / "artifacts/requirements/_migration.yaml").exists() == (where == "檢查 A")
        assert U.q(root, "maintenance", "end", "--by", "m").returncode != 0
        p.write_bytes(orig)                                                                                           # 模擬經授權的人工修復：恢復成記錄值
        ok(U.q(root, "operation", "resume", rid)); ok(U.q(root, "migrate", "verify", "--rolled-back"))

def test_ac_09_85_terminal_inconsistency_blocks_all_writes():
    """防禦性（故障注入）：造出 Rt2 存在、Rt1 不存在的非法排列 → 所有寫入在第 0 步停止；唯讀指令照常、verify 失敗。"""
    root, info = migrated(); x = x_of(root)
    ok(U.q(root, "migrate", "rollback", "--op", x, "--by", "m"))
    (pathlib.Path(root) / f"operations/_global/status.d/{x}-rolled_back.yaml").unlink()
    before = U.snapshot(root)
    for cmd in (["maintenance", "end", "--by", "m"], ["migrate", "--by", "m", "--new-request", "--acknowledge-idle", info["running"]], ["operation", "resume", x]):
        r = U.q(root, *cmd); assert r.returncode != 0 and "終態不一致" in r.stderr, (cmd, r.stderr)
    assert U.diff(before, U.snapshot(root)) == NOTHING
    ok(U.q(root, "operation", "list"))
    r = U.q(root, "migrate", "verify", "--rolled-back"); assert r.returncode != 0 and "終態紀錄" in r.stdout

# ---------------------------------------------------------------- 重新移轉（AC-09-63、90）
def test_ac_09_63_90_remigrate_after_rollback():
    root, info = migrated(); x = x_of(root)
    meta1 = U.load(root, "artifacts/requirements/SPEC-AUTH-001/v1.0/revisions/R000.meta.yaml")
    rev0_1 = U.load(root, f"clarifications/demo/AUTH/{info['clr']}.yaml")["answer_revisions"][0]["basis"]
    ok(U.q(root, "migrate", "rollback", "--op", x, "--by", "m"))
    r = U.q(root, "migrate", "--by", "m", "--acknowledge-idle", info["running"]); assert r.returncode != 0 and "--new-request" in r.stderr   # ①
    assert U.q(root, "operation", "resume", x).returncode != 0                                                        # ②
    x_audit = {p: p.read_bytes() for p in (pathlib.Path(root) / "operations/_global").glob(f"{x}/**/*") if p.is_file()}
    ok(U.q(root, "migrate", "--by", "m", "--acknowledge-idle", info["running"], "--new-request"))                    # ③
    y = x_of(root); assert y != x
    ok(U.q(root, "migrate", "verify"))
    assert {p: p.read_bytes() for p in x_audit} == x_audit                                                            # X 的稽核物不變
    manifest_y = U.load(root, f"operations/_global/{y}/manifest.yaml")
    assert not [e for e in manifest_y["restore"] + manifest_y["remove"] if x in e["path"]]                            # Y 的清單不包含 X 的稽核物
    meta2 = U.load(root, "artifacts/requirements/SPEC-AUTH-001/v1.0/revisions/R000.meta.yaml")
    keys = ("revision", "legacy", "revision_sha256", "target_decl_rev", "reference_pins")
    assert {k: meta2[k] for k in keys} == {k: meta1[k] for k in keys} and meta2["created_by_op"] == y != meta1["created_by_op"]
    assert U.load(root, f"clarifications/demo/AUTH/{info['clr']}.yaml")["answer_revisions"][0]["basis"] == rev0_1

# ---------------------------------------------------------------- P3 審查 P3-05、P3-06
def test_p3_05_testcase_revision_target_comes_from_the_tc(tmp_path):
    root = U.mkroot(); U.import_auth_spec(root)
    U.py(root, "from tests import p3_flow as F\nF.full()")
    U.q(root, "spec", "import", U.FIXTURES / "SPEC-AUTH-001-v1.1.md", "--spec-id", "SPEC-AUTH-001", "--version", "1.1", "--product", "demo", "--area", "AUTH", "--by", "o", check=True)
    before = U.snapshot(root)
    for ver in ("1.1",):
        r = U.q(root, "run", "new", "testcase-revision", "--input", "testcase_id=TC-AUTH-001", "--input", "reason=x", "--input", "spec_id=SPEC-AUTH-001", "--input", f"spec_version={ver}", "--by", "o")
        assert r.returncode != 0 and "必須是 TC-AUTH-001" in r.stderr, r.stderr
    r = U.q(root, "run", "new", "testcase-revision", "--input", "testcase_id=TC-AUTH-999", "--input", "reason=x", "--input", "spec_id=SPEC-AUTH-001", "--input", "spec_version=1.0", "--by", "o")
    assert r.returncode != 0 and "找不到被修訂的 TC" in r.stderr
    assert U.diff(before, U.snapshot(root)) == NOTHING                                                                 # 不留下 run、計數器不前進
    ok(U.q(root, "run", "new", "testcase-revision", "--input", "testcase_id=TC-AUTH-001", "--input", "reason=x", "--input", "spec_id=SPEC-AUTH-001", "--input", "spec_version=1.0", "--by", "o"))

def test_p3_06_approval_render_direct_api_and_nested():
    root = U.mkroot(); U.import_auth_spec(root)
    apr = U.py(root, "from tests import p3_flow as F\nfrom tools.qaos import engine\nr = F.new_run(); m = F.analyze(r); F.design_and_validate(r, m); print(engine.load_run(r)['waiting_on_approval_id'])").stdout.strip().splitlines()[-1]
    md = pathlib.Path(root) / f"approvals/{apr}.md"; md.unlink(missing_ok=True)
    n = len(U.op_list(root))
    U.py(root, f"from tools.qaos import approval_render\napproval_render.render('{apr}', new_request=True)")                 # 直接 Python API：自己是一個操作
    assert md.exists() and len(U.op_list(root)) == n + 1 and U.op_list(root)[-1]["action"] == "approval_render"
    md.unlink()
    U.py(root, f"from tools.qaos import approval_render, operation\noperation.run_operation('test_internal', lambda: approval_render.render('{apr}'), new_request=True)")   # 巢狀：併入外層操作
    assert md.exists() and len(U.op_list(root)) == n + 2 and U.op_list(root)[-1]["action"] == "test_internal"
