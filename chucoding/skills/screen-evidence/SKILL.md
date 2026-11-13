---
name: screen-evidence
description: 화면이 바뀌는 작업의 변경 전(AS-IS)과 변경 후(TO-BE)를 GIF나 이미지로 남겨 GitHub PR 본문과 Jira 댓글(원장이 없으면 HDIT, `QA_Bug` HDIT, PM이나 운영의 스토리 원장)에 넣는 절차. 원장 댓글에 함께 넣는 기획 외 추가 적용 화면 캡처를 포함한다. 동작이 필요한지로 GIF와 이미지를 고르는 기준, 기존 기능 수정과 신규 기능, 레거시 이관, 벤치마킹에 따라 AS-IS 출처를 정하는 기준, ego-browser 녹화와 캡처, base 커밋으로 되돌린 AS-IS 녹화, ffmpeg GIF 인코딩, 동작 흐름이나 판정 기준이 바뀐 변경의 AS-IS와 TO-BE 시퀀스 다이어그램 PNG를 drawio로 렌더해 PR `변경 이유`에 넣는 절차, `gh pr create --attach` 업로드, Jira 첨부와 v2에서 v3로 이어지는 미디어 댓글 작성, 건너뛰는 조건을 포함한다. `chucoding:commit-pr`의 PR 생성 단계와 `chucoding:jira`의 개발완료 처리에서 호출한다. 사용자가 "GIF 녹화", "스크린샷 첨부", "AS-IS TO-BE", "변경 전후 영상", "PR에 GIF 넣어줘", "시퀀스 다이어그램", "흐름도 PR에 넣어줘"를 요청할 때도 사용한다.
---

# AS-IS와 TO-BE 화면 증빙

