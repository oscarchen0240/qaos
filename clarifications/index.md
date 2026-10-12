# Clarifications（待 PM 釐清的需求）

- 更新：2026-10-12

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
| [CLR-CASHFLOW-005](ba-admin/CASHFLOW/CLR-CASHFLOW-005.md) | APPLIED | SPEC-CASHFLOW-001 v0.1 | 入金額度上限的判定時機：req-cashin 階段判定（spec v07 定案文字）還是 end-cashin 階段判定（RD 2026-09-23 確認的實際開發流程）？ | A：以 RD 確認為準。額度上限實際於 end-cashin（入鈔機清點確認完成後）判定，這是防禦性設計——req-ca |
| [CLR-CASHFLOW-006](ba-admin/CASHFLOW/CLR-CASHFLOW-006.md) | APPLIED | SPEC-CASHFLOW-001 v0.1 | 額度上限被拒絕（1-OVER LIMIT）是否比照餘額不足（1-NO CREDITS），不寫入交易紀錄？ | B：所有未成立原因一律不寫入交易紀錄，不只額度上限。交易紀錄查詢／機台交易紀錄僅會顯示已完成、待確認、已取消、已逾時四種 |
| [CLR-CASHFLOW-007](ba-admin/CASHFLOW/CLR-CASHFLOW-007.md) | ANSWERED | SPEC-CASHFLOW-001 v0.1 | 機台餘額帶小數（例如 399.6）時出金，收據面額與櫃檯付現要怎麼處理？櫃檯只能付到個位數，小數部分（0.6）要捨去、四捨五入、進位，還是留在機台上？門檻為 0 的全額洗分是否比照？ | 依 SPEC-CASHFLOW-001 v0.2（2026-10-05 定案，第 127、168、336、360 行）： |
| [CLR-CASHFLOW-008](ba-admin/CASHFLOW/CLR-CASHFLOW-008.md) | INCORPORATED | SPEC-CASHFLOW-001 v0.1 | 待確認出金（PENDING）是否可由管理員手動取消收斂？REQ-CASHFLOW-026 依 2026-09-15 CLR-CASHFLOW-004 移除了「Admin 手動取消」路徑，只剩新 req-cashout 取代與人工出金連動取消，與 spec 原文及 CLR-REDPACKET-055 最新答案不一致；入金 PENDING 是否同樣可手動取消？ | 可以。待確認出金（PENDING）的收斂路徑恢復為三條：被新的 req-cashout 取代、櫃檯人工出金連動取消、管理 |
| [CLR-CASHFLOW-009](ba-admin/CASHFLOW/CLR-CASHFLOW-009.md) | OPEN | SPEC-CASHFLOW-001 v0.2 | 過渡期由前台呼叫 req-cashout／end-cashout 時使用何種認證：沿用機台憑證（JWT）或另立前台認證？ |  |
| [CLR-CASHFLOW-010](ba-admin/CASHFLOW/CLR-CASHFLOW-010.md) | OPEN | SPEC-CASHFLOW-001 v0.2 | 過渡期 req-cashout 成功後 end-cashout 失敗時，前台的重送策略為何（重試次數、間隔、放棄條件）？ |  |
| [CLR-CASHFLOW-011](ba-admin/CASHFLOW/CLR-CASHFLOW-011.md) | OPEN | SPEC-CASHFLOW-001 v0.2 | 入金的 order_id 由廠商於 req-cashin 帶入，還是由平台產生（暫定比照出金由平台產生）？ |  |
| [CLR-CASHFLOW-012](ba-admin/CASHFLOW/CLR-CASHFLOW-012.md) | OPEN | SPEC-CASHFLOW-001 v0.2 | 管理員手動取消待確認出金的防護規則：(1) 收據已印出才取消時，管理員事前要核對什麼、收據怎麼處理、機台與平台分數怎麼對齊？(2) 對已完成出金、已取消出金、待確認入金等非「待確認出金」目標呼叫取消 API 時的回應？(3) 手動取消與機台遲到的 end-cashout 同時到達時以哪個為準、輸的一方回什麼？(4) 重複送出取消請求時阻擋提示還是冪等？(5) 管理員能否取消其他站台機台的待確認出金？ |  |
| [CLR-CASHFLOW-013](ba-admin/CASHFLOW/CLR-CASHFLOW-013.md) | OPEN | SPEC-CASHFLOW-001 v0.2 | 金額小數精度與進位規則：餘額為 399.65、399.655 等兩位以上小數時，核可金額、收據面額、交易紀錄、日結報表各保留幾位、四捨五入或截斷？整數面額是否顯示 .00？throshold 能否帶小數（例 0.5）？ |  |
| [CLR-CASHFLOW-014](ba-admin/CASHFLOW/CLR-CASHFLOW-014.md) | OPEN | SPEC-CASHFLOW-001 v0.2 | 入金與出金的異常收斂：(1) end-cashin 超限回 1-OVER LIMIT、退鈔後，該筆 PENDING 轉成什麼狀態？機台會不會重送？平台收到重送是否必須固定拒絕（不得在額度釋放後轉為成功）？(2) end-cashin 清點金額為 0、大於 req-cashin 聲稱金額、帶小數時以哪個入帳、是否拒絕？req-cashin 有無防禦性預檢、門檻多少？(3) 有未完成 PENDING 時重置機台憑證，新 token 能否完成舊 TXID？舊 token 回 9-OTHER ERROR 時機台是否持續重送？(4) req-cashout 與 end-cashout 之間完成一筆入金時，end-cashout 後餘額是 0 還是該筆入金、屬於哪個場次？ |  |
| [CLR-CASHFLOW-015](ba-admin/CASHFLOW/CLR-CASHFLOW-015.md) | OPEN | SPEC-CASHFLOW-001 v0.2 | 機台請求中的機台帳號與 token 所屬機台不一致時（M1 的 token 對 M2、或對其他場館的 M3 發請求），是否一律拒絕？回覆碼為何？ |  |
| [CLR-CASHFLOW-016](ba-admin/CASHFLOW/CLR-CASHFLOW-016.md) | OPEN | SPEC-CASHFLOW-001 v0.2 | 洗分請求同時帶 throshold=0 與 mode=value（指定金額，例如洗 100）時，以哪一條為準：第 360 行「throshold=0 表示洗出當前全部餘額」，還是第 364 行「mode=value 時以請求金額核可、餘額不清空」？ |  |

## ba-admin / CASHOUT

