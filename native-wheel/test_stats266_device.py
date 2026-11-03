"""Late network replies must update the already-open native equipment screen.

The message constructor, paint entry and equipment calculator execute in ARM64.
The screenshot numbers are an output fixture, not fabricated account gear data.
"""
import json,struct
import test_stats_device as k
from test_stats265 import snapwire,gemwire
t=k.t;w=k.w;U=k.U;B=k.B;R=k.R
maps=json.loads((R/'stats-map.json').read_text())
observed=[51679,3337,22680,22898,22631]
correct=[168048,4585,22680,22898,22631]
checks=0
def paint(v,screen):
    a=maps[v].get('paint',maps[v]['calculate']-0x1810)
    k.execute(B+a,t.ENV,screen,t.alloc(0x20),extra=[B+a+4],stack_delta=-96)
def receive(v,payload):
    msg=t.message(payload);t.put(msg+0x30,'<B',132);a=w.report['hooks'][v]['controller']
    assert k.execute(B+a,t.ENV,t.alloc(0x20),msg,extra=[B+a+4])==t.STOP
def construct(v,payload,command=-124):
    array=t.alloc(0x14+len(payload));t.put(array+0x10,'<i',len(payload));U.mem_write(array+0x14,payload)
    msg=t.alloc(0x40);a=json.loads((R/'native-map.json').read_text())[v]['ctor']+0x8c
    k.execute(B+a,t.ENV,msg,command,array)
    stream=t.get(msg+0x20,'<Q');assert t.get(stream+0x18,'<i')==len(payload)and t.get(stream+0x20,'<i')==0
w.primitives[B+0xa616c8]=lambda:t.alloc(0x30)
w.primitives[B+0xa63cfc]=lambda:t.alloc(0x30)
w.primitives[B+0xaaa258]=lambda:None
def byte_array():
    length=w.r(1);p=t.alloc(0x14+length);t.put(p+0x10,'<i',length);return p
w.primitives[B+0x12e7c08]=byte_array
for v in range(6):
    for early in [False,True]:
        k.v=v;k.c=0;t.put(t.SERVICE+0x10,'<Q',t.SESSION+0x5000+v*0x100+int(early)*16)
        screen,out,p,f,pct,guarded=k.set_inputs(v,0,False)
        slots=t.get(t.get(k.player+0x78,'<Q')+0x10,'<Q');handles=[]
        for i in range(5):
            gear=t.get(slots+0x18+i*8,'<Q')
            if gear:t.put(gear+0x80,'<q',54);t.put(gear+0xb0,'<i',65536+i);handles.append(65536+i)
        for i,n in enumerate(observed):t.put(out+0x18+i*8,'<q',n)
        packet=snapwire(0,p,handles,f,pct,correct)
        (construct if early else receive)(v,packet)
        # No user selection or extra calculate() call between reply and paint.
        assert list(struct.unpack('<5q',U.mem_read(out+0x18,40)))==observed
        paint(v,screen)
        actual=list(struct.unpack('<5q',U.mem_read(out+0x18,40)))
        assert actual==correct,('stale native UI after reply',v,early,actual,correct)
        # An unsaved gear change must reject the old snapshot on the next frame.
        gear=t.get(slots+0x18,'<Q');fa=t.get(gear+0x48,'<Q');old=t.get(fa+0x18,'<q');t.put(fa+0x18,'<q',old+1)
        sentinel=[111,222,333,444,555]
        for i,n in enumerate(sentinel):t.put(out+0x18+i*8,'<q',n)
        paint(v,screen);assert list(struct.unpack('<5q',U.mem_read(out+0x18,40)))==sentinel
        checks+=3
    # GEM1-only servers also refresh an open screen; exercise the actual
    # costume selection in both the original calculator and C paint refresh.
    for hero in [0,4,9]:
        k.v=v;k.c=hero;t.put(t.SERVICE+0x10,'<Q',t.SESSION+0x8000+v*0x100+hero)
        screen,out,p,f,pct,_=k.set_inputs(v,hero,hero==4)
        k.calculate(v,screen,out)
        rules=k.fixture(v+hero+1);construct(v,gemwire(rules,[[0]*5 for _ in range(6)]),-110)
        paint(v,screen)
        actual=list(struct.unpack('<5q',U.mem_read(out+0x18,40)))
        assert actual==k.expected(rules,hero,p,f,pct),(v,hero,actual,k.expected(rules,hero,p,f,pct))
        checks+=1
report=dict(passed=True,variants=6,late_reply_and_early_constructor_checks=checks,screenshot_values=correct,
            original_message_constructor=True,original_paint_entry=True,no_manual_recalculate=True,
            screenshot_account_gear_reproduced=False,physical_device_tested=False,live_requests=0)
(R/'build/stats266-device-check.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS',report)
