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

def address_pair(a):
    adrp,add=struct.unpack_from('<II',n.b,a)
    assert adrp&0x9f000000==0x90000000 and add&0xff000000==0x91000000
    imm=((adrp>>5)&0x7ffff)*4+((adrp>>29)&3)
    if imm&(1<<20):imm-=1<<21
    return (a&-4096)+imm*4096+((add>>10)&4095)*(4096 if add&(1<<22) else 1)

controllers = [n.bounds(a)[0] for a in matches(0x52b780, 32)]
ticks = [a-4 for a in matches(0x511410, 64)]
spins = [a-0x7c for a in matches(0x503d08, 24)]
clock = [0x5e21f8,0x6c6f84,0x7abc48,0x89090c,0x9755d0,0xa5a294]
services = [0x5010d4,0x5ef70c,0x6d43d0,0x7b9094,0x89dd58,0x982a1c]
homes=[n.bounds(a)[0]for a in matches(0x53c0c4,12)]
home_paints=[n.bounds(a)[0]for a in matches(0x53cb84,24)]
home_selects=[a+20 for a in matches(0x53dc44,28)]
room_titles=[a+8 for a in matches(0x54e8ac,20)]
v9s=sorted(set(n.bounds(a)[0]for a in n.callers(0x5bd128)))
walks=sorted(set(n.bounds(a)[0]for a in matches(0x59be08,36)))
key_resets=sorted(set(n.bounds(a)[0]for a in matches(0x5ace14,36)))
assert len(v9s)==len(walks)==len(key_resets)==6
assert len(homes)==len(home_paints)==len(home_selects)==len(room_titles)==6
assert len(controllers)==len(ticks)==len(spins)==6
room_calls=[a+0x1998 for a in controllers]
# This call sequence also occurs in other controller branches. Anchor it to
# the exact room-list case, then verify every non-address instruction.
for a in room_calls:
    for offset in range(-0x40,0x20,4):
        w,v=struct.unpack_from('<I',n.b,0x519ba4+offset)[0],struct.unpack_from('<I',n.b,a+offset)[0]
        if w&0x7c000000!=0x14000000 and w&0x9f000000!=0x90000000:assert w==v,(hex(a),offset)
    assert n.bounds(branch(a))[0]==branch(a)
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
    maps.append(dict(clock=clock[i],controller=controllers[i],tick=ticks[i],speed=branch(ticks[i]),service=services[i],alloc=alloc,ctor=ctor,send=send,room_get=branch(room_calls[i]-0x34),room_build_call=room_calls[i],room_build=branch(room_calls[i])))
    h=homes[i];paint=home_paints[i];select=home_selects[i]
    maps[-1].update(home_build=h,home_class=address_pair(h+0x15c),width_class=address_pair(branch(paint+0xb0)+0xc))
    maps[-1].update(home_count=h+0x1b4,home_append_call=h+0x23c,home_select=select,home_select_zero=select+0x150,home_after_action=select+0x3c,room_title_site=room_titles[i])
    v9=v9s[i];calls=n.callers(walks[i]);assert len(calls)==4
    assert n.bounds(calls[0])[0]==n.bounds(calls[1])[0]
    maps[-1].update(v9=v9,v9_ctor_call=v9+0x38,command_alloc=branch(v9+0x40),command_ctor=branch(v9+0xe8),clock_alloc=branch(v9+0x348),clock_ctor=branch(v9+0x358),walk=walks[i],walk_input_calls=calls[:2],key_reset=key_resets[i])
    maps[-1]['home_widths']=[dict(site=paint+(a-0x53cb0c),reg=reg,kind=kind)for a,reg,kind in [(0x53cb98,3,'columns'),(0x53d128,8,'width'),(0x53d150,9,'negative'),(0x53d15c,10,'width'),(0x53d174,10,'width')]]
    assert n.b[maps[-1]['home_count']:maps[-1]['home_count']+4]==n.b[0x53c0c8:0x53c0cc]
    assert branch(maps[-1]['home_append_call'])==0x12e7f74
Path('native-wheel/native-map.json').write_text(json.dumps(maps,indent=2)+'\n')
fields=['service','alloc','ctor','send','room_get']
Path('native-wheel/NativeMap.h').write_text('// Generated for the guarded native Army2Hoanggia executable only.\n'
    'typedef struct { uintptr_t service, alloc, ctor, send, room_get; } AGNativeMap;\n'
    'static const AGNativeMap AGMaps[6] = {\n'+''.join('    {'+', '.join(hex(m[f]) for f in fields)+'},\n' for m in maps)+'};\n')
print('Mapped controller, room, clock and home-menu sites in all six native variants')
