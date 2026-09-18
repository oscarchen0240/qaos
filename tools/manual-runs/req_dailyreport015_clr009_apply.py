#!/usr/bin/env python3
"""修正REQ-DAILYREPORT-015的statement，正式套用CLR-DAILYREPORT-009的PM回覆：
未兌現金額仍受結算日期範圍限制（只是不受統計週期切分本身影響），並非完全不受任何篩選條件限制。
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store

SID, SV = "SPEC-DAILYREPORT-001", "0.1"
p = store.requirements_path(SID, SV)
d = store.load(p)

for r in d["requirements"]:
    if r["requirement_id"] == "REQ-DAILYREPORT-015":
        r["statement"] = (
            "統計週期非按日時：各金額與筆數欄為該週期內各營業日的合計；期末餘額取最後營業日；"
            "未兌現金額不受統計週期切分方式影響，一律為截至查詢當下的累計，但仍受結算日期範圍這個"
            "篩選條件限制（依CLR-DAILYREPORT-009確認：範圍外的未兌現收據不計入；「不受週期影響」"
            "指的是不會因為切成週/月而被打散或重複計算，不是不受結算日期範圍本身限制）。"
        )
        r.setdefault("history", []).append({
            "at": store.now(), "from_status": "ACTIVE", "to_status": "ACTIVE", "by": "oscarchen@blockaction.tech",
            "trigger": "clarification_applied_CLR-DAILYREPORT-009：未兌現金額仍受結算日期範圍限制，正式套用",
        })
        break
else:
    raise SystemExit("REQ-DAILYREPORT-015 not found")

store.save(p, d)
print("REQ-DAILYREPORT-015 updated")
