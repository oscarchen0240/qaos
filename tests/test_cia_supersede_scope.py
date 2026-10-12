"""spec-change-impact 的取代範圍與 G-COMPARE 失敗出路（RUN-20261012-001 事故：T2 修訂了 CIR 判定 unaffected 的 TC，到 T4 G-COMPARE 才 FAIL，
且 T4 沒有路徑退回 T2，只能取消 run）。

1. G-DESIGN（change 模式、run 有 CIR）以 gates.supersede_scope_issues 擋下取代範圍外的 Draft：取代 unaffected／obsolete、版本不是 CIR 的 active_version、
   同一張 TC 被多筆 Draft 取代；合法取代 affected TC 不受影響。
2. G-COMPARE 只剩 Draft 超出 CIR 範圍的問題（T4 重交報告也修不好）→ 建立 HUMAN_OVERRIDE：override 進 APPLY_CHANGE、reject 退回 T2 再給一次迭代、cancel 取消 run；
   報告本身仍有問題時維持只寫診斷的 READY 重試。修正前已通過 G-DESIGN 的 Draft 以暫時停用 G-DESIGN 模擬。
3. spec-change-impact 的 G-TVAL 迭代超限 override 後，ChangeImpact 必須進入 COMPARING，T5 才建得出 APPLY_CHANGE。
狀態一律以正式流程建立（同 test_p6_c01_fixes.py）。"""
import json, pytest
from tests import p1_util as U
from tests.test_p6_cia_manual_flows import cia_py

P1, P2 = "01BX5ZZKBKACTAV9WEVGEMMVR", "01BX5ZZKBKACTAV9WEVGEMMVS"
HELPERS = """
def extra_sup(tc_id, ver=1, prefix=P1):
    '''Designer 多取代一張 TC（以 draft_set 中對應 AC 的案例改寫，draft_id 末碼改 Z 避免與本輪其他稿相同）。'''
    base, _ = H.draft_set(prefix=prefix); o = store.load(store.tc_version_path(tc_id, ver))
    x = copy.deepcopy(next(t for t in base if t['acceptance_criteria_ids'] == o['acceptance_criteria_ids'])); x['draft_id'] = x['draft_id'][:-1] + 'Z'
    x.update(source='change_workflow', supersedes_testcase={'testcase_id': tc_id, 'version': ver}); return x
def design_g(rid, cid, cir, prefix, it=0, extra=(), mutate=None):
    '''同 design()，但回傳 G-DESIGN 結果而不要求 PASS；mutate(new) 在提交前改動 Draft。'''
    base, _ = H.draft_set(prefix=prefix); H.legacy_acs(base, set(rm.ac_history(SPEC)["owners"])); new = []
    for i in cir["testcase_impact"]:
        if i["impact"] != "affected": continue
        old = store.load(store.tc_version_path(i["testcase_id"], i["active_version"]))
        d = copy.deepcopy(next(x for x in base if x["acceptance_criteria_ids"] == old["acceptance_criteria_ids"]))
        d.update(source="change_workflow", supersedes_testcase={"testcase_id": i["testcase_id"], "version": i["active_version"]}); new.append(d)
    new += [copy.deepcopy(x) for x in extra]
    if mutate: mutate(new)
    rids = sorted({r for t in new for r in t["requirement_ids"]})
    did, pd = H.write_artifact(rid, "T2", "agent-test-designer", "TestCaseDraft", {"mode": "change", "spec_id": SPEC, "spec_version": "1.0", "change_impact_id": cir["change_impact_id"], "testcases": new},
                               [{"entity_type": "Requirement", "id": r} for r in rids] + [{"entity_type": "Artifact", "id": cid}], {"type": "ChangeImpactReport", "ids": [cid]}, "test-design", iteration=it)
    rep = H.design_report(did, new); rep["mode"] = "change"
    _, pr = H.write_artifact(rid, "T2", "agent-test-designer", "TestDesignReport", rep, [{"entity_type": "Artifact", "id": did}], {"type": "TestCaseDraft", "ids": [did]}, "test-design", iteration=it)
    assert engine.submit(rid, "T2", str(pd))[0] and engine.submit(rid, "T2", str(pr))[0]
    return did, new, engine.evaluate_gate(rid, "T2")
def legacy_design(rid, cid, cir, prefix, extra):
    '''修正前的 G-DESIGN 不核對取代範圍：本次 T2 的 gate 暫時停用，讓範圍外的 Draft 進入 T3／T4（模擬事故時已在途中的 run）。'''
    orig = gates.GATES["G-DESIGN"]; gates.GATES["G-DESIGN"] = lambda *a: []
    try: return design(rid, cid, cir, prefix, extra=extra)
    finally: gates.GATES["G-DESIGN"] = orig
def start():
    rid = cia_new("R001", "declaration_changed")
    rmid = t0(rid, {"REQ-AUTH-001": "密碼長度至少 8 碼（新判定）"})
    return rid, rmid
def ci(rid): return store.load(f"runs/{rid}/entities/change-impact.yaml")["status"]
def tasks(rid): return {t["task_id"]: [t["status"], t["iteration"]] for t in engine.load_run(rid)["tasks"]}
def waiting(rid):
    a = engine.load_run(rid).get("waiting_on_approval_id")
    return (a, store.load(f"approvals/{a}.yaml")) if a else (None, None)
"""

