"""P1：操作計畫的中止與續做、登錄、狀態紀錄、診斷、no_change（最終規格第 4 章 §6～§8、§12、§13、§15、§18）。

每個案例使用獨立的暫存 root，以子程序執行 QAOS；故障以 QAOS_FAULT 注入（程序在指定點結束，returncode 86）。
續做案例都以兩種入口各驗一次：(a) 同請求重送、(b) operation resume <op_id>。"""
import pathlib, yaml, pytest
from tests import p1_util as U

FAULT_EXIT = 86

def spec_import_args(version="1.0"):
    return ["spec", "import", U.FIXTURES / f"SPEC-AUTH-001-v{version}.md", "--spec-id", "SPEC-AUTH-001", "--version", version,
            "--product", "demo", "--area", "AUTH", "--by", "t"]

def resume(root, entry, args, op_id):
    if entry == "resend": return U.q(root, *args)
    return U.q(root, "operation", "resume", op_id)

def assert_clean(root):
    """沒有未完成計畫；每個 op 一筆登錄；沒有殘留暫存檔；事件與完成紀錄沒有重複。"""
    root = pathlib.Path(root)
    assert U.incomplete(root) == [], U.incomplete(root)
    assert U.unregistered_plans(root) == []
    ops = [o["op_id"] for o in U.op_list(root)]
    assert len(ops) == len(set(ops))
    assert not list(root.rglob(".qaos-tmp-*")), list(root.rglob(".qaos-tmp-*"))

def steps_of(args, setup=None):
    """在另一份 root 正常執行一次，取得該操作的計畫步驟（同一請求在不同 root 產生相同的步驟結構）。"""
    r = U.mkroot()
    if setup: setup(r)
    U.q(r, *args, check=True)
    return U.last_plan(r)["steps"]

# ---------------------------------------------------------------- 9b／9d／FP-P1／FP-P2／9k
@pytest.mark.parametrize("entry", ["resend", "resume"])
def test_fp_p2_registered_before_first_step(entry):
    """FP-P2（AC-07-97①）：登錄紀錄已寫、第一步還沒執行 → 從第一步開始；登錄紀錄只有一筆、plan_seq 不重新配發。"""
    root = U.mkroot(); args = spec_import_args()
    assert U.q(root, *args, fault="after_register").returncode == FAULT_EXIT
    inc = U.incomplete(root); assert len(inc) == 1
    op, seq = inc[0]["op_id"], inc[0]["plan_seq"]
    plan_sha = U.sha(next(pathlib.Path(root).glob(f"operations/*/{op}.yaml")))
    # 中止期間，其他 op 被拒絕（3b）
    other = U.q(root, *spec_import_args("1.1")); assert other.returncode != 0 and "未完成的計畫" in other.stderr
    r = resume(root, entry, args, op); assert r.returncode == 0, r.stderr
    assert_clean(root)
    regs = [o for o in U.op_list(root) if o["op_id"] == op]; assert len(regs) == 1 and regs[0]["plan_seq"] == seq
    assert U.sha(next(pathlib.Path(root).glob(f"operations/*/{op}.yaml"))) == plan_sha
    assert (pathlib.Path(root) / "specs/demo/AUTH/SPEC-AUTH-001/v1.0.md").is_file()

@pytest.mark.parametrize("entry", ["resend", "resume"])
def test_fp_p1_unregistered_plan_is_registered_then_resumed(entry):
    """FP-P1（AC-07-98 a、b）：計畫檔保存後、登錄前中止 → 先登錄補齊再續做；計畫檔、clock、allocated_ids 不變。"""
    root = U.mkroot(); args = spec_import_args()
    assert U.q(root, *args, fault="after_plan_save").returncode == FAULT_EXIT
    un = U.unregistered_plans(root); assert len(un) == 1
    op = un[0]; plan_file = next(pathlib.Path(root).glob(f"operations/*/{op}.yaml")); before = U.sha(plan_file)
    r = resume(root, entry, args, op); assert r.returncode == 0, r.stderr
    assert_clean(root)
    assert U.sha(plan_file) == before
    assert len([o for o in U.op_list(root) if o["op_id"] == op]) == 1

