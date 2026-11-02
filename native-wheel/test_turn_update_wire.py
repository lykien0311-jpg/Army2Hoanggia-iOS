"""Installed arena update hook -> Apple pulse -> original Service shot packet.

The original update body is a controlled boundary here; actual native walking
is independently executed by test_ufo_native_movement.py.
"""
import test_turn_wire as w
from unicorn import UC_HOOK_CODE
from unicorn.arm64_const import *
import struct

t=w.t;U=w.U;B=w.B;continuation=0;first=0;g=canvas=arena=p=0
def hook(uc,pc,size,_):
    if pc!=continuation:return
    # Stand in for the original method after its displaced STP has run.
    sp=U.reg_read(UC_ARM64_REG_SP);imm=(first>>15)&127;imm=imm-128 if imm&64 else imm
    r1=first&31;r2=(first>>10)&31
    reg=lambda n:getattr(__import__('unicorn.arm64_const',fromlist=['']),f'UC_ARM64_REG_X{n}')
    U.reg_write(reg(r1),t.get(sp,'<Q'));U.reg_write(reg(r2),t.get(sp+8,'<Q'))
    U.reg_write(UC_ARM64_REG_SP,sp-imm*8)
    t.put(canvas+0xb8,'<Q',arena);t.put(g+0x266,'<B',2);t.put(p+0x166,'<B',0)
    t.ret()
U.hook_add(UC_HOOK_CODE,hook)
def update(site):
    U.reg_write(UC_ARM64_REG_SP,t.STACK+0x30000);U.reg_write(UC_ARM64_REG_LR,t.STOP)
    U.reg_write(UC_ARM64_REG_X0,t.ENV);U.reg_write(UC_ARM64_REG_X1,arena)
    U.emu_start(B+site,t.STOP+4,count=200000)
    assert U.reg_read(UC_ARM64_REG_PC)==t.STOP

cases=0
for entry in w.report['arena_update_hooks']:
    v=entry['variant'];m=w.turns[v];continuation=B+entry['site']+4;first=int.from_bytes(bytes.fromhex(entry['first']),'little')
    g=t.alloc(0x400);pg=t.alloc(0x400);ag=t.alloc(0x200);canvas=t.alloc(0x200)
    arena=t.alloc(0x200);array=t.alloc(0x200);p=t.alloc(0x200);room=t.alloc(0x200);proj=t.alloc(0x200)
    for address,value in [(m['arena_class'],g),(m['player_class'],pg),(m['array_class'],ag),(m['projectile_class'],proj),(w.notes[v]['canvas'],canvas),(w.notes[v]['room_class'],room)]:t.put(B+address,'<Q',value)
    t.put(g+0xe8,'<Q',arena);t.put(ag+0xa0,'<Q',array);t.put(ag+0xd0,'<B',2)
    t.put(array+0x10,'<I',8);t.put(array+0x28,'<Q',p);U.mem_write(room+0x130,bytes([8,5]))
    t.put(p+0x68,'<q',1000);t.put(p+0x114,'<i',240);t.put(p+0x118,'<i',350)
    t.put(t.SERVICE+0x10,'<Q',t.SESSION)
    w.receive(v,-115,struct.pack('>I',0x55464f01))
    for num in(51,52,53):
        U.mem_write(pg+0x1a7,bytes(2));t.put(canvas+0xb8,'<Q',0);t.put(g+0x266,'<B',7)
        t.put(p+0x166,'<B',1);t.put(p+0x16f,'<B',0)
        ticket=987000+num
        w.receive(v,24,bytes([2])+struct.pack('>IiQ',1429485652,num,ticket))
        w.receive(v,-115,struct.pack('>iBQHBBhh',num,2,ticket,173,28,0,240,350))
        w.packets.clear();t.put(proj+0x118,'<B',1);update(entry['site']);assert not w.packets
        t.put(proj+0x118,'<B',0);update(entry['site'])
        expected=(22,struct.pack('>BhhhBB',0,240,350,173,28,1))
        assert w.packets==[expected],(v,entry['method'],num,w.packets)
        update(entry['site']);assert w.packets==[expected]
        cases+=1
print('PASS:',cases,'installed post-arena-update -> compiled pulse -> original command22 cases, repeated turns and animation guard')
