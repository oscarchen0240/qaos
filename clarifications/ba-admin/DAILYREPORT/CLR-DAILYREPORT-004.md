# CLR-DAILYREPORT-004：REQ-DAILYREPORT-007 不符合時系統應如何反應？（Spec 未定義拒絕行為）

- 產品 / 功能：ba-admin / DAILYREPORT
- 規格：SPEC-DAILYREPORT-001 v0.1  §§列表欄位/結算期間 + §業務規則/日結時間
- 相關需求：REQ-DAILYREPORT-007
- 提出者：agent-spec-analyst（2026-09-13）
- 狀態：ANSWERED

## 背景
「結算期間」欄按日顯示營業日（依場館設定的日結時間切分，UTC+0）；按週／按月／區間合計顯示該週期起訖日期。
Spec 未定義場館未設定日結時間時的預設值

## 可能的解讀（請勾選或補充）
- （無預設選項，請自由回答）

## 若未回答的影響
Test Designer 只能以 exploratory（假設）方式撰寫此需求的負向案例，expected 需 Human 確認

## PM 回覆
日結時間為場館設定欄位（每日結算的截止時刻，UTC+0），畫面截圖顯示欄位有預設值「上午 12:00」（即 00:00 UTC+0）。→ 未設定時以 00:00 UTC+0 切分營業日。
— PM（2026-09-13，經 Oscar 轉達），2026-09-13，落地方式：requirement_clarified
