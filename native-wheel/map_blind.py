"""Guard the six arena world/HUD boundaries and native Graphics layout."""
from pathlib import Path
import json,re
from keystone import Ks,KS_ARCH_ARM64,KS_MODE_LITTLE_ENDIAN
R=Path(__file__).resolve().parent
b=(R.parent/'validation/inspect-ipa/Army2Hoanggia').read_bytes()
k=Ks(KS_ARCH_ARM64,KS_MODE_LITTLE_ENDIAN)
def asm(s):return bytes(k.asm(s)[0])
needle=asm('stp x1,x2,[x29,#-0x60]; stur x2,[x29,#-0x68]; mov x1,x2')
painters=[m.start()-0x2c for m in re.finditer(re.escape(needle),b)]
assert len(painters)==6
maps=[]
for v,p in enumerate(painters):
    hud=p+0xb58
    assert b[p:p+12]==asm('stp x28,x27,[sp,#-96]!; stp x26,x25,[sp,#16]; stp x24,x23,[sp,#32]')
    assert b[p+0x1c:p+0x20]==asm('sub sp,sp,#0xf0')
    assert b[hud:hud+12]==asm('ldur x1,[x29,#-0x58]; ldrb wzr,[x1]; mov x0,x19')
    for off,word in [(0x50,'stur w9,[x29,#-0x6c]'),(0x38c,'stur w8,[x29,#-0x8c]'),(0x3a0,'stur w8,[x29,#-0x90]')]:
        assert b[p+off:p+off+4]==asm(word),(v,hex(p+off))
    maps.append(dict(variant=v,paint=p,site=p+0x34,hud=hud,hud_first_widget=p+0xca4))
for a,word in [(0xc46648,'stp s0,s2,[x1,#0x28]'),(0xc465e4,'str w2,[x8,#0x38]'),(0xc466b8,'stp w8,w9,[x1,#0x48]')]:
    assert b[a:a+4]==asm(word),hex(a)
(R/'blind-map.json').write_text(json.dumps(maps,indent=2)+'\n')
print('Guarded six arena painter/HUD boundaries and native Graphics primitive state')
