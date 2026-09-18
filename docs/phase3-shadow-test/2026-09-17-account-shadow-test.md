# Phase 3 影子測試紀錄：qaos-test-designer × SPEC-ACCOUNT-001

- **日期**：2026-09-17
- **Run**：RUN-20260916-008（spec-to-testcase，spec_id=SPEC-ACCOUNT-001, spec_version=0.1）—— COMPLETED
- **目的**：與 SITELIST 同步派工的 Phase 3 影子測試。ACCOUNT 是開發包①（帳號與機台管理，創建帳號的所有功能＋機台管理與機台憑證，不含任何金流）。Phase 2 已有 57 條 ACTIVE TestCase，Test Designer 獨立設計出 64 條 TestCaseDraft。
- **結果**：G-DESIGN 兩輪後 PASS，G-TVAL **第一輪即 PASS**（本專案至今唯一一次首輪直接過關的 Phase 3 影子測試，跟同批的 SITELIST 十輪、CASHFLOW 多輪形成強烈對比）。

---

## 設計階段（T2）

64 條 TC，覆蓋 31/32 requirement、65/67 AC。第一次 G-DESIGN 因兩個結構問題 FAIL（REQ-ACCOUNT-028 高風險無 non-happy TC 未走豁免流程；一條 REQ-016 的 TC 技巧標籤跟 rejection_contract 規則衝突），修正後第二次 PASS。

**未覆蓋項目**（皆結構化記載）：
- REQ-ACCOUNT-020：機台憑證唯一性驗證需要開發包③的憑證檢查 API，該 API 尚不存在（spec.md 明文「在此之前驗證憑證的 API 尚不存在」）
- AC-ACCOUNT-0282/0283（REQ-ACCOUNT-028）：存提款次數/金額計算需要真實機台交易（開分/入金/洗分/出金），完全屬開發包③範圍

## 獨立驗證階段（T3）

**唯一一輪，直接 PASS**。獨立 Validator 用程式化交叉比對（traceability graph、technique-tag 分布、quote-vs-spec 逐字比對、金流關鍵字掃描）驗證：
- 兩個 `NO_REJECTION_CONTRACT:` 豁免（REQ-020/REQ-028）皆對照 spec.md 原文確認成立
- 全部 64 條 TC 對「開分/入金/洗分/出金/金流/注單/日結/核實」關鍵字掃描零命中，確認沒有誤觸金流範圍
- `security_rule` 技巧只精準用在 3 條 `type: security` 的 requirement（010/011/017）
- `technique_summary` 逐條核對完全一致

只有 minor 等級的建議（操作員測試帳號是否存在的步驟措辭、coverage_matrix 結構化程度、design_rationale 略嫌制式、一條 TC 掛靠 AC 略鬆散），無 blocker/major。

## Phase 2 × Phase 3 交叉比對

67 條 AC 中：
- **64 條**：兩邊都覆蓋，其中 60 條 1:1 對應
- **只有 Phase2 覆蓋（3 條）**：AC-ACCOUNT-0201、0282、0283——皆為需要開發包③（CASHFLOW）才能真正執行的案例，Phase2 已先寫好當「待未來可執行」的文件性 TC（其中 TC-ACCOUNT-036 有正式標記 assumption 說明目前無法執行、需等待開發包③，已由 APR-0017 核准；TC-ACCOUNT-047/048 未加註明說明但內容同樣依賴開發包③）。Phase3 判斷「還不能測就不寫」，兩邊策略不同、皆合理，維持 Phase2 現狀
- **4 條 TC 數量不同（Phase3=2, Phase2=1）**：逐條讀完斷言後確認，其中 3 條（AC-0091 機台不可事後綁定、AC-0193 重置憑證取消路徑、AC-0161 重設連結重複使用）是 Phase3 真的補了 Phase2 沒想到的純新增負向案例；1 條（AC-0012）是 Phase3 拆分後新增了跟 Phase2 不同層面但互補的斷言（Phase2 測後端資料模型「同一份會員資料無獨立資料表」，Phase3 測前台選單入口「沒有獨立管理選單」），兩邊互補保留

## 最終處置

依 ADR-007 風險分級（ACCOUNT 不涉金流、屬低風險），這 4 條新增案例**不走完整的獨立 Validator 重審流程**——它們已經是原始 T3 那輪（PASS、無 blocker/major）的一部分，直接走輕量方式：用 `bin/qaos approve APR-0105 --decision reject --per-item <id>:approve`（僅對這 4 條指定 approve，其餘 60 條維持 reject 預設）核准加入 Registry，並在核准後獨立查驗 Registry 狀態（確認恰好 4 條變 ACTIVE、60 條維持非 ACTIVE），避免重演 CASHFLOW 那次 `--per-item` 誤用事故。

**結果**：Phase2 既有 57 條 ACTIVE TC + 新增 4 條（TC-ACCOUNT-059、075、093、101）= 61 條 ACTIVE。其餘 60 條 Phase3 草稿不採用。

## 與 CASHFLOW/SITELIST 的對比

ACCOUNT 是本輪三份 spec 中過程最平順的一次：無規則爭議、無 CLR 需求、Validator 首輪即 PASS、交叉比對落差全部是單純的「純新增負向案例」而非規則分歧或內容誤判。這佐證了 ADR-007 風險分級的判斷依據——低風險/不涉金流的功能區，Phase 3 agent 設計品質穩定性明顯高於高風險/金流相關功能區（CASHFLOW、SITELIST 的 admin 例外規則）。
