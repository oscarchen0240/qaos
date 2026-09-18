#!/bin/bash
# Claude Code hook 入口：stdin 的 hook JSON 交給 log_event.py 寫進 .warroom/events.jsonl。
# 無論如何 exit 0、不輸出任何東西（stdout 會被 Claude Code 當成 hook 回饋）。
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$DIR/log_event.py" >/dev/null 2>&1 </dev/stdin
exit 0