| ID | 狀態 | 規格 | 問題 | PM 回覆 |
|---|---|---|---|---|
| [CLR-CASHOUT-001](ba-admin/CASHOUT/CLR-CASHOUT-001.md) | APPLIED | SPEC-CASHOUT-001 v0.1 | TC-DRAFT-01M2R6NEJ7BJH8707E9B1MM8SH / ...VDDAW6 / ...YDRNZ（AC-CASHOUT-0251/0252/0291）的assumption標註『操作員角色的權限範圍(含是否限定單一場館)定義於開發包⑥PLATFORMRULE，該包尚未完成Phase 3測試設計』，此權限規則本身（操作員無權切換場館）是否為過去已規劃定案的既有設計，而非待PLATFORMRULE補完才會定義的規則？ | 操作員無權限切換至其他場館，切換場館的設定在後台管理員系統，此權限只有站長跟admin有權限，這是過去就規劃好的權限事宜 |
| [CLR-CASHOUT-002](ba-admin/CASHOUT/CLR-CASHOUT-002.md) | APPLIED | SPEC-CASHOUT-001 v0.1 | 機台洗分（單階段交易）實際上會不會出現「待處理／等待中」（＝spec 概念的待確認）狀態？若不會，TC-CASHOUT-044「尚未完成的洗分不會出現在核實頁」如何驗證？ | A：洗分一送出就完成，不會有中間狀態。機台洗分為單階段交易（req-keyout，帳務立即生效），不會停在「待處理／等待 |
| [CLR-CASHOUT-003](ba-admin/CASHOUT/CLR-CASHOUT-003.md) | OPEN | SPEC-CASHOUT-001 v0.2 | 已核實（已兌現）的出金收據還能不能作廢？若同一張待核實收據被櫃檯核實、同時被站長作廢，最終以哪個為準、輸的一方看到什麼？ |  |
| [CLR-CASHOUT-004](ba-admin/CASHOUT/CLR-CASHOUT-004.md) | OPEN | SPEC-CASHOUT-001 v0.2 | 洗分出金核實的金額範圍篩選是否接受小數輸入？邊界是否含等號（min＝max＝399.60 能否查到該筆）？ |  |
| [CLR-CASHOUT-005](ba-admin/CASHOUT/CLR-CASHOUT-005.md) | OPEN | SPEC-CASHOUT-001 v0.2 | (1)「出收據那天」以什麼切日：場館日結時間（營業日）還是 UTC+0 00:00？(2) 跨日核實（D 日出收據、D+n 日核實）的兌現金額（現金淨收的扣除項）記在 D 日列還是核實那天的列？(3) 收據永久有效，日結報表結算日期若有上限或資料保留期，最早的未兌現收據超出時怎麼呈現？ |  |
| [CLR-CASHOUT-006](ba-admin/CASHOUT/CLR-CASHOUT-006.md) | OPEN | SPEC-CASHOUT-001 v0.2 | 出金核實按下確認後請求逾時、網路中斷或後端部分失敗時：核實狀態、機台交易紀錄核實欄位、會員列表提款次數／金額三處是否同進同退？畫面如何提示？櫃檯如何判斷可否付現？ |  |
| [CLR-CASHOUT-007](ba-admin/CASHOUT/CLR-CASHOUT-007.md) | OPEN | SPEC-CASHOUT-001 v0.2 | 作廢送出鈕連點或作廢請求重送時，系統要阻擋提示還是冪等忽略？作廢原因與後台操作紀錄是否保留第一次的內容、不重複追加？ |  |
| [CLR-CASHOUT-008](ba-admin/CASHOUT/CLR-CASHOUT-008.md) | OPEN | SPEC-CASHOUT-001 v0.2 | 過渡期以前台結算結果畫面照片代替收據：畫面上的結算分數顯示到小數第幾位？照片金額（例 399.6、399 或 400）與核實彈窗面額（399.60）不一致時，櫃檯以哪個為準、照付、拒付或轉人工？ |  |

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
| [CLR-DAILYREPORT-011](ba-admin/DAILYREPORT/CLR-DAILYREPORT-011.md) | ANSWERED | SPEC-DAILYREPORT-001 v0.1 | 出金在洗分出金核實頁被「作廢」後，該筆收據金額在場館日結報表如何呈現？ | 依 SPEC-DAILYREPORT-001 v0.3（2026-10-05 定案，第 53、54 行）：出金在洗分出金 |
| [CLR-DAILYREPORT-012](ba-admin/DAILYREPORT/CLR-DAILYREPORT-012.md) | APPLIED | SPEC-DAILYREPORT-001 v0.1 | 場館日結報表「依場次明細」是否應列出進行中的場次（結束時間「—」、時長累計至查詢當下）？ | B：場館日結報表「依場次明細」只列已結束／逾時結束／日結結算的場次，進行中場次不列。現行實作（時長僅於結算時計算一次、明 |
| [CLR-DAILYREPORT-013](ba-admin/DAILYREPORT/CLR-DAILYREPORT-013.md) | APPLIED | SPEC-DAILYREPORT-001 v0.1 | 場館日結報表對「進行中場次」的處理：CLR-DAILYREPORT-012 的定案（2026-09-22，B）與 spec 2026-09-17 修訂相反，以哪一個為準？①「依場次明細」是否列出進行中場次？②「期末餘額」是否計入進行中場次累計到查詢當下的分數？ | A：以 spec 2026-09-17 為準。①依場次明細列出進行中場次：結束時間「—」，場次時長與期末餘額為累計到查詢 |
| [CLR-DAILYREPORT-014](ba-admin/DAILYREPORT/CLR-DAILYREPORT-014.md) | INCORPORATED | SPEC-DAILYREPORT-001 v0.2 | REQ-DAILYREPORT-001 不符合時系統應如何反應？（Spec 未定義拒絕行為） | 比照操作員：管理員或站長查詢、匯出管轄範圍外的場館（含直接呼叫 API 帶範圍外場館參數）時，前端不提供範圍外場館選項， |
| [CLR-DAILYREPORT-015](ba-admin/DAILYREPORT/CLR-DAILYREPORT-015.md) | INCORPORATED | SPEC-DAILYREPORT-001 v0.3 | 未兌現金額如何歸屬到各列：v0.3 第 53、70 行定為以出收據的日期歸屬（週期列為各營業日合計），CLR-DAILYREPORT-009（v0.1 時回答）定為不受統計週期切分、範圍內較早日期出的未兌現收據不落在該日／該週的列。以哪一邊為準？ | 以 v0.3 為準：未兌現金額以出收據的日期歸屬——每列只含當日（週期列為該週期內各營業日）出的收據中、截至查詢當下仍為 |
| [CLR-DAILYREPORT-016](ba-admin/DAILYREPORT/CLR-DAILYREPORT-016.md) | INCORPORATED | SPEC-DAILYREPORT-001 v0.3 | 查詢期間沒有任何交易與場次、但機台留有分數時，期初／期末餘額顯示什麼：v0.3 第 64、68 行定為沿用最近一個營業日的結算值（從未有分數者為 0），CLR-DAILYREPORT-006（當時尚無期初餘額欄）定為各欄位顯示 0。以哪一邊為準？ | 以 v0.3 為準：查詢期間沒有任何交易與場次時，列表仍列出該結算期間，各金額與筆數欄顯示 0；期初／期末餘額依時點值規 |
| [CLR-DAILYREPORT-017](ba-admin/DAILYREPORT/CLR-DAILYREPORT-017.md) | OPEN | SPEC-DAILYREPORT-001 v0.3 | 「逾時結束」的場次結束後機台仍留有分數時：日結時是否承接成隔日新場次的期初餘額、是否計入期末餘額？（v0.3 第 128 行只列「承接洗分餘數或日結結算轉入者」，第 151 行只涵蓋進行中的場次；可能定義於開發包③ 機台金流與場次 v02，本包未宣告引用） |  |
| [CLR-DAILYREPORT-018](ba-admin/DAILYREPORT/CLR-DAILYREPORT-018.md) | OPEN | SPEC-DAILYREPORT-001 v0.3 | 場館修改日結時間後：(1) 只影響之後的營業日，還是回溯重切過去？(2) 切換當天營業日的長度（例 00:00 改 06:00，是 30 小時還是 18 小時）？(3) 已以收據日歸屬的未兌現／已作廢／已兌現與日結結算場次的歸屬營業日會不會跳列？(4) 結算日期區間沒有上限、匯出不分頁，長區間（數年、依場次明細）的查詢與匯出有無效能目標、逾時或筆數上限？ |  |
| [CLR-DAILYREPORT-019](ba-admin/DAILYREPORT/CLR-DAILYREPORT-019.md) | OPEN | SPEC-DAILYREPORT-001 v0.3 | 長區間條件下連點匯出 CSV 或重複送出查詢時，系統是否防連點、有無同時匯出的併發上限？ |  |
| [CLR-DAILYREPORT-020](ba-admin/DAILYREPORT/CLR-DAILYREPORT-020.md) | OPEN | SPEC-DAILYREPORT-001 v0.3 | (1) 操作員能否查看場館日結報表？可看哪些場館？(2) 使用者登入後管轄範圍被調整（站長移出某子站台、操作員改調場館），既有工作階段是否立即套用新範圍、已開啟的報表頁再查詢或匯出會不會取得舊範圍資料？ |  |
| [CLR-DAILYREPORT-021](ba-admin/DAILYREPORT/CLR-DAILYREPORT-021.md) | OPEN | SPEC-DAILYREPORT-001 v0.3 | 櫃檯對機台帳號的人工入金（補分）、人工出金（結清待確認出金），以及被取消（新請求取代、人工出金連動、管理員手動取消）的待確認出金，在日結報表各欄與餘額驗算式中如何計入？ |  |
| [CLR-DAILYREPORT-022](ba-admin/DAILYREPORT/CLR-DAILYREPORT-022.md) | OPEN | SPEC-DAILYREPORT-001 v0.3 | 機台停用、報廢（只停用不刪除）或改歸屬其他場館時，它的留存分數是否繼續計入原場館的期初／期末餘額？歷史列會不會跟著搬？ |  |
| [CLR-DAILYREPORT-023](ba-admin/DAILYREPORT/CLR-DAILYREPORT-023.md) | OPEN | SPEC-DAILYREPORT-001 v0.3 | 注單數是否計入取消或退款的注單？歸屬營業日依下注時間還是結算時間？ |  |

