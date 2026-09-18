#!/usr/bin/env python3
"""產生假的 .warroom/events.jsonl（含假 subagent meta.json），用來驗證 Pipeline 面板。

用法：
  python3 admin-ui/fixtures/make_demo_events.py <warroom_dir> [<fake_projects_dir>]

- session demo-ended-…：對應真實 RUN-20260916-008 的時間軸（T2 設計 → T3 驗證 → 等待核准），已結束
- session demo-live-…：從「現在」往回推的進行中 session，qaos-test-designer 正在跑
- session demo-dev-…：假裝是開發管理介面的 session（沒有 pipeline agent，應被建議忽略）
"""
import json
import pathlib
import sys
import time

warroom = pathlib.Path(sys.argv[1]).resolve()
projects = pathlib.Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else warroom / "_fake_projects"
warroom.mkdir(parents=True, exist_ok=True)


def iso(t: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t))


def meta(session: str, agent_id: str, agent_type: str, description: str) -> str:
    d = projects / "-Users-oscar-Desktop-qa-agent-os" / session / "subagents"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"agent-{agent_id}.meta.json").write_text(json.dumps({"agentType": agent_type, "description": description}, ensure_ascii=False))
    return str(projects / "-Users-oscar-Desktop-qa-agent-os" / f"{session}.jsonl")


lines: list[dict] = []


def ev(ts: float, session: str, event: str, **kw):
    rec = {"ts": iso(ts), "session_id": session, "event": event, "agent_id": "", "agent_type": "", "subagent_name": "", "tool_name": "",
           "file_path": "", "reason": "", "cwd": "/Users/oscar/Desktop/qa-agent-os", "transcript_path": "", "tag": ""}
    rec.update(kw)
    lines.append(rec)


# ---- 1) 已結束的 session：貼齊 RUN-20260916-008（UTC 15:06 建 run、15:19 T2、15:29 T3、15:29 等待核准）----
S1 = "demo-ended-4b1f9c2e"
t0 = time.mktime(time.strptime("2026-09-16T15:05:00Z", "%Y-%m-%dT%H:%M:%SZ")) - time.timezone
tp1 = meta(S1, "a1demo000000001", "qaos-test-designer", "ACCOUNT Phase3測試設計")
meta(S1, "a1demo000000002", "general-purpose", "ACCOUNT影子測試獨立審查")
ev(t0, S1, "SessionStart", reason="startup", transcript_path=tp1)
ev(t0 + 60 * 2, S1, "SubagentStart", agent_id="a1demo000000001", agent_type="qaos-test-designer", subagent_name="qaos-test-designer")
ev(t0 + 60 * 15, S1, "SubagentStop", agent_id="a1demo000000001", agent_type="qaos-test-designer", subagent_name="qaos-test-designer")
ev(t0 + 60 * 15 + 30, S1, "Stop")
ev(t0 + 60 * 16, S1, "SubagentStart", agent_id="a1demo000000002", agent_type="general-purpose", subagent_name="general-purpose")
ev(t0 + 60 * 24, S1, "SubagentStop", agent_id="a1demo000000002", agent_type="general-purpose", subagent_name="general-purpose")
ev(t0 + 60 * 25, S1, "Stop")
ev(t0 + 60 * 40, S1, "SessionEnd", reason="prompt_input_exit")

# ---- 2) 進行中的 session：現在往回推 ----
S2 = "demo-live-7e3a5d90"
now = time.time()
tp2 = meta(S2, "a2demo000000001", "general-purpose", "CASHFLOW影子測試第二輪獨立審查")
meta(S2, "a2demo000000002", "qaos-test-designer", "CASHFLOW T2修訂輪(iteration 2)")
ev(now - 60 * 32, S2, "SessionStart", reason="startup", transcript_path=tp2, tag="1")
ev(now - 60 * 30, S2, "SubagentStart", agent_id="a2demo000000001", agent_type="general-purpose", subagent_name="general-purpose")
ev(now - 60 * 12, S2, "SubagentStop", agent_id="a2demo000000001", agent_type="general-purpose", subagent_name="general-purpose")
ev(now - 60 * 11, S2, "Stop")
ev(now - 60 * 4, S2, "SubagentStart", agent_id="a2demo000000002", agent_type="qaos-test-designer", subagent_name="qaos-test-designer")
ev(now - 60 * 1, S2, "PostToolUse", agent_id="a2demo000000002", tool_name="Write", file_path="testcases/final/CASHFLOW-final.html")

# ---- 3) 開發 admin-ui 的 session：只有 Explore，沒有 pipeline agent ----
S3 = "demo-dev-c0ffee12"
ev(now - 60 * 50, S3, "SessionStart", reason="startup")
ev(now - 60 * 49, S3, "SubagentStart", agent_id="a3demo000000001", agent_type="Explore", subagent_name="Explore")
ev(now - 60 * 48, S3, "SubagentStop", agent_id="a3demo000000001", agent_type="Explore", subagent_name="Explore")
ev(now - 60 * 3, S3, "Stop")

lines.sort(key=lambda r: r["ts"])
out = warroom / "events.jsonl"
out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in lines), encoding="utf-8")
print(f"wrote {len(lines)} events → {out}\nfake meta → {projects}")
