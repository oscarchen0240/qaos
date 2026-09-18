# CLR-DAILYREPORT-002：REQ-DAILYREPORT-003 不符合時系統應如何反應？（Spec 未定義拒絕行為）

- 產品 / 功能：ba-admin / DAILYREPORT
- 規格：SPEC-DAILYREPORT-001 v0.1  §§篩選器/機台帳號
- 相關需求：REQ-DAILYREPORT-003
- 提出者：agent-spec-analyst（2026-09-13）
- 狀態：APPLIED

## 背景
篩選欄「機台帳號」為文字輸入，輸入會員編號；留空表示場館全部機台。
Spec 未定義輸入不存在或非本場館的機台帳號時的回應（空列表？錯誤提示？）

## 可能的解讀（請勾選或補充）
- （無預設選項，請自由回答）

## 若未回答的影響
Test Designer 只能以 exploratory（假設）方式撰寫此需求的負向案例，expected 需 Human 確認

## PM 回覆
輸入不存在或非本場館的機台帳號：找不到用戶即可，API 回 rows: []（空列表，不報錯）。
— PM（2026-09-13，經 Oscar 轉達），2026-09-13，落地方式：requirement_clarified
