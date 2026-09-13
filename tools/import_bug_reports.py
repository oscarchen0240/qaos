#!/usr/bin/env python3
"""把 ../bug-reports/bug-0N-*.md 轉成 ManualTestRecord（testcases/manual/）+ inline Evidence。
只做機械萃取；requirement 對映留給 Test Designer(mode=manual)（WF-D）。可重跑：已匯入的來源檔會跳過。"""
import re, sys, pathlib, yaml
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from tools.qaos import store, ids, schema

if len(sys.argv) < 2: sys.exit("用法：python3 tools/import_bug_reports.py <bug-reports 目錄> [tester]")
SRC = pathlib.Path(sys.argv[1]).resolve()
TESTER = sys.argv[2] if len(sys.argv) > 2 else "oscarchen@blockaction.tech"
SPEC_HINT = {"spec_id": "SPEC-ADMQUERY-001", "spec_version": "1.0"}
# 每份 bug 涉及的草稿條文（供 Test Designer 參考，不是正式 requirement_id）
CLAUSES = {"01": ["§3.2 R6", "§3.1 R1"], "02": ["§3.1 R5", "§3.1 R1", "§3.1 R2"], "03": ["§3.1 R1", "§3.1 R2"], "04": ["§3.4 R9", "§3.2 R6"],
           "05": ["§3.1 R4"], "06": ["§3.2 R7", "§3.2 R6"], "07": ["§3.1 R3"], "08": ["§3.3 R8"]}

def sections(text):
    return {m.group(1).strip(): m.group(2).strip() for m in re.finditer(r"\n## ([^\n]+)\n(.*?)(?=\n## |\Z)", text, re.S)}

def pick(secs, prefix):
    return next((v for k, v in secs.items() if k.startswith(prefix)), "")

def steps_of(text):
    out = [re.sub(r"^\d+\.\s*", "", l).strip() for l in text.splitlines() if re.match(r"^\d+\.\s", l.strip())]
    return out or [l.strip("- ").strip() for l in text.splitlines() if l.strip()]

existing = {store.load(p).get("notes", "") for p in (store.ROOT / "testcases" / "manual").glob("MAN-*.yaml")}
done = []
for f in sorted(SRC.glob("bug-0[1-8]-*.md")):
    if any(f.name in n for n in existing): print("skip (exists)", f.name); continue
    text = f.read_text(encoding="utf-8"); secs = sections(text)
    head = text.split("\n## ")[0]
    title = re.sub(r"^# Bug #\d+[:：]\s*", "", head.splitlines()[0]).strip()
    tool = (re.search(r"工具:\s*`([^`]+)`", head) or [None, "?"])[1]
    date = (re.search(r"發現日期:\s*(\d{4}-\d{2}-\d{2})", head) or [None, "2026-08-06"])[1]
    sev = (re.search(r"嚴重度:\s*([^\n]+)", head) or [None, ""])[1]
    n = f.name[4:6]
    evidence_text = pick(secs, "證據")
    eid = ids.alloc("EVD"); owner = "bug-reports"
    (store.ROOT / "evidence" / owner).mkdir(parents=True, exist_ok=True)
    uri = f"evidence/{owner}/{eid}.md"; (store.ROOT / uri).write_text(evidence_text, encoding="utf-8")
    ev = {"evidence_id": eid, "type": "api_response", "uri": uri, "sha256": store.sha256_text(evidence_text), "mime_type": "text/markdown",
          "captured_at": f"{date}T00:00:00Z", "captured_by": TESTER, "description": f"{f.name} 的「證據」段落（人工核對基準 vs 篩選結果）", "inline_content": evidence_text}
    assert not schema.errors(ev, "execution/evidence.schema.json"); store.save(f"evidence/{owner}/{eid}.yaml", ev)
    rid = ids.alloc("MAN")
    rec = {"record_id": rid, "title": f"[{tool}] {title}", "tester": TESTER, "tested_at": f"{date}T00:00:00Z", "product": "mcp-admin", "functional_area": "ADMQUERY",
           "spec_hint": dict(SPEC_HINT), "environment": "mcp-admin (test-mcp-admin.springkyle.online) via Claude Code MCP client",
           "preconditions": [f"工具 `{tool}` 可呼叫", "已取得不帶 query 的 baseline 資料"],
           "steps_performed": steps_of(pick(secs, "我做了什麼測試")), "observed_result": pick(secs, "結論"), "outcome": "fail", "evidence_ids": [eid],
           "notes": f"source: bug-reports/{f.name}; severity(原報告): {sev}; 涉及草稿條文: {', '.join(CLAUSES.get(n, []))}"}
    errs = schema.errors(rec, "testcase/manual-test-record.schema.json")
    if errs: sys.exit(f"{f.name}: " + "; ".join(errs))
    store.save(f"testcases/manual/{rid}.yaml", rec); store.audit(None, TESTER, "IMPORT_MANUAL_RECORD", f"{rid} ← {f.name} evidence={eid}")
    done.append((rid, eid, f.name, len(rec["steps_performed"])))
for d in done: print(*d)
print(f"{len(done)} records imported")
