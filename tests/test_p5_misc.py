"""P5：其他契約——ADR-010 與 ADR-008 的註記（AC-10A-33）、操作裝飾器對應、A10 撤回、answer 的出處與 kind 限制。"""
import json, pathlib, re
from tests import p1_util as U
from tests.test_p4_dispatch import mkroot, py

REPO = pathlib.Path(__file__).resolve().parents[1]

def test_ac_10a_33_adr_010_and_adr_008_note():
    adr10 = (REPO / "docs/decisions/ADR-010-clarification-lifecycle-manual-confirmation.md").read_text(encoding="utf-8")
    for d in ("Decision 1", "Decision 2", "Decision 3", "Decision 4", "Consequences"):
        assert d in adr10, d
    for word in ("**修改**", "**取消**", "**放寬**"):
        assert word in adr10
    assert "不驗證** `--tc-conclusion`" in adr10 and "retire_planned` 不代表已退休" in adr10 and "不保證完整" in adr10          # §13 的限制
    assert len(re.findall(r"^\d+\. ", adr10.split("## 已知限制")[1].split("## 範圍外")[0], flags=re.M)) == 10
    adr8 = (REPO / "docs/decisions/ADR-008-clarification-apply-impact-scan.md").read_text(encoding="utf-8")
    assert "(ADR-010-clarification-lifecycle-manual-confirmation.md)" in adr8 and "部分被" in adr8

EXPECTED_OPS = {
    ('approval_render.py', 'approval_render'): 'render',
    ('approval_render.py', 'approval_render_html'): 'render_html',
    ('bug_lifecycle.py', 'bug_close'): 'close',
    ('bug_lifecycle.py', 'bug_resolve'): 'resolve',
    ('bug_lifecycle.py', 'bug_verify'): 'verify',
    ('bugindex.py', 'bug_index'): 'build',
    ('clarification.py', 'applicability_add'): 'applicability_add',
    ('clarification.py', 'clarification_addenda_add'): 'addenda_add',
    ('clarification.py', 'clarification_answer'): 'answer',
    ('clarification.py', 'clarification_ask'): 'ask',
    ('clarification.py', 'clarification_index'): 'build_index',
    ('clarification.py', 'clarification_metadata_upgrade'): 'metadata_upgrade',
    ('clarification.py', 'clarification_new'): 'new',
    ('clarification.py', 'clarification_withdraw'): 'withdraw',
    ('cli.py', 'bug_transition'): 'bug_transition',
    ('cli.py', 'evidence_add'): 'evidence_add',
    ('cli.py', 'execution_import'): 'execution_import',
    ('clr_lifecycle.py', 'clarification_apply'): 'apply',
    ('clr_lifecycle.py', 'clarification_fulfill'): 'fulfill',
    ('clr_lifecycle.py', 'clarification_impact'): 'impact',
    ('clr_lifecycle.py', 'clarification_waive_item'): 'waive_item',
    ('dispatch.py', 'dispatch'): 'dispatch',
    ('engine.py', 'approve'): 'approve',
    ('engine.py', 'evaluate_gate'): 'evaluate_gate',
    ('engine.py', 'run_cancel'): 'cancel',
    ('engine.py', 'run_new'): 'new_run',
    ('engine.py', 'submit'): 'submit',
    ('final_export.py', 'tc_final'): 'export',
    ('ids.py', 'id_alloc'): 'alloc_cmd',
    ('req_export.py', 'req_export'): 'export',
    ('rm.py', 'req_accept_declaration'): 'accept_declaration',
    ('spec_ops.py', 'spec_import'): 'spec_import',
    ('spec_ops.py', 'spec_metadata_upgrade'): 'metadata_upgrade',
    ('spec_ops.py', 'spec_reference_add'): 'reference_add',
    ('spec_ops.py', 'spec_reference_declare_empty'): 'reference_declare_empty',
    ('spec_ops.py', 'spec_reference_remove'): 'reference_remove',
    ('tc_export.py', 'tc_export'): 'export',
    ('tc_ops.py', 'manual_new'): 'manual_new',
    ('tc_ops.py', 'tc_retire'): 'retire',
    ('tc_ops.py', 'tc_revise'): 'revise',
}

