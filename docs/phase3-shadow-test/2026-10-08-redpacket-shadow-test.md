# Phase 3 影子測試紀錄：需求 A 上線後首次 spec-to-testcase × SPEC-REDPACKET-001

- **日期**：2026-10-08
- **Run**：RUN-20261008-001（spec-to-testcase，spec_id=SPEC-REDPACKET-001, spec_version=0.1）—— COMPLETED
- **目的**：需求 A（引用宣告、派發包、決策點、路由表、executor）2026-10-08 部署後第一次實際產 TC，同時驗收新流程。
- **結果**：G-SPEC 首輪 PASS（33 需求、103 AC、70 決策點，自動開 CLR-REDPACKET-001～025）；G-DESIGN 三輪皆 PASS；G-TVAL 第 1、2 輪 FAIL、第 3 輪 PASS。APR-0194 核准 72 條、逐項退回 4 條 exploratory，Registry 新增 **TC-REDPACKET-001～076 中 72 條 ACTIVE**。

---

## 前置：spec 匯入與引用宣告

- 來源：紅包開發包_20260929_r2 / `spec/紅包_spec_v01.md`，匯入為 SPEC-REDPACKET-001@0.1（新 area REDPACKET）。
- 引用只能指向已匯入版本，因此另匯入：SPEC-SYSADMIN-001@0.1（系統管理）、SPEC-REPORTS-001@0.1（各式報表），兩者 analyze（未寫政策欄位，保留日後補 reference_only 的可能）；開發包版前言與通用規則匯入為 SPEC-COMMON-001@0.2（多管理員／操作員內部說明區塊）。
- 引用宣告 decl_rev 7：normative SYSADMIN@0.1、REPORTS@0.1、SITELIST@0.6、PLATFORMRULE@0.2、DAILYREPORT@0.2、ARCADE@0.7；informative COMMON@0.2。開發包③⑧未附，不宣告。
- 疏漏：開發包內其實附有 `proto/紅包_proto_v01.html`（spec 寫 `protos/…`），未當引用來源處理，導致 6 張 proto 類 document_request。

## T1 Spec Analyst／G-SPEC

- 33 需求全部 ACTIVE（無 critical，不建 RESOLVE_AMBIGUITY）；決策點 E1 45 個，未定 25 個（E4 16：major 5／minor 11；E3 9：major 1／minor 8）。
- G-SPEC PASS 後 runtime 依路由表自動開 25 張 CLR：spec_question 16、document_request 9。依路由 R4/R6，minor／major 不擋流程，依賴的斷言只能 exploratory。
- Spec Analyst 自行編 REQ-REDPACKET-001～033，未經 `bin/qaos id`；送出前由 Supervisor 補配 33 次讓計數器對齊。

## T2 ⇄ T3 三輪

| 輪 | G-DESIGN | G-TVAL | 主要問題 |
|---|---|---|---|
| iter0 | PASS（75 條） | FAIL 4 major／9 minor | TC 隱含依賴 E3/E4 未定事項卻寫成確定斷言（取整、機台視角欄位、過渡期出金） |
| iter1 | PASS（76 條） | FAIL 3 major／9 minor | 13 條全修；但修正衍生新 major（結算鍵提示），另抓到 iter0 漏報的「日結時間修改何時生效」 |
| iter2 | PASS（76 條） | **PASS** 0 major／1 minor | 原則改為：依賴未定事項的斷言一律 exploratory 或刪除，不為修補新增確定斷言 |

## 核准（APR-0194）

- approve 72 條 grounded；per-item reject TC-REDPACKET-011、043、067、069（exploratory，假設待 CLR-REDPACKET-002／010／022 回覆，不由核准者代為確認）。
- 核准後 33／33 需求仍有 ACTIVE TC；AC 覆蓋 100／103，缺 AC-0224、0282、0283（僅由被退回的 exploratory 覆蓋），待 CLR 回覆後補建。

## 關鍵教訓

1. **新關卡有效，但最難的錯在機械檢查之外**：三輪 major 全是「斷言隱含依賴未定事項、未宣告 decision_refs」，G-DESIGN 只檢查已宣告的 decision_refs，靠 Validator 語意審查才抓到。跨需求依賴無法宣告，只能改條件式或只記錄。
2. **修補時不要新增確定斷言**：iter1 為修 minor 加了一句確定斷言，反而製造新 major。iter2 改採「未定就 exploratory 或刪除」後一次通過。
3. **CLR 不擋流程是設計取捨**：25 張 minor／major CLR 開出後流程照走，72 條確定 TC 先進 Registry；代價是 CLR 回覆後要走 apply → RM revision → TC 修訂收斂 exploratory 與補覆蓋。

## 待辦（程式／規則缺陷，走 MR，本次未修）

1. Spec Analyst 自行編 REQ ID 未經計數器，G-SPEC 落地不檢查。（已修：分支 qaos/gate-integrity）
2. `store.save` 在 agent 環境丟 `NoExecutorContext`，agent 定義未更新。
3. G-DESIGN 抓不到未宣告的隱含依賴；decision_refs 無法跨需求宣告。
4. Validator 合約「未被 RESOLVE_AMBIGUITY 覆蓋的 assumption → blocker」與需求 A §3.6 衝突。
5. 派給 Validator 的 Draft 未剝除 design_rationale。（已修：分支 qaos/gate-integrity）
6. Test Designer agent 定義仍寫「自己 submit／gate」。
7. `bin/qaos id` 不加 `--new-request` 會回傳上次配發的同一 ID，有覆寫 artifact 風險。
8. G-TVAL 範圍檢查不看 `expected_result_spec_reference`，該欄位無 hash。（已修：分支 qaos/gate-integrity）
9. 自動開 CLR 後 `clarifications/index.md` 未重建。（已修：分支 qaos/gate-integrity）
10. TC Risk Reviewer 的 applies_to_areas 未含 REDPACKET（涉入帳、餘額、稽核）。
11. 派發包決議快照納入閉包內其他 spec 的全部 CLR（含舊版本）。

