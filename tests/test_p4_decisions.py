"""P4 FIX-05：決策點的不合法組合 X1～X18、有效狀態與路由、G-DESIGN 逐決策點限制、RESOLVE_AMBIGUITY 的決議條目與 preflight
（需求 A 第 1 章 §3；AC-05-1～15、AC-06-1；以及延到 P4 的 AC-08 G-SPEC 部分、AC-09-12）。

範例 A～F 以測試 root 中的小型 spec（tests/p4_flow.py 的 SPEC-DEMO-001 等）重現同樣的資料形狀與推導，不是 SITELIST／DAILYREPORT 的真實資料；
真實資料的重現在 M1 預演時驗收。所有狀態都經正式流程建立（spec import／reference add、run new、dispatch、submit、gate、approve、
clarification new／answer／applicability add）；CLR 的入口 D（腳本呼叫 clarification.new）另外標示。"""
import json, pathlib
import pytest
from tests import p1_util as U
from tests.test_p4_dispatch import mkroot, py

CONFLICT_SIDES = 'sides=[F.sref("| 子站台：刪除 | 可操作 | 可操作 |", loc="§角色與權限"), F.sref("任何站台都不能刪除。")], note="表格允許刪除子站台；刪除規則禁止"'
EXAMPLE_A = f'F.req(1, [F.dp("Q01", "conflict", "critical", {CONFLICT_SIDES}, resolution=None, decision_needed="以表格或刪除規則為準")], ambiguity=F.amb("critical", "critical"))'
TWELVE = ("question_id", "topic", "subject", "params", "role_scope", "level", "known_rules", "conflict_sides", "conflict_note", "coverage", "decision_needed", "detail_gaps")

def clr_file(root, cid):
    return U.load(root, f"clarifications/demo/DEMO/{cid}.yaml")

