# Phase 3 影子測試紀錄：qaos-test-designer × SPEC-BONUSCCY-002

- **日期**：2026-09-18
- **Run**：RUN-20260918-004（spec-to-testcase，spec_id=SPEC-BONUSCCY-002, spec_version=1.0）—— COMPLETED
- **目的**：波次2（CASHOUT＋BONUSCCY-002＋BONUSCCY-003同步派工）之一。BONUSCCY-002是「紅利幣別盤點」規格，涵蓋六種紅利類型的發放幣別規則與人工存款不觸發活動的規則。Phase 2 已有 13 條 ACTIVE TestCase，Test Designer 獨立設計出 9 條 TestCaseDraft（後經 4 輪修正擴增至 13 條）。
- **結果**：G-DESIGN 首輪即 PASS，G-TVAL 歷經 4 輪才 PASS——本專案目前修正輪次最多的一次，過程中發現並修正了一個真正的高風險覆蓋缺口。

---

## 設計與驗證階段

**第一輪 FAIL**（4個major）：REQ-BONUSCCY-004底下4條TC的quote把PM澄清內容當成spec.md原文引用，修正：quote只保留spec.md真正存在的句子。

**第二輪 FAIL**（1個blocker）：獨立Validator指出REQ-BONUSCCY-006（high risk）statement列出六種紅利類型（返水、代理佣金、推薦獎勵、每日/累積簽到、首存/次存活動、累積存款活動），但draft只針對返水/代理佣金設計了TC，簽到、首存/次存兩項完全無TC也無uncovered_with_reason記錄——spec.md對這兩項各有⚠️特別警示（簽到的道具獎勵不是錢不進錢包沒有幣別；首存/次存的「幣種」欄位選的是金流通道不是發放幣別）。修正時同時查證發現Validator把「推薦獎勵」也列為缺口是誤判（實際已由REQ-BONUSCCY-009既有TC覆蓋，只是掛在不同requirement_id底下）。

**第三輪 FAIL**（1個blocker+1個major）：新增的兩條TC提交後，test_design_report.yaml的coverage_matrix未同步納入，report本身無法反映缺口已補齊；首存/次存TC的step要求「透過TTK通道完成一筆存款」，與spec.md「線上站台也不會用非系統幣別的通道存款，目前都是死路」直接衝突，未揭露此環境限制。

**第四輪 PASS**：修正coverage_matrix同步、首存/次存TC補上「環境不支援則標記待執行」的退路（比照JACKPOT/跨站台推薦TC既有寫法）、簽到TC拿掉未支持的「道具持有清單」斷言並補上前台存取precondition。獨立Validator逐條核對13條TC與coverage_matrix完全一致，gates.py結構性規則（exploratory數量、assumptions欄位）全數符合，僅剩2個advisory（首存/次存TC可再補干擾排除敘述、環境限制的條件式語氣可再確定化），判定PASS。

## Phase 2 × Phase 3 交叉比對

9 條 AC 全部兩邊都覆蓋。**重要發現**：Phase2的AC-BONUSCCY-008底下其實已有5條TC（TC-010~014），分別對應返水、代理佣金、首存活動、簽到、累積存款活動五種類型——代表人工測試設計者一開始就已經意識到REQ-006 statement列舉的類型需要逐一驗證，這與Phase3歷經4輪才補齊的過程形成對比。逐條讀完斷言後：

