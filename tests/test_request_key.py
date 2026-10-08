"""CLI `--request-key` 與 `--json`（ADR-011；review-handoff admin-ui-backend-review R01、R02、R07）。

每個案例一份獨立的暫存 root，以子程序執行 QAOS（才能以 QAOS_FAULT 真的中止程序、比對整個 root 的前後內容）。
故障以 QAOS_FAULT 注入、鎖以 QAOS_PAUSE 持有，都是測試用的同步點。"""
import json, time, pathlib, subprocess, sys, hashlib
import pytest, yaml
from tests import p1_util as U
from tools.qaos import operation

BY = "oscar@example.com"

def snapshot(root) -> dict:
    root = pathlib.Path(root); skip = {operation.OWNER_PATH, operation.LOCK_PATH}
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file() and p.relative_to(root).as_posix() not in skip}

def exe(root, *extra, actual="ok", fault=None):
    return U.q(root, "execution", "import", "--testcase-id", "TC-AUTH-001", "--testcase-version", "1", "--result", "pass", "--environment", "stage",
               "--build", "b1", "--executed-at", "2026-10-08T00:00:00Z", "--actual-result", actual, "--by", BY, *extra, fault=fault)

def evd(root, *extra, text="hello", fault=None):
    return U.q(root, "evidence", "add", "--type", "log", "--inline", text, "--by", BY, *extra, fault=fault)

def js(r) -> dict:
    """--json：stdout 必須剛好是一行、一個 JSON 物件。"""
    lines = r.stdout.splitlines()
    assert len(lines) == 1, (r.stdout, r.stderr)
    return json.loads(lines[0])

def key_index(root, key):
    p = pathlib.Path(root) / operation.request_key_path(key)
    return yaml.safe_load(p.read_text(encoding="utf-8")) if p.is_file() else None

# ---------------------------------------------------------------- 1. 同 key 重送已完成 → completed、沒有寫入
def test_same_key_completed_replay_no_write():
    root = U.mkroot()
    a = js(exe(root, "--request-key", "admin:testrun-1/result-1/exe", "--json"))
    assert a["ok"] and a["outcome"] == "new" and a["request_key"] == "admin:testrun-1/result-1/exe"
    exe_id = a["ids"]["execution_id"]; assert exe_id.startswith("EXE-") and a["result"] == exe_id and a["action"] == "execution_import"
    assert key_index(root, "admin:testrun-1/result-1/exe") == {"request_key": "admin:testrun-1/result-1/exe", "op_id": a["op_id"]}
    before = snapshot(root)
    r = exe(root, "--request-key", "admin:testrun-1/result-1/exe", "--json"); b = js(r)
    assert b["ok"] and b["outcome"] == "completed" and b["op_id"] == a["op_id"] and b["ids"] == {"execution_id": exe_id}
    assert "換一個新的 --request-key" in r.stderr                                    # 給人看的提示改到 stderr
    assert snapshot(root) == before
    assert len(list((root / "executions").rglob("EXE-*.yaml"))) == 1

# ---------------------------------------------------------------- 2. 中斷後同 key 重送 → resumed，不被 3b 擋
@pytest.mark.parametrize("point", ["after_plan_save", "after_register", "after_output:1", "before_completed"])
def test_same_key_resumes_after_crash(point):
    root = U.mkroot()
    r = exe(root, "--request-key", "k1", fault=point); assert r.returncode == 86, (r.stdout, r.stderr)
    blocked = js(evd(root, "--json"))                                                # 沒有 key 的其他請求被 3b 擋下，附上未完成的 op
    assert blocked["ok"] is False and blocked["error_kind"] == "incomplete_plan" and len(blocked["incomplete_ops"]) == 1
    op = blocked["incomplete_ops"][0]
    assert key_index(root, "k1") == {"request_key": "k1", "op_id": op}             # 計畫保存之前就已綁定
    out = js(exe(root, "--request-key", "k1", "--json"))
    assert out["ok"] and out["outcome"] == "resumed" and out["op_id"] == op and out["ids"]["execution_id"].startswith("EXE-")
    assert len(list((root / "executions").rglob("EXE-*.yaml"))) == 1
    assert U.q(root, "operation", "list", "--incomplete").stdout.count(op) == 0

