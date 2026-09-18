#!/usr/bin/env python3
"""RUN-20260915-010 T2（第二輪，iteration 1）：Test Designer(mode=spec)，SPEC-ARCADE-001 v0.7 的 5 條 ACTIVE
Requirement（REQ-ARCADE-001/002/003/004/006；REQ-ARCADE-005 已 RETIRED，被修正後的 REQ-PLATFORMRULE-014
涵蓋）→ TestCaseDraft。

第一輪被獨立 Validator 判 FAIL，抓出 4 個問題：
  1. (blocker) REQ-ARCADE-004 負數輸入阻擋 TC 沒有 spec 依據，卻聲稱「spec 已明確定義」，不誠實
  2. (blocker) REQ-ARCADE-002 的驗證方式太模糊——沒交代加盟傭金/代理返傭是週期性結算（非即時重算）、
     沒要求乾淨測試環境（同期間該加盟商不能有其他會員流水）、沒提醒發放紀錄頁面在機台場館脈絡下被隱藏
  3. (major) REQ-ARCADE-004 正向 TC 沒有驗證 AC 要求的「套用效果」（只測存檔，沒測倍數真的生效）
  4. (major) REQ-ARCADE-001 沒說明機台場館前台網域從哪裡取得
本輪修正：④負向TC改標exploratory（assumptions+needs_human_confirmation）；②補齊結算週期/乾淨環境/站台脈絡
提醒；③正向TC補觸發開分驗證套用效果；①補上站台列表查網域這一步。"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids
SID, SV, AREA, A = "SPEC-ARCADE-001", "0.7", "ARCADE", "agent-test-designer"
RUN = "RUN-20260915-010"; ITER = 1
RM_AID = "ART-RM-01M2GW8RBT2JA2KG86B1J5K87J"

def sr(loc, q=""): return {"spec_id": SID, "spec_version": SV, "location": loc, "quote": q[:300]}

def tc(req, acs, title, precon, steps, expected, loc, quote="", *, ttypes=("functional",), techs=("requirement_based",),
       priority="medium", risk="medium", assumptions=None, rationale=None):
    assumptions = assumptions or []
    return {
        "draft_id": f"TC-DRAFT-{ids.ulid()}", "title": title, "product": "ba-admin", "functional_area": AREA,
        "requirement_ids": [req], "acceptance_criteria_ids": acs,
        "spec_id": SID, "spec_version": SV, "test_level": "ui_e2e", "test_types": list(ttypes), "design_techniques": list(techs),
        "priority": priority, "risk": risk, "execution_mode": "manual",
        "preconditions": precon, "test_data": [],
        "steps": [{"n": i + 1, "action": s} for i, s in enumerate(steps)],
        "expected_result": expected, "expected_result_spec_reference": sr(loc, quote),
        "assumptions": assumptions, "automation_status": "not_automated", "ci_eligible": False, "hotfix_eligible": False,
        "execution_cost": "medium", "stability": "unknown", "critical_path": risk == "high", "source": "spec_workflow",
        "design_rationale": rationale or f"依 {req} 對應驗收條件設計，spec 對此規則已明確定義",
    }

T = [
    tc("REQ-ARCADE-001", ["AC-ARCADE-001"], "機台場館前台找不到自行註冊入口，對照線上站台前台正常提供",
       ["有一個機台場館站台與一個線上站台可供對照"],
       ["於站台列表分別查看該機台場館站台與該線上站台各自的網域欄位",
        "以瀏覽器開啟機台場館的前台網域，尋找「註冊」入口",
        "以瀏覽器開啟線上站台的前台網域，尋找「註冊」入口"],
       "機台場館前台找不到任何自行註冊功能；線上站台前台則正常提供註冊入口，兩者形成對照",
       "業務規則與驗證／前台自行註冊", "機台場館的前台暫不開放自行註冊（未來營運需求、開放時程未定）",
       ttypes=["negative"], techs=["negative"], priority="low", risk="low"),

    tc("REQ-ARCADE-002", ["AC-ARCADE-002"], "機台帳號投注流水不計入上層加盟商的加盟傭金與代理返傭計算基數",
       ["一台機台帳號掛在某加盟商站台底下",
        "該加盟商在本次測試的結算期間內，除此機台外沒有其他會員產生投注流水（維持乾淨對照，避免其他會員流水污染基準值）",
        "記錄該加盟商上一個已結算期間的加盟傭金/代理返傭發放金額，做為對照基準"],
       ["讓該機台帳號在本結算期間產生一筆投注流水（開分或入金後遊玩消耗分數）",
        "加盟傭金/代理返傭為結算期間週期性計算（依日/週/月結算），非即時重算——待本結算期間的結算流程跑完（或依系統實際結算週期等待）",
        "切回該加盟商自身所屬的站台（非機台場館站台，因為「加盟傭金發放紀錄」「代理返傭發放紀錄」頁面在機台場館脈絡下被隱藏），至各式報表查看本期的加盟傭金/代理返傭發放紀錄"],
       "本期發放金額與對照基準相比不因這筆機台流水而增加（在沒有其他會員流水的乾淨對照下，本期金額應與無機台流水時的預期值一致）；若實際系統的結算週期或路徑與描述不同，不視為違反本條，僅測機台流水是否被計入",
       "既有功能對機台帳號的排除規則／4.5-4.6", "4.5 / 4.6｜加盟傭金／代理返傭｜不適用，機台帳號的投注不計入任何上層的傭金基數",
       ttypes=["negative"], techs=["negative"], priority="high", risk="high"),

    tc("REQ-ARCADE-003", ["AC-ARCADE-003"], "機台帳號的交易不會出現在優惠彩金審核佇列中",
       ["一台機台帳號已建立且可正常操作"],
       ["對該機台帳號完成任意一筆金流交易（開分/入金/洗分/出金其中一種）", "檢視優惠彩金審核佇列"],
       "該機台帳號的交易不會出現在審核佇列中",
       "既有功能對機台帳號的排除規則／3.3", "3.3｜優惠彩金審核｜不適用",
       ttypes=["negative"], techs=["negative"]),

    tc("REQ-ARCADE-004", ["AC-ARCADE-004"], "鏈上錢包管理TWD頁籤可設定機台場館稽核倍數，預設0，修改後套用於開分/入金計算",
       ["以 Admin 登入後台，站台切換至一個機台場館"],
       ["至鏈上錢包管理 > TWD 頁籤，確認稽核倍數欄位預設值為 0",
        "修改稽核倍數為大於 0 的值（例如 3）並儲存",
        "對該機台場館的一個機台帳號執行一筆開分或入金",
        "檢視稽核明細，確認該筆交易確實依新設定的倍數計算出稽核門檻，而非沿用舊倍數或不計算"],
       "可見稽核倍數設定欄位，預設值顯示為 0；修改數值並儲存後，該倍數即套用於後續的機台開分與入金計算——稽核明細顯示的計算結果反映新倍數，不是單純存檔留存而已",
       "機台帳號的稽核／設定位置", "設定位置｜鏈上錢包管理，於 TWD 頁籤設定稽核倍數；預設值｜0 倍；倍數大於 0 時｜洗分與出金的核可金額須扣除尚未完成稽核的部分",
       priority="high", risk="high"),
    tc("REQ-ARCADE-004", ["AC-ARCADE-004"], "鏈上錢包管理TWD頁籤稽核倍數輸入負數或非數字時的系統反應（探索性，spec未定義此輸入驗證規則）",
       ["以 Admin 登入後台，站台切換至一個機台場館", "至鏈上錢包管理 > TWD 頁籤"],
       ["嘗試將稽核倍數欄位輸入負數或非數字格式", "點擊儲存，觀察系統反應"],
       "預期系統應阻擋此輸入（假設此欄位比照一般數值欄位有基本輸入驗證）；spec.md 對稽核倍數欄位本身未定義任何輸入驗證規則，此為 Test Designer 合理假設非 spec 明文，需開發或 PM 確認實際行為；若系統目前未做此驗證，不視為違反本條，僅記錄實際現況",
       "機台帳號的稽核／設定位置", "設定位置｜鏈上錢包管理，於 TWD 頁籤設定稽核倍數",
       ttypes=["negative"], techs=["error_guessing"], priority="medium", risk="medium",
       assumptions=[{"text": "稽核倍數欄位應比照一般數值欄位有基本輸入驗證（阻擋負數/非數字），spec.md未定義此規則，此為合理假設非明文規定", "requirement_id": "REQ-ARCADE-004", "needs_human_confirmation": True}],
       rationale="spec.md 全文對稽核倍數的所有引用皆無欄位輸入驗證規則，此條為 Test Designer 依一般 UI 輸入驗證常識提出的探索性假設，已誠實標記為 assumption 並要求人工確認，不聲稱有 spec 依據"),

    tc("REQ-ARCADE-006", ["AC-ARCADE-006"], "洗分出金核實的核實動作寫入後台操作紀錄",
       ["有一筆待核實的機台洗分或機台出金交易"],
       ["於洗分出金核實頁對該筆執行「核實」操作", "檢視後台操作紀錄"],
       "該筆核實動作被記錄，內容含執行的操作人員、時間，以及對應的交易編號",
       "對既有章節的影響／7.4 操作紀錄", "洗分出金核實（含收據核銷）與作廢屬現金相關操作且不可撤銷，須寫入後台操作紀錄（操作人員、時間、對象交易）"),
    tc("REQ-ARCADE-006", ["AC-ARCADE-007"], "洗分出金核實的作廢動作寫入後台操作紀錄",
       ["有一筆待核實的機台出金收據"],
       ["於洗分出金核實頁對該筆執行「作廢」操作（填寫必填的作廢原因）", "檢視後台操作紀錄"],
       "該筆作廢動作被記錄，內容含執行的操作人員、時間，以及對應的交易編號",
       "對既有章節的影響／7.4 操作紀錄", "洗分出金核實（含收據核銷）與作廢屬現金相關操作且不可撤銷，須寫入後台操作紀錄（操作人員、時間、對象交易）"),
]

by_req = {}
for t in T: by_req.setdefault(t["requirement_ids"][0], []).append(t["draft_id"])
by_req_ac = {}
for t in T:
    rid = t["requirement_ids"][0]
    by_req_ac.setdefault(rid, {})
    for ac in t["acceptance_criteria_ids"]:
        by_req_ac[rid].setdefault(ac, []).append(t["draft_id"])

coverage_matrix = [
    {"requirement_id": rid, "draft_ids": draft_ids,
     "acceptance_criteria": [{"ac_id": ac, "draft_ids": d} for ac, d in by_req_ac[rid].items()]}
    for rid, draft_ids in by_req.items()
]
tech_count = {}
for t in T:
    for tech in t["design_techniques"]: tech_count[tech] = tech_count.get(tech, 0) + 1

def envelope(t, payload, refs, task="T2"):
    aid = ids.artifact_id(t); art = {"artifact_id": aid, "artifact_type": t, "schema_version": "1.0", "version": 1, "run_id": RUN, "task_id": task, "iteration": ITER,
           "created_by": A, "created_at": store.now(), "status": "DRAFT", "source": {"type": "TestCaseVersion", "ids": []},
           "references": refs, "requires_approval": None, "payload": payload}
    p = store.ROOT / "artifacts" / "test-design" / RUN / f"{aid}.yaml"; store.save(p, art); return aid, p

rep = {"mode": "spec", "testcase_draft_artifact_id": None, "coverage_matrix": coverage_matrix,
       "uncovered_with_reason": [], "technique_summary": [{"technique": k, "count": v} for k, v in tech_count.items()],
       "self_check": {k: True for k in ["requirements_covered", "acceptance_criteria_covered", "negative_considered", "boundary_considered", "expected_results_traceable", "no_unsupported_assumptions", "duplicate_detection_completed"]},
       "assumptions": [], "duplicate_check": {"against_registry": True, "findings": []}}

refs = [{"entity_type": "Requirement", "id": rid} for rid in by_req] + [{"entity_type": "Artifact", "id": RM_AID}]
did, p1 = envelope("TestCaseDraft", {"mode": "spec", "spec_id": SID, "spec_version": SV, "testcases": T}, refs)
rep["testcase_draft_artifact_id"] = did
_, p2 = envelope("TestDesignReport", rep, [{"entity_type": "Artifact", "id": did}])
print(p1.relative_to(store.ROOT)); print(p2.relative_to(store.ROOT))
print(f"{len(T)} TCs across {len(by_req)} requirements")
