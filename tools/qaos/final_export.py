"""testcases/final/<AREA>-final.html／-final-active.json：某功能區全部 ACTIVE TC 的最終整合文件（DoD 三項之一）。

事實來源：testcases/registry（ACTIVE 指標）→ testcases/versions（內容）→ artifacts/requirements（需求標題）。
樣式一律用內建範本 tools/qaos/templates/final-head.html（只替換標題）；副標題沿用既有 final.html 的 brand-sub。
不從既有檔擷取 <head>：新功能區沒有既有檔時會退化成無樣式，而退化的檔案又會在下次匯出時被沿用。
"""
import html, json, re, pathlib
from . import store, operation

HEAD_TEMPLATE = pathlib.Path(__file__).resolve().parent / "templates" / "final-head.html"

def _active_tcs(area):
    out = []
    for p in store.glob(f"testcases/registry/TC-{area}-*.yaml"):
        ptr = store.load(p)
        if ptr.get("status") != "ACTIVE": continue
        out.append(store.load(store.tc_version_path(p.stem, ptr["active_version"])))
    return out

def _req_index(tcs):
    """requirement_id → {title, statement}，依 TC 所掛的 spec 載入 RM。"""
    from . import rm, refs
    idx = {}
    for t in tcs:                                                             # TC 的依據：版本檔 pin → TC sidecar（需求 A 第 5 章 §4.1）
        pin = rm.tc_pin_for_display(t["testcase_id"], t["version"])            # 移轉前的 legacy TC 才可退回最新 revision／legacy 檢視
        for rid in t.get("requirement_ids", []):
            if rid not in idx:
                r, _ = refs.find_requirement(rid, t["spec_id"], t["spec_version"], pin=pin)
                if r: idx[rid] = r
    return idx

def _head(area):
    return HEAD_TEMPLATE.read_text(encoding="utf-8").replace("__AREA__", html.escape(area))

def _existing_subtitle(area):
    p = f"testcases/final/{area}-final.html"
    if store.exists(p):
        sub = re.search(r'<div class="brand-sub">([^<]*)</div>', store.read_text(p))
        if sub: return html.unescape(sub.group(1).split(" · ")[0])
    return area

def _cut(s, n=40): return html.escape(s if len(s) <= n else s[:n] + "...")

def _card(t):
    exp = bool(t.get("assumptions")); cls = "exploratory" if exp else "grounded"
    acs = t.get("acceptance_criteria_ids", [])
    search = " ".join([t["testcase_id"], t["title"], *t["requirement_ids"], *acs, t["priority"], t["risk"]]).lower()
    badge = '<span class="p3-badge">Phase 3 整合</span>' if (t["version"] > 1 or t.get("source") == "change_workflow") else ""
    pills = [f"<span class='pill pill-{cls}'>{'exploratory · 含待確認假設' if exp else 'grounded · 已確認'}</span>",
             f"<span class='pill pill-neutral'>優先 {t['priority']}</span>", f"<span class='pill pill-risk-{t['risk']}'>風險 {t['risk']}</span>",
             f'<span class="pill pill-neutral">{t["test_level"]}</span>'] + [f'<span class="pill pill-neutral">{a}</span>' for a in acs]
    pre = "".join(f"<li>{html.escape(p)}</li>" for p in t.get("preconditions", []))
    steps = "".join(f"<li><span class='step-n'>{s['n']}</span><span>{html.escape(s['action'])}</span></li>" for s in t["steps"])
    assum = ("<div class='assumptions'><div class='assumptions-label'>⚠ 假設 / 待確認</div><ul>" + "".join(f"<li>{html.escape(a['text'])}</li>" for a in t["assumptions"]) + "</ul></div>") if exp else ""
    ref = t.get("expected_result_spec_reference") or {}
    quote = f'<span class="spec-quote">{html.escape(ref["quote"])}</span>' if ref.get("quote") else ""
    return f'''<article class="tc-card" data-search="{html.escape(search)}" data-class="{cls}">
  <header class="tc-head">
    <div class="tc-id-row">
      <span class="tc-id">{t["testcase_id"]}</span>
      <span class="tc-ver">v{t["version"]}</span>
      {badge}
    </div>
    <h3 class="tc-title">{html.escape(t["title"])}</h3>
    <div class="tc-pills">
      {chr(10).join("      " + p for p in pills).strip()}
    </div>
  </header>

  <div class="tc-body">
    <div class="tc-section">
      <div class="tc-label">前置條件</div>
      <ul class="tc-precon">{pre}</ul>
    </div>
    <div class="tc-section">
      <div class="tc-label">步驟</div>
      <ol class="tc-steps">{steps}</ol>
    </div>
    <div class="tc-section">
      <div class="tc-label">預期結果</div>
      <p class="tc-expected">{html.escape(t["expected_result"])}</p>
    </div>
    {assum}
    <div class="tc-spec">
      <span class="spec-loc">{html.escape(ref.get("location", ""))}</span>
      {quote}
    </div>
  </div>
</article>'''

