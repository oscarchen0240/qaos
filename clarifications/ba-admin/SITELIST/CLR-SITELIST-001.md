# CLR-SITELIST-001：REQ-SITELIST-002 不符合時系統應如何反應？（Spec 未定義拒絕行為）

- 產品 / 功能：ba-admin / SITELIST
- 規格：SPEC-SITELIST-001 v0.4  §§站台類型與機台專屬欄位 + §業務規則-站台類型隨主站台
- 相關需求：REQ-SITELIST-002
- 提出者：agent-spec-analyst（2026-09-13）
- 狀態：APPLIED

## 背景
站台類型於主站台（根層）選定，子站台一律與主站台同類型，不可個別選擇
Spec 只描述 UI 唯讀跟隨；未定義若繞過 UI（直接呼叫建立站台 API）帶入與上層站台不同的站台類型時，後端是否也拒絕

## 可能的解讀（請勾選或補充）
- （無預設選項，請自由回答）

## 若未回答的影響
Test Designer 只能以 exploratory（假設）方式撰寫此需求的負向案例，expected 需 Human 確認

## PM 回覆
後端也會拒絕：若透過 API 帶入與上層站台不同的站台類型，後端會擋下，不只是前端唯讀限制。
— PM（2026-09-14，經 Oscar 轉達），2026-09-13，落地方式：requirement_clarified
