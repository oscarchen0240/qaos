#!/usr/bin/env python3
"""RUN-20260916-002 T2（iteration 1）：回應 ART-TVR-01M2MCBGSSWE7THQ3ZTC429P56 的 FAIL。

修正範圍（其餘 43 條 TC 原封不動照抄自 iteration 0）：
1. major/missing_coverage：REQ-CASHFLOW-008 的 statement 已於 2026-09-15 由 Oscar 更正移除「Admin／站長於交易紀錄手動取消」
   這條入金 PENDING 收斂路徑（交易紀錄查詢頁不存在手動取消功能，洗分出金核實頁的「作廢」僅適用已完成出金交易），但其下
   AC-CASHFLOW-0083（given/when/then 及 states 欄位）在 RequirementModel 中尚未同步更新，仍描述這條已被否定的操作路徑。
   判定：AC-CASHFLOW-0083 描述的操作在實際系統中不存在，故不再適用，於 uncovered_with_reason 記載理由（比照
   REQ-CASHFLOW-026／AC-CASHFLOW-0261 的既有處理方式），coverage_matrix 中明確列出 AC-CASHFLOW-0083: draft_ids=[]。
   同時補上 TC-DRAFT-...BHQFH（AC-0081）與 TC-DRAFT-...R9NWHN（AC-0082）原本空白的 design_rationale。
2. minor/technique_mismatch x3：以下三條 TC 標記 decision_table 但實際僅為二元對照或單一結果的條件判斷，非多條件交叉矩陣，
   改標為 equivalence_partitioning：
   - TC-DRAFT-01M2MBHFR6DWN957ZRBKQNHYGF（列印異常：列印前 vs 列印後兩情境）
   - TC-DRAFT-01M2MBHFR73WF9S3D39DM64KQJ（餘額不足 vs 其餘原因二元對照）
   - TC-DRAFT-01M2MBHFR7AN6YRP73P88CB402（機台停用/站台非開通 → 單一結果 7-OUT OF SERVICE）
   TC-DRAFT-01M2MBHFR7GAYKTSCJ7ZSNGAF1（五種未成立原因對應五種狀態碼）維持 decision_table，未動。
"""
import sys, pathlib, copy, collections
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids

RUN = "RUN-20260916-002"
TASK = "T2"
AGENT = "agent-test-designer"
OLD_TCD_ID = "ART-TCD-01M2MBHFR84GTKRE91A7V17TX0"
OLD_TDR_ID = "ART-TDR-01M2MBHFS65E95JBSSJ6BYXE4W"
OLD_TCD_PATH = f"artifacts/test-design/{RUN}/{OLD_TCD_ID}.yaml"
OLD_TDR_PATH = f"artifacts/test-design/{RUN}/{OLD_TDR_ID}.yaml"

old_tcd = store.load(OLD_TCD_PATH)
old_tdr = store.load(OLD_TDR_PATH)

tcd_payload = copy.deepcopy(old_tcd["payload"])
tdr_payload = copy.deepcopy(old_tdr["payload"])

tcs_by_id = {tc["draft_id"]: tc for tc in tcd_payload["testcases"]}

# ---------------------------------------------------------------------------
# 1. REQ-CASHFLOW-008 / AC-CASHFLOW-0083：補 design_rationale
# ---------------------------------------------------------------------------
AC0083_NOTE = (
    "同需求下的 AC-CASHFLOW-0083（Admin/站長於交易紀錄手動取消入金 PENDING）因 statement 已於 2026-09-15 由 Oscar 確認更正"
    "（該操作路徑不存在於實際系統：交易紀錄查詢頁無手動取消功能，洗分出金核實頁的「作廢」僅適用已完成出金交易），"
    "本設計判斷該 AC 不再適用，已於 TestDesignReport.uncovered_with_reason 記載理由，不設計對應 TC。"
)

bkyk = tcs_by_id["TC-DRAFT-01M2MBHFR6BKYKP99P5GHBHQFH"]
bkyk["design_rationale"] = (
    "依 AC-CASHFLOW-0081 設計：以 requirement_based 驗證 spec 明定的『入帳成功時預留轉為實際分數餘額』，"
    "並以 state_transition 驗證 PENDING(已預留)→已完成(轉實際餘額) 這個狀態轉換是否讓分數真正可用（不只是帳面數字改變，"
    "而是能被後續洗分/出金實際動用）；額外以 error_guessing 補測轉正後同一 TXID 再次呼叫 end-cashin 是否仍具備 "
    "REQ-CASHFLOW-011 定義的冪等性。本 TC 僅涵蓋 AC-CASHFLOW-0081。" + AC0083_NOTE
)

