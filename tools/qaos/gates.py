"""Quality Gate 的 Structural 檢查（deterministic）。每個函式回傳 issues list；空 = PASS。"""
import hashlib, json
from . import store, refs, rm, dispatch, decisions, sources, spec_ops

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
    if issues: return issues
    ctx, more = spec_context(run, task, arts)
    if ctx is None: return issues + more
    issues += more
    for r in p["requirements"]:
        for i, ref in enumerate(r.get("source_refs") or []):                          # 需求層的有型別依據（第 3 章 §6.3；附錄 A 3-26）
            if not isinstance(ref, dict) or ref.get("type") != "spec":
                issues.append(f"X10：{r['requirement_id']} source_refs[{i}] 只接受 spec 型；clarification、approval 型請放在決策點的 known_rules 或 resolution"); continue
            errs, _ = sources.validate(ref, target=ctx.target)
            issues += [f"X10：{r['requirement_id']} source_refs[{i}]：{e}" for e in errs]
        issues += decisions.check(r, ctx)[0]
    return issues

def spec_context(run, task, arts):
    """G-SPEC 的派發包檢查（第 1 章 §2.7 第 1～3 點）；回傳 (decisions.Ctx 或 None, issues)。"""
    rm_art, sa = arts["RequirementModel"], arts.get("SpecAnalysis"); p = _payload(rm_art); issues = []
    e = dispatch.current_entry(task)
    if e is None: return None, [f"{task['task_id']} iteration {task['iteration']} 沒有派發包"]
    try: packet = dispatch.load_packet(e)
    except dispatch.DispatchError as ex: return None, [str(ex)]
    for a in (sa, rm_art):
        if a is not None and a.get("dispatch_packet_sha256") != e["sha256"]:
            issues.append(f"{a['artifact_type']} 的 dispatch_packet_sha256 不是本 task iteration {task['iteration']} 的派發包")
    tgt = packet.get("target")
    if not tgt or (tgt["spec_id"], str(tgt["spec_version"])) != (p["spec_id"], str(p["spec_version"])):
        return None, issues + [f"派發包的目標不是 {p['spec_id']}@{p['spec_version']}"]
    try: now = sources.basis_hash(sources.basis(p["spec_id"], p["spec_version"]))
    except (spec_ops.SpecError, sources.SourceError) as ex: return None, issues + [f"目標 {p['spec_id']}@{p['spec_version']}：{ex}"]
    if now != packet["basis_hash"]:
        issues.append("派發包之後目標或引用閉包的宣告已改變（basis_hash 不同）；同一 iteration 不能重新派發，請取消此 run 後重新分析")
    # 1. consulted_sources 的 hash：派發包、spec.yaml 登記值、實體檔都要相符
    allowed = {decisions._pk(tgt)} | {decisions._pk(n) for n in packet["closure"]} | {decisions._pk(x["pin"]) for x in packet["extra_inputs"] if x["kind"] == "spec_pin"}
    consulted = (_payload(sa).get("consulted_sources") if sa else None)
    if consulted is None: issues.append("SpecAnalysis 缺 consulted_sources（申報實際查閱的來源）")
    for c in consulted or []:
        k = decisions._pk(c)
        if k not in allowed: issues.append(f"consulted_sources 的 {c['spec_id']}@{c['spec_version']} hash 和派發包不符（或不在派發包內）"); continue
        try: spec_ops.verify_pin(c["spec_id"], c["spec_version"], c["content_hash"])
        except spec_ops.SpecError as ex: issues.append(f"consulted_sources 的 {c['spec_id']}@{c['spec_version']}：{ex}")
    # 2. depth=1 的 normative 參考沒有查閱 → 必須列在相關決策點的 unconsulted_normative
    seen = {decisions._pk(c) for c in consulted or []}
    listed = {decisions._pk(u["pin"]) for r in p["requirements"] for dp in r.get("decision_points") or [] for u in dp["coverage"]["unconsulted_normative"]}
    for n in packet["closure"]:
        if n.get("required") and decisions._pk(n) not in seen and decisions._pk(n) not in listed:
            issues.append(f"必讀參考 {n['spec_id']}@{n['spec_version']}（depth=1 normative）沒有查閱，也沒有列在任何決策點的 unconsulted_normative")
    return decisions.Ctx.from_packet(packet), issues