# ---------------------------------------------------------------- AC-05-1、AC-06-1（入口 B）、範例 A；AC-05-2、範例 B；AC-09-12
def test_ac_05_1_2_conflict_critical_then_resolved_by_approval(tmp_path):
    root = mkroot(tmp_path)
    a = py(root, f"""
rid = F.new_run(); g = F.analyze(rid, [{EXAMPLE_A}]); apr = F.waiting(rid)
rev = F.revision_req("REQ-DEMO-001"); run = engine.load_run(rid)
tcs = [F.tc(1, "REQ-DEMO-001", "刪除子站台", drefs=[{{"requirement_id": "REQ-DEMO-001", "question_id": "Q01", "basis_ref": None}}])]
arts = {{"TestCaseDraft": {{"artifact_id": "ART-TCD-X", "payload": {{"mode": "spec", "spec_id": F.SPEC, "spec_version": F.VER, "testcases": tcs}}}},
        "TestDesignReport": {{"artifact_id": "ART-TDR-X", "payload": H.design_report("ART-TCD-X", tcs)}}}}
print(json.dumps({{"g": g["result"], "issues": g["issues"], "rid": rid, "apr": apr, "apr_doc": store.load(f"approvals/{{apr}}.yaml"), "rev": rev, "pin": run["requirement_model_revision"],
                  "clrs": F.clrs(requirement_id="REQ-DEMO-001"), "gd": gates.g_design(run, None, arts)}}))""")
    assert a["g"] == "PASS", a["issues"]
    dp = a["rev"]["decision_points"][0]
    assert dp["derived"] == {"state": "E2", "effective_level": "critical", "route": "R3", "resolved": False, "gap_missing": False, "gap_unverified": False}
    revdoc = U.load(root, f"artifacts/requirements/SPEC-DEMO-001/v1.0/revisions/{a['pin']['revision']}.yaml")
    e = next(t for t in U.load(root, f"runs/{a['rid']}/run.yaml")["tasks"] if t["task_id"] == "T1")["dispatch_packets"][-1]
    assert revdoc["dispatch_packet_sha256"] == e["sha256"] and set(revdoc["decision_snapshot_hashes"]) == {"resolutions", "run_decisions"}
    assert dp["basis_hash"] and a["rev"]["status"] == "DRAFT" and a["rev"]["ambiguity"]["level"] == "critical" and a["rev"]["ambiguity"]["raised_level"] == "critical"
    apr = a["apr_doc"]
    assert apr["type"] == "RESOLVE_AMBIGUITY" and apr["requirement_model_revision"] == a["pin"]
    assert len(a["clrs"]) == 1; c = a["clrs"][0]
    assert c["kind"] == "conflict_resolution" and c["approval_id"] == a["apr"] and {"entity_type": "Clarification", "id": c["clarification_id"]} in apr["impact"]
    src = {k: v for k, v in dp.items() if k not in ("basis", "resolution", "basis_hash", "derived")}
    assert {k: c.get(k) for k in TWELVE if k in src} == {k: src[k] for k in TWELVE if k in src}     # AC-06-1：入口 B 逐欄抄寫
    assert "possible_source_missing" not in c and c["status"] == "OPEN"
    assert any("REQ-DEMO-001" in i and ("非 ACTIVE" in i or "禁止" in i) for i in a["gd"]), a["gd"]   # G-DESIGN 拒絕依賴它的 TC
    cid, rid = c["clarification_id"], a["rid"]
    U.q(root, "clarification", "answer", cid, "--answer", "任何站台都不能刪除，表格的「可操作」是舊文案。", "--answered-by", "pm", "--resolution", "requirement_clarified", "--by", "oscar", check=True)
    b = py(root, f"""
apr = "{a['apr']}"
src = F.cref("{cid}", "任何站台都不能刪除")
F.approve(apr, resolutions=[{{"requirement_id": "REQ-DEMO-001", "question_id": "Q01", "outcome": "select_interpretation", "source": src, "rationale": "依 PM 回答：任何站台都不能刪除"}}])
res = {{"source": F.aref(apr, 0, "依 PM 回答"), "decided_at": "2026-10-07", "adopted_side_index": 1}}
r = F.req(1, [F.dp("Q01", "conflict", "critical", {CONFLICT_SIDES}, resolution=res)], ambiguity=F.amb("none", "critical"))
g = F.analyze("{rid}", [r]); rev = F.revision_req("REQ-DEMO-001")
side = lambda i: F.ident(rev["decision_points"][0]["conflict_sides"][i])
dref = lambda br: [{{"requirement_id": "REQ-DEMO-001", "question_id": "Q01", "basis_ref": br}}]
reqs = rm.requirements_of(engine.load_run("{rid}")["requirement_model_revision"])
null = json.loads(json.dumps(reqs)); null["REQ-DEMO-001"]["decision_points"][0]["resolution"]["adopted_side_index"] = None
f0 = gates._decision_ref_issues(F.tc(9, "REQ-DEMO-001", "x", drefs=dref(side(0))), reqs)
f_null = [gates._decision_ref_issues(F.tc(9, "REQ-DEMO-001", "x", drefs=dref(side(i))), null) for i in (0, 1)]
ok_null = gates._decision_ref_issues(F.tc(9, "REQ-DEMO-001", "x", drefs=dref(F.ident(res["source"]))), null)
d = F.design("{rid}", [F.tc(1, "REQ-DEMO-001", "刪除子站台被拒", techs=["negative"], types=["negative"], drefs=dref(F.ident(res["source"]))),
                       F.tc(2, "REQ-DEMO-001", "站台列表沒有刪除按鈕", drefs=dref(side(1)))])
print(json.dumps({{"g": g["result"], "issues": g["issues"], "rev": rev, "clr_status": clr.load("{cid}")["status"], "f0": f0, "f_null": f_null, "ok_null": ok_null, "d": d["result"], "d_issues": d.get("issues"),
                  "n_clrs": len(F.clrs(requirement_id="REQ-DEMO-001"))}}))""")
    assert b["g"] == "PASS", b["issues"]
    dp = b["rev"]["decision_points"][0]
    assert dp["derived"]["state"] == "E1" and dp["derived"]["effective_level"] == "none" and dp["derived"]["resolved_conflict"] is True
    assert b["rev"]["status"] == "ACTIVE" and (b["rev"]["ambiguity"]["level"], b["rev"]["ambiguity"]["raised_level"]) == ("none", "critical")
    assert b["clr_status"] == "INCORPORATED"                               # 核准不再 apply CLR（第 6 章 §3.4）；重新分析以 approval 包裝明確引用最新答案 → A4（P5）
    assert b["n_clrs"] == 1                                                # E1 不開單
    assert b["d"] == "PASS", b["d_issues"]                                 # 引用 resolution、被採用的 side 1 → PASS
    assert any("未被採用" in i for i in b["f0"]), b["f0"]                  # 引用 side 0 → FAIL
    assert all(f for f in b["f_null"]) and b["ok_null"] == []              # adopted_side_index: null → 兩側都不能引用，只能引用 resolution
    # AC-09-12：revision 引用的 CLR 答案變成新的 rev → decision_revised；新 run 不跳過分析；沿用舊 rev 重新分析 → G-SPEC FAIL（附錄 A 3-18）
    U.q(root, "clarification", "answer", cid, "--answer", "任何站台都不能刪除；總站台另議。", "--answered-by", "pm", "--resolution", "requirement_clarified", "--by", "oscar", check=True)
    c = py(root, f"""
o = rm.outdated(F.current_rev()); rid2 = F.new_run(); cur = engine.load_run(rid2)["current_task_id"]
r = F.req(1, [F.dp("Q01", "conflict", "critical", {CONFLICT_SIDES}, resolution={{"source": F.cref("{cid}", "任何站台都不能刪除", rev=0), "decided_at": "2026-10-07", "adopted_side_index": 1}})],
          ambiguity=F.amb("none", "critical"))
g = F.analyze(rid2, [r])
print(json.dumps([o["decision_revised"], cur, g["result"], g["issues"]]))""")
    assert c[0] is True and c[1] == "T1"
    assert c[2] == "FAIL" and any("附錄 A 3-18" in i and "rev 1" in i for i in c[3]), c[3]

