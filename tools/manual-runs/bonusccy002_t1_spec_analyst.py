#!/usr/bin/env python3
"""T1：Spec Analyst 對 SPEC-BONUSCCY-002 v1.0（18 紅利/彩金幣別盤點）產出 SpecAnalysis + RequirementModel。
本包盤點各類紅利實際發放的幣別，核心規則：除彩金活動與遊戲商JACKPOT/促銷派彩外，其餘紅利一律發站台系統幣別。
逐節比對後刻意排除以下範圍：
- 排除規則層面已由 SPEC-ACCOUNT-001/SPEC-PLATFORMRULE-001 驗證過「機台帳號不參與返水/優惠活動/簽到」，
  本包大部分一般紅利規則對機台帳號天然不適用，本次只在線上站台測試（SpringKyle 站台同時啟用 TTK/USDT 兩種幣別，適合驗證幣別不受下注/存款幣別影響）
- 「存款通道幣別與站台系統幣別不一致」四個 ❌ 情境（累積存款門檻/簽到有效會員/VIP儲值統計/首存次存被灌大或不發）：
  spec.md 明講「現在還沒有非系統幣別的存款會進來」，目前無真實管道可測，本次不寫成確定 Requirement
- 「存款活動門檻換算」目前程式未實作（spec 明講 2100 TWD 誤判達標是已知落差，非本次要驗證的正確行為），排除
- 「人工存款不進錢包」這件事本身（含未指定幣別預設站台系統幣別）已由 SPEC-BONUSCCY-001 REQ-BONUSCCY-003 驗證，本次只測「人工存款不觸發活動/統計」這個新角度
只測真正未被覆蓋、且有明確規則陳述的範圍：一般紅利發放幣別、彩金活動的自選幣別例外、遊戲商JACKPOT/促銷派彩的錢包幣別規則、
推薦註冊金的收款人站台幣別歸屬、人工存款不觸發任何活動與統計。"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids
RUN = sys.argv[1]; SID, SV, A = "SPEC-BONUSCCY-002", "1.0", "agent-spec-analyst"
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
 req("一般紅利一律發站台系統幣別，不受玩家使用其他已啟用幣別下注或存款影響", "返水、代理佣金、推薦獎勵、每日/累積簽到、首存/次存活動、累積存款活動，皆發站台系統幣別；玩家用哪個錢包下注、用什麼幣別存款，都不影響這些紅利發出來的幣別", "functional", "success",
     "§一句話 + §每一種紅利發什麼幣別", "除了「彩金活動」與「遊戲商JACKPOT／促銷派彩」，其他紅利一律發「站台系統幣別」。玩家拿哪個錢包下注、用什麼幣別存款，都不影響紅利發出來的幣別",
     [("玩家所屬線上站台已啟用兩種以上幣別（例如TTK、USDT，站台系統幣別為USDT），玩家持有並使用TTK餘額下注/存款", "該玩家獲得一筆返水或代理佣金等一般紅利", "紅利發放進站台系統幣別（USDT）錢包，不是玩家下注/存款所用的TTK")],
     "high", rc_true("規則已明確定義，是本包核心規則；錯發幣別直接是金流正確性問題", "§每一種紅利發什麼幣別")),
 req("彩金活動的發放幣別為後台建立活動時自行指定的幣別", "彩金活動是全站唯一可以自己選發放幣別的紅利類型，不受站台系統幣別限制，依後台建活動時選定的幣別，送進玩家對應幣別的錢包", "functional", "success",
     "§每一種紅利發什麼幣別", "彩金活動 | 後台建活動時自己填的幣別 | 全站唯一可以自己選發放幣別的紅利 ｜ 2026-09-02 與 PM 確認：彩金依後台建活動時選的幣別，送進玩家對應幣別的錢包",
     [("後台建立一個彩金活動，指定發放幣別為站台系統幣別以外的某個已啟用幣別（例如TTK）", "玩家符合條件獲得該筆彩金", "彩金送進玩家的TTK錢包（後台指定的幣別），不是站台系統幣別，且玩家原本沒有該幣別錢包時會自動出現一列")],
     "medium", rc_true("規則已明確定義，且是本包唯一的例外規則", "§每一種紅利發什麼幣別")),
 req("遊戲商JACKPOT／促銷派彩的發放幣別為玩家下注當下所使用的錢包幣別", "遊戲商JACKPOT／促銷派彩由玩家該筆遊戲的錢包幣別決定，依遊戲幣別依匯率換算後入帳（PP、AWC、SABA等遊戲商）", "functional", "success",
     "§每一種紅利發什麼幣別", "遊戲商 JACKPOT／促銷派彩 | 玩家該筆遊戲的錢包幣別 | 由遊戲幣別依匯率換算後入帳（PP、AWC、SABA 等）",
     [("玩家使用TTK錢包餘額在某遊戲商遊戲下注，中得該遊戲商發放的JACKPOT或促銷派彩", "檢視派彩入帳結果", "派彩依匯率換算後進入TTK錢包（玩家下注當下所用的錢包幣別），不是站台系統幣別")],
     "medium", rc_true("規則已明確定義；執行時依賴測試環境是否有可觸發JACKPOT/促銷派彩的遊戲商遊戲，若環境不支援可標記為待執行", "§每一種紅利發什麼幣別")),
 req("推薦註冊金進入收款人所屬站台的幣別", "推薦獎勵、推薦註冊金皆發站台系統幣別；推薦註冊金特別之處在於，是進「收款人所屬站台」的系統幣別，不是贈送人/推薦人所屬站台的幣別", "functional", "success",
     "§每一種紅利發什麼幣別", "推薦獎勵、推薦註冊金 | 站台系統幣別 | 註冊金進「收款人所屬站台」的幣別",
     [("推薦人所屬站台A（系統幣別X）推薦一名新玩家於站台B（系統幣別Y）註冊，A、B系統幣別不同", "新玩家獲得推薦註冊金", "註冊金依收款人（新玩家）所屬站台B的系統幣別Y發放，不是推薦人所屬站台A的幣別X")],
     "medium", rc_true("規則已明確定義；此為跨站台情境，執行時需要兩個系統幣別不同的站台互相推薦關係，若測試環境不易建置可標記為待執行", "§每一種紅利發什麼幣別")),
 req("人工存款不觸發任何活動與累積統計，但稽核流水正常計入", "人工存款不會進任何活動與累積統計：不觸發首存/次存活動、不累積存款活動的累積門檻、不計入簽到活動的有效會員門檻、不計入玩家累積儲值統計（不推進VIP等級）；但稽核流水（打碼量）仍依後台填的稽核倍數正常計入。「錢進玩家錢包」這個基本行為已由 SPEC-BONUSCCY-001 REQ-BONUSCCY-003 驗證，本條不重複測", "functional", "success",
     "§人工存款", "人工存款不會進任何活動與累積統計。它只做兩件事：把錢加進錢包、寫一筆交易紀錄 ｜ 首存／次存活動 ❌不觸發，不算首儲、也不會配到任何存款活動 ｜ 累積存款活動 ❌不累積 ｜ 簽到活動的「有效會員」門檻 ❌不計入 ｜ 玩家累積儲值統計（VIP等級的依據） ❌不計入，所以也不會推進VIP等級 ｜ 稽核流水（打碼量） ✅有，依後台填的稽核倍數",
     [("玩家原本未達首存活動門檻，對其執行一筆金額足以達標的人工存款", "檢視首存活動是否被觸發、是否發放獎勵", "不觸發，該玩家不算首儲，也不會配到任何存款活動"),
      ("玩家原本未達簽到活動的有效會員門檻，對其執行一筆金額足以達標的人工存款", "檢視簽到活動的有效會員狀態", "門檻不計入這筆人工存款金額，玩家不會因此變成有效會員"),
      ("對玩家執行一筆人工存款", "檢視該筆存款是否計入稽核流水（打碼量）", "依後台填寫的稽核倍數正常計入稽核流水")],
     "high", rc_true("規則已明確定義，且 2026-09-02 已由 PM 二次確認（後台人工存款目前走 v4，不計入累積儲值，對 VIP 等級也沒有影響）；若人工存款被誤計入活動或統計，可能被用來刷首存/次存優惠或人為推進 VIP 等級，風險標 high", "§人工存款")),
]
rm = {"spec_id": SID, "spec_version": SV, "requirements": reqs, "traceability": [{"requirement_id": r["requirement_id"], "spec_reference": r["spec_reference"]} for r in reqs]}
sa = {"spec_id": SID, "spec_version": SV, "content_hash": H,
      "summary": "18 紅利（彩金）幣別盤點：核心規則是除彩金活動與遊戲商JACKPOT/促銷派彩外，其餘紅利一律發站台系統幣別，不受玩家實際下注/存款幣別影響；另盤點人工存款不進任何活動與累積統計、存款通道幣別與系統幣別不一致時的四個已知風險（目前無真實管道可測，本次排除）。"
                 "逐節比對後：機台帳號天然不參與返水/優惠活動/簽到已由 SPEC-ACCOUNT-001/SPEC-PLATFORMRULE-001 驗證，本包一般紅利規則只在線上站台測；人工存款「錢進錢包」本身已由 SPEC-BONUSCCY-001 REQ-BONUSCCY-003 驗證，不重複；存款通道幣別不一致的四個❌情境與存款活動門檻換算，spec 明講目前無真實管道可測，本次排除，等真實TWD存款通道開通後再補測。",
      "scope": {"in_scope": ["一般紅利（返水/代理佣金/推薦獎勵/簽到/首存次存/累積存款）發放幣別=站台系統幣別，不受其他已啟用幣別影響", "彩金活動的自選發放幣別例外", "遊戲商JACKPOT/促銷派彩的下注錢包幣別規則", "推薦註冊金的收款人站台幣別歸屬", "人工存款不觸發任何活動與累積統計（但稽核流水正常計入）"],
                "out_of_scope": ["機台帳號的返水/優惠活動/簽到——天然排除，已由 SPEC-ACCOUNT-001/SPEC-PLATFORMRULE-001 驗證", "人工存款「錢進錢包」本身與未指定幣別預設站台系統幣別——已由 SPEC-BONUSCCY-001 REQ-BONUSCCY-003 驗證", "存款通道幣別與站台系統幣別不一致的四個❌情境——目前無真實非系統幣別存款管道可測", "存款活動門檻的匯率換算——spec 明講現行程式尚未實作，屬已知未來落差非本次驗證對象"]},
      "requirement_ids": [r["requirement_id"] for r in reqs],
      "ambiguities": [], "constraints": [], "edge_case_candidates": [], "open_questions": []}
def envelope(t, payload, sub, refs):
    aid = ids.artifact_id(t)
    art = {"artifact_id": aid, "artifact_type": t, "schema_version": "1.0", "version": 1, "run_id": RUN, "task_id": "T1", "iteration": 0, "created_by": A, "created_at": store.now(), "status": "DRAFT",
           "source": {"type": "SpecVersion", "ids": [f"{SID}@{SV}"]}, "references": refs, "requires_approval": None, "payload": payload}
    p = store.ROOT / "artifacts" / sub / RUN / f"{aid}.yaml"; store.save(p, art); print(p.relative_to(store.ROOT)); return p
refs = [{"entity_type": "SpecVersion", "id": SID, "version": SV}]
envelope("SpecAnalysis", sa, "spec-analysis", refs); envelope("RequirementModel", rm, "requirements", refs)
print(f"{len(reqs)} requirements drafted")
