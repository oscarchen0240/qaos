#!/usr/bin/env python3
"""RUN-20260923-005(008)/006(009)/007(011) T1：Test Designer(mode=change) 依 CLR-CASHFLOW-005
RD 回覆 A（額度上限判定時機由 req-cashin 改為 end-cashin）反轉三條 TC 的斷言方向。
用法：cashflow_clr005_revise_t1.py <RUN> [iter]"""
import sys, pathlib, collections
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids
RUN = sys.argv[1]; ITER = int(sys.argv[2]) if len(sys.argv) > 2 else 0
OLD = {"RUN-20260923-005": "TC-CASHFLOW-008", "RUN-20260923-006": "TC-CASHFLOW-009", "RUN-20260923-007": "TC-CASHFLOW-011"}[RUN]
SID, SV, A = "SPEC-CASHFLOW-001", "0.1", "agent-test-designer"
RM_AID = store.load(store.requirements_path(SID, SV))["source_artifact_id"]
old = store.load(store.tc_version_path(OLD, store.load(store.tc_pointer_path(OLD))["active_version"]))
def sr(loc, q=""): return {"spec_id": SID, "spec_version": SV, "location": loc, **({"quote": q[:300]} if q else {})}
RATIONALE = ("CLR-CASHFLOW-005 RD 回覆 A（2026-09-23）：req-cashin 階段入鈔機尚未完成實體清點，客戶端回報金額不可信，"
             "若此時依此數字判斷額度上限，攻擊者可宣稱鉅額數字造成機台卡在等待中的 DoS；額度上限改於 end-cashin（依入鈔機實際清點金額）判定，"
             "超限則退鈔。RM REQ-CASHFLOW-007／009 已反轉，本 TC 依新規則重寫斷言方向。ADR-008 影響掃描判定需修訂。")
COMMON_PRE = ["機台已透過憑證通過認證", "機台所屬場館為開通狀態，機台為啟用狀態"]
if OLD == "TC-CASHFLOW-008":
    T = dict(title="req-cashin 不判額度（含鉅額防禦）；end-cashin 依實際清點金額判定，恰等於上限成立、超過 1 單位則 1-OVER LIMIT 退鈔",
      pre=COMMON_PRE + ["設定該場館額度上限為 A，並確認目前「全場館機台分數餘額合計（已入帳）」恰為 A-100"],
      steps=["送出 req-cashin，金額為遠超額度上限數個量級的鉅額數值（例如 A 的 1000 倍），確認仍回 0-OK、建立 PENDING 並取得 TXID"
             "——驗證 req-cashin 本階段不依客戶端聲稱金額判定額度，不會因巨額數字被拒或卡住（CLR-CASHFLOW-005 防 DoS 的核心行為）",
             "送出該筆 end-cashin，實際清點金額改為 100（模擬入鈔機清點結果與聲稱金額不同），確認回覆與分數變化",
             "另送出 req-cashin，金額 1，確認同樣建立 PENDING",
             "送出其 end-cashin（實際清點金額 1），使「全場館機台分數餘額合計（已入帳）＋本筆實際清點金額」恰等於額度上限 A",
             "確認回覆 0-OK、分數正常增加",
             "再送出 req-cashin（金額 1，同樣建立 PENDING），送出其 end-cashin（實際清點金額 1），使加計後超過額度上限 A",
             "確認此筆 end-cashin 的回覆與分數變化；若為純 API 直連環境（無實體機台），以回覆碼 1-OVER LIMIT 且帳務未異動為判定依據；有實體機台時另確認機台退鈔"],
      expected="第一筆：req-cashin 送鉅額數字仍成功建立 PENDING（不判額度、不卡住），end-cashin 以實際清點金額 100 入帳、回 0-OK；第二筆：req-cashin 建立 PENDING，end-cashin 實際金額 1 使加計恰等於上限，回 0-OK 並正常入帳；第三筆：req-cashin 建立 PENDING，end-cashin 實際金額 1 使加計超過上限，回 1-OVER LIMIT，不更新帳務（純 API 環境以此為準，實體機台另確認退鈔）",
      acs=["AC-CASHFLOW-0071","AC-CASHFLOW-0072"], reqs=["REQ-CASHFLOW-007"])
elif OLD == "TC-CASHFLOW-009":
    T = dict(title="兩筆入金的 end-cashin 幾乎同時到達且各自單看不超限但合計會超限時，場館鎖序列化正確擋下第二筆",
      pre=COMMON_PRE,
      steps=["建構場館餘額合計已接近額度上限的情境（例如尚餘額度剛好等於單筆入金金額）",
             "兩台不同機台各自完成 req-cashin，取得各自 TXID（本階段皆會成功建立 PENDING，不判定額度）",
             "以測試工具對同一場館的兩台機台併發送出兩個 end-cashin HTTP 請求（同一時間發出，不依序等待回應），實際清點金額皆等於尚餘額度，各自單看皆不超限，但兩筆合計會超限",
             "檢視兩筆 end-cashin 的回應與帳務是否更新"],
      expected="依場館鎖逐筆序列化處理：先取得鎖的一筆 end-cashin 通過並完成入帳，另一筆的判定基準已包含前者剛入帳的金額，因而正確被擋下回 1-OVER LIMIT、不更新帳務（純 API 環境以回覆碼與帳務未異動為判定依據，實體機台另確認退鈔）；不會兩筆皆通過而使全場館餘額超過額度上限。與 TC-CASHFLOW-011（單純狀態前置下的超限拒絕）的差異：本案驗證的是場館鎖序列化下的併發正確性，非單一狀態判定",
      acs=["AC-CASHFLOW-0073"], reqs=["REQ-CASHFLOW-007"])
