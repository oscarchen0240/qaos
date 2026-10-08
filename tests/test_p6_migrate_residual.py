"""P6-G2：P3 移轉／回復／verify 留待 P6 的項目（需求 A 第 5 章 §10～§15；AC-09-14、45、47、48、50、58、73、74、76、79、81～85、89(b)、§12；AC-07-44、80、82）。

資料來源：
- legacy 資料由需求 A 之前的程式（base 2e01d4b，tests/p3_legacy.py 以 git archive 匯出）以它自己的正式流程產生；
  AC-09-50 的「有 PENDING APR 的 RUNNING run」：舊程式的 `_create_approval` 先存 APR、再把 run 轉 WAITING_HUMAN，
  兩者之間沒有原子性。fixture 在**舊程式**的程序中，以故障注入讓「轉 WAITING_HUMAN」那一步崩潰兩次，留下兩張 PENDING APR
  而 run 仍是 RUNNING（標明：舊程式中的故障注入；之後不手改任何業務檔）。
- 新程式的狀態全部以正式指令建立；中止點以 QAOS_FAULT 注入；同步以 QAOS_PAUSE。
- 只有標明「竄改」「故障注入」「模擬經授權的人工修復」「函式層」的子例，才在流程後改檔或替換函式。"""
import json, os, pathlib, subprocess, sys, time, yaml, pytest
from tests import p1_util as U, p3_legacy as L
from tests.test_p3_migrate import legacy, migrated, x_of, ok, status_files, plans, NOTHING, _r_plan
import shutil, tempfile

MARKER = "artifacts/requirements/_migration.yaml"
SPEC_YAML = "specs/demo/AUTH/SPEC-AUTH-001/spec.yaml"
META = "artifacts/requirements/SPEC-AUTH-001/v1.0/revisions/R000.meta.yaml"

def P(root, rel=""): return pathlib.Path(root) / rel
def G(rp): return {g: [s for s in rp["steps"] if s.get("group") == g] for g in ("takeover", "restore", "marker", "terminal")}
def prog(root, plan, st): return P(root, f"operations/{plan['scope']}/{plan['op_id']}/progress.d/{st['seq']:04d}-{st['step_id']}.yaml")
def out_after(root, st):
    p = P(root, st["path"]); return (not p.exists()) if st["expected_after"] is None else (p.is_file() and U.sha(p) == st["expected_after"])
def out_before(root, st):
    p = P(root, st["path"]); return (not p.exists()) if st["expected_before"] is None else (p.is_file() and U.sha(p) == st["expected_before"])
def done(root, plan, st): return out_after(root, st) and prog(root, plan, st).is_file()
def before(root, plan, st): return out_before(root, st) and not prog(root, plan, st).exists()
def go(root, entry, args, op, fault=None):
    return U.q(root, *args, fault=fault) if entry == "resend" else U.q(root, "operation", "resume", op, fault=fault)
def rb_args(x): return ["migrate", "rollback", "--op", x, "--by", "m"]
def classify(root, op_id) -> dict:
    out = U.py(root, f"import json\nfrom tools.qaos import operation as O\nc = O.classify_steps(O.load_plan('{op_id}'))\n"
                     "print(json.dumps({'status': c.status, 'conflicts': c.conflicts, 'external': c.external}))").stdout.strip().splitlines()[-1]
    d = json.loads(out); d["status"] = {int(k): v for k, v in d["status"].items()}; return d
def assert_like_55(before_snap, root):
    """結果和 AC-09-55 相同：restore 回到 pre、remove 不存在；只新增稽核、控制證據與 run 的事件檔。"""
    d = U.diff(before_snap, U.snapshot(root))
    assert d["changed"] == [] and d["removed"] == [], d
    assert all(p.startswith(("operations/", "runs/_audit.d/", "runs/RUN-", "locks/")) for p in d["added"]), d["added"]
    assert not [p for p in d["added"] if p.startswith("runs/RUN-") and "/audit.d/" not in p]

def partial_x(pick, kind="after_progress", mode="--acknowledge-idle", src=None):
    """以正式流程讓 X 中止在 pick(xplan, info) 指定的步驟（kind：after_progress = 完成紀錄已寫；after_output = 輸出已落盤、完成紀錄未寫）。
    先以 after_register 中止（計畫已固定），讀計畫決定 seq，再以同請求重送、在該點中止。回傳 (root, info, x, xplan, migrate 參數, 移轉前快照)。"""
    root, info = (src or legacy)(); snap = U.snapshot(root)
    args = ["migrate", "--by", "m", mode, info["running"]]
    ok(U.q(root, "maintenance", "start", "--by", "m"))
    assert U.q(root, *args, fault="after_register").returncode == 86
    x = U.incomplete(root)[0]["op_id"]; xp = U.plan_of(root, x)
    assert U.q(root, *args, fault=f"{kind}:{pick(xp, info)}").returncode == 86
    return root, info, x, xp, args, snap

def seq_path(suffix): return lambda xp, info: next(s["seq"] for s in xp["steps"] if s["path"].endswith(suffix))
CLR_STEP = lambda xp, info: next(s["seq"] for s in xp["steps"] if s["path"] == f"clarifications/demo/AUTH/{info['clr']}.yaml")
MARKER_STEP = seq_path("_migration.yaml")

# ======================================================================== AC-09-50 的 fixture（舊程式）
_APR_TPL = {}
APR_EXTRA = r'''
from tools.qaos import state as _st
_orig = _st.apply
def _crash(machine, obj, to, *a, **k):
    if machine == "workflow_run" and to == "WAITING_HUMAN": raise SystemExit(99)      # 舊程式中的故障注入：APR 已存、run 尚未轉 WAITING_HUMAN
    return _orig(machine, obj, to, *a, **k)
tcs3, _ = H.draft_set(prefix="01CX5ZZKBKACTAV9WEVGEMMVR")
did3, pd3 = H.write_artifact(rid2, "T2", "agent-test-designer", "TestCaseDraft", {"mode": "spec", "spec_id": SPEC, "spec_version": VER, "testcases": tcs3}, refs2, {"type": "RequirementModel", "ids": [rmid]}, "test-design")
_, pr3 = H.write_artifact(rid2, "T2", "agent-test-designer", "TestDesignReport", H.design_report(did3, tcs3), [{"entity_type": "Artifact", "id": did3}], {"type": "TestCaseDraft", "ids": [did3]}, "test-design")
assert engine.submit(rid2, "T2", str(pd3))[0] and engine.submit(rid2, "T2", str(pr3))[0] and engine.evaluate_gate(rid2, "T2")["result"] == "PASS"
_, pv3 = H.write_artifact(rid2, "T3", "agent-test-validator", "TestValidationReport", H.validation_report(did3, rmid, "PASS"),
                         [{"entity_type": "Artifact", "id": did3}, {"entity_type": "Artifact", "id": rmid}], {"type": "TestCaseDraft", "ids": [did3]}, "validation")
assert engine.submit(rid2, "T3", str(pv3))[0]
_st.apply = _crash
for _ in range(2):
    try: engine.evaluate_gate(rid2, "T3")
    except SystemExit: pass
_st.apply = _orig
'''

def apr_legacy():
    """舊程式產生：RUNNING 的 run 帶兩張 PENDING APR（見模組說明）。回傳 (root, 摘要)。"""
    if not _APR_TPL:
        root = U.mkroot(migrated=False); old = L.old_checkout()
        code = L.OLD_FLOW.replace('print(json.dumps({"done"', APR_EXTRA + '\nprint(json.dumps({"done"')
        env = {**os.environ, "QAOS_ROOT": str(root), "PYTHONDONTWRITEBYTECODE": "1"}
        r = subprocess.run([sys.executable, "-c", code], cwd=old, env=env, capture_output=True, text=True, timeout=300)
        if r.returncode != 0: raise AssertionError(f"舊程式的 legacy 流程失敗：\n{r.stdout}\n{r.stderr}")
        _APR_TPL.update(root=root, info=json.loads(r.stdout.strip().splitlines()[-1]))
    dst = pathlib.Path(tempfile.mkdtemp(prefix="qaos-p6-")) / "root"; shutil.copytree(_APR_TPL["root"], dst)
    return dst, dict(_APR_TPL["info"])

