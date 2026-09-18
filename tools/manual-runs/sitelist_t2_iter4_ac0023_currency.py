#!/usr/bin/env python3
"""RUN-20260916-007 T2 iteration 4：修訂 iteration 3 的 TestCaseDraft / TestDesignReport。

處理 Validator（ART-TVR-01M2QQVJMG6DTM8MQJ3DAYX9T3）的 blocker + major：
  blocker：AC-SITELIST-0023 then 子句的第二個斷言（核心貨幣依所選類型連動建立、不需 admin
          自身的鏈上錢包管理預先啟用該幣別）完全沒有任何 TC 覆蓋 → 本輪新增一條聚焦 TC。
  major ：coverage_matrix 宣稱 AC-SITELIST-0023 由兩條既有 TC 覆蓋，但那兩條 TC 自身的
          acceptance_criteria_ids 未列入該 AC → 本輪改為 AC-0023.draft_ids 僅列新 TC，
          uncovered_with_reason 精確描述「斷言一刻意不獨立覆蓋、斷言二由新 TC 覆蓋」。
其餘 65 條 TC 原封不動沿用。
"""
import sys, pathlib, collections, copy
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids

RUN = "RUN-20260916-007"
ITER = 4
SID, SV, AREA, A = "SPEC-SITELIST-001", "0.4", "SITELIST", "agent-test-designer"
RM_AID = "ART-RM-01M2E2SWZ3GR030YTSZS54E1NE"
PREV_TCD = "ART-TCD-01M2QPKZ950XF3BQ9M1HKQPM4B"
PREV_TDR = "ART-TDR-01M2QPKZ9784J2HYBCWD5PG6BN"
BASE = store.ROOT / "artifacts" / "test-design" / RUN

prev_tcd = store.load(BASE / f"{PREV_TCD}.yaml")
prev_tdr = store.load(BASE / f"{PREV_TDR}.yaml")
TCS = copy.deepcopy(prev_tcd["payload"]["testcases"])
REP = copy.deepcopy(prev_tdr["payload"])

TC_AC0011 = "TC-DRAFT-01M2NCSW5C2NPYX0YR2ATYY7QA"   # 根層站台可自由二擇一站台類型
TC_AC0091 = "TC-DRAFT-01M2NCSW5D81FCS58EVQ44M0D0"   # 核心貨幣下拉選項依站台類型過濾
TC_AC0021 = "TC-DRAFT-01M2NCSW5CF3M957FW8FTEYYS8"   # 子站台強制跟隨
TC_BYPASS = "TC-DRAFT-01M2NCSW5CPSGPYY3SVMV27JMF"   # API bypass（negative / exploratory）
TC_REMOVED = "TC-DRAFT-01M2NCSW5C4CVZTP2HE4NCEX54"  # iteration 3 已移除的重複 TC

NEW = f"TC-DRAFT-{ids.ulid()}"

ASSUMPTIONS = [
    "「帳務管理 > 鏈上錢包管理」這個頁面、以及各頁標題下方的「站台切換」下拉選單，在 SPEC-SITELIST-001 v0.4 全文完全沒有出現（「鏈上錢包」四字零命中）；"
    "step 5 的頁面路徑與「機台場館的鏈上錢包管理僅顯示法幣 TWD 頁籤、只啟用這一種幣別」這個預期觀察，依據來自 SPEC-ARCADE-001 v0.7「機台場館的後台選單」表與 "
    "SPEC-UPDATEPACK-001 v0.1「機台場館的情形」，屬跨 spec 推論，需人工確認在「從站台列表新建機台根站台」這個情境下同樣成立。",

    "AC-SITELIST-0023 then 子句中「不需 admin 自身的鏈上錢包管理預先啟用該幣別」這一句，在 spec.md v0.4 查無出處，"
    "CLR-SITELIST-010（status: APPLIED）的 PM 答覆也只寫到「核心貨幣依所選類型連動建立」、沒有這一句；其唯一出處是 RequirementModel 的 AC 文字本身。"
    "需人工向 PM 確認此斷言的來源與精確語意（是「不需要先啟用」還是「建立時會順帶啟用」）後，才能把它當成確定規則。",

    "本 TC 能否真正證明「不需預先啟用」，取決於執行當下 admin 自身的鏈上錢包管理中 TWD 恰好不是啟用狀態（step 1 的基準觀察）；"
    "若環境中 admin 的 TWD 原本即為啟用，這個否定前提不成立，本次執行只能驗證「連動建立」的正面部分。"
    "spec 沒有任何條文說明 admin 層的幣別啟用狀態如何設定或重置，因此「如何佈置出 TWD 未啟用的 admin 環境」是我無法從 spec 推導的，需環境負責人協助。",

    "新建站台狀態固定為「待開通」（spec.md §操作/新增站台）；spec 未定義「待開通」狀態的站台是否會出現在後台的「站台切換」下拉選單中。"
    "若不出現，step 5 / step 6 無法執行，本 TC 的可驗證範圍將退回到 step 3/4（站台列表頁面內可觀察的核心貨幣連動帶入），需人工確認站台切換清單的納入條件。",
]

