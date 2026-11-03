"""Installed ARM64 waits after actual projectile/part-effect completion.

Run Apple's compiled bridge and original native projectile finalizer, four
part-death particle submissions, and canvas completion counter. JVM monitor
waits, randomness and particle allocation are controlled boundaries. This is
not physical-device or live-server acceptance.
"""
import json,re,struct
import lief
import test_device_bridge as t
from unicorn import UC_HOOK_CODE
from unicorn.arm64_const import *

U=t.u;B=t.MAIN;R=t.ROOT;X=[UC_ARM64_REG_X0+i for i in range(31)]
raw=(R.parent/'validation/inspect-ipa/Army2Hoanggia').read_bytes()
prepared=(R/'build/prepared-native').read_bytes()
report=json.loads((R/'build/hook-report.json').read_text())
turns=json.loads((R/'turn-map.json').read_text());notes=json.loads((R/'notes-map.json').read_text())
pm=lief.MachO.parse(str(R/'build/prepared-native')).at(0)
last=max(e+1 for a,e,p in U.mem_regions() if B<=a<B+0x4000000)
for seg in pm.segments:
    if seg.name=='__PAGEZERO':continue
    end=(seg.virtual_address+seg.virtual_size+4095)&-4096
    if end>last:U.mem_map(last,end-last);last=end
    if seg.file_size:U.mem_write(seg.virtual_address,prepared[seg.file_offset:seg.file_offset+seg.file_size])

def branch(a):
    word=struct.unpack_from('<I',raw,a)[0];assert word&0xfc000000==0x94000000
    n=word&0x3ffffff;return a+4*(n-(1<<26) if n&(1<<25) else n)
def copies(a,n):
    found=[m.start() for m in re.finditer(re.escape(raw[a:a+n]),raw)]
    assert len(found)==6,(hex(a),found);return found
finalizers=[m.start() for m in re.finditer(re.escape(raw[0x580fdc:0x580ffc]),raw)
            if raw[m.start()+0x34:m.start()+0x38]==raw[0x581010:0x581014]]
part_effects=[m.start() for m in re.finditer(re.escape(raw[0x5988fc:0x59891c]),raw)
              if raw[m.start()+0x28:m.start()+0x48]==raw[0x598924:0x598944]]
counter_starts=copies(0x510ce4,24)
assert len(finalizers)==len(part_effects)==6,(finalizers,part_effects)
legacy=[];timed=[];stops=set();watched=0;clear_after=3;exit_mode='';s={};particles=[];primitives={}
def hook(uc,pc,size,_):
    if pc in stops:U.emu_stop();return
    if pc==B+report['dlsym']:
        name=bytes(U.mem_read(t.reg(1),100)).split(b'\0')[0].decode();t.ret(t.symbols['_'+name]);return
    if pc==B+0xaaa6e8:
        legacy.append((t.reg(0),t.reg(1)));t.ret();return
    if pc==B+0xaaa730:
        timed.append((t.reg(0),t.reg(1),t.reg(2)))
        assert timed[-1]==(t.ENV,s['monitor'],16)
        t.now+=.016
        if exit_mode=='scene':t.put(s['canvas']+0xb8,'<Q',0)
        elif exit_mode=='session':t.put(t.SERVICE+0x10,'<Q',t.SESSION+0x100)
        elif exit_mode=='stage':t.put(s['boss']+0x16c,'<B',12)
        elif len(timed)>=clear_after:t.put(watched,'<B',0)
        t.ret();return
    if pc in primitives:
        kind=primitives[pc]
        if kind=='world':t.ret(s['arena'])
        elif kind=='random':t.ret(0)
        elif kind=='particle':particles.append(tuple(t.reg(i) for i in range(2,7)));t.ret()
        return
    t.hook(uc,pc,size,_)
U.hook_del(t.BASE_HOOK);U.hook_add(UC_HOOK_CODE,hook)
def execute(pc,*args,stop=None,registers=None):
    global stops
    stops=set(stop or [t.STOP])
    sp=t.STACK+0x30000;frame=sp+0x1000
    U.reg_write(UC_ARM64_REG_SP,sp);U.reg_write(UC_ARM64_REG_X29,frame);U.reg_write(UC_ARM64_REG_LR,t.STOP)
    for i,a in enumerate(args):U.reg_write(X[i],a&((1<<64)-1))
    for i,a in (registers or {}).items():U.reg_write(X[i],a)
    U.emu_start(pc,t.STOP+4,count=2000000)
    assert U.reg_read(UC_ARM64_REG_PC) in stops,(hex(pc),hex(U.reg_read(UC_ARM64_REG_PC)))
    assert U.reg_read(UC_ARM64_REG_SP)==sp
    assert t.lockDepth==0 and t.get(t.ENV+0x10,'<Q')==0 and t.get(t.ENV+0x38,'<Q')==0
def run_wait(wait,old=False):
    legacy.clear();timed.clear()
    actor=s['actor'];sp=t.STACK+0x30000;frame=sp+0x1000
    t.put(frame-0x78,'<i',actor);t.put(sp+0x4cc,'<i',actor)
    if old:execute(t.symbols['_AGTurnAwait'],t.ENV,s['monitor'],v,wait['kind'],actor)
    else:execute(B+wait['site'],t.ENV,s['monitor'],stop=[B+wait['site']+4])
