"""P6-G3：完整 workflow 的整合流程（需求 A 第 6 章 §5.6、附錄 A 6-31、1-39；AC-A-B1-7、8；AC-09-15、17、28～32）。

每個案例使用獨立的暫存 root，狀態一律以正式流程建立：spec import、run new、dispatch、submit、evaluate_gate、approve、
run cancel、clarification answer／applicability add、clarification apply、migrate（legacy 資料由需求 A 之前的程式以它自己的正式流程產生）。
agent 的產出（artifact 檔）由 tests/helpers.write_artifact 寫入，這是「外部寫入」。"""
import json, pathlib, pytest
from tests import p1_util as U
from tests.test_p4_dispatch import mkroot, py

# ---------------------------------------------------------------- manual-test-to-regression 的完整流程（T1～T6）
MANUAL = """
from tests import p5_flow as P
from tools.qaos import clr_lifecycle as L, tc_ops
def two_targets():
    '''CLR 經 applicability 用到 REQ-DEMO-002；同一份 revision 中 REQ-001、REQ-002 都採用它（兩個採用目標）。'''
    rid, cid, apr = P.ra_p1()
    bh = sources.basis_hash(sources.basis(F.SPEC, F.VER))
    clr.applicability_add(cid, 0, "REQ-DEMO-002", "site.child.delete", ["admin"], {}, "SPEC-DEMO-001@1.0", "同一條規則", "oscar", confirm_basis=bh, new_request=True)
    res = {"source": F.cref(cid, "任何站台都不能刪除"), "decided_at": "2026-10-07", "adopted_side_index": 1}
    g = F.analyze(rid, [P.conflict_req(1, res), P.conflict_req(2, res)]); assert g["result"] == "PASS", g
    return rid, cid, g
def manual_run(cid, g, req="REQ-DEMO-002", n=3):
    '''manual-test-to-regression：T1 Designer（manual）→ G-DESIGN → T2 Validator PASS → T3 ACTIVATE。回傳 (run_id, TC ID)。'''
    src = F.cref(cid, "任何站台都不能刪除")
    rec = tc_ops.manual_new(f"手動測試：{req} 刪除子站台", "demo", "DEMO", ["進入站台列表", "刪除子站台"], "沒有刪除按鈕", "pass", F.BY, spec_id=F.SPEC, spec_version=F.VER, new_request=True)
    m = engine.new_run("manual-test-to-regression", {"manual_record_id": rec}, F.BY, new_request=True)["run_id"]
    t = F.tc(n, req, f"手動：刪除子站台被拒（{req}）", techs=["negative"], types=["negative"], mode="manual",
             drefs=[{"requirement_id": req, "question_id": "Q01", "basis_ref": F.ident(src)}], srcs=[src])
    did, pd = H.write_artifact(m, "T1", "agent-test-designer", "TestCaseDraft", {"mode": "manual", "spec_id": F.SPEC, "spec_version": F.VER, "testcases": [t]},
                               [{"entity_type": "Requirement", "id": req}], {"type": "ManualTestRecord", "ids": [rec]}, "test-design")
    rep = H.design_report(did, [t]); rep["mode"] = "manual"
    _, pr = H.write_artifact(m, "T1", "agent-test-designer", "TestDesignReport", rep, [{"entity_type": "Artifact", "id": did}], {"type": "TestCaseDraft", "ids": [did]}, "test-design")
    assert engine.submit(m, "T1", str(pd))[0] and engine.submit(m, "T1", str(pr))[0]; gd = engine.evaluate_gate(m, "T1"); assert gd["result"] == "PASS", gd
    before = set(p.stem for p in store.glob("testcases/registry/TC-DEMO-*.yaml"))
    _, pv = H.write_artifact(m, "T2", "agent-test-validator", "TestValidationReport", H.validation_report(did, g["rmid"], "PASS"),
                             [{"entity_type": "Artifact", "id": did}], {"type": "TestCaseDraft", "ids": [did]}, "validation")
    assert engine.submit(m, "T2", str(pv))[0]; gv = engine.evaluate_gate(m, "T2"); assert gv["result"] == "PASS", gv
    F.approve(F.waiting(m))
    new = sorted(set(p.stem for p in store.glob("testcases/registry/TC-DEMO-*.yaml")) - before)
    assert len(new) == 1, new
    return m, new[0]
def suite(m, tc_id, decision="approve"):
    '''T4 Regression Curator → G-REG → T5 UPDATE_SUITE_MEMBERSHIP 核准 → T6 WorkflowSummary。'''
    prop = {"suite_id": "SUITE-FULL", "suite_type": "full_regression", "base_suite_version": None, "trigger": "manual",
            "proposed_memberships": [{"testcase_id": tc_id, "pinned_version": "active", "justification": "手動測試轉回歸", "risk_tag": "site"}],
            "diff": {"add": [{"testcase_id": tc_id, "reason": "new"}], "remove": [], "repin": []},
            "selection_criteria": "manual 轉回歸", "summary": {"total": 1, "added": 1, "removed": 0, "repinned": 0}}
    _, p = H.write_artifact(m, "T4", "agent-regression-curator", "RegressionProposal", prop, [{"entity_type": "TestCase", "id": tc_id}], {"type": "Registry", "ids": []}, "regression")
    assert engine.submit(m, "T4", str(p))[0]; gr = engine.evaluate_gate(m, "T4"); assert gr["result"] == "PASS", gr
    apr = F.waiting(m); a = store.load(f"approvals/{apr}.yaml")
    F.approve(apr, decision=decision)
    return a["type"]
"""

