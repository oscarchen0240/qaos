"""requirements/<SPEC>-v<ver>.md：某 Spec 版本的 Requirement 人可讀清單（給 Human 檢查 Spec Analyst 的切法）。"""
from . import store, operation

def build(spec_id: str, spec_version: str) -> str:
    """唯讀：產生內容，不寫檔（`req-export --stdout` 用）。"""
    from . import clarification as clr
    doc = store.load(store.requirements_path(spec_id, spec_version)); reqs = doc["requirements"]
    answered = {}
    for c in clr.list_(open_only=False):
        if c["spec_id"] == spec_id and c.get("requirement_id") and c["status"] in ("ANSWERED", "APPLIED"): answered.setdefault(c["requirement_id"], []).append(c)
    spec = store.load(store.spec_dir(spec_id) / "spec.yaml")
    tcs = {}
    for ptr in store.glob("testcases/registry/TC-*.yaml"):
        d = store.load(ptr)
        for v in d["versions"]:
            t = store.load(store.tc_version_path(d["testcase_id"], v["version"]))
            if t["spec_id"] == spec_id:
                for r in t["requirement_ids"]: tcs.setdefault(r, []).append(f"{d['testcase_id']} v{v['version']}")
    lines = [f"# Requirements — {spec_id} v{spec_version}（{spec['title']}）", "", f"- 共 {len(reqs)} 條；由 Spec Analyst 自 spec 切分，每條附原文位置與引句，請檢查切法是否合理", "- 事實來源：`" + store.requirements_path(spec_id, spec_version) + "`", ""]
    for r in reqs:
        amb = r.get("ambiguity") or {}; rc = r.get("rejection_contract") or {}
        lines += [f"## {r['requirement_id']} {r.get('title', '')}", "", f"**需求**：{r['statement']}", "",
                  f"- 類型 {r['type']} · 行為 {r.get('behavior_kind', '—')} · 風險 {r.get('risk', '—')} · 狀態 {r['status']}",
                  f"- spec 位置：{r['spec_reference']['location']}" + (f"　引句：「{r['spec_reference']['quote']}」" if r['spec_reference'].get('quote') else ""),
                  "- 驗收條件："] + [f"  - {ac['ac_id'].split('-')[-1]}：給定 {ac['given']}；當 {ac['when']}；則 {ac['then']}" for ac in r["acceptance_criteria"]]
        if r.get("inputs"): lines.append("- 輸入：" + "；".join(f"{i['name']}（{i['type']}{'，必填' if i.get('required') else ''}{'，' + str(i['constraints']) if i.get('constraints') else ''}）" for i in r["inputs"]))
        if r.get("states"): lines.append("- 狀態轉換：" + "；".join(f"{s['from']}→{s['to']}（{s.get('trigger', '')}{'，不允許' if s.get('allowed') is False else ''}）" for s in r["states"]))
        if rc:
            if rc.get("defined"): lines.append(f"- 不符合時系統怎麼做：spec 有寫" + (f"——{rc['description']}" if rc.get("description") else ""))
            elif answered.get(r["requirement_id"]): lines.append(f"- 不符合時系統怎麼做：spec v{spec_version} 沒寫 → **PM 已回答**（見下）")
            else: lines.append(f"- 不符合時系統怎麼做：**spec 沒寫，尚未有 PM 回答**" + (f"——{rc['description']}" if rc.get("description") else ""))
        for c in answered.get(r["requirement_id"], []):
            lines.append(f"- ✅ PM 回答（{c['clarification_id']}）：{c['answer']}")
        if amb: lines.append(f"- ⚠ 歧義（{amb['level']}）：{amb['description']}" + (f"　可能解讀：{' / '.join(amb.get('options', []))}" if amb.get("options") else ""))
        lines.append(f"- 對應 TC：{', '.join(tcs.get(r['requirement_id'], [])) or '（尚無）'}"); lines.append("")
    return "\n".join(lines) + "\n"

@operation.operation("req_export")
def export(spec_id: str, spec_version: str) -> str:
    """寫檔：requirements/<spec>-v<ver>.md（衍生輸出）。"""
    p = f"requirements/{spec_id}-v{spec_version}.md"; store.write_derived(p, build(spec_id, spec_version)); return p
