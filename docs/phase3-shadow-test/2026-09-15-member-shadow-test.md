# Phase 3 影子測試紀錄：qaos-test-designer × SPEC-MEMBER-001

- **日期**：2026-09-15
- **Run**：RUN-20260915-013（spec-to-testcase，spec_id=SPEC-MEMBER-001, spec_version=0.2）
- **目的**：測試 `.claude/agents/qaos-test-designer.md` 這個新建立的 Phase 3 agent，能否獨立完成 Test Designer 角色的工作。同一份 RequirementModel（18條 ACTIVE Requirement），先前已由人工扮演此角色走完整流程、核准為 26 條 ACTIVE TestCase（`testcases/MEMBER.md`）。這次讓 agent 完全獨立重做一次（刻意不讓它讀既有 TC，避免抄答案），產出送去跟審查人工版本用同一套獨立 Validator 機制（fork 出的乾淨 context subagent）審查，比較兩者差異、評估 agent 品質。
- **結果**：三輪皆 FAIL，第三輪（`max_validation_iterations=3`）觸發 **HUMAN_OVERRIDE（APR-0055，待人工裁決）**。

---

## 三輪演進總表

| 輪次 | TC數 | 新問題 | 被修好的問題 |
|---|---|---|---|
| 1 | 24 | 4個：REQ-MEMBER-005系統邊界誤判×2(blocker，假設後台有「申請出金」按鈕)、assumptions未誠實揭露(major)、design_technique系統性亂貼(major)、design_rationale全部24條皆空字串 | — |
| 2 | 24 | 1個新blocker：REQ-MEMBER-005修正後的precondition「稽核=1可避免投注門檻干擾」這個假設，跟同批REQ-MEMBER-011的TC自相矛盾（那條TC示範稽核倍數會改變投注門檻），且未標記為assumption | 第1輪全部4個問題 |
| 3 | 24 | 1個major：test_level未反映跨產品依賴這個原則，只套用在REQ-005，沒有一致套用到結構相同的REQ-007（TC11，後台切換狀態→驗證動作在前台登入）；另2個minor（assumptions報告層級摘要缺失、revision_of_issues記錄不完整） | 第2輪的blocker；並且**agent自主發現**並修正了一個沒人點名的新問題（REQ-004混淆「透過邀請鏈註冊」與「取得加盟商身分」兩個獨立條件） |

## 關鍵觀察

1. **Agent 學會了「修正被明確點名的錯誤」**，且修正品質隨輪次提升（design_rationale 從全空到全部具體、design_technique 從系統性亂貼收斂到誠實標記、系統邊界判斷從錯誤到正確）。

2. **Agent 展現了初步的主動發現能力**：第三輪在沒被要求的情況下，自己抓到並修正了 REQ-MEMBER-004 的一個邏輯漏洞（見 prompt 第10條「跨TC一致性自檢」新增後的效果）。

3. **但這個自檢能力沒有窮盡性**：它把修正模式套用到「被驗證抓到的具體案例」，卻沒能把同一個抽象原則（test_level 該反映真實系統邊界）系統性套用到全部 24 條 TC 逐一檢查。第二輪、第三輪的新問題，本質上是**同一類問題**（未經驗證的系統機制假設藏在 precondition 裡）換了個位置重演。

4. 這代表問題已經不是「prompt 少寫了一條規則」層次，比較接近**這個 agent 配置在「窮盡式自我審查」這件事上的能力邊界**。是否要繼續加 prompt 去逼近這個邊界，還是接受目前的迭代天花板、改為在既有的 3-round 上限後固定走人工複審，是需要人工決定的方向性問題。

## Prompt 演進

`.claude/agents/qaos-test-designer.md` 在本次影子測試期間新增：
- 第0條：動手寫 TC 前先確定功能實際發生在哪個介面（回應第1輪 blocker）
- 強化第1條：assumption 揭露不只適用於業務斷言，也適用於「測試資料怎麼佈置」的隱性假設
- 強化第3條：不要寫死具體帳號/編號
- 第9條：`design_techniques` 標籤誠實性，逐一給 decision_table/boundary_value/state_transition 的判斷標準
- 第10條（回應第2輪 blocker）：整批寫完後做一次跨 TC 一致性自檢——但第三輪證明這條指令本身沒能讓 agent 做到「窮盡」，只讓它多抓到一個案例

