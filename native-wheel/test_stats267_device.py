"""21 attack gems from real server/JAR packets with real native item identity.

Native class metadata and the original equipment-selection instructions prove
that +0x80 is a template long, while +0xb0 is the inventory-handle int.
The numerical regression uses synthetic points/base, not unseen account data.
"""
import base64,json,struct
import test_stats_device as k
t=k.t;w=k.w;U=k.U;B=k.B;R=k.R
# The emulator retains allocations instead of running a Java GC. Keep all
# 3,006 fixture lifetimes in a larger test-only arena; production is unchanged.
U.mem_map(t.HEAP+0x2000000,0x2000000)
def fixture_alloc(n):
    p=t.cursor;t.cursor+=(n+15)&-16;assert t.cursor<t.HEAP+0x4000000;U.mem_write(p,bytes(n));return p
t.alloc=fixture_alloc
regression=json.loads((R/'build/stats267-fixture.json').read_text())
rows=[regression]+json.loads((R/'build/stats267-all-fixtures.json').read_text())
maps=json.loads((R/'stats-map.json').read_text())
def receive(v,cmd,payload):
    msg=t.message(payload);t.put(msg+0x30,'<B',cmd&255);a=w.report['hooks'][v]['controller']
    assert k.execute(B+a,t.ENV,t.alloc(0x20),msg,extra=[B+a+4])==t.STOP
def gear_items(payload):
    p=memoryview(payload);pos=1;items={}
    def read(fmt):
        nonlocal pos
        n=struct.calcsize(fmt);result=struct.unpack_from(fmt,p,pos);pos+=n;return result
    for _ in range(p[0]):
        h=read('>i')[0];hero,kind,template=read('>bbh');n=read('>H')[0];pos+=n;size=read('>B')[0];f=[];pct=[]
        for j in range(size//2):a,b=read('>qq');f.append(a);pct.append(b)
        read('>5b');items[h]=(template,f,pct)
    selected=[read('>i')[0]for _ in range(5)];assert pos==len(p)
    return items,selected
checks=0
for v in range(6):
    t.put(t.SERVICE+0x10,'<Q',t.SESSION+0xa000+v*0x100)
    for row in rows:
        hero=row['hero'];k.v=v;k.c=hero
        screen,out,*_=k.set_inputs(v,hero,False);t.put(k.player+0x28,'<Q',k.arr(row['points']))
        t.put(k.character+0x18,'<h',row.get('nativeBase',280))
        slots=t.get(t.get(k.player+0x78,'<Q')+0x10,'<Q');bag,selected=gear_items(base64.b64decode(row['101']))
        for i,h in enumerate(selected):
            template,f,pct=bag[h];item=t.alloc(0xc8)
            t.put(item+0x80,'<q',template);t.put(item+0xb0,'<i',h)
            t.put(item+0x48,'<Q',k.arr(f));t.put(item+0x50,'<Q',k.arr(pct));t.put(slots+0x18+i*8,'<Q',item)
        receive(v,-110,base64.b64decode(row['-110']))
        actual=k.calculate(v,screen,out)
        assert actual==row['jar_expected'],('native inventory identity drops gem %',v,hero,row.get('family'),row.get('count'),actual,row['jar_expected'])
        if row is regression:assert actual[1]==4585
        receive(v,-124,base64.b64decode(row['-124']))
        paint=maps[v]['paint'];k.execute(B+paint,t.ENV,screen,t.alloc(0x20),extra=[B+paint+4],stack_delta=-96)
        assert list(struct.unpack('<5q',U.mem_read(out+0x18,40)))==row['expected']
        checks+=2
report=dict(passed=True,variants=6,server_JAR_fixtures=len(rows),checks=checks,attack_gem_count=21,final_attack_percent=42,
            independent_server_and_Sua12_JAR_attack=4585,native_inventory_handle_offset='0xb0',
            native_template_id_offset='0x80',actual_Apple_ARM64=True,physical_device_tested=False,
            synthetic_account_fixture=True,live_requests=0)
(R/'build/stats267-device-check.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS',report)
