#!/usr/bin/env python3
"""RUN-20260915-009 T1：Bug Analyst，依 Oscar 2026-09-15 實機截圖，核心貨幣(TWD)停用後
出金/洗分未被阻擋（違反剛由 PM 確認、已寫入 requirements.yaml 的 REQ-BONUSCCY-004）。"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids
RUN = "RUN-20260915-009"; ITER = 1
SID, SV, A = "SPEC-BONUSCCY-001", "1.0", "agent-bug-analyst"
def sr(loc, q=""): return {"spec_id": SID, "spec_version": SV, "location": loc, "quote": q[:300]}
ENV = {"name": "stage", "account": "ACAA00349（站長）"}

payload = {
    "draft_id": f"BUG-DRAFT-{ids.ulid()}",
    "title": "[前後台][機台站台] 核心貨幣(TWD)停用後，出金/洗分仍可成功執行，未被阻擋",
    "product": "ba-admin", "functional_area": "CASHFLOW",
    "severity_proposed": "critical", "priority_proposed": "high",
    "severity_rationale": "REQ-BONUSCCY-004 已由 PM 2026-09-15 明確確認：核心貨幣停用後，入金/出金/開分/洗分四項操作皆須被阻擋，目的是資金池出問題時即時止損。實測顯示出金、洗分兩項操作在核心貨幣已停用的情況下仍正常扣分成功，直接違反止損設計初衷——站台明明已經表態「這個幣別不能再動」，玩家分數卻仍能被兌現出金/洗掉，止損機制形同虛設。severity 定為 critical：涉及資金安全控制且是 PM 剛確認的明確規則，非模糊地帶",
    "environment": ENV, "spec_id": SID, "spec_version": SV, "requirement_id": "REQ-BONUSCCY-004",
    "acceptance_criteria_ids": ["AC-BONUSCCY-022", "AC-BONUSCCY-024"],
    "preconditions": [
        "機台站台（Arcade Machine）的鏈上錢包管理中，核心貨幣 TWD 對應的兩筆錢包幣別紀錄皆已停用（見 EVD-0055；截圖狀態欄「禁用」按鈕本身易誤讀為可點擊動作而非狀態顯示，已由 Oscar 2026-09-15 直接確認：該截圖當下 TWD 確實已是停用狀態，非待點擊的動作按鈕）",
    ],
    "reproduction_steps": [
        "登入機台版後台，至鏈上錢包管理，將該站台核心貨幣 TWD 對應的兩筆錢包幣別紀錄狀態改為停用",
        "切到機台版前台，依序嘗試：入金（投紙鈔，觸發 req-cashin → end-cashin）、出金（按 CASHOUT 鍵，觸發 req-cashout → end-cashout）、開分（店員收現金加分，觸發 req-keyin）、洗分（觸發 req-keyout）",
        "觀察四項操作各自的系統回應",
    ],
    "expected_result": "四項操作（入金、出金、開分、洗分）皆應被系統阻擋，不應完成入帳/扣分",
    "expected_result_spec_reference": sr("§一句話（限制段落）", "補充（2026-09-15 PM確認）：核心貨幣可停用作即時止損用途，停用後入金/出金/開分/洗分四項操作皆須被阻擋"),
    "actual_result": "出金（req-cashout→end-cashout）與洗分（req-keyout）皆回 0-OK，成功完成扣分，未被阻擋；入金（req-cashin→end-cashin）與開分（req-keyin）雖然失敗，但回的是「7-OUT OF SERVICE（服務不可用 DB/Redis/下游異常）」這種下游基礎設施錯誤訊息，而非「核心貨幣已停用」的明確業務拒絕——目前看似被擋，但實際上可能只是巧合的下游異常，而非系統刻意的止損邏輯",
    "actual_result_evidence_map": [
        {"claim": "鏈上錢包管理中，該站台核心貨幣 TWD 的兩筆紀錄皆為停用狀態（畫面本身的按鈕樣式易生歧義，已由 Oscar 2026-09-15 直接口頭確認截圖當下確實為停用狀態）", "evidence_id": "EVD-0055"},
        {"claim": "核心貨幣已停用時，入金 end-cashin 回 7-OUT OF SERVICE（服務不可用），而非明確的核心貨幣已停用拒絕", "evidence_id": "EVD-0056"},
        {"claim": "核心貨幣已停用時，開分 req-keyin 回 7-OUT OF SERVICE（服務不可用），而非明確的核心貨幣已停用拒絕", "evidence_id": "EVD-0057"},
        {"claim": "核心貨幣已停用時，出金 req-cashout→end-cashout 兩階段皆回 0-OK，成功完成扣分——未被阻擋", "evidence_id": "EVD-0058"},
        {"claim": "核心貨幣已停用時，洗分 req-keyout 回 0-OK（平台核可金額:100），成功完成扣分——未被阻擋", "evidence_id": "EVD-0059"},
    ],
    "evidence_ids": ["EVD-0055", "EVD-0056", "EVD-0057", "EVD-0058", "EVD-0059"],
    "api": {"url": "req-cashout / end-cashout / req-keyout", "method": "POST"},
    "impact": "核心貨幣停用做為資金池出問題時的緊急止損手段完全失效：出金與洗分仍可正常把玩家分數兌現/清空，等同於停用形同虛設。入金/開分雖目前意外被擋，但擋下的原因是下游基礎設施異常（DB/Redis）而非業務邏輯判斷，一旦下游恢復正常，入金/開分很可能也會跟出金/洗分一樣被錯誤放行——四項操作背後應是同一個判斷點（核心貨幣 enabled 狀態），目前顯然缺乏統一的檢查",
    "suspected_area": "後端：cashflow 服務（req-cashin/end-cashin、req-cashout/end-cashout、req-keyin、req-keyout 四支 API）在處理交易前，未檢查該站台核心貨幣對應的 wallet_currency.enabled 狀態；出金/洗分完全遺漏此檢查，入金/開分目前的失敗疑似只是下游服務異常的巧合，非刻意設計的阻擋邏輯",
    "ambiguity_suspected": False, "duplicate_candidates": [],
}
aid = ids.artifact_id("BugDraft")
art = {"artifact_id": aid, "artifact_type": "BugDraft", "schema_version": "1.0", "version": 1, "run_id": RUN, "task_id": "T1", "iteration": ITER,
       "created_by": A, "created_at": store.now(), "status": "DRAFT",
       "source": {"type": "Evidence", "ids": payload["evidence_ids"]},
       "references": [{"entity_type": "Requirement", "id": "REQ-BONUSCCY-004"}] + [{"entity_type": "Evidence", "id": e} for e in payload["evidence_ids"]],
       "requires_approval": None, "payload": payload}
p = store.ROOT / "artifacts" / "bug-analysis" / RUN / f"{aid}.yaml"; store.save(p, art)
print(p.relative_to(store.ROOT))
