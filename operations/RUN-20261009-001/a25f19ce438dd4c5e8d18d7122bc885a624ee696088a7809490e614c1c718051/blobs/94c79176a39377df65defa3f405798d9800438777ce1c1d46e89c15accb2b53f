# CLR-SITELIST-021：場次逾時時間的單位、最低值與上限，以及低於下限或格式錯誤時的前後端回應。CLR-SITELIST-003 rev 0（針對 v0.4）答「後端最低 1 小時；超過 17 位數時前端格式錯誤、後端回 COMMON_INVALID_REQUEST_FORMAT」，但 v0.7 原文未載，且答案 basis 不同（X16），需以 applicability 綁定到 v0.7 或重新確認

- 產品 / 功能：ba-admin / SITELIST
- 規格：SPEC-SITELIST-001 v0.7  §§站台類型與機台專屬欄位/場次逾時時間 L85 + §業務規則與驗證/場次逾時 L234
- 相關需求：REQ-SITELIST-006
- 提出者：agent-spec-analyst（2026-10-09）
- 狀態：OPEN

## 背景
REQ-SITELIST-006：場次逾時時間為機台仍有餘額但無任何交易與遊玩時，自動結束場次的時間長度；預設 1 小時，管理員與站長可調整，操作員唯讀（v0.7 第 85 行、開發包⑧第八節）；期間內有任何交易或注單即重新起算（實體機台正本）。最低值與輸入格式的拒絕行為 v0.7 未載（前版依 CLR-SITELIST-003 記載，本版列為待綁定決策點 Q02）。

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
- SPEC-SITELIST-001 v0.7 §業務規則與驗證 場次逾時（第 234 行）：「逾時時間取自場館設定，預設 1 小時」

## 還需決定的事
場次逾時時間的單位、最低值與上限，以及低於下限或格式錯誤時的前後端回應。CLR-SITELIST-003 rev 0（針對 v0.4）答「後端最低 1 小時；超過 17 位數時前端格式錯誤、後端回 COMMON_INVALID_REQUEST_FORMAT」，但 v0.7 原文未載，且答案 basis 不同（X16），需以 applicability 綁定到 v0.7 或重新確認
- 細節：unit
- 細節：min_value
- 細節：max_value
- 細節：error_code_value

## PM 回覆
（待回覆）

