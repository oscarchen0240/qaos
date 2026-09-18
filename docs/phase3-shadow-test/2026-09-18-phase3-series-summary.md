# Phase 3 影子測試系列總結：13 份 spec 的跨 spec 回顧

- **期間**：2026-09-15（MEMBER）～ 2026-09-18（ARCADE）
- **範圍**：13 份 spec 全部完成（SPEC-COMMON-001 依 2026-09-18 決定排除，不計缺口）
- **方法**：每份 spec 由 Test Designer 獨立設計 TestCaseDraft（不讀 Phase 2 既有 TC），經 G-DESIGN／G-TVAL 後，與 Phase 2 人工版 TC 交叉比對，只把有淨新增驗證價值的納入 Registry
- **數據來源**：本檔所有數字均從 `runs/*/run.yaml`（engine 記錄的 gate 結果）、`approvals/*.yaml`（T4 候選）、`testcases/registry/`（最終狀態）、各 spec 的 shadow-test 文件讀出，未憑記憶

---

## 1. 總覽

| Spec | Phase2 既有 | Phase3 草稿 | G-DESIGN 被擋次數¹ | 獨立審查輪次² | engine G-TVAL³ | 整合方式 | 新增 | 修訂 | 最終 ACTIVE |
|---|---|---|---|---|---|---|---|---|---|
| MEMBER | 26 | 24 | 0 | 3（F/F/F→override） | F/F/F | 修訂型 | 0 | **14** | 26 |
| CASHFLOW | 60 | 47 | 3 | 3（F/F/P） | F/F/P | 修訂型 | 0 | **4** | 60 |
| SITELIST | 57 | 66 | 0 | **10** | 10 輪 | CLR 修正型⁴ | 0 | 0 | 57 |
| ACCOUNT | 57 | 64 | 1 | 1（P） | P | 輕量新增 | 4 | 0 | 61 |
| TXLOG | 41 | 45 | 0 | 2（F/P） | F/P | 輕量新增 | 2 | 0 | 43 |
| BONUSCCY-001 | 12 | 14 | 4 | 3（F/F/P） | F/F/P | 輕量新增 | 4 | 0 | 16 |
| CASHOUT | 42 | 45 | 0 | 1（P） | P | 輕量新增 | 6 | 0 | 48 |
| BONUSCCY-002 | 13 | 13 | 2 | 4（F/F/F/P） | F/F/F/F/P⁵ | 輕量新增 | 4 | 0 | 17 |
| BONUSCCY-003 | 6 | 6 | 0 | 1（P） | P | 全數不採用 | 0 | 0 | 6 |
| DAILYREPORT | 54 | 43 | 0 | 2（F/P） | P | 輕量新增 | 1 | 1⁶ | 55 |
| UPDATEPACK | 16 | 16 | 0 | 2（F/P） | P | 輕量新增 | 2 | 0 | 18 |
| PLATFORMRULE | 32 | 32 | 0 | 2（F/P） | P | 輕量新增⁷ | 2 | 0 | 34 |
| ARCADE | 7 | 7 | 0 | 1（P） | P | 輕量新增 | 2 | 0 | 9 |
| **合計** | **423** | **422** | — | — | — | — | **27** | **19** | **450** |

¹ `run.yaml` T2 structural gate 結果中的 FAIL 數（structural 重試不計 iteration）。
² 以 shadow-test 文件記載的**獨立 Validator subagent** 審查輪次為準。
³ engine `run.yaml` T3 semantic gate 序列。**從 DAILYREPORT 起與 ② 不一致**：後期做法是獨立審查先行、FAIL 修正後才把最終 PASS 送進 engine，engine 只看到一個 P，低估真實輪次。
⁴ SITELIST 的價值不在 TC，而在交叉比對揪出 RequirementModel 的資料錯誤（CLR-SITELIST-010→011→012），Phase 2 的 57 條原封不動。
⁵ 5 個 semantic 結果中有 1 次是提交格式錯誤造成的重複，實際內容輪次 4。
⁶ TC-DAILYREPORT-046 依 CLR-DAILYREPORT-009 走 `testcase-revision` 修訂為 v2（原斷言方向被 PM 推翻）。
⁷ PLATFORMRULE 曾被外部指揮台整批 approve（32 條全 ACTIVE），確認非刻意後以 `tc retire` 退回 30 條（APR-0126~0155），最終回到分析建議的 2 條。

