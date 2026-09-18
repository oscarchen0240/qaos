# CLR-ACCOUNT-001：REQ-ACCOUNT-010 不符合時系統應如何反應？（Spec 未定義拒絕行為）

- 產品 / 功能：ba-admin / ACCOUNT
- 規格：SPEC-ACCOUNT-001 v0.1  §§角色與權限 + 開發包⑦附註
- 相關需求：REQ-ACCOUNT-010
- 提出者：agent-spec-analyst（2026-09-13）
- 狀態：APPLIED

## 背景
Admin 可操作；站長可於管轄範圍內的站台操作（帳號建立於目前所在站台底下）；操作員不可新增機台帳號
Spec 未定義操作員嘗試建立帳號時的具體回應（按鈕隱藏／API 拒絕）

## 可能的解讀（請勾選或補充）
- （無預設選項，請自由回答）

## 若未回答的影響
Test Designer 只能以 exploratory（假設）方式撰寫此需求的負向案例，expected 需 Human 確認

## PM 回覆
操作員權限在會員列表裡「創建會員帳號」按鈕隱藏（前端層級，非彈窗開啟後才擋）。
— PM（2026-09-14，經 Oscar 轉達），2026-09-13，落地方式：requirement_clarified
