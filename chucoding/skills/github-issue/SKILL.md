---
name: github-issue
description: GitHub 이슈로 만든 워크스페이스에서 착수부터 이슈 종료까지 따르는 절차. 이슈 조회, 워크트리 base 정렬, 이슈 번호를 반영한 커밋과 PR, 머지 확인 후 이슈 종료를 포함한다. GitHub 이슈 URL이나 `#번호`, `owner/repo#번호`가 착수 입력으로 들어오거나 GitHub 이슈를 닫아달라는 요청이 있을 때 사용한다. Jira 티켓 키로 착수한 작업에는 쓰지 않는다.
---

# GitHub 이슈 작업 지침

오르카 워크스페이스를 GitHub 이슈로 만들어 착수한 작업에 이 절차를 적용한다. 이슈 조회부터 커밋, PR, 이슈 종료까지가 적용 범위다.

## 1. 착수 경로 판별

착수 입력에서 아래를 찾아 경로를 정한다. 판별은 사용자가 준 입력으로만 하고, 워크트리 이름이나 원격 호스트로 추정하지 않는다.

| 입력에 있는 것 | 경로 |
|------|------|
| `https://github.com/<owner>/<repo>/issues/<번호>`, `#<번호>`, `<owner>/<repo>#<번호>` | 이 스킬 |
| Jira 티켓 키(`HDIT-1234`, `HOM-1234`)나 `*.atlassian.net/browse/<키>` | `chucoding:jira` |

- 원격이 GitHub라는 사실은 판별 근거가 아니다. Jira로 관리하는 저장소도 GitHub에 있다.
- 양쪽 다 없으면 어느 경로인지 추측하지 말고 되묻는다.
- 양쪽이 같이 들어오면 Jira를 정본으로 보고 `chucoding:jira`를 따르되, GitHub 이슈는 참고 자료로만 읽는다.

## 2. 이슈 조회

- URL에서 `owner`, `repo`, 번호를 뽑아 `gh issue view <번호> --repo <owner>/<repo>`로 본문과 라벨, 댓글을 읽는다.
- 이슈 본문이 착수의 정본 요구사항이다. 제목만 보고 범위를 정하지 않는다.
- 이슈에 적힌 범위와 실제 저장소 상태가 어긋나면 작업 전에 어긋난 지점을 밝힌다.

## 3. 워크트리 base 정렬

오르카 워크트리는 저장소 기본 브랜치에 붙어 만들어지는데, 저장소가 실제로 쓰는 통합 브랜치가 `develop`이면 작업 대상 파일이 아예 보이지 않거나 이미 처리된 변경을 다시 만들게 된다. 조사를 시작하기 전에 base를 맞춘다.

1. `git branch --show-current`와 `git log --oneline -3`으로 현재 붙은 지점을 확인한다.
2. `gh repo view --repo <owner>/<repo> --json defaultBranchRef`와 `gh pr list --repo <owner>/<repo> --state merged --limit 8 --json number,baseRefName`으로 이 저장소가 실제로 머지하는 통합 브랜치를 확인한다. 최근 PR의 base가 정본이다.
3. 현재 브랜치에 작업 커밋이 아직 없으면 `git fetch origin <통합브랜치>` 후 `git reset --hard origin/<통합브랜치>`로 맞춘다.
4. 이미 작업 커밋이 있으면 `reset`하지 않는다. 어긋난 사실을 알리고 어떻게 맞출지 되묻는다.

브랜치 이름은 오르카가 만든 워크스페이스 이름을 그대로 쓰고 임의로 바꾸지 않는다.

## 4. 범위 확정

- 이슈가 지시한 삭제나 변경 대상이 다른 목적의 내용과 섞여 있으면 혼자 정리하지 않는다. 무엇이 섞여 있는지 근거와 함께 정리해 선택지로 묻는다.
- 이슈 범위 밖의 유사 항목은 건드리지 않고, 왜 두었는지 보고에 남긴다.

## 5. 작업과 테스트

- 테스트는 `테스트 실행 지침`을 그대로 따른다. GitHub 이슈 작업이라고 생략하지 않는다.
- 프로젝트에 vitest나 E2E 환경이 없으면 실행하지 않은 이유를 보고에 밝힌다.

## 6. 커밋과 PR

- 커밋 메시지와 PR 초안은 `chucoding:commit-pr`을 따른다.
- PR 제목의 이슈 번호는 브랜치명에서 찾되, 브랜치명에 없으면 착수 입력의 GitHub 이슈 번호를 쓴다. `유형(61): 제목` 형태가 된다. 착수 이슈가 있는데 `NO-ISSUE`를 쓰지 않는다.
- PR 본문에는 `(#번호)`로 이슈를 참조한다. `Closes #번호` 같은 자동 종료 키워드는 임의로 넣지 않는다. 이슈를 닫는 시점은 사용자가 정한다.
- Assignee와 라벨은 `chucoding:commit-pr`의 `5. Assignee와 라벨`을 따른다.
- `chucoding:commit-pr`의 `7. PR 생성 후 티켓 상태 전환`은 Jira 티켓이 있을 때의 규칙이다. GitHub 이슈로 착수한 작업에서는 수행하지 않는다.

## 7. 이슈 종료

- 이슈는 사용자가 종료를 요청할 때만 닫는다. PR을 만들었다고 스스로 닫지 않는다.
- 닫기 전에 `gh pr view <PR번호> --repo <owner>/<repo> --json number,state,mergedAt,mergeCommit,baseRefName`으로 PR의 머지 여부를 조회한다. 조회하지 않은 상태로 머지됐다거나 머지되지 않았다고 쓰지 않는다.
- 닫기는 아래 형태로 실행한다. 어디서 처리됐는지 이슈만 보고 추적할 수 있도록 PR 링크를 댓글로 남긴다.

  ```bash
  gh issue close <번호> --repo <owner>/<repo> --reason completed \
    --comment "<한 줄 요약>. 관련 PR: https://github.com/<owner>/<repo>/pull/<PR번호>"
  ```

- 실행 후 `gh issue view <번호> --repo <owner>/<repo> --json number,state,stateReason,closedAt`으로 반영을 확인한다. 도구 성공 메시지로 대신하지 않는다.
- 이슈 내용대로 끝나지 않았으면 `--reason not planned`를 임의로 고르지 않고 어느 사유로 닫을지 되묻는다.
- 보고에는 이슈 상태, PR 머지 여부, 남은 후속 작업을 함께 적는다.

## Jira 규칙과 섞지 않기

- GitHub 이슈로 착수한 작업에서는 Jira 티켓을 만들지도, 상태를 바꾸지도, Actual start를 채우지도 않는다.
- 작업 도중 Jira 티켓이 필요해 보이면 만들지 말고 대화로 제안한 뒤 지시를 기다린다. `chucoding:jira`의 `티켓 생성` 규칙이 그대로 적용된다.
