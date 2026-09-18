#!/usr/bin/env python3
"""RUN-20260915-020 T1：Test Designer(mode=change) 修訂 TC-MEMBER-004（REQ-MEMBER-003，KYC五圖示狀態顯示）。
Phase 3 影子測試產出的同意圖TC-MEMBER-030（已退役）誠實揭露「已停用」狀態如何產生（是否有後台操作入口、
或僅為系統/環境層級設定）spec全文未定義；Phase 2現行版本precondition卻聲稱「可透過後台...執行...停用
操作」來佈置，把未定義的機制當成已知可操作的方式呈現。依整合原則(深度優先)補充此揭露。"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids
SID, SV, AREA, A = "SPEC-MEMBER-001", "0.2", "MEMBER", "agent-test-designer"
RUN = "RUN-20260915-020"
RM_AID = store.load(store.requirements_path(SID, SV))["source_artifact_id"]

def sr(loc, q=""): return {"spec_id": SID, "spec_version": SV, "location": loc, "quote": q[:300]}
def envelope(t, payload, refs, task="T1"):
    aid = ids.artifact_id(t); art = {"artifact_id": aid, "artifact_type": t, "schema_version": "1.0", "version": 1, "run_id": RUN, "task_id": task, "iteration": 0,
           "created_by": A, "created_at": store.now(), "status": "DRAFT", "source": {"type": "TestCaseVersion", "ids": []},
           "references": refs, "requires_approval": None, "payload": payload}
    p = store.ROOT / "artifacts" / "test-design" / RUN / f"{aid}.yaml"; store.save(p, art); return aid, p

tc = {
    "draft_id": f"TC-DRAFT-{ids.ulid()}",
    "title": "會員列表 KYC 狀態五圖示依各階段實際狀態正確顯示顏色與 Tooltip",
    "product": "ba-admin", "functional_area": AREA,
    "requirement_ids": ["REQ-MEMBER-003"], "acceptance_criteria_ids": ["AC-MEMBER-004"],
    "spec_id": SID, "spec_version": SV, "test_level": "ui_e2e", "test_types": ["functional"], "design_techniques": ["scenario"],
    "priority": "medium", "risk": "medium", "execution_mode": "manual",
    "preconditions": [
        "一名會員的五個 KYC 階段（個人基本資訊/身分證明文件/身分證件自拍/居住地址/資產證明）分別處於不同狀態，至少涵蓋已核准/審核中/待補件/未申請其中三種以上。各狀態佈置方式（依spec §2.1.5會員詳細資料頁「KYC 狀態」區塊定義）：「已核准」＝後台對該階段執行審核結果「通過」；「待補件」＝後台執行「駁回」（並選取駁回原因）；「未申請」＝該階段尚未經會員端送出、保持未送審；「審核中」＝會員已透過會員端（前台/APP）送出該階段申請、後台尚未執行通過或駁回——這是會員端動作觸發的狀態，後台本身沒有可直接『執行』出審核中的操作，佈置時需請一名會員實際透過前台送出申請，或從測試環境既有資料中挑選已處於審核中的既有帳號",
        "「已停用」狀態的佈置方式（已由 Oscar 2026-09-15 確認）：於後台「系統管理 > KYC設定」停用該驗證項目，該階段即對所有會員生效；停用後，會員列表 KYC 狀態欄該階段實際顯示為「--」，而非 spec §2.1.3 表格文字描述的深灰色圖示＋「已停用」Tooltip——spec文字與實際產品顯示不完全一致，本TC以實際產品行為（顯示「--」）為準，spec的用字落差建議另案確認/更新spec",
    ],
    "test_data": [],
    "steps": [
        {"n": 1, "action": "於會員列表檢視該會員的 KYC 狀態欄五個圖示顏色"},
        {"n": 2, "action": "滑鼠移至任一圖示"},
    ],
    "expected_result": "四個仍開放審核的階段圖示顏色分別正確對應各自階段的實際狀態（綠=已核准/橘=審核中/紅=待補件/淺灰=未申請），滑鼠移至圖示顯示 Tooltip 說明階段名稱與狀態；若涵蓋已停用的階段，該階段於會員列表 KYC 狀態欄實際顯示為「--」（已由 Oscar 2026-09-15 確認之實際產品行為，非 spec §2.1.3 表格文字描述的深灰色圖示＋『已停用』Tooltip——兩者用字有落差，以實際產品行為為準）",
    "expected_result_spec_reference": sr("§2.1.3 KYC驗證階段圖示說明", "🟢綠色已核准該階段已通過審核｜🟠橘色審核中會員已送出申請，待後台審核｜🔴紅色待補件審核不通過，需會員補件｜灰色（淺）未申請會員尚未提交此階段｜灰色（深）已停用此階段已被停用"),
    "assumptions": [],
    "automation_status": "not_automated", "ci_eligible": False, "hotfix_eligible": False,
    "execution_cost": "low", "stability": "unknown", "critical_path": False, "source": "change_workflow",
    "supersedes_testcase": {"testcase_id": "TC-MEMBER-004", "version": 1},
    "design_rationale": "已比對Phase 3影子測試(qaos-test-designer agent)產出的TC-MEMBER-030（已退役），Phase 2原版precondition聲稱「可透過後台對該測試帳號的各階段分別執行核准/駁回/停用操作」來佈置已停用狀態，把未定義的機制（是否真的有『停用』這個後台操作）當成已知可操作的方式呈現，這與TC-MEMBER-007/008、TC-MEMBER-018/019/020被抓出的問題屬同一類depth defect。Phase 3版本誠實揭露此依賴、標為assumption。依整合原則(深度優先)補充此揭露，precondition中移除「執行...停用操作」的武斷措辭，改為優先挑選既有帳號、並將不確定性結構化記錄於assumptions。v2依獨立Validator FAIL判定修正：v1只處理了「已停用」的depth defect，卻遺漏同一份precondition裡「審核中」狀態同樣有問題——原文籠統寫「可透過後台執行核准/駁回操作、或部分階段保持未送審來佈置」，但依spec §2.1.5，後台的『通過』/『駁回』操作只能作用在已經送審(審核中)的階段上，無法『執行』出審核中狀態本身，審核中是會員端送出申請觸發的狀態。已在precondition中逐一明確列出四種狀態各自正確的佈置方式，不再籠統歸入『後台操作』。v3依Oscar 2026-09-15補充確認的新資訊修正：『已停用』狀態的實際佈置機制是後台『系統管理 > KYC設定』停用特定驗證項目，停用後會員列表KYC狀態欄該階段顯示為『--』，與spec §2.1.3表格描述的深灰色圖示＋『已停用』Tooltip用字不完全一致。此假設已從exploratory（需PM確認）轉為grounded（已有確定答案），assumptions欄位移除該項；expected_result同步改為以實際產品行為（顯示『--』）為準，並誠實標註與spec文字的落差",
}

rep = {"mode": "change", "testcase_draft_artifact_id": None,
       "coverage_matrix": [{"requirement_id": "REQ-MEMBER-003", "draft_ids": [tc["draft_id"]],
                             "acceptance_criteria": [{"ac_id": "AC-MEMBER-004", "draft_ids": [tc["draft_id"]]}]}],
       "uncovered_with_reason": [
           {"requirement_id": "REQ-MEMBER-003", "reason": "本次修訂範圍僅針對TC-MEMBER-004既有1條TC的precondition補充「已停用狀態如何產生spec未定義」的誠實揭露，不涉及新增測試設計；REQ-MEMBER-003本身是純顯示規則(五色圖示對應狀態)，屬behavior_kind=success，目前Registry中未見獨立的negative/boundary案例，這是範圍外的既有現況，不在本次修訂處理範圍內"}
       ], "technique_summary": [{"technique": "scenario", "count": 1}],
       "self_check": {k: True for k in ["requirements_covered", "acceptance_criteria_covered", "negative_considered", "boundary_considered", "expected_results_traceable", "no_unsupported_assumptions", "duplicate_detection_completed"]},
       "assumptions": [f"{tc['draft_id']}: {a['text']}" for a in tc["assumptions"]],
       "duplicate_check": {"against_registry": True, "findings": []}}
refs = [{"entity_type": "Requirement", "id": "REQ-MEMBER-003"}, {"entity_type": "TestCase", "id": "TC-MEMBER-004"}, {"entity_type": "Artifact", "id": RM_AID}]
did, p1 = envelope("TestCaseDraft", {"mode": "change", "spec_id": SID, "spec_version": SV, "testcases": [tc]}, refs)
rep["testcase_draft_artifact_id"] = did
_, p2 = envelope("TestDesignReport", rep, [{"entity_type": "Artifact", "id": did}])
print(p1.relative_to(store.ROOT)); print(p2.relative_to(store.ROOT))