---

## 2. 整體數字

- **Registry 最終**：450 條 ACTIVE（13 份 spec），其中 34 條 exploratory（帶 `assumptions` 待人工確認）
- **Phase 3 對 Registry 的實質貢獻**：27 條新增 + 19 條修訂 = **46 條**（占最終 450 條的 10.2%）
- **「輕量新增型」10 份 spec 的採用率**：候選 285 條 → 採用 27 條 = **9.5%**。這個數字低是**設計使然**——交叉比對原則是「深度底線 ＞ 廣度覆蓋 ＞ 深度精進」，Phase 2 人工版已覆蓋的一律不重複採用；採用率高反而代表 Phase 2 品質差
- **Validator 抓漏率**：13 份中 **9 份**（69%）至少被獨立 Validator 抓出一次 blocker／major；真正首輪即 PASS 的只有 ACCOUNT、BONUSCCY-003、CASHOUT、ARCADE 四份
- **Test Designer 的 G-DESIGN structural 表現**：13 份中 **12 份首次提交即 structural PASS**（只有 CASHFLOW 首次被擋）；整個過程中曾被 structural gate 擋過的有 4 份（CASHFLOW 3 次、BONUSCCY-001 4 次、BONUSCCY-002 2 次、ACCOUNT 1 次），全是 schema／枚舉／欄位型別層級的抄寫錯誤（如 `state_change` 不在 test_types 枚舉、draft_id 長度、quote 超 300 字），不是設計問題；structural 重試不消耗 semantic iteration（`test_40` 保證），所以這些不影響輪次計數

---

## 3. 方法論演進（三個階段）

| 階段 | Spec | 整合方式 | 為什麼改 |
|---|---|---|---|
| **修訂型** | MEMBER、CASHFLOW | 把 Phase 3 發現的洞併回 Phase 2 既有 TC，產生 v2 版本（MEMBER 14 條、CASHFLOW 4 條） | MEMBER 一份就跑了三輪 + override + 一次誤核准事故，每條修訂都走全套 Validator＋逐條核准，Oscar 審核成本過高 → 催生 **ADR-007**（風險分級審查） |
| **輕量新增型** | ACCOUNT 起的 10 份 | Phase 2 不動；Phase 3 草稿只挑有淨新增驗證角度的納入，其餘 reject；用 `--decision reject --per-item X:approve` 安全模式 | ADR-007 落地。SITELIST 十輪的教訓：多數往返是在修同一條規則的認知，而非 TC 本身 |
| **真 subagent 設計** | DAILYREPORT 起的 4 份 | Test Designer 改用 `qaos-test-designer` subagent（前 9 份是「人扮 agent」腳本），且刻意不讓它讀 Phase 2 TC | 前 9 份的獨立性其實是「我不刻意抄」，非結構性隔離；後 4 份才是真正的獨立設計視角。結果：4 份全部首輪 G-DESIGN PASS，交叉比對後 1～2 條淨新增，證明獨立視角品質可信 |

另外兩條同期形成的流程規則：
- **獨立 Validator 一律附 `gates.py` 原始碼**（BONUSCCY-001 起）：因為 Validator 曾對 `is_exploratory()` 的判定規則做出錯誤的技術主張，我未查證就照改，反而觸發真正的結構性上限。
- **核准流程分級**（ARCADE 起）：Phase2×3 交叉比對後的 `ACTIVATE_TESTCASE` 可自主 per-item 核准；但 `NEEDS_DECISION`／`HUMAN_OVERRIDE` 這類 run 流程控制單一律只寫建議到 `.warroom/recommendations/`，由使用者在指揮台決定。

---

## 4. Test Designer（agent）的表現

