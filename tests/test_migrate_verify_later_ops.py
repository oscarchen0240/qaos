"""`migrate verify` 在 X 之後的合法操作（需求 A 第 5 章 §12.1～§12.5；AC-09-92～95；附錄 A 5-17、5-18）。

legacy 資料沿用 P3 的範本（舊程式以正式流程產生）；之後全部以新程式的正式指令操作。
標明「竄改」的子例才在流程後故意修改檔案；「故障注入」「時鐘注入」只用測試專用的環境變數（QAOS_FAULT、QAOS_TEST_CLOCK）。"""
import pathlib, shutil, tempfile, uuid, yaml, pytest
from tests import p1_util as U, p3_legacy as L
from tests.test_p3_migrate import legacy, x_of, ok, plans

GLOBAL = "runs/_audit.log"

def verify(root): return U.q(root, "migrate", "verify")
def vok(root):
    r = verify(root); assert r.returncode == 0, r.stdout + r.stderr; return r
COUNTERS = "testcases/registry/_counters.yaml"
def vok_but(root, *untouched):
    """只剩 §12.5 的回報：後續業務操作改寫的 untouched 路徑（例如建立 run 配發 ID 改寫 _counters.yaml）；audit 檢視與事件檔都不被回報。"""
    r = verify(root); issues = [l[2:] for l in r.stdout.splitlines() if l.startswith("- ")]
    assert issues and all(any(i == f"untouched {u} 被改動" for u in untouched) for i in issues), r.stdout + r.stderr
    return r
def vfail(root, *needles):
    """失敗，而且每個關鍵字都出現在回報的問題行中（不含只供對照的附註）。"""
    r = verify(root); assert r.returncode != 0 and "verify 失敗" in r.stdout, r.stdout + r.stderr
    issues = "\n".join(l for l in r.stdout.splitlines() if l.startswith("- "))
    for n in needles: assert n in issues, (n, r.stdout)
    return r

def P(root, rel) -> pathlib.Path: return pathlib.Path(root) / rel
def clock(root, op): return U.plan_of(root, op)["clock"]
def blob(root, plan, step): return P(root, f"operations/{plan['scope']}/{plan['op_id']}/blobs/{step['blob']}").read_bytes()
def last_op(root, action): return [o for o in U.op_list(root) if o["action"] == action][-1]["op_id"]
def copy(root):
    dst = pathlib.Path(tempfile.mkdtemp(prefix="qaos-mv-")) / "root"; shutil.copytree(root, dst); return dst

def migrated(extra_env=None):
    root, info = legacy()
    U.q(root, "maintenance", "start", "--by", "m", check=True)
    U.q(root, "migrate", "--by", "m", "--acknowledge-idle", info["running"], check=True, extra_env=extra_env)
    return root, info

def spec_import(root, sid, extra_env=None, fault=None, check=True):
    f = pathlib.Path(root).parent / f"{sid}.md"; f.write_text(f"# {sid}\n", encoding="utf-8")
    return U.q(root, "spec", "import", f, "--spec-id", sid, "--version", "1.0", "--product", "demo", "--area", sid.split("-")[1],
               "--by", "o", check=check, extra_env=extra_env, fault=fault)

def new_run(root):
    r = U.q(root, "run", "new", "regression-generation", "--input", 'target_suites=["full_regression"]', "--input", "scope=all",
            "--input", "trigger=manual", "--by", "t", check=True)
    return r.stdout.split()[0]

def diagnose(root, run_id):
    """對新 run 提交不合格的產出 → 驗證失敗，只寫一個診斷事件（第 4 章 §13）。"""
    code = f"""
from tests import helpers as H
rp, p = H.write_artifact("{run_id}", "T1", "agent-regression-curator", "RegressionProposal", {{"suite_id": "X"}}, [], {{"type": "Registry", "ids": []}}, "regression")
print(p)
"""
    art = U.py(root, code).stdout.strip()
    before = set(pathlib.Path(root).glob(f"runs/{run_id}/audit.d/adhoc-*.yaml"))
    r = U.q(root, "submit", run_id, "T1", art); assert r.returncode != 0 and "INVALID" in r.stdout
    new = set(pathlib.Path(root).glob(f"runs/{run_id}/audit.d/adhoc-*.yaml")) - before; assert len(new) == 1
    return new.pop()

