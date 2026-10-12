"""同版本 CIA 的 reason=decision_added（ADR-012；需求 A 第 5 章 §8、附錄 A 5-19～5-21）：
同版本新回答、目前 revision 沒有引用的 CLR，經同版本 CIA 落地到新 revision（A4）→ G-IMPACT → apply --path a6。

狀態以正式流程建立：spec import、run new、dispatch、submit、evaluate_gate、approve、clarification new／answer／withdraw／applicability add、
req accept-declaration、clarification apply、migrate（legacy 資料由需求 A 之前的程式以它自己的正式流程產生）。例外（各自標明）：
沒有派發包的 revision 以 rm.save_requirements（唯一的需求寫入點）經 executor 產生，模擬 P4 之前的分析；派發包遺失的反例刪除派發包檔（標明的竄改）。
agent 的產出（artifact 檔）由 tests/helpers.write_artifact 寫入，這是「外部寫入」。"""
import json
from tests import p1_util as U
from tests.test_p4_dispatch import mkroot, py

FLOW = """
from tests import p5_flow as P
from tools.qaos import clr_lifecycle as L
SREF = lambda: F.sref("任何站台都不能刪除。")
def req1():
    return F.req(1, [F.dp("Q01", "defined_in_target", "none", known=[SREF()])])
def req2_open():
    '''REQ-DEMO-002/Q01 未定義（E4，minor）：G-SPEC 自動開 CLR，需求仍 ACTIVE。'''
    return F.req(2, [F.dp("Q01", "undefined", "minor", topic="error_code", subject="site.delete.error_code", decision_needed="刪除失敗時的錯誤代碼")],
                 ambiguity=F.amb("minor", "minor"), statement="刪除失敗的錯誤回應")
def req2_adopt(cid, statement="刪除失敗回傳錯誤代碼 E403"):
    '''REQ-DEMO-002/Q01 以 CLR 最新答案為依據（defined_by_decision，clarification 型 SourceRef）。'''
    return F.req(2, [F.dp("Q01", "defined_by_decision", "none", topic="error_code", subject="site.delete.error_code", known=[F.cref(cid, "E403")])], statement=statement)
def baseline():
    '''spec-to-testcase：R001（REQ-001 定義於目標、REQ-002 自動開 CLR）→ REQ-001 的一張 TC → ACTIVATE。回傳 (R001 pin, CLR ID, TC ID)。'''
    rid = F.new_run(); g = F.analyze(rid, [req1(), req2_open()]); assert g["result"] == "PASS", g
    dref = [{"requirement_id": "REQ-DEMO-001", "question_id": "Q01", "basis_ref": F.ident(SREF())}]
    d = F.design(rid, [F.tc(1, "REQ-DEMO-001", "刪除子站台被拒", techs=["negative"], types=["negative"], drefs=dref, srcs=[SREF()])], uncovered=["REQ-DEMO-002"])
    assert d["result"] == "PASS", d
    v = F.validate(rid, d["did"], g["rmid"]); assert v["result"] == "PASS", v
    F.approve(F.waiting(rid)); assert engine.load_run(rid)["status"] == "COMPLETED"
    cid = F.clrs(requirement_id="REQ-DEMO-002")[0]["clarification_id"]
    tc = [p.stem for p in store.glob("testcases/registry/TC-DEMO-*.yaml")]; assert len(tc) == 1
    return F.current_rev(), cid, tc[0]
def cia(from_rev, reason):
    try: return engine.new_run("spec-change-impact", {"spec_id": F.SPEC, "from_version": F.VER, "to_version": F.VER, "from_revision": from_rev, "reason": reason}, F.BY, new_request=True)["run_id"]
    except engine.EngineError as e: return {"error": str(e)}
def cir_for(rid, tc_id):
    '''CIA agent（impact 階段）：TC 只引用 REQ-001（unchanged）→ unaffected；REQ-002 changed。'''
    run = engine.load_run(rid); fr, to = run["from_requirement_model_revision"], run["requirement_model_revision"]
    a, b = rm.requirements_of(fr), rm.requirements_of(to)
    diff = [{"requirement_id": r, "change": "unchanged"} if a[r]["statement"] == b[r]["statement"] else
            {"requirement_id": r, "change": "changed", "detail": f"{a[r]['statement']} → {b[r]['statement']}"} for r in sorted(set(a) | set(b))]
    tpin = rm.tc_pin(tc_id, 1)
    return {"change_impact_id": f"CI-{F.SPEC}-1.0-1.0", "spec_id": F.SPEC, "from_version": "1.0", "to_version": "1.0", "from_rm_revision": fr, "to_rm_revision": to,
            "requirement_diff": diff, "pin_groups": [{"from_pin": tpin, "testcase_ids": [tc_id], "requirement_diff": diff}],
            "testcase_impact": [{"testcase_id": tc_id, "active_version": 1, "impact": "unaffected", "reason": "只驗 REQ-DEMO-001", "affected_requirement_ids": [], "pin_group_index": 0}],
            "summary": {"requirements_changed": sum(x["change"] == "changed" for x in diff), "requirements_added": 0, "requirements_removed": 0,
                        "testcases_affected": 0, "testcases_obsolete": 0, "testcases_unaffected": 1},
            "completeness": {"all_active_requirements_judged": True, "all_referencing_testcases_judged": True}}
def impact(rid, cir):
    refs_ = [{"entity_type": "SpecVersion", "id": F.SPEC, "version": "1.0"}, {"entity_type": "TestCaseVersion", "id": cir["testcase_impact"][0]["testcase_id"], "version": 1}]
    _, p = H.write_artifact(rid, "T1", "agent-change-impact-analyst", "ChangeImpactReport", cir, refs_, {"type": "SpecVersion", "ids": []}, "change-impact")
    assert engine.submit(rid, "T1", str(p))[0]
    return engine.evaluate_gate(rid, "T1")
"""

