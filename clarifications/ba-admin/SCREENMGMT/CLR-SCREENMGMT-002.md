# CLR-SCREENMGMT-002：「畫面管理」的「前台顯示」開關 OFF 時，預期效果是否包含隱藏前台底部導覽 TAB 與其下遊戲？目前沒有畫面管理的 spec

- 產品 / 功能：ba-admin / SCREENMGMT
- 規格：SPEC-ARCADE-001 v0.7
- 相關需求：—
- 提出者：oscarchen@blockaction.tech（2026-09-13）
- 狀態：APPLIED

## 背景
實測四個娛樂城區塊前台顯示皆 OFF 後，首頁區塊卡片隱藏，但底部 TAB 與 TAB 內遊戲仍完整可玩；只有在遊戲商管理逐一停用所有遊戲，TAB 才消失（見 MAN-20260913-016 / EVD 圖 1–6）。開發包與正本 v07 均無畫面管理章節。

## 可能的解讀（請勾選或補充）
- [ ] OFF 應等價於隱藏 TAB 與遊戲（與遊戲商管理全數停用同效）
- [ ] OFF 僅影響首頁區塊卡片（現況即正確，需補 spec 說明）

## 若未回答的影響
需 PM 提供畫面管理 spec 或定案；定案前無法開正式 Bug

## PM 回覆
定案：畫面管理的區塊「前台顯示」OFF 時，該區塊內容全部隱藏（含前台 TAB 與其下遊戲），不需同時到遊戲商管理停用遊戲。→ 現況只隱藏首頁卡片，MAN-016 成立為 bug；需先有畫面管理 spec / requirement 才能走 WF-B。
【2026-09-14 補充】已修復：後台畫面管理 GA 區塊前台顯示 OFF 後，前台底部導覽只剩 S PLUS / RSG / ATG，GA 未顯示（截圖）。MAN-20260913-016 的問題已由 RD 修正，尚未開成正式 Bug（待 SPEC-SCREENMGMT-001 草稿確認後，可補開並直接 resolve/verify/close 留紀錄，或只保留人工紀錄）。
— PM（2026-09-13，經 Oscar 轉達），2026-09-13，落地方式：requirement_clarified