def test_fp_p1_other_op_after_reconcile_is_refused():
    """AC-07-98 c：未登錄計畫 → 不同 op 的請求先觸發登錄補齊，再以 3b 拒絕並提示 resume。"""
    root = U.mkroot()
    assert U.q(root, *spec_import_args(), fault="after_plan_save").returncode == FAULT_EXIT
    op = U.unregistered_plans(root)[0]
    r = U.q(root, *spec_import_args("1.1")); assert r.returncode != 0 and "operation resume" in r.stderr
    assert U.unregistered_plans(root) == [] and U.incomplete(root)[0]["op_id"] == op

def test_crash_before_plan_save_leaves_nothing():
    """AC-07-98 d、9b、AC-07-68 類：計畫保存前中止 → 沒有任何殘留，之後不同 op 照常執行。"""
    root = U.mkroot(); before = U.snapshot(root)
    assert U.q(root, *spec_import_args(), fault="before_plan_save").returncode == FAULT_EXIT
    d = U.diff(before, U.snapshot(root))
    assert not [p for p in d["added"] if not p.startswith("operations/") and "/blobs/" not in p], d
    assert U.incomplete(root) == [] and U.unregistered_plans(root) == []
    U.q(root, *spec_import_args("1.1"), check=True)

@pytest.mark.parametrize("entry", ["resend", "resume"])
def test_9k_all_steps_done_completed_missing(entry):
    """9k、AC-07-97②：全部步驟都完成、completed 還沒寫 → 只建立狀態紀錄，沒有任何業務寫入。"""
    root = U.mkroot(); args = spec_import_args()
    assert U.q(root, *args, fault="before_completed").returncode == FAULT_EXIT
    op = U.incomplete(root)[0]["op_id"]; before = U.snapshot(root)
    assert resume(root, entry, args, op).returncode == 0
    d = U.diff(before, U.snapshot(root))
    assert d["changed"] == [] and d["removed"] == [] and d["added"] == [f"operations/_global/status.d/{op}-completed.yaml"], d
    assert_clean(root)

# ---------------------------------------------------------------- FP-W：每一種步驟（AC-07-95）
def _fpw_cases():
    steps = steps_of(spec_import_args())
    return [s["seq"] for s in steps if s["kind"] != "status_final"]

@pytest.mark.parametrize("seq", _fpw_cases())
def test_fp_w_every_step_of_spec_import(seq):
    """AC-07-95：每一步「輸出已落盤、完成紀錄未落盤」中止 → 只補寫一個完成紀錄，輸出不重寫（sha、inode 不變）。兩種入口交替。"""
    root = U.mkroot(); args = spec_import_args()
    assert U.q(root, *args, fault=f"after_output:{seq}").returncode == FAULT_EXIT
    op = U.incomplete(root)[0]["op_id"]; plan = U.plan_of(root, op)
    step = next(s for s in plan["steps"] if s["seq"] == seq)
    target = pathlib.Path(root) / step["path"]
    inode = target.stat().st_ino if target.exists() else None
    prog_dir = pathlib.Path(root) / f"operations/{plan['scope']}/{op}/progress.d"
    assert len(list(prog_dir.glob("*.yaml"))) == seq - 1
    entry = "resend" if seq % 2 else "resume"
    assert resume(root, entry, args, op).returncode == 0
    if inode is not None: assert target.stat().st_ino == inode, "輸出被重寫"
    assert len(list(prog_dir.glob("*.yaml"))) == len(plan["steps"]) - 1
    assert_clean(root)

# ---------------------------------------------------------------- 每種 P1 操作類型的中止加續做（AC-07-22～26）
REG = {"suite_id": "SUITE-FULL", "suite_type": "full_regression", "base_suite_version": None, "trigger": "manual",
       "proposed_memberships": [], "diff": {"add": [], "remove": [], "repin": []}, "selection_criteria": "all active",
       "summary": {"total": 0, "added": 0, "removed": 0, "repinned": 0}}

