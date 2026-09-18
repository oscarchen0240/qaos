#!/usr/bin/env python3
"""修正 REQ-SITELIST-001 v0.4 requirements.yaml 裡兩條 ambiguity 欄位的 schema 違規：
`resolved_note` 不是 Ambiguity schema 允許的欄位（只允許 level/description/options/resolved_by_approval），
發現於本次 bin/qaos validate 才注意到，屬於先前手動編輯遺留、非本次修訂新增的問題。
把 resolved_note 的內容併入 description 保留稽核資訊，移除不合規欄位。"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store

p = store.requirements_path('SPEC-SITELIST-001', '0.4')
d = store.load(p)
fixed = []
for r in d['requirements']:
    amb = r.get('ambiguity')
    if amb and 'resolved_note' in amb:
        note = amb.pop('resolved_note')
        amb['description'] = amb['description'] + '【已解決】' + note
        fixed.append(r['requirement_id'])

store.save(p, d)
print('fixed:', fixed)
