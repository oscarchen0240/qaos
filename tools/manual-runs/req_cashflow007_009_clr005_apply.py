#!/usr/bin/env python3
"""套用 CLR-CASHFLOW-005 RD 回覆 A（2026-09-23）：額度上限判定時機由 req-cashin 改為 end-cashin。
spec v07「移至 req-cashin」定案作廢，RD 理由：req-cashin 階段入鈔機尚未清點完成，金額不可信，
若此時依聲稱金額判斷會構成 DoS 攻擊面；開分（req-keyin）不受影響。
REQ-CASHFLOW-007／009 的判定時機互換。"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store
SID, SV, BY = "SPEC-CASHFLOW-001", "0.1", "oscarchen@blockaction.tech"
p = store.requirements_path(SID, SV); d = store.load(p)
NOTE = ("【2026-09-23 CLR-CASHFLOW-005 RD 回覆 A，推翻 spec v07「額度上限判定與預留移至 req-cashin」定案】"
        "req-cashin 階段入鈔機尚未完成實體清點，客戶端回報的金額不可信；若此時依此數字判斷額度上限，"
        "攻擊者可宣稱鉅額數字造成整台機台卡在等待中的 DoS。額度上限實際於 end-cashin（入鈔機清點確認完成後）"
        "依實際金額判定，超限則退鈔。開分（req-keyin，純數字輸入非實體入鈔）不受影響，維持單階段立即判定。")
for r in d["requirements"]:
    if r["requirement_id"] == "REQ-CASHFLOW-007":
        r["title"] = "入金額度上限於 end-cashin 階段依實際清點金額判定"
        r["statement"] = ("req-cashin 階段建立 PENDING、取得 TXID，**不**於此階段判定額度上限（客戶端回報金額未經入鈔機清點確認、不可信）；"
                          "額度上限於 **end-cashin** 階段以場館鎖內「當下全場館餘額合計＋已預留未入帳的入金金額＋本筆實際清點金額」判定，"
                          "未超限才更新帳務、回 0-OK，超限則回 1-OVER LIMIT、機台退鈔、不更新帳務。" + NOTE)
        r["spec_reference"]["quote"] = "（v07 定案已作廢，見 CLR-CASHFLOW-005；本欄不再逐字引用 spec.md，待正本更新）"
        for ac in r["acceptance_criteria"]:
            if ac["ac_id"] == "AC-CASHFLOW-0071":
                ac["given"] = "req-cashin 送出（不論金額，本階段不判定額度）"; ac["then"] = "建立 PENDING 並取得 TXID，尚未判定額度上限、尚未預留"
            elif ac["ac_id"] == "AC-CASHFLOW-0072":
                ac["given"] = "end-cashin 確認時，全場館餘額合計＋已預留金額＋本筆實際清點金額 將超過額度上限"
                ac["then"] = "回 1-OVER LIMIT，不更新帳務、不關閉為已完成，機台退鈔"
            elif ac["ac_id"] == "AC-CASHFLOW-0073":
                ac["given"] = "兩筆入金的 end-cashin 幾乎同時到達，各自單看不超限但合計會超限"
                ac["then"] = "場館鎖內逐筆序列化判定：先處理的一筆通過並入帳，第二筆的判定基準已包含第一筆的實際入帳金額，因而正確被擋下回 1-OVER LIMIT"
        r.setdefault("history", []).append({"at": store.now(), "from_status": "ACTIVE", "to_status": "ACTIVE", "by": BY,
            "trigger": "clarification_applied_CLR-CASHFLOW-005：額度上限判定時機由 req-cashin 改為 end-cashin，AC-0071/0072/0073 given/then 對應反轉"})
    if r["requirement_id"] == "REQ-CASHFLOW-009":
        r["title"] = "end-cashin 依實際清點金額判定額度上限並完成入帳"
        r["statement"] = ("收到 end-cashin 且 TXID 相符時，**本階段判定額度上限**（依入鈔機實際清點金額）；"
                          "未超限則更新帳務、預留概念不再區分（req-cashin 未預留），回 0-OK；超限則回 1-OVER LIMIT、機台退鈔、不更新帳務。" + NOTE)
        r["spec_reference"]["quote"] = "（v07 定案已作廢，見 CLR-CASHFLOW-005；本欄不再逐字引用 spec.md，待正本更新）"
        ac = r["acceptance_criteria"][0]
        ac["given"] = "PENDING 存在且 TXID 相符，end-cashin 帶入入鈔機實際清點金額"
        ac["then"] = "本階段判定額度上限：未超限則更新帳務、關閉 PENDING，回 0-OK；超限則回 1-OVER LIMIT、機台退鈔"
        r.setdefault("history", []).append({"at": store.now(), "from_status": "ACTIVE", "to_status": "ACTIVE", "by": BY,
            "trigger": "clarification_applied_CLR-CASHFLOW-005：end-cashin 改為額度上限判定階段（原「不再判定」整條反轉）"})
store.save(p, d); print("REQ-CASHFLOW-007／009 已反轉")
