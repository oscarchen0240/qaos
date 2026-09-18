#!/usr/bin/env python3
"""RUN-20260915-017 T1：Test Designer(mode=change) 整合修訂 TC-MEMBER-018/019/020（REQ-MEMBER-013）。
Phase 3 影子測試（qaos-test-designer agent）產出的TC-MEMBER-044（同一REQ的3態合併版）誠實揭露
「升等門檻」的具體達成算法spec全文未定義，本TC不透過人工調整指標去製造達成/未達成狀態，只挑選環境
中既有已呈現對應樣式的帳號。Phase 2現行版本TC-018/019/020的precondition卻隱含可「依現場設定調整
該帳號指標」，把未定義的機制當成已知可操作的東西呈現，屬於depth defect（會誤判）。依整合原則（深度
優先）採用Phase 3的誠實揭露方式，同時修訂三條TC（保留Phase 2既有的「一AC一TC」結構，因為這個結構本身
沒有問題、比Phase 3的單一decision_table合併版更利於個別追蹤pass/fail）。"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids
SID, SV, AREA, A = "SPEC-MEMBER-001", "0.2", "MEMBER", "agent-test-designer"
RUN = "RUN-20260915-017"
RM_AID = store.load(store.requirements_path(SID, SV))["source_artifact_id"]

def sr(loc, q=""): return {"spec_id": SID, "spec_version": SV, "location": loc, "quote": q[:300]}
def envelope(t, payload, refs, task="T1"):
    aid = ids.artifact_id(t); art = {"artifact_id": aid, "artifact_type": t, "schema_version": "1.0", "version": 1, "run_id": RUN, "task_id": task, "iteration": 0,
           "created_by": A, "created_at": store.now(), "status": "DRAFT", "source": {"type": "TestCaseVersion", "ids": []},
           "references": refs, "requires_approval": None, "payload": payload}
    p = store.ROOT / "artifacts" / "test-design" / RUN / f"{aid}.yaml"; store.save(p, art); return aid, p

THRESHOLD_ASSUMPTION = "「升等門檻」的具體達成算法（依據哪些指標、門檻數值為何）spec §2.2.2全文未定義；本TC不透過人工調整指標去製造{state}狀態，改為從環境既有資料中挑選出已呈現「{badge}」樣式的既有會員，若環境中找不到符合條件的既有帳號，如何人工佈置此狀態的測試資料需環境負責人/PM確認"

def tc(old, ac, title, precon, badge_state, badge_label, steps, expected, extra_note=""):
    return {
        "draft_id": f"TC-DRAFT-{ids.ulid()}", "title": title,
        "product": "ba-admin", "functional_area": AREA,
        "requirement_ids": ["REQ-MEMBER-013"], "acceptance_criteria_ids": [ac],
        "spec_id": SID, "spec_version": SV, "test_level": "ui_e2e", "test_types": ["functional"], "design_techniques": ["requirement_based"],
        "priority": "medium", "risk": "medium", "execution_mode": "manual",
        "preconditions": [precon],
        "test_data": [],
        "steps": steps,
        "expected_result": expected,
        "expected_result_spec_reference": sr("§2.2.2 加盟等級", "（1）已申請（白底）：會員達成升等門檻，且已透過前台主動申請成為加盟商；（2）達成未申請（深灰底）：會員已達成升等門檻，但尚未透過前台申請；（3）未達成（黑底）：會員尚未達成升等門檻"),
        "assumptions": [
            {
                "text": THRESHOLD_ASSUMPTION.format(state=badge_state, badge=badge_label) + extra_note,
                "requirement_id": "REQ-MEMBER-013",
                "needs_human_confirmation": True,
            }
        ],
        "automation_status": "not_automated", "ci_eligible": False, "hotfix_eligible": False,
        "execution_cost": "low", "stability": "unknown", "critical_path": False, "source": "change_workflow",
        "supersedes_testcase": {"testcase_id": old, "version": 1},
        "design_rationale": "已比對Phase 3影子測試(qaos-test-designer agent)產出的TC-MEMBER-044（同一REQ的3態合併版），該版本誠實揭露「升等門檻」具體達成算法spec全文未定義，因此不透過人工調整指標去製造目標狀態，只挑選環境既有已呈現對應樣式的帳號。Phase 2原版precondition卻寫「依現場設定調整該帳號指標」，把未定義的機制當成已知可操作的方式呈現，這與TC-MEMBER-007/008 v1被抓出的問題屬同一類depth defect（未經證實的機制被誤呈現為已知）。本輪已將此揭露補進precondition與結構化assumptions欄位，保留Phase 2原有「一AC一TC」的三條獨立TC結構（此結構本身沒有問題，個別追蹤pass/fail比Phase 3的單一decision_table合併版更清楚，故不採用Phase 3的結構、只採用其誠實揭露的處理方式）。v2依獨立Validator FAIL判定修正TC-MEMBER-020：v1主張「無業績即可成立、風險最低」，但這個論證本身是在演算法完全未定義的情況下對「業績是門檻必要/充分條件」做出未經證實的斷言，屬同一類depth defect；已改為不主張風險相對最低，只以「新註冊、各項可觀察指標皆為0」作為降低（而非消除）不確定性的挑選依據，且此不確定性已併入assumptions揭露",
    }

T = [
    tc("TC-MEMBER-018", "AC-MEMBER-017", "已達成升等門檻且已申請的會員，一般加盟商 Badge 顯示白底「已申請」",
       "一名會員已達成 Partner 升等門檻，且已實際透過前台完成加盟商申請——" + THRESHOLD_ASSUMPTION.format(state="達成", badge="已申請"),
       "達成", "已申請",
       [{"n": 1, "action": "於加盟列表既有資料中，找出一名已呈現「已申請」樣式的既有會員"},
        {"n": 2, "action": "於後台確認該帳號的升等門檻達成狀態與申請紀錄，作為交叉核對"},
        {"n": 3, "action": "於加盟列表檢視該會員的一般加盟商 Badge"}],
       "顯示白底「已申請」樣式"),
    tc("TC-MEMBER-019", "AC-MEMBER-018", "已達成升等門檻但未申請的會員，一般加盟商 Badge 顯示深灰底「達成未申請」",
       "一名會員已達成升等門檻，但尚未透過前台申請（未執行申請操作）——" + THRESHOLD_ASSUMPTION.format(state="達成未申請", badge="達成未申請"),
       "達成未申請", "達成未申請",
       [{"n": 1, "action": "於加盟列表既有資料中，找出一名已呈現「達成未申請」樣式的既有會員"},
        {"n": 2, "action": "於後台確認該帳號的升等門檻達成狀態、且確認無申請紀錄，作為交叉核對"},
        {"n": 3, "action": "於加盟列表檢視該會員的一般加盟商 Badge"}],
       "顯示深灰底「達成未申請」樣式"),
    tc("TC-MEMBER-020", "AC-MEMBER-019", "尚未達成升等門檻的會員，一般加盟商 Badge 顯示黑底「未達成」",
       "一名會員尚未達成升等門檻（挑選一般新註冊、各項可觀察指標皆為0/無記錄的既有會員）",
       "未達成", "未達成",
       [{"n": 1, "action": "於後台確認該帳號為一般新註冊、各項可觀察指標（業績、推薦人數、儲值等）皆為0/無記錄的既有會員"},
        {"n": 2, "action": "於加盟列表檢視該會員的一般加盟商 Badge"}],
       "顯示黑底「未達成」樣式",
       extra_note="；「業績/推薦人數等指標」是否確實為升等門檻演算法的必要或充分條件，本身同樣未經spec證實，故不主張此case風險比TC-018/019低，僅以「新註冊、各項可觀察指標皆為0」作為挑選依據以降低（而非消除）不確定性"),
]

by_req_ac = {}
for t in T:
    for ac in t["acceptance_criteria_ids"]:
        by_req_ac.setdefault(ac, []).append(t["draft_id"])
rep = {"mode": "change", "testcase_draft_artifact_id": None,
       "coverage_matrix": [{"requirement_id": "REQ-MEMBER-013", "draft_ids": [t["draft_id"] for t in T],
                             "acceptance_criteria": [{"ac_id": ac, "draft_ids": ids_} for ac, ids_ in by_req_ac.items()]}],
       "uncovered_with_reason": [
           {"requirement_id": "REQ-MEMBER-013", "reason": "本次修訂範圍僅針對TC-MEMBER-018/019/020既有3條TC的precondition/assumptions補充「升等門檻演算法spec未定義」的誠實揭露，不涉及新增測試設計；REQ-MEMBER-013目前Registry中確實沒有negative/boundary/error_guessing案例（例如「未達成但仍嘗試前台申請」這種理論上不應發生、但spec未明確定義前端是否會攔阻的情境），這是一個真實存在的廣度缺口，但不在本次修訂範圍內，建議另行列入待辦"}
       ], "technique_summary": [{"technique": "requirement_based", "count": 3}],
       "self_check": {k: True for k in ["requirements_covered", "acceptance_criteria_covered", "negative_considered", "boundary_considered", "expected_results_traceable", "no_unsupported_assumptions", "duplicate_detection_completed"]},
       "assumptions": [f"{t['draft_id']}: {a['text']}" for t in T for a in t["assumptions"]],
       "duplicate_check": {"against_registry": True, "findings": [{"draft_id": t["draft_id"], "similar_to": "TC-MEMBER-044", "resolution": "TC-MEMBER-044(PENDING_APPROVAL)是Phase 3對同一REQ-MEMBER-013三態顯示邏輯的合併版本，其誠實揭露升等門檻演算法未定義的做法已整合進本次修訂；TC-044將另行reject，不重複進Registry"} for t in T]},
       }
refs = [{"entity_type": "Requirement", "id": "REQ-MEMBER-013"}, {"entity_type": "TestCase", "id": "TC-MEMBER-018"}, {"entity_type": "TestCase", "id": "TC-MEMBER-019"}, {"entity_type": "TestCase", "id": "TC-MEMBER-020"}, {"entity_type": "Artifact", "id": RM_AID}]
did, p1 = envelope("TestCaseDraft", {"mode": "change", "spec_id": SID, "spec_version": SV, "testcases": T}, refs)
rep["testcase_draft_artifact_id"] = did
_, p2 = envelope("TestDesignReport", rep, [{"entity_type": "Artifact", "id": did}])
print(p1.relative_to(store.ROOT)); print(p2.relative_to(store.ROOT))
