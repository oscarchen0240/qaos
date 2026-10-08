"""P6 AC-A-B1-7 的正式流程 helper（不是 pytest 測試；檔名不以 test_ 開頭）：在 DAILYREPORT 真實資料的移轉後工作複本上，
以正式流程（engine.new_run、dispatch、submit、evaluate_gate、approve）做同版本 spec-change-impact。
agent 的產出（artifact 檔）由 tests/helpers.write_artifact 寫入（「外部寫入」，模擬 agent）；內容以快照中 RUN-20261001-007
（DAILYREPORT 0.1→0.2 的正式 CIA）既有的 SpecAnalysis／RequirementModel 為底，只改指定需求的 statement。
由 tests/p6_rehearsal.py --mode ac-b1-7 以子程序（QAOS_ROOT=工作複本）呼叫。"""
import copy, json
from tools.qaos import engine, store, rm, gates, dispatch
from tests import helpers as H

BY = "p6-rehearsal@example.com"
SPEC, VER, AREA, PRODUCT = "SPEC-DAILYREPORT-001", "0.2", "DAILYREPORT", "ba-admin"
BASE_RUN = "RUN-20261001-007"          # 快照中 DAILYREPORT 0.1→0.2 的正式 CIA（T0 產出作為重新分析的底稿）

def _art(run_id, aid):
    return store.load(store.find_artifact(aid))

def base_t0():
    run = engine.load_run(BASE_RUN); t0 = engine._task(run, "T0"); out = {}
    for aid in t0["output_artifact_ids"]:
        a = _art(BASE_RUN, aid); out[a["artifact_type"]] = copy.deepcopy(a["payload"])
    return out

def active():
    """本 spec 的全部 ACTIVE TC：[(tc_id, active_version, 版本檔)]。"""
    out = []
    for p in sorted(store.glob(f"testcases/registry/TC-*.yaml")):
        d = store.load(p)
        if d.get("status") != "ACTIVE" or d.get("active_version") is None: continue
        v = store.load(store.tc_version_path(d["testcase_id"], d["active_version"]))
        if v["spec_id"] == SPEC: out.append((d["testcase_id"], d["active_version"], v))
    return out

def pins():
    return {t: rm.tc_pin(t, v) for t, v, _ in active()}

def cia_new(from_rev, reason="declaration_changed"):
    return engine.new_run("spec-change-impact", {"spec_id": SPEC, "from_version": VER, "to_version": VER, "from_revision": from_rev, "reason": reason}, BY, new_request=True)["run_id"]

def t0(rid, changes):
    """T0 Spec Analyst：重新分析同一版本（spec 內容相同）；changes = {requirement_id: 新 statement}。回傳 (RM artifact id, gate 結果)。"""
    b = base_t0(); m = b["RequirementModel"]; sa = b["SpecAnalysis"]
    for r in m["requirements"]:
        if r["requirement_id"] in changes: r["statement"] = changes[r["requirement_id"]]
    sa.pop("consulted_sources", None)                                                    # 由 helpers 依本次派發包重新填入
    refs_ = [{"entity_type": "SpecVersion", "id": SPEC, "version": VER}]
    _, p1 = H.write_artifact(rid, "T0", "agent-spec-analyst", "SpecAnalysis", sa, refs_, {"type": "SpecVersion", "ids": [f"{SPEC}@{VER}"]}, "spec-analysis")
    rmid, p2 = H.write_artifact(rid, "T0", "agent-spec-analyst", "RequirementModel", m, refs_, {"type": "SpecVersion", "ids": [f"{SPEC}@{VER}"]}, "requirements")
    s1, s2 = engine.submit(rid, "T0", str(p1)), engine.submit(rid, "T0", str(p2))
    if not (s1[0] and s2[0]): return rmid, {"result": "SUBMIT_INVALID", "issues": [s1[1], s2[1]]}
    return rmid, engine.evaluate_gate(rid, "T0")

