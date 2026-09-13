# Clarifications（待 PM 釐清的需求）

- 更新：2026-09-13

## ba-admin / DAILYREPORT

| ID | 狀態 | 規格 | 問題 | PM 回覆 |
|---|---|---|---|---|
| [CLR-DAILYREPORT-001](ba-admin/DAILYREPORT/CLR-DAILYREPORT-001.md) | ANSWERED | SPEC-DAILYREPORT-001 v0.1 | REQ-DAILYREPORT-001 不符合時系統應如何反應？（Spec 未定義拒絕行為） | 操作員無權限切換到非自身的場館，前端已擋（站台切換選單不提供其他場館）。註：未回答直接呼叫 API 帶其他站台參數的後端 |
| [CLR-DAILYREPORT-002](ba-admin/DAILYREPORT/CLR-DAILYREPORT-002.md) | ANSWERED | SPEC-DAILYREPORT-001 v0.1 | REQ-DAILYREPORT-003 不符合時系統應如何反應？（Spec 未定義拒絕行為） | 輸入不存在或非本場館的機台帳號：找不到用戶即可，API 回 rows: []（空列表，不報錯）。 |
| [CLR-DAILYREPORT-003](ba-admin/DAILYREPORT/CLR-DAILYREPORT-003.md) | ANSWERED | SPEC-DAILYREPORT-001 v0.1 | REQ-DAILYREPORT-004 不符合時系統應如何反應？（Spec 未定義拒絕行為） | 結算日期異常（起日晚於迄日等）：找不到資料即可，API 回 rows: []。註：與 Spec「必填」的關係——未填時是 |
| [CLR-DAILYREPORT-004](ba-admin/DAILYREPORT/CLR-DAILYREPORT-004.md) | ANSWERED | SPEC-DAILYREPORT-001 v0.1 | REQ-DAILYREPORT-007 不符合時系統應如何反應？（Spec 未定義拒絕行為） | 日結時間為場館設定欄位（每日結算的截止時刻，UTC+0），畫面截圖顯示欄位有預設值「上午 12:00」（即 00:00  |
| [CLR-DAILYREPORT-005](ba-admin/DAILYREPORT/CLR-DAILYREPORT-005.md) | ANSWERED | SPEC-DAILYREPORT-001 v0.1 | REQ-DAILYREPORT-011 不符合時系統應如何反應？（Spec 未定義拒絕行為） | 提醒標示的呈現方式如截圖：交易列表中待核實的機台洗分列顯示黃色標籤「⚠ 現金未確認」，核實狀態欄為藍色「待核實」；已核實 |
| [CLR-DAILYREPORT-006](ba-admin/DAILYREPORT/CLR-DAILYREPORT-006.md) | ANSWERED | SPEC-DAILYREPORT-001 v0.1 | REQ-DAILYREPORT-016 不符合時系統應如何反應？（Spec 未定義拒絕行為） | 無資料時列表仍列出，日期正常顯示、各欄位顯示 0。欄位清單（PM 提供）：場館、場次數、開分金額、洗分金額、已核實洗分、 |
| [CLR-DAILYREPORT-007](ba-admin/DAILYREPORT/CLR-DAILYREPORT-007.md) | ANSWERED | SPEC-DAILYREPORT-001 v0.1 | 「當日結束的場次筆數」是否包含狀態為「逾時結束」與「日結結算」的場次？ | 逾時結束的時間會超過日結時間；而 Spec 規定日結時間到達時強制結束所有進行中的場次，因此當日內場次只會以「已結束」或 |
| [CLR-DAILYREPORT-008](ba-admin/DAILYREPORT/CLR-DAILYREPORT-008.md) | ANSWERED | SPEC-DAILYREPORT-001 v0.1 | 按週統計時，結算日期範圍內的不完整週如何顯示與計算？ | 不完整週照實際範圍顯示（截圖：結算日期 09-03 起、按週 → 列出「2026-09-07 ~ 2026-09-13」 |
| [CLR-DAILYREPORT-009](ba-admin/DAILYREPORT/CLR-DAILYREPORT-009.md) | ANSWERED | SPEC-DAILYREPORT-001 v0.1 | 「未兌現金額不受週期影響、累計至查詢當下」是否也不受結算日期範圍限制？ | 受結算日期範圍限制：結算日期仍是篩選條件，未兌現金額只算範圍內；只是不受統計週期切分影響。例：9/10 未兌現 200； |

## ba-admin / PLATFORMRULE

| ID | 狀態 | 規格 | 問題 | PM 回覆 |
|---|---|---|---|---|
| [CLR-PLATFORMRULE-001](ba-admin/PLATFORMRULE/CLR-PLATFORMRULE-001.md) | APPLIED | SPEC-PLATFORMRULE-001 v0.1 | 「站長＝最高權限」的定義是否仍有效？三份 spec 的權限層級互相矛盾 | 以功能 spec 三層模型為準：管理員（最高）＞站長＞操作員。原則：可見範圍由所屬站台決定、權限層級由角色決定，兩者分開 |