def test_crash_after_bind_before_plan_save():
    """綁定之後、計畫保存之前中止：該 op 從未建立。同 key 同內容 → 新建同一個 op；同 key 不同內容 → 改綁到新的 op（ADR-011）。"""
    root = U.mkroot()
    assert exe(root, "--request-key", "kb", fault="after_bind_key").returncode == 86
    first = key_index(root, "kb")["op_id"]
    assert not list((root / "operations").glob(f"*/{first}.yaml"))                 # 沒有計畫
    a = js(exe(root, "--request-key", "kb", "--json"))
    assert a["outcome"] == "new" and a["op_id"] == first
    root2 = U.mkroot()
    assert exe(root2, "--request-key", "kb", fault="after_bind_key").returncode == 86
    stale = key_index(root2, "kb")["op_id"]
    b = js(exe(root2, "--request-key", "kb", "--json", actual="changed"))
    assert b["outcome"] == "new" and b["op_id"] != stale and key_index(root2, "kb")["op_id"] == b["op_id"]
    c = js(exe(root2, "--request-key", "kb", "--json"))                              # 改綁之後，原內容才是「不同內容」
    assert c["error_kind"] == "key_conflict"

def test_bind_tmp_residue_cleaned():
    """綁定途中（暫存檔寫到一半）中止：同一 op 下次綁定時清除本 op、本 key 的暫存檔（故障以 short: 注入）。"""
    root = U.mkroot()
    assert exe(root, "--request-key", "kt", fault="short:bind_key").returncode == 86
    d = root / operation.REQUEST_KEY_DIR
    assert [p for p in d.iterdir() if p.name.startswith(".qaos-tmp-")] and not key_index(root, "kt")
    other = d / ".qaos-tmp-0123456789abcdef-x.yaml-deadbeef"; other.write_text("x")     # 不屬於本 op 的暫存檔：不動
    assert js(exe(root, "--request-key", "kt", "--json"))["outcome"] == "new"
    assert [p.name for p in d.iterdir() if p.name.startswith(".qaos-tmp-")] == [other.name] and key_index(root, "kt")

def test_operation_resume_then_conflict_detected():
    root = U.mkroot()
    assert exe(root, "--request-key", "k2", fault="after_register").returncode == 86
    assert js(exe(root, "--request-key", "k2", "--json", actual="changed"))["error_kind"] == "key_conflict"   # 未完成時就能偵測
    op = [l.split()[-1] for l in U.q(root, "operation", "list", "--incomplete").stdout.splitlines()[1:]][0]
    U.q(root, "operation", "resume", op, check=True)
    assert key_index(root, "k2")["op_id"] == op
    assert js(exe(root, "--request-key", "k2", "--json", actual="changed"))["error_kind"] == "key_conflict"

# ---------------------------------------------------------------- 2b. rollback 接管後 key 仍綁定原 op（第 01 輪 R01）
@pytest.mark.parametrize("point", ["after_plan_save", "after_register"])
def test_key_survives_rollback_takeover(point):
    root = U.mkroot(migrated=False)
    U.q(root, "maintenance", "start", "--by", "t", check=True)
    assert U.q(root, "migrate", "--by", "t", "--request-key", "m1", fault=point).returncode == 86
    x = key_index(root, "m1")["op_id"]                                               # 計畫保存之前就已綁定
    plan = yaml.safe_load(next(root.glob(f"operations/*/{x}.yaml")).read_text(encoding="utf-8"))
    assert plan["action"] == "migrate" and plan["canonical_request"]["request_key"] == "m1"
    same_key_rb = js(U.q(root, "migrate", "rollback", "--op", x, "--by", "t", "--request-key", "m1", "--json"))   # 以 X 的 key 發 rollback
    assert same_key_rb["error_kind"] == "key_conflict"
    U.q(root, "migrate", "rollback", "--op", x, "--by", "t", "--request-key", "r1", check=True)
    assert key_index(root, "m1")["op_id"] == x
    changed = js(U.q(root, "migrate", "--by", "changed", "--request-key", "m1", "--json"))
    assert changed["ok"] is False and changed["error_kind"] == "key_conflict"
    same = js(U.q(root, "migrate", "--by", "t", "--request-key", "m1", "--json"))  # 同內容：X 已終結 → 拒絕
    assert same["ok"] is False and same["error_kind"] == "refused" and "已終結" in same["message"]

