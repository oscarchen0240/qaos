"""P1：系統狀態、維護模式、初次請求准入與 resume_states（最終規格第 4 章 §5、§6.5、§8.2；AC-07-80～89、94）。"""
import pathlib, shutil, yaml, pytest
from tests import p1_util as U

FAULT_EXIT = 86
MAINT = "locks/maintenance.yaml"
MARKER = "artifacts/requirements/_migration.yaml"

def state(root):
    root = pathlib.Path(root)
    if (root / MAINT).is_file(): return "S_maint"
    return "S_post" if (root / MARKER).is_file() else "S_pre"

def spec_args(v="1.0"):
    return ["spec", "import", U.FIXTURES / f"SPEC-AUTH-001-v{v}.md", "--spec-id", "SPEC-AUTH-001", "--version", v, "--product", "demo", "--area", "AUTH", "--by", "t"]

def resume(root, entry, args, op):
    return U.q(root, *args) if entry == "resend" else U.q(root, "operation", "resume", op)

def legacy_running_run(root) -> str:
    """在另一份已移轉的 root 以正式流程建立 run，再把 run.yaml 複製到目標 root，模擬舊程式留下的 RUNNING run。"""
    src = U.mkroot()
    r = U.q(src, "run", "new", "regression-generation", "--input", 'target_suites=["full_regression"]', "--input", "scope=all", "--input", "trigger=manual", "--by", "t", check=True)
    run_id = r.stdout.split()[0]
    dst = pathlib.Path(root) / "runs" / run_id; dst.mkdir(parents=True)
    shutil.copy(pathlib.Path(src) / "runs" / run_id / "run.yaml", dst / "run.yaml")
    return run_id

def test_80_full_flow_reaches_s_post():
    root = U.mkroot(migrated=False)
    assert state(root) == "S_pre"
    U.q(root, "maintenance", "start", "--by", "t", check=True); assert state(root) == "S_maint"
    U.q(root, "migrate", "--by", "t", check=True); assert (pathlib.Path(root) / MARKER).is_file()
    U.q(root, "maintenance", "end", "--by", "t", check=True); assert state(root) == "S_post"
    assert U.incomplete(root) == []

def test_81_82_maintenance_refuses_business_allows_readonly():
    root = U.mkroot(); U.import_auth_spec(root)
    run_id = legacy_running_run(root)
    U.q(root, "maintenance", "start", "--by", "t", "--new-request", check=True)
    for args in (spec_args("1.1"), ["tc-export", "AUTH"], ["run", "cancel", run_id, "--by", "t"]):
        r = U.q(root, *args); assert r.returncode != 0 and "維護中" in r.stderr, (args, r.stderr)
    for args in (["operation", "list"], ["trace", "SPEC-AUTH-001"], ["req-export", "SPEC-AUTH-001", "1.0", "--stdout"], ["tc-export", "AUTH", "--stdout"]):
        r = U.q(root, *args); assert "維護中" not in r.stderr and "鎖由其他" not in r.stderr and "不允許" not in r.stderr, (args, r.stderr)   # 唯讀：不受維護模式與鎖影響

def test_83_maintenance_end_refused_while_plan_incomplete():
    """有未完成的計畫時 maintenance end 被拒絕（rollback 計畫的部分在 P3 驗收）。"""
    root = U.mkroot(migrated=False)
    U.q(root, "maintenance", "start", "--by", "t", check=True)
    assert U.q(root, "migrate", "--by", "t", fault="after_register").returncode == FAULT_EXIT
    r = U.q(root, "maintenance", "end", "--by", "t"); assert r.returncode != 0 and "未完成的計畫" in r.stderr

def test_84_migrate_refused_in_s_pre():
    root = U.mkroot(migrated=False)
    r = U.q(root, "migrate", "--by", "t"); assert r.returncode != 0 and "maintenance start" in r.stderr

@pytest.mark.parametrize("entry", ["resend", "resume"])
def test_85_86_run_cancel_in_s_pre(entry):
    root = U.mkroot(migrated=False); run_id = legacy_running_run(root)
    args = ["run", "cancel", run_id, "--by", "t"]
    assert U.q(root, *args, fault="after_output:1").returncode == FAULT_EXIT
    op = U.incomplete(root)[0]["op_id"]
    r = U.q(root, "maintenance", "start", "--by", "t"); assert r.returncode != 0 and "未完成的計畫" in r.stderr    # 86
    assert resume(root, entry, args, op).returncode == 0                                                      # 85
    assert U.load(root, f"runs/{run_id}/run.yaml")["status"] == "CANCELLED"
    assert not (pathlib.Path(root) / f"runs/{run_id}/audit.log").exists()     # 移轉前只寫事件、不 render
    U.q(root, "maintenance", "start", "--by", "t", check=True)

def test_87_business_plan_cannot_resume_in_maintenance():
    """防禦性：以故障注入造出「S_maint 中有未完成的業務計畫」，續做被 V4 拒絕（業務計畫的 resume_states 只有 S_post）。"""
    root = U.mkroot()
    assert U.q(root, *spec_args(), fault="after_register").returncode == FAULT_EXIT
    op = U.incomplete(root)[0]["op_id"]
    (pathlib.Path(root) / MAINT).write_text(yaml.safe_dump({"op_id": "x" * 64, "started_at": "t"}))   # 故障注入
    r = U.q(root, "operation", "resume", op); assert r.returncode != 0 and "resume_states" in r.stderr

