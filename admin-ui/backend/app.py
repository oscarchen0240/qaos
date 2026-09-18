from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import db
from .config import FRONTEND_DIST
from .routers import todos, nav, outputs, reports, pipeline, folders, tickets, automation, testruns, ci

app = FastAPI(title="QAOS Admin UI", docs_url="/api/docs", openapi_url="/api/openapi.json")


@app.on_event("startup")
def _startup():
    db.init_db()
    _chain_sigterm()


@app.on_event("shutdown")
def _shutdown():
    pipeline.SHUTTING_DOWN["flag"] = True


def _chain_sigterm():
    """uvicorn 的 shutdown 事件要等所有連線關閉才觸發；SSE 長連線得在 SIGTERM 當下就知道要收掉。"""
    import signal
    for sig in (signal.SIGTERM, signal.SIGINT):
        prev = signal.getsignal(sig)

        def handler(signum, frame, _prev=prev):
            pipeline.SHUTTING_DOWN["flag"] = True
            if callable(_prev):
                _prev(signum, frame)
        try:
            signal.signal(sig, handler)
        except ValueError:
            pass  # 非主執行緒時略過


app.include_router(todos.router)
app.include_router(nav.router)
app.include_router(outputs.router)
app.include_router(reports.router)
app.include_router(pipeline.router)
app.include_router(folders.router)
app.include_router(tickets.router)
app.include_router(automation.router)
app.include_router(testruns.router)
app.include_router(ci.router)


@app.get("/api/health")
def health():
    return {"ok": True}


# 建置後的前端由後端直接提供（開發時走 Vite proxy，不會進到這裡）
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{path:path}")
    def spa(path: str):
        target = FRONTEND_DIST / path
        if path and target.is_file():
            return FileResponse(target)
        return FileResponse(FRONTEND_DIST / "index.html")
