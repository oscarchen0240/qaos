"""每個測試 session 用一份乾淨的 QAOS root 副本（只複製定義層），避免污染 repo。"""
import os, shutil, pathlib, tempfile, pytest

REPO = pathlib.Path(__file__).resolve().parents[1]

def make_root(base: pathlib.Path) -> pathlib.Path:
    """在 base 建立一份乾淨的 QAOS root（定義層副本 + 空的資料目錄）。"""
    for d in ("schemas", "agents", "workflows", "permissions"):
        shutil.copytree(REPO / d, base / d)
    for d in ("specs", "testcases/registry", "testcases/versions", "testsuites", "bugs", "artifacts", "executions", "evidence", "approvals", "runs"):
        (base / d).mkdir(parents=True, exist_ok=True)
    return base

TMP = make_root(pathlib.Path(tempfile.mkdtemp(prefix="qaos-test-")))
os.environ["QAOS_ROOT"] = str(TMP)

@pytest.fixture(scope="session")
def root(): return TMP

@pytest.fixture(scope="session")
def fixtures(): return REPO / "tests" / "fixtures"