def _root():
    root = U.mkroot(); U.import_auth_spec(root)
    U.py(root, "from tests import p3_flow as F\nF.full()")
    U.q(root, "spec", "reference", "declare-empty", "SPEC-AUTH-001@1.0", "--reason", "CIA supersede scope", "--by", "oscar", check=True)
    return root

def run_cia(root, body):
    return cia_py(root, f"P1, P2 = {P1!r}, {P2!r}\n" + HELPERS + body)

DESIGN_CASES = {   # (CIR 改判, Draft 的額外取代／改動, 預期訊息)
    "legal":      ("", "", None),
    "unaffected": ("", "extra = [extra_sup('TC-AUTH-003')]", "CIR 把它判定為 unaffected"),
    "obsolete":   ("o = next(i for i in cir['testcase_impact'] if i['testcase_id'] == 'TC-AUTH-003'); o.update(impact='obsolete', reason='需求刪除'); "
                   "cir['summary'].update(testcases_obsolete=1, testcases_unaffected=cir['summary']['testcases_unaffected'] - 1)",
                   "extra = [extra_sup('TC-AUTH-003')]", "obsolete 只列入 retire 建議，不得重產"),
    "obsolete_not_reproduced": ("o = next(i for i in cir['testcase_impact'] if i['testcase_id'] == 'TC-AUTH-003'); o.update(impact='obsolete', reason='需求刪除'); "
                                "cir['summary'].update(testcases_obsolete=1, testcases_unaffected=cir['summary']['testcases_unaffected'] - 1)", "", None),
    "version":    ("", "mutate = lambda new: new[0]['supersedes_testcase'].update(version=new[0]['supersedes_testcase']['version'] + 1)", "必須等於 CIR 的 active_version"),
    "duplicate":  ("", "def mutate(new):\n    x = copy.deepcopy(new[0]); x['draft_id'] = x['draft_id'][:-1] + 'Y'; x['title'] += '（重複取代）'; new.append(x)", "一張 TC 只能有一個新版本"),
}

@pytest.mark.parametrize("case", list(DESIGN_CASES))
def test_g_design_blocks_superseding_tc_outside_cir_affected(case):
    """change 模式：Draft 取代 CIR 判定 unaffected／obsolete 的 TC、取代版本不是 CIR 的 active_version、同一張 TC 被兩筆 Draft 取代 → G-DESIGN Structural FAIL，
    指出 Draft 與 TC，T2 維持 READY 讓 Designer 修正（不會一路走到 G-COMPARE）。只合法取代 affected TC（含 CIR 另有 obsolete、但 Draft 沒有重產它）→ PASS。"""
    cir_edit, draft_edit, expect = DESIGN_CASES[case]
    out = run_cia(_root(), f"""
rid, rmid = start()
cir = cir_for(rid)
{cir_edit}
cid, g1 = impact(rid, cir); assert g1["result"] == "PASS", g1
extra, mutate = [], None
{draft_edit}
did, new, g = design_g(rid, cid, cir, P1, extra=extra, mutate=mutate)
print(json.dumps({{"g": g, "t2": tasks(rid)["T2"], "cur": engine.load_run(rid)["current_task_id"]}}, default=str))""")
    if expect is None:
        assert out["g"]["result"] == "PASS", out["g"]
        assert out["t2"][0] == "DONE" and out["cur"] == "T3"
    else:
        assert out["g"]["result"] == "FAIL" and out["g"]["layer"] == "structural", out["g"]
        assert any(expect in i for i in out["g"]["issues"]), out["g"]["issues"]
        assert out["t2"][0] == "READY"
        if case in ("unaffected", "obsolete"): assert any("TC-AUTH-003" in i for i in out["g"]["issues"])

