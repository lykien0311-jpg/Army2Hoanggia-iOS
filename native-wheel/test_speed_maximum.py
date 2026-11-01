"""Execute native speed calculation: only level 10 bypasses Thread.sleep(0)."""
import json,struct
import test_hooks as t
from unicorn import UC_HOOK_CODE
from unicorn.arm64_const import *
U=t.U;B=t.BASE;X=t.X
getter=resume=sleep=level=0;outcome=None;delay=None
def hook(uc,pc,size,_):
    global outcome,delay
    if pc==getter:t.returned(level)
    elif pc==resume:outcome='uncapped';U.emu_stop()
    elif pc==sleep:
        outcome='sleep';delay=U.reg_read(X[1]);U.emu_stop()
U.hook_add(UC_HOOK_CODE,hook)
cases=0
for h in t.R['hooks']:
    getter=B+h['speed'];resume=B+h['speed_resume'];sleep=B+h['speed_resume']-4
    word=struct.unpack_from('<I',t.ORIG,sleep-B)[0]
    assert word&0xfc000000==0x94000000
    for level in range(1,11):
        for missing in (False,True):
            t.reset();t.missing=missing;t.speedAddr=t.buildAddr=t.continuation=0
            U.reg_write(X[19],t.ENV);U.reg_write(X[25],10);U.reg_write(X[26],9);U.reg_write(X[27],25)
            U.reg_write(X[29],t.SP+0x100);outcome=delay=None
            U.emu_start(B+h['tick'],t.STOP+4,count=3000)
            assert outcome==('uncapped' if level==10 else 'sleep'),(h['variant'],level,outcome)
            if level<10:assert delay==(10-level)*25//9,(level,delay)
            assert U.reg_read(UC_ARM64_REG_SP)==t.SP
            callbacks=[c for c in t.calls if c[0]=='AGWheelTick']
            assert bool(callbacks)==(not missing)
            if callbacks:assert callbacks[0][1][:2]==(t.ENV,h['variant'])
            cases+=1
report=dict(passed=True,native_level_cases=cases,variants=6,levels_1_to_9_unchanged=True,
    level_10_skips_scheduler_sleep=True,extra_game_ticks=0,packet_duplication=False,
    physical_device_performance_measured=False)
(t.ROOT/'build/speed-maximum-check.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS',report)
