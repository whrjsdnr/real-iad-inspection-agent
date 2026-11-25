/* 화면 4종 스크린샷 + reduced-motion 정적 렌더 확인 (일회성 검증 스크립트). */
import { chromium } from 'playwright'

const BASE = process.env.GUI_BASE ?? 'http://localhost:5173'
const OUT = process.env.SHOT_DIR ?? '/tmp/gui-shots'

const routes = [
  ['intro', '#/'],
  ['dashboard', '#/dashboard'],
  ['chat', '#/chat'],
  ['inference', '#/inference'],
]

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1600, height: 950 } })

for (const [name, hash] of routes) {
  await page.goto(`${BASE}/${hash}`)
  await page.waitForTimeout(2500)
  await page.screenshot({ path: `${OUT}/${name}.png` })
  console.log('shot:', `${OUT}/${name}.png`)
}

// reduced-motion: 전 화면 즉시 정적 렌더 확인
const rp = await browser.newPage({
  viewport: { width: 1600, height: 950 },
  reducedMotion: 'reduce',
})
for (const [name, hash] of routes) {
  await rp.goto(`${BASE}/${hash}`)
  await rp.waitForTimeout(1200)
  const anim = await rp.evaluate(() => {
    const el = document.querySelector('.motion-rise')
    const dot = document.querySelector('.live-dot')
    const cs = el ? getComputedStyle(el) : null
    const ds = dot ? getComputedStyle(dot) : null
    return {
      riseOpacity: cs?.opacity,
      riseAnimationDuration: cs?.animationDuration,
      dotAnimationDuration: ds?.animationDuration,
    }
  })
  console.log(`reduced-motion ${name}:`, JSON.stringify(anim))
  await rp.screenshot({ path: `${OUT}/${name}-reduced.png` })
}

await browser.close()
console.log('done')
