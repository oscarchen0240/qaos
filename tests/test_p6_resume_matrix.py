"""P6-G1：操作類型的恢復驗收矩陣——補齊既有測試只涵蓋一半或沒有涵蓋的格子
（最終規格第 4 章 §15、§16、§18.2、§18.4、§18.12；第 5 章 §14；第 6 章 §8；第 6 章之後 §12.4 AC-A-B1-3；實作計畫 v11 §3.3、§4.4.5）。

每個案例使用獨立的暫存 root：初始狀態一律以正式流程（CLI、正式 API，tests/p4_flow.py、tests/p5_flow.py、tests/p3_legacy.py）建立，
同一種前置狀態只建一次範本、每個案例複製一份（root 內沒有絕對路徑）。故障以 QAOS_FAULT 注入（程序在指定點結束，returncode 86；
`raise:` 前綴則拋出例外）。標明「竄改」「模擬經授權的人工修復」的子例才在流程後修改檔案。

每個續做案例的共同斷言（§18 通用驗收方式 1～4，check_post）：
  1. 計畫檔 sha256 不變；該 op 只有一筆登錄紀錄、只有一筆 completed 狀態紀錄；progress.d 的完成紀錄數等於步驟數；
     每個 (op, step) 的事件檔恰好一個；沒有殘留暫存檔、沒有未登錄或未完成的計畫；
  2. 計畫完成；
  3. 中止期間其他 op 被拒絕（提示 operation resume），而且拒絕不寫入任何檔案；
  4. 每一步的路徑都等於計畫記錄的 expected_after（即 post_state／to_state）。
另外各測試斷言自己的業務物件沒有重複（CLR、APR、TC 版本、landing、掃描紀錄、fulfillment、狀態轉換）。"""
import json, pathlib, shutil, tempfile, yaml, pytest
from tests import p1_util as U
from tests import p3_legacy as LG
from tests.test_p4_dispatch import mkroot as _demo_root, py
from tests.test_p3_migrate import legacy as _legacy, x_of, status_files, _r_plan

FAULT = 86
NOTHING = {"added": [], "removed": [], "changed": []}
OTHER = ("audit", "render", "--new-request")                 # 一定是另一個 op 的寫入請求
HDR = "from tests import p5_flow as P\nfrom tools.qaos import clr_lifecycle as L\n"
ENTRIES = ["resend", "resume"]

# ================================================================ 範本與共同斷言
_T: dict = {}

def _copy(src: pathlib.Path) -> pathlib.Path:
    dst = pathlib.Path(tempfile.mkdtemp(prefix="qaos-p6g1-")) / "root"
    shutil.copytree(src, dst, symlinks=True)
    return dst

def template(name, build):
    """以正式流程建立一次範本（build() → (root, info)），回傳一份複本與 info。"""
    if name not in _T: _T[name] = build()
    root, info = _T[name]
    return _copy(root), dict(info)

def demo_root():
    return _demo_root(pathlib.Path(tempfile.mkdtemp(prefix="qaos-p6g1-src-")))

def plan_file(root, op) -> pathlib.Path:
    return next(pathlib.Path(root).glob(f"operations/*/{op}.yaml"))

def events_of(root, op) -> list[str]:
    root = pathlib.Path(root)
    return sorted(p.relative_to(root).as_posix() for p in (root / "runs").rglob(f"{op}-*.yaml"))

def regs_of(root, op) -> list[dict]:
    return [o for o in U.op_list(root) if o["op_id"] == op]

def check_post(root, op, plan_sha):
    """§18 通用斷言 1、2、4（見模組說明）。"""
    root = pathlib.Path(root); plan = U.plan_of(root, op)
    assert U.sha(plan_file(root, op)) == plan_sha, "計畫檔被改寫"
    regs = regs_of(root, op); assert len(regs) == 1 and regs[0]["statuses"] == {"completed"}, regs
    prog = list((root / f"operations/{plan['scope']}/{op}/progress.d").glob("*.yaml"))
    assert len(prog) == len(plan["steps"]) - 1, (len(prog), len(plan["steps"]))
    assert events_of(root, op) == sorted(s["path"] for s in plan["steps"] if s["kind"] == "event")
    for s in plan["steps"]:
        if s["kind"] in ("status_final", "control"): continue
        assert U.sha(root / s["path"]) == s["expected_after"], f"{s['seq']} {s['path']} 不等於計畫的 expected_after"
    assert U.incomplete(root) == [] and U.unregistered_plans(root) == []
    assert not list(root.rglob(".qaos-tmp-*"))
    return plan

def abort(root, args, fault, *, expect=FAULT):
    r = U.q(root, *args, fault=fault)
    assert r.returncode == expect, (fault, r.returncode, r.stdout[-800:], r.stderr[-800:])
    if fault == "after_plan_save":
        un = U.unregistered_plans(root); assert len(un) == 1, un; return un[0]
    inc = U.incomplete(root); assert len(inc) == 1, inc
    return inc[0]["op_id"]

def refused_without_writes(root, op, args=OTHER, hint="operation resume", reconcile=False):
    """§18 通用斷言 3：中止期間其他 op 被拒絕；被拒絕的請求不寫任何檔案（FP-P1 時第一個寫入請求只做登錄補齊）。"""
    before = U.snapshot(root)
    r = U.q(root, *args); assert r.returncode != 0 and hint in r.stderr and "Traceback" not in r.stderr, (args, r.stderr[-800:])
    d = U.diff(before, U.snapshot(root))
    if reconcile:                                                       # 登錄補齊＋清除本 op 計畫保存後留下的寫入清單與認領檔（附錄 A 4-18）
        assert d["changed"] == [] and all(p.startswith("operations/_global/staging.d/") and op in p for p in d["removed"]), d
        assert len(d["added"]) == 1 and d["added"][0].startswith("operations/_global/index.d/") and op in d["added"][0], d
    else: assert d == NOTHING, d
    return r

def cont(root, args, entry, op):
    r = U.q(root, *args) if entry == "resend" else U.q(root, "operation", "resume", op)
    assert r.returncode == 0, (entry, r.stdout[-800:], r.stderr[-800:])
    return r

def abort_and_resume(root, args, entry, fault, other=OTHER):
    """中止 → 斷言其他 op 被拒絕 → 以 entry 續做 → check_post。回傳 (op, plan)。"""
    op = abort(root, args, fault)
    psha = U.sha(plan_file(root, op))
    tail = None
    if fault.startswith("after_output:"):                               # FP-W：合法尾端的輸出不重寫（inode 不變）
        st = next(s for s in U.plan_of(root, op)["steps"] if s["seq"] == int(fault.split(":")[1]))
        if st["expected_after"] is not None: tail = (st["path"], (pathlib.Path(root) / st["path"]).stat().st_ino)
    if other: refused_without_writes(root, op, other, reconcile=(fault == "after_plan_save"))
    cont(root, args, entry, op)
    if tail: assert (pathlib.Path(root) / tail[0]).stat().st_ino == tail[1], f"{tail[0]}（合法尾端）被重寫"
    return op, check_post(root, op, psha)

def reference_steps(build_name, build, args) -> list[dict]:
    """在另一份複本正常執行一次，取得該請求的計畫步驟（同一份範本、同一請求產生相同的步驟結構）。"""
    key = ("steps", build_name, tuple(map(str, args)))
    if key not in _T:
        root, _ = template(build_name, build)
        U.q(root, *args, check=True); _T[key] = U.last_plan(root)["steps"]
    return _T[key]