def test_ac_a_b1_8_manual_full_flow_then_a6_landed_in(tmp_path):
    """AC-A-B1-8、附錄 A 6-31（第 6 章 §5.6 第 3 點）：manual-test-to-regression 有 spec 時以正式流程完整跑到 T6 COMPLETED
    （含 T5 UPDATE_SUITE_MEMBERSHIP 核准）並產生正式 TC；之後以該 manual run 作 a6 的 --landed-in。
    run 範圍限於最終 TestCaseDraft 各 TC 的 requirement_ids（REQ-002）：
    - 反例：T3 核准後、T4／T5 之前（run 是 RUNNING）→ 拒絕；
    - 反例：確認 REQ-001 的目標（在綁定 revision 中，但不在 run 範圍內）、延後 REQ-002 → 拒絕，CLR 不變；
    - 正例：確認 REQ-002、延後 REQ-001 → APPLIED，landing 記錄 landed_in＝manual run。
    沒有 spec 時 `run new` 拒絕（AC-09-23）由 test_p3_revisions.py::test_ac_09_23_manual_without_spec_is_refused 驗證。"""
    root = mkroot(tmp_path)
    out = py(root, MANUAL + """
from tools.qaos import trace
rid, cid, g = two_targets()
src = F.cref(cid, "任何站台都不能刪除")
P.ra_p3_design(rid, cid, g, extra_tcs=[F.tc(2, "REQ-DEMO-002", "刪除子站台被拒（REQ-002）", techs=["negative"], types=["negative"],
               drefs=[{"requirement_id": "REQ-DEMO-002", "question_id": "Q01", "basis_ref": F.ident(src)}], srcs=[src])])
m, tc_id = manual_run(cid, g)
T1, T2 = "SPEC-DEMO-001@1.0:REQ-DEMO-001#Q01", "SPEC-DEMO-001@1.0:REQ-DEMO-002#Q01"
tcs = [p.stem for p in store.glob("testcases/registry/TC-DEMO-*.yaml")]
concl = [f"{t}=updated" for t in tcs]
early = P.apply_(cid, landed_in=[m], targets=[T2], defer_targets=[f"{T1}=另一個 run 落地"], keywords=["刪除"], tc_conclusions=concl)
st_mid = engine.load_run(m)["status"]
atype = suite(m, tc_id)
run = engine.load_run(m)
h0 = P.clr_sha(cid)
out_scope = P.apply_(cid, landed_in=[m], targets=[T1], defer_targets=[f"{T2}=之後再確認"], keywords=["刪除"], tc_conclusions=concl)
h1 = P.clr_sha(cid)
ok = P.apply_(cid, landed_in=[m], targets=[T2], defer_targets=[f"{T1}=另一個 run 落地"], keywords=["刪除"], tc_conclusions=concl)
c = clr.load(cid)
v = store.load(store.tc_version_path(tc_id, 1))
print(json.dumps({"st_mid": st_mid, "early": early, "atype": atype, "status": run["status"], "tasks": {t["task_id"]: t["status"] for t in run["tasks"]},
                  "summary": [store.load(store.find_artifact(a))["artifact_type"] for t in run["tasks"] if t["task_id"] == "T6" for a in t.get("output_artifact_ids") or []],
                  "suites": [s["suite_id"] for s in trace.suites_of(tc_id)], "ptr": store.load(store.tc_pointer_path(tc_id))["status"],
                  "v_rev": v.get("requirement_model_revision"), "v_req": v["requirement_ids"], "bound": run["requirement_model_revision"],
                  "scope": sorted(L._run_scope(run) or ["<None：整份 revision>"]), "out_scope": out_scope, "h": [h0, h1], "ok": ok, "clr": c["status"], "landing": c["landings"][-1]}))""")
    assert out["st_mid"] == "RUNNING" and "不是 COMPLETED" in out["early"]["error"]              # T5 前不能作為 landed-in
    assert out["atype"] == "UPDATE_SUITE_MEMBERSHIP"
    assert out["status"] == "COMPLETED" and set(out["tasks"].values()) == {"DONE"}, out["tasks"]
    assert out["summary"] == ["WorkflowSummary"] and out["suites"] == ["SUITE-FULL"] and out["ptr"] == "ACTIVE"
    assert out["v_rev"] == out["bound"] and out["v_req"] == ["REQ-DEMO-002"]
    assert out["scope"] == ["REQ-DEMO-002"]
    assert "不含任何被 --target 確認的目標" in out["out_scope"]["error"] and out["h"][0] == out["h"][1]
    assert "error" not in out["ok"], out["ok"]
    assert out["clr"] == "APPLIED" and out["landing"]["path"] == "a6"
    lnd = out["landing"]
    assert lnd["landed_in"] and lnd["targets_confirmed"][0]["requirement_id"] == "REQ-DEMO-002"
    assert [d["target"] for d in lnd["targets_deferred"]] == ["SPEC-DEMO-001@1.0:REQ-DEMO-001#Q01"]

