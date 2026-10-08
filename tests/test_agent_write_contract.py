"""agent 寫入與契約（docs/phase3-shadow-test/2026-10-08-redpacket-shadow-test.md 待辦 #2、#4、#6、#10）：
agent 不經 executor 寫入，提交、關卡、正式 ID 由主 session 經 bin/qaos 執行；Validator 的 assumption 規則對齊需求 A §3.6；
REDPACKET 納入風險抽查。"""
import pathlib, yaml
import pytest
from tools.qaos import store, ids, engine

REPO = pathlib.Path(__file__).resolve().parents[1]
AGENTS = ["bug-analyst", "bug-validator", "change-impact-analyst", "regression-curator",
          "spec-analyst", "tc-risk-reviewer", "test-designer", "test-validator"]

def _contract(name): return yaml.safe_load((REPO / f"agents/{name}.yaml").read_text(encoding="utf-8"))
def _md(name): return (REPO / f".claude/agents/qaos-{name}.md").read_text(encoding="utf-8")

# ---- 指示所描述的寫法在沒有 executor 的環境可行，store 寫入函式則被拒
def test_agent_write_path_works_without_executor(tmp_path):
    counters = store.abspath(ids.COUNTERS)
    before = counters.read_bytes() if counters.exists() else None
    aid = ids.artifact_id("TestCaseDraft")
    assert aid.startswith("ART-TCD-") and (counters.read_bytes() if counters.exists() else None) == before   # ART 不寫計數器
    out = tmp_path / f"{aid}.yaml"; out.write_bytes(store.dump({"artifact_id": aid, "status": "DRAFT"}))
    assert yaml.safe_load(out.read_text(encoding="utf-8"))["artifact_id"] == aid
    for call in (lambda: store.save("artifacts/x.yaml", {}), lambda: store.write_text("artifacts/x.txt", "x"),
                 lambda: store.audit(None, "agent", "X"), lambda: ids.alloc("REQ", "DEMO")):
        with pytest.raises(store.NoExecutorContext): call()

# ---- 每個 agent 的契約與指示都禁止自行 submit／gate／commit，且不指示呼叫 store 寫入
@pytest.mark.parametrize("name", AGENTS)
def test_agent_forbids_self_submit_gate_commit(name):
    forbidden = " ".join(_contract(name)["forbidden_actions"])
    assert all(k in forbidden for k in ("bin/qaos submit", "gate", "git commit")), name
    md = _md(name)
    assert "NoExecutorContext" in md and "store.save(" not in md, name
    assert "寫完後用 `bin/qaos submit" not in md and "然後 `bin/qaos gate" not in md, name

def test_new_formal_ids_are_not_self_numbered():
    assert any("REQ／AC 正式 ID" in f and "不得猜號" in f for f in _contract("spec-analyst")["forbidden_actions"])
    for name in AGENTS:
        assert "照既有編號規則填寫" not in _md(name), name

# ---- Validator：E3～E5 的 exploratory 合法；已核准的 assumption 例外；舊 blanket blocker 不再出現
def test_validator_assumption_rule_matches_3_6():
    rule = " ".join(r for r in _contract("test-validator")["responsibilities"] if r.startswith("檢查 assumptions[]"))
    md = _md("test-validator")
    for text in (rule, md):
        assert "§3.6" in text and "E3～E5" in text and "resolved_by_approval" in text
        # 歷史核准例外只限原封沿用：核對被沿用版本、逐項有效決定、assumption 內容
        assert all(k in text for k in ("supersedes_testcase", "ACTIVATE_TESTCASE", "per_item", "batch_items", "requirement_id")), text[:60]
    assert "任何未被 ApprovalDecision(RESOLVE_AMBIGUITY) 覆蓋的假設 → blocker" not in rule
    gates_doc = (REPO / "docs/architecture/04-quality-gates.md").read_text(encoding="utf-8")
    assert "Validator 必須 FAIL 除非 Human 已決定" not in gates_doc and "§3.6" in gates_doc

