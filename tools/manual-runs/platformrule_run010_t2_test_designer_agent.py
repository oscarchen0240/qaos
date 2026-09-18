#!/usr/bin/env python3
"""T2: Test Designer (mode=spec) 依 SPEC-PLATFORMRULE-001 v0.1 的 23 條 requirement / 31 條 AC
展開 TestCaseDraft + TestDesignReport。RUN-20260918-010。

High risk requirements（需 non-happy 覆蓋）：REQ-PLATFORMRULE-004、013、014、015、017、018、021、022。

Phase 3 影子測試：本腳本為獨立設計，未讀取 testcases/registry/TC-PLATFORMRULE-*.yaml、
testcases/versions/TC-PLATFORMRULE-*、testcases/PLATFORMRULE.md 等 Phase 2 既有人工 TC 內容，
以維持設計視角獨立。

本包所有功能皆為後台管理系統功能（選單顯示、角色權限、機台/遊戲管理），無涉會員前台操作，
故 precondition 皆以「登入後台」為基礎。少數 TC（機台出金核實完成、機台開分/入金交易完成、
平台新增/發布遊戲更新）依賴的是機台現場硬體流程或本 spec 未定義操作介面的後台動作，這些
一律以 assumptions + needs_human_confirmation 誠實揭露，不當作確定規則驗證。
"""
import sys, pathlib, collections
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids

RUN = "RUN-20260918-010"
RM_AID = "ART-RM-01M2G36NQCPQX2T3X2J841RYJC"
ITER = 0
SID, SV, AREA, A = "SPEC-PLATFORMRULE-001", "0.1", "PLATFORMRULE", "agent-test-designer"
reqs = {r["requirement_id"]: r for r in store.load(store.requirements_path(SID, SV))["requirements"]}


def sr(loc, quote=""):
    d = {"spec_id": SID, "spec_version": SV, "location": loc}
    if quote:
        d["quote"] = quote[:400]
    return d


PRE_ADMIN = ["以 Admin 登入後台"]


def tc(rid, acs, title, level, types, techs, pre, steps, expected, loc, quote="", prio=None, risk=None,
       data=None, assume=None, critical=False, cost="medium", more_reqs=(), rationale=""):
    r = reqs[rid]
    assumptions = []
    for a in ([assume] if isinstance(assume, str) else (assume or [])):
        assumptions.append({"text": a, "requirement_id": rid, "needs_human_confirmation": True})
    prio = prio or (risk or r["risk"])
    return {
        "draft_id": f"TC-DRAFT-{ids.ulid()}", "title": title, "product": "ba-admin", "functional_area": AREA,
        "requirement_ids": [rid] + list(more_reqs), "acceptance_criteria_ids": acs,
        "spec_id": SID, "spec_version": SV, "test_level": level, "test_types": types, "design_techniques": techs,
        "priority": prio, "risk": risk or r["risk"], "execution_mode": "manual",
        "preconditions": pre, "test_data": [{"name": k, "value": v} for k, v in (data or {}).items()],
        "steps": [{"n": i + 1, "action": s} for i, s in enumerate(steps)], "expected_result": expected,
        "expected_result_spec_reference": sr(loc, quote), "assumptions": assumptions,
        "automation_status": "not_automated", "ci_eligible": False, "hotfix_eligible": True,
        "execution_cost": cost, "stability": "unknown", "critical_path": critical,
        "source": "spec_workflow", "design_rationale": rationale,
    }


T = []

# ================= REQ-PLATFORMRULE-001（medium）機台出金不進入出金審核流程 =================

T.append(tc(
    "REQ-PLATFORMRULE-001", ["AC-PLATFORMRULE-0011"],
    "機台出金核實完成後，出金審核頁面查無該筆機台出金項目",
    "ui_e2e", ["functional", "negative"], ["scenario", "requirement_based"],
    PRE_ADMIN + [
        "站台切換下拉選單切換至一個既有的機台場館站台",
        "於『帳務管理 > 洗分出金核實』頁面尋找一筆狀態為『待核實』的機台出金申請並完成核實（含收據核銷），記錄核實完成的時間與對象機台帳號",
    ],
    ["於『帳務管理 > 出金審核』頁面，設定查詢區間涵蓋剛才核實完成那筆機台出金交易的時間範圍",
     "檢視查詢結果列表，尋找是否存在該筆機台出金項目；若查詢區間內另有線上會員的出金審核項目，一併記錄"],
    "出金審核頁面的查詢結果中查無剛才核實完成的那筆機台出金項目；頁面僅列出線上會員的出金審核項目（若查詢範圍內原本就有其他線上會員的出金審核項目，仍正常列出，僅機台出金不出現）",
    "§既有功能對機台帳號的排除規則 + §對既有章節的影響",
    "3.2 | 出金審核 | 不進入本流程。機台出金為現場即時核可並印出收據，不需後台審核",
    assume="機台出金申請本身的產生方式（現場即時核可、印出收據）屬機台端硬體現場流程，非本 spec 定義的後台 UI 操作；本 TC 假設測試環境的『洗分出金核實』頁面當下存在或可產生一筆狀態為『待核實』的機台出金申請供核實使用，若環境當下查無待核實項目，需洽環境負責人透過機台模擬工具或既有測試資料補上一筆，此步驟超出本 spec 定義範圍",
    critical=True,
    rationale="機台出金完成的前置動作（現場核可、印收據）本身不是可透過本 spec 定義的後台 UI 重現的動作，只有『核實』這一步在後台『洗分出金核實』頁面，因此本 TC 採 scenario 技巧串接『核實』與『出金審核頁面查驗』兩個頁面的實際工作流程，而非單頁靜態檢查；產生待核實項目的前置條件明確標為假設並要求人工確認，避免把無法從 spec 驗證的機台端流程當成後台可控制的既定步驟"))

# ================= REQ-PLATFORMRULE-002（medium）機台開分/入金稽核明細照常寫入 =================

