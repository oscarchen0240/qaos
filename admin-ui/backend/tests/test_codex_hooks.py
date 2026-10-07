"""Codex 版 hooks：同一批 hook 腳本在 Codex 下的行為，以及 .codex/ 資產的一致性。

Codex 與 Claude Code 的差異（實測，Codex 0.160）：
- 不設 CLAUDE_PROJECT_DIR → 專案根改由 QAOS_PROJECT_DIR／payload.cwd 的 git toplevel 推出（session cwd 可能是子目錄）
- PreToolUse 不支援 permissionDecision=ask（會顯示 hook 失敗、指令照跑）→ 守門改 deny
- 檔案編輯工具叫 apply_patch，tool_input 沒有 file_path（路徑在 patch 內文）
"""
import json
import os
import pathlib
import re
import subprocess
import sys
import tomllib

import pytest

ADMIN_DIR = pathlib.Path(__file__).resolve().parents[2]
HOOKS_DIR = ADMIN_DIR / "hooks"
REPO_ROOT = ADMIN_DIR.parent
LAUNCHER = HOOKS_DIR / "codex" / "qaos-codex"
DEFINITION = HOOKS_DIR / "codex" / "qaos-hooks.json"


@pytest.fixture
def repo(tmp_path: pathlib.Path) -> pathlib.Path:
    """假專案（git repo）。session cwd 放在子目錄，驗證不會把 .warroom 建在子目錄。"""
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "sub" / "dir").mkdir(parents=True)
    return tmp_path.resolve()


def _codex_env(**extra) -> dict:
    env = {k: v for k, v in os.environ.items() if not k.startswith("CLAUDE") and k not in ("QAOS_PROJECT_DIR", "QAOS_HOOK_HOST")}
    env.update(extra)
    return env


def run_codex_hook(name: str, payload: dict | str, cwd: pathlib.Path, **env_extra):
    raw = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)
    r = subprocess.run([sys.executable, str(HOOKS_DIR / name)], input=raw, capture_output=True, text=True,
                       cwd=cwd, env=_codex_env(**env_extra), timeout=20)
    return r.returncode, r.stdout, r.stderr


def _events(root: pathlib.Path) -> list[dict]:
    p = root / ".warroom" / "events.jsonl"
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines()] if p.exists() else []


def _pre(cmd: str, **extra) -> dict:
    return {"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": cmd}, "session_id": "s1", "turn_id": "t1", **extra}


# ------------------------------------------------------------------ guard_qaos：Codex 下 deny
@pytest.mark.parametrize("cmd", [
    "bin/qaos approve APR-0001 --decision approve --by me",
    "bin/qaos clarification answer CLR-X --answer 'y' --by me",
    "bin/qaos bug close BUG-X --by me",
])
def test_guard_codex_denies_human_decision_commands(repo, cmd):
    rc, out, _ = run_codex_hook("guard_qaos.py", _pre(cmd), repo / "sub" / "dir", QAOS_HOOK_HOST="codex")
    assert rc == 0
    hso = json.loads(out.strip())["hookSpecificOutput"]
    assert hso["hookEventName"] == "PreToolUse"
    assert hso["permissionDecision"] == "deny"          # Codex 不支援 ask
    assert hso["permissionDecisionReason"].strip() and "指揮台" in hso["permissionDecisionReason"]  # deny 必須帶非空理由


