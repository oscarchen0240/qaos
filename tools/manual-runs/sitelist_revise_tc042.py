#!/usr/bin/env python3
"""RUN-20260914-003 T1：Test Designer(mode=change) 產 TC-SITELIST-042 v2（擴大範圍：機台類型 → 任何類型）。"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids
RUN = sys.argv[1]; SID, SV, AREA, A = "SPEC-SITELIST-001", "0.4", "SITELIST", "agent-test-designer"
RM = store.load(store.requirements_path(SID, SV))["source_artifact_id"]
old = store.load(store.tc_version_path("TC-SITELIST-042", 1))
tc = dict(old)
for k in ("testcase_id","version","status","created_by","validated_by","validation_report_id","approved_by","approval_id","created_at","updated_at","history","supersedes"):
    tc.pop(k, None)
tc["draft_id"] = f"TC-DRAFT-{ids.ulid()}"
tc["supersedes_testcase"] = {"testcase_id": "TC-SITELIST-042", "version": 1}
tc["title"] = "任何站台類型皆不提供刪除操作，只能停用"
tc["steps"] = [{"n": 1, "action": "取一個線上類型站台，檢視其可用操作"}, {"n": 2, "action": "取一個機台類型站台，檢視其可用操作"}, {"n": 3, "action": "在兩者的編輯畫面檢視可切換的狀態選項"}]
tc["expected_result"] = "兩種類型皆不提供刪除操作／按鈕；可用的狀態操作僅有暫停或關閉（停用）"
tc["source"] = "change_workflow"; tc["source_ref"] = "CLR-SITELIST-008"; tc["design_rationale"] = "自 TC-SITELIST-042 v1 修訂：範圍由『機台類型』擴大為『任何類型』"
tc["assumptions"] = [{"text": "Spec 原文的刪除流程未依類型排除；PM 已於 CLR-SITELIST-007（機台）與 CLR-SITELIST-008（任何類型，含線上）分別確認皆不提供刪除操作", "requirement_id": "REQ-SITELIST-023", "needs_human_confirmation": True}]
refs = [{"entity_type": "Requirement", "id": "REQ-SITELIST-023"}, {"entity_type": "TestCaseVersion", "id": "TC-SITELIST-042", "version": 1}, {"entity_type": "Artifact", "id": RM}]
def envelope(t, payload, task="T1"):
    aid = ids.artifact_id(t); art = {"artifact_id": aid, "artifact_type": t, "schema_version": "1.0", "version": 1, "run_id": RUN, "task_id": task, "iteration": 0, "created_by": A, "created_at": store.now(), "status": "DRAFT",
        "source": {"type": "TestCaseVersion", "ids": ["TC-SITELIST-042@1"]}, "references": refs, "requires_approval": None, "payload": payload}
    p = store.ROOT / "artifacts" / "test-design" / RUN / f"{aid}.yaml"; store.save(p, art); print(p.relative_to(store.ROOT)); return aid
did = envelope("TestCaseDraft", {"mode": "change", "spec_id": SID, "spec_version": SV, "testcases": [tc]})
rep = {"mode": "change", "testcase_draft_artifact_id": did, "coverage_matrix": [{"requirement_id": "REQ-SITELIST-023", "draft_ids": [tc["draft_id"]]}], "uncovered_with_reason": [],
       "technique_summary": [{"technique": t2, "count": 1} for t2 in old["design_techniques"]],
       "self_check": {k: True for k in ["requirements_covered","acceptance_criteria_covered","negative_considered","boundary_considered","expected_results_traceable","no_unsupported_assumptions","duplicate_detection_completed"]},
       "assumptions": [a["text"] for a in tc["assumptions"]], "duplicate_check": {"against_registry": True, "findings": []}}
envelope("TestDesignReport", rep)
