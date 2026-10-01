"""條件式 task（T2R／T2RR／T3RR）要有對應的 stage，不能被 stage_for_task 找不到就靜默跳過。

回歸背景：ADR-009 merge 後高風險 area 的 run 會多一個 <after>RR task（agent-tc-risk-reviewer／G-RISK），
spec-to-testcase 的 analysis_review=required 也會多一個 T2R（REVIEW_TEST_ANALYSIS）。pipeline.py 的
_run_stage_status 與 durations.py 的 run_durations 都是「stage_for_task 找不到就 continue」，
stages.yaml 沒補對應就等於這些 task 完全不會出現在階段／耗時統計裡（MR !1 code review minor finding）。
"""
import yaml

from backend.services import durations, pipeline, stages as st_svc


def _cfg():
    return st_svc.load()


def test_spec_to_testcase_risk_review_task_maps_to_stage(write_run):
    p = write_run("RUN-RR-001", "WAITING_HUMAN", "T4", [
        ("T1", "DONE", "agent-spec-analyst"), ("T2", "DONE", "agent-test-designer"),
        ("T3", "DONE", "agent-test-validator"),
        ("T3RR", "DONE", "agent-tc-risk-reviewer", {"type": "agent", "gate": "G-RISK"}),
        ("T4", "RUNNING", None), ("T5", "PENDING", "agent-supervisor"),
    ], workflow_id="spec-to-testcase")
    run = yaml.safe_load(p.read_text())
    run["run_id"] = "RUN-RR-001"
    cfg = _cfg()
    pipe = st_svc.pipeline_for_workflow(cfg, "spec-to-testcase")
    out = pipeline._run_stage_status(cfg, run, pipe)
    assert "risk-review" in out, "T3RR 不能被 stage_for_task 漏掉"
    assert out["risk-review"]["status"] == "done"
    assert out["risk-review"]["task_id"] == "T3RR"


def test_spec_to_testcase_analysis_review_task_maps_to_stage(write_run):
    p = write_run("RUN-RR-002", "RUNNING", "T2R", [
        ("T1", "DONE", "agent-spec-analyst"), ("T2", "DONE", "agent-test-designer"),
        ("T2R", "RUNNING", None, {"type": "approval"}),
        ("T3", "PENDING", "agent-test-validator"),
    ], workflow_id="spec-to-testcase")
    run = yaml.safe_load(p.read_text())
    run["run_id"] = "RUN-RR-002"
    cfg = _cfg()
    pipe = st_svc.pipeline_for_workflow(cfg, "spec-to-testcase")
    out = pipeline._run_stage_status(cfg, run, pipe)
    assert "analysis-review" in out, "T2R（analysis_review=required）不能被漏掉"
    assert out["analysis-review"]["status"] == "waiting_human"


def test_testcase_revision_risk_review_task_maps_to_stage(write_run):
    p = write_run("RUN-RR-003", "WAITING_HUMAN", "T3", [
        ("T1", "DONE", "agent-test-designer"), ("T2", "DONE", "agent-test-validator"),
        ("T2RR", "DONE", "agent-tc-risk-reviewer", {"type": "agent", "gate": "G-RISK"}),
        ("T3", "RUNNING", None), ("T4", "PENDING", "agent-supervisor"),
    ], workflow_id="testcase-revision")
    run = yaml.safe_load(p.read_text())
    run["run_id"] = "RUN-RR-003"
    cfg = _cfg()
    pipe = st_svc.pipeline_for_workflow(cfg, "testcase-revision")
    out = pipeline._run_stage_status(cfg, run, pipe)
    assert "risk-review" in out
    assert out["risk-review"]["status"] == "done"


def test_manual_test_to_regression_risk_review_task_maps_to_stage(write_run):
    p = write_run("RUN-RR-004", "RUNNING", "T2RR", [
        ("T1", "DONE", "agent-test-designer"), ("T2", "DONE", "agent-test-validator"),
        ("T2RR", "RUNNING", "agent-tc-risk-reviewer", {"type": "agent", "gate": "G-RISK"}),
    ], workflow_id="manual-test-to-regression")
    run = yaml.safe_load(p.read_text())
    run["run_id"] = "RUN-RR-004"
    cfg = _cfg()
    pipe = st_svc.pipeline_for_workflow(cfg, "manual-test-to-regression")
    out = pipeline._run_stage_status(cfg, run, pipe)
    assert "risk-review" in out
    assert out["risk-review"]["status"] == "active"


def test_spec_change_impact_risk_review_task_maps_to_stage(write_run):
    p = write_run("RUN-RR-005", "WAITING_HUMAN", "T5", [
        ("T1", "DONE", "agent-change-impact-analyst"), ("T2", "DONE", "agent-test-designer"),
        ("T3", "DONE", "agent-test-validator"),
        ("T3RR", "DONE", "agent-tc-risk-reviewer", {"type": "agent", "gate": "G-RISK"}),
        ("T4", "DONE", "agent-change-impact-analyst"), ("T5", "RUNNING", None),
    ], workflow_id="spec-change-impact")
    run = yaml.safe_load(p.read_text())
    run["run_id"] = "RUN-RR-005"
    cfg = _cfg()
    pipe = st_svc.pipeline_for_workflow(cfg, "spec-change-impact")
    out = pipeline._run_stage_status(cfg, run, pipe)
    assert "risk-review" in out
    assert out["risk-review"]["status"] == "done"


def test_run_durations_includes_risk_review_stage(write_run):
    """durations.run_durations 跟 pipeline._run_stage_status 是兩條獨立的 stage_for_task 呼叫路徑，兩邊都要修。"""
    p = write_run("RUN-RR-006", "COMPLETED", None, [
        ("T1", "DONE", "agent-spec-analyst", {"history": [{"to": "READY", "at": "2026-09-18T00:00:00Z"}, {"to": "DONE", "at": "2026-09-18T00:01:00Z"}]}),
        ("T2", "DONE", "agent-test-designer", {"history": [{"to": "READY", "at": "2026-09-18T00:01:00Z"}, {"to": "DONE", "at": "2026-09-18T00:02:00Z"}]}),
        ("T3", "DONE", "agent-test-validator", {"history": [{"to": "READY", "at": "2026-09-18T00:02:00Z"}, {"to": "DONE", "at": "2026-09-18T00:03:00Z"}]}),
        ("T3RR", "DONE", "agent-tc-risk-reviewer", {"type": "agent", "gate": "G-RISK",
         "history": [{"to": "READY", "at": "2026-09-18T00:03:00Z"}, {"to": "RUNNING", "at": "2026-09-18T00:03:05Z"}, {"to": "DONE", "at": "2026-09-18T00:04:00Z"}]}),
        ("T4", "DONE", None, {"type": "approval", "history": [{"to": "READY", "at": "2026-09-18T00:04:00Z"}, {"to": "DONE", "at": "2026-09-18T00:05:00Z"}]}),
        ("T5", "DONE", "agent-supervisor", {"history": [{"to": "READY", "at": "2026-09-18T00:05:00Z"}, {"to": "DONE", "at": "2026-09-18T00:05:01Z"}]}),
    ], workflow_id="spec-to-testcase")
    run = yaml.safe_load(p.read_text())
    run["run_id"] = "RUN-RR-006"
    d = durations.run_durations(run, now=0)
    assert "risk-review" in d["stages"], "run_durations 也要看得到 T3RR 對應的 risk-review 階段"
    assert d["stages"]["risk-review"]["elapsed"] is not None
