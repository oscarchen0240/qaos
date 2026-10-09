"""spec-to-bug：Bug Validator FAIL ×3 → HUMAN_OVERRIDE，以 override 強制通過 → bug VALIDATED → OPEN_BUG 核准 → run COMPLETED。
回歸：_route_back 已把 bug 退回 DRAFT，_after_override 不可再做 DRAFT → DRAFT（TransitionError）；
override 也要帶上 validator／report，否則 OPEN_BUG 核准時 Bug 的 validated_by／validation_report_id 為 None、不符 schema。
不依賴其他測試、也不寫入 session 共用的 root：在子程序中以 tmp_path 下的全新 QAOS root 執行，自行匯入專用的 SPEC-OVR-001，
由本 run 的 T0 建立 RequirementModel；單獨執行或任何執行順序結果都相同，也不影響其他測試的 Bug 數量斷言。"""
import contextlib, io, json, os, subprocess, sys
from tools.qaos import store, engine
from tools.qaos.cli import main as cli
from tests import helpers as H

SPEC, VER, BY = "SPEC-OVR-001", "1.0", "oscar@example.com"
SRC = {"type": "SpecVersion", "ids": [f"{SPEC}@{VER}"]}
CHECKS = ["violates_spec", "expected_has_spec_basis", "actual_supported_by_evidence", "reproduction_sufficient", "severity_reasonable", "priority_reasonable", "not_duplicate", "not_mere_ambiguity"]

def _spec_ref(loc, quote=""): return {"spec_id": SPEC, "spec_version": VER, "location": loc, "quote": quote}

def _requirement_model():
    req = {"requirement_id": "REQ-OVR-001", "version": 1, "spec_id": SPEC, "spec_version": VER, "type": "functional", "title": "優惠券每人限兌換一次",
           "statement": "同一張優惠券每位會員只能兌換一次", "acceptance_criteria": [
               {"ac_id": "AC-OVR-0011", "given": "會員已兌換過該優惠券", "when": "再次兌換同一張優惠券", "then": "系統拒絕並提示「已兌換」"}],
           "spec_reference": _spec_ref("§3.1 R1", "同一張優惠券每位會員只能兌換一次"), "ambiguity": None, "risk": "medium", "status": "DRAFT", "history": []}
    return {"spec_id": SPEC, "spec_version": VER, "requirements": [req], "traceability": [{"requirement_id": req["requirement_id"], "spec_reference": req["spec_reference"]}]}

def _bug_draft(evd):
    return {"draft_id": "BUG-DRAFT-01ARZ3NDEKTSV4RRFFQ69G5OVR", "title": "同一張優惠券可重複兌換", "product": "demo", "functional_area": "OVR",
            "severity_proposed": "major", "priority_proposed": "high", "severity_rationale": "優惠被重複使用", "environment": {"name": "stage"},
            "spec_id": SPEC, "spec_version": VER, "requirement_id": "REQ-OVR-001", "acceptance_criteria_ids": ["AC-OVR-0011"], "preconditions": ["會員已兌換過優惠券"],
            "reproduction_steps": ["再次兌換同一張優惠券"], "expected_result": "系統拒絕並提示「已兌換」", "expected_result_spec_reference": _spec_ref("§3.1 R1"),
            "actual_result": "第二次兌換同一張優惠券仍回傳兌換成功", "actual_result_evidence_map": [{"claim": "第二次兌換回 redeemed=true", "evidence_id": evd}],
            "evidence_ids": [evd], "impact": "優惠被重複使用", "suspected_area": "coupon api", "ambiguity_suspected": False, "duplicate_candidates": []}

def _fail_report(bd, evd):
    return {"result": "FAIL", "bug_draft_artifact_id": bd, "checks": {k: False for k in CHECKS},
            "issues": [{"testcase_id": "*", "issue_type": "other", "severity": "major", "violated_requirement": "REQ-OVR-001", "spec_reference": None,
                        "evidence": "e", "explanation": "重現步驟不足", "recommended_change": "補步驟"}],
            "evidence_verification": [{"evidence_id": evd, "hash_verified": True, "supports_claim": True}],
            "severity_assessment": {"severity_recommended": "major", "priority_recommended": "high", "agrees_with_analyst": True, "rationale": "同意"},
            "duplicate_check": {"searched": True, "duplicate_of": None}}

