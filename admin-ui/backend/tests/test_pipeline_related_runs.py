"""A6 稽核 Top 15：pipeline._related_runs（活著的 run 永遠在前 8 筆內，不被舊活動分數截掉）。

曾出過的真實 bug：剛建立、還沒累積事件的 run 分數低，被歷史活動多的舊 run 擠出前 8 筆，
即時分頁因此看不到車道。"""
from backend.services.pipeline import _related_runs


def _iso(ts: float) -> str:
    import datetime as dt
    return dt.datetime.fromtimestamp(ts, dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _run(run_id: str, status: str, created: float, updated: float, n_history: int = 0, activity_at: float | None = None) -> dict:
    """activity_at：history 事件的時間點，預設等於 updated（落在 session 區間內才會計分）。"""
    at = _iso(activity_at if activity_at is not None else updated)
    hist = [{"to": "RUNNING", "at": at} for _ in range(n_history)]
    return {"run_id": run_id, "status": status, "_created": created, "_updated": updated,
            "tasks": [{"history": hist, "gate_results": []}] if n_history else [{"history": [], "gate_results": []}],
            "history": []}


def _session(first: float, last: float) -> dict:
    return {"_first": first, "_last": last}


def test_freshly_created_active_run_is_never_pushed_out_of_top8():
    """9 條有分數的舊 run（每條都有大量活動）＋ 1 條剛建立、活動筆數為 0 但狀態是 RUNNING 的新 run
    → 新 run 必須出現在結果裡（不被舊分數擠出去），且排最前面。"""
    now = 1_800_000_000.0
    s = _session(now - 600, now)
    old_runs = [_run(f"RUN-OLD-{i}", "COMPLETED", now - 500, now - 400, n_history=5) for i in range(9)]
    new_run = _run("RUN-NEW-001", "RUNNING", now, now)  # 剛建立，_created 在區間內但 history 是空的 → 舊算法分數只有 2
    out = _related_runs(s, old_runs + [new_run])
    assert out[0]["run_id"] == "RUN-NEW-001"
    assert "RUN-NEW-001" in {r["run_id"] for r in out[:8]}


def test_terminal_runs_ranked_by_activity_score_among_themselves():
    """同樣都不是活著的 run，維持依活動分數排序（分數高的在前）。"""
    now = 1_800_000_000.0
    s = _session(now - 600, now)
    low = _run("RUN-LOW", "COMPLETED", now - 100, now - 90, n_history=1)
    high = _run("RUN-HIGH", "COMPLETED", now - 100, now - 90, n_history=5)
    out = _related_runs(s, [low, high])
    assert [r["run_id"] for r in out] == ["RUN-HIGH", "RUN-LOW"]


def test_run_outside_session_window_and_with_no_activity_is_excluded():
    """區間外、也沒有任何活動落在區間內的 run → 分數 0，不出現在結果裡。"""
    now = 1_800_000_000.0
    s = _session(now - 600, now)
    far = _run("RUN-FAR", "COMPLETED", now - 100_000, now - 99_000, n_history=0)
    out = _related_runs(s, [far])
    assert out == []
