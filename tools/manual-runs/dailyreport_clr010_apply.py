#!/usr/bin/env python3
"""套用 CLR-DAILYREPORT-010 PM 回覆 A（2026-09-22）：已兌現金額以收據日歸屬。
REQ-DAILYREPORT-011 statement 補收據日基準、新增 AC-0115（跨日兌現歸收據日）；REQ-012 現金淨收 statement 註明含未來付現。"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store
SID, SV, BY = "SPEC-DAILYREPORT-001", "0.1", "oscarchen@blockaction.tech"
p = store.requirements_path(SID, SV); d = store.load(p)
for r in d["requirements"]:
    if r["requirement_id"] == "REQ-DAILYREPORT-011":
        assert not any(a["ac_id"] == "AC-DAILYREPORT-0115" for a in r["acceptance_criteria"])
        r["statement"] = r["statement"].rstrip("。") + "。已兌現／未兌現皆以「收據日」歸屬：已兌現＝當日出金的收據中已核實（核銷）者的金額合計，不論實際付現是哪一天（CLR-DAILYREPORT-010 PM 定案 A，2026-09-22）；因此單列內 收據金額＝已兌現＋未兌現（＋已作廢，呈現方式見 CLR-DAILYREPORT-011）。"
        r["acceptance_criteria"].append({"ac_id": "AC-DAILYREPORT-0115", "given": "9/10 出金收據 1000，9/12 於洗分出金核實頁核銷（付現）", "when": "分別查看 9/10 與 9/12 的列", "then": "9/10 列：收據 1000、已兌現 1000、未兌現 0；9/12 列：收據 0、已兌現 0（已兌現歸收據日，不歸兌現日）"})
        r.setdefault("history", []).append({"at": store.now(), "from_status": "ACTIVE", "to_status": "ACTIVE", "by": BY, "trigger": "clarification_applied_CLR-DAILYREPORT-010：已兌現以收據日歸屬；新增 AC-0115 跨日兌現案例"})
    if r["requirement_id"] == "REQ-DAILYREPORT-012":
        r["statement"] = r["statement"].rstrip("。") + "。註：已兌現以收據日歸屬（CLR-DAILYREPORT-010 A），故現金淨收含未來才付現的收據金額，為推算值、非當日實際現金增減（spec 註解「代表場館端當日現金應該增減多少」應依此理解）。"
        r.setdefault("history", []).append({"at": store.now(), "from_status": "ACTIVE", "to_status": "ACTIVE", "by": BY, "trigger": "clarification_applied_CLR-DAILYREPORT-010：現金淨收語意註記"})
store.save(p, d); print("REQ-011 +AC-0115, REQ-012 note")
