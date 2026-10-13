# CLR-CASHFLOW-014：入金與出金的異常收斂：(1) end-cashin 超限回 1-OVER LIMIT、退鈔後，該筆 PENDING 轉成什麼狀態？機台會不會重送？平台收到重送是否必須固定拒絕（不得在額度釋放後轉為成功）？(2) end-cashin 清點金額為 0、大於 req-cashin 聲稱金額、帶小數時以哪個入帳、是否拒絕？req-cashin 有無防禦性預檢、門檻多少？(3) 有未完成 PENDING 時重置機台憑證，新 token 能否完成舊 TXID？舊 token 回 9-OTHER ERROR 時機台是否持續重送？(4) req-cashout 與 end-cashout 之間完成一筆入金時，end-cashout 後餘額是 0 還是該筆入金、屬於哪個場次？

- 產品 / 功能：ba-admin / CASHFLOW
- 規格：SPEC-CASHFLOW-001 v0.2
- 相關需求：REQ-CASHFLOW-007
- 提出者：oscarchen@blockaction.tech（2026-10-12）
- 狀態：ASKED

## 背景
依 CLR-CASHFLOW-005 入金額度改於 end-cashin 判定；第 371 行只列 1-NO RECORD、6-BAD DATA/FORMAT 會讓機台停止重送，1-OVER LIMIT、9-OTHER ERROR 不在其中——若持續重送，額度釋放後可能入帳，造成退鈔又加分。第 175、343 行與第 337、338 行對出金期間投鈔的餘額說法矛盾。（來源：2026-10-12／13 T3RR 風險抽查 CASHFLOW RF-06/03/10/13；問題單 C 主題 C5）

## 可能的解讀（請勾選或補充）
- （無預設選項，請自由回答）

## 若未回答的影響
機台金流 RF-06、03、10、13

## 已查文件
- SPEC-CASHFLOW-001 v0.2（b1e2c55628b9…）

## PM 回覆
（待回覆）

