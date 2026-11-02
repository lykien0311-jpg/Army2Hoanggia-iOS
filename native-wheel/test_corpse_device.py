"""Real marked corpse93 -> installed controller/NPC hooks, Apple ARM64.

Reproduce the old detached-part dispatch leaving live-flight14e set. Run the
replacement packet and animation code, then verify the following packet still
reaches the original controller. Only JVM, OS and unrelated base-player update
boundaries are controlled. No device or game socket is involved.
"""
import json,re,struct
import lief
import test_device_bridge as t
from unicorn import UC_HOOK_CODE
from unicorn.arm64_const import *
U=t.u;B=t.MAIN;R=t.ROOT;X=[UC_ARM64_REG_X0+i for i in range(31)]
raw=(R.parent/'validation/inspect-ipa/Army2Hoanggia').read_bytes()
prepared=(R/'build/prepared-native').read_bytes();report=json.loads((R/'build/hook-report.json').read_text())
turns=json.loads((R/'turn-map.json').read_text());notes=json.loads((R/'notes-map.json').read_text())
pm=lief.MachO.parse(str(R/'build/prepared-native')).at(0)
last=max(e+1 for a,e,p in U.mem_regions() if B<=a<B+0x4000000)
for seg in pm.segments:
    if seg.name=='__PAGEZERO':continue
    end=(seg.virtual_address+seg.virtual_size+4095)&-4096
    if end>last:U.mem_map(last,end-last);last=end
    if seg.file_size:U.mem_write(seg.virtual_address,prepared[seg.file_offset:seg.file_offset+seg.file_size])
flight=[m.start() for m in re.finditer(re.escape(raw[0x59a2e8:0x59a300]),raw)]
assert len(flight)==6
stops=set();waits=[];base_update=0;fallback=[];observe_controller=0
def hook(uc,pc,size,_):
    if pc in stops:
        if pc==observe_controller:fallback.append(t.reg(2))
        U.emu_stop();return
    if pc==B+report['dlsym']:
        name=bytes(U.mem_read(t.reg(1),100)).split(b'\0')[0].decode();t.ret(t.symbols.get('_'+name,0));return
    if pc==base_update:t.ret();return
    if pc in (B+0xaaa6e8,B+0xaaa730):waits.append(pc);raise AssertionError('Corpse packet entered a live-flight wait')
    t.hook(uc,pc,size,_)
U.hook_del(t.BASE_HOOK);U.hook_add(UC_HOOK_CODE,hook)
def execute(pc,*args,extra=()):
    global stops
    stops={t.STOP,*extra};sp=t.STACK+0x30000
    U.reg_write(UC_ARM64_REG_SP,sp);U.reg_write(UC_ARM64_REG_LR,t.STOP)
    for i,a in enumerate(args):U.reg_write(X[i],a&((1<<64)-1))
    U.emu_start(pc,t.STOP+4,count=2000000)
    end=U.reg_read(UC_ARM64_REG_PC);assert end in stops,(hex(pc),hex(end))
    assert t.lockDepth==0 and t.get(t.ENV+0x10,'<Q')==0 and t.get(t.ENV+0x38,'<Q')==0
    return end
def branch(a):
    w=struct.unpack_from('<I',raw,a)[0];assert w&0xfc000000==0x94000000
    n=w&0x3ffffff;return a+4*(n-(1<<26)if n&(1<<25)else n)
def setup(v,room=10,capacity=100,index=64,typ=18):
    s={n:t.alloc(size) for n,size in [('g',0x400),('pg',0x400),('ag',0x200),('arena',0x200),
      ('canvas',0x300),('room',0x200),('proj',0x200),('roster',0x18+8*capacity),('actor',0x240)]}
    m=turns[v]
    for a,n in [(m['arena_class'],'g'),(m['player_class'],'pg'),(m['array_class'],'ag'),
                (m['projectile_class'],'proj'),(notes[v]['room_class'],'room'),(notes[v]['canvas'],'canvas')]:
        t.put(B+a,'<Q',s[n]);t.put(B+a+9,'<B',2)
    t.put(s['g']+0xe8,'<Q',s['arena']);t.put(s['g']+0x266,'<B',2)
    t.put(s['canvas']+0xb8,'<Q',s['arena']);t.put(s['ag']+0xa0,'<Q',s['roster'])
    t.put(s['roster']+0x10,'<i',capacity);t.put(s['roster']+0x18+8*index,'<Q',s['actor'])
    t.put(s['actor']+0x16b,'<B',index);t.put(s['actor']+0x16c,'<B',typ);t.put(s['actor']+0x16f,'<B',5)
    t.put(s['actor']+0x159,'<B',1);t.put(s['actor']+0x114,'<i',300);t.put(s['actor']+0x118,'<i',100)
    U.mem_write(s['room']+0x130,bytes([room,5]));t.put(t.SERVICE+0x10,'<Q',t.SESSION)
    s.update(index=index,variant=v);return s
def packet(s,wire,cmd=93,prefix=b''):
    global observe_controller
    msg=t.message(prefix+wire);stream=t.get(msg+0x20,'<Q');t.put(stream+0x20,'<i',len(prefix));t.put(msg+0x30,'<B',cmd)
    saved=bytes(U.mem_read(stream,0x30));v=s['variant'];entry=report['hooks'][v]['controller'];observe_controller=B+entry+4
    stop=execute(B+entry,t.ENV,t.HEAP+0x9000,msg,extra=[observe_controller])
    assert bytes(U.mem_read(stream,0x30))==saved,'Observer changed the original byte reader'
    return stop==t.STOP
