"""tc-final 的 <head>：一律使用內建範本（tools/qaos/templates/final-head.html），不因沒有既有檔或既有檔已退化而產出無樣式的頁面。"""
import pathlib
from tools.qaos import final_export, store

TC = {"testcase_id": "TC-ZZHEAD-001", "version": 1, "title": "範例", "requirement_ids": ["REQ-ZZHEAD-001"], "acceptance_criteria_ids": ["AC-ZZHEAD-0011"],
      "priority": "high", "risk": "high", "test_level": "ui_e2e", "preconditions": ["p"], "steps": [{"n": 1, "action": "a"}], "expected_result": "e",
      "spec_id": "SPEC-ZZHEAD-001", "spec_version": "0.1", "assumptions": []}

def _export(monkeypatch, area):
    monkeypatch.setattr(final_export, "_active_tcs", lambda a: [dict(TC)])
    monkeypatch.setattr(final_export, "_req_index", lambda tcs: {})
    final_export.export(area, new_request=True)
    s = (store.ROOT / f"testcases/final/{area}-final.html").read_text(encoding="utf-8")
    return s[:s.find("<body>")], s

def test_new_area_gets_full_style(monkeypatch):
    head, _ = _export(monkeypatch, "ZZHEADNEW")
    assert "<title>ZZHEADNEW 測試案例集</title>" in head
    assert "--font-ui" in head and "prefers-color-scheme: dark" in head and ".tc-card" in head   # 完整樣式，不是一行的最小樣式
    assert "__AREA__" not in head
    assert head == pathlib.Path(final_export.HEAD_TEMPLATE).read_text(encoding="utf-8").replace("__AREA__", "ZZHEADNEW")

def test_degraded_existing_head_is_replaced_and_subtitle_kept(monkeypatch):
    p = store.ROOT / "testcases/final/ZZHEADOLD-final.html"; p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("<!DOCTYPE html><html><head><meta charset='utf-8'><title>x</title><style>body{font-family:sans-serif}</style></head><body>"
                 '<div class="brand-sub">紅包 &amp; 活動 · 最終整合版</div></body></html>', encoding="utf-8")
    head, s = _export(monkeypatch, "ZZHEADOLD")
    assert "body{font-family:sans-serif}" not in head and "--font-ui" in head
    assert '<div class="brand-sub">紅包 &amp; 活動 · 最終整合版</div>' in s          # 副標沿用既有檔，跳脫不重複

def _rules(css_head: str) -> set:
    """<style> 內的 CSS 規則集合（去除空白後以 } 切分），用來比較語意而不是排版。"""
    import re
    css = re.search(r"<style>(.*)</style>", css_head, re.S).group(1)
    norm = re.sub(r"\s+", "", css)
    return {r + "}" for r in norm.split("}") if r}

def test_template_covers_every_existing_final_head():
    """既有 final.html（repo 內）的每一條 CSS 規則，範本都要有；重新匯出不會讓任何功能區失去樣式（例如 MEMBER／CASHFLOW 的 .brand、.page-head 間距）。"""
    repo = pathlib.Path(__file__).resolve().parents[1]
    tpl = _rules(pathlib.Path(final_export.HEAD_TEMPLATE).read_text(encoding="utf-8"))
    files = sorted((repo / "testcases" / "final").glob("*-final.html"))
    checked = 0
    for f in files:
        s = f.read_text(encoding="utf-8"); head = s[:s.find("<body>")]
        if "<style>" not in head or "--font-ui" not in head: continue   # 已退化的檔（無完整樣式）不作為基準
        missing = _rules(head) - tpl
        assert not missing, f"{f.name} 有範本沒有的規則：{sorted(missing)[:5]}"
        checked += 1
    assert checked >= 1 or not files
