# CLR-DAILYREPORT-001：REQ-DAILYREPORT-001 不符合時系統應如何反應？（Spec 未定義拒絕行為）

- 產品 / 功能：ba-admin / DAILYREPORT
- 規格：SPEC-DAILYREPORT-001 v0.1  §§功能說明/權限表
- 相關需求：REQ-DAILYREPORT-001
- 提出者：agent-spec-analyst（2026-09-13）
- 狀態：ANSWERED

## 背景
場館日結報表依角色限制可見範圍：Admin 全部；站長 管轄範圍；操作員 自身場館。
Spec 未定義越權（例如操作員切換至非自身場館）時系統的回應：拒絕、隱藏選項或回空資料

## 可能的解讀（請勾選或補充）
- （無預設選項，請自由回答）

## 若未回答的影響
Test Designer 只能以 exploratory（假設）方式撰寫此需求的負向案例，expected 需 Human 確認

## PM 回覆
操作員無權限切換到非自身的場館，前端已擋（站台切換選單不提供其他場館）。註：未回答直接呼叫 API 帶其他站台參數的後端行為，TC-DAILYREPORT-004 的假設仍待確認。
【2026-09-14 補充】後端也擋了：直接呼叫 API 帶非自身場館參數會被後端拒絕。→ TC-DAILYREPORT-004 的假設已解。
— PM（2026-09-13，經 Oscar 轉達），2026-09-13，落地方式：requirement_clarified
