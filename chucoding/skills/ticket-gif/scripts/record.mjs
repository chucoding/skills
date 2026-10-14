// AS-IS와 TO-BE 녹화 스크립트. `ego-browser nodejs`로 실행
// 실행 전 sed로 치환: __OUT__(프레임 저장 폴더 절대경로), __NAME__(AS-IS 또는 TO-BE), __KEY__(티켓 키)
// 진입 경로, 대기 조건, 조작 셀렉터, 녹화 시간은 작업마다 수정
const { writeFile, mkdir } = await import('node:fs/promises')
const OUT = '__OUT__'
const task = await taskSpace('__KEY__ 녹화 __NAME__')
const page = task.page('p1')
// 실패해도 태스크 스페이스 정리와 뷰포트 고정 해제를 보장
try {
  // 네이티브 다이얼로그 무력화. 페이지 이동 전에 등록
  await page.cdp('Page.addScriptToEvaluateOnNewDocument', {
    source: `window.__dialogs=[];window.alert=(m)=>{window.__dialogs.push(['alert',m])};window.confirm=(m)=>{window.__dialogs.push(['confirm',m]);return true};window.prompt=(m,d)=>{window.__dialogs.push(['prompt',m]);return d??''};`,
  })
  // 창 크기와 무관하게 1440×900(16:10) 고정
  await page.cdp('Emulation.setDeviceMetricsOverride', { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false })

  // 실제 사용 경로로 진입. 상세 URL 직접 진입은 앱 구조(KeepAliveOutlet 등)에 따라 동작이 달라질 수 있음
  await page.goto('<목록 URL>')
  // … 목록 조회, 상세 진입, 대상 버튼이 보일 때까지 대기 …

  await page.cdp('Page.bringToFront')
  await page.waitForTimeout(2500)
  await page.events() // 이전 이벤트 비우기

  const frames = []
  await page.cdp('Page.startScreencast', { format: 'jpeg', quality: 80, maxWidth: 1440, maxHeight: 900, everyNthFrame: 1 })
  // 조작은 페이지 안 setTimeout으로 예약하고 Node는 프레임 수신과 ack만 담당
  // Node에서 evaluate나 click을 섞으면 같은 연결을 공유해 프레임 수신이 끊김(실측: 두 번째 이동 프레임 2장)
  await page.evaluate(() => {
    setTimeout(() => document.querySelector('<조작1 셀렉터>').click(), 1200)
    setTimeout(() => document.querySelector('<조작2 셀렉터>').click(), 3600)
  })
  const t0 = Date.now()
  while (Date.now() - t0 < 6000) {
    for (const e of await page.events()) {
      if (e.method === 'Page.screencastFrame') {
        frames.push({ data: e.params.data, ts: e.params.metadata.timestamp })
        // ack는 await로 즉시 전송. 늦으면 프레임 누락
        await page.cdp('Page.screencastFrameAck', { sessionId: e.params.sessionId }).catch(() => {})
      }
    }
  }
  await page.cdp('Page.stopScreencast')

  // 녹화 직후 rAF 횟수 측정. 초당 15 미만이면 창이 가려진 상태라 재녹화 필요
  const rafPerSec = await page.evaluate(
    () =>
      new Promise((resolve) => {
        let n = 0
        const start = performance.now()
        const tick = () => {
          n++
          if (performance.now() - start < 1000) requestAnimationFrame(tick)
          else resolve(n)
        }
        requestAnimationFrame(tick)
      }),
  )

  // 프레임 0장이면 저장하지 않고 실패 종료. 창 가림이나 조작 셀렉터 오류가 원인
  if (frames.length === 0) {
    console.log(JSON.stringify({ frames: 0, rafPerSec, error: '프레임 없음. 다시 녹화 필요' }))
    throw new Error('녹화 프레임 0장')
  }

  // 프레임 JPEG 저장과 ffmpeg concat 목록 작성. duration에 실제 프레임 간격 기록
  await mkdir(OUT, { recursive: true })
  let list = ''
  for (let i = 0; i < frames.length; i++) {
    const file = `f${String(i).padStart(4, '0')}.jpg`
    await writeFile(`${OUT}/${file}`, Buffer.from(frames[i].data, 'base64'))
    const dur = i < frames.length - 1 ? frames[i + 1].ts - frames[i].ts : 0.8
    list += `file '${file}'\nduration ${dur.toFixed(3)}\n`
  }
  list += `file 'f${String(frames.length - 1).padStart(4, '0')}.jpg'\n`
  await writeFile(`${OUT}/list.txt`, list)
  console.log(JSON.stringify({ frames: frames.length, rafPerSec }))
} finally {
  await page.cdp('Emulation.clearDeviceMetricsOverride').catch(() => {})
  await task.finish({ keep: [] })
}
