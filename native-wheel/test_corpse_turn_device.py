"""Fallen part -> real native endShoot23 -> command24 -> native camera owner.

Execute the installed corpse hook, original arena actor loop/completion gate,
Service.endShoot and turn changer/camera setter in ARM64. JVM virtual dispatch
for unrelated living actors, HUD, session send and message close are controlled.
No physical iPhone, live server or forced-turn timeout is involved.
"""
import json,struct,re
import capstone
import ufo_native_encounter as n
from unicorn import UC_HOOK_CODE
from unicorn.arm64_const import *
w=n.w;t=n.t;U=n.U;B=n.B;R=t.ROOT;raw=n.raw;X=w.X
presentation=json.loads((R/'presentation-map.json').read_text())
worlds=[p['arena_updates'][1]['entry'] for p in presentation]
vtables=[]
for h in w.report['corpse_hooks']:
    refs=[m.start()for m in re.finditer(re.escape(struct.pack('<Q',B+h['update'])),raw)]
    assert len(refs)==2
    vtables.append(B+min(refs)-0x90)
stop=0;dispatch={};current=None
for v,a in enumerate(worlds):
    dispatch[B+w.branch(a+0xb7c)]=v # virtual Player.update
    endshoot=w.branch(a+0xea0)
    w.primitives[B+w.branch(endshoot+0x6c)]=lambda:0 # Java message close

def hook(uc,pc,size,opaque):
    if pc==stop:U.emu_stop();return
    if pc in dispatch:
        v=dispatch[pc]
        if w.r(1)==current['boss']:
            return # Execute the unchanged native virtual dispatcher/vtable.
        else:t.ret() # unrelated living Player.update boundary
        return
    w.hook(uc,pc,size,opaque)
U.hook_del(w.NATIVE_HOOK);U.hook_add(UC_HOOK_CODE,hook)

def section(a,end):
    global stop
    stop=B+end
    U.emu_start(B+a,stop+4,count=2000000)
    assert U.reg_read(UC_ARM64_REG_PC)==stop,hex(U.reg_read(UC_ARM64_REG_PC))
    stop=0

def world_step(s,v):
    global current
    current=s;a=worlds[v];sp=t.STACK+0x30000;fp=sp+0x1000
    U.reg_write(UC_ARM64_REG_SP,sp);U.reg_write(UC_ARM64_REG_X29,fp)
    U.reg_write(UC_ARM64_REG_LR,t.STOP);U.reg_write(X[19],t.ENV)
    U.reg_write(X[20],B+w.turns[v]['arena_class']);t.put(fp-0x68,'<i',1)
    section(a+0xaa4,a+0xc7c)
    moving=t.get(sp+0x1bc,'<i')
    section(a+0xe38,a+0xf08)
    assert t.lockDepth==0 and t.get(t.ENV+0x10,'<Q')==0 and t.get(t.ENV+0x38,'<Q')==0
    return moving

def camera_fixture(s,v):
    change=w.report['turn_change_hooks'][v]['original'];body=w.branch(change+0x3c)
    camera_set=w.branch(body+0x2d0);camera_get=w.branch(body+0x2b8)
    camera=w.primitives[B+camera_get]()
    # Run the real camera setter, including its static mode and actor index.
    w.primitives.pop(B+camera_set,None)
    dis=capstone.Cs(capstone.CS_ARCH_ARM64,capstone.CS_MODE_ARM);dis.detail=True
    ins=list(dis.disasm(raw[camera_set+4:camera_set+12],B+camera_set+4))
    assert ins[0].mnemonic=='adrp' and ins[1].mnemonic=='add'
    cls=ins[0].operands[1].imm+ins[1].operands[2].imm
    glob=t.alloc(0x200);t.put(cls,'<Q',glob);t.put(cls+9,'<B',2)
    s.update(camera=camera,camera_global=glob)

def corpse_packet(s,v,y=320,remove=0):
    msg=t.message(struct.pack('>BhhIB',8,500,y,int(json.loads((R/'corpse-protocol-reference.json').read_text())['magic_decimal']),remove));t.put(msg+0x30,'<B',93)
    before=t.get(t.get(msg+0x20,'<Q')+0x20,'<i')
    w.call_address(B+t.maps[v]['controller'],t.ENV,t.alloc(0x20),msg)
    assert t.get(t.get(msg+0x20,'<Q')+0x20,'<i')==before