# ======================================================================== 移轉與 cancel（AC-09-45、47、48、50；AC-07-44）
def test_ac_09_45_run_cancel_in_s_pre_then_migrate():
    """AC-09-45：S_pre 先 `run cancel`（舊程式留下的 RUNNING run），進入維護後 `migrate` → 兩個操作都完成。
    另依 AC-07-43（真實舊位元組）：cancel 只寫事件、不 render；legacy 檔逐位元等於 cancel 之前的 audit.log。"""
    root, info = legacy(); rid = info["running"]
    logs = {p: p.read_bytes() for p in P(root).glob("runs/**/audit.log")}
    ok(U.q(root, "run", "cancel", rid, "--by", "o"))
    assert all(p.read_bytes() == b for p, b in logs.items())                                    # S_pre：不 render、不改 audit.log
    ok(U.q(root, "maintenance", "start", "--by", "m"))
    ok(U.q(root, "migrate", "--by", "m"))                                                        # 已沒有 RUNNING 的 run：不需指定處理方式
    ok(U.q(root, "migrate", "verify"))
    ops = U.op_list(root)
    assert [o["action"] for o in ops if o["action"] in ("run_cancel", "migrate")] == ["run_cancel", "migrate"] and all("completed" in o["statuses"] for o in ops)
    assert U.load(root, f"runs/{rid}/run.yaml")["status"] == "CANCELLED" and U.load(root, MARKER)["mode_per_run"] == {}
    for p, b in logs.items():
        assert (p.parent / "audit.legacy.log").read_bytes() == b and p.read_bytes().startswith(b)
    assert b"CANCEL_RUN" in P(root, f"runs/{rid}/audit.log").read_bytes()[len(logs[P(root, f'runs/{rid}/audit.log')]):]

@pytest.mark.parametrize("entry", ["resend", "resume"])
def test_ac_09_47_abort_after_cancel_step_before_sidecar(entry):
    """AC-09-47：`migrate --cancel-run` 在 cancel 步驟之後、sidecar 之前中止 → 續做（同請求重送／operation resume）。
    預期：同一 op_id；cancel 步驟已完成 → 略過（run.yaml、cancel 事件、完成紀錄的位元組與 inode 都不變，事件只有一筆）；寫入 sidecar 與標記。"""
    rid_box = {}
    def pick(xp, info):
        first_sc = next(s["seq"] for s in xp["steps"] if s["path"].startswith("artifacts/requirements/_bindings/"))
        cancel = [s for s in xp["steps"] if s["path"] == f"runs/{info['running']}/run.yaml" or s["path"].startswith(f"runs/{info['running']}/audit.d/")]
        assert cancel and max(s["seq"] for s in cancel) < first_sc
        rid_box["cancel"] = cancel; return first_sc - 1
    root, info, x, xp, args, _ = partial_x(pick, mode="--cancel-run")
    rid = info["running"]; cancel = rid_box["cancel"]
    assert U.load(root, f"runs/{rid}/run.yaml")["status"] == "CANCELLED" and all(done(root, xp, s) for s in cancel)
    assert not P(root, f"artifacts/requirements/_bindings/{rid}.yaml").exists() and not P(root, MARKER).exists()
    keep = {p: (p.read_bytes(), p.stat().st_ino) for s in cancel for p in (P(root, s["path"]), prog(root, xp, s))}
    ok(go(root, entry, args, x))
    assert x_of(root) == x and [o["op_id"] for o in U.op_list(root) if o["action"] == "migrate"] == [x]
    assert {p: (p.read_bytes(), p.stat().st_ino) for p in keep} == keep                         # 略過：沒有重寫
    assert len(list(P(root, f"runs/{rid}/audit.d").glob(f"{x}-*.yaml"))) == len([s for s in cancel if s["kind"] == "event"]) == 1
    assert U.load(root, f"artifacts/requirements/_bindings/{rid}.yaml")["requirement_model_revision"]["revision"] == "R000"
    assert U.load(root, MARKER)["mode_per_run"] == {rid: "cancel_run"}
    ok(U.q(root, "migrate", "verify"))

def test_ac_09_48_incomplete_run_cancel_plan_blocks_maintenance_and_migrate():
    """AC-09-48：移轉前有一份未完成的 `run cancel` 計畫（故障注入中止）→ `maintenance start`、`migrate` 都拒絕並提示 resume、沒有寫入；
    `operation resume` 完成它之後，`maintenance start` → `migrate` 完成。"""
    root, info = legacy(); rid = info["running"]
    assert U.q(root, "run", "cancel", rid, "--by", "o", fault="after_output:1").returncode == 86
    c = U.incomplete(root)[0]["op_id"]; snap = U.snapshot(root)
    for cmd in (["maintenance", "start", "--by", "m"], ["migrate", "--by", "m"], ["migrate", "--by", "m", "--cancel-run", rid]):
        r = U.q(root, *cmd); assert r.returncode != 0 and "operation resume" in r.stderr and c in r.stderr, (cmd, r.stderr)
    assert U.diff(snap, U.snapshot(root)) == NOTHING
    ok(U.q(root, "operation", "resume", c)); assert U.load(root, f"runs/{rid}/run.yaml")["status"] == "CANCELLED"
    ok(U.q(root, "maintenance", "start", "--by", "m")); ok(U.q(root, "migrate", "--by", "m")); ok(U.q(root, "migrate", "verify"))
    assert U.incomplete(root) == []

def _expected_tail(root, log_rel):
    """依目前事件檔，render 時接在 legacy 之後的內容（依 (at, op_id, step) 排序）。"""
    glob_ = log_rel == "runs/_audit.log"
    pats = ["runs/*/audit.d/*.yaml", "runs/_audit.d/*.yaml"] if glob_ else [f"{log_rel.rsplit('/', 1)[0]}/audit.d/*.yaml"]
    evs = [yaml.safe_load(p.read_text()) for pat in pats for p in P(root).glob(pat)]
    evs.sort(key=lambda e: (str(e["at"]), str(e["op_id"]), int(e["step"])))
    return "".join((f"{e.get('run_id') or '-'}\t" if glob_ else "") + f"{e['at']}\t{e['actor']}\t{e['action']}\t{e.get('detail') or ''}\n" for e in evs).encode()

def test_ac_09_50_cancel_run_cancels_every_pending_approval_and_07_44_render():
    """AC-09-50：有 PENDING APR 的 RUNNING run（舊程式 fixture，兩張）→ `migrate --cancel-run` → 所有 PENDING APR 都 CANCELLED，每張各有事件。
    AC-07-44（同 AC-07-43）：legacy 檔逐位元等於移轉前的 audit.log；第一次 render = legacy 原位元組 + cancel 事件 + 移轉事件（依序）。
    另確認回復：APR 回到 PENDING（restore）、run 回到 RUNNING、APR render 依實際狀態移除。"""
    root, info = apr_legacy(); rid = info["running"]; snap = U.snapshot(root)
    aprs = sorted(p for p in P(root).glob("approvals/APR-*.yaml") if yaml.safe_load(p.read_text())["run_id"] == rid)
    pend = [p for p in aprs if yaml.safe_load(p.read_text())["status"] == "PENDING"]
    assert len(pend) == 2 and U.load(root, f"runs/{rid}/run.yaml")["status"] == "RUNNING"
    logs = {p.relative_to(P(root)).as_posix(): p.read_bytes() for p in [*P(root).glob("runs/*/audit.log"), P(root, "runs/_audit.log")]}
    L.migrate(root, "--cancel-run", rid, check=True); x = x_of(root)
    assert U.load(root, f"runs/{rid}/run.yaml")["status"] == "CANCELLED"
    for p in pend:
        a = yaml.safe_load(p.read_text()); assert a["status"] == "CANCELLED", a["approval_id"]
        assert p.with_suffix(".md").is_file()
    evs = U.plan_of(root, x)["audit_events"]
    assert [e["action"] for e in evs if e["run_id"] == rid] == ["CANCEL_RUN"] + ["CANCEL_APPROVAL"] * len(pend)
    assert sorted(next(iter(e["detail"].split("："))) for e in evs if e["action"] == "CANCEL_APPROVAL") == sorted(p.stem for p in pend)
    man = U.load(root, f"operations/_global/{x}/manifest.yaml")
    assert {f"approvals/{p.name}" for p in pend} <= {e["path"] for e in man["restore"]}                # 表 11.3：cancel-run 的 PENDING APR 屬 restore
    for rel, b in logs.items():                                                                         # AC-07-44
        assert P(root, rel.replace("audit.log", "audit.legacy.log")).read_bytes() == b
        assert P(root, rel).read_bytes() == b + _expected_tail(root, rel), rel
    tail = P(root, f"runs/{rid}/audit.log").read_bytes()[len(logs[f'runs/{rid}/audit.log']):].decode()
    assert tail.index("CANCEL_RUN") < tail.index("CANCEL_APPROVAL")
    g = P(root, "runs/_audit.log").read_bytes()[len(logs["runs/_audit.log"]):].decode()
    assert "CANCEL_APPROVAL" in g and "\tMIGRATE\t" in g
    ok(U.q(root, "migrate", "verify"))
    ok(U.q(root, "migrate", "rollback", "--op", x, "--by", "m")); ok(U.q(root, "migrate", "verify", "--rolled-back"))
    assert_like_55(snap, root)
    assert all(yaml.safe_load(p.read_text())["status"] == "PENDING" for p in pend) and U.load(root, f"runs/{rid}/run.yaml")["status"] == "RUNNING"

