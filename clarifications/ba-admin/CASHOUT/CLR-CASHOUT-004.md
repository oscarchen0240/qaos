# CLR-CASHOUT-004：洗分出金核實的金額範圍篩選是否接受小數輸入？邊界是否含等號（min＝max＝399.60 能否查到該筆）？

- 產品 / 功能：ba-admin / CASHOUT
- 規格：SPEC-CASHOUT-001 v0.2
- 相關需求：REQ-CASHOUT-014
- 提出者：oscarchen@blockaction.tech（2026-10-12）
- 狀態：OPEN

## 背景
v0.2 起實際金額可能帶小數，第 57 行只寫「範圍輸入（min ～ max）」。（來源：2026-10-12／13 T3RR 風險抽查 CASHOUT RF-06；問題單 C 主題 C3）

## 可能的解讀（請勾選或補充）
- （無預設選項，請自由回答）

## 若未回答的影響
洗分出金核實 RF-06

## 已查文件
- SPEC-CASHOUT-001 v0.2（76c11bf6a07b…）

## PM 回覆
（待回覆）

