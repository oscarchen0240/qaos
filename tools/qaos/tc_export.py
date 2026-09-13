"""testcases/<AREA>.md：某功能區的 Test Case 人可讀總表（給人看，不是事實來源）。"""
from . import store

def export(area: str) -> str:
    rows = []
    for ptr in sorted((store.ROOT / "testcases" / "registry").glob(f"TC-{area}-*.yaml")):
        d = store.load(ptr)
        for v in d["versions"]:
            tc = store.load(store.tc_version_path(d["testcase_id"], v["version"])); rows.append(tc)
    from . import refs as _refs
    titles = {}
    def req_title(rid):
        if rid not in titles:
            r, _ = _refs.find_requirement(rid); titles[rid] = f"{rid.split('-')[-1]} {r.get('title', '')}".strip() if r else rid
        return titles[rid]
    lines = [f"# Test Cases — {area}", "", f"- 共 {len(rows)} 條版本；更新 {store.now()[:10]}；事實來源為 `testcases/versions/`", "- 「需求」欄＝這條案例依據的 spec 規則（編號 + 名稱），完整條文見 `artifacts/requirements/<spec>/v<ver>/requirements.yaml`", "",
             "| ID | 版 | 狀態 | 優先 | 風險 | 類別 | 需求 | 標題 | 步驟 | 預期結果 |", "|---|---|---|---|---|---|---|---|---|---|"]
    for t in rows:
        cls = "exploratory" if t.get("assumptions") else "grounded"
        steps = "<br>".join(f"{s['n']}. {s['action']}" for s in t["steps"])
        exp = t["expected_result"] + ("".join(f"<br>⚠ 假設：{a['text']}" for a in t.get("assumptions", [])))
        lines.append(f"| {t['testcase_id']} | v{t['version']} | {t['status']} | {t['priority']} | {t['risk']} | {cls} | {'；'.join(req_title(r) for r in t['requirement_ids'])} | {t['title']} | {steps} | {exp} |")
    out = "\n".join(lines) + "\n"; p = store.ROOT / "testcases" / f"{area}.md"; p.write_text(out, encoding="utf-8"); return str(p.relative_to(store.ROOT))
