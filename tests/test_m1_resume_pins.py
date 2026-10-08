"""移轉後恢復舊 run 時的 RM 綁定（需求 A 第 5 章 §4.1 run sidecar、移轉章；AC-09-20、AC-09-27）。

legacy 資料一律由需求 A 之前的程式碼（base 2e01d4b，tests/p3_legacy.old_checkout 匯出的唯讀副本）在暫存 root 上
以它自己的正式流程（spec import、new_run、submit、evaluate_gate、approve、cancel、manual_new）產生，不手改業務檔（舊程式碼 2e01d4b 在 root 上執行時，root 的定義層——schemas／agents／workflows／permissions——是新程式的版本，沿用 p3_legacy 的作法；2e01d4b 到目前的定義層差異對這些流程只有說明文字、version 字串與新增欄位，task graph、risk_review 與 applies_to_areas 都沒有變。cross_version 測試的舊 CIR 需要舊 schema，所以那裡改用舊定義層）。
之後全部以新程式的正式指令／API 操作：maintenance start → migrate（RUNNING 的 run 以 --acknowledge-idle 列入）
→ migrate verify → maintenance end → spec reference declare-empty ＋ 新 spec-to-testcase run 重新分析（產生內容不同的 R001，
拿掉 REQ-AUTH-004）→ 恢復舊 run（approve reject／dispatch／submit／evaluate_gate）。
agent 的產出（artifact 檔）由 tests/helpers.write_artifact 寫入，這是「外部寫入」。"""
import json, os, pathlib, subprocess, sys
import yaml
from tests import p1_util as U, p3_legacy as L

SPEC_DIR = "artifacts/requirements/SPEC-AUTH-001/v1.0"

# ---------------------------------------------------------------- 舊程式的正式流程（在 old_checkout 中以子程序執行）
OLD_COMMON = r"""
import json, copy
from tools.qaos import engine, store, tc_ops
from tools.qaos.cli import main as cli
from tests import helpers as H
BY = "oscar@example.com"; SPEC, VER = "SPEC-AUTH-001", "1.0"
def import_and_analyze(area):
    '''spec import（指定 area）→ spec-to-testcase T1 分析 → G-SPEC PASS（舊程式持久化 legacy requirements.yaml）。回傳 (run_id, RM artifact_id)。'''
    cli(["spec", "import", "tests/fixtures/SPEC-AUTH-001-v1.0.md", "--spec-id", SPEC, "--version", VER, "--product", "demo", "--area", area, "--by", BY])
    rid = engine.new_run("spec-to-testcase", {"spec_id": SPEC, "spec_version": VER}, BY)["run_id"]
    rm = H.requirement_model(); refs_ = [{"entity_type": "SpecVersion", "id": SPEC, "version": VER}]
    ch = store.load(store.spec_dir(SPEC) / "spec.yaml")["versions"][0]["content_hash"]
    sa = {"spec_id": SPEC, "spec_version": VER, "content_hash": ch, "summary": "s", "scope": {"in_scope": ["x"], "out_of_scope": []},
          "requirement_ids": [r["requirement_id"] for r in rm["requirements"]], "ambiguities": [], "constraints": [], "edge_case_candidates": [], "open_questions": []}
    _, p1 = H.write_artifact(rid, "T1", "agent-spec-analyst", "SpecAnalysis", sa, refs_, {"type": "SpecVersion", "ids": [f"{SPEC}@{VER}"]}, "spec-analysis")
    rmid, p2 = H.write_artifact(rid, "T1", "agent-spec-analyst", "RequirementModel", rm, refs_, {"type": "SpecVersion", "ids": [f"{SPEC}@{VER}"]}, "requirements")
    assert engine.submit(rid, "T1", str(p1))[0] and engine.submit(rid, "T1", str(p2))[0] and engine.evaluate_gate(rid, "T1")["result"] == "PASS"
    return rid, rmid
def login_tc(prefix, **upd):
    '''REQ-AUTH-004（登入成功）的 TC 稿；加上 error_guessing 讓單條 Draft 也滿足負向覆蓋規則。'''
    t = copy.deepcopy(H.draft_set(prefix=prefix)[0][4]); t.update(design_techniques=["scenario", "error_guessing"], **upd); return t
"""