new_tc = {
    "draft_id": NEW,
    "title": "機台類型根層站台建立時核心貨幣 TWD 連動啟用，過程中未在 admin 端預先啟用該幣別",
    "product": "ba-admin",
    "functional_area": AREA,
    "requirement_ids": ["REQ-SITELIST-002"],
    "acceptance_criteria_ids": ["AC-SITELIST-0023"],
    "spec_id": SID,
    "spec_version": SV,
    "test_level": "ui_e2e",
    "test_types": ["functional"],
    "design_techniques": ["requirement_based"],
    "priority": "high",
    "risk": "high",
    "execution_mode": "manual",
    "preconditions": [
        "以 Admin 身分登入 ba-admin 後台（Admin 可見全部站台、新增站台時可自由選取上層站台或留空）",
        "該 Admin 帳號同時看得到「後台管理員系統 > 站台列表」與「帳務管理 > 鏈上錢包管理」兩個選單項目（自行從環境中選定可用的 Admin 帳號，不指定特定帳號）",
        "頁面標題下方的「站台切換」下拉選單維持在最上層（admin）脈絡",
        "本次測試全程不得對任何站台的幣別啟用狀態做手動變更——step 1 是唯讀觀察，這是本 TC 成立的前提",
    ],
    "test_data": [
        {"name": "上層站台", "value": "留空（＝建立根層站台，即 AC-SITELIST-0023 所稱「上層為 admin」的情境）"},
        {"name": "站台類型", "value": "機台"},
        {"name": "預期連動的核心貨幣", "value": "TWD"},
        {"name": "站台名稱", "value": "自訂可辨識名稱，例如「AC0023-核心貨幣連動驗證」"},
        {"name": "站台代碼", "value": "兩碼大寫英文字，取環境中尚未使用的組合（例如 ZT）；若提示重複改試另一組",
         "note": "代碼格式規則見 spec.md §業務規則與驗證/站台代碼格式"},
    ],
    "steps": [
        {"n": 1,
         "action": "站台切換維持在 admin（最上層）脈絡，從左側選單進入「帳務管理 > 鏈上錢包管理」，檢視法幣頁籤，記錄 TWD 這個幣別是否存在、以及其狀態（啟用／關閉／禁用／根本沒有這個幣別）。本步驟只讀不改，不得在此啟用 TWD。",
         "expected": "取得 admin 自身的 TWD 幣別狀態，作為後續判讀「是否需要預先啟用」的比對基準"},
        {"n": 2,
         "action": "回到「後台管理員系統 > 站台列表」，在根層（路徑列顯示「站台列表」）點擊右上角「+ 新增站台」開啟 Modal，「上層站台」欄位保持留空，「站台類型」選「機台」。",
         "expected": "上層站台留空代表建立根層站台；站台類型欄位可自由選擇（不被強制跟隨規則鎖住）"},
        {"n": 3,
         "action": "在同一個 Modal 內檢視「核心貨幣」欄位的值（不做任何幣別啟用、匯入或其他前置操作），填妥站台名稱與兩碼大寫站台代碼後點擊「建立站台」。",
         "expected": "核心貨幣欄位依所選「機台」類型帶出 TWD；點擊建立後站台建立成功，列表出現該站台、狀態為「待開通」"},
        {"n": 4,
         "action": "在站台列表找到剛建立的站台，點擊該列的「編輯」開啟 Modal，檢視「核心貨幣」欄位。",
         "expected": "核心貨幣顯示為 TWD，且為唯讀（建立後不可修改）"},
        {"n": 5,
         "action": "將頁面標題下方的「站台切換」下拉選單切到剛建立的這個機台站台，再進入「帳務管理 > 鏈上錢包管理」，檢視法幣頁籤中 TWD 的狀態。若該站台因狀態為「待開通」而未出現在站台切換清單中，記錄此事實並跳過本步驟與 step 6（見 expected_result 的範圍說明）。",
         "expected": "該站台的鏈上錢包管理法幣頁籤存在 TWD 且狀態為啟用（跨 spec 預期，依據見 assumptions 第 1 條）"},
        {"n": 6,
         "action": "將「站台切換」切回 admin（最上層）脈絡，重新檢視「帳務管理 > 鏈上錢包管理」法幣頁籤的 TWD 狀態，與 step 1 記錄的基準值比對並記錄差異。",
         "expected": "記錄比對結果（此步驟純為建立負面事實的對照基準，不作為本 TC 的通過／失敗判準，理由見 expected_result）"},
    ],
    "expected_result":
        "在全程未於 admin 自身的「鏈上錢包管理」執行任何啟用 TWD 之前置操作的前提下（step 1 為唯讀觀察）："
        "step 3 的核心貨幣欄位依所選「機台」類型帶出 TWD 且站台建立成功、step 4 顯示該站台核心貨幣為 TWD（唯讀）、"
        "step 5 顯示該站台的鏈上錢包管理法幣頁籤 TWD 為啟用——亦即核心貨幣依所選站台類型連動建立，不以 admin 自身預先啟用該幣別為前提。"
        "【判讀範圍限制，執行者請務必一併回報】(1) 只有當 step 1 觀察到 admin 自身的 TWD 並非啟用狀態時，本次執行才構成「不需預先啟用」的完整證據；"
        "若 step 1 就發現 admin 的 TWD 原本即為啟用，則這次執行只能證明「連動建立」的部分，「不需預先啟用」在該環境下無法判定，應如實回報而非逕行判為 Pass。"
        "(2) 若新站台因「待開通」狀態未出現在站台切換清單，step 5/6 無法執行，本次可驗證範圍退回 step 3/4，同樣如實回報。"
        "(3) step 6 的比對結果僅供記錄：AC-SITELIST-0023 並未對「建立動作是否改變 admin 自身的幣別狀態」做任何要求，"
        "若發現 admin 端 TWD 狀態被此次建立改變，屬本 AC 未定義的行為，回報為待確認，不直接判為 Fail。",
    "expected_result_spec_reference": {
        "spec_id": SID,
        "spec_version": SV,
        "location": "§核心貨幣（第一項）＋ §操作/新增站台「核心貨幣」欄",
        "quote": "主站台（根層站台）的核心貨幣為下拉選單，選項依站台類型過濾——可選幣別清單依類型維護，目前線上＝USDT、機台＝TWD 各僅一種，故實際上等同自動帶入（2026-08-21 客戶定案）",
    },
    "assumptions": [{"text": t, "requirement_id": "REQ-SITELIST-002", "needs_human_confirmation": True} for t in ASSUMPTIONS],
    "automation_status": "not_automated",
    "ci_eligible": False,
    "hotfix_eligible": True,
    "execution_cost": "high",
    "stability": "unknown",
    "critical_path": False,
    "source": "spec_workflow",
    "design_rationale":
        "本 TC 只涵蓋 AC-SITELIST-0023 then 子句的第二個斷言（核心貨幣依所選類型連動建立、不需 admin 自身的鏈上錢包管理預先啟用該幣別）。"
        f"第一個斷言（站台類型欄位可自由選擇、不強制跟隨 admin 自身類型）在黑箱可觀察層面與 AC-SITELIST-0011 完全重疊，已由 {TC_AC0011} 覆蓋，此處不重複（見 TestDesignReport.uncovered_with_reason）。"
        f"與 {TC_AC0091}（AC-0091/0092）的差別：那條只驗證「新增站台 Modal 的核心貨幣下拉選單依站台類型過濾顯示 USDT／TWD」，"
        "停在選單顯示層，完全沒有觸及幣別在新站台是否真的連動啟用、以及是否以 admin 端預先啟用為前提；本 TC 的 step 5 才是這個斷言的驗證點。"
        "技術標 requirement_based 而非 decision_table：本 TC 只走「機台」這一條路徑、是單一條件對單一結果，沒有 2×2 以上的條件組合矩陣；"
        "也不是 negative（不驗證拒絕行為），故不落入 REQ-SITELIST-002 rejection_contract.defined=false 對 negative／error_guessing 的限制。"
        "依據分層（誠實揭露哪句有出處、哪句是推論）：step 3/4 的「機台→TWD 連動帶入、建立後唯讀」有 spec.md §核心貨幣 明文（即 expected_result_spec_reference 的引文）；"
        "step 5 的「該站台鏈上錢包管理法幣頁籤 TWD 為啟用」在 SPEC-SITELIST-001 v0.4 全文查無依據（本檔完全沒有出現「鏈上錢包」四字），"
        "是我依 SPEC-ARCADE-001 v0.7「機台場館的後台選單」表與 SPEC-UPDATEPACK-001 v0.1「機台場館的情形」做的跨 spec 推論；"
        "而「不需 admin 自身預先啟用」這句更只存在於 RequirementModel 的 AC 文字，CLR-SITELIST-010 的 PM 答覆並沒有這一句。"
        "因此本 TC 走 exploratory 路徑（assumptions 四條、全部 needs_human_confirmation: true），不宣稱 spec 已明確定義。"
        "範圍誠實聲明：這個斷言的否定面（「不需預先啟用」）能不能真的被黑箱驗證，取決於執行環境中 admin 自身的 TWD 恰好未啟用；"
        "前提不成立時本 TC 只能驗證正面的連動效果——這點寫進 expected_result 的判讀範圍限制而不是藏起來，避免執行者誤以為 Pass 就等於斷言成立。"
        "step 1 與 step 6 的存在是為了給這個「不需要／沒發生」的負面事實一個乾淨的比對基準（前後對照 admin 端狀態），"
        "但 step 6 明確標示為記錄用、不作判準，以免斷言超出 AC then 子句要求的範圍。",
}
TCS.append(new_tc)

