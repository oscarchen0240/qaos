# CLR-DAILYREPORT-007：「當日結束的場次筆數」是否包含狀態為「逾時結束」與「日結結算」的場次？

- 產品 / 功能：ba-admin / DAILYREPORT
- 規格：SPEC-DAILYREPORT-001 v0.1
- 相關需求：REQ-DAILYREPORT-009
- 提出者：oscarchen@blockaction.tech（2026-09-13）
- 狀態：APPLIED

## 背景
REQ-DAILYREPORT-009 major ambiguity；TC-DAILYREPORT-031 以假設處理。

## 可能的解讀（請勾選或補充）
- （無預設選項，請自由回答）

## 若未回答的影響
相關 Test Case 無法設計 / 相關 Bug 無法判定是否違反規格

## PM 回覆
逾時結束的時間會超過日結時間；而 Spec 規定日結時間到達時強制結束所有進行中的場次，因此當日內場次只會以「已結束」或「日結結算」收尾，兩者都計入當日場次數（場次數計算在今日）。→ TC-DAILYREPORT-031 的假設「含所有非進行中狀態、日結結算歸屬開始的營業日」已確認。
— PM／QA（2026-09-14，經 Oscar 轉達），2026-09-13，落地方式：requirement_clarified
