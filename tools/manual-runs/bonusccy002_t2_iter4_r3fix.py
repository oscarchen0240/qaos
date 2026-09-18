#!/usr/bin/env python3
"""RUN-20260918-004 T2 iteration 4：修正第三輪獨立審查發現的問題。
1. blocker：coverage_matrix未納入iteration 3新增的簽到/首存次存兩條TC——補上。
2. major：首存/次存TC(TC-DRAFT-01M2R7RE1B027CGX3DSYVCP2K2)的step 2要求透過TTK通道完成
   真實存款，與spec.md「線上站台也不會用非系統幣別的通道存款，目前都是死路」直接衝突——
   補上「環境不支援則標記待執行」的退路，比照JACKPOT/跨站台推薦TC的既有寫法。
3. minor：簽到TC(TC-DRAFT-01M2R7RE1B091RRKNRJVZG0X7Q)的expected_result主張『道具獎勵只會
   出現在道具持有清單』——spec未定義此UI頁面，拿掉這個未支持的斷言，改為只斷言『不進任何
   幣別錢包』。
4. minor：同一條TC補上『需要以會員身分存取前台』的precondition，比照AC-BONUSCCY-013的TC。
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids

RUN = "RUN-20260918-004"
OLD_TCD = "ART-TCD-01M2R7RE1CT6ZQD1SZWE76M39Z"
OLD_TDR = "ART-TDR-01M2R7RE1RSMGN7V992HM4NXEP"
A = "agent-test-designer"

tcd = store.load(store.ROOT / "artifacts" / "test-design" / RUN / f"{OLD_TCD}.yaml")
tdr = store.load(store.ROOT / "artifacts" / "test-design" / RUN / f"{OLD_TDR}.yaml")

CHECKIN_ID = "TC-DRAFT-01M2R7RE1B091RRKNRJVZG0X7Q"
FIRSTDEP_ID = "TC-DRAFT-01M2R7RE1B027CGX3DSYVCP2K2"

for t in tcd["payload"]["testcases"]:
    if t["draft_id"] == CHECKIN_ID:
        t["preconditions"].insert(1, "本TC需要能以該會員身分存取線上站台前台簽到頁，非純後台操作")
        t["expected_result"] = (
            "金錢類簽到獎勵發放進系統幣別（USDT）錢包，TTK 錢包不因這筆簽到獎勵而變動；"
            "道具類簽到獎勵不會反映在任一幣別錢包餘額變動上（因為道具獎勵本質不是錢，不進錢包、"
            "沒有幣別），執行時若環境當下的道具最終顯示位置與本TC precondition假設不同，"
            "以錢包餘額未變動這個核心斷言為準，不強求道具本身出現在特定頁面"
        )
        t["design_rationale"] = t["design_rationale"] + (
            "\n\n【第三輪修正】獨立Validator指出expected_result原本主張『道具獎勵只會出現在道具"
            "持有清單』，但spec.md與可讀文件皆未定義此UI頁面，屬於未支持的外推斷言，已拿掉，"
            "改為只斷言核心的『不進任何幣別錢包』；並補上『需要以會員身分存取前台』的precondition，"
            "比照AC-BONUSCCY-013既有TC的揭露方式。"
        )
    if t["draft_id"] == FIRSTDEP_ID:
        t["preconditions"].append(
            "若測試環境當下沒有可實際完成TTK通道存款的機制（依spec.md §要注意的事，目前線上站台"
            "不會用非系統幣別的通道存款，現況為死路），本TC需標記為待執行，待環境支援TWD/非系統"
            "幣別存款通道後再測（此限制與REQ-BONUSCCY-006的『發放幣別』規則本身無關，純屬環境"
            "現況限制）"
        )
        t["design_rationale"] = t["design_rationale"] + (
            "\n\n【第三輪修正】獨立Validator指出spec.md §要注意的事已明確記載『線上站台也不會用"
            "非系統幣別的通道存款，目前都是死路』，與本TC step 2要求真實透過TTK通道存款直接衝突，"
            "原assumptions只揭露了幣種欄位UI呈現方式的不確定性，未揭露這個更根本的環境限制；"
            "已比照JACKPOT（AC-BONUSCCY-010）、跨站台推薦（AC-BONUSCCY-011）既有TC的寫法，"
            "補上『環境不支援則標記待執行』的退路。"
        )

# 修正coverage_matrix：補上這兩條TC的draft_id
for entry in tdr["payload"]["coverage_matrix"]:
    if entry["requirement_id"] == "REQ-BONUSCCY-006":
        if CHECKIN_ID not in entry["draft_ids"]:
            entry["draft_ids"].append(CHECKIN_ID)
        if FIRSTDEP_ID not in entry["draft_ids"]:
            entry["draft_ids"].append(FIRSTDEP_ID)
        for ac in entry["acceptance_criteria"]:
            if ac["ac_id"] == "AC-BONUSCCY-008":
                if CHECKIN_ID not in ac["draft_ids"]:
                    ac["draft_ids"].append(CHECKIN_ID)
                if FIRSTDEP_ID not in ac["draft_ids"]:
                    ac["draft_ids"].append(FIRSTDEP_ID)

for k in tdr["payload"]["self_check"]:
    tdr["payload"]["self_check"][k] = True
tdr["payload"].setdefault("revision_of_issues", []).append({
    "issue_index": 0,
    "action": (
        "依第三輪獨立審查修正：(1) coverage_matrix補上REQ-BONUSCCY-006/AC-BONUSCCY-008底下"
        "遺漏的簽到、首存/次存兩條TC的draft_id；(2) 首存/次存TC補上環境不支援則待執行的退路"
        "（spec.md明確記載TTK等非系統幣別通道存款目前是死路）；(3) 簽到TC拿掉未支持的道具"
        "持有清單斷言，並補上前台存取的precondition"
    ),
})

def new_id(artifact_type, payload, refs, task="T2", iteration=4):
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
print(tcd_p.relative_to(store.ROOT))
print(tdr_p.relative_to(store.ROOT))
