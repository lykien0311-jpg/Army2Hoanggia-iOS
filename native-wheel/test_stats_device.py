"""Actual native equipment aggregation, installed controller hook and Apple C.

JVM allocation/accessor/vector primitives are controlled. The original native
equipment calculator, costume selection, five totals, hook frames, received
config parser and compiled formula execute. No live account is used.
"""
import json,struct
import ufo_sequence_harness as w
from unicorn import UC_HOOK_CODE
from unicorn.arm64_const import *
from test_stats import fixture,wire,expected
t=w.t;U=w.U;B=w.B;X=w.X;R=t.ROOT
maps=json.loads((R/'stats-map.json').read_text());checks=0;stops=set()
player=0;flags=0;character=0;costumes=[];costumeId=91
def hook(uc,pc,size,opaque):
    if pc in stops:U.emu_stop();return
    w.hook(uc,pc,size,opaque)
U.hook_del(w.NATIVE_HOOK);U.hook_add(UC_HOOK_CODE,hook)
def execute(pc,*args,extra=(),stack_delta=0):
    global stops,checks
    stops={t.STOP,*extra};sp=t.STACK+0x30000
    U.reg_write(UC_ARM64_REG_SP,sp);U.reg_write(UC_ARM64_REG_LR,t.STOP)
    for i,a in enumerate(args):U.reg_write(X[i],a&((1<<64)-1))
    saved=[]
    for i in range(19,30):
        value=t.HEAP+0x1000+i*16;U.reg_write(X[i],value);saved.append(value)
    try:U.emu_start(pc,t.STOP+4,count=2000000)
    except Exception:
        print('native failure',v,c,hex(U.reg_read(UC_ARM64_REG_PC)),hex(U.reg_read(UC_ARM64_REG_LR)),[hex(w.r(i))for i in range(6)])
        raise
    assert U.reg_read(UC_ARM64_REG_PC)in stops,hex(U.reg_read(UC_ARM64_REG_PC))
    assert U.reg_read(UC_ARM64_REG_SP)==sp+stack_delta
    assert [U.reg_read(X[i])for i in range(19,30)]==saved,'callee saved registers'
    assert t.lockDepth==0 and t.get(t.ENV+0x10,'<Q')==0 and t.get(t.ENV+0x38,'<Q')==0
    checks+=1
    return U.reg_read(UC_ARM64_REG_PC)
def arr(values):
    p=t.alloc(0x18+8*len(values));t.put(p+0x10,'<i',len(values))
    for i,n in enumerate(values):t.put(p+0x18+8*i,'<q',n)
    return p
def long_alloc():return arr([0]*w.r(1))
def set_inputs(v,c,useCostume):
    global player,flags,character,costumes
    s=w.setup(v,10);player=t.alloc(0x100);t.put(player+0xd9,'<B',c)
    points=[16000+c*7,900+c*3,800+c*11,700+c,600+c*13]
    t.put(player+0x28,'<Q',arr(points));screen=t.alloc(0x180);out=arr([0]*5);t.put(screen+0xa0,'<Q',out)
    outfit=t.alloc(0x30);slots=arr([0]*5);t.put(outfit+0x10,'<Q',slots);t.put(player+0x78,'<Q',outfit)
    flat=[0]*5;pct=[0]*5;immutable=[]
    for slot in range(5):
        if slot==2:continue
        equipment=t.alloc(0xc0);f=[700+slot*50+j for j in range(5)];p=[10+slot*3+j for j in range(5)]
        fa=arr(f);pa=arr(p);t.put(equipment+0x48,'<Q',fa);t.put(equipment+0x50,'<Q',pa);t.put(equipment+0x80,'<q',54);t.put(equipment+0xb0,'<i',65536+slot);t.put(slots+0x18+8*slot,'<Q',equipment)
        flat=[a+b for a,b in zip(flat,f)];pct=[a+b for a,b in zip(pct,p)]
        immutable.extend([fa,pa,equipment])
    flags=t.alloc(0x20);t.put(flags+0x10,'<i',10);t.put(flags+0x14+c,'<B',int(useCostume))
    costume=t.alloc(0xc0);cf=[101,103,107,109,113];cp=[3,5,7,11,13]
    t.put(costume+0x80,'<q',costumeId);t.put(costume+0xb0,'<i',65541);t.put(costume+0x48,'<Q',arr(cf));t.put(costume+0x50,'<Q',arr(cp))
    costumes=[costume]
    vector=t.alloc(0x40);t.put(vector+0x18,'<Q',arr(costumes));t.put(vector+0x24,'<i',len(costumes));t.put(screen+0xb0,'<Q',vector)
    if useCostume:flat=[a+b for a,b in zip(flat,cf)];pct=[a+b for a,b in zip(pct,cp)]
    character=t.alloc(0x30);t.put(character+0x18,'<h',200+c)
    # Only final summary array may change. Combat state remains byte-identical.
    guarded=[(s['arena'],0x200),(s['p'],0x200),(s['boss'],0x200),(player,0x100),
             (t.get(player+0x28,'<Q'),0x40),*((a,0x40)for a in immutable)]
    snapshots=[(a,bytes(U.mem_read(a,n)))for a,n in guarded]
    return screen,out,points,flat,pct,snapshots