## RM 待修（CLR 回覆時以 revision 一併處理）

- AC-REDPACKET-0191 算錯：依 spec 第 123 行應為期望金額 19、預算約可發放 263（RM 寫 18.4／271）。
- known_rules 漏收第 56、87、106 行。
- REQ-011 缺「日結時間修改後何時生效」決策點。
- REQ-027／028「洗分進行中」與 ARCADE 單階段洗分的潛在衝突。
- 匯入 proto 作為引用來源，處理 6 張 proto 類 document_request。

---

# 續：proto／開發包③ 引用與同版本 CIA（RUN-20261008-003）

- **Run**：RUN-20261008-003（spec-change-impact，同版本 CIA：SPEC-REDPACKET-001 0.1，R001 → R002，reason=declaration_changed）—— COMPLETED
- **結果**：G-SPEC、G-IMPACT、G-DESIGN、G-TVAL、G-COMPARE 皆首輪 PASS（G-TVAL 0 major）。APR-0195 核准 15 條改版（v2）、17 條新增（TC-REDPACKET-077～093），Registry **89 條 ACTIVE**，R002 的 123 個 AC 全有案例掛載（AC-0286 僅部分覆蓋）。

## 引用來源補齊

- 外部分析指出 6 張「缺互動原型」的 document_request 不成立：proto 就在開發包 `proto/`。匯入為 **SPEC-REDPACKET-002@0.1**（reference_only，HTML 原文存為 v0.1.md），Oscar 決定 **normative**（proto 有定義的細節視為規則依據）；decl_rev 8。CLR-002、012、013、014、021、024 以 `clarification fulfill` 補件，CLR-017 以 `waive-item` 豁免（目標 spec L252–257 已定義），7 張 APPLIED。
- 第一次重新分析（RUN-20261008-002）時發現**開發包③ 已匯入為 SPEC-CASHFLOW-001** 但未宣告。為避免 CLR 重開兩輪，在 G-SPEC 前取消 002、宣告 CASHFLOW 為 normative（decl_rev 9）後重開 003。

## R002 重新分析

- 33 需求、AC 103 → 123、決策點 70 → 84；ID 全數沿用。原 25 個未定：3 個全定（活動狀態、試算格式、差異百分比，依 proto）、9 個拆分（已定部分另立 E1 決策點）、其餘仍未定。
- 修正 R001 已知問題：AC-0191 改 19／263、補 known_rules 第 56／87／106 行、新增 REQ-011/Q04（日結時間修改生效時點，E4）；洗分判定與 ARCADE 可並存（非衝突）。
- 新衝突 2 個（E2 major，不擋流程）：REQ-022/Q04（spec L222 vs proto 規則篩選顯示條件）、REQ-028/Q04（spec「Admin 可手動取消待確認出金」vs 已落地 CLR-CASHFLOW-004「無手動取消」）。
- CLR：因 basis 改變（decl_rev、閉包），issue key 全部不同，新開 CLR-REDPACKET-026～050（25 張，17 張以 prior_version 指回舊單）；舊 OPEN 18 張經 Oscar 確認後撤回（附對應新單編號或「已由 proto 定義」）。

## 本輪經驗

1. **引用宣告要一次補齊再分析**：每改一次宣告，basis 就變，所有未決 CLR 會以新單重開、舊單須人工撤回。匯入新 spec 前應先盤點開發包附檔與 Registry 既有 spec（含別名，如「開發包③」＝CASHFLOW）。
2. **Designer 依前一輪教訓（未定事項一律 exploratory 或刪除）後，G-TVAL 首輪即 0 major**；Validator 逐一核對 25 個非 E1 決策點無隱含依賴。
3. **CIA 只看 AC／預期，漏掉共用前置條件**：57 條 unaffected 的「逐一取消排程直到列表沒有」在 R002（已結束／已取消會留在列表）下不可執行。Oscar 決定延到下一次 decision_applied CIA 一併修正；final 檔已加執行提示。
4. Change Impact Analyst 曾把 envelope status 自填 VALID、created_at 手填未來時間，submit 正確拒絕；以新 ID 重產。

## 新增待辦（程式／規則，走 MR）

12. 同版本 CIA 宣告改變時，所有未決 CLR 以新單重開、舊單不會自動結案（設計行為，但造成大量重複單；可考慮自動標記被取代）。
13. G-IMPACT／CIA 不檢查共用前置條件受需求變更的影響。
14. `run new`、`tc-export`、`tc-final` 等以參數判定重送：參數相同時只回放舊輸出（含過時狀態，如 run 已 CANCELLED 仍顯示 RUNNING）、不重新產生；匯出類指令資料變更後必須加 `--new-request`。
15. `bin/qaos tc-final` 產出的 html 缺樣式（只有 `body{font-family:sans-serif}`），與既有 final 版不一致。
16. agent 可自填 envelope status 與 created_at（submit 有擋 status，但 created_at 未驗）。（已修：分支 qaos/gate-integrity）

## 待處理

- CLR-REDPACKET-026～050（25 張 OPEN）待 PM 回覆；衝突單 038、047 待裁決（047 牽涉 CASHFLOW／TXLOG）。
- 回覆並 apply 後走 decision_applied 同版本 CIA，屆時一併修正 57 條前置條件、補 AC-0286「恢復可開啟」。
- TC-REDPACKET-011、043、067、069 為 DRAFT（無 active 版本）；067、069 已被 TC-088、089 取代（AC-0282／0287、0283／0285 的確定版），011、043 待 CLR-027、035。