def _pinned(run, spec_id, spec_version, end="target"):
    """run 綁定的 revision（第 5 章 §4.1；不讀可變的檢視）；和本次 artifact 的 spec 版本不符 → 錯誤。回傳 (RMPin, {requirement_id: requirement}) 或 (None, 錯誤訊息)。"""
    try: pin = rm.run_pin(run, end)
    except rm.RMError as e: return None, str(e)
    if (pin["spec_id"], pin["spec_version"]) != (spec_id, str(spec_version)):
        return None, f"artifact 的 {spec_id}@{spec_version} 和 run 綁定的 {pin['spec_id']}@{pin['spec_version']} {pin['revision']} 不符"
    return pin, rm.requirements_of(pin)

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
    e = dispatch.current_entry(task) if task is not None else None
    packet = dispatch.load_packet(e) if e is not None else None
    _, reqs = _pinned(run, p["spec_id"], p["spec_version"])
    if isinstance(reqs, str): return [reqs]
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
            # 已由核准解決的假設（resolved_by_approval，常見於 change 模式沿用現行版）不必再標需人工確認；否則必須外顯
            if a.get("needs_human_confirmation") is not True and not a.get("resolved_by_approval"):
                issues.append(f"{did} 的 assumption 未標 needs_human_confirmation: true（exploratory 案例的假設必須外顯；已核准者請填 resolved_by_approval）")
            if a["requirement_id"] not in tc["requirement_ids"]: issues.append(f"{did} 的 assumption 指向非本 TC 的 requirement {a['requirement_id']}")
        issues += _decision_ref_issues(tc, reqs)
        issues += source_ref_issues(tc, (p["spec_id"], str(p["spec_version"])), packet)
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
        if rc and rc.get("defined") is False and not decisions.is_new(r):         # 新資料改逐決策點限制（_decision_ref_issues）
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

def _confirmed_assumption(tc, rid) -> bool:
    return any(a.get("requirement_id") == rid and a.get("needs_human_confirmation") is True for a in tc.get("assumptions") or [])

def usable_sources(dp) -> list:
    """E1 決策點可以作為依據的來源身分：known_rules（basis 為 undefined 時除外）、resolution.source、adopted_side_index 指定的一側（§3.6）。"""
    kr = [dispatch.basis_ref(x) for x in dp.get("known_rules") or []]
    sides = [dispatch.basis_ref(x) for x in dp.get("conflict_sides") or []]
    res = dp.get("resolution") or {}
    allowed = ([] if dp["basis"] == "undefined" else kr) + ([dispatch.basis_ref(res["source"])] if res.get("source") else [])
    idx = res.get("adopted_side_index")
    if dp["basis"] == "conflict" and decisions.is_index(idx) and idx < len(sides): allowed.append(sides[idx])
    return allowed

def find_dp(reqs, rid, qid):
    return next((x for x in (reqs.get(rid) or {}).get("decision_points") or [] if x["question_id"] == qid), None)

def _decision_ref_issues(tc, reqs) -> list[str]:
    """G-DESIGN 逐決策點限制（第 1 章 §3.6）：依決策點的有效狀態限制依賴它的斷言；只作用在依賴該決策點的斷言。"""
    did = tc["draft_id"]; out = []; drefs = tc.get("decision_refs") or []
    new_reqs = [rid for rid in tc["requirement_ids"] if rid in reqs and decisions.is_new(reqs[rid])]
    for rid in new_reqs:                                                    # §3.6 第 1 點：expected 依據與 negative／error_guessing 斷言都要標明依賴的決策點
        if not any(r["requirement_id"] == rid for r in drefs):
            out.append(f"{did}：{rid} 有決策點，TC 的 expected 依據必須以 decision_refs 標明依賴的決策點")
    for ref in drefs:
        rid, qid, br = ref["requirement_id"], ref["question_id"], ref["basis_ref"]
        bad_idx = [k for k in ("answer_rev", "resolution_index") if br is not None and k in br and not decisions.is_index(br[k])]
        if bad_idx: out.append(f"{did} 的 decision_refs {rid}/{qid}：basis_ref 的 {', '.join(bad_idx)} 必須是整數表示"); continue
        if rid not in tc["requirement_ids"]: out.append(f"{did} 的 decision_refs 指向非本 TC 的 requirement {rid}"); continue
        r = reqs.get(rid); dp = next((x for x in (r or {}).get("decision_points") or [] if x["question_id"] == qid), None)
        if dp is None: out.append(f"{did} 的 decision_refs 指向不存在的決策點 {rid}/{qid}"); continue
        d = dp["derived"]; st = d["state"]; tag = f"{did} 依賴 {rid}/{qid}（{st} {d['effective_level']}）"
        if d["route"] in decisions.DRAFT_ROUTES: out.append(f"{tag}：critical 的未決事項禁止設計 TC"); continue
        kr = [dispatch.basis_ref(x) for x in dp.get("known_rules") or []]
        sides = [dispatch.basis_ref(x) for x in dp.get("conflict_sides") or []]
        res = dp.get("resolution") or {}; src = dispatch.basis_ref(res["source"]) if res.get("source") else None
        if br is not None and dp["basis"] == "undefined" and br in kr and br != src:
            out.append(f"{tag}：basis 為 undefined 的 known_rules 只是背景，不能作為 expected 依據（附錄 A 1-7）"); continue
        if st == "E1":
            allowed = usable_sources(dp)
            if br is None: out.append(f"{tag}：已定的決策點，斷言必須標明 basis_ref")
            elif br not in allowed:
                out.append(f"{tag}：引用了未被採用的衝突一側" if br in sides else f"{tag}：basis_ref 不是該決策點的 known_rules、resolution 或被採用的一側")
        elif st == "E2":
            if br is not None and br in sides: out.append(f"{tag}：衝突未決，不能引用該決策點的 conflict_sides")
        elif not _confirmed_assumption(tc, rid):
            out.append(f"{tag}：依賴的斷言只能 exploratory（assumptions 標 needs_human_confirmation: true）")
    return out

