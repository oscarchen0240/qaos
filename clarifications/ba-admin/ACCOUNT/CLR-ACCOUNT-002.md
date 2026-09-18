# CLR-ACCOUNT-002：REQ-ACCOUNT-016 不符合時系統應如何反應？（Spec 未定義拒絕行為）

- 產品 / 功能：ba-admin / ACCOUNT
- 規格：SPEC-ACCOUNT-001 v0.1  §§前台忘記密碼（線上會員）
- 相關需求：REQ-ACCOUNT-016
- 提出者：agent-spec-analyst（2026-09-13）
- 狀態：APPLIED

## 背景
會員於前台輸入帳號與綁定的電子信箱，相符時系統寄送具時效（預設 1 小時）的重設連結；逾時失效需重新申請，重新申請會使先前尚未使用的連結失效；點擊連結設定新密碼後舊密碼立即失效
Spec 未定義已使用過的連結被再次點擊時系統的具體回應

## 可能的解讀（請勾選或補充）
- （無預設選項，請自由回答）

## 若未回答的影響
Test Designer 只能以 exploratory（假設）方式撰寫此需求的負向案例，expected 需 Human 確認

## PM 回覆
前端顯示「連結已失效，請重新申請」。
— PM（2026-09-14，經 Oscar 轉達），2026-09-13，落地方式：requirement_clarified