# ---------------------------------------------------------------- spec-change-impact 的完整流程（T0～T5）
CIA = """
import json, copy
from tools.qaos import engine, store, rm, gates, dispatch
from tests import helpers as H
BY = "oscar@example.com"; SPEC = "SPEC-AUTH-001"
def active():
    out = []
    for p in sorted(store.glob("testcases/registry/TC-AUTH-*.yaml")):
        d = store.load(p)
        if d["status"] == "ACTIVE": out.append((d["testcase_id"], d["active_version"], store.load(store.tc_version_path(d["testcase_id"], d["active_version"]))))
    return out
def pins():
    return {t: rm.tc_pin(t, v)["revision"] for t, v, _ in active()}
def cia_new(from_rev, reason, ver="1.0"):
    return engine.new_run("spec-change-impact", {"spec_id": SPEC, "from_version": ver, "to_version": ver, "from_revision": from_rev, "reason": reason}, BY, new_request=True)["run_id"]
def t0(rid, changes, ver="1.0"):
    '''T0 Spec Analyst：重新分析同一版本；changes = {requirement_id: 新 statement}（spec 內容相同、分析結論改變）。'''
    m = H.requirement_model(ver)
    for r in m["requirements"]:
        if r["requirement_id"] in changes: r["statement"] = changes[r["requirement_id"]]
    ch = next(v for v in store.load(store.spec_dir(SPEC) / "spec.yaml")["versions"] if v["spec_version"] == ver)["content_hash"]
    sa = {"spec_id": SPEC, "spec_version": ver, "content_hash": ch, "summary": "重新分析", "scope": {"in_scope": [], "out_of_scope": []},
          "requirement_ids": [r["requirement_id"] for r in m["requirements"]], "ambiguities": [], "constraints": [], "edge_case_candidates": [], "open_questions": []}
    refs_ = [{"entity_type": "SpecVersion", "id": SPEC, "version": ver}]
    _, p1 = H.write_artifact(rid, "T0", "agent-spec-analyst", "SpecAnalysis", sa, refs_, {"type": "SpecVersion", "ids": [f"{SPEC}@{ver}"]}, "spec-analysis")
    rmid, p2 = H.write_artifact(rid, "T0", "agent-spec-analyst", "RequirementModel", m, refs_, {"type": "SpecVersion", "ids": [f"{SPEC}@{ver}"]}, "requirements")
    assert engine.submit(rid, "T0", str(p1))[0] and engine.submit(rid, "T0", str(p2))[0]
    g = engine.evaluate_gate(rid, "T0"); assert g["result"] == "PASS", g
    return rmid
def rdiff(a, b):
    out = []
    for r in sorted(set(a) | set(b)):
        if r not in a: out.append({"requirement_id": r, "change": "added"})
        elif r not in b: out.append({"requirement_id": r, "change": "removed"})
        else:
            same = (a[r]["statement"], a[r]["acceptance_criteria"]) == (b[r]["statement"], b[r]["acceptance_criteria"])
            out.append({"requirement_id": r, "change": "unchanged"} if same else {"requirement_id": r, "change": "changed", "detail": f"{a[r]['statement']} → {b[r]['statement']}"})
    return out
def cir_for(rid):
    '''CIA agent（impact 階段）的判定：候選＝本 spec 全部 ACTIVE TC，依各自的 pin 分組；每組以自己的 from_pin 對 to_revision 比對。'''
    run = engine.load_run(rid); to = run["requirement_model_revision"]; fr = run["from_requirement_model_revision"]
    to_reqs = rm.requirements_of(to); groups = {}
    for t, v, _ in active(): groups.setdefault(json.dumps(rm.tc_pin(t, v), sort_keys=True), []).append((t, v))
    pg, impact = [], []
    for k, (pin_s, members) in enumerate(sorted(groups.items(), key=lambda x: json.loads(x[0])["revision"])):
        pin = json.loads(pin_s); d = rdiff(rm.requirements_of(pin), to_reqs); chg = {x["requirement_id"] for x in d if x["change"] != "unchanged"}
        pg.append({"from_pin": pin, "testcase_ids": [t for t, _ in members], "requirement_diff": d})
        for t, v in members:
            hit = sorted(set(store.load(store.tc_version_path(t, v))["requirement_ids"]) & chg)
            impact.append({"testcase_id": t, "active_version": v, "impact": "affected" if hit else "unaffected", "reason": "需求變更" if hit else "-",
                           "affected_requirement_ids": hit, "pin_group_index": k})
    top = rdiff(rm.requirements_of(fr), to_reqs)
    return {"change_impact_id": f"CI-{SPEC}-1.0-1.0", "spec_id": SPEC, "from_version": "1.0", "to_version": "1.0", "from_rm_revision": fr, "to_rm_revision": to,
            "requirement_diff": top, "pin_groups": pg, "testcase_impact": impact,
            "summary": {"requirements_changed": sum(x["change"] == "changed" for x in top), "requirements_added": 0, "requirements_removed": 0,
                        "testcases_affected": sum(i["impact"] == "affected" for i in impact), "testcases_obsolete": 0,
                        "testcases_unaffected": sum(i["impact"] == "unaffected" for i in impact)},
            "completeness": {"all_active_requirements_judged": True, "all_referencing_testcases_judged": True}}
def impact(rid, cir):
    refs_ = [{"entity_type": "SpecVersion", "id": SPEC, "version": "1.0"}] + [{"entity_type": "TestCaseVersion", "id": i["testcase_id"], "version": i["active_version"]} for i in cir["testcase_impact"]]
    cid, p = H.write_artifact(rid, "T1", "agent-change-impact-analyst", "ChangeImpactReport", cir, refs_, {"type": "SpecVersion", "ids": []}, "change-impact")
    assert engine.submit(rid, "T1", str(p))[0]
    return cid, engine.evaluate_gate(rid, "T1")
def design(rid, cid, cir, prefix, it=0, extra=()):
    '''T2 Designer（change）：只重產 affected 的 TC，supersedes 舊 ACTIVE 版本；extra 為 new_required 的新 TC。回傳 (draft artifact, 新稿)。'''
    base, _ = H.draft_set(prefix=prefix); new = []
    for i in cir["testcase_impact"]:
        if i["impact"] != "affected": continue
        old = store.load(store.tc_version_path(i["testcase_id"], i["active_version"]))
        d = copy.deepcopy(next(x for x in base if x["acceptance_criteria_ids"] == old["acceptance_criteria_ids"]))
        d.update(source="change_workflow", supersedes_testcase={"testcase_id": i["testcase_id"], "version": i["active_version"]}); new.append(d)
    new += [copy.deepcopy(x) for x in extra]
    rids = sorted({r for t in new for r in t["requirement_ids"]})
    did, pd = H.write_artifact(rid, "T2", "agent-test-designer", "TestCaseDraft", {"mode": "change", "spec_id": SPEC, "spec_version": "1.0", "change_impact_id": cir["change_impact_id"], "testcases": new},
                               [{"entity_type": "Requirement", "id": r} for r in rids] + [{"entity_type": "Artifact", "id": cid}], {"type": "ChangeImpactReport", "ids": [cid]}, "test-design", iteration=it)
    rep = H.design_report(did, new); rep["mode"] = "change"
    _, pr = H.write_artifact(rid, "T2", "agent-test-designer", "TestDesignReport", rep, [{"entity_type": "Artifact", "id": did}], {"type": "TestCaseDraft", "ids": [did]}, "test-design", iteration=it)
    assert engine.submit(rid, "T2", str(pd))[0] and engine.submit(rid, "T2", str(pr))[0]
    g = engine.evaluate_gate(rid, "T2"); assert g["result"] == "PASS", g
    return did, new
def validate(rid, did, rmid, it=0):
    _, p = H.write_artifact(rid, "T3", "agent-test-validator", "TestValidationReport", H.validation_report(did, rmid, "PASS"),
                            [{"entity_type": "Artifact", "id": did}], {"type": "TestCaseDraft", "ids": [did]}, "validation", iteration=it)
    assert engine.submit(rid, "T3", str(p))[0]; g = engine.evaluate_gate(rid, "T3"); assert g["result"] == "PASS", g
def compare(rid, cid, cir, new, it=0, verdict="changed", diffs=True):
    sup = [d for d in new if d.get("supersedes_testcase")]; add = [d for d in new if not d.get("supersedes_testcase")]
    vcr = {"change_impact_id": cir["change_impact_id"], "comparisons": [{"testcase_id": d["supersedes_testcase"]["testcase_id"], "old_version": d["supersedes_testcase"]["version"],
           "new_draft_id": d["draft_id"], "verdict": verdict, "field_diffs": [{"field": "expected_result", "old": "-", "new": d["expected_result"]}] if verdict == "changed" and diffs else [],
           "impacted_requirement_ids": d["requirement_ids"]} for d in sup] +
           [{"testcase_id": None, "old_version": None, "new_draft_id": d["draft_id"], "verdict": "added", "field_diffs": [], "impacted_requirement_ids": d["requirement_ids"]} for d in add],
           "retire_recommendations": [], "summary": {"unchanged": 0, "changed": len(sup), "added": len(add), "removed": 0}}
    aid, p = H.write_artifact(rid, "T4", "agent-change-impact-analyst", "VersionComparisonReport", vcr, [{"entity_type": "Artifact", "id": cid}], {"type": "ChangeImpactReport", "ids": [cid]}, "change-impact", iteration=it)
    ok, pr = engine.submit(rid, "T4", str(p))
    if not ok: return aid, {"submit": pr}
    return aid, engine.evaluate_gate(rid, "T4")
def full_cia(rid, changes, prefix):
    rmid = t0(rid, changes); cir = cir_for(rid); cid, g1 = impact(rid, cir); assert g1["result"] == "PASS", g1
    did, new = design(rid, cid, cir, prefix); validate(rid, did, rmid); _, g4 = compare(rid, cid, cir, new); assert g4["result"] == "PASS", g4
    apr = engine.load_run(rid)["waiting_on_approval_id"]; assert store.load(f"approvals/{apr}.yaml")["type"] == "APPLY_CHANGE"
    engine.approve(apr, "approve", BY, rationale="套用", new_request=True)
    return {"cir": cir, "new": [d["supersedes_testcase"]["testcase_id"] for d in new], "status": engine.load_run(rid)["status"],
            "ci": store.load(f"runs/{rid}/entities/change-impact.yaml")["status"]}
"""

