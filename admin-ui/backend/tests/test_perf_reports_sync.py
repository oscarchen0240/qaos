"""第二批效能修正（/api/reports 與 /api/nav 在資料量大時仍要數秒到數十秒）：
- specflow 簽章在同一次 sync_outputs 內被重算上百次（每次 stat 全部 run 檔）
- /api/reports 一次請求呼叫 list_all() 五次，每次都跑一遍 sync_outputs
- outputs.list_files 每個檔案做四次 realpath，pipeline 每個 session 都重做一遍
鎖定的是呼叫次數／結構，不是執行時間；行為（回傳內容）不變。
"""
import json
import os
import threading

import pytest

from backend.services import runs as runs_mod
from backend.services import specflow as sf


def _final(root, name, cases):
    d = root / "testcases" / "final"
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(json.dumps(cases, ensure_ascii=False), encoding="utf-8")


def _case(i, area):
    return {"testcase_id": f"TC-{area}-{i:03d}", "version": 1, "spec_id": f"SPEC-{area}-001", "spec_version": "0.1", "title": "t"}


# ---------------------------------------------------------------- specflow.frozen_signature
def test_frozen_signature_computes_once_for_many_builds(full_sandbox, monkeypatch):
    calls = []
    real = runs_mod.signature
    monkeypatch.setattr(runs_mod, "signature", lambda: (calls.append(1), real())[1])
    with sf.frozen_signature():
        for _ in range(20):
            sf.run_phase("RUN-X")
    assert len(calls) == 1                           # 舊版：20 次
    calls.clear()
    sf.run_phase("RUN-X"); sf.run_phase("RUN-X")
    assert len(calls) == 2                           # 離開區塊後恢復每次重算（檔案變動馬上看得到）


def test_frozen_signature_is_released_even_when_the_block_raises_and_nesting_keeps_the_outer_pin(full_sandbox, monkeypatch):
    calls = []
    real = runs_mod.signature
    monkeypatch.setattr(runs_mod, "signature", lambda: (calls.append(1), real())[1])
    with pytest.raises(RuntimeError):
        with sf.frozen_signature():
            raise RuntimeError("boom")
    calls.clear()                                    # 進入區塊時算的那一次不算
    sf.run_phase("RUN-X"); sf.run_phase("RUN-X")
    assert len(calls) == 2                           # 例外離開區塊後也解除釘住
    calls.clear()
    with sf.frozen_signature():
        with sf.frozen_signature():
            sf.run_phase("RUN-X")
        sf.run_phase("RUN-X")
    assert len(calls) == 1                           # 巢狀不重新計算，內層結束也不放掉外層


def test_frozen_signature_only_applies_to_the_current_thread(full_sandbox, monkeypatch):
    seen = {}
    with sf.frozen_signature():
        pinned = sf._signature()
        t = threading.Thread(target=lambda: seen.update(other=sf._signature()))
        t.start(); t.join()
        # 另一個執行緒沒有被釘住：自己算（內容相同，但不是同一個被釘住的物件路徑）
        monkeypatch.setattr(runs_mod, "signature", lambda: ("changed",))
        t2 = threading.Thread(target=lambda: seen.update(fresh=sf._signature()))
        t2.start(); t2.join()
        assert sf._signature() is pinned
    assert seen["fresh"][0] == ("changed",)


# ---------------------------------------------------------------- sync_outputs 的簽章次數
def test_sync_outputs_computes_the_run_signature_once_regardless_of_group_count(full_sandbox, write_run, monkeypatch):
    for i in range(6):
        _final(full_sandbox.root, f"A{i}-final-active.json", [_case(1, f"A{i}")])
        write_run(f"RUN-2026101{i}-001", "COMPLETED", None, [("T0", "DONE", None)], spec_id=f"SPEC-A{i}-001", workflow_id="spec-to-testcase")
    calls = []
    real = runs_mod.signature
    monkeypatch.setattr(runs_mod, "signature", lambda: (calls.append(1), real())[1])
    full_sandbox.autoreports.sync_outputs()
    assert len(calls) == 1                           # 舊版：每個群組、每個 run_phase 呼叫各一次（上百次）


