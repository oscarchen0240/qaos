# CLR-REDPACKET-037：CSV 的欄位清單與順序、是否含總計列、狀態與作廢原因的輸出文字、時間格式（SPEC-REDPACKET-002@0.1 的匯出只是示意 toast，未定義檔案內容）

- 產品 / 功能：ba-admin / REDPACKET
- 規格：SPEC-REDPACKET-001 v0.1  §§紅包明細 L230
- 相關需求：REQ-REDPACKET-022
- 提出者：agent-spec-analyst（2026-10-08）
- 狀態：OPEN

## 背景
REQ-REDPACKET-022：紅包明細（優惠活動管理 > 活動排程 > 紅包活動 > 點擊活動名稱）列出該活動所有紅包。篩選：會員編號（多筆以「,」分隔；機台場館即機台帳號）、規則（僅有等級規則的活動顯示）、紅包狀態、產生時間（UTC+0）；搜尋／清除。列表欄位：紅包編號、會員編號、適用規則（產生當下的規則與序號・等級名稱，切換方案後不改寫；機台固定「預設規則」）、場次編號（產生當下的場次，僅供爭議追溯；線上顯示「—」）、產生時間、週期累計、紅包金額、稽核倍數、狀態、入帳時間、作廢原因（週期重置／活動結束／機台洗分／機台出金）。列表底部顯示篩選結果的紅包金額總計（僅計已入帳）；右上角「匯出 CSV」匯出整個查詢結果。

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
- SPEC-REDPACKET-001 v0.1 §紅包明細（第 246 行）：「頁面右上角提供「匯出 CSV」，匯出整個查詢結果。」
- SPEC-REDPACKET-002 v0.1 L413 紅包明細 匯出 CSV：「showToast('匯出整個查詢結果為 CSV（示意）')」

## 還需決定的事
CSV 的欄位清單與順序、是否含總計列、狀態與作廢原因的輸出文字、時間格式（SPEC-REDPACKET-002@0.1 的匯出只是示意 toast，未定義檔案內容）
- 細節：csv_columns
- 細節：total_row
- 細節：datetime_format

## PM 回覆
（待回覆）

