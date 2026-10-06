"""EntityRef 解析：Structural Gate 用來確認 artifact.references 逐一存在。"""
from . import store

def find_requirement(req_id: str, spec_id: str | None = None, spec_version: str | None = None):
    pattern = f"{spec_id}/v{spec_version}/requirements.yaml" if spec_id and spec_version else "*/*/requirements.yaml"
    for p in store.glob(f"artifacts/requirements/{pattern}"):
        d = store.load(p)
        for r in d.get("requirements", []):
            if r["requirement_id"] == req_id: return r, p
    return None, None

def find_ac(ac_id: str):
    for p in store.glob("artifacts/requirements/*/*/requirements.yaml"):
        for r in store.load(p).get("requirements", []):
            for ac in r.get("acceptance_criteria", []):
                if ac["ac_id"] == ac_id: return ac, r
    return None, None

def resolve(ref: dict) -> str | None:
    """回傳 None 表示存在；否則回傳錯誤訊息。"""
    t, i, v = ref["entity_type"], ref["id"], ref.get("version")
    if t == "Spec":
        return None if store.spec_dir(i) else f"Spec {i} 不存在"
    if t == "SpecVersion":
        d = store.spec_dir(i)
        if not d: return f"Spec {i} 不存在"
        vs = [x["spec_version"] for x in store.load(d / "spec.yaml")["versions"]]
        return None if str(v) in vs else f"SpecVersion {i}@{v} 不存在（有：{vs}）"
    if t == "Requirement":
        r, _ = find_requirement(i); return None if r else f"Requirement {i} 尚未持久化（需 G-SPEC PASS）"
    if t == "AcceptanceCriterion":
        ac, _ = find_ac(i); return None if ac else f"AC {i} 不存在"
    if t == "TestCase":
        return None if store.exists(store.tc_pointer_path(i)) else f"TestCase {i} 不在 Registry"
    if t == "TestCaseVersion":
        return None if store.exists(store.tc_version_path(i, int(v))) else f"TestCaseVersion {i} v{v} 不存在"
    if t == "TestSuite":
        return None if store.find_suite(i) else f"TestSuite {i} 不存在"
    if t == "TestExecution":
        return None if store.find_execution(i) else f"TestExecution {i} 不存在"
    if t == "Evidence":
        p = store.find_evidence(i)
        if not p: return f"Evidence {i} 不存在"
        e = store.load(p); fp = e["uri"]
        if store.exists(fp):
            actual = store.sha256_file(fp)
            if e.get("inline_content") is not None and store.sha256_text(e["inline_content"]) != actual:
                return f"Evidence {i} 檔案與 inline_content 不一致（可能被竄改）"
        elif e.get("inline_content") is not None:
            actual = store.sha256_text(e["inline_content"])
        else:
            return f"Evidence {i} 的檔案 {e['uri']} 不存在"
        return None if actual == e["sha256"] else f"Evidence {i} sha256 不符（可能被替換）"
    if t == "Bug":
        return None if store.find_bug(i) else f"Bug {i} 不存在"
    if t == "Artifact":
        p = store.find_artifact(i)
        if not p: return f"Artifact {i} 不存在"
        a = store.load(p)
        return None if a["status"] == "VALID" else f"Artifact {i} 狀態為 {a['status']}，只有 VALID 可被引用"
    if t == "WorkflowRun":
        return None if store.exists(f"runs/{i}/run.yaml") else f"Run {i} 不存在"
    if t == "ApprovalRequest":
        return None if store.exists(f"approvals/{i}.yaml") else f"ApprovalRequest {i} 不存在"
    if t == "ManualTestRecord":
        return None if store.exists(f"testcases/manual/{i}.yaml") else f"ManualTestRecord {i} 不存在"
    if t == "Clarification":
        return None if store.find_clarification(i) else f"Clarification {i} 不存在"
    if t == "ChangeImpact":
        return None  # run 期 entity，由 run 目錄保存
    return f"未知 entity_type {t}"
