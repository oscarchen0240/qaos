#!/usr/bin/env python3
"""套用CLR-SITELIST-011：鏈上錢包管理與站台核心貨幣是互不相依的獨立概念（鏈上錢包管理是platform級
幣種啟用/禁用的風險控管開關，跟站台建立時依類型連動的核心貨幣欄位完全無關）。取代先前的範圍待確認註記，
AC-SITELIST-0023不再需要標記為exploratory——「不需預先啟用」只是在說明兩個系統互不閘門，不是一個
需要獨立驗證的技術斷言。"""
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
                    '類型連動建立（例如選機台則連動啟用 TWD）。此連動建立與「鏈上錢包管理」（platform級'
                    '幣種出入金啟用/禁用的風險控管開關）完全無關、不互相依賴——已由 CLR-SITELIST-011 '
                    '正式確認兩者為互不相依的獨立概念，核心貨幣連動建立不需要、也不會檢查鏈上錢包管理的'
                    '任何狀態'
                )
                break
        break
else:
    raise SystemExit('not found')
store.save(p, d)
print('updated')
