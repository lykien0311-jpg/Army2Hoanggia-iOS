"""Execute signed-byte display paths for area IDs 0..255, all six variants.

Only number conversion changes. Raw IDs and the native join/packet methods
are preserved by the full-image restoration assertions in test_hooks.
"""
import struct,json
import test_hooks as t
from unicorn import UC_HOOK_CODE
from unicorn.arm64_const import *
U=t.U;B=t.BASE;X=t.X
zones=json.loads((t.ROOT/'zone-map.json').read_text())
stop=0;values=[]
def hook(uc,pc,size,_):
    if pc==stop:values.append(U.reg_read(X[2])&0xffffffff);uc.emu_stop()
U.hook_add(UC_HOOK_CODE,hook)
cases=0
for z in zones:
    for raw in [0,1,7,117,126,127,128,129,130,254,255]:
        for kind in ['row','title']:
            t.reset();values.clear()
            if kind=='row':
                pc=z['row_id_load'];U.reg_write(X[8],t.OBJECT)
                U.mem_write(t.OBJECT+0x1d,bytes([raw]));stop=B+pc+12
            else:
                pc=z['title_id_arg'];U.reg_write(X[22],raw if raw<128 else (raw-256)&0xffffffffffffffff)
                stop=B+pc+4
            U.emu_start(B+pc,stop+4,count=100)
            assert values==[raw],(z['variant'],kind,raw,values)
            if kind=='row':assert bytes(U.mem_read(t.OBJECT+0x1d,1))==bytes([raw])
            cases+=1
    for p in [p for p in t.R['zone_patches']if p['variant']==z['variant']and p['kind']=='waiting']:
        word=struct.unpack_from('<I',t.B,p['site'])[0];rn=(word>>5)&31;rd=word&31
        for raw in [127,128,129,255]:
            t.reset();U.reg_write(X[rn],t.OBJECT);U.mem_write(t.OBJECT+0x132,bytes([raw]))
            U.emu_start(B+p['site'],B+p['site']+4,count=1)
            assert U.reg_read(X[rd])==raw
            cases+=1
print('PASS:',cases,'area list/title/waiting-room conversions; 127,128,129 order and unchanged raw byte IDs')
