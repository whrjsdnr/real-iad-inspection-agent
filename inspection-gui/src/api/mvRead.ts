/** Preserve route-vs-data error diagnostics; never replace real reads with fixtures. */
export class MVReadError extends Error {
 constructor(public readonly kind:'route_not_registered'|'data_not_found'|'http_error',message:string){super(message);this.name='MVReadError'}
}
export async function mvRead<T>(url:string,signal:AbortSignal,label='MV 마스크 API'):Promise<T>{
 const response=await fetch(url,{signal})
 if(!response.ok){
  const body=(await response.text()).slice(0,500)
  const routeMissing=response.status===404&&(/"detail"\s*:\s*"Not Found"/.test(body)||/Cannot GET|<!doctype html/i.test(body))
  const kind=routeMissing?'route_not_registered':response.status===404?'data_not_found':'http_error'
  const target=typeof window==='undefined'?url:new URL(url,window.location.href).href
  const guidance=routeMissing?'API 경로 미등록/프록시 대상 또는 실행 중인 서버 버전 확인':response.status===404?'등록된 품목·카메라·train 데이터 범위 확인':'저장 캐시/서버 상태 확인'
  throw new MVReadError(kind,`${label} · GET ${target} → HTTP ${response.status} · ${guidance} · 응답 ${body}`)
 }
 return await response.json() as T
}
