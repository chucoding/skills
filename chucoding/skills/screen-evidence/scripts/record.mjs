// AS-IS와 TO-BE 녹화 스크립트. `ego-browser nodejs`로 실행
// 실행 전 sed로 치환: __OUT__(프레임 저장 폴더 절대경로), __NAME__(AS-IS 또는 TO-BE), __KEY__(티켓 키)
// 진입 경로, 대기 조건, 조작 셀렉터, 녹화 시간은 작업마다 수정
const { writeFile, mkdir, rm } = await import('node:fs/promises')
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

  // 녹화 시간(ms)과 초당 캡처 하한. 실측은 초당 약 14장
  const RECORD_MS = 6000
  const MIN_SHOTS_PER_SEC = 5
  const frames = []
  let shots = 0
  // 조작은 페이지 안 setTimeout으로 예약하고 Node는 캡처 반복만 담당
  // Node에서 evaluate나 click을 섞으면 같은 연결을 공유해 조작 시각이 캡처 왕복에 밀림
  await page.evaluate(() => {
    setTimeout(() => document.querySelector('<조작1 셀렉터>').click(), 1200)
    setTimeout(() => document.querySelector('<조작2 셀렉터>').click(), 3600)
  })
  // Page.startScreencast는 쓰지 않음. ego-browser의 page.cdp가 params의 sessionId를 거부해
  // Page.screencastFrameAck를 보낼 수 없고, ack가 없으면 프레임이 3장에서 멈춤
  // 캡처 실패는 삼키지 않고 그대로 던져 원인이 출력에 남게 함
  const t0 = Date.now()
  while (Date.now() - t0 < RECORD_MS) {
    const shot = await page.cdp('Page.captureScreenshot', { format: 'jpeg', quality: 80 })
    shots++
    // 직전과 같은 화면은 버림. 정지 구간의 길이는 concat 목록의 duration이 유지
    if (frames.length === 0 || frames[frames.length - 1].data !== shot.data) {
      frames.push({ data: shot.data, ts: Date.now() / 1000 })
    }
  }
  const shotsPerSec = Number((shots / ((Date.now() - t0) / 1000)).toFixed(1))

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

  // 캡처가 초당 하한에 못 미치면 저장하지 않고 실패 종료. 동작이 끊겨 담기므로 GIF로 쓸 수 없음
  if (shotsPerSec < MIN_SHOTS_PER_SEC) {
    console.log(JSON.stringify({ frames: frames.length, shots, shotsPerSec, rafPerSec, error: '캡처 속도 부족. 다시 녹화 필요' }))
    throw new Error(`초당 캡처 ${shotsPerSec}장. 하한 ${MIN_SHOTS_PER_SEC}장 미만`)
  }

  // 재녹화 시 이전 프레임이 시트에 섞이지 않도록 폴더 비우기. 보관 폴더의 frames- 폴더만 대상
  // 키 구간을 영숫자 시작으로 제한해 `..` 경로 통과 차단
  if (!/^\/.+\/\.cache\/chucoding\/screen-evidence\/[A-Za-z0-9][A-Za-z0-9._-]*\/frames-[A-Za-z0-9-]+$/.test(OUT)) {
    throw new Error(`프레임 폴더 경로 아님: ${OUT}`)
  }
  await rm(OUT, { recursive: true, force: true })
  await mkdir(OUT, { recursive: true })

  // 프레임 JPEG 저장과 ffmpeg concat 목록 작성. duration에 실제 프레임 간격 기록
  let list = ''
  for (let i = 0; i < frames.length; i++) {
    const file = `f${String(i).padStart(4, '0')}.jpg`
    await writeFile(`${OUT}/${file}`, Buffer.from(frames[i].data, 'base64'))
    const dur = i < frames.length - 1 ? frames[i + 1].ts - frames[i].ts : 0.8
    list += `file '${file}'\nduration ${dur.toFixed(3)}\n`
  }
  list += `file 'f${String(frames.length - 1).padStart(4, '0')}.jpg'\n`
  await writeFile(`${OUT}/list.txt`, list)
  console.log(JSON.stringify({ frames: frames.length, shots, shotsPerSec, rafPerSec }))
} finally {
  await page.cdp('Emulation.clearDeviceMetricsOverride').catch(() => {})
  await task.finish({ keep: [] })
}
