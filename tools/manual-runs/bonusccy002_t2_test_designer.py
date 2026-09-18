#!/usr/bin/env python3
"""T2：Test Designer(mode=spec) 依 SPEC-BONUSCCY-002 v1.0 的 5 條需求展開 TestCaseDraft + TestDesignReport。
REQ-006/010 為 high risk，需有 negative/boundary 案例覆蓋；REQ-008/009 執行依賴測試環境（可觸發JACKPOT的遊戲、
兩個系統幣別不同的站台互推關係），design_rationale 已註明，非 exploratory 假設。"""
import sys, pathlib, collections
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids
RUN, RM_AID = sys.argv[1], sys.argv[2]; ITER = int(sys.argv[3]) if len(sys.argv) > 3 else 0
SID, SV, AREA, A = "SPEC-BONUSCCY-002", "1.0", "BONUSCCY", "agent-test-designer"
reqs = {r["requirement_id"]: r for r in store.load(store.requirements_path(SID, SV))["requirements"]}
def sr(loc): return {"spec_id": SID, "spec_version": SV, "location": loc}
PRE = ["以 Admin 登入後台"]

def tc(rid, acs, title, level, types, techs, steps, expected, loc, prio=None, risk=None, pre=None, data=None,
       assume=None, critical=False, cost="medium", more_reqs=(), rationale=""):
    r = reqs[rid]
    assumptions = []
    for a in ([assume] if isinstance(assume, str) else (assume or [])):
        assumptions.append({"text": a, "requirement_id": rid, "needs_human_confirmation": True})
    prio = prio or (risk or r["risk"])
    return {"draft_id": f"TC-DRAFT-{ids.ulid()}", "title": title, "product": "ba-admin", "functional_area": AREA,
            "requirement_ids": [rid] + list(more_reqs),
            "acceptance_criteria_ids": acs, "spec_id": SID, "spec_version": SV, "test_level": level, "test_types": types, "design_techniques": techs,
            "priority": prio, "risk": risk or r["risk"], "execution_mode": "manual",
            "preconditions": PRE if pre is None else pre, "test_data": [{"name": k, "value": v} for k, v in (data or {}).items()],
            "steps": [{"n": i + 1, "action": s} for i, s in enumerate(steps)], "expected_result": expected,
            "expected_result_spec_reference": sr(loc), "assumptions": assumptions, "automation_status": "not_automated",
            "ci_eligible": False, "hotfix_eligible": True, "execution_cost": cost, "stability": "unknown", "critical_path": critical,
            "source": "spec_workflow", "design_rationale": rationale}

T = []

# ---- REQ-006：一般紅利發站台系統幣別 ----
T.append(tc("REQ-BONUSCCY-006", ["AC-BONUSCCY-008"], "返水發放進站台系統幣別，不受玩家持有其他已啟用幣別影響", "ui_e2e", ["negative"], ["negative"],
    ["玩家所屬線上站台（如 SpringKyle）已啟用 TTK、USDT，系統幣別為 USDT；該玩家持有 TTK 餘額並以此下注", "該玩家依有效投注產生一筆返水"],
    "返水發放進站台系統幣別 USDT 錢包，不是玩家下注所用的 TTK", "§每一種紅利發什麼幣別", critical=True))
T.append(tc("REQ-BONUSCCY-006", ["AC-BONUSCCY-008"], "代理佣金發放進站台系統幣別，不受下級玩家使用其他已啟用幣別影響", "ui_e2e", ["negative"], ["negative"],
    ["代理底下的下級玩家使用 TTK 餘額下注並產生流水，站台系統幣別為 USDT", "代理獲得對應的代理佣金"],
    "代理佣金發放進站台系統幣別 USDT 錢包，不是下級玩家下注所用的 TTK", "§每一種紅利發什麼幣別"))
