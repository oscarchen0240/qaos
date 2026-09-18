"""A6 稽核 Top 13：durations._task_durations（READY→RUNNING=agent工作、approval RUNNING→DONE=等人、多輪加總）。"""
from backend.services.durations import _task_durations


def _task(task_id: str, status: str, history: list[tuple[str, str]], ttype: str = "agent", iteration: int = 0) -> dict:
    return {"task_id": task_id, "status": status, "type": ttype, "iteration": iteration,
            "history": [{"to": to, "at": at} for to, at in history]}


def test_ready_to_running_counts_as_agent_work():
    t = _task("T2", "DONE", [("READY", "2026-09-18T00:00:00Z"), ("RUNNING", "2026-09-18T00:05:00Z"), ("DONE", "2026-09-18T00:05:10Z")])
    d = _task_durations(t, now=0, run_terminal=True)
    assert d["work"] == 300.0
    assert d["gate"] == 10.0
    assert d["human"] == 0.0
    assert d["elapsed"] == 310.0


def test_approval_running_to_done_counts_as_human_wait():
    t = _task("T4", "DONE", [("READY", "2026-09-18T00:00:00Z"), ("RUNNING", "2026-09-18T00:00:01Z"), ("DONE", "2026-09-18T01:00:01Z")], ttype="approval")
    d = _task_durations(t, now=0, run_terminal=True)
    assert d["human"] == 3600.0
    assert d["work"] == 1.0
    assert d["gate"] == 0.0


def test_multiple_iterations_sum_work_and_gate():
    """Designer 迭代 3 輪：每輪 READY→RUNNING（work）與 RUNNING→GATE_FAILED/DONE（gate）都要累加，iterations 取送出次數。"""
    hist = [
        ("READY", "2026-09-18T00:00:00Z"), ("RUNNING", "2026-09-18T00:01:00Z"), ("GATE_FAILED", "2026-09-18T00:01:05Z"),
        ("READY", "2026-09-18T00:02:00Z"), ("RUNNING", "2026-09-18T00:04:00Z"), ("GATE_FAILED", "2026-09-18T00:04:05Z"),
        ("READY", "2026-09-18T00:05:00Z"), ("RUNNING", "2026-09-18T00:06:00Z"), ("DONE", "2026-09-18T00:06:08Z"),
    ]
    t = _task("T2", "DONE", hist, iteration=2)
    d = _task_durations(t, now=0, run_terminal=True)
    assert d["work"] == (60 + 120 + 60)
    assert d["gate"] == (5 + 5 + 8)
    assert d["iterations"] == 3  # 送出次數（3）比 run.yaml 的 iteration 欄位（2，從 0 起算）更準


def test_in_progress_task_counts_elapsed_up_to_now():
    """還在跑（run 未終止、task 是 READY）→ work 要把「到現在」算進去，不能是 None。"""
    t = _task("T2", "READY", [("READY", "2026-09-18T00:00:00Z")])
    now = __import__("datetime").datetime(2026, 9, 18, 0, 3, 0, tzinfo=__import__("datetime").timezone.utc).timestamp()
    d = _task_durations(t, now=now, run_terminal=False)
    assert d["work"] == 180.0
    assert d["running"] is True
    assert d["elapsed"] == 180.0


def test_terminal_run_does_not_extend_elapsed_to_now():
    """run 已終止（CANCELLED/FAILED/COMPLETED）→ 不把「到現在」算進去，即使 task 仍是 READY/RUNNING。"""
    t = _task("T3", "READY", [("READY", "2026-09-18T00:00:00Z")])
    now = __import__("datetime").datetime(2026, 9, 18, 5, 0, 0, tzinfo=__import__("datetime").timezone.utc).timestamp()
    d = _task_durations(t, now=now, run_terminal=True)
    assert d["running"] is False
    assert d["work"] == 0.0


def test_task_with_no_history_marks_no_history():
    t = _task("T3", "PENDING", [])
    d = _task_durations(t, now=0, run_terminal=False)
    assert d["no_history"] is True
    assert d["elapsed"] is None