# ---- 歷史核准例外的情境：以契約描述的三步核對（直接前版 → 沿 supersedes 鏈追溯原始核准 → 核准種類／狀態／逐項有效決定）
#      對照 repo 內 Runtime 實際產生的資料，確認合法傳承會通過、改寫內容或逐項 reject 會被擋（不模擬模型本身）
def _load(rel): return yaml.safe_load((REPO / rel).read_text(encoding="utf-8"))

def _resolved_assumption_ok(supersedes: dict, a: dict, load=_load) -> bool:
    key = lambda x: (x["text"], x["requirement_id"], x.get("resolved_by_approval"))
    tc, ver, apr_id = supersedes["testcase_id"], supersedes["version"], a.get("resolved_by_approval")
    apr = load(f"approvals/{apr_id}.yaml")
    if apr["type"] not in ("ACTIVATE_TESTCASE", "APPLY_CHANGE") or apr["status"] != "DECIDED": return False
    covered = {i["version"] for i in apr["batch_items"] if i["id"] == tc}
    while ver is not None:                                    # 1、2：直接前版起沿 supersedes 鏈，每一版都要保有同一筆
        v = load(f"testcases/versions/{tc}/v{ver}.yaml")
        if key(a) not in {key(x) for x in v.get("assumptions") or []}: return False
        if ver in covered: break
        ver = v.get("supersedes")
    else:
        return False
    per = {i["id"]: i["decision"] for i in apr["decision"].get("per_item") or []}   # 3：per_item 優先
    return per.get(tc, apr["decision"]["decision"]) in ("approve", "override")

def test_resolved_assumption_chain_rule_against_runtime_data():
    a054 = _load("testcases/versions/TC-DAILYREPORT-054/v3.yaml")["assumptions"][0]
    assert _resolved_assumption_ok({"testcase_id": "TC-DAILYREPORT-054", "version": 3}, a054)        # 第二次沿用，核准只涵蓋 v1
    a073 = _load("testcases/versions/TC-PLATFORMRULE-073/v1.yaml")["assumptions"][0]
    assert _resolved_assumption_ok({"testcase_id": "TC-PLATFORMRULE-073", "version": 1}, a073)       # APPLY_CHANGE 核准
    assert not _resolved_assumption_ok({"testcase_id": "TC-DAILYREPORT-054", "version": 3}, dict(a054, text="改寫過的假設"))
    # 整批 approve、逐項 reject：讓版本內容與核准 ID 都相符，只剩逐項決定不同
    v011 = _load("testcases/versions/TC-REDPACKET-011/v1.yaml")
    a011 = dict(v011["assumptions"][0], needs_human_confirmation=False, resolved_by_approval="APR-0194")
    patched = lambda rel: dict(v011, assumptions=[a011]) if rel == "testcases/versions/TC-REDPACKET-011/v1.yaml" else _load(rel)
    assert not _resolved_assumption_ok({"testcase_id": "TC-REDPACKET-011", "version": 1}, a011, patched)
    apr = _load("approvals/APR-0194.yaml")                                                          # 對照：拿掉逐項 reject 就會通過
    no_reject = lambda rel: dict(apr, decision=dict(apr["decision"], per_item=[])) if rel == "approvals/APR-0194.yaml" else patched(rel)
    assert _resolved_assumption_ok({"testcase_id": "TC-REDPACKET-011", "version": 1}, a011, no_reject)
    md = _md("test-validator")
    assert "APPLY_CHANGE" in md and "supersedes` 鏈" in md

# ---- REDPACKET 的 spec-to-testcase run 會插入風險抽查 task
def test_redpacket_run_gets_risk_review(monkeypatch):
    assert "REDPACKET" in _contract("tc-risk-reviewer")["applies_to_areas"]
    wf = yaml.safe_load((REPO / "workflows/spec-to-testcase.yaml").read_text(encoding="utf-8"))
    monkeypatch.setattr(store, "run_area", lambda inputs: inputs["area"])
    assert engine._risk_review_task_id(wf, {"area": "REDPACKET"}) == "T3RR"
    assert engine._risk_review_task_id(wf, {"area": "SITELIST"}) is None
