#!/usr/bin/env python3
"""RUN-20260916-007 T2 iteration 1：依 ART-TVR-01M2ND9N1GT6MM5Z8JFGKFCC6R 的 issues/advisories 修訂
iteration 0 (ART-TCD-01M2NCSW5FJC0WN8ZKSTHXTYXV / ART-TDR-01M2NCSW6SMSKYNNSWM73849MD)。

不重新設計，僅針對 Validator 指出的問題做最小必要修改，其餘 TC 原封不動照抄。

Major issue 1: AC-SITELIST-0072 完全沒出現在 coverage_matrix / uncovered_with_reason，
    只藏在 TC-DRAFT-01M2NCSW5D04F7MWHF69J8YXQQ 的 design_rationale 文字裡。
    -> 在 coverage_matrix 補上 AC-SITELIST-0072（draft_ids: []，因其驗證效果不在 SITELIST 範圍內），
       並在 uncovered_with_reason 新增一筆 CROSS_SPEC_BOUNDARY 說明。

Major issue 2: TC-DRAFT-01M2NCSW5C4CVZTP2HE4NCEX54 的 expected_result_spec_reference.quote
    呈現成 spec.md 原文，實際上逐字擷取自 requirements.yaml REQ-SITELIST-002 的 statement 欄位
    （2026-09-15 Oscar 產品確認），spec.md 本身沒有這段例外文字。
    -> 改標 location 指向 statement，quote/design_rationale 明確揭露此非 spec.md 原文，
       比照 REQ-SITELIST-016 對 Oscar 確認事項的揭露方式。

Minor advisory 1（一併處理）: AC-SITELIST-0111/0112 標 security_rule 但本質是無限制/預設範圍的
    正向展示，未觸發任何拒絕/繞過機制 -> 改標 requirement_based；AC-SITELIST-0113（實際拒絕驗證）
    維持 security_rule 不變。

Minor advisory 2（一併處理）: REQ-SITELIST-023 的 uncovered_with_reason 用 NO_REJECTION_CONTRACT:
    前綴，但理由核心其實是「刪除功能不存在（moot）」-> 保留該前綴（G-DESIGN 結構化檢查以此前綴
    豁免 high risk 無 non-happy TC 的規則，機制上不支援改用其他前綴），但在理由文字中額外標註
    本質為 MOOT_REQUIREMENT，避免標籤名稱與理由性質不對應造成誤解。
"""
import sys, pathlib, copy
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids

RUN = "RUN-20260916-007"
TASK = "T2"
ITER = 1
A = "agent-test-designer"
RM_AID = "ART-RM-01M2E2SWZ3GR030YTSZS54E1NE"
TVR_AID = "ART-TVR-01M2ND9N1GT6MM5Z8JFGKFCC6R"

OLD_TCD_ID = "ART-TCD-01M2NCSW5FJC0WN8ZKSTHXTYXV"
OLD_TDR_ID = "ART-TDR-01M2NCSW6SMSKYNNSWM73849MD"

old_tcd = store.load(store.find_artifact(OLD_TCD_ID))
old_tdr = store.load(store.find_artifact(OLD_TDR_ID))

tcd_payload = copy.deepcopy(old_tcd["payload"])
tdr_payload = copy.deepcopy(old_tdr["payload"])

testcases = tcd_payload["testcases"]
by_id = {tc["draft_id"]: tc for tc in testcases}

# ---------------------------------------------------------------------------
# Major issue 2: TC-DRAFT-01M2NCSW5C4CVZTP2HE4NCEX54 (REQ-SITELIST-002 admin 例外)
# ---------------------------------------------------------------------------
tc2 = by_id["TC-DRAFT-01M2NCSW5C4CVZTP2HE4NCEX54"]
tc2["expected_result_spec_reference"] = {
    "spec_id": "SPEC-SITELIST-001",
    "spec_version": "0.4",
    "location": "REQ-SITELIST-002.statement（非 spec.md 章節原文；spec.md §業務規則-站台類型隨主站台僅載一般規則，此 admin 例外為 RequirementModel 記錄之產品確認，未見於 spec.md）",
    "quote": (
        "逐字引用自 requirements.yaml 中 REQ-SITELIST-002 的 statement 欄位："
        "「例外：當上層站台為 admin（最上層根站台）時，此強制跟隨規則不適用——底下子站台可自由選擇機台或線上類型，"
        "核心貨幣依所選類型連動建立（已由 Oscar 2026-09-15 確認，此為先前上報問題後調整定案的行為，非本次新發現缺陷）」。"
        "此段文字並非 spec.md 原文——spec.md（§業務規則-站台類型隨主站台）僅記載一般規則"
        "「站台類型於主站台（根層）選定，子站台一律與主站台同類型、不可個別選擇」，未見此 admin 例外。"
    ),
}
tc2["design_rationale"] = (
    "此 AC 描述的『上層站台為 admin』例外規則，經逐字比對 spec.md v0.4 全文（含 §業務規則-站台類型隨主站台），"
    "僅找到一般規則『子站台一律與主站台同類型、不可個別選擇』，未見 admin 例外文字；此例外僅記載於 "
    "RequirementModel（requirements.yaml）REQ-SITELIST-002 的 statement 欄位，並註明『已由 Oscar 2026-09-15 確認，"
    "此為先前上報問題後調整定案的行為』。iteration 0 版本曾將這段 statement 文字誤置於 expected_result_spec_reference.quote，"
    "呈現方式讓人誤以為 spec.md 該章節直接記載此例外（Validator issue 指出）；本次修訂已將 location/quote 改為明確指向 "
    "statement 欄位並在 quote 內文揭露『此段文字並非 spec.md 原文』，比照 REQ-SITELIST-016 對 Oscar 確認事項的揭露方式。"
    "『不需 admin 自身鏈上錢包管理預先啟用該幣別』一句涉及鏈上錢包管理，該功能不在 SITELIST spec 範圍內，本 TC 僅驗證"
    "『沒有出現任何阻擋提示』這個可觀察到的否定事實，不對鏈上錢包模組本身斷言。"
)

