"""tools/legacy_validate_snapshot.py（附錄 A 5-16、§15.1 W1、§15.2 R5、AC-09-64）。

以 legacy fixture（p3_legacy：需求 A 之前的程式以正式流程產生的 S_pre 資料）模擬部署與回復的定義層切換：
W1 對照與 R5 時資料 root 的定義層（schemas／agents／workflows／permissions）是舊程式 f5188b0 的版本，並以 f5188b0 的 bin/qaos 執行；
M2～R3 之間換成新程式的定義層，以新程式正式流程 maintenance start → migrate → migrate rollback → verify --rolled-back；R4 再換回舊定義層。"""
import json, pathlib, shutil, subprocess, sys, tempfile
import pytest
from tests import p1_util as U, p3_legacy as L

OLD = "f5188b0"
DEFS = ("schemas", "agents", "workflows", "permissions")
TOOL = U.REPO / "tools/legacy_validate_snapshot.py"

def old_program() -> pathlib.Path:
    d = pathlib.Path(tempfile.gettempdir()) / f"qaos-old-program-{OLD}"
    if not (d / "bin/qaos").exists():
        d.mkdir(parents=True, exist_ok=True)
        data = subprocess.run(["git", "-C", str(U.REPO), "archive", OLD, "bin", "tools", *DEFS], capture_output=True, check=True).stdout
        subprocess.run(["tar", "-x", "-C", str(d)], input=data, check=True)
    return d

def use_defs(root: pathlib.Path, src: pathlib.Path):
    for d in DEFS:
        shutil.rmtree(root / d); shutil.copytree(src / d, root / d)

def tool(*args):
    return subprocess.run([sys.executable, str(TOOL), *map(str, args)], cwd=U.REPO, capture_output=True, text=True, timeout=600)

def snap(root, out):
    r = tool("snapshot", "--root", root, "--program", old_program(), "--out", out); assert r.returncode == 0, r.stderr
    return json.loads(pathlib.Path(out).read_text(encoding="utf-8"))

@pytest.fixture(scope="module")
def world(tmp_path_factory):
    """W1 對照 → M2～R3（新程式）→ R4 → 回復後的對照。回傳 (root, w1 路徑, after 路徑, 資訊)。"""
    out = tmp_path_factory.mktemp("lvs"); old = old_program()
    root, info = L.legacy_root()
    bad = root / f"runs/{info['done']}/entities/m1-fixture.yaml"                              # fixture 建構：一個舊 validate 會判 INVALID 的既有檔（舊 infer 把 runs/ 下的 yaml 都當 run）
    bad.parent.mkdir(parents=True, exist_ok=True); bad.write_text("note: 測試用既有失敗\n", encoding="utf-8")
    use_defs(root, old)                                                                       # W1：舊程式的定義層
    w1 = out / "w1.json"; snap(root, w1)
    use_defs(root, U.REPO)                                                                    # M2：新程式
    L.migrate(root, "--acknowledge-idle", info["running"])
    x = yaml_load(root / "artifacts/requirements/_migration.yaml")["migrate_op_id"]
    U.q(root, "migrate", "rollback", "--op", x, "--by", "m", check=True)
    U.q(root, "migrate", "verify", "--rolled-back", check=True)
    use_defs(root, old)                                                                       # R4：舊程式
    (root / "locks/maintenance.yaml").unlink()                                                # R6（人工）
    after = out / "after.json"; snap(root, after)
    return root, w1, after, {**info, "x": x, "bad": bad.relative_to(root).as_posix()}

def yaml_load(p):
    import yaml
    return yaml.safe_load(pathlib.Path(p).read_text(encoding="utf-8"))

def cmp(root, w1, after, tmp):
    rep = tmp / "cmp.json"; r = tool("compare", "--w1", w1, "--after", after, "--root", root, "--report", rep)
    return r, json.loads(rep.read_text(encoding="utf-8"))

