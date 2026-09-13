"""bugs/index.md 與每個 bugs/<product>/<area>/index.md 的總表。"""
from . import store

def build():
    all_rows = []
    for area_dir in sorted(p for p in (store.ROOT / "bugs").glob("*/*") if p.is_dir()):
        bugs = [store.load(p) for p in sorted(area_dir.glob("BUG-*.yaml"))]
        if not bugs: continue
        prod, area = area_dir.parent.name, area_dir.name
        lines = [f"# Bugs — {prod} / {area}", "", f"- 更新：{store.now()[:10]}  · 共 {len(bugs)} 筆", "", "| ID | 狀態 | 嚴重度 | 優先級 | 標題 | 需求 | 核准 |", "|---|---|---|---|---|---|---|"]
        for b in bugs:
            lines.append(f"| [{b['bug_id']}]({b['bug_id']}.yaml) | {b['status']} | {b['severity']} | {b['priority']} | {b['title']} | {b['requirement_id']} | {b.get('approval_id', '')} |")
            all_rows.append((prod, area, b))
        (area_dir / "index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    lines = ["# Bug Repository 總索引", "", f"- 更新：{store.now()[:10]}  · 共 {len(all_rows)} 筆", "", "| 產品 / 功能 | ID | 狀態 | 嚴重度 | 標題 |", "|---|---|---|---|---|"]
    for prod, area, b in all_rows: lines.append(f"| [{prod}/{area}]({prod}/{area}/index.md) | {b['bug_id']} | {b['status']} | {b['severity']} | {b['title']} |")
    (store.ROOT / "bugs" / "index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(all_rows)
