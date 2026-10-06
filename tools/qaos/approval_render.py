"""ApprovalRequest → 人可讀 Markdown（approvals/<id>.md）。"""
from . import store, operation

@operation.operation("approval_render")
def render(apr_id: str) -> str:
    a = store.load(f"approvals/{apr_id}.yaml"); lines = [f"# {apr_id} · {a['type']}", "", f"- Run：{a['run_id']}  · 狀態：{a['status']}  · 提出：{a['requested_at'][:10]}", f"- **{a['summary']}**", ""]
    if a["type"] in ("ACTIVATE_TESTCASE", "APPLY_CHANGE") and a.get("batch_items"):
        from . import refs as _refs, clarification as clr
        answered = {}
        for c in clr.list_(open_only=False):
            if c.get("requirement_id") and c["status"] in ("ANSWERED", "APPLIED"): answered.setdefault(c["requirement_id"], []).append(c)
        def req_title(rid):
            r, _ = _refs.find_requirement(rid); return (f"{rid} {r.get('title', '')}".strip(), r) if r else (rid, None)
        groups = {}; exp = []
        for it in a["batch_items"]:
            v = store.load(store.tc_version_path(it["id"], it["version"])); groups.setdefault(v["requirement_ids"][0], []).append((it, v))
            if v.get("assumptions"): exp.append((it["id"], v))
        n_exp = len(exp); n_all = len(a["batch_items"])
        lines += ["## 這批要核准的 Test Case", "", f"- 共 {n_all} 條：**grounded {n_all - n_exp} 條**（預期結果有 spec 條文依據）、**⚠ exploratory {n_exp} 條**（預期結果含假設，approve 即接受該假設；假設下方附 PM 回答）",
                  "- 依「需求」分組；每組先列該需求的 spec 原文位置", "- 退回個別案例：`--per-item TC-xxx:reject`", ""]
        for rid, items in groups.items():
            title, r = req_title(rid)
            lines += [f"### {title}", ""]
            if r: lines += [f"> spec：{r['spec_reference']['location']}" + (f"　「{r['spec_reference']['quote']}」" if r['spec_reference'].get('quote') else "") + f"　· 風險 {r.get('risk', '—')}", ""]
            lines += ["| TC | 類別 | 標題 | 前置條件 | 步驟 | 預期結果 | 優先/風險 |", "|---|---|---|---|---|---|---|"]
            for it, v in items:
                cls = "⚠ exploratory" if v.get("assumptions") else "grounded"
                pre = "<br>".join(v["preconditions"]) or "—"; steps = "<br>".join(f"{st['n']}. {st['action']}" for st in v["steps"])
                expct = v["expected_result"]
                for a_ in v.get("assumptions", []):
                    expct += f"<br>⚠ 假設：{a_['text']}"
                    for c in answered.get(a_["requirement_id"], []): expct += f"<br>✅ PM（{c['clarification_id']}）：{c['answer'][:140]}…" if len(c['answer']) > 140 else f"<br>✅ PM（{c['clarification_id']}）：{c['answer']}"
                lines.append(f"| {it['id']} v{it['version']} | {cls} | {v['title']} | {pre} | {steps} | {expct} | {v['priority']}/{v['risk']} |")
            lines.append("")
    if a["type"] == "OPEN_BUG":
        lines += ["## 內容", ""]
        bd = None
        for aid in a.get("artifact_ids", []):
            art = store.load(store.find_artifact(aid))
            if art["artifact_type"] == "BugValidationReport":
                bd = store.load(store.find_artifact(art["payload"]["bug_draft_artifact_id"]))["payload"]; break
            if art["artifact_type"] == "BugDraft": bd = art["payload"]; break
        if bd:
            lines += [f"- **產品/功能**：{bd['product']} / {bd['functional_area']}　· **Spec**：{bd['spec_id']}@{bd['spec_version']}　· **需求**：{bd['requirement_id']}",
                      f"- **環境**：{bd['environment'].get('name', '—')}　· **測試帳號**：{bd['environment'].get('account', '—')}", ""]
            lines += ["**前置條件**"] + [f"- {p}" for p in bd["preconditions"]] + [""]
            lines += ["**重現步驟**"] + [f"{i+1}. {s}" for i, s in enumerate(bd["reproduction_steps"])] + [""]
            lines += [f"**預期結果**：{bd['expected_result']}", "", f"**實際結果**：{bd['actual_result']}", ""]
            if bd.get("actual_result_evidence_map"):
                lines += ["**證據對照**"] + [f"- {m['claim']}（{m['evidence_id']}）" for m in bd["actual_result_evidence_map"]] + [""]
            lines += [f"**影響**：{bd['impact']}", "", f"**懷疑方向**：{bd['suspected_area']}", ""]
        else:
            lines += [a.get("diff_summary", "（無法載入 BugDraft 內容）")]
    if a.get("artifact_ids"):
        lines += ["", "## 依據 artifact", ""] + [f"- {x}" for x in a["artifact_ids"]]
    lines += ["", "## 決定", "", f"```bash", f"bin/qaos approve {apr_id} --decision approve --by <you>", f"bin/qaos approve {apr_id} --decision approve --by <you> --per-item TC-xxx-001:reject", f"bin/qaos approve {apr_id} --decision reject --by <you> --rationale \"...\"", "```"]
    if a.get("decision"): lines += ["", f"**已決定：{a['decision']['decision']}** by {a['decision']['decided_by']} @ {a['decision']['decided_at']}"]
    out = "\n".join(lines) + "\n"; store.write_derived(f"approvals/{apr_id}.md", out); return out