# ---- coverage_matrix：AC-SITELIST-0023 改為僅由新 TC 覆蓋 ----
for row in REP["coverage_matrix"]:
    if row["requirement_id"] == "REQ-SITELIST-002":
        if NEW not in row["draft_ids"]:
            row["draft_ids"].append(NEW)
        for ac in row.get("acceptance_criteria", []):
            if ac["ac_id"] == "AC-SITELIST-0023":
                ac["draft_ids"] = [NEW]

# ---- uncovered_with_reason：精確描述「斷言一刻意不獨立覆蓋、斷言二由新 TC 覆蓋」 ----
REASON_002 = (
    "AC_PARTIALLY_COVERED: AC-SITELIST-0023 的 then 子句其實含兩個獨立斷言，本輪（iteration 4）分開處理，"
    "不再像 iteration 3 那樣籠統宣稱整條 AC 已被其他 TC 涵蓋。"
    "【斷言一】「站台類型欄位可自由選擇機台或線上，不強制跟隨 admin 自身的站台類型」——維持不另設獨立 TC。"
    "根層站台定義上沒有上層站台，admin 作為系統隱含上層從未落入 REQ-SITELIST-002「子站台一律與主站台同類型」這條強制跟隨規則的適用範圍；"
    f"其黑箱可觀察操作（上層站台留空 → 站台類型二擇一 → 依所選類型建立）與 AC-SITELIST-0011 完全相同，已由 {TC_AC0011} 覆蓋。"
    f"iteration 2 曾為此設計獨立 TC（{TC_REMOVED}），Validator 判定其產生不出任何新的黑箱可觀察證據、屬 duplicate（blocker），iteration 3 已移除，本輪維持移除。"
    "此部分屬「刻意不獨立覆蓋」，非遺漏。"
    "【斷言二】「核心貨幣依所選類型連動建立（例如選機台則連動啟用 TWD），不需 admin 自身的鏈上錢包管理預先啟用該幣別」——本輪新增 TC 真正覆蓋。"
    f"iteration 3 曾宣稱此斷言已由 AC-SITELIST-0091/0092 的 {TC_AC0091} 涵蓋，但該 TC 的 expected_result 只驗證「新增站台 Modal 的核心貨幣下拉選單依站台類型過濾顯示 USDT／TWD」，"
    "停在選單顯示層，完全沒有觸及幣別是否在新站台連動啟用、更沒有觸及是否以 admin 端預先啟用為前提；"
    "Validator 以全份 TC grep「鏈上／錢包／預先啟用」零命中證實該宣稱在事實層面不成立（blocker），此判斷成立。"
    f"本輪新增 {NEW} 聚焦驗證這個斷言，coverage_matrix 的 AC-SITELIST-0023.draft_ids 改為僅列這一條新 TC，"
    f"不再把 {TC_AC0011} / {TC_AC0091} 列為 AC-SITELIST-0023 的覆蓋者——此即 Validator major issue 指出的「coverage_matrix 宣稱與 TC 本體 acceptance_criteria_ids 記載不一致」，一併修正。"
    f"新 TC 為 exploratory：「不需預先啟用」這句在 spec.md 與 CLR-SITELIST-010 的 PM 答覆中皆無出處，且其驗證同時依賴跨 spec 的頁面知識（鏈上錢包管理、站台切換）與一個 spec 未定義的環境前提"
    "（admin 自身 TWD 未啟用），範圍限制已寫入該 TC 的 expected_result 與 assumptions。"
    "若人工確認後認為此斷言需要更確定的驗證依據，建議另開 Clarification 向 PM 問清「連動啟用」的精確語意與其在鏈上錢包管理頁面的可觀察表現，而非再堆更多 exploratory 案例。"
    f"【REQ-SITELIST-002 本身】AC-0021/0022 由 {TC_AC0021} 覆蓋；high risk 所需的 non-happy 覆蓋由 {TC_BYPASS}（negative／exploratory 的 API bypass 案例）滿足。"
)
found = False
for u in REP["uncovered_with_reason"]:
    if u["requirement_id"] == "REQ-SITELIST-002":
        u["reason"] = REASON_002
        found = True
