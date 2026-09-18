"""工程 CI 狀態（PROMPT-test-automation-coverage-audit A4）。

第一版只讀檔：admin-ui/data/ci-status.json（由 admin-ui/scripts/write_ci_status.py 本機寫入，或 GitLab artifact 同步過來）。
不打 GitLab API、不打 GitHub。這是「程式有沒有壞」的工程 CI，跟控制台「測試執行」的產品 TC 回合是兩回事。
"""
import json
import os

from fastapi import APIRouter

from ..config import ADMIN_DIR, DATA_DIR

router = APIRouter(prefix="/api/ci", tags=["ci"])
STATUS_FILE = DATA_DIR / "ci-status.json"
EXAMPLE_FILE = ADMIN_DIR / "config" / "ci-status.example.json"


@router.get("/status")
def status():
    web_url = os.environ.get("GITLAB_PIPELINE_URL", "")
    remote = ""
    try:
        import subprocess
        remote = subprocess.run(["git", "remote", "get-url", "origin"], cwd=ADMIN_DIR.parent, capture_output=True, text=True, timeout=5).stdout.strip()
    except Exception:  # noqa: BLE001
        pass
    if not STATUS_FILE.exists():
        return {"available": False, "file": str(STATUS_FILE.relative_to(ADMIN_DIR.parent)), "example": str(EXAMPLE_FILE.relative_to(ADMIN_DIR.parent)), "web_url": web_url, "remote": remote, "status": None}
    try:
        d = json.loads(STATUS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return {"available": False, "file": str(STATUS_FILE.relative_to(ADMIN_DIR.parent)), "error": str(e), "web_url": web_url, "remote": remote, "status": None}
    d.setdefault("jobs", [])
    if not d.get("web_url") and web_url:
        d["web_url"] = web_url
    return {"available": True, "file": str(STATUS_FILE.relative_to(ADMIN_DIR.parent)), "remote": remote, "status": d}
