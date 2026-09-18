"""Claude Code hook（PreToolUse, matcher=Bash）：人工決定類的 bin/qaos 指令，執行前一律先問 Oscar。

不擋、不代答：命中時回 permissionDecision=ask，Claude Code 會跳出權限確認（即使在自動核准模式），
由 Oscar 按下允許才執行。這樣「平台送出」與「在 QA session 口頭交辦」兩個入口都保留，
但 agent 不能在沒人看的情況下自己核准。

命中的指令：bin/qaos approve / clarification ask|answer|apply|withdraw / bug resolve|verify|close|transition。
其他指令不輸出任何東西。不打網路、不寫檔、無論如何 exit 0。
"""
import json
import re
import sys

PATTERN = re.compile(r"bin/qaos\s+(approve\b|clarification\s+(ask|answer|apply|withdraw)\b|bug\s+(resolve|verify|close|transition)\b)")


def main():
    raw = sys.stdin.read()
    if not raw.strip():
        return
    p = json.loads(raw)
    if p.get("hook_event_name") != "PreToolUse" or p.get("tool_name") != "Bash":
        return
    cmd = (p.get("tool_input") or {}).get("command") or ""
    m = PATTERN.search(cmd)
    if not m:
        return
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": f"[QAOS 指揮台守門] `{m.group(0)}` 是人工決定，請 Oscar 確認後才執行（或改在指揮台「單據」頁送出）。",
        }
    }, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception:  # noqa: BLE001
        pass
    sys.exit(0)
