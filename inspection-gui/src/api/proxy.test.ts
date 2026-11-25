import {it,expect} from 'vitest'
import {apiProxy} from '../../apiProxy'
it('proxies same-origin API without rewriting model/data identifiers',()=>{
 const rule=apiProxy()['/api']
 expect(rule.target).toBe('http://127.0.0.1:8080')
 expect(rule.rewrite('/api/health')).toBe('/health')
 expect(rule.rewrite('/api/tools/get_case_evidence?product_id=a%2Fb')).toBe('/tools/get_case_evidence?product_id=a%2Fb')
 expect(rule.rewrite('/apiculture')).toBe('/apiculture')
})
it('validates local-development target protocol and credentials',()=>{
 expect(apiProxy('http://127.0.0.1:18080')['/api'].target).toBe('http://127.0.0.1:18080')
 expect(()=>apiProxy('file:///tmp')).toThrow()
 expect(()=>apiProxy('http://user:secret@host')).toThrow()
})
