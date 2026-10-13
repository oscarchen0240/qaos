# CLR-CASHFLOW-011：入金的 order_id 由廠商於 req-cashin 帶入，還是由平台產生（暫定比照出金由平台產生）？

- 產品 / 功能：ba-admin / CASHFLOW
- 規格：SPEC-CASHFLOW-001 v0.2  §§出金（`req-cashout` → `end-cashout`）（第 335 行）
- 相關需求：REQ-CASHFLOW-045
- 提出者：agent-spec-analyst（2026-10-12）
- 狀態：ASKED

## 背景
REQ-CASHFLOW-045：出金的訂單編號（order_id）由平台產生，一筆出金一組、全系統唯一，格式為人工可朗讀、可輸入的短碼，印於收據（過渡期顯示於結算結果畫面），作為櫃檯核銷時的查詢鍵。入金交易同樣帶訂單編號，供交易紀錄查詢顯示與查詢；入金 order_id 由廠商於 req-cashin 帶入或由平台產生仍待確認，確認前暫定比照出金由平台產生，與出金共用同一組編號規則與全系統唯一性（Q02）

## 可能的解讀（請勾選或補充）
- （無預設選項，請自由回答）

## 若未回答的影響
依賴此決策點的斷言只能 exploratory，或不能引用衝突的任何一側

## 已查文件
- SPEC-CASHFLOW-001 v0.2（b1e2c55628b9…）

## 已確定的部分
- SPEC-CASHFLOW-001 v0.2 §入金（`req-cashin` → `end-cashin`）（第 323 行）：「入金交易同樣帶訂單編號（`order_id`），供交易紀錄查詢顯示與查詢（2026-09-09 定案）」
- SPEC-CASHFLOW-001 v0.2 §入金（`req-cashin` → `end-cashin`）（第 323 行）：「待確認：入金的 `order_id` 是廠商於 `req-cashin` 帶入或由平台產生（出金為平台產生）；確認前暫定比照出金由平台產生，與出金共用同一組編號規則與全系統唯一性」

## 還需決定的事
入金的 order_id 由廠商於 req-cashin 帶入，還是由平台產生（暫定比照出金由平台產生）？
- 細節：若由廠商帶入：格式、唯一性檢核與重複時的處理未定義

## PM 回覆
（待回覆）

