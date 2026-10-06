"""P1：flock 全域操作鎖、fork 掛鉤、exec 子程序、context 範圍（最終規格第 4 章 §4；AC-07-64～79）。

同步方式：QAOS_PAUSE=<point>=<dir> 讓 executor 在指定點建立 <dir>/paused，等 <dir>/go 出現才繼續；
77e 以 harness 擁有的具名 FIFO（O_RDWR 開啟並全程保持）、每則訊息固定截止時間（time.monotonic）加緩衝區讀行。"""
import os, sys, json, time, select, signal, pathlib, tempfile, subprocess, textwrap, yaml, pytest
from tests import p1_util as U

PY = sys.executable

def spec_args(v="1.0"):
    return ["spec", "import", U.FIXTURES / f"SPEC-AUTH-001-v{v}.md", "--spec-id", "SPEC-AUTH-001", "--version", v, "--product", "demo", "--area", "AUTH", "--by", "t"]

def popen_q(root, args, pause=None, fault=None):
    extra = {"QAOS_PAUSE": f"{pause[0]}={pause[1]}"} if pause else None
    return subprocess.Popen([PY, "-m", "tools.qaos", *map(str, args)], cwd=U.REPO, env=U.env_for(root, fault, extra),
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

def wait_file(p: pathlib.Path, timeout=20):
    end = time.monotonic() + timeout
    while not p.exists():
        if time.monotonic() > end: raise AssertionError(f"等待 {p} 逾時")
        time.sleep(0.02)

def acquire_once(root) -> str:
    """獨立程序 Q：嘗試取得鎖，立刻釋放；回傳 ok 或 held。"""
    code = "from tools.qaos import operation as op\ntry:\n c=op.acquire(); op.release(c); print('ok')\nexcept op.LockHeld: print('held')"
    return U.py(root, code).stdout.strip()

# ---------------------------------------------------------------- AC-07-64～72
def test_64_70_72_lock_held_same_request_refused_readonly_ok(tmp_path):
    root = U.mkroot(); U.import_auth_spec(root)
    d = tmp_path / "p"; a = popen_q(root, spec_args("1.1"), pause=("after_lock", d))
    try:
        wait_file(d / "paused")
        b = U.q(root, *spec_args("1.1")); assert b.returncode != 0 and "鎖由其他 executor 持有" in b.stderr   # 64：同一請求也拿不到鎖
        assert acquire_once(root) == "held"
        for args in (["operation", "list"], ["trace", "SPEC-AUTH-001"], ["tc-export", "AUTH", "--stdout"], ["run", "show", "RUN-00000000-000"]):
            r = U.q(root, *args); assert "鎖由其他" not in r.stderr, args                                       # 72／73：唯讀不取鎖
        w = U.q(root, "tc-export", "AUTH"); assert w.returncode != 0 and "鎖由其他" in w.stderr                   # 74：寫檔 export 被拒
    finally:
        (d / "go").write_text("1"); out, err = a.communicate(timeout=60)
    assert a.returncode == 0, err

def test_65_two_resumes_only_one_proceeds(tmp_path):
    root = U.mkroot(); args = spec_args()
    assert U.q(root, *args, fault="after_register").returncode == 86
    op = U.incomplete(root)[0]["op_id"]
    d = tmp_path / "p"; r1 = popen_q(root, ["operation", "resume", op], pause=("after_lock", d))
    try:
        wait_file(d / "paused")
        r2 = U.q(root, "operation", "resume", op); assert r2.returncode != 0 and "鎖由其他" in r2.stderr
    finally:
        (d / "go").write_text("1"); r1.communicate(timeout=60)
    assert r1.returncode == 0 and U.incomplete(root) == []

def test_66_different_ops_only_one_acquires(tmp_path):
    root = U.mkroot()
    d = tmp_path / "p"; a = popen_q(root, spec_args("1.0"), pause=("after_lock", d))
    try:
        wait_file(d / "paused")
        b = U.q(root, *spec_args("1.1")); assert b.returncode != 0 and "鎖由其他" in b.stderr
    finally:
        (d / "go").write_text("1"); a.communicate(timeout=60)

def test_67_69_kill9_after_plan_save(tmp_path):
    """67：保存計畫後被 kill -9 → 核心釋放鎖 → 同一請求續做；69：不同 op 被拒並提示 resume。"""
    root = U.mkroot(); args = spec_args()
    d = tmp_path / "p"; a = popen_q(root, args, pause=("after_plan_save", d))
    wait_file(d / "paused"); a.send_signal(signal.SIGKILL); a.wait(timeout=30)
    assert acquire_once(root) == "ok"                                     # 沒有殘留鎖
    c = U.q(root, *spec_args("1.1")); assert c.returncode != 0 and "operation resume" in c.stderr
    assert U.q(root, *args).returncode == 0 and U.incomplete(root) == []

def test_68_kill9_before_plan_save_no_residue(tmp_path):
    root = U.mkroot()
    d = tmp_path / "p"; a = popen_q(root, spec_args(), pause=("after_lock", d))
    wait_file(d / "paused"); a.send_signal(signal.SIGKILL); a.wait(timeout=30)
    assert U.incomplete(root) == [] and U.unregistered_plans(root) == []
    U.q(root, *spec_args("1.1"), check=True)

def test_70_child_write_while_parent_holds_lock_fails_fast():
    root = U.mkroot()
    code = textwrap.dedent(f"""
        import subprocess, sys, time
        from tools.qaos import operation as op
        c = op.acquire()
        t = time.monotonic()
        r = subprocess.run([sys.executable, "-m", "tools.qaos", "tc-export", "AUTH"], capture_output=True, text=True, timeout=30)
        print(r.returncode, round(time.monotonic() - t, 2), "鎖由其他" in r.stderr)
        op.release(c)
    """)
    rc, secs, msg = U.py(root, code).stdout.split()
    assert rc != "0" and msg == "True" and float(secs) < 20

def test_71_stale_owner_file_is_ignored():
    root = U.mkroot()
    (pathlib.Path(root) / "locks/qaos-operation.owner").write_text(yaml.safe_dump({"op_id": "dead", "pid": 999999, "host": "x", "started_at": "old"}))
    U.q(root, *spec_args(), check=True)
    assert yaml.safe_load((pathlib.Path(root) / "locks/qaos-operation.owner").read_text())["op_id"] != "dead"

# ---------------------------------------------------------------- fork 掛鉤（AC-07-77a～d、f、h～k）
FORK_PRELUDE = textwrap.dedent("""
    import os, sys, json, time, subprocess, errno
    from tools.qaos import operation as op
    def fd_closed(fd):
        try: os.fstat(fd); return False
        except OSError as e: return e.errno == errno.EBADF
    def q_acquire():
        r = subprocess.run([sys.executable, "-c", "from tools.qaos import operation as op\\ntry:\\n c=op.acquire(); op.release(c); print('ok')\\nexcept op.LockHeld: print('held')"], capture_output=True, text=True)
        return r.stdout.strip()
    def child_report(ctx):
        rep = {"executor_none": op.current() is None, "fd_closed": fd_closed(ctx.fd)}
        try: op.require_context(ctx); rep["ctx_valid"] = True
        except op.ContextInvalid: rep["ctx_valid"] = False
        try:
            from tools.qaos import store; store.save("x.yaml", {}); rep["write"] = True
        except Exception: rep["write"] = False
        try:
            c2 = op.acquire(); rep["child_acquire"] = "ok"; op.release(c2)
        except op.LockHeld: rep["child_acquire"] = "held"
        return rep
""")

def run_fork(root, body) -> dict:
    return json.loads(U.py(root, FORK_PRELUDE + textwrap.dedent(body)).stdout.strip().splitlines()[-1])

def test_77abc_fork_child_drops_lock_parent_keeps_it():
    root = U.mkroot()
    r = run_fork(root, """
        ctx = op.acquire(); rfd, wfd = os.pipe()
        pid = os.fork()
        if pid == 0:
            os.close(rfd); os.write(wfd, json.dumps(child_report(ctx)).encode()); os.close(wfd); time.sleep(1.5); os._exit(0)
        os.close(wfd); rep = json.loads(os.read(rfd, 65536).decode())
        rep["independent_while_child_alive"] = q_acquire()       # 77a
        os.waitpid(pid, 0); op.release(ctx)
        print(json.dumps(rep))
    """)
    assert r == {"executor_none": True, "fd_closed": True, "ctx_valid": False, "write": False, "child_acquire": "held", "independent_while_child_alive": "held"}

def test_77d_parent_exits_child_alive_lock_free(tmp_path):
    root = U.mkroot(); d = tmp_path / "s"; d.mkdir()
    code = FORK_PRELUDE + textwrap.dedent(f"""
        ctx = op.acquire()
        pid = os.fork()
        if pid == 0:
            open("{d}/child.pid", "w").write(str(os.getpid()))
            while not os.path.exists("{d}/go"): time.sleep(0.02)
            os._exit(0)
        while not os.path.exists("{d}/child.pid"): time.sleep(0.02)
        os._exit(0)                                   # 父程序結束（不釋放）
    """)
    p = subprocess.Popen([PY, "-c", code], cwd=U.REPO, env=U.env_for(root)); p.wait(timeout=30)
    child = int((d / "child.pid").read_text())
    try:
        os.kill(child, 0)                              # 子程序仍存活（只用來確認前提）
        assert acquire_once(root) == "ok"
    finally:
        (d / "go").write_text("1")

def test_77f_multiple_forks_while_holding():
    root = U.mkroot()
    r = run_fork(root, """
        ctx = op.acquire(); reps = []
        for i in range(3):
            rfd, wfd = os.pipe(); pid = os.fork()
            if pid == 0:
                os.close(rfd); rep = {"executor_none": op.current() is None, "fd_closed": fd_closed(ctx.fd)}
                os.write(wfd, json.dumps(rep).encode()); os._exit(0)
            os.close(wfd); reps.append(json.loads(os.read(rfd, 4096).decode())); os.waitpid(pid, 0)
        held = q_acquire(); hooks = op._HOOK_REGISTERED; op.release(ctx)
        print(json.dumps({"reps": reps, "held": held, "hook": hooks}))
    """)
    assert all(x == {"executor_none": True, "fd_closed": True} for x in r["reps"]) and r["held"] == "held" and r["hook"] is True

def test_77h_reacquire_then_fork_closes_current_fd():
    root = U.mkroot()
    r = run_fork(root, """
        c1 = op.acquire(); op.release(c1); c2 = op.acquire()
        rfd, wfd = os.pipe(); pid = os.fork()
        if pid == 0:
            os.close(rfd); os.write(wfd, json.dumps({"closed": fd_closed(c2.fd), "none": op.current() is None}).encode()); os._exit(0)
        os.close(wfd); rep = json.loads(os.read(rfd, 4096).decode()); os.waitpid(pid, 0)
        rep["held"] = q_acquire(); op.release(c2); print(json.dumps(rep))
    """)
    assert r == {"closed": True, "none": True, "held": "held"}

def test_77i_fork_without_lock():
    root = U.mkroot()
    r = run_fork(root, """
        rfd, wfd = os.pipe(); pid = os.fork()
        if pid == 0:
            os.close(rfd)
            try: c = op.acquire(); op.release(c); res = "ok"
            except op.LockHeld: res = "held"
            os.write(wfd, res.encode()); os._exit(0)
        os.close(wfd); res = os.read(rfd, 64).decode(); os.waitpid(pid, 0); print(json.dumps({"child": res}))
    """)
    assert r == {"child": "ok"}

def test_77j_child_reacquires_then_forks_grandchild(tmp_path):
    root = U.mkroot(); d = tmp_path / "s"; d.mkdir()
    code = FORK_PRELUDE + textwrap.dedent(f"""
        ctx = op.acquire()
        pid = os.fork()
        if pid == 0:
            while os.getppid() != 1 and not os.path.exists("{d}/parent_gone"): time.sleep(0.02)
            c = op.acquire()                                     # 父程序已結束：子程序取得自己的鎖
            rfd, wfd = os.pipe(); g = os.fork()
            if g == 0:
                os.close(rfd); os.write(wfd, json.dumps({{"closed": fd_closed(c.fd), "none": op.current() is None}}).encode()); os._exit(0)
            os.close(wfd); rep = json.loads(os.read(rfd, 4096).decode()); os.waitpid(g, 0)
            rep["held"] = q_acquire(); op.release(c)
            open("{d}/result.json", "w").write(json.dumps(rep)); os._exit(0)
        os._exit(0)
    """)
    p = subprocess.Popen([PY, "-c", code], cwd=U.REPO, env=U.env_for(root)); p.wait(timeout=30)
    (d / "parent_gone").write_text("1")
    wait_file(d / "result.json")
    assert json.loads((d / "result.json").read_text()) == {"closed": True, "none": True, "held": "held"}

def test_77k_old_context_refused_after_child_acquires_new(tmp_path):
    root = U.mkroot(); d = tmp_path / "s"; d.mkdir()
    r = run_fork(root, f"""
        ctx1 = op.acquire(); rfd, wfd = os.pipe(); pid = os.fork()
        if pid == 0:
            os.close(rfd)
            while not os.path.exists("{d}/released"): time.sleep(0.02)
            ctx2 = op.acquire(); rep = {{}}
            try: op.require_context(ctx1); rep["old"] = "ok"
            except op.ContextInvalid: rep["old"] = "refused"
            try: op.require_context(ctx2); rep["new"] = "ok"
            except op.ContextInvalid: rep["new"] = "refused"
            op.release(ctx2); os.write(wfd, json.dumps(rep).encode()); os._exit(0)
        os.close(wfd); op.release(ctx1); open("{d}/released", "w").write("1")
        rep = json.loads(os.read(rfd, 4096).decode()); os.waitpid(pid, 0); print(json.dumps(rep))
    """)
    assert r == {"old": "refused", "new": "ok"}

# ---------------------------------------------------------------- 77e：exec 子程序（FIFO 同步）與 dup 對照組
C_SCRIPT = textwrap.dedent("""
    import os, sys, time, select
    ctl, status = os.open(sys.argv[1], os.O_RDWR), os.open(sys.argv[2], os.O_RDWR)
    hold = int(sys.argv[3]) if len(sys.argv) > 3 else None
    buf = b""
    def readline(timeout=10):
        global buf
        deadline = time.monotonic() + timeout
        while b"\\n" not in buf:
            left = deadline - time.monotonic()
            if left <= 0: os._exit(3)
            r, _, _ = select.select([ctl], [], [], left)
            if r: buf += os.read(ctl, 4096)
        line, buf = buf.split(b"\\n", 1); return line.decode()
    os.write(status, f"ready {os.getpid()} {os.getppid()}{' fd=' + str(hold) if hold is not None else ''}\\n".encode())
    while True:
        cmd = readline()
        if cmd == "probe": os.write(status, f"alive {os.getpid()} {os.getppid()}\\n".encode())
        elif cmd == "close-fd": os.close(hold); os.write(status, b"closed\\n")
        elif cmd == "release": os.write(status, b"bye\\n"); os._exit(0)
""")

P_SCRIPT = textwrap.dedent("""
    import os, sys, subprocess
    from tools.qaos import operation as op
    ctx = op.acquire()
    c_script, ctl, status, mode = sys.argv[1:5]
    if mode == "ctrl":
        d = os.dup(ctx.fd)
        subprocess.Popen([sys.executable, c_script, ctl, status, str(d)], pass_fds=(d,))
    else:
        subprocess.Popen([sys.executable, c_script, ctl, status])
    line = sys.stdin.readline()          # 等 harness 指示結束
    os._exit(0)
""")

class Fifo:
    def __init__(self, path): os.mkfifo(path); self.fd = os.open(path, os.O_RDWR); self.buf = b""
    def write(self, s): os.write(self.fd, (s + "\n").encode())
    def readline(self, timeout=5.0):
        deadline = time.monotonic() + timeout
        while b"\n" not in self.buf:
            left = deadline - time.monotonic()
            if left <= 0: raise AssertionError("FIFO 讀取逾時")
            r, _, _ = select.select([self.fd], [], [], left)
            if r: self.buf += os.read(self.fd, 4096)
        line, self.buf = self.buf.split(b"\n", 1); return line.decode()
    def close(self): os.close(self.fd)

@pytest.mark.parametrize("mode,p_exit", [("main", "normal"), ("main", "sigkill"), ("ctrl", "normal")])
def test_77e_exec_child(tmp_path, mode, p_exit):
    root = U.mkroot()
    c_file = tmp_path / "c.py"; c_file.write_text(C_SCRIPT); p_file = tmp_path / "p.py"; p_file.write_text(P_SCRIPT)
    ctl, status = Fifo(str(tmp_path / "ctl")), Fifo(str(tmp_path / "status"))
    P = subprocess.Popen([PY, str(p_file), str(c_file), str(tmp_path / "ctl"), str(tmp_path / "status"), mode], cwd=U.REPO, env=U.env_for(root),
                         stdin=subprocess.PIPE, text=True, start_new_session=True)
    c_pid = None
    try:
        ready = status.readline(10).split(); assert ready[0] == "ready"; c_pid = int(ready[1]); assert int(ready[2]) == P.pid
        if p_exit == "sigkill": P.send_signal(signal.SIGKILL)
        else: P.stdin.write("exit\n"); P.stdin.flush()
        P.wait(timeout=10)
        ctl.write("probe"); alive = status.readline().split()
        assert alive[0] == "alive" and int(alive[1]) == c_pid and int(alive[2]) != P.pid    # C 仍在執行，父程序已改變
        if mode == "main":
            assert acquire_once(root) == "ok"                                                  # O_CLOEXEC：C 沒有鎖 fd
        else:
            assert acquire_once(root) == "held"                                                # 對照組：C 持有同一 open file description
            ctl.write("close-fd"); assert status.readline() == "closed"
            assert acquire_once(root) == "ok"
        ctl.write("release"); assert status.readline() == "bye"
        end = time.monotonic() + 5
        while True:
            try: os.kill(c_pid, 0)
            except ProcessLookupError: break
            if time.monotonic() > end: raise AssertionError("C 沒有結束")
            time.sleep(0.02)
        c_pid = None
    finally:
        for pid in ([c_pid] if c_pid else []):
            try: os.kill(pid, signal.SIGKILL)
            except ProcessLookupError: pass
        if P.poll() is None: P.kill(); P.wait()
        ctl.close(); status.close()

# ---------------------------------------------------------------- AC-07-79：context 的範圍
def test_79_no_context_no_write():
    root = U.mkroot()
    code = textwrap.dedent("""
        from tools.qaos import store, operation as op
        res = {}
        try: store.save("x.yaml", {}); res["direct"] = "written"
        except store.NoExecutorContext: res["direct"] = "refused"
        try: op.require_context(op.Context(token="forged", fd=0, owner_pid=0)); res["forged"] = "ok"
        except op.ContextInvalid: res["forged"] = "refused"
        print(res)
    """)
    out = U.py(root, code).stdout
    assert "'direct': 'refused'" in out and "'forged': 'refused'" in out
    assert not (pathlib.Path(root) / "x.yaml").exists()
