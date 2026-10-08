"""P5 測試用的正式流程（在子程序中呼叫）：建立 CLR 生命週期的 RA 夾具。全部經正式 API：run new、dispatch、submit、gate、approve、
clarification answer／ask／applicability add；agent 的產出由 tests/helpers.write_artifact 寫入（外部寫入）。"""
from tools.qaos import engine, store, clarification as clr, clr_lifecycle as L, sources
from tests import p4_flow as F
from tests.test_p4_decisions import CONFLICT_SIDES   # noqa: F401  （字串，供 eval 組裝需求）

SIDES = lambda: [F.sref("| 子站台：刪除 | 可操作 | 可操作 |", loc="§角色與權限"), F.sref("任何站台都不能刪除。")]
NOTE = "表格允許刪除子站台；刪除規則禁止"

def conflict_req(n=1, resolution=None, subject="site.child.delete", role=("admin",)):
    res = {} if resolution is None else {"resolution": resolution}
    amb = F.amb("none", "critical") if resolution else F.amb("critical", "critical")
    return F.req(n, [F.dp("Q01", "conflict", "critical", subject=subject, role=role, sides=SIDES(), note=NOTE, decision_needed="以表格或刪除規則為準", **res)], ambiguity=amb,
                 statement=f"站台刪除規則 {n}")

def ra_p1(n=1):
    """RA-P1：T1 回報 critical conflict → RESOLVE_AMBIGUITY → answer → approve（select_interpretation）。回傳 (rid, cid, apr)。"""
    rid = F.new_run(); g = F.analyze(rid, [conflict_req(n)]); assert g["result"] == "PASS", g
    apr = F.waiting(rid); cid = F.clrs(requirement_id=f"REQ-DEMO-{n:03d}")[0]["clarification_id"]
    clr.answer(cid, "任何站台都不能刪除，表格的「可操作」是舊文案。", "pm", "requirement_clarified", "oscar", new_request=True)
    F.approve(apr, resolutions=[{"requirement_id": f"REQ-DEMO-{n:03d}", "question_id": "Q01", "outcome": "select_interpretation", "source": F.cref(cid, "任何站台都不能刪除"),
                                 "rationale": "依 PM 回答：任何站台都不能刪除"}])
    return rid, cid, apr

def ra_p2(rid, cid, n=1):
    """RA-P2：T1 重開 → 以明確 SourceRef（clarification 型）引用 CLR 最新 rev 為 resolution → G-SPEC。回傳 gate 結果。"""
    res = {"source": F.cref(cid, "任何站台都不能刪除"), "decided_at": "2026-10-07", "adopted_side_index": 1}
    return F.analyze(rid, [conflict_req(n, res)])

def ra_p3_design(rid, cid, g, n=1, extra_tcs=()):
    """接續：Designer → Validator → ACTIVATE → run COMPLETED。回傳 TC ID 清單。"""
    src = F.cref(cid, "任何站台都不能刪除")
    dref = [{"requirement_id": f"REQ-DEMO-{n:03d}", "question_id": "Q01", "basis_ref": F.ident(src)}]
    d = F.design(rid, [F.tc(1, f"REQ-DEMO-{n:03d}", "刪除子站台被拒（依 PM 回答）", techs=["negative"], types=["negative"], drefs=dref, srcs=[src],
                            expected="系統拒絕刪除，提示子站台不可刪除"), *extra_tcs])
    assert d["result"] == "PASS", d
    v = F.validate(rid, d["did"], g["rmid"]); assert v["result"] == "PASS", v
    F.approve(F.waiting(rid))
    assert engine.load_run(rid)["status"] == "COMPLETED"
    return sorted(p.stem for p in store.glob("testcases/registry/TC-DEMO-*.yaml"))

def full_ra(n=1):
    rid, cid, apr = ra_p1(n); g = ra_p2(rid, cid, n); assert g["result"] == "PASS", g
    tcs = ra_p3_design(rid, cid, g, n)
    return {"rid": rid, "cid": cid, "apr": apr, "tcs": tcs, "target": f"SPEC-DEMO-001@1.0:REQ-DEMO-{n:03d}#Q01"}

def apply_(cid, path="a6", by="oscar", **kw):
    try: return L.apply(cid, path, by, impact_reviewed=kw.pop("impact_reviewed", "逐張確認"), new_request=True, **kw)
    except (L.LifecycleError, ValueError) as e: return {"error": str(e)}

def clr_sha(cid):
    return store.sha256_file(store.find_clarification(cid))
