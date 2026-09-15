---
name: browser-automation
description: ego-browser로 페이지를 열어 브라우저 자동화나 E2E 테스트를 할 때, 네이티브 다이얼로그(alert, confirm, prompt)가 열리기 전에 무력화하는 절차. 주입 스크립트, heredoc 단위로 만료되는 주입 수명, 다이얼로그를 띄울 수 있는 조작 전 확인 방법, 태스크 스페이스 정리를 포함한다. ego-browser를 사용하거나 E2E 테스트로 화면을 확인할 때 페이지를 열기 전에 사용한다.
---

이 스킬은 `ego-browser`로 페이지를 열어 브라우저 자동화나 E2E 테스트를 수행할 때 적용된다. 네이티브 다이얼로그 무력화, 주입 수명 관리, 조작 전 확인, 태스크 스페이스 정리 절차를 다룬다.

## 브라우저 자동화 지침

`ego-browser` 스킬로 페이지를 열 때는 네이티브 다이얼로그(`alert`, `confirm`, `prompt`)를 열리기 전에 무력화한다. 열린 뒤에는 처리할 수 없다. ego lite 는 다이얼로그가 열리면 `confirm` 기준 약 40ms 안에 태스크 스페이스 소유권을 `agentDelegatedToUser` 로 넘기고 `Page.handleJavaScriptDialog` 호출을 거부한다. 스킬 문서는 에이전트가 다이얼로그를 처리하라고 안내하지만 런타임이 그보다 이르게 권한을 회수하므로 그 경로는 쓸 수 없다. 한 번 위임되면 사용자 확인 없이 `takeOverTaskSpace()` 를 부를 수 없어 자력 복구도 막힌다.

- 주입은 `ego-browser nodejs` heredoc 단위로 만료된다. **페이지를 이동하는 모든 heredoc에서, 그 이동 직전에 매번 주입한다.** 한 번 주입해 두고 다음 heredoc에서 이동하면 무력화가 풀린 채로 진행된다.

```js
await cdp('Page.addScriptToEvaluateOnNewDocument', {
  source: `
    window.__dialogs = [];
    window.alert   = (m) => { window.__dialogs.push(['alert', m]) };
    window.confirm = (m) => { window.__dialogs.push(['confirm', m]); return true };
    window.prompt  = (m, d) => { window.__dialogs.push(['prompt', m]); return d ?? '' };
  `
})
```

- `addScriptToEvaluateOnNewDocument` 등록은 그 heredoc 의 CDP 세션에 묶여 있어 프로세스가 끝나면 함께 사라진다. 같은 heredoc 안에서만 이동과 새로고침을 넘어 살아남는다. 확인한 만료 시점은 다음과 같다.

| 시점 | 주입한 값 |
|------|-----------|
| 주입한 heredoc 안에서 이동한 뒤 | 살아 있음 |
| 다음 heredoc, 이동 전 | 살아 있음 (문서가 그대로라서) |
| 다음 heredoc, 이동한 뒤 | 사라짐 |

- 주입만 하고 이동하지 않으면 이미 열려 있는 문서에는 적용되지 않는다. 제어권을 되찾은 뒤 재주입할 때도 새로고침이나 이동을 함께 걸어야 효력이 생긴다.
- `js()` 로 덮어쓰지 않는다. 페이지 안에서 덮어쓰면 다음 이동에서 원래 함수가 돌아온다.
- 주입은 대상 탭 기준이다. 도중에 새 탭이 열리면 그 탭에도 다시 주입한다.
- `confirm` 이 항상 `true` 를 반환하므로 확인 버튼을 누른 분기로 플로우가 이어진다.
- 다이얼로그를 띄울 수 있는 조작(저장, 삭제, 이탈 등) 직전에 `window.__dialogs` 가 배열인지 `js()` 로 확인한다. `undefined` 또는 `null` 이면 무력화가 풀린 상태이므로 조작하지 말고 재주입과 이동을 먼저 한다. 값이 배열이면 그 내용으로 다이얼로그가 실제로 떴는지 읽는다.
- `beforeunload` 이탈 확인창은 `window.confirm` 과 다른 경로라 이 방식으로 막히지 않는다. 필요하면 그때 따로 처리한다.
- 다이얼로그 자체가 검증 대상일 때는 무력화하지 않고 핸드오프를 받아들인다. 사용자에게 무엇을 누를지 알린 뒤 확인을 받고 `takeOverTaskSpace()` 로 이어받는다.

태스크 스페이스는 작업이 끝나도 자동으로 닫히지 않는다. `completeTaskSpace(name, { keep: false })` 를 직접 호출해야 하며, 부르지 않으면 열어둔 탭이 그대로 남는다.
