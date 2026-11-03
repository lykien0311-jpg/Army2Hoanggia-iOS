"""Apple ARM64 diagnostic snapshots/packet observer never change battle bytes."""
import ctypes as C,json,re,struct
import test_device_bridge as t
R=t.ROOT;B=t.MAIN;U=t.u
class Actor(C.Structure):
    _fields_=[(f,C.c_int)for f in 'slot index character state visible gravity walk flight x y'.split()]+[('hp',C.c_int64)]
class Event(C.Structure):
    _fields_=[(f,C.c_int)for f in 'command length first'.split()]+[('serial',C.c_uint64)]
class Trace(C.Structure):pass
body=(R/'ShipTrace.h').read_text().rsplit('typedef struct {',1)[1].split('} AGShipTrace;')[0]
fields=[];types={'int':C.c_int,'uint64_t':C.c_uint64,'double':C.c_double,'AGShipActor':Actor,'AGShipEvent':Event}
for decl in body.split(';'):
    decl=decl.strip()
    if not decl:continue
    typ,names=decl.split(None,1)
    for name in names.split(','):
        m=re.fullmatch(r'(\w+)(?:\[(\w+)\])?',name.strip());assert m,name
        size=m[2];ct=types[typ]
        if size:ct=ct*16
        fields.append((m[1],ct))
Trace._fields_=fields
turns=json.loads((R/'turn-map.json').read_text());notes=json.loads((R/'notes-map.json').read_text())
cameras=[int(x,16)for x in re.findall('0x[0-9a-f]+',(R/'ShipTraceMap.h').read_text())]
out=t.alloc(C.sizeof(Trace))
def trace(v):
    assert t.call('_AGShipTraceGet',v,out)==1
    return Trace.from_buffer_copy(bytes(U.mem_read(out,C.sizeof(Trace))))
def tick(v,source=1):t.now+=.21;t.call('_AGShipTraceTick',t.ENV,v,source)
def receive(v,cmd,wire):
    msg=t.message(wire);t.put(msg+0x30,'<B',cmd&255)
    inp=t.get(msg+0x20,'<Q');before=bytes(U.mem_read(inp,0x30))
    t.call('_AGShipTraceReceive',t.ENV,msg,v)
    assert bytes(U.mem_read(inp,0x30))==before
    return msg
cases=0;t.sent.clear();t.now=100000. # Earlier movement fixtures reset their fake clock.
for v,m in enumerate(turns):
    s={n:t.alloc(z)for n,z in [('g',0x400),('ag',0x200),('pg',0x400),('arena',0x200),('canvas',0x300),
        ('room',0x200),('proj',0x200),('cam',0x80),('cg',0x200),('array',0x18+100*8),('p',0x240),('part',0x240)]}
    for address,n in [(m['arena_class'],'g'),(m['array_class'],'ag'),(m['player_class'],'pg'),
        (m['projectile_class'],'proj'),(notes[v]['canvas'],'canvas'),(notes[v]['room_class'],'room'),(cameras[v],'cg')]:
        t.put(B+address,'<Q',s[n]);t.put(B+address+9,'<B',2)
    t.put(s['g']+0xe8,'<Q',s['arena']);t.put(s['g']+0x266,'<B',2);t.put(s['g']+0xd8,'<Q',s['cam'])
    t.put(s['cam']+0x20,'<i',8);t.put(s['cg']+0xbc,'<B',1)
    t.put(s['ag']+0xa0,'<Q',s['array']);t.put(s['ag']+0xd0,'<B',8)
    t.put(s['canvas']+0xb8,'<Q',s['arena']);t.put(s['room']+0x130,'<B',10)
    t.put(s['array']+0x10,'<i',100);t.put(s['array']+0x18+2*8,'<Q',s['p']);t.put(s['array']+0x18+9*8,'<Q',s['part'])
    p=s['p'];a=s['part'];t.put(p+0x68,'<q',900000000000);t.put(p+0x16b,'<B',2);t.put(p+0x16c,'<B',2)
    t.put(a+0x16b,'<B',0);t.put(a+0x16c,'<B',18);t.put(a+0x16f,'<B',5);t.put(a+0x118,'<i',640)
    t.put(s['proj']+0x118,'<B',1);t.put(s['proj']+0x115,'<B',0)
    saved={n:bytes(U.mem_read(s[n],z))for n,z in [('g',0x400),('ag',0x200),('p',0x240),('part',0x240),('cam',0x80),('proj',0x200)]}
    tick(v);d=trace(v)
    assert (d.active,d.owner,d.local,d.cameraActor,d.cameraMode,d.projectileBusy)==(1,8,2,8,1,1),(v,d.active,d.owner,d.local,d.cameraActor,d.cameraMode,d.projectileBusy,d.sampleTime,d.samples)
    assert d.actorCount==2 and d.actors[1].slot==9 and d.actors[1].index==0 and d.actors[1].hp==0
    assert d.actors[0].hp==900000000000 # no32-bit HP truncation
    cases+=1
    # Real server turn owner can disagree with native owner/camera, exactly
    # the ambiguity the recording must expose. Never apply that turn here.
    receive(v,24,b'\x0a'+struct.pack('>IiQ',1429485652,17,900017));d=trace(v)
    assert (d.serverOwner,d.serverTurn,d.owner,d.cameraActor)==(10,17,8,8);cases+=1
    receive(v,93,struct.pack('>BhhIB',9,440,640,int(json.loads((R/'corpse-protocol-reference.json').read_text())['magic_decimal']),1));d=trace(v)
    assert (d.corpsePacketActor,d.corpseTargetX,d.corpseTargetY,d.corpseRemove)==(9,440,640,1);cases+=1
    t.call('_AGShipTraceWait',v,3,9,1);t.call('_AGShipTraceCorpse',v,0,18,0);d=trace(v)
    assert (d.waitActive,d.waitKind,d.waitActor,d.corpseHandled)==(1,3,9,0) and d.corpseRejected>0;cases+=1
    for i in range(20):receive(v,24,bytes([8+i%5]))
    d=trace(v);assert d.eventCount==16 and all(d.events[i].serial<d.events[i+1].serial for i in range(15))
    assert d.events[15].first==12 and d.serverTurn==-1;cases+=1
    before=d.samples
    for _ in range(50):t.call('_AGShipTraceTick',t.ENV,v,0)
    assert trace(v).samples==before,'Read-only sampling must remain throttled';cases+=1
    for n,data in saved.items():assert bytes(U.mem_read(s[n],len(data)))==data,(v,n)
    assert not t.sent,'Diagnostics sent a game packet';cases+=1
    t.put(s['canvas']+0xb8,'<Q',0);tick(v);assert trace(v).active==0
    t.put(s['canvas']+0xb8,'<Q',s['arena']);t.put(s['room']+0x130,'<B',8);tick(v)
    before=trace(v).receives;receive(v,24,b'\x02');assert trace(v).active==0 and trace(v).receives==before;cases+=1
result=dict(passed=True,variants=6,apple_arm64_observer_cases=cases,combat_bytes_changed=0,
    original_reader_unchanged=True,server_native_camera_disagreement_captured=True,
    corpse_roster_index_mismatch_captured=True,history_events=16,native_sampling_max_hz=5,
    diagnostics_game_packets=0,physical_device_tested=False)
(R/'build/ship-trace-check.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS',result)
