import {it,expect} from 'vitest'
import {modelViewDirection} from './modelView'
it('initial view exposes the detailed interfaces without claiming camera calibration',()=>{
 expect(modelViewDirection('usb')[2]).toBeLessThan(0)
 expect(modelViewDirection('audiojack')[0]).toBeLessThan(0)
 expect(modelViewDirection('toothbrush')[2]).toBeGreaterThan(0)
 expect(modelViewDirection('pcb')[1]).toBeGreaterThan(0)
 expect(modelViewDirection('usb','front')).toEqual([0,.15,1])
 for(const item of ['usb','toothbrush','unknown'])expect(modelViewDirection(item).every(Number.isFinite)).toBe(true)
})
