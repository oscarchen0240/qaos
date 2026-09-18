import html as html_mod

import markdown
from fastapi import HTTPException

from .. import db
from . import outputs as out_svc


def _outputs_of(con, report_id: int) -> list[str]:
    return _normalize_keys([r["output_path"] for r in db.rows(con.execute(
        "SELECT output_path FROM report_outputs WHERE report_id=? ORDER BY rowid", (report_id,)))])


def get(report_id: int) -> dict:
    with db.connect() as con:
        r = db.one(con.execute("SELECT * FROM reports WHERE id=?", (report_id,)))
        if not r:
            raise HTTPException(404, "報告不存在")
        r["output_paths"] = _outputs_of(con, report_id)
        return r


def list_all() -> list[dict]:
    from . import autoreports
    autoreports.sync_outputs()
    with db.connect() as con:
        rs = db.rows(con.execute("SELECT id, title, summary, kind, source_key, auto_generated_at, created_at, updated_at FROM reports ORDER BY updated_at DESC"))
        for r in rs:
            r["output_paths"] = _outputs_of(con, r["id"])
        return rs


def _set_outputs(con, report_id: int, paths: list[str]):
    con.execute("DELETE FROM report_outputs WHERE report_id=?", (report_id,))
    for k in _normalize_keys(paths):
        con.execute("INSERT INTO report_outputs (report_id, output_path) VALUES (?,?)", (report_id, k))


def create(title: str, summary: str, body_md: str, output_paths: list[str]) -> dict:
    ts = db.now()
    with db.connect() as con:
        cur = con.execute("INSERT INTO reports (title, summary, body_md, created_at, updated_at) VALUES (?,?,?,?,?)",
                          (title, summary, body_md, ts, ts))
        _set_outputs(con, cur.lastrowid, output_paths)
        rid = cur.lastrowid
    return get(rid)


def update(report_id: int, data: dict) -> dict:
    get(report_id)
    with db.connect() as con:
        paths = data.pop("output_paths", None)
        if data:
            data["updated_at"] = db.now()
            sets = ", ".join(f"{k}=?" for k in data)
            con.execute(f"UPDATE reports SET {sets} WHERE id=?", (*data.values(), report_id))
        elif paths is not None:
            con.execute("UPDATE reports SET updated_at=? WHERE id=?", (db.now(), report_id))
        if paths is not None:
            _set_outputs(con, report_id, paths)
    return get(report_id)


def delete(report_id: int):
    get(report_id)
    with db.connect() as con:
        con.execute("DELETE FROM reports WHERE id=?", (report_id,))


def regenerate(report_id: int) -> dict:
    """手動重生自動段落（只對 kind=output）。"""
    from . import autoreports
    r = get(report_id)
    if r.get("kind") == "output" and r.get("source_key"):
        with db.connect() as con:
            con.execute("UPDATE reports SET auto_signature=NULL WHERE id=?", (report_id,))
        autoreports.sync_outputs()
    return get(report_id)


# ---- 由產出產生內文樣板 ----
def _normalize_keys(keys: list[str]) -> list[str]:
    """report_outputs 存群組 key；M2 初版存的是檔案路徑，讀取時轉成群組 key。"""
    out = []
    for k in keys:
        if "/" in k:
            k, _ = out_svc.group_key_of(k.rsplit("/", 1)[-1], k)
        if k not in out:
            out.append(k)
    return out


def _output_rows(keys: list[str]) -> list[dict]:
    by_key = {g["key"]: g for g in out_svc.scan()}
    return [by_key[k] for k in _normalize_keys(keys) if k in by_key]


