# Bug Repository 總索引

- 更新：2026-10-01  · 共 9 筆

| 產品 / 功能 | ID | 狀態 | 嚴重度 | 標題 |
|---|---|---|---|---|
| [ba-admin/CASHFLOW](ba-admin/CASHFLOW/index.md) | BUG-CASHFLOW-001 | CLOSED | critical | [前後台][機台站台] 站台核心貨幣對應的錢包幣別(TWD)停用後，出金/洗分仍可成功執行，未被阻擋 |
| [ba-admin/CASHFLOW](ba-admin/CASHFLOW/index.md) | BUG-CASHFLOW-002 | CLOSED | critical | [後端][Arcade] 入金額度上限判定發生在 end-cashin 而非 req-cashin，且超額交易完全未留下交易紀錄 |
| [ba-admin/DAILYREPORT](ba-admin/DAILYREPORT/index.md) | BUG-DAILYREPORT-001 | CLOSED | major | [後端][機台][場館日結報表] 依場館彙總／依機台明細維度的 API 回應缺少「場次數」欄位 |
| [ba-admin/DAILYREPORT](ba-admin/DAILYREPORT/index.md) | BUG-DAILYREPORT-002 | CLOSED | major | [後端][機台][場館日結報表] 依場次明細維度的 API 回應缺少「開始時間」與「場次時長」欄位 |
| [ba-admin/DAILYREPORT](ba-admin/DAILYREPORT/index.md) | BUG-DAILYREPORT-003 | CLOSED | major | [後台][Arcade][後端][場館日結報表] 結算日期起日晚於迄日時 API 仍回傳資料，未依定案回空列表 |
| [ba-admin/DAILYREPORT](ba-admin/DAILYREPORT/index.md) | BUG-DAILYREPORT-004 | OPEN | critical | [後台][Arcade][後端][場館日結報表] 跨場次切換點的注單被拆成投注與派彩兩半分記不同場次／營業日，且日結結算場次歸到結束日而非開始的營業日 |
| [ba-admin/DAILYREPORT](ba-admin/DAILYREPORT/index.md) | BUG-DAILYREPORT-005 | OPEN | major | [後台][Arcade][後端][場館日結報表] 依場次明細未列出進行中場次，總計列期末餘額亦未計入進行中場次的分數 |
| [ba-admin/UPDATEPACK](ba-admin/UPDATEPACK/index.md) | BUG-UPDATEPACK-001 | CLOSED | major | [前端/後端][多幣別錢包展開] 帳戶餘額展開清單未依鏈上錢包管理實際啟用狀態產生，出現不存在/未啟用幣別、漏列已啟用幣別 |
| [ba-admin/UPDATEPACK](ba-admin/UPDATEPACK/index.md) | BUG-UPDATEPACK-002 | OPEN | major | [後台][arcade][前端/後端][注單查詢] 注單查詢列表缺少「場次編號」欄位，機台帳號注單無法顯示所屬場次編號 |
