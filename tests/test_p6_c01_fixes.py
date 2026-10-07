"""P6 第 01 輪 Codex 審查（requirement-a-p6-code-review-01-retry1.md）的修正測試。狀態都以正式流程建立；錯誤只放在 agent 提交的報告中。"""
import json, pytest
from tests import p1_util as U
from tests.test_p6_cia_manual_flows import cia_py

CASES = {
    "legal":       "vcr = new",
    "missing":     "vcr = copy.deepcopy(new[:1])",                                                      # 漏列 TC-AUTH-002
    "foreign":     "vcr = copy.deepcopy(new); vcr[0]['draft_id'] = vcr[0]['draft_id'].replace('01BX', '01ZX')",   # 不屬於本輪 Draft
    "swapped":     "vcr = copy.deepcopy(new); a, b = vcr[0]['supersedes_testcase'], vcr[1]['supersedes_testcase']; vcr[0]['supersedes_testcase'], vcr[1]['supersedes_testcase'] = b, a",
    "old_version": "vcr = copy.deepcopy(new); vcr[0]['supersedes_testcase'] = dict(vcr[0]['supersedes_testcase'], version=vcr[0]['supersedes_testcase']['version'] + 1)",
}
EXTRA = {   # Designer 本輪多取代一張 CIR 判定 unaffected 的 TC（TC-AUTH-003），報告與 Draft 一致（P6-S01-01）
    "extra_unaffected": "base, _ = H.draft_set(prefix='01BX5ZZKBKACTAV9WEVGEMMVR'); o = store.load(store.tc_version_path('TC-AUTH-003', 1)); "
                        "x = copy.deepcopy(next(t for t in base if t['acceptance_criteria_ids'] == o['acceptance_criteria_ids'])); x['draft_id'] = x['draft_id'][:-1] + 'Z'; "
                        "x.update(source='change_workflow', supersedes_testcase={'testcase_id': 'TC-AUTH-003', 'version': 1}); extra = [x]",
}
CASES["extra_unaffected"] = "vcr = new"
EXPECT = {"extra_unaffected": "沒有把它判定為 affected／obsolete", "missing": "應恰好比較一次", "foreign": "不屬於 G-TVAL 審過的本輪 Draft", "swapped": "比較卻對到", "old_version": "不是 CIR 的 active_version"}

@pytest.mark.parametrize("case", list(CASES))
def test_c01_01_g_compare_checks_coverage_and_draft_identity(case):
    """P6-C01-01：同版本 CIA，T1 正確判定 TC-AUTH-001、002 affected，T2 重產兩份新版，T3 審本輪 Draft 並 PASS；
    T4 的比較報告漏列一張、引用不屬於本輪 Draft 的 draft_id、對錯取代關係、old_version 不是 CIR 的 active_version，
    或 Designer 多取代一張 CIR 判定 unaffected 的 TC（報告與 Draft 一致；P6-S01-01）→ G-COMPARE Structural FAIL，
    不建立 APPLY_CHANGE、TC 版本不變；完整且正確的報告 → PASS 並建立 APPLY_CHANGE。（compare helper 依 supersedes_testcase 組報告，錯誤只改報告內容。）"""
    root = U.mkroot(); U.import_auth_spec(root)
    U.py(root, "from tests import p3_flow as F\nF.full()")
    U.q(root, "spec", "reference", "declare-empty", "SPEC-AUTH-001@1.0", "--reason", "P6-C01-01", "--by", "oscar", check=True)
    out = cia_py(root, f"""
rid = cia_new("R001", "declaration_changed")
rmid = t0(rid, {{"REQ-AUTH-001": "密碼長度至少 8 碼（新判定）"}})
cir = cir_for(rid); cid, g1 = impact(rid, cir); assert g1["result"] == "PASS", g1
extra = []
{EXTRA.get(case, "")}
did, new = design(rid, cid, cir, "01BX5ZZKBKACTAV9WEVGEMMVR", extra=extra); validate(rid, did, rmid)
before = {{t: v for t, v, _ in active()}}
{CASES[case]}
_, g4 = compare(rid, cid, cir, vcr)
run = engine.load_run(rid); apr = run.get("waiting_on_approval_id")
print(json.dumps({{"affected": sorted(i["testcase_id"] for i in cir["testcase_impact"] if i["impact"] == "affected"), "g4": g4, "t4": engine._task(run, "T4")["status"],
                  "apr": store.load(f"approvals/{{apr}}.yaml")["type"] if apr else None, "same": before == {{t: v for t, v, _ in active()}}}}, default=str))""")
    assert out["affected"] == ["TC-AUTH-001", "TC-AUTH-002"], out
    if case == "legal":
        assert out["g4"]["result"] == "PASS", out["g4"]
        assert out["apr"] == "APPLY_CHANGE"
    else:
        assert out["g4"]["result"] == "FAIL" and out["g4"]["layer"] == "structural", out["g4"]
        assert any(EXPECT[case] in i for i in out["g4"]["issues"]), out["g4"]["issues"]
        assert out["t4"] == "READY" and out["apr"] is None and out["same"]