def cia_py(root, body):
    return json.loads(U.py(root, CIA + body).stdout.strip().splitlines()[-1])

def legacy_migrated():
    """需求 A 之前的程式以正式流程產生 SPEC-AUTH-001@1.0 的 legacy RM 與 5 張 TC（沒有 pin）→ 新程式 migrate（R000、TC sidecar legacy_binding）。"""
    from tests import p3_legacy as LG
    root, info = LG.legacy_root()
    LG.migrate(root, "--cancel-run", info["running"])
    U.q(root, "maintenance", "end", "--by", "m", check=True)
    return root, info

def test_ac_09_28_29_30_two_rounds_same_version_cia_with_legacy_sidecar(tmp_path):
    """AC-09-28、29、30、AC-A-B1-7（測試 root 版的「同版本連續兩輪」）：同一個 root 依序執行兩輪完整 spec-change-impact
    （T0 重新分析 → T1 CIA impact → T2 Designer → T3 Validator → T4 compare → T5 APPLY_CHANGE）。
    起點：legacy 的 5 張 TC 由舊程式產生，移轉後以 sidecar 綁 R000（legacy_binding: true）。
    - 第一輪 R000→R001（declaration_changed）：REQ-AUTH-001 改變 → TC-A（001、002）affected 升 v2、版本檔綁 R001；TC-B（003～005）unaffected 留在 R000（sidecar）。
    - 第二輪 R001→R002（再次 declaration_changed）：REQ-AUTH-003 改變。CIR 必須有兩組（R000：TC-B；R001：TC-A）——legacy sidecar 與版本檔 pin 混合（AC-09-30）；
      TC-B 那組的 requirement_diff 是 R000→R002，含第一輪 REQ-AUTH-001 的變更（AC-09-29）。
      反例：只判 run 的 from 端那組（R001：TC-A）、缺少 TC-B → G-IMPACT FAIL（G2、G5）；TC-B 併到 R001 那組 → G4 FAIL。
    G1～G8 各自的反例見 test_p3_cia_groups.py::test_partition_violations_fail；DAILYREPORT 96 條另以真實資料複本驗收。"""
    root, info = legacy_migrated()
    tcs = info["tcs"]; assert len(tcs) == 5
    sc0 = {t: U.load(root, f"testcases/_bindings/{t}-v1.yaml") for t in tcs}
    assert all(s["requirement_model_revision"]["revision"] == "R000" and s["legacy_binding"] is True for s in sc0.values())
    U.q(root, "spec", "reference", "declare-empty", "SPEC-AUTH-001@1.0", "--reason", "移轉後補宣告", "--by", "oscar", check=True)
    r1 = cia_py(root, """
rid = cia_new("R000", "declaration_changed")
out = full_cia(rid, {"REQ-AUTH-001": "密碼長度必須大於或等於 8 個字元（含 8 字元）"}, "01BX5ZZKBKACTAV9WEVGEMMVR")
print(json.dumps({**out, "rid": rid, "pins": pins(), "groups": [[g["from_pin"]["revision"], g["testcase_ids"]] for g in out["cir"]["pin_groups"]],
                  "vers": {t: v for t, v, _ in active()}, "v2pin": {t: store.load(store.tc_version_path(t, 2)).get("requirement_model_revision", {}).get("revision") for t in out["new"]}}))""")
    assert r1["status"] == "COMPLETED" and r1["ci"] == "APPLIED"
    assert r1["groups"] == [["R000", tcs]]                                                       # 第一輪：全部是 legacy R000 一組
    A = sorted(r1["new"]); B = sorted(set(tcs) - set(A))
    assert len(A) == 2 and len(B) == 3
    assert r1["pins"] == {**{t: "R001" for t in A}, **{t: "R000" for t in B}}
    assert r1["v2pin"] == {t: "R001" for t in A} and all(r1["vers"][t] == 1 for t in B)
    for t in B: assert U.load(root, f"testcases/_bindings/{t}-v1.yaml") == sc0[t]                   # unaffected 保留原 pin（sidecar 不變）
    # 第二輪：再補一次宣告（informative 參考）→ declaration_changed
    (tmp_path / "ref.md").write_text("# 參考\n\n## 說明\n\n密碼規則補充。\n", encoding="utf-8")
    U.q(root, "spec", "import", tmp_path / "ref.md", "--spec-id", "SPEC-AUTHREF-001", "--version", "1.0", "--product", "demo", "--area", "AUTH", "--by", "oscar", check=True)
    U.q(root, "spec", "reference", "add", "SPEC-AUTH-001@1.0", "--ref", "SPEC-AUTHREF-001@1.0", "--role", "informative", "--by", "oscar", check=True)
    r2 = cia_py(root, """
rid = cia_new("R001", "declaration_changed")
CH = {"REQ-AUTH-001": "密碼長度必須大於或等於 8 個字元（含 8 字元）", "REQ-AUTH-003": "同一帳號連續 5 次密碼錯誤後鎖定 15 分鐘（以伺服器時間計）"}
rmid = t0(rid, CH); good = cir_for(rid)
# 反例 1：只判 run 的 from 端（R001）那組，缺少 TC-B（R000）的判定
k1 = next(k for k, g in enumerate(good["pin_groups"]) if g["from_pin"]["revision"] == "R001")
only = copy.deepcopy(good); only["pin_groups"] = [only["pin_groups"][k1]]
only["testcase_impact"] = [dict(i, pin_group_index=0) for i in only["testcase_impact"] if i["pin_group_index"] == k1]
_, bad1 = impact(rid, only)
# 反例 2：TC-B 併到 R001 那組（以 run 的 from_revision 比對）
merged = copy.deepcopy(good); g1 = merged["pin_groups"][k1]
g1["testcase_ids"] = [t for g in merged["pin_groups"] for t in g["testcase_ids"]]; merged["pin_groups"] = [g1]
for i in merged["testcase_impact"]: i["pin_group_index"] = 0
_, bad2 = impact(rid, merged)
cid, ok1 = impact(rid, good)
did, new = design(rid, cid, good, "01CX5ZZKBKACTAV9WEVGEMMVR"); validate(rid, did, rmid); _, g4 = compare(rid, cid, good, new)
run = engine.load_run(rid)
pk = {t: dispatch.load_packet(engine._task(run, t)["dispatch_packets"][-1])["rm_pins"] for t in ("T1", "T4")}
apr = engine.load_run(rid)["waiting_on_approval_id"]; engine.approve(apr, "approve", BY, rationale="套用", new_request=True)
print(json.dumps({"bad1": bad1, "bad2": bad2, "ok": ok1["result"], "ok_issues": ok1["issues"], "g4": g4["result"],
                  "groups": [[g["from_pin"]["revision"], g["testcase_ids"], {d["requirement_id"]: d["change"] for d in g["requirement_diff"]}] for g in good["pin_groups"]],
                  "impact": {i["testcase_id"]: [i["impact"], i["pin_group_index"]] for i in good["testcase_impact"]},
                  "new": [d["supersedes_testcase"]["testcase_id"] for d in new], "status": engine.load_run(rid)["status"],
                  "ci": store.load(f"runs/{rid}/entities/change-impact.yaml")["status"], "pins": pins(),
                  "pk": {t: [v["from"]["revision"], v["target"]["revision"], sorted(x["revision"] for x in v.get("pin_groups") or [])] for t, v in pk.items()},
                  "from_pin": good["from_rm_revision"]["revision"], "to_pin": good["to_rm_revision"]["revision"]}))""")
    assert r2["bad1"]["result"] == "FAIL" and any(i.startswith("G2") for i in r2["bad1"]["issues"]) and any(i.startswith("G5") for i in r2["bad1"]["issues"]), r2["bad1"]
    assert r2["bad2"]["result"] == "FAIL" and any(i.startswith("G4") for i in r2["bad2"]["issues"]), r2["bad2"]
    assert r2["ok"] == "PASS", r2["ok_issues"]
    g = {rev: (ids, d) for rev, ids, d in r2["groups"]}
    assert sorted(g) == ["R000", "R001"] and g["R000"][0] == B and g["R001"][0] == A               # AC-09-28、30：兩組、legacy sidecar 與版本檔 pin 混合
    assert g["R000"][1]["REQ-AUTH-001"] == "changed" and g["R000"][1]["REQ-AUTH-003"] == "changed"   # AC-09-29：R000→R002 涵蓋 R001 的變更
    assert g["R001"][1]["REQ-AUTH-001"] == "unchanged" and g["R001"][1]["REQ-AUTH-003"] == "changed"
    hit = [t for t, (imp, _) in r2["impact"].items() if imp == "affected"]
    assert len(hit) == 1 and hit[0] in B and r2["new"] == hit                                     # 第二輪影響 TC-B 中的 REQ-AUTH-003 那張
    assert r2["g4"] == "PASS" and r2["status"] == "COMPLETED" and r2["ci"] == "APPLIED"
    assert r2["pk"] == {"T1": ["R001", "R002", ["R000", "R001"]], "T4": ["R001", "R002", ["R000", "R001"]]}   # 第 5 章 §8：T1、T4 的派發包帶兩端與全部 pin_groups
    assert r2["pins"] == {**{t: "R001" for t in A}, **{t: "R000" for t in B if t != hit[0]}, hit[0]: "R002"}

