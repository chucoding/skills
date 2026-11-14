---
name: agents-md-loop
description: hd-cloud-client(허브 FE) `AGENTS.md` 보강 루프를 스프린트 마지막 날 한 번 같은 순서로 돈다. 매 스프린트 같은 제목, 필드, 설명 절로 보강 티켓을 만들고(같은 스프린트 티켓이 있으면 그것을 쓴다) 직전 보강 티켓을 `연결됨`으로 잇는다. 스크립트로 기간 안 PR의 자동 리뷰(`pr-auto-review`) 지적을 규칙 ID별 PR당 지적 수와 코드 지표로 집계하고, 그 행을 위키 `measurements.csv`에 덧붙이는 일은 `chucoding:handoff`로 위키 워크스페이스에 넘긴다. 직전 스프린트 대비 추이와 승격 후보(3개 PR 이상 반복)를 고정 형식 목록으로 티켓 설명과 댓글에 남기고, `AGENTS.md` 반영 후보 2~3개를 적어 hd-cloud-client에서 같은 티켓 키로 작업하라고 안내한다. 사용자가 "AGENTS.md 보강 루프 돌려줘", "이번 스프린트 리뷰 지적 측정해줘", "AGENTS.md 효과 측정", "보강 티켓 만들어줘", "리뷰 지적 추이", "승격 후보"를 요청할 때 사용한다.
---

# AGENTS.md 보강 루프

허브 저장소(`dev-rsquare/hd-cloud-client`) `AGENTS.md`에 기준서 규칙을 보강하고, 그 뒤 같은 리뷰 지적이 줄었는지 스프린트마다 재는 루프다. 스프린트 마지막 날 한 번, 아래 1~5단계를 이 순서로 돈다.

예약 실행은 두지 않는다. PR과 리뷰, 코멘트는 GitHub에 남아 있어 마지막 날 한 번 조회해도 결과가 같다.

