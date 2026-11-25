/** Bundle the actual renderer kernel for reuse; Three.js remains a peer import. */
import {build} from '../inspection-gui/node_modules/esbuild/lib/main.js'
import {readFile,writeFile,mkdir,copyFile} from 'node:fs/promises'
import {resolve,dirname} from 'node:path'
const folder='team_integration_kit/three_surface';await mkdir(folder,{recursive:true})
await build({entryPoints:['inspection-gui/src/three/surfaceSdk.ts'],outfile:folder+'/surface-runtime.mjs',bundle:true,format:'esm',platform:'browser',external:['three'],define:{'import.meta.env':'{}'},logLevel:'silent',plugins:[{
 name:'existing-css-tokens',setup(builder){builder.onResolve({filter:/\?raw$/},args=>({path:resolve(dirname(args.importer),args.path.replace(/\?raw$/,'')),namespace:'source-text'}));builder.onLoad({filter:/.*/,namespace:'source-text'},async args=>({contents:'export default '+JSON.stringify(await readFile(args.path,'utf8')),loader:'js'}))}
}]})
await copyFile('inspection-gui/src/styles/tokens.css',folder+'/surface-tokens.css')
await copyFile('config/surface_projection.json',folder+'/projection-presets.json')
await writeFile(folder+'/surface-runtime.d.mts',`import * as T from 'three';
export interface Projection {axes:['x'|'y'|'z','x'|'y'|'z'];normal_sign:number;quarter_turns:number}
export interface SurfaceRegion {region_id:string;label:string;grid_width:number;grid_height:number;values:(number|null)[];valid_observation_counts:number[];coverage_mask:number[];aggregation_method:string;source_bounds:[number,number,number,number];sample_products:number;unknown_products:number}
export interface SurfaceFrame {item:string;view:string;source:'ground_truth'|'rt'|'hvq';regions:SurfaceRegion[];projection:Projection;scope:'visualization_only_approximate';user_authorized_approximate_projection:boolean;version:string;[key:string]:unknown}
export interface RegionMesh {mesh:T.Mesh;region_id:string;detail_id?:string}
export function collectRegionMeshes(root:T.Object3D):RegionMesh[];
export function applyDisplaySurface(root:T.Object3D,sources:RegionMesh[],frame:SurfaceFrame,opacity?:number):{overlay:T.Group;hotspots:unknown[];setOpacity:(value:number)=>void;dispose:()=>void};
export function projectedGeometry(source:T.BufferGeometry,bounds:T.Box3,projection:Projection,minCos:number):T.BufferGeometry;
`)
process.stdout.write('Portable ESM renderer, type declarations, tokens and projection presets exported.\n')
