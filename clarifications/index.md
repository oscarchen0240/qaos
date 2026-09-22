# Clarifications（待 PM 釐清的需求）

- 更新：2026-09-22

## ba-admin / ACCOUNT

| ID | 狀態 | 規格 | 問題 | PM 回覆 |
|---|---|---|---|---|
| [CLR-ACCOUNT-001](ba-admin/ACCOUNT/CLR-ACCOUNT-001.md) | APPLIED | SPEC-ACCOUNT-001 v0.1 | REQ-ACCOUNT-010 不符合時系統應如何反應？（Spec 未定義拒絕行為） | 操作員權限在會員列表裡「創建會員帳號」按鈕隱藏（前端層級，非彈窗開啟後才擋）。 |
| [CLR-ACCOUNT-002](ba-admin/ACCOUNT/CLR-ACCOUNT-002.md) | APPLIED | SPEC-ACCOUNT-001 v0.1 | REQ-ACCOUNT-016 不符合時系統應如何反應？（Spec 未定義拒絕行為） | 前端顯示「連結已失效，請重新申請」。 |
| [CLR-ACCOUNT-003](ba-admin/ACCOUNT/CLR-ACCOUNT-003.md) | APPLIED | SPEC-ACCOUNT-001 v0.1 | REQ-ACCOUNT-018 不符合時系統應如何反應？（Spec 未定義拒絕行為） | 機台帳號無法使用信箱登入註冊，所以前台不存在「忘記密碼」這個功能可用（非送出後才被擋，而是機台帳號本身無法透過此入口操作 |
| [CLR-ACCOUNT-004](ba-admin/ACCOUNT/CLR-ACCOUNT-004.md) | APPLIED | SPEC-ACCOUNT-001 v0.1 | REQ-ACCOUNT-032 不符合時系統應如何反應？（Spec 未定義拒絕行為） | 機台前台沒有優惠活動頁面，玩家（機台）介面上根本無法進入優惠活動或簽到頁面，因此無從參與，不需要後端額外阻擋邏輯。 |
| [CLR-ACCOUNT-005](ba-admin/ACCOUNT/CLR-ACCOUNT-005.md) | APPLIED | SPEC-ACCOUNT-001 v0.1 | 機台場館底下手動建立「線上」型帳號，用途是什麼？行為上是否真的完全比照一般線上會員？額度上限/場館設定是否也套用到它？ | 選項B：機台場館底下建立的「線上」型帳號，雖然帳號類型是線上，但因所屬站台是機台場館，仍需套用該場館的部分設定（例如額度 |

## ba-admin / BONUSCCY

| ID | 狀態 | 規格 | 問題 | PM 回覆 |
|---|---|---|---|---|
| [CLR-BONUSCCY-001](ba-admin/BONUSCCY/CLR-BONUSCCY-001.md) | APPLIED | SPEC-BONUSCCY-001 v1.0 | 「搬站／改站台類型不得讓幣別與站台脫節」的擋阻檢查，具體的重現情境與畫面/錯誤訊息是什麼？ | 選項B：「改站台類型」單純是歷史保留描述，站台類型建立後不可修改（已由 SPEC-SITELIST-001 定案），這條 |
| [CLR-BONUSCCY-002](ba-admin/BONUSCCY/CLR-BONUSCCY-002.md) | APPLIED | SPEC-BONUSCCY-001 v1.0 | 停用站台核心貨幣本身對應的錢包幣別，實際發現：系統允許停用（不阻擋），停用後開分/入金失敗、但出金/洗分仍成功——這是預期設計，還是漏洞？ | 1. 可以停用核心貨幣——這是刻意設計，用途是當資金池出問題時可以即時止損。2. 當鏈上錢包的核心貨幣被關閉時，入金、出 |

## ba-admin / CASHFLOW

