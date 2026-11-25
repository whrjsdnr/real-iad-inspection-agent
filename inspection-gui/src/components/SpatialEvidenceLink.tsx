import {useState} from 'react'
import {openSpatialEvidence} from '../three/spatialActions'
export function SpatialEvidenceLink({gridId,model,method}:{gridId:string;model:string;method:string}){
 const [error,setError]=useState<string|null>(null)
 return <><button className="text-signal underline decoration-dotted" onClick={()=>{setError(null);void openSpatialEvidence({type:'spatial_focus',grid_id:gridId,model,method}).catch(e=>setError(String(e)))}}>공간 검사 근거 열기</button>{error&&<span role="alert" className="ml-2 text-xs text-warn">{error}</span>}</>
}
