"""P4 測試用的正式流程（在子程序中、QAOS_ROOT 指向暫存 root 時呼叫）：派發包、決策點的分析提交、設計、驗證、核准。
每一步都經過正式 API（spec import／reference add 由測試以 CLI 先建立；new_run、dispatch、submit、evaluate_gate、approve、clarification answer），
不手造業務狀態。agent 的產出（artifact 檔）由 tests/helpers.write_artifact 寫入，這是「外部寫入」。"""
from tools.qaos import engine, store, spec_ops, sources, dispatch, clarification as clr
from tests import helpers as H

BY = "oscar@example.com"
SPEC, VER, REF, REF2, OTHER = "SPEC-DEMO-001", "1.0", "SPEC-REF-001", "SPEC-REFB-001", "SPEC-OTHER-001"

# 目標 spec 的原文（行號在測試中被引用）
TARGET_TEXT = """# 站台規格

## 角色與權限

| 子站台：刪除 | 可操作 | 可操作 |

## 刪除規則

任何站台都不能刪除。

## 角色指派

站長的指派範圍依手冊 v01 的角色模型（見 7.1.1 角色說明）。

## 錯誤回應

越權操作由後端拒絕。
"""
REF_TEXT = "# 權限\n\n## 實作要求\n\n須在後端每一支 API 強制執行。\n\n越權操作一律回「無權限」。\n"
REF2_TEXT = "# 出金\n\n## 核實\n\n出金核實由財務執行。\n"
OTHER_TEXT = "# 其他\n\n## 無關\n\n與站台無關的規則。\n"

def pin(sid=SPEC, ver=VER):
    return spec_ops.verify_pin(sid, ver)

def sref(quote, sid=SPEC, loc="§刪除規則"):
    return {"type": "spec", **pin(sid), "location": loc, "quote": quote}

def cref(cid, quote, rev=None):
    r = clr.load(cid)["answer_revisions"][-1 if rev is None else rev]
    return {"type": "clarification", "clarification_id": cid, "answer_rev": r["rev"], "answer_sha256": r["sha256"], "quote": quote}

def aref(apr_id, idx, quote):
    a = store.load(f"approvals/{apr_id}.yaml")
    return {"type": "approval", "approval_id": apr_id, "decision_sha256": sources.chash(a["decision"]), "resolution_index": idx, "quote": quote}

def ident(ref):
    return dispatch.basis_ref(ref)

def refs_status(sid=SPEC, ver=VER):
    _, _, e = spec_ops.find_entry(sid, ver); return spec_ops.references_status(e)

def cov(consulted=None, unconsulted=(), missing=(), waivers=(), status=None):
    return {"references_status": status or refs_status(), "consulted": consulted if consulted is not None else [pin()],
            "unconsulted_normative": list(unconsulted), "missing_sources": list(missing), "waivers": list(waivers)}

def missing(line, text, name, sid=SPEC):
    return {"cited_at": {**pin(sid), "line": line, "text": text}, "name": name}

def dp(qid="Q01", basis="defined_in_target", level="none", topic="permission", subject="site.child.delete", role=("admin",), params=None,
       known=(), sides=(), note=None, resolution="absent", coverage=None, **kw):
    d = {"question_id": qid, "topic": topic, "subject": subject, "role_scope": list(role), "params": params or {}, "level": level, "basis": basis,
         "known_rules": list(known), "coverage": coverage or cov()}
    if sides: d["conflict_sides"] = list(sides)
    if note: d["conflict_note"] = note
    if resolution != "absent": d["resolution"] = resolution
    d.update(kw); return d

def amb(level, raised, desc="決策點推導"):
    return {"level": level, "raised_level": raised, "description": desc}

def req(n, dps=(), ambiguity=None, rc=None, statement="站台刪除規則", risk="medium"):
    rid = f"REQ-DEMO-{n:03d}"
    r = {"requirement_id": rid, "version": 1, "spec_id": SPEC, "spec_version": VER, "type": "functional", "title": statement, "statement": statement,
         "acceptance_criteria": [{"ac_id": f"AC-DEMO-{n:03d}", "given": "已登入後台", "when": "操作", "then": "依規則"}],
         "spec_reference": {"spec_id": SPEC, "spec_version": VER, "location": "§刪除規則", "quote": "任何站台都不能刪除。"},
         "ambiguity": ambiguity, "risk": risk, "status": "DRAFT", "history": []}
    if dps: r["decision_points"] = list(dps)
    if rc is not None: r["rejection_contract"] = rc
    return r

def new_run() -> str:
    return engine.new_run("spec-to-testcase", {"spec_id": SPEC, "spec_version": VER}, BY, new_request=True)["run_id"]

