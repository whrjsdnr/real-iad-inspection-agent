import original from '../../../inspect_ai_v6_precision.html?raw'
import tokens from '../styles/tokens.css?raw'

export const PRECISION_FRAME_TITLE='INSPECT AI V6 · 5시점 검사 개념 시연'
export const PRECISION_NAVIGATION='inspect-precision:navigate'
/** Source must be this one opaque-origin frame; message text never becomes code/URL. */
export function isPrecisionNavigation(event:Pick<MessageEvent,'source'|'data'>,frame:Window|null){
 const data=event.data
 return frame!==null&&event.source===frame&&data!==null&&typeof data==='object'&&Object.keys(data).sort().join(',')==='destination,type'&&data.type===PRECISION_NAVIGATION&&data.destination==='dashboard'
}

function replaceExactly(source:string,before:string,after:string){
 if(!source.includes(before))throw new Error('Precision source changed: integration boundary needs review')
 return source.replace(before,after)
}

/** Preserve teammate visuals inside a sandboxed demo; no operational API access. */
export function buildPrecisionDocument(){
 const palette=new Map<string,string>()
 for(const match of tokens.matchAll(/(--precision-color-\d+)\s*:\s*(#[\da-f]{3,8})\s*;/gi))palette.set(match[2].toLowerCase(),match[1])
 const tokenFor=(value:string)=>{const token=palette.get(value.toLowerCase());if(!token)throw new Error('Unregistered precision color');return token}
 let html=original.replace(/<style>([\s\S]*?)<\/style>/,(_tag,css:string)=>`<style>${tokens}\n${css.replace(/#[\da-f]{3,8}\b/gi,c=>`var(${tokenFor(c)})`)}</style>`)
 // Canvas color strings also resolve through the same CSS token source.
 html=html.replace(/(['"])(#[\da-f]{3,8})\1/gi,(_all,_quote:string,color:string)=>`precisionColor('${tokenFor(color)}')`)
 const csp="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:; connect-src 'none'; frame-src 'none'; base-uri 'none'; form-action 'none'"
 html=replaceExactly(html,'<meta charset="utf-8">',`<meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="${csp}">`)
 html=replaceExactly(html,"'use strict';",`'use strict';
const precisionColor=name=>getComputedStyle(document.documentElement).getPropertyValue(name).trim();
const precisionMotion=matchMedia('(prefers-reduced-motion: reduce)');
let precisionDisposed=false,precisionFrame=0,precisionPaint=0;
const precisionHostOrigin=document.referrer?new URL(document.referrer).origin:'*';
`)
 // Original prototype dashboard is never shown as an operational dashboard.
 const dashboardLine=html.split('\n').find(line=>line.startsWith('function dashboard(){'))
 if(!dashboardLine)throw new Error('Missing precision navigation boundary')
 html=replaceExactly(html,dashboardLine,`function dashboard(){if(mode!=='intro'||precisionDisposed)return;playing=false;cancelAnimationFrame(precisionFrame);window.parent.postMessage({type:'${PRECISION_NAVIGATION}',destination:'dashboard'},precisionHostOrigin);}`)
 html=replaceExactly(html,"if(t>=12)dashboard()",'if(t>=12)playing=false')
 // Replace the permanent RAF pump; paused/hidden/reduced-motion scenes stay idle.
 const tickLine=html.split('\n').find(line=>line.startsWith('function tick(now){'))
 if(!tickLine)throw new Error('Missing precision animation boundary')
 html=replaceExactly(html,tickLine,`function precisionSchedule(){if(!precisionDisposed&&!document.hidden&&playing&&!precisionMotion.matches&&!soft){cancelAnimationFrame(precisionFrame);precisionFrame=requestAnimationFrame(tick)}}
function tick(now){if(precisionDisposed||document.hidden||!playing)return;if(now-precisionPaint<1000/24){precisionSchedule();return}const dt=Math.min(.15,Math.max(0,(now-last)/1000));last=now;precisionPaint=now;t=Math.min(12,t+dt);render(t);if(t>=12){playing=false;q('pause').textContent='시연 완료'}precisionSchedule()}`)
 // User's replay/pause functions remain, with explicit scheduling on resume.
 html=replaceExactly(html,"q('replay').onclick=restart;", "q('replay').onclick=()=>{restart();precisionApplyMotion();precisionSchedule()};")
 html=replaceExactly(html,"q('pause').onclick=()=>{playing=!playing;q('pause').textContent=playing?'일시정지':'계속 재생';last=performance.now()}","q('pause').onclick=()=>{if(precisionMotion.matches)return;playing=!playing;q('pause').textContent=playing?'일시정지':'계속 재생';last=performance.now();if(playing)precisionSchedule();else cancelAnimationFrame(precisionFrame)}")
 const boot=`function precisionDispose(){if(precisionDisposed)return;precisionDisposed=true;playing=false;cancelAnimationFrame(precisionFrame);if(!soft){[flange,box,cylinder].forEach(mesh=>gl.deleteBuffer(mesh.b));gl.deleteProgram(prog);gl.getExtension('WEBGL_lose_context')?.loseContext()}}
function precisionApplyMotion(){cancelAnimationFrame(precisionFrame);if(precisionMotion.matches||soft){playing=false;t=5.2;q('pause').disabled=precisionMotion.matches||soft;q('pause').textContent=precisionMotion.matches?'모션 최소화 · 단계 선택':'CPU 모드 · 단계 선택';rendered=-1;render(t)}else{q('pause').disabled=false;q('pause').textContent=playing?'일시정지':'계속 재생'}}
precisionMotion.addEventListener('change',()=>{precisionApplyMotion();precisionSchedule()});
document.addEventListener('visibilitychange',()=>{cancelAnimationFrame(precisionFrame);last=performance.now();precisionSchedule()});
window.addEventListener('resize',()=>{if(!precisionDisposed){rendered=-1;render(t)}});
window.addEventListener('pagehide',precisionDispose,{once:true});
window.addEventListener('message',event=>{if(event.source===window.parent&&event.data?.type==='inspect-precision:dispose')precisionDispose()});
precisionApplyMotion();if(!precisionMotion.matches&&!soft){render(0);precisionSchedule()}`
 html=replaceExactly(html,'render(0);requestAnimationFrame(tick);',boot)
 // Parent provides the real CTA. The original demo skip button posts a narrow message.
 html=html.replace('인트로 건너뛰기 ›','실제 대시보드로 이동 ›')
 html=html.replace('</head>','<style>#dashboard{display:none!important}html{color-scheme:dark}body{overflow-x:hidden}main{padding-bottom:12px}footer{margin-bottom:8px}.viewport{height:clamp(390px,53vh,620px)}@media(max-width:550px){.viewport{height:430px}.controls{gap:6px}}</style></head>')
 return html
}
export const precisionDocument=buildPrecisionDocument()
