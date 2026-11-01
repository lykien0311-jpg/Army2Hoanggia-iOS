"""Run native inventory/shop input with the real Apple grid bridge."""
import test_device_bridge as t
import json,struct
from unicorn import UC_HOOK_CODE
from unicorn.arm64_const import *
U=t.u;B=t.MAIN;root=t.ROOT;X=[UC_ARM64_REG_X0+i for i in range(31)]
prepared=(root/'build/prepared-native').read_bytes();end=B+((len(prepared)+4095)&-4096)
last=max(e+1 for a,e,p in U.mem_regions()if B<=a<B+0x4000000)
if end>last:U.mem_map(last,end-last);last=end

import lief
pm=lief.MachO.parse(str(root/'build/prepared-native')).at(0)
for seg in pm.segments:
 if seg.name!='__PAGEZERO' and seg.file_size:
  end=(seg.virtual_address+seg.virtual_size+4095)&-4096
  if end>last:U.mem_map(last,end-last);last=end
  U.mem_write(seg.virtual_address,prepared[seg.file_offset:seg.file_offset+seg.file_size])
report=json.load(open(root/'build/hook-report.json'));grid=json.load(open(root/'grid-map.json'))['sites'];notes=json.load(open(root/'notes-map.json'))
raw=(root.parent/'validation/inspect-ipa/Army2Hoanggia').read_bytes()
def q(a):return struct.unpack_from('<Q',raw,a)[0]
def string(p):return raw[p-B:p-B+150].split(b'\0')[0].decode(errors='replace')if B<p<B+len(raw)else ''
def methods(clazz):
 out={}
 for a in range(clazz,clazz+0x1400,8):
  name=string(q(a));code=q(a+16);size=q(a+24)
  if name in ['j','l','n']and B+0x400000<code<B+0xb00000 and 4<=size<0x10000 and name not in out:out[name]=(code,size)
 return out
# Match the array in GridMap.h to the audited class references.
import re
h=(root/'GridMap.h').read_text().split('gridClasses[6][3]=')[1]
classes=[[int(x,16)for x in re.findall('0x[0-9a-f]+',line)]for line in h.splitlines()if '{0x'in line]
can=t.alloc(0x200);screen=t.alloc(0x200);keys=t.alloc(0x80);vec=t.alloc(0x80);regs=t.alloc(0x100)
t.put(keys+0x10,'<I',32);t.put(vec+0x24,'<I',70)
width=432;height=640;px=py=oldy=0;tap=drag=0;active=(0,0);primitives={}
def r(i):return U.reg_read(X[i])
def call(addr,*args):
 U.reg_write(UC_ARM64_REG_SP,t.STACK+0x30000);U.reg_write(UC_ARM64_REG_LR,t.STOP)
 for i,x in enumerate(args):U.reg_write(X[i],x&((1<<64)-1))
 try:U.emu_start(addr,t.STOP+4,count=100000)
 except Exception:
  print('FAIL PC',hex(U.reg_read(UC_ARM64_REG_PC)), 'LR',hex(U.reg_read(UC_ARM64_REG_LR)), 'active',active,'context',v,kind,width,height,'tap',tap,'pointer',px,py);raise
 assert U.reg_read(UC_ARM64_REG_PC)==t.STOP

def hook(u,pc,size,_):
 if pc==B+report['dlsym']:
  name=bytes(U.mem_read(r(1),100)).split(b'\0')[0].decode();t.ret(t.symbols['_'+name]);return
 # Calls made by a native input handler to its Java/graphics helpers are
 # mocked. All handler arithmetic, branches, loads and injected hooks run.
 if B<=pc<B+report['rxvm'] and not(active[0]<=pc<active[0]+active[1]):
  lr=U.reg_read(UC_ARM64_REG_LR);caller=lr-4
  if active[0]<=caller<active[0]+active[1]:
   name=primitives.get(pc,'skip')
   if name=='keys':value=keys
   elif name=='size':value=70
   elif name=='width':value=width
   elif name=='height':value=height
   elif name=='tap':value=tap
   elif name=='drag':value=drag
   elif name=='px':value=px
   elif name=='py':value=py
   elif name=='oldy':value=oldy
   elif name=='hit':
    def signed(x):return struct.unpack('<i',struct.pack('<I',x&0xffffffff))[0]
    x,y,w,h=map(signed,[r(1),r(2),r(3),r(4)]);value=int(x<=px<x+w and y<=py<y+h)
   elif name=='abs':value=abs(struct.unpack('<i',struct.pack('<I',r(1)&0xffffffff))[0])
   else:value=0
   t.ret(value)
U.hook_add(UC_HOOK_CODE,hook)
def target(a):
 w=struct.unpack_from('<I',raw,a)[0];d=w&0x3ffffff;assert w&0xfc000000==0x94000000
 return B+a+4*(d-(1<<26)if d&(1<<25)else d)
