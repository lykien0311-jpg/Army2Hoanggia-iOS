"""Original N/h key geometry -> Apple viewport bridge -> visible key boundary."""
import test_device_bridge as t
from unicorn import UC_HOOK_CODE
from unicorn.arm64_const import *
import struct,math

U=t.u;B=t.MAIN;constructing=False;native_width=native_height=0;button=None;translating=False;items=[];item_index=0
def f(i):return struct.unpack('<f',struct.pack('<I',U.reg_read(UC_ARM64_REG_S0+i)))[0]
def hook(uc,pc,size,_):
    global button,item_index
    if pc==B+0xbc5b20:
        assert t.reg(1)==list_object;item_index=0;t.ret(iterator_object);return
    if pc==B+0xbc1f24:t.ret(int(item_index<len(items)));return
    if pc==B+0xbc1f78:
        value=items[item_index];item_index+=1;t.ret(value);return
    if translating:
        if pc==B+0x1f7884:t.ret(native_height)
        elif pc==B+0x1fbd28:U.reg_write(UC_ARM64_REG_PC,B+0x1fbd0c)
        elif pc==B+0x1fd9e0:U.reg_write(UC_ARM64_REG_PC,t.STOP);U.emu_stop()
        return
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
    global constructing,translating,native_width,native_height,button_object,items
    native_width=width;native_height=height;items=[]
    parent=t.alloc(0x40);strings=t.alloc(0x60);button_object=t.alloc(0x80);result=[]
    t.put(parent+0x20,'<f',.5) # N/h spacing initialized before the fragment
    sp=t.STACK+0x30000
    for idx in range(8):
        U.reg_write(UC_ARM64_REG_SP,sp);U.reg_write(UC_ARM64_REG_X19,t.ENV);U.reg_write(UC_ARM64_REG_X20,strings)
        t.put(sp+0x58,'<Q',parent);t.put(sp+0x50,'<Q',parent);t.put(sp+0x30,'<Q',strings)
        t.put(sp+0x4c,'<I',idx);t.put(sp+0x3c,'<I',8)
        constructing=True;U.emu_start(B+0x1fd588,t.STOP+4,count=1000);constructing=False
        assert U.reg_read(UC_ARM64_REG_PC)==t.STOP
        key=t.alloc(0x80);x,y,w,h=button;t.put(key+0x50,'<ffff',x,y,w,h)
        # Execute the post-construction translation the old fixture omitted.
        U.reg_write(UC_ARM64_REG_X19,t.ENV);U.reg_write(UC_ARM64_REG_X21,key);U.reg_write(UC_ARM64_REG_X22,parent)
        U.reg_write(UC_ARM64_REG_S8,struct.unpack('<I',struct.pack('<f',x))[0]);U.reg_write(UC_ARM64_REG_S9,struct.unpack('<I',struct.pack('<f',y))[0])
        translating=True;U.emu_start(B+0x1fd9b4,t.STOP+4,count=1000);translating=False
        assert U.reg_read(UC_ARM64_REG_PC)==t.STOP
        items.append(key);result.append((t.get(key+0x50,'<f'),t.get(key+0x54,'<f'),w,h))
    return result,t.get(parent+0x24,'<I')

keys=t.alloc(0x40);batch=t.alloc(0x90);matrix=t.alloc(0x20);values=t.alloc(0x60)
layout=t.alloc(0x30);list_object=t.alloc(0x30);iterator_object=t.alloc(0x30)
t.put(keys+0x20,'<Q',layout);t.put(layout+0x18,'<Q',list_object)
t.put(batch+0x20,'<Q',matrix);t.put(matrix+0x10,'<Q',values);t.put(values+0x10,'<I',16)
notes=__import__('json').load(open(t.ROOT/'notes-map.json'));canvas=t.alloc(0x200);settings=t.alloc(0x100);key_class=t.alloc(0x100);renderer=t.alloc(0x100)
t.put(B+notes[0]['canvas'],'<Q',canvas);t.put(B+0x1f71860,'<Q',settings);t.put(settings+0xc0,'<B',1)
t.put(B+0x1f75860,'<Q',key_class);t.put(key_class+0xa0,'<Q',keys)
t.put(B+0x1f73100,'<Q',renderer);t.put(renderer+0xa0,'<Q',batch)
t.call('_AGViewportWheelVisible',1)
cases=0
for native_width,native_height in [(240,480),(312,636),(360,780),(688,312)]:
    buttons,key_height=native_buttons(native_width,native_height)
    t.put(keys+0x28,'<I',key_height);t.put(canvas+0x130,'<I',native_width)
    assert min(y for x,y,w,h in buttons)>=native_height-key_height+16
    for world_height in (native_height,native_height*1.2):
        for skew in(0,.00001):
            m=[0.]*16;m[0]=2/native_width;m[1]=skew;m[5]=-2/world_height;m[10]=1;m[13]=1;m[15]=1
            U.mem_write(values+0x14,struct.pack('<16f',*m))
            expected=min((1-(m[1]*px+m[5]*py+m[13]))/2 for x,y,w,h in buttons for px in(x,x+w)for py in(y,y+h))
            assert .1<expected<1
            for route in('paint','canvas tick'):
                if route=='paint':t.call('_AGViewportKeypad',t.ENV,keys,batch)
                else:t.call('_AGViewportCapture',t.ENV,0)
                actual=t.get(t.symbols['_keypadTopFraction'],'<d')
                assert abs(actual-expected)<1e-6,(native_width,native_height,key_height,route,actual,expected)
                cases+=1
print('PASS:',cases,'native final-key translation/projection checks; paint and game-tick routes, including skew and non-drawing batch')
