import os
import pathlib

ADMIN_DIR = pathlib.Path(__file__).resolve().parents[1]
PROJECT_ROOT = ADMIN_DIR.parent
STAGES_YAML = ADMIN_DIR / "config" / "stages.yaml"
FRONTEND_DIST = ADMIN_DIR / "frontend" / "dist"


def _env_path(name: str, default: pathlib.Path) -> pathlib.Path:
    v = os.environ.get(name)
    return pathlib.Path(v).resolve() if v else default


# 測試時可用環境變數把資料來源指到別處（例如 scratch 目錄），避免動到真實產出
DATA_DIR = _env_path("QAOS_ADMIN_DATA_DIR", ADMIN_DIR / "data")
DB_PATH = DATA_DIR / "admin.db"
FINAL_DIR = _env_path("QAOS_ADMIN_FINAL_DIR", PROJECT_ROOT / "testcases" / "final")
RUNS_DIR = _env_path("QAOS_ADMIN_RUNS_DIR", PROJECT_ROOT / "runs")
WARROOM_DIR = _env_path("QAOS_ADMIN_WARROOM_DIR", PROJECT_ROOT / ".warroom")
EVENTS_FILE = WARROOM_DIR / "events.jsonl"
