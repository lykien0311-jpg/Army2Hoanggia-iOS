"""Warm real controller/camera/HUD/NPC caches together, using the Apple dylib.

The old isolated clock tests injected their own camera pointer and never
warmed the corpse cache. Here all four callers share the packaged data page.
"""
import json,struct
import ufo_sequence_harness as w
from unicorn import UC_HOOK_CODE
from unicorn.arm64_const import *
t=w.t;U=w.U;B=w.B;R=t.ROOT;X=w.X
camera_maps=json.loads((R/'camera-map.json').read_text())
magic=json.loads((R/'corpse-protocol-reference.json').read_text())['magic_decimal']
stops=set();events=[];failures=[];checks=0
watched={t.symbols['_'+s]:s for s in ('AGCameraAllow','AGCorpseReceive','AGCorpseUpdate','AGBlindPaint')}
def hook(uc,pc,size,opaque):
    if pc in stops:U.emu_stop();return
    if pc in watched:events.append(watched[pc])
    w.hook(uc,pc,size,opaque)
U.hook_del(w.NATIVE_HOOK);U.hook_add(UC_HOOK_CODE,hook)
def execute(pc,*args,extra=(),inline=False):
    global stops
    stops={t.STOP,*extra};sp=t.STACK+0x30000
    U.reg_write(UC_ARM64_REG_SP,sp);U.reg_write(UC_ARM64_REG_X29,sp+0x1000)
    U.reg_write(UC_ARM64_REG_LR,t.STOP)
    for i,a in enumerate(args):U.reg_write(X[i],a&((1<<64)-1))
    if inline:U.reg_write(X[19],t.ENV)
    U.emu_start(pc,t.STOP+4,count=2000000)
    end=U.reg_read(UC_ARM64_REG_PC);assert end in stops,hex(end)
    assert t.lockDepth==0 and t.get(t.ENV+0x10,'<Q')==0 and t.get(t.ENV+0x38,'<Q')==0
    return end
def check(ok,label,v,order):
    global checks
    checks+=1
    if not ok:failures.append((v,order,label))
def receive(s,v):
    msg=t.message(struct.pack('>BhhIB',8,500,320,magic,0));t.put(msg+0x30,'<B',93)
    stream=t.get(msg+0x20,'<Q');saved=bytes(U.mem_read(stream,0x30))
    entry=w.report['hooks'][v]['controller'];events.clear()
    end=execute(B+entry,t.ENV,t.alloc(0x20),msg,extra=[B+entry+4])
    return end==t.STOP and bytes(U.mem_read(stream,0x30))==saved and events==['AGCorpseReceive']
def paint(v):
    h=w.report['blind_hooks'][v];events.clear()
    end=execute(B+h['site'],t.ENV,0,t.alloc(0x200),extra=[B+h['site']+4,B+h['hud']],inline=True)
    return end==B+h['site']+4 and events==['AGBlindPaint']
def corpse(s,v):
    a=s['boss'];entry=w.report['corpse_hooks'][v]['update'];events.clear()
    end=execute(B+entry,t.ENV,a,extra=[B+entry+4])
    return end==t.STOP and events==['AGCorpseUpdate'] and t.get(a+0x14e,'<B')==0
def pan(v,axis,delta):
    events.clear();execute(B+camera_maps[v]['pan_x'if axis==0 else'pan_y'],t.ENV,delta)
    return list(events)

t.now=100000.
for v in range(6):
    for order in ('controller_first','camera_first','corpse_first'):
        U.mem_write(B+w.report['rwvm'],bytes(512))
        s=w.setup(v,10);a=s['boss'];t.put(a+0x16c,'<B',18);t.put(a+0x16b,'<B',0)
        cg=t.alloc(0x200);t.put(B+camera_maps[v]['camera_class'],'<Q',cg)
        t.put(B+camera_maps[v]['camera_class']+9,'<B',2);t.put(cg+0xbc,'<B',0)
        t.now+=1
        if order=='camera_first':pan(v,0,20)
        if order=='corpse_first':
            t.put(a+0x68,'<q',0);t.put(a+0x14e,'<B',1)
            check(corpse(s,v),'corpse warmup',v,order);t.put(a+0x68,'<q',1000)
        check(receive(s,v),'controller consumes marked packet with its own function',v,order)
        check(paint(v),'HUD uses its own function',v,order)
        t.put(a+0x68,'<q',0);t.put(a+0x14e,'<B',1)
        check(corpse(s,v),'dead NPC uses its own function after HUD',v,order)
        check(paint(v),'HUD remains intact after dead NPC',v,order)
        for axis,delta in ((0,-20),(0,20),(1,-20),(1,20)):
            field=cg+(0xb4 if axis==0 else 0xb8)
            for wait,expected in ((.04,delta),(.01,0),(.03,delta)):
                t.now+=wait;t.put(field,'<i',0);seen=pan(v,axis,delta)
                check(t.get(field,'<i')==expected,'manual direction and15ms gate',v,order)
                check(seen==['AGCameraAllow'],'pan calls camera function only',v,order)
        t.put(cg+0xbc,'<B',1);t.put(cg+0xb4,'<i',0)
        check(pan(v,0,20)==[] and t.get(cg+0xb4,'<i')==20,'automatic mode bypasses pacing',v,order)
        check(receive(s,v),'controller remains intact after camera',v,order)
assert not failures,failures[:12]
result=dict(passed=True,variants=6,warmup_orders=3,shared_cache_native_cases=checks,
    four_manual_directions=True,manual_pan_interval_ms=15,automatic_mode_unchanged=True,
    corpse_HUD_and_camera_have_independent_callbacks=True,physical_device_tested=False,live_requests=0)
(R/'build/camera-cache-check.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS',result)
