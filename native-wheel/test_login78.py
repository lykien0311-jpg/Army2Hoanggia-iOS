"""Execute six actual ARM64 login methods, with JVM/transport endpoints simulated."""
import test_hooks as t
import json,struct
from unicorn import UC_HOOK_CODE
from unicorn.arm64_const import *
U,B,X=t.U,t.BASE,t.X
M=json.loads((t.ROOT/'login-map.json').read_text())
objects={};writes=[];opcodes=[];sent=[];handlers={}
next_object=t.ENV+0x8000

def text_object(s):
 global next_object
 p=next_object;next_object+=0x100;objects[p]=s;U.mem_write(p,bytes(0x100));return p

def branch(a):
 w=struct.unpack_from('<I',t.B,a)[0];assert w&0xfc000000==0x94000000
 n=w&0x3ffffff;return a+4*(n-(1<<26) if n&(1<<25) else n)

def hook(uc,pc,size,_):
 if pc==B+0x12e8038:
  s=t.string(U.reg_read(X[2]));assert len(s.encode('utf-16-le'))//2==U.reg_read(X[3]);p=text_object(s);t.writeq(U.reg_read(X[1]),p);t.returned(p)
 elif pc==B+M['write_utf']:
  assert U.reg_read(X[0])==t.ENV and U.reg_read(X[1])==t.ENV+0x5000
  writes.append(objects[U.reg_read(X[2])]);t.returned()
 elif pc in handlers:
  kind=handlers[pc]
  if kind=='alloc':t.returned(t.MSG)
  elif kind=='ctor':opcodes.append(U.reg_read(X[2]));t.returned()
  elif kind=='writer':t.returned(t.ENV+0x5000)
  elif kind=='send':sent.append(U.reg_read(X[2]));t.returned()
  else:t.returned()
U.hook_add(UC_HOOK_CODE,hook)
t.continuation=t.speedAddr=t.buildAddr=0
packets=[];checks=0
for i,v in enumerate(M['variants']):
 a=v['entry']
 handlers={B+0x1300d54:'enter',B+0x12e76d8:'leave'}
 for offset,kind in ((0x7c,'alloc'),(0x98,'ctor'),(0xa8,'writer'),(0x204,'send'),(0x218,'close')):handlers[B+branch(a+offset)]=kind
 for patched in (False,True):
  site=v['utf_calls'][2]
  original=t.ORIG[site:site+4];U.mem_write(B+site,t.B[site:site+4] if patched else original);U.ctl_remove_cache(B+a,B+v['end'])
  for user,password in [('probeuser','pass1234'),('kiên','mật khẩu 78')]:
   t.reset();objects.clear();writes.clear();opcodes.clear();sent.clear();next_object=t.ENV+0x8000
   U.mem_write(t.ENV+0x5000,bytes(0x100));t.writeq(t.OBJECT+0x10,t.ENV+0x6000)
   U.reg_write(X[2],text_object(user));U.reg_write(X[3],text_object(password));U.reg_write(X[4],text_object('2.4.0'))
   U.emu_start(B+a,t.STOP+4,count=20000);t.preserved()
   assert writes==[user,password,'2.4.1-HG78-IPA' if patched else '2.4.0','z1'],writes
   assert opcodes==[1] and sent==[t.MSG]
   checks+=1
   if patched:packets.append({'variant':i,'fields':writes.copy()})
  U.mem_write(B+site,t.B[site:site+4])
# Run the actual version-string getter, proving the in-game display is 2.4.1.
t.reset();U.emu_start(B+M['literal_getter'],t.STOP+4,count=1000)
assert objects[U.reg_read(X[0])]=='2.4.1';checks+=1
r={'passed':True,'actual_native_login_cases':checks,'variants':6,'old_login_marker':'2.4.0','new_login_marker':'2.4.1-HG78-IPA','display_version':'2.4.1','credentials_and_platform_tail_unchanged':True,'boundary_dependencies':'JVM strings and transport simulated','live_server_login':False,'packets':packets}
(t.ROOT/'build/login78-check.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print('PASS',checks,'native login/version cases, all six variants')
