#!/bin/sh
# Stop 훅
# 이 세션에서 만든 HDIT 티켓의 SP가 비어 있으면 턴 종료를 차단
#
# 판정은 sp-estimate-guard.py 가 맡음. python3 가 없는 환경은 조용히 통과

command -v python3 >/dev/null 2>&1 || exit 0
exec python3 "$(dirname "$0")/sp-estimate-guard.py"