# ---------------------------------------------------------------- AC-05-3、AC-06-1（入口 A）、範例 C
def test_ac_05_3_example_c_three_points(tmp_path):
    root = mkroot(tmp_path)
    out = py(root, """
rid = F.new_run(); ref = lambda q: F.sref(q, sid="SPEC-REF-001", loc="§實作要求")
cv = F.cov(consulted=[F.pin(), F.pin("SPEC-REF-001")])
q1 = F.dp("Q01", "defined_in_reference", "none", topic="rejection_response", subject="site.self.restriction.backend_enforcement", role=["admin", "site_manager"], known=[ref("須在後端每一支 API 強制執行。")], coverage=cv)
q2 = F.dp("Q02", "defined_in_reference", "none", topic="rejection_response", subject="site.self.restriction.response_semantics", role=["admin", "site_manager"], known=[ref("越權操作一律回「無權限」。")], coverage=cv)
q3 = F.dp("Q03", "undefined", "minor", topic="rejection_response", subject="site.self.restriction.error_code", role=["admin", "site_manager"], coverage=cv,
          decision_needed="實際錯誤代碼（spec 規定由後端定義）", detail_gaps=["error_code"])
g = F.analyze(rid, [F.req(1, [q1, q2, q3], ambiguity=F.amb("minor", "minor"), rc={"defined": False})])
rev = F.revision_req("REQ-DEMO-001")
dref = lambda q, br: [{"requirement_id": "REQ-DEMO-001", "question_id": q, "basis_ref": br}]
bad = F.design(rid, [F.tc(1, "REQ-DEMO-001", "越權時回傳的錯誤代碼", techs=["negative"], types=["negative"], drefs=dref("Q03", None))])
good = F.design(rid, [F.tc(2, "REQ-DEMO-001", "越權被後端拒絕", techs=["negative"], types=["negative"], drefs=dref("Q01", F.ident(q1["known_rules"][0]))),
                      F.tc(3, "REQ-DEMO-001", "錯誤代碼待確認", techs=["error_guessing"], types=["negative"], drefs=dref("Q03", None),
                           assumptions=[{"text": "錯誤代碼由後端定義，待確認", "requirement_id": "REQ-DEMO-001", "needs_human_confirmation": True}])])
print(json.dumps({"g": g["result"], "issues": g["issues"], "rev": rev, "clrs": F.clrs(requirement_id="REQ-DEMO-001"), "q3": q3, "bad": bad, "good": good["result"], "good_issues": good.get("issues")}))""")
    assert out["g"] == "PASS", out["issues"]
    st = {d["question_id"]: (d["derived"]["state"], d["derived"]["effective_level"], d["derived"]["route"]) for d in out["rev"]["decision_points"]}
    assert st == {"Q01": ("E1", "none", "R1"), "Q02": ("E1", "none", "R1"), "Q03": ("E4", "minor", "R6")}
    assert out["rev"]["status"] == "ACTIVE" and out["rev"]["rejection_contract"]["defined"] is False and out["rev"]["ambiguity"]["level"] == "minor"
    assert len(out["clrs"]) == 1; c = out["clrs"][0]
    assert c["kind"] == "spec_question" and "approval_id" not in c and "possible_source_missing" not in c
    assert {k: c.get(k) for k in TWELVE if k in out["q3"]} == {k: out["q3"][k] for k in TWELVE if k in out["q3"]}     # AC-06-1：入口 A 逐欄抄寫
    assert out["bad"]["result"] == "FAIL" and any("Q03" in i and "exploratory" in i for i in out["bad"]["issues"]), out["bad"]
    assert out["good"] == "PASS", out["good_issues"]                     # 只依賴 Q01 的 negative 不需要 exploratory

