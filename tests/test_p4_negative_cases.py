"""P4 的補充反例：approval 型依據的 outcome、每個 TC 的 decision_refs、混合 revision 的 preflight、所有決議條目的檢查、
system 撤回只限文件索取單、G-SPEC 對 coverage 與派發包的各項檢查、派發後宣告改變（需求 A 第 1 章 §3.4、§3.6、§3.7；附錄 A 1-22、1-27、1-30～1-32）。
所有狀態以正式流程建立（同 test_p4_decisions.py）；只有標明「函式層」的子例直接呼叫內部函式。"""
import json
from tests import p1_util as U
from tests.test_p4_dispatch import mkroot, py
from tests.test_p4_decisions import CONFLICT_SIDES, EXAMPLE_A

E3 = ('F.req(2, [F.dp("Q01", "undefined", "critical", subject="role.assign.site_manager_to_site_manager", role=["site_manager"], '
      'coverage=F.cov(missing=[F.missing(13, "手冊 v01 的角色模型（見 7.1.1 角色說明）", "手冊 7.1.1 角色說明")]))], ambiguity=F.amb("critical", "critical"), statement="站長指派範圍")')
ITEM = '{"cited_at": {**F.pin(), "line": 13}, "name": "手冊 7.1.1 角色說明"}'

def test_waive_missing_entry_is_not_a_behaviour_decision(tmp_path):
    """approval 型 known_rules 指向 waive_missing 條目、宣稱 defined_by_decision → X12（只有 select_interpretation 能作為依據）。"""
    root = mkroot(tmp_path)
    out = py(root, f"""
rid = F.new_run(); F.analyze(rid, [{E3}]); apr = F.waiting(rid)
F.approve(apr, resolutions=[{{"requirement_id": "REQ-DEMO-002", "question_id": "Q01", "outcome": "waive_missing", "waived": [{ITEM}], "rationale": "文件短期內無法取得"}}])
r = F.req(2, [F.dp("Q01", "defined_by_decision", "none", subject="role.assign.site_manager_to_site_manager", role=["site_manager"], known=[F.aref(apr, 0, "文件短期內無法取得")])], statement="站長指派範圍")
g = F.analyze(rid, [r]); print(json.dumps([g["result"], g["issues"]]))""")
    assert out[0] == "FAIL" and any(i.startswith("X12：") and "waive_missing" in i for i in out[1]), out[1]

def test_every_tc_on_new_requirement_needs_decision_refs(tmp_path):
    """§3.6 第 1 點：requirement_based 的 TC 沒有 decision_refs 也要 FAIL（否則可繞過 E4 的 exploratory 限制）。"""
    root = mkroot(tmp_path)
    out = py(root, """
rid = F.new_run()
g = F.analyze(rid, [F.req(1, [F.dp("Q01", "undefined", "minor", topic="error_code", subject="site.delete.error_code", decision_needed="刪除失敗時的錯誤代碼")], ambiguity=F.amb("minor", "minor"))])
d = F.design(rid, [F.tc(1, "REQ-DEMO-001", "刪除失敗回傳錯誤代碼 E403", expected="回傳錯誤代碼 E403")])
print(json.dumps([g["result"], d["result"], d.get("issues")]))""")
    assert out[0] == "PASS" and out[1] == "FAIL" and any("必須以 decision_refs 標明" in i for i in out[2]), out[2]

