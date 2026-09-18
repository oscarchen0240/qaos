# CLR-SITELIST-010：REQ-SITELIST-002「子站台強制跟隨主站台型別」規則，是否對根層站台（無上層站台，隱含上層為 admin）有例外？

- 產品 / 功能：ba-admin / SITELIST
- 規格：SPEC-SITELIST-001 v0.4
- 相關需求：REQ-SITELIST-002
- 提出者：oscarchen@blockaction.tech（2026-09-17）
- 狀態：APPLIED

## 背景
spec.md 原文僅載一般規則「子站台一律與主站台同類型、不可個別選擇」，未明文提及根層/admin例外；RequirementModel 先前的確認記錄有時序矛盾（記錄時間早於所述確認日期）且缺乏CLR交叉引用，Phase 3影子測試的獨立Validator審查連續兩輪認定此規則來源不可信，要求正式CLR記錄

## 可能的解讀（請勾選或補充）
- （無預設選項，請自由回答）

## 若未回答的影響
若無正式CLR記錄，REQ-SITELIST-002/AC-SITELIST-0023的真實性與稽核強度低於本文件其他確認案例，Test Designer與Validator皆無法判斷此規則是否可信

## PM 回覆
admin 例外規則為 PM 最終決定，非資料錯誤或臆測：根層站台（無上層站台）建立時，型別可自由選擇（機台或線上），核心貨幣依所選類型連動建立，不受REQ-SITELIST-002子站台強制跟隨規則約束。此為PM已定案且已開發完成上線的產品行為，非待定或實驗性設計。spec.md原文尚未反映此例外，屬spec文件落後於實際已上線行為的已知落差。
— PM（經 Oscar Chen 於 2026-09-17 對話直接確認），2026-09-17，落地方式：requirement_clarified
