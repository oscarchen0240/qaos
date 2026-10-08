"""Spec 進度（匯流圖）與 DoD：把「Phase 2 run」「Phase 3 run」「交叉整合」「匯出 final」接成一條線。

QAOS 的 workflow 只有 T1–T5；每份 spec 實際走法是：
  Phase 2 run（人扮 agent 腳本）─┐
  Phase 3 run（qaos-test-designer）─┴→ 交叉整合（QA session 自己比對＋testcase-revision run）→ 匯出 final
整合與匯出不是 run 裡的 task，所以這裡用留痕當證據（皆唯讀）：
  - docs/phase3-shadow-test/<date>-<slug>-shadow-test.md  （整合紀錄；內文 **Run**：RUN-… 指出哪個是 Phase 3 run）
  - runs/*/run.yaml workflow_id=testcase-revision           （修訂既有 Phase 2 TC）
  - testcases/final/<AREA>-final*                            （最終交付物）
DoD 三項（Oscar 2026-09-17 定）：1 整合完成（Phase 3 run COMPLETED、T4 已決定、修訂 run 都結束）2 shadow-test 文件 3 final 檔已產出且不落後 registry。
Phase 判定：shadow 文件點名的 run 為 Phase 3；同 spec 更早的 COMPLETED run 為 Phase 2；沒有文件時，最早的 COMPLETED run 視為 Phase 2、其後的視為 Phase 3。
"""
from __future__ import annotations

import datetime as dt
import pathlib
import re
import time

from ..config import PROJECT_ROOT
from . import outputs as out_svc
from . import runs as run_svc

SHADOW_DIR = PROJECT_ROOT / "docs" / "phase3-shadow-test"
_cache: tuple[tuple, dict] | None = None