| ID | 狀態 | 規格 | 問題 | PM 回覆 |
|---|---|---|---|---|
| [CLR-CASHFLOW-001](ba-admin/CASHFLOW/CLR-CASHFLOW-001.md) | OPEN | SPEC-CASHFLOW-001 v0.1 | REQ-CASHFLOW-042 不符合時系統應如何反應？（Spec 未定義拒絕行為） |  |
| [CLR-CASHFLOW-002](ba-admin/CASHFLOW/CLR-CASHFLOW-002.md) | OPEN | SPEC-CASHFLOW-001 v0.1 | REQ-CASHFLOW-043 不符合時系統應如何反應？（Spec 未定義拒絕行為） |  |
| [CLR-CASHFLOW-003](ba-admin/CASHFLOW/CLR-CASHFLOW-003.md) | WITHDRAWN | SPEC-CASHFLOW-001 v0.1 | 交易紀錄查詢頁的「Admin 手動取消待確認交易」操作，實際上存不存在？ |  |
| [CLR-CASHFLOW-004](ba-admin/CASHFLOW/CLR-CASHFLOW-004.md) | APPLIED | SPEC-CASHFLOW-001 v0.1 | 交易紀錄查詢頁的「手動取消」操作，2026-09-14的確認（REQ-TXLOG-028：此操作不存在）能否請RD重新核實實際畫面？ | 交易紀錄查詢頁確實不存在任何手動取消功能（REQ-TXLOG-028確認正確，維持不變）。所有待核實的交易一律要在「洗分 |

## ba-admin / CASHOUT

| ID | 狀態 | 規格 | 問題 | PM 回覆 |
|---|---|---|---|---|
| [CLR-CASHOUT-001](ba-admin/CASHOUT/CLR-CASHOUT-001.md) | APPLIED | SPEC-CASHOUT-001 v1.0 | TC-DRAFT-01M2R6NEJ7BJH8707E9B1MM8SH / ...VDDAW6 / ...YDRNZ（AC-CASHOUT-0251/0252/0291）的assumption標註『操作員角色的權限範圍(含是否限定單一場館)定義於開發包⑥PLATFORMRULE，該包尚未完成Phase 3測試設計』，此權限規則本身（操作員無權切換場館）是否為過去已規劃定案的既有設計，而非待PLATFORMRULE補完才會定義的規則？ | 操作員無權限切換至其他場館，切換場館的設定在後台管理員系統，此權限只有站長跟admin有權限，這是過去就規劃好的權限事宜 |

## ba-admin / DAILYREPORT

