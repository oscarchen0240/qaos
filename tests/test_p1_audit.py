"""P1：audit 事件檔、audit.log render、移轉凍結 legacy（最終規格第 4 章 §10；AC-07-36～49）。

legacy 資料（舊程式留下的 audit.log、run）以「在另一份 root 以正式流程產生、再複製」或直接寫入舊格式內容的方式建立，
模擬新程式部署前就存在的資料；這是 legacy fixture，不是對 QAOS 業務狀態的手改。"""
import pathlib, shutil, yaml, pytest
from tests import p1_util as U
from tests.test_p1_maintenance import legacy_running_run

FAULT_EXIT = 86

def spec_args(v="1.0"):
    return ["spec", "import", U.FIXTURES / f"SPEC-AUTH-001-v{v}.md", "--spec-id", "SPEC-AUTH-001", "--version", v, "--product", "demo", "--area", "AUTH", "--by", "t"]

def legacy_root():
    """S_pre 的 root，含一個 RUNNING 的 legacy run，以及舊格式的 run log 與全域 log。"""
    root = U.mkroot(migrated=False); run_id = legacy_running_run(root)
    run_log = pathlib.Path(root) / f"runs/{run_id}/audit.log"
    run_log.write_text("2026-09-01T00:00:00Z\toscar\tCREATE_WORKFLOW_RUN\tregression-generation\n", encoding="utf-8")
    glob_log = pathlib.Path(root) / "runs/_audit.log"
    glob_log.write_text(f"{run_id}\t2026-09-01T00:00:00Z\toscar\tCREATE_WORKFLOW_RUN\tregression-generation\n-\t2099-01-01T00:00:00Z\toscar\tFUTURE_LINE\tlegacy 最後一行的時間晚於之後的事件\n", encoding="utf-8")
    return root, run_id, run_log.read_bytes(), glob_log.read_bytes()

def migrate(root, *extra):
    U.q(root, "maintenance", "start", "--by", "m", check=True)
    U.q(root, "migrate", "--by", "m", *extra, check=True)
    U.q(root, "maintenance", "end", "--by", "m", check=True)

def test_43_45_49_legacy_freeze_and_first_render():
    root, run_id, run_legacy, glob_legacy = legacy_root()
    U.q(root, "run", "cancel", run_id, "--by", "t", check=True)          # S_pre：只寫事件、不 render
    assert (pathlib.Path(root) / f"runs/{run_id}/audit.log").read_bytes() == run_legacy
    assert (pathlib.Path(root) / "runs/_audit.log").read_bytes() == glob_legacy
    U.q(root, "maintenance", "start", "--by", "m", check=True)
    # AC-07-45：凍結之後、標記之前中止 → 重送 → 凍結略過、legacy 沒有被覆寫
    assert U.q(root, "migrate", "--by", "m", fault="after_output:1").returncode == FAULT_EXIT
    U.q(root, "migrate", "--by", "m", check=True)
    U.q(root, "maintenance", "end", "--by", "m", check=True)
    assert (pathlib.Path(root) / f"runs/{run_id}/audit.legacy.log").read_bytes() == run_legacy    # AC-07-41／43
    assert (pathlib.Path(root) / "runs/_audit.legacy.log").read_bytes() == glob_legacy
    run_log = (pathlib.Path(root) / f"runs/{run_id}/audit.log").read_bytes()
    assert run_log.startswith(run_legacy) and b"CANCEL_RUN" in run_log[len(run_legacy):]
    g = (pathlib.Path(root) / "runs/_audit.log").read_bytes()
    assert g.startswith(glob_legacy)                                   # AC-07-49：legacy 照抄在前，不交錯
    tail = g[len(glob_legacy):].decode()
    assert "CANCEL_RUN" in tail and "MIGRATE" in tail and "FUTURE_LINE" not in tail
    mk = U.load(root, "artifacts/requirements/_migration.yaml")
    assert mk["logs"][f"runs/{run_id}/audit.log"]["legacy"] == "frozen" and mk["logs"]["runs/_audit.log"]["legacy"] == "frozen"

def test_migrate_requires_running_run_choice():
    """RUNNING 的 run 必須逐一指定處理方式；沒有指定 → 拒絕、不寫任何檔案（--cancel-run 在 P3）。"""
    root, run_id, _, _ = legacy_root()
    U.q(root, "maintenance", "start", "--by", "m", check=True)
    before = U.snapshot(root)
    r = U.q(root, "migrate", "--by", "m"); assert r.returncode != 0 and run_id in r.stderr
    assert U.diff(before, U.snapshot(root)) == {"added": [], "removed": [], "changed": []}
    U.q(root, "migrate", "--by", "m", "--acknowledge-idle", run_id, check=True)
    assert U.load(root, "artifacts/requirements/_migration.yaml")["mode_per_run"] == {run_id: "acknowledge_idle"}

def test_47_frozen_legacy_deleted_render_refused():
    root, run_id, _, _ = legacy_root()
    migrate(root, "--acknowledge-idle", run_id)
    (pathlib.Path(root) / f"runs/{run_id}/audit.legacy.log").unlink()          # 竄改反例
    r = U.q(root, "audit", "render", run_id); assert r.returncode != 0 and "legacy" in r.stderr

