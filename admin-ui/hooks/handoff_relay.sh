#!/bin/bash
# Claude Code hook 入口（Stop / UserPromptSubmit）：把平台的交接紀錄接回 QA session。
# stdout 會被 Claude Code 讀取（Stop 的 block JSON、UserPromptSubmit 的上下文），stderr 丟掉；無論如何 exit 0。
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$DIR/handoff_relay.py" 2>/dev/null </dev/stdin
exit 0
