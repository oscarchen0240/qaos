"""P5 Codex 審查（requirement-a-p5-code-review.md 的 P5-01～03、-r2.md 的 P5-R2-01、03、04）的修正與補測。
狀態都以正式流程建立；標明「函式層」的子例直接呼叫內部函式。"""
import json
from tests import p1_util as U
from tests.test_p4_dispatch import mkroot, py
from tests.test_p5_paths import BUG, HDR

# 退回後重做：控制的是 agent 新產出的合法 artifact ID（不改 runtime 狀態），讓「舊稿 ID 大、新稿 ID 小」，檔名排序會選到舊稿。
REDO = BUG + """
from tools.qaos import ids
_q = []; _orig = ids.artifact_id
ids.artifact_id = lambda t: _q.pop(0) if (t == "BugDraft" and _q) else _orig(t)
T = "SPEC-DEMO-001@1.0:REQ-DEMO-001#Q01"
def adopt(cid):
    src = F.cref(cid, "任何站台都不能刪除")
    return {"srcs": [src], "drefs": [{"requirement_id": "REQ-DEMO-001", "question_id": "Q01", "basis_ref": F.ident(src)}]}
def redo_run(cid, first, second, old_id, new_id):
    '''第一稿（old_id）→ Validator PASS → 人 reject OPEN_BUG → Bug Analyst 重做第二稿（new_id）→ Validator PASS → 核准 → COMPLETED。'''
    b, evd = bug_run()
    _q[:] = [old_id]; bd1 = bug_draft(b, evd, **(adopt(cid) if first else {}))
    assert bug_validate(b, bd1, evd, "PASS")["result"] == "PASS"
    F.approve(F.waiting(b), decision="reject", rationale="重寫")
    _q[:] = [new_id]; bd2 = bug_draft(b, evd, **(adopt(cid) if second else {}))
    assert bug_validate(b, bd2, evd, "PASS")["result"] == "PASS"
    F.approve(F.waiting(b))
    run = engine.load_run(b); t1 = next(t for t in run["tasks"] if t["task_id"] == "T1")
    st = {a: store.load(store.find_artifact(a))["status"] for a in (bd1, bd2)}
    return b, {"run": run["status"], "t1_out": t1["output_artifact_ids"], "bd": [bd1, bd2], "status": st, "final": L._final_bugdraft(b)["artifact_id"]}
"""

def test_p5_01_final_bugdraft_is_this_round_output(tmp_path):
    """P5-01／P5-R2-01（第 6 章 §5.6、附錄 A 6-31）：退回重做後，舊稿仍是 VALID 而且 ID 較大；最終稿必須是本輪產出、最終 Validator 審過的那份。
    反例：只有被退回的舊稿採用 CLR → a6 以這個 run 為 landed-in 必須拒絕，CLR 不變。正例（反方向）：新稿採用、舊稿沒有 → a6 通過。"""
    root = mkroot(tmp_path)
    out = py(root, REDO + """
rid0, cid = e4_clr()
b1, r1 = redo_run(cid, True, False, "ART-BD-01ARZ3NDEKTSV4RRFFQ69G5FAZ", "ART-BD-01ARZ3NDEKTSV4RRFFQ69G5FAA")
s1 = clr.load(cid)["status"]
cands = L.impact(cid, ["刪除"], [], "oscar", new_request=True)["candidates"]; concl = [f"{x['tc_id']}=not_affected" for x in cands]
h0 = P.clr_sha(cid)
bad = P.apply_(cid, landed_in=[b1], targets=[T], keywords=["刪除"], tc_conclusions=concl)
h1 = P.clr_sha(cid); s2 = clr.load(cid)["status"]
b2, r2 = redo_run(cid, False, True, "ART-BD-01ARZ3NDEKTSV4RRFFQ69G5FBZ", "ART-BD-01ARZ3NDEKTSV4RRFFQ69G5FBA")
ok = P.apply_(cid, landed_in=[b2], targets=[T], keywords=["刪除"], tc_conclusions=concl)
print(json.dumps({"r1": r1, "s1": s1, "bad": bad, "h": [h0, h1], "s2": s2, "r2": r2, "ok": ok, "s3": clr.load(cid)["status"]}, default=str))""")
    r1, r2 = out["r1"], out["r2"]
    # 反例的前提：run 完成；T1 本輪只剩新稿；舊稿仍 VALID（檔名排序會選到它）；第一稿已讓 CLR INCORPORATED
    assert r1["run"] == "COMPLETED" and r1["t1_out"] == [r1["bd"][1]] and r1["status"] == {r1["bd"][0]: "VALID", r1["bd"][1]: "VALID"}, r1
    assert out["s1"] == "INCORPORATED"
    assert r1["final"] == r1["bd"][1]                                                     # 最終稿是本輪新稿，不是 ID 較大的舊稿
    assert "指定的目標不在解析結果中" in out["bad"].get("error", ""), out["bad"]                # 目標只來自被退回的舊稿，解析不到
    assert out["h"][0] == out["h"][1] and out["s2"] == "INCORPORATED"                        # 拒絕時 CLR 不變
    # 正例：新稿（ID 較小）採用、舊稿沒有 → 合法落地不會被舊稿遮掉
    assert r2["run"] == "COMPLETED" and r2["final"] == r2["bd"][1] and r2["status"][r2["bd"][0]] == "VALID", r2
    assert "error" not in out["ok"] and out["s3"] == "APPLIED", out["ok"]

