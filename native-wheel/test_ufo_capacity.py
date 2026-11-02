"""Native server-capacity roster, first NPC handoff and upper-slot effects."""
from ufo_native_encounter import *
cases=0
for v in range(6):
    for capacity in (10,64,65,100,127):
        for local in (0,7):
            s=w.setup(v,8,capacity=capacity,local=local);init_native(s,v)
            w.packets.clear();owner(v,8,1)
            assert t.get(s['ag']+0xd0,'<B')==8,('first UFO turn must precede next packet',v,capacity,local)
            high=t.alloc(0x200);t.put(high+0x68,'<q',1000)
            t.put(high+0x114,'<i',500);t.put(high+0x118,'<i',120)
            t.put(s['array']+0x18+(capacity-1)*8,'<Q',high)
            w.call_address(B+flight_start[v],t.ENV,high,500,120)
            owner(v,local,2)
            w.receive(v,-115,struct.pack('>iBQHBBhh',2,local,900002,173,28,13,240,350))
            w.settle(v)
            assert t.get(s['ag']+0xd0,'<B')==8 and not w.packets
            finish_flight(dict(s,boss=high),v);w.pulse(v)
            assert t.get(s['ag']+0xd0,'<B')==local
            settle_local(s,v);w.settle(v)
            assert w.packets==[w.expected(0)],('normal shot after native capacity handoff',v,capacity,local,w.packets)
            # The high actor's native flight wait must also honor capacities
            # above64. The timed JVM boundary models completion on its thread.
            w.call_address(B+flight_start[v],t.ENV,high,500,120)
            w.watched=high+0x14e;w.clear_after=3;w.timed.clear()
            w.call('AGTurnAwait',t.ENV,t.alloc(0x20),v,3,capacity-1)
            assert len(w.timed)==3 and t.get(high+0x14e,'<B')==0
            cases+=1
print('PASS:',cases,'native capacity and first-UFO sequences;10/64/65/100/127 slots, local0/7, upper-slot flight, normal shot and native wait')
