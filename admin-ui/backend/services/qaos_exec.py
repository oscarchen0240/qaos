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

import hashlib
import json
import os
import shlex
import sqlite3
import subprocess
import threading

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
    if mine != cur:
        return False
    # --spec-version 只在有帶時才更新 CLR 的 resulting_spec_version（CLI：`if resulting_spec_version: …`）。
    # 草稿明確指定了與目前不同的落地版本，就是有實際效果的更正，不算重複；沒指定則不更新，不影響判斷。
    wanted = str(ex.get("spec_version") or "").strip()
    return not wanted or wanted == str(d.get("resulting_spec_version") or "").strip()


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


def _text(v) -> str:
    """TimeoutExpired 的 output／stderr 在 POSIX 上可能是 bytes（即使 text=True），也可能是 None。"""
    if v is None:
        return ""
    return v.decode("utf-8", "replace") if isinstance(v, bytes) else v


def _run(cmd: str) -> dict:
    args = shlex.split(cmd)
    if not args or args[0] != "bin/qaos":
        raise ExecError(400, "只允許執行 bin/qaos")
    _write_guard()
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": os.environ.get("HOME", ""), "LANG": "en_US.UTF-8", "LC_ALL": "en_US.UTF-8", "PYTHONIOENCODING": "utf-8"}
    try:
        r = subprocess.run(args, cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=TIMEOUT, env=env)
        return {"command": cmd, "exit_code": r.returncode, "stdout": r.stdout[-4000:], "stderr": r.stderr[-4000:]}
    except subprocess.TimeoutExpired as e:
        # 逾時前 CLI 可能已經印出部分輸出、甚至已寫入部分狀態：保留已取得的輸出，並標明結果不確定（R10）
        return {"command": cmd, "exit_code": -1, "stdout": _text(e.output)[-4000:], "stderr": (_text(e.stderr)[-3900:] + f"\n逾時 {TIMEOUT}s").strip(), "timed_out": True}


RECONCILE = "bin/qaos operation list --incomplete"


def failure_hint(res: dict) -> str:
    """執行失敗時的提示。不再宣稱「QAOS 沒有改任何狀態」：逾時（或被訊號中斷）時 CLI 可能已寫入一部分，一般失敗這裡也無從確認。"""
    if res.get("timed_out") or res.get("exit_code", 0) < 0:
        return f"結果不確定：指令逾時或被中斷，QAOS 可能已完成部分或全部動作。請先對帳（{RECONCILE}），確認後再決定要不要重試；已取得的輸出見 stdout／stderr。"
    return f"執行失敗（exit {res.get('exit_code')}），看 stderr。這裡無法確認 QAOS 有沒有留下部分變更；有疑慮請先對帳（{RECONCILE}）。"


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


def _repair_torn_tail():
    """handoff.jsonl 是 append-only 的逐行 JSON。上一次寫到一半失敗會留下沒有換行的殘行（可能還切在多位元組字元中間，是非法 UTF-8）：
    之後任何 append 都會接在殘行後面、整行讀不出來，嚴格解碼的 reader（relay hook）還會整檔失敗。
    殘行本身若是完整的 JSON 物件，只補換行；否則把殘行搬到旁邊的 .torn 檔留存（不丟資料），主檔截回最後一個換行，讓主檔永遠是完整的行。"""
    if not HANDOFF_FILE.exists():
        return
    with open(HANDOFF_FILE, "r+b") as f:
        size = f.seek(0, os.SEEK_END)
        if size == 0:
            return
        f.seek(size - 1)
        if f.read(1) == b"\n":
            return
        pos, chunk = size, b""
        while pos > 0:                                   # 往回找最後一個換行
            step = min(65536, pos)
            pos -= step
            f.seek(pos)
            chunk = f.read(step) + chunk
            if b"\n" in chunk:
                break
        cut = pos + chunk.rfind(b"\n") + 1 if b"\n" in chunk else 0
        f.seek(cut)
        frag = f.read()
        try:
            ok = isinstance(json.loads(frag.decode("utf-8")), dict)
        except (UnicodeDecodeError, ValueError):
            ok = False
        if ok:
            f.seek(0, os.SEEK_END)
            f.write(b"\n")
            return
        with open(str(HANDOFF_FILE) + ".torn", "ab") as t:
            t.write(frag + b"\n")
        if os.fstat(f.fileno()).st_size == size:         # 期間沒有別人又寫入才截；否則留著殘行，由下面的 append 補換行
            f.truncate(cut)
        else:
            f.seek(0, os.SEEK_END)
            f.write(b"\n")