화면이 바뀌는 작업은 변경 전(AS-IS)과 변경 후(TO-BE)를 GIF나 이미지로 남겨 PR 본문과 Jira 댓글에 넣는다. 리뷰어와 QA가 PR이나 티켓을 열자마자 차이를 보게 하려는 것이다. 이 절차는 HDIT-4229(hd-cloud-client PR #2497)에서 사용자와 함께 확정했다.

동작 흐름이나 판정 기준이 바뀌어 화면만으로는 Why가 보이지 않는 변경은 AS-IS와 TO-BE 시퀀스 다이어그램도 같은 흐름(보관 폴더, `meta.txt`와 `pr-body.md`, `--attach`, Jira 첨부)으로 남긴다. 아래 `시퀀스 다이어그램` 절이 정본이다. 이 형식은 HDIT-6070(hd-cloud-client PR #2847)에서 사용자가 좋다고 평가해 정했다.

## 고정된 결정

아래는 사용자가 정한 것이라 바꾸지 않는다.

- **영상은 GIF로만 남긴다.** mp4로 올리거나 GIF와 함께 올리지 않는다. 0.4초짜리 전환은 영상이면 재생을 눌러도 순식간에 지나가지만, GIF는 자동으로 반복 재생돼 열자마자 보인다. 용량은 mp4의 약 3배지만 1MB 안팎이라 허용 범위다.
- **AS-IS가 있으면 AS-IS와 TO-BE를 좌우로 나란히 둔다.** PR과 Jira 모두 같다.
- **Jira 댓글에는 GitHub 링크를 넣지 않는다.** PR 링크도 넣지 않는다.

## 무엇을 남길지 정하기

녹화나 캡처를 시작하기 전에 아래 두 가지를 정한다. 근거는 티켓 제목과 설명, PR 의도 자료, diff다. 근거로 갈리지 않으면 추측하지 말고 되묻는다. 정한 값은 `meta.txt`에 남겨 개발완료 때 그대로 쓴다.

시퀀스 다이어그램을 함께 남길지는 아래 `시퀀스 다이어그램`의 `언제 만드는가`로 따로 정한다. 화면 증빙과 다이어그램은 서로 독립이라 둘 다, 한쪽만, 둘 다 없음이 모두 가능하다.

### 형식: GIF와 이미지

| 변경 성격 | 형식 | 예 |
|------|------|------|
| 확인하려면 동작이 필요하다 | GIF | 전환과 애니메이션, 클릭이나 입력에 따른 반응, 이동 순서, 로딩과 상태 변화 |
| 화면을 보면 확인된다 | 이미지(PNG) | 레이아웃, 문구, 색상, 정적 화면 신규 개발, 표시 값 |

- AS-IS와 TO-BE는 같은 형식으로 맞춘다. 한쪽만 동작이 필요하면 둘 다 GIF로 한다.
- 한 작업에 여러 화면이 있으면 화면마다 형식을 따로 정할 수 있다. 화면마다 한 행씩 쌓는다.

### AS-IS 출처

| 작업 종류 | AS-IS | 남기는 방법 |
|------|------|------|
| 기존 기능 수정 | 이 프로젝트의 변경 전 화면 | 아래 `AS-IS 녹화`처럼 변경 경로를 base 커밋으로 되돌려 남긴다 |
| 신규 기능 | 없음 | TO-BE만 남긴다 |
| 레거시 이관 | 이관 전 프로젝트의 같은 화면 | 레거시 서비스 주소에서 같은 경로와 조작으로 남긴다 |
| 벤치마킹 | 참고한 서비스의 화면 | 참고 서비스 주소에서 같은 경로와 조작으로 남긴다 |

- 레거시 이관과 벤치마킹은 캡션에 출처를 밝힌다. 예: `AS-IS(레거시 homedot-hub): …`, `AS-IS(벤치마킹 <서비스명>): …`. QA가 같은 프로젝트의 이전 화면으로 오해하지 않게 하려는 것이다.
- 레거시나 참고 서비스의 주소, 접속 계정, 대상 화면이 티켓에 없으면 되묻는다. 로그인이 필요한데 ego 브라우저에 로그인돼 있지 않으면 사용자에게 로그인을 부탁한다. 계정 정보를 대신 입력하지 않는다.
- 외부 서비스에서는 화면 이동과 조회만 한다. 저장, 삭제, 결제, 신청처럼 상대 서비스의 데이터를 바꾸는 조작은 하지 않는다.
- 기존 기능 수정이라도 변경 전 화면이 base 커밋에서 재현되지 않으면(예: 이미 운영 데이터가 바뀜) 그 사실을 밝히고 TO-BE만 남길지 되묻는다.

## 언제 남기고 어디에 쓰는가

| 시점 | 하는 일 | 호출하는 스킬 |
|------|------|------|
| PR 초안 제시 전 | GIF나 이미지를 만들어 PR 본문에 `--attach`로 넣는다 | `chucoding:commit-pr` |
| 개발완료 처리 | 같은 파일을 원장 티켓 댓글에 넣는다. 원장이 없으면 HDIT 티켓 댓글에도 넣고, 원장이 있으면 HDIT 댓글은 남기지 않는다. `QA_Bug` HDIT는 완료 댓글과 합친 한 댓글에 넣는다. 원장 판정과 댓글 형식의 정본은 `chucoding:jira`의 `원본 티켓 완료 댓글`이다 | `chucoding:jira` |

- 녹화와 캡처는 PR 초안을 제시하기 전에 한 번 한다. 개발완료 때 다시 하지 않는다.
- 작업 티켓이 원장(`chucoding:jira`의 `원장 판정`)에서 나온 개발 티켓이고 기획에 없던 동작을 따로 정해 적용했으면, 그 항목마다 화면을 하나씩 더 남긴다. 아래 `원장 댓글의 미디어`가 쓴다. 파일은 `<키>-extra-<번호>`로 두고 `meta.txt`에 `extra-<번호>: <항목 요약>` 줄을 항목 순서대로 남긴다. PR 본문에는 화면 증빙 블록 끝에 `**추가: <항목 요약>**` 줄과 `![<키>-extra-<번호>](./<키>-extra-<번호>.png)`를 같은 순서로 넣고, 그 파일도 `--attach`로 넘긴다. 원장 여부를 PR 시점에 알 수 없으면 티켓 설명의 `요청 출처:`나 연결된 스토리 티켓으로 보고, 애매하면 되묻는다.
- PR 생성 뒤 리뷰 반영으로 화면이 다시 바뀌었으면, Jira 댓글을 쓰기 전에 TO-BE만 다시 남긴다. 판정이 바뀌어 다이어그램이 달라졌으면 다이어그램 TO-BE도 다시 그린다. 이때 `gh pr edit --attach`로 PR 본문의 해당 TO-BE도 함께 바꾼다.
- GitHub 이슈로 착수한 작업(`chucoding:github-issue`)은 PR 절만 따른다. Jira 절은 수행하지 않는다.

### 보관 위치

스크래치패드는 세션마다 달라 PR 생성과 개발완료 처리 사이에 파일을 잃는다. 그래서 티켓별 고정 폴더에 둔다.

```
~/.cache/chucoding/screen-evidence/<티켓키>/
  <티켓키>-as-is.gif|png     # AS-IS가 있을 때만
  <티켓키>-to-be.gif|png
  <티켓키>-extra-<번호>.gif|png   # 원장 댓글에 넣을 기획 외 추가 적용 화면이 있을 때만
  meta.txt                   # 작업 브랜치, 형식, AS-IS 출처, 테스트방법 문구, 캡션, 다이어그램 여부
  pr-body.md                 # ./파일 상대 참조가 든 PR 본문 원본
  frames-as-is/, frames-to-be/   # GIF 녹화 프레임과 concat 목록
  <티켓키>-diagram-as-is.mmd|png   # 시퀀스 다이어그램을 남길 때만
  <티켓키>-diagram-to-be.mmd|png
```

- `meta.txt`에는 정한 형식과 AS-IS 출처, PR 본문과 Jira 댓글에 쓴 문구를 그대로 남긴다. 개발완료 때 같은 문구를 다시 쓰기 위해서다.
- `meta.txt`의 `format`은 `gif`, `png`, `none` 중 하나다. 화면마다 형식이 다르면 `gif,png`처럼 화면 순서대로 쉼표로 잇는다. `diagram`은 `yes`나 `no`이고, 줄이 없으면 `no`로 본다. 화면 증빙 없이 다이어그램만 남겼으면 `format: none`으로 적는다. 두 증빙을 함께 남기면 각자 끝날 때 자기 줄만 고쳐 쓴다. 다이어그램을 먼저 만들며 `format: none`을 적었더라도 화면 증빙을 남기면 실제 형식으로 바꾼다. 개발완료 때 `format: none`이면 화면 증빙이 없는 작업으로 보고, `format` 줄이 없으면(이 규칙 전의 폴더) 화면 증빙이 있는 것으로 본다. `meta.txt` 없이 PR에서 다시 받았으면 `<키>-as-is*`, `<키>-to-be*` alt의 파일이 있을 때만 화면 증빙이 있는 것으로 본다.
- `meta.txt` 첫 줄에는 `branch: <작업 브랜치>`를 적는다. 같은 티켓 키 폴더에 예전 작업의 파일이 남아 있어도, 개발완료 때 브랜치가 다르면 이번 증빙으로 쓰지 않게 하려는 것이다.
- PR 초안을 위해 증빙을 처음 만들 때와, 이미 열린 PR에 증빙을 넣어 달라는 직접 요청(아래 `GitHub PR에 넣기`의 예외)으로 만들 때는, 화면 증빙과 다이어그램 중 먼저 시작하는 쪽 전에 그 폴더의 기존 증빙 파일(`<키>-as-is*`, `<키>-to-be*`, `<키>-extra-*`, `<키>-diagram-*`, `meta.txt`, `pr-body.md`)을 한 번 지운다. 예전 작업의 파일이나 AS-IS가 없어진 재작업의 옛 AS-IS가 남지 않게 하려는 것이다. 나중에 시작하는 쪽에서 다시 지우면 먼저 만든 파일이 사라지므로 한 번만 지운다. 두 증빙을 모두 건너뛰기로 했을 때도 같은 파일을 지운다.
- PR 생성 뒤 리뷰 반영으로 한쪽만 다시 만들 때는 그쪽 파일만 지운다. 화면 TO-BE를 다시 남기면 `<키>-to-be*`만, 다이어그램 TO-BE를 다시 그리면 `<키>-diagram-to-be*`만 지우고 `meta.txt`와 `pr-body.md`는 남겨 해당 줄과 블록만 고친다. AS-IS는 base 기준이라 리뷰 반영으로 바뀌지 않는다.
- `pr-body.md`에는 `--attach`로 생성하기 전의 PR 본문을 그대로 남긴다. 생성 뒤 PR 본문의 `./파일` 참조는 업로드 주소로 바뀌어, 리뷰 반영으로 TO-BE를 다시 넣을 때 `gh pr edit --body-file`에 쓸 원본이 없어지기 때문이다. 다시 넣을 때는 현재 PR 본문에서 증빙 블록만 `pr-body.md`의 블록으로 바꿔 쓴다. 그사이 고친 다른 섹션을 되돌리지 않기 위해서다. 다이어그램 표도 있는 본문에서 화면 TO-BE만 다시 남겼으면 화면 증빙 블록만 바꾸고, 다이어그램 표는 현재 본문(이미 업로드 주소)을 그대로 두며 `--attach`에도 화면 파일만 넘긴다. 리뷰 반영으로 판정이 바뀌어 다이어그램을 고쳤으면 같은 방식으로 다이어그램 TO-BE 칸만 바꾸고 그 PNG를 `--attach`로 넘긴다. 화면은 그대로이고 다이어그램만 고쳤으면 화면 증빙 블록과 화면 파일은 건드리지 않는다.
- 화면이 여럿이면 파일 이름 끝에 화면 번호를 붙인다. 예: `<키>-to-be-1.png`, `<키>-to-be-2.gif`.
- 폴더와 파일 이름의 티켓 키는 브랜치 이름의 키다.
- 티켓 키가 없는 GitHub 이슈 경로면 `<저장소>-<이슈번호>`를 키 대신 쓴다.
- 개발완료 때 폴더에 파일이 없으면 PR에서 다시 받는다. `gh api repos/<o>/<r>/pulls/<n> -H "Accept: application/vnd.github.html+json" --jq .body_html`에서 `<img src="https://private-user-images…?jwt=…">`를 뽑아(`&amp;`는 `&`로) `curl -o`로 받는다. 주소가 `https://private-user-images.githubusercontent.com/`로 시작하고 `alt`가 보관 파일 이름(`<키>-as-is`, `<키>-to-be`, `<키>-extra-<번호>`, `<키>-diagram-as-is`, `<키>-diagram-to-be` 등, 아래 PR 본문 템플릿의 alt)과 맞는 것만 받는다. PR 본문은 다른 사람도 고칠 수 있어서다. 주소의 jwt는 보고나 로그에 그대로 남기지 않는다. jwt는 몇 분 안에 만료되므로 받기 직전에 조회한다. 받은 파일의 형식과 크기를 `file`과 `sips`로 확인한다. 받은 파일은 PR 생성 뒤 바뀌었을 수 있으므로 Read로 내용을 다시 보고 아래 `민감정보 확인`을 다시 한다. 다이어그램 PNG를 PR에서 다시 받았으면 `.mmd` 원본이 없으므로, 아래 `다이어그램을 넣는 범위`의 설명 중복 판정과 댓글의 `Mermaid 원본` `expand`를 생략하고 그 사실을 게시 전 출력에 밝힌다. 그리고 Jira에 올리기 전에 PR에서 다시 받은 파일이라는 사실과 파일 목록을 보여 주고 게시 여부를 묻는다. 개발완료 전환의 게시 승인은 보관 폴더의 파일에만 적용한다.

## 건너뛰는 조건

이 절은 화면 증빙(GIF와 이미지)의 조건이다. 시퀀스 다이어그램은 아래 `시퀀스 다이어그램`의 건너뛰는 조건을 따로 본다. 화면이 바뀌지 않는 BE 전용 변경도 판정 기준이 바뀌었으면 다이어그램은 남길 수 있다.

아래면 화면 증빙을 남기지 않고, 건너뛴 사실과 이유를 PR 초안 제시나 완료 보고에 한 줄로 남긴다.

- 화면이 바뀌지 않는 변경이다. BE 전용, 리팩터링, 문서, 설정, 테스트만 바뀐 경우다.
- 개발 서버를 띄울 수 없는 저장소이거나, 변경 화면에 들어갈 계정과 데이터가 없다.
- `ego-browser`를 쓸 수 없다.
- 사용자가 이번 작업은 남기지 않겠다고 밝혔다.
- macOS가 아니다. 크기 확인(`sips`)과 창 전면화(`open -a`)가 macOS 전용이다.

화면 변화 여부가 애매하면(예: 공통 컴포넌트 수정이 여러 화면에 번지는 경우) 남길 화면을 되묻는다.

화면 증빙을 남기지 않았으면(다이어그램만 남긴 경우 포함) Jira 쪽은 아래처럼 처리한다.

- HDIT 티켓의 `[개발완료]` 댓글은 남기지 않는다.
- 원본 티켓 완료 댓글은 미디어 블록 없이 `chucoding:jira`의 기존 형식대로 남긴다. 원장 댓글도 미디어 없이 남기며, 게시 전 검수는 그대로 받는다.

## 녹화와 캡처

### 준비

- 페이지를 열기 전에 `Skill` 도구로 `chucoding:browser-automation`을 호출한다. 스크립트에는 다이얼로그 무력화 주입이 이미 들어 있다.
- 개발 서버가 떠 있지 않으면 전역 AGENTS.md `개발 서버 지침`대로 띄운다. AS-IS가 레거시나 참고 서비스면 그 주소를 쓴다.
- GIF를 만들 때만 ffmpeg가 필요하다. 시스템 것을 쓰고, 없으면 스크래치패드에 `npm i ffmpeg-static@5.2.0`으로 받아 `node_modules/ffmpeg-static/ffmpeg`를 쓴다. 전역 설치는 하지 않는다. 아래에서 이 경로를 `$FF`라 부르고, 반드시 절대경로로 둔다. `encode.sh`가 프레임 폴더로 `cd`한 뒤 실행하므로 상대경로면 GIF 인코딩에서 실패한다.
- 화면 크기는 GIF와 이미지 모두 1440×900(16:10)으로 고정한다. 고정하지 않으면 ego 창 크기(예: 1908×807)를 따라 화면이 납작해지고, Jira에서 좌우로 놓으면 높이가 187px밖에 안 된다.
- 실제 사용 경로로 진입한다. 상세 URL로 바로 들어가면 앱 구조(KeepAliveOutlet 등)에 따라 동작이 달라질 수 있다.
- 스크립트의 `__KEY__`와 `__OUT__`은 sed로 JS 문자열 안에 그대로 들어간다. 치환 전에 키가 `^[A-Za-z0-9][A-Za-z0-9._-]*$`에 맞는지 확인하고, 맞지 않으면 멈춘다. 따옴표나 `#`가 섞이면 스크립트가 깨지거나 그 문자가 코드로 실행되기 때문이다. 아래 명령의 `KEY` 검사가 이 확인이다.

### 이미지 캡처

[`scripts/capture.mjs`](scripts/capture.mjs)를 스크래치패드에 복사해 진입 경로와 대기 조건을 고친다. `__OUT__`, `__NAME__`, `__KEY__`는 실행할 때 sed로 치환한다.

```bash
KEY=<키>; [[ "$KEY" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]] || { echo "키 형식 오류: $KEY"; exit 1; }
OUT=$HOME/.cache/chucoding/screen-evidence/$KEY/$KEY-to-be.png
sed -e "s#__OUT__#$OUT#" -e "s#__NAME__#TO-BE#" -e "s#__KEY__#$KEY#" capture.mjs | ego-browser nodejs
```

- 스켈레톤이나 로딩 표시가 사라진 뒤 캡처한다.
- 결과는 1440×900 PNG다. 화면 아래까지 담아야 하면 `captureBeyondViewport: true`로 바꾸고, 높이가 달라지므로 `sips`로 실제 크기를 확인해 Jira에 그 값을 쓴다.
- 캡처한 PNG를 Read로 열어 대상 화면이 담겼는지 눈으로 확인한다. 아래 `민감정보 확인`도 함께 한다.

### GIF 녹화

[`scripts/record.mjs`](scripts/record.mjs)를 스크래치패드에 복사해 진입 경로, 대기 조건, 조작 셀렉터, 녹화 시간을 작업에 맞게 고친다.

```bash
KEY=<키>; [[ "$KEY" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]] || { echo "키 형식 오류: $KEY"; exit 1; }
OUT=$HOME/.cache/chucoding/screen-evidence/$KEY/frames-to-be
(sed -e "s#__OUT__#$OUT#" -e "s#__NAME__#TO-BE#" -e "s#__KEY__#$KEY#" record.mjs | ego-browser nodejs) & sleep 3; open -a "ego lite"; wait
```

스크립트에 담긴 판단은 다음과 같다.

- **조작은 페이지 안에서 `setTimeout`으로 예약한다.** Node 쪽은 프레임 수신과 ack만 한다. Node에서 `evaluate`나 `click`을 섞으면 같은 연결을 쓰느라 프레임 수신이 끊긴다.
- **ack는 프레임을 받는 즉시 `await`로 보낸다.** 늦으면 프레임이 끊긴다.
- **화면이 바뀔 때만 프레임이 온다.** 정지 구간에는 프레임이 없고, concat 목록의 `duration`이 실제 시간을 지켜 준다.
- **ego 창을 앞으로 가져온다.** 창이 다른 창 뒤에 있으면 rAF가 초당 2회로 떨어져 애니메이션이 진행되지 않는다. 그래서 스크립트를 백그라운드로 띄운 뒤 `open -a "ego lite"`로 창을 앞으로 가져온다. 사용자 화면의 포커스를 ego가 가져가므로 녹화 전에 한 줄로 알린다.
- **rAF 횟수를 잰다.** 스크립트가 끝에 `{"frames":…,"rafPerSec":…}`를 출력한다. `rafPerSec`가 15 미만이면 창이 가려진 상태였으므로 다시 녹화한다.

### 실패했던 방법

다시 쓰지 않는다.

- **브라우저 안 MediaRecorder로 webm 인코딩**: AS-IS 영상이 멈춘 화면으로 인코딩돼 있었다.
- **macOS `screencapture -v`**: ego 앱이 Spaces 개요 화면으로 바뀌어 사용자 데스크톱을 건드린다.

### AS-IS 녹화(기존 기능 수정)

AS-IS 출처가 이 프로젝트의 변경 전 화면일 때만 쓴다. 레거시 이관과 벤치마킹은 그 서비스 주소로 위 스크립트를 그대로 돌린다.

개발 서버(Vite HMR)는 그대로 두고, 작업 트리의 변경 경로만 base 커밋으로 되돌려 녹화하거나 캡처한 뒤 바로 복원한다.

```bash
git diff --name-only --diff-filter=M <base커밋> HEAD -- <대상 경로>   # 변경 경로 목록
git status --short -- <변경 경로>            # 비어 있어야 진행
git checkout <base커밋> -- <변경 경로>       # AS-IS로 되돌림
sleep 4                                     # HMR 반영 대기
# … 녹화나 캡처 …
git checkout HEAD -- <변경 경로>             # 복원
git status --short -- <변경 경로>            # 비어 있는지 다시 확인
```

- **`git stash`는 쓰지 않는다.** stash 스택은 워크트리끼리 공유된다.
- base 커밋은 `chucoding:commit-pr`의 `### 1. PR 제안 시점` 통합 브랜치 판정으로 정한 base와의 merge-base다.
- base 커밋에 없는 신규 파일은 checkout으로 지워지지 않는다. 이전 코드가 import하지 않으면 남아 있어도 무해하다.
- 변경 경로에 커밋하지 않은 변경(staged, untracked 포함)이 있으면 되돌리지 않는다. 복원이 `HEAD` 기준이라 그 변경이 사라지기 때문이다. 먼저 커밋할지 사용자에게 묻고, 커밋한 뒤에 진행한다.
- `<변경 경로>`는 base와 HEAD 양쪽에 있는 수정 파일(`--diff-filter=M`)로 한정한다. 신규 파일을 넘기면 첫 checkout이, 삭제하거나 이름을 바꾼 파일을 넘기면 복원 checkout이 실패해 옛 파일이 작업 트리에 남는다.
- 삭제나 이름 변경이 AS-IS 재현에 꼭 필요하면 이 방법으로 되돌리지 않고, base 커밋을 따로 띄울 방법(예: 별도 워크트리의 개발 서버)을 사용자에게 묻는다.
- 녹화나 캡처가 중간에 실패해도 복원 명령은 반드시 실행하고, 마지막 `git status --short -- <변경 경로>`가 비어 있는지 확인한 뒤 다음 단계로 간다. 변경 경로 밖의 파일은 판정에 넣지 않는다.

### GIF 검증과 인코딩

[`scripts/encode.sh`](scripts/encode.sh)로 첫 프레임 크기 확인, 프레임 시트 생성, GIF 인코딩을 한 번에 한다. 경로는 절대경로로 넘긴다.

```bash
bash <이 스킬 디렉토리>/scripts/encode.sh "$FF" ~/.cache/chucoding/screen-evidence/<키>/frames-as-is ~/.cache/chucoding/screen-evidence/<키>/<키>-as-is.gif
```

- 첫 프레임이 1440×900인지 출력으로 확인한다.
- **프레임 시트(`sheet.png`)를 Read로 열어 눈으로 확인한다.** AS-IS에는 결함이나 이전 동작이, TO-BE에는 바뀐 동작이 실제로 담겼는지 본다. 담기지 않았으면 GIF를 쓰지 않고 다시 녹화한다. 아래 `민감정보 확인`도 함께 한다.
- 프레임이 0장이면 `record.mjs`와 `encode.sh` 모두 실패로 끝난다. 창 가림(`rafPerSec`)이나 조작 셀렉터를 확인하고 다시 녹화한다.
- 결과는 960×600 GIF다. 인코딩 옵션(`fps=25`, `palettegen=stats_mode=diff`, `paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle`, `-loop 0`)은 확정본이라 바꾸지 않는다.

### 민감정보 확인

증빙은 PR과 Jira(HDIT, 원장)에 그대로 올라가고, HDIT 게시는 개발완료 전환에 딸려 따로 승인받지 않는다(원장 댓글만 게시 전에 검수받는다). 그래서 파일을 만든 직후에 확인한다.

- GIF는 프레임 시트가 아니라 프레임 전체로 확인한다. 시트는 최대 12장 샘플이라 잠깐 비친 화면을 놓친다. 프레임 폴더의 JPEG를 전부 Read로 훑거나, 프레임이 많으면 `tile`로 여러 장의 시트를 나눠 만들어 전부 본다.

- 실제 고객 이름, 연락처, 주소, 계약 금액 같은 개인정보나 영업 정보가 보이는지 본다. 테스트 단지(예: 999999)와 테스트 계정을 쓰면 대부분 피할 수 있다.
- 레거시나 벤치마킹 서비스 화면에 로그인 계정 이름, 이메일, 상대 서비스의 비공개 데이터가 보이는지 본다.
- 보이면 쓰지 않고, 테스트 데이터로 다시 남기거나 그 영역을 가리는 방법을 사용자에게 묻는다. 그대로 올릴지는 사용자가 정한다.

## 시퀀스 다이어그램

동작 흐름이나 판정 기준이 바뀐 변경은 AS-IS와 TO-BE 시퀀스 다이어그램을 PNG로 렌더해 PR `변경 이유`에 넣는다. 화면 캡처는 결과만 보여 주므로, 어느 단계의 판정이 바뀌어 결과가 달라졌는지는 다이어그램으로 보인다.

### 언제 만드는가

- 요청이나 응답의 순서, 분기 조건, 검증과 필터 기준, 상태 전이처럼 여러 주체(사용자, FE, BE, 외부 시스템) 사이의 흐름이 바뀐 변경
- 화면 결과만 보면 무엇이 왜 달라졌는지 드러나지 않는 변경. 예: HDIT-6070은 FE 사전검증 기준을 BE 발송 필터와 맞췄고, 화면 캡처는 '실패' 표시만 보여 줬다
- BE 전용 변경이어도 해당한다. 화면 증빙의 건너뛰는 조건과 따로 판정한다

AS-IS 다이어그램은 base 커밋의 코드에서 확인한 흐름만 그린다. 레거시 이관과 벤치마킹처럼 이 저장소의 base 코드로 이전 흐름을 확인할 수 없으면 AS-IS 다이어그램은 만들지 않고 TO-BE만 남긴다. 신규 흐름도 TO-BE만 남긴다.

아래면 만들지 않고, 건너뛴 사실과 이유를 PR 초안 제시에 한 줄로 남긴다. 화면 증빙도 함께 건너뛰면 두 사실을 한 줄로 합친다.

- 흐름이나 판정이 바뀌지 않는다. 레이아웃, 문구, 색상, 리팩터링, 문서, 설정, 테스트만 바뀐 경우다.
- 바뀐 것이 한 주체 안의 계산 하나뿐이라 주체 사이의 메시지로 그릴 것이 없다.
- `drawio`가 없다. 다른 렌더 수단을 짐작해 고르지 않고 되묻는다.
- 사용자가 이번 작업은 다이어그램을 남기지 않겠다고 밝혔다.

애매하면 추측하지 말고 되묻는다. 화면 증빙과 달리 코드를 되돌리거나 ego 창을 앞으로 가져오는 부수효과가 없으므로, `chucoding:commit-pr`이 증빙 여부를 물은 뒤에는 따로 승인받지 않고 만들어 PR 초안에 보인다.

### 작성 규칙

- `sequenceDiagram`으로 쓴다. 참여자는 `actor 관리자`, `FE`, `BE`, `문자 발송`처럼 4개 안팎으로 둔다. 핵심 메시지만 남긴다.
- AS-IS와 TO-BE의 참여자와 메시지 순서를 같게 둔다. 좌우로 놓았을 때 달라진 줄만 눈에 띄게 하려는 것이다. TO-BE에서 새로 생긴 메시지는 같은 자리에 끼워 넣는다.
- 색상은 `rect`로 감싸 세 가지만 쓴다. `chucoding:jira` `다이어그램`의 `classDef` 세 색과 같은 값이다(`classDef`는 `sequenceDiagram`에서 쓸 수 없다).

  | 쓰는 곳 | `rect` | `classDef` 대응 |
  |------|------|------|
  | AS-IS의 문제 구간 | `rect rgb(248, 206, 204)` | `pain` `#f8cecc` |
  | TO-BE의 바뀐 판정 | `rect rgb(255, 242, 204)` | `changed` `#fff2cc` |
  | TO-BE의 결과 | `rect rgb(213, 232, 212)` | `good` `#d5e8d4` |

- 메시지 문구에 가운뎃점(`·`)과 줄표(`—`)를 쓰지 않는다. 나열은 쉼표로 쓰고, 줄을 나눌 때는 `<br/>`을 쓴다.
- 예시(HDIT-6070 TO-BE 일부)

  ```
  sequenceDiagram
      actor A as 관리자
      participant FE as FE 선거인명부
      participant BE as BE
      A->>FE: 명부 열기 / 대상 추가
      rect rgb(255, 242, 204)
      FE->>FE: 번호 검증 (010 + 8자리)
      end
      rect rgb(213, 232, 212)
      FE-->>A: 070, 011 번호는 '실패'<br/>유효하지 않은 휴대폰 번호
      end
  ```

### 렌더와 검증

원본은 보관 폴더에 `<키>-diagram-as-is.mmd`, `<키>-diagram-to-be.mmd`로 쓰고 같은 이름의 PNG로 렌더한다. 렌더 명령의 정본은 `chucoding:jira`의 `다이어그램`이다. 아래는 그 명령을 보관 폴더 이름에 맞춘 것이고, 명령을 바꿀 때는 두 곳을 함께 고친다.

```bash
KEY=<키>; [[ "$KEY" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]] || { echo "키 형식 오류: $KEY"; exit 1; }
mkdir -p ~/.cache/chucoding/screen-evidence/$KEY && cd ~/.cache/chucoding/screen-evidence/$KEY
for side in as-is to-be; do
  N=$KEY-diagram-$side; [ -f $N.mmd ] || continue
  drawio -x -f xml --mermaid-image 1 -o $N.drawio $N.mmd \
    && drawio -x -f png -e -b 10 -s 2 -o $N.png $N.drawio && rm $N.drawio
done
sips -g pixelWidth -g pixelHeight $KEY-diagram-*.png
```

- AS-IS가 없는 신규 흐름이면 `as-is.mmd`를 쓰지 않는다. 위 명령은 원본이 있는 쪽만 렌더한다.
- 렌더한 PNG를 Read로 열어 글자가 잘리거나 겹친 곳, Mermaid 문법 오류 상자가 없는지 본다. 있으면 원본을 고쳐 다시 렌더한다.
- 크기는 `sips` 출력으로 확인해 Jira에 그 값을 쓴다. HDIT-6070 실측은 2배 스케일로 약 1650×1900이었다.
- 다이어그램에도 `민감정보 확인`을 한다. 실제 고객 이름이나 연락처를 예시 값으로 넣지 않는다.

## GitHub PR에 넣기

- `gh --version`이 2.99.0 이상이어야 `--attach`가 있다. 낮으면 직접 업그레이드하지 않고 `brew upgrade gh`를 실행할지 사용자에게 묻는다. `gh image`라는 명령은 없다.
- **증빙은 PR을 만들 때 함께 넣는다.** 리뷰어가 PR을 처음 열 때부터 변경 전후를 보게 하려는 것이다. PR을 먼저 만들고 나중에 붙이지 않는다. 그래서 녹화와 캡처는 PR 초안을 제시하기 전에 끝낸다.
- 예외로 사용자가 이미 열린 PR에 증빙을 넣어 달라고 직접 요청하면, 현재 PR 본문(`gh pr view <번호> --json body`)의 테스트 섹션에 화면 증빙 블록을, 변경 이유의 문제 서술 아래에 다이어그램 표를 넣은 본문을 `pr-body.md`로 저장한다. 변경된 본문을 보여 주고 승인을 받은 뒤 `gh pr edit --body-file pr-body.md --attach …`로 올린다. 이 경우에도 녹화 전 `무엇을 남길지 정하기`와 `민감정보 확인`은 같다.
- 화면 증빙 블록은 저장소 PR 템플릿의 테스트 섹션(템플릿이 없으면 `chucoding:commit-pr` 3항목의 `테스트 방법`) 안에 둔다. 녹화와 캡처는 증빙 수집이라 테스트 실행 기록이 아니다. 테스트 섹션의 다른 항목은 `chucoding:commit-pr` 규칙대로 실제 실행한 테스트만 적는다.
- AS-IS가 있으면 2칸 표로 좌우 배치한다. GIF면 첫 줄 괄호에 `실제 속도, 반복 재생`을 붙이고, 이미지면 붙이지 않는다.

  ```markdown
  **녹화**: <진입 경로와 조작> (<환경>, 1440×900, 실제 속도, 반복 재생)

  | AS-IS: <한 줄 설명> | TO-BE: <한 줄 설명> |
  |---|---|
  | ![<키>-as-is](./<키>-as-is.gif) | ![<키>-to-be](./<키>-to-be.gif) |
  ```

- 신규 기능처럼 AS-IS가 없으면 표 없이 TO-BE만 둔다. 이미지면 첫 줄 제목을 `**캡처**`로 쓴다.

  ```markdown
  **캡처**: <진입 경로> (<환경>, 1440×900)

  **TO-BE: <한 줄 설명>**
  ![<키>-to-be](./<키>-to-be.png)
  ```

- 시퀀스 다이어그램은 `변경 이유`(템플릿이면 변경 이유를 옮겨 담는 목적과 결정 섹션)의 첫 문단, 즉 문제 서술 바로 아래에 캡션 없는 2칸 표로 둔다. 다이어그램은 Why를 보여 주는 것이라 테스트 섹션에 두지 않는다. AS-IS가 없으면 표 없이 이미지 한 줄만 둔다.

  ```markdown
  | AS-IS | TO-BE |
  |---|---|
  | ![<키>-diagram-as-is](./<키>-diagram-as-is.png) | ![<키>-diagram-to-be](./<키>-diagram-to-be.png) |
  ```

- `--attach`는 본문의 `![alt](./파일)` 참조를 업로드 주소로 바꾼다. 참조 문자열과 `--attach` 인자가 같아야 하므로 보관 폴더에서 `./<파일>` 형태로 넘긴다. 저장소 밖에서 실행하므로 저장소와 브랜치를 명시한다. 파일마다 `--attach`를 하나씩 붙인다. 다이어그램 PNG도 화면 증빙과 같은 `gh pr create`에 함께 넘긴다. `.mmd` 원본은 넘기지 않는다.

  ```bash
  cd ~/.cache/chucoding/screen-evidence/<키>
  gh pr create -R <owner>/<repo> --head <브랜치> --base <base> --title "…" --body-file <본문 파일> \
    --attach ./<키>-as-is.gif --attach ./<키>-to-be.gif --assignee @me
  # 리뷰 반영으로 화면 TO-BE나 다이어그램 TO-BE를 다시 남겼을 때만. 이미 열린 PR의 본문 교체(다시 남긴 파일만 넘김)
  gh pr edit <번호> -R <owner>/<repo> --body-file <본문 파일> --attach ./<키>-as-is.gif --attach ./<키>-to-be.gif
  ```

- PR 초안을 제시할 때는 본문의 참조가 `./<키>-to-be.gif` 같은 상대경로로 보이고, 생성 때 업로드 주소로 바뀐다는 점을 함께 알린다. 정한 형식과 AS-IS 출처도 한 줄로 함께 밝힌다. 다이어그램이 있으면 렌더한 PNG의 전체 경로와 Mermaid 원본을 함께 보인다.
- 일부 첨부만 실패해도 PR은 만들어지고 종료 코드가 0이 아니다. 출력된 PR URL을 확인하고 실패한 첨부를 보고한다.
- **업로드를 확인한다.** 비공개 저장소는 ego 브라우저가 GitHub에 로그인돼 있지 않으면 404다. 대신 `gh api repos/<o>/<r>/pulls/<n> -H "Accept: application/vnd.github.html+json" --jq .body_html`로 렌더링된 `<img src>` 중 `https://private-user-images.githubusercontent.com/`로 시작하는 것만 뽑아(`&amp;`는 `&`로) `curl -sI`로 `200`과 `content-type`(`image/gif` 또는 `image/png`), 바이트 수를 확인한다. 다이어그램 PNG도 같은 방법으로 확인한다.

## Jira 댓글에 넣기

`chucoding:jira`의 개발완료 처리에서 호출한다. 인증은 `~/.config/homedot-worktime/config.env`의 `JIRA_EMAIL`과 `JIRA_API_TOKEN`, 사이트는 `https://rsquare.atlassian.net`이다.

### 다이어그램을 넣는 범위

- 다이어그램은 화면 증빙에 딸려 간다. 화면 증빙이 있는 HDIT 증빙 댓글과 `QA_Bug` HDIT의 합친 댓글에만 넣는다. 자리는 화면 미디어 블록 아래다.
- 원장 완료 댓글에는 넣지 않는다. QA와 PM은 화면으로 확인하고, 흐름도는 개발 근거라 HDIT와 PR에 있으면 충분하다. 원장이 있는 작업은 HDIT 증빙 댓글도 남기지 않으므로 다이어그램은 PR에만 남는다.
- 화면 증빙 없이 다이어그램만 남긴 작업(`meta.txt`의 `format: none`)은 Jira에 넣지 않고 PR에만 둔다. `[개발완료]`와 `테스트방법 :` 머리가 맞지 않기 때문이다.
- 티켓 설명에 같은 다이어그램이 이미 있으면 넣지 않는다. 판정 대상은 댓글을 다는 HDIT 티켓의 설명이다. `GET /rest/api/3/issue/<HDIT키>?fields=description`의 ADF에서 `expand`(`attrs.title`이 `Mermaid 원본`) 안 `codeBlock` 텍스트를 모아, 보관 폴더의 `.mmd`와 공백을 정규화해 비교한다. 남긴 `.mmd`가 모두(AS-IS가 없으면 TO-BE 하나) 일치할 때만 건너뛰고 그 사실을 완료 보고에 한 줄로 남긴다. 하나라도 다르면 남긴 다이어그램을 모두 넣는다. 첨부 파일 이름으로는 판정하지 않는다. 설명에 붙인 다이어그램은 이름 규칙이 다를 수 있다(HDIT-6070은 `HDIT-voter-phone-*`).

### HDIT 댓글 형식

```
[개발완료]
테스트방법 : 단지 999999 목록 > 상세 진입 후 다음 → 이전, 실제 속도, 반복 재생
```

- 두 줄은 한 paragraph 안에서 `hardBreak`로 나눈다. 링크 mark는 넣지 않는다.
- `테스트방법 :` 뒤에는 녹화하거나 캡처한 진입 경로와 조작을 적는다. GIF면 끝에 `실제 속도, 반복 재생`을 붙이고, 이미지면 붙이지 않는다. `meta.txt`의 문구를 쓴다.
- 이슈 유형이 `QA_Bug`인 HDIT면 이 두 줄 앞에 `chucoding:jira`의 `QA_Bug 티켓`에 정한 멘션 문단과 `[추가로 수정된것]` 본문이 온다. 두 줄과 미디어 배치는 그대로다.
- 그 아래에 AS-IS가 있으면 좌우 두 열(`AS-IS: <한 줄 설명>`과 파일, `TO-BE: <한 줄 설명>`과 파일)을 두고, 없으면 `TO-BE: <한 줄 설명>` 문단과 파일 하나만 둔다.

### 미디어 블록 만들기

v3 ADF로 미디어를 넣으려면 media 파일 id(UUID)가 필요한데, `GET /rest/api/3/attachment/<id>`의 `mediaApiFileId`는 null로 온다. 그래서 v2 위키 마크업으로 한 번 써서 Jira가 media 노드를 만들게 한 뒤, v3로 다시 쓴다. 티켓마다 아래를 따로 한다.

1. **파일을 그 티켓에 첨부한다.** `POST /rest/api/3/issue/<키>/attachments`, multipart, 헤더 `X-Atlassian-Token: no-check`, 파일 `Content-Type`은 `image/gif` 또는 `image/png`. media는 티켓 단위라 HDIT에 붙인 첨부를 원장 티켓에서 쓸 수 없다. HDIT와 원장 각각에 댓글을 다는 티켓마다 첨부한다. `QA_Bug` HDIT의 합친 댓글은 그 댓글에 쓸 파일을 그 HDIT에 한 번만 첨부한다.
2. **v2로 댓글을 처음 쓴다.** `POST /rest/api/2/issue/<키>/comment`에 머리 문장과 파일 마크업을 함께 보낸다. 파일은 `!<파일명>|width=<w>,height=<h>!`로 쓴다. 원장 댓글이거나 `QA_Bug` HDIT의 합친 댓글이면 멘션을 `[~accountid:<accountId>]`로 이 단계에 넣는다. 멘션 알림은 댓글을 처음 만들 때 확실히 가므로, 수정 단계에서 처음 넣지 않는다. 파일명은 그 티켓에 첨부한 이름이고, width와 height는 파일 실제 크기다(GIF 960×600, 이미지 1440×900. 다르면 `sips`로 잰 값). **width와 height를 둘 다 준다.** width만 주면 Jira가 height를 엉뚱하게 채워(실측 960×183) 플레이어가 납작해진다.
3. **media id를 읽는다.** `GET /rest/api/3/issue/<키>/comment/<id>`의 본문을 재귀로 훑어 `type: media` 노드의 `attrs.id`를 모은다. 첨부한 파일 수와 다르면 멈추고 보고한다.
4. **v3로 전체를 다시 쓴다.** `PUT /rest/api/3/issue/<키>/comment/<id>`에 머리 문단과 미디어 블록을 담는다. media `attrs`는 `{"id": "<media id>", "type": "file", "collection": "<읽은 값>", "width": <w>, "height": <h>}`로 둔다. `collection`은 3단계에서 읽은 값을 그대로 쓰고, width와 height는 2단계와 같다.

AS-IS가 있으면 `layoutSection`으로 좌우 배치한다.

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

AS-IS가 없으면 `layoutSection` 없이 캡션 paragraph와 `mediaSingle`(`layout: center`, `width: 100`, `widthType: percentage`)만 둔다. 화면이 여럿이면 화면마다 위 블록을 이어 붙인다.

다이어그램을 넣으면 화면 미디어 블록 뒤에 같은 `layoutSection`을 하나 더 두고 캡션을 `AS-IS 흐름`, `TO-BE 흐름`으로 쓴다. AS-IS 다이어그램이 없으면 `layoutSection` 없이 `TO-BE 흐름` 캡션과 `mediaSingle` 하나만 둔다. media `width`와 `height`는 `sips`로 잰 PNG 크기다. 그 뒤 최상위에 `expand`(`attrs.title`은 `Mermaid 원본`) 하나를 두고 AS-IS, TO-BE 원본을 그 순서로 `codeBlock`에 넣는다. `layoutColumn` 안에 넣지 않는 것은 `chucoding:jira` `다이어그램`과 같다. 1단계 첨부와 2단계 v2 파일 마크업에 다이어그램 PNG도 화면 파일 뒤에 넣어, 3단계에서 읽는 media id 순서가 화면, 다이어그램 순이 되게 한다.

- HDIT 댓글이면 머리 문단은 `[개발완료]`, `hardBreak`, `테스트방법 : …`이다.
- `QA_Bug` HDIT의 합친 댓글이면 머리는 멘션 문단, 본문 제목, 목록, `[개발완료]`와 `테스트방법 :` 문단 순이다. 2단계의 멘션 삽입, 3단계의 멘션 확인, 4단계의 mention 노드 재사용은 아래 원장 댓글과 같이 한다.
- 원장 댓글이면 머리는 `chucoding:jira`의 `원장 완료 댓글` ADF 전체(멘션 문단, 본문 제목, 목록)이고, 미디어 배치는 아래 `원장 댓글의 미디어`를 따른다. 3단계에서 media id와 함께 `type: mention` 노드의 `attrs.id`도 모아, 의도한 멘션 대상이 모두 있는지 확인한다. 빠졌으면 4단계로 가지 말고 그 사실을 보고하고 되묻는다. 4단계에서는 3단계에서 읽은 mention 노드를 그대로 옮겨 쓴다.
- 2단계 이후 실패하면 재시도하지 말고 남은 댓글 id와 상태를 보고한다. v2로 쓴 댓글이 그대로 남아 있으면 지우지 않고 그 사실을 보고한다.

### 원장 댓글의 미디어

`chucoding:jira`의 `원장 완료 댓글`이 쓰는 미디어다. 댓글 형식과 게시 승인은 그쪽이 정본이고, 이 절은 어떤 파일을 어떻게 놓을지만 정한다.

- 원장 댓글은 후속 개발 티켓이 모두 끝났을 때 한 번 달리므로, 여러 티켓의 증빙이 한 댓글에 모일 수 있다. 후속 개발 티켓마다 그 키의 보관 폴더를 찾고, 폴더의 `meta.txt` 브랜치가 그 티켓의 작업 브랜치(그 티켓 PR의 `headRefName`)와 같을 때만 쓴다. 이번 작업 브랜치와 비교하지 않는다. 폴더가 없으면 위 `보관 위치`의 PR 재다운로드를 따른다.
- 배치는 티켓마다 화면 미디어 블록(AS-IS와 TO-BE 좌우, AS-IS가 없으면 TO-BE 하나)을 두고, 모든 티켓의 블록 뒤에 `[기획 외 추가 적용]` 화면을 하나씩 둔다. 티켓 순서와 추가 화면 순서는 티켓 키 오름차순, 그 안에서 `meta.txt`의 `extra-<번호>` 순이다. 추가 화면은 캡션 paragraph(`meta.txt`의 `<항목 요약>`)와 `mediaSingle`이고, 파일 이름은 `<키>-extra-<번호>.png|gif`다. 캡처와 녹화 방법은 TO-BE와 같다.
- 보관 폴더가 없어 PR에서 다시 받았으면 `meta.txt`가 없으므로, 추가 화면의 캡션은 PR 본문의 `**추가: <항목 요약>**` 줄에서, 순서는 alt의 번호에서 읽는다. 브랜치 대조는 생략한다. PR을 그 티켓 키로 찾았기 때문이다.
- `[기획 외 추가 적용]` 항목의 화면이 보관 폴더에 없으면 개발완료 때 새로 찍지 않는다. 빠진 항목을 알리고 그 화면 없이 게시할지, 사용자가 캡처를 지시할지 묻는다.
- 게시 전 검수에서 붙일 파일의 전체 경로와 순서를 보이고, 각 파일을 Read로 열어 함께 보인다. 승인받은 파일만 원장 티켓에 첨부한다.

### 화면 확인

- ego 브라우저로 `https://rsquare.atlassian.net/browse/<키>?focusedCommentId=<id>`를 연다. `media-cdn.atlassian.com` 이미지가 첨부한 수만큼 뜨는지, AS-IS가 있으면 두 개가 같은 높이로 나란히 뜨는지 본다(HDIT-4229 실측: 각 442×276).
- 스크린샷 전체 경로와 댓글 링크를 보고에 남기고, 확인을 마치면 태스크 스페이스를 닫는다.
