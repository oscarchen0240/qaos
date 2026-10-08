"""Codex 版 hooks：同一批 hook 腳本在 Codex 下的行為，以及 .codex/ 資產的一致性。

Codex 與 Claude Code 的差異（實測，Codex 0.160）：
- 不設 CLAUDE_PROJECT_DIR → 專案根改由 QAOS_PROJECT_DIR／payload.cwd 的 git toplevel 推出（session cwd 可能是子目錄）
- PreToolUse 不支援 permissionDecision=ask（會顯示 hook 失敗、指令照跑）→ 守門改 deny
- 檔案編輯工具叫 apply_patch，tool_input 沒有 file_path（路徑在 patch 內文）
"""
import importlib.machinery
import importlib.util
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tomllib

import pytest
import yaml

ADMIN_DIR = pathlib.Path(__file__).resolve().parents[2]
HOOKS_DIR = ADMIN_DIR / "hooks"
REPO_ROOT = ADMIN_DIR.parent
LAUNCHER = HOOKS_DIR / "codex" / "qaos-codex"
DEFINITION = HOOKS_DIR / "codex" / "qaos-hooks.json"


def _load(path: pathlib.Path, name: str):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def _hostenv():
    if str(HOOKS_DIR) not in sys.path:
        sys.path.insert(0, str(HOOKS_DIR))
    return _load(HOOKS_DIR / "_hostenv.py", "qaos_hostenv_under_test")


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


def test_log_event_codex_relative_patch_paths_resolve_against_cwd(repo):
    """Codex review R1-02：session cwd 在 <repo>/testcases 時，patch 裡的 final/X.html 實際寫進 testcases/final/，要記到。"""
    cwd = repo / "testcases"
    cwd.mkdir()
    patch = "*** Begin Patch\n*** Add File: final/X-final.html\n+x\n*** Update File: ../docs/notes.md\n@@\n-a\n+b\n*** End Patch"
    run_codex_hook("log_event.py", _post_patch(repo, cwd, patch), cwd, QAOS_HOOK_HOST="codex")
    assert [e["file_path"] for e in _events(repo)] == ["testcases/final/X-final.html"]


def test_log_event_codex_dotdot_escaping_final_is_not_recorded(repo):
    """testcases/final/../../docs/X.html 實際在 final 目錄外，不可誤記。"""
    patch = "*** Begin Patch\n*** Add File: {r}/testcases/final/../../docs/X.html\n+x\n*** End Patch".format(r=repo)
    run_codex_hook("log_event.py", _post_patch(repo, repo, patch), repo, QAOS_HOOK_HOST="codex")
    assert _events(repo) == []


def test_log_event_codex_relative_path_from_repo_root(repo):
    patch = "*** Begin Patch\n*** Add File: testcases/final/A-final.html\n+x\n*** End Patch"
    run_codex_hook("log_event.py", _post_patch(repo, repo, patch), repo, QAOS_HOOK_HOST="codex")
    assert [e["file_path"] for e in _events(repo)] == ["testcases/final/A-final.html"]


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


def test_project_dir_claude_fallback_is_unchanged(repo, monkeypatch):
    """Codex review R1-03：Claude 沒有 CLAUDE_PROJECT_DIR 時維持舊 fallback（payload.cwd → os.getcwd()），
    不套用 QAOS_PROJECT_DIR 或 git toplevel；這兩個只屬於 Codex。"""
    h = _hostenv()
    sub = str(repo / "sub")
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    monkeypatch.setenv("QAOS_PROJECT_DIR", str(repo))          # Claude 分支不可讀這個
    monkeypatch.setenv("QAOS_HOOK_HOST", "claude")
    assert h.project_dir({"cwd": sub}) == sub                   # 不是 repo toplevel
    monkeypatch.chdir(repo / "sub" / "dir")
    assert h.project_dir({}) == os.getcwd()
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", "/claude/proj")
    assert h.project_dir({"cwd": sub}) == "/claude/proj"        # 有設時一律優先


