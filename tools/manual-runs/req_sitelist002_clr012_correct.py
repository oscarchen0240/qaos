#!/usr/bin/env python3
"""套用CLR-SITELIST-012：修正CLR-011「鏈上錢包管理與核心貨幣完全無關」的錯誤結論。
正確機制：鏈上錢包管理是每站台獨立一份、事後可調整的幣種出入金開關；核心貨幣是站台建立時定案、
不可更改也不能關閉的屬性；新站台建立時核心貨幣連動建立的同時會自動在該站台自己的鏈上錢包管理
啟用對應幣別（不需要admin自身的鏈上錢包管理預先啟用）。此修正有既有ACTIVE的TC-SITELIST-063
（早於本次CLR討論即存在）獨立佐證。"""
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
                    '站台類型欄位可自由選擇機台或線上，不強制跟隨 admin 自身的站台類型；核心貨幣依所選'
                    '類型連動建立（例如選機台則連動啟用 TWD）且此欄位不可更改、不能於後台關閉。與此同時，'
                    '該新站台自己的「鏈上錢包管理」（每站台獨立一份、可事後調整的幣種出入金開關）會自動'
                    '連動啟用對應幣別；此連動不需要 admin 自身的鏈上錢包管理預先啟用該幣別（即不依賴上層/'
                    'admin 的狀態）。【CLR-SITELIST-012已修正】先前CLR-SITELIST-011誤判兩者「完全無關」，'
                    '實際上兩者性質不同（核心貨幣不可變 vs 鏈上錢包管理可調整）但確有連動關係，已由既有'
                    'ACTIVE的TC-SITELIST-063（早於本次CLR討論即存在）獨立佐證修正。'
                )
                break
        break
else:
    raise SystemExit('not found')
store.save(p, d)
print('corrected')
