"""P5：CLR 生命週期——核准不再 apply、A4 納入、apply a6 的檢查、採用目標的確認與延後、最終關鍵字與 scan、show／stale-tcs
（需求 A 第 6 章 §3～§7；AC-10A-1～6、10、12、13、16～18、26～30、34、35、42、58～63）。

所有狀態以正式流程建立（tests/p5_flow.py）。拒絕案例依第 6 章 §12.1：先逐一斷言拒絕、CLR 檔 hash 不變，最後才執行成功例。"""
import json, pathlib, subprocess, sys
from tests import p1_util as U
from tests.test_p4_dispatch import mkroot, py
from tests.test_p1_lock_fork import popen_q, wait_file

HDR = "from tests import p5_flow as P\nfrom tools.qaos import clr_lifecycle as L\n"

def test_ra_end_to_end_and_apply_checks(tmp_path):
    """RA-P1～P3（AC-10A-1、2、3、42；AC-A-B1-1），以及在同一份狀態上的拒絕案例（AC-10A-4、5、10、18、29、41、61；附錄 A 6-17）。"""
    root = mkroot(tmp_path)
    out = py(root, HDR + """
rid, cid, apr = P.ra_p1()
s1 = clr.load(cid)["status"]; a1 = store.load(f"approvals/{apr}.yaml")
g = P.ra_p2(rid, cid); c2 = clr.load(cid)
tcs = P.ra_p3_design(rid, cid, g)
rid_c = F.new_run(); engine.cancel(rid_c, F.BY, new_request=True)                                   # 另一個 CANCELLED 的 run
scan = L.impact(cid, ["刪除"], [], "oscar", new_request=True)
T = "SPEC-DEMO-001@1.0:REQ-DEMO-001#Q01"; ok = dict(landed_in=[rid], targets=[T], keywords=["刪除"], tc_conclusions=[f"{t}=updated" for t in tcs])
h0 = P.clr_sha(cid); rej = {}
rej["missing_conclusion"] = P.apply_(cid, **{**ok, "tc_conclusions": []})
rej["cancelled_run"] = P.apply_(cid, **{**ok, "landed_in": [rid_c]})
rej["agent"] = P.apply_(cid, by="agent-supervisor", **ok)
rej["unknown_target"] = P.apply_(cid, **{**ok, "targets": [T, "SPEC-DEMO-001@1.0:REQ-DEMO-009#Q01"]})
rej["no_keyword"] = P.apply_(cid, **{**ok, "keywords": []})
rej["kw_and_reason"] = P.apply_(cid, **{**ok, "no_keyword_reason": "x"})
rej["stray"] = P.apply_(cid, **{**ok, "tc_conclusions": ok["tc_conclusions"] + ["TC-DEMO-999=updated"]})
rej["a7_on_incorporated"] = P.apply_(cid, path="a7", no_keyword_reason="x", tc_conclusions=[])
rej["a6b_defer"] = P.apply_(cid, path="a6b", landed_in=[rid], targets=["APR-0001#0"], defer_targets=[T + "=x"], keywords=["刪除"])
h1 = P.clr_sha(cid)
res = P.apply_(cid, **ok); c3 = clr.load(cid)
print(json.dumps({"s1": s1, "a1": a1["decision"], "s2": c2["status"], "land2": c2["landings"], "tcs": tcs, "scan": scan, "rej": rej, "h0": h0, "h1": h1,
                  "res": res, "c3": c3, "rid": rid}, default=str))""")
    assert out["s1"] == "ANSWERED" and out["a1"]["resolutions"][0]["outcome"] == "select_interpretation"           # AC-10A-1：核准只寫決議，沒有提前 APPLIED
    assert out["s2"] == "INCORPORATED" and out["land2"][-1]["type"] == "incorporated" and out["land2"][-1]["rm_pin"]["revision"]   # AC-10A-2
    assert {x["tc_id"] for x in out["scan"]["candidates"]} == set(out["tcs"])                                          # 先以掃描紀錄斷言候選（§12.1 第 3 點）
    rej = out["rej"]
    assert "缺少 --tc-conclusion" in rej["missing_conclusion"]["error"] and out["tcs"][0] in rej["missing_conclusion"]["error"]   # AC-10A-4
    assert "COMPLETED" in rej["cancelled_run"]["error"]                                                                          # AC-10A-5
    assert "只能由人執行" in rej["agent"]["error"]                                                                               # AC-10A-10
    assert "不在解析結果中" in rej["unknown_target"]["error"]                                                                    # AC-10A-18
    assert "沒有最終關鍵字" in rej["no_keyword"]["error"]                                                                        # AC-10A-29
    assert "互相矛盾" in rej["kw_and_reason"]["error"]
    assert "不在重新掃描的候選中" in rej["stray"]["error"]                                                                        # 附錄 A 6-17
    assert "需要 CLR 狀態為 ANSWERED" in rej["a7_on_incorporated"]["error"]                                                      # AC-10A-41
    assert "不接受 --defer-target" in rej["a6b_defer"]["error"]
    assert out["h0"] == out["h1"]                                                                                     # 所有拒絕都沒有改 CLR
    c3 = out["c3"]; l = c3["landings"][-1]
    assert c3["status"] == "APPLIED" and l["path"] == "a6" and l["landed_in"] == [out["rid"]]                           # AC-10A-3、42
    assert l["targets_confirmed"][0]["requirement_id"] == "REQ-DEMO-001" and l["targets_confirmed"][0]["via"] == "own_scope"
    assert l["scan_units"] == [{"product": "demo", "area": "DEMO"}] and l["final_keywords"] == ["刪除"] and l["rule_version"]
    assert [x["tc_id"] for x in l["candidates"]] == out["tcs"] and all(len(x["tc_version_sha256"]) == 64 for x in l["candidates"])
    assert all({"target_requirement", "clr_requirement", "keyword:刪除"} <= set(x["reasons"]) for x in l["candidates"])   # AC-10A-12：候選規則 (a)(c)(d)
    assert l["conclusions"] == [{"tc_id": t, "conclusion": "updated"} for t in out["tcs"]] and l["impact_reviewed"] and l["by"] == "oscar"
    assert c3["history"][-1]["to_status"] == "APPLIED"

