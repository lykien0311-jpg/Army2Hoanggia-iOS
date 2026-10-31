"""Native actor construction/animation -> JAR predicates -> original shot wire.

Execute the real native player and UFO constructors and animation setters.
Graphics, allocation, Java helpers and final transport remain boundaries;
this is not an iPhone/VPS acceptance test. In particular, no real video-state
bits can be recovered from a screen recording. The regression checks the
provable JAR/native field mismatch, rather than assuming all actors are idle.
"""
import re,struct
import test_turn_wire as w
from unicorn import UC_HOOK_CODE
from unicorn.arm64_const import *

t=w.t;U=w.U;B=w.B
X=[getattr(__import__('unicorn.arm64_const',fromlist=['']),f'UC_ARM64_REG_X{i}')for i in range(31)]

def copies(pc,n=32):
    hits=[x.start()for x in re.finditer(re.escape(w.raw[pc:pc+n]),w.raw)]
    assert len(hits)==6,(hex(pc),hits)
    return hits

ctors=copies(0x593650);bossctors=copies(0x5a2ad4)
flightstarts=copies(0x59a2e8);itemstarts=copies(0x599aa0)
constructing=False;stub_calls=set();alloc_int=0

def hook(uc,pc,size,_):
    if not constructing or pc not in stub_calls:return
    if pc==alloc_int:
        n=U.reg_read(UC_ARM64_REG_X1);a=t.alloc(0x14+4*n)
        t.put(a+0x10,'<i',n);t.ret(a)
    else:t.ret(0)

U.hook_add(UC_HOOK_CODE,hook)

def native(pc,*args,extra=()):
    sp=t.STACK+0x30000
    U.reg_write(UC_ARM64_REG_SP,sp);U.reg_write(UC_ARM64_REG_LR,t.STOP)
    for i,v in enumerate(args):U.reg_write(X[i],v&((1<<64)-1))
    for i,v in enumerate(extra):t.put(sp+i*8,'<Q',v)
    U.emu_start(pc,t.STOP+4,count=400000)
    assert U.reg_read(UC_ARM64_REG_PC)==t.STOP,(hex(pc),hex(U.reg_read(UC_ARM64_REG_PC)))

cases=0
for v,m in enumerate(w.turns):
    ctor=ctors[v];bossctor=bossctors[v]
    stub_calls.clear()
    for begin,length in((ctor,2276),(bossctor,796)):
        for pc in range(begin,begin+length,4):
            word=struct.unpack_from('<I',w.raw,pc)[0]
            if word&0xfc000000==0x94000000:stub_calls.add(B+w.branch(pc))
    stub_calls.discard(B+ctor);alloc_int=B+w.branch(bossctor+0x48)
    g=t.alloc(0x400);pg=t.alloc(0x400);ag=t.alloc(0x200);canvas=t.alloc(0x200)
    arena=t.alloc(0x200);array=t.alloc(0x200);p=t.alloc(0x200);boss=t.alloc(0x200)
    room=t.alloc(0x200);proj=t.alloc(0x200)
    for address,value in[(m['arena_class'],g),(m['player_class'],pg),(m['array_class'],ag),
        (m['projectile_class'],proj),(w.notes[v]['canvas'],canvas),(w.notes[v]['room_class'],room)]:
        t.put(B+address,'<Q',value)
    # Native image/angle tables read directly by the constructor.
    images=t.alloc(0x18+32*8);angles=t.alloc(0x14+32*2)
    t.put(images+0x10,'<i',32);t.put(angles+0x10,'<i',32)
    t.put(pg+0xa0,'<Q',images);t.put(pg+0xa8,'<Q',angles)
    constructing=True
    native(B+ctor,t.ENV,p,100,2,240,350,0,2,extra=(0,0,1000))
    native(B+bossctor,t.ENV,boss,200,8,500,120,0,2,extra=(16,16000))
    constructing=False
    assert t.get(p+0x68,'<q')==1000 and t.get(boss+0x68,'<q')==16000
    assert t.get(p+0x114,'<i')==240 and t.get(p+0x118,'<i')==350
    assert t.get(boss+0x16c,'<B')==16 and t.get(boss+0x15c,'<B')==1
    # These values come from the original constructor, not an idle fixture.
    assert t.get(boss+0x166,'<B')==1
    assert t.get(boss+0x167,'<B')==0 and t.get(boss+0x14e,'<B')==0
    # The local actor must have finished gravity, as in reference Turn33.
    t.put(p+0x166,'<B',0)
    # Actual original item animation sets16a, separate from flight14e.
    native(B+itemstarts[v],t.ENV,p,3)
    assert t.get(p+0x16a,'<B')==1 and t.get(p+0x14e,'<B')==0
    t.put(g+0xe8,'<Q',arena);t.put(g+0x266,'<B',2);t.put(ag+0xa0,'<Q',array)
    t.put(ag+0xd0,'<B',2);t.put(canvas+0xb8,'<Q',arena)
    t.put(array+0x10,'<i',10);t.put(array+0x18+2*8,'<Q',p);t.put(array+0x18+8*8,'<Q',boss)
    U.mem_write(room+0x130,bytes([8,5]));t.put(t.SERVICE+0x10,'<Q',t.SESSION)
    fire=m['fire'];helper=w.branch(fire+0x1f4);service=w.branch(helper+0xd0)
    for at,kind in[(fire+0x50,'builder'),(fire+0x5c,'string'),(fire+0x6c,'append'),
        (fire+0x80,'append'),(fire+0x90,'bullet'),(helper+0x30,'variant'),
        (service+0xf0,'writer'),(service+0x16c,'short'),(service+0x258,'secondary'),(service+0x33c,'close')]:
        w.primitives[B+w.branch(at)]=kind
    w.receive(v,-115,struct.pack('>I',0x55464f01))
    for num in(81,82,83):
        U.mem_write(pg+0x1a7,bytes(2))
        ticket=987000+num
        w.receive(v,24,bytes([2])+struct.pack('>IiQ',1429485652,num,ticket))
        w.receive(v,-115,struct.pack('>iBQHBBhh',num,2,ticket,173,28,0,240,350))
        w.packets.clear();w.call('AGTurnTick',t.ENV,v)
        expected=(22,struct.pack('>BhhhBB',0,240,350,173,28,1))
        assert w.packets==[expected],('JAR permits native boss/item flags',v,num,w.packets)
        w.call('AGTurnTick',t.ENV,v);assert w.packets==[expected];cases+=1
    # Conversely, the real native flight start must defer a new shot.
    U.mem_write(pg+0x1a7,bytes(2));native(B+flightstarts[v],t.ENV,boss,510,130)
    assert t.get(boss+0x14e,'<B')==1
    w.receive(v,24,bytes([2])+struct.pack('>IiQ',1429485652,84,987084))
    w.receive(v,-115,struct.pack('>iBQHBBhh',84,2,987084,173,28,0,240,350))
    w.packets.clear();w.call('AGTurnTick',t.ENV,v);assert not w.packets
    # Controlled flight completion: do not zero unrelated native animations.
    t.put(boss+0x14e,'<B',0);w.call('AGTurnTick',t.ENV,v);assert w.packets==[expected];cases+=1

print('PASS:',cases,'native UFO/player constructor and original animation-setter -> repeated command22 cases; JAR actor predicates, exactly once, true flight deferral')
