"""唯讀索引 testcases/registry/ + testcases/versions/：每條 ACTIVE TC 的 active_version 與所屬 spec。

用途：比對 testcases/final/ 的 JSON 是否已過期（registry 有新版本／新 TC／退役 TC，但 final 還沒重新匯出）。
"""
import pathlib

import yaml

from ..config import PROJECT_ROOT

REG_DIR = PROJECT_ROOT / "testcases" / "registry"
VER_DIR = PROJECT_ROOT / "testcases" / "versions"
_ptr_cache: dict[str, tuple[float, dict]] = {}
_ver_cache: dict[str, tuple[float, dict]] = {}


def _load(path: pathlib.Path, cache: dict) -> dict | None:
    try:
        st = path.stat()
    except OSError:
        return None
    c = cache.get(str(path))
    if c and c[0] == st.st_mtime:
        return c[1]
    try:
        d = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001
        d = {}
    cache[str(path)] = (st.st_mtime, d)
    return d


def signature() -> tuple:
    if not REG_DIR.exists():
        return ()
    return (len(list(REG_DIR.glob("TC-*.yaml"))), max((p.stat().st_mtime for p in REG_DIR.glob("TC-*.yaml")), default=0))


def active_index(area_prefix: str | None = None) -> dict[str, dict]:
    """{tc_id: {active_version, spec_id, spec_version, updated_at, status}}，只含 ACTIVE。"""
    out: dict[str, dict] = {}
    if not REG_DIR.exists():
        return out
    pattern = f"TC-{area_prefix}-*.yaml" if area_prefix else "TC-*.yaml"
    for p in REG_DIR.glob(pattern):
        d = _load(p, _ptr_cache)
        if not d or d.get("status") != "ACTIVE" or not d.get("active_version"):
            continue
        tc, ver = d["testcase_id"], int(d["active_version"])
        v = _load(VER_DIR / tc / f"v{ver}.yaml", _ver_cache) or {}
        out[tc] = {"active_version": ver, "spec_id": v.get("spec_id"), "spec_version": v.get("spec_version"),
                   "updated_at": v.get("updated_at"), "title": v.get("title")}
    return out


def drift_for_final(cases: list[dict], area: str | None) -> dict:
    """final JSON 的 cases（含 testcase_id / version / spec_id / spec_version）對照 registry。"""
    if not cases:
        return {"stale": False, "newer": [], "added": [], "retired": []}
    prefix = area.split("-")[0] if area else None
    idx = active_index(prefix)
    specs = {(c.get("spec_id"), str(c.get("spec_version"))) for c in cases if c.get("spec_id")}
    final_v = {c["testcase_id"]: int(c.get("version") or 1) for c in cases if c.get("testcase_id")}
    newer = [t for t, v in final_v.items() if t in idx and idx[t]["active_version"] > v]
    retired = [t for t in final_v if t not in idx]
    added = [t for t, m in idx.items() if t not in final_v and (m.get("spec_id"), str(m.get("spec_version"))) in specs]
    return {"stale": bool(newer or added or retired), "newer": sorted(newer), "added": sorted(added), "retired": sorted(retired),
            "registry_active": sum(1 for m in idx.values() if (m.get("spec_id"), str(m.get("spec_version"))) in specs)}