@operation.operation("tc_final")
def export(area):
    tcs = _active_tcs(area)
    if not tcs: raise SystemExit(f"{area} 沒有 ACTIVE TC")
    reqs = _req_index(tcs); spec_ids = sorted({t["spec_id"] for t in tcs})
    head, subtitle = _head(area), _existing_subtitle(area)
    by_req = {}
    for t in tcs:
        for rid in t["requirement_ids"]: by_req.setdefault(rid, []).append(t)
    # 只在「第一個」掛的需求下列出，避免多需求 TC 重複出現
    placed = set(); groups = {}
    for rid in sorted(by_req):
        for t in by_req[rid]:
            if t["testcase_id"] not in placed: groups.setdefault(rid, []).append(t); placed.add(t["testcase_id"])
    n_exp = sum(1 for t in tcs if t.get("assumptions")); n_p3 = sum(1 for t in tcs if t["version"] > 1 or t.get("source") == "change_workflow")
    p3_ids = [t["testcase_id"] for t in tcs if t["version"] > 1 or t.get("source") == "change_workflow"]
    nav = "".join(f'<a href="#{rid}" class="nav-link"><span class="nav-num">{rid.split("-")[-1][-2:]}</span>{_cut(reqs.get(rid, {}).get("statement") or reqs.get(rid, {}).get("title") or rid)}</a>' for rid in groups)
    sections = "\n".join(f'''    <section class="req-group" id="{rid}">
      <div class="req-head">
        <span class="req-id">{rid}</span>
        <h2>{_cut(reqs.get(rid, {}).get("statement") or reqs.get(rid, {}).get("title") or rid)}</h2>
      </div>
      <div class="tc-grid">
{chr(10).join(_card(t) for t in ts)}
      </div>
    </section>''' for rid, ts in groups.items())
    body = f'''<body>
<div class="layout">
  <aside class="sidebar">
    <div class="brand">
      <div class="brand-eyebrow">QAOS · {" / ".join(spec_ids)}</div>
      <h1>{area} 測試案例集</h1>
    </div>
    <div class="brand-sub">{html.escape(subtitle)} · 最終整合版</div>
    <div class="stat-strip">
      <div class="stat"><b>{len(tcs)}</b><span>ACTIVE 案例</span></div>
      <div class="stat"><b>{len(tcs) - n_exp}</b><span>grounded 已確認</span></div>
      <div class="stat"><b>{n_exp}</b><span>exploratory 待確認</span></div>
      <div class="stat"><b>{n_p3}</b><span>Phase 3 整合修訂</span></div>
    </div>
    <input class="search-box" id="search" type="text" placeholder="搜尋 TC ID / 標題 / 需求...">
    <div class="filter-chips">
      <button class="chip active" data-chip="all">全部</button>
      <button class="chip" data-chip="grounded">grounded</button>
      <button class="chip" data-chip="exploratory">exploratory</button>
    </div>
    <div class="nav-title">依需求跳轉</div>
    <nav>{nav}</nav>
  </aside>
  <main class="main">
    <div class="page-head">
      <h1>{area} 功能區 · 最終測試案例</h1>
      <p>本頁彙整 {" / ".join(spec_ids)} 底下所有 ACTIVE 狀態的測試案例，共 {len(tcs)} 條，涵蓋 {len(groups)} 項需求。每條案例皆經過結構化 Gate 與獨立 Validator 審查通過並由 Oscar 核准。更新：{store.now()[:10]}。</p>
      <div class="integration-note">
        <b>Phase 2 × Phase 3 整合／修訂說明：</b> 其中 {n_p3} 條（{", ".join(p3_ids) or "—"}）為交叉比對後納入的整合版本、新增案例，或依 PM 澄清（CLR）修訂後的版本；修訂歷程見各 TC 的 history 與對應 run。
      </div>
    </div>

{sections}
  </main>
</div>
<script>
const search = document.getElementById('search');
const cards = Array.from(document.querySelectorAll('.tc-card'));
const chips = Array.from(document.querySelectorAll('.chip'));
let activeChip = 'all';
function applyFilter() {{
  const q = search.value.trim().toLowerCase();
  cards.forEach(c => {{
    const matchesText = !q || c.dataset.search.includes(q);
    const matchesChip = activeChip === 'all' || c.dataset.class === activeChip;
    c.hidden = !(matchesText && matchesChip);
  }});
  document.querySelectorAll('.req-group').forEach(g => {{
    const visible = g.querySelectorAll('.tc-card:not([hidden])').length > 0;
    g.hidden = !visible;
  }});
}}
search.addEventListener('input', applyFilter);
chips.forEach(chip => chip.addEventListener('click', () => {{
  chips.forEach(c => c.classList.remove('active'));
  chip.classList.add('active');
  activeChip = chip.dataset.chip;
  applyFilter();
}}));
</script>
</body>
</html>
'''
    store.write_derived(f"testcases/final/{area}-final.html", head + body)
    store.write_derived(f"testcases/final/{area}-final-active.json", json.dumps([{k: v for k, v in t.items() if k != "history"} for t in tcs], ensure_ascii=False, indent=2))
    return len(tcs), len(groups)