# ======================================================================== R 的中止點：部分移轉（AC-09-58、79、81）
@pytest.mark.parametrize("point", ["fp_r0", "r1_tail", "fp_r1"])
@pytest.mark.parametrize("entry", ["resend", "resume"])
def test_ac_09_81_58_partial_x_rollback_abort_points(point, entry):
    """AC-09-81：X 中止在 CLR rev 0 之後（正式流程＋故障注入），R 的清單同時有已寫的 remove、未寫的 remove（TC sidecar、標記）、
    已修改的 restore（CLR）、未修改的 restore（runs/_audit.log）。R 中止在 ① FP-R0 ② R1 輸出已落盤、完成紀錄未寫（FP-W）③ FP-R1，兩種入口續做。
    AC-09-58：③ 的 R 計畫同時有步驟與 no_change；續做不重算（R 計畫檔位元組不變：later_ops、x_progress、no_change 都沿用）；
    no_change 路徑不影響 L；R 不把自己列為後續操作；結果和 AC-09-55 相同。"""
    root, info, x, xp, _, snap = partial_x(CLR_STEP)
    args = rb_args(x)
    assert U.q(root, *args, fault="after_register").returncode == 86
    rp = _r_plan(root); rid = rp["op_id"]; rpf = P(root, f"operations/_global/{rid}.yaml"); rp_bytes = rpf.read_bytes(); g = G(rp)
    nc = {n["path"]: n["content_sha256"] for n in rp["no_change"]}; step_paths = {s["path"] for s in rp["steps"]}
    tc_sc = {f"testcases/_bindings/{t}-v1.yaml" for t in info["tcs"]}
    assert tc_sc <= set(nc) and MARKER in nc and nc[MARKER] is None and "runs/_audit.log" in nc                # 未寫的 remove、未修改的 restore 在 no_change
    assert f"clarifications/demo/AUTH/{info['clr']}.yaml" in step_paths and f"artifacts/requirements/_bindings/{info['running']}.yaml" in step_paths
    assert not (set(nc) & step_paths)
    assert [s["step_id"] for s in g["takeover"]][0] == "R1" and g["marker"] == [] and [s["step_id"] for s in g["terminal"]] == ["completed"]
    assert rp["later_ops_snapshot"] == [] and rp["x_progress"]["x_status_at_creation"] == "in_progress"
    body = [s for s in rp["steps"] if s["kind"] != "status_final"]; r1 = g["takeover"][0]
    if point == "r1_tail": assert U.q(root, "operation", "resume", rid, fault=f"after_output:{r1['seq']}").returncode == 86
    k = g["restore"][1]["seq"]
    if point == "fp_r1": assert U.q(root, "operation", "resume", rid, fault=f"after_progress:{k}").returncode == 86
    cls = classify(root, rid); st = cls["status"]
    assert cls["conflicts"] == [] and cls["external"] == []
    if point == "fp_r0": assert all(st[s["seq"]] == "not_executed" for s in body)                                # L 不存在；R1、R2 不是衝突
    if point == "r1_tail":
        assert st[r1["seq"]] == "tail" and all(st[s["seq"]] == "not_executed" for s in body if s["seq"] > r1["seq"])
        r1_ino = P(root, r1["path"]).stat().st_ino
    if point == "fp_r1": assert all(st[s["seq"]] == ("done" if s["seq"] <= k else "not_executed") for s in body)
    assert all(U.sha(P(root, p)) == sha for p, sha in nc.items())                                              # no_change 仍是記錄值，且不是步驟：不會被選為 L
    assert U.q(root, "operation", "resume", x).returncode != 0                                                 # X 已被接管
    ok(go(root, entry, args, rid))
    ok(U.q(root, "migrate", "verify", "--rolled-back"))
    assert rpf.read_bytes() == rp_bytes                                                                        # 不重算、不改寫 R 計畫
    if point == "r1_tail": assert P(root, r1["path"]).stat().st_ino == r1_ino and prog(root, rp, r1).is_file()   # 補寫完成紀錄、不重寫輸出
    assert status_files(root, x) == ["aborted_for_rollback"] and status_files(root, rid) == ["completed"]
    later = U.py(root, f"import json\nfrom tools.qaos import migrate as M\nprint(json.dumps([o['op_id'] for o in M.later_ops('{x}')]))").stdout.strip().splitlines()[-1]
    assert rid not in json.loads(later)                                                                        # R 不把自己列為後續操作
    assert_like_55(snap, root)

@pytest.mark.parametrize("case", ["r1", "restore", "marker"])
@pytest.mark.parametrize("entry", ["resend", "resume"])
def test_ac_09_79_r_fp_w_with_no_change(case, entry):
    """AC-09-79：X 中止在 FP-M3（標記已寫、render 未寫；正式流程＋故障注入），R 的計畫有 no_change（未修改的 runs/_audit.log）。
    R 在 ① R1 ② 某個 restore（CLR）③ 標記的 remove 這三步「輸出已落盤、完成紀錄未寫」時中止，兩種入口續做。
    預期：補寫自己的完成紀錄、不重寫輸出（inode 不變）、完成；no_change 不被選為 L；③ 不再執行檢查 A（以 before_check_a 故障點探測：不觸發），
    但執行檢查 B（before_check_b 故障點觸發）；aborted_for_rollback 只有一個；其他 status.d、index.d 紀錄不是衝突。"""
    root, info, x, xp, _, snap = partial_x(MARKER_STEP)
    assert P(root, MARKER).exists() and U.load(root, MARKER)["migrate_op_id"] == x
    args = rb_args(x)
    assert U.q(root, *args, fault="after_register").returncode == 86
    rp = _r_plan(root); rid = rp["op_id"]; g = G(rp)
    assert rp["no_change"] and "runs/_audit.log" in {n["path"] for n in rp["no_change"]} and g["marker"]
    st_ = {"r1": g["takeover"][0], "restore": next(s for s in g["restore"] if s["path"] == f"clarifications/demo/AUTH/{info['clr']}.yaml"), "marker": g["marker"][0]}[case]
    assert U.q(root, "operation", "resume", rid, fault=f"after_output:{st_['seq']}").returncode == 86
    assert out_after(root, st_) and not prog(root, rp, st_).exists()
    cls = classify(root, rid)
    assert cls["status"][st_["seq"]] == "tail" and cls["conflicts"] == [] and cls["external"] == []
    assert all(v == "done" for q, v in cls["status"].items() if q < st_["seq"]) and all(v == "not_executed" for q, v in cls["status"].items() if q > st_["seq"])
    ino = P(root, st_["path"]).stat().st_ino if P(root, st_["path"]).exists() else None
    others = {p: p.read_bytes() for d in ("index.d", "status.d") for p in P(root, f"operations/_global/{d}").glob("*.yaml")}
    if case == "marker":
        assert go(root, entry, args, rid, fault="before_check_b").returncode == 86                            # 檢查 B 會執行
        assert prog(root, rp, st_).is_file() and not P(root, MARKER).exists()
        r = go(root, entry, args, rid, fault="before_check_a"); assert r.returncode == 0, r.stderr             # 檢查 A 不再執行（故障點沒有被觸發）
    else:
        ok(go(root, entry, args, rid))
        assert P(root, st_["path"]).stat().st_ino == ino                                                        # 不重寫
    assert prog(root, rp, st_).is_file() and status_files(root, x) == ["aborted_for_rollback"] and status_files(root, rid) == ["completed"]
    assert all(p.read_bytes() == b for p, b in others.items())
    ok(U.q(root, "migrate", "verify", "--rolled-back")); assert_like_55(snap, root)

