#!/usr/bin/env python3
"""套用 CLR-CASHOUT-002 回覆 A（2026-09-23）：洗分為單階段交易，不會停在待處理／等待中（＝待確認）。
AC-CASHOUT-0041 的 given 原為「機台洗分交易狀態為待確認」，此情境不存在，改用出金（兩階段）；
REQ-CASHOUT-004 statement 補述洗分的未完成路徑僅有未成立。"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store
SID, SV, BY = "SPEC-CASHOUT-001", "0.1", "oscarchen@blockaction.tech"
p = store.requirements_path(SID, SV); d = store.load(p)
for r in d["requirements"]:
    if r["requirement_id"] == "REQ-CASHOUT-004":
        ac = [a for a in r["acceptance_criteria"] if a["ac_id"] == "AC-CASHOUT-0041"][0]
        assert "洗分" in ac["given"], ac["given"]
        ac["given"] = "一筆機台出金交易狀態為待確認（req-cashout 已核可但 end-cashout 完成回報未送達，尚未完成）"
        ac["then"] = ("查無此筆紀錄（因為該筆交易尚未完成，本頁不會有它的核實狀態紀錄）；需至機台交易紀錄查明狀態，"
                      "不可憑本頁無紀錄直接判斷已完成或未完成以外的狀態")
        r["statement"] = r["statement"].rstrip("）") + ("）。補充（CLR-CASHOUT-002 回覆 A，2026-09-23）：機台洗分為單階段交易（req-keyout，帳務立即生效），"
            "不會停在「待處理／等待中」（＝待確認）——畫面篩選器上那兩個技術值係與「出鈔」共用同一組的結果，對洗分不適用；"
            "洗分的未完成路徑僅有「已拒絕／錯誤」（＝未成立）。因此「未完成交易不會出現在本頁」的待確認情境須以出金（兩階段）驗證，"
            "AC-CASHOUT-0041 的 given 已據此自洗分改為出金")
        r.setdefault("history", []).append({"at": store.now(), "from_status": "ACTIVE", "to_status": "ACTIVE", "by": BY,
            "trigger": "clarification_applied_CLR-CASHOUT-002：洗分無待確認路徑；AC-CASHOUT-0041 given 自洗分改為出金，statement 補述洗分未完成路徑僅有未成立"})
        print("REQ-CASHOUT-004 statement 與 AC-CASHOUT-0041 已更新")
        break
else: raise SystemExit("REQ-CASHOUT-004 not found")
store.save(p, d)
