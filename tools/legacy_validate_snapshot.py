#!/usr/bin/env python3
"""舊程式 `bin/qaos validate` 的逐檔對照（需求 A 附錄 A 5-16、§15.1 W1、§15.2 R5、AC-09-64）。

兩個子指令：
  snapshot --root <資料 root> [--program <舊程式目錄>] --out <結果.json>
      以 <舊程式目錄>（預設＝資料 root）的 `bin/qaos validate`，對「舊 `schema.infer` 能推斷 schema 的全部 yaml」逐檔執行，
      每檔一個子程序（8 路平行），保存逐檔的路徑、推斷的 schema、退出碼、stdout／stderr **全文**（資料 root 的絕對路徑正規化為 `<ROOT>`）、
      檔案 sha256，以及資料 root 與舊程式的 git commit、本工具版本、Python 版本、時間。
      另記錄當時登錄紀錄（index.d）中已有的 op，以及舊程式環境的 jsonschema／PyYAML 版本。
      W1：資料 commit 之後、M2 之前（仍是舊程式）對主資料夾執行，結果作為 W1 對照。R5：程式 revert 之後再執行一次。
      範圍排除定義層（schemas、agents、workflows、permissions、tools、tests、admin-ui、docs、bin）與隱藏目錄。
      自我檢查：任何輸出含 Traceback，或 VALID 為 0 → 視為舊程式環境異常，結束碼 2，不寫結果。
      本工具只讀資料 root（結果檔不得寫在資料 root 內）；子程序是舊程式的唯讀指令 `validate` 與 `schema.infer`。
  compare --w1 <W1 對照.json> --after <回復後.json> --root <資料 root> [--op <X 的 op_id>] [--report <報告.json>]
      先核對兩份結果的中繼資料（資料 root、舊程式內容的雜湊、工具版本與 sha256、jsonschema／PyYAML 版本）相同，不同即不符。
      舊程式的 git HEAD 只記錄、不比對（R5 的 HEAD 是 revert commit）。
      依 5-16 判定：
        (1) W1 對照中有的路徑：回復後也必須存在，退出碼、stdout、stderr 全文都相同；
        (2) W1 對照中沒有的路徑：只允許是 `runs/_audit.d/<op>-<n>.yaml`、`runs/<run>/audit.d/<op>-<n>.yaml` 的事件檔，
            而且 <op> 必須能在登錄紀錄（`operations/_global/index.d/*.yaml`）中找到、在 W1 時尚未登錄（M2 之後），
            action 是 migrate、migrate_rollback、maintenance_start 或 maintenance_end；給了 --op 時，migrate 只限 X、
            migrate_rollback 只限 takeover_of 為 X 的 R。符合者不在舊 validate 的判定範圍；
        (3) 其他情況都視為不符。全部符合 → 結束碼 0；有不符 → 結束碼 1，逐項列出。
      前提：`later_ops_snapshot` 為空。給了 --op 時，工具讀 R 的計畫檔確認；非空時列為不符，後續操作寫入的路徑依後續操作報告人工判定。
"""
import argparse, concurrent.futures as cf, datetime, hashlib, json, os, pathlib, platform, re, subprocess, sys

TOOL_VERSION = "1"
DEF_LAYER = ("schemas", "agents", "workflows", "permissions", "tools", "tests", "admin-ui", "docs", "bin")
SKIP_PARTS = {".git", "node_modules", ".venv", "__pycache__"}
EXEMPT_ACTIONS = {"migrate", "migrate_rollback", "maintenance_start", "maintenance_end"}
EVENT_RE = re.compile(r"runs/(?:_audit\.d|[^/]+/audit\.d)/([0-9a-f]{64})-\d+\.yaml")

def _sha(p: pathlib.Path) -> str: return hashlib.sha256(p.read_bytes()).hexdigest()

