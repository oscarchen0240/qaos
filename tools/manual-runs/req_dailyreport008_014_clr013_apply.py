#!/usr/bin/env python3
"""套用 CLR-DAILYREPORT-013 PM 定案 A（2026-10-01）：以 spec 2026-09-17 為準，推翻 CLR-DAILYREPORT-012 的 B。
- REQ-DAILYREPORT-008：依場次明細列出進行中場次（結束時間「—」、場次時長與期末餘額累計到查詢當下）；恢復 AC-DAILYREPORT-0083
- REQ-DAILYREPORT-014：期末餘額計入進行中場次；已結算營業日取結算時點、尚未結算取截至查詢當下；新增 AC-DAILYREPORT-0143；風險改 high
spec_reference 的 quote 只引用專案收錄的 v0.1 原文（09-17 修訂不在 v0.1 內），定案出處寫在 location。"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store

SID, SV, BY = "SPEC-DAILYREPORT-001", "0.1", "oscarchen@blockaction.tech"
p = store.requirements_path(SID, SV); d = store.load(p)
reqs = {r["requirement_id"]: r for r in d["requirements"]}

r = reqs["REQ-DAILYREPORT-008"]
assert all(ac["ac_id"] != "AC-DAILYREPORT-0083" for ac in r["acceptance_criteria"]), "AC-0083 已存在"
r["statement"] = ("「場次編號」欄僅在「依場次明細」維度顯示，並附開始／結束時間與場次時長。依場次明細列出所有狀態的場次，含進行中："
                  "進行中場次的結束時間顯示「—」，場次時長與期末餘額為累計到查詢當下的值（依 CLR-DAILYREPORT-013 PM 定案 A，2026-10-01，"
                  "以 spec 2026-09-17 修訂為準，推翻 CLR-DAILYREPORT-012 的 B）。")
r["acceptance_criteria"].append({"ac_id": "AC-DAILYREPORT-0083",
    "given": "機台 A 有一個進行中場次（已有開分與投注，目前分數 X）",
    "when": "以含當日的結算日期依場次明細查詢，查看該場次列",
    "then": "該列狀態「進行中」、結束時間「—」，場次時長與期末餘額為累計到查詢當下的值（期末餘額＝X）"})
r["spec_reference"] = {"spec_id": SID, "spec_version": SV,
    "location": "§列表欄位/場次編號 + §背景:場次資訊（進行中場次的期末餘額依 CLR-DAILYREPORT-013 PM 定案 A／spec 2026-09-17）",
    "quote": "進行中的場次結束時間顯示「—」"}
r.setdefault("history", []).append({"at": store.now(), "from_status": "ACTIVE", "to_status": "ACTIVE", "by": BY,
    "trigger": "clarification_applied_CLR-DAILYREPORT-013：PM 定案 A，依場次明細列出進行中場次；恢復 AC-DAILYREPORT-0083（並加上期末餘額累計到查詢當下）"})

r = reqs["REQ-DAILYREPORT-014"]
assert all(ac["ac_id"] != "AC-DAILYREPORT-0143" for ac in r["acceptance_criteria"]), "AC-0143 已存在"
r["statement"] = ("期末餘額為各機台分數合計，計入進行中場次的分數：已結算的營業日取該日結算時點的值；尚未結算（含有進行中場次）的取截至查詢當下的分數。"
                  "統計週期非按日時取該週期最後一個營業日的值（依 CLR-DAILYREPORT-013 PM 定案 A，2026-10-01，以 spec 2026-09-17 修訂為準）。")
r["acceptance_criteria"].append({"ac_id": "AC-DAILYREPORT-0143",
    "given": "當日營業日尚未日結，機台 A 有進行中場次、目前分數 300",
    "when": "結算日期為當日，依機台明細查詢",
    "then": "機台 A 列的期末餘額為 300（截至查詢當下，含進行中場次的分數）"})
r["risk"] = "high"
r["spec_reference"] = {"spec_id": SID, "spec_version": SV,
    "location": "§列表欄位/期末餘額 + 欄位說明附註（計入進行中場次依 CLR-DAILYREPORT-013 PM 定案 A／spec 2026-09-17）",
    "quote": "該日結算時點各機台的分數合計"}
r.setdefault("history", []).append({"at": store.now(), "from_status": "ACTIVE", "to_status": "ACTIVE", "by": BY,
    "trigger": "clarification_applied_CLR-DAILYREPORT-013：PM 定案 A，期末餘額計入進行中場次（尚未結算取截至查詢當下）；新增 AC-DAILYREPORT-0143；風險 medium→high"})

store.save(p, d); print("REQ-DAILYREPORT-008／014 updated; AC-0083 restored; AC-0143 added")