def points_for(steps, entry, named=()):
    """FP-P1、FP-P2、9k，加上 FP-W 的每一步（兩種入口交替分擔），以及 named（兩種入口都做）的步驟界線。"""
    pts = ["after_plan_save", "after_register", "before_completed"]
    pts += [f"after_output:{s['seq']}" for s in steps if s["kind"] != "status_final" and (s["seq"] % 2 == 1) == (entry == "resend")]
    return pts + list(named)

def apply_every_point(build_name, build, args, entry, business, named=()):
    """對每個中止點：複製範本 → 中止 → 續做 → 共同斷言 → 業務斷言。"""
    steps = reference_steps(build_name, build, args)
    for fault in points_for(steps, entry, named):
        root, info = template(build_name, build)
        op, plan = abort_and_resume(root, args, entry, fault)
        business(root, info, op, plan, fault)

# ================================================================ 範本：G-SPEC 提交（9e～9j）、A4、TC 版本（9h）
SUBMIT_T1 = """
from tests import helpers as H
def submit_t1(rid, reqs):
    rm_ = {"spec_id": F.SPEC, "spec_version": F.VER, "requirements": reqs, "traceability": [{"requirement_id": r["requirement_id"], "spec_reference": r["spec_reference"]} for r in reqs]}
    sa = {"spec_id": F.SPEC, "spec_version": F.VER, "content_hash": F.pin()["content_hash"], "summary": "s", "scope": {"in_scope": ["x"], "out_of_scope": []},
          "requirement_ids": [r["requirement_id"] for r in reqs], "ambiguities": [], "constraints": [], "edge_case_candidates": [], "open_questions": []}
    refs_ = [{"entity_type": "SpecVersion", "id": F.SPEC, "version": F.VER}]; src = {"type": "SpecVersion", "ids": [f"{F.SPEC}@{F.VER}"]}
    for t, pl, sub in (("SpecAnalysis", sa, "spec-analysis"), ("RequirementModel", rm_, "requirements")):
        _, p = H.write_artifact(rid, "T1", "agent-spec-analyst", t, pl, refs_, src, sub); ok, pr = engine.submit(rid, "T1", str(p)); assert ok, pr
"""
OTHER_REQ = 'F.req(2, [F.dp("Q01", "undefined", "minor", topic="other", subject="ui.banner.color", decision_needed="首頁橫幅顏色要不要可設定")], ambiguity=F.amb("minor", "minor"), statement="首頁橫幅顏色規則")'

def build_gspec():
    """T1 已提交 SpecAnalysis＋RequirementModel：REQ-DEMO-001 critical conflict（→ RESOLVE_AMBIGUITY 核准單＋CLR）、REQ-DEMO-002 topic other（→ CLR）。"""
    root = demo_root()
    rid = py(root, HDR + SUBMIT_T1 + f"rid = F.new_run(); submit_t1(rid, [P.conflict_req(1), {OTHER_REQ}]); print(json.dumps(rid))")
    return root, {"rid": rid}

def gspec_business(root, info, op, plan, fault):
    """9e：CLR（含 topic other）只有計畫配發的那幾張；9f：.md 和 yaml 一致；9g：只有一張 APR、waiting_on_approval_id 指向它；
    9i：檢視（requirements.yaml）等於 revision；9j：spec.yaml、run.yaml 等於 after（共同斷言 4）。"""
    root = pathlib.Path(root); rid = info["rid"]
    clrs = sorted(p.stem for p in root.glob("clarifications/demo/DEMO/CLR-*.yaml"))
    assert clrs == sorted(i for i in plan["allocated_ids"] if i.startswith("CLR-")) and len(clrs) == 2, (fault, clrs, plan["allocated_ids"])
    docs = {c: U.load(root, f"clarifications/demo/DEMO/{c}.yaml") for c in clrs}
    assert [d.get("topic") for d in docs.values()].count("other") == 1, fault                                    # 9e：other 的 CLR 只有一張
    rendered = py(root, f"from tools.qaos import clarification as C\nprint(json.dumps({{c: C._render(C.load(c)) for c in {clrs!r}}}))")
    for c in clrs: assert (root / f"clarifications/demo/DEMO/{c}.md").read_text(encoding="utf-8") == rendered[c], (fault, c)   # 9f
    aprs = sorted(p.stem for p in root.glob("approvals/APR-*.yaml"))
    assert aprs == [i for i in plan["allocated_ids"] if i.startswith("APR-")] and len(aprs) == 1, (fault, aprs)
    assert U.load(root, f"runs/{rid}/run.yaml")["waiting_on_approval_id"] == aprs[0]                              # 9g
    view = U.load(root, "artifacts/requirements/SPEC-DEMO-001/v1.0/requirements.yaml")
    rev = U.load(root, f"artifacts/requirements/SPEC-DEMO-001/v1.0/revisions/{view['revision']}.yaml")
    idx = U.load(root, "artifacts/requirements/SPEC-DEMO-001/v1.0/revisions/index.yaml")["revisions"]
    assert [r["revision"] for r in idx] == ["R001"] and view["revision"] == "R001" and view["requirements"] == rev["requirements"]   # 9i

@pytest.mark.parametrize("entry", ENTRIES)
def test_9e_to_9j_gspec_submit_every_point(entry):
    """AC-07-9e、9f、9g、9i、9j、9k、AC-07-22（submit_gate 不含 A4）、FP-P1、FP-P2、FP-W（AC-07-95、97、98）以真實的 G-SPEC 提交驗收：
    每一步「輸出已落盤、完成紀錄未落盤」（兩種入口交替）以及恢復表各列的步驟界線（兩種入口都做）中止後續做。"""
    _, info = template("gspec", build_gspec); args = ["gate", info["rid"], "T1"]
    steps = reference_steps("gspec", build_gspec, args)
    seq = lambda pred: next(s["seq"] for s in steps if pred(s))
    clr_yaml = [s["seq"] for s in steps if s["path"].startswith("clarifications/") and s["path"].endswith(".yaml")]
    named = [f"after_progress:{seq(lambda s: '/revisions/R' in s['path'])}",                   # 9i：revision 等於 after、檢視等於 before
             f"after_progress:{seq(lambda s: s['path'].startswith('approvals/'))}",            # 9g：APR 已寫、run.yaml 等於 before
             f"after_progress:{clr_yaml[0]}",                                                    # 9e：部分 CLR 已寫
             f"after_progress:{clr_yaml[-1]}",                                                   # 9f：CLR yaml 已寫、.md 等於 before
             f"after_progress:{seq(lambda s: s['path'].endswith('/spec.yaml'))}"]                # 9j：spec.yaml 已寫、run.yaml 等於 before
    apply_every_point("gspec", build_gspec, args, entry, gspec_business, named)

def build_a4():
    """RA-P1（critical conflict → answer → approve select_interpretation）後，T1 重開並以 CLR 最新 rev 為 resolution 提交（G-SPEC 會觸發 A4）。"""
    root = demo_root()
    rid, cid = py(root, HDR + SUBMIT_T1 + """
rid, cid, apr = P.ra_p1()
res = {"source": F.cref(cid, "任何站台都不能刪除"), "decided_at": "2026-10-07", "adopted_side_index": 1}
submit_t1(rid, [P.conflict_req(1, res)])
print(json.dumps([rid, cid]))""")
    return root, {"rid": rid, "cid": cid}

def a4_business(root, info, op, plan, fault):
    c = U.load(root, f"clarifications/demo/DEMO/{info['cid']}.yaml")
    assert c["status"] == "INCORPORATED" and [l["type"] for l in c["landings"]] == ["incorporated"], (fault, c.get("landings"))   # landing 只有一筆
    assert [h["to_status"] for h in c["history"]].count("INCORPORATED") == 1, fault

