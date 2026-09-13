#!/usr/bin/env python3
"""RUN-002 / RUN-003 T1：以 Bug Analyst 角色產出 BugDraft（自 MAN-20260913-009 拆成兩個 Bug）。"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids
SID, SV, A = "SPEC-DAILYREPORT-001", "0.1", "agent-bug-analyst"
def sr(loc): return {"spec_id": SID, "spec_version": SV, "location": loc}
ENV = {"name": "stage", "url": "stage-admin-srv.springkyle.online", "account": "ACAA00280（站長）／ACAA00250（機台帳號，交易發起）"}
API = {"url": "https://stage-admin-srv.springkyle.online/api/v1/report/query-venue-daily-report", "method": "POST"}
BUGS = {
 "RUN-20260913-002": {
  "draft_id": "BUG-DRAFT-01M2DJ0000000000000000AA01", "title": "[後端][機台][場館日結報表] 依場館彙總／依機台明細維度的 API 回應缺少「場次數」欄位",
  "severity": "major", "priority": "high", "rationale": "Spec 明定的列表欄位整欄缺失（後端未回傳），對帳核心維度之一無法使用；非資料錯誤故不到 critical",
  "requirement_id": "REQ-DAILYREPORT-009", "acs": ["AC-DAILYREPORT-0091", "AC-DAILYREPORT-0092"], "tc": ("TC-DAILYREPORT-029", 1),
  "steps": ["登入後台，站台切換至機台場館（Arcade）", "進入 各式報表 > 場館日結報表，統計維度選「依場館彙總」，結算日期選 2026-09-08，搜尋", "觀察列表「場次數」欄", "開啟瀏覽器 Network，攔截 query-venue-daily-report 的回應 JSON，檢查是否有場次數欄位"],
  "expected": "「依場館彙總」列的場次數＝該場館底下所有機台帳號當日場次數的加總；API 回應應含對應欄位（如 sessionCount）", "loc": "§列表欄位/場次數（2026-09-03 定案）",
  "actual": "畫面「場次數」欄一律顯示「--」；API 回應整包無任何場次數欄位（僅 settlePeriod / endTime / 金額類欄位）",
  "map": [("畫面場次數欄顯示 --", "EVD-0009"), ("API 回應無 sessionCount 類欄位", "EVD-0044")], "evidence": ["EVD-0009", "EVD-0044"],
  "impact": "場館與平台對帳時無法得知當日場次筆數；依機台明細維度同樣受影響", "area": "後端 report/query-venue-daily-report 彙總層未計算場次數"},
 "RUN-20260913-003": {
  "draft_id": "BUG-DRAFT-01M2DJ0000000000000000AA02", "title": "[後端][機台][場館日結報表] 依場次明細維度的 API 回應缺少「開始時間」與「場次時長」欄位",
  "severity": "major", "priority": "high", "rationale": "Spec 明定場次編號需附開始／結束時間與時長；缺開始時間使前端連自行計算時長都不可能",
  "requirement_id": "REQ-DAILYREPORT-008", "acs": ["AC-DAILYREPORT-0081"], "tc": ("TC-DAILYREPORT-025", 1),
  "steps": ["登入後台，站台切換至機台場館（Arcade）", "進入 各式報表 > 場館日結報表，統計維度選「依場次明細」，結算日期選 2026-09-08，搜尋", "觀察每列「開始 ～ 結束」的開始時間與「場次時長」欄", "攔截 query-venue-daily-report 的回應 JSON，檢查是否有開始時間與時長欄位"],
  "expected": "每列有場次編號、開始時間、結束時間（UTC+0）、場次時長（結束－開始；進行中為累計至查詢當下）；API 回應應含開始時間（如 startTime）與時長（如 duration）欄位", "loc": "§列表欄位/場次編號 + §場次資訊/開始時間、場次時長",
  "actual": "畫面開始時間與場次時長皆顯示「--」；API 回應僅有 endTime，無開始時間與時長欄位",
  "map": [("畫面開始時間、場次時長顯示 --", "EVD-0009"), ("API 回應僅 endTime、無 startTime / duration", "EVD-0045")], "evidence": ["EVD-0009", "EVD-0045"],
  "impact": "無法檢視場次時長，場次明細維度失去核心資訊", "area": "後端 report/query-venue-daily-report 場次明細層未輸出 startTime / duration"},
}
for run, b in BUGS.items():
    payload = {"draft_id": b["draft_id"], "title": b["title"], "product": "ba-admin", "functional_area": "DAILYREPORT",
               "severity_proposed": b["severity"], "priority_proposed": b["priority"], "severity_rationale": b["rationale"], "environment": ENV,
               "spec_id": SID, "spec_version": SV, "requirement_id": b["requirement_id"], "acceptance_criteria_ids": b["acs"], "testcase_id": b["tc"][0], "testcase_version": b["tc"][1],
               "preconditions": ["測試帳號 ACAA00280（站長）可登入", "機台帳號 ACAA00250 於 2026-09-08 有已結束場次（sessionCode ACAA00250_20260908_0003）"],
               "reproduction_steps": b["steps"], "expected_result": b["expected"], "expected_result_spec_reference": sr(b["loc"]), "actual_result": b["actual"],
               "actual_result_evidence_map": [{"claim": c, "evidence_id": e} for c, e in b["map"]], "evidence_ids": b["evidence"], "api": API,
               "impact": b["impact"], "suspected_area": b["area"], "ambiguity_suspected": False, "duplicate_candidates": []}
    aid = ids.artifact_id("BugDraft")
    art = {"artifact_id": aid, "artifact_type": "BugDraft", "schema_version": "1.0", "version": 1, "run_id": run, "task_id": "T1", "iteration": 0, "created_by": A, "created_at": store.now(), "status": "DRAFT",
           "source": {"type": "ManualTestRecord", "ids": ["MAN-20260913-009"]},
           "references": [{"entity_type": "Requirement", "id": b["requirement_id"]}, {"entity_type": "TestCaseVersion", "id": b["tc"][0], "version": b["tc"][1]}, {"entity_type": "ManualTestRecord", "id": "MAN-20260913-009"}] + [{"entity_type": "Evidence", "id": e} for e in b["evidence"]],
           "requires_approval": None, "payload": payload}
    p = store.ROOT / "artifacts" / "bug-analysis" / run / f"{aid}.yaml"; store.save(p, art); print(run, p.relative_to(store.ROOT))