ESCALATE = """
rid, rmid = start()
cir = cir_for(rid); cid, g1 = impact(rid, cir); assert g1["result"] == "PASS", g1
did, new = legacy_design(rid, cid, cir, P1, [extra_sup('TC-AUTH-003')]); validate(rid, did, rmid)
mat = [[r["id"], r["version"]] for r in engine._task(engine.load_run(rid), "T3")["input_entity_refs"]]
_, g_both = compare(rid, cid, cir, new[:-1])                 # 報告漏比較 TC-AUTH-003 那筆：報告本身也有問題 → 只寫診斷
both = {"g": g_both, "t4": tasks(rid)["T4"], "apr": waiting(rid)[0], "status": engine.load_run(rid)["status"]}
_, g4 = compare(rid, cid, cir, new)                          # 報告與 Draft 一致：只剩 Draft 超出 CIR 範圍 → HUMAN_OVERRIDE
apr, a = waiting(rid)
esc = {"g": g4, "t4": tasks(rid)["T4"], "type": a["type"], "options": [o["key"] for o in a["options"]], "reopen": a.get("diff_summary"),
       "arts": a["artifact_ids"], "draft": did, "ci": ci(rid), "status": engine.load_run(rid)["status"]}
"""

def test_g_compare_scope_failure_escalates_then_reject_back_to_t2():
    """G-COMPARE：報告本身也有問題時維持只寫診斷的 READY 重試（不建核准單）；報告修好、只剩 Draft 超出 CIR 範圍 → Structural FAIL 並建立 HUMAN_OVERRIDE
    （override／reject／cancel，reopen_task=T2），T4 停在 GATE_FAILED。選 reject：本輪 VALIDATED 版本撤回 DRAFT、ChangeImpact 回 TEST_UPDATE_REQUIRED、
    T2 進入 iteration 1、T3／T4 重設；Designer 重做合法 Draft 後走完 T3、T4、APPLY_CHANGE，run COMPLETED、ChangeImpact APPLIED，unaffected 的 TC-AUTH-003 不變。"""
    out = run_cia(_root(), ESCALATE + """
engine.approve(apr, "reject", BY, rationale="退回 T2，不得重產 unaffected", new_request=True)
back = {"tasks": tasks(rid), "cur": engine.load_run(rid)["current_task_id"], "status": engine.load_run(rid)["status"], "ci": ci(rid),
        "mat": [[t, v, store.load(store.tc_version_path(t, v))["status"], next(x["status"] for x in store.load(store.tc_pointer_path(t))["versions"] if x["version"] == v)] for t, v in mat],
        "t3refs": engine._task(engine.load_run(rid), "T3")["input_entity_refs"]}
did2, new2, g2 = design_g(rid, cid, cir, P2, it=1); assert g2["result"] == "PASS", g2
validate(rid, did2, rmid, it=1); _, g4b = compare(rid, cid, cir, new2, it=1)
apr2, a2 = waiting(rid); t5 = a2["type"]
engine.approve(apr2, "approve", BY, rationale="套用", new_request=True)
print(json.dumps({"both": both, "esc": esc, "back": back, "g4b": g4b, "t5": t5, "status": engine.load_run(rid)["status"], "ci": ci(rid),
                  "vers": {t: v for t, v, _ in active()}}, default=str))""")
    b, e, k = out["both"], out["esc"], out["back"]
    assert b["g"]["result"] == "FAIL" and any("應恰好比較一次" in i for i in b["g"]["issues"]), b
    assert b["t4"][0] == "READY" and b["apr"] is None and b["status"] == "RUNNING"
    assert e["g"]["result"] == "FAIL" and e["g"]["layer"] == "structural" and e["g"]["approval_id"]
    assert e["g"]["issues"] and all("TC-AUTH-003" in i and "unaffected" in i for i in e["g"]["issues"]), e["g"]["issues"]
    assert e["t4"][0] == "GATE_FAILED" and e["type"] == "HUMAN_OVERRIDE" and e["options"] == ["override", "reject", "cancel"]
    assert e["reopen"] == "reopen_task=T2" and e["draft"] in e["arts"] and e["status"] == "WAITING_HUMAN" and e["ci"] == "COMPARING"
    assert k["status"] == "RUNNING" and k["cur"] == "T2" and k["tasks"]["T2"] == ["READY", 1]
    assert k["tasks"]["T3"][0] == "PENDING" and k["tasks"]["T4"][0] == "PENDING" and k["ci"] == "TEST_UPDATE_REQUIRED"
    assert len(k["mat"]) == 3 and all(m[2] == "DRAFT" and m[3] == "DRAFT" for m in k["mat"]), k["mat"]
    assert k["t3refs"] == []
    assert out["g4b"]["result"] == "PASS", out["g4b"]
    assert out["t5"] == "APPLY_CHANGE" and out["status"] == "COMPLETED" and out["ci"] == "APPLIED"
    assert out["vers"]["TC-AUTH-001"] == 3 and out["vers"]["TC-AUTH-002"] == 3 and out["vers"]["TC-AUTH-003"] == 1, out["vers"]

