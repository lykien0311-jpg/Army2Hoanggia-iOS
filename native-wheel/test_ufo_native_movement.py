"""Real native walking -> deferred ticket/aim -> original native shot packet.

The fixture executes d0_.l(Z), rather than guessing the coordinate offsets.
Only its Java/terrain boundaries and final packet transport are mocked.
"""
import test_turn_wire as w
from unicorn import UC_HOOK_CODE
from unicorn.arm64_const import *
import struct,json
t=w.t;U=w.U;B=w.B;X=w.X;maps=json.loads((t.ROOT/'native-map.json').read_text())
walk_calls=set();walking=False
def hook(uc,pc,size,_):
    if walking and pc in walk_calls:t.ret(0)
U.hook_add(UC_HOOK_CODE,hook)
def native_call(pc,*args):
    U.reg_write(UC_ARM64_REG_SP,t.STACK+0x30000);U.reg_write(UC_ARM64_REG_LR,t.STOP)
    for i,v in enumerate(args):U.reg_write(X[i],v&((1<<64)-1))
    U.emu_start(pc,t.STOP+4,count=200000)
    assert U.reg_read(UC_ARM64_REG_PC)==t.STOP
cases=0
for v,(m,map)in enumerate(zip(w.turns,maps)):
    fire=m['fire'];helper=w.branch(fire+0x1f4);service=w.branch(helper+0xd0)
    for at,kind in [(fire+0x50,'builder'),(fire+0x5c,'string'),(fire+0x6c,'append'),(fire+0x80,'append'),(fire+0x90,'bullet'),(helper+0x30,'variant'),(service+0xf0,'writer'),(service+0x16c,'short'),(service+0x258,'secondary'),(service+0x33c,'close')]:w.primitives[B+w.branch(at)]=kind
    walk=map['walk'];walk_calls.clear()
    for pc in range(walk,walk+876,4):
        word=struct.unpack_from('<I',w.raw,pc)[0]
        if word&0xfc000000==0x94000000:walk_calls.add(B+w.branch(pc))
    g=t.alloc(0x400);pg=t.alloc(0x400);ag=t.alloc(0x200);canvas=t.alloc(0x200)
    arena=t.alloc(0x200);array=t.alloc(0x200);p=t.alloc(0x200)
    for address,value in [(m['arena_class'],g),(m['player_class'],pg),(m['array_class'],ag),(w.notes[v]['canvas'],canvas)]:t.put(B+address,'<Q',value)
    t.put(g+0xe8,'<Q',arena);t.put(ag+0xa0,'<Q',array);t.put(ag+0xd0,'<B',2)
    t.put(array+0x10,'<I',8);t.put(array+0x28,'<Q',p);t.put(t.SERVICE+0x10,'<Q',t.SESSION)
    room=t.alloc(0x200);t.put(B+w.notes[v]['room_class'],'<Q',room);U.mem_write(room+0x130,bytes([8,5]));t.put(p+0x68,'<q',1000)
    t.put(p+0x80,'<i',110);t.put(p+0x84,'<i',90)
    t.put(p+0x114,'<i',240);t.put(p+0x118,'<i',350);t.put(p+0x173,'<B',3)
    walking=True;native_call(B+walk,t.ENV,p,1);walking=False
    x=t.get(p+0x114,'<i');y=t.get(p+0x118,'<i')
    assert x==243 and y==350,(v,x,y)
    assert t.get(p+0x80,'<i')==110 and t.get(p+0x84,'<i')==90
    assert t.get(p+0x166,'<B')==1
    # Complete the movement animation before the pending shot is allowed.
    t.put(p+0x166,'<B',0);t.put(p+0x16f,'<B',0)
    w.receive(v,-115,struct.pack('>I',0x55464f01))
    for num in [31,32,33]:
        U.mem_write(pg+0x1a7,bytes(2));t.put(p+0x16f,'<B',0)
        t.put(canvas+0xb8,'<Q',0);t.put(g+0x266,'<B',7)
        ticket=987000+num
        w.receive(v,24,bytes([2])+struct.pack('>IiQ',1429485652,num,ticket))
        w.receive(v,-115,struct.pack('>iBQHBBhh',num,2,ticket,173,28,0,x,y))
        w.packets.clear();w.call('AGTurnTick',t.ENV,v);assert not w.packets
        t.put(canvas+0xb8,'<Q',arena);t.put(g+0x266,'<B',2)
        w.call('AGTurnTick',t.ENV,v)
        expected=(22,struct.pack('>BhhhBB',0,x,y,173,28,1))
        assert w.packets==[expected],(v,num,w.packets)
        w.call('AGTurnTick',t.ENV,v);assert w.packets==[expected]
        assert t.get(p+0x114,'<i')==x and t.get(p+0x118,'<i')==y
        cases+=1
print('PASS:',cases,'native-walk/deferred-first-turn/repeated-turn original command22 cases across six variants')
