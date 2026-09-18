#!/usr/bin/env python3
"""獨立Validator第五輪指出：AC-SITELIST-0023裡「不需admin自身的鏈上錢包管理預先啟用該幣別」這句話，
CLR-SITELIST-010只解決了「型別可自由選擇」那半句，沒有涵蓋這句更具體的技術斷言，唯一出處仍是
RequirementModel自己的AC文字。在Oscar就這句話本身給出明確答覆前，先誠實標註範圍，避免誤以為
CLR-010已完全解決AC-0023的所有爭議。"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store

p = store.requirements_path('SPEC-SITELIST-001', '0.4')
d = store.load(p)
for r in d['requirements']:
    if r['requirement_id'] == 'REQ-SITELIST-002':
        for ac in r['acceptance_criteria']:
            if ac['ac_id'] == 'AC-SITELIST-0023':
                ac['then'] = (
                    ac['then'] + '【範圍註記：本then子句中「不需admin自身的鏈上錢包管理預先啟用該幣別」'
                    '這句技術斷言，CLR-SITELIST-010尚未涵蓋（CLR-010只確認了型別可自由選擇這部分），'
                    '目前唯一出處是本AC文字本身，仍待另案確認；對應TC已誠實標記為exploratory】'
                )
                break
        break
else:
    raise SystemExit('not found')
store.save(p, d)
print('annotated')
