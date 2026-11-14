---
name: agents-md-regress
description: hd-cloud-client(허브 FE) `AGENTS.md` 회귀 프롬프트를 돌려 두 가지를 정한다. 새 모델이 규칙 문장 없이도 지키는 규칙(은퇴 후보, `AGENTS.md`가 짧아지면 세션마다 토큰이 준다)과, 추론 강도를 낮춰도 위반이 늘지 않는 강도(권장 추론 강도)다. 실제 리뷰 지적이 나온 PR의 base 커밋과 줄인 요청으로 만든 고정 과제(`tasks/`)를 임시 worktree에서 `claude -p`로 모델 × 추론 강도 × 반복만큼 돌리고, 정규식과 고정된 채점 프롬프트로 규칙 위반을 센다. 결과 행은 `chucoding:handoff`로 위키 `regression-runs.csv`에 넘긴다. 새 모델을 쓰기 시작할 때나 `AGENTS.md`를 크게 바꿨을 때 사람이 `/chucoding:agents-md-regress`로 실행한다. 스프린트마다 돌리지 않는다(스프린트 측정은 `chucoding:agents-md-loop`). 사용자가 "회귀 프롬프트 돌려줘", "새 모델로 AGENTS.md 회귀", "추론 강도 낮춰도 되는지", "규칙 은퇴 후보", "agents-md-regress"를 요청할 때 사용한다.
---

# AGENTS.md 회귀 프롬프트

`chucoding:agents-md-loop`은 실제 PR에서 지적이 줄었는지 보지만, PR마다 과제 난이도와 모델, 추론 강도가 섞여 원인을 가를 수 없다. 이 스킬은 같은 과제를 조건만 바꿔 돌리는 통제 실험이다. 추론 강도는 PR 지표에 넣지 않고 여기서만 다룬다(사용자 결정, 2026-11-14).

정하는 것은 두 가지다.

- **은퇴 후보**: 규칙 문장을 지운 `AGENTS.md`(stripped)로 돌려도 위반이 늘지 않는 규칙이다. 빼는 결정은 사람이 한다. 기준서(위키) 규칙 자체는 남는다.
- **권장 추론 강도**: 모델마다 전체 위반률이 가장 낮은 값과 같은 강도 중 가장 낮은 강도다.

아래에서 `$S`는 `~/.claude/skills/chucoding/skills/agents-md-regress/scripts`, `$W`는 작업 폴더 `~/.claude/handoffs/<YYYYMMDD-HHMM>-agents-md-regress/`다. 위키 세션이 결과 행을 읽어야 하므로 세션 스크래치패드에 두지 않는다.

## 0. 먼저 확인할 것

- `claude --version`과 이번에 비교할 모델 id. 새 모델이 나왔으면 그 모델과 직전 주 모델을 함께 돌려야 비교가 된다.
- 과제의 base 커밋이 로컬 클론(`/Users/hyeonseoksuh/homedot/hd-cloud-client`)에 있는지: `python3 $S/regress.test.py -q`가 형식을 보고, 실행기가 worktree를 만들 때 없으면 실패한다. 없으면 `git -C <클론> fetch origin <sha>`로 객체만 받는다.
- 채점 프롬프트가 읽는 위키 기준서는 `origin/main` 기준이다. `git -C /Users/hyeonseoksuh/homedot/hd-cloud-wiki fetch origin main`을 먼저 한다. 위키 메인 체크아웃은 읽기 전용이다.

## 1. 과제 세트 (`tasks/`)

과제 하나는 실제로 그 지적이 나온 PR의 base 커밋과, 그 PR이 받은 요청을 줄인 프롬프트다(SWE-bench식 재현). HDIT-4867 자동 리뷰 지적에서 반복이 많은 규칙(`FSD-04`, `FSD-05`, `FSD-06`, `TS-01`, `GRID-02`, `GRID-07`, `REUSE-04`)을 골랐다.

