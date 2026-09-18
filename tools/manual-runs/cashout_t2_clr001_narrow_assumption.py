#!/usr/bin/env python3
"""RUN-20260918-003：依CLR-CASHOUT-001（PM 2026-09-18確認：操作員無場館切換權限是過去已規劃
定案的既有設計，切換場館設定在後台管理員系統，僅站長/admin有此權限，非待PLATFORMRULE補完
才算數），收斂AC-CASHOUT-0251/0252/0291三條exploratory TC的assumption揭露範圍：
拿掉『規則本身定義於PLATFORMRULE、尚未完成Phase 3』這個已被PM推翻的框架，
只保留『測試環境是否已備妥符合此限制的操作員帳號』這個單純的環境設定事實。"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.qaos import store, ids

RUN = "RUN-20260918-003"
OLD_TCD = "ART-TCD-01M2R6NEJ8SFRQWXWDBMMXRVAB"
OLD_TDR = "ART-TDR-01M2R6NEK3JQ7QXJ2S2VGTV2FV"
A = "agent-test-designer"

tcd = store.load(store.ROOT / "artifacts" / "test-design" / RUN / f"{OLD_TCD}.yaml")
tdr = store.load(store.ROOT / "artifacts" / "test-design" / RUN / f"{OLD_TDR}.yaml")

TARGETS = {
    "TC-DRAFT-01M2R6NEJ7BJH8707E9B1MM8SH": "REQ-CASHOUT-025",
    "TC-DRAFT-01M2R6NEJ7KF48PP8QT6VDDAW6": "REQ-CASHOUT-025",
    "TC-DRAFT-01M2R6NEJ73CPBHS75XK9YDRNZ": "REQ-CASHOUT-029",
}
NEW_TEXT = (
    "依CLR-CASHOUT-001（2026-09-18 PM確認）：操作員完全不具備切換場館的權限，此為過去已規劃"
    "定案的既有設計，場館切換的設定屬於後台管理員系統的範疇，僅站長與admin具備此權限——規則"
    "本身已定案，非待開發包⑥ PLATFORMRULE補完才算數。本TC唯一待確認的是測試環境層面的事實："
    "當下環境是否已存在一個確實依此規則設定好場館歸屬的操作員帳號、後端是否已如SPEC-CASHOUT-001"
    "所述拒絕跨場館請求，需環境負責人協助確認後才能視為可重複執行的既定案例。"
)

changed = []
for t in tcd["payload"]["testcases"]:
    if t["draft_id"] in TARGETS:
        t["assumptions"] = [{
            "text": NEW_TEXT, "requirement_id": TARGETS[t["draft_id"]], "needs_human_confirmation": True,
        }]
        changed.append(t["draft_id"])

assert len(changed) == 3, changed

# CASHOUT run 已在 T4（APR-0118）等待人工核准，T2/T3 皆已 DONE/VALID，此為 CLR 驅動的措辭
# 精準化（不影響已通過驗證的設計本身），比照 SITELIST CLR-012 對 requirements.yaml 的處理方式，
# 直接原地修正已 VALID 的 artifact 內容，不重跑整個 T2→T3 engine 流程。
tcd.setdefault("history", []).append({
    "at": store.now(), "by": A,
    "note": "依CLR-CASHOUT-001原地收斂AC-CASHOUT-0251/0252/0291三條TC的assumption文字",
})
tdr.setdefault("history", []).append({
    "at": store.now(), "by": A,
    "note": (
        "依CLR-CASHOUT-001（2026-09-18 PM確認）收斂三條TC的assumption：移除『規則定義於"
        "PLATFORMRULE、尚未完成Phase 3』的過時框架，只保留『測試環境是否已備妥符合限制的"
        "操作員帳號』這個單純環境設定事實的待確認範圍"
    ),
})

store.save(store.ROOT / "artifacts" / "test-design" / RUN / f"{OLD_TCD}.yaml", tcd)
store.save(store.ROOT / "artifacts" / "test-design" / RUN / f"{OLD_TDR}.yaml", tdr)
print("patched in place:", OLD_TCD, OLD_TDR)
print("changed testcases:", changed)
