"""Run compiled iPhone inventory bridge; OS/JNI and selection paint are mocked."""
from pathlib import Path
import struct,sys,functools
import lief
from unicorn import Uc,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm64_const import *
p=Path(sys.argv[1]);blob=p.read_bytes();m=lief.MachO.parse(str(p)).at(0)
L=0x200000000;B=0x100000000;H=0x600000000;F=0x400000000;S=0x700000000;STOP=F+0x30000
u=Uc(UC_ARCH_ARM64,UC_MODE_ARM)
for seg in m.segments:
 if seg.virtual_size:u.mem_map(L+seg.virtual_address,(seg.virtual_size+4095)&-4096);u.mem_write(L+seg.virtual_address,blob[seg.file_offset:seg.file_offset+seg.file_size])
u.mem_map(B,0x3000000);u.mem_map(H,0x800000);u.mem_map(F,0x40000);u.mem_map(S,0x40000)
symbols={s.name:L+s.value for s in m.symbols if s.value}
def put(a,f,*v):u.mem_write(a,struct.pack(f,*v))
def get(a,f):return struct.unpack(f,u.mem_read(a,struct.calcsize(f)))[0]
for rel in m.relocations:
 if rel.size==64 and int(rel.type)==1:put(L+rel.address,'<Q',get(L+rel.address,'<Q')+L)
names={};imports={}
for binding in m.dyld_info.bindings:
 name=binding.symbol.name
 if name not in names:names[name]=F+len(names)*256;imports[names[name]]=name
 put(L+binding.address,'<Q',names[name])
cursor=H+0x10000

def alloc(n):
 global cursor
 p=cursor;cursor+=(n+31)&-16;assert cursor<H+0x800000;u.mem_write(p,bytes(n));return p
E=H;JNI=H+0x1000;put(E,'<Q',JNI)
ENTER=F+0x20000;LEAVE=ENTER+0x100;put(JNI+217*8,'<Q',ENTER);put(JNI+218*8,'<Q',LEAVE)
regs=[UC_ARM64_REG_X0+i for i in range(31)]
def reg(i):return u.reg_read(regs[i])
def ret(n=0):u.reg_write(UC_ARM64_REG_X0,n&((1<<64)-1));u.reg_write(UC_ARM64_REG_PC,u.reg_read(UC_ARM64_REG_LR))
locks=0;refreshes=[]
pools=[0x2094ac0,0x20c34f0,0x20f11e0,0x211eed0,0x214cbc0,0x217a8b0]
classes=[0x2091350,0x20c0000,0x20edcf0,0x211b9e0,0x21496d0,0x21773c0]
canvases=[0x207dac0,0x20ad740,0x20db440,0x2109130,0x2136e20,0x2164b10]
refresh=[0x592220,0x67b7dc,0x7604a0,0x845164,0x929e28,0xa0eaec]

def row_sort_key(raw,cmp):
 key,qty,item,group,id,rank,fresh=struct.unpack('<QqQiiii',raw)
 if cmp==symbols['_byKey']:return (key,)
 if cmp==symbols['_grouped']:return (group,id if group else 0,rank)
 assert cmp==symbols['_updated'];return (-fresh,rank)

def hook(_,pc,size,data):
 global locks
 if pc==STOP:u.emu_stop();return
 if pc==ENTER:locks+=1;ret();return
 if pc==LEAVE:locks-=1;assert locks==0;ret();return
 if pc==B+0x1300d54:put(reg(1),'<Q',get(E+0x38,'<Q'));put(E+0x38,'<Q',reg(1));ret();return
 if pc in [B+a for a in refresh]:refreshes.append((pc,reg(1)));ret(1);return
 if pc not in imports:return
 name=imports[pc]
 if name=='__dyld_get_image_header':ret(B)
 elif name=='_malloc':ret(alloc(reg(0)))
 elif name=='_calloc':ret(alloc(reg(0)*reg(1)))
 elif name=='_free':ret()
 elif name in ['_memcpy','_memmove']:u.mem_write(reg(0),bytes(u.mem_read(reg(1),reg(2))));ret(reg(0))
 elif name in ['_memset','_bzero']:
  u.mem_write(reg(0),bytes([reg(1)&255])*reg(2)if name=='_memset'else bytes(reg(1)));ret(reg(0))
 elif name=='_qsort':
  ptr,n,sz,cmp=[reg(i)for i in range(4)];assert sz==40
  rows=[bytes(u.mem_read(ptr+i*sz,sz))for i in range(n)];rows.sort(key=lambda raw:row_sort_key(raw,cmp));u.mem_write(ptr,b''.join(rows));ret()
 elif name=='_bsearch':
  wanted=get(reg(0),'<Q');ptr,n,sz=reg(1),reg(2),reg(3);ret(next((ptr+i*sz for i in range(n)if get(ptr+i*sz,'<Q')==wanted),0))
 else:raise AssertionError(('unexpected import',name))
