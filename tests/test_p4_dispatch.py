"""P4 FIX-04：派發包（bin/qaos dispatch）、consulted_sources、G-SPEC 的派發包檢查、Validator 的派發包範圍（需求 A 第 1 章 §2；AC-04-1～5）。

每個案例使用獨立的暫存 root：spec 以 `spec import`、引用以 `spec reference add` 建立；run、派發、提交、gate、核准都走正式 API
（tests/p4_flow.py）。標明「竄改」的子例才在流程後修改檔案。"""
import json, pathlib, textwrap
from tests import p1_util as U

def py(root, body: str):
    code = ("import json\nfrom tests import p4_flow as F\nfrom tools.qaos import engine, store, rm, gates, sources, dispatch, decisions, clarification as clr\n"
            "from tests import helpers as H\n" + textwrap.dedent(body))
    return json.loads(U.py(root, code).stdout.strip().splitlines()[-1])

def mkroot(tmp_path, refs=("normative",), ref2=False):
    """SPEC-DEMO-001（目標）；refs 為空 → 沒有宣告（undeclared）；否則 normative 引用 SPEC-REF-001；ref2=True 另 normative 引用 SPEC-REFB-001。"""
    from tests import p4_flow as F
    root = U.mkroot()
    for sid, text in ((F.SPEC, F.TARGET_TEXT), (F.REF, F.REF_TEXT), (F.REF2, F.REF2_TEXT), (F.OTHER, F.OTHER_TEXT)):
        f = tmp_path / f"{sid}.md"; f.write_text(text, encoding="utf-8")
        U.q(root, "spec", "import", f, "--spec-id", sid, "--version", "1.0", "--product", "demo", "--area", "DEMO", "--by", "oscar", check=True)
    for role in refs:
        U.q(root, "spec", "reference", "add", f"{F.SPEC}@1.0", "--ref", f"{F.REF}@1.0", "--role", role, "--by", "oscar", check=True)
    if ref2: U.q(root, "spec", "reference", "add", f"{F.SPEC}@1.0", "--ref", f"{F.REF2}@1.0", "--role", "normative", "--by", "oscar", check=True)
    return root

def task(root, rid, tid):
    return next(t for t in U.load(root, f"runs/{rid}/run.yaml")["tasks"] if t["task_id"] == tid)

OK_REQ = """
F.req(1, [F.dp("Q01", "defined_in_target", "none", known=[F.sref("任何站台都不能刪除。")])])
"""

# ---------------------------------------------------------------- AC-04-1：同一 iteration 只能派發一次
def test_ac_04_1_dispatch_once_per_iteration(tmp_path):
    root = mkroot(tmp_path)
    rid = py(root, "print(json.dumps(F.new_run()))")
    r = U.q(root, "dispatch", rid, "T1", check=True)
    e = task(root, rid, "T1")["dispatch_packets"]
    assert len(e) == 1 and e[0]["iteration"] == 0 and e[0]["path"] == f"runs/{rid}/dispatch/T1-iter0.yaml"
    assert U.sha(pathlib.Path(root) / e[0]["path"]) == e[0]["sha256"] and e[0]["sha256"] in r.stdout
    pk = U.load(root, e[0]["path"])
    assert pk["target"]["spec_id"] == "SPEC-DEMO-001" and pk["iteration"] == 0 and pk["references_status"] == "declared"
    assert [(n["spec_id"], n["required"]) for n in pk["closure"]] == [("SPEC-REF-001", True)]
    assert pk["basis_hash"] == py(root, 'print(json.dumps(sources.basis_hash(sources.basis("SPEC-DEMO-001", "1.0"))))')
    before = U.snapshot(root)
    r2 = U.q(root, "dispatch", rid, "T1", "--new-request")
    assert r2.returncode != 0 and "同一 iteration 只能派發一次" in r2.stderr
    d = U.diff(before, U.snapshot(root))
    assert not d["changed"] and not d["removed"] and not [p for p in d["added"] if not p.startswith(("operations/", "locks/"))], d
    assert task(root, rid, "T1")["dispatch_packets"] == e
    # 不需要派發包的 task（approval）被拒
    r3 = U.q(root, "dispatch", rid, "T4")
    assert r3.returncode != 0 and "不需要派發包" in r3.stderr

