"""hook 腳本共用：判斷宿主（Claude Code／Codex）與解析專案根目錄。

Claude Code 會替 hook 設 CLAUDE_PROJECT_DIR；Codex 不會（也沒有任何對應的專案變數），
所以 Codex 下改由 QAOS_PROJECT_DIR 或 payload.cwd 所在 git repo 的 toplevel 推出專案根。
Claude 下的行為維持原樣（CLAUDE_PROJECT_DIR 優先）。任何錯誤都不外拋。
"""
import os
import subprocess


def detect_host(payload) -> str:
    """QAOS_HOOK_HOST 明確指定優先；否則 payload 帶 turn_id（Codex 的擴充欄位）就當 Codex。"""
    forced = (os.environ.get("QAOS_HOOK_HOST") or "").strip().lower()
    if forced in ("claude", "codex"):
        return forced
    return "codex" if isinstance(payload, dict) and "turn_id" in payload else "claude"


def _git_toplevel(cwd: str) -> str:
    try:
        r = subprocess.run(["git", "-C", cwd, "rev-parse", "--show-toplevel"], capture_output=True, text=True, timeout=2)
    except Exception:  # noqa: BLE001
        return ""
    return r.stdout.strip() if r.returncode == 0 else ""


def project_dir(payload, host: str | None = None) -> str:
    host = host or detect_host(payload)
    if host != "codex":
        v = os.environ.get("CLAUDE_PROJECT_DIR")
        if v:
            return v
    v = os.environ.get("QAOS_PROJECT_DIR")
    if v and os.path.isdir(v):
        return v
    cwd = (payload.get("cwd") if isinstance(payload, dict) else "") or os.getcwd()
    return _git_toplevel(cwd) or cwd