def test_guard_detects_codex_from_turn_id_without_env(repo):
    rc, out, _ = run_codex_hook("guard_qaos.py", _pre("bin/qaos approve APR-1 --by me"), repo)
    assert json.loads(out.strip())["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_guard_forced_claude_host_still_asks_even_with_turn_id(repo):
    rc, out, _ = run_codex_hook("guard_qaos.py", _pre("bin/qaos approve APR-1 --by me"), repo, QAOS_HOOK_HOST="claude")
    assert json.loads(out.strip())["hookSpecificOutput"]["permissionDecision"] == "ask"


def test_guard_codex_other_commands_and_garbage_pass_through(repo):
    for payload in (_pre("bin/qaos run show RUN-1"), _pre("pytest -q"), "{{{", ""):
        rc, out, _ = run_codex_hook("guard_qaos.py", payload, repo, QAOS_HOOK_HOST="codex")
        assert rc == 0 and out.strip() == ""


# ------------------------------------------------------------------ log_event
PATCH = """*** Begin Patch
*** Add File: {root}/testcases/final/CASHOUT-final.html
+<html></html>
*** Update File: {root}/testcases/final/CASHOUT-final.json
@@
-a
+b
*** Update File: {root}/docs/notes.md
@@
-x
+y
*** End Patch"""


def _post_patch(root: pathlib.Path, cwd: pathlib.Path, patch: str) -> dict:
    return {"hook_event_name": "PostToolUse", "tool_name": "apply_patch", "tool_input": {"command": patch},
            "tool_response": "ok", "tool_use_id": "u1", "session_id": "s1", "turn_id": "t1", "cwd": str(cwd), "transcript_path": None}


def test_log_event_codex_apply_patch_records_only_final_files_at_repo_root(repo):
    cwd = repo / "sub" / "dir"
    rc, out, _ = run_codex_hook("log_event.py", _post_patch(repo, cwd, PATCH.format(root=repo)), cwd, QAOS_HOOK_HOST="codex")
    assert rc == 0 and out == ""
    ev = _events(repo)
    assert [e["file_path"] for e in ev] == ["testcases/final/CASHOUT-final.html", "testcases/final/CASHOUT-final.json"]
    assert all(e["event"] == "PostToolUse" and e["tool_name"] == "apply_patch" and e["session_id"] == "s1" for e in ev)
    assert not (cwd / ".warroom").exists()               # 不可把 .warroom 建在 session cwd 的子目錄


def test_log_event_codex_apply_patch_outside_final_is_ignored(repo):
    patch = "*** Begin Patch\n*** Add File: {r}/docs/a.md\n+x\n*** End Patch".format(r=repo)
    rc, _, _ = run_codex_hook("log_event.py", _post_patch(repo, repo, patch), repo, QAOS_HOOK_HOST="codex")
    assert rc == 0 and _events(repo) == []


def test_log_event_codex_session_events_use_git_toplevel_not_cwd(repo):
    """SessionStart／SessionEnd 的 Codex payload 沒有 turn_id，不能靠 payload 判斷宿主；專案根仍要是 git toplevel。"""
    cwd = repo / "sub" / "dir"
    start = {"hook_event_name": "SessionStart", "session_id": "s1", "cwd": str(cwd), "model": "m", "permission_mode": "default",
             "source": "startup", "transcript_path": None}
    run_codex_hook("log_event.py", start, cwd, QAOS_HOOK_HOST="codex")
    ev = _events(repo)
    assert len(ev) == 1 and ev[0]["event"] == "SessionStart" and ev[0]["reason"] == "startup" and ev[0]["transcript_path"] == ""
    assert not (cwd / ".warroom").exists()


def test_log_event_project_dir_override_wins(repo, tmp_path_factory):
    other = tmp_path_factory.mktemp("proj")
    run_codex_hook("log_event.py", {"hook_event_name": "Stop", "session_id": "s1", "cwd": str(repo)}, repo,
                   QAOS_HOOK_HOST="codex", QAOS_PROJECT_DIR=str(other))
    assert len(_events(other)) == 1 and _events(repo) == []


def test_log_event_claude_write_behaviour_unchanged(run_hook, qaos_root):
    """Claude：CLAUDE_PROJECT_DIR 優先、Write 的 file_path 只記 testcases/final/。"""
    final = qaos_root / "testcases" / "final" / "X-final.html"
    run_hook("log_event.py", {"hook_event_name": "PostToolUse", "tool_name": "Write", "tool_input": {"file_path": str(final)}, "session_id": "s1", "cwd": str(qaos_root / "elsewhere")})
    run_hook("log_event.py", {"hook_event_name": "PostToolUse", "tool_name": "Edit", "tool_input": {"file_path": str(qaos_root / "docs" / "a.md")}, "session_id": "s1"})
    ev = _events(qaos_root)
    assert [(e["event"], e["tool_name"], e["file_path"]) for e in ev] == [("PostToolUse", "Write", "testcases/final/X-final.html")]


# ------------------------------------------------------------------ handoff_relay
def test_handoff_relay_works_under_codex_without_claude_project_dir(repo, qaos_root, write_run, write_handoff, read_handoff):
    """Codex：沒有 CLAUDE_PROJECT_DIR、cwd 在子目錄，仍要從 git toplevel 找到 .warroom/handoff.jsonl 與 runs/。
    repo 與 qaos_root 是同一個 tmp 目錄（repo 已 git init，qaos_root 補上 runs/ .warroom/）。"""
    assert repo == qaos_root.resolve()
    sub = repo / "sub"
    write_run("RUN-A", "RUNNING", "T3", [("T2", "DONE", "agent-test-designer"), ("T3", "READY", "agent-test-validator")])
    write_handoff("h-resume", "sess-A", "RUN-A")
    ups = {"hook_event_name": "UserPromptSubmit", "session_id": "sess-A", "turn_id": "t1", "cwd": str(sub), "prompt": "go"}
    rc, out, _ = run_codex_hook("handoff_relay.py", ups, sub, QAOS_HOOK_HOST="codex")
    assert rc == 0 and "QAOS 指揮台交接" in out and "RUN-A" in out
    stop = {"hook_event_name": "Stop", "session_id": "sess-A", "turn_id": "t1", "cwd": str(sub), "stop_hook_active": False, "last_assistant_message": "done"}
    rc, out, _ = run_codex_hook("handoff_relay.py", stop, sub, QAOS_HOOK_HOST="codex")
    payload = json.loads(out.strip())
    assert payload["decision"] == "block" and "RUN-A" in payload["reason"]      # Codex 的 Stop 輸出 schema 同樣是 decision=block＋reason
    assert [c["handoff_id"] for c in read_handoff() if c.get("kind") == "consumed"] == ["h-resume"]


# ------------------------------------------------------------------ 啟動器與 hooks 定義
def _launcher_flags() -> list[str]:
    return json.loads(subprocess.check_output([sys.executable, str(LAUNCHER), "--qaos-print-flags"], text=True))


def test_launcher_flags_round_trip_the_definition():
    flags = _launcher_flags()
    definition = json.loads(DEFINITION.read_text(encoding="utf-8"))["hooks"]
    assert flags[0::2] == ["-c"] * len(definition) and len(flags) == 2 * len(definition)
    parsed = {}
    for f in flags[1::2]:
        parsed.update(tomllib.loads(f)["hooks"])           # `hooks.X=[...]` 必須是合法 TOML，內容與 JSON 定義一致
    assert parsed == definition


def test_codex_hook_commands_are_codex_ready():
    definition = json.loads(DEFINITION.read_text(encoding="utf-8"))["hooks"]
    assert set(definition) == {"SessionStart", "SessionEnd", "UserPromptSubmit", "PreToolUse", "PostToolUse", "SubagentStart", "SubagentStop", "Stop"}
    commands = [(ev, h) for ev, groups in definition.items() for g in groups for h in g["hooks"]]
    assert len(commands) == 9                                # 與 .claude/settings.local.json 同為 9 個 hook
    for ev, h in commands:
        assert "CLAUDE_PROJECT_DIR" not in h["command"]      # Codex 不會設這個變數
        assert "git rev-parse --show-toplevel" in h["command"] and "QAOS_HOOK_HOST=codex" in h["command"]
        script = re.search(r"/admin-ui/hooks/(\w+\.sh)$", h["command"]).group(1)
        assert (HOOKS_DIR / script).is_file()
    assert [h["timeout"] for ev, h in commands if ev == "SessionEnd"] == [3]   # Codex 會把 SessionEnd 逾時夾到 3 秒
    post = definition["PostToolUse"][0]["matcher"]
    assert "apply_patch" in post.split("|") and definition["PreToolUse"][0]["matcher"] == "Bash"


def test_codex_hooks_mirror_claude_settings():
    """事件與腳本的對應要和 .claude/settings.local.json 一致（只允許 matcher 多 apply_patch、SessionEnd timeout 不同）。"""
    claude = json.loads((REPO_ROOT / ".claude" / "settings.local.json").read_text(encoding="utf-8"))["hooks"]
    codex = json.loads(DEFINITION.read_text(encoding="utf-8"))["hooks"]
    def scripts(defn):
        return {ev: [os.path.basename(h["command"].rstrip('"')) for g in groups for h in g["hooks"]] for ev, groups in defn.items()}
    assert scripts(codex) == scripts(claude)


def test_no_project_level_codex_hooks_json_is_tracked():
    """專案層 .codex/hooks.json 會讓每個 worktree／審查 session 都跳 Hooks need review（信任 key 含絕對路徑），不可進版控。"""
    r = subprocess.run(["git", "-C", str(REPO_ROOT), "ls-files", ".codex/hooks.json"], capture_output=True, text=True)
    if r.returncode != 0:
        pytest.skip("not a git checkout")
    assert r.stdout.strip() == ""


# ------------------------------------------------------------------ .codex/agents 與 .claude/agents 一致
ALLOWED_BODY_SUBSTITUTIONS = {"qaos-test-designer": [("Claude Code session", "Codex session")]}


def test_codex_agents_match_claude_agents():
    codex_dir, claude_dir = REPO_ROOT / ".codex" / "agents", REPO_ROOT / ".claude" / "agents"
    tomls = sorted(codex_dir.glob("*.toml"))
    assert tomls, ".codex/agents 不應是空的"
    assert [t.stem for t in tomls] == sorted(m.stem for m in claude_dir.glob("*.md"))      # 兩邊 agent 集合相同
    for t in tomls:
        d = tomllib.loads(t.read_text(encoding="utf-8"))
        assert set(d) == {"name", "description", "developer_instructions"}
        m = re.match(r"^---\n(.*?)\n---\n(.*)$", (claude_dir / f"{t.stem}.md").read_text(encoding="utf-8"), re.S)
        front = dict(l.split(": ", 1) for l in m.group(1).splitlines() if ": " in l)
        body = m.group(2).strip()
        for old, new in ALLOWED_BODY_SUBSTITUTIONS.get(t.stem, []):
            assert old in body, f"{t.stem}: 允許的替換 {old!r} 在 Claude 版找不到，請更新 ALLOWED_BODY_SUBSTITUTIONS"
            body = body.replace(old, new)
        assert d["name"] == front["name"] == t.stem
        assert d["description"] == front["description"]
        assert d["developer_instructions"].strip() == body, f"{t.name} 與 .claude/agents/{t.stem}.md 內容不一致"