# ---------------------------------------------------------------- /api/reports 只呼叫一次 list_all
def test_reports_list_calls_list_all_once_and_returns_the_same_counts(full_sandbox, monkeypatch):
    from backend.routers import reports as router
    from backend.services import reports as svc
    rows = [{"id": i, "title": f"t{i}", "summary": "", "kind": k, "source_key": None, "auto_generated_at": None, "created_at": "c", "updated_at": f"2026-10-0{i}", "output_paths": []}
            for i, k in enumerate(("output", "output", "manual", "automation"), start=1)]
    calls = []
    monkeypatch.setattr(svc, "list_all", lambda: (calls.append(1), [dict(r) for r in rows])[1])
    out = router.list_reports()
    assert len(calls) == 1                           # 舊版：5 次（每次都 sync_outputs）
    assert out["counts"] == {"all": 4, "output": 2, "automation": 1, "manual": 1} and out["total"] == 4
    assert [r["id"] for r in out["items"]] == [4, 3, 2, 1]
    assert router.list_reports(kind="output")["total"] == 2 and router.list_reports(q="t3")["total"] == 1


# ---------------------------------------------------------------- runs.signature
def test_runs_signature_matches_the_old_definition(full_sandbox):
    rd = full_sandbox.root / "runs"
    for name, has_yaml, mt in (("RUN-20261001-001", True, 1000.0), ("RUN-20261001-002", False, 0), ("RUN-20261002-001", True, 3000.0), ("_audit.d", True, 5.0), ("misc", True, 6.0)):
        d = rd / name
        d.mkdir(parents=True, exist_ok=True)
        if has_yaml:
            (d / "run.yaml").write_text("x: 1", encoding="utf-8")
            os.utime(d / "run.yaml", (mt, mt))
    (rd / "RUN-20261003-001").write_text("a file, not a dir", encoding="utf-8")
    old = tuple((p.name, (p / "run.yaml").stat().st_mtime) for p in sorted(rd.glob("RUN-*")) if (p / "run.yaml").exists())
    assert runs_mod.signature() == old == (("RUN-20261001-001", 1000.0), ("RUN-20261002-001", 3000.0))


def test_runs_signature_of_a_missing_directory(full_sandbox, monkeypatch, tmp_path):
    monkeypatch.setattr(runs_mod, "RUNS_DIR", tmp_path / "nope")
    assert runs_mod.signature() == ()


# ---------------------------------------------------------------- outputs.list_files 記憶化
def test_list_files_reuses_the_result_until_a_file_changes(full_sandbox, monkeypatch):
    o = full_sandbox.outputs
    _final(full_sandbox.root, "A-final-active.json", [_case(1, "A")])
    first = o.list_files()
    calls = []
    real = o.rel_of
    monkeypatch.setattr(o, "rel_of", lambda p: (calls.append(1), real(p))[1])
    assert o.list_files() == first and calls == []                    # 沒變：不重做 resolve
    _final(full_sandbox.root, "B-final-active.json", [_case(1, "B")])    # 新增檔案
    assert [f["name"] for f in o.list_files()] == ["A-final-active.json", "B-final-active.json"] and calls
    calls.clear()
    p = full_sandbox.root / "testcases" / "final" / "A-final-active.json"
    st = p.stat()
    os.utime(p, ns=(st.st_atime_ns, st.st_mtime_ns + 5_000_000_000))      # 內容被重新產生（mtime 變）
    changed = o.list_files()
    assert calls and changed[0]["mtime"] != first[0]["mtime"]


def test_list_files_returns_copies_so_callers_cannot_corrupt_the_cache(full_sandbox):
    o = full_sandbox.outputs
    _final(full_sandbox.root, "A-final-active.json", [_case(1, "A")])
    a = o.list_files()
    a[0]["name"] = "MUTATED"; a.append({"x": 1})
    b = o.list_files()
    assert [f["name"] for f in b] == ["A-final-active.json"]