# ---------------------------------------------------------------------------
# Minor advisory 1: AC-SITELIST-0111/0112 security_rule -> requirement_based
# ---------------------------------------------------------------------------
tc_ac0111 = by_id["TC-DRAFT-01M2NCSW5DR4JG223M8GXZ98HJ"]
tc_ac0111["design_techniques"] = ["requirement_based"]
tc_ac0111["design_rationale"] = (
    "此為 Admin 可見範圍規則的正向展示案例——顯示『無限制』這個預設狀態，過程未觸發任何拒絕或範圍限制的判斷邏輯，"
    "依 Validator advisory 改標 requirement_based（原標 security_rule 較貼合『驗證拒絕/限制被觸發』的案例，"
    "例如 AC-SITELIST-0113 才是真正繞不過去的拒絕驗證，繼續保留 security_rule）。"
)

tc_ac0112 = by_id["TC-DRAFT-01M2NCSW5D7HSAZ2GV8MSA3FE9"]
tc_ac0112["design_techniques"] = ["requirement_based"]
tc_ac0112["design_rationale"] = (
    "與 AC-SITELIST-0111（Admin 的正向對照案例）同樣是『預設可見範圍』的正向展示，本身未觸發任何拒絕/繞過機制，"
    "依 Validator advisory 改標 requirement_based，並與 AC-0111 保持一致標記，避免對稱情境貼不同技巧標籤；"
    "真正涉及『範圍外存取被拒絕』的驗證留給 AC-SITELIST-0113（security_rule）與 API 繞過案例負責。"
)

# ---------------------------------------------------------------------------
# TestDesignReport: technique_summary 需與上面兩處異動同步
# ---------------------------------------------------------------------------
tech_summary = {row["technique"]: row["count"] for row in tdr_payload["technique_summary"]}
tech_summary["security_rule"] -= 2
tech_summary["requirement_based"] = tech_summary.get("requirement_based", 0) + 2
tdr_payload["technique_summary"] = [{"technique": k, "count": v} for k, v in tech_summary.items() if v]

# ---------------------------------------------------------------------------
# Major issue 1: AC-SITELIST-0072 補進 coverage_matrix + uncovered_with_reason
# ---------------------------------------------------------------------------
for row in tdr_payload["coverage_matrix"]:
    if row["requirement_id"] == "REQ-SITELIST-007":
        row["acceptance_criteria"].append({"ac_id": "AC-SITELIST-0072", "draft_ids": []})
        break

tdr_payload["uncovered_with_reason"].append({
    "requirement_id": "REQ-SITELIST-007",
    "reason": (
        "CROSS_SPEC_BOUNDARY: AC-SITELIST-0072（報表依日結時間切分營業日）之斷言效果驗證點在 "
        "SPEC-DAILYREPORT-001 REQ-007（日結報表分日邏輯），不在 SITELIST 頁面本身可觀察範圍內；"
        "requirement.acceptance_criteria 原文本身也已註明『見 SPEC-DAILYREPORT-001 REQ-007』。"
        "本次任務範圍僅限 SITELIST 的 29 條需求，SITELIST 範圍內的部分（AC-SITELIST-0071：日結時間可設定並儲存）"
        "已由 TC-DRAFT-01M2NCSW5D04F7MWHF69J8YXQQ 覆蓋；AC-SITELIST-0072 本身的切分效果驗證需另由 "
        "SPEC-DAILYREPORT-001 對應的 Test Designer 任務負責，故此處明確列為 uncovered，不代表本次設計遺漏。"
        "（iteration 0 版本僅將此說明藏於該 TC 的 design_rationale 文字中，未走正式的 coverage_matrix / "
        "uncovered_with_reason 記載，已依 Validator issue 修正。）"
    ),
})

