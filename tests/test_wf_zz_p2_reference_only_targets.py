"""P2 AC-02-6（附錄 A 2-8）：已被 run、需求模型（RM）、TC 版本當作目標或依據的版本，不能以 metadata upgrade 設為 reference_only。
沿用前面 WF 測試以正式流程建立的 session root：SPEC-AUTH-001@1.0 已有 run、RM 與 TC 版本。"""
import pytest
from tools.qaos import store, spec_ops
from tools.qaos.cli import main as cli

def test_ac_02_6_used_by_run_rm_and_tc_is_refused(capsys):
    hits = spec_ops._uses_as_target("SPEC-AUTH-001", "1.0")
    assert any(h.startswith("RUN-") for h in hits) and "RM SPEC-AUTH-001@1.0" in hits and any(h.startswith("TC-AUTH-") for h in hits), hits
    p = store.spec_dir("SPEC-AUTH-001") / "spec.yaml"; before = p.read_bytes()
    with pytest.raises(SystemExit) as e:
        cli(["spec", "metadata", "upgrade", "SPEC-AUTH-001@1.0", "--analysis-policy", "reference_only", "--reason", "x", "--by", "oscar@example.com"])
    assert "reference_only" in str(e.value.code) and p.read_bytes() == before
