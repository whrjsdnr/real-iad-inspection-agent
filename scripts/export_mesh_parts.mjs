/** Export stable IDs from existing mesh factories, without rendering a model. */
import {build} from '../inspection-gui/node_modules/esbuild/lib/main.js'
import {createRequire} from 'node:module'
import {writeFile} from 'node:fs/promises'
const result=await build({stdin:{contents:`import {PARTS_BY_ITEM} from './inspection-gui/src/three/parts';export const parts=Object.entries(PARTS_BY_ITEM).flatMap(([item,parts])=>parts.map(part=>({item,region_id:part.region_id,part_id:part.part_id,display_name:part.label,material:part.material,detail_ids:(part.details??[]).map(d=>d.detail_id),parent_region_id:null,supported_views:[],mapping_status:'mesh_region_roi_not_registered'})));`,resolveDir:process.cwd(),loader:'ts'},bundle:true,platform:'node',format:'cjs',write:false,logLevel:'silent'})
const module={exports:{}};new Function('require','module','exports',result.outputFiles[0].text)(createRequire(import.meta.url),module,module.exports)
await writeFile('config/mesh_parts_catalog.json',JSON.stringify({version:'mesh-parts-from-source-v1',source:'inspection-gui/src/three/parts.ts',parts:module.exports.parts,physical_surface_uv_verified:false},null,2)+'\n')
process.stdout.write('Exported '+module.exports.parts.length+' stable mesh region IDs. No geometry rendering/inference.\n')
