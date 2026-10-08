"""需求 A 部署後 admin-ui 的相容修正（2026-10-08）。

需求 A 之後 bin/qaos 的行為改變，影響平台代為執行的指令：
- 寫入指令以「請求內容」算 op_id，內容相同的重送會被當成先前已完成：印出成功訊息、rc=0，但不寫入。
  Bug 有重開迴圈（RESOLVED→OPEN→IN_PROGRESS），所以人工決定的指令與重建 index 一律要帶 --new-request。
- clarification apply 必須帶 --path 與 --impact-reviewed（沒有 --note）；withdraw 必須帶 --reason。
- clarification list 改為唯讀，重建 index 要用 clarification index。
- CLR 新增非終止狀態 INCORPORATED；轉換帶 kinds（文件索取單不是用 apply 結案）。
- PROJECT_ROOT 若是 git worktree，寫入會落在副本 → 平台拒絕執行 bin/qaos。
"""
import json
import pathlib
import subprocess
import sys

import pytest
import yaml

ADMIN_DIR = pathlib.Path(__file__).resolve().parents[2]
REAL_SM = ADMIN_DIR.parent / "workflows" / "state-machines.yaml"


def _clr(root: pathlib.Path, clr_id: str, status: str, **extra) -> pathlib.Path:
    d = root / "clarifications" / "ba-admin" / "AREA"
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{clr_id}.yaml"
    p.write_text(yaml.safe_dump({"clarification_id": clr_id, "product": "ba-admin", "functional_area": "AREA", "spec_id": "SPEC-AREA-001", "spec_version": "0.1",
                                 "status": status, "question": "q?", "raised_at": "2026-10-01T00:00:00Z", **extra}, allow_unicode=True), encoding="utf-8")
    return p


def _bug(root: pathlib.Path, bug_id: str, status: str) -> None:
    d = root / "bugs" / "ba-admin" / "AREA"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{bug_id}.yaml").write_text(yaml.safe_dump({"bug_id": bug_id, "status": status, "title": "t"}, allow_unicode=True), encoding="utf-8")


@pytest.fixture
def real_sm(sandbox, monkeypatch):
    """用 repo 目前真正的 workflows/state-machines.yaml（需求 A 之後的版本）。"""
    monkeypatch.setattr(sandbox.tickets, "SM_PATH", REAL_SM)
    sandbox.tickets._cache.clear()
    return sandbox


# ------------------------------------------------------------ 指令組法
def test_withdraw_uses_reason_not_note(sandbox):
    out = sandbox.tickets.clarification_command("CLR-T-1", {"decision": "withdraw", "rationale": "重複提問"})
    assert out["warnings"] == []
    assert "--reason" in out["command"] and "--note" not in out["command"] and out["command"].endswith("--new-request")


def test_withdraw_without_reason_is_blocked_with_a_clear_warning(sandbox):
    out = sandbox.tickets.clarification_command("CLR-T-1", {"decision": "withdraw", "rationale": ""})
    assert any("--reason" in w for w in out["warnings"])


def test_apply_is_never_executable_from_the_console(sandbox):
    """apply 要 --path／--impact-reviewed／逐張 --tc-conclusion，指揮台不執行：永遠帶警告（按鈕停用、後端 409），只給指令骨架。"""
    _clr(sandbox.root, "CLR-T-2", "ANSWERED")
    out = sandbox.tickets.clarification_command("CLR-T-2", {"decision": "apply", "rationale": "x"})
    assert out["warnings"] and "--path" in out["warnings"][0]
    assert "--path" in out["command"] and "--impact-reviewed" in out["command"] and "--note" not in out["command"]


def test_apply_warning_for_document_request_points_to_fulfill(sandbox):
    _clr(sandbox.root, "CLR-T-3", "OPEN", kind="document_request")
    out = sandbox.tickets.clarification_command("CLR-T-3", {"decision": "apply"})
    assert "fulfill" in out["warnings"][0]


def test_ask_and_answer_keep_their_flags_and_add_new_request(sandbox):
    a = sandbox.tickets.clarification_command("CLR-T-4", {"decision": "ask", "extra": {"asked_to": "PM"}})
    assert a["warnings"] == [] and a["command"].endswith("--new-request") and "--to PM" in a["command"]
    b = sandbox.tickets.clarification_command("CLR-T-4", {"decision": "answer", "rationale": "回答", "extra": {"answered_by": "PM", "resolution": "no_change"}})
    assert b["warnings"] == [] and b["command"].endswith("--new-request") and "--resolution no_change" in b["command"]


