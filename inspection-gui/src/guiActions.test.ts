import {it,expect,vi} from 'vitest'
import {validateGuiAction,executeGuiAction,type GuiPorts} from './guiActions'
it('accepts only registered commands and supported current context',()=>{
 expect(validateGuiAction({type:'select_category',category:'usb'},['usb'],[])).toEqual({type:'select_category',category:'usb'})
 for(const invalid of [{type:'eval',code:'alert(1)'},{type:'navigate',page:'https://attacker'},{type:'select_category',category:'invented'},{type:'select_camera',camera:'C9'},{type:'highlight_region',region_id:'imagined'},{type:'rotate_camera',pose:'top',js:'malicious'},null])expect(()=>validateGuiAction(invalid,['usb'],['body'])).toThrow()
})
it('dispatches through explicit ports only',()=>{
 const ports:GuiPorts={category:vi.fn(),product:vi.fn(),camera:vi.fn(),region:vi.fn(),pose:vi.fn(),metric:vi.fn(),page:vi.fn()}
 executeGuiAction(validateGuiAction({type:'rotate_camera',pose:'top'},[],[]),ports)
 expect(ports.pose).toHaveBeenCalledWith('top');expect(ports.product).not.toHaveBeenCalled()
})
it('accepts registered spatial references and rejects arbitrary paths/code',()=>{
 const action={type:'spatial_focus',grid_id:'a'.repeat(24),model:'rt',method:'gaussian'}
 expect(validateGuiAction(action,[],[])).toEqual(action)
 for(const invalid of [{...action,grid_id:'../../secrets'},{...action,model:'javascript'},{...action,method:'eval()'},{...action,sql:'select *'}])expect(()=>validateGuiAction(invalid,[],[])).toThrow()
})