**做得好的**：
- 覆蓋率：13 份全部達到 requirement／AC 全覆蓋（或有合規的 `uncovered_with_reason`），CASHOUT 45 條一次到位（31/31 req、44/44 AC）
- 自我一致性檢查：後期 subagent 會在提交前主動跑「跨 TC 機制假設一致性」自檢，DAILYREPORT 因此自行避開了一個「設定變更立即生效」的未揭露假設
- 誠實揭露：ARCADE 的 5 條 exploratory 全部是「機台端硬體流程無法由後台觸發」這類真實環境依賴，非濫用

**反覆出現的弱點**（依出現次數）：
1. **quote 真實性**（CASHFLOW、BONUSCCY-001、PLATFORMRULE、ARCADE、UPDATEPACK 上游 RM）：把 PM 澄清內容當 spec 原文、把相隔數列的表格列拼接成連續引文、markdown 粗體位置誤植。這是最常見的問題類型
2. **環境依賴假設未揭露**（UPDATEPACK、CASHOUT）：precondition 隱含「測試環境已有某種站台／帳號」卻不標 assumptions，`gates.py` 的 `is_exploratory` 只看 assumptions 欄位，結構性檢查抓不到
3. **覆蓋縮減未結構化記載**（BONUSCCY-002）：requirement statement 列了六種類型，AC 用「等」字概括，草稿只做兩種，其餘既無 TC 也無 `uncovered_with_reason`
4. **局部修正沒同步 report**（BONUSCCY-002、DAILYREPORT）：補了 TC 但 `coverage_matrix`／`technique_summary` 沒更新，或改了 expected_result 沒理順 precondition 造成自相矛盾——**這類問題我自己的手動修正也犯過**

---

## 5. Validator 抓到的問題類型

| 類型 | 次數 | 代表案例 |
|---|---|---|
| quote 非逐字／拼接／來源混淆 | 6+ | PLATFORMRULE 相隔 11 列拼接、BONUSCCY-001 把 CLR 當原文 |
| 環境／機制假設未揭露 | 4 | UPDATEPACK 機台場館 fixture、DAILYREPORT 日結時間變更生效 |
| 邏輯自相矛盾 | 2 | DAILYREPORT 場次數公式含逾時結束卻引用 CLR 說不會出現 |
| 覆蓋縮減未記載 | 2 | BONUSCCY-002 REQ-006 四種紅利類型缺測 |
| report 與 draft 不同步 | 2 | BONUSCCY-002 coverage_matrix 漏兩條 |
| 對系統結構規則的**錯誤**技術主張 | 1 | BONUSCCY-001 宣稱 exploratory 計數與 design_techniques 相關（實際只看 assumptions） |
| RequirementModel 資料錯誤（交叉比對階段由我抓到，非 Validator） | 1 | SITELIST CLR-011 與既有 TC-063 矛盾 |

**Validator 本身的誤判**：BONUSCCY-002 第二輪把「推薦獎勵」列為缺口，實際已由 REQ-009 的 TC 覆蓋（RequirementModel 重複列舉造成的表面缺口）；BONUSCCY-001 的 `is_exploratory` 技術主張錯誤。兩次都是「對 RequirementModel／runtime 結構的判斷」而非「對業務內容的判斷」——這是為什麼後來規定 Validator 必須附 `gates.py`，且我對 Validator 的結構性主張一律自己查證原始碼。

---

## 6. 跨 spec 共通教訓

