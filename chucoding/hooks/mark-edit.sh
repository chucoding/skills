#!/bin/sh
# PostToolUse(Edit|Write|NotebookEdit) 훅
# 이번 세션에서 파일을 실제로 수정했다는 표시를 남김
# Stop 훅이 이 표시가 있을 때만 커밋 초안을 요구하도록 하는 것이 목적

input=$(cat 2>/dev/null)

session_id=$(printf '%s' "$input" \
  | sed -n 's/.*"session_id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' \
  | head -1)
[ -n "$session_id" ] || exit 0

marker_dir="${TMPDIR:-/tmp}/claude-commit-draft-guard"
mkdir -p "$marker_dir" 2>/dev/null || exit 0
: > "$marker_dir/$session_id" 2>/dev/null

exit 0
