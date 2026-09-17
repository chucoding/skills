#!/bin/sh
# PostToolUse 훅 (matcher: Skill)
# 스킬이 로드되면 대화 내역에 한 줄로 표시
#
# Skill 툴 호출은 대화 내역에 툴 호출로만 남아 눈에 잘 띄지 않는다.
# 훅이 systemMessage 를 출력하면 advisor 처럼 별도 줄로 찍혀 로드 여부 확인이 쉬워진다.
#
# 표시 대상은 이 플러그인의 스킬뿐이다.
# 모든 스킬을 표시하려면 아래 case 블록 제거.

input=$(cat 2>/dev/null)

# tool_input 객체 하나만 잘라낸 뒤 그 안에서 skill 값을 읽음
# tool_response 에 실린 스킬 본문이 같은 키를 담고 있어도 오인하지 않기 위함
skill=$(printf '%s' "$input" \
  | grep -o '"tool_input"[[:space:]]*:[[:space:]]*{[^}]*}' \
  | head -1 \
  | sed -n 's/.*"skill"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
[ -n "$skill" ] || exit 0

case "$skill" in
  chucoding:*) ;;
  *) exit 0 ;;
esac

printf '{"systemMessage":"🧩 %s 스킬 로드"}\n' "$skill"
exit 0