## ba-admin / PLATFORMRULE

| ID | 狀態 | 規格 | 問題 | PM 回覆 |
|---|---|---|---|---|
| [CLR-PLATFORMRULE-001](ba-admin/PLATFORMRULE/CLR-PLATFORMRULE-001.md) | APPLIED | SPEC-PLATFORMRULE-001 v0.1 | 「站長＝最高權限」的定義是否仍有效？三份 spec 的權限層級互相矛盾 | 以功能 spec 三層模型為準：管理員（最高）＞站長＞操作員。原則：可見範圍由所屬站台決定、權限層級由角色決定，兩者分開 |
| [CLR-PLATFORMRULE-002](ba-admin/PLATFORMRULE/CLR-PLATFORMRULE-002.md) | APPLIED | SPEC-PLATFORMRULE-001 v0.1 | REQ-PLATFORMRULE-011 不符合時系統應如何反應？（Spec 未定義拒絕行為） | 此為架構層要求（選單顯示規則需與排除規則同一來源，不得各自寫死），非使用者可觀察行為，且目前無任何排除項目被實際解除、無 |
| [CLR-PLATFORMRULE-003](ba-admin/PLATFORMRULE/CLR-PLATFORMRULE-003.md) | APPLIED | SPEC-PLATFORMRULE-001 v0.1 | 操作員角色是否可見「注單查詢」與「稽核明細」頁面？權限表未列此兩項，請補列定案 | 新需求：操作員有權限進入「注單查詢」與「稽核明細」（可見範圍比照其他報表頁限自身場館）。→ 權限表須補兩列（操作員：自身 |
| [CLR-PLATFORMRULE-004](ba-admin/PLATFORMRULE/CLR-PLATFORMRULE-004.md) | WITHDRAWN | SPEC-PLATFORMRULE-001 v0.2 | REQ-PLATFORMRULE-011 不符合時系統應如何反應？（Spec 未定義拒絕行為） |  |

## ba-admin / REDPACKET

