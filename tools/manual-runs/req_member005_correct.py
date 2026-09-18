#!/usr/bin/env python3
"""修正 REQ-MEMBER-005 / AC-MEMBER-007 / AC-MEMBER-008：
Oscar 2026-09-16 確認實際門檻機制與spec原文（僅定義『可提領餘額須大於10 USDT』）不同：
真正的門檻是「提領申請金額 扣除出金手續費（後台鏈上錢包管理設定的%）後」是否 >=10（含），
而非直接對「可提領餘額」欄位本身判斷、也不是「大於10」（不含10）。
spec.md §2.1.4從未提及出金手續費會計入此門檻判斷，這是spec與實際產品行為的落差。
確認範例（Oscar 2026-09-16）：手續費10%時，申請提領10 USDT→不可出金；申請提領11 USDT→可出金，會員實際到手10 USDT。"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store

SID, SV = "SPEC-MEMBER-001", "0.2"
path = store.requirements_path(SID, SV)
d = store.load(path)

for r in d["requirements"]:
    if r["requirement_id"] != "REQ-MEMBER-005":
        continue

    r["version"] = 2
    r["statement"] = (
        "會員申請出金時，「提領申請金額」扣除出金手續費（後台鏈上錢包管理設定的百分比）後的淨額，"
        "須大於等於 10 USDT 才可出金；門檻判斷對象是扣除手續費後的淨額，不是後台帳務資訊「可提領餘額」欄位本身。"
        "spec §2.1.4原文僅寫「可提領餘額...須大於10 USDT方可申請出金」，未提及出金手續費會計入此門檻判斷，"
        "此為spec原文與實際產品行為的落差（已由 Oscar 2026-09-16 以實際操作範例確認），建議另案更新spec原文。"
    )
    r["acceptance_criteria"] = [
        {
            "ac_id": "AC-MEMBER-007",
            "given": "出金手續費設定為 10%，會員申請提領 10 USDT（扣手續費後淨額未達 10 USDT）",
            "when": "送出提領申請",
            "then": "不可出金——扣除手續費後的淨額低於 10 USDT 門檻",
        },
        {
            "ac_id": "AC-MEMBER-008",
            "given": "出金手續費設定為 10%，會員申請提領 11 USDT（扣手續費後淨額恰為 10 USDT）",
            "when": "送出提領申請",
            "then": "可正常出金，會員實際到手 10 USDT——扣除手續費後淨額剛好達到 10 USDT 門檻（含）",
        },
    ]
    r["history"].append({
        "at": store.now(),
        "from_status": "ACTIVE",
        "to_status": "ACTIVE",
        "by": "oscarchen@blockaction.tech",
        "trigger": d["source_artifact_id"],
        "note": (
            "修正AC-MEMBER-007/008：原定義誤把門檻判斷對象設為『可提領餘額』欄位本身、且門檻方向為『大於10』(不含)。"
            "Oscar 2026-09-16確認實際機制：門檻判斷對象是『提領申請金額扣除出金手續費(後台鏈上錢包管理設定%)後的淨額』，"
            "且門檻含10(大於等於)。此為spec原文未揭露的產品行為，spec.md §2.1.4本身未修訂，僅更正RequirementModel與statement中誠實揭露此落差。"
        ),
    })

store.save(path, d)
print(f"REQ-MEMBER-005 已更新至 version {[r['version'] for r in d['requirements'] if r['requirement_id']=='REQ-MEMBER-005'][0]}")
print(path)
