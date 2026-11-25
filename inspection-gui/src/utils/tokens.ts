import source from '../styles/tokens.css?raw'
/** Single source for CSS and three.js tokens; also works in Node tests. */
export function cssVar(name:string,fallback=''):string {
  if(typeof document!=='undefined'&&typeof getComputedStyle!=='undefined'){
    const value=getComputedStyle(document.querySelector('[data-inspection-theme]')??document.documentElement).getPropertyValue(name).trim()
    if(value)return value
  }
  const line=source.split('\n').find(row=>row.trim().startsWith(`${name}:`))
  return line?.slice(line.indexOf(':')+1).split(';')[0].trim()??fallback
}
export function tokenRgb(name:string):[number,number,number]{
 const color=cssVar(name).replace('#','')
 if(!/^[\da-f]{6}$/i.test(color))throw new Error(`Expected RGB hex token: ${name}`)
 return [parseInt(color.slice(0,2),16),parseInt(color.slice(2,4),16),parseInt(color.slice(4,6),16)]
}