# ---------------------------------------------------------------------------
# Minor advisory 2: REQ-SITELIST-023 的 NO_REJECTION_CONTRACT 前綴補充說明
# 保留前綴：G-DESIGN 結構化檢查以 reason.startswith("NO_REJECTION_CONTRACT:") 判斷是否豁免
# high-risk 無 non-happy TC 的規則，系統目前不支援其他前綴分類，故不能改前綴，只能在文字內補充澄清。
# ---------------------------------------------------------------------------
for u in tdr_payload["uncovered_with_reason"]:
    if u["requirement_id"] == "REQ-SITELIST-023":
        assert u["reason"].startswith("NO_REJECTION_CONTRACT:")
        u["reason"] = (
            "NO_REJECTION_CONTRACT:（Validator advisory：本質更接近 MOOT_REQUIREMENT——刪除功能前後端皆不存在，"
            "此需求描述的情境根本不會發生，不只是『拒絕契約未定義』；因系統目前僅支援 NO_REJECTION_CONTRACT: "
            "此一前綴作為 high-risk 無 non-happy TC 的結構化豁免標記，故保留此前綴，於此補充澄清實際理由性質。）"
            + u["reason"][len("NO_REJECTION_CONTRACT:"):]
        )
        break

# ---------------------------------------------------------------------------
# revision_of_issues：逐條回應 ART-TVR-01M2ND9N1GT6MM5Z8JFGKFCC6R.payload.issues / advisories
# issue_index 對應該份報告 issues[] 陣列的索引（0-based）；advisories 另外備註
# ---------------------------------------------------------------------------
tdr_payload["revision_of_issues"] = [
    {
        "issue_index": 0,
        "action": (
            "major/missing_coverage（AC-SITELIST-0072）：在 coverage_matrix 的 REQ-SITELIST-007 列補上 "
            "acceptance_criteria 條目 AC-SITELIST-0072（draft_ids: []），並在 uncovered_with_reason 新增一筆 "
            "CROSS_SPEC_BOUNDARY 說明其驗證效果屬 SPEC-DAILYREPORT-001 REQ-007 責任範圍，不再只藏於 "
            "TC-DRAFT-01M2NCSW5D04F7MWHF69J8YXQQ 的 design_rationale 文字裡。"
        ),
        "draft_id": "TC-DRAFT-01M2NCSW5D04F7MWHF69J8YXQQ",
    },
    {
        "issue_index": 1,
        "action": (
            "major/spec_mismatch（TC-DRAFT-01M2NCSW5C4CVZTP2HE4NCEX54）：expected_result_spec_reference 改標 "
            "location 指向 REQ-SITELIST-002.statement，quote 內文明確揭露此段文字逐字引用自 requirements.yaml 的 "
            "statement 欄位、並非 spec.md 原文，spec.md 本身僅記載一般規則；design_rationale 同步更新，比照 "
            "REQ-SITELIST-016 對 Oscar 確認事項的揭露方式。"
        ),
        "draft_id": "TC-DRAFT-01M2NCSW5C4CVZTP2HE4NCEX54",
    },
    {
        "issue_index": 2,
        "action": (
            "minor advisory（AC-SITELIST-0111/0112 technique_mismatch）：design_techniques 由 security_rule 改為 "
            "requirement_based（正向展示、未觸發拒絕/限制機制），AC-SITELIST-0113 與 API 繞過案例維持 security_rule；"
            "technique_summary 同步調整（security_rule 14→12，requirement_based 24→26）。"
        ),
        "draft_id": "TC-DRAFT-01M2NCSW5DR4JG223M8GXZ98HJ",
    },
    {
        "issue_index": 3,
        "action": (
            "minor advisory（REQ-SITELIST-023 uncovered_with_reason 分類名稱）：系統的 G-DESIGN 結構化檢查僅支援 "
            "NO_REJECTION_CONTRACT: 前綴作為 high-risk 無 non-happy TC 的豁免標記，無法改標其他分類前綴而不破壞結構檢查；"
            "已在理由文字開頭補充『本質更接近 MOOT_REQUIREMENT』的澄清，保留前綴不變。"
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

tcd_refs = list(old_tcd["references"])  # 沿用 iteration 0 的 requirement 引用清單（未增刪覆蓋的 requirement）
new_tcd_id, tcd_path = envelope("TestCaseDraft", tcd_payload, tcd_refs, supersedes=OLD_TCD_ID)

tdr_payload["testcase_draft_artifact_id"] = new_tcd_id
tdr_refs = [{"entity_type": "Artifact", "id": new_tcd_id}, {"entity_type": "Artifact", "id": TVR_AID}]
new_tdr_id, tdr_path = envelope("TestDesignReport", tdr_payload, tdr_refs, supersedes=OLD_TDR_ID)

print(tcd_path.relative_to(store.ROOT))
print(tdr_path.relative_to(store.ROOT))
print(f"new TCD={new_tcd_id} new TDR={new_tdr_id}")
