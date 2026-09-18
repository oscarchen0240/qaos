#!/usr/bin/env python3
"""再次修正 REQ-MEMBER-005 / AC-MEMBER-007 / AC-MEMBER-008（version 2 → 3）。
Oscar 2026-09-16 進一步更正：先前(version 2)引入的『扣除出金手續費後淨額』機制是錯的說法。
最終確認：出金門檻只看「提領申請金額本身」是否 >= 10 USDT（含），與出金手續費、主錢包扣款完全無關。
手續費機制（提領金額 x 10% 從主錢包額外扣除、不影響會員實際到手金額）是另一件獨立的事，
不影響「能不能出金」這個門檻判斷，本次修正把手續費相關描述整個移除。
同時修正version 1遺留的rejection_contract.description方向錯誤（誤導方向為『大於』而非『大於等於』）。"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store

SID, SV = "SPEC-MEMBER-001", "0.2"
path = store.requirements_path(SID, SV)
d = store.load(path)

for r in d["requirements"]:
    if r["requirement_id"] != "REQ-MEMBER-005":
        continue

    r["version"] = 3
    r["statement"] = (
        "會員申請出金時，「提領申請金額」本身須大於等於 10 USDT 才可出金；門檻判斷對象是會員實際填寫送出的提領金額，"
        "與後台帳務資訊「可提領餘額」欄位的精確數值無關（只要可提領餘額足以支應本次提領金額即可），也與出金手續費計算無關。"
        "spec §2.1.4原文僅寫「可提領餘額...須大於10 USDT方可申請出金」，字面上用「大於」(不含10)且以「可提領餘額」為判斷對象，"
        "與實際產品行為（大於等於/含10、判斷對象是提領申請金額本身）有落差，已由 Oscar 2026-09-16 以實際操作確認並多次更正，"
        "建議另案更新spec原文。"
    )
    r["acceptance_criteria"] = [
        {
            "ac_id": "AC-MEMBER-007",
            "given": "會員可提領餘額足夠支應提領金額，提領申請金額本身為 9.99 USDT（邊界值，未達 10 USDT 門檻）",
            "when": "送出提領申請",
            "then": "不可出金——提領申請金額本身未達 10 USDT 門檻",
        },
        {
            "ac_id": "AC-MEMBER-008",
            "given": "會員可提領餘額足夠支應提領金額，提領申請金額本身恰為 10.00 USDT（邊界值，剛好達到門檻）",
            "when": "送出提領申請",
            "then": "可正常出金，申請成功送出——提領申請金額本身剛好達到 10 USDT 門檻（含）",
        },
    ]
    r["rejection_contract"]["description"] = (
        "規則已明確定義，是個精確的數值邊界規則，容易被誤實作成「大於」(不含10)而非「大於等於」(含10)，值得用邊界值驗證"
        "（此描述已於2026-09-16修正方向：原文誤把「大於等於」當成錯誤實作，實際上「大於等於」才是正確方向）"
    )
    r["history"].append({
        "at": store.now(),
        "from_status": "ACTIVE",
        "to_status": "ACTIVE",
        "by": "oscarchen@blockaction.tech",
        "trigger": d["source_artifact_id"],
        "note": (
            "再次修正AC-MEMBER-007/008（version 2→3）：Oscar 2026-09-16當天先確認『門檻判斷對象是提領金額扣除出金手續費後淨額』(version 2)，"
            "隨後又更正：出金手續費從主錢包額外扣除、不影響到手金額，且門檻判斷對象是『提領申請金額本身』(不涉及手續費)。"
            "本次version 3移除所有手續費相關描述，改為單純的『提領申請金額本身>=10』門檻。同時修正version 1遺留的rejection_contract.description"
            "方向錯誤（原文誤導方向為『大於』才對、『大於等於』是常見錯誤實作，實際相反）。"
        ),
    })

store.save(path, d)
print(f"REQ-MEMBER-005 已更新至 version {[r['version'] for r in d['requirements'] if r['requirement_id']=='REQ-MEMBER-005'][0]}")
print(path)