OLD_FLOW_20 = OLD_COMMON + r"""
# AUTH 不是高風險 area：testcase-revision 沒有 T2RR。先以完整 spec-to-testcase 產生 ACTIVE TC，
# 再對涵蓋 REQ-AUTH-004 的 TC 發起 testcase-revision：T1 Designer → G-DESIGN → T2 Validator → G-TVAL → T3 ACTIVATE 等待核准。
rid1, rmid = import_and_analyze("AUTH")
tcs, _ = H.draft_set()
refs2 = [{"entity_type": "Requirement", "id": r} for r in ["REQ-AUTH-001", "REQ-AUTH-002", "REQ-AUTH-003", "REQ-AUTH-004"]]
did, pd = H.write_artifact(rid1, "T2", "agent-test-designer", "TestCaseDraft", {"mode": "spec", "spec_id": SPEC, "spec_version": VER, "testcases": tcs}, refs2, {"type": "RequirementModel", "ids": [rmid]}, "test-design")
_, pr = H.write_artifact(rid1, "T2", "agent-test-designer", "TestDesignReport", H.design_report(did, tcs), [{"entity_type": "Artifact", "id": did}], {"type": "TestCaseDraft", "ids": [did]}, "test-design")
assert engine.submit(rid1, "T2", str(pd))[0] and engine.submit(rid1, "T2", str(pr))[0] and engine.evaluate_gate(rid1, "T2")["result"] == "PASS"
_, pv = H.write_artifact(rid1, "T3", "agent-test-validator", "TestValidationReport", H.validation_report(did, rmid, "PASS"),
                         [{"entity_type": "Artifact", "id": did}, {"entity_type": "Artifact", "id": rmid}], {"type": "TestCaseDraft", "ids": [did]}, "validation")
assert engine.submit(rid1, "T3", str(pv))[0] and engine.evaluate_gate(rid1, "T3")["result"] == "PASS"
engine.approve(engine.load_run(rid1)["waiting_on_approval_id"], "approve", BY)
tc4 = next(store.load(p)["testcase_id"] for p in sorted((store.ROOT / "testcases/registry").glob("TC-*.yaml"))
           if store.load(store.tc_version_path(store.load(p)["testcase_id"], 1))["requirement_ids"] == ["REQ-AUTH-004"])
rid = engine.new_run("testcase-revision", {"testcase_id": tc4, "reason": "補充登入成功的檢查點", "spec_id": SPEC, "spec_version": VER}, BY)["run_id"]
t = login_tc("01CX5ZZKBKACTAV9WEVGEMMVR", source="change_workflow", supersedes_testcase={"testcase_id": tc4, "version": 1}, title="正確帳密登入成功（修訂）")
d2, pd2 = H.write_artifact(rid, "T1", "agent-test-designer", "TestCaseDraft", {"mode": "change", "spec_id": SPEC, "spec_version": VER, "testcases": [t]},
                           [{"entity_type": "Requirement", "id": "REQ-AUTH-004"}], {"type": "RequirementModel", "ids": [rmid]}, "test-design")
rep = H.design_report(d2, [t]); rep["mode"] = "change"
_, pr2 = H.write_artifact(rid, "T1", "agent-test-designer", "TestDesignReport", rep, [{"entity_type": "Artifact", "id": d2}], {"type": "TestCaseDraft", "ids": [d2]}, "test-design")
assert engine.submit(rid, "T1", str(pd2))[0] and engine.submit(rid, "T1", str(pr2))[0]
g = engine.evaluate_gate(rid, "T1"); assert g["result"] == "PASS", g
_, pv2 = H.write_artifact(rid, "T2", "agent-test-validator", "TestValidationReport", H.validation_report(d2, rmid, "PASS"),
                          [{"entity_type": "Artifact", "id": d2}, {"entity_type": "Artifact", "id": rmid}], {"type": "TestCaseDraft", "ids": [d2]}, "validation")
assert engine.submit(rid, "T2", str(pv2))[0]
g = engine.evaluate_gate(rid, "T2"); assert g["result"] == "PASS", g
run = engine.load_run(rid)
print(json.dumps({"run": rid, "status": run["status"], "apr": run.get("waiting_on_approval_id"), "tc": tc4,
                  "tasks": {x["task_id"]: x["status"] for x in run["tasks"]}}))
"""

