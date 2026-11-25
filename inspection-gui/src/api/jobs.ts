import { API_BASE } from '../config'
import { requestJson,HttpError } from './retry'
import type { GuiInferenceResult } from '../types'

export const ASYNC_JOBS=import.meta.env.VITE_ASYNC_JOBS==='true'
export const JOB_API_BASE=import.meta.env.VITE_JOB_API_BASE??API_BASE
export interface Job {
 id:string;state:'QUEUED'|'RUNNING'|'COMPLETED'|'FAILED'|'CANCELLED';stage:string
 updated_at:string;progress:null;result:GuiInferenceResult|null;error:string|null
}
const POINTER='inspection-gui-job-v1'
interface Pointer{base:string;key:string;id?:string}
function remember(p:Pointer){try{localStorage.setItem(POINTER,JSON.stringify(p))}catch{/* storage disabled; running request still works */}}
export function rememberedJob():Pointer|null{try{const p=JSON.parse(localStorage.getItem(POINTER)??'null') as Pointer|null;return p?.base===JOB_API_BASE?p:null}catch{return null}}
let specification:Promise<void>|null=null
export function ensureJobApi(){
 specification??=requestJson<{paths:Record<string,unknown>}>(`${JOB_API_BASE}/openapi.json`).then(spec=>{
   if(!spec.paths['/inference/jobs']||!spec.paths['/inference/job-keys/{key}'])throw new Error('이 서버에는 비동기 작업 API가 배포되지 않았습니다. 운영 재시작 없이 별도 개발 서버를 사용하세요.')
 }).catch(e=>{specification=null;throw e})
 return specification
}
export async function submitJob(form:FormData,key:string,signal?:AbortSignal){
 await ensureJobApi();remember({base:JOB_API_BASE,key})
 let job:Job
 try{
   if(form.get('mode')==='existing'){
     job=await requestJson<Job>(`${JOB_API_BASE}/inference/jobs`,{method:'POST',headers:{'Content-Type':'application/json','Idempotency-Key':key},body:JSON.stringify({item:form.get('item'),product_id:form.get('product_id'),mode:'existing',record:false}),signal})
   }else job=await requestJson<Job>(`${JOB_API_BASE}/inference/jobs`,{method:'POST',headers:{'Idempotency-Key':key},body:form,signal})
 }catch(error){
   // Uncertain POST response: look up the original key. Never invent a new job.
   if(signal?.aborted)throw error
   if(error instanceof HttpError&&![408,429,502,503,504].includes(error.status))throw error
   try{job=await requestJson<Job>(`${JOB_API_BASE}/inference/job-keys/${encodeURIComponent(key)}`,{signal})}catch{throw error}
 }
 remember({base:JOB_API_BASE,key,id:job.id});return job
}
export async function resumeJob(signal?:AbortSignal){const p=rememberedJob();if(!p)return null;await ensureJobApi();return requestJson<Job>(p.id?`${JOB_API_BASE}/inference/jobs/${encodeURIComponent(p.id)}`:`${JOB_API_BASE}/inference/job-keys/${encodeURIComponent(p.key)}`,{signal})}
export async function monitorJob(job:Job,onUpdate:(job:Job)=>void,signal?:AbortSignal):Promise<GuiInferenceResult>{
 const started=Date.now();let current=job
 for(;;){
   onUpdate(current)
   if(current.state==='COMPLETED'){if(!current.result)throw new Error('완료 결과가 없습니다');return current.result}
   if(current.state==='FAILED'||current.state==='CANCELLED')throw new Error(current.error??current.stage)
   if(Date.now()-started>10*60*1000)throw new Error('화면 대기 시간을 초과했습니다. 작업은 취소되지 않았으며 상태 재확인이 가능합니다.')
   await new Promise<void>((resolve,reject)=>{
     if(signal?.aborted){reject(signal.reason);return}
     const onAbort=()=>{clearTimeout(timer);reject(signal?.reason)}
     const timer=setTimeout(()=>{signal?.removeEventListener('abort',onAbort);resolve()},2000)
     signal?.addEventListener('abort',onAbort,{once:true})
   })
   current=await requestJson<Job>(`${JOB_API_BASE}/inference/jobs/${encodeURIComponent(current.id)}`,{signal})
 }
}
