# CLR-SCREENMGMT-001：機台場館（核心貨幣 TWD）的遊戲商上架清單，是否應在畫面管理／遊戲商管理層級過濾掉不支援 TWD 的遊戲商（如 AMB）？

- 產品 / 功能：ba-admin / SCREENMGMT
- 規格：SPEC-SITELIST-001 v0.4
- 相關需求：—
- 提出者：oscarchen@blockaction.tech（2026-09-13）
- 狀態：APPLIED

## 背景
站台列表_spec_v04 定案機台場館核心貨幣固定 TWD，但所有機台相關 spec 皆未定義遊戲商上架清單是否依幣別過濾。實測 AMB（僅支援 USDT）仍出現在 Violet Arcade 前台 TAB，遊戲名稱顯示內部代碼、圖示破圖（見 MAN-20260913-015 / EVD）。已排除 locale 因素。

## 可能的解讀（請勾選或補充）
- [ ] 在畫面管理／遊戲商管理層級過濾，只允許支援 TWD 的遊戲商上架
- [ ] 允許所有遊戲商上架，由前端做幣別轉換或提示不支援

## 若未回答的影響
在 PM 定案前，MAN-015 無法判定為 Bug（Bug Validator 會判 AMBIGUITY）；相關 TC 無法設計

## PM 回覆
未來在 prod 先由人工幫廠商關閉不支援的遊戲與遊戲商；系統面目前未規劃自動過濾。→ MAN-015 不是 bug，屬作業流程；待未來有設計再開 spec。
— PM（2026-09-13，經 Oscar 轉達），2026-09-13，落地方式：no_change