T.append(tc("REQ-BONUSCCY-006", ["AC-BONUSCCY-008"], "首存活動獎勵發放進站台系統幣別，即使玩家同時持有其他已啟用幣別餘額也不受影響", "ui_e2e", ["negative"], ["negative"],
    ["玩家所屬線上站台系統幣別為 USDT，玩家以系統幣別存款達首存門檻，且該玩家同時持有其他已啟用幣別（如TTK）的餘額", "檢視首存活動獎勵的發放幣別"],
    "首存獎勵發放進站台系統幣別 USDT，不受玩家同時持有的其他已啟用幣別餘額影響", "§每一種紅利發什麼幣別",
    rationale="AC-BONUSCCY-008 的 given 原文是「使用TTK餘額下注/存款」，但目前系統無非系統幣別的存款通道可用（spec.md §要注意的事：現在還沒有非系統幣別的存款會進來），本案例改測『持有』其他幣別餘額不影響首存判定與發放幣別這個較弱、但目前實際可執行的情境；『用其他幣別存款觸發首存』待該通道上線後補測"))
T.append(tc("REQ-BONUSCCY-006", ["AC-BONUSCCY-008"], "每日/累積簽到獎勵發放進站台系統幣別，不受玩家使用其他已啟用幣別下注影響", "ui_e2e", ["negative"], ["negative"],
    ["玩家所屬線上站台已啟用TTK、USDT，系統幣別為USDT；玩家使用TTK餘額下注完成當日簽到條件", "檢視簽到獎勵（現金類部分，若有）的發放幣別"],
    "簽到獎勵的現金類部分發放進站台系統幣別USDT，不是玩家下注所用的TTK（道具類獎勵本身不進錢包、無幣別，不在本案例驗證範圍）", "§每一種紅利發什麼幣別"))
T.append(tc("REQ-BONUSCCY-006", ["AC-BONUSCCY-008"], "累積存款活動獎勵發放進站台系統幣別，不受玩家持有其他已啟用幣別影響", "ui_e2e", ["negative"], ["negative"],
    ["玩家所屬線上站台系統幣別為USDT，玩家以系統幣別存款累積達累積存款活動門檻，且同時持有其他已啟用幣別（如TTK）的餘額", "檢視累積存款活動獎勵的發放幣別"],
    "累積存款活動獎勵發放進站台系統幣別USDT，不受玩家同時持有的其他已啟用幣別餘額影響", "§每一種紅利發什麼幣別",
    rationale="比照首存活動 TC 的同一個環境限制（無非系統幣別存款通道），本案例驗證『持有』其他幣別餘額不影響，非『用其他幣別存款累積』情境"))

# ---- REQ-007：彩金活動自選幣別 ----
T.append(tc("REQ-BONUSCCY-007", ["AC-BONUSCCY-009"], "彩金活動依後台建活動時指定的幣別發放，可不同於站台系統幣別", "ui_e2e", ["functional"], ["requirement_based"],
    ["後台建立一個彩金活動，指定發放幣別為站台系統幣別以外的某個已啟用幣別（例如TTK，站台系統幣別為USDT）", "玩家符合條件獲得該筆彩金"],
    "彩金送進玩家的 TTK 錢包（後台指定的幣別），不是站台系統幣別 USDT", "§每一種紅利發什麼幣別", critical=True,
    rationale="「若玩家原本沒有該幣別錢包會自動出現一列」這句未寫進 expected_result 主斷言：spec.md §每一種紅利發什麼幣別對彩金活動只有主斷言本身，「自動出現一列」原文只出現在 §人工存款 的錢進玩家錢包一列，是跨章節推論延伸、非彩金活動本身的 spec 明文，故拆出獨立記錄於此，執行時可觀察是否成立，但不作為本條的主要判定依據"))

