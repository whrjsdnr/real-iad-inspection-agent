import {it,expect,vi} from 'vitest'
import * as T from 'three'
import defaults from '../../../config/surface_projection.json'
import {modelUV,sourceToModel,projectedGeometry,surfaceFieldTextures,type SurfaceFrame,type SurfaceRegion} from './surfaceProjection'
import {surfaceMaterial} from './surfaceShader'
import {applyDisplaySurface,collectRegionMeshes} from './surfaceSdk'
const bounds=new T.Box3(new T.Vector3(-1,-1,-.5),new T.Vector3(1,1,.5))
const region={region_id:'bristle',label:'head',grid_width:2,grid_height:2,values:[1,0,null,.5],
 valid_observation_counts:[20,20,0,20],coverage_mask:[1,1,0,1],sample_products:20,unknown_products:0,source_bounds:[0,0,100,100],aggregation_method:'test'} as SurfaceRegion
const frame:SurfaceFrame={...defaults,render:{...defaults.render,contour_levels:[defaults.render.contour_levels[0],defaults.render.contour_levels[1],defaults.render.contour_levels[2]]},item:'toothbrush',view:'C1',source:'ground_truth',product_id:null,split:'train',projection:{axes:['x','y'],normal_sign:1,quarter_turns:0},regions:[region]}
it('maps source coordinates round-trip for every display rotation',()=>{
 for(let turn=0;turn<4;turn++){
  const projection={...frame.projection,quarter_turns:turn},point=sourceToModel(.2,.7,bounds,projection)
  const uv=modelUV(point,bounds,projection);expect(uv[0]).toBeCloseTo(.2);expect(uv[1]).toBeCloseTo(.7)
 }
})
it('replaces tiled primitive UV with one continuous part UV and keeps original geometry',()=>{
 const left=new T.BoxGeometry(.4,.5,.2).translate(-.5,0,0),right=new T.BoxGeometry(.4,.5,.2).translate(.5,0,0)
 const original=Array.from(left.getAttribute('uv').array)
 const a=projectedGeometry(left,bounds,frame.projection,.04),b=projectedGeometry(right,bounds,frame.projection,.04)
 const mean=(g:T.BufferGeometry)=>Array.from(g.getAttribute('uv').array).filter((_,i)=>i%2===0).reduce((sum,x)=>sum+x,0)/(g.getAttribute('uv').count)
 expect(mean(a)).toBeLessThan(mean(b));expect(Array.from(left.getAttribute('uv').array)).toEqual(original)
 const whole=projectedGeometry(left,bounds,frame.projection,-1)
 expect(whole.getAttribute('position').count).toBe(left.toNonIndexed().getAttribute('position').count)
 ;[left,right,a,b,whole].forEach(g=>g.dispose())
})
it('smooths only measured samples and leaves unknown coverage transparent',()=>{
 const fields=surfaceFieldTextures(region)!;expect(fields.signal.image.data[11]).toBe(0);expect(fields.mask.image.data[8]).toBe(0)
 const body=surfaceMaterial(fields,frame,region),filaments=surfaceMaterial(fields,frame,region,true)
 expect(filaments.uniforms.uAlpha.value.x).toBe(defaults.render.bristle_min_alpha)
 expect(filaments.uniforms.uAlpha.value.x).toBeGreaterThan(body.uniforms.uAlpha.value.x)
 expect(body.fragmentShader).toContain('uCoverage');expect(body.fragmentShader).toContain('sampleValue.r/max(sampleValue.a')
 const a=vi.spyOn(fields.signal,'dispose'),b=vi.spyOn(fields.mask,'dispose');fields.dispose();expect(a).toHaveBeenCalledOnce();expect(b).toHaveBeenCalledOnce();body.dispose();filaments.dispose()
 expect(surfaceFieldTextures({...region,values:[0,0,null,0]})).toBeNull()
})
it('portable adapter attaches real surface layers, rotates with model and cleans up without altering base material',()=>{
 const root=new T.Group(),owner=new T.Group();owner.userData.region_id='bristle';root.add(owner)
 const base=new T.Mesh(new T.BoxGeometry(2,2,1),new T.MeshStandardMaterial());owner.add(base)
 const originalGeometry=base.geometry,originalMaterial=base.material
 const layer=applyDisplaySurface(root,collectRegionMeshes(root),frame)
 expect(layer.overlay.children.length).toBeGreaterThan(0);expect(layer.hotspots.length).toBeGreaterThan(0)
 const material=(layer.overlay.children[0] as T.Mesh).material as T.ShaderMaterial
 expect(material.uniforms.uField.value.image.width).toBe(2)
 layer.setOpacity(.4);expect(material.uniforms.uOpacity.value).toBe(.4)
 const positions=Array.from((layer.overlay.children[0] as T.Mesh).geometry.getAttribute('position').array)
 root.rotation.y=Math.PI/2;root.updateMatrixWorld(true)
 expect(Array.from((layer.overlay.children[0] as T.Mesh).geometry.getAttribute('position').array)).toEqual(positions)
 layer.dispose();layer.dispose();expect(root.children).not.toContain(layer.overlay);expect(base.geometry).toBe(originalGeometry);expect(base.material).toBe(originalMaterial)
 base.geometry.dispose();base.material.dispose()
})