@pytest.mark.parametrize("draft", [
    {"decision": "resolve", "extra": {"external_ref": "J-1"}},
    {"decision": "verify", "extra": {"execution_id": "EXE-20261008-001"}},
    {"decision": "close"},
    {"decision": "transition", "extra": {"to": "IN_PROGRESS"}},
])
def test_every_bug_decision_command_carries_new_request(sandbox, draft):
    """重開迴圈下內容相同的請求會合法地再次出現；少了 --new-request 會「印成功卻沒寫入」。"""
    out = sandbox.tickets.bug_command("BUG-T-1", draft)
    assert out["warnings"] == [] and out["command"].endswith("--new-request")


# ------------------------------------------------------------ 執行後重建 index
def test_clarification_action_rebuilds_index_with_new_request_and_never_calls_list(real_sm, fake_qaos, write_run):
    sb = real_sm
    _clr(sb.root, "CLR-T-5", "OPEN")
    sb.tickets.save_draft("CLR-T-5", "clarification", "ask", None, "", None, {"asked_to": "PM"})
    res = sb.qaos_exec.execute("CLR-T-5")
    assert res["ok"] and fake_qaos["calls"][-1] == "bin/qaos clarification index --new-request"
    assert not any(c.startswith("bin/qaos clarification list") for c in fake_qaos["calls"])
    assert "clarifications/index.md 已重建" in res["hint"]


def test_bug_action_rebuilds_index_with_new_request(real_sm, fake_qaos):
    sb = real_sm
    _bug(sb.root, "BUG-T-2", "OPEN")
    sb.tickets.save_draft("BUG-T-2", "bug", "transition", None, "", None, {"to": "IN_PROGRESS"})
    res = sb.qaos_exec.execute("BUG-T-2")
    assert res["ok"] and fake_qaos["calls"][-1] == "bin/qaos bug index --new-request"
    assert "bugs/index.md 已重建" in res["hint"]


def test_hint_does_not_claim_index_rebuilt_when_the_rebuild_failed(real_sm, fake_qaos):
    sb = real_sm
    _bug(sb.root, "BUG-T-3", "OPEN")
    sb.tickets.save_draft("BUG-T-3", "bug", "transition", None, "", None, {"to": "IN_PROGRESS"})
    fake_qaos["side_effect"] = None
    orig = sb.qaos_exec._run

    def run(cmd):
        r = orig(cmd)
        return {**r, "exit_code": 2, "stderr": "index boom"} if cmd.startswith("bin/qaos bug index") else r
    sb.qaos_exec._run = run
    res = sb.qaos_exec.execute("BUG-T-3")
    assert "已重建" not in res["hint"] and "重建失敗" in res["hint"] and "index boom" in res["hint"]


def test_apply_request_is_rejected_with_409_and_nothing_runs(real_sm, fake_qaos):
    sb = real_sm
    _clr(sb.root, "CLR-T-6", "ANSWERED", answer="a", resolution="requirement_clarified")
    sb.tickets.save_draft("CLR-T-6", "clarification", "apply", None, "備註", None, None)
    with pytest.raises(sb.qaos_exec.ExecError) as ei:
        sb.qaos_exec.execute("CLR-T-6")
    assert ei.value.status == 409 and "指令尚未完整" in str(ei.value)
    assert fake_qaos["calls"] == []


# ------------------------------------------------------------ 狀態：INCORPORATED 與 kinds
def test_incorporated_is_an_active_non_terminal_status(real_sm):
    sb = real_sm
    for cid, st in (("CLR-A", "OPEN"), ("CLR-B", "INCORPORATED"), ("CLR-C", "APPLIED"), ("CLR-D", "WITHDRAWN"), ("CLR-E", "ANSWERED")):
        _clr(sb.root, cid, st)
    sb.tickets._cache.clear()
    assert [c["clarification_id"] for c in sb.tickets.clarifications(open_only=True)] == ["CLR-A", "CLR-E", "CLR-B"]    # 依狀態順序：OPEN, ANSWERED, INCORPORATED
    assert [c["clarification_id"] for c in sb.tickets.clarifications()][-2:] == ["CLR-C", "CLR-D"]                    # 終止狀態排最後


def test_incorporated_allows_apply_reanswer_and_withdraw(real_sm):
    assert real_sm.tickets._clr_allowed("INCORPORATED") == ["ANSWERED", "APPLIED", "WITHDRAWN"]


