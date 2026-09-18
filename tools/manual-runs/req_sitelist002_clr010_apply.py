#!/usr/bin/env python3
"""把 CLR-SITELIST-010 的正式回覆套用進 REQ-SITELIST-002：admin 例外規則是 PM 最終決定、
已開發完成上線，不是待定/臆測。取代先前只靠對話直接確認、缺乏 CLR 交叉引用的記錄方式，
補齊跟本檔案其他確認案例（如 CLR-SITELIST-008/009）一致的稽核強度。"""
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
            '類型連動建立（此為 PM 最終決定，已開發完成並上線，非待定或實驗性設計；正式確認見 CLR-SITELIST-010，'
            'spec.md 原文尚未反映此例外，屬 spec 文件落後於實際已上線行為的已知落差）'
        )
        at = store.now()
        r['history'].append({
            'at': at,
            'from_status': 'ACTIVE',
            'to_status': 'ACTIVE',
            'by': 'oscarchen@blockaction.tech',
            'trigger': (
                f'clarification_applied_CLR-SITELIST-010（{at[:10]}）：admin 例外規則正式確認為 PM 最終決定、'
                '已開發完成上線，取代先前 2026-09-14/09-16 兩筆僅靠對話確認、缺乏 CLR 交叉引用的記錄'
            ),
        })
        break
else:
    raise SystemExit('not found')
store.save(p, d)
print('saved, history entries now:', len(r['history']))