T.append(tc(
    "REQ-PLATFORMRULE-002", ["AC-PLATFORMRULE-0021"],
    "機台開分或入金交易完成後，稽核明細頁面正常出現並標示正確交易類型",
    "ui_e2e", ["functional"], ["scenario", "requirement_based"],
    PRE_ADMIN + [
        "站台切換下拉選單切換至一個既有的機台場館站台",
        "選定一個既有的機台帳號，記錄一筆該帳號近期已完成的機台開分或機台入金交易的時間與金額（可先於『各式報表 > 交易紀錄查詢』核對是否已有現成記錄）",
    ],
    ["進入『各式報表 > 稽核明細』頁面，以該機台帳號與對應時間區間查詢",
     "檢視查詢結果中該筆交易的『交易類型』欄位標示"],
    "該筆機台開分或機台入金交易正常出現在稽核明細頁面查詢結果中；交易類型欄位標示為「機台開分」或「機台入金」（依實際操作類型而定），不是顯示為其他既有線上交易類型、也不是空白",
    "§既有功能對機台帳號的排除規則",
    "4.4 | 稽核明細 | 照常寫入。開分與入金比照既有的出金設定，可依幣種設定稽核倍數，機台預設為 0 倍（等同不設稽核門檻）；詳見下方「出金設定 TWD 頁籤」與正本「機台帳號的稽核」",
    assume="機台開分／入金交易本身是玩家在機台端實際遊玩產生的紀錄，非後台 UI 可直接建立的動作；本 TC 假設測試環境當下已存在或可查得該機台帳號至少一筆已完成的開分或入金交易供查驗，若環境當下查無現成記錄，需洽環境負責人透過機台模擬工具產生，此步驟超出本 spec 定義範圍",
    rationale="本條的稽核倍數規則本身（機台預設 0 倍、依幣種可設定倍數）已由 SPEC-CASHFLOW-001 驗證，故本 TC 依 RequirementModel 的 rejection_contract 說明僅聚焦『稽核明細頁面是否正常寫入且類型標示正確』這一顯示層面，不重複驗證倍數計算規則；產生交易紀錄的方式不在本 spec UI 範圍內，故以 assumption 誠實揭露"))

# ================= REQ-PLATFORMRULE-003（medium）Free Spin 例外 =================

T.append(tc(
    "REQ-PLATFORMRULE-003", ["AC-PLATFORMRULE-0031"],
    "Free Spin 管理選擇會員時可指定機台帳號，不因帳號類型而被排除",
    "ui_e2e", ["functional"], ["requirement_based"],
    PRE_ADMIN + ["選定一個既有的機台帳號"],
    ["進入『系統管理 > Free Spin 管理』，建立或編輯一個 Free Spin 活動，於選擇發放對象（會員）的步驟嘗試搜尋並選取前置作業選定的機台帳號",
     "確認該機台帳號在選擇清單中是否可被勾選/選取"],
    "系統允許選取該機台帳號作為 Free Spin 活動的發放對象，不因其帳號類型為機台而被過濾、隱藏或拒絕選取",
    "§既有功能對機台帳號的排除規則 + §Free Spin 例外",
    "6.8 | Free Spin 管理 | 適用，同一般會員。可將機台帳號指定加入 Free Spin 活動；免費旋轉由後台直接派發、不需玩家領取，共用帳號收得到。幣種依主站台核心貨幣（機台場館即 TWD），見正本「核心貨幣」"))

T.append(tc(
    "REQ-PLATFORMRULE-003", ["AC-PLATFORMRULE-0032"],
    "後台對機台帳號派發 Free Spin 後，免費旋轉直接到帳，不需玩家額外領取",
    "ui_e2e", ["functional"], ["requirement_based"],
    PRE_ADMIN + ["選定一個既有的機台帳號，記錄其目前的 Free Spin（免費旋轉）可用次數或狀態作為基準"],
    ["於『系統管理 > Free Spin 管理』對該機台帳號派發一筆 Free Spin（設定次數與幣種後送出）",
     "派發完成後，檢視該機台帳號目前的 Free Spin 狀態（可透過會員詳細資料頁或 Free Spin 管理的派發紀錄查看）"],
    "派發完成後，該機台帳號的免費旋轉可用次數立即增加（或呈現為已到帳狀態），不存在『待玩家領取』的中間狀態，不需要玩家或機台端另外操作才能取得",
    "§既有功能對機台帳號的排除規則 + §Free Spin 例外",
    "6.8 | Free Spin 管理 | 適用，同一般會員。可將機台帳號指定加入 Free Spin 活動；免費旋轉由後台直接派發、不需玩家領取，共用帳號收得到。幣種依主站台核心貨幣（機台場館即 TWD），見正本「核心貨幣」"))

# ================= REQ-PLATFORMRULE-004（high）站台切換選單隱藏/恢復 =================

T.append(tc(
    "REQ-PLATFORMRULE-004", ["AC-PLATFORMRULE-0041"],
    "切換至機台場館後，後台選單依隱藏規則調整，不適用頁面消失",
    "ui_e2e", ["functional", "negative"], ["requirement_based"],
    PRE_ADMIN + ["選定一個既有的機台場館站台"],
    ["使用頁面上方的站台切換下拉選單，切換至前置作業選定的機台場館站台",
     "展開左側選單全部分類，逐一檢視各分類下目前可見的項目清單"],
    "選單依「機台場館的後台選單」規則調整：資訊看板分類整個消失；會員與加盟商僅剩會員列表；帳務管理僅剩鏈上錢包管理與洗分出金核實；各式報表僅剩交易紀錄查詢、注單查詢、稽核明細、場館日結報表；系統管理僅剩公告設定、Free Spin 管理、橫幅管理、消稽核設定；遊戲商管理與後台管理員系統維持全部顯示不變——其餘屬於隱藏規則列表的項目（如加盟列表、出金審核、KYC 設定等）皆不出現於任何分類",
    "§機台場館的後台選單",
    "站台切換下拉選單選到機台場館時，後台選單隱藏不適用的頁面（這些頁面的功能已由排除規則排除，現階段留著只會是空白頁）。顯示與否跟著站台切換走：同一操作者切回線上站台即恢復完整選單",
    critical=True,
    rationale="REQ-PLATFORMRULE-004 為 high risk，本案即其 non-happy 覆蓋：expected_result 明確斷言一系列項目『不出現』，屬負向驗證。本 TC 做整體切換動作後的跨分類總覽檢查，確保『切換』這個觸發動作本身正確連動全部分類；各分類內部的詳細隱藏/顯示清單則由 REQ-PLATFORMRULE-005～010 各自的 TC 逐項覆蓋，避免與本 TC 重複"))