@pytest.mark.parametrize("start_state", ["S_pre", "S_post"])
@pytest.mark.parametrize("point", ["after_register", "after_output:1"])
@pytest.mark.parametrize("entry", ["resend", "resume"])
def test_88_maintenance_start_abort(start_state, point, entry):
    """FP-S1（after_register）、FP-S2（after_output:1，維護檔已建立）。"""
    root = U.mkroot(migrated=start_state == "S_post")
    args = ["maintenance", "start", "--by", "t"] + (["--new-request"] if False else [])
    if start_state == "S_post": args = ["maintenance", "start", "--by", "t2"]   # 和 mkroot 的請求不同（不同 op）
    assert U.q(root, *args, fault=point).returncode == FAULT_EXIT
    op = U.incomplete(root)[0]["op_id"]
    m_sha = U.sha(pathlib.Path(root) / MAINT)
    for other in (["maintenance", "end", "--by", "other"], ["migrate", "--by", "other"], spec_args()):
        r = U.q(root, *other); assert r.returncode != 0 and ("未完成的計畫" in r.stderr), (other, r.stderr)
    assert resume(root, entry, args, op).returncode == 0
    assert state(root) == "S_maint" and U.incomplete(root) == []
    if m_sha: assert U.sha(pathlib.Path(root) / MAINT) == m_sha      # FP-S2：維護檔不重寫
    assert yaml.safe_load((pathlib.Path(root) / MAINT).read_text())["op_id"] == op

@pytest.mark.parametrize("migrated", [True, False])
@pytest.mark.parametrize("point", ["after_register", "after_output:1"])
@pytest.mark.parametrize("entry", ["resend", "resume"])
def test_89_maintenance_end_abort(migrated, point, entry):
    """FP-E1（after_register，維護檔還在）、FP-E2（after_output:1，維護檔已刪除；分別回到 S_post、S_pre）。"""
    root = U.mkroot(migrated=migrated)
    U.q(root, "maintenance", "start", "--by", "t3", check=True)
    args = ["maintenance", "end", "--by", "t3"]
    assert U.q(root, *args, fault=point).returncode == FAULT_EXIT
    op = U.incomplete(root)[0]["op_id"]
    for other in (["maintenance", "start", "--by", "t4"], spec_args()):
        r = U.q(root, *other); assert r.returncode != 0 and "未完成的計畫" in r.stderr
    assert resume(root, entry, args, op).returncode == 0       # FP-E2：在 S_pre／S_post 中續做 end，不被初次請求白名單拒絕
    assert state(root) == ("S_post" if migrated else "S_pre") and U.incomplete(root) == []

def test_94_identity_mismatch_is_refused():
    """防禦性：維護檔或移轉標記的 op_id 屬於其他 op → 續做被身分核對拒絕，不覆寫該檔。"""
    root = U.mkroot(migrated=False)
    assert U.q(root, "maintenance", "start", "--by", "t", fault="after_output:1").returncode == FAULT_EXIT
    op = U.incomplete(root)[0]["op_id"]
    m = pathlib.Path(root) / MAINT; d = yaml.safe_load(m.read_text()); d["op_id"] = "e" * 64; m.write_text(yaml.safe_dump(d))
    before = U.sha(m)
    r = U.q(root, "operation", "resume", op); assert r.returncode != 0 and "身分不符" in r.stderr
    assert U.sha(m) == before
    # 移轉標記屬於其他 op
    root2 = U.mkroot(migrated=False); U.q(root2, "maintenance", "start", "--by", "t", check=True)
    assert U.q(root2, "migrate", "--by", "t", fault="before_completed").returncode == FAULT_EXIT
    op2 = U.incomplete(root2)[0]["op_id"]
    mk = pathlib.Path(root2) / MARKER; d = yaml.safe_load(mk.read_text()); d["migrate_op_id"] = "d" * 64; mk.write_text(yaml.safe_dump(d))
    r = U.q(root2, "operation", "resume", op2); assert r.returncode != 0 and "身分不符" in r.stderr

def test_whitelist_table():
    """§6.5 初次請求白名單：S_pre 只允許 maintenance start 與 run cancel；S_maint 不允許業務寫入；S_post 不允許 migrate。"""
    root = U.mkroot(migrated=False)
    r = U.q(root, *spec_args()); assert r.returncode != 0 and "尚未移轉" in r.stderr
    r = U.q(root, "maintenance", "end", "--by", "t"); assert r.returncode != 0 and "不在維護中" in r.stderr
    r = U.q(root, "audit", "render"); assert r.returncode != 0 and "尚未移轉" in r.stderr     # AC-07-46
    root2 = U.mkroot()
    r = U.q(root2, "migrate", "--by", "x"); assert r.returncode != 0 and "必須先進入維護" in r.stderr
    U.q(root2, "maintenance", "start", "--by", "x", check=True)
    r = U.q(root2, "maintenance", "start", "--by", "y"); assert r.returncode != 0 and "已在維護中" in r.stderr
    r = U.q(root2, "migrate", "--by", "y"); assert r.returncode != 0 and "已移轉" in r.stderr
