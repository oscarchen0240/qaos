# CLR-REDPACKET-031：活動進行中修改場館「日結時間」時，當前週期的結束點與後續週期如何切分（是否產生過長／過短週期、待開啟紅包何時作廢）

- 產品 / 功能：ba-admin / REDPACKET
- 規格：SPEC-REDPACKET-001 v0.1  §§業務規則與驗證 L313
- 相關需求：REQ-REDPACKET-011
- 提出者：agent-spec-analyst（2026-10-08）
- 狀態：OPEN

## 背景
REQ-REDPACKET-011：重置方式為每日／每週一／每月 1 日／不重置。線上站台於 UTC+0 00:00 切分；機台場館於場館「日結時間」切分（每週／每月週期亦同），與場館日結報表的營業日對齊；表單提示同時顯示該場館日結時間的 UTC+0 與台灣時間。週期重置時累計歸零，該帳號所有待開啟紅包作廢，已入帳紀錄不受影響。

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
- SPEC-SITELIST-001 v0.6 §操作（第 182 行）：「| 機台專屬欄位 | 可修改（場館幣別唯讀） | 可修改（場館幣別唯讀） |」

## 還需決定的事
活動進行中修改場館「日結時間」時，當前週期的結束點與後續週期如何切分（是否產生過長／過短週期、待開啟紅包何時作廢）
- 細節：cycle_boundary_after_change

## PM 回覆
（待回覆）

