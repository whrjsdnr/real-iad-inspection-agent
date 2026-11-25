/** Development-only same-origin bridge; no operational CORS changes. */
export function apiProxy(target='http://127.0.0.1:8080') {
 const match=/^https?:\/\/(?:\[[\da-f:]+\]|[a-z\d.-]+)(?::(\d{1,5}))?\/?$/i.exec(target)
 if(!match||(match[1]&&(Number(match[1])<1||Number(match[1])>65535)))throw new Error('Invalid development API target')
 return {'/api':{target:target.replace(/\/$/,''),changeOrigin:true,rewrite:(path:string)=>path.replace(/^\/api(?=\/|\?|$)/,'')}}
}