def test_decision_added_end_to_end_t0_a4_impact_apply(tmp_path):
    """主路徑（CLR-TXLOG-002 的形狀）：R001 之後才回答的同版本 CLR（requirement_clarified）→ 判定成立 → 同版本 CIA（reason=decision_added）
    → T0 派發包的決議快照帶到這張 CLR → 新 revision 以 clarification 型 SourceRef 採用 → G-SPEC PASS、A4（INCORPORATED）
    → G-IMPACT PASS（依 revision 讀需求）→ run COMPLETED → apply --path a6 --landed-in 這個 run → APPLIED。
    反例：回答之前不成立；最新答案 resolution 為 no_change 不成立（同一張 CLR 之後改答 requirement_clarified 才成立）；同 area 其他 spec 的 CLR 不算；
    reason 和判定不符（decision_applied、declaration_changed）或不認得 → run new 拒絕、不建立 run；新 revision 已引用 → 不成立。"""
    root = mkroot(tmp_path)
    out = py(root, FLOW + """
r1, cid, tc = baseline()
runs0 = len(store.glob("runs/RUN-*/run.yaml"))
before_answer = [rm.decision_added(r1), cia("R001", "decision_added")]
clr.answer(cid, "刪除失敗時沿用頁面的錯誤提示，不改需求。", "pm", "no_change", "oscar", new_request=True)
no_change = rm.decision_added(r1)
clr.answer(cid, "刪除失敗時回傳錯誤代碼 E403。", "pm", "requirement_clarified", "oscar", new_request=True)
other = clr.new("demo", "DEMO", F.OTHER, "1.0", "其他規格的問題", "oscar", consulted=[f"{F.OTHER}@1.0"], new_request=True)["clarification_id"]
clr.answer(other, "其他規格的答案。", "pm", "requirement_clarified", "oscar", new_request=True)
added = rm.decision_added(r1)
wrong = [cia("R001", "decision_applied"), cia("R001", "declaration_changed"), cia("R001", "decision_new")]
runs1 = len(store.glob("runs/RUN-*/run.yaml"))
rid = cia("R001", "decision_added")
g0 = F.analyze(rid, [req1(), req2_adopt(cid)], task="T0")
run = engine.load_run(rid)
pk = dispatch.load_packet(engine._task(run, "T0")["dispatch_packets"][-1])
r2 = run["requirement_model_revision"]; c = clr.load(cid)
after = {"r1": rm.decision_added(r1), "r2": rm.decision_added(r2)}
g1 = impact(rid, cir_for(rid, tc))
st = engine.load_run(rid)["status"]
T = "SPEC-DEMO-001@1.0:REQ-DEMO-002#Q01"
ap = P.apply_(cid, landed_in=[rid], targets=[T], no_keyword_reason="答案只改 REQ-DEMO-002 的錯誤代碼，沒有可用的關鍵字")
print(json.dumps({"before": before_answer, "no_change": no_change, "added": added, "other": other, "wrong": wrong, "runs": [runs0, runs1], "rid": rid,
                  "snap": [[s["clarification_id"], s["answer_rev"], s["resolution"]] for s in pk["resolutions"]], "g0": [g0["result"], g0["issues"]],
                  "from": run["from_requirement_model_revision"]["revision"], "to": r2["revision"], "clr": c["status"],
                  "landing": [[l["type"], l.get("rm_pin", {}).get("revision"), l.get("run_id")] for l in c.get("landings") or []], "after": after,
                  "g1": [g1["result"], g1["issues"]], "status": st, "apply": ap, "final": clr.load(cid)["status"], "r1_after_apply": rm.decision_added(r1)}))""")
    assert out["before"][0] == [] and "判定結果不是 decision_added" in out["before"][1]["error"]
    assert out["no_change"] == []                                                                    # 最新答案 no_change → 不成立
    assert len(out["added"]) == 1 and out["other"] not in out["added"]                                # 同 area 其他 spec 的 CLR 不算
    cid = out["added"][0]
    assert "判定結果不是 decision_applied" in out["wrong"][0]["error"]
    assert "判定結果不是 declaration_changed" in out["wrong"][1]["error"]
    assert "reason 只能是" in out["wrong"][2]["error"] and "decision_added" in out["wrong"][2]["error"]
    assert out["runs"][0] == out["runs"][1]                                                          # 拒絕時不建立 run
    assert [cid, 1, "requirement_clarified"] in out["snap"]                                          # T0 的決議快照帶到這張 CLR 的最新答案
    assert out["g0"][0] == "PASS", out["g0"]
    assert (out["from"], out["to"]) == ("R001", "R002")
    assert out["clr"] == "INCORPORATED" and out["landing"] == [["incorporated", "R002", out["rid"]]]   # A4
    assert out["after"] == {"r1": [], "r2": []}                                                       # 新 revision 已引用 → 不成立；同版本已有 revision 引用最新答案 → R001 也不成立
    assert out["g1"][0] == "PASS", out["g1"]
    assert out["status"] == "COMPLETED"
    assert "error" not in out["apply"], out["apply"]
    assert out["final"] == "APPLIED" and out["r1_after_apply"] == []                                  # APPLIED 已人工確認落地 → 不再成立

