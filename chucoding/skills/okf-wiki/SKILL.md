---
name: okf-wiki
description: 저장소 안에 OKF v0.2 번들로 둔 LLM Wiki를 읽고 쓸 때 따르는 절차. 번들 구조(index.md와 log.md 예약 파일, 주제별 하위 디렉터리), 개념 문서 frontmatter 필수 필드와 UTC 시각 표기, draft와 stable과 deprecated 전환 조건, 무엇을 쓰고 쓰지 않는가, Ingest와 Query와 Lint 운영 동작을 포함한다. 저장소 AGENTS.md가 이 스킬을 가리키거나, 위키 문서를 찾아 읽거나 만들고 고칠 때, 위키를 가진 저장소에서 코드나 규칙을 바꾸는 PR을 준비할 때, 위키 검사를 요청받았을 때 사용한다.
---

저장소 안의 LLM Wiki를 [OKF v0.2](https://github.com/GoogleCloudPlatform/open-knowledge-format/blob/main/SPEC.md) 번들로 운영할 때 이 스킬을 적용한다. 위키는 [카파시 LLM Wiki 패턴](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)의 세 계층(원본, 위키, 스키마)과 세 동작(Ingest, Query, Lint)을 OKF 형식으로 구현한 것이다.

저장소마다 다른 값은 이 스킬에 두지 않는다. 아래 항목은 저장소 `AGENTS.md`를 따르고, 거기에 없으면 추측하지 말고 사용자에게 묻는다.

| 저장소 `AGENTS.md`가 정하는 값 | 예 |
|------|------|
| 위키 번들 경로 | `wiki/` |
| 허용하는 문서 유형(`type`) 목록 | `Architecture`, `Workflow`, `Decision` |
| `stale_after` 기본 기간 | 코드 파생 문서 3개월, 결정 기록 6개월 |
| 검사 명령 | `pnpm wiki:lint` |
| 저장소 제약 | 공개 저장소라서 쓰지 않을 내용 |

### 1. 작업 전 원칙

- 작업과 관련된 문서를 위키 루트 `index.md`에서 먼저 찾아 읽는다. 원본 코드 전체를 다시 훑기 전에 위키부터 본다.
- 위키 내용과 코드가 다르면 코드가 현재 동작의 정본이다. 어긋남을 작업 보고에 적고 `5. Ingest` 절차로 위키를 고친다.
- `status: draft`이거나 `verified`가 없는 문서는 사람이 확인하지 않은 내용이다. `sources`를 직접 열어 확인한 뒤 의존한다.

### 2. 번들 구조

세 계층은 아래와 같이 대응한다.

| 계층 | 위치 | 누가 쓰는가 |
|------|------|------|
| 원본 | 코드, 설정, 이슈와 PR | 사람과 에이전트가 평소 작업으로 씀. 위키 작업 중에는 읽기만 함 |
| 위키 | 위키 번들 디렉터리 | 에이전트가 쓰고 사람이 PR에서 리뷰 |
| 스키마 | 저장소 `AGENTS.md`와 이 스킬 | 사람이 정함 |

- `index.md`는 디렉터리 목록이고 `log.md`는 변경 이력이다. 두 이름은 예약 파일이므로 개념 문서 이름으로 쓰지 않는다.
- 루트 `index.md` frontmatter에는 `okf_version: "0.2"`를 둔다.
- 개념 문서는 주제별 하위 디렉터리에 둔다. 같은 디렉터리 `index.md`에 `- [제목](파일.md): 한 줄 설명` 형식으로 링크한다.
- 새 하위 디렉터리를 만들면 그 디렉터리에 `index.md`를 만들고 상위 `index.md`에 링크한다.
- 파일 이름은 `kebab-case.md`다.

### 3. 개념 문서 frontmatter

OKF v0.2 스펙의 필수 필드는 `type` 하나지만, 이 운영 방식은 `title`, `description`, `status`, `sources`, `generated`, `stale_after`까지 필수로 둔다. 나중에 도구를 바꿔도 출처와 신뢰 신호를 잃지 않기 위해서다.

```yaml
---
type: Workflow                    # 필수. 허용 목록은 저장소 AGENTS.md
title: 주문 결제 승인 흐름           # 필수
description: 한 문장 요약             # 필수
tags: [payment, order]            # 선택
status: draft                     # 필수. draft, stable, deprecated
sources:                          # 필수. 하나 이상
  - resource: ../../src/payment/approve.ts    # 저장소 안 경로는 문서 기준 상대 경로. 존재해야 함
  - id: pr-42
    title: "feat: 결제 승인 재시도"
    resource: https://github.com/<owner>/<repo>/pull/42
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-02T00:00:00Z }   # 필수
verified:                         # 선택. stable이면 human: 항목 필수
  - { by: human:<GitHub 아이디>, at: 2026-10-03T00:00:00Z }
stale_after: 2027-01-02T00:00:00Z # 필수. 이 시각이 지나면 검사가 실패
---
```

- 시각을 담는 값(`generated.at`, `verified[].at`, `stale_after`)은 모두 `2027-01-02T00:00:00Z`처럼 UTC 오프셋을 붙인 ISO 8601 datetime으로 쓴다. 날짜만 쓰면 타임존마다 다른 시각을 가리킨다. 근거는 OKF 저장소 PR [GoogleCloudPlatform/open-knowledge-format#6](https://github.com/GoogleCloudPlatform/open-knowledge-format/pull/6)이다.
- 행위자(`generated.by`, `verified[].by`)는 아래 세 형식 중 하나로 쓴다.

| 행위자 | 형식 | 예 |
|------|------|------|
| 에이전트 | `<도구>/<버전>` | `claude-code/claude-opus-5-5` |
| 사람 | `human:<id>` | `human:chucoding` |
| 자동 처리 | `process:<id>` | `process:nightly-import` |

- `sources`의 저장소 안 경로는 OKF 6.2에 따라 문서 기준 상대 경로로 쓴다. 스펙 본문과 예시가 엇갈린다는 이슈([open-knowledge-format#29](https://github.com/GoogleCloudPlatform/open-knowledge-format/issues/29))가 열려 있으므로, 결론이 바뀌면 이 규칙도 함께 고친다.
- 외부 출처는 `id`, `title`, `resource`를 함께 적는다.
- `stale_after`는 작성 시각에 저장소 `AGENTS.md`가 정한 기본 기간을 더해 잡는다.

### 4. 신뢰 규칙

| 상태 | 전환 조건 |
|------|------|
| `draft` | 새로 만든 문서, 그리고 내용을 고친 문서. 내용을 고치면 기존 `verified`를 지우고 `draft`로 내린다 |
| `stable` | 사람이 PR 리뷰로 내용을 확인해 `verified`에 `human:<id>` 항목이 생겼을 때만 올린다 |
| `deprecated` | 더 이상 맞지 않지만 링크와 이력 때문에 남길 문서. 본문에 대체 문서를 링크한다 |

- 에이전트는 사람 확인 없이 `stable`로 올리지 않는다. 사용자가 PR 리뷰에서 확인했다고 밝혔을 때 `verified`에 `{ by: human:<id>, at: <확인 시각> }`을 추가하고 `status`를 `stable`로 바꾼다.

### 5. 무엇을 쓰고 무엇을 쓰지 않는가

- 쓴다: 코드만 봐서는 알기 어려운 이유, 여러 곳을 함께 바꿔야 하는 값, 보안과 비용 경계, 되돌리기 어려운 결정
- 쓰지 않는다: 코드를 그대로 옮긴 설명, 함수 시그니처 목록, 커밋 이력으로 충분한 변경 내용
- 비밀 값처럼 저장소 공개 범위 때문에 쓰지 말아야 할 내용은 저장소 `AGENTS.md`의 제약을 따른다.

### 6. Ingest

코드나 규칙을 바꾸는 PR에서, 바뀐 사실을 다루는 위키 문서가 있으면 같은 PR에서 함께 고친다. 코드 변경을 자동으로 감지하지 않으므로 이 규칙이 코드 파생 문서를 최신으로 유지하는 유일한 장치다.

1. 위키 `index.md`에서 영향받는 문서를 찾는다.
2. 본문과 `sources`, `generated`를 갱신하고 `stale_after`를 다시 잡는다. 내용이 바뀌면 기존 `verified`를 지우고 `status`를 `draft`로 내린다.
3. 새 주제면 개념 문서를 만들고 디렉터리 `index.md`에 링크한다.
4. `log.md`에 변경 항목을 추가한다.
5. 저장소 `AGENTS.md`가 지정한 검사 명령을 통과시킨다.

`log.md` 항목 형식은 아래와 같다.

```markdown
## 2026-10-05

- **Update** 결제 승인 흐름의 재시도 횟수 변경을 반영 (#42)

## 2026-10-02

- **Creation** 위키 번들 골격과 초기 개념 문서 3건 작성 (#40)
  - [주문 결제 승인 흐름](payment/approve-flow.md), [환불 경계](payment/refund-boundary.md)
```

- 날짜 제목은 `## YYYY-MM-DD`이고 최신 날짜가 맨 위에 온다. 같은 날짜 제목이 있으면 그 아래에 추가한다.
- 각 항목은 `**Creation**`, `**Update**`, `**Deprecation**` 중 하나로 시작한다.
- 관련 이슈나 PR 번호를 괄호로 붙인다.

### 7. Query

설계 질문에는 위키를 먼저 찾아 답하고, 답에 쓴 문서를 링크한다. 위키에 없어 코드를 조사해 얻은 답이 다시 쓸 만하면 `6. Ingest`로 문서를 추가한다.

### 8. Lint

- 정적 검사: 저장소 `AGENTS.md`가 지정한 검사 명령을 실행한다. 검사 도구는 저장소마다 다르므로 이 스킬은 특정 도구를 정하지 않는다. 검사 대상은 보통 frontmatter 필수 키, `sources` 경로 존재, 깨진 링크, `index.md` 누락, `log.md` 형식, `stale_after` 만료다.
- 의미 검사: 요청을 받으면 문서끼리의 모순, 코드와 어긋난 주장, 고아 개념, 빠진 상호 참조를 점검해 수정 PR을 올린다.
- `stale_after`가 지난 문서는 `sources`를 다시 읽어 내용을 확인한 뒤 시각을 갱신한다. 확인 없이 시각만 미루지 않는다.
