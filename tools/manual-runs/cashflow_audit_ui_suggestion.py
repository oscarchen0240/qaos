#!/usr/bin/env python3
"""RUN-20260915-002 T1：Bug Analyst 依 Oscar 提供的實機截圖提出優化建議單（非規格牴觸，而是可用性建議）——
TWD 稽核設定（開分/洗分 vs 入金/出金兩組）在畫面與 API 回應上完全無法區分。"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids
RUN = sys.argv[1]; ITER = int(sys.argv[2]) if len(sys.argv) > 2 else 0
SID, SV, A = "SPEC-CASHFLOW-001", "0.1", "agent-bug-analyst"
def sr(loc): return {"spec_id": SID, "spec_version": SV, "location": loc}
ENV = {"name": "stage", "account": "ZZAA00261（管理員）"}

payload = {
    "draft_id": f"BUG-DRAFT-{ids.ulid()}",
    "title": "[優化建議][前端/後端][稽核設定] TWD 稽核設定「開分/洗分」與「入金/出金」兩組畫面與API回應完全相同，使用者無法區分",
    "product": "ba-admin", "functional_area": "CASHFLOW",
    "severity_proposed": "minor", "priority_proposed": "medium",
    "severity_rationale": "「開分/洗分」與「入金/出金」為兩組獨立稽核設定一事，係 Oscar（PM，2026-09-15）口頭直接確認的後端設計：後端目前對這兩組回傳的可視化欄位完全相同，前端未做視覺區隔，並非 spec 文字明訂（cashflow_spec.md／platformrule_spec.md 皆只描述『依幣種設定稽核倍數』單一資料模型，未提及兩組並存），故此判斷以 PM 直接確認為依據，非本 Analyst 自行臆測。severity 由 trivial 上修為 minor、priority 由 low 上修為 medium：spec 對稽核倍數誤設有明確警語（調高倍數前務必評估現場衝擊，設定不當會導致玩家當場洗不出錢、引發爭議），操作者在完全無法分辨兩組設定的情況下修改，有直接誤改稽核倍數、引發現場糾紛的風險；REQ-CASHFLOW-001 本身 risk=medium，與此風險路徑一致",
    "environment": ENV, "spec_id": SID, "spec_version": SV, "requirement_id": "REQ-CASHFLOW-001",
    "acceptance_criteria_ids": [],
    "preconditions": ["站台 Arcade（機台類型）的鏈上錢包管理／出金設定 TWD 頁籤，存在「開分/洗分」與「入金/出金」兩組獨立的稽核倍數設定（此為 Oscar 2026-09-15 口頭確認的後端設計，spec 文字本身未提及此二分）"],
    "reproduction_steps": [
        "以管理員 ZZAA00261 登入後台，站台切換選單切至 Arcade（機台）",
        "至帳務管理 > 出金設定（或鏈上錢包管理）TWD 頁籤",
        "檢視列表，注意到有兩筆名稱、代碼、付款方式、出金手續費、稽核倍數、狀態皆完全相同的「New Taiwan Dollar」紀錄",
        "開啟瀏覽器 Network，檢查對應查詢 API 的回應 JSON，確認兩筆紀錄的所有欄位值（paymentMethod/currencyName/currencySymbol/transactionFee/audit/status）是否完全相同",
    ],
    "expected_result": "使用者應能從畫面（或至少從 API 回應）分辨這兩組稽核設定分別對應「開分/洗分」還是「入金/出金」，避免改錯組別（此為可用性建議，非 spec 明文要求；「稽核倍數依幣種設定」本身是 spec 明文，但「兩組需可視覺區分」是本 Analyst 依 Oscar 口頭確認的資料模型推論出的可用性建議）",
    "expected_result_spec_reference": sr("§機台帳號的稽核（稽核倍數依幣種設定，機台預設 0 倍；『兩組』本身未見於 spec 文字，見 severity_rationale 說明來源）"),
    "actual_result": "兩筆 TWD 紀錄在畫面上完全無法區分（名稱、代碼、手續費、稽核倍數、狀態皆相同），API 回應的欄位值也完全相同，沒有任何分組標識欄位",
    "actual_result_evidence_map": [
        {"claim": "畫面上兩筆 New Taiwan Dollar 紀錄視覺上完全相同，無法分辨對應哪一組功能", "evidence_id": "EVD-0054"},
        {"claim": "API 回應中兩筆紀錄除順序外所有欄位值完全相同，無分組標識欄位", "evidence_id": "EVD-0053"},
    ],
    "evidence_ids": ["EVD-0053", "EVD-0054"],
    "impact": "操作者修改稽核倍數等設定時，無法確認自己改的是「開分/洗分」還是「入金/出金」哪一組，有改錯風險（例如原意只想調整入金稽核倍數，卻誤改到洗分那組）",
    "suspected_area": "前端：出金設定/鏈上錢包管理 TWD 頁籤列表元件未顯示分組標籤；後端：查詢 API 回應未包含可辨識分組的欄位（如 group/scope）",
    "ambiguity_suspected": False, "duplicate_candidates": [],
}
aid = ids.artifact_id("BugDraft")
art = {"artifact_id": aid, "artifact_type": "BugDraft", "schema_version": "1.0", "version": 1, "run_id": RUN, "task_id": "T1", "iteration": ITER,
       "created_by": A, "created_at": store.now(), "status": "DRAFT",
       "source": {"type": "Evidence", "ids": payload["evidence_ids"]},
       "references": [{"entity_type": "Requirement", "id": "REQ-CASHFLOW-001"}] + [{"entity_type": "Evidence", "id": e} for e in payload["evidence_ids"]],
       "requires_approval": None, "payload": payload}
p = store.ROOT / "artifacts" / "bug-analysis" / RUN / f"{aid}.yaml"; store.save(p, art)
print(p.relative_to(store.ROOT))
