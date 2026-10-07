"""P4 第二輪：TC 與 RR 的型別化 SourceRef 完整驗證、退回後下游 task 的新 iteration 與重新派發、新索引欄位的整數表示
（需求 A 第 1 章 §2.2、§2.6；第 3 章 §6；附錄 A 3-24、1-37～1-40）。所有狀態以正式流程建立；RR 的高風險 area 設定是
測試 root 定義層的設定（同 tests/test_wf_y_zzz_risk_review.py 把測試 area 當高風險的作法），另外標示。"""
import json, pathlib, yaml
from tests import p1_util as U
from tests.test_p4_dispatch import mkroot, py
from tests.test_p4_decisions import CONFLICT_SIDES, EXAMPLE_A

DIMS = ["boundary", "exception_flow", "concurrency", "duplicate_submission", "permission"]
OKQ = 'F.req(1, [F.dp("Q01", "defined_in_target", "none", known=[F.sref("任何站台都不能刪除。")])])'
DREF = '[{"requirement_id": "REQ-DEMO-001", "question_id": "Q01", "basis_ref": F.ident(F.sref("任何站台都不能刪除。"))}]'

def rr_root(tmp_path):
    """測試 root 定義層：把 DEMO 加進 tc-risk-reviewer 的 applies_to_areas（測試設定，不是業務資料）。"""
    root = mkroot(tmp_path); p = pathlib.Path(root) / "agents/tc-risk-reviewer.yaml"
    a = yaml.safe_load(p.read_text(encoding="utf-8")); a["applies_to_areas"] = a["applies_to_areas"] + ["DEMO"]
    p.write_text(yaml.safe_dump(a, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return root

# ---------------------------------------------------------------- P4-01：TC 的 source_refs 逐筆完整驗證
def test_tc_source_refs_are_validated_in_full(tmp_path):
    root = mkroot(tmp_path)
    out = py(root, f"""
c = clr.new("demo", "DEMO", F.SPEC, F.VER, "子站台能否刪除？", "oscar", requirement_id="REQ-DEMO-001", new_request=True)   # 入口 D
clr.answer(c["clarification_id"], "任何站台都不能刪除。", "pm", "requirement_clarified", "oscar", new_request=True)
rid = F.new_run(); g = F.analyze(rid, [{OKQ}])
good = F.sref("任何站台都不能刪除。")
bad_clr = dict(F.cref(c["clarification_id"], "任何站台都不能刪除"), answer_rev=5)
bad_apr = {{"type": "approval", "approval_id": "APR-9999", "decision_sha256": "0" * 64, "resolution_index": 0, "quote": "x"}}
bound = lambda ref: {DREF} + [{{"requirement_id": "REQ-DEMO-001", "question_id": "Q01", "basis_ref": F.ident(ref)}}]   # 綁定到決策點，讓來源驗證真的跑到
cases = {{
  "quote": (dict(good, quote="任何管理員都可以刪除任何站台。"), {DREF}),
  "hash": (dict(good, content_hash="0" * 64), {DREF}),
  "clr_rev": (bad_clr, bound(bad_clr)),
  "apr_missing": (bad_apr, bound(bad_apr)),
  "unbound": (F.cref(c["clarification_id"], "任何站台都不能刪除"), {DREF}),
}}
res = {{}}
for n, (ref, drefs) in cases.items():
    d = F.design(rid, [F.tc(1, "REQ-DEMO-001", "刪除子站台被拒", techs=["negative"], types=["negative"], drefs=drefs, srcs=[ref])])
    res[n] = [d["result"], d.get("issues")]
ok = F.design(rid, [F.tc(1, "REQ-DEMO-001", "刪除子站台被拒", techs=["negative"], types=["negative"], drefs={DREF}, srcs=[good])])
res["ok"] = [ok["result"], ok.get("issues")]
v = F.validate(rid, ok["did"], g["rmid"]); F.approve(F.waiting(rid))
res["tcs"] = [store.load(p)["status"] for p in store.glob("testcases/registry/TC-DEMO-*.yaml")]
print(json.dumps(res))""")
    for n, needle in (("quote", "quote 不在"), ("hash", "SPEC-DEMO-001"), ("clr_rev", "沒有 answer_rev 5"), ("apr_missing", "APR-9999 不存在"), ("unbound", "必須對應本 TC 的某筆 decision_refs")):
        r, issues = out[n]
        assert r == "FAIL" and any("source_refs[0]" in i and needle in i for i in issues), (n, issues)
    assert out["ok"][0] == "PASS", out["ok"]
    assert out["tcs"] == ["ACTIVE"]                                   # 只有合法來源的那一版成為 ACTIVE；失敗的版本沒有 materialize（核准型與 CLR 型的正例見 test_approval_source_bound_to_its_decision_point）

# ---------------------------------------------------------------- P4-02：退回後下游 task 進入新 iteration，可以重新派發
def test_downstream_tasks_get_new_iteration_after_route_back_and_reject(tmp_path):
    root = rr_root(tmp_path)
    out = py(root, f"""
from tests.test_p4_sources_and_iterations import review
rid = F.new_run(); g = F.analyze(rid, [{OKQ}])
d1 = F.design(rid, [F.tc(1, "REQ-DEMO-001", "刪除子站台被拒", techs=["negative"], types=["negative"], drefs={DREF})])
v0_sha = H.packet_sha(rid, "T3")
issue = {{"testcase_id": "*", "issue_type": "missing_coverage", "severity": "major", "violated_requirement": "REQ-DEMO-001", "spec_reference": None,
          "evidence": "e", "explanation": "缺少列表頁的檢查", "recommended_change": "補一條"}}
f1 = F.validate(rid, d1["did"], g["rmid"], "FAIL", [issue])
run = engine.load_run(rid); it = {{t["task_id"]: t["iteration"] for t in run["tasks"]}}
other = F.sref("與站台無關的規則。", sid="SPEC-OTHER-001", loc="§無關")
dispatch.dispatch(rid, "T2", [{{"ref": "SPEC-OTHER-001@1.0", "reason": "補充其他功能區的規則"}}], new_request=True)
d2 = F.design(rid, [F.tc(1, "REQ-DEMO-001", "刪除子站台被拒", techs=["negative"], types=["negative"], drefs={DREF}, srcs=[other]),
                    F.tc(2, "REQ-DEMO-001", "列表頁沒有刪除按鈕", drefs={DREF})])
it3_after_design = engine._task(engine.load_run(rid), "T3")["iteration"]
_, pv = H.write_artifact(rid, "T3", "agent-test-validator", "TestValidationReport", H.validation_report(d2["did"], g["rmid"], "PASS"),
                         [{{"entity_type": "Artifact", "id": d2["did"]}}], {{"type": "TestCaseDraft", "ids": [d2["did"]]}}, "validation", packet=v0_sha)
no_pkg = engine.submit(rid, "T3", str(pv))                            # iteration 1 還沒派發
dispatch.dispatch(rid, "T3", [{{"ref": "SPEC-OTHER-001@1.0", "reason": "Designer 本輪登記的補充來源"}}], new_request=True)
_, pv = H.write_artifact(rid, "T3", "agent-test-validator", "TestValidationReport", H.validation_report(d2["did"], g["rmid"], "PASS"),
                         [{{"entity_type": "Artifact", "id": d2["did"]}}], {{"type": "TestCaseDraft", "ids": [d2["did"]]}}, "validation", packet=v0_sha)
old_pkg = engine.submit(rid, "T3", str(pv))                           # 已派發新包，產出卻沿用 iteration 0 的包
v2 = F.validate(rid, d2["did"], g["rmid"], "PASS")
rr1 = review(rid, d2, g)
run = engine.load_run(rid); apr = F.waiting(rid)
F.approve(apr, decision="reject", rationale="整批重做")
run2 = engine.load_run(rid); it2 = {{t["task_id"]: t["iteration"] for t in run2["tasks"]}}; st2 = {{t["task_id"]: t["status"] for t in run2["tasks"]}}
d3 = F.design(rid, [F.tc(1, "REQ-DEMO-001", "刪除子站台被拒", techs=["negative"], types=["negative"], drefs={DREF}), F.tc(2, "REQ-DEMO-001", "列表頁沒有刪除按鈕", drefs={DREF})])
v3 = F.validate(rid, d3["did"], g["rmid"], "PASS")
run3 = engine.load_run(rid); it3_rr_after = [engine._task(run3, "T3")["iteration"], engine._task(run3, "T3RR")["iteration"]]
print(json.dumps({{"f1": f1["result"], "it": it, "it3_after_design": it3_after_design, "d2": d2["result"], "d2_issues": d2.get("issues"), "no_pkg": no_pkg[1], "old_pkg": old_pkg[1], "v2": v2["result"], "v2_issues": v2.get("issues"),
                  "rr1": rr1["result"], "it2": it2, "st2": st2, "t3_packets": [e["iteration"] for e in engine._task(run2, "T3")["dispatch_packets"]], "it3_rr_after": it3_rr_after}}))""")
    assert out["f1"] == "FAIL" and out["it"]["T2"] == 1 and out["it"]["T3"] == 0          # semantic FAIL 退回：Designer 進入 iteration 1；Validator 自己的 gate 操作中不改它的 iteration
    assert out["it3_after_design"] == 1                                                      # Designer 重做 PASS、Validator 被推進成 READY 時才進入 iteration 1
    assert out["d2"] == "PASS", out["d2_issues"]                                             # Designer 登記的額外來源通過 G-DESIGN
    assert any("iteration 1 還沒有派發包" in p for p in out["no_pkg"]), out["no_pkg"]
    assert any("沿用舊 iteration 的派發包不能提交" in p for p in out["old_pkg"]), out["old_pkg"]
    assert out["v2"] == "PASS", out["v2_issues"]                                             # Validator 以新派發包登記同一來源 → 範圍內
    assert out["rr1"] == "PASS"
    assert out["it2"]["T2"] == 2 and out["it2"]["T3"] == 1 and out["it2"]["T3RR"] == 0        # 整批 reject：Designer 進入新 iteration；下游在被推進時才進入
    assert out["it3_rr_after"] == [2, 1]                                                     # Designer 第三輪 PASS、Validator PASS 之後，T3、T3RR 都進入新的 iteration
    assert out["st2"]["T2"] == "READY" and out["st2"]["T3"] == "PENDING" and out["st2"]["T3RR"] == "PENDING"
    assert out["t3_packets"] == [0, 1]                                                      # 舊派發紀錄保留

def review(rid, d, g, spec_basis=None, needs_clarification=True, spec_basis_decision=None, related=("REQ-DEMO-001",)):
    """RR 提交（在子程序中呼叫）：五面向；一筆 finding 帶指定的 spec_basis。"""
    from tests import p4_flow as F
    from tests import helpers as H
    from tools.qaos import engine, store
    run = engine.load_run(rid); t3 = engine._task(run, "T3"); tvr = t3["output_artifact_ids"][-1]
    draft = store.load(store.find_artifact(d["did"]))["payload"]
    finding = {"finding_id": "RF-01", "dimension": "permission", "severity": "high", "related_testcase_ids": [], "related_requirement_ids": list(related),
               "gap": "跨站台管理員是否能刪除他站的子站台尚未覆蓋", "suggested_scenario": "以站長身分嘗試刪除其他站台的子站台，確認被拒且不留下紀錄",
               "spec_basis": spec_basis, "needs_clarification": needs_clarification, **({"spec_basis_decision": spec_basis_decision} if spec_basis_decision else {})}
    payload = {"reviewed": {"testcase_draft_artifact_id": d["did"], "validation_report_artifact_id": tvr, "functional_area": "DEMO", "spec_id": F.SPEC, "spec_version": F.VER,
                            "testcase_draft_ids": [t["draft_id"] for t in draft["testcases"]]},
               "dimension_results": [{"dimension": x, "status": "gaps_found" if x == "permission" else "covered", "rationale": f"{x} 已逐條檢視"} for x in DIMS],
               "findings": [finding], "summary": "抽查完成，列出一筆補充建議"}
    _, p = H.write_artifact(rid, "T3RR", "agent-tc-risk-reviewer", "TCRiskReview", payload, [{"entity_type": "Artifact", "id": d["did"]}], {"type": "TestCaseDraft", "ids": [d["did"]]}, "risk-review")
    ok, pr = engine.submit(rid, "T3RR", str(p))
    if not ok: return {"result": "SUBMIT_INVALID", "issues": pr}
    return engine.evaluate_gate(rid, "T3RR")

# ---------------------------------------------------------------- P4-04：RR 的 spec_basis 是型別化 SourceRef
def test_risk_review_spec_basis_source_ref_types(tmp_path):
    root = rr_root(tmp_path)
    out = py(root, f"""
from tests.test_p4_sources_and_iterations import review
c = clr.new("demo", "DEMO", F.SPEC, F.VER, "站長能否刪除他站子站台？", "oscar", requirement_id="REQ-DEMO-001", new_request=True)   # 入口 D
clr.answer(c["clarification_id"], "任何站台都不能刪除。", "pm", "requirement_clarified", "oscar", new_request=True)
z = clr.new("demo", "ZONE", "SPEC-OTHER-001", "1.0", "其他功能區的已回答問題", "oscar", new_request=True)            # 入口 D：不在派發包的 area
clr.answer(z["clarification_id"], "其他功能區的規則：一律保留紀錄。", "pm", "requirement_clarified", "oscar", new_request=True)
rid0 = F.new_run(); F.analyze(rid0, [{EXAMPLE_A}]); apr = F.waiting(rid0)
F.approve(apr, resolutions=[{{"requirement_id": "REQ-DEMO-001", "question_id": "Q01", "outcome": "select_interpretation", "source": None, "rationale": "以刪除規則為準：任何站台都不能刪除"}}])
res = {{"source": F.aref(apr, 0, "任何站台都不能刪除"), "decided_at": "2026-10-07", "adopted_side_index": 1}}
g = F.analyze(rid0, [F.req(1, [F.dp("Q01", "conflict", "critical", {CONFLICT_SIDES}, resolution=res)], ambiguity=F.amb("none", "critical"))])
dref = [{{"requirement_id": "REQ-DEMO-001", "question_id": "Q01", "basis_ref": F.ident(res["source"])}}]
d = F.design(rid0, [F.tc(1, "REQ-DEMO-001", "刪除子站台被拒", techs=["negative"], types=["negative"], drefs=dref)])
F.validate(rid0, d["did"], g["rmid"])
out = {{}}
Q = {{"requirement_id": "REQ-DEMO-001", "question_id": "Q01"}}
for n, sb, nc, sd in (("bad_quote", dict(F.sref("任何站台都不能刪除。"), quote="站長可以刪除他站"), False, None),
                      ("legacy", {{"location": "§刪除規則", "quote": "任何站台都不能刪除。"}}, False, None),
                      ("clr_outside", F.cref(z["clarification_id"], "一律保留紀錄"), False, Q),
                      ("approval_no_decision", F.aref(apr, 0, "任何站台都不能刪除"), False, None),
                      ("clr_not_usable", F.cref(c["clarification_id"], "任何站台都不能刪除"), False, Q)):
    r = review(rid0, d, g, sb, nc, sd); out[n] = [r["result"], r.get("issues")]
run = engine.load_run(rid0); t = engine._task(run, "T3RR")                 # 函式層：同一個 task、同一份派發包，只換 finding 的 spec_basis
base = store.load(store.find_artifact(t["output_artifact_ids"][-1]))
for n, sb, nc, sd in (("approval", F.aref(apr, 0, "任何站台都不能刪除"), False, Q), ("null", None, True, None)):
    a = json.loads(json.dumps(base)); a["payload"]["findings"][0].update(spec_basis=sb, needs_clarification=nc)
    a["payload"]["findings"][0].pop("spec_basis_decision", None)
    if sd: a["payload"]["findings"][0]["spec_basis_decision"] = sd
    issues = gates.g_risk(run, t, {{"TCRiskReview": a}}); out[n] = ["PASS" if not issues else "FAIL", issues]
r = review(rid0, d, g, F.sref("任何站台都不能刪除。"), False); out["spec"] = [r["result"], r.get("issues")]   # 正式流程 PASS
out["waiting"] = store.load(f"approvals/{{F.waiting(rid0)}}.yaml")["type"]
print(json.dumps(out))""")
    assert out["bad_quote"][0] == "FAIL" and any("quote 不在" in i for i in out["bad_quote"][1]), out["bad_quote"]
    assert out["legacy"][0] == "FAIL" and any("必須是型別化的 SourceRef" in i for i in out["legacy"][1]), out["legacy"]
    assert out["clr_outside"][0] == "FAIL" and any("不在本 task 派發包的範圍內" in i for i in out["clr_outside"][1]), out["clr_outside"]
    assert out["approval_no_decision"][0] == "FAIL" and any("spec_basis_decision" in i for i in out["approval_no_decision"][1]), out["approval_no_decision"]
    assert out["clr_not_usable"][0] == "FAIL" and any("不是 REQ-DEMO-001/Q01 可用的依據" in i for i in out["clr_not_usable"][1]), out["clr_not_usable"]
    for n in ("approval", "null", "spec"):
        assert out[n][0] == "PASS", (n, out[n])
    assert out["waiting"] == "ACTIVATE_TESTCASE"

# ---------------------------------------------------------------- P4-03：新索引欄位只接受整數表示
def test_new_index_fields_reject_float_representation(tmp_path):
    root = mkroot(tmp_path)
    E3 = ('F.req(2, [F.dp("Q01", "undefined", "critical", subject="role.assign.site_manager_to_site_manager", role=["site_manager"], '
          'coverage=F.cov(missing=[F.missing({LINE}, "手冊 v01 的角色模型（見 7.1.1 角色說明）", "手冊 7.1.1 角色說明")]{W}))], ambiguity=F.amb("critical", "critical"), statement="站長指派範圍")')
    out = py(root, f"""
rid = F.new_run()
line_float = F.analyze(rid, [{E3.format(LINE="13.0", W="")}])
F.analyze(rid, [{E3.format(LINE="13", W="")}]); apr = F.waiting(rid)
item = {{"cited_at": {{**F.pin(), "line": 13}}, "name": "手冊 7.1.1 角色說明"}}
def tryit(waived):
    try: F.approve(apr, resolutions=[{{"requirement_id": "REQ-DEMO-002", "question_id": "Q01", "outcome": "waive_missing", "waived": waived, "rationale": "文件無法取得"}}]); return "accepted"
    except engine.EngineError as e: return str(e)
pf = tryit([{{"cited_at": {{**F.pin(), "line": 13.0}}, "name": "手冊 7.1.1 角色說明"}}])
tryit([item])
dsha = sources.chash(store.load(f"approvals/{{apr}}.yaml")["decision"])
w = lambda idx, line=13: {{"approval_id": apr, "decision_sha256": dsha, "resolution_index": idx, "waived": [{{"cited_at": {{**F.pin(), "line": line}}, "name": "手冊 7.1.1 角色說明"}}]}}
res = {{"line_float": line_float, "pf": pf}}
for n, ww in (("idx_float", w(0.0)), ("idx_bool", w(False)), ("idx_neg", w(-1)), ("waived_line_float", w(0, 13.0))):
    res[n] = F.analyze(rid, [{E3.format(LINE="13", W=", waivers=[ww]")}])
res["ok"] = F.analyze(rid, [{E3.format(LINE="13", W=", waivers=[w(0)]")}])
# adopted_side_index 1.0、basis_ref 的 resolution_index 0.0
rid2 = F.new_run(); F.analyze(rid2, [{EXAMPLE_A}]); apr2 = F.waiting(rid2)
F.approve(apr2, resolutions=[{{"requirement_id": "REQ-DEMO-001", "question_id": "Q01", "outcome": "select_interpretation", "source": None, "rationale": "以刪除規則為準"}}])
r = lambda idx: F.req(1, [F.dp("Q01", "conflict", "critical", {CONFLICT_SIDES}, resolution={{"source": F.aref(apr2, 0, "以刪除規則為準"), "decided_at": "2026-10-07", "adopted_side_index": idx}})], ambiguity=F.amb("none", "critical"))
res["side_float"] = F.analyze(rid2, [r(1.0)])
res["side_ok"] = F.analyze(rid2, [r(1)])
br = dict(F.ident(F.aref(apr2, 0, "x")), resolution_index=0.0)
res["dref_float"] = F.design(rid2, [F.tc(1, "REQ-DEMO-001", "刪除子站台被拒", techs=["negative"], types=["negative"], drefs=[{{"requirement_id": "REQ-DEMO-001", "question_id": "Q01", "basis_ref": br}}])])
res["revs"] = [e["revision"] for e in store.load("artifacts/requirements/SPEC-DEMO-001/v1.0/revisions/index.yaml")["revisions"]]
print(json.dumps({{k: (v if isinstance(v, (str, list)) else [v["result"], v.get("issues")]) for k, v in res.items()}}))""")
    assert out["line_float"][0] == "FAIL" and any("cited_at.line 必須是正整數表示" in i for i in out["line_float"][1])
    assert "cited_at.line 必須是正整數表示" in out["pf"]
    for n in ("idx_float", "waived_line_float"):
        r, issues = out[n]
        assert r == "FAIL" and any(i.startswith("X14：") and "整數表示" in i for i in issues), (n, issues)
    for n in ("idx_bool", "idx_neg"):                                       # bool、負數在 schema 層就被拒（提交無效，不進 gate）
        assert out[n][0] == "SUBMIT_INVALID" and any("resolution_index" in i for i in out[n][1]), (n, out[n])
    assert out["ok"][0] == "PASS", out["ok"]
    assert out["side_float"][0] == "FAIL" and any(i.startswith("X11：") and "整數表示" in i for i in out["side_float"][1])
    assert out["side_ok"][0] == "PASS", out["side_ok"]
    assert out["dref_float"][0] == "FAIL" and any("整數表示" in i for i in out["dref_float"][1])

# ---------------------------------------------------------------- P4-05：Designer 契約的 major 舊規則限於 legacy
def test_designer_contract_scopes_major_rule_to_legacy():
    repo = pathlib.Path(__file__).resolve().parents[1]
    c = yaml.safe_load((repo / "agents/test-designer.yaml").read_text(encoding="utf-8"))
    major = [r for r in c["responsibilities"] if "ambiguity.level=major" in r]
    assert major and all(r.startswith("舊格式需求（沒有 decision_points）") and "新格式需求不套用" in r for r in major)
    md = (repo / ".claude/agents/qaos-test-designer.md").read_text(encoding="utf-8")
    assert "只依賴 E1 的 TC 不要加 assumption" in md

# ---------------------------------------------------------------- P4R2-01：核准型來源必須以實際依賴的決策點為引用處（TC 與 RR）
TWO = ('F.req(1, [F.dp("Q01", "defined_in_target", "none", known=[F.sref("任何站台都不能刪除。")])]), '
       'F.req(2, [F.dp("Q01", "defined_in_target", "none", subject="site.child.view", known=[F.sref("任何站台都不能刪除。")]), '
       'F.dp("Q02", "conflict", "critical", subject="site.child.delete", {SIDES}{RES})], ambiguity=F.amb("{L}", "critical"), statement="子站台規則")')

def test_approval_source_bound_to_its_decision_point(tmp_path):
    root = rr_root(tmp_path)
    out = py(root, f"""
from tests.test_p4_sources_and_iterations import review
rid = F.new_run()
F.analyze(rid, [{TWO.format(SIDES=CONFLICT_SIDES, RES="", L="critical")}]); apr = F.waiting(rid)
F.approve(apr, resolutions=[{{"requirement_id": "REQ-DEMO-002", "question_id": "Q02", "outcome": "select_interpretation", "source": None, "rationale": "以刪除規則為準：任何站台都不能刪除"}}])
src = F.aref(apr, 0, "任何站台都不能刪除")
RES = {{"source": src, "decided_at": "2026-10-07", "adopted_side_index": 1}}
g = F.analyze(rid, [{TWO.format(SIDES=CONFLICT_SIDES, RES=", resolution=RES", L="none")}])
k = F.ident(F.sref("任何站台都不能刪除。"))
d1 = lambda rid_, q, br: {{"requirement_id": rid_, "question_id": q, "basis_ref": br}}
ok2 = F.tc(2, "REQ-DEMO-002", "刪除子站台被拒（依核准決議）", techs=["negative"], types=["negative"], drefs=[d1("REQ-DEMO-002", "Q02", F.ident(src))], srcs=[src])
cases = {{
  "other_req_unbound": F.tc(1, "REQ-DEMO-001", "刪除子站台被拒", techs=["negative"], types=["negative"], drefs=[d1("REQ-DEMO-001", "Q01", k)], srcs=[src]),
  "other_req_bound":   F.tc(1, "REQ-DEMO-001", "刪除子站台被拒", techs=["negative"], types=["negative"], drefs=[d1("REQ-DEMO-001", "Q01", F.ident(src))], srcs=[src]),
  "same_req_other_q":  F.tc(3, "REQ-DEMO-002", "檢視子站台", techs=["negative"], types=["negative"], drefs=[d1("REQ-DEMO-002", "Q01", F.ident(src))], srcs=[src]),
}}
out = {{"g": [g["result"], g["issues"]]}}
for n, t in cases.items():
    r = F.design(rid, [t, ok2]); out[n] = [r["result"], r.get("issues")]
ok1 = F.tc(1, "REQ-DEMO-001", "刪除子站台被拒", techs=["negative"], types=["negative"], drefs=[d1("REQ-DEMO-001", "Q01", k)], srcs=[F.sref("任何站台都不能刪除。")])
okd = F.design(rid, [ok1, ok2]); out["ok"] = [okd["result"], okd.get("issues")]
F.validate(rid, okd["did"], g["rmid"])
d = {{"did": okd["did"]}}
for n, sd, rel in (("rr_other_req", {{"requirement_id": "REQ-DEMO-002", "question_id": "Q02"}}, ("REQ-DEMO-001",)),
                   ("rr_same_req_other_q", {{"requirement_id": "REQ-DEMO-002", "question_id": "Q01"}}, ("REQ-DEMO-002",))):
    r = review(rid, d, g, src, False, sd, rel); out[n] = [r["result"], r.get("issues")]
r = review(rid, d, g, src, False, {{"requirement_id": "REQ-DEMO-002", "question_id": "Q02"}}, ("REQ-DEMO-002",)); out["rr_ok"] = [r["result"], r.get("issues")]
print(json.dumps(out))""")
    assert out["g"][0] == "PASS", out["g"]
    assert out["other_req_unbound"][0] == "FAIL" and any("必須對應本 TC 的某筆 decision_refs" in i for i in out["other_req_unbound"][1]), out["other_req_unbound"]
    for n in ("other_req_bound", "same_req_other_q"):
        r, issues = out[n]
        assert r == "FAIL" and any("和引用處" in i and "不符" in i for i in issues) and any("不是該決策點的" in i for i in issues), (n, issues)
    assert out["ok"][0] == "PASS", out["ok"]
    assert out["rr_other_req"][0] == "FAIL" and any("不在 related_requirement_ids" in i for i in out["rr_other_req"][1]), out["rr_other_req"]
    assert out["rr_same_req_other_q"][0] == "FAIL" and any("不是 REQ-DEMO-002/Q01 可用的依據" in i for i in out["rr_same_req_other_q"][1]), out["rr_same_req_other_q"]
    assert out["rr_ok"][0] == "PASS", out["rr_ok"]

# ---------------------------------------------------------------- P4R2-02：豁免項目形狀錯誤 → 結構錯誤，不拋例外
def test_waived_item_shape_errors_are_reported(tmp_path):
    root = mkroot(tmp_path)
    out = py(root, """
rid = F.new_run()
F.analyze(rid, [F.req(1, [F.dp("Q01", "undefined", "critical", coverage=F.cov(missing=[F.missing(13, "手冊 v01 的角色模型（見 7.1.1 角色說明）", "手冊 7.1.1 角色說明")]))],
                      ambiguity=F.amb("critical", "critical"))])
apr = F.waiting(rid)
def tryit(waived):
    try: F.approve(apr, resolutions=[{"requirement_id": "REQ-DEMO-001", "question_id": "Q01", "outcome": "waive_missing", "waived": waived, "rationale": "文件暫時無法取得"}]); return "accepted"
    except engine.EngineError as e: return "EngineError: " + str(e)
res = {n: tryit(w) for n, w in (("list", [{"cited_at": [], "name": "手冊 7.1.1 角色說明"}]), ("str", [{"cited_at": "第 13 行", "name": "x"}]), ("scalar", [5]),
                                  ("no_key", [{"name": "手冊 7.1.1 角色說明"}]), ("pin_bad", [{"pin": "SPEC-REF-001@1.0"}]), ("not_list", "x"))}
res["status"] = [store.load(f"approvals/{apr}.yaml")["status"], engine.load_run(rid)["status"]]
res["ok"] = tryit([{"cited_at": {**F.pin(), "line": 13}, "name": "手冊 7.1.1 角色說明"}])
print(json.dumps(res))""")
    for n in ("list", "str", "scalar", "no_key", "pin_bad", "not_list"):
        assert out[n].startswith("EngineError: ") and "waived" in out[n], (n, out[n])
    assert out["status"] == ["PENDING", "WAITING_HUMAN"]
    assert out["ok"] == "accepted"
    r = U.q(root, "approve", "APR-0001", "--decision", "approve", "--by", "oscar", "--resolution",
            json.dumps({"requirement_id": "REQ-DEMO-001", "question_id": "Q01", "outcome": "waive_missing", "waived": [{"cited_at": [], "name": "x"}], "rationale": "r"}))
    assert "Traceback" not in r.stderr                                   # CLI：已核准過的單被拒，且沒有 traceback
