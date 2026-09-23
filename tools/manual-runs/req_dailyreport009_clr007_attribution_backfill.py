#!/usr/bin/env python3
"""回寫 CLR-DAILYREPORT-007 PM 回覆的第二層：日結結算場次歸屬「開始的營業日」。
首次 apply（2026-09-17）只載入第一層（日結結算計入場次數），第二層僅存在於 TC-DAILYREPORT-031 的 assumption
（APR-0003 核准），未進 RM statement——由 RUN-20260923-001 Bug Validator 指出（minor missing_traceability）。"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store
SID, SV, BY = "SPEC-DAILYREPORT-001", "0.1", "oscarchen@blockaction.tech"
p = store.requirements_path(SID, SV); d = store.load(p)
for r in d["requirements"]:
    if r["requirement_id"] == "REQ-DAILYREPORT-009":
        assert "歸屬" not in r["statement"], "已回寫過"
        r["statement"] = r["statement"].rstrip("。") + ("。日結結算場次的營業日歸屬：歸屬於場次**開始**的營業日，不因其被日結時刻強制結束而計入下一個營業日"
                                                        "（CLR-DAILYREPORT-007 PM 回覆的第二層，對應 TC-DAILYREPORT-031 已由 APR-0003 核准的假設；2026-09-23 回寫）。")
        r.setdefault("history", []).append({"at": store.now(), "from_status": "ACTIVE", "to_status": "ACTIVE", "by": BY,
            "trigger": "clarification_applied_CLR-DAILYREPORT-007（補回第二層）：日結結算場次歸屬開始的營業日；首次 apply 漏回寫，由 RUN-20260923-001 Bug Validator 指出"})
        print("REQ-DAILYREPORT-009 statement 已補第二層")
        break
else: raise SystemExit("not found")
store.save(p, d)