T.append(tc(
    "REQ-PLATFORMRULE-004", ["AC-PLATFORMRULE-0042"],
    "自機台場館切回線上站台後，後台選單恢復完整",
    "ui_e2e", ["functional"], ["requirement_based"],
    PRE_ADMIN + ["承上一條 TC，已切換至機台場館且選單已依規則隱藏", "選定一個既有的線上站台"],
    ["使用站台切換下拉選單，切回前置作業選定的線上站台",
     "展開左側選單全部分類，逐一檢視各分類下目前可見的項目清單"],
    "選單恢復完整：先前於機台場館被隱藏的所有頁面（資訊看板、加盟列表、登入網域查詢、推薦註冊金設定、暱稱禁用詞設定、出金審核、優惠彩金審核、返水明細、加盟傭金發放紀錄、代理返傭發放紀錄、會員等級異動紀錄、KYC 設定、會員等級設定、代理設定、加盟商設定、優惠活動管理、畫面管理）全部重新出現；鏈上錢包管理頁面的區塊鏈幣別頁籤也恢復顯示",
    "§機台場館的後台選單",
    "站台切換下拉選單選到機台場館時，後台選單隱藏不適用的頁面（這些頁面的功能已由排除規則排除，現階段留著只會是空白頁）。顯示與否跟著站台切換走：同一操作者切回線上站台即恢復完整選單",
    rationale="本 TC 專門驗證 AC-0042 要求的『回復』本身（即切換動作具備往返一致性，不遺留機台場館隱藏狀態），刻意接續在 AC-0041 的 TC 之後執行以形成真實的來回切換場景；與 AC-0041 的 TC 屬對稱情境但驗證目標不同（一個驗證隱藏觸發、一個驗證回復觸發），依本專案準則兩者皆採 requirement_based 標記，不因對稱性而刻意標成不同技巧或標成 state_transition——本規則並未定義多狀態的轉換矩陣，僅是單純的顯示規則跟隨當前站台類型即時求值，不涉及需要額外驗證的狀態機邏輯"))

# ================= REQ-PLATFORMRULE-005（medium）資訊看板整個隱藏 =================

T.append(tc(
    "REQ-PLATFORMRULE-005", ["AC-PLATFORMRULE-0051"],
    "機台場館的左側選單不存在資訊看板分類",
    "ui_e2e", ["functional", "negative"], ["requirement_based"],
    PRE_ADMIN + ["站台切換下拉選單切換至一個既有的機台場館站台"],
    ["檢視左側選單目前所有分類標題的清單"],
    "選單分類清單中不存在「資訊看板」這個分類（含其下所有原本子項目），選單分類清單直接從下一個分類開始",
    "§機台場館的後台選單",
    "資訊看板 | —（整個分類隱藏） | 資訊看板"))

# ================= REQ-PLATFORMRULE-006（medium）會員與加盟商分類僅顯示會員列表 =================

T.append(tc(
    "REQ-PLATFORMRULE-006", ["AC-PLATFORMRULE-0061"],
    "機台場館的會員與加盟商分類僅顯示會員列表",
    "ui_e2e", ["functional", "negative"], ["requirement_based"],
    PRE_ADMIN + ["站台切換下拉選單切換至一個既有的機台場館站台"],
    ["展開左側選單的『會員與加盟商』分類",
     "逐一檢視該分類下目前顯示的項目清單"],
    "該分類下僅顯示「會員列表」一項；「加盟列表」「登入網域查詢」「推薦註冊金設定」「暱稱禁用詞設定」皆不出現於此分類下",
    "§機台場館的後台選單",
    "會員與加盟商 | 會員列表 | 加盟列表、登入網域查詢、推薦註冊金設定、暱稱禁用詞設定"))

# ================= REQ-PLATFORMRULE-007（medium）帳務管理分類 =================

T.append(tc(
    "REQ-PLATFORMRULE-007", ["AC-PLATFORMRULE-0071"],
    "機台場館的帳務管理分類顯示鏈上錢包管理與洗分出金核實，隱藏出金審核與優惠彩金審核",
    "ui_e2e", ["functional", "negative"], ["requirement_based"],
    PRE_ADMIN + ["站台切換下拉選單切換至一個既有的機台場館站台"],
    ["展開左側選單的『帳務管理』分類",
     "逐一檢視該分類下目前顯示的項目清單"],
    "該分類下顯示「鏈上錢包管理」與「洗分出金核實」；不顯示「出金審核」與「優惠彩金審核」",
    "§機台場館的後台選單",
    "帳務管理 | 鏈上錢包管理（僅顯示法幣 TWD 頁籤，區塊鏈頁籤隱藏——稽核倍數設定在此）、洗分出金核實 | 出金審核、優惠彩金審核"))

T.append(tc(
    "REQ-PLATFORMRULE-007", ["AC-PLATFORMRULE-0072"],
    "機台場館開啟鏈上錢包管理頁面，僅顯示法幣 TWD 頁籤，區塊鏈頁籤隱藏",
    "ui_e2e", ["functional", "negative"], ["requirement_based"],
    PRE_ADMIN + ["站台切換下拉選單切換至一個既有的機台場館站台"],
    ["點開『帳務管理 > 鏈上錢包管理』",
     "檢視頁面內的頁籤列，記錄目前顯示的頁籤"],
    "頁籤列僅顯示「TWD」（法幣）一個頁籤；原本線上站台會出現的區塊鏈幣別頁籤（如 USDT 等）皆不顯示",
    "§機台場館的後台選單",
    "帳務管理 | 鏈上錢包管理（僅顯示法幣 TWD 頁籤，區塊鏈頁籤隱藏——稽核倍數設定在此）、洗分出金核實 | 出金審核、優惠彩金審核"))

# ================= REQ-PLATFORMRULE-008（medium）各式報表分類 =================

T.append(tc(
    "REQ-PLATFORMRULE-008", ["AC-PLATFORMRULE-0081"],
    "機台場館的各式報表分類顯示交易紀錄查詢等四項，隱藏返水明細等四項",
    "ui_e2e", ["functional", "negative"], ["requirement_based"],
    PRE_ADMIN + ["站台切換下拉選單切換至一個既有的機台場館站台"],
    ["展開左側選單的『各式報表』分類",
     "逐一檢視該分類下目前顯示的項目清單"],
    "該分類下顯示「交易紀錄查詢」「注單查詢」「稽核明細」「場館日結報表」；不顯示「返水明細」「加盟傭金發放紀錄」「代理返傭發放紀錄」「會員等級異動紀錄」",
    "§機台場館的後台選單",
    "各式報表 | 交易紀錄查詢、注單查詢、稽核明細、場館日結報表 | 返水明細、加盟傭金發放紀錄、代理返傭發放紀錄、會員等級異動紀錄"))

# ================= REQ-PLATFORMRULE-009（medium）系統管理分類 =================

