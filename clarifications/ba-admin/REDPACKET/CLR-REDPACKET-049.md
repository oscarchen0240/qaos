# CLR-REDPACKET-049：「週期即將重置」提示從重置前多久開始顯示（SPEC-REDPACKET-002@0.1 不含前台）；「目前累計」的定義見 Q03

- 產品 / 功能：ba-admin / REDPACKET
- 規格：SPEC-REDPACKET-001 v0.1  §§前台呈現說明 L164
- 相關需求：REQ-REDPACKET-031
- 提出者：agent-spec-analyst（2026-10-08）
- 狀態：OPEN

## 背景
REQ-REDPACKET-031：線上前台紅包入口顯示活動名稱、本週期累計進度（目前累計／適用規則的累積門檻）、本週期已產生數／適用規則的發放上限、待開啟紅包數，不顯示規則名稱；會員等級變動後進度與上限即改以新規則顯示。點擊待開啟紅包 → 開啟動畫 → 顯示金額 → 金額即時入錢包。週期即將重置時提示「未開啟的紅包將於重置時作廢」。「本週期累計進度」的目前累計為距下一個紅包已累計的值（第 291 行對「累計進度」的用法），不是本週期累計總額。

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
- SPEC-REDPACKET-001 v0.1 §前台呈現說明（第 167 行）：「週期即將重置時提示「未開啟的紅包將於重置時作廢」」
- SPEC-REDPACKET-001 v0.1 §前台呈現說明（第 176 行）：「前台動畫與版面細節由前台設計另定，本 spec 僅定義觸發時點與資料。」

## 還需決定的事
「週期即將重置」提示從重置前多久開始顯示（SPEC-REDPACKET-002@0.1 不含前台）；「目前累計」的定義見 Q03
- 細節：warning_lead_time

## PM 回覆
（待回覆）

