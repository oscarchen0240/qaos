#!/usr/bin/env python3
"""RUN-20260918-006 T1（testcase-revision）：依CLR-DAILYREPORT-009的PM回覆修正TC-DAILYREPORT-046。
原TC假設「未兌現金額不受結算日期範圍限制」，經CLR-DAILYREPORT-009正式推翻：未兌現金額仍受
結算日期範圍限制（只是不受統計週期切分本身影響），PM並提供具體算例佐證。斷言方向需整條反過來。
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids

RUN = "RUN-20260918-006"
RM_AID = "ART-RM-01M2D72FB77WAP7PFRAKC54QCR"
SID, SV, AREA, A = "SPEC-DAILYREPORT-001", "0.1", "DAILYREPORT", "agent-test-designer"
OLD_TC = "TC-DAILYREPORT-046"

def sr(loc, q=""):
    return {"spec_id": SID, "spec_version": SV, "location": loc, "quote": q[:300]}

tc = {
    "draft_id": f"TC-DRAFT-{ids.ulid()}",
    "title": "未兌現金額仍受結算日期範圍限制，範圍外的未兌現收據不計入",
    "product": "ba-admin", "functional_area": AREA,
    "requirement_ids": ["REQ-DAILYREPORT-015"], "acceptance_criteria_ids": ["AC-DAILYREPORT-0152"],
    "spec_id": SID, "spec_version": SV, "test_level": "ui_e2e", "test_types": ["negative"],
    "design_techniques": ["equivalence_partitioning"],
    "priority": "high", "risk": "high", "execution_mode": "manual",
    "preconditions": [
        "已登入後台並切換至機台場館站台（Arcade）", "進入 各式報表 > 場館日結報表",
        "測試場館已設定日結時間 06:00 UTC+0",
        "測試場館下有機台 A、B（會員編號已知），並依案例準備交易資料",
        "存在一筆結算日期為 09-10 的未兌現收據 200",
    ],
    "test_data": [{"name": "未兌現收據金額", "value": 200}, {"name": "收據結算日期", "value": "2026-09-10"}],
    "steps": [
        {"n": 1, "action": "以結算日期範圍 09-03～09-09（不含 09-10）、按週統計搜尋，記錄 09-07～09-09 與 09-03～09-06 兩列的未兌現金額"},
        {"n": 2, "action": "改以結算日期範圍 09-03～09-10（含 09-10）、按週統計搜尋，記錄 09-07～09-10 與 09-03～09-06 兩列的未兌現金額"},
    ],
    "expected_result": (
        "第一次查詢（範圍不含 09-10）：未兌現金額不包含這筆 200，09-07～09-09 列與 09-03～09-06 列皆不反映此筆收據；"
        "第二次查詢（範圍含 09-10）：09-07～09-10 這一列的未兌現金額包含這筆 200（較第一次同週次的未兌現金額多 200）。"
        "驗證未兌現金額仍以結算日期範圍為篩選條件，範圍外的未兌現收據不會被計入——『不受週期影響、累計至查詢當下』"
        "指的是不受『週期切分方式』影響（不會因為切成週而被打散或重複計算），不是不受『結算日期範圍』這個篩選條件限制"
    ),
    "expected_result_spec_reference": sr(
        "§列表欄位附註（此節已由 CLR-DAILYREPORT-009 補充精確定義）",
        "未兌現金額：不受統計週期切分影響，累計至查詢當下；結算日期範圍仍是篩選條件，未兌現金額只計範圍內"
    ),
    "assumptions": [],
    "automation_status": "not_automated", "ci_eligible": False, "hotfix_eligible": True,
    "execution_cost": "medium", "stability": "unknown", "critical_path": True, "source": "change_workflow",
    "supersedes_testcase": {"testcase_id": OLD_TC, "version": 1},
    "source_ref": "CLR-DAILYREPORT-009",
    "design_rationale": (
        "自 TC-DAILYREPORT-046 v1 修訂：v1 的 expected_result 明確寫『依假設：不受結算日期範圍限制』，"
        "該假設當初由 APR-0003 標記為 needs_human_confirmation=false（視為已確認），但 CLR-DAILYREPORT-009"
        "的PM正式回覆推翻了這個假設——未兌現金額仍受結算日期範圍限制，只是不受統計週期切分本身影響"
        "（例：9/10未兌現200，結算範圍09-03~09-09時該筆不計入任何一列，結算範圍09-03~09-10時才計入"
        "09-07~09-10這一列）。改用『同一筆收據、兩種結算範圍前後對照』的equivalence_partitioning設計，"
        "直接對比範圍含/不含該筆收據時的差異，比原本單一情境的斷言更能驗證『範圍才是篩選依據』這個"
        "修正後的正確機制，同時保留PM提供的具體算例作為expected_result的精確依據，不再是需要"
        "needs_human_confirmation的假設。"
    ),
}

rep = {
    "mode": "change", "testcase_draft_artifact_id": None,
    "coverage_matrix": [{
        "requirement_id": "REQ-DAILYREPORT-015", "draft_ids": [tc["draft_id"]],
        "acceptance_criteria": [{"ac_id": "AC-DAILYREPORT-0152", "draft_ids": [tc["draft_id"]]}],
    }],
    "uncovered_with_reason": [],
    "technique_summary": [{"technique": "equivalence_partitioning", "count": 1}],
    "self_check": {k: True for k in [
        "requirements_covered", "acceptance_criteria_covered", "negative_considered", "boundary_considered",
        "expected_results_traceable", "no_unsupported_assumptions", "duplicate_detection_completed"]},
    "assumptions": [], "duplicate_check": {"against_registry": True, "findings": []},
}

def envelope(t, payload, refs, task="T1"):
    aid = ids.artifact_id(t)
    art = {
        "artifact_id": aid, "artifact_type": t, "schema_version": "1.0", "version": 1, "run_id": RUN,
        "task_id": task, "iteration": 0, "created_by": A, "created_at": store.now(), "status": "DRAFT",
        "source": {"type": "TestCaseVersion", "ids": [OLD_TC]}, "references": refs,
        "requires_approval": None, "payload": payload,
    }
    p = store.ROOT / "artifacts" / "test-design" / RUN / f"{aid}.yaml"
    store.save(p, art)
    return aid, p

refs = [{"entity_type": "Requirement", "id": "REQ-DAILYREPORT-015"}, {"entity_type": "TestCase", "id": OLD_TC}, {"entity_type": "Artifact", "id": RM_AID}]
did, p1 = envelope("TestCaseDraft", {"mode": "change", "spec_id": SID, "spec_version": SV, "testcases": [tc]}, refs)
rep["testcase_draft_artifact_id"] = did
_, p2 = envelope("TestDesignReport", rep, [{"entity_type": "Artifact", "id": did}])
print(p1.relative_to(store.ROOT))
print(p2.relative_to(store.ROOT))
