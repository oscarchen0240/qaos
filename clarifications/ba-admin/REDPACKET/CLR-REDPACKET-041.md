# CLR-REDPACKET-041：操作員在機台場館紅包明細的「唯讀」是否包含「匯出 CSV」（目標第 257 行只寫自身場館唯讀；進入路徑已由 Q04 定義）

- 產品 / 功能：ba-admin / REDPACKET
- 規格：SPEC-REDPACKET-001 v0.1  §§角色與權限 L256
- 相關需求：REQ-REDPACKET-024
- 提出者：agent-spec-analyst（2026-10-08）
- 狀態：OPEN

## 背景
REQ-REDPACKET-024：機台場館：新增紅包活動／追加預算／取消排程——管理員、站長可操作，操作員不可；紅包明細——管理員、站長為管轄範圍，操作員為自身場館（唯讀）。操作員可經 優惠活動管理 > 活動排程 > 紅包活動 進入自身場館的紅包明細（紅包明細的功能路徑，第 201 行）。

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
- SPEC-REDPACKET-001 v0.1 §角色與權限（第 257 行）：「| 紅包明細 | 管轄範圍 | 管轄範圍 | 自身場館（唯讀） |」
- SPEC-REDPACKET-001 v0.1 §紅包明細（第 246 行）：「頁面右上角提供「匯出 CSV」，匯出整個查詢結果。」

## 還需決定的事
操作員在機台場館紅包明細的「唯讀」是否包含「匯出 CSV」（目標第 257 行只寫自身場館唯讀；進入路徑已由 Q04 定義）
- 細節：csv_export

## PM 回覆
（待回覆）

