#!/usr/bin/env python3
"""Phase 1 自我檢查：
1. 所有 schemas/**/*.json 可被 Draft 2020-12 metaschema 接受
2. agents/*.yaml 符合 agent-contract schema，且 allowed_actions ⊆ action-registry、forbidden 不與 allowed 重疊
3. workflows/*.yaml 符合 workflow-definition schema，且引用的 agent / gate 存在
4. 每個 Agent Contract 的 allowed_actions 不含 system-only / reserved / forbidden 類 action
"""
import json, glob, sys, pathlib, yaml
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

ROOT = pathlib.Path(__file__).resolve().parents[1]
errors = []

# --- 1. metaschema check + registry for $ref resolution ---
registry = Registry()
schemas = {}
for f in sorted((ROOT / "schemas").rglob("*.json")):
    s = json.load(open(f))
    Draft202012Validator.check_schema(s)
    schemas[f] = s
    registry = registry.with_resource(s["$id"], Resource.from_contents(s))
    # 也用相對路徑註冊，讓 "../common/defs.schema.json" 之類的 $ref 能解析
    rel = f.relative_to(ROOT / "schemas").as_posix()
    registry = registry.with_resource(f"https://qaos.local/schemas/{rel}", Resource.from_contents(s))
print(f"[1] {len(schemas)} schemas pass Draft 2020-12 metaschema")

def validator(rel):
    s = json.load(open(ROOT / "schemas" / rel))
    return Draft202012Validator(s, registry=registry)

# --- 2. agents ---
actions = yaml.safe_load(open(ROOT / "permissions/action-registry.yaml"))["actions"]
action_by_id = {a["id"]: a for a in actions}
not_grantable = {a["id"] for a in actions if a["category"] in ("system", "forbidden") or a["phase"] in ("reserved", "never")}
runtime_only = {a["id"] for a in actions if a.get("constraint") == "runtime_only"}
agent_ids = set()
v = validator("agent/agent-contract.schema.json")
for f in sorted((ROOT / "agents").glob("*.yaml")):
    c = yaml.safe_load(open(f))
    agent_ids.add(c["id"])
    for e in v.iter_errors(c):
        errors.append(f"{f.name}: {e.json_path}: {e.message}")
    allowed = set(c["allowed_actions"])
    unknown = allowed - set(action_by_id)
    if unknown: errors.append(f"{f.name}: unknown actions {unknown}")
    bad = allowed & (not_grantable | runtime_only)
    if bad: errors.append(f"{f.name}: grants non-grantable actions {bad}")
    forb = {x for x in c["forbidden_actions"] if x in action_by_id}
    if forb & allowed: errors.append(f"{f.name}: forbidden ∩ allowed = {forb & allowed}")
print(f"[2] {len(agent_ids)} agent contracts checked")

# --- 3. workflows ---
gates = {"G-SPEC","G-DESIGN","G-TVAL","G-BVAL","G-IMPACT","G-COMPARE","G-REG","G-APPROVAL"}
v = validator("workflow/workflow-definition.schema.json")
n=0
for f in sorted(p for p in (ROOT / "workflows").glob("*.yaml") if p.name != "state-machines.yaml"):
    w = yaml.safe_load(open(f)); n+=1
    for e in v.iter_errors(w):
        errors.append(f"{f.name}: {e.json_path}: {e.message}")
    for a in w["agents"]:
        base = a.split("(")[0]
        if base not in agent_ids: errors.append(f"{f.name}: unknown agent {a}")
    for g in w["gates"]:
        if g.split("(")[0] not in gates: errors.append(f"{f.name}: unknown gate {g}")
    for t in w["tasks"]:
        if "agent" in t and t["agent"] not in agent_ids: errors.append(f"{f.name}: task {t['id']} unknown agent {t['agent']}")
        if "gate" in t and t["gate"].split(".")[0] not in gates: errors.append(f"{f.name}: task {t['id']} unknown gate {t['gate']}")
print(f"[3] {n} workflow definitions checked")

if errors:
    print("\nERRORS:"); [print(" -", e) for e in errors]; sys.exit(1)
print("\nALL CHECKS PASSED")