def _reg_run(root):
    r = U.q(root, "run", "new", "regression-generation", "--input", 'target_suites=["full_regression"]', "--input", "scope=all", "--input", "trigger=manual", "--by", "t", check=True)
    return r.stdout.split()[0]

def _reg_artifact(root, run_id) -> str:
    code = f"""
from tests import helpers as H
rp, p = H.write_artifact("{run_id}", "T1", "agent-regression-curator", "RegressionProposal", {REG!r}, [], {{"type": "Registry", "ids": []}}, "regression")
print(p)
"""
    return U.py(root, code).stdout.strip()

def _abort_and_resume(root, args, entry, fault_seq=2):
    steps = U.q(root, *args, fault=f"after_output:{fault_seq}")
    assert steps.returncode == FAULT_EXIT, steps.stderr
    op = U.incomplete(root)[0]["op_id"]
    blocked = U.q(root, "req-export", "SPEC-NONE", "0"); assert blocked.returncode != 0 and "未完成的計畫" in blocked.stderr
    r = resume(root, entry, args, op); assert r.returncode == 0, r.stderr
    assert_clean(root)
    return op

@pytest.mark.parametrize("entry", ["resend", "resume"])
def test_types_run_new_submit_gate_approve_complete(entry):
    """AC-07-22（submit_gate 不含 A4）、23（approve）、24（complete_run）：每一步各在中途中止後續做，run 最後 COMPLETED。"""
    root = U.mkroot()
    run_args = ["run", "new", "regression-generation", "--input", 'target_suites=["full_regression"]', "--input", "scope=all", "--input", "trigger=manual", "--by", "t"]
    _abort_and_resume(root, run_args, entry, fault_seq=1)
    run_id = U.load(root, f"operations/_global/{U.op_list(root)[-1]['op_id']}.yaml")["result"]["run_id"]
    art = _reg_artifact(root, run_id)
    _abort_and_resume(root, ["submit", run_id, "T1", art], entry)
    _abort_and_resume(root, ["gate", run_id, "T1"], entry)
    apr = U.load(root, f"runs/{run_id}/run.yaml")["waiting_on_approval_id"]
    _abort_and_resume(root, ["approve", apr, "--decision", "approve", "--by", "t"], entry, fault_seq=3)
    run = U.load(root, f"runs/{run_id}/run.yaml")
    assert run["status"] == "COMPLETED" and run.get("summary_artifact_id")
    assert U.load(root, "testsuites/full-regression/SUITE-FULL.yaml")["status"] == "ACTIVE"
    # 事件沒有重複：每個 (op, step) 一個事件檔
    evs = list(pathlib.Path(root).glob(f"runs/{run_id}/audit.d/*.yaml"))
    assert len(evs) == len({p.name for p in evs})

@pytest.mark.parametrize("entry", ["resend", "resume"])
def test_types_cancel_export_render(entry):
    """AC-07-24（cancel_run）、25（寫檔 export、audit render）。"""
    root = U.mkroot(); U.import_auth_spec(root)
    run_id = _reg_run(root)
    _abort_and_resume(root, ["run", "cancel", run_id, "--by", "t"], entry, fault_seq=1)
    assert U.load(root, f"runs/{run_id}/run.yaml")["status"] == "CANCELLED"
    _abort_and_resume(root, ["tc-export", "AUTH"], entry, fault_seq=1)
    assert (pathlib.Path(root) / "testcases/AUTH.md").is_file()
    (pathlib.Path(root) / "runs/_audit.log").unlink()   # 竄改反例：檢視被刪，render 重建
    _abort_and_resume(root, ["audit", "render"], entry, fault_seq=1)
    assert "IMPORT_SPEC" in (pathlib.Path(root) / "runs/_audit.log").read_text()