def source_ref_issues(tc, target, packet=None) -> list[str]:
    """TC 的 source_refs 逐筆以共用驗證核對（hash、quote、答案修訂、核准條目；第 3 章 §6）。派發時登記的額外 spec 不受「目標或閉包內」限制，
    只核對 hash 與 quote（附錄 A 1-38）。clarification、approval 型必須是本 TC 某筆 decision_refs 的 basis_ref，並以那個決策點作為引用處驗證
    （核准條目的 requirement／question 必須相符；該 basis_ref 是否為決策點可用的來源由 _decision_ref_issues 核對）。範圍是否在派發包內由 G-TVAL 判定。"""
    extras = {decisions._pk(x["pin"]) for x in (packet or {}).get("extra_inputs") or [] if x["kind"] == "spec_pin"}
    out = []
    for i, r in enumerate(tc.get("source_refs") or []):
        tag = f"{tc['draft_id']} 的 source_refs[{i}]"
        if isinstance(r, dict) and r.get("type") in ("clarification", "approval"):
            try: ident = dispatch.basis_ref(r)
            except (KeyError, TypeError): ident = None
            ats = sorted({(d["requirement_id"], d["question_id"]) for d in tc.get("decision_refs") or [] if ident is not None and d.get("basis_ref") == ident})
            if not ats:
                out.append(f"{tag}：{r['type']} 型來源必須對應本 TC 的某筆 decision_refs（basis_ref 相同），以決策點作為引用處（附錄 A 1-38）"); continue
            for at in ats:
                errs, _ = sources.validate(r, target=target, at=at)
                out += [f"{tag}（引用處 {at[0]}/{at[1]}）：{e}" for e in errs]
            continue
        tgt = None if (isinstance(r, dict) and r.get("type") == "spec" and r.get("content_hash") and decisions._pk(r) in extras) else target
        errs, _ = sources.validate(r, target=tgt)
        out += [f"{tag}：{e}" for e in errs]
    return out

def draft_out_of_scope(draft_payload, packet) -> dict:
    """Draft 用到、但不在派發包範圍內的 SourceRef（第 1 章 §2.6）：{draft_id: [身分]}。"""
    out = {}
    for tc in draft_payload["testcases"]:
        refs_ = list(tc.get("source_refs") or []) + [r["basis_ref"] for r in tc.get("decision_refs") or [] if r.get("basis_ref")]
        bad = [dispatch.basis_ref(r) for r in refs_ if not dispatch.in_scope(packet, r)]
        if bad: out[tc["draft_id"]] = bad
    return out

_DRAFT_PRODUCER = {"TestCaseDraft": "agent-test-designer", "BugDraft": "agent-bug-analyst"}

def reviewed_draft_issues(run, task, art_type, draft_id) -> list[str]:
    """Validator 報告審查的 Draft 必須是產生者 task 本輪 output_artifact_ids 中、狀態 VALID 的那份（附錄 A 6-36）。
    人 reject 後重做會清空產生者的本輪產出、但不把舊稿改成 SUPERSEDED；Validator 語意 FAIL 退回則保留清單、把舊稿改成 SUPERSEDED。
    報告指向舊稿（或別的 artifact）時，正式 TC／Bug 與落地判定所看的 Draft 會不一致，所以 Structural FAIL。
    task 為 None：函式層直接呼叫，沒有 run 的輪次可核對。"""
    if task is None: return []
    gen = next((t for t in run.get("tasks") or [] if t.get("agent_id") == _DRAFT_PRODUCER[art_type]), None)
    if gen is None: return [f"run 沒有產生 {art_type} 的 task（{_DRAFT_PRODUCER[art_type]}）"]
    current = gen.get("output_artifact_ids") or []
    if draft_id not in current:
        return [f"報告審查的 {draft_id} 不是 {gen['task_id']} 本輪的產出（本輪產出：{', '.join(current) or '無'}）"]
    path = store.find_artifact(draft_id); a = store.load(path) if path else None
    if not a or a["artifact_type"] != art_type: return [f"報告審查的 {draft_id} 不是 {art_type}"]
    if a["status"] != "VALID": return [f"報告審查的 {draft_id} 狀態是 {a['status']}，不是本輪有效的 Draft"]
    return []

