# CLR-REDPACKET-022：櫃檯對機台帳號人工出金（或人工入金）是否視同出金而作廢待開啟紅包；出金停在「待確認」（不設逾時）期間紅包是否一直不可開啟，Admin 手動取消或被新出金取代時是否恢復；過渡期由前台完成的出金是否同樣適用

- 產品 / 功能：ba-admin / REDPACKET
- 規格：SPEC-REDPACKET-001 v0.1  §§業務規則與驗證 L328
- 相關需求：REQ-REDPACKET-028
- 提出者：agent-spec-analyst（2026-10-08）
- 狀態：OPEN

## 背景
REQ-REDPACKET-028：機台帳號完成洗分或出金（扣分成功）當下，該帳號待開啟紅包作廢（作廢原因機台洗分／機台出金），累計進度不歸零。紅包入帳與機台洗分／出金使用同一把帳號鎖：洗分或出金請求送出後、交易完成前，紅包不可開啟；交易完成依上述作廢，交易取消或未成立則恢復可開啟。

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
- SPEC-COMMON-001 v0.2（d31569007fd5…）

## 已確定的部分
- SPEC-ARCADE-001 v0.7 §業務規則與驗證（第 827 行）：「櫃檯對機台帳號人工出金時，必須同時取消該機台尚未完成的出金」
- SPEC-ARCADE-001 v0.7 §業務規則與驗證（第 829 行）：「出金：不設逾時，待確認保留至完成、被新出金取代、人工出金連動取消或 Admin 手動取消為止」

## 還需決定的事
櫃檯對機台帳號人工出金（或人工入金）是否視同出金而作廢待開啟紅包；出金停在「待確認」（不設逾時）期間紅包是否一直不可開啟，Admin 手動取消或被新出金取代時是否恢復；過渡期由前台完成的出金是否同樣適用
- 細節：manual_cashout_void
- 細節：pending_cashout_lock_duration
- 細節：admin_cancel_restore

## PM 回覆
（待回覆）