def analyze(rid, reqs, consulted="auto", packet="auto", task="T1") -> dict:
    """T1：提交 SpecAnalysis＋RequirementModel（必要時自動派發）並跑 G-SPEC。回傳 gate 結果；提交被拒時回傳 {"submit": 問題}。"""
    rm_ = {"spec_id": SPEC, "spec_version": VER, "requirements": reqs,
           "traceability": [{"requirement_id": r["requirement_id"], "spec_reference": r["spec_reference"]} for r in reqs]}
    sa = {"spec_id": SPEC, "spec_version": VER, "content_hash": pin()["content_hash"], "summary": "s", "scope": {"in_scope": ["x"], "out_of_scope": []},
          "requirement_ids": [r["requirement_id"] for r in reqs], "ambiguities": [], "constraints": [], "edge_case_candidates": [], "open_questions": []}
    if consulted != "auto": sa["consulted_sources"] = consulted
    refs_ = [{"entity_type": "SpecVersion", "id": SPEC, "version": VER}]; src = {"type": "SpecVersion", "ids": [f"{SPEC}@{VER}"]}
    _, p1 = H.write_artifact(rid, task, "agent-spec-analyst", "SpecAnalysis", sa, refs_, src, "spec-analysis", packet=packet)
    rmid, p2 = H.write_artifact(rid, task, "agent-spec-analyst", "RequirementModel", rm_, refs_, src, "requirements", packet=packet)
    probs = []
    for p in (p1, p2):
        ok, pr = engine.submit(rid, task, str(p)); probs += pr
    if probs: return {"submit": probs, "result": "SUBMIT_INVALID", "issues": probs, "rmid": rmid}
    return {**engine.evaluate_gate(rid, task), "rmid": rmid}

def tc(n, rid, title, techs=("requirement_based",), types=("functional",), drefs=None, srcs=None, assumptions=None, expected="依規則顯示", mode="spec"):
    t = H.tc(f"TC-DRAFT-01ARZ3NDEKTSV4RRFFQ69G{n:04d}", title, rid, "AC-DEMO-" + rid[-3:], "ui_e2e", list(types), list(techs), [f"步驟 {title}"], expected,
             "§刪除規則", prio="medium", risk="medium", functional_area="DEMO", spec_id=SPEC,
             expected_result_spec_reference={"spec_id": SPEC, "spec_version": VER, "location": "§刪除規則"}, mode=mode)
    if drefs is not None: t["decision_refs"] = drefs
    if srcs is not None: t["source_refs"] = srcs
    if assumptions: t["assumptions"] = assumptions
    return t

def design(rid, tcs, uncovered=()) -> dict:
    """T2：提交 Draft＋Report 並跑 G-DESIGN。"""
    rids = sorted({r for t in tcs for r in t["requirement_ids"]})
    did, pd = H.write_artifact(rid, "T2", "agent-test-designer", "TestCaseDraft", {"mode": "spec", "spec_id": SPEC, "spec_version": VER, "testcases": tcs},
                               [{"entity_type": "Requirement", "id": r} for r in rids], {"type": "RequirementModel", "ids": []}, "test-design")
    _, pr = H.write_artifact(rid, "T2", "agent-test-designer", "TestDesignReport", H.design_report(did, tcs, [{"requirement_id": u, "reason": "本測試不涵蓋"} for u in uncovered]),
                             [{"entity_type": "Artifact", "id": did}], {"type": "TestCaseDraft", "ids": [did]}, "test-design")
    for p in (pd, pr):
        ok, pr_ = engine.submit(rid, "T2", str(p))
        if not ok: return {"submit": pr_, "result": "SUBMIT_INVALID", "issues": pr_, "did": did}
    return {**engine.evaluate_gate(rid, "T2"), "did": did}

def validate(rid, did, rmid, result="PASS", issues=None) -> dict:
    _, pv = H.write_artifact(rid, "T3", "agent-test-validator", "TestValidationReport", H.validation_report(did, rmid, result, issues),
                             [{"entity_type": "Artifact", "id": did}, {"entity_type": "Artifact", "id": rmid}], {"type": "TestCaseDraft", "ids": [did]}, "validation")
    ok, pr = engine.submit(rid, "T3", str(pv))
    if not ok: return {"submit": pr, "result": "SUBMIT_INVALID", "issues": pr}
    return engine.evaluate_gate(rid, "T3")

def missing_ref_issue(did):
    return {"testcase_id": did, "issue_type": "missing_reference", "severity": "major", "violated_requirement": None, "spec_reference": None,
            "evidence": "source_refs 指向派發包以外的 spec", "explanation": "只能引用派發包範圍內的來源", "recommended_change": "改用派發包內的來源"}

def waiting(rid):
    return engine.load_run(rid).get("waiting_on_approval_id")

def approve(apr, decision="approve", resolutions=None, rationale="test"):
    return engine.approve(apr, decision, BY, rationale=rationale, resolutions=resolutions, new_request=True)

def clrs(**match):
    out = []
    for p in store.glob("clarifications/*/*/CLR-*.yaml"):
        c = store.load(p)
        if all(c.get(k) == v for k, v in match.items()): out.append(c)
    return sorted(out, key=lambda c: c["clarification_id"])

def current_rev():
    from tools.qaos import rm
    return rm.latest_pin(SPEC, VER)

def revision_req(rid_):
    from tools.qaos import rm
    return rm.requirements_of(current_rev())[rid_]
