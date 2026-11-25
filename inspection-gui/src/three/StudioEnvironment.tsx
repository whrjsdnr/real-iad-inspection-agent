import {useEffect} from 'react'
import {useThree} from '@react-three/fiber'
import {PMREMGenerator} from 'three'
import {RoomEnvironment} from 'three/examples/jsm/environments/RoomEnvironment.js'

/** Local procedural studio reflections, no HDR downloads or continuous rendering. */
export function StudioEnvironment(){
 const {gl,scene,invalidate}=useThree()
 useEffect(()=>{
  const previous=scene.environment,room=new RoomEnvironment(),generator=new PMREMGenerator(gl)
  const environment=generator.fromScene(room,.05)
  scene.environment=environment.texture;invalidate();room.dispose();generator.dispose()
  return ()=>{scene.environment=previous;environment.dispose();invalidate()}
 },[gl,scene,invalidate])
 return null
}