def test_decision_added_vs_decision_revised_when_cited_answer_is_revised(tmp_path):
    """新 revision 引用 rev 1 之後又改答 rev 2：引用舊 rev 屬 decision_revised，不是 decision_added（兩個判定互斥）。"""
    root = mkroot(tmp_path)
    out = py(root, FLOW + """
r1, cid, tc = baseline()
clr.answer(cid, "刪除失敗時回傳錯誤代碼 E403。", "pm", "requirement_clarified", "oscar", new_request=True)
rid = cia("R001", "decision_added")
g0 = F.analyze(rid, [req1(), req2_adopt(cid)], task="T0"); assert g0["result"] == "PASS", g0
r2 = engine.load_run(rid)["requirement_model_revision"]
clr.answer(cid, "刪除失敗時回傳錯誤代碼 E409。", "pm", "requirement_clarified", "oscar", new_request=True)
print(json.dumps({"added": rm.decision_added(r2), "revised": rm.outdated(r2)["decision_revised"], "as_added": cia(r2["revision"], "decision_added"),
                  "as_revised": cia(r2["revision"], "decision_revised")}))""")
    assert out["added"] == [] and out["revised"] is True
    assert "判定結果不是 decision_added" in out["as_added"]["error"]
    assert isinstance(out["as_revised"], str) and out["as_revised"].startswith("RUN-")

