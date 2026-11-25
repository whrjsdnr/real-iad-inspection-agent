/** Host-only, read-only regression against the isolated Vite development server. */
import {chromium} from '../inspection-gui/node_modules/playwright/index.mjs'
import {mkdir,writeFile,access} from 'node:fs/promises'
import path from 'node:path'
const base=process.env.GUI_VALIDATION_URL??'http://127.0.0.1:15173'
if(!['localhost','127.0.0.1'].includes(new URL(base).hostname))throw new Error('Use the isolated local development server')
const out=path.resolve('reports/gui_validation/category-overlap',new Date().toISOString().replaceAll(':','-'))
await mkdir(out,{recursive:true})
const result={state:'BLOCKED',checks:[],errors:[],screenshots:[]}
let browser
try{
 const env={...process.env},libs='/tmp/pw-libs/root/usr/lib/x86_64-linux-gnu'
 try{await access(libs);env.LD_LIBRARY_PATH=[libs,env.LD_LIBRARY_PATH].filter(Boolean).join(':')}catch{/* host libraries */}
 browser=await chromium.launch({headless:true,chromiumSandbox:true,env})
 const page=await browser.newPage({viewport:{width:1600,height:950},reducedMotion:'reduce'})
 page.on('pageerror',error=>result.errors.push(String(error)))
 await page.route('**/*',route=>{
  const request=route.request(),url=new URL(request.url())
  const readTools=['/api/tools/query_error_stats','/api/tools/compute_inspection_metrics','/api/tools/get_case_evidence','/api/tools/get_training_status']
  if(!['GET','HEAD','OPTIONS'].includes(request.method())&&!(request.method()==='POST'&&readTools.includes(url.pathname)))return route.abort('blockedbyclient')
  return route.continue()
 })
 await page.goto(base+'/#/dashboard',{waitUntil:'domcontentloaded'})
 const selector=page.getByRole('combobox').first()
 await selector.waitFor()
 await page.waitForFunction(()=>document.querySelector('canvas[data-inspection-category]'))
 const available=await selector.locator('option').evaluateAll(options=>options.map(option=>option.value).filter(Boolean))
 const categories=[...new Set(['toothbrush','sim_card_set',...available].filter(item=>available.includes(item)))]
 if(categories.length<2)throw new Error('Need at least two real category options; none will be fabricated')
 let previousCategory=null,previousOwner=null
 for(const category of [...categories,...categories.slice().reverse(),...categories.slice(0,2)]){
  await selector.selectOption(category)
  await page.waitForFunction(expected=>{
   const canvases=document.querySelectorAll('canvas[data-inspection-category]')
   if(canvases.length!==1||canvases[0].dataset.inspectionCategory!==expected)return false
   const scene=canvases[0].__inspectionScene
   if(!scene)return false
   let products=0,foreign=0
   scene.traverse(node=>{if(node.userData.inspectionProduct)products++;if(node.userData.category&&node.userData.category!==expected)foreign++})
   return products===1&&foreign===0
  },category,{timeout:15000})
  const check=await page.evaluate(()=>{
   const canvas=document.querySelector('canvas[data-inspection-category]'),categories=new Set()
   canvas.__inspectionScene.traverse(node=>{if(node.userData.category)categories.add(node.userData.category)})
   return {category:canvas.dataset.inspectionCategory,owner:canvas.dataset.rendererOwner,sceneCategories:[...categories],canvasCount:document.querySelectorAll('canvas[data-inspection-category]').length,wrapperCount:document.querySelectorAll('[data-category-scene]').length}
  })
  if(check.wrapperCount!==1)throw new Error('Multiple product scene wrappers remain')
  if(previousCategory!==null&&category!==previousCategory&&check.owner===previousOwner)throw new Error('Renderer reused across categories')
  result.checks.push(check);previousOwner=check.owner;previousCategory=category
 }
 const screenshot=path.join(out,'after-category-switches.png')
 await page.screenshot({path:screenshot,fullPage:true});result.screenshots.push(screenshot)
 result.state=result.errors.length?'FAILED':'AUTOMATED_CHECKS_PASSED_VISUAL_REVIEW_PENDING'
}catch(error){result.errors.push(String(error));result.state=result.checks.length?'FAILED':'BLOCKED'}
finally{
 if(browser)await browser.close()
 await writeFile(path.join(out,'result.json'),JSON.stringify(result,null,2))
 console.log(JSON.stringify(result,null,2))
}
if(result.errors.length)process.exitCode=1
