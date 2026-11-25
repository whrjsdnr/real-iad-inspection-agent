/** Inspect current geometry only; UV existence is not camera calibration. */
import {build} from '../inspection-gui/node_modules/esbuild/lib/main.js'
import {createRequire} from 'node:module'
import {mkdir,writeFile} from 'node:fs/promises'
const source=`import {partsForItem} from './inspection-gui/src/three/parts';
export function audit(){return partsForItem('toothbrush').map(part=>({region_id:part.region_id,surfaces:[{id:'base',make:part.makeGeometry},...(part.details??[]).map(d=>({id:d.detail_id,make:d.makeGeometry}))].map(surface=>{const g=surface.make(),uv=g.getAttribute('uv'),p=g.getAttribute('position'),positionsByUv=new Map();if(uv)for(let i=0;i<uv.count;i++){const key=uv.getX(i).toFixed(5)+','+uv.getY(i).toFixed(5),xyz=[p.getX(i),p.getY(i),p.getZ(i)].map(n=>n.toFixed(5)).join(',');if(!positionsByUv.has(key))positionsByUv.set(key,new Set());positionsByUv.get(key).add(xyz)}const result={surface:surface.id,vertices:p.count,uv_vertices:uv?.count??0,max_distinct_positions_sharing_uv:Math.max(0,...Array.from(positionsByUv.values(),set=>set.size))};g.dispose();return result})}))}`
const result=await build({stdin:{contents:source,resolveDir:process.cwd(),loader:'ts'},bundle:true,platform:'node',format:'cjs',write:false,logLevel:'silent'})
const module={exports:{}}
new Function('require','module','exports',result.outputFiles[0].text)(createRequire(import.meta.url),module,module.exports)
const report={status:'VERIFIED_GEOMETRY_UV_ATTRIBUTES_ONLY',physical_roi_uv_registration_verified:false,
 reason:'Primitive UVs repeat across distinct filament positions; no packed image-to-surface atlas or camera calibration is registered.',regions:module.exports.audit()}
await mkdir('reports/gui_validation/spatial-urgent',{recursive:true})
await writeFile('reports/gui_validation/spatial-urgent/toothbrush-uv-audit.json',JSON.stringify(report,null,2))
process.stdout.write(JSON.stringify(report,null,2)+'\n')
