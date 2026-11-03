"""Execute GEM1 aggregation and GEM2 matching with all six equipped slots."""
import json
import test_stats_device as k
from test_stats265 import gemwire,snapwire
t=k.t;w=k.w;B=k.B;R=k.R
checks=0
def receive(v,cmd,wire):
    msg=t.message(wire);t.put(msg+0x30,'<B',cmd&255);entry=w.report['hooks'][v]['controller']
    assert k.execute(B+entry,t.ENV,t.alloc(0x20),msg,extra=[B+entry+4])==t.STOP
for v in range(6):
    k.v=v;k.c=4;k.costumeId=91
    screen,out,p,f,pct,snapshots=k.set_inputs(v,4,True)
    slots=t.get(t.get(k.player+0x78,'<Q')+0x10,'<Q');handles=[]
    for i in range(5):
        item=t.get(slots+0x18+i*8,'<Q')
        if not item:
            item=t.alloc(0xc0);t.put(item+0x48,'<Q',k.arr([0]*5));t.put(item+0x50,'<Q',k.arr([0]*5));t.put(slots+0x18+i*8,'<Q',item)
        t.put(item+0x80,'<q',54);t.put(item+0xb0,'<i',65536+i);handles.append(65536+i)
    handles.append(65541);rows=k.fixture(v+1);receive(v,-110,gemwire(rows,[[2]*5 for _ in range(6)]))
    enabled,base,step,gain=rows[4];expected=[]
    for j in range(5):
        n=p[j]+f[j];ordinary=pct[j]-12
        if j==1:value=(100+n*gain//step[j]+ordinary)*112//100*base[j]//100
        else:value=(base[j]+n*step[j])*(100+ordinary)//100*112//100
        expected.append(max(0,min(2147483647,value)))
    assert k.calculate(v,screen,out)==expected,(v,k.calculate(v,screen,out),expected)
    values=[123456,654321,222222,333333,444444]
    receive(v,-124,snapwire(4,p,handles,f,pct,values));assert k.calculate(v,screen,out)==values
    t.put(k.costumes[0]+0xb0,'<i',65542);assert k.calculate(v,screen,out)!=values
    t.put(k.costumes[0]+0xb0,'<i',65541);assert k.calculate(v,screen,out)==values
    checks+=4
report=dict(passed=True,variants=6,checks=checks,six_equipped_handles=True,costume_pointer_from_original_calculator=True,gem_preview_and_snapshot_guards=True,physical_device_tested=False)
(R/'build/stats265-costume-check.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS',report)