@operation.operation("approval_render_html")
def render_html(apr_id: str) -> str:
    """approvals/<id>.html：固定欄寬、統一字級的審批頁（給人看；md 仍是文字版）。"""
    import html as H
    from . import refs as _refs, clarification as clr
    a = store.load(f"approvals/{apr_id}.yaml")
    answered = {}
    for c in clr.list_(open_only=False):
        if c.get("requirement_id") and c["status"] in ("ANSWERED", "APPLIED"): answered.setdefault(c["requirement_id"], []).append(c)
    css = """<style>
:root{--ink:#1c2326;--muted:#6b7674;--line:#d9dfdc;--bg:#f7f8f7;--head:#eef2f0;--exp:#fff7e0;--acc:#0e6b5f}
@media(prefers-color-scheme:dark){:root:not([data-theme=light]){--ink:#e4e9e7;--muted:#98a4a1;--line:#2c3538;--bg:#141819;--head:#1e2527;--exp:#3a3012;--acc:#4fb9a9}}
:root[data-theme=dark]{--ink:#e4e9e7;--muted:#98a4a1;--line:#2c3538;--bg:#141819;--head:#1e2527;--exp:#3a3012;--acc:#4fb9a9}
body{margin:0;padding:28px 32px 80px;background:var(--bg);color:var(--ink);font:14px/1.55 "IBM Plex Sans","PingFang TC","Noto Sans TC",system-ui,sans-serif}
h1{font-size:22px;margin:0 0 6px}h2{font-size:17px;margin:32px 0 8px;padding-top:14px;border-top:1px solid var(--line)}
.meta{color:var(--muted);margin-bottom:4px}.summary{margin:10px 0 18px;padding:10px 14px;border-left:3px solid var(--acc);background:var(--head)}
blockquote{margin:0 0 8px;color:var(--muted);font-size:13px}
table{width:100%;table-layout:fixed;border-collapse:collapse;font-size:13px;margin-bottom:6px}
th,td{border:1px solid var(--line);padding:7px 8px;vertical-align:top;text-align:left;word-break:break-word}
th{background:var(--head);font-weight:600;font-size:12.5px}
col.c-id{width:5.5%}col.c-cls{width:6%}col.c-title{width:15%}col.c-pre{width:17%}col.c-steps{width:24%}col.c-exp{width:26%}col.c-pr{width:6.5%}
tr.exp td{background:var(--exp)}.id{font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:12px}
ol{margin:0;padding-left:18px}.assume{margin-top:6px;padding-top:6px;border-top:1px dashed var(--line);font-size:12.5px}.pm{color:var(--acc)}
.cmd{font-family:ui-monospace,monospace;font-size:12.5px;background:var(--head);padding:10px 12px;border-radius:4px;white-space:pre-wrap}
</style>"""
    out = [f"<title>{apr_id} 審批</title>", css, f"<h1>{apr_id} · {a['type']}</h1>", f"<div class=meta>Run {a['run_id']} · 狀態 {a['status']} · 提出 {a['requested_at'][:10]}</div>", f"<div class=summary>{H.escape(a['summary'])}</div>"]
    if a["type"] in ("ACTIVATE_TESTCASE", "APPLY_CHANGE") and a.get("batch_items"):
        groups = {}; n_exp = 0
        for it in a["batch_items"]:
            v = store.load(store.tc_version_path(it["id"], it["version"])); groups.setdefault(v["requirement_ids"][0], []).append((it, v)); n_exp += bool(v.get("assumptions"))
        out.append(f"<p>共 {len(a['batch_items'])} 條：grounded {len(a['batch_items']) - n_exp} 條（預期結果有 spec 條文依據）、<b>exploratory {n_exp} 條</b>（黃底；預期結果含假設，approve 即接受該假設，假設下附 PM 回答）。依需求分組。</p>")
        for rid, items in groups.items():
            r, _ = _refs.find_requirement(rid)
            out.append(f"<h2>{H.escape(rid)} {H.escape(r.get('title', '') if r else '')}</h2>")
            if r: out.append(f"<blockquote>spec：{H.escape(r['spec_reference']['location'])}" + (f"　「{H.escape(r['spec_reference']['quote'])}」" if r['spec_reference'].get('quote') else "") + f"　· 風險 {r.get('risk', '—')}</blockquote>")
            out.append('<table><colgroup><col class=c-id><col class=c-cls><col class=c-title><col class=c-pre><col class=c-steps><col class=c-exp><col class=c-pr></colgroup><tr><th>TC</th><th>類別</th><th>標題</th><th>前置條件</th><th>步驟</th><th>預期結果</th><th>優先/風險</th></tr>')
            for it, v in items:
                exp_ = bool(v.get("assumptions")); short = it["id"].split("-")[-1]
                pre = "<br>".join(H.escape(x) for x in v["preconditions"]) or "—"
                steps = "<ol>" + "".join(f"<li>{H.escape(st['action'])}</li>" for st in v["steps"]) + "</ol>"
                expct = H.escape(v["expected_result"])
                if exp_:
                    expct += '<div class=assume>' + "".join(f"⚠ 假設：{H.escape(a_['text'])}" + "".join(f"<br><span class=pm>✅ PM（{c['clarification_id']}）：{H.escape(c['answer'])}</span>" for c in answered.get(a_["requirement_id"], [])) for a_ in v["assumptions"]) + "</div>"
                out.append(f'<tr class="{"exp" if exp_ else ""}"><td class=id title="{it["id"]}">{short}<br>v{it["version"]}</td><td>{"⚠ exploratory" if exp_ else "grounded"}</td><td>{H.escape(v["title"])}</td><td>{pre}</td><td>{steps}</td><td>{expct}</td><td>{v["priority"]}<br>{v["risk"]}</td></tr>')
            out.append("</table>")
    elif a["type"] == "OPEN_BUG":
        bd = None
        for aid in a.get("artifact_ids", []):
            art = store.load(store.find_artifact(aid))
            if art["artifact_type"] == "BugValidationReport":
                bd = store.load(store.find_artifact(art["payload"]["bug_draft_artifact_id"]))["payload"]; break
            if art["artifact_type"] == "BugDraft": bd = art["payload"]; break
        if bd:
            out.append("<h2>內容</h2>")
            out.append(f"<blockquote>{H.escape(bd['product'])} / {H.escape(bd['functional_area'])}　· Spec：{H.escape(bd['spec_id'])}@{H.escape(bd['spec_version'])}　· 需求：{H.escape(bd['requirement_id'])}　· 環境：{H.escape(bd['environment'].get('name', '—'))}　· 測試帳號：{H.escape(bd['environment'].get('account', '—'))}</blockquote>")
            out.append("<p><b>前置條件</b></p><ol>" + "".join(f"<li>{H.escape(p)}</li>" for p in bd["preconditions"]) + "</ol>")
            out.append("<p><b>重現步驟</b></p><ol>" + "".join(f"<li>{H.escape(s)}</li>" for s in bd["reproduction_steps"]) + "</ol>")
            out.append(f"<p><b>預期結果</b>：{H.escape(bd['expected_result'])}</p>")
            out.append(f"<p><b>實際結果</b>：{H.escape(bd['actual_result'])}</p>")
            if bd.get("actual_result_evidence_map"):
                out.append("<p><b>證據對照</b></p><ul>" + "".join(f"<li>{H.escape(m['claim'])}（{H.escape(m['evidence_id'])}）</li>" for m in bd["actual_result_evidence_map"]) + "</ul>")
            out.append(f"<p><b>影響</b>：{H.escape(bd['impact'])}</p>")
            out.append(f"<p><b>懷疑方向</b>：{H.escape(bd['suspected_area'])}</p>")
        elif a.get("diff_summary"):
            out.append("<h2>內容</h2><div class=summary style='white-space:pre-wrap'>" + H.escape(a["diff_summary"]) + "</div>")
    elif a.get("diff_summary"):
        out.append("<h2>內容</h2><div class=summary style='white-space:pre-wrap'>" + H.escape(a["diff_summary"]) + "</div>")
    out.append(f"<h2>決定</h2><div class=cmd>bin/qaos approve {apr_id} --decision approve --by &lt;you&gt;\nbin/qaos approve {apr_id} --decision approve --by &lt;you&gt; --per-item TC-xxx-001:reject\nbin/qaos approve {apr_id} --decision reject --by &lt;you&gt; --rationale \"...\"</div>")
    if a.get("decision"): out.append(f"<p><b>已決定：{a['decision']['decision']}</b> by {H.escape(a['decision']['decided_by'])} @ {a['decision']['decided_at']}</p>")
    html = "\n".join(out); store.write_derived(f"approvals/{apr_id}.html", html); return html