def g_tval(run, task, arts) -> list[str]:
    rep = arts.get("TestValidationReport")
    if not rep: return ["缺 TestValidationReport"]
    p = _payload(rep); issues = []
    draft = store.find_artifact(p["testcase_draft_artifact_id"])
    if not draft: return [f"報告指向的 draft {p['testcase_draft_artifact_id']} 不存在"]
    stale = reviewed_draft_issues(run, task, "TestCaseDraft", p["testcase_draft_artifact_id"])
    if stale: return stale
    did_set = {tc["draft_id"] for tc in store.load(draft)["payload"]["testcases"]}
    if p["result"] == "FAIL" and not p["issues"]: issues.append("FAIL 但 issues 為空")
    for i in p["issues"] + p["advisories"]:
        if i["testcase_id"] not in did_set and i["testcase_id"] != "*": issues.append(f"issue 指向不存在的 draft {i['testcase_id']}")
    if p["result"] == "PASS" and any(i["severity"] in ("blocker", "major") for i in p["issues"]):
        issues.append("PASS 但含 blocker/major issue")
    # 派發包範圍（AC-04-4）：Draft 用到範圍外的來源時，Validator 必須以 missing_reference（blocker／major）回報
    e = dispatch.current_entry(task) if task is not None else None     # task 為 None：函式層直接呼叫，沒有派發包可核對
    if e is not None:
        try: packet = dispatch.load_packet(e)
        except dispatch.DispatchError as ex: return issues + [str(ex)]
        for did, bad in draft_out_of_scope(store.load(draft)["payload"], packet).items():
            if not any(i["issue_type"] == "missing_reference" and i["testcase_id"] in (did, "*") and i["severity"] in ("blocker", "major") for i in p["issues"]):
                issues.append(f"{did} 用到派發包範圍外的來源 {bad}，Validator 沒有以 missing_reference 回報")
    return issues

def _bugdraft_source_issues(run, p, reqs) -> list[str]:
    """BugDraft 的明確 SourceRef（第一批選填）：共用驗證；clarification、approval 型必須對應 decision_refs 的決策點，並通過 X16。"""
    did = p["draft_id"]; out = source_ref_issues({"draft_id": did, "source_refs": p.get("source_refs"), "decision_refs": p.get("decision_refs")}, (p["spec_id"], str(p["spec_version"])))
    for d in p.get("decision_refs") or []:
        if d["requirement_id"] != p["requirement_id"]: out.append(f"{did} 的 decision_refs 指向非本 bug 的 requirement {d['requirement_id']}"); continue
        dp = find_dp(reqs, d["requirement_id"], d["question_id"])
        if dp is None: out.append(f"{did} 的 decision_refs 指向不存在的決策點 {d['requirement_id']}/{d['question_id']}"); continue
        for r in p.get("source_refs") or []:
            if r.get("type") in ("clarification", "approval") and dispatch.basis_ref(r) == d.get("basis_ref"):
                scope = {"spec_id": p["spec_id"], "requirement_id": d["requirement_id"], "subject": dp["subject"], "role_scope": dp["role_scope"], "params": dp["params"]}
                out += [f"{did}：{m}" for m in sources.x16(r, scope, dp.get("basis_hash"), at=(d["requirement_id"], d["question_id"]))]
    return out

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
        pin, reqs = _pinned(run, p["spec_id"], p["spec_version"])
        if pin is None: issues.append(reqs)
        elif p["requirement_id"] not in reqs: issues.append(f"requirement {p['requirement_id']} 不在 {p['spec_id']}@{p['spec_version']} {pin['revision']}")
        if not p["reproduction_steps"]: issues.append("reproduction_steps 為空")
        if p.get("source_refs") or p.get("decision_refs"): issues += _bugdraft_source_issues(run, p, reqs if pin is not None else {})
    if rep:
        p = _payload(rep)
        issues += reviewed_draft_issues(run, task, "BugDraft", p["bug_draft_artifact_id"])
        if p["result"] == "FAIL" and not p["issues"]: issues.append("FAIL 但 issues 為空")
        if p["result"] == "PASS":
            for ev in p["evidence_verification"]:
                if not (ev["hash_verified"] and ev["supports_claim"]): issues.append(f"PASS 但 evidence {ev['evidence_id']} 未通過驗證")
            if not all(p["checks"].values()): issues.append("PASS 但 checks 有 false")
        if p["result"] == "DUPLICATE" and not p["duplicate_check"]["duplicate_of"]: issues.append("DUPLICATE 但無 duplicate_of")
    return issues

