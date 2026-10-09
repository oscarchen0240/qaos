# CLR-SITELIST-019：新站台建立時，是否自動於該站台自己的「鏈上錢包管理」啟用核心貨幣對應幣別、且不依賴根站台 admin 的鏈上錢包管理狀態。CLR-SITELIST-012 rev 0（針對 v0.4，修正 CLR-SITELIST-011）答「會自動啟用、不依賴上層」，但 v0.7 原文未載，且答案 basis 不同（X16），需以 applicability 綁定到 v0.7 或請 PM 補入 spec

- 產品 / 功能：ba-admin / SITELIST
- 規格：SPEC-SITELIST-001 v0.7  §§站台類型與機台專屬欄位 L77 + §主站台 L118-119 + §業務規則與驗證/站台類型隨主站台 L228、根站台不參與繼承 L225
- 相關需求：REQ-SITELIST-002
- 提出者：agent-spec-analyst（2026-10-09）
- 狀態：OPEN

## 背景
REQ-SITELIST-002：站台類型於主站台（根站台 admin 底下第一層）選定，其下所有子站台一律與主站台同類型、不可個別選擇（新增視窗唯讀跟隨主站台）；根站台 admin 不參與繼承鏈，故於根站台底下新增主站台時可自由選擇線上或機台，核心貨幣依所選類型連動。以下兩點為前版依 CLR 記載、v0.7 原文未載的行為，本版列為待綁定決策點（見 Q02、Q03）：子站台以 API 帶入與上層不同類型時後端拒絕（CLR-SITELIST-001）；新站台建立時自動於該站台自己的鏈上錢包管理啟用對應幣別、不依賴根站台 admin 的設定（CLR-SITELIST-012，修正 CLR-SITELIST-011）。

## 可能的解讀（請勾選或補充）
- （無預設選項，請自由回答）

## 若未回答的影響
依賴此決策點的斷言只能 exploratory，或不能引用衝突的任何一側

## 已查文件
- SPEC-SITELIST-001 v0.7（c6001a294a5a…）
- SPEC-ARCADE-001 v0.8（7cbe9808a641…）
- SPEC-ROLEPERM-001 v0.2（d47f01840f02…）
- SPEC-ADMINSYS-001 v0.3（6d22cafaa1ce…）

## 已確定的部分
- SPEC-SITELIST-001 v0.7 §核心貨幣（第 96 行）：「主站台建立後，核心貨幣不可修改」

## 還需決定的事
新站台建立時，是否自動於該站台自己的「鏈上錢包管理」啟用核心貨幣對應幣別、且不依賴根站台 admin 的鏈上錢包管理狀態。CLR-SITELIST-012 rev 0（針對 v0.4，修正 CLR-SITELIST-011）答「會自動啟用、不依賴上層」，但 v0.7 原文未載，且答案 basis 不同（X16），需以 applicability 綁定到 v0.7 或請 PM 補入 spec
- 細節：wallet_auto_enable_on_create

## PM 回覆
（待回覆）

