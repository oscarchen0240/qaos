# 需求 A 驗收紀錄

依 `requirement-a-final.md` §0.2 分階段記錄：每條 AC 的驗收階段、測試、執行時的 commit 與結果。
早期階段只驗收能獨立驗證的部分；還不能執行的標「待 Pn」，於 P6 結清。

## P1：executor 基礎設施

- **執行 commit**：`99b384d4b1abf5c938588bd98e973cdf43d8f742`（分支 `qaos/requirement-a`；含 P1 程式碼審查 P1-01～P1-06、再審查 P1R2-01～04、局部複驗 P1R3-01～02、殘留清理複驗 P1R4-01～03、第二次複驗 P1R5-01 的修正，以及附錄 A 4-17 定案後補的計數器測試）。本紀錄所在的 commit 只改文件
- **環境**：macOS（Darwin 24.6）、Python 3.11.0、本機 APFS
- **資料**：每個 P1 案例使用獨立的暫存 root（只複製 schemas、agents、workflows、permissions），以正式流程建立狀態；故障以 `QAOS_FAULT` 注入、同步以 `QAOS_PAUSE` 暫停點完成。沒有使用 repo 的業務資料。
- **結果**（2026-10-07，於上述 commit 執行）：`pytest tests/` 213 passed；`tools/validate_phase1.py` ALL CHECKS PASSED（含 [4] fork 使用為零）

### 狀態說明

- **通過**：P1 已完整驗收。
- **部分**：P1 驗收了通用機制或部分情境，其餘列在「待」欄。
- **待 Pn**：依賴後續階段的功能，該階段完成時驗收。
- **撤銷**：依最終規格附錄 A 撤銷。

### AC 對照

| AC | 狀態 | 測試（tests/…） | 待 |
|---|---|---|---|
| AC-07-8 | 通過 | `test_p1_resume.py::test_validation_failure_writes_only_diagnostics`、`test_p1_review_fixes.py::test_p1_05_three_structural_failures_only_diagnostics`（連續 3 次）、`test_p1_05_diagnostic_beyond_boundary_is_refused`（對照組＋13 種越界：其他檔案、run 欄位、兩個 task、改寫或多寫 gate_results、PASS、兩個事件、終值 DONE／FAILED／強制改寫、任意 updated_at、started_at、改寫 history） | — |
| AC-07-9a | 通過 | 同上 | — |
| AC-07-9b | 通過 | `test_p1_resume.py::test_9b_id_counter_does_not_advance_before_plan_save`（計數器不前進、重送配到同一號碼）、`test_crash_before_plan_save_leaves_nothing`、`test_p1_review_fixes.py::test_p1_06_residue_before_plan_save_is_cleaned`（殘留清除） | — |
| AC-07-9c、9l | 通過 | `test_p1_misc.py::test_9c_9l_half_written_tmp_is_cleaned` | — |
| AC-07-9d | 通過 | `test_p1_resume.py::test_fp_p2_registered_before_first_step`、`test_fp_p1_*` | — |
| AC-07-9e～9j | 部分 | 通用機制：`test_p1_resume.py::test_fp_w_every_step_of_spec_import`（每一步）、`test_types_run_new_submit_gate_approve_complete`（APR 與 run.yaml 的寫入中止） | 各列的業務情境（CLR、TC 版本、revision、landing）待 P3、P5 |
| AC-07-9k | 通過 | `test_p1_resume.py::test_9k_all_steps_done_completed_missing` | — |
| AC-07-9m、AC-07-12 | 通過 | `test_p1_misc.py::test_9m_12_external_modification_stops` | — |
| AC-07-9n | 通過 | `test_p1_audit.py::test_36_37_38_other_ops_files_untouched`、`test_39_event_target_with_different_content_stops` | — |
| AC-07-9q | 通過 | `test_p1_audit.py::test_43_45_49_legacy_freeze_and_first_render` | — |
| AC-07-9r | 通過 | `test_p1_audit.py::test_9r_first_render_abort_keeps_original_audit_log` | — |
| AC-07-9t'' | 通過 | `test_p1_lock_fork.py::test_67_69_kill9_after_plan_save`、`test_68_kill9_before_plan_save_no_residue` | — |
| AC-07-9x、9y、9aa | 待 P5 | — | apply、impact 屬 P5 |
| AC-07-9z' | 通過 | `test_p1_resume.py::test_derived_output_failure_keeps_plan_in_progress` | — |
| AC-07-9ab | 通過 | `test_p1_lock_fork.py::test_77d_parent_exits_child_alive_lock_free`、`test_77e_exec_child` | — |
| AC-07-10 | 待 P5 | — | `topic: other` 的去重屬 P5 |
| AC-07-13～18 | 部分 | `test_p1_resume.py::test_same_request_is_idempotent_and_new_request_is_new_op`（op-P2、op-N4、參數不同即不同 op）；續做的同一 op（op-P1）由各 FP 測試涵蓋 | fulfill、apply 的 fixture（op-N1～N3、op-N5）待 P5；op-N6（migrate 第二次）待 P3 |
| AC-07-19 | 通過 | `test_p1_resume.py::test_duplicate_path_plan_is_rejected` | — |
| AC-07-20、21 | 撤銷 | — | — |
| AC-07-22（submit_gate，不含 A4） | 通過 | `test_p1_resume.py::test_types_run_new_submit_gate_approve_complete` | 含 A4 的部分待 P5 |
| AC-07-23（approve） | 部分 | 同上（UPDATE_SUITE_MEMBERSHIP 的 approve） | 含 A9 的 approve 待 P5 |
| AC-07-24（complete_run、cancel_run） | 通過 | 同上（approve 完成 run）、`test_types_cancel_export_render` | — |
| AC-07-25（寫檔 export、audit render） | 通過 | `test_types_cancel_export_render` | — |
| AC-07-26（maintenance start／end） | 通過 | `test_p1_maintenance.py::test_88_*`、`test_89_*` | — |
| AC-07-27 | 待 P5 | — | impact、apply、fulfill、waive-item |
| AC-07-28 | 待 P3 | — | migrate（完整資料移轉）、migrate rollback、metadata upgrade |
| AC-07-29 | 待 P2／P6 | — | applicability_add |
| AC-07-36～38（防禦性） | 通過 | `test_p1_audit.py::test_36_37_38_other_ops_files_untouched` | — |
| AC-07-39 | 通過 | `test_p1_audit.py::test_39_event_target_with_different_content_stops` | — |
| AC-07-40、42 | 通過 | `test_p1_audit.py::test_40_42_render_abort_formal_sequence` | — |
| AC-07-41、43、45、49 | 通過 | `test_p1_audit.py::test_43_45_49_legacy_freeze_and_first_render` | — |
| AC-07-44 | 待 P3 | — | `migrate --cancel-run` |
| AC-07-46 | 通過 | `test_p1_maintenance.py::test_whitelist_table` | — |
| AC-07-47 | 通過 | `test_p1_audit.py::test_47_frozen_legacy_deleted_render_refused`、`test_p1_review_fixes.py::test_p1_04_*`（全域紀錄缺漏、未知值、舊 run 缺紀錄；檢視不變且不建計畫；新 run 正常）、`test_p1r2_04_render_compares_parsed_times`（時區、小數秒、同秒、等價時間、缺時區、不合法、移轉清單；overlay 與磁碟兩種來源） | — |
| AC-07-48 | 通過 | `test_p1_audit.py::test_48_new_run_after_migration_uses_events_only` | — |
| AC-07-64、70、72、73、74 | 通過 | `test_p1_lock_fork.py::test_64_70_72_lock_held_same_request_refused_readonly_ok`、`test_70_child_write_while_parent_holds_lock_fails_fast` | — |
| AC-07-65 | 通過 | `test_p1_lock_fork.py::test_65_two_resumes_only_one_proceeds` | — |
| AC-07-66 | 通過 | `test_p1_lock_fork.py::test_66_different_ops_only_one_acquires` | — |
| AC-07-67、69 | 通過 | `test_p1_lock_fork.py::test_67_69_kill9_after_plan_save` | — |
| AC-07-68 | 通過 | `test_p1_lock_fork.py::test_68_kill9_before_plan_save_no_residue`、`test_p1_review_fixes.py::test_p1_06_residue_before_plan_save_is_cleaned`（故障、寫入清單建立後 SIGKILL、內容檔建立後 SIGKILL、內容檔暫存寫好後 SIGKILL；下一個寫入只刪清單列出的殘留，8 種外部內容（含形狀完全符合的內容檔）與空 hex 目錄原樣保留，差異與未中止的對照 root 相同）、`test_p1_06_abort_after_plan_save_keeps_blobs_and_drops_manifest`、`test_p1r4_01_*`（目標既存：不同內容、相同內容）、`test_p1r5_01_*`（同 op 既存的清單：非 QAOS 格式、可解析、symlink；staging.d 暫存；scope 計畫暫存；含 after_claim）、`test_p1r4_02_*`（scope、op、blobs、staging.d、內容檔各層 symlink；拒絕且 root 與外部檔案都不變）、`test_p1r4_03_*`（認領後、清單短寫、清單零位元組中止；清理途中中止兩次後完成） | 不取鎖的外部程式同時修改這些路徑，不在保證範圍內 |
| AC-07-71 | 通過 | `test_p1_lock_fork.py::test_71_stale_owner_file_is_ignored` | — |
| AC-07-75、76 | 通過 | `test_p1_misc.py::test_75_*`、`test_76_*` | — |
| AC-07-77a～c | 通過 | `test_p1_lock_fork.py::test_77abc_fork_child_drops_lock_parent_keeps_it` | — |
| AC-07-77d | 通過 | `test_p1_lock_fork.py::test_77d_parent_exits_child_alive_lock_free` | — |
| AC-07-77e、77e-ctrl | 通過 | `test_p1_lock_fork.py::test_77e_exec_child`（main 正常結束、main SIGKILL、ctrl） | — |
| AC-07-77f | 通過 | `test_p1_lock_fork.py::test_77f_multiple_forks_while_holding` | — |
| AC-07-77g | 通過 | `tools/validate_phase1.py` [4] | — |
| AC-07-77h～k | 通過 | `test_p1_lock_fork.py::test_77h_*`、`test_77i_*`、`test_77j_*`、`test_77k_*` | — |
| AC-07-78 | 通過 | `test_p1_resume.py::test_derived_output_failure_keeps_plan_in_progress` | — |
| AC-07-79 | 通過 | `test_p1_lock_fork.py::test_79_no_context_no_write`、`test_77abc_*`、`test_p1_review_fixes.py::test_p1_02_fork_inside_active_capture_cannot_write`（擷取中 fork、自建擷取） | — |
| AC-07-80 | 部分 | `test_p1_maintenance.py::test_80_full_flow_reaches_s_post` | `migrate verify` 待 P3 |
| AC-07-81 | 通過 | `test_p1_maintenance.py::test_81_82_maintenance_refuses_business_allows_readonly` | — |
| AC-07-82 | 部分 | 同上（唯讀指令） | `migrate verify` 待 P3 |
| AC-07-83 | 部分 | `test_p1_maintenance.py::test_83_maintenance_end_refused_while_plan_incomplete`（未完成的 migrate 計畫） | 未完成的 rollback 計畫待 P3 |
| AC-07-84 | 通過 | `test_p1_maintenance.py::test_84_migrate_refused_in_s_pre` | — |
| AC-07-85、86 | 通過 | `test_p1_maintenance.py::test_85_86_run_cancel_in_s_pre` | — |
| AC-07-87（防禦性） | 通過 | `test_p1_maintenance.py::test_87_business_plan_cannot_resume_in_maintenance` | — |
| AC-07-88 | 通過 | `test_p1_maintenance.py::test_88_maintenance_start_abort`（S_pre／S_post × FP-S1／S2 × 兩種入口） | — |
| AC-07-89 | 通過 | `test_p1_maintenance.py::test_89_maintenance_end_abort`（移轉前後 × FP-E1／E2 × 兩種入口） | — |
| AC-07-90～93 | 待 P3 | — | migrate、rollback 的續做與接管 |
| AC-07-94（防禦性） | 通過 | `test_p1_maintenance.py::test_94_identity_mismatch_is_refused` | — |
| AC-07-95 | 通過 | `test_p1_resume.py::test_fp_w_every_step_of_spec_import`（每一種步驟、兩種入口交替）、`test_multi_file_render_abort_after_first_file` | — |
| AC-07-96 | 通過 | `test_p1_resume.py::test_tamper_stops_resume`（四例） | — |
| AC-07-96（gate 退回） | 通過 | `test_p1_review_fixes.py::test_p1_01_validator_fail_gate_abort_then_resume`（G-TVAL，兩種入口）、`test_wf_b_bug_and_e_regression.py::test_12b_*`（G-BVAL：重送續做、完成後重送、下一輪新 op） | — |
| AC-07-97 | 通過 | `test_fp_p2_*`（①）、`test_9k_*`（②）、`test_registrations_stay_valid_and_seq_contiguous`（③）、`test_tampered_registration_refuses_resume`、`test_p1_review_fixes.py::test_p1_03_*`（④：action、registered_at、plan_sha256、plan_seq、檔名 × 未完成／已完成；完成狀態紀錄竄改） | — |
| AC-07-98 | 通過 | `test_fp_p1_unregistered_plan_is_registered_then_resumed`（a、b）、`test_fp_p1_other_op_after_reconcile_is_refused`（c）、`test_crash_before_plan_save_leaves_nothing`、`test_p1_06_residue_*`、`test_p1_06_registered_without_plan_is_refused`（已完成／未完成 × 只缺計畫、計畫與 op 目錄都缺、只剩計畫暫存；另有可清殘留也不清理；d） | — |
| AC-07-99（防禦性） | 通過 | `test_p1_resume.py::test_invalid_unregistered_plan_refuses_all_writes` | — |
| AC-07-100 | 通過 | `test_no_change_export_has_no_content_steps`（①）、`test_partial_no_change_and_tampered_no_change_path`（②④）、`test_multi_file_render_abort_after_first_file`（③） | — |
| AC-07-1～7、11、101～104 | 待 P5 | — | 去重與開單關卡 |