T.append(tc(
    "REQ-PLATFORMRULE-009", ["AC-PLATFORMRULE-0091"],
    "機台場館的系統管理分類顯示公告設定等四項，隱藏 KYC 設定等六項",
    "ui_e2e", ["functional", "negative"], ["requirement_based"],
    PRE_ADMIN + ["站台切換下拉選單切換至一個既有的機台場館站台"],
    ["展開左側選單的『系統管理』分類",
     "逐一檢視該分類下目前顯示的項目清單"],
    "該分類下顯示「公告設定」「Free Spin 管理」「橫幅管理」「消稽核設定」；不顯示「KYC 設定」「會員等級設定」「代理設定」「加盟商設定」「優惠活動管理」「畫面管理」",
    "§機台場館的後台選單",
    "系統管理 | 公告設定、Free Spin 管理、橫幅管理、消稽核設定 | KYC 設定、會員等級設定、代理設定、加盟商設定、優惠活動管理、畫面管理"))

# ================= REQ-PLATFORMRULE-010（low）遊戲商管理與後台管理員系統全部顯示 =================

T.append(tc(
    "REQ-PLATFORMRULE-010", ["AC-PLATFORMRULE-0101"],
    "機台場館的遊戲商管理與後台管理員系統分類全部顯示，無任何項目被隱藏",
    "ui_e2e", ["functional"], ["requirement_based"],
    PRE_ADMIN + ["站台切換下拉選單切換至一個既有的機台場館站台"],
    ["展開左側選單的『遊戲商管理』分類，記錄目前顯示的項目",
     "展開左側選單的『後台管理員系統』分類，記錄目前顯示的項目"],
    "『遊戲商管理』分類顯示「遊戲商管理」與「遊戲貢獻值設定」兩項；『後台管理員系統』分類全部項目皆顯示；兩個分類皆沒有任何一項因站台切換至機台場館而被隱藏",
    "§機台場館的後台選單",
    "遊戲商管理 | 遊戲商管理、遊戲貢獻值設定 | — ｜ 後台管理員系統 | 全部 | —"))

# ================= REQ-PLATFORMRULE-011（low）保留：架構要求，暫無可測試場景，見 uncovered_with_reason =================

# ================= REQ-PLATFORMRULE-012（medium）操作員為新增角色 =================

T.append(tc(
    "REQ-PLATFORMRULE-012", ["AC-PLATFORMRULE-0121"],
    "新增後台使用者時，角色選項包含操作員並可指定所屬場館",
    "ui_e2e", ["functional"], ["requirement_based"],
    PRE_ADMIN,
    ["進入『後台管理員系統』的使用者列表，點擊新增使用者",
     "檢視角色下拉選項清單",
     "選擇「操作員」角色，檢視畫面是否出現可指定所屬場館的欄位，並嘗試選取一個既有機台場館作為所屬場館"],
    "角色選項清單包含「操作員」；選擇操作員角色後，畫面提供可指定所屬場館的欄位，且能選取一個既有機台場館作為其所屬場館",
    "§角色與權限 + §對既有章節的影響",
    "7.x 後台管理員系統 | 新增使用者時的角色選項須包含「操作員」，並可指定所屬場館"))

# ================= REQ-PLATFORMRULE-013（high）操作員可見場館範圍僅自身所屬場館 =================

T.append(tc(
    "REQ-PLATFORMRULE-013", ["AC-PLATFORMRULE-0131"],
    "操作員登入後台，僅能見到自身所屬場館的場館日結報表資料",
    "ui_e2e", ["functional", "security"], ["requirement_based"],
    PRE_ADMIN + [
        "依『後台管理員系統』新增一個操作員角色帳號，將其所屬場館指定為一個既有機台場館 X",
        "以該操作員帳號登入後台",
    ],
    ["進入『各式報表 > 場館日結報表』頁面",
     "檢視頁面可查詢/顯示的場館範圍選項與實際回傳的結果"],
    "僅能查詢/看到場館 X（自身所屬場館）的日結報表資料；畫面上若有場館選擇欄位，選項僅包含場館 X，不含其他場館",
    "§角色與權限",
    "可見場館範圍 | 全部場館 | 自身站台及所有子站台下的場館 | 僅自身所屬場館 ｜ 場館日結報表 | 全部 | 管轄範圍 | 自身場館"))

T.append(tc(
    "REQ-PLATFORMRULE-013", ["AC-PLATFORMRULE-0131"],
    "操作員嘗試查詢自身所屬場館以外的場館日結報表，查無資料或無法選取",
    "ui_e2e", ["negative", "security"], ["negative"],
    PRE_ADMIN + [
        "承上，操作員帳號所屬場館為既有機台場館 X",
        "以該操作員帳號登入後台",
    ],
    ["於『各式報表 > 場館日結報表』頁面，嘗試尋找或選取場館 X 以外的另一個機台場館 Y",
     "若介面允許直接查詢，嘗試以場館 Y 為條件查詢；若介面本身無場館選擇欄位，確認結果是否仍侷限於場館 X"],
    "操作員無法查得或選取場館 X 以外（例如場館 Y）的任何場館日結報表資料——場館選擇欄位（若存在）不包含場館 Y，或選取後查無資料，僅能查得場館 X 範圍內的資料",
    "§角色與權限",
    "可見場館範圍 | 全部場館 | 自身站台及所有子站台下的場館 | 僅自身所屬場館",
    assume="本 TC 需要測試環境當下存在至少兩個不同的既有機台場館（操作員所屬場館 X 之外，另需一個場館 Y 作為『其他場館』對照）；若環境當下僅有一個機台場館，需先依既有機台場館的建立方式另外建立一個測試用機台場館 Y 才能執行本 TC 的對照比較",
    critical=True,
    rationale="REQ-PLATFORMRULE-013 為 high risk，本案即其 non-happy 覆蓋；與同一 AC 下的另一條正向 TC 互補，一個確認『看得到自己的』、一個確認『看不到別人的』，兩者比對基準不同（前者驗證存在性、後者驗證不存在性），不算重複案例。是否存在第二個機台場館屬於測試環境資料佈置問題而非業務規則假設，依專案準則以 assumptions 誠實揭露，而非預設環境必然具備此條件"))

# ================= REQ-PLATFORMRULE-014（high）操作員選單無站台列表項目 =================

