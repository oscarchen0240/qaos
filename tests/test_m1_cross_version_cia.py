"""AC-09-31（需求 A 第 5 章 §8～§9：CIA 候選完整性與 pin_groups 的恰好分割 G1～G8）的跨版本隔離測試。

AC 原文：DAILYREPORT 現況的 fixture（0.1 的 48 條、0.2 的 48 條）做 0.2→0.3。預期：候選必須是 96 條、分兩組；只判 0.2 的 48 條 → FAIL。

與真實 DAILYREPORT 的對應（以小型 fixture 重現同樣的資料形狀，不必 48 條）：
- DAILYREPORT 0.1 ↔ SPEC-AUTH-001 v1.0；0.2 ↔ v1.1；0.3 ↔ v1.2（tests/fixtures/SPEC-AUTH-001-v1.2.md，測試用合成檔：以 v1.1 為底，
  只把 §3.2 R3 的鎖定時間由 15 分鐘改為 30 分鐘）。
- DAILYREPORT 的 96 條是需求 A 之前的程式產生的：0.1 的 spec-to-testcase 建立 TC，之後 0.1→0.2 的正式 CIA（RUN-20261001-007）
  讓受影響的 TC 改綁 0.2、其餘留在 0.1。本測試以相同方式產生：
  需求 A 之前的程式（base 2e01d4b，tests/p3_legacy.old_checkout 匯出的唯讀 checkout）以子程序在暫存 root 跑它自己的正式流程——
  v1.0 spec-to-testcase（5 張 TC）→ v1.0→v1.1 spec-change-impact（REQ-AUTH-001 8→12，2 張 affected 升 v2 綁 1.1、3 張留在 1.0）。
  所以 legacy 資料是「1.0 的 3 張 + 1.1 的 2 張」ACTIVE TC，兩個版本都有 legacy requirements.yaml、TC 版本檔都沒有 pin。
  舊流程使用 2e01d4b 自己的定義層（schemas／agents／workflows／permissions，因舊 CIR 沒有 pin_groups，過不了新 schema）；
  舊流程結束後把定義層換成新程式的版本（等同部署新程式），再 migrate。
- 新程式 `migrate` 後：兩個版本各自的 legacy RM 成為 R000；每張 TC 的 active 版本以 sidecar（legacy_binding: true）綁「自己 spec_version 的 R000」
  ——對應 DAILYREPORT 0.1 的 48 條綁 0.1 R000、0.2 的 48 條綁 0.2 R000。

之後以新程式的正式流程做 1.1→1.2（對應 0.2→0.3）：spec import v1.2 → `run new spec-change-impact`（from 1.1、to 1.2）
→ T0 Spec Analyst 產出 1.2 的 RM（G-SPEC PASS）→ T1 提交 CIR：
  (i) 反例：只判 1.1 那組（run 的 from 端，對應「只判 0.2 的 48 條」）→ G-IMPACT FAIL（G2、G5），T1 回 READY、run 仍 RUNNING；
  (ii) 正確 CIR：兩組（1.0 R000、1.1 R000）恰好分割全部候選 → PASS；並斷言 T1 派發包的 rm_pins.pin_groups 含這兩組。
agent 的產出（artifact 檔）由 tests/helpers.write_artifact 寫入（「外部寫入」，模擬 agent），其餘狀態一律走正式流程。"""
import json, os, pathlib, shutil, subprocess, sys, tempfile
import pytest
from tests import p1_util as U
from tests import p3_legacy as LG

