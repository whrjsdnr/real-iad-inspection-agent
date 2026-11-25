/** HOST browser validation only. Reads actual data, never submits inference/review jobs. */
import {chromium} from '../inspection-gui/node_modules/playwright/index.mjs'
import {mkdir,writeFile,access} from 'node:fs/promises'
import path from 'node:path'
const base=process.env.GUI_VALIDATION_URL??'http://127.0.0.1:15173'
if(!['127.0.0.1','localhost'].includes(new URL(base).hostname))throw new Error('Use the local isolated development/sharing service')
const out=path.resolve('reports/gui_validation/spatial/screenshots',new Date().toISOString().replaceAll(':','-'))
await mkdir(out,{recursive:true})
const result={state:'BLOCKED',screenshots:[],errors:[],measurements:[]}
let browser
try{
 const env={...process.env},libs='/tmp/pw-libs/root/usr/lib/x86_64-linux-gnu'
 try{await access(libs);env.LD_LIBRARY_PATH=[libs,env.LD_LIBRARY_PATH].filter(Boolean).join(':')}catch{/* host libraries */}
 browser=await chromium.launch({headless:true,chromiumSandbox:true,env})
 const page=await browser.newPage({viewport:{width:1600,height:1050},reducedMotion:'reduce'})
 page.on('pageerror',error=>result.errors.push(String(error)))
 await page.route('**/*',route=>{
  const request=route.request(),pathname=new URL(request.url()).pathname
  const readPosts=['/team/login','/api/tools/query_error_stats','/api/tools/compute_inspection_metrics','/api/tools/get_case_evidence','/api/tools/get_training_status','/api/tools/get_final_performance','/api/tools/query_spatial_evidence']
  if(!['GET','HEAD','OPTIONS'].includes(request.method())&&!(request.method()==='POST'&&readPosts.includes(pathname)))return route.abort('blockedbyclient')
  return route.continue()
 })
 await page.goto(base+'/#/dashboard')
 if(page.url().includes('/team/login')){
  if(!process.env.TEAM_ACCESS_TOKEN)throw new Error('Provide the team environment locally; token is never printed')
  await page.getByLabel('팀 접속 키').fill(process.env.TEAM_ACCESS_TOKEN)
  await page.getByRole('button',{name:'접속',exact:true}).click()
 }
 const shot=async name=>{const file=path.join(out,name+'.png');await page.screenshot({path:file,fullPage:true});result.screenshots.push(file)}
 for(const item of ['toothbrush','zipper']){
  await page.getByRole('combobox').first().selectOption(item)
  const panel=page.locator('[aria-label="세부 공간 히트맵"]');await panel.scrollIntoViewIfNeeded()
  await page.getByLabel('공간 근거 제품',{exact:true}).waitFor()
  await page.waitForTimeout(1000);await shot(item+'-same-data-before-after')
  for(const model of ['rt','hvq','overlay']){
   await page.getByLabel('공간 모델',{exact:true}).selectOption(model)
   await page.waitForTimeout(700);await shot(item+'-'+model)
  }
  await page.getByLabel('공간 모델',{exact:true}).selectOption('rt')
  for(const camera of ['C1','C3','C5']){
   const available=await page.getByLabel('공간 카메라',{exact:true}).locator('option').evaluateAll(options=>options.map(option=>option.value))
   if(!available.includes(camera))continue
   await page.getByLabel('공간 카메라',{exact:true}).selectOption(camera);await page.waitForTimeout(500);await shot(item+'-'+camera)
  }
  const opacity=page.getByLabel('공간 히트맵 투명도',{exact:true});await opacity.press('Home')
  for(let step=0;step<7;step++)await opacity.press('ArrowRight')
  await shot(item+'-opacity')
  result.measurements.push({item,...await page.evaluate(()=>({asgi_fetch_browser_ms:Reflect.get(window,'__spatialApiMs')??null,canvas_draw_ms:Reflect.get(window,'__spatialRenderMs')??null,heap_bytes:performance.memory?.usedJSHeapSize??null}))})
 }
 await page.goto(base+'/#/chat');await page.getByRole('button',{name:'선택 부위 공간 근거 조회'}).click()
 const evidence=page.getByRole('button',{name:'공간 검사 근거 열기'}).first()
 await evidence.waitFor({timeout:10000});await shot('actual-tool-answer')
 await evidence.click();await page.locator('[aria-label="세부 공간 히트맵"]').scrollIntoViewIfNeeded();await page.waitForTimeout(600);await shot('tool-to-spatial-gui')
 result.state=result.errors.length?'FAILED':'CAPTURED_REQUIRES_HUMAN_VISUAL_REVIEW'
}catch(error){result.errors.push(String(error))}
finally{if(browser)await browser.close();await writeFile(path.join(out,'validation.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result,null,2))}
if(result.state==='BLOCKED'||result.state==='FAILED')process.exitCode=1