r9nwhn = tcs_by_id["TC-DRAFT-01M2MBHFR6D578YPFV41R9NWHN"]
r9nwhn["design_rationale"] = (
    "依 AC-CASHFLOW-0082 與 AC-CASHFLOW-0122 設計，以 state_transition 驗證 spec 明定的『PENDING(已預留)→已逾時(釋放)』"
    "狀態轉換，並確認預留額度確實自場館額度計算中釋放（而非僅狀態文字改變）。24 小時逾時的測試資料佈置方式為推測，"
    "已誠實標記於 assumptions 並要求環境負責人確認是否有可加速判定的測試機制。本 TC 僅涵蓋 AC-CASHFLOW-0082。" + AC0083_NOTE
)

# ---------------------------------------------------------------------------
# 2. 三條 technique_mismatch 修正：decision_table -> equivalence_partitioning
# ---------------------------------------------------------------------------
dwn = tcs_by_id["TC-DRAFT-01M2MBHFR6DWN957ZRBKQNHYGF"]
dwn["design_techniques"] = ["equivalence_partitioning", "error_guessing"]
dwn["design_rationale"] = dwn["design_rationale"] + (
    " 修正：原標記 decision_table，但本 TC 實際僅為『列印尚未開始就異常』與『已送入列印佇列後才故障』兩個等價類"
    "（故障發生於列印前 vs 列印後）各自對應單一結果的對照，並非多條件交叉組合出不同結果的決策矩陣，改標為 "
    "equivalence_partitioning 更能反映實際判斷邏輯，error_guessing 維持不變。"
)

wf9 = tcs_by_id["TC-DRAFT-01M2MBHFR73WF9S3D39DM64KQJ"]
wf9["design_techniques"] = ["equivalence_partitioning"]
wf9["design_rationale"] = (
    "驗證『餘額不足（1-NO CREDITS）』與『其餘未成立原因（如額度上限）』兩個等價類各自是否寫入交易紀錄的差異——"
    "這是二元對照而非多條件交叉組合出不同結果的決策矩陣，故標記為 equivalence_partitioning（原先誤標 decision_table）；"
    "此差異容易被誤以為『所有拒絕都會留紀錄』，是本規則的核心風險點，故仍以 high risk 對待。"
)

an6y = tcs_by_id["TC-DRAFT-01M2MBHFR7AN6YRP73P88CB402"]
an6y["design_techniques"] = ["equivalence_partitioning"]
an6y["design_rationale"] = (
    "驗證『機台停用』與『所屬場館站台非開通』兩個各自獨立的觸發條件，是否皆收斂為同一結果（7-OUT OF SERVICE）——"
    "這是兩個等價類分別映射至相同結果的對照，而非多條件交叉出不同結果的決策矩陣，故標記為 equivalence_partitioning"
    "（原先誤標 decision_table）。"
)

# ---------------------------------------------------------------------------
# 重新計算 technique_summary（以最終 testcases 為準，避免手算出錯）
# ---------------------------------------------------------------------------
tech_count = collections.Counter(t for tc in tcd_payload["testcases"] for t in tc["design_techniques"])
tdr_payload["technique_summary"] = [{"technique": k, "count": v} for k, v in tech_count.items()]

# ---------------------------------------------------------------------------
# coverage_matrix：REQ-CASHFLOW-008 明確列出 AC-CASHFLOW-0083（draft_ids=[]）表示已考慮但判定不適用
# ---------------------------------------------------------------------------
for row in tdr_payload["coverage_matrix"]:
    if row["requirement_id"] == "REQ-CASHFLOW-008":
        ac_ids_present = {a["ac_id"] for a in row["acceptance_criteria"]}
        if "AC-CASHFLOW-0083" not in ac_ids_present:
            row["acceptance_criteria"].append({"ac_id": "AC-CASHFLOW-0083", "draft_ids": []})
        break

