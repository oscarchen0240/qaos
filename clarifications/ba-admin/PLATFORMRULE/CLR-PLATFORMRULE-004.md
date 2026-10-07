# CLR-PLATFORMRULE-004：REQ-PLATFORMRULE-011 不符合時系統應如何反應？（Spec 未定義拒絕行為）

- 產品 / 功能：ba-admin / PLATFORMRULE
- 規格：SPEC-PLATFORMRULE-001 v0.2  §§機台場館的後台選單（拒絕行為處理依 CLR-PLATFORMRULE-002 PM 定案）
- 相關需求：REQ-PLATFORMRULE-011
- 提出者：agent-spec-analyst（2026-10-02）
- 狀態：WITHDRAWN

## 背景
選單顯示規則應與排除規則同一來源設定；未來某項功能對機台帳號恢復適用時，對應頁面隨之恢復顯示，不應各自寫死
此為架構/實作方式的要求（集中政策層、不得各自硬編碼），非可獨立驗證的使用者可觀察行為；目前沒有任何排除項目被解除。依 CLR-PLATFORMRULE-002 PM 定案（2026-09-14；v0.2 原文未載）：維持 defined=false，Test Design 不強行湊負向 TC，於 TestDesignReport 註記「架構要求，待未來有排除項目實際解除時再補測試」；未來驗證走「先解除某排除項目→驗證對應頁面恢復顯示」的真實案例

## 可能的解讀（請勾選或補充）
- （無預設選項，請自由回答）

## 若未回答的影響
Test Designer 只能以 exploratory（假設）方式撰寫此需求的負向案例，expected 需 Human 確認

## PM 回覆
（待回覆）

