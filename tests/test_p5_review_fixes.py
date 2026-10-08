"""P5 自審（交 Codex 前的反例審查）S5-01～07 的修正與補測。狀態都以正式流程建立；標明「竄改」的子例才在流程後修改檔案，
標明「函式層」的子例直接呼叫內部函式。"""
import json
from tests import p1_util as U
from tests.test_p4_dispatch import mkroot, py
from tests.test_p5_paths import BUG, HDR
from tests.test_p5_documents import TWO_MISSING, import_doc, doc_clr, fulfill

TWO_TARGETS = HDR + """
def two_targets():
    '''CLR 經 applicability 用到 REQ-DEMO-002；同一份 revision 中 REQ-001、REQ-002 都採用它（兩個目標）。'''
    rid, cid, apr = P.ra_p1()
    bh = sources.basis_hash(sources.basis(F.SPEC, F.VER))
    clr.applicability_add(cid, 0, "REQ-DEMO-002", "site.child.delete", ["admin"], {}, "SPEC-DEMO-001@1.0", "同一條規則", "oscar", confirm_basis=bh, new_request=True)
    res = {"source": F.cref(cid, "任何站台都不能刪除"), "decided_at": "2026-10-07", "adopted_side_index": 1}
    g = F.analyze(rid, [P.conflict_req(1, res), P.conflict_req(2, res)])
    return rid, cid, g
"""

def test_s5_01_landed_in_run_scope(tmp_path):
    """第 6 章 §5.6 第 3 點：spec-to-bug run 只以最終 BugDraft 的產出為準（綁定的 revision 含目標也不算）；manual run 只含本 run TC 的需求。"""
    root = mkroot(tmp_path)
    out = py(root, BUG + """
ra = P.full_ra(); cid = ra["cid"]
b, evd = bug_run(); bd = bug_draft(b, evd); assert bug_validate(b, bd, evd, "PASS")["result"] == "PASS"; F.approve(F.waiting(b))
h0 = P.clr_sha(cid)
r = P.apply_(cid, landed_in=[b], targets=[ra["target"]], keywords=["刪除"], tc_conclusions=[f"{t}=updated" for t in ra["tcs"]])
print(json.dumps({"st": engine.load_run(b)["status"], "r": r, "h": [h0, P.clr_sha(cid)], "s": clr.load(cid)["status"]}))""")
    assert out["st"] == "COMPLETED" and "不含任何被 --target 確認的目標" in out["r"]["error"] and out["h"][0] == out["h"][1] and out["s"] == "INCORPORATED"