1. **交叉比對的價值不在採用率，在「揪出兩邊都沒發現的東西」**：SITELIST 的 RequirementModel 資料錯誤、BONUSCCY-002「REQ-006 是 high risk 但 Phase 2 五條全是 happy path、零 non-happy 覆蓋」、UPDATEPACK「Phase 2 一句話同時斷言兩件事但 steps 沒有比對依據」——這些都不是 Phase 2 或 Phase 3 單獨看得出來的。
2. **一句話涵蓋兩個斷言的 TC，拆開才知道原本驗證強度不足**：不能只看「兩邊都有 TC 覆蓋同一個 AC」，要看 steps 是否給了可重複執行、有鑑別力的比對依據。
3. **對 Validator 的結構性技術主張，一律查 `gates.py` 原始碼再動手**：兩次誤判都在這一類。業務內容的判斷可信，系統規則的判斷要驗證。
4. **`clarification apply` 不會把答案寫回 RequirementModel**：這是 DAILYREPORT 波次揪出的系統性問題——25 張已 apply 的 CLR 裡 18 張的答案從沒進 RM，Test Designer 只讀 RM，所以把已解決的疑義當成 ambiguity。已全數補寫，但往後每 apply 一張 CLR 都要同步檢查 RM。
5. **核准動作可能發生在 session 之外，且執行者不一定看過分析**：PLATFORMRULE 的整批 approve 不是使用者看過 per-item 建議後的選擇，而是指揮台操作與 session 分析脫節。「已核准」≠「已依建議核准」，數量異常要主動查證。
6. **`is_exploratory` 只看 assumptions 欄位，所以「0 條 exploratory」的宣稱值得主動質疑**：UPDATEPACK 的 Test Designer 宣稱 0 條，實際有一條依賴未驗證的環境事實——結構性 gate 抓不到這種，要靠 Validator 被明確要求去質疑。
7. **樣本數小時 exploratory 比例會失真**：ARCADE 7 條中 5 條 exploratory 觸發 50% 熔斷，但那 5 條全是同一類天然環境依賴，不是品質問題。熔斷的 summary 文字是模板（「Spec 缺錯誤契約」），不代表逐條分析結論。
8. **我自己的手動修正也需要獨立審查**：DAILYREPORT 我改 expected_result 只補了 CLR 引用句，沒理順 precondition 與公式，造成自相矛盾，被第一輪 Validator 抓出。獨立審查機制不只針對 agent，也針對人。

---

## 7. 對 MODEL-ROUTING-POLICY §3「Phase 3 穩定」判斷的數據依據

Policy §3 定義「Phase 3 穩定」為「同一類真實 Spec 跑過 2～3 份」，屆時可考慮：三次 FAIL 由 Runtime 升一次 Opus、agent md 寫 default model。本系列的數據：

- **跑過 13 份**，遠超 2～3 份門檻
- **全程 Sonnet**（含 Test Designer subagent 與獨立 Validator subagent），唯一一次 Opus 例外是 SITELIST 第 4 輪（三輪 FAIL 後依 §2.2 第 2 條升級一次），結果該輪仍 FAIL（問題根源是 RequirementModel 資料錯誤，不是模型能力）
- **max_validation_iterations=3 觸發 HUMAN_OVERRIDE 共 3 次**（MEMBER、SITELIST 多次、BONUSCCY-002），每次都是「再給一次迭代」，沒有一次是靠 override 強制通過
- **後 4 份（真 subagent）全部首輪 G-DESIGN PASS**，獨立審查 1～2 輪即 PASS

**結論**：可以進入 Policy §3 的「Phase 3 穩定」階段。但 SITELIST 的 Opus 升級案例顯示，三次 FAIL 的根因多半是 spec／RM 資料問題而非模型能力，「Runtime 自動升一次 Opus」的價值存疑，建議先保留 Human 切模型。

---

## 8. Runtime 層級的系統性發現（已處理或已記錄）

| 發現 | 處理 |
|---|---|
| `clarification apply` 不回寫 RequirementModel | 18 張 CLR 答案已補寫進 RM（`tools/manual-runs/batch_18_clr_apply.py`） |
| T3 FAIL route back 時 T2 的 `output_artifact_ids` 不清空，直接 `gate` 會拿舊 artifact 推進 | 已固定為測試契約（`tests/test_wf_x_gate_rejection_branches.py::test_62`） |
| `gates.py` 9 條拒絕分支從未被測試觸發 | 已補測，gates.py 覆蓋 96%→100% |
| 外部指揮台 approve 與 session 脫節 | 核准流程分級規則；`.warroom/recommendations/` 建議機制 |
| Validator 對結構規則的技術誤判 | 獨立 Validator 一律附 `gates.py` |
| SPEC-DAILYREPORT-001 v0.1 缺「注單數」欄位定義 | 擱置，記錄於 memory 待統一處理 |
| design_techniques 出現 `scenario` 但 schema 無 enum | 記錄於 audit advisory，待決定 |