# ---------------------------------------------------------------- AC-04-5：額外來源必須附理由
def test_ac_04_5_extra_requires_reason(tmp_path):
    root = mkroot(tmp_path)
    rid = py(root, "print(json.dumps(F.new_run()))")
    r = U.q(root, "dispatch", rid, "T1", "--extra", "SPEC-OTHER-001@1.0")
    assert r.returncode != 0 and "--reason" in r.stderr
    out = py(root, f"""
try: dispatch.dispatch("{rid}", "T1", [{{"ref": "SPEC-OTHER-001@1.0", "reason": "  "}}]); print(json.dumps("accepted"))
except dispatch.DispatchError as e: print(json.dumps(str(e)))""")
    assert "沒有附理由" in out
    assert "dispatch_packets" not in task(root, rid, "T1")
    U.q(root, "dispatch", rid, "T1", "--extra", "SPEC-OTHER-001@1.0", "--reason", "站台規則引用的補充說明", check=True)
    pk = U.load(root, task(root, rid, "T1")["dispatch_packets"][0]["path"])
    x = pk["extra_inputs"]
    assert len(x) == 1 and x[0]["kind"] == "spec_pin" and x[0]["reason"] == "站台規則引用的補充說明"
    assert x[0]["sha256"] == x[0]["pin"]["content_hash"] == py(root, 'print(json.dumps(F.pin("SPEC-OTHER-001")["content_hash"]))')

# ---------------------------------------------------------------- AC-04-2：核准後重開（iteration+1），沿用舊派發包提交 → 拒絕
def test_ac_04_2_reopened_task_needs_new_packet(tmp_path):
    root = mkroot(tmp_path)
    out = py(root, """
rid = F.new_run()
crit = F.req(1, [F.dp("Q01", "conflict", "critical", sides=[F.sref("| 子站台：刪除 | 可操作 | 可操作 |", loc="§角色與權限"), F.sref("任何站台都不能刪除。")],
                      note="表格允許刪除子站台；刪除規則禁止", resolution=None, decision_needed="以哪一側為準")], ambiguity=F.amb("critical", "critical"))
g = F.analyze(rid, [crit]); apr = F.waiting(rid)
old = H.packet_sha(rid, "T1", auto=False)
F.approve(apr, resolutions=[{"requirement_id": "REQ-DEMO-001", "question_id": "Q01", "outcome": "select_interpretation", "source": None, "rationale": "以刪除規則為準：任何站台都不能刪除"}])
t1 = engine._task(engine.load_run(rid), "T1")
stale0 = F.analyze(rid, [crit], packet=old)                         # 還沒有新派發包
H.packet_sha(rid, "T1")                                               # 派發 iteration 1
stale = F.analyze(rid, [crit], packet=old)                          # 有新派發包，但產出沿用舊的
fresh = F.analyze(rid, [F.req(1, [F.dp("Q01", "conflict", "critical", sides=crit["decision_points"][0]["conflict_sides"], note="x",
             resolution={"source": F.aref(apr, 0, "以刪除規則為準"), "decided_at": "2026-10-07", "adopted_side_index": 1})], ambiguity=F.amb("none", "critical"))])
print(json.dumps({"g": g["result"], "iter": t1["iteration"], "status": t1["status"], "stale0": stale0.get("submit"), "stale": stale.get("submit"), "fresh": fresh.get("result"), "fresh_issues": fresh.get("issues"),
                  "packets": [e["iteration"] for e in engine._task(engine.load_run(rid), "T1")["dispatch_packets"]]}))""")
    assert out["g"] == "PASS" and out["iter"] == 1 and out["status"] == "READY"
    assert out["stale0"] and all("iteration 1 還沒有派發包" in p for p in out["stale0"]), out["stale0"]
    assert out["stale"] and any("沿用舊 iteration 的派發包不能提交" in p for p in out["stale"]), out["stale"]
    assert out["fresh"] == "PASS", out["fresh_issues"]
    assert out["packets"] == [0, 1]

