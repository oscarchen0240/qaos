"""tools/legacy_validate_snapshot.py（附錄 A 5-16、§15.1 W1、§15.2 R5、AC-09-64）。

以 legacy fixture（p3_legacy：需求 A 之前的程式碼以正式流程產生的 S_pre 資料；該流程執行時 root 的定義層是新程式的版本）模擬部署與回復的定義層切換：
W1 對照與 R5 時資料 root 的定義層（schemas／agents／workflows／permissions）換成舊程式 f5188b0 的版本，並以 f5188b0 的 bin/qaos 執行；
M2～R3 之間換回新程式的定義層，以新程式正式流程 maintenance start → migrate → migrate rollback → verify --rolled-back；R4 再換成舊定義層、R5 取結果、R6 刪維護檔。"""
import json, os, pathlib, shutil, subprocess, sys, tempfile
import pytest
from tests import p1_util as U, p3_legacy as L

OLD = "f5188b0"
DEFS = ("schemas", "agents", "workflows", "permissions")
TOOL = U.REPO / "tools/legacy_validate_snapshot.py"

def old_program() -> pathlib.Path:
    """f5188b0 的 bin、tools 與定義層（系統暫存目錄的快取；先解壓到臨時目錄再改名，以完成標記判斷是否完整）。"""
    d = pathlib.Path(tempfile.gettempdir()) / f"qaos-old-program-{OLD}"
    if not (d / ".complete").exists():
        tmp = pathlib.Path(tempfile.mkdtemp(prefix=f"qaos-old-program-{OLD}-", dir=d.parent))
        data = subprocess.run(["git", "-C", str(U.REPO), "archive", OLD, "bin", "tools", *DEFS], capture_output=True, check=True).stdout
        subprocess.run(["tar", "-x", "-C", str(tmp)], input=data, check=True)
        (tmp / ".complete").write_text(OLD)
        try: tmp.rename(d)
        except OSError:                                                                       # 另一個程序已完成（或留下不完整的舊目錄）
            if not (d / ".complete").exists(): shutil.rmtree(d, ignore_errors=True); tmp.rename(d)
            else: shutil.rmtree(tmp, ignore_errors=True)
    return d

def use_defs(root: pathlib.Path, src: pathlib.Path):
    for d in DEFS:
        shutil.rmtree(root / d); shutil.copytree(src / d, root / d)

def tool(*args):
    return subprocess.run([sys.executable, str(TOOL), *map(str, args)], cwd=U.REPO, capture_output=True, text=True, timeout=600)

def snap(root, out, program=None):
    r = tool("snapshot", "--root", root, "--program", program or old_program(), "--out", out); assert r.returncode == 0, r.stderr
    return json.loads(pathlib.Path(out).read_text(encoding="utf-8"))

def yaml_load(p):
    import yaml
    return yaml.safe_load(pathlib.Path(p).read_text(encoding="utf-8"))

@pytest.fixture(scope="module")
def world(tmp_path_factory):
    """W1 對照 → M2～R3（新程式）→ R4 → R5 回復後的結果 → R6。回傳 (root, w1 路徑, after 路徑, 資訊)。"""
    out = tmp_path_factory.mktemp("lvs"); old = old_program()
    root, info = L.legacy_root()
    bad = root / f"runs/{info['done']}/entities/m1-fixture.yaml"                              # fixture 建構：一個舊 validate 會判 INVALID 的既有檔（舊 infer 把 runs/ 下的 yaml 都當 run）
    bad.parent.mkdir(parents=True, exist_ok=True); bad.write_text("note: 測試用既有失敗\n" + "".join(f"{'long_unexpected_key_' * 12}{i}: 1\n" for i in range(2)), encoding="utf-8")   # 鍵名夠長，讓錯誤輸出超過 600 字元
    use_defs(root, old)                                                                       # W1：舊程式的定義層
    w1 = out / "w1.json"; snap(root, w1)
    use_defs(root, U.REPO)                                                                    # M2：新程式
    L.migrate(root, "--acknowledge-idle", info["running"])
    x = yaml_load(root / "artifacts/requirements/_migration.yaml")["migrate_op_id"]
    U.q(root, "migrate", "rollback", "--op", x, "--by", "m", check=True)
    U.q(root, "migrate", "verify", "--rolled-back", check=True)
    use_defs(root, old)                                                                       # R4：舊程式
    after = out / "after.json"; snap(root, after)                                             # R5
    (root / "locks/maintenance.yaml").unlink()                                                # R6（人工；locks/ 不在舊 validate 範圍）
    return root, w1, after, {**info, "x": x, "bad": bad.relative_to(root).as_posix()}

