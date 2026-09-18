#!/usr/bin/env python3
"""RUN-20260916-007 T2 iteration 2：依 Validator 對 iteration 1 draft
(ART-TCD-01M2NDK7CFZGE5ZN3V15MX6E1S / ART-TDR-01M2NDK7DHQX2ZWAR703G0NZRG) 的最新審查意見修訂。

不重新設計，僅針對指出的問題做最小必要修改，其餘 TC 原封不動照抄。

Blocker: TC-DRAFT-01M2NCSW5C4CVZTP2HE4NCEX54（REQ-SITELIST-002 admin 例外，AC-SITELIST-0023）。
    REQ-SITELIST-002 的 history 已由 Oscar 於 2026-09-16 直接對話確認 admin 例外規則為真（requirements.yaml
    已更新，取代先前日期矛盾、缺乏 CLR 交叉引用的舊記載），故本輪不再重新質疑規則本身的真實性。
    但 Validator 指出一個仍然成立的技術問題：本 TC step1「上層站台留空（建立於 admin 根節點之下、成為根層站台）」
    與 AC-SITELIST-0011（REQ-SITELIST-001，根層站台自由二擇一類型）在操作上完全無法區分——經重新讀取
    spec.md v0.4「操作／新增站台」表格，「上層站台」欄位只有「留空為根層」與「搜尋改選任意站台」兩種操作，
    全文找不到任何「選擇上層站台為 admin」的獨立 UI 入口，確認選項 A 成立：這是同一個操作情境。
    -> 不假裝這是一條獨立可執行路徑；title/expected_result/design_rationale 改為明確聚焦於
       「admin 作為隱含上層，本身不是一個帶有站台類型屬性的站台，故 REQ-002 的強制跟隨規則沒有型別
       來源可繼承、因此不會被觸發」這個 inheritance 例外角度，而非重複 AC-0011 已驗證的「可自由選型別」。

Major: TC-DRAFT-01M2NCSW5DRAA52SKEK2PP7534（REQ-SITELIST-017，AC-SITELIST-0172）。
    expected_result_spec_reference.quote 目前逐字擷取自 requirements.yaml REQ-SITELIST-017 的
    rejection_contract.description 欄位（「僅『開通』與『更新待審』兩狀態下的網域異動觸發此規則，
    其餘狀態不觸發」），卻呈現成 spec.md 原文。
    -> 改引 spec.md「站台狀態」表格「更新待審」列 + 「業務規則與驗證」表格「網域異動觸發」列的真實原文，
       並在 design_rationale 中誠實揭露「其餘狀態不觸發」是從這兩處條文（皆只列開通／更新待審兩狀態）
       推導出的否定推論，非 spec.md 逐字包含此句本身。

Minor advisory 1（一併處理）: TC-DRAFT-01M2NCSW5DTY026ESA9BXX381Z（AC-SITELIST-0161）的
    expected_result_spec_reference.quote 混入了非 spec.md 逐字文字（Oscar 於 2026-09-14 確認「任意狀態」
    含待開通的括號註記，該註記本身記載在 RequirementModel 的 spec_reference.quote 欄位，而非 spec.md）。
    -> quote 收斂為純 spec.md 原文「可切換為任意狀態」，確認註記移到 design_rationale。

Minor advisory 2（一併處理）: 全份 draft 裡「取一個既有的 X 站台」這類 precondition，對
    critical_path=true 的高優先案例補充明確的環境佈置 fallback（若環境無現成符合條件的站台，
    依哪一條已設計的 TC 操作路徑自行建立），避免執行者卡在「環境裡到底有沒有這種站台」。
    -> 針對 3 條 critical_path=true 且依賴既有站台環境的 TC（AC-SITELIST-0021/0022、AC-SITELIST-0101、
       AC-SITELIST-0171）補充 fallback 描述。
"""
import sys, pathlib, copy
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids

RUN = "RUN-20260916-007"
TASK = "T2"
ITER = 2
A = "agent-test-designer"
RM_AID = "ART-RM-01M2E2SWZ3GR030YTSZS54E1NE"

OLD_TCD_ID = "ART-TCD-01M2NDK7CFZGE5ZN3V15MX6E1S"
OLD_TDR_ID = "ART-TDR-01M2NDK7DHQX2ZWAR703G0NZRG"