def test_a5_old_run_and_stale_scan(tmp_path):
    """A5 之後：舊 run 不能作為 landed-in（AC-10A-6）；rev 0 時建立的 scan 只沿用關鍵字、目標依新 rev 重新解析（AC-10A-62）。"""
    root = mkroot(tmp_path)
    out = py(root, HDR + """
ra = P.full_ra(); cid = ra["cid"]
s0 = L.impact(cid, ["刪除"], [], "oscar", new_request=True)
clr.answer(cid, "任何站台都不能刪除；表格已更正。", "pm", "requirement_clarified", "oscar", new_request=True)      # A5：INCORPORATED → ANSWERED
s_a5 = clr.load(cid)["status"]
s_b = L.impact(cid, [], [ra["target"]], "oscar", new_request=True)                                   # rev 1 之後：TC 仍引用 rev 0 → 候選規則 (b)
rid2 = F.new_run(); g = F.analyze(rid2, [P.conflict_req(1, {"source": F.cref(cid, "任何站台都不能刪除"), "decided_at": "2026-10-07", "adopted_side_index": 1})])
s_re = clr.load(cid)["status"]
tcs = P.ra_p3_design(rid2, cid, g)
h0 = P.clr_sha(cid)
old = P.apply_(cid, landed_in=[ra["rid"]], targets=[ra["target"]], keywords=["刪除"], tc_conclusions=[f"{t}=updated" for t in tcs])
h1 = P.clr_sha(cid)
res = P.apply_(cid, landed_in=[rid2], targets=[ra["target"]], scan_id=s0["scan_id"], tc_conclusions=[f"{t}=updated" for t in tcs])
print(json.dumps({"s_a5": s_a5, "s_b": s_b, "ra_tcs": ra["tcs"], "s_re": s_re, "old": old, "h": [h0, h1], "res": res, "land": clr.load(cid)["landings"][-1]}, default=str))""")
    assert out["s_a5"] == "ANSWERED" and out["s_re"] == "INCORPORATED"
    b = {x["tc_id"]: x["reasons"] for x in out["s_b"]["candidates"]}
    assert set(out["ra_tcs"]) <= set(b) and all("stale_decision_ref:REQ-DEMO-001#Q01" in b[t] for t in out["ra_tcs"])   # AC-10A-12：候選規則 (b)
    assert "不含任何被 --target 確認的目標" in out["old"]["error"] and out["h"][0] == out["h"][1]                   # AC-10A-6
    assert out["res"]["scan_reused"] == "keywords_only"                                                            # AC-10A-62
    l = out["land"]; assert l["scan_reused"] == "keywords_only" and l["scan_answer_rev"] == 0 and l["answer_rev"] == 1 and l["final_keywords"] == ["刪除"]