def test_s5_01_manual_run_scope(tmp_path):
    root = mkroot(tmp_path)
    out = py(root, TWO_TARGETS + """
from tools.qaos import tc_ops
rid, cid, g = two_targets(); src = F.cref(cid, "任何站台都不能刪除")
P.ra_p3_design(rid, cid, g, extra_tcs=[F.tc(2, "REQ-DEMO-002", "刪除子站台被拒（REQ-002）", techs=["negative"], types=["negative"],
               drefs=[{"requirement_id": "REQ-DEMO-002", "question_id": "Q01", "basis_ref": F.ident(src)}], srcs=[src])])
rec = tc_ops.manual_new("手動測試：REQ-002 刪除子站台", "demo", "DEMO", ["進入站台列表", "刪除子站台"], "沒有刪除按鈕", "pass", F.BY, spec_id=F.SPEC, spec_version=F.VER, new_request=True)
m = engine.new_run("manual-test-to-regression", {"manual_record_id": rec}, F.BY, new_request=True)["run_id"]
dispatch.dispatch(m, "T1", new_request=True)
t = F.tc(3, "REQ-DEMO-002", "手動：刪除子站台被拒", techs=["negative"], types=["negative"], mode="manual",
         drefs=[{"requirement_id": "REQ-DEMO-002", "question_id": "Q01", "basis_ref": F.ident(src)}], srcs=[src])
did, pd = H.write_artifact(m, "T1", "agent-test-designer", "TestCaseDraft", {"mode": "manual", "spec_id": F.SPEC, "spec_version": F.VER, "testcases": [t]},
                           [{"entity_type": "Requirement", "id": "REQ-DEMO-002"}], {"type": "ManualTestRecord", "ids": [rec]}, "test-design")
rep = H.design_report(did, [t]); rep["mode"] = "manual"
_, pr = H.write_artifact(m, "T1", "agent-test-designer", "TestDesignReport", rep, [{"entity_type": "Artifact", "id": did}], {"type": "TestCaseDraft", "ids": [did]}, "test-design")
assert engine.submit(m, "T1", str(pd))[0] and engine.submit(m, "T1", str(pr))[0]; assert engine.evaluate_gate(m, "T1")["result"] == "PASS"
_, pv = H.write_artifact(m, "T2", "agent-test-validator", "TestValidationReport", H.validation_report(did, g["rmid"], "PASS"),
                         [{"entity_type": "Artifact", "id": did}], {"type": "TestCaseDraft", "ids": [did]}, "validation")
assert engine.submit(m, "T2", str(pv))[0]; assert engine.evaluate_gate(m, "T2")["result"] == "PASS"
F.approve(F.waiting(m))
all_t = sorted(L.target_id(x) for x in L._targets_in_revision(clr.load(cid), rm.run_pin(engine.load_run(m))))
mine = sorted(L.target_id(x) for x in L.run_targets(clr.load(cid), m))
print(json.dumps({"all": all_t, "mine": mine}))""")
    # 函式層：manual run 綁定的 revision 含兩個目標，但 run 的範圍（本 run TC 的需求）只有 REQ-002。
    # manual run 要走到 T6 才 COMPLETED（套件成員），完整的 apply 在 P6 的整合流程驗收。
    assert out["all"] == ["SPEC-DEMO-001@1.0:REQ-DEMO-001#Q01", "SPEC-DEMO-001@1.0:REQ-DEMO-002#Q01"]
    assert out["mine"] == ["SPEC-DEMO-001@1.0:REQ-DEMO-002#Q01"]

def test_s5_02_a9_only_when_this_approval_covers_all_items(tmp_path):
    """§6.7：先以 waive-item 豁免 D02，核准的 waive_missing 只列 D01 → 不是 A9（核准沒有涵蓋全部項目），最後判定 → APPLIED（A8）。"""
    root = mkroot(tmp_path)
    rid, cid, apr = doc_clr(root, level="critical")
    assert U.q(root, "clarification", "waive-item", cid, "--item", "D02", "--reason", "改向 PM 確認", "--by", "oscar").returncode == 0
    out = py(root, HDR + f"""
p = F.pin()
F.approve("{apr}", resolutions=[{{"requirement_id": "REQ-DEMO-001", "question_id": "Q01", "outcome": "waive_missing", "waived": [{{"cited_at": {{**p, "line": 13}}, "name": "手冊 7.1.1 角色說明"}}], "rationale": "手冊不再提供"}}])
c = clr.load("{cid}"); print(json.dumps([c["status"], [i["status"] for i in c["document_items"]], [l.get("path") for l in c.get("landings") or []],
                                        [w["source"] for i in c["document_items"] for w in i.get("waive_records") or []]]))""")
    assert out[0] == "APPLIED" and out[1] == ["waived", "waived"] and out[2] == ["a8"]
    assert out[3] == [f"approval {apr}", "waive-item"]

