"""Actual Apple ARM64 library + original equipment calculator + Sua12 wire fixtures.

Run after packaging/preparing the native main; fixtures are emitted by
fixtures-src/army2/server/EmitSua12Stats.java against the supplied Sua12 server.
"""
import base64,json,struct
import test_stats_device as k
from test_stats265 import snapwire
from unicorn.arm64_const import UC_ARM64_REG_PC
t=k.t;w=k.w;U=k.U;B=k.B;R=k.R
rows=json.loads((R/'build/sua12-stats-fixtures.json').read_text());checks=0
def receive(v,command,payload):
    msg=t.message(payload);t.put(msg+0x30,'<B',command&255);stream=t.get(msg+0x20,'<Q');before=bytes(U.mem_read(stream,0x30))
    entry=w.report['hooks'][v]['controller']
    assert k.execute(B+entry,t.ENV,t.alloc(0x20),msg,extra=[B+entry+4])==t.STOP
    assert bytes(U.mem_read(stream,0x30))==before
def inventory(blob):
    p=memoryview(blob);pos=1;items={}
    def read(fmt):
        nonlocal pos
        n=struct.calcsize(fmt);v=struct.unpack_from(fmt,p,pos);pos+=n;return v
    for _ in range(p[0]):
        h=read('>i')[0];hero,kind,template=read('>bbh');n=read('>H')[0];pos+=n;size=read('>B')[0];flat=[];pct=[]
        for j in range(size//2):a,b=read('>qq');flat.append(a);pct.append(b)
        read('>5b');items[h]=(flat,pct,template)
    chosen=[read('>i')[0]for _ in range(5)];assert pos==len(p)
    return items,chosen
for v in range(6):
    t.put(t.SERVICE+0x10,'<Q',t.SESSION+0x1000+v*0x100)
    for row in rows:
        hero=row['hero'];k.v=v;k.c=hero
        screen,out,*_=k.set_inputs(v,hero,False);player=k.player
        t.put(player+0x28,'<Q',k.arr(row['points']));t.put(k.character+0x18,'<h',row['nativeBase'])
        bag,chosen=inventory(base64.b64decode(row['101']));outfit=t.get(player+0x78,'<Q');slots=t.get(outfit+0x10,'<Q');flat=[0]*5;pct=[0]*5
        for i,h in enumerate(chosen):
            item=t.alloc(0xc8);f,p,template=bag[h];t.put(item+0x80,'<q',template);t.put(item+0xb0,'<i',h);t.put(item+0x48,'<Q',k.arr(f));t.put(item+0x50,'<Q',k.arr(p));t.put(slots+0x18+i*8,'<Q',item)
            flat=[a+b for a,b in zip(flat,f)];pct=[a+b for a,b in zip(pct,p)]
        receive(v,-110,base64.b64decode(row['-110']));receive(v,-124,base64.b64decode(row['-124']))
        assert k.calculate(v,screen,out)==row['expected'],(v,hero,row['modern'],row['family'],row['count'])
        checks+=1
        if row['family']==4 and row['count']==3:
            # A valid snapshot overrides stale local preview rules; malformed
            # replacements cannot damage it, and changed unsaved gear rejects it.
            values=[100001+hero,200002+v,300003,400004,500005]
            receive(v,-124,snapwire(hero,row['points'],chosen,flat,pct,values));assert k.calculate(v,screen,out)==values
            receive(v,-124,b'bad');assert k.calculate(v,screen,out)==values
            gear=t.get(slots+0x18,'<Q');t.put(gear+0xb0,'<i',65555);assert k.calculate(v,screen,out)!=values;t.put(gear+0xb0,'<i',chosen[0])
            fa=t.get(gear+0x48,'<Q');old=t.get(fa+0x18+8,'<q');t.put(fa+0x18+8,'<q',old+30);assert k.calculate(v,screen,out)!=values;t.put(fa+0x18+8,'<q',old)
            receive(v,-110,base64.b64decode(row['-110']));assert k.calculate(v,screen,out)!=values
            checks+=5
assert not w.packets
result=dict(passed=True,server_fixtures=len(rows),variants=6,matching_and_preview_checks=checks,all_five_stats=True,
            actual_Sua12_server_packets=True,actual_Apple_ARM64_library=True,original_native_calculator=True,
            streams_and_callee_saved_registers_preserved=True,live_requests=0,physical_device_tested=False)
(R/'build/stats265-device-check.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS',result)
