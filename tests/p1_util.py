"""P1 executor 驗收的共用工具：每個案例一份獨立的暫存 root，以子程序執行 QAOS（才能真的模擬崩潰）。"""
import os, sys, json, shutil, pathlib, tempfile, subprocess, hashlib, yaml

REPO = pathlib.Path(__file__).resolve().parents[1]
FIXTURES = REPO / "tests" / "fixtures"

def mkroot(migrated: bool = True) -> pathlib.Path:
    """全新的 root（只有定義層）；migrated=True 時以正式流程進入 S_post。"""
    root = pathlib.Path(tempfile.mkdtemp(prefix="qaos-p1-")).resolve()
    for d in ("schemas", "agents", "workflows", "permissions"):
        shutil.copytree(REPO / d, root / d)
    if migrated:
        q(root, "maintenance", "start", "--by", "t", check=True)
        q(root, "migrate", "--by", "t", check=True)
        q(root, "maintenance", "end", "--by", "t", check=True)
    return root

def env_for(root, fault: str | None = None, extra: dict | None = None) -> dict:
    env = dict(os.environ, QAOS_ROOT=str(root), PYTHONPATH=str(REPO))
    env.pop("QAOS_FAULT", None)
    if fault: env["QAOS_FAULT"] = fault
    if extra: env.update(extra)
    return env

def q(root, *args, fault: str | None = None, check: bool = False, extra_env: dict | None = None) -> subprocess.CompletedProcess:
    """執行 `python -m tools.qaos <args>`。故障注入結束程序時 returncode 為 86。"""
    r = subprocess.run([sys.executable, "-m", "tools.qaos", *map(str, args)], cwd=REPO, env=env_for(root, fault, extra_env),
                       capture_output=True, text=True, timeout=120)
    if check and r.returncode != 0:
        raise AssertionError(f"qaos {' '.join(map(str, args))} 失敗（{r.returncode}）：\n{r.stdout}\n{r.stderr}")
    return r

def py(root, code: str, fault: str | None = None, check: bool = True) -> subprocess.CompletedProcess:
    """在子程序執行一段 Python（已設定 QAOS_ROOT）。"""
    r = subprocess.run([sys.executable, "-c", code], cwd=REPO, env=env_for(root, fault), capture_output=True, text=True, timeout=120)
    if check and r.returncode != 0:
        raise AssertionError(f"python 失敗（{r.returncode}）：\n{r.stdout}\n{r.stderr}")
    return r

def load(root, rel):
    return yaml.safe_load((pathlib.Path(root) / rel).read_text(encoding="utf-8"))

def sha(path) -> str | None:
    p = pathlib.Path(path)
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None

def snapshot(root, exclude=("locks/qaos-operation.owner",)) -> dict:
    """root 下所有檔案的 sha256（排除定義層與診斷檔）。"""
    root = pathlib.Path(root); out = {}
    for p in root.rglob("*"):
        if not p.is_file(): continue
        r = p.relative_to(root).as_posix()
        if r.split("/")[0] in ("schemas", "agents", "workflows", "permissions") or r in exclude: continue
        out[r] = sha(p)
    return out

def diff(before: dict, after: dict) -> dict:
    return {"added": sorted(set(after) - set(before)), "removed": sorted(set(before) - set(after)),
            "changed": sorted(k for k in set(before) & set(after) if before[k] != after[k])}

def op_list(root) -> list[dict]:
    """依 index.d 與 status.d 列出計畫（不經 CLI）。"""
    root = pathlib.Path(root); out = []
    d = root / "operations/_global/index.d"
    for p in sorted(d.glob("*.yaml")) if d.is_dir() else []:
        rec = yaml.safe_load(p.read_text(encoding="utf-8")); op = rec["op_id"]
        st = {s.name[len(op) + 1:-5] for s in (root / "operations/_global/status.d").glob(f"{op}-*.yaml")} if (root / "operations/_global/status.d").is_dir() else set()
        out.append({**rec, "statuses": st})
    return out

def incomplete(root) -> list[dict]:
    return [o for o in op_list(root) if not o["statuses"]]

def last_plan(root) -> dict:
    ops = op_list(root)
    op = ops[-1]["op_id"]
    for p in pathlib.Path(root).glob(f"operations/*/{op}.yaml"):
        return yaml.safe_load(p.read_text(encoding="utf-8"))

def plan_of(root, op_id) -> dict:
    for p in pathlib.Path(root).glob(f"operations/*/{op_id}.yaml"):
        return yaml.safe_load(p.read_text(encoding="utf-8"))

def unregistered_plans(root) -> list[str]:
    regs = {o["op_id"] for o in op_list(root)}
    return [p.stem for p in pathlib.Path(root).glob("operations/*/*.yaml") if p.stem not in regs]

def import_auth_spec(root, version="1.0"):
    q(root, "spec", "import", FIXTURES / f"SPEC-AUTH-001-v{version}.md", "--spec-id", "SPEC-AUTH-001", "--version", version,
      "--product", "demo", "--area", "AUTH", "--by", "t", check=True)
