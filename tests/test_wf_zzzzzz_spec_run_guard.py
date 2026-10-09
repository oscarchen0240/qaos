"""同一 spec 同時只能有一個 run 在分析需求（review-handoff/spec-run-guard/impl-prompt.md；Oscar 2026-10-09 決定方案 B＋派發檢查）。

兩個 run 的分析都還沒落地時，後落地的一方會把先落地者的 REQ ID 當成「沿用」而通過 G-SPEC（同一 ID 對應兩種語意）。
- run new：新 run 會執行需求分析（依 _skip_decision）時，同一 spec_id（不分版本）不得有分析還沒落地（分析 task 不在終止狀態）的進行中 run。
- dispatch：派發分析 task 時，同一 spec 不得有另一個 run 的分析已派發、還沒落地（已落地的 run 被退回重開分析的情況）。
- 已落地、在等人工的 run 不擋（需求 A AC-09-2、09-3）；分析被略過的 run 不擋，也不被擋；不提供強制放行。
每個案例使用獨立的暫存 root，以正式流程（spec import、run new、submit、gate、approve、dispatch、tc revise）建立狀態。"""
import json, textwrap
from tests import p1_util as U

def py(root, body: str):
    code = ("import json\nfrom tests import p3_flow as F\nfrom tests import helpers as H\n"
            "from tools.qaos import engine, store, dispatch, tc_ops\nfrom tools.qaos.cli import evidence_add\n"
            "def tryit(fn):\n    try: return ['ok', fn()]\n    except (engine.EngineError, dispatch.DispatchError) as e: return ['refused', str(e)]\n"
            "def cia(): return engine.new_run('spec-change-impact', {'spec_id': F.SPEC, 'from_version': '1.0', 'to_version': '1.1'}, F.BY, new_request=True)['run_id']\n"
            "def bug():\n    evd = evidence_add('api_response', 'oscar', inline='{\"x\": 1}', owner='demo', description='d', new_request=True)\n"
            "    return engine.new_run('spec-to-bug', {'spec_id': F.SPEC, 'spec_version': F.VER, 'evidence_ids': [evd]}, F.BY, new_request=True)['run_id']\n"
            + textwrap.dedent(body))
    return json.loads(U.py(root, code).stdout.strip().splitlines()[-1])

def root_with_auth(*versions):
    root = U.mkroot(); U.import_auth_spec(root)
    for v in versions: U.import_auth_spec(root, v)
    return root

def test_unlanded_analysis_blocks_new_analysing_run_until_cancelled():
    root = root_with_auth()
    out = py(root, """
rid1 = F.new_run()                                                             # T1 READY：分析還沒落地
r2 = tryit(F.new_run)
r_bad_ver = tryit(lambda: engine.new_run('spec-to-testcase', {'spec_id': F.SPEC, 'spec_version': '9.9'}, F.BY, new_request=True))
engine.cancel(rid1, F.BY, new_request=True)
r3 = tryit(F.new_run)
print(json.dumps([rid1, r2, r_bad_ver, r3]))""")
    rid1, r2, r_bad_ver, r3 = out
    assert r2[0] == "refused" and rid1 in r2[1] and "spec-to-testcase" in r2[1] and "T1 READY" in r2[1] and "bin/qaos run cancel" in r2[1]
    assert r_bad_ver[0] == "refused" and "9.9" in r_bad_ver[1]                      # 輸入錯誤先於防護回報
    assert r3[0] == "ok"                                                            # CANCELLED 是終止狀態，不再占用

def test_landed_waiting_run_does_not_block_and_completed_run_frees():
    """AC-09-2：舊 run 已落地 R001、在等 RESOLVE_AMBIGUITY 時，新 run 可以重新分析；新 run 落地後再開第三個也可以。"""
    root = root_with_auth()
    out = py(root, """
rid1 = F.new_run(); F.analyze(rid1, crit=True)                                 # R001 落地（REQ-AUTH-002 DRAFT），run WAITING_HUMAN
st1 = engine.load_run(rid1)["status"]
r2 = tryit(F.new_run)
F.analyze(r2[1])                                                               # R002 落地
r3 = tryit(F.new_run)                                                          # R002 全部 ACTIVE → 分析被略過
print(json.dumps([st1, r2[0], r3[0], engine.load_run(r3[1])["current_task_id"]]))""")
    assert out == ["WAITING_HUMAN", "ok", "ok", "T2"]

