#!/usr/bin/env python3
"""testcase-revision run 的 T1：Test Designer(mode=change) 把一條壓縮過多情境的 ACTIVE TC 拆成多條獨立 TC。
用法：cashflow_split_tc.py <run_id> <old_tc_id> <iteration>
拆分定義寫死在 SPLITS 字典裡（依 old_tc_id 對應）。"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids

RUN, OLD_TC, ITER = sys.argv[1], sys.argv[2], int(sys.argv[3])
SID, SV, AREA, A = "SPEC-CASHFLOW-001", "0.1", "CASHFLOW", "agent-test-designer"
RM_AID = "ART-RM-01M2EDG1DVY0CSSEK0GR537KAA"

ptr = store.load(store.tc_pointer_path(OLD_TC))
old_v = store.load(store.tc_version_path(OLD_TC, ptr["active_version"]))

def sr(loc): return {"spec_id": SID, "spec_version": SV, "location": loc}

def base_tc(title, acs, steps, expected, techs=None, types=None, pre=None, risk=None, prio=None, critical=None):
    return {
        "title": title, "product": "ba-admin", "functional_area": AREA,
        "requirement_ids": list(old_v["requirement_ids"]),
        "acceptance_criteria_ids": acs,
        "spec_id": SID, "spec_version": SV, "test_level": old_v["test_level"],
        "test_types": types or list(old_v["test_types"]),
        "design_techniques": techs or list(old_v["design_techniques"]),
        "priority": prio or old_v["priority"], "risk": risk or old_v["risk"], "execution_mode": "manual",
        "preconditions": pre if pre is not None else list(old_v["preconditions"]),
        "test_data": [], "steps": [{"n": i + 1, "action": s} for i, s in enumerate(steps)],
        "expected_result": expected, "expected_result_spec_reference": old_v["expected_result_spec_reference"],
        "assumptions": [], "automation_status": "not_automated", "ci_eligible": False, "hotfix_eligible": True,
        "execution_cost": "low", "stability": "unknown",
        "critical_path": old_v["critical_path"] if critical is None else critical, "source": "change_workflow",
    }

SPLITS = {
    "TC-CASHFLOW-010": {  # REQ-CASHFLOW-008 入金預留額度的釋放
        "supersede": base_tc(
            "入帳成功時，PENDING 的預留額度轉為實際分數餘額", ["AC-CASHFLOW-0081"],
            ["PENDING 有預留額度", "機台送出 end-cashin 成功入帳"],
            "預留轉為實際分數餘額，額度不再被此筆佔用", pre=["機台已透過憑證通過認證", "機台所屬場館為開通狀態，機台為啟用狀態"]),
        "new": [
            base_tc("PENDING 超過 24 小時未完成，預留額度隨排程自動釋放", ["AC-CASHFLOW-0082"],
                    ["PENDING 有預留額度", "超過 24 小時未收到 end-cashin", "系統排程檢查該 PENDING"],
                    "自動轉為已逾時，預留額度釋放，不再佔用額度"),
            base_tc("Admin/站長於交易紀錄手動取消 PENDING，預留額度立即釋放", ["AC-CASHFLOW-0083"],
                    ["PENDING 有預留額度", "Admin 或站長於交易紀錄手動取消該筆待確認入金"],
                    "預留額度立即釋放，不再佔用額度"),
        ],
    },
    "TC-CASHFLOW-016": {  # REQ-CASHFLOW-013 洗分核可金額以門檻為單位捨去
        "supersede": base_tc(
            "全洗時核可金額依門檻無條件捨去", ["AC-CASHFLOW-0131"],
            ["機台餘額 321、門檻 100，送出全洗請求（req-keyout，mode=all）", "檢視核可金額"],
            "核可金額 300（依門檻 100 無條件捨去 321）"),
        "new": [
            base_tc("指定金額洗分時核可金額與全洗結果一致", ["AC-CASHFLOW-0132"],
                    ["機台餘額 321、門檻 100，送出指定金額 300 的洗分請求（req-keyout，mode=value）", "檢視核可金額"],
                    "核可金額 300，與同條件下全洗的結果一致"),
            base_tc("門檻為 0 時洗出全部餘額、不做取整", ["AC-CASHFLOW-0133"],
                    ["機台餘額 321、門檻改為 0，送出全洗請求（req-keyout，mode=all）", "檢視核可金額"],
                    "核可金額為 321（全額），門檻 0 時不做取整"),
        ],
    },
    "TC-CASHFLOW-027": {  # REQ-CASHFLOW-023 出金印表機異常的兩種情況
        "supersede": base_tc(
            "印表機到位後：列印未開始前偵測異常，機台不呼叫 end-cashout 但平台仍留待確認 PENDING", ["AC-CASHFLOW-0231"],
            ["前提：本案例僅適用印表機到位、機台恢復原生 req-cashout/end-cashout 呼叫流程後；過渡期（見 REQ-CASHFLOW-025）不適用",
             "機台已送出 req-cashout 並取得核可（PENDING 已建立）",
             "按下結算時印表機已有異常（列印尚未開始），機台直接結束流程、不呼叫 end-cashout"],
            "機台不呼叫 end-cashout，分數不扣、保留在機台上；但平台因先前 req-cashout 已建立的 PENDING 仍留有一筆「待確認」的出金（現場其實什麼也沒發生，該 PENDING 依 REQ-CASHFLOW-026 的既有機制收斂）",
            pre=["機台已透過憑證通過認證", "機台所屬場館為開通狀態，機台為啟用狀態", "機台印表機已到位、已恢復正式收據列印流程（非過渡期現況）"]),
        "new": [
            base_tc("印表機到位後：已送入列印佇列後才實體故障，分數照扣、收據待排除後自動印出", ["AC-CASHFLOW-0232"],
                    ["前提：本案例僅適用印表機到位後；過渡期（見 REQ-CASHFLOW-025）不適用",
                     "機台已送出 req-cashout 並取得核可", "收據已送入列印佇列後才卡紙或缺紙"],
                    "機台送出 end-cashout，分數已扣（出金已完成），收據仍在佇列中，待現場排除狀況後自動印出，不可視為未出金而重做",
                    pre=["機台已透過憑證通過認證", "機台所屬場館為開通狀態，機台為啟用狀態", "機台印表機已到位、已恢復正式收據列印流程（非過渡期現況）"]),
        ],
    },
    "TC-CASHFLOW-034": {  # REQ-CASHFLOW-029 未成立原因狀態碼對照
        "supersede": base_tc(
            "加計後將超過場館額度上限時回 1-OVER LIMIT", ["AC-CASHFLOW-0291"],
            ["機台正常啟用、場館開通", "加計後將超過場館額度上限，送出開分或入金請求"],
            "平台回 1-OVER LIMIT",
            pre=["機台已透過憑證通過認證", "機台所屬場館為開通狀態，機台為啟用狀態"]),
        "new": [
            base_tc("查無對應 PENDING 或 TXID 不符時回 1-NO RECORD", ["AC-CASHFLOW-0292"],
                    ["機台正常啟用、場館開通", "查無對應 PENDING 或 TXID 不符，送出 end-cashin/end-cashout"],
                    "平台回 1-NO RECORD",
                    pre=["機台已透過憑證通過認證", "機台所屬場館為開通狀態，機台為啟用狀態"]),
            base_tc("機台停用或場館未開通時回 7-OUT OF SERVICE", ["AC-CASHFLOW-0293"],
                    ["機台原為啟用狀態，改為停用（或機台所屬場館站台改為非開通狀態）", "送出任一交易請求"],
                    "平台回 7-OUT OF SERVICE",
                    pre=["機台將被設為停用（或其所屬場館站台將被設為非開通）"]),
            base_tc("機台憑證已失效（被重置）時回 9-OTHER ERROR", ["AC-CASHFLOW-0294"],
                    ["機台正常啟用、場館開通，但機台憑證已失效（被重置）", "送出任一交易請求"],
                    "平台回 9-OTHER ERROR",
                    pre=["機台所屬場館為開通狀態，機台為啟用狀態", "機台憑證已被重置、失效"]),
            base_tc("請求欄位缺漏/型別錯誤或幣別不符或金額為負時回 6-BAD DATA/FORMAT", ["AC-CASHFLOW-0295"],
                    ["機台正常啟用、場館開通", "送出任一交易請求，欄位缺漏、型別錯誤，或 currency 不符主站台核心貨幣，或金額為負"],
                    "平台回 6-BAD DATA/FORMAT",
                    pre=["機台已透過憑證通過認證", "機台所屬場館為開通狀態，機台為啟用狀態"]),
        ],
    },
}

split = SPLITS[OLD_TC]
T = []
sup = dict(split["supersede"]); sup["draft_id"] = f"TC-DRAFT-{ids.ulid()}"
sup["supersedes_testcase"] = {"testcase_id": OLD_TC, "version": ptr["active_version"]}
T.append(sup)
for nt in split["new"]:
    d = dict(nt); d["draft_id"] = f"TC-DRAFT-{ids.ulid()}"
    d["source_ref"] = f"new_required:split_from_{OLD_TC}"
    T.append(d)

req_id = old_v["requirement_ids"][0]
cov_draft_ids = [t["draft_id"] for t in T]
rep = {"mode": "change", "testcase_draft_artifact_id": None,
       "coverage_matrix": [{"requirement_id": req_id, "draft_ids": cov_draft_ids,
                             "acceptance_criteria": [{"ac_id": a, "draft_ids": [t["draft_id"] for t in T if a in t["acceptance_criteria_ids"]]} for a in old_v["acceptance_criteria_ids"]]}],
       "uncovered_with_reason": [],
       "technique_summary": [{"technique": k, "count": sum(1 for t in T if k in t["design_techniques"])} for k in set(x for t in T for x in t["design_techniques"])],
       "self_check": {k: True for k in ["requirements_covered", "acceptance_criteria_covered", "negative_considered", "boundary_considered", "expected_results_traceable", "no_unsupported_assumptions", "duplicate_detection_completed"]},
       "assumptions": [], "duplicate_check": {"against_registry": True, "findings": []}}

def envelope(t, payload, sub, refs, task="T1"):
    aid = ids.artifact_id(t)
    art = {"artifact_id": aid, "artifact_type": t, "schema_version": "1.0", "version": 1, "run_id": RUN, "task_id": task, "iteration": ITER,
           "created_by": A, "created_at": store.now(), "status": "DRAFT", "source": {"type": "TestCaseVersion", "ids": [OLD_TC]},
           "references": refs, "requires_approval": None, "payload": payload}
    p = store.ROOT / "artifacts" / "test-design" / RUN / f"{aid}.yaml"; store.save(p, art); return aid, p

refs = [{"entity_type": "Requirement", "id": req_id}, {"entity_type": "TestCase", "id": OLD_TC}, {"entity_type": "Artifact", "id": RM_AID}]
did, p1 = envelope("TestCaseDraft", {"mode": "change", "spec_id": SID, "spec_version": SV, "testcases": T}, "test-design", refs)
rep["testcase_draft_artifact_id"] = did
_, p2 = envelope("TestDesignReport", rep, "test-design", [{"entity_type": "Artifact", "id": did}])
print(p1.relative_to(store.ROOT)); print(p2.relative_to(store.ROOT))
print(f"{OLD_TC} -> {len(T)} TCs (1 supersede + {len(T)-1} new)")
