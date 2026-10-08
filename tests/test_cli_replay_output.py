"""CLI 對「同一請求重送且已完成」的回報（需求 A §3.2：回報已完成、不做任何寫入）。

- `qaos id`：舊 ID 不印到 stdout（避免被當成新 ID 使用），以非零結束並說明要加 --new-request。
- `qaos run new`：stdout 顯示 run 目前的狀態，不是建立當時存下的結果。"""
import pytest
from tools.qaos import cli, engine, store

BY = "oscar@example.com"

def test_id_replay_does_not_print_old_id(capsys):
    cli.main(["id", "ART-TVR", "--new-request"])
    first = capsys.readouterr().out.strip()
    assert first.startswith("ART-TVR-")
    # 不帶 --new-request 的同一請求（第一次就是不帶 token 的請求）
    cli.main(["id", "ART-TCD"]); base = capsys.readouterr().out.strip()
    assert base.startswith("ART-TCD-")
    with pytest.raises(SystemExit) as e:
        cli.main(["id", "ART-TCD"])
    out = capsys.readouterr()
    assert e.value.code != 0
    assert out.out == ""                                   # stdout 不出現舊 ID
    assert base in str(e.value.code) and "--new-request" in str(e.value.code)
    assert "先前已完成" not in out.err                     # 不重複印出通用提示
    cli.main(["id", "ART-TCD", "--new-request"])
    again = capsys.readouterr().out.strip()
    assert again.startswith("ART-TCD-") and again != base

def test_id_replay_counter_not_advanced(capsys):
    cli.main(["id", "REQ", "--area", "REPLAYX"]); first = capsys.readouterr().out.strip()
    counters = store.load("testcases/registry/_counters.yaml")["counters"]["REQ-REPLAYX"]
    with pytest.raises(SystemExit):
        cli.main(["id", "REQ", "--area", "REPLAYX"])
    assert store.load("testcases/registry/_counters.yaml")["counters"]["REQ-REPLAYX"] == counters
    assert first == "REQ-REPLAYX-001"

def test_run_new_replay_shows_current_status(capsys):
    args = ["run", "new", "regression-generation", "--input", 'target_suites=["smoke"]', "--input", "scope=all", "--input", "trigger=manual", "--by", BY]
    cli.main(args); first = capsys.readouterr().out.split()
    run_id = first[0]
    assert first[1] == "RUNNING"
    engine.cancel(run_id, BY)
    cli.main(args); out = capsys.readouterr()
    line = out.out.split()
    assert line[0] == run_id and line[1] == "CANCELLED"     # 目前狀態，不是建立時的 RUNNING
    assert "先前已完成" in out.err