def test_cross_workflow_and_cross_version_block_both_ways():
    root = root_with_auth("1.1")
    out = py(root, """
c1 = cia()                                                                     # CIA 1.0→1.1：1.1 沒有 RM → T0 分析
t0 = engine.load_run(c1)["tasks"][0]
a = tryit(F.new_run)                                                           # 同 spec 的 1.0：沒有 RM → 會分析 → 擋（不分版本）
engine.cancel(c1, F.BY, new_request=True)
s1 = F.new_run()                                                               # spec-to-testcase 1.0 分析中
b = tryit(cia)                                                                 # 反向也擋
print(json.dumps([t0["task_id"], t0["status"], a, b, s1]))""")
    tid, tst, a, b, s1 = out
    assert (tid, tst) == ("T0", "READY")
    assert a[0] == "refused" and "spec-change-impact" in a[1] and "T0 READY" in a[1]
    assert b[0] == "refused" and s1 in b[1]

def test_skipped_analysis_neither_blocks_nor_is_blocked():
    """spec-to-bug、spec-to-testcase 的分析被略過時不受影響；testcase-revision 沒有分析 task；它們進行中也不擋之後的分析 run。"""
    root = root_with_auth("1.1")
    out = py(root, """
F.full()                                                                       # 1.0 R001 全部 ACTIVE，TC-AUTH-001 ACTIVE
c1 = cia()                                                                     # 1.1 分析中（還沒落地）
b1 = tryit(bug)                                                                # 1.0 的 T0 被略過
s1 = tryit(F.new_run)                                                          # 1.0 的 T1 被略過
rv = tryit(lambda: tc_ops.revise('TC-AUTH-001', '補充步驟', F.BY, new_request=True)['run_id'])
skipped = [engine.load_run(b1[1])["tasks"][0]["status"], engine.load_run(s1[1])["current_task_id"]]
engine.cancel(c1, F.BY, new_request=True)
c2 = tryit(cia)                                                                # 進行中的 run 都沒有在分析 → 可以開
print(json.dumps([b1[0], s1[0], rv[0], skipped, c2[0]]))""")
    assert out == ["ok", "ok", "ok", ["DONE", "T2"], "ok"]

def test_other_spec_in_same_area_is_independent(tmp_path):
    root = root_with_auth()
    f = tmp_path / "auth2.md"; f.write_text((U.FIXTURES / "SPEC-AUTH-001-v1.0.md").read_text(encoding="utf-8"), encoding="utf-8")
    U.q(root, "spec", "import", f, "--spec-id", "SPEC-AUTH-002", "--version", "1.0", "--product", "demo", "--area", "AUTH", "--by", "t", check=True)
    out = py(root, """
F.new_run()
r = tryit(lambda: engine.new_run('spec-to-testcase', {'spec_id': 'SPEC-AUTH-002', 'spec_version': '1.0'}, F.BY, new_request=True)['run_id'])
print(json.dumps(r[0]))""")
    assert out == "ok"

def test_reopened_analysis_waits_for_the_other_dispatched_analysis():
    """已落地的 rid1 在等人工時開了 rid2 並派發；rid1 的核准退回重開 T1 後，派發要等 rid2 落地（先派發的先落地，不互相卡死）。"""
    root = root_with_auth()
    out = py(root, """
rid1 = F.new_run(); F.analyze(rid1, crit=True); apr = engine.load_run(rid1)["waiting_on_approval_id"]
rid2 = F.new_run(); dispatch.dispatch(rid2, "T1", by=F.BY, new_request=True)  # rid2 的分析已派發、還沒落地
engine.approve(apr, "reject", F.BY, rationale="重新分析", new_request=True)    # rid1 的 T1 重開（新 iteration）
t1 = engine.load_run(rid1)["tasks"][0]
d1 = tryit(lambda: dispatch.dispatch(rid1, "T1", by=F.BY, new_request=True)["path"])
F.analyze(rid2)                                                                # rid2 落地
d2 = tryit(lambda: dispatch.dispatch(rid1, "T1", by=F.BY, new_request=True)["path"])
print(json.dumps([t1["status"], t1["iteration"], rid2, d1, d2[0]]))""")
    st, it, rid2, d1, d2 = out
    assert st == "READY" and it == 1
    assert d1[0] == "refused" and rid2 in d1[1] and "分析還沒落地" in d1[1]
    assert d2 == "ok"

def test_function_level_unlanded_rules():
    """函式層：分析 task 依 agent 與 gate 認定，不寫死 task_id。"""
    from tools.qaos import engine
    assert engine.analysis_task({"tasks": [{"task_id": "T0", "agent_id": "agent-spec-analyst", "gate": "G-SPEC"}]})["task_id"] == "T0"
    assert engine.analysis_task({"tasks": [{"task_id": "T1", "agent_id": "agent-bug-analyst", "gate": "G-BVAL"}]}) is None
    assert engine._is_analysis("agent-spec-analyst", "G-SPEC") and not engine._is_analysis("agent-spec-analyst", "G-DESIGN")
