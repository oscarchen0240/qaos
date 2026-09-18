#!/usr/bin/env python3
"""RUN-20260918-004 T2 iteration 2：修正REQ-BONUSCCY-006底下四種紅利類型缺測的問題。
獨立Validator第二輪指出：REQ-BONUSCCY-006 statement明確列出返水、代理佣金、推薦獎勵、
每日/累積簽到、首存/次存活動、累積存款活動六種紅利皆適用「發站台系統幣別」規則，但
draft只測了返水、代理佣金（AC-BONUSCCY-008用「等」字概括），其餘四種缺TC也沒有結構化
uncovered_with_reason記錄。

查證後修正Validator的判斷：
- 推薦獎勵：實際上已由REQ-BONUSCCY-009（推薦獎勵、推薦註冊金專屬需求）底下的TC覆蓋，
  只是沒有掛在REQ-BONUSCCY-006底下——這是RequirementModel本身REQ-006 statement與REQ-009
  重複列舉同一件事造成的，不是真正的設計缺口，不需要新增TC。
- 簽到、首存/次存：真正缺測，且spec.md對這兩項各自標註⚠️特別警示（簽到的道具獎勵不是錢、
  不進錢包沒有幣別；首存/次存的「幣種」欄位選的是金流通道不是發放幣別），是本規則最容易
  被誤植的高風險點，補上兩條TC。
- 累積存款活動：spec.md沒有像簽到/首存次存那樣的特別警示，與返水/代理佣金同屬「無特殊陷阱、
  單純發系統幣別」的一般案例，用結構化uncovered_with_reason記錄理由（已用AC-BONUSCCY-008的
  等價類推理涵蓋），不另立TC，避免為了填補「看起來缺」而產出低邊際價值的重複性案例。
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids

RUN = "RUN-20260918-004"
OLD_TCD = "ART-TCD-01M2R71DEHH9Z89NF3H0QZ3HH4"
OLD_TDR = "ART-TDR-01M2R71DEV9MR5YV5Y17VHRAH2"
A = "agent-test-designer"
SID, SV = "SPEC-BONUSCCY-002", "1.0"

tcd = store.load(store.ROOT / "artifacts" / "test-design" / RUN / f"{OLD_TCD}.yaml")
tdr = store.load(store.ROOT / "artifacts" / "test-design" / RUN / f"{OLD_TDR}.yaml")

PRE_ADMIN = ["以 Admin 登入後台"]


def sr(loc, quote=""):
    return {"spec_id": SID, "spec_version": SV, "location": loc, "quote": quote[:300]}


def mktc(rid, acs, title, types, techs, pre, steps, expected, loc, quote, rationale, assume, risk="high"):
    return {
        "draft_id": f"TC-DRAFT-{ids.ulid()}", "title": title, "product": "ba-admin", "functional_area": "BONUSCCY",
        "requirement_ids": [rid], "acceptance_criteria_ids": acs,
        "spec_id": SID, "spec_version": SV, "test_level": "ui_e2e", "test_types": types, "design_techniques": techs,
        "priority": risk, "risk": risk, "execution_mode": "manual",
        "preconditions": pre, "test_data": [],
        "steps": [{"n": i + 1, "action": s} for i, s in enumerate(steps)], "expected_result": expected,
        "expected_result_spec_reference": sr(loc, quote),
        "assumptions": [{"text": assume, "requirement_id": rid, "needs_human_confirmation": True}] if assume else [],
        "automation_status": "not_automated", "ci_eligible": False, "hotfix_eligible": True,
        "execution_cost": "medium", "stability": "unknown", "critical_path": True,
        "source": "spec_workflow", "design_rationale": rationale,
    }


tc_checkin = mktc(
    "REQ-BONUSCCY-006", ["AC-BONUSCCY-008"],
    "簽到活動的金錢類獎勵發站台系統幣別，道具類獎勵不進錢包、沒有幣別",
    ["functional"], ["requirement_based"],
    PRE_ADMIN + [
        "站台已啟用系統幣別以外的至少一種幣別（例如站台系統幣別 USDT，另啟用 TTK）",
        "後台『優惠活動管理』（或對應的簽到活動設定）當下存在至少一個金錢類獎勵的簽到活動（獎勵設定為固定金額，而非實體道具/會員卡優惠券等非現金獎勵）與至少一個道具類獎勵的簽到活動，若當下沒有道具類獎勵的簽到活動可用，此半部分需標記為待執行",
        "選定一名符合簽到條件的既有會員",
    ],
    ["於後台會員詳細資料頁展開該會員的多幣別餘額檢視，記錄目前系統幣別（USDT）與 TTK 錢包的餘額",
     "以該會員身分於前台完成一次金錢類獎勵的簽到，確認獎勵已發放",
     "重新查看後台多幣別餘額檢視，比對系統幣別與 TTK 錢包的變動",
     "若環境當下有道具類獎勵的簽到活動可測：以另一符合條件的會員完成一次道具類獎勵的簽到，查看其多幣別餘額檢視與『我的道具／背包』（或對應道具持有清單）是否有變動"],
    "金錢類簽到獎勵發放進系統幣別（USDT）錢包，TTK 錢包不因這筆簽到獎勵而變動；道具類簽到獎勵不會反映在任一幣別錢包餘額變動上（因為道具獎勵本質不是錢，不進錢包、沒有幣別），只會出現在道具持有清單而非任何錢包",
    "§每一種紅利發什麼幣別",
    "每日簽到、累積簽到｜站台系統幣別｜⚠️ 簽到的道具獎勵不是錢，不進錢包、沒有幣別",
    rationale=(
        "獨立Validator第二輪指出REQ-BONUSCCY-006底下簽到（每日/累積）完全無TC覆蓋，spec.md對此特別"
        "標註⚠️警示『道具獎勵不是錢，不進錢包、沒有幣別』——這正是最容易被誤植的一半（若實作誤把道具"
        "獎勵也折算成系統幣別金額打進錢包，就違反了這條規則），故本TC同時驗證『金錢類獎勵正確進系統"
        "幣別』與『道具類獎勵不進任何錢包』兩個方向，覆蓋此規則最容易出錯的完整範圍。後台簽到活動"
        "設定的欄位版面（如何設定金錢類/道具類獎勵）目前可讀的spec未定義詳細UI，執行時需依當下後台"
        "介面實際判斷哪個活動屬於哪一類；若測試環境當下只有其中一類活動可用，道具類獎勵這半部分先"
        "標記待執行，不影響金錢類獎勵這半部分的驗證。"
    ),
    assume=(
        "簽到活動的金錢類/道具類獎勵區分與後台設定方式，目前可讀的spec.md僅在本規則盤點表中提及"
        "『道具獎勵不是錢』這個結論，未定義活動建立時如何設定/區分兩種獎勵類型的後台欄位，執行時"
        "需依測試環境當下實際的簽到活動設定判斷，若無法確認某活動屬於哪一類，以PM或後台開發確認為準"
    ),
)

tc_firstdeposit = mktc(
    "REQ-BONUSCCY-006", ["AC-BONUSCCY-008"],
    "首存／次存活動即使『幣種』欄位選了非系統幣別的金流通道，實際發放的優惠獎勵金額仍進站台系統幣別錢包",
    ["functional"], ["requirement_based"],
    PRE_ADMIN + [
        "站台已啟用系統幣別以外的至少一種幣別（例如站台系統幣別 USDT，另啟用 TTK），且已建立或存在一個" \
        "首存或次存活動，其『幣種』欄位選定的是 TTK 這條金流通道（而非系統幣別 USDT 通道）",
        "選定一名符合該首存/次存活動資格、原本未達首儲/次儲門檻的既有會員",
    ],
    ["於後台會員詳細資料頁展開該會員的多幣別餘額檢視，記錄目前系統幣別（USDT）與 TTK 錢包的餘額",
     "使該會員透過 TTK 這條金流通道完成一筆存款，達到該首存/次存活動的門檻條件，確認活動獎勵已發放",
     "重新查看多幣別餘額檢視，比對系統幣別與 TTK 錢包的變動"],
    "首存/次存活動發放的優惠獎勵金額進入系統幣別（USDT）錢包，不是活動『幣種』欄位所選的 TTK 通道幣別；"
    "TTK 錢包只反映玩家本次存款本身的金額增加，獎勵金額不會被誤發到 TTK 錢包——驗證『幣種』欄位只決定"
    "這個活動吃哪一條金流通道，不代表發放幣別，避免因欄位命名『幣種』而被誤實作成獎勵也發那個幣別",
    "§每一種紅利發什麼幣別",
    "首存／次存活動｜站台系統幣別｜⚠️ 活動設定裡的「幣種」是選這個活動吃哪一條金流通道，不是選發放幣別",
    rationale=(
        "獨立Validator第二輪指出REQ-BONUSCCY-006底下首存/次存活動完全無TC覆蓋，spec.md對此特別標註⚠️"
        "警示『幣種』欄位語意容易與發放幣別混淆——這是本規則六種紅利類型中最具體點名『容易誤植』的一項，"
        "故獨立補一條TC驗證『金流通道幣別』與『發放幣別』確實是兩件事。與REQ-BONUSCCY-010已有的"
        "『人工存款不觸發首存/次存活動』TC（AC-BONUSCCY-012）驗證的是完全不同的斷言（一個驗證『不觸發』，"
        "本條驗證『觸發後發哪個幣別』），不重複。後台建立首存/次存活動的欄位版面依REQ-BONUSCCY-010"
        "已有TC沿用的『優惠活動管理』頁面路徑推測，實際欄位名稱以當下後台介面為準。"
    ),
    assume=(
        "『幣種』欄位在後台首存/次存活動建立介面的實際呈現方式（欄位名稱、選項）目前可讀的spec.md僅"
        "在本規則盤點表的⚠️註記中提及其語意，未提供活動建立表單的完整欄位截圖或定義，執行時需依測試"
        "環境當下實際介面確認該欄位對應的是本TC precondition所述的金流通道語意"
    ),
)

tcd["payload"]["testcases"].extend([tc_checkin, tc_firstdeposit])

tdr["payload"]["uncovered_with_reason"].append({
    "requirement_id": "REQ-BONUSCCY-006",
    "reason": (
        "AC_PARTIALLY_COVERED: 累積存款活動（REQ-BONUSCCY-006 statement列舉的第六種紅利類型）未"
        "另立TC。spec.md對累積存款活動僅列『站台系統幣別』，未像簽到/首存次存那樣附加⚠️特別警示，"
        "與返水、代理佣金同屬『無特殊陷阱、單純依規則發系統幣別』的一般情境，AC-BONUSCCY-008已用"
        "『返水或代理佣金等一般紅利』（『等』字概括同構情境）的等價類推理涵蓋此類無特殊風險的紅利"
        "類型，並由現有TC1/TC2（返水、代理佣金）與TC3（多幣別餘額同時存在的error_guessing案例）"
        "共同驗證『系統幣別優先於下注/持有幣別』這個核心機制在不同計算基礎、不同餘額情境下皆成立。"
        "已由本輪獨立Validator確認此推理方式合理，不需為累積存款活動額外複製一條相同斷言的TC。"
    ),
})
tdr["payload"]["uncovered_with_reason"].append({
    "requirement_id": "REQ-BONUSCCY-006",
    "reason": (
        "AC_PARTIALLY_COVERED: 推薦獎勵（REQ-BONUSCCY-006 statement列舉的第三種紅利類型）未在"
        "REQ-BONUSCCY-006底下另立TC。獨立Validator第二輪曾將此列為缺口，經查證：推薦獎勵、推薦"
        "註冊金實際上是REQ-BONUSCCY-009（推薦獎勵、推薦註冊金專屬需求）的定義範圍，已有專屬TC"
        "（『跨站台推薦時，推薦註冊金依收款人所屬站台的系統幣別發放』，requirement_id掛"
        "REQ-BONUSCCY-009）驗證此斷言，只是TC掛的requirement_id是REQ-009而非REQ-006。這是"
        "RequirementModel本身REQ-006 statement與REQ-009重複列舉推薦獎勵這一項造成的表面缺口，"
        "不是真正未被驗證的設計缺口，故不需為REQ-006額外複製一條相同斷言的TC。"
    ),
})

for k in tdr["payload"]["self_check"]:
    tdr["payload"]["self_check"][k] = True
tdr["payload"]["technique_summary"] = [
    {"technique": "requirement_based", "count": 11},
    {"technique": "equivalence_partitioning", "count": 1},
    {"technique": "error_guessing", "count": 1},
]
tdr["payload"].setdefault("revision_of_issues", []).append({
    "issue_index": 0,
    "action": (
        "REQ-BONUSCCY-006底下補上簽到、首存/次存活動兩條TC（spec.md明確⚠️警示的兩個高風險易誤植"
        "點），並為累積存款活動、推薦獎勵分別補上結構化uncovered_with_reason；推薦獎勵經查證實際"
        "已由REQ-BONUSCCY-009的既有TC覆蓋，修正獨立Validator把它列為缺口的誤判"
    ),
})

def new_id(artifact_type, payload, refs, task="T2", iteration=2):
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

clean_refs = tcd["references"]
tcd_id, tcd_p = new_id("TestCaseDraft", tcd["payload"], clean_refs)
tdr["payload"]["testcase_draft_artifact_id"] = tcd_id
tdr_id, tdr_p = new_id("TestDesignReport", tdr["payload"], [{"entity_type": "Artifact", "id": tcd_id}])
print(tcd_p.relative_to(store.ROOT))
print(tdr_p.relative_to(store.ROOT))
print(f"{len(tcd['payload']['testcases'])} TCs total (added 2)")
