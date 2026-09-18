#!/usr/bin/env python3
"""eval v2 對照組 B：從 TestCaseDraft 剝除每條 TC 的 design_rationale，其餘完全不動。

對應 agents/test-validator.yaml 的 forbidden_actions：
  「讀取 Test Designer 的推理過程 / TestDesignReport.self_check 以外的內部說明（避免同源偏誤；只讀 Draft、Report coverage matrix、Spec、Requirement）」

剝除範圍刻意限定為 design_rationale 這一個欄位：它是「Designer 的推理過程」的直接載體；
Report 的 coverage_matrix / technique_summary / self_check 是結構化資料，不是推理，保持不動，以確保 A/B 只差單一變因。

用法：
    python3 strip_rationale.py <draft.yaml>      # 原地改寫
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
from tools.qaos import store

p = pathlib.Path(sys.argv[1]); d = store.load(p)
n = 0
for tc in d["payload"]["testcases"]:
    if "design_rationale" in tc: tc.pop("design_rationale"); n += 1
store.save(p, d)
print(f"已從 {n} 條 TC 移除 design_rationale → {p}")