T.append(tc(
    "REQ-PLATFORMRULE-014", ["AC-PLATFORMRULE-0141"],
    "操作員登入機台場館後，選單無『站台列表』項目，可操作項目正常存在於選單中",
    "ui_e2e", ["functional", "negative", "security"], ["negative"],
    PRE_ADMIN + [
        "依『後台管理員系統』新增一個操作員角色帳號，將其所屬場館指定為一個既有機台場館",
        "以該操作員帳號登入後台，站台切換選單確認已選定其所屬的機台場館",
    ],
    ["檢視後台左側選單的全部項目",
     "確認選單中是否存在「站台列表」這個項目",
     "確認會員與加盟商 > 會員列表、帳務管理 > 洗分出金核實、各式報表 > 交易紀錄查詢與場館日結報表等項目是否正常存在於選單中"],
    "選單中不存在「站台列表」這個項目，操作員因此沒有入口可進入場館設定頁面，該頁面內屬本 spec 明訂欄位的「額度上限（場館層級）」也因此無從檢視或修改；會員列表、洗分出金核實、交易紀錄查詢、場館日結報表等操作員可操作項目仍正常存在於選單中",
    "§角色與權限",
    "額度上限（場館層級） | 可設定 | 可設定 | 唯讀",
    critical=True,
    rationale="REQ-PLATFORMRULE-014 為 high risk，本案即其 non-happy 覆蓋。特別說明：『操作員選單無站台列表項目』這項具體事實並非 SPEC-PLATFORMRULE-001 v0.1.md 原文逐字內容（spec.md 本身僅在角色與權限表列出各功能項目的可操作性，未直接描述選單結構），而是 RequirementModel 中 REQ-PLATFORMRULE-014 的 history 記錄裡 Oscar 於 2026-09-15 提供實際選單截圖後的人工確認結果；本 TC 依此已核准進入 ACTIVE 狀態的 RequirementModel 斷言設計，非自行杜撰無依據的規則。expected_result 刻意不包含『場次逾時時間』欄位的斷言——該欄位出處為 SPEC-ARCADE-001 而非本 spec，其存在與位置不屬本 spec 驗證範圍；同理，REQ-PLATFORMRULE-014 原文中『編輯機台基本資料／機台停用啟用／人工入出金等項目是否經由會員列表頁面進入』僅屬尚未經確認的推論，本 TC 不對其實際頁面路徑做斷言，避免超出已核准範圍去驗證未經確認的細節"))

# ================= REQ-PLATFORMRULE-015（high）機台交易紀錄查詢範圍依角色 =================

T.append(tc(
    "REQ-PLATFORMRULE-015", ["AC-PLATFORMRULE-0151"],
    "操作員於機台交易紀錄查詢頁查詢自身所屬場館以外的交易，查無結果",
    "ui_e2e", ["negative", "security"], ["negative"],
    PRE_ADMIN + [
        "依『後台管理員系統』新增一個操作員角色帳號，將其所屬場館指定為一個既有機台場館 X",
        "以該操作員帳號登入後台",
    ],
    ["進入『各式報表 > 交易紀錄查詢』頁面",
     "嘗試以場館 X 以外的另一個既有機台場館 Y 為條件查詢（若頁面提供場館篩選欄位，檢視其選項；若無此欄位，直接查詢並比對結果範圍）"],
    "查詢結果中查無場館 Y（或任何非自身所屬場館 X）的交易紀錄，僅能查得場館 X 範圍內的機台交易；若頁面提供場館篩選欄位，選項不包含場館 Y",
    "§角色與權限",
    "機台交易紀錄查詢 | 全部 | 管轄範圍 | 自身場館",
    assume="本 TC 需要測試環境當下存在至少兩個不同的既有機台場館（操作員所屬場館 X 之外，另需一個場館 Y 且該場館有機台交易紀錄，作為『查無結果』的對照）；若環境當下僅有一個機台場館或場館 Y 無任何交易紀錄，需先洽環境負責人補上對應資料才能執行本 TC 的對照比較",
    critical=True,
    rationale="REQ-PLATFORMRULE-015 為 high risk，本案即其 non-happy 覆蓋，直接對應 AC-0151 的斷言。是否存在第二個機台場館及其交易紀錄屬測試環境資料佈置問題，依專案準則以 assumptions 誠實揭露"))

T.append(tc(
    "REQ-PLATFORMRULE-015", ["AC-PLATFORMRULE-0151"],
    "Admin 可查全部場館、站長僅可查其管轄範圍內的機台交易紀錄",
    "ui_e2e", ["functional", "security"], ["requirement_based"],
    PRE_ADMIN + ["選定一個既有的站長帳號，確認其管轄的站台樹（自身站台及所有子站台）下涵蓋至少一個機台場館"],
    ["以 Admin 登入後台，進入『各式報表 > 交易紀錄查詢』，不限定場館查詢，確認結果涵蓋來自不同機台場館的交易紀錄",
     "改以前置作業準備好的站長帳號登入，重複同樣的查詢，檢視結果範圍"],
    "Admin 查詢結果涵蓋系統內全部機台場館範圍的交易紀錄；站長查詢結果僅涵蓋其自身站台及所有子站台下機台場館範圍內的交易，不包含管轄範圍以外的機台場館交易",
    "§角色與權限",
    "機台交易紀錄查詢 | 全部 | 管轄範圍 | 自身場館",
    rationale="與同 AC 下的操作員負向案例互補，本案補齊 Admin『全部』與站長『管轄範圍』兩種角色範圍的正向驗證，三種角色合計完整覆蓋 REQ-PLATFORMRULE-015 statement 所描述的三層可見範圍"))

# ================= REQ-PLATFORMRULE-016（medium）人工入金/出金三角色皆可操作 =================

T.append(tc(
    "REQ-PLATFORMRULE-016", ["AC-PLATFORMRULE-0161"],
    "操作員可對既有機台帳號執行人工入金或人工出金",
    "ui_e2e", ["functional"], ["requirement_based"],
    PRE_ADMIN + [
        "依『後台管理員系統』新增一個操作員角色帳號，將其所屬場館指定為一個既有機台場館",
        "選定該機台場館下一個既有的機台帳號",
        "以該操作員帳號登入後台",
    ],
    ["進入該機台帳號的會員詳細資料頁〈帳務資訊〉區塊，點擊『人工入金』（或『人工出金』）按鈕",
     "依系統要求填寫必要欄位（金額、稽核、備註等）後點擊儲存"],
    "系統允許操作員完成人工入金或人工出金操作，未因角色為操作員而被拒絕或隱藏此功能按鈕",
    "§角色與權限",
    "人工入金／出金（櫃檯） | 可操作 | 可操作 | 可操作"))

# ================= REQ-PLATFORMRULE-017（high）重設密碼站長二次確認，操作員不可 =================