# 需求 A 之前的程式（2e01d4b）在暫存 root 上以它自己的正式流程產生 1.0、1.1 兩個版本的 ACTIVE TC（沒有 pin）
OLD_FLOW = r"""
import json
from tools.qaos import engine, store
from tools.qaos.cli import main as cli
from tests import helpers as H
BY = "oscar@example.com"; SPEC = "SPEC-AUTH-001"
def ch(ver): return next(v for v in store.load(store.spec_dir(SPEC) / "spec.yaml")["versions"] if v["spec_version"] == ver)["content_hash"]
def analyze(rid, task, ver, rm):
    sa = {"spec_id": SPEC, "spec_version": ver, "content_hash": ch(ver), "summary": "s", "scope": {"in_scope": ["x"], "out_of_scope": []},
          "requirement_ids": [r["requirement_id"] for r in rm["requirements"]], "ambiguities": [], "constraints": [], "edge_case_candidates": [], "open_questions": []}
    refs_ = [{"entity_type": "SpecVersion", "id": SPEC, "version": ver}]
    _, p1 = H.write_artifact(rid, task, "agent-spec-analyst", "SpecAnalysis", sa, refs_, {"type": "SpecVersion", "ids": [f"{SPEC}@{ver}"]}, "spec-analysis")
    rmid, p2 = H.write_artifact(rid, task, "agent-spec-analyst", "RequirementModel", rm, refs_, {"type": "SpecVersion", "ids": [f"{SPEC}@{ver}"]}, "requirements")
    assert engine.submit(rid, task, str(p1))[0] and engine.submit(rid, task, str(p2))[0] and engine.evaluate_gate(rid, task)["result"] == "PASS"
    return rmid
def active():
    out = []
    for p in sorted((store.ROOT / "testcases/registry").glob("TC-*.yaml")):
        d = store.load(p)
        if d["status"] == "ACTIVE": out.append((d["testcase_id"], d["active_version"], store.load(store.tc_version_path(d["testcase_id"], d["active_version"]))))
    return out
# v1.0：spec-to-testcase，5 張 ACTIVE TC
cli(["spec", "import", "tests/fixtures/SPEC-AUTH-001-v1.0.md", "--spec-id", SPEC, "--version", "1.0", "--product", "demo", "--area", "AUTH", "--by", BY])
rid1 = engine.new_run("spec-to-testcase", {"spec_id": SPEC, "spec_version": "1.0"}, BY)["run_id"]
rmid1 = analyze(rid1, "T1", "1.0", H.requirement_model())
tcs, _ = H.draft_set(); refs2 = [{"entity_type": "Requirement", "id": r} for r in ["REQ-AUTH-001", "REQ-AUTH-002", "REQ-AUTH-003", "REQ-AUTH-004"]]
did, pd = H.write_artifact(rid1, "T2", "agent-test-designer", "TestCaseDraft", {"mode": "spec", "spec_id": SPEC, "spec_version": "1.0", "testcases": tcs}, refs2, {"type": "RequirementModel", "ids": [rmid1]}, "test-design")
_, pr = H.write_artifact(rid1, "T2", "agent-test-designer", "TestDesignReport", H.design_report(did, tcs), [{"entity_type": "Artifact", "id": did}], {"type": "TestCaseDraft", "ids": [did]}, "test-design")
assert engine.submit(rid1, "T2", str(pd))[0] and engine.submit(rid1, "T2", str(pr))[0] and engine.evaluate_gate(rid1, "T2")["result"] == "PASS"
_, pv = H.write_artifact(rid1, "T3", "agent-test-validator", "TestValidationReport", H.validation_report(did, rmid1, "PASS"),
                         [{"entity_type": "Artifact", "id": did}, {"entity_type": "Artifact", "id": rmid1}], {"type": "TestCaseDraft", "ids": [did]}, "validation")
assert engine.submit(rid1, "T3", str(pv))[0] and engine.evaluate_gate(rid1, "T3")["result"] == "PASS"
engine.approve(engine.load_run(rid1)["waiting_on_approval_id"], "approve", BY); assert engine.load_run(rid1)["status"] == "COMPLETED"
# v1.0 → v1.1：spec-change-impact（REQ-AUTH-001 8→12；2 張 affected 升 v2 綁 1.1，3 張留在 1.0）——對應 DAILYREPORT 0.1→0.2 的 RUN-20261001-007
cli(["spec", "import", "tests/fixtures/SPEC-AUTH-001-v1.1.md", "--spec-id", SPEC, "--version", "1.1", "--product", "demo", "--area", "AUTH", "--change-summary", "密碼最小長度 8 → 12", "--by", BY])
rid = engine.new_run("spec-change-impact", {"spec_id": SPEC, "from_version": "1.0", "to_version": "1.1"}, BY)["run_id"]
rmid = analyze(rid, "T0", "1.1", H.requirement_model("1.1", "12"))
act = active(); affected = [t for t in act if "REQ-AUTH-001" in t[2]["requirement_ids"]]; assert len(affected) == 2
cir = {"change_impact_id": "CI-SPEC-AUTH-001-1.0-1.1", "spec_id": SPEC, "from_version": "1.0", "to_version": "1.1",
       "requirement_diff": [{"requirement_id": "REQ-AUTH-001", "change": "changed", "detail": "8 → 12"}] + [{"requirement_id": r, "change": "unchanged"} for r in ["REQ-AUTH-002", "REQ-AUTH-003", "REQ-AUTH-004"]],
       "testcase_impact": [{"testcase_id": t[0], "active_version": t[1], "impact": "affected" if t in affected else "unaffected", "reason": "邊界值變更" if t in affected else "-",
                            "affected_requirement_ids": ["REQ-AUTH-001"] if t in affected else []} for t in act],
       "summary": {"requirements_changed": 1, "requirements_added": 0, "requirements_removed": 0, "testcases_affected": 2, "testcases_obsolete": 0, "testcases_unaffected": len(act) - 2},
       "completeness": {"all_active_requirements_judged": True, "all_referencing_testcases_judged": True}}
refs_ = [{"entity_type": "SpecVersion", "id": SPEC, "version": "1.1"}]
cid, p = H.write_artifact(rid, "T1", "agent-change-impact-analyst", "ChangeImpactReport", cir, refs_ + [{"entity_type": "TestCaseVersion", "id": t[0], "version": t[1]} for t in act], {"type": "SpecVersion", "ids": []}, "change-impact")
assert engine.submit(rid, "T1", str(p))[0] and engine.evaluate_gate(rid, "T1")["result"] == "PASS"
tcs2, _ = H.draft_set(12, prefix="01BX5ZZKBKACTAV9WEVGEMMVR"); new = []
for t, d in zip(affected, tcs2[:2]):
    d = dict(d, spec_version="1.1", source="change_workflow", supersedes_testcase={"testcase_id": t[0], "version": t[1]}); d["expected_result_spec_reference"]["spec_version"] = "1.1"; new.append(d)
did, pd = H.write_artifact(rid, "T2", "agent-test-designer", "TestCaseDraft", {"mode": "change", "spec_id": SPEC, "spec_version": "1.1", "change_impact_id": cir["change_impact_id"], "testcases": new},
                           [{"entity_type": "Requirement", "id": "REQ-AUTH-001"}, {"entity_type": "Artifact", "id": cid}], {"type": "ChangeImpactReport", "ids": [cid]}, "test-design")
rep = H.design_report(did, new); rep["mode"] = "change"
_, pr = H.write_artifact(rid, "T2", "agent-test-designer", "TestDesignReport", rep, [{"entity_type": "Artifact", "id": did}], {"type": "TestCaseDraft", "ids": [did]}, "test-design")
assert engine.submit(rid, "T2", str(pd))[0] and engine.submit(rid, "T2", str(pr))[0] and engine.evaluate_gate(rid, "T2")["result"] == "PASS"
_, pv = H.write_artifact(rid, "T3", "agent-test-validator", "TestValidationReport", H.validation_report(did, rmid, "PASS", spec_version="1.1"), [{"entity_type": "Artifact", "id": did}], {"type": "TestCaseDraft", "ids": [did]}, "validation")
assert engine.submit(rid, "T3", str(pv))[0] and engine.evaluate_gate(rid, "T3")["result"] == "PASS"
vcr = {"change_impact_id": cir["change_impact_id"], "comparisons": [{"testcase_id": t[0], "old_version": t[1], "new_draft_id": d["draft_id"], "verdict": "changed",
       "field_diffs": [{"field": "steps[0]", "old": "8", "new": "12"}], "impacted_requirement_ids": ["REQ-AUTH-001"]} for t, d in zip(affected, new)],
       "retire_recommendations": [], "summary": {"unchanged": 0, "changed": 2, "added": 0, "removed": 0}}
_, p = H.write_artifact(rid, "T4", "agent-change-impact-analyst", "VersionComparisonReport", vcr, [{"entity_type": "Artifact", "id": cid}], {"type": "ChangeImpactReport", "ids": [cid]}, "change-impact")
assert engine.submit(rid, "T4", str(p))[0] and engine.evaluate_gate(rid, "T4")["result"] == "PASS"
engine.approve(engine.load_run(rid)["waiting_on_approval_id"], "approve", BY); assert engine.load_run(rid)["status"] == "COMPLETED"
print(json.dumps({"by_version": {t: [v, d["spec_version"]] for t, v, d in active()},
                  "pinless": all("requirement_model_revision" not in d for _, _, d in active())}))
"""