def test_mixed_revision_keeps_legacy_clr_rule(tmp_path):
    """同一 revision 同時有舊格式 critical 需求與新資料 critical 決策點：舊需求掛的 CLR 照舊規則（核准前必須已回答），新資料走新規則；
    核准都不再 apply CLR（ADR-010，P5 起）。"""
    root = mkroot(tmp_path)
    out = py(root, f"""
rid = F.new_run()
legacy = F.req(3, ambiguity={{"level": "critical", "description": "總站台能否停用？", "options": ["能", "不能"]}}, statement="總站台停用規則")
F.analyze(rid, [legacy, {EXAMPLE_A}]); apr = F.waiting(rid); doc = store.load(f"approvals/{{apr}}.yaml")
old = [r["id"] for r in doc["impact"] if clr.load(r["id"]).get("requirement_id") == "REQ-DEMO-003"][0]
new = [r["id"] for r in doc["impact"] if clr.load(r["id"]).get("requirement_id") == "REQ-DEMO-001"][0]
res = [{{"requirement_id": "REQ-DEMO-001", "question_id": "Q01", "outcome": "select_interpretation", "source": None, "rationale": "以刪除規則為準"}}]
try: F.approve(apr, resolutions=res); first = "accepted"
except engine.EngineError as e: first = str(e)
clr.answer(old, "總站台不能停用。", "pm", "requirement_clarified", "oscar", new_request=True)
F.approve(apr, resolutions=res)
print(json.dumps([first, clr.load(old)["status"], clr.load(new)["status"]]))""")
    assert "尚未有 PM 回答" in out[0]
    assert out[1] == "ANSWERED" and out[2] == "OPEN"                       # ADR-010（P5）：核准不再 apply 任何 CLR，舊格式的 CLR 也一樣；舊規則只剩「核准前必須已回答」

def test_short_decision_needed_still_opens_clarification(tmp_path):
    root = mkroot(tmp_path)
    out = py(root, """
rid = F.new_run()
g = F.analyze(rid, [F.req(1, [F.dp("Q01", "undefined", "minor", topic="error_code", subject="site.delete.error_code", decision_needed="錯誤碼")], ambiguity=F.amb("minor", "minor"))])
c = F.clrs(requirement_id="REQ-DEMO-001")
print(json.dumps([g["result"], [(x["question"], x["decision_needed"]) for x in c]]))""")
    assert out[0] == "PASS" and len(out[1]) == 1 and out[1][0][1] == "錯誤碼" and "Q01" in out[1][0][0] and out[1][0][0].endswith("：錯誤碼")

def test_preflight_checks_every_entry(tmp_path):
    """非 critical 決策點的條目、同一決策點兩筆、source 型別、source 未回答、E1 決策點的條目都拒絕，核准單維持 PENDING。"""
    root = mkroot(tmp_path)
    out = py(root, f"""
open_ = clr.new("demo", "DEMO", F.SPEC, F.VER, "尚未回答的問題", "oscar", no_source_check_reason="測試 fixture（入口 D，未附查閱證據）", requirement_id="REQ-DEMO-001", new_request=True)
rid = F.new_run()
q1 = F.dp("Q01", "conflict", "critical", {CONFLICT_SIDES})
q2 = F.dp("Q02", "conflict", "major", subject="site.child.edit", {CONFLICT_SIDES})
q3 = F.dp("Q03", "defined_in_target", "none", subject="site.child.view", known=[F.sref("任何站台都不能刪除。")])
F.analyze(rid, [F.req(1, [q1, q2, q3], ambiguity=F.amb("critical", "critical"))]); apr = F.waiting(rid)
ok = {{"requirement_id": "REQ-DEMO-001", "question_id": "Q01", "outcome": "select_interpretation", "source": None, "rationale": "以刪除規則為準"}}
def tryit(extra):
    try: F.approve(apr, resolutions=[ok] + extra); return "accepted"
    except engine.EngineError as e: return str(e)
base = {{"requirement_id": "REQ-DEMO-001", "rationale": "r"}}
r = [tryit([{{**base, "question_id": "Q02", "outcome": "waive_missing", "waived": [{{"pin": F.pin("SPEC-REF-001")}}]}}]),
     tryit([dict(ok)]),
     tryit([{{**base, "question_id": "Q02", "outcome": "select_interpretation", "source": {{"type": "approval", "approval_id": "APR-9999", "decision_sha256": "0" * 64, "resolution_index": 0, "quote": "x"}}}}]),
     tryit([{{**base, "question_id": "Q02", "outcome": "select_interpretation", "source": {{"type": "clarification", "clarification_id": open_["clarification_id"], "answer_rev": 0, "answer_sha256": "0" * 64, "quote": "x"}}}}]),
     tryit([{{**base, "question_id": "Q03", "outcome": "select_interpretation", "source": None}}]),
     store.load(f"approvals/{{apr}}.yaml")["status"]]
print(json.dumps(r))""")
    assert "Q02 是 E2，outcome 只能是 select_interpretation" in out[0]
    assert "兩筆 resolutions 條目" in out[1]
    assert "只能是 clarification 型或 null" in out[2]
    assert "沒有答案修訂" in out[3] or "不是 ANSWERED" in out[3]
    assert "已定，不需要決議" in out[4]
    assert out[5] == "PENDING"