### P1 的實作說明（審查時請一併確認）

1. **寫入擷取**：既有的業務邏輯在擷取（overlay）中執行一次，產生完整的計畫；所有步驟的內容存成計畫的內容檔（`operations/<scope>/<op>/blobs/<sha256>`），續做時寫入保存的內容，不重新計算。
2. **ID 配發**：計數器的更新是計畫中的一步，ID 由計畫固定；計畫保存前中止不前進、不留空號。Oscar 2026-10-07 定案（附錄 A 4-17），規格主文已同步。
3. **驗證失敗的診斷**：只寫 task 欄位（`gate_results` 追加並記錄被拒的 `artifact_id`、狀態回 READY）與一個事件檔；被提交的 artifact 不修改、不開核准單（附錄 A 4-16）。越權提交仍是正常操作（附錄 A 4-15；Oscar 決定、Codex 第二份審查接受）。
4. **Python API 的 op 身分**：直接呼叫寫入函式時，op_id 同樣由請求內容決定（同一請求重送 → 同一 op）；要刻意再執行一次，傳 `new_request=True`。既有測試中刻意建立相同輸入的 run，已改為明確傳入。
5. **唯讀指令**：`clarification list` 改為唯讀；寫 `clarifications/index.md` 改由 `clarification index`。
6. **P1 的 migrate**：只做空 root 也需要的部分（凍結 legacy audit、移轉標記、第一次 render）與 `--acknowledge-idle`。移轉清單、R000、sidecar、CLR rev 0、`--cancel-run`、`migrate verify`、`migrate rollback` 屬 P3。
7. **audit.log**：改為由事件檔整份重建（每個操作重建它影響的 run log 與全域 log），不再追加；需要和 Session B 協調（D8）。
8. **效能**：測試時間從約 5 秒增加到約 2 分鐘（每次寫入都經過計畫、fsync 與 render）；全域 log 的 render 每次讀取所有事件檔，資料量增加時可在第二批改為增量。
9. **登錄紀錄核對**：每次讀取登錄紀錄都核對全部紀錄的欄位、檔名與 `plan_seq` 連續性；和計畫、完成狀態紀錄的一致性（plan hash、action、registered_at）只在涉及該 op 時核對：續做、已完成回報、`operation list`，以及第 0 步的 rollback 紀錄（第 0 步不對所有紀錄做這項核對，附錄 A 4-11）。限制：兩筆登錄紀錄的 `plan_seq` 互換（仍連續）無法由紀錄本身偵測，`plan_seq` 不是可信的防竄改時間鏈；P3 的後續操作盤點沿用同一限制。
10. **計畫保存前的殘留**（附錄 A 4-18）：擁有權的根據是零位元組的認領檔 `staging.d/<op>.claim`（O_EXCL 建立、最先建立、最後刪除），寫入清單 `staging.d/<op>.yaml` 列出將新建的內容檔；保存計畫時本 op 的任何入口（op 目錄、認領檔、清單、本 op 的計畫暫存）已存在就拒絕，所以認領檔授予的清理權只涵蓋它之後本次新建的檔案。每個寫入請求取得鎖後，先核對有登錄紀錄卻沒有計畫檔的 op，有就拒絕、不做任何清理；再先核對全部待刪路徑（每一層不是 symlink、內容檔 hash 相符）才刪。沒有認領檔的內容一律不刪，看起來像 op 目錄的保留並回報。限制：不取鎖的外部程式同時修改這些路徑，不在保證範圍內（不宣稱跨檔原子性）。
11. **擷取 guard**：只載入 `store` 而沒有 executor 時，擷取與寫入一律拒絕（fail closed）。
12. **時間比較**：render 判定移轉後的新 run 時，把 `created_at`、`migrated_at` 解析成 UTC 時間再比較；缺時區或格式不合法 → 拒絕。

## P2：spec 引用、外部來源、有型別來源與 CLR 欄位

- **執行 commit**：`9b1bde0b0995a33c86b7dc7222bc57e9ea343ac3`（分支 `qaos/requirement-a`；P2 程式為 `490ba1b`、`33bc228`、`60ce878`，P2 程式碼審查 P2-01～03 的修正為 `ddab53e`，局部複驗 P2R2-01 的修正為 `9b1bde0`）。本紀錄所在的 commit 只改文件
- **環境**：同 P1
- **資料**：每個 P2 案例使用獨立的暫存 root，以正式 CLI 建立 spec、引用宣告、CLR、答案與適用紀錄；決策點欄位以入口 D（腳本呼叫 `clarification.new()`）提供。legacy spec 與 legacy CLR 以直接寫入舊格式檔案建立（模擬部署前就存在的資料）。核准單的 `decision.resolutions[]` 要到 P4 才由正式流程寫入，所以 approval 型 SourceRef 只以記憶體中的核准單做函式層測試。AC-02-6 的 RM、TC 情境沿用 session root（前面 WF 測試以正式流程建立）
- **結果**（2026-10-07，於上述 commit 執行）：`pytest tests/` 295 passed；`tools/validate_phase1.py` ALL CHECKS PASSED。主資料夾既有的 spec.yaml 與 54 張 CLR（唯讀）全部通過新 schema
- **突變檢查**：讓 `covers` 一律回傳 True、`x16` 一律通過時，5 個相關測試失敗；把 P2-01～03 的修正退回時，對應的 8 個反例失敗（4 個合法對照通過）；把 P2R2-01 的修正退回時，新增的 9 個反例全部失敗；之後都還原

### AC 對照

| AC | 狀態 | 測試（tests/…） | 待 |
|---|---|---|---|
| AC-01-1 | 通過 | `test_p2_spec.py::test_ac_01_1_*`（版本不存在、實體檔和登記值不符） | — |
| AC-01-2 | 通過 | `test_ac_01_2_legacy_spec_passes_schema_and_reads_as_undeclared`、`test_ac_01_2_existing_repo_specs_pass_new_schema` | — |
| AC-01-3 | 通過 | `test_ac_01_3_*`（add → remove → add；decl_rev 1、2、3；舊紀錄、content_hash、file、v.md 不變） | — |
| AC-01-4 | 通過 | `test_ac_01_4_reference_only_refused_at_each_entry`（7 個入口各一例；不建立 run、快照不變） | testcase-revision 以 inputs 帶入 reference_only 版本驗證；「TC 版本本身釘在 reference_only 版本上」在正式流程中無法產生（metadata upgrade 會拒絕），engine 另外核對屬防禦性 |
| AC-01-5 | 通過 | `test_ac_01_5_*` | — |
| 附錄 A 2-2、2-4 | 通過 | `test_reference_and_upgrade_only_by_human`（system、agent-*）、`test_reference_status_transitions_and_rules` | — |
| AC-02-1～5 | 通過 | `test_ac_02_1_*`～`test_ac_02_5_*`、`test_metadata_upgrade_only_fills_missing`、`test_source_fields_recorded` | — |
| AC-02-6 | 通過 | `test_ac_02_6_reference_only_refused_when_used_by_run`、`test_wf_zz_p2_reference_only_targets.py`（run、RM、TC）、`test_ac_02_6_referenced_in_closure_only_is_allowed`（附錄 A 2-8） | — |
| AC-02-7 | 通過 | `test_ac_02_7_*` | — |
| AC-10A-57 | 通過 | `test_ac_10a_57_blank_title_warns`、`test_p2_03_explicit_title_is_kept_and_blank_warns`（省略、空字串、半形與全形空白、有效名稱）、`test_title_normalization` | — |
| AC-06-1 | 待 P4 | — | 入口 A、B 逐欄抄寫需要決策點 |
| AC-06-2 | 通過 | `test_p2_sources.py::test_ac_06_2_*`（入口 D） | 入口 A、B 在 P4 |
| AC-06-3 | 通過 | `test_ac_06_3_*`（只有引用處 → 成立並產生 document_items；沒有引用處、空清單 → 拒絕、快照不變） | — |
| AC-06-4 | 通過 | `test_ac_06_4_*` | — |
| AC-06-5 | 通過 | `test_ac_06_5_*` | — |
| AC-07-29（applicability_add） | 部分 | `test_ac_07_29_applicability_add_abort_and_resume`（兩種入口） | P6 收尾 |
| AC-08-1、3、5、7、8、14、18、19、25、28、30、31 | 通過 | `test_ac_08_*`、`test_clarification_ref_checks_pinned_rev`、`test_answer_revisions_are_append_only_and_record_basis` | — |
| AC-08-21～24、35～37 | 通過 | `test_covers_table` | — |
| AC-08-2 | 部分 | `test_ac_08_2_*`（新產出的空或缺 quote、location FAIL） | 「舊資料不 FAIL」的實際檢查點是 G-SPEC（P4） |
| AC-08-6、17、27、38 | 部分 | `test_ac_08_6_*`、`test_ac_08_17_and_38_*`、`test_ac_08_27_28_*`（X16 FAIL；SourceRef 本身 PASS） | 「G-SPEC FAIL、不是 E1」在 P4 |
| AC-08-20、26、29 | 部分 | `test_covers_table`、`test_ac_08_27_28_*`（29：人確認 basis_hash 後 X16 PASS） | 「成為／不成為 E1」在 P4 |
| AC-08-9、12、13、33、34 | 部分 | `test_approval_ref_validation`、`test_ac_08_33_*`、`test_p2_01_approval_wrapper_validates_inner_source`（包裝內的 no_change、out_of_scope、錯 hash、錯 quote、已撤回都拒絕）、`test_p2_02_source_ref_index_shape`、`test_p2r2_01_*`（索引 0.0、1.0、0.5、-1 在 validate、x16、effective_basis 與核准單內部來源都回傳錯誤；addenda CLI 不拋 traceback）（記憶體中的核准單） | 核准單 `resolutions[]` 的正式寫入在 P4 |
| AC-08-10 | 部分 | `test_clarification_ref_checks_pinned_rev`（依釘選的 rev 驗證，新答案之後仍 PASS） | 舊 run 恢復在 P4（派發包快照） |
| AC-08-16、32 | 部分 | `test_ac_08_17_and_38_*`（legacy CLR＋applicability 的合成版本） | DAILYREPORT 實際資料在 P3 移轉後驗收 |
| AC-08-4 | 待 P3／P4 | — | CLR-CASHFLOW-005 的 rev 0 由移轉建立（P3）；完整 G-SPEC 在 P4 |
| AC-08-11、15 | 待 P4 | — | 派發與狀態推導 |

### P2 的實作說明（審查時請一併確認）