assert found, "REQ-SITELIST-002 應已存在於 uncovered_with_reason"

# ---- technique_summary 依實際重算 ----
tech_count = collections.Counter(t for tc in TCS for t in tc["design_techniques"])
REP["technique_summary"] = [{"technique": k, "count": v} for k, v in sorted(tech_count.items())]

# ---- report 層 assumptions（字串陣列）補上新 TC 的四條 ----
REP["assumptions"] = list(REP["assumptions"]) + ASSUMPTIONS

# ---- duplicate_check：預先交代新 TC 與 TC_AC0091 的差異 ----
REP["duplicate_check"]["findings"].append({
    "draft_id": NEW,
    "similar_to": TC_AC0091,
    "resolution": "非重複：TC_AC0091 驗證的是「新增站台 Modal 的核心貨幣下拉選單依站台類型過濾顯示哪些選項」（選單顯示層，REQ-SITELIST-009）；"
                  "本 TC 驗證的是「建立完成後該站台的核心貨幣 TWD 是否連動啟用，且此連動不以 admin 自身的鏈上錢包管理預先啟用 TWD 為前提」"
                  "（跨頁面的連動效果與前提條件，REQ-SITELIST-002／AC-SITELIST-0023）。兩者步驟、觀察頁面與斷言皆不同。"
})

