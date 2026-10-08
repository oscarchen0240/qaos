"""State machine 執行：只允許 workflows/state-machines.yaml 列出的轉換；每次轉換寫 history。"""
from . import store

_SM = None
def machines():
    global _SM
    if _SM is None: _SM = store.load("workflows/state-machines.yaml")["machines"]
    return _SM

class TransitionError(Exception): pass

def actor_class(by: str) -> str:
    if by == "system": return "system"
    if by.startswith("agent-"): return f"agent:{by}"
    return "human"

def check(machine: str, frm: str | None, to: str, by: str, obj: dict | None = None):
    m = machines()[machine]
    if frm is None:
        if to != m["initial"]: raise TransitionError(f"{machine}: 初始狀態必須是 {m['initial']}，不是 {to}")
        return {"from": None, "to": to}
    cls = actor_class(by)
    rules = [t for t in m["transitions"] if t["from"] == frm and t["to"] == to]
    if not rules: raise TransitionError(f"{machine}: 沒有 {frm} → {to} 這條轉換")
    kind = (obj or {}).get("kind", "spec_question")                        # 轉換可限定 kind（例如 CLR 的 A9 只限 document_request）
    for t in rules:
        allowed = t["by"]
        if (cls in allowed or (cls.startswith("agent:") and "agent" in allowed)) and ("kinds" not in t or kind in t["kinds"]): return t
    raise TransitionError(f"{machine}: {frm} → {to} 不允許由 {by}" + (f"（kind {kind}）" if any("kinds" in t for t in rules) else "") + f"（允許：{[(t['by'], t.get('kinds')) for t in rules]}）")

def apply(machine: str, obj: dict, to: str, by: str, trigger: str, run_id: str | None = None, note: str = "", status_key: str = "status"):
    frm = obj.get(status_key)
    rule = check(machine, frm, to, by, obj)
    obj[status_key] = to
    entry = {"at": store.now(), "from_status": frm, "to_status": to, "by": by, "trigger": trigger}
    if run_id: entry["run_id"] = run_id
    if note: entry["note"] = note
    obj.setdefault("history", []).append(entry)
    if "updated_at" in obj or machine in ("testcase", "bug"): obj["updated_at"] = store.now()
    return rule