# ---------------------------------------------------------------- AC-05-4、11、12、14、15：X1～X18 各一個反例
X_CASES = {
    1: 'F.req(1, [F.dp("Q01", "defined_in_target", "major", known=[F.sref("任何站台都不能刪除。")])], ambiguity=F.amb("major", "major"))',
    2: f'F.req(1, [F.dp("Q01", "conflict", "minor", {CONFLICT_SIDES})], ambiguity=F.amb("minor", "minor"))',
    3: 'F.req(1, [F.dp("Q01", "conflict", "critical", sides=[F.sref("任何站台都不能刪除。")], note="只有一側")], ambiguity=F.amb("critical", "critical"))',
    4: 'F.req(1, [F.dp("Q01", "undefined", "none")])',
    5: 'F.req(1, [F.dp("Q01", "undefined", "minor", coverage=F.cov(consulted=[F.pin()], unconsulted=[{"pin": F.pin("SPEC-REF-001"), "reason": "out_of_scope"}]))], ambiguity=F.amb("minor", "minor"))',
    6: 'F.req(1, [F.dp("Q01", "defined_in_target", "none", known=[])])',
    7: 'F.req(1, [F.dp("Q01", "defined_in_target", "none", known=[F.sref("任何站台都不能刪除。")], resolution={"source": F.sref("任何站台都不能刪除。"), "decided_at": "2026-10-07", "adopted_side_index": None})])',
    8: 'F.req(1, [F.dp("Q01", "defined_in_target", "none", topic="rejection_response", known=[F.sref("越權操作由後端拒絕。", loc="§錯誤回應")])], rc={"defined": False})',
    9: 'F.req(1, [F.dp("Q01", "defined_in_target", "none", known=[F.sref("任何站台都不能刪除。")])], ambiguity=F.amb("minor", "minor"))',
    10: 'F.req(1, [F.dp("Q01", "defined_in_target", "none", known=[F.sref("任何站台都可以刪除。")])])',
    11: f'F.req(1, [F.dp("Q01", "conflict", "critical", {CONFLICT_SIDES}, resolution={{"source": F.cref(CID, "任何站台都不能刪除"), "decided_at": "2026-10-07", "adopted_side_index": 5}})], ambiguity=F.amb("none", "critical"))',
    "12a": 'F.req(1, [F.dp("Q01", "defined_by_decision", "none", known=[F.sref("任何站台都不能刪除。")])])',                                   # AC-05-11
    "12b": 'F.req(1, [F.dp("Q01", "defined_in_target", "none", known=[F.sref("須在後端每一支 API 強制執行。", sid="SPEC-REF-001", loc="§實作要求")])])',   # AC-05-12
    13: f'F.req(1, [F.dp("Q01", "conflict", "critical", {CONFLICT_SIDES}, resolution={{"adopted_side_index": 0}})], ambiguity=F.amb("critical", "critical"))',   # AC-05-14 前者
    14: 'F.req(1, [F.dp("Q01", "undefined", "minor", coverage=F.cov(waivers=[{"approval_id": "APR-9999", "decision_sha256": "0" * 64, "resolution_index": 0, "waived": [{"pin": F.pin("SPEC-REF-001")}]}]))], ambiguity=F.amb("minor", "minor"))',
    15: f'F.req(1, [F.dp("Q01", "conflict", "critical", {CONFLICT_SIDES}, resolution={{"source": F.sref("任何站台都不能刪除。"), "decided_at": "2026-10-07", "adopted_side_index": 1}})], ambiguity=F.amb("none", "critical"))',
    16: 'F.req(1, [F.dp("Q01", "defined_by_decision", "none", known=[F.cref(CID, "任何站台都不能刪除")], subject="site.parent.delete")])',
    17: 'F.req(1, [F.dp("Q01", "undefined", "minor", coverage=F.cov(unconsulted=[{"pin": F.pin("SPEC-OTHER-001"), "reason": "unavailable"}]))], ambiguity=F.amb("minor", "minor"))',
    18: 'F.req(1, [F.dp("Q01", "defined_in_target", "none", role=[], known=[F.sref("任何站台都不能刪除。")])])',   # AC-05-15
}

def test_ac_05_4_x_combinations_each_fail(tmp_path):
    root = mkroot(tmp_path)
    cases = ",\n".join(f"{k!r}: {v}" for k, v in X_CASES.items())
    out = py(root, f"""
c = clr.new("demo", "DEMO", F.SPEC, F.VER, "子站台能否刪除？", "oscar", no_source_check_reason="測試 fixture（入口 D，未附查閱證據）", requirement_id="REQ-DEMO-001", new_request=True,
            kind="spec_question", question_id="Q01", subject="site.child.delete", role_scope=["admin"], params={{}})   # 入口 D
clr.answer(c["clarification_id"], "任何站台都不能刪除。", "pm", "requirement_clarified", "oscar", new_request=True)
CID = c["clarification_id"]
cases = {{{cases}}}
rid = F.new_run(); res = {{}}
for k, r in cases.items():
    g = F.analyze(rid, [r]); res[str(k)] = [g.get("result"), g.get("issues") or g.get("submit")]
ok = F.analyze(rid, [F.req(1, [F.dp("Q01", "defined_by_decision", "none", known=[F.cref(CID, "任何站台都不能刪除")])])])
res["ok"] = [ok["result"], ok["issues"]]
print(json.dumps(res))""")
    for k in X_CASES:
        n = str(k).rstrip("ab")
        r, issues = out[str(k)]
        assert r == "FAIL" and any(i.startswith(f"X{n}：") for i in issues), (k, out[str(k)])
    assert out["ok"][0] == "PASS", out["ok"]                              # 同一張 CLR、範圍涵蓋 → defined_by_decision 合法（X16 正例）