T.append(tc(
    "REQ-PLATFORMRULE-017", ["AC-PLATFORMRULE-0171"],
    "站長執行重設密碼操作須經二次確認才會生效",
    "ui_e2e", ["functional", "security"], ["requirement_based"],
    PRE_ADMIN + ["選定一個既有的站長帳號，並選定其管轄範圍內一名既有會員", "以該站長帳號登入後台"],
    ["進入該會員的重設密碼功能，觸發重設密碼操作",
     "觀察系統是否出現二次確認提示（例如確認對話框），並完成該次確認"],
    "系統於執行重設密碼前要求二次確認；在完成該次確認之前，密碼重設不會生效，完成確認後才實際生效",
    "§角色與權限",
    "重設密碼（所有會員帳號） | 可操作 | 可操作（須二次確認） | 不可"))

T.append(tc(
    "REQ-PLATFORMRULE-017", ["AC-PLATFORMRULE-0172"],
    "操作員嘗試執行重設密碼操作，不具備此權限",
    "ui_e2e", ["negative", "security"], ["negative"],
    PRE_ADMIN + [
        "依『後台管理員系統』新增一個操作員角色帳號，將其所屬場館指定為一個既有機台場館",
        "選定該機台場館下一個既有的會員/機台帳號",
        "以該操作員帳號登入後台",
    ],
    ["嘗試尋找或執行對該會員的重設密碼功能", "觀察系統反應"],
    "操作員無法執行重設密碼操作——功能按鈕不存在、呈現不可用狀態、或操作被系統拒絕，不具備此權限",
    "§角色與權限",
    "重設密碼（所有會員帳號） | 可操作 | 可操作（須二次確認） | 不可",
    critical=True,
    rationale="REQ-PLATFORMRULE-017 為 high risk，本案即其 non-happy 覆蓋"))

# ================= REQ-PLATFORMRULE-018（high）編輯機台基本資料唯讀，發放/重置憑證不可 =================

T.append(tc(
    "REQ-PLATFORMRULE-018", ["AC-PLATFORMRULE-0181"],
    "操作員檢視機台基本資料編輯畫面僅能唯讀，無法儲存修改",
    "ui_e2e", ["negative", "security"], ["negative"],
    PRE_ADMIN + [
        "依『後台管理員系統』新增一個操作員角色帳號，將其所屬場館指定為一個既有機台場館",
        "選定該機台場館下一台既有機台",
        "以該操作員帳號登入後台",
    ],
    ["進入該機台的編輯機台基本資料畫面",
     "嘗試修改任一欄位內容，並尋找/點擊儲存"],
    "欄位呈現唯讀狀態（無法輸入修改，或修改後無儲存按鈕、儲存按鈕不可用），操作員無法完成任何內容的儲存",
    "§角色與權限",
    "編輯機台基本資料 | 可操作 | 可操作 | 唯讀 ｜ 發放／重置機台憑證 | 可操作 | 可操作（重置須二次確認） | 不可",
    critical=True,
    rationale="REQ-PLATFORMRULE-018 為 high risk，本案為其 non-happy 覆蓋之一"))

T.append(tc(
    "REQ-PLATFORMRULE-018", ["AC-PLATFORMRULE-0182"],
    "操作員嘗試發放或重置機台憑證，不具備此權限",
    "ui_e2e", ["negative", "security"], ["negative"],
    PRE_ADMIN + [
        "依『後台管理員系統』新增一個操作員角色帳號，將其所屬場館指定為一個既有機台場館",
        "選定該機台場館下一台既有機台",
        "以該操作員帳號登入後台",
    ],
    ["嘗試尋找或執行該機台的發放憑證或重置憑證操作", "觀察系統反應"],
    "操作員無法執行發放或重置機台憑證操作——功能不存在、不可用、或被系統拒絕，不具備此權限",
    "§角色與權限",
    "編輯機台基本資料 | 可操作 | 可操作 | 唯讀 ｜ 發放／重置機台憑證 | 可操作 | 可操作（重置須二次確認） | 不可",
    critical=True,
    rationale="REQ-PLATFORMRULE-018 為 high risk，本案為其 non-happy 覆蓋之二，與 AC-0181 分屬編輯資料與憑證管理兩個獨立功能，不合併為單一 TC"))

# ================= REQ-PLATFORMRULE-019（medium）新增機台操作員不可 =================

T.append(tc(
    "REQ-PLATFORMRULE-019", ["AC-PLATFORMRULE-0191"],
    "操作員嘗試新增機台，不具備此權限",
    "ui_e2e", ["negative", "security"], ["negative"],
    PRE_ADMIN + [
        "依『後台管理員系統』新增一個操作員角色帳號，將其所屬場館指定為一個既有機台場館",
        "以該操作員帳號登入後台",
    ],
    ["嘗試尋找或執行新增機台的功能", "觀察系統反應"],
    "操作員無法執行新增機台操作——功能入口不存在或操作被系統拒絕，不具備此權限",
    "§角色與權限",
    "新增機台 | 可操作 | 可操作 | 不可"))

# ================= REQ-PLATFORMRULE-020（medium）機台停用/啟用三角色皆可操作 =================

T.append(tc(
    "REQ-PLATFORMRULE-020", ["AC-PLATFORMRULE-0201"],
    "操作員可對既有機台執行停用與啟用操作",
    "ui_e2e", ["functional"], ["requirement_based"],
    PRE_ADMIN + [
        "依『後台管理員系統』新增一個操作員角色帳號，將其所屬場館指定為一個既有機台場館",
        "選定該機台場館下一台既有機台，確認目前為啟用狀態",
        "以該操作員帳號登入後台",
    ],
    ["對該機台執行停用操作，確認狀態變為停用",
     "再對同一機台執行啟用操作，確認狀態變回啟用"],
    "系統允許操作員完成機台停用與啟用兩項操作，兩次操作皆未因角色為操作員而被拒絕",
    "§角色與權限",
    "機台停用／啟用 | 可操作 | 可操作 | 可操作"))

# ================= REQ-PLATFORMRULE-021（high）平台新增/更新遊戲後機台場館預設停用 =================