# ---------------------------------------------------------------------------
# uncovered_with_reason：補上 REQ-CASHFLOW-008 / AC-CASHFLOW-0083 的落差理由
# ---------------------------------------------------------------------------
tdr_payload["uncovered_with_reason"].append({
    "requirement_id": "REQ-CASHFLOW-008",
    "reason": (
        "AC-CASHFLOW-0083（given: PENDING 有預留額度；when: Admin 或站長於交易紀錄手動取消；then: 預留額度立即釋放）："
        "REQ-CASHFLOW-008 的 statement 已於 2026-09-15 由 Oscar 確認更正（history 記載 "
        "CLR-CASHFLOW-004_applied_2026-09-15），明確移除『Admin／站長手動取消』這條入金 PENDING 收斂路徑——"
        "交易紀錄查詢頁不存在手動取消功能，洗分出金核實頁的『作廢』操作僅適用於已完成的出金交易，範圍對不上待確認狀態"
        "的入金 PENDING。但 RequirementModel 中 AC-CASHFLOW-0083 本身（given/when/then）與 states 欄位的人工取消轉換"
        "尚未同步更新，仍描述這條已被否定的操作路徑，屬 RequirementModel 內部 statement 與 AC 的資料落差（非本次設計"
        "新增問題）。對照 REQ-CASHFLOW-026：該需求的 AC-CASHFLOW-0261 已於同一次更正中被直接改寫為與更正後 statement "
        "一致（明確記載『不存在「Admin 手動取消」這個操作』），而 REQ-CASHFLOW-008 的 AC-CASHFLOW-0083 尚未同步。"
        "由於 AC-CASHFLOW-0083 描述的操作在實際系統中不存在，本設計判斷該 AC 不再適用，不設計對應 TC；"
        "REQ-CASHFLOW-008 的其餘 AC（AC-CASHFLOW-0081、AC-CASHFLOW-0082）已分別由 "
        "TC-DRAFT-01M2MBHFR6BKYKP99P5GHBHQFH、TC-DRAFT-01M2MBHFR6D578YPFV41R9NWHN 涵蓋。建議另行提出 "
        "Clarification/CLR，請 RequirementModel 維護者同步修正 AC-CASHFLOW-0083 與 states 欄位中對應的人工取消轉換，"
        "使其與已更正的 statement 一致（可能改寫為否定式驗收條件，或直接移除）。"
    ),
})

# ---------------------------------------------------------------------------
# revision_of_issues：逐條回應 ART-TVR-01M2MCBGSSWE7THQ3ZTC429P56.issues
# ---------------------------------------------------------------------------
tdr_payload["revision_of_issues"] = [
    {
        "issue_index": 0,
        "action": (
            "重新判斷 AC-CASHFLOW-0083 是否適用於已更正的 REQ-CASHFLOW-008 statement：確認該 AC 描述的『Admin/站長"
            "手動取消』操作已於 2026-09-15 被 Oscar 確認不存在於實際系統，判定不再適用；已於 uncovered_with_reason "
            "明確記載理由（比照 REQ-CASHFLOW-026 的處理方式），coverage_matrix 中 REQ-CASHFLOW-008 的 "
            "acceptance_criteria 明確列出 AC-CASHFLOW-0083: draft_ids=[] 以顯示已考慮但判定不適用；同時補上原本空白的 "
            "TC-DRAFT-01M2MBHFR6BKYKP99P5GHBHQFH 與 TC-DRAFT-01M2MBHFR6D578YPFV41R9NWHN 的 design_rationale。"
        ),
    },
    {
        "issue_index": 1,
        "action": "design_techniques 由 decision_table 改為 equivalence_partitioning（列印異常僅為列印前/列印後兩個等價類各自對應單一結果，非多條件交叉矩陣）",
        "draft_id": "TC-DRAFT-01M2MBHFR6DWN957ZRBKQNHYGF",
    },
    {
        "issue_index": 2,
        "action": "design_techniques 由 decision_table 改為 equivalence_partitioning（餘額不足 vs 其餘原因為二元對照，非多條件交叉矩陣），並補上原本空白的 design_rationale",
        "draft_id": "TC-DRAFT-01M2MBHFR73WF9S3D39DM64KQJ",
    },
    {
        "issue_index": 3,
        "action": "design_techniques 由 decision_table 改為 equivalence_partitioning（機台停用/站台非開通為兩個各自獨立條件收斂至同一結果，非多條件交叉出不同結果的矩陣），並補上原本空白的 design_rationale",
        "draft_id": "TC-DRAFT-01M2MBHFR7AN6YRP73P88CB402",
    },
]

# ---------------------------------------------------------------------------
# 組 envelope 並寫檔
# ---------------------------------------------------------------------------
def envelope(artifact_type, payload, references, source):
    aid = ids.artifact_id(artifact_type)
    art = {
        "artifact_id": aid, "artifact_type": artifact_type, "schema_version": "1.0", "version": 1,
        "run_id": RUN, "task_id": TASK, "iteration": 1, "created_by": AGENT, "created_at": store.now(),
        "status": "DRAFT", "source": source, "references": references, "requires_approval": None,
        "payload": payload,
    }
    p = store.ROOT / "artifacts" / "test-design" / RUN / f"{aid}.yaml"
    store.save(p, art)
    return aid, p

tcd_aid, tcd_p = envelope(
    "TestCaseDraft", tcd_payload,
    copy.deepcopy(old_tcd["references"]),
    copy.deepcopy(old_tcd["source"]),
)
tdr_payload["testcase_draft_artifact_id"] = tcd_aid
tdr_aid, tdr_p = envelope(
    "TestDesignReport", tdr_payload,
    [{"entity_type": "Artifact", "id": tcd_aid}],
    copy.deepcopy(old_tdr["source"]),
)

print(tcd_p.relative_to(store.ROOT))
print(tdr_p.relative_to(store.ROOT))
print(f"testcases: {len(tcd_payload['testcases'])}")
print("technique_summary:", dict(tech_count))