old_tcd = store.load(store.find_artifact(OLD_TCD_ID))
old_tdr = store.load(store.find_artifact(OLD_TDR_ID))

tcd_payload = copy.deepcopy(old_tcd["payload"])
tdr_payload = copy.deepcopy(old_tdr["payload"])

testcases = tcd_payload["testcases"]
by_id = {tc["draft_id"]: tc for tc in testcases}

# ---------------------------------------------------------------------------
# Blocker: TC-DRAFT-01M2NCSW5C4CVZTP2HE4NCEX54 (REQ-SITELIST-002 admin 例外, AC-SITELIST-0023)
# ---------------------------------------------------------------------------
tc_admin = by_id["TC-DRAFT-01M2NCSW5C4CVZTP2HE4NCEX54"]
tc_admin["title"] = "REQ-SITELIST-002 admin 例外角度驗證：根層站台建立情境中，型別不強制繼承自 admin 隱含上層（與 AC-SITELIST-0011 為同一操作路徑）"
tc_admin["steps"] = [
    {"n": 1, "action": "點擊「+ 新增站台」，上層站台留空（此操作路徑與 AC-SITELIST-0011 建立根層站台完全相同——admin 為系統隱含的根節點，並非一個可被選取的站台選項），站台類型選擇「機台」，核心貨幣下拉選單檢視"},
    {"n": 2, "action": "填妥其餘必填欄位後點擊「建立站台」，建立完成後檢視該站台的核心貨幣欄位值"},
]
tc_admin["expected_result"] = (
    "本操作與 AC-SITELIST-0011（TC-DRAFT-01M2NCSW5C2NPYX0YR2ATYY7QA）驗證的操作路徑相同（上層站台留空建立根層站台），"
    "本 TC 不重複斷言「可自由選擇類型」本身；額外驗證的角度是 REQ-SITELIST-002 描述的 inheritance 例外：站台類型欄位"
    "可自由選擇機台，核心貨幣下拉僅出現 TWD 並自動連動建立——因為 admin 作為根層站台的隱含上層，本身並非一個具備"
    "「站台類型」屬性的站台，REQ-002「子站台一律與主站台同類型」的強制跟隨規則因此沒有型別來源可繼承、不會被觸發，"
    "這正是此例外規則在系統中唯一會發生的位置（而非另一條操作上獨立於 AC-0011 之外的路徑）"
)
tc_admin["expected_result_spec_reference"] = {
    "spec_id": "SPEC-SITELIST-001",
    "spec_version": "0.4",
    "location": "REQ-SITELIST-002.statement + history（非 spec.md 章節原文；spec.md §業務規則-站台類型隨主站台僅載一般規則，此 admin 例外為 RequirementModel 記錄之產品確認，未見於 spec.md）",
    "quote": (
        "逐字引用自 requirements.yaml REQ-SITELIST-002.statement：「例外：當上層站台為 admin（最上層根站台）時，"
        "此強制跟隨規則不適用——子站台可自由選擇機台或線上類型，核心貨幣依所選類型連動建立（已由 Oscar 對話直接"
        "確認為真）」。此段非 spec.md 原文；spec.md 僅載一般規則、未見此例外，亦無任何把 admin 列為可選上層站台的 "
        "UI 入口（詳見 design_rationale）。"
    ),
}
tc_admin["design_rationale"] = (
    "選項A：經重新讀取 spec.md v0.4 全文（含 §操作/新增站台 的「上層站台」欄位表格、§業務規則-站台類型隨主站台），"
    "確認「上層站台」欄位的操作方式只有「自動帶入當前所在層／可搜尋改選任意站台」與「留空為根層」兩種，"
    "全文找不到任何「選擇上層站台為 admin」這種獨立於「留空」之外的 UI 操作入口——admin 是角色與系統隱含根節點，"
    "不是一個可被選取的站台實體。因此判定：本 TC 的 step1（上層站台留空、建立根層站台）與 AC-SITELIST-0011"
    "（TC-DRAFT-01M2NCSW5C2NPYX0YR2ATYY7QA）驗證的操作情境，在黑箱可觀察層面是完全相同的一個動作，"
    "並非另一條操作上獨立可執行的路徑，不應假裝它是。"
    "本次修訂已將 title/expected_result 改為明確聚焦於 REQ-SITELIST-002 描述的 inheritance 例外角度本身："
    "『admin 作為隱含上層，本身不是一個帶有站台類型屬性的站台，故 REQ-002 的強制跟隨規則沒有型別來源可繼承、"
    "因此不會被觸發』，而不是重複斷言 AC-SITELIST-0011 已經驗證過的『可自由選擇類型』這件事本身；"
    "expected_result 中也明確點出本 TC 與 AC-0011 為同一操作路徑，避免讓執行者誤以為兩條 TC 在操作步驟上有"
    "任何差異。此 admin 例外規則本身的真實性已由 Oscar 於對話中直接確認為真（requirements.yaml REQ-SITELIST-002 "
    "history 最後一筆記載，取代先前日期矛盾、缺乏 CLR 交叉引用的舊記載），本輪修訂不再重新質疑規則本身，"
    "quote/location 仍誠實揭露此例外文字並非 spec.md 原文、而是 RequirementModel statement 所載的產品確認，"
    "比照 REQ-SITELIST-016 對 Oscar 確認事項的揭露方式。"
    "『不需 admin 自身鏈上錢包管理預先啟用該幣別』一句涉及鏈上錢包管理，該功能不在 SITELIST spec 範圍內，"
    "本 TC 不對鏈上錢包模組本身斷言。"
)

