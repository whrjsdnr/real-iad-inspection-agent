/** Export actual display geometry for a software-only review. No model/API/DB access. */
import {build} from '../inspection-gui/node_modules/esbuild/lib/main.js'
import {mkdtemp,writeFile,rm} from 'node:fs/promises'
import {tmpdir} from 'node:os'
import path from 'node:path'
import {pathToFileURL} from 'node:url'
const temporary=await mkdtemp(path.join(tmpdir(),'inspection-display-mesh-'))
try{
 const partsFile=path.join(temporary,'parts.mjs'),viewsFile=path.join(temporary,'views.mjs')
 await build({entryPoints:['inspection-gui/src/three/parts.ts'],bundle:true,platform:'node',format:'esm',outfile:partsFile,logLevel:'silent'})
 await build({entryPoints:['inspection-gui/src/three/modelView.ts'],bundle:true,platform:'node',format:'esm',outfile:viewsFile,logLevel:'silent'})
 const {partsForItem,templateBounds,PARTS_BY_ITEM}=await import(pathToFileURL(partsFile).href)
 const {modelViewDirection}=await import(pathToFileURL(viewsFile).href)
 const representatives=new Set(['toothbrush','usb','pcb','bottle_cap','button_battery','zipper','terminalblock','phone_battery','sim_card_set'])
 const models=[],complexity=[]
 for(const category of Object.keys(PARTS_BY_ITEM)){
  const parts=partsForItem(category),bounds=templateBounds(parts),surfaces=[]
  let triangles=0,details=0,surfaceCount=0
  for(const part of parts){
   details+=part.details?.length??0
   for(const surface of [{material:part.material,makeGeometry:part.makeGeometry},...(part.details??[])]){
    let geometry=surface.makeGeometry();triangles+=(geometry.index?.count??geometry.getAttribute('position').count)/3;surfaceCount++
    if(representatives.has(category)){
     if(geometry.index){const copy=geometry.toNonIndexed();geometry.dispose();geometry=copy}
     surfaces.push({material:surface.material,position:part.position,vertices:Array.from(geometry.getAttribute('position').array)})
    }
    geometry.dispose()
   }
  }
  complexity.push({category,regions:parts.length,detail_surfaces:details,total_surfaces:surfaceCount,triangles})
  if(representatives.has(category))models.push({category,view:modelViewDirection(category),center:bounds.center.toArray(),size:bounds.size.toArray(),surfaces})
 }
 await writeFile(process.argv[2]??'/tmp/detailed-mesh-preview.json',JSON.stringify(models))
 await writeFile('reports/gui_validation/detail3d/geometry-complexity.json',JSON.stringify({scope:'display meshes only; not measured GPU calls or FPS',categories:complexity},null,2))
 console.log(`Exported ${models.length} previews; audited ${complexity.length} display templates`)
}finally{await rm(temporary,{recursive:true,force:true})}
