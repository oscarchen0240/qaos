"""Pipeline 階段大綱依 workflow_id 選對應模板（2026-09-22 修正：不同 workflow 不再共用 spec-to-testcase 的 T1..T5 大綱）。"""
from backend.services import pipeline, stages as st_svc


def _cfg():
    return st_svc.load()


def test_spec_to_bug_run_uses_its_own_stage_labels_not_spec_to_testcase(write_run):
    """事故重現：spec-to-bug 的 T1（Bug Analyst）過去被誤標成「Spec 分析」。現在要用 spec-to-bug 自己的大綱。"""
    p = write_run("RUN-BUG-001", "RUNNING", "T2", [
        ("T0", "DONE", None), ("T1", "DONE", "agent-bug-analyst"), ("T2", "RUNNING", "agent-bug-validator"),
        ("T3", "PENDING", None), ("T4", "PENDING", "agent-supervisor"),
    ], workflow_id="spec-to-bug")
    import yaml
    run = yaml.safe_load(p.read_text())
    run["run_id"] = "RUN-BUG-001"
    cfg = _cfg()
    pipe = st_svc.pipeline_for_workflow(cfg, "spec-to-bug")
    assert pipe["id"] == "spec-to-bug"
    out = pipeline._run_stage_status(cfg, run, pipe)
    assert out["bug-analysis"]["status"] == "done"
    assert out["bug-validation"]["status"] == "active"
    # 不會出現 spec-to-testcase 專屬的合成階段
    assert "integration" not in out and "final-export" not in out
    ids = {s["id"] for s in pipe["stages"]}
    assert "test-design" not in ids and "validation" not in ids  # spec-to-bug 沒有這兩個 id，是 bug-analysis/bug-validation


def test_spec_to_testcase_run_unaffected_by_multi_pipeline_refactor(write_run):
    """回歸：spec-to-testcase 的既有 8 階段大綱行為不變。"""
    p = write_run("RUN-TC-001", "WAITING_HUMAN", "T4", [
        ("T1", "DONE", "agent-spec-analyst"), ("T2", "DONE", "agent-test-designer"),
        ("T3", "DONE", "agent-test-validator"), ("T4", "RUNNING", None), ("T5", "PENDING", "agent-supervisor"),
    ], workflow_id="spec-to-testcase", waiting_on_approval_id="APR-1")
    import yaml
    run = yaml.safe_load(p.read_text()); run["run_id"] = "RUN-TC-001"
    cfg = _cfg()
    pipe = st_svc.pipeline_for_workflow(cfg, "spec-to-testcase")
    assert pipe["id"] == "spec-to-testcase"
    out = pipeline._run_stage_status(cfg, run, pipe)
    assert out["spec-analysis"]["status"] == "done"
    assert out["test-design"]["status"] == "done"
    assert out["validation"]["status"] == "done"
    assert out["approval"]["status"] == "waiting_human"


def test_independent_review_stage_differs_per_pipeline():
    """_classify_agent 的「獨立審查」啟發式要對應各自 pipeline 的 independent_review 節點，不是寫死 stage id 'validation'。"""
    cfg = _cfg()
    bug_pipe = st_svc.pipeline_for_workflow(cfg, "spec-to-bug")
    tc_pipe = st_svc.pipeline_for_workflow(cfg, "spec-to-testcase")
    assert st_svc.independent_review_stage(bug_pipe)["id"] == "bug-validation"
    assert st_svc.independent_review_stage(tc_pipe)["id"] == "validation"

    s = {"transcript_path": "", "session_id": "sess-x"}
    a = {"agent_type": "general-purpose", "agent_id": "a1", "subagent_name": ""}
    c = pipeline._classify_agent(bug_pipe, a, s)
    # 沒有 meta.json（讀不到 description）時退回 agent_type 本身，不會硬套 "Test Validator"
    assert c["role"] != "Test Validator（獨立審查）"


def test_unknown_workflow_falls_back_to_minimal_pipeline():
    cfg = _cfg()
    pipe = st_svc.pipeline_for_workflow(cfg, "some-future-workflow-not-yet-defined")
    assert pipe["id"] == "unknown"
    assert {s["id"] for s in pipe["stages"]} == {"intake", "summary"}


def test_all_six_known_workflows_have_dedicated_pipelines():
    cfg = _cfg()
    for wf in ("spec-to-testcase", "spec-to-bug", "testcase-revision", "manual-test-to-regression", "regression-generation", "spec-change-impact"):
        pipe = st_svc.pipeline_for_workflow(cfg, wf)
        assert pipe["id"] == wf, f"{wf} 應該有自己的 pipeline，不是 fallback"
        assert pipe["stages"][0]["id"] == "intake"
        assert pipe["stages"][-1]["id"] == "summary"
