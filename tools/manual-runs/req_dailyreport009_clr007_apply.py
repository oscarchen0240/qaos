#!/usr/bin/env python3
"""修正REQ-DAILYREPORT-009的statement與rejection_contract，正式套用CLR-DAILYREPORT-007的PM回覆：
逾時結束、日結結算兩種狀態都計入「當日結束的場次數」（只有進行中的場次不計入）。
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store

SID, SV = "SPEC-DAILYREPORT-001", "0.1"
p = store.requirements_path(SID, SV)
d = store.load(p)

for r in d["requirements"]:
    if r["requirement_id"] == "REQ-DAILYREPORT-009":
        r["statement"] = (
            "「場次數」於「依場館彙總」與「依機台明細」維度顯示，為當日結束的場次筆數："
            "依機台明細＝該機台帳號當日場次數；依場館彙總＝該場館底下所有機台帳號當日場次數的加總。"
            "「當日結束」包含「已結束」與「日結結算」兩種狀態（依CLR-DAILYREPORT-007確認：逾時結束的"
            "時間必然超過日結時間，而日結時間到達時會強制結束所有進行中場次，故當日內場次只會以"
            "「已結束」或「日結結算」收尾，兩者皆計入當日場次數）；僅「進行中」狀態不計入。"
        )
        r["rejection_contract"]["description"] = (
            "進行中場次不計（『當日結束的場次筆數』）；已結束與日結結算兩種狀態皆計入，"
            "此點已由CLR-DAILYREPORT-007正式確認"
        )
        r.setdefault("history", []).append({
            "at": store.now(), "from_status": "ACTIVE", "to_status": "ACTIVE", "by": "oscarchen@blockaction.tech",
            "trigger": "clarification_applied_CLR-DAILYREPORT-007：當日結束場次數計算範圍（已結束+日結結算皆計入）正式套用",
        })
        break
else:
    raise SystemExit("REQ-DAILYREPORT-009 not found")

store.save(p, d)
print("REQ-DAILYREPORT-009 updated")