def test_s5_03_incorporated_answer_stays_in_human_views(tmp_path):
    """A4 之後（INCORPORATED、APPLIED）需求清單與 ACTIVATE 審批頁仍顯示 PM 回答；未結案清單含 INCORPORATED。"""
    root = mkroot(tmp_path)
    out = py(root, HDR + """
from tools.qaos import req_export, approval_render
rid, cid, apr = P.ra_p1(); g = P.ra_p2(rid, cid); src = F.cref(cid, "任何站台都不能刪除")
P.ra_p3_design(rid, cid, g, extra_tcs=[F.tc(2, "REQ-DEMO-001", "刪除子站台的錯誤訊息", techs=["negative"], types=["negative"],
               drefs=[{"requirement_id": "REQ-DEMO-001", "question_id": "Q01", "basis_ref": F.ident(src)}], srcs=[src],
               assumptions=[{"text": "錯誤訊息文字待確認", "requirement_id": "REQ-DEMO-001", "needs_human_confirmation": True}])])
ra = {"rid": rid}
act = [p.stem for p in (store.ROOT / "approvals").glob("APR-*.yaml") if store.load(p)["type"] == "ACTIVATE_TESTCASE" and store.load(p)["run_id"] == ra["rid"]][0]
print(json.dumps({"s": clr.load(cid)["status"], "req": req_export.build(F.SPEC, F.VER), "html": approval_render.render_html(act, new_request=True),
                  "open": [c["clarification_id"] for c in clr.list_()], "cid": cid}))""")
    assert out["s"] == "INCORPORATED"
    assert out["cid"] in out["req"] and out["cid"] in out["html"] and out["cid"] in out["open"]

def test_s5_04_05_gate_for_agent_and_legacy_callers(tmp_path):
    """附錄 A 3-25：legacy_e6 只給系統對沒有決策點的舊格式需求開單；agent 開單的 coverage 必須是完整的 Coverage。"""
    root = mkroot(tmp_path)
    out = py(root, HDR + """
ra = P.full_ra(); r = {}
def tryit(k, *a, **kw):
    try: r[k] = clr.new("demo", "DEMO", F.SPEC, F.VER, "新問題：" + k, *a, new_request=True, **kw)["clarification_id"]
    except clr.ClarificationError as e: r[k] = "ERR " + str(e)
tryit("bare", "agent-spec-analyst", legacy_e6=True)
tryit("new_format", "agent-spec-analyst", requirement_id="REQ-DEMO-001", legacy_e6=True)
tryit("human", "oscar", requirement_id="REQ-DEMO-001", legacy_e6=True, no_source_check_reason="x")
base = dict(requirement_id="REQ-DEMO-001", kind="spec_question", question_id="Q09", topic="permission", subject="site.child.rename", role_scope=["admin"], params={}, level="minor", known_rules=[])
tryit("cov_empty", "agent-spec-analyst", coverage={}, **base)
tryit("cov_str", "agent-spec-analyst", coverage={"references_status": "undeclared", "consulted": "x", "unconsulted_normative": [], "missing_sources": [], "waivers": []}, **base)
tryit("cov_ok", "agent-spec-analyst", coverage={"references_status": "undeclared", "consulted": [], "unconsulted_normative": [], "missing_sources": [], "waivers": []}, **base)
print(json.dumps(r))""")
    for k in ("bare", "new_format", "human"): assert out[k].startswith("ERR") and "legacy_e6" in out[k], (k, out[k])
    for k in ("cov_empty", "cov_str"): assert out[k].startswith("ERR") and "完整的 Coverage" in out[k], (k, out[k])
    assert out["cov_ok"].startswith("CLR-")

def test_s5_06_07_apply_input_checks(tmp_path):
    """同一張 TC 兩個結論、重複延後、結論格式、同時確認又延後 → 拒絕；CLR 不變。"""
    root = mkroot(tmp_path)
    out = py(root, TWO_TARGETS + """
rid, cid, g = two_targets(); src = F.cref(cid, "任何站台都不能刪除")
tcs = P.ra_p3_design(rid, cid, g, extra_tcs=[F.tc(2, "REQ-DEMO-002", "刪除子站台被拒（REQ-002）", techs=["negative"], types=["negative"],
                     drefs=[{"requirement_id": "REQ-DEMO-002", "question_id": "Q01", "basis_ref": F.ident(src)}], srcs=[src])])
T1, T2 = "SPEC-DEMO-001@1.0:REQ-DEMO-001#Q01", "SPEC-DEMO-001@1.0:REQ-DEMO-002#Q01"
ok = dict(landed_in=[rid], targets=[T1], defer_targets=[T2 + "=下週"], keywords=["刪除"], tc_conclusions=[f"{t}=updated" for t in tcs])
h0 = P.clr_sha(cid); r = {}
r["dup"] = P.apply_(cid, **{**ok, "tc_conclusions": ok["tc_conclusions"] + [f"{tcs[0]}=not_affected"]})
r["dup_defer"] = P.apply_(cid, **{**ok, "defer_targets": [T2 + "=下週", T2 + "=再下週"]})
r["bogus"] = P.apply_(cid, **{**ok, "tc_conclusions": [f"{tcs[0]}=done"]})
r["empty_reason"] = P.apply_(cid, **{**ok, "tc_conclusions": [f"{tcs[0]}=deferred: "]})
r["both"] = P.apply_(cid, **{**ok, "targets": [T1, T2]})
print(json.dumps({"r": r, "h": [h0, P.clr_sha(cid)], "tc": tcs[0]}))""")
    r = out["r"]
    assert "重複給了 --tc-conclusion" in r["dup"]["error"] and out["tc"] in r["dup"]["error"]
    assert "重複給了 --defer-target" in r["dup_defer"]["error"]
    assert "結論只能是" in r["bogus"]["error"] and "結論只能是" in r["empty_reason"]["error"]
    assert "不能同時確認又延後" in r["both"]["error"]
    assert out["h"][0] == out["h"][1]