## 相關 Runtime 副產品

過程中也發現並修正了一個 Runtime 渲染缺口：`approval_render.py` 對 `HUMAN_OVERRIDE` 類型的 ApprovalRequest 沒有像 `ACTIVATE_TESTCASE`/`OPEN_BUG` 一樣渲染完整內容，只給一句話——這是本次意外發現、尚未修的技術債，跟之前修過的 `OPEN_BUG` 空白內容是同一類問題（都是特定 approval type 沒接上渲染邏輯）。

---

## 最終結案：Phase 2 × Phase 3 整合結果

**HUMAN_OVERRIDE（APR-0055）的裁決**：基於 `test_level` 欄位在 Runtime 裡零邏輯依賴（`grep -rn "test_level" tools/qaos/*.py` 零結果，純描述性 metadata），override 通過第三輪 FAIL，讓這 24 條 agent 版 TestCaseDraft 進入下一步討論——但**不是**直接核准進 Registry。

**Oscar 的關鍵決策（推翻了「整批擇一採用」的預設做法）**：
> 「我的目的是：對兩份tc的測項進行交叉比對後再進行整合，而不是最終產出的tc是純粹使用2或是3那份tc！！！ex: phase 2沒想到的測項phase 3 想到了，就要整合進去，當2或3的測項深度誰比較高，就使用誰的，去提高最終tc的深度跟廣度，達到優化tc的完整性」

因為 Phase 2（人工版，26條 ACTIVE）與 Phase 3（agent版，24條）覆蓋的是同一組 18 項需求，若整批核准 Phase 3 會與既有 Registry 產生重複 TC ID、且捨棄掉人工版本已驗證過的內容。因此改為**逐條交叉比對，採用兩邊之中更深入或更完整的處理方式，透過 `bin/qaos tc revise` 修訂既有 Phase 2 TC**，而非讓 Phase 3 版本以新 ID 進 Registry。

**確立的深度/廣度優先級**（用於判斷該不該整合、該整合什麼）：
```
深度底線（不能誤判） > 廣度覆蓋（不能留白） > 深度精進（可以慢慢做）
```
理由：廣度缺口是「未知風險」（沒有測到，但也沒有假裝測到）；深度缺陷（把未證實的機制講成已知、確定的事）是「已知但誤判的風險」——更危險，因為會製造錯誤的信心（以為測過了，但測試本身是錯的）。

### 中途事故：指令誤用導致整批誤核准

處理 TC-MEMBER-044 的 reject 時，`bin/qaos approve APR-0056 --decision approve --by ... --per-item TC-MEMBER-044:reject` 這行指令裡 `--decision approve` 是套用到整批的決定、`--per-item` 只是例外排除，不是「只處理這一項」——結果把同批其餘 23 條 Phase 3 TC 全部誤核准為 ACTIVE，直接違反上面 Oscar 否決的「整批採用」做法。發現後立即用 `bin/qaos tc retire`（非刪除，保留完整內容與審計軌跡）把 23 條全部撤銷回 RETIRED，恢復到交叉比對前的狀態，再重新逐條處理。

### 交叉比對的處理結果

| 類別 | 需求/TC | 處理方式 |
|---|---|---|
| 深度defect修正 | REQ-004(TC-005/006)、REQ-005(TC-007/008)、REQ-013(TC-018/019/020)、REQ-003(TC-004)、REQ-008(TC-012) | Phase 2 原版把未經證實的機制（邀請鏈≠加盟商身分、換算公式、升等門檻演算法、KYC已停用產生機制、後台備注欄位存在與否）講成已知/確定，依 Phase 3 或後續 Oscar 補充確認的資訊修正，多輪都經獨立 Validator FAIL→修正→PASS |
| 廣度缺口補齊 | REQ-010(TC-014，決策表由1組合擴至4組合)、REQ-011(TC-016，0/負數/留空從exploratory變grounded) | Phase 2 只測了部分情境，採用 Phase 3 更完整的設計 |
| 深度精進 | REQ-011(TC-015，抽象描述→具體數值)、REQ-014(TC-021/022，補持久性驗證)、REQ-017(TC-025，補實際驗證步驟) | Phase 3 版本更嚴謹但非致命缺陷，屬於「可以慢慢做」的優化，這輪一併處理掉 |
| 確認等效，未整合 | REQ-001/002/006/007/009/012/015/016/018 對應的 11 條 TC | 逐條比對 precondition/steps/expected_result，僅措辭詳略不同，無實質深度或廣度差異，維持 RETIRED |