# ---------------------------------------------------------------------------
# Major: TC-DRAFT-01M2NCSW5DRAA52SKEK2PP7534 (REQ-SITELIST-017, AC-SITELIST-0172)
# ---------------------------------------------------------------------------
tc_017 = by_id["TC-DRAFT-01M2NCSW5DRAA52SKEK2PP7534"]
tc_017["expected_result_spec_reference"] = {
    "spec_id": "SPEC-SITELIST-001",
    "spec_version": "0.4",
    "location": "§站台狀態（「更新待審」列） + §業務規則與驗證（「網域異動觸發」列）",
    "quote": (
        "站台狀態表格「更新待審」列：「站台處於『開通』或『更新待審』狀態下，若前台或後台網域有異動，儲存後自動切換」；"
        "業務規則與驗證表格「網域異動觸發」列：「站台為『開通』或『更新待審』時，儲存若有網域新增或刪除，系統自動切為"
        "『更新待審』；適用於所有角色」"
    ),
}
tc_017["design_rationale"] = (
    "iteration 1 版本的 quote 逐字擷取自 requirements.yaml REQ-SITELIST-017 的 rejection_contract.description "
    "欄位（『僅「開通」與「更新待審」兩狀態下的網域異動觸發此規則，其餘狀態不觸發』），卻呈現成 spec.md 原文，"
    "這段話實際上並非 spec.md 逐字文字（Validator 已指出）。本次修訂已改引 spec.md 兩處真實原文——"
    "「站台狀態」表格「更新待審」列的觸發說明，以及「業務規則與驗證」表格「網域異動觸發」列；兩處皆只明確列出"
    "「開通」與「更新待審」兩個狀態會因網域異動而觸發自動切換，未提及任何其他狀態。本 TC 斷言的『待開通/暫停/關閉"
    "狀態下網域異動不觸發』，是從這兩處條文的封閉列舉（只定義了這兩個狀態會觸發，未定義其他狀態也會觸發）推導出的"
    "否定推論，而非 spec.md 逐字包含『其餘狀態不觸發』這句話本身，在此誠實揭露這個推論過程，避免讓執行者誤以為"
    "spec.md 有一句逐字的『其餘狀態不觸發』。REQ-SITELIST-017 的 rejection_contract.defined=true 且以上兩處"
    "原文已足以支撐此推論，design_technique 用 equivalence_partitioning 是因為三個起始狀態（待開通/暫停/關閉）"
    "對同一觸發事件產生完全相同的結果（不觸發），屬同一等價類的多個代表值驗證。"
)

