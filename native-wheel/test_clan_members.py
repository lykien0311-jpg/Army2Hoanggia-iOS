"""Run all six native packet-118 member parsers against the server wire format."""
import io,json,struct,sys
from pathlib import Path
from unicorn import *
from unicorn.arm64_const import *
from keystone import *
ROOT=Path(__file__).resolve().parent
raw=(ROOT.parent/'validation/inspect-ipa/Army2Hoanggia').read_bytes();sites=json.loads((ROOT/'clan-members-map.json').read_text());ks=Ks(KS_ARCH_ARM64,KS_MODE_LITTLE_ENDIAN)
B=0x100000000;D=0x600000000;S=0x700000000

def utf(s):b=s.encode();return struct.pack('>H',len(b))+b

def check(site,count,page,patched):
 data=bytearray(raw)
 if patched:data[site:site+4]=bytes(ks.asm('bl 0xa64208',site)[0])
 u=Uc(UC_ARCH_ARM64,UC_MODE_ARM);u.mem_map(B,(len(data)+4095)&-4096);u.mem_write(B,bytes(data));u.mem_map(D,0x200000);u.mem_map(S,0x40000)
 delta=site-0x52cc4c;cursor=D+0x1000;objects=[];appended=[]
 def put(a,f,*v):u.mem_write(a,struct.pack(f,*v))
 def alloc():
  nonlocal cursor
  p=cursor;cursor+=0x400;return p
 def r(i):return u.reg_read(UC_ARM64_REG_X0+i)
 def read(n):
  b=wire.read(n)
  if len(b)!=n:raise EOFError('member record misaligned')
  return b
 payload=bytes([page])+utf('BIỆT ĐỘI')
 for i in range(count):payload+=struct.pack('>i',900+i)+utf('Thành viên '+str(i))+struct.pack('>iBBqBhI5h',1,i%10,i%2,999,99,page*10+i,14405600,1,2,3,4,5)+utf('Chưa đóng góp')+utf('')
 wire=io.BytesIO(payload)
 fp=S+0x30000;put(fp-0x60,'<Q',D+0x100);u.reg_write(UC_ARM64_REG_X29,fp);u.reg_write(UC_ARM64_REG_SP,fp-0x1030);u.reg_write(UC_ARM64_REG_X28,D)
 def hook(u,pc,size,_):
  a=pc-B
  if a==0x52fc6c+delta:u.emu_stop();return
  word=struct.unpack_from('<I',data,a)[0]
  if word&0xfc000000!=0x94000000:return
  disp=word&0x3ffffff;target=a+4*(disp-(1<<26)if disp&(1<<25)else disp)
  if target in (0xa63e54,0xa64274):value=read(1)[0]
  elif target==0xa64208:value=struct.unpack('>h',read(2))[0]&0xffffffff
  elif target==0xa63fa8:value=struct.unpack('>I',read(4))[0]
  elif target==0xa6419c:value=struct.unpack('>Q',read(8))[0]
  elif target==0xa642f0:read(struct.unpack('>H',read(2))[0]);value=alloc()
  elif target==0xa6c7c8:value=len(payload)-wire.tell()
  elif a==0x52c854+delta:
   value=alloc();objects.append(value);outer=alloc();put(value+0x18,'<Q',outer);put(outer+0x10,'<I',10)
   for j in range(10):inner=alloc();put(inner+0x10,'<I',5);put(outer+0x18+j*8,'<Q',inner)
  elif target==0x1dfcac:appended.append(r(2));value=0
  elif target==0x12e7cc8:value=alloc();put(value+0x10,'<I',5)
  else:value=alloc()
  u.reg_write(UC_ARM64_REG_X0,value);u.reg_write(UC_ARM64_REG_PC,pc+4)
 u.hook_add(UC_HOOK_CODE,hook);u.emu_start(B+0x52c608+delta,B+0x52fc70+delta,count=300000)
 assert u.reg_read(UC_ARM64_REG_PC)==B+0x52fc6c+delta
 assert wire.tell()==len(payload) and appended==objects and len(objects)==count
 for i,p in enumerate(objects):assert struct.unpack('<II',u.mem_read(p+0xc8,8))==(14405600,page*10+i)

cases=0
for site in sites:
 for count,page in [(0,0),(1,0),(10,0),(10,12),(10,25),(10,30)]:check(site,count,page,True);cases+=1
 try:check(site,1,0,False)
 except (EOFError,AssertionError,UcError):pass
 else:raise AssertionError('original parser must fail server fixture')
print('PASS:',cases,'native member-list packet fixtures; original fails all six variants')