def test_decision_added_accept_declaration_inherits_parent_snapshot(tmp_path):
    """accept-declaration 產生的 revision 沒有經過分析（accepted_without_analysis）：沿用 parent 的決議快照判定，
    不能因為它建立得比答案晚就視為看過（否則 R001 之後回答的 CLR 會在 accept-declaration 之後消失）。"""
    root = mkroot(tmp_path)
    out = py(root, FLOW + """
r1, cid, tc = baseline()
clr.answer(cid, "刪除失敗時回傳錯誤代碼 E403。", "pm", "requirement_clarified", "oscar", new_request=True)
print(json.dumps({"cid": cid, "r1": rm.decision_added(r1)}))""")
    U.q(root, "spec", "reference", "add", "SPEC-DEMO-001@1.0", "--ref", "SPEC-REFB-001@1.0", "--role", "normative", "--by", "oscar", check=True)
    U.q(root, "req", "accept-declaration", "SPEC-DEMO-001@1.0", "--rev", "R001", "--reason", "補宣告", "--by", "oscar", check=True)
    out2 = py(root, """
r2 = rm.latest_pin(F.SPEC, F.VER); doc = rm.load_revision(r2)
print(json.dumps({"rev": r2["revision"], "accepted": doc.get("accepted_without_analysis"), "da": rm.decision_added(r2),
                  "run": engine.new_run("spec-change-impact", {"spec_id": F.SPEC, "from_version": F.VER, "to_version": F.VER, "from_revision": "R002", "reason": "decision_added"}, F.BY, new_request=True)["status"]}))""")
    assert out["r1"] == [out["cid"]]
    assert out2["rev"] == "R002" and out2["accepted"] is True
    assert out2["da"] == [out["cid"]] and out2["run"] == "RUNNING"

def test_decision_added_time_fallback_for_revision_without_packet(tmp_path):
    """沒有派發包的 revision（P4 之前的分析）：以 revision 建立時間判定——之前回答的不算，之後回答（新的 answer_rev）才算。"""
    root = mkroot(tmp_path, refs=())
    out = py(root, """
import time
from tools.qaos import operation
cid = clr.new("demo", "DEMO", F.SPEC, F.VER, "刪除失敗的錯誤代碼？", "oscar", consulted=[f"{F.SPEC}@{F.VER}"], requirement_id="REQ-DEMO-001", new_request=True)["clarification_id"]
clr.answer(cid, "E403。", "pm", "requirement_clarified", "oscar", new_request=True)
time.sleep(1.1)
req = F.req(1); req["status"] = "ACTIVE"
pin = operation.run_operation("test_internal", lambda: rm.save_requirements(F.SPEC, F.VER, [req], reason="P4 之前的分析（沒有派發包）", by="system", source_artifact_id="ART-RM-01M5DECADDED00000000000000"), new_request=True)
doc = rm.load_revision(pin); early = rm.decision_added(pin)
time.sleep(1.1)
clr.answer(cid, "E409。", "pm", "spec_updated", "oscar", new_request=True)
print(json.dumps({"packet": doc.get("dispatch_packet_sha256"), "early": early, "late": rm.decision_added(pin), "cid": cid}))""")
    assert out["packet"] is None
    assert out["early"] == [] and out["late"] == [out["cid"]]

def test_decision_added_on_legacy_r000(tmp_path):
    """R000（legacy，沒有建立時間與派發包；比照附錄 A 5-14 對 decision_applied 的處理）：同版本任何 ANSWERED／INCORPORATED、
    最新答案為 requirement_clarified／spec_updated、R000 沒有引用的 CLR 即成立。未回答的 CLR 不算；改答 out_of_scope → 不成立；撤回 → 不成立。"""
    from tests.test_p6_cia_manual_flows import legacy_migrated
    root, info = legacy_migrated()
    body = f"cid, open_ = {info['clr']!r}, {info['open_clr']!r}\n" + """
SPEC = "SPEC-AUTH-001"
def new_cia(reason):
    try: return engine.new_run("spec-change-impact", {"spec_id": SPEC, "from_version": "1.0", "to_version": "1.0", "from_revision": "R000", "reason": reason}, F.BY, new_request=True)["status"]
    except engine.EngineError as e: return {"error": str(e)}
r0 = rm.latest_pin(SPEC, "1.0")
legacy = rm.decision_added(r0)
o = rm.outdated(r0); first = [o["declaration_changed"], o["decision_revised"], rm.decision_applied(r0)]
ok = new_cia("decision_added")
clr.answer(cid, "與需求無關。", "pm", "out_of_scope", "oscar", new_request=True)
oos = [rm.decision_added(r0), new_cia("decision_added")]
clr.answer(cid, "密碼下限 10 碼。", "pm", "spec_updated", "oscar", new_request=True)
again = rm.decision_added(r0)
clr.withdraw(cid, "oscar", "問錯規格", new_request=True)
print(json.dumps({"rev": r0["revision"], "legacy": legacy, "first": first, "ok": ok, "oos": oos, "again": again, "withdrawn": rm.decision_added(r0)}))"""
    out = py(root, body)
    assert out["rev"] == "R000"
    assert out["legacy"] == [info["clr"]] and info["open_clr"] not in out["legacy"]                  # 未回答的 CLR 不算
    assert out["first"] == [False, False, False]                                                     # 其他三種判定都不成立（原本的缺口）
    assert out["ok"] == "RUNNING"
    assert out["oos"][0] == [] and "判定結果不是 decision_added" in out["oos"][1]["error"]
    assert out["again"] == [info["clr"]]
    assert out["withdrawn"] == []