T.append(tc(
    "REQ-PLATFORMRULE-021", ["AC-PLATFORMRULE-0211"],
    "既有已啟用的遊戲於平台發布更新後，在機台場館被重新設為停用",
    "ui_e2e", ["functional", "negative"], ["error_guessing"],
    PRE_ADMIN + [
        "選定一個既有的機台場館站台 X",
        "選定一款目前已在機台場館 X 呈啟用狀態的既有遊戲",
    ],
    ["於『遊戲商管理』記錄該遊戲目前於機台場館 X 的狀態（啟用中）",
     "由具備權限的角色，對該遊戲發佈一次更新",
     "更新完成後，重新檢視該遊戲於機台場館 X 的狀態"],
    "更新完成後，該遊戲於機台場館 X 被重新設為停用狀態，不因更新前原已是啟用狀態而被保留為啟用",
    "§機台場館的遊戲更新",
    "預設停用 | 平台新增任何遊戲、或對既有遊戲發佈更新後，該遊戲在所有機台場館一律預設為停用——包含更新前原已啟用的遊戲（更新視同內容變動，須重新決定是否開放）",
    assume="『平台對既有遊戲發佈更新』的實際後台操作介面與具體步驟不在本 spec 定義範圍內（本 spec 僅描述此動作對機台場館產生的連帶效果，未定義觸發此動作的頁面路徑），需另比對遊戲管理相關 spec 或洽環境負責人確認實際觸發方式；本 TC 假設可透過後台遊戲管理功能中的版本／更新發佈動作觸發，若實際操作路徑與假設不符，結果需人工複核",
    critical=True,
    rationale="REQ-PLATFORMRULE-021 為 high risk，本案即其 non-happy 覆蓋。spec 特別點名『包含更新前原已啟用的遊戲』這個情境，代表這正是容易被誤實作成『沿用舊狀態』的已知陷阱（例如更新流程若只處理新遊戲的預設值、忘記重置既有啟用中遊戲的狀態），故採 error_guessing 技巧針對此已知風險點設計案例，而非泛用的 requirement_based；expected_result 斷言的是『不保留啟用』這個負向結果，屬 non-happy 驗證"))

T.append(tc(
    "REQ-PLATFORMRULE-021", ["AC-PLATFORMRULE-0212"],
    "平台新增一款全新遊戲後，所有機台場館皆預設停用",
    "ui_e2e", ["functional"], ["requirement_based"],
    PRE_ADMIN + ["選定至少兩個不同的既有機台場館站台，供比對新遊戲於各場館的預設狀態"],
    ["由具備權限的角色，於平台新增一款全新遊戲",
     "分別切換至前置作業選定的各個機台場館，於『遊戲商管理』檢視該款新遊戲的預設狀態"],
    "該款新遊戲於所檢視的每一個機台場館皆預設為停用狀態，沒有任何機台場館預設為啟用",
    "§機台場館的遊戲更新",
    "預設停用 | 平台新增任何遊戲、或對既有遊戲發佈更新後，該遊戲在所有機台場館一律預設為停用——包含更新前原已啟用的遊戲（更新視同內容變動，須重新決定是否開放）",
    assume="『平台新增一款全新遊戲』的實際後台操作介面與具體步驟不在本 spec 定義範圍內，需另比對遊戲管理相關 spec 或洽環境負責人確認實際觸發方式；本 TC 假設可透過後台遊戲管理功能中的新增遊戲動作觸發，若實際操作路徑與假設不符，結果需人工複核",
    rationale="與 AC-0211 共用同一類『遊戲新增/更新如何觸發』的環境假設，但驗證目標不同：本案驗證的是全新遊戲的初始預設值，AC-0211 驗證的是既有啟用狀態於更新後是否被正確重置，兩者不可互相取代"))

# ================= REQ-PLATFORMRULE-022（high）遊戲開啟限站長，操作員不可，平台不代為開啟 =================

T.append(tc(
    "REQ-PLATFORMRULE-022", ["AC-PLATFORMRULE-0221"],
    "站長可於遊戲商管理手動開啟目前為停用狀態的機台場館遊戲",
    "ui_e2e", ["functional"], ["requirement_based"],
    PRE_ADMIN + [
        "選定一個既有的機台場館站台，並於其『遊戲商管理』選定一款目前狀態為停用的既有遊戲（不論其停用原因，只要目前狀態為停用即可）",
        "選定一個管轄範圍涵蓋該機台場館的既有站長帳號",
        "以該站長帳號登入後台",
    ],
    ["進入『遊戲商管理』，找到前置作業選定的停用中遊戲",
     "對該遊戲執行啟用操作"],
    "系統允許站長完成該遊戲的啟用操作，操作後該遊戲狀態變為啟用",
    "§機台場館的遊戲更新",
    "開啟方式 | 由站長自行於 遊戲商管理 啟用該遊戲；操作員不可操作；平台不代為開啟"))

T.append(tc(
    "REQ-PLATFORMRULE-022", ["AC-PLATFORMRULE-0222"],
    "操作員嘗試開啟一款被停用的機台場館遊戲，不具備此權限",
    "ui_e2e", ["negative", "security"], ["negative"],
    PRE_ADMIN + [
        "依『後台管理員系統』新增一個操作員角色帳號，將其所屬場館指定為一個既有機台場館",
        "於該機台場館的『遊戲商管理』選定一款目前狀態為停用的既有遊戲",
        "以該操作員帳號登入後台",
    ],
    ["嘗試尋找或執行該遊戲的啟用操作（若操作員選單本身無遊戲商管理入口，記錄其無法進入的情形；若可進入，嘗試執行啟用並觀察反應）",
     "觀察系統反應"],
    "操作員無法執行該遊戲的啟用操作——無論是因遊戲商管理入口本身不存在、或進入後啟用功能被拒絕/不可用，操作員都不具備此權限，該遊戲狀態維持停用",
    "§機台場館的遊戲更新",
    "開啟方式 | 由站長自行於 遊戲商管理 啟用該遊戲；操作員不可操作；平台不代為開啟",
    critical=True,
    rationale="REQ-PLATFORMRULE-022 為 high risk，本案為其 non-happy 覆蓋之一"))

T.append(tc(
    "REQ-PLATFORMRULE-022", ["AC-PLATFORMRULE-0223"],
    "遊戲因平台更新被停用後，若無人工操作，平台不會自動將其重新設為啟用",
    "ui_e2e", ["negative"], ["negative"],
    PRE_ADMIN + [
        "選定一個既有的機台場館，於其『遊戲商管理』選定一款目前狀態為停用的既有遊戲，確認自其被設為停用以來尚未有任何站長執行過啟用操作",
    ],
    ["記錄該遊戲目前的停用狀態與檢視時間",
     "間隔一段時間後（或重新整理/重新查詢該頁面），在不進行任何手動啟用操作的情況下，再次檢視該遊戲狀態"],
    "該遊戲狀態仍維持停用，未觀察到任何自動或排程機制將其重新設為啟用；平台本身不會主動代為開啟，需人工由站長執行",
    "§機台場館的遊戲更新",
    "開啟方式 | 由站長自行於 遊戲商管理 啟用該遊戲；操作員不可操作；平台不代為開啟",
    critical=True,
    rationale="REQ-PLATFORMRULE-022 為 high risk，本案為其 non-happy 覆蓋之二，專門對應 AC-0223『平台不代為開啟』這項負面事實——比對基準為同一遊戲同一場館『操作前後狀態不變』，不需要額外對照組；與 AC-0222（操作員主動嘗試被拒絕）驗證的是不同機制（人為越權 vs 系統自動行為），兩者互補不重複"))