# ---------------------------------------------------------------- T1 CIA impact
def rdiff(a, b):
    """需求差異（依 revision 讀；statement 或 acceptance_criteria 不同 → changed）。"""
    out = []
    for r in sorted(set(a) | set(b)):
        if r not in a: out.append({"requirement_id": r, "change": "added"})
        elif r not in b: out.append({"requirement_id": r, "change": "removed"})
        else:
            same = (a[r]["statement"], a[r]["acceptance_criteria"]) == (b[r]["statement"], b[r]["acceptance_criteria"])
            out.append({"requirement_id": r, "change": "unchanged"} if same else {"requirement_id": r, "change": "changed", "detail": "statement 或 acceptance_criteria 改變"})
    return out

def cir_for(rid):
    """CIA agent（impact 階段）的判定（模擬）：候選＝本 spec 全部 ACTIVE TC（不論 spec_version、revision），依各自的 pin 分組；
    每組的 requirement_diff 以自己的 from_pin 對 run 的 to revision 比對（G7）。
    affected 的判定：TC 引用的需求，在「它自己的 pin」與 to 之間有變更——但 0.1 那組的 0.1→0.2 差異已由快照中的正式 CIA
    RUN-20261001-007 逐條判定過（留在 0.1 的 48 張當時判 unaffected），所以 0.1 那組以 0.2 R000 作為判定起點（只看之後的變更）。"""
    run = engine.load_run(rid); to = run["requirement_model_revision"]; fr = run["from_requirement_model_revision"]
    to_reqs = rm.requirements_of(to); base = rm.requirements_of(rm.pin_of(SPEC, VER, "R000")); groups = {}
    for t, v, _ in active(): groups.setdefault(json.dumps(rm.tc_pin(t, v), sort_keys=True), []).append((t, v))
    pg, impact = [], []
    for k, (pin_s, members) in enumerate(sorted(groups.items(), key=lambda x: (json.loads(x[0])["spec_version"], json.loads(x[0])["revision"]))):
        pin = json.loads(pin_s); own = rm.requirements_of(pin)
        d = rdiff(own, to_reqs)
        judge = d if pin["spec_version"] == VER else rdiff(base, to_reqs)
        chg = {x["requirement_id"] for x in judge if x["change"] != "unchanged"}
        pg.append({"from_pin": pin, "testcase_ids": [t for t, _ in members], "requirement_diff": d})
        for t, v in members:
            hit = sorted(set(store.load(store.tc_version_path(t, v))["requirement_ids"]) & chg)
            impact.append({"testcase_id": t, "active_version": v, "impact": "affected" if hit else "unaffected",
                           "reason": f"引用的需求 {', '.join(hit)} 改變" if hit else "引用的需求在本組判定起點之後沒有變更",
                           "affected_requirement_ids": hit, "pin_group_index": k})
    top = rdiff(rm.requirements_of(fr), to_reqs)
    return {"change_impact_id": f"CI-{SPEC}-{VER}-{VER}", "spec_id": SPEC, "from_version": VER, "to_version": VER, "from_rm_revision": fr, "to_rm_revision": to,
            "requirement_diff": top, "pin_groups": pg, "testcase_impact": impact,
            "summary": {"requirements_changed": sum(x["change"] == "changed" for x in top), "requirements_added": sum(x["change"] == "added" for x in top),
                        "requirements_removed": sum(x["change"] == "removed" for x in top),
                        "testcases_affected": sum(i["impact"] == "affected" for i in impact), "testcases_obsolete": 0,
                        "testcases_unaffected": sum(i["impact"] == "unaffected" for i in impact)},
            "completeness": {"all_active_requirements_judged": True, "all_referencing_testcases_judged": True}}

def impact(rid, cir):
    """以正式流程提交 CIR 到 T1：write_artifact（自動 dispatch）→ submit → evaluate_gate。回傳 (artifact id, gate 結果)。"""
    refs_ = [{"entity_type": "SpecVersion", "id": SPEC, "version": VER}] + [{"entity_type": "TestCaseVersion", "id": i["testcase_id"], "version": i["active_version"]}
                                                                            for i in cir["testcase_impact"] if store.exists(store.tc_version_path(i["testcase_id"], i["active_version"]))]
    cid, p = H.write_artifact(rid, "T1", "agent-change-impact-analyst", "ChangeImpactReport", cir, refs_, {"type": "SpecVersion", "ids": [f"{SPEC}@{VER}"]}, "change-impact")
    ok, pr = engine.submit(rid, "T1", str(p))
    if not ok: return cid, {"result": "SUBMIT_INVALID", "issues": pr}
    return cid, engine.evaluate_gate(rid, "T1")

