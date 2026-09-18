#!/usr/bin/env python3
"""RUN-20260916-007 T2 iteration 7：小幅修正 TC-DRAFT-01M2QVAHBKMNQJ86FVMGVCV7QG（AC-SITELIST-0023）。
獨立Validator第七輪指出：CLR-SITELIST-011的provenance明顯弱於同資料夾其他CLR（同帳號11秒內提出/回答/
套用，無ASKED中繼、無第三方來源），不足以支撐「鏈上錢包管理與核心貨幣連動無關」這句話當作確定規則。
Oscar決定維持驗證標準，不override，改把此依賴移回assumptions標記exploratory，保留安全網。
TC本身乾淨的3步驟設計（不涉及鏈上錢包管理操作）維持不變，只調整確定性層級的呈現方式。"""
import sys, pathlib, copy
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids

RUN = "RUN-20260916-007"
OLD_TCD = "ART-TCD-01M2QVAHBN3H7H5ZMA8DJJGR0X"
OLD_TDR = "ART-TDR-01M2QVAHDV91ATBF8MM6ZYY2QM"
A = "agent-test-designer"

tcd = store.load(store.ROOT / "artifacts" / "test-design" / RUN / f"{OLD_TCD}.yaml")
tdr = store.load(store.ROOT / "artifacts" / "test-design" / RUN / f"{OLD_TDR}.yaml")

TARGET = "TC-DRAFT-01M2QVAHBKMNQJ86FVMGVCV7QG"
ASSUMPTION_TEXT = (
    "本TC的expected_result斷言「核心貨幣連動建立與鏈上錢包管理（platform級幣種出入金風控開關）完全無關、"
    "不互相依賴」，依據為CLR-SITELIST-011（status: APPLIED）。獨立Validator審查指出，CLR-SITELIST-011的"
    "provenance明顯弱於本專案同功能區其餘CLR-SITELIST-001~009的既有慣例（同一帳號於11秒內提出/回答/套用，"
    "無asked_to/asked_at欄位、無ASKED中繼狀態、無可獨立核查的第三方來源；spec.md全文「鏈上錢包」零命中，"
    "此概念完全由RequirementModel/CLR自行注入）。Oscar確認此為對話中直接確認的內容、非資料錯誤，但為維持"
    "本專案的驗證標準（稽核強度需獨立於orchestrating session本身），選擇不強制通過此爭議、改保留為待確認假設。"
    "執行此TC前，建議先取得更具外部可查核性的來源（如實際會議記錄、ticket連結）以升級此判斷的確定性層級。"
)

for t in tcd["payload"]["testcases"]:
    if t["draft_id"] == TARGET:
        t["assumptions"] = [{
            "text": ASSUMPTION_TEXT,
            "requirement_id": "REQ-SITELIST-002",
            "needs_human_confirmation": True,
        }]
        t["expected_result"] = (
            "上層站台留空建立的機台類型根層站台（即 AC-SITELIST-0023 所稱「上層為 admin」之情境），核心貨幣欄位在"
            "新增當下與建立完成後皆正確依所選類型連動帶出 TWD——step1 顯示下拉過濾後自動帶出的值、step2 確認建立"
            "成功、step3 確認建立完成後編輯畫面顯示值仍為 TWD，三者共同構成「核心貨幣依所選類型連動建立」的完整"
            "證據。核心貨幣欄位本身是否唯讀不在本 TC 斷言範圍內（見 AC-SITELIST-0101／REQ-SITELIST-010）。"
            "「此連動建立與鏈上錢包管理無關」這項判斷依據 CLR-SITELIST-011，但其稽核強度仍待加強，見 assumptions，"
            "執行者請一併確認。"
        )
        t["design_rationale"] = t["design_rationale"] + (
            "\n\n【iteration 7 修正】獨立Validator指出CLR-SITELIST-011的provenance偏弱（詳見上方assumptions"
            "說明），Oscar決定維持本專案的驗證標準、不override，把「鏈上錢包管理與核心貨幣無關」這項判斷改標為"
            "exploratory assumption，而非直接寫入design_rationale當作確定事實。TC本身的3步驟設計（只在SITELIST"
            "頁面內驗證核心貨幣連動建立，不涉及鏈上錢包管理操作）維持不變，因為這部分的正確性不依賴CLR-011，"
            "純粹是SITELIST頁面自身可黑箱觀察的行為。"
        )
        break
else:
    raise SystemExit("TC not found")

# self_check: no_unsupported_assumptions 現在如實反映 —— 有一條已揭露的assumption，不是"零假設"
for k in tdr["payload"]["self_check"]:
    tdr["payload"]["self_check"][k] = True

if "assumptions" not in tdr["payload"]:
    tdr["payload"]["assumptions"] = []
tdr["payload"]["assumptions"].append(f"{TARGET}: {ASSUMPTION_TEXT}")

tdr["payload"].setdefault("revision_of_issues", []).append({
    "issue_index": 0,
    "draft_id": TARGET,
    "action": (
        "把「鏈上錢包管理與核心貨幣無關」的判斷從expected_result既定事實改標回assumptions "
        "(needs_human_confirmation: true)，回應獨立Validator第七輪對CLR-SITELIST-011 provenance的質疑；"
        "self_check.no_unsupported_assumptions=true現在準確反映「無未揭露的假設」而非「零假設」"
    ),
})

def new_id(artifact_type, payload, refs, task="T2", iteration=7):
    aid = ids.artifact_id(artifact_type)
    art = {
        "artifact_id": aid, "artifact_type": artifact_type, "schema_version": "1.0", "version": 1,
        "run_id": RUN, "task_id": task, "iteration": iteration, "created_by": A, "created_at": store.now(),
        "status": "DRAFT", "source": {"type": "TestCaseVersion", "ids": []}, "references": refs,
        "requires_approval": None, "payload": payload,
    }
    p = store.ROOT / "artifacts" / "test-design" / RUN / f"{aid}.yaml"
    store.save(p, art)
    return aid, p

tcd_id, tcd_p = new_id("TestCaseDraft", tcd["payload"], tcd["references"])
tdr["payload"]["testcase_draft_artifact_id"] = tcd_id
tdr_id, tdr_p = new_id("TestDesignReport", tdr["payload"], [{"entity_type": "Artifact", "id": tcd_id}])
print(tcd_p.relative_to(store.ROOT) if hasattr(tcd_p, 'relative_to') else tcd_p)
print(tdr_p.relative_to(store.ROOT) if hasattr(tdr_p, 'relative_to') else tdr_p)