def test_snapshot_keeps_full_output_and_metadata(world):
    """W1 對照保存逐檔全文：既有的 INVALID 檔，stdout 與直接執行舊 bin/qaos validate 的輸出逐字相同（不截短）；另記 sha256、舊程式與工具版本。"""
    root, w1, _, info = world; d = json.loads(w1.read_text(encoding="utf-8"))
    e = d["files"][info["bad"]]
    assert e["rc"] != 0 and e["stdout"].count("\n") > 3                                      # 多行錯誤
    assert d["tool_version"] and d["tool_sha256"] and d["python"] and d["no_schema"] >= 0 and d["summary"]["files"] == len(d["files"])
    assert all(len(v["sha256"]) == 64 for v in d["files"].values())

def test_rollback_passes_with_control_events_exempt(world, tmp_path):
    """正常回復：W1 對照中有的路徑結果全部相同（含既有的 INVALID）；多出的只有 maintenance_start、migrate、migrate_rollback 的事件檔，且都對應到 index.d → PASS。"""
    root, w1, after, info = world
    r, rep = cmp(root, w1, after, tmp_path)
    assert r.returncode == 0 and rep["result"] == "PASS" and not rep["problems"], rep["problems"]
    assert {e["action"] for e in rep["exempt"]} == {"maintenance_start", "migrate", "migrate_rollback"}
    assert info["x"] in {e["op_id"] for e in rep["exempt"]}

@pytest.mark.parametrize("case", ["result_changed", "output_changed", "w1_path_removed", "event_unregistered", "event_business_op", "non_event_new_yaml"])
def test_compare_reports_mismatch(world, tmp_path, case):
    """5-16 (1)～(3) 的反例：在回復後結果的複本上改動（標明的反例建構），compare 必須 FAIL 並指出規則。"""
    root, w1, after, info = world
    d = json.loads(after.read_text(encoding="utf-8")); f = d["files"]; regs = tmp_path / "root"
    shutil.copytree(root / "operations", regs / "operations")                               # 登錄紀錄的複本（只有這個目錄會被讀）
    run_yaml = f"runs/{info['done']}/run.yaml"
    if case == "result_changed": f[run_yaml] = dict(f[run_yaml], rc=1, stdout="INVALID (workflow/workflow-run.schema.json)\n")
    elif case == "output_changed": f[info["bad"]] = dict(f[info["bad"]], stdout=f[info["bad"]]["stdout"] + " - $: 多一行錯誤\n")   # 退出碼相同、只有輸出不同
    elif case == "w1_path_removed": del f[run_yaml]
    elif case == "event_unregistered": f["runs/_audit.d/" + "a" * 64 + "-1.yaml"] = dict(f[run_yaml])
    elif case == "event_business_op":
        op = "b" * 64
        (regs / "operations/_global/index.d" / f"99999999-{op}.yaml").write_text(f"plan_seq: 99999999\nop_id: {op}\naction: clarification_answer\n", encoding="utf-8")
        f[f"runs/{info['done']}/audit.d/{op}-1.yaml"] = dict(f[run_yaml])
    else: f[f"runs/{info['done']}/entities/new.yaml"] = dict(f[run_yaml])
    bad_after = tmp_path / "after-bad.json"; bad_after.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    r, rep = cmp(regs, w1, bad_after, tmp_path)
    assert r.returncode == 1 and rep["result"] == "FAIL", rep
    want = "(1)" if case in ("result_changed", "output_changed", "w1_path_removed") else "(3)"
    assert [p["rule"] for p in rep["problems"]] == [want], rep["problems"]

def test_snapshot_refuses_output_inside_root(world, tmp_path):
    root, *_ = world
    r = tool("snapshot", "--root", root, "--program", old_program(), "--out", root / "x.json")
    assert r.returncode != 0 and "資料 root" in r.stderr and not (root / "x.json").exists()
