"""Executor：全域操作鎖（flock）、操作計畫、續做、audit 事件檔、維護模式與准入（最終規格第 4 章）。

一次寫入操作的流程（run_operation）：
  取得 flock → 第 0 步（全域終態一致性核對）→ 登錄補齊 → 第 1～3 步（目標計畫／續做驗證／新請求准入）
  → 以擷取（store overlay）執行業務邏輯 → 產生計畫（每個 path 一步、no_change、固定 clock 與事件 payload）
  → 原子保存計畫（即已建立）→ 登錄 → 依序執行步驟（輸出 → fsync → 完成紀錄）→ completed 狀態紀錄 → 釋放鎖。
"""
from __future__ import annotations
import os, re, json, uuid, errno, fcntl, socket, hashlib, functools, pathlib, datetime, yaml
from dataclasses import dataclass
from . import store

# ---------------------------------------------------------------- 路徑
LOCK_PATH = "locks/qaos-operation.lock"
OWNER_PATH = "locks/qaos-operation.owner"
MAINT_PATH = "locks/maintenance.yaml"
MARKER_PATH = "artifacts/requirements/_migration.yaml"
GLOBAL = "_global"
INDEX_DIR = f"operations/{GLOBAL}/index.d"
STATUS_DIR = f"operations/{GLOBAL}/status.d"
STAGING_DIR = "operations/_global/staging.d"   # 計畫保存前的寫入清單（executor 擁有權的證據）

CONTROL_ACTIONS = {"maintenance_start", "maintenance_end", "migrate", "migrate_rollback"}
TERMINAL = ("aborted_for_rollback", "rolled_back")
AUDIT_KINDS = {"event", "control", "index", "status", "progress"}

class OperationError(Exception): pass
class LockHeld(OperationError): pass
class ContextInvalid(OperationError): pass
class Refused(OperationError): pass
class EvidenceConflict(OperationError): pass

# ---------------------------------------------------------------- 故障注入（只供測試）
def _faults() -> set[str]:
    return {f.strip() for f in os.environ.get("QAOS_FAULT", "").split(",") if f.strip()}

def fault(point: str):
    """QAOS_FAULT=<point>：在該點立即結束程序（模擬崩潰）；QAOS_FAULT=raise:<point>：在該點拋出例外。"""
    fs = _faults()
    if point in fs: os._exit(86)
    if f"raise:{point}" in fs: raise OSError(f"injected fault at {point}")

def pause(point: str):
    """QAOS_PAUSE=<point>=<dir>：在該點建立 <dir>/paused，等到 <dir>/go 出現才繼續（只供測試的同步點）。"""
    spec = os.environ.get("QAOS_PAUSE", "")
    if not spec or "=" not in spec: return
    pt, d = spec.split("=", 1)
    if pt != point: return
    import time
    d = pathlib.Path(d); d.mkdir(parents=True, exist_ok=True); (d / "paused").write_text(str(os.getpid()))
    deadline = time.monotonic() + 60
    while not (d / "go").exists():
        if time.monotonic() > deadline: os._exit(87)
        time.sleep(0.02)

# ---------------------------------------------------------------- flock executor（§4）
@dataclass(eq=False)
class Context:
    token: str
    fd: int
    owner_pid: int
    op_id: str | None = None

_EXECUTOR: Context | None = None
LAST_OUTCOME: dict = {}     # 最近一次 run_operation 的結果類型：new | completed | resumed（CLI 用來提示）
_HOOK_REGISTERED = False

def _drop_inherited_lock():
    """fork 掛鉤，只在子程序執行：只關閉繼承到的 fd，絕不 LOCK_UN（會解除父程序的鎖）。"""
    global _EXECUTOR
    store.drop_inherited_capture()        # 子程序繼承的擷取一律失效
    ex = _EXECUTOR
    if ex is None: return
    _EXECUTOR = None
    try: os.close(ex.fd)
    except OSError: pass