1. **模組**：spec 的寫入指令集中在新模組 `tools/qaos/spec_ops.py`（`spec import` 從 `cli.py` 移入）；SourceRef 相關的讀取函式在新模組 `tools/qaos/sources.py`。第 2 章 §6 原寫「`store.py` 讀寫版本條目、legacy 預設值」，改由 `spec_ops` 提供。
2. **介面補充**：附錄 A 2-12、3-23、3-24（索引只接受整數表示、`--package-file`、`--analysis-policy`、宣告紀錄的 `action`、答案修訂的 `op_id`、紀錄 `sha256` 的定義、`--params` 用 JSON 等）。
3. **回答必須能建立 basis**：CLR 的 spec 版本沒有匯入時拒絕回答。主資料夾目前只有 `CLR-CASHOUT-001`（APPLIED，`SPEC-CASHOUT-001@1.0` 未匯入）會遇到；它已 APPLIED 不會再回答，但 P3 移轉建立 rev 0 時要處理。既有測試 `test_20b` 因此先以正式流程匯入它使用的 spec，保留原本驗影響掃描的意圖。
4. **第 6 章 A3 提前**：狀態機加入 ANSWERED → ANSWERED（追加答案修訂），讓「答案修訂只能追加」可以實際運作；第 6 章其餘轉換（INCORPORATED、新的 apply 檢查等）仍在 P5。
5. **SourceRef 在需求、TC、RR、bug schema 中的位置**（第 3 章 §6.3、§14）沒有在 P2 加入：這些位置要配合 G-SPEC、G-DESIGN 的新檢查才有意義，移到 P4 一起做。P2 只提供 defs 的 SourceRef 與驗證函式。
6. **開單關卡與去重**（入口 C 的 `--consulted`、issue key）屬 P5；P2 的 `clarification.new()` 只在給了決策點欄位時驗證，舊的呼叫端不受影響。

## P3：RM revision、綁定、過時判定、CIA 候選、移轉與回復

- **執行 commit**：`f72ecf6526150866b15ae0d54f9ebf1f291423da`（分支 `qaos/requirement-a`；P3 程式為 `7430b7d`、`282b401`、`982ffe2`、`74de040`，P3 程式碼審查 P3-01～06 的修正為 `4a84069`，局部複驗 P3R2-01、02 的修正為 `f72ecf6`）。本紀錄所在的 commit 只改文件
- **環境**：同 P1
- **資料**：每個案例使用獨立的暫存 root。新程式的狀態以正式流程建立（`tests/p3_flow.py`：new_run、submit、gate、approve）；移轉用的 legacy 資料由**需求 A 之前的程式**（base `2e01d4b`，以 `git archive` 匯出到系統暫存目錄，唯讀）以它自己的正式流程產生（`tests/p3_legacy.py`）。標明「竄改」「故障注入」「模擬經授權的人工修復」的子例才在流程後修改檔案。CIA 的 G1～G8 以正式流程產生的兩批候選 TC（分屬 R001、R002）搭配記憶體中的 run 與 CIR 驗證（CIA agent 新契約在 P4）
- **結果**（2026-10-07，於上述 commit 執行）：`pytest tests/` 371 passed；`tools/validate_phase1.py` ALL CHECKS PASSED
- **突變檢查**：拿掉 `_skip` 的第 2、3 條與無 T0 流程的過時檢查時，5 個相關測試失敗；把 P3-01～06 的修正退回時，對應的 7 個反例全部失敗；把 P3R2-01、02 的修正退回時，新增的 5 個反例全部失敗；之後都還原

### AC 對照

| AC | 狀態 | 測試（tests/…） | 待 |
|---|---|---|---|
| AC-09-1、2 | 通過 | `test_p3_revisions.py::test_ac_09_1_2_*`、`test_revision_files_are_immutable_and_indexed` | — |
| AC-09-3、20 | 部分 | `test_p3_migrate.py::test_old_running_run_resumes_on_its_sidecar_revision`（移轉前就在跑的 run，移轉後另有內容不同的 R001；舊 run 的引用解析與 G-DESIGN 仍依 sidecar 的 R000） | 真實 RUN-20261002-001 複本與派發包（P4）在 M1 預演時驗收 |
| AC-09-4 | 通過 | `test_migrate_acknowledge_idle_results`、`test_ac_09_55_56_*`（cancel-run 的 run 屬 restore） | — |
| AC-09-5 | 通過 | P1 的白名單測試、`test_ac_09_26_*`（標記寫入前業務寫入被拒） | — |
| AC-09-6、42、46 | 通過 | `test_ac_09_6_42_46_running_run_needs_a_mode`（含附錄 A 5-6 的衝突與非 RUNNING） | — |
| AC-09-7、86 | 通過 | `test_skip_binds_latest_and_declaration_change_blocks_until_accepted` | — |
| AC-09-8、9 | 通過 | `test_closure_changes_and_newer_versions` | — |
| AC-09-10 | 通過 | P2 `test_closure_cycle_and_limit`（revision 的 reference_pins 用同一函式） | — |
| AC-09-11 | 部分 | `test_ac_09_1_2_*`（有 DRAFT 需求時不跳過） | SITELIST 實際資料在 P6 |
| AC-09-12 | 待 P4 | — | revision 中的 clarification 型 SourceRef 要等需求 schema 加入 SourceRef（P4） |
| AC-09-13 | 通過 | `test_migrate_acknowledge_idle_results` | — |
| AC-09-14 | 部分 | 各案例分別斷言 run.yaml、R(n)、TC 版本不變 | P6 彙整 |
| AC-09-15 | 待 P4／P6 | — | PLATFORMRULE fixture 與完整 CIA agent 流程 |
| AC-09-16 | 通過 | `test_ac_09_16_*` | — |
| AC-09-17、32 | 部分 | `test_ac_09_17_32_*`（一張 PENDING 核准單；重送不重複轉換與 audit） | 同一 run 多張 PENDING 核准單的 fixture、「之後的新 run 不會綁到 0.6」以真實資料在 P6 |
| AC-09-18、19 | 待 P5 | — | RESOLVE_AMBIGUITY 的決議與 CLR 生命週期 |
| AC-09-21、22 | 通過 | `test_testcase_revision_binds_latest_and_refuses_when_outdated`、`test_p3_migrate.py::test_p3_05_*`（直接 run new 指定別的版本或不存在的 TC → 拒絕、不留下 run） | 派發包的 RMPin 在 P4 |
| AC-09-23 | 通過 | `test_ac_09_23_manual_without_spec_is_refused`、`test_manual_with_spec_hint_binds_latest` | — |
| AC-09-24、66、67 | 部分 | 程式有明確分支（regression-generation 不產生 sidecar；沒有 audit.log 的 run、沒有 render 的 CLR 屬 remove） | legacy fixture 沒有這三種資料，M1 預演時驗收 |
| AC-09-25、34 | 通過 | P2 `test_ac_01_4_*` | — |
| AC-09-26 | 通過 | `test_ac_09_26_x_resumes_after_partial_migration` | — |
| AC-09-27、33 | 待 P4 | — | 派發包、decision_refs |
| AC-09-28～30 | 部分 | `test_p3_cia_groups.py`（兩個 pin 的分組與 G1～G8） | 兩輪完整 CIA 與 legacy sidecar 混合在 P4／P6 |
| AC-09-31 | 部分 | `test_candidates_include_every_active_tc_of_the_spec`（只判一組 → G2、G5 FAIL） | DAILYREPORT 實際資料在 P6 |
| AC-09-35～41 | 通過 | `test_p3_cia_groups.py::test_partition_violations_fail`（G1～G8 各例） | — |
| AC-09-43、44 | 通過 | `test_migrate_acknowledge_idle_results`、`test_ac_09_44_cancel_run_in_same_operation`（fixture 的 run ID） | 真實 ID 依附錄 A 5-10 在 M1 |
| AC-09-45、47、48、50 | 待 | — | 本輪沒有對應測試（S_pre 先 cancel 再移轉；cancel 步驟後中止；未完成的 cancel 計畫；有 PENDING APR 的 RUNNING run） |
| AC-09-55、56 | 通過 | `test_ac_09_55_56_rollback_after_completed_migration`（兩種模式） | — |
| AC-09-57、71、72、75 | 通過 | `test_rollback_after_partial_migration`（FP-M0、M1、M2、FP-W） | — |
| AC-09-58、79、81 | 部分 | `test_rollback_abort_points_then_resume`（依不可變 R 計畫找出 R0、takeover 尾端、restore 中途、檢查 A 後、標記尾端、檢查 B 前、Rt1 尾端，先斷言各群組狀態，再以兩種入口續做） | X 未完成時的 R1 尾端、`no_change` 不被選為 L 的逐點斷言在 P6 |
| AC-09-59 | 通過 | `test_ac_09_59_82_*`（含重送仍拒、修復後完成） | — |
| AC-09-82 | 部分 | `test_ac_09_59_82_*`、`test_ac_09_82_t7_other_categories`（restore、remove、untouched、audit.log 竄改） | X 的 no_change 業務檔一例未單獨測 |
| AC-09-60、61 | 通過 | `test_ac_09_60_61_later_ops`（預設拒絕與報告；① T7 拒絕；② 回復並保留清單外的新檔） | — |
| AC-09-63、90 | 通過 | `test_ac_09_63_90_remigrate_after_rollback` | — |
| AC-09-64 | 待 M1 | — | 以舊程式驗證 R5 |
| AC-09-65 | 通過 | `test_ac_09_65_rollback_requires_maintenance` | — |
| AC-09-68 | 通過 | `test_ac_09_55_56_*`（回復後沒有任何既有檔案被改動或刪除；鎖檔保留） | — |
| AC-09-73 | 部分 | `test_ac_09_73_t5_evidence_conflict`（刪除尾端前的完成紀錄 → T5 拒絕、不寫入）、`test_p3_01_*`（已完成的 X 缺最後一個完成紀錄、completed 竄改 → 拒絕） | 刪除事件、改事件內容（AC-09-74）、續做 X（AC-09-76）在 P6 |
| AC-09-83、84 | 部分 | `test_check_a_and_b_stop_on_external_change_then_repair`（③ 檢查 A、④ 檢查 B，含修復後完成）、`test_p3_02_*`（R 已凍結的 X 完成紀錄被刪 → 檢查 A 停止，兩種入口）、`test_p3r2_01_*`（維護往返後 audit.log 被正常 render 的步驟，完成紀錄仍凍結並核對）、`test_p3r2_02_*`（X 計畫被竄改 → 停止；修復後完成） | ①②、⑤～⑦ 在 P6 |
| AC-09-85 | 部分 | `test_ac_09_85_terminal_inconsistency_blocks_all_writes`（⑥ 防禦性） | ①～⑤ 的逐點斷言在 P6 |
| migrate verify（§12） | 部分 | `test_p3_03_verify_detects_missing_or_tampered_evidence`（移轉後缺 X 完成紀錄、回復後 R 事件竄改、回復後缺 X 完成紀錄 → 失敗並列出路徑；恢復後通過）、`test_p3r2_01_round_trip_*`、`test_p3r2_02_*`（回復後 X 完成紀錄被刪或改、X 計畫被改 → 失敗） | 其餘各類的逐項負例在 P6 |
| AC-09-88 | 通過 | `test_migrate_acknowledge_idle_results`、`test_ac_09_88_legacy_r000_skip_rule_and_89_declaration` | — |
| AC-09-89 | 部分 | 同上（a） | (b) 舊 run 依固定 pin 續做在 P6 |
| AC-09-91 | 通過 | `test_ac_09_91_declarations_before_migration_refuse`（兩例，防禦性） | — |
| AC-07-90～93 | 部分 | `test_rollback_after_partial_migration`、`test_rollback_abort_points_then_resume` | FP 表逐點彙整在 P6 |
| AC-07-28（migrate、rollback 的中止加續做） | 部分 | 同上 | metadata upgrade 的中止續做在 P6 |

### P3 的實作說明（審查時請一併確認）

