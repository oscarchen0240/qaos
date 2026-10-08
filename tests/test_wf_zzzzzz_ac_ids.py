"""AC ID 推導規則（docs/architecture/02-data-model.md §5；B+ 調整版 v2 核心 1、1b、2）：
- G-SPEC 以 ac_id_issues 檢查：新 AC 必須是 AC-<AREA>-<所屬 REQ 序號><AC 序號>（從 1 起、不補 0）、序號大於歷史最大值；
  既有 AC 不得改掛 REQ；已刪除的 AC 不得重用；同一份 model 內不得重複；新增 AC 不得用舊 3 位數格式。
- 一條 REQ 有 10 個以上 AC：G-SPEC 不擋，寫 audit 與 gate_results 的 advisory 紀錄（D3）。
- bin/qaos id AC 一律拒絕，計數器不變（D2）。
- Spec Analyst 的派發包附 ac_seq_high_water（同 spec 所有版本、所有 revision，只計推導格式）；其他 agent 的派發包不帶。"""
import copy
import pytest
from tools.qaos import store, engine, gates, dispatch, ids, rm as rm_mod, schema
from tools.qaos.cli import main as cli
from tests import helpers as H

AREA, SPEC = "ACRULE", "SPEC-ACRULE-001"
S = {}

def _swap(obj):
    if isinstance(obj, dict): return {k: _swap(v) for k, v in obj.items()}
    if isinstance(obj, list): return [_swap(v) for v in obj]
    if isinstance(obj, str): return obj.replace("SPEC-AUTH-001", SPEC).replace("AUTH", AREA)
    return obj

def _ac(aid): return {"ac_id": aid, "given": "前提", "when": "操作", "then": "結果"}

def _rm(ver="1.0", req1_acs=None):
    rm = _swap(copy.deepcopy(H.requirement_model(spec_version=ver)))
    if req1_acs is not None: rm["requirements"][0]["acceptance_criteria"] = [_ac(a) for a in req1_acs]
    return rm

def _submit_t1(rid, rm, ver="1.0"):
    refs_ = [{"entity_type": "SpecVersion", "id": SPEC, "version": ver}]
    h = next(v for v in store.load(store.spec_dir(SPEC) / "spec.yaml")["versions"] if v["spec_version"] == ver)["content_hash"]
    sa = {"spec_id": SPEC, "spec_version": ver, "content_hash": h, "summary": "x", "scope": {"in_scope": [], "out_of_scope": []},
          "requirement_ids": [r["requirement_id"] for r in rm["requirements"]], "ambiguities": [], "constraints": [], "edge_case_candidates": [], "open_questions": []}
    _, p1 = H.write_artifact(rid, "T1", "agent-spec-analyst", "SpecAnalysis", sa, refs_, {"type": "SpecVersion", "ids": []}, "spec-analysis")
    _, p2 = H.write_artifact(rid, "T1", "agent-spec-analyst", "RequirementModel", rm, refs_, {"type": "SpecVersion", "ids": []}, "requirements")
    assert engine.submit(rid, "T1", str(p1))[0] and engine.submit(rid, "T1", str(p2))[0]
    return engine.evaluate_gate(rid, "T1")

def _packet(rid, task_id):
    run = engine.load_run(rid); return dispatch.current_packet(run, engine._task(run, task_id))

TEN = [f"AC-{AREA}-001{n}" for n in range(1, 11)]                     # 0011…00110：第 10 個是 …00110

def test_01_setup_and_new_spec_packet_has_empty_high_water(fixtures):
    for ver in ("1.0", "1.1"):
        cli(["spec", "import", str(fixtures / f"SPEC-AUTH-001-v{ver}.md"), "--spec-id", SPEC, "--version", ver, "--product", "demo", "--area", AREA, "--by", "oscar@example.com"])
    S["run"] = engine.new_run("spec-to-testcase", {"spec_id": SPEC, "spec_version": "1.0"}, "oscar@example.com", new_request=True)["run_id"]
    H.packet_sha(S["run"], "T1")
    pk = _packet(S["run"], "T1")
    assert pk["ac_seq_high_water"] == {} and schema.errors(pk, "workflow/dispatch-packet.schema.json") == []

