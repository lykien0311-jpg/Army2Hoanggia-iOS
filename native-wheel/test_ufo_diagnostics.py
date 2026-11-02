"""Observe compiled device state without granting turns or sending packets."""
import ctypes as C,re,struct
import ufo_sequence_harness as w
t=w.t
header=(w.ROOT/'UfoDiagnostics.h').read_text().split('typedef struct {',1)[1].split('}',1)[0]
fields=[]
for ctype,names in re.findall(r'(uint64_t|uint32_t|double|int)\s+([^;]+);',header):
    fields += [(n.strip(),{'uint64_t':C.c_uint64,'uint32_t':C.c_uint32,'double':C.c_double,'int':C.c_int}[ctype])for n in names.split(',')]
class Snapshot(C.Structure):_fields_=fields
ptr=t.alloc(C.sizeof(Snapshot))
def get(v):
    assert w.call('AGUfoDiagnosticsGet',v,ptr)==1
    return Snapshot.from_buffer_copy(bytes(w.U.mem_read(ptr,C.sizeof(Snapshot))))
cases=0
assert w.call('AGUfoDiagnosticsGet',-1,ptr)==0
assert w.call('AGUfoDiagnosticsGet',6,ptr)==0
assert w.call('AGUfoDiagnosticsGet',0,0)==0
for v in range(6):
    had=w.call('AGUfoDiagnosticsGet',v,ptr)
    before=Snapshot.from_buffer_copy(bytes(w.U.mem_read(ptr,C.sizeof(Snapshot)))) if had else Snapshot()
    s=w.setup(v);w.packets.clear();w.pulse(v);d=get(v)
    assert d.enabled and d.active and d.local==2 and d.owner==2
    assert d.modes==before.modes+1 and d.starts==before.starts+1 and d.ticks==before.ticks+1
    assert d.last115Length==4 and d.lastMagic==0x55464f01
    assert not w.packets;cases+=1
    w.queue(v,11);w.pulse(v);d=get(v)
    assert d.turns==before.turns+1 and d.aims==before.aims+1 and d.accepted==before.accepted+1
    assert d.hasPlan and d.turn==11 and d.serverOwner==2
    assert d.sequence!=d.applied and d.last24Length==17 and d.last115Length==21
    assert d.planX==240 and d.planY==350 and d.lastAimOwner==2
    assert not w.packets;cases+=1
    t.put(s['proj']+0x118,'<B',1);w.pulse(v);d=get(v)
    assert d.effects==1 and d.blocked&1 and not d.sent;cases+=1
    for _ in range(3):
        ticks=d.ticks;d=get(v);assert d.ticks==ticks and not w.packets
    cases+=1
    monitor=t.alloc(0x20);w.watched=s['proj']+0x118;w.clear_after=3;w.timed.clear()
    w.call('AGTurnAwait',t.ENV,monitor,v,0,8);d=get(v)
    assert d.waits==before.waits+1 and not d.waitActive and d.waitKind==0 and d.waitActor==8
    assert len(w.timed)==3 and not w.packets;cases+=1
    w.receive(v,-115,b'\x00\x01\x02');d=get(v)
    assert d.last115Length==3 and d.hasPlan;cases+=1
    w.receive(v,-115,struct.pack('>I',0x55464f00));d=get(v)
    assert not d.enabled and not d.hasPlan and d.modes==before.modes+2;cases+=1
    t.put(t.SERVICE+0x10,'<Q',0);w.pulse(v);d=get(v)
    assert d.contextOK==0 and not w.packets;cases+=1
print('PASS:',cases,'compiled ARM64 read-only diagnostic snapshots; mode/turn/aim lengths, blockers, native sequence, wait completion, malformed input, no packets')