1. **模組**：revision 與綁定在新模組 `tools/qaos/rm.py`（第 5 章 §16 原寫 `store.py`）；移轉、回復、verify 在新模組 `tools/qaos/migrate.py`。
2. **附錄 A 5-12（R）**：CLR 的 spec 版本沒有匯入時跳過 rev 0 並記為例外。2026-10-07 更新：規則保留作為安全網；唯一會遇到的 `CLR-CASHOUT-001` 由 Oscar 決定以資料更正處理（spec_version 1.0 → 0.1，主資料夾 main `e312a00`）。
3. **附錄 A 5-13（R）**：T7 接受 `audit.log` 的正常重新 render，否則回復點之後任何操作（含維護開關）都會讓回復永遠被拒。
4. **附錄 A 5-14（I）**：實作補充的定義（revision 編號、run 欄位、`legacy_binding`、清單中的循環項目、`untouched` 範圍、R 的事件等）。
5. **既有測試配合新規則**：manual run 必須有 spec（第 5 章 §4.3），兩個 ADR-009 的 manual 測試改為有 spec 或驗證拒絕；gate 單元測試的需求模型改經 `save_requirements` 建立（需求 ID 改成符合 schema 的格式）；test_15 的 CIR 加上兩端 revision 與 pin_groups。
6. **被接管的計畫**：被未完成 R 接管的 X，即使已完成，對它的請求（重送、`operation resume`）也拒絕並提示續做 R（第 5 章 §13.10）。
7. **agent 指示**：CIA 的 pin_groups 只改了 schema 與 gate；change-impact-analyst 的契約與指示依 D7 在 P4 更新。整個需求 A 是同一個 MR，P3 與 P4 之間沒有部署空窗。
8. **AC-09-50 等未測項目**：舊程式的 legacy fixture 沒有「有 PENDING APR 的 RUNNING run」等資料；這些在 M1 預演（真實資料的唯讀複本）或 P6 驗收，已在上表標「待」。
9. **顯示端的退回**：核准單渲染、final export 只有在移轉前（沒有移轉標記）的 legacy 資料缺 pin 時，才改用最新 revision 顯示；移轉後缺 pin 一律報錯。
10. **`migrate verify`（移轉後）**：由 X 的不可變計畫逐步核對，所以要在移轉剛完成、離開維護之前執行（第 5 章 §15 M3）；之後的操作會重新 render audit.log，屬正常變動。

## P4：派發包、決策點、狀態推導與路由、G-DESIGN、preflight、agent 契約

- **執行 commit**：`9c11b75d102c0973059896733c7026607b298650`（分支 `qaos/requirement-a`；P4 程式、schema、agent 契約與測試為 `865f287`，P4 程式碼審查 P4-01～05 的修正為 `9403628`，下游 iteration 與舊輪產出的重評修正為 `ff21296`、`1654b0b`，局部複驗 P4R2-01～03 的修正為 `5de98c2`，第二次局部複驗 P4R3-01 與測試證據的修正為 `9c11b75`）。本紀錄所在的 commit 只改文件
- **環境**：同 P1
- **資料**：每個案例使用獨立的暫存 root。spec 以 `spec import`、引用以 `spec reference add` 建立；run、派發、提交、gate、核准、CLR 的回答與適用紀錄都走正式 API（`tests/p4_flow.py`）。CLR 的入口 D（腳本呼叫 `clarification.new()`）另外標示。範例 A～F 以測試 root 中的小型 spec（`SPEC-DEMO-001`、`SPEC-REF-001` 等）重現同樣的資料形狀與推導，**不是** SITELIST、DAILYREPORT 的真實資料；真實資料的重現在 M1 預演時驗收。標明「函式層」的子例直接呼叫內部函式（64 組合路由表、狀態機的 kind 限制、G-SPEC 的派發包 sha 核對）；標明「竄改」的子例才在流程後修改檔案
- **既有測試的配合**：需要派發包的 task，測試 helper（`tests/helpers.write_artifact`）在寫入 artifact 前以正式指令 `dispatch` 產生派發包並填入 `dispatch_packet_sha256`（模擬 orchestrator 在派工前執行 `qaos dispatch`）；SpecAnalysis 沒有給 `consulted_sources` 時，helper 以派發包中的目標與全部必讀參考填入（模擬讀完必讀來源）
- **結果**（2026-10-07，於上述 commit 執行）：`pytest tests/` 408 passed（快照與 commit 的程式、測試內容逐檔相同）；`tools/validate_phase1.py` ALL CHECKS PASSED
- **突變檢查**（在 scratchpad 的複本上逐一套用、跑對應測試，worktree 不變）：P4 原有 31 項、審查修正 12 項（TC 的 source_refs 不驗、額外來源也套目標限制、下游不加 iteration、5 個索引欄位不查整數表示、RR 不驗 SourceRef／不查範圍／接受舊形狀、Designer 契約回到舊規則）、P4 局部複驗修正 7 項（TC 核准型與 CLR 型來源不綁定決策點、驗證不傳引用處、RR 不查關聯需求、RR 不查可用依據、RR 不要求 spec_basis_decision、豁免項目不查物件形狀、同輪重評被擋）、第二次局部複驗修正 1 項（豁免項目可同時有 cited_at 與 pin）全部被對應測試抓到——派發（沒有派發包、沿用舊派發包、同一 iteration 重複派發、額外來源不附理由）、G-SPEC（consulted hash、必讀參考、派發包 sha、派發後宣告改變、references_status、引用處文字、consulted 不在閉包、X14、X15 的 CLR 狀態、X16、X18 的 `*` 混用、3-18、approval 依據的 outcome、agent 自填推導欄位）、推導（豁免不影響 gap_missing）、G-DESIGN（E1 引用未採用的一側、背景 known_rules、E3～E5 的 exploratory、每個 TC 的 decision_refs）、G-TVAL（派發包範圍）、preflight（defer、重複條目、混合 revision 的舊規則）、開單（去重、短問題文字）、A9 與狀態機的 kind 限制
- **自審**：交 Codex 前以獨立 agent 找反例，發現 9 項（1 項 blocker：`withdraw` 的操作裝飾器被移位；4 項 major：approval 型依據未限 `select_interpretation`、只有 negative TC 要求 decision_refs、混合 revision 時略過舊規則、附錄 A 1-19 需要審查確認；4 項 minor）。8 項已修正並補反例；1-19 之後經 Codex 審查、Oscar 決定「停下由人處理」（見實作說明第 2 點）

### AC 對照

| AC | 狀態 | 測試（tests/…） | 待 |
|---|---|---|---|
| AC-04-1 | 通過 | `test_p4_dispatch.py::test_ac_04_1_*`（第二次拒絕、快照不變、sha 和 task 紀錄一致；approval task 不需要派發包） | — |
| AC-04-2 | 通過 | `test_ac_04_2_*`（核准後 iteration 1：還沒派發 → 拒絕；已派發新包、產出沿用舊包 → 拒絕；新包 → PASS） | — |
| AC-04-3 | 通過 | `test_ac_04_3_*`（hash 不符、不在派發包內、必讀參考沒查也沒列 → FAIL；列為 out_of_scope → PASS；竄改參考檔 → FAIL）、`test_p4_negative_cases.py::test_gspec_packet_sha_*` | — |
| AC-04-4 | 通過 | `test_ac_04_4_*`（合法但不在 Validator 派發包範圍內的來源（Designer 派發時以 `--extra` 登記、Validator 沒有登記的 `SPEC-OTHER-001`）：Validator 沒報 missing_reference → G-TVAL Structural FAIL；有報 → 依 Validator FAIL 退回 Designer）、`test_p4_sources_and_iterations.py::test_downstream_*`（Designer 登記額外來源後，Validator 以新派發包登記同一來源 → PASS） | — |
| 第 3 章 §6（TC 的 SourceRef） | 通過 | `test_tc_source_refs_are_validated_in_full`（quote、hash、不存在的答案修訂、不存在的核准單、沒有綁定決策點的 CLR 來源 → G-DESIGN FAIL、沒有 materialize；合法 spec 來源 → ACTIVE）、`test_approval_source_bound_to_its_decision_point`（核准來源用在其他需求、同需求的其他問題 → FAIL；用在它裁決的決策點 → PASS）、`test_clarification_source_full_flow`（自動開的衝突 CLR → 回答 → 核准選定 → 以 CLR 為 resolution 重新分析 → TC 同題引用 → G-DESIGN、G-TVAL、RR 同題 `spec_basis_decision` → ACTIVATE，TC 成為 ACTIVE） | — |
| 第 3 章 §6.3（RR 的 SourceRef） | 通過 | `test_risk_review_spec_basis_source_ref_types`（錯 quote、舊形狀、範圍外 CLR、approval 型缺 `spec_basis_decision`、不是該決策點可用的 CLR → FAIL；spec 型正式流程 PASS 並建立 ACTIVATE 核准單；approval 型（指定決策點）與 null＋needs_clarification 以函式層對同一 task 核對 PASS）、`test_approval_source_bound_to_its_decision_point`（RR 以正式流程：核准來源指向關聯需求以外、同需求其他問題 → FAIL；指向它裁決的決策點 → PASS） | — |
| 附錄 A 1-39（下游新 iteration） | 通過 | `test_downstream_tasks_get_new_iteration_after_route_back_and_reject`（semantic FAIL 退回、整批 reject；Validator、RR 在被推進時進入新 iteration、舊包拒絕、舊派發紀錄保留）、`test_wf_x_gate_rejection_branches.py::test_62`（舊輪產出不能在新輪重評）、`test_62b`（同一輪 G-DESIGN FAIL 後不重新提交、直接再 gate：仍以同一組 artifact 重評，iteration 與派發包不變；再以標明的規則替身模擬規則修正後 PASS 推進）、`test_p1_review_fixes.py::test_p1_01_*`（Validator FAIL 的 gate 中止後兩種入口續做） | CIA compare 的重做在 P6 的整合流程 |
| 附錄 A 1-37（索引表示） | 通過 | `test_new_index_fields_reject_float_representation`（waiver index、豁免項目行號、cited line、adopted side、basis_ref 索引的浮點寫法 → 結構錯誤、不拋例外、沒有錯誤 revision；bool、負數在 schema 層拒絕） | — |
| 附錄 A 1-37（豁免項目形狀） | 通過 | `test_waived_item_shape_errors_are_reported`（cited_at 為清單、字串、純量、缺欄位、pin 形狀錯、pin 的 content_hash 為清單、cited_at 與 pin 同時存在、waived 不是清單 → API 回結構錯誤；以仍 PENDING 的核准單走 CLI：非零結束、訊息指出 waived、沒有 traceback、持久檔案不變；cited_at 型與 pin 型的合法項目各用一張核准單仍可核准） | — |
| 附錄 A 1-19 | 通過 | `test_unavailable_reference_without_citation_stops_the_run`（沒有正文引用處 → G-SPEC FAIL、不持久化；列出正文引用處 → E3、開文件索取單） | — |
| AC-04-5 | 通過 | `test_ac_04_5_*`（CLI 與 API 都拒絕；附理由後記錄 kind、hash、理由） | — |
| AC-05-1 | 通過 | `test_p4_decisions.py::test_ac_05_1_2_*`（E2 critical、R3、DRAFT、conflict_resolution、核准單綁 revision、G-DESIGN 拒絕） | 真實 REQ-SITELIST-022 在 M1 |
| AC-05-2 | 通過 | 同上（核准 → 重新分析 → E1 none；ACTIVE；none／critical；resolution 與 side 1 PASS、side 0 FAIL；`adopted_side_index: null` 兩側都不能引用（函式層）） | 同上；CLR A4（INCORPORATED）在 P5 |
| AC-05-3 | 通過 | `test_ac_05_3_*`（Q01、Q02 E1、Q03 E4 minor；`rejection_contract.defined` false；只依賴 Q01 的 negative 不必 exploratory） | — |
| AC-05-4、11、12、15 | 通過 | `test_ac_05_4_x_combinations_each_fail`（X1～X18 各一例，訊息指出編號；X12 含 AC-05-11、12 兩例；同一 CLR、範圍涵蓋的正例 PASS）、`test_gspec_coverage_and_x_subconditions` | — |
| AC-05-5、6 | 通過 | `test_ac_05_5_6_13_*`（只開文件索取單＋等文件核准單；preflight 允許 OPEN 的文件索取單；A9 撤回；重開 T1；E4 critical → 新 spec_question 指回原單；退回後重跑不重複開單） | — |
| AC-05-7 | 通過 | `test_ac_05_7_*`（E5 minor、`possible_source_missing`；背景 CLR 當依據 → G-DESIGN FAIL；當 resolution → X16） | 真實 REQ-DAILYREPORT-001 在 M1 |
| AC-05-8 | 通過 | `test_ac_05_8_*` | — |
| AC-05-9 | 通過 | `test_ac_05_9_*`（沒有 applicability → X16；加入後 E1；side 0 PASS、side 1 FAIL） | 真實 REQ-DAILYREPORT-012 在 M1 |
| AC-05-10 | 通過 | `test_ac_05_5_6_13_*`（defer 拒絕、核准單維持 PENDING）、`test_preflight_checks_every_entry` | — |
| AC-05-13 | 通過 | `test_ac_05_5_6_13_*`（只有名稱相同、指向別的 question → X14） | — |
| AC-05-14 | 通過 | X13 在 `test_ac_05_4_*`；X15（條目 rationale 只有空白）在 `test_ac_05_14_*` | — |
| §3.5.2 64 組合 | 通過 | `test_64_legal_combinations_route_table`（函式層；統計 R1 44、R2 4、R3 4、R4 4、R5 2、R6 2、R7 1、R8 2、R9 1） | — |
| AC-06-1 | 通過 | `test_ac_05_1_2_*`（入口 B）、`test_ac_05_3_*`（入口 A）：12 個欄位逐欄等於來源決策點 | — |
| AC-08-2 | 通過 | 新產出見 P2；舊資料（沒有決策點）G-SPEC PASS：`test_legacy_requirement_and_derived_fields` | — |
| AC-08-6、17、27、38 | 通過 | X16 → G-SPEC FAIL、不是 E1：`test_ac_05_4_*`、`test_ac_05_7_background_clr_as_resolution_is_x16`、`test_ac_05_9_*` | — |
| AC-08-20、26、29 | 通過 | 範圍涵蓋或人工 applicability 後成為 E1：`test_ac_05_1_2_*`、`test_ac_05_9_*` | — |
| AC-08-9、12、13、33、34 | 通過 | 核准單 `resolutions[]` 由正式 approve 寫入：`test_ac_05_1_2_*`、`test_ac_05_14_*`、`test_waive_missing_entry_is_not_a_behaviour_decision` | — |
| AC-08-10 | 部分 | 派發包保存決議快照（`resolutions`、`run_decisions`），revision 記錄兩份快照的 hash | 舊 run 恢復時以快照比對的完整情境在 M1／P6 |
| AC-08-11 | 通過 | `test_ac_05_1_2_*` 的後段（CLR 新增 rev 1 → decision_revised、新 run 不跳過；沿用 rev 0 → G-SPEC FAIL，附錄 A 3-18） | — |
| AC-08-15 | 部分 | conflict 沒有 resolution → E2（`test_ac_05_1_2_*`） | 「不因日期較晚自動採用」是 Spec Analyst 的判斷，只能以契約要求 |
| AC-08-4 | 待 M1 | — | CLR-CASHFLOW-005 的真實資料 |
| AC-08-16、32 | 部分 | 同 P2 | DAILYREPORT 實際資料在 M1 |
| AC-09-12 | 通過 | `test_ac_05_1_2_*` 的後段（approval 包裝內的 CLR 也展開檢查） | — |
| AC-09-27 | 部分 | `test_p3_migrate.py::test_old_running_run_resumes_on_its_sidecar_revision`（移轉前就在跑的 spec-to-testcase run，T2、T3 的派發包都帶 sidecar 的 R000） | manual run 與 RR 的組合在 M1 |
| AC-09-33 | 通過 | `test_p4_flows.py::test_ac_09_33_*`（manual new → run new 綁最新 revision → dispatch → Draft 帶 decision_refs、SourceRef → gate → Validator → ACTIVATE；TC 版本帶 `requirement_model_revision`） | — |
| AC-09-28～30 | 部分 | CIA 的派發包帶全部 pin_groups：`test_cia_packet_carries_pin_groups`；契約與指示已更新 | 兩輪完整 CIA 與 legacy sidecar 混合在 P6 |