def _cia_candidates(spec_id) -> tuple[dict, list[str]]:
    """候選 C：spec_id 等於 CIR、狀態 ACTIVE 的全部 TC（不論 spec_version、revision），各自依 §4.1 解析 pin。回傳 ({tc_id: RMPin}, 錯誤)。"""
    out, errs = {}, []
    for ptr in store.glob("testcases/registry/TC-*.yaml"):
        d = store.load(ptr)
        if d.get("status") != "ACTIVE" or d.get("active_version") is None: continue
        v = store.load(store.tc_version_path(d["testcase_id"], d["active_version"]))
        if v["spec_id"] != spec_id: continue
        try: out[d["testcase_id"]] = rm.tc_pin(d["testcase_id"], d["active_version"])
        except rm.RMError as e: errs.append(str(e))
    return out, errs

def g_impact(run, task, arts) -> list[str]:
    """CIA 候選完整性與 pin_groups 的恰好分割（需求 A 第 5 章 §9，G1～G8）；依 revision 讀需求，不讀檢視。"""
    cir = arts.get("ChangeImpactReport")
    if not cir: return ["缺 ChangeImpactReport"]
    p = _payload(cir); issues = []
    for v in (p["from_version"], p["to_version"]):
        err = refs.resolve({"entity_type": "SpecVersion", "id": p["spec_id"], "version": v})
        if err: issues.append(err)
    to_pin, to_reqs = _pinned(run, p["spec_id"], p["to_version"])
    if to_pin is None: return issues + [to_reqs]
    if p["to_rm_revision"] != to_pin: issues.append(f"to_rm_revision 不是 run 綁定的 {to_pin['revision']}")
    from_pin, from_reqs = _pinned(run, p["spec_id"], p["from_version"], end="from")   # run 欄位 → run sidecar
    if from_pin is None:
        if rm.latest_pin(p["spec_id"], p["from_version"]) is not None: return issues + [from_reqs]   # from 端有需求模型，run 卻沒有綁定 → 錯誤
        from_reqs = {}                                                                             # from 端本來就沒有需求模型
    elif p["from_rm_revision"] != from_pin: issues.append(f"from_rm_revision 不是 run 綁定的 {from_pin['revision']}")
    judged = {d["requirement_id"] for d in p["requirement_diff"]}
    for rid in set(from_reqs) | set(to_reqs):
        if rid not in judged: issues.append(f"requirement {rid} 未出現在 requirement_diff")
    # 候選與分組（G1～G8）
    cand, errs = _cia_candidates(p["spec_id"]); issues += errs
    C = set(cand); groups = p["pin_groups"]; I = [t["testcase_id"] for t in p["testcase_impact"]]
    member_of = {}
    for k, g in enumerate(groups):
        ids_ = g["testcase_ids"]
        if not ids_ or len(ids_) != len(set(ids_)): issues.append(f"G1：pin_groups[{k}] 是空組或組內有重複")
        for t in ids_: member_of.setdefault(t, []).append(k)
    all_ids = [t for g in groups for t in g["testcase_ids"]]
    if set(all_ids) != C or len(all_ids) != len(C):
        issues.append(f"G2：pin_groups 不是候選的恰好分割（缺 {sorted(C - set(all_ids))}、多 {sorted(set(all_ids) - C)}、重複 {sorted(t for t in member_of if len(member_of[t]) > 1)}）")
    pins = [json.dumps(g["from_pin"], sort_keys=True) for g in groups]
    if len(pins) != len(set(pins)): issues.append("G3：pin_groups 的 from_pin 有重複")
    for k, g in enumerate(groups):
        for t in g["testcase_ids"]:
            if t in cand and cand[t] != g["from_pin"]: issues.append(f"G4：{t} 自己的 pin 是 {cand[t]['revision']}，不是 pin_groups[{k}] 的 {g['from_pin']['revision']}")
    if set(I) != C or len(I) != len(C):
        issues.append(f"G5：testcase_impact 必須恰好等於候選（缺 {sorted(C - set(I))}、未知 {sorted(set(I) - C)}、重複 {sorted({t for t in I if I.count(t) > 1})}）")
    for t in p["testcase_impact"]:
        k = t.get("pin_group_index")
        if t["testcase_id"] in member_of and (k is None or member_of[t["testcase_id"]] != [k]):
            issues.append(f"G6：{t['testcase_id']} 的 pin_group_index {k} 不等於所屬組 {member_of[t['testcase_id']]}")
    for k, g in enumerate(groups):
        try: rm.verify_pin(g["from_pin"]); g_from = rm.requirements_of(g["from_pin"])
        except rm.RMError as e: issues.append(f"G8：pin_groups[{k}] 的 from_pin 無法解析：{e}"); continue
        rids = [d["requirement_id"] for d in g["requirement_diff"]]
        if sorted(rids) != sorted(set(g_from) | set(to_reqs)) or len(rids) != len(set(rids)):
            issues.append(f"G7：pin_groups[{k}] 的 requirement_diff 必須恰好涵蓋 {g['from_pin']['revision']} 與 {to_pin['revision']} 的需求各一次")
    if not (p["completeness"]["all_active_requirements_judged"] and p["completeness"]["all_referencing_testcases_judged"]):
        issues.append("completeness 自我宣告未通過")
    return issues