def calculate(v,screen,out):
    execute(B+maps[v]['calculate'],t.ENV,screen)
    return list(struct.unpack('<5q',U.mem_read(out+0x18,40)))
def legacy(p,f,pct,c):
    hp=1000+10*(p[0]+f[0])+(1000+p[0])*pct[0]//100
    result=[hp,(200+c)*(100+(p[1]+f[1])//3+pct[1])//100]
    for j in range(2,5):
        n=(p[j]+f[j])*10;result.append(n+n*pct[j]//100)
    return result
def receive(v,payload):
    msg=t.message(payload);t.put(msg+0x30,'<B',146);stream=t.get(msg+0x20,'<Q')
    before=bytes(U.mem_read(stream,0x30))
    entry=w.report['hooks'][v]['controller']
    assert execute(B+entry,t.ENV,t.alloc(0x20),msg,extra=[B+entry+4])==t.STOP
    assert bytes(U.mem_read(stream,0x30))==before,'configuration consumed a battle stream'
w.primitives[B+0x12e7d88]=long_alloc
w.primitives[B+0x1dfce8]=lambda:len(costumes)
w.primitives[B+0x1dfcb8]=lambda:costumes[w.r(2)]
w.primitives[B+0x1b65d4]=lambda:w.r(1)
for m in maps:
    a=m['calculate']
    w.primitives[B+m['player_get']]=lambda:player
    w.primitives[B+w.branch(a+0x58)]=lambda:flags
    w.primitives[B+w.branch(a+0xe8)]=lambda:costumeId
    w.primitives[B+w.branch(a+0xd4)]=lambda:w.r(1)
    w.primitives[B+m['character_get']]=lambda:character
for v in range(6):
    t.put(t.SERVICE+0x10,'<Q',t.SESSION+0x1000+v*0x100)
    for c,useCostume in [(0,False),(4,True),(9,False)]:
        screen,out,p,f,pct,snapshots=set_inputs(v,c,useCostume)
        # Before a server configuration the exact original summary survives.
        if c==0:assert calculate(v,screen,out)==legacy(p,f,pct,c)
        rows=fixture(v+3);receive(v,wire(rows))
        assert calculate(v,screen,out)==expected(rows,c,p,f,pct)
        if c==0:assert expected(rows,c,p,f,pct)[0]>65535
        for a,before in snapshots:assert bytes(U.mem_read(a,len(before)))==before,'combat or input data changed'
        # A changed server rule takes effect on the next real calculation.
        rows[c][1][0]+=7777;receive(v,wire(rows))
        assert calculate(v,screen,out)==expected(rows,c,p,f,pct)
        # Malformed replacement retains the last complete rule set.
        receive(v,wire(rows)[:-1]);assert calculate(v,screen,out)==expected(rows,c,p,f,pct)
        rows[c]=(False,*rows[c][1:]);receive(v,wire(rows))
        assert calculate(v,screen,out)==legacy(p,f,pct,c)
    # A different connection cannot reuse the previous account's config.
    rows=fixture(v);receive(v,wire(rows));t.put(t.SERVICE+0x10,'<Q',t.SESSION+0x3000+v*0x100)
    assert calculate(v,screen,out)==legacy(p,f,pct,c)
    receive(v,b'bad');assert calculate(v,screen,out)==legacy(p,f,pct,c)
    receive(v,wire(rows));assert calculate(v,screen,out)==expected(rows,c,p,f,pct)
assert not w.packets,'stats path sent a network packet'
result=dict(passed=True,variants=6,characters=[0,4,9],native_controller_and_calculator_calls=checks,
            original_equipment_and_costume_aggregation=True,five_attributes=True,above_uint16=True,
            disabled_and_missing_rules_keep_legacy=True,reconnect_isolation=True,malformed_update_atomic=True,
            combat_and_inputs_unchanged=True,callee_saved_registers_preserved=True,stream_positions_unchanged=True,
            physical_device_tested=False,live_requests=0)
(R/'build/stats-device-check.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS',result)
