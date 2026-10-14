// 정적 화면 캡처 스크립트. `ego-browser nodejs`로 실행
// 실행 전 sed로 치환: __OUT__(PNG 저장 경로 절대경로), __NAME__(AS-IS 또는 TO-BE), __KEY__(티켓 키)
// 진입 경로와 대기 조건은 작업마다 수정
const { writeFile, mkdir } = await import('node:fs/promises')
const { dirname } = await import('node:path')
const OUT = '__OUT__'
const task = await taskSpace('__KEY__ 캡처 __NAME__')
const page = task.page('p1')

// 네이티브 다이얼로그 무력화. 페이지 이동 전에 등록
await page.cdp('Page.addScriptToEvaluateOnNewDocument', {
  source: `window.__dialogs=[];window.alert=(m)=>{window.__dialogs.push(['alert',m])};window.confirm=(m)=>{window.__dialogs.push(['confirm',m]);return true};window.prompt=(m,d)=>{window.__dialogs.push(['prompt',m]);return d??''};`,
})
// GIF와 같은 1440×900(16:10) 고정
await page.cdp('Emulation.setDeviceMetricsOverride', { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false })

// 실제 사용 경로로 진입
await page.goto('<목록 URL>')
// … 대상 화면이 다 그려질 때까지 대기(스켈레톤, 로딩 표시 해제 확인) …
await page.waitForTimeout(1000)

// 뷰포트 기준 캡처. 화면 아래까지 담아야 하면 captureBeyondViewport: true
const { data } = await page.cdp('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false })
await page.cdp('Emulation.clearDeviceMetricsOverride')

await mkdir(dirname(OUT), { recursive: true })
await writeFile(OUT, Buffer.from(data, 'base64'))
console.log(JSON.stringify({ out: OUT }))
await task.finish({ keep: [] })