DEFS = ("schemas", "agents", "workflows", "permissions")
OLD_DEFS = pathlib.Path(tempfile.gettempdir()) / f"qaos-base-{LG.BASE}-defs"

def _old_defs() -> pathlib.Path:
    """2e01d4b 的定義層（git archive 匯出到系統暫存目錄，唯讀；與 p3_legacy.old_checkout 同樣以快取目錄重用）。"""
    if not all((OLD_DEFS / d).is_dir() for d in DEFS):
        OLD_DEFS.mkdir(parents=True, exist_ok=True)
        data = subprocess.run(["git", "-C", str(U.REPO), "archive", LG.BASE, *DEFS], capture_output=True, check=True).stdout
        subprocess.run(["tar", "-x", "-C", str(OLD_DEFS)], input=data, check=True)
    return OLD_DEFS

def legacy_two_versions():
    """S_pre：舊程式以正式流程產生 1.0、1.1 兩個版本的 ACTIVE TC（沒有 pin）。回傳 (root, {tc_id: [active_version, spec_version]}, pinless)。
    舊程式的 CIA 要用它自己那一版的定義層（新 schema 要求 pin_groups 等欄位，舊程式產不出來），所以 root 先放 2e01d4b 的
    schemas／agents／workflows／permissions（git archive 匯出，唯讀來源）；舊流程跑完後換成新程式的定義層——等同部署新程式，之後才 migrate。"""
    old = LG.old_checkout(); old_defs = _old_defs()
    root = pathlib.Path(tempfile.mkdtemp(prefix="qaos-m1cv-")).resolve()
    for d in DEFS: shutil.copytree(old_defs / d, root / d)
    env = {**os.environ, "QAOS_ROOT": str(root), "PYTHONDONTWRITEBYTECODE": "1"}
    r = subprocess.run([sys.executable, "-c", OLD_FLOW], cwd=old, env=env, capture_output=True, text=True, timeout=300)
    if r.returncode != 0: raise AssertionError(f"舊程式的 legacy 流程失敗：\n{r.stdout}\n{r.stderr}")
    out = json.loads(r.stdout.strip().splitlines()[-1])
    for d in DEFS:                                                      # 部署新程式：定義層換成新版
        shutil.rmtree(root / d); shutil.copytree(U.REPO / d, root / d)
    return root, out["by_version"], out["pinless"]

