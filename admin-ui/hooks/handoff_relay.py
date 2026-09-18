"""Claude Code hook（Stop / UserPromptSubmit）：把平台的交接紀錄接回 QA session。

讀 .warroom/handoff.jsonl（只有 admin-ui 後端會寫），找「給這個 session、尚未消費」的紀錄：
- Stop：若 run.yaml 確認該 run 仍 RUNNING 且 current task 為 READY（resume_agent），輸出 {"decision":"block","reason":...}
        讓 Claude 接續執行；只 append 這一筆 consumed(resumed)。其餘 pending 原封不動——run 已 COMPLETED／又在等人的
        notify_only 交接不可被 no-op 吞掉（PROMPT-test-automation-coverage-audit A6 #5）。stop_hook_active 為真時不擋（防迴圈）。
- UserPromptSubmit：把待處理的交接摘要印到 stdout（成為本回合上下文），不擋、不改指令；notify_only 顯示過即標 consumed(notified)。

保證：不打網路、只讀 handoff.jsonl / run.yaml、只 append handoff.jsonl；任何錯誤靜默 exit 0。
只認 session_id 相符的紀錄，所以開發 admin-ui 的 session 不會被影響。
"""
import json
import os
import sys
import time

MAX_LINES_SCAN = 500


def _read(path):
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()[-MAX_LINES_SCAN:]
    except OSError:
        return []
    out = []
    for ln in lines:
        try:
            out.append(json.loads(ln))
        except ValueError:
            continue
    return out


def _run_state(project, run_id):
    """不依賴 pyyaml：只抓 status / current_task_id 與該 task 的 status、agent_id（縮排式 yaml 逐行掃）。"""
    p = os.path.join(project, "runs", run_id, "run.yaml")
    try:
        with open(p, encoding="utf-8") as f:
            lines = f.read().splitlines()
    except OSError:
        return None
    status = cur = None
    for ln in lines:
        if ln.startswith("status:"):
            status = ln.split(":", 1)[1].strip().strip("'\"")
        elif ln.startswith("current_task_id:"):
            cur = ln.split(":", 1)[1].strip().strip("'\"")
    tstat = agent = None
    if cur:
        in_task = False
        for ln in lines:
            s = ln.strip()
            if s.startswith("- task_id:"):
                in_task = s.split(":", 1)[1].strip().strip("'\"") == cur
            elif in_task and s.startswith("status:"):
                tstat = s.split(":", 1)[1].strip().strip("'\"")
            elif in_task and s.startswith("agent_id:"):
                agent = s.split(":", 1)[1].strip().strip("'\"")
            elif in_task and s.startswith("- task_id:"):
                break
    return {"status": status, "current_task_id": cur, "task_status": tstat, "agent_id": agent}


def main():
    raw = sys.stdin.read()
    if not raw.strip():
        return
    p = json.loads(raw)
    ev = p.get("hook_event_name") or ""
    sid = p.get("session_id") or ""
    if ev not in ("Stop", "UserPromptSubmit") or not sid:
        return
    project = os.environ.get("CLAUDE_PROJECT_DIR") or p.get("cwd") or os.getcwd()
    hpath = os.path.join(project, ".warroom", "handoff.jsonl")
    recs = _read(hpath)
    consumed = {r.get("handoff_id") for r in recs if r.get("kind") == "consumed"}
    pending = [r for r in recs if r.get("kind") == "handoff" and r.get("session_id") == sid and r.get("id") not in consumed]
    if not pending:
        return

    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    def _resumable(r):
        """真的有 agent task 在等：run RUNNING 且 current task READY（以 run.yaml 當下狀態為準，不信 handoff 寫入時的快照）。"""
        st = _run_state(project, r.get("run_id") or "") if r.get("run_id") else None
        return (r, st) if (st and st["status"] == "RUNNING" and st["task_status"] == "READY") else None

    if ev == "UserPromptSubmit":
        # 顯示所有待接續；notify_only（沒有 task 要接）顯示過就算送達，標 notified；resume_agent 留給 Stop 去 block
        lines = ["[QAOS 指揮台交接] 以下單據已由平台執行，尚未由本 session 接續："]
        notified = []
        for r in pending[-5:]:
            lines.append(f"- {r.get('ts')} {r.get('ticket_id')} {r.get('action')} → run {r.get('run_id')} {r.get('run_status_after')}，current_task={r.get('next_task')}。{r.get('hint','')}")
        for r in pending:
            if _resumable(r) is None:
                notified.append(r["id"])
        if notified:
            with open(hpath, "a", encoding="utf-8") as f:
                for hid in notified:
                    f.write(json.dumps({"kind": "consumed", "handoff_id": hid, "ts": ts, "by": "relay", "note": "notified"}, ensure_ascii=False) + "\n")
        print("\n".join(lines))
        return

    # Stop：只接「run 真的在等 agent 動」的第一筆，也只 consume 這一筆；其餘 pending 原封不動（不可 no-op 吞單）
    if p.get("stop_hook_active"):
        return
    todo = next((x for x in (_resumable(r) for r in pending) if x), None)
    if not todo:
        return
    with open(hpath, "a", encoding="utf-8") as f:
        f.write(json.dumps({"kind": "consumed", "handoff_id": todo[0]["id"], "ts": ts, "by": "relay", "note": "resumed"}, ensure_ascii=False) + "\n")
    r, st = todo
    reason = (f"QAOS 指揮台已對 {r.get('ticket_id')} 執行「{r.get('action')}」（{r.get('by')}）。"
              f"run {r.get('run_id')} 現在 {st['status']}，current_task_id={st['current_task_id']}（{st.get('agent_id') or ''}，狀態 READY）。"
              f"請依 QAOS Runtime 既有流程接續執行這個 task；若你判斷不該由本 session 接手，說明原因後停止即可。")
    print(json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception:  # noqa: BLE001
        pass
    sys.exit(0)
