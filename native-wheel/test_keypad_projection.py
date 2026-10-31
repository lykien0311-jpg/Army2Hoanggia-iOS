"""Original N/h key geometry -> Apple viewport bridge -> visible key boundary."""
import test_device_bridge as t
from unicorn import UC_HOOK_CODE
from unicorn.arm64_const import *
import struct,math

U=t.u;B=t.MAIN;constructing=False;native_width=native_height=0;button=None
def f(i):return struct.unpack('<f',struct.pack('<I',U.reg_read(UC_ARM64_REG_S0+i)))[0]
def hook(uc,pc,size,_):
    global button
    if not constructing:return
    if pc==B+0x1f790c:t.ret(native_width)
    elif pc==B+0x1f7884:t.ret(native_height)
    elif pc==B+0x1fd62c:
        # Texture/font setup does not change the geometry registers.
        U.reg_write(UC_ARM64_REG_PC,B+0x1fd6fc)
    elif pc==B+0x1fb014:t.ret(button_object)
    elif pc==B+0x1fb0e8:
        button=(f(0),f(1),t.reg(2),t.reg(3));U.reg_write(UC_ARM64_REG_PC,t.STOP);U.emu_stop()
U.hook_add(UC_HOOK_CODE,hook)

def native_buttons(width,height):
    global constructing,native_width,native_height,button_object
    native_width=width;native_height=height
    parent=t.alloc(0x40);strings=t.alloc(0x60);button_object=t.alloc(0x80);result=[]
    t.put(parent+0x20,'<f',.5) # N/h spacing initialized before the fragment
    sp=t.STACK+0x30000
    for idx in range(8):
        U.reg_write(UC_ARM64_REG_SP,sp);U.reg_write(UC_ARM64_REG_X19,t.ENV);U.reg_write(UC_ARM64_REG_X20,strings)
        t.put(sp+0x58,'<Q',parent);t.put(sp+0x50,'<Q',parent);t.put(sp+0x30,'<Q',strings)
        t.put(sp+0x4c,'<I',idx);t.put(sp+0x3c,'<I',8)
        constructing=True;U.emu_start(B+0x1fd588,t.STOP+4,count=1000);constructing=False
        assert U.reg_read(UC_ARM64_REG_PC)==t.STOP;result.append(button)
    return result,t.get(parent+0x24,'<I')

keys=t.alloc(0x40);batch=t.alloc(0x90);matrix=t.alloc(0x20);values=t.alloc(0x60)
t.put(batch+0x20,'<Q',matrix);t.put(batch+0x85,'<B',1);t.put(matrix+0x10,'<Q',values);t.put(values+0x10,'<I',16)
cases=0
for native_width,native_height in [(240,480),(312,636),(360,780),(688,312)]:
    buttons,key_height=native_buttons(native_width,native_height)
    t.put(keys+0x28,'<I',key_height)
    for world_height in (native_height,native_height*1.2):
        for sign in(1,-1):
            m=[0.]*16;m[0]=2/native_width;m[5]=sign*2/world_height;m[10]=1;m[13]=-sign;m[15]=1
            U.mem_write(values+0x14,struct.pack('<16f',*m))
            expected=min((1-(m[5]*y+m[13]))/2 for x,y,w,h in buttons for y in(y,y+h))
            if not .1<expected<1:continue
            t.call('_AGViewportKeypad',t.ENV,keys,batch)
            actual=t.get(t.symbols['_keypadTopFraction'],'<d')
            assert abs(actual-expected)<1e-6,(native_width,native_height,key_height,actual,expected)
            cases+=1
assert cases>=8
print('PASS:',cases,'original native key geometry/projection boundary checks; actual Apple viewport callback')
