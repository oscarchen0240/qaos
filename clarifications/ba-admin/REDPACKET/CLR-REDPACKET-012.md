# CLR-REDPACKET-012：試算數值的顯示格式：期望金額與最高成本的小數位數、成本占比以百分比或比值顯示及其位數

- 產品 / 功能：ba-admin / REDPACKET
- 規格：SPEC-REDPACKET-001 v0.1  §§新增優惠活動 — 紅包 L123
- 相關需求：REQ-REDPACKET-019
- 提出者：agent-spec-analyst（2026-10-08）
- 狀態：OPEN

## 背景
REQ-REDPACKET-019：成本試算由系統自動計算、不可編輯，每個規則各自計算並顯示於該規則區塊：單個紅包期望金額＝Σ（各獎項金額 × 中獎機率），固定金額時即紅包金額；每帳號單週期最高成本＝權重表最大獎項金額（或固定金額）× 單週期發放上限；成本占比＝單個紅包期望金額 ÷ 累積門檻；預算約可發放＝活動總預算 ÷ 該規則單個紅包期望金額（無條件捨去），未設總預算時顯示「不限」。

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
- 缺：互動原型 protos/紅包_proto_v01.html（SPEC-REDPACKET-001 v0.1 第 9 行提到）

## 已確定的部分
- SPEC-REDPACKET-001 v0.1 §新增優惠活動 — 紅包（第 125 行）：「代表平台每收 100 有效流水貢獻回饋多少」

## 還需決定的事
試算數值的顯示格式：期望金額與最高成本的小數位數、成本占比以百分比或比值顯示及其位數
- 細節：decimal_places
- 細節：ratio_format

## PM 回覆
（待回覆）

