/** Host-only actual GUI validation. Never sends inference/review requests. */
import {chromium} from '../inspection-gui/node_modules/playwright/index.mjs'
import {mkdir,writeFile,access} from 'node:fs/promises'
import path from 'node:path'
const base=process.env.GUI_VALIDATION_URL??'http://127.0.0.1:18082'
if(!['127.0.0.1','localhost'].includes(new URL(base).hostname))throw new Error('Local development preview only')
const out=path.resolve('reports/gui_validation/spatial-urgent/screenshots',new Date().toISOString().replaceAll(':','-'))
await mkdir(out,{recursive:true})
const report={state:'BLOCKED',screenshots:[],errors:[],api:[],physical_surface_uv:'UNVERIFIED_USER_AUTHORIZED_APPROXIMATE_3D'}
let browser
try{
 const env={...process.env},libs='/tmp/pw-libs/root/usr/lib/x86_64-linux-gnu'
 try{await access(libs);env.LD_LIBRARY_PATH=[libs,env.LD_LIBRARY_PATH].filter(Boolean).join(':')}catch{/* host libraries */}
 browser=await chromium.launch({headless:true,chromiumSandbox:true,env})
 const page=await browser.newPage({viewport:{width:1700,height:1150},reducedMotion:'reduce'})
 page.on('pageerror',e=>report.errors.push(String(e)))
 await page.route('**/*',route=>['GET','HEAD','OPTIONS'].includes(route.request().method())?route.continue():route.abort('blockedbyclient'))
 page.on('response',async response=>{
  if(response.url().includes('/heatmaps/surface?')){
   try{const data=await response.json();report.api.push({url:response.url(),http:response.status(),product:data.product_id,view:data.view,source:data.source,regions:data.regions?.length,distinct_values:new Set(data.regions?.flatMap(region=>region.values)).size})}catch(e){report.errors.push(String(e))}
  }
 })
 await page.goto(base+'/#/spatial')
 const shot=async name=>{const file=path.join(out,name+'.png');await page.screenshot({path:file,fullPage:true});report.screenshots.push(file)}
 await page.getByLabel('공간 검증 품목',{exact:true}).selectOption('toothbrush')
 await page.getByRole('button',{name:'재질 보기',exact:true}).click();await page.waitForTimeout(300);await shot('01-material')
 await page.getByRole('button',{name:'부위별 집계',exact:true}).click();await page.waitForTimeout(300);await shot('02-region-color')
 await page.getByRole('button',{name:'3D 공간 히트맵',exact:true}).click()
 await page.getByLabel('3D 표면 데이터',{exact:true}).waitFor()
 const choose=async source=>{
  await Promise.all([page.waitForResponse(response=>response.url().includes('/heatmaps/surface?')&&response.url().includes('source='+source)&&response.ok()),page.getByLabel('3D 표면 데이터',{exact:true}).selectOption(source)])
  await page.waitForTimeout(500)
 }
 await choose('rt');await shot('03-rt-surface')
 const model=page.locator('canvas[data-inspection-category="toothbrush"]'),bounds=await model.boundingBox()
 if(bounds){await page.mouse.move(bounds.x+bounds.width*.5,bounds.y+bounds.height*.5);await page.mouse.down();await page.mouse.move(bounds.x+bounds.width*.7,bounds.y+bounds.height*.6,{steps:12});await page.mouse.up()}
 await page.waitForTimeout(300);await shot('04-rotated-surface')
 await choose('hvq');await shot('05-hvq-real-map')
 await choose('ground_truth');await shot('06-train-mask-surface')
 for(const camera of ['C2','C3','C4','C5']){
  await page.getByLabel('3D 표면 데이터 시점',{exact:true}).selectOption(camera);await page.waitForTimeout(700);await shot('07-'+camera)
 }
 await page.getByLabel('3D 표면 투명도',{exact:true}).fill('0.4');await shot('08-opacity')
 await page.getByLabel('공간 검증 품목',{exact:true}).selectOption('zipper');await page.waitForTimeout(700);await shot('09-zipper')
 await page.route('**/api/heatmaps/surface?**',route=>route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({detail:'validation-only transient API failure'})}))
 await page.getByLabel('3D 표면 데이터 시점',{exact:true}).selectOption('C1');await page.waitForTimeout(700);await shot('10-api-failure')
 report.state=report.errors.length?'FAILED':'CAPTURED_REQUIRES_VISUAL_REVIEW'
}catch(e){report.errors.push(String(e))}
finally{if(browser)await browser.close();await writeFile(path.join(out,'validation.json'),JSON.stringify(report,null,2));process.stdout.write(JSON.stringify({out,...report},null,2)+'\n')}
if(report.state!=='CAPTURED_REQUIRES_VISUAL_REVIEW')process.exitCode=1
