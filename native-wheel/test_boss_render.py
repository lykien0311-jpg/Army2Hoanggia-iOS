"""Execute each lobby hook through the original sprite renderer to image draws.

This catches client-preview vs server-actor ID confusion: passing an integer
to a mocked renderer is insufficient. JVM image/graphics boundaries are mocked.
"""
import json,struct
import test_hooks as t
from unicorn import UC_HOOK_CODE
from unicorn.arm64_const import *
U=t.U;B=t.BASE;X=t.X
turns=json.loads((t.ROOT/'turn-map.json').read_text())
raw=(t.ROOT.parent/'validation/inspect-ipa/Army2Hoanggia').read_bytes()
def branch(a):
    w=struct.unpack_from('<I',raw,a)[0];assert w&0xfc000000==0x94000000
    n=w&0x3ffffff;return a+4*(n-(1<<26)if n&(1<<25)else n)
draws=[];primitives={};balloon=t.ENV+0xf000
def hook(uc,pc,size,_):
    if pc in [B+0x1c6150,B+0x1c6144]:
        draws.append((U.reg_read(X[2]),tuple(U.reg_read(r)for r in X[3:8])));t.returned()
    elif pc==B+0x1c61b0:t.returned(48)
    elif pc==B+0x1c6194:t.returned()
    elif pc in primitives:t.returned(balloon if primitives[pc]=='balloon'else 1)
U.hook_add(UC_HOOK_CODE,hook)
types={3:12,4:12,5:13,6:14,7:15,8:16,9:16,10:17,11:22,12:25,13:26,16:15}
cases=0
for h,turn in zip(t.R['boss_hooks'],turns):
    inner=branch(h['boss_renderer']+0x78)
    primitives[B+branch(inner+0x470)]='tick'
    primitives[B+branch(inner+0x548)]='balloon'
    g=t.ENV+0x4000;array=t.ENV+0x5000
    t.writeq(B+turn['player_class'],g);U.mem_write(B+turn['player_class']+9,b'\x02')
    images={off:t.ENV+0x7000+off for off in range(0xa8,0x178,8)}
    for off,img in images.items():t.writeq(g+off,img)
    t.writeq(g+0xa0,array);U.mem_write(array+0x10,struct.pack('<I',32))
    for i in range(32):t.writeq(array+0x18+i*8,t.ENV+0x8000+i*0x40)
    expected={12:t.ENV+0x8000+12*0x40,13:images[0x158],14:t.ENV+0x8000+14*0x40,
              15:images[0xb0],16:images[0x128],17:balloon,22:images[0x138],25:images[0x110],26:images[0x118]}
    for room,typ in [*types.items(),(14,12),(15,16),(14,25),(15,26)]:
        t.reset();t.continuation=B+h['boss_call']+4;draws.clear()
        rg=t.ENV+0x3000;t.writeq(B+h['room_class'],rg)
        U.mem_write(rg+0x130,bytes([room]));U.mem_write(rg+0x132,b'\x81')
        U.reg_write(X[2],typ if room in [14,15]else 15)
        U.reg_write(X[3],1);U.reg_write(X[4],120);U.reg_write(X[5],250);U.reg_write(X[6],2);U.reg_write(X[7],0)
        U.emu_start(B+h['boss_call'],t.STOP+4,count=10000)
        assert t.stopKind==t.continuation
        assert draws and draws[0][0]==expected[typ],(h['variant'],room,typ,draws,expected[typ])
        assert U.reg_read(UC_ARM64_REG_SP)==t.SP
        cases+=1
print('PASS:',cases,'lobby hook -> original renderer -> actual image-selection cases; UFO, ghosts, all boss types and linked stages')