# ---------------------------------------------------------------- T2～T5
_DRAFT_KEYS = None
def _draft_keys():
    global _DRAFT_KEYS
    if _DRAFT_KEYS is None:
        s = json.loads((store.ROOT / "schemas/artifact/testcase-draft.schema.json").read_text(encoding="utf-8")) if (store.ROOT / "schemas").exists() else None
        if s is None:
            import pathlib; s = json.loads((pathlib.Path(__file__).resolve().parents[1] / "schemas/artifact/testcase-draft.schema.json").read_text(encoding="utf-8"))
        _DRAFT_KEYS = set(s["properties"]["testcases"]["items"]["properties"])
    return _DRAFT_KEYS

def design(rid, cid, cir, rnd, changes):
    """T2 Designer（change）：只重產 affected 的 TC（以舊 ACTIVE 版本為底，改綁 0.2、supersedes 舊版）。回傳 (draft artifact id, 新稿, gate)。"""
    keys = _draft_keys(); new = []
    for n, i in enumerate(x for x in cir["testcase_impact"] if x["impact"] == "affected"):
        old = store.load(store.tc_version_path(i["testcase_id"], i["active_version"]))
        d = {k: copy.deepcopy(v) for k, v in old.items() if k in keys}
        d.update(draft_id=f"TC-DRAFT-01P6B17{rnd}{n:018d}", spec_version=VER, source="change_workflow",
                 supersedes_testcase={"testcase_id": i["testcase_id"], "version": i["active_version"]})
        d["expected_result_spec_reference"] = dict(d["expected_result_spec_reference"], spec_version=VER)
        d["expected_result"] = d["expected_result"].rstrip() + f"（P6 預演第 {rnd} 輪：依 {', '.join(i['affected_requirement_ids'])} 重新分析後的敘述複核）"
        d["design_rationale"] = f"P6 AC-A-B1-7 預演：{', '.join(i['affected_requirement_ids'])} 在同版本重新分析中改變，取代 {i['testcase_id']} v{i['active_version']}"
        new.append(d)
    rids = sorted({r for t in new for r in t["requirement_ids"]})
    did, pd = H.write_artifact(rid, "T2", "agent-test-designer", "TestCaseDraft", {"mode": "change", "spec_id": SPEC, "spec_version": VER, "change_impact_id": cir["change_impact_id"], "testcases": new},
                               [{"entity_type": "Requirement", "id": r} for r in rids] + [{"entity_type": "Artifact", "id": cid}], {"type": "ChangeImpactReport", "ids": [cid]}, "test-design")
    rep = H.design_report(did, new); rep["mode"] = "change"
    _, pr = H.write_artifact(rid, "T2", "agent-test-designer", "TestDesignReport", rep, [{"entity_type": "Artifact", "id": did}], {"type": "TestCaseDraft", "ids": [did]}, "test-design")
    s1, s2 = engine.submit(rid, "T2", str(pd)), engine.submit(rid, "T2", str(pr))
    if not (s1[0] and s2[0]): return did, new, {"result": "SUBMIT_INVALID", "issues": [s1[1], s2[1]]}
    return did, new, engine.evaluate_gate(rid, "T2")

def validate(rid, did, rmid, new):
    n_req = len({r for t in new for r in t["requirement_ids"]}); n_ac = len({a for t in new for a in t["acceptance_criteria_ids"]})
    rep = {"result": "PASS", "testcase_draft_artifact_id": did, "validated_against": {"spec_id": SPEC, "spec_version": VER, "requirement_model_artifact_id": rmid},
           "issues": [], "advisories": [], "coverage_summary": {"requirements_total": n_req, "requirements_covered": n_req, "ac_total": n_ac, "ac_covered": n_ac},
           "checks": {k: True for k in ["no_spec_mismatch", "no_requirement_mismatch", "expected_result_valid", "steps_executable", "traceability_complete", "no_critical_ambiguity", "no_duplicates", "edge_cases_reasonable"]}}
    tvr, p = H.write_artifact(rid, "T3", "agent-test-validator", "TestValidationReport", rep, [{"entity_type": "Artifact", "id": did}], {"type": "TestCaseDraft", "ids": [did]}, "validation")
    ok, pr = engine.submit(rid, "T3", str(p))
    if not ok: return tvr, {"result": "SUBMIT_INVALID", "issues": pr}
    return tvr, engine.evaluate_gate(rid, "T3")