# ---------------------------------------------------------------------------
# Minor advisory 1: TC-DRAFT-01M2NCSW5DTY026ESA9BXX381Z (AC-SITELIST-0161)
# quote 混入非 spec.md 逐字文字（Oscar 確認的括號註記）
# ---------------------------------------------------------------------------
tc_0161 = by_id["TC-DRAFT-01M2NCSW5DTY026ESA9BXX381Z"]
tc_0161["expected_result_spec_reference"] = {
    "spec_id": "SPEC-SITELIST-001",
    "spec_version": "0.4",
    "location": "§角色與權限/狀態切換",
    "quote": "可切換為任意狀態",
}
tc_0161["design_rationale"] = (
    "這是驗證『Admin 可手動選取的狀態集合』這一個等價類（4 種皆可、更新待審不可選）的案例，"
    "equivalence_partitioning 比 decision_table 更貼切，因為這裡不是多條件組合，而是同一角色對同一組"
    "可選值域的驗證。quote 欄位已收斂為 spec.md「角色與權限」表格「狀態切換」列 Admin 欄的純原文"
    "「可切換為任意狀態」；iteration 1 版本的 quote 混入了 requirements.yaml REQ-SITELIST-016 "
    "spec_reference.quote 欄位裡附加的括號註記「（『任意狀態』範圍已於 2026-09-14 由 Oscar 確認含待開通）」，"
    "這段確認記錄本身並非 spec.md 逐字文字，而是 RequirementModel 記載的產品確認（因為 spec.md『站台狀態』表格"
    "的『待開通』觸發方式只列『新建站台自動設定』，未直接列為 Admin 可手動選取的目標狀態，此處存在解讀空間，"
    "已由 Oscar 於 2026-09-14 直接確認『任意狀態』的範圍包含待開通）。本次修訂已將此確認記錄移至此處"
    "design_rationale 說明，expected_result 中保留此註記則是為了讓執行者理解『四種目標狀態皆可切換』這個"
    "斷言範圍的依據，不影響 quote 欄位的純粹性。"
)

# ---------------------------------------------------------------------------
# Minor advisory 2: critical_path=true 且依賴既有站台環境的 TC 補充 fallback
# ---------------------------------------------------------------------------
tc_002_inherit = by_id["TC-DRAFT-01M2NCSW5CF3M957FW8FTEYYS8"]  # AC-SITELIST-0021/0022, critical_path
tc_002_inherit["steps"] = [
    {"n": 1, "action": "取一個既有的機台類型站台（自行從環境中選定，或延用本批次已建立的機台根站台），在其底下點擊「+ 新增站台」，檢視站台類型欄位"},
    {"n": 2, "action": "取一個既有的線上類型站台（自行從環境中選定；若環境中無既有的線上類型站台，可依 AC-SITELIST-0011 的操作路徑，即 TC-DRAFT-01M2NCSW5C2NPYX0YR2ATYY7QA 的 step1，另建一個線上根站台後使用），在其底下點擊「+ 新增站台」，檢視站台類型欄位"},
]

tc_core_ccy = by_id["TC-DRAFT-01M2NCSW5D3W9ZQDASZW5FV4BK"]  # AC-SITELIST-0101, critical_path
tc_core_ccy["steps"] = [
    {"n": 1, "action": "取一個既有的主站台（根層站台，自行從環境中選定；若環境中無合適的既有主站台，可依 AC-SITELIST-0011 的操作路徑，即 TC-DRAFT-01M2NCSW5C2NPYX0YR2ATYY7QA 的 step1，先建立一個後使用），點擊「編輯」，檢視核心貨幣欄位的呈現方式"},
    {"n": 2, "action": "嘗試以瀏覽器操作改變其值，並點擊「儲存變更」，儲存後重新開啟編輯畫面確認"},
]

tc_domain_pending = by_id["TC-DRAFT-01M2NCSW5D9XQCZV6MBVYQ9AQJ"]  # AC-SITELIST-0171, critical_path
tc_domain_pending["steps"] = [
    {"n": 1, "action": "取一個狀態為開通的站台（自行從環境中選定；若環境中無現成的開通狀態站台，可依 AC-SITELIST-0153 的操作路徑，即 TC-DRAFT-01M2NCSW5DZPS5F0FR84FE18P6 的 step1-2，取一個模板已填妥的站台，將狀態切換為開通後使用）"},
    {"n": 2, "action": "編輯該站台，新增一筆前台網域並點擊「儲存變更」"},
    {"n": 3, "action": "檢視站台狀態"},
]

