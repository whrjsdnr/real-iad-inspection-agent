/** Run on host Ubuntu AFTER starting the isolated read-only GUI.
 * Never posts inference/reviews/chat, never starts/stops operational services.
 */
import {chromium} from '../inspection-gui/node_modules/playwright/index.mjs'
import {mkdir,writeFile,access} from 'node:fs/promises'
import path from 'node:path'
const base=process.env.GUI_VALIDATION_URL??'http://127.0.0.1:15173'
const parsed=new URL(base)
if(!['127.0.0.1','localhost'].includes(parsed.hostname))throw new Error('Use the isolated local validation server')
const stamp=new Date().toISOString().replaceAll(':','-')
const out=path.resolve('reports/gui_validation/screenshots',stamp)
await mkdir(out,{recursive:true})
const result={started_at:new Date().toISOString(),base,screenshots:[],errors:[],measurements:[],skipped:[]}
let browser
try{
 const env={...process.env}
 const libs='/tmp/pw-libs/root/usr/lib/x86_64-linux-gnu'
 try{await access(libs);env.LD_LIBRARY_PATH=[libs,env.LD_LIBRARY_PATH].filter(Boolean).join(':')}catch{/* use host libraries */}
 // Keep Chromium's sandbox enabled; no --no-sandbox or host security changes.
 browser=await chromium.launch({headless:true,chromiumSandbox:true,env})
 const context=await browser.newContext({viewport:{width:1600,height:950},reducedMotion:'reduce'})
 const page=await context.newPage()
 page.on('pageerror',e=>result.errors.push(String(e)))
 await page.route('**/*',async route=>{
  const req=route.request(),url=new URL(req.url())
  if(req.method()==='POST'&&!['/api/tools/query_error_stats','/api/tools/compute_inspection_metrics','/api/tools/get_case_evidence','/api/tools/get_training_status'].includes(url.pathname))return route.abort('blockedbyclient')
  return route.continue()
 })
 const shot=async name=>{const filename=`${name}.png`;await page.screenshot({path:path.join(out,filename),fullPage:true});result.screenshots.push(filename)}
 const overflow=async name=>result.measurements.push({name,...await page.evaluate(()=>({viewport:innerWidth,content:document.documentElement.scrollWidth,overflow:document.documentElement.scrollWidth>innerWidth+1,heap_bytes:performance.memory?.usedJSHeapSize??null}))})
 const start=performance.now();await page.goto(base+'/#/',{waitUntil:'domcontentloaded'});await page.getByRole('button',{name:/대시보드 시작하기/}).waitFor();result.measurements.push({name:'intro_dom_ready_ms',value:performance.now()-start})
 await page.waitForTimeout(1200);await shot('intro-reduced');await overflow('intro-desktop')
 const precision=page.frameLocator('iframe[title="INSPECT AI V6 · 5시점 검사 개념 시연"]')
 if(await page.locator('iframe').count()){
  await precision.locator('#timeline button').nth(1).click();await page.waitForTimeout(400)
  await shot('precision-five-camera-scene')
  await precision.locator('#timeline button').nth(2).click();await page.waitForTimeout(400);await shot('precision-model-evidence')
 }else await page.getByRole('button',{name:/02.*카메라|카메라 C1/}).first().click().catch(()=>result.skipped.push('Camera-stage step selector unavailable'))
 await shot('five-camera-scene')
 await page.getByRole('button',{name:/대시보드 시작하기/}).click();await page.waitForTimeout(1400);await shot('dashboard')
 const displayModes=page.getByRole('group',{name:'3D 표시 모드'})
 if(await displayModes.count()){for(const mode of ['재질','겹쳐 보기','히트맵']){await displayModes.getByRole('button',{name:mode,exact:true}).click();await page.waitForTimeout(400);await shot(`3d-${mode==='재질'?'material':mode==='히트맵'?'heatmap':'overlay'}`)}await displayModes.getByRole('button',{name:'겹쳐 보기',exact:true}).click()}
 const selector=page.getByRole('combobox').first();const available=await selector.locator('option').evaluateAll(nodes=>nodes.map(n=>n.value))
 const categories=['toothbrush','usb','bottle_cap','pcb','button_battery','zipper','wooden_beads'].filter(c=>available.includes(c))
 for(const category of categories){const t=performance.now();await selector.selectOption(category);await page.waitForTimeout(650);await shot(`template-${category}`);result.measurements.push({name:'category_ui_settle_ms',category,value:performance.now()-t})}
 const parts=page.getByRole('group',{name:'부위 선택'}).getByRole('button')
 if(await parts.count()){await parts.first().click();await page.waitForTimeout(500);await shot('region-selection-and-no-data-heatmap')}
 await overflow('dashboard-desktop')
 const before=await page.evaluate(()=>performance.memory?.usedJSHeapSize??null)
 for(let i=0;i<12&&categories.length>1;i++){await selector.selectOption(categories[i%categories.length]);await page.waitForTimeout(150)}
 result.measurements.push({name:'category_switch_heap_bytes',before,after:await page.evaluate(()=>performance.memory?.usedJSHeapSize??null),note:'No forced GC; not a leak proof or WebGL frame-time measurement'})
 const item=categories[0]??available[0]
 if(item){
  const response=await context.request.get(`${base}/api/inference/sample_products?item=${encodeURIComponent(item)}&limit=1`)
  if(response.ok()){
   const products=(await response.json()).products
   if(products?.length){await page.goto(`${base}/#/dashboard?focus=${encodeURIComponent(products[0])}&camera=C1`);try{await page.getByRole('dialog').waitFor({timeout:8000});await shot('individual-product');await page.keyboard.press('Escape')}catch{result.skipped.push('Individual product dialog did not open')}}else result.skipped.push('No real complete five-view product returned')
  }else result.skipped.push('Real product API unavailable')
 }
 await page.goto(base+'/#/chat');await page.waitForTimeout(700);await shot('chat-context-controls')
 await page.goto(base+'/#/inference');await page.waitForTimeout(700);await shot('inference-idle');result.skipped.push('Actual inference-progress screen: no model job was submitted; use an existing isolated lightweight test job')
 await page.goto(base+'/#/');await page.setViewportSize({width:390,height:844});await page.waitForTimeout(700);await shot('intro-mobile');await overflow('intro-mobile')
 await page.goto(base+'/#/dashboard');await page.waitForTimeout(700);await shot('dashboard-mobile');await overflow('dashboard-mobile')
 await page.route('**/api/**',r=>r.abort('connectionfailed'));await page.reload();await page.waitForTimeout(1200);await shot('api-connection-failure')
 // Real failures must not reveal fixture case IDs.
 const text=await page.locator('body').innerText();if(text.includes('FIXTURE 폭백'))throw new Error('Unexpected fixture fallback')
 result.state=result.errors.length?'PARTIAL':'CAPTURED_REQUIRES_HUMAN_REVIEW'
 await context.close()
}catch(error){result.state='BLOCKED';result.errors.push(String(error))}
finally{if(browser)await browser.close();result.finished_at=new Date().toISOString();await writeFile(path.join(out,'browser-validation.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result,null,2))}
if(result.state==='BLOCKED')process.exitCode=2
