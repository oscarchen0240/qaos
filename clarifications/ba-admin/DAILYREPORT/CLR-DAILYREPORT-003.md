# CLR-DAILYREPORT-003：REQ-DAILYREPORT-004 不符合時系統應如何反應？（Spec 未定義拒絕行為）

- 產品 / 功能：ba-admin / DAILYREPORT
- 規格：SPEC-DAILYREPORT-001 v0.1  §§篩選器/結算日期
- 相關需求：REQ-DAILYREPORT-004
- 提出者：agent-spec-analyst（2026-09-13）
- 狀態：ANSWERED

## 背景
結算日期為日期範圍、必填；不設區間上限。
Spec 只寫「必填」，未定義未填時的提示文案或阻擋方式；亦未定義起日晚於迄日時的行為

## 可能的解讀（請勾選或補充）
- （無預設選項，請自由回答）

## 若未回答的影響
Test Designer 只能以 exploratory（假設）方式撰寫此需求的負向案例，expected 需 Human 確認

## PM 回覆
結算日期異常（起日晚於迄日等）：找不到資料即可，API 回 rows: []。註：與 Spec「必填」的關係——未填時是否也回空列表而非阻擋，建議 spec v0.2 明寫。
【2026-09-14 補充】未填結算日期時，前端 popup 警示「失敗：結算日期為必填」（截圖）；不送出查詢。→ TC-DAILYREPORT-009 的假設已解（阻擋方式＝popup）。
— PM（2026-09-13，經 Oscar 轉達），2026-09-13，落地方式：requirement_clarified