# ---------------------------------------------------------------------------
# TestDesignReport: 本輪修改未變更任何 design_techniques，technique_summary 無需調整
# ---------------------------------------------------------------------------
tdr_payload["revision_of_issues"] = [
    {
        "issue_index": 0,
        "action": (
            "blocker（TC-DRAFT-01M2NCSW5C4CVZTP2HE4NCEX54，AC-SITELIST-0023 操作情境與 AC-SITELIST-0011 無法區分）："
            "重新讀取 spec.md v0.4「操作/新增站台」表格，確認「上層站台」欄位只有「留空為根層」與「搜尋改選任意站台」"
            "兩種操作，無「選擇 admin 為上層」這種獨立 UI 入口，判定為選項A（同一操作情境）；title/expected_result 改為"
            "明確聚焦於『admin 不會把自身型別強加給子站台』這個 inheritance 例外角度，並在 expected_result 中明講"
            "本 TC 與 AC-SITELIST-0011 為同一操作路徑，不再假裝是獨立可執行的路徑。REQ-SITELIST-002 的 admin 例外規則"
            "本身的真實性已由 Oscar 於 2026-09-16 對話中直接確認（requirements.yaml history 已更新），本輪不再質疑"
            "規則真實性，僅處理操作路徑重疊的技術問題。"
        ),
        "draft_id": "TC-DRAFT-01M2NCSW5C4CVZTP2HE4NCEX54",
    },
    {
        "issue_index": 1,
        "action": (
            "major（TC-DRAFT-01M2NCSW5DRAA52SKEK2PP7534，quote 逐字取自 rejection_contract.description 卻呈現成 "
            "spec.md 原文）：改引 spec.md「站台狀態」表格「更新待審」列 + 「業務規則與驗證」表格「網域異動觸發」列的"
            "真實原文，並在 design_rationale 中揭露『其餘狀態不觸發』是從這兩處條文的封閉列舉推導出的否定推論，"
            "非 spec.md 逐字文字。"
        ),
        "draft_id": "TC-DRAFT-01M2NCSW5DRAA52SKEK2PP7534",
    },
    {
        "issue_index": 2,
        "action": (
            "minor advisory（TC-DRAFT-01M2NCSW5DTY026ESA9BXX381Z，quote 混入 Oscar 確認的括號註記）：quote 收斂為純"
            "spec.md 原文「可切換為任意狀態」，確認記錄移至 design_rationale。"
        ),
        "draft_id": "TC-DRAFT-01M2NCSW5DTY026ESA9BXX381Z",
    },
    {
        "issue_index": 3,
        "action": (
            "minor advisory（critical_path=true 的 TC 對『既有站台』的環境佈置缺乏 fallback 說明）：對"
            "TC-DRAFT-01M2NCSW5CF3M957FW8FTEYYS8（AC-0021/0022）、TC-DRAFT-01M2NCSW5D3W9ZQDASZW5FV4BK（AC-0101）、"
            "TC-DRAFT-01M2NCSW5D9XQCZV6MBVYQ9AQJ（AC-0171）補充『若環境中無現成符合條件的站台，依哪一條已設計 TC "
            "的操作路徑自行建立』的具體 fallback 描述。"
        ),
        "draft_id": "*",
    },
]

# ---------------------------------------------------------------------------
# Envelope + submit
# ---------------------------------------------------------------------------
def envelope(artifact_type, payload, references, supersedes=None):
    aid = ids.artifact_id(artifact_type)
    art = {
        "artifact_id": aid, "artifact_type": artifact_type, "schema_version": "1.0", "version": 1,
        "run_id": RUN, "task_id": TASK, "iteration": ITER, "created_by": A, "created_at": store.now(),
        "status": "DRAFT", "source": {"type": "RequirementModel", "ids": [RM_AID]},
        "references": references, "requires_approval": None, "payload": payload,
    }
    if supersedes:
        art["supersedes_artifact_id"] = supersedes
    p = store.ROOT / "artifacts" / "test-design" / RUN / f"{aid}.yaml"
    store.save(p, art)
    return aid, p

tcd_refs = list(old_tcd["references"])
new_tcd_id, tcd_path = envelope("TestCaseDraft", tcd_payload, tcd_refs, supersedes=OLD_TCD_ID)

tdr_payload["testcase_draft_artifact_id"] = new_tcd_id
tdr_refs = [{"entity_type": "Artifact", "id": new_tcd_id}]
new_tdr_id, tdr_path = envelope("TestDesignReport", tdr_payload, tdr_refs, supersedes=OLD_TDR_ID)

print(tcd_path.relative_to(store.ROOT))
print(tdr_path.relative_to(store.ROOT))
print(f"new TCD={new_tcd_id} new TDR={new_tdr_id}")