@pytest.mark.parametrize("entry", ENTRIES)
def test_submit_gate_with_a4_every_point(entry):
    """AC-07-22（submit_gate 含 A4）、第 6 章 §8 第 3 點：每個中止點續做後 CLR 只轉 INCORPORATED 一次、incorporated landing 只有一筆。
    （test_p5_resume.py::test_gate_with_a4_and_apply_a6 只在第 2 步中止、沒有斷言其他 op 被拒絕與計畫不變。）"""
    _, info = template("a4", build_a4)
    apply_every_point("a4", build_a4, ["gate", info["rid"], "T1"], entry, a4_business)

TWO_TCS = """
tc1 = F.tc(1, "REQ-DEMO-001", "刪除子站台被拒絕並顯示提示", techs=["negative"], types=["negative"], expected="系統拒絕刪除")
tc2 = F.tc(2, "REQ-DEMO-001", "刪除總站台被拒絕並顯示提示", techs=["negative"], types=["negative"], expected="系統拒絕刪除")
"""

def build_tval():
    """一般需求（G-SPEC PASS）→ 兩張 TC 的設計（G-DESIGN PASS）→ Validator PASS 報告已提交、T3 還沒 gate。"""
    root = demo_root()
    out = py(root, TWO_TCS + """
rid = F.new_run(); g = F.analyze(rid, [F.req(1)]); assert g["result"] == "PASS", g                     # 沒有決策點的需求（TC 不需要 decision_refs）
d = F.design(rid, [tc1, tc2]); assert d["result"] == "PASS", d
_, pv = H.write_artifact(rid, "T3", "agent-test-validator", "TestValidationReport", H.validation_report(d["did"], g["rmid"], "PASS"),
                         [{"entity_type": "Artifact", "id": d["did"]}, {"entity_type": "Artifact", "id": g["rmid"]}], {"type": "TestCaseDraft", "ids": [d["did"]]}, "validation")
ok, pr = engine.submit(rid, "T3", str(pv)); assert ok, pr
print(json.dumps(rid))""")
    return root, {"rid": out}

def _tcs(root):
    return sorted(p.stem for p in pathlib.Path(root).glob("testcases/registry/TC-*.yaml"))

def tval_business(root, info, op, plan, fault):
    """9h：所有列入的 TC 都是 PENDING_APPROVAL；TC 與版本檔沒有重複；核准單只有一張。"""
    root = pathlib.Path(root); tcs = _tcs(root)
    assert len(tcs) == 2, (fault, tcs)
    for t in tcs:
        assert sorted(p.name for p in (root / f"testcases/versions/{t}").glob("v*.yaml")) == ["v1.yaml"], (fault, t)
        assert U.load(root, f"testcases/versions/{t}/v1.yaml")["status"] == "PENDING_APPROVAL", (fault, t)
    aprs = sorted(p.stem for p in root.glob("approvals/APR-*.yaml")); assert len(aprs) == 1, (fault, aprs)
    assert U.load(root, f"runs/{info['rid']}/run.yaml")["waiting_on_approval_id"] == aprs[0]

@pytest.mark.parametrize("entry", ENTRIES)
def test_9h_tc_versions_and_activate_approve(entry):
    """AC-07-9h（部分 TC 版本檔等於 before → 只寫那些；所有列入的 TC 都是 PENDING_APPROVAL）、AC-07-22（G-TVAL 的 submit_gate）、
    AC-07-23、24（ACTIVATE 的 approve 與 complete_run）：每個中止點續做；核准後兩張 TC 各只有 v1、ACTIVE，run COMPLETED 一次。"""
    _, info = template("tval", build_tval); rid = info["rid"]; args = ["gate", rid, "T3"]
    steps = reference_steps("tval", build_tval, args)
    vers = [s["seq"] for s in steps if s["path"].startswith("testcases/versions/")]
    assert len(vers) == 2, [s["path"] for s in steps]
    apply_every_point("tval", build_tval, args, entry, tval_business, named=[f"after_progress:{vers[0]}"])   # 9h：只寫了第一張 TC 版本
    root, _ = template("tval", build_tval); U.q(root, *args, check=True)
    apr = U.load(root, f"runs/{rid}/run.yaml")["waiting_on_approval_id"]
    a_args = ["approve", apr, "--decision", "approve", "--by", "oscar@example.com"]
    op, plan = abort_and_resume(root, a_args, entry, "after_output:2")
    for t in _tcs(root):
        assert U.load(root, f"testcases/registry/{t}.yaml")["status"] == "ACTIVE"
        assert sorted(p.name for p in (pathlib.Path(root) / f"testcases/versions/{t}").glob("v*.yaml")) == ["v1.yaml"]
    run = U.load(root, f"runs/{rid}/run.yaml")
    assert run["status"] == "COMPLETED" and [h.get("to_status") for h in run["history"]].count("COMPLETED") == 1, run["history"]

# ================================================================ metadata upgrade（AC-07-28）
def build_legacy_migrated():
    """需求 A 之前的程式產生的 legacy 資料，經 maintenance start → migrate → maintenance end 進入 S_post（tests/p3_legacy.py）。"""
    root, info = _legacy()
    LG.migrate(root, "--acknowledge-idle", info["running"], check=True)
    U.q(root, "maintenance", "end", "--by", "m", check=True)
    return root, info

SPEC_UP = ["spec", "metadata", "upgrade", "SPEC-AUTH-001@1.0", "--analysis-policy", "analyze", "--reason", "補分析政策", "--by", "oscar"]

def spec_up_business(root, info, op, plan, fault):
    spec = U.load(root, "specs/demo/AUTH/SPEC-AUTH-001/spec.yaml"); e = spec["versions"][0]
    assert e["analysis_policy"] == "analyze" and len(e["metadata_history"]) == 1 and e["metadata_history"][0]["op_id"] == op, (fault, e.get("metadata_history"))
    assert U.sha(pathlib.Path(root) / "specs/demo/AUTH/SPEC-AUTH-001/v1.0.md") == _T["legacy_md_sha"]                 # 版本內容不變

@pytest.mark.parametrize("entry", ENTRIES)
def test_spec_metadata_upgrade_abort_and_resume(entry):
    """AC-07-28（metadata upgrade：spec）：legacy spec 的 analysis_policy 補值在每個中止點中止，兩種入口續做；metadata_history 只有一筆、v1.0.md 不變。
    （驗收紀錄 P3：「metadata upgrade 的中止續做在 P6」。）"""
    root, _ = template("legacy_migrated", build_legacy_migrated)
    _T.setdefault("legacy_md_sha", U.sha(root / "specs/demo/AUTH/SPEC-AUTH-001/v1.0.md"))
    apply_every_point("legacy_migrated", build_legacy_migrated, SPEC_UP, entry, spec_up_business)

def clr_up_args(info):
    return ["clarification", "metadata", "upgrade", info["clr"], "--kind", "spec_question", "--question-id", "Q01", "--subject", "password.min_length",
            "--role-scope", "*", "--params", "{}", "--reason", "補答案範圍", "--by", "oscar"]

def clr_up_business(root, info, op, plan, fault):
    c = U.load(root, f"clarifications/demo/AUTH/{info['clr']}.yaml")
    assert (c["kind"], c["question_id"], c["subject"], c["role_scope"], c["params"]) == ("spec_question", "Q01", "password.min_length", ["*"], {}), fault
    assert [h["trigger"] for h in c["history"]].count("metadata_upgrade") == 1, fault
    assert c["answer_revisions"] == _T["legacy_clr_revs"] and c["status"] == "ANSWERED", fault                       # 答案、修訂、狀態不變

