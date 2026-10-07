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

- **執行 commit**：`4a84069b86d805829509e215d5e6e97e2833fba2`（分支 `qaos/requirement-a`；P3 程式為 `7430b7d`、`282b401`、`982ffe2`、`74de040`，P3 程式碼審查 P3-01～06 的修正為 `4a84069`）。本紀錄所在的 commit 只改文件
- **環境**：同 P1
- **資料**：每個案例使用獨立的暫存 root。新程式的狀態以正式流程建立（`tests/p3_flow.py`：new_run、submit、gate、approve）；移轉用的 legacy 資料由**需求 A 之前的程式**（base `2e01d4b`，以 `git archive` 匯出到系統暫存目錄，唯讀）以它自己的正式流程產生（`tests/p3_legacy.py`）。標明「竄改」「故障注入」「模擬經授權的人工修復」的子例才在流程後修改檔案。CIA 的 G1～G8 以正式流程產生的兩批候選 TC（分屬 R001、R002）搭配記憶體中的 run 與 CIR 驗證（CIA agent 新契約在 P4）
- **結果**（2026-10-07，於上述 commit 執行）：`pytest tests/` 366 passed；`tools/validate_phase1.py` ALL CHECKS PASSED
- **突變檢查**：拿掉 `_skip` 的第 2、3 條與無 T0 流程的過時檢查時，5 個相關測試失敗；把 P3-01～06 的修正退回時，對應的 7 個反例全部失敗；之後都還原

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
| AC-09-83、84 | 部分 | `test_check_a_and_b_stop_on_external_change_then_repair`（③ 檢查 A、④ 檢查 B，含修復後完成）、`test_p3_02_*`（R 已凍結的 X 完成紀錄被刪 → 檢查 A 停止，兩種入口） | ①②、⑤～⑦ 在 P6 |
| AC-09-85 | 部分 | `test_ac_09_85_terminal_inconsistency_blocks_all_writes`（⑥ 防禦性） | ①～⑤ 的逐點斷言在 P6 |
| migrate verify（§12） | 部分 | `test_p3_03_verify_detects_missing_or_tampered_evidence`（移轉後缺 X 完成紀錄、回復後 R 事件竄改、回復後缺 X 完成紀錄 → 失敗並列出路徑；恢復後通過） | 其餘各類的逐項負例在 P6 |
| AC-09-88 | 通過 | `test_migrate_acknowledge_idle_results`、`test_ac_09_88_legacy_r000_skip_rule_and_89_declaration` | — |
| AC-09-89 | 部分 | 同上（a） | (b) 舊 run 依固定 pin 續做在 P6 |
| AC-09-91 | 通過 | `test_ac_09_91_declarations_before_migration_refuse`（兩例，防禦性） | — |
| AC-07-90～93 | 部分 | `test_rollback_after_partial_migration`、`test_rollback_abort_points_then_resume` | FP 表逐點彙整在 P6 |
| AC-07-28（migrate、rollback 的中止加續做） | 部分 | 同上 | metadata upgrade 的中止續做在 P6 |

### P3 的實作說明（審查時請一併確認）

1. **模組**：revision 與綁定在新模組 `tools/qaos/rm.py`（第 5 章 §16 原寫 `store.py`）；移轉、回復、verify 在新模組 `tools/qaos/migrate.py`。
2. **附錄 A 5-12（R，待 Oscar 確認）**：CLR 的 spec 版本沒有匯入時跳過 rev 0 並記為例外。
3. **附錄 A 5-13（R）**：T7 接受 `audit.log` 的正常重新 render，否則回復點之後任何操作（含維護開關）都會讓回復永遠被拒。
4. **附錄 A 5-14（I）**：實作補充的定義（revision 編號、run 欄位、`legacy_binding`、清單中的循環項目、`untouched` 範圍、R 的事件等）。
5. **既有測試配合新規則**：manual run 必須有 spec（第 5 章 §4.3），兩個 ADR-009 的 manual 測試改為有 spec 或驗證拒絕；gate 單元測試的需求模型改經 `save_requirements` 建立（需求 ID 改成符合 schema 的格式）；test_15 的 CIR 加上兩端 revision 與 pin_groups。
6. **被接管的計畫**：被未完成 R 接管的 X，即使已完成，對它的請求（重送、`operation resume`）也拒絕並提示續做 R（第 5 章 §13.10）。
7. **agent 指示**：CIA 的 pin_groups 只改了 schema 與 gate；change-impact-analyst 的契約與指示依 D7 在 P4 更新。整個需求 A 是同一個 MR，P3 與 P4 之間沒有部署空窗。
8. **AC-09-50 等未測項目**：舊程式的 legacy fixture 沒有「有 PENDING APR 的 RUNNING run」等資料；這些在 M1 預演（真實資料的唯讀複本）或 P6 驗收，已在上表標「待」。
9. **顯示端的退回**：核准單渲染、final export 只有在移轉前（沒有移轉標記）的 legacy 資料缺 pin 時，才改用最新 revision 顯示；移轉後缺 pin 一律報錯。
10. **`migrate verify`（移轉後）**：由 X 的不可變計畫逐步核對，所以要在移轉剛完成、離開維護之前執行（第 5 章 §15 M3）；之後的操作會重新 render audit.log，屬正常變動。