def test_kinds_filter_document_request_transitions(real_sm):
    t = real_sm.tickets
    assert t._clr_allowed("OPEN", "document_request") == ["APPLIED", "ASKED", "WITHDRAWN"]                  # 沒有 ANSWERED：文件索取單不能 answer
    assert t._clr_allowed("OPEN", "spec_question") == ["ANSWERED", "ASKED", "WITHDRAWN"]                    # 沒有 APPLIED：spec_question 不能從 OPEN 直接 apply
    assert t._clr_allowed("OPEN") == t._clr_allowed("OPEN", "spec_question")                                # 沒指定 kind 的舊單視為 spec_question


def test_legacy_clr_without_kind_defaults_to_spec_question(real_sm):
    _clr(real_sm.root, "CLR-OLD", "OPEN")
    real_sm.tickets._cache.clear()
    assert real_sm.tickets.clarifications()[0]["kind"] == "spec_question"


# ------------------------------------------------------------ PROJECT_ROOT 與 worktree 防護
def test_project_root_can_be_pointed_at_the_main_checkout(tmp_path):
    code = "from backend import config; print(config.PROJECT_ROOT); print(config.RUNS_DIR); print(config.WARROOM_DIR)"
    env = {"PATH": "/usr/bin:/bin", "QAOS_ADMIN_PROJECT_ROOT": str(tmp_path)}
    out = subprocess.run([sys.executable, "-c", code], cwd=ADMIN_DIR, env=env, capture_output=True, text=True, check=True).stdout.splitlines()
    assert out == [str(tmp_path.resolve()), str((tmp_path / "runs").resolve()), str((tmp_path / ".warroom").resolve())]


def test_project_root_defaults_to_the_checkout_above_admin_ui():
    code = "from backend import config; print(config.PROJECT_ROOT)"
    out = subprocess.run([sys.executable, "-c", code], cwd=ADMIN_DIR, env={"PATH": "/usr/bin:/bin"}, capture_output=True, text=True, check=True).stdout.strip()
    assert out == str(ADMIN_DIR.parent.resolve())


# ---- 寫入防護：用真的 git 結構驗證（Codex review：不能只看 .git 是不是檔案）
GIT_ENV = {"PATH": "/usr/bin:/bin:/opt/homebrew/bin:/usr/local/bin", "HOME": "/nonexistent", "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null"}


def _git(cwd, *args):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "protocol.file.allow=always", *args], cwd=cwd, env=GIT_ENV, check=True, capture_output=True)


def _repo_with_bin_qaos(path: pathlib.Path) -> pathlib.Path:
    """有一個 commit、含可執行 bin/qaos 的 git repo。"""
    path.mkdir(parents=True)
    _git(path, "init", "-q")
    (path / "bin").mkdir()
    (path / "bin" / "qaos").write_text("#!/bin/sh\n")
    (path / "bin" / "qaos").chmod(0o755)
    _git(path, "add", "-A")
    _git(path, "commit", "-q", "-m", "init")
    return path


@pytest.fixture
def exec_calls(sandbox, monkeypatch):
    """git 照常執行，bin/qaos 換成假的並記錄；回傳被執行的 bin/qaos 指令清單。"""
    real_run, calls = subprocess.run, []

    def run(args, **kw):
        if args and args[0] == "git":
            return real_run(args, **kw)
        calls.append(list(args))
        return subprocess.CompletedProcess(args, 0, "ok", "")
    monkeypatch.setattr(sandbox.qaos_exec.subprocess, "run", run)
    return calls


def _try(sandbox, monkeypatch, root: pathlib.Path):
    monkeypatch.setattr(sandbox.qaos_exec, "PROJECT_ROOT", root)
    return sandbox.qaos_exec._run("bin/qaos bug index --new-request")


def test_normal_checkout_is_allowed(sandbox, monkeypatch, exec_calls, tmp_path):
    root = _repo_with_bin_qaos(tmp_path / "main")
    assert _try(sandbox, monkeypatch, root)["exit_code"] == 0 and exec_calls == [["bin/qaos", "bug", "index", "--new-request"]]