### P4 的實作說明（審查時請一併確認）

1. **模組**：派發包在新模組 `tools/qaos/dispatch.py`；決策點的檢查與推導（X1～X18、旗標、E1～E5、路由）在新模組 `tools/qaos/decisions.py`。G-SPEC 呼叫它檢查，`_apply_effects` 呼叫它推導並持久化。
2. **附錄 A 1-19（R，Oscar 2026-10-07 確認）**：E3 只由 `unavailable` 的未查參考構成、又沒有正文引用處時，G-SPEC FAIL、停下由人處理（重新讀取後取消 run 重新分析，或移除該引用宣告），不捏造引用處、不新增 pin 型文件項目。
3. **附錄 A 1-20～1-36**：派發包欄位與範圍、Validator 漏報、P4 的開單去重鍵、推導結果的保存、G-DESIGN 第 1 點的機械判斷、preflight 對所有條目的檢查、approval 型依據的 outcome、system 撤回的 kind 限制等定案。
4. **第 6 章提前的部分**：新資料的 RESOLVE_AMBIGUITY 核准不再 apply CLR；`waive_missing` 只做 A9（P4 沒有 fulfill，A8 與 `fulfill`、`waive-item` 在 P5）。A4（INCORPORATED）與 issue key 去重仍在 P5。
5. **既有測試**：helper 自動派發與填 `consulted_sources`（見上）。舊格式需求（沒有決策點）的行為不變，既有 WF 測試沒有改動斷言。
6. **agent 契約與指示**：spec-analyst、test-designer、test-validator、tc-risk-reviewer、change-impact-analyst 的契約版本升級，並更新對應的 `.claude/agents/qaos-*.md`（派發包、決策點、decision_refs、派發包範圍、pin_groups）。
7. **狀態機**：CLR 的 OPEN／ASKED → WITHDRAWN 拆成人（A10）與 system（A9，`kinds: [document_request]`）兩條；`state.check` 支援以 `kinds` 限定轉換。
8. **下游 iteration 的時點**（`1654b0b`）：被退回的下游 task 在下一次推進成 READY 時才進入新 iteration，不在自己的 gate 操作中改變，gate 的請求身分仍含 iteration（`ff21296` 曾把它拿掉，造成退回後對同一組 artifact 的重評被當成「已完成」，已還原）。需要派發包的 task，上一輪的產出不能在新一輪重新評估：`test_62` 的契約因此改變（原本固定「退回後不重新提交、直接 gate 舊 artifact 也會推進」），同一 iteration 內的重評另以 `test_62b` 固定（真正的 FAIL → READY → 不重新提交的第二次 gate）。
9. **審查修正（P4-01～05）**：附錄 A 1-37～1-40；1-19 經 Oscar 確認（停下由人處理，不新增 pin 型文件項目）。AC-04-4 的測試改用「合法但範圍外」的來源：Designer 派發時以 `--extra` 登記、Validator 派發包沒有登記的 spec。閉包外、未登記的 spec 在 G-DESIGN 就因 SourceRef 驗證失敗；沒有綁定決策點的 CLR、核准來源也在 G-DESIGN 被拒（P4R2-01），都不會走到 Validator。

## P5：開單關卡與 issue key 去重、CLR 生命週期（FIX-10）、ADR-010

- **執行 commit**：`3c00168d0e8f91c19c4567100d1c7ea107f25c30`（分支 `qaos/requirement-a`；P5 程式、schema、狀態機、ADR 與測試）。本紀錄所在的 commit 只改文件
- **環境**：同 P1
- **資料**：每個案例使用獨立的暫存 root。spec、引用、run、派發、提交、gate、核准、CLR 的開單／詢問／回答／適用紀錄／impact／apply／fulfill／waive-item 都走正式 API 或 CLI（`tests/p5_flow.py` 的 RA-P1～P3 共用流程）。第二個 product 以 `spec import --product other` 建立。故障恢復以 `QAOS_FAULT` 注入（明確標示）；標明「函式層」的子例直接呼叫內部函式
- **既有測試的配合**：入口 D（以人為 `--by`）的開單一律附 `--consulted` 或 `--no-source-check --reason`；`withdraw` 附 `--reason`；舊的 `clarification apply`（沒有 `--path`）改為 `--path a7`；舊資料的 RESOLVE_AMBIGUITY 核准後 CLR 維持 ANSWERED（`test_wf_z_*::test_20`、`test_20b`、`test_21` 依 ADR-010 改寫）；P4 範例 B 的 CLR 在重新分析採用後成為 INCORPORATED
- **結果**（2026-10-07，於上述 commit 執行）：`pytest tests/` 450 passed（快照與 commit 的程式、測試內容逐檔相同）；`tools/validate_phase1.py` ALL CHECKS PASSED
- **突變檢查**（在 scratchpad 的複本上逐一套用、跑對應測試，worktree 不變）：P5 原有 24 項、驗收補測 1 項（候選規則 (b)）、自審修正 25 項，全部被對應測試抓到（未突變的複本作為對照組全部通過）——開單關卡（agent 缺欄位、人工沒有查閱證據、legacy_e6 的驗證、coverage 完整）、去重（topic other、basis 不同、舊單 possible_duplicate）、A4（revision、BugDraft、只認最新 rev）、apply（缺結論、多餘結論、重複結論、結論格式、CANCELLED run、agent、不存在的目標、同時確認又延後、沒有關鍵字、scan 屬於別張 CLR、a7 的全部歷史、a6b 的 spec-to-bug／6-6／reject 決議、landed-in 的 run 範圍）、文件索取單（fulfill 的版本、cited_at.text 比對、waive-item 只能由人、A9 只計本張核准）、給人看的文件與未結案清單、G-SPEC 需求層 source_refs、G-BVAL 的 BugDraft 來源、目標解析的 X16（竄改）、stale-tcs 的目標
- **自審**：交 Codex 前以獨立 agent 找反例，發現 9 項（3 項 major：landed-in 沒有比對 run 的範圍、先以 waive-item 豁免再核准部分項目時誤判 A9、INCORPORATED 的 PM 回答從需求清單與審批頁消失；6 項 minor：`legacy_e6` 可繞過開單關卡、agent 開單的 coverage 只檢查非 None、同一張 TC 可給兩個結論、多項檢查沒有測試抓到、舊格式 CLR 的結案路徑（規格缺口）、stale-tcs 沒有沿用 (a)～(d)）。程式問題全部修正並補反例（`tests/test_p5_review_fixes.py`）；規格缺口寫入附錄 A 6-35（R）。沒有測試抓到的檢查中，A4「只認最新 rev」在 revision 路徑上會先被 G-SPEC 的 3-18 擋下（AC-08-11），屬防禦性檢查；目標解析的 X16 以標明「竄改」的子例驗證（正式流程沒有移除 applicability 的指令）

### AC 對照