def cmp(root, w1, after, tmp, *extra):
    rep = tmp / "cmp.json"; r = tool("compare", "--w1", w1, "--after", after, "--root", root, "--report", rep, *extra)
    return r, json.loads(rep.read_text(encoding="utf-8"))

def test_snapshot_keeps_full_output_and_metadata(world):
    """W1 對照保存逐檔全文：既有 INVALID 檔的 stdout／stderr 與直接執行舊 bin/qaos validate 的輸出（只正規化 root 路徑）逐字相同，
    而且長度超過 M1 截短保存的範圍（多於 5 行、600 字元）；另記 sha256、舊程式內容雜湊、環境版本、W1 時已登錄的 op。"""
    root, w1, _, info = world; d = json.loads(w1.read_text(encoding="utf-8")); e = d["files"][info["bad"]]
    use_defs(root, old_program())
    try:
        r = subprocess.run([str(old_program() / "bin/qaos"), "validate", str(root / info["bad"])], cwd=old_program(),
                           env=dict(os.environ, QAOS_ROOT=str(root), PYTHONDONTWRITEBYTECODE="1"), capture_output=True, text=True)
    finally: use_defs(root, old_program())
    norm = lambda s: s.replace(str(root), "<ROOT>")
    assert e["rc"] == r.returncode != 0 and e["stdout"] == norm(r.stdout) and e["stderr"] == norm(r.stderr)
    assert e["stdout"].count("\n") > 5 and len(e["stdout"]) > 600, (len(e["stdout"]), e["stdout"][:200])
    assert len(d["program_sha256"]) == 64 and set(d["env_versions"]) == {"jsonschema", "PyYAML"} and d["registered_ops"] == []
    assert all(len(v["sha256"]) == 64 for v in d["files"].values()) and d["summary"]["files"] == len(d["files"])

def test_rollback_passes_with_control_events_exempt(world, tmp_path):
    """正常回復：W1 對照中有的路徑結果全部相同（含既有的 INVALID）；多出的只有 maintenance_start、migrate、migrate_rollback 的事件檔，
    都對應到 index.d、W1 時尚未登錄 → PASS。給 --op X 時同樣 PASS（R 由 takeover_of 推得，later_ops_snapshot 為空）。"""
    root, w1, after, info = world
    for extra in ((), ("--op", info["x"])):
        r, rep = cmp(root, w1, after, tmp_path, *extra)
        assert r.returncode == 0 and rep["result"] == "PASS" and not rep["problems"], (extra, rep["problems"])
        assert {e["action"] for e in rep["exempt"]} == {"maintenance_start", "migrate", "migrate_rollback"}
        assert info["x"] in {e["op_id"] for e in rep["exempt"]}

CASES = ["result_changed", "output_changed", "stderr_changed", "w1_path_removed", "event_unregistered", "event_business_op",
         "non_event_new_yaml", "meta_program_changed", "event_op_registered_at_w1", "event_other_migrate_with_op", "later_ops_not_empty"]
RULE = {"result_changed": "(1)", "output_changed": "(1)", "stderr_changed": "(1)", "w1_path_removed": "(1)", "meta_program_changed": "(meta)",
        "later_ops_not_empty": "(前提)"}