# ---------------------------------------------------------------- AC-04-3：consulted_sources 的 hash 不符 → G-SPEC FAIL；必讀參考沒查也沒列 → FAIL
def test_ac_04_3_consulted_hash_and_required_reading(tmp_path):
    root = mkroot(tmp_path, ref2=True)
    out = py(root, f"""
rid = F.new_run(); r = {OK_REQ.strip()}
bad = [{{**F.pin(), "content_hash": "0" * 64, "read_scope": "full"}}, {{**F.pin("SPEC-REF-001"), "read_scope": "full"}}, {{**F.pin("SPEC-REFB-001"), "read_scope": "full"}}]
g1 = F.analyze(rid, [r], consulted=bad)
outside = [{{**F.pin(), "read_scope": "full"}}, {{**F.pin("SPEC-REF-001"), "read_scope": "full"}}, {{**F.pin("SPEC-REFB-001"), "read_scope": "full"}}, {{**F.pin("SPEC-OTHER-001"), "read_scope": "sections", "sections": ["§無關"]}}]
g2 = F.analyze(rid, [r], consulted=outside)
skip = [{{**F.pin(), "read_scope": "full"}}, {{**F.pin("SPEC-REF-001"), "read_scope": "full"}}]
g3 = F.analyze(rid, [r], consulted=skip)
listed = F.req(1, [F.dp("Q01", "defined_in_target", "none", known=[F.sref("任何站台都不能刪除。")],
                        coverage=F.cov(consulted=[F.pin(), F.pin("SPEC-REF-001")], unconsulted=[{{"pin": F.pin("SPEC-REFB-001"), "reason": "out_of_scope", "note": "出金核實與站台刪除無關"}}]))])
g4 = F.analyze(rid, [listed], consulted=skip)
print(json.dumps([g1["result"], g1["issues"], g2["result"], g2["issues"], g3["result"], g3["issues"], g4["result"], g4["issues"]]))""")
    r1, i1, r2, i2, r3, i3, r4, i4 = out
    assert r1 == "FAIL" and any("hash 和派發包不符" in i and "SPEC-DEMO-001" in i for i in i1), i1
    assert r2 == "FAIL" and any("SPEC-OTHER-001" in i and "不在派發包內" in i for i in i2), i2
    assert r3 == "FAIL" and any("必讀參考 SPEC-REFB-001@1.0" in i for i in i3), i3
    assert r4 == "PASS", i4                                              # 範例 H：已定義時，範圍外的 normative 參考列為 out_of_scope 合法

def test_ac_04_3_tampered_reference_file_fails_gate(tmp_path):
    """竄改反例：派發後改動閉包內參考 spec 的實體檔 → consulted 的 hash 和實體檔不符，G-SPEC FAIL。"""
    root = mkroot(tmp_path)
    rid = py(root, "rid = F.new_run(); H.packet_sha(rid, 'T1'); print(json.dumps(rid))")
    p = next(pathlib.Path(root).glob("specs/demo/DEMO/SPEC-REF-001/*.md")); p.write_text(p.read_text(encoding="utf-8") + "竄改\n", encoding="utf-8")
    out = py(root, f"""g = F.analyze("{rid}", [{OK_REQ.strip()}]); print(json.dumps([g["result"], g["issues"]]))""")
    assert out[0] == "FAIL" and any("SPEC-REF-001" in i for i in out[1]), out[1]

# ---------------------------------------------------------------- AC-04-4：Draft 用到派發包範圍外的來源 → Validator 必須報 missing_reference
def test_ac_04_4_out_of_scope_source_needs_missing_reference(tmp_path):
    root = mkroot(tmp_path)
    out = py(root, f"""
zone = clr.new("demo", "ZONE", "SPEC-OTHER-001", "1.0", "其他功能區的已回答問題", "oscar", new_request=True)   # 入口 D：不屬於目標或引用的 area
clr.answer(zone["clarification_id"], "其他功能區的規則：一律保留紀錄。", "pm", "requirement_clarified", "oscar", new_request=True)
rid = F.new_run(); g = F.analyze(rid, [{OK_REQ.strip()}])
k = F.ident(F.sref("任何站台都不能刪除。"))
dref = [{{"requirement_id": "REQ-DEMO-001", "question_id": "Q01", "basis_ref": k}}]
outside = F.cref(zone["clarification_id"], "一律保留紀錄")                # 合法的 SourceRef（hash、quote 都對），但不在 Validator 的派發包範圍內
t1 = F.tc(1, "REQ-DEMO-001", "刪除子站台被拒", techs=["negative"], types=["negative"], drefs=dref, srcs=[outside])
t2 = F.tc(2, "REQ-DEMO-001", "站台列表沒有刪除按鈕", drefs=dref, srcs=[F.sref("任何站台都不能刪除。")])
d = F.design(rid, [t1, t2])
v1 = F.validate(rid, d["did"], g["rmid"], "PASS")
v2 = F.validate(rid, d["did"], g["rmid"], "FAIL", [F.missing_ref_issue(t1["draft_id"])])
run = engine.load_run(rid)
print(json.dumps({{"g": g["result"], "d": d["result"], "v1": v1, "v2": v2["result"], "v2_layer": v2["layer"], "t1": t1["draft_id"], "t2": t2["draft_id"],
                  "cur": run.get("current_task_id"), "t2iter": engine._task(run, "T2")["iteration"]}}))""")
    assert out["g"] == "PASS" and out["d"] == "PASS"
    v1 = out["v1"]
    assert v1["result"] == "FAIL" and v1["layer"] == "structural"
    assert any(out["t1"] in i and "missing_reference" in i for i in v1["issues"]) and not any(out["t2"] in i for i in v1["issues"]), v1["issues"]
    assert out["v2"] == "FAIL" and out["v2_layer"] == "semantic"          # 有回報 → 結構檢查通過，依 Validator 的 FAIL 退回 Designer
    assert out["cur"] == "T2" and out["t2iter"] == 1
