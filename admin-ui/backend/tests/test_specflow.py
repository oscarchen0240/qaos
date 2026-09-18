"""A6 稽核 Top 12：specflow.build（Phase 2/3 判定、DoD 三項、新 run 在跑時整合退回 pending）。"""


def _spec(full_sandbox, key: str) -> dict:
    data = full_sandbox.specflow.build()
    return next(s for s in data["specs"] if s["key"] == key)


def test_two_completed_runs_are_phase2_then_phase3(full_sandbox, write_run):
    """同 spec 兩個 COMPLETED run，較早的是 Phase 2、較晚的是 Phase 3（沒有 shadow 文件時的預設判定）。"""
    write_run("RUN-20260913-001", "COMPLETED", "T5", [("T5", "DONE", None)], spec_id="SPEC-AREA-001")
    import time
    full_sandbox.root  # noop, keep created_at ordering explicit below
    write_run("RUN-20260915-001", "COMPLETED", "T5", [("T5", "DONE", None)], spec_id="SPEC-AREA-001")
    # write_run 夾具兩筆的 created_at 相同（固定字串），改用檔案 mtime 排序不可靠；直接調整其中一筆的 created_at
    import yaml
    p = full_sandbox.root / "runs" / "RUN-20260915-001" / "run.yaml"
    doc = yaml.safe_load(p.read_text())
    doc["created_at"] = "2026-09-15T00:00:00Z"
    p.write_text(yaml.safe_dump(doc, allow_unicode=True))
    data = full_sandbox.specflow.build()
    assert data["run_phase"]["RUN-20260913-001"] == "phase2"
    assert data["run_phase"]["RUN-20260915-001"] == "phase3"


def test_shadow_doc_pins_phase3_run_even_if_not_latest(full_sandbox, write_run, write_shadow_doc):
    """shadow 文件明確點名某個 run → 那個是 Phase 3，即使不是最新的 COMPLETED run（例如後面又跑了修訂）。"""
    write_run("RUN-20260913-001", "COMPLETED", "T5", [("T5", "DONE", None)], spec_id="SPEC-AREA-002")
    write_run("RUN-20260915-001", "COMPLETED", "T5", [("T5", "DONE", None)], spec_id="SPEC-AREA-002")
    write_shadow_doc("area-002", ["RUN-20260915-001"], "分析內容")
    data = full_sandbox.specflow.build()
    assert data["run_phase"]["RUN-20260915-001"] == "phase3"


def test_cancelled_phase3_run_with_doc_still_counts_as_integrated(full_sandbox, write_run, write_shadow_doc):
    """Phase 3 run 在整合完成後被 run cancel（shadow 文件會註明）→ 仍算整合完成（不是失敗）。"""
    write_run("RUN-20260913-001", "COMPLETED", "T5", [("T5", "DONE", None)], spec_id="SPEC-AREA-004")
    write_run("RUN-20260916-002", "CANCELLED", "T4", [("T4", "DONE", None)], spec_id="SPEC-AREA-004")
    write_shadow_doc("area-004", ["RUN-20260916-002"], "已於整合完成後 run cancel。")
    spec = _spec(full_sandbox, "AREA-004")
    assert spec["dod"]["integrated"] is True
    assert spec["integration"]["status"] == "done"


def test_dod_all_three_true_when_final_and_doc_and_integration_present(full_sandbox, write_run, write_shadow_doc):
    """DoD 三項：整合完成 + shadow 文件 + final 已產出，且 final 檔的時間不落後 Phase3 結束時間。"""
    write_run("RUN-20260913-001", "COMPLETED", "T5", [("T5", "DONE", None)], spec_id="SPEC-AREA-005")
    write_run("RUN-20260915-001", "COMPLETED", "T5", [("T4", "DONE", None, {"approval_id": "APR-1"}), ("T5", "DONE", None)], spec_id="SPEC-AREA-005")
    write_shadow_doc("area-005", ["RUN-20260915-001"], "整合完成。")
    final_dir = full_sandbox.root / "testcases" / "final"
    final_dir.mkdir(parents=True, exist_ok=True)
    (final_dir / "AREA-005-final-active.json").write_text("[]", encoding="utf-8")
    (final_dir / "AREA-005-final.html").write_text("<html></html>", encoding="utf-8")
    spec = _spec(full_sandbox, "AREA-005")
    assert spec["dod"] == {"integrated": True, "shadow_doc": True, "final": True}
    assert spec["complete"] is True


def test_missing_final_reports_incomplete(full_sandbox, write_run, write_shadow_doc):
    """整合完成、有 shadow 文件，但 final 還沒匯出 → missing 含 final，complete=False。"""
    write_run("RUN-20260913-001", "COMPLETED", "T5", [("T5", "DONE", None)], spec_id="SPEC-AREA-006")
    write_run("RUN-20260915-001", "COMPLETED", "T5", [("T4", "DONE", None, {"approval_id": "APR-1"}), ("T5", "DONE", None)], spec_id="SPEC-AREA-006")
    write_shadow_doc("area-006", ["RUN-20260915-001"], "整合完成。")
    spec = _spec(full_sandbox, "AREA-006")
    assert "final" in spec["missing"]
    assert spec["complete"] is False
