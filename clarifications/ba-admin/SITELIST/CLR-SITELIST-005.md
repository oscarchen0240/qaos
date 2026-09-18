# CLR-SITELIST-005：REQ-SITELIST-012 不符合時系統應如何反應？（Spec 未定義拒絕行為）

- 產品 / 功能：ba-admin / SITELIST
- 規格：SPEC-SITELIST-001 v0.4  §§角色與權限 + §操作/新增站台
- 相關需求：REQ-SITELIST-012
- 提出者：agent-spec-analyst（2026-09-13）
- 狀態：APPLIED

## 背景
Admin 新增站台時可自由選取上層站台（留空為根層）；站長新增站台時上層站台固定為當前所在層，不可修改
Spec 只定義前端行為（站長欄位唯讀）；未定義若站長繞過前端直接呼叫建立站台 API 並帶入其他上層站台時，後端是否拒絕——此為已知風險區域，Test Designer 應設計對應的負向／探索性案例

## 可能的解讀（請勾選或補充）
- （無預設選項，請自由回答）

## 若未回答的影響
Test Designer 只能以 exploratory（假設）方式撰寫此需求的負向案例，expected 需 Human 確認

## PM 回覆
已修改：站長不可自由選取上層站台，需點進不同子站後新增站台，上層站台選單會自動帶入其選擇的站台；後端已拒絕（不接受繞過前端指定其他上層站台）。此前 RD 回報的「直接呼叫 API 仍會成功」風險已修復。
— PM（2026-09-14，經 Oscar 轉達），2026-09-13，落地方式：requirement_clarified