def test_p5_01_final_draft_must_match_validator(tmp_path):
    """函式層：產生者本輪產出與最終 Validator 報告審的 Draft 對不上時，視為沒有最終稿（不退回去用其他 VALID 稿）。"""
    root = mkroot(tmp_path)
    out = py(root, REDO + """
rid0, cid = e4_clr()
b, evd = bug_run(); bd = bug_draft(b, evd, **adopt(cid)); assert bug_validate(b, bd, evd, "PASS")["result"] == "PASS"
run = engine.load_run(b); ok = L._final_draft(run, "BugDraft")["artifact_id"]
t2 = next(t for t in run["tasks"] if t["task_id"] == "T2"); saved = list(t2["output_artifact_ids"]); t2["output_artifact_ids"] = []
none_val = L._final_draft(run, "BugDraft")
t2["output_artifact_ids"] = saved; t1 = next(t for t in run["tasks"] if t["task_id"] == "T1"); t1["output_artifact_ids"] = []
none_gen = L._final_draft(run, "BugDraft")
print(json.dumps({"ok": ok, "bd": bd, "none_val": none_val, "none_gen": none_gen}))""")
    assert out["ok"] == out["bd"] and out["none_val"] is None and out["none_gen"] is None

def test_p5_01_manual_run_scope_after_override_reject(tmp_path):
    """P5-R2-01 manual 交界（函式層）：manual run 的 Validator FAIL ×3 → HUMAN_OVERRIDE「再給一次」會清空 T1 本輪產出，第三稿仍 VALID 而且 ID 較大；
    run 範圍必須取本輪 Draft（REQ-002），不是舊稿（REQ-001）。manual run 要到 T6 才 COMPLETED，完整 apply 在 P6 驗收。"""
    root = mkroot(tmp_path)
    from tests.test_p5_review_fixes import TWO_TARGETS
    out = py(root, TWO_TARGETS + """
from tests import helpers as H
from tools.qaos import tc_ops, ids
_q = []; _orig = ids.artifact_id
ids.artifact_id = lambda t: _q.pop(0) if (t == "TestCaseDraft" and _q) else _orig(t)
rid, cid, g = two_targets(); src = F.cref(cid, "任何站台都不能刪除")
rec = tc_ops.manual_new("手動測試：刪除子站台", "demo", "DEMO", ["進入站台列表", "刪除子站台"], "沒有刪除按鈕", "pass", F.BY, spec_id=F.SPEC, spec_version=F.VER, new_request=True)
m = engine.new_run("manual-test-to-regression", {"manual_record_id": rec}, F.BY, new_request=True)["run_id"]
def design(n, req, aid, it):
    t = F.tc(n, req, f"手動：刪除子站台被拒（{req}）", techs=["negative"], types=["negative"], mode="manual",
             drefs=[{"requirement_id": req, "question_id": "Q01", "basis_ref": F.ident(src)}], srcs=[src])
    _q[:] = [aid]
    did, pd = H.write_artifact(m, "T1", "agent-test-designer", "TestCaseDraft", {"mode": "manual", "spec_id": F.SPEC, "spec_version": F.VER, "testcases": [t]},
                               [{"entity_type": "Requirement", "id": req}], {"type": "ManualTestRecord", "ids": [rec]}, "test-design", iteration=it)
    rep = H.design_report(did, [t]); rep["mode"] = "manual"
    _, pr = H.write_artifact(m, "T1", "agent-test-designer", "TestDesignReport", rep, [{"entity_type": "Artifact", "id": did}], {"type": "TestCaseDraft", "ids": [did]}, "test-design", iteration=it)
    assert engine.submit(m, "T1", str(pd))[0] and engine.submit(m, "T1", str(pr))[0]; assert engine.evaluate_gate(m, "T1")["result"] == "PASS"
    return did
def validate(did, result, it):
    issue = {"testcase_id": "*", "issue_type": "other", "severity": "major", "violated_requirement": None, "spec_reference": None, "evidence": "x", "explanation": "x", "recommended_change": "x"}
    _, pv = H.write_artifact(m, "T2", "agent-test-validator", "TestValidationReport", H.validation_report(did, g["rmid"], result, [issue] if result == "FAIL" else None),
                             [{"entity_type": "Artifact", "id": did}], {"type": "TestCaseDraft", "ids": [did]}, "validation", iteration=it)
    assert engine.submit(m, "T2", str(pv))[0]; return engine.evaluate_gate(m, "T2")["result"]
dispatch.dispatch(m, "T1", new_request=True)
olds = []
for it in range(3):
    d = design(3 + it, "REQ-DEMO-001", f"ART-TCD-01ARZ3NDEKTSV4RRFFQ69G5FZ{it}", it); olds.append(d); assert validate(d, "FAIL", it) == "FAIL"
apr = F.waiting(m); assert store.load(f"approvals/{apr}.yaml")["type"] == "HUMAN_OVERRIDE"
F.approve(apr, decision="reject", rationale="再給一次")
new = design(9, "REQ-DEMO-002", "ART-TCD-01ARZ3NDEKTSV4RRFFQ69G5FA0", 3); assert validate(new, "PASS", 3) == "PASS"
run = engine.load_run(m)
print(json.dumps({"old_status": store.load(store.find_artifact(olds[-1]))["status"], "new": new, "final": L._final_draft(run, "TestCaseDraft")["artifact_id"],
                  "scope": sorted(L._run_scope(run)), "mine": sorted(L.target_id(x) for x in L.run_targets(clr.load(cid), m))}))""")
    assert out["old_status"] == "VALID"                                     # 前提：舊稿殘留為 VALID，而且 ID 較大
    assert out["final"] == out["new"] and out["scope"] == ["REQ-DEMO-002"]
    assert out["mine"] == ["SPEC-DEMO-001@1.0:REQ-DEMO-002#Q01"]

