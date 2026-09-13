#!/usr/bin/env python3
"""把 Phase 1 的 Markdown 文件組成單頁 HTML（Artifact 用）。Mermaid 區塊轉為 <pre class="mermaid">。"""
import re, html, pathlib, sys, markdown
ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "docs" / "review.html"

SECTIONS = [
    ("review",     "00 · Architecture Review",   "docs/architecture/00-architecture-review.md"),
    ("sec-01",     "01 · System Architecture",   "docs/architecture/01-system-architecture.md"),
    ("sec-02",     "02 · Data Model & ERD",      "docs/architecture/02-data-model.md"),
    ("sec-03",     "03 · State Machines",        "docs/architecture/03-state-machines.md"),
    ("sec-04",     "04 · Quality Gates",         "docs/architecture/04-quality-gates.md"),
    ("sec-05",     "05 · Permission Matrix",     "docs/architecture/05-permission-matrix.md"),
    ("sec-09",     "09 · Human Approval Flow",   "docs/architecture/09-human-approval-flow.md"),
    ("wf-spec-to-testcase", "WF-A · Spec → Test Case", "docs/workflows/spec-to-testcase.md"),
    ("wf-spec-to-bug",      "WF-B · Spec → Bug",       "docs/workflows/spec-to-bug.md"),
    ("wf-spec-change-impact","WF-C · Spec Change Impact","docs/workflows/spec-change-impact.md"),
    ("wf-manual-test-to-regression","WF-D · Manual → Regression","docs/workflows/manual-test-to-regression.md"),
    ("wf-regression-generation","WF-E · Regression Generation","docs/workflows/regression-generation.md"),
    ("contracts",  "Agent Contracts",            "docs/agent-contracts/README.md"),
    ("sec-07",     "07 · Skill Evaluation",      "docs/architecture/07-skill-evaluation.md"),
    ("sec-06",     "06 · Repository Structure",  "docs/architecture/06-repository-structure.md"),
    ("sec-08",     "08 · Roadmap · Risks",       "docs/architecture/08-roadmap.md"),
    ("decisions",  "NEEDS_DECISION",             "docs/decisions/NEEDS_DECISION.md"),
]

LINKMAP = [
    (r'\]\(0([0-9])-[a-z-]+\.md\)', r'](#sec-0\1)'),
    (r'\]\(\.\./workflows/([a-z-]+)\.md\)', r'](#wf-\1)'),
    (r'\]\(\.\./workflows/\*\.md\)', r'](#wf-spec-to-testcase)'),
    (r'\]\(\.\./decisions/NEEDS_DECISION\.md\)', r'](#decisions)'),
    (r'\]\(\.\./agent-contracts/README\.md\)', r'](#contracts)'),
    (r'\]\(docs/architecture/00-architecture-review\.md\)', r'](#review)'),
    (r'\]\(docs/decisions/NEEDS_DECISION\.md\)', r'](#decisions)'),
]

def convert(md_text):
    blocks = []
    def stash(m):
        blocks.append(m.group(1)); return f"\n\nMERMAIDBLOCK{len(blocks)-1}\n\n"
    md_text = re.sub(r"```mermaid\n(.*?)```", stash, md_text, flags=re.S)
    for pat, rep in LINKMAP: md_text = re.sub(pat, rep, md_text)
    md_text = re.sub(r"^# .*\n", "", md_text, count=1)  # 首行 H1 由 section header 取代
    h = markdown.markdown(md_text, extensions=["tables", "fenced_code", "sane_lists"])
    for i, b in enumerate(blocks):
        h = h.replace(f"<p>MERMAIDBLOCK{i}</p>", f'<div class="diagram"><pre class="mermaid">{html.escape(b)}</pre></div>')
    h = h.replace("<table>", '<div class="tablewrap"><table>').replace("</table>", "</table></div>")
    h = h.replace("[NEEDS_DECISION", '<span class="tag tag-amber">NEEDS_DECISION').replace("NEEDS_DECISION-", "NEEDS_DECISION-").replace("]</span>", "</span>")
    return h

nav = "\n".join(f'<a href="#{sid}">{html.escape(t)}</a>' for sid, t, _ in SECTIONS)
body = []
for sid, title, path in SECTIONS:
    md = (ROOT / path).read_text()
    body.append(f'<section id="{sid}"><div class="sec-head"><span class="eyebrow">{html.escape(path)}</span><h1>{html.escape(title)}</h1></div>{convert(md)}</section>')