def _run_output(run, before_task, art_type):
    """before_task 之前、各 task 本輪 output_artifact_ids 中最後一份 VALID 的 art_type。"""
    ids_ = [t["task_id"] for t in run["tasks"]]; found = None
    for t in run["tasks"][:ids_.index(before_task["task_id"])]:
        for aid in t.get("output_artifact_ids") or []:
            path = store.find_artifact(aid); a = store.load(path) if path else None
            if a and a["artifact_type"] == art_type and a["status"] == "VALID": found = a
    return found

def _compare_coverage_issues(run, task, p) -> list[str]:
    """比較報告的對象與集合（docs/architecture/04-quality-gates.md G-COMPARE；P6-C01-01）：以本 run 本輪有效的 CIR 與 G-TVAL 審過的 Draft 機械核對——
    CIR 中 affected／obsolete 的 TC 各恰好比較一次且 old_version 等於 active_version；new_draft_id 必須屬於 G-TVAL 審過的 Draft，且該 Draft 的每張 TC 恰好比較一次；
    有 supersedes_testcase 的 TC 必須對到它取代的 TC 與版本，沒有的必須是 added。只核對身分與集合，不判斷 diff 的語意。"""
    cir, rep = _run_output(run, task, "ChangeImpactReport"), _run_output(run, task, "TestValidationReport")
    if cir is None: return ["本 run 沒有本輪有效的 ChangeImpactReport，無法核對比較範圍"]
    if rep is None: return ["本 run 沒有本輪有效的 TestValidationReport，無法核對比較的 Draft"]
    issues = []; cp = cir["payload"]
    if p["change_impact_id"] != cp["change_impact_id"]: issues.append(f"change_impact_id {p['change_impact_id']} 不是本 run 的 {cp['change_impact_id']}")
    draft_path = store.find_artifact(rep["payload"]["testcase_draft_artifact_id"])
    drafts = {tc["draft_id"]: tc for tc in store.load(draft_path)["payload"]["testcases"]} if draft_path else {}
    impacted = {t["testcase_id"]: t["active_version"] for t in cp["testcase_impact"] if t["impact"] in ("affected", "obsolete")}
    by_tc, by_draft = {}, {}
    for c in p["comparisons"]:
        if c["testcase_id"] is not None: by_tc.setdefault(c["testcase_id"], []).append(c)
        if c["new_draft_id"] is not None: by_draft.setdefault(c["new_draft_id"], []).append(c)
    for tc_id, ver in sorted(impacted.items()):
        cs = by_tc.get(tc_id) or []
        if len(cs) != 1: issues.append(f"{tc_id}（CIR 判定 affected／obsolete）應恰好比較一次，實際 {len(cs)} 次"); continue
        if cs[0]["old_version"] != ver: issues.append(f"{tc_id} 的 old_version {cs[0]['old_version']} 不是 CIR 的 active_version {ver}")
    for d in sorted(by_draft):
        if d not in drafts: issues.append(f"new_draft_id {d} 不屬於 G-TVAL 審過的本輪 Draft {rep['payload']['testcase_draft_artifact_id']}")
    for d, tc in sorted(drafts.items()):
        cs = by_draft.get(d) or []
        if len(cs) != 1: issues.append(f"本輪 Draft 的 {d} 應恰好比較一次，實際 {len(cs)} 次"); continue
        sup = tc.get("supersedes_testcase"); c = cs[0]
        if sup and (c["testcase_id"], c["old_version"]) != (sup["testcase_id"], sup["version"]):
            issues.append(f"{d} 取代 {sup['testcase_id']} v{sup['version']}，比較卻對到 {c['testcase_id']} v{c['old_version']}")
        if not sup and c["verdict"] != "added": issues.append(f"{d} 是新 TC，verdict 應為 added（實際 {c['verdict']}）")
    for tc_id in sorted(set(by_tc) - set(impacted)):
        if not any((tc.get("supersedes_testcase") or {}).get("testcase_id") == tc_id for tc in drafts.values()):
            issues.append(f"{tc_id} 不在 CIR 的 affected／obsolete，也沒有本輪 Draft 取代它")
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
    if task is not None: issues += _compare_coverage_issues(run, task, p)        # task 為 None：函式層直接呼叫，沒有 run 的輪次可核對
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

