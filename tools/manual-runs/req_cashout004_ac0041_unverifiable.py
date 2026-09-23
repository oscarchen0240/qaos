#!/usr/bin/env python3
"""RD 2026-09-23 確認（採方案 B）：出金與洗分一送出都直接完成進入待核實，後端無法攔截 end-cashout
完成回報，「待確認」狀態無法在測試環境製造 → AC-CASHOUT-0041 無法以黑箱測試驗證，TC-CASHOUT-044 已退役。
規則本身仍有效，僅標註驗證能力缺口與零覆蓋事實。"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store
SID, SV, BY = "SPEC-CASHOUT-001", "0.1", "oscarchen@blockaction.tech"
p = store.requirements_path(SID, SV); d = store.load(p)
for r in d["requirements"]:
    if r["requirement_id"] == "REQ-CASHOUT-004":
        ac = [a for a in r["acceptance_criteria"] if a["ac_id"] == "AC-CASHOUT-0041"][0]
        assert "無法" not in ac["then"], "已標註過"
        ac["then"] = ac["then"].rstrip("。") + ("。⚠️ 驗證能力缺口（RD 2026-09-23 確認）：出金與洗分一送出都直接完成並進入待核實，"
            "後端無法攔截 end-cashout 完成回報，「待確認」狀態無法在測試環境製造，本 AC 目前無法以黑箱測試驗證；"
            "原對應案例 TC-CASHOUT-044 已退役（APR-0171），本 AC 現為零覆蓋。規則本身仍然有效，"
            "未來若具備故障注入／攔截能力應重新建立案例")
        r["statement"] = r["statement"] + ("。【2026-09-23 補充】RD 確認後端無法製造「待確認」狀態，AC-CASHOUT-0041 無法黑箱驗證、"
            "對應案例已退役並標為零覆蓋；AC-CASHOUT-0042（未成立的出金）仍由 TC-CASHOUT-045 覆蓋，本 requirement 未完全失去覆蓋")
        r.setdefault("history", []).append({"at": store.now(), "from_status": "ACTIVE", "to_status": "ACTIVE", "by": BY,
            "trigger": "AC-CASHOUT-0041 標註驗證能力缺口（RD 2026-09-23 確認無法製造待確認狀態，方案 B）；TC-CASHOUT-044 退役 APR-0171，本 AC 零覆蓋"})
        print("AC-CASHOUT-0041 已標註零覆蓋與驗證能力缺口")
        break
else: raise SystemExit("not found")
store.save(p, d)
