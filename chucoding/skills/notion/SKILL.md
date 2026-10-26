---
name: notion
description: Notion 페이지를 읽거나 수정할 때 따르는 작성 규칙. Notion 마크다운 규격(테이블 문법, 특수문자 이스케이프, 구분선 금지), 한국어 작성과 Mermaid 다이어그램 활용, 아키텍처 구조도를 drawio로 그려 PNG로 업로드하는 절차, MCP 인증이 끊겼을 때 로그인 창을 띄우는 재연결 절차, 접근 실패 시 공유 설정 안내를 포함한다. Notion 링크나 페이지 UUID가 주어지거나 Notion 문서를 읽고 쓰라는 요청이 있을 때 사용한다.
---

Notion 페이지 URL이나 UUID가 주어지거나 Notion 문서를 읽고 쓰라는 요청이 있을 때 이 스킬을 적용한다. 수정 전 조회와 최소 범위 수정, Notion 마크다운 규격(`notion://docs/notion-flavored-markdown-spec`) 확인은 Notion MCP 도구 설명을 따르고, 이 스킬은 그 위에 더하는 작성 규칙과 연결, 접근 실패 처리만 다룬다.

### 1. Notion용 마크다운

- 테이블은 Notion에서 지원되는 테이블 문법을 사용하고, 셀 안에는 서식 있는 텍스트만 사용한다.
- 특수문자(역슬래시, 별표, 물결표, 백틱, 달러, 대괄호, 꺾쇠괄호, 중괄호, 파이프, 캐럿)는 문맥에 따라 이스케이프한다. 코드 블록 안은 리터럴로 둔다.
- 구분선(`---`)은 새로 만들지 않는다. 섹션은 `#` 제목으로만 나누고, 목록이나 테이블로 구조를 정리한다.
- 기존 페이지에 있는 구분선은 수정 요청 범위에 들어오지 않으면 그대로 둔다.

### 2. 작성 형식

- Notion 페이지에 쓰는 내용은 한국어로 작성한다.
- 섹션은 `#` 제목으로 구분하고, 비교나 정리에는 테이블을 사용한다.
- 예시 코드는 언어 태그를 포함한 코드 블록으로 작성한다.
- 설계 문서, 데이터 흐름 등을 정리할 때 Mermaid 다이어그램을 적극 활용한다.
  - 데이터 흐름(API 호출, 번들 분리 등)
  - 시퀀스 다이어그램(사용자 플로우)
  - 아키텍처 결정 비교
- 아키텍처 구조도(시스템 구성, 컴포넌트/모듈 간 의존 관계)는 Mermaid 대신 `drawio` 스킬로 그려 PNG 이미지로 넣는다. 위 Mermaid 목록(데이터 흐름, 시퀀스, 아키텍처 결정 비교)은 계속 Mermaid로 그린다. 순서는 다음과 같다.
  1. `Skill` 도구로 `drawio` 스킬을 호출해 다이어그램을 그린다.
  2. 그 스킬의 내보내기 절차대로 XML을 포함한 PNG(`<이름>.drawio.png`)로 내보낸다. 내보낸 PNG는 draw.io에서 다시 열어 고칠 수 있다.
  3. `notion-create-file-upload`에 파일 이름을 넘겨 업로드 URL을 받고, Bash의 `curl`로 받은 `upload_headers`를 모두 붙여 `file` 필드에 PNG를 담은 multipart POST 요청을 한 번 보낸다. 한 번에 올릴 수 있는 파일은 20 MiB까지다.
  4. 응답의 `suggested_markdown`을 새 페이지면 `notion-create-pages`의 본문에, 기존 페이지면 `notion-update-page`로 원하는 위치에 넣는다. 업로드한 파일은 페이지에 넣기 전까지 임시 상태라 만료되면 지워지므로 바로 넣는다.
  5. draw.io 데스크톱 CLI가 없어 PNG를 만들지 못했거나, 파일이 20 MiB를 넘거나, 업로드가 실패하면 받은 오류를 그대로 보여주고 Mermaid로 대신 그릴지 사용자에게 묻는다.

### 3. 연결과 접근 실패

Notion 작업을 시작할 때 첫 도구 호출 전에 `ToolSearch`로 `select:mcp__notion__notion-fetch,mcp__notion__authenticate,mcp__notion__complete_authentication`을 조회해 연결 상태를 판정한다. 조회는 있는 도구만 돌려준다. 작업 도중 도구 호출이 인증 오류(401, 토큰 만료)로 실패하면 `notion-fetch`가 남아 있어도 인증이 끊긴 것으로 보고, `authenticate`가 있으면 아래 재연결 순서를, 없으면 `/mcp` 안내를 따른다. 재연결 순서는 한 작업 요청 안에서 한 번만 수행한다.

- `notion-fetch`가 있으면 연결된 상태다. 원래 작업을 진행한다.
- `notion-fetch`가 없고 `authenticate`가 있으면 인증이 끊긴 상태다. 사용자에게 `/mcp` 입력을 먼저 요청하지 않고 아래 순서로 재연결한다.
- `notion-fetch`와 `authenticate`가 모두 없으면 서버가 연결되지 않은 상태다. 사용자에게 알리고 `/mcp`에서 `notion` 서버 상태를 확인하도록 안내한다.

재연결 순서는 다음과 같다.

1. `mcp__notion__authenticate`를 호출해 인증 URL을 받는다.
2. macOS면 `open "<URL>"`로 기본 브라우저에서 연다. 그 밖의 환경에서는 열지 않는다. 어느 경우든 URL을 응답에 함께 적는다.
3. 사용자에게 브라우저에서 승인한 뒤 알려 달라고 하고 응답을 기다린다. 승인을 대신할 방법은 없다.
4. 사용자가 승인했다고 하면 위 조회를 다시 한다. `notion-fetch`가 있으면 원래 작업을 이어 간다.
5. 여전히 `notion-fetch`가 없으면 승인 뒤 브라우저 주소창에 남은 `http://localhost:<port>/callback?code=...&state=...` 전체 URL을 달라고 해서 `mcp__notion__complete_authentication`의 `callback_url`로 넘기고, 4단계의 조회를 한 번 더 한다. `notion-fetch`가 있으면 원래 작업을 이어 간다.
6. 그래도 `notion-fetch`가 없거나, 사용자가 승인을 거부했거나 콜백 URL을 주지 못했거나, `authenticate`가 URL을 주지 않았거나, 도구 호출이 오류를 돌려주면 받은 오류(없으면 도구가 여전히 없다는 사실)를 그대로 보여주고 `/mcp`에서 `notion`을 직접 재인증하도록 안내한다. 같은 절차를 자동으로 반복하지 않는다.

인증은 되어 있는데 조회나 수정이 권한 문제로 실패하면 사용자에게 Notion URL 확인과 공유 설정(연동 계정 접근 허용)을 안내한다.
