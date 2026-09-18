#!/usr/bin/env python3
"""RUN-20260916-002 T2（iteration 2）：回應 ART-TVR-01M2MDFEB69P2GMKGKMKQXVMVN 的 FAIL。

上一輪（iteration 1，ART-TCD-01M2MCSQ3VZQ168YTF5BSQRA4N / ART-TDR-01M2MCSQ4RP6JGDP0T6XJT6GP6）
已修正前一份 TestValidationReport 的問題，但本輪 Validator 又抓到：

1. blocker：47 條 TC 中 34 條 design_rationale 為空字串（違反本專案硬規則：design_rationale 不准留空）。
   為全部 34 條補上實質內容：(a) 為何選擇該 design_techniques 組合、(b) test_data/佈置方式的選擇邏輯、
   (c) 若涵蓋多個 AC/requirement，說明整合理由。
2. major：全部 47 條 TC 的 expected_result_spec_reference 都缺少 quote。為全部 47 條補上逐字（或多列表格
   逐字）引用 spec.md 對應段落的 quote，可截斷但需對應到該 TC 的 expected_result 斷言。多數直接沿用
   RequirementModel 中對應 requirement 的 spec_reference.quote（該 quote 本身已是從 spec.md 逐字抽錄，經
   G-SPEC 驗證過），避免重新斷章取義；REQ-CASHFLOW-029（五種狀態碼）與 REQ-CASHFLOW-041（機台停用/場館未
   開通）則直接從 spec.md 附錄表格複製對應列。
3. minor x2：
   - TC-DRAFT-01M2MBHFR7GAYKTSCJ7ZSNGAF1（REQ-029）design_techniques 由 decision_table 改為
     equivalence_partitioning（5 個步驟各自是單一條件→單一結果的對照，非多條件交叉矩陣）。
   - TC-DRAFT-01M2MBHFR6DKCMSGEGYMHNEMNM（REQ-020 AC-0201）design_techniques 由 boundary_value 改為
     requirement_based（驗證的是「出金不套用洗分門檻取整」這個功能性事實，321 只是任選一個非門檻整數倍的
     值，並未真正操作任何數值邊界）。
"""
import sys, pathlib, copy, collections
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids

RUN = "RUN-20260916-002"
TASK = "T2"
AGENT = "agent-test-designer"
OLD_TCD_ID = "ART-TCD-01M2MCSQ3VZQ168YTF5BSQRA4N"
OLD_TDR_ID = "ART-TDR-01M2MCSQ4RP6JGDP0T6XJT6GP6"
OLD_TCD_PATH = f"artifacts/test-design/{RUN}/{OLD_TCD_ID}.yaml"
OLD_TDR_PATH = f"artifacts/test-design/{RUN}/{OLD_TDR_ID}.yaml"

old_tcd = store.load(OLD_TCD_PATH)
old_tdr = store.load(OLD_TDR_PATH)

tcd_payload = copy.deepcopy(old_tcd["payload"])
tdr_payload = copy.deepcopy(old_tdr["payload"])

tcs_by_id = {tc["draft_id"]: tc for tc in tcd_payload["testcases"]}