# ---------------------------------------------------------------- AC-09-15：PLATFORMRULE 形狀（legacy R000 → 裁決改變 → 同版本 R001）
PLATFORM = """
from tools.qaos import clarification as clr
R5 = {"requirement_id": "REQ-AUTH-005", "version": 1, "spec_id": SPEC, "spec_version": "1.0", "type": "functional", "title": "密碼需含英文字母（PM 裁決）",
      "statement": "密碼必須包含至少一個英文字母", "acceptance_criteria": [{"ac_id": "AC-AUTH-006", "given": "使用者在設定密碼", "when": "輸入只有數字的密碼", "then": "系統拒絕並提示需含英文字母"}],
      "spec_reference": {"spec_id": SPEC, "spec_version": "1.0", "location": "§3.1 R2", "quote": ""}, "ambiguity": None, "risk": "medium", "status": "DRAFT", "history": []}
_orig_rm = H.requirement_model
def rm_with_ruling(ver="1.0", min_len="8"):
    m = _orig_rm(ver, min_len); m["requirements"].append(copy.deepcopy(R5))
    m["traceability"].append({"requirement_id": "REQ-AUTH-005", "spec_reference": R5["spec_reference"]}); return m
"""

def test_ac_09_15_platformrule_shape_same_version_cia(tmp_path):
    """AC-09-15（同版本 CIA，PLATFORMRULE 0.2 的形狀）：legacy RM 移轉為 R000（全部 ACTIVE、TC 以 sidecar 綁 R000），之後 PM 的裁決改變
    （CLR 追加 answer rev 1），spec 內容不變；同版本 CIA R000→R001（reason=declaration_changed：移轉後補宣告）由 T0 重新分析：
    REQ-AUTH-001 的 statement 改變、新增 REQ-AUTH-005（PLATFORMRULE CLR-003 的「新增需求＋改既有需求」形狀）。
    預期：CIR 列出受影響的需求（changed、added／new_required）與 TC（affected）；g_impact 讀 R000 與 R001，不是檢視：
    T0 之後把檢視 requirements.yaml 竄改回 R000 的內容（標明的竄改）——
    - 反例：依檢視寫的 CIR（requirement_diff 沒有 REQ-AUTH-005）→ G-IMPACT FAIL；
    - 正例：依 revision 寫的 CIR → PASS；Designer（affected 兩張 supersede、REQ-005 一張新 TC）→ Validator → compare → APPLY_CHANGE → APPLIED，
      新 TC 與新版本都綁 R001，unaffected 的 TC 留在 R000。"""
    root, info = legacy_migrated()
    U.q(root, "spec", "reference", "declare-empty", "SPEC-AUTH-001@1.0", "--reason", "移轉後補宣告", "--by", "oscar", check=True)
    view = pathlib.Path(root) / "artifacts/requirements/SPEC-AUTH-001/v1.0/requirements.yaml"
    r000_view = view.read_bytes()
    out = cia_py(root, PLATFORM + f"""
cid0 = {info["clr"]!r}
clr.answer(cid0, "密碼下限 8 碼，而且必須含英文字母。", "pm@example.com", "requirement_clarified", "oscar", new_request=True)   # 裁決改變（rev 1）
rid = cia_new("R000", "declaration_changed")
H.requirement_model = rm_with_ruling
rmid = t0(rid, {{"REQ-AUTH-001": "密碼長度必須大於或等於 8 個字元，且必須含英文字母"}})
H.requirement_model = _orig_rm
print(json.dumps({{"rid": rid, "rmid": rmid, "answer_revs": len(clr.load(cid0)["answer_revisions"])}}))""")
    rid, rmid = out["rid"], out["rmid"]
    assert out["answer_revs"] == 2
    assert view.read_bytes() != r000_view
    view.write_bytes(r000_view)                                                                  # 竄改：檢視改回 R000 的內容
    out = cia_py(root, f"rid, rmid = {rid!r}, {rmid!r}\n" + """
run = engine.load_run(rid)
good = cir_for(rid)
good["new_required"] = [{"requirement_id": "REQ-AUTH-005", "reason": "PM 裁決新增的需求"}]
good["summary"]["requirements_added"] = 1
# 反例：依檢視（R000 內容）寫的 CIR——to 端沒有 REQ-AUTH-005
viewish = copy.deepcopy(good); viewish.pop("new_required")
for blk in [viewish["requirement_diff"]] + [g["requirement_diff"] for g in viewish["pin_groups"]]:
    blk[:] = [d for d in blk if d["requirement_id"] != "REQ-AUTH-005"]
_, bad = impact(rid, viewish)
cid, ok = impact(rid, good)
nt = H.tc("TC-DRAFT-01DX5ZZKBKACTAV9WEVGEMMVZZ", "只有數字的密碼被拒（PM 裁決）", "REQ-AUTH-005", "AC-AUTH-006", "api", ["negative"], ["negative"],
          ["輸入長度 10 但只有數字的密碼", "送出"], "系統拒絕，提示需含英文字母", "§3.1 R2", prio="medium", risk="medium", mode="change", source_ref="new_required:REQ-AUTH-005")
did, new = design(rid, cid, good, "01DX5ZZKBKACTAV9WEVGEMMVR", extra=[nt]); validate(rid, did, rmid); _, g4 = compare(rid, cid, good, new)
apr = engine.load_run(rid)["waiting_on_approval_id"]; engine.approve(apr, "approve", BY, rationale="套用", new_request=True)
added = sorted({t for t, _, _ in active()} - {i["testcase_id"] for i in good["testcase_impact"]})
print(json.dumps({"from": run["from_requirement_model_revision"]["revision"], "to": run["requirement_model_revision"]["revision"], "bad": bad, "ok": ok,
                  "diff": {d["requirement_id"]: d["change"] for d in good["requirement_diff"]}, "impact": {i["testcase_id"]: i["impact"] for i in good["testcase_impact"]},
                  "g4": g4, "status": engine.load_run(rid)["status"], "ci": store.load(f"runs/{rid}/entities/change-impact.yaml")["status"], "added": added,
                  "pins": pins(), "new_req": [store.load(store.tc_version_path(t, 1))["requirement_ids"] for t in added]}))""")
    assert out["from"] == "R000" and out["to"] == "R001"
    assert out["bad"]["result"] == "FAIL" and any("REQ-AUTH-005" in i for i in out["bad"]["issues"]) and any(i.startswith("G7") for i in out["bad"]["issues"]), out["bad"]
    assert out["ok"]["result"] == "PASS", out["ok"]["issues"]
    assert out["diff"] == {"REQ-AUTH-001": "changed", "REQ-AUTH-002": "unchanged", "REQ-AUTH-003": "unchanged", "REQ-AUTH-004": "unchanged", "REQ-AUTH-005": "added"}
    aff = sorted(t for t, i in out["impact"].items() if i == "affected"); assert len(aff) == 2 and len(out["impact"]) == 5
    assert out["g4"]["result"] == "PASS" and out["status"] == "COMPLETED" and out["ci"] == "APPLIED"
    assert len(out["added"]) == 1 and out["new_req"] == [["REQ-AUTH-005"]]
    assert out["pins"] == {**{t: "R001" for t in aff + out["added"]}, **{t: "R000" for t in out["impact"] if t not in aff}}