@pytest.mark.parametrize("entry", ["resend", "resume"])
def test_ac_09_79_tampered_r1_record_stops(entry):
    """AC-09-79「竄改既有紀錄的內容 → 停止」：R1 已落盤（合法尾端）後，竄改 `status.d/<X>-aborted_for_rollback` 的內容 → 續做停止、不重寫。"""
    root, info, x, xp, _, _ = partial_x(MARKER_STEP)
    args = rb_args(x); assert U.q(root, *args, fault="after_register").returncode == 86
    rp = _r_plan(root); rid = rp["op_id"]; r1 = G(rp)["takeover"][0]
    assert U.q(root, "operation", "resume", rid, fault=f"after_output:{r1['seq']}").returncode == 86
    f = P(root, r1["path"]); f.write_bytes(f.read_bytes() + b"note: x\n")                                       # 竄改
    snap = U.snapshot(root)
    r = go(root, entry, args, rid); assert r.returncode != 0 and "停止" in r.stderr and r1["path"] in r.stderr, r.stderr
    assert U.diff(snap, U.snapshot(root)) == NOTHING and status_files(root, rid) == []

# ======================================================================== T5 與 X 續做的證據衝突（AC-09-73、74、76）
def _x72():
    """AC-09-72 的狀態（cancel-run 模式）：X 中止在 CLR rev 0 的完成紀錄之後；cancel 事件已寫並有完成紀錄，TC sidecar、標記還沒寫。"""
    return partial_x(CLR_STEP, mode="--cancel-run")

def _cancel_event(xp, info):
    return next(s for s in xp["steps"] if s["kind"] == "event" and s["path"].startswith(f"runs/{info['running']}/audit.d/"))

def _tamper(case):
    """回傳 (root, info, x, xp, X 的參數, 竄改的 X 步驟, 竄改說明)。各例都是「竄改」。"""
    if case == "event_tail_changed":                                                                            # 74②：合法尾端的事件（輸出已落盤、沒有完成紀錄）
        root, info, x, xp, args, _ = partial_x(lambda xp, info: _cancel_event(xp, info)["seq"], kind="after_output", mode="--cancel-run")
        ev = _cancel_event(xp, info); assert not prog(root, xp, ev).exists()
        f = P(root, ev["path"]); f.write_bytes(f.read_bytes() + b"x: 1\n"); return root, info, x, xp, args, ev
    root, info, x, xp, args, _ = _x72(); ev = _cancel_event(xp, info); assert done(root, xp, ev)
    if case == "event_deleted": P(root, ev["path"]).unlink(); return root, info, x, xp, args, ev                 # 73①
    if case == "event_changed": f = P(root, ev["path"]); f.write_bytes(f.read_bytes() + b"x: 1\n"); return root, info, x, xp, args, ev   # 74①
    if case == "progress_deleted":                                                                              # 73②：尾端之前某一步的完成紀錄
        s = next(s for s in xp["steps"] if s["step_id"] == "backup1"); prog(root, xp, s).unlink(); return root, info, x, xp, args, s
    raise AssertionError(case)

T_CASES = ["event_deleted", "progress_deleted", "event_changed", "event_tail_changed"]

@pytest.mark.parametrize("case", T_CASES)
def test_ac_09_73_74_t5_refuses_with_report(case):
    """AC-09-73 ①（刪除有完成紀錄的 X 事件）、②（刪除尾端之前的完成紀錄）；AC-09-74 ①（改有完成紀錄的事件）、②（改合法尾端的事件）。
    預期：T5 拒絕，不建立 R、不寫入任何檔案；報告列出步驟、路徑與原因；X 仍是 in_progress。"""
    root, info, x, xp, _, s = _tamper(case)
    snap = U.snapshot(root); n = len(plans(root))
    r = U.q(root, *rb_args(x)); assert r.returncode != 0 and "T5" in r.stderr, r.stderr
    path = s["path"] if case != "progress_deleted" else prog(root, xp, s).relative_to(P(root)).as_posix()
    assert (s["path"] in r.stderr or path in r.stderr) and f"步驟 {s['step_id']}" in r.stderr
    assert any(w in r.stderr for w in ("缺完成紀錄", "既不是 before 也不是 after", "輸出不存在或被還原", "完成紀錄")), r.stderr   # 原因
    assert U.diff(snap, U.snapshot(root)) == NOTHING and len(plans(root)) == n and status_files(root, x) == []

@pytest.mark.parametrize("case", T_CASES)
def test_ac_09_73_t5_report_names_the_step(case):
    """AC-09-73：T5 報告列出步驟（P6-G2-01：修正前 migrate._report 只輸出路徑與原因，每列印成「記錄值 None，目前值 None」）。"""
    root, info, x, xp, _, s = _tamper(case)
    r = U.q(root, *rb_args(x)); assert r.returncode != 0 and "T5" in r.stderr
    assert s["step_id"] in r.stderr and "記錄值 None，目前值 None" not in r.stderr, r.stderr

@pytest.mark.parametrize("case", T_CASES)
@pytest.mark.parametrize("entry", ["resend", "resume"])
def test_ac_09_76_resume_x_stops_on_evidence_conflict(case, entry):
    """AC-09-76：AC-09-73、74 的竄改狀態，改成續做 X（同請求重送、operation resume X）。
    預期：V5 停止，不重寫被刪除的事件、完成紀錄；回報證據衝突；其他檔案不變。"""
    root, info, x, xp, args, s = _tamper(case)
    snap = U.snapshot(root)
    r = go(root, entry, args, x); assert r.returncode != 0 and "停止" in r.stderr and "證據衝突" in r.stderr, r.stderr
    assert U.diff(snap, U.snapshot(root)) == NOTHING and status_files(root, x) == []

def test_ac_09_74_3_x_event_changed_after_rollback_fails_verify():
    """AC-09-74 ③：R 完成之後才改 X 事件的內容（竄改）→ `verify --rolled-back` 失敗並列出該證據衝突；恢復後通過。"""
    root, info, x, xp, _, _ = _x72()
    ok(U.q(root, *rb_args(x))); ok(U.q(root, "migrate", "verify", "--rolled-back"))
    ev = _cancel_event(xp, info); f = P(root, ev["path"]); orig = f.read_bytes(); f.write_bytes(orig + b"x: 1\n")
    r = U.q(root, "migrate", "verify", "--rolled-back"); assert r.returncode != 0 and "證據衝突" in r.stdout and ev["path"] in r.stdout, r.stdout
    f.write_bytes(orig); ok(U.q(root, "migrate", "verify", "--rolled-back"))

# ======================================================================== T7：X 的 no_change 業務檔（AC-09-82 ④）
def test_ac_09_82_4_x_no_change_business_file():
    """AC-09-82 ④：以正式流程完成 X（X 的計畫有 no_change 業務檔：舊程式已 render 的 CLR .md），故障注入改動它 → `migrate rollback`。
    預期：T7 拒絕、報告列出路徑與類別；沒有 R、沒有任何終態紀錄；標記仍在、衝突檔不被寫入；重送與 operation resume 都不能把它當成功略過。"""
    root, info = migrated(); x = x_of(root); xp = U.plan_of(root, x)
    md = f"clarifications/demo/AUTH/{info['clr']}.md"
    assert md in {n["path"] for n in xp["no_change"] if n["kind"] == "business"}
    f = P(root, md); f.write_bytes(f.read_bytes() + b"\n<!-- injected -->\n"); bad = f.read_bytes()                   # 故障注入
    snap = U.snapshot(root); n = len(plans(root))
    for cmd in (rb_args(x), ["operation", "resume", x], rb_args(x)):
        r = U.q(root, *cmd)
        if cmd[0] == "migrate": assert r.returncode != 0 and "T7" in r.stderr and md in r.stderr and "x_no_change" in r.stderr, r.stderr
    assert U.diff(snap, U.snapshot(root)) == NOTHING and len(plans(root)) == n
    assert status_files(root, x) == ["completed"] and P(root, MARKER).exists() and f.read_bytes() == bad
    assert not [o for o in U.op_list(root) if o["action"] == "migrate_rollback"]