# 新程式：1.1 → 1.2 的 spec-change-impact（正式流程）
NEW_FLOW = r"""
import json, copy
from tools.qaos import engine, store, rm, gates, dispatch
from tools.qaos.cli import main as cli
from tests import helpers as H
BY = "oscar@example.com"; SPEC = "SPEC-AUTH-001"; FROM, TO = "1.1", "1.2"
NEW_R3 = "同一帳號連續 5 次密碼錯誤後鎖定 30 分鐘"
def active():
    out = []
    for p in sorted(store.glob("testcases/registry/TC-AUTH-*.yaml")):
        d = store.load(p)
        if d["status"] == "ACTIVE": out.append((d["testcase_id"], d["active_version"], store.load(store.tc_version_path(d["testcase_id"], d["active_version"]))))
    return out
def rdiff(a, b):
    out = []
    for r in sorted(set(a) | set(b)):
        if r not in a: out.append({"requirement_id": r, "change": "added"})
        elif r not in b: out.append({"requirement_id": r, "change": "removed"})
        else:
            same = (a[r]["statement"], a[r]["acceptance_criteria"]) == (b[r]["statement"], b[r]["acceptance_criteria"])
            out.append({"requirement_id": r, "change": "unchanged"} if same else {"requirement_id": r, "change": "changed", "detail": f"{a[r]['statement']} → {b[r]['statement']}"})
    return out
def task_status(rid, tid): return engine._task(engine.load_run(rid), tid)["status"]
cli(["spec", "import", "tests/fixtures/SPEC-AUTH-001-v1.2.md", "--spec-id", SPEC, "--version", TO, "--product", "demo", "--area", "AUTH", "--change-summary", "鎖定 15 → 30 分鐘", "--by", BY])
rid = engine.new_run("spec-change-impact", {"spec_id": SPEC, "from_version": FROM, "to_version": TO}, BY, new_request=True)["run_id"]
run = engine.load_run(rid); out = {"rid": rid, "current_after_new": run["current_task_id"], "from_pin": run.get("from_requirement_model_revision")}
# T0 Spec Analyst：1.2 的 RM（REQ-AUTH-003 改變）
m = H.requirement_model(TO, "12")
for r in m["requirements"]:
    if r["requirement_id"] == "REQ-AUTH-003":
        r["statement"] = NEW_R3; r["acceptance_criteria"][0]["then"] = "帳號鎖定 30 分鐘，後續登入回「帳號已鎖定」"
ch = next(v for v in store.load(store.spec_dir(SPEC) / "spec.yaml")["versions"] if v["spec_version"] == TO)["content_hash"]
sa = {"spec_id": SPEC, "spec_version": TO, "content_hash": ch, "summary": "v1.2", "scope": {"in_scope": [], "out_of_scope": []},
      "requirement_ids": [r["requirement_id"] for r in m["requirements"]], "ambiguities": [], "constraints": [], "edge_case_candidates": [], "open_questions": []}
refs_ = [{"entity_type": "SpecVersion", "id": SPEC, "version": TO}]
_, p1 = H.write_artifact(rid, "T0", "agent-spec-analyst", "SpecAnalysis", sa, refs_, {"type": "SpecVersion", "ids": [f"{SPEC}@{TO}"]}, "spec-analysis")
rmid, p2 = H.write_artifact(rid, "T0", "agent-spec-analyst", "RequirementModel", m, refs_, {"type": "SpecVersion", "ids": [f"{SPEC}@{TO}"]}, "requirements")
s1, s2 = engine.submit(rid, "T0", str(p1)), engine.submit(rid, "T0", str(p2))
out["t0_submit"] = [s1[0], s2[0], str(s1[1])[:300], str(s2[1])[:300]]
g0 = engine.evaluate_gate(rid, "T0"); out["t0"] = [g0["result"], g0["issues"][:5]]
run = engine.load_run(rid); fr, to = run["from_requirement_model_revision"], run["requirement_model_revision"]
out["from_pin"], out["to_pin"] = fr, to
# 候選（G-IMPACT 實際使用的函式）與每張 TC 的 pin／sidecar
cand, errs = gates._cia_candidates(SPEC); out["cand"] = cand; out["cand_errs"] = errs
out["tc"] = {t: {"version": v, "spec_version": d["spec_version"], "pin": rm.tc_pin(t, v), "in_version_file": "requirement_model_revision" in d,
                 "sidecar": store.load(f"testcases/_bindings/{t}-v{v}.yaml") if store.exists(f"testcases/_bindings/{t}-v{v}.yaml") else None} for t, v, d in active()}
out["r000"] = {ver: rm.pin_of(SPEC, ver, "R000") for ver in ("1.0", "1.1")}
# CIA agent（impact 階段）的判定：候選＝本 spec 全部 ACTIVE TC，依各自的 pin 分組；每組以自己的 from_pin 對 to revision 比對（G7）
to_reqs = rm.requirements_of(to); groups = {}
for t, v, _ in active(): groups.setdefault(json.dumps(rm.tc_pin(t, v), sort_keys=True), []).append((t, v))
pg, imp = [], []
for k, (pin_s, members) in enumerate(sorted(groups.items(), key=lambda x: json.loads(x[0])["spec_version"])):
    pin = json.loads(pin_s); d = rdiff(rm.requirements_of(pin), to_reqs); chg = {x["requirement_id"] for x in d if x["change"] != "unchanged"}
    pg.append({"from_pin": pin, "testcase_ids": [t for t, _ in members], "requirement_diff": d})
    for t, v in members:
        hit = sorted(set(store.load(store.tc_version_path(t, v))["requirement_ids"]) & chg)
        imp.append({"testcase_id": t, "active_version": v, "impact": "affected" if hit else "unaffected", "reason": "需求變更" if hit else "-",
                    "affected_requirement_ids": hit, "pin_group_index": k})
top = rdiff(rm.requirements_of(fr), to_reqs)
good = {"change_impact_id": f"CI-{SPEC}-{FROM}-{TO}", "spec_id": SPEC, "from_version": FROM, "to_version": TO, "from_rm_revision": fr, "to_rm_revision": to,
        "requirement_diff": top, "pin_groups": pg, "testcase_impact": imp,
        "summary": {"requirements_changed": sum(x["change"] == "changed" for x in top), "requirements_added": 0, "requirements_removed": 0,
                    "testcases_affected": sum(i["impact"] == "affected" for i in imp), "testcases_obsolete": 0, "testcases_unaffected": sum(i["impact"] == "unaffected" for i in imp)},
        "completeness": {"all_active_requirements_judged": True, "all_referencing_testcases_judged": True}}
def impact(cir):
    refs2 = [{"entity_type": "SpecVersion", "id": SPEC, "version": TO}] + [{"entity_type": "TestCaseVersion", "id": i["testcase_id"], "version": i["active_version"]} for i in cir["testcase_impact"]]
    cid, p = H.write_artifact(rid, "T1", "agent-change-impact-analyst", "ChangeImpactReport", cir, refs2, {"type": "SpecVersion", "ids": [f"{SPEC}@{TO}"]}, "change-impact")
    try:
        ok, pr = engine.submit(rid, "T1", str(p))
        if not ok: return {"result": "SUBMIT_INVALID", "issues": [str(pr)]}
        return engine.evaluate_gate(rid, "T1")
    except Exception as e:                                              # 反例意外 PASS 時 run 已離開 T1：記錄下來，讓對應的測試各自失敗
        return {"result": "EXCEPTION", "issues": [f"{type(e).__name__}: {e}"[:300]]}
# (i) 反例：只判 run 的 from 端（1.1 R000）那組——對應「只判 0.2 的 48 條」
k1 = next(k for k, g in enumerate(pg) if g["from_pin"] == fr)
only = copy.deepcopy(good); only["pin_groups"] = [only["pin_groups"][k1]]
only["testcase_impact"] = [dict(i, pin_group_index=0) for i in only["testcase_impact"] if i["pin_group_index"] == k1]
only["summary"]["testcases_affected"] = sum(i["impact"] == "affected" for i in only["testcase_impact"])
only["summary"]["testcases_unaffected"] = sum(i["impact"] == "unaffected" for i in only["testcase_impact"])
bad = impact(only)
run = engine.load_run(rid)
out["bad"] = {"result": bad["result"], "issues": bad["issues"], "T1": task_status(rid, "T1"), "run_status": run["status"], "current": run["current_task_id"],
              "only_ids": only["pin_groups"][0]["testcase_ids"]}
# (ii) 正確 CIR：兩組恰好分割全部候選
ok = impact(good)
run = engine.load_run(rid); e = (engine._task(run, "T1").get("dispatch_packets") or [None])[-1]
pk = dispatch.load_packet(e)["rm_pins"] if e else {}
ci = f"runs/{rid}/entities/change-impact.yaml"
out["ok"] = {"result": ok["result"], "issues": ok["issues"], "T1": task_status(rid, "T1"), "run_status": run["status"], "current": run["current_task_id"],
             "ci": store.load(ci)["status"] if store.exists(ci) else None}
out["groups"] = [{"from_pin": g["from_pin"], "testcase_ids": g["testcase_ids"], "diff": {d["requirement_id"]: d["change"] for d in g["requirement_diff"]}} for g in pg]
out["impact"] = {i["testcase_id"]: [i["impact"], i["pin_group_index"]] for i in imp}
out["packet"] = {"from": pk.get("from"), "target": pk.get("target"), "pin_groups": pk.get("pin_groups")}
print(json.dumps(out, ensure_ascii=False))
"""

