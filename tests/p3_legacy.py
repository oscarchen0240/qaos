"""P3 移轉測試的 legacy fixture：以需求 A 之前的程式（base commit 2e01d4b，`git archive` 匯出到系統暫存目錄，唯讀）
在暫存 root 上執行它自己的正式流程，產生「新程式部署前就存在」的資料：legacy requirements.yaml、沒有 pin 的 run／TC、
沒有 answer_revisions 的 CLR、追加式的 audit.log。這是 legacy fixture，不是對新程式業務狀態的手改。"""
import json, os, pathlib, subprocess, sys, tempfile
from tests import p1_util as U

BASE = "2e01d4b"
OLD = pathlib.Path(tempfile.gettempdir()) / f"qaos-base-{BASE}"

def old_checkout() -> pathlib.Path:
    if not (OLD / "tools/qaos/engine.py").exists():
        OLD.mkdir(parents=True, exist_ok=True)
        data = subprocess.run(["git", "-C", str(U.REPO), "archive", BASE, "tools", "tests"], capture_output=True, check=True).stdout
        subprocess.run(["tar", "-x", "-C", str(OLD)], input=data, check=True)
    return OLD

OLD_FLOW = r"""
import json
from tools.qaos import engine, store, clarification
from tools.qaos.cli import main as cli
from tests import helpers as H
BY = "oscar@example.com"; SPEC, VER = "SPEC-AUTH-001", "1.0"
cli(["spec", "import", "tests/fixtures/SPEC-AUTH-001-v1.0.md", "--spec-id", SPEC, "--version", VER, "--product", "demo", "--area", "AUTH", "--by", BY])
rid1 = engine.new_run("spec-to-testcase", {"spec_id": SPEC, "spec_version": VER}, BY)["run_id"]
rm = H.requirement_model(); refs_ = [{"entity_type": "SpecVersion", "id": SPEC, "version": VER}]
ch = store.load(store.spec_dir(SPEC) / "spec.yaml")["versions"][0]["content_hash"]
sa = {"spec_id": SPEC, "spec_version": VER, "content_hash": ch, "summary": "s", "scope": {"in_scope": ["x"], "out_of_scope": []},
      "requirement_ids": [r["requirement_id"] for r in rm["requirements"]], "ambiguities": [], "constraints": [], "edge_case_candidates": [], "open_questions": []}
_, p1 = H.write_artifact(rid1, "T1", "agent-spec-analyst", "SpecAnalysis", sa, refs_, {"type": "SpecVersion", "ids": [f"{SPEC}@{VER}"]}, "spec-analysis")
rmid, p2 = H.write_artifact(rid1, "T1", "agent-spec-analyst", "RequirementModel", rm, refs_, {"type": "SpecVersion", "ids": [f"{SPEC}@{VER}"]}, "requirements")
assert engine.submit(rid1, "T1", str(p1))[0] and engine.submit(rid1, "T1", str(p2))[0] and engine.evaluate_gate(rid1, "T1")["result"] == "PASS"
tcs, _ = H.draft_set()
refs2 = [{"entity_type": "Requirement", "id": r} for r in ["REQ-AUTH-001", "REQ-AUTH-002", "REQ-AUTH-003", "REQ-AUTH-004"]]
did, pd = H.write_artifact(rid1, "T2", "agent-test-designer", "TestCaseDraft", {"mode": "spec", "spec_id": SPEC, "spec_version": VER, "testcases": tcs}, refs2, {"type": "RequirementModel", "ids": [rmid]}, "test-design")
_, pr = H.write_artifact(rid1, "T2", "agent-test-designer", "TestDesignReport", H.design_report(did, tcs), [{"entity_type": "Artifact", "id": did}], {"type": "TestCaseDraft", "ids": [did]}, "test-design")
assert engine.submit(rid1, "T2", str(pd))[0] and engine.submit(rid1, "T2", str(pr))[0] and engine.evaluate_gate(rid1, "T2")["result"] == "PASS"
_, pv = H.write_artifact(rid1, "T3", "agent-test-validator", "TestValidationReport", H.validation_report(did, rmid, "PASS"),
                         [{"entity_type": "Artifact", "id": did}, {"entity_type": "Artifact", "id": rmid}], {"type": "TestCaseDraft", "ids": [did]}, "validation")
assert engine.submit(rid1, "T3", str(pv))[0] and engine.evaluate_gate(rid1, "T3")["result"] == "PASS"
engine.approve(engine.load_run(rid1)["waiting_on_approval_id"], "approve", BY)
rid2 = engine.new_run("spec-to-testcase", {"spec_id": SPEC, "spec_version": VER}, BY)["run_id"]      # 舊程式：RM 已存在 → 跳過 T1，T2 READY（RUNNING）
c = clarification.new("demo", "AUTH", SPEC, VER, "密碼下限是幾碼？", BY, requirement_id="REQ-AUTH-001")
clarification.answer(c["clarification_id"], "密碼下限 8 碼。", "pm@example.com", "requirement_clarified", BY)
c2 = clarification.new("demo", "AUTH", SPEC, VER, "登入失敗要不要鎖？", BY, requirement_id="REQ-AUTH-003")   # 未回答（沒有 rev 0）
print(json.dumps({"done": rid1, "running": rid2, "clr": c["clarification_id"], "open_clr": c2["clarification_id"],
                  "tcs": sorted(p.stem for p in (store.ROOT / "testcases/registry").glob("TC-*.yaml"))}))
"""

def legacy_root() -> tuple[pathlib.Path, dict]:
    """S_pre 的 root，含舊程式以正式流程產生的資料；回傳 (root, 摘要)。"""
    root = U.mkroot(migrated=False); old = old_checkout()
    env = {**os.environ, "QAOS_ROOT": str(root), "PYTHONDONTWRITEBYTECODE": "1"}
    r = subprocess.run([sys.executable, "-c", OLD_FLOW], cwd=old, env=env, capture_output=True, text=True, timeout=300)
    if r.returncode != 0: raise AssertionError(f"舊程式的 legacy 流程失敗：\n{r.stdout}\n{r.stderr}")
    return root, json.loads(r.stdout.strip().splitlines()[-1])

def migrate(root, *extra, check=True, fault=None):
    U.q(root, "maintenance", "start", "--by", "m", check=True)
    return U.q(root, "migrate", "--by", "m", *extra, check=check, fault=fault)
