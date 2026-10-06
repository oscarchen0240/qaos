"""Executor：全域操作鎖（flock）、操作計畫、續做、audit 事件檔、維護模式與准入（最終規格第 4 章）。

一次寫入操作的流程（run_operation）：
  取得 flock → 第 0 步（全域終態一致性核對）→ 登錄補齊 → 第 1～3 步（目標計畫／續做驗證／新請求准入）
  → 以擷取（store overlay）執行業務邏輯 → 產生計畫（每個 path 一步、no_change、固定 clock 與事件 payload）
  → 原子保存計畫（即已建立）→ 登錄 → 依序執行步驟（輸出 → fsync → 完成紀錄）→ completed 狀態紀錄 → 釋放鎖。
"""
from __future__ import annotations
import os, json, uuid, errno, fcntl, socket, hashlib, functools, pathlib, datetime, yaml
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
        r = store.rel(v)
        return {"path": r, "sha256": store.sha256_file(r) if store.exists(r) else None}
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

def _atomic_replace(rel_path: str, data: bytes, tag: str):
    t = store.ROOT / rel_path; t.parent.mkdir(parents=True, exist_ok=True)
    tmp = _tmp_name(t, tag)
    with open(tmp, "wb") as f: f.write(data); f.flush(); os.fsync(f.fileno())
    os.replace(tmp, t); _fsync_dir(t.parent)

def _link_create(rel_path: str, data: bytes, tag: str) -> bool:
    """暫存檔 → fsync → link 到目標（已存在就失敗）→ 刪暫存檔。回傳 True 表示新建立；已存在且內容相同回傳 False。"""
    t = store.ROOT / rel_path; t.parent.mkdir(parents=True, exist_ok=True)
    tmp = _tmp_name(t, tag)
    with open(tmp, "wb") as f: f.write(data); f.flush(); os.fsync(f.fileno())
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
        rec = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        op = rec.get("op_id")
        if not op or not p.name.endswith(f"-{op}.yaml"):
            raise EvidenceConflict(f"登錄紀錄 {p.name} 內容和檔名不符")
        if op in out: raise EvidenceConflict(f"op {op} 有兩筆登錄紀錄")
        rec["_file"] = p.name; out[op] = rec
    return out

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
        plan = load_plan(op)
        if not plan: continue
        group = [s["path"] for s in plan.get("steps", []) if s.get("group") == "terminal"]
        present = [(store.ROOT / p).is_file() for p in group]
        seen_missing = False
        for path, ok in zip(group, present):
            if not ok: seen_missing = True
            elif seen_missing:
                raise Refused(f"終態不一致：rollback 計畫 {op} 的 {path} 存在，但排在它前面的終態步驟不存在；需人工處理")

# ---------------------------------------------------------------- 登錄補齊（§6.2）
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

def render_log_bytes(log_rel: str, extra_events: list[dict], mk: dict) -> bytes:
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
    if info and info.get("legacy") == "frozen":
        legacy_rel = log_rel.replace("audit.log", "audit.legacy.log")
        lb = _disk_bytes(legacy_rel)
        if lb is None or store.sha256_bytes(lb) != info["sha256"]:
            raise Refused(f"render {log_rel}：legacy 檔 {legacy_rel} 不存在或 hash 不符")
        head = lb
    elif info is None and not global_log:
        run_id = log_rel.split("/")[1]
        if run_id in (mk.get("runs") or []):
            raise Refused(f"render {log_rel}：移轉標記中應有它的 legacy 狀態，但缺少")
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
            body = render_log_bytes(lg, events, {**mk, "logs": {**mk.get("logs", {}), lg: {"legacy": "absent"}}})
            out[lg] = lb + body
        else:
            out[lg] = render_log_bytes(lg, events, mk)
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
        else: _atomic_replace(step["path"], data, tag)
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
def _save_plan(plan: dict, blobs: dict):
    for sha, data in blobs.items():
        _link_create(blob_path(plan["scope"], plan["op_id"], sha), data, tag=plan["op_id"][:16])
    data = store.dump(plan)
    errs = _plan_errors(plan)
    if errs: raise OperationError("計畫不符 schema：" + "; ".join(errs[:3]))
    fault("before_plan_save")
    _atomic_replace(plan_path(plan["scope"], plan["op_id"]), data, tag=plan["op_id"][:16])
    fault("after_plan_save")
    return data

def _takeover_target(op: str) -> str | None:
    """若 op 被一份未完成的 rollback 計畫接管，回傳該 R 的 op_id。"""
    for r, reg in registrations().items():
        if reg.get("action") == "migrate_rollback" and plan_state(r) == "in_progress":
            p = load_plan(r)
            if p and p.get("takeover_of") == op: return r
    return None

def _resume(plan: dict, *, request_hash: str | None):
    regs = registrations()
    reg = regs.get(plan["op_id"])
    data = (store.ROOT / plan_path(plan["scope"], plan["op_id"])).read_bytes()
    if reg is None or reg["plan_sha256"] != store.sha256_bytes(data):
        raise EvidenceConflict(f"V1：{plan['op_id']} 的計畫檔和登錄紀錄不符")
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

def _diagnostic_allowed(cap: store.Capture) -> bool:
    return all(data is not None and (r.startswith("runs/") and r.endswith("/run.yaml") or r.startswith("artifacts/")) for r, data in cap.files.items()) and len(cap.events) <= 1

def run_operation(action: str, fn, *, request=None, scope: str = GLOBAL, new_request: bool = False, resume_op: str | None = None):
    """寫入操作的唯一入口。request：可呼叫物件，在取得鎖之後計算 CanonicalRequest（不含 new_request_token）。"""
    LAST_OUTCOME.clear()
    ctx = acquire()
    try:
        check_terminal_consistency()                         # 第 0 步
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
        cap = store.begin_capture(clock, today, op)
        try: result = fn()
        finally: store.end_capture()
        if cap.diagnostic and _diagnostic_allowed(cap):
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
    logs = ["runs/_audit.log"] if target in (None, "--global") else [f"runs/{target}/audit.log"]
    cap = store.capturing()
    for lg, data in render_logs(cap, [], logs).items():
        store.write_derived(lg, data.decode("utf-8"))
    return {"rendered": logs}

def audit_render(target: str | None = None, new_request: bool = False):
    return run_operation("audit_render", lambda: _audit_render(target), request=lambda: {"params": {"target": target or "--global"}}, new_request=new_request)
