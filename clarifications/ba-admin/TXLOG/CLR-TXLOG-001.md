# CLR-TXLOG-001：REQ-TXLOG-029 不符合時系統應如何反應？（Spec 未定義拒絕行為）

- 產品 / 功能：ba-admin / TXLOG
- 規格：SPEC-TXLOG-001 v0.1  §§操作
- 相關需求：REQ-TXLOG-029
- 提出者：agent-spec-analyst（2026-09-14）
- 狀態：APPLIED

## 背景
手動取消規格上限定「僅 Admin」「僅待確認狀態」，但 spec 未明確定義非 Admin 身分嘗試執行、或對非待確認狀態的交易嘗試執行時，系統具體如何阻擋（按鈕隱藏／停用／或允許操作後回錯誤）
Spec 只定義了誰可以執行與對什麼狀態執行，未定義不符合條件時系統具體的阻擋機制（按鈕隱藏/停用/操作後拒絕）

## 可能的解讀（請勾選或補充）
- （無預設選項，請自由回答）

## 若未回答的影響
Test Designer 只能以 exploratory（假設）方式撰寫此需求的負向案例，expected 需 Human 確認

## PM 回覆
此問題已 moot：交易紀錄查詢頁（本包）實際上並不提供『手動取消』這個操作，spec.md §操作 描述的『手動取消：僅 Admin 可對待確認狀態的交易執行』這段是錯誤敘述，非現行產品行為。凡是待確認/待核實交易需要的人工處理，一律在『洗分出金核實』頁（SPEC-CASHOUT-001）進行，不在本頁。REQ-TXLOG-028/029 需回頭修正。
— oscarchen@blockaction.tech，2026-09-14，落地方式：spec_updated
