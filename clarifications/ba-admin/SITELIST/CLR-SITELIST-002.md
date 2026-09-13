# CLR-SITELIST-002：REQ-SITELIST-005 不符合時系統應如何反應？（Spec 未定義拒絕行為）

- 產品 / 功能：ba-admin / SITELIST
- 規格：SPEC-SITELIST-001 v0.4  §§站台類型與機台專屬欄位/額度上限 + §業務規則-額度上限（場館）
- 相關需求：REQ-SITELIST-005
- 提出者：agent-spec-analyst（2026-09-13）
- 狀態：ANSWERED

## 背景
額度上限為場館層級設定，該場館底下所有機台帳號共用同一份額度，以全場館機台分數餘額合計檢核；設為 0 代表不限制；修改後即時生效，不影響既有餘額
Spec 未定義輸入負數或非數字時系統的回應

## 可能的解讀（請勾選或補充）
- （無預設選項，請自由回答）

## 若未回答的影響
Test Designer 只能以 exploratory（假設）方式撰寫此需求的負向案例，expected 需 Human 確認

## PM 回覆
額度上限輸入負數：前端顯示「值必須大於或等於 0」，後端也會拒絕（雙層驗證）。
— PM（2026-09-14，經 Oscar 轉達），2026-09-13，落地方式：requirement_clarified
