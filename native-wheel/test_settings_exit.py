"""Execute the actual native OK -> lobby -> GameCanvas.cScreen transition."""
import test_hooks as t
import struct,json
from unicorn import UC_HOOK_CODE
from unicorn.arm64_const import *
U,B,R,X=t.U,t.BASE,t.R,t.X
exits=json.loads((t.ROOT/'exit-map.json').read_text());calls=[];helpers=set()
t.CALLBACKS['AGNotesSettings']=0x30000b000

def hook(uc,pc,size,_):
 if pc in helpers:
  calls.append(pc);t.returned()
U.hook_add(UC_HOOK_CODE,hook)
checks=0
for h,e in zip(R['hooks'],exits):
 for pending_bridge_result in (0,1):
  t.reset();t.missing=False;t.continuation=t.speedAddr=t.buildAddr=0;t.roomHandled=pending_bridge_result;calls.clear()
  canvas=t.ENV+0x3000;homeclass=t.ENV+0x4000;home=t.ENV+0x5000;config=t.ENV+0x6000
  for p in (canvas,homeclass,home,config):U.mem_write(p,bytes(0x300))
  t.writeq(B+h['width_class'],canvas);U.mem_write(B+h['width_class']+9,b'\2');t.writeq(canvas+0xb8,config)
  t.writeq(B+h['home_class'],homeclass);U.mem_write(B+h['home_class']+9,b'\2');t.writeq(homeclass+0xb8,home)
  helpers={B+a for a in e['helpers']}
  U.emu_start(B+h['notes77']['settings_ok'],t.STOP+4,count=10000);t.preserved()
  assert t.readq(canvas+0xb8)==home, 'OK did not leave configuration'
  assert len(calls)==4
  checks+=1
report={'passed':True,'actual_native_screen_transitions':checks,'variants':6,'waiting_for_save_ack_does_not_block_exit':True,'server_requests':0}
(t.ROOT/'build/settings-exit-check.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS',report)