@pytest.mark.parametrize("entry", ENTRIES)
def test_clarification_metadata_upgrade_abort_and_resume(entry):
    """AC-07-28（metadata upgrade：clarification）：移轉後的 legacy CLR（rev 0 由移轉建立）補 kind／question_id／scope，在每個中止點中止、
    兩種入口續做；history 只有一筆 metadata_upgrade、answer_revisions 不變。"""
    root, info = template("legacy_migrated", build_legacy_migrated)
    _T.setdefault("legacy_clr_revs", U.load(root, f"clarifications/demo/AUTH/{info['clr']}.yaml")["answer_revisions"])
    apply_every_point("legacy_migrated", build_legacy_migrated, clr_up_args(info), entry, clr_up_business)

# ================================================================ applicability_add（AC-07-29 的 P6 收尾）
def build_appl():
    from tests import test_p2_sources as S
    root = S.mk(pathlib.Path(tempfile.mkdtemp(prefix="qaos-p6g1-src-"))); cid = S.scoped_clr(root)
    return root, {"cid": cid, "bh": S.basis_hash(root)}

def appl_args(info):
    return ["clarification", "applicability", "add", info["cid"], "--answer-rev", "0", "--requirement", "REQ-AUTH-002", "--subject", "password.min_length",
            "--role-scope", "*", "--params", "{}", "--target", "SPEC-A-001@1.0", "--rationale", "REQ-AUTH-002 的密碼下限同一題", "--by", "oscar", "--confirm-basis", info["bh"]]

D2_SCOPE = {"spec_id": "SPEC-A-001", "requirement_id": "REQ-AUTH-002", "subject": "password.min_length", "role_scope": ["*"], "params": {}}

def appl_business(root, info, op, plan, fault):
    from tests import test_p2_sources as S
    c = S.clr(root, info["cid"])
    assert len(c["applicability"]) == 1 and c["applicability"][0]["op_id"] == op and c["applicability"][0]["scope"]["requirement_id"] == "REQ-AUTH-002", fault
    rendered = py(root, f"from tools.qaos import clarification as C\nprint(json.dumps(C._render(C.load('{info['cid']}'))))")
    assert (pathlib.Path(root) / f"clarifications/demo/AUTH/{info['cid']}.md").read_text(encoding="utf-8") == rendered, fault   # 衍生輸出和 yaml 一致
    assert S.x16(root, S.cref(root, info["cid"], 0, "下限是 8 碼"), scope=D2_SCOPE) == [], fault                                 # 續做後的紀錄在下游生效

@pytest.mark.parametrize("entry", ENTRIES)
def test_applicability_add_every_point(entry):
    """AC-07-29（applicability_add，§16「P2 實作、P6 收尾」）：P2 的 test_ac_07_29_* 只在第 1 步中止、只斷言紀錄一筆。
    P6 收尾：每個中止點（FP-P1、FP-P2、每一步 FP-W、9k）兩種入口續做，加上 §18.4 的完整斷言（其他 op 被拒絕、事件／登錄／狀態紀錄不重複、
    計畫不變、post_state），衍生 .md 與 yaml 一致，而且續做寫入的適用紀錄在下游生效（X16：REQ-AUTH-002 的使用處由不成立變成成立）。"""
    from tests import test_p2_sources as S
    root, info = template("appl", build_appl)
    assert S.x16(root, S.cref(root, info["cid"], 0, "下限是 8 碼"), scope=D2_SCOPE) != []                       # 對照：加入之前 X16 不成立
    apply_every_point("appl", build_appl, appl_args(info), entry, appl_business)

# ================================================================ CLR 生命週期（AC-07-27、9x、9y、9aa、第 6 章 §8）
def build_a6():
    """完整 RA（RA-P1 → P2 → P3）：CLR INCORPORATED、run COMPLETED、TC ACTIVE。"""
    root = demo_root()
    ra = py(root, HDR + "print(json.dumps(P.full_ra()))")
    return root, ra

def a6_args(info):
    return ["clarification", "apply", info["cid"], "--path", "a6", "--landed-in", info["rid"], "--target", info["target"], "--keyword", "刪除",
            *sum((["--tc-conclusion", f"{t}=updated"] for t in info["tcs"]), []), "--impact-reviewed", "逐張確認", "--by", "oscar"]

def applied_business(path, prior=()):
    def check(root, info, op, plan, fault):
        c = next(U.load(root, p.relative_to(root).as_posix()) for p in pathlib.Path(root).glob(f"clarifications/*/*/{info['cid']}.yaml"))
        assert c["status"] == "APPLIED" and [l["type"] for l in c["landings"]] == [*prior, "applied"] and c["landings"][-1]["path"] == path, (fault, c["landings"])   # 9x
        assert [h["to_status"] for h in c["history"]].count("APPLIED") == 1 and c["landings"][-1]["op_id"] == op, fault
    return check

@pytest.mark.parametrize("entry", ENTRIES)
def test_apply_a6_every_point(entry):
    """AC-07-27（apply a6）、AC-07-9x（CLR 狀態寫入之後、landing 之前：同一檔一起寫出，見 test_p5_resume 的註解；續做後 landing 只有一筆）。"""
    _, info = template("a6", build_a6)
    apply_every_point("a6", build_a6, a6_args(info), entry, applied_business("a6", ("incorporated",)))

from tests.test_p5_paths import BUG                         # 已含 HDR：e4_clr、bug_run、bug_draft、bug_validate、reject_with

def build_a6b():
    """e4 的 CLR 已回答；兩個 spec-to-bug run 都以 reject 決議（條目 source 指向 CLR 最新 rev）COMPLETED（tests/test_p5_paths.py 的正式流程）。"""
    root = demo_root()
    out = py(root, BUG + """
rid0, cid = e4_clr()
entry = lambda src: [{"requirement_id": "REQ-DEMO-001", "question_id": "Q01", "outcome": "select_interpretation", "source": src, "rationale": "依 PM 回答，這不是 bug"}]
runs = []
for _ in range(2):
    b, evd = bug_run(); bd = bug_draft(b, evd); assert bug_validate(b, bd, evd, "AMBIGUITY")["result"] == "AMBIGUITY"
    apr = reject_with(b, entry(F.cref(cid, "任何站台都不能刪除"))); assert engine.load_run(b)["status"] == "COMPLETED"; runs.append([b, apr])
print(json.dumps({"cid": cid, "runs": runs}))""")
    return root, out

def a6b_args(info, i=0):
    b, apr = info["runs"][i]
    return ["clarification", "apply", info["cid"], "--path", "a6b", "--landed-in", b, "--target", f"{apr}#0", "--keyword", "刪除", "--impact-reviewed", "逐張確認", "--by", "oscar"]

@pytest.mark.parametrize("entry", ENTRIES)
def test_apply_a6b_every_point(entry):
    """AC-07-27（apply a6b，round-12 §5 新增）：a6b 在每個中止點中止，兩種入口續做；landing 只有一筆、path a6b、只轉 APPLIED 一次。"""
    _, info = template("a6b", build_a6b)
    apply_every_point("a6b", build_a6b, a6b_args(info), entry, applied_business("a6b"))

def build_noref():
    """沒有任何引用的 CLR：開單 → 回答 no_change（a7 的前置）。"""
    root = demo_root()
    cid = py(root, """
q = clr.new("demo", "DEMO", F.SPEC, F.VER, "子站台的排序要不要可設定？", "oscar", consulted=["SPEC-DEMO-001@1.0"], new_request=True)
clr.answer(q["clarification_id"], "維持現狀，不需要。", "pm", "no_change", "oscar", new_request=True)
print(json.dumps(q["clarification_id"]))""")
    return root, {"cid": cid}

def impact_args(info):
    return ["clarification", "impact", info["cid"], "--keyword", "排序", "--by", "oscar"]

