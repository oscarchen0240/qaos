#!/usr/bin/env python3
"""T1：Spec Analyst 對 SPEC-BONUSCCY-001 v1.0（17 給 QA 的說明：系統記帳幣別改為每站自訂）產出 SpecAnalysis + RequirementModel。
這份文件是「給 QA 的變更說明」，不是逐頁 UI spec，講的是「系統幣別（記帳基準）從全平台寫死 USDT，
改成每個站台開站時自訂 core_currency，機台站台用 TWD、線上站台維持 USDT」這個架構變更，
影響 21 處原本寫死 USDT 的地方，本檔按其「實際被改到的地方」表格逐項比對既有六份已測 spec 後發現：
- 「誰決定/可以改嗎/依站台類型過濾清單」已由 SPEC-SITELIST-001（REQ-004/008/009/010）完整驗證，不重複
- 「後台鏈上錢包管理僅顯示法幣TWD頁籤」已由 SPEC-PLATFORMRULE-001（REQ-007）驗證，不重複
- 「開站流程建站時寫入核心貨幣」與「機台帳號幣別取自核心貨幣」已由 SITELIST 與 SPEC-ACCOUNT-001（REQ-026）驗證，不重複
- 「發獎勵進站台核心貨幣錢包」是逐紅利類型的詳細規則，屬於 SPEC-BONUSCCY-002（18 紅利幣別盤點）的範圍，本檔只提一句話帶過，
  本次刻意不重複測試，留給 BONUSCCY-002 逐條覆蓋
- 「新玩家註冊初始錢包依核心貨幣」對機台帳號已由 ACCOUNT-026 驗證；對線上帳號因「現有線上站台全部維持USDT，
  不受本次改動影響」（本檔原文），目前沒有任何非 USDT 的線上站台可供測試，暫不可測，本次不寫成確定 Requirement
只測真正未被覆蓋、且本次改動有明確規則陳述的範圍：注單查詢頁金額顯示、後台查詢(會員列表/Dashboard)JOIN條件正確性、
人工出入金預設幣別、核心貨幣必須是啟用幣別的防呆、機台前台資產列表僅列核心貨幣。
「搬站／改站台類型不得讓幣別與站台脫節」原文只有一句結論、沒有具體重現情境與畫面描述，另開 Clarification 確認後再補。"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids
RUN = sys.argv[1]; SID, SV, A = "SPEC-BONUSCCY-001", "1.0", "agent-spec-analyst"
AREA = "BONUSCCY"
spec = store.load(store.spec_dir(SID) / "spec.yaml"); H = spec["versions"][0]["content_hash"]
def sr(loc, q=""): return {"spec_id": SID, "spec_version": SV, "location": loc, "quote": q[:300]}
def rc_true(desc, loc): return {"defined": True, "description": desc, "spec_reference": sr(loc)}

def req(title, stmt, typ, kind, loc, quote, acs, risk, rc, inputs=None, states=None, amb=None):
    rid = ids.alloc("REQ", AREA)
    r = {"requirement_id": rid, "version": 1, "spec_id": SID, "spec_version": SV, "type": typ, "title": title, "statement": stmt,
         "acceptance_criteria": [{"ac_id": ids.alloc("AC", AREA), "given": g, "when": w, "then": t} for (g, w, t) in acs],
         "spec_reference": sr(loc, quote), "ambiguity": amb, "risk": risk, "status": "DRAFT", "history": [], "behavior_kind": kind, "rejection_contract": rc}
    if inputs: r["inputs"] = inputs
    if states: r["states"] = states
    return r

reqs = [
 req("注單查詢/明細頁的金額欄位以站台核心貨幣顯示", "機台站台（TWD核心貨幣）的注單三層金額（game_bet_log → wallet_reference → system_wallet_reference）第三層的幣別與換算已改依站台核心貨幣；後台注單查詢/明細頁的金額欄位應對應顯示核心貨幣，不是寫死的 USDT", "functional", "success",
     "§實際被改到的地方（表格第2項：注單三層金額）", "注單三層金額 | game_bet_log → …_wallet_reference → …_system_wallet_reference，第三層的幣別與換算改依站台核心貨幣",
     [("一筆機台（TWD核心貨幣站台）的注單", "檢視後台注單查詢/明細頁的金額欄位", "金額以站台核心貨幣（TWD）顯示，不是寫死顯示 USDT 或其換算值")],
     "medium", rc_true("規則已明確定義；日結報表層級的核心貨幣計算已由 SPEC-DAILYREPORT-001 REQ-013 驗證，本條測的是注單查詢/明細頁本身，過去未被任何 spec 測過", "§實際被改到的地方")),
 req("會員列表與 Dashboard 總會員數正確涵蓋機台（TWD）站台會員", "後台查詢頁（會員列表、Dashboard 總會員數等）原本的 JOIN 條件比對寫死的 USDT 常數，已改為依站台核心貨幣查詢；機台（TWD核心貨幣）站台的會員應正確被涵蓋，不因舊有寫死的比對條件而被排除或漏計", "functional", "success",
     "§實際被改到的地方（表格第3項：後台查詢）", "後台查詢 | 注單列表與明細、返水明細、營運日報、會員列表、Dashboard 總會員數 —— 這些的 JOIN 條件原本比對常數",
     [("機台（TWD核心貨幣）站台底下已有會員", "檢視 Dashboard 總會員數統計", "這些會員正確計入總會員數，不因原本寫死 USDT 的 JOIN 條件而被排除"),
      ("站台切換選單切至機台（TWD）站台", "檢視會員列表", "正確列出該站台會員，不因幣別相關的查詢條件而遺漏資料")],
     "high", rc_true("規則已明確定義，屬於這次架構變更的核心回歸風險——若 JOIN 條件沒改乾淨，機台站台的資料會在報表/列表裡悄悄消失而不是報錯，風險標 high", "§實際被改到的地方")),
 req("人工存入／人工提出未指定幣別時，預設寫入站台核心貨幣", "人工出入金四支功能原本沒有明確寫入幣別（靠資料表 DEFAULT 或寫死 USDT），已改為取站台核心貨幣；對機台（TWD核心貨幣）帳號執行人工存入/提出且未指定幣別時，應寫入/扣除該站台的核心貨幣（TWD）", "functional", "success",
     "§實際被改到的地方（表格第6項：人工出入金）", "人工出入金 | 四支原本沒有明確寫入幣別（靠資料表 DEFAULT 或填死 USDT），改成取核心貨幣",
     [("對一個機台（TWD核心貨幣）帳號執行人工存入，未指定幣別", "檢視入帳結果", "金額寫入該站台核心貨幣（TWD）錢包，不是寫死的 USDT"),
      ("對同一機台帳號執行人工提出，未指定幣別", "檢視扣款結果", "從該站台核心貨幣（TWD）錢包扣除，不是寫死的 USDT")],
     "high", rc_true("規則已明確定義，直接關係金流正確性——若預設幣別沒改乾淨，錢會進錯錢包或找不到對應餘額扣款", "§實際被改到的地方")),
 req("站台核心貨幣僅能設定為目前已啟用中的錢包幣別", "站台的核心貨幣（系統幣別）必須是啟用中的錢包幣別之一（wallet_currency.enabled=1），否則獎勵會發到玩家看不到的錢包；設定核心貨幣時若選擇未啟用的幣別，系統應阻擋", "constraint", "rejection",
     "§一句話（限制段落）", "一個限制：站台的系統幣別必須是啟用中的錢包幣別之一（wallet_currency.enabled = 1），否則獎勵會發到玩家看不到的錢包",
     [("建立或編輯站台時，嘗試將核心貨幣設定為目前未啟用的錢包幣別", "送出設定", "系統阻擋，不允許設定為非啟用中的幣別")],
     "medium", rc_true("規則已明確定義是限制條件本身；具體的錯誤訊息文案本檔未給，若畫面實際文案與預期不符不算違反本條，只測「是否被阻擋」這個行為本身", "§一句話")),
 req("機台站台的前台資產列表僅顯示核心貨幣，不列出其他幣別的零餘額項目", "機台（TWD核心貨幣）站台玩家只有 TWD 一種錢包；前台資產列表只列核心貨幣（TWD），不再像以前那樣列出一排餘額 0 的其他幣別", "constraint", "success",
     "§⭐兩種站台差很多 + 實際被改到的地方（表格第8項）", "前台資產列表 | 只列 TWD（本次改的，見下表第 8 項） ｜ 機台站台的資產列表 | 只列核心貨幣，不再列出一排餘額 0 的其他幣別",
     [("以機台帳號登入前台", "檢視前台資產列表", "只顯示核心貨幣 TWD 一種，不列出其他幣別的零餘額項目")],
     "low", rc_true("規則已明確定義；此為前台（玩家端）畫面，過去所有已測 spec 皆為後台管理端，本條是第一次測前台資產列表", "§⭐兩種站台差很多")),
]
rm = {"spec_id": SID, "spec_version": SV, "requirements": reqs, "traceability": [{"requirement_id": r["requirement_id"], "spec_reference": r["spec_reference"]} for r in reqs]}
sa = {"spec_id": SID, "spec_version": SV, "content_hash": H,
      "summary": "17 給 QA 的說明：系統記帳幣別（核心貨幣/系統幣別）從全平台寫死 USDT，改成每個站台開站時自訂，機台站台用 TWD、線上站台維持 USDT，影響 21 處原寫死 USDT 的地方（發獎勵、注單三層金額、後台查詢、開站流程、新玩家註冊、人工出入金、擋阻檢查、機台前台資產列表）。"
                 "逐項比對後：核心貨幣設定/繼承/不可修改/依站台類型過濾清單已由 SPEC-SITELIST-001 驗證、鏈上錢包管理僅TWD頁籤已由 SPEC-PLATFORMRULE-001 驗證、機台帳號幣別取自核心貨幣已由 SPEC-ACCOUNT-001 驗證，本次不重複。"
                 "發獎勵進核心貨幣錢包的逐紅利類型細節屬於 SPEC-BONUSCCY-002（18紅利幣別盤點）範圍，本次不重複測試。新玩家註冊初始錢包對線上帳號因現無非USDT線上站台可測，暫不可測。"
                 "只測真正未覆蓋且有明確規則陳述的範圍：注單查詢頁金額顯示、後台查詢(會員列表/Dashboard)JOIN條件正確性、人工出入金預設幣別、核心貨幣須為啟用幣別的防呆、機台前台資產列表。",
      "scope": {"in_scope": ["注單查詢/明細頁金額以核心貨幣顯示", "會員列表/Dashboard 對機台(TWD)站台的查詢正確性（不因JOIN條件遺漏）", "人工存入/提出未指定幣別時預設用核心貨幣", "核心貨幣須為啟用中幣別的設定防呆", "機台站台前台資產列表僅列核心貨幣"],
                "out_of_scope": ["已由 SPEC-SITELIST-001 驗證的核心貨幣設定/繼承/不可修改/依站台類型過濾清單規則本身", "已由 SPEC-PLATFORMRULE-001 驗證的鏈上錢包管理僅顯示法幣TWD頁籤", "已由 SPEC-ACCOUNT-001 驗證的機台帳號幣別取自核心貨幣", "逐紅利類型（返水/簽到/代理/推薦/活動等）發放幣別的詳細規則，屬 SPEC-BONUSCCY-002 範圍", "線上帳號新註冊初始錢包依核心貨幣——現無非USDT線上站台可測，暫不可測", "機台場館前台不開放自行註冊——屬背景說明，非本檔改動內容，且已在其他包記錄為既定行為"]},
      "requirement_ids": [r["requirement_id"] for r in reqs],
      "ambiguities": [],
      "constraints": [], "edge_case_candidates": [], "open_questions": []}
def envelope(t, payload, sub, refs):
    aid = ids.artifact_id(t)
    art = {"artifact_id": aid, "artifact_type": t, "schema_version": "1.0", "version": 1, "run_id": RUN, "task_id": "T1", "iteration": 0, "created_by": A, "created_at": store.now(), "status": "DRAFT",
           "source": {"type": "SpecVersion", "ids": [f"{SID}@{SV}"]}, "references": refs, "requires_approval": None, "payload": payload}
    p = store.ROOT / "artifacts" / sub / RUN / f"{aid}.yaml"; store.save(p, art); print(p.relative_to(store.ROOT)); return p
refs = [{"entity_type": "SpecVersion", "id": SID, "version": SV}]
envelope("SpecAnalysis", sa, "spec-analysis", refs); envelope("RequirementModel", rm, "requirements", refs)
print(f"{len(reqs)} requirements drafted")