OLD_FLOW_27 = OLD_COMMON + r"""
# CASHFLOW 是高風險 area（agents/tc-risk-reviewer.yaml applies_to_areas）：manual run 的 task graph 含 T2RR。
# 分析用的 spec-to-testcase run 在 T1 PASS 後 cancel；manual record 帶 spec_hint → manual-test-to-regression run →
# T1 Designer（manual）提交 Draft → G-DESIGN PASS → 停在 T2（Validator）READY、run RUNNING。
rid1, rmid = import_and_analyze("CASHFLOW")
engine.cancel(rid1, BY)
rec = tc_ops.manual_new("手動測試：正確帳密登入", "demo", "CASHFLOW", ["輸入正確帳密", "點擊登入"], "導向首頁並顯示使用者名稱", "pass", BY, spec_id=SPEC, spec_version=VER)
m = engine.new_run("manual-test-to-regression", {"manual_record_id": rec}, BY)["run_id"]
t = login_tc("01CX5ZZKBKACTAV9WEVGEMMVM", source="manual_integration", functional_area="CASHFLOW", title="手動：正確帳密登入成功")
did, pd = H.write_artifact(m, "T1", "agent-test-designer", "TestCaseDraft", {"mode": "manual", "spec_id": SPEC, "spec_version": VER, "testcases": [t]},
                           [{"entity_type": "Requirement", "id": "REQ-AUTH-004"}], {"type": "ManualTestRecord", "ids": [rec]}, "test-design")
rep = H.design_report(did, [t]); rep["mode"] = "manual"
_, pr = H.write_artifact(m, "T1", "agent-test-designer", "TestDesignReport", rep, [{"entity_type": "Artifact", "id": did}], {"type": "TestCaseDraft", "ids": [did]}, "test-design")
assert engine.submit(m, "T1", str(pd))[0] and engine.submit(m, "T1", str(pr))[0]
g = engine.evaluate_gate(m, "T1"); assert g["result"] == "PASS", g
run = engine.load_run(m)
print(json.dumps({"run": m, "status": run["status"], "current": run.get("current_task_id"), "tasks": [x["task_id"] for x in run["tasks"]],
                  "draft": did, "draft_ids": [t["draft_id"]]}))
"""

def legacy_root(flow: str) -> tuple[pathlib.Path, dict]:
    """全新 root（只有定義層），以舊程式（2e01d4b）執行 flow；回傳 (root, flow 最後一行的 JSON 摘要)。"""
    root = U.mkroot(migrated=False); old = L.old_checkout()
    env = {**os.environ, "QAOS_ROOT": str(root), "PYTHONDONTWRITEBYTECODE": "1"}
    r = subprocess.run([sys.executable, "-c", flow], cwd=old, env=env, capture_output=True, text=True, timeout=300)
    if r.returncode != 0: raise AssertionError(f"舊程式的 legacy 流程失敗：\n{r.stdout}\n{r.stderr}")
    return root, json.loads(r.stdout.strip().splitlines()[-1])

def ok(r): assert r.returncode == 0, r.stdout + r.stderr; return r

