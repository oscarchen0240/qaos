"""P6 自審 S00 的補測（requirement-a-p6-self-review-00.md）。狀態都以正式流程建立。"""
import json
from tests.test_p4_dispatch import mkroot, py

def test_ac_08_10_old_run_keeps_pinned_answer_rev_after_new_answer(tmp_path):
    """AC-08-10（P6-S00-05）：舊 run 的 revision 以 CLR rev 0 為 resolution；之後 PM 再回答（追加 rev 1，A5 → ANSWERED）；
    舊 run 接著 Designer → Validator → ACTIVATE，TC 以釘選的 rev 0 為依據 → G-DESIGN、G-TVAL PASS，run COMPLETED（依釘選的 rev 驗證，不因新答案失敗）。
    對照：同一 run 的 Designer 改引用最新的 rev 1（revision 沒有採用它）→ G-DESIGN FAIL。"""
    root = mkroot(tmp_path)
    out = py(root, """
from tests import p5_flow as P
rid, cid, apr = P.ra_p1(); g = P.ra_p2(rid, cid); assert g["result"] == "PASS", g
rev0 = clr.load(cid)["answer_revisions"][-1]["rev"]
clr.answer(cid, "任何站台都不能刪除；另外子站台也不能改名。", "pm", "requirement_clarified", "oscar", new_request=True)
c = clr.load(cid); rev1 = c["answer_revisions"][-1]["rev"]
def tcs(rev):
    src = F.cref(cid, "任何站台都不能刪除", rev=rev)
    return [F.tc(1, "REQ-DEMO-001", "刪除子站台被拒（依 PM 回答）", techs=["negative"], types=["negative"],
                 drefs=[{"requirement_id": "REQ-DEMO-001", "question_id": "Q01", "basis_ref": F.ident(src)}], srcs=[src], expected="系統拒絕刪除")]
bad = F.design(rid, tcs(rev1))
d = F.design(rid, tcs(rev0)); v = F.validate(rid, d["did"], g["rmid"]) if d["result"] == "PASS" else {"result": None}
if v["result"] == "PASS": F.approve(F.waiting(rid))
print(json.dumps({"revs": [rev0, rev1], "status_after_answer": c["status"], "bad": [bad["result"], bad.get("issues")], "d": [d["result"], d.get("issues")],
                  "v": v["result"], "run": engine.load_run(rid)["status"]}, default=str))""")
    assert out["revs"][1] == out["revs"][0] + 1 and out["status_after_answer"] == "ANSWERED"
    assert out["bad"][0] == "FAIL", out["bad"]
    assert out["d"][0] == "PASS", out["d"]
    assert out["v"] == "PASS" and out["run"] == "COMPLETED"
