"""Quality Gate 的 Structural 檢查（deterministic）。每個函式回傳 issues list；空 = PASS。"""
import hashlib
from . import store, refs

def _payload(art): return art["payload"]

def g_spec(run, task, arts) -> list[str]:
    issues = []
    rm = arts.get("RequirementModel"); sa = arts.get("SpecAnalysis")
    if not rm: return ["缺 RequirementModel artifact"]
    if not sa: issues.append("缺 SpecAnalysis artifact")
    p = _payload(rm); d = store.spec_dir(p["spec_id"])
    if not d: return [f"Spec {p['spec_id']} 不存在"]
    spec = store.load(d / "spec.yaml")
    ver = next((v for v in spec["versions"] if v["spec_version"] == p["spec_version"]), None)
    if not ver: return [f"SpecVersion {p['spec_version']} 不存在"]
    actual = store.sha256_file(d / ver["file"])
    if actual != ver["content_hash"]: issues.append(f"Spec 內容 hash 與 spec.yaml 不符（{ver['file']}）")
    if sa and _payload(sa).get("content_hash") != ver["content_hash"]: issues.append("SpecAnalysis.content_hash 與 Spec 版本不符")
    ids = set()
    for r in p["requirements"]:
        if r["requirement_id"] in ids: issues.append(f"重複 requirement_id {r['requirement_id']}")
        ids.add(r["requirement_id"])
        if not r.get("acceptance_criteria"): issues.append(f"{r['requirement_id']} 沒有 Acceptance Criterion")
        if not r.get("spec_reference", {}).get("location"): issues.append(f"{r['requirement_id']} 缺 spec_reference.location")
        if r["spec_id"] != p["spec_id"] or r["spec_version"] != p["spec_version"]: issues.append(f"{r['requirement_id']} 的 spec 綁定與 model 不一致")
    for t in p.get("traceability", []):
        if t["requirement_id"] not in ids: issues.append(f"traceability 指向不存在的 {t['requirement_id']}")
    if sa:
        for rid in _payload(sa).get("requirement_ids", []):
            if rid not in ids: issues.append(f"SpecAnalysis.requirement_ids 含不存在的 {rid}")
    return issues

def _active_requirements(spec_id, spec_version):
    path = store.requirements_path(spec_id, spec_version)
    if not store.exists(path): return None
    return {r["requirement_id"]: r for r in store.load(path)["requirements"]}

NON_HAPPY_TYPES = {"negative", "boundary"}
NON_HAPPY_TECH = {"negative", "error_guessing", "boundary_value"}
MAX_EXPLORATORY_PER_REQ = 3

def is_exploratory(tc) -> bool:
    return bool(tc.get("assumptions"))

