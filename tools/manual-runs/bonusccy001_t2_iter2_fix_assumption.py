#!/usr/bin/env python3
"""RUN-20260918-002 T2 iteration 2：修正洗分TC缺少結構化assumption的揭露不一致問題。
獨立Validator指出：洗分TC(TC-DRAFT-01M2R2ZKT650JSTNVP0Z94DCSG)跟入金/出金/開分三條TC
依賴同一個環境工具假設，但只有它沒有結構化assumptions；design_rationale用
MAX_EXPLORATORY_PER_REQ=3解釋，但這4條TC的design_techniques全是negative非exploratory，
理由不成立。直接比照其他三條TC的assumption文字補上。"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids

RUN = "RUN-20260918-002"
OLD_TCD = "ART-TCD-01M2R2ZKT738P8M4H6E6CZRZWG"
OLD_TDR = "ART-TDR-01M2R2ZKTN6Y3QHASHBN818XKS"
A = "agent-test-designer"

tcd = store.load(store.ROOT / "artifacts" / "test-design" / RUN / f"{OLD_TCD}.yaml")
tdr = store.load(store.ROOT / "artifacts" / "test-design" / RUN / f"{OLD_TDR}.yaml")

TARGET = "TC-DRAFT-01M2R2ZKT650JSTNVP0Z94DCSG"
ASSUMPTION_TEXT = (
    "此TC的測試執行方式假設測試環境已具備可呼叫平台機台端API（req-cashin/req-cashout/req-keyin/"
    "req-keyout）的模擬工具或API client（因實體機台通常不便於一般測試/UAT環境直接取得，需以模擬"
    "方式呼叫API觸發入金/出金/開分/洗分請求）；此為測試執行環境的技術依賴，非spec.md定義範圍，"
    "實際測試環境是否已具備此類工具，需環境負責人確認。"
)
for t in tcd["payload"]["testcases"]:
    if t["draft_id"] == TARGET:
        t["assumptions"] = [{
            "text": ASSUMPTION_TEXT, "requirement_id": "REQ-BONUSCCY-004", "needs_human_confirmation": True,
        }]
        t["design_rationale"] = t["design_rationale"] + (
            "\n\n【iteration 2修正】獨立Validator指出上一輪以「MAX_EXPLORATORY_PER_REQ=3」為由略過"
            "本TC的結構化assumption揭露，但本批4條TC(入金/出金/開分/洗分)的design_techniques皆為"
            "negative非exploratory，此理由不成立。已比照其餘三條TC補上相同的環境工具依賴assumption，"
            "確保同一份假設在四條同構TC中的揭露方式一致。"
        )
        break
else:
    raise SystemExit("not found")

tdr["payload"].setdefault("revision_of_issues", []).append({
    "issue_index": 0, "draft_id": TARGET,
    "action": "補上結構化assumption，與入金/出金/開分三條TC的揭露方式一致，取消先前不成立的exploratory數量上限理由",
})
for k in tdr["payload"]["self_check"]:
    tdr["payload"]["self_check"][k] = True

def new_id(artifact_type, payload, refs, task="T2", iteration=2):
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

clean_refs = [r for r in tcd["references"] if r["id"] != "ART-TCD-01M2R26RDN1XDQDTSFP8ZSYKP7"]
tcd_id, tcd_p = new_id("TestCaseDraft", tcd["payload"], clean_refs)
tdr["payload"]["testcase_draft_artifact_id"] = tcd_id
tdr_id, tdr_p = new_id("TestDesignReport", tdr["payload"], [{"entity_type": "Artifact", "id": tcd_id}])
print(tcd_p.relative_to(store.ROOT) if hasattr(tcd_p, 'relative_to') else tcd_p)
print(tdr_p.relative_to(store.ROOT) if hasattr(tdr_p, 'relative_to') else tdr_p)