# Method maps and input primitives are identified by native getter code, not
# by the supplied layout's arithmetic.
anchors={0x1dfce8:'size',0x50bf38:'keys',0x50c0e0:'width',0x50bec0:'height',0x50c068:'tap',0x50c0a4:'drag',0x50b950:'px',0x50c158:'py',0x50c11c:'oldy',0x50c1f0:'hit',0xaa6f80:'abs'}
# The six corresponding getters have stable tails. Derive each through the
# original native instructions in the handler at known call-site offsets.
baseMethods=[methods(c)['j']for c in classes[0]]
baseCalls=[]
for start,size in baseMethods:
 d={}
 for a in range(start-B,start-B+size,4):
  w=struct.unpack_from('<I',raw,a)[0]
  if w&0xfc000000==0x94000000:
   dest=target(a)-B
   if dest in anchors:d[a-(start-B)]=anchors[dest]
 baseCalls.append(d)
cases=0
for v,cl in enumerate(classes):
 globals=[t.alloc(0x200)for _ in range(3)]
 for c,g in zip(cl,globals):t.put(B+c,'<Q',g);t.put(g+0xa8,'<Q',vec)
 t.put(B+notes[v]['canvas'],'<Q',can);t.put(can+0xb8,'<Q',screen)
 for kind,c in enumerate(cl):
  fn=methods(c)['j'];primitives={target(fn[0]-B+off):name for off,name in baseCalls[kind].items()}
  for width,height in [(240,320),(320,480),(432,640),(640,432)]:
   U.mem_write(screen,bytes(0x200));t.put(screen,'<Q',globals[kind]);t.put(can+0x130,'<I',width);t.put(can+0x128,'<I',height)
   t.put(screen+(0x70 if kind in [0,1]else 0x78),'<Q',vec)
   t.put(screen+(0xbc if kind==0 else 0xb0 if kind==1 else 0xb8),'<I',70)
   layoutSite=next(s for s in grid if s['variant']==v and s['kind']==kind and s['metric']=='LAYOUT')
   U.mem_write(regs,bytes(0x100));t.put(regs+8,'<Q',screen)
   active=(0,0);call(t.symbols['_AGGridAdjust'],regs,B+layoutSite['site'])
   x=t.get(screen+0x50,'<i');y=t.get(screen+0x54,'<i');w=t.get(screen+0x58,'<i');hh=t.get(screen+0x5c,'<i')
   assert 0<=x<width and w<=width and y+hh<=height and w>width*.70
   cols=t.get(screen+0xc0,'<i')if kind==0 else t.get(globals[kind]+0xb0,'<i')
   cell=t.get(screen+0xb8,'<i')if kind==0 else t.get(globals[kind]+0xb8,'<i')
   assert 3<=cols<=7 and cols*cell<=w-24
   cases+=1
   # Run left/right and up/down through the original handler, not a copied
   # selection formula. These indices straddle row boundaries.
   selectedOff=0xc8 if kind==0 else 0xa8 if kind==1 else 0xb0
   for key,start,expected in [(4,7,6),(6,6,7),(8,7,7+cols),(2,cols,0)]:
    U.mem_write(keys+0x14,bytes(32));t.put(keys+0x14+key,'<B',1);t.put(screen+selectedOff,'<I',start)
    active=fn;tap=drag=0;call(fn[0],t.ENV,screen)
    assert t.get(screen+selectedOff,'<I')==expected,(v,kind,width,key,t.get(screen+selectedOff,'<I'),expected)
    cases+=1
   # Native pointer selection uses the dynamic cell and columns, including
   # the formerly unreachable rightmost column and rows after scrolling.
   for row,col,scroll in [(0,cols-1,0),(1,0,0),(4,cols-1,cell*3)]:
    U.mem_write(keys+0x14,bytes(32));t.put(globals[kind]+(0xa8 if kind==0 else 0xc4),'<i',scroll);t.put(globals[kind]+(0xac if kind==0 else 0xc8),'<i',scroll)
    px=x+4+col*cell+cell//2;py=y+20+(row*cell-scroll)+cell//2;oldy=py
    if py<y+20:continue
    tap=1;drag=0;active=fn;call(fn[0],t.ENV,screen);expected=row*cols+col
    assert t.get(screen+selectedOff,'<I')==expected,(v,kind,width,'touch',px,py,t.get(screen+selectedOff,'<I'),expected)
    cases+=1
   if kind>0:
    # Resizing recalculates the row count/scroll bound, then a real native
    # drag reaches that bound instead of stopping at the former 40px grid.
    tap=0;drag=0;active=(0,0);call(t.symbols['_AGInventoryTick'],v)
    limit=t.get(globals[kind]+0xd4,'<i')
    assert limit==max(0,((70+cols-1)//cols)*cell-(hh-110))
    U.mem_write(keys+0x14,bytes(32));oldy=3000;py=0;drag=1;active=fn;call(fn[0],t.ENV,screen)
    assert t.get(globals[kind]+0xc4,'<i')==limit,(v,kind,width,'drag',t.get(globals[kind]+0xc4,'<i'),limit)
    cases+=1
print('PASS:',cases,'Apple/native grid layout, keyboard and pointer selection cases across six variants and four screen sizes')