def test_project_dir_codex_branch(repo, tmp_path_factory, monkeypatch):
    h = _hostenv()
    monkeypatch.setenv("QAOS_HOOK_HOST", "codex")
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", "/claude/proj")    # Codex 分支忽略它
    monkeypatch.delenv("QAOS_PROJECT_DIR", raising=False)
    assert h.project_dir({"cwd": str(repo / "sub" / "dir")}) == str(repo)
    other = tmp_path_factory.mktemp("proj")
    monkeypatch.setenv("QAOS_PROJECT_DIR", str(other))
    assert h.project_dir({"cwd": str(repo)}) == str(other)
    monkeypatch.setenv("QAOS_PROJECT_DIR", "/no/such/dir")      # 無效 override 退回 git toplevel
    assert h.project_dir({"cwd": str(repo / "sub")}) == str(repo)


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


@pytest.fixture
def hooked_repo(repo: pathlib.Path) -> pathlib.Path:
    """repo 內放一份 admin-ui/hooks（含可執行的 .sh），像真實專案。"""
    shutil.copytree(HOOKS_DIR, repo / "admin-ui" / "hooks")
    return repo


def test_launcher_resolves_project_root_from_cwd_or_cd_flag(hooked_repo):
    L = _load(LAUNCHER, "qaos_codex_launcher")
    sub = hooked_repo / "sub" / "dir"
    assert L.resolve_project_dir(["-C", str(sub), "x"], {}) == hooked_repo
    assert L.resolve_project_dir([f"--cd={sub}"], {}) == hooked_repo
    assert L.resolve_project_dir([f"-C{sub}"], {}) == hooked_repo
    assert L.resolve_project_dir(["exec", "--cd", str(sub), "prompt"], {}) == hooked_repo
    assert L.resolve_project_dir([], {"QAOS_PROJECT_DIR": str(hooked_repo)}) == hooked_repo     # 有效 override


def test_launcher_refuses_when_root_cannot_be_verified(tmp_path, tmp_path_factory, hooked_repo, monkeypatch):
    """Codex review R1-01：找不到 git 根目錄、override 無效、或腳本缺少時一律中止，不啟動沒有守門的 session。"""
    L = _load(LAUNCHER, "qaos_codex_launcher2")
    nongit = tmp_path_factory.mktemp("nongit")
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(nongit.parent))     # 避免上層目錄剛好是 git repo
    with pytest.raises(L.LauncherError, match="找不到 QAOS 專案根"):
        L.resolve_project_dir(["-C", str(nongit)], {})
    with pytest.raises(L.LauncherError, match="不是目錄"):
        L.resolve_project_dir([], {"QAOS_PROJECT_DIR": "/no/such/dir"})
    with pytest.raises(L.LauncherError, match="缺少或不可執行"):
        L.resolve_project_dir([], {"QAOS_PROJECT_DIR": str(nongit)})                    # 目錄存在但沒有 hook 腳本
    (hooked_repo / "admin-ui" / "hooks" / "guard_qaos.sh").chmod(0o644)
    with pytest.raises(L.LauncherError, match="guard_qaos.sh"):
        L.resolve_project_dir([], {"QAOS_PROJECT_DIR": str(hooked_repo)})              # 守門腳本不可執行


def test_launcher_rejects_directory_posing_as_hook_script(hooked_repo, tmp_path_factory):
    """Codex review R2-01：os.access(X_OK) 對目錄也是 True，守門入口是目錄時不可通過驗證，也不可啟動 codex。"""
    L = _load(LAUNCHER, "qaos_codex_launcher3")
    guard = hooked_repo / "admin-ui" / "hooks" / "guard_qaos.sh"
    guard.unlink()
    guard.mkdir(mode=0o755)
    with pytest.raises(L.LauncherError, match="guard_qaos.sh"):
        L.resolve_project_dir([], {"QAOS_PROJECT_DIR": str(hooked_repo)})
    work = tmp_path_factory.mktemp("fake")
    marker = work / "ran"
    env = _codex_env(CODEX_BIN=str(_fake_codex(work)), FAKE_CODEX_MARKER=str(marker))
    r = subprocess.run([sys.executable, str(LAUNCHER), "exec", "-C", str(hooked_repo), "hi"], capture_output=True, text=True, env=env, cwd=work, timeout=20)
    assert r.returncode != 0 and not marker.exists() and "guard_qaos.sh" in r.stderr


def test_launcher_accepts_symlinked_hook_script(hooked_repo):
    L = _load(LAUNCHER, "qaos_codex_launcher4")
    real = hooked_repo / "real_guard.sh"
    shutil.copy2(HOOKS_DIR / "guard_qaos.sh", real)
    guard = hooked_repo / "admin-ui" / "hooks" / "guard_qaos.sh"
    guard.unlink()
    guard.symlink_to(real)
    assert L.resolve_project_dir([], {"QAOS_PROJECT_DIR": str(hooked_repo)}) == hooked_repo


