"""Run the actual arena prologue, new world mask branch and native HUD entry."""
import json,struct
import test_hooks as t
from unicorn import UC_HOOK_CODE
from unicorn.arm64_const import *
U=t.U;B=t.BASE;X=t.X;CALL=0x30001b000;active=0;seen=[]
t.CALLBACKS['AGBlindPaint']=CALL+0x100
t.CALLBACKS['AGNotesReceive']=CALL+0x200
stop=0
def hook(uc,pc,size,_):
    if pc==CALL:
        args=tuple(U.reg_read(r) for r in X[:3]);seen.append(args)
        for reg in X[:18]:U.reg_write(reg,0xbeef)
        U.reg_write(UC_ARM64_REG_NZCV,0x60000000);t.returned(active)
    elif pc==stop:U.emu_stop()
U.hook_add(UC_HOOK_CODE,hook)
cases=0
for h in t.R['blind_hooks']:
    for mode in ('normal','blind','missing'):
        t.reset();t.speedAddr=t.buildAddr=t.continuation=0;t.missing=mode=='missing';seen.clear()
        active=mode=='blind'
        if mode!='missing':t.writeq(B+t.R['rwvm']+41*8,CALL)
        stop=B+(h['hud'] if active else h['site']+4)
        U.mem_write(t.SP-0x400,b'\xa5'*0x400)
        U.emu_start(B+h['paint'],t.STOP+4,count=3000)
        assert U.reg_read(UC_ARM64_REG_PC)==stop
        fp=U.reg_read(X[29]);assert t.readq(fp-0x60)==t.OBJECT and t.readq(fp-0x68)==t.MSG
        if active:
            for off,value in ((0x6c,2),(0x8c,5),(0x90,10)):
                assert int.from_bytes(U.mem_read(fp-off,4),'little')==value
            assert U.reg_read(X[22])==B+t.R['turn_map'][h['variant']]['arena_class']
        else:assert tuple(U.reg_read(r) for r in X[:3])==(t.ENV,t.MSG,t.MSG)
        assert bool(seen)==(mode!='missing')
        if seen:assert seen==[(t.ENV,t.MSG,h['variant'])]
        cases+=1
for h in t.R['hooks']:
    stop=0
    for command in (106,20):
        for missing in (False,True):
            t.reset();t.missing=missing;t.speedAddr=t.buildAddr=0;t.continuation=B+h['controller']+4
            U.mem_write(t.MSG+0x30,bytes([command]));U.emu_start(B+h['controller'],t.STOP+4,count=3000)
            assert t.stopKind==t.continuation;t.preserved(True)
            assert tuple(U.reg_read(r) for r in X[:3])==(t.ENV,t.OBJECT,t.MSG)
            calls=[c for c in t.calls if c[0]=='AGNotesReceive'];assert bool(calls)==(not missing)
            if calls:assert calls[0][1][:3]==(t.ENV,t.MSG,h['variant'])
            cases+=1
report=dict(passed=True,native_branch_cases=cases,variants=6,
    white_branch_skips_world_and_reaches_original_HUD=True,
    original_controller_still_consumes_blind_and_start_packets=True,
    no_extra_native_stack_frame=True,optional_symbol_fallback=True)
(t.ROOT/'build/blind-hook-check.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS',report)
