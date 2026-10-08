# CLR-REDPACKET-007：機台帳號的紅包入帳在 4.1 機台視角（交易類型篩選、場次編號、核實狀態、來源等欄位）如何呈現；4.4 稽核明細機台帳號的紅包列欄位與單位（現列為 USDT）

- 產品 / 功能：ba-admin / REDPACKET
- 規格：SPEC-REDPACKET-001 v0.1  §§業務規則與驗證 L326
- 相關需求：REQ-REDPACKET-014
- 提出者：agent-spec-analyst（2026-10-08）
- 狀態：OPEN

## 背景
REQ-REDPACKET-014：玩家開啟紅包即以核心貨幣入帳至錢包（不經 3.3 優惠彩金審核、不提供線下給付）；入帳時寫入 4.1 交易紀錄（交易類型「紅包」，正值），所需有效投注額增加 紅包金額 × 稽核倍數（稽核倍數取自產生當下適用的規則），寫入 4.4 稽核明細（類型「紅包」）。

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
- SPEC-ARCADE-001 v0.7 §機台交易紀錄（第 564 行）：「| 交易類型 | 下拉選單 | 全部 / 機台開分 / 機台洗分 / 機台入金 / 機台出金 |」

## 還需決定的事
機台帳號的紅包入帳在 4.1 機台視角（交易類型篩選、場次編號、核實狀態、來源等欄位）如何呈現；4.4 稽核明細機台帳號的紅包列欄位與單位（現列為 USDT）
- 細節：arcade_view_type_filter
- 細節：session_column
- 細節：amount_unit

## PM 回覆
（待回覆）

