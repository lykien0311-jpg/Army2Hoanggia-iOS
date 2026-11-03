import ctypes as C,tempfile,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parent
class Clock(C.Structure):_fields_=[('player',C.c_size_t),('step',C.c_uint64),('direction',C.c_int),('initialized',C.c_int)]
with tempfile.TemporaryDirectory()as d:
 p=Path(d)/'move.so';subprocess.run(['cc','-dynamiclib'if sys.platform=='darwin'else'-shared','-fPIC','-O2','-Wall','-Wextra','-Werror',str(R/'Movement.c'),'-o',str(p)],check=True)
 l=C.CDLL(str(p));f=l.AGMoveAllowAt;f.argtypes=[C.POINTER(Clock),C.c_size_t,C.c_int,C.c_uint64];f.restype=C.c_int
 for tick in (1,2,5,10,25,50):
  c=Clock();times=[ms for ms in range(0,1000,tick) if f(C.byref(c),123,0,ms*1000000)]
  assert len(times)==min(len(range(0,1000,tick)),((999//tick)*tick)//30+1),(tick,times)
 for fps in (30,60,90,120,144,240,1000):
  c=Clock();times=[i for i in range(fps)if f(C.byref(c),123,0,i*1000000000//fps)]
  assert len(times)==min(fps,((fps-1)*1000000000//fps)//30000000+1),(fps,times)
 c=Clock();assert f(C.byref(c),123,0,0)==1
 assert f(C.byref(c),123,0,29999999)==0
 assert f(C.byref(c),123,0,30000000)==1
 assert f(C.byref(c),123,1,30000001)==1
 assert f(C.byref(c),124,1,30000002)==1
 assert f(C.byref(c),124,1,3000000000)==1
 assert f(C.byref(c),124,1,3000000001)==0
 assert f(C.byref(c),124,1,1)==1
 assert f(C.byref(c),0,1,2)==0
print('PASS: 30ms walking pace across20–1000 input ticks/second; immediate direction/player change; no catch-up burst, no queued steps after release')
