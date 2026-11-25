/** Socket-free integration test of Vite middleware + actual Python ASGI child. */
import {Writable} from 'node:stream'
import {writeFile} from 'node:fs/promises'
import {mvApiBridge} from '../inspection-gui/mvApiBridge.mjs'
let middleware
mvApiBridge().configureServer({middlewares:{use:fn=>{middleware=fn}}})
const call=(url,method='GET')=>new Promise((resolve,reject)=>{
 const headers={},chunks=[]
 const res=new Writable({write(chunk,encoding,callback){chunks.push(Buffer.from(chunk));callback()}})
 res.statusCode=200;res.setHeader=(key,value)=>{headers[key]=value}
 res.on('error',reject)
 res.on('finish',()=>{const bytes=Buffer.concat(chunks);resolve({status:res.statusCode,headers,bytes,body:bytes.toString()})})
 middleware({url,method},res,()=>resolve({status:'NEXT'}))
})
const checks=[]
for(const item of ['toothbrush','zipper']){
 const catalog=await call('/api/heatmaps/catalog?item='+item)
 if(catalog.status!==200||!JSON.parse(catalog.body).entries.length)throw new Error('catalog failed '+catalog.body)
 const response=await call(`/api/heatmaps/ground-truth?item=${item}&view=C1&split=train`)
 const data=JSON.parse(response.body)
 if(response.status!==200||data.values.length!==4096||data.known_products<=0)throw new Error('numeric map failed')
 const entry=JSON.parse(catalog.body).entries.find(entry=>entry.product_id&&entry.view==='C1')
 const image=await call('/api/heatmaps/evidence?id='+entry.id+'&kind=image')
 if(image.status!==200||image.bytes[0]!==255||image.bytes[1]!==216)throw new Error('actual image stream failed')
 checks.push({image_stream_bytes:image.bytes.length,url:`/api/heatmaps/ground-truth?item=${item}&view=C1&split=train`,status:response.status,
   transport:response.headers['X-MV-Transport'],known_products:data.known_products,unknown_products:data.unknown_products,
   grid:[data.grid_width,data.grid_height],distinct_values:new Set(data.values).size})
}
if((await call('/api/tools/query_error_stats')).status!=='NEXT')throw new Error('Existing API proxy was intercepted')
if((await call('/api/heatmaps/catalog','POST')).status!==405)throw new Error('Write was allowed')
const result={status:'VERIFIED_VITE_MIDDLEWARE_AND_REAL_PYTHON_READER_NO_TCP',checks,existing_proxy_untouched:true,writes_rejected:true}
await writeFile('reports/gui_validation/spatial-urgent/vite-mv-bridge-validation.json',JSON.stringify(result,null,2))
process.stdout.write(JSON.stringify(result,null,2)+'\n')
