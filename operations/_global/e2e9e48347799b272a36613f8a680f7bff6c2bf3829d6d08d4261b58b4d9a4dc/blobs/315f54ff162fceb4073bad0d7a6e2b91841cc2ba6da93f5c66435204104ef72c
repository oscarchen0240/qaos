# CLR-CASHFLOW-010：過渡期 req-cashout 成功後 end-cashout 失敗時，前台的重送策略為何（重試次數、間隔、放棄條件）？

- 產品 / 功能：ba-admin / CASHFLOW
- 規格：SPEC-CASHFLOW-001 v0.2  §§出金（`req-cashout` → `end-cashout`）（第 347 行）
- 相關需求：REQ-CASHFLOW-043
- 提出者：agent-spec-analyst（2026-10-12）
- 狀態：ASKED

## 背景
REQ-CASHFLOW-043：req-cashout 成功後，若前台呼叫 end-cashout 失敗，前台的重送策略 spec 明確標註待確認；前台無法補送時交易停在 PENDING，依既有人工出金連動取消處理

## 可能的解讀（請勾選或補充）
- （無預設選項，請自由回答）

## 若未回答的影響
依賴此決策點的斷言只能 exploratory，或不能引用衝突的任何一側

## 已查文件
- SPEC-CASHFLOW-001 v0.2（b1e2c55628b9…）

## 已確定的部分
- SPEC-CASHFLOW-001 v0.2 §出金（`req-cashout` → `end-cashout`）（第 347 行）：「`req-cashout` 成功後 `end-cashout` 失敗時前台的重送策略；前台無法補送時交易停在 PENDING，依既有人工出金連動取消處理」
- SPEC-CASHFLOW-001 v0.2 §出金（第 158 行）：「前台在完成回報失敗時的重送策略待前台定案」

## 還需決定的事
過渡期 req-cashout 成功後 end-cashout 失敗時，前台的重送策略為何（重試次數、間隔、放棄條件）？
- 細節：spec v0.2 仍標「待確認／待前台定案」；無法補送時停在 PENDING 的收斂路徑已定義（人工出金連動取消；另見 REQ-CASHFLOW-026 管理員手動取消）

## PM 回覆
（待回覆）

