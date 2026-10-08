# CLR-REDPACKET-034：新總預算小於或等於目前總預算時，後端是否同樣拒絕及其回應（狀態碼與訊息）；前端行為已由 SPEC-REDPACKET-002@0.1 confirmBudget() 定義（見 Q05）

- 產品 / 功能：ba-admin / REDPACKET
- 規格：SPEC-REDPACKET-001 v0.1  §§活動排程 L190
- 相關需求：REQ-REDPACKET-016
- 提出者：agent-spec-analyst（2026-10-08）
- 狀態：OPEN

## 背景
REQ-REDPACKET-016：設有總預算、且狀態為進行中或排程中的活動，列表提供「追加預算」：開啟視窗顯示目前總預算、已占用與剩餘；輸入新的總預算（須大於目前總預算），點擊「確認」即時生效，原本預算用罄的活動恢復產生紅包。只能調高、不能調低；未設總預算的活動不提供此操作、不可改為有預算。每次追加寫入操作紀錄（操作人員、時間、調整前與調整後金額）。活動狀態依 SPEC-REDPACKET-002@0.1 getStatus()：已取消排程 → 已取消；開始時間晚於現在 → 排程中；區間活動結束時間早於現在 → 已結束；其餘 → 進行中。列表有狀態欄與狀態篩選（全部／進行中／排程中／已結束／已取消），已結束與已取消的活動仍列出。新總預算不大於目前總預算時，前端於欄位顯示「須大於目前總預算（只能調高、不能調低）」且不生效。

## 可能的解讀（請勾選或補充）
- （無預設選項，請自由回答）

## 若未回答的影響
依賴此決策點的斷言只能 exploratory，或不能引用衝突的任何一側

## 已查文件
- SPEC-REDPACKET-001 v0.1（590d35efdb11…）
- SPEC-SYSADMIN-001 v0.1（688ddf35ab03…）
- SPEC-REPORTS-001 v0.1（a4ec6b0d93ef…）
- SPEC-SITELIST-001 v0.6（b57f48c699cc…）
- SPEC-PLATFORMRULE-001 v0.2（b36b764b7756…）
- SPEC-DAILYREPORT-001 v0.2（7930c1fb9c11…）
- SPEC-ARCADE-001 v0.7（0e216890e8a3…）
- SPEC-REDPACKET-002 v0.1（71bd6dd03dc4…）
- SPEC-CASHFLOW-001 v0.1（b34624219b5a…）
- SPEC-COMMON-001 v0.2（d31569007fd5…）

## 已確定的部分
- SPEC-REDPACKET-001 v0.1 §活動排程（第 193 行）：「輸入新的總預算（須大於目前總預算）」
- SPEC-REDPACKET-002 v0.1 L987 confirmBudget()：「if(!(v>a.budget)){setErr('field-newbudget');return;}」

## 還需決定的事
新總預算小於或等於目前總預算時，後端是否同樣拒絕及其回應（狀態碼與訊息）；前端行為已由 SPEC-REDPACKET-002@0.1 confirmBudget() 定義（見 Q05）
- 細節：backend_enforcement
- 細節：backend_response

## PM 回覆
（待回覆）

