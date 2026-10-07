"""P3：RM revision、綁定、過時判定、_skip 優先序、沒有 T0 的流程、同版本 CIA、req accept-declaration（需求 A 第 5 章 §3～§8）。

每個案例使用獨立的暫存 root，以正式流程（spec import、run new、submit、gate、approve、spec reference、tc revise）建立狀態；
流程程式在 tests/p3_flow.py。legacy fixture（舊程式留下、沒有 revision 索引的 requirements.yaml）另外標示。"""
import json, pathlib, textwrap, yaml, pytest
from tests import p1_util as U

def py(root, body: str):
    code = "import json\nfrom tests import p3_flow as F\nfrom tools.qaos import engine, store, rm, gates, sources, tc_ops, operation\nfrom tests import helpers as H\n" + textwrap.dedent(body)
    return json.loads(U.py(root, code).stdout.strip().splitlines()[-1])

def root_with_auth():
    root = U.mkroot(); U.import_auth_spec(root); return root

def revs(root):
    return [e["revision"] for e in U.load(root, "artifacts/requirements/SPEC-AUTH-001/v1.0/revisions/index.yaml")["revisions"]]

def rev_bytes(root, rev):
    return (pathlib.Path(root) / f"artifacts/requirements/SPEC-AUTH-001/v1.0/revisions/{rev}.yaml").read_bytes()

def pin_of(root, rid, field="requirement_model_revision"):
    return (U.load(root, f"runs/{rid}/run.yaml").get(field) or {}).get("revision")

def current(root, rid):
    return U.load(root, f"runs/{rid}/run.yaml").get("current_task_id")

# ---------------------------------------------------------------- AC-09-1、2：重新分析產生 R(n+1)，舊 run 仍讀 R(n)
def test_ac_09_1_2_reanalysis_new_revision_and_old_run_keeps_its_pin():
    root = root_with_auth()
    out = py(root, """
rid1 = F.new_run(); F.analyze(rid1, crit=True)                     # R001：REQ-AUTH-002 有未解決的 critical → DRAFT
rid2 = F.new_run()                                                 # 最新 revision 有非 ACTIVE 需求 → 不跳過 T1
cur2 = engine.load_run(rid2)["current_task_id"]
F.analyze(rid2)                                                    # R002：全部 ACTIVE
tcs, _ = H.draft_set(); arts = {"TestCaseDraft": {"artifact_id": "ART-TCD-X", "payload": {"mode": "spec", "spec_id": "SPEC-AUTH-001", "spec_version": "1.0", "testcases": tcs}},
                               "TestDesignReport": {"artifact_id": "ART-TDR-X", "payload": H.design_report("ART-TCD-X", tcs)}}
g1 = gates.g_design(engine.load_run(rid1), None, arts); g2 = gates.g_design(engine.load_run(rid2), None, arts)
print(json.dumps([rid1, rid2, cur2, g1, g2]))""")
    rid1, rid2, cur2, g1, g2 = out
    assert cur2 == "T1" and revs(root) == ["R001", "R002"]
    assert pin_of(root, rid1) == "R001" and pin_of(root, rid2) == "R002"
    assert any("REQ-AUTH-002" in i and "非 ACTIVE" in i for i in g1)                                   # 舊 run 讀它綁定的 R001
    assert not any("非 ACTIVE" in i for i in g2)                                                        # 新 run 讀 R002
    assert U.load(root, "artifacts/requirements/SPEC-AUTH-001/v1.0/requirements.yaml")["revision"] == "R002"   # 檢視是最新 revision

def test_revision_files_are_immutable_and_indexed():
    root = root_with_auth()
    py(root, "rid = F.new_run(); F.analyze(rid, crit=True); print(json.dumps(rid))")
    r001 = rev_bytes(root, "R001"); idx0 = U.load(root, "artifacts/requirements/SPEC-AUTH-001/v1.0/revisions/index.yaml")["revisions"][0]
    py(root, "rid = F.new_run(); F.analyze(rid); print(json.dumps(rid))")
    assert rev_bytes(root, "R001") == r001                                                              # R(n) 位元不變
    idx = U.load(root, "artifacts/requirements/SPEC-AUTH-001/v1.0/revisions/index.yaml")["revisions"]
    assert idx[0] == idx0 and idx[1]["revision"] == "R002" and idx[1]["sha256"] == U.sha(pathlib.Path(root) / idx[1]["path"])
    doc = U.load(root, idx[1]["path"])
    assert doc["parent"] == "R001" and doc["target_decl_rev"] == 0 and doc["reference_pins"] == [] and doc["op_id"] and doc["run_id"].startswith("RUN-")

