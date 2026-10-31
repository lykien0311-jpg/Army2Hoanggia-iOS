"""Original wait call site -> Apple predicate bridge, with lost-notify replay.

Java wait releases/reacquires a monitor in the real app. Here only that OS/JVM
boundary is mocked, so animation completion and spurious wakes are controlled.
"""
import test_turn_wire as w
from unicorn import UC_HOOK_CODE
from unicorn.arm64_const import *
import struct

t=w.t;U=w.U;B=w.B;X=w.X
legacy=[];timed=[];stop_at=0;watched=0;clear_after=3;change_scene=False;canvas=0
def hook(uc,pc,size,_):
    if pc==B+0xaaa6e8:
        legacy.append((w.r(0),w.r(1)));t.ret()
    elif pc==B+0xaaa730:
        timed.append((w.r(0),w.r(1),w.r(2)))
        assert w.r(0)==t.ENV and w.r(2)==16
        if change_scene:t.put(canvas+0xb8,'<Q',0)
        elif len(timed)>=clear_after:t.put(watched,'<B',0)
        t.ret()
    elif pc==stop_at:
        U.reg_write(UC_ARM64_REG_PC,t.STOP);U.emu_stop()
U.hook_add(UC_HOOK_CODE,hook)
def run(site,actor=3):
    global stop_at
    stop_at=B+site+4;legacy.clear();timed.clear()
    sp=t.STACK+0x30000;frame=sp+0x1000
    U.reg_write(UC_ARM64_REG_SP,sp);U.reg_write(UC_ARM64_REG_X29,frame);U.reg_write(UC_ARM64_REG_LR,t.STOP)
    U.reg_write(X[0],t.ENV);U.reg_write(X[1],monitor)
    t.put(frame-0x78,'<i',actor);t.put(sp+0x4cc,'<i',actor)
    try:U.emu_start(B+site,t.STOP+4,count=200000)
    except Exception:
        print('wait failure',v,hex(site),hex(U.reg_read(UC_ARM64_REG_PC)),[hex(w.r(i))for i in range(5)])
        raise
    assert U.reg_read(UC_ARM64_REG_PC)==t.STOP
    assert U.reg_read(UC_ARM64_REG_SP)==sp and U.reg_read(UC_ARM64_REG_X29)==frame

cases=0
for v,m in enumerate(w.turns):
    g=t.alloc(0x400);pg=t.alloc(0x400);ag=t.alloc(0x200);canvas=t.alloc(0x200)
    arena=t.alloc(0x200);array=t.alloc(0x200);p=t.alloc(0x200);room=t.alloc(0x200);proj=t.alloc(0x200);monitor=t.alloc(0x20)
    for address,value in [(m['arena_class'],g),(m['player_class'],pg),(m['array_class'],ag),(m['projectile_class'],proj),(w.notes[v]['canvas'],canvas),(w.notes[v]['room_class'],room)]:t.put(B+address,'<Q',value)
    t.put(g+0xe8,'<Q',arena);t.put(canvas+0xb8,'<Q',arena);t.put(ag+0xa0,'<Q',array)
    t.put(array+0x10,'<i',8);t.put(array+0x18+3*8,'<Q',p);U.mem_write(room+0x130,bytes([8,5]))
    t.put(t.SERVICE+0x10,'<Q',t.SESSION)
    for wait in m['waits']:
        site=wait['site'];kind=wait['kind'];watched={0:proj+0x118,1:canvas+0x13c,2:p+0x166,3:p+0x16a}[kind]
        new=bytes(U.mem_read(B+site,4))
        # The old IPA performs Object.wait() even after completion. Replaying
        # that instruction records the otherwise indefinite monitor wait.
        U.mem_write(B+site,w.raw[site:site+4]);U.ctl_remove_cache(B+site,B+site+4);t.put(watched,'<B',0);run(site)
        assert legacy==[(t.ENV,monitor)] and not timed
        U.mem_write(B+site,new);U.ctl_remove_cache(B+site,B+site+4);run(site);assert not legacy and not timed,(v,kind,legacy,timed);cases+=1
        # A busy animation stays pending through two spurious timed wakes.
        t.put(watched,'<B',1);clear_after=3;run(site)
        assert not legacy and timed==[(t.ENV,monitor,16)]*3;cases+=1
        # Leaving the arena releases the queue without waiting for old flags.
        change_scene=True;t.put(watched,'<B',1);run(site)
        assert not legacy and timed==[(t.ENV,monitor,16)];cases+=1
        change_scene=False;t.put(canvas+0xb8,'<Q',arena);t.put(watched,'<B',0)
        t.put(canvas+0xb8,'<Q',0);run(site);assert not legacy and not timed;cases+=1
        t.put(canvas+0xb8,'<Q',arena)
        # Other rooms retain their original Java wait dispatch.
        t.put(room+0x130,'<B',3);run(site);assert legacy==[(t.ENV,monitor)] and not timed;cases+=1
        t.put(room+0x130,'<B',8)
print('PASS:',cases,'Apple ARM64 native-monitor predicate/lost-notify/spurious-wake/scene/other-room checks across six variants')
