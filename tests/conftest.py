"""每個測試 session 用一份乾淨的 QAOS root 副本（只複製定義層），避免污染 repo。

新安裝的 root 以正式流程進入移轉後狀態（S_post）：maintenance start → migrate → maintenance end。
所有寫入一律經過 executor（tools/qaos/operation.py）。"""
import os, shutil, pathlib, tempfile, pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
TMP = pathlib.Path(tempfile.mkdtemp(prefix="qaos-test-"))
for d in ("schemas", "agents", "workflows", "permissions"):
    shutil.copytree(REPO / d, TMP / d)
for d in ("specs", "testcases/registry", "testcases/versions", "testsuites", "bugs", "artifacts", "executions", "evidence", "approvals", "runs"):
    (TMP / d).mkdir(parents=True, exist_ok=True)
os.environ["QAOS_ROOT"] = str(TMP)

from tools.qaos import operation as _op   # noqa: E402  （QAOS_ROOT 設定之後才 import）
_op.maintenance_start("conftest")
_op.migrate("conftest")
_op.maintenance_end("conftest")

@pytest.fixture(scope="session")
def root(): return TMP

@pytest.fixture(scope="session")
def fixtures(): return REPO / "tests" / "fixtures"
