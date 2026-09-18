from fastapi import APIRouter

from .. import db
from ..services import outputs as out_svc
from ..services import pipeline as pipe_svc
from ..services import tickets as ticket_svc
from .todos import sync_auto_complete

router = APIRouter(prefix="/api/nav", tags=["nav"])


@router.get("")
def nav_counts():
    from ..services import autoreports
    autoreports.sync_outputs()
    with db.connect() as con:
        sync_auto_complete(con)
        open_todos = con.execute("SELECT COUNT(*) FROM todos WHERE status<>'done'").fetchone()[0]
        reports = con.execute("SELECT COUNT(*) FROM reports").fetchone()[0]
        reports_unreviewed = con.execute("SELECT COUNT(*) FROM reports WHERE kind<>'manual' AND TRIM(body_md)=''").fetchone()[0]
    return {
        "pipeline": {"active_sessions": pipe_svc.snapshot()["live_count"]},
        "outputs": out_svc.counts(),
        "reports": {"total": reports, "unreviewed": reports_unreviewed},
        "todos": {"open": open_todos},
        "tickets": ticket_svc.counts(),
        "automation": {"runs": _test_runs(), "open": _open_runs()},
    }


def _test_runs() -> int:
    # M4 stub：test_runs 目前永遠空；M7 接 runner 後這裡就會有數字
    with db.connect() as con:
        return con.execute("SELECT COUNT(*) FROM test_runs").fetchone()[0]


def _open_runs() -> int:
    from ..services import testruns
    return testruns.open_count()
