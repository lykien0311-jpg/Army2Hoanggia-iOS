"""Run the actual room sprite call, not the old coordinate-only helper.

IDs are cross-checked against the shipped FightManager boss constructors.
The actual native renderer receives the selected ID with its coordinates and
other arguments unchanged. The two old coordinate patch sites stay intact.
"""
import test_hooks as t
from unicorn import UC_HOOK_CODE
from unicorn.arm64_const import *
U=t.U;B=t.BASE;X=t.X
expected={3:12,4:12,5:13,6:14,7:15,8:16,9:16,10:17,11:22,12:25,13:26,16:15}
events=[];renderer=0
def hook(uc,pc,size,_):
    if pc==renderer:
        events.append(tuple(U.reg_read(r) for r in X[:11]));uc.emu_stop()
U.hook_add(UC_HOOK_CODE,hook)
cases=0
for m,turn in zip(t.R['boss_hooks'],t.R['turn_map']):
    for site in turn['boss_sites']:assert t.B[site:site+4]==t.ORIG[site:site+4]
    for room in [-1,0,1,2,*range(3,18),255]:
        for stage in [12,15,26]:
            t.reset();events.clear();globals=t.ENV+0x7000
            t.writeq(B+m['room_class'],globals);U.mem_write(globals+0x130,bytes([room&255]))
            U.reg_write(X[2],stage);U.reg_write(UC_ARM64_REG_NZCV,0xa0000000)
            before=tuple(U.reg_read(r)for r in X[:11]);renderer=B+m['boss_renderer']
            U.emu_start(B+m['boss_call'],t.STOP+4,count=1000)
            assert len(events)==1
            after=events[0];assert after[2]==expected.get(room,stage),(m['variant'],room,after[2])
            assert after[:2]+after[3:]==before[:2]+before[3:]
            assert U.reg_read(UC_ARM64_REG_NZCV)==0xa0000000
            assert U.reg_read(UC_ARM64_REG_SP)==t.SP
            assert U.reg_read(UC_ARM64_REG_LR)==B+m['boss_call']+4
            cases+=1
print('PASS:',cases,'real sprite-call cases across six variants; UFO 8/9=16, Super Boss 16=Trex15; linked stages and coordinates preserved')

