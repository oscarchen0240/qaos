"""Claude Code hook：從 stdin 讀 hook JSON，只留必要欄位，append 一行到 .warroom/events.jsonl。

保證：不打網路、不輸出 stdout、任何錯誤都吞掉並以 exit 0 結束（由 log_event.sh 再保險一次）。
"""
import json
import os
import sys
import time

MAX_BYTES = 5 * 1024 * 1024   # 超過就輪替
KEEP_ROTATED = 3
FINAL_PREFIX = "testcases/final/"


def main() -> None:
    raw = sys.stdin.read()
    if not raw.strip():
        return
    p = json.loads(raw)
    ev = p.get("hook_event_name") or ""
    tool_input = p.get("tool_input") or {}
    file_path = tool_input.get("file_path") or ""

    if ev == "PostToolUse":
        # 只記錄寫進 testcases/final/ 的 Write / Edit
        norm = file_path.replace("\\", "/")
        if FINAL_PREFIX not in norm and not norm.startswith(FINAL_PREFIX):
            return
        idx = norm.find(FINAL_PREFIX)
        file_path = norm[idx:] if idx >= 0 else norm

    rec = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "session_id": p.get("session_id") or "",
        "event": ev,
        "agent_id": p.get("agent_id") or "",
        "agent_type": p.get("agent_type") or "",
        "subagent_name": p.get("subagent_name") or "",
        "tool_name": p.get("tool_name") or "",
        "file_path": file_path,
        "reason": p.get("reason") or p.get("source") or "",
        "cwd": p.get("cwd") or "",
        "transcript_path": p.get("transcript_path") or "",
        "tag": os.environ.get("QAOS_TRACK", ""),
    }

    project = os.environ.get("CLAUDE_PROJECT_DIR") or rec["cwd"] or os.getcwd()
    warroom = os.path.join(project, ".warroom")
    os.makedirs(warroom, exist_ok=True)
    path = os.path.join(warroom, "events.jsonl")

    try:
        if os.path.getsize(path) > MAX_BYTES:
            for i in range(KEEP_ROTATED, 0, -1):
                src = path if i == 1 else f"{path[:-6]}.{i - 1}.jsonl"
                dst = f"{path[:-6]}.{i}.jsonl"
                if os.path.exists(src):
                    os.replace(src, dst)
    except OSError:
        pass

    line = json.dumps(rec, ensure_ascii=False) + "\n"
    with open(path, "a", encoding="utf-8") as f:
        f.write(line)


if __name__ == "__main__":
    try:
        main()
    except Exception:  # noqa: BLE001 — hook 絕不能影響 Claude Code
        pass
    sys.exit(0)