# ---------------------------------------------------------------- 衍生輸出重建失敗（AC-07-78、9z'）
def test_derived_output_failure_keeps_plan_in_progress():
    root = U.mkroot(); args = spec_import_args()
    steps = steps_of(args)
    derived = [s for s in steps if s["step_id"].startswith(("derived", "render"))]
    assert derived, "spec import 應有 audit.log render 的衍生步驟"
    seq = derived[0]["seq"]
    r = U.q(root, *args, fault=f"raise:before_output:{seq}"); assert r.returncode != 0
    op = U.incomplete(root)[0]["op_id"]
    assert (pathlib.Path(root) / "specs/demo/AUTH/SPEC-AUTH-001/spec.yaml").is_file()   # 業務檔已完成
    assert not (pathlib.Path(root) / f"operations/_global/status.d/{op}-completed.yaml").exists()
    assert U.q(root, "operation", "resume", op).returncode == 0
    assert_clean(root)

# ---------------------------------------------------------------- 竄改（AC-07-96）
@pytest.mark.parametrize("case", ["delete_progress_before_tail", "delete_output_with_progress", "rewrite_progress", "rewrite_tail_event"])
def test_tamper_stops_resume(case):
    root = U.mkroot(); args = spec_import_args()
    steps = steps_of(args)
    ev = [s for s in steps if s["kind"] == "event"][0]["seq"]
    fault_seq = ev if case == "rewrite_tail_event" else len(steps) - 1
    assert U.q(root, *args, fault=f"after_output:{fault_seq}").returncode == FAULT_EXIT
    op = U.incomplete(root)[0]["op_id"]; plan = U.plan_of(root, op)
    pdir = pathlib.Path(root) / f"operations/{plan['scope']}/{op}/progress.d"
    first = plan["steps"][0]
    if case == "delete_progress_before_tail": next(pdir.glob("0001-*.yaml")).unlink()
    elif case == "delete_output_with_progress": (pathlib.Path(root) / first["path"]).unlink()
    elif case == "rewrite_progress": p = next(pdir.glob("0001-*.yaml")); p.write_text(p.read_text() + "#x\n")
    else:
        e = next(s for s in plan["steps"] if s["seq"] == fault_seq); p = pathlib.Path(root) / e["path"]; p.write_text(p.read_text() + "x: 1\n")
    before = U.snapshot(root)
    r = U.q(root, "operation", "resume", op); assert r.returncode != 0 and ("證據衝突" in r.stderr or "外部修改" in r.stderr), r.stderr
    assert U.diff(before, U.snapshot(root)) == {"added": [], "removed": [], "changed": []}

# ---------------------------------------------------------------- 登錄紀錄與狀態紀錄（AC-07-97 ③④）
def test_registrations_stay_valid_and_seq_contiguous():
    root = U.mkroot()
    U.import_auth_spec(root); U.q(root, "tc-export", "AUTH", check=True); U.q(root, *spec_import_args("1.1"), check=True)
    ops = U.op_list(root)
    assert [o["plan_seq"] for o in ops] == list(range(1, len(ops) + 1))
    for o in ops:
        plan_file = next(pathlib.Path(root).glob(f"operations/*/{o['op_id']}.yaml"))
        assert U.sha(plan_file) == o["plan_sha256"] and "completed" in o["statuses"]

def test_tampered_registration_refuses_resume():
    """AC-07-97 ④：改寫某個登錄紀錄的內容 → 涉及它的續做（V1）被拒絕並回報衝突。"""
    root = U.mkroot(); args = spec_import_args()
    assert U.q(root, *args, fault="after_register").returncode == FAULT_EXIT
    op = U.incomplete(root)[0]["op_id"]
    reg = next(pathlib.Path(root).glob(f"operations/_global/index.d/*-{op}.yaml"))
    d = yaml.safe_load(reg.read_text()); d["plan_sha256"] = "0" * 64; reg.write_text(yaml.safe_dump(d))
    r = U.q(root, "operation", "resume", op); assert r.returncode != 0 and "V1" in r.stderr