def test_s5_07_a6b_checks(tmp_path):
    """a6b 的檢查各一個能走到該檢查的反例：落地 run 不是 spec-to-bug、CLR 另有 revision 上的目標（附錄 A 6-6）、--target 不是 reject 決議。"""
    root = mkroot(tmp_path)
    out = py(root, BUG + """
ra = P.full_ra()
b, evd = bug_run(); bd = bug_draft(b, evd); assert bug_validate(b, bd, evd, "PASS")["result"] == "PASS"; apr_b = F.waiting(b); F.approve(apr_b)
r = {}
r["not_bug"] = P.apply_(ra["cid"], path="a6b", landed_in=[ra["rid"]], targets=["APR-0001#0"], keywords=["刪除"])
r["rev_target"] = P.apply_(ra["cid"], path="a6b", landed_in=[b], targets=[f"{apr_b}#0"], keywords=["刪除"])
print(json.dumps(r))""")
    assert "必須是 spec-to-bug" in out["not_bug"]["error"]
    assert "另有 revision 上的採用目標" in out["rev_target"]["error"]

def test_s5_07_a6b_target_must_be_reject_decision(tmp_path):
    root = mkroot(tmp_path)
    out = py(root, BUG + """
rid0, cid = e4_clr()
b, evd = bug_run(); bd = bug_draft(b, evd); assert bug_validate(b, bd, evd, "PASS")["result"] == "PASS"; apr_b = F.waiting(b); F.approve(apr_b)
print(json.dumps([P.apply_(cid, path="a6b", landed_in=[b], targets=[f"{apr_b}#0"], keywords=["刪除"]), store.load(f"approvals/{apr_b}.yaml")["type"]]))""")
    assert out[1] != "RESOLVE_AMBIGUITY" and "不是決議為 reject 的 RESOLVE_AMBIGUITY" in out[0]["error"]

def test_s5_07_bugdraft_old_rev_does_not_incorporate(tmp_path):
    """BugDraft 引用 CLR 的舊 rev（G-BVAL 允許引用存在的修訂）→ 不觸發 A4（A4 只認最新 answer_rev）。"""
    root = mkroot(tmp_path)
    out = py(root, BUG + """
rid0, cid = e4_clr(); src0 = F.cref(cid, "任何站台都不能刪除")
clr.answer(cid, "任何站台都不能刪除（含總站台）。", "pm", "requirement_clarified", "oscar", new_request=True)
b, evd = bug_run()
try: bug_draft(b, evd, srcs=[src0], drefs=[{"requirement_id": "REQ-DEMO-001", "question_id": "Q01", "basis_ref": F.ident(src0)}]); g = "PASS"
except AssertionError as e: g = "FAIL " + str(e)
c = clr.load(cid); print(json.dumps([g, c["status"], [l["type"] for l in c.get("landings") or []]]))""")
    assert out[0] == "PASS", out                                    # 必須是合法舊 rev 通過 G-BVAL，而不是更早的失敗（審查 A 的驗收建議）
    assert out[1] == "ANSWERED" and out[2] == [], out