else:
    T = dict(title="即使 req-cashin 已成功建立 PENDING，end-cashin 時全場館餘額已達額度上限，仍會被擋下並退鈔",
      pre=COMMON_PRE,
      steps=["req-cashin 已送出並成功建立 PENDING、取得 TXID（本階段未判定額度、未預留）",
             "在收到 end-cashin 前，令全場館餘額合計因其他交易已達到額度上限",
             "機台送出 end-cashin，TXID 相符，帶入實際清點金額"],
      expected="平台於 end-cashin 判定額度上限：因加計後將超過上限，回 1-OVER LIMIT，不更新帳務、不關閉 PENDING 為已完成（純 API 環境以回覆碼與帳務未異動為判定依據，實體機台另確認退鈔）——與 req-cashin 階段是否已建立 PENDING 無關，該 PENDING 本身不代表額度已通過。與 TC-CASHFLOW-009（併發序列化下的超限拒絕）的差異：本案驗證的是單一交易在單純狀態前置下的超限拒絕，非併發序列化",
      acs=["AC-CASHFLOW-0091"], reqs=["REQ-CASHFLOW-009"])
tc = {k: old[k] for k in ("product", "functional_area", "spec_id", "spec_version", "test_level", "test_types", "design_techniques",
                          "priority", "risk", "execution_mode", "test_data", "automation_status", "ci_eligible", "hotfix_eligible",
                          "execution_cost", "stability", "critical_path")}
tc.update({"draft_id": f"TC-DRAFT-{ids.ulid()}", "title": T["title"], "requirement_ids": T["reqs"], "acceptance_criteria_ids": T["acs"],
           "preconditions": T["pre"], "steps": [{"n": i + 1, "action": s} for i, s in enumerate(T["steps"])], "expected_result": T["expected"],
           "expected_result_spec_reference": sr("SPEC-CASHFLOW-001 v0.1（依 RM REQ-CASHFLOW-007／009，2026-09-23 依 CLR-CASHFLOW-005 回寫；spec.md 正本 v07 文字已作廢，待更新）"),
           "assumptions": old.get("assumptions", []), "source": "change_workflow",
           "supersedes_testcase": {"testcase_id": OLD, "version": old["version"]}, "design_rationale": RATIONALE})
cnt = collections.Counter(tc["design_techniques"])
rm = store.load(store.requirements_path(SID, SV)); owner = {a["ac_id"]: r["requirement_id"] for r in rm["requirements"] for a in r["acceptance_criteria"]}
cov = {}
for rid in tc["requirement_ids"]: cov[rid] = {"requirement_id": rid, "draft_ids": [tc["draft_id"]], "acceptance_criteria": []}
for aid in tc["acceptance_criteria_ids"]: cov[owner[aid]]["acceptance_criteria"].append({"ac_id": aid, "draft_ids": [tc["draft_id"]]})
rep = {"mode": "change", "testcase_draft_artifact_id": None, "coverage_matrix": list(cov.values()), "uncovered_with_reason": [],
       "technique_summary": [{"technique": k, "count": v} for k, v in cnt.items()],
       "self_check": {k: True for k in ["requirements_covered", "acceptance_criteria_covered", "negative_considered", "boundary_considered",
                                        "expected_results_traceable", "no_unsupported_assumptions", "duplicate_detection_completed"]},
       "assumptions": [], "duplicate_check": {"against_registry": True, "findings": []}}
def envelope(t, payload, refs):
    aid = ids.artifact_id(t); art = {"artifact_id": aid, "artifact_type": t, "schema_version": "1.0", "version": 1, "run_id": RUN, "task_id": "T1",
        "iteration": ITER, "created_by": A, "created_at": store.now(), "status": "DRAFT",
        "source": {"type": "TestCaseVersion", "ids": [f"{OLD}@v{old['version']}"]}, "references": refs, "requires_approval": None, "payload": payload}
    p = store.ROOT / "artifacts" / "test-design" / RUN / f"{aid}.yaml"; store.save(p, art); return aid, p
refs = [{"entity_type": "Requirement", "id": r} for r in tc["requirement_ids"]] + [{"entity_type": "TestCase", "id": OLD}, {"entity_type": "Artifact", "id": RM_AID}]
did, p1 = envelope("TestCaseDraft", {"mode": "change", "spec_id": SID, "spec_version": SV, "testcases": [tc]}, refs)
rep["testcase_draft_artifact_id"] = did
_, p2 = envelope("TestDesignReport", rep, [{"entity_type": "Artifact", "id": did}])
print(p1.relative_to(store.ROOT)); print(p2.relative_to(store.ROOT))