def acquire(op_id: str | None = None) -> Context:
    global _EXECUTOR, _HOOK_REGISTERED
    lp = store.ROOT / LOCK_PATH
    lp.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(lp, os.O_RDWR | os.O_CREAT | os.O_CLOEXEC, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(fd)
        raise LockHeld(f"鎖由其他 executor 持有（{_owner_info()}）；請稍後再試，或以 `operation list` 查看未完成的計畫")
    ctx = Context(token=uuid.uuid4().hex, fd=fd, owner_pid=os.getpid(), op_id=op_id)
    _EXECUTOR = ctx
    if not _HOOK_REGISTERED:
        os.register_at_fork(after_in_child=_drop_inherited_lock); _HOOK_REGISTERED = True
    return ctx

def release(ctx: Context):
    global _EXECUTOR
    require_context(ctx)
    _EXECUTOR = None
    os.close(ctx.fd)

def require_context(ctx: Context | None):
    if _EXECUTOR is None or ctx is not _EXECUTOR or ctx.token != _EXECUTOR.token or ctx.owner_pid != os.getpid():
        raise ContextInvalid("executor context 已失效（不是目前持有鎖的程序）")

def current() -> Context | None:
    return _EXECUTOR

def _capture_guard(cap) -> bool:
    """擷取只屬於建立它、而且仍持有 executor context 的程序。"""
    ex = _EXECUTOR
    return ex is not None and ex.owner_pid == os.getpid() and cap.owner_pid == os.getpid() and cap.owner_token == ex.token

store.CAPTURE_GUARD = _capture_guard

def _write_owner(ctx: Context):
    """診斷檔：只供顯示，不是權威。"""
    info = {"op_id": ctx.op_id, "pid": os.getpid(), "host": socket.gethostname(), "started_at": store.real_now()}
    _atomic_replace(OWNER_PATH, store.dump(info), tag="owner")

def _owner_info() -> str:
    p = store.ROOT / OWNER_PATH
    try: d = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except Exception: return "持有者資訊不可得"
    return f"診斷檔記錄 op={d.get('op_id')} pid={d.get('pid')} host={d.get('host')} since={d.get('started_at')}（可能已過期）"

# ---------------------------------------------------------------- canonical request 與 op_id（§3）
def canonical(obj) -> bytes:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")

def op_id_of(request: dict) -> str:
    return hashlib.sha256(canonical(request)).hexdigest()

def normalize(v):
    """把呼叫參數轉成可 canonical 化的形式；路徑一律換成 {path, sha256}。"""
    if isinstance(v, pathlib.Path):
        p = v.resolve()
        try: return {"path": p.relative_to(store.ROOT).as_posix()}   # root 內的檔可能被操作本身改寫：只用路徑
        except ValueError: return {"path": str(p), "sha256": store.sha256_bytes(p.read_bytes()) if p.is_file() else None}
    if isinstance(v, dict): return {str(k): normalize(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)): return [normalize(x) for x in v]
    if v is None or isinstance(v, (bool, int, float, str)): return v
    return str(v)

# ---------------------------------------------------------------- 低階寫入（只由 executor 使用）
def _fsync_dir(d: pathlib.Path):
    try:
        fd = os.open(d, os.O_RDONLY)
        try: os.fsync(fd)
        finally: os.close(fd)
    except OSError: pass

def _tmp_name(target: pathlib.Path, tag: str) -> pathlib.Path:
    return target.parent / f".qaos-tmp-{tag}-{target.name}-{uuid.uuid4().hex[:8]}"

def _write_tmp(tmp: pathlib.Path, data: bytes, point: str | None = None):
    """寫暫存檔並 fsync。測試用：QAOS_FAULT=short:<point>／empty:<point> 只寫一半／零位元組後立即結束（模擬短寫）。"""
    fs = _faults() if point else set()
    cut = len(data) // 2 if f"short:{point}" in fs else 0 if f"empty:{point}" in fs else None
    with open(tmp, "wb") as f:
        f.write(data if cut is None else data[:cut]); f.flush(); os.fsync(f.fileno())
    if cut is not None: os._exit(86)

def _atomic_replace(rel_path: str, data: bytes, tag: str, point: str | None = None):
    t = store.ROOT / rel_path; t.parent.mkdir(parents=True, exist_ok=True)
    tmp = _tmp_name(t, tag)
    _write_tmp(tmp, data)
    if point: fault(point)
    os.replace(tmp, t); _fsync_dir(t.parent)

def _link_create(rel_path: str, data: bytes, tag: str, pause_point: str | None = None, point: str | None = None) -> bool:
    """暫存檔 → fsync → link 到目標（已存在就失敗）→ 刪暫存檔。回傳 True 表示新建立；已存在且內容相同回傳 False。"""
    t = store.ROOT / rel_path; t.parent.mkdir(parents=True, exist_ok=True)
    tmp = _tmp_name(t, tag)
    _write_tmp(tmp, data, point)
    if pause_point: pause(pause_point)
    try:
        os.link(tmp, t); _fsync_dir(t.parent); return True
    except FileExistsError:
        if t.read_bytes() == data: return False
        raise EvidenceConflict(f"{rel_path} 已存在但內容不同")
    finally:
        try: os.unlink(tmp)
        except OSError: pass

def _delete(rel_path: str):
    t = store.ROOT / rel_path
    try: t.unlink(); _fsync_dir(t.parent)
    except FileNotFoundError: pass

def _cur_sha(rel_path: str) -> str | None:
    p = store.ROOT / rel_path
    return store.sha256_bytes(p.read_bytes()) if p.is_file() else None

def _clean_tmp(plan: dict):
    """續做前只清除本 op 的殘留暫存檔；其他 op 的暫存檔一律不動。"""
    tag = plan["op_id"][:16]
    dirs = {(store.ROOT / s["path"]).parent for s in plan["steps"]}
    for d in dirs:
        if d.is_dir():
            for f in d.glob(f".qaos-tmp-{tag}-*"):
                try: f.unlink()
                except OSError: pass

# ---------------------------------------------------------------- 系統狀態（§5）
def marker() -> dict | None:
    p = store.ROOT / MARKER_PATH
    return yaml.safe_load(p.read_text(encoding="utf-8")) if p.is_file() else None

def maintenance() -> dict | None:
    p = store.ROOT / MAINT_PATH
    return yaml.safe_load(p.read_text(encoding="utf-8")) if p.is_file() else None

def system_state() -> str:
    if (store.ROOT / MAINT_PATH).is_file(): return "S_maint"
    return "S_post" if (store.ROOT / MARKER_PATH).is_file() else "S_pre"

# ---------------------------------------------------------------- 計畫、登錄、狀態紀錄
def plan_path(scope: str, op_id: str) -> str: return f"operations/{scope}/{op_id}.yaml"
def op_dir(scope: str, op_id: str) -> str: return f"operations/{scope}/{op_id}"
def blob_path(scope: str, op_id: str, sha: str) -> str: return f"{op_dir(scope, op_id)}/blobs/{sha}"
def progress_path(plan: dict, step: dict) -> str: return f"{op_dir(plan['scope'], plan['op_id'])}/progress.d/{step['seq']:04d}-{step['step_id']}.yaml"
def status_path(op_id: str, status: str) -> str: return f"{STATUS_DIR}/{op_id}-{status}.yaml"

def progress_bytes(plan: dict, step: dict) -> bytes:
    return store.dump({"op_id": plan["op_id"], "seq": step["seq"], "step_id": step["step_id"], "path": step["path"], "after_sha256": step["expected_after"]})

def registrations() -> dict[str, dict]:
    """op_id → 登錄紀錄（含 _file）。同一 op 有兩筆以上 → 證據衝突。"""
    out = {}
    d = store.ROOT / INDEX_DIR
    if not d.is_dir(): return out
    for p in sorted(d.glob("*.yaml")):
        if p.name.startswith(".qaos-tmp"): continue
        rec = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        op = rec.get("op_id")
        if set(rec) != REG_FIELDS or not isinstance(rec.get("plan_seq"), int) or p.name != f"{rec['plan_seq']:08d}-{op}.yaml":
            raise EvidenceConflict(f"登錄紀錄 {p.name} 的欄位或檔名不符")
        if op in out: raise EvidenceConflict(f"op {op} 有兩筆登錄紀錄")
        rec["_file"] = p.name; out[op] = rec
    # plan_seq 在持鎖下以 max+1 配發、link-create 寫入，所以必定是 1..N 連續且不重複；不是 → 有人改過登錄紀錄
    seqs = sorted(r["plan_seq"] for r in out.values())
    if seqs != list(range(1, len(seqs) + 1)): raise EvidenceConflict(f"登錄紀錄的 plan_seq 不符（不連續或重複）：{seqs[:5]}…")
    return out

REG_FIELDS = {"plan_seq", "op_id", "action", "plan_sha256", "registered_at"}

def verify_registration(op: str, reg: dict | None = None) -> dict:
    """涉及某個 op 的續做、已完成回報與盤點時，核對登錄紀錄與不可變計畫的一致性（附錄 A 4-11）。回傳計畫。"""
    reg = reg or registrations().get(op)
    p = plan_files().get(op)
    if reg is None or p is None: raise EvidenceConflict(f"op {op} 缺少登錄紀錄或計畫檔")
    data = p.read_bytes(); plan = yaml.safe_load(data.decode("utf-8")) or {}
    bad = [k for k, ok in (("plan_sha256", reg["plan_sha256"] == store.sha256_bytes(data)), ("action", reg["action"] == plan.get("action")),
                           ("registered_at", reg["registered_at"] == plan.get("clock")), ("op_id", plan.get("op_id") == op)) if not ok]
    if bad: raise EvidenceConflict(f"V1：op {op} 的登錄紀錄和計畫不符（{', '.join(bad)}）")
    st = statuses(op)
    if "completed" in st:
        expect = store.dump({"op_id": op, "status": "completed", "at": plan["clock"]})
        if (store.ROOT / status_path(op, "completed")).read_bytes() != expect:
            raise EvidenceConflict(f"op {op} 的 completed 狀態紀錄內容不符")
    return plan

def plan_files() -> dict[str, pathlib.Path]:
    out = {}
    base = store.ROOT / "operations"
    if not base.is_dir(): return out
    for p in base.glob("*/*.yaml"):
        out[p.stem] = p
    return out

def load_plan(op_id: str) -> dict | None:
    p = plan_files().get(op_id)
    return yaml.safe_load(p.read_text(encoding="utf-8")) if p else None

def statuses(op_id: str) -> set[str]:
    d = store.ROOT / STATUS_DIR
    if not d.is_dir(): return set()
    return {p.name[len(op_id) + 1:-5] for p in d.glob(f"{op_id}-*.yaml")}

def plan_state(op_id: str) -> str:
    st = statuses(op_id)
    for t in TERMINAL:
        if t in st: return t
    return "completed" if "completed" in st else "in_progress"

def incomplete_plans() -> list[str]:
    return [op for op in registrations() if plan_state(op) == "in_progress"]

def _register(plan: dict, plan_bytes: bytes):
    regs = registrations()
    if plan["op_id"] in regs:
        if regs[plan["op_id"]]["plan_sha256"] != store.sha256_bytes(plan_bytes):
            raise EvidenceConflict(f"{plan['op_id']} 的登錄紀錄和計畫檔不符")
        return
    seq = max([r["plan_seq"] for r in regs.values()], default=0) + 1
    rec = {"plan_seq": seq, "op_id": plan["op_id"], "action": plan["action"], "plan_sha256": store.sha256_bytes(plan_bytes), "registered_at": plan["clock"]}
    _link_create(f"{INDEX_DIR}/{seq:08d}-{plan['op_id']}.yaml", store.dump(rec), tag=plan["op_id"][:16])

# ---------------------------------------------------------------- 第 0 步：全域終態一致性核對（§6.1）
def check_terminal_consistency():
    """每份已登錄的 rollback 計畫，依它不可變的 terminal 群組核對前綴；不一致 → 拒絕本次寫入請求，不做任何持久寫入。"""
    for op, reg in registrations().items():
        if reg.get("action") != "migrate_rollback": continue
        plan = verify_registration(op, reg)
        group = [s["path"] for s in plan.get("steps", []) if s.get("group") == "terminal"]
        present = [(store.ROOT / p).is_file() for p in group]
        seen_missing = False
        for path, ok in zip(group, present):
            if not ok: seen_missing = True
            elif seen_missing:
                raise Refused(f"終態不一致：rollback 計畫 {op} 的 {path} 存在，但排在它前面的終態步驟不存在；需人工處理")

# ---------------------------------------------------------------- 登錄補齊（§6.2）
_HEX64 = re.compile(r"[0-9a-f]{64}")
_RUN_SCOPE = re.compile(r"RUN-[0-9]{8}-[0-9]{3,}")
STAGING_KIND = "qaos-plan-staging"

def _staging_manifest(plan: dict, blobs: dict) -> bytes:
    """計畫保存前、寫任何內容檔之前，先記下本 op 將寫的確切檔案；清理只依這份清單刪除。"""
    return store.dump({"kind": STAGING_KIND, "op_id": plan["op_id"], "scope": plan["scope"], "at": plan["clock"], "blobs": sorted(blobs)})

def _parse_manifest(data: bytes, op: str) -> dict | None:
    try: m = yaml.safe_load(data.decode("utf-8"))
    except Exception: return None
    ok = (isinstance(m, dict) and set(m) == {"kind", "op_id", "scope", "at", "blobs"} and m["kind"] == STAGING_KIND and m["op_id"] == op
          and isinstance(m["scope"], str) and (m["scope"] == GLOBAL or _RUN_SCOPE.fullmatch(m["scope"]))
          and isinstance(m["blobs"], list) and all(isinstance(b, str) and _HEX64.fullmatch(b) for b in m["blobs"]))
    return m if ok else None

def _no_symlink_path(p: pathlib.Path):
    """從 ROOT 到 p 的每一層（含 p 本身）都不能是 symlink；否則證據衝突（不沿 symlink 刪到 root 之外或清單之外的檔案）。"""
    cur = store.ROOT
    for part in p.relative_to(store.ROOT).parts:
        cur = cur / part
        if cur.is_symlink(): raise EvidenceConflict(f"{cur.relative_to(store.ROOT)} 是 symlink，需人工處理")

def _claim_path(op: str) -> pathlib.Path: return store.ROOT / STAGING_DIR / f"{op}.claim"

def cleanup_unplanned():
    """持鎖中清除「計畫檔保存之前就中止」留下的殘留（AC-07-68、98d；附錄 A 4-18）。
    1. 有登錄紀錄卻沒有計畫檔的 op → 證據衝突，拒絕本次寫入；在清理任何東西之前檢查。
    2. 擁有權的證據（都由 executor 在寫入前建立）：
       - `staging.d/<op>.claim`：零位元組、以 O_EXCL 建立（不會半寫），最先建立、最後刪除；沒有它，本 op 在 staging.d 的任何檔案都不算 executor 的；
       - `staging.d/<op>.yaml`：寫入清單，在 op 目錄不存在時才建立，列出本 op 將新建的內容檔。
    3. 先核對全部待刪路徑（每一層都不是 symlink、清單列出的內容檔內容等於其 hash），全部通過才刪；任何一項不符 → 證據衝突，不刪任何東西。
    4. 沒有證據的內容一律不刪；看起來像 op 目錄（64 位 hex）卻沒有計畫也沒有證據的，保留並回報。"""
    import sys
    base = store.ROOT / "operations"
    if not base.is_dir(): return
    plans, regs = plan_files(), registrations()
    missing = sorted(set(regs) - set(plans))
    if missing: raise EvidenceConflict(f"op {', '.join(missing)} 有登錄紀錄卻沒有計畫檔，需人工處理")
    def report(x): print(f"qaos: 保留無法辨識的內容 {x.relative_to(store.ROOT)}（沒有計畫，也沒有 executor 的寫入證據）", file=sys.stderr)
    staging = store.ROOT / STAGING_DIR
    if os.path.lexists(staging): _no_symlink_path(staging)
    files_rm: list[pathlib.Path] = []; dirs_rm: list[pathlib.Path] = []; last_rm: list[pathlib.Path] = []; owned: set[str] = set()
    if staging.is_dir():
        entries = sorted(staging.iterdir())
        ops = {m.group(1) for f in entries if (m := re.fullmatch(r"([0-9a-f]{64})\.(?:claim|yaml)", f.name))}
        tmp_of = {}
        for f in entries:
            m = re.fullmatch(r"\.qaos-tmp-([0-9a-f]{16})-([0-9a-f]{64})\.yaml-[0-9a-f]{8}", f.name)
            if m and m.group(2).startswith(m.group(1)): tmp_of.setdefault(m.group(2), []).append(f)
        for f in entries:
            if not (re.fullmatch(r"[0-9a-f]{64}\.(?:claim|yaml)", f.name) or any(f in v for v in tmp_of.values())): report(f)
        for op in sorted(ops | set(tmp_of)):
            claim, man_p = _claim_path(op), staging / f"{op}.yaml"
            if not claim.is_file() or claim.is_symlink():            # 沒有認領檔 → 不能證明屬於 executor（認領檔最先建立、最後刪除）
                for t in [man_p, *tmp_of.get(op, [])]:
                    if os.path.lexists(t): report(t)
                continue
            for x in [claim, man_p, *tmp_of.get(op, [])]:
                if x.is_symlink() or (x.exists() and not x.is_file()): raise EvidenceConflict(f"{x.relative_to(store.ROOT)} 不是一般檔案，需人工處理")
            man = _parse_manifest(man_p.read_bytes(), op) if man_p.is_file() else None
            if man_p.is_file() and man is None:
                raise EvidenceConflict(f"{man_p.relative_to(store.ROOT)} 不是有效的寫入清單（清單以 link 完整建立，不會半寫），需人工處理")
            if op not in plans and man is not None:                  # 計畫未保存：只刪清單列出、而且內容相符的檔案
                sd = store.ROOT / "operations" / man["scope"]; d = sd / op; b = d / "blobs"
                for x in (sd, d, b):
                    if os.path.lexists(x): _no_symlink_path(x)
                for sha in man["blobs"]:
                    t = b / sha
                    if t.is_symlink() or (t.exists() and not t.is_file()): raise EvidenceConflict(f"{t.relative_to(store.ROOT)} 不是一般檔案，需人工處理")
                    if t.is_file():
                        if hashlib.sha256(t.read_bytes()).hexdigest() != sha: raise EvidenceConflict(f"{t.relative_to(store.ROOT)} 的內容和清單不符，需人工處理")
                        files_rm.append(t)
                if b.is_dir():
                    pat = re.compile(rf"\.qaos-tmp-{op[:16]}-({'|'.join(man['blobs']) or 'x^'})-[0-9a-f]{{8}}")
                    for x in b.iterdir():
                        if pat.fullmatch(x.name):
                            if x.is_symlink() or not x.is_file(): raise EvidenceConflict(f"{x.relative_to(store.ROOT)} 不是一般檔案，需人工處理")
                            files_rm.append(x)
                if sd.is_dir():
                    for x in sd.glob(f".qaos-tmp-{op[:16]}-{op}.yaml-*"):
                        if x.is_symlink() or not x.is_file(): raise EvidenceConflict(f"{x.relative_to(store.ROOT)} 不是一般檔案，需人工處理")
                        files_rm.append(x)
                dirs_rm += [b, d]; owned.add(op)
            # 只有認領、沒有清單：內容檔在清單建立之後才寫，所以只需刪 staging.d 中的證據與暫存
            last_rm += [*tmp_of.get(op, []), man_p, claim]           # 證據最後刪：清理途中中止，下一次仍能依同一份證據繼續
    for f in files_rm: f.unlink(); fault("cleanup_mid")
    for d in dirs_rm:
        if d.is_dir() and not any(d.iterdir()): d.rmdir()
        elif d.exists(): report(d)                                   # 清單之外還有東西：保留並回報
    for f in last_rm:
        if f.exists(): f.unlink()
    for scope in sorted(base.iterdir()):
        if scope.is_symlink() or not scope.is_dir() or not (scope.name == GLOBAL or _RUN_SCOPE.fullmatch(scope.name)): continue
        for d in sorted(scope.iterdir()):
            if d.is_dir() and _HEX64.fullmatch(d.name) and d.name not in plans and d.name not in owned: report(d)

def reconcile_registrations():
    regs = registrations()
    for op, p in plan_files().items():
        if op in regs or op.startswith("adhoc-"): continue
        data = p.read_bytes()
        plan = yaml.safe_load(data.decode("utf-8")) or {}
        errs = _plan_errors(plan)
        if errs or plan.get("op_id") != op or op_id_of(plan.get("canonical_request", {})) != op:
            raise Refused(f"未登錄的計畫檔 {store.rel(p)} 不合法（{'; '.join(errs) or 'op_id 和 canonical_request 不對應'}）；拒絕所有寫入，需人工處理")
        _register(plan, data)

def _plan_errors(plan: dict) -> list[str]:
    from . import schema
    return schema.errors(plan, "workflow/operation-plan.schema.json")

# ---------------------------------------------------------------- 准入（§6.5）與 resume_states（§8.2）
def admit(action: str, state: str):
    mk = (store.ROOT / MARKER_PATH).is_file()
    ok = {
        "maintenance_start": state in ("S_pre", "S_post"),
        "maintenance_end": state == "S_maint",
        "migrate": state == "S_maint" and not mk,
        "migrate_rollback": state == "S_maint",
        "run_cancel": state in ("S_pre", "S_post"),
    }.get(action, state == "S_post")
    if ok: return
    reason = {"S_pre": "尚未移轉", "S_maint": "維護中", "S_post": "已移轉"}[state]
    if action == "maintenance_start" and state == "S_maint": reason = "已在維護中"
    if action == "maintenance_end": reason = "不在維護中"
    if action == "migrate" and state == "S_maint": reason = "已移轉（移轉標記已存在）"
    if action in ("migrate", "migrate_rollback") and state != "S_maint": reason = "必須先進入維護（maintenance start）"
    raise Refused(f"{action} 在目前狀態 {state} 不允許：{reason}")

def resume_states_for(action: str, state: str) -> dict:
    """建立計畫時記錄續做時接受的狀態。"""
    mk = (store.ROOT / MARKER_PATH).is_file()
    m = maintenance()
    if action == "maintenance_start": return {"kind": "maintenance_start", "admitted": state}
    if action == "maintenance_end":
        return {"kind": "maintenance_end", "maint_sha256": _cur_sha(MAINT_PATH), "marker_present": mk}
    if action == "migrate": return {"kind": "migrate"}
    if action == "migrate_rollback": return {"kind": "migrate_rollback"}
    if action == "run_cancel": return {"kind": "fixed", "states": [state]}
    return {"kind": "fixed", "states": ["S_post"]}

def check_resume_state(plan: dict):
    rs, state, op = plan["resume_states"], system_state(), plan["op_id"]
    k = rs["kind"]
    if k == "fixed": ok = state in rs["states"]
    elif k == "maintenance_start":
        m = maintenance()
        ok = (state == rs["admitted"] and m is None) or (state == "S_maint" and m is not None and m.get("op_id") == op)
        if state == "S_maint" and m is not None and m.get("op_id") != op:
            raise Refused(f"續做 {op}：維護檔屬於其他 op（{m.get('op_id')}），身分不符")
    elif k == "maintenance_end":
        ok = (state == "S_maint" and _cur_sha(MAINT_PATH) == rs["maint_sha256"]) or \
             (maintenance() is None and (store.ROOT / MARKER_PATH).is_file() == rs["marker_present"])
    elif k == "migrate":
        mk = marker()
        ok = state == "S_maint" and (mk is None or mk.get("migrate_op_id") == op)
        if state == "S_maint" and mk is not None and mk.get("migrate_op_id") != op:
            raise Refused(f"續做 {op}：移轉標記屬於其他 op（{mk.get('migrate_op_id')}），身分不符")
    elif k == "migrate_rollback":
        mk = marker()
        ok = state == "S_maint" and (mk is None or mk.get("migrate_op_id") == plan.get("takeover_of"))
    else: ok = False
    if not ok: raise Refused(f"續做 {op}（{plan['action']}）：目前狀態 {state} 不在它的 resume_states")

# ---------------------------------------------------------------- classify_steps（§8.3）
@dataclass
class Classified:
    status: dict            # seq → done | tail | not_executed | conflict | external_change
    conflicts: list
    external: list
    no_change_issues: list

def classify_steps(plan: dict) -> Classified:
    steps = [s for s in plan["steps"] if s.get("kind") != "status_final"]
    outs, recs = {}, {}
    for s in steps:
        cur = _cur_sha(s["path"])
        outs[s["seq"]] = "after" if cur == s["expected_after"] else ("before" if cur == s["expected_before"] else "other")
        pp = store.ROOT / progress_path(plan, s)
        if not pp.is_file(): recs[s["seq"]] = "absent"
        else: recs[s["seq"]] = "present" if pp.read_bytes() == progress_bytes(plan, s) else "bad"
    L = max([s["seq"] for s in steps if outs[s["seq"]] == "after" or recs[s["seq"]] == "present"], default=0)
    status, conflicts, external = {}, [], []
    for s in steps:
        q, o, r = s["seq"], outs[s["seq"]], recs[s["seq"]]
        audit_obj = s["kind"] in AUDIT_KINDS
        def bad(reason):
            if audit_obj: conflicts.append({"seq": q, "path": s["path"], "reason": reason}); status[q] = "conflict"
            else: external.append({"seq": q, "path": s["path"], "reason": reason}); status[q] = "external_change"
        if r == "bad": conflicts.append({"seq": q, "path": s["path"], "reason": "完成紀錄被竄改"}); status[q] = "conflict"; continue
        if o == "other": bad("內容既不是 before 也不是 after"); continue
        if q < L:
            if o == "after" and r == "present": status[q] = "done"
            elif o == "after": conflicts.append({"seq": q, "path": s["path"], "reason": "尾端之前缺完成紀錄"}); status[q] = "conflict"
            else: bad("已證實執行過的步驟，輸出不存在或被還原")
        elif q == L:
            if o == "after": status[q] = "done" if r == "present" else "tail"
            else: bad("有完成紀錄，輸出卻不存在或被還原")
        else:
            status[q] = "not_executed"
    issues = []
    for nc in plan.get("no_change", []):
        if _cur_sha(nc["path"]) != nc["content_sha256"]:
            item = {"path": nc["path"], "reason": "no_change 路徑被改動"}
            (conflicts if nc.get("kind") in AUDIT_KINDS else external).append(item); issues.append(item)
    return Classified(status, conflicts, external, issues)

# ---------------------------------------------------------------- 計畫產生
def _event_path(op_id: str, run_id: str | None, step: int) -> str:
    base = f"runs/{run_id}/audit.d" if run_id else "runs/_audit.d"
    return f"{base}/{op_id}-{step}.yaml"

def _event_payload(cap: store.Capture, op_id: str, idx: int) -> dict:
    e = cap.events[idx]
    return {"at": cap.clock, "actor": e["actor"], "action": e["action"], "detail": e["detail"] or "", "op_id": op_id, "step": idx + 1, "run_id": e["run_id"]}

def _disk_bytes(rel_path: str) -> bytes | None:
    p = store.ROOT / rel_path
    return p.read_bytes() if p.is_file() else None

def build_plan(cap: store.Capture, *, op_id: str, request: dict, action: str, scope: str, state: str, result) -> tuple[dict, dict]:
    """把擷取結果變成計畫；回傳 (plan, blobs: sha → bytes)。"""
    steps, no_change, blobs, events = [], [], {}, []
    seq = 0
    def add(path, kind, after: bytes | None, group=None, sid=None):
        nonlocal seq
        before = _disk_bytes(path)
        if before == after:
            no_change.append({"path": path, "kind": kind, "content_sha256": store.sha256_bytes(after) if after is not None else None}); return
        seq += 1
        st = {"seq": seq, "step_id": sid or f"s{seq}", "path": path, "kind": kind,
              "expected_before": store.sha256_bytes(before) if before is not None else None,
              "expected_after": store.sha256_bytes(after) if after is not None else None,
              "blob": store.sha256_bytes(after) if after is not None else None}
        if group: st["group"] = group
        if after is not None: blobs[st["blob"]] = after
        steps.append(st)
    # 1. 業務檔與事件（依擷取序列）
    for item in cap.sequence:
        if item[0] == "file":
            r = item[1]
            if r in cap.derived: continue
            add(r, "business", cap.files[r])
        else:
            idx = item[1]; ev = _event_payload(cap, op_id, idx); events.append(ev)
            add(_event_path(op_id, ev["run_id"], idx + 1), "event", store.dump(ev), sid=f"event{idx + 1}")
    # 2. 衍生輸出
    for item in cap.sequence:
        if item[0] == "file" and item[1] in cap.derived:
            add(item[1], "business", cap.files[item[1]], sid=f"derived{len(steps) + 1}")
    # 3. audit.log render（移轉標記存在於計畫完成後的狀態時）
    for path, data in render_logs(cap, events).items():
        add(path, "business", data, sid=f"render{len(steps) + 1}")
    # 4. completed 狀態紀錄（最後一步，沒有完成紀錄）
    seq += 1
    done = store.dump({"op_id": op_id, "status": "completed", "at": cap.clock})
    blobs[store.sha256_bytes(done)] = done
    steps.append({"seq": seq, "step_id": "completed", "path": status_path(op_id, "completed"), "kind": "status_final",
                  "expected_before": None, "expected_after": store.sha256_bytes(done), "blob": store.sha256_bytes(done)})
    plan = {"plan_schema": 1, "op_id": op_id, "action": action, "scope": scope, "canonical_request": request, "request_hash": op_id,
            "admitted_state": state, "resume_states": resume_states_for(action, state), "clock": cap.clock,
            "allocated_ids": list(cap.allocated_ids), "steps": steps, "no_change": no_change, "audit_events": events,
            "result": json.loads(json.dumps(result, ensure_ascii=False, default=str))}
    return plan, blobs

# ---------------------------------------------------------------- audit.log render（§10）
def _format_line(ev: dict, global_log: bool) -> str:
    line = f"{ev['at']}\t{ev['actor']}\t{ev['action']}\t{ev.get('detail') or ''}\n"
    return f"{ev.get('run_id') or '-'}\t{line}" if global_log else line

def _all_events(pattern: str) -> list[dict]:
    out = []
    for p in (store.ROOT).glob(pattern):
        if p.is_file() and not p.name.startswith(".qaos-tmp"):
            out.append(yaml.safe_load(p.read_text(encoding="utf-8")))
    return out

def render_log_bytes(log_rel: str, extra_events: list[dict], mk: dict, overlay: dict | None = None) -> bytes:
    """legacy 原位元組（frozen 時驗證 hash）＋依 (at, op_id, step) 排序的事件。"""
    global_log = log_rel == "runs/_audit.log"
    if global_log: evs = _all_events("runs/*/audit.d/*.yaml") + _all_events("runs/_audit.d/*.yaml")
    else: evs = _all_events(f"{log_rel.rsplit('/', 1)[0]}/audit.d/*.yaml")
    keys = {(e["op_id"], e["step"]) for e in evs}
    for e in extra_events:
        if (global_log or f"runs/{e['run_id']}/audit.log" == log_rel) and (e["op_id"], e["step"]) not in keys: evs.append(e)
    evs.sort(key=lambda e: (str(e["at"]), str(e["op_id"]), int(e["step"])))
    head = b""
    info = (mk.get("logs") or {}).get(log_rel)
    if info is not None:
        legacy = info.get("legacy")
        if legacy == "frozen":
            legacy_rel = log_rel.replace("audit.log", "audit.legacy.log")
            lb = _disk_bytes(legacy_rel)
            if lb is None or store.sha256_bytes(lb) != info.get("sha256"):
                raise Refused(f"render {log_rel}：legacy 檔 {legacy_rel} 不存在或 hash 不符")
            head = lb
        elif legacy != "absent":
            raise Refused(f"render {log_rel}：移轉標記中的 legacy 狀態不合法（{legacy!r}）")
    elif global_log:
        raise Refused("render runs/_audit.log：移轉標記中缺少全域 log 的 legacy 狀態")
    else:   # 標記中沒有它：只有能證明是移轉之後才建立的 run，才只用事件
        run_id = log_rel.split("/")[1]
        rr = f"runs/{run_id}/run.yaml"
        run = overlay[rr] if overlay and rr in overlay else _disk_bytes(rr)
        created = (yaml.safe_load(run.decode("utf-8")) or {}).get("created_at") if run else None
        try: after_migration = created is not None and parse_ts(created) >= parse_ts(mk.get("migrated_at"))
        except ValueError: after_migration = False          # 缺時區或格式不合法 → 不能證明，拒絕
        if run_id in (mk.get("runs") or []) or not after_migration:
            raise Refused(f"render {log_rel}：移轉標記中沒有它的 legacy 狀態，也無法證明它是移轉後建立的 run")
    return head + "".join(_format_line(e, global_log) for e in evs).encode("utf-8")

def render_logs(cap: store.Capture, events: list[dict], logs: list[str] | None = None) -> dict[str, bytes]:
    """依計畫完成後的移轉標記，重建受影響的 audit.log；標記不存在時不 render。"""
    mk_bytes = cap.files[MARKER_PATH] if MARKER_PATH in cap.files else _disk_bytes(MARKER_PATH)
    if mk_bytes is None: return {}
    mk = yaml.safe_load(mk_bytes.decode("utf-8")) or {}
    if logs is None:
        logs = sorted({f"runs/{e['run_id']}/audit.log" for e in events if e["run_id"]}) + (["runs/_audit.log"] if events else [])
        if MARKER_PATH in cap.files:   # 移轉本身：第一次 render 所有 legacy log
            logs = sorted(set(logs) | set((mk.get("logs") or {}).keys()))
    out = {}
    for lg in logs:
        legacy_rel = lg.replace("audit.log", "audit.legacy.log")
        if legacy_rel in cap.files:   # 同一計畫內剛凍結的 legacy：以 overlay 內容驗證
            info = (mk.get("logs") or {}).get(lg)
            lb = cap.files[legacy_rel]
            if info and info.get("legacy") == "frozen" and store.sha256_bytes(lb) != info["sha256"]:
                raise Refused(f"render {lg}：凍結內容 hash 不符")
            body = render_log_bytes(lg, events, {**mk, "logs": {**mk.get("logs", {}), lg: {"legacy": "absent"}}}, cap.files)
            out[lg] = lb + body
        else:
            out[lg] = render_log_bytes(lg, events, mk, cap.files)
    return out

# ---------------------------------------------------------------- 執行（§7.8、§8）
def _write_step(plan: dict, step: dict):
    fault(f"before_output:{step['seq']}")
    tag = plan["op_id"][:16]
    if step["expected_after"] is None:
        _delete(step["path"])
    else:
        data = _load_blob(plan, step)
        if step["kind"] in ("event", "index", "status", "status_final"): _link_create(step["path"], data, tag)
        else: _atomic_replace(step["path"], data, tag, point=f"before_replace:{step['seq']}")
    fault(f"after_output:{step['seq']}")

def _load_blob(plan: dict, step: dict) -> bytes:
    p = store.ROOT / blob_path(plan["scope"], plan["op_id"], step["blob"])
    if not p.is_file(): raise EvidenceConflict(f"計畫的內容檔 {store.rel(p)} 不存在")
    data = p.read_bytes()
    if store.sha256_bytes(data) != step["expected_after"]: raise EvidenceConflict(f"計畫的內容檔 {store.rel(p)} 被竄改")
    return data

def execute(plan: dict):
    _clean_tmp(plan)
    final = plan["steps"][-1]
    if (store.ROOT / final["path"]).is_file():
        if _cur_sha(final["path"]) != final["expected_after"]: raise EvidenceConflict(f"{final['path']} 內容不符")
        return
    cls = classify_steps(plan)
    if cls.conflicts or cls.external:
        lines = [f"- {c.get('path')}：{c['reason']}" for c in cls.conflicts + cls.external]
        raise EvidenceConflict(f"續做 {plan['op_id']} 停止（{'證據衝突' if cls.conflicts else '外部修改'}），沒有重寫任何檔案：\n" + "\n".join(lines))
    for s in plan["steps"][:-1]:
        st = cls.status[s["seq"]]
        if st == "done": continue
        if st == "not_executed": _write_step(plan, s)
        _link_create(progress_path(plan, s), progress_bytes(plan, s), tag=plan["op_id"][:16])
        fault(f"after_progress:{s['seq']}")
    fault("before_completed")
    _write_step(plan, final)

# ---------------------------------------------------------------- 主流程（§6）
def check_plan_structure(plan: dict):
    """每個 path 在一個計畫中最多一步（AC-07-19）；違反 → 計畫產生失敗，沒有任何寫入。"""
    paths = [s["path"] for s in plan.get("steps", [])]
    dup = sorted({x for x in paths if paths.count(x) > 1})
    if dup: raise OperationError(f"計畫中同一路徑出現兩次：{dup}")

def _save_plan(plan: dict, blobs: dict):
    check_plan_structure(plan)
    op = plan["op_id"]; d = store.ROOT / op_dir(plan["scope"], op)
    if os.path.lexists(d) or os.path.lexists(_claim_path(op)):     # 清理之後仍存在 → 不屬於 executor，不取得它的擁有權
        raise EvidenceConflict(f"{d.relative_to(store.ROOT)} 或其認領檔已存在，但沒有計畫，需人工處理")
    staging = f"{STAGING_DIR}/{op}.yaml"
    _claim_path(op).parent.mkdir(parents=True, exist_ok=True)
    os.close(os.open(_claim_path(op), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)); _fsync_dir(_claim_path(op).parent)
    fault("after_claim")
    _link_create(staging, _staging_manifest(plan, blobs), tag=op[:16], point="staging_manifest")   # 寫入清單：先於任何內容檔
    pause("after_staging")
    for i, (sha, data) in enumerate(blobs.items()):
        _link_create(blob_path(plan["scope"], plan["op_id"], sha), data, tag=plan["op_id"][:16], pause_point="blob_tmp_written")
        if i == 0: pause("after_first_blob")
    data = store.dump(plan)
    errs = _plan_errors(plan)
    if errs: raise OperationError("計畫不符 schema：" + "; ".join(errs[:3]))
    fault("before_plan_save")
    _atomic_replace(plan_path(plan["scope"], plan["op_id"]), data, tag=plan["op_id"][:16])
    fault("after_plan_save"); pause("after_plan_save")
    _delete(staging); fault("after_staging_removed")
    _delete(f"{STAGING_DIR}/{op}.claim")
    return data

def _takeover_target(op: str) -> str | None:
    """若 op 被一份未完成的 rollback 計畫接管，回傳該 R 的 op_id。"""
    for r, reg in registrations().items():
        if reg.get("action") == "migrate_rollback" and plan_state(r) == "in_progress":
            p = load_plan(r)
            if p and p.get("takeover_of") == op: return r
    return None

def _resume(plan: dict, *, request_hash: str | None):
    verify_registration(plan["op_id"])
    if request_hash is not None and request_hash != plan["request_hash"]:
        raise EvidenceConflict("V1：請求和計畫的 request_hash 不符")
    others = [o for o in incomplete_plans() if o not in (plan["op_id"], plan.get("takeover_of"))]
    if others: raise Refused(f"V3：存在其他未完成的計畫 {others}（不合法狀態），需人工處理")
    check_resume_state(plan)
    execute(plan)
    LAST_OUTCOME.update(kind="resumed", op_id=plan["op_id"])
    return plan.get("result")

def _write_diagnostics(cap: store.Capture):
    """驗證失敗：不建立計畫，只寫允許的診斷（task 欄位與一個事件檔）。"""
    eid = f"adhoc-{uuid.uuid4().hex}"
    for r, data in cap.files.items():
        if data is None: continue
        _atomic_replace(r, data, tag="diag")
    for i, e in enumerate(cap.events[:1]):
        ev = {"at": cap.clock, "actor": e["actor"], "action": e["action"], "detail": e["detail"] or "", "op_id": eid, "step": 0, "run_id": e["run_id"]}
        _link_create(_event_path(eid, e["run_id"], 0), store.dump(ev), tag="diag")

DIAG_TASK_FIELDS = {"gate_results", "status", "history", "started_at"}

def parse_ts(v) -> datetime.datetime:
    """RFC3339 時間 → UTC 的 aware datetime。缺時區或格式不合法 → ValueError（呼叫端據此拒絕）。"""
    if isinstance(v, datetime.datetime): d = v
    elif isinstance(v, str): d = datetime.datetime.fromisoformat(v.replace("Z", "+00:00") if v.endswith("Z") else v)
    else: raise ValueError(f"不是時間：{v!r}")
    if d.tzinfo is None: raise ValueError(f"時間缺少時區：{v!r}")
    return d.astimezone(datetime.timezone.utc)

def _same_ts(v, clock: str) -> bool:
    try: return parse_ts(v) == parse_ts(clock)
    except ValueError: return False

def _check_diagnostic(cap: store.Capture):
    """驗證失敗只允許兩種診斷（第 4 章 §13、附錄 A 4-16），超出 → 拒絕、不寫入：
    1. 一份 run.yaml：run 本身只有 updated_at 可以變，而且只能是本次 executor 的時間；只有一個 task 變更，
       它的 gate_results 只追加一筆 structural FAIL、history 只追加、狀態依狀態機合法轉換且最後回到 READY、
       started_at 只能設為本次時間（task 重新進入 RUNNING 時）；
    2. 最多一個 audit 事件。"""
    from . import state
    files = dict(cap.files)
    runs = [r for r in files if r.startswith("runs/") and r.endswith("/run.yaml")]
    def bad(msg): raise OperationError(f"驗證失敗的診斷超出允許範圍：{msg}")
    if len(files) != len(runs) or len(runs) > 1 or len(cap.events) > 1 or any(files[r] is None for r in runs):
        bad(f"{sorted(files)}，事件 {len(cap.events)} 筆")
    for r in runs:
        before = yaml.safe_load((store.ROOT / r).read_text(encoding="utf-8")); after = yaml.safe_load(files[r].decode("utf-8"))
        if before.get("updated_at") != after.get("updated_at") and not _same_ts(after.get("updated_at"), cap.clock):
            bad(f"{r} 的 updated_at 只能是本次時間")
        strip = lambda run: {**{k: v for k, v in run.items() if k != "updated_at"}, "tasks": [{k: v for k, v in t.items() if k not in DIAG_TASK_FIELDS} for t in run.get("tasks", [])]}
        if strip(before) != strip(after): bad(f"改動了 {r} 中不允許的欄位")
        changed = [(tb, ta) for tb, ta in zip(before["tasks"], after["tasks"]) if tb != ta]
        if len(changed) > 1: bad(f"只能改動一個 task（{r}）")
        for tb, ta in changed:
            gb, ga = tb.get("gate_results") or [], ta.get("gate_results") or []
            new = ga[len(gb):]
            if ga[:len(gb)] != gb or len(new) != 1: bad("gate_results 只能追加一筆")
            if new[0].get("result") != "FAIL" or new[0].get("layer") != "structural" or not _same_ts(new[0].get("at"), cap.clock):
                bad("追加的 gate_results 必須是本次的 structural FAIL")
            hb, ha = tb.get("history") or [], ta.get("history") or []
            if ha[:len(hb)] != hb: bad("history 只能追加")
            cur = tb.get("status")
            for h in ha[len(hb):]:
                if h.get("from_status") != cur or not _same_ts(h.get("at"), cap.clock): bad("history 追加的轉換不連續或時間不符")
                try: state.check("task", cur, h["to_status"], h.get("by", ""))
                except Exception as e: bad(f"task 狀態轉換不合法：{e}")
                cur = h["to_status"]
            if cur != ta.get("status") or ta.get("status") != "READY": bad(f"task 最後狀態必須是 READY（實際 {ta.get('status')}）")
            if tb.get("started_at") != ta.get("started_at") and not _same_ts(ta.get("started_at"), cap.clock):
                bad("started_at 只能設為本次時間（task 重新進入 RUNNING）")

def run_operation(action: str, fn, *, request=None, scope: str = GLOBAL, new_request: bool = False, resume_op: str | None = None):
    """寫入操作的唯一入口。request：可呼叫物件，在取得鎖之後計算 CanonicalRequest（不含 new_request_token）。"""
    LAST_OUTCOME.clear()
    ctx = acquire()
    pause("after_lock")
    try:
        check_terminal_consistency()                         # 第 0 步
        cleanup_unplanned()                                  # 計畫保存前中止的殘留（不屬於任何計畫）
        reconcile_registrations()                            # 登錄補齊
        if resume_op is not None:                            # operation resume <op>
            ctx.op_id = resume_op; _write_owner(ctx)
            plan = load_plan(resume_op)
            if plan is None or resume_op not in registrations(): raise Refused(f"op {resume_op} 不存在")
            return _existing(plan, request_hash=None)
        req = {"request_schema": 1, "action": action, **(request() if request else {})}
        if new_request: req["new_request_token"] = uuid.uuid4().hex
        op = op_id_of(req); ctx.op_id = op; _write_owner(ctx)
        plan = load_plan(op)
        if plan is not None: return _existing(plan, request_hash=op)          # 第 2 步
        if incomplete_plans():                                                 # 3b
            raise Refused(f"存在未完成的計畫 {incomplete_plans()}；請先 `operation resume <op_id>`")
        state = system_state(); admit(action, state)                           # 3c
        clock = store.real_now(); today = store.real_today()
        cap = store.begin_capture(clock, today, op, owner_token=ctx.token)
        try: result = fn()
        finally: store.end_capture()
        if cap.diagnostic:
            _check_diagnostic(cap)
            _write_diagnostics(cap); LAST_OUTCOME.update(kind="diagnostic", op_id=None); return result
        plan, blobs = build_plan(cap, op_id=op, request=req, action=action, scope=scope, state=state, result=result)
        data = _save_plan(plan, blobs)
        _register(plan, data); fault("after_register")
        execute(plan)
        LAST_OUTCOME.update(kind="new", op_id=op)
        return result
    finally:
        if current() is ctx: release(ctx)

def _existing(plan: dict, *, request_hash: str | None):
    op = plan["op_id"]
    st = plan_state(op)
    if st == "completed":
        verify_registration(op)
        LAST_OUTCOME.update(kind="completed", op_id=op); return plan.get("result")
    if st in TERMINAL: raise Refused(f"op {op} 已終結（{st}）；要重做請以 --new-request 建立新 op")
    r = _takeover_target(op)
    if r: raise Refused(f"op {op} 已被 rollback 計畫 {r} 接管；請續做 {r}")
    return _resume(plan, request_hash=request_hash)

def in_operation() -> bool:
    return store.capturing() is not None

def operation(action: str, request=None, scope=None):
    """把寫入函式包成操作。巢狀呼叫（已在擷取中）直接執行，不另外取鎖。
    request(*args, **kwargs) → dict：CanonicalRequest 的 targets／params／inputs（在取得鎖之後計算）。"""
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*args, new_request: bool = False, **kwargs):
            if in_operation(): return fn(*args, **kwargs)
            req = (lambda: request(*args, **kwargs)) if request else (lambda: {"params": normalize({"args": list(args), "kwargs": kwargs})})
            sc = scope(*args, **kwargs) if scope else GLOBAL
            return run_operation(action, lambda: fn(*args, **kwargs), request=req, scope=sc or GLOBAL, new_request=new_request)
        wrapper.__wrapped_operation__ = action
        return wrapper
    return deco

