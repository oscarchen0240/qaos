"""唯讀掃描 clarifications/<product>/<area>/CLR-*.yaml，找未回答的釐清單。"""
import yaml

from ..config import PROJECT_ROOT

_cache: dict[str, tuple[float, dict]] = {}
OPEN_STATUSES = ("OPEN", "ASKED")


def open_for_spec(spec_id: str | None) -> list[dict]:
    if not spec_id:
        return []
    base = PROJECT_ROOT / "clarifications"
    if not base.exists():
        return []
    out = []
    for p in base.glob("*/*/CLR-*.yaml"):
        try:
            st = p.stat()
            c = _cache.get(str(p))
            if c and c[0] == st.st_mtime:
                d = c[1]
            else:
                d = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
                _cache[str(p)] = (st.st_mtime, d)
        except Exception:  # noqa: BLE001
            continue
        if d.get("spec_id") == spec_id and d.get("status") in OPEN_STATUSES:
            out.append({"clarification_id": d.get("clarification_id") or p.stem, "status": d.get("status"), "question": (d.get("question") or "")[:120],
                        "raised_at": d.get("raised_at")})
    out.sort(key=lambda c: c.get("raised_at") or "")
    return out
