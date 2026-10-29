"""Real Notes77 raster/wire fixtures, generated offline from the supplied server.jar."""
from pathlib import Path
import ctypes as C,struct,random,json
R=Path(__file__).resolve().parent;D=R.parent/'fixtures/data'
class Packet(C.Structure):
 _fields_=[(n,C.c_int) for n in 'kind status boss type required failures'.split()]+[('expires',C.c_uint64),('g',C.c_uint16*22),('d',C.c_uint16*7),('nonceLength',C.c_uint16),('nonce',C.c_uint8*1024),('text',C.c_char*4096),('imageLength',C.c_uint32),('pieceLength',C.c_uint32),('image',C.c_uint8*24000),('piece',C.c_uint8*24000)]
class State(C.Structure):
 _fields_=[('packet',Packet)]+[(n,C.c_int) for n in 'boss inRoom active waiting op used focus'.split()]+[('selected',C.c_int*8)]+[(n,C.c_int) for n in 'x y placed rotation dragging grabX grabY down rotationTouch rotationMoved rotationX lastKey'.split()]+[('waitSince',C.c_double),('blinkSince',C.c_double),('serial',C.c_uint64),('notice',C.c_char*512)]
lib=C.CDLL(str(R/'build/libnotesprotocol.so'))
lib.AGNotesParse.argtypes=[C.c_void_p,C.c_size_t,C.c_int,C.POINTER(Packet)]
lib.AGCaptchaInit.argtypes=[C.POINTER(State)]
lib.AGCaptchaContext.argtypes=[C.POINTER(State),C.c_int,C.c_int]
lib.AGCaptchaReceive.argtypes=[C.POINTER(State),C.POINTER(Packet),C.c_double]
lib.AGCaptchaAction.argtypes=[C.POINTER(State),C.c_int,C.c_double]
lib.AGCaptchaKey.argtypes=[C.POINTER(State),C.c_int,C.c_int,C.c_double]
lib.AGCaptchaTouch.argtypes=[C.POINTER(State),C.c_int,C.c_int,C.c_int,C.c_double]
lib.AGCaptchaSend.argtypes=[C.POINTER(State),C.c_int,C.c_int,C.c_int,C.c_void_p];lib.AGCaptchaSend.restype=C.c_size_t
checks=0

def ok(v):
 global checks
 assert v;checks+=1

def parse(wire,command=-123):
 p=Packet();return lib.AGNotesParse(wire,len(wire),command,C.byref(p)),p

def send(s,op):
 out=C.create_string_buffer(1040);n=lib.AGCaptchaSend(C.byref(s),op,480,640,out);return out.raw[:n]

def touch(s,cell):
 a=s.packet.g;x=a[2]+cell%3*(a[4]+a[5])+a[4]//2;y=a[3]+cell//3*(a[4]+a[5])+a[4]//2
 lib.AGCaptchaTouch(C.byref(s),0,x,y,1);lib.AGCaptchaTouch(C.byref(s),2,x,y,1)

def setup(p):
 s=State();lib.AGCaptchaInit(C.byref(s));lib.AGCaptchaContext(C.byref(s),1,1);ok(lib.AGCaptchaReceive(C.byref(s),C.byref(p),1)==1);return s

for f in sorted(D.glob('*.bin')):
 wire=f.read_bytes();valid,p=parse(wire);ok(valid==1);ok(p.kind==1 and p.type in range(1,7));s=State();lib.AGCaptchaInit(C.byref(s));ok(not lib.AGCaptchaReceive(C.byref(s),C.byref(p),1));ok(not s.active)
 lib.AGCaptchaContext(C.byref(s),1,0);ok(not lib.AGCaptchaReceive(C.byref(s),C.byref(p),1));s=setup(p)
 # Every packet must be atomic: truncated fields/images and trailing data fail.
 rng=random.Random(77)
 for cut in sorted(set([0,1,2,3,10,20,len(wire)-1]+[rng.randrange(len(wire)) for _ in range(20)])):ok(not parse(wire[:cut])[0])
 ok(not parse(wire+b'\0')[0]);bad=bytearray(wire);bad[0]=9;ok(not parse(bytes(bad))[0])
 # Answer bytes must use the original nonce and the unscaled server coordinate system.
 answer=f.with_suffix('.answer').read_bytes()
 if p.type in (1,2,4):
  touch(s,answer[0]);ok(s.used==1);touch(s,answer[0]);ok(s.used==0)
  for cell in answer:touch(s,cell)
  ok(s.used==len(answer));touch(s,next(i for i in range(9) if i not in answer));ok(s.used==len(answer))
 elif p.type in (3,5):
  lib.AGCaptchaAction(C.byref(s),1,2);ok(not s.waiting and s.op==-1)
  x,y=struct.unpack('>HH',answer);side=p.d[2];lib.AGCaptchaTouch(C.byref(s),0,s.x+side//2,s.y+side//2,2);lib.AGCaptchaTouch(C.byref(s),1,x,y,2);lib.AGCaptchaTouch(C.byref(s),2,x,y,2);ok(s.placed)
 else:
  for _ in range(answer[0]):lib.AGCaptchaAction(C.byref(s),5,2)
  ok(s.rotation==answer[0])
 lib.AGCaptchaAction(C.byref(s),1,3);ok(s.op==1 and s.waiting)
 expected=b'\2\1'+struct.pack('>H',p.nonceLength)+bytes(p.nonce[:p.nonceLength])+bytes([len(answer)])+answer
 ok(send(s,1)==expected)
 before=s.op;lib.AGCaptchaAction(C.byref(s),2,4);ok(s.op==before) # no resend/refresh while waiting
 lib.AGCaptchaAction(C.byref(s),2,14);ok(s.op==2 and s.waiting)
 ok(send(s,2)==b'\2\2'+struct.pack('>H',p.nonceLength)+bytes(p.nonce[:p.nonceLength]))
 lib.AGCaptchaContext(C.byref(s),0,1);ok(not s.active and not s.waiting);ok(not lib.AGCaptchaReceive(C.byref(s),C.byref(p),15))
 s=setup(p);lib.AGCaptchaContext(C.byref(s),1,0);ok(not s.active);ok(not lib.AGCaptchaReceive(C.byref(s),C.byref(p),15));lib.AGCaptchaContext(C.byref(s),1,1);ok(lib.AGCaptchaReceive(C.byref(s),C.byref(p),16)==1)
 lib.AGCaptchaAction(C.byref(s),3,17);ok(not s.active and s.op==3 and send(s,3)==b'\2\3')
for data,cmd in [(b'\1\1\0\0',-122),(b'\1\0\0\0',-122),(b'\2\3\0',-123),(b'\2\3\1',-123),(b'\2\0',-123),(b'\2\2\2\0\0',-123)]:ok(parse(data,cmd)[0]==1)
for data,cmd in [(b'\1\2\0\0',-122),(b'\1\1',-122),(b'\2\3\2',-123),(b'\2\0\0',-123),(b'\2\2\2\0\5abc',-123)]:ok(parse(data,cmd)[0]==0)
s=State();lib.AGCaptchaInit(C.byref(s));ok(send(s,0)==b'\2\0\1\xe0\2\x80')
report={'passed':True,'assertions':checks,'server_fixtures':30,'modes':6,'viewports':5,'live_requests':0,'packet_size':C.sizeof(Packet),'state_size':C.sizeof(State)}
(R/'build/notes-protocol-check.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS',report)