def g_design(run, task, arts) -> list[str]:
    issues = []
    tcd = arts.get("TestCaseDraft"); tdr = arts.get("TestDesignReport")
    if not tcd or not tdr: return ["缺 TestCaseDraft 或 TestDesignReport"]
    p = _payload(tcd); rep = _payload(tdr)
    reqs = _active_requirements(p["spec_id"], p["spec_version"])
    if reqs is None: return [f"RequirementModel {p['spec_id']}@{p['spec_version']} 尚未持久化"]
    ac_owner = {}   # ac_id → 所屬 requirement_id 集合（AC 嵌在 requirement 底下，正常只有一個）
    for rid, r in reqs.items():
        for ac in r.get("acceptance_criteria", []): ac_owner.setdefault(ac["ac_id"], set()).add(rid)
    ac_ids = set(ac_owner)
    seen = {}; draft_ids = set(); by_req = {}; tech_count = {}
    for tc in p["testcases"]:
        did = tc["draft_id"]; draft_ids.add(did)
        for t in tc["design_techniques"]: tech_count[t] = tech_count.get(t, 0) + 1
        for rid in tc["requirement_ids"]:
            by_req.setdefault(rid, []).append(tc)
            if rid not in reqs: issues.append(f"{did} 引用不存在的 requirement {rid}")
            elif reqs[rid]["status"] != "ACTIVE":
                issues.append(f"{did} 引用非 ACTIVE 的 requirement {rid}（{reqs[rid]['status']}）")
            elif (reqs[rid].get("ambiguity") or {}).get("level") == "critical" and not (reqs[rid].get("ambiguity") or {}).get("resolved_by_approval"):
                issues.append(f"{did} 為 critical ambiguity 的 {rid} 設計 TC")
        for aid in tc.get("acceptance_criteria_ids", []):
            if aid not in ac_ids: issues.append(f"{did} 引用不存在的 AC {aid}")
            elif not (ac_owner[aid] & set(tc["requirement_ids"])):
                issues.append(f"{did} 引用的 AC {aid} 屬於 {'/'.join(sorted(ac_owner[aid]))}，不在本 TC 的 requirement_ids 內")
        if not tc["expected_result"].strip(): issues.append(f"{did} expected_result 為空")
        if not tc["design_techniques"]: issues.append(f"{did} 無 design_techniques")
        for a in tc.get("assumptions", []):
            if a.get("needs_human_confirmation") is not True: issues.append(f"{did} 的 assumption 未標 needs_human_confirmation: true（exploratory 案例的假設必須外顯）")
            if a["requirement_id"] not in tc["requirement_ids"]: issues.append(f"{did} 的 assumption 指向非本 TC 的 requirement {a['requirement_id']}")
        if p["mode"] == "change" and not tc.get("supersedes_testcase") and not tc.get("source_ref", "").startswith("new_required"):
            issues.append(f"{did} mode=change 但無 supersedes_testcase（新 TC 需 source_ref 以 new_required 開頭）")
        h = hashlib.sha1((tc["title"].strip() + "|" + "|".join(s["action"].strip() for s in tc["steps"])).encode()).hexdigest()
        if h in seen: issues.append(f"{did} 與 {seen[h]} 重複（title+steps）")
        seen[h] = did
    if rep["testcase_draft_artifact_id"] != tcd["artifact_id"]: issues.append("TestDesignReport 指向的 draft artifact 不是本次提交的")
    covered = {row["requirement_id"] for row in rep["coverage_matrix"] if row["draft_ids"]}
    uncovered = {u["requirement_id"]: u["reason"] for u in rep["uncovered_with_reason"]}
    scope = set(reqs) if p["mode"] == "spec" else covered | set(uncovered)
    for rid in scope:
        if rid in reqs and reqs[rid]["status"] == "ACTIVE" and rid not in covered and rid not in uncovered:
            issues.append(f"requirement {rid} 未被覆蓋且無 uncovered_with_reason")
    for row in rep["coverage_matrix"]:
        for did in row["draft_ids"]:
            if did not in draft_ids: issues.append(f"coverage_matrix 引用不存在的 draft {did}")
    # --- technique_summary 必須與 Draft 實際統計一致 ---
    declared = {t["technique"]: t["count"] for t in rep["technique_summary"]}
    for tech, n in tech_count.items():
        if declared.get(tech) != n: issues.append(f"technique_summary.{tech} 宣告 {declared.get(tech)}，Draft 實際 {n}")
    for tech, n in declared.items():
        if tech not in tech_count and n: issues.append(f"technique_summary.{tech} 宣告 {n}，Draft 實際 0")
    # --- 負向 / 反邏輯覆蓋（行為契約驅動） ---
    def non_happy(tc): return bool(set(tc["test_types"]) & NON_HAPPY_TYPES or set(tc["design_techniques"]) & NON_HAPPY_TECH)
    total_non_happy = sum(1 for tc in p["testcases"] if non_happy(tc))
    for rid in scope:
        r = reqs.get(rid)
        if not r or r["status"] != "ACTIVE": continue
        tcs = by_req.get(rid, []); reason = uncovered.get(rid, "")
        if r.get("risk") == "high" and not any(non_happy(tc) for tc in tcs) and not reason.startswith("NO_REJECTION_CONTRACT:"):
            issues.append(f"{rid} 為 high risk 但沒有任何 negative / boundary / error_guessing 案例（或 uncovered_with_reason 需以 'NO_REJECTION_CONTRACT:' 開頭）")
        if r.get("behavior_kind") == "rejection" and tcs and not any("negative" in tc["test_types"] for tc in tcs):
            issues.append(f"{rid} 為 rejection 類需求，必須有 test_types 含 negative 的案例")
        cons = [i for i in r.get("inputs", []) if any(k in (i.get("constraints") or {}) for k in ("min", "max", "min_length", "max_length"))]
        if cons and tcs and not any("boundary_value" in tc["design_techniques"] for tc in tcs):
            issues.append(f"{rid} 的 inputs 有數值/長度限制（{', '.join(i['name'] for i in cons)}），必須有 boundary_value 案例")
        if r.get("states") and tcs and not any("state_transition" in tc["design_techniques"] for tc in tcs):
            issues.append(f"{rid} 定義了狀態轉換，必須有 state_transition 案例")
        rc = r.get("rejection_contract")
        if rc and rc.get("defined") is False:
            for tc in tcs:
                if set(tc["design_techniques"]) & {"negative", "error_guessing"} and not is_exploratory(tc):
                    issues.append(f"{tc['draft_id']}：{rid} 的 rejection_contract 未定義，以 negative / error_guessing 技術寫的案例必須是 exploratory（assumptions + needs_human_confirmation），不得寫成確定規則；若 expected 有條文依據請改用 requirement_based / boundary_value")
        n_exp = sum(1 for tc in tcs if is_exploratory(tc))
        if n_exp > MAX_EXPLORATORY_PER_REQ: issues.append(f"{rid} 有 {n_exp} 條 exploratory，超過上限 {MAX_EXPLORATORY_PER_REQ}（Spec 缺錯誤契約應回補 Spec，而非堆案例）")
    if p["testcases"] and total_non_happy == 0 and any(reqs[r]["status"] == "ACTIVE" and r not in uncovered for r in scope if r in reqs):
        issues.append("整份 Draft 沒有任何 negative / boundary / error_guessing 案例")
    sc = rep["self_check"]
    for k, v in sc.items():
        if v is not True: issues.append(f"self_check.{k} 未通過")
    return issues

