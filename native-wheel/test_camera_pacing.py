"""Manual camera rate stays independent of frame rate, axes and walking."""
import ctypes as C,json,subprocess,sys,tempfile
from pathlib import Path
R=Path(__file__).resolve().parent
class Clock(C.Structure):
    _fields_=[('player',C.c_size_t),('step',C.c_uint64),('direction',C.c_int),('initialized',C.c_int)]
checks=0
with tempfile.TemporaryDirectory() as d:
    p=Path(d)/'camera.so'
    subprocess.run(['cc','-dynamiclib' if sys.platform=='darwin' else '-shared','-fPIC','-O2','-Wall','-Wextra','-Werror',str(R/'Movement.c'),'-o',str(p)],check=True)
    lib=C.CDLL(str(p));f=lib.AGCameraAllowAt
    f.argtypes=[C.POINTER(Clock),C.c_size_t,C.c_int,C.c_int,C.c_uint64];f.restype=C.c_int
    walk=lib.AGMoveAllowAt;walk.argtypes=[C.POINTER(Clock),C.c_size_t,C.c_int,C.c_uint64];walk.restype=C.c_int
    for fps in (20,30,60,90,120,144,240,1000,10000):
        for delta in (-20,20):
            clocks=(Clock*2)();steps=[0,0];walker=Clock();walks=0
            for frame in range(fps):
                now=frame*1000000000//fps
                for axis in (0,1):steps[axis]+=f(clocks,123,axis,delta,now)
                walks+=walk(C.byref(walker),456,0,now)
            expected=min(fps,((fps-1)*1000000000//fps)//30000000+1)
            assert steps==[expected,expected] and walks==expected,(fps,delta,steps,walks)
            checks+=1
    clocks=(Clock*2)()
    assert f(clocks,123,0,-20,0)==1
    assert f(clocks,123,0,-20,29999999)==0
    assert f(clocks,123,1,-20,29999999)==1
    assert f(clocks,123,0,20,30000000)==1
    assert f(clocks,124,0,20,30000001)==1
    assert f(clocks,124,0,20,5000000000)==1
    assert f(clocks,124,0,20,5000000001)==0
    assert f(clocks,124,0,20,1)==1
    assert f(clocks,0,0,20,2)==0
    assert f(clocks,124,2,20,2)==0
    assert f(clocks,124,-1,20,2)==0
    assert f(clocks,124,0,0,2)==0
report=dict(passed=True,frame_rate_direction_cases=checks,pan_interval_ms=30,
    independent_axes=True,walking_independent=True,no_sleep_or_queued_steps=True)
(R/'build').mkdir(exist_ok=True)
(R/'build/camera-pacing-check.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS',report)
