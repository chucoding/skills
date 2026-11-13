---
name: firebase-env
description: Firebase 저장소를 워크트리나 새 클론에서 개발하고 배포할 때 따르는 절차. 죽은 토큰을 걸러내는 인증 검증, 워크트리마다 다시 필요한 `firebase use` 연결, 빌드 시점에 번들로 인라인되는 환경변수 확인, 기존 저장소에서 `firebase init`을 쓰지 않는 이유, `--only`로 좁히는 배포를 포함한다. 저장소에 `firebase.json`이 있거나 firebase, firestore, functions, hosting, 배포, 에뮬레이터가 언급되면 `firebase` 명령을 실행하기 전에 사용한다.
---

# Firebase 개발 환경 지침

`firebase.json`이 있는 저장소를 오르카 워크트리나 새 클론에서 다룰 때 이 절차를 따른다. 착수 점검부터 배포까지가 적용 범위다.

이 지침이 필요한 이유는 Firebase CLI의 상태가 **저장소가 아니라 로컬 머신에 흩어져 저장되기** 때문이다. 인증 토큰은 홈 디렉터리의 configstore에, 활성 프로젝트는 디렉터리 경로별 맵에 있고, 빌드 타임 환경변수는 gitignore된 `.env`에 있다. 저장소를 clone하거나 워크트리를 새로 만들면 코드는 그대로지만 이 셋이 전부 비어 있다. 그런데 CLI는 비어 있다는 사실을 착수 시점에 알려주지 않고, 배포하거나 사용자가 화면을 열어본 뒤에야 드러난다.

## 1. 착수 점검

Firebase 관련 명령을 처음 실행하기 전에 세 가지를 순서대로 확인한다. 셋 다 통과해야 그다음으로 간다.

### 1.1 인증이 실제로 살아 있는지

`firebase login`의 출력을 신뢰하지 않는다. 이 명령은 configstore에 토큰 **레코드가 있는지**만 보고 `Already logged in as ...`을 출력한다. 토큰이 폐기됐는지는 확인하지 않는다. Google은 OAuth refresh token을 6개월간 미사용 시 폐기하므로, 몇 달 만에 만지는 저장소에서 흔히 발생한다.

실제 API를 한 번 때려서 검증한다.

```bash
firebase projects:list
```

프로젝트 표가 나오면 유효하다. `Failed to list Firebase projects`가 나오면 토큰이 죽은 것이다. `firebase-debug.log`에서 `POST https://www.googleapis.com/oauth2/v3/token 400`과 뒤따르는 `401`을 확인할 수 있다.

죽었으면 재인증한다. `--reauth` 없이 `firebase login`만 실행하면 `Already logged in`만 출력하고 아무 일도 일어나지 않는다.

```bash
firebase login --reauth
```

이 명령은 브라우저가 필요하고 사용자 입력을 받는다. 에이전트가 직접 실행하지 말고 사용자에게 실행을 요청한다. 브라우저가 없는 환경이면 `firebase login --no-localhost`를 안내한다.

재인증이 끝난 뒤 `firebase login <코드>`가 `No pending login session found`로 실패하는 경우가 있는데, 이는 앞선 프로세스가 세션을 이미 소진했다는 뜻이지 실패가 아니다. `firebase projects:list`로 다시 검증해 통과하면 그대로 진행한다.

### 1.2 이 디렉터리가 프로젝트에 연결돼 있는지

```bash
firebase use
```

프로젝트 ID가 나오면 통과다. `Error: No active project`면 연결이 없다.

`.firebaserc`는 대개 `.gitignore` 대상이라 저장소에 커밋되지 않는다. 그래서 **워크트리를 새로 만들 때마다, 클론할 때마다 다시 연결해야 한다.** CLI는 디렉터리 절대경로를 키로 활성 프로젝트를 기억하므로, 메인 체크아웃에서 연결해 두었어도 워크트리에는 적용되지 않는다.

연결할 프로젝트 ID는 추측하지 않는다. 저장소의 `.env`에 이미 들어 있는 경우가 많으니 거기서 찾는다. `.env` 위치는 저장소마다 다르므로(루트, `app/`, `packages/*/`) 먼저 찾는다.

```bash
find . -name ".env*" -not -path "*/node_modules/*"
grep -rE "PROJECT_ID" <찾은 .env 경로>
firebase projects:list
```

