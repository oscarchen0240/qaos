"""P4：派發包在其他流程中的使用——manual-test-to-regression（AC-09-33）、spec-change-impact 的 pin_groups（第 1 章 §2.3）。
所有狀態以正式流程建立（spec import、run new、dispatch、submit、gate、approve、manual new）。"""
import json
from tests import p1_util as U
from tests.test_p4_dispatch import mkroot, py

def test_ac_09_33_manual_run_dispatch_decision_refs_and_pin(tmp_path):
    root = mkroot(tmp_path)
    out = py(root, """
from tools.qaos import tc_ops
r0 = F.new_run(); k = F.sref("任何站台都不能刪除。")
g = F.analyze(r0, [F.req(1, [F.dp("Q01", "defined_in_target", "none", known=[k])])]); engine.cancel(r0, F.BY, new_request=True)
rec = tc_ops.manual_new("手動測試：刪除子站台", "demo", "DEMO", ["進入站台列表", "嘗試刪除子站台"], "沒有刪除按鈕", "pass", F.BY, spec_id=F.SPEC, spec_version=F.VER, new_request=True)
run = engine.new_run("manual-test-to-regression", {"manual_record_id": rec}, F.BY, new_request=True); rid = run["run_id"]
e = dispatch.dispatch(rid, "T1", new_request=True); pk = dispatch.load_packet(e)
t = F.tc(1, "REQ-DEMO-001", "刪除子站台被拒（手動紀錄）", techs=["negative"], types=["negative"], mode="manual",
         drefs=[{"requirement_id": "REQ-DEMO-001", "question_id": "Q01", "basis_ref": F.ident(k)}], srcs=[k])
did, pd = H.write_artifact(rid, "T1", "agent-test-designer", "TestCaseDraft", {"mode": "manual", "spec_id": F.SPEC, "spec_version": F.VER, "testcases": [t]},
                           [{"entity_type": "Requirement", "id": "REQ-DEMO-001"}], {"type": "ManualTestRecord", "ids": [rec]}, "test-design")
rep = H.design_report(did, [t]); rep["mode"] = "manual"
_, pr = H.write_artifact(rid, "T1", "agent-test-designer", "TestDesignReport", rep, [{"entity_type": "Artifact", "id": did}], {"type": "TestCaseDraft", "ids": [did]}, "test-design")
assert engine.submit(rid, "T1", str(pd))[0] and engine.submit(rid, "T1", str(pr))[0]
gd = engine.evaluate_gate(rid, "T1")
_, pv = H.write_artifact(rid, "T2", "agent-test-validator", "TestValidationReport", H.validation_report(did, g["rmid"], "PASS"),
                         [{"entity_type": "Artifact", "id": did}], {"type": "TestCaseDraft", "ids": [did]}, "validation")
assert engine.submit(rid, "T2", str(pv))[0]
gv = engine.evaluate_gate(rid, "T2")
F.approve(F.waiting(rid))
tc_id = [p.stem for p in (store.ROOT / "testcases/registry").glob("TC-DEMO-*.yaml")][0]
v = store.load(store.tc_version_path(tc_id, 1))
print(json.dumps({"bound": run["requirement_model_revision"], "pk": pk["rm_pins"]["target"], "gd": gd["result"], "gd_issues": gd["issues"], "gv": gv["result"],
                  "v": v, "ptr": store.load(store.tc_pointer_path(tc_id))["status"]}))""")
    assert out["bound"] == out["pk"] and out["pk"]["revision"] == "R001"                     # run new 綁最新 revision；派發包帶同一個 RMPin
    assert out["gd"] == "PASS", out["gd_issues"]
    assert out["gv"] == "PASS" and out["ptr"] == "ACTIVE"
    v = out["v"]
    assert v["requirement_model_revision"] == out["bound"] and v["decision_refs"][0]["question_id"] == "Q01" and v["source_refs"][0]["type"] == "spec"

def test_cia_packet_carries_pin_groups(tmp_path):
    """spec-change-impact 的派發包帶全部 pin_groups 的 RMPin（候選 TC 各自的綁定）。"""
    root = mkroot(tmp_path)
    (tmp_path / "v11.md").write_text(__import__("tests.p4_flow", fromlist=["x"]).TARGET_TEXT + "\n## 新增\n\n新規則。\n", encoding="utf-8")
    U.q(root, "spec", "import", tmp_path / "v11.md", "--spec-id", "SPEC-DEMO-001", "--version", "1.1", "--product", "demo", "--area", "DEMO", "--by", "oscar", check=True)
    out = py(root, """
rid = F.new_run(); k = F.sref("任何站台都不能刪除。")
g = F.analyze(rid, [F.req(1, [F.dp("Q01", "defined_in_target", "none", known=[k])])])
dref = [{"requirement_id": "REQ-DEMO-001", "question_id": "Q01", "basis_ref": F.ident(k)}]
d = F.design(rid, [F.tc(1, "REQ-DEMO-001", "刪除子站台被拒", techs=["negative"], types=["negative"], drefs=dref)])
F.validate(rid, d["did"], g["rmid"]); F.approve(F.waiting(rid))
cia = engine.new_run("spec-change-impact", {"spec_id": F.SPEC, "from_version": "1.0", "to_version": "1.1"}, F.BY, new_request=True)
cur = cia["current_task_id"]                                         # to 端還沒分析 → T0 Spec Analyst；派發包同時帶 from 端候選的 pin_groups
e = dispatch.dispatch(cia["run_id"], cur, new_request=True)
print(json.dumps({"cur": cur, "agent": engine._task(cia, cur).get("agent_id"), "pk": dispatch.load_packet(e) if e else None,
                  "tc_pin": rm.tc_pin([p.stem for p in (store.ROOT / "testcases/registry").glob("TC-DEMO-*.yaml")][0], 1)}))""")
    assert out["agent"] == "agent-spec-analyst" and out["pk"]["target"]["spec_version"] == "1.1"
    assert out["pk"]["rm_pins"]["pin_groups"] == [out["tc_pin"]]