| AC | 狀態 | 測試（tests/…） | 待 |
|---|---|---|---|
| AC-07-1、2、3、6 | 通過 | `test_p5_gate_dedupe.py::test_ac_07_1_2_3_6_*`（不同 subject、role_scope、同 topic 不同 subject → 各自新開；params 陣列排序去重、鍵順序無關 → 同一個 key） | — |
| AC-07-4、10、11 | 通過 | `test_ac_07_4_10_11_*`（topic `other` 一律新開並互標 possible_duplicate；同一請求中止後重送沿用計畫中的 ID；新請求新開） | — |
| AC-07-5 | 通過 | `test_ac_07_5_*`（重送 G-SPEC：入口 A、B 連結既有單、不重複開單，audit 有 LINK_CLARIFICATION） | — |
| AC-07-7、104 | 通過 | `test_ac_07_7_and_104_*`（只有 basis 不同 → 新開、`prior_version`；basis 也相同 → 連結） | — |
| AC-07-101～103 | 通過 | `test_ac_07_101_102_103_*`（agent 缺決策點欄位 → 拒絕；人工沒有查閱證據也沒有理由 → 拒絕；同需求已有沒有 key 的舊單 → possible_duplicate＋WARN_POSSIBLE_DUPLICATE） | — |
| AC-10A-1～3、42；AC-A-B1-1 | 通過 | `test_p5_lifecycle.py::test_ra_end_to_end_*`（每個停點斷言 ANSWERED → INCORPORATED → APPLIED） | — |
| AC-10A-4、5、10、18、29、41 | 通過 | 同上，在同一份狀態上的拒絕案例，CLR 檔 hash 不變 | — |
| AC-10A-6、62 | 通過 | `test_a5_old_run_and_stale_scan` | — |
| AC-10A-7、20～22 | 通過 | `test_p5_documents.py::test_fulfill_name_match_mapping_and_applied` | — |
| AC-10A-8、23～25 | 通過 | `test_one_document_two_items_and_revalidation`（以正式 `spec reference remove` 讓第一項失效） | — |
| AC-10A-9、36～38、40 | 通過 | `test_p5_paths.py::test_a7_paths`（approval 包裝、revision、TC 各一處引用都被列出） | — |
| AC-10A-39 | 部分 | `test_a7_paths` 以**現行** TC 版本的 `decision_refs` 驗證「全部歷史」的引用檢查 | SUPERSEDED 版本的專門案例在 P6 |
| AC-10A-11、32 | 通過 | `test_bug_flow_a4_and_a6`（有 SourceRef 的 BugDraft → A4 → a6 APPLIED；沒有 SourceRef → 不觸發 A4） | — |
| AC-10A-12 | 通過 | RA-P3（原題目標唯一、候選 (a)(c)(d) 都要結論）；(b) 在 `test_a5_old_run_and_stale_scan`、`test_two_targets_confirm_and_defer` | — |
| AC-10A-13、16、17、34 | 通過 | `test_two_targets_confirm_and_defer`（applicability 讓答案有兩個目標；只確認一個 → 拒絕；延後 → 通過；`show` 列出延後目標、`deferred` 與 `retire_planned` 的 TC，`updated` 不列） | — |
| AC-10A-14、47 | 待 P6 | — | 同 product、跨 area 的掃描範圍。跨 product 的單位分開掃描已由 AC-10A-50、51 驗證，同 product 另一個 area 尚未有專門案例 |
| AC-10A-15 | 部分 | 候選結論的檢查對所有目標一致：原題目標（AC-10A-4）、延後目標（AC-10A-66）都有反例 | 「已確認的第二個目標」的專門反例在 P6 |
| AC-10A-19 | 通過 | P4 `test_ac_05_9_*`（沒有 applicability → X16，不成為 E1，也不會成為採用目標） | — |
| AC-10A-26、27、30、58～61、63 | 通過 | `test_keyword_rules_and_scan_validation`、`test_no_keyword_reason_with_empty_scan` | — |
| AC-10A-28 | 部分 | apply 一律在鎖內重新掃描、landing 保存當下的版本與 sha256（`test_keyword_rules_*`） | 「scan 後 TC 被修訂」的專門案例在 P6 |
| AC-10A-31、43～45 | 通過 | `test_a6b_bug_reject_path`（舊 rev、普通 reject）、`test_s5_07_a6b_*`（條目不是 reject 決議）、`test_p5_review_r2_fixes.py::test_ac_10a_44_a6b_scope_mismatch_rejected`（scope 不符 → X16） | — |
| AC-10A-46 | 通過 | `test_a6b_reject_approval_is_not_a_wrapper_in_gspec` | — |
| AC-10A-33 | 通過 | `test_p5_misc.py::test_ac_10a_33_*` | — |
| AC-10A-35 | 通過 | `test_show_and_stale_tcs_readonly_while_locked` | — |
| AC-10A-48～51、64～66；AC-A-B1-17 | 通過 | `test_p5_cross_product.py::test_r1102_cross_product`（依 P2 → P3a → N2 → N1 → N3 → P5，每個反例後 CLR 檔 hash 不變） | — |
| AC-10A-52～56 | 通過 | `test_name_validity` | — |
| AC-10A-57 | 通過 | 見 P2 | — |
| AC-10A-67～69 | 通過 | `test_waive_item_and_approval_waive_interplay` | — |
| AC-A-B1-3（P5 的操作） | 通過 | `test_p5_resume.py`：submit_gate（含 A4）、apply a6、impact、apply a7、fulfill、waive-item、approve（含 A9），每種都以同請求重送與 `operation resume` 兩種入口續做；landing、掃描紀錄、fulfillment、WITHDRAWN 都只有一筆 | 其他操作類型與恢復表全部列在 P6 |
| 附錄 A 6-31（run 的範圍） | 通過 | `test_p5_review_fixes.py::test_s5_01_landed_in_run_scope`（spec-to-bug run 綁定的 revision 含目標、但 BugDraft 沒有採用 → 拒絕）、`test_s5_01_manual_run_scope`（函式層：manual run 只含本 run TC 的需求）；最終稿的身分見下方「Codex 審查修正」P5-01 | manual run 的完整 apply（要走到 T6 才 COMPLETED）在 P6 |
| 附錄 A 6-32（A9 的涵蓋範圍） | 通過 | `test_s5_02_*`（waive-item 豁免 D02、核准只列 D01 → APPLIED，不是 A9） | — |
| 給人看的文件 | 通過 | `test_s5_03_*`（INCORPORATED 時需求清單、ACTIVATE 審批頁仍顯示 PM 回答；未結案清單含 INCORPORATED） | — |
| 附錄 A 3-25、3-30 | 通過 | `test_s5_04_05_*`（legacy_e6 不帶需求、用在新格式需求、由人呼叫 → 拒絕；coverage 為空或型別錯 → 拒絕） | — |
| 附錄 A 6-33 與 apply 的輸入檢查 | 通過 | `test_s5_06_07_apply_input_checks`、`test_s5_07_a6b_*`、`test_s5_07_fulfill_version_and_cited_text_and_agent`、`test_s5_07_gate_source_refs`、`test_s5_07_bugdraft_old_rev_does_not_incorporate`、`test_s5_07_target_resolution_requires_x16`（竄改） | — |
| 附錄 A 6-34（stale-tcs） | 通過 | `test_s5_09_*`（A5 之後兩個需求上的 TC 都列為 stale_decision_ref＋target_requirement） | — |
| AC-A-B1-12 | 部分 | 上述 AC-10A-1～69 中標「通過」的項目 | 標「部分」「待 P6」的項目 |
| AC-A-B1-15 | 通過 | AC-10A-33～35 | — |
| AC-A-B1-16 | 通過 | A6（RA-P3）、A6b、A7 各走一次正式流程；a6b 帶 `--defer-target`、a7 帶 `--landed-in`／`--target`／`--defer-target` 都被拒絕（`test_a7_paths`、`test_a6b_bug_reject_path`） | — |

### P5 的實作說明（審查時請一併確認）

1. **模組**：CLR 生命週期（A4、目標解析、掃描、apply、fulfill、waive-item、最後判定、show、stale-tcs）在新模組 `tools/qaos/clr_lifecycle.py`；`clarification.py` 保留開單（關卡、issue key、去重）、ask、answer、withdraw、applicability。舊的 `impact`、`apply_`、`document_final_judgment`、`waive_items_by_approval` 移除或搬到新模組。
2. **核准不再 apply**（附錄 A 6-25）：P4 只對新資料停止 apply；P5 起新舊資料的 approve、override 都不 apply 任何 CLR。舊資料核准前「掛的 CLR 都必須已回答」的檢查保留。
3. **A4 的觸發位置**（附錄 A 6-22）：G-SPEC 持久化 revision 之後、G-BVAL 驗證 BugDraft 之後。同一份 revision 或 BugDraft 每張 CLR 只寫一筆 incorporated landing；APPLIED 後再被採用（A4'）只追加 landing、不改狀態。BugDraft 的 `source_refs`、`decision_refs` 是第一批選填欄位；Bug Analyst 的契約與指示沒有改（規格沒有列入），agent 不提供時不觸發 A4（ADR-010 限制 8）。
4. **開單關卡**（附錄 A 3-25、3-27）：舊格式需求的自動開單（入口 A、B 的舊路徑）以 `legacy_e6` 豁免決策點欄位；人工開單需要查閱證據或理由。
5. **掃描紀錄**（附錄 A 6-24）：`impact` 是寫入操作，掃描紀錄以全域 `SCAN-<ULID>` 命名；`--scan` 不能指向別張 CLR 的紀錄。
6. **撤回**（附錄 A 6-30）：A10 只能由人執行、`--reason` 必填；被撤回的 CLR 讓引用它的 revision 成為 `decision_revised`。
7. **自審修正**：landed-in 的 run 範圍（6-31）、A9 只計本張核准（6-32）、`req-export` 與審批頁改用 `ANSWERED_STATES`、未結案清單（`clarification list`、舊路徑的開單去重）含 INCORPORATED、`legacy_e6` 與 agent coverage 的驗證（3-25、3-30）、apply 輸入重複（6-33）、stale-tcs 的目標（6-34）。
8. **舊格式 CLR 的結案路徑**（附錄 A 6-35，R，請審查確認）：核准不再 apply 後，舊格式需求的 CLR 經重新分析轉為新格式並以 resolution 引用 → A4 → a6；系統不另開路徑。現存資料在 M1 預演確認。前置（二擇一，讓 X16 成立）：有 requirement_id、basis 相同、範圍一致 → 以 metadata upgrade 補齊自身範圍；basis 不同或沒有 requirement_id → 以 applicability `--confirm-basis` 確認（自帶範圍，不需要先補 metadata）；都不能確認 → 重新詢問或 A10（P5-R2-04 補充，見下方「Codex 審查修正」）。
9. **已知限制**：見 ADR-010。

### P5 Codex 審查修正

兩份 Codex 審查（審查 A 的 P5-01～03、審查 B 的 P5-R2-01～04）的修正。每項一個 commit，測試在 `tests/test_p5_review_r2_fixes.py`；狀態以正式流程建立，標明「函式層」的子例直接呼叫內部函式。

| 問題 | 修正 | 測試 |
|---|---|---|
| P5-01／P5-R2-01：最終 BugDraft／manual TestCaseDraft 以檔名排序挑選，退回重做後會選到仍為 VALID 的舊稿 | `_final_draft`：取產生者 task 本輪 `output_artifact_ids` 中的 VALID Draft，而且必須是本 run 最後一份 VALID 驗證報告審查的那份；對不上視為沒有最終稿。`_final_bugdraft`（spec-to-bug）與 `_run_scope`（manual）共用 | `test_p5_01_final_bugdraft_is_this_round_output`（正式流程：OPEN_BUG reject 重做、舊稿 ID 較大；只有舊稿採用 → a6 拒絕、CLR 不變；反方向新稿採用 → APPLIED）、`test_p5_01_manual_run_scope_after_override_reject`（函式層：FAIL ×3 → HUMAN_OVERRIDE reject 重做後，run 範圍取本輪 Draft）、`test_p5_01_final_draft_must_match_validator`（函式層：產出與報告對不上 → 沒有最終稿） |
| P5-02／P5-R2-03：去重命中時在 schema 驗證之前返回，無效的決策點欄位（level、coverage 的 enum 等）會變成連結 | `_check_request_shape`：去重之前以 schema 驗證完整的待開單輸入（ID、狀態以合法佔位值代入，不配號、不寫檔）；連結仍不寫回既有 CLR | `test_p5_02_dedupe_hit_still_validates_input`（同 key＋無效 level、無效 references_status、不同 key＋無效 level 都拒絕；沒有 LINK audit、既有 CLR hash 不變；同 key 合法輸入照常連結）；`test_p5_02_shape_checked_before_source_validation`（自審補充：形狀檢查排在來源與 pin 驗證之前，缺 content_hash、consulted 型別錯 → 關卡拒絕而不是 KeyError／TypeError；area 不合 ID 格式 → 訊息指向 area） |
| P5-03：無關鍵字結案後，stale-tcs 仍退回舊掃描的關鍵字 | 關鍵字取最近一次 applied landing（無關鍵字結案時為空集合）；完全沒有 applied landing 時才取最近一次掃描（6-19） | `test_p5_03_stale_tcs_keywords_follow_latest_applied_landing`（a7 以 no_keyword_reason 結案 → stale-tcs 不列背景命中的 TC；只有 impact、沒有 applied landing → 仍以掃描關鍵字列出） |
| P5-R2-04：6-35 的舊格式結案方案漏列 X16 的前置（自身範圍、basis） | 附錄 A 6-35 補明前置（二擇一）：(1) 有 requirement_id、basis 相同、範圍一致 → metadata upgrade 補齊；(2) basis 不同或沒有 requirement_id → applicability `--confirm-basis`（自帶範圍，不需要先做 (1)）；(3) 都不能確認 → 重新詢問或 A10；M1 逐單記錄。程式不變，X16 不放寬 | `test_p5_r2_04_legacy_e6_close_requires_scope`（E6 自動單 → 核准仍 ANSWERED → 直接引用 X16 FAIL → metadata upgrade → PASS、INCORPORATED → a6 APPLIED）、`test_p5_r2_04_legacy_e6_basis_change_requires_applicability`（答案之後新增 normative 引用 → 只補 metadata 仍 X16 FAIL → applicability 後 PASS）、`test_p5_r2_04_legacy_e6_applicability_alone`（自審補充：不做 metadata upgrade、只靠 applicability 也成立）。移轉 rev 0 的現存資料在 M1 預演 |
| P5-R2-02：(d) 關鍵字只比對 steps 的 action，漏掉 `steps[].expected` | 2026-10-07 Oscar 決定採納：比對 steps 的 action 與 expected；附錄 A 6-16 改列 R、ADR-010 Decision 1 註明；`RULE_VERSION` 升為 "2"（"1" 的掃描只沿用關鍵字）。調查：真實資料 499 張 ACTIVE TC 沒有 steps[].expected，7 張 CLR 的 24 組歷史關鍵字重跑候選差異 0 | `test_p5_r2_02_keyword_matches_step_expected`（只在 steps[].expected 命中的 TC 成為候選；缺結論 → 拒絕、CLR 不變；補結論 → APPLIED，landing 的 rule_version 為 "2"） |
| 審查 A 的驗收建議（逐項核實後調整） | AC-10A-34 原測試沒有 `retire_planned` → 補一張 retire_planned 的 TC 並斷言 `show`；AC-10A-44 原測試沒有 scope 不符的子例 → 補反例（突變對照：移除 X16 檢查後該測試失敗）；`test_s5_07_bugdraft_old_rev_does_not_incorporate` 原本捕捉 AssertionError，任何更早的失敗都會綠燈 → 改為要求 G-BVAL PASS（突變對照：A4 不比對 rev 時該測試失敗）；`test_p5_resume.py` 的 apply 中止點註解更正為「CLR YAML（狀態與 landing 一起寫出）寫出之後」。AC-A-B1-15 隨 AC-10A-34 維持通過 | `test_two_targets_confirm_and_defer`、`test_ac_10a_44_a6b_scope_mismatch_rejected`、`test_s5_07_bugdraft_old_rev_does_not_incorporate` |