def test_g_compare_scope_failure_override_proceeds_to_apply_change():
    """HUMAN_OVERRIDE 選 override（需 rationale）：視為 G-COMPARE 通過，T4 DONE，建立 APPLY_CHANGE（ChangeImpact PENDING_APPROVAL）；核准後 Draft 的取代全部落地。"""
    out = run_cia(_root(), ESCALATE + """
try: engine.approve(apr, "override", BY, rationale="", new_request=True); no_rationale = None
except engine.EngineError as ex: no_rationale = str(ex)
engine.approve(apr, "override", BY, rationale="TC-AUTH-003 的修訂經人工確認可接受", new_request=True)
apr2, a2 = waiting(rid); mid = {"t4": tasks(rid)["T4"], "type": a2["type"], "ci": ci(rid), "items": sorted(i["id"] for i in a2["batch_items"])}
engine.approve(apr2, "approve", BY, rationale="套用", new_request=True)
run = engine.load_run(rid); summ = store.load(store.find_artifact(run["summary_artifact_id"]))["payload"]
print(json.dumps({"esc": esc, "no_rationale": no_rationale, "mid": mid, "status": run["status"], "ci": ci(rid), "vers": {t: v for t, v, _ in active()},
                  "overrides": summ["overrides"], "apr": apr}, default=str))""")
    assert out["esc"]["type"] == "HUMAN_OVERRIDE" and "rationale" in out["no_rationale"]
    assert out["mid"]["t4"][0] == "DONE" and out["mid"]["type"] == "APPLY_CHANGE" and out["mid"]["ci"] == "PENDING_APPROVAL"
    assert out["mid"]["items"] == ["TC-AUTH-001", "TC-AUTH-002", "TC-AUTH-003"]
    assert out["status"] == "COMPLETED" and out["ci"] == "APPLIED" and out["apr"] in out["overrides"]
    assert out["vers"]["TC-AUTH-003"] == 2

def test_g_compare_scope_failure_cancel():
    """HUMAN_OVERRIDE 選 cancel（整體決定 approve、--option cancel，同 admin-ui 的組法）→ run CANCELLED，Registry 不變。"""
    out = run_cia(_root(), ESCALATE + """
before = {t: v for t, v, _ in active()}
engine.approve(apr, "approve", BY, selected_option="cancel", new_request=True)
print(json.dumps({"esc": esc, "status": engine.load_run(rid)["status"], "same": before == {t: v for t, v, _ in active()}}, default=str))""")
    assert out["esc"]["type"] == "HUMAN_OVERRIDE" and out["status"] == "CANCELLED" and out["same"]

def test_g_tval_override_in_change_impact_reaches_apply_change():
    """spec-change-impact 的 Validator FAIL ×3 → HUMAN_OVERRIDE override：ChangeImpact 由 TEST_UPDATE_REQUIRED 進入 COMPARING（比照 G-TVAL PASS），
    T4 比較 PASS 後才能建立 APPLY_CHANGE（修正前 COMPARING 以外的狀態轉 PENDING_APPROVAL 會失敗，run 卡在 T4）。"""
    out = run_cia(_root(), """
rid, rmid = start()
cir = cir_for(rid); cid, g1 = impact(rid, cir); assert g1["result"] == "PASS", g1
issue = {"testcase_id": "*", "issue_type": "other", "severity": "major", "violated_requirement": None, "spec_reference": None, "evidence": "x", "explanation": "x", "recommended_change": "x"}
for it, pre in enumerate(["01BX5ZZKBKACTAV9WEVGEMMV1", "01BX5ZZKBKACTAV9WEVGEMMV2", "01BX5ZZKBKACTAV9WEVGEMMV3"]):
    did, new = design(rid, cid, cir, pre, it=it)
    _, pv = H.write_artifact(rid, "T3", "agent-test-validator", "TestValidationReport", H.validation_report(did, rmid, "FAIL", [issue]),
                             [{"entity_type": "Artifact", "id": did}], {"type": "TestCaseDraft", "ids": [did]}, "validation", iteration=it)
    assert engine.submit(rid, "T3", str(pv))[0]; assert engine.evaluate_gate(rid, "T3")["result"] == "FAIL"
apr, a = waiting(rid); assert a["type"] == "HUMAN_OVERRIDE", a
engine.approve(apr, "override", BY, rationale="人工判定可接受", new_request=True)
mid = ci(rid)
_, g4 = compare(rid, cid, cir, new, it=0)
apr2, a2 = waiting(rid)
print(json.dumps({"mid": mid, "g4": g4, "t5": a2 and a2["type"], "ci": ci(rid)}, default=str))""")
    assert out["mid"] == "COMPARING"
    assert out["g4"]["result"] == "PASS", out["g4"]
    assert out["t5"] == "APPLY_CHANGE" and out["ci"] == "PENDING_APPROVAL"

