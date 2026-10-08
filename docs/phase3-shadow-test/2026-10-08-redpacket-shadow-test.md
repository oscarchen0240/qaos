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

1. Spec Analyst 自行編 REQ ID 未經計數器，G-SPEC 落地不檢查。
2. `store.save` 在 agent 環境丟 `NoExecutorContext`，agent 定義未更新。
3. G-DESIGN 抓不到未宣告的隱含依賴；decision_refs 無法跨需求宣告。
4. Validator 合約「未被 RESOLVE_AMBIGUITY 覆蓋的 assumption → blocker」與需求 A §3.6 衝突。
5. 派給 Validator 的 Draft 未剝除 design_rationale。
6. Test Designer agent 定義仍寫「自己 submit／gate」。
7. `bin/qaos id` 不加 `--new-request` 會回傳上次配發的同一 ID，有覆寫 artifact 風險。
8. G-TVAL 範圍檢查不看 `expected_result_spec_reference`，該欄位無 hash。
9. 自動開 CLR 後 `clarifications/index.md` 未重建。
10. TC Risk Reviewer 的 applies_to_areas 未含 REDPACKET（涉入帳、餘額、稽核）。
11. 派發包決議快照納入閉包內其他 spec 的全部 CLR（含舊版本）。

## RM 待修（CLR 回覆時以 revision 一併處理）

- AC-REDPACKET-0191 算錯：依 spec 第 123 行應為期望金額 19、預算約可發放 263（RM 寫 18.4／271）。
- known_rules 漏收第 56、87、106 行。
- REQ-011 缺「日結時間修改後何時生效」決策點。
- REQ-027／028「洗分進行中」與 ARCADE 單階段洗分的潛在衝突。
- 匯入 proto 作為引用來源，處理 6 張 proto 類 document_request。