def test_ac_05_14_approval_entry_without_rationale_is_x15(tmp_path):
    """AC-05-14 後者：核准條目的 rationale 只有空白（schema 允許的最短值）→ 以它為 resolution 時 X15。"""
    root = mkroot(tmp_path)
    out = py(root, f"""
rid = F.new_run(); F.analyze(rid, [{EXAMPLE_A}]); apr = F.waiting(rid)
F.approve(apr, resolutions=[{{"requirement_id": "REQ-DEMO-001", "question_id": "Q01", "outcome": "select_interpretation", "source": None, "rationale": " "}}])
r = F.req(1, [F.dp("Q01", "conflict", "critical", {CONFLICT_SIDES}, resolution={{"source": F.aref(apr, 0, " "), "decided_at": "2026-10-07", "adopted_side_index": 1}})], ambiguity=F.amb("none", "critical"))
g = F.analyze(rid, [r]); print(json.dumps([g["result"], g["issues"]]))""")
    assert out[0] == "FAIL" and any(i.startswith("X15：") and "缺 rationale" in i for i in out[1]), out[1]

# ---------------------------------------------------------------- AC-05-5、6、13、範例 E：critical 缺文件、豁免與 preflight
def test_ac_05_5_6_13_missing_document_waiver(tmp_path):
    root = mkroot(tmp_path)
    E = ('F.req(2, [F.dp("Q01", "undefined", "critical", topic="permission", subject="role.assign.site_manager_to_site_manager", role=["site_manager"], '
         'coverage=F.cov(missing=[F.missing(13, "手冊 v01 的角色模型（見 7.1.1 角色說明）", "手冊 7.1.1 角色說明")]{W}))], ambiguity=F.amb("critical", "critical"), statement="站長指派範圍")')
    a = py(root, f"""
rid = F.new_run(); g = F.analyze(rid, [{E.format(W="")}]); apr = F.waiting(rid)
print(json.dumps({{"rid": rid, "g": g["result"], "issues": g["issues"], "apr": store.load(f"approvals/{{apr}}.yaml"), "clrs": F.clrs(requirement_id="REQ-DEMO-002"), "rev": F.revision_req("REQ-DEMO-002")}}))""")
    assert a["g"] == "PASS", a["issues"]
    assert a["rev"]["decision_points"][0]["derived"]["state"] == "E3" and a["rev"]["decision_points"][0]["derived"]["route"] == "R5" and a["rev"]["status"] == "DRAFT"
    assert [c["kind"] for c in a["clrs"]] == ["document_request"]           # AC-05-5：只開文件索取單，不開 spec_question
    doc = a["clrs"][0]; assert [(i["item_id"], i["status"]) for i in doc["document_items"]] == [("D01", "open")]
    assert "等文件或豁免" in a["apr"]["summary"]
    rid, apr = a["rid"], a["apr"]["approval_id"]
    W = 'cited = {**F.pin(), "line": 13}; item = {"cited_at": cited, "name": "手冊 7.1.1 角色說明"}'
    # preflight 反例：只有名稱相同（行號不同）、缺條目、E3 用不允許的 outcome 以外的 defer
    pf = py(root, f"""
{W}
def tryit(res):
    try: F.approve("{apr}", resolutions=res); return "accepted"
    except engine.EngineError as e: return str(e)
base = {{"requirement_id": "REQ-DEMO-002", "question_id": "Q01", "rationale": "文件短期內無法取得，改向 PM 直接確認"}}
print(json.dumps([tryit([{{**base, "outcome": "waive_missing", "waived": [{{"cited_at": {{**F.pin(), "line": 12}}, "name": "手冊 7.1.1 角色說明"}}]}}]),
                  tryit([]), tryit([{{**base, "outcome": "defer"}}]), store.load("approvals/{apr}.yaml")["status"]]))""")
    assert "不完全等於" in pf[0] and "恰好有一筆" in pf[1] and "outcome 是 defer：核准時不允許" in pf[2] and pf[3] == "PENDING"     # AC-05-10 的 defer 也在此
    b = py(root, f"""
{W}
F.approve("{apr}", resolutions=[{{"requirement_id": "REQ-DEMO-002", "question_id": "Q01", "outcome": "waive_missing", "waived": [item], "rationale": "文件短期內無法取得，改向 PM 直接確認"}}])
doc = clr.load("{doc['clarification_id']}"); run = engine.load_run("{rid}"); t1 = engine._task(run, "T1")
w = {{"approval_id": "{apr}", "decision_sha256": sources.chash(store.load("approvals/{apr}.yaml")["decision"]), "resolution_index": 0, "waived": [item]}}
# AC-05-13：只有名稱相同的豁免項目、指向另一個 question_id 的條目 → X14
same_name = dict(w, waived=[{{"cited_at": {{**F.pin(), "line": 12}}, "name": "手冊 7.1.1 角色說明"}}])
x14a = F.analyze("{rid}", [{E.format(W=', waivers=[same_name]')}])
q2 = F.req(2, [F.dp("Q02", "undefined", "critical", topic="permission", subject="role.assign.site_manager_to_site_manager", role=["site_manager"],
                    coverage=F.cov(missing=[F.missing(13, "手冊 v01 的角色模型（見 7.1.1 角色說明）", "手冊 7.1.1 角色說明")], waivers=[w]))], ambiguity=F.amb("critical", "critical"), statement="站長指派範圍")
x14b = F.analyze("{rid}", [q2])
g = F.analyze("{rid}", [{E.format(W=', waivers=[w]')}]); apr2 = F.waiting("{rid}")
print(json.dumps({{"doc": doc, "t1": [t1["status"], t1["iteration"]], "x14a": x14a["issues"], "x14b": x14b["issues"], "g": g["result"], "issues": g["issues"],
                  "rev": F.revision_req("REQ-DEMO-002"), "clrs": F.clrs(requirement_id="REQ-DEMO-002"), "apr2": store.load(f"approvals/{{apr2}}.yaml") if apr2 else None}}))""")
    d = b["doc"]
    assert d["status"] == "WITHDRAWN" and d["document_items"][0]["status"] == "waived" and d["history"][-1]["by"] == "system"   # A9
    assert b["t1"] == ["READY", 1]
    assert any(i.startswith("X14：") and "不完全等於" in i for i in b["x14a"]), b["x14a"]
    assert any(i.startswith("X14：") and "不是本決策點" in i for i in b["x14b"]), b["x14b"]
    assert b["g"] == "PASS", b["issues"]
    der = b["rev"]["decision_points"][0]["derived"]
    assert (der["state"], der["effective_level"], der["route"], der["gap_missing"]) == ("E4", "critical", "R7", False)
    sq = [c for c in b["clrs"] if c["kind"] == "spec_question"]
    assert len(sq) == 1 and sq[0]["related_clarifications"] == [{"id": doc["clarification_id"], "relation": "waived_document_request"}]
    assert len([c for c in b["clrs"] if c["kind"] == "document_request"]) == 1      # 沒有再開文件索取單
    assert "等文件" not in b["apr2"]["summary"] and {"entity_type": "Clarification", "id": sq[0]["clarification_id"]} in b["apr2"]["impact"]
    # 重跑 G-SPEC（退回後同樣的分析）不重複開單
    c = py(root, f"""
F.approve("{b['apr2']['approval_id']}", decision="reject")
w = {{"approval_id": "{apr}", "decision_sha256": sources.chash(store.load("approvals/{apr}.yaml")["decision"]), "resolution_index": 0, "waived": [{{"cited_at": {{**F.pin(), "line": 13}}, "name": "手冊 7.1.1 角色說明"}}]}}
g = F.analyze("{rid}", [{E.format(W=', waivers=[w]')}])
print(json.dumps([g["result"], [(c["kind"], c["status"]) for c in F.clrs(requirement_id="REQ-DEMO-002")], store.load(f"approvals/{{F.waiting('{rid}')}}.yaml")["summary"]]))""")
    assert c[0] == "PASS" and sorted(map(tuple, c[1])) == [("document_request", "WITHDRAWN"), ("spec_question", "OPEN")] and "等文件" not in c[2]