# ===========================================================================
# 1. design_rationale：34 條空白補齊
# ===========================================================================
RATIONALE = {
"TC-DRAFT-01M2MBHFR6VK7VQ6491GXPR5NK":
    "此案例採 requirement_based，直接依 AC-CASHFLOW-0021 逐字驗證『核可金額須扣除未完成稽核部分』這條規則本身，"
    "不涉及邊界或例外分支，故不需 boundary_value 或 negative。test_data 選稽核倍數=1（最小的非 0 值，恰可開啟稽核"
    "門檻但不引入倍數本身如何影響金額的複雜度）、機台餘額=1000 與未完成稽核部分=400 皆為刻意選擇的整數，讓『扣除後"
    "剩 600』的計算結果一望即知、便於執行者核對，而非測試任何特定邊界值；佈置『有未完成稽核金額』狀態的具體操作方式"
    "因 spec 未重新定義稽核判定的精確依據（例如以有效投注額對比存入金額的比例），已誠實標記於 assumptions 並要求"
    "人工確認，避免佈置步驟隱含未經驗證的機制假設。",
"TC-DRAFT-01M2MBHFR6A6Y344W8M8RGB34Z":
    "此案例選 boundary_value，因為驗證的核心是『扣除未完成稽核部分後金額恰為 0』這個邊界點（AC-CASHFLOW-0022 明確"
    "描述此邊界情境），故刻意讓 test_data 中機台餘額與未完成稽核部分相等（皆為 400），使扣除後精確落在 0 這個邊界，"
    "而非隨意挑一個不足額的數字；此手法與 AC-0021 的一般性驗證（TC-DRAFT-...VK7VQ6491GXPR5NK）互補——前者驗證扣除"
    "計算本身，本案例驗證扣除後為 0 時的邊界行為（視同餘額不足）。佈置『未完成稽核金額』狀態的具體操作方式同樣缺乏"
    "spec 明文定義，已標記於 assumptions 待環境負責人確認，避免佈置步驟隱含未經驗證的稽核判定機制假設。",
"TC-DRAFT-01M2MBHFR6XP0FQFE63NXFH2BG":
    "此案例採 boundary_value，直接測試 AC-CASHFLOW-0041 描述的『超過上限』邊界的相鄰兩點：加總『恰等於上限 A』"
    "（應成立）與『超過上限 1 單位』（應被拒絕），是驗證『超過…上限』這種比較邏輯最直接的邊界取值方式，而非任意選"
    "一個明顯超額的大數字。test_data 未寫死具體數字，改用相對量『現有合計為 A-100』搭配『開分 100』與『再開分 1』，"
    "讓執行者可依測試環境當下實際場館餘額推算出 A 與應佈置的差額，避免寫死可能不存在於環境中的絕對金額。"
    "expected_result 中『交易紀錄留有未成立紀錄』一句依 REQ-CASHFLOW-030（超過額度上限非餘額不足的例外情形，應留下"
    "未成立紀錄）補充說明，非 AC-CASHFLOW-0041 本身逐字斷言，但兩需求邏輯一致，一併驗證以提高本案例的驗證密度，"
    "不另拆一條 TC。",
"TC-DRAFT-01M2MBHFR66GECM0VGRNFRGH61":
    "此案例與 REQ-CASHFLOW-004（開分超限）採相同的邊界值設計手法：以『加總後恰等於上限』與『再加 1 即超限』兩個"
    "相鄰邊界點驗證入金額度判定，因為 AC-CASHFLOW-0071/0072 描述的正是這條比較邏輯的邊界行為，而非一般性功能是否"
    "運作。刻意合併 AC-0071（成立並預留）與 AC-0072（超限拒絕）於同一條 TC，因兩者本質是同一次測試流程中連續發生"
    "的一組對照（先驗證恰好通過、緊接著驗證下一筆超額），拆成兩條 TC 需重複佈置相同的初始額度環境，效率較差且無法"
    "體現『這兩個結果是同一組邊界的兩側』這個設計意圖。test_data 同樣未寫死絕對金額，改以『現有合計為 A-100』的相對"
    "描述，避免依賴測試環境當下不確定的實際額度數字。",
"TC-DRAFT-01M2MBHFR6YQ1QD64Q6R3K85C1":
    "採 negative 技術，直接對應 AC-CASHFLOW-0101 的『查無對應 PENDING 或 TXID 不符』這個明確拒絕分支；因 spec 對"
    "此分支的回應（僅記錄 log、回 1-NO RECORD、不變更任何資料）已在 §附錄-入金 逐字定義，屬於已定義的拒絕契約，故"
    "直接以 requirement 層級的斷言驗證，不需標記為 exploratory。test_data 選擇『從未建立過的 TXID』而非『已逾時"
    "關閉的 TXID』作為主要驗證路徑，是因為前者最單純、最不受其他狀態轉換（如 REQ-CASHFLOW-012 的 24 小時逾時）干擾，"
    "能單獨隔離『查無 PENDING』這個條件本身的行為；若需驗證『已逾時後查無 PENDING』的組合情境，屬於 "
    "REQ-CASHFLOW-012 的驗證範圍（見 TC-DRAFT-...DCNCAB8P4Z88GE0E）。",
"TC-DRAFT-01M2MBHFR6PRPRFPHNWNVJK009":
    "REQ-CASHFLOW-011 的冪等性是本包防止重複入帳的關鍵防線（spec 明確標註『關鍵防線』），故除 requirement_based "
    "直接驗證 AC-CASHFLOW-0111 定義的行為外，另加 error_guessing 標籤，因為步驟中特意模擬機台『15 秒未收到成功回覆"
    "即重送』與『跨斷電續送』這類真實會觸發的重送情境，而非僅呼叫兩次 API 的表面測試；這是針對已知高風險重放攻擊面"
    "的主動探測。test_data 未特別佈置金額，因為本案例驗證的是『重複呼叫是否加值兩次』這個布林性質的行為，任何非零"
    "金額皆可驗證，無需鎖定特定數值。",
"TC-DRAFT-01M2MBHFR6DCNCAB8P4Z88GE0E":
    "以 state_transition 驗證 spec 明定的 PENDING → 已逾時 這個狀態轉換，並合併 AC-CASHFLOW-0121（轉態本身）與 "
    "AC-CASHFLOW-0122（轉態後的後續行為）於同一條 TC，因為 0122 描述的正是『轉為已逾時之後』這個後續狀態下的行為，"
    "兩者在時間軸上是連續的同一個場景，拆開驗證需重複佈置相同的 24 小時等待條件，效率較差。24 小時等待為系統固定值"
    "而非可調參數，若無法加速判定，此 TC 的 execution_cost 與 stability 皆會受影響，此為誠實揭露於 assumptions 的"
    "環境限制而非本設計新增的假設。",
"TC-DRAFT-01M2MBHFR6NRXT46KMDY0BA2X1":
    "test_data 直接沿用 spec 範例表格中的『機台餘額 321、門檻 100』組合（並非隨機挑選），因為這正是 spec 用來說明"
    "捨去規則的官方範例，核可金額 300 的正確性可直接對照 spec 驗證，降低測試設計本身出錯的風險。合併 "
    "AC-CASHFLOW-0131（全洗）與 AC-CASHFLOW-0132（指定金額洗）於同一 TC，是因為 AC-0132 的核心斷言正是『與全洗結果"
    "相同』——這是一個相對性斷言，必須在同一組餘額/門檻條件下比較兩種操作模式的結果才有意義，拆開成兩條獨立 TC 反而"
    "會割裂這個『兩者應相同』的比較邏輯。標記 boundary_value 是因為 321 相對於門檻 100 恰好落在『捨去後餘 21』這個"
    "非整除邊界，能同時驗證捨去計算的正確性。",
"TC-DRAFT-01M2MBHFR6BE24MJN4AECVH993":
    "門檻 0 是 spec 明確定義的特例邊界（『門檻為 0 時表示洗出全部餘額、不做取整』），與 AC-CASHFLOW-0131/0132"
    "（門檻 100 的一般捨去情形，見另一條 TC）互為對照組：同樣的機台餘額 321，僅改變門檻是否為 0 這一個變數，藉此"
    "隔離驗證『門檻=0 是否真的完全跳過取整邏輯』而非受其他佈置差異干擾，因此標記 boundary_value（門檻值本身的邊界："
    "0 vs 正值）。",
"TC-DRAFT-01M2MBHFR6T17X9W76XDMFJJ6Y":
    "延續與 REQ-CASHFLOW-013 相同的測試資料（餘額 321、門檻 100），是刻意設計的承接關係：先驗證洗出 300 後餘數 21 "
    "確實保留在帳號上不被清除（AC-CASHFLOW-0141），緊接著在同一條 TC 的第二步驗證『餘數 21 單獨存在時無法再洗出』"
    "（AC-CASHFLOW-0142）——後者的佈置條件正是前者操作後自然產生的結果，兩個 AC 在邏輯上是一個操作的先後兩階段觀察，"
    "合併驗證比重新佈置一次餘額為 21 的獨立情境更能真實反映『餘數留存』這個規則的實際運作序列。標記 boundary_value "
    "是因為驗證核心是『餘數（不足一個門檻單位）』這個邊界情形下可洗金額的計算結果。",
"TC-DRAFT-01M2MBHFR6W2SA9J8T04FP4Y5S":
    "負值、缺漏、非數值三者皆屬 spec 定義的『規格外』等價類（廠商保證外情形），三者共享同一個防禦性處理結果（回 "
    "6-BAD DATA/FORMAT、不寫入帳務），故以 equivalence_partitioning 將三種輸入劃分為同一類異常輸入分別測試，而非"
    "逐一視為獨立情境；此設計目的是驗證『任何不符合廠商保證（正值或 0）的輸入』都收斂到同一個防禦分支，而非驗證某個"
    "特定數值的邊界（例如 threshold=-1 並非在測試『-1 與 0 的邊界』，僅是負值等價類中任取一個代表值）。",
"TC-DRAFT-01M2MBHFR64JFFPFVBD3Y80CK0":
    "test_data 選餘額 50、門檻 100（餘額小於一個門檻單位但非 0），是刻意避開『餘額恰為 0』這個更單純的情形，用以"
    "驗證『不足一個門檻單位即視為可洗金額 0』這個規則在餘額非零時依然成立，而不只是『沒錢自然洗不出來』的平凡情形；"
    "這是驗證計算邏輯（餘額<門檻 ⟹ 核可金額=0）而非單純驗證『無餘額不能操作』，故標記 boundary_value。",
"TC-DRAFT-01M2MBHFR6896H6AZQMQQWBHAT":
    "此需求本質與 REQ-CASHFLOW-005（開分無防護）同構，皆是驗證『沒有防護』這件事本身，故同樣選 error_guessing 而非"
    " negative——預期結果是重按後仍然成功（非拒絕）。test_data 刻意選『指定金額洗分且洗完後餘額仍足夠再洗一次同額』"
    "這個 spec 明確點名『第二次仍會成功』的特定組合（餘額 1000、洗 300、剩 700 仍夠再洗 300），而非隨機選一組數字；"
    "這是本規則唯一會實際造成重複扣款的組合（多數重複操作會被『餘額不足』自然擋下，見 spec §四種金流/洗分 機台顯示"
    "失敗時要怎麼辦），若佈置成餘額不足以再洗一次同額，則測試不到 spec 明確警告的風險情境。",
"TC-DRAFT-01M2MBHFR6MS79WC71E4CZVMM5":
    "以 state_transition 驗證出金 PENDING 的『有效 → 已取消（被新請求取代）』轉換，並合併 REQ-CASHFLOW-022"
    "（end-cashout 查無對應 PENDING 回 1-NO RECORD）於同一 TC，因為驗證『舊 PENDING 真的已失效』最直接的方式就是"
    "嘗試對它呼叫 end-cashout、確認觸發 REQ-CASHFLOW-022 的查無對應分支——這兩個需求在此情境下是因果相連的同一組"
    "行為（一個是取代機制、一個是取代後舊請求的自然後果），拆開驗證反而無法證明『失效』是真的生效而非僅是狀態欄位"
    "文字改變。",
"TC-DRAFT-01M2MBHFR6DKCMSGEGYMHNEMNM":
    "依獨立 Validator 意見修正：本案例驗證的是『出金完全不套用洗分門檻取整規則』這個功能性事實"
    "（AC-CASHFLOW-0201），並非任何數值邊界——刻意選 321 只是為了排除『餘額恰好是常見門檻整數倍』時無法區分『真的"
    "沒取整』與『取整後剛好結果相同』這兩種可能的歧義，屬於一般案例的選值考量，而非邊界值分析，故改標為 "
    "requirement_based 更精確反映實際判斷邏輯（原標 boundary_value 為誤用）。",
"TC-DRAFT-01M2MBHFR6NM5FDTJ6SZ7BCCXD":
    "與 AC-CASHFLOW-0201（同需求下的一般全額出金情境，見另一條 TC）互為對照組，同樣驗證『出金核可金額』計算規則，"
    "但取值刻意落在『餘額為 0』這個明確邊界（核可金額為 0 時的行為分支），故維持 boundary_value 標記——與前一條 TC "
    "的技巧選擇差異（requirement_based vs boundary_value）是刻意的：前者驗證『不取整』這個功能性規則，本條驗證"
    "『金額為 0』這個計算結果的邊界分支，兩者驗證的性質不同，非隨意湊技巧多樣性。",
"TC-DRAFT-01M2MBHFR6DVP7ESQKHM4G00K5":
    "以 state_transition 驗證『進行中 → 已結束(出金)』這個場次狀態轉換是否伴隨『餘額歸 0』正確發生，並額外以 "
    "error_guessing 針對 REQ-CASHFLOW-021 明文要求的冪等性（同 TXID 重複呼叫 end-cashout）做主動探測，因為出金"
    "冪等性若失效會直接造成『分數被扣成負值』這種嚴重資料錯誤，屬於高風險組合行為，值得在同一條 TC 內連續驗證"
    "（先完成、再重放）而非分拆。",
"TC-DRAFT-01M2MBHFR6G0FXNJJESAVKGBW5":
    "採 scenario 技巧，因為本案例本質是模擬一段連續的現場操作序列（結算無反應 → 分數未扣 → 玩家再按一次 → 舊 "
    "PENDING 自動取代），需要依時間順序串連多個步驟觀察狀態變化，而非單一輸入對單一輸出的規則驗證，故不適合標為 "
    "requirement_based 或 boundary_value。合併 AC-CASHFLOW-0241 與 AC-CASHFLOW-0242 是因為兩者描述的正是同一個"
    "現場情境的前後兩步（先無反應不扣分、接著重按由新請求自動取代），拆開驗證會失去『這是使用者連續操作同一問題』"
    "的情境完整性。",
"TC-DRAFT-01M2MBHFR6TZW6B37XSBNJ32CV":
    "直接依 AC-CASHFLOW-0251 逐字驗證過渡期（機台暫無印表機）的兩階段呼叫順序與扣分時點定義，採 requirement_based"
    "因為這是對明確定義流程的直接對照，不涉及邊界或例外分支。之所以未涵蓋 REQ-CASHFLOW-042（前台呼叫認證方式）與 "
    "REQ-CASHFLOW-043（end-cashout 失敗重送策略）這兩個同屬過渡期但明確標註『待確認』的開放問題，是因為兩者的具體"
    "行為尚無定案可測，已分別於 TestDesignReport.uncovered_with_reason 記載理由，不在本 TC 範圍內。",
"TC-DRAFT-01M2MBHFR69N6D59K767Q9DD2T":
    "採 negative 技術驗證『不存在某功能』這個否定性斷言（AC-CASHFLOW-0252 明確定義『系統不提供取消』），需要主動"
    "排查是否有任何後台或 API 入口可達成單純取消，而非僅依賴正面流程無法觸發取消就直接下結論。requirement_ids 同時"
    "列出 REQ-CASHFLOW-019 與 REQ-CASHFLOW-027，是因為 expected_result 中明確引用這兩個需求作為『取消訴求應改由這"
    "兩條路徑收斂』的替代說明（新請求取代、人工出金連動取消），屬於同一情境下互補說明其為何『不能取消』並不代表"
    "『無法收斂』，並非這兩個需求本身的直接驗證對象，本 TC 覆蓋範圍仍以 AC-CASHFLOW-0252 為主。",
"TC-DRAFT-01M2MBHFR6FY005FGJYW5ZZKRM":
    "以 requirement_based 直接驗證 AC-CASHFLOW-0271 定義的人工出金連動取消規則，並額外以 error_guessing 主動嘗試"
    "對已被取消的原 TXID 呼叫 end-cashout（模擬機台在人工處理完成前仍持續重送 end-cashout 的真實情境），驗證此時"
    "是否正確觸發 REQ-CASHFLOW-022 的『查無對應 PENDING』分支而非誤判完成扣分——這是驗證『連動取消』是否真正徹底"
    "生效（而非僅狀態欄位改變、底層仍可被完成）的關鍵路徑，屬於本規則『避免同一筆錢被領兩次』核心風險的直接探測。",
"TC-DRAFT-01M2MBHFR6XQB7BEF038786QTW":
    "直接依 AC-CASHFLOW-0281 驗證『人工入金不需處理既有入金 PENDING』這條與人工出金相反的規則，採 "
    "requirement_based 因為是對明確定義行為的直接對照；設計時特別參照同一份草案中 REQ-CASHFLOW-027（人工出金必須"
    "連動取消既有 PENDING，見另一條 TC）的驗證手法，確保兩條 TC 對『後續是否仍可用原 TXID 完成』這一步的驗證方式"
    "一致（皆以原 TXID 呼叫對應的 end-API 驗證最終結果），使兩者『刻意不對稱』的規則差異能被同一種驗證邏輯清楚對照"
    "出來，而非採用不同的驗證深度掩蓋了這個易混淆點。",
"TC-DRAFT-01M2MBHFR7GAYKTSCJ7ZSNGAF1":
    "依獨立 Validator 意見修正：本案例的 5 個步驟各自是『單一觸發條件 → 單一固定狀態碼』的一對一對照（例如『超過"
    "額度上限』恆對應 1-OVER LIMIT），並非多個條件交叉組合出不同結果的決策矩陣，故改標為 equivalence_partitioning，"
    "將五種未成立原因視為五個各自獨立的等價類分別驗證，與同份草案中其餘三條已修正的類似案例（REQ-023/026 印表機"
    "異常、REQ-030 餘額不足對照、REQ-041 停用/未開通）採一致的標籤判斷邏輯。情境三（機台停用/場館未開通）的後台"
    "操作切換路徑因 spec 未明確定義所在頁面，已標記於 assumptions 待環境負責人確認，避免佈置步驟隱含未經驗證的操作"
    "入口假設。",
"TC-DRAFT-01M2MBHFR731GMAY97H62T6FNC":
    "採 negative 驗證『此狀態碼永遠不會被使用』這個否定性斷言，刻意對照『已登入』與『未登入』兩種前台登入狀態皆需"
    "驗證，因為若僅測其中一種，無法排除『平台恰好在另一種登入狀態下才會誤觸發 2-OCCUPIED』的可能性；此為 low risk "
    "需求（廠商保留碼、非核心業務邏輯），故僅以單一 TC 涵蓋兩種登入狀態的等價驗證，不額外擴充更多情境。",
"TC-DRAFT-01M2MBHFR7578AW414F03BV0NB":
    "採 negative 直接驗證幣別不符時的拒絕規則，選以 req-keyin（開分）作為代表性 API 而非逐一測試四種金流 API 各自"
    "的幣別檢查，是因為 spec 將『幣別一致性』列為業務規則層級的通用驗證（§業務規則與驗證），適用於所有交易請求而非"
    "個別金流的特有邏輯，選單一 API 驗證足以代表此規則的正確性；若後續發現不同金流 API 對此檢查的實作有落差，應視"
    "為個別 API 的缺陷而非本規則設計遺漏。",
"TC-DRAFT-01M2MBHFR7FFFGAH13FXKK91BC":
    "以 state_transition 驗證『無場次 → 進行中』與『已結束(有餘數) → 進行中(新場次)』兩種場次開始路徑（分別對應 "
    "AC-CASHFLOW-0331 與 0332），合併於同一 TC 是因為兩者是 REQ-CASHFLOW-033 定義的同一條規則下的兩種觸發來源，"
    "理解上需相互對照。額外加入 negative 標籤的第 6 步（分數維持 0 時不應意外建立場次）是針對『場次開始』這個規則"
    "的反向探測——驗證的是觸發條件的『必要性』（沒有分數轉正就不該有新場次），這部分未在 AC 中逐字要求，但屬於狀態"
    "轉換規則常見的隱含反向約束，已於步驟中註明『屬理論情境』以誠實標示其驗證邊界，未過度延伸至無憑無據的斷言。",
"TC-DRAFT-01M2MBHFR7CMM7NG5Y0DG9VJ26":
    "直接依 AC-CASHFLOW-0341 驗證交易歸屬規則，採 requirement_based；驗證『結束場次的那筆洗分交易本身，歸屬於被它"
    "結束的場次』這句話是本規則最容易被誤實作的細節（直覺上可能誤植入新場次），故步驟中特別在洗分結束當下立即查詢"
    "該筆洗分交易自身的場次編號，而非僅驗證其他一般交易的歸屬。",
"TC-DRAFT-01M2MBHFR7C48Q0C1GX7JD0CG2":
    "以 state_transition 驗證『進行中 → 已結束』與『進行中 → 進行中（不變）』兩種對照轉換，合併 "
    "AC-CASHFLOW-0351（成功交易觸發結束）與 AC-CASHFLOW-0352（被拒絕或取消不觸發）於同一 TC，因為這兩者是驗證"
    "『觸發場次結束的條件邊界』所必須的正反兩面對照——僅驗證成功案例無法排除『任何請求（含失敗的）都會結束場次』"
    "這種過度寬鬆實作的可能性，必須同時驗證失敗/取消案例確實不觸發才能證明系統正確辨識了觸發條件。步驟 5-6 額外"
    "驗證『PENDING 被新請求取代』這種特殊的失效路徑同樣不觸發結束，是因為這是 REQ-CASHFLOW-019 定義的取代機制與"
    "本規則交界處，容易被忽略的組合情境。",
"TC-DRAFT-01M2MBHFR7VPRRGBQSG7V7K2XA":
    "直接依 AC-CASHFLOW-0361 驗證分數歸零結束場次的規則，採 requirement_based。因『分數因投注輸完歸 0』的觸發機制"
    "屬於遊戲/投注引擎範疇、不在本包（機台金流與場次純後端）定義的四種金流 API 範圍內，test_data 僅佈置一個小額"
    "餘額（例如 10）以縮短需要投注消耗的時間，具體如何在測試環境觸發分數歸零已誠實標記於 assumptions 待確認，避免"
    "佈置步驟隱含對投注引擎介面的未經驗證假設。",
"TC-DRAFT-01M2MBHFR7MQ9G300VBQDQQRM6":
    "以 state_transition 驗證『進行中 → 逾時結束』的轉換，並以 boundary_value 驗證『逾時時間即將到達前發生一筆"
    "交易』這個時間邊界點是否正確觸發計時重新起算（AC-CASHFLOW-0372）而非誤判逾時，這是本規則最容易出錯的臨界點"
    "（若重新起算的判斷時機有誤差，可能在交易發生瞬間仍被判定逾時）。test_data 未寫死具體時間長度，改用『可設定的"
    "短值（例如 2 分鐘）』並註明依場館設定範圍調整，是因為場次逾時時間為場館可調整項（不同於入金 PENDING 的 24 "
    "小時系統固定值），可直接透過既有設定縮短驗證所需時間，不需標記為需人工確認的假設。",
"TC-DRAFT-01M2MBHFR75GM0TKM39J6P0T3R":
    "以 state_transition 驗證『進行中 → 已結束(日結結算)』的批次轉換，並以 boundary_value 驗證『日結時間到達』"
    "這個時間點觸發的精確性（步驟中設定日結時間為『即將到達的時刻』以縮短等待），同時佈置兩台機台驗證此為場館層級"
    "的批次結束（而非僅單一機台），確保『所有進行中場次』這個全稱量詞式斷言被實際驗證而非僅抽樣一台即視為通過。",
"TC-DRAFT-01M2MBHFR7BYY2H6BRBS3N5VRD":
    "採 error_guessing 主動嘗試以近乎同時的方式觸發兩個場次開始條件（同一機台的開分與入金各一筆同時使分數轉正），"
    "探測併發情境下是否可能產生兩個進行中場次這個理論風險，而非僅驗證正常序列操作下的行為。因手動或一般序列化測試"
    "工具難以真正製造毫秒級並發，此限制已誠實標記於 assumptions，若需嚴謹驗證併發安全性需搭配專門的壓測工具，本 "
    "TC 僅能驗證『幾乎同時』情境下的表面結果。",
"TC-DRAFT-01M2MBHFR7XAPNHNGVR90YMB5H":
    "直接依 AC-CASHFLOW-0401 驗證線上會員頁面場次欄位顯示規則，採 requirement_based；此為 low risk 的單純 UI 顯示"
    "規則，故僅以單一情境（任一線上會員的任一筆紀錄）驗證，不額外擴充邊界或負向案例。",
"TC-DRAFT-01M2MBHFR7ZRFCM13FB7T3G46T":
    "採 negative 驗證『某功能不存在』這個否定性斷言，需主動檢視稽核倍數設定介面與開分相關操作是否存在任何可綁定至"
    "單筆交易的欄位或交易類型，而非僅因『沒看到』就直接判定不存在——這是本 spec 明確排除的範圍（v07 定案本次不"
    "實作），驗證重點是確認目前系統確實維持刻意排除的狀態，避免日後不小心誤實作進去卻未被察覺。",
}

