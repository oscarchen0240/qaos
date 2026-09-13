# CLR-PLATFORMRULE-001：「站長＝最高權限」的定義是否仍有效？三份 spec 的權限層級互相矛盾

- 產品 / 功能：ba-admin / PLATFORMRULE
- 規格：SPEC-PLATFORMRULE-001 v0.1
- 相關需求：—
- 提出者：oscarchen@blockaction.tech（2026-09-13）
- 狀態：APPLIED

## 背景
前言與通用規則_spec_v01 寫站長=最高權限；站台列表_spec_v04 為 Admin/站長兩層；機台場館平台規則_spec_v01 為 Admin/站長/操作員三層。延伸：ZZAA00264（站長，指派在 admin）可自由選取上層站台是否為 bug？

## 可能的解讀（請勾選或補充）
- [ ] 以前言為準：站長最高
- [ ] 以功能 spec 三層模型為準：管理員 > 站長 > 操作員

## 若未回答的影響
影響站台列表 / 平台規則所有權限相關 TC 的 expected

## PM 回覆
以功能 spec 三層模型為準：管理員（最高）＞站長＞操作員。原則：可見範圍由所屬站台決定、權限層級由角色決定，兩者分開。ZZAA00264 案確認為 bug（站長不應有自由選取上層站台的管理員專屬能力）。前言「站長＝最高權限」已過時。
— PM，2026-09-13，落地方式：requirement_clarified