# ---------------------------------------------------------------- AC-05-7、範例 D：沒有宣告引用 → E5；CLR 只當背景
def test_ac_05_7_example_d_unverified(tmp_path):
    root = mkroot(tmp_path, refs=())
    out = py(root, """
bg = clr.new("demo", "DEMO", F.SPEC, F.VER, "操作員越權要怎麼擋？", "oscar", no_source_check_reason="測試 fixture（入口 D，未附查閱證據）", requirement_id="REQ-DEMO-001", new_request=True,
             kind="spec_question", question_id="Q09", subject="report.venue_scope.out_of_scope_query", role_scope=["operator"], params={})   # 入口 D
clr.answer(bg["clarification_id"], "操作員越權前後端皆擋。", "pm", "requirement_clarified", "oscar", new_request=True)
k = F.cref(bg["clarification_id"], "操作員越權前後端皆擋")
rid = F.new_run()
g = F.analyze(rid, [F.req(1, [F.dp("Q01", "undefined", "minor", topic="rejection_response", subject="report.venue_scope.out_of_scope_query", role=["admin", "site_manager"],
                                    known=[k], decision_needed="管理員、站長存取範圍外場館時的系統反應")], ambiguity=F.amb("minor", "minor"), rc={"defined": False})])
bad = F.design(rid, [F.tc(1, "REQ-DEMO-001", "範圍外查詢被擋", techs=["negative"], types=["negative"], drefs=[{"requirement_id": "REQ-DEMO-001", "question_id": "Q01", "basis_ref": F.ident(k)}],
                          assumptions=[{"text": "前後端皆擋", "requirement_id": "REQ-DEMO-001", "needs_human_confirmation": True}])])
print(json.dumps({"g": g["result"], "issues": g["issues"], "rev": F.revision_req("REQ-DEMO-001"), "clrs": [c for c in F.clrs(requirement_id="REQ-DEMO-001") if c["clarification_id"] != bg["clarification_id"]], "bad": bad}))""")
    assert out["g"] == "PASS", out["issues"]
    der = out["rev"]["decision_points"][0]["derived"]
    assert (der["state"], der["effective_level"], der["route"], der["gap_unverified"]) == ("E5", "minor", "R8", True)
    assert len(out["clrs"]) == 1 and out["clrs"][0]["kind"] == "spec_question" and out["clrs"][0]["possible_source_missing"] is True
    assert out["bad"]["result"] == "FAIL" and any("只是背景" in i for i in out["bad"]["issues"]), out["bad"]