u.hook_add(UC_HOOK_CODE,hook)
def call(name,*args):
 u.reg_write(UC_ARM64_REG_SP,S+0x30000);u.reg_write(UC_ARM64_REG_LR,STOP)
 for i,v in enumerate(args):u.reg_write(regs[i],v)
 u.emu_start(symbols[name],STOP+4,count=1000000)
 assert u.reg_read(UC_ARM64_REG_PC)==STOP and locks==0
 return reg(0)
def item(id,quantity=1,equipment=False):
 p=alloc(0xd0);put(p+0xbd,'<B',not equipment);put(p+0x80,'<q',id);put(p+0x90,'<q',quantity);put(p+0xb0,'<I',id if equipment else 0);return p
def vector(rows):
 a=alloc(0x18+8*len(rows));put(a+0x10,'<I',len(rows))
 for i,p in enumerate(rows):put(a+0x18+8*i,'<Q',p)
 v=alloc(0x30);put(v+0x10,'<Q',a);put(v+0x24,'<I',len(rows));return v

def ids(v):
 a=get(v+0x10,'<Q');return [get(get(a+0x18+8*i,'<Q')+0x80,'<q')for i in range(get(v+0x24,'<I'))]
for v in range(6):
 canvas=alloc(0x180);screen=alloc(0xe0);clazz=alloc(0x180);pool=alloc(0xc0)
 put(B+canvases[v],'<Q',canvas);put(canvas+0xb8,'<Q',screen);put(screen,'<Q',clazz);put(B+classes[v],'<Q',clazz);put(B+pools[v],'<Q',pool);put(clazz+0xa0,'<Q',screen)
 put(canvas+0x130,'<i',432);put(screen+0x50,'<i',19);put(screen+0x54,'<i',68);put(screen+0x58,'<i',408);put(screen+0x5c,'<i',520);put(screen+0xc0,'<i',7);put(screen+0xb8,'<i',54)
 geometry=alloc(28);assert call('_AGInventoryGeometry',v,geometry)==1;assert struct.unpack('<7i',u.mem_read(geometry,28))==(432,12,68,408,520,7,54)
 rows=[item(104,5),item(70001,equipment=True),item(7,99),item(120,1)];vec=vector(rows);put(pool+0xa8,'<Q',vec);put(screen+0x70,'<Q',vec);put(screen+0x90,'<Q',rows[0])
 call('_AGInventoryOrder',E,v,canvas,screen,1);assert ids(vec)==[70001,7,104,120]
 assert get(screen+0x90,'<Q')==rows[1]
 fresh=[item(70001,equipment=True),item(7,99),item(105,1),item(120,1)];nextvec=vector(fresh);put(pool+0xa8,'<Q',nextvec)
 put(canvas+0x108,'<Q',123);call('_AGInventoryOrder',E,v,canvas,screen,1);assert get(screen+0x70,'<Q')==vec
 put(canvas+0x108,'<Q',0);call('_AGInventoryOrder',E,v,canvas,screen,1);assert get(screen+0x70,'<Q')==nextvec and ids(nextvec)==[105,70001,7,120]
 assert get(screen+0x90,'<Q')==fresh[2]and get(fresh[2]+0x90,'<q')==1
 # Selected recipe must resolve into the next server vector at action time.
 put(screen+0xc8,'<i',3);put(screen+0x90,'<Q',fresh[3]);newpaper=item(120,1);replacement=vector([fresh[0],newpaper,fresh[2],fresh[1]]);put(pool+0xa8,'<Q',replacement)
 assert call('_AGInventoryResolve',E,fresh[3])==newpaper
 assert get(screen+0x70,'<Q')==replacement and get(screen+0xc8,'<i')==1 and get(screen+0x90,'<Q')==newpaper
 call('_AGInventoryOrder',E,v,canvas,screen,0);call('_AGInventoryOrder',E,v,canvas,screen,1);assert ids(replacement)==[70001,7,105,120]
 assert any(pc==B+refresh[v]for pc,s in refreshes)
 # Simulate 100 refreshes while keeping template IDs and handles unchanged.
 for turn in range(100):
  put(fresh[1]+0x90,'<q',100+turn);call('_AGInventoryOrder',E,v,canvas,screen,1);assert ids(replacement)[0]==7
print('PASS compiled ARM64 bridge: all six variants, 600 updates, vector replacement, dialog deferral, recipe re-resolution, reopen sorting and selected-item refresh')