def diag_file(root, run_id=None, **over):
    """測試中直接寫入的診斷事件（格式由 over 調整；預設有效）。"""
    hexid = uuid.uuid4().hex
    ev = {"at": "2099-01-01T00:00:00Z", "actor": "t", "action": "GATE_FAIL", "detail": "d", "op_id": f"adhoc-{hexid}", "step": 0, "run_id": run_id}
    ev.update(over)
    d = P(root, f"runs/{run_id}/audit.d" if run_id else "runs/_audit.d"); d.mkdir(parents=True, exist_ok=True)
    p = d / f"adhoc-{over.pop('_name', hexid)}-0.yaml"
    ev.pop("_name", None)
    p.write_text(yaml.safe_dump(ev, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return p

_RICH = {}
def rich():
    """X（acknowledge-idle）→ maintenance end → 新建 run → 診斷事件 → spec import（render 全域 log，含診斷事件）。回傳獨立複本。"""
    if not _RICH:
        root, info = migrated(); ok(U.q(root, "maintenance", "end", "--by", "m"))
        rid = new_run(root); d = diagnose(root, rid); spec_import(root, "SPEC-ZA-001")
        _RICH.update(root=root, info=info, rid=rid, diag=d.relative_to(root).as_posix())
    return copy(_RICH["root"]), dict(_RICH)

# ---------------------------------------------------------------- AC-09-92：合法狀態通過
def test_ac_09_92_1_2_maintenance_end_and_business_op():
    root, info = migrated(); x = x_of(root)
    vok(root)
    ok(U.q(root, "maintenance", "end", "--by", "m"))
    r = vok(root)                                                                   # ①：部署 W2 的情境（舊程式回報 2 項失敗）
    assert "maintenance_end" in r.stdout and "X 之後的已完成操作" in r.stdout
    xs = next(s for s in U.plan_of(root, x)["steps"] if s["path"] == GLOBAL)
    assert P(root, GLOBAL).read_bytes().startswith(blob(root, U.plan_of(root, x), xs))   # 一般情況：以計畫值開頭
    spec_import(root, "SPEC-ZB-001"); vok(root)                                    # ②

def test_ac_09_92_3_7_diagnostic_and_new_run():
    root, info = migrated(); ok(U.q(root, "maintenance", "end", "--by", "m"))
    rid = new_run(root); vok_but(root, COUNTERS)                                    # ⑦：新 run 的 log 依 (c)
    d = diagnose(root, rid); ev = yaml.safe_load(d.read_text())
    line = f"{rid}\t{ev['at']}\t{ev['actor']}\t{ev['action']}\t{ev['detail']}\n"
    assert line not in P(root, GLOBAL).read_text(); vok_but(root, COUNTERS)        # ③ 診斷寫在最後一次 render 之後
    spec_import(root, "SPEC-ZC-001")
    assert line in P(root, GLOBAL).read_text(); vok_but(root, COUNTERS)            # ③ 診斷已被 render 進全域 log

def test_ac_09_92_4_render_without_events():
    root, _ = rich()
    ok(U.q(root, "audit", "render", "--global")); vok_but(root, COUNTERS)
    ok(U.q(root, "audit", "render", _RICH["rid"])); vok_but(root, COUNTERS)

def test_ac_09_92_5_same_second_and_earlier_clock():
    root, info = migrated(); x = x_of(root); xc = clock(root, x)
    ok(U.q(root, "maintenance", "end", "--by", "m", extra_env={"QAOS_TEST_CLOCK": xc}))
    sides = set()
    for i in range(80):                                                             # 同秒、op_id 大於與小於 X 各至少一例
        spec_import(root, f"SPEC-S{i:02d}-001", extra_env={"QAOS_TEST_CLOCK": xc})
        o = last_op(root, "spec_import"); sides.add(o < x)
        if sides == {True, False}: break
    assert sides == {True, False}
    t = P(root, GLOBAL).read_bytes(); xs = next(s for s in U.plan_of(root, x)["steps"] if s["path"] == GLOBAL)
    assert not t.startswith(blob(root, U.plan_of(root, x), xs))                    # 事件排進 X 時內容的中間
    vok(root)
    spec_import(root, "SPEC-EARLY-001", extra_env={"QAOS_TEST_CLOCK": "2001-01-01T00:00:00Z"}); vok(root)   # 早於 X
    rid = new_run(root); vok_but(root, COUNTERS)
    U.q(root, "run", "cancel", rid, "--by", "t", check=True, extra_env={"QAOS_TEST_CLOCK": "2001-01-01T00:00:01Z"}); vok_but(root, COUNTERS)   # run 檢視 (c)、早於 X
    # X 中 render 過的 run（acknowledge-idle 的 RUNNING run）：同秒的後續事件；只回報 untouched 的 run.yaml（§12.5），audit 檢視不被回報
    # run 檢視同秒、op_id 小於與大於 X 各至少一例：從同一狀態複製，以 --new-request 取得不同的 op_id
    sides = set()
    for _ in range(80):                                                             # op_id 是隨機的；X 的 op_id 偏向一端時需要多試幾次
        c = copy(root)
        U.q(c, "run", "cancel", info["running"], "--by", "t", "--new-request", check=True, extra_env={"QAOS_TEST_CLOCK": xc})
        o = last_op(c, "run_cancel"); assert clock(c, o) == xc
        if (o < x) in sides: shutil.rmtree(c.parent); continue
        vok_but(c, COUNTERS, f"runs/{info['running']}/run.yaml"); sides.add(o < x)
        if sides == {True, False}: break
    assert sides == {True, False}

def test_ac_09_92_6_rollback_then_remigrate():
    root, info = migrated(); x1 = x_of(root)
    ok(U.q(root, "migrate", "rollback", "--op", x1, "--by", "m")); ok(U.q(root, "migrate", "verify", "--rolled-back"))
    ok(U.q(root, "migrate", "--by", "m", "--acknowledge-idle", info["running"], "--new-request")); x2 = x_of(root); assert x2 != x1
    vok(root); ok(U.q(root, "maintenance", "end", "--by", "m")); spec_import(root, "SPEC-ZD-001"); vok(root)

def test_ac_09_92_8_9_diagnostic_edge_cases():
    root, _ = rich(); x = x_of(root); xc = clock(root, x)
    diag_file(root); vok_but(root, COUNTERS)                                                      # ⑧ 格式有效、非正式流程寫入 → 通過（§18 第 12 點）
    diag_file(root, _RICH["rid"], detail="第一行\n第二行", at="2099-01-02T00:00:00Z")
    ok(U.q(root, "audit", "render", "--global")); vok_but(root, COUNTERS)                        # ⑨ detail 含換行，只 render 全域
    diag_file(root, at=xc); vok_but(root, COUNTERS)                                               # ⑨ 與 X 同秒、寫在 X 之後（未 render）
    ok(U.q(root, "audit", "render", "--global", "--new-request")); vok_but(root, COUNTERS)
    # ⑨ 與 X 同秒、寫在 X 之前（X 第一次 render 已包含）
    root, info = legacy(); T = "2030-01-01T00:00:00Z"
    U.q(root, "maintenance", "start", "--by", "m", check=True)
    diag_file(root, at=T)
    U.q(root, "migrate", "--by", "m", "--acknowledge-idle", info["running"], check=True, extra_env={"QAOS_TEST_CLOCK": T})
    vok(root); ok(U.q(root, "maintenance", "end", "--by", "m")); vok(root)

# ---------------------------------------------------------------- AC-09-93：竄改失敗（每例使用獨立複本；還原後再次通過）
def tamper_case(fn, *needles):
    root, info = rich(); vok_but(root, COUNTERS)
    snap = {p: p.read_bytes() for p in pathlib.Path(root).rglob("*") if p.is_file()}             # 整個 root
    fn(root, info); vfail(root, *needles)
    for p in [p for p in pathlib.Path(root).rglob("*") if p.is_file()]:
        if p not in snap: p.unlink()
    for p, b in snap.items(): p.write_bytes(b)
    vok_but(root, COUNTERS)

def _edit(root, rel, f): p = P(root, rel); p.write_bytes(f(p.read_bytes()))
def _x_blob(root, view):
    x = x_of(root); xp = U.plan_of(root, x); return blob(root, xp, next(s for s in xp["steps"] if s["path"] == view))
def _end_op(root): return last_op(root, "maintenance_end")
def _end_event(root):
    o = _end_op(root); return next(s["path"] for s in U.plan_of(root, o)["steps"] if s["kind"] == "event")

@pytest.mark.parametrize("case", ["append", "head_byte", "drop_required", "swap", "dup"])
def test_ac_09_93_1_4_log_text(case):
    def fn(root, info):
        lines = P(root, GLOBAL).read_bytes().splitlines(keepends=True)
        if case == "append": lines.append(b"-\t2099-01-01T00:00:00Z\tx\tFORGED\t\n")
        elif case == "head_byte": lines[0] = (b"X" if lines[0][:1] != b"X" else b"Y") + lines[0][1:]
        elif case == "drop_required": lines = [l for l in lines if b"MAINTENANCE_END" not in l]
        elif case == "swap": lines[-1], lines[-2] = lines[-2], lines[-1]
        else: lines.append(lines[-1])
        P(root, GLOBAL).write_bytes(b"".join(lines))
    tamper_case(fn, f"audit 檢視 {GLOBAL}")

def test_ac_09_93_5_replace_with_x_content_global():
    tamper_case(lambda root, info: P(root, GLOBAL).write_bytes(_x_blob(root, GLOBAL)), f"audit 檢視 {GLOBAL}")

def test_ac_09_93_5_replace_with_x_content_run_view():
    root, info = migrated(); x = x_of(root); ok(U.q(root, "maintenance", "end", "--by", "m"))
    view = f"runs/{info['running']}/audit.log"; before = P(root, view).read_bytes()
    U.q(root, "run", "cancel", info["running"], "--by", "t", check=True)
    assert P(root, view).read_bytes() != before
    P(root, view).write_bytes(before)                                               # 竄改：換回 X 時的內容
    vfail(root, f"audit 檢視 {view}")

def test_ac_09_93_6_event_and_log_changed_together():
    def fn(root, info):
        ev = _end_event(root); _edit(root, ev, lambda b: b.replace(b"detail: ''", b"detail: x"))
        _edit(root, GLOBAL, lambda b: b.replace(b"\tMAINTENANCE_END\t\n", b"\tMAINTENANCE_END\tx\n"))
    tamper_case(fn, "maintenance_end", "缺失或不符")

def test_ac_09_93_7_unregistered_event():
    fake = lambda root: P(root, f"runs/_audit.d/{'f' * 64}-1.yaml")
    def only_file(root, info):
        fake(root).write_text(yaml.safe_dump({"at": "2099-01-01T00:00:00Z", "actor": "x", "action": "FORGED", "detail": "", "op_id": "f" * 64, "step": 1, "run_id": None}))
    tamper_case(only_file, "無法對應")
    def rendered(root, info):
        only_file(root, info); ok(U.q(root, "audit", "render", "--global")); assert b"FORGED" in P(root, GLOBAL).read_bytes()
    tamper_case(rendered, "無法對應", f"audit 檢視 {GLOBAL}")

def test_ac_09_93_8_deleted_events():
    def pre_x(root, info):
        o = last_op(root, "maintenance_start"); ev = next(s["path"] for s in U.plan_of(root, o)["steps"] if s["kind"] == "event"); P(root, ev).unlink()
    tamper_case(pre_x, "maintenance_start")
    tamper_case(lambda root, info: P(root, _end_event(root)).unlink(), "maintenance_end", "缺失或不符")

def test_ac_09_93_9_completed_removed():
    tamper_case(lambda root, info: P(root, f"operations/_global/status.d/{_end_op(root)}-completed.yaml").unlink(), "未完成的操作")

def test_ac_09_93_10_forged_completed_or_missing_progress():
    # (a) 故障注入：中止在事件步驟的完成紀錄之前；竄改：log 含它的事件、補上內容正確的 completed
    root, _ = rich()
    r = spec_import(root, "SPEC-ZF-001", fault="after_register", check=False); assert r.returncode == 86
    o = U.incomplete(root)[0]["op_id"]; plan = U.plan_of(root, o)
    ev_step = next(s for s in plan["steps"] if s["kind"] == "event")
    assert U.q(root, "operation", "resume", o, fault=f"after_output:{ev_step['seq']}").returncode == 86
    assert P(root, ev_step["path"]).exists() and not P(root, f"operations/_global/{o}/progress.d/{ev_step['seq']:04d}-{ev_step['step_id']}.yaml").exists()
    ev = plan["audit_events"][0]
    P(root, GLOBAL).write_bytes(P(root, GLOBAL).read_bytes() + f"-\t{ev['at']}\t{ev['actor']}\t{ev['action']}\t{ev['detail']}\n".encode())
    P(root, f"operations/_global/status.d/{o}-completed.yaml").write_text(yaml.safe_dump({"op_id": o, "status": "completed", "at": plan["clock"]}, sort_keys=False))
    vfail(root, f"{ev_step['seq']:04d}-{ev_step['step_id']}")
    # (b) 正式完成 maintenance end 後刪除／改動完成紀錄，並把全域 log 換回 X 的內容
    for mode in ("delete", "change"):
        root, info = migrated(); ok(U.q(root, "maintenance", "end", "--by", "m"))
        o = _end_op(root); pl = U.plan_of(root, o); s = pl["steps"][0]
        pp = P(root, f"operations/_global/{o}/progress.d/{s['seq']:04d}-{s['step_id']}.yaml")
        pp.unlink() if mode == "delete" else pp.write_bytes(pp.read_bytes() + b"# x\n")
        P(root, GLOBAL).write_bytes(_x_blob(root, GLOBAL))
        vfail(root, pp.relative_to(root).as_posix())

def test_ac_09_93_11_registration_changed():
    def fn(root, info):
        p = next(pathlib.Path(root).glob(f"operations/_global/index.d/*-{_end_op(root)}.yaml"))
        rec = yaml.safe_load(p.read_text()); rec["plan_sha256"] = "0" * 64; p.write_text(yaml.safe_dump(rec, sort_keys=False))
    tamper_case(fn, "plan_sha256")

@pytest.mark.parametrize("variant", ["extra_field", "step1", "step_false", "wrong_run", "name_mismatch", "bad_at", "detail_int"])
def test_ac_09_93_12_invalid_diagnostic(variant):
    def fn(root, info):
        over = {"extra_field": {"extra": 1}, "step1": {"step": 1}, "step_false": {"step": False}, "wrong_run": {},
                "name_mismatch": {"_name": uuid.uuid4().hex}, "bad_at": {"at": "2099-13-45T00:00:00Z"}, "detail_int": {"detail": 3}}[variant]
        f = diag_file(root, None, **over)
        if variant == "wrong_run":                                                   # 全域目錄中的事件帶 run_id
            ev = yaml.safe_load(f.read_text()); ev["run_id"] = info["rid"]; f.write_text(yaml.safe_dump(ev, sort_keys=False))
    tamper_case(fn, "無法對應")

def test_ac_09_93_13_diagnostic_older_than_x():
    tamper_case(lambda root, info: diag_file(root, at="2000-01-01T00:00:00Z"), "X 時的內容無法由前段事件重建")

def test_ac_09_93_14_no_change_run_log():
    def fn(root, info):
        x = x_of(root); nc = [n["path"] for n in U.plan_of(root, x)["no_change"] if n["path"].endswith("/audit.log")]
        assert nc; _edit(root, nc[0], lambda b: b + b"forged\n")
    tamper_case(fn, "audit 檢視 runs/")

@pytest.mark.parametrize("mode", ["change", "delete"])
def test_ac_09_93_15_new_run_log(mode):
    def fn(root, info):
        v = P(root, f"runs/{info['rid']}/audit.log")
        v.unlink() if mode == "delete" else v.write_bytes(v.read_bytes() + b"forged\n")
    tamper_case(fn, "audit 檢視 runs/RUN-")

def test_ac_09_93_16_rolled_back_x1_not_executed_event():
    root, info = legacy()
    r = L.migrate(root, "--acknowledge-idle", info["running"], check=False, fault="after_progress:6"); assert r.returncode == 86
    x1 = U.incomplete(root)[0]["op_id"]
    ok(U.q(root, "migrate", "rollback", "--op", x1, "--by", "m"))
    ok(U.q(root, "migrate", "--by", "m", "--acknowledge-idle", info["running"], "--new-request")); vok(root)
    rplan = next(U.plan_of(root, o) for o in plans(root) if (U.plan_of(root, o) or {}).get("action") == "migrate_rollback")
    xp = U.plan_of(root, x1); ne = {s["seq"] for s in rplan["x_progress"]["steps"] if s["status"] == "not_executed"}
    st = next(s for s in xp["steps"] if s["kind"] == "event" and s["seq"] in ne)
    P(root, st["path"]).parent.mkdir(parents=True, exist_ok=True); P(root, st["path"]).write_bytes(blob(root, xp, st))   # 竄改：以計畫內容寫入
    vfail(root, st["path"])

def test_ac_09_93_17_tmp_file_ignored():
    root, _ = rich()
    P(root, "runs/_audit.d/.qaos-tmp-x-abc.yaml").write_text("garbage: [")
    vok_but(root, COUNTERS)

# ---------------------------------------------------------------- AC-09-94a：診斷事件的時間倒退（預期失敗，不誤放行）
def _sparse_x1_diag_rollback():
    """全新 root（X1 時沒有 _counters.yaml，之後配發 ID 不改寫 untouched）：X1 → maintenance end → 新建 run → 正式診斷事件
    → maintenance start → rollback（--allow-later-ops）。回傳 (root, 新 run, 診斷事件的 at)。"""
    root = U.mkroot(migrated=False)
    ok(U.q(root, "maintenance", "start", "--by", "m")); ok(U.q(root, "migrate", "--by", "m")); x1 = x_of(root)
    ok(U.q(root, "maintenance", "end", "--by", "m"))
    rid = new_run(root); at = yaml.safe_load(diagnose(root, rid).read_text())["at"]
    ok(U.q(root, "maintenance", "start", "--by", "m", "--new-request"))
    ok(U.q(root, "migrate", "rollback", "--op", x1, "--by", "m", "--allow-later-ops"))
    ok(U.q(root, "migrate", "verify", "--rolled-back"))
    return root, rid, at

def test_ac_09_94a_remigrate_with_earlier_clock():
    """AC-09-94a：X1 → 新建 run → 正式診斷事件 → R → 以較早的 clock 重新移轉 X2：X2 第一次 render 已包含該診斷事件，
    但依 at 被分到後段 → 只因判定 1 失敗（§18 第 11 點 (b)），不混入證據衝突。正常 clock 為對照組（通過）。"""
    root, rid, at = _sparse_x1_diag_rollback()
    ok(U.q(root, "migrate", "--by", "m", "--acknowledge-idle", rid, "--new-request")); vok(root)        # 對照：正常 clock
    root, rid, at = _sparse_x1_diag_rollback()
    U.q(root, "migrate", "--by", "m", "--acknowledge-idle", rid, "--new-request", check=True, extra_env={"QAOS_TEST_CLOCK": "2001-01-01T00:00:00Z"})
    assert at > "2001-01-01T00:00:00Z"
    r = vfail(root, f"audit 檢視 {GLOBAL}：X 時的內容無法由前段事件重建", f"audit 檢視 runs/{rid}/audit.log：X 時的內容無法由前段事件重建")
    issues = [l for l in r.stdout.splitlines() if l.startswith("- ")]
    assert all("X 時的內容無法由前段事件重建" in i for i in issues), r.stdout

def test_c01_injected_completed_of_aborted_x1_fails():
    """竄改：部分移轉 X1 → R → X2 之後，補寫 X1 未執行的 completed（內容等於計畫值）→ 失敗；刪除後通過。"""
    root, info = legacy()
    assert L.migrate(root, "--acknowledge-idle", info["running"], check=False, fault="after_progress:6").returncode == 86
    x1 = U.incomplete(root)[0]["op_id"]
    ok(U.q(root, "migrate", "rollback", "--op", x1, "--by", "m"))
    ok(U.q(root, "migrate", "--by", "m", "--acknowledge-idle", info["running"], "--new-request")); vok(root)
    xp = U.plan_of(root, x1); st = xp["steps"][-1]; assert st["kind"] == "status_final"
    P(root, st["path"]).write_bytes(blob(root, xp, st))
    vfail(root, f"證據衝突：{x1[:12]}… 未執行步驟的輸出 {st['path']}")
    P(root, st["path"]).unlink(); vok(root)

def test_c02_rollback_after_later_render_then_remigrate():
    """正式流程：X1 → maintenance end（render 改寫 X1 的 audit 檢視）→ R（該步凍結為 external_change, proof: progress）→ X2 → 通過。"""
    root, info = migrated(); x1 = x_of(root)
    ok(U.q(root, "maintenance", "end", "--by", "m")); ok(U.q(root, "maintenance", "start", "--by", "m", "--new-request"))
    ok(U.q(root, "migrate", "rollback", "--op", x1, "--by", "m")); ok(U.q(root, "migrate", "verify", "--rolled-back"))
    rp = next(U.plan_of(root, o) for o in plans(root) if (U.plan_of(root, o) or {}).get("action") == "migrate_rollback")
    assert any(r["status"] == "external_change" and r["proof"] == "progress" for r in rp["x_progress"]["steps"])
    ok(U.q(root, "migrate", "--by", "m", "--acknowledge-idle", info["running"], "--new-request")); vok(root)
    ok(U.q(root, "maintenance", "end", "--by", "m")); vok(root)

# ---------------------------------------------------------------- AC-09-94：合法中斷（明確失敗並提示續做）
def test_ac_09_94_interrupted_operations():
    root, _ = rich()
    r = spec_import(root, "SPEC-ZG-001", fault="before_completed", check=False); assert r.returncode == 86       # (b) 所有 render 之後
    o = U.incomplete(root)[0]["op_id"]
    interrupted(root, o)
    ok(U.q(root, "operation", "resume", o)); vok_but(root, COUNTERS)
    r = U.q(root, "run", "new", "regression-generation", "--input", 'target_suites=["full_regression"]', "--input", "scope=all",
            "--input", "trigger=manual", "--by", "t", "--new-request", fault="after_register"); assert r.returncode == 86
    o = U.incomplete(root)[0]["op_id"]; plan = U.plan_of(root, o)
    renders = [s for s in plan["steps"] if s["path"].endswith("audit.log")]; assert len(renders) == 2
    assert U.q(root, "operation", "resume", o, fault=f"after_progress:{renders[0]['seq']}").returncode == 86   # (a) 全域與 run 的 render 之間
    interrupted(root, o)
    ok(U.q(root, "operation", "resume", o)); vok_but(root, COUNTERS)
    r = spec_import(root, "SPEC-ZH-001", fault="after_register", check=False); assert r.returncode == 86            # (c) 事件檔已寫、完成紀錄未寫
    o = U.incomplete(root)[0]["op_id"]; st = next(s for s in U.plan_of(root, o)["steps"] if s["kind"] == "event")
    assert U.q(root, "operation", "resume", o, fault=f"after_output:{st['seq']}").returncode == 86
    assert P(root, st["path"]).exists() and not P(root, f"operations/_global/{o}/progress.d/{st['seq']:04d}-{st['step_id']}.yaml").exists()
    interrupted(root, o)
    ok(U.q(root, "operation", "resume", o)); vok_but(root, COUNTERS)

def interrupted(root, o):
    """合法中斷：只回報未完成操作（與竄改的訊息區分），不回報證據衝突或事件缺失；其餘只剩 §12.5 的 untouched。"""
    r = verify(root); issues = [l[2:] for l in r.stdout.splitlines() if l.startswith("- ")]
    assert r.returncode != 0 and any(i.startswith(f"未完成的操作 {o}") and f"operation resume {o}" in i and "不是竄改" in i for i in issues), r.stdout
    rest = [i for i in issues if not i.startswith("未完成的操作") and i != f"untouched {COUNTERS} 被改動"]
    assert not any("證據衝突" in i or "缺失或不符" in i or "無法對應" in i for i in issues), r.stdout
    assert all(i.startswith("audit 檢視 ") for i in rest), r.stdout                  # 已 render 進 log 的未完成事件只會讓檢視不符

# ---------------------------------------------------------------- AC-09-95：blobs 只有被步驟引用的內容（附錄 A 5-18）
def test_ac_09_95_no_orphan_blobs():
    root, info = migrated(); x = x_of(root)
    def check(o):
        pl = U.plan_of(root, o)
        on_disk = {p.name for p in P(root, f"operations/_global/{o}/blobs").iterdir()}
        assert on_disk == {s["blob"] for s in pl["steps"] if s.get("blob")}, o
    check(x)
    drafts = [p for p in P(root, f"operations/_global/{x}/blobs").iterdir() if b"manifest_sha256: null" in p.read_bytes()]
    assert drafts == []
    ok(U.q(root, "migrate", "rollback", "--op", x, "--by", "m"))
    check(next(o for o in plans(root) if (U.plan_of(root, o) or {}).get("action") == "migrate_rollback"))

# ---------------------------------------------------------------- 穩健性（自審補充）
def test_corrupt_later_plan_reports_instead_of_crashing():
    root, _ = rich(); o = _end_op(root)
    P(root, f"operations/_global/{o}.yaml").write_text("steps: [\n")                  # 竄改：計畫檔變成非法 YAML
    r = vfail(root, f"op {o} 的登錄紀錄或計畫檔無法核對"); assert "Traceback" not in r.stdout + r.stderr

def test_test_clock_must_be_well_formed():
    root, _ = rich()
    r = spec_import(root, "SPEC-ZI-001", extra_env={"QAOS_TEST_CLOCK": "not-a-time"}, check=False)
    assert r.returncode != 0 and "QAOS_TEST_CLOCK" in r.stderr

def test_too_many_same_second_diagnostics_need_manual_check():
    root, _ = rich(); xc = clock(root, x_of(root))
    for _ in range(11): diag_file(root, at=xc)
    vfail(root, "與 X 同秒的診斷事件太多（11）")

def test_c04_malformed_registration_reports_instead_of_crashing():
    root, _ = rich(); o = _end_op(root)
    f = next(P(root, "operations/_global/index.d").glob(f"*-{o}.yaml")); f.write_text("plan_seq: [\n")    # 竄改：登錄紀錄變成非法 YAML
    r = vfail(root, f"登錄紀錄 {f.name} 無法解析"); assert "Traceback" not in r.stdout + r.stderr
    f.write_text("- a\n"); r = vfail(root, f"登錄紀錄 {f.name} 的內容不是 mapping"); assert "Traceback" not in r.stdout + r.stderr

def test_c06_conflicting_terminal_status_of_rolled_back_x1():
    """竄改：X1 → R（rolled_back）→ X2 之後，補寫相反的 aborted_for_rollback；或改動 R 寫的 rolled_back → 失敗；還原後通過。"""
    root = U.mkroot(migrated=False)
    ok(U.q(root, "maintenance", "start", "--by", "m")); ok(U.q(root, "migrate", "--by", "m")); x1 = x_of(root)
    ok(U.q(root, "migrate", "rollback", "--op", x1, "--by", "m")); ok(U.q(root, "migrate", "--by", "m", "--new-request")); vok(root)
    rb = P(root, f"operations/_global/status.d/{x1}-rolled_back.yaml"); assert rb.exists()
    f = P(root, f"operations/_global/status.d/{x1}-aborted_for_rollback.yaml")
    f.write_text(yaml.safe_dump({"op_id": x1, "status": "aborted_for_rollback", "by": "forged", "at": "2026-01-01T00:00:00Z"}))
    vfail(root, f"{x1[:12]}… 的終態紀錄應恰好是 ['rolled_back']", f.relative_to(root).as_posix())
    f.unlink(); vok(root)
    data = rb.read_bytes(); rb.write_bytes(data + b"# x\n")
    vfail(root, f"寫入的稽核紀錄 {rb.relative_to(root).as_posix()} 缺失或不符")
    rb.write_bytes(data); vok(root)

def test_c05_verify_does_not_rescan_status_per_operation():
    """全操作核對與附註共用一次載入的狀態索引：逐 op 掃描 status.d 的次數不隨後續操作數增加（只剩 X 本身的固定查詢）。"""
    code = """
from tools.qaos import operation as op, migrate as m
calls = [0]; orig = op.statuses
def counted(o): calls[0] += 1; return orig(o)
op.statuses = counted
m.verify()
print(calls[0], len(op.registrations()))
"""
    root, _ = rich(); a, n1 = map(int, U.py(root, code).stdout.split())
    for i in range(5): spec_import(root, f"SPEC-P{i}-001")
    b, n2 = map(int, U.py(root, code).stdout.split())
    assert n2 == n1 + 5 and a == b <= 2, (a, b, n1, n2)