- **AC-BONUSCCY-008**：
  - 返水、代理佣金：Phase2/Phase3斷言重疊——不採用Phase3版本
  - **多幣別同時持有的error_guessing edge case**（Phase3獨有）：查證發現Phase2的5條TC全數為requirement_based/happy-path風格，REQ-BONUSCCY-006（high risk）在Phase2完全沒有non-happy-path覆蓋，這條TC填補了此真正的覆蓋缺口——**採用**
  - 首存活動（Phase2 TC-012，驗證多幣別持有情境）vs **首存/次存幣種欄位陷阱**（Phase3，驗證⚠️警示的欄位語意陷阱，兩者是不同驗證角度）——**採用Phase3版本**（雖標記待執行，比照JACKPOT/跨站台推薦TC的既有處理慣例保留）
  - 簽到（Phase2 TC-013，明確聲明「道具類獎勵不在本案例驗證範圍」）vs **簽到含道具類不進任何錢包的負向驗證**（Phase3）——Phase3多驗證了一個有意義的負向斷言，對應spec明確⚠️警示——**採用Phase3版本**
  - 累積存款活動：Phase2/Phase3斷言重疊——不採用
- **AC-009（彩金活動）、AC-010（JACKPOT）、AC-011（推薦註冊金）**：兩邊斷言重疊，Phase3的補充句多為既有斷言的延伸說明，不構成新驗證角度——不採用
- **AC-012（人工存款不觸發首存/次存）**：Phase3多了「查『優惠活動管理』參與/發放紀錄」這個雙重驗證管道，但該頁面路徑屬合理推測非spec明確定義，Phase2版本已足夠清楚可執行——不採用
- **AC-013（簽到有效會員門檻）**：兩邊斷言重疊——不採用
- **AC-014（稽核流水）**：Phase2版本只驗證「有依倍數計入」；**Phase3版本用「同金額、不同稽核倍數比較增量大小」的相對驗證法**，能驗證「倍數確實生效影響數值」而非僅「有計入」，是更精確的機制驗證，能抓到Phase2版本抓不到的bug（倍數欄位有填但未生效）——**採用Phase3版本**
- **AC-015（累積存款門檻）、AC-016（VIP等級）**：Phase2版本明確測了「金額剛好卡在邊界值」，驗證強度不輸甚至優於Phase3——不採用

**最終處置**：依ADR-007走輕量方式，用`bin/qaos approve APR-0121 --decision reject --per-item TC-BONUSCCY-054:approve --per-item TC-BONUSCCY-060:approve --per-item TC-BONUSCCY-063:approve --per-item TC-BONUSCCY-064:approve`核准這4條新增TC，其餘9條Phase3草稿不採用。核准後獨立查驗Registry狀態，確認恰好4條變ACTIVE。

**結果**：Phase2既有13條ACTIVE TC + 新增4條（TC-BONUSCCY-054、060、063、064）= 17條ACTIVE。

## 關鍵教訓

這是本專案迄今修正輪次最多（4輪）的案例，但也最清楚示範了「深度底線 > 廣度覆蓋 > 深度精進」原則的完整應用：
1. **深度底線**：REQ-BONUSCCY-006（high risk）一度完全沒有non-happy-path覆蓋——這是Phase2、Phase3草稿初版都沒發現的真正缺口，直到交叉比對階段系統性檢查每個Phase2 TC的design_techniques分布才浮現，最終由Phase3的error_guessing案例補上。
2. **廣度覆蓋**：簽到、首存/次存兩個spec明確⚠️警示的高風險點，Phase3草稿一開始完全缺測，經過第二輪Validator抓出、第三/四輪逐步修正到位。
3. **深度精進但不濫用**：AC-014稽核流水的「倍率比較法」確實比Phase2版本更嚴謹，值得採用；但AC-012/015/016等多處Phase3提供的「額外驗證管道」或「補充說明」，在Phase2版本已經可執行、可觀察、有明確spec依據的情況下，並未只因為「看起來更詳細」就採用，避免了為了用而用的重複案例。

另外，Phase2的AC-008五條TC本身呈現的設計思路（用「多幣別同時持有」情境反覆驗證五種紅利類型各自不受其他幣別影響），與Phase3後來才想到的「幣種欄位陷阱」「道具類不進錢包」是兩種不同但互補的風險角度——這提醒了交叉比對不能只看「這個AC兩邊有沒有TC」，還要看「兩邊TC實際在測什麼機制面向」，同一個AC底下可能有多個值得各自獨立保留的驗證角度。
