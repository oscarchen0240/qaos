# CLR-SITELIST-006：REQ-SITELIST-013 不符合時系統應如何反應？（Spec 未定義拒絕行為）

- 產品 / 功能：ba-admin / SITELIST
- 規格：SPEC-SITELIST-001 v0.4  §§角色與權限 + §操作/編輯站台 + §業務規則-上層站台循環防護
- 相關需求：REQ-SITELIST-013
- 提出者：agent-spec-analyst（2026-09-13）
- 狀態：ANSWERED

## 背景
Admin 編輯時可修改上層站台，選取時自動排除自身及子站台；站長編輯時唯讀顯示，如需變更須通知 Admin
Spec 只定義 UI 選單排除循環選項；未定義若繞過 UI 直接呼叫編輯 API 帶入會形成循環的上層站台 ID 時，後端是否驗證並拒絕

## 可能的解讀（請勾選或補充）
- （無預設選項，請自由回答）

## 若未回答的影響
Test Designer 只能以 exploratory（假設）方式撰寫此需求的負向案例，expected 需 Human 確認

## PM 回覆
同 CLR-SITELIST-005：站長於編輯時的上層站台唯讀限制，後端已拒絕繞過前端的修改。（本次確認聚焦於站長權限；Admin 編輯時的循環防護是否也有對應後端驗證，未在本次回覆中明確涵蓋，若後續測試發現可繞過，需另案處理）
— PM（2026-09-14，經 Oscar 轉達），2026-09-13，落地方式：requirement_clarified