**移到 P6（2026-10-07 Oscar 決定）**：
- 自審 F1：G-BVAL／G-TVAL 不檢查 Validator 報告審查的 Draft 是否為產生者本輪產出；agent 送審舊稿時 `_final_draft` 為 None（fail-closed，不會讓舊稿成為落地證據，但正式 Bug／TC 與落地判定所看的 Draft 不一致）。P6 在 gate 加檢查並補正式流程測試。
- 自審 F5：spec-to-bug 的 Bug 被 REJECTED（CONFIRM_DUPLICATE、RESOLVE_AMBIGUITY reject）但 run COMPLETED 時，最終 BugDraft 仍可作為 a6 的 landed-in。決定：排除，這類情況改走 a6b 或其他 run；P6 補附錄 A 定案、程式與測試。

## P6：整合驗收

- **執行 commit**：`b1983279d6c55f2077d29edf0aaadcd4720388de`（分支 `qaos/requirement-a`；階段基準 `1e1ca11`；`7abf703` 併入 `origin/main` `f5188b0`，含 MR !7 與 2026-10-02～05 的業務資料 commit）。本紀錄所在的 commit 只改文件
- **環境**：同 P1
- **資料**：測試 root 一律以正式流程建立（legacy 資料由 base `2e01d4b` 的舊程式以自己的正式流程產生）；故障以 `QAOS_FAULT` 注入、同步以 `QAOS_PAUSE`。AC-A-B1-4 的預演用 `tests/p6_rehearsal.py`，資料來源是 `git archive 7ef07ee`（tree `cb9e6258`，4617 檔，唯讀，執行前後逐檔 shasum 相同），**不是正式 M1**（M1 用部署當天主資料夾的資料、含第二份工作複本的故障演練，需 Oscar 授權）
- **結果**：見本段最後「執行結果」
- **突變檢查**：在 scratchpad 的複本上逐一套用、跑對應測試——F1、F5 共 2 組，G1 15 組（14 組抓到；未抓到的「拿掉已有標記就拒絕 migrate」另有准入的兩道防護，屬多重防護），G2 24 組、G3 10 組、G4 16 組全部抓到

### P6 的修正

| 編號 | 問題 | 修正 | 測試 |
|---|---|---|---|
| F1（附錄 A 6-36） | G-TVAL／G-BVAL 不核對 Validator 報告審查的 Draft 是否為產生者本輪產出；語意 FAIL 退回不清空產生者的 `output_artifact_ids`（舊稿改 SUPERSEDED 留在清單），submit 的引用檢查只看 `references`，payload 指向舊稿的報告可以通過 | `gates.reviewed_draft_issues`：必須在產生者本輪 `output_artifact_ids` 中、型別相符、VALID；否則 Structural FAIL | `test_p6_f1_f5.py::test_f1_*`（TC：references 指新稿、payload 審舊稿；Bug：OPEN_BUG reject 後舊稿仍 VALID；函式層：非 Draft、沒有產生者） |
| F5（附錄 A 6-37） | Bug 已 REJECTED 的 spec-to-bug run 仍可作為 a6 的 landed-in | `clr_lifecycle.bug_rejected`；最終 BugDraft 為 None；a6 明確拒絕並提示 a6b | `test_f5_*`（CONFIRM_DUPLICATE、RESOLVE_AMBIGUITY reject；對照組 Bug 成立的 run → APPLIED） |
| P6-S00-01 | spec-change-impact 判定 NO_IMPACT 時，`_advance` 對已標 DONE 的 T2 做 DONE → READY 而崩潰（base 就有；需求 A 的同版本 CIA 最常走到） | NO_IMPACT 分支從最後一個略過的 task 之後推進 | `test_p6_cia_manual_flows.py::test_p6_g3_same_version_cia_no_impact_completes` |
| P6-S00-02 | T5 證據衝突報告沒有列出步驟，每列印「記錄值 None，目前值 None」 | `migrate._report` 列出步驟與 seq；沒有記錄值時不印 | `test_p6_migrate_residual.py::test_ac_09_73_t5_report_names_the_step` |
| P6-S00-03（附錄 A 5-15） | AC-09-85 ⑤「不執行檢查 A」與 §13.7 續做表矛盾 | AC 依續做表更正 | `test_ac_09_85_terminal_phase[partial_after_check_b-*]` |
| P6-S00-05 | AC-08-10 原本只有函式層與派發包快照的證據 | 補正式流程測試 | `test_p6_s00_fixes.py::test_ac_08_10_*` |
| P6-S00-06 | `test_ac_09_73_74_t5_refuses_with_report` 有永遠成立的替代斷言 | 改為斷言「步驟 <step_id>」 | 同左 |
| P6-S00-07 | F5 的拒絕訊息對 CONFIRM_DUPLICATE 的 run 也提示 a6b（a6b 對它必拒） | 依 `duplicate_of` 分兩種提示；`resolve_targets` 也略過 REJECTED 的 run（防禦性，正式入口由 a6 的拒絕先擋下） | `test_f5_*` |
| P6-C01-01 | G-COMPARE 只檢查逐列欄位，不核對比較範圍與 Draft 身分：漏列 affected TC、引用非本輪 draft_id 的報告仍 PASS，APPLY_CHANGE 會啟用沒有被比較的版本 | `gates._compare_coverage_issues`：以本 run 本輪有效的 CIR 與 G-TVAL 審過的 Draft 核對——affected／obsolete 的 TC 恰好比較一次且 `old_version` 等於 `active_version`；`new_draft_id` 屬於該 Draft、Draft 的每張 TC 恰好比較一次；取代關係與版本相符、新 TC 為 added；`change_impact_id` 相符。只核對身分與集合，不判斷 diff 語意 | `test_p6_c01_fixes.py::test_c01_01_*`（漏列、非本輪 draft_id、取代關係錯、old_version 錯 → Structural FAIL、不建立 APPLY_CHANGE；合法 → PASS） |
| P6-C01-03（附錄 A 6-38） | AC-A-B1-4「全部 schema PASS」照字面不成立（14 檔失敗，全部是移轉前既有資料或其逐位元複本） | Oscar 2026-10-08 決定：AC 改為 baseline 比對（新增修改檔 PASS、R000 只繼承原檔失敗、不新增其他失敗），附錄 A 6-38 列出 14 檔清單與規則，2 個歷史 CIR 列入 baseline、不放寬 CIR schema；預演腳本依此檢查 | `tests/p6_rehearsal.py`（三種模式） |
| P6-C02-01 | 附錄 A 6-38 (4) 的「（屬 untouched）」與移轉清單的正式分類不符（12 個歷史 artifact 不在 `untouched` 清單，實際以逐檔內容比對確認） | 改為「以移轉前後逐檔內容比對確認；不要求列在 `untouched` 類別」 | — |
| P6-S02-01～03 | 預演報告沒記錄程式版本；6-38 的「baseline」同時指移轉前與移轉後兩個集合；(4) 抓不到 baseline 檔被刪除 | 報告記錄 `--code-commit`；6-38 區分「移轉前 baseline」與「移轉後預期失敗清單」並註明只涵蓋有 schema 的檔案；(4) 納入刪除 | `tests/p6_rehearsal.py`（三種模式重跑） |
| P6-S01-01 | G-COMPARE 仍放行「本輪 Draft 取代 CIR 判定 unaffected 的 TC」，APPLY_CHANGE 會含未被判定受影響的 TC | Draft 取代的 TC 必須在 CIR 的 affected／obsolete 中；G-TVAL 審過的 Draft 檔不存在時直接 FAIL | `test_c01_01_*[extra_unaffected]` |
| P6-S01-02 | AC-A-B1-7 列記錄的程式 commit 不含所用的腳本 | 改記實際組成，並記乾淨匯出目錄的重跑結果 | — |
| P6-C01-02 | AC-A-B1-7 規定在同一個 root 依序驗收，原本的證據分散在三個不同的 root | 補同一份工作複本的連續流程（見 AC-A-B1-7 列） | `tests/p6_rehearsal.py --mode ac-b1-7` |
| P6-C01-04 | 恢復矩陣的紀錄寫成「每種操作 × 兩種入口 × 每個中止點」，強於實際證據 | 紀錄改寫為實際範圍（逐點循環、FP-W 兩種入口交替分擔、指定代表點） | — |
| merge | MR !7 的獨立 root 測試在需求 A 下是 `S_pre`，spec import 被拒 | 子程序內先走 maintenance start → migrate → maintenance end | `test_wf_zzzz_bug_override.py` |

### 前面階段「部分」「待」項目的結清