REPORT_ERRORS = {   # 本輪 Draft 多取代 unaffected 的 TC-AUTH-003（最後一筆）；報告除此之外還寫錯 → 仍是報告問題，只寫診斷、不升級（自審 1）
    "old_version": ("vcr = copy.deepcopy(new); vcr[-1]['supersedes_testcase'] = dict(vcr[-1]['supersedes_testcase'], version=99)", "比較卻對到"),
    "as_added":    ("vcr = copy.deepcopy(new); vcr[-1].pop('supersedes_testcase')", "比較列應恰好是"),
}

@pytest.mark.parametrize("case", list(REPORT_ERRORS))
def test_g_compare_report_errors_on_out_of_scope_rows_stay_diagnostic(case):
    """被超出範圍取代的 TC，比較列仍要對到取代它的 Draft 與版本：報告把那一列寫錯（old_version、當成 added）→ 報告問題，T4 READY、不建 HUMAN_OVERRIDE，
    避免 override 帶著錯誤的比較報告進 APPLY_CHANGE。"""
    edit, expect = REPORT_ERRORS[case]
    out = run_cia(_root(), f"""
rid, rmid = start()
cir = cir_for(rid); cid, g1 = impact(rid, cir); assert g1["result"] == "PASS", g1
did, new = legacy_design(rid, cid, cir, P1, [extra_sup('TC-AUTH-003')]); validate(rid, did, rmid)
{edit}
_, g4 = compare(rid, cid, cir, vcr)
print(json.dumps({{"g": g4, "t4": tasks(rid)["T4"], "apr": waiting(rid)[0]}}, default=str))""")
    assert out["g"]["result"] == "FAIL" and any(expect in i for i in out["g"]["issues"]), out["g"]
    assert any("unaffected" in i for i in out["g"]["issues"]) and out["t4"][0] == "READY" and out["apr"] is None

def test_g_design_rejects_payload_mode_spec_in_change_task():
    """spec-change-impact 的 T2 以 payload mode=spec（source=spec_workflow）提交、取代 unaffected 的 TC：payload 自填的 mode 不能繞過檢查（自審 2）。"""
    out = run_cia(_root(), """
rid, rmid = start()
cir = cir_for(rid); cid, g1 = impact(rid, cir); assert g1["result"] == "PASS", g1
base, _ = H.draft_set(prefix=P1); H.legacy_acs(base, set(rm.ac_history(SPEC)["owners"]))
x = extra_sup('TC-AUTH-003'); x["source"] = "spec_workflow"
did, pd = H.write_artifact(rid, "T2", "agent-test-designer", "TestCaseDraft", {"mode": "spec", "spec_id": SPEC, "spec_version": "1.0", "testcases": [x]},
                           [{"entity_type": "Requirement", "id": r} for r in x["requirement_ids"]], {"type": "ChangeImpactReport", "ids": [cid]}, "test-design")
rep = H.design_report(did, [x])
_, pr = H.write_artifact(rid, "T2", "agent-test-designer", "TestDesignReport", rep, [{"entity_type": "Artifact", "id": did}], {"type": "TestCaseDraft", "ids": [did]}, "test-design")
assert engine.submit(rid, "T2", str(pd))[0] and engine.submit(rid, "T2", str(pr))[0]
print(json.dumps({"g": engine.evaluate_gate(rid, "T2"), "t2": tasks(rid)["T2"]}, default=str))""")
    issues = out["g"]["issues"]
    assert out["g"]["result"] == "FAIL" and out["t2"][0] == "READY", out["g"]
    assert any("mode=spec" in i and "mode=change" in i for i in issues) and any("TC-AUTH-003" in i and "unaffected" in i for i in issues), issues

def test_human_override_decision_must_match_option():
    """HUMAN_OVERRIDE 的 decision 與 option 必須一致（自審 3）：approve 只代表取消，必須帶 --option cancel；override／reject 帶不同 option → 拒絕，核准單維持 PENDING。"""
    out = run_cia(_root(), ESCALATE + """
errs = []
for d, opt in (("approve", None), ("approve", "override"), ("reject", "cancel"), ("override", "reject")):
    try: engine.approve(apr, d, BY, rationale="x", selected_option=opt, new_request=True); errs.append(None)
    except engine.EngineError as ex: errs.append(str(ex))
st = store.load(f"approvals/{apr}.yaml")["status"]; run_st = engine.load_run(rid)["status"]
engine.approve(apr, "reject", BY, rationale="退回", selected_option="reject", new_request=True)
print(json.dumps({"errs": errs, "st": st, "run": run_st, "after": engine.load_run(rid)["current_task_id"]}, default=str))""")
    assert all(out["errs"]), out["errs"]
    assert "--option cancel" in out["errs"][0] and out["st"] == "PENDING" and out["run"] == "WAITING_HUMAN" and out["after"] == "T2"