def test_s5_07_fulfill_version_and_cited_text_and_agent(tmp_path):
    """fulfill：只認 CLR 版本以後的宣告；名稱比對也看 cited_at.text（title 只出現在引用處文字）；waive-item 只能由人執行。"""
    root = mkroot(tmp_path)
    _, cid, _ = doc_clr(root)
    f = tmp_path / "old.md"; f.write_text("# 舊版站台規格\n\n## 刪除\n\n舊規則。\n", encoding="utf-8")
    U.q(root, "spec", "import", f, "--spec-id", "SPEC-DEMO-001", "--version", "0.9", "--product", "demo", "--area", "DEMO", "--by", "oscar", check=True)
    d = tmp_path / "role.md"; d.write_text("# 角色\n\n內容。\n", encoding="utf-8")
    U.q(root, "spec", "import", d, "--spec-id", "SPEC-ROLE-001", "--version", "1.0", "--product", "demo", "--area", "DOCS", "--external-filename", "後台角色與權限_spec_v02.md", "--by", "oscar", check=True)
    U.q(root, "spec", "reference", "add", "SPEC-DEMO-001@0.9", "--ref", "SPEC-ROLE-001@1.0", "--role", "informative", "--by", "oscar", check=True)
    r = fulfill(root, cid, "D02", "SPEC-ROLE-001"); assert r.returncode != 0 and "v1.0 以後" in r.stderr, r.stderr   # 只宣告在 0.9（早於 CLR 的 1.0）
    import_doc(root, tmp_path, "SPEC-MODEL-001", filename="x_v01.md", title="角色模型")                    # 只出現在 D01 的 cited_at.text
    r = fulfill(root, cid, "D01", "SPEC-MODEL-001"); assert r.returncode == 0, r.stderr
    c = U.load(root, f"clarifications/demo/DEMO/{cid}.yaml")
    m = c["document_items"][0]["fulfillments"][-1]["match"]; assert m == {"method": "name_match", "matched_text": "角色模型", "by": "oscar"}
    assert "角色模型" not in c["document_items"][0]["name"]
    out = py(root, HDR + f"""
try: L.waive_item("{cid}", "D02", "x", "agent-spec-analyst", new_request=True); print(json.dumps("ok"))
except L.LifecycleError as e: print(json.dumps(str(e)))""")
    assert "只能由人" in out

def test_s5_07_gate_source_refs(tmp_path):
    """G-SPEC：需求層 source_refs 只接受 spec 型、quote 要對得上（X10，附錄 A 3-26）；G-BVAL：BugDraft 的 CLR 來源必須對應存在的決策點、quote 要對得上。"""
    root = mkroot(tmp_path)
    out = py(root, BUG + """
rid, cid, apr = P.ra_p1(); src = F.cref(cid, "任何站台都不能刪除")
res = {"source": src, "decided_at": "2026-10-07", "adopted_side_index": 1}
def r5(refs_):
    q = F.req(5, [F.dp("Q01", "defined_in_target", "none", known=[F.sref("任何站台都不能刪除。")])]); q["source_refs"] = refs_; return q
g = F.analyze(rid, [P.conflict_req(1, res), r5([src])]); out = {"clr": [g["result"], g.get("issues") or []]}
g = F.analyze(rid, [P.conflict_req(1, res), r5([F.sref("這句話不在 spec 裡。")])]); out["bad_quote"] = [g["result"], g.get("issues") or []]
g = F.analyze(rid, [P.conflict_req(1, res), r5([F.sref("任何站台都不能刪除。")])]); out["ok"] = [g["result"], g.get("issues") or []]
k = F.sref("任何站台都不能刪除。")
P.ra_p3_design(rid, cid, g, extra_tcs=[F.tc(5, "REQ-DEMO-005", "刪除被拒（REQ-005）", techs=["negative"], types=["negative"],
               drefs=[{"requirement_id": "REQ-DEMO-005", "question_id": "Q01", "basis_ref": F.ident(k)}], srcs=[k])])
b, evd = bug_run()
try: bug_draft(b, evd, srcs=[src], drefs=[{"requirement_id": "REQ-DEMO-001", "question_id": "Q09", "basis_ref": F.ident(src)}]); out["bd_no_dp"] = "PASS"
except AssertionError as e: out["bd_no_dp"] = str(e)
engine.cancel(b, F.BY, new_request=True)
b2, evd2 = bug_run(); bad = {**src, "quote": "PM 沒說過這句"}
try: bug_draft(b2, evd2, srcs=[bad], drefs=[{"requirement_id": "REQ-DEMO-001", "question_id": "Q01", "basis_ref": F.ident(bad)}]); out["bd_quote"] = "PASS"
except AssertionError as e: out["bd_quote"] = str(e)
print(json.dumps(out))""")
    assert out["clr"][0] == "FAIL" and any("X10" in i and "只接受 spec 型" in i for i in out["clr"][1]), out["clr"]
    assert out["bad_quote"][0] == "FAIL" and any("X10" in i and "source_refs[0]" in i for i in out["bad_quote"][1]), out["bad_quote"]
    assert out["ok"][0] == "PASS", out["ok"]
    assert "不存在的決策點" in out["bd_no_dp"], out["bd_no_dp"]
    assert out["bd_quote"] != "PASS" and "quote" in out["bd_quote"], out["bd_quote"]