def test_system_withdraw_only_for_document_request():
    """函式層：狀態機的 A9（system 撤回）只限 document_request；人工撤回（A10）不受 kind 限制。"""
    from tools.qaos import state
    assert state.check("clarification", "OPEN", "WITHDRAWN", "system", {"kind": "document_request"})["by"] == ["system"]
    for obj in ({"kind": "spec_question"}, {}, {"kind": "conflict_resolution"}):
        try: state.check("clarification", "OPEN", "WITHDRAWN", "system", obj); raise AssertionError("應拒絕")
        except state.TransitionError as e: assert "kind" in str(e)
    assert state.check("clarification", "ASKED", "WITHDRAWN", "oscar", {"kind": "spec_question"})["by"] == ["human"]

# ---------------------------------------------------------------- G-SPEC 的其他檢查
def test_gspec_coverage_and_x_subconditions(tmp_path):
    root = mkroot(tmp_path)
    out = py(root, f"""
open_ = clr.new("demo", "DEMO", F.SPEC, F.VER, "尚未回答的問題", "oscar", no_source_check_reason="測試 fixture（入口 D，未附查閱證據）", requirement_id="REQ-DEMO-001", new_request=True)
rid = F.new_run(); F.analyze(rid, [{E3}]); apr = F.waiting(rid)
F.approve(apr, resolutions=[{{"requirement_id": "REQ-DEMO-002", "question_id": "Q01", "outcome": "waive_missing", "waived": [{ITEM}], "rationale": "文件短期內無法取得"}}])
dsha = sources.chash(store.load(f"approvals/{{apr}}.yaml")["decision"])
def e3(**cov):
    return F.req(2, [F.dp("Q01", "undefined", "critical", subject="role.assign.site_manager_to_site_manager", role=["site_manager"],
                          coverage=F.cov(missing=[F.missing(13, "手冊 v01 的角色模型（見 7.1.1 角色說明）", "手冊 7.1.1 角色說明")], **cov))], ambiguity=F.amb("critical", "critical"), statement="站長指派範圍")
k = F.sref("任何站台都不能刪除。")
cases = {{
  "waiver_sha": e3(waivers=[{{"approval_id": apr, "decision_sha256": "0" * 64, "resolution_index": 0, "waived": [{ITEM}]}}]),
  "status": F.req(1, [F.dp("Q01", "defined_in_target", "none", known=[k], coverage=F.cov(status="undeclared"))]),
  "cited_text": F.req(2, [F.dp("Q01", "undefined", "minor", coverage=F.cov(missing=[F.missing(12, "手冊 v01 的角色模型", "手冊 7.1.1 角色說明")]))], ambiguity=F.amb("minor", "minor")),
  "consulted": F.req(1, [F.dp("Q01", "defined_in_target", "none", known=[k], coverage=F.cov(consulted=[F.pin(), F.pin("SPEC-OTHER-001")]))]),
  "x18_star": F.req(1, [F.dp("Q01", "defined_in_target", "none", known=[k], role=["*", "admin"])]),
  "x15_open": F.req(1, [F.dp("Q01", "undefined", "minor", resolution={{"source": {{"type": "clarification", "clarification_id": open_["clarification_id"], "answer_rev": 0, "answer_sha256": "0" * 64, "quote": "x"}},
                                                                     "decided_at": "2026-10-07", "adopted_side_index": None}})], ambiguity=F.amb("none", "minor")),
}}
res = {{}}
rid2 = F.new_run()
for n, r in cases.items():
    g = F.analyze(rid if n == "waiver_sha" else rid2, [r]); res[n] = [g["result"], g["issues"]]
print(json.dumps(res))""")
    expect = {"waiver_sha": "X14：", "status": "references_status", "cited_text": "第 12 行沒有", "consulted": "不在派發包的閉包內", "x18_star": "X18：", "x15_open": "X15："}
    for n, needle in expect.items():
        r, issues = out[n]
        assert r == "FAIL" and any(needle in i for i in issues), (n, issues)