cases=0
for v in range(6):
    for room in (10,14,15):
        for typ in (17,18,19,20,21):
            s=w.setup(v,room);n.init_native(s,v);camera_fixture(s,v)
            a=s['boss'];t.put(a+0x16b,'<B',0);t.put(a+0x16c,'<B',typ)
            klass=t.alloc(0x80);t.put(klass+0x28,'<Q',vtables[v]);t.put(a,'<Q',klass)
            t.put(a+0x68,'<q',0);t.put(a+0x16f,'<B',5);t.put(a+0x159,'<B',1)
            t.put(B+w.notes[v]['canvas']+9,'<B',2);t.put(B+w.notes[v]['room_class']+9,'<B',2)
            # A real native handoff to an actor whose death arrived earlier
            # resets that actor's state5 to0. This reproduces the stale-state
            # edge without directly manufacturing the broken state0.
            n.owner(v,8,100+cases)
            assert t.get(a+0x16f,'<B')==0,'Native turn reset no longer reproduces the edge'
            assert t.get(s['camera']+0x20,'<i')==8
            corpse_packet(s,v);w.packets.clear();t.put(s['proj']+0x115,'<B',1)
            # A living actor still moving remains a real completion blocker.
            t.put(s['p']+0x166,'<B',1)
            world_step(s,v)
            assert not w.packets and t.get(s['proj']+0x115,'<B')==1
            t.put(s['p']+0x166,'<B',0)
            world_step(s,v)
            assert t.get(a+0x16f,'<B')==5,('dead part retained live state',v,room,typ)
            assert w.packets==[(23,b'')],('native endShoot withheld',v,room,typ,w.packets)
            assert t.get(s['proj']+0x115,'<B')==0
            # Keep the actual corpse hook running to the destination, then
            # further updates: it must not re-arm gravity or duplicate ACK23.
            for frame in range(24):world_step(s,v)
            assert t.get(a+0x118,'<i')==320 and t.get(a+0x166,'<B')==0
            assert w.packets==[(23,b'')]
            # Server-selected next turn, unchanged native case body, ownership
            # and camera setter all execute after the completion ACK.
            n.owner(v,2,300+cases)
            assert t.get(s['ag']+0xd0,'<B')==2
            assert t.get(s['camera']+0x20,'<i')==2
            assert t.get(s['camera_global']+0xbc,'<B')==1
            world_step(s,v)
            assert t.get(a+0x166,'<B')==0 and t.get(a+0x16f,'<B')==5
            # Stale live-flight and walking predicates cannot pin a corpse.
            t.put(a+0x14e,'<B',1);t.put(a+0x167,'<B',1)
            world_step(s,v)
            assert t.get(a+0x14e,'<B')==0 and t.get(a+0x167,'<B')==0
            assert t.get(s['camera']+0x20,'<i')==2
            # Settled corpses can receive a later sink/remove destination.
            corpse_packet(s,v,y=360,remove=1)
            for frame in range(4):world_step(s,v)
            assert t.get(a+0x118,'<i')==360 and t.get(a+0x159,'<B')==0
            assert w.packets==[(23,b'')]
            cases+=1
result=dict(passed=True,variants=6,rooms=[10,14,15],characters=[17,18,19,20,21],
    native_endshoot_and_server_turn_camera_sequences=cases,
    native_turn_reset_reproduces_dead_to_idle=True,native_completion_packet=23,
    native_camera_owner_after_server_turn=2,duplicate_completion_packets=0,
    living_moving_actor_still_blocks_completion=True,
    native_actor_field16b=0,original_virtual_dispatch_and_vtable=True,
    landed_corpses_rearm_gravity=False,synthetic_turns=0,
    physical_device_tested=False,live_requests=0)
(R/'build/corpse-turn-check.json').write_text(json.dumps(result,indent=2)+'\n')
print('PASS',result)