| ID | 狀態 | 規格 | 問題 | PM 回覆 |
|---|---|---|---|---|
| [CLR-DAILYREPORT-001](ba-admin/DAILYREPORT/CLR-DAILYREPORT-001.md) | APPLIED | SPEC-DAILYREPORT-001 v0.1 | REQ-DAILYREPORT-001 不符合時系統應如何反應？（Spec 未定義拒絕行為） | 操作員無權限切換到非自身的場館，前端已擋（站台切換選單不提供其他場館）。註：未回答直接呼叫 API 帶其他站台參數的後端 |
| [CLR-DAILYREPORT-002](ba-admin/DAILYREPORT/CLR-DAILYREPORT-002.md) | APPLIED | SPEC-DAILYREPORT-001 v0.1 | REQ-DAILYREPORT-003 不符合時系統應如何反應？（Spec 未定義拒絕行為） | 輸入不存在或非本場館的機台帳號：找不到用戶即可，API 回 rows: []（空列表，不報錯）。 |
| [CLR-DAILYREPORT-003](ba-admin/DAILYREPORT/CLR-DAILYREPORT-003.md) | APPLIED | SPEC-DAILYREPORT-001 v0.1 | REQ-DAILYREPORT-004 不符合時系統應如何反應？（Spec 未定義拒絕行為） | 結算日期異常（起日晚於迄日等）：找不到資料即可，API 回 rows: []。註：與 Spec「必填」的關係——未填時是 |
| [CLR-DAILYREPORT-004](ba-admin/DAILYREPORT/CLR-DAILYREPORT-004.md) | APPLIED | SPEC-DAILYREPORT-001 v0.1 | REQ-DAILYREPORT-007 不符合時系統應如何反應？（Spec 未定義拒絕行為） | 日結時間為場館設定欄位（每日結算的截止時刻，UTC+0），畫面截圖顯示欄位有預設值「上午 12:00」（即 00:00  |
| [CLR-DAILYREPORT-005](ba-admin/DAILYREPORT/CLR-DAILYREPORT-005.md) | APPLIED | SPEC-DAILYREPORT-001 v0.1 | REQ-DAILYREPORT-011 不符合時系統應如何反應？（Spec 未定義拒絕行為） | 提醒標示的呈現方式如截圖：交易列表中待核實的機台洗分列顯示黃色標籤「⚠ 現金未確認」，核實狀態欄為藍色「待核實」；已核實 |
| [CLR-DAILYREPORT-006](ba-admin/DAILYREPORT/CLR-DAILYREPORT-006.md) | APPLIED | SPEC-DAILYREPORT-001 v0.1 | REQ-DAILYREPORT-016 不符合時系統應如何反應？（Spec 未定義拒絕行為） | 無資料時列表仍列出，日期正常顯示、各欄位顯示 0。欄位清單（PM 提供）：場館、場次數、開分金額、洗分金額、已核實洗分、 |
| [CLR-DAILYREPORT-007](ba-admin/DAILYREPORT/CLR-DAILYREPORT-007.md) | APPLIED | SPEC-DAILYREPORT-001 v0.1 | 「當日結束的場次筆數」是否包含狀態為「逾時結束」與「日結結算」的場次？ | 逾時結束的時間會超過日結時間；而 Spec 規定日結時間到達時強制結束所有進行中的場次，因此當日內場次只會以「已結束」或 |
| [CLR-DAILYREPORT-008](ba-admin/DAILYREPORT/CLR-DAILYREPORT-008.md) | APPLIED | SPEC-DAILYREPORT-001 v0.1 | 按週統計時，結算日期範圍內的不完整週如何顯示與計算？ | 不完整週照實際範圍顯示（截圖：結算日期 09-03 起、按週 → 列出「2026-09-07 ~ 2026-09-13」 |
| [CLR-DAILYREPORT-009](ba-admin/DAILYREPORT/CLR-DAILYREPORT-009.md) | APPLIED | SPEC-DAILYREPORT-001 v0.1 | 「未兌現金額不受週期影響、累計至查詢當下」是否也不受結算日期範圍限制？ | 受結算日期範圍限制：結算日期仍是篩選條件，未兌現金額只算範圍內；只是不受統計週期切分影響。例：9/10 未兌現 200； |
| [CLR-DAILYREPORT-010](ba-admin/DAILYREPORT/CLR-DAILYREPORT-010.md) | APPLIED | SPEC-DAILYREPORT-001 v0.1 | 「已兌現金額」以收據日還是兌現日歸屬？（同一筆出金跨日兌現時，記在出收據那天還是付現那天） | A：已兌現金額以收據日歸屬——「當日出金的收據中，已核實（核銷）者的金額合計」，記在出收據那天，不論實際付現是哪一天（同 |
| [CLR-DAILYREPORT-011](ba-admin/DAILYREPORT/CLR-DAILYREPORT-011.md) | ASKED | SPEC-DAILYREPORT-001 v0.1 | 出金在洗分出金核實頁被「作廢」後，該筆收據金額在場館日結報表如何呈現？ |  |
| [CLR-DAILYREPORT-012](ba-admin/DAILYREPORT/CLR-DAILYREPORT-012.md) | APPLIED | SPEC-DAILYREPORT-001 v0.1 | 場館日結報表「依場次明細」是否應列出進行中的場次（結束時間「—」、時長累計至查詢當下）？ | B：場館日結報表「依場次明細」只列已結束／逾時結束／日結結算的場次，進行中場次不列。現行實作（時長僅於結算時計算一次、明 |

## ba-admin / PLATFORMRULE

