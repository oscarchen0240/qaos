# CLR-CASHOUT-001：TC-DRAFT-01M2R6NEJ7BJH8707E9B1MM8SH / ...VDDAW6 / ...YDRNZ（AC-CASHOUT-0251/0252/0291）的assumption標註『操作員角色的權限範圍(含是否限定單一場館)定義於開發包⑥PLATFORMRULE，該包尚未完成Phase 3測試設計』，此權限規則本身（操作員無權切換場館）是否為過去已規劃定案的既有設計，而非待PLATFORMRULE補完才會定義的規則？

- 產品 / 功能：ba-admin / CASHOUT
- 規格：SPEC-CASHOUT-001 v1.0
- 相關需求：REQ-CASHOUT-025
- 提出者：oscarchen@blockaction.tech（2026-09-17）
- 狀態：APPLIED

## 背景
REQ-CASHOUT-025 statement已載明『操作員完全不具備切換站台的權限...已由Oscar 2026-09-14確認』，但對應TC的assumption仍寫成規則定義於PLATFORMRULE、尚未完成，兩者用詞不一致，需再次向PM確認此規則的定案狀態，以便正確收斂TC的assumption揭露範圍

## 可能的解讀（請勾選或補充）
- （無預設選項，請自由回答）

## 若未回答的影響
若確認為既有定案規則，TC的assumption應收斂為只揭露『測試環境是否已備妥符合此限制的操作員帳號』這個環境設定事實，不應暗示規則本身待PLATFORMRULE補完才算數

## PM 回覆
操作員無權限切換至其他場館，切換場館的設定在後台管理員系統，此權限只有站長跟admin有權限，這是過去就規劃好的權限事宜
— oscarchen@blockaction.tech，2026-09-17，落地方式：requirement_clarified