# ---------------------------------------------------------------- AC-09-17、32：同一 run 多張 PENDING 核准單
def test_ac_09_17_32_cancel_run_with_several_pending_approvals(tmp_path):
    """AC-09-17、32（第 5 章 §10）：同一個 run 有多張 PENDING 核准單時，`run cancel` 把該 run **所有** PENDING 的核准單轉 CANCELLED
    （不只 waiting_on_approval_id），別的 run 的 PENDING 與本 run 已 DECIDED 的核准單不動；重送兩次只轉換一次、audit 不重複；revision 與 sidecar 保留。
    fixture：run B 以正式流程走到 ACTIVATE 核准單 PENDING（另有一張已 DECIDED 的 RESOLVE_AMBIGUITY）；run C 以正式流程走到 ACTIVATE PENDING。
    現行引擎的正式流程同一 run 一次只會有一張 PENDING，第二張 PENDING（NEEDS_DECISION）以故障注入寫入（標明；模擬舊程式或中斷留下的資料）。"""
    root = U.mkroot(); U.import_auth_spec(root)
    out = json.loads(U.py(root, """
import json, copy
from tests import p3_flow as F, helpers as H
from tools.qaos import engine, store
b = F.new_run(); rmid = F.analyze(b, crit=True)                     # RESOLVE_AMBIGUITY
amb = engine.load_run(b)["waiting_on_approval_id"]
print(json.dumps({"b": b, "amb": amb, "amb_type": store.load(f"approvals/{amb}.yaml")["type"]}))""").stdout.strip().splitlines()[-1])
    assert out["amb_type"] == "RESOLVE_AMBIGUITY"
    b, amb = out["b"], out["amb"]
    out = json.loads(U.py(root, f"""
import json, copy
from tests import p3_flow as F, helpers as H
from tools.qaos import engine, store
b, amb = {b!r}, {amb!r}
engine.approve(amb, "reject", F.BY, rationale="重新分析", new_request=True)            # DECIDED；T1 重開
rmid = F.analyze(b); F.design_and_validate(b, rmid)                                 # ACTIVATE PENDING
act = engine.load_run(b)["waiting_on_approval_id"]
c = F.new_run(); F.design_and_validate(c, rmid, prefix="01CX5ZZKBKACTAV9WEVGEMMVR")   # 別的 run 的 PENDING（最新 revision 全部 ACTIVE → 跳過 T1）
other = engine.load_run(c)["waiting_on_approval_id"]
# 故障注入：同一 run B 的第二張 PENDING 核准單
extra = copy.deepcopy(store.load(f"approvals/{{act}}.yaml")); extra.update(approval_id="APR-0900", type="NEEDS_DECISION", summary="故障注入：殘留的 PENDING", batch_items=[])
H.raw_save("approvals/APR-0900.yaml", extra)
print(json.dumps({{"act": act, "other": other, "c": c, "pin": engine.load_run(b)["requirement_model_revision"]}}))""").stdout.strip().splitlines()[-1])
    act, other, c, pin = out["act"], out["other"], out["c"], out["pin"]
    revdir = pathlib.Path(root) / "artifacts/requirements/SPEC-AUTH-001/v1.0/revisions"
    rev_before = {p.name: U.sha(p) for p in revdir.iterdir()}
    sc = pathlib.Path(root) / f"artifacts/requirements/_bindings/{b}.yaml"; sc_before = U.sha(sc)
    for _ in range(2): U.q(root, "run", "cancel", b, "--by", "oscar", check=True)          # 重送兩次
    st = {a: U.load(root, f"approvals/{a}.yaml")["status"] for a in (amb, act, "APR-0900", other)}
    assert st == {amb: "DECIDED", act: "CANCELLED", "APR-0900": "CANCELLED", other: "PENDING"}, st
    run = U.load(root, f"runs/{b}/run.yaml")
    assert run["status"] == "CANCELLED" and run["requirement_model_revision"] == pin
    assert U.load(root, f"runs/{c}/run.yaml")["status"] == "WAITING_HUMAN"
    log = (pathlib.Path(root) / f"runs/{b}/audit.log").read_text()
    assert log.count("CANCEL_RUN") == 1 and log.count(f"CANCEL_APPROVAL\t{act}") == 1 and log.count("CANCEL_APPROVAL\tAPR-0900") == 1 and f"CANCEL_APPROVAL\t{amb}" not in log
    assert {p.name: U.sha(p) for p in revdir.iterdir()} == rev_before and U.sha(sc) == sc_before   # revision 與 sidecar 保留

