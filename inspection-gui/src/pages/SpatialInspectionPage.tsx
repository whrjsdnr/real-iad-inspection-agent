import {Scene} from '../three/Scene'
import {SceneControls} from '../components/SceneControls'
import {useStore} from '../store'
import {SurfaceHUD} from '../components/SurfaceHUD'
import {PRODUCT_TEMPLATES} from '../three/catalog'
/** Surface viewer uses actual cached numeric fields, never inference or reviews. */
export function SpatialInspectionPage(){
 const item=useStore(s=>s.filters.item)
 return <main className="glass space-y-3 p-4" aria-label="3D 공간 검사">
  <div className="flex flex-wrap items-center justify-between gap-3"><h1 className="text-lg font-semibold text-tx">3D 표면 검사 · {item}</h1><select className="btn" aria-label="공간 검증 품목" value={item} onChange={e=>useStore.getState().setItem(e.target.value,false)}>{Object.keys(PRODUCT_TEMPLATES).map(category=><option value={category} key={category}>{category}</option>)}</select></div>
  <SceneControls/>
  <div className="relative h-[72vh] min-h-[480px]"><Scene/><SurfaceHUD/></div>
  <p className="text-xs text-muted">드래그 회전 · 스크롤 확대 · 실제 격자 데이터의 표시용 근사 투영입니다. 실측 위치 복원은 아닙니다.</p>
 </main>
}
