#!/usr/bin/env python3
"""T1：Spec Analyst 對 SPEC-ARCADE-001 v0.7（實體機台正本）產出 SpecAnalysis + RequirementModel。
本檔是「實體機台開發包」的正本（單一依據），已被拆成六個開發包分別抽錄並個別完整測試過
（ACCOUNT/SITELIST/CASHFLOW/TXLOG/CASHOUT/DAILYREPORT/PLATFORMRULE，共 7 個 spec_id，經背景
Explore agent 逐段核對統計）。本次只針對「正本才有、七份既有 requirements.yaml 完全沒涵蓋到」
的真正新內容建 Requirement，避免重複測試已覆蓋的規則。已知有出入/矛盾之處（B類）另循 Clarification
或直接修正既有 spec 處理，不在本次 RequirementModel 範圍內。

排除的內容：
- 正本開頭功能說明/名詞對照/角色與權限/機台帳號排除規則整表等，已由 ACCOUNT/PLATFORMRULE 完整涵蓋
- 四種金流、場次規則、洗分出金核實、場館日結報表核心邏輯，已由 CASHFLOW/CASHOUT/DAILYREPORT 完整涵蓋
- 機台前台「僅顯示當前進行中場次」的顯示隔離規則（500/539/835行）：發生在機台前台遊戲畫面（玩家/店員操作介面），
  不在 QAOS 現有七包的後台 admin 系統範圍內，標記 out_of_scope，不在本次建 Requirement

本次涵蓋：機台場館前台不開放註冊（A1）、加盟傭金/代理返傭不計入機台流水的底層規則本身（A2）、
機台帳號交易不進優惠彩金審核佇列的底層規則本身（A3）、出金設定TWD頁籤稽核倍數設定操作本身（A4）、
場次逾時時間欄位操作員唯讀（A5）、洗分出金核實的核實/作廢寫入操作紀錄（A6）。"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids
RUN = sys.argv[1]; SID, SV, A = "SPEC-ARCADE-001", "0.7", "agent-spec-analyst"
AREA = "ARCADE"
spec = store.load(store.spec_dir(SID) / "spec.yaml"); H = spec["versions"][0]["content_hash"]
def sr(loc, q=""): return {"spec_id": SID, "spec_version": SV, "location": loc, "quote": q[:300]}
def rc_true(desc, loc): return {"defined": True, "description": desc, "spec_reference": sr(loc)}

def req(title, stmt, typ, kind, loc, quote, acs, risk, rc):
    rid = ids.alloc("REQ", AREA)
    r = {"requirement_id": rid, "version": 1, "spec_id": SID, "spec_version": SV, "type": typ, "title": title, "statement": stmt,
         "acceptance_criteria": [{"ac_id": ids.alloc("AC", AREA), "given": g, "when": w, "then": t} for (g, w, t) in acs],
         "spec_reference": sr(loc, quote), "ambiguity": None, "risk": risk, "status": "DRAFT", "history": [], "behavior_kind": kind, "rejection_contract": rc}
    return r

reqs = [
 req("機台場館前台暫不開放自行註冊", "機台場館（含自行經營的機台主站台）的前台不提供自行註冊入口；機台帳號一律由後台建立。線上站台前台維持開放以帳號密碼方式自行註冊，不受影響", "constraint", "rejection",
     "業務規則與驗證／前台自行註冊", "機台場館的前台暫不開放自行註冊（未來營運需求、開放時程未定）",
     [("站在一個機台場館的前台網域上", "尋找自行註冊入口", "找不到任何自行註冊功能；同一站台切到線上站台的前台則正常提供註冊入口，兩者形成對照")],
     "low", rc_true("規則已明確定義", "§264行/§343行/§803行")),

 req("機台帳號的投注不計入任何上層加盟商/代理的傭金與返傭計算基數", "機台帳號即使掛在某加盟商底下，該加盟商的加盟傭金與代理返傭計算基數，皆不含機台帳號產生的流水——這是機台帳號流水量級遠大於線上玩家、若不排除會使整間場館的流水被誤算成該加盟商業績的底層防護規則", "constraint", "rejection",
     "既有功能對機台帳號的排除規則／4.5-4.6", "4.5 / 4.6｜加盟傭金／代理返傭｜不適用，機台帳號的投注不計入任何上層的傭金基數",
     [("一台機台帳號掛在某加盟商站台底下且產生了投注流水", "計算該加盟商當期的加盟傭金與代理返傭", "該機台帳號的流水不計入計算基數，加盟商的傭金/返傭金額不因此增加")],
     "high", rc_true("規則已明確定義；不排除的後果在正本167-171行有明確說明：機台帳號若掛在某加盟商底下，整間店的流水都會算成他的業績", "§149行/§157行/§171行")),

 req("機台帳號的交易不會出現在優惠彩金審核佇列中", "機台帳號不適用任何優惠活動，其交易（開分/入金/洗分/出金）不會產生優惠彩金審核項目，不會出現在該審核佇列中", "constraint", "rejection",
     "既有功能對機台帳號的排除規則／3.3", "3.3｜優惠彩金審核｜不適用",
     [("一台機台帳號完成任意一筆金流交易（開分/入金/洗分/出金）", "檢視優惠彩金審核佇列", "該機台帳號的交易不會出現在審核佇列中")],
     "medium", rc_true("規則已明確定義", "§152行")),

 req("帳務管理出金設定TWD頁籤可設定機台場館的稽核倍數", "帳務管理 > 出金設定，於 TWD 頁籤可設定稽核倍數，供機台開分與入金依此倍數計算稽核門檻；預設值為 0 倍（即開分/入金不產生稽核門檻）", "functional", "success",
     "機台帳號的稽核／設定位置", "設定位置｜帳務管理 > 出金設定，於 TWD 頁籤設定稽核倍數；預設值｜0 倍——即開分與入金不產生稽核門檻，玩家隨時可洗分與出金",
     [("以 Admin 登入後台，站台切換至一個機台場館", "至帳務管理 > 出金設定 > TWD 頁籤", "可見稽核倍數設定欄位，預設值顯示為 0；修改數值並儲存後，該倍數即套用於後續的機台開分與入金計算")],
     "high", rc_true("規則已明確定義；預設0倍是刻意設計，正本201行明確警告調高倍數前務必評估現場衝擊，屬高風險設定項", "§195行/§196行/§201行/§784行")),

 req("場館設定的場次逾時時間欄位，操作員僅能檢視不可修改", "場館設定的「場次逾時時間」欄位，站長可調整，操作員僅能檢視、不可修改", "constraint", "rejection",
     "場館設定", "場次逾時時間｜機台仍有餘額但無任何交易與遊玩時，自動結束場次的時間長度；預設 1 小時，站長可調整，操作員唯讀",
     [("以操作員角色登入後台，站台切換至自身所屬的機台場館", "檢視該場館設定的「場次逾時時間」欄位", "該欄位為唯讀狀態，操作員無法修改其數值")],
     "medium", rc_true("規則已明確定義", "§218行")),

 req("洗分出金核實的核實與作廢動作須寫入後台操作紀錄", "洗分出金核實頁的核實（洗分/出金）與作廢（僅出金）動作，因屬現金相關且不可撤銷的操作，須寫入後台操作紀錄，記錄操作人員、時間與對象交易", "functional", "success",
     "對既有章節的影響／7.4 操作紀錄", "洗分出金核實（含收據核銷）與作廢屬現金相關操作且不可撤銷，須寫入後台操作紀錄（操作人員、時間、對象交易）",
     [("對一筆待核實的機台洗分或機台出金執行「核實」操作", "檢視後台操作紀錄", "該筆核實動作被記錄，內容含執行的操作人員、時間，以及對應的交易編號"),
      ("對一筆待核實的機台出金收據執行「作廢」操作", "檢視後台操作紀錄", "該筆作廢動作被記錄，內容含執行的操作人員、時間，以及對應的交易編號")],
     "medium", rc_true("規則已明確定義", "§791行")),
]
rm = {"spec_id": SID, "spec_version": SV, "requirements": reqs, "traceability": [{"requirement_id": r["requirement_id"], "spec_reference": r["spec_reference"]} for r in reqs]}
sa = {"spec_id": SID, "spec_version": SV, "content_hash": H,
      "summary": "實體機台（正本），975行，為六個既有開發包（ACCOUNT/SITELIST/CASHFLOW/TXLOG/CASHOUT/DAILYREPORT/PLATFORMRULE，共7個spec_id）"
                 "的單一依據，各包為抽錄，重疊部分如有出入以本檔為準。經背景 Explore agent 逐段比對七份既有 requirements.yaml，"
                 "確認絕大部分內容（機台帳號排除規則整表、場館設定、核心貨幣模型、四種金流、場次規則、未成立原因、洗分出金核實、"
                 "場館日結報表、機台憑證、重設密碼、操作員權限大表、後台選單顯示規則、遊戲更新預設停用等）皆已被七包完整且正確涵蓋，"
                 "數值與規則逐一核對一致，不重複測。另有已知的正本與現況不一致之處（手動取消功能存在與否等）已另開 Clarification "
                 "（CLR-CASHFLOW-003）或屬於既有 requirement 已正確反映現況、僅正本文字待更新，不在本次 RequirementModel 範圍。"
                 "本次僅針對七包完全沒有對應 Requirement 涵蓋到的六項真正新內容建立 Requirement。",
      "scope": {"in_scope": ["機台場館前台不開放自行註冊", "機台帳號流水不計入上層加盟傭金/代理返傭基數（底層規則本身）",
                              "機台帳號交易不進優惠彩金審核佇列（底層規則本身）", "出金設定TWD頁籤稽核倍數設定操作本身",
                              "場次逾時時間欄位操作員唯讀", "洗分出金核實的核實/作廢寫入操作紀錄"],
                "out_of_scope": ["機台帳號排除規則整表、場館設定、核心貨幣模型、四種金流、場次規則、未成立原因、洗分出金核實核心流程、"
                                 "場館日結報表、機台憑證、重設密碼、操作員權限大表、後台選單顯示規則、遊戲更新預設停用——已由七份既有 "
                                 "requirements.yaml 完整涵蓋且數值一致",
                                 "機台前台「僅顯示當前進行中場次」的顯示隔離規則（正本500/539/835行）——發生在機台前台遊戲畫面（玩家/店員"
                                 "操作介面），不在 QAOS 現有七包負責的後台 admin 系統範圍內",
                                 "正本與現況的已知落差（手動取消功能、admin根層站台類型例外、重送次數/來源欄位未實作、交易紀錄查詢頁篩選器"
                                 "UI）——分別已開 Clarification（CLR-CASHFLOW-003）或已由既有 requirement 正確反映現況，正本文字本身的更新"
                                 "不在 QAOS RequirementModel 職責範圍"]},
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