def init(v,room,count,boss_slot):
    m=turns[v]
    q={n:t.alloc(size) for n,size in [('g',0x400),('pg',0x400),('ag',0x200),('canvas',0x300),
       ('arena',0x200),('roster',0x18+8*count),('p',0x200),('boss',0x200),('room',0x200),('proj',0x200),('monitor',0x20)]}
    for a,n in [(m['arena_class'],'g'),(m['player_class'],'pg'),(m['array_class'],'ag'),
                (m['projectile_class'],'proj'),(notes[v]['canvas'],'canvas'),(notes[v]['room_class'],'room')]:
        t.put(B+a,'<Q',q[n]);t.put(B+a+9,'<B',2)
    t.put(q['g']+0xe8,'<Q',q['arena']);t.put(q['g']+0x266,'<B',7)
    t.put(q['canvas']+0xb8,'<Q',q['arena']);t.put(q['ag']+0xa0,'<Q',q['roster'])
    t.put(q['roster']+0x10,'<i',count);t.put(q['roster']+0x18+7*8,'<Q',q['p'])
    t.put(q['roster']+0x18+boss_slot*8,'<Q',q['boss']);t.put(q['boss']+0x16c,'<B',17)
    U.mem_write(q['room']+0x130,bytes([room,5]));q['actor']=7
    t.put(t.SERVICE+0x10,'<Q',t.SESSION)
    return q

cases=native_projectiles=native_parts=0
for v,m in enumerate(turns):
    # A real native part-death effect submits four particles and sets the
    # canvas busy flag. Its original frame counter, not the bridge, clears it.
    primitives.clear()
    for d,kind in [(0x20,'world'),(0x4c,'random'),(0x6c,'random'),(0x8c,'particle')]:
        primitives[B+branch(part_effects[v]+d)]=kind
    for room,count,slot in [(10,9,8),(14,100,64),(15,127,126)]:
        s=init(v,room,count,slot)
        waits=m['waits'];shot=next(w for w in waits if w['kind']==0)
        effect=next(w for w in waits if w['kind']==1)
        manager=t.alloc(0x80);t.put(s['proj']+0x118,'<B',1)
        execute(B+finalizers[v],t.ENV,manager)
        assert t.get(s['proj']+0x118,'<B')==0
        assert t.get(s['canvas']+0x13c,'<B')==1
        assert t.get(manager+0x4c,'<I')==0 and t.get(manager+0x5d,'<B')==1
        run_wait(shot,old=True);assert legacy==[(t.ENV,s['monitor'])] and not timed
        run_wait(shot);assert not legacy and not timed;native_projectiles+=1

        particles.clear();t.put(s['boss']+0x114,'<i',300);t.put(s['boss']+0x118,'<i',120)
        execute(B+part_effects[v],t.ENV,s['boss'])
        assert len(particles)==4 and t.get(s['canvas']+0x13c,'<B')==1
        assert t.get(s['canvas']+0x118,'<I')==0
        for frame_no in range(1,21):
            frame=t.STACK+0x31000;t.put(frame-0x60,'<i',1)
            a=counter_starts[v]
            execute(B+a,stop=[B+a+0x64,B+a+0x134],registers={19:t.ENV,21:B+notes[v]['canvas']})
            assert t.get(s['canvas']+0x13c,'<B')==(frame_no<20)
        run_wait(effect,old=True);assert legacy==[(t.ENV,s['monitor'])] and not timed
        run_wait(effect);assert not legacy and not timed;native_parts+=1

        for wait in waits:
            watched={0:s['proj']+0x118,1:s['canvas']+0x13c,2:s['p']+0x167,3:s['p']+0x14e}[wait['kind']]
            t.put(watched,'<B',0);run_wait(wait,old=True)
            assert legacy==[(t.ENV,s['monitor'])] and not timed
            run_wait(wait);assert not legacy and not timed;cases+=1
            # Long animation remains pending through 79 spurious wakes;
            # even elapsed time beyond a second cannot finish it early.
            t.put(watched,'<B',1);clear_after=80;run_wait(wait)
            assert len(timed)==80 and not legacy and t.get(watched,'<B')==0;cases+=1
            for exit_mode in ('scene','session'):
                t.put(watched,'<B',1);run_wait(wait)
                assert len(timed)==1 and not legacy and t.get(watched,'<B')==1
                t.put(s['canvas']+0xb8,'<Q',s['arena']);t.put(t.SERVICE+0x10,'<Q',t.SESSION);cases+=1
            exit_mode='';t.put(watched,'<B',0)
        # Linked stages without a balloon retain the previous bridge.
        if room!=10:
            t.put(s['boss']+0x16c,'<B',12);run_wait(shot)
            assert legacy==[(t.ENV,s['monitor'])] and not timed;cases+=1
        t.put(s['room']+0x130,'<B',3);run_wait(shot)
        assert legacy==[(t.ENV,s['monitor'])] and not timed;cases+=1

result=dict(passed=True,apple_native_wait_cases=cases,variants=6,rooms=[10,14,15],
    roster_capacities=[9,100,127],native_finalizer_lost_notify_replays=native_projectiles,
    native_part_effect_counter_lost_notify_replays=native_parts,
    native_part_particles=4,native_effect_completion_frames=20,
    busy_waits_survive_79_spurious_wakes=True,timeout_does_not_clear_flags=True,
    scene_and_connection_changes_release_wait=True,other_stages_keep_previous_bridge=True,
    physical_device_tested=False,live_requests=0)
(R/'build/airship-wait-check.json').write_text(json.dumps(result,indent=2)+'\n')
print('PASS',result)