def resume(op_id: str):
    return run_operation("operation_resume", None, resume_op=op_id)

# ---------------------------------------------------------------- 唯讀查詢
def list_operations(incomplete_only: bool = False) -> list[dict]:
    out = []
    regs = registrations()
    for op, reg in sorted(regs.items(), key=lambda kv: kv[1]["plan_seq"]):
        verify_registration(op, reg)
        st = plan_state(op)
        if incomplete_only and st != "in_progress": continue
        out.append({"plan_seq": reg["plan_seq"], "op_id": op, "action": reg["action"], "state": st, "registered_at": reg["registered_at"]})
    for op in plan_files():
        if op not in regs: out.append({"plan_seq": None, "op_id": op, "action": (load_plan(op) or {}).get("action"), "state": "unregistered"})
    return out

# ---------------------------------------------------------------- 控制類操作（§5.2）與移轉（P1：空 root 也需要的部分）
def _maint_start():
    store.save(MAINT_PATH, {"op_id": store.capturing().op_id, "started_at": store.now()})
    store.audit(None, "system", "MAINTENANCE_START", "")
    return {"state": "S_maint"}

def _maint_end():
    store.delete(MAINT_PATH)
    store.audit(None, "system", "MAINTENANCE_END", "")
    return {"state": "S_post" if (store.ROOT / MARKER_PATH).is_file() else "S_pre"}