DIMS = ["boundary", "exception_flow", "concurrency", "duplicate_submission", "permission"]
def risk_review(rid, did, tvr, new):
    """T3RR（DAILYREPORT 是高風險 area，ADR-009）：五面向逐一 covered，沒有 finding。"""
    payload = {"reviewed": {"testcase_draft_artifact_id": did, "validation_report_artifact_id": tvr, "functional_area": AREA, "spec_id": SPEC, "spec_version": VER,
                            "testcase_draft_ids": [t["draft_id"] for t in new]},
               "dimension_results": [{"dimension": x, "status": "covered", "rationale": f"{x}：本次只重產受影響的 TC，沿用舊版已涵蓋的情境"} for x in DIMS],
               "findings": [], "summary": "P6 預演抽查：五面向沒有新增缺口"}
    _, p = H.write_artifact(rid, "T3RR", "agent-tc-risk-reviewer", "TCRiskReview", payload, [{"entity_type": "Artifact", "id": did}, {"entity_type": "Artifact", "id": tvr}],
                            {"type": "TestCaseDraft", "ids": [did]}, "risk-review")
    ok, pr = engine.submit(rid, "T3RR", str(p))
    if not ok: return {"result": "SUBMIT_INVALID", "issues": pr}
    return engine.evaluate_gate(rid, "T3RR")

def compare(rid, cid, cir, new):
    vcr = {"change_impact_id": cir["change_impact_id"],
           "comparisons": [{"testcase_id": d["supersedes_testcase"]["testcase_id"], "old_version": d["supersedes_testcase"]["version"], "new_draft_id": d["draft_id"], "verdict": "changed",
                            "field_diffs": [{"field": "expected_result", "old": "-", "new": d["expected_result"]}], "impacted_requirement_ids": d["requirement_ids"]} for d in new],
           "retire_recommendations": [], "summary": {"unchanged": 0, "changed": len(new), "added": 0, "removed": 0}}
    aid, p = H.write_artifact(rid, "T4", "agent-change-impact-analyst", "VersionComparisonReport", vcr, [{"entity_type": "Artifact", "id": cid}], {"type": "ChangeImpactReport", "ids": [cid]}, "change-impact")
    ok, pr = engine.submit(rid, "T4", str(p))
    if not ok: return aid, {"result": "SUBMIT_INVALID", "issues": pr}
    return aid, engine.evaluate_gate(rid, "T4")

# ---------------------------------------------------------------- 觀察
def task_states(rid):
    run = engine.load_run(rid)
    return {t["task_id"]: {"status": t["status"], "iteration": t.get("iteration"), "outputs": len(t.get("output_artifact_ids") or [])} for t in run["tasks"]}

def ci_status(rid):
    p = f"runs/{rid}/entities/change-impact.yaml"
    return store.load(p)["status"] if store.exists(p) else None

def packet_pins(rid, task_id):
    run = engine.load_run(rid); e = (engine._task(run, task_id).get("dispatch_packets") or [None])[-1]
    if e is None: return None
    pk = dispatch.load_packet(e)["rm_pins"]
    return {"from": pk.get("from"), "target": pk.get("target"), "pin_groups": pk.get("pin_groups")}

def groups_view(cir):
    return [{"from_pin": f"{g['from_pin']['spec_version']} {g['from_pin']['revision']}", "n": len(g["testcase_ids"]), "testcase_ids": g["testcase_ids"],
             "diff_changed": sorted(d["requirement_id"] for d in g["requirement_diff"] if d["change"] != "unchanged"), "diff_n": len(g["requirement_diff"])} for g in cir["pin_groups"]]

# ---------------------------------------------------------------- 一輪完整的同版本 CIA（AC-A-B1-7 第 1、2 段）
def sidecar_shas():
    import hashlib
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((store.ROOT / "testcases/_bindings").glob("TC-DAILYREPORT-*.yaml"))}

def pin_view(p): return f"{p['spec_version']} {p['revision']}" if p else None

