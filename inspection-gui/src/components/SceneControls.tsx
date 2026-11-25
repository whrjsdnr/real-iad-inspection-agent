import {Box,Layers,Flame} from 'lucide-react'
import {useScenePreferences} from '../three/scenePreferences'
import {useStore} from '../store'
import {SurfaceControls} from './SurfaceControls'
const MODES=[{mode:'material',label:'재질 보기',icon:Box},{mode:'heatmap',label:'부위별 집계',icon:Layers},{mode:'surface',label:'3D 공간 히트맵',icon:Flame}] as const
export function SceneControls(){
 const mode=useScenePreferences(s=>s.mode),setMode=useScenePreferences(s=>s.setMode)
 const item=useStore(s=>s.filters.item),fullBrush=useScenePreferences(s=>s.fullBrush),setFullBrush=useScenePreferences(s=>s.setFullBrush)
 return <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line bg-panel px-4 py-3" aria-label="3D 표시 설정">
  <div className="inline-flex flex-wrap gap-1 rounded-lg border border-line bg-bg p-1" role="group" aria-label="3D 표시 모드">{MODES.map(({mode:next,label,icon:Icon})=><button key={next} className={`btn ${mode===next?'btn-active':''}`} aria-pressed={mode===next} onClick={()=>setMode(next)}><Icon size={14} aria-hidden/>{label}</button>)}</div>
  {item==='toothbrush'&&<label className="flex items-center gap-2 text-xs text-muted"><input type="checkbox" checked={fullBrush} onChange={e=>setFullBrush(e.target.checked)}/>전체 외형 참고</label>}
  {mode==='surface'&&<SurfaceControls/>}
 </div>
}