둘을 대조해 일치하는 ID로 연결한다.

```bash
firebase use <project-id>
```

여러 환경(dev, prod)을 오가는 저장소면 `firebase use --add`로 alias를 붙인다. 다만 이 명령은 대화형이라 사용자에게 맡기고, 에이전트는 결과만 검증한다. alias에 공백이 섞여 들어가는 일이 있으니 `.firebaserc`를 눈으로 확인한다.

```json
{ "projects": { "default": "<project-id>" } }
```

`Error: Invalid project id`는 configstore의 `activeProjects`에 남은 alias가 `.firebaserc`에 없을 때 난다. `.firebaserc`는 gitignore 대상이라 워크트리를 지우면 함께 사라지지만 configstore 항목은 남으므로, 이슈 번호로 워크트리 경로를 재사용하면 alias만 남고 매핑이 없는 상태가 된다. `No active project`가 아니라 이 에러가 나오면 이 상태를 먼저 의심한다.

`firebase use --clear`도 같은 에러로 막힌다. 현재 값을 먼저 검증하기 때문이다. 복구하려면 `.firebaserc`를 올바르게 다시 쓰고, CLI configstore의 `activeProjects`에서 해당 디렉터리 항목을 지운 뒤 `firebase use default`로 다시 잡는다.

경로 구분자 이스케이프가 까다로우니 키를 문자열 포함 여부로 찾는다.

```bash
node -e "
const fs=require('fs'), path=require('path');
const home = process.env.USERPROFILE || process.env.HOME;
const p=path.join(home,'.config','configstore','firebase-tools.json');
const d=JSON.parse(fs.readFileSync(p,'utf8'));
const keys=Object.keys(d.activeProjects||{}).filter(k=>k.includes('<디렉터리명>'));
for (const k of keys) delete d.activeProjects[k];
fs.writeFileSync(p, JSON.stringify(d, null, '\t'));
console.log('지운 키:', keys);
"
firebase use default && firebase use
```

### 1.3 빌드 타임에 인라인되는 환경변수가 채워졌는지

이 단계가 셋 중 가장 조용히 실패한다. 건너뛰어도 빌드는 성공하고 타입 검사도 통과하며, 배포 후 사용자가 기능을 눌러야 드러난다.

Vite의 `VITE_*`, CRA의 `REACT_APP_*`, Next의 `NEXT_PUBLIC_*`은 런타임에 읽는 값이 아니라 **빌드 시점에 문자열로 치환된다.** 값이 비어 있으면 빈 문자열이 그대로 번들에 박히고, `${FUNCTIONS_URL}/foo` 같은 코드는 같은 오리진의 `/foo`를 호출해 404가 난다.

저장소에 이 값을 채우는 부트스트랩 스크립트가 있는지 먼저 본다. `package.json`의 scripts에서 `proxy`, `setup`, `bootstrap`, `env` 같은 이름을 찾고, `scripts/` 디렉터리도 훑는다. 있으면 빌드 전에 돌린다.

```bash
pnpm proxy   # 저장소마다 이름이 다르다
```

그런 다음 빈 값이 남았는지 확인한다.

```bash
grep -nE "^[A-Z_]+=$" <.env 경로>
```

출력이 있으면 아직 덜 채워진 것이다. 어떤 키가 필수인지는 `.env.example`과 대조해 판단한다.

빌드를 이미 했다면 산출물에서 직접 검증할 수 있다. 이것이 가장 확실한 방법이다.

빌드 산출물 디렉터리는 저장소마다 다르다(`dist`, `build`, `.next`). `vite.config.ts`나 `next.config.js`의 출력 설정에서 확인한 뒤 대입한다.

```bash
grep -aoh "=\"\"" <산출물 경로>/assets/*.js | head
grep -ao ".\{0,40\}cloudfunctions\.net.\{0,20\}" <산출물 경로>/assets/*.js | head
```

호출 주소가 들어 있어야 할 자리에 빈 문자열만 보이면 그 빌드는 배포하면 안 된다. `.env`를 채우고 다시 빌드한다.

## 2. `firebase init`을 쓰지 않는다

이미 `firebase.json`이 있는 저장소에서 `firebase init`은 설정을 새로 쓰는 명령이다. 기존 `firebase.json`, `firestore.rules`, `functions/`를 덮어쓸지 되묻고, 프롬프트를 잘못 넘기면 hosting rewrites나 보안 규칙이 조용히 사라진다. 커밋되지 않은 규칙 변경이 함께 날아가면 복구도 어렵다.