def full_round(from_rev, changes, rnd, negative_only_from_group=False):
    """正式流程：run new → T0 → T1（可選先送「只判 run 的 from 端那組」的反例）→ T2 → T3 → T3RR → T4 → T5 approve。逐停點記錄。"""
    out = {"stops": []}; sc_before = sidecar_shas(); act_before = {t: v for t, v, _ in active()}
    def stop(name, **kw):
        run = engine.load_run(rid)
        out["stops"].append({"stop": name, "run_status": run["status"], "current_task": run.get("current_task_id"), "change_impact": ci_status(rid), **kw})
    rid = cia_new(from_rev); out["run_id"] = rid; run = engine.load_run(rid)
    out["from_pin"] = run["from_requirement_model_revision"]
    stop("run new", T0=task_states(rid)["T0"]["status"], from_pin=pin_view(out["from_pin"]))
    rmid, g = t0(rid, changes); run = engine.load_run(rid); out["to_pin"] = run.get("requirement_model_revision")
    stop("T0 G-SPEC", gate=g["result"], issues=g["issues"][:5], to_pin=pin_view(out["to_pin"]), T1=task_states(rid)["T1"]["status"])
    cir = cir_for(rid); out["groups"] = groups_view(cir)
    out["affected"] = [i["testcase_id"] for i in cir["testcase_impact"] if i["impact"] == "affected"]
    if negative_only_from_group:                                                                  # AC-09-28：缺少 TC-B 的判定 → FAIL
        k1 = next(k for k, g_ in enumerate(cir["pin_groups"]) if g_["from_pin"] == out["from_pin"])
        bad = copy.deepcopy(cir); bad["pin_groups"] = [bad["pin_groups"][k1]]
        bad["testcase_impact"] = [dict(i, pin_group_index=0) for i in bad["testcase_impact"] if i["pin_group_index"] == k1]
        _, gb = impact(rid, bad)
        stop("T1 反例：只判 run 的 from 端那組", gate=gb["result"], issues=[i[:200] for i in gb["issues"]], T1=task_states(rid)["T1"])
        out["only_from_group"] = {"result": gb["result"], "issues": [i[:200] for i in gb["issues"]], "T1_after": task_states(rid)["T1"], "ci_after": ci_status(rid)}
        if engine.load_run(rid)["status"] != "RUNNING" or task_states(rid)["T1"]["status"] != "READY":
            out["aborted"] = "反例沒有 FAIL，run 已離開 T1；本輪無法繼續"; return out
    cid, g = impact(rid, cir)
    out["packet_T1"] = {k: (pin_view(v) if k != "pin_groups" else [pin_view(x) for x in v or []]) for k, v in (packet_pins(rid, "T1") or {}).items()}
    stop("T1 G-IMPACT", gate=g["result"], issues=g["issues"][:5], T2=task_states(rid)["T2"]["status"])
    if not out["affected"]:
        out["final"] = {"status": engine.load_run(rid)["status"], "change_impact": ci_status(rid), "tasks": task_states(rid)}; return out
    did, new, g = design(rid, cid, cir, rnd, changes); stop("T2 G-DESIGN", gate=g["result"], issues=g["issues"][:5])
    tvr, g = validate(rid, did, rmid, new); stop("T3 G-TVAL", gate=g["result"], issues=g["issues"][:5])
    g = risk_review(rid, did, tvr, new); stop("T3RR G-RISK", gate=g["result"], issues=g["issues"][:5])
    _, g = compare(rid, cid, cir, new)
    out["packet_T4"] = {k: (pin_view(v) if k != "pin_groups" else [pin_view(x) for x in v or []]) for k, v in (packet_pins(rid, "T4") or {}).items()}
    run = engine.load_run(rid); apr = run.get("waiting_on_approval_id"); out["approval"] = apr
    stop("T4 G-COMPARE", gate=g["result"], issues=g["issues"][:5], approval=apr, approval_type=store.load(f"approvals/{apr}.yaml")["type"] if apr else None)
    engine.approve(apr, "approve", BY, rationale="P6 AC-A-B1-7 預演：套用", new_request=True)
    stop("T5 APPLY_CHANGE approve", approval_status=store.load(f"approvals/{apr}.yaml")["status"])
    act_after = {t: v for t, v, _ in active()}; sc_after = sidecar_shas(); p = pins()
    out["final"] = {"status": engine.load_run(rid)["status"], "change_impact": ci_status(rid), "tasks": task_states(rid),
                    "affected_after": {t: {"version": act_after[t], "old_version": act_before[t], "pin": pin_view(p[t]),
                                           "pin_in_version_file": pin_view(store.load(store.tc_version_path(t, act_after[t])).get("requirement_model_revision"))} for t in out["affected"]},
                    "unaffected_version_changed": sorted(t for t in act_before if t not in out["affected"] and act_after.get(t) != act_before[t]),
                    "sidecars_changed": sorted(k for k in sc_before if sc_after.get(k) != sc_before[k]), "sidecars_added": sorted(set(sc_after) - set(sc_before)),
                    "pins_by_group": _count_pins(p), "candidates": len(p)}
    return out

