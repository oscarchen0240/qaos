#!/usr/bin/env python3
"""舊程式 `bin/qaos validate` 的逐檔對照（需求 A 附錄 A 5-16、§15.1 W1、§15.2 R5、AC-09-64）。

兩個子指令：
  snapshot --root <資料 root> [--program <舊程式目錄>] --out <結果.json>
      以 <舊程式目錄>（預設＝資料 root）的 `bin/qaos validate`，對「舊 `schema.infer` 能推斷 schema 的全部 yaml」逐檔執行，
      每檔一個子程序（8 路平行），保存逐檔的路徑、推斷的 schema、退出碼、stdout／stderr **全文**（資料 root 的絕對路徑正規化為 `<ROOT>`）、
      檔案 sha256，以及資料 root 與舊程式的 git commit、本工具版本、Python 版本、時間。
      W1：資料 commit 之後、M2 之前（仍是舊程式）對主資料夾執行，結果作為 W1 對照。R5：程式 revert 之後再執行一次。
      本工具只讀資料 root；子程序是舊程式的唯讀指令 `validate`。
  compare --w1 <W1 對照.json> --after <回復後.json> --root <資料 root> [--report <報告.json>]
      依 5-16 判定：
        (1) W1 對照中有的路徑：回復後也必須存在，退出碼、stdout、stderr 全文都相同；
        (2) W1 對照中沒有的路徑：只允許是 `runs/_audit.d/<op>-<n>.yaml`、`runs/<run>/audit.d/<op>-<n>.yaml` 的事件檔，
            而且 <op> 必須能在登錄紀錄（`operations/_global/index.d/*.yaml`）中找到，action 是 migrate、migrate_rollback、
            maintenance_start 或 maintenance_end；符合者不在舊 validate 的判定範圍；
        (3) 其他情況都視為不符。全部符合 → 結束碼 0；有不符 → 結束碼 1，逐項列出。
      前提：`later_ops_snapshot` 為空。使用 `--allow-later-ops` 時，後續業務操作寫入的檔案依後續操作報告人工判定，本工具會把它們列為不符。
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

def _candidates(root: pathlib.Path) -> list[str]:
    out = []
    for p in sorted(root.rglob("*.yaml")):
        rel = p.relative_to(root)
        if rel.parts[0] in DEF_LAYER or rel.parts[0].startswith(".") or SKIP_PARTS & set(rel.parts) or not p.is_file(): continue
        out.append(rel.as_posix())
    return out

def _inferred(root: pathlib.Path, program: pathlib.Path, rels: list[str]) -> dict:
    """以舊程式自己的 schema.infer 決定範圍（在舊程式目錄以子程序執行；stdin 傳入路徑清單）。"""
    code = ("import sys, json\nfrom tools.qaos import schema\n"
            "print(json.dumps({r: schema.infer(r) for r in json.load(sys.stdin)}))")
    env = dict(os.environ, QAOS_ROOT=str(root), PYTHONDONTWRITEBYTECODE="1")
    r = subprocess.run([sys.executable, "-c", code], cwd=program, env=env, input=json.dumps(rels), capture_output=True, text=True)
    if r.returncode != 0: raise SystemExit(f"舊程式的 schema.infer 執行失敗：\n{r.stderr[-2000:]}")
    return json.loads(r.stdout.strip().splitlines()[-1])

def snapshot(root: pathlib.Path, program: pathlib.Path, workers: int = 8) -> dict:
    root, program = root.resolve(), program.resolve()
    qaos = program / "bin/qaos"
    if not qaos.is_file(): raise SystemExit(f"找不到舊程式的 bin/qaos：{qaos}")
    inf = _inferred(root, program, _candidates(root))
    files = sorted(r for r, s in inf.items() if s)
    env = dict(os.environ, QAOS_ROOT=str(root), PYTHONDONTWRITEBYTECODE="1")
    norm = lambda s: s.replace(str(root), "<ROOT>")
    def run(rel):
        r = subprocess.run([str(qaos), "validate", str(root / rel)], cwd=program, env=env, capture_output=True, text=True)
        return rel, {"schema": inf[rel], "rc": r.returncode, "stdout": norm(r.stdout), "stderr": norm(r.stderr), "sha256": _sha(root / rel)}
    with cf.ThreadPoolExecutor(workers) as ex: results = dict(ex.map(run, files))
    return {"tool": "legacy_validate_snapshot", "tool_version": TOOL_VERSION, "tool_sha256": _sha(pathlib.Path(__file__)),
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"), "python": platform.python_version(),
            "root": str(root), "root_git_head": _git_head(root), "program": str(program), "program_git_head": _git_head(program),
            "scope": "舊 schema.infer 能推斷 schema 的全部 yaml（排除定義層與隱藏目錄）", "no_schema": len(inf) - len(files),
            "summary": {"files": len(results), "valid": sum(1 for v in results.values() if v["rc"] == 0), "invalid": sum(1 for v in results.values() if v["rc"] != 0)},
            "files": results}

def _registered(root: pathlib.Path) -> dict:
    out = {}
    d = root / "operations/_global/index.d"
    for p in sorted(d.glob("*.yaml")) if d.is_dir() else []:
        txt = p.read_text(encoding="utf-8")
        op = re.search(r"^op_id:\s*(\S+)", txt, re.M); act = re.search(r"^action:\s*(\S+)", txt, re.M)
        if op and act: out[op.group(1)] = act.group(1)
    return out

def compare(w1: dict, after: dict, root: pathlib.Path) -> dict:
    a, b = w1["files"], after["files"]; regs = _registered(root.resolve())
    problems, exempt = [], []
    for rel, v in sorted(a.items()):                                                       # (1)
        if rel not in b: problems.append({"path": rel, "rule": "(1)", "reason": "W1 對照中有，回復後不在範圍內（不存在或推斷不出 schema）"}); continue
        diff = [k for k in ("rc", "stdout", "stderr") if v[k] != b[rel][k]]
        if diff: problems.append({"path": rel, "rule": "(1)", "reason": f"結果與 W1 對照不同：{', '.join(diff)}", "w1": {k: v[k] for k in diff}, "after": {k: b[rel][k] for k in diff}})
    for rel in sorted(set(b) - set(a)):                                                    # (2)、(3)
        m = EVENT_RE.fullmatch(rel); act = regs.get(m.group(1)) if m else None
        if m and act in EXEMPT_ACTIONS: exempt.append({"path": rel, "op_id": m.group(1), "action": act, "rc": b[rel]["rc"]})
        else: problems.append({"path": rel, "rule": "(3)", "reason": "W1 對照中沒有，且不是可對應到 X、R 或控制類操作的事件檔" +
                               (f"（op 的 action 是 {act}）" if act else "（op 不在登錄紀錄中）" if m else "")})
    return {"result": "PASS" if not problems else "FAIL", "w1_files": len(a), "after_files": len(b),
            "exempt": exempt, "problems": problems,
            "note": "前提：later_ops_snapshot 為空；使用 --allow-later-ops 時，後續操作報告列出的路徑另依該報告人工判定（附錄 A 5-16）"}

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0]); sp = ap.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("snapshot"); s.add_argument("--root", required=True, type=pathlib.Path); s.add_argument("--program", type=pathlib.Path)
    s.add_argument("--out", required=True, type=pathlib.Path); s.add_argument("--workers", type=int, default=8)
    c = sp.add_parser("compare"); c.add_argument("--w1", required=True, type=pathlib.Path); c.add_argument("--after", required=True, type=pathlib.Path)
    c.add_argument("--root", required=True, type=pathlib.Path); c.add_argument("--report", type=pathlib.Path)
    a = ap.parse_args(argv)
    if a.cmd == "snapshot":
        out = a.out.resolve()
        if out.is_relative_to(a.root.resolve()): raise SystemExit("輸出檔不能寫在資料 root 內")
        res = snapshot(a.root, a.program or a.root, a.workers)
        out.write_text(json.dumps(res, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
        print(f"{res['summary']['files']} 檔：VALID {res['summary']['valid']}、INVALID {res['summary']['invalid']}；推斷不出 schema {res['no_schema']} 檔 → {out}")
        return 0
    rep = compare(json.loads(a.w1.read_text(encoding="utf-8")), json.loads(a.after.read_text(encoding="utf-8")), a.root)
    if a.report: a.report.write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{rep['result']}：W1 {rep['w1_files']} 檔、回復後 {rep['after_files']} 檔；豁免的事件檔 {len(rep['exempt'])}；不符 {len(rep['problems'])}")
    for p in rep["problems"][:50]: print(f"  {p['rule']} {p['path']}：{p['reason']}")
    return 0 if rep["result"] == "PASS" else 1

if __name__ == "__main__": sys.exit(main())
