import type {StatsRow} from '../types'
import type {SurfaceMode} from './scenePreferences'
import {rateToColor} from '../utils/heat'
/** Uniform region statistic only. No invented spatial hotspots or score scaling. */
export function heatAppearance(row:StatsRow|undefined,mode:SurfaceMode,intensity:number){
 const valid=!!row&&Number.isFinite(row.den)&&row.den>0&&row.rate!==null&&Number.isFinite(row.rate)&&row.rate>=0&&row.rate<=1
 const enabled=valid&&(mode==='overlay'||mode==='heatmap')
 return {enabled,color:valid?rateToColor(row!.rate):null,opacity:enabled?(mode==='heatmap'?1:Math.max(.25,Math.min(1,Number.isFinite(intensity)?intensity:.88))):0}
}
