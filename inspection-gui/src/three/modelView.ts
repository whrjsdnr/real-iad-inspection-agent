import {PRODUCT_TEMPLATES} from './catalog'
/** Display angles for template legibility; never a calibration or C1–C5 mapping. */
export function modelViewDirection(item:string,pose='reset'):[number,number,number]{
 if(pose==='top')return [0,.99,.05]
 if(pose==='front')return [0,.15,1]
 if(pose==='right')return [1,.15,0]
 const template=PRODUCT_TEMPLATES[item]
 if(template?.family==='connector')return template.form==='jack'?[-1,.6,.8]:[.85,.75,-1.2]
 if(template?.family==='board')return [.85,1,-1]
 if(template?.family==='brush')return [.7,.45,1.5]
 if(template?.family==='disc'||template?.family==='ring')return [.85,1.15,1]
 if(template?.family==='zipper')return [.8,1.25,1]
 return [.85,.8,1]
}
