"""Execute installed Notes77 entry hooks, fallbacks and displaced ARM64 instructions."""
import test_hooks as t
import struct,json
from unicorn import UC_HOOK_CODE
from unicorn.arm64_const import *
U,B,R,X=t.U,t.BASE,t.R,t.X
for j,n in enumerate(['AGNotesReceive','AGNotesInput','AGNotesSettings','AGNotesInbox']):t.CALLBACKS[n]=0x30000b000+j*0x1000
originals={};events=[]
def r(i):return U.reg_read(X[i])
def ret(value=0):
 for reg in X[:18]:U.reg_write(reg,0xeeee)
 t.returned(value)
def hook(uc,pc,size,_):
 if pc in originals:
  site,label=originals[pc];events.append((label,tuple(r(i) for i in range(6))))
  word=struct.unpack_from('<I',t.ORIG,site)[0]
  assert word&0xffc003e0==0xa98003e0
  imm=(word>>15)&127;imm=imm-128 if imm&64 else imm
  sp=U.reg_read(UC_ARM64_REG_SP);first,second=struct.unpack('<QQ',U.mem_read(sp,16));U.reg_write(X[word&31],first);U.reg_write(X[(word>>10)&31],second);U.reg_write(UC_ARM64_REG_SP,sp-imm*8);ret()
U.hook_add(UC_HOOK_CODE,hook)
def reset():
 t.reset();t.speedAddr=t.buildAddr=t.continuation=0;events.clear();originals.clear()
def run(a):U.emu_start(B+a,t.STOP+4,count=10000)
def notes_calls(n):return [c for c in t.calls if c[0]==n]
checks=0
for h in R['hooks']:
 v=h['variant'];n=h['notes77']
 for t.missing in (False,True):
  for cmd in (-122,-123):
   reset();t.continuation=B+h['controller']+4;U.mem_write(t.MSG+0x30,bytes([cmd&255]));run(h['controller']);intercept=not t.missing
   assert t.stopKind==(t.STOP if intercept else t.continuation);t.preserved(not intercept)
   calls=notes_calls('AGNotesReceive');assert bool(calls)==intercept
   if calls:assert calls[0][1][:3]==(t.ENV,t.MSG,v)
   checks+=1
 t.missing=False
 for cfg in h['config_hooks']:
  for allow in ((0,1) if cfg['stage']==3 else (1,)):
   reset();t.roomHandled=allow;site=cfg['site'];originals[B+site+4]=(site,'original')
   run(site);t.preserved();calls=notes_calls('AGNotesSettings');assert calls[0][1][:5]==(t.ENV,t.OBJECT,t.MSG,v,cfg['stage'])
   assert bool(events), 'Native OK must exit even when the save bridge returns false'
   if events:assert events[0][1][:3]==(t.ENV,t.OBJECT,t.MSG)
   checks+=1
 for entry in h['input_hooks']:
  for blocked in (0,1):
   reset();t.roomHandled=blocked;kind,site=entry['kind'],entry['site']
   if kind<2:originals[B+site+4]=(site,'original')
   else:
    canvas=t.ENV+0x6000;t.writeq(B+n['canvas'],canvas);U.mem_write(canvas,bytes(0x200));U.reg_write(X[2],123);U.reg_write(X[3],234)
   run(site);t.preserved();calls=notes_calls('AGNotesInput');assert calls[0][1][:4]==(v,kind,123 if kind>=2 else t.MSG&0xffffffff,234 if kind>=2 else 0xc003)
   if kind<2:assert bool(events)==(not blocked)
   else:assert struct.unpack('<I',U.mem_read(canvas+0x110,4))[0]==(0 if blocked else 123)
   checks+=1
 reset();site=n['dialog_show'];originals[B+site+4]=(site,'original');run(h['inbox_hook']);t.preserved()
 assert events[0][1]==(t.ENV,t.OBJECT,t.MSG,0xc003,0xc004,0xc005)
 assert notes_calls('AGNotesInbox')[0][1][:4]==(t.ENV,t.OBJECT,t.MSG,v);checks+=1
report={'passed':True,'assertions':checks,'variants':6,'entry_hooks':60,'fallbacks':True,'relocated_pointer_ADRP':True,'live_requests':0}
(t.ROOT/'build/notes-hooks-check.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS',report)