def impact_business(root, info, op, plan, fault):
    c = U.load(root, f"clarifications/demo/DEMO/{info['cid']}.yaml"); assert len(c["scan_ids"]) == 1, fault
    scans = list(pathlib.Path(root).glob("clarifications/demo/DEMO/scans/*.yaml"))
    assert len(scans) == 1, (fault, scans)                                                                       # 9y：掃描紀錄只有一份

@pytest.mark.parametrize("entry", ENTRIES)
def test_9y_impact_every_point(entry):
    """AC-07-9y（impact 在掃描紀錄寫入之前中止 → 續做；掃描紀錄只有一份）、AC-07-27（impact）：
    除了每個 FP-W 點，另在掃描紀錄那一步的輸出之前（before_output）中止，兩種入口都做。"""
    _, info = template("noref", build_noref); args = impact_args(info)
    steps = reference_steps("noref", build_noref, args)
    scan = next(s["seq"] for s in steps if "/scans/" in s["path"])
    apply_every_point("noref", build_noref, args, entry, impact_business, named=[f"before_output:{scan}"])

def build_noref_scanned():
    root, info = build_noref()
    U.q(root, *impact_args(info), check=True)
    info["scan"] = U.load(root, f"clarifications/demo/DEMO/{info['cid']}.yaml")["scan_ids"][0]
    return root, info

def a7_args(info):
    return ["clarification", "apply", info["cid"], "--path", "a7", "--scan", info["scan"], "--impact-reviewed", "無影響", "--by", "oscar"]

@pytest.mark.parametrize("entry", ENTRIES)
def test_9aa_apply_a7_every_point(entry):
    """AC-07-9aa、AC-07-27（apply a7）：全部歷史掃描在擷取中完成、結果（reference_scan_sha256）由計畫固定；計畫保存後的每個中止點
    （FP-P2 = 掃描之後、任何寫入之前）兩種入口續做，landing 只有一筆且 reference_scan_sha256 等於計畫中的值。"""
    _, info = template("noref_scanned", build_noref_scanned); args = a7_args(info)
    def business(root, info, op, plan, fault):
        applied_business("a7")(root, info, op, plan, fault)
        land = U.load(root, f"clarifications/demo/DEMO/{info['cid']}.yaml")["landings"][-1]
        step = next(s for s in plan["steps"] if s["path"].endswith(f"{info['cid']}.yaml"))
        blob = yaml.safe_load((pathlib.Path(root) / f"operations/{plan['scope']}/{op}/blobs/{step['blob']}").read_text(encoding="utf-8"))
        assert land["reference_scan_sha256"] and land["reference_scan_sha256"] == blob["landings"][-1]["reference_scan_sha256"], fault
    apply_every_point("noref_scanned", build_noref_scanned, args, entry, business)

@pytest.mark.parametrize("entry", ENTRIES)
def test_9aa_state_changed_after_scan_stops(entry):
    """AC-07-9aa 的停止分支（竄改反例）：a7 計畫保存後中止；中止期間 CLR（計畫步驟的路徑）被改成既不是 before 也不是 after → 續做停止、不覆寫，
    計畫維持未完成，提示重新發出請求（以 --new-request）；模擬經授權的人工修復（恢復原內容）後續做完成。
    （正式流程中其他 op 在中止期間一律被 3b 拒絕，所以「歷史出現新的引用」只能以竄改模擬。）"""
    root, info = template("noref_scanned", build_noref_scanned); args = a7_args(info)
    op = abort(root, args, "after_register")
    p = pathlib.Path(root) / f"clarifications/demo/DEMO/{info['cid']}.yaml"; orig = p.read_bytes()
    p.write_bytes(orig + b"# external\n")
    before = U.snapshot(root)
    r = U.q(root, *args) if entry == "resend" else U.q(root, "operation", "resume", op)
    assert r.returncode != 0 and "外部修改" in r.stderr and "Traceback" not in r.stderr, r.stderr
    assert U.diff(before, U.snapshot(root)) == NOTHING and regs_of(root, op)[0]["statuses"] == set()
    p.write_bytes(orig)                                                                                     # 模擬經授權的人工修復
    cont(root, args, entry, op)
    check_post(root, op, U.sha(plan_file(root, op)))

def build_docs():
    """兩張文件索取單：CLR-A（REQ-DEMO-001）、CLR-B（REQ-DEMO-002），各缺兩項（D01 手冊、D02 角色與權限 spec）；
    已匯入並宣告兩份可名稱比對 D02 的文件 SPEC-ROLE-001（v02）、SPEC-ROLE-002（v03）。"""
    from tests.test_p5_documents import import_doc, TWO_MISSING
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="qaos-p6g1-src-")); root = _demo_root(tmp)
    import_doc(root, tmp, "SPEC-ROLE-001", filename="後台角色與權限_spec_v02.md")
    import_doc(root, tmp, "SPEC-ROLE-002", filename="後台角色與權限_spec_v03.md")
    req1 = TWO_MISSING.format(LEVEL="critical"); req2 = req1.replace("F.req(1,", "F.req(2,")
    out = py(root, HDR + f"""
res = []
for n, rq in ((1, lambda: {req1}), (2, lambda: {req2})):
    rid = F.new_run(); g = F.analyze(rid, [rq()]); assert g["result"] == "PASS", g
    c = [x for x in F.clrs(requirement_id=f"REQ-DEMO-{{n:03d}}") if x.get("kind") == "document_request"][-1]
    res.append([rid, c["clarification_id"], F.waiting(rid)])
print(json.dumps(res))""")
    pin = U.load(root, "specs/demo/DEMO/SPEC-DEMO-001/spec.yaml")["versions"][0]["content_hash"]
    return root, {"A": out[0][1], "B": out[1][1], "aprB": out[1][2], "pin": pin}

def fulfill_args(cid, item="D02", doc="SPEC-ROLE-001"):
    return ["clarification", "fulfill", cid, "--item", item, "--document", f"{doc}@1.0", "--by", "oscar"]

def doc(root, cid):
    return U.load(root, f"clarifications/demo/DEMO/{cid}.yaml")

@pytest.mark.parametrize("entry", ENTRIES)
def test_fulfill_and_waive_item_every_point(entry):
    """AC-07-27（fulfill、waive-item）：每個中止點兩種入口續做；fulfillment、waive_records 各只有一筆；waive-item 之後 A8 → APPLIED 一次。"""
    _, info = template("docs", build_docs)
    def f_business(root, info, op, plan, fault):
        c = doc(root, info["A"]); it = c["document_items"][1]
        assert c["status"] == "OPEN" and it["status"] == "fulfilled" and len(it["fulfillments"]) == 1, (fault, it)
    apply_every_point("docs", build_docs, fulfill_args(info["A"]), entry, f_business)
    def build_docs_fulfilled():
        root, inf = template("docs", build_docs); U.q(root, *fulfill_args(inf["A"]), check=True); return root, inf
    w_args = ["clarification", "waive-item", info["A"], "--item", "D01", "--reason", "手冊不再提供", "--by", "oscar"]
    def w_business(root, info, op, plan, fault):
        c = doc(root, info["A"])
        assert c["status"] == "APPLIED" and [l["path"] for l in c["landings"] if l["type"] == "applied"] == ["a8"], (fault, c["landings"])
        assert len(c["document_items"][0]["waive_records"]) == 1 and [h["to_status"] for h in c["history"]].count("APPLIED") == 1, fault
    apply_every_point("docs_fulfilled", build_docs_fulfilled, w_args, entry, w_business)