def test_tc_version_binds_run_revision():
    root = root_with_auth()
    rid = py(root, "print(json.dumps(F.full()))")
    tv = U.load(root, "testcases/versions/TC-AUTH-001/v1.yaml")
    assert tv["requirement_model_revision"] == U.load(root, f"runs/{rid}/run.yaml")["requirement_model_revision"]

# ---------------------------------------------------------------- 不退回讀可變的檢視
def test_no_fallback_to_view():
    root = root_with_auth()
    out = py(root, """
tcs, _ = H.draft_set(); arts = {"TestCaseDraft": {"artifact_id": "ART-TCD-X", "payload": {"mode": "spec", "spec_id": "SPEC-AUTH-001", "spec_version": "1.0", "testcases": tcs}},
                               "TestDesignReport": {"artifact_id": "ART-TDR-X", "payload": H.design_report("ART-TCD-X", tcs)}}
rid = F.full()
print(json.dumps(gates.g_design({"run_id": "RUN-20260101-998"}, None, arts)))""")
    assert out and "沒有綁定需求模型 revision" in out[0]

def test_save_requirements_refuses_unmigrated_legacy_view():
    root = root_with_auth()
    legacy = pathlib.Path(root) / "artifacts/requirements/SPEC-AUTH-001/v1.0/requirements.yaml"     # legacy fixture：舊程式留下、沒有 revision 索引
    legacy.parent.mkdir(parents=True); legacy.write_text("spec_id: SPEC-AUTH-001\nspec_version: '1.0'\nrequirements: []\n", encoding="utf-8")
    before = U.snapshot(root)
    r = U.py(root, """
from tests import p3_flow as F
rid = F.new_run()""", check=False)
    assert r.returncode == 0                                                                              # legacy 檢視存在但沒有索引 → 視為沒有 RM，不跳過
    r = U.py(root, """
from tests import p3_flow as F
from tools.qaos import engine
rid = [r for r in __import__('os').listdir(__import__('tools.qaos.store', fromlist=['ROOT']).ROOT / 'runs') if r.startswith('RUN-')][0]
F.analyze(rid)""", check=False)
    assert r.returncode != 0 and "未移轉的 legacy requirements.yaml" in r.stderr

# ---------------------------------------------------------------- _skip 優先序（§7）、宣告變動、accept-declaration（AC-09-7、86）
def test_skip_binds_latest_and_declaration_change_blocks_until_accepted():
    root = root_with_auth()
    py(root, "print(json.dumps(F.full()))")
    rid3 = py(root, "print(json.dumps(F.new_run()))")
    assert pin_of(root, rid3) == "R001" and current(root, rid3) == "T2"                                  # 5. 跳過，綁最新 revision
    assert "SKIP_TASK" in (pathlib.Path(root) / f"runs/{rid3}/audit.log").read_text()
    h0 = py(root, 'print(json.dumps(sources.basis_hash(sources.basis("SPEC-AUTH-001", "1.0"))))')
    U.q(root, "spec", "reference", "declare-empty", "SPEC-AUTH-001@1.0", "--reason", "AUTH 不引用其他文件", "--by", "oscar", check=True)
    o = py(root, 'print(json.dumps(rm.outdated(rm.latest_pin("SPEC-AUTH-001", "1.0"))))')
    assert o["declaration_changed"] and not o["decision_revised"] and "decl_rev 0 → 1" in o["details"][0]                  # AC-09-86
    assert py(root, 'print(json.dumps(sources.basis_hash(sources.basis("SPEC-AUTH-001", "1.0"))))') != h0
    rid4 = py(root, "print(json.dumps(F.new_run()))")
    assert current(root, rid4) == "T1" and not pin_of(root, rid4)                                       # 3. 不跳過
    r = U.q(root, "req", "accept-declaration", "SPEC-AUTH-001@1.0", "--rev", "R001", "--reason", "x", "--by", "agent-spec-analyst"); assert r.returncode != 0
    r = U.q(root, "req", "accept-declaration", "SPEC-AUTH-001@1.0", "--rev", "R009", "--reason", "x", "--by", "oscar"); assert r.returncode != 0 and "最新" in r.stderr
    U.q(root, "req", "accept-declaration", "SPEC-AUTH-001@1.0", "--rev", "R001", "--reason", "宣告沒有引用，需求不變", "--by", "oscar", check=True)
    r002 = U.load(root, "artifacts/requirements/SPEC-AUTH-001/v1.0/revisions/R002.yaml"); r001 = U.load(root, "artifacts/requirements/SPEC-AUTH-001/v1.0/revisions/R001.yaml")
    assert r002["accepted_without_analysis"] is True and r002["accepted_diff"] == {"added": [], "removed": [], "changed": []} and r002["target_decl_rev"] == 1
    assert r002["requirements"] == r001["requirements"]                                                  # 需求內容相同
    r = U.q(root, "req", "accept-declaration", "SPEC-AUTH-001@1.0", "--rev", "R002", "--reason", "x", "--by", "oscar", "--new-request")
    assert r.returncode != 0 and "沒有宣告變動" in r.stderr
    rid5 = py(root, "print(json.dumps(F.new_run()))")
    assert pin_of(root, rid5) == "R002" and current(root, rid5) == "T2"

