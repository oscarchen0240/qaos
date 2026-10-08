"""M5b：平台代為執行 bin/qaos（核准／釐清／Bug 的人工決定）。

邊界（2026-09-18 Oscar 放寬邊界 1 後的約定）：
- 只跑 tickets.py 組出來的 `bin/qaos …` 指令，args[0] 必須是 bin/qaos；不接受任意指令。
- 同時間只跑一條（process 內鎖），逾時 60 秒；執行前再做一次狀態預檢，不符就拒絕、不重試。
- 執行後把交接紀錄 append 到 `.warroom/handoff.jsonl`（append-only），給 QA session 的 relay hook 與人看。
- 釐清／Bug 動作後順帶跑 `bin/qaos clarification index --new-request` / `bin/qaos bug index --new-request` 重建 index.md（也是 QAOS 自己的指令）。
  需求 A 後寫入指令以「請求內容」算 op_id，內容相同的重送會被當成先前已完成而不再寫入，所以重建 index 一定要帶 --new-request；
  `clarification list` 已改為唯讀，不會重建 index。
- 寫入的 QAOS 路徑清單見 README「單據 › M5b」。
"""
from __future__ import annotations

import json
import os
import shlex
import subprocess
import threading
import uuid

from .. import db
from ..config import PROJECT_ROOT, WARROOM_DIR
from . import runs as run_svc
from . import tickets as tk

HANDOFF_FILE = WARROOM_DIR / "handoff.jsonl"
TIMEOUT = 60
_lock = threading.Lock()


class ExecError(Exception):
    def __init__(self, status: int, msg: str):
        super().__init__(msg)
        self.status = status


# ---------- 預檢 ----------
def _preflight(ticket_id: str, kind: str, draft: dict) -> tuple[dict, str, str | None]:
    """回 (command_out, action, run_id)。任何不符都丟 ExecError(409)。"""
    if kind == "approval":
        d = tk.approval_detail(ticket_id)
        if not d:
            raise ExecError(404, "approval 不存在")
        if d["status"] != "PENDING":
            raise ExecError(409, f"{ticket_id} 已經是 {d['status']}，不能再核准")
        run = run_svc.get(d["run_id"]) if d.get("run_id") else None
        if run and run["status"] != "WAITING_HUMAN":
            raise ExecError(409, f"run {d['run_id']} 目前是 {run['status']}，不是 WAITING_HUMAN；為避免與 QA session 同時寫 run.yaml，先不執行")
        if run and run.get("waiting_on_approval_id") and run["waiting_on_approval_id"] != ticket_id:
            raise ExecError(409, f"run 正在等的是 {run['waiting_on_approval_id']}，不是 {ticket_id}")
        cmd = tk.approval_command(ticket_id, draft)
        return cmd, draft.get("decision") or "", d.get("run_id")
    if kind == "clarification":
        d = tk.clarification_detail(ticket_id)
        if not d:
            raise ExecError(404, "clarification 不存在")
        action = draft.get("decision") or "answer"
        target = {"ask": "ASKED", "answer": "ANSWERED", "apply": "APPLIED", "withdraw": "WITHDRAWN"}.get(action)
        if target not in (d.get("allowed") or []):
            raise ExecError(409, f"{ticket_id} 目前 {d['status']}，狀態機不允許 → {target}")
        if action == "answer" and _answer_already_registered(d, draft):
            raise ExecError(409, f"{ticket_id} 已經登記過這個回答（內容、回答者、落地方式都相同），不再追加重複的答案修訂；"
                                 "要追加新的修訂，請先修改回答內容或落地方式。")
        return tk.clarification_command(ticket_id, draft), action, d.get("run_id")
    if kind == "bug":
        d = tk.bug_detail(ticket_id)
        if not d:
            raise ExecError(404, "bug 不存在")
        action = draft.get("decision") or "transition"
        st = d["status"]
        need = {"resolve": ("OPEN", "IN_PROGRESS"), "verify": ("RESOLVED",), "close": ("VERIFIED",)}
        if action in need and st not in need[action]:
            raise ExecError(409, f"{ticket_id} 目前 {st}，{action} 需要 {'/'.join(need[action])}")
        if action == "transition":
            to = (draft.get("extra") or {}).get("to") or ""
            if to not in {a["to"] for a in d.get("allowed") or []}:
                raise ExecError(409, f"{ticket_id} 目前 {st}，狀態機不允許 → {to or '(空)'}")
        return tk.bug_command(ticket_id, draft), action, None
    raise ExecError(400, f"未知單據類型 {kind}")


def _answer_already_registered(d: dict, draft: dict) -> bool:
    """answer 有合法的自轉換（ANSWERED→ANSWERED 追加修訂、INCORPORATED→ANSWERED 要求重新納入），而且我們對釐清指令帶 --new-request，
    所以狀態機擋不住「同一份回答再送一次」（HTTP 重送、第一次回應遺失後重試、舊草稿再按一次）。
    以資料為準：目前登記的最新回答與這份草稿的內容、回答者、落地方式全都相同，就視為重複，不送。"""
    if d.get("status") not in ("ANSWERED", "INCORPORATED"):
        return False
    ex = draft.get("extra") or {}
    mine = ((draft.get("rationale") or "").strip(), ex.get("answered_by") or ex.get("asked_to") or "PM", ex.get("resolution") or "requirement_clarified")
    cur = ((d.get("answer") or "").strip(), d.get("answered_by"), d.get("resolution"))
    return mine == cur