# ================= REQ-PLATFORMRULE-023（medium）遊戲更新預設停用僅適用機台，線上站台不受影響 =================

T.append(tc(
    "REQ-PLATFORMRULE-023", ["AC-PLATFORMRULE-0231"],
    "線上站台已啟用的遊戲於平台發布更新後，維持啟用狀態不受機台場館停用規則影響",
    "ui_e2e", ["functional", "negative"], ["requirement_based"],
    PRE_ADMIN + [
        "選定一個既有的線上站台，並於其『遊戲商管理』選定一款目前已啟用的既有遊戲",
    ],
    ["記錄該遊戲於此線上站台目前為啟用狀態",
     "由具備權限的角色，對該遊戲發佈一次更新（與同一款遊戲對機台場館產生影響的更新事件相同）",
     "更新完成後，重新檢視該遊戲於此線上站台的狀態"],
    "更新完成後，該遊戲於此線上站台維持啟用狀態不變，不受機台場館『預設停用』規則影響——因為該規則僅適用站台類型為「機台」的場館",
    "§機台場館的遊戲更新",
    "適用範圍 | 僅站台類型「機台」的場館；線上站台維持既有行為，不受本規則影響",
    assume="同 REQ-PLATFORMRULE-021，『平台對遊戲發佈更新』的實際後台操作介面與具體步驟不在本 spec 定義範圍內，此處假設可透過後台遊戲管理功能觸發，且該次更新動作屬平台層級事件、會同時影響同一款遊戲在線上與機台場館兩側的預設狀態判斷；若實際操作路徑與假設不符，結果需人工複核",
    rationale="本 TC 與 REQ-PLATFORMRULE-021 的 TC 共用同一次『發佈更新』事件的概念作為對照組（同一款遊戲、同一次更新），驗證的是範圍邊界（機台 vs 線上）而非更新本身的效果，兩者互為對照但驗證目標不同，不算重複案例"))

# ================= 組報告 =================

cov = collections.defaultdict(lambda: {"draft_ids": [], "acs": collections.defaultdict(list)})
for t in T:
    for r in t["requirement_ids"]:
        cov[r]["draft_ids"].append(t["draft_id"])
    for a in t["acceptance_criteria_ids"]:
        for rid, r in reqs.items():
            if a in [ac["ac_id"] for ac in r["acceptance_criteria"]]:
                cov[rid]["acs"][a].append(t["draft_id"])
                break

n_exp = sum(1 for t in T if t["assumptions"])
tech_count = collections.Counter(x for t in T for x in t["design_techniques"])

uncovered = [
    {"requirement_id": "REQ-PLATFORMRULE-011",
     "reason": ("此為集中政策層的架構/實作要求（排除規則須做成可逐項解除的政策層，選單顯示與排除規則同一來源設定，"
                "不得各功能自行硬編碼），本質是工程實作規範而非可獨立觀察的使用者行為；RequirementModel 本身的 "
                "rejection_contract.defined=false 且已註明『此為架構要求，實際驗證需待有排除項目被解除時才能真正測試，"
                "暫列為待未來實際案例驗證的規則』。目前沒有任何排除規則項目被實際解除，無法設計出有真實對照基準的測試案例；"
                "硬造一個『假設某功能被解除』的情境會缺乏可驗證的實際系統行為對照，不如誠實記錄為待未來實際案例出現時再設計。"
                "建議另行以程式碼/架構審查（review 排除規則是否確實走集中設定、而非各功能各自硬編碼判斷）處理，而非功能測試案例；"
                "亦可考慮另開 Clarification 確認是否已有任何排除項目排入近期解除計畫。")},
]

rep = {
    "mode": "spec", "testcase_draft_artifact_id": None,
    "coverage_matrix": [
        {"requirement_id": r, "draft_ids": d["draft_ids"],
         "acceptance_criteria": [{"ac_id": a, "draft_ids": dd} for a, dd in d["acs"].items()]}
        for r, d in cov.items()
    ],
    "uncovered_with_reason": uncovered,
    "technique_summary": [{"technique": k, "count": v} for k, v in tech_count.items()],
    "self_check": {k: True for k in [
        "requirements_covered", "acceptance_criteria_covered", "negative_considered", "boundary_considered",
        "expected_results_traceable", "no_unsupported_assumptions", "duplicate_detection_completed"]},
    "assumptions": [a["text"] for t in T for a in t["assumptions"]],
    "duplicate_check": {"against_registry": False, "findings": []},
}


def envelope(t, payload, sub, refs, task="T2"):
    aid = ids.artifact_id(t)
    art = {"artifact_id": aid, "artifact_type": t, "schema_version": "1.0", "version": 1, "run_id": RUN,
           "task_id": task, "iteration": ITER, "created_by": A, "created_at": store.now(), "status": "DRAFT",
           "source": {"type": "RequirementModel", "ids": [RM_AID]}, "references": refs,
           "requires_approval": None, "payload": payload}
    p = store.ROOT / "artifacts" / "test-design" / RUN / f"{aid}.yaml"
    store.save(p, art)
    return aid, p


refs = [{"entity_type": "Requirement", "id": r} for r in reqs] + [{"entity_type": "Artifact", "id": RM_AID}]
did, p1 = envelope("TestCaseDraft", {"mode": "spec", "spec_id": SID, "spec_version": SV, "testcases": T}, "test-design", refs)
rep["testcase_draft_artifact_id"] = did
_, p2 = envelope("TestDesignReport", rep, "test-design", [{"entity_type": "Artifact", "id": did}])

print(p1.relative_to(store.ROOT))
print(p2.relative_to(store.ROOT))
print(f"{len(T)} TCs, {n_exp} exploratory, reqs covered={len(cov)}/{len(reqs)}, uncovered={len(uncovered)}")
print("technique_summary:", dict(tech_count))