def test_closure_changes_and_newer_versions(tmp_path):
    """AC-09-8：只匯入參考文件的新版本 → newer_available，不擋 _skip；AC-09-9：A→B normative，B 改宣告 C → A declaration_changed。"""
    root = root_with_auth()
    for sid, text in (("SPEC-B-001", "# B\n"), ("SPEC-C-001", "# C\n")):
        f = tmp_path / f"{sid}.md"; f.write_text(text, encoding="utf-8")
        U.q(root, "spec", "import", f, "--spec-id", sid, "--version", "1.0", "--product", "demo", "--area", "AUTH", "--by", "oscar", check=True)
    U.q(root, "spec", "reference", "add", "SPEC-AUTH-001@1.0", "--ref", "SPEC-B-001@1.0", "--role", "normative", "--by", "oscar", check=True)
    py(root, "print(json.dumps(F.full()))")
    meta = U.load(root, "artifacts/requirements/SPEC-AUTH-001/v1.0/revisions/R001.yaml")
    assert [n["spec_id"] for n in meta["reference_pins"]] == ["SPEC-B-001"] and meta["target_decl_rev"] == 1
    f = tmp_path / "b2.md"; f.write_text("# B 第二版\n", encoding="utf-8")
    U.q(root, "spec", "import", f, "--spec-id", "SPEC-B-001", "--version", "2.0", "--product", "demo", "--area", "AUTH", "--by", "oscar", check=True)
    o = py(root, 'print(json.dumps(rm.outdated(rm.latest_pin("SPEC-AUTH-001", "1.0"))))')
    assert o["newer_available"] and not o["declaration_changed"]
    rid = py(root, "print(json.dumps(F.new_run()))"); assert current(root, rid) == "T2"                  # 不擋 _skip
    U.q(root, "spec", "reference", "add", "SPEC-B-001@1.0", "--ref", "SPEC-C-001@1.0", "--role", "normative", "--by", "oscar", check=True)
    o = py(root, 'print(json.dumps(rm.outdated(rm.latest_pin("SPEC-AUTH-001", "1.0"))))')
    assert o["declaration_changed"] and any("SPEC-B-001@1.0 的 decl_rev 0 → 1" in d for d in o["details"]) and any("閉包組成改變" in d for d in o["details"])
    rid = py(root, "print(json.dumps(F.new_run()))"); assert current(root, rid) == "T1"

def test_legacy_view_without_revision_is_not_treated_as_r000():
    """移轉前（沒有索引）的 legacy 檢視不是 R000；§7 第 4 點的 legacy 例外只適用於移轉建立的 R000（P3 移轉測試另驗）。"""
    root = root_with_auth()
    out = py(root, 'print(json.dumps(rm.latest_pin("SPEC-AUTH-001", "1.0")))')
    assert out is None

# ---------------------------------------------------------------- 沒有 T0 的流程（§4.3；AC-09-21、22、23）
def test_testcase_revision_binds_latest_and_refuses_when_outdated():
    root = root_with_auth()
    py(root, "print(json.dumps(F.full()))")
    out = py(root, 'run = tc_ops.revise("TC-AUTH-001", "調整", "oscar@example.com", new_request=True); print(json.dumps([run["run_id"], run.get("requirement_model_revision"), run.get("testcase_pin")]))')
    assert out[1]["revision"] == "R001" and out[2]["revision"] == "R001"                                 # AC-09-21：new_run 時綁最新；舊 pin 一併記錄
    U.q(root, "run", "cancel", out[0], "--by", "oscar", check=True)
    U.q(root, "spec", "reference", "declare-empty", "SPEC-AUTH-001@1.0", "--reason", "x", "--by", "oscar", check=True)
    before = U.snapshot(root)
    r = U.py(root, 'from tools.qaos import tc_ops\ntc_ops.revise("TC-AUTH-001", "調整", "oscar@example.com", new_request=True)', check=False)
    assert r.returncode != 0 and "declaration_changed" in r.stderr                                        # AC-09-22
    assert U.diff(before, U.snapshot(root)) == {"added": [], "removed": [], "changed": []}

