"""ID 配發：只有 Runtime 可呼叫；counters 存於 testcases/registry/_counters.yaml。"""
import time, secrets
from . import store, operation

COUNTERS = "testcases/registry/_counters.yaml"
_B32 = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"

def ulid() -> str:
    t = int(time.time() * 1000); out = ""
    for _ in range(10): out = _B32[t & 31] + out; t >>= 5
    return out + "".join(secrets.choice(_B32) for _ in range(16))

def _load():
    return store.load(COUNTERS) if store.exists(COUNTERS) else {"schema_version": "1.0", "counters": {}}

AC_REJECTED = "AC 不由計數器配發：AC ID 依所屬 REQ 推導為 AC-<AREA>-<REQ 序號><AC 序號>（AC 序號從 1 起、不補 0），見 docs/architecture/02-data-model.md §5"

def alloc(kind: str, area: str | None = None, width: int = 3) -> str:
    """kind ∈ TC REQ BUG CLR (需 area) | EXE RUN (日期) | EVD APR (全域) | ART-<TYPE>
    計數器的更新是操作計畫的一步（ID 由計畫固定）；ART- 用 ULID，不寫計數器。
    AC 不經計數器：一律拒絕（由所屬 REQ 推導；既有的 AC-<AREA> 計數器保留不動）。"""
    if kind.startswith("ART-"): return f"{kind}-{ulid()}"
    if kind == "AC":
        raise ValueError(AC_REJECTED)
    d = _load(); c = d["counters"]
    if kind in ("TC", "REQ", "BUG", "CLR"):
        if not area: raise ValueError(f"{kind} 需要 area")
        key = f"{kind}-{area}"
        if kind == "REQ":                                                    # 舊 area 的計數器可能落後於已持久化的需求：從已用的最大序號之後配發
            from . import rm
            c[key] = max(c.get(key, 0), rm.max_requirement_seq(area))
        c[key] = c.get(key, 0) + 1
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
    cap = store.capturing()
    if cap is not None: cap.allocated_ids.append(out)
    return out

@operation.operation("id_alloc")
def alloc_cmd(kind: str, area: str | None = None) -> str:
    """CLI `qaos id`：配發一個 ID（寫計數器，要經過 executor）。"""
    return alloc(kind, area)

ART_PREFIX = {
    "SpecAnalysis": "ART-SA", "RequirementModel": "ART-RM", "TestDesignReport": "ART-TDR", "TestCaseDraft": "ART-TCD",
    "TestValidationReport": "ART-TVR", "BugDraft": "ART-BD", "BugValidationReport": "ART-BVR", "ChangeImpactReport": "ART-CIR",
    "VersionComparisonReport": "ART-VCR", "RegressionProposal": "ART-RP", "ApprovalRequest": "ART-AR", "WorkflowSummary": "ART-WS",
    "TCRiskReview": "ART-TRR",
}
def artifact_id(artifact_type: str) -> str:
    return alloc(ART_PREFIX[artifact_type])