def _append_handoff(rec: dict):
    WARROOM_DIR.mkdir(parents=True, exist_ok=True)
    _repair_torn_tail()
    with open(HANDOFF_FILE, "ab") as f:
        f.write((json.dumps(rec, ensure_ascii=False) + "\n").encode("utf-8"))


def _handoff_records() -> list[dict]:
    """逐行（位元組）解碼並解析，壞行（非法 UTF-8、殘缺 JSON）略過，不讓一行壞資料拖垮整份。"""
    if not HANDOFF_FILE.exists():
        return []
    out = []
    for raw in HANDOFF_FILE.read_bytes().split(b"\n"):
        if not raw.strip():
            continue
        try:
            r = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            continue
        if isinstance(r, dict):
            out.append(r)
    return out


def handoff_tail(n: int = 50) -> list[dict]:
    out = _handoff_records()[-n * 3:]
    consumed = {r.get("handoff_id") for r in out if r.get("kind") == "consumed"}
    items = [r for r in out if r.get("kind") == "handoff"]
    for r in items:
        r["consumed"] = r["id"] in consumed
    return items[-n:]


def stable_handoff_id(*parts: str) -> str:
    """交接 ID 由內容衍生（不是隨機）：同一件事重複補做得到同一個 ID，handoff.jsonl 裡就只會有一筆。"""
    return hashlib.sha1("\x1f".join(parts).encode("utf-8")).hexdigest()[:12]


def handoff_recorded(handoff_id: str) -> bool:
    return any(r.get("kind") == "handoff" and r.get("id") == handoff_id for r in _handoff_records())


def append_handoff_once(rec: dict):
    """冪等：同一個 ID 已經在 handoff.jsonl 裡就不再寫。補做交接時前一次可能其實已寫成功、只是後面的步驟失敗。"""
    if not handoff_recorded(rec["id"]):
        _append_handoff(rec)
        if not handoff_recorded(rec["id"]):      # 寫完要讀得回來才算數；否則後面會把交接標成完成、卻沒有任何有效紀錄
            raise OSError(f"handoff {rec['id']} 寫入後讀不回來（{HANDOFF_FILE}）")


def _unfinished_execution(ticket_id: str) -> dict | None:
    """這張單最近一筆還沒收尾的執行紀錄：started（CLI 執行前先落的，結果未記錄）或 pending（CLI 已成功、後段未完成）。"""
    with db.connect() as con:
        return db.one(con.execute("SELECT * FROM ticket_executions WHERE ticket_id=? AND completion IN ('started','pending') ORDER BY id DESC LIMIT 1", (ticket_id,)))


def _post_steps(raw: str | None) -> list[dict]:
    try:
        v = json.loads(raw or "[]")
        return v if isinstance(v, list) else []
    except ValueError:
        return []


# CLI 已成功、但把結果寫進 ticket_executions 失敗時，這個 process 還握有的結果（row id → 內容）。
# 只在同一個 process 內有效；重啟後留下的 started 紀錄代表「結果未記錄」，會被標成不確定，要對帳。
_unsaved: dict[int, dict] = {}


def _start_execution(ticket_id: str, kind: str, action: str, command: str, run_id: str | None, started: str) -> int:
    """CLI 執行『前』先落一筆 started：之後不論在哪一步失敗，歷史裡都有這次嘗試的識別（row id），handoff ID 也由它衍生。"""
    with db.connect() as con:
        return con.execute("""INSERT INTO ticket_executions (ticket_id, kind, action, command, exit_code, post_json, run_id, started_at, ended_at, completion)
                              VALUES (?,?,?,?,NULL,'[]',?,?,?, 'started')""", (ticket_id, kind, action, command, run_id, started, started)).lastrowid


def _record_outcome(row_id: int, res: dict, post: list[dict], ended: str, completion: str, hint: str = "", handoff_id: str | None = None):
    with db.connect() as con:
        con.execute("UPDATE ticket_executions SET exit_code=?, stdout=?, stderr=?, post_json=?, ended_at=?, completion=?, hint=?, handoff_id=? WHERE id=?",
                    (res["exit_code"], res["stdout"], res["stderr"], json.dumps(post, ensure_ascii=False), ended, completion, hint, handoff_id, row_id))