def test_decision_added_does_not_block_skip_or_frozen_flows(tmp_path):
    """ADR-012 §3：decision_added 只是同版本 CIA 的 reason，不擋 _skip、不擋無 T0 流程的 run new（比照 decision_applied），只在 run 的 audit 記 WARN_DECISION_ADDED。"""
    root = mkroot(tmp_path)
    out = py(root, FLOW + """
r1, cid, tc = baseline()
clr.answer(cid, "刪除失敗時回傳錯誤代碼 E403。", "pm", "requirement_clarified", "oscar", new_request=True)
assert rm.decision_added(r1) == [cid]
s = engine.new_run("spec-to-testcase", {"spec_id": F.SPEC, "spec_version": F.VER}, F.BY, new_request=True)
t = engine.new_run("testcase-revision", {"testcase_id": tc, "reason": "改寫步驟", "spec_id": F.SPEC, "spec_version": F.VER}, F.BY, new_request=True)
warn = lambda r: [l for l in (store.ROOT / f"runs/{r['run_id']}/audit.log").read_text(encoding="utf-8").splitlines() if "WARN_DECISION_ADDED" in l]
print(json.dumps({"skip": [x["status"] for x in s["tasks"] if x["task_id"] == "T1"], "bound": s.get("requirement_model_revision", {}).get("revision"),
                  "trev": t["requirement_model_revision"]["revision"], "cid": cid, "warn": [warn(s), warn(t)]}))""")
    assert out["skip"] == ["DONE"] and out["bound"] == "R001"
    assert out["trev"] == "R001"
    for w in out["warn"]:                                                                             # 只提示：audit 記下尚未落地的 CLR 與建議的 reason
        assert len(w) == 1 and out["cid"] in w[0] and "reason=decision_added" in w[0], w

def test_decision_added_follows_dispatch_snapshot_not_timestamps(tmp_path):
    """ADR-012 §2：以決議快照判定，不以時間推定。
    (a) T0 派發之後、G-SPEC 持久化之前才回答（回答時間早於 revision 建立時間）→ 新 revision 沒看過 → 成立；
    (b) 派發前已回答、在快照中但分析沒有採用 → 不成立，run new 拒絕；
    (c) revision 記錄的派發包遺失 → 無法判定，run new 拒絕且不建立 run。"""
    root = mkroot(tmp_path)
    out = py(root, FLOW + """
import os
r1, cid, tc = baseline()
clr.answer(cid, "刪除失敗時回傳錯誤代碼 E403。", "pm", "requirement_clarified", "oscar", new_request=True)
# (b) 先派發（快照含 rev 0）→ T0 沒有採用（REQ-002 維持未定義，連回既有 CLR）→ R002
rb = cia("R001", "decision_added")
gb = F.analyze(rb, [req1(), req2_open()], task="T0"); assert gb["result"] == "PASS", gb
r2 = engine.load_run(rb)["requirement_model_revision"]
b = [rm.decision_added(r2), cia("R002", "decision_added")]
# (a) 從 R002 的角度新答案 rev 1：先派發 T0，再回答，然後才提交 → R003 沒看過 rev 1
clr.answer(cid, "改為回傳錯誤代碼 E409。", "pm", "requirement_clarified", "oscar", new_request=True)
ra = cia("R002", "decision_added")
dispatch.dispatch(ra, "T0")
clr.answer(cid, "最後確認：回傳錯誤代碼 E410。", "pm", "requirement_clarified", "oscar", new_request=True)
ga = F.analyze(ra, [req1(), req2_open()], task="T0"); assert ga["result"] == "PASS", ga
r3 = engine.load_run(ra)["requirement_model_revision"]; doc3 = rm.load_revision(r3)
answered = clr.load(cid)["answer_revisions"][-1]["answered_at"]
a = [rm.decision_added(r3), answered < doc3["created_at"] or answered == doc3["created_at"]]
# (c) R003 的派發包遺失
pk = next(e for t in engine.load_run(ra)["tasks"] for e in t.get("dispatch_packets") or [] if e["sha256"] == doc3["dispatch_packet_sha256"])
os.remove(store.abspath(pk["path"]))
n0 = len(store.glob("runs/RUN-*/run.yaml")); c_ = cia("R003", "decision_added"); n1 = len(store.glob("runs/RUN-*/run.yaml"))
print(json.dumps({"cid": cid, "b": b, "a": a, "c": c_, "n": [n0, n1]}))""")
    assert out["b"][0] == [] and "判定結果不是 decision_added" in out["b"][1]["error"]
    assert out["a"] == [[out["cid"]], True]
    assert "無法判定 decision_added" in out["c"]["error"] and "派發包" in out["c"]["error"] and out["n"][0] == out["n"][1]