def _ts(s: str | None) -> float | None:
    if not s:
        return None
    try:
        return dt.datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _iso(t: float | None) -> str | None:
    return dt.datetime.fromtimestamp(t, dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z") if t else None


def spec_key(spec_id: str | None) -> str | None:
    """SPEC-BONUSCCY-002 → BONUSCCY-002；SPEC-CASHFLOW-001 → CASHFLOW-001"""
    m = re.match(r"SPEC-([A-Z0-9_]+-\d+)", spec_id or "")
    return m.group(1) if m else None


def _area(key: str) -> str:
    return key.rsplit("-", 1)[0]


def _matches_key(name: str, key: str) -> bool:
    """final 群組 key／shadow slug 與 spec key 的對應：BONUSCCY-002 ↔ 'BONUSCCY-002'；CASHFLOW-001 ↔ 'CASHFLOW' 或 'CASHFLOW-001'"""
    n = name.upper()
    return n == key or (key.endswith("-001") and n == _area(key))


def _shadow_docs() -> list[dict]:
    out = []
    if not SHADOW_DIR.exists():
        return out
    for p in sorted(SHADOW_DIR.glob("*-shadow-test.md")):
        m = re.match(r"(\d{4}-\d{2}-\d{2})-(.+)-shadow-test\.md$", p.name)
        if not m:
            continue
        run_ids = []
        try:
            head = p.read_text(encoding="utf-8")[:4000]
            run_ids = re.findall(r"\bRUN-\d{8}-\d{3,}\b", head)   # 流水號是最小三位，單日第 1000 筆起四位
        except OSError:
            pass
        out.append({"path": str(p.relative_to(PROJECT_ROOT)), "date": m.group(1), "slug": m.group(2), "mtime": p.stat().st_mtime, "run_ids": run_ids})
    return out


def _signature() -> tuple:
    docs = tuple((p.name, p.stat().st_mtime) for p in SHADOW_DIR.glob("*.md")) if SHADOW_DIR.exists() else ()
    fin = tuple((q.name, q.stat().st_mtime) for q in out_svc.FINAL_DIR.iterdir() if q.is_file()) if out_svc.FINAL_DIR.exists() else ()
    return (run_svc.signature(), docs, fin)


def build() -> dict:
    """回 {"specs": [...], "run_phase": {run_id: "phase2"|"phase3"|"revision"|...}}，帶快取。"""
    global _cache
    sig = _signature()
    if _cache and _cache[0] == sig:
        return _cache[1]
    runs = run_svc.all_runs()
    docs = _shadow_docs()
    groups = {g["key"]: g for g in out_svc.scan()}
    now = time.time()

    by_spec: dict[str, list[dict]] = {}
    for r in runs:
        if r.get("workflow_id") != "spec-to-testcase":
            continue
        k = spec_key(r.get("spec_id"))
        if k:
            by_spec.setdefault(k, []).append(r)
    revisions = [r for r in runs if r.get("workflow_id") == "testcase-revision"]
    run_phase: dict[str, str] = {r["run_id"]: "revision" for r in revisions}
    specs = []
    for key, rs in sorted(by_spec.items()):
        rs = sorted(rs, key=lambda r: r.get("_created") or 0)
        doc = next((d for d in docs if _matches_key(d["slug"], key)), None)
        completed = [r for r in rs if r["status"] == "COMPLETED"]
        p3 = None
        if doc:
            p3 = next((r for r in rs if r["run_id"] in doc["run_ids"]), None)
        if p3 is None and len(completed) >= 2:
            p3 = completed[-1]
        p2 = [r for r in completed if p3 is None or (r.get("_created") or 0) < (p3.get("_created") or 0)]
        if p3 is None and len(completed) == 1:
            p2 = completed  # 只有一個完成的 run → 視為 Phase 2，Phase 3 尚未開始
        others = [r for r in rs if r not in p2 and r is not p3]  # 取消／進行中
        for r in p2: run_phase[r["run_id"]] = "phase2"
        if p3: run_phase[p3["run_id"]] = "phase3"
        for r in others:
            # 進行中且已有 Phase 2 → 當作 Phase 3 嘗試；否則 Phase 2 嘗試
            run_phase[r["run_id"]] = "phase3" if p2 else "phase2"

        p3_end = _ts(p3.get("updated_at")) if p3 else None
        t4 = next((t for t in (p3 or {}).get("tasks", []) if t["task_id"] == "T4"), None)
        approval_id = t4.get("approval_id") if t4 else None
        # 修訂 run：同功能區、且在 Phase 3 結束後建立（沒有 Phase 3 時不歸屬）
        area = _area(key)
        revs = [r for r in revisions if re.match(rf"TC-{re.escape(area)}-", r.get("testcase_id") or "") and p3_end and (r.get("_created") or 0) >= p3_end - 60]
        revs_open = [r for r in revs if r["status"] in ("RUNNING", "WAITING_HUMAN", "CREATED")]
        last_rev_end = max([(_ts(r.get("updated_at")) or 0) for r in revs if r["status"] in ("COMPLETED", "CANCELLED", "FAILED")], default=None)
        # final
        grp = next((g for g in groups.values() if _matches_key(g["key"], key)), None)
        final_mtime = grp["mtime"] if grp else None
        drift_stale = bool(grp and (grp.get("meta") or {}).get("drift", {}).get("stale"))

        integ_end = max([x for x in (doc["mtime"] if doc else None, last_rev_end) if x], default=None)
        dod = {
            # Phase 3 run 可能在整合完成後被 run cancel（shadow 文件會寫明），所以 CANCELLED＋有文件也算整合完成
            "integrated": bool(p3 and ((p3["status"] == "COMPLETED" and (t4 or {}).get("status") == "DONE") or (p3["status"] == "CANCELLED" and doc)) and not revs_open),
            "shadow_doc": bool(doc),
            "final": bool(grp and (p3_end is None or final_mtime >= p3_end - 60) and not drift_stale),
        }
        missing = [k for k, v in dod.items() if not v]
        # 階段狀態（給階段條與耗時分析）
        p3_terminal = bool(p3 and p3["status"] in ("COMPLETED", "CANCELLED", "FAILED"))
        # 同 spec 又有新的 spec-to-testcase run 在跑（例如 Phase 3 重做）→ 整合要等新 run 完成，不算進行中
        redo_active = any(r["status"] in ("RUNNING", "WAITING_HUMAN", "CREATED") for r in others)
        # 同 spec 又有 run 在跑（重做）→ 一律 pending，不沿用舊的整合證據（即使舊的 shadow 文件與修訂都已結束）
        integ_status = "pending" if redo_active else ("done" if dod["shadow_doc"] and not revs_open else ("active" if (p3_terminal and p3["status"] != "FAILED") else "pending"))
        final_status = "done" if dod["final"] else ("stale" if (grp and drift_stale) else "pending")
        integ_elapsed = (integ_end - p3_end) if (integ_end and p3_end and integ_status == "done") else ((now - p3_end) if (p3_end and integ_status == "active") else None)
        final_elapsed = (final_mtime - integ_end) if (final_mtime and integ_end and final_status == "done") else None
        specs.append({
            "key": key, "spec_id": (p3 or (p2 or rs)[0]).get("spec_id"), "area": area,
            "phase2": [_lite(r) for r in p2], "phase3": _lite(p3) if p3 else None, "others": [_lite(r) | {"phase": run_phase[r["run_id"]]} for r in others],
            "approval_id": approval_id, "phase3_end": _iso(p3_end),
            "integration": {"status": integ_status, "elapsed": max(0.0, integ_elapsed) if integ_elapsed is not None else None, "doc": doc["path"] if doc else None, "doc_at": _iso(doc["mtime"]) if doc else None,
                            "revisions": [_lite(r) for r in revs], "revisions_open": len(revs_open), "ended_at": _iso(integ_end)},
            "final": {"status": final_status, "elapsed": max(0.0, final_elapsed) if final_elapsed is not None else None, "group_key": grp["key"] if grp else None, "at": _iso(final_mtime), "stale": drift_stale, "case_count": (grp or {}).get("meta", {}).get("case_count")},
            "dod": dod, "missing": missing, "complete": not missing,
        })
    result = {"specs": specs, "run_phase": run_phase, "generated_at": _iso(now)}
    _cache = (sig, result)
    return result


def _lite(r: dict) -> dict:
    return {"run_id": r["run_id"], "status": r["status"], "created_at": r.get("created_at"), "updated_at": r.get("updated_at"), "spec_version": r.get("spec_version"),
            "iterations": max([t.get("iteration") or 0 for t in r.get("tasks", [])] or [0])}


def run_phase(run_id: str) -> str | None:
    return build()["run_phase"].get(run_id)


def stage_evidence(run: dict) -> dict[str, dict]:
    """給 pipeline._run_stage_status：spec-to-testcase run 的 integration / final-export 節點。只有 Phase 3 run 才接整合線；Phase 2 run 的這兩節點標 n/a。"""
    key = spec_key(run.get("spec_id"))
    if not key:
        return {}
    data = build()
    spec = next((s for s in data["specs"] if s["key"] == key), None)
    if not spec:
        return {}
    phase = data["run_phase"].get(run["run_id"])
    if phase != "phase3":
        return {"integration": {"status": "skipped", "note": "Phase 2 run：整合在 Phase 3 之後", "started": False}, "final-export": {"status": "skipped", "note": "Phase 2 run", "started": False}}
    if not spec["phase3"] or spec["phase3"]["run_id"] != run["run_id"]:
        # 這條是 Phase 3 的新嘗試（還在跑或被取消），整合與匯出要等它完成後才接得上；不能借用上一條 Phase 3 run 的證據
        return {"integration": {"status": "pending", "note": "等這條 run 完成後才會進入交叉整合", "started": False}, "final-export": {"status": "pending", "started": False}}
    i, f = spec["integration"], spec["final"]
    return {
        "integration": {"status": i["status"], "elapsed_seconds": i["elapsed"], "elapsed_running": i["status"] == "active", "doc": i["doc"], "revisions": len(i["revisions"]), "started": i["status"] != "pending", "at": i["ended_at"]},
        "final-export": {"status": "done" if f["status"] == "done" else ("failed" if f["status"] == "stale" else "pending"), "elapsed_seconds": f["elapsed"], "stale": f["stale"], "at": f["at"], "started": f["status"] != "pending"},
    }
