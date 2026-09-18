#!/usr/bin/env python3
"""直接修正 REQ-SITELIST-002 的確認紀錄：獨立 Validator 第二輪審查發現既有 history 有時序矛盾
（記錄時間 2026-09-14 早於所述確認日期 2026-09-15，且缺乏 CLR 交叉引用），Oscar 於 2026-09-17
對話中直接確認這條「admin 例外」規則是新設計、確實存在，不是資料錯誤。補一筆正式 history 記錄取代
先前存疑的記載，並在 statement 加註新的確認來源。"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store

p = store.requirements_path('SPEC-SITELIST-001', '0.4')
d = store.load(p)
for r in d['requirements']:
    if r['requirement_id'] == 'REQ-SITELIST-002':
        r['statement'] = (
            '站台類型於主站台（根層）選定，子站台一律與主站台同類型，不可個別選擇；例外：當上層站台為 admin'
            '（最上層根站台）時，此強制跟隨規則不適用——底下子站台可自由選擇機台或線上類型，核心貨幣依所選'
            '類型連動建立（此為新設計規則，已由 Oscar 於對話中直接確認為真，取代先前記錄中日期'
            '矛盾、來源不明的確認記載，確認時間見本條 history 最後一筆的 at 欄位）'
        )
        at = store.now()
        r['history'].append({
            'at': at,
            'from_status': 'ACTIVE',
            'to_status': 'ACTIVE',
            'by': 'oscarchen@blockaction.tech',
            'trigger': (
                f'product_confirmation_{at[:10]}：Oscar 直接於對話中確認 admin 例外規則為新設計、非資料錯誤'
                '（修正先前 2026-09-14 記錄與所述 2026-09-15 確認日期矛盾、且缺乏 CLR 交叉引用的問題，此次'
                '以直接對話確認取代，trigger 日期與本筆 at 時間戳同步產生，避免重蹈先前的日期矛盾）'
            ),
        })
        break
else:
    raise SystemExit('REQ-SITELIST-002 not found')

store.save(p, d)
print('saved', p)