def test_s5_09_stale_tcs_follows_targets(tmp_path):
    """§7：stale-tcs 沿用 (a)～(d)；A5 之後 revision 還沒重新納入時，仍以採用舊 rev 的決策點為目標，找到兩個需求上依賴舊答案的 TC。"""
    root = mkroot(tmp_path)
    out = py(root, TWO_TARGETS + """
rid, cid, g = two_targets(); src = F.cref(cid, "任何站台都不能刪除")
tcs = P.ra_p3_design(rid, cid, g, extra_tcs=[F.tc(2, "REQ-DEMO-002", "刪除子站台被拒（REQ-002）", techs=["negative"], types=["negative"],
                     drefs=[{"requirement_id": "REQ-DEMO-002", "question_id": "Q01", "basis_ref": F.ident(src)}], srcs=[src])])
assert clr.load(cid)["status"] == "INCORPORATED"
clr.answer(cid, "任何站台都不能刪除（含總站台）。", "pm", "requirement_clarified", "oscar", new_request=True)
print(json.dumps({"s": L.stale_tcs(cid), "tcs": tcs}))""")
    got = {x["tc_id"]: x["reasons"] for x in out["s"]["tcs"]}
    assert set(out["tcs"]) <= set(got)
    for t, req in zip(out["tcs"], ("REQ-DEMO-001", "REQ-DEMO-002")):
        assert f"stale_decision_ref:{req}#Q01" in got[t] and "target_requirement" in got[t], (t, got[t])
    assert out["s"]["note"].startswith("不保證完整")

def test_s5_07_target_resolution_requires_x16(tmp_path):
    """目標解析只收通過 X16 的採用（竄改：revision 採用之後，從 CLR 檔移除 REQ-002 的 applicability；正式流程沒有移除 applicability 的指令）。"""
    root = mkroot(tmp_path)
    before = py(root, TWO_TARGETS + """
rid, cid, g = two_targets(); print(json.dumps([cid, [L.target_id(t) for t in L.resolve_targets(clr.load(cid))]]))""")
    cid, targets = before
    assert targets == ["SPEC-DEMO-001@1.0:REQ-DEMO-001#Q01", "SPEC-DEMO-001@1.0:REQ-DEMO-002#Q01"]
    p = root / f"clarifications/demo/DEMO/{cid}.yaml"
    import yaml
    d = yaml.safe_load(p.read_text(encoding="utf-8"))
    for rev in d["answer_revisions"]: rev.pop("applicability", None)                                # 竄改
    d.pop("applicability", None)
    p.write_text(yaml.safe_dump(d, allow_unicode=True, sort_keys=False), encoding="utf-8")
    after = py(root, HDR + f"""print(json.dumps([L.target_id(t) for t in L.resolve_targets(clr.load("{cid}"))]))""")
    assert after == ["SPEC-DEMO-001@1.0:REQ-DEMO-001#Q01"]