def g_tval(run, task, arts) -> list[str]:
    rep = arts.get("TestValidationReport")
    if not rep: return ["缺 TestValidationReport"]
    p = _payload(rep); issues = []
    draft = store.find_artifact(p["testcase_draft_artifact_id"])
    if not draft: return [f"報告指向的 draft {p['testcase_draft_artifact_id']} 不存在"]
    did_set = {tc["draft_id"] for tc in store.load(draft)["payload"]["testcases"]}
    if p["result"] == "FAIL" and not p["issues"]: issues.append("FAIL 但 issues 為空")
    for i in p["issues"] + p["advisories"]:
        if i["testcase_id"] not in did_set and i["testcase_id"] != "*": issues.append(f"issue 指向不存在的 draft {i['testcase_id']}")
    if p["result"] == "PASS" and any(i["severity"] in ("blocker", "major") for i in p["issues"]):
        issues.append("PASS 但含 blocker/major issue")
    return issues

def g_bval(run, task, arts) -> list[str]:
    """T1（Bug Analyst 提交 BugDraft）只跑 structural；T2（Validator）跑報告一致性。"""
    issues = []
    bd = arts.get("BugDraft"); rep = arts.get("BugValidationReport")
    if bd:
        p = _payload(bd)
        for eid in p["evidence_ids"]:
            err = refs.resolve({"entity_type": "Evidence", "id": eid})
            if err: issues.append(err)
        for m in p["actual_result_evidence_map"]:
            if m["evidence_id"] not in p["evidence_ids"]: issues.append(f"actual_result_evidence_map 引用未列入 evidence_ids 的 {m['evidence_id']}")
        r, _ = refs.find_requirement(p["requirement_id"], p["spec_id"], p["spec_version"])
        if not r: issues.append(f"requirement {p['requirement_id']} 不在 {p['spec_id']}@{p['spec_version']} 的 RequirementModel")
        if not p["reproduction_steps"]: issues.append("reproduction_steps 為空")
    if rep:
        p = _payload(rep)
        if p["result"] == "FAIL" and not p["issues"]: issues.append("FAIL 但 issues 為空")
        if p["result"] == "PASS":
            for ev in p["evidence_verification"]:
                if not (ev["hash_verified"] and ev["supports_claim"]): issues.append(f"PASS 但 evidence {ev['evidence_id']} 未通過驗證")
            if not all(p["checks"].values()): issues.append("PASS 但 checks 有 false")
        if p["result"] == "DUPLICATE" and not p["duplicate_check"]["duplicate_of"]: issues.append("DUPLICATE 但無 duplicate_of")
    return issues