| ID | 狀態 | 規格 | 問題 | PM 回覆 |
|---|---|---|---|---|
| [CLR-REDPACKET-001](ba-admin/REDPACKET/CLR-REDPACKET-001.md) | WITHDRAWN | SPEC-REDPACKET-001 v0.1 | 除權重表機率合計外，其餘驗證（門檻、上限、總預算、活動幣種、等級規則、活動名稱字數）不符時系統如何回應：前端阻擋方式與提示文字、後端是否同樣拒絕及回應 |  |
| [CLR-REDPACKET-002](ba-admin/REDPACKET/CLR-REDPACKET-002.md) | APPLIED | SPEC-REDPACKET-001 v0.1 | 稽核倍數的允許範圍（可否為 0、可否為小數、上限）、中獎機率與紅包金額／門檻／總預算允許的小數位數 |  |
| [CLR-REDPACKET-003](ba-admin/REDPACKET/CLR-REDPACKET-003.md) | WITHDRAWN | SPEC-REDPACKET-001 v0.1 | 換算為核心貨幣後金額的小數位數與捨入方式（影響是否剛好達門檻） |  |
| [CLR-REDPACKET-004](ba-admin/REDPACKET/CLR-REDPACKET-004.md) | WITHDRAWN | SPEC-REDPACKET-001 v0.1 | 已計入累計的注單事後被取消、派彩取消、廢除取消結算或重新結算時，累計是否扣回；若已因此產生紅包（待開啟或已入帳），是否作廢或追回 |  |
| [CLR-REDPACKET-005](ba-admin/REDPACKET/CLR-REDPACKET-005.md) | WITHDRAWN | SPEC-REDPACKET-001 v0.1 | 單筆注單使累計跨越多個門檻而超過上限時，超出上限部分的累計是否保留、紅包明細「週期累計」顯示值為何 |  |
| [CLR-REDPACKET-006](ba-admin/REDPACKET/CLR-REDPACKET-006.md) | WITHDRAWN | SPEC-REDPACKET-001 v0.1 | 活動進行中修改場館「日結時間」時，當前週期的結束點與後續週期如何切分（是否產生過長／過短週期、待開啟紅包何時作廢） |  |
| [CLR-REDPACKET-007](ba-admin/REDPACKET/CLR-REDPACKET-007.md) | WITHDRAWN | SPEC-REDPACKET-001 v0.1 | 機台帳號的紅包入帳在 4.1 機台視角（交易類型篩選、場次編號、核實狀態、來源等欄位）如何呈現；4.4 稽核明細機台帳號的紅包列欄位與單位（現列為 USDT） |  |
| [CLR-REDPACKET-008](ba-admin/REDPACKET/CLR-REDPACKET-008.md) | WITHDRAWN | SPEC-REDPACKET-001 v0.1 | 輸入的新總預算小於或等於目前總預算時，系統如何回應（確認鈕停用或送出後提示、提示文字、後端是否拒絕） |  |
| [CLR-REDPACKET-009](ba-admin/REDPACKET/CLR-REDPACKET-009.md) | WITHDRAWN | SPEC-REDPACKET-001 v0.1 | 活動狀態（排程中、進行中、已結束、已取消）的定義、判定時點與在列表上的顯示位置（6.5.1 既有排程列表沒有狀態欄）；已結束或已取消的活動是否仍列於排程列表 |  |
| [CLR-REDPACKET-010](ba-admin/REDPACKET/CLR-REDPACKET-010.md) | WITHDRAWN | SPEC-REDPACKET-001 v0.1 | 追加預算的操作紀錄於何處檢視（後台操作紀錄頁或紅包明細），以及可檢視的角色 |  |
| [CLR-REDPACKET-011](ba-admin/REDPACKET/CLR-REDPACKET-011.md) | WITHDRAWN | SPEC-REDPACKET-001 v0.1 | 「同一站台」的範圍：主站台與其子站台的紅包活動是否各自獨立判斷重疊；某站台的活動是否涵蓋子站台的會員 |  |
| [CLR-REDPACKET-012](ba-admin/REDPACKET/CLR-REDPACKET-012.md) | APPLIED | SPEC-REDPACKET-001 v0.1 | 試算數值的顯示格式：期望金額與最高成本的小數位數、成本占比以百分比或比值顯示及其位數 |  |
| [CLR-REDPACKET-013](ba-admin/REDPACKET/CLR-REDPACKET-013.md) | APPLIED | SPEC-REDPACKET-001 v0.1 | 差異百分比的計算基準（(實際－期望)÷期望）與小數位數；實際等於期望時的顯示與色標 |  |
| [CLR-REDPACKET-014](ba-admin/REDPACKET/CLR-REDPACKET-014.md) | APPLIED | SPEC-REDPACKET-001 v0.1 | CSV 的欄位清單與順序、是否含總計列、狀態與作廢原因的輸出文字、時間格式 |  |
| [CLR-REDPACKET-015](ba-admin/REDPACKET/CLR-REDPACKET-015.md) | WITHDRAWN | SPEC-REDPACKET-001 v0.1 | 線上站台紅包明細、匯出 CSV、取消排程的可操作角色與可見範圍（管轄範圍是否含子站台）；SPEC-SYSADMIN-001@0.1 6.5 未載明權限 |  |
| [CLR-REDPACKET-016](ba-admin/REDPACKET/CLR-REDPACKET-016.md) | WITHDRAWN | SPEC-REDPACKET-001 v0.1 | 無權限角色直接呼叫新增、追加預算、取消排程或紅包明細 API 時，後端的回應（狀態碼與訊息） |  |
| [CLR-REDPACKET-017](ba-admin/REDPACKET/CLR-REDPACKET-017.md) | APPLIED | SPEC-REDPACKET-001 v0.1 | 操作員能否進入優惠活動管理與活動排程列表、能否匯出紅包明細 CSV（「唯讀」是否含匯出） |  |
| [CLR-REDPACKET-018](ba-admin/REDPACKET/CLR-REDPACKET-018.md) | WITHDRAWN | SPEC-REDPACKET-001 v0.1 | 操作員越權操作（含直接呼叫 API）時的系統回應：按鈕隱藏或停用、後端回應與訊息 |  |
| [CLR-REDPACKET-019](ba-admin/REDPACKET/CLR-REDPACKET-019.md) | WITHDRAWN | SPEC-REDPACKET-001 v0.1 | 紅包入帳（分數增加）與場次的關係：最後一局輸光使場次歸零結束後才開啟紅包，分數由 0 轉正時是否建立新場次；紅包入帳歸屬哪個場次（紅包明細的場次編號是產生當下的場次，可能與入帳時不同）；場館日結報表「依場次明細」維度的期初／期末餘額是否含紅包 |  |
| [CLR-REDPACKET-020](ba-admin/REDPACKET/CLR-REDPACKET-020.md) | WITHDRAWN | SPEC-REDPACKET-001 v0.1 | 「機台場館啟用紅包」的方式與時點：是全平台一次上線、依場館開關啟用，或另有設定；啟用前機台場館的選單與機台帳號是否仍完全排除（目前正本與開發包⑥皆為排除） |  |
| [CLR-REDPACKET-021](ba-admin/REDPACKET/CLR-REDPACKET-021.md) | APPLIED | SPEC-REDPACKET-001 v0.1 | 「尚有紅包未開啟」提示是否為可取消的確認視窗（玩家可先返回開啟紅包）或僅告知後繼續交易；店員以鑰匙選單洗分時提示顯示於何處 |  |
| [CLR-REDPACKET-022](ba-admin/REDPACKET/CLR-REDPACKET-022.md) | WITHDRAWN | SPEC-REDPACKET-001 v0.1 | 櫃檯對機台帳號人工出金（或人工入金）是否視同出金而作廢待開啟紅包；出金停在「待確認」（不設逾時）期間紅包是否一直不可開啟，Admin 手動取消或被新出金取代時是否恢復；過渡期由前台完成的出金是否同樣適用 |  |
| [CLR-REDPACKET-023](ba-admin/REDPACKET/CLR-REDPACKET-023.md) | WITHDRAWN | SPEC-REDPACKET-001 v0.1 | 機台紅包稽核倍數大於 0 時，紅包產生的稽核如何影響機台洗分／出金的核可金額：正本的扣除規則以出金設定 TWD 倍數大於 0 為條件、計入交易僅開分與入金，出金設定為 0 倍而紅包倍數大於 0 時是否仍扣除 |  |
| [CLR-REDPACKET-024](ba-admin/REDPACKET/CLR-REDPACKET-024.md) | APPLIED | SPEC-REDPACKET-001 v0.1 | 「週期即將重置」提示的起始時點（重置前多久）；「目前累計」顯示的是本週期累計總額還是距下一個紅包的累計（範例中週期累計 1,084 與超出 84 並存） |  |
| [CLR-REDPACKET-025](ba-admin/REDPACKET/CLR-REDPACKET-025.md) | WITHDRAWN | SPEC-REDPACKET-001 v0.1 | 紅包金額欄的位置、是否進總計列與 CSV、在「依場次明細」維度的值（場次歸屬見 REQ-REDPACKET-025 Q02），以及營業日依入帳時間歸屬的確認 |  |
| [CLR-REDPACKET-026](ba-admin/REDPACKET/CLR-REDPACKET-026.md) | ANSWERED | SPEC-REDPACKET-001 v0.1 | 後端是否同樣拒絕不合法的紅包活動設定（門檻、上限、總預算、活動幣種、等級規則、權重表、活動名稱、活動時間），以及直接呼叫 API 時的回應（狀態碼與訊息）；前端阻擋方式與提示文字已由 SPEC-REDPACKET-002@0.1 saveAdd() 定義（見 Q05） | PM 2026-10-10 回覆（原題 001，已寫入紅包 spec v02）：前端在該欄位標紅框、下方顯示提示；按「儲 |
| [CLR-REDPACKET-027](ba-admin/REDPACKET/CLR-REDPACKET-027.md) | ANSWERED | SPEC-REDPACKET-001 v0.1 | 稽核倍數可否為負數、可否為小數及其上限；中獎機率、紅包金額、累積門檻與總預算允許的小數位數（可否為 0 已由 Q06 定義） | PM 2026-10-10 回覆（原題 002，已寫入紅包 spec v02）：累積門檻、紅包金額、中獎機率、總預算、稽 |
| [CLR-REDPACKET-028](ba-admin/REDPACKET/CLR-REDPACKET-028.md) | ANSWERED | SPEC-REDPACKET-001 v0.1 | 換算為核心貨幣後金額的小數位數與捨入方式（影響是否剛好達門檻） | PM 2026-10-10 回覆（原題 003，已寫入紅包 spec v02）：換算後四捨五入至小數 2 位再計入累計； |
| [CLR-REDPACKET-029](ba-admin/REDPACKET/CLR-REDPACKET-029.md) | ANSWERED | SPEC-REDPACKET-001 v0.1 | 已計入累計的注單事後被取消、派彩取消、廢除取消結算或重新結算時，累計是否扣回；若已因此產生紅包（待開啟或已入帳），是否作廢或追回 | PM 2026-10-10 回覆（原題 004，已寫入紅包 spec v02）：負值有效流水貢獻照實扣減，累計可暫時為負 |
| [CLR-REDPACKET-030](ba-admin/REDPACKET/CLR-REDPACKET-030.md) | ANSWERED | SPEC-REDPACKET-001 v0.1 | 單筆注單使累計一次跨越多個門檻並在途中達到單週期上限時：(1) 觸發上限那筆注單在最後一個紅包之後的剩餘流水是否仍計入本週期累計（第 319 行「停止累計」的生效時點；影響之後因升級改用上限較高的規則時的進度）；(2) 同一筆注單產生的多個紅包，紅包明細「週期累計」各顯示什麼值（第 239、280 行只示範單一紅包的情形） | PM 2026-10-10 回覆（原題 005，已寫入紅包 spec v02）：循環產生到上限為止；產生達上限的那一個紅 |
| [CLR-REDPACKET-031](ba-admin/REDPACKET/CLR-REDPACKET-031.md) | ANSWERED | SPEC-REDPACKET-001 v0.1 | 活動進行中修改場館「日結時間」時，當前週期的結束點與後續週期如何切分（是否產生過長／過短週期、待開啟紅包何時作廢） | PM 2026-10-10 回覆（原題 006，已寫入紅包 spec v02）：立即生效，週期只往前、不倒退。調早：本週 |
| [CLR-REDPACKET-032](ba-admin/REDPACKET/CLR-REDPACKET-032.md) | ANSWERED | SPEC-REDPACKET-001 v0.1 | 場館「日結時間」修改後何時生效（即時、下一個營業日或其他）；SPEC-SITELIST-001@0.6 只寫明額度上限與場次逾時時間「修改後即時生效」，日結時間的生效時點在目標與各參考皆未定義。此為 Q02（週期如何切分）的前提 | PM 2026-10-10 回覆（原題 006，已寫入紅包 spec v02）：立即生效，週期只往前、不倒退。調早：本週 |
| [CLR-REDPACKET-033](ba-admin/REDPACKET/CLR-REDPACKET-033.md) | ANSWERED | SPEC-REDPACKET-001 v0.1 | 範圍只限機台帳號的呈現細節（Q02 已定義 4.1 交易類型與 4.4 稽核明細類型新增「紅包」、線上與機台皆有）：(1) 4.1 機台視角擴充（SPEC-ARCADE-001@0.7 機台交易紀錄）的交易類型下拉是否加入「紅包」，以及紅包列的場次編號、交易狀態、核實狀態、請求／實際金額、完成時間、來源等欄位值；(2) 4.4 稽核明細中機台帳號紅包列的金額單位（現行欄位標示 USDT，機台為 TWD） | PM 2026-10-10 回覆（原題 007，已寫入紅包 spec v02）：4.1 機台視角交易類型下拉新增「紅包」 |
| [CLR-REDPACKET-034](ba-admin/REDPACKET/CLR-REDPACKET-034.md) | ANSWERED | SPEC-REDPACKET-001 v0.1 | 新總預算小於或等於目前總預算時，後端是否同樣拒絕及其回應（狀態碼與訊息）；前端行為已由 SPEC-REDPACKET-002@0.1 confirmBudget() 定義（見 Q05） | PM 2026-10-10 回覆（原題 008，已寫入紅包 spec v02）：「確認」鈕停用，欄位下方提示「新的總預算 |
| [CLR-REDPACKET-035](ba-admin/REDPACKET/CLR-REDPACKET-035.md) | ANSWERED | SPEC-REDPACKET-001 v0.1 | 追加預算的操作紀錄於何處檢視（後台操作紀錄頁或紅包明細），以及可檢視的角色 | PM 2026-10-10 回覆（原題 010，已寫入紅包 spec v02）：寫入7.4 操作紀錄（操作人員、時間、活 |
| [CLR-REDPACKET-036](ba-admin/REDPACKET/CLR-REDPACKET-036.md) | ANSWERED | SPEC-REDPACKET-001 v0.1 | 「同一站台」的範圍：主站台與其子站台的紅包活動是否各自獨立判斷重疊；某站台的活動是否涵蓋子站台的會員 | PM 2026-10-10 回覆（原題 011，已寫入紅包 spec v02）：各站台獨立：主站台與子站台各自判斷時段重 |
| [CLR-REDPACKET-037](ba-admin/REDPACKET/CLR-REDPACKET-037.md) | ANSWERED | SPEC-REDPACKET-001 v0.1 | CSV 的欄位清單與順序、是否含總計列、狀態與作廢原因的輸出文字、時間格式（SPEC-REDPACKET-002@0.1 的匯出只是示意 toast，未定義檔案內容） | PM 2026-10-10 回覆（原題 014，已寫入紅包 spec v02）：欄位與順序同列表（紅包編號 → 作廢原因 |
| [CLR-REDPACKET-038](ba-admin/REDPACKET/CLR-REDPACKET-038.md) | WITHDRAWN | SPEC-REDPACKET-001 v0.1 | 預設規則關閉且只有一組等級規則的活動，紅包明細是否顯示「規則」篩選 |  |
| [CLR-REDPACKET-039](ba-admin/REDPACKET/CLR-REDPACKET-039.md) | ANSWERED | SPEC-REDPACKET-001 v0.1 | 線上站台紅包明細、匯出 CSV、取消排程的可操作角色與可見範圍（管轄範圍是否含子站台）；SPEC-SYSADMIN-001@0.1 6.5 未載明權限 | PM 2026-10-10 回覆（原題 015，已寫入紅包 spec v02）：三項都與新增活動同權限（財務、站長、管理 |
| [CLR-REDPACKET-040](ba-admin/REDPACKET/CLR-REDPACKET-040.md) | ANSWERED | SPEC-REDPACKET-001 v0.1 | 無權限角色直接呼叫新增、追加預算、取消排程或紅包明細 API 時，後端的回應（狀態碼與訊息） | PM 2026-10-10 回覆（原題 016，已寫入紅包 spec v02）：後端拒絕並回傳「無權限」、資料不變。錯誤 |
| [CLR-REDPACKET-041](ba-admin/REDPACKET/CLR-REDPACKET-041.md) | ANSWERED | SPEC-REDPACKET-001 v0.1 | 操作員在機台場館紅包明細的「唯讀」是否包含「匯出 CSV」（目標第 257 行只寫自身場館唯讀；進入路徑已由 Q04 定義） | PM 2026-10-10 回覆（原題 017，已寫入紅包 spec v02）：操作員可進入優惠活動管理、活動排程列表與 |
| [CLR-REDPACKET-042](ba-admin/REDPACKET/CLR-REDPACKET-042.md) | APPLIED | SPEC-REDPACKET-001 v0.1 | 操作員越權操作（含直接呼叫 API）時的系統回應：按鈕隱藏或停用、後端回應與訊息 |  |
| [CLR-REDPACKET-043](ba-admin/REDPACKET/CLR-REDPACKET-043.md) | ANSWERED | SPEC-REDPACKET-001 v0.1 | 紅包入帳（分數增加）與場次的關係：(1) 場次因輸光歸零結束後才開啟紅包，分數由 0 轉正時是否建立新場次（SPEC-ARCADE-001@0.7 只列開分、入金會建立場次）；(2) 紅包入帳歸屬哪個場次（紅包明細的場次編號是產生當下的場次，第 237 行，入帳時可能已不同）；(3) 場館日結報表「依場次明細」維度的期初／期末餘額與紅包金額如何計入 | PM 2026-10-10 回覆（原題 019，已寫入紅包 spec v02）：入帳歸屬入帳當下進行中的場次；沒有場次時 |
| [CLR-REDPACKET-044](ba-admin/REDPACKET/CLR-REDPACKET-044.md) | ANSWERED | SPEC-REDPACKET-001 v0.1 | 「機台場館啟用紅包」的方式、粒度與時點：全平台一次解除，或依場館個別啟用（有無開關、由誰設定）；啟用前的行為見 Q03 | PM 2026-10-10 回覆（原題 020，已寫入紅包 spec v02）：隨版本對所有機台場館一次上線，不設場館開 |
| [CLR-REDPACKET-045](ba-admin/REDPACKET/CLR-REDPACKET-045.md) | ANSWERED | SPEC-REDPACKET-001 v0.1 | 「尚有紅包未開啟，交易完成後將作廢」提示出現後，玩家或店員可否先返回、不送出交易（以便先開啟紅包），還是提示後交易直接繼續 | PM 2026-10-10 回覆（原題 021，已寫入紅包 spec v02）：可取消的確認視窗：［返回開啟紅包］關閉視 |
| [CLR-REDPACKET-046](ba-admin/REDPACKET/CLR-REDPACKET-046.md) | ANSWERED | SPEC-REDPACKET-001 v0.1 | 櫃檯對機台帳號執行人工出金（扣分）時，是否視同「出金」而作廢待開啟紅包、作廢原因為何；人工入金（補分）是否影響待開啟紅包。待確認期間的鎖定、取消與被取代後恢復、過渡期前台出金已由 Q03 定義 | PM 2026-10-10 回覆（原題 022，已寫入紅包 spec v02）：櫃檯人工出金視同出金完成，作廢待開啟紅包 |
| [CLR-REDPACKET-047](ba-admin/REDPACKET/CLR-REDPACKET-047.md) | WITHDRAWN | SPEC-REDPACKET-001 v0.1 | 待確認出金能否由 Admin 手動取消（並因此使紅包恢復可開啟），以 spec 原文或 CLR-CASHFLOW-004 為準 |  |
| [CLR-REDPACKET-048](ba-admin/REDPACKET/CLR-REDPACKET-048.md) | ANSWERED | SPEC-REDPACKET-001 v0.1 | 機台紅包稽核倍數大於 0 時，紅包產生的未完成稽核是否扣減洗分／出金的核可金額。SPEC-CASHFLOW-001@0.1 的扣除規則以「出金設定的 TWD 稽核倍數大於 0」為觸發條件（第 245、363 行），計入交易只有開分與入金（第 57 行），未提到紅包：(1) 出金設定為 0 倍、紅包倍數大於 0 時是否仍扣除；(2) 出金一律以全部餘額核可、清空餘額（第 332 行），扣除稽核後的出金如何處理（核可金額減少後餘額是否仍清空、剩餘分數去向） | (1) 已定案——PM 2026-10-10 回覆（原題 023，已寫入紅包 spec v02）：扣減。扣除條件改為「帳 |
| [CLR-REDPACKET-049](ba-admin/REDPACKET/CLR-REDPACKET-049.md) | ANSWERED | SPEC-REDPACKET-001 v0.1 | 「週期即將重置」提示從重置前多久開始顯示（SPEC-REDPACKET-002@0.1 不含前台）；「目前累計」的定義見 Q03 | PM 2026-10-10 回覆（原題 024，已寫入紅包 spec v02）：有待開啟紅包時進度顯示滿格「已達有效流水 |
| [CLR-REDPACKET-050](ba-admin/REDPACKET/CLR-REDPACKET-050.md) | ANSWERED | SPEC-REDPACKET-001 v0.1 | 紅包金額欄在列表中的位置；「依場次明細」維度的紅包金額與期初／期末餘額如何計入（依 REQ-REDPACKET-025 Q02 的場次歸屬）。營業日依入帳歸屬（第 350 行「當日已入帳」）見 Q01，總計列與 CSV 見 Q03 | PM 2026-10-10 回覆（原題 025，已寫入紅包 spec v02）：位於「有效投注額」之後、「損益」之前；列 |
| [CLR-REDPACKET-051](ba-admin/REDPACKET/CLR-REDPACKET-051.md) | OPEN | SPEC-REDPACKET-001 v0.2 | 4.1 機台視角紅包列的「其餘機台專屬欄位」指哪些欄位：SPEC-TXLOG-001@0.1 列表另有訂單編號、機台帳號（來源機台）、幣別、請求金額、實際金額、核實人員／時間、未成立原因、交易時間、完成時間、重送次數、來源；其中請求金額、實際金額、完成時間是否顯示紅包金額與入帳時間，或一律顯示「—」，目標未逐欄定義 |  |
| [CLR-REDPACKET-052](ba-admin/REDPACKET/CLR-REDPACKET-052.md) | ANSWERED | SPEC-REDPACKET-001 v0.2 | 紅包明細「實際平均紅包金額」差異百分比：差異恰為 0 時顯示「0.0%」或「+0.0%」；差異絕對值小於 0.005% 時以紅／綠（依高低）或灰色標示 | 依 proto（SPEC-REDPACKET-002@0.2）：PM 2026-10-10 回覆原題 013 明定差異百 |
| [CLR-REDPACKET-053](ba-admin/REDPACKET/CLR-REDPACKET-053.md) | ANSWERED | SPEC-REDPACKET-001 v0.2 | 預設規則關閉且只有一組等級規則的活動，紅包明細是否顯示「規則」篩選 | 依紅包 spec v02（目標）第 272 行：規則篩選「僅有等級規則的活動顯示」——預設規則關閉、只有一組等級規則的活 |
| [CLR-REDPACKET-054](ba-admin/REDPACKET/CLR-REDPACKET-054.md) | ANSWERED | SPEC-REDPACKET-001 v0.2 | 線上站台的站長能否檢視、操作（新增、追加預算、取消排程、紅包明細、匯出 CSV）其子站台的紅包活動：依目標限自身站台，或依 SPEC-ROLEPERM-001@0.2 含整棵子樹 | 依紅包 spec v02（目標）：PM 2026-10-10 回覆原題 015 明定——三項都與新增活動同權限（財務、站 |
| [CLR-REDPACKET-055](ba-admin/REDPACKET/CLR-REDPACKET-055.md) | ANSWERED | SPEC-REDPACKET-001 v0.2 | 待確認出金能否由管理員手動取消（並因此使紅包恢復可開啟），以 spec 原文（目標、SPEC-CASHFLOW-001@0.2、SPEC-ARCADE-001@0.8）或 CLR-CASHFLOW-004 為準；若存在，操作入口為何 | 依紅包 spec v02 與 PM 最新回覆（2026-10-10，原題 022）：櫃檯人工出金視同出金完成，作廢待開啟 |
| [CLR-REDPACKET-056](ba-admin/REDPACKET/CLR-REDPACKET-056.md) | OPEN | SPEC-REDPACKET-001 v0.2 | 機台扣除「未完成稽核的部分」的計算與出金後的處理：(1) 扣除的是什麼金額——剩餘未達的所需有效投注額、尚未完成稽核的紅包金額，或其他（例：30 TWD 紅包、稽核 1 倍、已打 10，扣 20 或 30）；(2) 出金依 SPEC-CASHFLOW-001@0.2 一律清空餘額，扣除後核可金額小於餘額時，被扣除的分數留在機台（不清空、不結束場次？）或作廢；洗分扣除後的餘數是否照洗分留餘數規則開新場次承接。目標與 SPEC-CASHFLOW-001@0.2、SPEC-ARCADE-001@0.8 皆未定義（原機台預設 0 倍不會觸發，紅包稽核使其可達） |  |
| [CLR-REDPACKET-057](ba-admin/REDPACKET/CLR-REDPACKET-057.md) | ANSWERED | SPEC-REDPACKET-001 v0.2 | 表單驗證提示文字以目標第 415 行或 SPEC-REDPACKET-002@0.2 為準（等級規則缺漏、適用等級未勾、權重表三處）；「此等級已屬於其他規則」「活動名稱最多 25 字元」在前端何時顯示（或僅為後端回應） | 依紅包 spec v02（目標）第 415 行的提示文字：PM 2026-10-10 回覆原題 001 明定「全部提示文 |
| [CLR-REDPACKET-058](ba-admin/REDPACKET/CLR-REDPACKET-058.md) | OPEN | SPEC-REDPACKET-001 v0.2 | 機台場館的紅包金額是否應限制為整數？若允許 1 位小數（例 10.5），機台入帳後的分數、4.1／4.4 金額、日結報表紅包金額是否都照記含小數？ |  |
| [CLR-REDPACKET-059](ba-admin/REDPACKET/CLR-REDPACKET-059.md) | OPEN | SPEC-REDPACKET-001 v0.2 | 紅包領取送出後中途失敗（前端逾時、連線中斷、後端寫入錢包／交易紀錄／稽核明細其中一步失敗）時：是否保證全部寫入或全部不寫？能否安全重試？前台顯示什麼？ |  |
| [CLR-REDPACKET-060](ba-admin/REDPACKET/CLR-REDPACKET-060.md) | OPEN | SPEC-REDPACKET-001 v0.2 | 重送與重放：(1) 對已入帳的紅包事後再送一次相同的領取請求（或機台重送），回應為何？是否以紅包編號冪等、絕不重複入帳？(2) 同一筆注單的結算通知被重送（相同注單編號再送一次正值）時，紅包累計是否以注單編號去重？ |  |
| [CLR-REDPACKET-061](ba-admin/REDPACKET/CLR-REDPACKET-061.md) | OPEN | SPEC-REDPACKET-001 v0.2 | 領取 API 是否檢查紅包屬於呼叫者？玩家 A 帶玩家 B 的紅包編號、或機台 M2 帶 M1 的紅包編號呼叫領取時，回應為何（拒絕與錯誤碼）？ |  |
| [CLR-REDPACKET-062](ba-admin/REDPACKET/CLR-REDPACKET-062.md) | OPEN | SPEC-REDPACKET-001 v0.2 | 線上站台的財務在紅包功能的管轄範圍是否含子站台（檢視、追加預算、取消排程、匯出明細）？ |  |
| [CLR-REDPACKET-063](ba-admin/REDPACKET/CLR-REDPACKET-063.md) | OPEN | SPEC-REDPACKET-001 v0.2 | 「洗分／出金後才達標」的紅包直接以已作廢建立；若此時活動預算已用罄（剩餘預算小於抽出金額），要不要建立這個已作廢紅包？是否計入本期已獲得與單週期上限？ |  |

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
| [CLR-SITELIST-013](ba-admin/SITELIST/CLR-SITELIST-013.md) | ANSWERED | SPEC-SITELIST-001 v0.6 | REQ-SITELIST-035 不符合時系統應如何反應？（Spec 未定義拒絕行為） | 選 A：前端限制，後端也拒絕，資料不變；所有權限限制都在後端每一支 API 強制執行（開發包⑧既有規則，站台列表已補註） |
| [CLR-SITELIST-014](ba-admin/SITELIST/CLR-SITELIST-014.md) | ANSWERED | SPEC-SITELIST-001 v0.6 | REQ-SITELIST-036 不符合時系統應如何反應？（Spec 未定義拒絕行為） | 站長不可指派站長，也不可指派管理員：角色下拉選單依操作者自身角色過濾，站長的畫面不會出現「管理員」與「站長」選項；直接呼 |
| [CLR-SITELIST-015](ba-admin/SITELIST/CLR-SITELIST-015.md) | ANSWERED | SPEC-SITELIST-001 v0.6 | REQ-SITELIST-037 不符合時系統應如何反應？（Spec 未定義拒絕行為） | 選 A：後端拒絕並回傳「無權限」錯誤，資料不變；不採用「當作不存在／回空結果」。spec 只規定「無權限」這個語意，錯誤 |
| [CLR-SITELIST-016](ba-admin/SITELIST/CLR-SITELIST-016.md) | ANSWERED | SPEC-SITELIST-001 v0.6 | v0.6 原文與已落地的 CLR 定案直接牴觸，本 RM 不自行裁定。v0.6（版本日期 2026-09-04）§角色與權限「子站台：刪除｜可操作｜可操作」、§列表欄位「操作｜編輯、刪除」、§操作/刪除站台（確認彈窗、二次確認、不可復原）、§業務規則/刪除確認，皆定義管理員與站長可刪除管轄範圍內的子站台（僅自身站台與根站台不可刪除）；CLR-SITELIST-008／009（2026-09-14，PM 與後端共同確認，晚於 v0.6 版本日期）定案「任何類型的站台皆不提供刪除操作，前後端皆拒絕，只能暫停／關閉」，原因是刪除會影響站台樹狀結構。v0.6 取自 ba-spec main 2026-09-29 快照仍保留刪除敘述，QA 增補草稿要求移除該節亦未合入正本，無法判斷是 spec 未同步 CLR，還是產品方向已改回可刪除。 | 選 A：任何站台都不能刪除，線上、機台、根站台皆同。畫面沒有刪除按鈕，以 API 直接呼叫後端也拒絕；要停止服務一律切「 |
| [CLR-SITELIST-017](ba-admin/SITELIST/CLR-SITELIST-017.md) | ANSWERED | SPEC-SITELIST-001 v0.6 | 與 REQ-SITELIST-022 同一衝突（v0.6 原文可刪除子站台 vs CLR-SITELIST-008／009 任何站台皆不可刪除），應一併裁定；若採 v0.6 原文，刪除仍有子站台的站台時子樹如何處理 v0.6 亦未定義。 | 選 A：任何站台都不能刪除，因此「刪除仍有子站台的站台時子樹如何處理」的情境不會發生，B1～B3 的追問不適用，本條僅供 |
| [CLR-SITELIST-018](ba-admin/SITELIST/CLR-SITELIST-018.md) | ANSWERED | SPEC-SITELIST-001 v0.7 | 以 API 建立子站台並帶入與主站台不同的站台類型時，後端是否拒絕、回應為何。v0.7 第 59、223 行的「後端強制／無權限」只列權限類限制（管轄範圍、自身站台限制、角色指派上限），未涵蓋類型繼承。CLR-SITELIST-001 rev 0（針對 v0.4）答「後端會擋下」，但該答案的 basis 與本次分析不同、也沒有自身答案範圍，不能直接作為 v0.7 的依據（X16）；需以 applicability 綁定到 v0.7 或重新確認，並確認回應內容 | 後端拒絕：以 API 建立子站台並帶入與主站台（上層站台）不同的站台類型時，後端會擋下，不只是前端唯讀限制。回應內容（錯 |
| [CLR-SITELIST-019](ba-admin/SITELIST/CLR-SITELIST-019.md) | ANSWERED | SPEC-SITELIST-001 v0.7 | 新站台建立時，是否自動於該站台自己的「鏈上錢包管理」啟用核心貨幣對應幣別、且不依賴根站台 admin 的鏈上錢包管理狀態。CLR-SITELIST-012 rev 0（針對 v0.4，修正 CLR-SITELIST-011）答「會自動啟用、不依賴上層」，但 v0.7 原文未載，且答案 basis 不同（X16），需以 applicability 綁定到 v0.7 或請 PM 補入 spec | 會自動啟用，且不依賴上層：新站台建立時，核心貨幣連動建立的同時，會自動在該站台自己的「鏈上錢包管理」啟用對應幣別（例如機 |
| [CLR-SITELIST-020](ba-admin/SITELIST/CLR-SITELIST-020.md) | ANSWERED | SPEC-SITELIST-001 v0.7 | 額度上限的允許範圍：負數如何拒絕（前端提示與後端回應）、上限值、可否帶小數。CLR-SITELIST-002 rev 0（針對 v0.4）答「前端顯示『值必須大於或等於 0』，後端也拒絕」，但 v0.7 原文未載，且答案 basis 不同（X16），需以 applicability 綁定到 v0.7 或重新確認 | 負數拒絕：額度上限輸入負數時，前端顯示「值必須大於或等於 0」，後端也會拒絕（雙層驗證）。上限值、可否帶小數，原答覆未定 |
| [CLR-SITELIST-021](ba-admin/SITELIST/CLR-SITELIST-021.md) | ANSWERED | SPEC-SITELIST-001 v0.7 | 場次逾時時間的單位、最低值與上限，以及低於下限或格式錯誤時的前後端回應。CLR-SITELIST-003 rev 0（針對 v0.4）答「後端最低 1 小時；超過 17 位數時前端格式錯誤、後端回 COMMON_INVALID_REQUEST_FORMAT」，但 v0.7 原文未載，且答案 basis 不同（X16），需以 applicability 綁定到 v0.7 或重新確認 | 單位為小時，後端最低值為 1 小時（低於 1 小時會被拒絕）；輸入超過 17 位數（極端格式）時，前端跳格式錯誤，後端阻 |
| [CLR-SITELIST-022](ba-admin/SITELIST/CLR-SITELIST-022.md) | OPEN | SPEC-SITELIST-001 v0.7 | 根站台 admin 底下能否存在站長帳號；若存在，其起始層與能否看到根站台這一列（v0.7 與開發包⑧只寫根站台自身的管理員看得到根站台列） |  |
| [CLR-SITELIST-023](ba-admin/SITELIST/CLR-SITELIST-023.md) | OPEN | SPEC-SITELIST-001 v0.7 | 客服、清稽核客服、財務三種角色能否進入站台列表、能否操作、可見範圍是否同為管轄範圍（開發包⑧第九節列為尚未定案，不阻擋開工） |  |
| [CLR-SITELIST-024](ba-admin/SITELIST/CLR-SITELIST-024.md) | OPEN | SPEC-SITELIST-001 v0.7 | 管理員略過前端，以 API 將子站台的上層站台設為其自身或其子孫站台時，後端是否拒絕、回應為何（第 59 行後端強制只列管轄範圍、自身站台限制、角色指派上限，未列循環防護；CLR-SITELIST-006 亦註明未涵蓋） |  |
| [CLR-SITELIST-025](ba-admin/SITELIST/CLR-SITELIST-025.md) | OPEN | SPEC-SITELIST-001 v0.7 | 管理員（尤其根站台 admin 的管理員）把站台改掛到不同類型或不同核心貨幣的主站台底下、或改掛到根站台底下使其成為主站台時，系統如何處理：禁止？允許且類型／貨幣如何變化？與「類型建立後不可修改」「子站台一律與主站台同類型」如何調和 |  |
| [CLR-SITELIST-026](ba-admin/SITELIST/CLR-SITELIST-026.md) | OPEN | SPEC-SITELIST-001 v0.7 | 「上層站台的管理員」是僅指直屬上層站台的管理員，還是任一管轄範圍涵蓋該站台的祖先站台管理員（例如根站台 admin 的管理員對孫層站台）；§角色與權限寫管理員對管轄範圍內所有子站台可切任意狀態 |  |
| [CLR-SITELIST-027](ba-admin/SITELIST/CLR-SITELIST-027.md) | OPEN | SPEC-SITELIST-001 v0.7 | 操作員能否進入站台列表（例如唯讀檢視自身場館的額度上限、場次逾時時間）；v0.7 與開發包⑧第五節的站台列表權限只列管理員與站長，開發包⑧第八節卻寫操作員對額度上限、場次逾時時間「唯讀」，未說明在哪個頁面檢視。前版 AC-SITELIST-0164 沿用 v0.4 RM 的「站台列表不對操作員開放」，v0.7 無原文依據 |  |
| [CLR-SITELIST-028](ba-admin/SITELIST/CLR-SITELIST-028.md) | OPEN | SPEC-SITELIST-001 v0.7 | 對主站台以下的使用者（看不到根站台），點擊路徑列「站台列表」回到的「根層」是指其起始層（自身所屬站台這一列）還是其他；路徑列是否顯示其上層站台節點 |  |
| [CLR-SITELIST-029](ba-admin/SITELIST/CLR-SITELIST-029.md) | OPEN | SPEC-SITELIST-001 v0.7 | 根站台 admin 新增或刪除網域時：(A) 不觸發更新待審、維持開通；(B) 觸發更新待審（則由誰、如何切回開通）；(C) 根站台的網域不可異動 |  |
| [CLR-SITELIST-030](ba-admin/SITELIST/CLR-SITELIST-030.md) | OPEN | SPEC-SITELIST-001 v0.7 | 「無權限」錯誤的實際錯誤代碼與回應格式（HTTP 狀態、錯誤代碼、訊息）；v0.7 與開發包⑧只規定語意、錯誤代碼由後端定義，CLR-SITELIST-015 註明截至 2026-10-09 後端尚未定案，須向後端確認後才能寫入 Test Case 的預期結果 |  |
| [CLR-SITELIST-031](ba-admin/SITELIST/CLR-SITELIST-031.md) | OPEN | SPEC-SITELIST-001 v0.7 | 「每個站台皆有管理員」的管理員帳號由誰、在什麼時機建立：(a) 沿用現行流程（自行註冊後由上層站台的管理員指派）；(b) 站台建立時由系統一併產生。若為 (b)，站台列表「新增站台」流程須多一步（產生帳號並一次性顯示帳密），SPEC-SITELIST-001 需再進版（開發包⑧第九節，不阻擋開工） |  |
| [CLR-SITELIST-032](ba-admin/SITELIST/CLR-SITELIST-032.md) | OPEN | SPEC-SITELIST-001 v0.7 | 以 API 建立子站台並帶入與主站台不同的站台類型時，後端拒絕的回應內容為何（錯誤代碼、訊息、HTTP 狀態）？ |  |
| [CLR-SITELIST-033](ba-admin/SITELIST/CLR-SITELIST-033.md) | OPEN | SPEC-SITELIST-001 v0.7 | 額度上限的上限值為何？可否帶小數（幾位）？超出時前後端如何回應？ |  |
| [CLR-SITELIST-034](ba-admin/SITELIST/CLR-SITELIST-034.md) | OPEN | SPEC-SITELIST-001 v0.7 | 場次逾時時間（單位：小時）的上限值為何？超出上限時前後端如何回應？ |  |

