"""Compiled Apple UFO encounter regression using native command24 bodies."""
from ufo_native_encounter import *
counts=0
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
            t.put(s['counter']+0x4c,'<i',77);t.put(s['controller']+0xb0,'<B',1)
            owner(v,2,num);aim(v,num);w.packets.clear()
            for _ in range(4):w.settle(v)
            assert t.get(s['ag']+0xd0,'<B')==8,('early native handoff',v,room,num)
            assert not w.packets,('shot during UFO',v,room,num)
            assert t.get(s['counter']+0x4c,'<i')==77,'Native tail reset projectile counter too early'
            assert t.get(s['controller']+0xb0,'<B')==1
            finish_flight(s,v);w.settle(v)
            assert t.get(s['ag']+0xd0,'<B')==8 and not w.packets,('projectile still active',v)
            finish_projectile(s,v);w.pulse(v)
            assert t.get(s['ag']+0xd0,'<B')==2
            assert t.get(s['g']+0x266,'<B')==2
            assert t.get(s['counter']+0x4c,'<i')==0 and t.get(s['controller']+0xb0,'<B')==0
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
# Elapsed time must not bypass a still-active UFO effect. The controlled JVM
# wait clears the predicate only after6.4s, beyond the removed5s shortcut.
wait_cases=0
for v in range(6):
    s=w.setup(v);monitor=t.alloc(0x20)
    w.watched=s['proj']+0x118;t.put(w.watched,'<B',1)
    w.clear_after=400;w.timed.clear();w.legacy.clear();before=t.now
    w.call('AGTurnAwait',t.ENV,monitor,v,0,8)
    assert len(w.timed)==400 and t.now-before>6.39,(v,len(w.timed),t.now-before)
    wait_cases+=1
    t.put(s['room']+0x130,'<B',3);w.timed.clear();w.legacy.clear()
    w.call('AGTurnAwait',t.ENV,monitor,v,0,8)
    assert w.legacy==[(t.ENV,monitor)] and not w.timed;wait_cases+=1
print('PASS:',wait_cases,'UFO completion-over-timeout and unchanged other-room native waits')