def maintenance_start(by: str, new_request: bool = False):
    return run_operation("maintenance_start", _maint_start, request=lambda: {"params": {"by": by}}, new_request=new_request)

def maintenance_end(by: str, new_request: bool = False):
    return run_operation("maintenance_end", _maint_end, request=lambda: {"params": {"by": by}}, new_request=new_request)

def _migrate(by: str, acknowledge_idle: list[str]):
    """P1：凍結 legacy audit、寫移轉標記、第一次 render。資料轉換（R000、sidecar、CLR rev 0 等）與 rollback 在 P3。"""
    running = []
    for p in store.glob("runs/*/run.yaml"):
        r = store.load(p)
        if r.get("status") == "RUNNING": running.append(r["run_id"])
    missing = [r for r in running if r not in acknowledge_idle]
    if missing:
        raise Refused(f"RUNNING 的 run 必須逐一指定處理方式：{missing}（--acknowledge-idle <run_id>；--cancel-run 在 P3 提供）")
    logs, runs = {}, sorted(p.parent.name for p in store.glob("runs/*/run.yaml"))
    for lg in sorted({store.rel(p) for p in store.glob("runs/*/audit.log")} | ({"runs/_audit.log"} if store.exists("runs/_audit.log") else set())):
        legacy = lg.replace("audit.log", "audit.legacy.log")
        if store.exists(legacy): raise Refused(f"{legacy} 已存在，移轉拒絕")
        data = store.read_bytes(lg)
        store.write_bytes(legacy, data)
        logs[lg] = {"legacy": "frozen", "sha256": store.sha256_bytes(data)}
    if "runs/_audit.log" not in logs: logs["runs/_audit.log"] = {"legacy": "absent"}
    for r in runs:
        if f"runs/{r}/audit.log" not in logs: logs[f"runs/{r}/audit.log"] = {"legacy": "absent"}
    store.save(MARKER_PATH, {"migrate_op_id": store.capturing().op_id, "migrated_at": store.now(), "migrated_by": by,
                             "mode_per_run": {r: "acknowledge_idle" for r in acknowledge_idle}, "runs": runs, "logs": logs})
    store.audit(None, by, "MIGRATE", f"{len(logs)} logs; runs={len(runs)}")
    return {"logs": len(logs), "runs": len(runs)}

def migrate(by: str, acknowledge_idle: list[str] | None = None, new_request: bool = False):
    ack = sorted(acknowledge_idle or [])
    return run_operation("migrate", lambda: _migrate(by, ack), request=lambda: {"params": {"by": by, "acknowledge_idle": ack}}, new_request=new_request)

def _audit_render(target: str | None):
    mk = marker()
    if mk is None: raise Refused("尚未移轉（沒有移轉標記），不能 render")
    if target not in (None, "--global") and not store.exists(f"runs/{target}/run.yaml"): raise Refused(f"run {target} 不存在")
    logs = ["runs/_audit.log"] if target in (None, "--global") else [f"runs/{target}/audit.log"]
    cap = store.capturing()
    for lg, data in render_logs(cap, [], logs).items():
        store.write_derived(lg, data.decode("utf-8"))
    return {"rendered": logs}

def audit_render(target: str | None = None, new_request: bool = False):
    return run_operation("audit_render", lambda: _audit_render(target), request=lambda: {"params": {"target": target or "--global"}}, new_request=new_request)
