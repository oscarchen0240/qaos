#!/usr/bin/env python3
"""把 Validator 的 JSON 審查結果對照答案卷，算召回／誤報。

用法：
    python3 score.py <validator_result.json> <answer_key.json>

機械判定規則：
- 植入點 E*：issues 或 advisories 中有 testcase_id 指向該 draft_id 者算「命中」；severity 為 blocker/major 算「實質抓到」，
  只有 minor 算「弱抓到」，完全沒有算「漏抓」。issue 描述是否真的對應錯誤本質，由人工另行核對。
- 對照組 C*：若有 blocker/major 指向它 → 誤報。
- 未植入的其他 TC：若有 blocker/major 指向它 → 誤報。
- 整體 result 應為 FAIL。
"""
import json, sys

res = json.load(open(sys.argv[1], encoding="utf-8")); key = json.load(open(sys.argv[2], encoding="utf-8"))
SEV = {"blocker": 3, "major": 2, "minor": 1}
findings = [dict(i, _src="issues") for i in res.get("issues", [])] + [dict(i, _src="advisories") for i in res.get("advisories", [])]

def hits(draft_id):
    return [f for f in findings if f.get("testcase_id") == draft_id]

injected = {k: v for k, v in key.items() if k.startswith("E")}
controls = {k: v for k, v in key.items() if k.startswith("C")}
injected_ids = {v["draft_id"] for v in injected.values()}

print(f"整體 result：{res.get('result')}（期望 FAIL）")
print()
print(f"{'tag':<4}{'TC':<8}{'類型':<38}{'判定':<8}{'最高 severity':<14}命中的 issue_type")
strong = weak = miss = 0
for tag, v in injected.items():
    h = hits(v["draft_id"]); top = max((SEV.get(f.get("severity"), 0) for f in h), default=0)
    verdict = "實質抓到" if top >= 2 else ("弱抓到" if top == 1 else "漏抓")
    strong += top >= 2; weak += top == 1; miss += top == 0
    types = ", ".join(sorted({f.get("issue_type", "?") for f in h})) or "—"
    sev = {3: "blocker", 2: "major", 1: "minor", 0: "—"}[top]
    print(f"{tag:<4}{v['suffix']:<8}{v['type']:<38}{verdict:<8}{sev:<14}{types}")

print()
print(f"召回：實質抓到 {strong}/8、弱抓到 {weak}/8、漏抓 {miss}/8")

fp = []
for tag, v in controls.items():
    h = [f for f in hits(v["draft_id"]) if SEV.get(f.get("severity"), 0) >= 2]
    if h: fp.append((tag, v["suffix"], [f.get("issue_type") for f in h]))
for f in findings:
    tid = f.get("testcase_id")
    if tid and tid != "*" and tid not in injected_ids and tid not in {v["draft_id"] for v in controls.values()} and SEV.get(f.get("severity"), 0) >= 2:
        fp.append(("other", tid[-6:], [f.get("issue_type")]))
print(f"誤報（對未植入 TC 報 blocker/major）：{len(fp)} 筆" + (" → " + "; ".join(f"{t}:{s} {ty}" for t, s, ty in fp) if fp else ""))
print()
print("門檻（v1）：實質抓到 ≥ 7/8 且 誤報 = 0 且 result = FAIL")
ok = strong >= 7 and not fp and res.get("result") == "FAIL"
print("結果：", "通過" if ok else "未通過")