## ba-admin / SCREENMGMT

| ID | 狀態 | 規格 | 問題 | PM 回覆 |
|---|---|---|---|---|
| [CLR-SCREENMGMT-001](ba-admin/SCREENMGMT/CLR-SCREENMGMT-001.md) | ANSWERED | SPEC-SITELIST-001 v0.4 | 機台場館（核心貨幣 TWD）的遊戲商上架清單，是否應在畫面管理／遊戲商管理層級過濾掉不支援 TWD 的遊戲商（如 AMB）？ | 未來在 prod 先由人工幫廠商關閉不支援的遊戲與遊戲商；系統面目前未規劃自動過濾。→ MAN-015 不是 bug，屬 |
| [CLR-SCREENMGMT-002](ba-admin/SCREENMGMT/CLR-SCREENMGMT-002.md) | ANSWERED | SPEC-ARCADE-001 v0.7 | 「畫面管理」的「前台顯示」開關 OFF 時，預期效果是否包含隱藏前台底部導覽 TAB 與其下遊戲？目前沒有畫面管理的 spec | 定案：畫面管理的區塊「前台顯示」OFF 時，該區塊內容全部隱藏（含前台 TAB 與其下遊戲），不需同時到遊戲商管理停用遊 |

## ba-admin / SITELIST

| ID | 狀態 | 規格 | 問題 | PM 回覆 |
|---|---|---|---|---|
| [CLR-SITELIST-001](ba-admin/SITELIST/CLR-SITELIST-001.md) | ANSWERED | SPEC-SITELIST-001 v0.4 | REQ-SITELIST-002 不符合時系統應如何反應？（Spec 未定義拒絕行為） | 後端也會拒絕：若透過 API 帶入與上層站台不同的站台類型，後端會擋下，不只是前端唯讀限制。 |
| [CLR-SITELIST-002](ba-admin/SITELIST/CLR-SITELIST-002.md) | ANSWERED | SPEC-SITELIST-001 v0.4 | REQ-SITELIST-005 不符合時系統應如何反應？（Spec 未定義拒絕行為） | 額度上限輸入負數：前端顯示「值必須大於或等於 0」，後端也會拒絕（雙層驗證）。 |
| [CLR-SITELIST-003](ba-admin/SITELIST/CLR-SITELIST-003.md) | ANSWERED | SPEC-SITELIST-001 v0.4 | REQ-SITELIST-006 不符合時系統應如何反應？（Spec 未定義拒絕行為） | 場次逾時時間：後端設計最低值為 1 小時（低於 1 小時會被拒絕）。輸入超過 17 位數（極端格式）時，前端跳格式錯誤， |
| [CLR-SITELIST-004](ba-admin/SITELIST/CLR-SITELIST-004.md) | ANSWERED | SPEC-SITELIST-001 v0.4 | REQ-SITELIST-011 不符合時系統應如何反應？（Spec 未定義拒絕行為） | 以「三個角色的關係」權限範圍圖為準（同 CLR-PLATFORMRULE-001 附圖）：範圍由所屬站台決定，不是角色本 |
| [CLR-SITELIST-005](ba-admin/SITELIST/CLR-SITELIST-005.md) | ANSWERED | SPEC-SITELIST-001 v0.4 | REQ-SITELIST-012 不符合時系統應如何反應？（Spec 未定義拒絕行為） | 已修改：站長不可自由選取上層站台，需點進不同子站後新增站台，上層站台選單會自動帶入其選擇的站台；後端已拒絕（不接受繞過前 |
| [CLR-SITELIST-006](ba-admin/SITELIST/CLR-SITELIST-006.md) | ANSWERED | SPEC-SITELIST-001 v0.4 | REQ-SITELIST-013 不符合時系統應如何反應？（Spec 未定義拒絕行為） | 同 CLR-SITELIST-005：站長於編輯時的上層站台唯讀限制，後端已拒絕繞過前端的修改。（本次確認聚焦於站長權限 |
| [CLR-SITELIST-007](ba-admin/SITELIST/CLR-SITELIST-007.md) | ANSWERED | SPEC-SITELIST-001 v0.4 | REQ-SITELIST-023 不符合時系統應如何反應？（Spec 未定義拒絕行為） | 機台類型站台不提供刪除操作，只能停用（暫停／關閉）；不會出現在確認刪除的流程裡。（原問題「有子站台時如何刪除」對機台類型 |
| [CLR-SITELIST-008](ba-admin/SITELIST/CLR-SITELIST-008.md) | OPEN | SPEC-SITELIST-001 v0.4 | 線上類型的主站台若帶有子站台，執行刪除時系統如何處理其子站台？ |  |