@pytest.fixture(scope="module")
def world():
    root, by_version, pinless = legacy_two_versions()
    LG.migrate(root)                                                    # maintenance start + migrate（新程式）
    U.q(root, "maintenance", "end", "--by", "m", check=True)
    out = json.loads(U.py(root, NEW_FLOW).stdout.strip().splitlines()[-1])
    return {"root": root, "legacy": by_version, "pinless": pinless, **out}

def _versions(w):
    v10 = sorted(t for t, (_, sv) in w["legacy"].items() if sv == "1.0")
    v11 = sorted(t for t, (_, sv) in w["legacy"].items() if sv == "1.1")
    return v10, v11

def test_legacy_fixture_shape_two_versions(world):
    """legacy fixture（舊程式正式流程）：1.0、1.1 兩個版本都有 ACTIVE TC，且版本檔都沒有 pin（對應 DAILYREPORT 0.1、0.2 的 legacy TC）。"""
    v10, v11 = _versions(world)
    assert world["pinless"] is True
    assert len(v10) >= 2 and len(v11) >= 2, world["legacy"]
    assert len(v10) + len(v11) == len(world["legacy"]) == 5
    assert all(world["legacy"][t][0] == 2 for t in v11) and all(world["legacy"][t][0] == 1 for t in v10)   # 1.1 那批是舊 CIA 升出來的 v2