assert len(RATIONALE) == 34, f"預期 34 條，實際 {len(RATIONALE)}"
for did, text in RATIONALE.items():
    tc = tcs_by_id[did]
    assert tc["design_rationale"] == "", f"{did} 原本非空，不應覆蓋"
    tc["design_rationale"] = text

# ===========================================================================
# 2. expected_result_spec_reference.quote：47 條全部補上
# ===========================================================================
QUOTE = {
"TC-DRAFT-01M2MBHFR6D6R13GTVBE4BAPCJ":
    "預設值 | 0 倍——即開分與入金不產生稽核門檻，玩家隨時可洗分與出金 ｜ 稽核明細 | 兩種交易照常寫入，類型顯示為"
    "「機台開分」「機台入金」",
"TC-DRAFT-01M2MBHFR6VK7VQ6491GXPR5NK":
    "倍數大於 0 時 | 洗分與出金的核可金額須扣除尚未完成稽核的部分；扣除後為 0 時視同餘額不足，機台畫面顯示餘額不足",
"TC-DRAFT-01M2MBHFR6A6Y344W8M8RGB34Z":
    "倍數大於 0 時 | 洗分與出金的核可金額須扣除尚未完成稽核的部分；扣除後為 0 時視同餘額不足，機台畫面顯示餘額不足",
"TC-DRAFT-01M2MBHFR6BNDJ0KH6Q06T303M":
    "交易紀錄的類型記為「機台開分」，金額為正值。交易完成（分數入帳）當下直接累計進該機台帳號於會員列表的「存款"
    "次數」「存款金額」（不需核實）",
"TC-DRAFT-01M2MBHFR6XP0FQFE63NXFH2BG":
    "判定與入帳於場館鎖內執行，與入金的預留共用同一把鎖而序列化，判定基準須含已預留未入帳的入金金額（v07 定案）；"
    "開分為單階段，判定即入帳。超過額度上限回 1-OVER LIMIT，不寫入任何帳務異動",
"TC-DRAFT-01M2MBHFR629BDC9VGDJ2VV9D5":
    "開分無任何自然防護——只要不超過額度上限，重按幾次就加幾次，是最高風險項",
"TC-DRAFT-01M2MBHFR62QDDARD522CKR67Z":
    "收到 req-cashin 一律建立新的 PENDING 並產生唯一 TXID，不使既有 PENDING 失效；同一帳號可同時存在多筆有效入金"
    " PENDING",
"TC-DRAFT-01M2MBHFR66GECM0VGRNFRGH61":
    "先取得場館鎖…在鎖內以「當下全場館機台分數餘額合計 ＋ 已預留未入帳的入金金額 ＋ 本筆金額」判定；未超限才建立"
    " PENDING、把本筆金額計入預留、釋放鎖，超限則回 1-OVER LIMIT、不建立 PENDING、不預留",
"TC-DRAFT-01M2MBHFR6ZCT58YWSAWFGDKH0":
    "先取得場館鎖…在鎖內以「當下全場館機台分數餘額合計 ＋ 已預留未入帳的入金金額 ＋ 本筆金額」判定；未超限才建立"
    " PENDING、把本筆金額計入預留、釋放鎖，超限則回 1-OVER LIMIT、不建立 PENDING、不預留",
"TC-DRAFT-01M2MBHFR6BKYKP99P5GHBHQFH":
    "預留額度的釋放（v07 定案）：入帳成功時預留轉為實際分數餘額",
"TC-DRAFT-01M2MBHFR6D578YPFV41R9NWHN":
    "PENDING 逾時（24 小時）由排程關閉時釋放；入金 PENDING 保留 24 小時，逾期自動轉「已逾時」；之後再收到 "
    "end-cashin 一律回 1-NO RECORD，機台停止重送，流程收斂",
"TC-DRAFT-01M2MBHFR6DJSNN5NG2KY6REYK":
    "收到 end-cashin 且 TXID 相符時，關閉 PENDING、更新帳務、把預留轉為實際餘額，回 0-OK。本階段不再判定額度上限",
"TC-DRAFT-01M2MBHFR6YQ1QD64Q6R3K85C1":
    "收到 end-cashin 但查無 PENDING 或 TXID 不符時，僅記錄 log 後丟棄，回 1-NO RECORD，不變更任何資料",
"TC-DRAFT-01M2MBHFR6PRPRFPHNWNVJK009":
    "平台必須具備冪等性：相同 TXID 第二次以後收到時，若該 PENDING 已完成，直接回 0-OK 且不重複加值",
"TC-DRAFT-01M2MBHFR6DCNCAB8P4Z88GE0E":
    "入金 PENDING 保留 24 小時，逾期自動轉「已逾時」；之後再收到 end-cashin 一律回 1-NO RECORD，機台停止重送，"
    "流程收斂",
"TC-DRAFT-01M2MBHFR6NRXT46KMDY0BA2X1":
    "計算規則：核可金額 ＝ 餘額以門檻為單位無條件捨去。例：門檻 100、餘額 321 → 核可 300；門檻 0、餘額 321 → "
    "核可 321（全額）",
"TC-DRAFT-01M2MBHFR6BE24MJN4AECVH993":
    "計算規則：核可金額 ＝ 餘額以門檻為單位無條件捨去。例：門檻 100、餘額 321 → 核可 300；門檻 0、餘額 321 → "
    "核可 321（全額）",
"TC-DRAFT-01M2MBHFR6T17X9W76XDMFJJ6Y":
    "餘數保留 | 洗分（門檻大於 0 時）僅扣除核可金額，不足一個門檻單位的餘數留在機台帳號上；系統不另記交易、不清空"
    "餘額",
"TC-DRAFT-01M2MBHFR6W2SA9J8T04FP4Y5S":
    "規格外的值（負值、缺漏、非數值）屬廠商保證外情形，防禦性處理：拒絕該筆、回 6-BAD DATA/FORMAT，不寫入任何"
    "帳務異動",
"TC-DRAFT-01M2MBHFR64JFFPFVBD3Y80CK0":
    "核可金額為 0 時回 1-NO CREDITS，不寫入任何帳務異動與交易紀錄",
"TC-DRAFT-01M2MBHFR61WZY318CERV7CY4J":
    "單階段，回 0-OK 即已完成扣款，無回滾機制；完成當下當前場次即結束，餘數由新場次承接",
"TC-DRAFT-01M2MBHFR6896H6AZQMQQWBHAT":
    "指定金額洗分、且洗完後餘額仍足夠再洗一次同額時，第二次會成功…玩家就被扣了兩次卻只拿到一次現金",
"TC-DRAFT-01M2MBHFR6MS79WC71E4CZVMM5":
    "同一帳號同時只允許一筆有效出金 PENDING；收到 req-cashout 時若已有既存 PENDING，必須先標記失效再建立新的｜"
    "收到 end-cashout 但查無 PENDING 或 TXID 不符時，僅記錄 log 後丟棄，回 1-NO RECORD",
"TC-DRAFT-01M2MBHFR6DKCMSGEGYMHNEMNM":
    "核可金額 ＝ req-cashout 當下的全部餘額（清空餘額、不套門檻）",
"TC-DRAFT-01M2MBHFR6NM5FDTJ6SZ7BCCXD":
    "核可金額為 0 時回 1-NO CREDITS，不建立 PENDING、不寫入交易紀錄",
"TC-DRAFT-01M2MBHFR6DVP7ESQKHM4G00K5":
    "end-cashout 扣分完成當下當前場次即結束，餘額歸 0、無餘數承接…同樣須對相同 TXID 的重複 end-cashout 具備冪等性",
"TC-DRAFT-01M2MBHFR6DWN957ZRBKQNHYGF":
    "列印還沒開始就偵測到異常（含按下結算時印表機即有異常）：機台直接結束流程、不通知平台，分數不扣、保留在機台"
    "上。平台這邊會留下一筆「待確認」的出金，現場其實什麼也沒發生｜已送入列印佇列後才實體故障（卡紙、缺紙）：如上"
    "所述，分數照扣，收據待狀況排除後自動印出",
"TC-DRAFT-01M2MBHFR6G0FXNJJESAVKGBW5":
    "按了結算卻沒有任何反應…分數一毛都沒扣，請玩家或店員再按一次結算即可。就算平台端留有前一筆待確認的出金，也會"
    "被新的一筆自動取代，不需人工處理",
"TC-DRAFT-01M2MBHFR6TZW6B37XSBNJ32CV":
    "扣分時點＝前台回報完成、平台扣分成功當下（不再以「送入列印佇列」為準）；場次亦於此時結束",
"TC-DRAFT-01M2MBHFR69N6D59K767Q9DD2T":
    "前台在請求出金到回報完成之間不提供取消",
"TC-DRAFT-01M2MBHFR6HECM6WW8W7JPPVPY":
    "第一階段有 15 秒逾時…但平台此時已建立 PENDING，該筆將永遠等不到 end-cashout，須由新的 req-cashout 取代或 "
    "Admin 手動取消收斂",
"TC-DRAFT-01M2MBHFR6FY005FGJYW5ZZKRM":
    "櫃檯對機台帳號人工出金時，必須同時取消該機台尚未完成的出金交易｜收到 end-cashout 但查無 PENDING 或 TXID 不"
    "符時，僅記錄 log 後丟棄，回 1-NO RECORD",
"TC-DRAFT-01M2MBHFR6XQB7BEF038786QTW":
    "櫃檯對機台帳號人工入金時，不需處理尚未完成的入金",
"TC-DRAFT-01M2MBHFR7GAYKTSCJ7ZSNGAF1":
    "1-OVER LIMIT｜超過額度上限；1-NO RECORD｜查無對應交易（查無對應 PENDING，或 TXID 不符）；7-OUT OF SERVICE｜機台停用中/場館未開通；9-OTHER ERROR｜憑證失效/系統錯誤；6-BAD DATA/FORMAT｜資料格式錯誤（欄位缺漏、型別錯誤、currency 與主站台核心貨幣不符、金額為負）",
"TC-DRAFT-01M2MBHFR73WF9S3D39DM64KQJ":
    "餘額不足 | 洗分時可洗金額為 0…或出金時餘額為 0。屬正常情形。不寫入交易紀錄——平台僅回覆機台餘額不足；本表"
    "其餘原因才會留下「未成立」紀錄",
"TC-DRAFT-01M2MBHFR731GMAY97H62T6FNC":
    "2-OCCUPIED | （不啟用）| 平台不回此碼…平台不把前台登入狀態當作機台交易的阻擋條件，不啟用此碼",
"TC-DRAFT-01M2MBHFR7578AW414F03BV0NB":
    "機台送來的幣別與主站台核心貨幣不符時，拒絕交易並記為「資料格式錯誤」",
"TC-DRAFT-01M2MBHFR7FFFGAH13FXKK91BC":
    "無進行中場次時，開分或入金完成使分數由 0 轉為有餘額，建立新場次；或前一場次因洗分結束後留有餘數，立即建立"
    "新場次承接",
"TC-DRAFT-01M2MBHFR7CMM7NG5Y0DG9VJ26":
    "進行中期間所有的開分、入金、洗分、出金與注單，一律歸屬於這個場次；結束場次的那筆洗分／出金交易，歸屬於被它"
    "結束的場次",
"TC-DRAFT-01M2MBHFR7C48Q0C1GX7JD0CG2":
    "任一筆洗分或出金交易完成（扣分成功）當下，場次即結束…核實僅是付現核銷",
"TC-DRAFT-01M2MBHFR7VPRRGBQSG7V7K2XA":
    "歸零結束 | 分數因投注輸完歸 0 時結束",
"TC-DRAFT-01M2MBHFR7MQ9G300VBQDQQRM6":
    "超過場館設定的「場次逾時時間」沒有任何交易與遊玩紀錄時，自動結束並標記為「逾時結束」…期間內有任何交易或注單"
    "即重新起算",
"TC-DRAFT-01M2MBHFR75GM0TKM39J6P0T3R":
    "日結結算 | 場館日結時間到達時，所有進行中的場次一律結束並標記為「日結結算」，剩餘分數轉為隔日新場次的期初"
    "餘額",
"TC-DRAFT-01M2MBHFR7BYY2H6BRBS3N5VRD":
    "併發 | 一台機台同時間只會有一個進行中的場次",
"TC-DRAFT-01M2MBHFR7XAPNHNGVR90YMB5H":
    "與線上會員共用的頁面…所帶的場次編號欄位，線上帳號沒有場次，一律顯示「—」",
"TC-DRAFT-01M2MBHFR7AN6YRP73P88CB402":
    "機台停用 | 停用中的機台無法運作；不影響餘額與尚未完成的交易｜場館站台狀態 | 場館站台（含自行經營的機台主"
    "站台）不是「開通」狀態時，該場館所有機台一律無法運作",
"TC-DRAFT-01M2MBHFR7ZRFCM13FB7T3G46T":
    "客戶回覆（2026-08-21）機台目前不需要稽核（維持預設 0 倍），但實務上存在「開分招待」活動…此活動無法以本節的"
    "稽核倍數實現：倍數是幣種層級設定，一設就綁全場館所有開分與入金，而招待只綁特定一筆；且「送分」為無現金流的"
    "交易，四種金流中尚無此類型",
}