def test_02_g_spec_rejects_ac_rule_violations_with_specific_messages():
    bad = _rm(req1_acs=[f"AC-{AREA}-0011", f"AC-{AREA}-0023", f"AC-{AREA}-00105", f"AC-{AREA}-777"])
    bad["requirements"][1]["acceptance_criteria"].append(_ac(f"AC-{AREA}-0011"))                  # 跨 REQ 重複
    r = _submit_t1(S["run"], bad)
    assert r["result"] == "FAIL"
    msg = "\n".join(r["issues"])
    assert f"AC-{AREA}-0023 不符合推導規則：REQ-{AREA}-001 的 AC 必須是 AC-{AREA}-001<AC 序號>" in msg       # 前綴不是所屬 REQ
    assert f"AC-{AREA}-00105 不符合推導規則" in msg                                                        # AC 序號補 0
    assert f"AC-{AREA}-777 不符合推導規則" in msg and "不可用舊 3 位數格式" in msg                         # 新增 AC 用舊格式
    assert f"AC-{AREA}-0011 重複：同時出現在 REQ-{AREA}-001 與 REQ-{AREA}-002" in msg
    assert len(r["issues"]) == 4, r["issues"]

def test_03_ten_acs_pass_with_advisory_before_structural_result():
    rid = S["run"]
    r = _submit_t1(rid, _rm(req1_acs=TEN))
    assert r["result"] == "PASS", r["issues"]
    g = engine._task(engine.load_run(rid), "T1")["gate_results"]
    adv, last = g[-2], g[-1]
    assert adv["layer"] == "advisory" and adv["result"] == "WARN" and f"REQ-{AREA}-001 有 10 個 AC" in adv["details"][0]
    assert last["layer"] == "structural" and last["result"] == "PASS"                                  # 最後一筆仍是本次判定
    acts = [store.load(p)["action"] for p in store.glob(f"runs/{rid}/audit.d/*.yaml")]
    assert "GATE_ADVISORY" in acts
    run = engine.load_run(rid)
    assert schema.errors(engine._task(run, "T1"), "workflow/task.schema.json") == []

def test_04_history_rules_on_rerun():
    """歷史：REQ-001 有 0011…00110（最大 10）、REQ-002 0021、REQ-003 0031、REQ-004 0041。"""
    reqs = lambda **over: _rm(req1_acs=over.get("req1", TEN))["requirements"]
    assert gates.ac_id_issues(SPEC, reqs()) == []                                                        # 原樣沿用
    assert gates.ac_id_issues(SPEC, reqs(req1=TEN + [f"AC-{AREA}-00111"])) == []                        # 新增取 11
    low = gates.ac_id_issues(SPEC, reqs(req1=TEN[:8] + [f"AC-{AREA}-0019"]))                            # 0019 已存在 → 沿用，不報
    assert low == []
    moved = _rm(req1_acs=TEN)["requirements"]; moved[1]["acceptance_criteria"].append(_ac(f"AC-{AREA}-0031"))
    moved[2]["acceptance_criteria"] = [_ac(f"AC-{AREA}-0032")]
    out = gates.ac_id_issues(SPEC, moved)
    assert any(f"AC-{AREA}-0031 在 {SPEC} 歷史上屬於 REQ-{AREA}-003，不能改掛到 REQ-{AREA}-002" in m for m in out)

def _save_rev(sid, ver, reqs):
    """以 rm.save_requirements（唯一的需求寫入點）經 executor 持久化一份新 revision（模擬一次重新分析的落地結果）。"""
    from tools.qaos import operation
    @operation.operation("test_save_requirements")
    def _go(): return rm_mod.save_requirements(sid, ver, reqs, reason="analysis", by="test", source_artifact_id=ids.artifact_id("RequirementModel"))
    return _go(new_request=True)

def _latest_reqs(sid, ver):
    return copy.deepcopy(store.load(rm_mod.index(sid, ver)[-1]["path"])["requirements"])

def test_05_deleted_sequence_cannot_be_reused_and_new_must_exceed_high_water():
    """新 revision 刪掉 0019、00110：已刪除的 AC 不得重用；新 AC 必須 > 歷史最大 10。"""
    reqs = _latest_reqs(SPEC, "1.0"); reqs[0]["acceptance_criteria"] = reqs[0]["acceptance_criteria"][:8]
    _save_rev(SPEC, "1.0", reqs)
    req1 = lambda acs: _rm(req1_acs=acs)["requirements"]
    out = gates.ac_id_issues(SPEC, req1(TEN[:8] + [f"AC-{AREA}-00110"]))
    assert len(out) == 1 and f"AC-{AREA}-00110 已從 {SPEC} 的最新 revision 刪除，序號不得重用；REQ-{AREA}-001 新增 AC 取 11 起" in out[0]
    assert gates.ac_id_issues(SPEC, req1(TEN[:8] + [f"AC-{AREA}-0019"]))[0].startswith(f"AC-{AREA}-0019 已從")
    assert gates.ac_id_issues(SPEC, req1(TEN[:8] + [f"AC-{AREA}-00111"])) == []
    assert rm_mod.ac_history(SPEC)["high_water"][f"REQ-{AREA}-001"] == 10

