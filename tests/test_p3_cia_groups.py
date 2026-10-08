"""P3：CIA 候選完整性與 pin_groups 的恰好分割 G1～G8（需求 A 第 5 章 §9；AC-09-28～30、35～41）。

候選 TC 以正式流程建立：第一輪 spec-to-testcase 產生一批綁 R001 的 TC；宣告變動後重新分析得到 R002，再產生一批綁 R002 的 TC。
g_impact 以記憶體中的 run（帶 from、to 兩端 RMPin）呼叫，CIR 也在記憶體中組出（CIA agent 的新契約在 P4 落實）。"""
import json, copy, pytest
from tests import p1_util as U

SETUP = """
import json
from tests import p3_flow as F
from tools.qaos import engine, store, rm, gates
from tools.qaos.cli import main as cli
F.full()                                                                          # 第一批 TC 綁 R001
cli(["spec", "reference", "declare-empty", "SPEC-AUTH-001@1.0", "--reason", "x", "--by", "oscar"])
rid2 = F.new_run(); rmid2 = F.analyze(rid2); F.design_and_validate(rid2, rmid2, prefix="01BX5ZZKBKACTAV9WEVGEMMVR"); F.approve_pending(rid2)   # 第二批 TC 綁 R002
r001, r002 = rm.pin_of("SPEC-AUTH-001", "1.0", "R001"), rm.pin_of("SPEC-AUTH-001", "1.0", "R002")
"""

@pytest.fixture(scope="module")
def world():
    root = U.mkroot(); U.import_auth_spec(root)
    out = json.loads(U.py(root, SETUP + "c, _ = gates._cia_candidates('SPEC-AUTH-001'); print(json.dumps([r001, r002, sorted(t for t in c if c[t] == r001), sorted(t for t in c if c[t] == r002)]))").stdout.strip().splitlines()[-1])
    A[:], B[:] = out[2], out[3]
    assert len(A) >= 2 and len(B) >= 2
    return root, out[0], out[1]

def gate(root, cir, r001, r002):
    code = SETUP.split("F.full()")[0] + f"""
run = {{"run_id": "RUN-20260101-997", "requirement_model_revision": {r002!r}, "from_requirement_model_revision": {r001!r}}}
print(json.dumps(gates.g_impact(run, None, {{"ChangeImpactReport": {{"artifact_id": "ART-CIR-X", "payload": {cir!r}}}}})))"""
    return json.loads(U.py(root, code).stdout.strip().splitlines()[-1])

REQS = [f"REQ-AUTH-00{i}" for i in range(1, 5)]
A, B = [], []   # A 綁 R001、B 綁 R002（由 fixture 依正式流程的結果填入）

def good(r001, r002):
    diff = [{"requirement_id": r, "change": "unchanged"} for r in REQS]
    groups = [{"from_pin": r001, "testcase_ids": list(A), "requirement_diff": copy.deepcopy(diff)}, {"from_pin": r002, "testcase_ids": list(B), "requirement_diff": copy.deepcopy(diff)}]
    impact = [{"testcase_id": t, "active_version": 1, "impact": "unaffected", "reason": "-", "affected_requirement_ids": [], "pin_group_index": 0 if t in A else 1} for t in A + B]
    return {"change_impact_id": "CI-SPEC-AUTH-001-1.0-1.0", "spec_id": "SPEC-AUTH-001", "from_version": "1.0", "to_version": "1.0", "from_rm_revision": r001, "to_rm_revision": r002,
            "requirement_diff": copy.deepcopy(diff), "pin_groups": groups, "testcase_impact": impact,
            "summary": {"requirements_changed": 0, "requirements_added": 0, "requirements_removed": 0, "testcases_affected": 0, "testcases_obsolete": 0, "testcases_unaffected": len(A) + len(B)},
            "completeness": {"all_active_requirements_judged": True, "all_referencing_testcases_judged": True}}

def test_correct_partition_passes(world):
    root, r001, r002 = world
    assert gate(root, good(r001, r002), r001, r002) == []

def mutate(name, c, r001, r002):
    g = c["pin_groups"]; imp = c["testcase_impact"]
    if name == "ac35_missing_group": del g[0]                                                          # 只列一組，另一組的 TC 宣稱 unaffected
    elif name == "ac36_in_two_groups": g[1]["testcase_ids"].append(A[0])
    elif name == "ac37_wrong_group": g[0]["testcase_ids"].remove(A[0]); g[1]["testcase_ids"].append(A[0]); next(i for i in imp if i["testcase_id"] == A[0])["pin_group_index"] = 1
    elif name == "ac38_unknown_in_group": g[0]["testcase_ids"].append("TC-AUTH-099")
    elif name == "ac39_unknown_in_impact": imp.append(dict(imp[0], testcase_id="TC-AUTH-099"))
    elif name == "ac39_missing_in_impact": del imp[0]
    elif name == "ac40_empty_group": g.append({"from_pin": {**r001, "revision": "R003"}, "testcase_ids": [], "requirement_diff": []})
    elif name == "ac40_same_from_pin": g[1]["from_pin"] = r001
    elif name == "ac41_wrong_index": imp[0]["pin_group_index"] = 1
    elif name == "g7_diff_missing": g[0]["requirement_diff"] = g[0]["requirement_diff"][1:]
    elif name == "g7_diff_duplicate": g[0]["requirement_diff"].append(g[0]["requirement_diff"][0])
    elif name == "g8_bad_pin": g[0]["from_pin"] = {**r001, "sha256": "0" * 64}
    elif name == "to_pin_mismatch": c["to_rm_revision"] = r001
    return c

EXPECT = {"ac35_missing_group": "G2", "ac36_in_two_groups": "G2", "ac37_wrong_group": "G4", "ac38_unknown_in_group": "G2", "ac39_unknown_in_impact": "G5",
          "ac39_missing_in_impact": "G5", "ac40_empty_group": "G1", "ac40_same_from_pin": "G3", "ac41_wrong_index": "G6", "g7_diff_missing": "G7",
          "g7_diff_duplicate": "G7", "g8_bad_pin": "G8", "to_pin_mismatch": "to_rm_revision"}

@pytest.mark.parametrize("name", sorted(EXPECT))
def test_partition_violations_fail(name, world):
    root, r001, r002 = world
    issues = gate(root, mutate(name, good(r001, r002), r001, r002), r001, r002)
    assert any(i.startswith(EXPECT[name]) or EXPECT[name] in i for i in issues), (name, issues)

def test_candidates_include_every_active_tc_of_the_spec(world):
    """候選不論 spec_version、revision：只判 R001 那組（現行 gates.py 只看 from_version 的缺口）→ FAIL（AC-09-31 的機制）。"""
    root, r001, r002 = world
    c = good(r001, r002); c["pin_groups"] = c["pin_groups"][:1]; c["testcase_impact"] = [i for i in c["testcase_impact"] if i["testcase_id"] in A]
    issues = gate(root, c, r001, r002)
    assert any(i.startswith("G2") for i in issues) and any(i.startswith("G5") for i in issues)