def wire(s,x=320,y=320,remove=0):return struct.pack('>BhhIB',s['index'],x,y,0x43505239,remove)
def step(s):
    v=s['variant'];a=report['corpse_hooks'][v]['update']
    return execute(B+a,t.ENV,s['actor'],extra=[B+a+4])==t.STOP
def changed_code(a,data):U.mem_write(B+a,data);U.ctl_remove_cache(B+a,B+a+len(data))

old_cases=new_cases=fallback_cases=0
for v,mp in enumerate(report['corpse_hooks']):
    entry=mp['update'];base_update=B+branch(entry+0x104)
    # Original live-flight start, then original NPC switch for each detached
    # part. Its target is the common return block and never calls flight-end.
    table=entry+0x1c04
    for typ in (18,19,20,21):
        s=setup(v,typ=typ)
        target=table+struct.unpack_from('<i',raw,table+(typ-11)*4)[0]
        assert target==entry+0x1bac
        execute(B+flight[v],t.ENV,s['actor'],320,320)
        assert t.get(s['actor']+0x14e,'<B')==1
        new=bytes(U.mem_read(B+entry,4));changed_code(entry,raw[entry:entry+4])
        for _ in range(5):
            execute(B+entry,t.ENV,s['actor'])
            assert t.get(s['actor']+0x14e,'<B')==1
        changed_code(entry,new);old_cases+=1
    base_update=0
    for room,capacity,index in [(10,9,8),(14,100,64),(15,127,126)]:
        for typ in (17,18,19,20,21):
            s=setup(v,room,capacity,index,typ);a=s['actor'];before=bytes(U.mem_read(a,0x240))
            assert packet(s,wire(s),prefix=b'xx')
            assert bytes(U.mem_read(a,0x240))==before,'Packet should enqueue animation without changing live flags'
            assert t.get(a+0x14e,'<B')==0
            # Network progress is independent of the still-falling corpse.
            assert not packet(s,b'\x02',cmd=24)
            assert t.get(a+0x118,'<i')==100 and not waits
            expected_y=100;speed=0
            for frame in range(20):
                speed=min(24,speed+2);expected_y=min(320,expected_y+speed)
                assert step(s) and t.get(a+0x114,'<i')==320 and t.get(a+0x118,'<i')==expected_y
                assert t.get(a+0x14e,'<B')==0
                if frame==2:assert packet(s,wire(s)) # repeat must not restart the fall
            assert expected_y==320 and t.get(a+0x159,'<B')==1
            assert not packet(s,b'\x02',cmd=24) # queue remains open after landing
            # Same actor can be moved again and removed only at the destination.
            assert packet(s,wire(s,y=360,remove=1));assert step(s)
            assert t.get(a+0x159,'<B')==1
            for _ in range(3):assert step(s)
            assert t.get(a+0x118,'<i')==360 and t.get(a+0x159,'<B')==0
            new_cases+=1
    # Marked corpse packets never relocate a live part or override live update.
    s=setup(v);a=s['actor'];t.put(a+0x68,'<q',1000);before=bytes(U.mem_read(a,0x240))
    assert packet(s,wire(s)) and bytes(U.mem_read(a,0x240))==before
    assert not step(s);fallback_cases+=1
    # Ordinary5-byte flight, malformed/unmarked extensions, non-airship rooms
    # and native UFO actors take the unchanged controller/update paths.
    for payload in [wire(s)[:5],wire(s)[:5]+b'xxxx\0',wire(s)[:-1],wire(s)+b'\0']:
        assert not packet(s,payload);fallback_cases+=1
    t.put(a+0x68,'<q',0)
    for room,typ in [(8,16),(9,16),(3,18),(14,12),(15,22)]:
        t.put(s['room']+0x130,'<B',room);t.put(a+0x16c,'<B',typ)
        assert not packet(s,wire(s)) and not step(s);fallback_cases+=1
    # Session, arena, replaced actors, new match and revival cannot reuse motion.
    for reset in ('session','arena','replace','match','revive'):
        s=setup(v);a=s['actor'];assert packet(s,wire(s));assert step(s)
        if reset=='session':t.put(t.SERVICE+0x10,'<Q',t.SESSION+0x100)
        elif reset=='arena':
            arena=t.alloc(0x200);t.put(s['g']+0xe8,'<Q',arena);t.put(s['canvas']+0xb8,'<Q',arena)
        elif reset=='replace':
            new=t.alloc(0x240);U.mem_write(new,bytes(U.mem_read(a,0x240)));t.put(s['roster']+0x18+s['index']*8,'<Q',new);s['actor']=new;a=new
        elif reset=='match':assert not packet(s,b'',cmd=20)
        else:t.put(a+0x68,'<q',1);assert not step(s);t.put(a+0x68,'<q',0)
        before=t.get(a+0x118,'<i');assert step(s);assert t.get(a+0x118,'<i')==before
        fallback_cases+=1

result=dict(passed=True,variants=6,old_native_detached_part_flight_stalls=old_cases,
    marked_packet_and_full_fall_sequences=new_cases,stale_live_normal_UFO_and_reset_cases=fallback_cases,
    rooms=[10,14,15],characters=[17,18,19,20,21],roster_capacities=[9,100,127],
    wire_command=93,wire_length=10,wire_magic='43505239',native_reader_unchanged=True,
    no_wait_during_corpse_motion=True,subsequent_controller_packets_reachable=True,
    animation_matches_JAR_acceleration_and_destination=True,physical_device_tested=False,live_requests=0)
(R/'build/corpse-device-check.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS',result)