def _count_pins(p):
    c = {}
    for x in p.values(): c[pin_view(x)] = c.get(pin_view(x), 0) + 1
    return dict(sorted(c.items()))

# ---------------------------------------------------------------- AC-09-35～41 反例（AC-A-B1-7 第 3 段）
EXPECT = {"AC-09-35 只列 A 那一組（B 那組缺，B 宣稱 unaffected）": "G2", "AC-09-36 B 同時在兩組": "G2", "AC-09-37 B 被放進 R001 組": "G4",
          "AC-09-38 組中有不在候選內的 TC-Z": "G2", "AC-09-39 testcase_impact 有不在候選內的 TC-Z": "G5", "AC-09-40a 有空組": "G1",
          "AC-09-40b 兩組的 from_pin 相同": "G3", "AC-09-41 B 的 pin_group_index 指向 R001 組": "G6",
          "（附加）G7 B 那組的 requirement_diff 少一條": "G7", "（附加）G8 B 那組的 from_pin sha256 錯誤": "G8"}

def outsider():
    """TC-Z：不在候選內的真實 TC（別的 spec 的 ACTIVE TC）。"""
    for p in sorted(store.glob("testcases/registry/TC-*.yaml")):
        d = store.load(p)
        if d.get("status") == "ACTIVE" and d.get("active_version") and store.load(store.tc_version_path(d["testcase_id"], d["active_version"]))["spec_id"] != SPEC:
            return d["testcase_id"], d["active_version"]

def mutate(name, c, A, B, z):
    g = c["pin_groups"]; imp = c["testcase_impact"]
    kB = next(k for k, x in enumerate(g) if B in x["testcase_ids"]); kA = next(k for k, x in enumerate(g) if A in x["testcase_ids"])
    iB = next(i for i in imp if i["testcase_id"] == B)
    if name.startswith("AC-09-35"):
        assert iB["impact"] == "unaffected"; del g[kB]
    elif name.startswith("AC-09-36"): g[kA]["testcase_ids"].append(B)
    elif name.startswith("AC-09-37"): g[kB]["testcase_ids"].remove(B); g[kA]["testcase_ids"].append(B); iB["pin_group_index"] = kA
    elif name.startswith("AC-09-38"): g[kB]["testcase_ids"].append(z[0])
    elif name.startswith("AC-09-39"): imp.append(dict(iB, testcase_id=z[0], active_version=z[1]))
    elif name.startswith("AC-09-40a"): g.append({"from_pin": c["to_rm_revision"], "testcase_ids": [], "requirement_diff": [{"requirement_id": d["requirement_id"], "change": "unchanged"} for d in c["requirement_diff"]]})
    elif name.startswith("AC-09-40b"): g[kA]["from_pin"] = copy.deepcopy(g[kB]["from_pin"])
    elif name.startswith("AC-09-41"): iB["pin_group_index"] = kA
    elif "G7" in name: g[kB]["requirement_diff"] = g[kB]["requirement_diff"][1:]
    elif "G8" in name: g[kB]["from_pin"] = dict(g[kB]["from_pin"], sha256="0" * 64)
    return c

