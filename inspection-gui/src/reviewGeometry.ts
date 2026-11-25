/** object-contain 여백을 제외하고 화면 좌표를 원본 좌표로 변환한다. */
export function originalPoint(clientX:number,clientY:number,rect:{left:number;top:number;width:number;height:number},width:number,height:number):[number,number]|null {
 if(width<=0||height<=0||rect.width<=0||rect.height<=0)return null
 const scale=Math.min(rect.width/width,rect.height/height)
 const x=(clientX-rect.left-(rect.width-width*scale)/2)/scale
 const y=(clientY-rect.top-(rect.height-height*scale)/2)/scale
 if(x<0||y<0||x>width||y>height)return null
 return [Math.round(x),Math.round(y)]
}