| 자리 | 무엇 |
|------|------|
| 이 스킬 | 절차 |
| 위키 `homedot-hub/knowledge/standards/effect/measurement.md` | 측정 정의 버전, `measurements.csv` 칸의 뜻, 기준선 출처(HDIT-4867), 보강 이력 |
| 위키 `homedot-hub/knowledge/standards/effect/measurements.csv` | 결과 시계열(정본). 1년 추이는 이 파일로 본다 |
| `scripts/period.py`, `scripts/collect.py`, `scripts/measure.py`, `scripts/report.py` | 측정 기간 시작 판정, 수집, 집계와 행 덧붙이기, 결과 요약 |
| Notion `AGENTS.md 보강 루프` (https://app.notion.com/p/417321af0002800ba8d8cb00042e82c8) | 사람용 설명. 이 스킬은 고치지 않는다 |

수치의 정본은 위키 CSV이고 티켓 설명과 댓글은 요약이다. Notion은 사람용, 위키는 에이전트용으로 나누고 합치지 않는다(사용자 지시, 2026-11-14).

아래에서 `<위키>`는 `/Users/hyeonseoksuh/homedot/hd-cloud-wiki`, `$S`는 `~/.claude/skills/chucoding/skills/agents-md-loop/scripts`다.

## 0. 먼저 확인할 것

작업 폴더 `$W`는 `~/.claude/handoffs/<YYYYMMDD-HHMM>-agents-md-loop/`로 만든다. 3단계에서 위키 세션이 이 폴더의 행 파일을 읽어야 하므로 세션 스크래치패드에 두지 않는다.

위키 메인 체크아웃은 읽기 전용이다(전역 AGENTS.md `위키 직접 읽기`). 위키 파일은 원격 기준으로 읽는다.

```bash
git -C <위키> fetch origin main
git -C <위키> show origin/main:homedot-hub/knowledge/standards/effect/measurements.csv > "$W/measurements.main.csv"
git -C <위키> show origin/main:homedot-hub/knowledge/standards/effect/measurement.md
```

- `measurements.csv`가 `origin/main`에 없으면 측정 데이터를 처음 넣은 HDIT-6655 위키 PR이 아직 머지되지 않은 것이다. 직전 측정과 비교할 수 없으므로 멈추고 사용자에게 알린다.
- 측정 정의 버전: `measurement.md`의 최신 버전과 이번 조건(범위 경로, 리뷰어, 제외 PR, 자동 리뷰 형식)이 같은지 본다. 다르면 3단계 브리핑에 버전을 올리라는 지시와 이유를 넣고, 4단계에서 직전과 비교하지 않는다.
- 기준서 규칙 문장이 직전 측정 뒤에 바뀌었는지: `git -C <위키> log origin/main --since <직전 측정일> -- homedot-hub/knowledge/standards/`. 자동 리뷰의 규칙 렌즈가 기준서를 읽으므로, 바뀌었으면 4단계 해석에 적는다.
- `gh api repos/dev-rsquare/hd-cloud-client --jq .permissions.pull`이 `true`인지.

## 1. 보강 티켓 생성

매번 같은 제목, 필드, 설명 절로 만든다. 스프린트 사이에 티켓을 나란히 놓고 읽기 쉽게 하려는 것이다(사용자 요청). 생성 규칙과 필드 값은 `chucoding:jira`의 `티켓 생성`을 따르고, 이 절은 그 규칙과 달라지는 값만 적는다.

**멱등**: 먼저 같은 스프린트 티켓을 찾는다. JQL 텍스트 검색은 토큰 단위라 `#`를 어떻게 다루는지 확실하지 않으므로 결과를 후보로만 쓰고, 제목 문자열이 아래 형식과 정확히 같은 것만 같은 티켓으로 본다. 있으면 새로 만들지 않고 그 티켓으로 2단계부터 진행한다.

```text
project = HDIT AND summary ~ "\"AGENTS.md 보강\"" ORDER BY created DESC
```

**직전 보강 티켓**: 멱등 JQL 결과에서 제목 형식이 같고 이번 스프린트가 아닌 것 중 가장 최근 것이다. 처음 돌릴 때는 없으므로 아래 `첫 실행`을 따른다.

**측정 기간**: 사람이 매번 넣지 않고 아래 순서로 정한다. 다음 스프린트 티켓을 미리 만들어 두지 않고, 실행 시점에 직전 티켓과 PR에서 기간을 찾기로 했다(사용자 결정, 2026-11-14).

1. 직전 보강 티켓 키로 hd-cloud-client에서 `AGENTS.md`를 바꾼 머지 PR을 찾는다. 있으면 그 머지 시각이 기간 시작이다. 같은 티켓의 보강 PR이 여럿이면 마지막 머지 시각을 쓴다.
2. 머지된 보강 PR이 없으면(반영할 규칙이 없었거나 아직 머지 전) 0단계의 `measurements.main.csv` 마지막 행의 `period_end`부터 이어서 잰다. 아직 머지 전이어도 측정을 멈추지 않는다.
3. 기간 종료는 2단계 실행 시각이다. `measure.py --end`의 기본값이 그 시각을 `period_end` 칸에 남겨 다음 회차의 2번 근거가 된다.

```bash
python3 $S/period.py --prev-ticket <직전 보강 티켓 키> --csv "$W/measurements.main.csv" > "$W/period.json"
```

- 출력의 `start`가 기간 시작이고, `basis`는 설명 `측정 기간` 절에 그대로 적는 근거 한 줄이다. `open`에 PR 번호가 있으면 직전 보강 PR이 아직 머지 전이라는 사실과 그 PR 번호도 같은 절에 적는다.
- 근거는 티켓에만 남긴다. CSV에는 `period_start` 칸에 시작 시각만 들어가고 칸을 늘리지 않는다.
- 사용자가 기간을 지정하면 그 값으로 덮어쓰고, 근거에 `사용자 지정`이라고 적는다.
- `period_end`에 시각 없이 날짜만 있으면(기준선 행의 `2026-11-13`) `measure.py`가 그날 00:00 UTC로 읽는다. 그 값에서 이어질 때는 근거에 이 사실을 덧붙인다.

**첫 실행**: 직전 보강 티켓이 없으면 기준선(HDIT-4867 후 기간, `26_4_#3`)과 HDIT-6654 보강을 직전 기록으로 본다. `period.py --prev-ticket HDIT-6654`로 기간 시작을 정하고(HDIT-6654 보강 PR의 머지 시각), 설명의 직전 측정은 `26_4_#3, HDIT-4867`이다. 연결은 이 루프를 만든 HDIT-6655에 한다.

**제목**: `[FE] AGENTS.md 보강 <스프린트명>: 리뷰 지적 측정과 규칙 반영`. `<스프린트명>`은 측정하는 스프린트(지금 활성 스프린트) 이름이다. 예: `26_4_#4`.

**`chucoding:jira` 기본값과 다른 값**

- 보고자: 스킬을 돌린 사람(`GET /rest/api/3/myself`). `chucoding:jira`는 보고자를 되묻지만, 이 루프는 사용자가 실행한 사람으로 정했다(2026-11-14). 작업자도 같다.
- QA수행: `개발`(`{"id":"10284"}`). `QA수행 판정` 표의 1번(사용자 지정)이다. 아래 연결 때문에 직전 보강 티켓이 상위 티켓으로 잡혀 판정표대로 가면 6번을 거쳐 되묻게 되는데, 이 루프 티켓은 모두 개발자가 직접 확인하는 측정과 문서 보강이라 매번 `개발`로 고정한다.
- SP: `chucoding:jira`의 `SP 산정`대로 생성 직후 기입한다. 직전 보강 티켓의 SP와 업무 로그를 먼저 대조한다.

**설명**: 절 이름과 순서를 바꾸지 않는다. `chucoding:jira`의 `표 대신 쓰는 형식`대로 제목과 목록만 쓴다. 결과 요약과 반영 후보는 생성 때 `4단계에서 채운다`로 둔다.

```markdown
## 배경
허브 AGENTS.md에 기준서 규칙을 보강하고 그 뒤 같은 리뷰 지적이 줄었는지 스프린트마다 재는 루프의 <스프린트명> 회차다.
* 설명: https://app.notion.com/p/417321af0002800ba8d8cb00042e82c8

## 측정 기간과 측정 정의 버전
* 기간: <start> ~ <end> (PR 생성 시각, [start, end)). 생성 때 <end>는 `2단계 실행 시각`으로 두고 4단계에서 채운다
* 기간 시작 근거: <period.json의 basis>
* 측정 정의: <버전> (위키 homedot-hub/knowledge/standards/effect/measurement.md)
* 직전 측정: <직전 스프린트>, <직전 보강 티켓 키>

## 결과 요약
4단계에서 채운다

## 반영 후보
4단계에서 채운다

## 관련 링크
* 결과 시계열: 위키 homedot-hub/knowledge/standards/effect/measurements.csv
* 직전 보강 티켓: <키>
* 위키 브랜치: docs/<티켓키>-agents-md-metrics
```

**연결**: 직전 보강 티켓(첫 실행은 HDIT-6655)을 `연결됨`(`Discovery - Connected`)으로 잇는다. `chucoding:jira` `현재 티켓 연결`의 payload에서 현재 티켓 자리에 직전 보강 티켓을 넣는다. 직전 티켓이 `connects to` 쪽이다.

**승인과 확인**: 생성 전에 제목, 필드(QA수행 값과 위 근거 포함), 연결 대상, 설명 전문을 `chucoding:jira`의 `수정 전 초안 검토`대로 보이고 승인받는다. 스킬 호출을 생성 요청으로 보지만 초안 승인은 건너뛰지 않는다. 생성 뒤에는 `chucoding:jira`대로 필드와 링크를 다시 조회한다.

티켓을 만들었으면(또는 찾았으면) `homedot-cloud-devteam:ticket-start`로 `개발중`으로 옮긴 뒤 2단계로 간다.

## 2. 수집과 집계

기간 시작은 1단계 `period.json`의 `start`이고 종료는 이 단계의 실행 시각이다. 스프린트의 `startDate`와 `endDate`는 쓰지 않는다. 측정 정의 v1의 범위 경로, 리뷰어, 제외 PR은 스크립트 기본값이다. 정의가 바뀌었으면 인자로 넘긴다.

```bash
python3 $S/collect.py --work "$W" --since <start의 KST 날짜> --exclude 2339,2348,2528,2539,2626,2666
python3 $S/measure.py --work "$W" --start <start> \
  --sprint <스프린트명> --ticket <티켓키> > "$W/rows.csv"
```

`--end`는 사용자가 기간을 지정했을 때만 넘긴다. 넘기지 않으면 실행 시각이 들어간다. 그 값은 `rows.csv`의 `period_end` 칸에서 읽어 4단계에서 설명의 `<end>`에 채운다.

| 인자 | 기본값(측정 정의 v1) |
|------|------|
| `--reviewer` | `hyeonseok-suh` |
| `--scope-regex`(collect) | `/payroll\|^src/pages/erp/` |
| `--exclude` | `2339,2348,2528,2539,2626,2666`(승격과 통합 PR) |
| `--def-version`(measure) | `v1` |

- `measure.py`의 표준 오류 끝 줄로 범위 PR 수와 지적 수를 확인한다. 0건이면 기간이나 범위 인자를 의심하고 멈춘다.
- 규칙 ID는 자동 리뷰 지적 **제목**에 붙은 표기를 정규식으로 센다. 제목에 ID가 없는 지적은 `NO_RULE_ID` 한 칸이다. 군집으로 나눠 봐야 하는 질문이 있을 때만 `$W/items.jsonl`을 읽어 분류하고, 분류 결과는 행으로 쌓지 않고 티켓 댓글에 적는다.
- `diff 없음` 경고가 나온 PR(diff가 GitHub 한도인 파일 300개를 넘는 PR 등)은 코드 지표에서 빠진다. 4단계 해석에 적는다.
- `collect.py`가 `--limit`에 닿았다고 경고하면 늘려서 다시 돌린다.

## 3. 위키 CSV 행 추가

위키는 다른 저장소라 `chucoding:handoff`로 위키 워크스페이스에 넘기고 결과를 기다리지 않는다. 브리핑에 아래를 넣는다.

- 브랜치: `origin/main`에서 `docs/<티켓키>-agents-md-metrics`
- 넘길 행: `$W/rows.csv`의 전체 경로. 행을 고치지 말고 아래 명령으로 그대로 덧붙인다. 같은 `(sprint, def_version, ticket, metric, rule_id)` 행이 이미 있으면 명령이 거절하므로, 그때는 지우거나 고치지 말고 사용자에게 알린다.

  ```bash
  python3 ~/.claude/skills/chucoding/skills/agents-md-loop/scripts/measure.py \
    --rows <$W/rows.csv> --append homedot-hub/knowledge/standards/effect/measurements.csv
  MEASUREMENTS_CSV=homedot-hub/knowledge/standards/effect/measurements.csv \
    python3 ~/.claude/skills/chucoding/skills/agents-md-loop/scripts/measure.test.py -q
  ```

- 0단계에서 측정 정의 버전을 올려야 했으면 `measurement.md` 버전 표를 고치라는 지시와 이유
- 직전 회차의 반영 후보가 hd-cloud-client에 머지됐으면 `measurement.md` 「보강 이력」에 그 날짜와 PR을 채우라는 지시
- 커밋과 PR 제목: `docs(<티켓키>): <스프린트명> AGENTS.md 보강 루프 측정 행을 더한다`. PR 절차는 위키의 `wiki-review-harness`와 `create-pr`을 따른다.

## 4. 결과 요약

위키 PR이 머지되기 전이므로 0단계의 `origin/main` 사본에 이번 행을 붙인 미리보기 CSV로 요약한다.

```bash
cp "$W/measurements.main.csv" "$W/measurements.preview.csv"
python3 $S/measure.py --rows "$W/rows.csv" --append "$W/measurements.preview.csv"
python3 $S/report.py --csv "$W/measurements.preview.csv" --sprint <스프린트명>
```

- 출력은 같은 측정 정의 버전의 직전 측정과 비교한 규칙별 PR당 지적 수 목록, 코드 지표 목록, 승격 후보 줄이다. 줄 형식이 고정돼 있어 스프린트 사이에 나란히 읽힌다.
- **승격 후보**는 이번 측정에서 같은 규칙 ID의 지적이 **3개 PR 이상**에서 나온 규칙이다(`auto_findings_prs`). `CONV`가 후보면 기준서에 아직 없는 관행이 반복된다는 뜻이다.
- **은퇴 후보**: 한 규칙의 `auto_findings`가 3스프린트 연속 0건이고, 그 규칙의 코드 지표가 있으면 그것도 같은 기간 0건인 규칙이다. `AGENTS.md`에서 뺄지는 사람이 정하고 기준서 규칙 자체는 남는다. 미리보기 CSV에서 직접 확인해 있으면 적는다.
- 설명 `측정 기간` 절의 `<end>`를 `rows.csv`의 `period_end`로 채운다.
- 출력을 티켓 설명의 `결과 요약` 절에 그대로 넣고, 같은 출력을 댓글로도 남긴다. 그 아래에 해석을 몇 줄 붙인다.
  - 대조군(보강하지 않은 규칙과 `LENS_BUG`, `LENS_ADVERSARIAL`)이 함께 줄었으면 보강 효과로 읽지 않는다.
  - 0단계에서 찾은 기준서 변경과 `diff 없음` PR을 적는다.
- 설명은 전체를 덮어쓰므로 `chucoding:jira` `다이어그램`의 설명 백업과 SP 근거 문단 보존 규칙을 따른다. 댓글은 `게시 전 전문 출력`과 `게시 절차`를 따른다. 설명과 댓글을 한 번에 보이고 승인받는다.

## 5. 반영 안내

`AGENTS.md`는 hd-cloud-client 저장소에 있어 이 스킬이 고치지 않는다. 그 저장소 `AGENTS.md` §8이 `scripts/` 커밋을 막으므로 스크립트도 그쪽에 두지 않는다.

- 승격 후보와 직전 대비 늘어난 규칙 중 2~3개를 골라 티켓 `반영 후보` 절에 적는다. 규칙마다 아래 네 가지를 한 목록 항목으로 쓴다.
  - 규칙 ID
  - 이번 PR당 지적 수
  - 지적이 나온 PR 번호(`$W/items.jsonl`의 `pr`)
  - `AGENTS.md`에 넣을 문장의 방향 한 줄
- 위키 `measurement.md` 「보강 이력」에 이미 있는 규칙을 다시 고르면 그 이유를 적는다.
- 반영할 규칙이 없으면 `반영 후보` 절에 `이번 회차 반영 없음`과 이유를 적는다.
- 4단계와 같은 승인에 묶어 설명을 고친다.
- 사용자에게 "같은 티켓 키로 hd-cloud-client 워크스페이스에서 `AGENTS.md`를 고친다"고 안내하고 끝낸다. 티켓 상태는 hd-cloud-client PR이 머지된 뒤 그쪽 세션이 옮긴다.

## 하지 않는 것

- hd-cloud-client 저장소와 그 `AGENTS.md`를 고치지 않는다.
- 위키 메인 체크아웃을 고치지 않는다. 위키 변경은 3단계 핸드오프로만 한다.
- Notion 페이지를 고치지 않는다.
- 이미 쌓인 `measurements.csv` 행을 고치지 않는다.
- 측정 정의 버전이 다른 행끼리 비교하지 않는다.
- 크론이나 예약 실행을 두지 않는다.