# ---------- 執行 ----------
def _git_dirs(root) -> tuple[str, str] | None:
    """(這個 checkout 的 git dir, 共同 git dir) 的絕對路徑；不是 git 工作樹或 git 不能執行時回 None。"""
    try:
        r = subprocess.run(["git", "-C", str(root), "rev-parse", "--path-format=absolute", "--absolute-git-dir", "--git-common-dir"],
                           capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    lines = r.stdout.splitlines()
    return (lines[0], lines[1]) if r.returncode == 0 and len(lines) == 2 else None


def _write_guard() -> None:
    """bin/qaos 只能在 QAOS 專案根執行，而且不能是 linked worktree（寫入會落到副本，與主資料夾的 QAOS 資料分岔）。

    linked worktree 的判斷看 git 本身：它的 git dir（<共同目錄>/worktrees/<名稱>）不等於共同 git dir。
    只看 `.git` 是不是檔案不夠——`git init --separate-git-dir` 的主 checkout 與 submodule 的 `.git` 也是檔案。
    """
    if not (PROJECT_ROOT / "bin" / "qaos").is_file():
        raise ExecError(409, f"PROJECT_ROOT（{PROJECT_ROOT}）底下找不到 bin/qaos，不是 QAOS 專案根；請用 QAOS_ADMIN_PROJECT_ROOT 指向主資料夾。")
    dirs = _git_dirs(PROJECT_ROOT)
    if dirs is None:
        if (PROJECT_ROOT / ".git").exists():       # 看起來是 git checkout 卻查不出來：寧可擋下，不要猜
            raise ExecError(409, f"無法確認 PROJECT_ROOT（{PROJECT_ROOT}）是不是 git worktree（git 指令失敗），為避免寫入落到副本，已拒絕執行 bin/qaos。")
        return
    git_dir, common_dir = (os.path.realpath(d) for d in dirs)
    if git_dir != common_dir:
        raise ExecError(409, f"PROJECT_ROOT（{PROJECT_ROOT}）是 git worktree，不是主資料夾；為避免寫入落到副本，已拒絕執行 bin/qaos。"
                             "請用 QAOS_ADMIN_PROJECT_ROOT 指向主資料夾後重啟指揮台。")


def _run(cmd: str) -> dict:
    args = shlex.split(cmd)
    if not args or args[0] != "bin/qaos":
        raise ExecError(400, "只允許執行 bin/qaos")
    _write_guard()
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": os.environ.get("HOME", ""), "LANG": "en_US.UTF-8", "LC_ALL": "en_US.UTF-8", "PYTHONIOENCODING": "utf-8"}
    try:
        r = subprocess.run(args, cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=TIMEOUT, env=env)
        return {"command": cmd, "exit_code": r.returncode, "stdout": r.stdout[-4000:], "stderr": r.stderr[-4000:]}
    except subprocess.TimeoutExpired:
        return {"command": cmd, "exit_code": -1, "stdout": "", "stderr": f"逾時 {TIMEOUT}s"}


def _index_note(post: list[dict], index_path: str) -> str:
    """順帶重建 index 的結果要照實說：重建指令失敗時不能宣稱已重建。"""
    bad = [x for x in post if x["exit_code"] != 0]
    if not bad:
        return f"{index_path} 已重建。"
    return f"但 {index_path} 重建失敗（{(bad[0]['stderr'] or bad[0]['stdout'] or '無訊息').strip()[-200:]}），請在終端機執行 {bad[0]['command']}。"


def _owner_session(run_id: str | None) -> str | None:
    """這條 run 屬於哪個 QA session：pipeline 的 related_runs 含它、未忽略、最近活動者。"""
    if not run_id:
        return None
    try:
        from . import pipeline
        snap = pipeline.snapshot()
        cands = [v for v in snap["sessions"] if not v["ignored"] and any(r["run_id"] == run_id for r in v["related_runs"])]
        cands.sort(key=lambda v: (v["health"]["state"] in ("live", "stalled"), v["last_seen"]), reverse=True)
        return cands[0]["session_id"] if cands else None
    except Exception:  # noqa: BLE001
        return None


def _append_handoff(rec: dict):
    WARROOM_DIR.mkdir(parents=True, exist_ok=True)
    with open(HANDOFF_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def handoff_tail(n: int = 50) -> list[dict]:
    if not HANDOFF_FILE.exists():
        return []
    out = []
    for line in HANDOFF_FILE.read_text(encoding="utf-8").splitlines()[-n * 3:]:
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    consumed = {r.get("handoff_id") for r in out if r.get("kind") == "consumed"}
    items = [r for r in out if r.get("kind") == "handoff"]
    for r in items:
        r["consumed"] = r["id"] in consumed
    return items[-n:]


def execute(ticket_id: str) -> dict:
    draft = tk.get_draft(ticket_id)
    if not draft:
        raise ExecError(409, "還沒有草稿；先在畫面上做決定")
    kind = draft["kind"]
    cmd_out, action, run_id = _preflight(ticket_id, kind, draft)
    if cmd_out.get("warnings"):
        raise ExecError(409, "指令尚未完整：" + "；".join(cmd_out["warnings"]))
    if not _lock.acquire(blocking=False):
        raise ExecError(409, "另一條 bin/qaos 正在執行，稍後再試")
    started = db.now()
    try:
        res = _run(cmd_out["command"])
        post: list[dict] = []
        if res["exit_code"] == 0:
            if kind == "clarification":
                post.append(_run("bin/qaos clarification index --new-request"))
            elif kind == "bug":
                post.append(_run("bin/qaos bug index --new-request"))
    finally:
        _lock.release()
    ended = db.now()

    if run_id:
        run_svc._cache.pop(str(run_svc.RUNS_DIR / run_id / "run.yaml"), None)  # 強制重讀
    run_after = run_svc.get(run_id) if run_id else None
    next_task = None
    cur = None
    hint = ""
    session_id = None
    if res["exit_code"] != 0:
        hint = "執行失敗，QAOS 沒有改任何狀態；看 stderr。"
    elif kind == "approval" and run_after:
        cur = next((t for t in run_after["tasks"] if t["task_id"] == run_after.get("current_task_id")), None)
        next_task = run_after.get("current_task_id")
        session_id = _owner_session(run_id)
        st = run_after["status"]
        if st == "RUNNING" and cur and cur["status"] == "READY":
            hint = f"run {run_id} 已推進到 {next_task}（{cur.get('agent_id') or cur.get('type')}）。QA session 會在下一回合結束或你送出任何訊息時由 relay hook 接續；沒裝 relay 就到 QA session 說「繼續 {run_id}」。"
        elif st == "WAITING_HUMAN":
            hint = f"run {run_id} 又開了新的核准單（{run_after.get('waiting_on_approval_id')}），回單據頁處理。"
        elif st == "COMPLETED":
            hint = f"run {run_id} 已完成。若是啟用 TC，請到 QA session 跑 tc-export 重新匯出 final（產出頁會顯示「final 已過期」）。"
        elif st == "CANCELLED":
            hint = f"run {run_id} 已取消。"
        else:
            hint = f"run {run_id} 現在 {st}。"
    elif kind == "clarification":
        hint = "釐清單已更新，" + _index_note(post, "clarifications/index.md") + ("若已回答且有對應 RESOLVE_AMBIGUITY 核准單，回核准頁套用。" if action == "answer" else "")
    elif kind == "bug":
        hint = "Bug 已更新，" + _index_note(post, "bugs/index.md")

    handoff_id = None
    if res["exit_code"] == 0:
        handoff_id = uuid.uuid4().hex[:12]
        # 交接分類：run 還有 READY 的 agent task 要接 → resume_agent（relay 會 block 讓 QA session 接續）；
        # 其他（run 結案／又在等人／釐清、Bug 動作）→ notify_only（relay 只在 UserPromptSubmit 顯示，不擋、不吞）
        resume = bool(kind == "approval" and run_after and run_after["status"] == "RUNNING" and cur and cur.get("status") == "READY")
        _append_handoff({
            "kind": "handoff", "id": handoff_id, "ts": ended, "ticket_id": ticket_id, "ticket_kind": kind, "action": action,
            "handoff_kind": "resume_agent" if resume else "notify_only",
            "command": cmd_out["command"], "exit_code": res["exit_code"], "run_id": run_id,
            "run_status_after": run_after["status"] if run_after else None, "next_task": next_task,
            "next_agent": (cur.get("agent_id") if (kind == "approval" and run_after and cur) else None),
            "session_id": session_id, "hint": hint, "by": tk.operator(),
        })
        tk.mark_sent(ticket_id, cmd_out["command"])

    with db.connect() as con:
        con.execute("""INSERT INTO ticket_executions (ticket_id, kind, action, command, exit_code, stdout, stderr, post_json, run_id, run_status_after, next_task, session_id, handoff_id, hint, started_at, ended_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (ticket_id, kind, action, cmd_out["command"], res["exit_code"], res["stdout"], res["stderr"], json.dumps(post, ensure_ascii=False),
                     run_id, run_after["status"] if run_after else None, next_task, session_id, handoff_id, hint, started, ended))
    return {"ok": res["exit_code"] == 0, **res, "post": post, "run_id": run_id, "run_status_after": run_after["status"] if run_after else None,
            "next_task": next_task, "session_id": session_id, "handoff_id": handoff_id, "hint": hint, "started_at": started, "ended_at": ended}


def executions(ticket_id: str) -> list[dict]:
    with db.connect() as con:
        rows = db.rows(con.execute("SELECT * FROM ticket_executions WHERE ticket_id=? ORDER BY id DESC LIMIT 20", (ticket_id,)))
    for r in rows:
        r["post"] = json.loads(r.pop("post_json") or "[]")
        r["ok"] = r["exit_code"] == 0
    return rows