@pytest.mark.parametrize("decision", ["reject", "override"])
def test_compare_escalation_on_inflight_run_left_in_test_update_required(decision):
    """修正前在 G-TVAL 迭代超限選 override 的在途 run，ChangeImpact 停在 TEST_UPDATE_REQUIRED（自審 4；以外部寫入模擬該舊狀態）：
    G-COMPARE 升級後 reject 仍可退回 T2、override 仍可建立 APPLY_CHANGE（先補走 VALIDATING → COMPARING）。"""
    out = run_cia(_root(), ESCALATE + f"""
p = f"runs/{{rid}}/entities/change-impact.yaml"; c = store.load(p); c["status"] = "TEST_UPDATE_REQUIRED"; H.raw_save(p, c)
engine.approve(apr, "{decision}", BY, rationale="在途 run", new_request=True)
a2 = waiting(rid)[1]
print(json.dumps({{"ci": ci(rid), "cur": engine.load_run(rid)["current_task_id"], "t5": a2 and a2["type"]}}, default=str))""")
    if decision == "reject": assert out["ci"] == "TEST_UPDATE_REQUIRED" and out["cur"] == "T2" and out["t5"] is None
    else: assert out["ci"] == "PENDING_APPROVAL" and out["t5"] == "APPLY_CHANGE"

RETIRE = {   # (CIR 改判, retire_recommendations, 預期訊息)
    "not_obsolete": ("", "[{'testcase_id': 'TC-AUTH-001', 'reason': 'x'}]", "不是 CIR 判定 obsolete 的 TC"),
    "legal":        ("o = next(i for i in cir['testcase_impact'] if i['testcase_id'] == 'TC-AUTH-003'); o.update(impact='obsolete', reason='需求刪除'); "
                     "cir['summary'].update(testcases_obsolete=1, testcases_unaffected=cir['summary']['testcases_unaffected'] - 1)",
                     "[{'testcase_id': 'TC-AUTH-003', 'reason': '需求刪除'}]", None),
}

@pytest.mark.parametrize("case", list(RETIRE))
def test_g_compare_checks_retire_recommendations(case):
    """retire_recommendations 在 APPLY_CHANGE 核准後會被退役：只能是 CIR obsolete、且沒有本輪新版的 TC（自審 6）。列 affected 的 TC → 報告問題（READY）；
    obsolete 的 TC 列為 removed 並建議退役 → PASS。"""
    cir_edit, retire, expect = RETIRE[case]
    out = run_cia(_root(), f"""
rid, rmid = start()
cir = cir_for(rid)
{cir_edit}
cid, g1 = impact(rid, cir); assert g1["result"] == "PASS", g1
did, new = design(rid, cid, cir, P1); validate(rid, did, rmid)
sup = [d for d in new if d.get("supersedes_testcase")]
obs = [i for i in cir["testcase_impact"] if i["impact"] == "obsolete"]
vcr = {{"change_impact_id": cir["change_impact_id"], "comparisons": [{{"testcase_id": d["supersedes_testcase"]["testcase_id"], "old_version": d["supersedes_testcase"]["version"],
       "new_draft_id": d["draft_id"], "verdict": "changed", "field_diffs": [{{"field": "expected_result", "old": "-", "new": d["expected_result"]}}], "impacted_requirement_ids": d["requirement_ids"]}} for d in sup] +
       [{{"testcase_id": i["testcase_id"], "old_version": i["active_version"], "new_draft_id": None, "verdict": "removed", "field_diffs": [], "impacted_requirement_ids": []}} for i in obs],
       "retire_recommendations": {retire}, "summary": {{"unchanged": 0, "changed": len(sup), "added": 0, "removed": len(obs)}}}}
aid, p = H.write_artifact(rid, "T4", "agent-change-impact-analyst", "VersionComparisonReport", vcr, [{{"entity_type": "Artifact", "id": cid}}], {{"type": "ChangeImpactReport", "ids": [cid]}}, "change-impact")
assert engine.submit(rid, "T4", str(p))[0]; g4 = engine.evaluate_gate(rid, "T4")
print(json.dumps({{"g": g4, "t4": tasks(rid)["T4"], "apr": waiting(rid)[1] and waiting(rid)[1]["type"]}}, default=str))""")
    if expect is None: assert out["g"]["result"] == "PASS" and out["apr"] == "APPLY_CHANGE", out["g"]
    else:
        assert out["g"]["result"] == "FAIL" and any(expect in i for i in out["g"]["issues"]), out["g"]
        assert out["t4"][0] == "READY" and out["apr"] is None