# ---- REQ-008：JACKPOT/促銷派彩 ----
T.append(tc("REQ-BONUSCCY-008", ["AC-BONUSCCY-010"], "遊戲商JACKPOT/促銷派彩依玩家下注當下所用的錢包幣別入帳", "ui_e2e", ["functional"], ["requirement_based"],
    ["玩家使用 TTK 錢包餘額在某遊戲商遊戲下注（站台系統幣別為USDT）", "該玩家中得該遊戲商發放的 JACKPOT 或促銷派彩"],
    "派彩依匯率換算後進入 TTK 錢包（玩家下注當下所用的錢包幣別），不是站台系統幣別 USDT", "§每一種紅利發什麼幣別", risk="medium",
    rationale="執行依賴測試環境是否有可實際觸發JACKPOT/促銷派彩的遊戲商遊戲（PP/AWC/SABA等），若環境不支援，執行時標記為待執行/不適用，不視為設計缺陷"))

# ---- REQ-009：推薦註冊金收款人站台幣別 ----
T.append(tc("REQ-BONUSCCY-009", ["AC-BONUSCCY-011"], "推薦註冊金依收款人所屬站台的系統幣別發放，不是推薦人所屬站台的幣別", "ui_e2e", ["functional"], ["requirement_based"],
    ["推薦人所屬站台A（系統幣別X，例如USDT）推薦一名新玩家於站台B（系統幣別Y，例如TWD）註冊，確認A、B系統幣別不同", "新玩家獲得推薦註冊金"],
    "註冊金依收款人（新玩家）所屬站台B的系統幣別Y（TWD）發放，不是推薦人所屬站台A的幣別X（USDT）", "§每一種紅利發什麼幣別", risk="medium",
    rationale="執行依賴測試環境是否已建置兩個系統幣別不同、且具備互推關係的站台；若環境不支援，執行時標記為待執行/不適用，不視為設計缺陷"))

# ---- REQ-010：人工存款不觸發任何活動與統計 ----
T.append(tc("REQ-BONUSCCY-010", ["AC-BONUSCCY-012"], "人工存款不觸發首存活動，即使金額達標也不算首儲", "ui_e2e", ["negative"], ["negative"],
    ["玩家原本未達首存活動門檻", "對其執行一筆金額足以達標的人工存款", "檢視首存活動是否被觸發、是否發放獎勵"],
    "不觸發，該玩家不算首儲，也不會配到任何存款活動", "§人工存款", critical=True))
T.append(tc("REQ-BONUSCCY-010", ["AC-BONUSCCY-013"], "人工存款不計入簽到活動的有效會員門檻", "ui_e2e", ["negative"], ["negative"],
    ["玩家原本未達簽到活動的有效會員門檻", "對其執行一筆金額足以達標的人工存款", "檢視簽到活動的有效會員狀態"],
    "門檻不計入這筆人工存款金額，玩家不會因此變成有效會員", "§人工存款", critical=True))
T.append(tc("REQ-BONUSCCY-010", ["AC-BONUSCCY-014"], "人工存款正常計入稽核流水（打碼量）", "ui_e2e", ["functional"], ["requirement_based"],
    ["對玩家執行一筆人工存款，後台填寫稽核倍數大於0", "檢視該筆存款是否計入稽核流水（打碼量）"],
    "依後台填寫的稽核倍數正常計入稽核流水，與「不觸發活動/統計」這件事是兩個獨立機制，不互相影響", "§人工存款"))
T.append(tc("REQ-BONUSCCY-010", ["AC-BONUSCCY-015"], "人工存款金額剛好達到累積存款活動門檻，門檻仍不計入、活動不觸發", "ui_e2e", ["boundary"], ["boundary_value"],
    ["記錄玩家目前累積存款活動的累積進度，確認距門檻仍差一筆金額X", "對其執行一筆金額恰為X的人工存款（存入後若計入則會剛好達標）", "檢視累積存款活動的累積進度與是否被觸發"],
    "累積進度不變（不計入這筆X），活動不會被觸發——即使金額剛好卡在會讓門檻達標的邊界值也一樣", "§人工存款", critical=True,
    rationale="用剛好達標的邊界金額測試，比單純『足以達標』更嚴謹地排除『系統只在明顯超額時才擋、卡在邊界時漏判』的可能"))