RISK_DIMENSIONS = ("boundary", "exception_flow", "concurrency", "duplicate_submission", "permission")

def g_risk(run, task, arts) -> list[str]:
    """ADR-009：高風險抽查只檢查結構一致性（審的是本 run Validator PASS 的 draft、五面向齊全、建議可追溯）；
    建議內容不擋關，由 Human 在 ACTIVATE／APPLY_CHANGE 核准單上判斷。"""
    rr = arts.get("TCRiskReview")
    if not rr: return ["缺 TCRiskReview"]
    e = dispatch.current_entry(task) if task is not None else None
    rr_packet = dispatch.load_packet(e) if e is not None else None
    p = _payload(rr); rv = p["reviewed"]; issues = []
    ids_ = [t["task_id"] for t in run["tasks"]]
    vt = next((t for t in reversed(run["tasks"][:ids_.index(task["task_id"])]) if t.get("agent_id") == "agent-test-validator"), None)
    tvr = None
    for aid in reversed(vt["output_artifact_ids"] if vt else []):
        ap = store.find_artifact(aid)
        a = store.load(ap) if ap else None
        if a and a["artifact_type"] == "TestValidationReport" and a["status"] == "VALID": tvr = a; break
    if not tvr: return ["找不到本 run Validator 的 VALID TestValidationReport"]
    if rv["validation_report_artifact_id"] != tvr["artifact_id"]: issues.append(f"reviewed.validation_report_artifact_id 應為 {tvr['artifact_id']}")
    if rv["testcase_draft_artifact_id"] != tvr["payload"]["testcase_draft_artifact_id"]: issues.append(f"reviewed.testcase_draft_artifact_id 應為 {tvr['payload']['testcase_draft_artifact_id']}（Validator 審過的那份）")
    dp = store.find_artifact(tvr["payload"]["testcase_draft_artifact_id"])
    draft = store.load(dp)["payload"] if dp else {"testcases": []}
    did_set = {tc["draft_id"] for tc in draft["testcases"]}
    # spec 綁定以 Validator 審過的 draft 為準；run 有指定 spec／目標版本時也必須一致（避免用舊版 requirement 支撐新版抽查）
    if (rv["spec_id"], rv["spec_version"]) != (draft.get("spec_id"), draft.get("spec_version")):
        issues.append(f"reviewed spec {rv['spec_id']}@{rv['spec_version']} 與 Validator 審過的 draft {draft.get('spec_id')}@{draft.get('spec_version')} 不符")
    inp = run["input"]; want_ver = inp.get("to_version") or inp.get("spec_version")
    if inp.get("spec_id") and rv["spec_id"] != inp["spec_id"]: issues.append(f"reviewed.spec_id {rv['spec_id']} 與 run 的 {inp['spec_id']} 不符")
    if want_ver and rv["spec_version"] != want_ver: issues.append(f"reviewed.spec_version {rv['spec_version']} 與 run 的目標版本 {want_ver} 不符")
    area = store.run_area(inp)
    if rv["functional_area"] != area: issues.append(f"reviewed.functional_area {rv['functional_area']} 與本 run 的 area {area} 不符")
    if set(rv["testcase_draft_ids"]) != did_set:
        issues.append(f"testcase_draft_ids 必須恰為 draft 全部 TC（缺 {sorted(did_set - set(rv['testcase_draft_ids']))}，多 {sorted(set(rv['testcase_draft_ids']) - did_set)}）")
    dims = [d["dimension"] for d in p["dimension_results"]]
    if sorted(dims) != sorted(RISK_DIMENSIONS): issues.append(f"dimension_results 必須五個面向各一（實際 {dims}）")
    found = {f["dimension"] for f in p["findings"]}
    for d in p["dimension_results"]:
        if d["status"] == "gaps_found" and d["dimension"] not in found: issues.append(f"{d['dimension']} 標 gaps_found 但沒有對應 finding")
        if d["status"] != "gaps_found" and d["dimension"] in found: issues.append(f"{d['dimension']} 有 finding 但 status 為 {d['status']}")
    seen = set()
    for f in p["findings"]:
        if f["finding_id"] in seen: issues.append(f"finding_id {f['finding_id']} 重複")
        seen.add(f["finding_id"])
        sb = f["spec_basis"]
        if sb is not None and "type" in sb:                                  # 型別化 SourceRef（第 3 章 §6.3；附錄 A 1-40）
            issues += _rr_basis_issues(run, rv, f, sb)
            if rr_packet is not None and not dispatch.in_scope(rr_packet, sb):
                issues.append(f"{f['finding_id']} 的 spec_basis 不在本 task 派發包的範圍內")
        elif sb is not None and rr_packet is not None:
            issues.append(f"{f['finding_id']} 的 spec_basis 必須是型別化的 SourceRef（spec／clarification／approval）；舊的 {{location, quote}} 只保留給派發包之前的舊產出")
        elif sb is not None and not (sb["location"].strip() and sb["quote"].strip()):
            issues.append(f"{f['finding_id']} 的 spec_basis 只有空白；沒有依據請填 null 並標 needs_clarification")
        elif sb is None and not f["needs_clarification"]:
            issues.append(f"{f['finding_id']} 沒有 spec 依據卻未標 needs_clarification（不得自行寫出預期行為）")
        pin, reqs = _pinned(run, rv["spec_id"], rv["spec_version"])
        for rid in f["related_requirement_ids"]:
            if pin is None: issues.append(reqs); break
            if rid not in reqs: issues.append(f"{f['finding_id']} 引用的 {rid} 不在 {rv['spec_id']}@{rv['spec_version']} {pin['revision']}")
        for tid in f["related_testcase_ids"]:
            if tid in did_set: continue
            if not _active_tc_in_area(tid, rv["functional_area"]):
                issues.append(f"{f['finding_id']} 引用的 {tid} 既不是本次 draft，也不是同 area 的 ACTIVE TC")
    return issues