def test_two_targets_confirm_and_defer(tmp_path):
    """跨需求的採用（applicability，AC-10A-13）讓答案有兩個目標：只確認一個 → 拒絕並列出遺漏（AC-10A-16）；另一個延後 → 通過，
    landing 記錄延後與理由、show 列出、延後目標的單位仍被掃描（AC-10A-17）。"""
    root = mkroot(tmp_path)
    out = py(root, HDR + """
rid, cid, apr = P.ra_p1()
bh = sources.basis_hash(sources.basis(F.SPEC, F.VER))
clr.applicability_add(cid, 0, "REQ-DEMO-002", "site.child.delete", ["admin"], {}, "SPEC-DEMO-001@1.0", "答案同樣適用 REQ-DEMO-002 的子站台刪除", "oscar", confirm_basis=bh, new_request=True)
res = {"source": F.cref(cid, "任何站台都不能刪除"), "decided_at": "2026-10-07", "adopted_side_index": 1}
g = F.analyze(rid, [P.conflict_req(1, res), P.conflict_req(2, res)])
src = F.cref(cid, "任何站台都不能刪除")
tcs = P.ra_p3_design(rid, cid, g, extra_tcs=[F.tc(2, "REQ-DEMO-002", "刪除子站台被拒（REQ-002）", techs=["negative"], types=["negative"],
                                                    drefs=[{"requirement_id": "REQ-DEMO-002", "question_id": "Q01", "basis_ref": F.ident(src)}], srcs=[src])])
T1, T2 = "SPEC-DEMO-001@1.0:REQ-DEMO-001#Q01", "SPEC-DEMO-001@1.0:REQ-DEMO-002#Q01"
targets = [l["requirement_id"] for l in L.resolve_targets(clr.load(cid))]
h0 = P.clr_sha(cid)
miss = P.apply_(cid, landed_in=[rid], targets=[T1], keywords=["刪除"], tc_conclusions=[f"{t}=updated" for t in tcs])
h1 = P.clr_sha(cid)
ok = P.apply_(cid, landed_in=[rid], targets=[T1], defer_targets=[T2 + "=REQ-002 的 TC 下週一起修"], keywords=["刪除"],
              tc_conclusions=[f"{tcs[0]}=updated", f"{tcs[1]}=deferred:等 REQ-002 一起修"])
print(json.dumps({"targets": targets, "miss": miss, "h": [h0, h1], "ok": ok, "land": clr.load(cid)["landings"][-1], "show": L.show(cid), "tcs": tcs}, default=str))""")
    assert out["targets"] == ["REQ-DEMO-001", "REQ-DEMO-002"]
    assert "沒有被 --target 確認或 --defer-target 延後" in out["miss"]["error"] and "REQ-DEMO-002" in out["miss"]["error"] and out["h"][0] == out["h"][1]
    l = out["land"]
    assert l["targets_deferred"] == [{"target": "SPEC-DEMO-001@1.0:REQ-DEMO-002#Q01", "reason": "REQ-002 的 TC 下週一起修"}]
    assert {x["tc_id"] for x in l["candidates"]} == set(out["tcs"])                                    # 延後目標的候選仍被掃描、要有結論
    follow = out["show"]["follow_ups"]
    assert {"target": "SPEC-DEMO-001@1.0:REQ-DEMO-002#Q01", "deferred_reason": "REQ-002 的 TC 下週一起修"} in follow     # AC-10A-34
    assert {"tc_id": out["tcs"][1], "conclusion": "deferred:等 REQ-002 一起修"} in follow