def migrate_and_make_r001(root, *ack):
    """新程式：maintenance start → migrate（ack 為 RUNNING 的 run）→ migrate verify → maintenance end；
    之後宣告引用為空、以新 spec-to-testcase run 重新分析，產生拿掉 REQ-AUTH-004 的 R001。回傳 (R000 pin, R001 pin)。"""
    ok(U.q(root, "maintenance", "start", "--by", "m"))
    ok(U.q(root, "migrate", "--by", "m", *[x for r in ack for x in ("--acknowledge-idle", r)]))
    ok(U.q(root, "migrate", "verify"))
    ok(U.q(root, "maintenance", "end", "--by", "m"))
    ok(U.q(root, "spec", "reference", "declare-empty", "SPEC-AUTH-001@1.0", "--reason", "x", "--by", "o"))
    U.py(root, "from tests import p3_flow as F\nr = F.new_run(); F.analyze(r, drop=('REQ-AUTH-004',))")
    idx = U.load(root, f"{SPEC_DIR}/revisions/index.yaml")["revisions"]
    assert [e["revision"] for e in idx] == ["R000", "R001"]
    pins = [{"spec_id": "SPEC-AUTH-001", "spec_version": "1.0", "revision": e["revision"], "sha256": e["sha256"]} for e in idx]
    assert "REQ-AUTH-004" in {q["requirement_id"] for q in U.load(root, f"{SPEC_DIR}/revisions/R000.yaml")["requirements"]}
    assert "REQ-AUTH-004" not in {q["requirement_id"] for q in U.load(root, f"{SPEC_DIR}/revisions/R001.yaml")["requirements"]}   # 最新 revision 已沒有它
    assert pins[0]["sha256"] != pins[1]["sha256"]
    return pins[0], pins[1]

def sidecar_pin(root, rid):
    sc = U.load(root, f"artifacts/requirements/_bindings/{rid}.yaml")
    assert sc["subject"]["run_id"] == rid and sc.get("legacy_binding") is True
    return sc["requirement_model_revision"]

def packet(root, rid, tid):
    """task 本次 iteration 的派發包（依 run.yaml 的 dispatch_packets 紀錄讀，並核對 sha256）。"""
    run = U.load(root, f"runs/{rid}/run.yaml")
    t = next(x for x in run["tasks"] if x["task_id"] == tid)
    e = next(x for x in t["dispatch_packets"] if x["iteration"] == t["iteration"])
    assert U.sha(pathlib.Path(root) / e["path"]) == e["sha256"]
    return U.load(root, e["path"])