def test_06_high_water_spans_other_spec_versions_and_packet_matches():
    """1.1 還沒有任何 revision：歷史最大序號取自 1.0 的 revision；派發包的 ac_seq_high_water 與 G-SPEC 計算一致。"""
    rid = engine.new_run("spec-to-testcase", {"spec_id": SPEC, "spec_version": "1.1"}, "oscar@example.com", new_request=True)["run_id"]
    S["run11"] = rid
    H.packet_sha(rid, "T1")
    pk = _packet(rid, "T1")
    assert pk["ac_seq_high_water"] == {f"REQ-{AREA}-001": 10, f"REQ-{AREA}-002": 1, f"REQ-{AREA}-003": 1, f"REQ-{AREA}-004": 1}
    assert pk["ac_seq_high_water"] == dict(sorted(rm_mod.ac_history(SPEC)["high_water"].items()))
    out = gates.ac_id_issues(SPEC, _rm(ver="1.1", req1_acs=TEN[:8] + [f"AC-{AREA}-0019"])["requirements"])
    assert len(out) == 1 and "已從" in out[0]                                                             # 1.0 R002 已刪除 0019

def test_07_legacy_three_digit_ac_reused_as_is_but_new_ones_must_be_derived(fixtures):
    """舊格式（MEMBER 這類）：先持久化一份 3 位數 AC 的舊資料，重新分析時原樣沿用 → 通過；新增 3 位數 → FAIL；新增推導格式 → 通過。"""
    sid, area = "SPEC-ACLEG-001", "ACLEG"
    cli(["spec", "import", str(fixtures / "SPEC-AUTH-001-v1.0.md"), "--spec-id", sid, "--version", "1.0", "--product", "demo", "--area", area, "--by", "oscar@example.com"])
    tpl = _latest_reqs(SPEC, "1.0")[1]                                                                   # 已落地、符合 schema 的需求當範本
    legacy = {**tpl, "requirement_id": f"REQ-{area}-001", "spec_id": sid, "spec_version": "1.0",
              "acceptance_criteria": [{**tpl["acceptance_criteria"][0], "ac_id": f"AC-{area}-001"}, {**tpl["acceptance_criteria"][0], "ac_id": f"AC-{area}-002"}]}
    legacy["spec_reference"] = {**tpl["spec_reference"], "spec_id": sid}
    _save_rev(sid, "1.0", [legacy])
    with_ac = lambda extra: [{**legacy, "acceptance_criteria": legacy["acceptance_criteria"] + [_ac(extra)]}]
    assert gates.ac_id_issues(sid, [legacy]) == []
    new_old = gates.ac_id_issues(sid, with_ac(f"AC-{area}-003"))
    assert len(new_old) == 1 and "不可用舊 3 位數格式" in new_old[0]
    assert gates.ac_id_issues(sid, with_ac(f"AC-{area}-0011")) == []
    assert rm_mod.ac_history(sid)["high_water"] == {}                                                    # 舊 3 位數不計入

def test_08_non_spec_analyst_packets_have_no_high_water():
    """G-SPEC PASS 後 run 進到 T2：Test Designer 的派發包不帶 ac_seq_high_water。"""
    rid = S["run"]
    H.packet_sha(rid, "T2")
    assert "ac_seq_high_water" not in _packet(rid, "T2")

def test_09_id_ac_is_rejected_and_counter_unchanged():
    before = ids._load()["counters"].get(f"AC-{AREA}")
    ops_before = len(store.glob("operations/_global/*.yaml"))
    with pytest.raises(SystemExit) as e:
        cli(["id", "AC", "--area", AREA, "--new-request"])
    assert "AC 不由計數器配發" in str(e.value.code)
    assert len(store.glob("operations/_global/*.yaml")) == ops_before                                 # 進入操作前就拒絕，不留下操作紀錄
    with pytest.raises(ValueError, match="AC 不由計數器配發"):
        ids.alloc("AC", AREA)
    assert ids._load()["counters"].get(f"AC-{AREA}") == before
