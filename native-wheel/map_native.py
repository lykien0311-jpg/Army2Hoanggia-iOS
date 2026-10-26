"""Derive all six native variants from guarded instructions in the supplied IPA."""
import sys, re, struct, json
from pathlib import Path
sys.path.insert(0, 'review')
import native as n

def matches(a, size):
    return [m.start() for m in re.finditer(re.escape(n.b[a:a+size]), n.b)]

def branch(a):
    w = struct.unpack_from('<I', n.b, a)[0]
    assert w & 0xfc000000 == 0x94000000, hex(a)
    imm = w & 0x3ffffff
    return a + 4 * (imm - (1 << 26) if imm & (1 << 25) else imm)

controllers = [n.bounds(a)[0] for a in matches(0x52b780, 32)]
ticks = [a-4 for a in matches(0x511410, 64)]
spins = [a-0x7c for a in matches(0x503d08, 24)]
clock = [0x5e21f8,0x6c6f84,0x7abc48,0x89090c,0x9755d0,0xa5a294]
services = [0x5010d4,0x5ef70c,0x6d43d0,0x7b9094,0x89dd58,0x982a1c]
assert len(controllers)==len(ticks)==len(spins)==6
maps=[]
for i in range(6):
    p=spins[i]
    # Shared runtime byte/int writers, message class layout, exact clock body.
    assert branch(p+0xdc)==0xa64a3c and branch(p+0x124)==0xa64cd4
    for o in range(0, 0x22c, 4):
        w,v=struct.unpack_from('<I', n.b, clock[0]+o)[0],struct.unpack_from('<I', n.b,clock[i]+o)[0]
        if w&0x7c000000!=0x14000000 and w&0x9f000000!=0x90000000: assert w==v
    alloc,ctor,send=branch(p+0x78),branch(p+0x94),branch(p+0x14c)
    assert n.b[ctor+0x30:ctor+0x3c]==n.b[0x4f96c4:0x4f96d0]
    assert n.b[controllers[i]:controllers[i]+4]==n.b[controllers[0]:controllers[0]+4]
    maps.append(dict(clock=clock[i],controller=controllers[i],tick=ticks[i],speed=branch(ticks[i]),service=services[i],alloc=alloc,ctor=ctor,send=send))
Path('native-wheel/native-map.json').write_text(json.dumps(maps,indent=2)+'\n')
fields=['service','alloc','ctor','send']
Path('native-wheel/NativeMap.h').write_text('// Generated for the guarded native Army2Hoanggia executable only.\n'
    'typedef struct { uintptr_t service, alloc, ctor, send; } AGNativeMap;\n'
    'static const AGNativeMap AGMaps[6] = {\n'+''.join('    {'+', '.join(hex(m[f]) for f in fields)+'},\n' for m in maps)+'};\n')
print(json.dumps([{k:hex(v)for k,v in m.items()}for m in maps],indent=2))
