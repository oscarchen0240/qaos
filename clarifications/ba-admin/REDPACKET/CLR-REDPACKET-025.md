# CLR-REDPACKET-025：紅包金額欄的位置、是否進總計列與 CSV、在「依場次明細」維度的值（場次歸屬見 REQ-REDPACKET-025 Q02），以及營業日依入帳時間歸屬的確認

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
- SPEC-COMMON-001 v0.2（d31569007fd5…）

## 已確定的部分
- SPEC-DAILYREPORT-001 v0.2 §列表欄位（第 68 行）：「期末餘額 ＝ 期初餘額 ＋ 開分金額 ＋ 進鈔金額 ＋ 損益 － 洗分金額 － 收據金額」

## 還需決定的事
紅包金額欄的位置、是否進總計列與 CSV、在「依場次明細」維度的值（場次歸屬見 REQ-REDPACKET-025 Q02），以及營業日依入帳時間歸屬的確認
- 細節：column_position
- 細節：total_and_csv
- 細節：session_dimension_value

## PM 回覆
（待回覆）