def test_ac_05_7_background_clr_as_resolution_is_x16(tmp_path):
    """範例 D 的延伸：把範圍不涵蓋（operator）的 CLR 當成 resolution → X16 FAIL，不會成為 E1。"""
    root = mkroot(tmp_path, refs=())
    out = py(root, """
bg = clr.new("demo", "DEMO", F.SPEC, F.VER, "操作員越權要怎麼擋？", "oscar", no_source_check_reason="測試 fixture（入口 D，未附查閱證據）", requirement_id="REQ-DEMO-001", new_request=True,
             kind="spec_question", question_id="Q09", subject="report.venue_scope.out_of_scope_query", role_scope=["operator"], params={})
clr.answer(bg["clarification_id"], "操作員越權前後端皆擋。", "pm", "requirement_clarified", "oscar", new_request=True)
k = F.cref(bg["clarification_id"], "操作員越權前後端皆擋"); rid = F.new_run()
g = F.analyze(rid, [F.req(1, [F.dp("Q01", "undefined", "minor", topic="rejection_response", subject="report.venue_scope.out_of_scope_query", role=["admin", "site_manager"],
                                    resolution={"source": k, "decided_at": "2026-10-07", "adopted_side_index": None})], ambiguity=F.amb("none", "minor"), rc={"defined": True})])
print(json.dumps([g["result"], g["issues"]]))""")
    assert out[0] == "FAIL" and any(i.startswith("X16：") and "範圍不涵蓋" in i for i in out[1]), out[1]

# ---------------------------------------------------------------- AC-05-8：E1 與 E2 major 並存
def test_ac_05_8_e1_and_e2_major(tmp_path):
    root = mkroot(tmp_path)
    out = py(root, f"""
rid = F.new_run(); k = F.sref("任何站台都不能刪除。")
q1 = F.dp("Q01", "defined_in_target", "none", known=[k])
q2 = F.dp("Q02", "conflict", "major", subject="site.child.edit", {CONFLICT_SIDES})
g = F.analyze(rid, [F.req(1, [q1, q2], ambiguity=F.amb("major", "major"))])
dref = lambda q, br: [{{"requirement_id": "REQ-DEMO-001", "question_id": q, "basis_ref": br}}]
bad = F.design(rid, [F.tc(1, "REQ-DEMO-001", "編輯子站台", drefs=dref("Q02", F.ident(q2["conflict_sides"][0])))])
good = F.design(rid, [F.tc(2, "REQ-DEMO-001", "刪除子站台被拒", techs=["negative"], types=["negative"], drefs=dref("Q01", F.ident(k)))])
print(json.dumps({{"g": g["result"], "issues": g["issues"], "rev": F.revision_req("REQ-DEMO-001"), "clrs": F.clrs(requirement_id="REQ-DEMO-001"), "bad": bad, "good": good}}))""")
    assert out["g"] == "PASS", out["issues"]
    assert out["rev"]["status"] == "ACTIVE" and [c["kind"] for c in out["clrs"]] == ["conflict_resolution"]
    assert out["bad"]["result"] == "FAIL" and any("衝突未決" in i for i in out["bad"]["issues"])
    assert out["good"]["result"] == "PASS", out["good"]

# ---------------------------------------------------------------- AC-05-9、範例 F：applicability 讓別題的答案成為已裁決衝突的依據
def test_ac_05_9_example_f_applicability(tmp_path):
    root = mkroot(tmp_path)
    a = py(root, """
c = clr.new("demo", "DEMO", F.SPEC, F.VER, "現金淨收的語意？", "oscar", no_source_check_reason="測試 fixture（入口 D，未附查閱證據）", requirement_id="REQ-DEMO-002", new_request=True,
            kind="spec_question", question_id="Q01", subject="report.cash_net.semantics", role_scope=["*"], params={})   # 入口 D（屬於另一條需求）
clr.answer(c["clarification_id"], "現金淨收不是當日實際現金增減。", "pm", "requirement_clarified", "oscar", new_request=True)
print(json.dumps([c["clarification_id"], sources.basis_hash(sources.basis(F.SPEC, F.VER))]))""")
    cid, bh = a
    R = (f'F.req(1, [F.dp("Q01", "conflict", "major", subject="report.cash_net.semantics", role=["*"], {CONFLICT_SIDES}, '
         f'resolution={{"source": F.cref("{cid}", "不是當日實際現金增減"), "decided_at": "2026-09-22", "adopted_side_index": 0}})], ambiguity=F.amb("none", "major"))')
    b = py(root, f"""rid = F.new_run(); g = F.analyze(rid, [{R}]); print(json.dumps([rid, g["result"], g["issues"]]))""")
    rid = b[0]
    assert b[1] == "FAIL" and any(i.startswith("X16：") for i in b[2]), b[2]            # 沒有 applicability → X16
    U.q(root, "clarification", "applicability", "add", cid, "--answer-rev", "0", "--requirement", "REQ-DEMO-001", "--subject", "report.cash_net.semantics",
        "--role-scope", "*", "--params", "{}", "--target", "SPEC-DEMO-001@1.0", "--rationale", "答案直接定義現金淨收語意，適用 REQ-DEMO-001", "--confirm-basis", bh, "--by", "oscar", check=True)
    c = py(root, f"""
g = F.analyze("{rid}", [{R}]); rev = F.revision_req("REQ-DEMO-001")
side = lambda i: F.ident(rev["decision_points"][0]["conflict_sides"][i])
dref = lambda br: [{{"requirement_id": "REQ-DEMO-001", "question_id": "Q01", "basis_ref": br}}]
bad = F.design("{rid}", [F.tc(1, "REQ-DEMO-001", "現金淨收等於當日現金增減", drefs=dref(side(1)))])
good = F.design("{rid}", [F.tc(2, "REQ-DEMO-001", "現金淨收跨日兌現", techs=["negative"], types=["negative"], drefs=dref(side(0)))])
print(json.dumps({{"g": g["result"], "issues": g["issues"], "rev": rev, "bad": bad, "good": good}}))""")
    assert c["g"] == "PASS", c["issues"]
    assert c["rev"]["decision_points"][0]["derived"]["state"] == "E1" and (c["rev"]["ambiguity"]["level"], c["rev"]["ambiguity"]["raised_level"]) == ("none", "major")
    assert c["bad"]["result"] == "FAIL" and any("未被採用" in i for i in c["bad"]["issues"])
    assert c["good"]["result"] == "PASS", c["good"]