def a9_args(info):
    p = {"spec_id": "SPEC-DEMO-001", "spec_version": "1.0", "content_hash": info["pin"]}
    res = {"requirement_id": "REQ-DEMO-002", "question_id": "Q01", "outcome": "waive_missing", "rationale": "改向 PM 直接確認",
           "waived": [{"cited_at": {**p, "line": 13}, "name": "手冊 7.1.1 角色說明"}, {"cited_at": {**p, "line": 3}, "name": "後台角色與權限_spec_vNN.md"}]}
    return ["approve", info["aprB"], "--decision", "approve", "--by", "oscar", "--resolution", json.dumps(res, ensure_ascii=False)]

@pytest.mark.parametrize("entry", ENTRIES)
def test_approve_with_a9_every_point(entry):
    """AC-07-23（approve 不 apply、含 A9）、第 6 章 §8 恢復表「核准決議寫入之後、A9 之前中止」：每個中止點兩種入口續做；文件索取單只 WITHDRAWN 一次。"""
    _, info = template("docs", build_docs)
    def business(root, info, op, plan, fault):
        c = doc(root, info["B"])
        assert c["status"] == "WITHDRAWN" and [h["to_status"] for h in c["history"]].count("WITHDRAWN") == 1, (fault, c["history"])
        a = U.load(root, f"approvals/{info['aprB']}.yaml"); assert a["status"] == "DECIDED" and a["decision"]["decision"] == "approve", (fault, a["status"])
    apply_every_point("docs", build_docs, a9_args(info), entry, business)

# ================================================================ 操作身分（AC-07-13～18：op-P1、op-P2、op-N1～N6）
def test_op_p1_p2_fulfill_same_request():
    """AC-07-13（op-P1、op-P2，以 fulfill 驗收）：fulfill 中止後同參數重送 → 同一個 op 續做（不新增登錄）；完成後再以同參數執行 → 同一個 op，
    回報「已完成」，沒有任何寫入。"""
    root, info = template("docs", build_docs); args = fulfill_args(info["A"])
    op = abort(root, args, "after_output:1"); n = len(U.op_list(root))
    cont(root, args, "resend", op)
    assert len(U.op_list(root)) == n
    assert [o["op_id"] for o in U.op_list(root)][-1] == op and regs_of(root, op)[0]["statuses"] == {"completed"}          # op-P1
    before = U.snapshot(root)
    r = U.q(root, *args); assert r.returncode == 0 and "先前已完成的同一請求" in r.stderr, r.stderr                         # op-P2
    assert U.diff(before, U.snapshot(root)) == NOTHING and len(U.op_list(root)) == n
    assert len(doc(root, info["A"])["document_items"][1]["fulfillments"]) == 1

def test_op_n1_n2_fulfill_different_requests():
    """AC-07-14（op-N1：fulfill CLR-A 與 CLR-B 用同一份文件 → op 不同、各自處理；op-N2：CLR-A 先用文件 P1、再用文件 P2 → op 不同）。
    op 不同的證據：第一個請求中止時，第二個請求不是續做而是被 3b 拒絕並提示 resume 第一個 op；之後各自成為新的登錄紀錄。"""
    root, info = template("docs", build_docs)
    a1, b1, a2 = fulfill_args(info["A"]), fulfill_args(info["B"]), fulfill_args(info["A"], doc="SPEC-ROLE-002")
    op_a1 = abort(root, a1, "after_output:1")
    for other in (b1, a2):
        r = refused_without_writes(root, op_a1, other); assert op_a1 in r.stderr                                            # 不是同一個 op（否則會續做）
    cont(root, a1, "resume", op_a1)
    U.q(root, *b1, check=True); op_b1 = U.op_list(root)[-1]["op_id"]
    U.q(root, *a2, check=True); op_a2 = U.op_list(root)[-1]["op_id"]
    assert len({op_a1, op_b1, op_a2}) == 3
    assert [o["action"] for o in U.op_list(root)[-3:]] == ["clarification_fulfill"] * 3
    fa, fb = doc(root, info["A"])["document_items"][1]["fulfillments"], doc(root, info["B"])["document_items"][1]["fulfillments"]
    assert [f["document_pin"]["spec_id"] for f in fa] == ["SPEC-ROLE-001", "SPEC-ROLE-002"] and [f["document_pin"]["spec_id"] for f in fb] == ["SPEC-ROLE-001"]

def test_op_n3_n4_n5_apply():
    """AC-07-15（op-N3：apply CLR-A --landed-in RUN-1 與 --landed-in RUN-2 → op 不同）、AC-07-16（op-N4：apply 已完成，同參數加 --new-request →
    新 op；狀態檢查拒絕（已 APPLIED），沒有任何寫入）、AC-07-17（op-N5：有一份以 CLR-A 為 target 的未完成計畫時 answer CLR-A → 拒絕，提示 operation resume <op_id>）。"""
    root, info = template("a6b", build_a6b); cid = info["cid"]
    run1 = a6b_args(info, 0); run2 = [info["runs"][1][0] if a == info["runs"][0][0] else a for a in run1]   # 只有 --landed-in 不同
    op1 = abort(root, run1, "after_output:1")
    r = refused_without_writes(root, op1, run2); assert op1 in r.stderr                                                       # op-N3
    r = refused_without_writes(root, op1, ["clarification", "answer", cid, "--answer", "補充", "--answered-by", "pm", "--resolution", "requirement_clarified", "--by", "oscar"])
    assert f"operation resume" in r.stderr and op1 in r.stderr                                                              # op-N5
    cont(root, run1, "resend", op1)
    c = doc(root, cid); assert c["landings"][-1]["landed_in"] == [info["runs"][0][0]] and c["landings"][-1]["op_id"] == op1
    n = len(U.op_list(root)); before = U.snapshot(root)
    r = U.q(root, *run1); assert r.returncode == 0 and "先前已完成的同一請求" in r.stderr                                    # op-P2（apply）
    r = U.q(root, *run1, "--new-request"); assert r.returncode != 0 and "APPLIED" in r.stderr and "Traceback" not in r.stderr, r.stderr   # op-N4
    r = U.q(root, *run2); assert r.returncode != 0 and "APPLIED" in r.stderr                                                  # 不同 op、已 APPLIED → 拒絕
    assert U.diff(before, U.snapshot(root)) == NOTHING and len(U.op_list(root)) == n
    assert [l["type"] for l in doc(root, cid)["landings"]].count("applied") == 1

def test_op_n6_migrate_twice_in_s_maint():
    """AC-07-18（op-N6）：S_maint 中兩次 migrate，第一次中止 → 第二次（同參數）是同一個 op、續做完成，標記的 migrate_op_id 等於它；
    已有標記時，--new-request 的 migrate 被拒絕、沒有任何寫入。"""
    root, info = _legacy(); args = ["migrate", "--by", "m", "--acknowledge-idle", info["running"]]
    U.q(root, "maintenance", "start", "--by", "m", check=True)
    x = abort(root, args, "after_progress:6"); n = len(U.op_list(root))
    cont(root, args, "resend", x)
    assert x_of(root) == x and len(U.op_list(root)) == n and status_files(root, x) == ["completed"]
    before = U.snapshot(root)
    r = U.q(root, *args, "--new-request"); assert r.returncode != 0 and "Traceback" not in r.stderr, r.stderr
    assert U.diff(before, U.snapshot(root)) == NOTHING and len(U.op_list(root)) == n
    assert U.q(root, "migrate", "verify").returncode == 0