REP["revision_of_issues"] = list(REP.get("revision_of_issues", [])) + [
    {"issue_index": 0, "draft_id": NEW,
     "action": "iteration 4／blocker（AC-SITELIST-0023 的「核心貨幣連動、不需預先啟用」斷言零覆蓋）："
               "接受 Validator 的事實核對——iteration 3 宣稱該斷言已由 AC-0091/0092 的 TC 涵蓋並不成立，該 TC 只驗證下拉選單過濾顯示。"
               f"本輪新增 {NEW} 聚焦此斷言：step 1 先唯讀記錄 admin 自身鏈上錢包管理的 TWD 狀態作為基準，step 2-4 於站台列表建立機台根站台並確認核心貨幣連動帶入 TWD，"
               "step 5 切換站台後於該站台的鏈上錢包管理確認 TWD 為啟用，step 6 回頭比對 admin 端狀態（僅記錄、不作判準）。"
               "因「不需預先啟用」一句在 spec.md 與 CLR-SITELIST-010 皆無出處、且驗證依賴跨 spec 頁面知識與 spec 未定義的環境前提，此 TC 以 exploratory 處理（4 條 assumptions），"
               "並在 expected_result 明寫判讀範圍限制（admin 端 TWD 原本即啟用時無法判定、待開通站台若不在站台切換清單則 step5/6 無法執行），不硬湊成一條看似確定的驗證。"},
    {"issue_index": 1, "draft_id": TC_AC0011,
     "action": "iteration 4／major（coverage_matrix 宣稱 AC-SITELIST-0023 由 TC_AC0011 與 TC_AC0091 覆蓋，但兩條 TC 自身的 acceptance_criteria_ids 未列入該 AC）："
               "改為 AC-SITELIST-0023.draft_ids 僅列本輪新增的 TC（該 TC 的 acceptance_criteria_ids 確實含 AC-SITELIST-0023），"
               "兩條既有 TC 不再被宣稱為 AC-0023 的覆蓋者、本體維持不動；型別選擇重複的部分改由 uncovered_with_reason 以 AC_PARTIALLY_COVERED 前綴逐項說明，"
               "記載與 TC 本體因此一致。"},
    {"issue_index": 2, "draft_id": "TC-DRAFT-01M2NCSW5DCHMTM4ZVB90KXN76",
     "action": "iteration 4／minor advisory（REQ-SITELIST-020「恰好兩碼大寫英文字」的長度邊界未見對應 AC 或 TC）："
               "認同 Validator 的判斷「屬 RequirementModel 本身 AC 未涵蓋，非本輪 TestCaseDraft 遺漏既有 AC」。"
               "現有 AC-SITELIST-0201~0204 皆不含長度不足／超過 2 碼時的系統行為，若在此自行補一條 boundary_value TC，等於把「長度不足 2 碼會被擋」寫成確定規則，"
               "但 spec.md §業務規則與驗證只寫「必須為恰好兩碼大寫英文字；輸入時自動轉大寫並過濾非英文字元」，未定義過濾後長度不等於 2 時的反應。"
               "維持不新增，建議依 Validator 的 recommended_change 另開 Clarification，待 RM 補上對應 AC 後再設計。"},
]

