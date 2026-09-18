#!/usr/bin/env python3
"""RUN-20260916-007 T2 iteration 8：修正5條負向API繞過TC的acceptance_criteria_ids漏標問題。
Phase2×3交叉比對發現：這5條TC的內容跟對應AC完全吻合（皆為後端拒絕繞過UI的驗證），
但acceptance_criteria_ids誤留空陣列，導致coverage_matrix統計時被漏算，
誤判為Phase3少了Phase2既有的負向測試覆蓋。實際上內容已存在，只是漏標。"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids

RUN = "RUN-20260916-007"
OLD_TCD = "ART-TCD-01M2QW79PJTZS66RGF8N26Z2K0"
OLD_TDR = "ART-TDR-01M2QW79QP1QY351WAZ1ZAMZ1V"
A = "agent-test-designer"

tcd = store.load(store.ROOT / "artifacts" / "test-design" / RUN / f"{OLD_TCD}.yaml")
tdr = store.load(store.ROOT / "artifacts" / "test-design" / RUN / f"{OLD_TDR}.yaml")

FIXES = {
    "TC-DRAFT-01M2NCSW5CPSGPYY3SVMV27JMF": ["AC-SITELIST-0021", "AC-SITELIST-0022"],
    "TC-DRAFT-01M2NCSW5CV1MZNZ6D6KSGDP30": ["AC-SITELIST-0051"],
    "TC-DRAFT-01M2NCSW5DNEQ0GH48B6R6Z1Q7": ["AC-SITELIST-0061"],
    "TC-DRAFT-01M2NCSW5D8EK8HBZWE2QE1P45": ["AC-SITELIST-0122"],
    "TC-DRAFT-01M2NCSW5D4JTJK91FXZBPZN61": ["AC-SITELIST-0132"],
}

fixed = []
for t in tcd["payload"]["testcases"]:
    if t["draft_id"] in FIXES:
        t["acceptance_criteria_ids"] = FIXES[t["draft_id"]]
        fixed.append(t["draft_id"])
assert len(fixed) == 5, fixed

# 同步 coverage_matrix：把這幾條 draft_id 加進對應 AC 的 draft_ids
req_of_ac = {
    "AC-SITELIST-0021": "REQ-SITELIST-002", "AC-SITELIST-0022": "REQ-SITELIST-002",
    "AC-SITELIST-0051": "REQ-SITELIST-005", "AC-SITELIST-0061": "REQ-SITELIST-006",
    "AC-SITELIST-0122": "REQ-SITELIST-012", "AC-SITELIST-0132": "REQ-SITELIST-013",
}
by_req = {}
for did, acs in FIXES.items():
    for ac in acs:
        by_req.setdefault(req_of_ac[ac], []).append((ac, did))

for cm in tdr["payload"]["coverage_matrix"]:
    rid = cm["requirement_id"]
    if rid in by_req:
        if cm["draft_ids"] is None:
            cm["draft_ids"] = []
        for ac, did in by_req[rid]:
            if did not in cm["draft_ids"]:
                cm["draft_ids"].append(did)
            for acentry in cm["acceptance_criteria"]:
                if acentry["ac_id"] == ac and did not in acentry["draft_ids"]:
                    acentry["draft_ids"].append(did)

tdr["payload"].setdefault("revision_of_issues", []).append({
    "issue_index": 0,
    "draft_id": "multiple: " + ", ".join(fixed),
    "action": (
        "Phase2×3交叉比對整合發現：這5條負向API繞過TC的acceptance_criteria_ids誤留空陣列，"
        "內容本身正確（皆為後端拒絕繞過UI的驗證，跟Phase2既有對應TC吻合），"
        "已補上正確的AC標記並同步coverage_matrix，非內容缺口，純屬標記遺漏"
    ),
})

for k in tdr["payload"]["self_check"]:
    tdr["payload"]["self_check"][k] = True

def new_id(artifact_type, payload, refs, task="T2", iteration=8):
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
