"""Execute Apple ARM64 camera and walk clocks together, using controlled time."""
import json
import test_device_bridge as t
from unicorn import UC_HOOK_CODE
now_ns=0
def exact_time(uc,pc,size,_):
    if pc in t.imports and t.imports[pc]=='_clock_gettime':
        t.put(t.reg(1),'<qq',now_ns//1000000000,now_ns%1000000000);t.ret()
    else:t.hook(uc,pc,size,_)
# Integer nanoseconds avoid turning exact30ms boundaries into29.999999ms
# through the general fixture's floating-point clock conversion.
t.u.hook_del(t.BASE_HOOK);t.u.hook_add(UC_HOOK_CODE,exact_time)
cases=0
for variant in range(6):
    for fps in (20,60,120,1000):
        for delta in (-20,20):
            camera=t.alloc(0x100);player=t.alloc(0x200);start=(2000+cases*100)*1000000000
            counts=[0,0];walking=0
            for frame in range(fps):
                now_ns=start+frame*1000000000//fps
                for axis in (0,1):counts[axis]+=t.call('_AGCameraAllow',variant,camera,axis,delta&0xffffffff)
                walking+=t.call('_AGMoveAllow',variant,player,0)
            expected=min(fps,((fps-1)*1000000000//fps)//15000000+1)
            expected_walk=min(fps,((fps-1)*1000000000//fps)//30000000+1)
            assert counts==[expected,expected] and walking==expected_walk,(variant,fps,delta,counts,walking)
            cases+=1
for variant in (-1,6):assert t.call('_AGCameraAllow',variant&0xffffffff,t.alloc(0x100),0,20)==0
report=dict(passed=True,apple_arm64_timing_cases=cases,variants=6,
    manual_camera_interval_ms=15,walking_interval_ms=30,independent_axes=True,
    frame_rates=[20,60,120,1000],live_game_requests=0)
(t.ROOT/'build/camera-device-check.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS',report)