## ba-admin / TXLOG

| ID | 狀態 | 規格 | 問題 | PM 回覆 |
|---|---|---|---|---|
| [CLR-TXLOG-001](ba-admin/TXLOG/CLR-TXLOG-001.md) | APPLIED | SPEC-TXLOG-001 v0.1 | REQ-TXLOG-029 不符合時系統應如何反應？（Spec 未定義拒絕行為） | 此問題已 moot：交易紀錄查詢頁（本包）實際上並不提供『手動取消』這個操作，spec.md §操作 描述的『手動取消： |
| [CLR-TXLOG-002](ba-admin/TXLOG/CLR-TXLOG-002.md) | ANSWERED | SPEC-TXLOG-001 v0.1 | 交易紀錄查詢（機台視角）是否提供待確認交易的手動取消？REQ-TXLOG-028 目前依 2026-09-14／09-15 的確認（CLR-TXLOG-001、CLR-CASHFLOW-004）寫為「本頁不提供手動取消」，與 spec 原文及 CLR-REDPACKET-055 最新答案不一致；適用範圍（出金／入金）與可操作角色為何？ | 提供。交易紀錄查詢（4.1 機台視角）提供待確認「機台出金」的手動取消：僅管理員可操作（RD 已確認）、僅對交易狀態「待 |