def _abandon(row: dict):
    """上一次嘗試沒有留下結果（process 在 CLI 前後中斷）：標成不確定，之後照一般預檢走；預檢會擋掉狀態已經改變的單據。"""
    hint = f"這次嘗試沒有記錄到結果，QAOS 可能已完成部分或全部動作。請先對帳（{RECONCILE}）。"
    with db.connect() as con:
        con.execute("UPDATE ticket_executions SET completion='abandoned', hint=? WHERE id=?", (hint, row["id"]))


def execute(ticket_id: str) -> dict:
    if not _lock.acquire(blocking=False):
        raise ExecError(409, "另一條 bin/qaos 正在執行，稍後再試")
    with tk.draft_lock:
        tk.INFLIGHT.add(ticket_id)       # 執行期間不能改這張單的草稿，收尾的 mark_sent 才不會標到後來的新決定
    try:
        # 草稿、預檢、組指令與執行都在同一把鎖內：兩個請求交錯時，後取得鎖的一定讀到前一個請求寫入後的最新狀態，
        # 重複的回答（--new-request 擋不住的合法自轉換）才擋得住；預檢放在鎖外會讓兩個請求都通過舊狀態的預檢。
        # R04：上一次 CLI 已成功、但後段（交接、mark_sent、執行紀錄）沒做完時，只補做後段；不預檢（QAOS 狀態已經變了，預檢必然不符）也不重跑指令。
        last = _unfinished_execution(ticket_id)
        if last:
            ctx = _unsaved.get(last["id"])
            if last["completion"] == "started" and ctx:
                # 這個 process 知道上次 CLI 成功，只是結果沒寫進去：補寫結果
                _record_outcome(last["id"], ctx["res"], ctx["post"], ctx["ended"], "pending", "", ctx["handoff_id"])
                _unsaved.pop(last["id"], None)
                last = _unfinished_execution(ticket_id)
            if last and last["completion"] == "pending":
                res = {"command": last["command"], "exit_code": 0, "stdout": last["stdout"], "stderr": last["stderr"]}
                return _finish_success(last["id"], ticket_id, last["kind"], last["action"], last["command"], last["run_id"], res,
                                       _post_steps(last["post_json"]), last["started_at"], last["ended_at"], last["handoff_id"], resumed=True)
            if last:
                _abandon(last)
        draft = tk.get_draft(ticket_id)
        if not draft:
            raise ExecError(409, "還沒有草稿；先在畫面上做決定")
        kind = draft["kind"]
        cmd_out, action, run_id = _preflight(ticket_id, kind, draft)
        if cmd_out.get("warnings"):
            raise ExecError(409, "指令尚未完整：" + "；".join(cmd_out["warnings"]))
        started = db.now()
        row_id = _start_execution(ticket_id, kind, action, cmd_out["command"], run_id, started)
        res = _run(cmd_out["command"])
        ended = db.now()
        if res["exit_code"] != 0:
            hint = failure_hint(res)
            _record_outcome(row_id, res, [], ended, "done", hint)
            return {"ok": False, **res, "post": [], "run_id": run_id, "run_status_after": None, "next_task": None, "session_id": None, "handoff_id": None,
                    "hint": hint, "started_at": started, "ended_at": ended}
        # CLI 已改了 QAOS：馬上把成功結果記下來（含由本次嘗試衍生的 handoff ID），index 重建、交接等後段才開始；
        # 之後任何一步失敗都只補後段
        hid = stable_handoff_id("ticket", ticket_id, str(row_id))
        try:
            _record_outcome(row_id, res, [], ended, "pending", "", hid)
        except (OSError, sqlite3.Error) as e:
            _unsaved[row_id] = {"res": res, "post": [], "ended": ended, "handoff_id": hid, "ticket_id": ticket_id}
            raise ExecError(500, f"指令已成功執行（QAOS 已改變），但執行紀錄寫入失敗：{e}。再按一次「執行」會補寫紀錄並完成交接，不會重跑指令。") from e
        return _finish_success(row_id, ticket_id, kind, action, cmd_out["command"], run_id, res, [], started, ended, hid, resumed=False)
    finally:
        with tk.draft_lock:
            # 同 process 已知 CLI 成功、但結果還沒寫進 DB（_unsaved）時，草稿要繼續鎖著直到補做完成，否則補做會標到後來的新決定
            if not any(c["ticket_id"] == ticket_id for c in _unsaved.values()):
                tk.INFLIGHT.discard(ticket_id)
        _lock.release()


