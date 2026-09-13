"""ID 配發：只有 Runtime 可呼叫；counters 存於 testcases/registry/_counters.yaml。"""
import time, secrets
from . import store

COUNTERS = "testcases/registry/_counters.yaml"
_B32 = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"

def ulid() -> str:
    t = int(time.time() * 1000); out = ""
    for _ in range(10): out = _B32[t & 31] + out; t >>= 5
    return out + "".join(secrets.choice(_B32) for _ in range(16))

def _load():
    return store.load(COUNTERS) if store.exists(COUNTERS) else {"schema_version": "1.0", "counters": {}}

def alloc(kind: str, area: str | None = None, width: int = 3) -> str:
    """kind ∈ TC REQ AC BUG (需 area) | EXE RUN (日期) | EVD APR (全域) | ART-<TYPE>"""
    d = _load(); c = d["counters"]
    if kind in ("TC", "REQ", "AC", "BUG", "CLR"):
        if not area: raise ValueError(f"{kind} 需要 area")
        key = f"{kind}-{area}"; c[key] = c.get(key, 0) + 1
        out = f"{kind}-{area}-{c[key]:0{width}d}"
    elif kind in ("EXE", "RUN"):
        key = f"{kind}-{store.today()}"; c[key] = c.get(key, 0) + 1
        out = f"{kind}-{store.today()}-{c[key]:03d}"
    elif kind in ("EVD", "APR"):
        c[kind] = c.get(kind, 0) + 1; out = f"{kind}-{c[kind]:04d}"
    elif kind.startswith("ART-"):
        out = f"{kind}-{ulid()}"
    elif kind == "MAN":
        key = f"MAN-{store.today()}"; c[key] = c.get(key, 0) + 1
        out = f"MAN-{store.today()}-{c[key]:03d}"
    else:
        raise ValueError(f"unknown id kind {kind}")
    store.save(COUNTERS, d)
    return out

ART_PREFIX = {
    "SpecAnalysis": "ART-SA", "RequirementModel": "ART-RM", "TestDesignReport": "ART-TDR", "TestCaseDraft": "ART-TCD",
    "TestValidationReport": "ART-TVR", "BugDraft": "ART-BD", "BugValidationReport": "ART-BVR", "ChangeImpactReport": "ART-CIR",
    "VersionComparisonReport": "ART-VCR", "RegressionProposal": "ART-RP", "ApprovalRequest": "ART-AR", "WorkflowSummary": "ART-WS",
}
def artifact_id(artifact_type: str) -> str:
    return alloc(ART_PREFIX[artifact_type])