def test_every_tc_has_legacy_sidecar_bound_to_own_version_r000(world):
    """移轉後：每張 ACTIVE TC 的版本檔仍沒有 pin，sidecar 是 legacy_binding: true，且綁「自己 spec_version 的 R000」。"""
    r000 = world["r000"]
    assert set(world["tc"]) == set(world["legacy"])
    for t, x in world["tc"].items():
        sv = world["legacy"][t][1]
        assert x["spec_version"] == sv and x["version"] == world["legacy"][t][0]
        assert x["in_version_file"] is False
        assert x["sidecar"] is not None and x["sidecar"]["legacy_binding"] is True, (t, x["sidecar"])
        assert x["sidecar"]["requirement_model_revision"] == r000[sv], (t, x["sidecar"])
        assert x["pin"] == r000[sv] and x["pin"]["revision"] == "R000" and x["pin"]["spec_version"] == sv

def test_run_binds_from_1_1_r000_and_t0_g_spec_passes(world):
    """run new spec-change-impact（1.1→1.2）：from 端綁 1.1 R000；T0 Spec Analyst 產出 1.2 RM → G-SPEC PASS，to 端綁 1.2 的 revision。"""
    assert world["current_after_new"] == "T0"
    assert world["t0_submit"][:2] == [True, True], world["t0_submit"]
    assert world["t0"][0] == "PASS", world["t0"]
    assert world["from_pin"] == world["r000"]["1.1"]
    assert world["to_pin"]["spec_version"] == "1.2" and world["to_pin"]["spec_id"] == "SPEC-AUTH-001"