# ================================================================ migrate X 的中止與續做（AC-07-90、91；FP-M0～M5）
def _x_points(steps):
    seq = lambda pred: next(s["seq"] for s in steps if pred(s))
    marker = seq(lambda s: s["path"].endswith("_migration.yaml"))
    render = seq(lambda s: s["step_id"].startswith("render"))
    return {"FP-M0": "after_register", "FP-M1": f"after_progress:{seq(lambda s: s['step_id'] == 'backup2')}",
            "FP-M2": f"after_progress:{seq(lambda s: s['step_id'] == 's3')}", "FP-M3": f"after_progress:{marker}",
            "FP-M4": f"raise:before_output:{render}", "FP-M5": "before_completed"}

_MIG = {}
def _migrate_steps():
    if not _MIG:
        root, info = _legacy(); LG.migrate(root, "--acknowledge-idle", info["running"], check=True)
        _MIG["steps"] = U.plan_of(root, x_of(root))["steps"]
    return _MIG["steps"]

@pytest.mark.parametrize("point", ["FP-M0", "FP-M1", "FP-M2", "FP-M3", "FP-M4", "FP-M5"])
@pytest.mark.parametrize("entry", ENTRIES)
def test_migrate_x_abort_points_then_resume(point, entry):
    """AC-07-90（FP-M3、FP-M5；另以 FP-M0、FP-M2 確認從中段續做）、AC-07-91（FP-M4：render 失敗 → 計畫保持 in_progress，續做重建 →
    audit.log 開頭逐位元等於移轉前的原檔）、AC-09-71（FP-M1 的續做）。兩種入口續做；已寫的輸出（標記、事件、render 檔）不重寫（inode 與 sha 不變），
    status.d/<X>-completed 只有一個；中止期間 migrate --new-request、業務寫入、maintenance end 都被拒絕，只有 rollback 接管被允許（見 AC-07-92 的測試）。"""
    steps = _migrate_steps(); fault = _x_points(steps)[point]
    root, info = _legacy(); args = ["migrate", "--by", "m", "--acknowledge-idle", info["running"]]
    orig_log = (root / "runs/_audit.log").read_bytes()
    U.q(root, "maintenance", "start", "--by", "m", check=True)
    x = abort(root, args, fault, expect=1 if point == "FP-M4" else FAULT)
    plan = U.plan_of(root, x); psha = U.sha(plan_file(root, x))
    written = {s["path"]: (root / s["path"]).stat().st_ino for s in plan["steps"] if s["kind"] in ("business", "event") and s["expected_after"]
               and (root / s["path"]).exists() and U.sha(root / s["path"]) == s["expected_after"]}
    for other in (args + ["--new-request"], ["maintenance", "end", "--by", "m"],
                  ["clarification", "answer", info["open_clr"], "--answer", "鎖 5 分鐘", "--answered-by", "pm", "--resolution", "requirement_clarified", "--by", "o"]):
        before = U.snapshot(root); r = U.q(root, *other)
        assert r.returncode != 0 and "Traceback" not in r.stderr, (other, r.stderr); assert U.diff(before, U.snapshot(root)) == NOTHING, other
    cont(root, args, entry, x)
    for p, ino in written.items(): assert (root / p).stat().st_ino == ino, f"{p} 被重寫"
    assert U.sha(plan_file(root, x)) == psha and status_files(root, x) == ["completed"] and len(regs_of(root, x)) == 1
    assert events_of(root, x) == sorted(s["path"] for s in plan["steps"] if s["kind"] == "event")
    for s in plan["steps"]:
        if s["kind"] in ("business", "event"): assert U.sha(root / s["path"]) == s["expected_after"], s["path"]
    assert (root / "runs/_audit.log").read_bytes().startswith(orig_log)                                                 # AC-07-91
    assert U.q(root, "migrate", "verify").returncode == 0

def test_fp_m6_x_evidence_deleted_then_resume_stops():
    """FP-M6、AC-09-76（竄改）：X 中止在 FP-M2 之後，刪掉已完成步驟的完成紀錄、或改寫已寫的事件後續做 X → V5 停止，不重寫、不寫任何檔案（兩種入口）。"""
    for variant in ("progress_deleted", "output_tampered"):
        root, info = _legacy(); args = ["migrate", "--by", "m", "--acknowledge-idle", info["running"]]
        U.q(root, "maintenance", "start", "--by", "m", check=True)
        x = abort(root, args, "after_progress:6"); plan = U.plan_of(root, x)
        if variant == "progress_deleted":
            sorted((root / f"operations/_global/{x}/progress.d").glob("*.yaml"))[1].unlink()
        else:
            p = root / next(s["path"] for s in plan["steps"] if s["step_id"] == "s1"); p.write_bytes(p.read_bytes() + b"# tampered\n")
        before = U.snapshot(root)
        for cmd in (args, ["operation", "resume", x]):
            r = U.q(root, *cmd); assert r.returncode != 0 and ("證據衝突" in r.stderr or "外部修改" in r.stderr), (variant, r.stderr)
        assert U.diff(before, U.snapshot(root)) == NOTHING and status_files(root, x) == []

# ================================================================ rollback R（AC-07-92、93；FP-R0、R1、R2、R4）
@pytest.mark.parametrize("entry", ENTRIES)
def test_ac_07_92_rollback_of_unmarked_x_aborted_at_fp_r0(entry):
    """AC-07-92：X 中止在 FP-M2（還沒標記）→ rollback R 中止在 FP-R0（R 已建立、R1 還沒執行）。中止期間：重送 X、operation resume X 都被拒絕並提示續做 R；
    migrate rollback --op X --new-request 被拒絕；其他 op 被拒絕。兩種入口續做 R：status.d/<X>-aborted_for_rollback 只有一個，R 的計畫不變，verify --rolled-back 通過。"""
    root, info = _legacy(); x_args = ["migrate", "--by", "m", "--acknowledge-idle", info["running"]]
    U.q(root, "maintenance", "start", "--by", "m", check=True)
    x = abort(root, x_args, "after_progress:6")
    r_args = ["migrate", "rollback", "--op", x, "--by", "m"]
    assert U.q(root, *r_args, fault="after_register").returncode == FAULT
    rp = _r_plan(root); rid = rp["op_id"]; rsha = U.sha(plan_file(root, rid))
    assert not (root / "artifacts/requirements/_migration.yaml").exists() and status_files(root, x) == []
    for cmd in (x_args, ["operation", "resume", x]):
        before = U.snapshot(root); r = U.q(root, *cmd)
        assert r.returncode != 0 and rid in r.stderr and "接管" in r.stderr, (cmd, r.stderr); assert U.diff(before, U.snapshot(root)) == NOTHING
    for cmd in (r_args + ["--new-request"], list(OTHER), ["maintenance", "end", "--by", "m"]):
        before = U.snapshot(root); r = U.q(root, *cmd)
        assert r.returncode != 0 and "Traceback" not in r.stderr, (cmd, r.stderr); assert U.diff(before, U.snapshot(root)) == NOTHING, cmd
    cont(root, r_args, entry, rid)
    assert status_files(root, x) == ["aborted_for_rollback"] and status_files(root, rid) == ["completed"] and U.sha(plan_file(root, rid)) == rsha
    assert len(regs_of(root, rid)) == 1 and events_of(root, rid) == sorted(s["path"] for s in rp["steps"] if s["kind"] == "event")
    assert U.q(root, "migrate", "verify", "--rolled-back").returncode == 0