**最終數字**：Phase 2 的 26 條 ACTIVE TC 中，**14 條**因整合 Phase 3 的發現而修訂（版本號 v2 以上，UI 上標「Phase 3 整合」）；Phase 3 原始的 24 條 TestCaseDraft 全數維持 RETIRED / DRAFT（不佔用 Registry 的獨立 TC ID）——其中 13 條的內容被吸收進上述修訂、11 條確認為純重複無額外價值。ACTIVE 總數維持 26 條不變。

**最終交付**：整合後的完整 TC 集已發佈為 [MEMBER 測試案例集](https://claude.ai/code/artifact/988747a7-5a77-4fbb-b7df-c1ca5a7f69f8)（依需求分組、可篩選 grounded/exploratory，標註哪些條目經過 Phase 3 整合），供實際測試執行使用；`testcases/MEMBER.md` 為系統自動匯出的完整版本稽核記錄。

### 這次實驗學到的事

1. **Agent 獨立設計的價值不在「取代」，在「交叉校驗」**：Phase 3 沒有一次抓到 Phase 2 完全沒發現的全新需求缺口，但多次抓到 Phase 2 把「未經證實」寫成「已知」的同一類 depth defect——這正是單一視角（不管是人工還是單一 agent）難以自己發現的盲點，需要第二個獨立視角交叉比對才浮現。
2. **「誠實揭露要進結構化 assumptions 欄位、不能只藏在文字描述裡」**這條原則貫穿整個整合過程，被獨立 Validator 反覆用來抓出同一類疏漏（TC-007/008、TC-016 皆因此被 FAIL 過至少一輪）。
3. **系統性指令風險**：`approve --decision X --per-item Y:Z` 這種「整體決定 + 例外」語意在操作上容易誤解成「只處理例外」，這次造成了需要額外一輪 retire 才能收拾的事故——操作這類批次指令前，應該先確認決定的作用範圍。

---

## 附錄：第三輪（最終版）24條 TestCaseDraft 完整內容

> 產出檔案：`artifacts/test-design/RUN-20260915-013/ART-TCD-01M2HWNZY62YX5RRFSJ9X1H13X.yaml`

### TC1｜OTP 報表可查詢指定年月的 OTP 使用次數
- requirement: REQ-MEMBER-001　ac: AC-MEMBER-001
- test_level: ui_e2e　test_types: functional　design_techniques: requirement_based　priority/risk: low/low
- preconditions: 以 Admin 登入後台，進入「會員與加盟商 > 會員列表」頁面
- steps: 1.點擊頁面頂部「OTP報表」按鈕，開啟彈窗 2.輸入指定年份與月份（例如 2026/08） 3.點擊「搜尋」 4.檢視查詢結果 5.點擊✕關閉彈窗，確認返回會員列表頁
- expected_result: 彈窗顯示指定年月的 OTP 使用次數查詢結果；點擊✕後彈窗關閉，返回會員列表頁不受影響

### TC2｜未選 KYC 階段時，KYC 狀態篩選欄位不可單獨作用
- requirement: REQ-MEMBER-002　ac: AC-MEMBER-002
- test_level: ui_e2e　test_types: negative　design_techniques: requirement_based　priority/risk: medium/medium
- preconditions: 以 Admin 登入後台，進入會員列表頁面，篩選器的 KYC 階段欄位維持未選擇（預設空值）
- steps: 1.嘗試直接操作 KYC 狀態篩選欄位（點擊下拉或嘗試選取任一狀態值）
- expected_result: KYC 狀態欄位不可篩選或無作用（例如反灰無法點擊、或即使可操作也不影響搜尋結果）——須先選定 KYC 階段才可有效篩選 KYC 狀態

### TC3｜已選定 KYC 階段後，搭配 KYC 狀態可正確篩選
- requirement: REQ-MEMBER-002　ac: AC-MEMBER-003
- test_level: ui_e2e　test_types: functional　design_techniques: requirement_based　priority/risk: medium/medium
- preconditions: 以 Admin 登入後台，進入「會員與加盟商 > 會員列表」頁面
- steps: 1.篩選器選擇 KYC 階段「身分證明文件驗證」 2.KYC 狀態選「審核中」 3.點擊搜尋
- expected_result: 搜尋結果僅包含『身分證明文件驗證』階段目前狀態為『審核中』的會員，不符合此組合條件的會員不出現在結果中

### TC4｜會員列表 KYC 狀態欄五個圖示依各階段實際狀態正確顯示顏色與 Tooltip
- requirement: REQ-MEMBER-003　ac: AC-MEMBER-004
- test_level: ui_e2e　test_types: functional　design_techniques: scenario　priority/risk: medium/medium
- preconditions: 以 Admin 登入後台，進入「會員與加盟商 > 會員列表」頁面；需要一名會員，其五個 KYC 階段合計涵蓋已核准/審核中/待補件/未申請/已停用五種狀態中至少三種以上——「已核准」「待補件」可由後台人員於會員詳細頁 KYC 狀態區塊對已開放審核的階段分別執行「通過」/「駁回」取得；「未申請」為該階段本就尚未送審的既有帳號；「審核中」需為會員已透過前台送出、後台尚未審核的既有測試帳號；「已停用」這個狀態如何產生 spec 全文未描述任何後台操作入口（見assumptions）
- steps: 1.於會員列表找到目標會員，檢視其 KYC 狀態欄五個圖示 2.逐一核對每個圖示顏色是否對應該階段目前的實際狀態 3.滑鼠移至任一圖示，確認顯示 Tooltip
- expected_result: 五個圖示顏色分別正確對應各自階段的實際狀態；滑鼠移至任一圖示時顯示 Tooltip，內容包含該階段名稱與目前狀態文字
- assumptions: 「已停用」狀態如何產生（是否有後台操作入口）spec 全文未定義，需環境負責人確認（needs_human_confirmation: true）

### TC5｜加盟商會員透過邀請鏈註冊時，側邊面板正確顯示完整上下層邀請鏈
- requirement: REQ-MEMBER-004　ac: AC-MEMBER-005
- test_level: ui_e2e　test_types: functional　design_techniques: requirement_based　priority/risk: medium/medium
- preconditions: 以 Admin 登入後台，進入會員列表；取一名既有會員，須同時符合兩個各自獨立的條件：(a)目前已具加盟商身分（見REQ-013，與註冊方式無關）(b)當初是透過另一名既有會員的前台邀請連結完成註冊
- steps: 1.於會員列表點擊該會員的會員編號，開啟右側簡易資料面板 2.檢視面板頂部的邀請鏈顯示
- expected_result: 面板頂部顯示完整的上下層關係：上層會員編號→當前會員編號→會員N人，且上層顯示的是實際邀請該會員註冊的會員編號
- **第三輪自檢新發現的修正**：舊版precondition把「透過邀請鏈註冊」跟「取得加盟商身分」混為一談（暗示註冊本身會讓人升級為加盟商），已修正為要求兩個獨立條件同時成立

### TC6｜非透過邀請鏈註冊的加盟商會員，側邊面板上層顯示為站長
- requirement: REQ-MEMBER-004　ac: AC-MEMBER-006
- test_level: ui_e2e　test_types: functional　design_techniques: requirement_based　priority/risk: medium/medium
- preconditions: 以 Admin 登入後台，進入會員列表；取一名並非透過前台邀請鏈註冊、且目前已具加盟商身分的會員
- steps: 1.點擊該會員編號，開啟側邊簡易資料面板 2.檢視面板頂部的邀請鏈顯示
- expected_result: 邀請鏈的上層顯示為「站長」，而非空白、錯誤資料或系統報錯

### TC7｜可提領餘額恰為 10 USDT 時不可於前台申請出金（邊界值，剛好不達門檻）
- requirement: REQ-MEMBER-005　ac: AC-MEMBER-007
- test_level: **integration**　test_types: boundary　design_techniques: boundary_value　priority/risk: high/high
- preconditions: 後台「可提領餘額」欄位只是唯讀顯示，spec全文沒有描述後台有可點擊的「申請出金」入口，此規則實際驗證入口是會員前台；需要一名會員的可提領餘額恰為10.00 USDT，spec未給出可提領餘額與帳戶餘額/提領所需有效投注額/稽核倍數之間的換算公式，佈置方式改為「透過人工存入/提出反覆調整，以後台實際顯示的讀數為準」，不依賴任何未經驗證的公式推算
- steps: 1.於後台帳務資訊區塊確認可提領餘額顯示為10.00 USDT 2.以該會員身分登入會員前台，進入出金/提領申請功能 3.嘗試送出出金申請
- expected_result: 前台阻擋出金申請，申請入口不可用或送出後被系統拒絕
- assumptions: ①前台測試環境是否可用需確認 ②可提領餘額換算公式spec未定義，需環境負責人/PM確認（皆 needs_human_confirmation: true）
- **第三輪修正**：移除第二輪「稽核=1可避免投注門檻干擾」這個跟REQ-011自相矛盾的假設，改為誠實承認換算公式未知；test_level 從 ui_e2e 改為 integration，結構化反映跨產品依賴

### TC8｜可提領餘額為 10.01 USDT 時可正常於前台申請出金（邊界值，略高於門檻）
- requirement: REQ-MEMBER-005　ac: AC-MEMBER-008
- test_level: **integration**　test_types: boundary　design_techniques: boundary_value　priority/risk: high/high
- （precondition/assumptions 同 TC7，數值改為 10.01）
- steps: 1.於後台確認可提領餘額顯示為10.01 USDT 2.以該會員身分登入會員前台 3.送出出金申請
- expected_result: 前台允許正常申請出金，申請成功送出

### TC9｜KYC 審核選擇駁回但未選取駁回原因時，系統阻擋儲存
- requirement: REQ-MEMBER-006　ac: AC-MEMBER-009
- test_level: ui_e2e　test_types: negative　design_techniques: negative　priority/risk: medium/medium
- preconditions: 以 Admin 登入後台，進入一名既有會員的詳細資料頁；取該會員KYC狀態區塊中至少一個已開放審核的階段
- steps: 1.對該階段選擇審核結果為「駁回」，不選取駁回原因 2.點擊「儲存」
- expected_result: 系統阻擋儲存，要求先選取駁回原因

### TC10｜顯示為『--』（未開放審核）的 KYC 階段不可執行審核操作
- requirement: REQ-MEMBER-006　ac: AC-MEMBER-010
- test_level: ui_e2e　test_types: negative　design_techniques: negative　priority/risk: medium/medium
- preconditions: 取該會員KYC狀態區塊中至少一個顯示為『--』的階段
- steps: 1.找到顯示為『--』的階段，嘗試對其執行審核操作
- expected_result: 該階段不存在可用的審核操作入口，無法執行任何審核動作

### TC11｜會員帳號狀態切換為停用後，該會員無法登入前台 ⚠️（本輪FAIL主因）
- requirement: REQ-MEMBER-007　ac: AC-MEMBER-011
- test_level: **ui_e2e（Validator指出應改為integration，未修正）**　test_types: negative　design_techniques: state_transition　priority/risk: high/high
- preconditions: 以 Admin 登入後台，一名會員目前帳號狀態為啟用
- steps: 1.於該會員詳細資料頁點擊帳號狀態旁的鉛筆圖示，將狀態從啟用切換為停用 2.該會員嘗試以自己的帳號**登入前台**
- expected_result: 該會員無法登入，前台系統拒絕其登入請求
- **問題**：steps第2步驗證動作發生在會員前台（跨出ba-admin），跟REQ-005結構相同（後台改狀態→前台驗證結果），但test_level沒有比照改為integration，被Validator判為「跨TC一致性自檢沒有窮盡」的證據

### TC12｜會員等級可由後台人員編輯，操作人員自動帶入當前登入帳號
- requirement: REQ-MEMBER-008　ac: AC-MEMBER-012
- test_level: ui_e2e　test_types: functional　design_techniques: requirement_based　priority/risk: medium/medium
- steps: 1.點擊會員等級旁「編輯」按鈕 2.選擇不同等級 3.後台備注選填 4.點擊儲存
- expected_result: 會員等級成功更新；操作人員欄位自動帶入當前登入帳號

### TC13｜人工存入可用「,」分隔一次對多筆會員編號批次執行
- requirement: REQ-MEMBER-009　ac: AC-MEMBER-013
- test_level: ui_e2e　test_types: functional　design_techniques: requirement_based　priority/risk: medium/medium
- steps: 1.確認會員編號欄預設帶入當前會員編號 2.額外以「,」分隔輸入另一名既有會員編號 3.填寫其他必填欄位後儲存
- expected_result: 系統對所有輸入的會員編號各自執行一筆相同金額的人工存入操作

### TC14｜人工存入前台備注與後台備注兩個必填欄位的組合驗證
- requirement: REQ-MEMBER-010　ac: AC-MEMBER-014
- test_level: ui_e2e　test_types: negative　design_techniques: decision_table　priority/risk: medium/medium
- steps: 四種組合（前台留空/後台留空/兩者皆空/兩者皆填）
- expected_result: 前三種皆阻擋，第四種（皆填寫）成功送出
- 備註：第三輪補上「兩者皆留空」這格使2x2矩陣完整（回應第二輪 advisory）

### TC15｜稽核倍數大於1時，提領所需有效投注額依倍數增加而非單純加回存入金額
- requirement: REQ-MEMBER-011　ac: AC-MEMBER-015
- test_level: ui_e2e　test_types: functional　design_techniques: requirement_based　priority/risk: high/high
- steps: 1.記錄存入前「提領所需有效投注額」(X) 2.人工存入100 USDT、稽核填3 3.檢視存入後數值
- expected_result: 變為 X+(100×3)=X+300，而非單純 X+100

### TC16｜稽核欄位輸入 0、負數或留空時的系統反應（exploratory）
- requirement: REQ-MEMBER-011　ac: AC-MEMBER-015
- test_level: ui_e2e　test_types: negative　design_techniques: error_guessing　priority/risk: high/high
- expected_result: spec未定義此規則，只能記錄實際觀察到的行為，不預設正確答案
- assumptions: 無效稽核值的系統反應spec未定義，需PM確認（needs_human_confirmation: true）

### TC17｜加盟列表點擊狀態 Toggle 可將啟用中的加盟商切換為停用
- requirement: REQ-MEMBER-012　ac: AC-MEMBER-016
- test_level: ui_e2e　test_types: functional　design_techniques: state_transition　priority/risk: medium/medium

### TC18｜加盟列表一般加盟商 Badge 三態顯示
- requirement: REQ-MEMBER-013　ac: AC-MEMBER-017/018/019
- test_level: ui_e2e　test_types: functional　design_techniques: decision_table　priority/risk: medium/medium
- assumptions: 升等門檻演算法spec未定義，需環境負責人確認（needs_human_confirmation: true）

### TC19｜客製化加盟商 Inline 編輯確認儲存
- requirement: REQ-MEMBER-014　ac: AC-MEMBER-020
- test_level: ui_e2e　test_types: functional　design_techniques: requirement_based　priority/risk: medium/medium

### TC20｜客製化加盟商 Inline 編輯取消還原
- requirement: REQ-MEMBER-014　ac: AC-MEMBER-021
- test_level: ui_e2e　test_types: functional　design_techniques: requirement_based　priority/risk: medium/medium

### TC21｜點擊最後登入IP跳轉至登入網域查詢頁
- requirement: REQ-MEMBER-015　ac: AC-MEMBER-022
- test_level: ui_e2e　test_types: functional　design_techniques: requirement_based　priority/risk: low/low

### TC22｜推薦註冊金新增時會員編號留空應被阻擋
- requirement: REQ-MEMBER-016　ac: AC-MEMBER-023
- test_level: ui_e2e　test_types: negative　design_techniques: negative　priority/risk: medium/medium

### TC23｜刪除推薦註冊金設定須二次確認，永久刪除不可復原
- requirement: REQ-MEMBER-017　ac: AC-MEMBER-024
- test_level: ui_e2e　test_types: negative　design_techniques: requirement_based　priority/risk: medium/medium

### TC24｜暱稱禁用詞四分頁設定互相獨立
- requirement: REQ-MEMBER-018　ac: AC-MEMBER-025
- test_level: ui_e2e　test_types: functional　design_techniques: requirement_based　priority/risk: low/low

---

## 待人工裁決（APR-0055）

```bash
bin/qaos approve APR-0055 --decision approve --by <you>    # override：接受現狀，記錄TC11已知瑕疵
bin/qaos approve APR-0055 --decision reject --by <you> --rationale "..."  # 再給一次機會
```
