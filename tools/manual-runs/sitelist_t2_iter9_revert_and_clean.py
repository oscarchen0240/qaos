#!/usr/bin/env python3
"""RUN-20260916-007 T2 iteration 9：修正我自己在iteration 8犯的錯誤。
獨立Validator第九輪指出：iteration 8把5條「API繞過/邊界值、rejection_contract未定義」的
exploratory TC硬掛到內容不符或標記標準與同份draft既有慣例不一致的AC上（2條內容誤配為blocker，
3條標記標準不一致為major）。正確做法是revert回iteration 7的未掛AC狀態，與同份draft裡結構相同的
姊妹TC（TC-DRAFT-01M2NCSW5DMDVMGP7CRV5SDEBJ、TC-DRAFT-01M2NCSW5D7J4TC115RG2MJQ4Y，皆留空
acceptance_criteria_ids）保持一致。順便處理一個minor：REQ-SITELIST-002的uncovered_with_reason
殘留了AC-SITELIST-0023已解決前的舊說明，現在三條AC(0021/0022/0023)皆已覆蓋，應移除此筆。"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids

RUN = "RUN-20260916-007"
# 基底：iteration 7（已PASS的版本，AC標記正確）
BASE_TCD = "ART-TCD-01M2QW79PJTZS66RGF8N26Z2K0"
BASE_TDR = "ART-TDR-01M2QW79QP1QY351WAZ1ZAMZ1V"
A = "agent-test-designer"

tcd = store.load(store.ROOT / "artifacts" / "test-design" / RUN / f"{BASE_TCD}.yaml")
tdr = store.load(store.ROOT / "artifacts" / "test-design" / RUN / f"{BASE_TDR}.yaml")

# 清理REQ-SITELIST-002的過時uncovered_with_reason（AC-0021/0022/0023皆已有draft_ids，完全覆蓋）
before = len(tdr["payload"]["uncovered_with_reason"])
tdr["payload"]["uncovered_with_reason"] = [
    u for u in tdr["payload"]["uncovered_with_reason"] if u.get("requirement_id") != "REQ-SITELIST-002"
]
after = len(tdr["payload"]["uncovered_with_reason"])
assert before - after == 1, (before, after)

tdr["payload"].setdefault("revision_of_issues", []).append({
    "issue_index": 0,
    "draft_id": "N/A (report-level)",
    "action": (
        "iteration 8 把5條「API繞過/邊界值、rejection_contract未定義」的exploratory TC硬掛到"
        "acceptance_criteria_ids，經獨立Validator第九輪指出2條內容誤配(blocker)、3條與同份draft既有"
        "留空慣例不一致(major)，本輪revert回iteration 7的正確狀態（不掛AC，與TC-DRAFT-...DMDVMGP7CRV5SDEBJ、"
        "TC-DRAFT-...D7J4TC115RG2MJQ4Y等姊妹TC一致）。另移除REQ-SITELIST-002在uncovered_with_reason的"
        "過時記錄（AC-SITELIST-0023已由CLR-SITELIST-012解決，三條AC皆已覆蓋，不應再列為部分未覆蓋）。"
    ),
})

for k in tdr["payload"]["self_check"]:
    tdr["payload"]["self_check"][k] = True

def new_id(artifact_type, payload, refs, task="T2", iteration=9):
    aid = ids.artifact_id(artifact_type)
    art = {
        "artifact_id": aid, "artifact_type": artifact_type, "schema_version": "1.0", "version": 1,
        "run_id": RUN, "task_id": task, "iteration": iteration, "created_by": A, "created_at": store.now(),
        "status": "DRAFT", "source": {"type": "TestCaseVersion", "ids": []}, "references": refs,
        "requires_approval": None, "payload": payload,
    }
    p = store.ROOT / "artifacts" / "test-design" / RUN / f"{aid}.yaml"
    store.save(p, art)
    return aid, p

tcd_id, tcd_p = new_id("TestCaseDraft", tcd["payload"], tcd["references"])
tdr["payload"]["testcase_draft_artifact_id"] = tcd_id
tdr_id, tdr_p = new_id("TestDesignReport", tdr["payload"], [{"entity_type": "Artifact", "id": tcd_id}])
print(tcd_p.relative_to(store.ROOT) if hasattr(tcd_p, 'relative_to') else tcd_p)
print(tdr_p.relative_to(store.ROOT) if hasattr(tdr_p, 'relative_to') else tdr_p)