# ---------------------------------------------------------------- AC-09-20
def test_ac_09_20_waiting_human_testcase_revision_resumes_on_sidecar_r000():
    """AC-09-20：既有 WAITING_HUMAN 的 testcase-revision run → 移轉 → 恢復；G-DESIGN 讀 sidecar 的 R000，不讀之後產生的 R001。

    fixture：舊程式（2e01d4b）以正式流程 spec import（AUTH）→ spec-to-testcase 全流程（TC ACTIVE）→ 對涵蓋 REQ-AUTH-004 的 TC
    發起 testcase-revision，走到 T3 ACTIVATE_TESTCASE 等待核准（run WAITING_HUMAN）。
    新程式：移轉（WAITING_HUMAN 不需 --acknowledge-idle）→ verify → 結束維護 → 重新分析產生拿掉 REQ-AUTH-004 的 R001 →
    核准單 reject 讓 Designer 重做 → dispatch T1 → 提交仍引用 REQ-AUTH-004 的 Draft → G-DESIGN。
    斷言：派發包 rm_pins.target 等於 sidecar 的 R000（revision 與 sha256）；G-DESIGN PASS（依 R000）；
    同一份 Draft 若依 R001 評估會因「引用不存在的 requirement REQ-AUTH-004」而 FAIL（證明兩個 revision 可區分）；
    run.yaml 自始至終沒有 requirement_model_revision（綁定只在 sidecar）。"""
    root, info = legacy_root(OLD_FLOW_20); rid = info["run"]
    assert info["status"] == "WAITING_HUMAN" and info["tasks"]["T3"] == "RUNNING" and info["apr"]
    assert "T2RR" not in info["tasks"]
    r000, r001 = migrate_and_make_r001(root)
    sc = sidecar_pin(root, rid)
    assert sc == r000                                                                                                # sidecar 綁的是 R000（sha 也相同）
    assert "requirement_model_revision" not in U.load(root, f"runs/{rid}/run.yaml")                                  # 移轉不寫 run.yaml
    assert U.load(root, f"runs/{rid}/run.yaml")["status"] == "WAITING_HUMAN"

    ok(U.q(root, "approve", info["apr"], "--decision", "reject", "--by", "o", "--rationale", "請依意見重做"))
    run = U.load(root, f"runs/{rid}/run.yaml")
    assert run["status"] == "RUNNING" and run["current_task_id"] == "T1"
    ok(U.q(root, "dispatch", rid, "T1"))
    pk = packet(root, rid, "T1")
    assert pk["rm_pins"]["target"] == sc == r000 and pk["rm_pins"]["target"] != r001

    code = f"""
import copy, json
from tools.qaos import engine, store, gates
from tests import helpers as H
rid, tc = "{rid}", "{info['tc']}"
rmid = store.load("{SPEC_DIR}/revisions/R000.yaml")["source_artifact_id"]
it = engine._task(engine.load_run(rid), "T1")["iteration"]
t = copy.deepcopy(H.draft_set(prefix="01CX5ZZKBKACTAV9WEVGEMMVS")[0][4])
t.update(source="change_workflow", supersedes_testcase={{"testcase_id": tc, "version": 1}}, title="正確帳密登入成功（修訂二）", design_techniques=["scenario", "error_guessing"])
d, pd = H.write_artifact(rid, "T1", "agent-test-designer", "TestCaseDraft", {{"mode": "change", "spec_id": "SPEC-AUTH-001", "spec_version": "1.0", "testcases": [t]}},
                         [{{"entity_type": "Requirement", "id": "REQ-AUTH-004"}}], {{"type": "RequirementModel", "ids": [rmid]}}, "test-design", iteration=it)
rep = H.design_report(d, [t]); rep["mode"] = "change"
_, pr = H.write_artifact(rid, "T1", "agent-test-designer", "TestDesignReport", rep, [{{"entity_type": "Artifact", "id": d}}], {{"type": "TestCaseDraft", "ids": [d]}}, "test-design", iteration=it)
assert engine.submit(rid, "T1", str(pd))[0] and engine.submit(rid, "T1", str(pr))[0]
g = engine.evaluate_gate(rid, "T1")
# 對照（唯讀、不寫檔）：同一份 Draft 若依最新的 R001 評估
run = engine.load_run(rid); latest = {json.dumps(r001)}
arts = {{"TestCaseDraft": store.load(pd), "TestDesignReport": store.load(pr)}}
alt = gates.g_design({{**run, "requirement_model_revision": latest}}, None, arts)
print(json.dumps({{"g": g, "alt": alt, "it": it}}, ensure_ascii=False))"""
    out = json.loads(U.py(root, code).stdout.strip().splitlines()[-1])
    assert out["g"]["result"] == "PASS", out["g"]                                                                     # 依 sidecar 的 R000 → PASS
    assert any("引用不存在的 requirement REQ-AUTH-004" in i for i in out["alt"]), out["alt"]                          # 依 R001 → FAIL
    run = U.load(root, f"runs/{rid}/run.yaml")
    assert "requirement_model_revision" not in run and U.load(root, f"artifacts/requirements/_bindings/{rid}.yaml")["requirement_model_revision"] == r000
    assert next(t for t in run["tasks"] if t["task_id"] == "T1")["status"] == "DONE" and run["current_task_id"] == "T2"