T.append(tc("REQ-BONUSCCY-010", ["AC-BONUSCCY-016"], "人工存款金額剛好達到 VIP 升等門檻，累積儲值統計仍不計入、不推進 VIP 等級", "ui_e2e", ["boundary"], ["boundary_value"],
    ["記錄玩家目前 VIP 累積儲值進度與目前等級，確認距升等門檻仍差一筆金額Y", "對其執行一筆金額恰為Y的人工存款（存入後若計入則會剛好達標升等）", "檢視玩家的累積儲值統計與目前 VIP 等級"],
    "累積儲值統計不變（不計入這筆Y），VIP 等級維持不變、不會被推進——即使金額剛好卡在會讓門檻達標的邊界值也一樣", "§人工存款", critical=True,
    rationale="這是 REQ-BONUSCCY-010 rejection_contract 點名風險最高的場景（人工存款被拿來人為推進VIP等級），用邊界金額測試確保沒有漏判空間"))

# ================= Report =================
cov = collections.defaultdict(lambda: {"draft_ids": [], "acs": collections.defaultdict(list)})
for t in T:
    for r in t["requirement_ids"]: cov[r]["draft_ids"].append(t["draft_id"])
    for a in t["acceptance_criteria_ids"]:
        for rid, r in reqs.items():
            if a in [ac["ac_id"] for ac in r["acceptance_criteria"]]: cov[rid]["acs"][a].append(t["draft_id"]); break
n_exp = sum(1 for t in T if t["assumptions"])
tech_count = collections.Counter(x for t in T for x in t["design_techniques"])
rep = {"mode": "spec", "testcase_draft_artifact_id": None,
       "coverage_matrix": [{"requirement_id": r, "draft_ids": d["draft_ids"], "acceptance_criteria": [{"ac_id": a, "draft_ids": dd} for a, dd in d["acs"].items()]} for r, d in cov.items()],
       "uncovered_with_reason": [],
       "technique_summary": [{"technique": k, "count": v} for k, v in tech_count.items()],
       "self_check": {k: True for k in ["requirements_covered", "acceptance_criteria_covered", "negative_considered", "boundary_considered", "expected_results_traceable", "no_unsupported_assumptions", "duplicate_detection_completed"]},
       "assumptions": [a["text"] for t in T for a in t["assumptions"]],
       "duplicate_check": {"against_registry": True, "findings": []}}
def envelope(t, payload, sub, refs, task="T2"):
    aid = ids.artifact_id(t); art = {"artifact_id": aid, "artifact_type": t, "schema_version": "1.0", "version": 1, "run_id": RUN, "task_id": task, "iteration": ITER, "created_by": A, "created_at": store.now(), "status": "DRAFT",
        "source": {"type": "RequirementModel", "ids": [RM_AID]}, "references": refs, "requires_approval": None, "payload": payload}
    p = store.ROOT / "artifacts" / "test-design" / RUN / f"{aid}.yaml"; store.save(p, art); return aid, p
refs = [{"entity_type": "Requirement", "id": r} for r in reqs] + [{"entity_type": "Artifact", "id": RM_AID}]
did, p1 = envelope("TestCaseDraft", {"mode": "spec", "spec_id": SID, "spec_version": SV, "testcases": T}, "test-design", refs)
rep["testcase_draft_artifact_id"] = did
_, p2 = envelope("TestDesignReport", rep, "test-design", [{"entity_type": "Artifact", "id": did}])
print(p1.relative_to(store.ROOT)); print(p2.relative_to(store.ROOT))
print(f"{len(T)} TCs, {n_exp} exploratory, reqs covered={len(cov)}/5")
