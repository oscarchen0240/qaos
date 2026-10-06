"""檔案儲存層：路徑約定、YAML I/O、hash，以及 executor 的寫入擷取（overlay）。

所有寫入一律經過 executor（tools/qaos/operation.py）：
- 在操作的擷取期間，save／write_text／write_bytes／delete 只記錄到記憶體 overlay，audit() 只記錄事件；
  讀取（load／exists／read_bytes／glob）先看 overlay、再看檔案系統（read-your-writes）。
- 擷取結束後，executor 把 overlay 變成操作計畫的步驟，再依序寫入。
- 沒有作用中的擷取時呼叫寫入函式 → NoExecutorContext（不允許繞過 executor 直接寫檔）。
"""
import os, re, fnmatch, hashlib, datetime, pathlib, yaml

def find_root(start: pathlib.Path | None = None) -> pathlib.Path:
    env = os.environ.get("QAOS_ROOT")
    if env: return pathlib.Path(env).resolve()
    p = (start or pathlib.Path.cwd()).resolve()
    for cand in [p, *p.parents]:
        if (cand / "permissions" / "action-registry.yaml").exists(): return cand
    raise SystemExit("qaos: 找不到 QAOS root（需含 permissions/action-registry.yaml），或設定 QAOS_ROOT")

ROOT = find_root()

class NoExecutorContext(Exception):
    """寫入函式在沒有 executor 擷取的情況下被呼叫。"""

# ---- 寫入擷取（由 operation.py 開始與結束） ----
class Capture:
    def __init__(self, clock: str, today: str, op_id: str, owner_token: str | None = None):
        self.clock, self.today, self.op_id = clock, today, op_id
        self.owner_pid, self.owner_token = os.getpid(), owner_token   # 只有建立它、而且持有 executor context 的程序能使用
        self.files: dict[str, bytes | None] = {}     # rel → 最終內容（None = 刪除）
        self.derived: set[str] = set()               # 衍生輸出的 rel
        self.sequence: list[tuple] = []              # ("file", rel) 第一次觸碰 | ("event", idx)
        self.events: list[dict] = []                 # {run_id, actor, action, detail}
        self.allocated_ids: list[str] = []
        self.diagnostic = False

    def put(self, rel_path: str, data: bytes | None, derived: bool = False):
        if rel_path not in self.files: self.sequence.append(("file", rel_path))
        self.files[rel_path] = data
        if derived: self.derived.add(rel_path)
        else: self.derived.discard(rel_path)

_CAP: Capture | None = None
CAPTURE_GUARD = None   # operation.py 設定：核對擷取的持有者仍是目前持鎖的 executor context

def begin_capture(clock: str, today: str, op_id: str, owner_token: str | None = None) -> Capture:
    global _CAP
    if _CAP is not None: raise RuntimeError("擷取已在進行中")
    cap = Capture(clock, today, op_id, owner_token)
    if CAPTURE_GUARD is not None and not CAPTURE_GUARD(cap):
        raise NoExecutorContext("沒有持鎖的 executor context，不能開始擷取")
    _CAP = cap; return _CAP

def end_capture():
    global _CAP
    _CAP = None

def drop_inherited_capture():
    """fork 掛鉤：子程序繼承的擷取一律失效（不能把子程序當成巢狀 executor）。"""
    global _CAP
    _CAP = None

def _valid(cap: Capture | None) -> bool:
    if cap is None or cap.owner_pid != os.getpid(): return False
    return CAPTURE_GUARD is None or CAPTURE_GUARD(cap)

def capturing() -> Capture | None:
    return _CAP if _valid(_CAP) else None

def mark_diagnostic():
    """驗證失敗的程式路徑呼叫：本次只產生允許的診斷寫入，不建立操作計畫（最終規格第 4 章 §13）。"""
    cap = capturing()
    if cap is not None: cap.diagnostic = True

def _require_capture() -> Capture:
    if not _valid(_CAP):
        raise NoExecutorContext("寫入必須經過 executor（取得 flock 的操作）；不能直接寫檔")
    return _CAP

# ---- 時間 ----
def real_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def real_today() -> str:
    return datetime.date.today().strftime("%Y%m%d")

def now() -> str:
    cap = capturing()
    return cap.clock if cap is not None else real_now()

def today() -> str:
    cap = capturing()
    return cap.today if cap is not None else real_today()

# ---- 路徑 ----
def rel(path) -> str:
    """把任意路徑轉成相對 ROOT 的 posix 字串。"""
    p = pathlib.Path(path)
    if p.is_absolute(): return p.resolve().relative_to(ROOT).as_posix()
    return p.as_posix()

def abspath(path) -> pathlib.Path:
    return ROOT / rel(path)

# ---- 讀取（overlay 優先） ----
def read_bytes(path) -> bytes:
    r = rel(path); cap = capturing()
    if cap is not None and r in cap.files:
        data = cap.files[r]
        if data is None: raise FileNotFoundError(str(ROOT / r))
        return data
    p = ROOT / r
    if not p.exists(): raise FileNotFoundError(str(p))
    return p.read_bytes()

def read_text(path) -> str:
    return read_bytes(path).decode("utf-8")

def load(path) -> dict:
    return yaml.safe_load(read_bytes(path).decode("utf-8")) or {}