def test_g_design_rejects_duplicate_draft_ids():
    """Codex 01 M1：draft_id 重複 → G-DESIGN FAIL（比較報告與 Validator 以 draft_id 指稱新稿，重複時身分有歧義）。"""
    out = run_cia(_root(), """
rid, rmid = start()
cir = cir_for(rid); cid, g1 = impact(rid, cir); assert g1["result"] == "PASS", g1
def mutate(new): new[1]["draft_id"] = new[0]["draft_id"]
did, new, g = design_g(rid, cid, cir, P1, mutate=mutate)
print(json.dumps({"g": g}, default=str))""")
    assert out["g"]["result"] == "FAIL" and any("必須唯一" in i for i in out["g"]["issues"]), out["g"]

def test_g_compare_duplicate_draft_id_cannot_hide_out_of_scope_draft():
    """Codex 01 M1 反例：在途 Draft 中取代 unaffected TC-AUTH-003 的稿和合法稿共用 draft_id、排在前面，比較報告只列後一筆。
    G-COMPARE 必須以完整清單判定範圍（不經 draft_id 索引）：不得 PASS／建立 APPLY_CHANGE。報告漏列同一 draft_id 的另一筆仍是報告問題（Codex 02 M3），
    T4 READY；報告照 Draft 逐筆寫後才升級（見 test_g_compare_duplicate_draft_id_with_correct_report_escalates_then_reject），Registry 不變。"""
    out = run_cia(_root(), """
rid, rmid = start()
cir = cir_for(rid); cid, g1 = impact(rid, cir); assert g1["result"] == "PASS", g1
x = extra_sup('TC-AUTH-003')
def mutate(new):
    x2 = new.pop(); x2["draft_id"] = new[0]["draft_id"]; new.insert(0, x2)
orig = gates.GATES["G-DESIGN"]; gates.GATES["G-DESIGN"] = lambda *a: []
did, new, g2 = design_g(rid, cid, cir, P1, extra=[x], mutate=mutate); gates.GATES["G-DESIGN"] = orig
validate(rid, did, rmid)
before = {t: v for t, v, _ in active()}
_, g4 = compare(rid, cid, cir, new[1:])
apr, a = waiting(rid)
print(json.dumps({"g": g4, "type": a and a["type"], "t4": tasks(rid)["T4"], "same": before == {t: v for t, v, _ in active()}}, default=str))""")
    issues = out["g"]["issues"]
    assert out["g"]["result"] == "FAIL" and out["type"] is None and out["t4"][0] == "READY" and out["same"], out
    assert any("必須唯一" in i for i in issues) and any("TC-AUTH-003" in i and "unaffected" in i for i in issues) and any("比較列應恰好對到" in i for i in issues), issues

VERDICT_ERRORS = {   # 報告的 verdict／身分／summary 不一致 → 報告問題（T4 READY），範圍內與範圍外的列都一樣（Codex 01 M2）
    "removed_with_new": ("compare(rid, cid, cir, new, verdict='removed')", "verdict removed 不得帶 new_draft_id"),
    "sup_as_added":     ("compare(rid, cid, cir, new, verdict='added')", "verdict added 不得帶舊 testcase_id"),
}

@pytest.mark.parametrize("scope", ["in_scope", "out_of_scope"])
@pytest.mark.parametrize("case", list(VERDICT_ERRORS) + ["summary"])
def test_g_compare_verdict_identity_and_summary_are_report_issues(case, scope):
    """Codex 01 M2：supersedes 的列只能是 changed／unchanged；removed 不得帶新稿；added 不得帶舊 TC；summary 必須等於逐列統計。
    這些都能改報告修正 → 報告問題，T4 READY、不建 HUMAN_OVERRIDE（out_of_scope：Draft 另外多取代 unaffected 的 TC-AUTH-003，也不得因此升級）。"""
    extra = "[extra_sup('TC-AUTH-003')]" if scope == "out_of_scope" else "[]"
    call, expect = VERDICT_ERRORS.get(case, (None, "summary.changed"))
    body = f"_, g4 = {call}" if call else """sup = [d for d in new if d.get("supersedes_testcase")]
vcr = {"change_impact_id": cir["change_impact_id"], "comparisons": [{"testcase_id": d["supersedes_testcase"]["testcase_id"], "old_version": d["supersedes_testcase"]["version"],
       "new_draft_id": d["draft_id"], "verdict": "changed", "field_diffs": [{"field": "expected_result", "old": "-", "new": d["expected_result"]}], "impacted_requirement_ids": d["requirement_ids"]} for d in sup],
       "retire_recommendations": [], "summary": {"unchanged": 0, "changed": len(sup) + 1, "added": 0, "removed": 0}}
aid, p = H.write_artifact(rid, "T4", "agent-change-impact-analyst", "VersionComparisonReport", vcr, [{"entity_type": "Artifact", "id": cid}], {"type": "ChangeImpactReport", "ids": [cid]}, "change-impact")
assert engine.submit(rid, "T4", str(p))[0]; g4 = engine.evaluate_gate(rid, "T4")"""
    out = run_cia(_root(), f"""
rid, rmid = start()
cir = cir_for(rid); cid, g1 = impact(rid, cir); assert g1["result"] == "PASS", g1
did, new = legacy_design(rid, cid, cir, P1, {extra}); validate(rid, did, rmid)
{body}
print(json.dumps({{"g": g4, "t4": tasks(rid)["T4"], "apr": waiting(rid)[0]}}, default=str))""")
    assert out["g"]["result"] == "FAIL" and any(expect in i for i in out["g"]["issues"]), out["g"]
    assert out["t4"][0] == "READY" and out["apr"] is None

