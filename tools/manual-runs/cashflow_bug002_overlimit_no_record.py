#!/usr/bin/env python3
"""RUN-20260923-004 T1：Bug Analyst 依 Oscar 2026-09-23 提供的截圖（EVD-0073～0075），
針對「入金額度上限判定發生在 end-cashin 而非 req-cashin；超額交易完全未留下紀錄」提出 BugDraft。"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids
RUN = sys.argv[1]; ITER = int(sys.argv[2]) if len(sys.argv) > 2 else 0
SID, SV, A = "SPEC-CASHFLOW-001", "0.1", "agent-bug-analyst"
def sr(loc, q=""): return {"spec_id": SID, "spec_version": SV, "location": loc, **({"quote": q[:300]} if q else {})}
ENV = {"name": "stage", "site": "Arcade（機台場館）", "account": "ACAA00417（機台帳號）；查詢者 ZZAA00415（站長）"}
EVD = ["EVD-0073", "EVD-0074", "EVD-0075"]

payload = {
    "draft_id": f"BUG-DRAFT-{ids.ulid()}",
    "title": "[後端][Arcade] 入金額度上限判定發生在 end-cashin 而非 req-cashin，且超額交易完全未留下交易紀錄",
    "product": "ba-admin", "functional_area": "CASHFLOW",
    "severity_proposed": "critical", "priority_proposed": "high",
    "severity_rationale": "兩個獨立問題疊加：①判定時機與現行定案（SPEC-ARCADE-001 v0.7 v07，2026-09-04 全數定案）相反——額度上限應於 req-cashin（第一階段）判定並預留、不建立 PENDING，v07 changelog 明載『紙鈔不會在超額的情況下被收』；實際是 req-cashin 先成功建立 PENDING、紙鈔已進錢箱，到 end-cashin 才拒絕，等同執行的是已被 v07 明文廢除的 v06 舊邏輯（『入帳階段超限處置待定案』一條已於 v07 移除）。②AC-CASHFLOW-0302（本次 TC-CASHFLOW-035 步驟2）明定『交易因額度上限或其他原因被拒絕，有留下「未成立」的交易紀錄，可查得拒絕原因』；實際交易紀錄查詢總筆數 0，連 PENDING 曾經建立過的痕跡都沒有。這代表现金（紙鈔）已進入機台錢箱、玩家帳戶卻完全沒有任何後台紀錄可查——若機台未忠實退鈔或退鈔失敗，場館端無從對帳、玩家亦無憑據申訴，屬資金軌跡缺失的嚴重風險，故評 critical。priority high：額度上限是每個場館的日常防護機制，觸發條件明確、非邊緣情境",
    "environment": ENV, "spec_id": SID, "spec_version": SV, "requirement_id": "REQ-CASHFLOW-030",
    "acceptance_criteria_ids": ["AC-CASHFLOW-0302"],
    "testcase_id": "TC-CASHFLOW-035", "testcase_version": 1,
    "api": {"url": "req-cashin / end-cashin", "method": "POST", "request_evidence_id": "EVD-0074", "response_evidence_id": "EVD-0074"},
    "preconditions": [
        "stage 環境，站台切換下拉選單已選定 Arcade（機台類型站台），機台帳號 ACAA00417",
        "該場館目前全場館機台分數餘額合計已接近或等同場館額度上限設定值（不確定當下確切額度，以送出遠超上限的金額測試）",
    ],
    "reproduction_steps": [
        "以開發工具對機台 ACAA00417 送出 req-cashin，金額為足以使全場館分數餘額合計超過場館額度上限的極大值",
        "檢視 req-cashin 回應：本次回 0-OK（成功），並取得 TXID",
        "以同一 TXID 送出 end-cashin（確認入金）",
        "檢視 end-cashin 回應：本次回 1-OVER LIMIT（超過場館額度上限）",
        "進入 各式報表 > 交易紀錄查詢，以機台帳號 ACAA00417 查詢（不設其他篩選），檢視搜尋結果",
    ],
    "expected_result": "①額度上限應於 req-cashin（第一階段）判定，超額時 req-cashin 本身即回 1-OVER LIMIT、不建立 PENDING、紙鈔不進錢箱（SPEC-ARCADE-001 v0.7 v07 定案）；②不論判定發生在哪一階段，只要交易因額度上限被拒絕，都應在交易紀錄查詢留下一筆「未成立」紀錄，可查得未成立原因為超過額度上限（AC-CASHFLOW-0302）",
    "expected_result_spec_reference": sr("SPEC-ARCADE-001 v0.7 §入金（req-cashin→end-cashin）＋ changelog v07（2026-09-04）：「入金額度上限的判定與預留移至 req-cashin……end-cashin 不再判定額度，超額因此在紙鈔捲入錢箱前就被擋下，原『入帳階段超限處置待定案』一條移除」；SPEC-CASHFLOW-001 v0.1 §四種金流/交易不成立的原因 AC-CASHFLOW-0302「交易因額度上限或其他原因被拒絕，有留下「未成立」的交易紀錄，可查得拒絕原因」"),
    "actual_result": "req-cashin 回 0-OK、建立 PENDING、取得 TXID（紙鈔已進錢箱）；end-cashin 才回 1-OVER LIMIT——判定時機與 v07 定案相反，等同執行已被明文廢除的 v06 舊邏輯。且以觸發此筆超額的機台帳號查詢交易紀錄，總筆數 0、查無任何紀錄（含 PENDING 曾建立過的痕跡），不僅未成立紀錄未留下，連該筆入金本身在系統中完全找不到",
    "actual_result_evidence_map": [
        {"claim": "洗分因餘額不足回 1-NO CREDITS（對照組，spec 明文允許此例外不留紀錄，行為正確）", "evidence_id": "EVD-0073"},
        {"claim": "入金 req-cashin 回 0-OK 建立 PENDING（TXID 1af58cd7-7170-4ee5-a9b0-ad3ef6bb3910），end-cashin 確認同一 TXID 才回 1-OVER LIMIT", "evidence_id": "EVD-0074"},
        {"claim": "交易紀錄查詢機台帳號 ACAA00417，無篩選條件，總筆數 0，查無任何紀錄", "evidence_id": "EVD-0075"},
    ],
    "evidence_ids": EVD,
    "impact": "任何導致全場館分數餘額合計超過額度上限的入金，紙鈔會先被機台收下（req-cashin 成功建 PENDING），到 end-cashin 才拒絕；該筆交易從頭到尾不會出現在交易紀錄查詢，場館端無法對帳、無法查核是否已忠實退鈔，玩家亦無憑據申訴。TC-CASHFLOW-035 判 fail；連動影響同樣依賴『未成立會留紀錄』前提的 TC-TXLOG-125/141/146/147/148/154/158/159/164/165、TC-CASHFLOW-005/042、TC-CASHOUT-045 等案例的有效性，待本單釐清後一併檢視",
    "suspected_area": "後端額度上限判定邏輯：疑似仍執行 v06（判定於 end-cashin）而非 v07（判定於 req-cashin）的版本；以及未成立交易的紀錄寫入邏輯，疑似完全未實作或僅實作餘額不足以外原因中的特定分支。兩者需 RD 分別確認是否為同一段程式碼的問題",
    "ambiguity_suspected": False,
    "duplicate_candidates": [],
}
aid = ids.artifact_id("BugDraft")
art = {"artifact_id": aid, "artifact_type": "BugDraft", "schema_version": "1.0", "version": 1, "run_id": RUN, "task_id": "T1", "iteration": ITER,
       "created_by": A, "created_at": store.now(), "status": "DRAFT",
       "source": {"type": "Evidence", "ids": EVD},
       "references": [{"entity_type": "Requirement", "id": "REQ-CASHFLOW-030"}, {"entity_type": "TestCase", "id": "TC-CASHFLOW-035"}] + [{"entity_type": "Evidence", "id": e} for e in EVD],
       "requires_approval": None, "payload": payload}
p = store.ROOT / "artifacts" / "bug-analysis" / RUN / f"{aid}.yaml"; store.save(p, art)
print(p.relative_to(store.ROOT))