def test_48_new_run_after_migration_uses_events_only():
    root = U.mkroot()
    r = U.q(root, "run", "new", "regression-generation", "--input", 'target_suites=["full_regression"]', "--input", "scope=all", "--input", "trigger=manual", "--by", "t", check=True)
    run_id = r.stdout.split()[0]
    log = (pathlib.Path(root) / f"runs/{run_id}/audit.log").read_text()
    assert log.splitlines()[0].split("\t")[2] == "CREATE_WORKFLOW_RUN"
    assert not (pathlib.Path(root) / f"runs/{run_id}/audit.legacy.log").exists()

@pytest.mark.parametrize("entry", ["resend", "resume"])
def test_40_42_render_abort_formal_sequence(entry):
    root = U.mkroot(); U.import_auth_spec(root)
    glog = pathlib.Path(root) / "runs/_audit.log"; prev = glog.read_bytes()
    args = ["audit", "render"]
    # 先讓檢視落後一個事件：以新請求再 render 一次前，刪掉檢視（竄改反例），確保 render 有內容步驟
    glog.unlink()
    assert U.q(root, *args, fault="before_output:1").returncode == FAULT_EXIT      # 原子替換之前中止
    assert not glog.exists()                                                       # AC-07-42：沒有半寫內容
    op = U.incomplete(root)[0]["op_id"]; planned = U.plan_of(root, op)
    r = U.q(root, *spec_args("1.1")); assert r.returncode != 0 and "未完成的計畫" in r.stderr   # B 被 3b 拒絕
    assert (U.q(root, *args) if entry == "resend" else U.q(root, "operation", "resume", op)).returncode == 0
    assert glog.read_bytes() == prev                                               # A 依固定輸入完成，不納入之後的事件
    U.q(root, *spec_args("1.1"), check=True)                                       # B 正式寫入事件
    U.q(root, *args, "--new-request", check=True)                                  # render C
    assert glog.read_text().count("IMPORT_SPEC") == 2

def test_36_37_38_other_ops_files_untouched():
    """防禦性：以故障注入放入「另一個 op」的事件檔與暫存檔，本操作續做時不碰它們（正式流程中不會發生）。"""
    root = U.mkroot(); args = spec_args()
    plan_steps = None
    # 36：A 在寫入事件檔之前中止
    assert U.q(root, *args, fault="after_output:1").returncode == FAULT_EXIT
    op = U.incomplete(root)[0]["op_id"]; plan = U.plan_of(root, op)
    ev = next(s for s in plan["steps"] if s["kind"] == "event")
    ev_dir = (pathlib.Path(root) / ev["path"]).parent; ev_dir.mkdir(parents=True, exist_ok=True)
    b_event = ev_dir / ("b" * 64 + "-1.yaml"); b_event.write_text(yaml.safe_dump({"op_id": "b" * 64, "step": 1, "at": "x", "actor": "b", "action": "B", "detail": "", "run_id": None}))
    b_tmp = ev_dir / f".qaos-tmp-{'b' * 16}-x.yaml-0000"; b_tmp.write_text("partial")    # 38：B 寫到一半
    b_sha, t_sha = U.sha(b_event), U.sha(b_tmp)
    assert U.q(root, "operation", "resume", op).returncode == 0
    assert (pathlib.Path(root) / ev["path"]).is_file()                              # A 建立自己的事件
    assert U.sha(b_event) == b_sha and U.sha(b_tmp) == t_sha                        # B 的檔不受影響
    # 37：A 的事件已完整建立後中止，再放入 B 的事件 → 略過、可完成
    root2 = U.mkroot()
    assert U.q(root2, *args, fault=f"after_output:{ev['seq']}").returncode == FAULT_EXIT
    op2 = U.incomplete(root2)[0]["op_id"]
    b2 = (pathlib.Path(root2) / ev["path"]).parent / ("c" * 64 + "-1.yaml"); b2.write_text("c: 1\n")
    assert U.q(root2, "operation", "resume", op2).returncode == 0 and b2.read_text() == "c: 1\n"

def test_39_event_target_with_different_content_stops():
    root = U.mkroot(); args = spec_args()
    assert U.q(root, *args, fault="after_output:1").returncode == FAULT_EXIT
    op = U.incomplete(root)[0]["op_id"]; plan = U.plan_of(root, op)
    ev = next(s for s in plan["steps"] if s["kind"] == "event")
    p = pathlib.Path(root) / ev["path"]; p.parent.mkdir(parents=True, exist_ok=True); p.write_text("tampered: true\n")
    r = U.q(root, "operation", "resume", op); assert r.returncode != 0 and ("證據衝突" in r.stderr or "內容不同" in r.stderr)
    assert p.read_text() == "tampered: true\n"

def test_9r_first_render_abort_keeps_original_audit_log():
    """9r：移轉的第一次 render 在原子替換之前中止 → audit.log 仍是移轉前的原內容；續做後才是 legacy＋事件。"""
    root, run_id, run_legacy, glob_legacy = legacy_root()
    U.q(root, "maintenance", "start", "--by", "m", check=True)
    ref, rid2, _, _ = legacy_root(); U.q(ref, "maintenance", "start", "--by", "m", check=True)
    U.q(ref, "migrate", "--by", "m", "--acknowledge-idle", rid2, check=True)
    render = [s for s in U.last_plan(ref)["steps"] if s["path"] == "runs/_audit.log"][0]
    args = ["migrate", "--by", "m", "--acknowledge-idle", run_id]
    assert U.q(root, *args, fault=f"before_replace:{render['seq']}").returncode == FAULT_EXIT
    assert (pathlib.Path(root) / "runs/_audit.log").read_bytes() == glob_legacy
    U.q(root, *args, check=True)
    assert (pathlib.Path(root) / "runs/_audit.log").read_bytes().startswith(glob_legacy)