DUP_SETUP = """
rid, rmid = start()
cir = cir_for(rid); cid, g1 = impact(rid, cir); assert g1["result"] == "PASS", g1
x = extra_sup('TC-AUTH-003')
def mutate(new):
    x2 = new.pop(); x2["draft_id"] = new[0]["draft_id"]; new.insert(0, x2)
orig = gates.GATES["G-DESIGN"]; gates.GATES["G-DESIGN"] = lambda *a: []
did, new, g2 = design_g(rid, cid, cir, P1, extra=[x], mutate=mutate); gates.GATES["G-DESIGN"] = orig
validate(rid, did, rmid)
before = {t: v for t, v, _ in active()}
"""

def test_g_compare_duplicate_draft_id_still_checks_report():
    """Codex 02 M3：draft_id 重複（Draft 的問題）時，報告的其餘檢查照常進行。報告只列一筆、old_version 寫 99、new_draft_id 是 foreign、
    建議退役 unaffected 的 TC-AUTH-005 → 報告問題，T4 READY、不建 HUMAN_OVERRIDE，Registry 不變（不會 override 後退役 unaffected TC）。"""
    out = run_cia(_root(), DUP_SETUP + """
rows = [{"testcase_id": d["supersedes_testcase"]["testcase_id"], "old_version": 99, "new_draft_id": d["draft_id"][:-1] + "Q", "verdict": "changed",
         "field_diffs": [{"field": "expected_result", "old": "-", "new": d["expected_result"]}], "impacted_requirement_ids": d["requirement_ids"]} for d in new[1:]]
vcr = {"change_impact_id": cir["change_impact_id"], "comparisons": rows, "retire_recommendations": [{"testcase_id": "TC-AUTH-005", "reason": "誤退役 unaffected"}],
       "summary": {"unchanged": 0, "changed": len(rows), "added": 0, "removed": 0}}
aid, p = H.write_artifact(rid, "T4", "agent-change-impact-analyst", "VersionComparisonReport", vcr, [{"entity_type": "Artifact", "id": cid}], {"type": "ChangeImpactReport", "ids": [cid]}, "change-impact")
assert engine.submit(rid, "T4", str(p))[0]; g4 = engine.evaluate_gate(rid, "T4")
print(json.dumps({"g": g4, "t4": tasks(rid)["T4"], "apr": waiting(rid)[0], "same": before == {t: v for t, v, _ in active()}}, default=str))""")
    issues = out["g"]["issues"]
    assert out["g"]["result"] == "FAIL" and out["t4"][0] == "READY" and out["apr"] is None and out["same"], out
    for expect in ("不屬於 G-TVAL 審過的本輪 Draft", "TC-AUTH-005 不是 CIR 判定 obsolete", "不是 CIR 的 active_version", "必須唯一"):
        assert any(expect in i for i in issues), (expect, issues)

def test_g_compare_duplicate_draft_id_with_correct_report_escalates_then_reject():
    """draft_id 重複、報告照 Draft 逐筆寫（同一 draft_id 兩列，各對到所取代的 TC）→ 只剩 Draft 問題，升級 HUMAN_OVERRIDE；reject → 退回 T2，Registry 不變。"""
    out = run_cia(_root(), DUP_SETUP + """
_, g4 = compare(rid, cid, cir, new)
apr, a = waiting(rid)
engine.approve(apr, "reject", BY, rationale="draft_id 重複，退回重做", new_request=True)
print(json.dumps({"g": g4, "type": a and a["type"], "cur": engine.load_run(rid)["current_task_id"], "t2": tasks(rid)["T2"],
                  "same": before == {t: v for t, v, _ in active()}}, default=str))""")
    issues = out["g"]["issues"]
    assert out["g"]["result"] == "FAIL" and out["type"] == "HUMAN_OVERRIDE", out
    assert all("必須唯一" in i or ("TC-AUTH-003" in i and "unaffected" in i) for i in issues), issues
    assert out["cur"] == "T2" and out["t2"] == ["READY", 1] and out["same"]
