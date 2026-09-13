"""每個測試 session 用一份乾淨的 QAOS root 副本（只複製定義層），避免污染 repo。"""
import os, shutil, pathlib, tempfile, pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
TMP = pathlib.Path(tempfile.mkdtemp(prefix="qaos-test-"))
for d in ("schemas", "agents", "workflows", "permissions"):
    shutil.copytree(REPO / d, TMP / d)
for d in ("specs", "testcases/registry", "testcases/versions", "testsuites", "bugs", "artifacts", "executions", "evidence", "approvals", "runs"):
    (TMP / d).mkdir(parents=True, exist_ok=True)
os.environ["QAOS_ROOT"] = str(TMP)

@pytest.fixture(scope="session")
def root(): return TMP

@pytest.fixture(scope="session")
def fixtures(): return REPO / "tests" / "fixtures"