def test_decision_added_landing_version_spec_updated_and_applicability(tmp_path):
    """落地途徑（ADR-012 §1）：
    - spec_updated 且 resulting_spec_version 指向其他版本 → 答案落在那個版本的 spec 原文，本版本不成立；沒有 resulting_spec_version → 成立；
    - 經人工適用紀錄（applicability）適用到同 area 另一個 spec 版本 → 該版本成立；適用紀錄補在 revision 之前 → 不成立（時間判定）。"""
    root = mkroot(tmp_path, refs=())
    out = py(root, """
import time
from tools.qaos import operation
def save(sid, n):
    req = F.req(1); req["status"] = "ACTIVE"; req["spec_id"] = sid; req["requirement_id"] = f"REQ-DEMO-{n:03d}"
    req["acceptance_criteria"][0]["ac_id"] = f"AC-DEMO-{n:03d}1"; req["spec_reference"]["spec_id"] = sid
    return operation.run_operation("test_internal", lambda: rm.save_requirements(sid, F.VER, [req], reason="P4 之前的分析（沒有派發包）", by="system",
                                   source_artifact_id="ART-RM-01M5DECADDED00000000000000"), new_request=True)
demo = save(F.SPEC, 1)
time.sleep(1.1)
cid = clr.new("demo", "DEMO", F.SPEC, F.VER, "刪除失敗的錯誤代碼？", "oscar", consulted=[f"{F.SPEC}@{F.VER}"], requirement_id="REQ-DEMO-001", new_request=True)["clarification_id"]
clr.answer(cid, "已寫入下一版 spec。", "pm", "spec_updated", "oscar", resulting_spec_version="1.1", new_request=True)
moved = rm.decision_added(demo)
cid2 = clr.new("demo", "DEMO", F.SPEC, F.VER, "刪除成功後的提示文字？", "oscar", consulted=[f"{F.SPEC}@{F.VER}"], requirement_id="REQ-DEMO-001", new_request=True)["clarification_id"]
clr.answer(cid2, "spec 原文已更正（同版本）。", "pm", "spec_updated", "oscar", new_request=True)
in_place = rm.decision_added(demo)
other = save(F.OTHER, 2)
time.sleep(1.1)
before_ap = rm.decision_added(other)
bh = sources.basis_hash(sources.basis(F.OTHER, F.VER))
clr.applicability_add(cid, 0, "REQ-DEMO-002", "site.delete.error_code", ["*"], {}, f"{F.OTHER}@{F.VER}", "同一條錯誤代碼規則", "oscar", confirm_basis=bh, new_request=True)
after_ap = rm.decision_added(other)
print(json.dumps({"cid": cid, "cid2": cid2, "moved": moved, "in_place": in_place, "before_ap": before_ap, "after_ap": after_ap}))""")
    cid = out["cid"]
    assert out["moved"] == []                                                                         # resulting_spec_version 1.1：不落在 1.0
    assert out["in_place"] == [out["cid2"]]                                                           # 沒有 resulting_spec_version：落在自身版本
    assert out["before_ap"] == []                                                                     # 沒有適用紀錄：CLR 不屬於 SPEC-OTHER-001
    assert out["after_ap"] == [cid]                                                                   # 適用紀錄晚於 revision 建立時間 → 成立
