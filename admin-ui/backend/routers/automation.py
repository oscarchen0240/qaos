"""M4 自動化測試預留（stub）。

目前只定義 API 契約與資料表（db.py 的 test_runs / test_results），**不接任何 runner**。
除了「列出既有 run」之外，所有端點回 501，讓前端與文件先對齊，M7 接執行時再填實作。

規劃中的流程（M7，需先放寬邊界 1 才能寫回 QAOS）：
  1. 從產出／資料夾挑 TC → POST /runs 建一個 test_run（trigger=manual|ci|schedule）
  2. 執行者（人或 runner）逐條回報 POST /runs/{id}/results：pass | fail | blocked | skipped，可附 duration_ms、log_path、evidence
  3. run 結束 → autoreports.upsert_auto(kind="automation", source_key=str(run_id)) 自動產一份報告
  4. fail 的結果 → 產 bug 草稿，走「單據 › Bug」頁組 `bin/qaos bug ...`（或 M7 直接執行）
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .. import db

router = APIRouter(prefix="/api/automation", tags=["automation"])

NOT_IMPL = "自動化測試尚未實作（M4 stub）；見 admin-ui/backend/routers/automation.py 的契約說明"

RESULT_VALUES = ("pass", "fail", "blocked", "skipped")
RUN_STATUS = ("planned", "running", "done", "aborted")


class RunIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    trigger: str = "manual"            # manual | ci | schedule
    testcase_ids: list[str] = []       # 來自產出 JSON 或資料夾
    note: str = ""


class ResultIn(BaseModel):
    testcase_id: str
    result: str                        # pass | fail | blocked | skipped
    duration_ms: int | None = None
    log_path: str | None = None
    evidence: list[str] = []           # 截圖／log 路徑，M7 存 admin-ui/data/evidence/
    note: str = ""


@router.get("/contract")
def contract():
    """讓前端顯示「預留了什麼」；不是功能。"""
    return {
        "status": "stub",
        "tables": ["test_runs", "test_results"],
        "result_values": list(RESULT_VALUES),
        "run_status": list(RUN_STATUS),
        "endpoints": [
            {"method": "GET", "path": "/api/automation/runs", "state": "ok", "desc": "列出 test_runs（目前永遠空）"},
            {"method": "POST", "path": "/api/automation/runs", "state": "501", "desc": "建立一次執行：name、trigger、testcase_ids"},
            {"method": "GET", "path": "/api/automation/runs/{id}", "state": "501", "desc": "單次執行與逐條結果"},
            {"method": "POST", "path": "/api/automation/runs/{id}/results", "state": "501", "desc": "回報一條 TC 的 pass/fail/blocked/skipped＋證據"},
            {"method": "POST", "path": "/api/automation/runs/{id}/finish", "state": "501", "desc": "結束執行 → 自動產報告（kind=automation）"},
            {"method": "GET", "path": "/api/automation/runners", "state": "501", "desc": "可用的 runner（未定）"},
        ],
        "next": "M7：從產出／資料夾挑 TC 建 run、逐條記 OK/NG、NG 產 bug 草稿到「單據 › Bug」；寫回 QAOS 需先放寬邊界 1。",
    }


@router.get("/runs")
def list_runs():
    with db.connect() as con:
        rows = con.execute("SELECT id, name, trigger, status, started_at, ended_at, created_at FROM test_runs ORDER BY id DESC").fetchall()
    return [dict(r) for r in rows]


@router.post("/runs", status_code=501)
def create_run(body: RunIn):
    raise HTTPException(501, NOT_IMPL)


@router.get("/runs/{run_id}", status_code=501)
def get_run(run_id: int):
    raise HTTPException(501, NOT_IMPL)


@router.post("/runs/{run_id}/results", status_code=501)
def add_result(run_id: int, body: ResultIn):
    if body.result not in RESULT_VALUES:
        raise HTTPException(400, f"result 必須是 {', '.join(RESULT_VALUES)}")
    raise HTTPException(501, NOT_IMPL)


@router.post("/runs/{run_id}/finish", status_code=501)
def finish_run(run_id: int):
    raise HTTPException(501, NOT_IMPL)


@router.get("/runners", status_code=501)
def runners():
    raise HTTPException(501, NOT_IMPL)