# ======================================================================== FP-R4 的外部改動與 §13.9 修復表（AC-09-83 ①②）
def _r_at_fp_r1():
    """部分移轉的 X（R 有 no_change）；R 中止在 restore 群組的第 2 步完成紀錄之後（FP-R1）。"""
    root, info, x, xp, _, snap = partial_x(CLR_STEP)
    args = rb_args(x); assert U.q(root, *args, fault="after_register").returncode == 86
    rp = _r_plan(root); rid = rp["op_id"]; rs = G(rp)["restore"]
    assert rs[0]["path"] == f"clarifications/demo/AUTH/{info['clr']}.yaml" and len(rs) >= 6
    assert U.q(root, "operation", "resume", rid, fault=f"after_progress:{rs[1]['seq']}").returncode == 86
    assert done(root, rp, rs[0]) and done(root, rp, rs[1]) and before(root, rp, rs[2])
    return root, info, x, rp, rid, args, rs, snap

def _stops(root, args, rid, what):
    for cmd in (args, ["operation", "resume", rid]):                                                          # 兩種入口都停止
        r = U.q(root, *cmd); assert r.returncode != 0 and what in r.stderr, (what, r.stderr)
    assert status_files(root, rid) == [] and U.q(root, "maintenance", "end", "--by", "m").returncode != 0

def _finish(root, rid, snap):
    ok(U.q(root, "operation", "resume", rid)); ok(U.q(root, "migrate", "verify", "--rolled-back")); assert_like_55(snap, root)

def test_ac_09_83_1_unprocessed_step_path_changed_then_repaired_to_before():
    """AC-09-83 ①：FP-R1 之後改動尚未處理的步驟路徑（故障注入）→ 兩種入口 V5 停止；R 保持 in_progress、沒有 Rt2；maintenance end 拒絕。
    修復表：恢復成表外的內容 → 仍停止；沒有完成紀錄的步驟恢復成 before（模擬經授權的人工修復）→ 完成，verify 通過。"""
    root, info, x, rp, rid, args, rs, snap = _r_at_fp_r1()
    s = next(s for s in rs[3:] if s["kind"] == "business" and s["expected_before"] is not None)
    f = P(root, s["path"]); orig = f.read_bytes(); f.write_bytes(orig + b"# external\n")
    _stops(root, args, rid, "V5")
    f.write_bytes(orig + b"# other\n"); _stops(root, args, rid, "V5")                                            # 表外內容 → 仍停止
    f.write_bytes(orig); _finish(root, rid, snap)                                                                # 恢復成 before

def test_ac_09_83_2_r_no_change_path_changed_then_repaired():
    """AC-09-83 ②：R 的 no_change 路徑（未修改的 runs/_audit.log）被外部改動 → 兩種入口 V5 停止；恢復成記錄值 → 完成。"""
    root, info, x, rp, rid, args, rs, snap = _r_at_fp_r1()
    nc = next(n for n in rp["no_change"] if n["path"] == "runs/_audit.log")
    f = P(root, nc["path"]); orig = f.read_bytes(); assert U.sha(f) == nc["content_sha256"]
    f.write_bytes(orig + b"external\n"); _stops(root, args, rid, "V5")
    f.write_bytes(orig); _finish(root, rid, snap)

def test_ac_09_83_done_step_changed_repair_table():
    """AC-09-83 修復表：有完成紀錄的步驟（CLR 的 restore）被外部改動 → 停止；恢復成 before（移轉後的內容）→ 仍停止；恢復成 after → 完成。"""
    root, info, x, rp, rid, args, rs, snap = _r_at_fp_r1()
    s = rs[0]; f = P(root, s["path"]); after = f.read_bytes()
    bk = P(root, f"operations/_global/{x}/backup/{s['path']}"); assert bk.read_bytes() == after
    f.write_bytes(after + b"# external\n"); _stops(root, args, rid, "V5")
    xpost = next(e for e in U.load(root, f"operations/_global/{x}/manifest.yaml")["restore"] if e["path"] == s["path"])["planned_post_sha256"]
    blob = P(root, f"operations/_global/{x}/blobs/{xpost}"); f.write_bytes(blob.read_bytes()); assert U.sha(f) == s["expected_before"]
    _stops(root, args, rid, "V5")                                                                               # 恢復成 before → 仍停止
    f.write_bytes(after); _finish(root, rid, snap)                                                               # 恢復成 after → 完成

def test_ac_09_83_unauthorized_after_limits():
    """AC-09-83「未授權的恢復成 after」（已揭露的外部寫入限制，不是授權的修復方式；以故障注入造出）：
    (a) 前面還有未執行步驟的非相鄰步驟被改成 after → L 被往後推，前面的步驟被判為衝突／外部修改，停止；
    (b) 目前已執行前綴的下一步被改成 after → 被當成合法尾端，補寫完成紀錄後繼續完成（測試斷言這個行為，屬外部寫入限制）。"""
    root, info, x, rp, rid, args, rs, snap = _r_at_fp_r1()
    nxt, far = rs[2], rs[4]
    assert far["expected_after"] is None and nxt["expected_after"] is None                                     # remove 步驟：after = 不存在
    f = P(root, far["path"]); orig = f.read_bytes(); f.unlink()                                                  # (a)
    r = U.q(root, "operation", "resume", rid); assert r.returncode != 0 and nxt["path"] in r.stderr, r.stderr
    assert classify(root, rid)["status"][nxt["seq"]] == "external_change" and status_files(root, rid) == []
    f.write_bytes(orig)                                                                                          # 恢復成 before
    P(root, nxt["path"]).unlink()                                                                                # (b)
    cls = classify(root, rid); assert cls["status"][nxt["seq"]] == "tail"
    _finish(root, rid, snap); assert prog(root, rp, nxt).is_file()

# ======================================================================== 標記與兩次檢查（AC-09-84 ②～⑦）
def test_ac_09_84_2_partial_x_marker_in_no_change():
    """AC-09-84 ②：部分移轉（X 沒寫到標記）→ rollback：R 沒有標記步驟、標記在 R 的 no_change（不存在）；X 未完成，terminal 只有 Rt2。
    檢查 A、B 時斷言各群組的狀態（標記都不存在）；完成後再送寫入請求，第 0 步不把它當終態不一致。"""
    root, info, x, xp, _, snap = partial_x(CLR_STEP); args = rb_args(x)
    assert U.q(root, *args, fault="after_check_a").returncode == 86
    rp = _r_plan(root); rid = rp["op_id"]; g = G(rp)
    assert g["marker"] == [] and {"path": MARKER, "kind": "business", "content_sha256": None} in rp["no_change"]
    assert [s["step_id"] for s in g["terminal"]] == ["completed"]
    assert all(done(root, rp, s) for s in g["takeover"] + g["restore"]) and not P(root, MARKER).exists() and not P(root, g["terminal"][0]["path"]).exists()
    assert U.q(root, "operation", "resume", rid, fault="after_check_b").returncode == 86
    assert not P(root, MARKER).exists() and not P(root, g["terminal"][0]["path"]).exists()
    ok(U.q(root, "operation", "resume", rid)); ok(U.q(root, "migrate", "verify", "--rolled-back")); assert_like_55(snap, root)
    ok(U.q(root, "maintenance", "end", "--by", "m")); ok(U.q(root, "maintenance", "start", "--by", "m", "--new-request"))   # 第 0 步通過
    ok(U.q(root, "operation", "list"))

