import {create} from 'zustand'
export type SurfaceMode='material'|'overlay'|'heatmap'|'spatial'|'model_spatial'|'ground_truth'|'truth_model_compare'|'surface'
export const isSpatialMode=(mode:SurfaceMode)=>mode==='spatial'||mode==='model_spatial'
interface ScenePreferences {
 mode:SurfaceMode
 intensity:number
 fullBrush:boolean
 setMode:(mode:SurfaceMode)=>void
 setIntensity:(value:number)=>void
 setFullBrush:(value:boolean)=>void
}
/** Visual-only controls. Never change scores, thresholds, filters, or API inputs. */
export const useScenePreferences=create<ScenePreferences>(set=>({
 mode:'surface',intensity:.88,fullBrush:false,
 setMode:mode=>set({mode}),
 setIntensity:value=>{if(Number.isFinite(value))set({intensity:Math.max(.25,Math.min(1,value))})},
 setFullBrush:fullBrush=>set({fullBrush}),
}))
