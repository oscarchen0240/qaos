"""JSON Schema 驗證（Draft 2020-12），含 $ref registry；可由檔案路徑推斷 schema。"""
import json, pathlib
from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from .store import ROOT

_registry = None
_cache: dict[str, Draft202012Validator] = {}

def registry() -> Registry:
    global _registry
    if _registry is None:
        r = Registry()
        for f in (ROOT / "schemas").rglob("*.json"):
            s = json.load(open(f, encoding="utf-8"))
            res = Resource.from_contents(s)
            r = r.with_resource(s["$id"], res)
            rel = f.relative_to(ROOT / "schemas").as_posix()
            r = r.with_resource(f"https://qaos.local/schemas/{rel}", res)
        _registry = r
    return _registry

def validator(rel: str) -> Draft202012Validator:
    if rel not in _cache:
        s = json.load(open(ROOT / "schemas" / rel, encoding="utf-8"))
        _cache[rel] = Draft202012Validator(s, registry=registry())
    return _cache[rel]

def errors(obj, rel: str) -> list[str]:
    return [f"{e.json_path}: {e.message}" for e in sorted(validator(rel).iter_errors(obj), key=lambda e: str(e.json_path))]

PATH_RULES = [
    ("testcases/versions/", "testcase/testcase-version.schema.json"),
    ("testcases/registry/_counters", None),
    ("testcases/registry/", "testcase/registry-pointer.schema.json"),
    ("testcases/manual/", "testcase/manual-test-record.schema.json"),
    ("testsuites/", "testcase/test-suite.schema.json"),
    ("bugs/", "bug/bug.schema.json"),
    ("clarifications/", "spec/clarification.schema.json"),
    ("executions/", "execution/test-execution.schema.json"),
    ("evidence/", "execution/evidence.schema.json"),
    ("approvals/", "approval/approval-request.schema.json"),
    ("artifacts/requirements/", "artifact/envelope.schema.json"),  # run 期 RequirementModel artifact；持久化 requirements.yaml 另行處理
    ("artifacts/", "artifact/envelope.schema.json"),
    ("runs/", "workflow/workflow-run.schema.json"),
    ("agents/", "agent/agent-contract.schema.json"),
    ("workflows/state-machines", None),
    ("workflows/", "workflow/workflow-definition.schema.json"),
]

def infer(path: str) -> str | None:
    rel = pathlib.Path(path).resolve().relative_to(ROOT).as_posix() if str(path).startswith("/") else str(path)
    if rel.endswith("requirements.yaml") and rel.startswith("artifacts/requirements/"):
        return "spec/requirements-file.schema.json"
    if rel.startswith("specs/") and rel.endswith("spec.yaml"):
        return "spec/spec.schema.json"
    for prefix, schema in PATH_RULES:
        if rel.startswith(prefix): return schema
    return None
