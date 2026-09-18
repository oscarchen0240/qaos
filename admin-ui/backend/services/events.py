"""讀 .warroom/events*.jsonl（hook 寫入），整理成 session 結構。唯讀。"""
import json
import pathlib
import re
from datetime import datetime, timezone

from ..config import EVENTS_FILE, WARROOM_DIR

_cache: dict[str, tuple[float, int, list[dict]]] = {}


def _parse_ts(s: str) -> float:
    try:
        return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()
    except Exception:  # noqa: BLE001
        return 0.0


def _read(path: pathlib.Path) -> list[dict]:
    st = path.stat()
    c = _cache.get(str(path))
    if c and c[0] == st.st_mtime and c[1] == st.st_size:
        return c[2]
    out = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line or not line.startswith("{"):
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not d.get("session_id") or not d.get("event"):
                continue
            d["_t"] = _parse_ts(d.get("ts", ""))
            out.append(d)
    _cache[str(path)] = (st.st_mtime, st.st_size, out)
    return out


def files() -> list[pathlib.Path]:
    """輪替檔由舊到新：events.3.jsonl … events.1.jsonl, events.jsonl"""
    if not WARROOM_DIR.exists():
        return []
    rotated = sorted(WARROOM_DIR.glob("events.*.jsonl"), key=lambda p: -int(re.search(r"\.(\d+)\.jsonl$", p.name).group(1)))
    return [*rotated, *( [EVENTS_FILE] if EVENTS_FILE.exists() else [] )]


def signature() -> tuple:
    """用來偵測是否有變化（給 SSE 輪詢）。"""
    return tuple((str(p), p.stat().st_mtime, p.stat().st_size) for p in files())


def all_events() -> list[dict]:
    evs: list[dict] = []
    for p in files():
        evs.extend(_read(p))
    evs.sort(key=lambda e: e["_t"])
    return evs


def sessions() -> dict[str, dict]:
    """依 session_id 分組，整理 agent 區間、final 寫入、生命週期。"""
    out: dict[str, dict] = {}
    for e in all_events():
        sid = e["session_id"]
        s = out.get(sid)
        if s is None:
            s = out[sid] = {
                "session_id": sid, "first_seen": e["ts"], "last_seen": e["ts"], "_first": e["_t"], "_last": e["_t"],
                "started_at": None, "ended_at": None, "end_reason": None, "cwd": e.get("cwd") or "",
                "transcript_path": "", "tag": "", "agents": [], "final_writes": [], "stops": 0, "event_count": 0,
                "agent_types": [],
            }
        s["last_seen"] = e["ts"]; s["_last"] = e["_t"]; s["event_count"] += 1
        if e.get("cwd"): s["cwd"] = e["cwd"]
        if e.get("transcript_path"): s["transcript_path"] = e["transcript_path"]
        if e.get("tag"): s["tag"] = e["tag"]
        ev = e["event"]
        if ev == "SessionStart":
            if not s["started_at"]:
                s["started_at"] = e["ts"]
            s["ended_at"] = None  # resume 之後視為再次活著
        elif ev == "SessionEnd":
            s["ended_at"] = e["ts"]; s["end_reason"] = e.get("reason") or ""
        elif ev == "Stop":
            s["stops"] += 1
        elif ev == "SubagentStart":
            s["agents"].append({
                "agent_id": e.get("agent_id") or "", "agent_type": e.get("agent_type") or "", "subagent_name": e.get("subagent_name") or "",
                "started_at": e["ts"], "_start": e["_t"], "ended_at": None, "_end": None,
            })
            if e.get("agent_type") and e["agent_type"] not in s["agent_types"]:
                s["agent_types"].append(e["agent_type"])
        elif ev == "SubagentStop":
            aid = e.get("agent_id") or ""
            atype = e.get("agent_type") or ""
            a = next((a for a in reversed(s["agents"]) if a["ended_at"] is None and a["agent_id"] == aid), None) if aid else None
            if a is None and atype:
                # 沒有 id 才退而用 type 配對；id 不明又沒 type 的 Stop（Start 在 hook 載入前就發生）直接忽略，不能亂關別的 agent
                a = next((a for a in reversed(s["agents"]) if a["ended_at"] is None and a["agent_type"] == atype), None)
            if a:
                a["ended_at"] = e["ts"]; a["_end"] = e["_t"]
        elif ev == "PostToolUse" and e.get("file_path"):
            s["final_writes"].append({"ts": e["ts"], "path": e["file_path"], "tool": e.get("tool_name") or "", "agent_id": e.get("agent_id") or ""})
    return out
