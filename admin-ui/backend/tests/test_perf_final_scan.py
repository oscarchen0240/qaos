"""指揮台產出頁／導覽列／pipeline 變慢的修正（registry 簽章每檔重算、pipeline 每個 session 重掃 final、_ts 重複 strptime）。

資料量長大後（registry 上千個 TC、final 上千個檔、數十個 session），`/api/outputs` 要十幾秒、`/api/nav` 超過兩分鐘，頁面轉不出來。
這裡鎖定三個結構性原因（呼叫次數，而不是賭執行時間），並確認行為沒變。
"""
import json

import pytest

from backend.services import registry as registry_mod
from backend.services import runs as runs_mod


def _final(root, name, cases):
    d = root / "testcases" / "final"
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(json.dumps(cases, ensure_ascii=False), encoding="utf-8")


def _case(i, area="AREA"):
    return {"testcase_id": f"TC-{area}-{i:03d}", "version": 1, "spec_id": f"SPEC-{area}-001", "spec_version": "0.1", "title": "t"}


# ---------------------------------------------------------------- registry.signature
def test_signature_counts_only_tc_yaml_and_reports_the_newest_mtime(full_sandbox):
    import os
    reg = full_sandbox.root / "testcases" / "registry"
    for i, mt in ((1, 1000.0), (2, 3000.0), (3, 2000.0)):
        p = reg / f"TC-A-{i:03d}.yaml"
        p.write_text("x: 1", encoding="utf-8")
        os.utime(p, (mt, mt))
    (reg / "index.yaml").write_text("x: 1", encoding="utf-8")                  # 不是 TC-*.yaml，不算
    (reg / "TC-A-004.md").write_text("x", encoding="utf-8")
    assert registry_mod.signature() == (3, 3000.0)


def test_signature_of_an_empty_or_missing_registry(full_sandbox, monkeypatch, tmp_path):
    assert registry_mod.signature() == (0, 0)
    monkeypatch.setattr(registry_mod, "REG_DIR", tmp_path / "nope")
    assert registry_mod.signature() == ()


# ---------------------------------------------------------------- scan_files 只算一次簽章
def test_scan_files_computes_the_registry_signature_once_per_scan(full_sandbox, monkeypatch):
    for i in range(8):
        _final(full_sandbox.root, f"A{i}-final-active.json", [_case(1, f"A{i}")])
    calls = []
    real = registry_mod.signature
    monkeypatch.setattr(registry_mod, "signature", lambda: (calls.append(1), real())[1])
    items = full_sandbox.outputs.scan_files()
    assert len(items) == 8
    assert len(calls) == 1                           # 舊版：每個檔案各算一次（8 次），每次都掃整個 registry


def test_meta_cache_is_invalidated_only_when_the_registry_signature_changes(full_sandbox, monkeypatch):
    o = full_sandbox.outputs
    _final(full_sandbox.root, "A-final-active.json", [_case(1)])
    p = full_sandbox.root / "testcases" / "final" / "A-final-active.json"
    parsed = []
    real = o._parse_json
    monkeypatch.setattr(o, "_parse_json", lambda path: (parsed.append(1), real(path))[1])
    st = p.stat()
    o._meta(p, st, (5, 100.0)); o._meta(p, st, (5, 100.0))
    assert len(parsed) == 1                          # 簽章沒變：用快取
    o._meta(p, st, (6, 200.0))
    assert len(parsed) == 2                          # registry 有變：重新解析（drift 要重算）


def test_scan_files_still_reports_drift_after_the_registry_changes(full_sandbox):
    """行為不變：registry 新增 TC 後，final 的 drift 要重新計算。"""
    wr = full_sandbox.root
    reg = wr / "testcases" / "registry"
    ver = wr / "testcases" / "versions"
    import yaml

    def add_tc(i):
        tc = f"TC-AREA-{i:03d}"
        (reg / f"{tc}.yaml").write_text(yaml.safe_dump({"testcase_id": tc, "active_version": 1, "status": "ACTIVE"}), encoding="utf-8")
        (ver / tc).mkdir(parents=True, exist_ok=True)
        (ver / tc / "v1.yaml").write_text(yaml.safe_dump({"testcase_id": tc, "version": 1, "spec_id": "SPEC-AREA-001", "spec_version": "0.1"}), encoding="utf-8")
    add_tc(1)
    _final(wr, "AREA-final-active.json", [_case(1)])
    first = full_sandbox.outputs.scan_files()[0]["meta"]["drift"]
    assert first["stale"] is False
    add_tc(2)                                        # registry 多一條 ACTIVE：final 沒有它
    second = full_sandbox.outputs.scan_files()[0]["meta"]["drift"]
    assert second["stale"] is True and second["added"] == ["TC-AREA-002"]


