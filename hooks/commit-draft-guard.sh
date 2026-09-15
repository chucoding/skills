#!/bin/sh
# Stop 훅
# 이번 세션에서 파일을 수정했고 커밋되지 않은 변경이 남아 있는데
# 커밋 초안을 제시하지 않은 채 턴을 끝내려 하면 차단
#
# 무한 루프 방지: 표시 파일을 읽는 즉시 지운다.
# 차단 후 이어지는 턴에는 표시가 없으므로 다시 차단되지 않는다.

input=$(cat 2>/dev/null)

session_id=$(printf '%s' "$input" \
  | sed -n 's/.*"session_id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' \
  | head -1)
[ -n "$session_id" ] || exit 0

marker="${TMPDIR:-/tmp}/claude-commit-draft-guard/$session_id"
[ -f "$marker" ] || exit 0

# 표시 소비. 이 지점 이후로는 어떤 경로로 끝나든 재차단되지 않는다
rm -f "$marker" 2>/dev/null

# 이미 커밋 초안을 제시했으면 통과
# 코드 펜스와 커밋 초안임을 가리키는 표현이 함께 있을 때만 초안으로 인정
if printf '%s' "$input" | grep -q '```' \
  && printf '%s' "$input" | grep -qE '커밋 메시지|커밋 초안|Co-Authored-By'; then
  exit 0
fi

# 훅의 작업 디렉터리를 세션의 작업 디렉터리로 맞춤
# JSON 안의 윈도우 경로는 역슬래시가 이스케이프되어 있으므로 슬래시로 되돌림
cwd=$(printf '%s' "$input" \
  | sed -n 's/.*"cwd"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' \
  | head -1 \
  | sed 's/\\/\//g')
if [ -n "$cwd" ] && [ -d "$cwd" ]; then
  cd "$cwd" 2>/dev/null || exit 0
fi

# git 저장소가 아니거나 커밋할 변경이 없으면 통과
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0
[ -n "$(git status --porcelain 2>/dev/null)" ] || exit 0

printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"Stop","decision":"block","reason":"이번 턴에서 파일을 수정했고 커밋되지 않은 변경이 작업 트리에 남아 있는데 커밋 초안을 제시하지 않았다. commit-pr 스킬을 호출해 제목과 본문을 갖춘 커밋 메시지 초안을 제시하고, AskUserQuestion으로 커밋과 커밋 & 푸시 선택지를 물어라. 테스트 실행 지침에 해당하는 변경이면 초안보다 먼저 테스트를 실행하라. 다만 작업이 아직 중간 단계이거나, 스크래치패드나 임시 파일만 바꿨거나, 사용자가 커밋하지 않겠다고 밝혔다면 초안을 만들지 말고 그 사실만 한 줄로 밝히고 끝내라."}}'
exit 0