def _recover_run(n, changes):
    """反例意外沒有 FAIL（例如突變對照讓某個檢查失效）時，run 已離開 T1：在同一份工作複本再製造一次 declaration_changed
    （匯入合成參考、reference add，與腳本其他輪相同的正式指令），從最新 revision 開新的同版本 CIA run，讓後續反例仍各自在 READY 的 T1 提交。"""
    from tools.qaos.cli import main as cli
    f = store.ROOT.parent / f"{store.ROOT.name}-synthetic-recover-{n}.md"
    f.write_text(f"# 補充參考 R{n}（P6 預演合成檔）\n\n## 說明\n\n反例逃脫後重開 run 用。\n", encoding="utf-8")
    sid = f"SPEC-DAILYREPORTREC-{n:03d}"
    cli(["spec", "import", str(f), "--spec-id", sid, "--version", "1.0", "--product", PRODUCT, "--area", AREA, "--by", BY])
    cli(["spec", "reference", "add", f"{SPEC}@{VER}", "--ref", f"{sid}@1.0", "--role", "informative", "--by", BY])
    rid = cia_new(rm.latest_pin(SPEC, VER)["revision"]); t0(rid, changes)
    return rid

def negatives_round(from_rev):
    """同版本 CIA 一個 run：T0 重新分析（內容不變）→ T1 依序提交 10 份錯誤的 CIR（各自從正確 CIR 的深拷貝突變，互不污染），
    每份 FAIL 後 T1 回 READY、change_impact 不前進；最後提交正確的 CIR → PASS → NO_IMPACT → COMPLETED。
    某份反例意外沒有 FAIL（run 離開 T1）時記為逃脫，並以 _recover_run 開新 run 繼續後面的反例。"""
    out = {"cases": [], "recovery_runs": []}
    changes = {"REQ-DAILYREPORT-013": "P6 預演：重新分析後的 REQ-013 敘述（第 1 輪）", "REQ-DAILYREPORT-012": "P6 預演：重新分析後的 REQ-012 敘述（第 2 輪）"}
    rid = cia_new(from_rev); out["run_id"] = rid
    rmid, g0 = t0(rid, changes)
    run = engine.load_run(rid); out["T0"] = g0["result"]; out["from_pin"] = pin_view(run["from_requirement_model_revision"]); out["to_pin"] = pin_view(run["requirement_model_revision"])
    good = cir_for(rid); out["groups"] = groups_view(good)
    p = pins()
    A = sorted(t for t, x in p.items() if x["spec_version"] == VER and x["revision"] == "R001")[0]
    B = sorted(t for t, x in p.items() if x["spec_version"] == VER and x["revision"] == "R000")[0]
    z = outsider(); out.update(A=A, A_pin=pin_view(p[A]), B=B, B_pin=pin_view(p[B]), Z=z[0])
    for name, want in EXPECT.items():
        if engine.load_run(rid)["status"] != "RUNNING" or task_states(rid)["T1"]["status"] != "READY":
            rid = _recover_run(len(out["recovery_runs"]) + 1, changes); out["recovery_runs"].append(rid); good = cir_for(rid)
        bad = mutate(name, copy.deepcopy(good), A, B, z)
        before = task_states(rid)["T1"]
        try: _, g = impact(rid, bad); err = None
        except Exception as e: g, err = {"result": "EXCEPTION", "issues": []}, f"{type(e).__name__}: {e}"[:500]
        after = task_states(rid)["T1"]
        codes = sorted({i.split("：")[0] for i in g["issues"] if i[:1] == "G" and i[1:2].isdigit()})
        out["cases"].append({"case": name, "expect": want, "run_id": rid, "result": g["result"], "codes": codes, "issues": [i[:220] for i in g["issues"]][:8], "error": err,
                             "T1_before": before, "T1_after": after, "change_impact": ci_status(rid), "run_status": engine.load_run(rid)["status"]})
    if engine.load_run(rid)["status"] != "RUNNING" or task_states(rid)["T1"]["status"] != "READY":
        rid = _recover_run(len(out["recovery_runs"]) + 1, changes); out["recovery_runs"].append(rid); good = cir_for(rid)
    _, g = impact(rid, good)
    run = engine.load_run(rid)
    out["good"] = {"run_id": rid, "result": g["result"], "issues": g["issues"][:5], "status": run["status"], "change_impact": ci_status(rid), "tasks": task_states(rid),
                   "affected": [i["testcase_id"] for i in good["testcase_impact"] if i["impact"] == "affected"]}
    return out
