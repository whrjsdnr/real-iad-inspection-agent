import * as T from 'three';
export interface Projection {axes:['x'|'y'|'z','x'|'y'|'z'];normal_sign:number;quarter_turns:number}
export interface SurfaceRegion {region_id:string;label:string;grid_width:number;grid_height:number;values:(number|null)[];valid_observation_counts:number[];coverage_mask:number[];aggregation_method:string;source_bounds:[number,number,number,number];sample_products:number;unknown_products:number}
export interface SurfaceFrame {item:string;view:string;source:'ground_truth'|'rt'|'hvq';regions:SurfaceRegion[];projection:Projection;scope:'visualization_only_approximate';user_authorized_approximate_projection:boolean;version:string;[key:string]:unknown}
export interface RegionMesh {mesh:T.Mesh;region_id:string;detail_id?:string}
export function collectRegionMeshes(root:T.Object3D):RegionMesh[];
export function applyDisplaySurface(root:T.Object3D,sources:RegionMesh[],frame:SurfaceFrame,opacity?:number):{overlay:T.Group;hotspots:unknown[];setOpacity:(value:number)=>void;dispose:()=>void};
export function projectedGeometry(source:T.BufferGeometry,bounds:T.Box3,projection:Projection,minCos:number):T.BufferGeometry;
