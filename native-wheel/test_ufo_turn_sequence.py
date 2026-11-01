"""UFO -> finished effects -> original native player turn -> auto -> UFO.

Execute the shipped ARM64 turn changer, flight completion, gravity update and
projectile finalizer. Terrain/math, HUD/camera and JVM/network are controlled
boundaries. The tests do not establish physical-device acceptance.
"""
import re,struct
import ufo_sequence_harness as w
from unicorn.arm64_const import *
t=w.t;U=w.U;B=w.B;raw=w.raw

def copies(a,n=32):
    found=[m.start()for m in re.finditer(re.escape(raw[a:a+n]),raw) if m.start()>=a]
    assert len(found)==6,(hex(a),found);return found
fall=copies(0x597250,64);flight_start=copies(0x59a2e8,24)
flight_end=copies(0x59c174)
shot_end=[m.start() for m in re.finditer(re.escape(raw[0x580fdc:0x580ffc]),raw) if raw[m.start()+0x34:m.start()+0x38]==raw[0x581010:0x581014]]
assert len(shot_end)==6,shot_end
changes=w.report['turn_change_hooks'];counts=0

def init_native(s,v):
    entry=changes[v]['original'];body=w.branch(entry+0x3c)
    # The native turn changer checks its empty chat/status string before
    # updating ownership. Run its real getter; mock only the Java String literal.
    empty=t.alloc(0x20);t.put(s['g']+0x148,'<Q',empty)
    w.primitives[B+w.branch(body+0x34)]=lambda:empty
    s['empty']=empty
    hud=t.alloc(0x200);camera=t.alloc(0x200)
    w.primitives[B+w.branch(body+0x290)]=lambda:hud
    w.primitives[B+w.branch(body+0x2a4)]=lambda:w.phase_log.append(('timer',v))
    w.primitives[B+w.branch(body+0x2b8)]=lambda:camera
    w.primitives[B+w.branch(body+0x2d0)]=lambda:w.phase_log.append(('owner',v,w.r(2)))
    w.primitives[B+w.branch(body+0x22c)]=lambda:w.phase_log.append(('position',v))



def prepare_notifications(v):
    # Fixed native call sites from 580fdc..5810f0.
    for delta in (0xe8,0xf4):
        pc=shot_end[v]+delta
        assert struct.unpack_from('<I',raw,pc)[0]&0xfc000000==0x94000000
        w.primitives[B+w.branch(pc)]=lambda:0


def settle_local(s,v):
    a=fall[v];w.settle_calls.clear()
    for pc in range(a,a+964,4):
        word=struct.unpack_from('<I',raw,pc)[0]
        if word&0xfc000000==0x94000000:w.settle_calls[B+w.branch(pc)]=0
    w.settle_calls.pop(B+w.branch(a+0x248),None)
    for off,value in ((0xb4,2000),(0x160,1),(0x194,1),(0x254,2)):
        w.settle_calls[B+w.branch(a+off)]=value
    w.settling=True;w.call_address(B+a,t.ENV,s['p']);w.settling=False
    assert t.get(s['p']+0x166,'<B')==0


def finish_flight(s,v):
    a=flight_end[v];w.flight_calls.clear();vector=t.alloc(0x20)
    for pc in range(a,a+552,4):
        word=struct.unpack_from('<I',raw,pc)[0]
        if word&0xfc000000==0x94000000:w.flight_calls[B+w.branch(pc)]=0
    w.flight_calls[B+w.branch(a+0x30)]=2000 # map width
    w.flight_calls[B+w.branch(a+0xd0)]=vector # vector allocation
    w.flight_calls[B+w.branch(a+0x19c)]=120 # terrain/map height
    w.flying=True;w.call_address(B+a,t.ENV,s['boss'],8);w.flying=False
    assert t.get(s['boss']+0x14e,'<B')==0


def owner(v,who,num):
    ticket=900000+num
    w.receive(v,24,bytes([who])+struct.pack('>IiQ',1429485652,num,ticket))
    # Execute the actual installed call-site hook, including its fallback.
    w.call_address(B+changes[v]['hook'],t.ENV,who)
    return ticket

def aim(v,num):
    w.receive(v,-115,struct.pack('>iBQHBBhh',num,2,900000+num,173,28,13,240,350))

def finish_projectile(s,v):
    obj=t.alloc(0x80)
    w.call_address(B+shot_end[v],t.ENV,obj)
    assert t.get(s['proj']+0x118,'<B')==0

for v in range(6):
    for room in (8,9):
        s=w.setup(v,room);p=s['p'];init_native(s,v);prepare_notifications(v)
        w.packets.clear();w.phase_log.clear()
        # The local player remains index2 while the native current actor is8.
        owner(v,8,10);assert t.get(s['g']+0x266,'<B')==2
        assert t.get(s['ag']+0xd0,'<B')==8,(v,room,t.get(s['ag']+0xd0,'<B'),w.phase_log)
        w.settle(v);assert not w.packets;counts+=1
        for num in (11,13,15):
            # Start real native flight at the current UFO coordinates. The
            # terrain/math boundaries will let its own completion method end it.
            x=t.get(s['boss']+0x114,'<i');y=t.get(s['boss']+0x118,'<i')
            w.call_address(B+flight_start[v],t.ENV,s['boss'],x,y)
            assert t.get(s['boss']+0x14e,'<B')==1
            t.put(s['proj']+0x118,'<B',1)
            owner(v,2,num);aim(v,num);w.packets.clear()
            for _ in range(4):w.settle(v)
            assert t.get(s['ag']+0xd0,'<B')==8,('early native handoff',v,room,num)
            assert not w.packets,('shot during UFO',v,room,num)
            finish_flight(s,v);w.settle(v)
            assert t.get(s['ag']+0xd0,'<B')==8 and not w.packets,('projectile still active',v)
            finish_projectile(s,v);w.pulse(v)
            assert t.get(s['ag']+0xd0,'<B')==2
            assert t.get(s['g']+0x266,'<B')==2
            assert not w.packets
            settle_local(s,v)
            t.put(p+0x172,'<B',100)
            w.settle(v)
            assert w.packets==[(26,b'\x64'),w.expected(0)],('local POW/shot',v,room,num,w.packets)
            w.settle(v);assert len(w.packets)==2
            # The player's projectile must also finish before UFO's next turn.
            t.put(s['proj']+0x118,'<B',1);owner(v,8,num+1)
            w.settle(v);assert t.get(s['ag']+0xd0,'<B')==2
            finish_projectile(s,v);w.pulse(v)
            assert t.get(s['ag']+0xd0,'<B')==8
            w.packets.clear();counts+=1
        assert [x[2]for x in w.phase_log if x[0]=='owner']==[8,2,8,2,8,2,8]
        # Native changeTurn can return without changing ownership when a
        # status/chat string is displayed. It must stay pending, then retry.
        t.put(s['g']+0x148,'<Q',t.alloc(0x20))
        owner(v,2,21);aim(v,21);w.packets.clear();w.settle(v)
        assert t.get(s['ag']+0xd0,'<B')==8 and not w.packets
        t.put(s['g']+0x148,'<Q',s['empty']);w.pulse(v)
        assert t.get(s['ag']+0xd0,'<B')==2
        settle_local(s,v);w.settle(v)
        assert w.packets==[w.expected(0)],('postponed handoff',v,room,w.packets)
        counts+=1
print('PASS:',counts,'ARM64 encounter sequences across both UFO rooms and all six variants; real native ownership, flight/projectile completion, gravity, POW then shot, no overlapping turns')
