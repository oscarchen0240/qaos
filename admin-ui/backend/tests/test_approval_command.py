"""A6 稽核 Top 10：tickets.approval_command 指令組裝與警告。"""


def test_per_item_reject_with_reason_goes_into_rationale(sandbox, write_run, write_approval):
    write_run("RUN-A", "WAITING_HUMAN", "T4", [("T4", "RUNNING", None)])
    write_approval("APR-A", "RUN-A", batch_items=[{"id": "TC-X-001", "version": 1}, {"id": "TC-X-002", "version": 1}])
    draft = {"decision": "approve", "per_item": {"TC-X-001": {"decision": "reject", "reason": "步驟2缺前置"}}}
    out = sandbox.tickets.approval_command("APR-A", draft)
    assert "--per-item TC-X-001:reject" in out["command"]
    assert "退回：TC-X-001：步驟2缺前置" in out["command"]
    assert out["rejected"] == ["TC-X-001"]
    assert out["warnings"] == []


def test_all_rejected_but_decision_approve_warns(sandbox, write_run, write_approval):
    write_run("RUN-B", "WAITING_HUMAN", "T4", [("T4", "RUNNING", None)])
    write_approval("APR-B", "RUN-B", batch_items=[{"id": "TC-Y-001", "version": 1}])
    draft = {"decision": "approve", "per_item": {"TC-Y-001": {"decision": "reject", "reason": "不採用"}}}
    out = sandbox.tickets.approval_command("APR-B", draft)
    assert any("整批退回請把整體決定改成" in w for w in out["warnings"])


def test_override_without_rationale_warns(sandbox, write_run, write_approval):
    write_run("RUN-C", "WAITING_HUMAN", "T4", [("T4", "RUNNING", None)])
    write_approval("APR-C", "RUN-C")
    out = sandbox.tickets.approval_command("APR-C", {"decision": "override"})
    assert "override 需要 --rationale" in out["warnings"]
    out2 = sandbox.tickets.approval_command("APR-C", {"decision": "override", "rationale": "設計已足夠周延"})
    assert "override 需要 --rationale" not in out2["warnings"]


def test_missing_reject_reason_warns_with_count(sandbox, write_run, write_approval):
    write_run("RUN-D", "WAITING_HUMAN", "T4", [("T4", "RUNNING", None)])
    write_approval("APR-D", "RUN-D", batch_items=[{"id": "TC-Z-001", "version": 1}, {"id": "TC-Z-002", "version": 1}])
    draft = {"decision": "approve", "per_item": {"TC-Z-001": {"decision": "reject"}, "TC-Z-002": {"decision": "reject"}}}
    out = sandbox.tickets.approval_command("APR-D", draft)
    assert any("未填理由" in w and "共 2 條" in w for w in out["warnings"])


def test_reject_with_per_item_but_decision_not_approve_warns(sandbox, write_run, write_approval):
    write_run("RUN-E", "WAITING_HUMAN", "T4", [("T4", "RUNNING", None)])
    write_approval("APR-E", "RUN-E", batch_items=[{"id": "TC-W-001", "version": 1}])
    draft = {"decision": "reject", "per_item": {"TC-W-001": {"decision": "reject", "reason": "x"}}}
    out = sandbox.tickets.approval_command("APR-E", draft)
    assert any("只在 --decision approve 時有意義" in w for w in out["warnings"])