def _rr_basis_issues(run, rv, f, sb) -> list[str]:
    """RR finding 的型別化依據（附錄 A 1-40）：clarification、approval 型必須以 spec_basis_decision 指定引用處——
    需求在 finding 的關聯需求內、決策點存在且已定（E1）、依據是該決策點可用的來源；再以該引用處做共用驗證。spec 型只做共用驗證。"""
    fid = f["finding_id"]; target = (rv["spec_id"], str(rv["spec_version"])); at = None
    if sb["type"] in ("clarification", "approval"):
        sd = f.get("spec_basis_decision")
        if not sd: return [f"{fid}：{sb['type']} 型依據必須以 spec_basis_decision 指定對應的需求與決策點"]
        at = (sd["requirement_id"], sd["question_id"])
        if at[0] not in f["related_requirement_ids"]: return [f"{fid}：spec_basis_decision 的 {at[0]} 不在 related_requirement_ids"]
        pin, reqs = _pinned(run, *target)
        if pin is None: return [reqs]
        dp = find_dp(reqs, *at)
        if dp is None: return [f"{fid}：spec_basis_decision 指向不存在的決策點 {at[0]}/{at[1]}"]
        if dp["derived"]["state"] != "E1": return [f"{fid}：{at[0]}/{at[1]} 尚未定案（{dp['derived']['state']}），沒有可引用的裁決；請填 null 並標 needs_clarification"]
        try: ident = dispatch.basis_ref(sb)
        except (KeyError, TypeError): ident = None
        if ident not in usable_sources(dp): return [f"{fid}：spec_basis 不是 {at[0]}/{at[1]} 可用的依據（known_rules、resolution 或被採用的一側）"]
    elif f.get("spec_basis_decision"):
        sd = f["spec_basis_decision"]
        if sd["requirement_id"] not in f["related_requirement_ids"]: return [f"{fid}：spec_basis_decision 的 {sd['requirement_id']} 不在 related_requirement_ids"]
    errs, _ = sources.validate(sb, target=target, at=at)
    return [f"{fid} 的 spec_basis：{e}" for e in errs]

def _active_tc_in_area(tc_id, area) -> bool:
    """看 pointer 指向的 ACTIVE 版本本身：狀態 ACTIVE 且 functional_area 相符（不只看 ID 前綴）。"""
    if not store.exists(store.tc_pointer_path(tc_id)): return False
    ptr = store.load(store.tc_pointer_path(tc_id)); ver = ptr.get("active_version")
    if ptr.get("status") != "ACTIVE" or ver is None or not store.exists(store.tc_version_path(tc_id, ver)): return False
    v = store.load(store.tc_version_path(tc_id, ver))
    return v.get("status") == "ACTIVE" and v.get("functional_area") == area

GATES = {"G-SPEC": g_spec, "G-DESIGN": g_design, "G-TVAL": g_tval, "G-BVAL": g_bval, "G-IMPACT": g_impact, "G-COMPARE": g_compare, "G-REG": g_reg, "G-RISK": g_risk}

def semantic_result(gate: str, arts) -> str | None:
    """Semantic 層：從 Validator artifact 讀 result；非 validator gate 回 None（= 只有 structural）。"""
    if gate == "G-TVAL" and "TestValidationReport" in arts: return arts["TestValidationReport"]["payload"]["result"]
    if gate == "G-BVAL" and "BugValidationReport" in arts: return arts["BugValidationReport"]["payload"]["result"]
    return None
