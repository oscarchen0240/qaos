# CLR-DAILYREPORT-009：「未兌現金額不受週期影響、累計至查詢當下」是否也不受結算日期範圍限制？

- 產品 / 功能：ba-admin / DAILYREPORT
- 規格：SPEC-DAILYREPORT-001 v0.1
- 相關需求：REQ-DAILYREPORT-015
- 提出者：oscarchen@blockaction.tech（2026-09-13）
- 狀態：APPLIED

## 背景
REQ-015 major ambiguity；TC-DAILYREPORT-046 以假設「不受結算日期限制」處理

## 可能的解讀（請勾選或補充）
- （無預設選項，請自由回答）

## 若未回答的影響
相關 Test Case 無法設計 / 相關 Bug 無法判定是否違反規格

## PM 回覆
受結算日期範圍限制：結算日期仍是篩選條件，未兌現金額只算範圍內；只是不受統計週期切分影響。例：9/10 未兌現 200；(a) 結算 09-03～09-09 按週 → 09-07～09-09 列未兌現 1000、09-03～09-06 列 0；(b) 結算 09-03～09-10 → 09-07～09-10 列 1200、09-03～09-06 列 0。→ **TC-DAILYREPORT-046 的假設（不受結算日期限制）是錯的**，該案 expected 需改為「不包含範圍外的 200」；建議 APR-0003 逐項 reject TC-046，待 spec v0.2 走 WF-C 重寫。
— PM／QA（2026-09-14，經 Oscar 轉達，附截圖），2026-09-13，落地方式：requirement_clarified
