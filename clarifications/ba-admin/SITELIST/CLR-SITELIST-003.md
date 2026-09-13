# CLR-SITELIST-003：REQ-SITELIST-006 不符合時系統應如何反應？（Spec 未定義拒絕行為）

- 產品 / 功能：ba-admin / SITELIST
- 規格：SPEC-SITELIST-001 v0.4  §§站台類型與機台專屬欄位/場次逾時時間
- 相關需求：REQ-SITELIST-006
- 提出者：agent-spec-analyst（2026-09-13）
- 狀態：ANSWERED

## 背景
場次逾時時間為機台仍有餘額但無任何交易與遊玩時，自動結束場次的時間長度；預設 1 小時，站長可調整
Spec 未定義輸入 0、負數或極大值時系統的回應；「操作員唯讀」屬實體機台功能角色，本 spec 未定義該角色，無法在本功能區驗證

## 可能的解讀（請勾選或補充）
- （無預設選項，請自由回答）

## 若未回答的影響
Test Designer 只能以 exploratory（假設）方式撰寫此需求的負向案例，expected 需 Human 確認

## PM 回覆
場次逾時時間：後端設計最低值為 1 小時（低於 1 小時會被拒絕）。輸入超過 17 位數（極端格式）時，前端跳格式錯誤，後端阻擋並回傳通用錯誤代碼 COMMON_INVALID_REQUEST_FORMAT。
— PM（2026-09-14，經 Oscar 轉達），2026-09-13，落地方式：requirement_clarified
