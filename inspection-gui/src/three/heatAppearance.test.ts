import {it,expect,afterEach} from 'vitest'
import {heatAppearance} from './heatAppearance'
import {mappedHeatRow} from './heatEvidence'
import {useScenePreferences} from './scenePreferences'
import {useStore} from '../store'
import type {StatsRow,StatsResponse} from '../types'
const row:StatsRow={group:{part_id:'body'},num:8,den:10,rate:.8,reason:null,stat_key:'test'}
afterEach(()=>useScenePreferences.setState({mode:'overlay',intensity:.88}))
it('changes presentation opacity without changing measured values',()=>{
 const before=JSON.stringify(row)
 expect(heatAppearance(row,'material',1).enabled).toBe(false)
 expect(heatAppearance(row,'overlay',.85).opacity).toBe(.85)
 expect(heatAppearance(row,'heatmap',.25).opacity).toBe(1)
 expect(JSON.stringify(row)).toBe(before)
})
it('never substitutes a uniform region color for spatial or model-spatial modes',()=>{
 for(const mode of ['spatial','model_spatial'] as const){
  expect(heatAppearance(row,mode,.9).enabled).toBe(false)
  expect(heatAppearance(row,mode,.9).opacity).toBe(0)
 }
})
it('keeps missing samples and unverified mappings neutral in every display mode',()=>{
 const stats={mapping_verified:false,mapping_version:null,rows:[row]} as StatsResponse
 for(const mode of ['material','overlay','heatmap'] as const){
  expect(heatAppearance(mappedHeatRow(stats,'body'),mode,1).enabled).toBe(false)
  expect(heatAppearance({...row,den:0,rate:null},mode,1).enabled).toBe(false)
 }
 expect(heatAppearance({...row,num:0,rate:0},'heatmap',1).enabled).toBe(true)
 expect(heatAppearance({...row,rate:NaN},'heatmap',1).enabled).toBe(false)
})
it('keeps display controls independent of inspection filters and rejects nonfinite input',()=>{
 const filters=useStore.getState().filters
 useScenePreferences.getState().setMode('heatmap');useScenePreferences.getState().setIntensity(50)
 expect(useScenePreferences.getState().intensity).toBe(1)
 useScenePreferences.getState().setIntensity(-1);expect(useScenePreferences.getState().intensity).toBe(.25)
 useScenePreferences.getState().setIntensity(NaN);expect(useScenePreferences.getState().intensity).toBe(.25)
 expect(useStore.getState().filters).toBe(filters)
})
