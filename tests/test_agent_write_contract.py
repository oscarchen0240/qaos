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

# ---- REDPACKET 的 spec-to-testcase run 會插入風險抽查 task
def test_redpacket_run_gets_risk_review(monkeypatch):
    assert "REDPACKET" in _contract("tc-risk-reviewer")["applies_to_areas"]
    wf = yaml.safe_load((REPO / "workflows/spec-to-testcase.yaml").read_text(encoding="utf-8"))
    monkeypatch.setattr(store, "run_area", lambda inputs: inputs["area"])
    assert engine._risk_review_task_id(wf, {"area": "REDPACKET"}) == "T3RR"
    assert engine._risk_review_task_id(wf, {"area": "SITELIST"}) is None