page = f"""<title>QAOS Architecture Review</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Sora:wght@500;600;700&family=IBM+Plex+Sans:ital,wght@0,400;0,500;0,600;1,400&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root {{
  --bg:#F5F7F5; --surface:#FFFFFF; --ink:#1B2325; --ink-2:#4E5B59; --muted:#7A8785;
  --line:#D5DCD8; --line-strong:#B9C3BF;
  --accent:#0E6B5F; --accent-ink:#FFFFFF; --accent-soft:#DDEDE9;
  --amber:#9A6210; --amber-soft:#F6EAD2;
  --code-bg:#EEF2F0;
  --font-display:"Sora", "Helvetica Neue", Arial, sans-serif;
  --font-body:"IBM Plex Sans", "PingFang TC", "Noto Sans TC", system-ui, sans-serif;
  --font-mono:"IBM Plex Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --bg:#131719; --surface:#1A2022; --ink:#E4E9E7; --ink-2:#B4BFBC; --muted:#7F8C89;
  --line:#2A3335; --line-strong:#3B4749;
  --accent:#4FB9A9; --accent-ink:#0C1A18; --accent-soft:#183531;
  --amber:#E0A94A; --amber-soft:#3A2C12;
  --code-bg:#20282A;
}} }}
:root[data-theme="dark"] {{
  --bg:#131719; --surface:#1A2022; --ink:#E4E9E7; --ink-2:#B4BFBC; --muted:#7F8C89;
  --line:#2A3335; --line-strong:#3B4749;
  --accent:#4FB9A9; --accent-ink:#0C1A18; --accent-soft:#183531;
  --amber:#E0A94A; --amber-soft:#3A2C12;
  --code-bg:#20282A;
}}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--ink); font-family:var(--font-body); font-size:15px; line-height:1.65; }}
a {{ color:var(--accent); text-decoration:none; }} a:hover {{ text-decoration:underline; }}
a:focus-visible, button:focus-visible {{ outline:2px solid var(--accent); outline-offset:2px; }}
.shell {{ display:grid; grid-template-columns:260px minmax(0,1fr); min-height:100vh; }}
nav {{ position:sticky; top:0; height:100vh; overflow-y:auto; border-right:1px solid var(--line); padding:28px 20px; background:var(--surface); }}
nav .brand {{ font-family:var(--font-display); font-weight:700; font-size:18px; letter-spacing:-.01em; margin-bottom:4px; }}
nav .brand small {{ display:block; font-family:var(--font-mono); font-weight:400; font-size:11px; color:var(--muted); letter-spacing:.04em; margin-top:4px; }}
nav .stamp {{ display:inline-block; margin:14px 0 22px; padding:6px 10px; border:1.5px solid var(--amber); color:var(--amber); border-radius:3px; font-family:var(--font-mono); font-size:11px; letter-spacing:.06em; text-transform:uppercase; }}
nav a {{ display:block; padding:6px 8px; margin:1px 0; border-radius:4px; color:var(--ink-2); font-size:13.5px; }}
nav a:hover {{ background:var(--accent-soft); color:var(--ink); text-decoration:none; }}
main {{ padding:40px 56px 120px; max-width:1180px; }}
.hero {{ border-bottom:1px solid var(--line); padding-bottom:28px; margin-bottom:12px; }}
.hero h1 {{ font-family:var(--font-display); font-size:34px; font-weight:700; letter-spacing:-.02em; line-height:1.15; margin:0 0 10px; text-wrap:balance; }}
.hero p {{ max-width:68ch; color:var(--ink-2); margin:0 0 20px; }}
.stats {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(130px,1fr)); gap:12px; }}
.stat {{ border:1px solid var(--line); border-radius:6px; padding:12px 14px; background:var(--surface); }}
.stat b {{ display:block; font-family:var(--font-display); font-size:26px; font-weight:600; color:var(--accent); font-variant-numeric:tabular-nums; line-height:1.1; }}
.stat span {{ font-size:12px; color:var(--muted); letter-spacing:.04em; text-transform:uppercase; }}
section {{ padding:44px 0 8px; border-top:1px solid var(--line); scroll-margin-top:16px; }}
section:first-of-type {{ border-top:0; }}
.sec-head {{ margin-bottom:18px; }}
.eyebrow {{ font-family:var(--font-mono); font-size:11.5px; color:var(--muted); letter-spacing:.04em; }}
section h1 {{ font-family:var(--font-display); font-size:26px; font-weight:600; letter-spacing:-.015em; margin:4px 0 0; text-wrap:balance; }}
section h2 {{ font-family:var(--font-display); font-size:19px; font-weight:600; margin:34px 0 10px; letter-spacing:-.01em; text-wrap:balance; }}
section h3 {{ font-family:var(--font-display); font-size:15.5px; font-weight:600; margin:26px 0 8px; }}
p, li {{ max-width:78ch; }}
blockquote {{ margin:16px 0; padding:12px 18px; border-left:3px solid var(--accent); background:var(--accent-soft); border-radius:0 6px 6px 0; }}
blockquote p {{ margin:0; }}
code {{ font-family:var(--font-mono); font-size:.88em; background:var(--code-bg); padding:1px 5px; border-radius:3px; }}
pre {{ font-family:var(--font-mono); font-size:12.5px; line-height:1.55; background:var(--code-bg); padding:14px 16px; border-radius:6px; overflow-x:auto; }}
pre code {{ background:none; padding:0; }}
.tablewrap {{ overflow-x:auto; margin:14px 0 22px; border:1px solid var(--line); border-radius:6px; background:var(--surface); }}
table {{ border-collapse:collapse; width:100%; font-size:13.5px; }}
th, td {{ text-align:left; vertical-align:top; padding:8px 11px; border-bottom:1px solid var(--line); }}
th {{ font-family:var(--font-display); font-weight:600; font-size:12.5px; letter-spacing:.02em; background:var(--code-bg); position:sticky; top:0; }}
tr:last-child td {{ border-bottom:0; }}
td code {{ white-space:nowrap; }}
.diagram {{ overflow-x:auto; margin:16px 0 26px; padding:16px; border:1px solid var(--line); border-radius:6px; background:var(--surface); }}
.diagram pre.mermaid {{ background:none; padding:0; margin:0; }}
.tag {{ font-family:var(--font-mono); font-size:.82em; padding:1px 6px; border-radius:3px; white-space:nowrap; }}
.tag-amber {{ background:var(--amber-soft); color:var(--amber); }}
hr {{ border:0; border-top:1px solid var(--line); margin:28px 0; }}
@media (max-width:1000px) {{ .shell {{ grid-template-columns:1fr; }} nav {{ position:static; height:auto; border-right:0; border-bottom:1px solid var(--line); }} main {{ padding:28px 20px 80px; }} }}
@media (prefers-reduced-motion: no-preference) {{ html {{ scroll-behavior:smooth; }} }}
</style>
<div class="shell">
<nav>
  <div class="brand">QAOS<small>QA Agent Operating System · Phase 1</small></div>
  <div class="stamp">Awaiting Approval</div>
  {nav}
</nav>
<main>
  <div class="hero">
    <h1>QAOS Architecture Review</h1>
    <p>Phase 1 — Architecture Discovery 的完整產出：系統架構、資料模型、狀態機、Quality Gates、權限矩陣、五個 Workflow、八份 Agent Contract、Skill 評估與 Roadmap。閱讀順序：先看 00 的矛盾清單與 DoD，再看 NEEDS_DECISION，回覆 <code>APPROVE ARCHITECTURE</code> 後進入 Phase 2。</p>
    <div class="stats">
      <div class="stat"><b>8</b><span>Agents + Runtime</span></div>
      <div class="stat"><b>5</b><span>Workflows</span></div>
      <div class="stat"><b>35</b><span>JSON Schemas</span></div>
      <div class="stat"><b>8</b><span>Quality Gates</span></div>
      <div class="stat"><b>34</b><span>Actions</span></div>
      <div class="stat"><b>14</b><span>Mermaid 圖</span></div>
      <div class="stat"><b>13</b><span>待決事項</span></div>
    </div>
  </div>
  {"".join(body)}
</main>
</div>
"""
OUT.write_text(page)
print("wrote", OUT, len(page)//1024, "KB")
