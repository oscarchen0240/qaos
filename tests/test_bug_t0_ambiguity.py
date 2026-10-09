"""spec-to-bug：T0（Spec Analyst、G-SPEC）帶 critical ambiguity 的 RESOLVE_AMBIGUITY 後續（需求 A 第 6 章 §3.4）。
T0 階段 bug.yaml 尚不存在（Bug Analyst 的 T1 還沒跑），核准後不得碰 bug entity；approve 重開 T0（iteration+1），之後照常走 T1 → T2 → OPEN_BUG。
Bug Validator 判定的 ambiguity（T2）維持原行為：approve 退回 T1、reject → bug REJECTED、run COMPLETED。"""
import json
from tests.test_p4_dispatch import mkroot, py
from tests.test_p5_paths import BUG

T0 = BUG + """
from tests import p5_flow as P2
def t0_ambiguity():
    '''spec-to-bug run 的 T0 回報 critical conflict → RESOLVE_AMBIGUITY；回傳 (rid, evd, apr, cid)。'''
    rid, evd = bug_run()
    g = F.analyze(rid, [P2.conflict_req(1)], task="T0"); assert g["result"] == "PASS", g
    apr = F.waiting(rid); cid = F.clrs(requirement_id="REQ-DEMO-001")[0]["clarification_id"]
    clr.answer(cid, "任何站台都不能刪除，表格的「可操作」是舊文案。", "pm", "requirement_clarified", "oscar", new_request=True)
    return rid, evd, apr, cid
def entries(cid):
    return [{"requirement_id": "REQ-DEMO-001", "question_id": "Q01", "outcome": "select_interpretation", "source": F.cref(cid, "任何站台都不能刪除"),
             "rationale": "依 PM 回答：任何站台都不能刪除"}]
def tasks(rid):
    return {t["task_id"]: {"status": t["status"], "iteration": t["iteration"]} for t in engine.load_run(rid)["tasks"]}
"""

def test_t0_ambiguity_approve_reopens_t0_and_completes(tmp_path):
    """approve：不碰 bug entity、T0 以 iteration+1 重開；T0 帶 resolution 重提 → T1 → T2 PASS → OPEN_BUG approve → run COMPLETED、bug OPEN。"""
    root = mkroot(tmp_path)
    out = py(root, T0 + """
rid, evd, apr, cid = t0_ambiguity()
before = tasks(rid)
F.approve(apr, resolutions=entries(cid))
run = engine.load_run(rid); after = tasks(rid); bug_exists = store.exists(f"runs/{rid}/entities/bug.yaml")
g = F.analyze(rid, [P2.conflict_req(1, {"source": F.cref(cid, "任何站台都不能刪除"), "decided_at": "2026-10-07", "adopted_side_index": 1})], task="T0")
t_after_spec = tasks(rid)
bd = bug_draft(rid, evd); v = bug_validate(rid, bd, evd, "PASS")
F.approve(F.waiting(rid))
fin = engine.load_run(rid); b = store.load(f"runs/{rid}/entities/bug.yaml")
print(json.dumps({"before": before, "after": after, "status": run["status"], "cur": run["current_task_id"], "bug_exists": bug_exists, "g": g["result"],
                  "t_after_spec": t_after_spec, "v": v["result"], "fin": fin["status"], "bug": b["status"], "apr": store.load(f"approvals/{apr}.yaml")["status"]}))""")
    assert out["before"]["T0"] == {"status": "DONE", "iteration": 0}
    assert out["apr"] == "DECIDED" and out["status"] == "RUNNING" and out["cur"] == "T0"
    assert out["after"]["T0"] == {"status": "READY", "iteration": 1} and out["after"]["T1"]["status"] == "PENDING"
    assert out["bug_exists"] is False
    assert out["g"] == "PASS" and out["t_after_spec"]["T0"]["status"] == "DONE" and out["t_after_spec"]["T1"]["status"] == "READY"
    assert out["v"] == "PASS" and out["fin"] == "COMPLETED" and out["bug"] == "OPEN"

def test_t0_ambiguity_override_reopens_t0(tmp_path):
    """override 與 approve 相同：重開 T0，不碰 bug entity。"""
    root = mkroot(tmp_path)
    out = py(root, T0 + """
rid, evd, apr, cid = t0_ambiguity()
engine.approve(apr, "override", F.BY, rationale="直接採 PM 回答", resolutions=entries(cid), new_request=True)
print(json.dumps({"t": tasks(rid), "status": engine.load_run(rid)["status"], "bug_exists": store.exists(f"runs/{rid}/entities/bug.yaml")}))""")
    assert out["status"] == "RUNNING" and out["t"]["T0"] == {"status": "READY", "iteration": 1} and out["bug_exists"] is False

def test_t0_ambiguity_reject_reopens_t0(tmp_path):
    """reject（退回 Spec 作者）：同 spec 類流程（附錄 A 6-39、AC-09-18）——run 不結束、T0 以 iteration+1 重開、CLR 不變、不建立 bug entity。"""
    root = mkroot(tmp_path)
    out = py(root, T0 + """
rid, evd, apr, cid = t0_ambiguity()
h0 = P2.clr_sha(cid)
F.approve(apr, decision="reject", rationale="退回 Spec 作者")
run = engine.load_run(rid)
print(json.dumps({"t": tasks(rid), "status": run["status"], "cur": run["current_task_id"], "bug_exists": store.exists(f"runs/{rid}/entities/bug.yaml"),
                  "clr": [h0, P2.clr_sha(cid), clr.load(cid)["status"]]}))""")
    assert out["status"] == "RUNNING" and out["cur"] == "T0" and out["t"]["T0"] == {"status": "READY", "iteration": 1} and out["t"]["T1"]["status"] == "PENDING"
    assert out["bug_exists"] is False and out["clr"][0] == out["clr"][1] and out["clr"][2] == "ANSWERED"

def test_validator_ambiguity_paths_unchanged(tmp_path):
    """T2（Bug Validator）判定 AMBIGUITY：approve → bug DRAFT、T1 重開（iteration+1）；reject → bug REJECTED、run COMPLETED（回歸）。"""
    root = mkroot(tmp_path)
    out = py(root, T0 + """
res = {}; rid0, cid0 = e4_clr()
for dec in ("approve", "reject"):
    rid, evd = bug_run(); bd = bug_draft(rid, evd); v = bug_validate(rid, bd, evd, "AMBIGUITY")
    apr = F.waiting(rid); F.approve(apr, decision=dec, rationale="x")
    res[dec] = {"v": v["result"], "t": tasks(rid), "status": engine.load_run(rid)["status"], "bug": store.load(f"runs/{rid}/entities/bug.yaml")["status"]}
print(json.dumps(res))""")
    a, r = out["approve"], out["reject"]
    assert a["v"] == "AMBIGUITY" and a["bug"] == "DRAFT" and a["status"] == "RUNNING" and a["t"]["T1"] == {"status": "READY", "iteration": 1}
    assert r["bug"] == "REJECTED" and r["status"] == "COMPLETED"