assert len(QUOTE) == 47, f"預期 47 條，實際 {len(QUOTE)}"
assert set(QUOTE) == set(tcs_by_id), "QUOTE 的 draft_id 集合須與 testcases 完全一致"
for did, quote in QUOTE.items():
    tcs_by_id[did]["expected_result_spec_reference"]["quote"] = quote

# ===========================================================================
# 3. technique_mismatch x2
# ===========================================================================
gaf1 = tcs_by_id["TC-DRAFT-01M2MBHFR7GAYKTSCJ7ZSNGAF1"]
assert gaf1["design_techniques"] == ["decision_table"]
gaf1["design_techniques"] = ["equivalence_partitioning"]

dkcm = tcs_by_id["TC-DRAFT-01M2MBHFR6DKCMSGEGYMHNEMNM"]
assert dkcm["design_techniques"] == ["boundary_value"]
dkcm["design_techniques"] = ["requirement_based"]
dkcm["test_types"] = ["functional"]  # 原為 boundary，技巧改為 requirement_based 後同步調整 test_type

# ===========================================================================
# 重新計算 technique_summary（以最終 testcases 為準，避免手算出錯）
# ===========================================================================
tech_count = collections.Counter(t for tc in tcd_payload["testcases"] for t in tc["design_techniques"])
tdr_payload["technique_summary"] = [{"technique": k, "count": v} for k, v in tech_count.items()]