# ---------------------------------------------------------------- legacy（E6）不受影響；推導欄位不能由 agent 填寫（附錄 A 1-11）
def test_legacy_requirement_and_derived_fields(tmp_path):
    root = mkroot(tmp_path)
    out = py(root, """
rid = F.new_run()
legacy = F.req(1, ambiguity={"level": "major", "description": "舊格式"})       # 沒有 decision_points：E6，現行行為
d = F.dp("Q01", "defined_in_target", "none", known=[F.sref("任何站台都不能刪除。")]); d["basis_hash"] = "0" * 64
sub = F.analyze(rid, [F.req(2, [d])])
g = F.analyze(rid, [legacy])
print(json.dumps([sub.get("submit"), g["result"], g["issues"], F.revision_req("REQ-DEMO-001")]))""")
    assert out[0] and any("推導的欄位" in p for p in out[0]), out[0]
    assert out[1] == "PASS" and out[3]["status"] == "ACTIVE" and "decision_points" not in out[3]

# ---------------------------------------------------------------- §3.5.2：64 個合法抽象組合各恰一條路由（函式層）
def test_64_legal_combinations_route_table():
    """抽象維度 basis×level×resolved×gap_missing×gap_unverified＝160；排除 X1、X2、X4、X7 後剩 64 個，各對應一條路由，統計和規格相同。
    函式層：以記憶體中的決策點呼叫 decisions.derive_dp（resolved 以有 source 的 resolution 表示；gap_missing 以未豁免的缺檔表示）。"""
    import itertools
    from tools.qaos import decisions
    pin = {"spec_id": "SPEC-DEMO-001", "spec_version": "1.0", "content_hash": "a" * 64}
    routes = {}
    for basis, level, resolved, gm, gu in itertools.product(("defined_in_target", "defined_in_reference", "defined_by_decision", "undefined", "conflict"),
                                                             decisions.LEVELS, (True, False), (True, False), (True, False)):
        defined = basis in decisions.DEFINED
        if (defined and level in ("major", "critical")) or (basis == "conflict" and level in ("none", "minor")) or (basis == "undefined" and level == "none") or (defined and resolved):
            continue                                                        # X1、X2、X4、X7
        ctx = decisions.Ctx(pin, "b" * 64, "undeclared" if gu else "declared", [])
        cov = {"references_status": ctx.references_status, "consulted": [pin], "unconsulted_normative": [], "waivers": [],
               "missing_sources": [{"cited_at": {**pin, "line": 1, "text": "x"}, "name": "缺檔"}] if gm else []}
        dp = {"question_id": "Q01", "basis": basis, "level": level, "coverage": cov, "resolution": {"source": {"type": "clarification"}, "adopted_side_index": None} if resolved else None}
        d = decisions.derive_dp({"requirement_id": "REQ-DEMO-001"}, dp, ctx)
        routes[(basis, level, resolved, gm, gu)] = d["route"]
    assert len(routes) == 64
    from collections import Counter
    assert Counter(routes.values()) == {"R1": 44, "R2": 4, "R3": 4, "R4": 4, "R5": 2, "R6": 2, "R7": 1, "R8": 2, "R9": 1}
    assert routes[("undefined", "critical", False, True, False)] == "R5" and routes[("undefined", "critical", True, True, True)] == "R1"
    assert routes[("undefined", "critical", False, False, False)] == "R7" and routes[("undefined", "critical", False, False, True)] == "R9"