def template(paths: list[str]) -> str:
    rows = _output_rows(paths)
    lines = ["## 摘要", "", "（在此填寫整體結論）", "", "## 引用產出", ""]
    for o in rows:
        m = o["meta"]
        lines.append(f"### {o['label']}")
        lines.append("")
        lines.append("- 檔案：" + "、".join(f"`{f['path']}`" for f in o["files"]))
        if m.get("case_count") is not None:
            lines.append(f"- 案例數：{m['case_count']}")
        if m.get("specs"):
            lines.append(f"- Spec：{', '.join(m['specs'])}")
        if m.get("priority"):
            lines.append("- 優先級：" + "、".join(f"{k} {v}" for k, v in m["priority"].items()))
        if m.get("exploratory") is not None:
            lines.append(f"- exploratory（含假設）：{m['exploratory']}")
        lines.append(f"- 產生時間：{o['modified_at']}")
        lines.append(f"- 審閱狀態：{o['review_status']}" + (f"；備註：{o['note']}" if o["note"] else ""))
        lines.append("")
    lines += ["## 發現與建議", "", "- ", ""]
    return "\n".join(lines)


# ---- 匯出 ----
def export_md(report_id: int) -> tuple[str, str]:
    r = get(report_id)
    rows = _output_rows(r["output_paths"])
    parts = [f"# {r['title']}", "", f"- 建立：{r['created_at']}", f"- 更新：{r['updated_at']}"]
    if r["summary"]:
        parts += ["", "> " + r["summary"].replace("\n", "\n> ")]
    if rows:
        parts += ["", "## 引用產出", "", "| 模組 | 檔案 | 案例數 | 產生時間 | 審閱 |", "|---|---|---|---|---|"]
        for o in rows:
            files = "<br>".join(f"`{f['path']}`" for f in o["files"])
            parts.append(f"| {o['label']} | {files} | {o['meta'].get('case_count') or '—'} | {o['modified_at']} | {o['review_status']} |")
    if r.get("auto_md"):
        parts += ["", r["auto_md"].rstrip(), ""]
    if r["body_md"].strip():
        parts += ["", "## 結論與備註", "", r["body_md"], ""]
    return f"report-{report_id}.md", "\n".join(parts)


def render_html(body_md: str) -> str:
    return markdown.markdown(body_md, extensions=["tables", "fenced_code", "sane_lists"])


def export_html(report_id: int) -> tuple[str, str]:
    r = get(report_id)
    rows = _output_rows(r["output_paths"])
    e = html_mod.escape
    refs = ""
    if rows:
        def files_html(o):
            return "<br>".join(f"<code>{e(f['path'])}</code>" for f in o["files"])
        trs = "".join(
            f"<tr><td>{e(o['label'])}</td><td>{files_html(o)}</td><td>{o['meta'].get('case_count') or '—'}</td>"
            f"<td>{e(o['modified_at'])}</td><td>{e(o['review_status'])}</td></tr>" for o in rows)
        refs = f"<h2>引用產出</h2><table><thead><tr><th>模組</th><th>檔案</th><th>案例數</th><th>產生時間</th><th>審閱</th></tr></thead><tbody>{trs}</tbody></table>"
    doc = f"""<!doctype html>
<html lang="zh-Hant"><head><meta charset="utf-8"><title>{e(r['title'])}</title>
<style>
body{{font-family:"IBM Plex Sans","Noto Sans TC",-apple-system,sans-serif;max-width:900px;margin:40px auto;padding:0 24px;color:#1c1f26;line-height:1.6}}
h1{{font-size:26px;margin-bottom:4px}} .meta{{color:#626a76;font-family:ui-monospace,monospace;font-size:12px}}
blockquote{{border-left:3px solid #2f4bd6;margin:16px 0;padding:6px 14px;background:#f3f5ff;color:#1f2f8f}}
table{{border-collapse:collapse;width:100%;font-size:13px}} th,td{{border:1px solid #e4e6e9;padding:6px 10px;text-align:left;vertical-align:top}} th{{background:#f6f6f3}}
code{{font-family:ui-monospace,monospace;font-size:12px;background:#f1f2f4;padding:1px 4px;border-radius:3px}}
</style></head><body>
<h1>{e(r['title'])}</h1>
<div class="meta">建立 {e(r['created_at'])} · 更新 {e(r['updated_at'])}</div>
{f'<blockquote>{e(r["summary"])}</blockquote>' if r['summary'] else ''}
{refs}
{render_html(r.get('auto_md') or '')}
{('<h2>結論與備註</h2>' + render_html(r['body_md'])) if r['body_md'].strip() else ''}
</body></html>"""
    return f"report-{report_id}.html", doc