def _git_head(d: pathlib.Path) -> str | None:
    r = subprocess.run(["git", "-C", str(d), "rev-parse", "HEAD"], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None

def _program_sha(program: pathlib.Path) -> str:
    """舊程式內容的雜湊（bin/qaos、tools/qaos、schemas 的逐檔路徑與 sha256）。W1 與 R5 的 git HEAD 會不同（R5 是 revert commit），所以比內容不比 HEAD。"""
    h = hashlib.sha256()
    files = [program / "bin/qaos", *sorted((program / "tools/qaos").rglob("*.py")), *sorted((program / "schemas").rglob("*.json"))]
    for f in files:
        if f.is_file() and "__pycache__" not in f.parts: h.update(f"{f.relative_to(program).as_posix()}\0{_sha(f)}\n".encode())
    return h.hexdigest()

def _candidates(root: pathlib.Path) -> list[str]:
    out = []
    for p in sorted(root.rglob("*.yaml")):
        rel = p.relative_to(root)
        if rel.parts[0] in DEF_LAYER or rel.parts[0].startswith(".") or SKIP_PARTS & set(rel.parts) or not p.is_file(): continue
        out.append(rel.as_posix())
    return out

def _inferred(root: pathlib.Path, program: pathlib.Path, rels: list[str]) -> dict:
    """以舊程式自己的 schema.infer 決定範圍（在舊程式目錄以子程序執行；stdin 傳入路徑清單）。"""
    code = ("import sys, json, importlib.metadata as md\nfrom tools.qaos import schema\n"
            "v = {k: md.version(k) for k in ('jsonschema', 'PyYAML')}\n"
            "print(json.dumps({'infer': {r: schema.infer(r) for r in json.load(sys.stdin)}, 'versions': v}))")
    env = dict(os.environ, QAOS_ROOT=str(root), PYTHONDONTWRITEBYTECODE="1")
    r = subprocess.run([sys.executable, "-c", code], cwd=program, env=env, input=json.dumps(rels), capture_output=True, text=True)
    if r.returncode != 0: raise SystemExit(f"舊程式的 schema.infer 執行失敗：\n{r.stderr[-2000:]}")
    return json.loads(r.stdout.strip().splitlines()[-1])

def snapshot(root: pathlib.Path, program: pathlib.Path, workers: int = 8) -> dict:
    root, program = root.resolve(), program.resolve()
    qaos = program / "bin/qaos"
    if not qaos.is_file(): raise SystemExit(f"找不到舊程式的 bin/qaos：{qaos}")
    got = _inferred(root, program, _candidates(root)); inf = got["infer"]
    files = sorted(r for r, s in inf.items() if s)
    env = dict(os.environ, QAOS_ROOT=str(root), PYTHONDONTWRITEBYTECODE="1")
    norm = lambda s: s.replace(str(root), "<ROOT>")
    def run(rel):
        r = subprocess.run([str(qaos), "validate", str(root / rel)], cwd=program, env=env, capture_output=True, text=True)
        return rel, {"schema": inf[rel], "rc": r.returncode, "stdout": norm(r.stdout), "stderr": norm(r.stderr), "sha256": _sha(root / rel)}
    with cf.ThreadPoolExecutor(workers) as ex: results = dict(ex.map(run, files))
    broken = [r for r, v in results.items() if "Traceback" in v["stdout"] + v["stderr"]]
    if broken or (results and not any(v["rc"] == 0 for v in results.values())):
        _abort(broken)
    return {"tool": "legacy_validate_snapshot", "tool_version": TOOL_VERSION, "tool_sha256": _sha(pathlib.Path(__file__)),
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"), "python": platform.python_version(),
            "root": str(root), "root_git_head": _git_head(root), "program": str(program), "program_git_head": _git_head(program), "program_sha256": _program_sha(program),
            "scope": "舊 schema.infer 能推斷 schema 的全部 yaml（排除定義層與隱藏目錄）", "no_schema": len(inf) - len(files),
            "env_versions": got["versions"], "registered_ops": sorted(_registered(root)),
            "summary": {"files": len(results), "valid": sum(1 for v in results.values() if v["rc"] == 0), "invalid": sum(1 for v in results.values() if v["rc"] != 0)},
            "files": results}

def _abort(broken):
    print(f"舊程式環境異常：Traceback {len(broken)} 檔（例如 {broken[:3]}），或沒有任何 VALID；不寫結果", file=sys.stderr)
    raise SystemExit(2)

def _registered(root: pathlib.Path) -> dict:
    out = {}
    d = root / "operations/_global/index.d"
    for p in sorted(d.glob("*.yaml")) if d.is_dir() else []:
        txt = p.read_text(encoding="utf-8")
        op = re.search(r"^op_id:\s*(\S+)", txt, re.M); act = re.search(r"^action:\s*(\S+)", txt, re.M)
        if op and act: out[op.group(1)] = act.group(1)
    return out

META = ("root", "program_sha256", "tool_version", "tool_sha256", "env_versions")

def _plan_text(root: pathlib.Path, op: str) -> str:
    p = root / f"operations/_global/{op}.yaml"
    return p.read_text(encoding="utf-8") if p.is_file() else ""

def compare(w1: dict, after: dict, root: pathlib.Path, x: str | None = None) -> dict:
    a, b = w1["files"], after["files"]; root = root.resolve(); regs = _registered(root)
    problems, exempt = [], []
    for k in META:
        if w1.get(k) != after.get(k): problems.append({"path": "-", "rule": "(meta)", "reason": f"兩份結果的 {k} 不同", "w1": w1.get(k), "after": after.get(k)})
    pre_ops = set(w1.get("registered_ops") or [])
    allowed = None
    if x:
        rs = [op for op, act in regs.items() if act == "migrate_rollback" and re.search(rf"^takeover_of:\s*{x}\s*$", _plan_text(root, op), re.M)]
        allowed = {x, *rs}
        for r in rs:
            if not re.search(r"^later_ops_snapshot:\s*\[\]\s*$", _plan_text(root, r), re.M):
                problems.append({"path": f"operations/_global/{r}.yaml", "rule": "(前提)", "reason": "R 的 later_ops_snapshot 不是空的：後續操作寫入的路徑另依後續操作報告人工判定"})
        if not rs: problems.append({"path": "-", "rule": "(前提)", "reason": f"登錄紀錄中找不到 takeover_of 為 {x} 的 rollback 計畫"})
    for rel, v in sorted(a.items()):                                                       # (1)
        if rel not in b: problems.append({"path": rel, "rule": "(1)", "reason": "W1 對照中有，回復後不在範圍內（不存在或推斷不出 schema）"}); continue
        diff = [k for k in ("rc", "stdout", "stderr") if v[k] != b[rel][k]]
        if diff: problems.append({"path": rel, "rule": "(1)", "reason": f"結果與 W1 對照不同：{', '.join(diff)}", "w1": {k: v[k] for k in diff}, "after": {k: b[rel][k] for k in diff}})
    for rel in sorted(set(b) - set(a)):                                                    # (2)、(3)
        m = EVENT_RE.fullmatch(rel); op = m.group(1) if m else None; act = regs.get(op) if m else None
        why = None
        if not m: why = ""
        elif act is None: why = "（op 不在登錄紀錄中）"
        elif act not in EXEMPT_ACTIONS: why = f"（op 的 action 是 {act}）"
        elif op in pre_ops: why = "（op 在 W1 時已登錄，不是 M2 之後的操作）"
        elif allowed is not None and act in ("migrate", "migrate_rollback") and op not in allowed: why = "（不是本次的 X 或接管 X 的 R）"
        if why is None: exempt.append({"path": rel, "op_id": op, "action": act, "rc": b[rel]["rc"]})
        else: problems.append({"path": rel, "rule": "(3)", "reason": "W1 對照中沒有，且不是可對應到 X、R 或 M2 之後控制類操作的事件檔" + why})
    return {"result": "PASS" if not problems else "FAIL", "w1_files": len(a), "after_files": len(b),
            "exempt": exempt, "problems": problems,
            "note": "前提：later_ops_snapshot 為空（給了 --op 時已核對）；非空時後續操作報告列出的路徑另依該報告人工判定（附錄 A 5-16）"}

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0]); sp = ap.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("snapshot"); s.add_argument("--root", required=True, type=pathlib.Path); s.add_argument("--program", type=pathlib.Path)
    s.add_argument("--out", required=True, type=pathlib.Path); s.add_argument("--workers", type=int, default=8)
    c = sp.add_parser("compare"); c.add_argument("--w1", required=True, type=pathlib.Path); c.add_argument("--after", required=True, type=pathlib.Path)
    c.add_argument("--root", required=True, type=pathlib.Path); c.add_argument("--op"); c.add_argument("--report", type=pathlib.Path)
    a = ap.parse_args(argv)
    if a.cmd == "snapshot":
        out = a.out.resolve()
        if out.is_relative_to(a.root.resolve()): raise SystemExit("輸出檔不能寫在資料 root 內")
        res = snapshot(a.root, a.program or a.root, a.workers)
        out.write_text(json.dumps(res, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
        print(f"{res['summary']['files']} 檔：VALID {res['summary']['valid']}、INVALID {res['summary']['invalid']}；推斷不出 schema {res['no_schema']} 檔 → {out}")
        return 0
    if a.report and a.report.resolve().is_relative_to(a.root.resolve()): raise SystemExit("報告檔不能寫在資料 root 內")
    rep = compare(json.loads(a.w1.read_text(encoding="utf-8")), json.loads(a.after.read_text(encoding="utf-8")), a.root, a.op)
    if a.report: a.report.write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{rep['result']}：W1 {rep['w1_files']} 檔、回復後 {rep['after_files']} 檔；豁免的事件檔 {len(rep['exempt'])}；不符 {len(rep['problems'])}")
    for p in rep["problems"][:50]: print(f"  {p['rule']} {p['path']}：{p['reason']}")
    return 0 if rep["result"] == "PASS" else 1

if __name__ == "__main__": sys.exit(main())
