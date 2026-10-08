"""Claude Code／Codex hook：從 stdin 讀 hook JSON，只留必要欄位，append 一行到 .warroom/events.jsonl。

保證：不打網路、不輸出 stdout、任何錯誤都吞掉並以 exit 0 結束（由 log_event.sh 再保險一次）。

PostToolUse 只記錄寫進 testcases/final/ 的檔案：Claude 的 Write／Edit 看 tool_input.file_path（比對方式維持原樣）；
Codex 的 apply_patch 沒有 file_path，從 patch 內文的 `*** Add/Update/Delete File:`、`*** Move to:` 行取路徑
（一個 patch 動到幾個 final 檔就記幾筆）。patch 裡的路徑可能是相對於工具 cwd 的相對路徑（甚至帶 ..），
所以先依 payload.cwd 解析並 normalize，再判斷是否落在 testcases/final/ 下。
"""
import json
import os
import re
import sys
import time

from _hostenv import project_dir

MAX_BYTES = 5 * 1024 * 1024   # 超過就輪替
KEEP_ROTATED = 3
FINAL_PREFIX = "testcases/final/"
PATCH_FILE_LINE = re.compile(r"^\*\*\* (?:Add File|Update File|Delete File|Move to): (.+?)\s*$", re.M)


def _written_paths(tool_input) -> list[tuple[str, bool]]:
    """回傳 [(路徑, 是否來自 patch 內文)]。"""
    if isinstance(tool_input, str):
        return [(x, True) for x in PATCH_FILE_LINE.findall(tool_input)]
    if not isinstance(tool_input, dict):
        return []
    fp = tool_input.get("file_path")
    if fp:
        return [(fp, False)]
    patch = tool_input.get("command") or tool_input.get("input") or ""
    return [(x, True) for x in PATCH_FILE_LINE.findall(patch)] if isinstance(patch, str) else []


def _final_path(raw_path: str, patch_cwd: str | None = None) -> str:
    """patch_cwd 有值（patch 路徑）時：相對路徑接到 cwd 後 normalize（消掉 .. 與 .），再找 testcases/final/。"""
    norm = raw_path.replace("\\", "/")
    if patch_cwd is not None:
        if not norm.startswith("/"):
            norm = patch_cwd.replace("\\", "/").rstrip("/") + "/" + norm
        norm = os.path.normpath(norm).replace("\\", "/")
    idx = norm.find(FINAL_PREFIX)
    return norm[idx:] if idx >= 0 else ""


def main() -> None:
    raw = sys.stdin.read()
    if not raw.strip():
        return
    p = json.loads(raw)
    ev = p.get("hook_event_name") or ""
    tool_input = p.get("tool_input") or {}

    if ev == "PostToolUse":
        cwd = p.get("cwd") or os.getcwd()
        file_paths = [fp for fp in (_final_path(x, cwd if from_patch else None) for x, from_patch in _written_paths(tool_input)) if fp]
        if not file_paths:
            return
    else:
        file_paths = [""]

    base = {
        "session_id": p.get("session_id") or "",
        "event": ev,
        "agent_id": p.get("agent_id") or "",
        "agent_type": p.get("agent_type") or "",
        "subagent_name": p.get("subagent_name") or "",
        "tool_name": p.get("tool_name") or "",
        "reason": p.get("reason") or p.get("source") or "",
        "cwd": p.get("cwd") or "",
        "transcript_path": p.get("transcript_path") or "",
        "tag": os.environ.get("QAOS_TRACK", ""),
    }

    warroom = os.path.join(project_dir(p), ".warroom")
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

    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with open(path, "a", encoding="utf-8") as f:
        for fp in file_paths:
            rec = {"ts": ts, **base, "file_path": fp}
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    try:
        main()
    except Exception:  # noqa: BLE001 — hook 絕不能影響 Claude Code
        pass
    sys.exit(0)
