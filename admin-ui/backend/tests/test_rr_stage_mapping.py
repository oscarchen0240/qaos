"""條件式 task（T2R／T2RR／T3RR）要有對應的 stage，不能被 stage_for_task 找不到就靜默跳過。

回歸背景：ADR-009 merge 後高風險 area 的 run 會多一個 <after>RR task（agent-tc-risk-reviewer／G-RISK），
spec-to-testcase 的 analysis_review=required 也會多一個 T2R（REVIEW_TEST_ANALYSIS）。pipeline.py 的
_run_stage_status 與 durations.py 的 run_durations 都是「stage_for_task 找不到就 continue」，
stages.yaml 沒補對應就等於這些 task 完全不會出現在階段／耗時統計裡（MR !1 code review minor finding）。

MR !5 第 01 輪審查（Codex）又抓到兩個問題，本檔已對應修正：
- R1-01：補上 stage 對應後，沒有觸發這個條件式 task 的 run（例如非高風險 area 沒有 RR）在
  session_view 裡會顯示成「待進行（pending）」，不是真的不適用。修法是 stages.yaml 幫這 5 個
  stage 標 conditional: true，pipeline.py 新增 _stage_applies()，在 session_view 的階段清單裡
  把「conditional 但這個 run 沒有對應 runtime task」的 stage 直接排除，不是顯示成 pending。
- R1-02：spec-to-testcase 相關測試會呼叫到 specflow（stage_evidence／run_phase），沒有用
  full_sandbox 隔離就會碰到真實專案資料。已補上 full_sandbox fixture。
"""
import yaml

from backend.services import durations, pipeline, stages as st_svc


def _cfg():
    return st_svc.load()


def test_spec_to_testcase_risk_review_task_maps_to_stage(full_sandbox, write_run):
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


def test_spec_to_testcase_analysis_review_task_maps_to_stage(full_sandbox, write_run):
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


def test_run_durations_includes_risk_review_stage(full_sandbox, write_run):
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


# ---------------------------------------------------------------- R1-01：conditional stage 不該顯示成「待進行」

def _stage(conditional: bool = True) -> dict:
    return {"id": "risk-review", "conditional": conditional}


def test_conditional_stage_with_no_runtime_task_does_not_apply():
    """非高風險 area 的 run 沒有 T3RR → risk-review 這個 stage 不適用，不是「待進行」。"""
    assert pipeline._stage_applies(_stage(), {}, {"run_id": "RUN-1", "status": "COMPLETED"}) is False


def test_conditional_stage_with_runtime_task_applies():
    """這個 run 真的有 T3RR → risk-review 照常顯示（status 由 r 決定，不受這個檢查影響）。"""
    assert pipeline._stage_applies(_stage(), {"status": "done"}, {"run_id": "RUN-1", "status": "COMPLETED"}) is True


def test_conditional_stage_without_active_run_still_applies():
    """沒有 active_run（例如還沒建過 run 的 session 板面）時不做這個判斷，維持原本顯示所有階段的行為。"""
    assert pipeline._stage_applies(_stage(), {}, None) is True


def test_non_conditional_stage_always_applies_even_without_runtime_data():
    """一般（非條件式）stage 即使還沒有 runtime 資料（task 還沒開始）也照常顯示成 pending，不受這個檢查影響。"""
    assert pipeline._stage_applies(_stage(conditional=False), {}, {"run_id": "RUN-1", "status": "RUNNING"}) is True


def test_session_view_excludes_risk_review_for_run_without_rr_task(full_sandbox, write_run, monkeypatch):
    """端到端重現 R1-01：testcase-revision 的 run 沒有 T2RR（低風險 area），COMPLETED 後 risk-review
    不該出現在 session_view 的 stages 清單裡（修正前會以 status=pending 出現）。"""
    from backend.services import clarifications
    monkeypatch.setattr(clarifications, "PROJECT_ROOT", full_sandbox.root)  # 不碰真專案的 clarifications/
    write_run("RUN-RR-007", "COMPLETED", "T4", [
        ("T1", "DONE", "agent-test-designer"), ("T2", "DONE", "agent-test-validator"),
        ("T3", "DONE", None, {"type": "approval"}), ("T4", "DONE", "agent-supervisor"),
    ], workflow_id="testcase-revision", created_at="2026-09-18T00:00:00Z", updated_at="2026-09-18T00:05:00Z")
    run = full_sandbox.runs.get("RUN-RR-007")
    now = run["_created"] + 300  # 落在 _related_runs 的 ±10 分鐘視窗內，run 才會被選為 active_run
    cfg = _cfg()
    s = {"session_id": "sess-rr-007", "agents": [], "ended_at": "2026-09-18T00:10:00Z", "_last": now, "_first": now - 60,
         "agent_types": [], "final_writes": [], "tag": None, "cwd": "", "started_at": None, "first_seen": None,
         "last_seen": None, "event_count": 0, "stops": 0, "end_reason": None}
    view = pipeline.session_view(cfg, s, {}, [run], now)
    ids = {st["id"] for st in view["stages"]}
    assert "risk-review" not in ids, "沒有 T2RR 的 run 不該顯示 risk-review（修正前會以 pending 顯示）"
    assert "validation" in ids and "approval" in ids  # 一般 stage 不受影響
