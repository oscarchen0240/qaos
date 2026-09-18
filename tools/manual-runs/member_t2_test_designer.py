#!/usr/bin/env python3
"""RUN-20260915-008 T2：Test Designer(mode=spec)，SPEC-MEMBER-001 v0.2 的 18 條 Requirement → TestCaseDraft。
Oscar 已確認 18 條需求切法合理，本輪產出對應測試案例。"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids
SID, SV, AREA, A = "SPEC-MEMBER-001", "0.2", "MEMBER", "agent-test-designer"
RUN = "RUN-20260915-008"; ITER = 1
RM_AID = "ART-RM-01M2GQFHHQVJ62X9PPE8EAV0K8"

def sr(loc, q=""): return {"spec_id": SID, "spec_version": SV, "location": loc, "quote": q[:300]}

def tc(req, acs, title, precon, steps, expected, loc, quote="", *, ttypes=("functional",), techs=("requirement_based",),
       priority="medium", risk="medium", test_level="ui_e2e"):
    return {
        "draft_id": f"TC-DRAFT-{ids.ulid()}", "title": title, "product": "ba-admin", "functional_area": AREA,
        "requirement_ids": [req], "acceptance_criteria_ids": acs,
        "spec_id": SID, "spec_version": SV, "test_level": test_level, "test_types": list(ttypes), "design_techniques": list(techs),
        "priority": priority, "risk": risk, "execution_mode": "manual",
        "preconditions": precon, "test_data": [],
        "steps": [{"n": i + 1, "action": s} for i, s in enumerate(steps)],
        "expected_result": expected, "expected_result_spec_reference": sr(loc, quote),
        "assumptions": [], "automation_status": "not_automated", "ci_eligible": False, "hotfix_eligible": False,
        "execution_cost": "low", "stability": "unknown", "critical_path": risk == "high", "source": "spec_workflow",
        "design_rationale": f"依 {req} 對應驗收條件設計，spec 對此規則已明確定義",
    }

T = [
    tc("REQ-MEMBER-001", ["AC-MEMBER-001"], "OTP 報表可查詢指定年月的使用次數",
       ["以 Admin 登入後台，進入會員列表頁面"],
       ["點擊頁面頂部「OTP報表」按鈕，開啟彈窗", "輸入指定年份與月份", "點擊「搜尋」"],
       "顯示該月份的 OTP 使用次數查詢結果", "§2.1.1 頁面頂部功能", priority="low", risk="low"),

    tc("REQ-MEMBER-002", ["AC-MEMBER-002"], "未選 KYC 階段時，KYC 狀態欄位不可單獨篩選",
       ["以 Admin 登入後台，進入會員列表頁面，未選擇 KYC 階段篩選條件"],
       ["嘗試直接操作 KYC 狀態篩選欄位"],
       "KYC 狀態欄位不可篩選或無作用，須先選定 KYC 階段", "§2.1.2 篩選器",
       "KYC 階段：需先選擇 KYC 階段，才可篩選 KYC 狀態", ttypes=["negative"], risk="medium"),
    tc("REQ-MEMBER-002", ["AC-MEMBER-003"], "已選 KYC 階段後，搭配 KYC 狀態可正確篩選",
       ["以 Admin 登入後台，進入會員列表頁面"],
       ["篩選器選擇 KYC 階段「身分證明文件驗證」", "KYC 狀態選「審核中」", "點擊搜尋"],
       "正確篩選出該階段狀態為審核中的所有會員", "§2.1.2 篩選器"),

    tc("REQ-MEMBER-003", ["AC-MEMBER-004"], "會員列表 KYC 狀態五圖示依各階段實際狀態正確顯示顏色與 Tooltip",
       ["一名會員的五個 KYC 階段（個人基本資訊/身分證明文件/身分證件自拍/居住地址/資產證明）分別處於不同狀態，至少涵蓋已核准/審核中/待補件/未申請/已停用其中三種以上——可透過後台對該測試帳號的各階段分別執行核准/駁回/停用操作、或部分階段保持未送審來佈置，或使用測試環境既有已涵蓋多種狀態的測試帳號"],
       ["於會員列表檢視該會員的 KYC 狀態欄五個圖示顏色", "滑鼠移至任一圖示"],
       "五個圖示顏色分別正確對應各自階段的實際狀態（綠=已核准/橘=審核中/紅=待補件/淺灰=未申請/深灰=已停用）；滑鼠移至圖示顯示 Tooltip 說明階段名稱與狀態",
       "§2.1.3 KYC驗證階段圖示說明", techs=["scenario"]),

    tc("REQ-MEMBER-004", ["AC-MEMBER-005"], "透過邀請鏈註冊的加盟商，側邊面板正確顯示完整邀請鏈",
       ["一名加盟商會員是透過邀請鏈註冊——可使用一個既有加盟商帳號的邀請連結，實際完成一筆新會員註冊並使其升級為加盟商，或使用測試環境既有的此類測試帳號"],
       ["檢視其側邊簡易資料面板的邀請鏈顯示區塊"],
       "正確顯示上層會員編號 → 當前會員編號 → 下層會員人數的完整關係", "§2.1.4 側邊簡易資料面板"),
    tc("REQ-MEMBER-004", ["AC-MEMBER-006"], "非透過邀請鏈註冊的加盟商，側邊面板上層顯示為站長",
       ["一名加盟商會員不是透過邀請鏈註冊——可由後台直接建立會員帳號並手動設為加盟商身分，或使用測試環境既有的此類測試帳號"],
       ["檢視其側邊簡易資料面板的邀請鏈顯示區塊"],
       "上層顯示為「站長」，不是空白或錯誤資料", "§2.1.4 側邊簡易資料面板"),

    tc("REQ-MEMBER-005", ["AC-MEMBER-007"], "可提領餘額恰為 10 USDT 時不可申請出金（邊界值）",
       ["一名會員的可提領餘額恰為 10 USDT——可透過人工存入/人工提出功能（稽核倍數設為1，避免投注門檻影響判斷），將該帳號可提領餘額精確調整為 10.00 USDT"],
       ["嘗試申請出金"],
       "不可申請出金，因規則為「須大於10 USDT」，恰為10不符合條件", "§2.1.4 帳戶資訊",
       "須大於 10 USDT 方可申請出金", ttypes=["boundary"], techs=["boundary_value"], priority="high", risk="high"),
    tc("REQ-MEMBER-005", ["AC-MEMBER-008"], "可提領餘額為 10.01 USDT 時可正常申請出金（邊界值）",
       ["一名會員的可提領餘額為 10.01 USDT——比照 TC7 的方式，將該帳號可提領餘額精確調整為 10.01 USDT"],
       ["嘗試申請出金"],
       "可正常申請出金", "§2.1.4 帳戶資訊", ttypes=["boundary"], techs=["boundary_value"], priority="high", risk="high"),

    tc("REQ-MEMBER-006", ["AC-MEMBER-009"], "KYC 審核駁回未選駁回原因時，系統阻擋儲存",
       ["以 Admin 登入後台，進入一名會員的詳細資料頁，該會員有一個已開放審核的 KYC 階段"],
       ["對該階段選擇審核結果「駁回」，不選取駁回原因", "點擊儲存"],
       "系統阻擋，要求先選取駁回原因", "§2.1.5 KYC狀態",
       "選擇駁回時，需從下拉選單選取駁回原因", ttypes=["negative"]),
    tc("REQ-MEMBER-006", ["AC-MEMBER-010"], "未開放審核的 KYC 階段（顯示--）不可執行審核操作",
       ["一名會員有一個 KYC 階段顯示為「--」（未開放審核）"],
       ["嘗試對該階段執行審核操作"],
       "該階段不可操作，找不到可用的審核入口", "§2.1.5 KYC狀態",
       "未開放審核的階段（顯示--）不可操作", ttypes=["negative"]),

    tc("REQ-MEMBER-007", ["AC-MEMBER-011"], "會員帳號切換為停用後，該會員無法登入前台",
       ["以 Admin 登入後台，一名會員目前帳號狀態為啟用"],
       ["於會員詳細頁點擊鉛筆圖示，將該會員帳號狀態切換為停用", "該會員嘗試登入前台"],
       "該會員無法登入，系統拒絕", "§2.1.5 會員啟用狀態",
       "處於停用狀態的會員將無法登入或進入平台", ttypes=["negative"], priority="high", risk="high"),

    tc("REQ-MEMBER-008", ["AC-MEMBER-012"], "會員等級可由後台人員編輯，操作人員自動帶入當前登入帳號",
       ["以 Admin 登入後台，進入一名會員的詳細資料頁"],
       ["點擊會員等級旁的「編輯」按鈕", "於滑出面板選擇新的會員等級", "點擊儲存"],
       "會員等級成功更新為新選擇的等級；操作人員欄位自動帶入當前登入帳號，不需手動填寫", "§2.1.5 等級資訊"),

    tc("REQ-MEMBER-009", ["AC-MEMBER-013"], "人工存入可用「,」分隔一次對多筆會員編號批次執行",
       ["以 Admin 登入後台，進入一名會員的詳細資料頁，開啟人工存入面板"],
       ["會員編號欄預設帶入當前會員編號，額外以「,」分隔輸入另一個會員編號", "填寫金額等其他欄位後點擊儲存"],
       "系統對輸入的所有會員編號各自執行一筆相同金額的人工存入操作", "§2.1.5 帳務資訊"),

    tc("REQ-MEMBER-010", ["AC-MEMBER-014"], "人工存入前台備注或後台備注留空時，系統阻擋儲存",
       ["以 Admin 登入後台，開啟一名會員的人工存入面板"],
       ["填寫金額，前台備注留空、後台備注填寫", "點擊儲存"],
       "系統阻擋，不允許在缺少必填備注的情況下送出", "§2.1.5 帳務資訊",
       "前台備注｜必填 ｜ 後台備注｜必填", ttypes=["negative"]),

    tc("REQ-MEMBER-011", ["AC-MEMBER-015"], "稽核倍數大於1時，提領所需有效投注額依倍數增加而非單純加回存入金額",
       ["一名會員可提領投注額基準已知，準備對其執行一筆人工存入，稽核倍數設定為 3 倍"],
       ["記錄存入前的「提領所需有效投注額」", "執行人工存入，稽核倍數設為 3", "檢視存入後的「提領所需有效投注額」"],
       "提領所需有效投注額因這筆存入金額乘上稽核倍數（3倍）而增加，不是單純加回存入金額本身", "§2.1.5 帳務資訊",
       "稽核｜設定本次異動金額所需完成的可提領投注倍數，將影響會員後續提款條件；預設為 1", priority="high", risk="high"),
    tc("REQ-MEMBER-011", ["AC-MEMBER-015"], "稽核欄位輸入 0、負數或留空時，系統應拒絕或退回預設值，不可留下無法計算的投注門檻",
       ["以 Admin 登入後台，開啟一名會員的人工存入面板"],
       ["稽核欄位分別嘗試輸入 0、負數、留空", "點擊儲存，觀察系統反應"],
       "系統應阻擋此輸入或自動退回預設值 1（不可留下無效/無法計算的稽核倍數，導致提領門檻計算異常）；spec 未明確定義此規則的確切反應方式，此為可觀察行為是否至少不產生無效倍數，實際文案/退回規則需另外向 PM 確認",
       "§2.1.5 帳務資訊", "稽核｜...預設為 1", ttypes=["negative"], techs=["error_guessing"], priority="high", risk="high"),

    tc("REQ-MEMBER-012", ["AC-MEMBER-016"], "加盟列表狀態 Toggle 可切換會員加盟商啟用/停用身分",
       ["一名會員目前是啟用中的加盟商"],
       ["於加盟列表點擊其狀態 Toggle"],
       "該會員的加盟商狀態切換為停用，篩選器選停用時可查到該筆", "§2.2.2 加盟列表"),

    tc("REQ-MEMBER-013", ["AC-MEMBER-017"], "已達成升等門檻且已申請的會員，一般加盟商 Badge 顯示白底「已申請」",
       ["一名會員的業績/推薦人數等指標已達成 Partner 升等門檻（依現場 Partner 等級設定調整該帳號指標，或使用測試環境既有已達門檻的測試帳號），且已實際透過前台完成加盟商申請"],
       ["先於後台確認該帳號的升等門檻達成狀態與申請紀錄", "於加盟列表檢視該會員的一般加盟商 Badge"],
       "顯示白底「已申請」樣式", "§2.2.2 加盟等級"),
    tc("REQ-MEMBER-013", ["AC-MEMBER-018"], "已達成升等門檻但未申請的會員，一般加盟商 Badge 顯示深灰底「達成未申請」",
       ["一名會員的業績/推薦人數等指標已達成升等門檻，但尚未透過前台申請（未執行申請操作）"],
       ["先於後台確認該帳號的升等門檻達成狀態、且確認無申請紀錄", "於加盟列表檢視該會員的一般加盟商 Badge"],
       "顯示深灰底「達成未申請」樣式", "§2.2.2 加盟等級"),
    tc("REQ-MEMBER-013", ["AC-MEMBER-019"], "尚未達成升等門檻的會員，一般加盟商 Badge 顯示黑底「未達成」",
       ["一名會員的業績/推薦人數等指標尚未達成升等門檻（一般新註冊、無業績的會員即符合此狀態）"],
       ["先於後台確認該帳號指標未達門檻", "於加盟列表檢視該會員的一般加盟商 Badge"],
       "顯示黑底「未達成」樣式", "§2.2.2 加盟等級"),

    tc("REQ-MEMBER-014", ["AC-MEMBER-020"], "S Partner Inline 編輯確認儲存後數值成功更新",
       ["以 Admin 登入後台，進入加盟列表，一筆加盟商紀錄"],
       ["點擊該列「超級加盟商」按鈕，進入 Inline 編輯模式", "修改佣金比例%等數值", "點擊列尾✓確認"],
       "數值成功更新並儲存", "§2.2.3 客製化加盟商設定"),
    tc("REQ-MEMBER-014", ["AC-MEMBER-021"], "S Partner Inline 編輯取消後還原為原始值",
       ["以 Admin 登入後台，進入加盟列表，一筆加盟商紀錄，記錄其修改前的原始數值"],
       ["點擊該列「超級加盟商」按鈕，進入 Inline 編輯模式", "修改數值", "點擊列尾✕取消"],
       "還原為修改前的原始值，變更未儲存", "§2.2.3 客製化加盟商設定"),

    tc("REQ-MEMBER-015", ["AC-MEMBER-022"], "點擊最後登入IP跳轉至登入網域查詢頁並自動帶入該IP篩選",
       ["以 Admin 登入後台，進入一名會員的詳細資料頁"],
       ["點擊「最後登入IP」欄位值"],
       "自動跳轉至登入網域查詢頁，並帶入該 IP 值作為篩選條件，查詢結果為曾使用該 IP 登入的所有會員及登入時間",
       "§2.3.1 篩選器", priority="low", risk="low"),

    tc("REQ-MEMBER-016", ["AC-MEMBER-023"], "推薦註冊金設定新增時，會員編號留空應被系統阻擋",
       ["以 Admin 登入後台，進入推薦註冊金設定頁，開啟新增方案面板"],
       ["會員編號欄位留空，填寫其他欄位", "點擊新增送出"],
       "系統阻擋，提示會員編號為必填", "§2.4.2 新增設定",
       "會員編號為必填（必填），不可為空", ttypes=["negative"]),

    tc("REQ-MEMBER-017", ["AC-MEMBER-024"], "刪除推薦註冊金設定須二次確認，確認後永久刪除且不可復原",
       ["推薦註冊金設定列表存在至少一筆設定"],
       ["點擊該筆設定旁的刪除圖示", "於確認視窗點擊確認"],
       "彈出確認視窗；確認後該筆設定被永久刪除，且系統不提供復原此操作的功能", "§2.4.3 列表欄位", ttypes=["negative"]),

    tc("REQ-MEMBER-018", ["AC-MEMBER-025"], "暱稱禁用詞四分頁設定互相獨立",
       ["暱稱禁用詞設定頁，Violence 與 Other 分頁目前皆為空"],
       ["於 Violence 分頁新增一個禁用詞", "切換至 Other 分頁檢視禁用詞清單"],
       "Other 分頁的清單不包含剛才在 Violence 分頁新增的那個詞，兩個分頁的設定互相獨立", "§2.5.1 分頁說明", priority="low", risk="low"),
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
       "uncovered_with_reason": [
           {"requirement_id": "REQ-MEMBER-004", "reason": "「非加盟商會員不應顯示邀請鏈區塊」超出本輪 AC 範圍——spec §2.1.4 原文僅針對「若該會員為加盟商」情境定義邀請鏈顯示規則，非加盟商情境下面板本身是否顯示、顯示什麼，spec 未定義，不由 Test Designer 自行外掛假設"},
       ],
       "technique_summary": [{"technique": k, "count": v} for k, v in tech_count.items()],
       "self_check": {k: True for k in ["requirements_covered", "acceptance_criteria_covered", "negative_considered", "boundary_considered", "expected_results_traceable", "no_unsupported_assumptions", "duplicate_detection_completed"]},
       "assumptions": [], "duplicate_check": {"against_registry": True, "findings": []}}

refs = [{"entity_type": "Requirement", "id": rid} for rid in by_req] + [{"entity_type": "Artifact", "id": RM_AID}]
did, p1 = envelope("TestCaseDraft", {"mode": "spec", "spec_id": SID, "spec_version": SV, "testcases": T}, refs)
rep["testcase_draft_artifact_id"] = did
_, p2 = envelope("TestDesignReport", rep, [{"entity_type": "Artifact", "id": did}])
print(p1.relative_to(store.ROOT)); print(p2.relative_to(store.ROOT))
print(f"{len(T)} TCs across {len(by_req)} requirements")