def test_ac_09_23_manual_without_spec_is_refused():
    root = root_with_auth()
    rec = U.q(root, "manual", "new", "--title", "t", "--product", "demo", "--area", "AUTH", "--step", "s", "--observed", "o", "--outcome", "pass", "--by", "oscar", check=True).stdout.split()[0]
    before = U.snapshot(root)
    r = U.q(root, "run", "new", "manual-test-to-regression", "--input", f"manual_record_id={rec}", "--by", "oscar")
    assert r.returncode != 0 and "沒有可分析的 spec" in r.stderr
    assert not list((pathlib.Path(root) / "runs").glob("RUN-*")) and U.diff(before, U.snapshot(root)) == {"added": [], "removed": [], "changed": []}   # 計數器不前進

def test_manual_with_spec_hint_binds_latest():
    root = root_with_auth()
    py(root, "print(json.dumps(F.full()))")
    rec = U.q(root, "manual", "new", "--title", "t", "--product", "demo", "--area", "AUTH", "--step", "s", "--observed", "o", "--outcome", "pass",
              "--spec-id", "SPEC-AUTH-001", "--spec-version", "1.0", "--by", "oscar", check=True).stdout.split()[0]
    rid = U.q(root, "run", "new", "manual-test-to-regression", "--input", f"manual_record_id={rec}", "--by", "oscar", check=True).stdout.split()[0]
    assert pin_of(root, rid) == "R001"

# ---------------------------------------------------------------- 同版本 CIA（§8；AC-09-16）
def test_ac_09_16_same_version_cia_requires_revision_and_matching_reason():
    root = root_with_auth()
    py(root, "print(json.dumps(F.full()))")
    base = ["run", "new", "spec-change-impact", "--input", "spec_id=SPEC-AUTH-001", "--input", "from_version=1.0", "--input", "to_version=1.0", "--by", "oscar"]
    for extra, msg in (([], "from_revision"), (["--input", "from_revision=R001"], "reason"), (["--input", "reason=declaration_changed"], "from_revision"),
                       (["--input", "from_revision=R009", "--input", "reason=declaration_changed"], "沒有 revision R009"),
                       (["--input", "from_revision=R001", "--input", "reason=declaration_changed"], "判定結果不是 declaration_changed")):
        r = U.q(root, *base, *extra); assert r.returncode != 0 and msg in r.stderr, (extra, r.stderr)
    assert len(list((pathlib.Path(root) / "runs").glob("RUN-*"))) == 1
    U.q(root, "spec", "reference", "declare-empty", "SPEC-AUTH-001@1.0", "--reason", "x", "--by", "oscar", check=True)
    r = U.q(root, *base, "--input", "from_revision=R001", "--input", "reason=decision_revised"); assert r.returncode != 0
    rid = U.q(root, *base, "--input", "from_revision=R001", "--input", "reason=declaration_changed", check=True).stdout.split()[0]
    assert pin_of(root, rid, "from_requirement_model_revision") == "R001" and current(root, rid) == "T0"   # 同版本時 T0 一定執行

# ---------------------------------------------------------------- run cancel（§10；AC-09-17、32）
def test_ac_09_17_32_run_cancel_cancels_all_pending_approvals_once():
    root = root_with_auth()
    rid = py(root, "rid = F.new_run(); rmid = F.analyze(rid); F.design_and_validate(rid, rmid); print(json.dumps(rid))")   # T4 核准單 PENDING
    apr = U.load(root, f"runs/{rid}/run.yaml")["waiting_on_approval_id"]; assert U.load(root, f"approvals/{apr}.yaml")["status"] == "PENDING"
    pin = U.load(root, f"runs/{rid}/run.yaml")["requirement_model_revision"]
    for _ in range(2): U.q(root, "run", "cancel", rid, "--by", "oscar", check=True)                      # 重送兩次
    run = U.load(root, f"runs/{rid}/run.yaml")
    assert run["status"] == "CANCELLED" and run["requirement_model_revision"] == pin                       # 已綁定的 revision 保留
    assert U.load(root, f"approvals/{apr}.yaml")["status"] == "CANCELLED"
    log = (pathlib.Path(root) / f"runs/{rid}/audit.log").read_text()
    assert log.count("CANCEL_RUN") == 1 and log.count(f"CANCEL_APPROVAL\t{apr}") == 1                      # 核准單只轉換一次、audit 不重複