| ID | 狀態 | 規格 | 問題 | PM 回覆 |
|---|---|---|---|---|
| [CLR-PLATFORMRULE-001](ba-admin/PLATFORMRULE/CLR-PLATFORMRULE-001.md) | APPLIED | SPEC-PLATFORMRULE-001 v0.1 | 「站長＝最高權限」的定義是否仍有效？三份 spec 的權限層級互相矛盾 | 以功能 spec 三層模型為準：管理員（最高）＞站長＞操作員。原則：可見範圍由所屬站台決定、權限層級由角色決定，兩者分開 |
| [CLR-PLATFORMRULE-002](ba-admin/PLATFORMRULE/CLR-PLATFORMRULE-002.md) | APPLIED | SPEC-PLATFORMRULE-001 v0.1 | REQ-PLATFORMRULE-011 不符合時系統應如何反應？（Spec 未定義拒絕行為） | 此為架構層要求（選單顯示規則需與排除規則同一來源，不得各自寫死），非使用者可觀察行為，且目前無任何排除項目被實際解除、無 |
| [CLR-PLATFORMRULE-003](ba-admin/PLATFORMRULE/CLR-PLATFORMRULE-003.md) | APPLIED | SPEC-PLATFORMRULE-001 v0.1 | 操作員角色是否可見「注單查詢」與「稽核明細」頁面？權限表未列此兩項，請補列定案 | 新需求：操作員有權限進入「注單查詢」與「稽核明細」（可見範圍比照其他報表頁限自身場館）。→ 權限表須補兩列（操作員：自身 |

## ba-admin / SCREENMGMT

| ID | 狀態 | 規格 | 問題 | PM 回覆 |
|---|---|---|---|---|
| [CLR-SCREENMGMT-001](ba-admin/SCREENMGMT/CLR-SCREENMGMT-001.md) | APPLIED | SPEC-SITELIST-001 v0.4 | 機台場館（核心貨幣 TWD）的遊戲商上架清單，是否應在畫面管理／遊戲商管理層級過濾掉不支援 TWD 的遊戲商（如 AMB）？ | 未來在 prod 先由人工幫廠商關閉不支援的遊戲與遊戲商；系統面目前未規劃自動過濾。→ MAN-015 不是 bug，屬 |
| [CLR-SCREENMGMT-002](ba-admin/SCREENMGMT/CLR-SCREENMGMT-002.md) | APPLIED | SPEC-ARCADE-001 v0.7 | 「畫面管理」的「前台顯示」開關 OFF 時，預期效果是否包含隱藏前台底部導覽 TAB 與其下遊戲？目前沒有畫面管理的 spec | 定案：畫面管理的區塊「前台顯示」OFF 時，該區塊內容全部隱藏（含前台 TAB 與其下遊戲），不需同時到遊戲商管理停用遊 |

## ba-admin / SITELIST