REP["testcase_draft_artifact_id"] = None  # 稍後填入


def envelope(t, payload, refs, supersedes):
    aid = ids.artifact_id(t)
    art = {"artifact_id": aid, "artifact_type": t, "schema_version": "1.0", "version": 1, "run_id": RUN,
           "task_id": "T2", "iteration": ITER, "created_by": A, "created_at": store.now(), "status": "DRAFT",
           "source": {"type": "RequirementModel", "ids": [RM_AID]}, "references": refs,
           "requires_approval": None, "payload": payload, "supersedes_artifact_id": supersedes}
    p = BASE / f"{aid}.yaml"
    store.save(p, art)
    return aid, p


did, p1 = envelope("TestCaseDraft",
                   {"mode": "spec", "spec_id": SID, "spec_version": SV, "testcases": TCS},
                   prev_tcd["references"], PREV_TCD)
REP["testcase_draft_artifact_id"] = did
rid, p2 = envelope("TestDesignReport", REP, [{"entity_type": "Artifact", "id": did}], PREV_TDR)

print(p1)
print(p2)
print(f"TCs={len(TCS)} new={NEW}")
print("techniques:", dict(sorted(tech_count.items())))
exp = sum(1 for t in TCS if t["assumptions"])
print(f"exploratory total={exp}; REQ-002 exploratory={sum(1 for t in TCS if 'REQ-SITELIST-002' in t['requirement_ids'] and t['assumptions'])}")
