/** Supply the API base URL and token at runtime; never commit real credentials. */
export interface SpatialGrid {
  item:string;product_id:string;region_id:string;view:string;model:'rt'|'hvq';
  grid_width:number;grid_height:number;values:(number|null)[];values_2d:(number|null)[][];
  observation_counts:number[];coverage_mask:number[];mapping_status:string;
  mapping_version:string;source:string;rate_supported:boolean;
}
export class InspectionClient {
  constructor(private baseUrl:string,private token:string){}
  async get<T>(path:string,params:Record<string,string|number>={}):Promise<T>{
    const query=new URLSearchParams(Object.entries(params).map(([key,value])=>[key,String(value)]));
    const response=await fetch(this.baseUrl.replace(/\/$/,'')+path+'?'+query,{
      headers:{Authorization:'Bearer '+this.token},credentials:'omit',signal:AbortSignal.timeout(15000)});
    if(!response.ok)throw new Error(`Inspection API ${response.status}`);
    return await response.json() as T;
  }
  toothbrushGrid(){return this.get<SpatialGrid>('/parts/spatial-heatmap',{
    item:'toothbrush',product_id:'toothbrush/NG/CH/S0001',view:'C1',region_id:'bristle',model:'rt',resolution:32,method:'confidence_area'});}
}

export function preservedTrainMask(client:InspectionClient,item='toothbrush',view='C1'){
  return client.get('/heatmaps/ground-truth',{item,view,split:'train'});
}
