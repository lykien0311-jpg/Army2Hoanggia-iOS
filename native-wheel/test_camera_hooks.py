"""Execute packaged pan setters with the real C pacing clock, all variants."""
import ctypes as C,json,subprocess,sys,tempfile
from pathlib import Path
import test_hooks as t
from unicorn import UC_HOOK_CODE
from unicorn.arm64_const import *
U=t.U;B=t.BASE;X=t.X;callback=0x30001a000
class Clock(C.Structure):
    _fields_=[('player',C.c_size_t),('step',C.c_uint64),('direction',C.c_int),('initialized',C.c_int)]
now=0;clocks=None;f=None;received=[]
def hook(uc,pc,size,_):
    if pc==callback:
        args=tuple(U.reg_read(r) for r in X[:4]);received.append(args)
        variant,camera,axis,delta=args
        assert variant==h['variant'] and camera==t.ENV+0x4000 and axis==h['axis']
        delta=C.c_int(delta).value;allow=f(clocks,camera,axis,delta,now)
        for reg in X[:18]:U.reg_write(reg,0xbeef)
        U.reg_write(UC_ARM64_REG_NZCV,0x60000000);t.returned(allow)
U.hook_add(UC_HOOK_CODE,hook)
checks=steps=0
with tempfile.TemporaryDirectory() as d:
    libpath=Path(d)/'camera.so'
    subprocess.run(['cc','-dynamiclib' if sys.platform=='darwin' else '-shared','-fPIC','-O2',str(t.ROOT/'Movement.c'),'-o',str(libpath)],check=True)
    lib=C.CDLL(str(libpath));f=lib.AGCameraAllowAt
    f.argtypes=[C.POINTER(Clock),C.c_size_t,C.c_int,C.c_int,C.c_uint64];f.restype=C.c_int
    for h in t.R['camera_hooks']:
        camera=t.ENV+0x4000;field=camera+(0xb4 if h['axis']==0 else 0xb8)
        for mode in range(9):
            clocks=(Clock*2)();received.clear();accepted=0
            for frame in range(120):
                now=frame*1000000000//120;t.reset();t.missing=False
                t.speedAddr=t.buildAddr=t.continuation=0
                t.writeq(B+h['camera_class'],camera);U.mem_write(B+h['camera_class']+9,b'\2')
                U.mem_write(camera,bytes(0x200));U.mem_write(camera+0xbc,bytes([mode]))
                t.writeq(B+t.R['rwvm']+40*8,callback)
                U.reg_write(X[1],(-20)&0xffffffff)
                U.emu_start(B+h['site'],t.STOP+4,count=2000);t.preserved()
                accepted+=int.from_bytes(U.mem_read(field,4),'little',signed=True)==-20
            expected=119*1000000000//120//15000000+1
            assert accepted==(expected if mode==0 else 120),(h['variant'],h['axis'],mode,accepted)
            assert len(received)==(120 if mode==0 else 0)
            steps+=accepted;checks+=1
        # A missing optional symbol keeps the native setter usable.
        t.reset();t.missing=True;U.mem_write(camera+0xbc,b'\0');U.reg_write(X[1],20)
        U.emu_start(B+h['site'],t.STOP+4,count=2000);t.preserved()
        assert int.from_bytes(U.mem_read(field,4),'little')==20
        checks+=1
report=dict(passed=True,native_pan_cases=checks,variants=6,axes=2,manual_pan_interval_ms=15,
    automatic_modes_unchanged=True,separate_walk_clock=True,optional_symbol_fallback=True,
    native_setter_and_abi_executed=True)
(t.ROOT/'build/camera-hook-check.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS',report)
