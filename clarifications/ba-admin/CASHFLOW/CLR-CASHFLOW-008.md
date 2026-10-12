# CLR-CASHFLOW-008：待確認出金（PENDING）是否可由管理員手動取消收斂？REQ-CASHFLOW-026 依 2026-09-15 CLR-CASHFLOW-004 移除了「Admin 手動取消」路徑，只剩新 req-cashout 取代與人工出金連動取消，與 spec 原文及 CLR-REDPACKET-055 最新答案不一致；入金 PENDING 是否同樣可手動取消？

- 產品 / 功能：ba-admin / CASHFLOW
- 規格：SPEC-CASHFLOW-001 v0.1
- 相關需求：REQ-CASHFLOW-026
- 提出者：oscarchen@blockaction.tech（2026-10-12）
- 狀態：INCORPORATED

## 背景
SPEC-CASHFLOW-001 v0.1 第 341、344、372 行與 v0.2 第 260、345、348、376 行皆寫待確認出金可由管理員手動取消收斂（含 Operator Reset 後只能手動取消、機台報廢死單清理）。2026-09-15 CLR-CASHFLOW-004 依 RD 畫面移除此路徑（REQ-CASHFLOW-026），並移除入金預留於手動取消時釋放（REQ-CASHFLOW-008）。2026-10-12 Oscar 確認（CLR-REDPACKET-055 rev 1）待確認出金的管理員手動取消要做，後端已完成、前端未開發。

## 可能的解讀（請勾選或補充）
- （無預設選項，請自由回答）

## 若未回答的影響
REQ-CASHFLOW-026（出金死單收斂路徑）與引用手動取消的 CASHFLOW TC（約 4 張）需重新判定；REQ-CASHFLOW-008 視入金是否適用

## 已查文件
- SPEC-CASHFLOW-001 v0.1（b34624219b5a…）
- SPEC-CASHFLOW-001 v0.2（b1e2c55628b9…）
- SPEC-REDPACKET-001 v0.2（75afb8365acd…）

## 已確定的部分
- SPEC-CASHFLOW-001 v0.1 §出金 第一階段 15 秒逾時（第 341 行）：「須由新的 `req-cashout` 取代或 Admin 手動取消收斂」
- CLR-REDPACKET-055 答案 rev 1：「待確認出金的管理員手動取消是要做的功能，後端已開發完成，僅前端尚未開發」

## PM 回覆
可以。待確認出金（PENDING）的收斂路徑恢復為三條：被新的 req-cashout 取代、櫃檯人工出金連動取消、管理員手動取消（於 4.1 交易紀錄查詢機台視角操作；僅管理員，RD 已確認；取消後交易標記為「已取消」，分數不異動）。Operator Reset 後機台停止重送、機台報廢等死單，由管理員手動取消清理。後端已開發完成，前端尚未開發。入金沒有手動取消：待確認入金只依 24 小時逾時轉「已逾時」收斂；入金額度上限的判定時機依 CLR-CASHFLOW-005（end-cashin 依實際清點金額判定、req-cashin 不預留額度），REQ-CASHFLOW-008 維持 2026-09-15 移除「手動取消釋放預留」的結論。2026-09-15 CLR-CASHFLOW-004 對出金「移除 Admin 手動取消路徑」的部分不再適用。（rev 1：刪除 rev 0 中「預留額度於入帳或逾時釋放」一句，該句與 CLR-CASHFLOW-005 不一致）
— Oscar（2026-10-12；角色經 RD 確認），2026-10-12，落地方式：requirement_clarified
