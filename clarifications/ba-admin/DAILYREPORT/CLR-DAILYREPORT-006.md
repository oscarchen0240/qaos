# CLR-DAILYREPORT-006：REQ-DAILYREPORT-016 不符合時系統應如何反應？（Spec 未定義拒絕行為）

- 產品 / 功能：ba-admin / DAILYREPORT
- 規格：SPEC-DAILYREPORT-001 v0.1  §§列表欄位末段 + §操作
- 相關需求：REQ-DAILYREPORT-016
- 提出者：agent-spec-analyst（2026-09-13）
- 狀態：ANSWERED

## 背景
列表底部顯示當前篩選結果的各欄總計；頁面右上角「匯出 CSV」匯出當前篩選結果。本頁為統計檢視，不提供新增／編輯／刪除／審核。
Spec 未定義無資料時匯出 CSV 的行為（空檔？停用按鈕？）

## 可能的解讀（請勾選或補充）
- （無預設選項，請自由回答）

## 若未回答的影響
Test Designer 只能以 exploratory（假設）方式撰寫此需求的負向案例，expected 需 Human 確認

## PM 回覆
無資料時列表仍列出，日期正常顯示、各欄位顯示 0。欄位清單（PM 提供）：場館、場次數、開分金額、洗分金額、已核實洗分、待核實洗分、進鈔金額、收據金額、已兌現金額、未兌現金額、現金淨收、注單數、有效投注額、損益、期末餘額。註：此清單含「注單數」，Spec v0.1 列表欄位無此欄 → spec 需補；匯出 CSV 無資料時的行為未明說，推定同列表（一列 0）。
— PM（2026-09-13，經 Oscar 轉達），2026-09-13，落地方式：requirement_clarified
