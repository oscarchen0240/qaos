"""A6 #8：Pipeline 主狀態合成（純函式 pipeline._primary）。run CANCELLED + session live → 主標不是「執行中」。"""
import time

import pytest

from backend.services import pipeline


def _run(status: str, **kw) -> dict:
    now = time.time()
    return {"run_id": "RUN-T-001", "status": status, "_created": now - 600, "_updated": now - 60, "file_mtime": now - 60,
            "waiting_on_approval_id": kw.get("apr"), "spec_id": "SPEC-TEST-001", "spec_version": "0.1"}


def _session(ended: bool = False) -> dict:
    return {"ended_at": "2026-09-18T00:00:00Z" if ended else None}


@pytest.mark.parametrize("state", ["live", "stalled"])
def test_cancelled_run_with_live_session_is_not_running(state):
    v = pipeline._primary(_run("CANCELLED"), "測試設計", {"state": state, "idle_seconds": 5}, _session(), time.time(), "TEST v0.1")
    assert v["primary_status"] == "cancelled"
    assert "已取消" in v["primary_label"]
    assert "執行中" not in v["primary_label"]
    assert v["clock_frozen"] is True
    assert v["secondary"] == "session 仍連線"


def test_completed_run_freezes_clock():
    v = pipeline._primary(_run("COMPLETED"), None, {"state": "ended", "idle_seconds": 0}, _session(ended=True), time.time(), "TEST v0.1")
    assert v["primary_status"] == "completed" and v["clock_frozen"] is True
    assert v["run_elapsed_seconds"] is not None and v["run_elapsed_seconds"] <= 600


def test_waiting_human_shows_approval_id():
    v = pipeline._primary(_run("WAITING_HUMAN", apr="APR-0009"), None, {"state": "live", "idle_seconds": 1}, _session(), time.time(), "TEST v0.1")
    assert v["primary_status"] == "waiting_human"
    assert "等你決定" in v["primary_label"] and "APR-0009" in v["primary_label"]
    assert v["clock_frozen"] is False


def test_running_run_with_stalled_session_marks_secondary():
    v = pipeline._primary(_run("RUNNING"), "獨立驗證", {"state": "stalled", "idle_seconds": 700}, _session(), time.time(), "TEST v0.1")
    assert v["primary_status"] == "running" and "執行中" in v["primary_label"] and "獨立驗證" in v["primary_label"]
    assert v["secondary"] == "可能卡住"


def test_no_run_only_events():
    v = pipeline._primary(None, None, {"state": "live", "idle_seconds": 1}, _session(), time.time(), None)
    assert v["primary_status"] == "no_run"