@pytest.mark.parametrize("point", ["check_a_passed", "marker_tail", "marker_done"])
@pytest.mark.parametrize("entry", ["resend", "resume"])
def test_ac_09_84_3_4_5_which_check_runs_on_resume(point, entry):
    """AC-09-84 ③ 檢查 A 通過後、標記刪除前；④ 標記已刪、完成紀錄未寫；⑤ 標記的完成紀錄已寫、終態未寫（已完成的 X）。
    兩種入口續做：③ 重新執行檢查 A（before_check_a 故障點被觸發）；④⑤ 不執行檢查 A（before_check_a 不觸發），只執行檢查 B（before_check_b 觸發）。
    每個點先斷言群組狀態；完成後 verify 通過。"""
    root, info = migrated(); x = x_of(root); args = rb_args(x); snap = None
    assert U.q(root, *args, fault="after_register").returncode == 86
    rp = _r_plan(root); rid = rp["op_id"]; g = G(rp); m = g["marker"][0]
    fault = {"check_a_passed": "after_check_a", "marker_tail": f"after_output:{m['seq']}", "marker_done": f"after_progress:{m['seq']}"}[point]
    assert U.q(root, "operation", "resume", rid, fault=fault).returncode == 86
    assert all(done(root, rp, s) for s in g["takeover"] + g["restore"]) and all(not P(root, s["path"]).exists() for s in g["terminal"])
    if point == "check_a_passed":
        assert before(root, rp, m)
        assert go(root, entry, args, rid, fault="before_check_a").returncode == 86                             # 重新執行檢查 A
        assert before(root, rp, m)
        ok(go(root, entry, args, rid))
    else:
        assert out_after(root, m) and prog(root, rp, m).is_file() == (point == "marker_done")
        assert go(root, entry, args, rid, fault="before_check_b").returncode == 86                             # 檢查 B 會執行
        assert done(root, rp, m) and all(not P(root, s["path"]).exists() for s in g["terminal"])
        r = go(root, entry, args, rid, fault="before_check_a"); assert r.returncode == 0, r.stderr              # 檢查 A 不執行
    assert status_files(root, x) == ["completed", "rolled_back"] and status_files(root, rid) == ["completed"]
    ok(U.q(root, "migrate", "verify", "--rolled-back"))

def test_ac_09_84_6_marker_of_other_op_at_check_a():
    """AC-09-84 ⑥（防禦性、函式層故障注入；不屬於正式流程）：R 停在檢查 A 之前，續做時讓檢查 A 讀到的標記屬於其他 op
    （只在 check_a 期間替換 operation.marker；V5 與 resume_states 讀到真實標記）。預期：檢查 A 停止、標記不刪除；之後正常續做完成。"""
    root, info = migrated(); x = x_of(root)
    assert U.q(root, *rb_args(x), fault="before_check_a").returncode == 86
    rid = _r_plan(root)["op_id"]; mk = P(root, MARKER).read_bytes()
    code = f"""
from tools.qaos import migrate as M, operation as O
orig = M.check_a
def wrapped(plan, xplan, manifest):
    real = O.marker
    O.marker = lambda: {{**(real() or {{}}), "migrate_op_id": "0" * 64}}
    try: return orig(plan, xplan, manifest)
    finally: O.marker = real
M.check_a = wrapped
try: O.resume('{rid}'); print("NO-STOP")
except O.EvidenceConflict as e: print("STOP", e)
"""
    out = U.py(root, code).stdout
    assert "STOP 檢查 A 停止" in out and "不刪除" in out, out
    assert P(root, MARKER).read_bytes() == mk and status_files(root, rid) == [] and U.q(root, "maintenance", "end", "--by", "m").returncode != 0
    ok(U.q(root, "operation", "resume", rid)); ok(U.q(root, "migrate", "verify", "--rolled-back"))

@pytest.mark.parametrize("what", ["restore_output", "untouched"])
def test_ac_09_84_7_change_before_check_a(what):
    """AC-09-84 ⑦：R 中止在 restore 群組完成之後、檢查 A 之前，續做前故障注入改動 ⑦a 一個有完成紀錄的 restore 輸出（CLR）、⑦b 一個 untouched 路徑。
    預期：⑦a 在 V5 停止，沒有到達檢查 A；⑦b V5 通過，在檢查 A 停止。兩種入口都斷言：標記保留、沒有終態紀錄、maintenance end 拒絕；修復後完成。"""
    root, info = migrated(); x = x_of(root); args = rb_args(x)
    assert U.q(root, *args, fault="before_check_a").returncode == 86
    rp = _r_plan(root); rid = rp["op_id"]; g = G(rp)
    assert all(done(root, rp, s) for s in g["takeover"] + g["restore"]) and before(root, rp, g["marker"][0])
    p = P(root, f"clarifications/demo/AUTH/{info['clr']}.yaml" if what == "restore_output" else SPEC_YAML); orig = p.read_bytes()
    p.write_bytes(orig + b"# external\n")
    for cmd in (args, ["operation", "resume", rid]):
        r = U.q(root, *cmd); assert r.returncode != 0, r.stderr
        if what == "restore_output": assert "V5" in r.stderr and "檢查 A" not in r.stderr, r.stderr
        else: assert "檢查 A" in r.stderr and "V5" not in r.stderr, r.stderr
        assert P(root, MARKER).exists() and all(not P(root, s["path"]).exists() for s in g["terminal"])
    assert U.q(root, "maintenance", "end", "--by", "m").returncode != 0
    p.write_bytes(orig)                                                                                          # 模擬經授權的人工修復：⑦a 恢復成 after、⑦b 恢復成記錄值
    ok(U.q(root, "operation", "resume", rid)); ok(U.q(root, "migrate", "verify", "--rolled-back"))

# ======================================================================== 終態階段（AC-09-85 ①～⑤）
@pytest.mark.parametrize("point", ["after_check_b", "rt1_tail", "rt1_done", "partial_after_check_b"])
@pytest.mark.parametrize("entry", ["resend", "resume"])
def test_ac_09_85_terminal_phase(point, entry):
    """AC-09-85 ① 檢查 B 通過後、Rt1 寫入前；② Rt1 已寫、完成紀錄未寫；③ Rt1 完成紀錄已寫、Rt2 未寫；⑤ 部分移轉（terminal 只有 Rt2）重做 ①。
    每例先斷言群組狀態；兩種入口續做：第 0 步通過；不執行檢查 A（before_check_a 不觸發）；再執行一次檢查 B（before_check_b 觸發）；
    Rt1、Rt2 各只有一個、Rt1 不重寫；verify 通過。"""
    if point == "partial_after_check_b": root, info, x, _, _, _ = partial_x(CLR_STEP)
    else: root, info = migrated(); x = x_of(root)
    args = rb_args(x); assert U.q(root, *args, fault="after_register").returncode == 86
    rp = _r_plan(root); rid = rp["op_id"]; g = G(rp); term = g["terminal"]
    if point == "partial_after_check_b": assert [s["step_id"] for s in term] == ["completed"] and g["marker"] == []
    else: assert [s["step_id"] for s in term] == ["Rt1", "completed"]
    rt1 = term[0] if len(term) == 2 else None
    fault = {"after_check_b": "after_check_b", "partial_after_check_b": "after_check_b", "rt1_tail": f"after_output:{term[0]['seq']}", "rt1_done": f"after_progress:{term[0]['seq']}"}[point]
    assert U.q(root, "operation", "resume", rid, fault=fault).returncode == 86
    assert all(done(root, rp, s) for s in g["takeover"] + g["restore"] + g["marker"]) and not P(root, MARKER).exists()
    assert not P(root, term[-1]["path"]).exists()
    if rt1:
        if point == "after_check_b": assert before(root, rp, rt1)
        else: assert out_after(root, rt1) and prog(root, rp, rt1).is_file() == (point == "rt1_done")
    ino = P(root, rt1["path"]).stat().st_ino if rt1 and P(root, rt1["path"]).exists() else None
    if rt1 is None:                                                                                              # ⑤：marker 群組是空的
        # §13.7 續做表「marker 群組是空的」那一列：檢查 A（標記必須不存在）→ 檢查 B → terminal。R 沒有可持久化的「檢查 B 已通過」證據，
        # 所以續做時會重新執行檢查 A；這和 AC-09-85 ⑤「不執行檢查 A」的文字不一致（規格內部不一致，見 P6-G2 回報），這裡斷言實作依 §13.7 表的行為。
        assert go(root, entry, args, rid, fault="before_check_a").returncode == 86
    assert go(root, entry, args, rid, fault="before_check_b").returncode == 86                                 # 再執行一次檢查 B
    r = go(root, entry, args, rid, fault=None if rt1 is None else "before_check_a"); assert r.returncode == 0, r.stderr   # ①②③：不執行檢查 A；完成
    if ino is not None: assert P(root, rt1["path"]).stat().st_ino == ino                                         # Rt1 不重寫
    assert status_files(root, rid) == ["completed"]
    assert status_files(root, x) == (["completed", "rolled_back"] if rt1 else ["aborted_for_rollback"])
    ok(U.q(root, "migrate", "verify", "--rolled-back"))