def test_launcher_cd_scan_stops_at_double_dash(hooked_repo, monkeypatch):
    """Codex review R2-02：`--` 之後是提示文字，以 -C／--cd= 開頭也不是選項；專案根仍由目前目錄決定，參數原樣傳給 codex。"""
    L = _load(LAUNCHER, "qaos_codex_launcher5")
    monkeypatch.chdir(hooked_repo / "sub")
    monkeypatch.delenv("QAOS_PROJECT_DIR", raising=False)
    assert L._cd_target(["exec", "--", "-C/no/such/qaos-directory"]) == os.getcwd()
    assert L._cd_target(["exec", "--", "--cd=/no/such/qaos-directory"]) == os.getcwd()
    assert L.resolve_project_dir(["exec", "--", "-C/no/such/qaos-directory"], {}) == hooked_repo
    assert L._cd_target(["-C", "/x", "--", "-C/y"]) == "/x"                    # `--` 之前的仍照常解析


def test_launcher_passes_prompt_after_double_dash_through_untouched(hooked_repo, tmp_path_factory):
    work = tmp_path_factory.mktemp("fake")
    marker = work / "ran"
    env = _codex_env(CODEX_BIN=str(_fake_codex(work)), FAKE_CODEX_MARKER=str(marker))
    r = subprocess.run([sys.executable, str(LAUNCHER), "exec", "--", "-C/no/such/qaos-directory"], capture_output=True, text=True,
                       env=env, cwd=hooked_repo / "sub", timeout=20)
    assert r.returncode == 0 and marker.exists()
    args = [l[4:] for l in r.stdout.splitlines() if l.startswith("ARG:")]
    assert args[16:] == ["exec", "--", "-C/no/such/qaos-directory"]
    assert r.stdout.splitlines()[0] == f"ROOT={hooked_repo}"


def _fake_codex(tmp_path: pathlib.Path) -> pathlib.Path:
    f = tmp_path / "fake-codex"
    f.write_text('#!/bin/bash\necho "ROOT=$QAOS_PROJECT_DIR"\nprintf "ARG:%s\\n" "$@"\ntouch "$FAKE_CODEX_MARKER"\n')
    f.chmod(0o755)
    return f


def test_launcher_exec_passes_verified_root_and_hooks_to_codex(hooked_repo, tmp_path_factory):
    work = tmp_path_factory.mktemp("fake")
    marker = work / "ran"
    env = _codex_env(CODEX_BIN=str(_fake_codex(work)), FAKE_CODEX_MARKER=str(marker))
    r = subprocess.run([sys.executable, str(LAUNCHER), "exec", "-C", str(hooked_repo / "sub" / "dir"), "hi"],
                       capture_output=True, text=True, env=env, cwd=work, timeout=20)
    assert r.returncode == 0 and marker.exists()
    lines = r.stdout.splitlines()
    assert lines[0] == f"ROOT={hooked_repo}"                    # 驗證過的絕對根目錄傳給 codex
    args = [l[4:] for l in lines if l.startswith("ARG:")]
    assert args[0:16:2] == ["-c"] * 8 and all(a.startswith("hooks.") for a in args[1:16:2])      # 8 個事件的 -c 參數在最前面
    assert args[16:] == ["exec", "-C", str(hooked_repo / "sub" / "dir"), "hi"]                  # 使用者參數原樣轉給 codex


def test_launcher_exec_aborts_without_starting_codex_outside_git(tmp_path_factory):
    work = tmp_path_factory.mktemp("fake")
    nongit = tmp_path_factory.mktemp("nongit")
    marker = work / "ran"
    env = _codex_env(CODEX_BIN=str(_fake_codex(work)), FAKE_CODEX_MARKER=str(marker), GIT_CEILING_DIRECTORIES=str(nongit.parent))
    r = subprocess.run([sys.executable, str(LAUNCHER), "exec", "hi"], capture_output=True, text=True, env=env, cwd=nongit, timeout=20)
    assert r.returncode != 0 and not marker.exists()            # codex 沒被啟動
    assert "找不到 QAOS 專案根" in r.stderr


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
SYNC_AGENTS = HOOKS_DIR / "codex" / "sync-agents"
SYNC_HINT = "請執行 admin-ui/hooks/codex/sync-agents 重新產生 .codex/agents 並一併 commit"


