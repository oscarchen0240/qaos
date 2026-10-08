import os
import pathlib

def _env_path(name: str, default: pathlib.Path) -> pathlib.Path:
    v = os.environ.get(name)
    return pathlib.Path(v).resolve() if v else default


ADMIN_DIR = pathlib.Path(__file__).resolve().parents[1]
# QAOS 專案根（bin/qaos 的執行目錄，也是 approvals／clarifications／bugs／runs… 的讀取來源）。
# 預設是本檔所在 checkout 的上一層；從 git worktree 跑 dev server 時必須用 QAOS_ADMIN_PROJECT_ROOT 指回主資料夾，
# 否則平台執行 bin/qaos 的寫入會落在 worktree 副本（qaos_exec 另有擋住 worktree 的防護）。
PROJECT_ROOT = _env_path("QAOS_ADMIN_PROJECT_ROOT", ADMIN_DIR.parent)
STAGES_YAML = ADMIN_DIR / "config" / "stages.yaml"
FRONTEND_DIST = ADMIN_DIR / "frontend" / "dist"


# 測試時可用環境變數把資料來源指到別處（例如 scratch 目錄），避免動到真實產出
DATA_DIR = _env_path("QAOS_ADMIN_DATA_DIR", ADMIN_DIR / "data")
DB_PATH = DATA_DIR / "admin.db"
FINAL_DIR = _env_path("QAOS_ADMIN_FINAL_DIR", PROJECT_ROOT / "testcases" / "final")
RUNS_DIR = _env_path("QAOS_ADMIN_RUNS_DIR", PROJECT_ROOT / "runs")
WARROOM_DIR = _env_path("QAOS_ADMIN_WARROOM_DIR", PROJECT_ROOT / ".warroom")
EVENTS_FILE = WARROOM_DIR / "events.jsonl"
