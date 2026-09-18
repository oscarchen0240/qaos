# Phase 3 影子測試紀錄：qaos-test-designer × SPEC-SITELIST-001

- **日期**：2026-09-17
- **Run**：RUN-20260916-007（spec-to-testcase，spec_id=SPEC-SITELIST-001, spec_version=0.4）—— 已於整合完成後 `run cancel`
- **目的**：與 SITELIST（站台列表，全部開發包的前置相依）並行的 Phase 3 影子測試。Phase 2 已有 57 條 ACTIVE TestCase，Test Designer 獨立設計出 66 條 TestCaseDraft。
- **結果**：G-TVAL 十輪後 PASS。是本專案至今輪數最多的一次 Phase 3 影子測試，主因是同一條規則（REQ-SITELIST-002 admin 例外）被連續戳出多層問題，加上我自己犯了兩次流程/分析錯誤。

---

## 十輪演進總表

| 輪次 | 結果 | 卡點 |
|---|---|---|
| 1 | FAIL | 正常首輪問題：AC-0072 覆蓋沒走結構化記載、REQ-002 引文誤導成 spec 原文 |
| 2 | FAIL | Validator 質疑 admin 例外規則本身的真實性（RM 記錄時序矛盾：確認日期早於記錄時間）+ REQ-017 同類引文問題 |
| 3 | FAIL | Oscar 確認規則為真後，Validator 指出這條 TC 跟 AC-0011 操作路徑完全重複、無新證據 |
| 4 | FAIL | 開的 CLR-010 被抓到「同一人17秒內自問自答」的結構性弱點；「已涵蓋」宣稱經 grep 查證是假的（升級 Opus 處理） |
| 5 | FAIL | CLR-010 沒涵蓋到「不需預先啟用」這句話；新 TC 的 step4 斷言越界到別的 AC |
| 6 | PASS | 上述修正確認生效，僅剩 2 個 minor |
| 7 | FAIL | 深入追問「不需預先啟用」的精確語意，發現鏈上錢包管理跟核心貨幣其實是兩個不同系統（CLR-011），但 CLR-011 本身的 provenance 又被 Validator 用同資料夾其他 9 張 CLR 當基準比對後判定過弱；Oscar 決定不 override、改標 exploratory 保留安全網 |
| 8 | PASS | exploratory 標記修正確認生效，issues 掛零 |
| 9 | FAIL | Phase2×3 交叉比對時發現既有 ACTIVE 的 TC-SITELIST-063（早於本輪討論即存在）斷言「核心貨幣連動建立會自動啟用該站台自己的鏈上錢包管理」，直接推翻 CLR-011「完全無關」的結論，緊急開 CLR-012 修正；同時我自己把 5 條「API繞過/邊界值、spec未定義」的 exploratory TC 誤掛到內容不符或標記標準不一致的 AC 上 |
| 10 | PASS | CLR-012 修正 + revert 誤掛的 5 條 TC，確認一致 |

## 關鍵教訓

1. **CLR 的稽核強度是可以被獨立 Validator 用「同資料夾其他 CLR 的既有慣例」當基準比對出來的**——不是靠內容寫得好不好判斷，是看 raised_by／asked_to／ASKED 中繼狀態／回覆間隔這些結構性欄位。本專案 orchestrating session（我）即時記錄對話確認的 CLR，天生就是這種比對下的弱項，這是架構限制，不是流程能修正的。

2. **這個限制的正確處理方式不是硬闖（override），是保留 exploratory 標記當安全網**——Oscar 明確定調「保留驗證標準，這是這個專案的鐵則」。TC 本身的黑箱驗證設計可以維持正確，只是把確定性層級誠實標低，等有更強來源時再升級。

3. **既有的 ACTIVE TC 是比對話確認更強的獨立證據**——第9輪最關鍵的轉折是 Phase 2×3 交叉比對這個動作本身揪出了 TC-SITELIST-063（早於這一整串 CLR 討論就存在）跟 CLR-011 結論矛盾。這證明了「先做完 Phase 3 設計、再做交叉比對」這個順序的價值：交叉比對不只是選optimal TC，也是一層額外的事實查核。

4. **我自己在這輪犯了兩次錯，都被獨立 Validator 抓到**：
   - 過早升級到 Opus 前，沒有先精確定位問題範圍（「不需預先啟用」這句話原來語意不完整）
   - 交叉比對時，看到「Phase2=2條、Phase3=1條」就直接假設是漏標並動手修正，沒有先驗證內容是否真的對應到目標 AC、也沒有檢查同份草案內部是否已有一致的處理慣例——這次的 fix 反而製造了新的不一致，被第9輪抓到後才發現正確做法是完全不動（revert）。
   教訓：TC 數量落差不能直接當作「該補標籤」的證據，必須先讀懂 AC 的 given/when/then 精確範圍，並檢查同一份草案內部有沒有既定慣例可循。

## Phase 2 × Phase 3 交叉比對最終結果

66 條 AC 中：
- **64 條**：語意等價或 Phase2 既有 TC 已完整涵蓋，維持 Phase2 現有 57 條 ACTIVE TC 不動
- **AC-SITELIST-0023**（REQ-SITELIST-002 admin 例外）：透過 CLR-SITELIST-012 修正機制描述，採用 Phase2 既有的 TC-SITELIST-063（在本輪討論前就已存在且正確），Phase3 對應草稿不予採用
- **AC-SITELIST-0241**（主站台可獨立經營）：Phase3 的合併版 TC 只測了「互不影響」，沒測到 REQ-SITELIST-024 statement 裡「主站台可自行經營作為一間場館」這個獨立斷言；沿用 Phase2 既有的 TC-SITELIST-045，與 Phase3 版本互補
- **AC-SITELIST-0072**：Phase3 判斷「驗證點在 SPEC-DAILYREPORT-001」正確，SITELIST 範圍內的部分（AC-SITELIST-0071）已由既有 TC 涵蓋，不需修正
- **AC-SITELIST-0231**：兩邊皆判定不適用（刪除功能不存在），RequirementModel 已知的資料落差

**最終處置**：APR-0113（66條Phase3草稿整批啟用）reject，Phase2 既有 57 條 ACTIVE TC 維持不動，全部有價值的內容都已經在既有 TC 或本輪的 CLR 修正中處理完畢，無需任何 `tc revise`。

## 本輪產出的 CLR

- CLR-SITELIST-010：REQ-SITELIST-002 admin 例外規則本身的真實性確認
- CLR-SITELIST-011：鏈上錢包管理與站台核心貨幣的關係（後被 CLR-012 修正）
- CLR-SITELIST-012：修正 CLR-011「完全無關」的錯誤結論，改為「性質不同但有連動關係」，並記載既有 TC-SITELIST-063 作為獨立佐證
