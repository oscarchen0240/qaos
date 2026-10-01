"""檔案儲存層：路徑約定、YAML I/O、audit log、hash。"""
import os, hashlib, datetime, pathlib, yaml

def find_root(start: pathlib.Path | None = None) -> pathlib.Path:
    env = os.environ.get("QAOS_ROOT")
    if env: return pathlib.Path(env).resolve()
    p = (start or pathlib.Path.cwd()).resolve()
    for cand in [p, *p.parents]:
        if (cand / "permissions" / "action-registry.yaml").exists(): return cand
    raise SystemExit("qaos: 找不到 QAOS root（需含 permissions/action-registry.yaml），或設定 QAOS_ROOT")

ROOT = find_root()

def now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def today() -> str:
    return datetime.date.today().strftime("%Y%m%d")

def load(path) -> dict:
    p = ROOT / path if not str(path).startswith("/") else pathlib.Path(path)
    if not p.exists(): raise FileNotFoundError(str(p))
    with open(p, encoding="utf-8") as f: return yaml.safe_load(f) or {}

def save(path, obj):
    p = ROOT / path if not str(path).startswith("/") else pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        yaml.safe_dump(obj, f, allow_unicode=True, sort_keys=False, width=120)
    return p

def exists(path) -> bool:
    return (ROOT / path).exists()

def sha256_file(path) -> str:
    p = ROOT / path if not str(path).startswith("/") else pathlib.Path(path)
    return hashlib.sha256(p.read_bytes()).hexdigest()

def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def audit(run_id: str | None, actor: str, action: str, detail: str = ""):
    line = f"{now()}\t{actor}\t{action}\t{detail}\n"
    if run_id:
        p = ROOT / "runs" / run_id / "audit.log"; p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "a", encoding="utf-8") as f: f.write(line)
    p = ROOT / "runs" / "_audit.log"; p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as f: f.write(f"{run_id or '-'}\t{line}")

# ---- entity 路徑約定 ----
def spec_dir(spec_id: str) -> pathlib.Path | None:
    for p in (ROOT / "specs").glob(f"*/*/{spec_id}"):
        if (p / "spec.yaml").exists(): return p
    return None

def run_area(inputs: dict) -> str | None:
    """run 所屬 functional area（ADR-009），依序：run 的 spec_id → manual record 的 spec_hint.spec_id（皆看 spec 所在目錄）
    → manual record 的 functional_area（須為大寫 area 代碼，空白／無效不算）。判定不了回 None，由 new_run 拒絕。"""
    def _spec_area(sid):
        d = spec_dir(sid) if sid else None
        return d.parent.name if d else None
    if inputs.get("spec_id"): return _spec_area(inputs["spec_id"])
    rid = inputs.get("manual_record_id")
    rec = load(f"testcases/manual/{rid}.yaml") if rid and exists(f"testcases/manual/{rid}.yaml") else {}
    area = _spec_area((rec.get("spec_hint") or {}).get("spec_id"))
    if area: return area
    fa = (rec.get("functional_area") or "").strip()
    return fa if fa.isascii() and fa.isalpha() and fa.isupper() else None

def requirements_path(spec_id: str, spec_version: str) -> str:
    return f"artifacts/requirements/{spec_id}/v{spec_version}/requirements.yaml"

def tc_version_path(tc_id: str, version: int) -> str:
    return f"testcases/versions/{tc_id}/v{version}.yaml"

def tc_pointer_path(tc_id: str) -> str:
    return f"testcases/registry/{tc_id}.yaml"

def suite_path(suite_type: str, suite_id: str) -> str:
    return f"testsuites/{suite_type.replace('_', '-')}/{suite_id}.yaml"

def bug_path(product: str, area: str, bug_id: str) -> str:
    return f"bugs/{product}/{area}/{bug_id}.yaml"

def find_bug(bug_id: str) -> pathlib.Path | None:
    for p in (ROOT / "bugs").glob(f"*/*/{bug_id}.yaml"): return p
    return None

def find_artifact(artifact_id: str) -> pathlib.Path | None:
    for p in (ROOT / "artifacts").rglob(f"{artifact_id}.yaml"): return p
    return None

def find_execution(exe_id: str) -> pathlib.Path | None:
    for p in (ROOT / "executions").rglob(f"{exe_id}.yaml"): return p
    return None

def find_evidence(evd_id: str) -> pathlib.Path | None:
    for p in (ROOT / "evidence").rglob(f"{evd_id}.yaml"): return p
    return None

def find_suite(suite_id: str) -> pathlib.Path | None:
    for p in (ROOT / "testsuites").rglob(f"{suite_id}.yaml"): return p
    return None

def clarification_path(product: str, area: str, clr_id: str) -> str:
    return f"clarifications/{product}/{area}/{clr_id}.yaml"

def find_clarification(clr_id: str) -> pathlib.Path | None:
    for p in (ROOT / "clarifications").glob(f"*/*/{clr_id}.yaml"): return p
    return None