def test_index_pointing_to_plan_without_key_is_evidence_conflict():
    """索引指向的計畫沒有帶同一個 key（竄改）→ 證據衝突（internal）；指向不存在的 op → 視為未綁定，同內容重送時改回（竄改）。"""
    root = U.mkroot()
    a = js(exe(root, "--request-key", "kx", "--json")); plain = js(evd(root, "--json"))
    p = root / operation.request_key_path("kx")
    p.write_text(yaml.safe_dump({"request_key": "kx", "op_id": plain["op_id"]}), encoding="utf-8")   # 竄改：指向沒有 key 的計畫
    o = js(exe(root, "--request-key", "kx", "--json")); assert o["error_kind"] == "internal" and "沒有帶這個 key" in o["message"]
    p.write_text(yaml.safe_dump({"request_key": "kx", "op_id": "a" * 64}), encoding="utf-8")         # 竄改：指向不存在的 op
    r = js(exe(root, "--request-key", "kx", "--json"))
    assert r["outcome"] == "completed" and r["op_id"] == a["op_id"] and key_index(root, "kx")["op_id"] == a["op_id"]

# ---------------------------------------------------------------- 3. 同 key 不同內容 → key_conflict、沒有寫入
def test_same_key_different_content_conflict_no_write():
    root = U.mkroot()
    js(exe(root, "--request-key", "k3", "--json"))
    before = snapshot(root)
    r = exe(root, "--request-key", "k3", "--json", actual="changed"); c = js(r)
    assert r.returncode != 0 and c["ok"] is False and c["error_kind"] == "key_conflict" and "已用於不同內容" in c["message"]
    assert snapshot(root) == before
    r = exe(root, "--request-key", "k3", actual="changed")                           # 不帶 --json：一般錯誤訊息
    assert r.returncode != 0 and "已用於不同內容" in r.stderr and snapshot(root) == before

def test_key_conflict_checked_before_incomplete_plan():
    """key 已綁定一個未完成的 op 時，改內容重送 → key_conflict（而不是被 3b 擋下時才發現）。"""
    root = U.mkroot()
    assert exe(root, "--request-key", "k4", fault="after_register").returncode == 86
    c = js(exe(root, "--request-key", "k4", "--json", actual="changed"))
    assert c["error_kind"] == "key_conflict"

# ---------------------------------------------------------------- 4. 不同 key、相同內容 → 兩個 op、兩筆 EXE（R02）
def test_different_keys_same_content_two_ops():
    root = U.mkroot()
    a = js(exe(root, "--request-key", "admin:testrun-1/result-1/exe", "--json"))
    b = js(exe(root, "--request-key", "admin:testrun-2/result-7/exe", "--json"))
    assert a["outcome"] == b["outcome"] == "new" and a["op_id"] != b["op_id"]
    assert a["ids"]["execution_id"] != b["ids"]["execution_id"]
    assert len(list((root / "executions").rglob("EXE-*.yaml"))) == 2
    c = exe(root)                                                                     # 不帶 key：和兩個有 key 的請求都不同
    assert c.returncode == 0 and len(list((root / "executions").rglob("EXE-*.yaml"))) == 3

# ---------------------------------------------------------------- 5. 互斥與格式
def test_request_key_and_new_request_are_exclusive():
    root = U.mkroot(); before = snapshot(root)
    r = exe(root, "--request-key", "k5", "--new-request")
    assert r.returncode == 2 and "not allowed with argument" in r.stderr             # argparse 層級的錯誤（ADR-011：維持原生行為）
    assert snapshot(root) == before

@pytest.mark.parametrize("key", ["", "有中文", "a b", "x" * 129, "a\\b", "k;rm"])
def test_invalid_key_format_refused(key):
    root = U.mkroot(); before = snapshot(root)
    o = js(exe(root, "--request-key", key, "--json"))
    assert o["ok"] is False and o["error_kind"] == "validation" and "格式不符" in o["message"]
    assert snapshot(root) == before

def test_api_rejects_key_with_new_request():
    root = U.mkroot()
    r = U.py(root, "from tools.qaos import cli\ntry: cli.evidence_add('log', 'x', inline='a', new_request=True, request_key='k')\nexcept ValueError as e: print(e)")
    assert "不能同時使用" in r.stdout

# ---------------------------------------------------------------- 6. --json：成功與各種失敗
def test_json_success_ids_and_audit():
    root = U.mkroot()
    o = js(evd(root, "--request-key", "admin:testrun-1/result-1/ev-3", "--json"))
    assert o["ok"] and o["outcome"] == "new" and o["ids"] == {"evidence_id": o["result"]} and o["allocated_ids"] == [o["result"]]
    events = [yaml.safe_load(p.read_text(encoding="utf-8")) for p in (root / "runs/_audit.d").glob(f"{o['op_id']}-*.yaml")]
    assert any(e["action"] == "REQUEST_KEY" and e["detail"] == "admin:testrun-1/result-1/ev-3 → evidence_add" for e in events)
    plain = js(evd(root, "--json", text="other"))                                     # 沒有 key：request_key 為 null，也沒有 REQUEST_KEY 事件
    assert plain["ok"] and plain["request_key"] is None
    ev2 = [yaml.safe_load(p.read_text(encoding="utf-8")) for p in (root / "runs/_audit.d").glob(f"{plain['op_id']}-*.yaml")]
    assert not any(e["action"] == "REQUEST_KEY" for e in ev2)