def test_operation_decorators_wrap_the_intended_functions():
    """每個 @operation.operation(...) 都直接裝飾預期的函式（新增函式時裝飾器被移位，會讓寫入指令失去操作包裝；P4 自審 S4-01 的回歸）。
    新增或改名操作時要同步更新 EXPECTED_OPS。"""
    found = {}
    for f in sorted((REPO / "tools/qaos").glob("*.py")):
        lines = f.read_text(encoding="utf-8").split("\n")
        for i, l in enumerate(lines):
            m = re.match(r'@operation\.operation\("([a-z_]+)"', l)
            if m:
                fn = re.match(r"def (\w+)", lines[i + 1]); found[(f.name, m.group(1))] = fn.group(1) if fn else None
    assert found == EXPECTED_OPS
    from tools.qaos import clarification as clr, clr_lifecycle as L
    for fn in (clr.new, clr.ask, clr.answer, clr.withdraw, clr.applicability_add, L.impact, L.apply, L.fulfill, L.waive_item):
        assert getattr(fn, "__wrapped_operation__", None), fn.__name__

def test_withdraw_answer_rules_and_decision_revised(tmp_path):
    """A10：撤回要理由、只能由人；撤回 INCORPORATED 的 CLR → 引用它的 revision 為 decision_revised（附錄 A 6-3）。
    A2：文件索取單不以回答結案；answer_sources 的 spec 型要核對 SpecPin。"""
    root = mkroot(tmp_path)
    out = py(root, """
from tests import p5_flow as P
from tools.qaos import clr_lifecycle as L
ra = P.full_ra(); cid = ra["cid"]
r = {}
for by, reason in (("agent-x", "x"), ("oscar", " ")):
    try: clr.withdraw(cid, by, reason, new_request=True); r[by + reason] = "accepted"
    except (clr.ClarificationError, ValueError) as e: r[by + reason] = str(e)
before = rm.outdated(F.current_rev())["decision_revised"]
clr.withdraw(cid, "oscar", "PM 撤回這個決議，改開新單", new_request=True)
after = rm.outdated(F.current_rev())
bad_src = None
q = clr.new("demo", "DEMO", F.SPEC, F.VER, "另一個需要回答的問題", "oscar", consulted=["SPEC-DEMO-001@1.0"], new_request=True)
try: clr.answer(q["clarification_id"], "a", "pm", "requirement_clarified", "oscar", answer_sources=[{"type": "spec", "spec_id": F.SPEC, "spec_version": F.VER, "content_hash": "0" * 64, "location": "§x"}], new_request=True)
except clr.ClarificationError as e: bad_src = str(e)
clr.answer(q["clarification_id"], "a", "pm", "requirement_clarified", "oscar", new_request=True,
           answer_sources=[{**F.pin(), "type": "spec", "location": "§刪除規則"}, {"type": "message", "channel": "slack", "sent_by": "pm", "at": "2026-10-07"}])
print(json.dumps({"r": r, "before": before, "after": after, "status": clr.load(cid)["status"], "bad_src": bad_src,
                  "srcs": clr.load(q["clarification_id"])["answer_revisions"][-1]["answer_sources"]}))""")
    assert "只能由人" in out["r"]["agent-xx"] or "human" in out["r"]["agent-xx"].lower()
    assert "--reason 必填" in out["r"]["oscar "]
    assert out["before"] is False and out["status"] == "WITHDRAWN"
    assert out["after"]["decision_revised"] is True and any("已撤回" in d for d in out["after"]["details"])
    assert out["bad_src"] and "answer_sources[0]" in out["bad_src"]
    assert [s["type"] for s in out["srcs"]] == ["spec", "message"]