def test_candidates_are_all_active_tcs_across_versions(world):
    """AC-09-31：候選＝本 spec 全部 ACTIVE TC（兩個版本都有，數量＝兩版本總和），各自的 pin 是自己版本的 R000。"""
    v10, v11 = _versions(world); r000 = world["r000"]
    assert world["cand_errs"] == []
    assert len(world["cand"]) == len(v10) + len(v11)
    assert sorted(world["cand"]) == sorted(v10 + v11)
    assert all(world["cand"][t] == r000["1.0"] for t in v10) and all(world["cand"][t] == r000["1.1"] for t in v11)

def test_only_from_version_group_fails_g2_g5(world):
    """AC-09-31 反例：只判 1.1（run 的 from 端）那組——對應「只判 0.2 的 48 條」→ G-IMPACT FAIL，訊息含 G2 與 G5；T1 回 READY、run 仍 RUNNING。"""
    v10, v11 = _versions(world); b = world["bad"]
    assert sorted(b["only_ids"]) == v11
    assert b["result"] == "FAIL", b
    assert any(i.startswith("G2") for i in b["issues"]) and any(i.startswith("G5") for i in b["issues"]), b["issues"]
    g2 = next(i for i in b["issues"] if i.startswith("G2")); g5 = next(i for i in b["issues"] if i.startswith("G5"))
    assert all(t in g2 for t in v10) and all(t in g5 for t in v10)                       # 缺的正是 1.0 那組
    assert b["T1"] == "READY" and b["run_status"] == "RUNNING" and b["current"] == "T1"