# ===========================================================================
# revision_of_issues：逐條回應 ART-TVR-01M2MDFEB69P2GMKGKMKQXVMVN.payload.issues
# ===========================================================================
tdr_payload["revision_of_issues"] = [
    {
        "issue_index": 0,
        "action": (
            "為 issue 中列出的全部 34 條 draft_id 補上實質內容的 design_rationale，每條分別針對該 TC 實際的 "
            "design_techniques 選型理由、test_data/佈置方式的選擇邏輯，以及涵蓋多個 AC/requirement 時的整合理由"
            "說明，非制式模板句。"
        ),
    },
    {
        "issue_index": 1,
        "action": (
            "為全部 47 條 TC 的 expected_result_spec_reference 補上 quote；多數直接沿用 RequirementModel 中對應 "
            "requirement.spec_reference.quote（已於 G-SPEC 驗證為忠實抽錄自 spec.md），REQ-CASHFLOW-029 與 "
            "REQ-CASHFLOW-041 因涉及跨列對照，改為直接逐字複製 spec.md 附錄/業務規則表格中的對應列。"
        ),
    },
    {
        "issue_index": 2,
        "action": "design_techniques 由 decision_table 改為 equivalence_partitioning（5 個未成立原因各自是單一"
                   "條件→單一固定狀態碼的對照，非多條件交叉出不同結果的決策矩陣），design_rationale 已同步說明理由。",
        "draft_id": "TC-DRAFT-01M2MBHFR7GAYKTSCJ7ZSNGAF1",
    },
    {
        "issue_index": 3,
        "action": "design_techniques 由 boundary_value 改為 requirement_based（測試資料 321 僅為任選的非門檻整數"
                   "倍值，驗證的是『出金不套用取整規則』這個功能性事實，並未真正操作任何數值邊界），"
                   "test_types 同步由 boundary 改為 functional，design_rationale 已同步說明理由。",
        "draft_id": "TC-DRAFT-01M2MBHFR6DKCMSGEGYMHNEMNM",
    },
]