def test_linked_worktree_is_refused_without_touching_bin_qaos(sandbox, monkeypatch, exec_calls, tmp_path):
    main = _repo_with_bin_qaos(tmp_path / "main")
    wt = tmp_path / "wt"
    _git(main, "worktree", "add", "-q", str(wt), "-b", "side")
    with pytest.raises(sandbox.qaos_exec.ExecError) as ei:
        _try(sandbox, monkeypatch, wt)
    assert ei.value.status == 409 and "worktree" in str(ei.value) and "QAOS_ADMIN_PROJECT_ROOT" in str(ei.value)
    assert exec_calls == []


def test_subdirectory_of_a_linked_worktree_is_refused_too(sandbox, monkeypatch, exec_calls, tmp_path):
    main = _repo_with_bin_qaos(tmp_path / "main")
    wt = tmp_path / "wt"
    _git(main, "worktree", "add", "-q", str(wt), "-b", "side")
    (wt / "sub" / "bin").mkdir(parents=True)
    (wt / "sub" / "bin" / "qaos").write_text("#!/bin/sh\n")
    with pytest.raises(sandbox.qaos_exec.ExecError) as ei:
        _try(sandbox, monkeypatch, wt / "sub")
    assert "worktree" in str(ei.value) and exec_calls == []


def test_separate_git_dir_main_checkout_is_allowed(sandbox, monkeypatch, exec_calls, tmp_path):
    """`git init --separate-git-dir` 的主 checkout，.git 是檔案但它就是主資料夾（Codex review P2）。"""
    root = tmp_path / "main"
    root.mkdir()
    _git(root, "init", "-q", f"--separate-git-dir={tmp_path / 'gitdir'}")
    assert (root / ".git").is_file()
    (root / "bin").mkdir()
    (root / "bin" / "qaos").write_text("#!/bin/sh\n")
    assert _try(sandbox, monkeypatch, root)["exit_code"] == 0 and len(exec_calls) == 1


def test_submodule_checkout_is_allowed(sandbox, monkeypatch, exec_calls, tmp_path):
    inner = _repo_with_bin_qaos(tmp_path / "inner")
    outer = _repo_with_bin_qaos(tmp_path / "outer")
    _git(outer, "submodule", "add", "-q", str(inner), "sub")
    assert (outer / "sub" / ".git").is_file()
    assert _try(sandbox, monkeypatch, outer / "sub")["exit_code"] == 0 and len(exec_calls) == 1


def test_missing_bin_qaos_is_a_clear_error_not_a_crash(sandbox, monkeypatch, exec_calls, tmp_path):
    root = tmp_path / "empty"
    root.mkdir()
    with pytest.raises(sandbox.qaos_exec.ExecError) as ei:
        _try(sandbox, monkeypatch, root)
    assert ei.value.status == 409 and "bin/qaos" in str(ei.value) and exec_calls == []


def test_plain_directory_without_git_is_allowed_when_bin_qaos_exists(sandbox, monkeypatch, exec_calls, tmp_path):
    root = tmp_path / "plain"
    (root / "bin").mkdir(parents=True)
    (root / "bin" / "qaos").write_text("#!/bin/sh\n")
    assert _try(sandbox, monkeypatch, root)["exit_code"] == 0


def test_git_failure_on_a_git_checkout_fails_closed(sandbox, monkeypatch, tmp_path):
    root = tmp_path / "main"
    (root / ".git").mkdir(parents=True)
    (root / "bin").mkdir()
    (root / "bin" / "qaos").write_text("#!/bin/sh\n")

    def boom(args, **kw):
        raise OSError("git not found")
    monkeypatch.setattr(sandbox.qaos_exec.subprocess, "run", boom)
    with pytest.raises(sandbox.qaos_exec.ExecError) as ei:
        _try(sandbox, monkeypatch, root)
    assert ei.value.status == 409 and "無法確認" in str(ei.value)


def test_only_bin_qaos_can_be_executed(sandbox):
    with pytest.raises(sandbox.qaos_exec.ExecError) as ei:
        sandbox.qaos_exec._run("rm -rf /")
    assert ei.value.status == 400


def test_bug_filing_reports_the_worktree_refusal_as_a_bugfile_error(sandbox, monkeypatch, exec_calls, tmp_path):
    from backend.services import qaos_bug
    main = _repo_with_bin_qaos(tmp_path / "main")
    wt = tmp_path / "wt"
    _git(main, "worktree", "add", "-q", str(wt), "-b", "side")
    monkeypatch.setattr(sandbox.qaos_exec, "PROJECT_ROOT", wt)
    with pytest.raises(qaos_bug.BugFileError) as ei:
        qaos_bug._run_or_raise("bin/qaos evidence add --type log --inline x --by me", "登記證據", [])
    assert ei.value.status == 409 and "worktree" in str(ei.value) and exec_calls == []


