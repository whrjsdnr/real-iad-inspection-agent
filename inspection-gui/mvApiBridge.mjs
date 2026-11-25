/** Vite development transport only. Runs the existing read-only ASGI routes. */
import {spawn} from 'node:child_process'
import {createReadStream} from 'node:fs'
import {fileURLToPath} from 'node:url'
const root=fileURLToPath(new URL('../',import.meta.url))
const allowed=new Set(['/heatmaps/catalog','/heatmaps/ground-truth','/heatmaps/metadata','/heatmaps/evidence','/products/findings','/heatmaps/surface','/heatmaps/surface-layout','/sharing/kit'])
export function mvApiBridge(){
 return {name:'local-mv-readonly-api',configureServer(server){
  let active=0
  const waiting=[]
  const release=()=>{active--;const next=waiting.shift();if(next){active++;next()}}
  server.middlewares.use((req,res,next)=>{
   const url=new URL(req.url??'/', 'http://localhost'),path=url.pathname.replace(/^\/api(?=\/)/,'')
   if(!url.pathname.startsWith('/api/')||!allowed.has(path))return next()
   if(req.method!=='GET'){res.statusCode=405;res.end('GET only');return}
   let settled=false
   const fail=message=>{if(settled||res.writableEnded||res.destroyed)return;settled=true;res.statusCode=503;res.setHeader('Content-Type','application/json');res.end(JSON.stringify({detail:message}))}
   const run=()=>{
    if(res.writableEnded||res.destroyed){release();return}
    const child=spawn(root+'.venv/bin/python',[root+'scripts/mv_api_bridge.py'],{
     cwd:root,env:{...process.env,OMP_NUM_THREADS:'1',OPENBLAS_NUM_THREADS:'1',MKL_NUM_THREADS:'1'},stdio:['pipe','pipe','pipe']})
    let output=''
    const timer=setTimeout(()=>{child.kill();fail('Local MV API bridge timed out; inspect cache/loader')},15000)
    child.stdin.on('error',()=>fail('Cannot send request to local MV reader'))
    child.stdout.on('data',chunk=>{output+=chunk.toString();if(output.length>8*1024*1024){child.kill();fail('Local MV response limit exceeded')}})
    child.stderr.on('data',()=>{/* Do not send environment/log text into API responses. */})
    child.on('error',()=>{clearTimeout(timer);fail('Cannot start repository Python MV reader')})
    child.on('close',()=>{
     clearTimeout(timer);release();if(settled||res.writableEnded||res.destroyed)return
     try{
      const data=JSON.parse(output)
      res.statusCode=data.status;res.setHeader('Content-Type',data.content_type)
      if(data.filename)res.setHeader('Content-Disposition',`attachment; filename="${data.filename}"`)
      res.setHeader('X-MV-Transport','vite-local-existing-asgi-routes');res.setHeader('Cache-Control','private, no-store')
      settled=true
      if(data.file){const stream=createReadStream(data.file);stream.on('error',()=>res.destroy());stream.pipe(res)}
      else res.end(Buffer.from(data.body??'','base64'))
     }catch{fail('Invalid response from local MV reader')}
    })
    res.on('close',()=>{clearTimeout(timer);if(!settled)child.kill()})
    child.stdin.end(JSON.stringify({path,query:url.search.slice(1)}))
   }
   // Bound local CPU/memory even while rapidly changing camera/category filters.
   if(active<2){active++;run()}
   else if(waiting.length<16)waiting.push(run)
   else {res.setHeader('Retry-After','1');fail('Local MV reader queue is full; retry shortly')}
  })
 }}
}