# ---------------------------------------------------------------- pipeline 不再為每個 session 解析整個 final
def test_list_files_matches_scan_files_fields_without_parsing_or_touching_the_tracking_table(full_sandbox, monkeypatch):
    o = full_sandbox.outputs
    _final(full_sandbox.root, "AREA-final-active.json", [_case(1)])
    (full_sandbox.root / "testcases" / "final" / "AREA-final.html").write_text("<title>t</title>", encoding="utf-8")
    (full_sandbox.root / "testcases" / "final" / ".hidden.json").write_text("[]", encoding="utf-8")
    real_json, real_html = o._parse_json, o._parse_html
    monkeypatch.setattr(o, "_parse_json", lambda p: pytest.fail("list_files 不應解析內容"))
    monkeypatch.setattr(o, "_parse_html", lambda p: pytest.fail("list_files 不應解析內容"))
    with full_sandbox.db.connect() as con:
        before = con.execute("SELECT COUNT(*) FROM output_files").fetchone()[0]
    light = o.list_files()
    with full_sandbox.db.connect() as con:
        assert con.execute("SELECT COUNT(*) FROM output_files").fetchone()[0] == before == 0
    monkeypatch.setattr(o, "_parse_json", real_json)
    monkeypatch.setattr(o, "_parse_html", real_html)
    full = o.scan_files()
    keys = ("path", "name", "group_key", "area", "kind", "size", "mtime", "modified_at")
    assert [{k: f[k] for k in keys} for f in light] == [{k: f[k] for k in keys} for f in full]
    assert all(not f["name"].startswith(".") for f in light)


def test_pipeline_final_files_uses_the_light_listing(full_sandbox, monkeypatch):
    from backend.services import pipeline
    _final(full_sandbox.root, "AREA-final-active.json", [_case(1)])
    _final(full_sandbox.root, "OTHER-final-active.json", [_case(1, "OTHER")])
    monkeypatch.setattr(full_sandbox.outputs, "scan_files", lambda: pytest.fail("pipeline 不該用會解析內容的 scan_files"))
    run = {"run_id": "RUN-X", "inputs": {"spec_id": "SPEC-AREA-001"}}
    monkeypatch.setattr(pipeline, "_area_of", lambda r: "AREA")
    out = pipeline._final_files(run, {"final_writes": []})
    assert out["area"] == "AREA" and [f["name"] for f in out["files"]] == ["AREA-final-active.json"]
    assert set(out["files"][0]) == {"name", "path", "group_key", "kind", "modified_at", "mtime"}     # 呼叫端用到的欄位不變


# ---------------------------------------------------------------- runs._ts
def test_ts_is_memoized_and_behaves_as_before():
    runs_mod._ts_cached.cache_clear()
    assert runs_mod._ts("2026-10-13T00:00:00Z") == 1791849600.0
    assert runs_mod._ts("2026-10-13T00:00:00Z") == 1791849600.0
    assert runs_mod._ts_cached.cache_info().hits >= 1
    assert runs_mod._ts(None) == 0.0 and runs_mod._ts("") == 0.0 and runs_mod._ts("not a time") == 0.0


@pytest.mark.parametrize("bad", [["2026-10-13T00:00:00Z"], {"at": 1}, [[]]])
def test_ts_keeps_tolerating_malformed_yaml_values_that_are_not_hashable(bad):
    """run.yaml 的 at 若被寫成 list／dict，舊版（沒有快取）當成 0；lru_cache 會對不可 hash 的輸入丟 TypeError，要接住。"""
    assert runs_mod._ts(bad) == 0.0


def test_signature_with_only_negative_mtimes_matches_the_old_definition(full_sandbox):
    import os
    reg = full_sandbox.root / "testcases" / "registry"
    for i, mt in ((1, -500.0), (2, -100.0)):
        p = reg / f"TC-A-{i:03d}.yaml"
        p.write_text("x: 1", encoding="utf-8")
        os.utime(p, (mt, mt))
    old = (len(list(reg.glob("TC-*.yaml"))), max((p.stat().st_mtime for p in reg.glob("TC-*.yaml")), default=0))
    assert registry_mod.signature() == old == (2, -100.0)
