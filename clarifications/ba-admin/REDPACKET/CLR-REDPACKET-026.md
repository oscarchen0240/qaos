# CLR-REDPACKET-026：後端是否同樣拒絕不合法的紅包活動設定（門檻、上限、總預算、活動幣種、等級規則、權重表、活動名稱、活動時間），以及直接呼叫 API 時的回應（狀態碼與訊息）；前端阻擋方式與提示文字已由 SPEC-REDPACKET-002@0.1 saveAdd() 定義（見 Q05）

- 產品 / 功能：ba-admin / REDPACKET
- 規格：SPEC-REDPACKET-001 v0.1  §§業務規則與驗證 L334
- 相關需求：REQ-REDPACKET-003
- 提出者：agent-spec-analyst（2026-10-08）
- 狀態：OPEN

## 背景
REQ-REDPACKET-003：儲存時檢查：活動幣種至少勾選一個；預設規則關閉時至少須有一個等級規則；每個等級規則至少勾選一個等級；一個等級只能屬於一個規則；各生效規則（關閉的預設規則不檢查）的累積門檻須大於 0、單週期發放上限須為大於 0 的整數；總預算有填時須大於 0；權重表至少一列、各列金額須大於 0、機率合計須為 100%（否則阻擋儲存）；活動名稱最多 25 字元。前端驗證（依 SPEC-REDPACKET-002@0.1）：活動時間必填，區間的結束時間須晚於開始時間；活動名稱必填、輸入欄最多 25 字元；權重表最後一列不可移除；稽核倍數可為 0。儲存時任一欄位不合法即不建立，於該欄位以紅框與訊息標示並提示「請修正標示紅框的欄位」。

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
- SPEC-REDPACKET-001 v0.1 §業務規則與驗證（第 334 行）：「累積門檻須大於 0；單週期發放上限須為大於 0 的整數；總預算有填時須大於 0」
- SPEC-REDPACKET-002 v0.1 L891 saveAdd() 前端阻擋：「if(bad){showToast('請修正標示紅框的欄位');return;}」

## 還需決定的事
後端是否同樣拒絕不合法的紅包活動設定（門檻、上限、總預算、活動幣種、等級規則、權重表、活動名稱、活動時間），以及直接呼叫 API 時的回應（狀態碼與訊息）；前端阻擋方式與提示文字已由 SPEC-REDPACKET-002@0.1 saveAdd() 定義（見 Q05）
- 細節：backend_enforcement
- 細節：backend_response

## PM 回覆
（待回覆）