| ID | 狀態 | 規格 | 問題 | PM 回覆 |
|---|---|---|---|---|
| [CLR-SITELIST-001](ba-admin/SITELIST/CLR-SITELIST-001.md) | APPLIED | SPEC-SITELIST-001 v0.4 | REQ-SITELIST-002 不符合時系統應如何反應？（Spec 未定義拒絕行為） | 後端也會拒絕：若透過 API 帶入與上層站台不同的站台類型，後端會擋下，不只是前端唯讀限制。 |
| [CLR-SITELIST-002](ba-admin/SITELIST/CLR-SITELIST-002.md) | APPLIED | SPEC-SITELIST-001 v0.4 | REQ-SITELIST-005 不符合時系統應如何反應？（Spec 未定義拒絕行為） | 額度上限輸入負數：前端顯示「值必須大於或等於 0」，後端也會拒絕（雙層驗證）。 |
| [CLR-SITELIST-003](ba-admin/SITELIST/CLR-SITELIST-003.md) | APPLIED | SPEC-SITELIST-001 v0.4 | REQ-SITELIST-006 不符合時系統應如何反應？（Spec 未定義拒絕行為） | 場次逾時時間：後端設計最低值為 1 小時（低於 1 小時會被拒絕）。輸入超過 17 位數（極端格式）時，前端跳格式錯誤， |
| [CLR-SITELIST-004](ba-admin/SITELIST/CLR-SITELIST-004.md) | APPLIED | SPEC-SITELIST-001 v0.4 | REQ-SITELIST-011 不符合時系統應如何反應？（Spec 未定義拒絕行為） | 以「三個角色的關係」權限範圍圖為準（同 CLR-PLATFORMRULE-001 附圖）：範圍由所屬站台決定，不是角色本 |
| [CLR-SITELIST-005](ba-admin/SITELIST/CLR-SITELIST-005.md) | APPLIED | SPEC-SITELIST-001 v0.4 | REQ-SITELIST-012 不符合時系統應如何反應？（Spec 未定義拒絕行為） | 已修改：站長不可自由選取上層站台，需點進不同子站後新增站台，上層站台選單會自動帶入其選擇的站台；後端已拒絕（不接受繞過前 |
| [CLR-SITELIST-006](ba-admin/SITELIST/CLR-SITELIST-006.md) | APPLIED | SPEC-SITELIST-001 v0.4 | REQ-SITELIST-013 不符合時系統應如何反應？（Spec 未定義拒絕行為） | 同 CLR-SITELIST-005：站長於編輯時的上層站台唯讀限制，後端已拒絕繞過前端的修改。（本次確認聚焦於站長權限 |
| [CLR-SITELIST-007](ba-admin/SITELIST/CLR-SITELIST-007.md) | APPLIED | SPEC-SITELIST-001 v0.4 | REQ-SITELIST-023 不符合時系統應如何反應？（Spec 未定義拒絕行為） | 機台類型站台不提供刪除操作，只能停用（暫停／關閉）；不會出現在確認刪除的流程裡。（原問題「有子站台時如何刪除」對機台類型 |
| [CLR-SITELIST-008](ba-admin/SITELIST/CLR-SITELIST-008.md) | APPLIED | SPEC-SITELIST-001 v0.4 | 線上類型的主站台若帶有子站台，執行刪除時系統如何處理其子站台？ | 不論線上或機台類型，站台皆不支援刪除功能，僅能暫停或關閉（停用）。此為對 spec 原文「刪除站台」一節（點擊列表刪除、 |
| [CLR-SITELIST-009](ba-admin/SITELIST/CLR-SITELIST-009.md) | APPLIED | SPEC-SITELIST-001 v0.4 | CLR-SITELIST-008 回答「任何類型皆不可刪除」，這是指前端限制、後端也限制、還是回答有誤（可能指別的情境）？ | 已確認：前端與後端皆拒絕刪除站台，不論線上或機台類型皆同（與 CLR-SITELIST-008 的結論一致，非誤答）。原 |
| [CLR-SITELIST-010](ba-admin/SITELIST/CLR-SITELIST-010.md) | APPLIED | SPEC-SITELIST-001 v0.4 | REQ-SITELIST-002「子站台強制跟隨主站台型別」規則，是否對根層站台（無上層站台，隱含上層為 admin）有例外？ | admin 例外規則為 PM 最終決定，非資料錯誤或臆測：根層站台（無上層站台）建立時，型別可自由選擇（機台或線上），核 |
| [CLR-SITELIST-011](ba-admin/SITELIST/CLR-SITELIST-011.md) | APPLIED | SPEC-SITELIST-001 v0.4 | AC-SITELIST-0023「核心貨幣依所選類型連動建立，不需admin自身的鏈上錢包管理預先啟用該幣別」這句話裡，鏈上錢包管理跟站台核心貨幣是什麼關係？ | 鏈上錢包管理與站台核心貨幣是兩個完全不同、互不相依的概念。鏈上錢包管理管理的是「此平台整體能使用的幣種有哪些」，啟用/禁 |
| [CLR-SITELIST-012](ba-admin/SITELIST/CLR-SITELIST-012.md) | APPLIED | SPEC-SITELIST-001 v0.4 | 修正CLR-SITELIST-011：鏈上錢包管理與站台核心貨幣的精確關係為何？ | 修正CLR-SITELIST-011：鏈上錢包管理與站台核心貨幣不是「完全無關」，而是「性質不同但有連動關係」。(1)鏈 |

## ba-admin / TXLOG

| ID | 狀態 | 規格 | 問題 | PM 回覆 |
|---|---|---|---|---|
| [CLR-TXLOG-001](ba-admin/TXLOG/CLR-TXLOG-001.md) | APPLIED | SPEC-TXLOG-001 v0.1 | REQ-TXLOG-029 不符合時系統應如何反應？（Spec 未定義拒絕行為） | 此問題已 moot：交易紀錄查詢頁（本包）實際上並不提供『手動取消』這個操作，spec.md §操作 描述的『手動取消： |