def test_gspec_packet_sha_function_level_and_declaration_change(tmp_path):
    root = mkroot(tmp_path)
    out = py(root, """
rid = F.new_run(); H.packet_sha(rid, "T1"); run = engine.load_run(rid); task = engine._task(run, "T1")
arts = {"RequirementModel": {"artifact_type": "RequirementModel", "dispatch_packet_sha256": "0" * 64, "payload": {"spec_id": F.SPEC, "spec_version": F.VER, "requirements": []}},
        "SpecAnalysis": {"artifact_type": "SpecAnalysis", "dispatch_packet_sha256": "0" * 64, "payload": {"consulted_sources": [{**F.pin(), "read_scope": "full"}]}}}
_, fl = gates.spec_context(run, task, arts)                                   # 函式層：G-SPEC 自己也核對派發包 sha（不只靠 submit）
print(json.dumps([rid, fl]))""")
    rid, fl = out
    assert any("dispatch_packet_sha256 不是本 task" in i for i in fl), fl
    U.q(root, "spec", "reference", "add", "SPEC-DEMO-001@1.0", "--ref", "SPEC-REFB-001@1.0", "--role", "normative", "--by", "oscar", check=True)   # 派發之後改宣告
    out2 = py(root, f"""g = F.analyze("{rid}", [F.req(1, [F.dp("Q01", "defined_in_target", "none", known=[F.sref("任何站台都不能刪除。")])])]); print(json.dumps([g["result"], g["issues"]]))""")
    assert out2[0] == "FAIL" and any("basis_hash 不同" in i for i in out2[1]), out2[1]

def test_unavailable_reference_without_citation_stops_the_run(tmp_path):
    """附錄 A 1-19（Oscar 2026-10-07 確認）：缺文件只由 unavailable 的必讀參考構成、又沒有正文引用處 → G-SPEC FAIL，需求不持久化、不開文件索取單；
    列出正文引用處（目標中真的有那一行）→ 正常推導為 E3、開文件索取單。"""
    root = mkroot(tmp_path)
    out = py(root, """
rid = F.new_run(); un = [{"pin": F.pin("SPEC-REF-001"), "reason": "unavailable", "note": "讀取失敗"}]
g1 = F.analyze(rid, [F.req(1, [F.dp("Q01", "undefined", "minor", coverage=F.cov(consulted=[F.pin()], unconsulted=un))], ambiguity=F.amb("minor", "minor"))])
n_rev = len((store.load("artifacts/requirements/SPEC-DEMO-001/v1.0/revisions/index.yaml") if store.exists("artifacts/requirements/SPEC-DEMO-001/v1.0/revisions/index.yaml") else {}).get("revisions") or [])
g2 = F.analyze(rid, [F.req(1, [F.dp("Q01", "undefined", "minor", coverage=F.cov(consulted=[F.pin()], unconsulted=un,
                                    missing=[F.missing(13, "手冊 v01 的角色模型（見 7.1.1 角色說明）", "權限參考文件")]))], ambiguity=F.amb("minor", "minor"))])
print(json.dumps([g1["result"], g1["issues"], n_rev, g2["result"], g2["issues"], [c["kind"] for c in F.clrs(requirement_id="REQ-DEMO-001")]]))""")
    assert out[0] == "FAIL" and any("附錄 A 1-19" in i and "不得捏造引用處" in i for i in out[1]), out[1]
    assert out[2] == 0
    assert out[3] == "PASS", out[4]
    assert out[5] == ["document_request"]
