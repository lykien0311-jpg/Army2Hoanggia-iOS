"""Exercise the Apple-built UFO protocol and original fire entry, without a server."""
import test_device_bridge as t
import json,struct
from unicorn import UC_HOOK_CODE
from unicorn.arm64_const import *
U=t.u;B=t.MAIN;X=[UC_ARM64_REG_X0+i for i in range(31)];R=json.load(open(t.ROOT/'turn-map.json'))
# Existing bridge fixture installs real Java exception guard, import shims and
# the verified game image. Only Java service access and final fire are mocked.
notes=json.load(open(t.ROOT/'notes-map.json'));shots=[];blocked=0
native={B+m['fire']:i for i,m in enumerate(R)}
def r(i):return U.reg_read(X[i])
def ret(v=0):t.ret(v)
def hook(u,pc,size,_):
 if pc in native:
  v=native[pc];p=r(1);assert r(0)==t.ENV
  shots.append((v,p,t.get(p+0xa4,'<h'),t.get(p+0x16d,'<B'),t.get(p+0x16e,'<B'),t.get(p+0x134,'<i')));ret()
 elif pc==t.symbols['_AGNotesBlocksAuto']:ret(blocked)
U.hook_add(UC_HOOK_CODE,hook)
def call(name,*args):
 U.reg_write(UC_ARM64_REG_SP,t.STACK+0x30000);U.reg_write(UC_ARM64_REG_LR,t.STOP)
 for i,x in enumerate(args):U.reg_write(X[i],x&((1<<64)-1))
 U.emu_start(t.symbols['_'+name],t.STOP+4,count=100000)
 assert U.reg_read(UC_ARM64_REG_PC)==t.STOP

def recv(v,cmd,wire):
 msg=t.alloc(0x40);stream=t.alloc(0x40);a=t.alloc(len(wire)+0x20)
 t.put(msg+0x20,'<Q',stream);t.put(msg+0x30,'<B',cmd&255)
 t.put(stream+0x10,'<Q',a);t.put(stream+0x18,'<I',len(wire));t.put(stream+0x20,'<I',0);t.put(a+0x10,'<I',len(wire));U.mem_write(a+0x14,wire)
 call('AGTurnReceive',t.ENV,msg,v)
 assert t.get(stream+0x20,'<I')==0,'Observer consumed native stream'

def turn(v,owner=2,num=8,ticket=987654):recv(v,24,bytes([owner])+struct.pack('>IiQ',1429485652,num,ticket))
def aim(v,owner=2,num=8,ticket=987654,angle=173,force=28,release=0,x=240,y=350):recv(v,-115,struct.pack('>iBQHBBhh',num,owner,ticket,angle,force,release,x,y))
cases=0
for v,m in enumerate(R):
 globals=t.alloc(0x400);pg=t.alloc(0x400);ag=t.alloc(0x200);canvas=t.alloc(0x200);arena=t.alloc(0x200);array=t.alloc(0x200);p=t.alloc(0x200)
 t.put(B+m['arena_class'],'<Q',globals);t.put(B+m['player_class'],'<Q',pg);t.put(B+m['array_class'],'<Q',ag);t.put(B+notes[v]['canvas'],'<Q',canvas)
 t.put(globals+0xe8,'<Q',arena);t.put(globals+0x266,'<B',2);t.put(ag+0xa0,'<Q',array);t.put(ag+0xd0,'<B',2);t.put(canvas+0xb8,'<Q',arena)
 t.put(array+0x10,'<I',8);t.put(array+0x18+16,'<Q',p)
 # A real first turn follows spawn/falling. Keep the old spawn position
 # different from the live coordinates, instead of populating only the
 # two stale fields as the previous fixture did.
 t.put(p+0x114,'<i',110);t.put(p+0x118,'<i',90)
 t.put(p+0x80,'<i',240);t.put(p+0x84,'<i',350)
 t.put(p+0xa6,'<H',0x55aa)
 t.put(t.SERVICE+0x10,'<Q',t.SESSION)
 recv(v,-115,struct.pack('>I',0x55464f01))
 for label,kw in [('normal',{}),('wrong turn',{'num':7}),('wrong owner',{'owner':1}),('wrong ticket',{'ticket':123}),('bad angle',{'angle':360}),('zero force',{'force':0}),('large force',{'force':31}),('large release',{'release':31}),('stale origin',{'x':241})]:
  turn(v);shots.clear();aim(v,**kw);call('AGTurnTick',t.ENV,v)
  assert bool(shots)==(label=='normal'),(v,label,shots)
  if shots:
   assert shots==[(v,p,173,28,0,0)]
   assert t.get(p+0x114,'<h')==240 and t.get(p+0x118,'<h')==350
   assert t.get(p+0xa6,'<H')==0x55aa,'angle write corrupted the adjacent native field'
   call('AGTurnTick',t.ENV,v);assert len(shots)==1
  cases+=1
 # Busy animation, captcha and dialog defer, then exactly one native fire.
 for target,off,fmt in [(pg,0x1a7,'<B'),(pg,0x1a8,'<B'),(p,0x166,'<B'),(p,0x16a,'<B'),(canvas,0x108,'<Q')]:
  turn(v);shots.clear();aim(v);t.put(target+off,fmt,1);call('AGTurnTick',t.ENV,v);assert not shots
  t.put(target+off,fmt,0);call('AGTurnTick',t.ENV,v);assert len(shots)==1;cases+=1
 turn(v);shots.clear();aim(v);blocked=1;call('AGTurnTick',t.ENV,v);assert not shots;blocked=0;call('AGTurnTick',t.ENV,v);assert len(shots)==1;cases+=1
 for label in ['manual','next turn','mode off','leave screen','connection','start match','other local']:
  recv(v,-115,struct.pack('>I',0x55464f01));turn(v);shots.clear();aim(v)
  if label=='manual':call('AGTurnManual',v)
  elif label=='next turn':turn(v,num=9,ticket=8765)
  elif label=='mode off':recv(v,-115,struct.pack('>I',0x55464f00))
  elif label=='leave screen':t.put(canvas+0xb8,'<Q',0)
  elif label=='connection':t.put(t.SERVICE+0x10,'<Q',t.SESSION+16)
  elif label=='start match':recv(v,20,b'')
  elif label=='other local':t.put(ag+0xd0,'<B',3)
  call('AGTurnTick',t.ENV,v);assert not shots,(v,label)
  t.put(canvas+0xb8,'<Q',arena);t.put(ag+0xd0,'<B',2);t.put(t.SERVICE+0x10,'<Q',t.SESSION);cases+=1
 # Unticketed and malformed turn/aim packets cannot establish a firing turn.
 for wire in [b'',b'\x02',bytes([2])+bytes(16),bytes([8])+struct.pack('>IiQ',1429485652,8,987654)]:
  recv(v,-115,struct.pack('>I',0x55464f01));recv(v,24,wire);shots.clear();aim(v);call('AGTurnTick',t.ENV,v);assert not shots;cases+=1
print('PASS:',cases,'Apple ARM64 UFO turn/ticket/native fire checks across six variants; duplicate, manual, captcha, stale aim, scene and connection guards')

