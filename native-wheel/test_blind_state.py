"""Bomb-blind applies only to the local target, with server-controlled expiry."""
import ctypes as C,json,subprocess,sys,tempfile
from pathlib import Path
R=Path(__file__).resolve().parent
class State(C.Structure):_fields_=[('arena',C.c_size_t),('local',C.c_int),('valid',C.c_int),('active',C.c_int)]
cases=0
with tempfile.TemporaryDirectory() as d:
    p=Path(d)/'blind.so';subprocess.run(['cc','-dynamiclib' if sys.platform=='darwin' else '-shared','-fPIC','-O2','-Wall','-Wextra','-Werror',str(R/'BlindState.c'),'-o',str(p)],check=True)
    lib=C.CDLL(str(p));packet=lib.AGBlindPacket;packet.argtypes=[C.POINTER(State),C.c_size_t,C.c_int,C.c_int,C.c_int];packet.restype=C.c_int
    ctx=lib.AGBlindContext;ctx.argtypes=[C.POINTER(State),C.c_size_t,C.c_int];ctx.restype=C.c_int
    reset=lib.AGBlindReset;reset.argtypes=[C.POINTER(State)]
    for local in range(8):
        s=State();assert packet(C.byref(s),123,local,0,local)==1 and s.active
        for frame in range(10000):assert ctx(C.byref(s),123,local)==1 and s.active
        for target in [x for x in range(8) if x!=local]+[8,64,100,127,255]:
            for status in (0,1):assert packet(C.byref(s),123,local,status,target)==0 and s.active;cases+=1
        assert packet(C.byref(s),123,local,2,local)==0 and s.active
        assert packet(C.byref(s),123,local,1,local)==1 and not s.active
        assert packet(C.byref(s),123,local,0,local)==1 and s.active
        assert ctx(C.byref(s),124,local)==1 and not s.active
        packet(C.byref(s),124,local,0,local);reset(C.byref(s));assert not s.active
        packet(C.byref(s),124,local,0,local);assert ctx(C.byref(s),0,local)==0 and not s.active
        for invalid in (-1,8,127):assert packet(C.byref(s),123,invalid,0,invalid)==0 and not s.active
        cases+=10
report=dict(passed=True,state_cases=cases,local_slots=8,server_state0_applies=True,
    server_state1_clears=True,other_players_do_not_change_local_blindness=True,
    expiry_independent_of_speed_and_frame_count=True,arena_change_and_exit_reset=True)
(R/'build').mkdir(exist_ok=True);(R/'build/blind-state-check.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS',report)
