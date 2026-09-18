"""A6 稽核 Top 11：tickets._activation_context 與 _recommendation（shadow 文件解析、交叉比對守門）。"""


def _approval_detail(sandbox, apr_id: str):
    return sandbox.tickets.approval_detail(apr_id)


def test_no_phase2_active_means_no_review_needed(full_sandbox, write_run, write_approval):
    """同 spec 沒有既有 ACTIVE TC（新 spec）→ context 仍回傳，但 phase2_active=0、needs_review=False（沒東西好守）。"""
    write_run("RUN-20260918-001", "WAITING_HUMAN", "T4", [("T4", "RUNNING", None)], spec_id="SPEC-NEWAREA-001")
    write_approval("APR-A", "RUN-20260918-001", batch_items=[{"id": "TC-NEWAREA-001", "version": 1}])
    ctx = _approval_detail(full_sandbox, "APR-A")["context"]
    assert ctx["phase2_active"] == 0
    assert ctx["needs_review"] is False
    assert ctx["recommendation"] is None


def test_needs_review_when_phase2_active_and_no_shadow_doc(full_sandbox, write_run, write_approval, write_registry_tc):
    """有 Phase 2 ACTIVE、但沒有 shadow 文件點名這個 run → needs_review=True、cross_compared=False。"""
    write_registry_tc("TC-AREA-001", 1, "SPEC-AREA-001")
    write_run("RUN-20260918-002", "WAITING_HUMAN", "T4", [("T4", "RUNNING", None)], spec_id="SPEC-AREA-001")
    write_approval("APR-B", "RUN-20260918-002", batch_items=[{"id": "TC-AREA-050", "version": 1}])
    ctx = _approval_detail(full_sandbox, "APR-B")["context"]
    assert ctx["phase2_active"] == 1
    assert ctx["cross_compared"] is False
    assert ctx["needs_review"] is True
    assert ctx["recommendation"] is None


def test_per_item_pattern_recommendation(full_sandbox, write_run, write_approval, write_registry_tc, write_shadow_doc):
    """文件用 --per-item 指令寫法：能解析出採用清單並標 cross_compared。"""
    write_registry_tc("TC-AREA-001", 1, "SPEC-AREA-001")
    write_run("RUN-20260918-003", "WAITING_HUMAN", "T4", [("T4", "RUNNING", None)], spec_id="SPEC-AREA-001")
    write_approval("APR-C", "RUN-20260918-003", batch_items=[{"id": "TC-AREA-048", "version": 1}, {"id": "TC-AREA-051", "version": 1}, {"id": "TC-AREA-060", "version": 1}])
    write_shadow_doc("area", ["RUN-20260918-003"], "**最終處置**：用 `bin/qaos approve APR-C --decision reject --per-item TC-AREA-048:approve --per-item TC-AREA-051:approve`")
    ctx = _approval_detail(full_sandbox, "APR-C")["context"]
    assert ctx["cross_compared"] is True
    rec = ctx["recommendation"]
    assert rec["found"] is True
    assert sorted(rec["adopt"]) == ["TC-AREA-048", "TC-AREA-051"]
    assert rec["reject"] == ["TC-AREA-060"]


def test_listed_pattern_recommendation_with_bare_numbers(full_sandbox, write_run, write_approval, write_registry_tc, write_shadow_doc):
    """文件用「保留／採用 TC-…、051」這種列舉寫法（含裸數字，補回 area 前綴）。"""
    write_registry_tc("TC-PLATFORMRULE-001", 1, "SPEC-PLATFORMRULE-001")
    write_run("RUN-20260918-004", "WAITING_HUMAN", "T4", [("T4", "RUNNING", None)], spec_id="SPEC-PLATFORMRULE-001")
    write_approval("APR-D", "RUN-20260918-004", batch_items=[{"id": "TC-PLATFORMRULE-048", "version": 1}, {"id": "TC-PLATFORMRULE-051", "version": 1}, {"id": "TC-PLATFORMRULE-060", "version": 1}])
    write_shadow_doc("platformrule", ["RUN-20260918-004"], "僅保留TC-PLATFORMRULE-048、051這2條新增TC，其餘30條Phase3草稿退役。")
    rec = _approval_detail(full_sandbox, "APR-D")["context"]["recommendation"]
    assert rec["found"] is True
    assert sorted(rec["adopt"]) == ["TC-PLATFORMRULE-048", "TC-PLATFORMRULE-051"]
    assert "TC-PLATFORMRULE-060" in rec["reject"]


def test_undecipherable_doc_reports_not_found(full_sandbox, write_run, write_approval, write_registry_tc, write_shadow_doc):
    """文件存在但沒有可辨識的採用清單寫法 → found=False，附原因。"""
    write_registry_tc("TC-AREA-001", 1, "SPEC-AREA-001")
    write_run("RUN-20260918-005", "WAITING_HUMAN", "T4", [("T4", "RUNNING", None)], spec_id="SPEC-AREA-001")
    write_approval("APR-E", "RUN-20260918-005", batch_items=[{"id": "TC-AREA-070", "version": 1}])
    write_shadow_doc("area", ["RUN-20260918-005"], "這次分析很仔細，細節請看附件。")
    rec = _approval_detail(full_sandbox, "APR-E")["context"]["recommendation"]
    assert rec["found"] is False
    assert rec["note"]


def test_overlap_hint_by_shared_requirement_id(full_sandbox, write_run, write_approval, write_registry_tc):
    """新 TC 與既有 ACTIVE TC 共用需求編號 → overlap 提示列出既有 TC。"""
    write_registry_tc("TC-AREA-001", 1, "SPEC-AREA-001", requirement_ids=["REQ-AREA-001"])
    write_run("RUN-20260918-006", "WAITING_HUMAN", "T4", [("T4", "RUNNING", None)], spec_id="SPEC-AREA-001")
    write_approval("APR-F", "RUN-20260918-006", batch_items=[{"id": "TC-AREA-099", "version": 1}])
    write_registry_tc("TC-AREA-099", 1, "SPEC-AREA-001", requirement_ids=["REQ-AREA-001"])
    ctx = _approval_detail(full_sandbox, "APR-F")["context"]
    assert ctx["overlap_count"] == 1
    assert ctx["overlap"]["TC-AREA-099"] == ["TC-AREA-001"]