# ---------------------------------------------------------------- AC-09-27
def test_ac_09_27_old_manual_run_rr_and_validator_packets_share_sidecar_r000():
    """AC-09-27：已存在、綁定 R000 的舊 manual run（manual-test-to-regression）移轉後恢復；RR（T2RR）與 Validator（T2）的派發包使用同一個 R000。

    fixture：舊程式（2e01d4b）以正式流程 spec import（CASHFLOW，高風險 area）→ spec-to-testcase T1 分析後 cancel →
    manual new（spec_hint 指向 SPEC-AUTH-001@1.0）→ run new manual-test-to-regression（task graph 含 T2RR）→
    T1 Designer 提交 Draft（REQ-AUTH-004）→ G-DESIGN PASS；run RUNNING、停在 T2 READY。
    新程式：移轉（--acknowledge-idle 該 run）→ verify → 結束維護 → 重新分析產生拿掉 REQ-AUTH-004 的 R001 →
    dispatch T2 → 提交 Validator PASS → G-TVAL PASS → dispatch T2RR → 提交 TCRiskReview → G-RISK PASS → ACTIVATE 等待核准。
    斷言：T2 與 T2RR 派發包的 rm_pins 完全相同，target 等於 sidecar 的 R000（revision、sha256），不是 R001；run.yaml 沒有 pin。"""
    root, info = legacy_root(OLD_FLOW_27); rid = info["run"]
    assert info["status"] == "RUNNING" and info["current"] == "T2" and info["tasks"][:3] == ["T1", "T2", "T2RR"]
    r000, r001 = migrate_and_make_r001(root, rid)
    sc = sidecar_pin(root, rid)
    assert sc == r000
    assert "requirement_model_revision" not in U.load(root, f"runs/{rid}/run.yaml")

    ok(U.q(root, "dispatch", rid, "T2"))
    code = f"""
import json
from tools.qaos import engine, store
from tests import helpers as H
m, did = "{rid}", "{info['draft']}"
rmid = store.load("{SPEC_DIR}/revisions/R000.yaml")["source_artifact_id"]
it = engine._task(engine.load_run(m), "T2")["iteration"]
_, pv = H.write_artifact(m, "T2", "agent-test-validator", "TestValidationReport", H.validation_report(did, rmid, "PASS"),
                         [{{"entity_type": "Artifact", "id": did}}, {{"entity_type": "Artifact", "id": rmid}}], {{"type": "TestCaseDraft", "ids": [did]}}, "validation", iteration=it)
assert engine.submit(m, "T2", str(pv))[0]
g = engine.evaluate_gate(m, "T2")
print(json.dumps({{"g": g, "tvr": pv.stem, "cur": engine.load_run(m)["current_task_id"]}}, ensure_ascii=False))"""
    out = json.loads(U.py(root, code).stdout.strip().splitlines()[-1])
    assert out["g"]["result"] == "PASS", out["g"]
    assert out["cur"] == "T2RR"
    ok(U.q(root, "dispatch", rid, "T2RR"))
    code = f"""
import json
from tools.qaos import engine
from tests import helpers as H
m, did, tvr = "{rid}", "{info['draft']}", "{out['tvr']}"
DIMS = ["boundary", "exception_flow", "concurrency", "duplicate_submission", "permission"]
payload = {{"reviewed": {{"testcase_draft_artifact_id": did, "validation_report_artifact_id": tvr, "functional_area": "CASHFLOW",
                          "spec_id": "SPEC-AUTH-001", "spec_version": "1.0", "testcase_draft_ids": {json.dumps(info['draft_ids'])}}},
           "dimension_results": [{{"dimension": d, "status": "covered", "rationale": f"{{d}} 已逐條檢視本次 draft"}} for d in DIMS],
           "findings": [], "summary": "抽查完成，五個面向都已逐條檢視，沒有補充建議"}}
_, p = H.write_artifact(m, "T2RR", "agent-tc-risk-reviewer", "TCRiskReview", payload, [{{"entity_type": "Artifact", "id": did}}, {{"entity_type": "Artifact", "id": tvr}}],
                        {{"type": "TestCaseDraft", "ids": [did]}}, "risk-review")
assert engine.submit(m, "T2RR", str(p))[0]
g = engine.evaluate_gate(m, "T2RR"); run = engine.load_run(m)
print(json.dumps({{"g": g, "status": run["status"]}}, ensure_ascii=False))"""
    out2 = json.loads(U.py(root, code).stdout.strip().splitlines()[-1])
    assert out2["g"]["result"] == "PASS", out2["g"]
    assert out2["status"] == "WAITING_HUMAN"

    v, rr = packet(root, rid, "T2"), packet(root, rid, "T2RR")
    assert v["agent_id"] == "agent-test-validator" and rr["agent_id"] == "agent-tc-risk-reviewer"
    assert v["rm_pins"] == rr["rm_pins"]                                                                              # 兩者彼此相同
    for pk in (v, rr):
        assert pk["rm_pins"]["target"] == sc == r000                                                                  # revision 與 sha256 都是 sidecar 的 R000
        assert pk["rm_pins"]["target"] != r001 and pk["rm_pins"]["target"]["revision"] == "R000"
    assert "requirement_model_revision" not in U.load(root, f"runs/{rid}/run.yaml")                                  # 綁定仍只在 sidecar
