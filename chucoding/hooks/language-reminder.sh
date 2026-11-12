#!/bin/sh
# UserPromptSubmit, PostToolUse 훅
# 마지막 사용자 메시지 뒤로 도구 호출이 길게 이어지면 응답 언어 리마인더를 컨텍스트에 주입
#
# language 설정 적용 뒤에도 도구 호출 뒤 응답의 영어 비율이 남았고,
# 사용자 메시지 뒤 도구 결과 수가 늘수록 높아졌음
# (HDIT-6084, 2026-11-12 측정: 1개 뒤 6%, 4~7개 뒤 16%, 16개 이상 뒤 21%)
# 작업 중간에 끼어든 하네스 메시지 직후에는 같은 도구 횟수에서 영어 비율이 절반 가까이로 낮았으므로,
# 지시를 실패 지점 가까이 다시 넣는 방식을 먼저 시험함
#
# 기준 이상이면 주기를 두지 않고 도구 호출마다 주입함
# 끼어든 메시지의 효과가 바로 다음 응답에서 관측됐고, 주기를 두면 그 사이 호출에서 다시 멀어지기 때문
# 비용은 호출당 약 60토큰이라 도구 50회 연쇄에서도 약 3천 토큰. 효과를 재측정할 때 주기 조정 여부를 함께 판단
#
# 사용법
#   sh language-reminder.sh reset   UserPromptSubmit 에서 세션별 도구 횟수를 0으로 되돌림
#   sh language-reminder.sh         PostToolUse 에서 횟수를 올리고 기준 이상이면 리마인더 출력

# 영어 비율이 뛰기 시작한 4~7개 구간에 맞춘 기준
THRESHOLD=4

input=$(cat 2>/dev/null)

session_id=$(printf '%s' "$input" \
  | sed -n 's/.*"session_id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' \
  | head -1 \
  | tr -cd 'A-Za-z0-9-')
[ -n "$session_id" ] || exit 0

state_dir="${TMPDIR:-/tmp}/claude-language-reminder"
mkdir -p "$state_dir" 2>/dev/null || exit 0
state="$state_dir/$session_id"

if [ "$1" = "reset" ]; then
  printf '0' > "$state" 2>/dev/null
  exit 0
fi

count=$(cat "$state" 2>/dev/null)
case "$count" in
  ''|*[!0-9]*) count=0 ;;
esac
count=$((count + 1))
printf '%s' "$count" > "$state" 2>/dev/null

[ "$count" -ge "$THRESHOLD" ] || exit 0

printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":"응답 언어 리마인더: 도구 호출 사이의 진행 안내와 중간 보고, 최종 보고 모두 한국어로 쓴다. 코드, 경로, 식별자는 원문을 유지한다."}}'
exit 0
