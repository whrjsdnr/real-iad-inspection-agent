import {describe,it,expect} from 'vitest'
import {originalPoint} from './reviewGeometry'
describe('원본 검수 좌표',()=>{
 it('contain 여백을 제외한다',()=>{
  const r={left:0,top:0,width:800,height:400}
  expect(originalPoint(400,200,r,1000,1000)).toEqual([500,500])
  expect(originalPoint(10,200,r,1000,1000)).toBeNull()
  expect(originalPoint(600,400,r,1000,1000)).toEqual([1000,1000])
 })
 it('크기가 없으면 좌표 생성 불가',()=>expect(originalPoint(0,0,{left:0,top:0,width:0,height:0},0,0)).toBeNull())
})
