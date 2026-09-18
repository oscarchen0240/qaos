"""A6 稽核 Top 14：autoreports.runs_for_group / main_run（依 spec 編號精確對應，BONUSCCY-001/002/003 不混）。"""


def test_runs_for_group_does_not_mix_sibling_specs(full_sandbox, write_run):
    """曾出過的真實 bug：舊版只看功能區前綴，會把 BONUSCCY-001/002/003 混在一起。
    新版必須精確對應：BONUSCCY-002 的群組只認 SPEC-BONUSCCY-002 的 run。"""
    write_run("RUN-A", "COMPLETED", "T5", [("T5", "DONE", None)], spec_id="SPEC-BONUSCCY-001")
    write_run("RUN-B", "COMPLETED", "T5", [("T5", "DONE", None)], spec_id="SPEC-BONUSCCY-002")
    write_run("RUN-C", "COMPLETED", "T5", [("T5", "DONE", None)], spec_id="SPEC-BONUSCCY-003")
    out = full_sandbox.autoreports.runs_for_group("BONUSCCY-002")
    ids = {r["run_id"] for r in out}
    assert ids == {"RUN-B"}


def test_runs_for_group_area_only_key_matches_dash001(full_sandbox, write_run):
    """CASHFLOW（無編號後綴）的群組要認 SPEC-CASHFLOW-001。"""
    write_run("RUN-D", "COMPLETED", "T5", [("T5", "DONE", None)], spec_id="SPEC-CASHFLOW-001")
    out = full_sandbox.autoreports.runs_for_group("CASHFLOW")
    assert {r["run_id"] for r in out} == {"RUN-D"}


def test_runs_for_group_includes_revision_runs_by_area_prefix(full_sandbox, write_run):
    """testcase-revision 沒有 spec_id，只能靠功能區前綴（testcase_id）納入，且不排除其他 spec-to-testcase run。"""
    write_run("RUN-E", "COMPLETED", "T5", [("T5", "DONE", None)], spec_id="SPEC-BONUSCCY-002")
    write_run("RUN-F", "COMPLETED", None, [], workflow_id="testcase-revision", testcase_id="TC-BONUSCCY-045")
    out = full_sandbox.autoreports.runs_for_group("BONUSCCY-002")
    assert {r["run_id"] for r in out} == {"RUN-E", "RUN-F"}


def test_main_run_prefers_phase3(full_sandbox, write_run, write_shadow_doc):
    """主 run＝Phase 3 spec-to-testcase run（整合線起點），不是最新完成的那條。"""
    write_run("RUN-20260913-001", "COMPLETED", "T5", [("T5", "DONE", None)], spec_id="SPEC-AREA-007")
    write_run("RUN-20260915-001", "COMPLETED", "T5", [("T5", "DONE", None)], spec_id="SPEC-AREA-007")
    write_shadow_doc("area-007", ["RUN-20260915-001"], "整合完成。")
    runs = full_sandbox.autoreports.runs_for_group("AREA-007")
    main = full_sandbox.autoreports.main_run(runs)
    assert main["run_id"] == "RUN-20260915-001"


def test_main_run_falls_back_to_latest_completed_when_no_phase3_doc(full_sandbox, write_run):
    """沒有 shadow 文件可判定 Phase 3 時，退而求其次取最新完成的 spec-to-testcase run。"""
    write_run("RUN-20260913-001", "COMPLETED", "T5", [("T5", "DONE", None)], spec_id="SPEC-AREA-008")
    out = full_sandbox.autoreports.runs_for_group("AREA-008")
    main = full_sandbox.autoreports.main_run(out)
    assert main["run_id"] == "RUN-20260913-001"