@pytest.mark.parametrize("what", ["restore_output", "untouched"])
def test_ac_09_85_4_change_in_terminal_phase(what):
    """AC-09-85 ④：③ 的狀態（Rt1 完成紀錄已寫、Rt2 未寫），續做前故障注入改動 ④a 一個有完成紀錄的 restore 輸出、④b 一個 untouched 路徑。
    預期：④a 在 V5 停止、沒有到達檢查 B；④b V5 通過、在檢查 B 停止。兩種入口：Rt1 不重寫、Rt2 不寫、R 保持 in_progress、maintenance end 拒絕；
    Rt1 已記錄的 X 終態不撤回。依修復表恢復（④a 恢復成 after，④b 恢復成記錄值；模擬經授權的處理）之後續做完成。"""
    root, info = migrated(); x = x_of(root); args = rb_args(x)
    assert U.q(root, *args, fault="after_register").returncode == 86
    rp = _r_plan(root); rid = rp["op_id"]; rt1, rt2 = G(rp)["terminal"]
    assert U.q(root, "operation", "resume", rid, fault=f"after_progress:{rt1['seq']}").returncode == 86
    assert done(root, rp, rt1) and not P(root, rt2["path"]).exists()
    keep = (P(root, rt1["path"]).read_bytes(), P(root, rt1["path"]).stat().st_ino)
    p = P(root, f"clarifications/demo/AUTH/{info['clr']}.yaml" if what == "restore_output" else SPEC_YAML); orig = p.read_bytes()
    p.write_bytes(orig + b"# external\n")
    for cmd in (args, ["operation", "resume", rid]):
        r = U.q(root, *cmd); assert r.returncode != 0
        if what == "restore_output": assert "V5" in r.stderr and "檢查 B" not in r.stderr, r.stderr
        else: assert "檢查 B" in r.stderr and "V5" not in r.stderr, r.stderr
        assert (P(root, rt1["path"]).read_bytes(), P(root, rt1["path"]).stat().st_ino) == keep and not P(root, rt2["path"]).exists()
    assert status_files(root, rid) == [] and status_files(root, x) == ["completed", "rolled_back"]
    assert U.q(root, "maintenance", "end", "--by", "m").returncode != 0
    p.write_bytes(orig)
    ok(U.q(root, "operation", "resume", rid)); ok(U.q(root, "migrate", "verify", "--rolled-back"))

# ======================================================================== migrate verify 各類的逐項負例（§12）
def _mut_cases_post(root, info, x):
    xp = U.plan_of(root, x); man = U.load(root, f"operations/_global/{x}/manifest.yaml")
    ev = next(s for s in xp["steps"] if s["kind"] == "event")
    idx_pre = next(u["path"] for u in man["untouched"] if "/index.d/" in u["path"])
    return [("restore", f"clarifications/demo/AUTH/{info['clr']}.yaml", "append"),
            ("remove 被改", f"testcases/_bindings/{info['tcs'][0]}-v1.yaml", "append"),
            ("remove 缺失", META, "delete"),
            ("retain_audit backup", man["restore"][0]["backup_path"], "delete"),
            ("retain_audit 清單", f"operations/_global/{x}/manifest.yaml", "append"),
            ("planned_audit 事件", ev["path"], "delete"),
            ("planned_audit completed", f"operations/_global/status.d/{x}-completed.yaml", "delete"),
            ("shared_control 鎖檔", "locks/qaos-operation.lock", "delete"),
            ("shared_control 既有 index.d", idx_pre, "append"),
            ("untouched", SPEC_YAML, "append"),
            ("其他：標記", MARKER, "delete")]

def _mutate(root, rel, how):
    f = P(root, rel); orig = f.read_bytes() if f.exists() else None
    if how == "append": f.write_bytes(orig + b"# tampered\n")
    elif how == "delete": f.unlink()
    elif how.startswith("create:"): f.parent.mkdir(parents=True, exist_ok=True); f.write_bytes(how[7:].encode())
    return orig

def _restore(root, rel, orig):
    f = P(root, rel)
    if orig is None: f.unlink()
    else: f.write_bytes(orig)

def _verify_each(root, cases, flag):
    ok(U.q(root, "migrate", "verify", *flag))
    fails = []
    for label, rel, how in cases:                                                                               # 竄改（各類一例），驗證後恢復
        orig = _mutate(root, rel, how)
        r = U.q(root, "migrate", "verify", *flag)
        if r.returncode == 0: fails.append(label)
        _restore(root, rel, orig)
        ok(U.q(root, "migrate", "verify", *flag))
    assert fails == [], f"verify 沒有發現：{fails}"

def test_verify_after_migrate_each_category():
    """§12 移轉後：restore、remove、retain_audit（backup、清單）、planned_audit（事件、completed）、shared_control（鎖檔、既有 index.d）、untouched、
    其他（標記）各一個竄改例 → verify 失敗；恢復後通過。"""
    root, info = migrated(); x = x_of(root)
    _verify_each(root, _mut_cases_post(root, info, x), [])

def test_verify_after_rollback_each_category():
    """§12 回復後（已完成的 X）：restore 不等於 pre、remove 又出現、X 的 retain_audit（事件）、R 的 retain_audit（完成紀錄、接管事件、Rt1、completed）、
    shared_control（多一個終態、鎖檔）、untouched、其他（標記又出現）各一例 → verify --rolled-back 失敗；恢復後通過。"""
    root, info = migrated(); x = x_of(root); mk = P(root, MARKER).read_text()
    ok(U.q(root, *rb_args(x)))
    xp = U.plan_of(root, x); rp = _r_plan(root); rid = rp["op_id"]; g = G(rp)
    xev = next(s for s in xp["steps"] if s["kind"] == "event")
    cases = [("restore", f"clarifications/demo/AUTH/{info['clr']}.yaml", "append"),
             ("remove", META, "create:x: 1\n"),
             ("X retain_audit 事件", xev["path"], "delete"),
             ("R 完成紀錄", prog(root, rp, g["restore"][0]).relative_to(P(root)).as_posix(), "delete"),
             ("R 接管事件", g["takeover"][-1]["path"], "append"),
             ("R 的 Rt1", g["terminal"][0]["path"], "delete"),
             ("R completed", g["terminal"][-1]["path"], "delete"),
             ("shared_control 多一個終態", f"operations/_global/status.d/{x}-aborted_for_rollback.yaml", f"create:op_id: {x}\n"),
             ("shared_control 鎖檔", "locks/qaos-operation.lock", "delete"),
             ("untouched", SPEC_YAML, "append"),
             ("其他：標記仍存在", MARKER, "create:" + mk)]
    _verify_each(root, cases, ["--rolled-back"])
    assert U.q(root, "maintenance", "end", "--by", "m", fault="after_register").returncode == 86                # 其他：有未完成的計畫
    r = U.q(root, "migrate", "verify", "--rolled-back"); assert r.returncode != 0 and "未完成的計畫" in r.stdout, r.stdout

def test_verify_after_partial_rollback_planned_audit_must_stay_absent():
    """§12 回復後（X 未完成）：not_executed 步驟的預定事件、完成紀錄，以及 `status.d/<X>-completed` 出現 → 列為證據衝突；移除後通過。"""
    root, info, x, xp, _, _ = partial_x(CLR_STEP)
    ok(U.q(root, *rb_args(x)))
    ev = next(s for s in xp["steps"] if s["kind"] == "event")                                                    # MIGRATE 事件在標記之後：未執行
    tc = next(s for s in xp["steps"] if s["path"].startswith("testcases/_bindings/"))
    assert not P(root, ev["path"]).exists() and not prog(root, xp, tc).exists()
    cases = [("未執行的預定事件", ev["path"], "create:x: 1\n"),
             ("未執行步驟的完成紀錄", prog(root, xp, tc).relative_to(P(root)).as_posix(), "create:x: 1\n"),
             ("X 未完成卻有 completed", f"operations/_global/status.d/{x}-completed.yaml", f"create:op_id: {x}\n")]
    _verify_each(root, cases, ["--rolled-back"])

