# 需求 A 最終規格：spec 依據、查閱證據與追溯

- **狀態**：最終條文，作為需求 A 實作與驗收**唯一的依據**，隨 MR 一起審查。
- **驗收的性質**：本文件所有 AC、fixture、故障點都是**預期結果**，在實作並以對應的 head SHA 執行之前，都不代表已經通過。
- **範圍**：需求 A 第一批（FIX-01、02、04～10）；FIX-03 與報表類屬第二批，條文列出但第一批不實作、不驗收。

## 0. 讀法

### 0.1 文件結構

| 章 | 內容 | 其他章提到它時的稱呼 |
|---|---|---|
| 第 1 章 | 共用名詞、派發包與決策點（FIX-04）、狀態推導與路由（FIX-05）、範例 A～H、核准決議表 | 共用名詞章 |
| 第 2 章 | spec 引用宣告、`reference_only`（FIX-01）、外部來源與 metadata 升級（FIX-02）、引用候選掃描（FIX-03，第二批） | spec 引用章 |
| 第 3 章 | CLR 欄位（FIX-06）、有型別來源與答案修訂（FIX-08）、issue key 去重與開單關卡（FIX-07 第 1、9 點） | 去重與開單關卡章 |
| 第 4 章 | executor 基礎設施（FIX-07）：操作身分、flock 全域操作鎖、操作計畫、續做、audit 事件檔、衍生輸出、維護模式與准入 | 執行器章、操作計畫章、操作執行章 |
| 第 5 章 | RM revision、綁定、閉包、過時判定、CIA 候選完整性、`run cancel`、移轉 `migrate`、`migrate verify`、`migrate rollback`、部署與回復停點（FIX-09） | 移轉與回復章 |
| 第 6 章 | CLR 生命週期（FIX-10）、`clarification apply`、文件索取單、第一批整合驗收 AC-A-B1、ADR-010 的內容、分階段方案 S0～S7 | CLR 生命週期章 |
| 附錄 A | 各章來源沒有定義的細節，逐項定案（實作定義、需求層釐清、待 Oscar 決定） | — |

- 各章內的 `§` 編號指**該章**的小節。
- 各章互相引用時，以上表的稱呼指向對應的章。
- 附錄 A 的定案優先於各章中標為「待確認」的文字。

### 0.2 實作階段與 AC 的對應

| 階段 | 內容 | 主要 AC |
|---|---|---|
| P1 | 第 4 章的 executor 基礎設施；第 5 章移轉中「空 root 也需要的部分」（凍結 legacy audit、標記、第一次 render），讓新安裝的 root 能以正式流程進入 `S_post` | AC-07-8、9a～9n 等可獨立驗證的部分、13～19、22～29 中 P1 的類型、36～49、64～79（含 77a～77k）、80～89、94～100 |
| P2 | 第 2 章 FIX-01、02；第 3 章 FIX-08、FIX-06 的 schema 與來源 | AC-01、AC-02、AC-08（含 35～38）、AC-06 中可獨立驗證的部分 |
| P3 | 第 5 章其餘部分：revision、資料移轉、綁定、閉包、過時判定、同版本 CIA、CIA 候選 G1～G8、cancel、manual、testcase-revision、`migrate verify`、`migrate rollback` | AC-09-1～50、54、55～91；AC-07-90～93；AC-A-B1-7、8 |
| P4 | 第 1 章 FIX-04、05，以及 agent 契約與指示 | AC-04-1～5、AC-05-1～15 |
| P5 | 第 3 章去重與開單關卡；第 6 章 FIX-10；ADR-010 | AC-07-1～7、10、11、101～104；AC-10A-1～69 |
| P6 | 整合驗收 | AC-A-B1-1～17；所有標「待 Pn」的項目 |

早期階段只驗收能獨立驗證的部分；不手造業務狀態，也不把還不能執行的 AC 標成通過。這些項目在完成紀錄中標「待 Pn」，於 P6 結清。

### 0.3 不在需求 A 範圍內

以下屬於需求 B（延後），本文件不實作、不驗收：

- 採用身分、影響批次、domain、事件鏈（seq、prev_sha、head）、fold、`legit`、`matches`、`decision_point_hash`；
- completion_guard、system 自動結案、`reincorporation_needed`、後續批次、`open_followups`；
- 補修 run（`obligation_repair`）、G-IMPACT 影響對帳、impact_snapshot、impact_sha；
- 細粒度實體鎖。

對應移到需求 B 的 AC：AC-04-6～12、AC-07-50、AC-07-51～55 中與批次和 CLR 鎖相關的部分、AC-07-56～63、AC-09-51～53。

### 0.4 和 ADR 的關係

- 新增 **ADR-010**，逐項說明 ADR-008 Decision 1～4 與 Consequences 的保留、取消、修改；ADR-008 標註哪些部分被 ADR-010 取代。必須涵蓋的內容見第 6 章 §10。
- CLR 結案改為人工確認加 runtime 輕量檢查；系統**不保證**機械完整性，已知限制見第 6 章。


---

## 第 1 章　共用名詞、派發包與決策點、狀態推導與路由（FIX-04、FIX-05）

> 本章所有 AC 都是**預期結果**，尚未實作、尚未執行。範例中的推導是需求層的推演，不是產品測試結果。
> 批次：FIX-04、FIX-05 都屬**第一批**（實作階段 P4）。
> 本章不含需求 B 的任何名詞與機制（採用身分、影響批次、domain、`matches`、`decision_point_hash`、completion_guard 等）。

---

### 0. 目的

1. **共用名詞章**：給出各章共用的資料身分與推導名詞（SpecPin、RMPin、RefNode、SourceRef、QuestionScope、`covers`、basis、basis_hash、effective_basis、DecisionPoint、decision_refs、CanonicalRequest、op_id、PlanStep、事件檔）的最終定義。其他章節第一次使用這些名詞時，引用本章即可。
2. **FIX-04**：分析輸入由 runtime 產生並釘選成不可變的**派發包**；Spec Analyst 申報實際查閱的來源；需求底下以**決策點**記錄每個待決或已決事項；TC 以 `decision_refs` 標明每個斷言依賴的決策點與依據。
3. **FIX-05**：runtime 從決策點的欄位推導**有效狀態**（E1～E6）與**有效等級**，以不合法組合（X1～X18）擋下矛盾資料，再依路由表決定需求狀態、開哪一種 CLR、是否建立 RESOLVE_AMBIGUITY 核准單，以及 TC 設計的限制；G-DESIGN 逐決策點限制 TC；RESOLVE_AMBIGUITY 核准前做 preflight。

---

### 1. 共用名詞

#### 1.1 canonical JSON 與 hash

凡本規格中「canonical sha256」「canonical JSON」：鍵依字典序排列、不含空白、UTF-8 編碼、不做 Unicode 正規化；對 canonical JSON 的位元組取 sha256。陣列是否排序、去重，由各名詞自己的定義決定。

#### 1.2 名詞表

| 名詞 | 定義 |
|---|---|
| **SpecPin** | `{spec_id, spec_version, content_hash}`。使用時，`content_hash` 必須同時等於 `spec.yaml` 的登記值與實體檔的 sha256。 |
| **RMPin** | 需求模型（RM）修訂版的身分：`{spec_id, spec_version, revision, sha256}`。`revision` 為 `R000`、`R001`…；revision 檔不可變（FIX-09）。 |
| **RefNode** | 引用閉包中的一個節點：SpecPin＋`decl_rev`＋`role`（`normative`／`informative`）＋`depth`（距目標 spec 的層數，直接引用為 1）。 |
| **閉包** | （閱讀閉包）目標 spec 版本的 normative 遞移引用，加上直接層的 informative 引用；循環以已訪集合終止；超過 50 個節點拒絕（FIX-09）。用於派發包、`reference_pins`。basis 只取其中的 normative 遞移部分（見 basis）。 |
| **SourceRef** | 有型別的依據引用，共三型，三型都帶 `quote`：<br>• `spec`：SpecPin＋`location`＋`quote`<br>• `clarification`：`clarification_id`＋`answer_rev`＋`answer_sha256`＋`quote`<br>• `approval`：`approval_id`＋`decision_sha256`＋`resolution_index`＋`quote`<br>驗證摘要（完整規則見 FIX-08）：quote 正規化只做三件事（合併空白、移除 `**`、移除行首引用符號）；spec 型的 quote 必須逐字存在於 hash 對應的實體檔，而且 spec 必須是目標或在閉包內；clarification 型依**被釘選的** `answer_revisions[answer_rev]` 驗證 hash 和 quote，不對照目前答案；approval 型只接受 RESOLVE_AMBIGUITY、決議為 approve 或 override 的核准單，`decision_sha256` 對 decision 區塊的 canonical JSON 計算，`resolutions[resolution_index]` 的 `requirement_id`、`question_id` 必須和引用處相符，quote 必須在該條目的 rationale 中。 |
| **basis_ref** | SourceRef 的**身分**（不含 quote）：<br>• clarification：`(clarification_id, answer_rev, answer_sha256)`<br>• approval：`(approval_id, resolution_index, decision_sha256)`<br>• spec：`(SpecPin, location)` |
| **QuestionScope** | 一個問題（或答案）適用的範圍：`{spec_id, requirement_id, subject, role_scope, params}`。<br>• `subject`：受描述物件與面向的路徑字串，格式 `^[a-z0-9_]+(\.[a-z0-9_]+)*$`（例如 `csv_export.header_when_empty`）。<br>• `role_scope`：角色清單，或 `["*"]` 代表與角色無關；**必須明示，空陣列不合法**（X18）。<br>• `params`：鍵值對，鍵和值只允許 `[a-z0-9_]`，值可以是陣列；`{}` 代表沒有參數限制。<br>新 CLR 以自身的這五個欄位作為答案範圍；舊 CLR（沒有 `subject`）**沒有答案範圍**，只能透過 `applicability[]`，或由人以 `clarification metadata upgrade` 補欄位。 |
| **`covers(A, D)`** | 答案範圍 A 是否涵蓋決策點範圍 D；以下全部成立才為真：<br>1. `A.spec_id == D.spec_id`，而且 `A.requirement_id == D.requirement_id`；<br>2. `A.subject == D.subject`；<br>3. 角色：`A.role_scope == ["*"]`，或 `D.role_scope ⊆ A.role_scope`；D 為 `["*"]` 時，A 也必須是 `["*"]`；<br>4. params：A 的每一個鍵都必須出現在 D 中而且值相等（值為陣列時，D 的值 ⊆ A 的值）；A 沒有的鍵代表 A 不限制該維度，D 可以多出鍵。<br>直觀上：A 必須和 D 一樣寬或更寬。A 比 D 窄（多限制一個參數、少一個角色）就不涵蓋。`spec_id` 相同即可跨版本比較，但跨版本、跨宣告的重用另受 basis_hash 檢查（X16）。答案的 `spec_id` 和決策點不同時，只能透過 `applicability[]`。 |
| **basis** | 某次分析或某個答案所依據的文件集合：`{target: SpecPin, target_decl_rev, closure: [RefNode(spec_id, spec_version, content_hash, decl_rev)]（排序）}`。<br>• `target_decl_rev`：目標 spec 版本**自己**在當時的宣告修訂（沒有任何宣告時為 0）。<br>• `closure` 只取 **normative 遞移閉包**（不含 informative；見附錄 A 1-1），和派發包、`reference_pins` 使用的閱讀閉包（另含直接層 informative）不同。 |
| **basis_hash** | `sha256(canonical(basis))`。<br>• 每個決策點的 basis_hash 由 runtime 依本次分析的目標 SpecPin 與閉包推導，agent 不填寫。<br>• CLR 每個 `answer_rev` 記錄回答當時的 `basis` 與 `basis_hash`：新答案由 runtime 在 `answer` 時記錄；legacy 答案在移轉時以 CLR 的 `spec_id`、`spec_version`，從 registry 取 `content_hash`，`target_decl_rev: 0`、`closure: []`（移轉前不存在任何宣告，見第 5 章 §3）。<br>• 同一 spec 版本只要目標自己的 `decl_rev`（`target_decl_rev`），或閉包中任一節點的 `decl_rev` 改變，basis_hash 就改變。 |
| **Applicability**（適用紀錄） | CLR 上只能追加的人工紀錄：`{answer_rev, scope: QuestionScope（每個維度都必須明示）, basis_hash, rationale, by（人）, at, sha256}`。`basis_hash` 是人確認時看到的本次 basis（由 CLI 依指定目標版本計算並顯示）。指令與限制見 FIX-08。 |
| **effective_basis** | SourceRef 實際代表的依據，依型別解析：<br>• `clarification` → `(clarification_id, answer_rev, answer_sha256)`。<br>• `approval` → 解析 `decision.resolutions[resolution_index]`。以下全部成立時，得到條目 `source` 的 `(clarification_id, answer_rev, answer_sha256)`：核准單類型是 RESOLVE_AMBIGUITY；決議是 approve 或 override；`decision_sha256` 相符；條目 outcome 是 `select_interpretation`；條目的 `requirement_id`、`question_id` 等於引用處；條目的 `source` 是 clarification 型。條目 `source` 為 null（核准者自行裁決）→ effective_basis 是 `(approval_id, resolution_index, decision_sha256)`，**不是任何 CLR**。條目 `source` 是 approval 型（巢狀）→ 不合法（X15）。<br>• `spec` → `(spec_id, spec_version, content_hash, location)`，不是 CLR。<br>補充：解析時，approval 條目內部的 clarification 來源也必須通過 X16（遞迴）。**決議為 reject 的 RESOLVE_AMBIGUITY 核准單不是 approval 包裝**，不能作為 approval 型 SourceRef（X15）；它的條目內部 source 只在 CLR 的 bug reject 結案路徑（`apply --path a6b`）中作為落地證據使用（見 CLR 生命週期章）。 |
| **DecisionPoint**（決策點） | 需求底下的一個待決或已決事項。欄位見 §2.5。一條需求可以有多個決策點。 |
| **question_id** | 決策點在同一條需求內的穩定 ID，格式 `Q<NN>`。重新分析時，同一個決策點必須保留原 ID（規則同 requirement_id）。 |
| **有效狀態（E1～E6）、effective_level** | runtime 對每個決策點推導的狀態與有效等級（§3.3）。`level` 是原始等級，只保留歷史。 |
| **decision_refs** | TC 斷言所依賴的決策點：`[{requirement_id, question_id, basis_ref}]`。`basis_ref` 是該斷言所用依據的 SourceRef 身分。 |
| **DispatchPacket**（派發包） | runtime 為某個 run 的某個 task 的某次 iteration 產生的不可變輸入包（§2.2、§2.3）。 |
| **CanonicalRequest** | 一個寫入請求的版本化正規表示：<br>`{request_schema: 1, action, targets: {run_id?, task_id?, iteration?, approval_id?, clarification_ids[]（排序）, spec_pins[]（排序）}, params: 該動作所有影響語意的參數（自由文字以其 sha256 表示）, inputs: {artifact_sha256s[]（排序）, dispatch_packet_sha256?}, new_request_token?}`。<br>`new_request_token` 只有使用者在第一次發出時明示 `--new-request` 才存在（uuid）；之後要接著做，用 `operation resume <op_id>`。 |
| **op_id** | `sha256(canonical(CanonicalRequest))`。只從請求本身計算，不從操作進行中會改變的狀態計算，所以續做時不變。同一請求重送 → 同一 op_id：計畫未完成就續做；已完成就回報「已完成」、不做任何事。刻意再發同內容的請求必須帶 `--new-request`，仍要通過該動作自身的狀態檢查。op 身分只用來決定續做哪一份計畫，**不代表**持有操作鎖（鎖與 executor 見 FIX-07）。 |
| **PlanStep**（計畫步驟） | 操作計畫中的一步：`{path, expected_before, expected_after, content_ref}`。`expected_before` 為 null 代表這一步之前檔案不應存在；`content_ref` 是從計畫內容重建最終檔案的方式。同一份計畫中，**每個 path 最多一步**（產生計畫時就合併同一檔案的所有變更；同一路徑出現兩次 → 計畫產生失敗）。before 等於 after 的路徑不成為步驟，列入 `no_change`。續做時：檔案等於 `expected_after` → 略過；等於 `expected_before`（或 before 為 null 且檔案不存在）→ 原子寫入；其他 → 停止並報告外部修改。有步驟完成紀錄時規則更嚴格（只能略過，內容不符就停止）。可重建的衍生輸出（md、html、audit.log 等）不列入步驟。完整規則見 FIX-07。 |
| **事件檔**（audit 事件檔） | 每一筆 audit 事件是一個獨立檔案，是 audit 的**權威紀錄**：<br>• run 內：`runs/<run_id>/audit.d/<op_id>-<step>.yaml`；全域：`runs/_audit.d/<op_id>-<step>.yaml`。<br>• 內容 `{at（計畫的 clock）, actor, action, detail, op_id, step, run_id}`；payload 和時間由計畫固定。<br>• 寫入：同目錄暫存檔 → fsync → `os.link` 到目標；目標已存在就失敗（檔名即 ownership）。續做時：不存在就建立；存在且 sha256 相符就略過；存在但內容不同就停止。只刪除本 op_id 的殘留暫存檔。<br>• 沒有操作計畫的 audit 一律寫成事件檔，op_id 為 `adhoc-<uuid>`、step 為 0；不再有任何程式對 `audit.log` 追加。<br>• `audit.log` 是由 `audit render` 重建的檢視：legacy 原位元組在前，接著是依 `(at, op_id, step)` 排序的事件。移轉標記寫入之前不 render。細節見 FIX-07。 |

---

### 2. FIX-04 派發包、決策點、decision_refs（第一批）

#### 2.1 目的

分析的輸入不再取決於手寫 prompt：runtime 產生並保存每次 iteration 的輸入；agent 申報實際查閱的來源，gate 以 hash 驗證；需求與 TC 以決策點為單位記錄依據，讓開單、設計、落地都能追溯。

#### 2.2 `bin/qaos dispatch`

```text
bin/qaos dispatch <run_id> <task_id> [--extra <path|spec_pin> --reason <文字>]...
```

1. 產生不可變的 `runs/<run_id>/dispatch/<task_id>-iter<N>.yaml`，路徑和 sha256 記在 task 的 `dispatch_packets[]`。
2. **同一 iteration 只能派發一次**；同一 iteration 已有派發包 → 拒絕。要改輸入就必須進入新的 iteration。
3. **額外來源**只能在產生派發包時登記，寫在 `extra_inputs[]`，每一筆附理由和 hash；沒寫理由 → 拒絕。
4. 人工核准後重開 task 時，engine 會讓 iteration 加 1（現行 `_after_ambiguity` 已經如此），所以必須產生新的派發包；沿用舊派發包提交 → 拒絕。
5. `dispatch` 會寫入 repo，因此是寫入指令：依 FIX-07 取得操作鎖、以操作計畫執行。

#### 2.3 派發包內容

| 項目 | 內容 |
|---|---|
| 目標 | 目標 SpecPin |
| 綁定的需求模型 | run 綁定的 RMPin：前版 SpecPin 與前版 RMPin；同版本重新分析時為 `from_revision`；spec-change-impact 時包含**全部 pin_groups** 的 RMPin |
| 閉包 | normative 遞移閉包的 RefNode 清單（只有 `depth=1` 列為**必讀**）；informative 直接參考 |
| 決議快照 | 同 area 以及直接參考所屬 area 中，狀態為 ANSWERED、INCORPORATED、APPLIED 的 CLR；每張附 `answer_rev`、`answer_sha256`、答案全文、該 rev 的 `basis_hash`、答案範圍（QuestionScope）、`applicability[]` 快照 |
| 本 run 已決的裁決 | 本 run 已決的 RESOLVE_AMBIGUITY 決議快照（`decision_sha256`＋`resolutions[]`） |
| 待決問題 | 同 area 中 OPEN、ASKED 的 CLR 清單 |
| 額外來源 | `extra_inputs[]`（每筆附理由和 hash） |

派發包保存所用決議的快照，所以舊 run 恢復時可以自給自足，不依賴 CLR 的目前內容。

#### 2.4 SpecAnalysis 新增欄位

- `consulted_sources[]`：Spec Analyst 申報實際查閱的來源，每筆是 SpecPin＋`read_scope`。
- `dispatch_packet_sha256`：本次分析所用的派發包。

#### 2.5 需求的新增欄位

1. **`decision_points[]`**：每個決策點的欄位如下（欄位語意與合法組合見 §3）。

   | 欄位 | 說明 |
   |---|---|
   | `question_id` | `Q<NN>`，同一需求內穩定 |
   | `topic` | 受控分類（例如 `rejection_response`、`deletion_policy`、`assignment_scope`、`aggregation_rule`、`display_rule`、`other`）；只是分類，不單獨決定問題身分。`topic: other` 時 `subject` 必須非空 |
   | `subject`、`role_scope`、`params` | 決策點的 QuestionScope 維度（加上需求所屬的 `spec_id`、`requirement_id`） |
   | `level` | **原始等級**：`none`、`minor`、`major`、`critical`，保留提出時的歧義程度 |
   | `basis` | 實質依據，單值：`defined_in_target`、`defined_in_reference`、`defined_by_decision`、`undefined`、`conflict` |
   | `known_rules[]` | 已知規則，SourceRef 清單 |
   | `conflict_sides[]`、`conflict_note` | 衝突的各側（SourceRef）與說明 |
   | `resolution` | 裁決，null 或 `{source: SourceRef（clarification 或 approval 型）, decided_at, adopted_side_index}` |
   | `coverage` | 查閱覆蓋：`references_status`、`consulted[]`、`unconsulted_normative[]`、`missing_sources[]`、`waivers[]`（§3.1） |
   | `decision_needed`、`detail_gaps[]` | 還需要決定的事、缺少的細節 |
   | `prior_clarifications[]` | 相關的既有 CLR |
   | `basis_hash` | **runtime 推導**（§1.2），不由 agent 填寫 |

2. **`doc_issues[]`**：文件本身的問題（例如同一份 spec 中殘留互相矛盾的文案），和行為裁決分開記錄。每筆 `{kind, location（SpecPin＋line）, note, status}`，例如 `kind: wording_conflict`、`status: pending_owner_decision`。**不影響需求狀態，也不自動開單。**
3. **`ambiguity`**（新資料，即有 `decision_points` 的需求）：
   - `ambiguity.level` = 所有決策點 effective_level 的最大值；
   - 新增 `ambiguity.raised_level` = 所有決策點原始 `level` 的最大值；
   - 兩者都由推導決定，和推導值不同 → X9。
4. **`rejection_contract.defined`**（新資料）：由 runtime 推導——topic 為 `rejection_response` 的決策點全部是 E1 時為 true，否則為 false。agent 填了但和推導值不同 → X8。舊資料照舊。
5. 豁免記錄在決策點的 `coverage.waivers[]`，指向核准單；重新分析時讀取豁免，所以不會再開同一張文件索取單，也不會再建立同一張核准單。
6. 「行為已裁決」與「文案待同步」分開：行為走決策點的 `resolution`（E1，可以作為 TC 依據）；文案矛盾放在 `doc_issues`。

#### 2.6 TC 與下游 agent

1. TC 新增 `decision_refs[] = {requirement_id, question_id, basis_ref}`；TC 的 expected 依據用 SourceRef 表示。
2. 下游 Test Designer、Test Validator、TC Risk Reviewer 的輸入帶派發包；**只能引用派發包範圍內的來源**。Validator、Risk Reviewer 檢查 Draft 用到的 SourceRef 都在派發包範圍內；不在範圍內 → Validator 報 `missing_reference`。
3. agent 契約與指示寫明「只能使用派發包內的來源，額外來源要申報」。

#### 2.7 G-SPEC 新增檢查

1. `consulted_sources` 的 hash 必須和派發包、`spec.yaml` 登記值、實體檔都相符；否則 FAIL。
2. 派發包中 `depth=1` 的 normative 參考，沒有出現在 consulted 時，必須列在相關決策點的 `coverage.unconsulted_normative[]` 並附理由；否則 FAIL。
3. 提交的 SpecAnalysis 的 `dispatch_packet_sha256` 必須是該 task 本次 iteration 的派發包。
4. 每個決策點都必須通過 X1～X18（§3.4）；違反時 G-SPEC FAIL，訊息指出組合編號。

#### 2.8 涉及的 schema、模組、CLI、契約

- **schema**：`schemas/workflow/task.schema.json`、`workflow-run.schema.json`（`dispatch_packets`）、新增 `schemas/workflow/dispatch-packet.schema.json`；`schemas/artifact/spec-analyst-input`、`spec-analysis`、`test-designer-input`、`test-validator-input`、`tc-risk-reviewer-input`、`testcase-draft`；`schemas/testcase/testcase-version.schema.json`（`decision_refs`）；`schemas/common/defs.schema.json`（DecisionPoint、Coverage、Resolution、DocIssue；SpecPin、RefNode、SourceRef 等共用定義由 FIX-01、FIX-08 加入）；`schemas/spec/requirement.schema.json`。
- **程式**：`tools/qaos/cli.py`（`dispatch`）、新增 `tools/qaos/dispatch.py`、`engine.py`、`gates.py`（`g_spec`）。
- **agent 契約與指示**：`agents/spec-analyst.yaml`、`test-designer.yaml`（critical 規則改讀有效等級）、`test-validator.yaml`、`tc-risk-reviewer.yaml`、`change-impact-analyst.yaml`，以及對應的 `.claude/agents/qaos-*.md`。

#### 2.9 限制

`consulted_sources` 是 agent 自我申報，只能證明「派發時有提供、hash 正確」，**不能證明讀過或讀懂**；transcript 的讀檔紀錄不作為 gate 依據。

---

### 3. FIX-05 狀態推導、合法組合、路由、G-DESIGN、preflight（第一批）

#### 3.1 決策點欄位語意

| 欄位 | 語意 |
|---|---|
| `basis` | 5 選 1，單值（§2.5） |
| `level` | 原始等級：`none`、`minor`、`major`、`critical` |
| `resolution` | null，或 `{source, decided_at, adopted_side_index}`。只對 `conflict`、`undefined` 有意義。`adopted_side_index` 是 conflict 時被採用的 `conflict_sides` 索引；裁決採用兩側以外的新解讀時為 null；basis 為 `undefined` 時一律為 null |
| `coverage.references_status` | 抄自目標版本：`undeclared`、`declared_empty`、`declared` |
| `coverage.consulted[]` | SpecPin 清單 |
| `coverage.unconsulted_normative[]` | `{pin, reason: unavailable 或 out_of_scope, note}`；pin 必須是 `depth=1` 的 normative 參考 |
| `coverage.missing_sources[]` | 被引用、但沒取得的文件：`{cited_at: SpecPin＋line＋text, name}` |
| `coverage.waivers[]` | `{approval_id, decision_sha256, resolution_index, waived: [missing_source 的 cited_at 身分＋name，或 unconsulted 的 pin]}` |

#### 3.2 推導旗標（agent 不能填寫）

- **`waiver_valid(w)`**：以下全部成立——
  - 核准單類型是 RESOLVE_AMBIGUITY，決議是 approve 或 override，`decision_sha256` 相符；
  - `resolutions[w.resolution_index]` 的 `requirement_id`、`question_id` 等於本決策點，outcome 是 `waive_missing`；
  - `waived` 的每一項，都**逐一完全相等**於本決策點 `missing_sources`（以 cited_at 的 SpecPin＋line＋name 判斷）或 `unconsulted_normative`（以 pin 判斷）中的某一項。只有名稱相同不算。
- **`gap_missing`**：`missing_sources`，或 `reason: unavailable` 的 `unconsulted_normative`，有任一項沒有被有效 waiver 涵蓋。
- **`gap_unverified`**：`references_status: undeclared`，或有未處理的引用候選。
- **`resolved`**：`resolution` 非 null，而且通過 X12～X16。

#### 3.3 有效狀態與有效等級

依序判斷，第一個成立的就是有效狀態：

| 有效狀態 | 條件 | effective_level |
|---|---|---|
| **E1 已定** | `basis` 為 `defined_*`；或 `basis` 為 `conflict`、`undefined`，而且 `resolved` | `defined_*`：等於 `level`（受 X1 限制只能是 none 或 minor）；`resolved`：`none` |
| **E2 衝突未決** | `basis = conflict`，沒有 `resolved` | `level` |
| **E3 缺文件** | `basis = undefined`，沒有 `resolved`，有 `gap_missing` | `level` |
| **E4 未定義（已查證）** | `basis = undefined`，沒有 `resolved`、沒有 `gap_missing`、沒有 `gap_unverified` | `level` |
| **E5 未定義（未查證）** | `basis = undefined`，沒有 `resolved`、沒有 `gap_missing`，有 `gap_unverified` | `level` |
| **E6 legacy** | 需求沒有 `decision_points`（舊資料） | 現行 `ambiguity.level` |

- 需求層（新資料）：`ambiguity.level` = 所有決策點 effective_level 的最大值；`ambiguity.raised_level` = 所有決策點 `level` 的最大值。
- E1 中，`resolution` 來自 conflict 的稱為「**已裁決衝突**」。
- `engine.py` 的 critical 判斷（`_has_unresolved_critical`、`_persist_requirements`）、`agents/test-designer.yaml` 的「不為 critical 設計 TC」規則，新資料一律改讀**有效等級**；契約文字同步修改。

#### 3.4 不合法組合（G-SPEC FAIL）

| # | 組合 | 理由 |
|---|---|---|
| X1 | `basis` 為 `defined_*`，`level` 為 major 或 critical | 已有依據就不該有高等級歧義；真有疑慮應為 conflict |
| X2 | `basis = conflict`，`level` 為 none 或 minor | 衝突至少是 major |
| X3 | `basis = conflict`，`conflict_sides` 少於 2 筆，或沒有 `conflict_note` | 無法表示衝突 |
| X4 | `basis = undefined`，`level = none` | 未定義至少是 minor |
| X5 | `basis = undefined`，`unconsulted_normative` 有 `reason: out_of_scope` 的項目 | 有該查的沒查，就不能宣稱未定義；改用 unavailable 或去查 |
| X6 | `basis` 為 `defined_*`，`known_rules` 是空的 | 沒有依據 |
| X7 | `basis` 為 `defined_*`，`resolution` 非 null | 不需要裁決 |
| X8 | 新資料中 `rejection_contract.defined` 有填，但和推導值不同 | 以推導值為準 |
| X9 | 新資料中 `ambiguity.level` 不等於最大 effective_level，或 `raised_level` 不等於最大 `level` | 避免兩欄位互相矛盾 |
| X10 | 任何 SourceRef 本身驗證失敗（FIX-08） | — |
| X11 | `adopted_side_index` 超出 `conflict_sides` 範圍；或 `basis = undefined` 時 `adopted_side_index` 不是 null | 採用的一側必須存在 |
| X12 | basis 和 `known_rules` 的來源型別或身分不對應（下表） | 防止偽造依據 |
| X13 | `resolution` 不完整：沒有 `source`，卻帶有 `adopted_side_index` 或其他 resolution 子欄位 | — |
| X14 | 任何 waiver 不符合 `waiver_valid`（**整筆拒絕，不是忽略**） | — |
| X15 | `resolution.source` 是 approval 型，但：核准單不是決議為 approve 或 override 的 RESOLVE_AMBIGUITY（含決議為 reject 的核准單）；或條目的 `requirement_id`、`question_id` 和引用處不符；或條目 outcome 不是 `select_interpretation`；或條目缺 `rationale`；或條目 `source` 是 approval 型（巢狀）。`resolution.source` 是 clarification 型，而該 CLR 不是 ANSWERED、INCORPORATED、APPLIED | — |
| X16 | 作為 basis 依據（`defined_by_decision` 的 `known_rules`）或 resolution 的 clarification 型來源，以下兩者都不成立：(a) 該 `answer_rev` 的 basis_hash 等於本決策點的 basis_hash，而且 CLR 自身的答案範圍 `covers` 決策點的 QuestionScope；(b) `applicability[]` 中有一筆 `answer_rev` 相同、`basis_hash` 等於本決策點、而且 `scope covers` 決策點 QuestionScope 的人工紀錄。approval 型來源**遞迴**對 `resolutions[index].source` 檢查。不論有沒有開過新 CLR，解析 SourceRef 時就比較。只當背景的 `known_rules`（basis 為 undefined）與 `conflict_sides` 不檢查 | 防止答案被錯用到不同角色、參數、需求或不同 basis |
| X17 | `unconsulted_normative` 中有 pin 不是 `depth=1` 的 normative 參考 | — |
| X18 | `role_scope` 為空陣列 | 範圍必須明示（`["*"]` 才代表與角色無關） |

**X12 的對應表**：

| basis | `known_rules` 至少一筆必須是 | 其他 |
|---|---|---|
| `defined_in_target` | `spec` 型，SpecPin 等於目標 | 可以另外附參考或決議作補充 |
| `defined_in_reference` | `spec` 型，SpecPin 在閉包內、不等於目標 | 同上 |
| `defined_by_decision` | `clarification` 或 `approval` 型，而且通過 X16 | 同上 |
| `undefined` | 不限；`known_rules` 只當背景，**不能**作為 TC 對這個決策點的 expected 依據 | — |
| `conflict` | `conflict_sides` 至少兩筆（X3） | — |

說明：`basis` 為 `defined_*` 時，`unconsulted_normative` 中有 `out_of_scope` 項目**是合法的**（已有定義，不依賴那些文件；範例 H）。

#### 3.5 路由

##### 3.5.1 路由表（以有效狀態＋有效等級查表）

| 路由 | 有效狀態 | effective_level | 需求狀態 | 開單（CLR kind） | 核准單 | TC 設計（逐決策點，依 `decision_refs`） |
|---|---|---|---|---|---|---|
| R1 | E1 | none、minor | ACTIVE | 不開 | 無 | 正常；可以引用 `known_rules`（basis 為 undefined 時除外）、resolution，以及 `adopted_side_index` 指定的那一側 |
| R2 | E2 | major | ACTIVE | `conflict_resolution` | 無 | 不能引用該決策點的 `conflict_sides`；其他部分照常 |
| R3 | E2 | critical | DRAFT | `conflict_resolution` | RESOLVE_AMBIGUITY | 禁止 |
| R4 | E3 | minor、major | ACTIVE | `document_request` | 無 | 依賴的斷言只能 exploratory |
| R5 | E3 | critical | DRAFT | `document_request` | RESOLVE_AMBIGUITY（等文件或豁免） | 禁止 |
| R6 | E4 | minor、major | ACTIVE | `spec_question` | 無 | 依賴的斷言只能 exploratory |
| R7 | E4 | critical | DRAFT | `spec_question` | RESOLVE_AMBIGUITY | 禁止 |
| R8 | E5 | minor、major | ACTIVE | `spec_question`，`possible_source_missing: true` | 無 | 依賴的斷言只能 exploratory |
| R9 | E5 | critical | DRAFT | `spec_question`，`possible_source_missing: true` | RESOLVE_AMBIGUITY | 禁止 |
| R0 | E6 | — | 現行行為 | 現行行為 | 現行行為 | 現行行為 |

- **需求狀態**取所有決策點中最嚴格的一個：任一決策點落在 DRAFT 列 → 需求為 DRAFT。
- **開單數**：每個 E2～E5 的決策點各算一個 issue key（FIX-07）；key 相同時連結，不重複開單。開單數依「不同 issue key 的數量」計算。
- 兩個自動開單函式（`_open_rejection_clarifications`、`_open_clarifications`）與 RESOLVE_AMBIGUITY 的建立，對新資料改由本路由表驅動；E6 維持現行行為。
- **為什麼沒有遺漏**：E1 的 effective_level，`resolved` 時是 none，`defined_*` 時受 X1 限制只能是 none 或 minor，所以 E1 只有一列；E2 受 X2 限制只會是 major 或 critical；E3～E5 受 X4 限制只會是 minor 以上。

##### 3.5.2 64 個合法抽象組合各恰一條路由

抽象維度：`basis`（5）×`level`（4）×`resolved`（是／否）×`gap_missing`（是／否）×`gap_unverified`（是／否）＝160 種；排除 X1（`defined_*` 加 major、critical）、X2（conflict 加 none、minor）、X4（undefined 加 none）、X7（`defined_*` 加 resolution）之後，剩下 **64 個合法組合**，每一個恰好對應一條路由（R1～R9）。前提：SourceRef、waiver、scope 等其餘驗證都有效（否則由 X3、X5、X6、X8～X18 在 G-SPEC FAIL）；E6（沒有決策點）不在此抽象之內，走 R0。

| # | basis | level | resolved | gap_missing | gap_unverified | 有效狀態 | effective_level | 路由 |
|---|---|---|---|---|---|---|---|---|
| 1 | `defined_in_target` | none | 否 | 否 | 否 | E1 | none | R1 |
| 2 | `defined_in_target` | none | 否 | 否 | 是 | E1 | none | R1 |
| 3 | `defined_in_target` | none | 否 | 是 | 否 | E1 | none | R1 |
| 4 | `defined_in_target` | none | 否 | 是 | 是 | E1 | none | R1 |
| 5 | `defined_in_target` | minor | 否 | 否 | 否 | E1 | minor | R1 |
| 6 | `defined_in_target` | minor | 否 | 否 | 是 | E1 | minor | R1 |
| 7 | `defined_in_target` | minor | 否 | 是 | 否 | E1 | minor | R1 |
| 8 | `defined_in_target` | minor | 否 | 是 | 是 | E1 | minor | R1 |
| 9 | `defined_in_reference` | none | 否 | 否 | 否 | E1 | none | R1 |
| 10 | `defined_in_reference` | none | 否 | 否 | 是 | E1 | none | R1 |
| 11 | `defined_in_reference` | none | 否 | 是 | 否 | E1 | none | R1 |
| 12 | `defined_in_reference` | none | 否 | 是 | 是 | E1 | none | R1 |
| 13 | `defined_in_reference` | minor | 否 | 否 | 否 | E1 | minor | R1 |
| 14 | `defined_in_reference` | minor | 否 | 否 | 是 | E1 | minor | R1 |
| 15 | `defined_in_reference` | minor | 否 | 是 | 否 | E1 | minor | R1 |
| 16 | `defined_in_reference` | minor | 否 | 是 | 是 | E1 | minor | R1 |
| 17 | `defined_by_decision` | none | 否 | 否 | 否 | E1 | none | R1 |
| 18 | `defined_by_decision` | none | 否 | 否 | 是 | E1 | none | R1 |
| 19 | `defined_by_decision` | none | 否 | 是 | 否 | E1 | none | R1 |
| 20 | `defined_by_decision` | none | 否 | 是 | 是 | E1 | none | R1 |
| 21 | `defined_by_decision` | minor | 否 | 否 | 否 | E1 | minor | R1 |
| 22 | `defined_by_decision` | minor | 否 | 否 | 是 | E1 | minor | R1 |
| 23 | `defined_by_decision` | minor | 否 | 是 | 否 | E1 | minor | R1 |
| 24 | `defined_by_decision` | minor | 否 | 是 | 是 | E1 | minor | R1 |
| 25 | `conflict` | major | 否 | 否 | 否 | E2 | major | R2 |
| 26 | `conflict` | major | 否 | 否 | 是 | E2 | major | R2 |
| 27 | `conflict` | major | 否 | 是 | 否 | E2 | major | R2 |
| 28 | `conflict` | major | 否 | 是 | 是 | E2 | major | R2 |
| 29 | `conflict` | major | 是 | 否 | 否 | E1 | none | R1 |
| 30 | `conflict` | major | 是 | 否 | 是 | E1 | none | R1 |
| 31 | `conflict` | major | 是 | 是 | 否 | E1 | none | R1 |
| 32 | `conflict` | major | 是 | 是 | 是 | E1 | none | R1 |
| 33 | `conflict` | critical | 否 | 否 | 否 | E2 | critical | R3 |
| 34 | `conflict` | critical | 否 | 否 | 是 | E2 | critical | R3 |
| 35 | `conflict` | critical | 否 | 是 | 否 | E2 | critical | R3 |
| 36 | `conflict` | critical | 否 | 是 | 是 | E2 | critical | R3 |
| 37 | `conflict` | critical | 是 | 否 | 否 | E1 | none | R1 |
| 38 | `conflict` | critical | 是 | 否 | 是 | E1 | none | R1 |
| 39 | `conflict` | critical | 是 | 是 | 否 | E1 | none | R1 |
| 40 | `conflict` | critical | 是 | 是 | 是 | E1 | none | R1 |
| 41 | `undefined` | minor | 否 | 否 | 否 | E4 | minor | R6 |
| 42 | `undefined` | minor | 否 | 否 | 是 | E5 | minor | R8 |
| 43 | `undefined` | minor | 否 | 是 | 否 | E3 | minor | R4 |
| 44 | `undefined` | minor | 否 | 是 | 是 | E3 | minor | R4 |
| 45 | `undefined` | minor | 是 | 否 | 否 | E1 | none | R1 |
| 46 | `undefined` | minor | 是 | 否 | 是 | E1 | none | R1 |
| 47 | `undefined` | minor | 是 | 是 | 否 | E1 | none | R1 |
| 48 | `undefined` | minor | 是 | 是 | 是 | E1 | none | R1 |
| 49 | `undefined` | major | 否 | 否 | 否 | E4 | major | R6 |
| 50 | `undefined` | major | 否 | 否 | 是 | E5 | major | R8 |
| 51 | `undefined` | major | 否 | 是 | 否 | E3 | major | R4 |
| 52 | `undefined` | major | 否 | 是 | 是 | E3 | major | R4 |
| 53 | `undefined` | major | 是 | 否 | 否 | E1 | none | R1 |
| 54 | `undefined` | major | 是 | 否 | 是 | E1 | none | R1 |
| 55 | `undefined` | major | 是 | 是 | 否 | E1 | none | R1 |
| 56 | `undefined` | major | 是 | 是 | 是 | E1 | none | R1 |
| 57 | `undefined` | critical | 否 | 否 | 否 | E4 | critical | R7 |
| 58 | `undefined` | critical | 否 | 否 | 是 | E5 | critical | R9 |
| 59 | `undefined` | critical | 否 | 是 | 否 | E3 | critical | R5 |
| 60 | `undefined` | critical | 否 | 是 | 是 | E3 | critical | R5 |
| 61 | `undefined` | critical | 是 | 否 | 否 | E1 | none | R1 |
| 62 | `undefined` | critical | 是 | 否 | 是 | E1 | none | R1 |
| 63 | `undefined` | critical | 是 | 是 | 否 | E1 | none | R1 |
| 64 | `undefined` | critical | 是 | 是 | 是 | E1 | none | R1 |

統計：R1 44 個、R2 4、R3 4、R4 4、R5 2、R6 2、R7 1、R8 2、R9 1，合計 64。

#### 3.6 G-DESIGN 逐決策點限制

1. TC 的每一個 expected 依據，以及每一個 negative 或 error_guessing 斷言，都必須用 `decision_refs` 標明依賴的決策點。
2. 依決策點的有效狀態判斷：

   | 依賴的決策點 | 限制 |
   |---|---|
   | E1 | 正常。`basis_ref` 只能指向該決策點的 `known_rules`（basis 為 `undefined` 時除外）、`resolution.source`，或 `adopted_side_index` 指定的那一側 |
   | E1（已裁決衝突） | 可以引用 resolution 和被採用的一側；引用其他側 → FAIL。`adopted_side_index` 為 null 時，只能引用 resolution，兩側都不能引用。G-DESIGN 依 `adopted_side_index` 判斷可引用的一側，不靠 quote 比對 |
   | E2（major） | 不能引用該決策點的 `conflict_sides` |
   | E3、E4、E5（minor、major） | 依賴的斷言必須是 exploratory，`needs_human_confirmation: true` |
   | 屬於 DRAFT 需求的決策點 | FAIL（E2～E5 critical 禁止設計） |

3. `basis` 為 `undefined` 的 `known_rules` 只是背景，以它作為該決策點的 expected 依據 → FAIL。
4. 需求推導出 `rejection_contract.defined=false` 時，negative 技術的 TC 沒有 `decision_refs` → FAIL。
5. 限制只作用在**依賴該決策點的斷言**：同一需求中已定的其他決策點不受影響（例如範例 C 中只有依賴 Q03 的斷言須 exploratory）。

#### 3.7 RESOLVE_AMBIGUITY 的決議條目與 preflight

**決議條目**：approve 或 override 時，`decision.resolutions[]` 每筆為 `{requirement_id, question_id, outcome, source?, rationale}`；outcome 有三種：

| outcome | 意義 |
|---|---|
| `select_interpretation` | 指定一個解讀：`source` 指向 CLR 的 answer_rev（clarification 型），或 `source` 為 null（這份核准本身就是裁決）。重新分析時，決策點的 `resolution` 指向這筆條目 → E1 |
| `waive_missing` | 帶 `waived[]`，逐項列出被豁免的缺檔（cited_at 身分＋name）或未查參考（pin）。重新分析時寫進 `coverage.waivers` → 從 E3 變成 E4 或 E5，再依路由開 `spec_question`；新單和原文件索取單的 kind、issue key 都不同，`related_clarifications` 指回原單 |
| `defer` | 核准 approve 時**不允許**（等同沒有做決定）；要延後就不要核准 |

**preflight**（取代現行 `engine.py` `_preflight_approval`「所有掛的 CLR 都必須已回答」的規則；寫入 decision 之前執行，失敗時核准單維持 PENDING、run 維持 WAITING_HUMAN）：

1. approve 或 override 時，該 revision 中每一個**有效等級為 critical** 的決策點，都必須有**恰好一筆** `resolutions[]` 條目，outcome 必須和有效狀態相符：

   | 有效狀態 | 允許的 outcome |
   |---|---|
   | E2 | `select_interpretation` |
   | E3 | `select_interpretation` 或 `waive_missing` |
   | E4、E5 | `select_interpretation` |

2. `select_interpretation` 的 `source` 若是 CLR，該 CLR 必須是 ANSWERED、INCORPORATED 或 APPLIED；`source` 為 null 代表這份核准本身就是裁決。
3. `waive_missing` 時，**允許**對應的文件索取單仍是 OPEN 或 ASKED。
4. 任何條目 outcome 為 `defer` → 拒絕。
5. reject 時不檢查（依現行行為）。

核准之後的動作（寫入 `resolutions`、不再自動 apply CLR、文件索取單的豁免處理、重開 Spec Analyst task 且 iteration 加 1）見 CLR 生命週期章。

#### 3.8 涉及的 schema、模組

- `engine.py`：`_apply_effects`、兩個開單函式改由路由表驅動、`_preflight_approval`、`_persist_requirements` 與 `_has_unresolved_critical` 的 critical 判斷改讀有效等級。
- `gates.py`：`g_spec`（X1～X18）、`g_design`（逐決策點限制）。
- `schemas/spec/clarification.schema.json`（`kind`）、`schemas/approval/approval-request.schema.json`（`decision.resolutions[]`）。
- agent 契約：`agents/test-designer.yaml` 與 `.claude/agents/qaos-test-designer.md` 的 critical 規則改讀有效等級。

---

### 4. 範例 A～H 與推導

以下 hash 中，spec 檔的 `content_hash` 是實際值；`<sha256:…>` 是示意值；quote 標「節錄」的部分，實作 fixture 要以實際原文展開。`SPEC-ROLEPERM-001` 是 ⑧（後台角色與權限 spec）的暫定 ID，正式 ID 待決定。範例 G 只示範形狀，不是推導對象。

#### 範例 A：REQ-SITELIST-022（v0.6，PM 回答前）

```yaml
requirement_id: REQ-SITELIST-022
spec_id: SPEC-SITELIST-001
spec_version: "0.6"
ambiguity: {level: critical, raised_level: critical, description: "子站台能否刪除"}
decision_points:
  - question_id: Q01
    topic: deletion_policy
    subject: site.child.delete
    params: {}
    role_scope: [admin, site_manager]
    level: critical
    basis: conflict
    known_rules: []
    conflict_sides:
      - {type: spec, spec_id: SPEC-SITELIST-001, spec_version: "0.6", content_hash: b57f48c699cccfbebb7d3a7ad506685c17778aabf973df98145b5c82329d66ca, location: "§角色與權限", quote: "| 子站台：刪除 | 可操作 | 可操作 |"}
      - {type: clarification, clarification_id: CLR-SITELIST-009, answer_rev: 0, answer_sha256: "<sha256:CLR-009 rev0>", quote: "<CLR-009 答案節錄>"}
    conflict_note: "v0.6 允許刪除子站台；CLR-009 定案任何站台不可刪除"
    resolution: null
    coverage:
      references_status: undeclared
      consulted: [{spec_id: SPEC-SITELIST-001, spec_version: "0.6", content_hash: b57f48c699cccfbebb7d3a7ad506685c17778aabf973df98145b5c82329d66ca}]
      unconsulted_normative: []
      missing_sources: []
      waivers: []
    decision_needed: "以 v0.6 或 CLR-009 為準"
```

**推導**：conflict、沒有 resolution → **E2**，effective critical（R3）→ 需求 DRAFT、開 `conflict_resolution`、建立 RESOLVE_AMBIGUITY、禁止設計 TC。X2、X3 通過；CLR-009 作為 `conflict_sides` 不檢查 X16。

#### 範例 B：同一題，PM 回答並核准後，留在 v0.6 重新分析

和 A 相同，只變動以下欄位：

```yaml
ambiguity: {level: none, raised_level: critical, description: "子站台能否刪除（已裁決）"}
decision_points:
  - question_id: Q01
    level: critical            # 原始等級保留
    basis: conflict
    resolution:
      source: {type: approval, approval_id: APR-0192, decision_sha256: "<sha256:APR-0192 decision>", resolution_index: 0, quote: "依 CLR-SITELIST-016 PM 回答：任何站台皆不可刪除"}
      decided_at: "<核准時間>"
      adopted_side_index: 1
```

APR-0192 的決議區塊：

```yaml
decision:
  decision: approve
  decided_by: oscarchen@blockaction.tech
  resolutions:
    - requirement_id: REQ-SITELIST-022
      question_id: Q01
      outcome: select_interpretation
      source: {type: clarification, clarification_id: CLR-SITELIST-016, answer_rev: 0, answer_sha256: "<sha256:CLR-016 rev0>", quote: "任何站台都不能刪除"}
      rationale: "依 CLR-SITELIST-016 PM 回答：任何站台皆不可刪除"
```

CLR-SITELIST-016 是舊單，沒有 `subject`。前置資料（S3，由人執行）：以 `clarification metadata upgrade` 補上 `subject: site.child.delete`、`role_scope: [admin, site_manager]`、`params: {}`（`spec_id: SPEC-SITELIST-001`、`requirement_id: REQ-SITELIST-022` 已存在，不改寫）；rev 0 在回答時記錄 basis = `{target: SITELIST 0.6 的 SpecPin, closure: []}`（`references_status` undeclared）。

**推導**：
- X15：APR-0192 是 approve 的 RESOLVE_AMBIGUITY；條目 `requirement_id`、`question_id` 相符；outcome 為 `select_interpretation`、有 rationale；條目 source（CLR-016）為已回答狀態 → 通過。
- effective_basis：approval 包裝解析為 **CLR-016 rev 0**，和直接引用 CLR-016 rev 0 相同。
- X16 遞迴檢查 CLR-016 rev 0：rev 0 的 basis（0.6、閉包空）和本次決策點的 basis 相同 → basis_hash 相同；補欄位後 CLR-016 的答案範圍 `covers` 決策點 → (a) 成立。`adopted_side_index: 1` 在範圍內（X11）→ `resolved`。
- 結果：**E1**，effective none（R1）→ 需求 ACTIVE、不開單；`ambiguity.level: none`、`raised_level: critical`（X9 通過）。
- TC 可以引用 resolution 和 `conflict_sides[1]`；引用 `conflict_sides[0]`（v0.6 那一側）→ G-DESIGN FAIL；`adopted_side_index: null` 時兩側都不能引用。
- G-SPEC 提交時，revision 中這個 SourceRef 的 effective_basis 等於 CLR-016 的最新 answer_rev 並通過 X16 → CLR-016 轉為 INCORPORATED（CLR 生命週期章 A4）。
- **補欄位之前**：舊單沒有答案範圍，也沒有 applicability → X16 FAIL，不是 E1。
- 如果改走「取消 run、0.4→0.7」路線：CLR-016 在 0.7 使用時 basis 不同 → (a) 不成立，需要 (b) 的人工適用紀錄。

#### 範例 C：REQ-SITELIST-035（v0.7，⑧ 已宣告）

```yaml
requirement_id: REQ-SITELIST-035
spec_version: "0.7"
ambiguity: {level: minor, raised_level: minor}
decision_points:
  - question_id: Q01
    topic: rejection_response
    subject: site.self.restriction.backend_enforcement
    params: {}
    role_scope: [admin, site_manager]
    level: none
    basis: defined_in_reference
    known_rules:
      - {type: spec, spec_id: SPEC-ROLEPERM-001, spec_version: "0.2", content_hash: d47f01840f02a548141f47834702a8fb277f6f69f9119d1f037d209c48408c66, location: "§四 管轄範圍／實作要求", quote: "須在後端每一支 API 強制執行"}
    coverage: &cov_c
      references_status: declared
      consulted:
        - {spec_id: SPEC-SITELIST-001, spec_version: "0.7", content_hash: c6001a294a5a6bb9c37effd3e2e46df53a5405db0efff2db0d5537df144897a2}
        - {spec_id: SPEC-ROLEPERM-001, spec_version: "0.2", content_hash: d47f01840f02a548141f47834702a8fb277f6f69f9119d1f037d209c48408c66}
      unconsulted_normative: []
      missing_sources: []
      waivers: []
  - question_id: Q02
    topic: rejection_response
    subject: site.self.restriction.response_semantics
    params: {}
    role_scope: [admin, site_manager]
    level: none
    basis: defined_in_reference
    known_rules:
      - {type: spec, spec_id: SPEC-ROLEPERM-001, spec_version: "0.2", content_hash: d47f01840f02a548141f47834702a8fb277f6f69f9119d1f037d209c48408c66, location: "§四 管轄範圍／實作要求", quote: "越權操作一律回「無權限」"}
    coverage: *cov_c
  - question_id: Q03
    topic: rejection_response
    subject: site.self.restriction.error_code
    params: {}
    role_scope: [admin, site_manager]
    level: minor
    basis: undefined
    known_rules: []
    coverage: *cov_c
    decision_needed: "實際錯誤代碼（spec 規定由後端定義）"
    detail_gaps: [error_code]
```

（`&cov_c`／`*cov_c` 是 YAML 錨點；序列化後就是三份完整相同的 coverage。）

**推導**：
- Q01、Q02：`defined_in_reference`；`known_rules` 是閉包內、不等於目標的 spec（X12 通過）→ E1 none。
- Q03：undefined、minor、沒有缺口、已宣告 → **E4 minor**（R6）→ 一張 `spec_question`（一個 issue key）。
- 需求 ACTIVE，`ambiguity.level: minor`；`rejection_contract.defined` 推導為 false（Q03 不是 E1）。
- 只有依賴 Q03 的斷言必須 exploratory；只依賴 Q01 的 negative TC 不需要。
- SITELIST 0.7 的 depth=1 normative 只有 ⑧，所以沒有其他未查參考可列（列入閉包外的 pin 會違反 X17）。

#### 範例 D：REQ-DAILYREPORT-001（v0.2，沒有宣告引用，重現歷史情境）

```yaml
decision_points:
  - question_id: Q01
    topic: rejection_response
    subject: report.venue_scope.out_of_scope_query
    params: {}
    role_scope: [admin, site_manager]
    level: minor
    basis: undefined
    known_rules:
      - {type: clarification, clarification_id: CLR-DAILYREPORT-001, answer_rev: 0, answer_sha256: "<sha256:CLR-001 rev0>", quote: "<CLR-001 答案節錄：操作員越權前後端皆擋>"}
    coverage:
      references_status: undeclared
      consulted: [{spec_id: SPEC-DAILYREPORT-001, spec_version: "0.2", content_hash: 7930c1fb9c1161c04aabaaf3ebd9f082da9e0a28709cbfc575159a5d89c5fc70}]
      unconsulted_normative: []
      missing_sources: []
      waivers: []
    decision_needed: "管理員、站長存取範圍外場館時的系統反應"
```

**推導**：undefined、沒有 resolution、沒有 `gap_missing`、`undeclared` → **E5 minor**（R8）→ `spec_question`，`possible_source_missing: true`。
- CLR-001 在 undefined basis 下只是背景，不檢查 X16；TC 對 Q01 以 CLR-001 作為 expected 依據 → G-DESIGN FAIL。
- CLR-001 的答案範圍（補欄位後）是 `[operator]`，不涵蓋 `[admin, site_manager]`；如果有人把它當 resolution → X16 FAIL，不會變成 E1。
- `role_scope` 和 CLR-001 不同，所以 issue key 不同、新開，不和 CLR-001 合併。

#### 範例 E：REQ-SITELIST-036（v0.6），critical 缺文件，以及豁免

豁免前：

```yaml
requirement_id: REQ-SITELIST-036
decision_points:
  - question_id: Q01
    topic: assignment_scope
    subject: role.assign.site_manager_to_site_manager
    params: {}
    role_scope: [site_manager]
    level: critical
    basis: undefined
    known_rules: []
    coverage:
      references_status: declared
      consulted: [{spec_id: SPEC-SITELIST-001, spec_version: "0.6", content_hash: b57f48c699cccfbebb7d3a7ad506685c17778aabf973df98145b5c82329d66ca}]
      unconsulted_normative: []
      missing_sources:
        - {cited_at: {spec_id: SPEC-SITELIST-001, spec_version: "0.6", content_hash: b57f48c699cccfbebb7d3a7ad506685c17778aabf973df98145b5c82329d66ca, line: 39, text: "手冊 v01 的角色模型（見 7.1.1 角色說明）"}, name: "手冊 7.1.1 角色說明"}
      waivers: []
```

**推導（豁免前）**：`gap_missing` → **E3 critical**（R5）→ 需求 DRAFT、`document_request`（一個文件項目）、RESOLVE_AMBIGUITY（等文件或豁免）。

核准決議（文件索取單仍是 OPEN；preflight 允許）：

```yaml
resolutions:
  - {requirement_id: REQ-SITELIST-036, question_id: Q01, outcome: waive_missing, waived: [{cited_at: {spec_id: SPEC-SITELIST-001, spec_version: "0.6", content_hash: b57f48c699cccfbebb7d3a7ad506685c17778aabf973df98145b5c82329d66ca, line: 39}, name: "手冊 7.1.1 角色說明"}], rationale: "文件短期內無法取得，改向 PM 直接確認"}
```

核准操作：寫入決議 → 豁免涵蓋文件索取單的全部項目 → 文件索取單轉 WITHDRAWN（A9）→ 重開 Spec Analyst task。

重新分析後：

```yaml
      waivers:
        - {approval_id: APR-XXXX, decision_sha256: "<sha256>", resolution_index: 0, waived: [<同上 cited_at＋name>]}
```

**推導（豁免後）**：`waiver_valid` 成立（類型、決議、條目、逐項相等）→ 沒有 `gap_missing`、已宣告 → **E4 critical**（R7）→ 開 `spec_question` 和新的 RESOLVE_AMBIGUITY。新單 kind、issue key 都不同；`related_clarifications` 指回已 WITHDRAWN 的文件索取單。重跑 G-SPEC 不重複開單，也不再出現文件索取單或「等文件」核准單。

#### 範例 F：REQ-DAILYREPORT-012（v0.3），已裁決衝突加文案待同步

CLR-DAILYREPORT-010 的實際狀態：`requirement_id: REQ-DAILYREPORT-011`、`status: APPLIED`；答案原文含「現金淨收（開分＋進鈔－已核實洗分－已兌現）含未來才付現的收據金額，不是當日實際現金增減」。rev 0 是 legacy 答案，basis 為 DAILYREPORT 0.1、`closure: []`。

S3 對 CLR-010 的兩個追加動作（**不改答案、不改狀態**；APPLIED 的 CLR 只能追加 `applicability`、`evidence_addenda`、`landings`）：

```yaml
applicability:
  - {answer_rev: 0, scope: {spec_id: SPEC-DAILYREPORT-001, requirement_id: REQ-DAILYREPORT-012, subject: report.cash_net.semantics, role_scope: ["*"], params: {}}, basis_hash: "<0.3 本次的 basis_hash>", rationale: "CLR-010 的答案直接定義現金淨收的語意（含未來付現的收據、非當日實際現金增減），適用 REQ-012", by: oscarchen@blockaction.tech, at: "<S3 時間>", sha256: "<sha256>"}
evidence_addenda:
  - {source: {type: document, file_name: "問題單回覆.html", sha256: 16c59e6280f53015673182e92efa6189adac92df8eac2adbf395220f18b6894d, package_sha256: 00a6cd752ea9f2e38e2c81081fd5b8ed07d822c88078053b960974d07b208a7e, location: "CLR-DAILYREPORT-010 段"}, note: "PM 於 2026-10-05 重申同一決議並補註不可直接對帳", by: oscarchen@blockaction.tech, at: "<S3 時間>"}
```

需求：

```yaml
requirement_id: REQ-DAILYREPORT-012
spec_version: "0.3"
ambiguity: {level: none, raised_level: major}
decision_points:
  - question_id: Q01
    topic: aggregation_rule
    subject: report.cash_net.semantics
    params: {}
    role_scope: ["*"]
    level: major
    basis: conflict
    known_rules: []
    conflict_sides:
      - {type: spec, spec_id: SPEC-DAILYREPORT-001, spec_version: "0.3", content_hash: 535d360df2afe72602ff397f6fcd1f329b9225472aaba13b798b95f590c3fc6d, location: "§列表欄位/現金淨收（第 55 行）", quote: "不等於當日實際的現金增減"}
      - {type: spec, spec_id: SPEC-DAILYREPORT-001, spec_version: "0.3", content_hash: 535d360df2afe72602ff397f6fcd1f329b9225472aaba13b798b95f590c3fc6d, location: "§列表欄位 附註（第 74 行）", quote: "代表場館端當日現金應該增減多少"}
    conflict_note: "第 55 行與第 74 行對現金淨收是否為當日實際現金增減互相矛盾"
    resolution:
      source: {type: clarification, clarification_id: CLR-DAILYREPORT-010, answer_rev: 0, answer_sha256: "<sha256:CLR-010 rev0>", quote: "不是當日實際現金增減"}
      decided_at: "2026-09-22"
      adopted_side_index: 0
    coverage:
      references_status: declared
      consulted:
        - {spec_id: SPEC-DAILYREPORT-001, spec_version: "0.3", content_hash: 535d360df2afe72602ff397f6fcd1f329b9225472aaba13b798b95f590c3fc6d}
        - {spec_id: SPEC-ROLEPERM-001, spec_version: "0.2", content_hash: d47f01840f02a548141f47834702a8fb277f6f69f9119d1f037d209c48408c66}
        - {spec_id: SPEC-CASHOUT-001, spec_version: "0.2", content_hash: 76c11bf6a07b6537100acbfd886f7bdd5adf15317e718127f20b52c007ddd6b6}
      unconsulted_normative: []
      missing_sources: []
      waivers: []
doc_issues:
  - {kind: wording_conflict, location: {spec_id: SPEC-DAILYREPORT-001, spec_version: "0.3", content_hash: 535d360df2afe72602ff397f6fcd1f329b9225472aaba13b798b95f590c3fc6d, line: 74}, note: "行為已由 CLR-010 裁決；第 74 行文案待 PM 同步（是否送出另行決定）", status: pending_owner_decision}
```

**推導**：
- X15：CLR-010 是 APPLIED，屬已回答 → 通過。X10：rev 0 存在、hash 相符、quote 在 rev 0 的答案中。
- X16：(a) 不成立（rev 0 的 basis 是 0.1，本次是 0.3＋閉包；而且 CLR-010 自身是 REQ-011，不涵蓋 REQ-012）；(b) 成立：applicability 的 `answer_rev: 0`、`basis_hash` 等於 0.3 這次的 basis_hash、scope 和決策點完全相同 → `covers`。`adopted_side_index: 0` 在範圍內 → `resolved`。
- 結果：**E1**，effective none（R1）→ ACTIVE、不開單；`ambiguity.level: none`、`raised_level: major`（X9 通過）。level 保留 major 也合法，因為 X1 只適用 `defined_*`。
- TC 可以引用 resolution 和 side 0（第 55 行）；引用 side 1（第 74 行）→ G-DESIGN FAIL。`doc_issues` 不影響狀態。
- 第 74 行中「推算值」「與現場點鈔差異須人工查核」兩點和第 55 行不衝突；TC 要引用時，必須另開決策點（例如 subject `report.cash_net.reconciliation_note`、basis `defined_in_target`、quote 取第 74 行不衝突的片段），不能引用 side 1 那句。
- 反例：拿掉 applicability → X16 FAIL；applicability 的 basis_hash 不是 0.3 這次的（例如之後又改了宣告）→ X16 FAIL，需要新的紀錄。

#### 範例 G：CLR 的落地紀錄（**預期形狀**，不是推導對象）

```yaml
clarification_id: CLR-SITELIST-016
kind: conflict_resolution          # 舊單：由人以 metadata upgrade 補上 kind、question_id、subject 等欄位（留 history）
question_id: Q01
spec_id: SPEC-SITELIST-001
requirement_id: REQ-SITELIST-022
subject: site.child.delete
role_scope: [admin, site_manager]
params: {}
status: APPLIED
answer_revisions:
  - {rev: 0, answer: "選 A：任何站台都不能刪除……", answered_by: "PM（2026-10-05，經 Oscar 轉達）", answered_at: "<S3 時間>", resolution: spec_updated,
     basis: {target: {spec_id: SPEC-SITELIST-001, spec_version: "0.6", content_hash: b57f48c699cccfbebb7d3a7ad506685c17778aabf973df98145b5c82329d66ca}, closure: []}, basis_hash: "<sha256>",
     answer_sources: [{type: document, file_name: "問題單回覆.html", sha256: 16c59e6280f53015673182e92efa6189adac92df8eac2adbf395220f18b6894d, package_sha256: 00a6cd752ea9f2e38e2c81081fd5b8ed07d822c88078053b960974d07b208a7e, location: "CLR-SITELIST-016／017 段"}, {type: spec, spec_id: SPEC-SITELIST-001, spec_version: "0.7", content_hash: c6001a294a5a6bb9c37effd3e2e46df53a5405db0efff2db0d5537df144897a2, location: "變更記錄 v07（第 249 行）"}],
     sha256: "<sha256>"}
resulting_spec_version: "0.7"
landings:
  - {type: incorporated, rm_pin: {spec_id: SPEC-SITELIST-001, spec_version: "0.6", revision: R001, sha256: "<sha256>"}, run_id: "<落地 run>", op_id: "<op>"}
  - {type: applied, path: a6, landed_in: ["<落地 run>"],
     targets_confirmed: ["SPEC-SITELIST-001@0.6:REQ-SITELIST-022#Q01"], targets_deferred: [],
     scan_units: [{product: ba-admin, area: SITELIST}], final_keywords: ["<關鍵字>"], scan_reused: "<keywords_only 或 full；未用 --scan 時省略>",
     rule_version: "<掃描規則版本>", candidates: [{tc_id: "<TC>", active_version: "<版本>", tc_version_sha256: "<sha256>", reasons: ["<候選理由>"]}],
     conclusions: [{tc_id: "<TC>", conclusion: "<updated|not_affected|retire_planned|deferred:理由>"}], scan_sha256: "<sha256>", op_id: "<op>"}
```

這只是形狀示意；landing 各欄位的權威定義見 CLR 生命週期章。實際驗收以正式流程建立的 COMPLETED run、核准單與 `apply` 檢查為準，不能借用本範例當作已驗證。

#### 範例 H：已定義，但有範圍外的 normative 參考沒查

```yaml
requirement_id: REQ-DAILYREPORT-001
spec_version: "0.3"
decision_points:
  - question_id: Q01
    topic: rejection_response
    subject: report.venue_scope.out_of_scope_query
    params: {}
    role_scope: [admin, site_manager]
    level: none
    basis: defined_in_reference
    known_rules:
      - {type: spec, spec_id: SPEC-ROLEPERM-001, spec_version: "0.2", content_hash: d47f01840f02a548141f47834702a8fb277f6f69f9119d1f037d209c48408c66, location: "§四 管轄範圍／實作要求（第 120 行）", quote: "含場館日結報表查詢、匯出範圍外場館"}
    coverage:
      references_status: declared
      consulted:
        - {spec_id: SPEC-DAILYREPORT-001, spec_version: "0.3", content_hash: 535d360df2afe72602ff397f6fcd1f329b9225472aaba13b798b95f590c3fc6d}
        - {spec_id: SPEC-ROLEPERM-001, spec_version: "0.2", content_hash: d47f01840f02a548141f47834702a8fb277f6f69f9119d1f037d209c48408c66}
      unconsulted_normative:
        - {pin: {spec_id: SPEC-CASHOUT-001, spec_version: "0.2", content_hash: 76c11bf6a07b6537100acbfd886f7bdd5adf15317e718127f20b52c007ddd6b6}, reason: out_of_scope, note: "出金核實規則與範圍權限無關"}
      missing_sources: []
      waivers: []
```

**推導**：CASHOUT 0.2 是 DAILYREPORT 0.3 的 depth=1 normative 參考，X17 通過；basis 是 `defined_in_reference`，X5 不適用 → **E1 none**（R1）。可以序列化，也合法。

---

### 5. 核准決議表（現行 `engine.py` 行為，本需求不修改）

依 `engine.py` 的 `_commit_testcases`（ACTIVATE_TESTCASE、APPLY_CHANGE 共用）與 `_finish_approval_task`：

- `activated`：per_item 決議（沒有該項的 per_item 時採整體決議）為 approve 或 override、因此被啟用的 TC。
- `_finish_approval_task(ok = 整體決議 ∈ {approve, override} or bool(activated), back_to_generator = 整體決議 == "reject")`：`ok` 為真時直接推進，忽略 `back_to_generator`；`ok` 為假且 `back_to_generator` 為真時，退回 Test Designer（iteration 加 1）。

| # | 整體決議 | per_item | 現行結果 | 後續（需求 A） |
|---|---|---|---|---|
| 1 | approve 或 override | 全部 approve、override，或沒有 per_item | 全部啟用（舊 ACTIVE 版本轉 SUPERSEDED）；推進，之後 run 可以 COMPLETED。APPLY_CHANGE：change_impact 轉 APPLIED，並依 VersionComparisonReport 的 retire 建議 retire TC | 核准與 run 完成都**不**改變任何 CLR 的狀態；run COMPLETED 後可作為 `clarification apply --landed-in` 的候選，仍須通過 apply 的檢查 |
| 2 | approve 或 override | 部分 reject | 被 reject 的 TC 版本回 DRAFT；其餘啟用；推進，之後 run 可以 COMPLETED。APPLY_CHANGE 同第 1 列 | 同第 1 列 |
| 3 | **reject** | **至少一項 approve 或 override** | 那些項目**啟用**；`ok = bool(activated) = True` → **推進**（不回 Designer）；APPLY_CHANGE 的 change_impact 被設為 `TEST_UPDATE_REQUIRED`（不執行 retire 建議）；之後 run 可以 COMPLETED | 同第 1 列。【已知不一致】change_impact 為 `TEST_UPDATE_REQUIRED`、run 卻 COMPLETED；本需求不修改，只記錄 |
| 4 | reject | 沒有 per_item，或 per_item 全部 reject | 沒有啟用；`ok = False` → 退回 Test Designer；run 不會 COMPLETED | 該 run 未 COMPLETED，不能作為 landed-in |

驗收：AC-A-B1-13（4 列各一個案例；第 3 列以 ACTIVATE_TESTCASE 和 APPLY_CHANGE 各測一次）。

---

### 6. 驗收 AC（全部是預期結果）

fixture 一律經測試 root 的正式流程建立（`spec import`、`spec reference add`、`run new`、`dispatch`、`submit`、`approve`…），不手造 run、revision、TC、CLR。範例中的示意 hash 與「節錄」quote 要以實際內容展開。

#### 6.1 FIX-04

| AC | 前置條件／情境 | 預期結果 |
|---|---|---|
| AC-04-1 | 對同一 run、同一 task、同一 iteration 執行兩次 `dispatch` | 第二次拒絕；第一次產生的派發包檔案 sha256 和 task `dispatch_packets[]` 的紀錄一致 |
| AC-04-2 | RESOLVE_AMBIGUITY 核准後重開 Spec Analyst task（iteration 加 1），沒有產生新派發包就提交（沿用舊 iteration 的派發包） | 提交被拒絕（iteration 已改變） |
| AC-04-3 | SpecAnalysis 的 `consulted_sources` 中某筆 hash 和派發包、登記值或實體檔不符（竄改） | G-SPEC FAIL |
| AC-04-4 | TestCaseDraft 的某個 SourceRef 指向派發包範圍以外的來源 | Test Validator 報 `missing_reference` |
| AC-04-5 | `dispatch --extra <來源>` 沒有附 `--reason` | 拒絕 |

#### 6.2 FIX-05

| AC | 前置條件／情境 | 預期結果 |
|---|---|---|
| AC-05-1 | 範例 A（REQ-SITELIST-022，conflict critical，沒有 resolution） | E2 critical；需求 DRAFT；開 `conflict_resolution`；建立 RESOLVE_AMBIGUITY；G-DESIGN 拒絕依賴該決策點的 TC |
| AC-05-2 | 範例 B（CLR-016 已補 QuestionScope，rev 0 basis 與本次相同；resolution 為 APR-0192 條目，`adopted_side_index: 1`） | E1，effective none；需求 ACTIVE；`ambiguity.level: none`、`raised_level: critical`；TC 引用 resolution 和 side 1 → PASS；引用 side 0 → G-DESIGN FAIL；另以 `adopted_side_index: null` 測：兩側都不能引用 |
| AC-05-3 | 範例 C（同一需求三個決策點） | Q01、Q02 為 E1 none，Q03 為 E4 minor；需求 ACTIVE；`rejection_contract.defined = false`；只依賴 Q01 的 negative TC 不是 exploratory → PASS；依賴 Q03 卻不是 exploratory → G-DESIGN FAIL |
| AC-05-4 | X1～X17 各一個反例 | 每個都 G-SPEC FAIL，訊息指出組合編號（X18 見 AC-05-15） |
| AC-05-5 | 範例 E 豁免前（E3 critical） | 只開文件索取單（`document_request`），並建立「等文件或豁免」的 RESOLVE_AMBIGUITY；**不**開 `spec_question` |
| AC-05-6 | 範例 E，文件索取單仍是 OPEN 時，以 `waive_missing`（完整列出 cited_at）核准 | preflight 通過；核准操作把文件索取單轉為 WITHDRAWN（A9）；重開 Spec Analyst task；新 revision 帶有效 waiver → E4 critical → 新的 `spec_question` 和新的 RESOLVE_AMBIGUITY，新單 `related_clarifications` 指回文件索取單；重跑 G-SPEC 不重複開單，也不再出現文件索取單或「等文件」核准單 |
| AC-05-7 | 範例 D（REQ-DAILYREPORT-001 v0.2，`references_status: undeclared`） | E5 minor；開 `spec_question`，`possible_source_missing: true`；CLR-001 只當背景；TC 對 Q01 以 CLR-001 作為 expected 依據 → G-DESIGN FAIL |
| AC-05-8 | 同一需求兩個決策點，分別為 E1 與 E2 major | 需求 ACTIVE；開一張 `conflict_resolution`；只依賴 E1 決策點的 TC → G-DESIGN PASS |
| AC-05-9 | 範例 F（CLR-010 有 0.3 basis_hash 的 applicability） | G-SPEC PASS → G-DESIGN PASS（依 resolution 與第 55 行設計的現金淨收跨日兌現 TC，即 AC-R7-2 的 TC）；引用 side 1（第 74 行）→ G-DESIGN FAIL；拿掉 applicability → X16 FAIL |
| AC-05-10 | approve 時 `resolutions[]` 有 `outcome: defer` | 拒絕；核准單維持 PENDING |
| AC-05-11 | 偽造的 `defined_by_decision`：`known_rules` 只有 spec 型來源 | X12 FAIL |
| AC-05-12 | 錯誤的目標：`defined_in_target`，但 `known_rules` 只有參考 spec | X12 FAIL |
| AC-05-13 | 跨問題的 waiver：waiver 指向另一個 question_id 的條目；或 `waived` 項目只有名稱相同 | X14 FAIL |
| AC-05-14 | 不完整的 resolution：有 `adopted_side_index` 但沒有 `source`；另以 approval 條目缺 `rationale` 測 | 前者 X13 FAIL；後者 X15 FAIL |
| AC-05-15 | 決策點的 `role_scope` 為空陣列 | X18 FAIL |

---

### 7. 已知限制

1. `consulted_sources` 是自我申報，只證明有提供、hash 正確，不證明讀過或讀懂。決策點與 CLR 上的查閱證據，能證明提供了哪些版本、`known_rules` 的 quote 逐字存在；不能證明讀懂，也不能證明「已查文件都沒有答案」。
2. `gap_unverified` 中「未處理的引用候選」依賴引用候選掃描（FIX-03，第二批）。
3. 64 個合法組合各恰一條路由，是在 SourceRef、waiver、scope 等其他驗證都有效的前提下的抽象結論；它是需求層推導，不代表 G-SPEC 實作已驗證。
4. E6（沒有決策點的舊資料）維持現行行為，不享有本章的推導與檢查。
5. 核准決議表第 3 列（整體 reject、部分項目 approve 時 run 仍推進並可能 COMPLETED，而 APPLY_CHANGE 的 change_impact 為 `TEST_UPDATE_REQUIRED`）是現行行為的不一致，本需求不修改；是否另開 QAOS 的 bug 待決定。
6. 「錯誤代碼由後端定義」這類問題（範例 C 的 Q03）在第一批仍依現行規則開給 PM 的 `spec_question`，不新增分流。


---

## 第 2 章　spec 引用宣告、外部來源與引用候選掃描（FIX-01、FIX-02、FIX-03）

> 本章所有 AC 都是**預期結果**，尚未實作、尚未執行。
> 批次：FIX-01、FIX-02 屬**第一批**；FIX-03 屬**第二批**（條文完整列出，但第一批不實作、不驗收）。

---

### 1. 目的

1. 讓每個 spec 版本可以**明確宣告**它引用了哪些其他 spec 版本（規則依據或背景參考），宣告有不可改寫的修訂歷史；沒有宣告過的舊資料不被誤認為「沒有引用」。
2. 讓手冊、附件這類只供參考、不做需求分析的文件，也能以 spec 版本的形式匯入（有 hash、可被引用），但不能被當成任何 run 的分析目標。
3. 為每個 spec 版本記錄結構化的外部來源（開發包、外部檔名、外部版本標示、原檔 hash），偵測重複匯入與「外部檔就地修改」。
4. 為舊資料提供由人執行、可稽核、只補缺欄位的 metadata 升級入口，不自動回填。
5. （第二批）匯入時以固定規則掃描文件中的引用線索，產生候選，交由人確認，降低漏宣告。

---

### 2. 名詞

| 名詞 | 定義 |
|---|---|
| **SpecPin** | `{spec_id, spec_version, content_hash}`。使用時，`content_hash` 必須同時等於 `spec.yaml` 登記值與實體檔的 sha256。 |
| **RefNode** | 引用閉包中的一個節點：SpecPin＋`decl_rev`＋`role`＋`depth`。`references[]` 存放的是直接層（被本版本直接引用）的 RefNode。 |
| **role** | 引用的角色：`normative`（規則依據）或 `informative`（背景參考）。 |
| **references_status** | spec 版本條目的引用宣告狀態：`undeclared`（從未宣告；舊資料預設，**不等於沒有引用**）、`declared_empty`（人確認沒有引用，必須附 `reason`）、`declared`（有宣告）。 |
| **reference_declarations[]／decl_rev** | 引用宣告的修訂歷史，只能追加。每一次新增或移除引用，都追加一筆並配發遞增的 `decl_rev`；舊紀錄不改寫。`references[]` 是**最新** `decl_rev` 的內容。 |
| **analysis_policy** | spec 版本的分析政策：`analyze`（預設；可建立需求模型、可當 run 目標）或 `reference_only`（只當參考文件：不建需求模型、不能當任何 run 的目標，但可以被其他 spec 引用）。 |
| **source** | spec 版本的結構化外部來源（§4.1）。沒有 `source` 的舊條目稱為 **legacy 條目**。 |
| **metadata_history[]** | `spec metadata upgrade` 的變更紀錄，只能追加。 |
| **reference_candidates[]／candidates_ack**（第二批） | 引用候選掃描的結果與人的處置紀錄（§5）。 |
| RMPin、basis、basis_hash、閉包、`declaration_changed`、操作計畫、op_id、全域操作鎖（flock） | 定義見共用名詞章。 |

---

### 3. FIX-01 引用宣告與參考型 spec（第一批）

#### 3.1 spec 版本條目新增的欄位

| 欄位 | 內容 |
|---|---|
| `references_status` | `undeclared`／`declared_empty`（＋`reason`，必填）／`declared` |
| `references[]` | 直接層 RefNode。每筆：SpecPin、`role`（`normative`／`informative`）、`scope`（選填，章節或關鍵段落說明）、`declared_by`、`declared_at` |
| `reference_declarations[]` | 只能追加；每筆帶遞增的 `decl_rev` |
| `analysis_policy` | `analyze`（預設）／`reference_only` |

- 舊的 `spec.yaml` 不需修改即可通過 schema；讀取時缺 `references_status` 視為 `undeclared`，缺 `analysis_policy` 視為 `analyze`。
- 移轉不寫入 `spec.yaml`；既有版本條目維持原樣，直到人以本章的指令宣告或升級。

#### 3.2 宣告規則

1. 引用只能指向**已匯入**的 spec 版本（`analyze` 或 `reference_only` 都可以）。指定的版本不存在，或 SpecPin 的 hash 與登記值、實體檔不符 → 拒絕，`spec.yaml` 位元不變。
2. **允許循環引用**（例如 A 引用 B、B 引用 A）。閉包展開時以已訪集合終止循環；閉包規則（normative 遞移加直接 informative、超過 50 個節點拒絕）定義在 revision 與閉包章（FIX-09）。
3. references **只能由人宣告**；agent 不得自行新增。第二批的掃描候選（§5）也必須經人確認後，才由人宣告寫入。
4. 每次 add、remove 各追加一筆 `reference_declarations`，產生新的 `decl_rev`；舊紀錄、版本條目的 `content_hash`、`file` 位元不變。引用宣告只改 metadata，不改版本內容與 hash。
5. `declared_empty` 必須附 `reason`，否則拒絕。
6. 宣告指令屬於寫入指令，依 FIX-07 在讀取任何狀態前取得全域操作鎖，並以操作計畫執行。

#### 3.3 CLI

```text
bin/qaos spec reference add            # 為某 spec 版本新增一筆直接引用（SpecPin、role、scope 選填）→ 新 decl_rev
bin/qaos spec reference remove         # 移除一筆直接引用 → 新 decl_rev
bin/qaos spec reference declare-empty  # 宣告沒有引用，必須附 reason
```

（各子指令的參數形式見「已知限制」第 6 點。）

#### 3.4 reference_only 的 7 個拒絕入口

以下入口指向 `analysis_policy: reference_only` 的版本時，`run new` 一律拒絕，不建立 run：

| # | workflow | 入口 |
|---|---|---|
| 1 | spec-to-testcase | `inputs.spec_id` |
| 2 | spec-change-impact | from 端（`spec_id`＋`from_version`） |
| 3 | spec-change-impact | to 端（`spec_id`＋`to_version`） |
| 4 | spec-to-bug | `inputs.spec_id` |
| 5 | testcase-revision | 由被修訂 TC 版本推得的 `spec_id`／`spec_version` |
| 6 | manual-test-to-regression | `inputs.spec_id` |
| 7 | manual-test-to-regression | manual record 的 `spec_hint.spec_id` |

- regression-generation 不涉及 spec，不適用。
- manual-test-to-regression 另有規則：`inputs.spec_id` 與 `spec_hint` 都沒有 → 拒絕（定義見 workflow 綁定章）。

#### 3.5 和其他功能的關係（只列介面，規則在各自章節）

- 決策點的 `coverage.references_status` 抄自目標版本；`undeclared` 時只能判為未經驗證的未定義（見狀態推導章，FIX-04／FIX-05）。
- basis 的閉包由 RefNode（含各節點 `decl_rev`）組成；閉包中任一節點的 `decl_rev` 改變或閉包組成改變，判為 `declaration_changed`（見 FIX-08、FIX-09）。
- 文件索取單的 `fulfill` 以目標版本**目前** `decl_rev` 的 `references` 重新驗證文件是否仍被宣告（見 CLR 生命週期章，FIX-10）。

---

### 4. FIX-02 外部來源、`spec import` 規則與 metadata 升級（第一批）

#### 4.1 `source` 欄位（spec 版本條目）

| 欄位 | 說明 |
|---|---|
| `package_name` | 開發包名稱 |
| `package_sha256` | zip 或 manifest 的 hash；可為空 |
| `external_filename` | 外部檔名 |
| `external_version_label` | 外部版本標示（內部版本號維持內部遞增，以此欄對照外部） |
| `external_effective_date` | 外部文件自己宣告的生效日（例如變更記錄日期）；由人輸入，只當參考資訊 |
| `external_commit` | 來源聲稱的 commit，固定附 `claimed: true`；第一批**沒有**任何指令能解除 claimed |
| `source_bytes_sha256` | 原始檔位元組的 sha256 |

#### 4.2 `spec import` 的規則

| # | 情況 | 結果 |
|---|---|---|
| 1 | **同一 SPEC** 內已有相同 `content_hash` 的版本 | 拒絕，並指出既有版本 |
| 2 | **不同 SPEC** 有相同 hash | 匯入成功，輸出警告 |
| 3 | 同一 SPEC、同一 `external_filename` 已以**不同 hash** 匯入過 | 匯入成功並提示「外部檔就地修改」；`change_summary` **必填**，空白則拒絕 |
| 4 | 匯入時有正規化（例如 CRLF 換行） | `content_hash` 記錄存檔後的 hash，`source_bytes_sha256` 記錄原檔 hash，兩者都保存；不同時輸出提示 |
| 5 | legacy 條目（沒有 `source`） | 讀取正常；**不自動回填**；**不參與**同名比對 |
| 6 | `title` 正規化後為空 | 匯入成功（不阻擋），輸出**警告**；不修改 schema（`title` 在 schema 中只是字串） |

- **title 正規化**：全形轉半形、去除所有空白（含全形空白）、轉小寫；結果長度為 0 即為「空」。來源欄位不存在、是空字串或全為空白，都屬於「空」。同一正規化規則也用於文件索取單的名稱比對（見 FIX-10；空名稱不得參與自動比對）。
- `spec import` 為寫入指令，依 FIX-07 取得全域操作鎖。

#### 4.3 `spec metadata upgrade <spec_id>@<ver>`

1. **由人執行**，必須帶 `--by` 與 `--reason`；以操作計畫執行（FIX-07，可中止後續做）。
2. **只能補 legacy 條目缺少的欄位**：缺 `source` 時補 `source`；缺 `analysis_policy` 時補 `analysis_policy`。已有值的欄位不可經此指令改寫。
3. 不能改動 `file`、`content_hash`、`spec_version`；`v<ver>.md` 位元不變。
4. 每次升級追加一筆 `metadata_history[]`：舊值、新值、時間、執行者、理由。
5. 補 `source_bytes_sha256` 時必須提供原檔路徑，由指令當場重算 hash；與 `content_hash` 不同時要求附說明。
6. 設成 `reference_only` 的前提：沒有任何 run、RM revision、TC 以該版本為目標或依據；否則拒絕。
7. 升級為 `reference_only` 後，該版本適用 §3.4 的 7 個拒絕入口。

---

### 5. FIX-03 引用候選掃描（**第二批**）

> 本節屬第二批：依賴第一批的 FIX-01、FIX-02；第一批的 references 由人工宣告即可運作，不依賴本節。

#### 5.1 行為

1. 新增 `bin/qaos spec scan-references <file> [--package <dir|zip>]`；`spec import` 也會自動執行同一掃描。
2. **掃描規則**：

   | 規則 | 說明 |
   |---|---|
   | ``[^\s/`]+_spec_v(\d+|NN)\.md`` | spec 檔名，可匹配 `vNN` |
   | `開發包([①-⑳]+)` | 開發包代號；逐字元拆開（「③⑧」拆成 ③、⑧ 兩個候選） |
   | `手冊\s*\d+(\.\d+)+` | 手冊章節 |
   | `\d+\.\d+(\.\d+)?\s*\S+` | 章節編號加標題 |
   | `正本` | 正本字樣 |
   | 「見／詳見／依」後接以上任一種 | 引用語 |

3. **掃描範圍**：目標檔案，以及同一包的 README、包內其他檔案提到但**包內沒附**的文件。
4. **比對結果**（每個候選附行號、命中文字）：
   - `matched`：包內 manifest 或已匯入版本中**有實際檔案**，而且 hash 已知。只有檔名、拿不到檔案時，不能算 matched。
   - `name_only`：名稱或代號對得上，但沒有檔案或 hash。
   - `unresolved`：完全對不上。
   - 同名但 hash 不同：標示差異，不是 `matched`。
5. **持久化**：結果寫進版本條目的 `reference_candidates[]`（行號、命中文字、比對結果、掃描規則版本）；人的處置寫進 `candidates_ack`（誰、何時、處置）。重新掃描是**追加**一筆新紀錄，不覆寫舊紀錄。
6. 掃描**只提出候選**，不自動寫入 references，不猜檔案或版本；寫入 references 一律經人確認後以 `spec reference add` 宣告。
7. 有未處理的 `unresolved` 或 `name_only` 候選時，匯入仍成功；但該版本當 run 目標時，`run new` 要求先 ack，或帶 `--accept-unresolved-references` 並附理由。
8. 輸出固定附注：「沒有命中不代表沒有引用，也不代表全文沒有答案」（沒有任何候選時也要附）。

#### 5.2 範圍

新模組 `tools/qaos/refscan.py`、`cli.py`、`schemas/spec/spec.schema.json`、`engine.py`（`run new` 檢查）。

---

### 6. 涉及的 schema、模組、CLI

| 類別 | 項目 | FIX |
|---|---|---|
| schema | `schemas/spec/spec.schema.json`：`references_status`、`references[]`、`reference_declarations[]`、`analysis_policy`、`source`、`metadata_history[]`；第二批加 `reference_candidates[]`、`candidates_ack` | 01、02、03 |
| schema | `schemas/common/defs.schema.json`：SpecPin、RefNode | 01 |
| 模組 | `tools/qaos/cli.py`（`spec reference add\|remove\|declare-empty`、`spec import` 的 source 參數與檢查、`spec metadata upgrade`；第二批 `spec scan-references`） | 01、02、03 |
| 模組 | `tools/qaos/store.py`（讀寫版本條目、legacy 預設值） | 01、02 |
| 模組 | `tools/qaos/engine.py`（`run new` 的 reference_only 拒絕；第二批的未處理候選檢查） | 01、03 |
| 模組 | `tools/qaos/refscan.py`（新增，第二批） | 03 |

---

### 7. 驗收 AC（全部是預期結果）

#### FIX-01

| AC | 前置條件／情境 | 預期結果 |
|---|---|---|
| AC-01-1 | 以 `spec reference add` 宣告一個不存在的 spec 版本，或 SpecPin 的 hash 與 `spec.yaml` 登記值或實體檔 sha256 不符 | 拒絕；`spec.yaml` 位元不變 |
| AC-01-2 | 未修改的舊 `spec.yaml`（沒有新欄位） | 通過 schema；讀取時 `references_status` 視為 `undeclared` |
| AC-01-3 | 對同一版本依序執行 add、remove | 各追加一筆 `reference_declarations`，`decl_rev` 遞增；舊紀錄、`content_hash`、`file` 位元不變 |
| AC-01-4 | 以 `reference_only` 版本分別作為 §3.4 的 7 個入口（spec-to-testcase、spec-change-impact 的 from 和 to、spec-to-bug、testcase-revision、manual 的 inputs.spec_id 和 spec_hint.spec_id）執行 `run new` | 每個入口各一個測試，全部拒絕，不建立 run |
| AC-01-5 | `spec reference declare-empty` 不附 reason | 拒絕 |

#### FIX-02

| AC | 前置條件／情境 | 預期結果 |
|---|---|---|
| AC-02-1 | (a) 匯入與同一 SPEC 既有版本 hash 相同的檔案；(b) 匯入與另一 SPEC 某版本 hash 相同的檔案 | (a) 拒絕並指出既有版本；(b) 成功並輸出警告 |
| AC-02-2 | 同一 SPEC、同一 `external_filename` 已以不同 hash 匯入過，再匯入新內容 | CLI 輸出「外部檔就地修改」提示；`change_summary` 空白時拒絕，有填時成功 |
| AC-02-3 | 匯入 CRLF 換行的檔案（匯入時正規化） | `content_hash` 與 `source_bytes_sha256` 都有記錄；兩者不同時輸出提示 |
| AC-02-4 | 存在 legacy 條目（沒有 `source`）時讀取與匯入 | 讀取正常；legacy 條目不被當成同名比對對象 |
| AC-02-5 | 對 legacy 條目執行 `spec metadata upgrade` | 前後 `v<ver>.md` 與 `content_hash` 位元不變；`metadata_history` 多一筆 |
| AC-02-6 | 對已被 run、RM revision 或 TC 當作目標或依據的版本，以 `metadata upgrade` 設 `reference_only` | 拒絕 |
| AC-02-7 | 以 `metadata upgrade` 設為 `reference_only` 之後，以該版本作為 7 個入口之一執行 `run new` | 依 AC-01-4 拒絕 |
| AC-10A-57 | 以正式 `spec import` 匯入 `title` 全為空白（例如全形加半形空白「　 」）的 spec | 匯入成功，並輸出 title 正規化後為空的警告 |

#### FIX-03（第二批）

| AC | 前置條件／情境 | 預期結果 |
|---|---|---|
| AC-03-1 | 以 9/29 紅包開發包的 README 為 fixture 掃描 | 偵測到 ⑧（第 31、62 行）；「③⑧」拆成兩個候選 |
| AC-03-2 | 以 SITELIST v0.6 為 fixture 掃描 | 偵測到 `後台管理員系統_spec_vNN.md`（第 5 行）與「手冊 7.1.1」（第 39 行） |
| AC-03-3 | 候選只有檔名、沒有實際檔案 | 結果為 `name_only`，不是 `matched` |
| AC-03-4 | 候選同名但 hash 不同 | 標示差異，不是 `matched` |
| AC-03-5 | 掃描沒有任何候選 | 輸出仍附「沒有命中不代表沒有引用，也不代表全文沒有答案」 |
| AC-03-6 | 對同一版本重新掃描 | 追加新紀錄，舊紀錄保留不變 |

AC 合計 19 條：AC-01-1～5、AC-02-1～7、AC-10A-57（第一批）；AC-03-1～6（第二批）。

---

### 8. 已知限制

1. `undeclared` 只代表從未宣告，不代表沒有引用；舊資料在人宣告之前一律以未宣告處理。
2. 引用宣告的正確性（是否漏宣告、role 是否正確）由人負責；第一批沒有自動掃描輔助，第二批的掃描也只提出候選，「沒有命中」不代表沒有引用。
3. `external_commit` 只是來源聲稱（`claimed: true`），系統不驗證遠端；第一批沒有解除 claimed 的指令。`external_effective_date` 只作參考，不參與任何判定。
4. legacy 條目不自動回填 `source`，也不參與同名比對，因此舊資料之間的「外部檔就地修改」無法被偵測，除非人以 `metadata upgrade` 補上 `source`。
5. `title` 正規化後為空只給警告、不阻擋匯入；這類版本在文件索取單的名稱比對中無法以 title 自動比對成立，只能以有效的外部檔名比對或人工對應。
6. 以下細節尚未定義，實作前需確認：`spec reference add|remove|declare-empty` 與 `spec import` 新參數的具體形式；`reference_declarations[]` 每筆除 `decl_rev` 外的欄位；`references_status` 在移除全部引用、或 `declared_empty` 之後再新增引用時的轉換；`declare-empty` 是否產生新的 `decl_rev`。


---

## 第 3 章　CLR 欄位、有型別來源、issue key 去重與開單關卡（FIX-06、FIX-08、FIX-07 第 1、9 點）

> 範圍：FIX-06（CLR 欄位、傳遞、`clarification metadata upgrade`）、FIX-08（有型別來源、不可變答案修訂、適用範圍、basis、effective_basis、applicability）、FIX-07 的 issue key 去重與開單關卡。
> 不含：影響批次、義務、重新納入等嚴格落地追蹤（不屬於需求 A）；操作計畫、全域鎖、續做、audit 事件檔（見操作計畫章）；CLR 狀態機、`apply`／`fulfill` 的檢查流程（見 CLR 生命週期章）；E1～E6 推導與路由表（見狀態推導章）。
> 本章所有 AC 都是**預期結果**，尚未實作。

---

### 1. 目的

1. 讓每一張 CLR 記錄「依據了哪些文件、已確定什麼、還缺什麼」，自動開單時逐欄抄自決策點，不重新撰寫。
2. 讓需求、決策點、TC、CLR 引用的依據都是**有型別、可機械驗證**的來源（spec 原文、已回答的 CLR、有效的核准決議），不再把 PM 決議偽裝成 spec 原文。
3. CLR 的答案不可覆寫；每一個答案修訂都記錄回答當時的依據（basis），跨版本或跨範圍沿用答案時必須有人工確認紀錄。
4. 開單去重只合併「完全等價」的問題：寧可多開、標示可能重複，也不錯併。
5. 所有受支援的開單入口都經過同一個關卡。

---

### 2. 名詞

共用名詞（SpecPin、RMPin、RefNode、DecisionPoint、decision_refs、CanonicalRequest、op_id、PlanStep、閉包、E1～E6）定義見共用名詞章。本章用到的定義如下：

| 名詞 | 定義 |
|---|---|
| **SpecPin** | `{spec_id, spec_version, content_hash}`；使用時 content_hash 必須同時等於 `spec.yaml` 的登記值與實體檔的 sha256。 |
| **RefNode** | 閉包中的一個節點：SpecPin＋`decl_rev`＋`role`（normative／informative）＋`depth`。 |
| **SourceRef** | 有型別的依據引用，共三型：`spec`、`clarification`、`approval`，三型都帶 `quote`（§6）。 |
| **answer_rev** | CLR 不可變答案修訂的序號（0 起算）；`answer_sha256` 為該修訂答案文字的 sha256。 |
| **basis** | 一次分析或一次回答所依據的文件集合：`{target: SpecPin, target_decl_rev, closure: [RefNode(spec_id, spec_version, content_hash, decl_rev)]（排序）}`；`closure` 只取 normative 遞移閉包（定義見第 1 章名詞表）。 |
| **basis_hash** | basis 的 canonical JSON 的 sha256。 |
| **QuestionScope** | 問題範圍：`{spec_id, requirement_id, subject, role_scope, params}`（§8）。 |
| **covers(A, D)** | 答案範圍 A 是否涵蓋決策點範圍 D（§8）。 |
| **Applicability** | CLR 的人工適用紀錄，只能追加：`{answer_rev, scope: QuestionScope, basis_hash, rationale, by, at, sha256}`（§11）。 |
| **effective_basis** | 一個 SourceRef 實際依據的身分；approval 包裝會解析到條目內部的 CLR 答案（§10）。 |
| **issue key** | 開單去重用的 canonical sha256（§4）。 |
| **Landing** | CLR 的落地紀錄，只能追加（§3.7）。 |
| **入口 A／B／C／D** | 開單入口。A：G-SPEC 通過後自動開單（現行 `engine.py` `_open_rejection_clarifications`）；B：critical 自動開單並建立 RESOLVE_AMBIGUITY 核准單（現行 `_open_clarifications`）；C：CLI 人工 `clarification new`；D：腳本直接呼叫 `clarification.new()`。所有入口最後都進 `clarification.new()`。 |

---

### 3. CLR 欄位（FIX-06）

#### 3.1 新增欄位

| 欄位 | 說明 | 寫入方式 |
|---|---|---|
| `kind` | `spec_question`／`conflict_resolution`／`document_request` | 自動入口由有效狀態決定（§3.2）；沒有 kind 的舊 CLR 視為 `spec_question` |
| `question_id` | 決策點在同一需求內的穩定 ID（`Q<NN>`） | 抄自決策點 |
| `topic` | 受控分類 | 抄自決策點 |
| `subject` | 受描述物件與面向的路徑字串，格式 `^[a-z0-9_]+(\.[a-z0-9_]+)*$` | 抄自決策點 |
| `params` | 鍵值對；鍵和值只能用 `[a-z0-9_]`，值可以是陣列；`{}` 代表沒有參數限制 | 抄自決策點 |
| `role_scope` | 角色清單，或 `["*"]`（與角色無關）；空陣列不合法（X18） | 抄自決策點 |
| `level` | 原始等級（none／minor／major／critical） | 抄自決策點 |
| `known_rules[]` | 已確定的部分，SourceRef＋quote | 抄自決策點 |
| `conflict_sides[]`、`conflict_note` | 衝突的兩側與說明 | 抄自決策點 |
| `coverage` | `references_status`、`consulted[]`（SpecPin）、`unconsulted_normative[]`、`missing_sources[]`、`waivers[]`，結構同決策點的 coverage | 抄自決策點 |
| `possible_source_missing` | 是否可能缺文件（有效狀態 E5 時為 true） | runtime 推導 |
| `decision_needed` | 只寫還缺的決策，不重問已知規則 | 抄自決策點 |
| `detail_gaps[]` | 錯誤碼、提示訊息、操作細節，和規則分開列 | 抄自決策點 |
| `issue_key` | §4 | runtime 計算 |
| `related_clarifications[]` | `{id, relation}`；relation 至少有 `prior_version`、`possible_duplicate` | runtime 去重時寫入 |
| `answer_revisions[]` | 不可變答案修訂（§7） | `answer` 追加 |
| `applicability[]` | 人工適用紀錄（§11） | `applicability add` 追加 |
| `evidence_addenda[]` | 補充佐證（§3.6） | 只能追加 |
| `landings[]` | 落地紀錄（§3.7） | 只能追加 |
| `document_items[]` | 文件索取單的逐項清單（§3.4） | 建立時產生；`fulfill`、`waive-item` 更新 |
| scan 紀錄的連結 | 連到 `clarification impact` 保存的掃描紀錄 | `impact` 寫入 |

`spec_id`、`requirement_id` 等既有欄位保留。頂層的 `answer` 欄位保留，作為最新答案修訂的檢視。

#### 3.2 kind 的決定（自動入口）

依決策點的有效狀態（推導規則見狀態推導章）：

| 有效狀態 | kind |
|---|---|
| E2（衝突未決） | `conflict_resolution` |
| E3（缺文件） | `document_request` |
| E4（未定義，已查證） | `spec_question` |
| E5（未定義，未查證） | `spec_question`，`possible_source_missing: true` |

每個 E2～E5 的決策點各算一個 issue key；開單數等於不同 issue key 的數量（key 相同時連結，不重複開單）。

#### 3.3 自動入口 A、B 逐欄抄寫

- 以下 **12 個欄位**從來源決策點逐欄抄寫，不重新撰寫：
  `question_id, topic, subject, params, role_scope, level, known_rules, conflict_sides, conflict_note, coverage, decision_needed, detail_gaps`。
- `kind` 由有效狀態決定；`possible_source_missing`、`issue_key` 由 runtime 計算。
- `known_rules` 的每個 SourceRef 都依 §6 驗證；quote 不在來源 → 拒絕開單。
- 人工入口 C 以 CLI 參數提供同樣的欄位（參數名稱見已知限制）。

#### 3.4 文件索取單

- `document_request` 的 `coverage.missing_sources` **至少一項**。每一項只需要**引用處**：`{cited_at: SpecPin＋line＋text, name}`；**不需要**缺檔本身的 hash。沒有引用處 → 拒絕。
- 建立時，`missing_sources` 的每一項各成為一個 `document_items[]`：`{item_id, cited_at, name, status: open}`。
- 每次 `fulfill` 追加一筆 `fulfillments[]`（只能追加）：
  `{item_id, document_pin: SpecPin, target_pin: SpecPin, target_decl_rev, match: {method: name_match | human_mapping, matched_text?, reason?, by}, op_id, at, sha256}`。
- `waive-item` 把項目標為 `waived`。逐項判定、名稱比對、結案條件見 CLR 生命週期章。

#### 3.5 答案修訂（欄位）

`answer_revisions[]` 每筆：`{rev, answer, answered_by, answered_at, resolution, answer_sources[], basis, basis_hash, sha256}`。
- `resolution`：`requirement_clarified`／`spec_updated`／`no_change`／`out_of_scope`。
- `answer_sources[]`：答案的出處（spec、document 或 message 型，帶完整身分），驗證規則見 CLR 生命週期章。
- 不可變規則、basis 的記錄方式見 §7。

#### 3.6 evidence_addenda

- 只能追加。內容是一筆來源（document 型：`file_name`、`sha256`、`package_sha256`、`location`；或 spec 型 SourceRef）加說明 `note`，並記錄 `by`、`at`。
- **不改變**答案、`answer_sha256`、`answer_revisions`、狀態。
- 用途：例如 PM 重申同一決議的回覆檔，附加為佐證；**真正改變決議**時必須另開 CLR（relation `prior_version`）。

#### 3.7 landings 的最終形狀

`landings[]` 只能追加，每筆都有 `type`、`op_id`、`at`：

| type | 寫入時機 | 欄位 |
|---|---|---|
| `incorporated` | revision 或 BugDraft 以明確 SourceRef 引用本 CLR 最新 answer_rev（納入；含再次引用） | `rm_pin`（revision 時）或 `bug_draft`（BugDraft 時）、`run_id`、`op_id`、`at` |
| `applied` | `clarification apply` 成功 | 見下表 |

`applied` landing 的欄位：

| 欄位 | a6 | a6b | a7 | 說明 |
|---|---|---|---|---|
| `path` | ✓ | ✓ | ✓ | `a6`／`a6b`／`a7` |
| `landed_in[]` | ✓ | ✓（恰好一個） | — | 落地 run |
| `targets_confirmed[]` | ✓ | ✓ | — | 確認的採用目標（帶 product、area） |
| `targets_deferred[]` | ✓ | — | — | 延後的目標與理由 |
| `final_keywords[]` 或 `no_keyword_reason` | ✓ | ✓ | ✓ | 最終關鍵字（CLI 關鍵字與 scan 關鍵字的聯集）；空集合時保存理由 |
| `scan_id`、`scan_answer_rev` | 選填 | 選填 | 選填 | 使用 `--scan` 時記錄 |
| `scan_reused` | ✓ | ✓ | ✓ | `keywords_only`（scan 屬於舊答案修訂或規則版本不同，只沿用關鍵字）／`full` |
| `rule_version` | ✓ | ✓ | ✓ | 掃描規則版本 |
| `scan_units[]` | ✓ | ✓ | ✓ | 掃描單位 `(product, area)` |
| `candidates[]` | ✓ | ✓ | ✓ | 鎖內重新掃描的候選 `{tc_id, active_version, tc_version_sha256, reasons[]}` |
| `conclusions[]` | ✓ | ✓ | ✓ | 每張候選的結論 |
| `scan_sha256` | ✓ | ✓ | ✓ | 鎖內候選掃描結果的 sha256 |
| `reference_scan_sha256` | — | — | ✓ | 「全部歷史都沒有引用」掃描結果的 sha256 |

產生這些欄位的檢查流程見 CLR 生命週期章。

#### 3.8 PM 用的頁面

`clarification._render` 產生的 `.md` 要渲染：「已查文件」、「已確定的部分」、「還需決定的事」、「衝突兩邊」。舊 CLR 沒有這些欄位時，不顯示這些段落。

#### 3.9 legacy 相容與 `clarification metadata upgrade`

- 舊 CLR 不修改也能通過 schema。
- `bin/qaos clarification metadata upgrade`：
  - 只能由人執行，以操作計畫執行（寫入規則見操作計畫章）。
  - **只能補** legacy 缺的欄位：`kind`、`question_id`、`subject`、`role_scope`、`params`；不能改寫既有欄位（例如已存在的 `spec_id`、`requirement_id`）。
  - 追加 history；**答案、answer_revisions 和狀態都不變**。
  - 用途：讓舊 CLR 有自己的答案範圍（§8），`covers` 才可能成立。

#### 3.10 證據力與限制

- **能證明**：派發包提供了哪些版本（hash 可驗證）；`known_rules` 的 quote 逐字存在於對應來源。
- **不能證明**：agent 讀懂了；「已查文件都沒有答案」這種否定陳述；關鍵字沒命中不等於沒有答案。

---

### 4. issue key 與去重（FIX-07 第 1 點）

#### 4.1 issue key

issue key = 以下欄位 canonical JSON 的 sha256：

```text
{kind, spec_id,
 basis: 和 basis_hash 相同的完整 basis 物件
        {target: 目標 SpecPin, target_decl_rev, closure: normative 閉包的 RefNode（依 (spec_id, spec_version) 排序、去重）},
 requirement_id, topic, subject,
 params: 依鍵排序；值為陣列時排序、去重,
 role_scope: 排序、去重}
```

- canonical JSON：鍵依字典序排列、不含空白、UTF-8、不做 Unicode 正規化。
- **自由文字（`decision_needed`、說明）不進 key。**

#### 4.2 去重規則（依序判斷；只適用於新請求，也就是新的 op_id）

| 順序 | 條件 | 處理 |
|---|---|---|
| 1 | `topic: other`（此時 `subject` 必須非空） | **永遠新開**，不自動連結。同需求下其他 `other` 的單列進 `related_clarifications`，relation `possible_duplicate` |
| 2 | 已有任一非 WITHDRAWN 的 CLR，issue key **完全相同** | **不新開，改成連結**。入口 B 仍要把該 CLR 加進核准單的 `impact`；audit 記錄 `LINK_CLARIFICATION` |
| 3 | 只有 `basis` 不同，其他 key 欄位都相同 | 新開，relation `prior_version`，**只作追溯**；能否沿用舊答案一律依 X16（§9.3） |
| 4 | 舊 CLR（沒有 issue key）而且同 `requirement_id` | 新開，relation `possible_duplicate`，audit 留警告；由人決定是否撤回 |
| 5 | 其他（例如同需求、不同 subject 或不同角色） | 新開 |

- 自動去重只比對完全相同的 key，不判斷語意。原則：**寧可多開、標示可能重複，也不可錯併**。
- 同一請求重送（同一 op_id）時沿用計畫中已配發的 CLR ID，不會因為 `other` 規則多開一張（續做規則見操作計畫章）。

---

### 5. 開單關卡（FIX-07 第 9 點）

關卡在 `clarification.new()` 內，所有入口共用：

| 開單者 | 必要條件 |
|---|---|
| agent 或 system（入口 A、B） | 決策點欄位齊全並通過驗證（§3.3 的 12 欄、SourceRef 驗證） |
| 人工 CLI（入口 C） | 必須帶 `--consulted <spec_id@ver>`（可重複），或 `--no-source-check --reason <文字>`；理由寫進 history |
| 腳本（入口 D） | 沿用同一個函式，自動受同樣約束 |

- 只保證**受支援的入口**；直接寫檔繞過 API 不在保證範圍。
- `--by` 只是字串，不是權限邊界；本需求只保證留下可稽核的紀錄。
- 關卡驗證失敗時不寫任何業務檔（失敗處理見操作計畫章）。

---

### 6. SourceRef（FIX-08）

#### 6.1 三型與驗證

| type | 必要欄位 | 驗證（任一不成立 → 該 SourceRef 驗證失敗，X10） |
|---|---|---|
| `spec` | SpecPin、`location`、`quote` | SpecPin 的 hash 和登記值、實體檔都相符；quote 正規化後必須逐字存在於該實體檔；spec 必須是目標，或在目標版本的 normative／informative 閉包內 |
| `clarification` | `clarification_id`、`answer_rev`、`answer_sha256`、`quote` | 被釘選的 `answer_revisions[answer_rev]` 存在、hash 相符；quote 在**該修訂**的答案中；該修訂的 resolution 是 `requirement_clarified` 或 `spec_updated` |
| `approval` | `approval_id`、`decision_sha256`、`resolution_index`、`quote` | 核准單類型是 RESOLVE_AMBIGUITY，決議是 approve 或 override；`decision_sha256` 對 decision 區塊（canonical JSON）計算並相符；`decision.resolutions[resolution_index]` 的 `requirement_id`、`question_id` 等於引用處；quote 在該條目的 `rationale` 中 |

- 未回答的 CLR（OPEN、ASKED）沒有答案修訂，不能被引用。
- 作為 resolution 的 clarification 來源，CLR 必須是 ANSWERED、INCORPORATED 或 APPLIED（X15）。
- ACTIVATE 等其他類型核准單的 rationale **不算**裁決。
- **防偽裝**：把 CLR 原文標成 `type: spec` → quote 不在 spec 實體檔 → FAIL。

#### 6.2 quote 規則

- **正規化只處理三件事**：連續空白合併、移除 `**`、移除行首的 markdown 引用符號。其他差異一律 FAIL。
- 新產出的 quote 不能是空字串，也不能缺。
- `location` 必須非空。
- 章節核對是**警告層級**：`location` 以 `§標題` 開頭時，檢查實體檔有沒有這個標題；沒有就警告，不 FAIL。

#### 6.3 適用位置

- 需求的 `source_refs[]`（舊的 `spec_reference` 保留，視為 `type: spec` 的舊格式）
- 決策點的 `known_rules`、`conflict_sides`、`resolution`
- TC 的 expected 依據、`decision_refs[].basis_ref`
- RR 的 `spec_basis`
- CLR 的 `known_rules`
- bug schema：第一批只放寬型別；bug flow 的 SourceRef 強制屬第二批

#### 6.4 legacy quote

- 舊資料（例如 quote 寫「（v07 定案已作廢，見 CLR-CASHFLOW-005…）」）**不 FAIL**，也**不自動改寫**。
- 之後的新 revision 只要沿用該需求，就必須改成型別化來源（例如 `type: clarification`）。
- 不合格清單由第二批的 `refs report` 列出。

---

### 7. 答案修訂、basis、basis_hash

1. **不可變**：`answer()` 每次寫入都**追加**一筆 `answer_revisions[]`，舊修訂位元不變。
2. **rev 0**：舊 CLR 第一次透過新版 `answer()` 寫入，或被移轉處理時，先把既有答案存成 rev 0，其 hash 等於原答案文字的 sha256。
3. **basis 的記錄**：
   - 新答案：`answer` 時由 runtime 記錄該修訂的 `basis`、`basis_hash`。
   - legacy 答案（rev 0）：移轉時以 CLR 的 `spec_id`、`spec_version` 從 registry 取 content_hash，`target_decl_rev: 0`、`closure: []`；這些值由移轉計畫固定（第 5 章 §3、§11.5）。
4. **依釘選的 rev 驗證**：clarification 型 SourceRef 一律對照它釘選的 `answer_rev` 驗證，不對照目前答案。舊 run、舊 revision 在之後有新答案時，恢復驗證仍 PASS（歷史有效）。
5. **decision_revised**：新派發時，若上一個 revision 引用的不是該 CLR 的最新 answer_rev → 對應決策點標 `decision_revised`；新 RM 必須重新判定，否則 G-SPEC FAIL。
6. 派發包保存所用決議的快照（answer_rev、answer_sha256、答案全文、basis_hash、applicability），舊 run 恢復時可以自給自足（派發包規則見派發包章）。

---

### 8. QuestionScope 與 covers

- **QuestionScope** = `{spec_id, requirement_id, subject, role_scope, params}`。
  - `role_scope`：必須明示；角色清單或 `["*"]`。空陣列不合法（X18）。
  - `params`：`{}` 代表沒有參數限制。
- **`covers(A, D)`**（答案範圍 A 涵蓋決策點範圍 D），以下全部成立：
  1. `A.spec_id == D.spec_id` 而且 `A.requirement_id == D.requirement_id`；
  2. `A.subject == D.subject`；
  3. 角色：`A.role_scope == ["*"]`，或 `D.role_scope ⊆ A.role_scope`；D 為 `["*"]` 時，A 也必須是 `["*"]`；
  4. params：A 的每個鍵都必須出現在 D 中而且值相等（陣列時 D 的值 ⊆ A 的值）；A 沒有的鍵代表 A 不限制該維度，D 可以有額外的鍵。
- **答案範圍的來源**：
  - 新 CLR：自身的 `spec_id, requirement_id, subject, role_scope, params`。
  - 舊 CLR（沒有 subject）：**沒有答案範圍**；只能用 `applicability[]`，或以 `clarification metadata upgrade` 補上欄位。
- **跨 spec**（答案的 spec_id 和決策點不同）：只能走 `applicability[]`。
- 不能用缺欄位代表全域適用。

---

### 9. X12、X15、X16

#### 9.1 X12：basis 和來源型別的對應

| 決策點 basis | `known_rules` 至少一筆必須是 | 其他 |
|---|---|---|
| `defined_in_target` | `spec` 型，SpecPin 等於目標 | 可另附參考或決議作補充 |
| `defined_in_reference` | `spec` 型，SpecPin 在閉包內、不等於目標 | 同上 |
| `defined_by_decision` | `clarification` 或 `approval` 型，而且通過 X16 | 同上 |
| `undefined` | 不限；`known_rules` 只當背景，**不能**作為 TC 對這個決策點的 expected 依據 | — |
| `conflict` | `conflict_sides` 至少兩筆 | — |

不對應 → X12（G-SPEC FAIL）。

#### 9.2 X15：resolution 條目

以下任一成立 → X15（G-SPEC FAIL）：
- `resolution.source` 是 approval 型，但對應條目的 outcome 不是 `select_interpretation`，或缺 `rationale`；
- approval 條目的 `requirement_id`、`question_id` 和引用處不同；
- `resolution.source` 是 clarification 型，而該 CLR 不是 ANSWERED、INCORPORATED、APPLIED；
- **巢狀 approval**：approval 條目的 `source` 又是 approval 型；
- 以**決議為 reject** 的核准單作為 approval 型 SourceRef（只接受 approve 或 override）。

#### 9.3 X16：適用範圍與 basis

clarification 型來源**作為依據**（`defined_by_decision` 的依據）**或 resolution** 時，以下二選一必須成立，否則 X16 FAIL：

- **(a) 答案自身**：該 `answer_rev` 的 basis_hash **等於**決策點本次的 basis_hash，而且 CLR 自身的 QuestionScope `covers` 決策點的 QuestionScope；
- **(b) 人工紀錄**：`applicability[]` 中有一筆 `answer_rev` 相同、`basis_hash` 等於本次 basis_hash、而且 `scope covers` 決策點 scope 的紀錄。

補充：
- 解析 SourceRef 時**一律比較**，不論有沒有開過新 CLR、有沒有 `prior_version` 關係。
- basis 沒變而且自身 scope 涵蓋時直接成立，不需要另外開單或人工紀錄。
- 同一版本只改了宣告（閉包中某節點的 decl_rev 改變）也會改變 basis_hash，同樣需要 (a) 或 (b)。
- **approval 型**：遞迴對 `resolutions[resolution_index].source` 執行 X16；外層合法不代表內層通過。
- 只當背景的 `known_rules`（basis 為 undefined）不檢查 X16。
- 不會因為 quote 吻合就自動視為適用。

---

### 10. effective_basis

依 SourceRef（含 `decision_refs[].basis_ref`）的型別解析：

| 型別 | effective_basis |
|---|---|
| `clarification` | `(clarification_id, answer_rev, answer_sha256)` |
| `approval` | 解析 `approval.decision.resolutions[resolution_index]`，以下全部成立：核准單類型是 RESOLVE_AMBIGUITY；決議是 approve 或 override；`decision_sha256` 相符；條目 outcome 是 `select_interpretation`；條目的 `requirement_id`、`question_id` 等於引用處。<br>• 條目 `source` 是 clarification 型 → effective_basis 是該 source 的 `(clarification_id, answer_rev, answer_sha256)`（approval 包裝）。<br>• 條目 `source` 是 null（核准者自行裁決）→ effective_basis 是 `(approval_id, resolution_index, decision_sha256)`，**不是任何 CLR**。<br>• 條目 `source` 是 approval 型（巢狀）→ 不合法（X15）。 |
| `spec` | `(spec_id, spec_version, content_hash, location)`，不是 CLR |

- 解析時，條目本身也必須通過 X16。
- 「經 approval 包裝引用 CLR」和「直接引用 CLR」解析到同一個 effective_basis。
- 真正的其他來源（其他 CLR、核准者自行裁決、spec 原文）不會解析成這張 CLR。
- **決議為 reject 的核准單不是 approval 包裝**：
  - effective_basis 只接受 approve 或 override 的包裝；G-SPEC 中以 reject 核准單作為 approval 型 SourceRef → X15 FAIL，不會被當成裁決。
  - bug reject 路徑（apply `--path a6b`）的依據是 reject 決議條目**內部的** clarification `source`；該 reject 核准單只是**落地證據**。條目內部的 source 必須指向本 CLR 的最新 answer_rev，並通過 X16 的 scope 與 basis 檢查（apply 檢查見 CLR 生命週期章）。
- effective_basis 的使用者：A4 納入判定、apply 的採用目標解析、A7「全部歷史都沒有引用」的檢查（approval 包裝要展開）、`clarification stale-tcs`（見 CLR 生命週期章）。

---

### 11. `clarification applicability add`

```text
bin/qaos clarification applicability add <CLR>
    --answer-rev <N>
    --requirement <REQ> --subject <subject> --role-scope <角色…|*> --params <鍵值…|{}>
    --target <spec_id@ver>
    --rationale <文字> --by <人>
```

- **只有人**可以執行；`--by` 為 agent 或 system → 拒絕。
- `requirement`、`subject`、`role_scope`、`params` **全部必填**；`["*"]`、`{}` 都必須明示，缺任何一維 → 拒絕。
- CLI 依 `--target` 指定的目標版本**計算並顯示**本次的 basis_hash，由人確認後才寫入。
- 寫入 `applicability[]`：`{answer_rev, scope: QuestionScope, basis_hash, rationale, by, at, sha256}`；**只能追加**。
- 可在任何非 WITHDRAWN 的狀態追加；**不改變**狀態與答案。
- 以操作計畫執行（操作類型 `applicability_add`）。
- 不禁止跨 product 的 applicability；跨 product 目標的候選掃描依 `(product, area)` 處理（見 CLR 生命週期章）。

---

### 12. APPLIED 之後

- APPLIED 的 CLR **不追加答案修訂**；企圖追加 → 拒絕。
- 只能追加 `applicability`、`evidence_addenda`、`landings`；狀態、`answer_sha256`、`answer_revisions` 不變。
- 要改變決議 → 另開 CLR，relation `prior_version`。

---

### 13. 沒有自動的日期優先

- spec 原文和決議不一致 → 判為 `conflict` 決策點；必須有**明確指名這個衝突**的 resolution，才算 E1。
- `external_effective_date`、`answered_at`、`decided_at` 只當參考資訊顯示，不自動決定優先序。

---

### 14. 涉及的 schema、模組、CLI

| 類別 | 項目 |
|---|---|
| schema | `schemas/common/defs.schema.json`（SourceRef、QuestionScope）、`schemas/spec/clarification.schema.json`、`schemas/spec/requirement.schema.json`、`schemas/approval/approval-request.schema.json`（`decision.resolutions[]`）、`schemas/artifact/testcase-draft.schema.json`、`schemas/testcase/testcase-version.schema.json`、`schemas/artifact/tc-risk-review.schema.json`、`schemas/artifact/bug-draft.schema.json`、`schemas/bug/bug.schema.json`（只放寬） |
| 模組 | 新增 `tools/qaos/sources.py`（SourceRef 驗證、quote 正規化、covers、X16、effective_basis 解析）；`refs.py`；`gates.py`（G-SPEC、G-DESIGN、G-RISK）；`clarification.py`（`new` 的關卡與去重、`_render`、`answer` 的修訂、`applicability add`、evidence_addenda 追加、`metadata upgrade`）；`engine.py`（入口 A、B 的開單與逐欄抄寫、核准時驗證 resolutions）；`cli.py` |
| CLI | `clarification new --consulted …`／`--no-source-check --reason …`；`clarification applicability add`；`clarification metadata upgrade`；第二批：`refs report` |

---

### 15. 驗收 AC（全部是預期結果，尚未實作）

#### 15.1 CLR 欄位（AC-06）

| AC | 前置條件／情境 | 預期結果 |
|---|---|---|
| AC-06-1 | 入口 A 或 B 自動開出 CLR | 12 個欄位（`question_id, topic, subject, params, role_scope, level, known_rules, conflict_sides, conflict_note, coverage, decision_needed, detail_gaps`）和來源決策點逐欄相等（深度比較） |
| AC-06-2 | 開單時 `known_rules` 的某個 quote 不在其來源中 | 拒絕開單 |
| AC-06-3 | 文件索取單的 `missing_sources` 只有引用處、沒有缺檔 hash；另一張完全沒有引用處 | 前者通過；後者拒絕 |
| AC-06-4 | 未修改的舊 CLR | 通過 schema；渲染時不顯示新段落 |
| AC-06-5 | 對舊 CLR 執行 `clarification metadata upgrade` | 只能補缺的欄位；企圖改寫既有欄位 → 拒絕；答案和狀態不變；history 多一筆 |

#### 15.2 issue key 去重（AC-07）

| AC | 前置條件／情境 | 預期結果 |
|---|---|---|
| AC-07-1 | REQ-DAILYREPORT-011 已有 CLR-010（topic `aggregation_rule`，subject `cashout.redeemed_amount.attribution_date`）；新問題 subject `cashout.voided_receipt.display` | 新開 |
| AC-07-2 | REQ-DAILYREPORT-001 已有 CLR-001（role_scope `[operator]`）；新問題 role_scope `[admin, site_manager]` | 新開 |
| AC-07-3 | 同需求、同 topic `display_rule`，subject 分別為 `csv_export.header_when_empty` 和 `csv_export.decimal_format` | 兩張都新開 |
| AC-07-4 | `topic: other`，兩種不同 subject；以及相同 subject 再出現一次 | 不同 subject 兩張都新開，互相標 `possible_duplicate`；相同 subject 仍新開並標記 |
| AC-07-5 | 同一個 RM 重送 G-SPEC，入口 A、B 各測一次 | 不會重複開單；入口 B 連結時，核准單的 `impact` 包含該 CLR |
| AC-07-6 | params `{role: [b, a]}` 與 `{role: [a, b, a]}`；以及鍵順序不同的同內容 params | 算出相同的 issue key |
| AC-07-7 | 只有 basis 不同（例如 spec 換版），其他 key 欄位相同 | 新開，`related_clarifications` 帶 `prior_version`（只作追溯，不產生待人判定的沿用狀態） |
| AC-07-10 | `topic: other` 的 CLR 已寫入後中止 → 重送同一請求 | 沿用計畫中的 CLR ID，沒有第二張 |
| AC-07-11 | 以新的輸入（新 iteration）再問一次同樣的 `other` 問題 | 新開，標 `possible_duplicate`（屬新請求） |
| AC-07-101 | agent 或 system 開單（入口 A、B）時，決策點欄位不齊全 | 拒絕；業務檔不寫入（同 AC-07-8 的診斷寫入規則） |
| AC-07-102 | 人工 `clarification new`：(a) 沒有 `--consulted`，也沒有 `--no-source-check --reason`；(b) 帶 `--no-source-check --reason <文字>`；(c) 帶 `--consulted <SpecPin>…` | (a) 拒絕，不寫入；(b) 成立，理由寫入 history；(c) 成立，consulted 寫入 CLR |
| AC-07-103 | 同一 requirement 已有 legacy CLR（沒有 issue key）時，以新問題開單 | 新開，新單標 `possible_duplicate`，並寫一筆 audit 警告事件 |
| AC-07-104 | fixture 前提：topic 用一般受控詞（例如 `permission`，不能用 `other`，因為 `other` 一律新開）；既有單有 issue key、不是 WITHDRAWN；兩次開單是不同 op 的新請求（不是同一請求重送）。同一需求、同一 topic／subject／params／role_scope 的問題，前後兩次開單之間：(a) 只有目標 spec 的 `target_decl_rev` 改變（例如沒有引用的目標執行 `declare-empty`；內容 hash 與閉包都沒變）；(b) `target_decl_rev` 也沒變 | (a) issue key 不同 → 新開，`related_clarifications` 帶 `prior_version`；(b) issue key 相同 → 連結既有的單，不新開 |

AC-07-8（驗證失敗時業務檔 hash 不變）屬於驗證失敗處理，列在操作計畫章；它也涵蓋開單關卡失敗時不寫入。

開單關卡由 AC-07-101、102 驗收；legacy 同需求標 `possible_duplicate` 由 AC-07-103 驗收（附錄 A 3-1、3-2）。`LINK_CLARIFICATION` audit 事件併入 AC-07-5 驗收。

#### 15.3 有型別來源、答案修訂、適用範圍（AC-08）

| AC | 前置條件／情境 | 預期結果 |
|---|---|---|
| AC-08-1 | spec 型 quote：逐字存在；只差空白或 `**`；有其他差異 | 前兩者 PASS；其他差異 FAIL |
| AC-08-2 | 新產出的 quote 為空或缺；舊資料的不合格 quote | 新產出 FAIL；舊資料不 FAIL |
| AC-08-3 | spec 型 SourceRef 引用目標閉包以外的 spec | FAIL |
| AC-08-4 | 依 CLR-CASHFLOW-005（APPLIED，移轉後有 rev 0）的決議產生新 Draft，SourceRef 用 `type: clarification` | **SourceRef 本身**的驗證 PASS（釘選 rev 的 answer_sha256、quote）。作為本次決策的依據或 resolution 時，還必須通過 X16（basis 與 scope 相符，或有相符的 applicability），否則完整的 G-SPEC FAIL（見 AC-08-38）。測試不得只呼叫基本解析就宣稱 Draft 或 G-SPEC 有效 |
| AC-08-5 | clarification 型 SourceRef 引用 OPEN 或 ASKED 的 CLR | FAIL |
| AC-08-6 | clarification 型來源作為依據或 resolution，CLR 自身範圍不涵蓋引用處，也沒有相符的 applicability | FAIL（X16） |
| AC-08-7 | 把 CLR 原文標成 `type: spec` | FAIL |
| AC-08-8 | `location` 的 `§標題` 在實體檔中不存在 | 只警告，不 FAIL |
| AC-08-9 | approval 型 SourceRef 引用 ACTIVATE_TESTCASE 的核准單 | FAIL |
| AC-08-10 | 舊 run 釘選 rev 1（H1），之後答案更新為 rev 2（H2）；舊 run 恢復 | 依 rev 1 驗證，PASS |
| AC-08-11 | 新 run 派發時，上一個 revision 引用 rev 1，最新是 rev 2 | 決策點標 `decision_revised`；新 RM 沒有重新判定就 FAIL |
| AC-08-12 | approval 型 SourceRef 的條目 `requirement_id` 或 `question_id` 和引用處不符 | FAIL |
| AC-08-13 | 同一份核准單被引用到沒有列在 `resolutions` 中的需求 | FAIL |
| AC-08-14 | 舊 CLR 第一次被新版 `answer()` 寫入 | rev 0 的 hash 等於原答案文字的 sha256 |
| AC-08-15 | spec 原文和決議不一致，但沒有 resolution | 判為 conflict；不會因為日期較晚就自動採用 |
| AC-08-16 | REQ-DAILYREPORT-012（v0.3）以 CLR-010 rev 0 作 resolution；CLR-010 有一筆人建立的 applicability，scope 為完整 QuestionScope `{SPEC-DAILYREPORT-001, REQ-DAILYREPORT-012, report.cash_net.semantics, ["*"], {}}` | PASS（basis_hash 也相符時；basis_hash 的驗收見 AC-08-32）。CLR 自身範圍為 REQ-DAILYREPORT-011；本 AC 的 REQ-012 是人建立的 applicability 的目標（附錄 A 3-31） |
| AC-08-17 | 同 AC-08-16，但沒有 applicability | X16 FAIL |
| AC-08-18 | agent 或 system 執行 `applicability add` | 拒絕 |
| AC-08-19 | 對 APPLIED 的 CLR 追加 `evidence_addenda`；另企圖追加答案修訂 | 追加 addenda 後狀態、`answer_sha256`、`answer_revisions` 都不變；追加答案修訂被拒絕 |
| AC-08-20 | 答案範圍 A：REQ-001、subject S、`[operator]`、`{}`；決策點 D：REQ-001、S、`[admin, site_manager]`、`{}` | 不涵蓋 → X16 FAIL，不能成為 E1 |
| AC-08-21 | A：REQ-001、S、`["*"]`、`{target_scope: own_venue}`；D：REQ-001、S、`[admin]`、`{target_scope: out_of_scope}` | 不涵蓋（params 值不同） |
| AC-08-22 | A：REQ-001、S、`[admin]`、`{}`；D：REQ-001、S、`[admin, site_manager]`、`{}` | 不涵蓋（site_manager 不在 A 中） |
| AC-08-23 | A：REQ-001、S、`[admin, site_manager]`、`{}`；D：REQ-001、S、`[admin]`、`{target_scope: out_of_scope}` | 涵蓋 |
| AC-08-24 | 舊 CLR 加上人建立的 applicability `{REQ-001, S, [admin, site_manager], {}}`；D：REQ-001、S、`[admin, site_manager]`、`{}` | 涵蓋 |
| AC-08-25 | `applicability add` 省略 `role_scope` | 拒絕 |
| AC-08-26 | CLR-010 的 applicability scope `{SPEC-DAILYREPORT-001, REQ-012, report.cash_net.semantics, ["*"], {}}`；D 為相同 scope | 涵蓋 → E1 |
| AC-08-27 | CLR 在 v0.1 回答（basis_hash H1）；v0.2 的決策點 basis_hash H2、scope 相同；沒有開任何新 CLR；以它作 resolution | X16 FAIL（H1 ≠ H2 且沒有人工紀錄），不是 E1 |
| AC-08-28 | 同一版本，只有宣告改變（閉包中某節點的 decl_rev 改變）→ basis_hash 改變 | X16 FAIL |
| AC-08-29 | 人執行 `applicability add --answer-rev 0 --target <SPEC>@0.2 …`，CLI 顯示 H2，人確認 | 成立 → E1 |
| AC-08-30 | basis 沒變（H1 = H1），自身 scope 涵蓋 | 直接成立；沒有新單、沒有人工紀錄 |
| AC-08-31 | 人工紀錄的 basis_hash 是 H2，但決策點後來改成 H3（宣告又改變） | FAIL，需要新的紀錄 |
| AC-08-32 | CLR-010 rev 0 的 basis 是 DAILYREPORT 0.1（legacy，閉包空）；REQ-012 在 0.3 的 basis 為 0.3＋閉包；人建立 `{answer_rev: 0, scope: {SPEC-DAILYREPORT-001, REQ-DAILYREPORT-012, report.cash_net.semantics, ["*"], {}}, basis_hash: <0.3 本次的 hash>}` | 成立 → E1；紀錄明確記下人核對的是 0.3 那一次的 basis |
| AC-08-33 | approval 型 SourceRef：外層核准條目合法，但內層 clarification source 的 basis 不符（沒有 (a) 也沒有 (b)） | X16 FAIL |
| AC-08-34 | approval 條目的 `source` 又是 approval 型（巢狀） | X15 FAIL |
| AC-08-35 | `covers`：答案 A 的 params 為 `{mode: cash}`，決策點 D 為 `{}`；其他欄位相同 | 不涵蓋（A 比 D 窄）→ 作為依據或 resolution 時 X16 FAIL |
| AC-08-36 | `covers`：答案 A 的 params 為 `{}`，決策點 D 為 `{mode: cash}`；其他欄位相同 | 涵蓋（A 不限制 mode） |
| AC-08-37 | `covers`：A 為 `{mode: [cash, credit]}`、D 為 `{mode: [cash]}` → 涵蓋；A 為 `{mode: [cash]}`、D 為 `{mode: [cash, credit]}` → 不涵蓋 | 依 `covers` 的陣列子集規則 |
| AC-08-38 | legacy CLR（rev 0 的 basis 閉包為空）的答案，作為本次決策的依據或 resolution；分別在 (a) 本次 basis_hash 與 rev 0 不同、沒有相符的 applicability；(b) 有人建立、basis_hash 與 scope 都相符的 applicability | (a) SourceRef 本身驗證 PASS，但 X16 FAIL，G-SPEC FAIL；(b) X16 PASS |
| AC-10A-46 | 見第 6 章（同一條，以第 6 章為準） | — |

AC 可驗收的最早階段：AC-06 的 schema 與 `metadata upgrade` 可先驗；入口 A、B 逐欄抄寫要等決策點與開單實作。AC-08 中 SourceRef 驗證函式可先以單元測試驗收，涉及 G-SPEC 的部分要等 G-SPEC 新檢查實作後才完整驗收。去重 AC 要等決策點與開單實作。早期階段不手造業務狀態，也不把還不能執行的 AC 標成通過。

---

### 16. 已知限制

1. 查閱證據（consulted）是自我申報：只證明有提供、hash 正確，不證明讀過或讀懂；不能證明「已查文件都沒有答案」。
2. 開單關卡只保證受支援的入口；直接寫檔可以繞過；`--by` 不是權限邊界。
3. 去重只比對完全相同的 issue key，不判斷語意；可能多開，靠 `possible_duplicate` 標示由人處理。
4. 人建立的 applicability 是否真的適用，由人負責；系統只驗證範圍與 basis 是否相符。
5. legacy quote 不 FAIL、不自動改寫；不合格清單要到第二批的 `refs report` 才能列出。
6. bug flow 的 SourceRef 強制屬第二批；第一批 bug schema 只放寬型別。
7. 人工入口 C 以 CLI 提供 12 個欄位的參數名稱尚未定案；`topic` 受控詞的初始清單尚未定案。


---

## 第 4 章　executor 基礎設施（FIX-07：操作身分、全域操作鎖、操作計畫、續做、audit、維護模式）

> 本章所有 AC 都是**預期結果**，尚未實作、尚未執行。
> 本章不含：issue key 去重與開單關卡（見「去重與開單關卡」章）；rollback 接管准入 T1～T7、`x_progress`、R 的步驟群組、檢查 A／B、`later_ops_snapshot`、移轉清單（見「移轉與回復」章）。

---

### 1. 目的

QAOS 的每一個會寫入 repo 的操作，都必須：

1. 在**同一台主機上同一時間只有一個 executor** 寫入；
2. 寫入前先保存一份**不可變的操作計畫**，所有 ID、時間、每個檔案的最終內容都事先固定；
3. 中途被中止（崩潰、`kill -9`、例外）後，以**同一請求重送**或 `operation resume` 續做到計畫的最終狀態，不產生重複的業務物件；
4. 稽核證據（事件、完成紀錄、登錄、狀態）被刪改時能被發現並停止，不重寫、不偽造；
5. 移轉前不改動任何既有的 `audit.log`。

不承諾多檔原子性；承諾的是「驗證失敗不寫業務檔」與「可續做到計畫的最終狀態」。

---

### 2. 名詞

| 名詞 | 定義 |
|---|---|
| SpecPin、RMPin、SourceRef、QuestionScope、basis_hash、effective_basis | 定義見共用名詞章 |
| **CanonicalRequest** | 一次寫入請求的正規化內容（action、targets、語意參數、inputs、可選的 `new_request_token`），見 §3 |
| **op_id** | CanonicalRequest 的 canonical JSON 的 sha256；一份操作計畫的身分 |
| **executor** | 目前持有全域操作鎖（flock）的那一個程序 |
| **executor context**（`Context`） | 持鎖程序中代表「我是 executor」的物件：`{token, fd, owner_pid, op_id}`，見 §4.4 |
| **操作計畫**（plan） | 取得鎖、通過准入後產生並原子保存的不可變檔案，見 §7 |
| **PlanStep**（步驟） | 計畫中的一個寫入動作：`{seq, step_id, path, kind, expected_before, expected_after, content_ref}`；同一計畫中每個 path 最多一步；每一步都滿足 `expected_before ≠ expected_after` |
| **`no_change[]`** | 計畫產生時 before 等於 after 的路徑清單；不成為步驟，見 §7.4 |
| **事件檔** | 一筆 audit 事件一個獨立檔案，以 link 建立、已存在就失敗，見 §10 |
| **登錄紀錄**（`index.d`） | 每份計畫一個不可變檔案，記錄 `plan_seq`，見 §7.5 |
| **狀態紀錄**（`status.d`） | 每個（op, 狀態）一個不可變檔案，見 §7.6 |
| **步驟完成紀錄**（`progress.d`） | 每一步輸出落盤並 fsync 之後以 link 建立的不可變檔案，見 §7.7 |
| **稽核物** | 事件檔、移轉清單、backup、登錄紀錄、狀態紀錄、完成紀錄、計畫檔 |
| **業務檔** | 稽核物以外、由計畫寫入的檔案（CLR、APR、run.yaml、revision、TC 版本、衍生輸出等） |
| **合法尾端** | 最後一個已執行的步驟「輸出已落盤、完成紀錄未落盤」的狀態，見 §8.3 |
| **未登錄計畫** | 計畫檔已存在、但沒有登錄紀錄的計畫，見 §6.2 |
| **`S_pre`／`S_maint`／`S_post`** | 系統狀態，見 §5.1 |
| **移轉標記** | `artifacts/requirements/_migration.yaml`，內容含 `migrate_op_id` 與每個 audit log 的 legacy 狀態；定義見移轉與回復章 |
| **R、X** | R 是 `migrate rollback` 的計畫，X 是它接管的 `migrate` 計畫；定義見移轉與回復章 |

---

### 3. 操作身分：CanonicalRequest 與 op_id

#### 3.1 CanonicalRequest

```text
{request_schema: 1,
 action,
 targets: {run_id?, task_id?, iteration?, approval_id?,
           clarification_ids[]（排序）, spec_pins[]（排序）},
 params: 該動作所有影響語意的參數
         （例如 document_pin、landed_in、resolution、decision、resolutions、per_item、
          impact_reviewed 的 sha256、reason 的 sha256 …）,
 inputs: {artifact_sha256s[]（排序）, dispatch_packet_sha256?},
 new_request_token?: 只有使用者明示 --new-request 時才存在（uuid）,
 request_key?: 呼叫端明示 --request-key 時才存在（ADR-011；和 new_request_token 互斥）}
```

- `op_id = sha256(canonical JSON)`。canonical JSON：鍵依字典序、不含空白、UTF-8（和 issue key 相同的規則）。
- op_id **只從請求本身計算**，不從操作進行中會改變的目前狀態計算；所以續做時重算出的 op_id 不變。

#### 3.2 重送、新請求與續做

| 情況 | 處理 |
|---|---|
| 同一請求重送，計畫存在且 `in_progress` | 同一 op_id → 進入續做驗證（§8.1） |
| 同一請求重送，計畫已 `completed` | 回報「已完成」，不做任何寫入（冪等） |
| 同一請求重送，計畫已是終態（`aborted_for_rollback`、`rolled_back`） | 拒絕；提示要重做必須以 `--new-request` 建立新 op |
| 刻意再發一次相同內容的請求 | 必須加 `--new-request`：產生新 token → 新 op_id；之後仍要通過該動作本身的狀態檢查 |
| `--new-request` 之後要續做 | 用 `operation resume <op_id>`（token 只在第一次發出時產生） |
| 呼叫端有穩定的請求身分（ADR-011） | 加 `--request-key <key>`：同 key 同內容 → 同一 op（已完成回報、未完成續做，不被第 3b 步擋下）；同 key 不同內容 → 拒絕（`key_conflict`）；不同 key 同內容 → 不同 op。key 索引在 `operations/_global/request_keys.d/` |

#### 3.3 CLI

- `bin/qaos operation list`：唯讀，不取鎖；直接讀 `index.d`、`status.d` 列出所有計畫與狀態（含未完成計畫），並回報終態不一致（§6.1）。
- `bin/qaos operation resume <op_id>`：寫入入口；取得鎖後依 §6 的判斷順序，只能進入第 2 步的續做驗證。
- 寫入指令的 `--json`（ADR-011）：stdout 只輸出一個 JSON 物件（成功：`outcome`、`op_id`、`ids`、`result`；失敗：`error_kind`、`incomplete_ops`），其他訊息改到 stderr。`completed` 回放的是當時存下的結果，不是實體目前的狀態。
- 各寫入指令的 `--new-request` 旗標。
- 沒有 `operation break-lock`：flock 沒有殘留鎖，不需要斷鎖（§4.2）。

---

### 4. 全域操作鎖：flock executor

#### 4.1 鎖檔與取得

1. **鎖檔**：`locks/qaos-operation.lock`。第一次使用時建立，之後**固定存在、永不刪除、不被替換**（inode 固定，避免開出第二把鎖）。
2. **取得**（每個寫入指令在 CLI 入口、**讀取任何狀態與產生計畫之前**執行一次）：
   1. `fd = os.open(鎖檔, O_RDWR | O_CREAT | O_CLOEXEC)`（實作要明確驗證此 fd 不可繼承）；
   2. `fcntl.flock(fd, LOCK_EX | LOCK_NB)`。
   - 成功 → 本程序成為唯一的 executor，直到關閉 fd 或程序結束。
   - 失敗（`EWOULDBLOCK`）→ 關閉 fd，**立即拒絕**，訊息附上診斷檔（§4.3）中的持有者資訊，並說明「鎖由其他 executor 持有」。**不等待**，所以巢狀呼叫或子程序不會形成死結。
3. 同一時間最多只有一個程序持有鎖 → **任何時刻最多只有一個 executor**，同一份計畫也不會被兩個程序同時續做。
4. op 身分只用來決定續做哪一份計畫，**不代表**持有鎖。ownership 由持有的開檔描述子決定，不靠 PID，所以 PID 重複使用不會造成誤判。

#### 4.2 自動釋放

- 程序正常結束、崩潰、被終止時，核心釋放 flock。
- 因此**沒有殘留鎖**：不需要代刪鎖、不需要斷鎖、不會刪掉新持有者的鎖。
- 釋放鎖不等於忽略未完成的計畫：下一個取得鎖的請求依 §6 處理（同 op 續做；其他 op 拒絕並提示 resume）。

#### 4.3 診斷檔

- `locks/qaos-operation.owner`：取得鎖之後，以原子替換寫入 `{op_id, pid, host, started_at}`。
- **只用來顯示訊息，不是權威**。可能是過期的（例如持有者已崩潰）；讀取者不得依據它做任何判斷。新的 executor 會覆寫它。

#### 4.4 executor context

- `Context{token(uuid4), fd, owner_pid, op_id}`；模組狀態 `_EXECUTOR = None | Context`。
- context **只存在於實際持有鎖的程序中**。任何寫入函式都必須傳入 ctx，並先呼叫 `require_context(ctx)`：
  - `_EXECUTOR` 不是 None、`ctx is _EXECUTOR`、`ctx.token == _EXECUTOR.token`、`ctx.owner_pid == os.getpid()`，全部成立才放行；否則拋出「context 已失效」錯誤，不做任何寫入。
- admin-ui（Session B）的後端如果在同一台主機上透過 `bin/qaos`，或以 Python 直接呼叫寫入函式，都必須經過同一個取得流程（另外開檔、flock，各自取得、彼此互斥），**不能自行建立 context**。

#### 4.5 巢狀呼叫

- 鎖在 CLI 入口取得一次；內部函式以 executor context 執行，**不再取鎖**。
- 父操作（例如 `answer` 內部重建 requirements md 與 approval render 的 `_resync_human_docs`）在同一個 context 中直接呼叫 export、render 函式，不另外取鎖，也不以子程序呼叫 CLI。
- 持有鎖時以子程序呼叫 `bin/qaos` 的寫入指令是禁止的；如果發生，子程序因 `LOCK_NB` 立即失敗並清楚報錯，父程序不會卡住。

#### 4.6 fd 不被子程序繼承

1. **exec 路徑**：鎖檔以 `O_CLOEXEC` 開啟。經 `subprocess`、`os.exec*`、`posix_spawn` 建立的子程序**不會**取得這個 fd。`O_CLOEXEC` 只處理 exec，不處理 fork。
2. **fork 路徑**（允許 fork）：
   - 取得鎖時，以 `os.register_at_fork(after_in_child=_drop_inherited_lock)` 註冊掛鉤；整個程序只註冊一次（模組層級旗標避免重複）。
   - 掛鉤在執行時讀取**目前**的 `_EXECUTOR`（不在註冊時捕捉 fd）。在子程序中：
     1. `_EXECUTOR` 是 None → 不做事；
     2. 否則把 `_EXECUTOR` 設為 None，對繼承到的 fd 執行 **`os.close(fd)`**（忽略 `OSError`）；
     3. **絕不**呼叫 `fcntl.flock(fd, LOCK_UN)`：子程序和父程序的 fd 指向同一個 open file description，在子程序中 `LOCK_UN` 會解除父程序的鎖。`os.close` 只關閉子程序那一份；只要父程序仍保有自己的 fd，鎖就仍然存在。
   - 子程序中任何使用舊 context 的地方，都因 `owner_pid` 不符而被 `require_context` 拒絕。
3. **子程序要寫入時**：必須自己重新走取得流程（開檔、`flock(LOCK_EX | LOCK_NB)`）。父程序仍持有鎖時立即失敗。
4. 父程序結束後，存活的 fork 子程序**不持有**鎖（它那一份 fd 已在 fork 時關閉）。

#### 4.7 參考實作（取得、釋放、掛鉤、context 檢查）

```text
模組狀態：_EXECUTOR = None | Context{token(uuid4), fd, owner_pid, op_id}
          _HOOK_REGISTERED = False

acquire(op_id) -> Context:
    fd = os.open(LOCK_PATH, O_RDWR | O_CREAT | O_CLOEXEC)
    try: fcntl.flock(fd, LOCK_EX | LOCK_NB)
    except BlockingIOError: os.close(fd); raise LockHeld
    ctx = Context(token=uuid4(), fd=fd, owner_pid=os.getpid(), op_id=op_id)
    _EXECUTOR = ctx
    if not _HOOK_REGISTERED: os.register_at_fork(after_in_child=_drop_inherited_lock); _HOOK_REGISTERED = True
    return ctx

release(ctx):
    require_context(ctx)
    _EXECUTOR = None                       # 先清除模組狀態
    os.close(ctx.fd)

_drop_inherited_lock():                    # 只在子程序執行
    ex = _EXECUTOR                         # 讀取「目前」的狀態
    if ex is None: return
    _EXECUTOR = None
    try: os.close(ex.fd)                   # 只關閉子程序那一份；不呼叫 flock(LOCK_UN)
    except OSError: pass

require_context(ctx):
    if _EXECUTOR is None or ctx is not _EXECUTOR or ctx.token != _EXECUTOR.token or ctx.owner_pid != os.getpid():
        raise ContextInvalid
```

- `owner_pid`、token 是第二道保險（例如掛鉤沒有執行的情況），**不能取代**關閉 fd。

#### 4.8 fork 使用的靜態檢查

- 以 `tools/validate_phase1.py` 或新增的靜態檢查，列出 QAOS 自身程式碼中所有 `os.fork`、`multiprocessing` 的使用（預期為零）；有新增時提示要有對應的測試（AC-07-77g）。
- 對 QAOS 原始碼搜尋為零，不能單獨證明第三方或原生依賴都不會 fork；實作審查時仍須核對所用的依賴。

---

### 5. 系統狀態與維護模式

#### 5.1 三種狀態

| 狀態 | 條件 |
|---|---|
| `S_pre` | 沒有移轉標記，也不在維護中 |
| `S_maint` | 在維護中（`locks/maintenance.yaml` 存在），不論是否已移轉 |
| `S_post` | 有移轉標記，而且不在維護中 |

#### 5.2 維護模式

- `bin/qaos maintenance start`：建立 `locks/maintenance.yaml`，內容含開始它的 `maintenance start` 的 op_id。
- `bin/qaos maintenance end`：刪除 `locks/maintenance.yaml`。
- 兩者都是寫入指令，以操作計畫執行（控制類操作）；計畫記錄 `admitted_state`、`to_state`、`resume_states`（§8.2）。
- 舊程式不認得維護檔；維護窗口的開始（新程式部署前）只能靠人工協調停止其他寫入。

#### 5.3 唯讀指令

- 包含：`list`、`show`、`trace`、`approvals`、`clarification list`、`clarification show`、`clarification stale-tcs`、`req-export --stdout`、`tc-export --stdout`、`operation list`、`migrate verify`。
- **不取鎖**，任何狀態（含 `S_maint`）都可以執行。
- **不保證**跨檔一致的快照（可能讀到另一個操作寫到一半的多檔狀態）；輸出開頭附這段說明。`migrate verify` 標明「讀取期間如果有寫入，結果可能不一致」；在維護窗口中其他寫入已停止，結果是一致的。

---

### 6. 寫入請求的判斷順序（取得 flock 之後）

所有寫入入口（新請求，含 `maintenance start|end`、`migrate`、`migrate rollback`、`run cancel`、其他業務寫入；同請求重送；`operation resume` 任何 op）在取得 flock 之後，依序執行：第 0 步 → 登錄補齊 → 第 1～3 步。

#### 6.1 第 0 步：全域終態一致性核對

- **時點**：取得 flock 之後、登錄補齊與任何計畫分派之前。這段期間不做任何持久寫入。
- **適用**：所有寫入入口，不論 action 或目標。
- **核對內容**：
  1. 從 `index.d` 找出所有 action 是 `migrate rollback` 的計畫 R；
  2. 依每份 R 不可變的計畫檔取得它的 `terminal` 群組（X 已完成時是 Rt1、Rt2；X 未完成時只有 Rt2；群組定義見移轉與回復章）；
  3. 確認符合**前綴規則**：已存在的終態紀錄，一定從群組的第一步開始連續存在；
  4. 某個終態紀錄存在、但計畫中排在它前面的終態步驟不存在（典型：`<R>-completed` 存在、`<X>-rolled_back` 不存在）→ **終態不一致**。
- **終態不一致時**：
  - **拒絕本次寫入請求**，回報不一致的 R、缺少的終態步驟、已存在的終態紀錄；
  - 不執行登錄補齊；不建立計畫檔；不新增 `index.d`、`status.d`、`progress.d`、`audit.d` 紀錄；維護檔與移轉標記不變；
  - 不刪除已存在的終態紀錄、不補寫缺少的終態步驟、不重新產生任何計畫；
  - 鎖檔、診斷檔屬於 executor 的控制面，照 §4 處理；
  - 由人處理，系統不提供自動出口。
- **不會誤擋**：部分移轉的 R（X 未完成，`terminal` 只有 Rt2）；終態階段中止（Rt1 已寫、Rt2 未寫，符合前綴）。
- 唯讀指令不受影響；`operation list`、`migrate verify` 回報終態不一致。

#### 6.2 登錄補齊

- **時點**：第 0 步之後、第 1 步之前；第 0 步拒絕時不執行。在任何狀態（`S_pre`、`S_maint`、`S_post`）都可以執行，因為它只完成一份已保存計畫的建立，不是新的業務寫入。
- 找出**未登錄計畫**（計畫檔存在、沒有登錄紀錄）。計畫在 flock 下建立、一次只有一份，所以正常情況下最多一份。實作上掃描計畫目錄（資料量變大時改用第二批的資料量索引）。
- 依序驗證：
  1. 計畫檔符合 schema；
  2. `op_id` 等於 `canonical_request`（含 `new_request_token`）的雜湊；
  3. 沒有其他登錄紀錄使用同一個 op_id。
- **通過** → 以 link 建立登錄紀錄（`plan_sha256` 等於計畫檔目前的 sha256），之後當成一般的 `in_progress` 計畫。沿用計畫中原有的 `clock`、`allocated_ids`（以及 rollback 計畫凍結的欄位），**不重新產生**；計畫檔一個位元組都不改。
- 登錄紀錄的 link 已存在且內容相符（補齊本身中止後重跑）→ 略過。
- **不通過** → 拒絕本次寫入請求（任何 action），回報這份計畫檔；不刪除、不覆寫、不登錄，由人處理（AC-07-99）。
- 計畫檔保存**之前**中止 → 沒有計畫；計數器的更新是計畫的一步，所以計數器不前進、沒有空號（§7.3）；寫入證據與內容檔的殘留由下一個寫入請求清除（附錄 A 4-18）。

#### 6.3 第 1 步：找出目標計畫

| 入口 | 目標計畫 |
|---|---|
| 一般寫入指令 | 由 CanonicalRequest 計算 op_id（帶 `--new-request` 時產生新 op；帶 `--request-key` 時 key 是請求的一部分，並先核對 key 索引：已綁定其他 op → 拒絕，ADR-011） |
| `operation resume <op>` | 指定的 op；這個 op 不存在 → 拒絕 |

#### 6.4 第 2 步：目標計畫已存在

| 目標計畫的狀態 | 處理 |
|---|---|
| `completed` | 回報已完成，不重做寫入。終態不一致的 R 不承認為已完成；這種情況已在第 0 步攔下 |
| `aborted_for_rollback`、`rolled_back` | **拒絕**；提示這個 op 已終結，要重做就以 `--new-request` 建立新 op |
| 被一份未完成的 rollback 計畫 R 指定為 `takeover_of`（不論 R 的第一步是否完成） | **拒絕**；提示續做 R（見移轉與回復章） |
| `in_progress` | 進行**續做驗證**（§8.1）。通過 → 執行剩下的步驟；不通過 → 拒絕，列出不符合的項目 |

#### 6.5 第 3 步：新請求（目標計畫不存在）

- **3a**：請求是 `migrate rollback --op X` → 走接管准入 T1～T7（見移轉與回復章）。
- **3b**：存在任何未完成的計畫 → **拒絕**，提示 `operation resume <op_id>`。
- **3c**：依下表的**初次請求白名單**決定。

| 寫入動作（只適用於初次請求） | `S_pre` | `S_maint` | `S_post` |
|---|---|---|---|
| `maintenance start` | 允許 | 拒絕（已在維護中） | 允許 |
| `maintenance end` | 拒絕（不在維護中） | 允許 | 拒絕 |
| `migrate`（含 `--acknowledge-idle`、`--cancel-run`） | 拒絕（必須先進入維護） | 允許（前提：標記不存在） | 拒絕（已移轉） |
| `migrate rollback --op X` | 拒絕 | 依 T1～T7 | 拒絕（必須先進入維護） |
| `run cancel` | 允許（移轉前白名單；使用新版規則） | 拒絕（維護中改用 `migrate --cancel-run`） | 允許（一般業務） |
| 其他所有業務寫入（含寫檔 export、`audit render`、`impact`、`answer`、`apply`…） | 拒絕（「尚未移轉」） | 拒絕（「維護中」） | 允許 |

- 「沒有未完成計畫」由 3b 統一檢查，只套用在初次請求；接管准入例外（見移轉與回復章）。
- `operation resume` 不是初次請求，不在表中；它只能進入第 2 步的續做驗證。
- 沒有任何旗標可以繞過白名單。

---

### 7. 操作計畫

#### 7.1 建立順序

1. 取得 flock，通過第 0 步、登錄補齊、第 1～3 步。
2. 在擷取中配發 ID（§7.3）；計數器的更新是計畫中的一步。
3. 在記憶體中產生完整計畫（含 `clock`、`allocated_ids`、所有步驟的 `expected_after`、`audit_events` 的完整 payload）。
4. **原子保存**計畫檔 `operations/<scope>/<op_id>.yaml`（沒有 run 的動作 scope 為 `_global`）。**保存完成，計畫就已建立。**
5. 以 link 建立登錄紀錄（§7.5）。
6. 依序執行步驟（§7.8）。
7. 最後一步建立 `status.d/<op_id>-completed.yaml`。

#### 7.2 計畫內容

| 欄位 | 內容 |
|---|---|
| `canonical_request`、`request_hash` | CanonicalRequest 與其雜湊（= op_id） |
| `action` | 計畫的操作類型；續做時一律以此為準，和使用哪個 CLI 入口無關 |
| `admitted_state` | 建立時的實際狀態（`S_pre`／`S_maint`／`S_post`） |
| `resume_states` | 續做時接受的狀態（§8.2） |
| `to_state`、狀態變更所屬步驟 | 只有控制類操作：預期的 `to_state`，以及它自己造成的狀態變更所屬的步驟 |
| `pre_state` | run 和 task 的狀態、相關檔案的 sha256 |
| `clock` | 固定的時間值；本操作所有寫入（含事件時間、登錄時間）都用它 |
| `allocated_ids` | 本操作會用到的 ID（CLR、APR、revision 編號等），在擷取中配發、由計畫固定 |
| `steps[]` | PlanStep 清單（§7.4）；每個 path 最多一步 |
| `no_change[]` | `{path, kind, content_sha256 \| absent}`（§7.4） |
| `audit_events` | 每個事件的**完整 payload**，時間一律取自 `clock`；所以每個事件步驟都有可預先算出的 `expected_after` |
| `post_state` | 計畫完成後應達到的狀態 |
| rollback 計畫的 `takeover_of`、`x_status_at_creation`、`x_progress`、`later_ops_snapshot`；R 步驟的 `group` | 見移轉與回復章 |

#### 7.3 ID 配發

- 在擷取中配發：讀取計數器、算出 ID，計數器的更新與使用 ID 的業務寫入一起成為計畫的步驟，ID 記入 `allocated_ids`。
- 計畫保存前中止 → 計數器沒有前進、沒有空號；重送時沒有計畫，重新配發，得到同一個號碼。中止前沒有任何以該 ID 發布的物件，所以這不是重複使用 ID。
- 計畫保存後，續做一律使用計畫中的 `allocated_ids`，不重新配發。
- 單一全域鎖與「未完成計畫阻擋新請求」保證同一時間只有一份計畫在配發，ID 不會重複。

#### 7.4 PlanStep 與 `no_change`

- PlanStep：`{seq, step_id, path, kind, expected_before, expected_after, content_ref}`。
  - `expected_before`：sha256；null（absent）代表這一步之前檔案不應存在。
  - `expected_after`：sha256；刪除步驟為「不存在」。
  - `content_ref`：從計畫內容重建最終檔案的方式。
  - `kind`：`business`（業務檔，含衍生輸出）、`event`、`control`、`index`、`status`。
- **每個 path 最多一步**：同一操作中對同一檔案的多次變更（例如 CLR 新建後又轉 INCORPORATED），在計畫產生時合併成一個最終內容。計畫產生時同一路徑出現兩次 → 計畫產生失敗（程式錯誤），沒有任何業務寫入。跨操作的多次變更屬於不同計畫，後一個計畫的 `expected_before` 就是前一個的 `expected_after`。
- **步驟必須有內容變更**：計畫產生時逐路徑比較 `expected_before`、`expected_after`（「不存在」也算一種內容）：
  - 不同 → 成為步驟；
  - 相同 → **不成為步驟**，列入 `no_change[]`：不寫入、沒有完成紀錄、沒有對應的事件步驟，不參與 L 的推導（§8.3）。
- 因此每個步驟都滿足 before ≠ after；「輸出等於 `expected_after`」代表這一步的寫入已經發生（外部寫入的例外見 §19）。
- 典型的 `no_change`：export 或 render 重新產生的內容和現有檔案相同；rollback 的 `remove` 目標原本就不存在、`restore` 目標已是 pre（見移轉與回復章）。
- 一份計畫可以完全沒有內容步驟；這時只有計畫檔、登錄紀錄、計畫要求的事件，以及 `completed` 狀態紀錄。
- `no_change[]` 隨計畫檔原子保存，續做時不重算。

#### 7.5 登錄紀錄 `index.d`

- 路徑：`operations/_global/index.d/<plan_seq>-<op_id>.yaml`，以 link 建立（已存在就失敗）。
- 內容：`{plan_seq, op_id, action, plan_sha256, registered_at: 計畫的 clock}`。
- `plan_seq` 等於目前最大值加一。
- 同一個 op 只能有一筆登錄紀錄。登錄前先檢查是否已有該 op 的紀錄：有就沿用，**不重新配號**。中止後重跑時，`plan_seq` 和登錄內容必須重算出相同的結果。
- 沒有共享索引檔。`operation list` 和後續操作的盤點直接讀 `index.d`、`status.d`；之後如果需要彙整檢視，只能當作可重建的衍生輸出，不能當成證據。

#### 7.6 狀態紀錄 `status.d`

- 路徑：`operations/_global/status.d/<op_id>-<status>.yaml`，以 link 建立，內容由寫入它的計畫固定。
- 判定：
  - 沒有任何狀態紀錄 → `in_progress`；
  - `<op>-completed` → `completed`；
  - `<op>-aborted_for_rollback`、`<op>-rolled_back` → 終態。終態優先於 `completed`（X 完成後被回復時兩者並存，以終態為準）。
- 每個狀態紀錄是獨立路徑、只由一個步驟寫一次，所以每一筆都能各自做三向判斷與 sha256 核對；合法的新增不會讓既有紀錄的 hash 失效。
- `completed` 是計畫的**最後一步**，沒有對應的完成紀錄，它本身就是完成的證據。

#### 7.7 步驟完成紀錄 `progress.d`

- 路徑：`operations/<scope>/<op_id>/progress.d/<seq>-<step>.yaml`。
- 內容：`{op_id, seq, step_id, path, after_sha256}`。
- 在該步驟的輸出落盤並 fsync **之後**以 link 建立。

#### 7.8 執行順序

- 除了 `completed` 狀態紀錄之外，每一步依序做三件事：(1) 寫輸出 → (2) fsync → (3) link 完成紀錄。三件事都完成，才進入下一步。
- 業務步驟全部完成後，才執行衍生輸出步驟（§12）；之後才寫 `completed`。

---

### 8. 續做

#### 8.1 同計畫續做驗證（同請求重送與 `operation resume` 共用）

| 檢查 | 內容 |
|---|---|
| **V1 身分** | 計畫檔的 sha256 等於它的登錄紀錄中的 `plan_sha256`（未登錄計畫先做登錄補齊）。同請求重送時：本次 CanonicalRequest 的雜湊等於計畫的 `request_hash`。action 一律取計畫記錄的 action |
| **V2 計畫狀態** | 必須是 `in_progress`，而且沒有被未完成的 R 接管（第 2 步已排除） |
| **V3 其他未完成計畫** | 未完成計畫的集合扣掉自己（僅限 R：再扣掉它的 `takeover_of` X），必須是空集合。正常流程中必然為空；不為空代表不合法狀態 → 拒絕並回報 |
| **V4 狀態** | 目前狀態加上身分核對，必須屬於計畫的 `resume_states`（§8.2）。**不重新套用**第 3c 步的初次請求前提 |
| **V5 步驟** | 先執行 `classify_steps`（§8.3）：<br>• 有任何**衝突** → **停止**，回報證據衝突，**不重寫**任何檔案<br>• 業務檔是 `external_change` → 停止<br>• `done`（proof：progress）→ 略過<br>• **合法尾端** → 補寫**這一步自己**的完成紀錄，然後略過<br>• `not_executed` → 依序執行：寫輸出 → fsync → link 完成紀錄<br>另外逐項核對 `no_change[]`（§8.3） |

#### 8.2 各 action 的 `resume_states`

建立計畫時寫入計畫檔；續做時只接受這些狀態。

| 計畫 action | `admitted_state` | `resume_states` | 身分核對 |
|---|---|---|---|
| `maintenance start` | `S_pre` 或 `S_post`（記錄實際值） | ① `admitted_state`（維護檔不存在）<br>② `S_maint`，而且維護檔內容的 op_id 等於本計畫 | 維護檔的 op_id 不同 → 拒絕 |
| `maintenance end` | `S_maint`（記錄維護檔的 sha256，以及標記是否存在） | ① `S_maint`，而且維護檔的 sha256 等於記錄值<br>② 維護檔不存在，而且標記是否存在和記錄相同（即 `to_state`：`S_pre` 或 `S_post`） | 維護檔的 sha256 |
| `migrate` X | `S_maint`、標記不存在 | ① `S_maint`、標記不存在<br>② `S_maint`，而且標記的 `migrate_op_id` 等於 X | 標記屬於其他 op → 拒絕 |
| `migrate rollback` R | `S_maint` | `S_maint`，而且標記的 `migrate_op_id` 等於 X，或標記不存在（已被 R 移除） | `takeover_of` 等於 X |
| `run cancel` | `S_pre` 或 `S_post` | `admitted_state` | — |
| 其他業務寫入 | `S_post` | `S_post` | — |

- 這張表只放行「計畫自己預先記錄的合法狀態變更」，不對任意同 op 的請求無條件放行。
- 例：業務計畫在 `S_maint` 中續做 → V4 不符 → 拒絕；`maintenance end` 以 `operation resume` 在 `S_post` 中續做 → 符合 ② → 允許。

#### 8.3 `classify_steps(plan)` 與合法尾端

T5（rollback 接管准入，見移轉與回復章）和 V5 共用這一個判定函式。依序檢查計畫的每一步：

- **輸出**：目前內容等於 `expected_after` → `after`；等於 `expected_before`，或屬於 absent-create 且檔案不存在 → `before`；其他 → `other`。（每步 before ≠ after，所以三者互斥。）
- **紀錄**：完成紀錄存在且內容等於計畫值 → `present`；不存在 → `absent`；存在但內容不符 → `bad`。

令 **L** 為「輸出是 `after`，或紀錄是 `present`」的步驟中順序最後的一個。

| 位置 | 輸出 | 紀錄 | 判定 |
|---|---|---|---|
| L 之前 | `after` | `present` | `done`（proof：progress） |
| L 之前 | `after` | `absent` | **衝突**：尾端之前缺完成紀錄 |
| L 之前 | `before` | 任意 | **衝突**：已證實執行過的步驟，輸出卻不存在或被還原 |
| L | `after` | `present` | `done`（proof：progress） |
| L | `after` | `absent` | `done`（proof：**合法尾端**） |
| L | `before` | `present` | **衝突**：有完成紀錄，輸出卻不存在或被還原 |
| L 之後 | `before` | `absent` | `not_executed` |
| L 之後 | `after` | 任意 | 不會發生（L 的定義已排除） |
| 任意 | `other` | 任意 | 稽核物 → **衝突**；業務檔 → `external_change` |
| 任意 | 任意 | `bad` | **衝突**（完成紀錄被竄改） |

- 「衝突」只適用於**稽核物**。業務檔在相同情況（L 之前是 `before`、L 是 `before` 而紀錄 `present`、或 `other`）記為 `external_change` 並列入報告。V5 遇到 `external_change` 一律停止，不重寫；T5 的處理見移轉與回復章。
- **`no_change[]` 的核對**（和 L 的推導分開、逐項進行）：內容等於記錄值 → 符合；不符：稽核物 → 衝突，業務檔 → `external_change`。這些路徑在計畫執行期間不應改變。
- 業務步驟寫完、它對應的事件步驟還沒執行就中止：業務步驟是 L（合法尾端或 `done`），事件步驟是 `not_executed`，**不算竄改**。
- 事件檔一律以完整 sha256 核對，不只核對 `op_id`、`step_id`。
- `x_status_at_creation` 為 `completed` 時的判定方式（rollback 接管用）見移轉與回復章。

**合法尾端最多一個（不變式）**：

- 前提：每個步驟 before ≠ after；executor 依序對步驟 1…n 執行「寫輸出 → fsync → link 完成紀錄」，前一步三件事都完成才開始下一步；沒有外部寫入。
- 在任何時間點中止，都存在某個 k，使得：步驟 1…k−1 是（`after`, `present`）；步驟 k 是（`before`, `absent`）、（`after`, `absent`）或（`after`, `present`）之一；步驟 k+1…n 是（`before`, `absent`）。
- 所以 L = k 或 L = k−1；整份計畫中只有 L 可能是（`after`, `absent`）。偏離此不變式的組合只能來自外部刪改，依上表判為衝突或 `external_change`。
- 此推導**依賴每步 before ≠ after**；before = after 的路徑如果仍是步驟，未執行時也是 `after`，會把 L 往後推。所以 `no_change` 剔除是不變式的前提。

**兩個入口對合法尾端的處理不同**：

| 入口 | 處理 |
|---|---|
| V5（計畫自己續做） | 補寫**它自己**這一步的完成紀錄，然後從下一步繼續。這一步確實已成功（輸出等於計畫值），補寫完成紀錄不算補寫未執行的事件 |
| T5（R 接管） | R 只凍結這一步的實際存在與 sha256（proof：`content_tail`），**不替 X 補寫完成紀錄**（見移轉與回復章） |

#### 8.4 和三向規則的關係

- **三向規則**：目前內容等於 after → 略過；等於 before，或建立步驟且檔案不存在 → 寫入；其他 → **停止**，報告「外部修改」，不覆寫。
- 沒有完成紀錄的步驟仍沿用三向規則；有完成紀錄的步驟更嚴格：**只能略過**，內容不符就停止（衝突）。

#### 8.5 未登錄計畫與續做

- 計畫檔已保存、登錄紀錄未寫 → 下一個寫入請求先做登錄補齊（§6.2）；之後依第 1～3 步：同一 op → 續做；其他 op → 3b 拒絕並提示 resume。

---

### 9. 寫入方式

| 對象 | 方式 |
|---|---|
| 業務檔、計畫檔、診斷檔、衍生輸出（單檔原子寫入） | 同目錄暫存檔 → fsync → `os.replace`。正式路徑不會出現半寫內容 |
| 事件檔、登錄紀錄、狀態紀錄、完成紀錄 | 同目錄暫存檔 → fsync → `os.link(暫存檔, 目標)`（目標已存在就失敗）→ 刪除暫存檔 |
| 刪除步驟 | 刪除目標路徑（例如 `maintenance end` 刪維護檔） |

- 續做前清除**本 op_id** 的殘留暫存檔；檔名不屬於本 op_id 的暫存檔**一律不動**。
- 不多檔原子；承諾見 §14。

---

### 10. audit 事件檔與 `audit render`

#### 10.1 事件檔（權威紀錄）

- 路徑：run 內 `runs/<run_id>/audit.d/<op_id>-<step>.yaml`；全域 `runs/_audit.d/<op_id>-<step>.yaml`。
- 內容：`{at（計畫的 clock）, actor, action, detail, op_id, step, run_id}`；完整 payload 由計畫的 `audit_events` 固定。
- 以 link 建立：檔名 `op_id-step` 只屬於這個操作；不會有半寫的目標檔；不接觸任何其他檔案。
- 續做：

  | 目標檔狀態 | 處理 |
  |---|---|
  | 不存在 | 建立 |
  | 存在、sha256 等於計畫的預期內容 | 略過 |
  | 存在、內容不同 | 停止（衝突） |

- **沒有計畫的 audit**（原本 `store.audit` 的其他呼叫）一律改寫成事件檔，op_id 用 `adhoc-<uuid>`，step 為 0。不再有任何程式碼對 `audit.log` 追加。

#### 10.2 `audit.log` 是可重建的檢視

- `bin/qaos audit render [<run_id>|--global]`：寫入指令，要取鎖；只有在 `S_post` 允許作為初次請求。
- 產生方式：讀取 `audit.legacy.log`（移轉時凍結的舊內容）加上全部事件檔，依 `(at, op_id, step)` 排序事件，產生完整內容，以原子替換寫入 `audit.log`。
- 標記寫入之後，每個操作完成前會重建它影響的 `audit.log`（作為衍生輸出步驟，§12）。
- 行格式維持現行的 tab 分隔，讓現有讀取者照常讀取；檔案改成整份替換、不再追加（需和 Session B 協調）。

#### 10.3 移轉標記寫入之前不 render

- 標記寫入之前，所有操作（含白名單中的 `run cancel`）**只寫事件檔、不 render**，也不寫入、不改動任何既有的 `audit.log`。
- 移轉前手動執行 `audit render` → 拒絕（第 3c 步「尚未移轉」；也沒有標記）。

#### 10.4 render 依 legacy 狀態處理

- render 必須已有移轉標記。
- 標記中每個 log 的 legacy 狀態是 `frozen: <sha256>` 或 `absent`（凍結步驟屬移轉章）。
- `frozen` → 讀取 `audit.legacy.log`、驗證 sha256 → **原位元組照抄**作為開頭（不重新排序、不解析）→ 接上依 `(at, op_id, step)` 排序的事件 → 原子替換。legacy 最後一行的時間戳晚於之後的事件時，仍是 legacy 在前、事件在後，不交錯。
- `absent`，或**移轉後才建立的 run**（標記中沒有它，且 run 的 `created_at` 晚於標記時間）→ 只用事件檔。
- 其他情況（標記中應有它卻缺 legacy 檔、hash 不符）→ **拒絕**，不以空檔代替。

---

### 11. 寫入指令與唯讀指令

- **要取鎖的寫入指令**：所有會寫入 repo 的指令，含 `req-export`、`tc-export`、`tc-final`、`approval`（render md／html）、`audit render`、`clarification impact`（保存掃描紀錄）、`maintenance start|end`、`migrate`、`migrate rollback`、`run cancel`，以及原本的業務操作。
- **不取鎖的唯讀指令**：§5.3 的清單，含新增的 `--stdout` 版 export（`req-export --stdout`、`tc-export --stdout`）。
- 鎖被持有時執行寫檔的 export → 立即失敗（拒絕）。
- 父操作內部呼叫 export、render 函式時共用父操作的 executor context，不另外取鎖（§4.5）。

---

### 12. 衍生輸出

- 衍生輸出：requirements／testcases 的 md、final html／json、approval md／html、CLR 的 md、`audit.log`。
- 業務步驟**全部完成後**才重建衍生輸出。
- **每個檔案一個步驟**，各自有 `expected_after` 和完成紀錄；不把部分成功的多檔輸出包成一個步驟。
- 以原子替換寫入。render 失敗時該檔仍是 `before`（原子替換沒有發生）。
- 重建以計畫固定的 `clock` 和輸入快照達到決定性，不使用重試當下的時間。
- 計畫產生時，重新產生的內容和現有檔案相同 → 列入 `no_change`，不成為步驟；所有檔都相同 → 這次 render 或 export 沒有內容步驟。
- **重建失敗或中止**：計畫**不標記完成**（不寫 `completed`），保持 `in_progress`；之後 `resume`（或同請求重送）重試重建。業務檔不受影響。
- 續做時重新產生的內容和 `expected_after` 不同 → 停止，不寫入。
- 多檔 render 中止在第 k 個檔之後：前 k 個略過，其餘依序寫入。

---

### 13. 驗證失敗

- 預檢（驗證）失敗時，**業務檔不寫入**（RM、revision、CLR、APR、spec.yaml、TC 版本等），也不建立計畫。
- 只允許兩種診斷寫入：
  1. run.yaml 中該 task 的 `gate_results` 追加，以及 task 狀態回 READY；
  2. 一個 audit 事件檔。
- 修正輸入後重送，是新的 op_id。
- 診斷寫入**不建立操作計畫**：在持有鎖的 executor context 中直接寫入上述兩項；事件檔的身分是 `adhoc-<uuid>`（檔名 `adhoc-<uuid>-0`）。不產生登錄、狀態或完成紀錄，也不會成為未完成計畫，所以不會阻擋之後的請求。
- 診斷寫入不在續做的保證範圍內：兩項寫入之間中止時，可能只留下其中一項；這只影響診斷資訊，不影響業務檔。

---

### 14. 承諾清單

1. 驗證失敗不寫業務檔（只允許 §13 的兩種診斷寫入）。
2. 寫入中止後，可續做到計畫的 `post_state`。
3. 不產生重複的業務物件（ID 由計畫固定；每個 path 最多一步）。
4. 任何時刻最多只有一個 executor；同一時間只有一份計畫在讀寫。
5. 不寫入、不截斷、不刪除其他操作的檔案（含其他 op 的暫存檔、事件檔）。
6. 移轉標記寫入之前，不改動任何既有的 `audit.log`。
7. 固定的 flock 鎖檔永不刪除。
8. 不補寫任何未執行成功的事件；續做時只補寫「已確實執行成功的合法尾端」自己的完成紀錄。
9. 已證實的稽核證據缺失或竄改會被發現並停止，不重寫、不偽造。
10. **不承諾多檔原子性。**

---

### 15. 故障恢復表（預期結果）

**通則**：

- 每一步依 §8.3、§8.4 處理；每個 path 在一個計畫中最多一步。
- 比較方式：固定 clock 和 ID 後比較語意欄位（物件數量、ID、狀態、指向關係）。不要求和另一次獨立成功的執行逐位元相同；但同一次計畫的續做，所有輸出必須等於計畫的 `expected_after`。
- 每個續做都以兩種入口驗收：同請求重送、`operation resume`。

以「G-SPEC 提交」為主例，其他操作同樣處理：

| AC | 故障點 | 當下狀態 | 恢復 | 恢復後必須成立 |
|---|---|---|---|---|
| 9a | 預檢失敗 | 沒有計畫 | 不需要；修正輸入後重送（新 op_id） | 業務檔不變；只有 §13 的診斷寫入 |
| 9b | ID 配發後、計畫保存前 | 計數器沒有前進，沒有計畫（只有寫入證據與內容檔的殘留） | 重送 → 清除殘留 → 沒有計畫 → 重新配發（同一個號碼） → 正常執行 | 只有一組業務物件；計數器沒有空號 |
| 9c | 計畫的暫存檔寫到一半 | 暫存殘留，正式計畫不存在 | 清除本 op 暫存 → 同 9b | 同 9b |
| 9d | 計畫保存後、第一步前 | 計畫存在 | 先登錄補齊（若未登錄，FP-P1）→ 從第一步執行 | 所有 ID 等於計畫中的 ID |
| 9e | 部分 CLR（含 `topic: other`）已寫 | 各 CLR 等於 after 或不存在 | 略過或建立 | `other` 的 CLR 只有一張 |
| 9f | CLR 的 `.md` 等於 before 或不存在 | — | 寫入（衍生輸出步驟） | `.md` 和 yaml 一致 |
| 9g | APR 已寫，run.yaml 等於 before | — | APR 略過、run.yaml 寫入 | 只有一張 APR；`waiting_on_approval_id` 指向它 |
| 9h | 部分 TC 版本檔等於 before | — | 只寫那些 | 所有列入的 TC 都是 PENDING_APPROVAL |
| 9i | revision 等於 after，檢視等於 before | — | 寫入檢視 | 檢視等於 revision |
| 9j | spec.yaml、CLR 狀態、run.yaml 中有等於 before 的 | — | 逐一寫入 | 達到 `post_state`；landings 各只有一筆 |
| 9k | 全部步驟等於 after，`completed` 未寫 | — | 只建立 `status.d/<op>-completed` | 沒有任何業務寫入 |
| 9l | 正式檔等於 before，同目錄殘留本 op 暫存檔 | — | 清除後寫入 | 正式檔不出現半寫內容 |
| 9m | 有業務檔既不等於 before 也不等於 after | — | **停止**，不覆寫 | 計畫維持未完成，報告路徑；人工處理後才能繼續 |
| 9n | audit 事件檔 | — | 不存在就建立；存在且 sha 相符就略過；存在但內容不同就停止；只刪除本 op_id 的暫存檔 | 每個 `op_id-step` 只有一個事件檔；`audit.log` 由 render 重建 |
| 9q | migrate 在凍結 legacy audit 之後、標記之前中止 | — | 續做；凍結步驟略過 | legacy 沒有被覆寫 |
| 9r | 第一次 render 在原子替換之前中止 | — | 續做 | `audit.log` 仍是移轉前的原內容（標記之前從未被改動）或上一份完整檢視 |
| 9t'' | executor 在任何時點崩潰或被終止 | — | 核心釋放 flock；下一個請求取得鎖：有同 op 的未完成計畫 → 續做；有其他 op 的未完成計畫 → 拒絕並提示 resume；沒有計畫 → 照常執行 | 沒有殘留鎖需要處理 |
| 9x | `apply` 在 CLR 狀態寫入之後、landing 之前中止 | — | 依計畫續做 | landing 只有一筆 |
| 9y | `impact` 在掃描紀錄寫入之前中止 | — | 續做 | 掃描紀錄只有一份 |
| 9z' | 業務步驟完成後，重建衍生輸出失敗或中止 | — | 計畫不標記完成；`resume` 重試重建 | 業務檔不變 |
| 9aa | `apply --path a7` 在全部歷史掃描之後、寫入之前中止 | 計畫已記錄 `reference_scan_sha256` | 續做依計畫；如果重新取得鎖之後歷史有了新的引用，計畫的 `pre_state` 和目前狀態不符 → 依 before／after 規則停止，提示重新發出請求 | — |
| 9ab | executor 在 fork 之後、子程序仍存活時崩潰或結束 | 子程序已在 fork 時關閉它那一份鎖 fd | 下一個請求依 9t'' 處理（同 op 續做，或其他 op 被拒絕並提示 resume） | 鎖隨父程序結束而釋放 |

**本章的故障點**（每個都以同請求重送、`operation resume` 兩種入口驗收）：

| 故障點 | 中止時的狀態 | 續做結果 | 續做期間其他請求 | AC |
|---|---|---|---|---|
| **FP-P1**（所有操作）計畫檔已保存，登錄紀錄還沒寫 | 不變 | 下一個寫入請求做登錄補齊 → 同 op 續做；計畫檔、`clock`、`allocated_ids` 不變 | 補齊之後依 3b 拒絕 | AC-07-98（rollback 計畫另見 AC-09-80） |
| **FP-P2**（所有操作）登錄紀錄已寫，第一步還沒執行 | 不變 | 從第一步開始；登錄紀錄只有一筆 | 拒絕（3b） | AC-07-97 |
| **FP-W**（所有操作、所有步驟）步驟輸出已落盤，完成紀錄未落盤 | 依步驟而定 | 合法尾端：補寫該步的完成紀錄，不重寫輸出 → 繼續（migrate 的這種中止被 R 接管時見移轉與回復章） | 依各操作 | AC-07-95 |
| **FP-S1** `maintenance start`：計畫已建立，維護檔還沒建立 | `admitted_state` | 建立維護檔 → 完成 | 拒絕（3b） | AC-07-88 |
| **FP-S2** `maintenance start`：維護檔已建立，計畫未完成 | `S_maint`（自己的維護檔） | 維護檔略過（不重寫，sha256 不變）→ 完成 | 拒絕（3b），含 `maintenance end`、`migrate` | AC-07-88 |
| **FP-E1** `maintenance end`：計畫已建立，維護檔還在 | `S_maint` | 刪除 → 完成 | 拒絕 | AC-07-89 |
| **FP-E2** `maintenance end`：維護檔已刪除，計畫未完成 | `S_pre` 或 `S_post` | 刪除步驟略過 → 完成 | 拒絕，含 `maintenance start` 和業務寫入 | AC-07-89 |

FP-M0～M6（migrate）、FP-R0～R5（rollback）見移轉與回復章；對應的 AC-07-90～93 列在本章 §18.12。

---

### 16. 每種操作類型的中止加續做（完整清單）

每一種操作類型都至少驗收一個「中途中止 → 續做 → 完成」案例，以兩種入口各做一次：

| 操作類型 | 最早可部分驗收 | 完整驗收 |
|---|---|---|
| submit_gate（不含 A4） | P1 | — |
| submit_gate（含 A4） | — | P5 |
| approve（不 apply，含 A9） | — | P5 |
| complete_run（需求 A 只持久化 COMPLETED 並重建衍生輸出，不碰 CLR） | P1 | — |
| cancel_run（`run cancel`） | P1 | — |
| 寫檔 export | P1 | — |
| `audit render` | P1 | — |
| `maintenance start`、`maintenance end` | P1 | — |
| `impact` | — | P5 |
| `apply`（a6、a6b、a7） | — | P5 |
| `fulfill` | — | P5 |
| `waive-item` | — | P5 |
| `migrate` | — | P3 |
| `migrate rollback` | — | P3 |
| metadata upgrade（spec、clarification） | — | P3 |
| `applicability_add` | P2 實作 | P6 收尾 |

另外：§15 的 9a～9n、9q、9r、9t''、9x、9y、9z'、9aa、9ab，以及 FP-P1、FP-P2、FP-W、FP-S1～S2、FP-E1～E2（加上移轉與回復章的 FP-M0～M6、FP-R0～R5）的**每一個故障點**都要驗收。所有標「待 Pn」的項目在 P6 結清。

---

### 17. 涉及的 schema、模組、CLI

| 類別 | 項目 |
|---|---|
| 新增模組 | `tools/qaos/operation.py`（計畫、續做、flock executor、fork 掛鉤、context 的 `owner_pid` 檢查、`classify_steps`、登錄補齊、第 0 步、維護模式的准入） |
| 修改模組 | `store.py`（原子 save、audit 事件、render）、`engine.py`（各動作改為「計畫 → 步驟」）、`clarification.py`（`_resync_human_docs` 改走 context）、`cli.py`、`req_export.py`、`tc_export.py`、`final_export.py`、`approval_render.py`（改用 executor context 和原子寫入）、`tools/validate_phase1.py` 或新增的靜態檢查（fork 使用清單） |
| 新增 schema | `schemas/workflow/operation-plan.schema.json`（含 `audit_events` 完整 payload、`no_change`、`admitted_state`、`resume_states`）、`schemas/workflow/audit-event.schema.json` |
| CLI | `operation list`、`operation resume <op_id>`、`audit render [<run_id>\|--global]`、`maintenance start`、`maintenance end`、`--new-request`、`req-export --stdout`、`tc-export --stdout` |
| 檔案配置 | `locks/qaos-operation.lock`、`locks/qaos-operation.owner`、`locks/maintenance.yaml`、`operations/<scope>/<op_id>.yaml`、`operations/<scope>/<op_id>/progress.d/`、`operations/_global/index.d/`、`operations/_global/status.d/`、`runs/<run_id>/audit.d/`、`runs/_audit.d/` |
| 測試 | `tests/`（全部以獨立的測試 root，`QAOS_ROOT` 指向暫存目錄；fixture 經正式指令建立，不使用 repo 業務資料） |

---

### 18. 驗收 AC（全部是預期結果）

**通用驗收方式**：

- 測試在獨立的測試 root 執行；初始資料一律經正式流程建立，只有標明「竄改反例」或「故障注入」的才在流程後修改檔案。
- 故障點以測試專用的中止點注入（例如在指定步驟之後讓程序結束）。
- 每個續做案例都分成 (a) 同請求重送、(b) `operation resume <op>` 兩例。
- 每例斷言：
  1. **沒有重複的寫入**：控制檔、標記的 sha256 不變；`audit.d`、`progress.d` 沒有多出檔案；每個 op 只有一筆登錄紀錄，每個 (op, status) 只有一筆狀態紀錄；計畫檔的 sha256 不變；
  2. 計畫可以完成；
  3. 續做完成之前，其他 op 被拒絕（接管 rollback 的例外依表列）；
  4. 完成之後的狀態等於計畫記錄的 `to_state`。
- 停止案例先斷言步驟分類和完成紀錄，再斷言**實際停止的位置**，不能只看最後傳回失敗。
- 防禦性 AC 的故障注入程式只存在於測試中，不作為正式流程可達性的證據。

**分工**：AC-07-1～7、AC-07-11（issue key 去重）在「去重與開單關卡」章。

#### 18.1 驗證失敗與基本續做

| AC | 前置條件／情境 | 預期結果 |
|---|---|---|
| AC-07-8 | 任一驗證（預檢）失敗（P1 以 submit_gate 驗證） | RM、revision、spec.yaml、clarifications、approvals、TC 版本等業務檔的 hash 和失敗前完全相同；run.yaml 除了允許的診斷欄位（該 task 的 `gate_results` 追加、狀態回 READY），其他不變；最多一個診斷 audit 事件檔；沒有計畫檔 |
| AC-07-9a～9n | §15 故障恢復表 9a～9n 每一列（含寫入中斷：暫存檔寫到一半） | 各列「恢復後必須成立」欄 |
| AC-07-9q、9r、9t''、9x、9y、9z'、9aa、9ab | §15 對應列 | 各列「恢復」與「必須成立」欄 |
| AC-07-10 | 見第 3 章 §15.2（同一條；以第 3 章為準，完整驗收在 P5） | — |
| AC-07-12 | 續做時發現某個目標業務檔已被別人修改（既不是 before 也不是 after） | 停止並報告，不覆寫；計畫維持未完成 |

#### 18.2 操作身分（AC-07-13～18）

以下 fixture 驗收 AC-07-13～18，涵蓋 submit_gate、approve、complete_run、cancel_run、apply、fulfill、migrate 的 op_id 計算。對應：AC-07-13 = op-P1、op-P2；14 = op-N1、op-N2；15 = op-N3；16 = op-N4；17 = op-N5；18 = op-N6（附錄 A 4-1）：

| fixture | 情境 | 預期結果 |
|---|---|---|
| op-P1 | `fulfill CLR-A` 以文件 P1 執行到一半中止，再以同參數執行 | 同一個 op_id，續做 |
| op-P2 | 同上，已完成後再以同參數執行 | 同一個 op_id，回報「已完成」，沒有任何寫入 |
| op-N1 | `fulfill CLR-A`（文件 P1），然後 `fulfill CLR-B`（文件 P1） | op_id 不同，兩張各自處理 |
| op-N2 | `fulfill CLR-A`（文件 P1），然後 `fulfill CLR-A`（文件 P2） | op_id 不同 |
| op-N3 | `apply CLR-A --landed-in RUN-1`，和 `--landed-in RUN-2` | op_id 不同 |
| op-N4 | `apply CLR-A` 已完成，再以同參數加 `--new-request` | op_id 不同；狀態檢查拒絕（已 APPLIED），沒有任何寫入 |
| op-N5 | 有一份以 CLR-A 為 target 的未完成計畫，此時執行 `answer CLR-A` | 拒絕，提示 `operation resume <op_id>` |
| op-N6 | 在 `S_maint` 中兩次 `migrate`，第一次中止 | 第二次同 op_id 續做；已有標記時，`--new-request` 的 migrate 被拒絕 |

#### 18.3 計畫結構與 audit 殘段

| AC | 前置條件／情境 | 預期結果 |
|---|---|---|
| AC-07-19 | 計畫產生時同一路徑出現兩次 | 計畫產生失敗，沒有任何業務寫入 |
| AC-07-20、AC-07-21 | **撤銷**（附錄 A 4-2）：原驗收對象（`audit.log` 追加時的檔尾殘段）在本規格中不存在；audit 一律寫事件檔，`audit.log` 只由 render 整份替換。「不碰其他操作的檔案」由 AC-07-38、39 驗收 | — |

#### 18.4 每種操作類型的中止加續做（AC-07-22～29）

| AC | 前置條件／情境 | 預期結果 |
|---|---|---|
| AC-07-22～29 | §16 清單中的每一種操作類型，各以故障注入在中途中止，兩種入口各續做一次 | 續做完成；沒有重複的業務物件、事件、登錄或狀態紀錄；中止期間其他 op 被拒絕；依 §16 的階段完成驗收。對應：22 = submit_gate；23 = approve；24 = complete_run、cancel_run；25 = 寫檔 export、`audit render`；26 = `maintenance start|end`；27 = `impact`、`apply`、`fulfill`、`waive-item`；28 = `migrate`、`migrate rollback`、metadata upgrade；29 = `applicability_add`（附錄 A 4-3） |

#### 18.5 audit 事件檔（AC-07-36～41）

| AC | 前置條件／情境 | 預期結果 |
|---|---|---|
| AC-07-36（防禦性） | 操作 A 寫入事件檔之前中止；以故障注入放入另一個 op B 的事件檔；A 續做 | A 建立自己的事件檔；B 的事件檔不受影響 |
| AC-07-37（防禦性） | A 的事件檔已完整建立後中止；以故障注入放入 B 的事件檔；A 續做 | A 的目標存在且 sha 相符 → 略過，可以達到 post_state；B 的事件檔不受影響 |
| AC-07-38（防禦性） | A 中止後，以故障注入放入 B 的暫存檔（模擬 B 寫到一半）；A 續做 | A 只刪除自己 op_id 的暫存檔；B 的暫存檔不動 |
| AC-07-39 | A 的事件目標檔存在但內容不同 | A 停止並報告 |
| AC-07-40 | 正式序列：render 計畫 A 在原子替換之前中止 → 此時業務操作 B 依 3b 被拒絕 → 以 (a) 同請求重送、(b) `operation resume` 各續做 A 一次 → A 完成 → B 以正式流程寫入新事件 → 以新請求執行 render C | A 續做時使用計畫固定的輸入與 `expected_after`，不納入 B 的事件；A 完成後 B 才能執行；C 的結果是包含全部事件（含 B）的完整檢視；事件檔沒有遺失 |
| AC-07-41 | 移轉後，原有 audit 內容在 `audit.legacy.log` 中逐位元相同 | render 的結果以它為開頭 |
| AC-07-42 | `audit render` 中止（原子替換之前） | `audit.log` 仍是上一份完整檢視 |

#### 18.6 移轉前不 render、legacy 狀態（AC-07-43～49）

全部以含真實舊位元組的唯讀複本執行。

| AC | 前置條件／情境 | 預期結果 |
|---|---|---|
| AC-07-43 | 有舊的 run log 和全域 log → 移轉前 `run cancel X`（`S_pre`；寫事件、不 render）→ `maintenance start` → `migrate` | 兩個 `audit.legacy.log` 都逐位元等於 cancel 之前的 `audit.log`；第一次 render 的結果 = legacy 原位元組 + cancel 事件 + 移轉事件 |
| AC-07-44 | `migrate --cancel-run X` | 同 AC-07-43 |
| AC-07-45 | migrate 在凍結之後、標記之前中止 → 重送 | 凍結略過（hash 相符）；繼續寫標記和 render；legacy 沒有被覆寫 |
| AC-07-46 | 移轉前手動執行 `audit render` | 拒絕（沒有標記） |
| AC-07-47 | 標記之後，某個 frozen 的 log 的 legacy 檔被刪除 | render 拒絕 |
| AC-07-48 | 移轉後新建的 run | render 只用事件檔 |
| AC-07-49 | 某個 legacy 的最後一行時間戳晚於之後的事件 | legacy 位元組照抄在前，事件接在後面，不交錯排序 |

#### 18.7 flock executor（AC-07-64～72）

以兩個（或多個）子程序加同步點驗收。

| AC | 前置條件／情境 | 預期結果 |
|---|---|---|
| AC-07-64 | A 以 op X 持鎖、仍在執行；B 送出相同請求（op 也是 X） | B 的 flock 失敗 → 拒絕；A 不受影響 |
| AC-07-65 | 兩個 `operation resume X` 同時放行（原 executor 已死） | 只有一個取得鎖並續做；另一個被拒絕 |
| AC-07-66 | 不同 op 的 A、B 同時放行 | 只有一個取得 |
| AC-07-67 | A 保存計畫後被 `kill -9` → B 送出相同請求 | 核心已釋放鎖 → B 取得 → 發現 op X 的未完成計畫 → 續做 |
| AC-07-68 | A 取得鎖、在保存計畫**之前**被終止 → B（不同 op）送出 | B 取得；沒有未完成計畫 → 照常執行；沒有任何殘留需要處理 |
| AC-07-69 | A 保存計畫後被終止 → C（不同 op）送出 | C 取得鎖後發現 op X 未完成 → 拒絕，提示 resume |
| AC-07-70 | 持有鎖的操作以子程序呼叫寫入指令 | 子程序立即失敗並清楚報錯，父程序不會卡住 |
| AC-07-71 | 診斷檔寫的是已死的程序，鎖實際上是空的 | 新請求取得成功；診斷檔被覆寫 |
| AC-07-72 | 鎖被持有時執行 `list`、`show`、`trace`、stdout 版 export | 不取鎖，照常執行 |

（各 fixture 和編號依情境順序對應，附錄 A 4-4。）

#### 18.8 寫檔 export 與巢狀 executor（AC-07-73～76）

| AC | 前置條件／情境 | 預期結果 |
|---|---|---|
| AC-07-73 | 鎖被持有時，執行 `list`、`show`、`req-export --stdout` | 照常執行 |
| AC-07-74 | 鎖被持有時，執行寫檔的 `req-export` | 拒絕（立即失敗） |
| AC-07-75 | `answer`（父操作）內部重建 requirements md 和 approval render | 不另外取鎖；沒有死結；檔案以原子替換寫入 |
| AC-07-76 | `answer` 在重建衍生輸出前中止 → 續做 | 衍生輸出被重建 |

#### 18.9 fd 不繼承與 fork 掛鉤（AC-07-77a～k）

以測試用的獨立暫存 root、多個子程序驗收。

| AC | 前置條件／情境 | 預期結果 |
|---|---|---|
| AC-07-77a | 父程序取得鎖，然後 `os.fork()`；子程序保持存活。另一個獨立程序嘗試取得鎖 | 獨立程序失敗（父程序仍持有，鎖沒有被子程序解除） |
| AC-07-77b | 接續 77a：子程序嘗試使用繼承來的 executor context 執行寫入 | 拋出「context 已失效」錯誤；沒有任何寫入 |
| AC-07-77c | 接續 77a：子程序自己重新走取得流程 | `LOCK_NB` 立即失敗（父程序仍持有）；沒有任何寫入 |
| AC-07-77d | 父程序在 fork 之後結束，子程序仍存活。獨立程序嘗試取得鎖 | **成功**（子程序已關閉它那一份 fd） |
| AC-07-77e | 父程序以 `subprocess.Popen` 啟動另一個程式（exec），然後結束；exec 子程序仍存活。獨立程序嘗試取得鎖（流程見下） | 成功（`O_CLOEXEC` 讓子程序沒有這個 fd） |
| AC-07-77e-ctrl | 敏感度對照組（流程見下） | C 持有 dup 的 fd 時，獨立程序取鎖失敗；C 關閉後取鎖成功 |
| AC-07-77f | 父程序在**持有鎖期間**多次 fork | 掛鉤只註冊一次；每個子程序都關閉 fd、context 都失效；父程序的鎖始終存在 |
| AC-07-77g | 程式碼檢查：QAOS 自身程式碼中 `os.fork`、`multiprocessing` 的使用 | 列出清單（預期為零）；有新增時，檢查提示要有對應的測試 |
| AC-07-77h | 同一程序：acquire → release → acquire → fork；子程序檢查 | 子程序關閉的是**第二次**取得的 fd；父程序的鎖仍在（獨立程序取鎖失敗） |
| AC-07-77i | 沒有持鎖時 fork | 掛鉤不做事；子程序可以正常 acquire |
| AC-07-77j | 父程序結束後，子程序 acquire，再 fork 孫程序 | 孫程序關閉繼承的 fd；子程序（現在的 executor）的鎖仍在 |
| AC-07-77k | 子程序在掛鉤執行後，先 acquire 自己的新 context ctx2（測試以同步點安排父程序先釋放），再以 fork 前取得的舊 ctx1 呼叫寫入函式 | `require_context(ctx1)` 因 `ctx1 is not _EXECUTOR`、token 不同、`owner_pid` 不符而拒絕；用 ctx2 可以寫入 |

另需補測的實作邊界（併入 77b、77h～k 驗收）：同一程序釋放後再取得、無鎖時 fork、子程序重新取得後再 fork、繼承 context 的清理路徑。

**77e 的同步通道**：

- harness H 在暫存目錄建立兩個具名 FIFO：`ctl`（H → C）、`status`（C → H），都以 `os.open(path, O_RDWR)` 開啟並**全程保持開啟**（P 結束不影響通道，C 不會讀到 EOF）。
- **期限與讀行**：每則訊息有固定截止時間 `deadline = time.monotonic() + timeout`（預設 5 秒）。讀取迴圈：`select.select([fd], [], [], max(0, deadline - time.monotonic()))` → 有資料就 `os.read(fd, 4096)` 附加到該 fd 專用的緩衝區 → 出現 `\n` 時切出一行，其餘留給下一則 → 超過截止時間還沒有完整一行 → 測試失敗並清理。`select` 可讀只代表有位元組；收到部分資料後**不改用**沒有期限的 `readline`。C 端讀 `ctl` 用同樣規則。
- 這套機制要在專案實際環境（macOS、Python 3.11）中驗證。

**77e 主流程**：

1. H 以 `subprocess.Popen([python, p_script, lock_path, ctl, status], stdin=PIPE, start_new_session=True)` 啟動 P；P 以 QAOS executor 取得鎖。
2. P 以 `subprocess.Popen([python, c_script, ctl, status])` 啟動 C（exec；不傳任何鎖 fd；不對 C 呼叫 `wait`）。
3. C 在 `status` 寫入 `ready <pid> <ppid>`，然後阻塞讀取 `ctl`。H 記下 C 的 pid 與當時的 ppid（等於 P 的 pid）。
4. P 結束，兩個變體：(i) H 透過 P 的 stdin 送 `exit`，P 正常結束；(ii) H 對 P 送 `SIGKILL`。
5. H 以 `Popen.wait()` 回收 P，確認已結束。
6. H 向 `ctl` 寫入 `probe`；C 在期限內回覆 `alive <pid> <ppid>`：pid 等於第 3 步記下的值，**ppid 不等於 P 的 pid**。能回覆即代表 C 正在執行；不以 `kill(pid, 0)` 證明存活。
7. 獨立程序 Q 執行 acquire → 預期**成功**；Q 立即釋放並結束，由 H 回收。
8. 清理：H 送 `release`，C 回覆 `bye` 後結束；H 輪詢等待 C 的 pid 不存在（`ProcessLookupError`），最多 5 秒（`kill(pid, 0)` 只用來確認清理完成）；逾時 → 對 C 送 `SIGKILL` 並把測試標為失敗。全部包在 `try/finally`：任何失敗都對仍存活的 P、C、Q 送 `SIGKILL`，回收 P、Q，關閉 FIFO，刪除暫存目錄。

**77e-ctrl：敏感度對照組**：

1. P 以 executor 取得鎖，持鎖的 fd 為 L。
2. P 執行 `D = os.dup(L)`（D 和 L 指向同一個 open file description，共享同一個 flock；`os.dup` 產生的 fd 預設不可繼承）。
3. P 以 `subprocess.Popen([python, c_ctrl_script, ctl, status, str(D)], pass_fds=(D,))` 啟動 C（`close_fds=True` 預設下只保留 D，以同一 fd 編號傳給 C）。
4. C 回報 `ready <pid> <ppid> fd=<D>`，**保持 fd 開啟**，繼續回應 probe。
5. P 結束（L 關閉，D 的副本仍在 C 中）；H 以 `Popen.wait()` 回收 P。
6. H 送 `probe`，C 在期限內回覆 `alive …`，且 ppid 已改變。
7. Q 取鎖 → **預期失敗**（`LOCK_NB` 立即失敗）。
8. H 送 `close-fd`，C 執行 `os.close(D)`，回覆 `closed`。
9. Q 再次取鎖 → **預期成功**；Q 釋放並結束，由 H 回收。
10. H 送 `release`，C 回覆 `bye` 並結束；依主流程第 8 步清理。

判讀：主流程中 Q 成功；對照組中 C 持有 dup 時 Q 失敗、C 關閉後 Q 成功。這證明測試確實能偵測「持鎖的 open file description 被子程序繼承」。單純「另開一個指向同一鎖檔的 fd」不能當對照組（另開的 fd 不會延續原本的 flock）。

#### 18.10 衍生輸出與 context 範圍

| AC | 前置條件／情境 | 預期結果 |
|---|---|---|
| AC-07-78 | 業務步驟全部完成後，以故障注入讓衍生輸出重建失敗 | 計畫**不標記**完成，保持 `in_progress`；之後 `resume` 重試重建並完成；業務檔不受影響 |
| AC-07-79 | (1) 非持鎖程序（含 admin-ui 後端以 Python 直接呼叫寫入函式）嘗試自行建立 context 或直接寫入；(2) fork 子程序使用繼承的 context | (1) 必須經過同一取得流程，否則拒絕；(2) 因 `owner_pid` 不符被拒絕（同 77b） |

#### 18.11 維護、准入與續做（AC-07-80～89、94～100）

全部走實際 CLI 和 executor；續做案例都分兩種入口，並套用通用驗收方式的四項斷言。

| AC | 前置條件／情境 | 預期結果 |
|---|---|---|
| AC-07-80 | 完整流程：`maintenance start` → `migrate` → `migrate verify` → `maintenance end` | 全部成功；end 之後是 `S_post` |
| AC-07-81 | `S_maint` 中執行一般業務寫入（例如 `answer`）、寫檔 export、`run cancel` | 拒絕（「維護中」） |
| AC-07-82 | `S_maint` 中執行唯讀指令與 `migrate verify` | 照常執行 |
| AC-07-83 | 有未完成的 rollback 計畫時執行 `maintenance end` | 拒絕 |
| AC-07-84 | `S_pre` 中執行 `migrate`（未進入維護） | 拒絕 |
| AC-07-85 | `S_pre` 中執行 `run cancel` → 中止 → `operation resume` | 允許續做 |
| AC-07-86 | `S_pre` 中有一份中止的 `run cancel` 計畫，此時執行 `maintenance start` | 拒絕（有未完成計畫）；續做完成後才允許 |
| AC-07-87 | `S_maint` 中 `operation resume` 一份業務計畫 | 拒絕（V4：不在它的 `resume_states`） |
| AC-07-88 | `maintenance start`（分別從 `S_pre`、`S_post` 開始）中止在 FP-S1、FP-S2 | 兩種入口都能續做完成；FP-S2 的維護檔不重寫；中止期間 `maintenance end`、`migrate`、`run cancel`、業務寫入都被拒絕，並提示續做 |
| AC-07-89 | `maintenance end` 中止在 FP-E1、FP-E2（FP-E2 分成移轉後到 `S_post`、回復後到 `S_pre` 兩例） | 兩種入口都能續做完成；FP-E2 是在 `S_pre`／`S_post` 中續做 end，**不被**初次請求白名單拒絕；中止期間 `maintenance start` 和業務寫入都被拒絕 |
| AC-07-94（防禦性） | 以測試專用的故障注入，讓 `locks/maintenance.yaml` 或移轉標記的 op_id 屬於其他 op，然後續做 start、migrate | V4 身分核對拒絕；不覆寫該檔。只證明身分檢查存在，不屬於正式流程 |
| AC-07-95 | 以 P1 的操作類型（`run cancel`、`maintenance start`、寫檔 export、`audit render`），在**每一種步驟**（業務檔、事件檔、衍生輸出、狀態紀錄之前的最後一步）的「輸出已落盤、完成紀錄未落盤」中止（FP-W） | 兩種入口都續做完成；該步只補寫一個完成紀錄，輸出不重寫（sha256、inode 不變）；多檔 render 中止在第 k 個檔之後：前 k 個略過，其餘依序寫入；另一例：多檔 render 中有部分檔案內容不變（在 `no_change`），中止點在它們前後各一次，結果相同 |
| AC-07-96 | 同 95 的中止狀態，續做之前分別竄改：① 刪除尾端之前某一步的完成紀錄；② 刪除一個有完成紀錄的輸出；③ 改寫完成紀錄的內容；④ 改寫尾端事件的內容 | 四例都在 V5 停止，回報證據衝突，不重寫任何檔案 |
| AC-07-97 | 登錄紀錄與狀態紀錄：① 在登錄紀錄寫入之後、第一步之前中止（FP-P2）；② 在 `status.d/<op>-completed` 寫入之前中止；③ 連續完成多個操作之後，重新驗證先前某個操作的紀錄；④ 改寫某個既有登錄紀錄的內容 | ①：續做時登錄紀錄只有一筆，`plan_seq` 不重新配發；②：續做時只建立狀態紀錄；③：後續操作新增的紀錄**不**讓先前的紀錄失效，`plan_seq` 連續、不重複；④：涉及該紀錄的續做（V1）與後續操作盤點被拒絕，`operation list` 回報衝突（附錄 A 4-11） |
| AC-07-98 | 未登錄計畫（FP-P1）：以 P1 的操作，在計畫檔保存之後、登錄紀錄寫入之前中止。之後分別：(a) 同請求重送；(b) `operation resume <op>`；(c) 不同 op 的寫入請求；(d) 在保存計畫**之前**中止，再送不同 op | (a)(b)：先登錄補齊，再續做完成；計畫檔的 sha256、`clock`、`allocated_ids` 不變；登錄紀錄只有一筆；(c)：登錄補齊之後，以 3b 拒絕，提示 resume；(d)：沒有任何殘留，照常執行 |
| AC-07-99（防禦性） | 以測試專用的故障注入，放入一份 schema 不符，或 `op_id` 和 `canonical_request` 不對應的未登錄計畫檔 | 所有寫入請求都拒絕，並回報該檔；不刪除、不覆寫、不登錄；唯讀指令照常執行。不屬於正式流程 |
| AC-07-100 | 內容不變的路徑，以 P1 的操作驗證：① 寫檔 export、`audit render` 的所有輸出都和現有檔案相同；② 部分輸出相同、部分不同；③ 同 ②，在每個內容步驟的前後各中止一次（含 FP-W），兩種入口續做；④ 同 ②，中止期間由測試竄改一個 `no_change` 路徑（稽核物、業務檔各一例） | ①：計畫沒有內容步驟，只有計畫檔、登錄紀錄、計畫要求的事件和 `completed`；不寫任何輸出檔；②：相同的檔在 `no_change`，不成為步驟；③：不同的檔依序寫入、續做完成；相同的檔不被選為 L，也不被判為衝突；④：稽核物 → 衝突，停止；業務檔 → `external_change`，停止；都不重寫 |

#### 18.12 migrate、rollback 的續做與接管（AC-07-90～93；規則見移轉與回復章）

| AC | 前置條件／情境 | 預期結果 |
|---|---|---|
| AC-07-90 | `migrate` 中止在 FP-M3、FP-M5（另以 FP-M0、FP-M2 確認從中段續做） | 兩種入口都能續做；標記不重寫，每個 render 檔只寫一次，`status.d/<X>-completed` 只有一個；已寫事件不重寫；中止期間只允許 `migrate rollback --op X` 接管，`migrate --new-request` 和業務寫入都被拒絕 |
| AC-07-91 | `migrate` 的第一次 render 失敗（FP-M4，故障注入在 render） | 計畫保持 `in_progress`；續做時重建 render → 完成；`audit.log` 開頭逐位元等於移轉前的原檔 |
| AC-07-92 | rollback R 中止在 FP-R0（R 已建立，X 還沒標記） | 兩種入口都能續做 R，`status.d/<X>-aborted_for_rollback` **只有一個**；中止期間：重送 X、`operation resume X` 都被拒絕並提示續做 R；`migrate rollback --op X --new-request` 被拒絕；其他 op 被拒絕 |
| AC-07-93 | rollback R 中止在 FP-R1、FP-R2 | 兩種入口都能續做完成；`x_progress`、`later_ops_snapshot` 不重算；FP-R2 是在無標記的 `S_maint` 中續做，符合 R 的 `resume_states` |

#### 18.13 AC 的最早驗收階段

| AC 群組 | 最早的部分驗收 | 完整驗收 |
|---|---|---|
| AC-07-8 | P1（以 submit_gate 驗證「驗證失敗不寫業務檔」） | — |
| AC-07-9a～9n、10、12、13～19（20、21 已撤銷） | P1（可獨立驗證的部分） | 依賴去重或 CLR 生命週期的部分在 P5（例如 AC-07-10、9x、9y、9aa） |
| AC-07-22～29 | P1（§16 中標 P1 的類型） | P2／P3／P5／P6（依 §16） |
| AC-07-36～49、64～79（含 77a～k） | P1 | — |
| AC-07-80～89、94～100 | P1（88、89、94、99 也在 P1；95～98、100 以 P1 的操作類型驗證） | — |
| AC-07-90～93 | — | P3 |

早期階段只驗收能獨立驗證的部分；不手造業務狀態，也不把還不能執行的 AC 標成通過，這些在完成紀錄中標「待 Pn」，於 P6 結清。

---

### 19. 已知限制

1. **單機、本地檔案系統**：flock 只在同一台主機的本地檔案系統上可靠。不支援 NFS 或多主機共用。
2. **fork 的覆蓋範圍**：fork 子程序的隔離只涵蓋經由 Python 的 fork（`os.fork`、`multiprocessing` 的 fork 啟動方式；`register_at_fork` 的範圍）。C 擴充模組直接呼叫 `fork(2)` 不在保證範圍內；QAOS 目前沒有這類依賴，並以靜態檢查（AC-07-77g）提示新增的使用。
3. **全域鎖無法並行**：不同 run 的寫入操作無法同時執行；對目前單機、單一使用者的用法沒有影響。
4. **唯讀指令不保證一致快照**：可能讀到另一個操作寫到一半的多檔狀態。
5. **不承諾多檔原子性**：中止後多檔處於中間狀態，靠續做到 `post_state` 收斂。
6. **整段尾端被一致刪除無法偵測**：把最後一個或幾個已執行步驟的輸出和完成紀錄一起刪掉（或把業務檔還原成 before 再刪掉紀錄），無法和「從未執行」區分。
7. **外部寫入成計畫值會被當成已執行**：中止期間外部把某個未執行步驟的輸出寫成剛好等於計畫值，這一步會被當成已執行；如果它在原本的尾端之後，會把 L 往後推，使前面未執行的步驟被判為衝突（拒絕，不會誤放行）。
8. **不保證偵測所有外部修改**：flock 只排除經過 executor 的寫入；不取鎖的外部修改（例如 admin-ui 後端直接寫檔）沒有跨多檔的原子保證，落在計畫路徑以外的修改可能不被發現。維護窗口期間必須以人工協調停止其他外部寫入。
9. **維護模式的導入**：新程式部署之前，舊程式不認得維護檔，維護窗口只能靠人工協調。
10. **`audit.log` 改成整份替換**：不再追加；現有讀取者（含 admin-ui，Session B）需要配合。
11. **診斷檔不是權威**：只供顯示，可能過期。
12. **第三方依賴的 fork**：對 QAOS 原始碼的靜態搜尋為零，不代表第三方或原生依賴不會 fork；實作審查時須另外核對。
13. **防禦性驗收**：AC-07-36～38 的另一個 op 的事件檔或暫存檔，正式流程中不會出現（flock 與第 3b 步不允許兩份未完成計畫交錯），所以以故障注入建立，只證明「不碰其他操作的檔案」的檢查存在。


---

## 第 5 章　RM revision、綁定、CIA 候選完整性、移轉與回復（FIX-09）

> 本章所有 AC 都是**預期結果**，尚未實作、尚未執行。
> 執行器（flock、操作計畫、登錄紀錄、完成紀錄、`classify_steps`、維護模式、初次請求准入與續做驗證）的完整規則見執行器章（FIX-07）；本章只寫移轉與回復需要的部分，並和執行器章共用同一套函式與狀態。

---

### 1. 目的

1. 需求模型（RM）不再被覆寫：同一個 spec 版本每次持久化都產生不可變的修訂版（revision），run 與 TC 版本都綁定確切的 revision。
2. 舊 run 恢復時，一律讀它綁定的 revision，不讀可變的檢視。
3. 依引用閉包判定「過時」，擋住不該沿用舊分析的 `_skip` 與無 T0 的流程。
4. 同一個 spec 版本可以重新做變更影響分析（同版本 CIA）。
5. CIA 的候選涵蓋同一 spec 的**全部** ACTIVE TC，依每張 TC 自己的 pin 分組，並以 G1～G8 機械檢查恰好分割。
6. 既有資料以一次性、可續做、可回復的移轉（`migrate`）建立 R000、綁定 sidecar、CLR rev 0，並保留 legacy audit。
7. 移轉可以由 `migrate rollback` 接管並回復；回復有准入、凍結證據、兩次終態前檢查與受控的人工修復。

---

### 2. 名詞

共用名詞（CanonicalRequest、op_id、basis、basis_hash、SourceRef、QuestionScope、DecisionPoint、effective_basis）定義見共用名詞章。本章另外使用：

| 名詞 | 定義 |
|---|---|
| **SpecPin** | `{spec_id, spec_version, content_hash}`；使用時 content_hash 要和 `spec.yaml` 登記值、實體檔的 sha256 都相符 |
| **RMPin** | 指向一份 RM revision 的釘選：`{spec_id, spec_version, revision, sha256}` |
| **RefNode** | 引用閉包中的一個節點：SpecPin ＋ `decl_rev` ＋ `role`（normative／informative）＋ `depth` |
| **RM revision** | 同一 spec 版本下不可變的需求模型修訂版，檔名 `R000`、`R001`… |
| **檢視** | `requirements.yaml`，最新 revision 的實體化內容，供既有讀取者使用；不是依據的權威來源 |
| **sidecar** | 不修改原檔、另外寫一個綁定檔來記錄 RMPin。run sidecar：`artifacts/requirements/_bindings/<run_id>.yaml`；TC sidecar：`testcases/_bindings/<tc_id>-v<N>.yaml` |
| **legacy_binding** | sidecar 上的旗標 `legacy_binding: true`，表示這是移轉時的**盡力綁定**，不宣稱是當時實際使用的模型 |
| **pin_groups** | CIA 報告中依「TC 自己的 RMPin」分出的組：`{from_pin: RMPin, testcase_ids[], requirement_diff[]}` |
| **PlanStep** | 操作計畫的一步：`{path, expected_before, expected_after, content_ref}`；同一計畫中每個 path 最多一步 |
| **移轉標記** | `artifacts/requirements/_migration.yaml`；存在表示已移轉 |
| **移轉清單（manifest）** | `operations/_global/<migrate_op>/manifest.yaml`，逐檔記錄移轉會碰到的每個路徑與其類別（§11.3） |
| **X、R** | X：一份 `migrate` 計畫。R：一份 `migrate rollback` 計畫，接管 X（`takeover_of: X`） |
| **登錄紀錄** | `operations/_global/index.d/<plan_seq>-<op_id>.yaml`，每份計畫一筆、不可變 |
| **狀態紀錄** | `operations/_global/status.d/<op_id>-<status>.yaml`，每個 (op, status) 一筆、不可變；沒有狀態紀錄 → `in_progress` |
| **完成紀錄** | `operations/<scope>/<op>/progress.d/<seq>-<step>.yaml`，內容 `{op_id, seq, step_id, path, after_sha256}`；每步輸出落盤並 fsync 之後以 link 建立 |
| **`classify_steps`** | 判定計畫每一步是 `done`、`not_executed`、合法尾端、衝突或 `external_change` 的單一函式（§13.4）；rollback 接管准入（T5）與續做（V5）共用 |
| **`no_change`** | 計畫產生時 `expected_before` 等於 `expected_after` 的路徑；不成為步驟，只記錄路徑與當時內容（或「不存在」） |
| **合法尾端** | 最後一個已執行步驟「輸出已落盤、完成紀錄未落盤」；整份計畫最多一個 |
| **S_pre／S_maint／S_post** | S_pre：沒有移轉標記、不在維護中。S_maint：`locks/maintenance.yaml` 存在（不論是否已移轉）。S_post：有移轉標記、不在維護中 |
| **`x_progress`** | R 建立時對 X 執行 `classify_steps` 的凍結結果（§13.5） |
| **`later_ops_snapshot`** | R 建立時計算的「X 之後的業務寫入計畫」清單（§13.11） |

---

### 3. RM revision 與檢視

1. 每次持久化需求，都寫入不可變的 `artifacts/requirements/<spec_id>/v<ver>/revisions/R<NNN>.yaml`。內容包含：sha256、來源、`run_id`、`reason`、`target_decl_rev`、`reference_pins`（RefNode 閉包，§5）、`decision_snapshot_hashes`、`op_id`。
2. revision 的索引放在 `artifacts/requirements/<spec_id>/v<ver>/revisions/index.yaml`。
3. `requirements.yaml` 保留為最新 revision 的實體化檢視，供既有讀取者使用。
4. **今後只能透過** `store.save_requirements(spec_id, ver, doc, reason, by)` 寫需求；它產生新 revision、更新索引與檢視。CLR apply、manual-run 腳本都走這個函式。歷史上直接寫檔的腳本不回頭修改；直接寫檔的偵測（`req verify`）屬第二批。
5. **移轉不修改既有的 `requirements.yaml`**：
   - legacy 的 `requirements.yaml` 等同 R000 的檢視，兩者 hash 相同（R000 是原檔的逐位元複本）。
   - 移轉新建 `revisions/R000.yaml`、`revisions/R000.meta.yaml` 與 `revisions/index.yaml`。
   - **R000 的不可變輔助資料**：R000 是 legacy 檔的逐位元複本，不能加欄位，所以 R000 的 `target_decl_rev` 與 `reference_pins` 存在 `revisions/R000.meta.yaml`：`{revision: R000, legacy: true, revision_sha256（= R000 的 sha256）, target_decl_rev: 0, reference_pins: [], created_by_op}`。這個檔由移轉計畫以「只能建立」的步驟寫入一次，之後不修改。
   - **為什麼是 0 與空閉包**：移轉之前不存在任何引用宣告（`spec reference` 等宣告指令只能在 `S_post` 執行），所以每個 legacy spec 版本在移轉當下的 `decl_rev` 都是 0、閉包為空。這是由移轉前的狀態推得的事實，不是以目前的 registry 動態填入。
   - **移轉的前提**：移轉時，如果有任何 spec 版本已經有 `references` 或 `reference_declarations`（正式流程中不會發生），移轉拒絕，不建立計畫（AC-09-91）。
   - **統一的讀取規則**：所有需要 revision 的 `target_decl_rev` 或 `reference_pins` 的地方（過時判定、`_skip`、無 T0 流程的 `run new`、派發、CIA 的 pin_groups），一律經由同一個解析函式取得：R001 之後讀 revision 檔本身的欄位；R000 讀 `R000.meta.yaml`。缺少應有的資料 → 拒絕並回報，不以目前狀態補值。
   - 移轉之後的新分析，仍經由 `save_requirements` 更新檢視；「不修改」只限移轉當下。
   - schema、`save_requirements`、讀取點與回復測試都要配合這條規則。
6. 同一版本重新分析 → 產生 R(n+1)，R(n) 位元不變。

---

### 4. 綁定與解析

#### 4.1 解析順序

- **run 的依據**：run.yaml 的 `requirement_model_revision`（run pin）→ run sidecar → **錯誤**。
- **TC 的依據**：TC 版本檔內的 `requirement_model_revision`（TC pin）→ TC sidecar → **錯誤**。
- 任何地方都**不退回**讀可變的檢視。
- 進行中的 run 一律使用它已綁定的 revision；恢復執行（例如核准後繼續）時不重新解析 `requirements.yaml`。
- 涵蓋的讀取點：
  - `engine.py` 的 `_materialize_testcases`、`_active_requirements` 的所有呼叫端；
  - `gates.py` 的 `g_design`、`g_impact`、`g_risk`；
  - `refs.resolve` 對 Requirement 的解析；
  - 派發包的產生；
  - `tc_ops`；
  - `req_export`、`final_export`：在 run 的脈絡內用 run 綁定的 revision；在 run 外輸出時用最新 revision，並在輸出中標明 revision。

#### 4.2 六個 workflow 的綁定表

| workflow | 目標 spec／版本的來源 | 新 run 的綁定 | CLR 納入（A4） | 移轉時的既有 run | reference_only 拒絕點 |
|---|---|---|---|---|---|
| spec-to-testcase | inputs 的 `spec_id`、`spec_version` | T1 提交時，或 `_skip` 時（`new_run` 中） | T1 提交 | 有 RM → sidecar 綁目標版本的 R000；T1 尚未完成 → 不綁，之後正常綁定 | inputs |
| spec-change-impact | `spec_id`、`from_version`、`to_version`（同版本時加 `from_revision`、`reason`） | from：`new_run` 時綁最新 revision（同版本時用 `from_revision`）；to：T0 提交或 `_skip` 時 | T0 提交 | sidecar：from、to 兩端各綁該版本的 R000（存在才綁）；TC 依各自的 sidecar | from、to |
| spec-to-bug | inputs 的 `spec_id`、`spec_version` | T0 提交時，或 `_skip` 時 | T0、G-BVAL 提交 | 有 RM → sidecar 綁 R000 | inputs |
| testcase-revision | TC 版本自己的 `spec_id`、`spec_version`（`tc_ops.revise`） | `new_run` 時綁該版本的最新 revision（§4.3） | 不納入 | sidecar 綁 R000，`legacy_binding: true` | 由 TC 推得的 spec_id |
| manual-test-to-regression | inputs 的 `spec_id`，或 manual record 的 `spec_hint`；**兩者都沒有 → 拒絕** | `new_run` 時綁最新 revision（§4.3） | 不納入 | sidecar 綁 R000，`legacy_binding: true` | inputs、`spec_hint` |
| regression-generation | 不涉及 spec（`target_suites`、`scope`、`change_impact_id`） | 不綁 | 不納入 | **不產生** sidecar（明確例外） | 不適用 |

- 跳過 T0（`_skip`）時，run 綁定最新 revision。
- 沒有 T0 的流程（testcase-revision、manual）在 `run new` 時凍結 revision。

#### 4.3 testcase-revision 與 manual

- **testcase-revision**：`new_run` 時綁定該 TC `spec_version` 的最新 revision；被修訂 TC 自己的舊 pin 一併記錄，供 diff 使用。以下任一成立 → `run new` **拒絕**，提示先重新分析：
  - `declaration_changed`；
  - `decision_revised`；
  - 最新 revision 有非 ACTIVE 的需求。
- **manual-test-to-regression**：
  - inputs 的 `spec_id`／`spec_version` 或 manual record 的 `spec_hint` 必須有一個存在，而且指向已匯入、非 reference_only 的版本。
  - 兩者都沒有 → `run new` **拒絕**，不建立 run（`runs/` 不留下新目錄；計數器不前進），提示「先在 manual record 補 `spec_hint`，或以 inputs 指定 spec」。
  - 有 spec 時：綁定與拒絕條件同 testcase-revision。
  - 保留「沒有 spec 就不能產生正式 TC」的既有限制；`manual new` 本身照常可以建立，不需要 spec。

#### 4.4 reference_only 的 7 個入口

以下 7 個入口遇到 reference_only 的 spec 版本一律拒絕（reference_only 的定義見 FIX-01 章）：spec-to-testcase 的 inputs、spec-change-impact 的 from、spec-change-impact 的 to、spec-to-bug 的 inputs、testcase-revision（由 TC 推得）、manual 的 inputs、manual 的 `spec_hint`。

---

### 5. 引用閉包

- `reference_pins` = 從目標 spec 版本出發的 **normative 遞移閉包**，加上**直接層**的 informative 參考。
- revision 另外記錄 **`target_decl_rev`**：目標 spec 版本自己在分析當時的 `decl_rev`（沒有任何宣告時為 0）。目標的宣告變動（含 `declare-empty`、在 `declared_empty` 之後新增）即使不改變閉包內容，也會改變它。
- 每個節點記錄 SpecPin、`decl_rev`、`depth`（即 RefNode）。
- 以 `spec_id@version` 的已訪集合終止循環；閉包不重複。
- 節點超過 **50** 個 → 拒絕。
- 派發包只把 `depth=1` 的節點列為必讀；遞移節點用於過時判定。

---

### 6. 過時判定

過時判定是**衍生查詢**，不寫入任何 RM。判定函式在第一批（`_skip`、派發、無 T0 流程的 `run new` 會用到）；`spec outdated` 報表在第二批。

| 判定 | 條件 | 效果 |
|---|---|---|
| `newer_available` | 閉包中某個 spec 有更新的匯入版本 | 只提示；不改 pins，不擋 `_skip` |
| `declaration_changed` | 目標 spec 版本目前的 `decl_rev` 和 revision 記錄的 `target_decl_rev` 不同；或閉包中**任一節點**目前的 `decl_rev` 和 pins 記錄的不同；或閉包組成改變 | 擋 `_skip`；擋無 T0 流程的 `run new` |
| `decision_revised` | revision 引用的 CLR 答案已經不是最新的 `answer_rev` | 擋 `_skip`；擋無 T0 流程的 `run new` |

- `req accept-declaration <spec_id@ver> --rev R<NNN> --reason`：產生新 revision，需求內容相同、pins 更新，並記錄 `accepted_diff`（新增或移除的節點）與 `accepted_without_analysis: true`，明示新 pins 的文件**沒有經過分析**。
- references remove → 產生新的 `decl_rev`；舊 revision 的 pins 不變。

---

### 7. `_skip` 的優先序

依序判斷，第一個成立者決定結果：

1. 沒有 RM → 不跳過。
2. 最新 revision 有任何非 ACTIVE 的需求 → 不跳過（優先於 legacy 例外）。
3. `declaration_changed` 或 `decision_revised` → 不跳過。
4. 只有 R000（legacy）、`references_status: undeclared`、全部 ACTIVE → 跳過，並在 run 的 audit 記錄警告。
5. 其他 → 跳過。

跳過時，run 綁定最新 revision。

---

### 8. 同版本 CIA

- 指令：`run new spec-change-impact --input spec_id=X --input from_version=V --input to_version=V --input from_revision=R<NNN> --input reason=declaration_changed|decision_revised|decision_applied`。
- 同版本時 `from_revision` 和 `reason` **必填**；缺任一 → `run new` 拒絕。
- `from_revision` 必須是該版本已存在的 revision。
- `reason` 必須和判定函式的實際結果相符（例如宣稱 `declaration_changed` 時，判定函式必須回報該狀態）；不符 → 拒絕。
- 同版本時 T0 **一定執行**（`run_if` 視為成立），產生 `to_revision`。
- CIR 新增 `from_rm_revision`、`to_rm_revision`（RMPin）；`g_impact` 依 revision 讀需求，不讀檢視。
- T1、T4 的派發包帶兩端（與全部 pin_groups）的 RMPin。

---

### 9. CIA 候選完整性與 pin_groups

適用於同版本與跨版本的 spec-change-impact。

1. **候選** C = `spec_id` 等於 CIR 的 spec_id、狀態為 ACTIVE 的**全部 TC**，不論 spec_version 與 revision。
2. 每張 TC 的 pin 依 §4.1 解析（版本檔欄位 → TC sidecar）。依不同的 pin 分組：

   ```text
   pin_groups[]: {from_pin: RMPin, testcase_ids[], requirement_diff[]}
   to_rm_revision: RMPin
   testcase_impact[]: {..., pin_group_index}
   ```

3. 每組的 `requirement_diff` 涵蓋「該組 from_pin 的需求 ∪ to_revision 的需求」。
4. **`g_impact` 的分割檢查**：令 G_k 為第 k 組的 `testcase_ids`，I 為 `testcase_impact` 的 ID 清單。以下全部成立才 PASS：

   | # | 檢查 |
   |---|---|
   | G1 | 每組 `testcase_ids` 非空，組內沒有重複 |
   | G2 | ⋃G_k = C，而且 Σ\|G_k\| = \|C\|（恰好分割：沒有缺、沒有重複歸組、沒有額外 ID） |
   | G3 | 各組的 `from_pin` 互不相同 |
   | G4 | 對每張 t ∈ G_k，t 自己解析出的 pin 等於 G_k 的 `from_pin` |
   | G5 | I 恰好等於 C：沒有缺、沒有重複、沒有未知 ID |
   | G6 | 每筆 `testcase_impact` 有 `pin_group_index`，而且等於該 TC 所屬組的索引 |
   | G7 | 每組的 `requirement_diff` 恰好涵蓋「from_pin 的需求 ∪ to_revision 的需求」，每個需求恰好一次 |
   | G8 | `from_pin` 能解析到實際存在、hash 相符的 revision |

5. unaffected 的 TC 保留原 pin（與 spec_version），下一輪會再以它自己的 pin 比對，不會被排除。affected 的 TC 新版本綁定 `to_revision`。
6. 這修正現行 `g_impact` 只要求判定 `spec_version == from_version` 的 TC 的缺口（`gates.py:185`）。

---

### 10. `run cancel`

- 把 run 轉為 CANCELLED，並把該 run **所有** PENDING 的核准單（不只 `waiting_on_approval_id`）轉為 CANCELLED。
- 每張被取消的 `approval_id` 和取消理由寫進 run 的 audit 事件。
- 已綁定的 revision 和 sidecar 保留。
- 以操作計畫執行；重送不重複轉換、不重複寫 audit。
- 准入：S_pre 允許（移轉前白名單，使用新版規則）；S_maint 拒絕（維護中改用 `migrate --cancel-run`）；S_post 允許。
- 移轉標記寫入之前，`run cancel` **只寫 audit 事件檔，不 render**，不寫入、不改動任何既有的 `audit.log`。

---

### 11. 移轉 `migrate`

#### 11.1 執行狀態與准入

第 0 步、登錄補齊、初次請求白名單、續做驗證 V1～V5 與各 action 的 `resume_states`（含 `migrate`、`migrate rollback`）以第 4 章 §6、§8 為準，本章不重複。和移轉直接相關的重點：`migrate` 只能在 `S_maint`、標記不存在時作為初次請求；`migrate rollback` 依本章 §13.1 的 T1～T7；業務寫入計畫的 `resume_states` 只有 `S_post`，所以移轉前與維護中都不能續做業務計畫。

#### 11.2 指令與 RUNNING run 的處理

- `migrate [--acknowledge-idle <run_id>]… [--cancel-run <run_id>]… [--new-request]`，兩個旗標都可以重複。
- 每個 **RUNNING** 的 run，必須由人逐一選擇處理方式，並記錄在清單的 `mode_per_run` 與移轉標記中：
  - `--acknowledge-idle <run_id>`：確認沒有 agent 正在執行，以目前狀態寫 sidecar；run.yaml 不修改（列入 `untouched`）。
  - `--cancel-run <run_id>`：在**同一個**移轉操作中，先執行該 run 的取消步驟（同 §10：run 轉 CANCELLED、所有 PENDING APR 轉 CANCELLED、只寫事件檔），再寫 sidecar。
  - 或事先在 S_pre 以 `run cancel` 取消。
- 三者都沒有 → **拒絕，而且不寫任何檔案**（連計畫都不寫）。
- 部署當天以重新讀取的業務現況為準決定處理方式（§15 M3）。

#### 11.3 移轉清單（manifest）

`migrate` 在**取得 flock 之後、任何業務寫入之前**，依**實際的 pre-state 逐檔**產生清單。

- 對 `restore` 類的每個檔案，把原始位元組備份到 `operations/_global/<migrate_op>/backup/<原路徑>`。
- 清單以原子方式寫入，sha256 記在移轉計畫中。
- **所有路徑都是完整的具體路徑**，不用目錄或 glob 當作刪除依據。
- 清單和 backup 的內容在建立計畫時就已決定並寫在計畫檔中；migrate 開頭的**清單步驟**只負責把它們寫成檔案：清單一步、每個 backup 一步，每一步都有 `expected_after`。

```text
manifest:
  migrate_op_id, created_at, base_commit, mode_per_run: {RUN-…: acknowledge_idle | cancel_run}
  restore[]:        {path, category, pre_sha256, backup_path, backup_sha256, planned_post_sha256}   # 原本存在、會被修改
  remove[]:         {path, category, planned_post_sha256}                                           # 原本不存在、本次新增
  retain_audit[]:   {path, category, producing_step, kind: control | index | event | progress | status, planned_sha256}  # 回復後保留的稽核證據
  planned_audit[]:  {path, producing_step, kind, planned_sha256}                                    # 預定稽核輸出；只是預定，不是證據
  shared_control[]: {path, category, pre_state: present | absent, rule}                             # 不恢復、不刪除；依 rule 核對
  untouched[]:      {path, pre_sha256}                                                              # 必須不變
```

共六個類別。**分類由 migrate 依實際狀態決定**；同一種資料，原本存在和原本不存在會落在不同類別：

| 資料 | 原本存在時 | 原本不存在時 | acknowledge-idle | cancel-run |
|---|---|---|---|---|
| `runs/<id>/run.yaml`（被處理的 RUNNING run） | `restore` | （不會發生） | 不列入（不修改，改列 `untouched`） | `restore` |
| 該 run 的 PENDING `approvals/APR-*.yaml` | `restore` | — | 不列入（`untouched`） | `restore` |
| 上述 APR 的 render（`approvals/APR-*.md`、`.html`） | `restore` | `remove` | 不列入 | 依實際狀態 |
| 有答案的 `clarifications/**/CLR-*.yaml`（追加 rev 0） | `restore` | — | `restore` | `restore` |
| 上述 CLR 的 render（`CLR-*.md`） | `restore` | `remove` | 依實際狀態 | 依實際狀態 |
| `artifacts/requirements/**/revisions/R000.yaml`、`revisions/R000.meta.yaml`、`revisions/index.yaml` | — | `remove` | 同左 | 同左 |
| `artifacts/requirements/**/requirements.yaml` | `untouched` | — | 同左 | 同左 |
| run sidecar、TC sidecar | — | `remove` | 同左 | 同左 |
| `runs/<id>/audit.legacy.log`、`runs/_audit.legacy.log` | （不應存在；存在 → 移轉拒絕） | `remove`（重新移轉時會再產生） | 同左 | 同左 |
| `runs/<id>/audit.log`、`runs/_audit.log`（第一次 render 時整份替換或新建） | `restore`（備份原位元組） | `remove`（render 新建的） | 同左 | 同左 |
| 移轉的 audit 事件檔 `runs/<id>/audit.d/<migrate_op>-<step>.yaml`、`runs/_audit.d/<migrate_op>-<step>.yaml`（含 cancel 事件） | — | 先列 `planned_audit`；實際落盤後屬 `retain_audit`（kind: event） | 同左 | 同左 |
| 移轉標記 `artifacts/requirements/_migration.yaml` | （存在 → 已移轉，移轉拒絕） | `remove` | 同左 | 同左 |
| 移轉計畫 `operations/_global/<migrate_op>.yaml`、清單、backup 檔 | — | `retain_audit`（kind: control） | 同左 | 同左 |
| 步驟完成紀錄 `operations/_global/<migrate_op>/progress.d/*` | — | 先列 `planned_audit`；實際落盤後屬 `retain_audit`（kind: progress） | 同左 | 同左 |
| X 的登錄紀錄 `operations/_global/index.d/<plan_seq>-<migrate_op>.yaml` | — | `retain_audit`（kind: index；在清單步驟之前寫入） | 同左 | 同左 |
| X 的狀態紀錄 `operations/_global/status.d/<migrate_op>-completed.yaml` | — | 先列 `planned_audit`（kind: status）；實際落盤後屬 `retain_audit` | 同左 | 同左 |
| 移轉前已存在的其他登錄紀錄、狀態紀錄（`index.d/*`、`status.d/*`，逐檔列出） | `untouched` | — | 同左 | 同左 |
| `locks/qaos-operation.lock` | `shared_control`（rule：必須存在；**永不刪除**） | `shared_control`（同左） | 同左 | 同左 |
| `locks/qaos-operation.owner` | `shared_control`（rule：任意內容，只供診斷） | `shared_control`（同左） | 同左 | 同左 |
| `locks/maintenance.yaml`（內容含開始它的 `maintenance start` op_id） | `shared_control`（rule：依維護狀態，由 `maintenance start\|end` 管理） | — | 同左 | 同左 |
| `operations/_global/index.d/`、`status.d/` 目錄 | `shared_control`（rule：只新增檔案；清單列出的既有紀錄不變） | `shared_control`（同左） | 同左 | 同左 |
| `spec.yaml`、TC 版本檔、`testcases/registry/*`、其他 run 的 run.yaml | `untouched` | — | 同左 | 同左 |

#### 11.4 計畫固定所有輸出

- 計畫保存時就固定：`clock`、`allocated_ids`、每一步的 path、`expected_before`、`expected_after`，以及 `audit_events` 的**完整 payload**（事件時間一律取自計畫的 `clock`）。
- 所以每一個步驟（含事件檔、清單、backup、衍生輸出、登錄與狀態紀錄）都有建立計畫時就能算出的 `expected_after` sha256；續做時事件檔一律以完整 sha256 核對。
- `expected_before` 等於 `expected_after` 的路徑不成為步驟，改列計畫的 `no_change[]: {path, kind, content_sha256 | absent}`；因此每一步都滿足 before ≠ after。
- 每一步依序：(1) 寫輸出 → (2) fsync → (3) link 完成紀錄；三件事都完成才進入下一步。最後一步是 `status.d/<X>-completed.yaml`，它沒有完成紀錄，本身就是完成證據。

#### 11.5 步驟順序

建立順序：取得 flock、通過准入 → 在記憶體產生完整計畫 → 原子保存計畫檔（**保存完成就是計畫已建立**）→ 以 link 建立登錄紀錄 → 依序執行步驟：

1. **清單步驟**：清單一步、每個 backup 一步。
2. **凍結 legacy audit**：對每個 `runs/<id>/audit.log` 與 `runs/_audit.log`：
   - 存在 → 逐位元複製成 `audit.legacy.log`；計畫記錄來源的 sha256（產生計畫時讀取），步驟的 `expected_before` 為「不存在」，`expected_after` 等於來源的 sha256。
   - 不存在 → 在移轉標記中記錄 `legacy: absent`。
3. **cancel 步驟**（`--cancel-run` 指定的 run）：只寫事件檔，不 render。
4. **R000**（逐位元複製 `requirements.yaml`）、`revisions/R000.meta.yaml`（只能建立；`target_decl_rev: 0`、`reference_pins: []`）與 `revisions/index.yaml`。
5. **run sidecar**（6 個 workflow，依 §4.2 的移轉欄）。
6. **CLR rev 0**：每張有答案的 CLR 建立 `answer_revisions[0]`，含 legacy basis `{target: CLR 的 spec_id@spec_version（content_hash 取自移轉計畫產生時的 registry）, target_decl_rev: 0, closure: []}` 與它的 basis_hash（理由同 R000：移轉前不存在任何宣告）；這些值在移轉計畫中固定；CLR 狀態不變。
7. **TC sidecar**：所有 ACTIVE 以及 PENDING_APPROVAL 的 TC 版本，綁定**該版本 spec_version 的 R000**，標 `legacy_binding: true`。
8. **移轉標記**。
9. **第一次 render**（§11.7）：衍生輸出每個檔案一步。
10. **狀態紀錄** `status.d/<X>-completed.yaml`。

- 各業務步驟對應的 audit 事件步驟依計畫的 `audit_events` 寫入（以 link 建立，已存在就失敗）。
- 業務步驟寫完、它對應的事件步驟還沒執行就中止：業務步驟是 L（合法尾端或 `done`），事件步驟是 `not_executed`，不算竄改。

#### 11.6 移轉標記的內容

`artifacts/requirements/_migration.yaml` 包含：

- `migrate_op_id`；
- 時間、執行者；
- 檔案清單和 hash；
- run 清單，以及每個被處理 RUNNING run 的處理方式（acknowledge-idle／cancel-run）；
- 每一個 log 的 legacy 狀態：`frozen: <sha256>` 或 `absent`。

標記存在而且 `migrate_op_id` 不是本計畫 → 屬於其他 op，續做拒絕、不覆寫。

#### 11.7 第一次 render 與 `audit.log`

- 移轉標記寫入之前，所有操作只寫事件檔、不 render，不改動任何既有的 `audit.log`。標記寫入之前手動執行 `audit render` → 拒絕。
- render 的規則（標記寫入後）：
  - 該 log 在標記中是 `frozen` → 讀取 `audit.legacy.log`，驗證 sha256 → **原位元組照抄**作為開頭（不重新排序、不解析）→ 接上事件檔依 `(at, op_id, step)` 排序後的內容 → 原子替換 `audit.log`。
  - 在標記中是 `absent`，或是移轉後才建立的 run（標記中沒有它，而且 run 的 `created_at` 晚於標記時間）→ 只用事件檔。
  - 其他情況（標記中應有它卻缺 legacy 檔、hash 不符）→ **拒絕**，不以空檔代替。
- 第一次 render 涵蓋所有 log，每個檔一步；render 失敗時該檔仍是 before（原子替換沒有發生），計畫保持 `in_progress`，續做時以計畫固定的 `clock` 和輸入快照重新產生同一份內容；重新產生的內容和 `expected_after` 不同 → 停止，不寫入。
- `audit.log` 只在「新程式部署並進入維護」到「移轉標記寫入」之間停止更新；標記寫入之後，即使仍在維護中，第一次 render 與之後允許的指令都會更新 `audit.log`。

#### 11.8 移轉的續做

- 中止後以同請求重送或 `operation resume X` 續做，走執行器的續做驗證（V1～V5）：
  - `done` → 略過；合法尾端 → 補寫**這一步自己**的完成紀錄後略過；`not_executed` → 依序執行。
  - 稽核物衝突或業務檔 `external_change` → 停止，不重寫任何檔案。
- 凍結步驟：legacy 已存在而且 sha 相符 → 略過。凍結在標記之前，標記之前不 render，所以「凍結到已 render 的內容」不可能發生。
- 計畫檔已保存、登錄紀錄還沒寫 → 下一個寫入請求先做登錄補齊，沿用原計畫的 `clock`、`allocated_ids`，計畫檔不改。
- X 未完成期間，只允許 `migrate rollback --op X` 接管；`migrate --new-request` 與業務寫入都被拒絕。

---

### 12. `migrate verify`

- `migrate verify`（移轉後）與 `migrate verify --rolled-back`（回復後）是唯讀指令，不取鎖；輸出標明「讀取期間如果有寫入，結果可能不一致」。在維護窗口中執行時結果一致。
- 依類別核對：

| 類別 | 移轉後 | 回復後 |
|---|---|---|
| `restore` | 等於 `planned_post_sha256` | 等於 `pre_sha256` |
| `remove` | 等於 `planned_post_sha256` | 不存在 |
| `retain_audit`（X） | X 已完成：全部存在；sha256 等於計畫值 | 依 R 凍結的 `x_progress`：`done` 的稽核物（含 `content_tail`）存在、sha256 等於凍結值；缺失或竄改 → **失敗**（證據衝突） |
| `planned_audit`（X） | X 已完成：全部已落盤 | `not_executed` 步驟的預定事件、完成紀錄，以及 `status.d/<X>-completed`（X 未完成時）**必須不存在**；出現 → 列為證據衝突 |
| `retain_audit`（R） | — | R 的計畫檔、登錄紀錄、完成紀錄、接管事件、回復事件、狀態紀錄全部存在，sha256 等於 R 計畫中的值 |
| `shared_control` | 鎖檔存在；清單列出的既有 `index.d`、`status.d` 紀錄不變 | 同左；另有 `status.d/<X>-rolled_back` 或 `<X>-aborted_for_rollback`（只有一個，內容 `by: R`），以及 `status.d/<R>-completed` |
| `untouched` | 等於 `pre_sha256` | 等於 `pre_sha256` |
| 其他 | 標記存在，而且 `migrate_op_id` 等於 X | 標記不存在；沒有未完成的計畫 |

- 發現終態不一致的 R（§13.8）時，`migrate verify` 與 `operation list` 回報該不一致。

---

### 13. `migrate rollback`

#### 13.1 接管准入（新請求 `migrate rollback --op X [--allow-later-ops]`）

全部成立才建立 R：

| 條件 | 內容 |
|---|---|
| T1 | 狀態是 S_maint |
| T2 | X 存在、action 是 `migrate`、狀態是 `in_progress` 或 `completed`；而且 X 沒有被其他 R（不論是否完成）接管過 |
| T3 | 除了 X 之外，沒有其他未完成的計畫（有 → 拒絕，提示先續做那些計畫） |
| T4 | X 已完成 → 標記存在，而且 `migrate_op_id` 等於 X。X 未完成 → 標記不存在，或等於 X |
| T5 | 計算 `x_progress`（§13.5）。有證據衝突 → **拒絕**，不建立 R、不寫入任何檔案，產出證據衝突報告 |
| T6 | 計算 `later_ops_snapshot`。非空 → 依 §13.11 處理（預設拒絕） |
| T7 | **回復可行性**：依 §13.3 算出 R 的步驟和 `no_change`。以下任一成立 → **拒絕**：<br>• 清單內的路徑，內容既不是回復前（`planned_post_sha256`）、也不是回復目標（`pre_sha256` 或「不存在」）<br>• `untouched` 路徑和記錄值不符<br>• X 計畫的 `no_change` 業務檔和記錄值不符<br>拒絕時：不建立 R、不寫入任何檔案、不標記 X 終結、不刪除移轉標記；產出路徑報告，列出每個路徑的記錄值、目前值和所屬類別 |

- 「不寫入任何檔案」指不寫接管計畫、業務計畫和業務資料；鎖檔、診斷檔屬於執行器的控制面，照既有規則處理。路徑報告只輸出到標準輸出，不建立業務物件。
- T7 依**目前內容**判斷，不看歷史上是否碰過：路徑曾被後續操作修改、但目前已是合法的 pre 或 post，T7 接受。
- T7 拒絕後以相同請求重送：沒有計畫可續做，重新檢查並再次拒絕。

#### 13.2 R 建立後凍結的欄位（續做時都不重算）

`takeover_of: X`、`x_status_at_creation`、`x_progress`、`later_ops_snapshot`、R 自己的 `no_change[]`。

#### 13.3 R 建立計畫時依清單逐路徑決定

判斷依據是 R 建立當下、在 flock 中讀到的實際內容：

| 類別 | 目前內容 | R 的處理 |
|---|---|---|
| `restore` | 等於 `planned_post_sha256` | 成為步驟：before = `planned_post_sha256`，after = `pre_sha256`；先核對 backup 的 sha256 再以 backup 原子替換，替換後驗證等於 `pre_sha256` |
| `restore` | 已等於 `pre_sha256`（X 沒改到） | 列入 R 的 `no_change`，不成為步驟 |
| `restore` | 等於 `planned_post_sha256`，但 backup 缺失或 hash 不符 | 證據衝突 → T5 拒絕 |
| `remove` | 等於 `planned_post_sha256` | 成為步驟：before = `planned_post_sha256`，after = 不存在 |
| `remove` | 不存在（X 沒寫到） | 列入 R 的 `no_change`，不成為步驟 |
| 任一 | 其他內容 | **T7 拒絕**，不建立 R |
| `retain_audit` | — | **不動**，保留在原位置；只核對 `x_progress` 中已證實存在的部分 |
| `planned_audit` | — | **不動，也不補寫**；未執行步驟的預定事件、完成紀錄、狀態紀錄保持不存在 |
| `shared_control` | — | **不動**；固定鎖檔永不刪除；診斷檔、維護檔依各自規則；`index.d`、`status.d` 只新增 R 自己的紀錄 |
| `untouched` | — | **不動**；verify 與檢查時核對 |

- R 的每個步驟都滿足 before ≠ after；R 的計畫只有步驟和 `no_change` 兩類，**沒有**「無法回復」這一類（有就由 T7 拒絕）。
- 續做時，`no_change` 的路徑如果改變 → `external_change`，停止。
- rollback 自己寫入的計畫檔、登錄紀錄、完成紀錄、事件檔（含接管事件）、狀態紀錄屬於 R 的 `retain_audit`，R 完成時應全部存在，sha256 等於 R 計畫中的值。

#### 13.4 `classify_steps`（T5 與 V5 共用）

判定規則、合法尾端與不變式以第 4 章 §8.3 為準。本章只補充接管時的差異：

- T5 不因業務檔的 `external_change` 拒絕，改由 T7 逐路徑判斷；V5 遇到 `external_change` 一律停止。
- X 的計畫狀態是 `completed` 時，不跑尾端推導，直接要求：除了最後的 `completed` 狀態紀錄之外，每一步的完成紀錄都存在且相符；稽核物都等於 `expected_after`；業務檔被後續操作或外部修改屬於 `external_change`。
- 合法尾端：V5（X 自己續做）補寫它自己這一步的完成紀錄後繼續；T5（R 接管）只在 `x_progress` 凍結它的實際存在和 sha256（proof：`content_tail`），**不替 X 補寫**。

#### 13.5 `x_progress`

R 在 T5 對 X 執行 `classify_steps`，把結果寫入 R 的計畫檔，之後不再重算：

```text
x_progress:
  x_status_at_creation: in_progress | completed
  tail_step: <seq> | null                       # 合法尾端；最多一個
  steps[]: {seq, step_id, kind: business | event | control | index | status,
            status: done | not_executed | external_change,
            proof: progress | content_tail | completed_status | null,
            evidence: {path, sha256} | null}
  conflicts[]: {seq, step_id, path, reason}     # 不為空 → T5 拒絕，不建立 R
  no_change_check[]: {path, ok | changed}        # X 計畫的 no_change 核對（稽核物 changed → 列入 conflicts）
```

- `done` 的稽核物記下路徑和 sha256（必須等於計畫值）；合法尾端記為 `proof: content_tail`。
- `not_executed` 的步驟：輸出必須是 `before`；它的預定事件、完成紀錄必須不存在。
- 業務檔的 `external_change`：不列入 `conflicts`，但會讓 T7 拒絕，並列入路徑報告。
- X 已完成時：所有步驟都應是 `done`（proof：progress，最後一步是 `completed_status`）；所有預定稽核都應存在且相符；業務檔被後續操作改過 → `external_change`，依 §13.11 處理。
- X 只有計畫檔和登錄紀錄、清單還沒寫時：L 不存在，所有步驟都是 `not_executed`；規劃的路徑必須全部是 `before`；R 只執行 R1、R2 和 R 的狀態紀錄。

**不補寫原則**：

- R 不建立、不修改任何屬於 X 的事件檔、完成紀錄或 `completed` 狀態紀錄。
- R 只寫 X 的終態紀錄（`aborted_for_rollback` 或 `rolled_back`），內容標明 `by: R`。
- X 的取消只出現在 R 自己的接管事件中，標明「由 R 取消、未執行」；不會出現聲稱 X 某個步驟已成功的事件。
- cancel-run 同理：X 在 cancel 步驟之前中止 → 那個 run 從未被取消，也沒有 cancel 事件；X 的 cancel 步驟已完成 → 它的事件保留，對應的 run.yaml、APR 由 `restore` 回復。

#### 13.6 R 的步驟與固定群組

R 的每個步驟在計畫中帶一個建立時決定、之後不變的 `group`。檢查只依群組判斷。

| 群組 | 步驟 | 內容 |
|---|---|---|
| `takeover` | R1 | 只在 X 未完成時才有：以 link 建立 `status.d/<X>-aborted_for_rollback.yaml`（內容 `{by: R, at: R 的 clock}`） |
| `takeover` | R2 | 寫 R 的接管事件：`x_progress` 摘要，以及「未執行的 X 步驟清單：已取消、不補寫」 |
| `restore` | R3…Rk | 依清單執行 `restore`、`remove`（§13.3），移轉標記除外；對應的回復事件步驟也屬於這個群組 |
| — | （檢查 A） | 刪除標記前的檢查（唯讀，不是步驟） |
| `marker` | Rk+1 | 刪除移轉標記。只在 R 建立時標記存在、而且屬於 X 時才有；否則標記在 R 的 `no_change`，這個群組是空的 |
| — | （檢查 B） | 寫入終態前的檢查（唯讀，不是步驟） |
| `terminal` | Rt1 | 只在 X 已完成時才有：建立 `status.d/<X>-rolled_back.yaml` |
| `terminal` | Rt2（最後一步） | 建立 `status.d/<R>-completed.yaml`；沒有完成紀錄，本身就是完成的證據 |

- 群組順序固定是 `takeover` → `restore` → `marker` → `terminal`。
- 每一步都是不同的路徑，各自有 `expected_after`；除了 Rt2，每一步都有完成紀錄。
- 終態步驟只能以 link 建立一次；已存在的終態紀錄只能略過或補完成紀錄，不會重寫。

#### 13.7 檢查 A 與檢查 B

| 核對對象 | 檢查 A（刪除標記前） | 檢查 B（寫入第一個終態步驟前；終態階段續做時也執行） |
|---|---|---|
| `takeover` 群組 | 全部 after，完成紀錄都存在 | 同左 |
| `restore` 群組 | 全部 after，完成紀錄都存在 | 同左 |
| `marker` 群組（有標記步驟時） | **before**：標記仍等於 R 計畫的 `expected_before`，內容的 `migrate_op_id` 等於 X；沒有完成紀錄 | **after**：標記不存在，完成紀錄存在 |
| 標記在 R 的 `no_change`（沒有標記步驟） | 仍不存在 | 仍不存在 |
| `terminal` 群組 | **全部 before**：狀態紀錄都不存在 | 符合前綴規則：已寫的終態步驟是 after，之後的是 before；第一次執行檢查 B 時兩者都是 before |
| R 的 `no_change`、X 的 `no_change`、`untouched` | 等於記錄值 | 同左 |
| R 的計畫檔、登錄紀錄 | 等於計畫值、登錄值 | 同左 |
| X 的 `retain_audit` | 依 `x_progress`：`done` 的證據存在，sha256 等於凍結值 | 同左 |
| X 的 `planned_audit` 中 `not_executed` 的部分 | 不存在 | 同左 |
| `shared_control` | 鎖檔存在；清單列出的既有 `index.d`、`status.d` 紀錄不變 | 同左 |

- 到檢查點時，已執行的群組不會留下沒有完成紀錄的步驟（續做時 V5 已補寫合法尾端的完成紀錄）。
- `retain_audit` 與控制證據只要求「已經應該存在」的部分；R 自己的 `terminal` 在檢查 A 時必須不存在。
- 任一項不符 → **停止**，R 保持 `in_progress`，不執行下一步。標記不屬於 X → 停止，不刪除。
- 兩次檢查都是唯讀的，重複執行不改變任何檔案。

**續做時依實際階段決定要做哪一個檢查**（依 R 不可變的步驟清單、`group` 與 `classify_steps`，不重算計畫）：

| 階段 | 續做時的處理 |
|---|---|
| `takeover` 或 `restore` 還有未完成的步驟 | V5 依序完成 → 檢查 A → `marker` → 檢查 B → `terminal` |
| `takeover`、`restore` 都完成；`marker` 是 `not_executed`（標記仍在） | 檢查 A → 刪除標記 → 檢查 B → `terminal` |
| `marker` 是合法尾端（標記已不存在、沒有完成紀錄） | 補寫標記步驟的完成紀錄 → **不再執行檢查 A** → 檢查 B → `terminal` |
| `marker` 已是 `done`，`terminal` 全部 before | **不再執行檢查 A** → 檢查 B → `terminal` |
| `terminal` 已部分寫入（例如 Rt1 已寫、Rt2 未寫） | 不執行檢查 A；先以 V5 處理已寫的終態步驟（合法尾端補完成紀錄；已 `done` 略過；不重寫、不偽造）→ 依前綴規則**再執行一次檢查 B** → 寫入剩下的終態步驟 |
| `marker` 群組是空的（標記在 `no_change`） | 檢查 A（標記必須不存在）→ 檢查 B → `terminal`；`terminal` 已部分寫入時同上一列 |

已刪除的標記，**不會**重新套用「必須仍存在」的條件。

**檢查的保證範圍**：

- 兩次檢查只保證**檢查當下**讀到的值。flock 只排除經過執行器的寫入；對不取鎖的外部修改沒有跨多檔的原子保證；最後一次檢查之後才發生的人工修改擋不住。所以維護窗口與人工修復期間，必須依 W1 的人工協調停止其他外部寫入。
- 殘餘情況：檢查 B 通過、Rt1 已寫入之後，不取鎖的外部修改改動了已回復的路徑 → 續做時再執行的檢查 B 停止，R 不寫 Rt2；Rt1 已記錄的 X 終態不撤回；R 保持 `in_progress`，依 §13.9 修復後續做。
- 結論：T7 保證 R 建立時每個清單路徑都能回復；V5 與兩次檢查保證 R 執行期間被外部改動時停在 `in_progress`、不寫 Rt2；停在檢查 A 時標記保留。

#### 13.8 終態前綴與全域一致性核對（第 0 步）

- **前綴規則**：R 的 `terminal` 群組中，已存在的終態紀錄一定是從群組第一步開始連續存在。X 已完成時群組是 Rt1、Rt2；X 未完成時只有 Rt2。
- 所有寫入入口在登錄補齊之前執行的第 0 步，以第 4 章 §6.1 為準：發現終態不一致即拒絕本次寫入請求，不做任何持久寫入。
- 終態不一致的 R **不承認為已完成**。部分移轉的 R（只有 Rt2）、終態階段中止（Rt1 已寫、Rt2 未寫）都合法。

#### 13.9 R 停止後的受控處理

1. 系統回報停止的路徑、記錄值和目前值。
2. 由 Oscar 授權人工修復。可恢復成什麼內容依**可證實的進度**決定，不放寬 V5：

   | 路徑狀況 | 只能恢復成 | 原因 |
   |---|---|---|
   | 步驟**有**完成紀錄 | after | 恢復成 before 會被 V5 判成「已執行的輸出被還原」而停止 |
   | 步驟**沒有**完成紀錄（不論被破壞前是不是合法尾端） | before | 續做時重新執行，寫入同一份計畫值；內容已被破壞成 `other` 時不推定曾經執行過 |
   | `no_change`、`untouched` | 記錄值 | — |
   | 標記（檢查 A 停止時） | R 計畫的 `expected_before`（屬於 X） | — |

   判斷不出適用哪一列時，回報給人處理，不由系統推定。
3. 執行 `operation resume R`，續做時依 V5 判斷。
- 不允許重算 R 的計畫、改寫計畫檔，或以其他內容覆寫。
- R 停止期間，`maintenance end` 被拒絕（存在未完成計畫），維護窗口持續。
- R1 可能已把 X 標成 `aborted_for_rollback`，X 不能再續做；資料只能經由 R 完成回復，或由 Oscar 另外決定處理方式。
- **未授權的恢復成 after**（已明示的外部寫入限制，不是授權的修復方式）：沒有完成紀錄的步驟被改成 after：
  - 剛好是目前已執行前綴的下一步 → 被當成合法尾端；
  - 前面還有未執行的步驟 → L 被往後推，前面的步驟被判為衝突，停止。

#### 13.10 R 已保存、X 未標記，以及對 X 的請求

- R 已保存（登錄紀錄中同時有 X `in_progress`、R `in_progress`、`takeover_of: X`）、R1 還沒完成就中止：
  - **續做 R**（同請求重送或 `operation resume R`）：V3 排除自己和 X；R1 依 V5 判斷 `status.d/<X>-aborted_for_rollback.yaml`：不存在 → 寫入；存在、內容相符、沒有完成紀錄 → 合法尾端，補寫 R1 的完成紀錄；存在、內容不符 → 衝突，停止。這個檔只能以 link 建立一次，X 的終態紀錄只會有一筆。
  - **對 X 的請求**（同請求重送 X、`operation resume X`）→ 拒絕，提示續做 R；即使 R1 還沒執行也一樣。
  - **另一個 rollback 請求**（例如 `migrate rollback --op X --new-request`）→ T2 不成立，拒絕，提示續做 R。
  - **其他所有 op** → 拒絕（存在未完成計畫）。
- R 計畫檔已保存、登錄紀錄還沒寫就中止 → R 已建立（未登錄計畫）。下一個寫入請求先做登錄補齊，沿用 R 計畫中凍結的 `x_progress`、`later_ops_snapshot`、`clock`，不重算、**不重新走 T1～T6**；補齊後 R 的 `takeover_of` 生效。
- 目標計畫的狀態處理：
  - `aborted_for_rollback`、`rolled_back` → 拒絕；提示要重做就以 `--new-request` 建立新 op。
  - 被一份未完成的 R 指定為 `takeover_of`（不論 R 的第一步是否完成）→ 拒絕；提示續做 R。
- 之後重新安裝或重新移轉時不會誤判：標記已被移除 → 不算已移轉；X 已是終態 → 不算未完成、也不能續做；重新移轉必須用新的 op。

#### 13.11 回復點之後有後續操作

- **`later_ops_snapshot`**：登錄紀錄中 `plan_seq` 大於 X、而且 action 屬於業務寫入（§11.1 表最後一列與 `run cancel`）的計畫。排除：R 自己；控制類操作（`maintenance start|end`、其他 `migrate rollback`）；不寫計畫的唯讀指令。R 建立時計算一次，續做時不重算。
1. **預設拒絕**：`later_ops_snapshot` 非空時，`migrate rollback` 拒絕，並產出「後續操作報告」：
   - 列出每一份後續計畫的 op_id、action、targets，以及它新增或修改的路徑（來自該計畫的 steps）。
   - 每個項目分三類：
     - **會失去**：只能在新格式下存在的資料（新的 revision、`answer_revisions` 的新 rev、fulfillments、applicability、INCORPORATED 狀態等）；
     - **需要人工轉換**：可以用舊格式表達的業務內容（例如新的答案文字）；
     - **衝突**：後續操作修改過、本次清單也包含的路徑。
   - 報告只能盤點經由執行器計畫的寫入；外部手動修改、沒有接上執行器的來源（例如 admin-ui 後端直接寫入）無法盤點。這類修改落在清單內、`untouched` 或 `no_change` 路徑時，會以 T7 拒絕（R 建立前）或 V5／終態前檢查停止（R 執行中）的形式出現；落在清單以外的路徑時**不一定會被發現**，可能在回復後殘留。
2. **`--allow-later-ops`**：
   - 只解除 T6「有後續操作」的前置拒絕。
   - **不授權**覆寫內容衝突：後續操作改過清單內的路徑、`untouched` 或 `no_change` 路徑，而目前內容無法回復 → T7 拒絕整個接管，**不會部分回復**。
   - T7 以目前內容判斷：路徑曾被碰過但目前已是合法的 pre 或 post → 接受。
   - 後續操作新增的、清單以外的檔案會保留。
   - 不解除 T5 的證據衝突。
3. **需要人工轉換時**：不能沿用舊的 `pre_sha256` 宣稱完全復原；要以報告為依據另外建立新的快照保存資料，回復後再以新的操作計畫重建。這些步驟各自驗收，不屬於 rollback 本身的保證。
4. Oscar 依報告決定：(a) 不回復、向前修正（建議的預設）；或 (b) 依第 2、3 點處理。證據衝突（T5、V5）的處理也由 Oscar 決定，系統只回報、不自動放行。任何回復都需要 Oscar 明確授權。

---

### 14. 故障點（每個故障點都驗收兩種入口：同請求重送、`operation resume`）

| 故障點 | 中止時的狀態 | 續做結果（預期） | 續做期間其他請求（預期） | 對應 AC |
|---|---|---|---|---|
| **FP-M0** 計畫已建立，清單還沒寫 | S_maint、無標記 | 續做 → 從清單步驟開始；或接管 rollback | 只允許接管 rollback | AC-07-90、AC-09-75 |
| **FP-M1** 清單和 backup 已完成，還沒有業務寫入 | 同上 | 續做；或接管 | 同上 | AC-09-71 |
| **FP-M2** 部分業務步驟和事件已寫（例如中止在 sidecar） | 同上 | 續做（已完成步驟略過、事件不重寫）；或接管 | 同上 | AC-09-57、72 |
| **FP-M3** 標記已寫，第一次 render 還沒執行 | S_maint、標記等於 X | 續做：標記略過 → render → 完成 | 同上 | AC-07-90 |
| **FP-M4** render 失敗 | 同上 | 計畫保持 `in_progress`；續做時重建 render → 完成 | 同上 | AC-07-91 |
| **FP-M5** render 全部完成，`status.d/<X>-completed` 還沒寫 | 同上 | 只建立狀態紀錄 | 同上 | AC-07-90 |
| **FP-M6** 已完成步驟的證據被刪除或竄改後續做 X | 同上 | V5 停止，**不重寫**事件 | 同上 | AC-09-76 |
| **FP-R0** R 已建立，R1 還沒執行 | S_maint、標記等於 X 或不存在 | 續做 R：`status.d/<X>-aborted_for_rollback` 只建立一次 → 完成 | X 的續做拒絕；第二個 rollback 拒絕；其他 op 拒絕 | AC-07-92 |
| **FP-R1** X 已標記，`restore`／`remove` 執行到一半 | 同上 | 續做 R（不重算 `x_progress`、`later_ops`）→ 完成 | 同上 | AC-09-58、AC-07-93 |
| **FP-R2** 標記已移除，`terminal` 全部 before（標記步驟可能是合法尾端或已有完成紀錄） | S_maint、無標記 | 續做 R：`takeover`、`restore` 略過；不再執行檢查 A；檢查 B → 寫入 `terminal` → 完成 | 同上 | AC-07-93、AC-09-84 |
| **FP-R3** R 完成之後，續做 X 或重送 X | S_maint、無標記 | 拒絕（X 已終結） | — | AC-09-63 |
| **FP-R4** R 執行期間，尚未處理的步驟路徑、`no_change` 或 `untouched` 路徑被外部改動 | S_maint；標記依停止點而定 | V5、檢查 A 或檢查 B 停止，R 保持 `in_progress`；不寫終態；停在檢查 A 時標記保留。依 §13.9 修復後續做完成 | 同 FP-R0 | AC-09-83 |
| **FP-R5** 終態階段：檢查 B 已通過，`terminal` 還沒寫，或已部分寫入（Rt1 是合法尾端或已有完成紀錄，Rt2 未寫） | S_maint、無標記 | 續做 R：不執行檢查 A；V5 處理已寫的終態步驟（不重寫）→ 依前綴規則再執行一次檢查 B → 寫入剩下的終態步驟 → 完成 | 同上 | AC-09-85 |

所有計畫共通的 FP-P1（計畫已保存、登錄未寫）、FP-W（輸出已落盤、完成紀錄未落盤）也適用於 migrate 與 rollback（AC-09-78、79、80）；定義見執行器章。

---

### 15. 部署與回復停點

#### 15.1 部署與移轉（M0～M5、W1～W2）

| 停點 | 內容 | 需要的確認 |
|---|---|---|
| **M0** | MR 經程式碼審查通過；還沒 merge | Oscar 觸發 |
| **M1 預演**（merge 之前） | 在獨立 worktree（分支程式）上執行；來源資料唯讀、另建可寫的隔離工作複本、使用獨立的 `QAOS_ROOT`；**絕不對原資料執行**。<br>**第一份工作複本**依序：1. `maintenance start` 2. `migrate`（依當天模式）3. `migrate verify` 4. `migrate rollback` 5. `migrate verify --rolled-back` 6. `migrate --new-request`（確認可以重做）7. `migrate verify` 8. `maintenance end`。<br>**第二份工作複本**以故障注入演練：FP-M2（中途中止 → 直接 rollback）、FP-M3（標記已寫、render 未完成 → 續做）、FP-R0（R 已保存、X 未標記 → 續做 R）、FP-W（輸出已落盤、完成紀錄未落盤 → 直接 rollback，以及續做）、FP-P1（計畫已保存、未登錄 → 登錄補齊後續做） | Oscar 確認報告 |
| **W1 進入維護窗口** | 人工協調：admin-ui 後端停止寫入，其他 session 不執行 QAOS 寫入。這段時間舊程式還不認得維護模式，只能靠人工協調。先以資料 commit 記錄目前狀態，作為回復點（依當下授權）。之後、M2 之前（仍是舊程式），以舊程式對 `schema.infer` 能推斷 schema 的全部 yaml 逐檔執行 `bin/qaos validate`（`tools/legacy_validate_snapshot.py snapshot`），作為 R5 的 W1 對照（附錄 A 5-16）：保存逐檔結果（路徑、推斷的 schema、退出碼、輸出全文）、逐檔 sha256、資料 commit、舊程式 SHA 與工具版本；未追蹤的業務檔要納入資料 commit 或另存快照 | Oscar 宣告開始；admin-ui 後端的寫入方式需事先確認 |
| **M2 merge 與部署** | merge；本機 `main` 的 working tree 切換到新程式；立刻執行 `maintenance start` | Oscar merge |
| **M3 移轉** | 重新讀取業務現況（RUNNING／WAITING_HUMAN 的 run、PENDING APR）→ `migrate --acknowledge-idle\|--cancel-run …` → `migrate verify` | Oscar 明確授權（含 RUNNING run 的處理方式） |
| **M4 驗證** | 標記存在、第一次 render 成功；原本存在的 `audit.log` 開頭逐位元等於移轉前的原檔；`untouched` 全部吻合；抽查 sidecar；pytest、`validate_phase1` 通過 | 回報 |
| **W2 結束維護窗口** | `maintenance end`；通知 admin-ui 恢復 | Oscar 宣告 |
| **M5 資料 commit** | 記錄移轉結果 | Oscar 當下明確授權 |

#### 15.2 程式 revert 與資料回復（R0～R6）

| 停點 | 內容 | 執行時的程式 |
|---|---|---|
| R0 | 決定回復並授權（先看後續操作報告與 T5 證據報告） | — |
| R1 | 進入維護窗口（人工協調，同 W1）；`maintenance start` | 新程式 |
| R2 | `migrate rollback --op X`（中止時依 §13 續做 R） | 新程式（舊程式沒有回復功能，所以資料先回復） |
| R3 | `migrate verify --rolled-back` 全部通過 | 新程式 |
| R4 | 程式 revert：在 `main` 上 revert MR 的 merge commit（以指定方式）；本機 working tree 回到舊程式 | — |
| R5 | 以**舊程式**驗證：`validate_phase1`、pytest；對全部業務資料執行舊的 `bin/qaos validate`，以 baseline 比對判定（附錄 A 5-16）：W1 對照中有的檔案，逐檔結果與 W1 對照（舊程式＋W1 的資料）相同；W1 對照中沒有、且能對應到 X、R 或控制類操作的保留事件檔，不在舊 validate 的判定範圍；確認 `restore` 類全部等於 `pre_sha256`、`remove` 類全部不存在 | 舊程式 |
| R6 | 移除 `locks/maintenance.yaml`（舊程式不認得它）；**鎖檔、診斷檔、登錄與狀態紀錄、`retain_audit` 都保留**；結束維護窗口並通知 admin-ui | — |

- 資料回復（R2、R3）一定在程式 revert（R4）之前；R4 之後不再執行新程式的寫入指令。
- R6 刪除維護檔不經過 `maintenance end`（R4 之後舊程式沒有這個指令），是人工步驟，需授權並記錄在回復報告中。
- 之後如果重新部署新程式：終態紀錄可避免誤判；重新移轉要用新 op；新程式第一次啟動、執行 `maintenance start` 前，要確認登錄紀錄中沒有未完成計畫。

---

### 16. 涉及的 schema、模組、CLI

- **schema**：
  - `schemas/spec/requirements-file.schema.json`（檢視，配合 §3 第 5 點「移轉不修改」與索引分離）；
  - 新增 `schemas/spec/requirements-revision.schema.json`、`schemas/spec/binding.schema.json`（sidecar）；
  - `schemas/workflow/workflow-run.schema.json`（`requirement_model_revision`）；
  - `schemas/testcase/testcase-version.schema.json`（`requirement_model_revision`）；
  - `schemas/artifact/change-impact-report.schema.json`（`from_rm_revision`、`to_rm_revision`、`pin_groups`、`pin_group_index`）、`change-impact-input.schema.json`（`from_revision`、`reason`）；
  - 新增 `schemas/workflow/migration-manifest.schema.json`（含 `planned_audit`）；
  - 操作計畫 schema 增加 rollback 計畫的 `takeover_of`、`x_progress`、`later_ops_snapshot`、`group`、`no_change`。
- **模組**：`engine.py`（`_persist_requirements`、`_skip`、綁定、讀取點、`cancel`、同版本 CIA）、`gates.py`（`g_impact` 改寫、`g_design`、`g_risk`）、`refs.py`、`store.py`（`save_requirements`、revision 讀取）、`tc_ops.py`、`req_export.py`、`final_export.py`、新增 `tools/qaos/migrate.py`、`operation.py`（執行器）、`cli.py`。
- **workflow**：`workflows/spec-change-impact.yaml`、`spec-to-testcase.yaml`（修正 skip_if 的文字，使其和程式一致）、`manual-test-to-regression.yaml`（spec 必要）。
- **agent 契約**：`agents/change-impact-analyst.yaml` 與對應指示檔（pin_groups）。
- **CLI**：
  - `migrate [--acknowledge-idle <run>]… [--cancel-run <run>]… [--new-request]`
  - `migrate verify [--rolled-back]`
  - `migrate rollback --op <X> [--allow-later-ops] [--new-request]`
  - `maintenance start|end`、`operation list`、`operation resume <op>`（執行器章）
  - `run cancel <run_id>`
  - `run new spec-change-impact … --input from_revision=R<NNN> --input reason=…`
  - `req accept-declaration <spec_id@ver> --rev R<NNN> --reason`
  - 第二批：`spec outdated`、`req verify`

---

### 17. 驗收 AC（全部是預期結果）

#### 17.1 通則

- fixture 的初始資料一律經測試 root 的正式流程建立；只有標明「竄改」或「故障注入」的才在流程後故意修改檔案。
- 所有 `migrate` 案例都先以 `maintenance start` 進入 S_maint。
- 每個停止案例先斷言各群組的狀態與完成紀錄，再斷言**實際停止的位置**（V5、檢查 A、檢查 B 或 T7），不能只看最後傳回失敗。
- 要驗收某個檢查點時，故障注入要選在那個檢查點才會被發現的路徑（例如 `untouched`），並先斷言前面的 V5 已通過；不為了讓案例到達檢查點而放寬 V5。
- 人工修復的子例都標示為「測試中模擬的授權處理」，不是一般業務流程的前提。
- 成功路徑一律以正式操作和故障注入建立，不手改業務資料。

#### 17.2 revision、綁定、閉包、過時判定、CIA、cancel、移轉基本行為（AC-09-1～50、54）

- **AC-09-1**：同一 spec 版本重新分析。預期：產生 R(n+1)，R(n) 位元不變。
- **AC-09-2**：舊 run 綁定 R(n)，新 run 重新分析產生 R(n+1)。預期：新 run 綁 R(n+1)；舊 run 恢復時讀到的是 R(n)。
- **AC-09-3**（真實結構的舊 run）：以 RUN-20261002-001 的 run.yaml 唯讀複本（WAITING_HUMAN、沒有 revision 欄位）為 fixture → 移轉（建立 R000、sidecar）→ 另一個 run 重新分析 v0.6，產生 R001 → 恢復舊 run（核准 APR-0192 的複本）。預期：舊 run 的 T0 重開時，派發包裡的前版 RM 是 R000，不是 R001。
- **AC-09-4**：移轉前後比較。預期：所有 run.yaml 的 hash 不變（`--cancel-run` 指定的 run 除外，它屬於 `restore`）；R000 的 hash 等於原 `requirements.yaml`；`requirements.yaml` 本身不變。
- **AC-09-5**：沒有移轉標記時，嘗試持久化需求、建立新 run、恢復 run。預期：全部拒絕（S_pre：「尚未移轉」；S_maint：「維護中」）。
- **AC-09-6**：有 RUNNING 的 run，且沒有以 `--acknowledge-idle`、`--cancel-run` 指定、也沒有事先 `run cancel`，執行移轉。預期：拒絕，不寫任何檔案（連計畫都不寫）。
- **AC-09-7**：只補宣告 references（內容不變）。預期：`declaration_changed`，`_skip` 不跳過；`accept-declaration` 之後跳過，新 revision 記錄 `accepted_without_analysis: true` 與 `accepted_diff`。
- **AC-09-8**：只匯入參考文件的新版本。預期：`newer_available`，pins 不變，不擋 `_skip`。
- **AC-09-9**：A→B（normative），B 在同一版本改宣告 C。預期：A 判為 `declaration_changed`。
- **AC-09-10**：A↔B 循環；另以 51 個節點的閉包。預期：循環時閉包終止、沒有重複節點；51 個節點 → 拒絕。
- **AC-09-11**：同時有 DRAFT 和 ACTIVE 需求的 legacy RM（例如 SITELIST v0.6 的 022／023）。預期：不跳過，即使是 legacy。
- **AC-09-12**：revision 引用的 CLR 答案變成 rev 2。預期：`decision_revised`，不跳過。
- **AC-09-13**：移轉後的 TC sidecar。預期：綁定該版本 spec_version 的 R000，並帶 `legacy_binding: true`。
- **AC-09-14**：AC-09-1～13 的所有測試。預期：既有 run.yaml、R(n)、TC 版本檔的 hash 都不變（新增的 sidecar 不算修改）。
- **AC-09-15**（同版本 CIA）：PLATFORMRULE 0.2 的 fixture，R000 → R001（spec 內容相同、裁決改變）。預期：CIR 列出受影響的需求和 TC；`g_impact` 讀的是 R000 和 R001，不是檢視。
- **AC-09-16**：同版本但沒有 `from_revision` 或 `reason`；另一例 `reason` 和判定函式結果不符。預期：兩例 `run new` 都拒絕。
- **AC-09-17**：`run cancel`。預期：run 為 CANCELLED；它**所有** PENDING 的核准單為 CANCELLED（不只 `waiting_on_approval_id`）；revision 和 sidecar 保留；之後的新 run（0.4→0.7）不會綁到 0.6 的任何 revision。
- **AC-09-18**：RESOLVE_AMBIGUITY 被 reject。預期：run 沒有結束，T0 以 iteration+1 重開（回歸測試，確認現行行為不變）。
- **AC-09-19**：RESOLVE_AMBIGUITY 被 approve。預期：不再自動 apply CLR（和 FIX-10 一起測）。
- **AC-09-20**：既有 WAITING_HUMAN 的 testcase-revision run（fixture）→ 移轉 → 恢復。預期：G-DESIGN 讀到的是 sidecar 的 R000。
- **AC-09-21**：新的 testcase-revision run。預期：`new_run` 時綁定最新 revision；派發包的 RMPin 和它相同。
- **AC-09-22**：testcase-revision 的目標版本有 `declaration_changed`。預期：`run new` 拒絕。
- **AC-09-23**：manual record 沒有 `spec_hint`、inputs 也沒有 spec，執行 `run new manual-test-to-regression`。預期：拒絕；`runs/` 沒有新目錄；計數器不前進。
- **AC-09-24**：regression-generation。預期：移轉前後行為不變；不產生 sidecar。
- **AC-09-25**：reference_only 拒絕點。預期：§4.4 的 7 個入口各一個測試，全部拒絕。
- **AC-09-26**：移轉在寫了一半 sidecar 時中止 → 以同請求重送或 `operation resume` 續做。預期：續做完成，最終 sidecar 完整；標記寫入之前，業務寫入一直被拒絕。
- **AC-09-27**：已存在、綁定 R000 的舊 manual run，移轉後恢復。預期：RR、Validator 的派發包使用同一個 R000。
- **AC-09-28**（連續兩輪）：R000→R001：TC-A affected，升版綁 R001；TC-B unaffected，留在 R000。之後 R001→R002 影響 TC-B。預期：CIR 必須有兩組（R000：TC-B；R001：TC-A）；缺少 TC-B 的判定 → `g_impact` FAIL。
- **AC-09-29**：AC-09-28 中 TC-B 那組。預期：requirement_diff 是 R000→R002，涵蓋 R001 的變更。
- **AC-09-30**：legacy 的 TC（sidecar R000）和新 TC（版本檔內 pin）混合。預期：正確分組。
- **AC-09-31**（跨版本）：DAILYREPORT 現況的 fixture（0.1 的 48 條、0.2 的 48 條）做 0.2→0.3。預期：候選必須是 96 條、分兩組；只判 0.2 的 48 條 → FAIL。
- **AC-09-32**：`run cancel` 重送兩次。預期：核准單只轉換一次，audit 不重複。
- **AC-09-33**：`manual new`（含 `spec_hint`，指向測試 root 中已分析的 spec）→ `run new manual-test-to-regression --input manual_record_id=…` → 綁定最新 revision → `dispatch T1` → 提交 Draft（`decision_refs`、SourceRef）→ gate → Validator → ACTIVATE approve。預期：正式 TC 建立，版本檔帶 `requirement_model_revision`。
- **AC-09-34**：manual 的 `spec_hint` 指向 reference_only 的版本。預期：`run new` 拒絕。
- **AC-09-35**：候選 A（pin R001）、B（pin R000）；`testcase_impact` 列 A 和 B，B 宣稱 unaffected；`pin_groups` 只列 A 那一組。預期：G2 FAIL。
- **AC-09-36**：B 同時出現在兩組。預期：G2 FAIL。
- **AC-09-37**：B 被放進 R001 組（它的 pin 是 R000）。預期：G4 FAIL。
- **AC-09-38**：組中有一個不在候選內的 TC-Z。預期：G2 FAIL。
- **AC-09-39**：`testcase_impact` 中有不在候選內的 TC-Z。預期：G5 FAIL。
- **AC-09-40**：有空組；另一例兩組的 `from_pin` 相同。預期：G1 或 G3 FAIL。
- **AC-09-41**：B 在 R000 組，但它的 `testcase_impact` 的 `pin_group_index` 指向 R001 組。預期：G6 FAIL。
- **AC-09-42**：RUNNING 的 run 沒有被指定處理方式 → 移轉；之後指定 `--acknowledge-idle` 再移轉。預期：前者拒絕；後者寫入 sidecar，run.yaml 不變。
- **AC-09-43**：沒有移轉標記、RUN-20260914-001 為 RUNNING，執行 `migrate --acknowledge-idle RUN-20260914-001`。預期：移轉完成；該 run 的 sidecar 綁 DAILYREPORT 0.1 的 R000；run.yaml 不變。
- **AC-09-44**：同上情境，執行 `migrate --cancel-run RUN-20260914-001`。預期：同一個操作中，該 run 改成 CANCELLED（沒有 PENDING 的 APR 需要處理）→ 寫 sidecar → 標記。
- **AC-09-45**：在 S_pre 先 `run cancel RUN-20260914-001`，再（進入維護後）`migrate`。預期：兩個操作都完成。
- **AC-09-46**：同上情境，`migrate` 不指定任何處理方式。預期：拒絕，沒有任何寫入。
- **AC-09-47**：AC-09-44 在 cancel 步驟之後、sidecar 之前中止 → 重送同一個 migrate。預期：同一 op_id 續做；cancel 步驟已完成 → 略過；寫入 sidecar 和標記。
- **AC-09-48**：移轉前有一份未完成的 `run cancel` 計畫。預期：`maintenance start`、`migrate` 都被拒絕並提示 resume；`operation resume` 完成該計畫後，`maintenance start` → `migrate` 完成。
- **AC-09-49**：移轉前執行 `answer CLR-…`。預期：拒絕：「尚未移轉」。
- **AC-09-50**：有 PENDING APR 的 RUNNING run（fixture），`migrate --cancel-run`。預期：所有 PENDING APR 都改成 CANCELLED。
- **AC-09-54**：移轉前（沒有移轉標記）以 `operation resume` 續做各種未完成計畫。預期：只有 `resume_states` 包含目前狀態的計畫可以續做（S_pre 的 `run cancel`；S_maint 的 `migrate`、`migrate rollback`；維護控制操作依其 `resume_states`）；業務寫入計畫一律拒絕續做（V4）。

#### 17.3 移轉清單、verify、rollback、稽核證據、回復可行性、終態、目標宣告變動與 legacy pin（AC-09-55～91）

- **AC-09-55**：acknowledge-idle；原本有 `audit.log`、有 CLR render → 移轉 → rollback。預期：
  - `restore`：CLR yaml、CLR md、audit.log 都回到 `pre_sha256`；
  - `remove`：R000、revision 索引、sidecar、legacy log、標記都不存在；
  - 檢查 A 在標記仍存在、`terminal` 全部 before 時通過；檢查 B 在標記刪除後、`terminal` 全部 before 時通過（沒有外部修改時兩次檢查都不擋正常流程）；
  - X 的 `retain_audit` 全部存在、相符；`shared_control` 保留；
  - run.yaml、APR 在 `untouched` 中，而且沒有變；
  - `verify --rolled-back` 通過。
- **AC-09-56**：cancel-run（fixture 有 PENDING APR）→ rollback。預期：除了 AC-09-55 的結果（含檢查 A、B 都通過），另外 run.yaml、APR yaml、APR render 都回到 `pre_sha256`；cancel 的事件檔屬於已證實的 `retain_audit`，保留。
- **AC-09-57**：migrate 中止在寫 sidecar 時（FP-M2）→ 直接 `migrate rollback --op X`（不續做 X）。預期：
  - 接管成功，X 被標記 `aborted_for_rollback`；
  - `x_progress` 正確區分已完成和未執行的步驟；
  - R 的步驟只包含已寫的 `remove` 和已修改的 `restore`；未寫的 `remove`、未修改的 `restore` 列入 R 的 `no_change`；
  - 已落盤的事件保留，未執行的預定事件不存在；
  - `verify --rolled-back` 通過；
  - 之後同 op 重送 X，被拒絕。
- **AC-09-58**：rollback R 執行到一半中止（FP-R1；R 的計畫中同時有步驟和 `no_change` 路徑）→ 同 op 重送 R。預期：依同計畫續做；不重算 `later_ops`、`x_progress`、`no_change`；`no_change` 路徑不影響 L 的推導，已執行的步驟正確略過；R 不把自己列為後續操作；結果和 AC-09-55 相同。
- **AC-09-59**：移轉後以故障注入把清單內某張 CLR 改成既不是移轉前、也不是移轉後的內容 → `migrate rollback --op X`。預期：
  - T7 拒絕：不建立 R、不寫入任何檔案；
  - X 的狀態不變、移轉標記仍在、仍在維護中；
  - 路徑報告列出該 CLR 的記錄值和目前值；
  - 相同請求重送仍被拒絕（沒有計畫可續做，T7 重新檢查）；
  - 模擬經授權的人工修復：該 CLR 恢復成移轉後的內容 → 相同請求重送 → 建立 R、完成，`verify --rolled-back` 通過。
- **AC-09-60**：移轉後有一次正式的 `answer`（後續操作）→ rollback。預期：預設拒絕；報告列出會失去、需要人工轉換、衝突的項目。
- **AC-09-61**：同 AC-09-60，加 `--allow-later-ops`，分兩例：① 後續的 `answer` 改過清單內的 CLR；② 後續操作只寫清單以外的路徑。預期：① T6 放行但 T7 拒絕；不建立 R、不寫入；沒有部分回復，也沒有任何終態紀錄。② 建立 R 並完成；清單路徑全部回復；後續操作新增的檔案保留；`verify --rolled-back` 通過。
- **AC-09-62**：清單以外、和移轉同時期新增的合法檔案。預期：不受回復影響。
- **AC-09-63**：rollback 完成後重新移轉。預期：
  - ① 以相同參數、不加 `--new-request` 執行 `migrate` → 得到 X → X 是 `rolled_back` → 拒絕，提示用 `--new-request`；
  - ② `operation resume X` → 拒絕；
  - ③ `migrate --new-request` → 產生新 op Y；不會誤判已移轉；清單依當時的 pre-state 重新產生；Y 的清單不包含 X 的稽核物；X 的稽核物保持不變；
  - `migrate verify` 通過。
- **AC-09-64**：R0～R6 完整順序（測試中以舊版程式的 checkout 執行 R5）。前提：AC-09-55～59、61、71～85 先通過。預期：舊程式的 `validate_phase1`、pytest 都通過；舊的 `bin/qaos validate` 依附錄 A 5-16 以 baseline 比對——W1 對照中有的檔案，逐檔結果與 W1 對照（舊程式＋W1 的資料）相同；W1 對照中沒有、且能對應到 X、R 或控制類操作的保留事件檔，不在舊 validate 的判定範圍（W1 對照中既有的失敗不算新失敗）；R6 之後鎖檔仍存在，但舊程式不讀取它。
- **AC-09-65**：不在維護中執行 rollback。預期：拒絕（S_pre 或 S_post）。
- **AC-09-66**：某個 run 原本沒有 `audit.log` → 移轉（render 新建）→ rollback。預期：該 `audit.log` 屬於 `remove`，回復後不存在；legacy 狀態在標記中記為 `absent`。
- **AC-09-67**：CLR 原本沒有 `.md` render → 移轉時產生 → rollback。預期：該 `.md` 屬於 `remove`，回復後不存在。
- **AC-09-68**：控制檔已經存在（執行器、`maintenance start` 先建立了鎖檔、診斷檔、登錄紀錄和狀態紀錄）→ 移轉 → rollback。預期：鎖檔、診斷檔在 `shared_control`，不刪除、不恢復；移轉前已存在的 `index.d`、`status.d` 紀錄在 `untouched`，全部不變。
- **AC-09-69**：控制檔第一次被建立（全新的工作複本）→ 移轉 → rollback。預期：同 AC-09-68；鎖檔仍存在。
- **AC-09-70**（正式流程）：1. 以正式流程完成 `maintenance start` → `migrate` X → `maintenance end`，進入 S_post；2. 執行一次正式的業務寫入（例如 `answer`），以故障注入讓它中止，留下未完成計畫 B；3. 在 S_post 執行 `maintenance start`。預期：
  - 第 3 步被拒絕，訊息提示 `operation resume B`，沒有建立任何檔案；
  - 在 S_post 執行 `operation resume B` → 完成；
  - 再執行 `maintenance start` → 成功；
  - `migrate rollback --op X` → 進入 T6：B 是後續操作 → 預設拒絕（同 AC-09-60），**不會**以「還有未完成計畫」拒絕。
- **AC-09-70-def**（防禦性測試，不屬於正式流程）：以測試專用的故障注入跳過 `maintenance start` 的未完成計畫檢查，造出「S_maint 中存在未完成的業務計畫 B」。預期：`migrate rollback --op X` → T3 拒絕；`operation resume B` → V4 拒絕（業務計畫的 `resume_states` 只有 S_post）；`maintenance end` → 拒絕；系統回報不合法狀態、不自動放行；這個 AC 只證明防禦檢查存在，不作為正式流程可達性的證據；故障注入程式只存在於測試中。
- **AC-09-71**：X 中止在清單和 backup 完成之後、第一個業務步驟之前（FP-M1）→ rollback。預期：
  - `x_progress`：只有清單和 backup 的步驟是 `done`；
  - `restore` 全部還在 pre、`remove` 全部不存在（都在 R 的 `no_change`）；
  - 所有 `planned_audit` 都不存在，而且沒有被補寫；
  - 計畫檔、登錄紀錄、清單、backup 及它們的完成紀錄保留，sha256 相符；
  - R 的接管事件列出所有未執行的步驟；
  - `verify --rolled-back` 通過。
- **AC-09-72**：X 中止在部分業務步驟和事件已寫之後（例如 CLR rev 0 和事件已寫，sidecar 和標記還沒寫）→ rollback。預期：
  - 已寫的 CLR 由 `restore` 回復；
  - 已寫的事件保留，身分和 sha256 相符；
  - sidecar、標記、render、完成相關的預定事件不存在，而且沒有被補寫；
  - cancel-run 模式下，如果 cancel 步驟還沒執行，就沒有 cancel 事件；
  - `verify --rolled-back` 通過。
- **AC-09-73**：同 AC-09-72，rollback 之前做以下任一刪除（各一例）：① 刪除一個有完成紀錄的 X 事件；② 刪除尾端之前某一步的完成紀錄（它的輸出仍在）。預期：T5 拒絕，不建立 R、不寫入任何檔案；報告列出該步驟、路徑和原因；X 仍是 `in_progress`。
- **AC-09-74**：同 AC-09-72，但把一個 X 事件改內容（sha256 不等於計畫值），分三例：① 有完成紀錄的事件；② 合法尾端的事件（沒有完成紀錄）；③ 在 R 完成之後才改內容。預期：①② 同 AC-09-73（事件內容由計畫固定，任何不符都是衝突，不因沒有完成紀錄而放行）；③ `verify --rolled-back` 失敗，並列出該證據衝突。
- **AC-09-75**：X 中止在計畫已建立並登錄、清單還沒寫（FP-M0）→ rollback。預期：R 只執行 R1、R2 和 R 的狀態紀錄；verify 確認 X 計畫中所有規劃的路徑都等於 `expected_before`；不存在任何 X 事件。
- **AC-09-76**：同 AC-09-73、74 的竄改狀態，但改成續做 X（同請求重送和 `operation resume X` 各一例）。預期：V5 停止，不重寫被刪除的事件、完成紀錄；回報證據衝突；其他檔案不變。
- **AC-09-77**：AC-09-55、57 和 63 之後執行 `audit render`，以及 run、CLR 的 `show`。預期：render 中屬於 X 的事件，標明所屬 op 的終態（`rolled_back` 或 `aborted_for_rollback`，by R）；不把 X 的 cancel、CLR rev 0 等事件呈現成目前的業務狀態；run、CLR 的目前狀態以回復後的業務檔為準；保留的稽核不會被刪除。
- **AC-09-78**：X 在某一步「輸出已落盤、完成紀錄還沒寫」時中止（FP-W），分三例：① 業務檔（例如 CLR rev 0）；② 事件檔；③ 業務步驟已有完成紀錄、它的事件步驟還沒執行。每例分別執行：(a) 直接 `migrate rollback --op X`；(b) 同請求重送 X；(c) `operation resume X`。預期：
  - (a)：T5 不拒絕；①② 該步凍結為 `content_tail`，R 不替 X 補寫完成紀錄；③ 的事件是 `not_executed`，不存在、不被補寫；`verify --rolled-back` 通過；
  - (b)(c)：X 補寫該步自己的完成紀錄（只有一個），不重寫輸出，繼續到完成；
  - 對照：在同一故障點另外刪除一個已有完成紀錄的事件 → 仍然拒絕（同 AC-09-73）。
- **AC-09-79**：R 在某一步「輸出已落盤、完成紀錄還沒寫」時中止，分三例：① R1 的 `status.d/<X>-aborted_for_rollback`；② 某個 `restore`；③ 移轉標記的 `remove`。每例都以同請求重送 R、`operation resume R` 續做；R 的計畫中有 `no_change` 路徑。預期：
  - R 補寫自己的完成紀錄，不重寫輸出，然後完成；
  - ③：續做時不再執行檢查 A（標記已不存在），直接執行檢查 B（`terminal` 全部 before）；
  - `no_change` 路徑不被選為 L；
  - `status.d/<X>-aborted_for_rollback` 只有一個；其他 `status.d`、`index.d` 紀錄不被視為衝突；
  - 竄改既有紀錄的內容 → 停止。
- **AC-09-80**：R 的計畫檔已保存、登錄紀錄還沒寫（FP-P1）。之後分別：① 同請求重送 R；② 重送 X；③ `operation resume X`；④ 另一個 `migrate rollback --op X --new-request`。預期：
  - 任何請求都先做登錄補齊：R 被登錄，R 計畫檔的 sha256 不變，`x_progress`、`later_ops_snapshot`、`clock` 都沿用；
  - ① 續做 R，完成；②③ 被拒絕，提示續做 R；④ 被拒絕（T2：X 已被 R 接管）。
- **AC-09-81**：以正式流程建立「部分移轉」：X 在部分業務步驟完成之後中止，使 R 的清單中同時有已寫的 `remove`、未寫的 `remove`（例如 sidecar 還沒建立）、已修改的 `restore`、還沒修改的 `restore`。然後分別在以下各點中止 R：① FP-R0（R 已建立，R1 還沒執行）；② R1 的輸出已落盤、完成紀錄未落盤（FP-W）；③ 部分 `restore`／`remove` 已執行（FP-R1）。每點都以同請求重送 R、`operation resume R` 續做。預期：
  - R 的計畫：未寫的 `remove`、未修改的 `restore` 在 `no_change`，不是步驟；
  - ①：L 不存在，所有步驟依序執行；R1、R2 不被判為衝突；
  - ②：R1 是合法尾端，補寫完成紀錄；
  - ③：已執行的步驟略過，其餘繼續；
  - 三點都能完成，`verify --rolled-back` 通過；所有狀態都由正式流程和故障注入建立，不手改業務資料。
- **AC-09-82**：以正式流程完成 X，使 R 的計畫會同時有一般步驟與 `no_change` 路徑（例如 X 沒改到的 `restore`）。然後以故障注入，在以下其中一處造成無法回復的內容（各一例）：① 清單內的 `restore` 路徑；② 清單內的 `remove` 路徑；③ `untouched` 路徑；④ X 的 `no_change` 業務檔。再執行 `migrate rollback --op X`。預期：
  - 四例都 T7 拒絕，報告列出路徑和類別；
  - 沒有建立 R；沒有 `status.d/<X>-rolled_back`、`<X>-aborted_for_rollback` 或任何 R 的紀錄；
  - 移轉標記仍在，衝突檔不被寫入；
  - 重送和 `operation resume` 都不能把它當成功而略過（沒有 R 可續做，重送會重新檢查並再次拒絕）；
  - 不能以無衝突的 AC-09-81 取代這個 AC。
- **AC-09-83**（FP-R4）：R 建立之後、執行期間，以故障注入在以下時點造成外部改動（各一例）：① 尚未處理的 `restore` 步驟路徑（中止在 FP-R1 後改動）；② R 的 `no_change` 路徑；③ `untouched` 路徑，改在所有 `restore`／`remove` 完成之後、標記刪除之前；④ 同 ③，但改在標記刪除之後、終態紀錄寫入之前。每例都以同請求重送 R、`operation resume R` 續做。預期：
  - ①②：V5 停止；③：檢查 A 停止，標記保留；④：檢查 B 停止；
  - 四例中 R 都保持 `in_progress`，沒有 `status.d/<R>-completed`；X 已完成的例子中，也沒有 `<X>-rolled_back`；
  - `maintenance end` 被拒絕；
  - 依 §13.9 的修復表模擬經授權的人工修復，再 `operation resume R` → 完成，`verify --rolled-back` 通過。子例：沒有完成紀錄的步驟（①）恢復成 before → 完成；有完成紀錄的步驟被改動 → 恢復成 after → 完成；恢復成 before → 仍停止；②③④ 恢復成記錄值 → 完成；
  - 恢復成表外的內容 → 仍停止；
  - 未授權的恢復成 after（驗證已揭露的限制）：選一個前面還有未執行步驟的非相鄰步驟改成 after → L 被往後推，前面的步驟被判為衝突，停止；選目前已執行前綴的下一步改成 after → 被當成合法尾端，補寫完成紀錄後繼續，測試斷言這個行為並標明屬於外部寫入限制。
- **AC-09-84**：標記與兩次檢查。各例由正式流程和故障注入建立：① 已完成的 X → rollback，沒有中止；② 部分移轉（X 沒寫到標記）→ rollback，標記在 R 的 `no_change`；③ ① 的 R 中止在檢查 A 通過之後、標記刪除之前；④ ① 的 R 中止在標記已刪除、完成紀錄未寫（合法尾端）；⑤ ① 的 R 中止在標記刪除的完成紀錄已寫、終態紀錄未寫；⑥ 防禦性：以故障注入讓檢查 A 時的標記屬於其他 op；⑦ R 中止在 `restore` 群組完成之後、檢查 A 之前，續做前以故障注入改動：⑦a 一個有完成紀錄的 `restore` 輸出，⑦b 一個 `untouched` 路徑。預期：
  - 每個檢查點先斷言各群組的狀態：檢查 A 時 `takeover`、`restore` 全部 after，`marker` before，`terminal` 全部 before；檢查 B 時 `marker` after，`terminal` 全部 before；不能只斷言檢查函式傳回 True；
  - ①：檢查 A（標記仍在、屬於 X）通過 → 刪除標記 → 檢查 B 通過 → 完成；
  - ②：R 沒有標記步驟；X 未完成，`terminal` 只有 Rt2；完成後再送任何寫入請求，第 0 步都不會把它當成終態不一致；檢查 A、B 都要求標記不存在，通過 → 完成；
  - ③④⑤：兩種入口都能續做完成；③ 重新執行檢查 A；④⑤ 不執行檢查 A，只執行檢查 B；
  - ⑥：檢查 A 停止，標記不刪除；這例不屬於正式流程；
  - ⑦a：在 V5 停止，沒有到達檢查 A；⑦b：先斷言 V5 通過，再斷言在檢查 A 停止；
  - ⑦a、⑦b 兩種入口都斷言：標記保留、沒有終態紀錄、`maintenance end` 被拒絕；
  - ①～⑤ 的 `verify --rolled-back` 都通過。
- **AC-09-85**（FP-R5）：終態階段。以已完成的 X 建立 R（`terminal` 有 Rt1、Rt2），各例由正式流程和故障注入建立：① 檢查 B 通過之後、Rt1 寫入之前中止；② Rt1 已寫入、完成紀錄未寫（合法尾端）；③ Rt1 的完成紀錄已寫、Rt2 未寫；④ 同 ③，續做前以故障注入改動：④a 一個有完成紀錄的 `restore` 輸出，④b 一個 `untouched` 路徑；⑤ 以部分移轉（X 未完成，`terminal` 只有 Rt2）重做 ①；⑥ 防禦性：以測試專用的故障注入造出 Rt2（`<R>-completed`）存在、Rt1（`<X>-rolled_back`）不存在的非法排列（移轉標記已移除，維護檔仍在，其他計畫都已完成並登錄），分別送出：⑥a 同請求重送 R；⑥b `operation resume R`；⑥c 新的 `maintenance end`；⑥d 其他新的寫入 action（`migrate --new-request`、`maintenance start`）；⑥e `operation resume` 另一個已存在的 op（例如已完成的 X）；⑥f 同時放入一份合法的未登錄計畫，再送 ⑥c；⑥g 唯讀指令 `operation list`、`migrate verify --rolled-back`。①～⑤ 都以同請求重送 R、`operation resume R` 續做。預期：
- **AC-09-86**：目標宣告變動、閉包為空。S 沒有任何引用（`undeclared`），以正式流程分析產生 revision（`target_decl_rev` = 0）→ 人執行 `spec reference declare-empty S --reason …`。預期：S 的 `decl_rev` 變成 1；閉包仍為空；判定為 `declaration_changed`；擋 `_skip` 與無 T0 流程的 `run new`；以本次 basis 計算的 basis_hash 和舊的不同。
- **AC-09-87**：接續 AC-09-86。(a) 在 `declared_empty` 之後 `spec reference add` 一筆 informative 引用；(b) 舊 run 依它固定的 pin 續做（中止後以兩種入口續做）。預期：(a) `decl_rev` 再增加，判定為 `declaration_changed`（即使 informative 不進 basis 的閉包）；(b) 舊 run 的續做依計畫中固定的 pin 與證據完成，不因宣告變動而改寫計畫。
- **AC-09-88**：legacy R000 的輔助資料。在含 legacy RM 的唯讀複本上移轉。預期：`R000.meta.yaml` 存在，`target_decl_rev: 0`、`reference_pins: []`、`revision_sha256` 等於 R000；R000 與原 `requirements.yaml` 的 hash 都不變；移轉後第一次過時判定、`_skip`、無 T0 流程的 `run new` 都能經由統一的解析函式取得 R000 的 pin，結果和移轉前的行為一致（沒有任何宣告 → 不判定 `declaration_changed`）。
- **AC-09-89**：接續 AC-09-88。(a) 對該 spec 版本執行 `spec reference declare-empty --reason …`（或 add 一筆引用）；(b) 一個綁定 R000 的舊 run 中止後，以兩種入口續做。預期：(a) `decl_rev` 變成 1 → 判定 `declaration_changed`，擋 `_skip` 與無 T0 流程的 `run new`；(b) 續做使用計畫中固定的 R000 pin，不重算、不改寫 `R000.meta.yaml`。
- **AC-09-90**：rollback 與重新移轉（獨立 fixture，不接在 AC-09-89 的宣告變更之後）。預期：rollback 後 `R000.meta.yaml` 不存在（`remove` 類）；以新 op X2 重新移轉 → 重新建立的 `R000.meta.yaml` 中，**業務 pin 欄位**（`revision`、`legacy`、`revision_sha256`、`target_decl_rev`、`reference_pins`）與 legacy CLR rev 0 的 basis（`{target, target_decl_rev: 0, closure: []}`）和第一次移轉 X1 相同；`created_by_op` 等於 X2、不等於 X1（不比較整個 meta 檔的 hash）；其他控制證據依 X2 的計畫核對；沒有沿用或遺留上一次移轉的過時 pin。
- **AC-09-91**（防禦性）：以測試專用的故障注入，讓某個 spec 版本在移轉前就有宣告。分兩例：(a) 目前 `references` 非空；(b) `references` 為空，但已有 `reference_declarations`（有宣告歷史）。預期：兩例都拒絕移轉，不建立計畫、不寫任何檔案。前提檢查不能只看目前 `references` 是否非空。只證明前提檢查存在，不屬於正式流程。
- AC-09-88、89、90 各使用獨立的 fixture；AC-09-89 的宣告變更之後，rollback 仍受 `untouched`、T7 與後續操作限制。
  - 每例先斷言各群組的狀態（例如 ③：`takeover`、`restore`、`marker` 全部 after，Rt1 after 且有完成紀錄，Rt2 before）；
  - ①②③：第 0 步通過（② 符合前綴規則）；不執行檢查 A；依前綴規則再執行一次檢查 B → 通過 → 寫入剩下的終態步驟 → 完成；
  - ⑤：第 0 步通過（R 只有 Rt2，合法）；`marker` 群組是空的、`terminal` 尚未寫入，依 §13.7 續做表「`marker` 群組是空的」一列再執行一次檢查 A（條件與檢查 B 相同：標記必須不存在）→ 檢查 B → 寫入 Rt2 → 完成（附錄 A 5-15）；
  - `status.d/<X>-rolled_back`、`<R>-completed` 各只有一個；Rt1 不重寫；
  - ④a：在 V5 停止，沒有到達檢查 B；④b：先斷言 V5 通過，再斷言在檢查 B 停止；
  - ④a、④b 兩種入口都斷言：Rt1 不重寫、Rt2 不寫，R 保持 `in_progress`，`maintenance end` 被拒絕；Rt1 已記錄的 X 終態不撤回；
  - ④a、④b 依修復表恢復（④a 恢復成 after，④b 恢復成記錄值；標示為測試中模擬的授權處理）之後續做，完成；
  - ⑥a～⑥f：全部在**第 0 步**停止，理由是「終態不一致」；斷言沒有新的計畫檔；沒有新的 `index.d`、`status.d`、`progress.d`、`audit.d` 紀錄；⑥f 的未登錄計畫沒有被登錄；維護檔不變，`maintenance end` 沒有離開維護；Rt2 沒有被刪除，Rt1 沒有被補寫；
  - ⑥g：照常執行；`operation list` 回報 R 終態不一致；`verify --rolled-back` 失敗並列出缺少的 Rt1；
  - ⑥ 不屬於正式流程，只證明第 0 步的攔截範圍；
  - ①②③⑤ 的 `verify --rolled-back` 都通過。

#### 17.4 第一批整合驗收

AC-A-B1-7（CIA 候選完整性）、AC-A-B1-8（manual）列在第 6 章 §12 的第一批整合驗收表。

---

### 18. 已知限制

1. **TC 與舊 run 的 legacy 綁定是盡力綁定**：TC 建立後 RM 可能被腳本就地改過，sidecar 的 R000 不宣稱是當時實際使用的模型。
2. **整段尾端被一致刪除**（例如把最後一個或幾個已執行步驟的輸出和完成紀錄一起刪掉，或把業務檔還原成 before 再刪掉紀錄），無法和「從未執行」區分。
3. **外部把未執行步驟的輸出寫成剛好等於計畫值**，這一步會被當成已執行；如果它在原本尾端之後，會把 L 往後推，使前面未執行的步驟被判為衝突（拒絕，不會誤放行）。
4. **檢查只保證當下讀值**：flock 只排除經過執行器的寫入；對不取鎖的外部修改沒有跨多檔的原子保證；最後一次檢查之後的人工修改擋不住。維護窗口與人工修復期間必須以人工協調停止其他外部寫入。Rt1 寫入後才發生的外部修改，會讓 Rt2 停止，但 Rt1 不撤回。
5. **後續操作報告只能盤點經由執行器計畫的寫入**；外部手動修改或未接上執行器的寫入（例如 admin-ui 後端直接寫入）若落在清單以外的路徑，不一定會被發現，可能在回復後殘留。不能把「無法盤點」解讀成「所有外部修改都一定會被擋下」。
6. **W1 期間舊程式不認得維護模式**，只能靠人工協調停止寫入。
7. **`audit.log` 改為整份替換**、不再追加；行格式維持現行 tab 分隔，但讀取者（含 admin-ui）需要配合。
8. **R6 是人工步驟**：程式 revert 後以人工移除維護檔，需授權並記錄。
9. **終態不一致沒有自動出口**：第 0 步拒絕所有寫入，只能由人處理。
10. 直接寫 `requirements.yaml` 的偵測（`req verify`）與 `spec outdated` 報表在第二批；第一批只提供判定函式。


---

## 第 6 章　CLR 生命週期（FIX-10，人工確認結案）

> 本章為需求 A 最終規格的一部分（FIX-10）。所有 AC 都是**預期結果**，尚未實作、尚未執行。fixture 的初始資料一律經測試 root 的正式流程建立（`spec import`、`spec reference add|remove`、`run new`、`dispatch`、`submit`、`approve`、`applicability add` 等），不手造 run、引用、TC、pin 或 CLR；只有標明「竄改反例」者才在流程後故意修改檔案。

---

### 1. 目的

1. RESOLVE_AMBIGUITY 核准**不再**讓 CLR 直接結案。「核准」「答案被分析納入（INCORPORATED）」「人工確認結案（APPLIED）」是三個不同事件。
2. CLR 結案（APPLIED）由**人逐張確認**，runtime 只做輕量檢查：落地 run 已完成、該 run 的產出確實引用最新答案、採用目標都被明示確認或延後、每一張影響候選 TC 都有結論、掃描依據可重現。
3. 文件索取單（`document_request`）依**逐項**的 fulfill／waive 結案，每一項保存可重新驗證的對應證據。
4. 系統**不**自動結案、**不**機械保證「所有受影響 TC 都已落實答案」；這是明列的已知限制（§13）。

---

### 2. 本章使用的名詞

以下名詞的完整定義見共用名詞章，這裡只給一句說明：

| 名詞 | 說明 |
|---|---|
| CLR | Clarification，要問 PM 或索取文件的單子（`clarifications/<product>/<area>/<CLR-ID>.yaml`）。`kind`：`spec_question`、`conflict_resolution`、`document_request`；舊資料沒有 kind 時視為 `spec_question`。 |
| answer_rev | CLR 不可變的答案修訂（`answer_revisions[]` 的一筆），每筆帶 basis、basis_hash、answer_sources。「最新 answer_rev」指最後一筆。 |
| SpecPin | `{spec_id, spec_version, content_hash}`，指定一份已匯入 spec 的特定版本內容。 |
| RMPin | `{spec_id, spec_version, revision, sha256}`，指定需求模型的某個不可變 revision。 |
| SourceRef | 有型別的來源引用，分 `spec`、`clarification`、`approval` 三型。 |
| QuestionScope | 一個決策問題的適用範圍（`subject`、`role_scope`、`params`）。 |
| effective_basis | 解析 SourceRef 後實際作為依據的來源：approval 包裝會展開成具名條目內部的 clarification source；**只有 approve 或 override 的核准單算包裝**，reject 核准單不是包裝。 |
| X16 | 答案作為依據時的適用性檢查：(a) 答案自身的 basis_hash 等於本次而且 scope 涵蓋，或 (b) `applicability` 中有 answer_rev、basis_hash、scope 都符合的人工紀錄。 |
| applicability | CLR 上只能追加的人工適用性紀錄，用來把答案用到原題以外的 requirement／scope。 |
| decision_refs | TC 斷言依賴的決策點清單 `[{requirement_id, question_id, basis_ref}]`。 |
| landing | CLR 上只能追加的落地紀錄（`landings[]`）。 |
| 採用目標（adopted target） | 本章 §5.4 定義：最新答案實際被採用的決策點。 |
| 掃描單位（scan unit） | 本章 §5.10 定義：`(product, area)` 組合。 |
| op_id、操作計畫、executor、flock | 定義見操作執行章。本章所有寫入指令都在全域操作鎖（flock）內、以操作計畫執行。 |

---

### 3. 狀態機

#### 3.1 狀態

`OPEN`、`ASKED`、`ANSWERED`、`INCORPORATED`、`APPLIED`、`WITHDRAWN`。終止狀態：**APPLIED、WITHDRAWN**。

#### 3.2 轉換表

「同 A2」的 kind = `spec_question`、`conflict_resolution`、legacy（沒有 kind 的舊單）。

| # | 轉換 | 觸發者 | 條件 | 適用 kind |
|---|---|---|---|---|
| A1 | OPEN → ASKED | 人 `ask` | `--sent-at`、`--channel` 選填；補記時兩個時間都保留 | 全部 |
| A2 | OPEN、ASKED → ANSWERED | 人 `answer` | answer_sources 驗證通過；記錄此 rev 的 basis | spec_question、conflict_resolution、legacy |
| A3 | ANSWERED → ANSWERED | 人 `answer` | 追加一筆 answer_rev | 同 A2 |
| A4 | ANSWERED → INCORPORATED | system（G-SPEC 提交、G-BVAL 提交的操作） | 提交的 revision 或 BugDraft 中，有**明確的 SourceRef**，其 effective_basis 等於這張 CLR 的**最新** answer_rev，而且通過 X16；追加 landing `{type: incorporated, rm_pin 或 bug_draft, run_id, op_id}` | 同 A2 |
| A4' | INCORPORATED → INCORPORATED | system | 其他 revision 或 BugDraft 再引用；只追加 landing | 同 A2 |
| A5 | INCORPORATED → ANSWERED | 人 `answer` | 追加新 answer_rev（代表需要重新納入）；既有 landings 保留 | 同 A2 |
| A6 | INCORPORATED → APPLIED | 人 `apply --path a6` | §5 | 同 A2 |
| A6b | ANSWERED、INCORPORATED → APPLIED | 人 `apply --path a6b` | bug reject 路徑：落地 run 是因 RESOLVE_AMBIGUITY reject 而 COMPLETED 的 spec-to-bug run，該 reject 決議中有一個條目，其**內部** clarification source 指向本 CLR 的最新 answer_rev（最終沒有 BugDraft 或 revision 引用它）；其餘依 §5 | 同 A2 |
| A7 | ANSWERED → APPLIED | 人 `apply --path a7` | 最新答案的 resolution 是 `no_change` 或 `out_of_scope`，而且**全部歷史**都沒有引用本 CLR 的任何 answer_rev（§5.8） | 同 A2 |
| A8 | OPEN、ASKED → APPLIED | `fulfill`、`waive-item` 之後，或核准操作套用 `waive_missing` 之後的**最後判定** | §6.6 | document_request |
| A9 | OPEN、ASKED → WITHDRAWN | system（核准操作套用 `waive_missing` 之後的最後判定） | 核准的 `waive_missing` 涵蓋本單**全部**文件項目，而且依重新驗證，**沒有任何**項目是有效的 fulfillment（§6.7） | document_request |
| A10 | OPEN、ASKED、ANSWERED、INCORPORATED → WITHDRAWN | 人（`withdraw`） | 附理由；INCORPORATED 時，引用它的 revision 在下次判定時為 `decision_revised` | 全部 |

#### 3.3 通則

1. APPLIED 之後**只能追加** `applicability`、`evidence_addenda`、`landings`；狀態不變；不追加答案修訂。
2. 舊資料：既有的 APPLIED、ANSWERED 不變；沒有 kind 的舊 CLR 視為 `spec_question`。
3. **第一批中 A4 的範圍**：只辨識**有明確 SourceRef** 的引用。spec-to-bug 的 SourceRef 強制屬於第二批，所以第一批中沒有提供 SourceRef 的 BugDraft **不會**觸發 A4（維持舊行為）。不宣稱所有 bug 都已追溯。
4. 這種情況下（沒有 SourceRef，所以沒有採用目標），如果 PM 的答案事實上被該 bug 判斷用到，正確做法是在第二批 SourceRef 強制之後重新走 A6；在那之前，人依實際狀況選擇 A7（確實沒有引用，而且答案是 `no_change`／`out_of_scope`）或 A10（撤回）。系統不替人判斷。
5. **不再有 system 自動結案**：run 完成（complete_run）只持久化 COMPLETED 並重建衍生輸出，不碰 CLR。

#### 3.4 呼叫端

| 呼叫端 | 行為 |
|---|---|
| `engine.py` `_after_ambiguity`（approve、override） | **不再 apply**。只寫入決議（含 `resolutions[]`）；對文件索取單套用 `waive_missing` 後執行最後判定（§6.6、§6.7，結果可能是 A8、A9 或不變）；重開分析任務（依 workflow 實際的 task ID，例如 spec-to-testcase 是 T1） |
| `_after_ambiguity`（reject） | 依現行行為：spec 類流程重開分析，CLR 不變；spec-to-bug 為 bug 改 REJECTED、run COMPLETED，CLR 不變（之後可由人以 A6b 結案） |
| G-SPEC 提交、G-BVAL 提交 | A4、A4' |
| CLI `clarification apply` | A6、A6b、A7 |
| CLI `clarification fulfill`、`waive-item` | 逐項記錄，之後執行最後判定（§6.6） |
| CLI `clarification ask`、`answer`、`withdraw` | A1、A2／A3／A5、A10 |
| run 完成 | 不觸發任何 CLR 轉換 |

---

### 4. `clarification impact`（保存掃描紀錄）

```text
bin/qaos clarification impact <CLR> [--keyword <詞> ...] [--target <spec_id>@<ver>:<REQ>#<Q> ...]
```

1. **寫入操作**：保存掃描紀錄，因此要取全域操作鎖、以操作計畫執行。維護中或尚未移轉時被拒絕（同所有業務寫入）。
2. 依 §5.10 的掃描單位與候選規則掃描；`--target` 作為掃描輸入（決定目標的掃描單位與 (a)(b) 候選）。
3. 掃描紀錄（schema `schemas/spec/clarification-scan.schema.json`）：

   ```text
   clarifications/<product>/<area>/scans/<CLR>-<scan_id>.yaml
   {scan_id, clr_id, answer_rev, keywords[], targets[], scan_units[], rule_version,
    candidates: sorted[{tc_id, active_version, tc_version_sha256, reasons[]}],
    scanned_at, op_id, sha256}
   ```

4. 掃描紀錄是 `apply` 的**關鍵字來源**之一，不是 CLR 狀態的證據；apply 一律在鎖內重新掃描（§5.9）。
5. 中止後續做：掃描紀錄只有一份。

---

### 5. `clarification apply`

#### 5.1 指令

```text
bin/qaos clarification apply <CLR> --path a6|a6b|a7
    [--landed-in <run_id> ...]                                        # a6：至少一個；a6b：恰好一個；a7：不接受
    [--target <spec_id>@<ver>:<REQ>#<Q> ...]                          # a6；a6b 只接受指向 reject 決議條目的 --target；a7 不接受
    [--defer-target <spec_id>@<ver>:<REQ>#<Q>=<理由> ...]             # 只限 a6
    [--keyword <詞> ...] [--scan <scan_id>] [--no-keyword-reason <文字>]  # 依最終關鍵字規則（§5.9）
    --tc-conclusion <TC-ID>=<updated|not_affected|retire_planned|deferred:<理由>> ...
    --impact-reviewed <整體說明>
    --by <人>
```

#### 5.2 三條路徑（必須明確選擇，runtime 不推測）

runtime 驗證 `--path` 和 CLR 狀態、最新答案的 resolution、輸入是否一致；不一致就拒絕。

| 路徑 | CLR 狀態 | 最新答案的 resolution | 必填 | **不接受**（帶了就拒絕） |
|---|---|---|---|---|
| `a6` | INCORPORATED | `requirement_clarified` 或 `spec_updated` | `--landed-in`（至少一個）、每個採用目標的 `--target` 或 `--defer-target`、關鍵字輸入（§5.9）、所有候選的 `--tc-conclusion`、`--impact-reviewed`、`--by` | — |
| `a6b` | ANSWERED 或 INCORPORATED | `requirement_clarified` 或 `spec_updated` | `--landed-in`（**恰好一個** spec-to-bug run）、`--target`（指向該 run 的 RESOLVE_AMBIGUITY reject 決議中、以本 CLR 為 source 的條目）、關鍵字輸入、所有候選的 `--tc-conclusion`、`--impact-reviewed`、`--by` | `--defer-target` |
| `a7` | ANSWERED | `no_change` 或 `out_of_scope` | 關鍵字輸入、背景候選的 `--tc-conclusion`、`--impact-reviewed`、`--by` | `--landed-in`、`--target`、`--defer-target` |

#### 5.3 執行順序

全部在**全域操作鎖內**、以操作計畫執行；任一項不成立就拒絕，**CLR 不變**：

1. `--by` 是人（不是 agent 或 system）。
2. 路徑和 CLR 狀態、resolution、輸入一致（§5.2）。
3. **a6、a6b**：解析採用目標（§5.4）→ 目標確認／延後（§5.5）→ landed-in 檢查（§5.6）；a6b 另驗有效依據（§5.7）。
4. **a7**：全部歷史無引用檢查（§5.8）。
5. 最終關鍵字與 scan 驗證（§5.9）。
6. 依掃描單位重新掃描候選（§5.10）；每一張候選都要有 `--tc-conclusion`（§5.11）。
7. 寫入：CLR 狀態 → landing → history → 重建衍生輸出（§5.12）。

#### 5.4 採用目標的解析（a6、a6b）

1. 在鎖內掃描以下來源中，**effective_basis 等於本 CLR 最新 answer_rev**、而且**通過 X16** 的決策點：
   - 每一個 spec 版本的**最新** revision（不只落地 run 的）；
   - 每一個 `--landed-in` run 綁定的目標 revision、最終 BugDraft，以及 RESOLVE_AMBIGUITY 決議（bug reject 路徑）。
2. 每個採用目標的身分：

   ```text
   {product, area, spec_id, spec_version, 來源（revision、BugDraft 或決議條目）,
    requirement_id, question_id, QuestionScope, 適用依據: own_scope | applicability(entry_sha)}
   ```

   - `product`、`area` 從目標 spec 自己的 `spec.yaml` 讀取（`product`、`functional_area`），**不**沿用 CLR 的 product。
3. 允許跨 requirement、跨 question、跨 area、跨 product 的採用（只要經 X16 成立）。沒有 applicability 的跨需求使用，在 G-SPEC 時就會因 X16 FAIL，不會成為採用目標。
4. CLR 原題（CLR 自身的 requirement／question）只作為**背景候選**（§5.10 (c)），不是唯一的落地範圍，也不要求 landed-in run 包含原題的 requirement。
5. 目標**一律在鎖內重新解析**，從不沿用 scan 紀錄中的目標身分。

#### 5.5 目標的確認與延後

- `--target <spec_id>@<ver>:<REQ>#<Q>`：確認本次 apply 涵蓋這個目標。
- `--defer-target <…>=<理由>`：具名延後；記錄在 landing，可用 `clarification show` 查詢。
- **a6**：解析出的目標，**每一個**都必須被 `--target` 或 `--defer-target` 涵蓋，否則拒絕並列出遺漏的目標。
- 指定了不存在於解析結果的目標 → 拒絕。
- **a6b**：`--target` 必須是落地 run 的 reject 決議條目；不接受 `--defer-target`。
- 延後的目標**仍然**納入掃描單位，其候選仍須逐張給結論（§5.10、§5.11）。

#### 5.6 landed-in 檢查（a6、a6b）

每一個 `--landed-in` run：

1. 狀態是 COMPLETED（CANCELLED 等其他狀態 → 拒絕）；
2. 它綁定的目標 revision（或最終 BugDraft；a6b 為 reject 決議條目）中，**至少含一個被 `--target` 確認的目標**（因此也必然引用最新 answer_rev）；
3. run 的範圍包含該確認目標的 requirement_id。

- 只含被延後目標的 run 不能作為 landed-in（不放寬此規則）。
- 答案追加新 rev（A5）之後，舊 run 的產出引用的是舊 rev，不會含任何依最新 rev 解析出的目標 → 拒絕；需先重新分析納入最新 rev。
- 不要求每個已確認目標都各有自己的已完成 run（§13 第 5 點）。

#### 5.7 A6b 的有效依據

1. 解析 reject 核准單（類型 RESOLVE_AMBIGUITY、決議 reject）中 `--target` 指定的 `resolutions[index]`。
2. 該條目**內部的** `source` 必須是 clarification 型、指向本 CLR 的**最新** answer_rev，並通過 X16 的 scope 和 basis 檢查。
3. 該 reject 核准單是**落地證據**，**不是** approval 包裝。effective_basis 仍然只接受 approve 或 override 的包裝；所以在 G-SPEC 中，以 reject 核准單作為 approval 型 SourceRef → X15 FAIL，不會被當成裁決。
4. 以下**任一項成立** → 拒絕：條目 source 指向舊 rev、scope 不符、條目不是 reject 決議中的條目、普通的 reject（條目沒有 source）。合法例：reject 決議中的條目，其內部 source 指向本 CLR 的最新 rev、scope 相符（AC-10A-43）。

#### 5.8 A7：全部歷史無引用檢查

1. 掃描以下**全部歷史**：
   - 所有 RM revision（不只最新）；
   - 所有 BugDraft；
   - 所有 TC 版本（含 SUPERSEDED、RETIRED）的 `decision_refs`；
   - 所有核准單的 `decision.resolutions`（含 approve、override、reject）。
2. 只要有任何一處的 effective_basis，或條目內部的 source，指向本 CLR 的**任何** answer_rev → 拒絕，並列出引用位置（例如 APR 與條目）。approval 包裝也要展開檢查。
3. 計畫記錄 `reference_scan_sha256`。
4. 候選只有 (c) 背景候選加 (d) 關鍵字候選，都只在 CLR 自身的 `(product, area)`；每一張都要有結論。**沒有任何候選時也可以通過**（仍要求 `--impact-reviewed`）。

#### 5.9 最終關鍵字規則與 scan 驗證

1. **最終關鍵字** = `--keyword` 的集合 ∪ `--scan` 紀錄中的 keywords（去重）。`--scan` 只是關鍵字的來源之一，可以和 `--no-keyword-reason` 一起使用。
2. 規則：

   | 最終關鍵字 | `--no-keyword-reason` | 結果 |
   |---|---|---|
   | 非空 | 沒有 | 關鍵字模式 |
   | 非空 | 有 | **拒絕**（互相矛盾） |
   | 空 | 有 | 無關鍵字模式；理由保存在 landing |
   | 空 | 沒有 | **拒絕** |

   - 沒有 `--keyword`、`--scan`、`--no-keyword-reason` 任何一項 → 最終關鍵字為空且沒有理由 → 拒絕。
3. **scan 的驗證**：
   - `scan.clr_id` 必須等於本 CLR，否則拒絕。
   - `scan.answer_rev` 不等於最新 rev → **只沿用關鍵字**，scan 中的目標和候選一律不採用；apply 輸出提示「scan 屬於舊答案修訂，目標已重新解析」。
   - `scan.rule_version` 和目前規則不同 → 同樣只沿用關鍵字。
   - 目標一律在鎖內重新解析（§5.4 第 5 點）。
4. **鎖內重新掃描**：apply 一律以最終關鍵字和目標重新掃描候選。使用 `--scan` 時，若重新掃描的候選（tc_id、active_version）和保存的不同 → 顯示差異，**以重新掃描的結果為準**，每一張都必須有結論。
5. landing 記錄：`{scan_id?, scan_answer_rev?, scan_reused: keywords_only | full, final_keywords, no_keyword_reason?}`。

#### 5.10 掃描單位與候選規則

1. **掃描單位**：

   ```text
   scan_units = {(CLR.product, CLR.area)} ∪ {(t.product, t.area) | t ∈ 確認的目標 ∪ 延後的目標}
   ```

   - 不同 product、相同 area 名稱 → 兩個單位分開掃描，不合併。
   - a7 只有 `(CLR.product, CLR.area)` 一個單位。
2. **候選規則**（每個單位內各自執行；只看 ACTIVE TC）：

   | 規則 | 內容 | 適用單位 | 路徑 |
   |---|---|---|---|
   | (a) 目標需求候選 | `requirement_ids` 含該單位內任一目標的 requirement_id | 有目標的單位 | a6、a6b |
   | (b) 依賴舊答案的 TC | `decision_refs` 的 `(requirement_id, question_id)` 等於該單位內某個目標、scope 相同，但 effective_basis **不是**最新 answer_rev（含舊 rev、其他來源）；legacy TC 沒有 decision_refs 時由 (a) 涵蓋 | 有目標的單位 | a6、a6b |
   | (c) CLR 原題的背景候選 | `requirement_ids` 含 CLR 自身 requirement | **只在** CLR 自身的單位 | a6、a6b、a7 |
   | (d) 關鍵字候選 | title、preconditions、steps、expected_result 的文字命中任一最終關鍵字 | **所有**單位 | a6、a6b、a7 |

3. 掃描紀錄與 landing 都記錄 `scan_units`。
4. 規則版本以 `rule_version` 記錄。

#### 5.11 每張候選的 `--tc-conclusion`

- 格式：`<TC-ID>=updated | not_affected | retire_planned | deferred:<理由>`。
- 重新掃描得到的**每一張**候選（含延後目標所在單位的候選）都必須有結論；缺少 → 拒絕，並列出缺少結論的 TC。
- 結論只記錄人的判斷；系統不驗證是否屬實（§13）。`retire_planned` 不代表已退休，`deferred` 不會被自動追蹤。

#### 5.12 寫入內容

1. CLR 狀態改為 APPLIED。
2. 追加一筆 landing（只能追加），可以重現 apply 當時的完整候選和結論：

   ```text
   {type: applied, path: a6 | a6b | a7,
    landed_in[]（a7 無）, targets_confirmed[], targets_deferred[{target, reason}]（a6）,
    scan_units[], final_keywords | no_keyword_reason,
    scan_id?, scan_answer_rev?, scan_reused: keywords_only | full,
    rule_version,
    candidates: [{tc_id, active_version, tc_version_sha256, reasons[]}],
    conclusions,
    scan_sha256, reference_scan_sha256（a7）, op_id}
   ```

3. 追加 history（摘要）；landing 是完整證據，history 不是唯一證據。
4. 業務步驟全部完成後重建衍生輸出（CLR `.md` 等）；重建失敗時計畫**不標記完成**，`resume` 重試重建，業務檔不變。
5. 中止後續做：landing 只有一筆。

---

### 6. 文件索取單

#### 6.1 document_items

- 建立 `document_request` 時，`missing_sources` 至少一項（只需要引用處：SpecPin＋行號＋命中文字，不需要缺檔本身的 hash）；每一項各成為一個 `document_items[]`：

  ```text
  {item_id, cited_at, name, status: open | fulfilled | waived, fulfillments[]}
  ```

#### 6.2 `fulfill`

```text
bin/qaos clarification fulfill <CLR> --item <item_id> --document <spec_id>@<ver>
     [--mapping-reason <文字>] --by <人>
```

條件（任一不成立就拒絕；`--by` 記錄執行的人）：

1. document 版本已匯入、hash 相符。
2. document 在 CLR 目標 spec（同一 spec_id、版本 ≥ CLR 的 spec_version）某個版本**目前有效的** decl_rev 中，被宣告為 reference；該目標版本即 `target_pin`。
3. 對應方式成立（§6.3）：名稱比對成立，或附 `--mapping-reason` 走人工對應。

#### 6.3 名稱比對（`name_match`）與人工對應（`human_mapping`）

1. **比對來源**：
   - `n1` = document 版本的 `source.external_filename`，去掉副檔名、去掉結尾的 `_v\d+` 或 `_vNN`；
   - `n2` = spec 的 `title`。
2. **正規化**：全形轉半形、去除所有空白（含全形空白）、轉小寫。`item.name`、`item.cited_at.text` 也做同樣的正規化。
3. **有效性**：正規化後**長度大於 0** 的才算有效名稱。來源欄位不存在、是空字串、全是空白，或去掉版本和副檔名之後變成空的 → 該來源**不參與**比對。
4. **比對成立**：至少有一個有效名稱，以子字串方式出現在正規化後的 `item.name` 或 `item.cited_at.text` 中。`item.name` 和 `cited_at.text` 正規化後都是空的 → 該項只能走人工對應。
5. 沒有任何有效名稱，或比對不成立 → **必須**附 `--mapping-reason`（human_mapping，記錄執行者和理由，例如別名、一份文件補多項）；沒有理由 → 拒絕。
6. 系統**不理解**文件內容；human_mapping 的正確性由人負責。
7. **匯入端**：`spec import` 對 title 正規化後為空的情況輸出**警告**，不阻擋匯入，不修改 schema。

#### 6.4 fulfillment 紀錄

每一次 fulfill 追加一筆（只能追加），保存在該 item 的 `fulfillments[]`：

```text
{item_id, document_pin: SpecPin, target_pin: SpecPin, target_decl_rev,
 match: {method: name_match | human_mapping, matched_text?, reason?, by},
 op_id, at, sha256}
```

- 同一份文件可以補多項；每一項各有一筆 fulfillment，對應方式各自判斷。

#### 6.5 `waive-item`

```text
bin/qaos clarification waive-item <CLR> --item <item_id> --reason <文字> --by <人>
```

- 人執行；該項改為 `waived`。

#### 6.6 最後判定（A8）

在以下時點執行，三處共用同一個判定函式：`fulfill` 之後、`waive-item` 之後、核准操作套用 `waive_missing` 之後。

1. 先依 §6.7 判斷是否為 A9 的情況；是 → A9，結束。
2. 否則逐項依**重新驗證的結果**分類（不看歷史紀錄是否存在）：
   - **有效的 fulfillment**：取該項**最新一筆** fulfillment，重新驗證：
     1. `document_pin` 仍是已匯入、hash 相符的版本；
     2. `target_pin` 的**目前** decl_rev 的 `references` 仍包含 `document_pin`；
     3. 對應方式的紀錄完整。
   - **waived**：以 `waive-item` 豁免，或被核准的 `waive_missing` 條目以 `item_id` 列出。
   - 其他（沒有 fulfillment、或最新一筆已失效，而且沒有被豁免）→ 未完成。
3. 全部項目都是有效的 fulfillment 或 waived → **APPLIED**（追加 landing）。
4. 任一項未完成 → 不轉換；`clarification show` 顯示未完成與失效的項目和原因。重新宣告（新的 decl_rev）並重新 fulfill 該項後，可再判定。

#### 6.7 A9

- 核准操作套用 `waive_missing` 時，先把核准條目以 `item_id` 列出的項目標為 `waived`。
- **A9（WITHDRAWN）只在以下兩者同時成立時發生**：核准的 `waive_missing` 涵蓋本單**全部**項目；而且依 §6.6 的重新驗證，**沒有任何**項目是有效的 fulfillment。
- 其他情況（只涵蓋部分項目，或已有有效的 fulfillment）→ 執行 §6.6 的最後判定：全部項目都是有效 fulfillment 或 waived → APPLIED；否則不轉換。

#### 6.8 和 TC 流程的關係

- 文件 fulfill **不依賴** TC 核准：文件匯入並宣告之後就可以 fulfill，可和分析、revise、核准交錯進行。寫入操作仍由 flock 依序執行，同一時間只有一個 executor。

---

### 7. 唯讀查詢

| 指令 | 內容 | 鎖 |
|---|---|---|
| `clarification show <CLR>` | 狀態、answer_revisions、landings；列出 `deferred`、`retire_planned` 的 TC 與理由、`--defer-target` 的延後目標與理由；文件項目狀態，以及失效項目和原因 | 不取鎖 |
| `clarification stale-tcs <CLR>` | 隨時查詢依賴本 CLR、但尚未依最新答案處理的 TC。依據：TC 的 `decision_refs`、`requirement_ids`，以及最近一次 landing 的關鍵字；掃描規則同 (a)～(d)。輸出開頭附「不保證完整」的說明 | 不取鎖 |
| `clarification list` | 清單 | 不取鎖 |

- 唯讀指令不保證跨檔一致的快照（可能讀到另一個操作寫到一半的多檔狀態），輸出開頭附此說明。
- 唯讀指令不寫任何檔案。

---

### 8. 和操作計畫、維護狀態的關係

1. `impact`、`apply`（a6、a6b、a7）、`fulfill`、`waive-item`、`ask`、`answer`、`withdraw`，以及含 A4 的 submit_gate、含 A9 的 approve，都是業務寫入：取全域操作鎖、以操作計畫執行；尚未移轉時拒絕（「尚未移轉」），維護中拒絕（「維護中」）。准入與續做的完整規則見操作執行章與移轉章。
2. 恢復（預期結果）：

   | 故障點 | 恢復 |
   |---|---|
   | `apply` 在 CLR 狀態寫入之後、landing 之前中止 | 依計畫續做；landing 只有一筆 |
   | `impact` 在掃描紀錄寫入之前中止 | 續做；掃描紀錄只有一份 |
   | 業務步驟完成後，重建衍生輸出失敗或中止 | 計畫不標記完成；`resume` 重試重建；業務檔不變 |
   | `apply --path a7` 在全部歷史掃描之後、寫入之前中止 | 依計畫續做；計畫已記錄 `reference_scan_sha256`。重新取得鎖後，若歷史出現新的引用（由其他操作造成），計畫的 `pre_state` 和目前狀態不符 → 依 before／after 規則停止，提示重新發出請求 |
   | 核准決議寫入之後、A9 之前中止 | 續做；文件索取單只 WITHDRAWN 一次 |

3. 每種本章相關的操作類型各要有一個「中止加續做」驗收：submit_gate（含 A4）、approve（不 apply、含 A9）、impact、apply（a6、a6b、a7）、fulfill、waive-item、applicability_add。

---

### 9. 涉及的 schema、模組、CLI

| 類別 | 項目 |
|---|---|
| 狀態機 | `workflows/state-machines.yaml`：A1～A10、A6b |
| schema | `schemas/spec/clarification.schema.json`：`kind`、`answer_revisions[]`、`applicability[]`、`evidence_addenda[]`、`landings[]`（含 `path`、`scan_units`、`scan_reused`、`reference_scan_sha256` 等欄位）、`document_items[].fulfillments[]`、掃描紀錄的連結<br>新增 `schemas/spec/clarification-scan.schema.json` |
| 模組 | `tools/qaos/clarification.py`：`ask`、`answer`、`apply_`、`impact`、`fulfill`、`waive_item`、`stale_tcs`、`_render`<br>`tools/qaos/engine.py`：`_after_ambiguity` 不再 apply；G-SPEC、G-BVAL 提交的 A4、A4'<br>`tools/qaos/cli.py`：`apply --path`、`--target`、`--defer-target`、`--scan`、`--no-keyword-reason`、`--tc-conclusion`；`impact --target`；`fulfill`、`waive-item`、`stale-tcs` |
| 文件 | 新增 `docs/decisions/ADR-010-clarification-lifecycle-manual-confirmation.md`；`docs/decisions/ADR-008-clarification-apply-impact-scan.md` 加狀態註記（§10） |
| 實作階段 | P5（名稱正規化函式與 `spec import` 警告可在 P2 先驗，AC-10A-57） |

---

### 10. ADR-010 必須涵蓋的內容（與 ADR-008 的關係）

新增 ADR-010，**逐項**同步 ADR-008 Decision 第 1～4 點，並在 ADR-008 標註哪些部分被 ADR-010 取代。

#### 10.1 形式

1. ADR-010 列明對 ADR-008 的**保留、取消、修改**對照，不能只寫「ADR-008 被取代」，也不能只標第 3、4 點而遺漏第 1、2 點的介面與證據保存敘述。
2. ADR-008 加狀態註記，以相對連結指向 ADR-010；現行契約以 ADR-010 為準，ADR-008 原文保留為歷史。
3. ADR-010 的 Status／Accepted 日期反映 Oscar 實際的決定。
4. 記錄這是「CLR 結案先維持人工確認」的取捨，**不等於**原本的 DoD 完全維持。

#### 10.2 逐點內容

| ADR-008 | ADR-010 的處理 | 必須寫明 |
|---|---|---|
| Decision 1（`impact` 掃描範圍與關鍵字） | **修改** | 掃描以 `(product, area)` 分開，納入採用目標與 CLR 原題／關鍵字背景候選；跨 product、延後目標仍須依規則掃描。關鍵字採 `keyword ∪ scan.keywords`，空集合必須提供理由。目標解析與 apply 重掃在鎖內進行；舊 scan 不可取代當前狀態。`impact` 保存掃描紀錄 |
| Decision 2（`apply` 沒有 `--impact-reviewed` 就拒絕；候選與結論寫入 history note） | **修改** | 不能再只靠一段 `--impact-reviewed` 文字表示逐張完成。需說明每張候選的 `--tc-conclusion`、最新答案綁定、目標確認／延後與 landed-in 檢查；landing 保存候選版本／hash、結論、關鍵字、掃描依據。history note 可以是摘要，不能成為唯一證據 |
| Decision 3（RESOLVE_AMBIGUITY 核准即 apply） | **取消** | approve 和 override 都取消自動 apply；保留明確 SourceRef 納入的 A4；寫清 A6、A6b、A7 各自的前提；文件索取單另依逐項 fulfillment／waiver 結案。A6b 中 reject 條目的內部 source 是落地證據，reject 核准不是有效的裁決包裝 |
| Decision 4（需修訂／retire 的 TC 必須在同一次工作中處理完；「四項缺一不可」） | **放寬** | 「四項缺一不可」「同次工作處理完」不再作為 APPLIED 的硬保證；允許 `retire_planned`、`deferred`，但必須逐張記錄、可查詢。區分 CLR 人工結案、TC 尚待處理、final 輸出更新三件事 |
| Consequences | **修改** | 同步目前的 CLI、狀態機、證據位置與新驗收；ADR-008 原有測試標示為歷史驗證；保留原本「關鍵字掃描是文字比對，會漏掉換了說法的依賴」的限制 |

#### 10.3 必須明列的限制與風險

1. §13 已知限制全部（AC-10A-33）。
2. 結論真實性由人負責；延後事項不自動追蹤；部分已確認目標沒有自己的 completed run；事後新增的依賴不自動重開。
3. APPLIED 不代表全部 TC、版本、area 都已完成；`retire_planned` 不代表已退休。

#### 10.4 範圍外

- Oscar 本機 DoD memory 的修改另依 Oscar 授權，ADR-010 不代為修改，也不構成修改授權。

---

### 11. 分階段方案 S0～S7

每個階段結束都是停點，由 Oscar 明確授權後才進入下一階段。

| 階段 | 內容 | 前置條件 | 停點時由 Oscar 決定 | 失敗或取消 |
|---|---|---|---|---|
| S0 收件 | 登記回覆包的 manifest | 授權 | 原檔要不要入 repo | 不影響正式資料 |
| S1 匯入 | 7 份文件 | P：第一批 merge、移轉完成。Q：先用舊 importer，之後 `metadata upgrade` | P 或 Q；⑧ 的 ID、area、policy | revert 由 Oscar 決定 |
| S2 宣告 | 引用表 | 第一批、移轉完成 | 確認 | remove → 新的 decl_rev |
| S3 CLR 資料 | ask 補記、answer、metadata upgrade、applicability（確認 basis）、evidence_addenda | S1、S2 | scope 和 basis | 操作計畫（驗證失敗時 CLR 不變） |
| S3' 文件索取單 | `fulfill`（名稱比對或人工對應）；可和 S4～S7 交錯 | S1、S2 | 人工對應的理由 | 失效項目不結案 |
| S4 裁決與分析 | RESOLVE_AMBIGUITY；各 run 的 T0／T1；CIA 候選依 G1～G8 | S3 | 每張核准 | cancel → 該 run 所有 PENDING 的 APR 取消 |
| S5 revise | Designer → Validator → RR → CIA compare | S4 | — | 依現行規則迭代 |
| S6 核准 | per_item（依核准決議表） | S5 | **Oscar** | — |
| S7 結案 | `impact`（保存掃描）→ 依每張 CLR 的狀態選 `apply --path a6`（已納入）、`a6b`（bug reject）或 `a7`（`no_change`／`out_of_scope`，而且沒有引用） | S6（a6）；a7 不依賴 S4～S6 | **Oscar 逐張確認路徑、目標、TC 結論** | 檢查不通過時 CLR 不變 |

- S3' 與 S4～S7 的「交錯」是工作安排；寫入操作仍由 flock 依序執行。
- S7 只代表人工結論已落地，**不等於**全部 TC 都已更新完；`retire_planned`、`deferred` 和延後的目標要在交接中可見（`clarification show`）。
- 其他沿用內容（版本對照、引用表、CLR 資料清單、SITELIST 的 approve／reject／cancel、現金淨收 AC-R7-1～3）不在本章展開。

---

### 12. 驗收（全部是預期結果）

#### 12.1 通則

1. 每個拒絕案例都斷言：指令失敗、**CLR 檔的 hash 不變**（CLR 狀態與 landings 都沒有改變）。
2. 多個反例共用同一份正式建立的狀態時，先逐一斷言拒絕不改 CLR，最後才執行成功例。
3. 「列出缺少結論的 TC」類斷言，先以 `impact` 的掃描紀錄斷言該 TC（ID 與版本）確實在候選中，再刪去它的結論；拒絕訊息中，apply **重新掃描**的候選仍須包含該 ID。不可只依 TC 的描述推定它已入選。
4. spec-to-testcase 的分析任務是 T1（Spec Analyst）；測試以 workflow 實際的 task ID 為準。

#### 12.2 fixture 索引

| fixture | AC | | fixture | AC |
|---|---|---|---|---|
| RA-P1 | AC-10A-1 | | RA-N1 | AC-10A-4 |
| RA-P2 | AC-10A-2 | | RA-N2 | AC-10A-5 |
| RA-P3 | AC-10A-3 | | RA-N3 | AC-10A-6 |
| RA-P4 | AC-10A-7 | | RA-N4（= R1003-N2） | AC-10A-8、AC-10A-24 |
| RA-P5 | AC-10A-11 | | RA-N5（同 R1101-N1、N2） | AC-10A-9 |
| RA-P6 | AC-10A-31（同 R1101-P4 / AC-10A-43） | | RA-N6 | AC-10A-10 |
| RA-P7（同 R1101-P1） | AC-10A-36 | | RA-N7 | AC-10A-32 |

#### 12.3 AC-10A-1～69

**RA：基本生命週期**

| AC | fixture | 前置條件／情境 | 預期結果 |
|---|---|---|---|
| AC-10A-1 | RA-P1 | spec-to-testcase：T1 回報 critical conflict → 建立 RESOLVE_AMBIGUITY → 人 `answer` → approve（`select_interpretation`） | CLR 仍是 **ANSWERED**（沒有提前 APPLIED）；核准只寫入決議、重開 T1 |
| AC-10A-2 | RA-P2 | 接續：T1 重開 → 新 revision 以**明確 SourceRef** 引用 CLR rev 0 → G-SPEC 提交 | A4 → INCORPORATED；新增一筆 `type: incorporated` 的 landing |
| AC-10A-3 | RA-P3 | 接續：Designer → Validator → ACTIVATE → run COMPLETED → `apply --path a6 --landed-in <run> --target <原題目標> --keyword …`，全部候選都有 `--tc-conclusion` | **APPLIED**；landing 有完整的掃描內容（目標、掃描單位、關鍵字、候選版本與 sha256、結論） |
| AC-10A-4 | RA-N1 | 同 AC-10A-3，但缺任一候選（含依賴舊答案的 TC）的結論 | 拒絕，列出缺少結論的 TC；CLR 不變 |
| AC-10A-5 | RA-N2 | `--landed-in` 是 CANCELLED 的 run，或該 run 的 revision 沒有引用最新 rev | 拒絕；CLR 不變 |
| AC-10A-6 | RA-N3 | A5（`answer` 追加新 rev）之後，以舊 run 作為 `--landed-in` | 拒絕（舊 run 的 revision 引用的是舊 rev）；CLR 不變 |
| AC-10A-7 | RA-P4 | 文件索取單兩項：fulfill 第一項（有效名稱比對或人工對應） | 仍是 OPEN／ASKED |
| | | 接續：fulfill 第二項 | **APPLIED** |
| AC-10A-8 | RA-N4 | 同 AC-10A-24（R1003-N2） | 不結案；`show` 顯示失效項目和原因 |
| AC-10A-9 | RA-N5 | 答案 `no_change`，但有引用（`--path a7`） | 拒絕（同 AC-10A-38、39） |
| AC-10A-10 | RA-N6 | agent 執行 `apply` | 拒絕；CLR 不變 |
| AC-10A-11 | RA-P5 | bug 流程：BugDraft 以明確 SourceRef 引用 CLR → A4 → bug run COMPLETED → `apply --path a6 --landed-in <bug run>` | **APPLIED** |

**R1002：採用目標**

| AC | fixture | 前置條件／情境 | 預期結果 |
|---|---|---|---|
| AC-10A-12 | R1002-P1（原題） | CLR 原題 REQ-011／Q1；revision 以它解決 REQ-011／Q1；run COMPLETED；`apply --path a6 --target <REQ-011#Q1>`，候選 (a)(b)(c)(d) 都有結論 | 解析出一個目標；**APPLIED** |
| AC-10A-13 | R1002-P2（跨需求） | 人以 `applicability add` 把答案用到 REQ-012／Q2（記錄本次 basis）；新 revision 以它解決 REQ-012；run 只處理 REQ-012 | 解析出 REQ-012／Q2 的目標；`--target` 確認；run 範圍檢查依 REQ-012 → 通過；(b) 掃描 REQ-012／Q2 中依賴舊答案的 TC |
| AC-10A-14 | R1002-P3（跨 area） | 答案經 applicability 用到同 product、另一個 area 的 spec | 候選掃描範圍包含該 area；那裡依賴舊答案的 TC 被列出 |
| AC-10A-15 | R1002-N1 | run 含原題 REQ-011，但目標 REQ-012／Q2 中有一張依賴舊答案的 TC 沒有結論 | 拒絕，列出該 TC |
| AC-10A-16 | R1002-N2 | 解析出兩個目標，只 `--target` 一個，另一個沒有處理 | 拒絕，列出遺漏的目標 |
| AC-10A-17 | R1002-P4 | 同 AC-10A-16，另一個用 `--defer-target …=理由` | 通過；landing 記錄延後的目標與理由；`clarification show` 列出；延後目標的單位仍被掃描 |
| AC-10A-18 | R1002-N3 | `--target` 指定一個不存在於解析結果的目標 | 拒絕 |
| AC-10A-19 | R1002-N4 | 沒有 applicability 就把答案用到 REQ-012（在 G-SPEC 時） | X16 FAIL；不會成為採用目標 |

**R1003：文件項目對應證據**

| AC | fixture | 前置條件／情境 | 預期結果 |
|---|---|---|---|
| AC-10A-20 | R1003-N1 | 缺「角色與權限」「手冊 7.1」兩項；兩項都用已宣告、但不相關的 reference P，不附 `--mapping-reason` | 名稱比對不成立 → 拒絕 |
| AC-10A-21 | R1003-P1 | 缺「後台角色與權限_spec_vNN.md」，fulfill 用外部檔名「後台角色與權限_spec_v02.md」的文件 | 名稱比對成立 → fulfilled |
| AC-10A-22 | R1003-P2 | 別名：缺「手冊 7.1.1 角色說明」，fulfill 用後台管理員系統 v03，附 `--mapping-reason "手冊第七章即後台管理員系統 spec"` | 人工對應 → fulfilled；紀錄含理由與執行者 |
| AC-10A-23 | R1003-P3 | 一份文件補兩項，各自 fulfill | 兩筆 fulfillment；兩項 fulfilled → APPLIED |
| AC-10A-24 | R1003-N2（RA-N4） | 兩項用不同的文件；第一項 fulfilled 之後，以正式的 `spec reference remove` 移除它的宣告；再 fulfill 第二項 | 第一項依保存的 `target_pin` 和目前 decl_rev 重新驗證 → 失效 → 不結案；`show` 顯示原因；證據可由保存資料重現 |
| AC-10A-25 | R1003-P4 | 接續 AC-10A-24：重新宣告（新的 decl_rev）並重新 fulfill 第一項 | **APPLIED** |

**R1004：關鍵字與掃描紀錄**

| AC | fixture | 前置條件／情境 | 預期結果 |
|---|---|---|---|
| AC-10A-26 | R1004-N1 | 某 TC 沒有掛 CLR 的 requirement、也沒有 decision_refs，但 expected 含「進行中」；apply 帶 `--keyword 進行中`，但沒有給它結論 | 拒絕，列出該 TC |
| AC-10A-27 | R1004-P1 | 接續：補上該 TC 的結論 | 通過；landing 有該關鍵字和這張 TC（含版本與 sha256） |
| AC-10A-28 | R1004-P2 | `impact` 產生 S1 → 某張候選 TC 被修訂（active_version 改變）→ `apply --scan S1` | 鎖內重新掃描 → 顯示差異 → 以新版本為準要求結論；landing 保存最新版本 |
| AC-10A-29 | R1004-N2 | 沒有 `--keyword`、`--scan`、`--no-keyword-reason` | 拒絕 |
| AC-10A-30 | R1004-P3 | `--no-keyword-reason "PM 答案只影響 REQ-012 的單一欄位，requirement 候選已涵蓋"` | 通過；理由記錄在 landing |

**A6b、第一批 A4 範圍**

| AC | fixture | 前置條件／情境 | 預期結果 |
|---|---|---|---|
| AC-10A-31 | RA-P6 | bug reject 路徑：RESOLVE_AMBIGUITY reject 的 `resolutions` 條目內部 source 引用 CLR 最新 rev；bug REJECTED、run COMPLETED；沒有 BugDraft 引用 → `apply --path a6b --landed-in <bug run> --target <reject 決議條目>` | A6b → **APPLIED** |
| AC-10A-32 | RA-N7 | 第一批中，BugDraft 沒有提供 SourceRef | 不觸發 A4（舊行為）；之後沒有採用目標，人依實際狀況選 A7（AC-10A-36、37）或 A10 |

**文件與查詢**

| AC | 情境 | 預期結果 |
|---|---|---|
| AC-10A-33 | 檢查 `docs/decisions/` | ADR-010 存在，內容符合 §10，並列出 §13 的已知限制；ADR-008 有指向 ADR-010 的狀態註記 |
| AC-10A-34 | 對含 `deferred`、`retire_planned` 結論與延後目標的 APPLIED CLR 執行 `clarification show` | 列出這些 TC、延後目標及各自理由 |
| AC-10A-35 | 鎖被持有時執行 `clarification stale-tcs <CLR>` | 照常執行（不取鎖）；不寫任何檔案；輸出開頭附「不保證完整」的說明 |

**R1101：apply 三分支**

| AC | fixture | 前置條件／情境 | 預期結果 |
|---|---|---|---|
| AC-10A-36 | R1101-P1（= RA-P7） | 開 CLR → `ask` → `answer --resolution no_change`，沒有任何引用 → `impact --keyword …` → `apply --path a7 --scan <id> --tc-conclusion …（背景候選）--impact-reviewed …` | **APPLIED**；landing 的 `path` 是 a7 |
| AC-10A-37 | R1101-P2 | `answer --resolution out_of_scope`；背景候選為零；`--no-keyword-reason …` | **APPLIED** |
| AC-10A-38 | R1101-N1 | `no_change`，但某張核准單的 approve 決議 `resolutions[0].source` 指向本 CLR rev 0（approval 包裝） | 拒絕，列出 APR 和條目 |
| AC-10A-39 | R1101-N2 | `no_change`，但某張 SUPERSEDED 的 TC 版本 `decision_refs` 曾引用 rev 0 | 拒絕（全部歷史） |
| AC-10A-40 | R1101-N3 | `--path a7` 卻帶了 `--landed-in` | 拒絕 |
| AC-10A-41 | R1101-N4 | CLR 是 INCORPORATED，卻用 `--path a7` | 拒絕（路徑和狀態不符） |
| AC-10A-42 | R1101-P3（A6 回歸） | RA-P3 帶 `--path a6` | **APPLIED** |
| AC-10A-43 | R1101-P4（A6b） | RA-P6 帶 `--path a6b --target <reject 決議條目>` | **APPLIED** |
| AC-10A-44 | R1101-N5（A6b） | 條目的 source 指向舊 rev，或 scope 不符，或條目不是 reject 決議中的條目 | 拒絕 |
| AC-10A-45 | R1101-N6 | 普通的 RESOLVE_AMBIGUITY reject（條目沒有 source）被當成 A6b 證據 | 拒絕 |
| AC-10A-46 | R1101-N7 | 在 G-SPEC 中，以 reject 核准單作為 approval 型 SourceRef | X15 FAIL（只接受 approve 或 override） |

**R1102：跨 product 的目標**

共用前置流程（全部以測試 root 的正式指令建立）：
1. `spec import`：product A 的 spec SA（area X）、product B 的 spec SB（area Y）；以正式流程建立兩邊的 ACTIVE TC（spec-to-testcase run，經 ACTIVATE approve 後 COMPLETED）。
2. 在 SA 開 CLR-1（原題 SA 的 REQ-011／Q1）→ `ask` → `answer`（`requirement_clarified`）。
3. product A 的落地：spec-change-impact（或 spec-to-testcase）run RA，對 SA 寫入新 revision，以明確 SourceRef 引用 CLR-1 rev 0 解決 REQ-011／Q1 → A4 → INCORPORATED → RA 依正式流程完成 → COMPLETED。
4. product B 的採用：`applicability add`（CLR-1 rev 0 → SB 的 REQ-B1／Q1，記錄 SB 本次的 basis_hash，由人確認）→ run RB 對 SB 寫入 revision，以明確 SourceRef 引用 CLR-1 rev 0 → A4' → RB 依正式流程完成 → COMPLETED。

| AC | fixture | 類型 | 前置條件／情境 | 預期結果 |
|---|---|---|---|---|
| AC-10A-47 | R1102-P1 | apply 正例 | 同 product、跨 area（同 AC-10A-14） | 兩個 area 都掃描 |
| AC-10A-48 | R1102-P2 | 目標解析正例 | 前置 1～4 → 解析採用目標 | 得到兩個目標：`SA@ver:REQ-011#Q1`（product A）、`SB@ver:REQ-B1#Q1`（product B） |
| AC-10A-49 | R1102-N1 | apply 反例 | 同 AC-10A-65，但 `--landed-in RB`（只含被延後的 SB 目標），沒有 RA | 拒絕（RB 不含已確認的目標）；CLR 不變 |
| AC-10A-50 | R1102-P3a | **impact 掃描正例，不是 apply 正例** | 前置 1～4 → `impact CLR-1 --target <SB 目標> --keyword …` | 掃描紀錄的 `scan_units` 含 `(B, Y)`；SB 中依賴舊答案的 TC 被列為候選；不宣稱 apply 或 APPLIED |
| AC-10A-51 | R1102-P4 | 掃描正例 | 不同 product、相同 area 名稱 | 兩個單位分開掃描，不因 area 名稱相同而合併 |
| AC-10A-64 | R1102-N2 | apply 反例 | 前置 1～4 → `apply --path a6 --landed-in RB --defer-target <SB 目標>=<理由> …`（沒有任何 `--target`） | 拒絕：RB 不含任何已確認的目標；而且 SA 目標既沒有確認也沒有延後。CLR 不變 |
| AC-10A-65 | R1102-P5 | **完整 A6 成功正例** | 前置 1～4 → `apply --path a6 --landed-in RA --target <SA 目標> --defer-target <SB 目標>=<理由> --keyword … --tc-conclusion …（含 SA、SB 兩邊的全部候選）--impact-reviewed … --by <人>` | RA 是 COMPLETED、含已確認的 SA 目標、範圍包含 REQ-011；SB 目標被延後；`scan_units = {(A, X), (B, Y)}`；SB 的候選仍被掃描、每一張都有結論 → **APPLIED**；landing 記錄確認的目標、延後的目標和理由、兩個掃描單位、全部候選和結論。不要求被延後的 SB 另有 landed-in |
| AC-10A-66 | R1102-N3 | apply 反例 | 同 AC-10A-65，但 SB 中一張依賴舊答案的 TC 沒有 `--tc-conclusion`（先以 `impact` 掃描紀錄斷言該 TC 的 ID 和版本在候選中） | 拒絕，列出該 TC；拒絕訊息中重新掃描的候選仍含該 ID；CLR hash 不變 |
| AC-10A-67 | 文件豁免 ① | 兩項文件：第一項已有效 fulfilled；核准的 `waive_missing` 只豁免第二項 | 核准後執行最後判定 → **APPLIED**；landing 只有一筆；第二項記為 waived |
| AC-10A-68 | 文件豁免 ② | 兩項文件：第一項已有效 fulfilled；核准的 `waive_missing` 涵蓋兩項 | 不是 A9（已有有效 fulfillment）→ 最後判定 **APPLIED** |
| AC-10A-69 | 文件豁免 ③ | (a) 兩項都沒有 fulfillment，核准的 `waive_missing` 涵蓋兩項；(b) 第一項曾 fulfilled，但其 reference 後來以正式 `spec reference remove` 移除（重新驗證失效），核准的 `waive_missing` 涵蓋兩項 | (a) **A9 WITHDRAWN**；(b) 依重新驗證沒有有效 fulfillment → **A9 WITHDRAWN**（以重新驗證的結果分類，不看歷史紀錄是否存在） |

- 執行順序：P2 → P3a → N2 → N1 → N3 → 最後 P5；每個反例之後斷言 CLR 檔的 hash 不變；執行期間測試 root 中沒有其他業務改動。

**R1103：名稱有效性**（文件一律以正式 `spec import` 建立）

| AC | fixture | 前置條件／情境 | 預期結果 |
|---|---|---|---|
| AC-10A-52 | R1103-N1 | title 為「　 」（全形加半形空白）、外部檔名不相關的文件 P，不附理由 | 沒有有效名稱可以比對成立 → 拒絕 |
| AC-10A-53 | R1103-N2 | 外部檔名是「_v02.md」（去掉版本後為空），title 也是空的 | 拒絕 |
| AC-10A-54 | R1103-P1 | 外部檔名「後台角色與權限_spec_v02.md」→ n1 =「後台角色與權限_spec」；缺項引用「後台角色與權限_spec_vNN.md」 | 比對成立 |
| AC-10A-55 | R1103-P2 | title「後台角色與權限」完整出現在缺項的 `cited_at.text` 中 | 比對成立 |
| AC-10A-56 | R1103-P3 | 名稱無效，但附 `--mapping-reason` | human_mapping，fulfilled |
| AC-10A-57 | R1103-P4 | 見第 2 章（同一條，以第 2 章為準） | — |

**R1104：最終關鍵字與 scan 驗證**

| AC | fixture | 前置條件／情境 | 預期結果 |
|---|---|---|---|
| AC-10A-58 | R1104-N1 | `impact`（沒有關鍵字）產生 S1 → `apply --scan S1`，沒有理由 | 拒絕 |
| AC-10A-59 | R1104-P1 | 同上，加上 `--no-keyword-reason …` | 通過；landing 保存理由和 scan_id |
| AC-10A-60 | R1104-P2 | 非空的 scan S2（`進行中`）→ `apply --scan S2` | 關鍵字模式；在鎖內重新掃描 |
| AC-10A-61 | R1104-N2 | 非空的 scan，又加上 `--no-keyword-reason` | 拒絕 |
| AC-10A-62 | R1104-P3 | S2 在 rev 0 時建立；`answer` 追加 rev 1（A5）並重新納入（A4）→ `apply --scan S2` | 只沿用關鍵字；目標依 rev 1 重新解析；landing 記錄 `scan_reused: keywords_only` |
| AC-10A-63 | R1104-N3 | `--scan` 指向另一張 CLR 的紀錄 | 拒絕 |

#### 12.4 第一批整體驗收 AC-A-B1-1～17

（與其他章重疊的項目照列；完整定義以各章為準。）

| AC | 內容 | 預期結果 |
|---|---|---|
| AC-A-B1-1 | critical 端到端：RA-P1 → P2 → P3 | 每個停點都斷言 CLR 狀態（ANSWERED → INCORPORATED → APPLIED）；沒有提前 APPLIED |
| AC-A-B1-2 | 驗證失敗 | 不寫業務檔；只允許兩種診斷寫入（`gate_results` 追加和 task 回 READY，以及一個 audit 事件檔） |
| AC-A-B1-3 | 故障恢復表每一列，以及每種操作類型的中止加續做（完整清單見操作執行章，含本章 §8 的項目） | 依恢復規則續做到 post_state；不產生重複業務物件 |
| AC-A-B1-4 | 舊資料唯讀複本移轉 | schema：非逐位元 legacy 複本的新增／修改檔全部 PASS；legacy 複本（R000）只允許繼承原檔既有的失敗；不新增其他失敗（baseline failure 清單與比對規則見附錄 A 6-38）；R000 的 hash 等於原檔；`_skip` 的預期結果（SITELIST v0.6 為 false）；RUN-20261002-001 的 sidecar；RUN-20260914-001 三種處理方式；TC sidecar（96、44、57 條）；CLR rev 0；`audit.legacy.log` 逐位元等於原 `audit.log` |
| AC-A-B1-5 | 既有測試 | pytest 全部通過、`tools/validate_phase1.py` 通過；數量以實際收集到的為準 |
| AC-A-B1-6 | S1（Q）→ S3 | 全程只用第一批的指令即可完成 |
| AC-A-B1-7 | CIA 候選完整性 | 在同一個測試 root 依序執行：DAILYREPORT 現況 96 條分兩組（0.1、0.2 各 48 條，皆為 legacy sidecar R000）→ PASS；同版本連續兩輪（AC-09-28、29）通過；G1～G8 的 7 個反例（AC-09-35～41）各自 FAIL 在對應的檢查 |
| AC-A-B1-8 | manual-test-to-regression | 有 spec 時，以真實流程完整跑到 T6 COMPLETED（含 UPDATE_SUITE_MEMBERSHIP）並產生正式 TC；沒有 spec 時 `run new` 拒絕（AC-09-23） |
| AC-A-B1-9 | 跨 basis、approval 包裝的 effective_basis | AC-08-27～32（跨 basis）成立；effective_basis 解析：approval 包裝解析成條目內的 CLR rev；條目 source 為 null 時是核准本身；條目的 requirement／question 和引用處不同時 X15 FAIL（附錄 A 6-21） |
| AC-A-B1-10 | audit 事件檔與移轉凍結 | AC-07-36～49 成立 |
| AC-A-B1-11 | flock executor | AC-07-64～72（含子程序同步點）、AC-07-77a～77k 與 77e-ctrl、AC-07-78、79 通過 |
| AC-A-B1-12 | CLR 生命週期 fixture | RA 全部（含 RA-P7）、R1002、R1003、R1004、R1101、R1102、R1103、R1104 全部通過，以及文件豁免 AC-10A-67～69（即 AC-10A-1～69） |
| AC-A-B1-13 | 核准決議表 | 4 列的預期結果成立 |
| AC-A-B1-14 | 寫檔 export 與巢狀 executor | AC-07-73～76 通過 |
| AC-A-B1-15 | ADR 與查詢指令 | AC-10A-33～35 通過 |
| AC-A-B1-16 | 三條 apply 路徑 | A6、A6b、A7 各走一次完整的正式流程（RA-P3、RA-P6、RA-P7）；每條路徑的「不接受」輸入都被拒絕（a6b 帶 `--defer-target`；a7 帶 `--landed-in`、`--target`、`--defer-target`） |
| AC-A-B1-17 | 跨 product 的目標 | 以正式流程建立第二個 product，依序驗收 R1102-P2 → P3a（掃描正例）→ N2（只有延後目標時拒絕）→ N3（延後目標的候選缺結論時拒絕）→ P5（完整 A6 成功） |

---

### 13. 已知限制（明列，不屬於需求 A 的保證範圍）

1. 系統**不驗證** `--tc-conclusion` 是否屬實；例如標 `updated` 的 TC 是否真的已更新並核准。由人負責。
2. `deferred`、`retire_planned` 的 TC 和 `--defer-target` 的目標**不會被自動追蹤**；只記錄在 landing，可用 `clarification show` 查詢。`retire_planned` 不代表已退休。
3. 關鍵字由人選擇；換了說法、同義改寫、沒有追溯欄位的間接依賴，可能被漏掃。
4. 一次 apply 確認的 landed-in run，不證明所有 spec 版本、所有 area 的相關 TC 都已完成（不過 a6 的所有採用目標都必須被明示確認或延後）。APPLIED 不代表全部 TC、版本、area 都已完成。
5. 每個 landed-in run 至少含一個已確認的目標，但**不保證每個已確認的目標都各有自己的已完成 run**；人可以確認一個沒有對應 run 的目標（例如判斷它的 TC 都不受影響）。這是人工確認的一部分。
6. APPLIED 之後，新出現的依賴 TC 或新的採用，**不會**自動重新開單或提醒；`stale-tcs` 只是唯讀查詢，依據是 TC 的 `decision_refs`、`requirement_ids` 與最近一次 landing 的關鍵字，不保證完整。
7. 文件的人工對應（`human_mapping`）正確性由人負責；系統不理解文件內容。
8. 第一批中，沒有提供 SourceRef 的 BugDraft 不會觸發 A4。
9. fork 的覆蓋範圍：fork 子程序的鎖隔離只涵蓋經由 Python 的 fork（`os.register_at_fork` 的範圍）；C 擴充模組直接 fork 不在保證範圍內。QAOS 目前沒有這類依賴，並以靜態檢查（AC-07-77g）提示新增的使用（規則見操作執行章）。
10. 以上限制屬於需求 B（如果重啟）的範圍；在需求 B 完成之前，CLR 結案依本章由人逐張確認，這是 Oscar 決定的取捨。


---

## 附錄 A　實作定義與待確認事項的處理

> 各章來源沒有定義、或彼此需要對齊的細節，在本附錄逐項定案，實作與驗收依此為準。
> - **類別 I（實作定義）**：介面、欄位、值域、命名這類細節，由實作決定，不改變需求的行為。
> - **類別 R（需求層釐清）**：會影響行為或驗收範圍的釐清、補充或修正；實作前須經審查確認。
> - **類別 O（待 Oscar 決定）**：業務資料或流程的決定，不阻擋實作。
> 各列的「位置」指本文件的章節。

### A.1 共用與派發（第 1 章）

| # | 項目 | 定案 | 類別 |
|---|---|---|---|
| 1-1 | basis 的閉包範圍與目標的宣告修訂 | basis = `{target: SpecPin, target_decl_rev, closure}`；closure 只取 **normative** 遞移閉包（不含 informative），每個節點帶它自己的 `decl_rev`。basis_hash 與 issue key 使用**同一個** basis（和 3-7 一致）。FIX-09 的「normative 遞移＋直接 informative」閉包只用於派發包、`reference_pins` 與閱讀範圍，不用於 basis。`target_decl_rev` 讓目標自己的宣告變動（即使閉包為空）也反映到 basis_hash 與 `declaration_changed`（第 5 章 §3、§6；AC-09-86、87） | R |
| 1-2 | 需求沒有任何 `rejection_response` 決策點時的 `rejection_contract` | 不產生 `rejection_contract`（不適用），因此不開「拒絕行為未定義」的 CLR；只有存在 `rejection_response` 決策點時才推導 `defined` | R |
| 1-3 | `topic` 受控詞初始清單 | `rejection_response`、`error_code`、`permission`、`boundary_value`、`state_transition`、`display_format`、`calculation`、`data_scope`、`other`；清單定義在 schema，之後以修改 schema 的方式增減 | I |
| 1-4 | `read_scope` 值域 | `full` 或 `sections`（`sections` 時另附章節清單） | I |
| 1-5 | `doc_issues` 的 kind／status | kind：`wording_conflict`、`missing_definition`、`inconsistent_reference`、`typo`；status：`open`、`pending_owner_decision`、`resolved` | I |
| 1-6 | 必須有派發包的 task | 第一批：Spec Analyst、Test Designer、Test Validator、TC Risk Reviewer、Change Impact Analyst；Bug Analyst／Bug Validator 的派發改造屬第二批。`dispatch` 會寫入派發包檔，所以是寫入指令、要取鎖 | I |
| 1-7 | basis 為 undefined、已裁決（E1）的決策點，`known_rules` 能否被 TC 引用 | 不能（採較嚴格的解讀）；TC 只能引用裁決本身 | R |
| 1-8 | `covers` 的資料形狀 | 只定義形狀：`role_scope` 是字串陣列，`["*"]` 代表與角色無關，`*` 不得和具名角色混用；`params` 是物件，值為純量或純量陣列；由 schema 強制。**涵蓋演算法以第 1 章名詞表的 `covers(A, D)` 為準**（A 的每個鍵必須出現在 D 中而且值相等，陣列時 D 的值 ⊆ A 的值；A 沒有的鍵代表不限制）；驗收見 AC-08-35～37 | I |
| 1-9 | preflight 對 legacy revision、以及沒有 revision 的 RESOLVE_AMBIGUITY（Bug Validator 建立）的適用 | 兩者都沿用現行規則：所有掛在核准單上的 CLR 必須已回答；不套用「每個 effective critical 決策點恰好一筆 resolution」 | R |
| 1-10 | E6 的「報告顯示未查證」 | 不實作；E6 維持現行行為 | I |
| 1-11 | agent 自填 `basis_hash` 等推導欄位 | 推導欄位不在 agent 的輸出 schema 中；agent 提交時帶了這些欄位 → Structural FAIL | I |
| 1-12 | 整體 approve／override、但 per_item 全部 reject | 依現行 `engine.py` 行為（推進、沒有 TC 啟用），在核准決議表另列一列說明 | I |
| 1-13 | 核准決議表第 3 列的現行不一致是否另開 QAOS bug | 待 Oscar 決定，不阻擋實作 | O |
| 1-14 | 範例 G 的 landing 形狀 | 以第 6 章 §5.12 的 landing 為準；保留 `at` 欄位 | I |
| 1-15 | clarification 型 SourceRef 只接受 `requirement_clarified`／`spec_updated` 的答案 | 保留（沒有被撤銷，且和 A6 採用目標的 resolution 限制一致） | R |
| 1-16 | 範例中的 ⑧ SPEC ID | 範例 ID 僅供說明（`SPEC-ROLEPERM-001` 為暫定），不是實作或驗收的固定值 | I |
| 1-17 | 第一批的 `gap_unverified` | 第一批沒有引用候選紀錄（FIX-03 屬第二批），`gap_unverified` 等同 `references_status: undeclared` | I |
| 1-18 | Applicability 的定義位置 | 以第 3 章為準；第 1 章只保留簡述並指向第 3 章 | I |
| 1-19 | 缺文件（E3）只由 `reason: unavailable` 的未查參考構成 | 文件索取單至少要有一個引用處（第 3 章 §3.4），未查參考本身沒有引用處。處理：推導為 E3、但決策點沒有 `missing_sources` 時 G-SPEC FAIL。目標正文有提到該參考時，把那一行列入 `missing_sources`；正文沒有提到時不得捏造引用處，run 停下由人處理（重新讀取後取消 run 重新分析，或移除該引用宣告）。依據：`spec reference add` 要求被引用的 spec 已匯入且 hash 相符，所以這種 unavailable 屬於執行問題而不是缺文件。**Oscar 2026-10-07 確認此做法**（不新增 pin 型文件項目） | R |
| 1-20 | `dispatch_packet_sha256` 的位置 | 放在 artifact envelope（所有需要派發包的 task 的產出都帶，SpecAnalysis 的這個欄位即 envelope 欄位）；submit 時必須等於 task 本次 iteration 的派發包，否則 Structural FAIL（沒有派發包、沿用舊 iteration 的派發包都拒絕） | I |
| 1-21 | 派發包的補充欄位與下游的範圍 | 派發包另含 `references_status`、`basis_hash`、`target_decl_rev`、`closure[].required`（depth=1 的 normative），以及 `decision_sources`：綁定 revision（含 pin_groups）中決策點已使用的 SourceRef 身分。下游 agent 的「派發包範圍」＝目標、閉包、決議快照中的同一 answer_rev、本 run 已決的裁決、`decision_sources`、登記的額外 spec | I |
| 1-22 | 派發之後目標或閉包的宣告改變 | G-SPEC 以目前的 basis_hash 核對派發包的 basis_hash，不同 → FAIL；同一 iteration 不能重新派發，處理方式是取消該 run 後重新分析 | R |
| 1-23 | Validator 漏報派發包範圍外的來源 | runtime 在 G-TVAL 以 Validator 自己的派發包重算 Draft 的 SourceRef（`source_refs`、`decision_refs[].basis_ref`）是否在範圍內；有範圍外的來源而報告沒有對該 TC 的 `missing_reference`（blocker 或 major）→ G-TVAL Structural FAIL。TC Risk Reviewer 不擋關，只在契約要求 | R |
| 1-24 | 第一批（P4）的自動開單去重 | issue key 在 P5；P4 以 `(spec_id, spec_version, requirement_id, question_id, kind)` 判斷，有未撤回的同鍵 CLR 就連結（DRAFT 路由時掛到核准單），不重開 | I |
| 1-25 | 豁免後新開的 `spec_question` 指回文件索取單 | `related_clarifications` 的 relation 使用 `waived_document_request` | I |
| 1-26 | 沒有 `rejection_response` 決策點、agent 卻填了 `rejection_contract` | 依附錄 A 1-2 推導為「不產生」，視為和推導值不同 → X8 | R |
| 1-27 | 新資料的 RESOLVE_AMBIGUITY 核准是否 apply CLR | 核准單上屬於新資料需求（revision 中有決策點）的 CLR，核准不再 apply（第 6 章 §3.4，P4 先套用於新資料）；屬於舊資料需求、或核准單沒有綁定 revision 的 CLR，核准前仍必須已回答。同一 revision 同時有兩種需求時兩套檢查並行。**P5 起**舊資料的核准也不再 apply（附錄 A 6-25） | R |
| 1-28 | P4 的 A9 與 A8 | P4 只有核准的 `waive_missing` 這條路徑：列出的項目標為 waived，涵蓋全部項目且沒有有效 fulfillment → WITHDRAWN（system）；`fulfill`、`waive-item` 與 A8 在 P5。狀態機允許 system 執行 OPEN／ASKED → WITHDRAWN，程式只在文件索取單的最後判定使用 | I |
| 1-29 | 推導結果的保存 | 持久化的決策點另存 `derived: {state, effective_level, route, resolved, gap_missing, gap_unverified, resolved_conflict?}` 與 `basis_hash`；G-DESIGN、preflight 讀 revision 中的 `derived`。revision 另記 `dispatch_packet_sha256` 與 `decision_snapshot_hashes: {resolutions, run_decisions}`（派發包兩份快照的 canonical sha256；附錄 A 5-14） | I |
| 1-30 | G-DESIGN 第 1 點的機械判斷 | TC 覆蓋的每一條新資料需求，都必須至少有一筆指向它的 `decision_refs`（expected 依據與 negative／error_guessing 斷言都要標明依賴的決策點；否則依賴 E3～E5 的斷言可以不標而繞過 exploratory 限制）；依賴 E1 決策點的 `decision_refs` 必須有 `basis_ref`；exploratory 的判斷是該 TC 有指向此需求、`needs_human_confirmation: true` 的 assumption。舊資料的「rejection_contract 未定義 → negative 必須 exploratory」規則只用於舊資料 | R |
| 1-31 | preflight 的補充 | 所有條目（不只 critical 決策點）都檢查：每個決策點最多一筆；outcome 必須是該決策點有效狀態允許的（E1 的決策點不接受條目）；條目必須指向綁定 revision 中存在的決策點；`select_interpretation` 的 source 只能是 clarification 型或 null；`waive_missing` 必須列出 `waived`，每一項完全等於該決策點的缺檔（cited_at 的 SpecPin＋line＋name）或未查參考（pin）；`resolutions` 只用於 RESOLVE_AMBIGUITY | I |
| 1-32 | G-SPEC 對 coverage 的檢查 | `coverage.references_status` 必須等於目標版本；`coverage.consulted` 只能是目標或派發包閉包內的 pin；`missing_sources[].cited_at` 的 pin 必須相符，且該行含有 `text`；同一需求的 `question_id` 不得重複 | R |
| 1-34 | approval 型 SourceRef 作為 `defined_by_decision` 的依據 | 只接受 outcome 為 `select_interpretation` 的條目（和 effective_basis 的定義一致）；指向 `waive_missing` 等其他條目 → X12（豁免缺文件不是行為裁決） | R |
| 1-35 | system 撤回 CLR 的範圍 | 狀態機以 `kinds: [document_request]` 限定 system 的 OPEN／ASKED → WITHDRAWN（A9）；其他 kind 只能由人撤回（A10） | I |
| 1-36 | 自動開單的問題文字 | `decision_needed` 至少 5 個字時作為 CLR 的 `question`；較短時改用「需求／question_id（subject）需要決定：<decision_needed>」，`decision_needed` 欄位仍逐字抄寫 | I |
| 1-37 | 新索引與行號的表示 | 同附錄 A 3-24：waiver 的 `resolution_index`、resolution 的 `adopted_side_index`、`cited_at.line`（含豁免項目）、`decision_refs[].basis_ref` 的 `answer_rev`／`resolution_index`，進入索引前一律檢查是整數表示（`type(v) is int`）；`0.0`、`1.0`、`13.0` 這類浮點寫法回報結構錯誤（X14、X11、G-SPEC、G-DESIGN、preflight），不轉換、不截斷、不拋例外。bool 與負數在 schema 層拒絕 | I |
| 1-38 | TC 的 `source_refs` 驗證 | G-DESIGN 以共用 SourceRef 驗證逐筆核對（hash、quote、答案修訂、核准條目，第 3 章 §6），失敗的 Draft 不會 materialize。clarification、approval 型必須和本 TC 某筆 `decision_refs` 的 `basis_ref` 相同，並以那個決策點作為引用處驗證（核准條目的 requirement／question 必須相符；basis_ref 是否為該決策點可用的來源由 §3.6 的檢查決定），不能引用其他需求或其他問題的裁決。spec 型的「目標或閉包內」限制不套用到 Designer 派發時以 `--extra` 登記、完整 SpecPin 相符的 spec（只核對 hash 與 quote）；是否在下游派發包範圍內由 G-TVAL／Validator 判定（1-23） | R |
| 1-39 | 退回或重開後的下游 task | 被退回而失效的下游 agent task（Validator、RR、CIA compare 等）重設為 PENDING、清空本輪產出；它在下一次被推進成 READY、而且目前 iteration 已派發過時進入下一個 iteration，要用新的派發包（不在被 gate 的 task 自己的 gate 操作中改它的 iteration，因為 gate 的請求身分含 iteration，否則中止後無法續做）。舊派發紀錄保留；需要派發包的 task，用其他 iteration 的派發包產出的 artifact 不能提交，也不能在新 iteration 重新評估（同一 iteration 內的重評不受影響）。適用 semantic FAIL 退回、整批核准 reject、RESOLVE_AMBIGUITY 後重開、HUMAN_OVERRIDE 的「再給一次迭代」（被重開的 generator 本身直接進入新 iteration）。NEEDS_DECISION 的 retry 不計入迭代（現行行為），沿用同一 iteration 的派發包；不需要派發包的 task 維持現行行為 | R |
| 1-40 | RR 的 `spec_basis` | 型別化 SourceRef（spec／clarification／approval），G-RISK 以共用驗證核對，並要求在 RR 本次的派發包範圍內；null 仍需 `needs_clarification: true`。clarification、approval 型必須另填 `spec_basis_decision: {requirement_id, question_id}`（Oscar 2026-10-07 決定）：需求在 finding 的 `related_requirement_ids` 內、決策點存在且已定（E1）、依據是該決策點可用的來源（known_rules、resolution 或被採用的一側），並以它作為引用處驗證；spec 型不需要這個欄位。舊的 `{location, quote}` 形狀只保留給派發包之前的舊產出，新產出（task 有派發包）使用 → G-RISK FAIL。RR 仍不判 PASS／FAIL、不擋核准的內容 | R |
| 1-33 | 範例中的 topic | 範例 A、E、F 的 `deletion_policy`、`assignment_scope`、`aggregation_rule` 不在 1-3 的受控清單內；範例只示意形狀，實作與驗收以 1-3 的清單為準 | I |

### A.2 spec 引用與外部來源（第 2 章）

| # | 項目 | 定案 | 類別 |
|---|---|---|---|
| 2-1 | `spec reference` 參數 | `spec reference add <spec_id>@<ver> --ref <spec_id>@<ver> --role normative\|informative [--scope <文字>] --by <人>`；`remove <spec_id>@<ver> --ref <spec_id>@<ver> [--reason] --by <人>`；`declare-empty <spec_id>@<ver> --reason <文字> --by <人>` | I |
| 2-2 | 「只能由人宣告」 | `--by` 必填；`--by` 是 `system` 或 `agent-*` → 拒絕（和 `apply` 相同的 actor 契約檢查；不是身分驗證，見已知限制） （拒絕條件，實作時補對應測試） | R |
| 2-3 | `reference_declarations[]` 每筆欄位 | `{decl_rev, references（完整快照）, references_status, reason?, by, at, op_id}`；每次 add、remove、declare-empty 都追加一筆、`decl_rev` 加一 | I |
| 2-4 | `references_status` 的轉換 | add → `declared`；移除最後一個引用 → 必須帶 `--reason`，狀態成為 `declared_empty`；`declared_empty` 之後 add → `declared`；三種操作都產生新的 `decl_rev`；因為 revision 記錄 `target_decl_rev`（附錄 A 1-1），所以即使閉包為空，也都會觸發 `declaration_changed`（AC-09-86、87） | R |
| 2-5 | 直接層 RefNode 的保存 | `references[]` 存 `{spec_id, spec_version, content_hash, role, scope?}`；`decl_rev`、`depth` 只在閉包展開時計算（直接層 depth = 1） | I |
| 2-6 | `spec import` 的 source 參數 | `--package`、`--external-filename`、`--external-version`、`--external-effective-date`、`--external-commit`；`source_bytes_sha256` 由實際匯入的檔案計算 | I |
| 2-7 | `spec metadata upgrade` 參數 | 同 2-6 的 source 參數，加 `--original-file`、`--reason`、`--by`；原檔 hash 和 `content_hash` 不同時，說明寫在 `metadata_history` 該筆的 `note` | I |
| 2-8 | AC-02-6「目標或依據」的範圍 | 指：run 的目標 spec 版本、RM revision 的目標 SpecPin、TC 版本的 spec pin。**不含**只出現在其他版本引用閉包中的情況（否則手冊類文件被引用後就無法事後設為 `reference_only`） | R |
| 2-9 | title 正規化後為空的警告 | 匯入成功；stderr 輸出「警告：title 正規化後為空，文件名稱比對不會使用這個 title」，並寫入一筆 audit 事件；不寫入 `spec.yaml` | I |
| 2-10 | FIX-03 的細節（規則清單維護者、`candidates_ack` 結構、同名不同 hash 的分類、規則版本編號） | 屬第二批，於第二批設計時定案 | I |
| 2-11 | remove 的紀錄 | 記在 `reference_declarations` 的該筆（by、at、reason） | I |
| 2-12 | P2 實作補充的介面 | `spec import` 另有 `--package-file <zip\|manifest>`（計算 `package_sha256`；`--package` 是名稱）與 `--analysis-policy`（手冊等文件以 `reference_only` 匯入）；新匯入的條目一律帶 `source`（至少 `source_bytes_sha256`），不是 legacy 條目；`--external-filename` 不給時不做同名比對。`reference_declarations[]` 每筆另記 `action`（add／remove／declare_empty）。add 時拒絕重複宣告與引用自己；目前有引用時拒絕 `declare-empty`（先 remove）。`metadata_history[]` 每筆 `{at, by, reason, note?, op_id, changes: {欄位: {old, new}}}` | I |

### A.3 CLR 欄位、有型別來源、去重與開單關卡（第 3 章）

| # | 項目 | 定案 | 類別 |
|---|---|---|---|
| 3-1 | 開單關卡沒有 AC | 新增 **AC-07-101**（agent 或 system 開單時缺決策點欄位 → 拒絕、不寫業務檔）、**AC-07-102**（人工 `clarification new` 沒有 `--consulted`、也沒有 `--no-source-check --reason` → 拒絕；帶 `--no-source-check --reason` → 成立，理由寫入 history）。內文見第 3 章 §15.2 | R |
| 3-2 | legacy 同需求標 `possible_duplicate` 沒有 AC | 新增 **AC-07-103**：同 requirement 已有 legacy CLR（沒有 issue key）時新開 → 新單標 `possible_duplicate`，並寫一筆 audit 警告事件 | R |
| 3-3 | AC-08-20～26、27～32 與 fixture 的對應 | 依 fixture 表的列序一對一（第 3 章已列） | I |
| 3-4 | AC-08-16 與 AC-08-32 | 保留兩條：AC-08-16 驗 QuestionScope 的涵蓋，AC-08-32 驗 basis_hash；AC-08-16 的預期補上「basis_hash 也相符時 PASS」 | I |
| 3-5 | AC-08-4 的 PASS 範圍 | 分開兩層：SourceRef 本身的驗證（hash、quote）與作為本次決策依據時的 X16。AC-08-4 驗前者；X16 的成功與失敗例見 AC-08-38 | R |
| 3-6 | 新答案的 basis | `answer` 時記錄：CLR 的 `spec_id@spec_version` 的 SpecPin ＋ 該時點的 normative 閉包（各節點的目前 `decl_rev`） | I |
| 3-7 | issue key 的 basis 與 basis_hash 的閉包 | issue key 直接使用和 basis_hash **同一個完整 basis 物件**（含 `target_decl_rev`，排序與序列化方式相同；第 3 章 §4.1）。驗收 AC-07-104 | R |
| 3-8 | landing 的類型 | 只有 `incorporated`、`applied`；文件項目以 `fulfillments[]` 記錄，不另設 landing 類型 | I |
| 3-9 | CLR 指向掃描紀錄的欄位 | `scan_ids[]`（掃描紀錄的路徑可由 scan_id 推得） | I |
| 3-10 | 沒有使用 `--scan` 時的 `scan_reused` | `none` | I |
| 3-11 | `evidence_addenda` | 每筆 `{source: SourceRef, note, by, at, op_id}`；指令 `clarification addenda add <CLR> --source <SourceRef> --note <文字> --by <人>` | I |
| 3-12 | `applicability add` 中人確認 basis_hash | CLI 先計算並顯示本次的 basis_hash；人必須以 `--confirm-basis <hash>` 帶入相同值才寫入；`--target <spec_id>@<ver>` 決定 scope 的 spec | I |
| 3-13 | landing 是否含 `by`、`impact_reviewed` | 含；同時寫入 history | I |
| 3-14 | 人工開單（入口 C）的參數與去重 | `clarification new` 增加 `--kind`、`--question-id`、`--subject`、`--role-scope`（可重複）、`--param k=v`（可重複）、`--topic`、`--level`、`--known-rule`（可重複）等參數；人工開單同樣計算 issue key 並套用去重規則 | I |
| 3-15 | `topic` 清單 | 同 1-3 | I |
| 3-16 | `related_clarifications` 的 `same_topic_other_scope` | 不實作（去重規則沒有使用） | I |
| 3-17 | clarification 型 SourceRef 指向 WITHDRAWN 的 CLR | 新提交的 SourceRef 指向 WITHDRAWN 的 CLR → FAIL（任何位置） | R |
| 3-18 | `decision_revised` 的「重新判定」 | 新的 revision 中，該決策點不得再以舊的 answer_rev 為 effective_basis：必須改引用最新 rev，或標為未解決（依推導成為 E3～E5）；否則 G-SPEC FAIL | R |
| 3-19 | `role_scope` 值的格式 | 和 `subject` 相同的字元限制，或 `*` | I |
| 3-20 | `answer_sha256` | 答案文字（UTF-8）的 sha256 | I |
| 3-21 | 第一批的 `refs.py` | 只做 SourceRef 的解析與驗證函式；`refs report` 屬第二批 | I |
| 3-22 | `defined_by_decision` 另附的補充 clarification 來源 | 也必須通過 X16（比「至少一筆」更嚴格） | R |
| 3-23 | P2 實作補充的定義 | 答案修訂每筆另記 `op_id`；回答時 CLR 的 spec 版本必須已匯入（無法建立 basis → 拒絕回答，不寫入）。`applicability[]` 與答案修訂以外的紀錄的 `sha256` 為該筆紀錄（不含 `sha256` 欄位）的 canonical sha256。`applicability add` 的 `answer_rev` 必須已存在於 `answer_revisions`（舊 CLR 的 rev 0 由移轉或下一次 `answer` 寫入）；`--params` 以 JSON 物件給（`{}` 明寫）。`evidence_addenda` 的來源是 SourceRef（依 CLR 的 spec 版本驗證）或 document 型 `{type: document, file_name, sha256, package_sha256?, location}`。開單時給了決策點欄位就驗證（`known_rules`／`conflict_sides` 的 SourceRef、`coverage` 中的 SpecPin、文件索取單的引用處），並由 `missing_sources` 產生 `document_items`（`D01`…）。第 6 章 A3（ANSWERED → ANSWERED 追加答案修訂）在 P2 加入狀態機 | I |
| 3-24 | SourceRef 索引的表示 | `answer_rev`、`resolution_index` 必須是 JSON／YAML 的整數表示且不小於 0；boolean、字串、`0.0` 這類浮點寫法一律是形狀錯誤（不轉換、不截斷）。`validate`、`x16`、`effective_basis`、`resolution_entry` 的入口都先做同一形狀檢查，核准單條目內部的來源同樣適用 | I |
| 3-25 | 舊格式需求（E6）的自動開單與開單關卡 | 沒有決策點的舊格式需求維持現行的入口 A、B（`legacy_e6`），不要求決策點欄位；有決策點的新資料一律經關卡（欄位齊全並通過驗證）。其他 agent／system 呼叫 `clarification.new()` 都受關卡約束。`legacy_e6` 在開單時驗證：呼叫者是 agent／system、帶 requirement_id，而且該需求在 spec 版本最新的 revision（移轉前為需求檔）中存在、沒有決策點；否則拒絕 | R |
| 3-26 | 需求層 `source_refs[]` | 需求層只接受 spec 型（G-SPEC 以 X10 驗證）；clarification、approval 型必須放在決策點的 `known_rules`、`resolution`（那裡才有可核對的引用處，對應附錄 A 1-38 的綁定規則） | R |
| 3-27 | 人工開單的查閱證據 | `--consulted <spec_id@ver>` 的 pin 寫入 CLR 的 `coverage.consulted`；入口 D（以人為 `--by`）給了決策點欄位、而且 `coverage.consulted` 非空時也算有查閱證據；`--no-source-check --reason` 的理由寫在 OPEN 那筆 history 的 note | I |
| 3-28 | 沒有 issue key 的 CLR | issue key 只在 kind、requirement_id、topic、subject、params、role_scope 都有值時計算（basis 由 CLR 的 spec 版本建立）；欄位不齊的新單（例如人工只填問題）沒有 issue key，去重規則 4 把它和移轉前的舊單一樣看待 | I |
| 3-29 | key 相同時的連結 | `clarification.new()` 回傳既有的 CLR（帶 `_linked: true`，不寫回）並寫一筆 `LINK_CLARIFICATION` audit；入口 B 把它加進核准單的 impact；CLI 顯示「已連結既有單」 | I |
| 3-30 | agent／system 開單的 coverage | 必須是完整的 Coverage：`references_status`、`consulted[]`、`unconsulted_normative[]`、`missing_sources[]`、`waivers[]` 五個欄位都在，清單欄位是清單；`known_rules` 必須是清單（可以是空的）。人工開單（入口 D）的 coverage 可以只有 `consulted` | I |
| 3-31 | AC-08-16 的需求 ID | 維持 REQ-DAILYREPORT-012。CLR-DAILYREPORT-010 自身的 `requirement_id` 是 REQ-DAILYREPORT-011（「已兌現金額」的歸屬日），它的 APPLIED 紀錄同時涵蓋 REQ-012（現金淨收）；AC-08-16 驗的是把 CLR-010 的答案以人建立的 applicability 套用到 REQ-012（`report.cash_net.semantics`），和 CLR 自身範圍是不同角色。M1（2026-10-08）以實際資料確認。2026-10-08 Oscar 決定（D-M1-3） | I |

### A.4 executor（第 4 章）

| # | 項目 | 定案 | 類別 |
|---|---|---|---|
| 4-1 | AC-07-13～18 與 fixture | 13 = op-P1、op-P2；14 = op-N1、op-N2；15 = op-N3；16 = op-N4；17 = op-N5；18 = op-N6 | I |
| 4-2 | AC-07-20、21 | **撤銷**：原驗收對象（`audit.log` 追加時的檔尾殘段）在事件檔機制下不存在；「不碰其他操作的檔案」由 AC-07-38、39 驗收 | R |
| 4-3 | AC-07-22～29 與操作類型 | 22 = submit_gate；23 = approve；24 = complete_run、cancel_run；25 = 寫檔 export、`audit render`；26 = `maintenance start`、`maintenance end`；27 = `impact`、`apply`、`fulfill`、`waive-item`；28 = `migrate`、`migrate rollback`、metadata upgrade；29 = `applicability_add` | I |
| 4-4 | AC-07-36～41、43～49、64～72、73～76 的對應 | 依 fixture 表的列序（第 4 章已列） | I |
| 4-5 | AC-07-36～38、40 的前置狀態 | 正式流程中，flock 與第 3b 步不允許兩份未完成計畫交錯，也不允許兩個寫檔 render 同時執行。改為**防禦性測試**：以測試專用的故障注入放入「另一個 op」的事件檔或暫存檔，驗證本操作不碰它們；AC-07-40 改為正式序列：A 中止 → B 被 3b 拒絕 → 兩種入口續做 A 完成 → B 正式寫入事件 → 以新請求 render C，C 包含全部事件；A 續做不重算輸入 | R |
| 4-6 | 計畫路徑的 `<scope>` | 操作的目標有 run 時 `<scope>` 是該 run_id（`operations/<run_id>/<op_id>.yaml`），否則是 `_global`。登錄紀錄與狀態紀錄一律在 `operations/_global/` | I |
| 4-7 | `action` 列舉 | 在 `operation-plan.schema.json` 中列舉，涵蓋第 4 章 §16 的全部操作類型，以及 `diagnostic`、`dispatch`、`spec_import`、`spec_reference`、`evidence_add`、`execution_import`、`manual_new`、`bug_lifecycle`、`tc_retire`、`tc_revise`、`clarification_*` 等現有寫入指令 | I |
| 4-8 | PlanStep 的 `kind` | PlanStep 帶 `kind`（`business`、`event`、`control`、`index`、`status`） | I |
| 4-9 | 驗證失敗時的診斷寫入 | **不建立操作計畫**（維持第 4 章 §13）：在持有鎖的 executor context 中，直接寫入允許的兩種診斷（task 的 `gate_results` 追加與狀態回 READY；一個 audit 事件檔）。`adhoc-<uuid>` 只用作這個事件檔的身分（檔名 `adhoc-<uuid>-0`），不是計畫的 op_id，不產生登錄、狀態或完成紀錄，也不會成為未完成計畫 | I |
| 4-10 | 每個操作 render 哪些 `audit.log` | 本操作有事件的每個 run 的 `audit.log`，加上全域 `runs/_audit.log` | I |
| 4-11 | AC-07-97④（改寫既有登錄紀錄）的檢查時點 | 第 0 步不掃描所有登錄紀錄。改為：該 op 被續做時由 V1 拒絕；`operation list` 與後續操作盤點（`later_ops_snapshot`）讀到內容不符的登錄紀錄時拒絕並回報。AC-07-97④ 的預期改為「涉及該紀錄的續做與盤點被拒絕並回報衝突」 | R |
| 4-12 | `operation list --incomplete` | 提供（只列未完成計畫） | I |
| 4-13 | `migrate` 是否為控制類操作 | 是：記錄 `admitted_state`、`to_state`、`resume_states`；不列入後續操作盤點 | I |
| 4-14 | 3b 拒絕前是否顯式釋放鎖 | 是（明確 `release` 後才回報拒絕；結果和程序結束相同） | I |
| 4-15 | Permission Guard 失敗（越權提交：`created_by` 不符、無權產出該型別、寫入路徑不在 `write_paths`） | **不屬於** §13 的「驗證失敗」，以正常操作（操作計畫）寫入：task 追加 `gate_results` FAIL 與 `permission_violations`，task 與 run 轉 FAILED，記 `PERMISSION_VIOLATION` 事件。被提交的 artifact 不修改。其餘結構驗證失敗（schema、引用、狀態、payload 前置）才是 §13 的診斷寫入（Oscar 2026-10-07 決定維持既有行為） | R |
| 4-16 | §13 診斷寫入的允許範圍 | 只寫一份 run.yaml 與最多一個事件檔，其他任何檔案都不寫（含被提交的 artifact、核准單）。run.yaml 中：run 本身只有 `updated_at` 可以變，而且只能是本次 executor 的時間；只有一個 task 變更，限 `gate_results`（只追加一筆本次的 structural FAIL，記錄被拒的 `artifact_id`）、`history`（只追加，每筆是本次時間、依 task 狀態機合法且前後相接）、`status`（最後必須是 READY）、`started_at`（只能設為本次時間，task 重新進入 RUNNING 時）。超出範圍 → 拒絕，不寫入。同一 task 連續多次失敗仍只寫診斷，不自動開核准單；要放棄由人執行 `run cancel`。越權提交不屬於診斷（見 4-15） | I |
| 4-17 | ID 配發的時點（§7.3） | 計數器的更新是計畫中的一步，ID 在擷取時配發、由計畫固定：計畫保存之前中止時計數器不前進（不留空號）；計畫保存之後中止時續做沿用計畫的 ID；不會重複使用 ID。**Oscar 2026-10-07 定案**（Codex 技術上同意），已同步第 4 章 §6.2、§7.1～7.3、恢復表 9b 與 AC-09-23 | R |
| 4-18 | 計畫保存前中止的殘留（AC-07-68、98d） | 保存計畫時，本 op 的任何入口（op 目錄、認領檔、寫入清單、staging.d 與 scope 目錄中本 op 的計畫暫存）在清理後仍存在 → 不取得擁有權，拒絕，不建立任何東西（認領檔不能追溯取得它建立之前就存在的檔案）。否則依序：以 O_EXCL 建立零位元組認領檔 `operations/_global/staging.d/<op_id>.claim` → 以 link-create 建立寫入清單 `staging.d/<op_id>.yaml`（op_id、scope、時間、將新建的內容檔 sha256）→ 寫內容檔 → 保存計畫 → 刪清單 → 刪認領檔。每個寫入請求取得鎖後：先核對「有登錄紀錄卻沒有計畫檔」的 op，有就拒絕、不做任何清理；認領檔是擁有權的根據，沒有認領檔的內容一律不刪（看起來像 op 目錄的保留並回報）。有認領檔者先核對全部待刪路徑（從 root 起每一層都不是 symlink、清單列出的內容檔 hash 相符），全部通過才刪：計畫未保存時刪清單列出的內容檔、其短寫暫存、該 op 的計畫暫存與因此變空的目錄；最後刪 staging.d 中的暫存、清單、認領檔（計畫已保存時只刪這些）。任何一項不符 → 證據衝突，不刪任何東西。不取鎖的外部程式同時修改這些路徑，不在保證範圍內 | I |

### A.5 revision 與移轉（第 5 章）

| # | 項目 | 定案 | 類別 |
|---|---|---|---|
| 5-1 | R001 之後的檢視與索引 | `requirements.yaml`（檢視）= 最新 revision 的需求文件內容，帶 `revision` 欄位；revision 檔另含 `{revision, parent, reason, target_decl_rev, reference_pins, source_artifact_id, created_at, op_id}`。`revisions/index.yaml`：`{revisions: [{revision, path, sha256, created_at, op_id, reason}]}`。R000 是 legacy `requirements.yaml` 的逐位元複本，移轉時不修改 legacy 檔（N1）；R000 的 `target_decl_rev`、`reference_pins` 存在不可變的 `R000.meta.yaml`（第 5 章 §3，附錄 A 5-11） | I |
| 5-2 | migrate 中 CLR `.md`、APR render、`revisions/index.yaml` 的位置 | CLR `.md`、APR `.md／.html` 是衍生輸出，排在所有業務步驟之後；`revisions/index.yaml` 和 R000 同一階段 | I |
| 5-3 | `reason=decision_applied` 的判定 | from_revision 中某個決策點的 effective_basis 指向的 CLR，在 from_revision 建立之後新增了 `applied` landing | R |
| 5-4 | 移轉時沒有 spec 的既有 manual run | sidecar 記錄 `binding: none`；之後需要 RM 的步驟拒絕並提示（現有資料中唯一的 manual run 有 spec，不受影響） | I |
| 5-5 | AC-09-43～50 的對應 | 依 fixture 表列序 | I |
| 5-6 | `--acknowledge-idle`／`--cancel-run` 的衝突 | 同一個 run 兩個都給、或給了不是 RUNNING 的 run → 拒絕，不建立計畫 （拒絕條件，實作時補對應測試） | R |
| 5-7 | 標記中的檔案清單 | 標記記錄移轉清單的 sha256，不另外重複列檔案清單 | I |
| 5-8 | revision 的來源欄位 | `source_artifact_id` | I |
| 5-9 | AC-09-19 與綁定表的「CLR 納入」欄 | 規則以第 6 章為準；第 5 章只保留指向 | I |
| 5-10 | AC 使用真實 ID | 這些 AC 在部署當天的唯讀複本上執行，ID 以當天重新讀取的業務現況為準 | I |
| 5-11 | legacy R000 與 legacy 答案的 `target_decl_rev` | R000 的 pin 存在只能建立一次的 `revisions/R000.meta.yaml`（`target_decl_rev: 0`、`reference_pins: []`）；legacy CLR rev 0 的 basis 為 `{target, target_decl_rev: 0, closure: []}`。依據是「移轉前不存在任何引用宣告」，不從目前的 registry 動態填入歷史 pin；移轉前若已有宣告則拒絕移轉。所有讀取點經由同一個解析函式。驗收 AC-09-88～91 | R |
| 5-12 | CLR 的 spec 版本沒有匯入時的 rev 0 | 移轉無法為它建立 legacy basis（沒有可核對的 content_hash），也不能在移轉中匯入 spec（業務寫入在移轉前與維護中都被拒絕）。處理：**跳過該 CLR 的 rev 0**，在移轉標記的 `exceptions[]` 記錄 `{path, kind: clr_rev0_skipped, reason}` 並回報；不捏造 pin、不以目前資料當歷史依據。該 CLR 沒有 `answer_revisions`，不能被 clarification 型 SourceRef 引用。規則保留作為安全網。現有資料原本只有 `CLR-CASHOUT-001`（標示 v1.0，但 SPEC-CASHOUT-001 只匯入過 v0.1）會遇到；**Oscar 2026-10-07 決定以資料更正處理**：該單的 spec_version 更正為 0.1（主資料夾 main `e312a00`，history 留紀錄），移轉時正常建立 rev 0，現有資料不再觸發這個例外 | R |
| 5-13 | T7 對 `audit.log` 檢視的判定 | `audit.log` 是由事件檔重建的衍生檢視，移轉之後的任何操作（含 `maintenance end`、`start`）都會重新 render 全域 log。T7 對 `runs/_audit.log`、`runs/<run>/audit.log` 另外接受「目前內容等於依目前事件與 legacy 重新 render 的結果」：這代表它只是被正常更新過，R 照樣回復成移轉前的位元組（restore）或刪除（remove），那一步的 `expected_before` 是目前內容。其他內容（竄改）仍以 T7 拒絕。否則 AC-09-61 ② 與 AC-09-70 的情境永遠會被 T7 拒絕 | R |
| 5-14 | P3 實作補充的定義 | 新分析的 revision 從 R001 起編號，R000 只由移轉建立。run.yaml 的 `requirement_model_revision` 是目標端（spec-change-impact 時是 to 端），另有 `from_requirement_model_revision`、testcase-revision 的 `testcase_pin`（被修訂 TC 的舊 pin）。移轉 sidecar 的 `legacy_binding` 在 testcase-revision、manual 與 TC sidecar 為 true，其他為 false。清單中會造成循環的項目只列路徑、不列 sha（清單自己那一步與標記那一步的完成紀錄、標記的 remove 項、計畫檔、登錄紀錄），verify 與 rollback 改依計畫步驟或登錄紀錄核對。`untouched` 涵蓋 spec.yaml、TC 版本、registry、其他 run.yaml、需求模型檢視、核准單、CLR、移轉前已存在的登錄與狀態紀錄。R 寫兩個事件：接管（R2）與回復摘要。`req accept-declaration` 需要 `--by`（只能由人），`--rev` 必須是最新 revision。revision 的 `decision_snapshot_hashes` 與派發包一起在 P4 加入。R000 的 `reason=decision_applied` 判定：revision 引用的 CLR 有任何 applied landing 即成立（R000 沒有建立時間） | I |
| 5-15 | AC-09-85 ⑤ 與 §13.7 續做表 | 部分移轉（`marker` 群組為空）的 R 在檢查 B 通過後、`terminal` 寫入前中止時，R 沒有可落盤的「檢查 B 已通過」證據，續做無法與「還沒做檢查 A」區分，依 §13.7 該列重新執行檢查 A。兩個檢查此時的條件相同（標記必須不存在），沒有安全差異；AC-09-85 ⑤ 原寫「不執行檢查 A」與續做表矛盾，改依續做表。P6 驗收時發現 | R |
| 5-16 | AC-09-64 R5 的舊 validate 判定 | 改為 baseline 比對，不改程式。**W1 對照**：W1 資料 commit 之後、M2 之前（仍是舊程式），對「舊 `schema.infer` 能推斷 schema 的全部 yaml」逐檔執行舊 `bin/qaos validate` 的結果（排除定義層 schemas、agents、workflows、permissions、tools、tests、admin-ui、docs、bin 與隱藏目錄——W1 與 R5 時它們都是舊程式本身；推斷不出 schema 的檔案舊 validate 本來就不判定；`locks/`、`operations/` 在舊 `PATH_RULES` 推斷為 None）。回復後以同一範圍再執行一次，判定：(1) **W1 對照中有的路徑**：逐檔的退出碼與輸出全文（去除 root 的絕對路徑）都與 W1 對照相同；W1 對照中既有的失敗不算新失敗。(2) **W1 對照中沒有的路徑**：只允許是回復後保留的稽核事件檔——X、R 的 `retain_audit`，以及 M2 之後的控制類操作（`maintenance start|end`）寫入的 `runs/_audit.d/*`、`runs/<run>/audit.d/*` 事件檔（路徑樣式只用來界定範圍，不是清單；清單路徑仍一律具體，§11.3）；每個檔案都必須能由檔名的 op_id 對應到登錄紀錄（`index.d`）中的 X、R 或上述控制類操作，只因路徑落在 `audit.d/` 不算。符合 (2) 的檔案不在舊 validate 的判定範圍。(3) 其他情況（W1 對照中有的路徑結果不同；W1 對照中沒有的路徑不符合 (2)）都視為不符，停止並交人處理。後續業務操作寫入的檔案不屬於 (2)，依下方的前提處理。**理由**：舊 `schema.infer` 的 `PATH_RULES` 把 `runs/` 下所有 yaml 推斷成 `workflow/workflow-run.schema.json`，這是舊程式的推斷限制——W1 時既有的 `runs/*/entities/*.yaml` 也因此失敗，保留的事件檔指定給舊 validate 時同樣失敗；舊程式的正常流程不掃描 `runs/_audit.d/`。**前提**：比對以 `later_ops_snapshot` 為空為前提；使用 `--allow-later-ops`（§13.11）時，後續操作報告列出的路徑另依該報告人工判定，本條只是有限的相容性判定，不能宣稱資料全部回到 W1 的狀態。**W1 對照的保存**（§15.1 W1 列）：逐檔結果（路徑、推斷的 schema、退出碼、輸出全文）、逐檔 sha256、資料 commit、舊程式 SHA 與工具版本，記在回復報告；未追蹤的業務檔要納入該資料 commit 或另存快照。工具：`tools/legacy_validate_snapshot.py`——`snapshot` 取得 W1 對照與回復後的結果（以舊程式的 `bin/qaos validate` 逐檔執行、保存全文），`compare --op X`（X 必填）依 (1)～(3) 判定：先核對中繼資料——兩份結果的資料 root 都必須等於比對時的 `--root`（不借用其他 root 的登錄紀錄），兩份結果都由目前版本的工具產生且中繼資料齊全，舊程式內容的雜湊、資料 root 實際使用的 schemas 的雜湊（舊程式從資料 root 讀 schemas）、工具的 sha256、舊程式所用 `python3` 環境的 jsonschema／PyYAML／referencing 與 Python 版本都相同（W1 與 R5 以同一個 canonical 路徑執行）；X 必須是登錄紀錄中的 migrate，接管 X 的 R 恰好一份，X 與 R 的計畫檔 sha256 都等於登錄紀錄的 `plan_sha256`；(2) 只豁免 W1 時尚未登錄的 op，migrate 只限 X、migrate_rollback 只限該 R；一律讀 R 的計畫確認 `later_ops_snapshot` 為空（找不到 R 或非空即不符）。`snapshot` 在舊程式環境或範圍異常（輸出含 Traceback，或沒有任何 VALID，包含範圍內一個檔案都沒有）時不寫結果。本條的 baseline 是舊程式的判定，與 6-38（新程式的 schema 驗證）不同。M1（2026-10-08）：對照組是主資料夾工作目錄的原樣複本（相當於 W1 對照），23 檔既有失敗，回復後逐檔相同（M1 比對的是退出碼、輸出首行與輸出末 600 字元）；4 個對照組中沒有的事件檔（X 1、`maintenance start` 1、R 2）被判 INVALID，三個 op 都在 `index.d` 中，屬 (2)。2026-10-08 Oscar 決定（D-M1-1） | R |

### A.6 CLR 生命週期（第 6 章）

| # | 項目 | 定案 | 類別 |
|---|---|---|---|
| 6-1 | AC 與 fixture 的逐條對應 | 依 fixture 表列序（第 6 章已列） | I |
| 6-2 | RA-P7 | 併入 AC-10A-36 | I |
| 6-3 | A1 補記保留兩個時間、A2 answer_sources 驗證、A4 landing 形狀、A10 撤回 INCORPORATED 時引用它的 revision 判定為 `decision_revised`、沒有 kind 的舊 CLR 視為 `spec_question` | 全部保留有效 | R |
| 6-4 | A4' 的條件；APPLIED 之後再被引用 | A4' 與 A4 條件相同（明確 SourceRef、最新 answer_rev、通過 X16）；APPLIED 之後再被引用 → 只追加 `incorporated` landing，狀態不變 | R |
| 6-5 | a6b 的 `--target` 格式 | `<APR>#<resolutions 索引>` | I |
| 6-6 | a6b 與 revision 上的採用目標 | CLR 另有 revision 上的採用目標時，a6b 拒絕並提示改用 a6（a6b 只用於答案僅經 bug reject 路徑落地的情況） | R |
| 6-7 | `scan_reused: full` | scan 屬於最新 answer_rev、rule_version 相同：沿用關鍵字，並以保存的候選和鎖內重新掃描的結果做差異顯示；目標仍一律重新解析 | I |
| 6-8 | `impact` 不帶 `--target` | 自動解析採用目標（和 `apply` 相同的規則），並執行 (a)～(d) | I |
| 6-9 | `--impact-reviewed` 保存位置 | landing 與 history 都保存 | I |
| 6-10 | A8 與 A9 的交會 | 已併入第 6 章 §3 轉換表、§3.4 呼叫端、§6.6、§6.7：核准套用 `waive_missing` 後也執行同一個最後判定；A9 只在全項豁免、而且依重新驗證沒有任何有效 fulfillment 時發生；其他情況全部有效 fulfilled 或 waived → APPLIED。驗收 AC-10A-67～69 | R |
| 6-11 | `waive_missing` 對 document_items 的涵蓋 | 核准決議的條目逐一列出 `item_id`；以 item_id 比對 | I |
| 6-12 | `fulfill`、`waive-item` 的 `--by` | 同 2-2：`system` 或 `agent-*` → 拒絕；這是 actor 契約檢查，不是身分驗證（列入已知限制） （拒絕條件，實作時補對應測試） | R |
| 6-13 | A10 的指令 | `clarification withdraw <CLR> --reason <文字> --by <人>`（reason 必填） | I |
| 6-14 | AC-A-B1-4 的「三種處理方式」 | `--acknowledge-idle`、`--cancel-run`、事先在 `S_pre` 以 `run cancel` 取消（第 5 章 §11.2） | I |
| 6-15 | S0～S7 沿用的業務資料（版本對照、引用表、SITELIST 處理、現金淨收 AC-R7-1～3） | 屬實際 revise 時的作業資料，不是程式實作或驗收的內容；在 S0 時另備作業清單 | O |
| 6-16 | (d) 關鍵字比對欄位 | title、preconditions、steps 的 `action` 與 `expected`、expected_result（第 6 章 §5.10(d) 的「steps」指步驟的全部文字欄位）。ADR-008 原實作只比對 `action`，本條起改為兩者都比對，掃描規則版本 `rule_version` 由 "1" 升為 "2"（"1" 的掃描紀錄依 §5.10 只沿用關鍵字）。2026-10-07 由 Oscar 決定（P5-R2-02），原列 I 類，因影響候選範圍改列 R | R |
| 6-17 | 給不在候選中的 TC 下結論 | 拒絕（避免打錯 ID） （拒絕條件，實作時補對應測試） | R |
| 6-18 | 恢復表「核准決議寫入之後、A9 之前中止」 | 保留 | I |
| 6-19 | `stale-tcs` 沒有 applied landing 時的關鍵字 | 用最近一次掃描紀錄的關鍵字；沒有掃描紀錄時只做 requirement 與 decision_refs 規則 | I |
| 6-20 | AC-A-B1-11 的範圍 | AC-07-77a～77k 與 77e-ctrl | I |
| 6-21 | AC-A-B1-9、10 引用的 fixture | AC-A-B1-9 = AC-08-27～32（跨 basis）加上 effective_basis 解析：approval 包裝解析成 CLR 的 rev（原 R603-P1）、source 為 null 時是核准本身（原 R603-N4）、條目的 requirement／question 不同時 X15 FAIL（原 R603-N5）；不含需求 B 的「匹配」判定。AC-A-B1-10 = AC-07-36～49 | I |
| 6-22 | A4 的「明確 SourceRef」位置 | 決策點的 `resolution.source`，以及 basis 為 `defined_by_decision` 的 `known_rules`（clarification、approval 型，approval 包裝展開）；必須是 CLR 最新 answer_rev、通過 X16（自身範圍或 applicability）。`conflict_sides`、undefined 的背景 `known_rules`、需求層 `source_refs` 不觸發 A4。同一份 revision（或 BugDraft）每張 CLR 一筆 incorporated landing | R |
| 6-23 | A8 的 landing | `{type: applied, path: a8, items: [{item_id, result: fulfilled｜waived}], op_id, at, by}`；`by` 是執行 fulfill／waive-item 或核准的人；A9 的 WITHDRAWN 由 system 寫入 | I |
| 6-24 | 掃描紀錄的 ID 與候選理由 | `scan_id = SCAN-<ULID>`，全域唯一（`--scan` 指到別張 CLR 的紀錄時可明確拒絕）；路徑 `clarifications/<product>/<area>/scans/<CLR>-<scan_id>.yaml`；沒有 `--scan` 時 `scan_reused: none`；`rule_version: "1"`。候選理由：`target_requirement`（a）、`stale_decision_ref:<REQ>#<Q>`（b）、`clr_requirement`（c）、`keyword:<詞>`（d） | I |
| 6-25 | 舊資料的核准是否 apply | P4 時舊資料的 RESOLVE_AMBIGUITY 核准仍 apply（附錄 A 1-27）；P5 起依第 6 章 §3.4，approve 和 override **都不再** apply 任何 CLR（新舊資料皆同）。舊資料的核准前檢查（所有掛的 CLR 都必須已回答）保留 | R |
| 6-26 | BugDraft 的 SourceRef | 第一批選填：`source_refs[]`、`decision_refs[]`；clarification、approval 型必須對應 `decision_refs` 的決策點（run 綁定的 revision 中），並通過共用驗證與 X16（G-BVAL）。`expected_result_spec_reference` 放寬為 SpecReference 或 SourceRef | I |
| 6-27 | 文件項目的紀錄位置 | fulfillment 存在各項目的 `fulfillments[]`；豁免存在 `waive_records[]`（`source` 為 `waive-item` 或 `approval <APR>`）。頂層 `fulfillments` 欄位不使用 | I |
| 6-28 | A1、A2 的補充欄位 | `ask --sent-at --channel`：`asked_at` 是記錄時間，`sent_at` 是實際送出時間，兩者並存。`answer --answer-source <JSON>`：spec 型（核對 SpecPin）、document 型（file_name、sha256、location）、message 型（channel、sent_by、at）。文件索取單不能 `answer` | I |
| 6-29 | a6b 的落地 run | 必須是 spec-to-bug、COMPLETED；`--target <APR>#<索引>` 的核准單屬於該 run、是 reject 決議；條目的 (requirement_id, question_id) 必須是該 run 綁定 revision 中的決策點，source 依自身範圍或 applicability 通過 X16 | R |
| 6-30 | 撤回（A10）與過時判定 | revision 引用的 CLR 被撤回時，`decision_revised` 為真（附錄 A 6-3）；過時判定展開 approval 包裝 | I |
| 6-31 | landed-in 的「run 的範圍」（§5.6 第 3 點） | spec-to-bug：只看該 run 最終 BugDraft 的明確 SourceRef（run 綁定的 revision 是分析依據，不是這個 run 的產出）；manual-test-to-regression：綁定 revision 中的目標，限於本 run 最終 TestCaseDraft 各 TC 的 `requirement_ids`；spec-to-testcase、spec-change-impact：綁定 revision 的全部需求 | R |
| 6-32 | A9 的「涵蓋全部項目」 | 只計**這張核准**的 `waive_missing` 列出的項目；先前以 `waive-item` 人工豁免的項目不算。核准沒有涵蓋全部項目時，依 §6.6 最後判定（全部有效 fulfillment 或 waived → APPLIED） | I |
| 6-33 | apply 輸入的重複 | 同一張 TC 重複給 `--tc-conclusion`（不論值是否相同）、同一個目標重複給 `--defer-target` → 拒絕 | I |
| 6-34 | `stale-tcs` 的目標 | 各 spec 版本最新 revision 中採用本 CLR **任一** answer_rev 的決策點（A5 之後、revision 還沒重新納入最新 rev 時，仍能以 (a)(b) 找到依賴舊答案的 TC），加上歷次 applied landing 確認與延後的目標；掃描單位、(a)～(d) 與 apply 相同；另外列出任何單位中 `decision_refs` 指向本 CLR 舊 rev 的 TC | I |
| 6-35 | 舊格式（E6）CLR 的結案路徑 | 核准不再 apply（6-25）之後，舊格式需求的 CLR 若回答 `requirement_clarified` 等需要落地的 resolution：重新分析時 Spec Analyst 依現行契約以決策點的 `resolution.source` 引用該 CLR（需求轉為新格式）→ A4 → a6；答案不需落地時走 a7；都不適用時由人撤回（A10）。系統不為舊格式需求另開結案路徑。**前置（X16 不放寬）**：舊格式單沒有 `subject`／`role_scope`／`params`（E6 自動單、移轉的 rev 0），直接引用會被 X16 擋下。重新分析之前由人逐單核對，二擇一讓 X16 成立：(1) CLR 有 `requirement_id`、舊答案的 basis 與新決策點相同、範圍也一致 → 以 `clarification metadata upgrade` 補 `subject`、`role_scope`、`params`（只補缺的欄位；`question_id` 不影響 X16，建議一併補上以利追溯）；(2) basis 不同（例如答案之後目標新增 normative 引用宣告、移轉 rev 0 的 legacy basis），或 CLR 沒有 `requirement_id`（metadata upgrade 補不了）→ 以 `clarification applicability add --confirm-basis` 確認舊答案適用於新決策點；applicability 自帶完整範圍，不需要先做 (1)；(3) 範圍或 basis 對不上而不能確認 → 不引用，重新詢問 PM 或撤回（A10）。**推論**：移轉後的 M1 預演要逐張列出現存 ANSWERED 的舊格式 CLR，記錄 (1)～(3) 的選擇、理由與最後走 a6、a7 或 A10 | R |
| 6-36 | Validator 報告審查的 Draft | G-TVAL 的 `testcase_draft_artifact_id`、G-BVAL 的 `bug_draft_artifact_id` 必須是產生者 task（agent-test-designer／agent-bug-analyst）本輪 `output_artifact_ids` 中、型別相符、狀態 VALID 的 artifact；否則 Structural FAIL（只寫診斷），不 materialize、不轉換 Bug 狀態。人 reject 後重做會清空產生者的本輪產出但不把舊稿改成 SUPERSEDED；Validator 語意 FAIL 退回則保留清單、把舊稿改成 SUPERSEDED；submit 的引用檢查只看 `references`，擋不到 payload 指向舊稿的報告。這條檢查讓正式 TC／Bug 與落地判定（§5.6、6-31 的最終稿）看的是同一份 Draft。2026-10-07 自審 F1，Oscar 決定移到 P6 | R |
| 6-37 | Bug 被 REJECTED 的 spec-to-bug run | Bug 經 CONFIRM_DUPLICATE 確認重複或 RESOLVE_AMBIGUITY reject 而 REJECTED、run 仍 COMPLETED 時，該 run 沒有最終 BugDraft：不作為 a6 的 `--landed-in`（明確拒絕），也不提供採用目標。答案只經 bug reject 路徑落地時走 a6b（6-29），否則以其他 run 落地。2026-10-07 自審 F5，Oscar 決定排除 | R |
| 6-38 | AC-A-B1-4 的 schema baseline 與比對規則 | **兩個集合**：「移轉前 baseline」＝移轉前對唯讀複本的全部業務資料做 schema 驗證時失敗的檔案；「移轉後預期失敗清單」＝移轉前 baseline ＋ 繼承原檔失敗的 R000。**比對規則**（移轉後再驗一次，必須同時成立）：(1) 移轉新增或修改的檔案（R000 除外）全部 PASS；(2) 失敗的 `revisions/R000.yaml` 必須與它所屬版本目錄的 `requirements.yaml`（`revisions/` 的上一層）逐位元相同，且該原檔在移轉前 baseline 中（只繼承原檔的失敗）；(3) 移轉後的失敗集合 ⊆ 移轉前 baseline ∪ (2) 的 R000；(4) 移轉前 baseline 的檔案沒有被修改或刪除（以移轉前後逐檔內容比對確認；不要求它們列在移轉清單的 `untouched` 類別）。規則只涵蓋有 schema 的檔案；沒有 schema 的移轉產物（`R000.meta.yaml`、revisions 索引、`operations/`、`audit.d/`、`_migration.yaml`）由 `migrate verify` 依計畫核對。**移轉後預期失敗清單**（資料快照 `git archive 7ef07ee`／`3a62d87`，14 檔＝移轉前 baseline 13 檔＋第 4 檔 TXLOG 0.1 的 R000）：1. `artifacts/change-impact/RUN-20261001-007/ART-CIR-01M3VNQQ2Q073T4VH6R8C6JHEN.yaml`<br>2. `artifacts/change-impact/RUN-20261002-002/ART-CIR-01M3XJ09X6JYPY1SNA4TAP8H3D.yaml`<br>3. `artifacts/requirements/SPEC-TXLOG-001/v0.1/requirements.yaml`<br>4. `artifacts/requirements/SPEC-TXLOG-001/v0.1/revisions/R000.yaml`<br>5. `artifacts/test-design/RUN-20260916-002/ART-TCD-01M2MBGVMK0N543JTJY81T0GSP.yaml`<br>6. `artifacts/test-design/RUN-20260916-002/ART-TCD-01M2ME3944YP3RRJ94T1RXVXTQ.yaml`<br>7. `artifacts/test-design/RUN-20260916-002/ART-TDR-01M2MCQZYJH4YZXYH70BXC6SFM.yaml`<br>8. `artifacts/validation/RUN-20260915-003/ART-TVR-01M2GGKWE2V1THXS6S8F99TTVK.yaml`<br>9. `artifacts/validation/RUN-20260915-004/ART-TVR-01M2GJM8F0Z29M0TPCTBCEASDF.yaml`<br>10. `artifacts/validation/RUN-20260915-006/ART-TVR-01M2GMZE38WR4JYJ3GYKSN8TDA.yaml`<br>11. `artifacts/validation/RUN-20260915-016/ART-TVR-01M2J9XT2E2GMNJP4BYX3JZQ4Z.yaml`<br>12. `artifacts/validation/RUN-20260915-016/ART-TVR-01M2JAJE9Y2D8YZDJ4NAP42RYT.yaml`<br>13. `artifacts/validation/RUN-20260915-022/ART-TVR-01M2JHHJG7TQ2B9E3JESWWE38A.yaml`<br>14. `artifacts/validation/RUN-20260916-007/ART-TVR-01M2QZ9R2PSGJHC14CMQDNYGD6.yaml`。第 3 與 5～14 檔連需求 A 之前（`2e01d4b`）的 schema 也不通過；第 1、2 檔是需求 A 為 CIR 新增必填 `from_rm_revision`、`to_rm_revision`、`pin_groups` 而失敗，所屬 run 已 COMPLETED、不會再被 gate 讀取，**列入 baseline，不放寬 CIR schema**；第 4 檔是第 3 檔的逐位元複本（繼承失敗，不屬於移轉前 baseline）。**M1 與部署當天**：以當天資料重新計算移轉前 baseline，並把移轉後的失敗集合與本清單比對；不同（多或少）時停下交 Oscar 核對，不自動接受。2026-10-08 Oscar 決定（P6-C01-03，選 (A)＋(A1)） | R |