| 키 | 뜻 |
|------|------|
| `id` | 파일 이름과 같다 |
| `rules` | 대상 규칙 ID |
| `source_pr`, `source_review` | 지적이 나온 PR과 리뷰 링크 |
| `base_commit` | PR의 분기점(40자 sha) |
| `prompt` | 에이전트에 주는 지시. 규칙 힌트를 넣지 않는다 |
| `grading.regex` | `agents-md-loop` `measure.py`의 코드 지표 이름. 추가된 줄을 결정적으로 센다 |
| `grading.judge` | 정규식으로 안 되는 규칙 ID. 채점 프롬프트로 판정한다 |
| `agents_md_strip` | 비교군에서 지울 `AGENTS.md` 줄의 부분 문자열 |
| `notes` | 고른 이유와 줄인 범위 |

- 프롬프트에는 규칙 힌트(규칙 ID, "export 하지 마" 같은 말)를 넣지 않는다. 에이전트가 저장소 `AGENTS.md`만 보고 지키는지를 재기 때문이다. `regress.test.py`가 대표 힌트 단어를 막는다.
- 과제를 고치면 이전 결과와 비교하지 않는다. 새 과제는 새 `id`로 더한다.

## 2. 계획과 승인

```bash
python3 $S/run.py --out "$W" --model <모델> [--model <모델>] --effort low --effort medium [--effort high] \
  --repeat 3 [--variant full --variant stripped] --plan
```

- 출력의 조합 수(과제 × 모델 × 강도 × 변형 × 반복), 채점 프롬프트 횟수, 실행 비용 상한(`--budget-usd` × 조합 수)을 사용자에게 보이고 승인받는다. 결과가 매번 달라서 반복은 기본 3회다.
- `stripped` 변형은 은퇴 판단이 필요할 때만 더한다. `agents_md_strip`이 빈 과제는 이 변형에서 빠진다.
- 승인 없이 `--yes`를 붙이지 않는다.

## 3. 실행

```bash
python3 $S/run.py --out "$W" <2단계와 같은 인자> --yes
```

실행기가 실행마다 하는 일은 아래와 같다.

1. 로컬 클론에서 과제 `base_commit`으로 임시 worktree를 시스템 임시 폴더(`agents-md-regress-*`)에 만든다. 사용자 메인 체크아웃과 Orca 워크트리는 건드리지 않는다. `~/.claude` 아래에 만들면 Claude Code가 보호 경로로 보고 편집을 거부한다(2026-11-15 실측: 16턴, 출력 8,670토큰을 쓰고 diff 0줄).
2. `AGENTS.md`를 `--agents-md-ref`(기본 `origin/main`)의 내용으로 덮어쓴다. base 커밋의 옛 `AGENTS.md`가 아니라 지금 규칙을 재기 위해서다. `stripped`면 과제의 `agents_md_strip` 줄을 지운다. 덮어쓴 상태를 임시 커밋해 채점 diff에서 뺀다.
3. `claude -p <프롬프트> --model <모델> --effort <강도> --output-format json --permission-mode acceptEdits --max-budget-usd <상한> --no-session-persistence --setting-sources project,local`로 돌린다. 사용자 설정(플러그인, 훅)과 사용자 전역 지침(`~/.claude/CLAUDE.md`)을 읽지 않아야 개인 규칙이 결과에 섞이지 않는다. 2026-11-15 실측에서 이 옵션을 주면 전역 지침 문자열이 보이지 않았고(입력 3,630토큰), 빼면 보였다(20,776토큰). 저장소 `CLAUDE.md`(`@AGENTS.md`)는 project 설정이라 그대로 읽힌다. 비대화형이라 셸 명령은 거부되고 파일 편집만 된다. worktree에 `node_modules`가 없어 타입 검사와 테스트는 돌지 않으므로 규칙 준수만 잰다.
4. 변경 diff(새 파일 포함)를 `$W/diffs/<run_id>.diff`에 남기고 채점한 뒤 worktree를 지운다(`git worktree remove`).

