/** Retry only transient transport/server failures. POST must carry an idempotency key. */
export class HttpError extends Error {
  constructor(public status:number,message:string,public retryAfter:string|null=null){super(message)}
}
export const RETRY_POLICY={attempts:4,initialMs:400,maxDelayMs:5000,deadlineMs:20000,requestMs:8000}
const retryable=new Set([408,429,502,503,504])
export function retryDelay(attempt:number,retryAfter:string|null,random=Math.random,now=Date.now()){
  const seconds=retryAfter===null?NaN:Number(retryAfter)
  const server=retryAfter===null?0:Number.isFinite(seconds)?Math.max(0,seconds*1000):Math.max(0,Date.parse(retryAfter)-now)
  const backoff=Math.min(RETRY_POLICY.maxDelayMs,RETRY_POLICY.initialMs*2**attempt)*(.5+random()*.5)
  return Math.max(Number.isFinite(server)?server:0,backoff)
}
export async function requestJson<T>(url:string,init:RequestInit={},deps:{fetch?:typeof fetch;sleep?:(ms:number)=>Promise<void>;now?:()=>number;random?:()=>number}={}):Promise<T>{
  const send=deps.fetch??fetch,clock=deps.now??Date.now,start=clock()
  const sleep=deps.sleep??(ms=>new Promise<void>((resolve,reject)=>{
    if(init.signal?.aborted){reject(init.signal.reason);return}
    const abort=()=>{clearTimeout(timer);reject(init.signal?.reason)}
    const timer=setTimeout(()=>{init.signal?.removeEventListener('abort',abort);resolve()},ms)
    init.signal?.addEventListener('abort',abort,{once:true})
  }))
  const canRetry=(init.method??'GET').toUpperCase()==='GET'||new Headers(init.headers).has('Idempotency-Key')
  for(let attempt=0;attempt<RETRY_POLICY.attempts;attempt++){
    if(init.signal?.aborted)throw init.signal.reason
    const remaining=RETRY_POLICY.deadlineMs-(clock()-start)
    if(remaining<=0)throw new Error('서버 상태 확인 시간 초과. 기존 작업 ID로 다시 확인하세요.')
    try{
      const timeout=AbortSignal.timeout(Math.min(RETRY_POLICY.requestMs,remaining))
      const res=await send(url,{...init,signal:init.signal?AbortSignal.any([init.signal,timeout]):timeout})
      if(!res.ok){const message=await res.text();throw new HttpError(res.status,message.slice(0,240),res.headers.get('Retry-After'))}
      return await res.json() as T
    }catch(error){
      if(init.signal?.aborted)throw init.signal.reason
      const transient=error instanceof HttpError?retryable.has(error.status):error instanceof TypeError||(error instanceof DOMException&&['TimeoutError','AbortError'].includes(error.name))
      if(!canRetry||!transient||attempt===RETRY_POLICY.attempts-1)throw error
      const delay=retryDelay(attempt,error instanceof HttpError?error.retryAfter:null,deps.random,clock())
      if(clock()-start+delay>=RETRY_POLICY.deadlineMs)throw error
      await sleep(delay)
    }
  }
  throw new Error('Retry limit reached')
}