def exists(path) -> bool:
    r = rel(path); cap = capturing()
    if cap is not None and r in cap.files: return cap.files[r] is not None
    return (ROOT / r).exists()

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def sha256_file(path) -> str:
    return sha256_bytes(read_bytes(path))

def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def match(rel_path: str, pattern: str) -> bool:
    """逐段比對；`*` 不跨 `/`，`**` 代表零或多段。"""
    a, b = rel_path.split("/"), pattern.split("/")
    def go(i, j):
        if j == len(b): return i == len(a)
        if b[j] == "**": return any(go(k, j + 1) for k in range(i, len(a) + 1))
        return i < len(a) and fnmatch.fnmatchcase(a[i], b[j]) and go(i + 1, j + 1)
    return go(0, 0)

def glob(pattern: str) -> list[pathlib.Path]:
    """相對 ROOT 的檔案 glob（支援 `**`）；合併 overlay 新增、排除 overlay 刪除；回傳排序後的絕對路徑。"""
    found = {p.relative_to(ROOT).as_posix() for p in ROOT.glob(pattern) if p.is_file()}
    cap = capturing()
    if cap is not None:
        for r, data in cap.files.items():
            if data is None: found.discard(r)
            elif match(r, pattern): found.add(r)
    return [ROOT / r for r in sorted(found)]

def rglob(base: str, name_pattern: str) -> list[pathlib.Path]:
    return glob(f"{base}/**/{name_pattern}")

def list_dirs(pattern: str) -> list[pathlib.Path]:
    """相對 ROOT 的目錄 glob（含 overlay 中新增檔案所在的目錄）。"""
    found = {p.relative_to(ROOT).as_posix() for p in ROOT.glob(pattern) if p.is_dir()}
    cap = capturing()
    if cap is not None:
        for r, data in cap.files.items():
            if data is None: continue
            parts = r.split("/")
            for k in range(1, len(parts)):
                d = "/".join(parts[:k])
                if match(d, pattern): found.add(d)
    return [ROOT / r for r in sorted(found)]

# ---- 寫入（只能在擷取中） ----
def dump(obj) -> bytes:
    return yaml.safe_dump(obj, allow_unicode=True, sort_keys=False, width=120).encode("utf-8")

def save(path, obj):
    write_bytes(path, dump(obj)); return ROOT / rel(path)

def write_bytes(path, data: bytes, derived: bool = False):
    _require_capture().put(rel(path), data, derived)

def write_text(path, text: str, derived: bool = False):
    write_bytes(path, text.encode("utf-8"), derived)

def write_derived(path, text: str):
    """衍生輸出（md、html、index、export 等可重建的檢視）：排在業務步驟之後，每個檔一步。"""
    write_text(path, text, derived=True)

def delete(path):
    _require_capture().put(rel(path), None)

def audit(run_id: str | None, actor: str, action: str, detail: str = ""):
    """記錄一筆 audit 事件；executor 把它寫成獨立的事件檔（audit.d），不再追加 audit.log。"""
    cap = _require_capture()
    cap.events.append({"run_id": run_id, "actor": actor, "action": action, "detail": detail})
    cap.sequence.append(("event", len(cap.events) - 1))

# ---- entity 路徑約定 ----
def spec_dir(spec_id: str) -> pathlib.Path | None:
    for p in glob(f"specs/*/*/{spec_id}/spec.yaml"): return p.parent
    return None

AREA_RE = re.compile(r"[A-Z0-9]+")   # 同 schemas/common/defs FunctionalArea

def run_area(inputs: dict) -> str | None:
    """run 所屬 functional area（ADR-009），依序：run 的 spec_id → manual record 的 spec_hint.spec_id（皆看 spec 所在目錄）
    → manual record 的 functional_area（須符合 ^[A-Z0-9]+$，與 spec.schema 一致；空白／無效不算）。判定不了回 None，由 new_run 拒絕。"""
    def _spec_area(sid):
        d = spec_dir(sid) if sid else None
        return d.parent.name if d else None
    if inputs.get("spec_id"): return _spec_area(inputs["spec_id"])
    rid = inputs.get("manual_record_id")
    rec = load(f"testcases/manual/{rid}.yaml") if rid and exists(f"testcases/manual/{rid}.yaml") else {}
    area = _spec_area((rec.get("spec_hint") or {}).get("spec_id"))
    if area: return area
    fa = (rec.get("functional_area") or "").strip()
    return fa if AREA_RE.fullmatch(fa) else None

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
    for p in glob(f"bugs/*/*/{bug_id}.yaml"): return p
    return None

def find_artifact(artifact_id: str) -> pathlib.Path | None:
    for p in rglob("artifacts", f"{artifact_id}.yaml"): return p
    return None

def find_execution(exe_id: str) -> pathlib.Path | None:
    for p in rglob("executions", f"{exe_id}.yaml"): return p
    return None

def find_evidence(evd_id: str) -> pathlib.Path | None:
    for p in rglob("evidence", f"{evd_id}.yaml"): return p
    return None

def find_suite(suite_id: str) -> pathlib.Path | None:
    for p in rglob("testsuites", f"{suite_id}.yaml"): return p
    return None

def clarification_path(product: str, area: str, clr_id: str) -> str:
    return f"clarifications/{product}/{area}/{clr_id}.yaml"

def find_clarification(clr_id: str) -> pathlib.Path | None:
    for p in glob(f"clarifications/*/*/{clr_id}.yaml"): return p
    return None
