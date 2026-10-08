"""CLI 對「同一請求重送且已完成」的回報（需求 A §3.2：回報已完成、不做任何寫入）。

- `qaos id`：舊 ID 不印到 stdout（避免被當成新 ID 使用），以非零結束並說明要加 --new-request。
- `qaos run new`、`tc revise`、`bug resolve|verify|close`：重送時顯示實體目前的狀態，不是當時存下的結果。
- `qaos gate`、`tc-final`：重送時明示輸出的是先前的結果。

前段以子程序、每案一份獨立 root 執行（才能比對整個 root 的前後內容與真正的 stderr）；
後段以 monkeypatch 驗證各指令的輸出格式。"""
import hashlib, pathlib
import pytest
from tests import p1_util as U
from tools.qaos import cli, engine, operation, bug_lifecycle, tc_ops, final_export

BY = "oscar@example.com"
RUN_ARGS = ["run", "new", "regression-generation", "--input", 'target_suites=["smoke"]', "--input", "scope=all", "--input", "trigger=manual", "--by", BY]

def snapshot(root) -> dict:
    """root 下全部檔案的內容 hash；排除 locks/（executor 依 §4.3 會覆寫 owner 診斷檔）。"""
    root = pathlib.Path(root)
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file() and p.relative_to(root).parts[0] != "locks"}

# ---------------------------------------------------------------- 子程序：id
def test_id_replay_no_write_no_stdout():
    root = U.mkroot()
    first = U.q(root, "id", "REQ", "--area", "REPLAYX", check=True).stdout.strip()
    assert first == "REQ-REPLAYX-001"
    before = snapshot(root)
    r = U.q(root, "id", "REQ", "--area", "REPLAYX")
    assert r.returncode != 0 and r.stdout == ""                       # 舊 ID 不出現在 stdout
    err = [l for l in r.stderr.splitlines() if l.strip()]
    assert len(err) == 1 and first in err[0] and "--new-request" in err[0]   # 只有一行說明，不重複印通用提示
    assert snapshot(root) == before                                    # 計數器、operations、audit 都沒有寫入
    again = U.q(root, "id", "REQ", "--area", "REPLAYX", "--new-request", check=True).stdout.strip()
    assert again == "REQ-REPLAYX-002"

def test_id_resumed_still_prints_planned_id():
    root = U.mkroot()
    crashed = U.q(root, "id", "ART-TVR", fault="before_completed")
    assert crashed.returncode == 86
    resumed = U.q(root, "id", "ART-TVR", check=True)                   # 未完成的計畫：續做，照常印出計畫固定的 ID
    planned = resumed.stdout.strip()
    assert planned.startswith("ART-TVR-") and "已續做" in resumed.stderr
    done = U.q(root, "id", "ART-TVR")                                  # 完成後再重送：不印 ID
    assert done.returncode != 0 and done.stdout == "" and planned in done.stderr

# ---------------------------------------------------------------- 子程序：run new
def test_run_new_replay_shows_current_status_without_write():
    root = U.mkroot()
    first = U.q(root, *RUN_ARGS, check=True).stdout.split()
    run_id = first[0]
    assert first[1] == "RUNNING"
    U.q(root, "run", "cancel", run_id, "--by", BY, check=True)
    before = snapshot(root)
    r = U.q(root, *RUN_ARGS, check=True)                               # exit 0（admin-ui 依 exit code 與第一欄的 run_id）
    line = r.stdout.split()
    assert line[0] == run_id and line[1] == "CANCELLED"                 # 目前狀態，不是建立時的 RUNNING
    assert "先前已完成" in r.stderr
    assert snapshot(root) == before                                    # 沒有新 run、計數器沒有前進

def test_run_new_replay_missing_run_fails_without_stale_output():
    root = U.mkroot()
    run_id = U.q(root, *RUN_ARGS, check=True).stdout.split()[0]
    (root / "runs" / run_id / "run.yaml").unlink()
    r = U.q(root, *RUN_ARGS)
    assert r.returncode != 0 and r.stdout == ""                        # 不回退成過時的 RUNNING，也不補建 run
    assert not (root / "runs" / run_id / "run.yaml").exists()

# ---------------------------------------------------------------- 輸出格式（monkeypatch）
def _completed(monkeypatch, func_owner, name, result):
    def fake(*a, **k):
        operation.LAST_OUTCOME.clear(); operation.LAST_OUTCOME.update(kind="completed", op_id="f" * 64); return result
    monkeypatch.setattr(func_owner, name, fake)

def test_gate_replay_marks_previous_result(monkeypatch, capsys):
    _completed(monkeypatch, engine, "evaluate_gate", {"gate": "G-TVAL", "layer": "semantic", "result": "PASS", "issues": []})
    monkeypatch.setattr(engine, "load_run", lambda rid: {"status": "WAITING_HUMAN", "current_task_id": "T4", "waiting_on_approval_id": "APR-9"})
    cli.main(["gate", "RUN-X", "T3"])
    out = capsys.readouterr().out.splitlines()
    assert out[0] == "先前結果（未重新評估）：G-TVAL semantic PASS"
    assert out[1] == "run=WAITING_HUMAN current_task=T4 waiting=APR-9"

def test_tc_final_replay_marks_previous_export(monkeypatch, capsys):
    _completed(monkeypatch, final_export, "export", (3, 2))
    cli.main(["tc-final", "AREAX"])
    assert capsys.readouterr().out.startswith("先前已匯出（未重新匯出；ACTIVE 有變動時請加 --new-request）：testcases/final/AREAX-final.html")

def test_tc_revise_replay_shows_current_run(monkeypatch, capsys):
    _completed(monkeypatch, tc_ops, "revise", {"run_id": "RUN-X", "current_task_id": "T1"})
    monkeypatch.setattr(engine, "load_run", lambda rid: {"run_id": rid, "status": "COMPLETED", "current_task_id": "T5"})
    cli.main(["tc", "revise", "TC-X-001", "--reason", "r", "--by", BY])
    assert capsys.readouterr().out.strip() == "RUN-X testcase-revision 先前已建立，目前 COMPLETED current_task=T5"

@pytest.mark.parametrize("args,fn", [
    (["bug", "resolve", "BUG-X-001", "--external-ref", "JIRA-1", "--by", BY], "resolve"),
    (["bug", "verify", "BUG-X-001", "--execution", "EXE-1", "--by", BY], "verify"),
    (["bug", "close", "BUG-X-001", "--by", BY], "close"),
])
def test_bug_lifecycle_replay_shows_current_status(monkeypatch, capsys, args, fn):
    _completed(monkeypatch, bug_lifecycle, fn, {"status": "RESOLVED"})
    monkeypatch.setattr(bug_lifecycle, "_load", lambda bid: ({"status": "CLOSED"}, None))
    cli.main(args)
    assert capsys.readouterr().out.strip() == "BUG-X-001 先前已處理，目前狀態 CLOSED"
