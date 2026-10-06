# 需求 A 驗收紀錄

依 `requirement-a-final.md` §0.2 分階段記錄：每條 AC 的驗收階段、測試、執行時的 commit 與結果。
早期階段只驗收能獨立驗證的部分；還不能執行的標「待 Pn」，於 P6 結清。

## P1：executor 基礎設施

- **執行 commit**：`04f29bf18f449340a85f9d529151434ce14d9a3a`（分支 `qaos/requirement-a`；含 P1 程式碼審查 P1-01～P1-06 的修正）
- **環境**：macOS（Darwin 24.6）、Python 3.11.0、本機 APFS
- **資料**：每個 P1 案例使用獨立的暫存 root（只複製 schemas、agents、workflows、permissions），以正式流程建立狀態；故障以 `QAOS_FAULT` 注入、同步以 `QAOS_PAUSE` 暫停點完成。沒有使用 repo 的業務資料。
- **結果**：`pytest tests/` 170 passed；`tools/validate_phase1.py` ALL CHECKS PASSED（含 [4] fork 使用為零）

### 狀態說明

- **通過**：P1 已完整驗收。
- **部分**：P1 驗收了通用機制或部分情境，其餘列在「待」欄。
- **待 Pn**：依賴後續階段的功能，該階段完成時驗收。
- **撤銷**：依最終規格附錄 A 撤銷。

### AC 對照

| AC | 狀態 | 測試（tests/…） | 待 |
|---|---|---|---|
| AC-07-8 | 通過 | `test_p1_resume.py::test_validation_failure_writes_only_diagnostics`、`test_p1_review_fixes.py::test_p1_05_three_structural_failures_only_diagnostics`（連續 3 次） | — |
| AC-07-9a | 通過 | 同上 | — |
| AC-07-9b | 通過 | `test_p1_resume.py::test_crash_before_plan_save_leaves_nothing`、`test_p1_review_fixes.py::test_p1_06_residue_before_plan_save_is_cleaned`（故障、SIGKILL；完整快照不排除任何目錄） | — |
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
| AC-07-47 | 通過 | `test_p1_audit.py::test_47_frozen_legacy_deleted_render_refused`、`test_p1_review_fixes.py::test_p1_04_*`（全域紀錄缺漏、未知值、舊 run 缺紀錄；檢視不變且不建計畫；新 run 正常） | — |
| AC-07-48 | 通過 | `test_p1_audit.py::test_48_new_run_after_migration_uses_events_only` | — |
| AC-07-64、70、72、73、74 | 通過 | `test_p1_lock_fork.py::test_64_70_72_lock_held_same_request_refused_readonly_ok`、`test_70_child_write_while_parent_holds_lock_fails_fast` | — |
| AC-07-65 | 通過 | `test_p1_lock_fork.py::test_65_two_resumes_only_one_proceeds` | — |
| AC-07-66 | 通過 | `test_p1_lock_fork.py::test_66_different_ops_only_one_acquires` | — |
| AC-07-67、69 | 通過 | `test_p1_lock_fork.py::test_67_69_kill9_after_plan_save` | — |
| AC-07-68 | 通過 | `test_p1_lock_fork.py::test_68_kill9_before_plan_save_no_residue` | — |
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
| AC-07-98 | 通過 | `test_fp_p1_unregistered_plan_is_registered_then_resumed`（a、b）、`test_fp_p1_other_op_after_reconcile_is_refused`（c）、`test_crash_before_plan_save_leaves_nothing`、`test_p1_06_*`（d） | — |
| AC-07-99（防禦性） | 通過 | `test_p1_resume.py::test_invalid_unregistered_plan_refuses_all_writes` | — |
| AC-07-100 | 通過 | `test_no_change_export_has_no_content_steps`（①）、`test_partial_no_change_and_tampered_no_change_path`（②④）、`test_multi_file_render_abort_after_first_file`（③） | — |
| AC-07-1～7、11、101～104 | 待 P5 | — | 去重與開單關卡 |

### P1 的實作說明（審查時請一併確認）

1. **寫入擷取**：既有的業務邏輯在擷取（overlay）中執行一次，產生完整的計畫；所有步驟的內容存成計畫的內容檔（`operations/<scope>/<op>/blobs/<sha256>`），續做時寫入保存的內容，不重新計算。
2. **ID 配發**：計數器的更新是計畫中的一步，ID 由計畫固定。和第 4 章 §7.3「配發在計畫保存之前」的差異列在最終規格附錄 A 4-17（類別 R，待確認）。
3. **驗證失敗的診斷**：只寫 task 欄位（`gate_results` 追加並記錄被拒的 `artifact_id`、狀態回 READY）與一個事件檔；被提交的 artifact 不修改、不開核准單（附錄 A 4-16）。越權提交仍是正常操作（附錄 A 4-15，類別 R，待確認）。
4. **Python API 的 op 身分**：直接呼叫寫入函式時，op_id 同樣由請求內容決定（同一請求重送 → 同一 op）；要刻意再執行一次，傳 `new_request=True`。既有測試中刻意建立相同輸入的 run，已改為明確傳入。
5. **唯讀指令**：`clarification list` 改為唯讀；寫 `clarifications/index.md` 改由 `clarification index`。
6. **P1 的 migrate**：只做空 root 也需要的部分（凍結 legacy audit、移轉標記、第一次 render）與 `--acknowledge-idle`。移轉清單、R000、sidecar、CLR rev 0、`--cancel-run`、`migrate verify`、`migrate rollback` 屬 P3。
7. **audit.log**：改為由事件檔整份重建（每個操作重建它影響的 run log 與全域 log），不再追加；需要和 Session B 協調（D8）。
8. **效能**：測試時間從約 5 秒增加到約 2 分鐘（每次寫入都經過計畫、fsync 與 render）；全域 log 的 render 每次讀取所有事件檔，資料量增加時可在第二批改為增量。
9. **登錄紀錄核對**：續做、已完成回報、`operation list` 與第 0 步都核對登錄紀錄的欄位、檔名、`plan_seq` 連續性，以及與計畫、完成狀態紀錄的一致性。限制：兩筆登錄紀錄的 `plan_seq` 互換（仍連續）無法由紀錄本身偵測。
10. **計畫保存前的殘留**：每個寫入請求取得鎖後，先清除沒有計畫也沒有登錄紀錄的 op 目錄與暫存檔。