GATE = """
from tests import p4_flow as F
from tools.qaos import clarification as clr, store
def mk(subject="site.child.delete", level="minor", cov=None):
    try:
        c = clr.new("demo", "DEMO", F.SPEC, F.VER, "子站台能否刪除？", "agent-spec-analyst", requirement_id="REQ-DEMO-001", new_request=True, kind="spec_question",
                    question_id="Q01", topic="permission", subject=subject, role_scope=["admin"], params={}, level=level, known_rules=[], coverage=cov or F.cov())
        return {"id": c["clarification_id"], "linked": bool(c.get("_linked"))}
    except clr.ClarificationError as e: return {"error": str(e)}
def links(): return [store.load(p)["action"] for p in store.glob("runs/_audit.d/*.yaml")].count("LINK_CLARIFICATION")
"""

def test_p5_02_dedupe_hit_still_validates_input(tmp_path):
    """P5-02／P5-R2-03（第 3 章 §5、附錄 A 3-29）：決策點欄位無效時，不論有沒有同 key 的既有單都拒絕；有同 key 時不連結、不寫 LINK audit，既有 CLR 不變。
    正例：同 key、欄位合法 → 照常連結。"""
    root = mkroot(tmp_path)
    out = py(root, GATE + """
first = mk(); h0 = store.sha256_bytes((store.ROOT / store.clarification_path("demo", "DEMO", first["id"])).read_bytes()); l0 = links()
bad_hit_level = mk(level="INVALID")
bad_hit_cov = mk(cov={**F.cov(), "references_status": "bogus"})
bad_new_level = mk(subject="site.child.rename", level="INVALID")                                    # 沒有同 key：原本就由 schema 拒絕
h1 = store.sha256_bytes((store.ROOT / store.clarification_path("demo", "DEMO", first["id"])).read_bytes()); l1 = links()
same = mk(); l2 = links()
print(json.dumps({"first": first, "bad": [bad_hit_level, bad_hit_cov, bad_new_level], "h": [h0, h1], "l": [l0, l1, l2], "same": same}))""")
    assert "id" in out["first"] and not out["first"]["linked"]
    for b in out["bad"]: assert "不符 schema" in b.get("error", ""), b
    assert out["h"][0] == out["h"][1] and out["l"][0] == out["l"][1]                                   # 沒有連結、沒有 LINK audit、既有單不變
    assert out["same"] == {"id": out["first"]["id"], "linked": True} and out["l"][2] == out["l"][1] + 1

