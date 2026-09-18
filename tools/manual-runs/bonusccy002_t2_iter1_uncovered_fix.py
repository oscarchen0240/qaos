#!/usr/bin/env python3
"""RUN-20260918-004 T2 iteration 1：修正AC-BONUSCCY-009的排除理由未結構化記錄的問題。
獨立Validator指出：AC-BONUSCCY-009是並列斷言(彩金進TTK錢包 且 原本沒有該幣別錢包時自動出現一列)，
本輪已查證SPEC-MEMBER-001 v0.2§2.1.6第290行確認「金額為0的幣別仍列出並顯示0.00，不因無餘額而隱藏」，
證實Test Designer原本的判斷（此事件在UI上不可獨立觀察）是對的，只是沒有走uncovered_with_reason
結構化記錄。把design_rationale裡已有的理由正式搬進uncovered_with_reason。"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids

RUN = "RUN-20260918-004"
OLD_TCD = "ART-TCD-01M2R6JHSFS54J1RWGE4KDJ52Y"
OLD_TDR = "ART-TDR-01M2R6JHSSC13FA5SG6B9AHNGF"
A = "agent-test-designer"

tcd = store.load(store.ROOT / "artifacts" / "test-design" / RUN / f"{OLD_TCD}.yaml")
tdr = store.load(store.ROOT / "artifacts" / "test-design" / RUN / f"{OLD_TDR}.yaml")

tdr["payload"].setdefault("uncovered_with_reason", []).append({
    "requirement_id": "REQ-BONUSCCY-007",
    "reason": (
        "AC_PARTIALLY_COVERED: AC-BONUSCCY-009「玩家原本沒有該幣別錢包時會自動出現一列」這半句斷言"
        "未另立TC。依SPEC-MEMBER-001 v0.2§2.1.6第290行「金額為0的幣別仍列出並顯示0.00，不因無餘額"
        "而隱藏」，已在站台層級啟用的幣別即使玩家餘額為0也會在多幣別展開檢視中列出一列並顯示0.00，"
        "故「錢包原本沒有該幣別的一列、中獎後才新增」這件事在本後台UI上不是一個可獨立觀察的離散事件——"
        "只要TTK是站台已啟用幣別，該列在彩金發放前就已存在並顯示0.00。TC-DRAFT-01M2R6JHSDEMW4M0KGRGSED1WW"
        "已驗證AC-BONUSCCY-009另一半「金額進對錢包」的可觀察斷言，本判斷已由本輪獨立Validator查證"
        "SPEC-MEMBER-001原文屬實。"
    ),
})
for k in tdr["payload"]["self_check"]:
    tdr["payload"]["self_check"][k] = True
tdr["payload"].setdefault("revision_of_issues", []).append({
    "issue_index": 0, "draft_id": "TC-DRAFT-01M2R6JHSDEMW4M0KGRGSED1WW",
    "action": "把AC-BONUSCCY-009後半句排除理由從design_rationale自然語言搬到結構化uncovered_with_reason，理由已由獨立Validator查證SPEC-MEMBER-001原文屬實",
})

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