# ---------------------------------------------------------------- 附錄 A 1-39：CIA compare 的重做
def test_appendix_a_1_39_cia_compare_redo_iterations_and_packets(tmp_path):
    """附錄 A 1-39（第 1 章 §2.2）在 spec-change-impact 的整合流程（同版本 R001→R002）：
    - G-COMPARE structural FAIL（verdict changed 卻沒有 field_diffs）→ T4 回 READY、不計入迭代：iteration 仍 0，同一份派發包重新提交 → PASS；
    - APPLY_CHANGE 整批 reject → 回 T2（iteration 1）；下游 T3、T4 重設為 PENDING、清空本輪產出，iteration 不在退回時改；
      T3、T4 被推進成 READY 時才進入 iteration 1，要用新的派發包：沒有新包時提交被拒、沿用 iteration 0 的包被拒；舊派發紀錄保留；
      T1（CIA impact）不重做。重做後 APPLY_CHANGE approve → APPLIED、COMPLETED。"""
    root = U.mkroot(); U.import_auth_spec(root)
    U.py(root, "from tests import p3_flow as F\nF.full()")
    U.q(root, "spec", "reference", "declare-empty", "SPEC-AUTH-001@1.0", "--reason", "補宣告", "--by", "oscar", check=True)
    out = cia_py(root, """
def it_st(rid):
    run = engine.load_run(rid); return {t["task_id"]: [t["status"], t["iteration"], len(t.get("output_artifact_ids") or []), [e["iteration"] for e in t.get("dispatch_packets") or []]] for t in run["tasks"]}
rid = cia_new("R001", "declaration_changed")
rmid = t0(rid, {"REQ-AUTH-001": "密碼長度必須大於或等於 8 個字元（含 8 字元）"}); cir = cir_for(rid); cid, g1 = impact(rid, cir); assert g1["result"] == "PASS", g1
did, new = design(rid, cid, cir, "01BX5ZZKBKACTAV9WEVGEMMVR"); validate(rid, did, rmid)
_, c_bad = compare(rid, cid, cir, new, diffs=False)
s_after_bad = it_st(rid)
_, c_ok = compare(rid, cid, cir, new)
apr = engine.load_run(rid)["waiting_on_approval_id"]
t4_old_sha = engine._task(engine.load_run(rid), "T4")["dispatch_packets"][0]["sha256"]
engine.approve(apr, "reject", BY, rationale="比較報告要重做", new_request=True)
s_reject = it_st(rid)
did2, new2 = design(rid, cid, cir, "01CX5ZZKBKACTAV9WEVGEMMVR", it=1)
s_after_design = it_st(rid)
validate(rid, did2, rmid, it=1)
s_after_val = it_st(rid)
vcr = {"change_impact_id": cir["change_impact_id"], "comparisons": [{"testcase_id": d["supersedes_testcase"]["testcase_id"], "old_version": d["supersedes_testcase"]["version"],
       "new_draft_id": d["draft_id"], "verdict": "changed", "field_diffs": [{"field": "expected_result", "old": "-", "new": d["expected_result"]}], "impacted_requirement_ids": d["requirement_ids"]} for d in new2],
       "retire_recommendations": [], "summary": {"unchanged": 0, "changed": len(new2), "added": 0, "removed": 0}}
_, p = H.write_artifact(rid, "T4", "agent-change-impact-analyst", "VersionComparisonReport", vcr, [{"entity_type": "Artifact", "id": cid}], {"type": "ChangeImpactReport", "ids": [cid]}, "change-impact", iteration=1, packet=t4_old_sha)
no_pkg = engine.submit(rid, "T4", str(p))
dispatch.dispatch(rid, "T4", new_request=True)
_, p = H.write_artifact(rid, "T4", "agent-change-impact-analyst", "VersionComparisonReport", vcr, [{"entity_type": "Artifact", "id": cid}], {"type": "ChangeImpactReport", "ids": [cid]}, "change-impact", iteration=1, packet=t4_old_sha)
old_pkg = engine.submit(rid, "T4", str(p))
_, c2 = compare(rid, cid, cir, new2, it=1)
apr2 = engine.load_run(rid)["waiting_on_approval_id"]; engine.approve(apr2, "approve", BY, rationale="套用", new_request=True)
print(json.dumps({"c_bad": c_bad, "s_after_bad": s_after_bad, "c_ok": c_ok["result"], "s_reject": s_reject, "s_after_design": s_after_design, "s_after_val": s_after_val,
                  "no_pkg": no_pkg[1], "old_pkg": old_pkg[1], "c2": c2["result"], "final": it_st(rid), "status": engine.load_run(rid)["status"],
                  "ci": store.load(f"runs/{rid}/entities/change-impact.yaml")["status"], "pins": pins(), "new2": [d["supersedes_testcase"]["testcase_id"] for d in new2],
                  "vers": {t: [(v["version"], v["status"]) for v in store.load(store.tc_pointer_path(t))["versions"]] for t in [d["supersedes_testcase"]["testcase_id"] for d in new2]},
                  "ptr": {t: store.load(store.tc_pointer_path(t))["active_version"] for t in [d["supersedes_testcase"]["testcase_id"] for d in new2]}}))""")
    assert out["c_bad"]["result"] == "FAIL" and any("field_diffs" in i for i in out["c_bad"]["issues"]), out["c_bad"]
    assert out["s_after_bad"]["T4"][:2] == ["READY", 0] and out["s_after_bad"]["T4"][3] == [0]     # structural FAIL 不計入迭代
    assert out["c_ok"] == "PASS"
    r = out["s_reject"]
    assert r["T2"][:2] == ["READY", 1] and r["T1"][:2] == ["DONE", 0]                              # 退回 Designer；CIA impact 不重做
    assert r["T3"][:3] == ["PENDING", 0, 0] and r["T4"][:3] == ["PENDING", 0, 0]                    # 下游 PENDING、清空本輪產出，iteration 尚未改
    assert r["T4"][3] == [0] and r["T3"][3] == [0]                                                 # 舊派發紀錄保留
    assert out["s_after_design"]["T3"][:2] == ["READY", 1] and out["s_after_design"]["T4"][:2] == ["PENDING", 0]
    assert out["s_after_val"]["T4"][:2] == ["READY", 1]                                            # 被推進成 READY 時進入 iteration 1
    assert any("iteration 1 還沒有派發包" in x for x in out["no_pkg"]), out["no_pkg"]
    assert any("沿用舊 iteration 的派發包不能提交" in x for x in out["old_pkg"]), out["old_pkg"]
    assert out["c2"] == "PASS" and out["status"] == "COMPLETED" and out["ci"] == "APPLIED"
    f = out["final"]
    assert f["T2"][3] == [0, 1] and f["T3"][3] == [0, 1] and f["T4"][3] == [0, 1] and f["T1"][3] == [0]
    assert all(out["pins"][t] == "R002" for t in out["new2"])
    for t in out["new2"]:                                                                          # 被退回那輪的版本回 DRAFT（現行行為）；重做的版本成為 ACTIVE
        assert out["vers"][t] == [[1, "SUPERSEDED"], [2, "DRAFT"], [3, "ACTIVE"]] and out["ptr"][t] == 3

