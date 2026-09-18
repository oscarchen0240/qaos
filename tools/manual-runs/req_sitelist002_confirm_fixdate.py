#!/usr/bin/env python3
"""修正剛剛寫入 REQ-SITELIST-002 的 history 最後一筆：trigger 字串裡硬寫的日期(2026-09-17)
跟 at 欄位實際的系統時間戳(store.now()產生，落在2026-09-16)不一致，重蹈了本來要修正的
「日期矛盾」問題。改成直接從 at 欄位動態取日期，兩者永遠同步。"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store

p = store.requirements_path('SPEC-SITELIST-001', '0.4')
d = store.load(p)
for r in d['requirements']:
    if r['requirement_id'] == 'REQ-SITELIST-002':
        last = r['history'][-1]
        assert last['trigger'].startswith('product_confirmation_2026-09-17'), last['trigger']
        date_str = last['at'][:10]
        last['trigger'] = (
            f'product_confirmation_{date_str}：Oscar 直接於對話中確認 admin 例外規則為新設計、非資料錯誤'
            '（修正先前 2026-09-14 記錄與所述 2026-09-15 確認日期矛盾、且缺乏 CLR 交叉引用的問題，此次'
            '以直接對話確認取代，trigger 日期與本筆 at 時間戳同步產生，避免重蹈先前的日期矛盾）'
        )
        r['statement'] = r['statement'].replace('已由 Oscar 於 2026-09-17 對話中直接確認為真', '已由 Oscar 於對話中直接確認為真（確認時間見 history 最後一筆的 at 欄位）')
        break
else:
    raise SystemExit('not found')
store.save(p, d)
print('fixed trigger date to match at:', last['at'])
