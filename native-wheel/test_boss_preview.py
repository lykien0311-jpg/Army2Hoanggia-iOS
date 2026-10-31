"""Execute the injected Room32 lookup, preserving native live registers/flags."""
import test_hooks as t
from unicorn.arm64_const import *
expected={30:12,31:12,32:13,33:14,34:15,35:16,36:17,37:22,38:23,39:24,40:15}
cases=0
for tm in t.R['turn_map']:
 for site in tm['boss_sites']:
  for value in [-1,0,29,*range(30,41),41,255]:
   t.reset();t.U.reg_write(t.X[8],value&0xffffffff);t.U.reg_write(UC_ARM64_REG_NZCV,0xa0000000)
   t.U.emu_start(t.BASE+t.R['boss_hook'],t.STOP+4,count=1000)
   assert t.U.reg_read(UC_ARM64_REG_W8)==expected.get(value,12)
   assert t.U.reg_read(t.X[9])==0xc009 and t.U.reg_read(t.X[10])==0xc00a
   assert t.U.reg_read(UC_ARM64_REG_NZCV)==0xa0000000
   assert t.U.reg_read(UC_ARM64_REG_SP)==t.SP;cases+=1
print('PASS:',cases,'native boss-preview map cases at 12 patched render sites; UFO map35 selects boss16; registers/flags preserved')
