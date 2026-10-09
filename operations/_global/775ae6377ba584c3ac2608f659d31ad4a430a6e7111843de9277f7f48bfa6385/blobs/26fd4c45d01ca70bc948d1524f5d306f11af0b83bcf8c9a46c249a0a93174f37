# CLR-SITELIST-020：額度上限的允許範圍：負數如何拒絕（前端提示與後端回應）、上限值、可否帶小數。CLR-SITELIST-002 rev 0（針對 v0.4）答「前端顯示『值必須大於或等於 0』，後端也拒絕」，但 v0.7 原文未載，且答案 basis 不同（X16），需以 applicability 綁定到 v0.7 或重新確認

- 產品 / 功能：ba-admin / SITELIST
- 規格：SPEC-SITELIST-001 v0.7  §§站台類型與機台專屬欄位/額度上限 L84 + §業務規則與驗證/額度上限（場館） L232
- 相關需求：REQ-SITELIST-005
- 提出者：agent-spec-analyst（2026-10-09）
- 狀態：ANSWERED

## 背景
REQ-SITELIST-005：額度上限為場館層級設定，該場館底下所有機台帳號共用同一份額度，開分／入金時以全場館機台分數餘額合計檢核；設為 0 代表不限制；修改後即時生效，不影響既有餘額。管理員與站長可設定，操作員唯讀（開發包⑧）。負數、上限與小數位等邊界的拒絕行為 v0.7 未載（前版依 CLR-SITELIST-002 記載負數雙層驗證，本版列為待綁定決策點 Q02）。

## 可能的解讀（請勾選或補充）
- （無預設選項，請自由回答）

## 若未回答的影響
依賴此決策點的斷言只能 exploratory，或不能引用衝突的任何一側

## 已查文件
- SPEC-SITELIST-001 v0.7（c6001a294a5a…）
- SPEC-ARCADE-001 v0.8（7cbe9808a641…）
- SPEC-ROLEPERM-001 v0.2（d47f01840f02…）
- SPEC-ADMINSYS-001 v0.3（6d22cafaa1ce…）

## 已確定的部分
- SPEC-SITELIST-001 v0.7 §業務規則與驗證 額度上限（場館）（第 232 行）：「設為 0 代表不限制」

## 還需決定的事
額度上限的允許範圍：負數如何拒絕（前端提示與後端回應）、上限值、可否帶小數。CLR-SITELIST-002 rev 0（針對 v0.4）答「前端顯示『值必須大於或等於 0』，後端也拒絕」，但 v0.7 原文未載，且答案 basis 不同（X16），需以 applicability 綁定到 v0.7 或重新確認
- 細節：negative_value_reject
- 細節：max_value
- 細節：decimal_places

## PM 回覆
負數拒絕：額度上限輸入負數時，前端顯示「值必須大於或等於 0」，後端也會拒絕（雙層驗證）。上限值、可否帶小數，原答覆未定義，另開 CLR 追問。沿用 CLR-SITELIST-002 rev 0。
— PM（2026-09-14，經 Oscar 轉達；沿用 CLR-SITELIST-002 rev 0），2026-10-09，落地方式：requirement_clarified
