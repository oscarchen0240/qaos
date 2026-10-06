"""bugs/index.md 與每個 bugs/<product>/<area>/index.md 的總表。"""
from . import store, operation

@operation.operation("bug_index")
def build():
    all_rows = []
    for area_dir in store.list_dirs("bugs/*/*"):
        bugs = [store.load(p) for p in store.glob(f"{store.rel(area_dir)}/BUG-*.yaml")]
        if not bugs: continue
        prod, area = area_dir.parent.name, area_dir.name
        lines = [f"# Bugs — {prod} / {area}", "", f"- 更新：{store.now()[:10]}  · 共 {len(bugs)} 筆", "", "| ID | 狀態 | 嚴重度 | 優先級 | 標題 | 需求 | 核准 |", "|---|---|---|---|---|---|---|"]
        for b in bugs:
            lines.append(f"| [{b['bug_id']}]({b['bug_id']}.yaml) | {b['status']} | {b['severity']} | {b['priority']} | {b['title']} | {b['requirement_id']} | {b.get('approval_id', '')} |")
            all_rows.append((prod, area, b))
        store.write_derived(f"{store.rel(area_dir)}/index.md", "\n".join(lines) + "\n")
    lines = ["# Bug Repository 總索引", "", f"- 更新：{store.now()[:10]}  · 共 {len(all_rows)} 筆", "", "| 產品 / 功能 | ID | 狀態 | 嚴重度 | 標題 |", "|---|---|---|---|---|"]
    for prod, area, b in all_rows: lines.append(f"| [{prod}/{area}]({prod}/{area}/index.md) | {b['bug_id']} | {b['status']} | {b['severity']} | {b['title']} |")
    store.write_derived("bugs/index.md", "\n".join(lines) + "\n")
    return len(all_rows)