def test_json_run_new_replay_is_stored_result():
    """completed 回放的是當時存下的結果（ADR-011）：JSON 的 result 不是 run 目前的狀態；人看的目前狀態在 stderr。"""
    root = U.mkroot()
    args = ["run", "new", "regression-generation", "--input", 'target_suites=["smoke"]', "--input", "scope=all", "--input", "trigger=manual", "--by", BY]
    a = js(U.q(root, *args, "--request-key", "rk", "--json"))
    rid = a["ids"]["run_id"]
    U.q(root, "run", "cancel", rid, "--by", BY, check=True)
    r = U.q(root, *args, "--request-key", "rk", "--json"); b = js(r)
    assert b["outcome"] == "completed" and b["ids"]["run_id"] == rid and b["result"]["status"] != "CANCELLED"
    assert f"{rid} CANCELLED" in r.stderr

def test_json_failure_kinds():
    root = U.mkroot()
    v = js(U.q(root, "evidence", "add", "--type", "log", "--by", BY, "--json"))       # 指令層的輸入檢查
    assert v == {"ok": False, "error_kind": "validation", "message": "evidence add 需要 --file 或 --inline", "incomplete_ops": []}
    U.q(root, "id", "REQ", "--area", "JSONX", check=True)
    rf = U.q(root, "id", "REQ", "--area", "JSONX", "--json"); f = js(rf)             # 已配發的 ID 不能重用
    assert rf.returncode != 0 and f["error_kind"] == "refused" and "REQ-JSONX-001" in f["message"]
    U.q(root, "maintenance", "start", "--by", BY, check=True)
    m = js(evd(root, "--json"))
    assert m["error_kind"] == "maintenance" and "維護中" in m["message"]
    U.q(root, "maintenance", "end", "--by", BY, check=True)
    ro = js(U.q(root, "tc-export", "AUTH", "--stdout", "--json"))
    assert ro["error_kind"] == "validation"

