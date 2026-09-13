# intake — 收件匣（2026-09-13）

原始文件的分類與去向。**正式資料在各目錄；本目錄只是原檔歸檔與追溯。**

| 類型 | 原始檔 | 去向 |
|---|---|---|
| **Spec（開發包 ②①③④⑤⑥⑦ + 正本 + 通用）** | `實體機台開發包_20260904/spec/*.md`（11） | `specs/ba-admin/<AREA>/SPEC-<AREA>-001/v<ver>.md`（v07→0.7、v04→0.4、v01→0.1、v02→0.2）；proto 在同目錄 `attachments/`；README 與開發總清單在 `package-20260904/` |
| **Spec（紅利幣別，PM 文件）** | `17-給QA的說明.md`、`18-紅利幣別盤點.md`、`20-紅利調整說明.md` | `specs/ba-admin/BONUSCCY/SPEC-BONUSCCY-001/002/003 v1.0` |
| **Bug 單（md ×3）** | 場館日結報表欄位缺失、洗分出金核實角標、系統使用者列表查無帳號 | `bugs/` 原檔；`testcases/manual/MAN-20260913-009~011`（WF-B / WF-D 輸入）；全文 Evidence |
| **Bug 單（html ×5，含 zip 內 3）** | ZZAA00264 上層站台、上層站台選單異常、子站台類型核心貨幣、不支援 TWD 遊戲商、畫面管理 OFF | `bugs/` 原檔；`MAN-20260913-012~016`；內嵌截圖抽成 `evidence/bug-intake-20260913/EVD-*.png`（27 張） |
| **PM 決策** | `待PM確認_站長最高權限定義疑問_精簡版.html`（已結案） | `pm-decisions/` 原檔；`clarifications/ba-admin/PLATFORMRULE/CLR-PLATFORMRULE-001`（ANSWERED，PM 回答已回填） |
| **RD 修復回報** | `0904files_修復回報.md`、`2026-09-04.md`、`2026-09-04_1500後.md` | `rd-reports/`。對應 MAN-012~014 的 bug 已「已修復待驗」；Phase 3 走 WF-B 開正式 Bug 後由 Human 推 RESOLVED → 驗證 → VERIFIED |
| **QA 筆記** | `紅利幣別改動_QA整理.md`、`機台與多幣別站台_測試checklist.md`、`機台測試checklist(.html/_v02.html)` | `qa-notes/`。checklist 為人工測試計畫，日後可轉 ManualTestRecord |
| **測試環境** | `機台開發用測試頁.md`（含 test 環境測試帳密） | `docs/environments/ba-admin-arcade-test.md` |
| Brief | `QA_Agent_Operating_System_Master_Architecture.md` | 已處理（Phase 1） |

## 待辦（依架構流程）
- 各 SPEC 尚未 Spec Analysis（除本輪執行者）。Phase 3 有 Agent 後批次跑 WF-A。
- ~~`MAN-015`~~ → `CLR-SCREENMGMT-001` PM 已答：人工在 prod 關閉，系統不過濾 → **不是 bug**，結案。
- ~~`MAN-016`~~ → `CLR-SCREENMGMT-002` PM 已答：OFF 應全部隱藏 → **是 bug**；Requirement 來源草稿 `specs/_drafts/SPEC-SCREENMGMT-001-v1.0.md`，PM 確認匯入後走 WF-A（1 條 REQ）→ WF-B。
- `CLR-DAILYREPORT-001~006` PM 已答 → 整理成 `specs/_drafts/SPEC-DAILYREPORT-001-v0.2-addendum.md`，待 Spec 作者合入後匯入 v0.2 → WF-C。
- `MAN-009`（場館日結報表欄位缺失）→ 已拆成兩個 WF-B run（RUN-002 場次數、RUN-003 開始時間/時長），待 Bug Validator 與 Human OPEN_BUG。
- `MAN-010`（洗分出金核實角標）、`MAN-011`（系統使用者列表）、`MAN-012~014`（站台列表三張）→ 對應 SPEC 需先 Spec Analysis（CASHOUT / PLATFORMRULE / SITELIST）後才能走 WF-B。
- RD 回報中的「新增功能（操作員角色 role-600、待審通知紅點）」可能對應 spec 變更 → 確認是否有新版 spec（WF-C）。

重跑：`python3 tools/intake_downloads_20260913.py`（已匯入者自動跳過）。

- `MAN-20260914-001`（逾時結束後不可再遊玩）→ WF-D RUN-20260914-001。Validator 排除了「期初餘額承接」「注單歸屬新場次」兩個不在紀錄／本 Spec 的行為；要驗證它們需先對 `SPEC-CASHFLOW-001`（開發包③）跑 WF-A，把場次規則納入 Requirement。