# ======================================================================== AC-09-89 (b)：舊 run 依固定 pin 續做
T2_T3 = """
from tools.qaos import engine, store
from tests import helpers as H
tcs, _ = H.draft_set(prefix="01CX5ZZKBKACTAV9WEVGEMMVR")
rmid = store.load("artifacts/requirements/SPEC-AUTH-001/v1.0/requirements.yaml")["source_artifact_id"]
refs_ = [{{"entity_type": "Requirement", "id": r}} for r in ["REQ-AUTH-001", "REQ-AUTH-002", "REQ-AUTH-003", "REQ-AUTH-004"]]
did, pd = H.write_artifact("{rid}", "T2", "agent-test-designer", "TestCaseDraft", {{"mode": "spec", "spec_id": "SPEC-AUTH-001", "spec_version": "1.0", "testcases": tcs}}, refs_, {{"type": "RequirementModel", "ids": [rmid]}}, "test-design")
_, pr = H.write_artifact("{rid}", "T2", "agent-test-designer", "TestDesignReport", H.design_report(did, tcs), [{{"entity_type": "Artifact", "id": did}}], {{"type": "TestCaseDraft", "ids": [did]}}, "test-design")
assert engine.submit("{rid}", "T2", str(pd))[0] and engine.submit("{rid}", "T2", str(pr))[0]
assert engine.evaluate_gate("{rid}", "T2")["result"] == "PASS"
_, pv = H.write_artifact("{rid}", "T3", "agent-test-validator", "TestValidationReport", H.validation_report(did, rmid, "PASS"), [{{"entity_type": "Artifact", "id": did}}, {{"entity_type": "Artifact", "id": rmid}}], {{"type": "TestCaseDraft", "ids": [did]}}, "validation")
assert engine.submit("{rid}", "T3", str(pv))[0]
"""

@pytest.mark.parametrize("entry", ["resend", "resume"])
def test_ac_09_89_b_old_run_resumes_on_fixed_r000_pin(entry):
    """AC-09-89 (b)：接續 AC-09-88／89(a)（移轉後 declare-empty，decl_rev 變 1；另以新 run 產生內容不同的 R001）。
    綁定 R000 的舊 run（移轉前就在跑）的 T3 gate 中止（故障注入）→ 兩種入口續做。
    預期：續做使用計畫中固定的 R000 pin（計畫檔不變、新 TC 版本綁 R000、不是最新的 R001）；不重算、不改寫 R000.meta.yaml 與 run sidecar。"""
    root, info = migrated(); ok(U.q(root, "maintenance", "end", "--by", "m")); rid = info["running"]
    meta = P(root, META).read_bytes(); sc = P(root, f"artifacts/requirements/_bindings/{rid}.yaml").read_bytes()
    ok(U.q(root, "spec", "reference", "declare-empty", "SPEC-AUTH-001@1.0", "--reason", "x", "--by", "o"))
    U.py(root, "from tests import p3_flow as F\nr = F.new_run(); F.analyze(r, drop=('REQ-AUTH-004',))")             # 最新 revision R001（沒有 REQ-AUTH-004）
    assert P(root, "artifacts/requirements/SPEC-AUTH-001/v1.0/revisions/R001.yaml").exists()
    U.py(root, T2_T3.format(rid=rid))
    r = U.py(root, f"from tools.qaos import engine\nengine.evaluate_gate('{rid}', 'T3')", fault="after_output:1", check=False); assert r.returncode == 86
    op_ = U.incomplete(root)[0]["op_id"]; pf = next(P(root).glob(f"operations/*/{op_}.yaml")); pbytes = pf.read_bytes()
    plan = yaml.safe_load(pbytes); assert plan["action"] == "evaluate_gate"
    if entry == "resend": U.py(root, f"from tools.qaos import engine\nprint(engine.evaluate_gate('{rid}', 'T3')['result'])")
    else: ok(U.q(root, "operation", "resume", op_))
    assert pf.read_bytes() == pbytes and U.incomplete(root) == [] and status_files(root, op_) == ["completed"]
    assert P(root, META).read_bytes() == meta and P(root, f"artifacts/requirements/_bindings/{rid}.yaml").read_bytes() == sc
    new_tcs = [s["path"] for s in plan["steps"] if s["path"].startswith("testcases/versions/")]
    assert new_tcs and all(U.load(root, p)["requirement_model_revision"]["revision"] == "R000" for p in new_tcs)
    assert U.load(root, f"runs/{rid}/run.yaml")["status"] == "WAITING_HUMAN"

# ======================================================================== AC-07-80、82（migrate verify 的部分）
def test_ac_07_80_82_full_flow_with_verify_and_readonly_without_lock():
    """AC-07-80：maintenance start → migrate → migrate verify → maintenance end，全部成功，end 之後是 S_post。
    AC-07-82：S_maint 中唯讀指令與 migrate verify 照常執行；verify 不取鎖（另一個 executor 持有鎖、以 QAOS_PAUSE 停在 after_lock 時仍可執行）。"""
    root, info = legacy()
    ok(U.q(root, "maintenance", "start", "--by", "m")); ok(U.q(root, "migrate", "--by", "m", "--acknowledge-idle", info["running"]))
    ok(U.q(root, "migrate", "verify"))
    for cmd in (["operation", "list"], ["trace", "SPEC-AUTH-001"]): ok(U.q(root, *cmd))
    d = pathlib.Path(tempfile.mkdtemp(prefix="qaos-p6-pause-"))
    holder = subprocess.Popen([sys.executable, "-m", "tools.qaos", "audit", "render"], cwd=U.REPO, env=U.env_for(root, extra={"QAOS_PAUSE": f"after_lock={d}"}),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        t0 = time.monotonic()
        while not (d / "paused").exists():
            assert time.monotonic() - t0 < 30 and holder.poll() is None; time.sleep(0.05)
        r = U.q(root, "migrate", "verify"); assert r.returncode == 0 and "不取鎖" in r.stdout, r.stdout + r.stderr       # 鎖被持有時照常執行
        r = U.q(root, "operation", "list"); assert r.returncode == 0
        assert U.q(root, "maintenance", "end", "--by", "m").returncode != 0                                      # 對照：寫入指令拿不到鎖
    finally:
        (d / "go").write_text("1"); holder.communicate(timeout=60)
    ok(U.q(root, "maintenance", "end", "--by", "m"))
    assert P(root, MARKER).is_file() and not P(root, "locks/maintenance.yaml").exists() and U.incomplete(root) == []
    assert U.py(root, "from tools.qaos import operation as O\nprint(O.system_state())").stdout.strip().splitlines()[-1] == "S_post"

# ======================================================================== AC-09-14 彙整
def test_ac_09_14_existing_run_yaml_revisions_and_tc_versions_unchanged():
    """AC-09-14（彙整）：移轉（acknowledge-idle）、移轉後的宣告與重新分析（產生 R001）、新 run 的設計／驗證／核准（新 TC）一路下來，
    既有的 run.yaml、R(n)、TC 版本檔的 hash 都不變（新增的 sidecar 不算修改）。各 AC 的個別斷言位置見 P6-G2 回報。"""
    root, info = legacy(); r_ = P(root)
    def H(): return {p.relative_to(r_).as_posix(): U.sha(p) for pat in ("runs/*/run.yaml", "testcases/versions/*/v*.yaml", "artifacts/requirements/*/*/revisions/R[0-9][0-9][0-9].yaml") for p in r_.glob(pat)}
    def same(old, new): assert {k: new.get(k) for k in old} == old
    h0 = H()
    L.migrate(root, "--acknowledge-idle", info["running"], check=True); ok(U.q(root, "migrate", "verify"))
    h1 = H(); same(h0, h1); assert set(h1) - set(h0) == {"artifacts/requirements/SPEC-AUTH-001/v1.0/revisions/R000.yaml"}
    assert len(list(r_.glob("testcases/_bindings/*.yaml"))) == len(info["tcs"])                                 # 只新增 sidecar
    ok(U.q(root, "maintenance", "end", "--by", "m"))
    ok(U.q(root, "spec", "reference", "declare-empty", "SPEC-AUTH-001@1.0", "--reason", "x", "--by", "o"))
    rid = U.py(root, "from tests import p3_flow as F\nprint(F.full(prefix='01CX5ZZKBKACTAV9WEVGEMMVR'))").stdout.strip().splitlines()[-1]
    h2 = H(); same(h1, h2)
    assert "artifacts/requirements/SPEC-AUTH-001/v1.0/revisions/R001.yaml" in h2 and f"runs/{rid}/run.yaml" in h2
    assert len([k for k in set(h2) - set(h1) if k.startswith("testcases/versions/")]) >= 1