| AC | P6 測試（tests/…） | 結果 |
|---|---|---|
| AC-07-9e～9j、9x、9y、9aa、9ab | `test_p6_resume_matrix.py::test_9e_to_9j_*`、`test_9h_*`、`test_apply_a6_every_point`、`test_apply_a6b_every_point`、`test_9y_*`、`test_9aa_*`、`test_9ab_*` | 通過 |
| AC-07-10、1～7、11、101～104 | P5 已通過（見 P5 段） | 通過 |
| AC-07-13～18（op-P1／P2、op-N1～N6） | `test_op_p1_p2_*`、`test_op_n1_n2_*`、`test_op_n3_n4_n5_apply`、`test_op_n6_*` | 通過 |
| AC-07-22～29（中止加續做） | `test_p6_resume_matrix.py` 的逐點循環（`apply_every_point`）：G-SPEC 與 G-TVAL 的 submit_gate、submit_gate 含 A4、approve 含 A9、impact、apply a6／a6b／a7、fulfill、waive-item、spec 與 clarification 的 metadata upgrade、applicability_add。每項的 FP-P1（計畫保存後）、FP-P2（登錄後）、9k（completed 之前）以兩種入口各做一次；FP-W（每一步輸出之後）由兩種入口**交替分擔**（奇數步驟同請求重送、偶數步驟 `operation resume`），每一步至少一次；另有指定點兩種入口都做（9h 的第一張 TC 版本之後、9y 的掃描紀錄之前）。**指定代表點**：ACTIVATE 的 approve／complete_run 只在第 2 步輸出之後中止、兩種入口各一次；migrate 為 FP-M0～M5 各點 × 兩種入口（`test_migrate_x_abort_points_then_resume`）；P1 的 `test_types_*`（run new、submit_gate、approve、complete_run、cancel_run、寫檔 export、audit render）各在指定代表中止點驗證；其餘見 P1、P3 | 通過（範圍如左；不是「全部操作 × 全部中止點 × 兩種入口」的笛卡兒積） |
| AC-07-44 | `test_p6_clr_residual.py::test_ac_07_44_*`、`test_p6_migrate_residual.py::test_ac_09_50_*`（逐位元比對 render） | 通過 |
| AC-07-80、82、83 | `test_p6_migrate_residual.py::test_ac_07_80_82_*`；83 已由 `test_p3_migrate.py::test_rollback_abort_points_then_resume` 涵蓋 | 通過 |
| AC-07-90～93 | `test_p6_resume_matrix.py::test_migrate_x_abort_points_then_resume`、`test_ac_07_92_*`、`test_ac_07_93_*` | 通過 |
| AC-08-4、16、32 | 快照預演：CLR-CASHFLOW-005 rev 0 的 SourceRef 驗證通過、X16 依 6-35 FAIL（函式層）；CLR-DAILYREPORT-010 rev 0 的 basis | 部分；完整驗證需 DAILYREPORT 0.3（M1）。AC-08-16 寫 REQ-DAILYREPORT-012，資料中為 011，待 Oscar 確認 |
| AC-08-10 | `test_p6_s00_fixes.py::test_ac_08_10_old_run_keeps_pinned_answer_rev_after_new_answer`（revision 以 rev 0 為 resolution → PM 再回答追加 rev 1 → 舊 run 以釘選的 rev 0 設計、驗證、ACTIVATE → COMPLETED；改引用 rev 1 → G-DESIGN FAIL） | 通過 |
| AC-09-27 | 快照預演：RUN-20261002-001 續做的派發包仍帶 sidecar 的 R000（AC-09-3／20） | 通過（manual 與 RR 的真實組合待 M1） |
| AC-09-3、20 | 快照預演（work1） | 通過；AC-09-20 的 WAITING_HUMAN testcase-revision run 快照中不存在，待 M1 |
| AC-09-11 | 快照預演：SITELIST 0.6 不跳過；DAILYREPORT 0.2 跳過並 WARN_LEGACY_SKIP | 通過 |
| AC-09-14 | `test_p6_migrate_residual.py::test_ac_09_14_*` | 通過 |
| AC-09-15 | `test_p6_cia_manual_flows.py::test_ac_09_15_*`（PLATFORMRULE 形狀的測試 spec） | 通過（真實 PLATFORMRULE 0.2 未驗） |
| AC-09-17、32 | `test_ac_09_17_32_cancel_run_with_several_pending_approvals`（第二張 PENDING 以故障注入建立）；快照預演：RUN-20261002-001 cancel、新 0.4→0.7 run 不綁 0.6 | 通過 |
| AC-09-18、19 | P5 RA 流程（`test_p5_lifecycle.py`） | 通過 |
| AC-09-24、66、67 | 快照預演：新 regression-generation run 不綁 revision（24） | 部分；快照沒有既有 regression-generation run、沒有缺 audit.log 的 run 與缺 render 的 CLR，待 M1 |
| AC-09-28～31、AC-A-B1-7 | `test_ac_09_28_29_30_two_rounds_*`（含 legacy R000 混合、G2＋G5、G4 反例）；快照預演：DAILYREPORT 96 條分 0.1／0.2 各 48 → PASS、只判一組 → G2、G5 FAIL（函式層 g_impact） | 通過（真實 0.3 的正式 CIA 待 M1） |
| AC-09-45、47、48、50 | `test_p6_migrate_residual.py::test_ac_09_45_*`、`_47_*`、`_48_*`、`_50_*` | 通過 |
| AC-09-58、79、81 | `test_ac_09_81_58_*`、`test_ac_09_79_*` | 通過 |
| AC-09-73、74、76 | `test_ac_09_73_74_*`、`test_ac_09_73_t5_report_names_the_step`、`test_ac_09_74_3_*`、`test_ac_09_76_*` | 通過 |
| AC-09-82 ④ | `test_ac_09_82_4_*` | 通過 |
| AC-09-83、84、85 | `test_ac_09_83_*`、`test_ac_09_84_*`、`test_ac_09_85_*`（84 ⑥ 為函式層，屬防禦性） | 通過 |
| migrate verify（§12） | `test_verify_after_migrate_each_category`、`test_verify_after_rollback_each_category`、`test_verify_after_partial_rollback_*` | 通過 |
| AC-09-89 (b) | `test_ac_09_89_b_*` | 通過 |
| AC-09-64 | — | 待 M1（以舊程式驗證 R5） |
| AC-10A-14、47 | `test_p6_clr_residual.py::test_ac_10a_14_47_same_product_cross_area` | 通過 |
| AC-10A-15 | `test_ac_10a_15_confirmed_second_target_stale_tc` | 通過 |
| AC-10A-28 | `test_ac_10a_28_candidate_revised_after_scan` | 通過 |
| AC-10A-39 | `test_ac_10a_39_superseded_version_counts_as_history`（正式流程中 SUPERSEDED 版本無法成為唯一引用處，以拒絕訊息列出 SUPERSEDED 版本並以突變驗證） | 通過 |
| 附錄 A 6-31（manual 的完整 apply）、AC-A-B1-8 | `test_p6_cia_manual_flows.py::test_ac_a_b1_8_manual_full_flow_then_a6_landed_in` | 通過 |
| 附錄 A 1-39（CIA compare 重做） | `test_appendix_a_1_39_cia_compare_redo_iterations_and_packets` | 通過 |
| 附錄 A 6-35（現存舊格式 CLR） | 快照預演：現存 ANSWERED 的舊格式 CLR 為 0 張；之後回答時會遇到的 OPEN／ASKED 舊格式單 10 張（CLR-CASHFLOW-001、002、007，CLR-DAILYREPORT-011、014，CLR-SITELIST-013～017） | 通過（M1 依當天資料重列） |

### 第一批整體驗收 AC-A-B1-1～17

| AC | 測試 | 結果 |
|---|---|---|
| 1 | `test_p5_lifecycle.py::test_ra_end_to_end_*`、`test_p6_clr_residual.py::test_ac_a_b1_1_every_stop_asserts_clr_state` | 通過 |
| 2 | `test_p1_resume.py::test_validation_failure_writes_only_diagnostics`、`test_p1_review_fixes.py::test_p1_05_*` | 通過 |
| 3 | `test_p6_resume_matrix.py`（逐點循環、兩種入口交替分擔 FP-W、指定代表點，範圍見 AC-07-22～29 列）＋ P1、P3、P5 的恢復測試 | 通過 |
| 4 | `tests/p6_rehearsal.py`（三種處理方式各一份工作複本）：R000 hash、`_skip`（SITELIST 0.6 false）、RUN-20261002-001 sidecar、RUN-20260914-001 三種處理方式、TC sidecar 96／44／57、CLR rev 0（42 張）、`audit.legacy.log`（92 份）、untouched 全部吻合；rollback、`--new-request` 重新移轉、verify 都通過；schema 依附錄 A 6-38：移轉新增或修改的檔案（R000 除外）全部 PASS、失敗的 R000 都是原檔逐位元複本、失敗集合 ⊆ 移轉前 baseline ∪ 繼承的 R000、移轉前 baseline 的檔案沒有被修改或刪除、失敗集合等於 6-38 的移轉後預期失敗清單（14 檔；只涵蓋有 schema 的檔案）。程式 `1b9c1e4`（`git archive` 匯出；報告的 `code_commit` 記錄此值），資料快照 `git archive 3a62d87`（來源前後 sha256 相同）；acknowledge-idle 36 項、cancel-run 31 項、pre-cancel 28 項全部 PASS | 通過 |
| 5 | 本段「執行結果」（610 passed、validate_phase1 ALL CHECKS PASSED） | 通過 |
| 6 | `test_ac_a_b1_6_s1_q_to_s3_first_batch_commands_only` | 通過 |
| 7 | `tests/p6_rehearsal.py --mode ac-b1-7`（`tests/p6_acb17_flow.py`）：在**同一份工作複本**依序執行——移轉（acknowledge-idle）後 DAILYREPORT 96 張候選＝0.1 R000 48＋0.2 R000 48（legacy sidecar）；第 1 輪 0.2 R000→R001（declare-empty 造成 declaration_changed）：G-IMPACT 兩組 48／48 PASS，affected 3 張走 T2、T3、T3RR、T4 → APPLY_CHANGE → APPLIED、COMPLETED，unaffected 的版本與 sidecar 逐位元不變；第 2 輪 R001→R002（from 為第 1 輪的 R001）：只判 from 端一組 → G2、G5 FAIL，正確 CIR 三組（0.1 R000、0.2 R000、0.2 R001）PASS、R000 組的 diff 涵蓋 R001 的變更 → APPLIED；第 3 輪以 AC-09-35～41（另加 G7、G8）各一份錯誤 CIR 送同一個 T1，各自 FAIL 在對應檢查、task 回 READY，最後正確 CIR → NO_IMPACT → COMPLETED。40 項檢查全部 PASS（程式為 `0271c69` 的 `tools/` 加上之後於 `d49a2af` commit 的兩個腳本；另於 `git archive cb8ce05` 的乾淨匯出目錄重跑 40／40 PASS；資料快照 `git archive 3a62d87`，來源前後 sha256 相同）；突變對照：G2、G4 失效時對應步驟失敗 | 通過（同版本 CIA；快照沒有 0.3，AC-09-31 的 0.2→0.3 跨版本情境待 M1） |
| 8 | 見附錄 A 6-31 列 | 通過 |
| 9 | `test_p2_sources.py::test_ac_08_27_28_*`、`test_ac_08_30_*`、`test_p6_clr_residual.py::test_ac_a_b1_9_effective_basis_in_formal_flow` | 通過（AC-08-32 真實資料見上） |
| 10 | `test_p1_audit.py` 各案例、AC-07-44 列 | 通過 |
| 11 | `test_p1_lock_fork.py`、`validate_phase1` [4] | 通過 |
| 12 | AC-10A-1～69（P5 段＋本段）、`test_ac_10a_36_ra_p7_background_candidates` | 通過 |
| 13 | `test_ac_a_b1_13_approval_table_activate[1,2,3,4a,4b]`、`test_ac_a_b1_13_row3_apply_change` | 通過 |
| 14 | `test_p1_lock_fork.py::test_64_70_72_*`、`test_p1_misc.py::test_75_*`、`test_76_*` | 通過 |
| 15 | AC-10A-33～35 | 通過 |
| 16 | `test_ra_end_to_end_*`、`test_a6b_bug_reject_path`、`test_a7_paths`、`test_ac_10a_36_*` | 通過 |
| 17 | `test_p5_cross_product.py::test_r1102_cross_product` | 通過 |

### 仍需正式 M1 或 Oscar 決定的項目

- **M1**：部署當天重新讀取主資料夾的業務現況（含 9/18 未追蹤的 run、執行紀錄與證據）後重做預演；第二份工作複本的故障演練（FP-M2、M3、R0、W、P1）；AC-09-20、24、64、66、67；AC-08-16、32 的完整驗證（需 DAILYREPORT 0.3）；真實 PLATFORMRULE 0.2 與 DAILYREPORT 0.3 的正式 CIA；依附錄 A 5-10 以當天真實 ID 驗收；AC-08-16 的需求 ID（AC 寫 REQ-DAILYREPORT-012，資料中為 011）以 M1 的實際對象驗證；M1 以當天資料重新計算附錄 A 6-38 的 baseline，與清單不同時停下交 Oscar
- **之後的需求議題**（Oscar 2026-10-08：先維持現行做法）：ARCADE 0.7 有 1 條 RETIRED 需求，依「最新 revision 有非 ACTIVE 需求」規則，移轉後 9 條 ACTIVE TC 不能直接 testcase-revision；是否改為只擋 DRAFT 另議
- **觀察**（不是本階段缺陷，列給審查參考）：G7 不檢查 `requirement_diff` 的 change 標記是否正確；G-COMPARE 不檢查 `new_draft_id` 是否為本輪 Draft、是否每張 affected TC 都有比對（與 6-36 同類）

### 執行結果

2026-10-08，於 `b198327` 以 `git archive` 匯出的乾淨目錄執行：

- `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q tests`：**610 passed**（17:29）。P5 收斂時 461 → merge MR !7 後 462 → P6 新增 148
- `python3 tools/validate_phase1.py`：**ALL CHECKS PASSED**（含 [4] fork 使用為零）
- 中途紀錄：`e761727`（merge 後）462 passed、`7ef07ee`（F1、F5 後）467 passed、`7279e29`（收尾測試後）609 passed，validate 都通過
- 自審：交審前以獨立 agent 找反例，提出 4 項（AC-A-B1-5 缺執行結果、AC-08-10 證據不對題、一條永遠成立的測試斷言、F5 拒絕訊息對確認重複的 run 提示 a6b），都已修正（見「P6 的修正」）
