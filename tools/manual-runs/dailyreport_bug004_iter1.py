#!/usr/bin/env python3
"""RUN-20260923-001 T1 iter 1：依 Oscar 2026-09-23 補充的依場次明細截圖（EVD-0072）重寫根因。
iter 0 把「損益與期末餘額錯誤」列為疑似獨立成因（Validator major issue 要求不得以「連帶」暗示因果）；
新證據證實三症狀同源：跨越場次切換點的注單，其投注與派彩分別依各自發生時間歸屬場次／營業日，被拆成兩半。"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids
RUN = sys.argv[1]; ITER = int(sys.argv[2]) if len(sys.argv) > 2 else 1
SID, SV, A = "SPEC-DAILYREPORT-001", "0.1", "agent-bug-analyst"
ENV = {"name": "stage", "site": "Arcade（機台場館，日結時間 00:00 UTC+0）", "account": "ACAA00414（機台帳號）；查詢者 ZZAA00411／ACAA00412（站長）"}
EVD = ["EVD-0068", "EVD-0069", "EVD-0070", "EVD-0071", "EVD-0072"]

payload = {
    "draft_id": f"BUG-DRAFT-{ids.ulid()}",
    "title": "[後台][Arcade][後端][場館日結報表] 跨場次切換點的注單被拆成投注與派彩兩半分記不同場次／營業日，且日結結算場次歸到結束日而非開始的營業日",
    "product": "ba-admin", "functional_area": "DAILYREPORT",
    "severity_proposed": "critical", "priority_proposed": "high",
    "severity_rationale": "本報表用途為「供平台與場館對帳、分潤」（spec §功能說明）。單一根因同時污染四個對帳欄位：注單數、有效投注額、損益、期末餘額，且三者的總和仍然正確（全場次合計 注單數 6／有效投注額 1000／損益 372 皆與注單查詢相符），只有分配到各營業日／各場次的結果是錯的——這類「總數對、分帳錯」的缺陷不會被總計列的檢查發現，使用者與對帳人員無從察覺。實測 09-22 列注單相關欄全為 0（該日實際有 6 筆注單）、0005 場次損益 −20（實際 +180）、0001 場次注單數 0 卻有有效投注額 200，皆為可直接證偽的錯誤。與同功能既有 BUG-DAILYREPORT-003 對照：該案 severity_rationale 明載「無金額計算錯誤，故不到 critical」而評 major；本案具備其所缺的金額計算錯誤要素，評 critical 有合理區隔。priority high：觸發條件是「注單的投注與派彩跨越場次切換點」，其中日結時刻每日必然發生，非邊緣情境",
    "environment": ENV, "spec_id": SID, "spec_version": SV, "requirement_id": "REQ-DAILYREPORT-009",
    "acceptance_criteria_ids": ["AC-DAILYREPORT-0091"],
    "testcase_id": "TC-DAILYREPORT-031", "testcase_version": 1,
    "preconditions": [
        "stage 環境後台，站台切換下拉選單已選定 Arcade（機台類型站台），Arcade 場館設定的日結時間為 00:00 UTC+0",
        "機台帳號 ACAA00414 於 2026-09-22 23:32 開始場次 ACAA00414_20260922_0005（開分 1000），該場次於 2026-09-23 00:00 日結時刻被強制結束（日結結算）；緊接著 00:00 開始新場次 ACAA00414_20260923_0001",
        "0005 場次期間產生 6 筆注單，投注時間 2026-09-22 23:55:50～23:59:57，投注額 200×4＋100×2＝1000；派彩欄為站方視角，6 筆為 −96／+100／+200／−192／−192／−192（玩家淨贏 372）",
        "其中流水號 6745026（投注額 200）的投注時間為 2026-09-22 23:59:57、派彩時間為 2026-09-23 00:00:24——投注在 0005 場次內、派彩已落在 0001 場次內",
    ],
    "reproduction_steps": [
        "進入 各式報表 > 場館日結報表，統計維度選「依場次明細」，結算日期 2026-09-23，機台帳號留空，搜尋",
        "檢視 ACAA00414_20260922_0005 與 ACAA00414_20260923_0001 兩列的 結算期間／場次時間／注單數／有效投注額／損益／期初餘額／期末餘額，以及底部總計列",
        "統計維度改為「依機台明細」，機台帳號 ACAA00414，結算日期 2026-09-21～2026-09-23，比對 09-22 與 09-23 兩列",
        "於 各式報表 > 注單查詢 以會員編號 ACAA00414 查詢同期間注單，核對 6 筆的投注時間、派彩時間、投注額與派彩",
        "開啟機台 ACAA00414 前台畫面，記錄實際餘額",
    ],
    "expected_result": "①一筆注單的投注與派彩應歸屬同一個場次／營業日（以單一基準計算，spec 未明示採投注時間或派彩時間，但不得把同一筆拆成兩半）：6745026 的投注額 200 與其派彩 392 應同屬一列；②同一列的注單數與有效投注額應採同一基準——不應出現「注單數 0 卻有有效投注額 200」（0001 場次）或「注單數 6 但有效投注額只算 5 筆」（0005 場次）；③損益應為該場次／營業日全部注單的損益合計，0005 場次應為 +180（前 5 筆玩家淨贏）或含第 6 筆的 +372，而非 −20（＝180 減去第 6 筆的投注額 200）；④日結結算場次 ACAA00414_20260922_0005、ACAA00314_20260922_0005 應歸屬其開始的營業日 2026-09-22，而非結束日 2026-09-23（依 CLR-DAILYREPORT-007 PM 回覆與 TC-DAILYREPORT-031 經 APR-0003 核准的假設，已回寫入 RM REQ-DAILYREPORT-009 statement）",
    "expected_result_spec_reference": {"spec_id": SID, "spec_version": SV,
        "location": "§列表欄位/場次數＋§業務規則/場次日結＋§背景：場次資訊（「期間所有的開分、入金、洗分、出金與注單，一律歸屬於這個場次」，SPEC-ARCADE-001 v0.7 §場次如何開始與結束）；日結結算場次的營業日歸屬依 CLR-DAILYREPORT-007（APPLIED）與 TC-DAILYREPORT-031（assumption 經 APR-0003 核准），已於 2026-09-23 回寫入 RM REQ-DAILYREPORT-009 statement。註：spec 未明示注單歸屬營業日採投注時間或派彩時間，亦未定義「注單數」欄（CLR-DAILYREPORT-006 已知缺口）——但本案三個症狀在任一基準下皆錯，故非 ambiguity"},
    "actual_result": "同一筆注單被拆成投注與派彩兩半分記不同場次：依場次明細（結算日期 2026-09-23）顯示 ACAA00414_20260922_0005（09-22 23:32～09-23 00:00）注單數 6／有效投注額 800／損益 −20／期末 2380，ACAA00414_20260923_0001（09-23 00:00～00:21）注單數 0／有效投注額 200／損益 +392／期末 2772；總計 注單數 6／有效投注額 1000／損益 372（總數與注單查詢相符，僅分配錯誤）。逐項驗算：有效投注額 800＝派彩時間亦在 0005 場次內的前 5 筆、200＝6745026（依派彩時間）；注單數 6 全記於 0005（依投注時間），故 0001 出現「注單數 0 卻有投注額 200」；損益 −20＝前 5 筆玩家淨贏 180 減去 6745026 的投注額 200，+392＝6745026 的派彩總額（本金 200＋淨贏 192）。另 ACAA00414_20260922_0005 與 ACAA00314_20260922_0005 兩個 9/22 開始的日結結算場次，結算期間皆顯示 2026-09-23；依機台明細 09-22 列因此注單數／有效投注額／損益全為 0，09-23 列為 注單數 6／有效投注額 800／損益 −20／期末 2380，與機台前台實際餘額 2772 差 392",
    "actual_result_evidence_map": [
        {"claim": "6 筆注單投注時間 2026-09-22 23:55:50～23:59:57，6745026 派彩時間 2026-09-23 00:00:24；投注額合計 1000；派彩（站方視角）合計 −372", "evidence_id": "EVD-0068"},
        {"claim": "依機台明細 09-23 列 注單數 6／有效投注額 800／損益 −20／期末 2380；09-22 列 注單數 0／有效投注額 0／損益 0", "evidence_id": "EVD-0069"},
        {"claim": "依場次明細 場次 ACAA00414_20260922_0005 時間 09-22 23:32～09-23 00:00，結算期間卻顯示 2026-09-23", "evidence_id": "EVD-0070"},
        {"claim": "機台前台實際餘額 2772，與依機台明細 09-23 列期末餘額 2380 差 392", "evidence_id": "EVD-0071"},
        {"claim": "依場次明細同一查詢下 0005 與 0001 兩場次的注單數 6/0、有效投注額 800/200、損益 −20/+392、總計 6／1000／372；另 ACAA00314_20260922_0005 同樣列於結算期間 2026-09-23", "evidence_id": "EVD-0072"},
    ],
    "evidence_ids": EVD,
    "impact": "任何注單只要投注與派彩跨越場次切換點（洗分／出金結束場次、分數歸零、逾時結束，以及每日必然發生的日結時刻），其投注額與派彩就會被拆記到兩個場次／兩個營業日，使注單數、有效投注額、損益、期末餘額四個欄位同時失真；因總計仍然正確，總計列的檢查無法發現。疊加日結結算場次歸屬結束日的問題後，整個營業日的注單資料會出現在隔日（本例 09-22 列注單相關欄全為 0，該日實際有 6 筆注單）。場館端點鈔對帳與平台分潤皆以此報表為準。TC-DAILYREPORT-031、TC-DAILYREPORT-077 判 fail",
    "suspected_area": "後端 query-venue-daily-report／場次彙總邏輯：①注單的金額彙總疑似分別以「扣分時點」歸投注額、以「派彩時點」歸派彩，未以單一注單為不可分割單位歸屬場次；②注單數以投注時間計、有效投注額以派彩時間計，兩者基準不一致；③場次的營業日歸屬疑似取場次結束時間（日結結算場次＝日結時刻＝下一營業日起點）而非開始時間。spec §場次資訊已明訂「期間所有的開分、入金、洗分、出金與注單，一律歸屬於這個場次」，可作為修正依據。前端未發現問題",
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