def test_keyword_rules_and_scan_validation(tmp_path):
    """關鍵字候選與 scan 的驗證（AC-10A-26、27、30、58～61、63）。"""
    root = mkroot(tmp_path)
    out = py(root, HDR + """
rid, cid, apr = P.ra_p1()
res = {"source": F.cref(cid, "任何站台都不能刪除"), "decided_at": "2026-10-07", "adopted_side_index": 1}
k2 = F.sref("越權操作由後端拒絕。", loc="§錯誤回應")
g = F.analyze(rid, [P.conflict_req(1, res), F.req(2, [F.dp("Q01", "defined_in_target", "none", subject="site.error", known=[k2])], statement="越權操作的回應")])
tcs = P.ra_p3_design(rid, cid, g, extra_tcs=[F.tc(2, "REQ-DEMO-002", "越權操作進行中被拒", techs=["negative"], types=["negative"],
                                                    drefs=[{"requirement_id": "REQ-DEMO-002", "question_id": "Q01", "basis_ref": F.ident(k2)}], srcs=[k2], expected="操作進行中時被後端拒絕")])
other = clr.new("demo", "DEMO", F.SPEC, F.VER, "另一張不相關的問題單", "oscar", no_source_check_reason="測試", requirement_id="REQ-DEMO-002", new_request=True)
clr.answer(other["clarification_id"], "其他答案", "pm", "requirement_clarified", "oscar", new_request=True)
s_other = L.impact(other["clarification_id"], ["x"], [], "oscar", new_request=True)
s_empty = L.impact(cid, [], [], "oscar", new_request=True); s_kw = L.impact(cid, ["進行中"], [], "oscar", new_request=True)
T = "SPEC-DEMO-001@1.0:REQ-DEMO-001#Q01"; base = dict(landed_in=[rid], targets=[T])
own = [t for t in tcs if "REQ-DEMO-001" in store.load(store.tc_version_path(t, 1))["requirement_ids"]]
kw_tc = [t for t in tcs if t not in own]
h0 = P.clr_sha(cid); r = {}
r["kw_missing"] = P.apply_(cid, **base, keywords=["進行中"], tc_conclusions=[f"{t}=updated" for t in own])                        # 26
r["scan_empty_no_reason"] = P.apply_(cid, **base, scan_id=s_empty["scan_id"], tc_conclusions=[f"{t}=updated" for t in own])       # 58
r["scan_kw_and_reason"] = P.apply_(cid, **base, scan_id=s_kw["scan_id"], no_keyword_reason="x", tc_conclusions=[f"{t}=updated" for t in tcs])   # 61
r["other_scan"] = P.apply_(cid, **base, scan_id=s_other["scan_id"], tc_conclusions=[f"{t}=updated" for t in own])                 # 63
h1 = P.clr_sha(cid)
ok = P.apply_(cid, **base, scan_id=s_kw["scan_id"], tc_conclusions=[f"{t}=updated" for t in own] + [f"{t}=not_affected" for t in kw_tc])   # 27、60
print(json.dumps({"r": r, "h": [h0, h1], "ok": ok, "land": clr.load(cid)["landings"][-1], "kw_tc": kw_tc, "s_kw": s_kw}, default=str))""")
    r = out["r"]
    assert "缺少 --tc-conclusion" in r["kw_missing"]["error"] and out["kw_tc"][0] in r["kw_missing"]["error"]
    assert "沒有最終關鍵字" in r["scan_empty_no_reason"]["error"]
    assert "互相矛盾" in r["scan_kw_and_reason"]["error"]
    assert f"屬於 " in r["other_scan"]["error"] and "第 6 章 §5.9" in r["other_scan"]["error"]
    assert out["h"][0] == out["h"][1]
    assert out["kw_tc"][0] in {x["tc_id"] for x in out["s_kw"]["candidates"]}
    l = out["land"]
    assert l["scan_reused"] == "full" and l["final_keywords"] == ["進行中"] and out["kw_tc"][0] in {x["tc_id"] for x in l["candidates"]}
    assert any("keyword:進行中" in x["reasons"] for x in l["candidates"] if x["tc_id"] == out["kw_tc"][0])

def test_no_keyword_reason_with_empty_scan(tmp_path):
    """AC-10A-30、59：空的 scan 加上 --no-keyword-reason → 通過；理由與 scan_id 記在 landing。"""
    root = mkroot(tmp_path)
    out = py(root, HDR + """
ra = P.full_ra(); cid = ra["cid"]
s = L.impact(cid, [], [], "oscar", new_request=True)
ok = P.apply_(cid, landed_in=[ra["rid"]], targets=[ra["target"]], scan_id=s["scan_id"], no_keyword_reason="PM 答案只影響單一欄位，requirement 候選已涵蓋",
              tc_conclusions=[f"{t}=updated" for t in ra["tcs"]])
print(json.dumps(clr.load(cid)["landings"][-1], default=str))""")
    assert out["no_keyword_reason"].startswith("PM 答案只影響") and out["scan_id"].startswith("SCAN-") and "final_keywords" not in out

def test_show_and_stale_tcs_readonly_while_locked(tmp_path):
    """AC-10A-35：鎖被持有時 stale-tcs 照常執行、不寫檔、開頭附「不保證完整」；show 也是唯讀。"""
    root = mkroot(tmp_path)
    cid = py(root, HDR + "ra = P.full_ra(); print(json.dumps(ra['cid']))")
    d = tmp_path / "pause"
    holder = popen_q(root, ["clarification", "index"], pause=("after_lock", d))
    try:
        wait_file(d / "paused"); before = U.snapshot(root, exclude=("locks/qaos-operation.owner", "locks/qaos-operation.lock"))
        r = U.q(root, "clarification", "stale-tcs", cid); assert r.returncode == 0, r.stderr
        st = json.loads(r.stdout); assert st["note"].startswith("不保證完整") and "不取鎖" in st["note"]
        r2 = U.q(root, "clarification", "show", cid); assert r2.returncode == 0 and json.loads(r2.stdout)["status"] == "INCORPORATED"
        assert U.diff(before, U.snapshot(root, exclude=("locks/qaos-operation.owner", "locks/qaos-operation.lock"))) == {"added": [], "removed": [], "changed": []}
    finally:
        (d / "go").write_text("1"); holder.wait(timeout=30)
