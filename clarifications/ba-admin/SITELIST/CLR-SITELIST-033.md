# CLR-SITELIST-033：額度上限的上限值為何？可否帶小數（幾位）？超出時前後端如何回應？

- 產品 / 功能：ba-admin / SITELIST
- 規格：SPEC-SITELIST-001 v0.7
- 相關需求：REQ-SITELIST-005
- 提出者：oscarchen@blockaction.tech（2026-10-09）
- 狀態：OPEN

## 背景
CLR-SITELIST-020 依 CLR-SITELIST-002 rev 0 已答負數的拒絕方式（前端「值必須大於或等於 0」、後端雙層驗證），但上限值與小數位原答覆未定義，v0.7 原文也沒有寫。

## 可能的解讀（請勾選或補充）
- （無預設選項，請自由回答）

## 若未回答的影響
額度上限的邊界值 TC 無法設計確定斷言，只能 exploratory

## 已查文件
- SPEC-SITELIST-001 v0.7（c6001a294a5a…）
- SPEC-ROLEPERM-001 v0.2（d47f01840f02…）

## PM 回覆
（待回覆）

