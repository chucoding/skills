---
name: ticket-gif
description: 화면 동작이 바뀌는 작업의 변경 전(AS-IS)과 변경 후(TO-BE)를 GIF로 녹화해 GitHub PR 본문과 Jira 댓글에 좌우로 나란히 넣는 절차. ego-browser 화면 녹화, base 커밋으로 되돌린 AS-IS 녹화, ffmpeg GIF 인코딩, `gh pr create --attach` 업로드, Jira 첨부와 v2에서 v3로 이어지는 미디어 댓글 작성, 건너뛰는 조건을 포함한다. `chucoding:commit-pr`의 PR 생성 단계와 `chucoding:jira`의 개발완료 처리에서 호출한다. 사용자가 "GIF 녹화", "AS-IS TO-BE", "변경 전후 영상", "PR에 GIF 넣어줘"를 요청할 때도 사용한다.
---

# AS-IS와 TO-BE GIF 증빙

화면 동작이 바뀌는 작업은 변경 전(AS-IS)과 변경 후(TO-BE)를 녹화한 GIF를 PR 본문과 Jira 댓글에 넣는다. 리뷰어와 QA가 PR이나 티켓을 열자마자 차이를 보게 하려는 것이다. 이 절차는 HDIT-4229(hd-cloud-client PR #2497)에서 사용자와 함께 확정했다.

## 고정된 결정

아래는 사용자가 정한 것이라 바꾸지 않는다.

- **형식은 GIF만 쓴다.** mp4와 함께 올리지 않는다. 0.4초짜리 전환은 영상이면 재생을 눌러도 순식간에 지나가지만, GIF는 자동으로 반복 재생돼 열자마자 보인다. 용량은 mp4의 약 3배지만 1MB 안팎이라 허용 범위다.
- **AS-IS와 TO-BE는 좌우로 나란히 둔다.** PR과 Jira 모두 같다.
- **Jira 댓글에는 GitHub 링크를 넣지 않는다.** PR 링크도 넣지 않는다.

## 언제 녹화하고 어디에 쓰는가

| 시점 | 하는 일 | 호출하는 스킬 |
|------|------|------|
| PR 생성 직전 | 녹화하고 GIF를 만들어 PR 본문에 `--attach`로 넣는다 | `chucoding:commit-pr` |
| 개발완료 처리 | 같은 GIF를 HDIT 티켓과 원본(HC, HOM) 티켓 댓글에 넣는다 | `chucoding:jira` |

- 녹화는 PR 생성 직전에 한 번 한다. 개발완료 때 다시 녹화하지 않는다.
- PR 생성 뒤 리뷰 반영으로 화면 동작이 다시 바뀌었으면, Jira 댓글을 쓰기 전에 TO-BE만 다시 녹화한다. 이때 `gh pr edit --attach`로 PR 본문의 TO-BE도 함께 바꾼다.
- GitHub 이슈로 착수한 작업(`chucoding:github-issue`)은 PR 절만 따른다. Jira 절은 수행하지 않는다.

### 보관 위치

스크래치패드는 세션마다 달라 PR 생성과 개발완료 처리 사이에 GIF를 잃는다. 그래서 티켓별 고정 폴더에 둔다.

```
~/.cache/chucoding/ticket-gif/<티켓키>/
  <티켓키>-as-is.gif
  <티켓키>-to-be.gif
  meta.txt              # 테스트방법 문구와 AS-IS, TO-BE 한 줄 설명
  frames-as-is/, frames-to-be/   # 녹화 프레임과 concat 목록
```

- `meta.txt`에는 PR 본문과 Jira 댓글에 쓴 문구를 그대로 남긴다. 개발완료 때 같은 문구를 다시 쓰기 위해서다.
- GIF 이름은 `<티켓키>-as-is.gif`, `<티켓키>-to-be.gif`로 한다. 티켓 키가 없는 GitHub 이슈 경로면 `<저장소>-<이슈번호>`를 쓴다.
- 개발완료 때 폴더에 GIF가 없으면 PR에서 다시 받는다. `gh api repos/<o>/<r>/pulls/<n> -H "Accept: application/vnd.github.html+json" --jq .body_html`에서 `<img src="https://private-user-images…gif?jwt=…">`를 뽑아(`&amp;`는 `&`로) `curl -o`로 받는다. jwt는 몇 분 안에 만료되므로 받기 직전에 조회한다. 받은 파일이 `image/gif`이고 960×600인지 확인한다.

## 건너뛰는 조건

아래면 녹화하지 않고, 건너뛴 사실과 이유를 PR 초안 제시나 완료 보고에 한 줄로 남긴다.

- 화면 동작이 바뀌지 않는 변경이다. BE 전용, 리팩터링, 문서, 설정, 테스트만 바뀐 경우다.
- 개발 서버를 띄울 수 없는 저장소이거나, 변경 화면에 들어갈 계정과 데이터가 없다.
- `ego-browser`를 쓸 수 없다.
- 사용자가 이번 작업은 녹화하지 않겠다고 밝혔다.

화면 변화 여부가 애매하면(예: 공통 컴포넌트 수정이 여러 화면에 번지는 경우) 녹화할 화면을 되묻는다.

GIF가 없으면 Jira 쪽은 아래처럼 처리한다.

- HDIT 티켓의 `[개발완료]` GIF 댓글은 남기지 않는다.
- 원본 티켓 완료 댓글은 GIF 블록 없이 `chucoding:jira`의 기존 형식대로 남긴다.

## 녹화

### 준비

- 페이지를 열기 전에 `Skill` 도구로 `chucoding:browser-automation`을 호출한다. 녹화 스크립트에는 다이얼로그 무력화 주입이 이미 들어 있다.
- 개발 서버가 떠 있지 않으면 전역 AGENTS.md `개발 서버 지침`대로 띄운다.
- ffmpeg는 시스템 것을 쓰고, 없으면 스크래치패드에 `npm i ffmpeg-static@5.2.0`으로 받아 `node_modules/ffmpeg-static/ffmpeg`를 쓴다. 전역 설치는 하지 않는다. 아래에서 이 경로를 `$FF`라 부른다.

### 녹화 스크립트

[`scripts/record.mjs`](scripts/record.mjs)를 스크래치패드에 복사해 진입 경로, 대기 조건, 조작 셀렉터, 녹화 시간을 작업에 맞게 고친다. `__OUT__`, `__NAME__`, `__KEY__`는 실행할 때 sed로 치환한다.

```bash
OUT=~/.cache/chucoding/ticket-gif/<키>/frames-to-be
(sed -e "s#__OUT__#$OUT#" -e "s#__NAME__#TO-BE#" -e "s#__KEY__#<키>#" record.mjs | ego-browser nodejs) & sleep 3; open -a "ego lite"; wait
```

스크립트에 담긴 판단은 다음과 같다.

- **화면 크기를 1440×900(16:10)으로 고정한다.** 고정하지 않으면 ego 창 크기(예: 1908×807)를 따라 영상이 납작해지고, Jira에서 좌우로 놓으면 높이가 187px밖에 안 된다.
- **실제 사용 경로로 진입한다.** 상세 URL로 바로 들어가면 앱 구조(KeepAliveOutlet 등)에 따라 동작이 달라질 수 있다.
- **조작은 페이지 안에서 `setTimeout`으로 예약한다.** Node 쪽은 프레임 수신과 ack만 한다. Node에서 `evaluate`나 `click`을 섞으면 같은 연결을 쓰느라 프레임 수신이 끊긴다.
- **ack는 프레임을 받는 즉시 `await`로 보낸다.** 늦으면 프레임이 끊긴다.
- **화면이 바뀔 때만 프레임이 온다.** 정지 구간에는 프레임이 없고, concat 목록의 `duration`이 실제 시간을 지켜 준다.
- **ego 창을 앞으로 가져온다.** 창이 다른 창 뒤에 있으면 rAF가 초당 2회로 떨어져 애니메이션이 진행되지 않는다. 그래서 스크립트를 백그라운드로 띄운 뒤 `open -a "ego lite"`로 창을 앞으로 가져온다. 사용자 화면의 포커스를 ego가 가져가므로 녹화 전에 한 줄로 알린다.
- **rAF 횟수를 잰다.** 스크립트가 끝에 `{"frames":…,"rafPerSec":…}`를 출력한다. `rafPerSec`가 15 미만이면 창이 가려진 상태였으므로 다시 녹화한다.

### 실패했던 방법

다시 쓰지 않는다.

- **브라우저 안 MediaRecorder로 webm 인코딩**: AS-IS 영상이 멈춘 화면으로 인코딩돼 있었다.
- **macOS `screencapture -v`**: ego 앱이 Spaces 개요 화면으로 바뀌어 사용자 데스크톱을 건드린다.

### AS-IS 녹화

개발 서버(Vite HMR)는 그대로 두고, 작업 트리의 변경 경로만 base 커밋으로 되돌려 녹화한 뒤 바로 복원한다.

```bash
git status --short                          # 시작 전 깨끗한지 확인
git checkout <base커밋> -- <변경 경로>       # AS-IS로 되돌림
sleep 4                                     # HMR 반영 대기
# … 녹화 …
git checkout HEAD -- <변경 경로>             # 복원
git status --short                          # 깨끗한지 다시 확인
```

- **`git stash`는 쓰지 않는다.** stash 스택은 워크트리끼리 공유된다.
- base 커밋은 `chucoding:commit-pr`의 `### 1. PR 제안 시점` 통합 브랜치 판정으로 정한 base와의 merge-base다.
- base 커밋에 없는 신규 파일은 checkout으로 지워지지 않는다. 이전 코드가 import하지 않으면 남아 있어도 무해하다.
- 커밋하지 않은 변경이 있으면 먼저 `git diff > <스크래치패드>/patch`로 떠 두고, 복원 뒤 `git diff`의 해시를 대조한다.

### 녹화 검증과 인코딩

[`scripts/encode.sh`](scripts/encode.sh)로 첫 프레임 크기 확인, 프레임 시트 생성, GIF 인코딩을 한 번에 한다. 경로는 절대경로로 넘긴다.

```bash
bash encode.sh "$FF" ~/.cache/chucoding/ticket-gif/<키>/frames-as-is ~/.cache/chucoding/ticket-gif/<키>/<키>-as-is.gif
```

- 첫 프레임이 1440×900인지 출력으로 확인한다.
- **프레임 시트(`sheet.png`)를 Read로 열어 눈으로 확인한다.** AS-IS에는 결함 장면이, TO-BE에는 고친 장면이 실제로 담겼는지 본다. 담기지 않았으면 GIF를 쓰지 않고 다시 녹화한다.
- 결과는 960×600 GIF다. 인코딩 옵션(`fps=25`, `palettegen=stats_mode=diff`, `paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle`, `-loop 0`)은 확정본이라 바꾸지 않는다.

## GitHub PR에 넣기

- `gh --version`이 2.99.0 이상이어야 `--attach`가 있다. 낮으면 직접 업그레이드하지 않고 `brew upgrade gh`를 실행할지 사용자에게 묻는다. `gh image`라는 명령은 없다.
- 녹화 블록은 저장소 PR 템플릿의 테스트 섹션(hd-cloud-client는 `테스트 방법`, 템플릿이 없으면 `How to test`) 안에 둔다. 녹화는 증빙 수집이라 테스트 실행 기록이 아니다. 테스트 섹션의 다른 항목은 `chucoding:commit-pr` 규칙대로 실제 실행한 테스트만 적는다.

  ```markdown
  **녹화** — <진입 경로와 조작> (<환경>, 1440×900, 실제 속도, 반복 재생)

  | AS-IS: <한 줄 설명> | TO-BE: <한 줄 설명> |
  |---|---|
  | ![AS-IS](./<키>-as-is.gif) | ![TO-BE](./<키>-to-be.gif) |
  ```

- `--attach`는 본문의 `![alt](./파일.gif)` 참조를 업로드 주소로 바꾼다. 참조 문자열과 `--attach` 인자가 같아야 하므로 GIF 폴더에서 `./<키>-as-is.gif` 형태로 넘긴다. 저장소 밖에서 실행하므로 저장소와 브랜치를 명시한다.

  ```bash
  cd ~/.cache/chucoding/ticket-gif/<키>
  gh pr create -R <owner>/<repo> --head <브랜치> --base <base> --title "…" --body-file <본문 파일> \
    --attach ./<키>-as-is.gif --attach ./<키>-to-be.gif --assignee @me --label <라벨>
  # 이미 열린 PR
  gh pr edit <번호> -R <owner>/<repo> --body-file <본문 파일> --attach ./<키>-as-is.gif --attach ./<키>-to-be.gif
  ```

- PR 초안을 제시할 때는 본문의 GIF 참조가 `./<키>-as-is.gif` 상대경로로 보이고, 생성 때 업로드 주소로 바뀐다는 점을 함께 알린다.
- 일부 첨부만 실패해도 PR은 만들어지고 종료 코드가 0이 아니다. 출력된 PR URL을 확인하고 실패한 첨부를 보고한다.
- **업로드를 확인한다.** 비공개 저장소는 ego 브라우저가 GitHub에 로그인돼 있지 않으면 404다. 대신 `gh api repos/<o>/<r>/pulls/<n> -H "Accept: application/vnd.github.html+json" --jq .body_html`로 렌더링된 `<img src>` 두 개를 뽑아(`&amp;`는 `&`로) `curl -sI`로 `200`과 `content-type: image/gif`, 바이트 수를 확인한다.

## Jira 댓글에 넣기

`chucoding:jira`의 개발완료 처리에서 호출한다. 인증은 `~/.config/homedot-worktime/config.env`의 `JIRA_EMAIL`과 `JIRA_API_TOKEN`, 사이트는 `https://rsquare.atlassian.net`이다.

### HDIT 댓글 형식

```
[개발완료]
테스트방법 : 단지 999999 목록 > 상세 진입 후 다음 → 이전, 실제 속도, 반복 재생
```

- 두 줄은 한 paragraph 안에서 `hardBreak`로 나눈다. 링크 mark는 넣지 않는다.
- `테스트방법 :` 뒤에는 녹화한 진입 경로와 조작을 적고 끝에 `실제 속도, 반복 재생`을 붙인다. `meta.txt`의 문구를 쓴다.
- 그 아래 좌우 두 열에 `AS-IS: <한 줄 설명>`과 GIF, `TO-BE: <한 줄 설명>`과 GIF를 둔다.

### 미디어 블록 만들기

v3 ADF로 미디어를 넣으려면 media 파일 id(UUID)가 필요한데, `GET /rest/api/3/attachment/<id>`의 `mediaApiFileId`는 null로 온다. 그래서 v2 위키 마크업으로 한 번 써서 Jira가 media 노드를 만들게 한 뒤, v3로 다시 쓴다. 티켓마다 아래를 따로 한다.

1. **GIF를 그 티켓에 첨부한다.** `POST /rest/api/3/issue/<키>/attachments`, multipart, 헤더 `X-Atlassian-Token: no-check`, 파일 `Content-Type: image/gif`. media는 티켓 단위라 HDIT에 붙인 첨부를 원본 티켓에서 쓸 수 없다. HDIT, HC, HOM 각각에 첨부한다.
2. **v2로 GIF만 담은 댓글을 쓴다.** `POST /rest/api/2/issue/<키>/comment`에 `{"body": "!<키>-as-is.gif|width=960,height=600! !<키>-to-be.gif|width=960,height=600!"}`. 파일명은 그 티켓에 첨부한 이름이다. **width와 height를 둘 다 준다.** width만 주면 Jira가 height를 엉뚱하게 채워(실측 960×183) 플레이어가 납작해진다.
3. **media id를 읽는다.** `GET /rest/api/3/issue/<키>/comment/<id>`의 본문을 재귀로 훑어 `type: media` 노드의 `attrs.id`를 모은다. 2개가 아니면 멈추고 보고한다.
4. **v3로 전체를 다시 쓴다.** `PUT /rest/api/3/issue/<키>/comment/<id>`에 머리 문단과 아래 `layoutSection`을 담는다. media `attrs`는 `{"id": "<media id>", "type": "file", "collection": "<읽은 값>", "width": 960, "height": 600}`로 둔다. `collection`은 3단계에서 읽은 값을 그대로 쓴다.

```json
{
  "type": "layoutSection",
  "content": [
    {"type": "layoutColumn", "attrs": {"width": 50}, "content": [
      {"type": "paragraph", "content": [{"type": "text", "text": "AS-IS: <한 줄 설명>"}]},
      {"type": "mediaSingle", "attrs": {"layout": "center", "width": 100, "widthType": "percentage"},
       "content": [{"type": "media", "attrs": {"id": "<AS-IS media id>", "type": "file", "collection": "<collection>", "width": 960, "height": 600}}]}
    ]},
    {"type": "layoutColumn", "attrs": {"width": 50}, "content": [
      {"type": "paragraph", "content": [{"type": "text", "text": "TO-BE: <한 줄 설명>"}]},
      {"type": "mediaSingle", "attrs": {"layout": "center", "width": 100, "widthType": "percentage"},
       "content": [{"type": "media", "attrs": {"id": "<TO-BE media id>", "type": "file", "collection": "<collection>", "width": 960, "height": 600}}]}
    ]}
  ]
}
```

- HDIT 댓글이면 머리 문단은 `[개발완료]`, `hardBreak`, `테스트방법 : …`이다.
- 원본(HC, HOM) 댓글이면 머리는 `chucoding:jira`의 `원본 티켓 완료 댓글` ADF 전체(멘션 문단, 본문 제목, 목록)이고, 그 뒤에 같은 `layoutSection`을 붙인다. v2 마크업에는 mention 노드를 넣기 어려우므로, 2단계에서는 GIF만 쓰고 멘션은 4단계 v3에서 넣는다. 수정으로 추가한 멘션에도 알림이 가는지는 이 순서로 처음 게시할 때 멘션 대상의 알림 수신을 사용자에게 확인받고, 가지 않으면 그 사실을 이 스킬에 반영한다.
- 2단계 이후 실패하면 재시도하지 말고 남은 댓글 id와 상태를 보고한다. GIF만 담긴 v2 댓글이 남아 있으면 지우지 않고 그 사실을 보고한다.

### 화면 확인

- ego 브라우저로 `https://rsquare.atlassian.net/browse/<키>?focusedCommentId=<id>`를 연다. `media-cdn.atlassian.com` 이미지 2개가 같은 높이로 나란히 뜨는지 본다(HDIT-4229 실측: 각 442×276).
- 스크린샷 전체 경로와 댓글 링크를 보고에 남기고, 확인을 마치면 태스크 스페이스를 닫는다.
