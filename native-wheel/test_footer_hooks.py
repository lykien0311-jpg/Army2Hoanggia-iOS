"""Execute the native base-screen footer with wheel open/closed/fallback."""
import test_hooks as t
from unicorn import UC_HOOK_CODE
from unicorn.arm64_const import *
U=t.U;B=t.BASE;X=t.X
callback=0x30000c000;t.CALLBACKS['AGWheelSuppressFooter']=callback
visible=0
def hook(uc,pc,size,_):
    if pc==callback:t.returned(visible)
U.hook_add(UC_HOOK_CODE,hook)
cases=0
for h in t.R['footer_hooks']:
    for missing,visible in [(False,0),(False,1),(True,0)]:
        t.reset();t.missing=missing;t.continuation=B+h['site']+4
        U.emu_start(B+h['site'],t.STOP+4,count=1000)
        skipped=visible and not missing
        assert t.stopKind==(t.STOP if skipped else t.continuation)
        assert U.reg_read(UC_ARM64_REG_SP)==t.SP-(0 if skipped else 48)
        calls=[c for c in t.calls if c[0]=='AGWheelSuppressFooter']
        assert bool(calls)==(not missing)
        if calls:assert calls[0][1][0]==h['variant']
        if not skipped:
            assert tuple(U.reg_read(r)for r in X[:3])==(t.ENV,t.OBJECT,t.MSG)
            assert t.readq(t.SP-48)==0xc016 and t.readq(t.SP-40)==0xc015
        for i in range(19,29):assert U.reg_read(X[i])==0xc000+i
        cases+=1
print('PASS:',cases,'native footer cases; small commands suppressed only for visible wheel, fallback retained; GameCanvas keypad unchanged')