def g_impact(run, task, arts) -> list[str]:
    cir = arts.get("ChangeImpactReport")
    if not cir: return ["缺 ChangeImpactReport"]
    p = _payload(cir); issues = []
    for v in (p["from_version"], p["to_version"]):
        err = refs.resolve({"entity_type": "SpecVersion", "id": p["spec_id"], "version": v})
        if err: issues.append(err)
    to_reqs = _active_requirements(p["spec_id"], p["to_version"]) or {}
    from_reqs = _active_requirements(p["spec_id"], p["from_version"]) or {}
    judged = {d["requirement_id"] for d in p["requirement_diff"]}
    for rid in set(from_reqs) | set(to_reqs):
        if rid not in judged: issues.append(f"requirement {rid} 未出現在 requirement_diff")
    judged_tc = {t["testcase_id"] for t in p["testcase_impact"]}
    for ptr in (store.ROOT / "testcases" / "registry").glob("TC-*.yaml"):
        d = store.load(ptr)
        if d["active_version"] is None: continue
        v = store.load(store.tc_version_path(d["testcase_id"], d["active_version"]))
        if v["spec_id"] == p["spec_id"] and v["spec_version"] == p["from_version"] and d["testcase_id"] not in judged_tc:
            issues.append(f"ACTIVE TC {d['testcase_id']}（引用 {p['from_version']}）未出現在 testcase_impact")
    if not (p["completeness"]["all_active_requirements_judged"] and p["completeness"]["all_referencing_testcases_judged"]):
        issues.append("completeness 自我宣告未通過")
    return issues

def g_compare(run, task, arts) -> list[str]:
    vcr = arts.get("VersionComparisonReport")
    if not vcr: return ["缺 VersionComparisonReport"]
    p = _payload(vcr); issues = []
    for c in p["comparisons"]:
        if c["verdict"] in ("changed", "unchanged", "removed") and (c["testcase_id"] is None or c["old_version"] is None):
            issues.append(f"verdict {c['verdict']} 需要 testcase_id + old_version")
        if c["verdict"] in ("changed", "unchanged", "added") and c["new_draft_id"] is None:
            issues.append(f"verdict {c['verdict']} 需要 new_draft_id")
        if c["verdict"] == "changed" and not c["field_diffs"]: issues.append(f"{c['testcase_id']} changed 但無 field_diffs")
    return issues

def g_reg(run, task, arts) -> list[str]:
    rp = arts.get("RegressionProposal")
    if not rp: return ["缺 RegressionProposal"]
    p = _payload(rp); issues = []; seen = set()
    for m in p["proposed_memberships"]:
        tid = m["testcase_id"]
        if tid in seen: issues.append(f"重複 membership {tid}")
        seen.add(tid)
        if not store.exists(store.tc_pointer_path(tid)): issues.append(f"{tid} 不在 Registry"); continue
        ptr = store.load(store.tc_pointer_path(tid))
        if ptr["status"] != "ACTIVE" or ptr["active_version"] is None: issues.append(f"{tid} 非 ACTIVE"); continue
        ver = ptr["active_version"] if m["pinned_version"] == "active" else m["pinned_version"]
        if not store.exists(store.tc_version_path(tid, ver)): issues.append(f"{tid} v{ver} 不存在"); continue
        tc = store.load(store.tc_version_path(tid, ver))
        if tc["status"] not in ("ACTIVE", "SUPERSEDED") and m["pinned_version"] != "active": issues.append(f"{tid} v{ver} 狀態 {tc['status']}")
        if p["suite_type"] == "ci_regression":
            if tc["execution_mode"] == "manual": issues.append(f"{tid} 為 manual，不得進 CI suite")
            if not tc["ci_eligible"]: issues.append(f"{tid} ci_eligible=false")
        if p["suite_type"] == "hotfix" and not tc["hotfix_eligible"]: issues.append(f"{tid} hotfix_eligible=false")
        if not m["justification"].strip() or not m["risk_tag"].strip(): issues.append(f"{tid} 缺 justification / risk_tag")
    return issues

GATES = {"G-SPEC": g_spec, "G-DESIGN": g_design, "G-TVAL": g_tval, "G-BVAL": g_bval, "G-IMPACT": g_impact, "G-COMPARE": g_compare, "G-REG": g_reg}

def semantic_result(gate: str, arts) -> str | None:
    """Semantic 層：從 Validator artifact 讀 result；非 validator gate 回 None（= 只有 structural）。"""
    if gate == "G-TVAL" and "TestValidationReport" in arts: return arts["TestValidationReport"]["payload"]["result"]
    if gate == "G-BVAL" and "BugValidationReport" in arts: return arts["BugValidationReport"]["payload"]["result"]
    return None