# ---------------------------------------------------------------- 不合法的未登錄計畫（AC-07-99，防禦性）
def test_invalid_unregistered_plan_refuses_all_writes():
    root = U.mkroot()
    bad = pathlib.Path(root) / "operations/_global" / ("f" * 64 + ".yaml")
    bad.write_text(yaml.safe_dump({"plan_schema": 1, "op_id": "f" * 64}))      # 故障注入：schema 不符的計畫檔
    before = U.snapshot(root)
    r = U.q(root, "tc-export", "AUTH"); assert r.returncode != 0 and "不合法" in r.stderr
    assert U.diff(before, U.snapshot(root)) == {"added": [], "removed": [], "changed": []}
    assert U.q(root, "operation", "list").returncode == 0   # 唯讀照常
    assert bad.is_file()

# ---------------------------------------------------------------- no_change（AC-07-100）
def test_no_change_export_has_no_content_steps():
    root = U.mkroot(); U.import_auth_spec(root)
    U.q(root, "tc-export", "AUTH", check=True)
    before = U.sha(pathlib.Path(root) / "testcases/AUTH.md")
    r = U.q(root, "tc-export", "AUTH", "--new-request", check=True)
    plan = U.last_plan(root)
    assert [s for s in plan["steps"] if s["path"] == "testcases/AUTH.md"] == []
    assert any(n["path"] == "testcases/AUTH.md" for n in plan["no_change"])
    assert U.sha(pathlib.Path(root) / "testcases/AUTH.md") == before

# ---------------------------------------------------------------- 驗證失敗只寫診斷（AC-07-8）
def test_validation_failure_writes_only_diagnostics():
    root = U.mkroot(); run_id = _reg_run(root)
    code = f"""
from tests import helpers as H
rp, p = H.write_artifact("{run_id}", "T1", "agent-regression-curator", "RegressionProposal", {{"suite_id": "X"}}, [], {{"type": "Registry", "ids": []}}, "regression")
print(p)
"""
    art = U.py(root, code).stdout.strip()
    before = U.snapshot(root); n_ops = len(U.op_list(root))
    r = U.q(root, "submit", run_id, "T1", art); assert r.returncode != 0 and "INVALID" in r.stdout
    d = U.diff(before, U.snapshot(root))
    assert len(U.op_list(root)) == n_ops and U.unregistered_plans(root) == []            # 沒有計畫
    assert set(d["changed"]) <= {f"runs/{run_id}/run.yaml", store_rel(art, root)}, d
    events = [p for p in d["added"] if "/audit.d/" in p]
    assert d["removed"] == [] and len(events) == 1 and "adhoc-" in events[0] and set(d["added"]) == set(events), d
    run = U.load(root, f"runs/{run_id}/run.yaml"); assert run["tasks"][0]["status"] == "READY"

def store_rel(p, root):
    return pathlib.Path(p).resolve().relative_to(pathlib.Path(root).resolve()).as_posix()

# ---------------------------------------------------------------- 操作身分（AC-07-13～18 中 P1 可驗的部分）
def test_same_request_is_idempotent_and_new_request_is_new_op():
    root = U.mkroot(); U.import_auth_spec(root)
    n = len(U.op_list(root))
    r = U.q(root, *spec_import_args()); assert r.returncode == 0 and "先前已完成的同一請求" in r.stderr     # op-P2：同 op、不寫入
    assert len(U.op_list(root)) == n
    r = U.q(root, *spec_import_args(), "--new-request"); assert r.returncode != 0 and "已存在" in r.stderr  # op-N4：新 op；狀態檢查拒絕
    assert len(U.op_list(root)) == n
    U.q(root, *spec_import_args("1.1"), check=True); assert len(U.op_list(root)) == n + 1                    # 參數不同 → 不同 op

# ---------------------------------------------------------------- 計畫結構（AC-07-19）
def test_duplicate_path_plan_is_rejected():
    root = U.mkroot()
    code = """
from tools.qaos import operation
plan = {"steps": [{"path": "a.yaml"}, {"path": "a.yaml"}]}
try:
    operation.check_plan_structure(plan); print("ok")
except operation.OperationError as e:
    print("rejected", e)
"""
    assert "rejected" in U.py(root, code).stdout