착수 단계에서 필요한 건 "이 디렉터리가 어느 프로젝트를 가리키는가" 하나뿐이고, 그건 `firebase use`가 한다. `firebase init`은 저장소에 Firebase 설정을 **처음 만들 때만** 쓴다.

기능을 새로 붙여야 해서 설정 파일 추가가 필요하면, `init` 전체를 돌리지 말고 `firebase init <feature>`로 대상을 좁히고, 덮어쓰기 프롬프트가 나오면 무엇을 덮어쓰는지 사용자에게 보고한 뒤 지시를 받는다.

## 3. 배포

### 배포 전 확인

```bash
firebase use                          # 활성 프로젝트가 잡혀 있는가
grep -nE "^[A-Z_]+=$" <.env 경로>    # 빌드 타임 변수에 빈 값이 없는가
```

hosting을 함께 올린다면 빌드 산출물이 최신인지도 본다. `firebase.json`의 hosting에 `predeploy`가 없으면 CLI는 빌드 디렉터리를 **있는 그대로** 올린다. 오래된 산출물이나 환경변수가 비어 있던 시절의 빌드가 그대로 나간다.

`hosting`은 멀티사이트 저장소에서 배열이므로 양쪽을 함께 처리한다.

```bash
node -e "
const h=require('./firebase.json').hosting;
const sites=Array.isArray(h)?h:h?[h]:[];
console.log(sites.map(s=>[s.site||s.target||'(단일)', s.predeploy??null]));
"
```

`predeploy`가 `null`인 사이트는 배포 전에 빌드를 직접 돌린다.

### 범위를 좁혀서 배포

`firebase deploy`는 functions, firestore 규칙, hosting을 전부 올린다. 작업과 무관한 대상까지 나가면 되돌릴 지점이 불분명해지므로 `--only`로 좁힌다.

```bash
firebase deploy --only functions,firestore:rules
firebase deploy --only functions:myFunction
firebase deploy --only hosting
```

저장소에 `pnpm push` 같은 전체 배포 스크립트가 있어도, 이번 변경에 필요한 대상만 올리는 편이 낫다. 전체 배포는 사용자가 명시적으로 요청했을 때만 쓴다.

### 배포는 사용자 승인을 받는다

배포는 되돌리기 어렵고 외부에 나가는 작업이다. 명령과 대상을 보여주고 승인을 받은 뒤 실행한다. 사용자가 직접 실행하겠다고 하면 명령만 정리해 전달한다.

### 스케줄 함수를 처음 배포했을 때

`onSchedule` 함수는 배포 직후 실행되지 않고 다음 스케줄까지 기다린다. Cloud Scheduler 콘솔에서 강제 실행하면 바로 결과를 볼 수 있다는 점을 사용자에게 알린다. 스케줄을 기다리게 두면 다음 날까지 검증이 밀린다.

## 4. Firebase 공식 스킬과의 관계

`firebase-basics`, `firebase-firestore`, `firebase-security-rules-auditor` 같은 Google 공식 스킬이 설치돼 있으면 각 기능의 사용법은 그쪽을 따른다. 이 스킬은 그 스킬들이 다루지 않는 지점만 채운다. 공식 스킬은 신규 프로젝트를 전제로 쓰여 있어서, 이미 굴러가는 저장소를 새 워크트리에서 다시 여는 상황과 죽은 토큰, gitignore된 `.firebaserc`, 빌드 타임 환경변수를 다루지 않는다.

충돌하는 지점에서는 이 스킬을 따른다. 특히 `firebase init` 관련 안내가 그렇다.

## 5. 막혔을 때

`firebase-debug.log`는 실패한 명령의 HTTP 요청과 응답 코드를 그대로 남긴다. 추측하기 전에 이 파일부터 읽는다. 대개 `.gitignore` 대상이라 커밋 걱정은 하지 않아도 된다.

에러 문자열은 firebase-tools 버전마다 바뀌므로 증상 목록을 외워 두지 않는다. 위 1절의 세 가지 검증(`projects:list`, `firebase use`, 빈 환경변수)을 순서대로 다시 돌려 어느 단계가 비어 있는지부터 좁힌다.