def test_codex_agents_are_in_sync_with_the_generator():
    r = subprocess.run([sys.executable, str(SYNC_AGENTS), "--check"], capture_output=True, text=True, cwd=REPO_ROOT)
    assert r.returncode == 0, f"{r.stdout}\n{SYNC_HINT}"


def test_codex_agents_match_claude_agents():
    """獨立於產生器再驗一次語意：名稱、描述、本文逐字一致（只允許產生器的宿主用語替換）。"""
    ALLOWED_BODY_SUBSTITUTIONS = _load(SYNC_AGENTS, "qaos_sync_agents").SUBSTITUTIONS
    codex_dir, claude_dir = REPO_ROOT / ".codex" / "agents", REPO_ROOT / ".claude" / "agents"
    tomls = sorted(codex_dir.glob("*.toml"))
    assert tomls, ".codex/agents 不應是空的"
    assert [t.stem for t in tomls] == sorted(m.stem for m in claude_dir.glob("*.md"))      # 兩邊 agent 集合相同
    for t in tomls:
        d = tomllib.loads(t.read_text(encoding="utf-8"))
        assert set(d) == {"name", "description", "developer_instructions"}
        m = re.match(r"^---\n(.*?)\n---\n(.*)$", (claude_dir / f"{t.stem}.md").read_text(encoding="utf-8"), re.S)
        front = yaml.safe_load(m.group(1))
        body = m.group(2).strip()
        for old, new in ALLOWED_BODY_SUBSTITUTIONS.get(t.stem, []):
            assert old in body, f"{t.stem}: 允許的替換 {old!r} 在 Claude 版找不到，請更新 ALLOWED_BODY_SUBSTITUTIONS"
            body = body.replace(old, new)
        assert d["name"] == front["name"] == t.stem
        assert d["description"] == front["description"]
        assert d["developer_instructions"].strip() == body, f"{t.name} 與 .claude/agents/{t.stem}.md 內容不一致。{SYNC_HINT}"


# ---- sync-agents 產生器的邊界（Codex review 第 04 輪 P2 ×2）
def _gen():
    return _load(SYNC_AGENTS, "qaos_sync_agents_edge")


def _md(tmp_path, front: str, body: str, stem: str = "probe"):
    p = tmp_path / f"{stem}.md"
    p.write_text(f"---\n{front}\n---\n{body}", encoding="utf-8")
    return p


def test_sync_agents_parses_frontmatter_as_yaml(tmp_path):
    """帶引號、冒號、跳脫字元的描述要和 YAML 語意一致，不能把引號當成內容。"""
    cases = {
        'description: "quoted: description"': "quoted: description",
        "description: 'single ''quoted'' text'": "single 'quoted' text",
        'description: "tab\\there and \\"escape\\""': 'tab\there and "escape"',
        "description: plain: value with colon": None,         # 這種寫法 YAML 本身就不合法 → 產生器要中止，不是默默吞掉
    }
    for line, expected in cases.items():
        md = _md(tmp_path, f"name: probe\n{line}", "body")
        if expected is None:
            with pytest.raises(Exception):
                _gen().render(md)
            continue
        parsed = tomllib.loads(_gen().render(md))
        assert parsed["description"] == expected == yaml.safe_load(f"name: probe\n{line}")["description"]


def test_sync_agents_rejects_missing_or_non_string_frontmatter(tmp_path):
    for front in ("name: probe", "name: probe\ndescription: 123", "description: only"):
        with pytest.raises(SystemExit):
            _gen().render(_md(tmp_path, front, "body"))


@pytest.mark.parametrize("n", [1, 2, 3, 4, 5, 6, 7])
def test_sync_agents_round_trips_runs_of_double_quotes_and_backslashes(tmp_path, n):
    q, bs = '"' * n, "\\"
    bodies = [f"start{q}end", f"{q}start", f"end{q}", f"a{q}b{bs}{q}c", f"{bs}{q}{bs}{bs}{q}", f"x{bs}", f"line1\n{q}\nline3", f"{q}"]
    for body in bodies:
        md = _md(tmp_path, "name: probe\ndescription: d", body)
        assert tomllib.loads(_gen().render(md))["developer_instructions"].strip() == body.strip(), repr(body)
