#!/usr/bin/env python3
"""T1：Spec Analyst 對 SPEC-BONUSCCY-003 v1.0（20 紅利調整說明）產出 SpecAnalysis + RequirementModel。
本包是「這次部署」的回歸測試範圍說明，不是新行為 spec：這次只改兩件事——①存款金額拆成「原始金額」
（進錢包/算流水/算手續費）與「核心貨幣金額」（比活動門檻/累積統計）兩個欄位（目前兩者數值相同，
因為所有存款幣別本來就等於站台記帳幣別）②簽到活動「有效會員」改讀正確的資料表 deposit_log_v2。
spec.md 自己列出「這次能測什麼」5 項（T1~T5）與「這次測不了」1 項，逐項比對後：
- T4（現有USDT站台首儲/次儲/累積存款/VIP等級/獎勵發放金額改前改後完全不變）本質是「重跑既有回歸」，
  這些行為本身已由 SPEC-BONUSCCY-002 的 TC（REQ-BONUSCCY-006/007/010）完整測過，本次不重複設計新 TC，
  執行時直接重跑那批既有 TC 作為本次部署的回歸依據即可
- 「幣別換算算得對不對」spec 明講目前無任何存款會觸發換算（線上站台只收USDT），無真實情境可測，排除
只測 T1、T2、T3、T5 四項真正需要新設計案例的回歸重點。"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids
RUN = sys.argv[1]; SID, SV, A = "SPEC-BONUSCCY-003", "1.0", "agent-spec-analyst"
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
 req("存款原始金額正確進玩家錢包，不受「原始金額/核心貨幣金額」欄位拆分影響", "存款金額拆成「原始金額」（進錢包、算流水倍數、算手續費）與「核心貨幣金額」（比活動門檻、累積儲值統計、有效會員）兩個欄位後，玩家存多少錢，進錢包的金額與幣別仍應正確——這是本次部署最重要的回歸點", "functional", "success",
     "§改了什麼／①存款金額拆成兩個 + §這次能測什麼／T2", "原始金額 | 玩家實際存的錢，玩家看到的幣別 | 進錢包、算流水倍數、算手續費 ｜ T2 入金金額進錢包正確：存多少就進多少，幣別正確。這是最重要的回歸點",
     [("玩家於線上站台完成一筆系統存款（非人工存款）", "檢視入帳結果", "存入多少金額就進玩家錢包多少金額，幣別與存款當下一致，不因新拆出的「原始金額」欄位而算錯或漏算")],
     "high", rc_true("規則已明確定義，且 spec.md 自己點名是本次部署最重要的回歸點", "§這次能測什麼")),
 req("流水倍數與手續費以實際存入金額（原始金額）為基數計算", "存款後的「提領所需有效投注額」（流水門檻）與手續費，應以玩家實際存入的原始金額為基數計算，不是核心貨幣金額（換算後的比較用數字）", "functional", "success",
     "§改了什麼／①存款金額拆成兩個 + §這次能測什麼／T3", "原始金額 | … | 進錢包、算流水倍數、算手續費 ｜ T3 流水倍數與手續費的基數正確：存款後的「提領所需有效投注額」要以實際存入金額為基數算，不是別的數字",
     [("玩家完成一筆系統存款", "檢視存款後的提領所需有效投注額（流水門檻）與手續費計算結果", "皆以玩家實際存入的原始金額為基數計算，不是核心貨幣金額或其他換算後的數字")],
     "medium", rc_true("規則已明確定義", "§這次能測什麼")),
 req("簽到活動前台進度條與後台判定一致，皆讀取正確的入帳資料表", "簽到活動「有效會員」的判定，前台進度條與後台判定改為皆讀取 deposit_log_v2（入帳成功的存款都在裡面），不再是前後台各自讀不同的舊表；前台進度條應正確顯示進度並與後台判定一致，不再永遠顯示 0", "functional", "success",
     "§改了什麼／②簽到活動的「有效會員」改讀正確的表 + §這次能測什麼／T1", "後台判定：以前讀區塊鏈明細表，現在讀 deposit_log_v2（入帳成功的都在裡面）；前台進度條：以前讀另一張更舊的區塊鏈表，現在同上、與後台一致 ｜ T1 前台進度條會動、且與後台一致：前台簽到頁的有效會員進度條，數字應該跟後台判定的累積金額一致。以前前台永遠顯示 0",
     [("玩家有已入帳成功的存款記錄，尚未達到有效會員門檻", "檢視前台簽到頁的有效會員進度條", "進度條正確顯示累積金額，與後台判定的累積金額一致，不再是以前那樣永遠顯示 0"),
      ("玩家的累積存款達到有效會員門檻", "開啟一次前台簽到頁", "進度條達標並直接寫入有效會員狀態，與後台最終判定結果一致")],
     "medium", rc_true("規則已明確定義；spec 特別提醒這是唯一會讓數字變的改動，部署後玩家只要開一次簽到頁就會用新口徑重算，本來已達標的玩家會立刻變成有效會員——這是修正不是錯誤，但要驗證這個變化确实如預期發生", "§改了什麼")),
 req("簽到活動「有效會員每月重置」機制，跨月後進度正確歸零重算", "簽到活動若開啟「有效會員每月重置」設定，跨月後有效會員的累積進度應正確歸零並重新開始計算，不受本次讀取資料表來源變更（改讀 deposit_log_v2）影響", "functional", "success",
     "§這次能測什麼／T5", "T5 每月重置仍正常：簽到活動若開了「有效會員每月重置」，跨月後進度應歸零重算",
     [("簽到活動已開啟「有效會員每月重置」設定，玩家上個月的累積進度已達有效會員門檻", "跨月後檢視該玩家本月的有效會員進度", "進度正確歸零，重新從 0 開始累積計算，不因改讀 deposit_log_v2 而受影響（例如不會誤讀到上個月已計入歸零前的舊資料）")],
     "medium", rc_true("規則已明確定義", "§這次能測什麼")),
]
rm = {"spec_id": SID, "spec_version": SV, "requirements": reqs, "traceability": [{"requirement_id": r["requirement_id"], "spec_reference": r["spec_reference"]} for r in reqs]}
sa = {"spec_id": SID, "spec_version": SV, "content_hash": H,
      "summary": "20 紅利調整說明：這次部署只改兩件事——存款金額拆成原始金額/核心貨幣金額兩欄位（目前數值相同、結構先做好）、簽到活動有效會員改讀 deposit_log_v2（唯一會讓數字變的改動）。spec.md 自己列出本次能測的 5 項（T1~T5）與測不了的 1 項（幣別換算，無真實通道）。"
                 "逐項比對後：T4（現有USDT站台首儲/次儲/累積存款/VIP等級/獎勵發放金額改前改後完全不變）本質是重跑既有回歸，這些行為已由 SPEC-BONUSCCY-002 的 TC 完整測過，本次不重複設計新 TC，執行時直接重跑那批既有 TC 即可；幣別換算 spec 明講無真實情境可測，排除。只測 T1/T2/T3/T5 四項真正需要新設計案例的回歸重點。",
      "scope": {"in_scope": ["T2：存款原始金額正確進玩家錢包（本次最重要回歸點）", "T3：流水倍數與手續費以原始金額為基數", "T1：簽到活動前台進度條與後台判定一致（讀取deposit_log_v2）", "T5：簽到活動有效會員每月重置機制"],
                "out_of_scope": ["T4：現有USDT站台紅利數字完全不變——已由 SPEC-BONUSCCY-002 的 TC（REQ-006/007/010對應TC）完整測過，執行時重跑既有TC作為本次部署回歸依據，不重複設計新TC", "幣別換算是否算得對——spec明講目前無任何存款會觸發換算，無真實情境可測，等線上站台開出非USDT存款通道後再補測", "機台站台——spec明講機台站台目前沒有任何紅利活動，不在這次測試範圍"]},
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
