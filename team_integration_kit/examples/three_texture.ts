/** Same renderer used by the GUI. Display approximation, not calibrated localization. */
import type {Object3D} from 'three'
import {applyDisplaySurface,collectRegionMeshes,type SurfaceFrame} from '../three_surface/surface-runtime.mjs'

export async function attachApproximateSurface(root:Object3D,apiBase:string,item:string,view:string,source:'ground_truth'|'rt'|'hvq',token?:string){
  const query=new URLSearchParams({item,view,source})
  const response=await fetch(apiBase.replace(/\/$/,'')+'/heatmaps/surface?'+query,{
    headers:token?{Authorization:'Bearer '+token}:{},signal:AbortSignal.timeout(15000),
  })
  if(!response.ok)throw new Error(`Surface API ${response.status}`)
  const frame=await response.json() as SurfaceFrame
  if(!frame.regions.length)throw new Error('No saved spatial evidence; do not substitute mock signals')
  return applyDisplaySurface(root,collectRegionMeshes(root),frame,.88)
}
