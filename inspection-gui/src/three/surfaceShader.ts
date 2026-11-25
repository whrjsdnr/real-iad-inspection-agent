/** Thermal-style presentation of actual measurements; no synthetic hotspots. */
import * as T from 'three'
import {cssVar} from '../utils/tokens'
import {MIN_DENOMINATOR} from '../config'
import type {SurfaceFrame,SurfaceRegion,surfaceFieldTextures} from './surfaceProjection'
import defaults from '../../../config/surface_projection.json'
export function surfaceMaterial(fields:NonNullable<ReturnType<typeof surfaceFieldTextures>>,frame:SurfaceFrame,region:SurfaceRegion,filament=false){
 const style={...defaults.render,...frame.render}
 return new T.ShaderMaterial({transparent:true,depthWrite:false,toneMapped:false,polygonOffset:true,polygonOffsetFactor:-1,polygonOffsetUnits:-1,
  uniforms:{uField:{value:fields.signal},uCoverage:{value:fields.mask},uOpacity:{value:1},
   uLow:{value:new T.Color(cssVar('--heat-ok'))},uMid:{value:new T.Color(cssVar('--heat-warn'))},uHigh:{value:new T.Color(cssVar('--heat-fail'))},
   uLevels:{value:new T.Vector3(...style.contour_levels)},uContourWidth:{value:style.contour_width},
   uFade:{value:new T.Vector2(style.fade_start,style.fade_end)},uAlpha:{value:new T.Vector2(filament?style.bristle_min_alpha:style.low_signal_alpha,style.high_signal_alpha)},
   uShape:{value:style.shape_shading},uLowSample:{value:region.sample_products<MIN_DENOMINATOR?1:0},uResolution:{value:new T.Vector2(region.grid_width,region.grid_height)}},
  vertexShader:`varying vec2 vFieldUv;varying float vShape;
   void main(){vFieldUv=uv;vec3 n=normalize(normalMatrix*normal);vShape=abs(dot(n,normalize(vec3(.25,.4,1.))));gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}`,
  fragmentShader:`uniform sampler2D uField;uniform sampler2D uCoverage;uniform float uOpacity;uniform vec3 uLow;uniform vec3 uMid;uniform vec3 uHigh;
   uniform vec3 uLevels;uniform float uContourWidth;uniform vec2 uFade;uniform vec2 uAlpha;uniform float uShape;uniform float uLowSample;uniform vec2 uResolution;
   varying vec2 vFieldUv;varying float vShape;
   void main(){
    if(texture2D(uCoverage,vFieldUv).r<.5)discard;
    vec4 sampleValue=texture2D(uField,vFieldUv);float value=clamp(sampleValue.r/max(sampleValue.a,.001),0.,1.);
    vec3 color=value<.5?mix(uLow,uMid,value*2.):mix(uMid,uHigh,(value-.5)*2.);
    float distanceToContour=min(abs(value-uLevels.x),min(abs(value-uLevels.y),abs(value-uLevels.z)));
    float contour=1.-smoothstep(uContourWidth*.3,uContourWidth,distanceToContour);
    color=mix(color,uMid,contour*.5);color*=1.-uShape+uShape*vShape;
    float alpha=mix(uAlpha.x,uAlpha.y,smoothstep(uFade.x,uFade.y,value));
    float hatch=mod(floor(vFieldUv.x*uResolution.x)+floor(vFieldUv.y*uResolution.y),4.);
    alpha*=mix(1.,mix(.6,1.,step(1.,hatch)),uLowSample);
    gl_FragColor=vec4(color,alpha*uOpacity);
    #include <colorspace_fragment>
   }`})
}
