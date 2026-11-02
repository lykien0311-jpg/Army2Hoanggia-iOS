"""Native update/wait/keypad call sites, including register and fallback paths."""
import test_hooks as t
import struct

U=t.U;X=t.X;B=t.BASE;R=t.R
t.CALLBACKS['AGBattleAwait']=0x300012000
body=0;body_done=False;old_waits=0
def hook(uc,pc,size,data):
    global body_done,old_waits
    if pc==body:
        # Execute the displaced native frame save, then stand in for its body.
        word=struct.unpack('<I',U.mem_read(pc-4,4))[0]
        # The continuation belongs to the original image; the copied STP was
        # executed in the trampoline. Decode the same guarded prologue here.
        word=current_first;imm=(word>>15)&127;imm=imm-128 if imm&64 else imm
        sp=U.reg_read(t.UC_ARM64_REG_SP);r1=word&31;r2=(word>>10)&31
        U.reg_write(X[r1],t.readq(sp));U.reg_write(X[r2],t.readq(sp+8))
        U.reg_write(t.UC_ARM64_REG_SP,sp-imm*8);body_done=True;t.returned(42)
    elif pc==B+0xaaa6e8:
        old_waits+=1;t.returned()
U.hook_add(t.UC_HOOK_CODE,hook)
cases=0
t.speedAddr=t.buildAddr=t.continuation=0
for update in R['arena_update_hooks']:
    body=B+update['site']+4;current_first=int.from_bytes(bytes.fromhex(update['first']),'little')
    for t.missing in (False,True):
        t.reset();body_done=False
        U.emu_start(B+update['site'],t.STOP+4,count=2000)
        t.preserved();assert body_done and U.reg_read(X[0])==42
        calls=[c for c in t.calls if c[0]=='AGTurnPulse']
        assert bool(calls)==(not t.missing)
        if calls:assert calls[0][1][:2]==(t.ENV,update['variant'])
        cases+=1
body=0
for wait in R['turn_wait_hooks']:
    for t.missing in (False,True):
        t.reset();old_waits=0;frame=t.SP+0x1000;U.reg_write(X[29],frame)
        offset=wait['actor_offset'];base=frame if wait['actor_register']=='x29'else t.SP
        if wait['kind']in(2,3):U.mem_write(base+offset,struct.pack('<i',3))
        U.emu_start(B+wait['hook'],t.STOP+4,count=2000)
        assert U.reg_read(t.UC_ARM64_REG_SP)==t.SP and U.reg_read(X[29])==frame
        assert all(U.reg_read(X[i])==0xc000+i for i in range(19,29))
        calls=[c for c in t.calls if c[0]=='AGBattleAwait']
        assert bool(calls)==(not t.missing) and old_waits==int(t.missing)
        if calls:
            # test_hooks logs three args; the callback's first three carry
            # Env, monitor and the native variant. C tests cover kind/actor.
            assert calls[0][1]==(t.ENV,t.OBJECT,wait['variant'])
        cases+=1
for t.missing in (False,True):
    t.reset();t.continuation=B+R['keypad_paint']+4
    U.emu_start(B+R['keypad_paint'],t.STOP+4,count=2000)
    assert t.stopKind==t.continuation
    assert U.reg_read(t.UC_ARM64_REG_SP)==t.SP-48
    assert tuple(U.reg_read(r)for r in X[:3])==(t.ENV,t.OBJECT,t.MSG)
    cb=[c for c in t.calls if c[0]=='AGViewportKeypad']
    assert bool(cb)==(not t.missing)
    cases+=1
print('PASS:',cases,'native post-update, predicate wait and keypad projection hook ABI/fallback cases')

# New command24 handoff call sites, including missing-module fallback.
t.CALLBACKS['AGTurnChange']=0x300013000
t.roomHandled=1
change_original=0;fallback_owner=[]
def change_hook(uc,pc,size,_):
    if pc==change_original:
        fallback_owner.append(tuple(U.reg_read(r)for r in X[:2]));t.returned()
U.hook_add(t.UC_HOOK_CODE,change_hook)
change_cases=0
body=t.continuation=t.speedAddr=t.buildAddr=0
for entry in R.get('turn_change_hooks',[]):
    change_original=B+entry['original']
    for t.missing in (False,True):
        for actor in (2,8):
            t.reset();fallback_owner.clear();U.reg_write(X[1],actor)
            U.emu_start(B+entry['hook'],t.STOP+4,count=2000);t.preserved()
            cb=[c for c in t.calls if c[0]=='AGTurnChange']
            assert bool(cb)==(not t.missing)
            if cb:assert cb[0][1]==(t.ENV,actor,entry['variant'])
            assert fallback_owner==([(t.ENV,actor)]if t.missing else [])
            change_cases+=1
print('PASS:',change_cases,'native turn-handoff hook ABI, original fallback and player/UFO actor indices')
