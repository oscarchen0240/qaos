"""agent 指示與契約：寫入一律由主 session 經 bin/qaos 執行；Validator 的 assumption 規則與需求 A §3.6 一致
（docs/phase3-shadow-test/2026-10-08-redpacket-shadow-test.md 待辦 #2、#4、#6、#10）。"""
import pathlib, yaml

REPO = pathlib.Path(__file__).resolve().parents[1]
AGENTS = ["bug-analyst", "bug-validator", "change-impact-analyst", "regression-curator",
          "spec-analyst", "tc-risk-reviewer", "test-designer", "test-validator"]

def _contract(name): return yaml.safe_load((REPO / f"agents/{name}.yaml").read_text(encoding="utf-8"))
def _md(name): return (REPO / f".claude/agents/qaos-{name}.md").read_text(encoding="utf-8")

def test_agents_do_not_submit_gate_or_commit():
    for name in AGENTS:
        assert any(f.startswith("自行執行 bin/qaos submit") and "git commit" in f for f in _contract(name)["forbidden_actions"]), name
        md = _md(name)
        assert "## 寫入與提交（由主 session 經 bin/qaos 執行）" in md and "NoExecutorContext" in md, name

def test_designer_no_longer_told_to_submit_or_store_save():
    md = _md("test-designer")
    assert "不要自己執行 `bin/qaos submit`、`bin/qaos gate`" in md
    assert "store.save(path" not in md and "寫完後用 `bin/qaos submit" not in md

def test_validator_assumption_rule_matches_3_6():
    rules = [r for r in _contract("test-validator")["responsibilities"] if r.startswith("檢查 assumptions[]")]
    assert len(rules) == 1 and "§3.6" in rules[0] and "不因未被 RESOLVE_AMBIGUITY 覆蓋而判 blocker" in rules[0]
    assert "不要因為 assumption 沒有被 RESOLVE_AMBIGUITY 覆蓋就判 blocker" in _md("test-validator")

def test_risk_reviewer_covers_redpacket():
    assert "REDPACKET" in _contract("tc-risk-reviewer")["applies_to_areas"]