- 채점: `grading.regex`는 `measure.py`의 정규식을 그대로 쓴다. `grading.judge`는 위키 기준서의 그 규칙 절과 diff를 주고 도구 없는 `claude -p`로 판정한다. 채점 모델과 추론 강도는 `grade.py`의 `JUDGE_MODEL`, `JUDGE_EFFORT`로 고정한다. 바꾸면 이전 결과와 비교하지 않는다.
- 기록: `$W/runs.csv`에 실행 × 규칙 ID마다 한 행이 쌓인다(과제, 모델, 추론 강도, 변형, 반복 번호, 위반 수, 입력과 출력 토큰, 걸린 시간, 비용, 채점 모델과 비용). 실행 단위 상세는 `$W/runs.jsonl`이다.
- 오류 실행(`is_error`, 시간 초과, 예산 초과)은 행에 남기되 위반률 계산에서 뺀다.
- 변경이 없는 실행은 실행기가 `변경 없음(권한 거부 n건)` 경고를 낸다. 위반 0건이 아니라 과제를 못 한 것이므로 `runs.jsonl`의 `result`와 `permission_denials`를 보고 원인을 적는다.
- 정규식은 같은 줄의 `gridRef.current?.api.<메서드>`만 잡는다. `const api = gridRef.current?.api`로 꺼내 부르는 모양은 채점 프롬프트만 잡는다(2026-11-15 `grid07-2816`: 정규식 0건, 채점 프롬프트 3건). `measure.py` 정규식을 고치면 스프린트 측정 정의가 바뀌므로 여기서 고치지 않는다.

## 4. 요약

```bash
python3 $S/summary.py --csv "$W/runs.csv"
```

- 모델 × 강도 × 변형별 규칙 위반률과 실행당 평균 토큰, 비용 표에 은퇴 후보 줄과 권장 추론 강도 줄이 이어진다.
- 채점 프롬프트 비용은 캐시 상태에 따라 달라진다(같은 diff에서 $0.71, $0.08). 계획 단계의 비용 상한에는 채점 비용이 들어 있지 않으므로 채점 횟수와 함께 따로 알린다.
- 반복 3회의 위반률은 거칠다. 한 번 차이로 결론 내리지 않고, 표와 함께 실행 수를 적어 보고한다.

## 5. 위키에 결과 넘기기

위키는 다른 저장소라 `chucoding:handoff`로 위키 워크스페이스에 넘기고 기다리지 않는다. 브리핑에 아래를 넣는다.

- 넘길 행: `$W/runs.csv`의 전체 경로. 위키 `homedot-hub/knowledge/standards/effect/regression-runs.csv` 끝에 그대로 덧붙인다. 위키 데이터 설명 문서가 칸 이름을 다르게 정했으면 위키 이름을 따르고, 같은 뜻의 칸끼리 옮긴다. 이미 쌓인 행은 고치지 않는다.
- 4단계 요약(표, 은퇴 후보, 권장 추론 강도)과 돌린 조건(모델, 강도, 반복, 변형, `AGENTS.md` ref와 sha, 채점 모델)
- 브랜치와 PR은 위키의 `create-pr`, `wiki-review-harness`를 따른다. 티켓 키가 없으면 브리핑에서 사용자에게 묻게 한다.

은퇴 후보를 `AGENTS.md`에서 실제로 빼는 일은 hd-cloud-client 저장소 작업이라 이 스킬이 하지 않는다. 후보와 근거를 보고하고 그 저장소에서 작업하라고 안내한다.

## 하지 않는 것

- hd-cloud-client 메인 체크아웃이나 Orca 워크트리를 바꾸지 않는다. 임시 worktree만 만들고 지운다.
- 승인 없이 전체 조합을 돌리지 않는다.
- 위키 메인 체크아웃과 Notion을 고치지 않는다.
- 추론 강도를 PR 측정 지표(`measurements.csv`)에 넣지 않는다.
