#!/usr/bin/env python3
"""套用 CLR-DAILYREPORT-012 PM 回覆 B：依場次明細不列進行中場次。
REQ-DAILYREPORT-008 statement 移除進行中規則、AC-DAILYREPORT-0083 作廢（AC 物件無 status 欄位，自列表移除並留 history）。"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store

SID, SV = "SPEC-DAILYREPORT-001", "0.1"
p = store.requirements_path(SID, SV); d = store.load(p)
for r in d["requirements"]:
    if r["requirement_id"] == "REQ-DAILYREPORT-008":
        r["statement"] = ("「場次編號」欄僅在「依場次明細」維度顯示，並附開始／結束時間與場次時長。"
                          "依場次明細只列出已結束／逾時結束／日結結算的場次，進行中場次不列（依 CLR-DAILYREPORT-012 PM 定案 B，2026-09-22）；"
                          "場次資訊表「進行中的場次結束時間顯示「—」、時長累計至查詢當下」一句不適用本報表。")
        before = [ac["ac_id"] for ac in r["acceptance_criteria"]]
        r["acceptance_criteria"] = [ac for ac in r["acceptance_criteria"] if ac["ac_id"] != "AC-DAILYREPORT-0083"]
        assert len(r["acceptance_criteria"]) == len(before) - 1, before
        r.setdefault("history", []).append({
            "at": store.now(), "from_status": "ACTIVE", "to_status": "ACTIVE", "by": "oscarchen@blockaction.tech",
            "trigger": "clarification_applied_CLR-DAILYREPORT-012：依場次明細不列進行中場次；AC-DAILYREPORT-0083 作廢移除（原 given「有一場次仍進行中」then「結束時間「—」、時長累計至查詢當下」）；TC-DAILYREPORT-027 已 retire",
        })
        break
else:
    raise SystemExit("REQ-DAILYREPORT-008 not found")
store.save(p, d); print("REQ-DAILYREPORT-008 updated; AC-0083 removed")