def test_correct_two_group_partition_passes_and_packet_has_both_groups(world):
    """AC-09-31 正例：兩組（1.0 R000、1.1 R000）恰好分割全部候選 → G-IMPACT PASS；T1 派發包的 rm_pins.pin_groups 含這兩組，
    from／target 為 run 的兩端。各組的 requirement_diff 以自己的 from_pin 對 1.2 比對：1.0 那組含 REQ-AUTH-001（8→12）與 REQ-AUTH-003，1.1 那組只有 REQ-AUTH-003。"""
    v10, v11 = _versions(world); r000 = world["r000"]
    assert world["ok"]["result"] == "PASS", world["ok"]["issues"]
    assert world["ok"]["T1"] == "DONE" and world["ok"]["run_status"] == "RUNNING" and world["ok"]["current"] != "T1"
    assert world["ok"]["ci"] == "TEST_UPDATE_REQUIRED"
    g = world["groups"]
    assert [x["from_pin"] for x in g] == [r000["1.0"], r000["1.1"]]
    assert sorted(g[0]["testcase_ids"]) == v10 and sorted(g[1]["testcase_ids"]) == v11
    assert g[0]["diff"]["REQ-AUTH-001"] == "changed" and g[0]["diff"]["REQ-AUTH-003"] == "changed"
    assert g[1]["diff"]["REQ-AUTH-001"] == "unchanged" and g[1]["diff"]["REQ-AUTH-003"] == "changed"
    hit = sorted(t for t, (imp, _) in world["impact"].items() if imp == "affected")
    assert len(hit) == 1 and hit[0] in v10                                                 # REQ-AUTH-003 的 TC 留在 1.0 那組
    pk = world["packet"]
    assert pk["from"] == world["from_pin"] and pk["target"] == world["to_pin"]
    assert sorted(json.dumps(p, sort_keys=True) for p in pk["pin_groups"] or []) == sorted(json.dumps(r000[v], sort_keys=True) for v in ("1.0", "1.1"))