def _flow(fixtures):
    """在子程序執行（QAOS_ROOT 為全新 root）；任何斷言失敗都會讓子程序以非 0 結束。"""
    from tools.qaos import operation   # 全新 root 為 S_pre：與 conftest 相同，以正式流程進入移轉後狀態再開始
    operation.maintenance_start("test"); operation.migrate("test"); operation.maintenance_end("test")
    cli(["spec", "import", os.path.join(fixtures, "SPEC-OVR-001-v1.0.md"), "--spec-id", SPEC, "--version", VER, "--product", "demo", "--area", "OVR", "--by", BY])
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf): cli(["evidence", "add", "--type", "api_response", "--inline", '{"redeemed":true}', "--owner", "manual", "--description", "第二次兌換成功", "--by", BY])
    evd = buf.getvalue().strip().splitlines()[-1]
    rid = engine.new_run("spec-to-bug", {"spec_id": SPEC, "spec_version": VER, "actual_behavior": "同一張優惠券可重複兌換", "evidence_ids": [evd]}, BY)["run_id"]
    # T0：本 spec 尚無 RequirementModel → Spec Analyst 建立
    rm = _requirement_model(); refs_ = [{"entity_type": "SpecVersion", "id": SPEC, "version": VER}]
    sa = {"spec_id": SPEC, "spec_version": VER, "content_hash": store.load(store.spec_dir(SPEC) / "spec.yaml")["versions"][0]["content_hash"], "summary": "優惠券兌換規則",
          "scope": {"in_scope": ["兌換次數"], "out_of_scope": []}, "requirement_ids": ["REQ-OVR-001"], "ambiguities": [], "constraints": [], "edge_case_candidates": [], "open_questions": []}
    _, p1 = H.write_artifact(rid, "T0", "agent-spec-analyst", "SpecAnalysis", sa, refs_, SRC, "spec-analysis")
    _, p2 = H.write_artifact(rid, "T0", "agent-spec-analyst", "RequirementModel", rm, refs_, SRC, "requirements")
    assert engine.submit(rid, "T0", str(p1))[0] and engine.submit(rid, "T0", str(p2))[0] and engine.evaluate_gate(rid, "T0")["result"] == "PASS"
    assert engine.load_run(rid)["current_task_id"] == "T1"
    # Bug Analyst ⇄ Validator：FAIL ×3 → HUMAN_OVERRIDE
    for it in range(3):
        bd, p = H.write_artifact(rid, "T1", "agent-bug-analyst", "BugDraft", _bug_draft(evd), [{"entity_type": "Requirement", "id": "REQ-OVR-001"}, {"entity_type": "Evidence", "id": evd}],
                                 {"type": "Evidence", "ids": [evd]}, "bug-analysis", iteration=it)
        assert engine.submit(rid, "T1", str(p))[0] and engine.evaluate_gate(rid, "T1")["result"] == "PASS"
        _, p = H.write_artifact(rid, "T2", "agent-bug-validator", "BugValidationReport", _fail_report(bd, evd), [{"entity_type": "Artifact", "id": bd}, {"entity_type": "Evidence", "id": evd}],
                                {"type": "BugDraft", "ids": [bd]}, "validation", iteration=it)
        assert engine.submit(rid, "T2", str(p))[0] and engine.evaluate_gate(rid, "T2")["result"] == "FAIL"
    run = engine.load_run(rid); apr = store.load(f"approvals/{run['waiting_on_approval_id']}.yaml")
    assert apr["type"] == "HUMAN_OVERRIDE" and store.load(engine._bug_path(run))["status"] == "DRAFT"
    # override → VALIDATED → OPEN_BUG
    engine.approve(apr["approval_id"], "override", BY, rationale="人工確認 bug 成立")
    run = engine.load_run(rid); assert run["status"] == "WAITING_HUMAN" and store.load(engine._bug_path(run))["status"] == "PENDING_APPROVAL"
    assert store.load(f"approvals/{run['waiting_on_approval_id']}.yaml")["type"] == "OPEN_BUG"
    engine.approve(run["waiting_on_approval_id"], "approve", BY)
    run = engine.load_run(rid); assert run["status"] == "COMPLETED"
    b = store.load(store.find_bug(store.load(engine._bug_path(run))["bug_id"]))
    rep = engine._valid_outputs(engine._task(run, "T2"))["BugValidationReport"]["artifact_id"]
    assert b["bug_id"].startswith("BUG-OVR-") and b["status"] == "OPEN" and b["validated_by"] == "agent-bug-validator" and b["validation_report_id"] == rep
    assert [h["to_status"] for h in b["history"]][-6:] == ["VALIDATION_FAILED", "DRAFT", "VALIDATING", "VALIDATED", "PENDING_APPROVAL", "OPEN"]   # 不得出現 DRAFT → DRAFT
    print(json.dumps({"root": str(store.ROOT), "bug_id": b["bug_id"]}))

def test_90_bug_validator_fail_x3_then_override_opens_bug(tmp_path, fixtures):
    from tests.conftest import REPO, make_root
    root = make_root(tmp_path / "root")
    code = f"from tests.test_wf_zzzz_bug_override import _flow; _flow({str(fixtures)!r})"
    r = subprocess.run([sys.executable, "-c", code], cwd=REPO, env={**os.environ, "QAOS_ROOT": str(root), "PYTHONDONTWRITEBYTECODE": "1"},
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, f"{r.stdout}\n{r.stderr}"
    out = json.loads(r.stdout.strip().splitlines()[-1])
    assert out["root"] == str(root) and (root / "bugs" / "demo" / "OVR" / f"{out['bug_id']}.yaml").exists()   # 確實寫在獨立 root
    assert not list((store.ROOT / "bugs").rglob("BUG-OVR-*.yaml"))                                                  # session 共用的 root 未被寫入