# ---------------------------------------------------------------- P6-G3-01：同版本 CIA 的 NO_IMPACT 走到 T6 COMPLETED（修正前 _advance 對已 DONE 的 T2 做 DONE → READY 而崩潰；base 2e01d4b 起就有）
def test_p6_g3_same_version_cia_no_impact_completes(tmp_path):
    """第 5 章 §8、AC-09-7 的延伸：只補宣告（declare-empty）→ 同版本 CIA R001→R002，T0 重新分析的需求內容和 R001 相同；
    CIA 判定全部 unaffected（NO_IMPACT）。預期：G-IMPACT PASS、change_impact 為 NO_IMPACT、T6 WorkflowSummary、run COMPLETED。"""
    root = U.mkroot(); U.import_auth_spec(root)
    U.py(root, "from tests import p3_flow as F\nF.full()")
    U.q(root, "spec", "reference", "declare-empty", "SPEC-AUTH-001@1.0", "--reason", "只補宣告", "--by", "oscar", check=True)
    out = cia_py(root, """
rid = cia_new("R001", "declaration_changed")
rmid = t0(rid, {}); cir = cir_for(rid)
assert all(i["impact"] == "unaffected" for i in cir["testcase_impact"])
try: _, g = impact(rid, cir); err = None
except Exception as e: g, err = {}, f"{type(e).__name__}: {e}"
run = engine.load_run(rid)
ci = store.load(f"runs/{rid}/entities/change-impact.yaml") if store.exists(f"runs/{rid}/entities/change-impact.yaml") else {}
print(json.dumps({"err": err, "g": g.get("result"), "status": run["status"], "ci": ci.get("status"), "t6": engine._task(run, "T6")["status"]}))""")
    assert out["err"] is None, out["err"]
    assert out["g"] == "PASS" and out["ci"] == "NO_IMPACT" and out["status"] == "COMPLETED" and out["t6"] == "DONE", out