def test_p5_03_stale_tcs_keywords_follow_latest_applied_landing(tmp_path):
    """P5-03（第 6 章 §7、附錄 A 6-19）：無關鍵字結案（no_keyword_reason）後，stale-tcs 以該 landing 的空關鍵字為準，不退回舊掃描的關鍵字。
    正例：完全沒有 applied landing 時，仍取最近一次掃描的關鍵字。"""
    root = mkroot(tmp_path)
    out = py(root, HDR + """
ra = P.full_ra()                                                                         # 建立含「刪除」的 ACTIVE TC
def no_req_clr(q):
    c = clr.new("demo", "DEMO", F.SPEC, F.VER, q, "oscar", consulted=["SPEC-DEMO-001@1.0"], new_request=True)["clarification_id"]
    clr.answer(c, "維持現狀。", "pm", "no_change", "oscar", new_request=True); return c
a = no_req_clr("子站台刪除後要不要保留紀錄？")
s = L.impact(a, ["刪除"], [], "oscar", new_request=True)
ok = P.apply_(a, path="a7", no_keyword_reason="答案不改任何行為，背景文字命中不相關", tc_conclusions=[])
b = no_req_clr("子站台刪除要不要二次確認？")
L.impact(b, ["刪除"], [], "oscar", new_request=True)
print(json.dumps({"scan": [x["tc_id"] for x in s["candidates"]], "ok": ok, "a": clr.load(a)["status"], "land": clr.load(a)["landings"][-1],
                  "stale_a": L.stale_tcs(a)["tcs"], "stale_b": L.stale_tcs(b)["tcs"]}, default=str))""")
    assert out["scan"] and out["a"] == "APPLIED" and "final_keywords" not in out["land"], out
    assert out["stale_a"] == []                                                              # 不再以舊 scan 的「刪除」列出 TC
    assert {x["tc_id"] for x in out["stale_b"]} == set(out["scan"]) and all(r == "keyword:刪除" for x in out["stale_b"] for r in x["reasons"])

E6 = HDR + """
def e6_answered():
    '''G-SPEC 對沒有決策點的舊格式 critical 需求自動開單（E6）→ 回答 → 核准（不再 apply，CLR 維持 ANSWERED）。'''
    rid = F.new_run()
    F.analyze(rid, [F.req(1, ambiguity={"level": "critical", "description": "站長能否刪除子站台未定義（舊格式）"})])
    cid = F.clrs(requirement_id="REQ-DEMO-001")[0]["clarification_id"]
    clr.answer(cid, "任何站台都不能刪除。", "pm", "requirement_clarified", "oscar", new_request=True)
    F.approve(F.waiting(rid)); return rid, cid
def upgrade(cid):
    clr.metadata_upgrade(cid, "oscar", "舊格式 E6 單轉新格式：人工核對自身範圍與新決策點一致", question_id="Q01", subject="site.child.delete", role_scope=["admin"], params={}, new_request=True)
def res(cid): return {"source": F.cref(cid, "任何站台都不能刪除"), "decided_at": "2026-10-07", "adopted_side_index": 1}
"""