@pytest.mark.parametrize("point", ["FP-R1", "FP-R2"])
@pytest.mark.parametrize("entry", ENTRIES)
def test_ac_07_93_rollback_of_marked_in_progress_x(point, entry):
    """AC-07-93：X 已寫標記但未完成（FP-M3）→ R 中止在 FP-R1（restore 執行到一半）或 FP-R2（標記已移除、terminal 全部 before）→ 兩種入口續做完成；
    x_progress、later_ops_snapshot 不重算（R 計畫的 sha256 不變）；FP-R2 是在無標記的 S_maint 中續做；X 的 aborted_for_rollback 只有一個。
    （test_p3_migrate.py::test_rollback_abort_points_then_resume 涵蓋 X 已完成的情況。）"""
    steps = _migrate_steps()
    root, info = _legacy(); x_args = ["migrate", "--by", "m", "--acknowledge-idle", info["running"]]
    U.q(root, "maintenance", "start", "--by", "m", check=True)
    x = abort(root, x_args, _x_points(steps)["FP-M3"])
    r_args = ["migrate", "rollback", "--op", x, "--by", "m"]
    assert U.q(root, *r_args, fault="after_register").returncode == FAULT
    rp = _r_plan(root); rid = rp["op_id"]; rsha = U.sha(plan_file(root, rid))
    G = {g: [s for s in rp["steps"] if s.get("group") == g] for g in ("takeover", "restore", "marker", "terminal")}
    assert G["marker"] and G["restore"], [s["step_id"] for s in rp["steps"]]
    fault = f"after_progress:{G['restore'][min(1, len(G['restore']) - 1)]['seq']}" if point == "FP-R1" else f"after_progress:{G['marker'][0]['seq']}"
    assert U.q(root, "operation", "resume", rid, fault=fault).returncode == FAULT
    assert (root / "artifacts/requirements/_migration.yaml").exists() == (point == "FP-R1")
    done = {s["path"]: (root / s["path"]).stat().st_ino for s in G["takeover"] + G["restore"]
            if (root / f"operations/_global/{rid}/progress.d/{s['seq']:04d}-{s['step_id']}.yaml").exists() and (root / s["path"]).exists()}
    assert done
    assert not (root / G["terminal"][0]["path"]).exists()
    assert U.q(root, *x_args).returncode != 0 and U.q(root, "maintenance", "end", "--by", "m").returncode != 0
    cont(root, r_args, entry, rid)
    for p, ino in done.items(): assert (root / p).stat().st_ino == ino, f"{p}（已完成的步驟）被重寫"
    assert U.sha(plan_file(root, rid)) == rsha and U.plan_of(root, rid)["x_progress"] == rp["x_progress"] and U.plan_of(root, rid)["later_ops_snapshot"] == rp["later_ops_snapshot"]
    assert status_files(root, x) == ["aborted_for_rollback"] and status_files(root, rid) == ["completed"]
    assert U.q(root, "migrate", "verify", "--rolled-back").returncode == 0

@pytest.mark.parametrize("entry", ENTRIES)
def test_fp_r4_unprocessed_step_path_changed_stops_then_repair(entry):
    """FP-R4、AC-09-83（尚未處理的步驟路徑）：R 中止在 restore 中途；中止期間，還沒執行的 restore 步驟路徑被外部改動 → 續做停止（不覆寫、R 保持 in_progress、
    不寫終態、標記保留）；模擬經授權的人工修復（恢復成記錄值）後續做完成。（test_p3_migrate 已涵蓋 untouched 路徑在檢查 A／B 的停止。）"""
    root, info = _legacy(); LG.migrate(root, "--acknowledge-idle", info["running"], check=True); x = x_of(root)
    r_args = ["migrate", "rollback", "--op", x, "--by", "m"]
    assert U.q(root, *r_args, fault="after_register").returncode == FAULT
    rp = _r_plan(root); rid = rp["op_id"]; restore = [s for s in rp["steps"] if s.get("group") == "restore"]
    later = [s for s in restore[1:] if s["kind"] == "business" and (root / s["path"]).is_file()]
    assert later, [(s["step_id"], s["kind"], s["path"]) for s in restore]
    assert U.q(root, "operation", "resume", rid, fault=f"after_progress:{restore[0]['seq']}").returncode == FAULT
    p = root / later[-1]["path"]; orig = p.read_bytes(); p.write_bytes(orig + b"# external\n")                        # 外部改動：尚未處理的 restore 步驟路徑
    before = U.snapshot(root)
    r = U.q(root, *r_args) if entry == "resend" else U.q(root, "operation", "resume", rid)
    assert r.returncode != 0 and ("外部修改" in r.stderr or "V5" in r.stderr or "證據衝突" in r.stderr), r.stderr
    assert U.diff(before, U.snapshot(root)) == NOTHING and status_files(root, rid) == [] and status_files(root, x) == ["completed"]
    assert (root / "artifacts/requirements/_migration.yaml").exists()
    p.write_bytes(orig)                                                                                                  # 模擬經授權的人工修復
    cont(root, r_args, entry, rid)
    assert status_files(root, x) == ["completed", "rolled_back"] and U.q(root, "migrate", "verify", "--rolled-back").returncode == 0

# ================================================================ 9ab：fork 之後 executor 崩潰、子程序仍存活
FORK_CRASH = """
import os, sys, time, pathlib
from tools.qaos import operation as op
from tools.qaos.cli import main
d = pathlib.Path(sys.argv[1]); orig = op.fault
def fault(point):
    if point == "after_register":                       # 計畫已保存並登錄、第一步之前：fork 一個長時間存活的子程序，然後父程序崩潰
        pid = os.fork()
        if pid == 0:
            nul = os.open(os.devnull, os.O_RDWR)
            for fd in (0, 1, 2): os.dup2(nul, fd)       # 不佔住 harness 的輸出管線
            (d / "child.pid").write_text(str(os.getpid()))
            while not (d / "go").exists(): time.sleep(0.02)
            os._exit(0)
        while not (d / "child.pid").exists(): time.sleep(0.02)
        os._exit(86)
    orig(point)
op.fault = fault
main(sys.argv[2:])
"""

@pytest.mark.parametrize("entry", ENTRIES)
def test_9ab_fork_child_alive_after_executor_crash(entry, tmp_path):
    """AC-07-9ab：executor 在 fork 之後崩潰、子程序仍存活 → 子程序在 fork 時已關閉它那一份鎖 fd，鎖隨父程序結束而釋放；
    下一個請求依 9t'' 處理：其他 op 被拒絕並提示 resume；同一個 op 以兩種入口續做完成。（test_p1_lock_fork.py::test_77d 只驗沒有計畫時鎖可取得。）"""
    import subprocess, sys, os, signal
    from tests.test_p1_lock_fork import acquire_once
    root = U.mkroot(); args = ["spec", "import", str(U.FIXTURES / "SPEC-AUTH-001-v1.0.md"), "--spec-id", "SPEC-AUTH-001", "--version", "1.0",
                               "--product", "demo", "--area", "AUTH", "--by", "t"]
    d = tmp_path / "s"; d.mkdir(); script = tmp_path / "crash.py"; script.write_text(FORK_CRASH, encoding="utf-8")
    p = subprocess.run([sys.executable, str(script), str(d), *args], cwd=U.REPO, env=U.env_for(root), capture_output=True, text=True, timeout=60)
    assert p.returncode == FAULT, p.stderr
    child = int((d / "child.pid").read_text())
    try:
        os.kill(child, 0)                                                                                 # 前提：子程序仍存活
        assert acquire_once(root) == "ok"                                                                 # 鎖已釋放
        op = U.incomplete(root)[0]["op_id"]; psha = U.sha(plan_file(root, op))
        refused_without_writes(root, op, OTHER)                                                           # 其他 op 被拒絕
        os.kill(child, 0)
        cont(root, args, entry, op)                                                                       # 同 op 續做（子程序仍存活）
        check_post(root, op, psha)
    finally:
        (d / "go").write_text("1")
        for _ in range(250):
            try: os.kill(child, 0); __import__("time").sleep(0.02)
            except ProcessLookupError: break
        else: os.kill(child, signal.SIGKILL)
