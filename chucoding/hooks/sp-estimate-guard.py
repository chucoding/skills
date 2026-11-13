"""Stop 훅 본체
이 세션에서 만든 HDIT 티켓의 SP(`customfield_10028`)가 비어 있으면 턴 종료를 차단

생성 수단(MCP, curl, 스크래치패드 스크립트)이 제각각이라 호출 패턴 대신 Jira 결과로 판정.
- 대상: 세션 시작 이후 내가 만든 HDIT 티켓 중 이 세션 transcript에 키가 나온 것
  (병렬 세션이 같은 시간대에 만든 티켓으로 차단하지 않기 위함)
- 제외: 연차 유형, `[데일리 스크럼]`, `[회의]` 제목 (폴러 `estimate_sp.targets`와 제목, 유형 기준만 같음.
  묶음 판정은 SP가 0인 티켓만 해당해 빈 SP와 겹치지 않으므로 생략)
- 무한 루프 방지: 키마다 한 번만 차단. 정당하게 못 채운 티켓은 두 번째 종료에서 통과
- 자격증명, 네트워크, transcript 중 하나라도 없으면 조용히 통과 (정본은 jira 스킬)
"""

import base64
import datetime as dt
import json
import os
import re
import sys
import tempfile
import urllib.request

JIRA_BASE = "https://rsquare.atlassian.net"
CONFIG = os.path.expanduser("~/.config/homedot-worktime/config.env")
SP_FIELD = "customfield_10028"
TIMEOUT = 6
# transcript에 Jira 흔적(읽기 포함)이 없으면 네트워크 호출 없이 통과
JIRA_HINT = re.compile(r"atlassian\.net|createJiraIssue|rest/api/3/issue")
SKIP_PREFIXES = ("[데일리 스크럼]", "[회의]")


def read_env(path):
    """config.env의 `KEY=VALUE` 줄을 사전으로 읽음"""
    env = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.replace("export ", "").strip()] = v.strip().strip("\"'")
    return env


def session_start(transcript):
    """transcript에서 처음 나오는 timestamp (UTC)"""
    m = re.search(r'"timestamp"\s*:\s*"([^"]+)"', transcript)
    if not m:
        return None
    try:
        start = dt.datetime.fromisoformat(m.group(1).replace("Z", "+00:00"))
    except ValueError:
        return None
    # 시간대 표기가 없으면 UTC로 간주
    return start if start.tzinfo else start.replace(tzinfo=dt.timezone.utc)


def search(env, jql):
    """`POST /rest/api/3/search/jql` 결과의 이슈 목록"""
    auth = base64.b64encode(f"{env['JIRA_EMAIL']}:{env['JIRA_API_TOKEN']}".encode()).decode()
    body = {"jql": jql, "fields": ["summary", "issuetype", SP_FIELD], "maxResults": 50}
    req = urllib.request.Request(
        JIRA_BASE + "/rest/api/3/search/jql",
        method="POST",
        data=json.dumps(body).encode(),
        headers={"Authorization": "Basic " + auth, "Content-Type": "application/json",
                 "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.load(r).get("issues") or []


def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return
    session_id = data.get("session_id")
    transcript_path = data.get("transcript_path")
    if not session_id or not transcript_path:
        return
    # 상태 파일 경로로 쓰므로 경로 문자가 섞인 값은 통과
    if not re.fullmatch(r"[A-Za-z0-9_-]+", session_id):
        return
    try:
        with open(transcript_path, encoding="utf-8", errors="replace") as f:
            transcript = f.read()
    except OSError:
        return
    if not JIRA_HINT.search(transcript):
        return
    start = session_start(transcript)
    if not start:
        return
    try:
        env = read_env(CONFIG)
    except (OSError, ValueError):
        return
    if not env.get("JIRA_EMAIL") or not env.get("JIRA_API_TOKEN"):
        return

    minutes = int((dt.datetime.now(dt.timezone.utc) - start).total_seconds() // 60) + 5
    jql = (f"project = HDIT AND creator = currentUser() AND created >= -{minutes}m "
           f"AND cf[10028] IS EMPTY ORDER BY created DESC")
    try:
        issues = search(env, jql)
    except Exception:  # noqa: BLE001 - 조회 실패는 통과 (보조 안전망)
        return

    empty = []
    for i in issues:
        key = i.get("key") or ""
        f = i.get("fields") or {}
        # 검색 색인이 방금 기입한 값을 아직 반영하지 않은 경우 대비
        if f.get(SP_FIELD) is not None:
            continue
        summary = (f.get("summary") or "").lstrip()
        if (f.get("issuetype") or {}).get("name") == "연차" or summary.startswith(SKIP_PREFIXES):
            continue
        # 키 뒤에 숫자가 이어지는 경우(HDIT-44 와 HDIT-445) 구분
        if not re.search(re.escape(key) + r"(?!\d)", transcript):
            continue
        empty.append(key)
    if not empty:
        return

    state_dir = os.path.join(tempfile.gettempdir(), "claude-sp-estimate-guard")
    state = os.path.join(state_dir, session_id)
    try:
        os.makedirs(state_dir, exist_ok=True)
        with open(state, encoding="utf-8") as f:
            blocked = set(f.read().split())
    except OSError:
        blocked = set()
    fresh = [k for k in empty if k not in blocked]
    if not fresh:
        return
    try:
        with open(state, "a", encoding="utf-8") as f:
            f.write("\n".join(fresh) + "\n")
    except OSError:
        return  # 기록하지 못하면 매번 차단하게 되므로 통과

    keys = ", ".join(fresh)
    reason = (
        f"이 세션에서 만든 티켓 {keys}의 SP(customfield_10028)가 비어 있다. "
        "chucoding:jira 스킬의 `SP 산정`을 지금 수행해 estimate_sp.py --key <키> --sp <값> --note \"<근거>\"로 기입하고, "
        "기입 직전 재조회에서 이미 값이 있으면 덮지 말고 그 값을 보고하라. "
        "기입할 수 없는 사유가 있으면 보고의 `하지 않은 것`에 키와 사유를 남기고 끝내라."
    )
    print(json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False))


if __name__ == "__main__":
    main()