@pytest.mark.parametrize("case", CASES)
def test_compare_reports_mismatch(world, tmp_path, case):
    """5-16 (1)～(3) 與前提的反例：在回復後結果（或登錄紀錄）的複本上改動（標明的反例建構），compare 必須 FAIL 並只指出對應的規則。"""
    root, w1, after, info = world
    w = json.loads(w1.read_text(encoding="utf-8")); d = json.loads(after.read_text(encoding="utf-8")); f = d["files"]
    regs = tmp_path / "root"; shutil.copytree(root / "operations", regs / "operations")     # 登錄紀錄與計畫檔的複本（compare 只讀 operations/）
    w["root"] = d["root"] = str(regs.resolve())
    run_yaml = f"runs/{info['done']}/run.yaml"; bad = info["bad"]; extra = ()
    def reg(op, action):
        (regs / "operations/_global/index.d" / f"99999999-{op}.yaml").write_text(f"plan_seq: 99999999\nop_id: {op}\naction: {action}\n", encoding="utf-8")
    if case == "result_changed": f[run_yaml] = dict(f[run_yaml], rc=1, stdout="INVALID (workflow/workflow-run.schema.json)\n")
    elif case == "output_changed": f[bad] = dict(f[bad], stdout=f[bad]["stdout"] + " - $: 多一行錯誤\n")        # 退出碼相同、只有 stdout 不同
    elif case == "stderr_changed": f[bad] = dict(f[bad], stderr=f[bad]["stderr"] + "warning\n")              # 退出碼與 stdout 相同、只有 stderr 不同
    elif case == "w1_path_removed": del f[run_yaml]
    elif case == "event_unregistered": f["runs/_audit.d/" + "a" * 64 + "-1.yaml"] = dict(f[run_yaml])
    elif case == "event_business_op":
        op = "b" * 64; reg(op, "clarification_answer"); f[f"runs/{info['done']}/audit.d/{op}-1.yaml"] = dict(f[run_yaml])
    elif case == "non_event_new_yaml": f[f"runs/{info['done']}/entities/new.yaml"] = dict(f[run_yaml])
    elif case == "meta_program_changed": d["program_sha256"] = "0" * 64
    elif case == "event_op_registered_at_w1":
        op = next(e for e in f if e.startswith("runs/_audit.d/") and info["x"] in e)
        w["registered_ops"] = [info["x"]]                                                        # W1 時已登錄的 op 不能當成 M2 之後的操作豁免
    elif case == "event_other_migrate_with_op":
        op = "c" * 64; reg(op, "migrate"); f[f"runs/_audit.d/{op}-1.yaml"] = dict(f[run_yaml]); extra = ("--op", info["x"])
    else:
        extra = ("--op", info["x"])
        rp = next(p for p in (regs / "operations/_global").glob("*.yaml") if "action: migrate_rollback" in p.read_text(encoding="utf-8"))
        rp.write_text(rp.read_text(encoding="utf-8").replace("later_ops_snapshot: []", "later_ops_snapshot:\n- op_id: x"), encoding="utf-8")
    w1b, afterb = tmp_path / "w1-bad.json", tmp_path / "after-bad.json"
    w1b.write_text(json.dumps(w, ensure_ascii=False), encoding="utf-8"); afterb.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    r, rep = cmp(regs, w1b, afterb, tmp_path, *extra)
    assert r.returncode == 1 and rep["result"] == "FAIL", rep
    assert [p["rule"] for p in rep["problems"]] == [RULE.get(case, "(3)")], rep["problems"]

def test_outputs_refused_inside_root(world, tmp_path):
    """snapshot 的結果檔、compare 的報告檔都不能寫在資料 root 內。"""
    root, w1, after, _ = world
    r = tool("snapshot", "--root", root, "--program", old_program(), "--out", root / "x.json")
    assert r.returncode != 0 and "資料 root" in r.stderr and not (root / "x.json").exists()
    r = tool("compare", "--w1", w1, "--after", after, "--root", root, "--report", root / "y.json")
    assert r.returncode != 0 and "資料 root" in r.stderr and not (root / "y.json").exists()

def test_snapshot_refuses_broken_old_environment(world, tmp_path):
    """舊程式環境壞掉（每個 validate 都以 Traceback 結束）→ 結束碼 2、不寫結果；W1 與 R5 若都壞掉也不會因結果相同而 PASS。"""
    root, *_ = world
    prog = tmp_path / "broken"; shutil.copytree(old_program(), prog)
    cli = prog / "tools/qaos/cli.py"; cli.write_text(cli.read_text(encoding="utf-8").replace("def cmd_validate(a):\n", "def cmd_validate(a):\n    raise RuntimeError('broken')\n", 1), encoding="utf-8")
    use_defs(root, old_program())
    try: r = tool("snapshot", "--root", root, "--program", prog, "--out", tmp_path / "z.json")
    finally: use_defs(root, old_program())
    assert r.returncode == 2 and "環境異常" in r.stderr and not (tmp_path / "z.json").exists(), r.stderr[-500:]
