#!/usr/bin/env python3
"""套用 CLR-CASHFLOW-006 回覆 B（2026-09-23）：所有未成立原因一律不寫入交易紀錄，不只餘額不足。
理由與 CLR-CASHFLOW-005 一致：客戶端未經驗證的輸入若被拒絕仍留紀錄，構成資料庫灌爆的攻擊面。
修正 REQ-CASHFLOW-030（本 spec）與 REQ-TXLOG-001／016／023（SPEC-TXLOG-001）。"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store
BY = "oscarchen@blockaction.tech"
NOTE = ("【2026-09-23 CLR-CASHFLOW-006 回覆 B】所有未成立原因（額度上限、資料格式錯誤、機台停用/場館未開通、憑證失效等）"
        "一律不寫入交易紀錄，理由與 CLR-CASHFLOW-005 一致：客戶端未經驗證的輸入若被拒絕仍留紀錄，攻擊者可高頻觸發使資料庫被大量無用紀錄灌爆。"
        "spec.md 正本相關文字（未成立原因、附錄狀態碼對照）待更新。")

# 1) SPEC-CASHFLOW-001 REQ-CASHFLOW-030
p1 = store.requirements_path("SPEC-CASHFLOW-001", "0.1"); d1 = store.load(p1)
for r in d1["requirements"]:
    if r["requirement_id"] == "REQ-CASHFLOW-030":
        r["title"] = "所有未成立原因一律不寫入交易紀錄"
        r["statement"] = "任何交易被判定為未成立（不論原因為額度上限、資料格式錯誤、機台停用/場館未開通、憑證失效或餘額不足），平台一律不寫入交易紀錄，僅回覆對應狀態碼；交易紀錄查詢／機台交易紀錄不會出現任何「未成立」狀態的紀錄。" + NOTE
        r["spec_reference"]["quote"] = "（v0.1 原文僅載明餘額不足不寫入；本規則已由 CLR-CASHFLOW-006 擴大至全部未成立原因，spec.md 待更新）"
        for ac in r["acceptance_criteria"]:
            if ac["ac_id"] == "AC-CASHFLOW-0302":
                ac["given"] = "交易因額度上限、資料格式錯誤、機台停用/場館未開通或憑證失效等任一未成立原因被拒絕"
                ac["then"] = "查無此次拒絕的紀錄，僅收到對應狀態碼；不會以「未成立」狀態出現在交易紀錄查詢中"
        r.setdefault("history", []).append({"at": store.now(), "from_status": "ACTIVE", "to_status": "ACTIVE", "by": BY,
            "trigger": "clarification_applied_CLR-CASHFLOW-006：AC-CASHFLOW-0302 反轉，所有未成立原因皆不寫入紀錄"})
        print("REQ-CASHFLOW-030 已更新")
store.save(p1, d1)

# 2) SPEC-TXLOG-001
p2 = store.requirements_path("SPEC-TXLOG-001", "0.1"); d2 = store.load(p2)
for r in d2["requirements"]:
    if r["requirement_id"] == "REQ-TXLOG-001":
        r["statement"] = "併入既有 4.1 交易紀錄查詢後，查詢範圍在機台交易時額外顯示尚未完成（待確認）、被取消、已逾時的交易；「未成立」的交易因不寫入紀錄，查詢結果不會出現（CLR-CASHFLOW-006，2026-09-23）"
        for ac in r["acceptance_criteria"]:
            if ac["ac_id"] == "AC-TXLOG-0011":
                ac["given"] = "查詢範圍包含機台交易"
                ac["then"] = "除已完成（已生效）的交易外，也列出待確認、已取消、已逾時的機台交易；未成立的交易不會出現"
        r.setdefault("history", []).append({"at": store.now(), "from_status": "ACTIVE", "to_status": "ACTIVE", "by": BY,
            "trigger": "clarification_applied_CLR-CASHFLOW-006：AC-TXLOG-0011 移除「未成立」，改為明確排除"})
        print("REQ-TXLOG-001 已更新")
    if r["requirement_id"] == "REQ-TXLOG-016":
        r["title"] = "交易狀態「未成立」不會有任何紀錄可查（不只餘額不足）"
        r["statement"] = ("未成立狀態代表平台拒絕了這筆請求，分數未異動；所有未成立原因（含額度上限、資料格式錯誤、機台停用/場館未開通、憑證失效、"
                          "餘額不足）皆不寫入交易紀錄，故「未成立」狀態實質上不會出現在交易紀錄查詢中（CLR-CASHFLOW-006，2026-09-23，擴大原僅排除餘額不足的規則）")
        for ac in r["acceptance_criteria"]:
            if ac["ac_id"] == "AC-TXLOG-0161":
                ac["given"] = "一筆交易因額度上限等任一未成立原因被平台拒絕"
                ac["then"] = "查無此筆交易，不會以未成立狀態出現在列表中（與 AC-TXLOG-0162 餘額不足同一待遇）"
        r.setdefault("history", []).append({"at": store.now(), "from_status": "ACTIVE", "to_status": "ACTIVE", "by": BY,
            "trigger": "clarification_applied_CLR-CASHFLOW-006：AC-TXLOG-0161 反轉，與 AC-TXLOG-0162 待遇一致"})
        print("REQ-TXLOG-016 已更新")
    if r["requirement_id"] == "REQ-TXLOG-023":
        r["statement"] = r["statement"].rstrip("。") + ("。【2026-09-23 補充】因所有未成立原因皆不寫入交易紀錄（CLR-CASHFLOW-006），"
            "「未成立」狀態實務上不會出現在查詢結果中，本欄位的正向顯示情境（AC-TXLOG-0231）無法以黑箱測試建立前置條件，僅負向分支（AC-TXLOG-0232）可驗證")
        r.setdefault("history", []).append({"at": store.now(), "from_status": "ACTIVE", "to_status": "ACTIVE", "by": BY,
            "trigger": "clarification_applied_CLR-CASHFLOW-006：補充 AC-TXLOG-0231 驗證能力缺口說明"})
        print("REQ-TXLOG-023 已更新（補充說明）")
store.save(p2, d2)