def test_json_locked(tmp_path):
    root = U.mkroot(); d = tmp_path / "p"
    holder = subprocess.Popen([sys.executable, "-m", "tools.qaos", "evidence", "add", "--type", "log", "--inline", "x", "--by", BY], cwd=U.REPO,
                              env=U.env_for(root, extra={"QAOS_PAUSE": f"after_lock={d}"}), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        end = time.monotonic() + 20
        while not (d / "paused").exists():
            assert time.monotonic() < end; time.sleep(0.02)
        r = evd(root, "--json", text="y"); o = js(r)
        assert r.returncode != 0 and o["error_kind"] == "locked"
    finally:
        (d / "go").write_text("1"); holder.communicate(timeout=60)

def test_json_gate_like_nonzero_exit_keeps_code(monkeypatch, capsys):
    """寫入成功、但指令以非零結束（例如 gate FAIL）：ok=true，exit_code 照舊（程序內 monkeypatch）。"""
    from tools.qaos import cli, engine
    def fake(*a, **k):
        operation.LAST_OUTCOME.clear()
        operation.LAST_OUTCOME.update(kind="new", op_id="a" * 64, action="evaluate_gate", request_key="g1", result={"result": "FAIL"}, allocated_ids=[])
        return {"gate": "G-TVAL", "layer": "semantic", "result": "FAIL", "issues": ["x"]}
    monkeypatch.setattr(engine, "evaluate_gate", fake)
    monkeypatch.setattr(engine, "load_run", lambda rid: {"status": "RUNNING", "current_task_id": "T2", "waiting_on_approval_id": None})
    with pytest.raises(SystemExit) as e: cli.main(["gate", "RUN-X", "T3", "--request-key", "g1", "--json"])
    out = capsys.readouterr()
    o = json.loads(out.out)
    assert e.value.code == 1 and o["ok"] is True and o["exit_code"] == 1 and o["result"] == {"result": "FAIL"}
    assert "G-TVAL semantic FAIL" in out.err

def test_json_internal_on_unexpected_exception(monkeypatch, capsys):
    from tools.qaos import cli, engine
    def boom(*a, **k): raise KeyError("x")
    monkeypatch.setattr(engine, "cancel", boom)
    with pytest.raises(SystemExit) as e: cli.main(["run", "cancel", "RUN-X", "--by", BY, "--json"])
    o = json.loads(capsys.readouterr().out)
    assert e.value.code == 1 and o["ok"] is False and o["error_kind"] == "internal" and "KeyError" in o["message"]

# ---------------------------------------------------------------- 7. 不帶新參數：行為不變（另見既有測試）
def test_without_new_flags_unchanged():
    root = U.mkroot()
    a = exe(root); assert a.returncode == 0 and a.stdout.strip().startswith("EXE-")
    b = exe(root); assert b.stdout.strip() == a.stdout.strip() and "先前已完成的同一請求" in b.stderr and "加 --new-request" in b.stderr
    assert not (root / operation.REQUEST_KEY_DIR).exists()

# ---------------------------------------------------------------- 第 01 輪 R02～R05
def test_manual_record_id_and_all_counter_kinds_named():
    import re
    from tools.qaos import cli
    kinds = set(re.findall(r'"([A-Z]+)"', re.search(r"def alloc\(.*?raise ValueError", (U.REPO / "tools/qaos/ids.py").read_text(encoding="utf-8"), re.S).group(0)))
    assert kinds - {"ART"} <= set(cli.ID_NAMES), kinds - set(cli.ID_NAMES)            # 每一種計數器 ID 都有名稱
    root = U.mkroot()
    args = ["manual", "new", "--title", "x", "--product", "demo", "--area", "AUTH", "--step", "s", "--observed", "o", "--outcome", "pass", "--by", "t", "--request-key", "rec", "--json"]
    a = js(U.q(root, *args)); assert a["ids"]["manual_record_id"].startswith("MAN-")
    b = js(U.q(root, *args)); assert b["outcome"] == "completed" and b["ids"] == a["ids"]
    m = js(U.q(root, "id", "MAN", "--request-key", "man", "--json")); assert m["ids"]["manual_record_id"] == m["result"]

def test_keyed_id_replay_hint_says_new_key():
    root = U.mkroot()
    U.q(root, "id", "REQ", "--area", "RX", "--request-key", "id1", check=True)
    r = U.q(root, "id", "REQ", "--area", "RX", "--request-key", "id1"); assert r.returncode == 1 and r.stdout == ""
    assert "換一個新的 --request-key" in r.stderr and "--new-request" not in r.stderr
    o = js(U.q(root, "id", "REQ", "--area", "RX", "--request-key", "id1", "--json"))
    assert o["error_kind"] == "refused" and "換一個新的 --request-key" in o["message"]

def test_json_replay_that_reads_current_state_can_fail():
    """ADR-011 §3：回放時人看的輸出讀目前狀態，讀取失敗 → 和不帶 --json 一樣以錯誤結束（validation）；op 仍是 completed。"""
    root = U.mkroot()
    args = ["run", "new", "regression-generation", "--input", 'target_suites=["smoke"]', "--input", "scope=all", "--input", "trigger=manual", "--by", BY, "--request-key", "run1"]
    a = js(U.q(root, *args, "--json"))
    (root / "runs" / a["ids"]["run_id"] / "run.yaml").unlink()                      # 故障情境：實體檔不存在
    r = U.q(root, *args, "--json"); o = js(r)
    assert r.returncode == 1 and o["ok"] is False and o["error_kind"] == "validation"
    assert U.q(root, *args).returncode == 1                                          # 不帶 --json：同樣失敗
    assert "completed" in [l.split()[1] for l in U.q(root, "operation", "list").stdout.splitlines()[1:] if l.split()[-1] == a["op_id"]]

def test_control_precondition_is_refused_not_maintenance():
    root = U.mkroot()                                                                  # 已移轉
    U.q(root, "maintenance", "start", "--by", "t", "--request-key", "maint2", check=True)
    o = js(U.q(root, "migrate", "--by", "t", "--request-key", "migrate2", "--json"))
    assert o["error_kind"] == "refused" and "已移轉" in o["message"]
    assert js(evd(root, "--json"))["error_kind"] == "maintenance"                     # 一般寫入：維護中
    again = js(U.q(root, "maintenance", "start", "--by", "t2", "--json"))
    assert again["error_kind"] == "refused" and "已在維護中" in again["message"]