def _finish_success(row_id: int, ticket_id: str, kind: str, action: str, command: str, run_id: str | None, res: dict, post: list[dict],
                    started: str, ended: str, handoff_id: str, resumed: bool) -> dict:
    """CLI 成功之後的後段：讀 run 現況、組提示、寫交接（冪等）、mark_sent、把執行紀錄改成 done。任何一步失敗都保留 pending，可重試補做。"""
    if not post and kind in ("clarification", "bug"):
        # 順帶重建 index（帶 --new-request，可重跑）。放在「成功結果已落地」之後：這一步拋例外或逾時也不會丟掉已成功的結果，重試會再做一次
        post = [_run("bin/qaos clarification index --new-request" if kind == "clarification" else "bin/qaos bug index --new-request")]
        try:
            with db.connect() as con:
                con.execute("UPDATE ticket_executions SET post_json=? WHERE id=?", (json.dumps(post, ensure_ascii=False), row_id))
        except sqlite3.Error:
            pass                         # post 只是歷史明細；最後的 done 更新會再寫一次
    try:
        if run_id:
            run_svc._cache.pop(str(run_svc.RUNS_DIR / run_id / "run.yaml"), None)  # 強制重讀
        run_after = run_svc.get(run_id) if run_id else None
        next_task = None
        cur = None
        hint = ""
        session_id = None
        if kind == "approval" and run_after:
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
        # 交接分類：run 還有 READY 的 agent task 要接 → resume_agent（relay 會 block 讓 QA session 接續）；
        # 其他（run 結案／又在等人／釐清、Bug 動作）→ notify_only（relay 只在 UserPromptSubmit 顯示，不擋、不吞）
        resume = bool(kind == "approval" and run_after and run_after["status"] == "RUNNING" and cur and cur.get("status") == "READY")
        append_handoff_once({
            "kind": "handoff", "id": handoff_id, "ts": ended, "ticket_id": ticket_id, "ticket_kind": kind, "action": action,
            "handoff_kind": "resume_agent" if resume else "notify_only",
            "command": command, "exit_code": res["exit_code"], "run_id": run_id,
            "run_status_after": run_after["status"] if run_after else None, "next_task": next_task,
            "next_agent": (cur.get("agent_id") if (kind == "approval" and run_after and cur) else None),
            "session_id": session_id, "hint": hint, "by": tk.operator(),
        })
        tk.mark_sent(ticket_id, command)
        with db.connect() as con:
            con.execute("UPDATE ticket_executions SET post_json=?, run_status_after=?, next_task=?, session_id=?, hint=?, completion='done' WHERE id=?",
                        (json.dumps(post, ensure_ascii=False), run_after["status"] if run_after else None, next_task, session_id, hint, row_id))
    except (OSError, sqlite3.Error) as e:
        raise ExecError(500, f"指令已成功執行（QAOS 已改變），但交接或執行紀錄寫入失敗：{e}。再按一次「執行」只會補做交接與紀錄，不會重跑指令。") from e
    return {"ok": True, **res, "post": post, "run_id": run_id, "run_status_after": run_after["status"] if run_after else None,
            "next_task": next_task, "session_id": session_id, "handoff_id": handoff_id, "hint": hint, "started_at": started, "ended_at": ended,
            "completed_pending": resumed}


def executions(ticket_id: str) -> list[dict]:
    with db.connect() as con:
        rows = db.rows(con.execute("SELECT * FROM ticket_executions WHERE ticket_id=? ORDER BY id DESC LIMIT 20", (ticket_id,)))
    for r in rows:
        raw = r.pop("post_json") or "[]"
        try:
            r["post"] = json.loads(raw)
        except ValueError:               # 舊版把序列化後的 JSON 直接切片存進來，可能已無法解析：照實標出，不讓整份歷史讀不出來
            r["post"] = []
            r["post_error"] = "這筆執行紀錄的步驟明細已損毀（舊版截斷），無法顯示"
        r["ok"] = r["exit_code"] == 0
        r["pending_completion"] = r.get("completion") == "pending"
    return rows
