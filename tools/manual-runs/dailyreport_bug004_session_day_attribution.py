#!/usr/bin/env python3
"""RUN-20260923-001 T1：Bug Analyst 依 Oscar 2026-09-23 提供的截圖（EVD-0068～0071），
針對「日結結算場次歸錯營業日，連帶注單／金額／損益全部歸錯日；同列注單數與有效投注額基準不一致；損益與期末餘額錯誤」提出 BugDraft。"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids
RUN = sys.argv[1]; ITER = int(sys.argv[2]) if len(sys.argv) > 2 else 0
SID, SV, A = "SPEC-DAILYREPORT-001", "0.1", "agent-bug-analyst"
ENV = {"name": "stage", "site": "Arcade（機台場館，日結時間 00:00 UTC+0）", "account": "ACAA00414（機台帳號）；查詢者 ACAA00412／ZZAA00411（站長）"}
EVD = ["EVD-0068", "EVD-0069", "EVD-0070", "EVD-0071"]

payload = {
    "draft_id": f"BUG-DRAFT-{ids.ulid()}",
    "title": "[後台][Arcade][後端][場館日結報表] 日結結算場次歸屬到結束日而非開始的營業日，該場次的開分與注單整批歸錯日；同列注單數與有效投注額基準不一致；另觀察到損益與期末餘額錯誤（成因待確認）",
    "product": "ba-admin", "functional_area": "DAILYREPORT",
    "severity_proposed": "critical", "priority_proposed": "high",
    "severity_rationale": "本報表的用途是「供平台與場館對帳、分潤」（spec §功能說明），本次在同一筆查詢中同時觀察到三個破壞對帳基礎的症狀：①跨日結時刻的場次連同其開分與全部注單被整批歸到隔一個營業日，使兩個營業日的數字同時失真（受影響日少計、隔日多計）；②同一列的注單數與有效投注額採用不同時間基準，列內自相矛盾；③損益值錯誤並據以推算期末餘額，實測期末餘額 2380 與機台前台實際餘額 2772 差 392。①②有共同的觸發條件與機制（同一筆跨日結時刻的場次／注單，日期標籤與時間基準不一致）；③目前找不到任何能從本批注單推導出 −20 的計算路徑，疑似獨立成因，須由 RD 確認是否同源——若確認不同源，應自本單拆出獨立追蹤與複測。期末餘額與現金淨收是場館端點鈔與分潤的依據，錯誤金額會直接進入帳務，且畫面外觀正常、無任何提示，使用者無從察覺。評 critical 而非 major：非單一欄位顯示問題，而是金額計算與歸屬同時錯誤且已可用實際餘額證偽。",
    "environment": ENV, "spec_id": SID, "spec_version": SV, "requirement_id": "REQ-DAILYREPORT-009",
    "acceptance_criteria_ids": ["AC-DAILYREPORT-0091"],
    "testcase_id": "TC-DAILYREPORT-031", "testcase_version": 1,
    "preconditions": [
        "stage 環境後台，站台切換下拉選單已選定 Arcade（機台類型站台），Arcade 場館設定的日結時間為 00:00 UTC+0",
        "機台帳號 ACAA00414 於 2026-09-22 23:32 有一個場次開始（開分 1000），該場次持續到 2026-09-23 00:00 的日結時間被強制結束（狀態日結結算），場次編號 ACAA00414_20260922_0005",
        "該場次期間產生 6 筆注單（投注時間 2026-09-22 23:55:50～23:59:57），投注額 200×4＋100×2＝1000；派彩欄為站方視角，6 筆分別為 −96／+100／+200／−192／−192／−192，站方淨損益 −372（玩家淨贏 372）",
        "其中流水號 6745026 那筆的派彩時間為 2026-09-23 00:00:24，晚於日結時刻",
    ],
    "reproduction_steps": [
        "進入 各式報表 > 場館日結報表，機台帳號填 ACAA00414，結算日期 2026-09-21～2026-09-23，統計週期按日，統計維度「依機台明細」，搜尋",
        "檢視 2026-09-22 與 2026-09-23 兩列的 場次數／開分金額／注單數／有效投注額／損益／期初餘額／期末餘額",
        "統計維度改為「依場次明細」，結算日期 2026-09-23，搜尋，檢視場次編號與場次起訖時間對應的結算期間",
        "於 各式報表 > 注單查詢 以會員編號 ACAA00414 查詢同期間注單，核對投注時間、派彩時間、投注額與派彩",
        "開啟機台 ACAA00414 的前台畫面，記錄其實際餘額",
    ],
    "expected_result": "①場次 ACAA00414_20260922_0005 為日結結算場次，應歸屬其開始的營業日 2026-09-22（依 CLR-DAILYREPORT-007 PM 回覆與 TC-DAILYREPORT-031 已核准假設），其開分 1000、6 筆注單、有效投注額、損益、現金淨收皆應計入 2026-09-22 列；②同一列的注單數與有效投注額須採同一時間基準，6 筆注單對應有效投注額 1000；③損益應等於該營業日全部注單的站方損益合計 −372，期末餘額應為 期初 + 開分 + 損益方向一致的結果，與機台前台實際餘額 2772 相符",
    "expected_result_spec_reference": {"spec_id": SID, "spec_version": SV,
        "location": "§列表欄位/場次數（「為當日結束的場次筆數」）＋§業務規則/場次日結（「日結時間到達時強制結束所有進行中的場次」）；日結結算場次的營業日歸屬依 CLR-DAILYREPORT-007（APPLIED，PM 2026-09-14 回覆確認 TC-DAILYREPORT-031 的假設）與 TC-DAILYREPORT-031 expected「日結結算場次歸屬開始的營業日」（assumption 由 APR-0003 核准）。註：RM REQ-DAILYREPORT-009 statement 目前僅載入 CLR-007 的第一層（日結結算計入場次數），「歸屬開始的營業日」一句原未回寫，已於 2026-09-23 補入（req_dailyreport009_clr007_attribution_backfill.py；本 bug 的依據不取決於該回寫，CLR-007 APPLIED 與 TC-031 經 APR-0003 核准的假設已足）"},
    "actual_result": "依場次明細顯示場次 ACAA00414_20260922_0005（場次時間 2026-09-22 23:32～2026-09-23 00:00、時長 27 分）的結算期間為 2026-09-23，場次編號本身帶 20260922；依機台明細 2026-09-23 列為 場次數 1／開分 1000／注單數 6／有效投注額 800／損益 −20／期初 1400／期末 2380，2026-09-22 列為 場次數 4／開分 1100／洗分 1300／注單數 0／有效投注額 0／損益 0／期末 1400。6 筆注單投注額合計 1000 但有效投注額顯示 800（恰少派彩時間跨越日結時刻的 6745026 那筆 200）；站方損益實為 −372 但顯示 −20；期末餘額 2380 與機台前台實際餘額 2772 相差 392（＝372＋20）",
    "actual_result_evidence_map": [
        {"claim": "6 筆注單投注時間 2026-09-22 23:55:50～23:59:57、派彩時間含 2026-09-23 00:00:24 一筆；投注額合計 1000；派彩（站方視角）合計 −372", "evidence_id": "EVD-0068"},
        {"claim": "依機台明細 09-23 列 注單數 6／有效投注額 800／損益 −20／期末 2380；09-22 列 注單數 0／有效投注額 0／損益 0", "evidence_id": "EVD-0069"},
        {"claim": "依場次明細 場次 ACAA00414_20260922_0005 時間 2026-09-22 23:32～2026-09-23 00:00，結算期間卻顯示 2026-09-23", "evidence_id": "EVD-0070"},
        {"claim": "機台前台實際餘額 2772，與報表期末餘額 2380 差 392", "evidence_id": "EVD-0071"},
    ],
    "evidence_ids": EVD,
    "impact": "凡是跨越日結時刻仍在進行中的場次（日結結算），其開分／入金／洗分／出金與全部注單都會被記到隔一個營業日，造成兩個營業日的對帳數字同時失真；同列的注單數與有效投注額另因時間基準不一致而互相矛盾。損益與期末餘額的錯誤（本例期末差 392）成因未明，不保證修好前兩項即一併解決，須獨立驗證。場館端點鈔對帳與平台分潤皆以此報表為準，且畫面無任何異常提示。TC-DAILYREPORT-031、TC-DAILYREPORT-077 判 fail",
    "suspected_area": "後端 query-venue-daily-report 的營業日歸屬邏輯：疑似以場次結束時間（日結結算場次＝日結時刻，屬下一個營業日的起點）決定結算期間，而非場次開始時間；注單彙總另疑似以派彩時間計金額、以投注時間計筆數（同列兩基準）；損益欄的計算來源需 RD 獨立排查——−20 無法由本批注單的任何組合推導（6 筆合計 −372、排除跨日那筆後 5 筆合計 −180），故不宜假設它與前兩項同源；期末餘額係以該損益推算，會一併錯。前端未發現問題",
    "ambiguity_suspected": False,
    "duplicate_candidates": [],
}
aid = ids.artifact_id("BugDraft")
art = {"artifact_id": aid, "artifact_type": "BugDraft", "schema_version": "1.0", "version": 1, "run_id": RUN, "task_id": "T1", "iteration": ITER,
       "created_by": A, "created_at": store.now(), "status": "DRAFT",
       "source": {"type": "Evidence", "ids": EVD},
       "references": [{"entity_type": "Requirement", "id": "REQ-DAILYREPORT-009"}, {"entity_type": "TestCase", "id": "TC-DAILYREPORT-031"}] + [{"entity_type": "Evidence", "id": e} for e in EVD],
       "requires_approval": None, "payload": payload}
p = store.ROOT / "artifacts" / "bug-analysis" / RUN / f"{aid}.yaml"; store.save(p, art)
print(p.relative_to(store.ROOT))
