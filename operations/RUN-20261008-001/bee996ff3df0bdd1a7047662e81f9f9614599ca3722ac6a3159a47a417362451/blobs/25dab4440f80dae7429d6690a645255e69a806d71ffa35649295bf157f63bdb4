# CLR-REDPACKET-004：已計入累計的注單事後被取消、派彩取消、廢除取消結算或重新結算時，累計是否扣回；若已因此產生紅包（待開啟或已入帳），是否作廢或追回

- 產品 / 功能：ba-admin / REDPACKET
- 規格：SPEC-REDPACKET-001 v0.1  §§業務規則與驗證 L309
- 相關需求：REQ-REDPACKET-008
- 提出者：agent-spec-analyst（2026-10-08）
- 狀態：OPEN

## 背景
REQ-REDPACKET-008：累計基準為有效流水貢獻（有效投注額 × 貢獻系數），以注單結算時點計入，只計以「活動幣種」下注的注單；貢獻系數為 0 的遊戲不計入。非核心貨幣注單的有效流水貢獻於注單結算當下依系統匯率（幣安 API）換算為核心貨幣後計入，換算後不因匯率變動重算。

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
- SPEC-REPORTS-001 v0.1 §4.2.1 篩選器（第 69 行）：「注單取消、派彩取消、廢除取消下注、廢除取消結算」

## 還需決定的事
已計入累計的注單事後被取消、派彩取消、廢除取消結算或重新結算時，累計是否扣回；若已因此產生紅包（待開啟或已入帳），是否作廢或追回
- 細節：accumulation_reversal
- 細節：generated_packet_handling

## PM 回覆
（待回覆）

