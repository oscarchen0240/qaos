# CLR-REDPACKET-050：紅包金額欄在列表中的位置；「依場次明細」維度的紅包金額與期初／期末餘額如何計入（依 REQ-REDPACKET-025 Q02 的場次歸屬）。營業日依入帳歸屬（第 350 行「當日已入帳」）見 Q01，總計列與 CSV 見 Q03

- 產品 / 功能：ba-admin / REDPACKET
- 規格：SPEC-REDPACKET-001 v0.1  §§對既有章節的影響 L350
- 相關需求：REQ-REDPACKET-032
- 提出者：agent-spec-analyst（2026-10-08）
- 狀態：OPEN

## 背景
REQ-REDPACKET-032：場館日結報表新增「紅包金額」欄（當日已入帳紅包合計）；餘額驗算式改為 期末餘額 ＝ 期初餘額 ＋ 開分 ＋ 進鈔 ＋ 紅包金額 ＋ 損益 － 洗分 － 收據；現金淨收不變（紅包無現金流入）。

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
- SPEC-REDPACKET-002 v0.1（71bd6dd03dc4…）
- SPEC-CASHFLOW-001 v0.1（b34624219b5a…）
- SPEC-COMMON-001 v0.2（d31569007fd5…）

## 已確定的部分
- SPEC-DAILYREPORT-001 v0.2 §列表欄位（第 68 行）：「期末餘額 ＝ 期初餘額 ＋ 開分金額 ＋ 進鈔金額 ＋ 損益 － 洗分金額 － 收據金額」
- SPEC-DAILYREPORT-001 v0.2 §列表欄位（第 57 行）：「「依場次明細」維度即顯示該場次的期初餘額」

## 還需決定的事
紅包金額欄在列表中的位置；「依場次明細」維度的紅包金額與期初／期末餘額如何計入（依 REQ-REDPACKET-025 Q02 的場次歸屬）。營業日依入帳歸屬（第 350 行「當日已入帳」）見 Q01，總計列與 CSV 見 Q03
- 細節：column_position
- 細節：session_dimension_value

## PM 回覆
（待回覆）

