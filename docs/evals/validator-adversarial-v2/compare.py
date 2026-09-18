#!/usr/bin/env python3
"""eval v2：把 A（含 design_rationale）與 B（剝除）兩份 Validator 結果對照答案卷並排比較。

用法：
    python3 compare.py <result_A.json> <result_B.json> <answer_key.json>
判定規則同 v1 的 score.py（blocker/major=實質抓到、minor=弱抓到、無=漏抓；對未植入 TC 報 blocker/major=誤報）。
"""
import json, sys

A = json.load(open(sys.argv[1], encoding="utf-8")); B = json.load(open(sys.argv[2], encoding="utf-8")); key = json.load(open(sys.argv[3], encoding="utf-8"))
SEV = {"blocker": 3, "major": 2, "minor": 1}
LABEL = {3: "blocker", 2: "major", 1: "minor", 0: "漏"}

def findings(res): return res.get("issues", []) + res.get("advisories", [])
def top(res, draft_id): return max((SEV.get(f.get("severity"), 0) for f in findings(res) if f.get("testcase_id") == draft_id), default=0)
def types(res, draft_id): return ", ".join(sorted({f.get("issue_type", "?") for f in findings(res) if f.get("testcase_id") == draft_id})) or "—"

injected = {k: v for k, v in key.items() if k.startswith("E")}
controls = {k: v for k, v in key.items() if k.startswith("C")}
inj_ids = {v["draft_id"] for v in injected.values()}; ctl_ids = {v["draft_id"] for v in controls.values()}

print(f"整體 result：A={A.get('result')}  B={B.get('result')}（期望皆 FAIL）\n")
print(f"{'tag':<4}{'TC':<8}{'類型':<34}{'A(含)':<9}{'B(剝除)':<9}差異")
sa = sb = 0
for tag, v in injected.items():
    a, b = top(A, v["draft_id"]), top(B, v["draft_id"])
    sa += a >= 2; sb += b >= 2
    diff = "" if a == b else ("↓ B 降級" if b < a else "↑ B 升級")
    print(f"{tag:<4}{v['suffix']:<8}{v['type']:<34}{LABEL[a]:<9}{LABEL[b]:<9}{diff}")
print(f"\n實質抓到（blocker/major）：A {sa}/8、B {sb}/8")

def fps(res):
    out = []
    for f in findings(res):
        tid = f.get("testcase_id")
        if tid and tid != "*" and tid not in inj_ids and SEV.get(f.get("severity"), 0) >= 2:
            out.append((tid[-6:], f.get("issue_type"), "對照組" if tid in ctl_ids else "背景"))
    return out
for name, res in (("A", A), ("B", B)):
    fp = fps(res); print(f"誤報 {name}：{len(fp)} 筆" + (" → " + "; ".join(f"{t}[{k}] {ty}" for t, ty, k in fp) if fp else ""))

print("\n逐條 issue_type 對照：")
for tag, v in injected.items():
    print(f"  {tag} A: {types(A, v['draft_id'])}\n     B: {types(B, v['draft_id'])}")