# ================================================================ 第 01 輪審查（list_files 快取的路徑解析依賴）
def test_list_files_notices_a_symlink_repointed_to_a_file_with_identical_metadata(full_sandbox):
    o = full_sandbox.outputs
    d = o.FINAL_DIR
    d.mkdir(parents=True, exist_ok=True)
    for name, text in ((".a", "aa"), (".b", "bb")):                     # 隱藏檔不會自己進清單；大小與 mtime 完全相同
        (d / name).write_text(text)
        os.utime(d / name, ns=(1_000_000_000_000, 1_000_000_000_000))
    link = d / "A-final-active.json"
    link.symlink_to(d / ".a")
    assert o.list_files()[0]["path"] == o.rel_of(link) == "testcases/final/.a"
    link.unlink()
    link.symlink_to(d / ".b")
    assert o.list_files()[0]["path"] == o.rel_of(link) == "testcases/final/.b"      # 舊（第一版快取）：永遠是 .a


def test_list_files_notices_the_final_directory_itself_being_repointed(full_sandbox, monkeypatch):
    o = full_sandbox.outputs
    base = full_sandbox.root / "testcases"
    for d in ("finalA", "finalB"):
        (base / d).mkdir(parents=True, exist_ok=True)
        (base / d / "A-final-active.json").write_text("[]")
        os.utime(base / d / "A-final-active.json", ns=(1_000_000_000_000, 1_000_000_000_000))
    link = base / "final_link"
    link.symlink_to(base / "finalA")
    monkeypatch.setattr(o, "FINAL_DIR", link)
    assert o.list_files()[0]["path"] == "testcases/finalA/A-final-active.json"
    link.unlink()
    link.symlink_to(base / "finalB")
    assert o.list_files()[0]["path"] == "testcases/finalB/A-final-active.json"


def test_list_files_hit_returns_the_items_it_just_validated_even_if_the_global_is_swapped_meanwhile(full_sandbox, monkeypatch):
    """比較指紋之後、取值之前，另一個執行緒換掉全域快取：命中時要回傳剛驗證過的那份，不是被換進來的別人的。"""
    o = full_sandbox.outputs
    _final(full_sandbox.root, "A-final-active.json", [_case(1, "A")])
    o.list_files()
    fp, items = o._list_cache
    other = (("other-dir", "x", ()), [{"name": "SWAPPED"}])

    class SwapOnCompare:
        def __eq__(self, rhs):
            monkeypatch.setattr(o, "_list_cache", other)               # 比較的當下，別的執行緒換了全域
            return fp == rhs
    monkeypatch.setattr(o, "_list_cache", (SwapOnCompare(), items))
    assert [f["name"] for f in o.list_files()] == ["A-final-active.json"]


def test_a_project_root_symlink_loop_still_raises_on_a_hot_cache(full_sandbox, monkeypatch):
    """FINAL_DIR 在專案外、PROJECT_ROOT 預熱後被改成指向自身的符號連結：原本 rel_of 的 resolve 會丟 RuntimeError，熱快取不能略過它。"""
    o = full_sandbox.outputs
    root = full_sandbox.root
    project = root / "project"
    project.mkdir()
    final = root / "external" / "final"
    final.mkdir(parents=True)
    p = final / "notes.json"
    p.write_text("[]")
    monkeypatch.setattr(o, "PROJECT_ROOT", project)
    monkeypatch.setattr(o, "FINAL_DIR", final)
    o.list_files()                                                  # 預熱
    project.rename(root / "project_saved")
    project.symlink_to("project")                                   # 指向自己的循環連結
    with pytest.raises(RuntimeError, match="Symlink loop"):
        o.rel_of(p)
    with pytest.raises(RuntimeError, match="Symlink loop"):
        o.list_files()                                              # 舊（realpath 指紋）：直接回傳快取