# ===========================================================================
# 組 envelope 並寫檔
# ===========================================================================
def envelope(artifact_type, payload, references, source):
    aid = ids.artifact_id(artifact_type)
    art = {
        "artifact_id": aid, "artifact_type": artifact_type, "schema_version": "1.0", "version": 1,
        "run_id": RUN, "task_id": TASK, "iteration": 2, "created_by": AGENT, "created_at": store.now(),
        "status": "DRAFT", "source": source, "references": references, "requires_approval": None,
        "payload": payload,
    }
    p = store.ROOT / "artifacts" / "test-design" / RUN / f"{aid}.yaml"
    store.save(p, art)
    return aid, p

tcd_aid, tcd_p = envelope(
    "TestCaseDraft", tcd_payload,
    copy.deepcopy(old_tcd["references"]),
    copy.deepcopy(old_tcd["source"]),
)
tdr_payload["testcase_draft_artifact_id"] = tcd_aid
tdr_aid, tdr_p = envelope(
    "TestDesignReport", tdr_payload,
    [{"entity_type": "Artifact", "id": tcd_aid}],
    copy.deepcopy(old_tdr["source"]),
)

print(tcd_p.relative_to(store.ROOT))
print(tdr_p.relative_to(store.ROOT))
print(f"testcases: {len(tcd_payload['testcases'])}")
print("technique_summary:", dict(tech_count))
print("empty design_rationale remaining:", sum(1 for tc in tcd_payload["testcases"] if not tc["design_rationale"].strip()))
print("missing quote remaining:", sum(1 for tc in tcd_payload["testcases"] if not tc["expected_result_spec_reference"].get("quote")))
