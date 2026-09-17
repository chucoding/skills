#!/bin/sh
# Stop 훅
# 이번 턴에 작업 트리가 달라졌는데 커밋 초안을 제시하지 않았으면 턴 종료를 차단
#
# 턴마다 `git status --porcelain` 의 해시를 세션별 상태 파일에 기록하고,
# 직전 턴과 달라졌을 때만 이번 턴에 파일이 바뀐 것으로 본다.
# 수정 수단을 가리지 않으므로 Edit/Write 뿐 아니라 Bash heredoc 과 sed 도 잡힌다.
#
# 무한 루프 방지: 차단 직전에 해시를 갱신한다.
# 차단 뒤 이어지는 종료에서는 해시가 같아 그대로 통과한다.

input=$(cat 2>/dev/null)

session_id=$(printf '%s' "$input" \
  | sed -n 's/.*"session_id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' \
  | head -1)
[ -n "$session_id" ] || exit 0

# 훅의 작업 디렉터리를 세션의 작업 디렉터리로 맞춤
# JSON 안의 윈도우 경로는 역슬래시가 이스케이프되어 있으므로 슬래시로 되돌림
cwd=$(printf '%s' "$input" \
  | sed -n 's/.*"cwd"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' \
  | head -1 \
  | sed 's/\\/\//g')
if [ -n "$cwd" ] && [ -d "$cwd" ]; then
  cd "$cwd" 2>/dev/null || exit 0
fi

git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0

state_dir="${TMPDIR:-/tmp}/claude-commit-draft-guard"
mkdir -p "$state_dir" 2>/dev/null || exit 0
# 같은 세션이 여러 저장소를 오갈 수 있으므로 저장소별로 상태를 나눔
repo=$(git rev-parse --show-toplevel 2>/dev/null | tr -cd 'A-Za-z0-9')
state="$state_dir/$session_id-$repo"

status=$(git status --porcelain 2>/dev/null)
hash=$(printf '%s' "$status" | md5sum 2>/dev/null | cut -d' ' -f1)
[ -n "$hash" ] || hash=$(printf '%s' "$status" | cksum | tr -d ' ')

previous=$(cat "$state" 2>/dev/null)
printf '%s' "$hash" > "$state" 2>/dev/null

# 이 세션에서 이 저장소를 처음 보는 턴은 기준선만 잡고 넘어감
# 세션 시작 전부터 있던 변경으로 채근하지 않기 위함
[ -n "$previous" ] || exit 0

# 이번 턴에 작업 트리가 달라지지 않았으면 통과
[ "$hash" != "$previous" ] || exit 0

# 커밋할 변경이 남아 있지 않으면 통과 (커밋을 마친 턴)
[ -n "$status" ] || exit 0

# 이미 커밋 초안을 제시했으면 통과
# 코드 펜스와 커밋 초안임을 가리키는 표현이 함께 있을 때만 초안으로 인정
if printf '%s' "$input" | grep -q '```' \
  && printf '%s' "$input" | grep -qE '커밋 메시지|커밋 초안|Co-Authored-By'; then
  exit 0
fi

printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"Stop","decision":"block","reason":"이번 턴에서 작업 트리가 달라졌고 커밋되지 않은 변경이 남아 있는데 커밋 초안을 제시하지 않았다. chucoding:commit-pr 스킬을 호출해 제목과 본문을 갖춘 커밋 메시지 초안을 제시하고, AskUserQuestion으로 커밋, 커밋 & 푸시, 커밋대기 세 선택지를 물어라. 승인 없이 git commit 을 실행하지 마라. 테스트 실행 지침에 해당하는 변경이면 초안보다 먼저 테스트를 실행하라. 다만 작업이 아직 중간 단계이거나, 스크래치패드나 임시 파일만 바꿨거나, 사용자가 커밋하지 않겠다고 밝혔다면 초안을 만들지 말고 그 사실만 한 줄로 밝히고 끝내라."}}'
exit 0