# ------------------------------------------------------------ 答案重送（Codex review P2）
def _answer_effect(sb, clr_path: pathlib.Path):
    """假 CLI 的副作用：把 CLR 寫成 ANSWERED，並記下這次的回答（同真正的 answer 指令）。"""
    def effect(cmd: str):
        if " clarification answer " in f" {cmd} ":
            import shlex
            a = shlex.split(cmd)
            get = lambda flag: a[a.index(flag) + 1]
            d = yaml.safe_load(clr_path.read_text(encoding="utf-8"))
            d.update({"status": "ANSWERED", "answer": get("--answer"), "answered_by": get("--answered-by"), "resolution": get("--resolution")})
            clr_path.write_text(yaml.safe_dump(d, allow_unicode=True), encoding="utf-8")
    return effect


def _answer_draft(sb, cid: str, text: str, by: str = "PM", resolution: str = "requirement_clarified"):
    return sb.tickets.save_draft(cid, "clarification", "answer", None, text, None, {"answered_by": by, "resolution": resolution})


def test_resending_the_same_answer_is_refused_and_does_not_add_a_revision(real_sm, fake_qaos):
    sb = real_sm
    p = _clr(sb.root, "CLR-R-1", "OPEN")
    fake_qaos["side_effect"] = _answer_effect(sb, p)
    _answer_draft(sb, "CLR-R-1", "答案 A")
    assert sb.qaos_exec.execute("CLR-R-1")["ok"]
    n = len(fake_qaos["calls"])
    for _ in range(2):                                   # 第一次回應遺失後重試、舊草稿再按一次
        with pytest.raises(sb.qaos_exec.ExecError) as ei:
            sb.qaos_exec.execute("CLR-R-1")
        assert ei.value.status == 409 and "已經登記過這個回答" in str(ei.value)
    assert len(fake_qaos["calls"]) == n                  # CLI 完全沒被呼叫


def test_a_changed_answer_or_resolution_is_a_new_revision_and_is_allowed(real_sm, fake_qaos):
    sb = real_sm
    p = _clr(sb.root, "CLR-R-2", "OPEN")
    fake_qaos["side_effect"] = _answer_effect(sb, p)
    _answer_draft(sb, "CLR-R-2", "答案 A")
    sb.qaos_exec.execute("CLR-R-2")
    _answer_draft(sb, "CLR-R-2", "答案 B（修訂）")
    assert sb.qaos_exec.execute("CLR-R-2")["ok"]
    _answer_draft(sb, "CLR-R-2", "答案 B（修訂）", resolution="no_change")      # 只改落地方式也算新修訂
    assert sb.qaos_exec.execute("CLR-R-2")["ok"]
    assert sum(1 for c in fake_qaos["calls"] if " clarification answer " in f" {c} ") == 3


def test_resending_an_old_answer_does_not_roll_an_incorporated_clr_back(real_sm, fake_qaos):
    """已被 revision 納入（INCORPORATED）後，原樣重送舊回答會 INCORPORATED→ANSWERED 要求重新納入——必須擋下；內容不同才是合法的 A5。"""
    sb = real_sm
    p = _clr(sb.root, "CLR-R-3", "INCORPORATED", answer="答案 A", answered_by="PM", resolution="requirement_clarified")
    _answer_draft(sb, "CLR-R-3", "答案 A")
    with pytest.raises(sb.qaos_exec.ExecError) as ei:
        sb.qaos_exec.execute("CLR-R-3")
    assert ei.value.status == 409 and fake_qaos["calls"] == []
    fake_qaos["side_effect"] = _answer_effect(sb, p)
    _answer_draft(sb, "CLR-R-3", "答案 C（PM 改口）")
    assert sb.qaos_exec.execute("CLR-R-3")["ok"]


def test_first_answer_on_an_open_clr_is_never_treated_as_a_duplicate(real_sm, fake_qaos):
    sb = real_sm
    _clr(sb.root, "CLR-R-4", "OPEN", answer="", answered_by=None, resolution=None)
    _answer_draft(sb, "CLR-R-4", "")
    # 空回答在指令組裝階段就會被 warning 擋下，不是重複判斷的範圍
    with pytest.raises(sb.qaos_exec.ExecError) as ei:
        sb.qaos_exec.execute("CLR-R-4")
    assert "指令尚未完整" in str(ei.value)