def test_p5_r2_04_legacy_e6_close_requires_scope(tmp_path):
    """P5-R2-04（附錄 A 6-35）：舊格式 E6 單沒有自身範圍，直接以新格式 resolution.source 引用 → G-SPEC X16 FAIL、CLR 維持 ANSWERED；
    人以 metadata upgrade 補齊自身範圍後，同一份分析 PASS → A4（INCORPORATED）→ Designer／Validator／核准 → a6 APPLIED。不放寬 X16。"""
    root = mkroot(tmp_path)
    out = py(root, E6 + """
rid, cid = e6_answered(); c0 = clr.load(cid); s0 = c0["status"]
g1 = F.analyze(rid, [P.conflict_req(1, res(cid))]); s1 = clr.load(cid)["status"]
upgrade(cid)
g2 = F.analyze(rid, [P.conflict_req(1, res(cid))]); s2 = clr.load(cid)["status"]
tcs = P.ra_p3_design(rid, cid, g2)
ok = P.apply_(cid, landed_in=[rid], targets=["SPEC-DEMO-001@1.0:REQ-DEMO-001#Q01"], keywords=["刪除"], tc_conclusions=[f"{t}=updated" for t in tcs])
print(json.dumps({"c0": [c0.get(k) for k in ("subject", "role_scope", "params", "question_id")], "s0": s0, "g1": [g1["result"], g1.get("issues")], "s1": s1,
                  "g2": g2["result"], "s2": s2, "ok": ok, "s3": clr.load(cid)["status"]}, default=str))""")
    assert out["c0"] == [None, None, None, None] and out["s0"] == "ANSWERED"                       # E6 自動單沒有自身範圍；核准不再 apply
    assert out["g1"][0] == "FAIL" and any("X16" in i and "沒有自身的答案範圍" in i for i in out["g1"][1]) and out["s1"] == "ANSWERED", out["g1"]
    assert out["g2"] == "PASS" and out["s2"] == "INCORPORATED"
    assert "error" not in out["ok"] and out["s3"] == "APPLIED", out["ok"]

def test_p5_r2_04_legacy_e6_basis_change_requires_applicability(tmp_path):
    """P5-R2-04（附錄 A 6-35）：舊答案之後目標新增 normative 引用宣告（basis 改變）→ 只補 metadata 仍 X16 FAIL；
    人以 applicability（--confirm-basis 帶入目前 basis_hash）確認舊答案仍適用後才 PASS → INCORPORATED。"""
    root = mkroot(tmp_path)
    a = py(root, E6 + """
rid, cid = e6_answered(); engine.cancel(rid, F.BY, new_request=True)
print(json.dumps({"cid": cid}))""")
    U.q(root, "spec", "reference", "add", "SPEC-DEMO-001@1.0", "--ref", "SPEC-REFB-001@1.0", "--role", "normative", "--by", "oscar", "--new-request", check=True)
    out = py(root, E6 + f"""
from tools.qaos import sources
cid = "{a['cid']}"; upgrade(cid)
rid = F.new_run(); g1 = F.analyze(rid, [P.conflict_req(1, res(cid))]); s1 = clr.load(cid)["status"]
bh = sources.basis_hash(sources.basis(F.SPEC, F.VER))
clr.applicability_add(cid, 0, "REQ-DEMO-001", "site.child.delete", ["admin"], {{}}, "SPEC-DEMO-001@1.0", "引用宣告變更後人工確認答案仍適用", "oscar", confirm_basis=bh, new_request=True)
g2 = F.analyze(rid, [P.conflict_req(1, res(cid))])
print(json.dumps({{"g1": [g1["result"], g1.get("issues")], "s1": s1, "g2": g2["result"], "s2": clr.load(cid)["status"]}}, default=str))""")
    assert out["g1"][0] == "FAIL" and any("X16" in i and "basis_hash 不同" in i for i in out["g1"][1]) and out["s1"] == "ANSWERED", out["g1"]
    assert out["g2"] == "PASS" and out["s2"] == "INCORPORATED"

def test_ac_10a_44_a6b_scope_mismatch_rejected(tmp_path):
    """AC-10A-44（審查 A 驗收缺口）：reject 決議條目的 source 指向本 CLR 最新 rev，但條目落在 subject 不同的決策點（scope 不符）→ X16 拒絕，CLR 不變。
    對照：同一個 run 的同型條目落在 CLR 自身的決策點 → APPLIED（確認拒絕確實來自 scope）。"""
    root = mkroot(tmp_path)
    out = py(root, BUG + """
rid = F.new_run()
F.analyze(rid, [F.req(1, [F.dp("Q01", "undefined", "minor", decision_needed="站長能否刪除自己站的子站台")], ambiguity=F.amb("minor", "minor")),
                F.req(2, [F.dp("Q01", "defined_in_target", "none", known=[F.sref("任何站台都不能刪除。")], subject="site.child.rename")])])
cid = F.clrs(requirement_id="REQ-DEMO-001")[0]["clarification_id"]
clr.answer(cid, "任何站台都不能刪除。", "pm", "requirement_clarified", "oscar", new_request=True)
src = F.cref(cid, "任何站台都不能刪除")
entry = lambda req: {"requirement_id": req, "question_id": "Q01", "outcome": "select_interpretation", "source": src, "rationale": "依 PM 回答，這不是 bug"}
b, evd = bug_run(); bd = bug_draft(b, evd); bug_validate(b, bd, evd, "AMBIGUITY"); apr = reject_with(b, [entry("REQ-DEMO-002"), entry("REQ-DEMO-001")])
h0 = P.clr_sha(cid)
bad = P.apply_(cid, path="a6b", landed_in=[b], targets=[f"{apr}#0"], keywords=["刪除"])
h1 = P.clr_sha(cid)
ok = P.apply_(cid, path="a6b", landed_in=[b], targets=[f"{apr}#1"], keywords=["刪除"])
print(json.dumps({"st": engine.load_run(b)["status"], "bad": bad, "h": [h0, h1], "ok": ok, "s": clr.load(cid)["status"]}, default=str))""")
    assert out["st"] == "COMPLETED"
    assert "沒有通過 X16" in out["bad"].get("error", ""), out["bad"]
    assert out["h"][0] == out["h"][1]
    assert "error" not in out["ok"] and out["s"] == "APPLIED", out["ok"]

