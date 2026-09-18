#!/usr/bin/env python3
"""RUN-20260918-001 T2 iteration 1：修正TC-DRAFT-01M2R29PNMXV0DH63DKNF2ZMM6的quote揭露缺失。
獨立Validator指出：此TC的quote拿掉了REQ-TXLOG-017自己spec_reference.quote裡已有的揭露註記
（原文「或由Admin手動取消為止」已確認為錯誤敘述），跟同批其他TC(REQ-025/026/028)的揭露慣例不一致。
直接比照REQ-TXLOG-017本身的spec_reference.quote補回揭露註記。"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids

RUN = "RUN-20260918-001"
OLD_TCD = "ART-TCD-01M2R29PNQKKA7V3GWN6PHYTPW"
OLD_TDR = "ART-TDR-01M2R29PPJQ4ZGZD6951S1HW9R"
A = "agent-test-designer"

tcd = store.load(store.ROOT / "artifacts" / "test-design" / RUN / f"{OLD_TCD}.yaml")
tdr = store.load(store.ROOT / "artifacts" / "test-design" / RUN / f"{OLD_TDR}.yaml")

TARGET = "TC-DRAFT-01M2R29PNMXV0DH63DKNF2ZMM6"
for t in tcd["payload"]["testcases"]:
    if t["draft_id"] == TARGET:
        t["expected_result_spec_reference"]["quote"] = (
            "出金不設逾時，待確認會一直保留，直到機台補完回報、被新的出金取代、櫃檯人工出金連動取消，"
            "或轉介至「洗分出金核實」頁人工處理（原文「或由 Admin 手動取消為止」已由 Oscar 2026-09-14 "
            "確認為錯誤敘述，見 REQ-TXLOG-028）"
        )
        t["expected_result_spec_reference"]["location"] = "§交易狀態 + §相關業務規則"
        break
else:
    raise SystemExit("not found")

tdr["payload"].setdefault("revision_of_issues", []).append({
    "issue_index": 0,
    "draft_id": TARGET,
    "action": (
        "補回quote的揭露註記（原文已確認為錯誤敘述），比照REQ-TXLOG-017自己spec_reference.quote"
        "的既有寫法，與同批其他TC(REQ-025/026/028)的揭露慣例一致"
    ),
})
for k in tdr["payload"]["self_check"]:
    tdr["payload"]["self_check"][k] = True

def new_id(artifact_type, payload, refs, task="T2", iteration=1):
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
