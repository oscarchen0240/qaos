#!/bin/bash
# Claude Code hook 入口（PreToolUse Bash）：人工決定類的 bin/qaos 指令 → 回 permissionDecision=ask，讓 Oscar 按允許。
# 無論如何 exit 0；stdout 給 Claude Code 讀，stderr 丟掉。
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$DIR/guard_qaos.py" 2>/dev/null </dev/stdin
exit 0