def test_p5_02_shape_checked_before_source_validation(tmp_path):
    """P5-02 自審補充：形狀錯的輸入在來源與 pin 驗證之前就由開單關卡拒絕（ClarificationError），不會以 KeyError／TypeError 崩潰；
    functional_area 不合 CLR ID 格式時，訊息指向 area 而不是佔位 ID。"""
    root = mkroot(tmp_path)
    out = py(root, GATE + """
def human(area="DEMO", **kw):
    try: clr.new("demo", area, F.SPEC, F.VER, "子站台能否刪除？", "oscar", requirement_id="REQ-DEMO-001", new_request=True, **kw); return "accepted"
    except clr.ClarificationError as e: return "gate: " + str(e)
    except Exception as e: return f"crash: {type(e).__name__}: {e}"
pin = F.cov()["consulted"][0]
r = {"no_hash": human(coverage={**F.cov(), "consulted": [{"spec_id": pin["spec_id"], "spec_version": pin["spec_version"]}]}),
     "str_consulted": human(coverage={**F.cov(), "consulted": "x"}),
     "bad_area": human(area="demo-x", consulted=["SPEC-DEMO-001@1.0"]),
     "ok": human(consulted=["SPEC-DEMO-001@1.0"])}
print(json.dumps(r))""")
    for k in ("no_hash", "str_consulted"): assert out[k].startswith("gate: 開單關卡：輸入不符 schema"), (k, out[k])
    assert out["bad_area"].startswith("gate: 開單關卡：functional_area 必須是大寫英數"), out["bad_area"]
    assert out["ok"] == "accepted"

def test_p5_r2_04_legacy_e6_applicability_alone(tmp_path):
    """P5-R2-04 自審補充（附錄 A 6-35 (2)）：basis 改變時，不做 metadata upgrade、只以 applicability 確認也能讓 X16 成立 → INCORPORATED；
    對照：applicability 之前直接引用 → X16 FAIL。"""
    root = mkroot(tmp_path)
    a = py(root, E6 + """
rid, cid = e6_answered(); engine.cancel(rid, F.BY, new_request=True)
print(json.dumps({"cid": cid}))""")
    U.q(root, "spec", "reference", "add", "SPEC-DEMO-001@1.0", "--ref", "SPEC-REFB-001@1.0", "--role", "normative", "--by", "oscar", "--new-request", check=True)
    out = py(root, E6 + f"""
from tools.qaos import sources
cid = "{a['cid']}"
rid = F.new_run(); g1 = F.analyze(rid, [P.conflict_req(1, res(cid))])
bh = sources.basis_hash(sources.basis(F.SPEC, F.VER))
clr.applicability_add(cid, 0, "REQ-DEMO-001", "site.child.delete", ["admin"], {{}}, "SPEC-DEMO-001@1.0", "人工確認舊答案適用新決策點", "oscar", confirm_basis=bh, new_request=True)
g2 = F.analyze(rid, [P.conflict_req(1, res(cid))]); c = clr.load(cid)
print(json.dumps({{"g1": g1["result"], "g2": g2["result"], "s": c["status"], "subject": c.get("subject")}}, default=str))""")
    assert out == {"g1": "FAIL", "g2": "PASS", "s": "INCORPORATED", "subject": None}, out
