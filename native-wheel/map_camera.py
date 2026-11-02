"""Derive guarded manual pan setters and camera state for all native variants."""
from pathlib import Path
import bisect,json,re,struct
import lief
from keystone import Ks,KS_ARCH_ARM64,KS_MODE_LITTLE_ENDIAN

R=Path(__file__).resolve().parent
data=(R.parent/'validation/inspect-ipa/Army2Hoanggia').read_bytes()
ks=Ks(KS_ARCH_ARM64,KS_MODE_LITTLE_ENDIAN)
def asm(s):return bytes(ks.asm(s)[0])
def pair(a):
    w,v=struct.unpack_from('<II',data,a)
    assert w&0x9f000000==0x90000000 and v&0xff000000==0x91000000
    assert w&31==v>>5&31
    imm=((w>>5)&0x7ffff)*4+((w>>29)&3)
    if imm&(1<<20):imm-=1<<21
    return (a&-4096)+imm*4096+((v>>10)&4095)
needle=asm('ldr x8,[x20]; str w19,[x8,#0xb4]; ldp x29,x30,[sp,#0x10]')
setters=[m.start()-0x2c for m in re.finditer(re.escape(needle),data)]
assert len(setters)==6
maps=[]
for x in setters:
    y=x+0x40;clazz=pair(x+0x10)
    for a,field in [(x,0xb4),(y,0xb8)]:
        assert data[a:a+16]==asm('stp x20,x19,[sp,#-32]!; stp x29,x30,[sp,#16]; add x29,sp,#16; mov w19,w1')
        assert pair(a+0x10)==clazz
        assert data[a+0x2c:a+0x40]==asm(f'ldr x8,[x20]; str w19,[x8,#{field}]; ldp x29,x30,[sp,#16]; ldp x20,x19,[sp],#32; ret')
    getter=x-0x228;update=x+0x314
    assert data[getter+0x2c:getter+0x30]==asm('ldrb w0,[x8,#0xbc]')
    assert data[update+0x54:update+0x58]==asm('ldrsb w9,[x8,#0xbc]')
    assert data[update+0x140:update+0x144]==asm('ldr w9,[x8,#0xb4]')
    maps.append(dict(pan_x=x,pan_y=y,camera_class=clazz,mode_get=getter,update=update))
(R/'camera-map.json').write_text(json.dumps(maps,indent=2)+'\n')
print('Mapped six camera variants: manual mode 0, pan deltas b4/b8, unchanged native auto-follow modes')
